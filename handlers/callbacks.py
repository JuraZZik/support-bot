import logging
import os
from zoneinfo import ZoneInfo
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_ID, BACKUP_ENABLED, BACKUP_FULL_PROJECT, BACKUP_FILE_LIST, BACKUP_SEND_TO_TELEGRAM, BACKUP_MAX_SIZE_MB
from locales import get_text
from services.tickets import ticket_service
from services.bans import ban_manager
from services.feedback import feedback_service
from services.alerts import alert_service
from storage.data_manager import data_manager
from storage.instruction_store import INSTRUCTION_MESSAGES, SEARCH_RESULT_MESSAGES, INBOX_MENU_MESSAGES
from utils.keyboards import get_rating_keyboard, get_settings_keyboard, get_language_keyboard
from locales import set_locale, _

logger = logging.getLogger(__name__)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main callback query handler"""
    query = update.callback_query
    data = query.data
    user = update.effective_user

    await query.answer()

    # ========== Open ticket card (from search and regular menu) ==========
    if data.startswith("ticket:"):
        ticket_id = data.split(":")[1]
        from handlers.admin import show_ticket_card
        await show_ticket_card(update, context, ticket_id)
        return

    # ========== Feedback after rating (no cooldown) ==========
    if data == "after_rate_suggestion":
        context.user_data["state"] = "awaiting_suggestion"
        context.user_data["skip_cooldown"] = True
        await query.message.reply_text(_("messages.write_suggestion"))
        return

    elif data == "after_rate_review":
        context.user_data["state"] = "awaiting_review"
        context.user_data["skip_cooldown"] = True
        await query.message.reply_text(_("messages.write_review"))
        return

    # ========== Handle feedback prompt cancellation ==========
    elif data == "cancel_feedback_prompt":
        try:
            await query.delete_message()
        except Exception as e:
            logger.error(f"Failed to delete feedback prompt: {e}")
            await query.answer("✅")
        return

    # ========== Handle user menu ==========
    elif data == "user_start_question":
        await query.message.reply_text(_("messages.describe_question", n=20))
        context.user_data["state"] = "awaiting_question"
        return

    elif data == "user_suggestion":
        can_send, error_msg = feedback_service.check_cooldown(user.id, "suggestion")
        if not can_send:
            context.user_data["state"] = None
            await query.message.reply_text(error_msg)
            return

        context.user_data["state"] = "awaiting_suggestion"
        await query.message.reply_text(_("messages.write_suggestion"))
        return

    elif data == "user_review":
        can_send, error_msg = feedback_service.check_cooldown(user.id, "review")
        if not can_send:
            context.user_data["state"] = None
            await query.message.reply_text(error_msg)
            return

        context.user_data["state"] = "awaiting_review"
        await query.message.reply_text(_("messages.write_review"))
        return

    # ========== Handle language change for user ==========
    elif data == "user_change_language":
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🇷🇺 Русский", callback_data="user_lang:ru"),
                InlineKeyboardButton("🇬🇧 English", callback_data="user_lang:en")
            ],
            [InlineKeyboardButton(f"◀️ {_('buttons.back')}", callback_data="user_home")]
        ])

        await query.edit_message_text(
            _("messages.choose_language"),
            reply_markup=keyboard
        )
        return

    elif data.startswith("user_lang:"):
        locale = data.split(":")[1]

        data_manager.update_user_data(user.id, {"locale": locale})

        from locales import set_user_locale
        set_user_locale(user.id, locale)
        set_locale(locale)

        await query.edit_message_text(
            _("admin.language_changed")
        )

        from handlers.start import get_user_inline_menu
        await context.bot.send_message(
            chat_id=user.id,
            text=_("welcome.user", name=user.first_name or "friend"),
            reply_markup=get_user_inline_menu()
        )
        return

    # ========== Search ticket by ID ==========
    elif data == "search_ticket_start":
        from storage.instruction_store import INBOX_MENU_MESSAGES

        # 🗑️ Delete inbox menu
        inbox_msg_id = INBOX_MENU_MESSAGES.get(ADMIN_ID)
        if inbox_msg_id:
            try:
                await context.bot.delete_message(chat_id=ADMIN_ID, message_id=inbox_msg_id)
                logger.info(f"✅ Deleted inbox menu: {inbox_msg_id}")
            except Exception as e:
                logger.error(f"Failed to delete inbox menu: {e}")
            INBOX_MENU_MESSAGES.pop(ADMIN_ID, None)

        # 🗑️ Delete PREVIOUS search menu (if exists)
        search_menu_msg_id = context.user_data.get("search_menu_msg_id")
        if search_menu_msg_id:
            try:
                await context.bot.delete_message(chat_id=ADMIN_ID, message_id=search_menu_msg_id)
                logger.info(f"✅ Deleted previous search menu: {search_menu_msg_id}")
            except Exception as e:
                logger.error(f"Failed to delete search menu: {e}")

        # 🗑️ Delete PREVIOUS search result (if exists)
        old_result_msg_id = SEARCH_RESULT_MESSAGES.get(ADMIN_ID)
        if old_result_msg_id:
            try:
                await context.bot.delete_message(chat_id=ADMIN_ID, message_id=old_result_msg_id)
                logger.info(f"✅ Deleted old search result: {old_result_msg_id}")
            except Exception as e:
                logger.error(f"Failed to delete old search result: {e}")

        # ✨ Send NEW search menu message
        msg = await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=_("search.prompt"),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(text=_("search.button_cancel"), callback_data="admin_inbox")
            ]])
        )

        # 💾 Save message_id of new menu
        context.user_data["search_menu_msg_id"] = msg.message_id
        context.user_data["state"] = "search_ticket_input"
        logger.info(f"🔍 New search menu created: {msg.message_id}")
        return

    # ========== Handle admin menu ==========
    elif data == "admin_inbox":
        await handle_admin_inbox(update, context)
        return

    elif data == "admin_stats":
        await handle_admin_stats(update, context)
        return

    elif data == "admin_settings":
        from handlers.admin import settings_handler
        await settings_handler(update, context)
        return

    # ========== Handle settings ==========
    elif data == "ban_user":
        context.user_data["state"] = "awaiting_ban_user_id"
        from utils.admin_screen import show_admin_screen
        await show_admin_screen(update, context, _("admin.enter_user_id"), None)
        return

    elif data == "unban_user":
        context.user_data["state"] = "awaiting_unban_user_id"
        from utils.admin_screen import show_admin_screen
        await show_admin_screen(update, context, _("admin.enter_unban_id"), None)
        return

    elif data == "bans_list":
        await handle_bans_list(update, context)
        return

    elif data == "clear_tickets":
        count = ticket_service.clear_active_tickets()
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"◀️ {_('buttons.back')}", callback_data="settings")]
        ])
        from utils.admin_screen import show_admin_screen
        await show_admin_screen(
            update, context,
            _("admin.tickets_cleared") if count > 0 else _("admin.no_active_tickets"),
            keyboard
        )
        return

    # ========== Handle manual backup creation ==========
    elif data == "create_backup":
        from services.backup import backup_service
        from utils.admin_screen import show_admin_screen

        if not BACKUP_ENABLED:
            await show_admin_screen(
                update, context,
                _("messages.backup_disabled_full"),
                get_settings_keyboard()
            )
            return

        admin_data = data_manager.get_user_data(ADMIN_ID)
        admin_locale = admin_data.get("locale", "ru")

        await query.answer(_("messages.backup_creating"), show_alert=False)

        try:
            backup_path, backup_info = backup_service.create_backup()

            if not backup_path:
                raise RuntimeError("Backup path is empty")

            backup_filename = os.path.basename(backup_path)
            size_formatted = backup_info.get("size_formatted", f"{backup_info.get('size_mb', 0):.1f}MB")

            logger.info(f"Manual backup created: {backup_filename} ({size_formatted})")

            if admin_locale == "ru":
                if backup_info.get("type") == "full":
                    message_text = (
                        f"✅ **Full project backup created:**\n\n"
                        f"📂 **Directory:** {backup_info.get('source_dir')}\n"
                        f"❌ **Excluded:** {backup_info.get('excluded_patterns')}\n"
                        f"📦 **Files in archive:** {backup_info.get('files_in_archive')}\n"
                        f"💾 **Size:** {size_formatted}\n"
                        f"📝 **File:** {backup_filename}"
                    )
                else:
                    message_text = (
                        f"✅ **Selective backup created:**\n\n"
                        f"📋 **Files:** {backup_info.get('files')}\n"
                        f"📦 **Files in archive:** {backup_info.get('files_in_archive')}\n"
                        f"💾 **Size:** {size_formatted}\n"
                        f"📝 **File:** {backup_filename}"
                    )
            else:
                if backup_info.get("type") == "full":
                    message_text = (
                        f"✅ **Full project backup created:**\n\n"
                        f"📂 **Directory:** {backup_info.get('source_dir')}\n"
                        f"❌ **Excluded:** {backup_info.get('excluded_patterns')}\n"
                        f"📦 **Files in archive:** {backup_info.get('files_in_archive')}\n"
                        f"💾 **Size:** {size_formatted}\n"
                        f"📝 **File:** {backup_filename}"
                    )
                else:
                    message_text = (
                        f"✅ **Selective backup created:**\n\n"
                        f"📋 **Files:** {backup_info.get('files')}\n"
                        f"📦 **Files in archive:** {backup_info.get('files_in_archive')}\n"
                        f"💾 **Size:** {size_formatted}\n"
                        f"📝 **File:** {backup_filename}"
                    )

            if BACKUP_SEND_TO_TELEGRAM:
                size_mb = backup_info.get("size_mb", 0)
                if size_mb <= BACKUP_MAX_SIZE_MB:
                    caption = f"📦 {_('admin.create_backup')}\n\n{message_text}"
                    await alert_service.send_backup_file(backup_path, caption)
                    logger.info(f"Backup sent to Telegram: {backup_filename} ({size_formatted})")
                else:
                    if admin_locale == "ru":
                        warning_msg = (
                            f"⚠️ **Backup too large to send:**\n\n"
                            f"{message_text}\n\n"
                            f"📌 Size: {size_formatted}\n"
                            f"📈 Limit: {BACKUP_MAX_SIZE_MB}MB\n"
                            f"📁 Backup saved on server: `/bot_data/backups/{backup_filename}`\n\n"
                            f"✅ File available for download from server"
                        )
                    else:
                        warning_msg = (
                            f"⚠️ **Backup too large to send:**\n\n"
                            f"{message_text}\n\n"
                            f"📌 Size: {size_formatted}\n"
                            f"📈 Limit: {BACKUP_MAX_SIZE_MB}MB\n"
                            f"📁 Backup saved on server: `/bot_data/backups/{backup_filename}`\n\n"
                            f"✅ File available for download from server"
                        )
                    message_text = warning_msg
                    logger.warning(f"Backup too large to send to Telegram: {backup_filename} ({size_formatted} > {BACKUP_MAX_SIZE_MB}MB)")

            await show_admin_screen(
                update, context,
                message_text,
                get_settings_keyboard()
            )

        except Exception as e:
            logger.error(f"Manual backup failed: {e}", exc_info=True)
            await show_admin_screen(
                update, context,
                _("admin.backup_failed", error=str(e)),
                get_settings_keyboard()
            )
        return

    elif data == "change_language":
        from utils.admin_screen import show_admin_screen
        await show_admin_screen(
            update, context,
            _("admin.choose_language"),
            get_language_keyboard()
        )
        return

    elif data == "settings":
        from utils.admin_screen import show_admin_screen
        await show_admin_screen(
            update, context,
            _("admin.settings"),
            get_settings_keyboard()
        )
        return

    # ========== Handle language change ==========
    elif data.startswith("lang:"):
        locale = data.split(":")[1]

        data_manager.update_user_data(ADMIN_ID, {"locale": locale})

        set_locale(locale)
        from utils.admin_screen import show_admin_screen
        await show_admin_screen(
            update, context,
            _("admin.language_changed"),
            get_settings_keyboard()
        )
        return

    # ========== Handle rating ==========
    elif data.startswith("rate:"):
        await handle_rating(update, context, data)
        return

    # ========== Handle feedback thank you ==========
    elif data.startswith("thank:"):
        await handle_thank_feedback(update, context, data)
        return

    # ========== Handle tickets by admin ==========
    elif data.startswith("take:"):
        await handle_take_ticket(update, context, data)
        return

    elif data.startswith("close:"):
        await handle_close_ticket(update, context, data)
        return

    elif data.startswith("reply:"):
        await handle_reply_ticket(update, context, data)
        return

    # ========== Handle inbox filters ==========
    elif data.startswith("inbox_filter:"):
        await handle_inbox_filter(update, context, data)
        return

    # ========== Handle pagination ==========
    elif data.startswith("inbox_page:"):
        await handle_inbox_page(update, context, data)
        return

    # ========== Other handlers ==========
    elif data == "admin_home":
        from handlers.start import get_admin_inline_menu
        from utils.admin_screen import show_admin_screen
        await show_admin_screen(
            update, context,
            _("welcome.admin"),
            get_admin_inline_menu()
        )
        return

    elif data == "user_home":
        from handlers.start import get_user_inline_menu
        await query.message.reply_text(
            _("welcome.user", name=query.from_user.first_name or "friend"),
            reply_markup=get_user_inline_menu()
        )
        return

    elif data == "noop":
        return

# ========== Helper handlers ==========
async def handle_admin_inbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display incoming tickets for admin"""
    from handlers.admin import show_inbox
    await show_inbox(update, context)

