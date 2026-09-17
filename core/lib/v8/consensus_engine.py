#!/usr/bin/env python3
"""ConsensusEngine v8.0 — 共识引擎：比较多个 Agent 输出，计算一致度，决定下一步"""


def _extract_keywords(text: str) -> set:
    """提取文本关键词。

    策略：
    - 若按空白符分割后得到多个词 → 英文场景，取长度 >= 2 的词
    - 若整段无空格 → 中文场景，取字符 2-gram（bigram）
    - 空或单字符 → 返回空集
    """
    words = text.split()
    if len(words) > 1:
        return {w for w in words if len(w) >= 2}
    # 中文场景：字符 bigram
    chars = text.strip()
    if len(chars) <= 1:
        return set()
    return {chars[i:i + 2] for i in range(len(chars) - 1)}


class ConsensusEngine:
    """共识引擎（单例）：比较多个 Agent 的输出，计算一致度，决定下一步。

    使用简单多数决 + 关键词重叠率判断文本相似度。
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    # ========== 公开接口 ==========

    def evaluate(self, results: dict) -> dict:
        """评估多个 Agent 的输出，计算共识。

        参数:
            results: {"模型名": "输出文本", ...}

        返回:
            {
                "consensus": bool,   # 是否达成共识
                "agreement": float,  # 一致度 0.0 ~ 1.0
                "decision": str      # 最终决策（最大共识组的代表输出）
            }
        """
        if not results:
            return {"consensus": False, "agreement": 0.0, "decision": None}

        outputs = list(results.values())

        # —— 只有 1 个模型：唯一输出就是决策 ——
        if len(outputs) == 1:
            return {"consensus": True, "agreement": 1.0, "decision": outputs[0]}

        # —— 分组：按关键词重叠率将相似输出归为同一组 ——
        groups = _cluster_by_similarity(outputs)

        # —— 找最大组 ——
        max_group = max(groups, key=len)
        agreement = round(len(max_group) / len(outputs), 2)
        consensus = agreement > 0.5

        return {
            "consensus": consensus,
            "agreement": agreement,
            "decision": max_group[0],
        }


# ========== 文本相似度（模块级工具函数） ==========


def _is_similar(text1: str, text2: str) -> bool:
    """判断两个文本是否一致：关键词重叠率 > 50% 视为一致。

    重叠率 = 交集大小 / min(两者关键词数)。
    若一方无关键词，回退到全等比较。
    """
    kw1 = _extract_keywords(text1)
    kw2 = _extract_keywords(text2)

    # 一方无有效关键词 → 全等比较
    if not kw1 or not kw2:
        return text1 == text2

    overlap = len(kw1 & kw2) / min(len(kw1), len(kw2))
    return overlap > 0.5


def _cluster_by_similarity(outputs: list) -> list:
    """将输出列表按文本相似度聚类，返回组列表。"""
    n = len(outputs)
    assigned = [False] * n
    groups: list[list[str]] = []

    for i in range(n):
        if assigned[i]:
            continue
        group = [outputs[i]]
        assigned[i] = True
        for j in range(i + 1, n):
            if assigned[j]:
                continue
            if _is_similar(outputs[i], outputs[j]):
                group.append(outputs[j])
                assigned[j] = True
        groups.append(group)

    return groups
