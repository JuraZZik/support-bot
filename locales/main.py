#!/usr/bin/env python3
"""
Telegram Support Bot - Main Entry Point
Support system for users via Telegram bot
"""
import asyncio
import logging
import os
from telegram.ext import ApplicationBuilder
from telegram import Update

from config import (
    TOKEN, ADMIN_ID, BOT_API_BASE, REQUEST_TIMEOUT,
    post_init, post_shutdown, DEFAULT_LOCALE
)
from locales import load_locales, set_locale, get_text
from handlers import register_all_handlers

logger = logging.getLogger(__name__)

# Application instance (global)
application = None


async def run_bot():
    """Start bot with polling"""
    global application

    try:
        async with application:
            await application.start()

            # Configure bot menu
            logger.info("Setting up bot menu...")
            try:
                from utils.menu import setup_bot_menu
                await setup_bot_menu(application)
                logger.info("Bot menu configured successfully")
            except Exception as e:
                logger.error(f"Failed to setup bot menu: {e}", exc_info=True)

            # Remove shutdown flag
            shutdown_flag = os.path.join(os.path.dirname(__file__), ".shutdown")
            try:
                if os.path.exists(shutdown_flag):
                    os.remove(shutdown_flag)
                    logger.debug("Shutdown flag removed")
            except OSError as e:
                logger.warning(f"Could not remove shutdown flag: {e}")

            # Configure alert service
            try:
                from services.alerts import alert_service
                alert_service.set_bot(application.bot)
                logger.info("Alert service bot configured")

                # Send startup alert
                await alert_service.send_startup_alert()
                logger.info("Startup alert sent successfully")
            except Exception as e:
                logger.error(f"Failed to setup alerts: {e}", exc_info=True)

            logger.info("Bot is running...")
            print(get_text("alerts.bot_started"))

            # Start polling
            await application.updater.start_polling(
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES
            )

            # Wait for shutdown signal
            stop_event = asyncio.Event()
            
            # Add signal handlers
            loop = asyncio.get_running_loop()
            
            def signal_handler(sig):
                """Sync signal handler for loop signals"""
                asyncio.create_task(shutdown_handler(sig, stop_event))
            
            loop.add_signal_handler(2, signal_handler, 2)   # SIGINT
            loop.add_signal_handler(15, signal_handler, 15)  # SIGTERM

            # Wait for stop event
            await stop_event.wait()
            logger.info("Stop event received, shutting down...")

            # Stop polling
            await application.updater.stop()
            logger.info("Polling stopped")

    except Exception as e:
        logger.critical(f"Fatal error in run_bot: {e}", exc_info=True)
        raise
    finally:
        try:
            await application.stop()
            logger.info("Application stopped")
        except Exception as e:
            logger.error(f"Error stopping application: {e}", exc_info=True)


async def shutdown_handler(sig, stop_event):
    """Handle shutdown signal"""
    logger.info(f"Received signal {sig}, stopping bot...")

    # Send shutdown alert
    try:
        from services.alerts import alert_service
        await alert_service.send_shutdown_alert()
        logger.info("Shutdown alert sent")
    except Exception as e:
        logger.error(f"Failed to send shutdown alert: {e}", exc_info=True)

    # Save data
    try:
        from storage.data_manager import data_manager
        data_manager.save()
        logger.info("Data saved")
    except Exception as e:
        logger.error(f"Failed to save data: {e}", exc_info=True)

    # Set stop event
    stop_event.set()


async def cleanup():
    """Clean up resources"""
    shutdown_flag = os.path.join(os.path.dirname(__file__), ".shutdown")
    try:
        with open(shutdown_flag, "w") as f:
            f.write("shutdown")
        logger.info("Shutdown flag created")
    except OSError as e:
        logger.warning(f"Could not create shutdown flag: {e}")


def main():
    """Main entry point"""
    global application

    # Load locales
    load_locales()
    set_locale(DEFAULT_LOCALE)

    # Build application
    application = (
        ApplicationBuilder()
        .token(TOKEN)
        .base_url(BOT_API_BASE + "/bot")
        .connect_timeout(REQUEST_TIMEOUT)
        .read_timeout(REQUEST_TIMEOUT)
        .write_timeout(REQUEST_TIMEOUT)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Register handlers
    register_all_handlers(application)

    # Run bot
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.critical(f"Unexpected error: {e}", exc_info=True)
    finally:
        try:
            asyncio.run(cleanup())
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)


if __name__ == "__main__":
    main()
