# -*- coding: utf-8 -*-
"""run_id —— 一次任务运行的全链标识（批152 · P0-0）。

设计原点（三条，都是「只有一个出口」的用法，见体检项 113）：
1. **定义只有一处**：`run_id = session_id + ":" + turn_id`（本模块 make_run_id）。
   注意 session_id 本身可能含 `:`（格式 "user:session"）⇒ 解析用 rsplit(":", 1)。
2. **落盘只有一个出口**：所有事件都经 `SessionEvent.to_dict()` 落 JSONL，因此在那里
   统一补 `run_id` 字段即可 —— **不改任何 log_event 调用点**，所有事件类型自动带上。
3. **取链只有一个入口**：`iter_run_events(run_id)` 机械扫 `data/session_logs/<session>.jsonl`。

为什么必须做（P0-0 的存在理由）：
- 批105 的「run_id 锚点窗口」是**手工在任务正文放唯一标记**换来的 ⇒ 不能机械化、且
  **措辞会改变行为**（批111 教训）；
- P0-1 的打点要归因、P0-4 要「每步 run_id 证据」——都建立在 run_id 是**系统字段**之上。

本模块**不依赖 session_log**（避免循环 import）：只按文件格式读 JSONL。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

RUN_SEP = ":"
DEFAULT_LOG_DIR = Path("data/session_logs")


def canonical_run_id(session_id: str, base_dir: Optional[Path] = None) -> str:
    """给出**与 SessionLog 落盘同源**的 run_id（批170）。

    背景（实测）：批167 的 round 级打点用 gateway 的 epoch 型 `_turn_id` 拼 run_id
    （`session_X:1789432222`），而 SessionLog 落盘的是 canonical 游标（`session_X:1`）
    ⇒ 两者**不同源** ⇒ `run_chain.py` 按打点里的 run_id 取到 **0 条事件**。

    优先级：①SessionLog 进程内游标 ②日志尾部的最后一个 run_id ③`session:0`。
    （本模块顶层刻意不 import session_log；这里用**函数内懒 import**，不引入循环依赖。）
    """
    try:
        from core.gateway.session_log import get_session_log  # 懒 import（避免循环依赖）

        _t = int(get_session_log(session_id, base_dir=base_dir).current_turn or 0)
        if _t > 0:
            return make_run_id(session_id, _t)
    except Exception:
        pass
    try:
        _last = ""
        for ev in iter_run_window(session_id, base_dir=base_dir):
            _last = ev.get("run_id") or _last
        if _last:
            return str(_last)
    except Exception:
        pass
    return make_run_id(session_id, 0)


# 与「全链」九段对应的事件类型关键词（用于链摘要；不改变任何判据，只是分类阅读）
CHAIN_HINTS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("plan", ("task_start", "turn_start", "goal_event", "plan")),
    ("execution", ("step_start", "step_end", "round", "assistant")),
    ("tool_events", ("tool", "tool_call", "tool_result")),
    ("guard_decision", ("guard", "deny", "allow", "write_pending")),
    ("artifact", ("artifact", "file", "write")),
    ("verification", ("verify", "verdict")),
    ("completion", ("turn_end", "done", "completion")),
    ("report", ("report", "notify", "final")),
)


def make_run_id(session_id: str, turn_id: Any) -> str:
    """run_id 的**唯一定义**：session_id + ':' + turn_id。"""
    try:
        _t = int(turn_id)
    except Exception:
        _t = 0
    return "%s%s%s" % (str(session_id or ""), RUN_SEP, _t)


def parse_run_id(run_id: str) -> Tuple[Optional[str], Optional[int]]:
    """把 run_id 还原成 (session_id, turn_id)；非法返回 (None, None)。

    session_id 可能自带 ':'（"user:session"）⇒ 从**最后**一个 ':' 切。
    """
    if not run_id or RUN_SEP not in str(run_id):
        return None, None
    _sid, _, _t = str(run_id).rpartition(RUN_SEP)
    if not _sid:
        return None, None
    try:
        return _sid, int(_t)
    except Exception:
        return None, None


def event_run_id(ev: Dict[str, Any]) -> str:
    """取一条事件记录的 run_id：**优先读字段**，老日志没有就按定义现算（向后兼容）。"""
    _r = ev.get("run_id")
    if _r:
        return str(_r)
    return make_run_id(ev.get("session_id", ""), ev.get("turn_id", 0))


def default_log_dir() -> Path:
    """日志根目录：优先 cwd 下的 data/session_logs（网关就是这么跑的）；
    若不存在（例如从别的目录调 CLI），回落到**代码根**下的 data/session_logs——
    避免「取链取到空」被误读成「这次跑没有任何事件」（体检项 63 的用法）。"""
    if DEFAULT_LOG_DIR.exists():
        return DEFAULT_LOG_DIR
    _root = Path(__file__).resolve().parents[2]  # core/gateway/run_id.py → 仓库根
    _alt = _root / "data" / "session_logs"
    return _alt if _alt.exists() else DEFAULT_LOG_DIR


def _log_file_for(session_id: str, base_dir: Optional[Path] = None) -> Path:
    _base = Path(base_dir) if base_dir else default_log_dir()
    _sid = str(session_id)
    if os.sep in _sid or "/" in _sid:
        _sid = _sid.replace("/", "_")
    return _base / ("%s.jsonl" % _sid)


def iter_run_events(run_id: str, base_dir: Optional[Path] = None) -> Iterable[Dict[str, Any]]:
    """机械取链：只出**属于该 run_id** 的事件（按落盘顺序）。

    容忍坏行（跳过多余/损坏 JSON），因为日志是 append-only 且可能被截断。
    """
    session_id, _turn = parse_run_id(run_id)
    if not session_id:
        return []
    _f = _log_file_for(session_id, base_dir)
    if not _f.exists():
        return []
    out: List[Dict[str, Any]] = []
    try:
        with open(_f, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                if not isinstance(ev, dict):
                    continue
                if event_run_id(ev) == run_id:
                    out.append(ev)
    except Exception:
        return out
    return out


def chain_summary(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """把一个 run 的事件列表归成「全链九段」的可读摘要（供 CLI / 报告用）。"""
    _by_type: Dict[str, int] = {}
    for ev in events:
        _t = str(ev.get("type") or "?")
        _by_type[_t] = _by_type.get(_t, 0) + 1
    _seg: Dict[str, int] = {}
    for _name, _keys in CHAIN_HINTS:
        _seg[_name] = sum(v for k, v in _by_type.items() if any(kk in k for kk in _keys))
    _first = events[0] if events else {}
    _last = events[-1] if events else {}
    return {
        "run_id": event_run_id(_first) if _first else "",
        "count": len(events),
        "types": _by_type,
        "segments": _seg,
        "t0": _first.get("ts"),
        "t1": _last.get("ts"),
        "first_type": _first.get("type"),
        "last_type": _last.get("type"),
    }


# ============================================================================
# 批152 · P0-0 追加：run 分组（turn_id 语义不纯时的**实用取链**方式）
# ----------------------------------------------------------------------------
# 实测（2026-09-14，session_146_verify3）：**同一次逻辑运行里，事件的 turn_id 有 4 种取值**：
#     turn=1789382956（epoch 秒：turn_start/step_start/step_end）
#     turn=1 / 2      （小计数器：assistant_message/tool_call/tool_result）
#     turn=0          （多数事件）
#     turn=-1         （approval.py 显式传的 -1）
# ⇒ 「run_id = session_id:turn_id」**机械可算**，但**一次运行会被切成 ≥4 个 run_id**。
# 因此这里补一个**按窗口分组**的取链：一次逻辑运行 = 一个 turn_start … 其后的 turn_end，
# 夹在其中的特殊 id（如 -1 的审批回执）也归入该 run —— today 就能取到**完整链**；
# 同时把「turn_id 不纯」作为 P0-0 的**已知限制 + 下一步（canonical 化）**上报（见执行卡）。
# ============================================================================


def _read_all(session_id: str, base_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """整文件读事件（容忍坏行）——供分组用，不做 run_id 过滤。"""
    _f = _log_file_for(session_id, base_dir)
    if not Path(_f).exists():
        return []
    out: List[Dict[str, Any]] = []
    try:
        with open(_f, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                if isinstance(ev, dict):
                    out.append(ev)
    except Exception:
        pass
    return out


def list_runs(session_id: str, base_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """按「run 窗口」分组：§turn_start§ 开新窗口，其后的 §turn_end§ 收尾；首个 turn_start 之前的事件归 run 0。"""
    evs = _read_all(session_id, base_dir)
    runs: List[Dict[str, Any]] = []
    cur: Optional[Dict[str, Any]] = None
    pre: List[Dict[str, Any]] = []
    for ev in evs:
        _t = str(ev.get("type") or "")
        if _t == "turn_start":
            if cur:
                runs.append(cur)
            cur = {
                "seq_from": ev.get("seq"),
                "seq_to": ev.get("seq"),
                "events": [ev],
                "started_at": ev.get("ts"),
                "ended_at": ev.get("ts"),
            }
        elif cur is None:
            pre.append(ev)
        else:
            cur["events"].append(ev)
            cur["seq_to"] = ev.get("seq")
            cur["ended_at"] = ev.get("ts")
    if cur:
        runs.append(cur)
    if pre:
        runs.insert(
            0,
            {
                "seq_from": pre[0].get("seq"),
                "seq_to": pre[-1].get("seq"),
                "events": pre,
                "started_at": pre[0].get("ts"),
                "ended_at": pre[-1].get("ts"),
            },
        )
    out: List[Dict[str, Any]] = []
    for i, r in enumerate(runs):
        _evs = r["events"]
        _types: Dict[str, int] = {}
        for e in _evs:
            _k = str(e.get("type"))
            _types[_k] = _types.get(_k, 0) + 1
        out.append(
            {
                "index": i,
                "seq_from": r["seq_from"],
                "seq_to": r["seq_to"],
                "count": len(_evs),
                "turn_ids": sorted({str(e.get("turn_id")) for e in _evs}),
                "started_at": r["started_at"],
                "ended_at": r["ended_at"],
                "types": _types,
                "user_head": next(
                    (
                        str((e.get("payload") or {}).get("content", ""))[:80]
                        for e in _evs
                        if e.get("type") == "user_message"
                    ),
                    "",
                ),
            }
        )
    return out


def iter_run_window(
    session_id: str, seq_from: int, seq_to: int, base_dir: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """取一个 run 窗口内的全部事件（含夹在其中的特殊 turn_id 事件，如 -1 的审批回执）。"""
    out = []
    for e in _read_all(session_id, base_dir):
        try:
            _s = int(e.get("seq"))
        except Exception:
            continue
        if int(seq_from) <= _s <= int(seq_to):
            out.append(e)
    return out


def latest_run(session_id: str, base_dir: Optional[Path] = None) -> Dict[str, Any]:
    """最后一个 run 窗口（today 取全链的默认入口）。"""
    _runs = list_runs(session_id, base_dir)
    return _runs[-1] if _runs else {}
