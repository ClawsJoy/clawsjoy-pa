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

    def post(self, role, text, topic=None):
        rows = self._read()
        seq = (rows[-1]["seq"] + 1) if rows else 1
        row = {"seq": seq, "role": role, "text": str(text)[:4000], "topic": topic, "ts": time.strftime("%H:%M:%S")}
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

    def respond(self, sid, user_text, topic=None, brain=None, profile_brief="", ledger_brief=""):
        s = self.session(sid)
        s.post("user", user_text, topic=topic)
        ctx = s.context_text(profile_brief, ledger_brief)
        if brain is None:
            reply = "PA(%s): 议题【%s】已记录; 待办见账本, 需要商量或分派就说。" % (sid, topic or s.latest_topic())
        else:
            reply = brain(ctx)
        s.post("assistant", reply, topic=topic or s.latest_topic())
        return {"session_id": sid, "topic": topic or s.latest_topic(), "context_used": ctx, "reply": reply}
