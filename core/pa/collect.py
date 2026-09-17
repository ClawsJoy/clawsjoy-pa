# -*- coding: utf-8 -*-
"""聊天层参数化收集(2026-09-13 聊天层落地第 1 步的聊天侧)。

定位: 表单是"显式建档"(老板主动填), 聊天是"隐式收集"(老板说话时顺手记)。
两者走**同一条**落库路径 core.pa.profile.collect_fields —— 一份数据, 两个入口。

为什么不用 LLM 抽取: 离线可测、零成本、无幻觉。规则**由字段表驱动**(DETECT_RULES 的 key
必须在 FIELD_SCHEMA 里), 字段表加一项 = 收集能力加一项, 不需要改逻辑。

契约:
  detect_fields(text) -> {key: 取值}   只返回有把握的命中; 拿不准就不返回(宁缺勿错)
  recap_line(hits)    -> str           一句话复述, PA 把它拼在回复末尾让老板当场纠正

注: 命中即写库(confirmed), 靠"复述 + supersedes 链"兜底纠正 —— 老板一句"不对",
旧条目标 revised, 新条目 supersedes 指向旧 id。这条链就是训练标注。
"""
from core.pa.profile import FIELD_SCHEMA

# 触发词表: {字段: {取值: [触发词...]}}  —— 顺序敏感: 先匹配的胜出,
# 所以"否"类(否定)规则必须排在"是"类前面, 否则"不要自动写"会被"自动写"命中。
DETECT_RULES = {
    "industry": {
        "光电": ["光电"],
        "制造": ["制造业", "制造", "工厂", "产线", "车间"],
        "贸易": ["贸易", "外贸", "进出口"],
        "服务": ["服务业", "咨询公司"],
    },
    "interests": {
        "技术": ["技术", "研发", "工艺"],
        "市场": ["市场", "营销", "获客"],
        "管理": ["管理", "团队", "组织"],
        "金融": ["金融", "投资", "融资"],
        "法务": ["法务", "合规", "合同", "专利"],
        "财税": ["财税", "税务", "会计", "开票"],
        "战略": ["战略", "规划", "布局"],
        "日常事务": ["日常事务", "琐事"],
    },
    "report_detail": {
        "详": ["汇报详细", "详细一点", "详尽", "说透", "多写点", "展开说"],
        "简": ["汇报简短", "简短", "简要", "别啰嗦", "一句话说"],
    },
    "tone": {"委婉": ["委婉", "客气点", "缓和"], "直接": ["直接说", "直接点", "直说", "别绕"]},
    "iteration": {
        "想清楚再动手": ["想清楚再动手", "先想清楚", "别急着动手"],
        "先给草稿再改": ["先给草稿", "先出草稿", "草稿再改"],
    },
    "risk_auto_write": {
        "否": ["不要自动写", "写入要确认", "写文件要我", "不要自动改文件"],
        "是": ["自动写文件", "免审批写", "文件自动写", "自动写"],
    },
    "risk_auto_exec": {
        "否": ["不要自动执行", "命令要确认", "执行命令要问"],
        "是": ["自动执行", "命令自动跑", "直接执行命令"],
    },
    "risk_auto_send": {
        "否": ["外发要确认", "发送要问我", "不要自动发"],
        "是": ["自动外发", "直接发出去", "自动发送"],
    },
}


def _rules_for(key):
    """只认字段表里有的字段/取值 —— 字段表是唯一真源; 顺序取 DETECT_RULES 的书写顺序。

    顺序即优先级: 否定规则("否")必须写在肯定规则("是")前面, 否则
    "不要自动写文件" 会被 "自动写" 命中 -> 误判为"是"。
    """
    spec = FIELD_SCHEMA.get(key)
    if not spec:
        return {}
    opts = set(spec["options"])
    raw = DETECT_RULES.get(key) or {}
    return {opt: [w for w in (words or []) if w] for opt, words in raw.items() if opt in opts}


def detect_fields(text):
    """从一句人话里识别字段取值。契约: 返回 {key: str|list}; 未命中字段不出现。"""
    t = str(text or "")
    if not t.strip():
        return {}
    hits = {}
    for key, spec in FIELD_SCHEMA.items():
        rules = _rules_for(key)
        found = []
        for opt, words in rules.items():  # DETECT_RULES 顺序 = 优先级
            if any(word in t for word in words):
                found.append(opt)
        if not found:
            continue
        if spec["type"] == "multi":
            hits[key] = found
        else:
            hits[key] = found[0]
    return hits


def recap_line(hits, limit=4):
    """一句话复述(PA 回复末尾用)。契约: 返回 str; hits 为空返回空串。"""
    if not hits:
        return ""
    parts = []
    for k, v in list(hits.items())[:limit]:
        spec = FIELD_SCHEMA.get(k) or {}
        label = spec.get("label", k)
        val = "、".join(v) if isinstance(v, list) else v
        parts.append("%s = %s" % (label, val))
    return "（记下了：%s。不对就说一句，我改。）" % "；".join(parts)
