# -*- coding: utf-8 -*-
"""会话事件溯源日志 — P2a 骨架(先写不读, 双写与 messages 并行)

设计依据: docs/reports/p2_event_sourcing_design.md
目标: append-only 事件日志 + 增量投影, 实现"模型可见=已落盘"不变量。
P2a: 只建 SessionLog 类 + 事件写入(JSONL 落盘), 不改变现有 messages 行为。

事件类型: session_start/turn_start/step_start/user_message/assistant_message/
          tool_call/tool_result/runtime_context/step_end/turn_end/session_end
"""
from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.gateway.run_id import make_run_id  # 批152 P0-0: run_id 定义

# ===== 事件类型常量 =====
EV_SESSION_START = "session_start"
EV_TURN_START = "turn_start"
EV_TURN_END = "turn_end"
EV_STEP_START = "step_start"
EV_STEP_END = "step_end"
EV_USER_MESSAGE = "user_message"
EV_ASSISTANT_MESSAGE = "assistant_message"
EV_TOOL_CALL = "tool_call"
EV_TOOL_RESULT = "tool_result"
EV_RUNTIME_CONTEXT = "runtime_context"
EV_SESSION_END = "session_end"
EV_GOAL_EVENT = "goal_event"  # P1: goal 生命周期事件(created/progress/status/archived), 审计回放

# ===== 投影为消息的事件(其余事件不投影) =====
_MESSAGE_EVENTS = {EV_USER_MESSAGE, EV_ASSISTANT_MESSAGE, EV_TOOL_RESULT}


# B 块(2026-09-13): 纯续跑话语判定(窄名单, 定义在 core/gateway/resume_context.py)。
# 惰性导入防循环 import; 失败时退化为"不跳过"(保持旧行为, 不引入新故障)。
def is_resume_utterance(text):
    try:
        from core.gateway.resume_context import is_resume_utterance as _iru

        return _iru(text)
    except Exception:
        return False


