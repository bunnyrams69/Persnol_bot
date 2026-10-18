import datetime
from typing import Union, List
from sqlalchemy.orm import Session

from app.database.models import User, FixedBlock, Deadline, RecurringGoal, DailySchedule, ScheduleVersion, ScheduleBlock, InboxItem
from app.planner.free_slots import get_free_slots, time_to_minutes, minutes_to_time

class TaskToSchedule:
    def __init__(self, id: int, title: str, estimated_minutes: int, priority: int, due_datetime: datetime.datetime, source: str):
        self.id = id
        self.title = title
        self.estimated_minutes = estimated_minutes
        self.priority = priority
        self.due_datetime = due_datetime
        self.source = source

from app.planner.deadline_allocator import allocate_deadlines
from app.planner.goal_allocator import allocate_goals

def generate_daily_schedule(
    db: Session,
    user_id: int,
    target_date: Union[datetime.date, str]
) -> DailySchedule:
    """
    Generates a deterministic schedule for a specific date and user.
    Creates a new Version of the schedule.
    """
    if isinstance(target_date, str):
        target_date = datetime.datetime.strptime(target_date, "%Y-%m-%d").date()
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User with ID {user_id} not found.")
        
    # 1. Fetch fixed blocks active on target_date's day of week
    weekday = target_date.weekday()  # 0 = Monday, ..., 6 = Sunday
    
    day_attributes = [
        FixedBlock.monday,
        FixedBlock.tuesday,
        FixedBlock.wednesday,
        FixedBlock.thursday,
        FixedBlock.friday,
        FixedBlock.saturday,
        FixedBlock.sunday
    ]
    
    active_fixed_blocks = db.query(FixedBlock).filter(
        FixedBlock.user_id == user_id,
        day_attributes[weekday] == True
    ).all()
    
    # 2. Extract fixed block time slots for free slot calculator
    fixed_slots = []
    fixed_schedule_blocks = []
    
    for fb in active_fixed_blocks:
        fixed_slots.append((fb.start_time, fb.end_time))
        
        # Add to schedule blocks
        # Determine block type from title or name
        b_type = "college" if "college" in fb.title.lower() else "gym" if "gym" in fb.title.lower() else "break" if "lunch" in fb.title.lower() or "travel" in fb.title.lower() else "custom"
        fixed_schedule_blocks.append({
            "title": fb.title,
            "type": b_type,
            "source": f"fixed:{fb.id}",
            "priority": fb.priority,
            "planned_start": fb.start_time,
            "planned_end": fb.end_time,
            "status": "pending"
        })
        
    # 3. Calculate initial free slots
    free_slots = get_free_slots(user.wake_time, user.sleep_time, fixed_slots)
    
    # 4. Fetch pending deadlines and scheduled inbox items
    deadlines = db.query(Deadline).filter(
        Deadline.user_id == user_id,
        Deadline.status == "pending",
        Deadline.due_datetime >= datetime.datetime.combine(target_date, datetime.time.min)
    ).all()
    
    scheduled_inbox = db.query(InboxItem).filter(
        InboxItem.user_id == user_id,
        InboxItem.status == "scheduled"
    ).all()
    
    # Map to unified TaskToSchedule list
    tasks = []
    for d in deadlines:
        tasks.append(TaskToSchedule(
            id=d.id,
            title=d.title,
            estimated_minutes=d.estimated_minutes,
            priority=d.priority,
            due_datetime=d.due_datetime,
            source=f"deadline:{d.id}"
        ))
        
    priority_map = {"urgent": 5, "high": 4, "medium": 3, "low": 2}
    for item in scheduled_inbox:
        tasks.append(TaskToSchedule(
            id=item.id,
            title=item.title,
            estimated_minutes=60,  # Default to 60 min blocks for raw inbox items
            priority=priority_map.get(item.priority, 3),
            due_datetime=datetime.datetime.combine(target_date, datetime.time.max),
            source=f"inbox:{item.id}"
        ))
        
    # Sort unified tasks by due date (closest first), priority (highest first), and duration (longest first)
    tasks = sorted(tasks, key=lambda x: (x.due_datetime, -x.priority, -x.estimated_minutes))
    
    deadline_blocks, remaining_slots = allocate_deadlines(free_slots, tasks)
    
    # 5. Fetch recurring goals
    goals = db.query(RecurringGoal).filter(RecurringGoal.user_id == user_id).all()
    goal_blocks, remaining_slots = allocate_goals(remaining_slots, goals)
    
    # 6. Fill any remaining gaps (> 5 minutes) as breaks
    break_blocks = []
    for start, end in remaining_slots:
        if (end - start) >= 5:
            break_blocks.append({
                "title": "☕ Break",
                "type": "break",
                "source": "break",
                "priority": 1,
                "planned_start": minutes_to_time(start),
                "planned_end": minutes_to_time(end),
                "status": "pending"
            })
            
    # Combine all blocks
    all_blocks = fixed_schedule_blocks + deadline_blocks + goal_blocks + break_blocks
    
    # Sort blocks chronologically
    all_blocks = sorted(all_blocks, key=lambda x: time_to_minutes(x["planned_start"]))
    
    # 7. Write to database
    # Check if daily schedule exists for this date
    daily_schedule = db.query(DailySchedule).filter(
        DailySchedule.user_id == user_id,
        DailySchedule.date == target_date
    ).first()
    
    if not daily_schedule:
        daily_schedule = DailySchedule(
            date=target_date,
            user_id=user_id,
            is_locked=False
        )
        db.add(daily_schedule)
        db.commit()
        db.refresh(daily_schedule)
        version_num = 1
    else:
        # Find latest version and increment
        latest_version = db.query(ScheduleVersion).filter(
            ScheduleVersion.daily_schedule_id == daily_schedule.id
        ).order_by(ScheduleVersion.version.desc()).first()
        
        version_num = (latest_version.version + 1) if latest_version else 1
        
        # Deactivate all existing versions
        db.query(ScheduleVersion).filter(
            ScheduleVersion.daily_schedule_id == daily_schedule.id
        ).update({"is_active": False})
        db.commit()
        
    # Create new ScheduleVersion
    schedule_version = ScheduleVersion(
        daily_schedule_id=daily_schedule.id,
        version=version_num,
        created_by="planner",
        notes=f"Auto-generated deterministic schedule (Version {version_num})",
        is_active=True
    )
    db.add(schedule_version)
    db.commit()
    db.refresh(schedule_version)
    
    # Add all schedule blocks
    for block_data in all_blocks:
        block = ScheduleBlock(
            schedule_version_id=schedule_version.id,
            title=block_data["title"],
            type=block_data["type"],
            source=block_data["source"],
            priority=block_data["priority"],
            planned_start=block_data["planned_start"],
            planned_end=block_data["planned_end"],
            status=block_data["status"]
        )
        db.add(block)
        
    db.commit()
    db.refresh(daily_schedule)
    
    return daily_schedule


