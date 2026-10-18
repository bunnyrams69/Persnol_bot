from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_energy_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for morning energy check-in."""
    keyboard = [
        [
            InlineKeyboardButton("1 🥱", callback_data="energy_1"),
            InlineKeyboardButton("2 💤", callback_data="energy_2"),
            InlineKeyboardButton("3 😐", callback_data="energy_3"),
            InlineKeyboardButton("4 ⚡", callback_data="energy_4"),
            InlineKeyboardButton("5 🚀", callback_data="energy_5"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_block_checkin_keyboard(block_id: int) -> InlineKeyboardMarkup:
    """Keyboard for checking if a schedule block was completed."""
    keyboard = [
        [
            InlineKeyboardButton("👍 Done", callback_data=f"block_done_{block_id}"),
            InlineKeyboardButton("👎 Not Done", callback_data=f"block_notdone_{block_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_skip_reason_keyboard(block_id: int) -> InlineKeyboardMarkup:
    """Keyboard for selecting skip reason."""
    reasons = [
        ("🥱 Too tired", "tired"),
        ("💼 Unexpected work", "work"),
        ("📐 Bad planning", "planning"),
        ("📱 Distraction", "distracted"),
        ("📉 Low motivation", "motivation"),
        ("❓ Other", "other")
    ]
    keyboard = []
    # Place 2 reasons per row
    for i in range(0, len(reasons), 2):
        row = [
            InlineKeyboardButton(reasons[i][0], callback_data=f"skip_{reasons[i][1]}_{block_id}"),
            InlineKeyboardButton(reasons[i+1][0], callback_data=f"skip_{reasons[i+1][1]}_{block_id}")
        ]
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

def get_schedule_approval_keyboard(schedule_id: int) -> InlineKeyboardMarkup:
    """Keyboard for 9:00 PM schedule approval/negotiation."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"sched_approve_{schedule_id}"),
            InlineKeyboardButton("💬 Negotiate", callback_data=f"sched_negotiate_{schedule_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_undo_inbox_keyboard(item_id: int) -> InlineKeyboardMarkup:
    """Keyboard with an Undo button for a newly captured inbox item."""
    keyboard = [
        [
            InlineKeyboardButton("↩️ Undo", callback_data=f"undo_inbox_{item_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

