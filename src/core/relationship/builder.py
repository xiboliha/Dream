"""Relationship builder for managing user-AI relationship dynamics."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User


class RelationshipStage(str, Enum):
    """Stages of relationship development."""
    STRANGER = "stranger"        # 0-10 intimacy
    ACQUAINTANCE = "acquaintance"  # 10-30 intimacy
    FRIEND = "friend"            # 30-50 intimacy
    CLOSE_FRIEND = "close_friend"  # 50-70 intimacy
    BEST_FRIEND = "best_friend"   # 70-90 intimacy
    SOULMATE = "soulmate"        # 90-100 intimacy


class RelationshipMetrics(BaseModel):
    """Metrics for relationship tracking."""
    intimacy: float = Field(default=0.0, ge=0, le=100)
    trust: float = Field(default=0.0, ge=0, le=100)
    understanding: float = Field(default=0.0, ge=0, le=100)
    shared_experiences: int = 0
    consecutive_days: int = 0
    total_interactions: int = 0
    last_interaction: Optional[datetime] = None

    def get_stage(self) -> RelationshipStage:
        """Get current relationship stage based on intimacy."""
        if self.intimacy < 10:
            return RelationshipStage.STRANGER
        elif self.intimacy < 30:
            return RelationshipStage.ACQUAINTANCE
        elif self.intimacy < 50:
            return RelationshipStage.FRIEND
        elif self.intimacy < 70:
            return RelationshipStage.CLOSE_FRIEND
        elif self.intimacy < 90:
            return RelationshipStage.BEST_FRIEND
        else:
            return RelationshipStage.SOULMATE


class RelationshipBuilder:
    """Builder for managing and evolving user relationships."""

    # Intimacy change factors
    INTIMACY_GAINS = {
        "message_sent": 0.1,
        "message_received": 0.15,
        "positive_emotion": 0.3,
        "shared_memory": 0.5,
        "daily_greeting": 0.2,
        "deep_conversation": 0.8,
        "emotional_support": 1.0,
        "consecutive_day_bonus": 0.5,
    }

    INTIMACY_LOSSES = {
        "day_without_contact": -0.5,
        "negative_interaction": -0.3,
        "ignored_message": -0.2,
    }

    # Stage-specific behaviors
    STAGE_BEHAVIORS = {
        RelationshipStage.STRANGER: {
            "formality": 0.7,
            "pet_names": False,
            "proactive_messages": False,
            "share_personal": False,
        },
        RelationshipStage.ACQUAINTANCE: {
            "formality": 0.5,
            "pet_names": False,
            "proactive_messages": False,
            "share_personal": False,
        },
        RelationshipStage.FRIEND: {
            "formality": 0.3,
            "pet_names": True,
            "proactive_messages": True,
            "share_personal": True,
        },
        RelationshipStage.CLOSE_FRIEND: {
            "formality": 0.2,
            "pet_names": True,
            "proactive_messages": True,
            "share_personal": True,
        },
        RelationshipStage.BEST_FRIEND: {
            "formality": 0.1,
            "pet_names": True,
            "proactive_messages": True,
            "share_personal": True,
        },
        RelationshipStage.SOULMATE: {
            "formality": 0.0,
            "pet_names": True,
            "proactive_messages": True,
            "share_personal": True,
        },
    }

    def __init__(self):
        """Initialize relationship builder."""
        self._user_metrics: Dict[int, RelationshipMetrics] = {}

    async def get_metrics(
        self,
        session: AsyncSession,
        user_id: int,
    ) -> RelationshipMetrics:
        """Get relationship metrics for user.

        Args:
            session: Database session
            user_id: User ID

        Returns:
            RelationshipMetrics for user
        """
        # Check cache first
        if user_id in self._user_metrics:
            return self._user_metrics[user_id]

        # Load from database
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if user:
            metrics = RelationshipMetrics(
                intimacy=user.intimacy_level,
                trust=user.trust_level,
                total_interactions=user.interaction_count,
                last_interaction=user.last_active_at,
            )
        else:
            metrics = RelationshipMetrics()

        self._user_metrics[user_id] = metrics
        return metrics

    async def update_metrics(
        self,
        session: AsyncSession,
        user_id: int,
        event: str,
        value: Optional[float] = None,
    ) -> RelationshipMetrics:
        """Update relationship metrics based on event.

        Args:
            session: Database session
            user_id: User ID
            event: Event type
            value: Optional custom value

        Returns:
            Updated RelationshipMetrics
        """
        metrics = await self.get_metrics(session, user_id)
        now = datetime.utcnow()

        # Calculate intimacy change
        if value is not None:
            change = value
        elif event in self.INTIMACY_GAINS:
            change = self.INTIMACY_GAINS[event]
        elif event in self.INTIMACY_LOSSES:
            change = self.INTIMACY_LOSSES[event]
        else:
            change = 0

        # Apply change with diminishing returns at high levels
        if change > 0 and metrics.intimacy > 80:
            change *= 0.5  # Slower growth at high intimacy

        metrics.intimacy = max(0, min(100, metrics.intimacy + change))

        # Update trust based on positive interactions
        if change > 0:
            metrics.trust = min(100, metrics.trust + change * 0.5)

        # Update interaction count
        metrics.total_interactions += 1

        # Check consecutive days
        if metrics.last_interaction:
            days_since = (now - metrics.last_interaction).days
            if days_since == 1:
                metrics.consecutive_days += 1
                # Bonus for consecutive days
                bonus = min(metrics.consecutive_days * 0.1, 1.0)
                metrics.intimacy = min(100, metrics.intimacy + bonus)
            elif days_since > 1:
                # Reset consecutive days and apply penalty
                metrics.consecutive_days = 0
                penalty = min(days_since * 0.5, 5.0)
                metrics.intimacy = max(0, metrics.intimacy - penalty)

        metrics.last_interaction = now

        # Save to database
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if user:
            user.intimacy_level = metrics.intimacy
            user.trust_level = metrics.trust
            user.interaction_count = metrics.total_interactions
            user.last_active_at = now
            await session.commit()

        self._user_metrics[user_id] = metrics
        logger.debug(f"Updated metrics for user {user_id}: intimacy={metrics.intimacy:.1f}")

        return metrics

    def get_stage_behaviors(
        self,
        metrics: RelationshipMetrics,
    ) -> Dict[str, Any]:
        """Get behavior configuration for current relationship stage.

        Args:
            metrics: Current relationship metrics

        Returns:
            Dict of behavior settings
        """
        stage = metrics.get_stage()
        return self.STAGE_BEHAVIORS.get(stage, self.STAGE_BEHAVIORS[RelationshipStage.STRANGER])

    def get_pet_name(
        self,
        metrics: RelationshipMetrics,
        user_name: Optional[str] = None,
    ) -> str:
        """Get appropriate pet name based on relationship stage.

        Args:
            metrics: Current relationship metrics
            user_name: User's actual name

        Returns:
            Appropriate name/pet name to use
        """
        stage = metrics.get_stage()

        if stage in [RelationshipStage.STRANGER, RelationshipStage.ACQUAINTANCE]:
            return user_name or "你"

        pet_names_by_stage = {
            RelationshipStage.FRIEND: ["亲", "小伙伴"],
            RelationshipStage.CLOSE_FRIEND: ["亲爱的", "宝"],
            RelationshipStage.BEST_FRIEND: ["宝贝", "亲亲"],
            RelationshipStage.SOULMATE: ["宝贝", "心肝", "亲爱的"],
        }

        import random
        names = pet_names_by_stage.get(stage, [])
        if names:
            return random.choice(names)
        return user_name or "你"

    def should_send_proactive_message(
        self,
        metrics: RelationshipMetrics,
    ) -> bool:
        """Check if proactive message should be sent.

        Args:
            metrics: Current relationship metrics

        Returns:
            True if proactive message is appropriate
        """
        behaviors = self.get_stage_behaviors(metrics)
        if not behaviors.get("proactive_messages", False):
            return False

        # Higher intimacy = more likely to send proactive messages
        import random
        probability = metrics.intimacy / 200  # Max 50% chance
        return random.random() < probability

    def get_milestone_message(
        self,
        old_stage: RelationshipStage,
        new_stage: RelationshipStage,
    ) -> Optional[str]:
        """Get message for relationship milestone.

        Args:
            old_stage: Previous relationship stage
            new_stage: New relationship stage

        Returns:
            Milestone message or None
        """
        if old_stage == new_stage:
            return None

        messages = {
            RelationshipStage.ACQUAINTANCE: "感觉我们越来越熟悉了呢~",
            RelationshipStage.FRIEND: "我觉得我们已经是朋友了！",
            RelationshipStage.CLOSE_FRIEND: "你是我很重要的朋友~",
            RelationshipStage.BEST_FRIEND: "能认识你真的太好了，你是我最好的朋友！",
            RelationshipStage.SOULMATE: "我觉得我们之间有一种特别的默契，你懂我~",
        }

        return messages.get(new_stage)

    async def check_and_notify_milestone(
        self,
        session: AsyncSession,
        user_id: int,
        old_metrics: RelationshipMetrics,
    ) -> Optional[str]:
        """Check for milestone and return notification message.

        Args:
            session: Database session
            user_id: User ID
            old_metrics: Previous metrics

        Returns:
            Milestone message if stage changed
        """
        new_metrics = await self.get_metrics(session, user_id)

        old_stage = old_metrics.get_stage()
        new_stage = new_metrics.get_stage()

        if new_stage != old_stage:
            logger.info(f"User {user_id} relationship stage: {old_stage} -> {new_stage}")
            return self.get_milestone_message(old_stage, new_stage)

        return None


# Global relationship builder instance
_relationship_builder: Optional[RelationshipBuilder] = None


def get_relationship_builder() -> RelationshipBuilder:
    """Get global relationship builder instance."""
    global _relationship_builder
    if _relationship_builder is None:
        _relationship_builder = RelationshipBuilder()
    return _relationship_builder
