import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_ID, PAGE_SIZE
from locales import get_text
from services.tickets import ticket_service
from services.bans import ban_manager
from storage.data_manager import data_manager
from storage.instruction_store import INSTRUCTION_MESSAGES, SEARCH_RESULT_MESSAGES, INBOX_MENU_MESSAGES
from utils.formatters import format_ticket_brief, format_ticket_card, format_ticket_preview
from utils.admin_screen import show_admin_screen, reset_admin_screen
from locales import _

logger = logging.getLogger(__name__)

async def inbox_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming tickets inbox"""
    user = update.effective_user

    if user.id != ADMIN_ID:
        return

    context.user_data["inbox_filter"] = "all"
    context.user_data["inbox_page"] = 0

    await show_inbox(update, context)

async def show_inbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display ticket list with pagination and filtering"""
    logger.info(f"🔍 DEBUG: PAGE_SIZE = {PAGE_SIZE}")

    filter_status = context.user_data.get("inbox_filter", "all")
    page = context.user_data.get("inbox_page", 0)

    # Get tickets
    if filter_status == "all":
        tickets = data_manager.get_all_tickets()
    else:
        tickets = data_manager.get_tickets_by_status(filter_status)

    # Sort by creation date (newest first)
    tickets = sorted(tickets, key=lambda t: t.created_at, reverse=True)

    # Pagination
    total_tickets = len(tickets)
    total_pages = max(1, (total_tickets + PAGE_SIZE - 1) // PAGE_SIZE)
    start_idx = page * PAGE_SIZE
    end_idx = min(start_idx + PAGE_SIZE, total_tickets)
    page_tickets = tickets[start_idx:end_idx]

    logger.info(f"🔍 DEBUG: total_tickets={total_tickets}, page={page}, start_idx={start_idx}, end_idx={end_idx}, showing={len(page_tickets)}")

    # Translate filter status names
    filter_names = {
        "all": _("inbox.filter_all"),
        "new": _("inbox.filter_new"),
        "working": _("inbox.filter_working"),
        "done": _("inbox.filter_done")
    }
    filter_display = filter_names.get(filter_status, filter_status)

    # Format text
    if not page_tickets:
        text = f"📥 **{_('inbox.title')}** ({filter_display})\n\n{_('inbox.no_tickets')}"
    else:
        header = f"📥 **{_('inbox.title')}** ({filter_display}) | {_('inbox.page', page=page+1, total=total_pages)}\n\n"
        previews = [format_ticket_preview(t) for t in page_tickets]
        text = header + "\n".join(previews)

    # Filter buttons
    filter_row = []
    for flt in ["all", "new", "working", "done"]:
        label = filter_names[flt]
        prefix = "✅ " if flt == filter_status else ""
        filter_row.append(
            InlineKeyboardButton(
                f"{prefix}{label}",
                callback_data=f"inbox_filter:{flt}"
            )
        )

    # Pagination buttons
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(f"◀️ {_('buttons.back')}", callback_data=f"inbox_page:{page-1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(f"{_('buttons.forward')} ▶️", callback_data=f"inbox_page:{page+1}"))

    # Search button (with localization)
    search_row = [InlineKeyboardButton(_("search.button"), callback_data="search_ticket_start")]

    # Main menu button
    home_row = [InlineKeyboardButton(f"{get_text('ui.home_emoji')} {_('buttons.main_menu')}", callback_data="admin_home")]

    # Build keyboard
    keyboard_rows = [filter_row]
    if nav_row:
        keyboard_rows.append(nav_row)
    keyboard_rows.append(search_row)
    keyboard_rows.append(home_row)

    keyboard = InlineKeyboardMarkup(keyboard_rows)

    # 🗑️ Delete old inbox menu message (if exists)
    old_inbox_msg_id = INBOX_MENU_MESSAGES.get(ADMIN_ID)
    if old_inbox_msg_id:
        try:
            await context.bot.delete_message(chat_id=ADMIN_ID, message_id=old_inbox_msg_id)
            logger.info(f"✅ Deleted old inbox menu: {old_inbox_msg_id}")
        except Exception as e:
            logger.error(f"Failed to delete old inbox menu: {e}")

    # ✨ Send NEW inbox menu
    msg = await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=text,
        reply_markup=keyboard
    )

    # 💾 Save message_id of new inbox menu
    INBOX_MENU_MESSAGES[ADMIN_ID] = msg.message_id
    logger.info(f"✅ Saved new inbox menu: {msg.message_id}")

async def show_ticket_card(update: Update, context: ContextTypes.DEFAULT_TYPE, ticket_id: str):
    """Display full ticket card"""
    ticket = ticket_service.get_ticket(ticket_id)

    if not ticket:
        await show_admin_screen(update, context, _("messages.ticket_not_found"), None)
        return

    text = format_ticket_card(ticket)

    # Action buttons
    actions = []

    if ticket.status == "new":
        actions.append([InlineKeyboardButton("✅ Take in progress", callback_data=f"take:{ticket_id}")])
    elif ticket.status == "working":
        actions.append([InlineKeyboardButton("💬 Reply", callback_data=f"reply:{ticket_id}")])
        actions.append([InlineKeyboardButton("✅ Close", callback_data=f"close:{ticket_id}")])

    actions.append([InlineKeyboardButton(f"◀️ {_('buttons.back')}", callback_data="admin_inbox")])
    actions.append([InlineKeyboardButton(f"{get_text('ui.home_emoji')} {_('buttons.main_menu')}", callback_data="admin_home")])

    keyboard = InlineKeyboardMarkup(actions)

    await show_admin_screen(update, context, text, keyboard)

async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display statistics"""
    user = update.effective_user

    if user.id != ADMIN_ID:
        return

    stats = data_manager.get_stats()
    banned_count = len(ban_manager.get_banned_list())
    stats["banned_count"] = banned_count

    text = _("admin.stats_text", **stats)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{get_text('ui.home_emoji')} {_('buttons.main_menu')}", callback_data="admin_home")]
    ])

    await show_admin_screen(update, context, text, keyboard)

async def settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display settings"""
    user = update.effective_user

    if user.id != ADMIN_ID:
        return

    from utils.keyboards import get_settings_keyboard

    await show_admin_screen(
        update, context,
        _("admin.settings"),
        get_settings_keyboard()
    )

async def home_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display admin main menu"""
    user = update.effective_user

    if user.id != ADMIN_ID:
        return

    from utils.keyboards import get_admin_main_keyboard

    await show_admin_screen(
        update, context,
        _("admin.welcome"),
        get_admin_main_keyboard()
    )

async def admin_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages from admin"""
    user = update.effective_user
    text = update.message.text

    if user.id != ADMIN_ID:
        return

    state = context.user_data.get("state")
    logger.info(f"🔍 DEBUG admin_text_handler: user_id={user.id}, state={state}, text={text[:20]}")

    # ========== NEW: Search ticket by ID ==========
    if state == "search_ticket_input":
        search_input = text.strip().replace("#", "")
        tickets_list = data_manager.get_all_tickets()

        # Find ticket by ID match
        found_ticket = None
        for ticket in tickets_list:
            if search_input in ticket.id:
                found_ticket = ticket
                break

        context.user_data["state"] = None

        # 🗑️ Delete search menu message (ticket number input prompt)
        search_menu_msg_id = context.user_data.get("search_menu_msg_id")
        if search_menu_msg_id:
            try:
                await context.bot.delete_message(chat_id=ADMIN_ID, message_id=search_menu_msg_id)
                logger.info(f"✅ Deleted search menu message_id={search_menu_msg_id}")
            except Exception as e:
                logger.error(f"Failed to delete search menu: {e}")
            context.user_data.pop("search_menu_msg_id", None)

        # 🗑️ Delete user's search input message
        try:
            await update.message.delete()
        except Exception as e:
            logger.error(f"Failed to delete search prompt: {e}")

        # 🗑️ Delete previous search result message (if exists)
        old_msg_id = SEARCH_RESULT_MESSAGES.get(ADMIN_ID)
        if old_msg_id:
            try:
                await context.bot.delete_message(chat_id=ADMIN_ID, message_id=old_msg_id)
            except Exception as e:
                logger.error(f"Failed to delete previous search result: {e}")

        if not found_ticket:
            # ❌ Not found - send new message
            msg = await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=_("search.not_found", ticket_number=search_input),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(text=_("search.button_new_search"), callback_data="search_ticket_start"),
                    InlineKeyboardButton(text=_("search.button_cancel"), callback_data="admin_inbox")
                ]])
            )
            SEARCH_RESULT_MESSAGES[ADMIN_ID] = msg.message_id
            return

        # ✅ Found - send message with ticket card
        msg = await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=format_ticket_preview(found_ticket),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(text=_("search.button_open"), callback_data=f"ticket:{found_ticket.id}")],
                [
                    InlineKeyboardButton(text=_("search.button_new_search"), callback_data="search_ticket_start"),
                    InlineKeyboardButton(text=_("search.button_cancel"), callback_data="admin_inbox")
                ]
            ])
        )
        SEARCH_RESULT_MESSAGES[ADMIN_ID] = msg.message_id
        return

    # ========== Previous logic ==========
    if state == "awaiting_ban_user_id":
        try:
            user_id = int(text.strip())
            context.user_data["ban_user_id"] = user_id
            context.user_data["state"] = "awaiting_ban_reason"

            await update.message.reply_text(_("admin.enter_ban_reason"))
        except ValueError:
            await update.message.reply_text("Invalid ID format")

    elif state == "awaiting_ban_reason":
        user_id = context.user_data.get("ban_user_id")
        if user_id:
            ban_manager.ban_user(user_id, text)
            context.user_data["state"] = None

            await update.message.reply_text(
                _("admin.user_banned", user_id=user_id, reason=text)
            )

    elif state == "awaiting_unban_user_id":
        try:
            user_id = int(text.strip())
            ban_manager.unban_user(user_id)
            context.user_data["state"] = None

            await update.message.reply_text(
                _("admin.user_unbanned", user_id=user_id)
            )
        except ValueError:
            await update.message.reply_text("Invalid ID format")

    elif state == "awaiting_reply":
        from handlers.user import handle_admin_reply
        await handle_admin_reply(update, context, text)

    else:
        msg = await update.message.reply_text(
            "⚠️ To reply to a ticket:\n"
            "1. Press '▶️ Take in progress'\n"
            "2. Then press '💬 Reply'\n"
            "3. Send your message"
        )
        INSTRUCTION_MESSAGES[ADMIN_ID] = msg.message_id
        logger.info(f"Saved instruction message_id={msg.message_id} for admin {ADMIN_ID}")

# ========================================
# ALIASES FOR main.py COMPATIBILITY
# ========================================
admin_inbox = inbox_handler
admin_stats = stats_handler
admin_settings = settings_handler
admin_home = home_handler
