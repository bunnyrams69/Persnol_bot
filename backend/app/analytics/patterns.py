import datetime
import logging
from collections import Counter
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.database.models import DailySchedule, ScheduleVersion, ScheduleBlock, MemoryPattern

logger = logging.getLogger("life_os.analytics.patterns")

CATEGORIES = ["gym", "agency", "dsa", "deadline"]

CATEGORY_DISPLAY = {
    "gym": "Gym",
    "agency": "AI Agency",
    "dsa": "DSA",
    "deadline": "Deadline"
}

WEEKDAY_NAMES = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
]

WEEKDAY_PLURALS = [
    "Mondays", "Tuesdays", "Wednesdays", "Thursdays", "Fridays", "Saturdays", "Sundays"
]

WEEKDAY_SHORTS = [
    "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"
]


def normalize_category(b_type: str, b_title: str = "") -> Optional[str]:
    """
    Normalizes a block's type and title into one of the 4 core categories:
    gym, agency, dsa, deadline. Returns None if it doesn't match.
    """
    t = (b_type or "").lower().strip()
    title = (b_title or "").lower().strip()

    if "dsa" in t or "dsa" in title:
        return "dsa"
    if "agency" in t or "agency" in title:
        return "agency"
    if "gym" in t or "gym" in title:
        return "gym"
    if "deadline" in t or "client" in title or "reel" in title:
        return "deadline"

    return None


def calculate_confidence(total_samples: int) -> float:
    """
    Calculates detection confidence rising with sample size.
    Requires at least 3 samples:
      total = 3  -> 0.59
      total = 4  -> 0.68
      total = 5  -> 0.77
      total = 6  -> 0.86
      total >= 7 -> 0.95 (capped)
    """
    if total_samples < 3:
        return 0.0
    return round(min(0.95, 0.50 + (total_samples - 2) * 0.09), 2)


def build_pattern_message(category: str, skipped: int, total: int, weekday_idx: int, most_common_reason: Optional[str]) -> str:
    """
    Builds a plain-English pattern message like:
    'DSA skipped 4 of 5 Wednesdays (most common reason: Tired)'
    """
    cat_name = "DSA" if category == "dsa" else CATEGORY_DISPLAY.get(category, category.title())
    weekday_plural = WEEKDAY_PLURALS[weekday_idx]

    if most_common_reason:
        return f"{cat_name} skipped {skipped} of {total} {weekday_plural} (most common reason: {most_common_reason})"
    return f"{cat_name} skipped {skipped} of {total} {weekday_plural}"


def detect_patterns_from_block_list(
    blocks_data: List[Dict[str, Any]],
    date_limit: Optional[datetime.date] = None,
    days_back: int = 28
) -> Dict[str, Any]:
    """
    Pure deterministic pattern detector on a list of raw block dicts.
    Each block dict should contain:
      - 'date': datetime.date (or str 'YYYY-MM-DD')
      - 'type': str
      - 'title': str (optional)
      - 'status': 'completed' | 'skipped' | 'pending'
      - 'reason': str (optional)
    """
    if date_limit is None:
        date_limit = datetime.date.today()
    start_date = date_limit - datetime.timedelta(days=days_back - 1)

    # Initialize stats accumulator: stats[weekday][category]
    # weekday: 0..6
    cell_stats = {
        w: {
            c: {
                "done": 0,
                "skipped": 0,
                "reasons": []
            }
            for c in CATEGORIES
        }
        for w in range(7)
    }

    total_blocks_counted = 0
    total_completed = 0
    total_skipped = 0

    for item in blocks_data:
        block_date = item.get("date")
        if isinstance(block_date, str):
            block_date = datetime.date.fromisoformat(block_date)

        if not (start_date <= block_date <= date_limit):
            continue

        cat = normalize_category(item.get("type", ""), item.get("title", ""))
        if not cat:
            continue

        status = item.get("status")
        weekday = block_date.weekday()

        if status == "completed":
            cell_stats[weekday][cat]["done"] += 1
            total_blocks_counted += 1
            total_completed += 1
        elif status == "skipped":
            cell_stats[weekday][cat]["skipped"] += 1
            reason = item.get("reason")
            if reason and str(reason).strip():
                cell_stats[weekday][cat]["reasons"].append(str(reason).strip())
            total_blocks_counted += 1
            total_skipped += 1

    flagged_patterns = []
    matrix = []

    for w in range(7):
        for c in CATEGORIES:
            data = cell_stats[w][c]
            done = data["done"]
            skipped = data["skipped"]
            total = done + skipped
            skip_rate = round(skipped / total, 2) if total > 0 else 0.0

            # Find most common reason
            most_common_reason = None
            if data["reasons"]:
                counts = Counter(data["reasons"])
                most_common_reason = counts.most_common(1)[0][0]

            # Flag condition: >= 3 samples and skip rate >= 60%
            is_flagged = (total >= 3 and skip_rate >= 0.60)
            conf = calculate_confidence(total) if is_flagged else 0.0
            msg = build_pattern_message(c, skipped, total, w, most_common_reason) if is_flagged else ""

            cell = {
                "weekday": w,
                "weekday_name": WEEKDAY_NAMES[w],
                "weekday_short": WEEKDAY_SHORTS[w],
                "category": c,
                "category_display": CATEGORY_DISPLAY[c],
                "done": done,
                "skipped": skipped,
                "total": total,
                "skip_rate": skip_rate,
                "most_common_reason": most_common_reason,
                "is_flagged": is_flagged,
            }
            matrix.append(cell)

            if is_flagged:
                flagged_patterns.append({
                    "weekday": w,
                    "weekday_name": WEEKDAY_NAMES[w],
                    "weekday_plural": WEEKDAY_PLURALS[w],
                    "category": c,
                    "category_display": CATEGORY_DISPLAY[c],
                    "done": done,
                    "skipped": skipped,
                    "total": total,
                    "skip_rate": skip_rate,
                    "confidence": conf,
                    "most_common_reason": most_common_reason,
                    "message": msg,
                })

    # Sort flagged patterns by skip_rate descending, then total descending
    flagged_patterns.sort(key=lambda p: (p["skip_rate"], p["total"]), reverse=True)

    return {
        "flagged_patterns": flagged_patterns,
        "matrix": matrix,
        "summary": {
            "total_blocks": total_blocks_counted,
            "total_completed": total_completed,
            "total_skipped": total_skipped,
            "flagged_count": len(flagged_patterns),
            "date_range": {
                "start": start_date.strftime("%Y-%m-%d"),
                "end": date_limit.strftime("%Y-%m-%d"),
                "days": days_back
            }
        }
    }


