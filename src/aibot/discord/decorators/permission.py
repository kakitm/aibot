import os
from collections.abc import Callable
from typing import TypeVar

from discord import Interaction, app_commands

T = TypeVar("T")


def is_admin_user() -> Callable[[T], T]:
    """Check if the user has administrative permission.

    Returns
    -------
    Callable[[T], T]
        A decorator that checks whether the user executing command is
        listed in the environment variable `ADMIN_USER_IDS`.

    """

    def predicate(interaction: Interaction) -> bool:
        return interaction.user.id in [int(i) for i in os.environ["ADMIN_USER_IDS"].split(",")]

    return app_commands.check(predicate)
