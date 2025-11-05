import os
import logging
from datetime import datetime, timedelta
from config import DATA_DIR, LOG_CLEANUP_ENABLED, LOG_RETENTION_DAYS, TIMEZONE

logger = logging.getLogger(__name__)

class LogService:
    def cleanup_old_logs(self):
        """Remove old logs if log cleanup is enabled"""
        if not LOG_CLEANUP_ENABLED:
            logger.debug("Log cleanup disabled")
            return

        try:
            cutoff = datetime.now(MOSCOW_TZ) - timedelta(days=LOG_RETENTION_DAYS)
            log_dir = DATA_DIR

            removed_count = 0
            for filename in os.listdir(log_dir):
                # Check if this is a log file
                if filename.startswith("bot.log") or filename.endswith(".log"):
                    file_path = os.path.join(log_dir, filename)

                    try:
                        mtime = datetime.fromtimestamp(os.path.getmtime(file_path), tz=MOSCOW_TZ)

                        if mtime < cutoff:
                            os.remove(file_path)
                            removed_count += 1
                            logger.info(f"Removed old log file: {filename} (modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')})")
                    except Exception as e:
                        logger.warning(f"Failed to remove log {filename}: {e}")

            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} old log file(s)")
            else:
                logger.debug(f"No logs older than {LOG_RETENTION_DAYS} days found")

        except Exception as e:
            logger.error(f"Log cleanup failed: {e}", exc_info=True)

# Global instance
log_service = LogService()
