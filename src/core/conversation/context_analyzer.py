"""Context analyzer for improving conversation continuity."""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from loguru import logger


@dataclass
class ContextMessage:
    """Message with context metadata."""
    role: str
    content: str
    timestamp: datetime
    importance_score: float = 0.5
    topic_keywords: List[str] = None

    def __post_init__(self):
        if self.topic_keywords is None:
            self.topic_keywords = []


@dataclass
class ConversationTopic:
    """Detected conversation topic."""
    keywords: List[str]
    start_index: int
    end_index: int
    importance: float


class ContextAnalyzer:
    """Analyzer for conversation context and continuity."""

    def __init__(self):
        """Initialize context analyzer."""
        # Keywords that indicate context dependency
        self.context_dependent_keywords = [
            # 指代词
            "这个", "那个", "它", "他", "她", "这", "那",
            # 疑问词（需要上文）
            "什么", "为什么", "怎么", "哪", "谁",
            # 转折/延续词
            "但是", "不过", "所以", "然后", "接着",
            # 情绪反应词（通常是对上文的反应）
            "哈哈", "啊", "哦", "嗯", "呃", "唉",
            # 否定/肯定（对上文的回应）
            "不是", "是的", "对", "没有", "有",
            # 追问词
            "还", "又", "再", "继续",
        ]

        # Keywords indicating topic change
        self.topic_change_keywords = [
            "对了", "话说", "另外", "还有", "顺便问一下",
            "换个话题", "说起来", "想起来了",
        ]

        # High importance patterns
        self.high_importance_patterns = [
            # 情感表达
            r'喜欢|爱|讨厌|恨|想念',
            # 重要事件
            r'生日|纪念日|约会|见面',
            # 承诺/计划
            r'答应|保证|一定|会|要',
            # 问题/困扰
            r'问题|麻烦|困扰|担心|焦虑',
            # 个人信息
            r'我叫|我是|我的|住在|工作',
        ]

    def analyze_context_dependency(self, message: str) -> float:
        """Analyze how much a message depends on previous context.

        Args:
            message: Message to analyze

        Returns:
            Dependency score (0.0-1.0), higher means more dependent
        """
        score = 0.0
        msg_lower = message.lower()

        # Check for context-dependent keywords
        keyword_count = sum(1 for kw in self.context_dependent_keywords if kw in message)
        score += min(keyword_count * 0.15, 0.6)

        # Very short messages often depend on context
        if len(message) <= 5:
            score += 0.3

        # Questions usually need context
        if any(q in message for q in ['？', '?', '吗', '呢']):
            score += 0.2

        # Emotional reactions depend on context
        if any(e in message for e in ['哈哈', '哭', '笑', '气', '！！']):
            score += 0.15

        return min(score, 1.0)

    def calculate_message_importance(self, message: str, role: str) -> float:
        """Calculate importance score for a message.

        Args:
            message: Message content
            role: Message role (user/assistant)

        Returns:
            Importance score (0.0-1.0)
        """
        import re

        score = 0.5  # Base score

        # User messages are generally more important
        if role == "user":
            score += 0.1

        # Check high importance patterns
        for pattern in self.high_importance_patterns:
            if re.search(pattern, message):
                score += 0.15

        # Longer messages tend to be more important
        if len(message) > 50:
            score += 0.1
        elif len(message) > 100:
            score += 0.2

        # Questions are important
        if any(q in message for q in ['？', '?', '什么', '为什么', '怎么']):
            score += 0.15

        # Emotional intensity
        exclamation_count = message.count('！') + message.count('!')
        if exclamation_count >= 2:
            score += 0.1

        return min(score, 1.0)

    def detect_topic_change(self, current_msg: str, previous_msg: str) -> bool:
        """Detect if there's a topic change between messages.

        Args:
            current_msg: Current message
            previous_msg: Previous message

        Returns:
            True if topic changed
        """
        # Explicit topic change keywords
        if any(kw in current_msg for kw in self.topic_change_keywords):
            return True

        # Extract keywords from both messages
        current_keywords = self._extract_keywords(current_msg)
        previous_keywords = self._extract_keywords(previous_msg)

        # Calculate keyword overlap
        if not current_keywords or not previous_keywords:
            return False

        overlap = len(set(current_keywords) & set(previous_keywords))
        overlap_ratio = overlap / max(len(current_keywords), len(previous_keywords))

        # Low overlap suggests topic change
        return overlap_ratio < 0.2

    def _extract_keywords(self, text: str, top_k: int = 5) -> List[str]:
        """Extract keywords from text.

        Args:
            text: Text to analyze
            top_k: Number of keywords to extract

        Returns:
            List of keywords
        """
        try:
            import jieba.analyse
            keywords = jieba.analyse.extract_tags(text, topK=top_k)
            return keywords
        except ImportError:
            # Fallback: simple word extraction
            import re
            words = re.findall(r'[\u4e00-\u9fff]+', text)
            return words[:top_k]

    def select_relevant_context(
        self,
        messages: List[Dict[str, str]],
        current_message: str,
        max_messages: int = 10,
        max_tokens: int = 2000,
    ) -> List[Dict[str, str]]:
        """Select most relevant messages for context.

        Args:
            messages: Historical messages
            current_message: Current user message
            max_messages: Maximum messages to include
            max_tokens: Approximate token limit

        Returns:
            Selected messages with highest relevance
        """
        if not messages:
            return []

        # Analyze current message
        current_dependency = self.analyze_context_dependency(current_message)
        current_keywords = set(self._extract_keywords(current_message))

        # Score each historical message
        scored_messages = []
        for i, msg in enumerate(messages):
            score = 0.0
            content = msg.get('content', '')
            role = msg.get('role', 'user')

            # Base importance
            importance = self.calculate_message_importance(content, role)
            score += importance * 0.4

            # Recency bonus (more recent = higher score)
            recency_score = (i + 1) / len(messages)
            score += recency_score * 0.3

            # Keyword relevance
            msg_keywords = set(self._extract_keywords(content))
            if current_keywords and msg_keywords:
                keyword_overlap = len(current_keywords & msg_keywords) / len(current_keywords)
                score += keyword_overlap * 0.3

            scored_messages.append((msg, score, i))

        # Sort by score
        scored_messages.sort(key=lambda x: x[1], reverse=True)

        # Select top messages while respecting limits
        selected = []
        total_tokens = 0

        # Always include the most recent messages (for continuity)
        recent_count = min(5, len(messages))
        recent_messages = messages[-recent_count:]
        selected.extend(recent_messages)
        total_tokens += sum(len(m.get('content', '')) for m in recent_messages)

        # Add high-scoring messages that aren't already included
        for msg, score, idx in scored_messages:
            if len(selected) >= max_messages:
                break
            if total_tokens >= max_tokens:
                break
            if msg not in selected:
                selected.append(msg)
                total_tokens += len(msg.get('content', ''))

        # Sort by original order
        selected_indices = [messages.index(m) for m in selected]
        selected_indices.sort()
        return [messages[i] for i in selected_indices]

    def build_context_summary(
        self,
        messages: List[Dict[str, str]],
        max_length: int = 500,
    ) -> str:
        """Build a summary of conversation context.

        Args:
            messages: Messages to summarize
            max_length: Maximum summary length

        Returns:
            Context summary string
        """
        if not messages:
            return "新对话开始"

        # Group messages by topic
        topics = []
        current_topic_msgs = []

        for i, msg in enumerate(messages):
            content = msg.get('content', '')

            if i > 0:
                prev_content = messages[i-1].get('content', '')
                if self.detect_topic_change(content, prev_content):
                    if current_topic_msgs:
                        topics.append(current_topic_msgs)
                    current_topic_msgs = [msg]
                else:
                    current_topic_msgs.append(msg)
            else:
                current_topic_msgs.append(msg)

        if current_topic_msgs:
            topics.append(current_topic_msgs)

        # Build summary
        summary_parts = []

        # Summarize each topic
        for topic_msgs in topics[-3:]:  # Last 3 topics
            topic_summary = []
            for msg in topic_msgs[-2:]:  # Last 2 messages per topic
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                # Truncate long messages
                if len(content) > 100:
                    content = content[:100] + "..."
                topic_summary.append(f"{role}: {content}")
            summary_parts.append("\n".join(topic_summary))

        summary = "\n---\n".join(summary_parts)

        # Truncate if too long
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."

        return summary

    def detect_reference_to_previous(self, current_msg: str, previous_msgs: List[str]) -> Optional[int]:
        """Detect if current message references a previous message.

        Args:
            current_msg: Current message
            previous_msgs: List of previous messages (most recent first)

        Returns:
            Index of referenced message, or None
        """
        # Check for explicit references
        reference_patterns = [
            "刚才", "刚刚", "之前", "上次", "你说的",
            "那个", "这个", "它", "那", "这",
        ]

        has_reference = any(pattern in current_msg for pattern in reference_patterns)
        if not has_reference:
            return None

        # Find most relevant previous message
        current_keywords = set(self._extract_keywords(current_msg))

        best_match_idx = None
        best_match_score = 0.0

        for i, prev_msg in enumerate(previous_msgs[:5]):  # Check last 5 messages
            prev_keywords = set(self._extract_keywords(prev_msg))
            if current_keywords and prev_keywords:
                overlap = len(current_keywords & prev_keywords)
                score = overlap / len(current_keywords)
                if score > best_match_score:
                    best_match_score = score
                    best_match_idx = i

        return best_match_idx if best_match_score > 0.3 else None
