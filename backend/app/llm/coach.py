import json
import datetime
import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.database.models import DailySchedule, ScheduleVersion, ScheduleBlock
from app.planner.engine import generate_daily_schedule, apply_negotiated_changes
from app.llm.client import call_llm
from app.llm.extractor import get_prompt_content
from app.llm.memory import get_user_memory_context

logger = logging.getLogger("life_os.llm")

def run_night_negotiation(
    db: Session,
    user_id: int,
    user_message: str,
    chat_history: List[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Executes the interactive night review and tomorrow's schedule negotiation.
    Loads today's execution results, tomorrow's current schedule version,
    and persistent memories. Integrates an automatic validation/correction loop.
    """
    if chat_history is None:
        chat_history = []
        
    today_date = datetime.date.today()
    tomorrow_date = today_date + datetime.timedelta(days=1)
    
    # 1. Ensure tomorrow's schedule exists
    tomorrow_sched = db.query(DailySchedule).filter(
        DailySchedule.user_id == user_id,
        DailySchedule.date == tomorrow_date
    ).first()
    if not tomorrow_sched:
        tomorrow_sched = generate_daily_schedule(db, user_id, tomorrow_date)
        
    # 2. Get tomorrow's active blocks
    active_version = db.query(ScheduleVersion).filter(
        ScheduleVersion.daily_schedule_id == tomorrow_sched.id,
        ScheduleVersion.is_active == True
    ).first()
    
    tomorrow_blocks_text = "No blocks scheduled."
    if active_version:
        blocks = sorted(active_version.blocks, key=lambda x: x.planned_start)
        tomorrow_blocks_text = "\n".join([
            f"- {b.planned_start} - {b.planned_end}: {b.title} [Type: {b.type}]"
            for b in blocks
        ])
        
    # 3. Get today's completion results
    today_sched = db.query(DailySchedule).filter(
        DailySchedule.user_id == user_id,
        DailySchedule.date == today_date
    ).first()
    
    today_blocks_text = "No blocks recorded today."
    if today_sched:
        today_version = db.query(ScheduleVersion).filter(
            ScheduleVersion.daily_schedule_id == today_sched.id,
            ScheduleVersion.is_active == True
        ).first()
        if today_version:
            blocks = sorted(today_version.blocks, key=lambda x: x.planned_start)
            today_blocks_text = "\n".join([
                f"{'✅' if b.status == 'completed' else '❌' if b.status == 'skipped' else '⏳'} "
                f"{b.planned_start} - {b.planned_end}: {b.title}"
                f"{f' (Reason: {b.reason})' if b.reason else ''}"
                for b in blocks
            ])
            
    # 4. Get user details and memory profile context
    from app.database.models import User
    user = db.query(User).filter(User.id == user_id).first()
    user_name = user.name if (user and user.name) else "User"

    memory_context = get_user_memory_context(db, user_id)
    
    # 4b. Run pattern detection and check for tomorrow's weekday
    from app.analytics.patterns import detect_patterns, save_detected_patterns
    patterns_res = detect_patterns(db, user_id, date_limit=today_date)
    flagged_pats = patterns_res.get("flagged_patterns", [])
    if flagged_pats:
        save_detected_patterns(db, user_id, flagged_pats)

    tomorrow_weekday = tomorrow_date.weekday()
    tomorrow_pats = [p for p in flagged_pats if p["weekday"] == tomorrow_weekday]

    if tomorrow_pats:
        warnings_lines = [
            f"- ⚠️ User historically skips {p['category_display']} on {p['weekday_plural']} "
            f"({p['skipped']} of {p['total']} times, {int(p['skip_rate']*100)}% skip rate). "
            f"Most common reason: {p['most_common_reason'] or 'unspecified'}."
            for p in tomorrow_pats
        ]
        tomorrow_patterns_text = (
            "\n".join(warnings_lines) +
            "\nCOACH DIRECTIVE: If the user attempts to move, skip, delay, or negotiate away these vulnerable blocks, "
            "challenge their excuse directly using this historical data! Ask them what is different tomorrow."
        )
    else:
        tomorrow_patterns_text = f"No recurring skip pattern detected for {tomorrow_date.strftime('%A')}s."

    # 5. Load night review system prompt
    try:
        system_template = get_prompt_content("night_review.md")
    except Exception as e:
        logger.error(f"Failed to read night_review.md: {e}")
        system_template = "You are the Life OS Coach. Review accomplishments and negotiate tomorrow's schedule."
        
    system_prompt = (
        f"{system_template}\n\n"
        f"--- USER PROFILE & LONG-TERM MEMORY ({user_name}) ---\n{memory_context}\n\n"
        f"--- TODAY'S SCHEDULE PERFORMANCE ({today_date}) ---\n{today_blocks_text}\n\n"
        f"--- TOMORROW'S PLAN UNDER NEGOTIATION ({tomorrow_date}) ---\n{tomorrow_blocks_text}\n\n"
        f"--- HISTORICAL PATTERN ALERTS FOR TOMORROW ({tomorrow_date.strftime('%A')}) ---\n{tomorrow_patterns_text}"
    )
    
    # 6. Format chat thread
    conversation_text = ""
    for msg in chat_history:
        role = user_name if msg["role"] == "user" else "Coach"
        conversation_text += f"{role}: {msg['content']}\n"
    conversation_text += f"{user_name}: {user_message}"
    
    # 7. Call LLM
    response_text = call_llm(system_prompt, conversation_text)
    response_text = response_text.replace("```json", "").replace("```", "").strip()
    
    # Helper to parse and execute actions
    def parse_and_apply(resp_str: str) -> Dict[str, Any]:
        data = json.loads(resp_str)
        actions = data.get("actions", [])
        coach_message = data.get("coach_message", "")
        negotiation_complete = data.get("negotiation_complete", False)
        
        if actions:
            # Planner validates and applies changes, writing a new Version
            try:
                apply_negotiated_changes(db, tomorrow_sched.id, actions)
                logger.info(f"Negotiated changes successfully saved as a new version.")
            except ValueError as val_error:
                # Collision or locked block exception! Raise to trigger AI feedback loop
                raise val_error
                
        # If user approved the schedule, lock it
        if negotiation_complete:
            tomorrow_sched.is_locked = True
            db.commit()
            
        return {
            "coach_message": coach_message,
            "actions_applied": len(actions),
            "negotiation_complete": negotiation_complete,
            "raw_response": resp_str
        }

    # Try parsing and applying actions, with automatic AI self-correction retry
    try:
        return parse_and_apply(response_text)
    except ValueError as validation_err:
        # Collision error happened! Let's pass the error to Claude and let it try again
        logger.warning(f"Negotiation validation failed: {validation_err}. Retrying with Claude correction...")
        
        correction_prompt = (
            f"{user_name}: {user_message}\n\n"
            f"SYSTEM NOTICE: Your proposed moves failed validation:\n"
            f"Error: {str(validation_err)}\n\n"
            f"Please review the collision with fixed blocks, change the start/end times "
            f"to resolve the conflict, and output corrected JSON."
        )
        
        corrected_response_text = call_llm(system_prompt, correction_prompt)
        corrected_response_text = corrected_response_text.replace("```json", "").replace("```", "").strip()
        
        try:
            return parse_and_apply(corrected_response_text)
        except Exception as retry_err:
            logger.error(f"Correction loop failed again: {retry_err}")
            # If it fails twice, return a safe message without applying actions
            return {
                "coach_message": f"I tried to move those slots, but there is a schedule conflict: {str(validation_err)}. Let's try picking another time.",
                "actions_applied": 0,
                "negotiation_complete": False,
                "raw_response": corrected_response_text
            }
    except Exception as parse_err:
        logger.error(f"Failed to parse Claude negotiation response: {parse_err}")
        return {
            "coach_message": "Let's review that schedule again. Can you restate what you want to change?",
            "actions_applied": 0,
            "negotiation_complete": False,
            "raw_response": response_text
        }