def detect_patterns(
    db: Session,
    user_id: int,
    date_limit: Optional[datetime.date] = None,
    days_back: int = 28
) -> Dict[str, Any]:
    """
    Loads the last 28 days of daily schedule blocks for a user and runs
    deterministic pattern detection.
    """
    if date_limit is None:
        date_limit = datetime.date.today()
    start_date = date_limit - datetime.timedelta(days=days_back - 1)

    schedules = db.query(DailySchedule).filter(
        DailySchedule.user_id == user_id,
        DailySchedule.date >= start_date,
        DailySchedule.date <= date_limit
    ).all()

    blocks_data: List[Dict[str, Any]] = []

    for sched in schedules:
        active_version = db.query(ScheduleVersion).filter(
            ScheduleVersion.daily_schedule_id == sched.id,
            ScheduleVersion.is_active == True
        ).first()

        if not active_version:
            continue

        for b in active_version.blocks:
            blocks_data.append({
                "date": sched.date,
                "type": b.type,
                "title": b.title,
                "status": b.status,
                "reason": b.reason,
            })

    return detect_patterns_from_block_list(blocks_data, date_limit=date_limit, days_back=days_back)


def save_detected_patterns(db: Session, user_id: int, flagged_patterns: List[Dict[str, Any]]) -> List[MemoryPattern]:
    """
    Saves or updates flagged patterns into MemoryPattern without creating duplicates.
    Matches existing rows using the evidence metadata tag (weekday + category).
    """
    saved_records = []

    for pat in flagged_patterns:
        w = pat["weekday"]
        cat = pat["category"]
        tag_prefix = f"tag:detector|weekday:{w}|category:{cat}"
        evidence_str = (
            f"{tag_prefix}|skipped:{pat['skipped']}|total:{pat['total']}"
            f"|rate:{int(pat['skip_rate'] * 100)}%|reason:{pat['most_common_reason'] or 'None'}"
        )

        # Look for existing record by tag or weekday+category match
        existing = db.query(MemoryPattern).filter(
            MemoryPattern.user_id == user_id
        ).all()

        match = None
        for rec in existing:
            if rec.evidence and tag_prefix in rec.evidence:
                match = rec
                break
            # Fallback check against pattern message if tag wasn't set yet
            if not match and f"{pat['category_display']} skipped" in rec.pattern and pat["weekday_plural"] in rec.pattern:
                match = rec
                break

        if match:
            match.pattern = pat["message"]
            match.confidence = pat["confidence"]
            match.evidence = evidence_str
            match.updated_at = datetime.datetime.utcnow()
            saved_records.append(match)
        else:
            new_pattern = MemoryPattern(
                user_id=user_id,
                pattern=pat["message"],
                confidence=pat["confidence"],
                evidence=evidence_str,
                created_at=datetime.datetime.utcnow(),
                updated_at=datetime.datetime.utcnow()
            )
            db.add(new_pattern)
            saved_records.append(new_pattern)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving detected patterns to MemoryPattern: {e}")
        raise e

    return saved_records
