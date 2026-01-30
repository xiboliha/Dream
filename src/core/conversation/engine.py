"""Conversation engine for managing dialogue flow."""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.conversation import (
    Conversation,
    Message,
    MessageType,
    MessageRole,
    ConversationStatus,
    ConversationContext,
    MessageSchema,
)
from src.models.user import User
from src.services.ai import AIMessage, AIRole, AIServiceProvider
from src.services.memory import MemoryManager
from src.services.knowledge import DialogueKnowledgeBase
from src.services.tools import WeatherTool
from src.utils.helpers import generate_session_id, get_time_greeting, calculate_typing_delay


class ConversationEngine:
    """Engine for managing conversations and generating responses."""

    def __init__(
        self,
        ai_service: AIServiceProvider,
        memory_manager: MemoryManager,
        max_context_messages: int = 10,
        response_timeout: float = 30.0,
        dialogue_rag=None,
    ):
        """Initialize conversation engine.

        Args:
            ai_service: AI service for generating responses
            memory_manager: Memory manager for context
            max_context_messages: Maximum messages in context
            response_timeout: Response generation timeout
            dialogue_rag: Optional RAG service for dialogue retrieval
        """
        self.ai_service = ai_service
        self.memory_manager = memory_manager
        self.max_context_messages = max_context_messages
        self.response_timeout = response_timeout
        self.dialogue_rag = dialogue_rag

        # Load system prompt
        self._system_prompt = self._load_system_prompt()

        # Initialize dialogue knowledge base
        self.dialogue_kb = DialogueKnowledgeBase()

        # Kaomoji patterns to filter
        self._kaomoji_patterns = [
            r'\(.*?[・ω･ᴗ°▽╥︿◕ಠ益].*?\)',  # (｡・ω-)✧ style
            r'[（\(][^)）]*[・ω･ᴗ°▽╥︿◕ಠ益][^)）]*[）\)]',
            r'~\s*\([^)]+\)',  # ~(xxx) style
            r'\^[_\-\.]+\^',  # ^_^ ^-^ ^.^
            r'>\s*_\s*<',  # >_<
            r'=\s*[_\.]\s*=',  # =_= =.=
            r'[oO][_\.][oO]',  # o_o O.O
            r'[TtQq][_\.][TtQq]',  # T_T Q_Q
            r'[xX][_\.][xX]',  # x_x X.X
            r':-?[)(\]\[DPpOo3]',  # Western emoticons
            r'[;:]-?[)(\]\[DPpOo3]',
        ]

        # Initialize tools
        self.weather_tool = WeatherTool()

    def _filter_response(self, content: str) -> str:
        """Filter out kaomoji and excessive emoji from response."""
        import re

        filtered = content

        # Remove kaomoji patterns
        for pattern in self._kaomoji_patterns:
            filtered = re.sub(pattern, '', filtered)

        # Remove common kaomoji strings directly
        kaomoji_strings = [
            '(｡・ω-)✧', '(・ω・)', '(≧▽≦)', '(╯▽╰)', '(◕‿◕)',
            '(●\'◡\'●)', '(✿◠‿◠)', '(*^▽^*)', '(〃▽〃)', '(๑•̀ㅂ•́)و✧',
            '(ノ´▽`)ノ', '╮(╯▽╰)╭', '(づ｡◕‿‿◕｡)づ', '(っ´▽`)っ',
            '~(｡・ω-)✧', '～(｡・ω-)✧', '(｡･ω･｡)', '(・ω<)',
            '(≧∇≦)/', '(^_^)', '(^-^)', '(^.^)', '^_^', '^-^', '^.^',
            '(*≧ω≦)', '(✧ω✧)', '(◠‿◠)', '(｡♥‿♥｡)', '(灬ºωº灬)',
        ]
        for kaomoji in kaomoji_strings:
            filtered = filtered.replace(kaomoji, '')

        # Remove excessive emoji (keep max 1)
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )
        emojis = emoji_pattern.findall(filtered)
        if len(emojis) > 1:
            # Keep only the first emoji
            for emoji in emojis[1:]:
                filtered = filtered.replace(emoji, '', 1)

        # Clean up extra spaces and tildes
        filtered = re.sub(r'~+\s*$', '', filtered)  # Remove trailing ~
        filtered = re.sub(r'\s{2,}', ' ', filtered)  # Multiple spaces to one
        filtered = filtered.strip()

        return filtered

    async def _check_and_get_weather(self, user_message: str) -> Optional[str]:
        """Check if user is asking about weather and fetch if needed.

        Args:
            user_message: User's message

        Returns:
            Weather info string or None
        """
        import re

        # Weather keywords
        weather_keywords = ['天气', '气温', '温度', '下雨', '下雪', '晴天', '阴天', '多少度', '冷不冷', '热不热', '冷吗', '热吗']

        # Check if message contains weather-related keywords
        if not any(kw in user_message for kw in weather_keywords):
            return None

        # Try to extract city name
        city_patterns = [
            r'([^\s，。？！]+?)(?:的|那边|这边)?天气',
            r'天气.*?([^\s，。？！]{2,4}(?:市|县|区)?)',
        ]

        city = None
        for pattern in city_patterns:
            match = re.search(pattern, user_message)
            if match:
                city = match.group(1)
                city = city.replace('现在', '').replace('今天', '').replace('明天', '').replace('你', '')
                if len(city) >= 2:
                    break

        # Default to 昆山 (her location) if no city specified
        if not city or len(city) < 2:
            city = "昆山"

        # Fetch weather with error handling
        try:
            weather = await self.weather_tool.get_weather(city)
            if weather.get("success"):
                return self.weather_tool.format_weather_response(weather)
        except Exception as e:
            logger.warning(f"Weather fetch failed: {e}")

        return None

    def _load_system_prompt(self) -> str:
        """Load system prompt from file."""
        import os
        prompt_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..", "config", "prompts", "system", "base_prompt.txt"
        )
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"System prompt not found: {prompt_path}")
            return "你是一个AI女友助手，名叫小爱。请用温暖、关心的语气与用户交流。"

    async def get_or_create_conversation(
        self,
        session: AsyncSession,
        user_id: int,
        create_new: bool = False,
    ) -> Conversation:
        """Get active conversation or create new one.

        Args:
            session: Database session
            user_id: User ID
            create_new: Force create new conversation

        Returns:
            Conversation instance
        """
        if not create_new:
            # Try to get active conversation
            result = await session.execute(
                select(Conversation)
                .where(
                    and_(
                        Conversation.user_id == user_id,
                        Conversation.status == ConversationStatus.ACTIVE.value,
                    )
                )
                .order_by(desc(Conversation.last_message_at))
                .limit(1)
            )
            conversation = result.scalar_one_or_none()

            if conversation:
                return conversation

        # Create new conversation
        conversation = Conversation(
            user_id=user_id,
            session_id=generate_session_id(),
            status=ConversationStatus.ACTIVE.value,
        )
        session.add(conversation)
        await session.commit()
        await session.refresh(conversation)

        logger.info(f"Created new conversation {conversation.session_id} for user {user_id}")
        return conversation

    async def add_message(
        self,
        session: AsyncSession,
        conversation: Conversation,
        role: str,
        content: str,
        message_type: str = MessageType.TEXT.value,
        **kwargs,
    ) -> Message:
        """Add a message to the conversation.

        Args:
            session: Database session
            conversation: Conversation instance
            role: Message role (user/assistant/system)
            content: Message content
            message_type: Type of message
            **kwargs: Additional message attributes

        Returns:
            Created Message instance
        """
        message = Message(
            conversation_id=conversation.id,
            user_id=conversation.user_id,
            role=role,
            message_type=message_type,
            content=content,
            **kwargs,
        )
        session.add(message)

        # Update conversation stats
        conversation.message_count += 1
        conversation.last_message_at = datetime.utcnow()
        if role == MessageRole.USER.value:
            conversation.user_message_count += 1
        elif role == MessageRole.ASSISTANT.value:
            conversation.assistant_message_count += 1

        await session.commit()
        await session.refresh(message)

        return message

    async def get_conversation_history(
        self,
        session: AsyncSession,
        conversation: Conversation,
        limit: Optional[int] = None,
    ) -> List[Message]:
        """Get conversation message history.

        Args:
            session: Database session
            conversation: Conversation instance
            limit: Maximum messages to return

        Returns:
            List of messages
        """
        query = (
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(desc(Message.created_at))
        )

        if limit:
            query = query.limit(limit)

        result = await session.execute(query)
        messages = list(result.scalars().all())
        messages.reverse()  # Chronological order

        return messages

    async def build_context(
        self,
        session: AsyncSession,
        conversation: Conversation,
        user_message: str,
    ) -> ConversationContext:
        """Build conversation context for AI.

        Args:
            session: Database session
            conversation: Conversation instance
            user_message: Current user message

        Returns:
            ConversationContext with all relevant information
        """
        # Get message history
        history = await self.get_conversation_history(
            session, conversation, limit=self.max_context_messages
        )

        # Convert to schemas
        messages = [
            MessageSchema(
                user_id=msg.user_id,
                role=msg.role,
                content=msg.content,
                message_type=msg.message_type,
                created_at=msg.created_at,
            )
            for msg in history
        ]

        # Get user memory profile
        user_profile = await self.memory_manager.build_user_profile(
            session, conversation.user_id
        )

        # Search for relevant memories based on current message
        relevant_memories = await self.memory_manager.search_memories(
            session, conversation.user_id, user_message, limit=5
        )

        context = ConversationContext(
            user_id=conversation.user_id,
            session_id=conversation.session_id,
            messages=messages,
            user_profile=user_profile.model_dump() if user_profile else None,
            relevant_memories=[
                {"key": m.key, "value": m.value, "type": m.memory_type}
                for m in relevant_memories
            ],
            current_mood=conversation.mood,
            topic=conversation.topic,
        )

        return context

    def _build_system_prompt(
        self,
        context: ConversationContext,
        personality_config: Optional[Dict[str, Any]] = None,
        user_message: str = "",
    ) -> str:
        """Build system prompt with context.

        Args:
            context: Conversation context
            personality_config: Optional personality configuration
            user_message: Current user message for few-shot matching

        Returns:
            Formatted system prompt
        """
        # Get current time
        now = datetime.now()
        current_time = now.strftime("%Y年%m月%d日 %H:%M 星期") + ["一", "二", "三", "四", "五", "六", "日"][now.weekday()]

        # Get user profile context
        user_profile_text = ""
        if context.user_profile:
            from src.models.memory import UserMemoryProfile
            profile = UserMemoryProfile(**context.user_profile)
            user_profile_text = profile.to_prompt_context()

        # Format recent memories
        recent_memories_text = ""
        if context.relevant_memories:
            recent_memories_text = "\n".join([
                f"- {m['key']}: {m['value']}"
                for m in context.relevant_memories[:5]
            ])

        # Format conversation context
        conversation_context_text = ""
        if context.messages:
            recent = context.messages[-5:]
            conversation_context_text = "\n".join([
                f"{m.role}: {m.content[:100]}..."
                for m in recent
            ])

        # Build prompt
        prompt = self._system_prompt.format(
            current_time=current_time,
            user_profile=user_profile_text or "暂无用户信息",
            recent_memories=recent_memories_text or "暂无相关记忆",
            important_memories="",
            conversation_context=conversation_context_text or "新对话开始",
        )

        # Add few-shot examples from dialogue knowledge base
        if user_message:
            few_shot_prompt = self.dialogue_kb.build_few_shot_prompt(user_message)
            if few_shot_prompt:
                prompt += f"\n\n{few_shot_prompt}"

        # Add personality traits if provided
        if personality_config:
            traits = personality_config.get("traits", {})
            style = personality_config.get("language_style", {})
            prompt += f"\n\n【人格特质】\n"
            prompt += f"- 温暖程度: {traits.get('warmth', 0.7)}\n"
            prompt += f"- 活泼程度: {traits.get('playfulness', 0.5)}\n"
            prompt += f"- 表情使用: {'多' if style.get('emoji_usage', 0.5) > 0.5 else '少'}\n"

        return prompt

    async def generate_response(
        self,
        session: AsyncSession,
        conversation: Conversation,
        user_message: str,
        personality_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate AI response to user message.

        Args:
            session: Database session
            conversation: Conversation instance
            user_message: User's message
            personality_config: Optional personality configuration

        Returns:
            Generated response text
        """
        start_time = datetime.utcnow()

        # Check if user is asking about weather
        weather_info = await self._check_and_get_weather(user_message)

        # Search for similar dialogues using RAG
        rag_context = ""
        if self.dialogue_rag and self.dialogue_rag.is_initialized:
            try:
                similar_dialogues = await self.dialogue_rag.search(user_message, top_k=3, threshold=0.5)
                if similar_dialogues:
                    rag_context = self.dialogue_rag.build_context_prompt(similar_dialogues)
                    logger.debug(f"RAG found {len(similar_dialogues)} similar dialogues")
            except Exception as e:
                logger.warning(f"RAG search failed: {e}")

        # Build context
        context = await self.build_context(session, conversation, user_message)

        # Build messages for AI (pass user_message for few-shot matching)
        system_prompt = self._build_system_prompt(context, personality_config, user_message)

        # Add RAG context if available
        if rag_context:
            system_prompt += f"\n\n{rag_context}"

        # If we have weather info, add it to the context
        if weather_info:
            system_prompt += f"\n\n【实时信息】\n{weather_info}"

        ai_messages = [
            AIMessage(role=AIRole.SYSTEM, content=system_prompt)
        ]

        # Add conversation history
        for msg in context.messages[-self.max_context_messages:]:
            role = AIRole.USER if msg.role == MessageRole.USER.value else AIRole.ASSISTANT
            ai_messages.append(AIMessage(role=role, content=msg.content))

        # Add current message
        ai_messages.append(AIMessage(role=AIRole.USER, content=user_message))

        # Generate response
        try:
            response = await asyncio.wait_for(
                self.ai_service.chat(
                    messages=ai_messages,
                    temperature=0.8,
                    max_tokens=500,
                ),
                timeout=self.response_timeout,
            )

            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            logger.info(
                f"Generated response for user {conversation.user_id} "
                f"in {response_time:.0f}ms, tokens: {response.total_tokens}"
            )

            # Filter out kaomoji and excessive emoji
            filtered_content = self._filter_response(response.content)
            return filtered_content

        except asyncio.TimeoutError:
            logger.error(f"Response generation timeout for user {conversation.user_id}")
            return "抱歉，我思考得太久了，能再说一遍吗？"
        except Exception as e:
            logger.error(f"Response generation error: {e}")
            return "哎呀，我好像走神了，你刚才说什么？"

    async def process_message(
        self,
        session: AsyncSession,
        user_id: int,
        message_content: str,
        message_type: str = MessageType.TEXT.value,
        personality_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Process incoming message and generate response.

        Args:
            session: Database session
            user_id: User ID
            message_content: Message content
            message_type: Type of message
            personality_config: Optional personality configuration

        Returns:
            Dict with response and metadata
        """
        # Get or create conversation
        conversation = await self.get_or_create_conversation(session, user_id)

        # Save user message
        user_msg = await self.add_message(
            session,
            conversation,
            role=MessageRole.USER.value,
            content=message_content,
            message_type=message_type,
        )

        # Generate response
        response_content = await self.generate_response(
            session,
            conversation,
            message_content,
            personality_config,
        )

        # Save assistant message
        assistant_msg = await self.add_message(
            session,
            conversation,
            role=MessageRole.ASSISTANT.value,
            content=response_content,
            message_type=MessageType.TEXT.value,
        )

        # 记录对话日志到监控系统
        from src.utils.logger import get_log_store
        response_time = (datetime.utcnow() - conversation.updated_at).total_seconds() * 1000 if conversation.updated_at else 0
        get_log_store().add_chat_log(
            user_id=user_id,
            user_msg=message_content,
            ai_response=response_content,
            response_time=response_time,
        )

        # Extract memories in background (don't wait)
        asyncio.create_task(
            self._extract_memories_background(
                session, user_id, conversation.id,
                [
                    {"role": "user", "content": message_content},
                    {"role": "assistant", "content": response_content},
                ]
            )
        )

        # Calculate typing delay for realistic feel
        typing_delay = calculate_typing_delay(response_content)

        return {
            "response": response_content,
            "conversation_id": conversation.id,
            "session_id": conversation.session_id,
            "message_id": assistant_msg.id,
            "typing_delay": typing_delay,
        }

    async def _extract_memories_background(
        self,
        session: AsyncSession,
        user_id: int,
        conversation_id: int,
        messages: List[Dict[str, str]],
    ) -> None:
        """Extract memories in background task."""
        try:
            await self.memory_manager.extract_memories(
                session, user_id, conversation_id, messages
            )
        except Exception as e:
            # 静默处理记忆提取错误，不影响主对话流程
            logger.debug(f"Background memory extraction skipped: {e}")

    async def end_conversation(
        self,
        session: AsyncSession,
        conversation: Conversation,
    ) -> None:
        """End a conversation session.

        Args:
            session: Database session
            conversation: Conversation to end
        """
        conversation.status = ConversationStatus.ENDED.value
        conversation.ended_at = datetime.utcnow()
        await session.commit()

        logger.info(f"Ended conversation {conversation.session_id}")

    async def get_greeting(
        self,
        session: AsyncSession,
        user_id: int,
        personality_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate a greeting message.

        Args:
            session: Database session
            user_id: User ID
            personality_config: Optional personality configuration

        Returns:
            Greeting message
        """
        time_greeting = get_time_greeting()

        # Get user profile for personalization
        profile = await self.memory_manager.build_user_profile(session, user_id)

        # Check if we know the user's name
        user_name = None
        for fact in profile.facts:
            if fact.key in ["real_name", "name", "姓名"]:
                user_name = fact.value
                break

        if user_name:
            greeting = f"{time_greeting}，{user_name}~"
        else:
            greeting = f"{time_greeting}~"

        # Add personality-specific flair
        if personality_config:
            expressions = personality_config.get("expressions", {})
            greetings = expressions.get("greetings", [])
            if greetings:
                import random
                greeting = random.choice(greetings)

        return greeting
