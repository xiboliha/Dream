"""Dialogue knowledge base for persona-consistent responses."""

import json
import os
import random
import re
from typing import Dict, List, Optional, Tuple

from loguru import logger


class DialogueKnowledgeBase:
    """Knowledge base for retrieving persona-consistent dialogue examples."""

    def __init__(self, knowledge_dir: Optional[str] = None):
        """Initialize dialogue knowledge base.

        Args:
            knowledge_dir: Directory containing knowledge files
        """
        if knowledge_dir is None:
            knowledge_dir = os.path.join(
                os.path.dirname(__file__),
                "..", "..", "..", "config", "knowledge"
            )
        self.knowledge_dir = knowledge_dir
        self.examples: Dict = {}
        self.response_patterns: Dict = {}
        self.forbidden_patterns: List[str] = []
        self._load_knowledge()

    def _load_knowledge(self) -> None:
        """Load dialogue examples from JSON file."""
        examples_path = os.path.join(self.knowledge_dir, "dialogue_examples.json")

        try:
            with open(examples_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Index examples by category and keywords
            self.examples = {}
            for category_data in data.get("examples", []):
                category = category_data["category"]
                self.examples[category] = category_data["scenarios"]

            self.response_patterns = data.get("response_patterns", {})
            self.forbidden_patterns = data.get("forbidden_patterns", {}).get("examples", [])

            logger.info(f"Loaded {len(self.examples)} dialogue categories")

        except FileNotFoundError:
            logger.warning(f"Dialogue examples not found: {examples_path}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse dialogue examples: {e}")

    def find_similar_scenario(
        self,
        user_message: str,
        mood: str = "neutral"
    ) -> Optional[Dict]:
        """Find similar dialogue scenario based on user message.

        Args:
            user_message: User's input message
            mood: Current mood/energy state

        Returns:
            Matching scenario with example responses, or None
        """
        user_message_lower = user_message.lower().strip()

        # Direct match keywords
        keyword_mappings = {
            "打招呼": ["hello", "hi", "你好", "嗨", "在吗", "在不在"],
            "日常问候": ["在干嘛", "干嘛呢", "吃了吗", "吃饭了吗", "今天怎么样", "忙吗", "忙不忙"],
            "情绪低落": ["累", "好累", "心情不好", "不开心", "烦", "烦死了", "难过", "郁闷"],
            "开心分享": ["开心", "高兴", "好消息", "升职", "加薪", "好玩的", "给你看"],
            "撒娇互动": ["想你", "想我吗", "喜欢你", "爱你", "抱抱", "亲亲", "么么"],
            "被敷衍时": ["嗯", "哦", "好", "行", "知道了"],
            "兴趣话题": ["喜欢什么", "推荐", "可爱", "猫", "狗", "玩偶", "毛绒"],
            "拒绝催促": ["快点", "快一点", "怎么这么慢", "催", "赶紧"],
            "傲娇回应": ["你真好", "可爱", "谢谢", "厉害", "棒"],
            "主动关心": ["回来了", "我回来了", "要去忙", "先忙了", "走了"],
        }

        # Find matching category
        matched_category = None
        for category, keywords in keyword_mappings.items():
            for keyword in keywords:
                if keyword in user_message_lower:
                    matched_category = category
                    break
            if matched_category:
                break

        # Special case: very short messages might be "被敷衍时"
        if not matched_category and len(user_message.strip()) <= 2:
            if user_message.strip() in ["嗯", "哦", "好", "行", "ok", "嗯嗯"]:
                matched_category = "被敷衍时"

        if not matched_category:
            return None

        # Find best matching scenario in category
        scenarios = self.examples.get(matched_category, [])
        if not scenarios:
            return None

        # Try to find exact or close match
        best_match = None
        best_score = 0

        for scenario in scenarios:
            user_pattern = scenario["user"].lower()
            score = 0

            # Exact match
            if user_pattern == user_message_lower:
                score = 100
            # Contains match
            elif user_pattern in user_message_lower or user_message_lower in user_pattern:
                score = 50
            # Keyword overlap
            else:
                pattern_words = set(user_pattern)
                message_words = set(user_message_lower)
                overlap = len(pattern_words & message_words)
                if overlap > 0:
                    score = overlap * 10

            if score > best_score:
                best_score = score
                best_match = scenario

        return best_match

    def get_example_response(
        self,
        user_message: str,
        mood: str = "neutral"
    ) -> Optional[str]:
        """Get a random example response for the user message.

        Args:
            user_message: User's input message
            mood: Current mood state

        Returns:
            Example response string, or None if no match
        """
        scenario = self.find_similar_scenario(user_message, mood)
        if scenario and scenario.get("responses"):
            return random.choice(scenario["responses"])
        return None

    def get_response_guidance(
        self,
        user_message: str,
        mood: str = "neutral"
    ) -> Dict:
        """Get guidance for generating response.

        Args:
            user_message: User's input message
            mood: Current mood state

        Returns:
            Dict with example_responses, pattern_info, and forbidden_patterns
        """
        scenario = self.find_similar_scenario(user_message, mood)

        # Determine energy mode
        energy_mode = "low_energy"  # Default
        high_energy_triggers = ["可爱", "猫", "狗", "玩偶", "好吃", "奶茶", "甜"]
        for trigger in high_energy_triggers:
            if trigger in user_message:
                energy_mode = "high_energy"
                break

        pattern_info = self.response_patterns.get(energy_mode, {})

        return {
            "example_responses": scenario.get("responses", []) if scenario else [],
            "context": scenario.get("context", "") if scenario else "",
            "energy_mode": energy_mode,
            "pattern_characteristics": pattern_info.get("characteristics", []),
            "forbidden_patterns": self.forbidden_patterns,
        }

    def build_few_shot_prompt(
        self,
        user_message: str,
        num_examples: int = 3
    ) -> str:
        """Build few-shot examples for the prompt.

        Args:
            user_message: User's input message
            num_examples: Number of examples to include

        Returns:
            Formatted few-shot prompt string
        """
        guidance = self.get_response_guidance(user_message)

        lines = []
        lines.append("## 回复风格参考")
        lines.append("")

        # Add energy mode info
        if guidance["energy_mode"] == "high_energy":
            lines.append("【当前状态：遇到喜欢的东西，可以稍微兴奋一点】")
        else:
            lines.append("【当前状态：低功耗模式，回复简短自然】")
        lines.append("")

        # Add example responses if available
        if guidance["example_responses"]:
            lines.append("类似情况的回复示例：")
            for resp in guidance["example_responses"][:num_examples]:
                lines.append(f'- "{resp}"')
            lines.append("")

        # Add characteristics
        if guidance["pattern_characteristics"]:
            lines.append("回复特点：")
            for char in guidance["pattern_characteristics"]:
                lines.append(f"- {char}")
            lines.append("")

        # Add forbidden patterns
        if guidance["forbidden_patterns"]:
            lines.append("绝对不要说这种话：")
            for forbidden in guidance["forbidden_patterns"][:4]:
                lines.append(f'- "{forbidden}"')
            lines.append("")

        return "\n".join(lines)
