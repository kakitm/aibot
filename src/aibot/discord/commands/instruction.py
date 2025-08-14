import os

from discord import Interaction, SelectOption, TextStyle, ui

from src.aibot.discord.client import BotClient
from src.aibot.discord.decorators.instruction import is_restricted
from src.aibot.discord.decorators.permission import is_admin_user
from src.aibot.logger import logger
from src.aibot.services.instruction import InstructionService
from src.aibot.services.restriction import RestrictionService

client = BotClient().get_instance()
instruction_service = InstructionService.get_instance()
restriction_service = RestrictionService.get_instance()

MAX_CHARS_PER_MESSAGE = int(os.getenv("MAX_CHARS_PER_MESSAGE", "1000"))


class SystemInstructionModal(ui.Modal, title="システム指示設定"):
    """Modal for setting system instructions."""

    def __init__(self) -> None:
        """Initialize the modal."""
        super().__init__()

    instruction_input: ui.TextInput = ui.TextInput(
        label="システム指示",
        placeholder="システム指示を入力してください",
        style=TextStyle.paragraph,
        required=True,
        max_length=1024,
    )

    async def on_submit(self, interaction: Interaction) -> None:
        """Handle modal submission."""
        try:
            user = interaction.user
            logger.info("User ( %s ) is setting system instruction", user)

            instruction_content = self.instruction_input.value

            await interaction.response.defer(ephemeral=True)

            # Create and activate instruction through service layer
            result = await instruction_service.create_and_activate_instruction(
                content=instruction_content,
                created_by=user.id,
            )

            if result and result.get("success"):
                logger.info(
                    "System instruction created and activated (ID: %d) for user %s",
                    result["instruction_id"],
                    user,
                )
                await interaction.followup.send(
                    "システム指示が設定されました",
                    ephemeral=True,
                )
            else:
                logger.error("Failed to create system instruction for user %s", user)
                await interaction.followup.send(
                    "システム指示の設定に失敗しました",
                    ephemeral=True,
                )

        except Exception as err:
            msg = f"Error in system command modal: {err!s}"
            logger.exception(msg)
            await interaction.followup.send(
                "システム指示の設定中にエラーが発生しました",
                ephemeral=True,
            )


class SystemInstructionSelect(ui.Select):
    """Select menu for choosing system instructions."""

    def __init__(self, files_info: list[dict], action: str) -> None:
        """Initialize the select menu."""
        self.files_info = files_info
        self.action = action

        options = [
            SelectOption(
                label=file_info["preview"],
                value=file_info["filename"],
            )
            for file_info in files_info  # files_info is already limited to 25 items
        ]

        if not options:
            options.append(
                SelectOption(
                    label="利用可能な指示ファイルがありません",
                    value="none",
                ),
            )

        super().__init__(
            placeholder="システム指示を選択してください...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: Interaction) -> None:
        """Handle select menu callback."""
        try:
            if self.values[0] == "none":
                await interaction.response.send_message(
                    "利用可能な指示ファイルがありません。",
                    ephemeral=True,
                )
                return

            filename = self.values[0]
            file_info = next((f for f in self.files_info if f["filename"] == filename), None)

            if not file_info:
                await interaction.response.send_message(
                    "選択されたファイルが見つかりません。",
                    ephemeral=True,
                )
                return

            if self.action == "view":
                # Display the full content
                content = file_info["content"]
                if len(content) > MAX_CHARS_PER_MESSAGE:
                    content = content[:MAX_CHARS_PER_MESSAGE] + "\n..."

                await interaction.response.send_message(
                    f"**{filename}** の内容:\n```\n{content}\n```",
                    ephemeral=True,
                )

            elif self.action == "activate":
                await interaction.response.defer(ephemeral=True)

                # Reactivate the existing instruction by filename
                result = await instruction_service.reactivate_instruction_by_filename(filename)

                if result and result.get("success"):
                    await interaction.followup.send(
                        f"**{filename}** をシステム指示として再設定しました。",
                        ephemeral=True,
                    )
                else:
                    error_message = (
                        result.get("message", "指示の再設定に失敗しました。")
                        if result
                        else "指示の再設定に失敗しました。"
                    )
                    await interaction.followup.send(
                        f"エラー: {error_message}",
                        ephemeral=True,
                    )

        except Exception as e:
            logger.exception("Error in system instruction select callback: %s", e)
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "エラーが発生しました。",
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    "エラーが発生しました。",
                    ephemeral=True,
                )


class SystemInstructionView(ui.View):
    """View for system instruction selection."""

    def __init__(self, files_info: list[dict], action: str) -> None:
        """Initialize the view."""
        super().__init__(timeout=300)
        self.add_item(SystemInstructionSelect(files_info, action))


async def _handle_instruction_files_interaction(interaction: Interaction, action: str) -> None:
    """Handle instruction files interaction for list and activate commands.

    Parameters
    ----------
    interaction : Interaction
        The Discord interaction.
    action : str
        The action to perform ("view" for list, "activate" for activate).

    """
    try:
        user = interaction.user
        action_name = "viewing" if action == "view" else "activating"
        logger.info("User ( %s ) is %s system instruction files", user, action_name)

        # Get instruction files with content
        files_info = instruction_service.get_instruction_files_with_content()

        if not files_info:
            await interaction.response.send_message(
                "利用可能なシステム指示ファイルがありません。",
                ephemeral=True,
            )
            return

        # Create view with select menu
        view = SystemInstructionView(files_info, action)

        if action == "view":
            message = f"**利用可能なシステム指示一覧 （{len(files_info)}件）**"  # noqa: RUF001
        else:
            message = f"**システム指示の設定 （{len(files_info)}件）**"  # noqa: RUF001

        await interaction.response.send_message(
            message,
            view=view,
            ephemeral=True,
        )

    except Exception as err:
        msg = f"Error in {action} instruction files interaction: {err!s}"
        logger.exception(msg)
        await interaction.response.send_message(
            "エラーが発生しました。システム管理者にお問い合わせください。",
            ephemeral=True,
        )


