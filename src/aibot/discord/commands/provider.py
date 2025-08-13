from discord import Interaction, SelectOption
from discord.ui import Select, View

from src.aibot.discord.client import BotClient
from src.aibot.discord.decorators.permission import is_admin_user
from src.aibot.logger import logger
from src.aibot.services.provider import ProviderManager, ProviderType

client = BotClient().get_instance()
provider_manager = ProviderManager.get_instance()


class ProviderSelector(Select):
    """Discord UI selector for choosing AI providers.

    This class creates a dropdown menu that allows users to
    select between different AI providers.
    """

    def __init__(self) -> None:
        """Initialize the provider selector with available options."""
        options = [
            SelectOption(
                label="Anthropic",
                value="anthropic",
                description="Use Anthropic API",
            ),
            SelectOption(
                label="Google",
                value="google",
                description="Use Google Gemini API",
            ),
            SelectOption(
                label="OpenAI",
                value="openai",
                description="Use OpenAI API",
            ),
        ]

        super().__init__(
            placeholder="AIプロバイダーを選択してください...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: Interaction) -> None:
        """Handle the user's selection of AI provider.

        Parameters
        ----------
        interaction : Interaction
            The Discord interaction context.

        """
        try:
            # Defer the response first
            await interaction.response.defer(ephemeral=True)

            chosen_provider: ProviderType = self.values[0]

            # Update the global provider setting
            provider_manager.set_provider(chosen_provider)

            # Get display name for user feedback
            display_name = provider_manager.get_provider_display_name()

            await interaction.followup.send(
                f"AIプロバイダーが `{display_name}` に設定されました",
                ephemeral=True,
            )

            logger.info(
                "User (%s) changed AI provider to: %s",
                interaction.user,
                chosen_provider,
            )
        except Exception as e:
            logger.error("Failed to change provider: %s", e)
            await interaction.followup.send(
                "**ERROR** - `/provider`コマンドの処理中にエラーが発生しました",
                ephemeral=True,
            )


@client.tree.command(name="provider", description="AIプロバイダーを選択します")
@is_admin_user()
async def provider_command(interaction: Interaction) -> None:
    """Select the AI provider to use for chat commands.

    Parameters
    ----------
    interaction : Interaction
        The interaction instance.

    """
    try:
        user = interaction.user
        logger.info("User (%s) is executing provider command", user)

        # Show current provider
        current_provider = provider_manager.get_provider_display_name()
        current_provider_message = f"現在のAIプロバイダーは `{current_provider}` です"

        # Create the selector
        selector = ProviderSelector()
        view = View()
        view.add_item(selector)

        await interaction.response.send_message(
            f"{current_provider_message}\n\n使用するAIプロバイダーを選択してください",
            view=view,
            ephemeral=True,
        )

    except Exception as err:
        msg = f"Error in provider command: {err!s}"
        logger.exception(msg)
        await interaction.response.send_message(
            "**ERROR** - `/provider`コマンドの処理中にエラーが発生しました",
            ephemeral=True,
        )
