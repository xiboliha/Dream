"""Scheduler service for timed tasks like greetings."""

import asyncio
from datetime import datetime, time
from typing import Callable, Dict, List, Optional

from loguru import logger
import pytz


class ScheduledTask:
    """Represents a scheduled task."""

    def __init__(
        self,
        name: str,
        callback: Callable,
        hour: int,
        minute: int = 0,
        timezone: str = "Asia/Shanghai",
        enabled: bool = True,
    ):
        """Initialize scheduled task.

        Args:
            name: Task name
            callback: Async callback function
            hour: Hour to run (0-23)
            minute: Minute to run (0-59)
            timezone: Timezone for scheduling
            enabled: Whether task is enabled
        """
        self.name = name
        self.callback = callback
        self.hour = hour
        self.minute = minute
        self.timezone = timezone
        self.enabled = enabled
        self.last_run: Optional[datetime] = None

    def should_run(self, now: datetime) -> bool:
        """Check if task should run now.

        Args:
            now: Current datetime

        Returns:
            True if task should run
        """
        if not self.enabled:
            return False

        # Check if already run today
        if self.last_run:
            if self.last_run.date() == now.date():
                return False

        # Check if it's time to run
        return now.hour == self.hour and now.minute == self.minute

    async def run(self) -> None:
        """Execute the task."""
        try:
            logger.info(f"Running scheduled task: {self.name}")
            await self.callback()
            self.last_run = datetime.now(pytz.timezone(self.timezone))
            logger.info(f"Completed scheduled task: {self.name}")
        except Exception as e:
            logger.error(f"Scheduled task {self.name} failed: {e}")


class SchedulerService:
    """Service for managing scheduled tasks."""

    def __init__(self, timezone: str = "Asia/Shanghai"):
        """Initialize scheduler service.

        Args:
            timezone: Default timezone
        """
        self.timezone = timezone
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def add_task(
        self,
        name: str,
        callback: Callable,
        hour: int,
        minute: int = 0,
        enabled: bool = True,
    ) -> None:
        """Add a scheduled task.

        Args:
            name: Task name
            callback: Async callback function
            hour: Hour to run
            minute: Minute to run
            enabled: Whether task is enabled
        """
        task = ScheduledTask(
            name=name,
            callback=callback,
            hour=hour,
            minute=minute,
            timezone=self.timezone,
            enabled=enabled,
        )
        self._tasks[name] = task
        logger.info(f"Added scheduled task: {name} at {hour:02d}:{minute:02d}")

    def remove_task(self, name: str) -> bool:
        """Remove a scheduled task.

        Args:
            name: Task name

        Returns:
            True if task was removed
        """
        if name in self._tasks:
            del self._tasks[name]
            logger.info(f"Removed scheduled task: {name}")
            return True
        return False

    def enable_task(self, name: str) -> bool:
        """Enable a scheduled task.

        Args:
            name: Task name

        Returns:
            True if task was enabled
        """
        if name in self._tasks:
            self._tasks[name].enabled = True
            return True
        return False

    def disable_task(self, name: str) -> bool:
        """Disable a scheduled task.

        Args:
            name: Task name

        Returns:
            True if task was disabled
        """
        if name in self._tasks:
            self._tasks[name].enabled = False
            return True
        return False

    async def _run_loop(self) -> None:
        """Main scheduler loop."""
        logger.info("Scheduler loop started")

        while self._running:
            try:
                now = datetime.now(pytz.timezone(self.timezone))

                for task in self._tasks.values():
                    if task.should_run(now):
                        asyncio.create_task(task.run())

                # Sleep until next minute
                await asyncio.sleep(60 - now.second)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(60)

        logger.info("Scheduler loop stopped")

    def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Scheduler service started")

    async def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduler service stopped")

    def list_tasks(self) -> List[Dict]:
        """List all scheduled tasks.

        Returns:
            List of task info dicts
        """
        return [
            {
                "name": task.name,
                "hour": task.hour,
                "minute": task.minute,
                "enabled": task.enabled,
                "last_run": task.last_run.isoformat() if task.last_run else None,
            }
            for task in self._tasks.values()
        ]


# Global scheduler instance
_scheduler: Optional[SchedulerService] = None


def get_scheduler() -> SchedulerService:
    """Get global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = SchedulerService()
    return _scheduler


def init_scheduler(timezone: str = "Asia/Shanghai") -> SchedulerService:
    """Initialize global scheduler."""
    global _scheduler
    _scheduler = SchedulerService(timezone)
    return _scheduler
