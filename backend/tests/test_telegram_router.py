import asyncio
import datetime
import pytest
from unittest.mock import AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.models import (
    Base,
    User,
    DailySchedule,
    ScheduleVersion,
    ScheduleBlock,
    InboxItem,
    MemoryProfile
)
from app.database.connection import settings
from app.telegram.handlers import (
    classify_text_intent,
    text_message_handler,
    today_command,
    patterns_command,
    inbox_command,
    start_command,
    callback_query_handler,
    format_today_schedule
)

TEST_DB_URL = "sqlite:///:memory:"

@pytest.fixture
def test_db():
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    
    # Seed owner user
    owner = User(id=1, name="Owner", telegram_id="123456789", timezone="Asia/Kolkata")
    db.add(owner)
    db.commit()
    
    # Seed today's schedule with blocks
    today_date = datetime.date.today()
    sched = DailySchedule(id=1, user_id=owner.id, date=today_date, energy_score=4)
    db.add(sched)
    db.commit()
    
    ver = ScheduleVersion(id=1, daily_schedule_id=sched.id, version=1, is_active=True)
    db.add(ver)
    db.commit()
    
    b1 = ScheduleBlock(
        schedule_version_id=ver.id,
        title="Gym Workout",
        type="gym",
        planned_start="07:00:00",
        planned_end="08:00:00",
        status="completed"
    )
    b2 = ScheduleBlock(
        schedule_version_id=ver.id,
        title="DSA Practice",
        type="dsa",
        planned_start="10:00:00",
        planned_end="11:30:00",
        status="pending"
    )
    b3 = ScheduleBlock(
        schedule_version_id=ver.id,
        title="AI Agency Outreach",
        type="agency",
        planned_start="14:00:00",
        planned_end="15:00:00",
        status="pending"
    )
    db.add_all([b1, b2, b3])
    db.commit()
    
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


# Mock Classes for Telegram Update and Message
class MockUser:
    def __init__(self, user_id=123456789, first_name="Owner"):
        self.id = user_id
        self.first_name = first_name

class MockMessage:
    def __init__(self, text: str):
        self.text = text
        self.replies = []
        self.reply_markups = []
        
    async def reply_text(self, text, reply_markup=None, parse_mode=None):
        self.replies.append(text)
        self.reply_markups.append(reply_markup)
        return self

class MockCallbackQuery:
    def __init__(self, data: str, message: MockMessage):
        self.data = data
        self.message = message
        self.answered = False
        self.edited_text = None
        
    async def answer(self):
        self.answered = True
        
    async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
        self.edited_text = text
        return self

class MockUpdate:
    def __init__(self, text: str = "", user_id: int = 123456789):
        self.effective_user = MockUser(user_id=user_id)
        self.message = MockMessage(text)
        self.callback_query = None


# --- 1. Unit Tests for Intent Classification ---

def test_intent_classification():
    """Validates classification of greetings, plan queries, pattern questions, tasks, and small talk."""
    # a. Greeting
    assert classify_text_intent("Hi") == "greeting"
    assert classify_text_intent("hi") == "greeting"
    assert classify_text_intent("Hello") == "greeting"
    assert classify_text_intent("hey there") == "greeting"
    assert classify_text_intent("Good morning") == "greeting"
    assert classify_text_intent("Hello bot!") == "greeting"

    # b. Plan questions
    assert classify_text_intent("What is the today plan") == "plan_today"
    assert classify_text_intent("Tell me the today's plan") == "plan_today"
    assert classify_text_intent("what is today's schedule") == "plan_today"
    assert classify_text_intent("what's next") == "plan_today"
    assert classify_text_intent("what now") == "plan_today"
    assert classify_text_intent("current block") == "plan_today"
    assert classify_text_intent("What is tomorrow's plan") == "plan_tomorrow"
    assert classify_text_intent("tomorrow schedule") == "plan_tomorrow"

    # c. Pattern questions
    assert classify_text_intent("what do I skip") == "patterns"
    assert classify_text_intent("patterns") == "patterns"
    assert classify_text_intent("what are my habits") == "patterns"
    assert classify_text_intent("skipping patterns") == "patterns"

    # d. Actionable tasks
    assert classify_text_intent("Finish pitch deck by Friday") == "task"
    assert classify_text_intent("finish client logo by Friday") == "task"
    assert classify_text_intent("Edit sunrise reel for client") == "task"
    assert classify_text_intent("Submit project report tomorrow") == "task"
    assert classify_text_intent("Buy protein powder") == "task"

    # Non-tasks (too short, small talk, questions)
    assert classify_text_intent("ok") == "non_task"
    assert classify_text_intent("thanks") == "non_task"
    assert classify_text_intent("how are you doing") == "non_task"
    assert classify_text_intent("Why is college so long?") == "non_task"


# --- 2. End-to-End Handler Tests with Database ---

def test_router_hi_saves_nothing(test_db, monkeypatch):
    """'Hi' should reply with friendly greeting and save nothing to Inbox."""
    monkeypatch.setattr("app.telegram.handlers.get_db", lambda: test_db)
    monkeypatch.setattr(settings, "TELEGRAM_OWNER_ID", "123456789")
    
    update = MockUpdate("Hi")
    context = AsyncMock()
    
    asyncio.run(text_message_handler(update, context))
    
    assert len(update.message.replies) == 1
    assert "Hey there!" in update.message.replies[0]
    assert "/today" in update.message.replies[0]
    
    # Verify no inbox items saved
    assert test_db.query(InboxItem).count() == 0


