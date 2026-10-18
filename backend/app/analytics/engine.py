import datetime
from collections import Counter
from sqlalchemy.orm import Session
from app.database.models import DailySchedule, ScheduleVersion, ScheduleBlock
from app.planner.free_slots import time_to_minutes

def calculate_block_minutes(start_str: str, end_str: str) -> int:
    """Calculate minutes between two time strings."""
    try:
        s_min = time_to_minutes(start_str)
        e_min = time_to_minutes(end_str)
        if e_min < s_min:
            e_min += 24 * 60
        return e_min - s_min
    except Exception:
        return 0

def get_weekly_stats(db: Session, user_id: int, date_limit: datetime.date = None) -> dict:
    """
    Computes performance statistics for the user over the last 7 days.
    """
    if date_limit is None:
        date_limit = datetime.date.today()
        
    start_date = date_limit - datetime.timedelta(days=6)
    
    # Query all daily schedules in range
    schedules = db.query(DailySchedule).filter(
        DailySchedule.user_id == user_id,
        DailySchedule.date >= start_date,
        DailySchedule.date <= date_limit
    ).all()
    
    total_planned_minutes = 0
    total_completed_minutes = 0
    
    agency_planned = 0
    agency_completed = 0
    dsa_planned = 0
    dsa_completed = 0
    
    completed_blocks_count = 0
    skipped_blocks_count = 0
    
    skip_reasons = []
    daily_completion = {}  # date_str -> completed_minutes
    
    for sched in schedules:
        active_version = db.query(ScheduleVersion).filter(
            ScheduleVersion.daily_schedule_id == sched.id,
            ScheduleVersion.is_active == True
        ).first()
        
        if not active_version:
            continue
            
        date_str = sched.date.strftime("%Y-%m-%d")
        daily_completion[date_str] = 0
        
        for b in active_version.blocks:
            # We don't count fixed 'college' or general 'break' blocks in focus metrics unless completed, 
            # let's focus on deadlines, dsa, agency, custom tasks for focus hours.
            # However, Reality Score is typically based on ALL scheduled blocks or core productive blocks.
            # Let's count core productive blocks (deadline, agency, dsa)
            is_productive = b.type in ["deadline", "agency", "dsa"]
            
            b_mins = calculate_block_minutes(b.planned_start, b.planned_end)
            
            if is_productive:
                total_planned_minutes += b_mins
                if b.type == "agency":
                    agency_planned += b_mins
                elif b.type == "dsa":
                    dsa_planned += b_mins
                    
            if b.status == "completed":
                completed_blocks_count += 1
                if is_productive:
                    total_completed_minutes += b_mins
                    daily_completion[date_str] += b_mins
                    if b.type == "agency":
                        agency_completed += b_mins
                    elif b.type == "dsa":
                        dsa_completed += b_mins
            elif b.status == "skipped":
                skipped_blocks_count += 1
                if b.reason:
                    skip_reasons.append(b.reason)

    # 1. Reality Score calculation
    reality_score = 0.0
    if total_planned_minutes > 0:
        reality_score = round((total_completed_minutes / total_planned_minutes) * 100, 1)
        
    # 2. Category percentages
    agency_score = 0.0
    if agency_planned > 0:
        agency_score = round((agency_completed / agency_planned) * 100, 1)
        
    dsa_score = 0.0
    if dsa_planned > 0:
        dsa_score = round((dsa_completed / dsa_planned) * 100, 1)
        
    # 3. Productive/Unproductive Days
    most_productive_day = "N/A"
    least_productive_day = "N/A"
    if daily_completion:
        sorted_days = sorted(daily_completion.items(), key=lambda x: x[1], reverse=True)
        most_productive_day = sorted_days[0][0] if sorted_days[0][1] > 0 else "N/A"
        least_productive_day = sorted_days[-1][0]
        
    # 4. Calculate Gym Streak
    gym_streak = 0
    check_date = date_limit
    
    # Count backwards up to 30 days
    for _ in range(30):
        sched = db.query(DailySchedule).filter(
            DailySchedule.user_id == user_id,
            DailySchedule.date == check_date
        ).first()
        
        if not sched:
            # If no schedule generated, but it's in the past, break streak
            if check_date < date_limit - datetime.timedelta(days=1):
                break
            # If it's today and not completed yet, check yesterday to continue streak
            check_date -= datetime.timedelta(days=1)
            continue
            
        active_version = db.query(ScheduleVersion).filter(
            ScheduleVersion.daily_schedule_id == sched.id,
            ScheduleVersion.is_active == True
        ).first()
        
        if not active_version:
            break
            
        # Find gym block
        gym_block = next((b for b in active_version.blocks if "gym" in b.title.lower() or b.type == "gym"), None)
        if gym_block:
            if gym_block.status == "completed":
                gym_streak += 1
            else:
                # Skipped or pending in the past breaks the streak
                # If it's today and still pending, we don't break the streak immediately, check yesterday
                if check_date == date_limit and gym_block.status == "pending":
                    pass
                else:
                    break
        else:
            # Gym not scheduled this day, since gym is daily, break
            break
            
        check_date -= datetime.timedelta(days=1)
        
    reason_counts = dict(Counter(skip_reasons))
    
    return {
        "reality_score": reality_score,
        "total_planned_hours": round(total_planned_minutes / 60, 1),
        "total_completed_hours": round(total_completed_minutes / 60, 1),
        "agency_planned_hours": round(agency_planned / 60, 1),
        "agency_completed_hours": round(agency_completed / 60, 1),
        "agency_score": agency_score,
        "dsa_planned_hours": round(dsa_planned / 60, 1),
        "dsa_completed_hours": round(dsa_completed / 60, 1),
        "dsa_score": dsa_score,
        "gym_streak": gym_streak,
        "completed_blocks_count": completed_blocks_count,
        "skipped_blocks_count": skipped_blocks_count,
        "most_productive_day": most_productive_day,
        "least_productive_day": least_productive_day,
        "skip_reasons_breakdown": reason_counts,
        "daily_focus_hours": {day: round(mins / 60, 1) for day, mins in daily_completion.items()}
    }
