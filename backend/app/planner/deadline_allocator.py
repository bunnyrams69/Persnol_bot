from typing import List, Tuple, Dict, Any
from app.planner.allocator import allocate_task
from app.planner.free_slots import minutes_to_time

def allocate_deadlines(
    free_slots: List[Tuple[int, int]],
    deadlines: List[Any]  # List of Deadline SQLAlchemy models or dicts
) -> Tuple[List[Dict[str, Any]], List[Tuple[int, int]]]:
    """
    Allocates deadlines sorted by:
    1. due_datetime ASC
    2. priority DESC
    3. estimated_minutes DESC
    
    Returns: (scheduled_blocks, remaining_free_slots)
    """
    scheduled_blocks = []
    current_free_slots = free_slots.copy()
    
    for deadline in deadlines:
        duration = deadline.estimated_minutes
        title = deadline.title
        priority = deadline.priority
        
        # Allocate task minutes using allocator (allows split if needed)
        allocated_chunks, updated_free = allocate_task(
            current_free_slots,
            duration,
            allow_split=True
        )
        
        if not allocated_chunks:
            # Couldn't schedule it (out of time in the day)
            continue
            
        current_free_slots = updated_free
        
        num_chunks = len(allocated_chunks)
        for i, (start_min, end_min) in enumerate(allocated_chunks):
            # If split, append (Part X) to title
            chunk_title = title
            if num_chunks > 1:
                chunk_title = f"{title} (Part {i+1})"
                
            block = {
                "title": chunk_title,
                "type": "deadline",
                "source": getattr(deadline, "source", f"deadline:{deadline.id}"),
                "priority": priority,
                "planned_start": minutes_to_time(start_min),
                "planned_end": minutes_to_time(end_min),
                "status": "pending"
            }
            scheduled_blocks.append(block)
            
    return scheduled_blocks, current_free_slots
