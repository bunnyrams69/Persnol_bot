import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.connection import get_db, settings
from app.database.models import User, DailySchedule, ScheduleVersion, ScheduleBlock, Deadline, RecurringGoal, InboxItem, MemoryProfile, MemoryBelief, MemoryGoal
from app.planner.engine import generate_daily_schedule
from app.analytics.engine import get_weekly_stats
from app.llm.coach import run_night_negotiation

router = APIRouter(prefix="/api")

# --- Pydantic Schemas ---

class UserSchema(BaseModel):
    id: int
    name: str
    telegram_id: str
    timezone: str
    wake_time: str
    sleep_time: str
    
    class Config:
        from_attributes = True

class UserUpdateSchema(BaseModel):
    name: Optional[str] = None
    wake_time: Optional[str] = None
    sleep_time: Optional[str] = None

class ScheduleBlockSchema(BaseModel):
    id: int
    schedule_version_id: int
    title: str
    type: str
    source: str
    priority: int
    planned_start: str
    planned_end: str
    actual_start: Optional[str] = None
    actual_end: Optional[str] = None
    status: str
    reason: Optional[str] = None

    class Config:
        from_attributes = True

class DailyScheduleSchema(BaseModel):
    id: int
    date: str
    user_id: int
    energy_score: Optional[int] = None
    is_locked: bool
    blocks: List[ScheduleBlockSchema] = []

class DeadlineSchema(BaseModel):
    id: int
    title: str
    client_name: Optional[str] = None
    estimated_minutes: int
    actual_minutes: Optional[int] = None
    due_datetime: datetime.datetime
    status: str
    priority: int
    
    class Config:
        from_attributes = True

class DeadlineCreateSchema(BaseModel):
    title: str
    client_name: Optional[str] = None
    estimated_minutes: int = 60
    due_datetime: datetime.datetime
    priority: int = 1

class RecurringGoalSchema(BaseModel):
    id: int
    name: str
    ratio: float
    minimum_minutes: int
    priority: int
    
    class Config:
        from_attributes = True

class GoalUpdateListSchema(BaseModel):
    ratios: List[dict]  # [{"id": 1, "ratio": 0.6}, {"id": 2, "ratio": 0.4}]

