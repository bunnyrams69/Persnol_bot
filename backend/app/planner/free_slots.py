from typing import List, Tuple

def time_to_minutes(time_str: str) -> int:
    """Convert 'HH:MM:SS' or 'HH:MM' string to minutes since midnight."""
    parts = time_str.split(":")
    hours = int(parts[0])
    minutes = int(parts[1])
    return hours * 60 + minutes

def minutes_to_time(minutes: int) -> str:
    """Convert minutes since midnight back to 'HH:MM:SS' format."""
    hours = (minutes // 60) % 24
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}:00"

def get_free_slots(
    wake_time_str: str,
    sleep_time_str: str,
    fixed_blocks: List[Tuple[str, str]]
) -> List[Tuple[int, int]]:
    """
    Computes a list of free time slots (start_minutes, end_minutes) within the
    wake-sleep window after subtracting the given fixed blocks.
    
    Args:
        wake_time_str: User wake time (e.g. "07:00:00")
        sleep_time_str: User sleep time (e.g. "23:00:00")
        fixed_blocks: List of (start_time, end_time) tuples for fixed blocks.
    """
    wake_min = time_to_minutes(wake_time_str)
    sleep_min = time_to_minutes(sleep_time_str)
    
    # If sleep_time is past midnight (e.g., 01:00 AM)
    if sleep_min < wake_min:
        sleep_min += 24 * 60
        
    free_slots = [(wake_min, sleep_min)]
    
    for start_str, end_str in fixed_blocks:
        b_start = time_to_minutes(start_str)
        b_end = time_to_minutes(end_str)
        
        # Adjust block time if it overlaps midnight and fits user's late schedule
        if b_end < b_start:
            b_end += 24 * 60
            
        new_slots = []
        for s_start, s_end in free_slots:
            # No overlap
            if b_end <= s_start or b_start >= s_end:
                new_slots.append((s_start, s_end))
            # Block completely covers slot
            elif b_start <= s_start and b_end >= s_end:
                continue
            # Block splits slot in middle
            elif b_start > s_start and b_end < s_end:
                new_slots.append((s_start, b_start))
                new_slots.append((b_end, s_end))
            # Block overlaps starting edge
            elif b_start <= s_start and b_end < s_end:
                new_slots.append((b_end, s_end))
            # Block overlaps ending edge
            elif b_start > s_start and b_end >= s_end:
                new_slots.append((s_start, b_start))
        
        free_slots = new_slots
        
    # Sort slots and filter out any slot smaller than 5 minutes
    free_slots = sorted([s for s in free_slots if (s[1] - s[0]) >= 5], key=lambda x: x[0])
    return free_slots
