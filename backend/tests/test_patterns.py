import datetime
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.models import Base, User, MemoryPattern, DailySchedule, ScheduleVersion, ScheduleBlock
from app.analytics.patterns import (
    detect_patterns_from_block_list,
    detect_patterns,
    save_detected_patterns,
)

TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def db_session():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_synthetic_patterns_three_cases():
    """
    Tests the 3 required synthetic cases:
    1. Should flag: Wednesday DSA 4 of 5 skipped (80% rate, sample size 5 >= 3)
    2. Below sample minimum: Monday Agency 2 of 2 skipped (100% rate, but sample size 2 < 3) -> NOT flagged
    3. Below rate threshold: Tuesday Gym 1 of 4 skipped (25% rate < 60%, sample size 4 >= 3) -> NOT flagged
    """
    ref_date = datetime.date(2026, 10, 18)  # Sunday
    synthetic_blocks = []

    # Case 1: Wednesday DSA (5 samples, 4 skipped with reason 'Tired', 1 completed)
    # Wednesdays in the 28-day window before 2026-10-18:
    # 2026-10-14 (Wed), 2026-10-07 (Wed), 2026-09-30 (Wed), 2026-09-23 (Wed), etc.
    # Case 1: Wednesday DSA (5 samples within the 28-day window: 4 skipped with 'Tired', 1 completed)
    # 4 Wednesdays in the 28-day window: Oct 14, Oct 7, Sep 30, Sep 23
    # Oct 14 has 2 sessions (one skipped, one completed)
    # Oct 7, Sep 30, Sep 23 have 1 skipped session each -> Total 5 sessions (4 skipped, 1 completed)
    synthetic_blocks.extend([
        {"date": datetime.date(2026, 10, 14), "type": "dsa", "title": "DSA Morning", "status": "skipped", "reason": "Tired"},
        {"date": datetime.date(2026, 10, 14), "type": "dsa", "title": "DSA Evening", "status": "completed", "reason": None},
        {"date": datetime.date(2026, 10, 7), "type": "dsa", "title": "DSA Practice", "status": "skipped", "reason": "Tired"},
        {"date": datetime.date(2026, 9, 30), "type": "dsa", "title": "DSA Practice", "status": "skipped", "reason": "Tired"},
        {"date": datetime.date(2026, 9, 23), "type": "dsa", "title": "DSA Practice", "status": "skipped", "reason": "Tired"},
    ])

    # Case 2: Monday Agency (2 samples, 2 skipped, 100% rate, but sample count 2 < 3)
    mondays = [
        datetime.date(2026, 10, 12),
        datetime.date(2026, 10, 5)
    ]
    for m_date in mondays:
        synthetic_blocks.append({
            "date": m_date,
            "type": "agency",
            "title": "AI Agency Outreach",
            "status": "skipped",
            "reason": "College work"
        })

    # Case 3: Tuesday Gym (4 samples, 1 skipped, 3 completed, 25% skip rate < 60%)
    tuesdays = [
        datetime.date(2026, 10, 13),
        datetime.date(2026, 10, 6),
        datetime.date(2026, 9, 29),
        datetime.date(2026, 9, 22)
    ]
    for i, t_date in enumerate(tuesdays):
        status = "skipped" if i == 0 else "completed"
        reason = "Overslept" if status == "skipped" else None
        synthetic_blocks.append({
            "date": t_date,
            "type": "gym",
            "title": "Morning Gym",
            "status": status,
            "reason": reason
        })

    result = detect_patterns_from_block_list(synthetic_blocks, date_limit=ref_date, days_back=28)
    flagged = result["flagged_patterns"]
    matrix = result["matrix"]

    # 1. Verification of Case 1 (Should flag)
    dsa_flagged = [p for p in flagged if p["category"] == "dsa" and p["weekday"] == 2]
    assert len(dsa_flagged) == 1, "Wednesday DSA should be flagged as a pattern"
    assert dsa_flagged[0]["skipped"] == 4
    assert dsa_flagged[0]["total"] == 5
    assert dsa_flagged[0]["skip_rate"] == 0.8
    assert dsa_flagged[0]["confidence"] > 0.5
    assert dsa_flagged[0]["most_common_reason"] == "Tired"
    assert "DSA skipped 4 of 5 Wednesdays (most common reason: Tired)" in dsa_flagged[0]["message"]

    # 2. Verification of Case 2 (Below sample minimum)
    agency_flagged = [p for p in flagged if p["category"] == "agency" and p["weekday"] == 0]
    assert len(agency_flagged) == 0, "Monday Agency should NOT flag because sample count is 2 (< 3)"

    # Verify that in the matrix it shows total=2, skipped=2, is_flagged=False
    agency_cell = next(c for c in matrix if c["category"] == "agency" and c["weekday"] == 0)
    assert agency_cell["total"] == 2
    assert agency_cell["skipped"] == 2
    assert agency_cell["skip_rate"] == 1.0
    assert agency_cell["is_flagged"] is False

    # 3. Verification of Case 3 (Below rate threshold)
    gym_flagged = [p for p in flagged if p["category"] == "gym" and p["weekday"] == 1]
    assert len(gym_flagged) == 0, "Tuesday Gym should NOT flag because skip rate is 25% (< 60%)"

    gym_cell = next(c for c in matrix if c["category"] == "gym" and c["weekday"] == 1)
    assert gym_cell["total"] == 4
    assert gym_cell["skipped"] == 1
    assert gym_cell["done"] == 3
    assert gym_cell["skip_rate"] == 0.25
    assert gym_cell["is_flagged"] is False

    # Total flagged patterns across all categories should be exactly 1
    assert len(flagged) == 1
    assert len(matrix) == 28  # 7 weekdays x 4 categories


