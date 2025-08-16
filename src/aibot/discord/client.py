from discord import Client, Intents, app_commands

intents = Intents.default()
intents.message_content = True
intents.members = True


class BotClient(Client):
    """A singleton class for the bot client."""

    _instance: "BotClient"
    tree: app_commands.CommandTree

    def __init__(self) -> None:
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    @classmethod
    def get_instance(cls) -> "BotClient":
        """Get the singleton instance of the bot client."""
        if not hasattr(cls, "_instance"):
            cls._instance = cls()
        return cls._instance

    async def setup_hook(self) -> None:
        """Set up the bot.

        This function called once during bot initialization after login
        but before WebSocket connection.
        """
        # Syncs the application commands to Discord
        await self.tree.sync()

    async def on_ready(self) -> None:
        """Event handler called when the bot is ready."""
