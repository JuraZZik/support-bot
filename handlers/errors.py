import logging
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest, RetryAfter, TimedOut, NetworkError
from services.alerts import alert_service
from config import RETRY_ATTEMPTS, RETRY_BACKOFF_SEC

logger = logging.getLogger(__name__)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Global error handler"""
    try:
        raise context.error
    except RetryAfter as e:
        logger.warning(f"RetryAfter: {e.retry_after}s")
        await asyncio.sleep(e.retry_after)
    except TimedOut:
        logger.warning("Request timed out")
    except NetworkError as e:
        logger.error(f"Network error: {e}", exc_info=True)
    except BadRequest as e:
        logger.error(f"Bad request: {e}", exc_info=True)
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "⚠️ An error occurred while processing the request."
                )
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)

        # Send error alert (use send_alert instead of send_error_alert)
        error_msg = f"{type(e).__name__}: {str(e)}"
        try:
            await alert_service.send_alert(f"🔴 **Bot Error**\n\n{error_msg}")
        except Exception as alert_error:
            logger.error(f"Failed to send error alert: {alert_error}")

        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ An unexpected error occurred. Administrator has been notified."
                )
            except Exception:
                pass

async def retry_on_error(func, *args, **kwargs):
    """Retry function execution on error with exponential backoff"""
    for attempt in range(RETRY_ATTEMPTS):
        try:
            return await func(*args, **kwargs)
        except (TimedOut, NetworkError) as e:
            if attempt < RETRY_ATTEMPTS - 1:
                wait_time = RETRY_BACKOFF_SEC * (2 ** attempt)
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"All {RETRY_ATTEMPTS} attempts failed")
                raise
        except Exception:
            raise
