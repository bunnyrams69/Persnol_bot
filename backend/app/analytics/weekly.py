import json
import datetime
import logging
from sqlalchemy.orm import Session

from app.database.models import WeeklyReview
from app.analytics.engine import get_weekly_stats
from app.llm.client import call_llm
from app.llm.extractor import get_prompt_content
from app.llm.memory import get_user_memory_context, process_memory_updates

logger = logging.getLogger("life_os.analytics.weekly")

def generate_weekly_review(db: Session, user_id: int, date_limit: datetime.date = None) -> dict:
    """
    Generates a weekly review via Claude, updates the user's persistent memory patterns/beliefs,
    and stores the wins, losses, and coaching feedback in the database.
    """
    if date_limit is None:
        date_limit = datetime.date.today()
        
    start_date = date_limit - datetime.timedelta(days=6)
    
    # 1. Fetch weekly statistics
    stats = get_weekly_stats(db, user_id, date_limit)
    
    # 2. Get user memory context
    memory_context = get_user_memory_context(db, user_id)
    
    # 2b. Run deterministic pattern detection and persist into MemoryPattern
    from app.analytics.patterns import detect_patterns, save_detected_patterns
    pattern_results = detect_patterns(db, user_id, date_limit=date_limit)
    flagged_patterns = pattern_results.get("flagged_patterns", [])
    if flagged_patterns:
        save_detected_patterns(db, user_id, flagged_patterns)
        
    pattern_lines = [f"  * {p['message']}" for p in flagged_patterns]
    flagged_patterns_str = "\n".join(pattern_lines) if pattern_lines else "None detected."
    
    # 3. Load weekly review system prompt template
    try:
        system_template = get_prompt_content("weekly_review.md")
    except Exception as e:
        logger.error(f"Failed to read weekly_review.md: {e}")
        system_template = "You are the Life OS Pattern Analyzer. Output wins, losses, coach_feedback, and new_patterns in JSON."
        
    # 4. Format user statistics for the prompt
    skip_reasons_str = ", ".join([f"{k}: {v} times" for k, v in stats.get("skip_reasons_breakdown", {}).items()])
    if not skip_reasons_str:
        skip_reasons_str = "No skips logged."
        
    user_prompt = (
        f"--- CURRENT MEMORY AND BELIEFS ---\n"
        f"{memory_context}\n\n"
        f"--- WEEKLY PERFORMANCE STATS (from {start_date} to {date_limit}) ---\n"
        f"- Reality Score: {stats.get('reality_score')}% (Target: > 70%)\n"
        f"- Total focus hours completed: {stats.get('total_completed_hours')} hrs (out of {stats.get('total_planned_hours')} planned)\n"
        f"- AI Agency output: {stats.get('agency_completed_hours')} hrs completed (out of {stats.get('agency_planned_hours')} planned) - Completion rate: {stats.get('agency_score')}%\n"
        f"- DSA Practice output: {stats.get('dsa_completed_hours')} hrs completed (out of {stats.get('dsa_planned_hours')} planned) - Completion rate: {stats.get('dsa_score')}%\n"
        f"- Gym Consistency: {stats.get('gym_streak')}-day streak\n"
        f"- Skips logged: {stats.get('skipped_blocks_count')} blocks skipped\n"
        f"- Registered skip reasons: {skip_reasons_str}\n\n"
        f"--- DETECTED BEHAVIORAL PATTERNS (last 28 days) ---\n"
        f"{flagged_patterns_str}\n"
    )
    
    logger.info("Calling Claude to generate weekly review...")
    # 5. Call Claude
    response_text = call_llm(system_template, user_prompt)
    response_text = response_text.replace("```json", "").replace("```", "").strip()
    
    try:
        data = json.loads(response_text)
    except Exception as e:
        logger.error(f"Failed to parse Claude weekly review response: {e}. Raw response: {response_text}")
        # Build a fallback dict if parsing fails
        data = {
            "wins": ["Gym streak kept active"],
            "losses": ["Could not parse weekly review details"],
            "coach_feedback": f"Review generation completed, but results formatting was invalid. Stats summary: Reality Score {stats.get('reality_score')}%",
            "new_patterns": []
        }
        response_text = json.dumps(data)
        
    # 6. Trigger long-term memory updates based on this review
    logger.info("Processing long-term memory updates based on weekly review...")
    process_memory_updates(db, user_id, response_text)
    
    # 7. Persist the WeeklyReview record in database
    wins_json = json.dumps(data.get("wins", []))
    losses_json = json.dumps(data.get("losses", []))
    coach_feedback = data.get("coach_feedback", "")
    
    weekly_review = WeeklyReview(
        user_id=user_id,
        start_date=start_date,
        end_date=date_limit,
        wins=wins_json,
        losses=losses_json,
        coach_feedback=coach_feedback
    )
    
    try:
        db.add(weekly_review)
        db.commit()
        db.refresh(weekly_review)
        logger.info(f"WeeklyReview record saved successfully with ID: {weekly_review.id}")
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving weekly review record: {e}")
        
    return {
        "id": weekly_review.id if hasattr(weekly_review, 'id') else None,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": date_limit.strftime("%Y-%m-%d"),
        "wins": data.get("wins", []),
        "losses": data.get("losses", []),
        "coach_feedback": coach_feedback,
        "new_patterns": data.get("new_patterns", []),
        "flagged_patterns": flagged_patterns
    }
