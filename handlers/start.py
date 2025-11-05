import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from config import ADMIN_ID, OTHER_BOT_USERNAME
from locales import get_text
from services.bans import ban_manager
from storage.data_manager import data_manager
from locales import _, set_locale

logger = logging.getLogger(__name__)

def get_user_inline_menu():
    """Menu for regular user"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(_("buttons.ask_question"), callback_data="user_start_question")],
        [InlineKeyboardButton(_("buttons.suggestion"), callback_data="user_suggestion")],
        [InlineKeyboardButton(_("buttons.review"), callback_data="user_review")],
        [InlineKeyboardButton(_("buttons.change_language"), callback_data="user_change_language")],
        [InlineKeyboardButton(_("buttons.back_to_service"), url=f"https://t.me/{OTHER_BOT_USERNAME}")]
    ])

def get_admin_inline_menu():
    """Admin menu keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(_("buttons.inbox"), callback_data="admin_inbox")],
        [InlineKeyboardButton(_("buttons.stats"), callback_data="admin_stats")],
        [InlineKeyboardButton(_("buttons.settings"), callback_data="admin_settings")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    chat = update.effective_chat

    # Check ban
    if ban_manager.is_banned(user.id):
        await update.message.reply_text(_("messages.banned"), reply_markup=ReplyKeyboardRemove())
        return

    # Load user's saved locale
    user_data = data_manager.get_user_data(user.id)
    user_locale = user_data.get("locale", "ru")

    from locales import set_user_locale
    set_user_locale(user.id, user_locale)
    set_locale(user_locale)

    # Admin
    if user.id == ADMIN_ID:
        # Remove old ReplyKeyboard and send menu in single message
        await update.message.reply_text(
            _("welcome.admin"),
            reply_markup=get_admin_inline_menu()
        )

        logger.info(f"Admin {user.id} started bot")
        return

    # Regular user - remove old buttons
    await update.message.reply_text(
        _("welcome.user", name=user.first_name or "friend"),
        reply_markup=get_user_inline_menu()
    )

    logger.info(f"User {user.id} (@{user.username}) started bot")

# Alias for import compatibility
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command for registration"""
    await start(update, context)
