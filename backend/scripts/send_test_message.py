import sys
import asyncio
from pathlib import Path

# Add backend root to Python path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from telegram import Bot
from app.database.connection import settings, SessionLocal
from main import send_tomorrow_schedule_prompt_job, send_morning_checkin_job


async def main():
    token = settings.TELEGRAM_BOT_TOKEN
    owner_id = settings.TELEGRAM_OWNER_ID

    print(f"[INFO] Connecting to Telegram bot...")
    bot = Bot(token)
    me = await bot.get_me()
    print(f"[OK] Bot username: @{me.username}")

    print(f"[INFO] Sending test notification to owner chat_id: {owner_id}...")
    try:
        msg = await bot.send_message(
            chat_id=owner_id,
            text=(
                f"👋 **LIFE OS Connected!**\n\n"
                f"The Personal Habit Tracker Agent is running.\n\n"
                f"Commands you can send right now:\n"
                f"📅 `/tomorrow` - Negotiate tomorrow's schedule (with pattern warnings!)\n"
                f"⚡ `/energy` - Morning energy check-in\n"
                f"📥 Or reply with any thought to capture it to your Inbox."
            ),
            parse_mode="Markdown"
        )
        print(f"[SUCCESS] Message delivered to Telegram! Message ID: {msg.message_id}")
    except Exception as e:
        print(f"[ERROR] Failed to send message: {e}")


if __name__ == "__main__":
    asyncio.run(main())
