from telegram import BotCommand, BotCommandScopeChat
from telegram.ext import Application
import logging
from config import ADMIN_ID

logger = logging.getLogger(__name__)

async def setup_bot_menu(application: Application):
    """Setup bot menu"""
    try:
        # Commands for regular users (only /start)
        user_commands = [
            BotCommand("start", "Main menu"),
        ]

        # Commands for admin (only /start)
        admin_commands = [
            BotCommand("start", "Main menu"),
        ]

        # Set commands for regular users
        await application.bot.set_my_commands(user_commands)

        # Set commands for admin
        await application.bot.set_my_commands(
            admin_commands,
            scope=BotCommandScopeChat(chat_id=ADMIN_ID)
        )

        logger.info("Bot menu configured successfully")
    except Exception as e:
        logger.error(f"Failed to setup bot menu: {e}", exc_info=True)
