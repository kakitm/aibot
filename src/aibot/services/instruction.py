import contextlib
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from src.aibot.infrastructure.dao.instruction import InstructionDAO
from src.aibot.logger import logger

# Configuration constants
PREVIEW_LENGTH = 20
MAX_INSTRUCTION_FILES = 100
DISCORD_SELECT_LIMIT = 25


class InstructionService:
    """System instruction management service."""

    _instance: "InstructionService | None" = None
    _instructions_dir: Path
    _static_instruction_file: Path

    def __new__(cls) -> "InstructionService":
        """Create or return the singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.__dict__["_instructions_dir"] = Path("resources/instructions")
            cls._instance.__dict__["_static_instruction_file"] = Path("resources/instructions/instructions.yml")
        return cls._instance

    @classmethod
    def get_instance(cls) -> "InstructionService":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        """Initialize the service."""
        if hasattr(self, "_initialized"):
            return
        self._dao = InstructionDAO()
        self._gen_dir = self._instructions_dir / "gen"
        self._ensure_directory()
        self._initialized = True

    def _ensure_directory(self) -> None:
        """Ensure the generated instructions directory exists."""
        self._gen_dir.mkdir(parents=True, exist_ok=True)

    def _generate_filename(self) -> str:
        """Generate a timestamped filename."""
        now = datetime.now(self._dao.TIMEZONE)
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        return f"{timestamp}.txt"

    def _cleanup_old_files(self) -> int:
        """Remove old instruction files if count exceeds MAX_INSTRUCTION_FILES."""
        files = self._get_instruction_files()
        removed_count = 0

        if len(files) > MAX_INSTRUCTION_FILES:
            files_to_remove = files[MAX_INSTRUCTION_FILES:]
            for file_path in files_to_remove:
                try:
                    file_path.unlink()
                    removed_count += 1
                except OSError as e:
                    logger.error("Failed to remove file %s: %s", file_path.name, e)

        return removed_count

    def _get_instruction_files(self) -> list[Path]:
        """Get all instruction txt files, sorted by modification time (newest first)."""
        if not self._gen_dir.exists():
            return []

        txt_files = list(self._gen_dir.glob("*.txt"))
        return sorted(txt_files, key=lambda f: f.stat().st_mtime, reverse=True)

    def load_static_instruction(self, command_name: str) -> str | None:
        """Load static instructions from YAML file."""
        if not self._static_instruction_file.exists():
            logger.warning("Static instruction file not found: %s", self._static_instruction_file)
            return None

        try:
            with self._static_instruction_file.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return data.get(command_name) if data else None
        except Exception as e:
            logger.error("Failed to load static instructions: %s", e)
            return None

    async def create_and_activate_instruction(
        self,
        content: str,
        created_by: int,
    ) -> dict[str, Any]:
        """Create a new instruction and activate it."""
        if not content or not content.strip():
            return {"success": False, "message": "ファイルの内容が空です。"}

        try:
            # Generate filename and save to file
            filename = self._generate_filename()
            file_path = self._gen_dir / filename

            with file_path.open("w", encoding="utf-8") as f:
                f.write(content.strip())

            # Cleanup old files
            removed_count = self._cleanup_old_files()
            if removed_count > 0:
                logger.info("Auto-cleanup removed %d old files", removed_count)

            # Save to database
            instruction_id = await self._dao.save_instruction(
                instruction=content.strip(),
                file_path=filename,
                created_by=created_by,
            )

            if instruction_id is None:
                # Cleanup file if database save failed
                with contextlib.suppress(Exception):
                    file_path.unlink()
                return {"success": False, "message": "データベースへの保存に失敗しました。"}

            # Activate the new instruction
            success = await self._dao.activate_instruction(instruction_id)
            if not success:
                return {"success": False, "message": "システム指示の有効化に失敗しました。"}

            logger.info("Created and activated instruction with ID %d", instruction_id)
        except Exception as e:
            logger.exception("Error creating and activating instruction: %s", e)
            return {"success": False, "message": "システム指示の作成中にエラーが発生しました。"}
        return {
            "success": True,
            "instruction_id": instruction_id,
            "filename": filename,
            "message": "システム指示が正常に作成・設定されました。",
        }

    async def reactivate_instruction_by_filename(self, filename: str) -> dict[str, Any]:
        """Reactivate an existing instruction by its filename."""
        file_path = self._gen_dir / filename
        if not file_path.exists():
            return {"success": False, "message": "指定されたファイルが見つかりません。"}

        try:
            # Get instruction record from database
            instruction_record = await self._dao.get_instruction_by_file_path(filename)
            if not instruction_record:
                return {
                    "success": False,
                    "message": "指定されたファイルに対応するシステム指示が見つかりません。",
                }

            # Activate the instruction
            success = await self._dao.activate_instruction(instruction_record["id"])
            if not success:
                return {"success": False, "message": "システム指示の再設定に失敗しました。"}

            logger.info("Reactivated instruction with ID %d", instruction_record["id"])
            return {
                "success": True,
                "instruction_id": instruction_record["id"],
                "filename": filename,
                "message": "システム指示が正常に再設定されました。",
            }

        except Exception as e:
            logger.exception("Error reactivating instruction: %s", e)
            return {"success": False, "message": "システム指示の再設定中にエラーが発生しました。"}

    async def reset_to_default(self) -> dict[str, Any]:
        """Reset system instructions to default by deactivating all custom instructions."""
        try:
            deactivated_count = await self._dao.deactivate_all_instructions()
            logger.info("Reset to default, deactivated %d instructions", deactivated_count)
        except Exception as e:
            logger.exception("Error resetting to default: %s", e)
            return {"success": False, "message": "リセット中にエラーが発生しました。"}
        return {
            "success": True,
            "deactivated_count": deactivated_count,
            "message": "システム指示をデフォルトにリセットしました。",
        }

    async def get_active_instruction_content(self) -> str | None:
        """Get the content of the currently active instruction."""
        try:
            return await self._dao.get_active_instruction()
        except Exception as e:
            logger.exception("Error fetching active instruction: %s", e)
            return None

    async def get_effective_instruction(self, command_name: str) -> str | None:
        """Get the effective instruction for a command."""
        try:
            # Try active instruction first
            custom_instruction = await self.get_active_instruction_content()
            if custom_instruction:
                return custom_instruction

            # Fall back to static instruction
            return self.load_static_instruction(command_name)

        except Exception as e:
            logger.exception("Error getting effective instruction: %s", e)
            return None

    def get_instruction_files_with_content(self) -> list[dict[str, Any]]:
        """Get instruction files with preview and full content."""
        files_info = []
        txt_files = self._get_instruction_files()

        for file_path in txt_files[:DISCORD_SELECT_LIMIT]:
            try:
                with file_path.open("r", encoding="utf-8") as f:
                    content = f.read().strip()

                if not content:
                    continue

                # Create preview
                preview = content[:PREVIEW_LENGTH]
                if len(content) > PREVIEW_LENGTH:
                    preview += "..."

                files_info.append(
                    {
                        "filename": file_path.name,
                        "preview": preview,
                        "content": content,
                    },
                )

            except Exception as e:
                logger.error("Error processing file %s: %s", file_path.name, e)
                continue

        return files_info

    async def delete_instruction_by_filename(self, filename: str) -> dict[str, Any]:
        """Delete an instruction by its filename."""
        try:
            # Delete from database
            db_deleted = await self._dao.delete_instruction_by_file_path(filename)

            # Delete file
            file_path = self._gen_dir / filename
            file_deleted = False
            if file_path.exists():
                try:
                    file_path.unlink()
                    file_deleted = True
                except Exception as e:
                    logger.error("Failed to delete file %s: %s", filename, e)

            if db_deleted or file_deleted:
                logger.info("Deleted instruction: %s", filename)
                return {
                    "success": True,
                    "filename": filename,
                    "message": "システム指示を正常に削除しました。",
                }
        except Exception as e:
            logger.exception("Error deleting instruction %s: %s", filename, e)
            return {"success": False, "message": "システム指示の削除中にエラーが発生しました。"}
        return {
            "success": False,
            "message": "指定されたシステム指示が見つかりませんでした。",
        }

    async def get_instruction_details(self, filename: str) -> dict[str, Any] | None:
        """Get detailed information about a specific instruction."""
        try:
            record = await self._dao.get_instruction_by_file_path(filename)
            if record is None:
                return None

            record["filename"] = filename
        except Exception as e:
            logger.error("Failed to get instruction details for %s: %s", filename, e)
            return None
        return record

    async def sync_files_with_database(self) -> dict[str, int]:
        """Synchronize files and database records."""
        stats = {"orphaned_files": 0, "valid_pairs": 0}

        try:
            txt_files = self._get_instruction_files()

            for file_path in txt_files:
                record = await self._dao.get_instruction_by_file_path(file_path.name)
                if record is None:
                    stats["orphaned_files"] += 1
                    logger.warning("Orphaned file found: %s", file_path.name)
                else:
                    stats["valid_pairs"] += 1

            logger.info("Sync stats: %s", stats)
        except Exception as e:
            logger.error("Failed to sync files with database: %s", e)
            return stats
        return stats
