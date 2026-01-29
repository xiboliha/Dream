"""Memory manager for coordinating short-term and long-term memory."""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.memory import (
    ShortTermMemory,
    LongTermMemory,
    MemoryType,
    MemoryStatus,
    ShortTermMemorySchema,
    LongTermMemorySchema,
    UserMemoryProfile,
)
from src.services.ai import AIMessage, AIRole, AIServiceProvider
from src.services.storage.cache import CacheService


class MemoryManager:
    """Manager for coordinating memory operations."""

    def __init__(
        self,
        ai_service: AIServiceProvider,
        cache_service: Optional[CacheService] = None,
        short_term_limit: int = 20,
        consolidation_threshold: float = 0.7,
    ):
        """Initialize memory manager.

        Args:
            ai_service: AI service for memory extraction
            cache_service: Optional cache service
            short_term_limit: Maximum short-term memories per user
            consolidation_threshold: Threshold for memory consolidation
        """
        self.ai_service = ai_service
        self.cache = cache_service
        self.short_term_limit = short_term_limit
        self.consolidation_threshold = consolidation_threshold

        # Load prompts
        self._extraction_prompt = self._load_prompt("extraction_prompt.txt")
        self._consolidation_prompt = self._load_prompt("consolidation_prompt.txt")

    def _load_prompt(self, filename: str) -> str:
        """Load prompt template from file."""
        import os
        prompt_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..", "config", "prompts", "memory", filename
        )
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"Prompt file not found: {prompt_path}")
            return ""

    async def extract_memories(
        self,
        session: AsyncSession,
        user_id: int,
        conversation_id: int,
        messages: List[Dict[str, str]],
    ) -> List[ShortTermMemory]:
        """Extract memories from conversation messages.

        Args:
            session: Database session
            user_id: User ID
            conversation_id: Conversation ID
            messages: List of messages to analyze

        Returns:
            List of extracted short-term memories
        """
        if not messages:
            return []

        # Format conversation for extraction
        conversation_text = "\n".join([
            f"{m['role']}: {m['content']}" for m in messages
        ])

        # Use AI to extract information
        prompt = self._extraction_prompt.format(conversation=conversation_text)

        try:
            response = await self.ai_service.simple_chat(
                user_message=prompt,
                system_prompt="你是一个记忆提取助手，负责从对话中提取重要信息。",
                temperature=0.3,
            )

            # Parse JSON response
            extracted = self._parse_extraction_response(response)
            if not extracted:
                return []

            # Create short-term memories
            memories = []
            for info in extracted.get("extracted_info", []):
                memory = ShortTermMemory(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    content=info.get("content", ""),
                    memory_type=self._map_info_type(info.get("type", "")),
                    extracted_info=info,
                    emotion_state=extracted.get("emotional_state", {}),
                    relevance_score=1.0,
                    consolidation_score=info.get("importance", 0.5),
                    should_consolidate=info.get("importance", 0.5) >= self.consolidation_threshold,
                )
                session.add(memory)
                memories.append(memory)

            await session.commit()
            logger.info(f"Extracted {len(memories)} memories for user {user_id}")
            return memories

        except Exception as e:
            logger.error(f"Memory extraction error: {e}")
            return []

    def _parse_extraction_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse AI extraction response."""
        import re
        try:
            # Try to find JSON in response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                # Clean up common issues
                json_str = re.sub(r',\s*}', '}', json_str)  # Remove trailing commas
                json_str = re.sub(r',\s*]', ']', json_str)  # Remove trailing commas in arrays
                return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse extraction response: {e}")
            logger.debug(f"Response was: {response[:500]}")
        return None

    def _map_info_type(self, info_type: str) -> str:
        """Map extracted info type to MemoryType."""
        type_mapping = {
            "用户基本信息": MemoryType.FACT.value,
            "用户偏好": MemoryType.PREFERENCE.value,
            "用户厌恶": MemoryType.PREFERENCE.value,
            "重要事件": MemoryType.EVENT.value,
            "情感状态": MemoryType.EMOTION.value,
            "关系信息": MemoryType.RELATIONSHIP.value,
            "生活习惯": MemoryType.HABIT.value,
            "价值观": MemoryType.FACT.value,
        }
        return type_mapping.get(info_type, MemoryType.CONTEXT.value)

    async def add_short_term_memory(
        self,
        session: AsyncSession,
        user_id: int,
        conversation_id: int,
        content: str,
        memory_type: str = MemoryType.CONTEXT.value,
        extracted_info: Optional[Dict] = None,
        emotion_state: Optional[Dict] = None,
    ) -> ShortTermMemory:
        """Add a short-term memory.

        Args:
            session: Database session
            user_id: User ID
            conversation_id: Conversation ID
            content: Memory content
            memory_type: Type of memory
            extracted_info: Extracted information
            emotion_state: Emotional state

        Returns:
            Created ShortTermMemory
        """
        memory = ShortTermMemory(
            user_id=user_id,
            conversation_id=conversation_id,
            content=content,
            memory_type=memory_type,
            extracted_info=extracted_info or {},
            emotion_state=emotion_state or {},
            relevance_score=1.0,
        )
        session.add(memory)
        await session.commit()

        # Enforce limit
        await self._enforce_short_term_limit(session, user_id)

        return memory

    async def _enforce_short_term_limit(
        self,
        session: AsyncSession,
        user_id: int,
    ) -> None:
        """Enforce short-term memory limit by removing oldest memories."""
        result = await session.execute(
            select(ShortTermMemory)
            .where(ShortTermMemory.user_id == user_id)
            .order_by(desc(ShortTermMemory.created_at))
        )
        memories = result.scalars().all()

        if len(memories) > self.short_term_limit:
            # Remove oldest memories beyond limit
            for memory in memories[self.short_term_limit:]:
                await session.delete(memory)
            await session.commit()

    async def consolidate_memories(
        self,
        session: AsyncSession,
        user_id: int,
    ) -> List[LongTermMemory]:
        """Consolidate short-term memories to long-term storage.

        Args:
            session: Database session
            user_id: User ID

        Returns:
            List of created long-term memories
        """
        # Get memories marked for consolidation
        result = await session.execute(
            select(ShortTermMemory)
            .where(
                and_(
                    ShortTermMemory.user_id == user_id,
                    ShortTermMemory.should_consolidate == True,
                )
            )
        )
        short_term_memories = result.scalars().all()

        if not short_term_memories:
            return []

        long_term_memories = []

        for stm in short_term_memories:
            # Check if similar memory exists
            existing = await self._find_similar_memory(
                session, user_id, stm.content, stm.memory_type
            )

            if existing:
                # Reinforce existing memory
                existing.reinforcement_count += 1
                existing.last_reinforced_at = datetime.utcnow()
                existing.confidence = min(1.0, existing.confidence + 0.1)
                long_term_memories.append(existing)
            else:
                # Create new long-term memory
                ltm = LongTermMemory(
                    user_id=user_id,
                    memory_type=stm.memory_type,
                    category=stm.extracted_info.get("type", "general"),
                    key=self._generate_memory_key(stm),
                    value=stm.content,
                    context=json.dumps(stm.extracted_info, ensure_ascii=False),
                    keywords=self._extract_keywords(stm.content),
                    importance=stm.consolidation_score,
                    confidence=stm.extracted_info.get("confidence", 0.5),
                    source_short_term_ids=[stm.id],
                )
                session.add(ltm)
                long_term_memories.append(ltm)

            # Mark short-term memory as processed
            stm.should_consolidate = False

        await session.commit()
        logger.info(f"Consolidated {len(long_term_memories)} memories for user {user_id}")
        return long_term_memories

    async def _find_similar_memory(
        self,
        session: AsyncSession,
        user_id: int,
        content: str,
        memory_type: str,
    ) -> Optional[LongTermMemory]:
        """Find similar existing long-term memory."""
        # Simple keyword-based matching
        keywords = self._extract_keywords(content)

        result = await session.execute(
            select(LongTermMemory)
            .where(
                and_(
                    LongTermMemory.user_id == user_id,
                    LongTermMemory.memory_type == memory_type,
                    LongTermMemory.status == MemoryStatus.ACTIVE.value,
                )
            )
        )
        memories = result.scalars().all()

        for memory in memories:
            memory_keywords = set(memory.keywords or [])
            if memory_keywords & set(keywords):
                return memory

        return None

    def _generate_memory_key(self, memory: ShortTermMemory) -> str:
        """Generate a key for the memory."""
        info = memory.extracted_info
        if info.get("type") and info.get("content"):
            return f"{info['type']}_{hash(info['content']) % 10000}"
        return f"{memory.memory_type}_{memory.id}"

    def _extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from content using jieba."""
        try:
            import jieba.analyse
            keywords = jieba.analyse.extract_tags(content, topK=5)
            return keywords
        except ImportError:
            # Fallback: simple word extraction
            return content.split()[:5]

    async def get_user_memories(
        self,
        session: AsyncSession,
        user_id: int,
        memory_types: Optional[List[str]] = None,
        limit: int = 50,
    ) -> List[LongTermMemory]:
        """Get user's long-term memories.

        Args:
            session: Database session
            user_id: User ID
            memory_types: Optional filter by memory types
            limit: Maximum memories to return

        Returns:
            List of long-term memories
        """
        query = select(LongTermMemory).where(
            and_(
                LongTermMemory.user_id == user_id,
                LongTermMemory.status == MemoryStatus.ACTIVE.value,
            )
        )

        if memory_types:
            query = query.where(LongTermMemory.memory_type.in_(memory_types))

        query = query.order_by(desc(LongTermMemory.importance)).limit(limit)

        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_recent_context(
        self,
        session: AsyncSession,
        user_id: int,
        limit: int = 10,
    ) -> List[ShortTermMemory]:
        """Get recent short-term memories for context.

        Args:
            session: Database session
            user_id: User ID
            limit: Maximum memories to return

        Returns:
            List of short-term memories
        """
        result = await session.execute(
            select(ShortTermMemory)
            .where(ShortTermMemory.user_id == user_id)
            .order_by(desc(ShortTermMemory.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_memories(
        self,
        session: AsyncSession,
        user_id: int,
        query: str,
        limit: int = 10,
    ) -> List[LongTermMemory]:
        """Search memories by keyword.

        Args:
            session: Database session
            user_id: User ID
            query: Search query
            limit: Maximum results

        Returns:
            List of matching memories
        """
        keywords = self._extract_keywords(query)

        result = await session.execute(
            select(LongTermMemory)
            .where(
                and_(
                    LongTermMemory.user_id == user_id,
                    LongTermMemory.status == MemoryStatus.ACTIVE.value,
                )
            )
        )
        all_memories = result.scalars().all()

        # Score and rank memories
        scored_memories = []
        for memory in all_memories:
            score = 0
            memory_keywords = set(memory.keywords or [])
            memory_content = memory.value.lower()

            for kw in keywords:
                if kw in memory_keywords:
                    score += 2
                if kw.lower() in memory_content:
                    score += 1

            if score > 0:
                scored_memories.append((memory, score))

        # Sort by score and return top results
        scored_memories.sort(key=lambda x: x[1], reverse=True)
        return [m for m, _ in scored_memories[:limit]]

    async def build_user_profile(
        self,
        session: AsyncSession,
        user_id: int,
    ) -> UserMemoryProfile:
        """Build comprehensive user memory profile.

        Args:
            session: Database session
            user_id: User ID

        Returns:
            UserMemoryProfile with all memory categories
        """
        # Get all long-term memories
        memories = await self.get_user_memories(session, user_id, limit=100)

        # Categorize memories
        facts = []
        preferences = []
        events = []
        relationships = []

        for memory in memories:
            schema = LongTermMemorySchema.model_validate(memory)
            if memory.memory_type == MemoryType.FACT.value:
                facts.append(schema)
            elif memory.memory_type == MemoryType.PREFERENCE.value:
                preferences.append(schema)
            elif memory.memory_type == MemoryType.EVENT.value:
                events.append(schema)
            elif memory.memory_type == MemoryType.RELATIONSHIP.value:
                relationships.append(schema)

        # Get recent context
        recent = await self.get_recent_context(session, user_id, limit=5)
        recent_context = [ShortTermMemorySchema.model_validate(m) for m in recent]

        return UserMemoryProfile(
            user_id=user_id,
            facts=facts,
            preferences=preferences,
            events=events,
            relationships=relationships,
            recent_context=recent_context,
        )

    async def update_memory_access(
        self,
        session: AsyncSession,
        memory_id: int,
    ) -> None:
        """Update memory access tracking.

        Args:
            session: Database session
            memory_id: Memory ID
        """
        result = await session.execute(
            select(LongTermMemory).where(LongTermMemory.id == memory_id)
        )
        memory = result.scalar_one_or_none()

        if memory:
            memory.access_count += 1
            memory.last_accessed_at = datetime.utcnow()
            await session.commit()
