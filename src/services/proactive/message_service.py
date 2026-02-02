"""Proactive messaging service for scheduled greetings and idle detection."""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable

from loguru import logger
import pytz


class ProactiveMessageService:
    """Service for sending proactive messages based on time and user activity."""

    def __init__(self, timezone: str = "Asia/Shanghai"):
        """Initialize proactive message service.

        Args:
            timezone: Timezone for scheduling
        """
        self.timezone = timezone
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._message_callback: Optional[Callable] = None

        # Track last activity per user
        self._user_last_activity: Dict[int, datetime] = {}

        # Track last proactive message per user (to avoid spam)
        self._user_last_proactive: Dict[int, datetime] = {}

        # Pending messages queue (for frontend polling)
        self._pending_messages: Dict[int, List[Dict]] = {}

        # Scheduled greeting templates (支持多条连发)
        self._greeting_templates = {
            "morning": [
                ["早安~"],
                ["起床了吗"],
                ["早", "醒了没"],
                ["早上好呀", "今天也要加油"],
            ],
            "noon": [
                ["该吃午饭了"],
                ["中午了", "吃饭没"],
                ["午饭吃什么呀"],
                ["饿了", "想吃好吃的"],
            ],
            "afternoon": [
                ["午睡醒了吗"],
                ["下午好~"],
                ["睡醒了没", "我刚醒"],
                ["好困", "不想上班"],
            ],
            "dinner": [
                ["晚饭吃了吗"],
                ["该吃晚饭了"],
                ["晚上吃什么", "我好饿"],
                ["下班了", "累死了"],
            ],
            "night": [
                ["早点睡"],
                ["晚安~"],
                ["该睡觉了", "困了"],
                ["晚安", "明天见"],
                ["要睡了", "你也早点休息"],
            ],
        }

        # Proactive chat templates (主动找话题聊天)
        self._proactive_chat_templates = [
            # 分享日常
            ["今天好累啊", "加班到现在"],
            ["刚下班", "终于可以休息了"],
            ["在追剧", "好好看"],
            # 看到有趣的
            ["！！！", "我刚看到一个超搞笑的"],
            ["哈哈哈哈", "笑死我了"],
            # 想念
            ["在干嘛", "想你了"],
            ["突然想你了"],
            # 吐槽
            ["烦死了", "今天又出问题了"],
            ["好无聊啊"],
            # 分享心情
            ["今天天气好好", "想出去走走"],
            ["好饿", "想吃火锅"],
            ["困了", "但是睡不着"],
            # 突然想起
            ["对了", "你上次说的那个事怎么样了"],
            ["诶", "我突然想起来一件事"],
            # 撒娇
            ["哼", "你都不理我"],
            ["无聊", "陪我聊天"],
        ]

        # Idle reminder templates (when user hasn't replied) - 支持多条
        self._idle_templates = [
            ["在干嘛呢"],
            ["怎么不说话了"],
            ["人呢"],
            ["忙吗"],
            ["..."],
            ["哼"],
            ["你是不是把我忘了"],
            ["在吗", "怎么不回我"],
            ["...", "不理我吗"],
        ]

        # Idle threshold in minutes
        self.idle_threshold_minutes = 30

    def set_message_callback(self, callback: Callable) -> None:
        """Set callback for sending messages.

        Args:
            callback: Async function(user_id, message) to send message
        """
        self._message_callback = callback

    def update_user_activity(self, user_id: int) -> None:
        """Update user's last activity timestamp.

        Args:
            user_id: User ID
        """
        now = datetime.now(pytz.timezone(self.timezone))
        self._user_last_activity[user_id] = now
        logger.debug(f"Updated activity for user {user_id}")

    def get_pending_messages(self, user_id: int) -> List[Dict]:
        """Get and clear pending proactive messages for user.

        Args:
            user_id: User ID

        Returns:
            List of pending messages
        """
        messages = self._pending_messages.get(user_id, [])
        if messages:
            self._pending_messages[user_id] = []
        return messages

    def _add_pending_message(self, user_id: int, message: str, msg_type: str = "proactive") -> None:
        """Add a pending message for user.

        Args:
            user_id: User ID
            message: Message content
            msg_type: Message type (proactive, greeting, idle)
        """
        if user_id not in self._pending_messages:
            self._pending_messages[user_id] = []

        self._pending_messages[user_id].append({
            "content": message,
            "type": msg_type,
            "timestamp": datetime.now(pytz.timezone(self.timezone)).isoformat(),
        })

        logger.info(f"Added proactive message for user {user_id}: {message}")

    def _add_pending_messages(self, user_id: int, messages: List[str], msg_type: str = "proactive") -> None:
        """Add multiple pending messages for user (连发多条).

        Args:
            user_id: User ID
            messages: List of message contents
            msg_type: Message type
        """
        if user_id not in self._pending_messages:
            self._pending_messages[user_id] = []

        now = datetime.now(pytz.timezone(self.timezone))
        for i, message in enumerate(messages):
            self._pending_messages[user_id].append({
                "content": message,
                "type": msg_type,
                "timestamp": now.isoformat(),
                "sequence": i,  # 标记顺序，前端可用于控制延迟
            })

        # Update last proactive time
        self._user_last_proactive[user_id] = now

        logger.info(f"Added {len(messages)} proactive messages for user {user_id}: {messages}")

    def _should_send_proactive(self, user_id: int, min_interval_minutes: int = 60) -> bool:
        """Check if we should send a proactive message to user.

        Args:
            user_id: User ID
            min_interval_minutes: Minimum minutes between proactive messages

        Returns:
            True if we should send
        """
        now = datetime.now(pytz.timezone(self.timezone))

        # Check last proactive message time
        last_proactive = self._user_last_proactive.get(user_id)
        if last_proactive:
            elapsed = (now - last_proactive).total_seconds() / 60
            if elapsed < min_interval_minutes:
                return False

        return True

    def _get_greeting_type(self, hour: int) -> Optional[str]:
        """Get greeting type based on hour.

        Args:
            hour: Current hour (0-23)

        Returns:
            Greeting type or None
        """
        from config.settings import settings

        if hour == settings.morning_greeting_hour:
            return "morning"
        elif hour == settings.noon_greeting_hour:
            return "noon"
        elif hour == settings.afternoon_nap_hour:
            return "afternoon"
        elif hour == settings.dinner_greeting_hour:
            return "dinner"
        elif hour == settings.night_greeting_hour:
            return "night"
        return None

    async def _check_scheduled_greetings(self, now: datetime) -> None:
        """Check and send scheduled greetings.

        Args:
            now: Current datetime
        """
        greeting_type = self._get_greeting_type(now.hour)
        if not greeting_type:
            return

        # Only trigger at minute 0
        if now.minute != 0:
            return

        # Send to all active users
        for user_id in list(self._user_last_activity.keys()):
            if self._should_send_proactive(user_id, min_interval_minutes=60):
                # 随机选择一个模板（可能是单条或多条）
                messages = random.choice(self._greeting_templates[greeting_type])
                self._add_pending_messages(user_id, messages, f"greeting_{greeting_type}")

    async def _check_idle_users(self, now: datetime) -> None:
        """Check for idle users and send reminders.

        Args:
            now: Current datetime
        """
        for user_id, last_activity in list(self._user_last_activity.items()):
            elapsed_minutes = (now - last_activity).total_seconds() / 60

            # Check if user has been idle
            if elapsed_minutes >= self.idle_threshold_minutes:
                # Don't spam - check if we sent a proactive message recently
                if self._should_send_proactive(user_id, min_interval_minutes=30):
                    # 随机选择一个模板（可能是单条或多条）
                    messages = random.choice(self._idle_templates)
                    self._add_pending_messages(user_id, messages, "idle_reminder")

    async def _check_random_chat(self, now: datetime) -> None:
        """Randomly initiate chat with active users (主动找话题).

        Args:
            now: Current datetime
        """
        # Only during reasonable hours (9:00 - 23:00)
        if now.hour < 9 or now.hour >= 23:
            return

        # Low probability to trigger (about once every 2-3 hours on average)
        if random.random() > 0.02:  # 2% chance per minute check
            return

        for user_id in list(self._user_last_activity.keys()):
            # Check if user was active recently (within last 2 hours)
            last_activity = self._user_last_activity.get(user_id)
            if not last_activity:
                continue

            elapsed_minutes = (now - last_activity).total_seconds() / 60
            if elapsed_minutes > 120:  # Skip if inactive for too long
                continue

            if self._should_send_proactive(user_id, min_interval_minutes=90):
                messages = random.choice(self._proactive_chat_templates)
                self._add_pending_messages(user_id, messages, "random_chat")

    async def _run_loop(self) -> None:
        """Main service loop."""
        logger.info("Proactive message service started")

        while self._running:
            try:
                now = datetime.now(pytz.timezone(self.timezone))

                # Check scheduled greetings
                await self._check_scheduled_greetings(now)

                # Check idle users
                await self._check_idle_users(now)

                # Check random chat (主动找话题)
                await self._check_random_chat(now)

                # Sleep for 1 minute
                await asyncio.sleep(60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Proactive message service error: {e}")
                await asyncio.sleep(60)

        logger.info("Proactive message service stopped")

    def start(self) -> None:
        """Start the service."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Proactive message service started")

    async def stop(self) -> None:
        """Stop the service."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Proactive message service stopped")


# Global instance
_proactive_service: Optional[ProactiveMessageService] = None


def get_proactive_service() -> ProactiveMessageService:
    """Get global proactive message service instance."""
    global _proactive_service
    if _proactive_service is None:
        _proactive_service = ProactiveMessageService()
    return _proactive_service


def init_proactive_service(timezone: str = "Asia/Shanghai") -> ProactiveMessageService:
    """Initialize global proactive message service."""
    global _proactive_service
    _proactive_service = ProactiveMessageService(timezone)
    return _proactive_service
