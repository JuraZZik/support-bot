from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from locales import get_text
from locales import _

def get_rating_keyboard(ticket_id: str):
    """Rating keyboard"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(_("rating.excellent"), callback_data=f"rate:{ticket_id}:excellent"),
            InlineKeyboardButton(_("rating.good"), callback_data=f"rate:{ticket_id}:good"),
            InlineKeyboardButton(_("rating.ok"), callback_data=f"rate:{ticket_id}:ok")
        ]
    ])

def get_settings_keyboard():
    """Settings keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚫 " + _("admin.ban_user"), callback_data="ban_user")],
        [InlineKeyboardButton("✅ " + _("admin.unban_user"), callback_data="unban_user")],
        [InlineKeyboardButton("📋 " + _("admin.bans_list"), callback_data="bans_list")],
        [InlineKeyboardButton("🗑 " + _("admin.clear_tickets"), callback_data="clear_tickets")],
        [InlineKeyboardButton("💾 " + _("admin.create_backup"), callback_data="create_backup")],
        [InlineKeyboardButton("🌐 " + _("admin.change_language"), callback_data="change_language")],
        [InlineKeyboardButton(f"{get_text('ui.home_emoji')} {_('buttons.main_menu')}", callback_data="admin_home")]
    ])

def get_language_keyboard():
    """Language selection keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇷🇺 Russian", callback_data="lang:ru")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang:en")],
        [InlineKeyboardButton(f"◀️ {_('buttons.back')}", callback_data="settings")]
    ])
