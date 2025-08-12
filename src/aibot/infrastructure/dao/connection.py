from __future__ import annotations

import datetime
from typing import TypedDict

import aiosqlite

from src.aibot.logger import logger

from .base import DAOBase

# Types
DatetimeLike = str | datetime.datetime


class ConnectionInfo(TypedDict):
    """Connection status snapshot."""

    channel_id: str
    guild_id: str | None
    connected_at: DatetimeLike
    last_updated: DatetimeLike


class ConnectionDAO(DAOBase):
    """Data Access Object for managin voice channel connections.

    This DAO manages both current connection status and connection history.
    The bot can only be connected to one voice channel at a time.

    Attributes
    ----------
    STATUS_TABLE_NAME : str
        Name of the database table for current connection status.
    HISTORY_TABLE_NAME : str
        Name of the database table for connection history.

    """

    STATUS_TABLE_NAME: str = "connection_status"
    HISTORY_TABLE_NAME: str = "connection_history"

    async def create_status_table(self) -> None:
        """Create connection status table if it doesn't exist.

        This table maintains the current connection state (single record).

        Raises
        ------
        ValueError
            If the table name contains invalid characters.

        """
        if not self.validate_table_name(self.STATUS_TABLE_NAME):
            msg = "INVALID TABLENAME: Only alphanumeric characters and underscores are allowed."
            raise ValueError(msg)

        conn = await aiosqlite.connect(super().DB_NAME)
        try:
            query = f"""
            CREATE TABLE IF NOT EXISTS {self.STATUS_TABLE_NAME} (
                id            INTEGER PRIMARY KEY CHECK (id = 1),
                channel_id    TEXT NOT NULL,
                guild_id      TEXT,
                connected_at  DATETIME NOT NULL,
                last_updated  DATETIME NOT NULL
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

    async def create_history_table(self) -> None:
        """Create connection history table if it doesn't exist.

        This table logs all connection events for analytics and debugging.

        Raises
        ------
        ValueError
            If the table name contains invalid characters.

        """
        if not self.validate_table_name(self.HISTORY_TABLE_NAME):
            msg = "INVALID TABLENAME: Only alphanumeric characters and underscores are allowed."
            raise ValueError(msg)

        conn = await aiosqlite.connect(super().DB_NAME)
        try:
            query = f"""
            CREATE TABLE IF NOT EXISTS {self.HISTORY_TABLE_NAME} (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id     TEXT NOT NULL,
                guild_id       TEXT,
                action         TEXT NOT NULL CHECK
                    (action IN ('CONNECT', 'DISCONNECT', 'ERROR')),
                timestamp      DATETIME NOT NULL,
                error_message  TEXT
            );
            """
            await conn.execute(query)
            await conn.commit()
        except Exception:
            logger.exception("Failed to create history table")
            raise
        finally:
            try:
                await conn.close()
            except Exception as close_err:
                logger.error(f"Failed to close connection: {close_err}")

    async def create_tables(self) -> None:
        """Create both status and history tables if they don't exist."""
        await self.create_status_table()
        await self.create_history_table()

    async def connect(self, channel_id: str, guild_id: str | None = None) -> None:
        """Update connection status to connected state.

        This method safely handles connection by:
        1. Logging any existing connection as disconnected
        2. Setting new connection status
        3. Recording the connection event in history

        Parameters
        ----------
        channel_id : str
            The ID of the voice channel to connect to.
        guild_id : str | None
            The ID of the guild (server) containing the channel.

        """
        conn = await aiosqlite.connect(super().DB_NAME)
        now = datetime.datetime.now(super().TIMEZONE)

        try:
            # Use transaction to ensure data consistency
            await conn.execute("BEGIN TRANSACTION;")

            # Log existing connection as disconnected if exists
            await self._log_disconnect_if_exists(conn, now)

            # Set new connection status (INSERT or REPLACE)
            status_query = """
            INSERT OR REPLACE INTO connection_status
            (id, channel_id, guild_id, connected_at, last_updated)
            VALUES (1, ?, ?, ?, ?);
            """
            await conn.execute(status_query, (channel_id, guild_id, now, now))

            # Log connection event in history
            await self._log_history(conn, channel_id, guild_id, "CONNECT", now)

            await conn.commit()
        except Exception as e:
            try:
                await conn.rollback()
            except Exception as rollback_err:
                logger.error(f"Rollback failed: {rollback_err}")
            try:
                await self._log_history(
                    conn,
                    channel_id,
                    guild_id,
                    "ERROR",
                    now,
                    f"Connection failed: {type(e).__name__}: {e}",
                )
                await conn.commit()
            except Exception as log_err:
                logger.error(f"Failed to log error: {log_err}")
            logger.exception("connect() failed")
            raise
        finally:
            try:
                await conn.close()
            except Exception as close_err:
                logger.error(f"Failed to close connection: {close_err}")

    async def disconnect(self) -> ConnectionInfo | None:
        """Disconnect from current voice channel.

        Returns information about the disconnected channel.

        Returns
        -------
        dict[str, str] | None
            Dictionary containing channel_id and guild_id of disconnected channel.
            Returns None if no active connection exists.

        """
        conn = await aiosqlite.connect(super().DB_NAME)
        now = datetime.datetime.now(super().TIMEZONE)

        connection_info = None
        try:
            await conn.execute("BEGIN TRANSACTION;")

            # Get current connection info before clearing
            connection_info = await self._get_current_connection_info(conn)

            if connection_info:
                # Clear connection status
                query = """
                DELETE FROM connection_status
                WHERE id = 1;
                """

                await conn.execute(query)

                # Log disconnect event
                await self._log_history(
                    conn,
                    connection_info["channel_id"],
                    connection_info["guild_id"],
                    "DISCONNECT",
                    now,
                )

            await conn.commit()
        except Exception as e:
            try:
                await conn.rollback()
            except Exception as rollback_err:
                logger.error(f"Rollback failed: {rollback_err}")
            # Try to log error to history as best-effort
            try:
                await self._log_history(
                    conn,
                    (connection_info["channel_id"] if connection_info else "UNKNOWN"),
                    (connection_info["guild_id"] if connection_info else None),
                    "ERROR",
                    now,
                    f"Disconnect failed: {type(e).__name__}: {e}",
                )
                await conn.commit()
            except Exception as log_err:
                logger.error(f"Failed to log error: {log_err}")
            logger.exception("disconnect() failed")
            raise
        finally:
            try:
                await conn.close()
            except Exception as close_err:
                logger.error(f"Failed to close connection: {close_err}")

        return connection_info

    async def get_current_connection(self) -> ConnectionInfo | None:
        """Get current connection status.

        Returns
        -------
        dict[str, str] | None
            Dictionary containing connection information if connected.
            Keys: channel_id, guild_id, connected_at, last_updated
            None if not connected.

        """
        conn = await aiosqlite.connect(super().DB_NAME)
        try:
            return await self._get_current_connection_info(conn)
        except aiosqlite.Error:
            logger.exception("Failed to get current connection")
            return None
        except Exception:
            raise
        finally:
            try:
                await conn.close()
            except Exception as close_err:
                logger.error(f"Failed to close connection: {close_err}")

    async def is_connected(self) -> bool:
        """Check if bot is currently connected to a voice channel.

        Returns
        -------
        bool
            True if connected, False otherwise.

        """
        connection_info = await self.get_current_connection()
        return connection_info is not None

    async def _get_current_connection_info(
        self,
        conn: aiosqlite.Connection,
    ) -> ConnectionInfo | None:
        """Internal method to get current connection info from database.

        Parameters
        ----------
        conn : aiosqlite.Connection
            Database connection to use.

        Returns
        -------
        dict[str, str] | None
            Connection information dictionary or None.

        """
        query = """
        SELECT channel_id, guild_id, connected_at, last_updated
        FROM connection_status
        WHERE id = 1;
        """
        cursor = await conn.execute(query)
        row = await cursor.fetchone()

        if row:
            return {
                "channel_id": row[0],
                "guild_id": row[1],
                "connected_at": row[2],
                "last_updated": row[3],
            }
        return None

    async def _log_disconnect_if_exists(
        self,
        conn: aiosqlite.Connection,
        timestamp: datetime.datetime,
    ) -> None:
        """Log existing connection as disconnected if it exists.

        Parameters
        ----------
        conn : aiosqlite.Connection
            Database connection to use.
        timestamp : datetime.datetime
            Timestamp for the disconnect event.

        """
        connection_info = await self._get_current_connection_info(conn)
        if connection_info:
            await self._log_history(
                conn,
                connection_info["channel_id"],
                connection_info["guild_id"],
                "DISCONNECT",
                timestamp,
                "Disconnected due to new connection",
            )

    async def _log_history(  # noqa: PLR0913
        self,
        conn: aiosqlite.Connection,
        channel_id: str,
        guild_id: str | None,
        action: str,
        timestamp: datetime.datetime,
        error_message: str | None = None,
    ) -> None:
        """Log connection event to history table.

        Parameters
        ----------
        conn : aiosqlite.Connection
            Database connection to use.
        channel_id : str
            ID of the voice channel.
        guild_id : str | None
            ID of the guild.
        action : str
            Action type ('CONNECT', 'DISCONNECT', 'ERROR').
        timestamp : datetime.datetime
            When the event occurred.
        error_message : str | None
            Error message if action is 'ERROR'.

        """
        query = """
        INSERT INTO connection_history
        (channel_id, guild_id, action, timestamp, error_message)
        VALUES (?, ?, ?, ?, ?);
        """
        await conn.execute(
            query,
            (
                channel_id,
                guild_id,
                action,
                timestamp,
                error_message,
            ),
        )