@dataclass
class SessionEvent:
    """单条会话事件(不可变事实)"""

    seq: int
    ts: float
    session_id: str
    turn_id: int
    step_id: int
    type: str
    payload: Dict[str, Any]

    def to_dict(self) -> dict:
        # 批152 · P0-0：**run_id 系统字段的唯一落盘出口**。
        # 所有事件都经这里落 JSONL ⇒ 在这里补一个字段，**全部事件类型自动带 run_id**
        # （不改任何 log_event 调用点；定义见 core/gateway/run_id.py，体检项 113 的用法）。
        return {
            "seq": self.seq,
            "ts": self.ts,
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "step_id": self.step_id,
            "type": self.type,
            "payload": self.payload,
            "run_id": make_run_id(self.session_id, self.turn_id),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SessionEvent":
        return cls(
            seq=int(d["seq"]),
            ts=float(d["ts"]),
            session_id=str(d["session_id"]),
            turn_id=int(d.get("turn_id", 0)),
            step_id=int(d.get("step_id", 0)),
            type=str(d["type"]),
            payload=d.get("payload", {}),
        )


class SessionLog:
    """事件日志: append-only 内存 + JSONL 落盘, 增量投影消息。

    P2a 只提供 append/读取能力; 不改变调用方现有 messages 行为(双写)。
    """

    def __init__(self, session_id: str, log_file: Optional[Path] = None, base_dir: Optional[Path] = None):
        self.session_id = session_id
        # 存储: base_dir/session_log.jsonl(默认 data/projects/{uid}/{sid}/session_log.jsonl)
        if log_file is None:
            _sid_dir = str(session_id)
            # session_id 格式 "user:session" 或 "session"; 默认放 data/session_logs/
            _base = base_dir or Path("data/session_logs")
            log_file = _base / f"{_sanitize(_sid_dir)}.jsonl"
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._events: List[SessionEvent] = []
        self._seq = 0
        self._turn = 0
        self._step = 0
        self._load()  # 崩溃恢复: 读 JSONL 重放

    # ===== 写入 =====
    def append(
        self, type_: str, payload: Optional[Dict] = None, turn_id: Optional[int] = None, step_id: Optional[int] = None
    ) -> SessionEvent:
        """追加事件: 内存 + JSONL 落盘(append-only)。

        批155 · **turn_id canonical 化**（P0-0 收尾）—— 规则三条：
          ① **唯一推进点 = EV_TURN_START**：一次运行（一个 run）只对应一个 turn_id，
             由 §SessionLog§ 的游标给出（§self._turn§，§set_turn()§ 仍可显式设置）。
          ② 其余事件**一律盖游标**，忽略调用方传进来的 epoch 值 / §-1§ / 小计数器
             （实测问题：同一 run 里 §turn_start§ 用 §int(time.time())§、工具事件用 0/1/2、
             §approval§ 用 §-1§ ⇒ 一次运行被切成 ≥4 个 run_id，取全链要打补丁）。
          ③ 调用方原值**不丢**：与游标不同时记进 §payload["turn_id_raw"]§（可追溯）。
        """
        with self._lock:
            self._seq += 1
            _pl = dict(payload or {})
            _raw = turn_id if turn_id is not None else _pl.get("turn_id")
            if type_ == EV_TURN_START:
                self._turn += 1  # ① 唯一推进点
            _canon = self._turn
            if _raw is not None and str(_raw) != str(_canon):
                _pl["turn_id_raw"] = _raw  # ③ 原值留痕
            _pl["turn_id"] = _canon
            ev = SessionEvent(
                seq=self._seq,
                ts=time.time(),
                session_id=self.session_id,
                turn_id=_canon,  # ② 盖游标
                step_id=step_id if step_id is not None else self._step,
                type=type_,
                payload=_pl,
            )
            self._events.append(ev)
            self._flush_one(ev)
            return ev

    def _flush_one(self, ev: SessionEvent) -> None:
        """追加写一行 JSONL(带锁, 与 .agent_state.json 同模式)"""
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(ev.to_dict(), ensure_ascii=False, default=str) + "\n")
                f.flush()
        except Exception:
            pass  # 落盘失败不影响内存事件(降级)

    # ===== 游标管理 =====
    def set_turn(self, turn_id: int) -> None:
        self._turn = turn_id

    def set_step(self, step_id: int) -> None:
        self._step = step_id

    def begin_turn(self) -> int:
        self._turn += 1
        self._step = 0
        return self._turn

    def begin_step(self) -> int:
        self._step += 1
        return self._step

    @property
    def current_turn(self) -> int:
        """当前 **canonical turn 游标**（批170：给外部打点用，避免它们各算一套 turn_id）。

        为什么需要这个属性：批167 的 round 级打点用 gateway 自己的 ⟪_turn_id⟫（epoch 型）
        拼 run_id ⇒ 与 SessionLog 落盘的 canonical run_id（⟪session:N⟫）**不同源** ⇒
        ⟪tools/run_chain.py <打点里的 run_id>⟫ 取到 **0 条事件**（P0-1 的「每步 run_id 证据」因此不成立）。
        打点一律改用本属性 ⇒ 打点与落盘**同一个 run_id**。
        """
        return self._turn

    # ===== 读取 =====
    def events(self) -> List[SessionEvent]:
        return list(self._events)

    def derive_messages(self, last_task_only: bool = False) -> List[dict]:
        """从事件投影 messages(仅 user/assistant/tool_result)

        P2b 修复: 过滤未执行的 tool_calls —— range(8)/max_total_tools 终止时,
        最后一轮 assistant 可能带 tool_calls 但无对应 tool_result, 投影出
        "assistant with tool_calls + 无 tool 响应" → DeepSeek 400。
        此处先收集全部 tool_result 的 call_id, 投影 assistant 时只保留有响应的
        tool_calls; 全部无响应则整个 tool_calls 字段不投影(退化为纯文本消息)。

        R5(2026-08-31): last_task_only=True 任务级上下文隔离 — 只投影最近一次
        真实用户消息(source=user_input)之后的事件。原实现投影全部历史: 3935 条
        tool_result 跨任务累积 → 每轮 input 48K。历史任务的工具输出对本任务无价值,
        还挤占预算。审计/归档仍在事件层保留, 仅投影截断。
        """
        _events = self._events
        if last_task_only:
            # 找最后一个真实用户消息索引(向后), 之后的事件才投影
            # 2026-09-07 任务死循环根因修复: 内部注入消息("[系统]" 前缀 — goal 续跑/steer/
            # 环境快照等, 旧日志曾以 source=user_input 落盘) 不能当"真实用户任务"边界 —
            # 否则重试/续跑时边界落在注入消息上, 真实任务文本被投影切掉 → 模型只见失败尾巴
            # → 空工具调用/空回复死循环。新写入已按 source=runtime_context 落盘(见写入方),
            # 此处对旧日志做防御性过滤, 双保险。
            _last_user_idx = -1
            for _ei in range(len(_events) - 1, -1, -1):
                _ev = _events[_ei]
                if _ev.type == EV_USER_MESSAGE and _ev.payload.get("source") == "user_input":
                    _ev_content = str(_ev.payload.get("content") or "")
                    if _ev_content.startswith("[系统]"):
                        continue  # 内部注入不当任务边界
                    # B 块(2026-09-13): 纯续跑话语("继续"/"继续任务")也**不是任务边界**。
                    # 事故(第三次同型): 老板回「继续」时, 边界落在"继续"这条事件上 →
                    # 投影从"继续"开始, **真实任务原文被整段切掉** → 模型手里只有两个字,
                    # 只能重新问/乱逛 → 任务链断(与恢复层注入的 BRIEF 一起被 rebuild_context 冲掉)。
                    # 这里继续往前找真正的任务消息; 找不到就退回不截断(全量投影, 安全侧)。
                    if is_resume_utterance(_ev_content):
                        continue
                    _last_user_idx = _ei
                    break
            if _last_user_idx >= 0:
                _events = _events[_last_user_idx:]
        # 第一遍: 收集已有 tool_result 的 call_id(与顺序无关, 容忍乱序落盘)
        _resolved_ids = {
            ev.payload.get("call_id") for ev in _events if ev.type == EV_TOOL_RESULT and ev.payload.get("call_id")
        }
        msgs = []
        for ev in _events:
            if ev.type == EV_USER_MESSAGE:
                # role 透传: 守卫注入的 system 消息在事件层记 user_message, 投影带原 role
                # R5(2026-08-31): 过滤 browser_local 审计回显(source=browser_local) — 本意是审计落盘,
                # 但被投影进 LLM 上下文 → 每次 browser_local 调用多一条 system(含完整命令), 跨任务堆积
                # → 11 次调用涨到 48K/轮。审计保留在事件层(审计面板可查), 不再注入模型上下文。
                if ev.payload.get("source") == "browser_local":
                    continue
                _m = {"role": ev.payload.get("role", "user"), "content": ev.payload.get("content", "")}
                _m.update(ev.payload.get("extra", {}))
                msgs.append(_m)
            elif ev.type == EV_ASSISTANT_MESSAGE:
                m = {"role": "assistant", "content": ev.payload.get("content", "")}
                if ev.payload.get("tool_calls"):
                    # P2b: 仅保留有 tool_result 响应的 tool_calls(过滤未执行的)
                    _valid_tcs = [
                        tc for tc in ev.payload["tool_calls"] if isinstance(tc, dict) and tc.get("id") in _resolved_ids
                    ]
                    if _valid_tcs:
                        m["tool_calls"] = _valid_tcs
                # 实测规则: 带 tool_calls 的 assistant 必须带 reasoning_content 字符串字段(可为空),
                # 否则 DeepSeek 400 "reasoning_content must be passed back"。
                # 事件 payload 可能存 None/缺失(旧事件) → derive 时统一补空字符串。
                if isinstance(ev.payload.get("reasoning_content"), str):
                    m["reasoning_content"] = ev.payload["reasoning_content"]
                elif m.get("tool_calls"):
                    m["reasoning_content"] = ""
                msgs.append(m)
            elif ev.type == EV_TOOL_RESULT:
                _tc = ev.payload.get("content", "") or ""
                if "未知工具" in _tc:
                    continue  # 过滤「未知工具」脏数据(7B 早期幻觉/历史残留)
                msgs.append({"role": "tool", "tool_call_id": ev.payload.get("call_id", ""), "content": _tc})
        return msgs

    def derive_turns(self) -> List[dict]:
        """从事件日志重建 turn 结构(审计用, 与 derive_messages 互补)。

        返回: [{turn_id, reason, reason_detail, started_at, steps: [
                {step_id, tools: [{name, call_id, success}], tokens}]}]
        """
        turns = []
        cur = None
        cur_step = None
        for ev in self._events:
            if ev.type == EV_TURN_START:
                cur = {
                    "turn_id": ev.payload.get("turn_id", ev.turn_id),
                    "reason": None,
                    "reason_detail": "",
                    "started_at": ev.ts,
                    "steps": [],
                }
            elif ev.type == EV_STEP_START:
                if cur is not None:
                    cur_step = {
                        "step_id": ev.payload.get("step_id", ev.step_id),
                        "tools": [],
                        "tokens": ev.payload.get("tokens", 0),
                    }
                    cur["steps"].append(cur_step)
            elif ev.type == EV_TOOL_CALL and cur_step is not None:
                cur_step["tools"].append(
                    {"name": ev.payload.get("name", ""), "call_id": ev.payload.get("call_id", ""), "success": None}
                )
            elif ev.type == EV_TOOL_RESULT and cur_step is not None and cur_step["tools"]:
                for _t in reversed(cur_step["tools"]):
                    if _t["call_id"] == ev.payload.get("call_id", "") and _t["success"] is None:
                        _t["success"] = bool(ev.payload.get("success"))
                        _t["content_len"] = len(str(ev.payload.get("content", "")))
                        break
            elif ev.type == EV_TURN_END:
                if cur is not None:
                    cur["reason"] = ev.payload.get("reason", "")
                    cur["reason_detail"] = ev.payload.get("reason_detail", "")
                    cur["tokens"] = ev.payload.get("tokens", 0)
                    turns.append(cur)
                    cur = None
                    cur_step = None
        return turns

    # ===== 持久化 =====
    def _load(self) -> None:
        """崩溃恢复: 读 JSONL 重放(校验 seq 单调)"""
        try:
            if not self.log_file.exists():
                return
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ev = SessionEvent.from_dict(json.loads(line))
                        if ev.seq <= self._seq:
                            continue  # 跳过重复/乱序
                        self._events.append(ev)
                        self._seq = ev.seq
                        self._turn = max(self._turn, ev.turn_id)
                        self._step = max(self._step, ev.step_id)
                    except Exception:
                        continue  # 损坏行跳过
        except Exception:
            pass

    def __len__(self) -> int:
        return len(self._events)


# ===== 会话日志注册表(进程内) =====
_logs: Dict[str, SessionLog] = {}
_logs_lock = threading.Lock()


def get_session_log(session_id: str, base_dir: Optional[Path] = None) -> SessionLog:
    """获取/创建会话日志(幂等, 进程内缓存)"""
    with _logs_lock:
        log = _logs.get(session_id)
        if log is None:
            log = SessionLog(session_id, base_dir=base_dir)
            _logs[session_id] = log
        return log


def _sanitize(name: str) -> str:
    """文件名安全化(替换路径分隔符)"""
    return name.replace("/", "_").replace(":", "_").replace("\\", "_")


# 便捷写入(供双写接入点调用, 带 try/except 降级)
def log_event(
    session_id: str,
    type_: str,
    payload: Optional[Dict] = None,
    turn_id: Optional[int] = None,
    step_id: Optional[int] = None,
) -> Optional[SessionEvent]:
    """安全追加事件(不抛异常, 失败降级)"""
    try:
        return get_session_log(session_id).append(type_, payload, turn_id, step_id)
    except Exception as _e:
        print(f"[SESSION_LOG_FAIL] type={type_} err={_e}")
        return None