@client.tree.command(
    name="activate",
    description="過去のシステム指示を再度使用します",
)
@is_restricted()
async def activate_command(interaction: Interaction) -> None:
    """Reactivate an existing system instruction."""
    await _handle_instruction_files_interaction(interaction, "activate")


@client.tree.command(
    name="list",
    description="利用可能なシステム指示を一覧表示します",
)
@is_restricted()
async def list_command(interaction: Interaction) -> None:
    """List available system instructions."""
    await _handle_instruction_files_interaction(interaction, "view")


@client.tree.command(
    name="create",
    description="新しいシステム指示を作成します",
)
@is_restricted()
async def create_command(interaction: Interaction) -> None:
    """Create a new system instruction."""
    try:
        logger.info("User ( %s ) is creating a new system instruction", interaction.user)

        modal = SystemInstructionModal()
        await interaction.response.send_modal(modal)

    except Exception as e:
        logger.exception("Error in create system instruction command: %s", e)
        await interaction.response.send_message(
            "エラーが発生しました。システム管理者にお問い合わせください。",
            ephemeral=True,
        )


@client.tree.command(
    name="reset",
    description="システム指示をデフォルトにリセットします",
)
@is_restricted()
async def reset_command(interaction: Interaction) -> None:
    """Reset system instructions to default."""
    try:
        user = interaction.user
        logger.info("User ( %s ) is resetting system instructions to default", user)

        await interaction.response.defer(ephemeral=True)

        # Reset to default through service layer
        result = await instruction_service.reset_to_default()

        if result and result.get("success"):
            logger.info("System instructions reset to default by user %s", user)
            await interaction.followup.send(
                "システム指示をデフォルトにリセットしました。",
                ephemeral=True,
            )
        else:
            error_message = (
                result.get("message", "リセットに失敗しました。")
                if result
                else "リセットに失敗しました。"
            )
            logger.error("Failed to reset system instructions for user %s", user)
            await interaction.followup.send(
                f"エラー: {error_message}",
                ephemeral=True,
            )

    except Exception as e:
        logger.exception("Error in reset system instruction command: %s", e)
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "エラーが発生しました。システム管理者にお問い合わせください。",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                "エラーが発生しました。システム管理者にお問い合わせください。",
                ephemeral=True,
            )


@client.tree.command(
    name="lock",
    description="制限モードを有効にします",
)
@is_admin_user()
async def lock_command(interaction: Interaction) -> None:
    """Enable restriction mode to prevent instruction creation/modification."""
    try:
        user = interaction.user
        logger.info("User ( %s ) is enabling restriction mode", user)

        await interaction.response.defer(ephemeral=True)

        # Enable restriction mode through service layer
        result = restriction_service.enable_restriction(user.id)

        if result and result.get("success"):
            was_already_active = result.get("was_already_active", False)
            if was_already_active:
                logger.info("Restriction mode was already active when requested by user %s", user)
            else:
                logger.info("Restriction mode enabled by user %s", user)

            await interaction.followup.send(
                result["message"],
                ephemeral=True,
            )
        else:
            error_message = (
                result.get("message", "制限モードの有効化に失敗しました。")
                if result
                else "制限モードの有効化に失敗しました。"
            )
            logger.error("Failed to enable restriction mode for user %s", user)
            await interaction.followup.send(
                f"エラー: {error_message}",
                ephemeral=True,
            )

    except Exception as e:
        logger.exception("Error in lock command: %s", e)
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "エラーが発生しました。システム管理者にお問い合わせください。",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                "エラーが発生しました。システム管理者にお問い合わせください。",
                ephemeral=True,
            )


@client.tree.command(
    name="unlock",
    description="制限モードを解除します",
)
@is_admin_user()
async def unlock_command(interaction: Interaction) -> None:
    """Disable restriction mode to allow instruction creation/modification."""
    try:
        user = interaction.user
        logger.info("User ( %s ) is disabling restriction mode", user)

        await interaction.response.defer(ephemeral=True)

        # Disable restriction mode through service layer
        result = restriction_service.disable_restriction(user.id)

        if result and result.get("success"):
            was_already_inactive = result.get("was_already_inactive", False)
            if was_already_inactive:
                logger.info(
                    "Restriction mode was already inactive when requested by user %s",
                    user,
                )
            else:
                logger.info("Restriction mode disabled by user %s", user)

            await interaction.followup.send(
                result["message"],
                ephemeral=True,
            )
        else:
            error_message = (
                result.get("message", "制限モードの無効化に失敗しました。")
                if result
                else "制限モードの無効化に失敗しました。"
            )
            logger.error("Failed to disable restriction mode for user %s", user)
            await interaction.followup.send(
                f"エラー: {error_message}",
                ephemeral=True,
            )

    except Exception as e:
        logger.exception("Error in unlock command: %s", e)
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "エラーが発生しました。システム管理者にお問い合わせください。",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                "エラーが発生しました。システム管理者にお問い合わせください。",
                ephemeral=True,
            )
