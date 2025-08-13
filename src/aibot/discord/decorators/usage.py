import os
from collections.abc import Callable
from typing import TypeVar, cast

from discord import Interaction, app_commands

from src.aibot.infrastructure.dao.usage import UsageDAO

T = TypeVar("T")


def has_daily_usage_left() -> Callable[[T], T]:
    """Check if the user has not reached their daily usage limit.

    Returns
    -------
    Callable[[T], T]
        A decorator that checks whether the user has not reached
        their daily limit of API calls.

    """

    async def predicate(interaction: Interaction) -> bool:
        # Admin users bypass usage limits
        if interaction.user.id in [int(i) for i in os.environ["ADMIN_USER_IDS"].split(",")]:
            return True

        # Check usage limits for regular users
        dao = UsageDAO()
        current_usage = await dao.get_user_daily_usage(interaction.user.id)
        user_limit = await dao.get_daily_usage_limit(interaction.user.id)

        return cast("bool", current_usage < user_limit)

    return app_commands.check(predicate)
