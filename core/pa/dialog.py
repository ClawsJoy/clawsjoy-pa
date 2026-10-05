# -*- coding: utf-8 -*-
"""PA 对话运行时 v0(2026-09-10): 通道无关、随时打断、新话题不丢上下文。

不是 v9_agent_chat 的轮次制任务循环:
  - 会话=追加式消息流(JSONL 持久), 无预算/守卫/工具循环
  - 新话题=在既有流上继续(打断语义: 响应带 latest_topic, 历史全保留)
  - 响应素材 = 画像 brief + 账本 brief + 本会话最近上下文(由通道侧的"脑"生成自然语言)
brain: 可调用对象(context_text)->str; 默认返回结构化文本(测试/无脑环境可用)
"""
import json
import time
from pathlib import Path
import threading   # ⭐ PM 2026-10-05（承 技总 970 §三 · 我落）：护 post() 之「读-改-写」

_LOCKS, _LOCKS_GUARD = {}, threading.Lock()


def _lock_for(path):
    """进程内 per-path 锁（⛔ msvcrt ／ ⛔ 新依赖 · 与 subtask_executor 同形分族）。"""
    with _LOCKS_GUARD:
        _lk = _LOCKS.get(str(path))
        if _lk is None:
            _lk = _LOCKS[str(path)] = threading.Lock()
        return _lk


# ⭐ PM 2026-10-05 22:34 §四⒝-2（技总之域）：会话档之**源标**（加性字段 · ⛔ 破既有读者）
#   病（逐字）：档行＝{"seq","role","text","topic","ts"} ⇒ **无源标** ⇒ 档读者（PM ／ 老板 ／
#     日后之席）无从辨「模型断言」vs「有据之答」；老板所见「T1已完成」之编造正出此路
#     ⇒ 屏上有标 ／ **档中无标** ⇒ 事后取证唯见模型之言 ＝ 看似有据（承「假绿」之族）。
#   ⇒ 加**加性键**（JSONL 加键 ＝ 向后兼容 · ⛔ 改 `text` 之体 · ⛔ 改既有四键）：
#     `origin`         答之来源类别（⭐ PM 1183 §五.3：原名 `src` 与响应 `src`＝走径标 **同字异义** ⇒ 改 `origin` · 一名一义）
#                      ｜`refused`（闸拒 · 无据不答）｜`unspecified`（调用方未声明 ⇒ ⛔ 当有据）
#     `grounded`       bool ／ ⛔ 缺键（缺键 ＝ 未标 ⇔ ⛔「无据」）
#     `answer_source`  str（后端之原值：decision ／ knowledge ／ refused ／ model ／ …）⇒ 供回指
#   ⚠ **唯当有值 ⇒ 落键**（⛔ 落 None ／ ⛔ 落空串 ⇒ 免「假标」）⇒ 旧行形不变。
#   ⚠ ⭐ **两写路同形**（PM 定 · 须与 CW 对齐）：`/v9/pa/dialog`（脑路）与
#     `POST /v9/pa/turn`（前端写路）**同键同义** ⇒ 唯键名与形一致，读者方可一比。
ORIGIN_MODEL = "model"
ORIGIN_GROUNDED = "grounded"
ORIGIN_REFUSED = "refused"
ORIGIN_UNSPECIFIED = "unspecified"


def _post_row(row, origin=None, grounded=None, answer_source=None):
    u"""源标之加性字段（⛔ 覆盖既有四键 · 唯当有值 ⇒ 落键）。"""
    if origin is not None and str(origin) != "":
        row["origin"] = str(origin)
    if grounded is not None:
        if isinstance(grounded, str):
            grounded = grounded.strip().lower() in ("1", "true", "yes", "y", "有据")
        row["grounded"] = bool(grounded)
    if answer_source is not None and str(answer_source) != "":
        row["answer_source"] = str(answer_source)
    return row


class DialogSession:
    def __init__(self, session_id, data_dir):
        self.sid = str(session_id)
        self.path = Path(data_dir) / ("session_%s.jsonl" % self.sid)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self):
        rows = []
        if self.path.exists():
            for ln in open(self.path, encoding="utf-8"):
                try:
                    rows.append(json.loads(ln))
                except Exception:
                    continue
        return rows

    def _append(self, row):
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def post(self, role, text, topic=None, origin=None, grounded=None, answer_source=None):
        # ⭐ PM 2026-10-05（承 技总 970 §三）：⭐ 只包「读-改-写」（`seq` 之算在锁内）
        #   负控之证（技总 `971 §三`）：拆锁下 8 线程 × 50 ⇒ 重号 79 ／ 丢 2 轮
        # ⭐ PM 2026-10-05 22:34 §四⒝-2：**源标之加性字段**（见 `_post_row` 之注）
        with _lock_for(self.path):
            rows = self._read()
            seq = (rows[-1]["seq"] + 1) if rows else 1
            row = {"seq": seq, "role": role, "text": str(text)[:4000], "topic": topic, "ts": time.strftime("%H:%M:%S")}
            _post_row(row, origin=origin, grounded=grounded, answer_source=answer_source)
            self._append(row)
        return row

    def history(self, n=20):
        return self._read()[-n:]

    def latest_topic(self):
        rows = self._read()
        for r in reversed(rows):
            if r.get("topic"):
                return r["topic"]
        return ""

    def context_text(self, profile_brief="", ledger_brief=""):
        rows = self._read()
        tail = []
        for r in rows[-6:]:
            tail.append("%s(%s): %s" % (r["role"], r.get("topic") or "-", str(r["text"])[:200]))
        parts = []
        if profile_brief:
            parts.append("【老板画像】\n" + profile_brief)
        if ledger_brief:
            parts.append("【待办/跟进】\n" + ledger_brief)
        parts.append("【本会话(%s)最近上下文】\n%s" % (self.sid, "\n".join(tail)))
        return "\n".join(parts)


class DialogRuntime:
    def __init__(self, data_dir="data/v9/pa/sessions"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def session(self, sid):
        return DialogSession(sid, self.data_dir)

    def respond(self, sid, user_text, topic=None, brain=None, profile_brief="", ledger_brief="",
                origin=None, grounded=None, answer_source=None):
        s = self.session(sid)
        s.post("user", user_text, topic=topic)
        ctx = s.context_text(profile_brief, ledger_brief)
        if brain is None:
            reply = "PA(%s): 议题【%s】已记录; 待办见账本, 需要商量或分派就说。" % (sid, topic or s.latest_topic())
        else:
            reply = brain(ctx)
        # ⭐ PM 2026-10-05 22:34 §四⒝-2：本路**本即脑（模型）路** ⇒ 缺省标 `model`
        #   （真值 · ⛔ 冒 `grounded`）；调用方知其实（如闸已判有据）⇒ 以显式值覆之。
        s.post("assistant", reply, topic=topic or s.latest_topic(),
               origin=(origin or ORIGIN_MODEL), grounded=grounded,
               answer_source=(answer_source or ORIGIN_MODEL))
        return {"session_id": sid, "topic": topic or s.latest_topic(), "context_used": ctx, "reply": reply}
