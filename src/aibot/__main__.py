import asyncio
import os

from dotenv import load_dotenv

# Load environment variables here
# This must happen before importing modules that rely on env vars
load_dotenv()

from src.aibot.discord.client import BotClient  # noqa: E402
from src.aibot.discord.commands import *  # noqa: E402, F403,
from src.aibot.infrastructure.dao.connection import ConnectionDAO  # noqa: E402
from src.aibot.infrastructure.dao.instruction import InstructionDAO  # noqa: E402
from src.aibot.infrastructure.dao.usage import UsageDAO  # noqa: E402
from src.aibot.logger import logger  # noqa: E402
from src.aibot.services.scheduler import TaskScheduler  # noqa: E402


async def main() -> None:  # noqa: D103
    # Create database tables
    await ConnectionDAO().create_tables()
    await InstructionDAO().create_table()
    await UsageDAO().create_tables()

    DISCORD_BOT_TOKEN: str = os.environ["DISCORD_BOT_TOKEN"]  # noqa: N806

    client = BotClient.get_instance()

    # Start all background schedulers
    TaskScheduler.start_all()

    try:
        await client.start(DISCORD_BOT_TOKEN)
    except Exception:
        logger.exception("Failed to start bot")
    finally:
        TaskScheduler.stop_all()
        logger.info("Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