async def handle_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display statistics for admin"""
    stats = data_manager.get_stats()
    banned_count = len(ban_manager.get_banned_list())
    stats["banned_count"] = banned_count

    text = _("admin.stats_text", **stats)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{get_text('ui.home_emoji')} {_('buttons.main_menu')}", callback_data="admin_home")]
    ])

    from utils.admin_screen import show_admin_screen
    await show_admin_screen(update, context, text, keyboard)

async def handle_rating(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Handle ticket rating"""
    query = update.callback_query
    parts = data.split(":")
    ticket_id = parts[1]
    rating = parts[2]
    user = query.from_user

    logger.info(f"Rating received: ticket_id={ticket_id}, rating={rating}")

    user_data = data_manager.get_user_data(user.id)
    user_locale = user_data.get("locale", "ru")
    set_locale(user_locale)

    ticket = ticket_service.rate_ticket(ticket_id, rating)

    if ticket:
        rating_text = _(f"rating.{rating}")

        await query.edit_message_text(
            _("messages.thanks_rating_text", rating=rating_text)
        )
        logger.info(f"User rated ticket {ticket_id} with {rating}")

        try:
            from handlers.user import send_or_update_ticket_card, TICKET_CARD_MESSAGES
            message_id = TICKET_CARD_MESSAGES.get(ticket_id)

            logger.info(f"TICKET_CARD_MESSAGES content: {TICKET_CARD_MESSAGES}")
            logger.info(f"Attempting to update admin card. ticket_id={ticket_id}, message_id={message_id}")

            if message_id:
                await send_or_update_ticket_card(context, ticket_id, action="closed", message_id=message_id)
                logger.info(f"✅ Updated admin ticket card with rating for {ticket_id}")
            else:
                logger.warning(f"⚠️ No message_id found for ticket {ticket_id} in TICKET_CARD_MESSAGES")
                logger.warning(f"Available keys: {list(TICKET_CARD_MESSAGES.keys())}")
        except Exception as e:
            logger.error(f"❌ Failed to update admin ticket card: {e}", exc_info=True)

        try:
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(_("buttons.suggestion"), callback_data="after_rate_suggestion"),
                    InlineKeyboardButton(_("buttons.review"), callback_data="after_rate_review")
                ],
                [
                    # ✅ CHANGED: Use "cancel" instead of "back" (cancel)
                    InlineKeyboardButton("❌ " + _("buttons.cancel"), callback_data="cancel_feedback_prompt"),
                    InlineKeyboardButton(f"{get_text('ui.home_emoji')} {_('buttons.main_menu')}", callback_data="user_home")
                ]
            ])

            await context.bot.send_message(
                chat_id=query.from_user.id,
                text=_("messages.invite_review"),
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Failed to send feedback prompt: {e}")
    else:
        await query.edit_message_text(_("messages.ticket_not_found"))

async def handle_thank_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Handle feedback thank you"""
    query = update.callback_query
    feedback_id = data.split(":")[1]

    feedback = feedback_service.thank_feedback(feedback_id)

    if feedback:
        feedback_type = feedback["type"]
        user_id = feedback["user_id"]

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✓ Thanked", callback_data="noop")]
        ])

        try:
            await query.edit_message_reply_markup(reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Failed to update button: {e}")

        try:
            if feedback_type == "suggestion":
                thank_msg = _("messages.thanks_suggestion")
            else:
                thank_msg = _("messages.thanks_review")

            await context.bot.send_message(
                chat_id=user_id,
                text=thank_msg
            )
            logger.info(f"Thanked user {user_id} for {feedback_type}")
        except Exception as e:
            logger.error(f"Failed to send thank message to user {user_id}: {e}")

        await query.answer("✅ User received thank you message")
    else:
        await query.answer("❌ Feedback not found")

async def handle_take_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Take ticket in progress"""
    ticket_id = data.split(":")[1]

    ticket = ticket_service.take_ticket(ticket_id, ADMIN_ID)

    if ticket:
        instruction_msg_id = INSTRUCTION_MESSAGES.get(ADMIN_ID)
        logger.info(f"🔍 DEBUG: INSTRUCTION_MESSAGES={INSTRUCTION_MESSAGES}")
        logger.info(f"🔍 DEBUG: Checking instruction_msg_id={instruction_msg_id} for ADMIN_ID={ADMIN_ID}")

        if instruction_msg_id:
            try:
                logger.info(f"🔍 DEBUG: Attempting to delete message_id={instruction_msg_id}")
                await context.bot.delete_message(
                    chat_id=ADMIN_ID,
                    message_id=instruction_msg_id
                )
                INSTRUCTION_MESSAGES.pop(ADMIN_ID, None)
                logger.info(f"✅ Deleted instruction message_id={instruction_msg_id}")
            except Exception as e:
                logger.error(f"❌ Failed to delete instruction message: {e}")
        else:
            logger.info(f"⚠️ No instruction message to delete")

        try:
            await context.bot.send_message(
                chat_id=ticket.user_id,
                text=_("messages.ticket_taken", ticket_id=ticket_id)
            )
        except Exception as e:
            logger.error(f"Failed to notify user: {e}")

        from handlers.user import send_or_update_ticket_card, TICKET_CARD_MESSAGES
        message_id = TICKET_CARD_MESSAGES.get(ticket_id) or update.callback_query.message.message_id
        TICKET_CARD_MESSAGES[ticket_id] = message_id
        await send_or_update_ticket_card(context, ticket_id, action="working", message_id=message_id)
    else:
        from utils.admin_screen import show_admin_screen
        await show_admin_screen(update, context, _("messages.ticket_not_found"), None)


async def handle_close_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Close ticket"""
    ticket_id = data.split(":")[1]
    ticket = ticket_service.close_ticket(ticket_id)

    if ticket:
        from handlers.user import send_or_update_ticket_card, TICKET_CARD_MESSAGES

        message_id = TICKET_CARD_MESSAGES.get(ticket_id) or update.callback_query.message.message_id
        TICKET_CARD_MESSAGES[ticket_id] = message_id

        logger.info(f"Saved message_id={message_id} for ticket {ticket_id}")

        # ✅ FIXED: Use action="closed" instead of action="working"
        await send_or_update_ticket_card(context, ticket_id, action="closed", message_id=message_id)

        try:
            await context.bot.send_message(
                chat_id=ticket.user_id,
                text=_("messages.rate_quality"),
                reply_markup=get_rating_keyboard(ticket_id)
            )
        except Exception as e:
            logger.error(f"Failed to send rating to user {ticket.user_id}: {e}")
    else:
        from utils.admin_screen import show_admin_screen
        await show_admin_screen(update, context, _("messages.ticket_not_found"), None)


async def handle_reply_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Start replying to ticket"""
    ticket_id = data.split(":")[1]

    instruction_msg_id = INSTRUCTION_MESSAGES.get(ADMIN_ID)
    logger.info(f"🔍 DEBUG: INSTRUCTION_MESSAGES={INSTRUCTION_MESSAGES}")
    logger.info(f"🔍 DEBUG: Checking instruction_msg_id={instruction_msg_id} for ADMIN_ID={ADMIN_ID}")

    if instruction_msg_id:
        try:
            logger.info(f"🔍 DEBUG: Attempting to delete message_id={instruction_msg_id}")
            await context.bot.delete_message(
                chat_id=ADMIN_ID,
                message_id=instruction_msg_id
            )
            INSTRUCTION_MESSAGES.pop(ADMIN_ID, None)
            logger.info(f"✅ Deleted instruction message_id={instruction_msg_id}")
        except Exception as e:
            logger.error(f"❌ Failed to delete instruction message: {e}")
    else:
        logger.info(f"⚠️ No instruction message to delete")

    ticket = None
    for t in data_manager.get_all_tickets():
        if t.id == ticket_id:
            ticket = t
            break

    if not ticket:
        await update.callback_query.answer("❌ Ticket not found", show_alert=True)
        return

    if ticket.status != "working":
        await update.callback_query.answer(
            "⚠️ First press '▶️ Take in progress'",
            show_alert=True
        )
        return

    context.user_data["state"] = "awaiting_reply"
    context.user_data["reply_ticket_id"] = ticket_id

    await update.callback_query.answer("✍️ Enter your reply")
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=_("messages.enter_reply")
    )

async def handle_inbox_filter(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Filter tickets"""
    filter_status = data.split(":")[1]

    context.user_data["inbox_filter"] = filter_status
    context.user_data["inbox_page"] = 0

    from handlers.admin import show_inbox
    await show_inbox(update, context)

async def handle_inbox_page(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Switch inbox page"""
    page = int(data.split(":")[1])

    context.user_data["inbox_page"] = page

    from handlers.admin import show_inbox
    await show_inbox(update, context)

async def handle_bans_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display banned users list"""
    banned = ban_manager.get_banned_list()

    if not banned:
        text = _("admin.no_bans")
    else:
        lines = ["📛 Banned users list:"]
        for user_id, reason in banned:
            lines.append(f"• ID: {user_id} - {reason}")
        text = "\n".join(lines)

    from utils.admin_screen import show_admin_screen
    await show_admin_screen(update, context, text, get_settings_keyboard())
