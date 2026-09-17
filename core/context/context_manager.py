"""上下文管理模块 — 合并 manager + retriever + filter_net"""

import json
import time
from pathlib import Path


def retrieve_related_history(user_id, session_id, current_task, limit=3):
    """从 SAG 查询与当前任务相关的历史上下文

    返回：list of {entity_name, signature, created_at}
    占位：filter_net 阶段（阶段6）接入工具流水入 SAG 后完整实现。
    """
    try:
        import psycopg2

        conn = psycopg2.connect("postgresql://clawsjoy:clawsjoy_secret@127.0.0.1:5432/clawsjoy_dev")
        cur = conn.cursor()
        cur.execute(
            "SELECT entity_name, signature, created_at FROM code_entities "
            "WHERE entity_type='tool_flow' AND signature ILIKE %s "
            "ORDER BY created_at DESC LIMIT %s",
            (f"%{current_task[:20]}%", limit),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [{"entity_name": r[0], "signature": r[1], "created_at": str(r[2])} for r in rows]
    except Exception:
        return []


def inject_retrieved(messages, retrieved):
    """把检索到的历史注入为 system 消息"""
    if not retrieved:
        return messages
    lines = ["[自动检索] 以下是与当前任务相关的历史上下文："]
    for r in retrieved:
        lines.append(f"- {r['entity_name']}: {str(r['signature'])[:200]}")
    messages.append({"role": "system", "content": "\n".join(lines)})
    return messages


# ===== #20 性能指标统计 =====
# tool_flow 追加 JSONL 指标文件(独立于 SAG, 供聚合统计): data/v8/tool_metrics.jsonl
# 每行: {tool, session_id, user_id, success, elapsed_ms, ts}
_TOOL_METRICS_PATH = None  # 测试隔离用
_TOOL_METRICS_LOCK = None
_TOOL_METRICS_FILE = "data/v8/tool_metrics.jsonl"


def _get_tool_metrics_lock():
    global _TOOL_METRICS_LOCK
    if _TOOL_METRICS_LOCK is None:
        import threading

        _TOOL_METRICS_LOCK = threading.Lock()
    return _TOOL_METRICS_LOCK


def _parse_flow_summary(summary, tool_name):
    """从 tool_flow summary 解析 success + elapsed_ms(向后兼容, 不破坏旧格式)。

    格式: "success (123ms)" / "error消息 (456ms)" / "exception: xxx (789ms)"
    """
    import re as _re

    _s = str(summary or "")
    _m = _re.search(r"\((\d+)\s*ms\)", _s)
    _elapsed = int(_m.group(1)) if _m else 0
    # #20 审核修复: 精确匹配成功格式 "success (Nms)"(tool_flow 生成格式固定),
    # 避免 "success=False (123ms)" 之类含 success 子串的失败 summary 被误判成功
    _low = _s.lower()
    if _re.match(r"^\s*success\s*\(", _low):
        _ok = True
    else:
        # 非成功格式一律视为失败(exception/error/fail/not found/success=False 等)
        _ok = False
    return _ok, _elapsed


def _append_tool_metric(tool_name, session_id, user_id, success, elapsed_ms, ts):
    """追加一行指标到 JSONL(线程安全)"""
    try:
        import os as _os

        _lock = _get_tool_metrics_lock()
        with _lock:
            if _TOOL_METRICS_PATH:
                _p = Path(_TOOL_METRICS_PATH)
            else:
                _base = _os.environ.get("PROJECT_ROOT", str(Path(__file__).resolve().parent.parent.parent))
                _p = Path(_base) / _TOOL_METRICS_FILE
            _p.parent.mkdir(parents=True, exist_ok=True)
            with open(str(_p), "a", encoding="utf-8") as _fh:
                _fh.write(
                    json.dumps(
                        {
                            "tool": str(tool_name or ""),
                            "session_id": str(session_id or ""),
                            "user_id": str(user_id or ""),
                            "success": success,
                            "elapsed_ms": int(elapsed_ms or 0),
                            "ts": float(ts or time.time()),
                        },
                        ensure_ascii=False,
                    )
                    + chr(10)
                )
    except Exception:
        pass


def record_tool_flow(tool_name, args, result_summary, user_id, session_id):
    """工具调用后记录流水入 SAG + #20 指标 JSONL"""
    _ok, _el = _parse_flow_summary(result_summary, tool_name)
    _append_tool_metric(tool_name, session_id, user_id, _ok, _el, time.time())
    try:
        from core.lib.code_entity_extractor import extractor

        entity_name = f"tool_flow::{tool_name}::{int(time.time())}"
        signature = json.dumps(
            {
                "tool": tool_name,
                "args": args if isinstance(args, dict) else {},
                "summary": result_summary[:200],
                "user_id": user_id,
                "session_id": session_id,
                "timestamp": time.time(),
                "success": _ok,
                "elapsed_ms": _el,
            },
            ensure_ascii=False,
        )
        extractor.upsert_entity(
            {
                "entity_type": "tool_flow",
                "entity_name": entity_name,
                "file_path": f"tool_flow/{session_id}",
                "signature": signature,
            }
        )
        return True
    except Exception:
        return False


def _p95(values):
    """P95 分位(升序); 空列表返回 0"""
    if not values:
        return 0
    _vs = sorted(values)
    _i = min(int(len(_vs) * 0.95), len(_vs) - 1)
    return _vs[_i]


def tool_flow_stats(window_hours=24, limit=100000):
    """#20 聚合统计: 按工具 / 按任务(session) 的成功率、平均耗时、P95。

    读取 data/v8/tool_metrics.jsonl 最近 window_hours 的记录。
    返回: {"generated_at", "window_hours", "total", "by_tool": {...}, "by_task": {...}}
    每项: {count, success, fail, success_rate, avg_ms, p95_ms}
    """
    try:
        import os as _os

        if _TOOL_METRICS_PATH:
            _p = Path(_TOOL_METRICS_PATH)
        else:
            _base = _os.environ.get("PROJECT_ROOT", str(Path(__file__).resolve().parent.parent.parent))
            _p = Path(_base) / _TOOL_METRICS_FILE
        if not _p.exists():
            return {"generated_at": time.time(), "window_hours": window_hours, "total": 0, "by_tool": {}, "by_task": {}}
        _cutoff = time.time() - float(window_hours) * 3600
        _by_tool = {}
        _by_task = {}
        _total = 0
        with _get_tool_metrics_lock():
            with open(str(_p), encoding="utf-8") as _fh:
                for _line in _fh:
                    _line = _line.strip()
                    if not _line:
                        continue
                    try:
                        _rec = json.loads(_line)
                    except Exception:
                        continue
                    if float(_rec.get("ts", 0)) < _cutoff:
                        continue
                    _total += 1
                    if _total > limit:
                        break
                    _tool = str(_rec.get("tool") or "unknown")
                    _sid = str(_rec.get("session_id") or "unknown")
                    _ok = _rec.get("success")
                    _ms = int(_rec.get("elapsed_ms", 0) or 0)
                    for _bucket, _k in ((_by_tool, _tool), (_by_task, _sid)):
                        _b = _bucket.setdefault(_k, {"count": 0, "success": 0, "fail": 0, "elapsed": []})
                        _b["count"] += 1
                        if _ok is True:
                            _b["success"] += 1
                        elif _ok is False:
                            _b["fail"] += 1
                        _b["elapsed"].append(_ms)

        def _finalize(_bucket):
            _out = {}
            for _k, _b in _bucket.items():
                _n = _b["count"]
                _sr = round(_b["success"] * 100.0 / _n, 1) if _n else 0.0
                _out[_k] = {
                    "count": _n,
                    "success": _b["success"],
                    "fail": _b["fail"],
                    "success_rate": _sr,
                    "avg_ms": round(sum(_b["elapsed"]) / _n, 1) if _n else 0,
                    "p95_ms": _p95(_b["elapsed"]),
                }
            return _out

        return {
            "generated_at": time.time(),
            "window_hours": window_hours,
            "total": _total,
            "by_tool": _finalize(_by_tool),
            "by_task": _finalize(_by_task),
        }
    except Exception as _e:
        print(f"[TOOL_METRICS] 统计失败: {_e}")
        return {
            "generated_at": time.time(),
            "window_hours": window_hours,
            "total": 0,
            "by_tool": {},
            "by_task": {},
            "error": str(_e)[:120],
        }


def query_tool_flow(query, limit=5):
    """查询工具流水（retriever 用）"""
    try:
        import psycopg2

        conn = psycopg2.connect("postgresql://clawsjoy:clawsjoy_secret@127.0.0.1:5432/clawsjoy_dev")
        cur = conn.cursor()
        cur.execute(
            "SELECT entity_name, signature FROM code_entities "
            "WHERE entity_type='tool_flow' AND signature ILIKE %s "
            "ORDER BY created_at DESC LIMIT %s",
            (f"%{query}%", limit),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [{"entity_name": r[0], "signature": json.loads(r[1])} for r in rows]
    except Exception:
        return []


def _inject_user_history(session_id, message, max_rounds=None):
    """#166 路牌注入：Agent 自动获取历史对话上下文。

    从 data/v8/user_messages/{session_id}.jsonl 读取最近消息（JSONL），
    并从 SAG（steps_summary 中 task_name 以 user_message_ 开头的记录）查询
    历史摘要，拼成可注入 _sys_prompt 的上下文片段。

    Args:
        session_id: 会话 ID（对应 data/v8/user_messages/{session_id}.jsonl）
        message: 当前用户消息（用于跳过自身）
        max_rounds: 最多注入最近多少轮对话（每轮 = 用户 + 助手 两条）

    Returns:
        str: 注入片段；无历史或失败返回 ""
    """
    # #166 从路由配置读取轮数：优先 V9 summary_layer.max_steps，回退 V8 core_layer.max_rounds，默认 3
    if max_rounds is None:
        try:
            # 2026-09-13 修静默失败：本模块**没有** _load_v9_routing_config 的 import →
            # 运行时 AttributeError → 被 except 吞 → 「按 YAML 配注入轮数」从迁入至今一次没生效。
            from core.gateway.v9_bridge.routing_config import _load_v9_routing_config as _load_v9_routing_config

            _cfg = _load_v9_routing_config()
            _mr = _cfg.get("summary_layer", {}).get("max_steps")
            if not _mr:
                with open(Path("config/v8/message_routing.yaml"), "r", encoding="utf-8") as _f:
                    _mr = (yaml.safe_load(_f) or {}).get("core_layer", {}).get("max_rounds")
            max_rounds = max(1, int(_mr or 3))
        except Exception:
            max_rounds = 3
    if not session_id:
        return ""
    parts = []

    # 1) JSONL 最近消息
    try:
        _fpath = Path("data/v8/user_messages") / f"{session_id}.jsonl"
        if _fpath.exists():
            _raw_lines = []
            with open(_fpath, "r", encoding="utf-8") as _f:
                _raw_lines = _f.readlines()
            _recent = []
            for _l in _raw_lines[-max_rounds * 2 :]:
                _l = _l.strip()
                if _l:
                    try:
                        _recent.append(json.loads(_l))
                    except Exception:
                        continue
            if _recent:
                _hist_lines = []
                for _entry in _recent:
                    _role = _entry.get("role", "")
                    _content = (_entry.get("content", "") or "").strip()
                    if not _content:
                        continue
                    # 跳过当前消息自身
                    if _role == "user" and _content[:200] == (message or "")[:200]:
                        continue
                    _label = "用户" if _role == "user" else "助手"
                    _hist_lines.append(f"{_label}: {_content[:200]}")
                if _hist_lines:
                    parts.append("【历史对话】\n" + "\n".join(_hist_lines))
    except Exception as _e:
        print(f"[USER_HISTORY] JSONL 读取失败: {_e}")

    # 2) SAG 摘要（task_name 前缀 user_message_ 的记录）
    try:
        from core.lib.code_entity_extractor import extractor as _hist_extractor

        _sag_rows = _hist_extractor.query_fulltext_by_keywords([session_id, "user_message_archive"])
        _sag_hits = []
        for _row in _sag_rows or []:
            _task = _row.get("task_name", "") or ""
            _sum = _row.get("summary", {}) or {}
            if not _task.startswith("user_message_"):
                continue
            # 精确匹配 session_id，避免串入其他会话的历史
            _sum_sid = _sum.get("session_id", "") or ""
            if _sum_sid and _sum_sid != session_id:
                continue
            _role = _sum.get("role", "")
            _content = (_sum.get("content", "") or "").strip()
            if not _content:
                continue
            # 跳过当前消息自身
            if _role == "user" and _content[:200] == (message or "")[:200]:
                continue
            _label = "用户" if _role == "user" else "助手"
            _sag_hits.append(f"{_label}: {_content[:300]}")
        if _sag_hits:
            parts.append("【SAG历史摘要】\n" + "\n".join(_sag_hits[-max_rounds * 2 :]))
    except Exception as _e2:
        print(f"[USER_HISTORY] SAG 查询失败: {_e2}")

    if not parts:
        return ""
    return "\n\n".join(parts)


def _get_skeleton_by_path(filepath, user_id="default", session_id="default"):
    """从 world_model 中提取单个文件的骨架"""
    import ast as _ast

    _state_file = Path(f"data/projects/{user_id}/{session_id}/clawsjoy_dev/.agent_state.json")
    if not _state_file.exists():
        return None
    try:
        _state = json.loads(_state_file.read_text(encoding="utf-8"))
        _wm = _state.get("world_model", {})
        if isinstance(_wm, str):
            try:
                _wm = json.loads(_wm)
            except (json.JSONDecodeError, ValueError):
                try:
                    _wm = _ast.literal_eval(_wm)
                except (ValueError, SyntaxError):
                    return None
        if not isinstance(_wm, dict):
            return None
        _info = _wm.get("modules", {}).get(filepath, {})
        return _info.get("skeleton") if _info.get("skeleton") else None
    except Exception:
        return None


def _is_repeat_read_attempt(messages, filepath):
    """检测 Agent 是否已经尝试读取过此文件（第二次读取放行）（从 agent_gateway_enhanced.py 迁移 v1）"""
    _count = 0
    for _m in messages:
        if _m["role"] == "assistant":
            for _tc in _m.get("tool_calls", []):
                if _tc.get("function", {}).get("name") == "read_file":
                    try:
                        _args = json.loads(_tc["function"]["arguments"])
                        if _args.get("path") == filepath:
                            _count += 1
                    except Exception:
                        pass
    return _count >= 1


def _is_repeat_read_attempt_v2(filepath, user_id="default", session_id="default"):
    _state_file = Path(f"data/projects/{user_id}/{session_id}/clawsjoy_dev/.agent_state.json")
    if not _state_file.exists():
        return False
    try:
        _state = json.loads(_state_file.read_text(encoding="utf-8"))
        _artifacts = _state.get("artifacts", [])
        _count = 0
        for _a in _artifacts:
            if _a.get("type") == "read_file" and _a.get("path", "").endswith(filepath):
                _count += 1
        return _count >= 1
    except Exception:
        return False


from core.gateway.execute_agent_task import _update_world_model


def _is_stale_read(filepath, lines_start, lines_end, cached):
    """判断是否为无效重复读取——同一位置连续缓存命中"""
