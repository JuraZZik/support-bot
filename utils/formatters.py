from datetime import datetime
from config import TIMEZONE

def format_ticket_brief(ticket) -> str:
    """Brief ticket preview for list (single line)"""
    status_emoji = {
        "new": "🆕",
        "working": "⏳",
        "done": "✅"
    }.get(ticket.status, "❓")

    # Show username and ID
    if ticket.username:
        username = f"@{ticket.username} (ID:{ticket.user_id})"
    else:
        username = f"ID:{ticket.user_id}"

    # First 30 characters of message
    try:
        if ticket.messages:
            first_msg = ticket.messages[0]
            # Check type - can be Message object
            if hasattr(first_msg, 'text'):
                msg_preview = first_msg.text[:30] + "..."
            elif isinstance(first_msg, dict):
                msg_preview = first_msg.get("text", "")[:30] + "..."
            else:
                msg_preview = str(first_msg)[:30] + "..."
        else:
            msg_preview = "No messages"
    except Exception:
        msg_preview = "No messages"

    return f"{status_emoji} {ticket.id} | {username} | {msg_preview}"

def format_ticket_card(ticket) -> str:
    """Full ticket card with message history"""
    from config import TICKET_HISTORY_LIMIT  # Import here

    status_names = {
        "new": "New",
        "working": "In progress",
        "done": "Closed"
    }

    # Show username and ID together
    if ticket.username:
        username = f"@{ticket.username} (ID: {ticket.user_id})"
    else:
        username = f"ID: {ticket.user_id}"

    status = status_names.get(ticket.status, ticket.status)

    created_str = ticket.created_at.strftime("%d.%m.%Y %H:%M")

    lines = [
        f"🎫 Ticket: {ticket.id}",
        f"👤 From: {username}",
        f"📊 Status: {status}",
        f"📅 Created: {created_str}",
    ]

    # Add rating if exists
    if hasattr(ticket, 'rating') and ticket.rating:
        rating_texts = {
            "excellent": "⭐⭐⭐ Excellent",
            "good": "⭐⭐ Good",
            "ok": "⭐ Okay"
        }
        rating_display = rating_texts.get(ticket.rating, ticket.rating)
        lines.append(f"⭐ Rating: {rating_display}")

    lines.extend(["", "📝 Message history:", ""])

    # Message history with limit
    if ticket.messages:
        # If TICKET_HISTORY_LIMIT > 0, show last N messages
        messages_to_show = ticket.messages[-TICKET_HISTORY_LIMIT:] if TICKET_HISTORY_LIMIT > 0 else ticket.messages

        for msg in messages_to_show:
            try:
                # Handle Message object
                if hasattr(msg, 'sender'):
                    sender = "👤 User" if msg.sender == "user" else "🛠 Support"
                    timestamp = msg.timestamp if hasattr(msg, 'timestamp') else datetime.now()
                    if hasattr(timestamp, 'strftime'):
                        time_str = timestamp.strftime("%H:%M")
                    else:
                        time_str = str(timestamp)
                    text = msg.text if hasattr(msg, 'text') else str(msg)

                    lines.append(f"{sender} [{time_str}]:")
                    lines.append(f"{text}")
                    lines.append("")
                # Handle dict
                elif isinstance(msg, dict):
                    sender = "👤 User" if msg.get("sender") == "user" else "🛠 Support"
                    timestamp = msg.get("timestamp", datetime.now())
                    if hasattr(timestamp, 'strftime'):
                        time_str = timestamp.strftime("%H:%M")
                    else:
                        time_str = str(timestamp)
                    text = msg.get("text", "")

                    lines.append(f"{sender} [{time_str}]:")
                    lines.append(f"{text}")
                    lines.append("")
                else:
                    lines.append(f"• {str(msg)}")
                    lines.append("")
            except Exception as e:
                lines.append(f"• [Display error]")
                lines.append("")
    else:
        lines.append("No messages")

    return "\n".join(lines)

def format_ticket_preview(ticket) -> str:
    """Ticket preview for inbox list (multi-line)"""
    status_emoji = {
        "new": "🆕",
        "working": "⏳",
        "done": "✅"
    }.get(ticket.status, "❓")

    # Show username and ID
    if ticket.username:
        username = f"@{ticket.username} (ID:{ticket.user_id})"
    else:
        username = f"ID:{ticket.user_id}"

    created_str = ticket.created_at.strftime("%d.%m.%Y %H:%M")

    # Safe preview retrieval
    try:
        if ticket.messages:
            first_msg = ticket.messages[0]
            if hasattr(first_msg, 'text'):
                msg_preview = first_msg.text[:100]
            elif isinstance(first_msg, dict):
                msg_preview = first_msg.get("text", "")[:100]
            else:
                msg_preview = str(first_msg)[:100]
        else:
            msg_preview = "No messages"
    except Exception:
        msg_preview = "No messages"

    return (
        f"{status_emoji} {ticket.id}\n"
        f"👤 {username}\n"
        f"📅 {created_str}\n"
        f"💬 {msg_preview}...\n"
    )
