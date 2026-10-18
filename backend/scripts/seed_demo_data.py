import sys
import argparse
import datetime
from pathlib import Path
from typing import List

# Ensure safe output encoding on Windows PowerShell/CMD
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add backend root to Python path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.database.connection import SessionLocal
from app.database.models import User, DailySchedule, ScheduleVersion, ScheduleBlock, MemoryPattern
from app.analytics.patterns import detect_patterns, save_detected_patterns

DEMO_MARKER = "demo"


def reset_demo_data(db, user_id: int):
    """
    Safely removes only demo rows (blocks marked with source='demo',
    versions marked with created_by='demo', and demo memory pattern tags).
    Your real data is completely untouched.
    """
    print("[RESET] Cleaning up existing demo data...")

    # 1. Delete demo schedule blocks
    demo_blocks = db.query(ScheduleBlock).filter(ScheduleBlock.source == DEMO_MARKER).all()
    demo_block_count = len(demo_blocks)
    for b in demo_blocks:
        db.delete(b)

    # 2. Delete demo schedule versions
    demo_versions = db.query(ScheduleVersion).filter(ScheduleVersion.created_by == DEMO_MARKER).all()
    demo_version_count = len(demo_versions)
    for v in demo_versions:
        db.delete(v)

    # 3. Clean up daily schedules that have no remaining versions
    empty_schedules = db.query(DailySchedule).filter(
        DailySchedule.user_id == user_id,
        ~DailySchedule.versions.any()
    ).all()
    for s in empty_schedules:
        db.delete(s)

    # 4. Remove demo detector patterns from memory
    demo_patterns = db.query(MemoryPattern).filter(
        MemoryPattern.user_id == user_id,
        MemoryPattern.evidence.like("%tag:detector%")
    ).all()
    for p in demo_patterns:
        db.delete(p)

    db.commit()
    print(f"[OK] Reset complete: Removed {demo_block_count} demo blocks, {demo_version_count} demo versions.")


def seed_demo_blocks(db, user_id: int, days_back: int = 28):
    """
    Inserts 4 weeks (28 days) of realistic daily logged blocks.
    Specific built-in patterns:
    1. DSA: Skipped most Wednesdays (4 of 4 skipped, primary reason: 'Tired').
    2. Agency: Skipped most Sundays (3 of 4 skipped, primary reason: 'Weekend burnout').
    3. Gym: High consistency (mostly completed, only 2 occasional misses).
    4. Deadlines: Client deliverables on Fridays (completed).
    """
    print(f"[SEED] Seeding {days_back} days of realistic activity logs for User #{user_id}...")

    # First ensure existing demo data is reset to avoid duplicates
    reset_demo_data(db, user_id)

    today = datetime.date.today()
    created_blocks_count = 0

    for day_offset in range(days_back, 0, -1):
        log_date = today - datetime.timedelta(days=day_offset)
        weekday = log_date.weekday()  # 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun

        # Find or create daily schedule
        daily_sched = db.query(DailySchedule).filter(
            DailySchedule.user_id == user_id,
            DailySchedule.date == log_date
        ).first()

        if not daily_sched:
            daily_sched = DailySchedule(
                user_id=user_id,
                date=log_date,
                energy_score=4 if weekday in [0, 1] else 3 if weekday in [2, 3] else 5 if weekday in [4, 5] else 2,
                is_locked=True
            )
            db.add(daily_sched)
            db.flush()

        # Create a demo schedule version
        sched_ver = ScheduleVersion(
            daily_schedule_id=daily_sched.id,
            version=1,
            created_by=DEMO_MARKER,
            notes="[DEMO] Realistic synthetic logs for pattern detection",
            is_active=True
        )
        db.add(sched_ver)
        db.flush()

        blocks_to_add: List[ScheduleBlock] = []

        # 1. Gym (Daily morning habit: 07:00 - 08:00)
        # Mostly done across all 4 weeks, with only 2 occasional misses
        if day_offset == 17:  # Miss #1 on a Tuesday
            gym_status = "skipped"
            gym_reason = "Overslept alarm"
        elif day_offset == 6:  # Miss #2 on a Friday
            gym_status = "skipped"
            gym_reason = "Sore from leg day"
        else:
            gym_status = "completed"
            gym_reason = None

        blocks_to_add.append(ScheduleBlock(
            schedule_version_id=sched_ver.id,
            title="Morning Gym",
            type="gym",
            source=DEMO_MARKER,
            priority=10,
            planned_start="07:00:00",
            planned_end="08:00:00",
            actual_start="07:05:00" if gym_status == "completed" else None,
            actual_end="08:00:00" if gym_status == "completed" else None,
            status=gym_status,
            reason=gym_reason
        ))

        # 2. DSA Practice (Scheduled on Mon, Tue, Wed, Thu, Sat: 16:00 - 18:00)
        # Core pattern: Skipped on Wednesdays with reason 'Tired'!
        if weekday in [0, 1, 2, 3, 5]:
            if weekday == 2:  # Wednesday
                # 4 of 4 Wednesdays skipped! (100% skip rate, reason 'Tired')
                dsa_status = "skipped"
                dsa_reason = "Tired"
            elif day_offset == 20:  # 1 occasional skip on a Monday
                dsa_status = "skipped"
                dsa_reason = "Lab assignment submission"
            else:
                dsa_status = "completed"
                dsa_reason = None

            blocks_to_add.append(ScheduleBlock(
                schedule_version_id=sched_ver.id,
                title="DSA Practice",
                type="dsa",
                source=DEMO_MARKER,
                priority=2,
                planned_start="16:00:00",
                planned_end="18:00:00",
                actual_start="16:00:00" if dsa_status == "completed" else None,
                actual_end="18:00:00" if dsa_status == "completed" else None,
                status=dsa_status,
                reason=dsa_reason
            ))

        # 3. AI Agency Outreach (Scheduled on Mon, Wed, Fri, Sun: 18:30 - 20:30)
        # Core pattern: Skipped on Sundays (3 of 4 skipped, reason 'Weekend burnout')
        if weekday in [0, 2, 4, 6]:
            if weekday == 6:  # Sunday
                if day_offset == 7:  # 1 completed Sunday
                    agency_status = "completed"
                    agency_reason = None
                else:  # 3 skipped Sundays
                    agency_status = "skipped"
                    agency_reason = "Weekend burnout"
            elif day_offset == 11:  # 1 occasional skip on a Wednesday
                agency_status = "skipped"
                agency_reason = "Team sync call rescheduled"
            else:
                agency_status = "completed"
                agency_reason = None

            blocks_to_add.append(ScheduleBlock(
                schedule_version_id=sched_ver.id,
                title="AI Agency Outreach",
                type="agency",
                source=DEMO_MARKER,
                priority=3,
                planned_start="18:30:00",
                planned_end="20:30:00",
                actual_start="18:30:00" if agency_status == "completed" else None,
                actual_end="20:30:00" if agency_status == "completed" else None,
                status=agency_status,
                reason=agency_reason
            ))

        # 4. Client Deliverable / Deadline (Scheduled on Fridays: 15:30 - 17:30)
        if weekday == 4:
            blocks_to_add.append(ScheduleBlock(
                schedule_version_id=sched_ver.id,
                title="Client Video Deliverable",
                type="deadline",
                source=DEMO_MARKER,
                priority=5,
                planned_start="15:30:00",
                planned_end="17:30:00",
                actual_start="15:30:00",
                actual_end="17:30:00",
                status="completed",
                reason=None
            ))

        db.add_all(blocks_to_add)
        created_blocks_count += len(blocks_to_add)

    db.commit()
    print(f"[OK] Successfully seeded {created_blocks_count} demo activity blocks across {days_back} days.")


