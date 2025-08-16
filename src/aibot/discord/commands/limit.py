import os

from discord import Colour, Embed, Interaction

from src.aibot.discord.client import BotClient
from src.aibot.discord.decorators.permission import is_admin_user
from src.aibot.infrastructure.dao.usage import UsageDAO
from src.aibot.logger import logger

client = BotClient.get_instance()
usage_dao = UsageDAO()


@client.tree.command(
    name="set-limit",
    description="1日あたりのリクエスト回数の上限を設定します",
)
@is_admin_user()
async def set_limit_command(interaction: Interaction, limit: int) -> None:
    """Set the default daily usage limit for per user.

    Parameters
    ----------
    interaction : Interaction
        The interaction object from the command.
    limit : int
        The maximum number of AI calls allowed per day.

    """
    try:
        if limit < 1:
            await interaction.response.send_message(
                "**limit**は1以上の整数を指定してください",
                ephemeral=True,
            )
            return

        await usage_dao.set_default_daily_limit(limit)

        await interaction.response.send_message(
            f"使用回数の上限を{limit}/dayに設定しました",
            ephemeral=True,
        )
        logger.info(
            "%s set default daily limit to %d",
            interaction.user,
            limit,
        )
    except Exception:
        await interaction.response.send_message(
            "**Error**: `/limit` コマンドでエラーが発生しました",
            ephemeral=True,
        )
        logger.exception("An error occurred in the limit command")


@client.tree.command(
    name="limit",
    description="現在の利用状況を確認します",
)
async def limit_command(interaction: Interaction) -> None:
    """Check user's limit and current usage."""
    try:
        user = interaction.user
        admin_ids: list[int] = [int(id_str) for id_str in os.environ["ADMIN_USER_IDS"].split(",")]

        user_limit = await usage_dao.get_daily_usage_limit(user.id)
        current_usage = await usage_dao.get_user_daily_usage(user.id)

        embed = Embed(
            description=f"<@{user.id}> の利用状況",
            color=Colour.blue(),
        )

        # Admin user is unlimited
        if user.id in admin_ids:
            embed.add_field(name="使用回数", value=f"{current_usage} / ∞", inline=True)
            embed.add_field(name="残り回数", value="∞", inline=True)
        else:
            embed.add_field(name="使用回数", value=f"{current_usage} / {user_limit}", inline=True)
            embed.add_field(name="残り回数", value=max(0, user_limit - current_usage), inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception:
        await interaction.response.send_message(
            "**ERROR**: 使用状況の取得に失敗しました",
            ephemeral=True,
        )
        logger.exception("An error occurred in the limit command")
