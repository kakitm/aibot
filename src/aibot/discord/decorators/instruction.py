"""Decorators for instruction related commands."""

from collections.abc import Callable
from typing import Any, TypeVar

from discord import Interaction

from src.aibot.services.restriction import RestrictionService

T = TypeVar("T")


def is_restricted() -> Callable[[T], T]:
    """Check if instruction creation is restricted (blocked by restriction mode).

    This decorator prevents command execution when restriction mode is active.
    Used to block instruction creation and modification commands for safety.

    Returns
    -------
    Callable[[T], T]
        A decorator that wraps the command function to check restriction mode.

    """

    def decorator(func: T) -> T:
        async def wrapper(interaction: Interaction, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
            """Wrapper function that checks restriction mode before executing command.

            Parameters
            ----------
            interaction : Interaction
                Discord interaction object.
            *args : Any
                Positional arguments for the original function.
            **kwargs : Any
                Keyword arguments for the original function.

            """
            restriction_service = RestrictionService.get_instance()

            if restriction_service.is_restricted():
                # Send restriction mode message
                await interaction.response.send_message(
                    "⚠️ 制限モードが有効です。カスタム指示の作成・変更ができません。",
                    ephemeral=True,
                )
                return

            # Restriction mode is not active, proceed with original function
            await func(interaction, *args, **kwargs)

        return wrapper

    return decorator
