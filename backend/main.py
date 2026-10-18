import asyncio
import datetime
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal, settings, engine, Base
from app.database.models import User, DailySchedule, ScheduleVersion, ScheduleBlock
from app.telegram.bot import get_telegram_app, send_morning_checkin, send_block_checkin, send_tomorrow_negotiation
from app.api.routes import router

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("life_os.main")

# Create FastAPI app
app = FastAPI(title="LIFE OS Backend", version="1.0")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# Initialize Scheduler
scheduler = BackgroundScheduler()

# --- Background Task Definitions ---

def check_block_endings():
    """Runs every minute to check if any active schedule block just ended."""
    db = SessionLocal()
    try:
        now = datetime.datetime.now()
        today_date = now.date()
        time_str = now.strftime("%H:%M:00")
        
        # Look for daily schedule for today
        sched = db.query(DailySchedule).filter(DailySchedule.date == today_date).first()
        if not sched:
            return
            
        active_version = db.query(ScheduleVersion).filter(
            ScheduleVersion.daily_schedule_id == sched.id,
            ScheduleVersion.is_active == True
        ).first()
        
        if not active_version:
            return
            
        # Get blocks that ended in the last minute (to handle small delays)
        # e.g., if block ended at 18:00:00 and current time is 18:00:15
        for b in active_version.blocks:
            if b.status == "pending" and b.planned_end <= time_str:
                # To prevent double notifications, we check if we already checked it in cache
                # Set status to pending still, but send message
                # For this MVP, we can check if it ended within the last 2 minutes
                b_end_time = datetime.datetime.strptime(f"{today_date} {b.planned_end}", "%Y-%m-%d %H:%M:%S")
                diff = (now - b_end_time).total_seconds()
                
                # Check within last 90 seconds
                if 0 <= diff <= 90:
                    owner_id = settings.TELEGRAM_OWNER_ID
                    if owner_id == "your_telegram_id_here":
                        owner_id = "123456789"
                        
                    # Trigger bot alert
                    logger.info(f"Triggering follow-up check-in for block: {b.title}")
                    
                    # Run bot message in event loop
                    asyncio.run(send_block_checkin(
                        settings.TELEGRAM_BOT_TOKEN,
                        owner_id,
                        b.id,
                        b.title
                    ))
    except Exception as e:
        logger.error(f"Error checking block endings: {e}")
    finally:
        db.close()


def send_morning_checkin_job():
    """Triggers the morning energy level survey."""
    owner_id = settings.TELEGRAM_OWNER_ID
    if owner_id == "your_telegram_id_here":
        owner_id = "123456789"
        
    logger.info("Triggering morning energy check-in...")
    try:
        asyncio.run(send_morning_checkin(settings.TELEGRAM_BOT_TOKEN, owner_id))
    except Exception as e:
        logger.error(f"Failed to send morning check-in: {e}")


