import logging
import datetime
from telegram import Bot
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from app.database.connection import settings
from app.telegram.handlers import (
    start_command,
    energy_command,
    today_command,
    tomorrow_command,
    patterns_command,
    inbox_command,
    help_command,
    text_message_handler,
    callback_query_handler
)
from app.telegram.keyboards import (
    get_energy_keyboard,
    get_block_checkin_keyboard,
    get_schedule_approval_keyboard
)

logger = logging.getLogger("life_os.telegram")

def get_telegram_app() -> Application:
    """Configures and returns the python-telegram-bot Application."""
    token = settings.TELEGRAM_BOT_TOKEN
    # Handle bootstrapping
    if not token or token == "your_bot_token_here":
        # Return a dummy application for testing/bootstrap
        token = "123456789:PlaceholderTokenForDevelopmentOnly"
        
    app = Application.builder().token(token).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("today", today_command))
    app.add_handler(CommandHandler("tomorrow", tomorrow_command))
    app.add_handler(CommandHandler("patterns", patterns_command))
    app.add_handler(CommandHandler("inbox", inbox_command))
    app.add_handler(CommandHandler("energy", energy_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(callback_query_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))
    
    return app


# --- Notification Functions for Scheduler Triggering ---

async def send_morning_checkin(bot_token: str, chat_id: str):
    """Sends the morning energy rating message."""
    async with Bot(bot_token) as bot:
        await bot.send_message(
            chat_id=chat_id,
            text="Good Morning. How is your energy level today?",
            reply_markup=get_energy_keyboard()
        )
        logger.info(f"Morning checkin sent to chat_id: {chat_id}")

async def send_block_checkin(bot_token: str, chat_id: str, block_id: int, block_title: str):
    """Sends a completion follow-up message at the end of a block."""
    async with Bot(bot_token) as bot:
        await bot.send_message(
            chat_id=chat_id,
            text=f"Did you finish **{block_title}**?",
            reply_markup=get_block_checkin_keyboard(block_id),
            parse_mode="Markdown"
        )
        logger.info(f"Block checkin sent for block {block_id} to chat_id: {chat_id}")

async def send_tomorrow_negotiation(
    bot_token: str,
    chat_id: str,
    schedule_id: int,
    blocks_summary: str,
    pattern_warning: str = None
):
    """Sends tomorrow's generated schedule with negotiation options (9 PM)."""
    async with Bot(bot_token) as bot:
        warning_section = f"\n\n{pattern_warning}" if pattern_warning else ""
        message_text = (
            f"📅 **Tomorrow's Schedule Plan**\n\n"
            f"{blocks_summary}"
            f"{warning_section}\n\n"
            f"Looks good, or do we need to negotiate?"
        )
        await bot.send_message(
            chat_id=chat_id,
            text=message_text,
            reply_markup=get_schedule_approval_keyboard(schedule_id),
            parse_mode="Markdown"
        )
        logger.info(f"Tomorrow schedule negotiation sent to chat_id: {chat_id}")
