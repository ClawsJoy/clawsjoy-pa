"""工具配额管理器 — 表格化配额表（#236）

每任务开始时初始化 20 个工具各 10 次，调用时递减。
用完返回降级指令：剩余可用工具列表 + 建议替代方案。
"""

import logging

logger = logging.getLogger(__name__)

# {session_id: {tool_name: {"initial": 10, "used": 0, "remaining": 10}}}
_quota_table = {}

# ===== 工具预设模式（P1-1）=====
# {session_id: mode} — 同 session 内模式保持一致，新任务时随 reset_quota 清空
_mode_cache = {}

# 写入任务关键词 → minimal 模式（只用核心读写执行工具）
_WRITE_KEYWORDS = ["修改", "创建", "修复", "新增", "重写", "实现", "完善",
                   "添加", "写入", "编辑", "生成", "删除", "调整", "设计"]
# 分析类任务关键词 → full 模式（开放全部 6 个工具）
_ANALYSIS_KEYWORDS = ["分析", "盘点", "排查", "审查", "检查", "审计", "调查",
                      "理解", "总结", "报告", "评估", "监控", "梳理"]

_modes_config_cache = None  # audit_rules.yaml modes 配置缓存

# 工具降级建议：工具用完时的替代方案
_TOOL_ALTERNATIVES = {
    "query_index": ["read_file (search=)", "search_files", "list_dir"],
    "read_file": ["query_index", "world_model 骨架"],
    "list_dir": ["项目树已注入", "query_index"],
    "search_files": ["项目树已注入", "list_dir"],
    "execute_command": ["write_file", "read_file"],
    "write_file": ["execute_command"],
}


def init_quota(session_id: str, tools: list = None, initial: int = 10):
    """任务开始时初始化配额表"""
    if tools is None:
        tools = ["read_file", "write_file", "list_dir", "search_files",
                 "execute_command", "query_index"]
    _quota_table[session_id] = {
        t: {"initial": initial, "used": 0, "remaining": initial}
        for t in tools
    }


def check_tool_quota(tool_name: str, session_id: str) -> tuple:
    """检查工具配额。返回 (allowed, remaining, suggestion)"""
    table = _quota_table.get(session_id)
    if not table:
        init_quota(session_id)

    if tool_name not in table:
        return (True, -1, "")

    entry = table[tool_name]
    if entry["remaining"] <= 0:
        alt = "、".join(_TOOL_ALTERNATIVES.get(tool_name, ["其他工具"]))
        suggestion = f"{tool_name} 已用完（0/{entry['initial']}）。建议改用：{alt}"
        return (False, 0, suggestion)

    return (True, entry["remaining"], "")


def consume_tool(tool_name: str, session_id: str):
    """工具调用成功时递减配额"""
    table = _quota_table.get(session_id)
    if table and tool_name in table:
        entry = table[tool_name]
        if entry["remaining"] > 0:
            entry["remaining"] -= 1
            entry["used"] += 1


def reset_quota(session_id: str):
    """新任务开始时重置"""
    if session_id in _quota_table:
        del _quota_table[session_id]
    if session_id in _mode_cache:
        del _mode_cache[session_id]


def get_quota_table(session_id: str) -> dict:
    """返回完整配额表（用于注入 System Prompt）"""
    return _quota_table.get(session_id, {})


def _load_modes_config() -> dict:
    """从 config/v8/audit_rules.yaml 加载 modes 配置（模块级缓存）。"""
    global _modes_config_cache
    if _modes_config_cache is not None:
        return _modes_config_cache
    _modes_config_cache = {"minimal": ["read_file", "write_file", "execute_command"],
                           "full": ["read_file", "write_file", "execute_command",
                                    "list_dir", "search_files", "query_index"]}
    try:
        import yaml as _y
        from pathlib import Path as _P
        _rules_path = _P("config/v8/audit_rules.yaml")
        if _rules_path.exists():
            _rules = _y.safe_load(_rules_path.read_text()) or {}
            _modes_cfg = _rules.get("modes") or {}
            if isinstance(_modes_cfg, dict) and _modes_cfg:
                _modes_config_cache = _modes_cfg
    except Exception as _e:
        print(f"[MODE_CONFIG] modes 配置加载失败，使用默认: {_e}")
    return _modes_config_cache


def get_mode(session_id: str, task_hint: str = "") -> str:
    """根据任务类型返回工具预设模式：minimal | full（P1-1）。

    任务类型判定（优先使用 task_hint，缺省回退 session 缓存/默认）：
      - 含"修改/创建/修复"等写入关键词 → minimal（只用核心读写执行工具）
      - 含"分析/盘点/排查"等分析关键词 → full（开放全部工具）
      - 无匹配 → 默认 minimal（避免简单任务过度探索）
    """
    if task_hint:
        if any(_kw in task_hint for _kw in _WRITE_KEYWORDS):
            return "minimal"
        if any(_kw in task_hint for _kw in _ANALYSIS_KEYWORDS):
            return "full"
    _cached = _mode_cache.get(session_id)
    if _cached:
        return _cached
    _mode_cache[session_id] = "minimal"
    return "minimal"


def get_mode_tools(session_id: str, task_hint: str = "") -> list:
    """返回当前模式允许的工具列表（来自 audit_rules.yaml modes 配置）。"""
    _mode = get_mode(session_id, task_hint)
    return _load_modes_config().get(_mode, [])


def _check_discuss_token_budget(user_id: str, server_id: str = "default", model: str = "") -> tuple:
    """检查讨论分支 token 预算。返回 (是否超限, 今日累计用量, 预算上限)"""
    import yaml as _y
    from pathlib import Path as _P
    from datetime import datetime as _dt
    try:
        _rules_path = _P("config/v8/audit_rules.yaml")
        if _rules_path.exists():
            _rules = _y.safe_load(_rules_path.read_text()) or {}
            _budget = _rules.get("token_budget", {}).get("per_day", 0)
        else:
            _budget = 0
        # 第1处：如果当前 model 是 Ollama，直接 return
        if model and "ollama" in model.lower():
            return (False, 0, _budget)
        _billing_file = _P(f"data/v8/billing_{server_id}.jsonl")
        if not _billing_file.exists():
            return (False, 0, _budget)
        _today = _dt.now().strftime("%Y-%m-%d")
        _total = 0
        with open(_billing_file) as _bf:
            for _line in _bf:
                try:
                    _entry = json.loads(_line)
                    # 第2处：跳过 Ollama，只统计 discuss 相关条目
                    _entry_model = (_entry.get("model", "") or "").lower()
                    if "ollama" in _entry_model:
                        continue
                    _summary = (_entry.get("summary", "") or "").lower()
                    _task_type = (_entry.get("task_type", "") or "").lower()
                    if "discuss" not in _summary and "discuss" not in _task_type:
                        continue
                    if _entry.get("timestamp", "").startswith(_today):
                        _total += _entry.get("tokens", 0)
                except Exception:
                    pass
        if _budget <= 0:
            return (False, _total, _budget)
        return (_total >= _budget, _total, _budget)
    except Exception as _e:
        print(f"[BUDGET_CHECK] 预算检查失败: {_e}")
        return (False, 0, 0)



