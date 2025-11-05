#!/usr/bin/env python3
"""
Task scheduler service
Manages periodic tasks (backups, log cleanup, etc.)
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for managing periodic tasks"""

    def __init__(self):
        self.tasks = []
        self.running = False

    async def start(self):
        """Start scheduler"""
        if self.running:
            logger.warning("Scheduler already running")
            return

        self.running = True
        logger.info("Scheduler service started")

    async def stop(self):
        """Stop scheduler"""
        if not self.running:
            return

        self.running = False

        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self.tasks.clear()
        logger.info("Scheduler service stopped")


# Global instance
scheduler_service = SchedulerService()
