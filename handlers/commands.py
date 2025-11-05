import logging
from telegram import Update
from telegram.ext import ContextTypes
from handlers.user import ask_question_handler, suggestion_handler, review_handler
from handlers.admin import inbox_handler, stats_handler, settings_handler

logger = logging.getLogger(__name__)

async def question_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /question"""
    await ask_question_handler(update, context)

async def suggestion_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /suggestion"""
    await suggestion_handler(update, context)

async def review_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /review"""
    await review_handler(update, context)

async def inbox_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /inbox"""
    await inbox_handler(update, context)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /stats"""
    await stats_handler(update, context)

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /settings"""
    await settings_handler(update, context)
