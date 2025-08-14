from discord import Interaction, app_commands

from src.aibot.discord.client import BotClient
from src.aibot.discord.decorators.permission import is_not_blocked_user
from src.aibot.discord.decorators.usage import has_daily_usage_left
from src.aibot.infrastructure.api.factory import ApiFactory
from src.aibot.infrastructure.dao.usage import UsageDAO
from src.aibot.logger import logger
from src.aibot.models.chat import ChatMessage
from src.aibot.services.instruction import InstructionService
from src.aibot.services.provider import ProviderManager

api_factory = ApiFactory()
client = BotClient().get_instance()
instruction_service = InstructionService.get_instance()
provider_manager = ProviderManager.get_instance()


@client.tree.command(name="chat", description="AIとシングルターンのチャットを行います")
@is_not_blocked_user()
@has_daily_usage_left()
@app_commands.rename(user_msg="message")
async def chat_command(interaction: Interaction, user_msg: str) -> None:
    """Single-turn chat with the bot.

    Parameters
    ----------
    interaction : Interaction
        The interaction instance.

    user_msg : str
        The message to send to the bot.

    """
    try:
        user = interaction.user
        logger.info("User ( %s ) is executing chat command", user)

        await interaction.response.defer()

        message = ChatMessage(role="user", content=user_msg)

        # Track usage
        usage_dao = UsageDAO()
        await usage_dao.increment_usage_count(user.id)

        # Get static instruction only (no custom instructions for chat command)
        system_instruction = instruction_service.load_static_instruction("chat")
        if system_instruction is None:
            logger.warning("No static instruction found for chat command")
            await interaction.followup.send(
                "システム指示が設定されていません。管理者に問い合わせてください。",
                ephemeral=True,
            )
            return

        # Get current provider and generate response
        current_provider = provider_manager.get_provider()
        logger.debug("Using AI provider: %s for chat", current_provider)

        response = await api_factory.generate_response(
            system=system_instruction,
            messages=[message],
        )

        await interaction.followup.send(f"{response.content}")
    except Exception as err:
        msg = f"Error in chat command: {err!s}"
        logger.exception(msg)
        await interaction.followup.send(
            "`/chat` コマンドの実行中にエラーが発生しました。",
            ephemeral=True,
        )
