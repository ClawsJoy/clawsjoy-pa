#!/usr/bin/env python3
"""DriftDetector v1.0 — 长循环任务漂移检测：基于关键词覆盖 + Jaccard 相似度的语义相关性评分"""

import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class DriftDetector:
    """漂移检测器（单例）—— 计算原始目标与当前输出的语义相关性分数。

    分数越高表示越贴近原始目标（漂移越小）：
        score = 0.6 * keyword_coverage + 0.4 * jaccard_similarity
    """

    _instance: Optional["DriftDetector"] = None

    def __new__(cls) -> "DriftDetector":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ----------------------------------------------------------
    # 公开接口
    # ----------------------------------------------------------
    def detect(self, goal: str, output: str) -> Dict:
        """检测原始目标与当前输出之间的漂移程度。

        Args:
            goal: 原始目标文本
            output: 当前输出文本

        Returns:
            dict: {
                "score": float,              # 语义相关性分数 0.0~1.0（越高越贴近目标）
                "level": str,                # low / medium / high（漂移程度）
                "keyword_coverage": float,   # 关键词覆盖率
                "jaccard_similarity": float, # Jaccard 相似度
                "goal_keywords": List[str],  # 目标关键词
            }
        """
        goal = (goal or "").strip()
        output = (output or "").strip()
        if not goal or not output:
            return {
                "score": 0.0,
                "level": "high",
                "keyword_coverage": 0.0,
                "jaccard_similarity": 0.0,
                "goal_keywords": [],
            }

        goal_kw = self._keywords(goal)
        output_kw = self._keywords(output)
        if not goal_kw or not output_kw:
            return {
                "score": 0.0,
                "level": "high",
                "keyword_coverage": 0.0,
                "jaccard_similarity": 0.0,
                "goal_keywords": goal_kw,
            }

        coverage = self._keyword_coverage(goal_kw, output_kw)
        jaccard = self._jaccard(goal_kw, output_kw)
        score = 0.6 * coverage + 0.4 * jaccard

        if score >= 0.6:
            level = "low"
        elif score >= 0.35:
            level = "medium"
        else:
            level = "high"

        return {
            "score": round(score, 4),
            "level": level,
            "keyword_coverage": round(coverage, 4),
            "jaccard_similarity": round(jaccard, 4),
            "goal_keywords": goal_kw,
        }

    def auto_correct(self, goal: str, output: str, correction_hint: Optional[str] = None) -> Dict:
        """漂移检测 → 自动纠正：基于 detect() 结果生成注入 LLM 的纠正提示。

        Args:
            goal: 原始目标文本
            output: 当前输出文本
            correction_hint: 可选的附加纠正提示

        Returns:
            dict: {
                "detected": bool,           # 是否检测到漂移（level 为 medium/high 时为 True）
                "level": str,               # low / medium / high（漂移程度）
                "score": float,             # 语义相关性分数
                "correction_prompt": str,   # 注入到上下文的纠正提示
            }
        """
        result = self.detect(goal, output)
        level = result["level"]
        score = result["score"]

        if level in ("medium", "high"):
            out_set = set(self._keywords(output))
            missing = [kw for kw in result["goal_keywords"] if kw not in out_set]
            prompt = (
                f"[DRIFT_CORRECT] 检测到任务漂移（level={level}, score={score:.2f}）。"
                f"请重新聚焦原始目标：「{goal}」。"
                f"当前输出偏离目标关键词：{missing[:10] or '（无法提取具体关键词）'}。"
            )
            if correction_hint:
                prompt += f" 纠正提示：{correction_hint}"
            detected = True
        else:
            prompt = (
                f"[DRIFT_OK] 当前输出与原始目标一致（score={score:.2f}, level={level}），无需纠正。"
            )
            detected = False

        return {
            "detected": detected,
            "level": level,
            "score": score,
            "correction_prompt": prompt,
        }

    # ----------------------------------------------------------
    # 内部实现
    # ----------------------------------------------------------
    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """切分文本：英文按单词，中文按 bigram（2-gram）近似分词。"""
        tokens: List[str] = []
        for m in re.finditer(r"[a-zA-Z0-9_]+", text):
            tokens.append(m.group(0).lower())
        for m in re.finditer(r"[\u4e00-\u9fff]+", text):
            seg = m.group(0)
            if len(seg) == 1:
                tokens.append(seg)
            else:
                tokens.extend(seg[i : i + 2] for i in range(len(seg) - 1))
        return tokens

    @classmethod
    def _keywords(cls, text: str) -> List[str]:
        """提取关键词：过滤停用词与纯数字后的 token 列表。"""
        stopwords = {
            "the", "a", "an", "of", "to", "in", "for", "on", "and", "or",
            "is", "are", "with", "as", "by", "at", "from", "this", "that",
            "it", "be", "was", "were", "we", "you", "your", "our",
            "已", "的", "了", "和", "与", "在", "是", "把", "被", "将", "为", "对", "从", "中", "并",
        }
        tokens = cls._tokenize(text)
        return [t for t in tokens if t not in stopwords and not t.isdigit()]

    @staticmethod
    def _keyword_coverage(goal_kw: List[str], output_kw: List[str]) -> float:
        """关键词覆盖率：目标关键词中有多少出现在输出中。"""
        if not goal_kw:
            return 0.0
        out_set = set(output_kw)
        hit = sum(1 for kw in goal_kw if kw in out_set)
        return hit / len(goal_kw)

    @staticmethod
    def _jaccard(a: List[str], b: List[str]) -> float:
        """Jaccard 相似度：|A ∩ B| / |A ∪ B|。"""
        set_a, set_b = set(a), set(b)
        union = set_a | set_b
        if not union:
            return 0.0
        return len(set_a & set_b) / len(union)
