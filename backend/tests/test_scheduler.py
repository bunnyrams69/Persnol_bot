import datetime
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.models import Base, User, FixedBlock, Deadline, RecurringGoal, DailySchedule, ScheduleVersion, ScheduleBlock
from app.planner.engine import generate_daily_schedule
from app.planner.free_slots import time_to_minutes

# Setup in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def db_session():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_deterministic_scheduler(db_session):
    # 1. Create a dummy user
    user = User(
        name="Test User",
        telegram_id="999999",
        timezone="Asia/Kolkata",
        wake_time="07:00:00",
        sleep_time="23:00:00"
    )
    db_session.add(user)
    db_session.commit()
    
    # 2. Add Fixed Blocks (Gym: 7-8 AM daily, College: 9 AM - 3 PM Mon-Fri)
    gym = FixedBlock(
        user_id=user.id,
        title="🏋 Gym",
        start_time="07:00:00",
        end_time="08:00:00",
        monday=True, tuesday=True, wednesday=True, thursday=True, friday=True, saturday=True, sunday=True,
        movable=False,
        priority=10
    )
    college = FixedBlock(
        user_id=user.id,
        title="🎓 College",
        start_time="09:00:00",
        end_time="15:00:00",
        monday=True, tuesday=True, wednesday=True, thursday=True, friday=True, saturday=False, sunday=False,
        movable=False,
        priority=9
    )
    db_session.add_all([gym, college])
    
    # 3. Add Deadline (120 minutes, due in 2 days)
    deadline = Deadline(
        user_id=user.id,
        title="Client Reel Edit",
        client_name="Sunrise Corp",
        estimated_minutes=120,
        due_datetime=datetime.datetime.utcnow() + datetime.timedelta(days=2),
        status="pending",
        priority=5
    )
    db_session.add(deadline)
    
    # 4. Add Recurring Goals (AI Agency: 60%, DSA: 40%)
    agency = RecurringGoal(
        user_id=user.id,
        name="🚀 AI Agency",
        ratio=0.60,
        minimum_minutes=60,
        priority=3
    )
    dsa = RecurringGoal(
        user_id=user.id,
        name="📘 DSA",
        ratio=0.40,
        minimum_minutes=60,
        priority=2
    )
    db_session.add_all([agency, dsa])
    db_session.commit()
    
    # 5. Generate schedule for a Tuesday (which has College + Gym)
    tuesday_date = datetime.date(2026, 6, 23)  # 2026-06-23 is a Tuesday
    
    daily_schedule = generate_daily_schedule(db_session, user.id, tuesday_date)
    
    # Verify schedule object
    assert daily_schedule is not None
    assert daily_schedule.date == tuesday_date
    
    # Verify version 1 is created and active
    version = db_session.query(ScheduleVersion).filter(
        ScheduleVersion.daily_schedule_id == daily_schedule.id,
        ScheduleVersion.is_active == True
    ).first()
    assert version is not None
    assert version.version == 1
    assert version.created_by == "planner"
    
    # Fetch blocks
    blocks = db_session.query(ScheduleBlock).filter(
        ScheduleBlock.schedule_version_id == version.id
    ).order_by(ScheduleBlock.planned_start).all()
    
    assert len(blocks) > 0
    
    # Assert Gym is at 07:00:00 -> 08:00:00
    gym_block = next((b for b in blocks if "Gym" in b.title), None)
    assert gym_block is not None
    assert gym_block.planned_start == "07:00:00"
    assert gym_block.planned_end == "08:00:00"
    
    # Assert College is at 09:00:00 -> 15:00:00
    college_block = next((b for b in blocks if "College" in b.title), None)
    assert college_block is not None
    assert college_block.planned_start == "09:00:00"
    assert college_block.planned_end == "15:00:00"
    
    # Verify deadline block exists (Client Reel Edit)
    deadline_block = next((b for b in blocks if "Client Reel Edit" in b.title), None)
    assert deadline_block is not None
    assert deadline_block.type == "deadline"
    
    # Calculate time allocated to Agency and DSA
    agency_blocks = [b for b in blocks if "AI Agency" in b.title]
    dsa_blocks = [b for b in blocks if "DSA" in b.title]
    
    agency_mins = sum(time_to_minutes(b.planned_end) - time_to_minutes(b.planned_start) for b in agency_blocks)
    dsa_mins = sum(time_to_minutes(b.planned_end) - time_to_minutes(b.planned_start) for b in dsa_blocks)
    
    assert agency_mins > 0
    assert dsa_mins > 0
    
    # Ratio check (Agency: 60%, DSA: 40% of leftover minutes)
    ratio = agency_mins / (agency_mins + dsa_mins)
    assert pytest.approx(ratio, 0.05) == 0.60
