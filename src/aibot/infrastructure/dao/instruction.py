import datetime

import aiosqlite

from src.aibot.logger import logger

from .base import DAOBase


class InstructionDAO(DAOBase):
    """Data Access Object for managing custom instructions."""

    TABLE_NAME: str = "custom_instruction"

    async def create_table(self) -> None:
        """Create table if it doesn't exist."""
        if not self.validate_table_name(self.TABLE_NAME):
            msg = "INVALID TABLENAME: Only alphanumeric characters and underscores are allowed."
            raise ValueError(msg)

        conn = await aiosqlite.connect(super().DB_NAME)
        try:
            query = f"""
            CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                instruction     TEXT NOT NULL,
                file_path       TEXT NOT NULL,
                created_by      INTEGER NOT NULL,
                created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
                activated_at    DATETIME DEFAULT NULL,
                deactivated_at  DATETIME DEFAULT NULL,
                is_active       BOOLEAN DEFAULT FALSE
            );
            """
            await conn.execute(query)
            await conn.commit()
        except Exception:
            logger.exception("Failed to create status table")
            raise
        finally:
            try:
                await conn.close()
            except Exception as close_err:
                logger.error(f"Failed to close connection: {close_err}")

    async def deactivate_all_instructions(self) -> int:
        """Deactivate all currently active instructions.

        Returns
        -------
        int
            Number of instructions that were deactivated.

        """
        conn = await aiosqlite.connect(super().DB_NAME)
        deactivated_at = datetime.datetime.now(super().TIMEZONE)
        try:
            query = """
            UPDATE custom_instruction
            SET is_active = FALSE, deactivated_at = ?
            WHERE is_active = TRUE;
            """
            cursor = await conn.execute(query, (deactivated_at,))
            await conn.commit()
            return cursor.rowcount or 0
        finally:
            await conn.close()

    async def save_instruction(
        self,
        instruction: str,
        file_path: str,
        created_by: int,
    ) -> int | None:
        """Save a custom instruction to the database.

        Parameters
        ----------
        instruction : str
            The custom instruction content.
        file_path : str
            The path to the generated instruction file.
        created_by : int
            The ID of the user who created the instruction.

        Returns
        -------
        int | None
            The ID of the created instruction, or None if failed to create.

        """
        if not instruction or not instruction.strip():
            msg = "Instruction cannot be empty."
            logger.warning(msg)

        conn = await aiosqlite.connect(super().DB_NAME)

        try:
            query = """
            INSERT INTO custom_instruction (instruction, file_path, created_by)
            VALUES (?, ?, ?);
            """
            cursor = await conn.execute(
                query,
                (
                    instruction.strip(),
                    file_path,
                    created_by,
                ),
            )
            await conn.commit()
            if cursor.lastrowid is None:
                msg = "Failed to create instruction: no ID returned"
                logger.error(msg)
                return None
            return cursor.lastrowid
        finally:
            await conn.close()

    async def activate_instruction(self, instruction_id: int) -> bool:
        """Activate a specific instruction and deactivate all others.

        Parameters
        ----------
        instruction_id : int
            The ID of the instruction to activate.

        Returns
        -------
        bool
            True if the instruction was successfully activated, False otherwise.

        """
        # First, deactivate all instructions
        await self.deactivate_all_instructions()

        conn = await aiosqlite.connect(super().DB_NAME)
        activated_at = datetime.datetime.now(super().TIMEZONE)
        try:
            query = """
            UPDATE custom_instruction
            SET is_active = TRUE, activated_at = ?, deactivated_at = NULL
            WHERE id = ?;
            """
            cursor = await conn.execute(
                query,
                (
                    activated_at,
                    instruction_id,
                ),
            )
            await conn.commit()
            return cursor.rowcount > 0
        finally:
            await conn.close()

    async def delete_instruction_by_file_path(self, file_path: str) -> bool:
        """Delete a custom instruction by its file path.

        Parameters
        ----------
        file_path : str
            The file path of the instruction to delete.

        Returns
        -------
        bool
            True if the instruction was successfully deleted, False otherwise.

        """
        conn = await aiosqlite.connect(super().DB_NAME)
        try:
            query = """
            DELETE FROM custom_instruction
            WHERE file_path = ?;
            """
            cursor = await conn.execute(query, (file_path,))
            await conn.commit()
            return cursor.rowcount > 0
        finally:
            await conn.close()

    async def get_active_instruction(self) -> str | None:
        """Get the instruction content from the currently active instruction.

        Returns
        -------
        str | None
            The instruction content if an active instruction exists with non-null
            activated_at and is_active=True, None otherwise.

        """
        conn = await aiosqlite.connect(super().DB_NAME)
        try:
            query = """
            SELECT instruction
            FROM custom_instruction
            WHERE activated_at IS NOT NULL AND is_active = TRUE
            ORDER BY activated_at DESC
            LIMIT 1;
            """
            cursor = await conn.execute(query)
            row = await cursor.fetchone()

            return row[0] if row else None
        finally:
            await conn.close()

    async def get_instruction_by_file_path(self, file_path: str) -> dict | None:
        """Get instruction record by file path.

        Parameters
        ----------
        file_path : str
            The file path of the instruction to retrieve.

        Returns
        -------
        dict | None
            Dictionary containing instruction details (id, instruction, created_by, etc.)
            or None if no instruction found with the given file path.

        """
        conn = await aiosqlite.connect(super().DB_NAME)
        try:
            query = """
            SELECT id, instruction, file_path, created_by, created_at,
                   activated_at, deactivated_at, is_active
            FROM custom_instruction
            WHERE file_path = ?;
            """
            cursor = await conn.execute(query, (file_path,))
            row = await cursor.fetchone()

            if row:
                return {
                    "id": row[0],
                    "instruction": row[1],
                    "file_path": row[2],
                    "created_by": row[3],
                    "created_at": row[4],
                    "activated_at": row[5],
                    "deactivated_at": row[6],
                    "is_active": row[7],
                }
            return None
        finally:
            await conn.close()

    async def update_file_path(self, old_path: str, new_path: str) -> bool:
        """Update the file path of a custom instruction.

        Parameters
        ----------
        old_path : str
            The current file path to update.
        new_path : str
            The new file path to set.

        Returns
        -------
        bool
            True if the file path was successfully updated, False otherwise.

        """
        conn = await aiosqlite.connect(super().DB_NAME)
        try:
            query = """
            UPDATE custom_instruction
            SET file_path = ?
            WHERE file_path = ?;
            """
            cursor = await conn.execute(
                query,
                (
                    new_path,
                    old_path,
                ),
            )
            await conn.commit()
            return cursor.rowcount > 0
        finally:
            await conn.close()
