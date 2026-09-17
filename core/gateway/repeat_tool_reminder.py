"""连续重复工具调用提醒(借鉴 Harness repeat-tool-reminder)

- canonicalize(arguments): 深度排序后序列化(对齐 Harness canonicalize 参数排序)
- observe(agent_id, tool_name, arguments) -> str | None: per-agent 计数,
  命中阈值 [3,5,8] 分档提醒(第3次温柔 / 第5、8次详细)
- reset(agent_id): 用户介入/新任务时重置
- 观察不否决: 只返回提醒文本, 不阻止工具执行(执行由调用方决定)

收敛旧内联检测: _execute_agent_task 原有 _loop_detect(5次) + consecutive(3次)
两套零散逻辑, 统一到此模块。
"""
import json
import threading

# 阈值分档(可配置): 第3次温柔提醒, 第5/8次详细提醒
THRESHOLDS = [3, 5, 8]

# 配置: include/exclude 工具名(默认 None = 全跟踪)
_INCLUDE = None  # 如 {"read_file", "write_file"} 只跟踪这些
_EXCLUDE = set()  # 如 {"list_dir"} 排除

# per-agent 计数: (agent_id, tool_name, canonical_args) -> count
_counts = {}
_lock = threading.Lock()


def configure(thresholds=None, include=None, exclude=None):
    """运行时配置阈值与跟踪范围(include/exclude 通配, 支持 * 前缀匹配)"""
    global THRESHOLDS, _INCLUDE, _EXCLUDE
    if thresholds is not None:
        THRESHOLDS = sorted(int(t) for t in thresholds)
    if include is not None:
        _INCLUDE = set(include)
    if exclude is not None:
        _EXCLUDE = set(exclude)


def canonicalize(arguments):
    """规范化参数: 深度排序后序列化(对齐 Harness canonicalize——同参数不同键序视为相同)"""
    if arguments is None:
        return ""
    try:
        return json.dumps(arguments, sort_keys=True, ensure_ascii=False, default=str)
    except Exception:
        return str(arguments)


def _wildcard_match(name, patterns):
    """通配符匹配(支持 * 后缀/前缀): read_* / *_file / 精确名"""
    for p in patterns or ():
        if p == "*" or p == name:
            return True
        if p.endswith("*") and name.startswith(p[:-1]):
            return True
        if p.startswith("*") and name.endswith(p[1:]):
            return True
    return False


def _tracked(tool_name):
    """是否跟踪该工具(include/exclude 通配)"""
    if _wildcard_match(tool_name, _EXCLUDE):
        return False
    if _INCLUDE is None:
        return True
    return _wildcard_match(tool_name, _INCLUDE)


def observe(agent_id, tool_name, arguments, thresholds=None):
    """观察一次工具调用; 命中阈值返回提醒文本(str), 否则 None。观察不否决。"""
    if not _tracked(tool_name):
        return None
    _thr = sorted(thresholds or THRESHOLDS)
    _key = (str(agent_id), tool_name, canonicalize(arguments))
    with _lock:
        n = _counts.get(_key, 0) + 1
        _counts[_key] = n
    if n not in _thr:
        return None
    _arg_preview = canonicalize(arguments)[:80]
    if n == _thr[0]:  # 温柔提醒
        return f"[重复提醒] 你已连续 {n} 次调用同一工具 {tool_name}({_arg_preview})。" "请切换策略或换个参数重试，避免无效循环。"
    # 详细提醒(第5/8次)
    return (
        f"[重复提醒] 连续 {n} 次调用 {tool_name}({_arg_preview})——"
        "可能是死循环。请重新审视任务目标：如果目标文件已满足，直接宣告完成；"
        "否则改用 read_file 定位后一次性 write_file 写入，不要再重复相同调用。"
    )


def reset(agent_id):
    """用户介入/新任务开始时重置该 agent 的计数"""
    _prefix = str(agent_id)
    with _lock:
        for k in [k for k in list(_counts) if k[0] == _prefix]:
            del _counts[k]


def stats():
    """当前计数快照(调试用)"""
    with _lock:
        return {str(k): v for k, v in _counts.items()}


def detect_retry_loop(*, messages, session_id):
    """重试循环检测（S3，从 _v9_bridge_loop 归位，2026-09-12）。

    检测两种卡死信号，走 steer 通道注入纠偏（失败则 fallback messages.append）：
    1) 连续 2 次 write_file path 为空 → 立即提示正确格式。
    2) 最近 5 次调用同一工具占比 >=3 → 提示换策略。

    契约：原地修改（messages 可能被 append），返回 None。观察不否决（不阻止工具执行）。
    """
    _recent_tools = []
    for _rm in messages[-6:]:
        if _rm["role"] == "assistant":
            for _tc in _rm.get("tool_calls", []):
                _recent_tools.append(_tc.get("function", {}).get("name", ""))
    # 空 path 快速干预：连续 2 次 write_file path 为空 → 立即提示
    _empty_path_count = 0
    for _rm in messages[-6:]:
        if _rm["role"] == "tool":
            _tc = str(_rm.get("content", ""))
            if "write_file path 不能为空" in _tc or "write_file path 为空" in _tc:
                _empty_path_count += 1
    if _empty_path_count >= 2:
        # P4 steer 全量迁移: 纠偏指令走 steer 通道
        try:
            from core.gateway.shared_state import add_steer

            add_steer(
                session_id,
                "[系统] write_file 缺少 path 参数。正确格式：write_file(path='clawsjoy_dev/...', content='...')。请检查 tool_calls 中的 arguments 是否包含 path 字段。",
            )
        except Exception:
            messages.append(
                {
                    "role": "system",
                    "content": "[系统] write_file 缺少 path 参数。正确格式：write_file(path='clawsjoy_dev/...', content='...')。请检查 tool_calls 中的 arguments 是否包含 path 字段。",
                }
            )

    if len(_recent_tools) >= 5:
        from collections import Counter as _Counter

        _tc_count = _Counter(_recent_tools[-5:])
        _most = _tc_count.most_common(1)[0]
        if _most[1] >= 3:
            _stuck_tool = _most[0]
            _alt = {"write_file": "python3 heredoc", "python3": "write_file", "read_file": "query_index"}
            _hint = _alt.get(_stuck_tool, "更换工具或策略")
            # P4 steer 全量迁移: 纠偏指令走 steer 通道
            try:
                from core.gateway.shared_state import add_steer

                add_steer(session_id, f"[系统] 检测到最近 5 次调用中 {_stuck_tool} 占比 {_most[1]}/5，可能陷入重试循环。建议尝试 {_hint}。")
            except Exception:
                messages.append(
                    {
                        "role": "system",
                        "content": f"[系统] 检测到最近 5 次调用中 {_stuck_tool} 占比 {_most[1]}/5，可能陷入重试循环。建议尝试 {_hint}。",
                    }
                )
