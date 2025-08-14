"""Restriction mode management service."""

import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytz

from src.aibot.logger import logger

if TYPE_CHECKING:
    from pytz.tzinfo import BaseTzInfo


class RestrictionService:
    """Service for managing instruction creation restriction mode.

    This service uses a simple file-based approach to manage restriction state.
    The presence of a lock file indicates restriction mode is active.

    """

    _instance: "RestrictionService | None" = None
    _lock_file_path: Path
    _timezone: "BaseTzInfo"

    def __new__(cls) -> "RestrictionService":
        """Create or return the singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.__dict__["_lock_file_path"] = Path("resources/restriction_mode.lock")
            tz_name = os.getenv("TIMEZONE", "Asia/Tokyo")
            cls._instance.__dict__["_timezone"] = pytz.timezone(tz_name)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "RestrictionService":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        """Initialize the service."""
        if hasattr(self, "_initialized"):
            return
        self._ensure_resources_directory()
        self._initialized = True

    def _ensure_resources_directory(self) -> None:
        """Ensure the resources directory exists."""
        self._lock_file_path.parent.mkdir(parents=True, exist_ok=True)

    def is_restricted(self) -> bool:
        """Check if restriction mode is active.

        Returns
        -------
        bool
            True if restriction mode is active, False otherwise.

        """
        return self._lock_file_path.exists()

    def enable_restriction(self, user_id: int) -> dict[str, Any]:
        """Enable restriction mode.

        Parameters
        ----------
        user_id : int
            The ID of the user enabling restriction mode.

        Returns
        -------
        dict[str, Any]
            Result dictionary with success status and message.

        """
        try:
            if self.is_restricted():
                return {
                    "success": True,
                    "message": "制限モードは既に有効です。",
                    "was_already_active": True,
                }

            # Create lock file with metadata
            lock_content = (
                f"Restricted by user ID: {user_id}\nTimestamp: {self._get_current_timestamp()}\n"
            )
            self._lock_file_path.write_text(lock_content, encoding="utf-8")

        except Exception as e:
            logger.exception("Failed to enable restriction mode: %s", e)
            return {
                "success": False,
                "message": "制限モードの有効化に失敗しました。",
            }
        logger.info("Restriction mode enabled by user %d", user_id)
        return {
            "success": True,
            "message": "制限モードを有効にしました。カスタム指示の作成・変更ができません。",
            "was_already_active": False,
        }

    def disable_restriction(self, user_id: int) -> dict[str, Any]:
        """Disable restriction mode.

        Parameters
        ----------
        user_id : int
            The ID of the user disabling restriction mode.

        Returns
        -------
        dict[str, Any]
            Result dictionary with success status and message.

        """
        try:
            if not self.is_restricted():
                return {
                    "success": True,
                    "message": "制限モードは既に無効です。",
                    "was_already_inactive": True,
                }

            # Remove lock file
            self._lock_file_path.unlink()

        except Exception as e:
            logger.exception("Failed to disable restriction mode: %s", e)
            return {
                "success": False,
                "message": "制限モードの無効化に失敗しました。",
            }
        logger.info("Restriction mode disabled by user %d", user_id)
        return {
            "success": True,
            "message": "制限モードを無効にしました。カスタム指示の作成・変更が可能です。",
            "was_already_inactive": False,
        }

    def get_restriction_status(self) -> dict[str, Any]:
        """Get current restriction mode status with details.

        Returns
        -------
        dict[str, Any]
            Dictionary containing restriction status and metadata.

        """
        try:
            is_restricted = self.is_restricted()
            status = {
                "is_restricted": is_restricted,
                "status_message": "制限モード有効" if is_restricted else "制限モード無効",
            }

            if is_restricted and self._lock_file_path.exists():
                try:
                    lock_content = self._lock_file_path.read_text(encoding="utf-8")
                    status["lock_details"] = lock_content.strip()
                except Exception as e:
                    logger.warning("Failed to read lock file details: %s", e)
                    status["lock_details"] = "詳細不明"

            return status  # noqa: TRY300

        except Exception as e:
            logger.exception("Failed to get restriction status: %s", e)
            return {
                "is_restricted": False,
                "status_message": "ステータス取得エラー",
                "error": str(e),
            }

    def _get_current_timestamp(self) -> str:
        """Get current timestamp as string.

        Returns
        -------
        str
            Current timestamp in ISO format.

        """
        return datetime.now(self._timezone).isoformat()
