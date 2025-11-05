from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, filters

from .start import start_handler
from .user import (
    ask_question_handler,
    suggestion_handler,
    review_handler,
    text_message_handler,
    media_handler,
    back_to_service_handler,
    support_menu_handler
)
from .admin import (
    inbox_handler,
    stats_handler,
    settings_handler,
    admin_text_handler
)
from .callbacks import callback_handler
from .errors import error_handler
from .commands import (
    question_command,
    suggestion_command,
    review_command,
    inbox_command,
    stats_command,
    settings_command
)

__all__ = [
    'start_handler',
    'ask_question_handler',
    'suggestion_handler',
    'review_handler',
    'text_message_handler',
    'media_handler',
    'back_to_service_handler',
    'support_menu_handler',
    'inbox_handler',
    'stats_handler',
    'settings_handler',
    'admin_text_handler',
    'callback_handler',
    'error_handler',
    'question_command',
    'suggestion_command',
    'review_command',
    'inbox_command',
    'stats_command',
    'settings_command',
    'register_all_handlers'
]


def register_all_handlers(application):
    """Register all bot handlers"""
    from config import ADMIN_ID

    # Start handler
    application.add_handler(CommandHandler("start", start_handler))

    # User conversation handlers (if they are ConversationHandler)
    if hasattr(ask_question_handler, 'entry_points'):
        application.add_handler(ask_question_handler)
        application.add_handler(suggestion_handler)
        application.add_handler(review_handler)

    # Admin handlers
    if hasattr(inbox_handler, 'entry_points'):
        application.add_handler(inbox_handler)
        application.add_handler(stats_handler)
        application.add_handler(settings_handler)

    # Commands
    if hasattr(question_command, 'commands'):
        application.add_handler(question_command)
        application.add_handler(suggestion_command)
        application.add_handler(review_command)
        application.add_handler(inbox_command)
        application.add_handler(stats_command)
        application.add_handler(settings_command)

    # Callback handler
    if hasattr(callback_handler, 'pattern'):
        application.add_handler(callback_handler)
    else:
        application.add_handler(CallbackQueryHandler(callback_handler))

    # Support menu and back handlers
    if hasattr(support_menu_handler, 'pattern'):
        application.add_handler(support_menu_handler)

    if hasattr(back_to_service_handler, 'pattern'):
        application.add_handler(back_to_service_handler)

    # Text handler (for regular users)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.User(ADMIN_ID),
        text_message_handler
    ))

    # Media handler
    application.add_handler(MessageHandler(
        (filters.PHOTO | filters.VIDEO | filters.Document.ALL) & ~filters.COMMAND,
        media_handler
    ))

    # Admin text handler
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID),
        admin_text_handler
    ))

    # Error handler
    application.add_error_handler(error_handler)