def main():
    parser = argparse.ArgumentParser(description="Seed realistic demo data for habit pattern detection.")
    parser.add_argument("--reset", action="store_true", help="Remove all demo data without creating new records.")
    parser.add_argument("--days", type=int, default=28, help="Number of past days to generate (default: 28).")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        user = db.query(User).first()
        if not user:
            print("[INFO] Creating default demo user...")
            user = User(
                name="Demo User",
                telegram_id="123456789",
                timezone="Asia/Kolkata",
                wake_time="07:00:00",
                sleep_time="23:00:00"
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        if args.reset:
            reset_demo_data(db, user.id)
            return

        # Seed realistic blocks
        seed_demo_blocks(db, user.id, days_back=args.days)

        # Run pattern detector
        print("\n[DETECT] Running Habit Pattern Detector on seeded logs...")
        results = detect_patterns(db, user.id, days_back=args.days)
        flagged = results.get("flagged_patterns", [])

        # Persist to MemoryPattern
        if flagged:
            saved = save_detected_patterns(db, user.id, flagged)
            print(f"[SAVE] Persisted {len(saved)} flagged patterns into MemoryPattern table.")

        print("\n" + "=" * 65)
        print("DETECTED BEHAVIORAL PATTERNS REPORT")
        print("=" * 65)
        if not flagged:
            print("No patterns flagged (no category reached >=3 samples and >=60% skip rate).")
        else:
            for idx, pat in enumerate(flagged, 1):
                print(f"\n[{idx}] Category: {pat['category_display']} on {pat['weekday_plural']}")
                print(f"    Message:      \"{pat['message']}\"")
                print(f"    Skip Rate:    {pat['skipped']} of {pat['total']} ({int(pat['skip_rate'] * 100)}%)")
                print(f"    Confidence:   {int(pat['confidence'] * 100)}%")
                print(f"    Main Reason:  {pat['most_common_reason']}")
        print("\n" + "=" * 65)

    finally:
        db.close()


if __name__ == "__main__":
    main()
