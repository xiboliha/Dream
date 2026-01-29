"""Main coordinator/dispatcher for message processing workflow."""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.conversation import ConversationEngine
from src.core.personality import get_personality_system
from src.core.relationship import get_relationship_builder, RelationshipMetrics
from src.core.security import get_content_filter, get_rate_limiter
from src.services.emotion import get_emotion_analyzer, get_emotion_tracker
from src.services.storage import get_database_service


class MessageContext:
    """Context object for message processing."""

    def __init__(
        self,
        user_id: int,
        wechat_id: str,
        nickname: str,
        content: str,
        message_type: str = "text",
        msg_id: Optional[str] = None,
    ):
        self.user_id = user_id
        self.wechat_id = wechat_id
        self.nickname = nickname
        self.content = content
        self.message_type = message_type
        self.msg_id = msg_id
        self.timestamp = datetime.utcnow()

        # Processing results
        self.emotion_result = None
        self.filter_result = None
        self.relationship_metrics = None
        self.personality_config = None
        self.response: Optional[str] = None
        self.metadata: Dict[str, Any] = {}


class Coordinator:
    """Main coordinator for orchestrating message processing."""

    def __init__(self, conversation_engine: ConversationEngine):
        """Initialize coordinator.

        Args:
            conversation_engine: Conversation engine instance
        """
        self.conversation_engine = conversation_engine
        self.content_filter = get_content_filter()
        self.rate_limiter = get_rate_limiter()
        self.emotion_analyzer = get_emotion_analyzer()
        self.emotion_tracker = get_emotion_tracker()
        self.personality_system = get_personality_system()
        self.relationship_builder = get_relationship_builder()

    async def process_message(
        self,
        session: AsyncSession,
        context: MessageContext,
    ) -> MessageContext:
        """Process incoming message through the full pipeline.

        Args:
            session: Database session
            context: Message context

        Returns:
            Updated context with response
        """
        try:
            # Step 1: Rate limiting
            is_allowed, rate_error = self.rate_limiter.check_rate_limit(context.user_id)
            if not is_allowed:
                context.response = rate_error
                context.metadata["blocked_by"] = "rate_limit"
                return context

            # Step 2: Content filtering
            context.filter_result = self.content_filter.filter_input(context.content)
            if not context.filter_result.is_safe:
                if context.filter_result.action == "redirect":
                    context.response = context.filter_result.modified_content
                elif context.filter_result.action == "block":
                    context.response = context.filter_result.reason
                context.metadata["blocked_by"] = "content_filter"
                return context

            # Step 3: Emotion analysis
            context.emotion_result = self.emotion_analyzer.analyze(context.content)
            self.emotion_tracker.record(context.user_id, context.emotion_result)

            # Step 4: Get relationship metrics
            context.relationship_metrics = await self.relationship_builder.get_metrics(
                session, context.user_id
            )
            old_metrics = RelationshipMetrics(**context.relationship_metrics.model_dump())

            # Step 5: Get personality configuration
            context.personality_config = self.personality_system.get_personality_for_user(
                context.user_id
            )

            # Adjust personality based on emotion and relationship
            self._adjust_personality_for_context(context)

            # Step 6: Generate response
            result = await self.conversation_engine.process_message(
                session=session,
                user_id=context.user_id,
                message_content=context.content,
                personality_config=context.personality_config,
            )
            context.response = result["response"]
            context.metadata.update(result)

            # Step 7: Filter output
            output_filter = self.content_filter.filter_output(context.response)
            if output_filter.modified_content:
                context.response = output_filter.modified_content

            # Step 8: Update relationship metrics
            event = self._determine_interaction_event(context)
            await self.relationship_builder.update_metrics(session, context.user_id, event)

            # Step 9: Check for relationship milestone
            milestone_msg = await self.relationship_builder.check_and_notify_milestone(
                session, context.user_id, old_metrics
            )
            if milestone_msg:
                context.response += f"\n\n{milestone_msg}"

            # Step 10: Evolve personality based on interaction
            self._evolve_personality(context)

            return context

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            context.response = "抱歉，我好像遇到了一点问题，稍后再聊好吗？"
            context.metadata["error"] = str(e)
            return context

    def _adjust_personality_for_context(self, context: MessageContext) -> None:
        """Adjust personality configuration based on context.

        Args:
            context: Message context
        """
        if not context.personality_config:
            return

        # Adjust based on emotion
        if context.emotion_result:
            emotion = context.emotion_result.primary_emotion
            intensity = context.emotion_result.intensity

            # Get emotional response style
            response_style = self.personality_system.get_emotional_response_style(
                emotion.value
            )

            # Adjust traits based on emotion
            if emotion.value == "sad":
                context.personality_config["traits"]["empathy"] = min(
                    1.0, context.personality_config["traits"].get("empathy", 0.7) + 0.2
                )
            elif emotion.value == "angry":
                context.personality_config["traits"]["patience"] = min(
                    1.0, context.personality_config["traits"].get("patience", 0.7) + 0.2
                )

        # Adjust based on relationship stage
        if context.relationship_metrics:
            behaviors = self.relationship_builder.get_stage_behaviors(
                context.relationship_metrics
            )
            context.personality_config["language_style"]["formality"] = behaviors.get(
                "formality", 0.5
            )
            context.personality_config["language_style"]["pet_names"] = behaviors.get(
                "pet_names", False
            )

    def _determine_interaction_event(self, context: MessageContext) -> str:
        """Determine the type of interaction event.

        Args:
            context: Message context

        Returns:
            Event type string
        """
        if context.emotion_result:
            emotion = context.emotion_result.primary_emotion
            if emotion.value in ["happy", "loving", "excited"]:
                return "positive_emotion"
            elif emotion.value in ["sad", "anxious", "fearful"]:
                return "emotional_support"

        # Check for deep conversation indicators
        if len(context.content) > 100:
            return "deep_conversation"

        return "message_received"

    def _evolve_personality(self, context: MessageContext) -> None:
        """Evolve personality based on interaction.

        Args:
            context: Message context
        """
        if not context.emotion_result:
            return

        interaction_data = {
            "user_emotion": context.emotion_result.primary_emotion.value,
            "intensity": context.emotion_result.intensity,
            "positive_feedback": context.emotion_result.primary_emotion.value in [
                "happy", "loving", "excited"
            ],
        }

        self.personality_system.evolve_personality(
            context.user_id, interaction_data
        )


