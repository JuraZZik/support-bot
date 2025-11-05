#!/usr/bin/env python3
"""
Utility for managing admin main screen
"""
import logging
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from config import ADMIN_ID

logger = logging.getLogger(__name__)

# Global storage of root message IDs for each admin
ADMIN_ROOT_MSG = {}


async def show_admin_screen(update: Update, context: ContextTypes.DEFAULT_TYPE,
                           text: str, keyboard: InlineKeyboardMarkup = None):
    """
    Show or update admin main screen.
    Instead of sending new messages, edit one root message.
    """
    user = update.effective_user
    chat_id = user.id

    if user.id != ADMIN_ID:
        return

    # Get root message ID from global storage
    root_msg_id = ADMIN_ROOT_MSG.get(chat_id)

    try:
        if root_msg_id:
            # Edit existing message
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text=text,
                    reply_markup=keyboard,
                    parse_mode=None
                )
            else:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=root_msg_id,
                    text=text,
                    reply_markup=keyboard,
                    parse_mode=None
                )
        else:
            # Create new root message
            if update.callback_query:
                msg = await update.callback_query.message.reply_text(
                    text=text,
                    reply_markup=keyboard
                )
            elif update.message:
                msg = await update.message.reply_text(
                    text=text,
                    reply_markup=keyboard
                )
            else:
                msg = await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=keyboard
                )

            # Save root message ID
            ADMIN_ROOT_MSG[chat_id] = msg.message_id

    except BadRequest as e:
        # If message unchanged - this is normal, skip update
        if "message is not modified" in str(e).lower():
            logger.debug(f"Message content unchanged, skipping update")
            return

        # For other errors, create new message
        logger.warning(f"Failed to edit message: {e}")
        if update.message:
            msg = await update.message.reply_text(text=text, reply_markup=keyboard)
        else:
            msg = await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)

        # Update root message ID
        ADMIN_ROOT_MSG[chat_id] = msg.message_id


def reset_admin_screen(chat_id: int):
    """
    Reset root message for admin.
    Useful when need to create new screen.
    """
    if chat_id in ADMIN_ROOT_MSG:
        del ADMIN_ROOT_MSG[chat_id]
        logger.debug(f"Admin screen reset for chat_id={chat_id}")
