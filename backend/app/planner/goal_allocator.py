from typing import List, Tuple, Dict, Any
from app.planner.allocator import allocate_task
from app.planner.free_slots import minutes_to_time

def allocate_goals(
    free_slots: List[Tuple[int, int]],
    goals: List[Any]
) -> Tuple[List[Dict[str, Any]], List[Tuple[int, int]]]:
    """
    Splits remaining free minutes among recurring goals based on their ratios.
    
    Args:
        free_slots: Leftover free slots after fixed blocks and deadlines.
        goals: List of RecurringGoal SQLAlchemy models.
        
    Returns: (scheduled_blocks, remaining_free_slots)
    """
    scheduled_blocks = []
    current_free_slots = free_slots.copy()
    
    total_free_minutes = sum(end - start for start, end in current_free_slots)
    if total_free_minutes <= 0 or not goals:
        return [], current_free_slots
        
    # Sort goals by priority DESC (highest importance first)
    sorted_goals = sorted(goals, key=lambda x: x.priority, reverse=True)
    
    # Calculate target minutes for each goal based on ratios
    # Keep track of remaining minutes to handle rounding
    minutes_left_to_allocate = total_free_minutes
    goal_allocations = []
    
    for i, goal in enumerate(sorted_goals):
        if i == len(sorted_goals) - 1:
            # Last goal gets whatever is left to prevent rounding leak
            target_min = minutes_left_to_allocate
        else:
            target_min = int(total_free_minutes * goal.ratio)
            target_min = min(target_min, minutes_left_to_allocate)
            
        minutes_left_to_allocate -= target_min
        goal_allocations.append((goal, target_min))
        
    # Allocate blocks for each goal
    for goal, target_min in goal_allocations:
        if target_min < 15:
            # Avoid scheduling blocks too small to be productive (e.g. < 15 mins)
            continue
            
        allocated_chunks, updated_free = allocate_task(
            current_free_slots,
            target_min,
            allow_split=True
        )
        
        if not allocated_chunks:
            continue
            
        current_free_slots = updated_free
        
        num_chunks = len(allocated_chunks)
        for idx, (start_min, end_min) in enumerate(allocated_chunks):
            chunk_title = goal.name
            if num_chunks > 1:
                chunk_title = f"{goal.name} (Part {idx+1})"
                
            block = {
                "title": chunk_title,
                "type": goal.name.lower().replace(" practice", "").replace(" ", "_"), # 'agency', 'dsa', etc.
                "source": f"goal:{goal.id}",
                "priority": goal.priority,
                "planned_start": minutes_to_time(start_min),
                "planned_end": minutes_to_time(end_min),
                "status": "pending"
            }
            scheduled_blocks.append(block)
            
    return scheduled_blocks, current_free_slots