def test_router_what_is_today_plan_returns_schedule(test_db, monkeypatch):
    """'What is the today plan' returns the schedule and saves nothing to Inbox."""
    monkeypatch.setattr("app.telegram.handlers.get_db", lambda: test_db)
    monkeypatch.setattr(settings, "TELEGRAM_OWNER_ID", "123456789")
    
    update = MockUpdate("What is the today plan")
    context = AsyncMock()
    
    asyncio.run(text_message_handler(update, context))
    
    assert len(update.message.replies) == 1
    reply = update.message.replies[0]
    assert "Today's Schedule" in reply
    assert "Gym Workout" in reply
    assert "DSA Practice" in reply
    
    # Verify no inbox items saved
    assert test_db.query(InboxItem).count() == 0


def test_router_tell_me_todays_plan_returns_schedule(test_db, monkeypatch):
    """'Tell me the today's plan' returns the schedule and saves nothing to Inbox."""
    monkeypatch.setattr("app.telegram.handlers.get_db", lambda: test_db)
    monkeypatch.setattr(settings, "TELEGRAM_OWNER_ID", "123456789")
    
    update = MockUpdate("Tell me the today's plan")
    context = AsyncMock()
    
    asyncio.run(text_message_handler(update, context))
    
    assert len(update.message.replies) == 1
    reply = update.message.replies[0]
    assert "Today's Schedule" in reply
    assert "AI Agency Outreach" in reply
    
    # Verify no inbox items saved
    assert test_db.query(InboxItem).count() == 0


def test_router_finish_pitch_deck_saves_task_with_undo(test_db, monkeypatch):
    """'Finish pitch deck by Friday' saves a task and attaches an Undo button."""
    monkeypatch.setattr("app.telegram.handlers.get_db", lambda: test_db)
    monkeypatch.setattr(settings, "TELEGRAM_OWNER_ID", "123456789")
    
    update = MockUpdate("Finish pitch deck by Friday")
    context = AsyncMock()
    
    asyncio.run(text_message_handler(update, context))
    
    # Verify task was saved
    items = test_db.query(InboxItem).all()
    assert len(items) == 1
    item = items[0]
    assert "pitch deck" in item.title.lower() or "finish" in item.title.lower()
    assert item.status == "active"
    
    # Verify reply message and keyboard
    assert len(update.message.replies) == 1
    assert "Added to Inbox:" in update.message.replies[0]
    
    markup = update.message.reply_markups[0]
    assert markup is not None
    # Check that undo button is attached with undo_inbox_{item.id}
    undo_button = markup.inline_keyboard[0][0]
    assert undo_button.callback_data == f"undo_inbox_{item.id}"
    assert "Undo" in undo_button.text

    # Test the Undo action
    cb_update = MockUpdate()
    cb_update.callback_query = MockCallbackQuery(
        data=f"undo_inbox_{item.id}",
        message=update.message
    )
    asyncio.run(callback_query_handler(cb_update, context))
    
    # Verify item deleted
    assert test_db.query(InboxItem).count() == 0
    assert "Undone:" in cb_update.callback_query.edited_text


def test_router_small_talk_not_saved(test_db, monkeypatch):
    """Small talk message like 'how are you doing' should reply with hint and save nothing."""
    monkeypatch.setattr("app.telegram.handlers.get_db", lambda: test_db)
    monkeypatch.setattr(settings, "TELEGRAM_OWNER_ID", "123456789")
    
    update = MockUpdate("how are you doing")
    context = AsyncMock()
    
    asyncio.run(text_message_handler(update, context))
    
    assert len(update.message.replies) == 1
    assert "Didn't catch a task there" in update.message.replies[0]
    assert test_db.query(InboxItem).count() == 0


def test_today_command_highlights_current_block(test_db, monkeypatch):
    """/today highlights the active block and shows minutes left."""
    monkeypatch.setattr("app.telegram.handlers.get_db", lambda: test_db)
    monkeypatch.setattr(settings, "TELEGRAM_OWNER_ID", "123456789")
    
    # Test format_today_schedule at 10:30 (during DSA Practice 10:00 - 11:30)
    fake_now = datetime.datetime.combine(datetime.date.today(), datetime.time(10, 30))
    schedule_text = format_today_schedule(test_db, user_id=1, current_dt=fake_now)
    
    assert "▶️ **10:00 - 11:30: 📘 DSA Practice**" in schedule_text
    assert "(60m left)" in schedule_text  # 11:30 - 10:30 = 60 mins


def test_start_command_lists_all_commands_and_app_name(test_db, monkeypatch):
    """/start displays config app_name and full command list."""
    monkeypatch.setattr("app.telegram.handlers.get_db", lambda: test_db)
    monkeypatch.setattr(settings, "TELEGRAM_OWNER_ID", "123456789")
    
    update = MockUpdate()
    context = AsyncMock()
    
    asyncio.run(start_command(update, context))
    
    reply = update.message.replies[0]
    assert settings.APP_NAME in reply
    assert "/today" in reply
    assert "/tomorrow" in reply
    assert "/patterns" in reply
    assert "/inbox" in reply
    assert "/energy" in reply
    assert "/help" in reply
