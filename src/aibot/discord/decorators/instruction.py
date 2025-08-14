"""Decorators for instruction related commands."""

from collections.abc import Callable
from typing import TypeVar

from discord import Interaction, app_commands

from src.aibot.services.restriction import RestrictionService

T = TypeVar("T")


def is_restricted() -> Callable[[T], T]:
    """Check if instruction creation is restricted (blocked by restriction mode).

    This decorator prevents command execution when restriction mode is active.
    Used to block instruction creation and modification commands for safety.

    Returns
    -------
    Callable[[T], T]
        A decorator that checks whether restriction mode is active.

    """

    async def predicate(interaction: Interaction) -> bool:
        restriction_service = RestrictionService.get_instance()

        if restriction_service.is_restricted():
            error_message = "⚠️ 制限モードが有効です。カスタム指示の作成・変更ができません。"
            await interaction.response.send_message(error_message, ephemeral=True)
            return False

        return True

    return app_commands.check(predicate)
