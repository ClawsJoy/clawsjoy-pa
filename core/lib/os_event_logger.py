"""OS事件日志记录器 - 记录操作系统级事件"""
import os as _os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# 日志文件路径
_EVENTS_DIR = Path(_os.environ.get("PROJECT_ROOT", ".")) / "data" / "v8"
_EVENTS_FILE = _EVENTS_DIR / "events_default.jsonl"



def _ensure_dir():
    """确保日志目录存在"""
    _EVENTS_DIR.mkdir(parents=True, exist_ok=True)


def write_os_event(
    event_type: str,           # 必填：degrade | intercept | auto_fix | pass | probe | llm_call
    operation: str = "",       # read | write | execute | query | publish
    os_action: str = "",       # blocked | degraded | corrected | allowed | redirected
    reason: str = "",          # llm_unavailable | billing_lost | state_persist_failed | checkpoint_lost | metacognition_failed | process_auto_started | stream_parse_failed
    command: str = "",         # 触发函数名或操作
    detail: Optional[Dict[str, Any]] = None,  # dict，补充上下文。LLM日志的provider/model/tokens/elapsed放这里
    session_id: str = "",
    user_id: str = "",
    server_id: str = "",
    task_id: str = "",
    channel_id: str = "",
    agent_name: str = "",
    agent_reaction=None,
    cost=None,
) -> None:
    """记录一个OS级事件到日志文件

    Args:
        event_type: 事件类型 (degrade/intercept/auto_fix/pass/probe/llm_call)
        operation: 操作类型 (read/write/execute/query/publish)
        os_action: OS动作 (blocked/degraded/corrected/allowed/redirected)
        reason: 原因
        command: 触发函数名或操作
        detail: 补充上下文
        session_id: 会话ID
        user_id: 用户ID
        server_id: 服务器ID
        task_id: 任务ID
        channel_id: 频道ID
        agent_name: Agent名称
        agent_reaction: Agent反应
        cost: 成本
    """

    try:
        _ensure_dir()

        event = {
            "timestamp": datetime.now().isoformat(),
            "domain": "code",
            "event_type": event_type,
            "operation": operation,
            "os_action": os_action,
            "reason": reason,
            "command": command,
            "detail": detail,
            "session_id": session_id,
            "user_id": user_id,
            "server_id": server_id,
            "task_id": task_id,
            "channel_id": channel_id,
            "agent_name": agent_name,
            "agent_reaction": agent_reaction,
            "cost": cost,
        }

        # LLM日志兼容性：从detail中提取provider/model/tokens/elapsed
        if event_type == "llm_call" and isinstance(detail, dict):
            for key in ("provider", "model", "tokens", "elapsed"):
                if key in detail:
                    event[key] = detail[key]

        with open(_EVENTS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    except Exception as e:
        logger.warning(f"[OS_EVENT] 写入事件失败: {e}")


def read_recent_os_events(max_lines: int = 50, filter_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """读取 events_default.jsonl 最近 N 行

    Args:
        max_lines: 最大读取行数，默认50
        filter_types: 事件类型过滤列表，如 ["degrade", "intercept"]，None表示不过滤

    Returns:
        List[Dict]: 事件列表，文件不存在或读取失败时返回空列表
    """
    try:
        if not _EVENTS_FILE.exists():
            return []

        with open(_EVENTS_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 取最后 max_lines 行
        tail_lines = lines[-max_lines:] if len(lines) > max_lines else lines

        events: List[Dict[str, Any]] = []
        for line in tail_lines:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                if filter_types and event.get("event_type") not in filter_types:
                    continue
                events.append(event)
            except json.JSONDecodeError:
                continue

        events = [e for e in events if e and "event_type" in e]
        return events

    except Exception as e:
        logger.warning(f"[OS_EVENT] 读取事件失败: {e}")
        return []
