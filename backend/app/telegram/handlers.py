import datetime
import json
import logging
import re
from typing import Optional, Tuple
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal, settings
from app.database.models import (
    User,
    DailySchedule,
    ScheduleVersion,
    ScheduleBlock,
    InboxItem,
    InboxExtraction,
    MemoryProfile
)
from app.telegram.keyboards import (
    get_energy_keyboard,
    get_block_checkin_keyboard,
    get_skip_reason_keyboard,
    get_schedule_approval_keyboard,
    get_undo_inbox_keyboard
)
from app.llm.extractor import extract_inbox_item
from app.llm.coach import run_night_negotiation
from app.analytics.patterns import detect_patterns

logger = logging.getLogger("life_os.telegram")

def get_db():
    return SessionLocal()

def verify_owner(update: Update) -> bool:
    """Verifies that the incoming message is from the authorized owner."""
    user = update.effective_user
    if not user:
        return False
    owner_id = settings.TELEGRAM_OWNER_ID
    # Handle bootstrap default values
    if owner_id == "your_telegram_id_here":
        owner_id = "123456789"
    return str(user.id) == str(owner_id)

def get_or_create_user(db: Session, effective_user) -> User:
    """Helper to retrieve or initialize the user row."""
    user = db.query(User).filter(User.telegram_id == str(effective_user.id)).first()
    if not user:
        user = User(
            name=effective_user.first_name or "Owner",
            telegram_id=str(effective_user.id),
            timezone=settings.TIMEZONE
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


# --- Intent Classification Patterns & Logic ---

GREETING_REGEX = re.compile(
    r"^(hi|hello|hey|good\s+(morning|afternoon|evening|day)|howdy|sup|yo|greetings)"
    r"(\s+(there|assistant|bot|friend|mate|all|everyone))?[!.,? ]*$",
    re.IGNORECASE
)

SMALL_TALK_PATTERNS = [
    r"^(thanks|thank you|thx|ty|thanks a lot|cheers)[\s.!]*$",
    r"^(ok|okay|k|cool|awesome|great|nice|perfect|sounds good|done|yes|no|yep|nope)[\s.!]*$",
    r"^(bye|goodbye|see you|see ya|good night)[\s.!]*$",
    r"^(how are you|how are you doing|how's everything|who are you|what can you do|what are you)[\s.?!]*$",
]

ACTION_VERBS = {
    "finish", "complete", "send", "email", "submit", "review", "write", "create",
    "build", "code", "implement", "fix", "debug", "buy", "order", "call", "prep",
    "prepare", "edit", "record", "film", "shoot", "upload", "post", "publish",
    "schedule", "clean", "read", "study", "practice", "solve", "design", "draft",
    "update", "pay", "wire", "invoice", "push", "deploy", "meet", "organize",
    "cancel", "book", "workout", "exercise", "deliver", "make", "pack", "remind",
    "follow", "setup", "check"
}

TASK_MARKERS = [
    r"\bby\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|tonight|next\s+week|\d{1,2}(:\d{2})?\s*(am|pm)?)\b",
    r"\b(urgent|deadline|due|asap|priority)\b",
    r"^(todo|task|action item)[:\s-]",
    r"\b(need to|have to|must|remind me to|remember to|don't forget to)\b",
]

def classify_text_intent(text: str) -> str:
    """
    Classifies raw plain text when chat_state is idle.
    Check order:
    1. Greeting (hi, hello, hey, good morning...)
    2. Plan question (today/tomorrow + plan/schedule, what's next, what now, current block)
    3. Pattern question (patterns, habits, what do I skip)
    4. Task (actionable) or non_task (small talk, too short, pure question)
    """
    raw = text.strip()
    clean = raw.lower()
    
    # 1. Greeting
    if GREETING_REGEX.match(clean):
        return "greeting"
        
    # 2. Plan question
    has_today = "today" in clean or "now" in clean or "current" in clean
    has_tomorrow = "tomorrow" in clean
    has_plan = "plan" in clean or "schedule" in clean
    
    plan_keywords = [
        "what's next", "whats next", "what is next",
        "what now", "current block", "next block",
        "what am i doing", "what do i have next",
        "show schedule", "show plan", "my plan", "my schedule"
    ]
    
    if has_tomorrow and has_plan:
        return "plan_tomorrow"
    if (has_today and has_plan) or any(pk in clean for pk in plan_keywords) or (has_plan and ("what is" in clean or "tell me" in clean or "show" in clean)):
        return "plan_today"
        
    # 3. Pattern question
    pattern_keywords = [
        "pattern", "patterns", "habit", "habits",
        "what do i skip", "what do i usually skip", "what am i skipping",
        "what i skip", "skip patterns", "skipping patterns",
        "where do i slack", "what do i miss", "why do i skip"
    ]
    if any(pk in clean for pk in pattern_keywords):
        return "patterns"
        
    # 4. Task vs Non-Task
    words = clean.split()
    if len(words) < 2 or len(clean) < 5:
        return "non_task"
        
    for stp in SMALL_TALK_PATTERNS:
        if re.match(stp, clean, re.IGNORECASE):
            return "non_task"
            
    is_question = clean.endswith("?") or any(clean.startswith(qw) for qw in ["who ", "why ", "where ", "when ", "is it ", "are you ", "what is "])
    has_task_marker = any(re.search(tm, clean, re.IGNORECASE) for tm in TASK_MARKERS)
    
    first_word = words[0].strip(".,!?:")
    has_action_verb = first_word in ACTION_VERBS or (len(words) > 1 and words[1].strip(".,!?:") in ACTION_VERBS and words[0] in ["please", "to", "just", "kindly"])
    
    if has_task_marker or has_action_verb:
        return "task"
        
    if is_question:
        return "non_task"
        
    if len(words) >= 3 and not is_question:
        return "task"
        
    return "non_task"


# --- Schedule & Pattern Formatters ---

def format_today_schedule(db: Session, user_id: int, current_dt: Optional[datetime.datetime] = None) -> str:
    """
    Renders today's schedule from the database, highlighting the current block
    with its icon, title, and remaining minutes.
    """
    if current_dt is None:
        current_dt = datetime.datetime.now()
        
    today_date = current_dt.date()
    now_mins = current_dt.hour * 60 + current_dt.minute
    
    sched = db.query(DailySchedule).filter(
        DailySchedule.user_id == user_id,
        DailySchedule.date == today_date
    ).first()
    
    if not sched:
        from app.planner.engine import generate_daily_schedule
        try:
            sched = generate_daily_schedule(db, user_id, today_date)
        except Exception as e:
            logger.error(f"Error generating today's schedule: {e}")
            return f"📅 **Today's Schedule ({today_date.strftime('%a, %d %b')})**\n\nNo active schedule found for today."
            
    active_version = None
    if sched:
        active_version = db.query(ScheduleVersion).filter(
            ScheduleVersion.daily_schedule_id == sched.id,
            ScheduleVersion.is_active == True
        ).first()
        
    blocks = sorted(active_version.blocks, key=lambda x: x.planned_start) if active_version and active_version.blocks else []
    
    if not blocks:
        return f"📅 **Today's Schedule ({today_date.strftime('%a, %d %b')})**\n\nNo blocks scheduled for today."
        
    lines = [f"📅 **Today's Schedule ({today_date.strftime('%a, %d %b')})**\n"]
    current_block_found = False
    
    for b in blocks:
        symbol = (
            "🏋" if "gym" in b.title.lower()
            else "🎓" if "college" in b.title.lower()
            else "🚀" if "agency" in b.title.lower()
            else "📘" if "dsa" in b.title.lower()
            else "🎬" if "client" in b.title.lower() or "reel" in b.title.lower()
            else "☕" if b.type == "break"
            else "🗓"
        )
        
        start_str = b.planned_start[:5]
        end_str = b.planned_end[:5]
        s_h, s_m = map(int, start_str.split(":"))
        e_h, e_m = map(int, end_str.split(":"))
        start_mins = s_h * 60 + s_m
        end_mins = e_h * 60 + e_m
        
        is_current = (start_mins <= now_mins < end_mins)
        
        if is_current:
            current_block_found = True
            mins_left = end_mins - now_mins
            lines.append(f"▶️ **{start_str} - {end_str}: {symbol} {b.title}** ⏳ *({mins_left}m left)*")
        elif b.status == "completed":
            lines.append(f"✅ ~{start_str} - {end_str}: {symbol} {b.title}~")
        elif b.status == "skipped":
            lines.append(f"❌ ~{start_str} - {end_str}: {symbol} {b.title}~ *(Skipped)*")
        else:
            lines.append(f"• {start_str} - {end_str}: {symbol} {b.title}")
            
    if not current_block_found:
        upcoming = [b for b in blocks if (int(b.planned_start[:2])*60 + int(b.planned_start[3:5])) > now_mins]
        if upcoming:
            next_b = upcoming[0]
            next_start_mins = int(next_b.planned_start[:2])*60 + int(next_b.planned_start[3:5])
            lines.append(f"\n💡 *Currently between blocks. Next: {next_b.title} at {next_b.planned_start[:5]} (in {next_start_mins - now_mins}m)*")
        else:
            lines.append("\n🏁 *All scheduled blocks for today are finished!*")
            
    return "\n".join(lines)


def format_tomorrow_schedule(db: Session, user_id: int) -> Tuple[str, int]:
    """Generates and formats tomorrow's planned schedule with pattern alerts."""
    tomorrow_date = datetime.date.today() + datetime.timedelta(days=1)
    
    sched = db.query(DailySchedule).filter(
        DailySchedule.user_id == user_id,
        DailySchedule.date == tomorrow_date
    ).first()
    
    if not sched:
        from app.planner.engine import generate_daily_schedule
        sched = generate_daily_schedule(db, user_id, tomorrow_date)
        
    active_version = db.query(ScheduleVersion).filter(
        ScheduleVersion.daily_schedule_id == sched.id,
        ScheduleVersion.is_active == True
    ).first()
    
    blocks = sorted(active_version.blocks, key=lambda x: x.planned_start) if active_version and active_version.blocks else []
    
    lines = [f"📅 **Tomorrow ({tomorrow_date.strftime('%a, %d %b')})**\n"]
    for b in blocks:
        symbol = "🏋" if "gym" in b.title.lower() else "🎓" if "college" in b.title.lower() else "🚀" if "agency" in b.title.lower() else "📘" if "dsa" in b.title.lower() else "🎬" if "client" in b.title.lower() or "reel" in b.title.lower() else "☕" if b.type == "break" else "🗓"
        lines.append(f"{symbol} {b.planned_start[:5]} - {b.planned_end[:5]}: {b.title}")
        
    # Check for tomorrow pattern warnings
    pat_data = detect_patterns(db, user_id, date_limit=datetime.date.today())
    tomorrow_flags = [p for p in pat_data.get("flagged_patterns", []) if p["weekday"] == tomorrow_date.weekday()]
    if tomorrow_flags:
        lines.append("")
        for p in tomorrow_flags:
            cat_name = "DSA" if p["category"] == "dsa" else p["category_display"]
            lines.append(f"⚠️ Heads up: you skip {cat_name} on {p['weekday_plural']} ({p['skipped']} of {p['total']}). What's different tomorrow?")

    lines.append("\nLooks good?")
    return "\n".join(lines), sched.id


def format_patterns_summary(db: Session, user_id: int) -> str:
    """Renders the flagged habit skip patterns detected over the last 28 days."""
    pat_data = detect_patterns(db, user_id, date_limit=datetime.date.today())
    flagged = pat_data.get("flagged_patterns", [])
    
    if not flagged:
        return (
            "🔍 **Habit Pattern Analysis (Last 28 Days)**\n\n"
            "✅ No negative habit patterns detected! Skip rates are below the 60% threshold across all categories. Great consistency!"
        )
        
    lines = [
        "🔍 **Detected Habit Patterns (Last 28 Days)**\n",
        f"Identified {len(flagged)} recurring skip pattern(s) (>=60% skip rate with >=3 samples):\n"
    ]
    for p in flagged:
        skip_pct = int(round(p["skip_rate"] * 100))
        conf_pct = int(round(p["confidence"] * 100))
        lines.append(
            f"⚠️ **{p['message']}**\n"
            f"   • Skip Rate: {skip_pct}% ({p['skipped']} of {p['total']} skipped)\n"
            f"   • Confidence: {conf_pct}%\n"
            f"   • Most common reason: _{p['most_common_reason']}_\n"
        )
    lines.append("💡 *Tip: The nightly coach and scheduler proactively warn you when these days approach.*")
    return "\n".join(lines)


def format_inbox_items(db: Session, user_id: int, limit: int = 5) -> str:
    """Renders the last N unprocessed active inbox items."""
    items = db.query(InboxItem).filter(
        InboxItem.user_id == user_id,
        InboxItem.status == "active"
    ).order_by(InboxItem.created_at.desc()).limit(limit).all()
    
    if not items:
        return "📥 **Inbox (Unprocessed Tasks)**\n\n🎉 Your Inbox is clean! No active unprocessed items."
        
    lines = [f"📥 **Inbox (Last {len(items)} Unprocessed Tasks)**\n"]
    for item in items:
        p_symbol = "🔴" if item.priority == "urgent" else "🟠" if item.priority == "high" else "🟡"
        date_str = item.created_at.strftime("%b %d") if item.created_at else ""
        lines.append(f"• **{item.title}** ({p_symbol} {item.priority.capitalize()} | {item.suggested_type.capitalize()}) — {date_str}")
        
    lines.append("\n💡 *Send plain text like 'finish client logo by Friday' to add a new task.*")
    return "\n".join(lines)


# --- Bot Command Handlers ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /start command."""
    if not verify_owner(update):
        await update.message.reply_text("Access denied. This is a personal Life OS instance.")
        return
        
    db = get_db()
    try:
        user = get_or_create_user(db, update.effective_user)
        await update.message.reply_text(
            f"Welcome back, {user.name}. {settings.APP_NAME} is running.\n\n"
            f"Commands:\n"
            f"📅 /today - Today's schedule with current block & time left\n"
            f"📅 /tomorrow - Review & approve tomorrow's plan\n"
            f"🔍 /patterns - Flagged habit skip patterns\n"
            f"📥 /inbox - View last 5 unprocessed tasks\n"
            f"⚡ /energy - Morning energy check-in\n"
            f"❓ /help - Command list\n\n"
            f"💬 Send any task (e.g. 'Finish pitch deck by Friday') to add to Inbox, or ask 'What is the today plan?'."
        )
    finally:
        db.close()


async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /today: shows today's schedule, current block marked, and remaining time."""
    if not verify_owner(update):
        return
    db = get_db()
    try:
        user = get_or_create_user(db, update.effective_user)
        schedule_text = format_today_schedule(db, user.id)
        await update.message.reply_text(schedule_text, parse_mode="Markdown")
    finally:
        db.close()


async def tomorrow_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends tomorrow's planned schedule for approval/negotiation."""
    if not verify_owner(update):
        return
    db = get_db()
    try:
        user = get_or_create_user(db, update.effective_user)
        text, sched_id = format_tomorrow_schedule(db, user.id)
        await update.message.reply_text(
            text,
            reply_markup=get_schedule_approval_keyboard(sched_id),
            parse_mode="Markdown"
        )
    finally:
        db.close()


async def patterns_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /patterns: displays flagged habit skip patterns."""
    if not verify_owner(update):
        return
    db = get_db()
    try:
        user = get_or_create_user(db, update.effective_user)
        patterns_text = format_patterns_summary(db, user.id)
        await update.message.reply_text(patterns_text, parse_mode="Markdown")
    finally:
        db.close()


async def inbox_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /inbox: displays the last 5 unprocessed inbox items."""
    if not verify_owner(update):
        return
    db = get_db()
    try:
        user = get_or_create_user(db, update.effective_user)
        inbox_text = format_inbox_items(db, user.id, limit=5)
        await update.message.reply_text(inbox_text, parse_mode="Markdown")
    finally:
        db.close()


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /help: lists all available commands."""
    if not verify_owner(update):
        return
    help_text = (
        f"🤖 **{settings.APP_NAME} - Command Reference**\n\n"
        f"📅 /today - Today's schedule with current block & time left\n"
        f"📅 /tomorrow - Review tomorrow's plan & approval\n"
        f"🔍 /patterns - Flagged habit skip patterns\n"
        f"📥 /inbox - View last 5 unprocessed tasks\n"
        f"⚡ /energy - Record your morning energy score (1-5)\n"
        f"❓ /help - Show this list of commands\n\n"
        f"💬 **Natural Language Support:**\n"
        f"• *'Hi'* / *'Hello'* -> Quick command list\n"
        f"• *'What is the today plan?'* or *'What now?'* -> Today's schedule\n"
        f"• *'What do I skip?'* -> Flagged habit patterns\n"
        f"• *'Finish pitch deck by Friday'* -> Adds task to Inbox with Undo button"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def energy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggers the morning energy questionnaire."""
    if not verify_owner(update):
        return
    await update.message.reply_text(
        "Good Morning. How is your energy level today?",
        reply_markup=get_energy_keyboard()
    )


# --- Plain Text Message Routing Handler ---

async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles raw text messages with strict intent routing:
    1. If user is negotiating schedule, routes to Claude Coach.
    2. Idle state:
       a. Greeting -> Short friendly line + quick commands. (Saves nothing)
       b. Plan question -> Today / tomorrow schedule from DB. (Saves nothing)
       c. Pattern question -> Flagged patterns from detector. (Saves nothing)
       d. Otherwise -> Task. If actionable, extracts and saves with Undo button.
          If non-task (too short, small talk, question), informs user and saves nothing.
    """
    if not verify_owner(update):
        return
        
    raw_text = update.message.text
    if not raw_text:
        return

    db = get_db()
    try:
        user = get_or_create_user(db, update.effective_user)
        
        # 1. Check if user is currently negotiating schedule
        chat_state_rec = db.query(MemoryProfile).filter(
            MemoryProfile.user_id == user.id,
            MemoryProfile.key == "chat_state"
        ).first()
        
        if chat_state_rec and chat_state_rec.value.startswith("negotiating:"):
            daily_schedule_id = int(chat_state_rec.value.split(":")[1])
            await update.message.reply_text("Thinking... 🧠")
            
            chat_history = []
            result = run_night_negotiation(db, user.id, raw_text, chat_history)
            coach_msg = result.get("coach_message", "")
            negotiation_complete = result.get("negotiation_complete", False)
            
            if negotiation_complete:
                chat_state_rec.value = "idle"
                db.commit()
                await update.message.reply_text(
                    f"{coach_msg}\n\nTomorrow's schedule is officially locked! 🔒",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text(
                    f"{coach_msg}\n\n*Review tomorrow's plan again: /tomorrow*",
                    reply_markup=get_schedule_approval_keyboard(daily_schedule_id),
                    parse_mode="Markdown"
                )
            return
            
        # 2. Idle State: Intent Routing
        intent = classify_text_intent(raw_text)
        
        # a. Greeting
        if intent == "greeting":
            await update.message.reply_text(
                "Hey there! 👋 Here are some quick commands you can use:\n\n"
                "📅 /today - View today's schedule\n"
                "📅 /tomorrow - Review tomorrow's plan\n"
                "🔍 /patterns - Flagged habit skip patterns\n"
                "📥 /inbox - View recent tasks\n"
                "⚡ /energy - Morning energy check-in\n"
                "❓ /help - Full command list\n\n"
                "You can also ask 'What is the today plan?' or send a task like 'Finish client logo by Friday'."
            )
            return

        # b. Plan question
        if intent == "plan_today":
            schedule_text = format_today_schedule(db, user.id)
            await update.message.reply_text(schedule_text, parse_mode="Markdown")
            return
            
        if intent == "plan_tomorrow":
            text, sched_id = format_tomorrow_schedule(db, user.id)
            await update.message.reply_text(
                text,
                reply_markup=get_schedule_approval_keyboard(sched_id),
                parse_mode="Markdown"
            )
            return

        # c. Pattern question
        if intent == "patterns":
            patterns_text = format_patterns_summary(db, user.id)
            await update.message.reply_text(patterns_text, parse_mode="Markdown")
            return

        # d. Non-task (small talk, too short, pure question)
        if intent == "non_task":
            await update.message.reply_text(
                "Didn't catch a task there. Try: 'finish client logo by Friday'"
            )
            return

        # e. Actionable Task -> Extract and save to Inbox
        extracted = extract_inbox_item(raw_text)
        
        # Guard against empty/invalid extraction
        task_title = extracted.get("title", "").strip()
        if not task_title or len(task_title) < 3:
            await update.message.reply_text(
                "Didn't catch a task there. Try: 'finish client logo by Friday'"
            )
            return

        inbox_item = InboxItem(
            user_id=user.id,
            title=task_title,
            description=extracted.get("description", raw_text),
            source="telegram",
            priority=extracted.get("priority", "medium").lower(),
            suggested_type=extracted.get("suggested_type", "personal").lower(),
            status="active"
        )
        db.add(inbox_item)
        db.commit()
        db.refresh(inbox_item)
        
        # Save Extraction Log
        extraction_log = InboxExtraction(
            inbox_item_id=inbox_item.id,
            model=settings.MODEL_NAME,
            prompt_version="1.0",
            raw_response=extracted.get("raw_response", ""),
            parsed_response=json.dumps(extracted)
        )
        db.add(extraction_log)
        db.commit()
        
        p_symbol = "🔴" if inbox_item.priority == "urgent" else "🟠" if inbox_item.priority == "high" else "🟡"
        await update.message.reply_text(
            f"Added to Inbox: **{inbox_item.title}** 📥\n"
            f"Priority: {p_symbol} {inbox_item.priority.capitalize()}\n"
            f"Type: {inbox_item.suggested_type.capitalize()}",
            reply_markup=get_undo_inbox_keyboard(inbox_item.id),
            parse_mode="Markdown"
        )
    finally:
        db.close()


# --- Callback Query Handler (Inline Buttons) ---

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles all inline callback button queries."""
    if not verify_owner(update):
        return
        
    query = update.callback_query
    await query.answer()
    
    data = query.data
    db = get_db()
    try:
        user = get_or_create_user(db, update.effective_user)
        
        # Case A: Energy morning check-in
        if data.startswith("energy_"):
            score = int(data.split("_")[1])
            today_date = datetime.date.today()
            
            today_sched = db.query(DailySchedule).filter(
                DailySchedule.user_id == user.id,
                DailySchedule.date == today_date
            ).first()
            
            if not today_sched:
                from app.planner.engine import generate_daily_schedule
                today_sched = generate_daily_schedule(db, user.id, today_date)
                
            today_sched.energy_score = score
            db.commit()
            
            multipliers = {1: 0.6, 2: 0.8, 3: 1.0, 4: 1.2, 5: 1.2}
            mult = multipliers.get(score, 1.0)
            
            coach_quotes = {
                1: "Energy is bottoming out (0.6x multiplier). Expecting low-intensity maintenance. No excuses, get the non-negotiables done.",
                2: "Low energy (0.8x multiplier). Watch out for distraction traps today. Keep moving forward.",
                3: "Baseline energy (1.0x multiplier). Standard output day. Do the work.",
                4: "High energy (1.2x multiplier). Prime state. Attack deep agency work and DSA.",
                5: "Peak energy (1.2x multiplier). Full output mode. Crush your limits today."
            }
            
            await query.edit_message_text(
                f"Recorded Energy: {score}/5 (Focus Multiplier: {mult}x)\n\n"
                f"**Coach:**\n_{coach_quotes[score]}_",
                parse_mode="Markdown"
            )
            
        # Case B: Block completed
        elif data.startswith("block_done_"):
            block_id = int(data.split("_")[2])
            block = db.query(ScheduleBlock).filter(ScheduleBlock.id == block_id).first()
            if block:
                block.status = "completed"
                block.actual_end = datetime.datetime.now().strftime("%H:%M:%S")
                db.commit()
                await query.edit_message_text(f"✅ Completed: **{block.title}**", parse_mode="Markdown")
                
        # Case C: Block not completed
        elif data.startswith("block_notdone_"):
            block_id = int(data.split("_")[2])
            block = db.query(ScheduleBlock).filter(ScheduleBlock.id == block_id).first()
            if block:
                await query.edit_message_text(
                    f"Why did you skip **{block.title}**?",
                    reply_markup=get_skip_reason_keyboard(block_id),
                    parse_mode="Markdown"
                )
                
        # Case D: Skip reason selected
        elif data.startswith("skip_"):
            parts = data.split("_")
            reason_key = parts[1]
            block_id = int(parts[2])
            
            reasons = {
                "tired": "Too tired",
                "work": "Unexpected work",
                "planning": "Bad planning",
                "distracted": "Distraction",
                "motivation": "Low motivation",
                "other": "Other"
            }
            
            block = db.query(ScheduleBlock).filter(ScheduleBlock.id == block_id).first()
            if block:
                block.status = "skipped"
                block.reason = reasons.get(reason_key, "Other")
                db.commit()
                await query.edit_message_text(
                    f"❌ Skipped: **{block.title}**\nReason logged: {block.reason}",
                    parse_mode="Markdown"
                )
                
        # Case E: Schedule Approve
        elif data.startswith("sched_approve_"):
            schedule_id = int(data.split("_")[2])
            sched = db.query(DailySchedule).filter(DailySchedule.id == schedule_id).first()
            if sched:
                sched.is_locked = True
                db.commit()
                await query.edit_message_text("Tomorrow's schedule approved and locked! 🔒🚀")
                
        # Case F: Schedule Negotiate
        elif data.startswith("sched_negotiate_"):
            schedule_id = int(data.split("_")[2])
            state_rec = db.query(MemoryProfile).filter(
                MemoryProfile.user_id == user.id,
                MemoryProfile.key == "chat_state"
            ).first()
            
            if state_rec:
                state_rec.value = f"negotiating:{schedule_id}"
            else:
                state_rec = MemoryProfile(user_id=user.id, key="chat_state", value=f"negotiating:{schedule_id}")
                db.add(state_rec)
            db.commit()
            
            await query.edit_message_text(
                "Coaching session started. 💬\n"
                "What changes do you need to make to tomorrow's schedule? Let's discuss."
            )

        # Case G: Undo newly added Inbox task
        elif data.startswith("undo_inbox_"):
            item_id = int(data.split("_")[2])
            item = db.query(InboxItem).filter(InboxItem.id == item_id).first()
            if item:
                item_title = item.title
                db.delete(item)
                db.commit()
                await query.edit_message_text(
                    f"🗑 Undone: **{item_title}** removed from Inbox.",
                    parse_mode="Markdown"
                )
            else:
                await query.edit_message_text("Item already removed from Inbox.")
                
    finally:
        db.close()
