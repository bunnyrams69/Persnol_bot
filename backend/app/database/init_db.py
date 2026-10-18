import datetime
import sys
import os
from pathlib import Path

# Adjust path to import app correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database.connection import engine, SessionLocal, Base, settings
from app.database.models import User, FixedBlock, RecurringGoal, MemoryProfile, MemoryBelief

def init_db():
    # Create all tables
    print("Creating tables if they don't exist...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # 1. User check / seed
        owner_id = settings.TELEGRAM_OWNER_ID
        if not owner_id or owner_id == "your_telegram_id_here":
            owner_id = "123456789"
            
        user = db.query(User).filter(User.telegram_id == owner_id).first()
        if not user:
            user = db.query(User).first()
            
        if not user:
            print(f"Seeding default user with Telegram ID: {owner_id}...")
            user = User(
                name="User",
                telegram_id=owner_id,
                timezone=settings.TIMEZONE,
                wake_time="07:00:00",
                sleep_time="23:00:00"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            print(f"User exists: {user.name} (ID: {user.id})")

        # 2. Fixed Blocks check / seed
        existing_blocks = db.query(FixedBlock).filter(FixedBlock.user_id == user.id).all()
        existing_block_titles = {b.title.lower() for b in existing_blocks}

        blocks_to_add = []
        # Gym (7:00 AM -> 8:00 AM) - Every day
        if not any("gym" in t for t in existing_block_titles):
            blocks_to_add.append(FixedBlock(
                user_id=user.id,
                title="🏋 Gym",
                start_time="07:00:00",
                end_time="08:00:00",
                monday=True, tuesday=True, wednesday=True, thursday=True, friday=True, saturday=True, sunday=True,
                movable=False,
                priority=10
            ))

        # College (9:00 AM -> 15:15:00) - Monday to Friday
        if not any("college" in t for t in existing_block_titles):
            blocks_to_add.append(FixedBlock(
                user_id=user.id,
                title="🎓 College",
                start_time="09:00:00",
                end_time="15:15:00",
                monday=True, tuesday=True, wednesday=True, thursday=True, friday=True, saturday=False, sunday=False,
                movable=False,
                priority=9
            ))

        # Lunch (13:00:00 -> 13:45:00) - Daily
        if not any("lunch" in t for t in existing_block_titles):
            blocks_to_add.append(FixedBlock(
                user_id=user.id,
                title="🍽 Lunch",
                start_time="13:00:00",
                end_time="13:45:00",
                monday=True, tuesday=True, wednesday=True, thursday=True, friday=True, saturday=True, sunday=True,
                movable=True,
                priority=5
            ))

        if blocks_to_add:
            print(f"Seeding {len(blocks_to_add)} missing fixed blocks...")
            db.add_all(blocks_to_add)
            db.commit()
        else:
            print("Fixed blocks already seeded.")

        # 3. Recurring Goals check / seed
        existing_goals = db.query(RecurringGoal).filter(RecurringGoal.user_id == user.id).all()
        existing_goal_names = {g.name.lower() for g in existing_goals}

        goals_to_add = []
        if not any("agency" in n for n in existing_goal_names):
            goals_to_add.append(RecurringGoal(
                user_id=user.id,
                name="🚀 AI Agency",
                ratio=0.60,
                minimum_minutes=60,
                priority=3
            ))

        if not any("dsa" in n for n in existing_goal_names):
            goals_to_add.append(RecurringGoal(
                user_id=user.id,
                name="📘 DSA Practice",
                ratio=0.40,
                minimum_minutes=60,
                priority=2
            ))

        if goals_to_add:
            print(f"Seeding {len(goals_to_add)} missing recurring goals...")
            db.add_all(goals_to_add)
            db.commit()
        else:
            print("Recurring goals already seeded.")

        # 4. Memory Profile check / seed
        existing_profiles = db.query(MemoryProfile).filter(MemoryProfile.user_id == user.id).all()
        existing_keys = {p.key for p in existing_profiles}

        default_memory_data = [
            ("name", user.name if user.name else "User"),
            ("age", "20"),
            ("college", "University"),
            ("dream", "Build an AI Agency to $10k/month and secure a top placement"),
            ("weakness", "Skips study sessions after heavy work or gym fatigue"),
            ("strengths", "Consistency at gym (never skips) and high drive for primary projects")
        ]

        memories_to_add = []
        for key, val in default_memory_data:
            if key not in existing_keys:
                memories_to_add.append(MemoryProfile(user_id=user.id, key=key, value=val))

        if memories_to_add:
            print(f"Seeding {len(memories_to_add)} missing memory profiles...")
            db.add_all(memories_to_add)
            db.commit()
        else:
            print("Memory profile already seeded.")

        # 5. Memory Beliefs check / seed
        existing_beliefs = db.query(MemoryBelief).filter(MemoryBelief.user_id == user.id).all()
        if not existing_beliefs:
            print("Seeding default memory belief...")
            belief = MemoryBelief(
                user_id=user.id,
                belief="Gym is non-negotiable. If I miss the gym, my day collapses.",
                status="active"
            )
            db.add(belief)
            db.commit()
        else:
            print("Memory beliefs already seeded.")

        print("Database initialization check completed successfully!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
