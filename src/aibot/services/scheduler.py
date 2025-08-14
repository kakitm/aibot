import asyncio
import datetime
import os
from collections.abc import Callable, Coroutine
from typing import ClassVar, TypeVar

import pytz

from src.aibot.infrastructure.dao.usage import UsageDAO
from src.aibot.logger import logger

T = TypeVar("T")
TIMEZONE = pytz.timezone(os.getenv("TIMEZONE", "Asia/Tokyo"))


class TaskScheduler:
    """Scheduler for running tasks at specific times.

    This class provides functionality to schedule tasks to run at
    specific times, such as daily at midnight.
    """

    _background_tasks: ClassVar[set[asyncio.Task]] = set()

    @staticmethod
    async def _wait_until(dt: datetime.datetime) -> None:
        """Wait until a specific datetime.

        Parameters
        ----------
        dt : datetime.datetime
            Target datetime to wait for.

        """
        now = datetime.datetime.now(TIMEZONE)
        if dt < now:
            # If the target time is in the past, add one day
            dt = dt + datetime.timedelta(days=1)

        # Calculate seconds until the target time
        wait_seconds = (dt - now).total_seconds()
        logger.debug("Waiting for %s seconds until %s", wait_seconds, dt)
        await asyncio.sleep(wait_seconds)

    @staticmethod
    async def _schedule_daily(
        time: datetime.time,
        task: Callable[[], Coroutine[None, None, T]],
    ) -> None:
        """Schedule a task to run daily at a specific time.

        Parameters
        ----------
        time : datetime.time
            Time of day to run the task.
        task : Callable[[], Coroutine[None, None, T]]
            Coroutine function to execute.

        """
        while True:
            # Next run datetime
            now = datetime.datetime.now(TIMEZONE)
            next_run = datetime.datetime.combine(now.date(), time, TIMEZONE)

            # If it's already past the time today, schedule for tomorrow
            if now.time() > time:
                next_run = next_run + datetime.timedelta(days=1)

            # Wait until the scheduled time
            await TaskScheduler._wait_until(next_run)

            # Execute the task
            try:
                logger.info("Running scheduled task at %s", next_run)
                await task()
                logger.info("Scheduled task completed successfully")
            except Exception as err:
                logger.exception("Error in scheduled task: %s", err)

            # Wait a bit to avoid running the task twice if execution is very fast
            await asyncio.sleep(1)

    @staticmethod
    def start_reset_usage_scheduler() -> asyncio.Task:
        """Start scheduler to reset usage counts at midnight."""
        # Reset time - midnight (00:00:00)
        reset_time = datetime.time(0, 0, 0, tzinfo=TIMEZONE)

        async def reset_all_usage() -> None:
            await UsageDAO().RESET()
            logger.info("Successfully reset all user API usage counts")

        # Create and return the task
        return asyncio.create_task(TaskScheduler._schedule_daily(reset_time, reset_all_usage))

    @classmethod
    def start_all(cls) -> None:
        """Start all background schedulers and manage them."""
        # Start usage reset scheduler
        task = cls.start_reset_usage_scheduler()
        cls._background_tasks.add(task)
        task.add_done_callback(cls._background_tasks.discard)
        logger.info("All schedulers started successfully")

    @classmethod
    def stop_all(cls) -> None:
        """Stop all background schedulers."""
        for task in cls._background_tasks:
            task.cancel()
        cls._background_tasks.clear()
        logger.info("All schedulers stopped")