def apply_negotiated_changes(
    db: Session,
    daily_schedule_id: int,
    actions: List[dict]
) -> ScheduleVersion:
    """
    Applies Claude's negotiated schedule modifications to create a new ScheduleVersion.
    Validates changes to ensure they do not collide with locked fixed blocks.
    """
    # 1. Fetch current active version
    active_version = db.query(ScheduleVersion).filter(
        ScheduleVersion.daily_schedule_id == daily_schedule_id,
        ScheduleVersion.is_active == True
    ).first()
    
    if not active_version:
        raise ValueError(f"No active schedule version found for DailySchedule ID {daily_schedule_id}.")
        
    daily_schedule = db.query(DailySchedule).filter(DailySchedule.id == daily_schedule_id).first()
    user_id = daily_schedule.user_id
    
    # 2. Get active fixed blocks for target weekday to validate collisions
    weekday = daily_schedule.date.weekday()
    day_attributes = [
        FixedBlock.monday,
        FixedBlock.tuesday,
        FixedBlock.wednesday,
        FixedBlock.thursday,
        FixedBlock.friday,
        FixedBlock.saturday,
        FixedBlock.sunday
    ]
    active_fixed_blocks = db.query(FixedBlock).filter(
        FixedBlock.user_id == user_id,
        day_attributes[weekday] == True
    ).all()
    
    # 3. Create mutable copy of existing blocks
    blocks_copy = []
    for b in active_version.blocks:
        blocks_copy.append({
            "title": b.title,
            "type": b.type,
            "source": b.source,
            "priority": b.priority,
            "planned_start": b.planned_start,
            "planned_end": b.planned_end,
            "status": b.status,
            "actual_start": b.actual_start,
            "actual_end": b.actual_end,
            "reason": b.reason
        })
        
    # 4. Apply each negotiated action
    for action in actions:
        action_type = action.get("action")
        block_title = action.get("block_title")
        planned_start = action.get("planned_start")
        planned_end = action.get("planned_end")
        
        if not action_type or not block_title or not planned_start or not planned_end:
            raise ValueError("Invalid negotiation action. Must specify action, block_title, planned_start, planned_end.")
            
        if action_type == "move":
            # Find the block (by title or partial match)
            block = next((b for b in blocks_copy if b["title"].lower() == block_title.lower() or block_title.lower() in b["title"].lower()), None)
            if not block:
                raise ValueError(f"Block '{block_title}' not found in tomorrow's schedule.")
                
            # If the block is a fixed block, it cannot be moved
            if "fixed:" in block["source"]:
                raise ValueError(f"Block '{block_title}' is a locked Fixed Block and cannot be rescheduled.")
                
            # Validate collisions with locked fixed blocks
            proposed_start_min = time_to_minutes(planned_start)
            proposed_end_min = time_to_minutes(planned_end)
            
            for fb in active_fixed_blocks:
                fb_start_min = time_to_minutes(fb.start_time)
                fb_end_min = time_to_minutes(fb.end_time)
                
                # Check intersection: startA < endB and endA > startB
                if proposed_start_min < fb_end_min and proposed_end_min > fb_start_min:
                    raise ValueError(
                        f"Collision: Rescheduling '{block_title}' to {planned_start}-{planned_end} "
                        f"overlaps with locked Fixed Block '{fb.title}' ({fb.start_time}-{fb.end_time})."
                    )
            
            # Apply time change
            block["planned_start"] = planned_start
            block["planned_end"] = planned_end
            
    # 5. Create new ScheduleVersion incrementing the counter
    new_version_num = active_version.version + 1
    
    # Deactivate all existing versions
    db.query(ScheduleVersion).filter(
        ScheduleVersion.daily_schedule_id == daily_schedule_id
    ).update({"is_active": False})
    db.commit()
    
    # Insert new active version
    new_version = ScheduleVersion(
        daily_schedule_id=daily_schedule_id,
        version=new_version_num,
        created_by="claude",
        notes=f"Negotiated adjustments applied (Version {new_version_num})",
        is_active=True
    )
    db.add(new_version)
    db.commit()
    db.refresh(new_version)
    
    # Add all copied/modified blocks
    # Re-sort blocks chronologically first
    sorted_blocks = sorted(blocks_copy, key=lambda x: time_to_minutes(x["planned_start"]))
    for block_data in sorted_blocks:
        b = ScheduleBlock(
            schedule_version_id=new_version.id,
            title=block_data["title"],
            type=block_data["type"],
            source=block_data["source"],
            priority=block_data["priority"],
            planned_start=block_data["planned_start"],
            planned_end=block_data["planned_end"],
            status=block_data["status"],
            actual_start=block_data["actual_start"],
            actual_end=block_data["actual_end"],
            reason=block_data["reason"]
        )
        db.add(b)
        
    db.commit()
    db.refresh(new_version)
    
    return new_version

