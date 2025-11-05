import os
import shutil
import logging
import tarfile
from datetime import datetime, timedelta
from typing import List, Tuple
from config import (
    BACKUP_DIR, DATA_DIR, DATA_FILE, BANNED_FILE,
    BACKUP_RETENTION_DAYS, BACKUP_FILE_PREFIX,
    BACKUP_ARCHIVE_TAR, TIMEZONE,
    BACKUP_FULL_PROJECT, BACKUP_FILE_LIST,
    BACKUP_EXCLUDE_PATTERNS,
    BACKUP_SEND_TO_TELEGRAM, BACKUP_MAX_SIZE_MB,
    BACKUP_ENABLED, BACKUP_SOURCE_DIR, LOG_LEVEL
)

logger = logging.getLogger(__name__)

class BackupService:
    def create_backup(self) -> Tuple[str, dict]:
        """Create backup. Returns tuple (backup_path, backup_info)"""
        if not BACKUP_ENABLED:
            logger.info("Backup is disabled by config")
            return "", {}

        try:
            timestamp = datetime.now(TIMEZONE).strftime("%Y%m%d_%H%M%S")
            backup_name = f"{BACKUP_FILE_PREFIX}{timestamp}"

            if BACKUP_FULL_PROJECT:
                return self._create_full_backup(backup_name)
            else:
                return self._create_files_backup(backup_name)

        except Exception as e:
            logger.error(f"Backup creation failed: {e}", exc_info=True)
            raise

    def _should_exclude(self, path_str: str) -> bool:
        """Check exclusion patterns"""
        filename = path_str.split('/')[-1]

        for pattern in BACKUP_EXCLUDE_PATTERNS:
            # *.log, *.pyc → file extension
            if pattern.startswith("*."):
                if filename.endswith(pattern[1:]):
                    if LOG_LEVEL == "DEBUG":
                        logger.info(f"EXCLUDING: {path_str} (ext: {pattern})")
                    return True

            # backups, venv, __pycache__ → directory in path
            elif "/" + pattern + "/" in "/" + path_str + "/" or path_str.startswith(pattern + "/") or path_str == pattern:
                if LOG_LEVEL == "DEBUG":
                    logger.info(f"EXCLUDING: {path_str} (dir: {pattern})")
                return True

            # bot.log → exact name or starts with pattern (only if pattern > 1 char)
            elif filename == pattern or (len(pattern) > 1 and filename.startswith(pattern)):
                if LOG_LEVEL == "DEBUG":
                    logger.info(f"EXCLUDING: {path_str} (name: {pattern})")
                return True

        return False

    def _format_size(self, size_bytes: int) -> str:
        """Format file size"""
        if size_bytes < 1024:
            return f"{size_bytes}B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f}KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f}MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f}GB"

    def _create_full_backup(self, backup_name: str) -> Tuple[str, dict]:
        """Create full project backup"""
        backup_path = os.path.join(BACKUP_DIR, f"{backup_name}.tar.gz")
        project_root = os.path.abspath(BACKUP_SOURCE_DIR)

        # Diagnostic logging
        logger.info(f"Backup source directory: {project_root}")
        logger.info(f"Directory exists: {os.path.exists(project_root)}")
        logger.info(f"Exclude patterns: {BACKUP_EXCLUDE_PATTERNS}")

        if os.path.exists(project_root):
            files_count = sum(len(files) for _, _, files in os.walk(project_root))
            logger.info(f"Total files in source directory: {files_count}")
        else:
            logger.error(f"Backup source directory does not exist: {project_root}")
            raise FileNotFoundError(f"Backup source directory not found: {project_root}")

        excluded_count = 0
        included_count = 0

        def filter_files(tarinfo):
            """Filter for excluding files and directories"""
            nonlocal excluded_count, included_count

            if self._should_exclude(tarinfo.name):
                excluded_count += 1
                return None

            if LOG_LEVEL == "DEBUG":
                logger.debug(f"INCLUDING: {tarinfo.name}")
            included_count += 1
            return tarinfo

        with tarfile.open(backup_path, "w:gz") as tar:
            tar.add(project_root, arcname=os.path.basename(project_root), filter=filter_files)
            files_added = len(tar.getmembers())

        logger.info(f"Full backup created: {backup_path}")
        logger.info(f"Files/dirs EXCLUDED: {excluded_count}")
        logger.info(f"Files/dirs INCLUDED: {included_count}")
        logger.info(f"Files/dirs added to backup: {files_added}")

        backup_size = os.path.getsize(backup_path)
        size_formatted = self._format_size(backup_size)
        logger.info(f"Backup file size: {backup_size} bytes ({size_formatted})")

        # Format backup info
        backup_info = {
            "type": "full",
            "source_dir": project_root,
            "excluded_patterns": ", ".join(BACKUP_EXCLUDE_PATTERNS),
            "files_in_archive": files_added,
            "size_bytes": backup_size,
            "size_formatted": size_formatted,
            "size_mb": backup_size / (1024 * 1024)  # For compatibility
        }

        return backup_path, backup_info

    def _create_files_backup(self, backup_name: str) -> Tuple[str, dict]:
        """Create backup of selected files"""
        backup_path = os.path.join(BACKUP_DIR, f"{backup_name}.tar.gz")

        logger.info(f"Creating backup of selected files: {BACKUP_FILE_LIST}")

        files_added = 0
        with tarfile.open(backup_path, "w:gz") as tar:
            for filename in BACKUP_FILE_LIST:
                file_path = os.path.join(DATA_DIR, filename)
                if os.path.isfile(file_path):
                    tar.add(file_path, arcname=filename)
                    files_added += 1
                    logger.debug(f"Added to backup: {filename}")
                else:
                    logger.warning(f"File {file_path} not found and skipped")

        logger.info(f"Files backup created: {backup_path}")
        logger.info(f"Files added to backup: {files_added}")

        backup_size = os.path.getsize(backup_path)
        size_formatted = self._format_size(backup_size)
        logger.info(f"Backup file size: {backup_size} bytes ({size_formatted})")

        # Format backup info
        backup_info = {
            "type": "files",
            "files": ", ".join(BACKUP_FILE_LIST),
            "files_in_archive": files_added,
            "size_bytes": backup_size,
            "size_formatted": size_formatted,
            "size_mb": backup_size / (1024 * 1024)  # For compatibility
        }

        return backup_path, backup_info

    def get_backup_size_mb(self, backup_path: str) -> float:
        """Get backup size in MB"""
        if os.path.isfile(backup_path):
            return os.path.getsize(backup_path) / (1024 * 1024)
        elif os.path.isdir(backup_path):
            total = sum(os.path.getsize(os.path.join(dirpath, filename))
                       for dirpath, _, filenames in os.walk(backup_path)
                       for filename in filenames)
            return total / (1024 * 1024)
        return 0

    def cleanup_old_backups(self):
        """Remove old backups"""
        try:
            cutoff = datetime.now(TIMEZONE) - timedelta(days=BACKUP_RETENTION_DAYS)

            for item in os.listdir(BACKUP_DIR):
                item_path = os.path.join(BACKUP_DIR, item)

                if not item.startswith(BACKUP_FILE_PREFIX):
                    continue

                mtime = datetime.fromtimestamp(os.path.getmtime(item_path), tz=TIMEZONE)

                if mtime < cutoff:
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    logger.info(f"Removed old backup: {item}")
        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}", exc_info=True)

    def list_backups(self) -> List[str]:
        """Get list of backups"""
        try:
            backups = []
            for item in os.listdir(BACKUP_DIR):
                if item.startswith(BACKUP_FILE_PREFIX):
                    backups.append(item)
            return sorted(backups, reverse=True)
        except Exception as e:
            logger.error(f"Failed to list backups: {e}", exc_info=True)
            return []

# Global instance
backup_service = BackupService()
