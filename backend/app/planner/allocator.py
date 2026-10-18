from typing import List, Tuple

def allocate_task_contiguous(
    free_slots: List[Tuple[int, int]],
    duration: int
) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
    """
    Attempts to allocate a duration contiguously inside the first available free slot.
    Returns: (allocated_slots, remaining_free_slots)
    """
    updated_slots = []
    allocated = []
    done = False
    
    for start, end in free_slots:
        if not done and (end - start) >= duration:
            # We found a contiguous slot! Allocate from the start of it
            allocated.append((start, start + duration))
            if (end - (start + duration)) >= 5:
                # Keep the remainder of this slot if it's at least 5 minutes
                updated_slots.append((start + duration, end))
            done = True
        else:
            updated_slots.append((start, end))
            
    return allocated, sorted(updated_slots, key=lambda x: x[0])

def allocate_task(
    free_slots: List[Tuple[int, int]],
    duration: int,
    allow_split: bool = True
) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
    """
    Allocates a task of a certain duration (in minutes).
    Attempts contiguous allocation first. If not possible and allow_split is True,
    it splits the task across the largest available free slots.
    
    Returns: (allocated_slots, remaining_free_slots)
    """
    # 1. Try to schedule contiguously
    allocated, remaining = allocate_task_contiguous(free_slots, duration)
    if allocated:
        return allocated, remaining
        
    # 2. If we couldn't schedule contiguously and splitting is allowed, fill slots
    if not allow_split:
        return [], free_slots
        
    allocated = []
    remaining_duration = duration
    
    # Sort free slots by size DESC to fill the largest ones first
    sorted_by_size = sorted(free_slots, key=lambda x: (x[1] - x[0]), reverse=True)
    temp_remaining_slots = []
    
    for start, end in sorted_by_size:
        if remaining_duration <= 0:
            temp_remaining_slots.append((start, end))
            continue
            
        slot_size = end - start
        if slot_size <= remaining_duration:
            # Consume this slot completely
            allocated.append((start, end))
            remaining_duration -= slot_size
        else:
            # Consume part of this slot
            allocated.append((start, start + remaining_duration))
            if (end - (start + remaining_duration)) >= 5:
                temp_remaining_slots.append((start + remaining_duration, end))
            remaining_duration = 0
            
    # Re-sort remaining slots chronologically
    final_free_slots = sorted(temp_remaining_slots, key=lambda x: x[0])
    # Re-sort allocated blocks chronologically
    allocated = sorted(allocated, key=lambda x: x[0])
    
    return allocated, final_free_slots
