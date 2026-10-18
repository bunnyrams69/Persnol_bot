import datetime
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
)
from sqlalchemy.orm import relationship

from app.database.connection import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    telegram_id = Column(String(50), unique=True, nullable=False)
    timezone = Column(String(50), default="Asia/Kolkata")
    wake_time = Column(String(20), default="07:00:00")  # Stored as "HH:MM:SS"
    sleep_time = Column(String(20), default="23:00:00")  # Stored as "HH:MM:SS"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    fixed_blocks = relationship("FixedBlock", back_populates="user", cascade="all, delete-orphan")
    deadlines = relationship("Deadline", back_populates="user", cascade="all, delete-orphan")
    recurring_goals = relationship("RecurringGoal", back_populates="user", cascade="all, delete-orphan")
    inbox_items = relationship("InboxItem", back_populates="user", cascade="all, delete-orphan")
    daily_schedules = relationship("DailySchedule", back_populates="user", cascade="all, delete-orphan")
    memory_profiles = relationship("MemoryProfile", back_populates="user", cascade="all, delete-orphan")
    memory_patterns = relationship("MemoryPattern", back_populates="user", cascade="all, delete-orphan")
    memory_beliefs = relationship("MemoryBelief", back_populates="user", cascade="all, delete-orphan")
    memory_goals = relationship("MemoryGoal", back_populates="user", cascade="all, delete-orphan")
    weekly_reviews = relationship("WeeklyReview", back_populates="user", cascade="all, delete-orphan")


class FixedBlock(Base):
    __tablename__ = "fixed_blocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(100), nullable=False)
    start_time = Column(String(20), nullable=False)  # "HH:MM:SS"
    end_time = Column(String(20), nullable=False)  # "HH:MM:SS"
    monday = Column(Boolean, default=False)
    tuesday = Column(Boolean, default=False)
    wednesday = Column(Boolean, default=False)
    thursday = Column(Boolean, default=False)
    friday = Column(Boolean, default=False)
    saturday = Column(Boolean, default=False)
    sunday = Column(Boolean, default=False)
    movable = Column(Boolean, default=False)
    priority = Column(Integer, default=1)

    user = relationship("User", back_populates="fixed_blocks")


class Deadline(Base):
    __tablename__ = "deadlines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    client_name = Column(String(100), nullable=True)
    estimated_minutes = Column(Integer, default=60)
    actual_minutes = Column(Integer, nullable=True)
    due_datetime = Column(DateTime, nullable=False)
    status = Column(String(50), default="pending")  # pending, completed, failed
    priority = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="deadlines")


class RecurringGoal(Base):
    __tablename__ = "recurring_goals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)  # e.g., AI Agency, DSA
    ratio = Column(Float, nullable=False)  # e.g., 0.60, 0.40
    minimum_minutes = Column(Integer, default=60)
    priority = Column(Integer, default=1)

    user = relationship("User", back_populates="recurring_goals")


class InboxItem(Base):
    __tablename__ = "inbox"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    source = Column(String(50), default="manual")  # telegram, whatsapp, voice, manual
    priority = Column(String(50), default="medium")  # low, medium, high, urgent
    suggested_type = Column(String(50), default="personal")  # deadline, dsa, agency, personal
    status = Column(String(50), default="active")  # active, scheduled, archived
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="inbox_items")
    extractions = relationship("InboxExtraction", back_populates="inbox_item", cascade="all, delete-orphan")


class InboxExtraction(Base):
    __tablename__ = "inbox_extractions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    inbox_item_id = Column(Integer, ForeignKey("inbox.id", ondelete="CASCADE"), nullable=False)
    model = Column(String(100), nullable=True)
    prompt_version = Column(String(50), nullable=True)
    raw_response = Column(Text, nullable=True)
    parsed_response = Column(Text, nullable=True)  # JSON String
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    inbox_item = relationship("InboxItem", back_populates="extractions")


class DailySchedule(Base):
    __tablename__ = "daily_schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)  # e.g., 2026-06-24
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    energy_score = Column(Integer, nullable=True)
    generated_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_locked = Column(Boolean, default=False)

    user = relationship("User", back_populates="daily_schedules")
    versions = relationship("ScheduleVersion", back_populates="daily_schedule", cascade="all, delete-orphan")


class ScheduleVersion(Base):
    __tablename__ = "schedule_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    daily_schedule_id = Column(Integer, ForeignKey("daily_schedules.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    created_by = Column(String(50), default="planner")  # planner, claude, user
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    daily_schedule = relationship("DailySchedule", back_populates="versions")
    blocks = relationship("ScheduleBlock", back_populates="version_ref", cascade="all, delete-orphan")


class ScheduleBlock(Base):
    __tablename__ = "schedule_blocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    schedule_version_id = Column(Integer, ForeignKey("schedule_versions.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    type = Column(String(50), nullable=False)  # gym, deadline, agency, dsa, break, college
    source = Column(String(50), default="custom")  # fixed, deadline, goal, custom
    priority = Column(Integer, default=1)
    planned_start = Column(String(20), nullable=False)  # "HH:MM:SS"
    planned_end = Column(String(20), nullable=False)  # "HH:MM:SS"
    actual_start = Column(String(20), nullable=True)  # "HH:MM:SS"
    actual_end = Column(String(20), nullable=True)  # "HH:MM:SS"
    status = Column(String(50), default="pending")  # pending, completed, skipped
    reason = Column(Text, nullable=True)

    version_ref = relationship("ScheduleVersion", back_populates="blocks")


class MemoryProfile(Base):
    __tablename__ = "memory_profile"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    key = Column(String(100), nullable=False)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User", back_populates="memory_profiles")


class MemoryPattern(Base):
    __tablename__ = "memory_patterns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    pattern = Column(Text, nullable=False)
    confidence = Column(Float, default=0.5)
    evidence = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User", back_populates="memory_patterns")


class MemoryBelief(Base):
    __tablename__ = "memory_beliefs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    belief = Column(Text, nullable=False)
    status = Column(String(50), default="active")  # active, historical
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="memory_beliefs")


class MemoryGoal(Base):
    __tablename__ = "memory_goals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    goal = Column(Text, nullable=False)
    deadline = Column(DateTime, nullable=True)
    priority = Column(Integer, default=1)
    status = Column(String(50), default="active")  # active, completed, abandoned
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="memory_goals")


class WeeklyReview(Base):
    __tablename__ = "weekly_reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    wins = Column(Text, nullable=False)  # JSON-encoded array of wins
    losses = Column(Text, nullable=False)  # JSON-encoded array of losses
    coach_feedback = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="weekly_reviews")