def test_save_detected_patterns_idempotent(db_session):
    """
    Tests that saving detected patterns to MemoryPattern is idempotent
    and updates existing records without creating duplicates.
    """
    user = User(
        name="Test User",
        telegram_id="888888",
        timezone="Asia/Kolkata",
        wake_time="07:00:00",
        sleep_time="23:00:00"
    )
    db_session.add(user)
    db_session.commit()

    flagged_pats_v1 = [
        {
            "weekday": 2,
            "weekday_name": "Wednesday",
            "weekday_plural": "Wednesdays",
            "category": "dsa",
            "category_display": "DSA",
            "skipped": 3,
            "total": 4,
            "skip_rate": 0.75,
            "confidence": 0.68,
            "most_common_reason": "Tired",
            "message": "DSA skipped 3 of 4 Wednesdays (most common reason: Tired)"
        }
    ]

    # First save
    save_detected_patterns(db_session, user.id, flagged_pats_v1)
    patterns_in_db = db_session.query(MemoryPattern).filter(MemoryPattern.user_id == user.id).all()
    assert len(patterns_in_db) == 1
    assert "3 of 4" in patterns_in_db[0].pattern
    assert patterns_in_db[0].confidence == 0.68

    # Second save with updated stats (e.g. next week, 4 of 5 skipped)
    flagged_pats_v2 = [
        {
            "weekday": 2,
            "weekday_name": "Wednesday",
            "weekday_plural": "Wednesdays",
            "category": "dsa",
            "category_display": "DSA",
            "skipped": 4,
            "total": 5,
            "skip_rate": 0.8,
            "confidence": 0.77,
            "most_common_reason": "Tired",
            "message": "DSA skipped 4 of 5 Wednesdays (most common reason: Tired)"
        }
    ]

    save_detected_patterns(db_session, user.id, flagged_pats_v2)
    patterns_in_db_after = db_session.query(MemoryPattern).filter(MemoryPattern.user_id == user.id).all()
    # Must NOT create a duplicate record
    assert len(patterns_in_db_after) == 1
    assert "4 of 5" in patterns_in_db_after[0].pattern
    assert patterns_in_db_after[0].confidence == 0.77


def test_get_patterns_api(db_session):
    """Tests GET /api/patterns endpoint."""
    from fastapi.testclient import TestClient
    from main import app
    from app.database.connection import get_db
    from app.api.routes import get_current_user

    test_user = User(
        name="Test User",
        telegram_id="777777",
        timezone="Asia/Kolkata",
        wake_time="07:00:00",
        sleep_time="23:00:00"
    )
    db_session.add(test_user)
    db_session.commit()
    db_session.refresh(test_user)

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: test_user
    try:
        client = TestClient(app)
        response = client.get("/api/patterns")
        assert response.status_code == 200
        data = response.json()
        assert "flagged_patterns" in data
        assert "matrix" in data
        assert "summary" in data
        assert len(data["matrix"]) == 28
    finally:
        app.dependency_overrides.clear()

