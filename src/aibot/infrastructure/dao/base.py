import os
import re
from typing import TYPE_CHECKING

import pytz

if TYPE_CHECKING:
    from pytz.tzinfo import BaseTzInfo


class DAOBase:
    """Base class for DAO classes."""

    DB_NAME: str = os.getenv("DB_NAME", "aibot.db")

    tz: str = os.getenv("TIMEZONE", "Asia/Tokyo")
    TIMEZONE: "BaseTzInfo" = pytz.timezone(tz)

    @staticmethod
    def validate_table_name(table_name: str) -> bool:
        """Validate the table name.

        Only letters, numbers, and underscores are allowed.

        Parameters
        ----------
        table_name : str
            The name of the table.

        Returns
        -------
        bool
            True if the table name is valid, False otherwise.

        """
        pattern = r"^[A-Za-z0-9_]+$"
        return bool(re.match(pattern, table_name))
