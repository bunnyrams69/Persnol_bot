# Life OS - Architecture

## Backend

-   Python 3.12
-   FastAPI
-   APScheduler
-   SQLite -\> PostgreSQL later
-   SQLAlchemy
-   Telegram Bot API
-   LLM API (MiniMax / Claude)

## Main Modules

-   api/
-   planner/
-   scheduler/
-   telegram/
-   llm/
-   analytics/
-   database/

## Database Tables

users, fixed_blocks, deadlines, recurring_goals, subtasks,
daily_schedule, weekly_reviews.

## Scheduler Logic

1.  Lock fixed blocks.
2.  Sort deadlines.
3.  Allocate deadline blocks.
4.  Split remaining time.
5.  Agency/DSA ratio.
6.  Generate daily schedule.
7.  Store and notify.

## AI Responsibilities

-   Night review
-   Pattern detection
-   Weekly reports
-   Coaching

Never use AI for scheduling.