class InboxItemSchema(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    source: str
    priority: str
    suggested_type: str
    status: str
    created_at: datetime.datetime
    
    class Config:
        from_attributes = True

class InboxCreateSchema(BaseModel):
    title: str
    description: Optional[str] = None
    source: str = "manual"
    priority: str = "medium"
    suggested_type: str = "personal"

class BlockStatusUpdateSchema(BaseModel):
    status: str  # completed, skipped, pending
    reason: Optional[str] = None

class CoachChatSchema(BaseModel):
    profile: List[dict]
    beliefs: List[str]
    goals: List[dict]

class MessageSchema(BaseModel):
    message: str

class PatternCellSchema(BaseModel):
    weekday: int
    weekday_name: str
    weekday_short: str
    category: str
    category_display: str
    done: int
    skipped: int
    total: int
    skip_rate: float
    most_common_reason: Optional[str] = None
    is_flagged: bool

class FlaggedPatternSchema(BaseModel):
    weekday: int
    weekday_name: str
    weekday_plural: str
    category: str
    category_display: str
    done: int
    skipped: int
    total: int
    skip_rate: float
    confidence: float
    most_common_reason: Optional[str] = None
    message: str

class PatternsResponseSchema(BaseModel):
    flagged_patterns: List[FlaggedPatternSchema]
    matrix: List[PatternCellSchema]
    summary: dict

# --- Route Implementations ---

def get_current_user(db: Session = Depends(get_db)) -> User:
    """Helper to return the single owner user."""
    owner_id = settings.TELEGRAM_OWNER_ID
    if owner_id == "your_telegram_id_here":
        owner_id = "123456789"
    user = db.query(User).filter(User.telegram_id == str(owner_id)).first()
    if not user:
        # Auto-create if database was not initialized
        user = User(
            name="User",
            telegram_id=str(owner_id),
            timezone=settings.TIMEZONE,
            wake_time="07:00:00",
            sleep_time="23:00:00"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

@router.get("/user", response_model=UserSchema)
def get_user_profile(user: User = Depends(get_current_user)):
    return user

@router.put("/user", response_model=UserSchema)
def update_user_profile(
    data: UserUpdateSchema,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if data.name is not None:
        user.name = data.name
    if data.wake_time is not None:
        user.wake_time = data.wake_time
    if data.sleep_time is not None:
        user.sleep_time = data.sleep_time
        
    db.commit()
    db.refresh(user)
    return user

@router.get("/schedule/date/{date_str}", response_model=DailyScheduleSchema)
def get_schedule_by_date(
    date_str: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
    sched = db.query(DailySchedule).filter(
        DailySchedule.user_id == user.id,
        DailySchedule.date == target_date
    ).first()
    
    if not sched:
        # Auto-generate on-demand
        sched = generate_daily_schedule(db, user.id, target_date)
        
    active_version = db.query(ScheduleVersion).filter(
        ScheduleVersion.daily_schedule_id == sched.id,
        ScheduleVersion.is_active == True
    ).first()
    
    blocks = []
    if active_version:
        blocks = db.query(ScheduleBlock).filter(
            ScheduleBlock.schedule_version_id == active_version.id
        ).order_by(ScheduleBlock.planned_start).all()
        
    return {
        "id": sched.id,
        "date": sched.date.strftime("%Y-%m-%d"),
        "user_id": sched.user_id,
        "energy_score": sched.energy_score,
        "is_locked": sched.is_locked,
        "blocks": blocks
    }

@router.post("/schedule/date/{date_str}/energy")
def set_schedule_energy(
    date_str: str,
    score: int = Query(..., ge=1, le=5),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
    sched = db.query(DailySchedule).filter(
        DailySchedule.user_id == user.id,
        DailySchedule.date == target_date
    ).first()
    
    if not sched:
        sched = generate_daily_schedule(db, user.id, target_date)
        
    sched.energy_score = score
    db.commit()
    return {"status": "success", "energy_score": score}


@router.post("/schedule/generate", response_model=DailyScheduleSchema)
def force_generate_schedule(
    date_str: str = Query(..., description="YYYY-MM-DD date to generate"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
    sched = generate_daily_schedule(db, user.id, target_date)
    
    active_version = db.query(ScheduleVersion).filter(
        ScheduleVersion.daily_schedule_id == sched.id,
        ScheduleVersion.is_active == True
    ).first()
    
    blocks = []
    if active_version:
        blocks = active_version.blocks
        
    return {
        "id": sched.id,
        "date": sched.date.strftime("%Y-%m-%d"),
        "user_id": sched.user_id,
        "energy_score": sched.energy_score,
        "is_locked": sched.is_locked,
        "blocks": blocks
    }

@router.post("/schedule/block/{block_id}/status", response_model=ScheduleBlockSchema)
def update_block_status(
    block_id: int,
    data: BlockStatusUpdateSchema,
    db: Session = Depends(get_db)
):
    block = db.query(ScheduleBlock).filter(ScheduleBlock.id == block_id).first()
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")
        
    block.status = data.status
    if data.status == "completed":
        block.actual_end = datetime.datetime.now().strftime("%H:%M:%S")
        block.reason = None
    elif data.status == "skipped":
        block.reason = data.reason or "No reason provided"
        
    db.commit()
    db.refresh(block)
    return block

@router.get("/deadlines", response_model=List[DeadlineSchema])
def get_deadlines(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Deadline).filter(Deadline.user_id == user.id).order_by(Deadline.due_datetime.asc()).all()

@router.post("/deadlines", response_model=DeadlineSchema)
def create_deadline(
    data: DeadlineCreateSchema,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    deadline = Deadline(
        user_id=user.id,
        title=data.title,
        client_name=data.client_name,
        estimated_minutes=data.estimated_minutes,
        due_datetime=data.due_datetime,
        priority=data.priority,
        status="pending"
    )
    db.add(deadline)
    db.commit()
    db.refresh(deadline)
    return deadline

@router.delete("/deadlines/{deadline_id}")
def delete_deadline(
    deadline_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    deadline = db.query(Deadline).filter(Deadline.id == deadline_id, Deadline.user_id == user.id).first()
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")
    db.delete(deadline)
    db.commit()
    return {"message": "Deadline deleted successfully"}

@router.get("/goals", response_model=List[RecurringGoalSchema])
def get_goals(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(RecurringGoal).filter(RecurringGoal.user_id == user.id).all()

@router.put("/goals", response_model=List[RecurringGoalSchema])
def update_goal_ratios(
    data: GoalUpdateListSchema,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify ratios add up to 1.0
    total_ratio = sum(item.get("ratio", 0) for item in data.ratios)
    if abs(total_ratio - 1.0) > 0.01:
        raise HTTPException(status_code=400, detail="Goal ratios must sum up to exactly 1.0 (100%)")
        
    for item in data.ratios:
        g_id = item.get("id")
        ratio = item.get("ratio")
        goal = db.query(RecurringGoal).filter(RecurringGoal.id == g_id, RecurringGoal.user_id == user.id).first()
        if goal:
            goal.ratio = ratio
            
    db.commit()
    return db.query(RecurringGoal).filter(RecurringGoal.user_id == user.id).all()

@router.get("/inbox", response_model=List[InboxItemSchema])
def get_inbox_items(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(InboxItem).filter(
        InboxItem.user_id == user.id,
        InboxItem.status != "archived"
    ).order_by(InboxItem.created_at.desc()).all()

@router.post("/inbox", response_model=InboxItemSchema)
def create_inbox_item(
    data: InboxCreateSchema,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    item = InboxItem(
        user_id=user.id,
        title=data.title,
        description=data.description,
        source=data.source,
        priority=data.priority,
        suggested_type=data.suggested_type,
        status="active"
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@router.put("/inbox/{item_id}", response_model=InboxItemSchema)
def update_inbox_item_status(
    item_id: int,
    status: str = Query(..., description="active, scheduled, archived"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    item = db.query(InboxItem).filter(InboxItem.id == item_id, InboxItem.user_id == user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inbox item not found")
        
    item.status = status
    db.commit()
    db.refresh(item)
    return item

@router.get("/analytics")
def get_analytics(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Get stats for the last 7 days ending today
    return get_weekly_stats(db, user.id)

@router.get("/patterns", response_model=PatternsResponseSchema)
def get_patterns(
    days: int = Query(28, description="Number of days to analyze (default 28)"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from app.analytics.patterns import detect_patterns, save_detected_patterns
    result = detect_patterns(db, user.id, days_back=days)
    if result.get("flagged_patterns"):
        save_detected_patterns(db, user.id, result["flagged_patterns"])
    return result

@router.get("/coach/chat", response_model=CoachChatSchema)
def get_coach_context(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Load profile keys
    profiles = db.query(MemoryProfile).filter(MemoryProfile.user_id == user.id).all()
    beliefs = db.query(MemoryBelief).filter(MemoryBelief.user_id == user.id, MemoryBelief.status == "active").all()
    goals = db.query(MemoryGoal).filter(MemoryGoal.user_id == user.id, MemoryGoal.status == "active").all()
    
    return {
        "profile": [{"key": p.key, "value": p.value} for p in profiles],
        "beliefs": [b.belief for b in beliefs],
        "goals": [{"goal": g.goal, "priority": g.priority, "deadline": g.deadline} for g in goals]
    }

@router.post("/coach/message")
def send_coach_message(
    data: MessageSchema,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Route manual text thread to Claude Coach night 리뷰 code.
    # Simulates the Telegram chat from the frontend dashboard UI!
    chat_state_rec = db.query(MemoryProfile).filter(
        MemoryProfile.user_id == user.id,
        MemoryProfile.key == "chat_state"
    ).first()
    
    # Check if there is an active negotiating daily schedule, else default to tomorrow's schedule id
    tomorrow_date = datetime.date.today() + datetime.timedelta(days=1)
    tomorrow_sched = db.query(DailySchedule).filter(
        DailySchedule.user_id == user.id,
        DailySchedule.date == tomorrow_date
    ).first()
    if not tomorrow_sched:
        tomorrow_sched = generate_daily_schedule(db, user.id, tomorrow_date)
        
    result = run_night_negotiation(db, user.id, data.message, chat_history=[])
    
    return result
