"""上下文管理模块 — 合并 manager + retriever + filter_net"""

import hashlib
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


# ⭐ T2-刀9 §二（2026-10-05 · PM 裁「准你办」）：失败之**因**之分
#   首辨「**闸之拦** ⟷ **器之坏**」（承「假红亦病」：拦不是坏）。
#   标识取**真源**：失败行之 `error` 原文（`AuditGuard` 传 `result.get("error")` · 见 guards/registry.py:640）
FAIL_KIND_MARKS = (
    ("guard_deny", ("[guard_deny]", "guard_deny", "越权", "工具调用被拒绝", "被拦截", "forbidden")),
    ("write_pending", ("write_pending", "待审批", "写入待审")),
    ("not_found", ("文件不存在", "目录不存在", "不存在", "not found", "no such file", "filenotfounderror")),
    ("timeout", ("timeout", "timed out", "超时")),
)
FAIL_KIND_BLOCK = ("guard_deny", "write_pending")          # 「闸之拦」
FAIL_KIND_BROKEN = ("tool_error", "not_found", "timeout")  # 「器之坏」


def classify_fail_kind(result_summary, tool_name=""):
    """⭐ T2-刀9 §二：失败之因分类（仅失败行调；成功行 ⛔ 调）。"""
    _low = str(result_summary or "").lower()
    for _k, _marks in FAIL_KIND_MARKS:
        for _m in _marks:
            if _m.lower() in _low:
                return _k
    return "tool_error"


def _append_tool_metric(tool_name, session_id, user_id, success, elapsed_ms, ts, fail_kind=None):
    """追加一行指标到 JSONL(线程安全)

    ⭐ T2-刀9 §二：**只增** `fail_kind` 一键（失败之因；成功行 ⛔ 调）。
    ⚠ 旧行**无此键** ⇒ 面须以「键在否」分「**旧行未标**」⟷「新行已标」（承「式未标 ＝ 缺」）。
    """
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
                            "fail_kind": (str(fail_kind) if fail_kind else None),
                        },
                        ensure_ascii=False,
                    )
                    + chr(10)
                )
    except Exception:
        pass


_TF_STAMP_LOCK = None
_TF_STAMP_LAST = [0]


def _next_tool_flow_stamp():
    """审计键之刻：**毫秒** + 同进程严格递增（老板 2026-10-03 裁「秒 -> 毫秒」）。

    为什么：原式 ``int(time.time())`` 是**秒**粒度 ⇒ 同一秒内的两次调用**同名**，
    第二条被 ``upsert_entity`` 吞掉。实测 2026-10-03 20:49:05：两发
    ``/v9/sandbox/query_index`` 只落 1 行（``tool_flow::query_index::1791031745``）。
    审计是「每一句都能被查」的地基 ⇒ 键必须唯一。
    反例门：同秒连发两次 ⇒ 须落**两**行。
    """
    global _TF_STAMP_LOCK
    import threading
    if _TF_STAMP_LOCK is None:
        _TF_STAMP_LOCK = threading.Lock()
    with _TF_STAMP_LOCK:
        _ms = int(time.time() * 1000)
        if _ms <= _TF_STAMP_LAST[0]:
            _ms = _TF_STAMP_LAST[0] + 1
        _TF_STAMP_LAST[0] = _ms
        return _ms


def record_tool_flow(tool_name, args, result_summary, user_id, session_id):
    """工具调用后记录流水入 SAG + #20 指标 JSONL"""
    _ok, _el = _parse_flow_summary(result_summary, tool_name)
    # ⭐ T2-刀9 §二：失败行落**因**（成功行 ⛔ 调）
    _fk = (None if _ok else classify_fail_kind(result_summary, tool_name))
    _append_tool_metric(tool_name, session_id, user_id, _ok, _el, time.time(), fail_kind=_fk)
    try:
        from core.lib.code_entity_extractor import extractor

        entity_name = f"tool_flow::{tool_name}::{_next_tool_flow_stamp()}"
        # ⭐ 写入面改形（老板 2026-10-03 裁 · ② · 出新版）：旧形把 args（含 query 原文）
        # 逐字写进 signature ⇒ 谁搜过什么永久留在检索面 ⇒ 污染（ILIKE 命中自己的审计行）
        # ＋ 隐私双料。新形（sigv=2）：args 只留 sha256 ＋ 条数，⛔ 不留原文。
        # 判据：写入后用原文子串在全表搜 ⇒ 须 0 命中（不回流）。
        _args_obj = args if isinstance(args, dict) else {}
        _args_sha256 = hashlib.sha256(
            json.dumps(_args_obj, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        signature = json.dumps(
            {
                "sigv": 2,
                "tool": tool_name,
                "args_sha256": _args_sha256,
                "args_n": len(_args_obj),
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
                        _b = _bucket.setdefault(_k, {"count": 0, "success": 0, "fail": 0, "elapsed": [],
                                                     "fail_kinds": {}})
                        _b["count"] += 1
                        if _ok is True:
                            _b["success"] += 1
                        elif _ok is False:
                            _b["fail"] += 1
                            # ⭐ 旧行无 `fail_kind` 键 ⇒ 照实记「未标」（⛔ 填「坏」⇒ 免假红）
                            _fk2 = _rec.get("fail_kind") or "未标（旧行无此键 ⇒ 因未知）"
                            _b["fail_kinds"][str(_fk2)] = _b["fail_kinds"].get(str(_fk2), 0) + 1
                        _b["elapsed"].append(_ms)

        def _finalize(_bucket):
            _out = {}
            for _k, _b in _bucket.items():
                _n = _b["count"]
                _sr = round(_b["success"] * 100.0 / _n, 1) if _n else 0.0
                _fk = _b.get("fail_kinds") or {}
                _blk = sum(v for k, v in _fk.items() if k in FAIL_KIND_BLOCK)
                _brk = sum(v for k, v in _fk.items() if k in FAIL_KIND_BROKEN)
                _unl = sum(v for k, v in _fk.items() if k not in FAIL_KIND_BLOCK and k not in FAIL_KIND_BROKEN)
                _out[_k] = {
                    "count": _n,
                    "success": _b["success"],
                    "fail": _b["fail"],
                    "success_rate": _sr,
                    "avg_ms": round(sum(_b["elapsed"]) / _n, 1) if _n else 0,
                    "p95_ms": _p95(_b["elapsed"]),
                    # ⭐ T2-刀9 §二：失败之因分布 ＋ 「拦 ⟷ 坏」之合
                    "fail_kinds": _fk,
                    "blocked_vs_broken": {"blocked": _blk, "broken": _brk, "unlabeled": _unl},
                }
            return _out

        _bt = _finalize(_by_tool)
        _bk = _finalize(_by_task)
        _blk_n = sum(v["blocked_vs_broken"]["blocked"] for v in _bt.values())
        _brk_n = sum(v["blocked_vs_broken"]["broken"] for v in _bt.values())
        _unl_n = sum(v["blocked_vs_broken"]["unlabeled"] for v in _bt.values())
        return {
            "generated_at": time.time(),
            "window_hours": window_hours,
            "total": _total,
            "by_tool": _bt,
            "by_task": _bk,
            "blocked_vs_broken": {"blocked": _blk_n, "broken": _brk_n, "unlabeled": _unl_n},
            "judge": ("「拦」＝闸之拦（guard_deny ＋ write_pending · ⛔ 器之坏）；"
                      "「坏」＝器之坏（tool_error ＋ not_found ＋ timeout）；"
                      "「unlabeled」＝旧行无 `fail_kind` 键 ⇒ 因**未知**（⛔ 归入坏）"),
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