def send_tomorrow_schedule_prompt_job():
    """Generates tomorrow's schedule (at 8:30 PM) and sends review notification (at 9:00 PM)."""
    db = SessionLocal()
    try:
        owner_id = settings.TELEGRAM_OWNER_ID
        if owner_id == "your_telegram_id_here":
            owner_id = "123456789"
            
        user = db.query(User).filter(User.telegram_id == str(owner_id)).first()
        if not user:
            logger.warning("No owner user found to send tomorrow's schedule.")
            return
            
        tomorrow_date = datetime.date.today() + datetime.timedelta(days=1)
        
        # 1. Run pattern detection and save flagged patterns into MemoryPattern
        from app.analytics.patterns import detect_patterns, save_detected_patterns
        pat_data = detect_patterns(db, user.id, date_limit=datetime.date.today())
        flagged_pats = pat_data.get("flagged_patterns", [])
        if flagged_pats:
            save_detected_patterns(db, user.id, flagged_pats)

        tomorrow_weekday = tomorrow_date.weekday()
        tomorrow_flags = [p for p in flagged_pats if p["weekday"] == tomorrow_weekday]

        warning_lines = []
        for p in tomorrow_flags:
            cat_name = "DSA" if p["category"] == "dsa" else p["category_display"]
            w_plural = p["weekday_plural"]
            warning_lines.append(f"⚠️ Heads up: you skip {cat_name} on {w_plural} ({p['skipped']} of {p['total']}). What's different tomorrow?")

        pattern_warning = "\n".join(warning_lines) if warning_lines else None

        # 2. Generate schedule if not done yet
        from app.planner.engine import generate_daily_schedule
        sched = db.query(DailySchedule).filter(
            DailySchedule.user_id == user.id,
            DailySchedule.date == tomorrow_date
        ).first()
        if not sched:
            sched = generate_daily_schedule(db, user.id, tomorrow_date)
            
        active_version = db.query(ScheduleVersion).filter(
            ScheduleVersion.daily_schedule_id == sched.id,
            ScheduleVersion.is_active == True
        ).first()
        
        # 3. Format blocks summary
        blocks = sorted(active_version.blocks, key=lambda x: x.planned_start)
        lines = []
        for b in blocks:
            symbol = "🏋" if "gym" in b.title.lower() else "🎓" if "college" in b.title.lower() else "🚀" if "agency" in b.title.lower() else "📘" if "dsa" in b.title.lower() else "🎬" if "client" in b.title.lower() or "reel" in b.title.lower() else "☕" if b.type == "break" else "🗓"
            lines.append(f"{symbol} {b.planned_start[:-3]} - {b.planned_end[:-3]}: {b.title}")
            
        summary = "\n".join(lines)
        
        # 4. Send Telegram notification with pattern warning
        asyncio.run(send_tomorrow_negotiation(
            settings.TELEGRAM_BOT_TOKEN,
            owner_id,
            sched.id,
            summary,
            pattern_warning=pattern_warning
        ))
    except Exception as e:
        logger.error(f"Failed to run tomorrow schedule job: {e}")
    finally:
        db.close()


def weekly_review_job():
    """Runs weekly review on Sunday nights to detect patterns and generate long-term memory updates."""
    db = SessionLocal()
    try:
        owner_id = settings.TELEGRAM_OWNER_ID
        if owner_id == "your_telegram_id_here":
            owner_id = "123456789"
        user = db.query(User).filter(User.telegram_id == str(owner_id)).first()
        if user:
            from app.analytics.weekly import generate_weekly_review
            generate_weekly_review(db, user.id)
    except Exception as e:
        logger.error(f"Failed to run weekly review job: {e}")
    finally:
        db.close()


# --- Startup & Shutdown Event Handlers ---

telegram_app = None

@app.on_event("startup")
async def startup_event():
    global telegram_app
    
    # 1. Initialize DB tables
    logger.info("Initializing database...")
    Base.metadata.create_all(bind=engine)
    
    # 2. Configure background scheduler jobs
    logger.info("Configuring background scheduler jobs...")
    
    # Check block ending status every 1 minute
    scheduler.add_job(check_block_endings, 'interval', minutes=1, id='check_block_endings')
    
    # Morning energy questionnaire at 7:00 AM (daily)
    scheduler.add_job(send_morning_checkin_job, 'cron', hour=7, minute=0, id='morning_checkin')
    
    # Tomorrow's plan approval outline at 9:00 PM (daily)
    scheduler.add_job(send_tomorrow_schedule_prompt_job, 'cron', hour=21, minute=0, id='tomorrow_plan')
    
    # Weekly review on Sunday at 9:30 PM
    scheduler.add_job(weekly_review_job, 'cron', day_of_week='sun', hour=21, minute=30, id='weekly_review')
    
    # Start scheduler
    scheduler.start()
    
    # 3. Initialize and start Telegram Bot polling
    token = settings.TELEGRAM_BOT_TOKEN
    if token and token != "your_bot_token_here":
        logger.info("Starting Telegram Bot listener (polling)...")
        telegram_app = get_telegram_app()
        await telegram_app.initialize()
        await telegram_app.updater.start_polling()
        await telegram_app.start()
    else:
        logger.warning("TELEGRAM_BOT_TOKEN is set to default. Telegram bot will not start.")


@app.on_event("shutdown")
async def shutdown_event():
    global telegram_app
    
    # Stop scheduler
    logger.info("Stopping background scheduler...")
    scheduler.shutdown()
    
    # Stop Telegram bot
    if telegram_app:
        logger.info("Stopping Telegram Bot...")
        await telegram_app.updater.stop()
        await telegram_app.stop()
        await telegram_app.shutdown()


@app.get("/")
def read_root():
    return {"status": "LIFE_OS API is active", "version": "1.0"}