class WorkflowState:
    """State management for conversation workflows."""

    def __init__(self):
        self._user_states: Dict[int, Dict[str, Any]] = {}

    def get_state(self, user_id: int) -> Dict[str, Any]:
        """Get workflow state for user."""
        if user_id not in self._user_states:
            self._user_states[user_id] = {
                "current_flow": None,
                "flow_data": {},
                "last_updated": datetime.utcnow(),
            }
        return self._user_states[user_id]

    def set_flow(self, user_id: int, flow_name: str, data: Dict[str, Any] = None) -> None:
        """Set current workflow for user."""
        state = self.get_state(user_id)
        state["current_flow"] = flow_name
        state["flow_data"] = data or {}
        state["last_updated"] = datetime.utcnow()

    def clear_flow(self, user_id: int) -> None:
        """Clear workflow for user."""
        if user_id in self._user_states:
            self._user_states[user_id]["current_flow"] = None
            self._user_states[user_id]["flow_data"] = {}

    def is_in_flow(self, user_id: int) -> bool:
        """Check if user is in a workflow."""
        state = self.get_state(user_id)
        return state["current_flow"] is not None


# Global instances
_coordinator: Optional[Coordinator] = None
_workflow_state: Optional[WorkflowState] = None


def get_coordinator() -> Coordinator:
    """Get global coordinator instance."""
    global _coordinator
    if _coordinator is None:
        raise RuntimeError("Coordinator not initialized")
    return _coordinator


def init_coordinator(conversation_engine: ConversationEngine) -> Coordinator:
    """Initialize global coordinator."""
    global _coordinator
    _coordinator = Coordinator(conversation_engine)
    return _coordinator


def get_workflow_state() -> WorkflowState:
    """Get global workflow state instance."""
    global _workflow_state
    if _workflow_state is None:
        _workflow_state = WorkflowState()
    return _workflow_state
