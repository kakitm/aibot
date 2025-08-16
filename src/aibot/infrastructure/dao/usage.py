import datetime

import aiosqlite

from .base import DAOBase


class UsageDAO(DAOBase):
    """Data Access Object for managing usage records.

    Attributes
    ----------
    LIMIT_TABLE_NAME : str
        Name of the database table for user limits.
    USAGE_TRACKING_TABLE_NAME : str
        Name of the database table for daily usage tracking.

    """

    USER_LIMITS_TABLE_NAME: str = "user_limits"
    USAGE_TRACKING_TABLE_NAME: str = "usage_tracking"

    async def create_user_limits_table(self) -> None:
        """Create table for managing user limits if it doesn't exist.

        Raises
        ------
        ValueError
            If the table name contains invalid characters.

        """
        if not self.validate_table_name(self.USER_LIMITS_TABLE_NAME):
            msg = "INVALID TABLENAME: Only alphanumeric characters and underscores are allowed."
            raise ValueError(msg)

        conn = await aiosqlite.connect(super().DB_NAME)
        try:
            query = f"""
            CREATE TABLE IF NOT EXISTS {self.USER_LIMITS_TABLE_NAME} (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL UNIQUE,
                daily_limit   INTEGER NOT NULL DEFAULT 10,
                last_updated  TIMESTAMP NOT NULL
            );
            """
            await conn.execute(query)
            await conn.commit()
        finally:
            await conn.close()

    async def create_usage_tracking_table(self) -> None:
        """Create table for tracking API usage if it doesn't exist.

        Raises
        ------
        ValueError
            If the table name contains invalid characters.

        """
        if not self.validate_table_name(self.USAGE_TRACKING_TABLE_NAME):
            msg = "INVALID TABLENAME: Only alphanumeric characters and underscores are allowed."
            raise ValueError(msg)

        conn = await aiosqlite.connect(super().DB_NAME)
        try:
            query = f"""
            CREATE TABLE IF  NOT EXISTS {self.USAGE_TRACKING_TABLE_NAME} (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL,
                usage_date   DATE NOT NULL,
                usage_count  INTEGER NOT NULL DEFAULT 0,
                UNIQUE(user_id, usage_date)
            );
            """
            await conn.execute(query)
            await conn.commit()
        finally:
            await conn.close()

    async def create_tables(self) -> None:
        """Create both user limits and usage tracking tables if they don't exist."""
        await self.create_user_limits_table()
        await self.create_usage_tracking_table()

    async def set_daily_usage_limit(self, daily_limit: int, user_id: int | None = None) -> None:
        """Set or update daily usage limit.

        Parameters
        ----------
        daily_limit : int
            Maximum number of calls allowed to make in one day.
        user_id : int | None
            ID of the user. If None, sets the default limit for all users.

        """
        conn = await aiosqlite.connect(super().DB_NAME)
        now = datetime.datetime.now(super().TIMEZONE)
        try:
            # Use user_id (0) to represent the default limit for all users
            target_user_id = user_id if user_id is not None else 0
            query = """
            INSERT INTO user_limits (user_id, daily_limit, last_updated)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                daily_limit = ?,
                last_updated = ?;
            """
            await conn.execute(
                query,
                (
                    target_user_id,
                    daily_limit,
                    now,
                    daily_limit,
                    now,
                ),
            )
            await conn.commit()
        finally:
            await conn.close()

    async def get_daily_usage_limit(self, user_id: int | None = None) -> int:
        """Get daily usage limit for a user or the default limit.

        Parameters
        ----------
        user_id : int | None
            ID of the user. If None, returns the default limit for all users.

        Returns
        -------
        int
            Maximum number of calls the user is allowed to make in one day.
            Returns 10 if no limit is set.

        """
        conn = await aiosqlite.connect(super().DB_NAME)
        try:
            target_user_id = 0 if user_id is None else user_id
            query = """
            SELECT daily_limit FROM user_limits WHERE user_id = ?;
            """
            cursor = await conn.execute(query, (target_user_id,))
            row = await cursor.fetchone()
            return row[0] if row else 10  # Default limit is 10
        finally:
            await conn.close()

    async def get_user_daily_usage(self, user_id: int) -> int:
        """Get the current day's usage count for a user.

        Parameters
        ----------
        user_id : int
            ID of the user.

        Returns
        -------
        int
            Number of calls the user has made today. Returns 0 if no record found.

        """
        conn = await aiosqlite.connect(super().DB_NAME)
        today = datetime.datetime.now(super().TIMEZONE).date()
        try:
            query = """
            SELECT usage_count FROM usage_tracking
            WHERE user_id = ? AND usage_date = ?;
            """
            cursor = await conn.execute(query, (user_id, today))
            row = await cursor.fetchone()
            return row[0] if row else 0
        finally:
            await conn.close()

    async def increment_daily_usage_count(self, user_id: int) -> None:
        """Increment the usage count for a user on the current day.

        Parameters
        ----------
        user_id : int
            ID of the user.

        """
        conn = await aiosqlite.connect(super().DB_NAME)
        today = datetime.datetime.now(super().TIMEZONE).date()
        try:
            query = """
            INSERT INTO usage_tracking (user_id, usage_date, usage_count)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, usage_date) DO UPDATE SET
                usage_count = usage_count + 1;
            """
            await conn.execute(query, (user_id, today))
            await conn.commit()
        finally:
            await conn.close()

    async def RESET(self) -> None:  # noqa: N802
        """Reset daily usage counts by removing records from yesterday."""
        conn = await aiosqlite.connect(super().DB_NAME)
        yesterday = (datetime.datetime.now(super().TIMEZONE) - datetime.timedelta(days=1)).date()
        try:
            # Delete records older than yesterday
            query = """
            DELETE FROM usage_tracking
            WHERE usage_date < ?;
            """
            await conn.execute(query, (yesterday,))
            await conn.commit()
        finally:
            await conn.close()
