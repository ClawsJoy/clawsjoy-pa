# -*- coding: utf-8 -*-
"""PA 待办/跟进账本(2026-09-10 v0): 事无巨细, 不丢不拖。

kind: todo(任务) | verify(待核实) | followup(跟进) | decision(决策待定)

2026-09-18（X-17② 批 2 · DS 拍 A）：**读写都走统一出口**（`core/pa/state_out`）——
坏状态 fail-loud，不再静默回落空账本；业务结构判据（`items` 需为 list）**留 PA 侧**。
"""
import os
import time
from pathlib import Path

from core.pa.state_out import read_state, write_state

KINDS = {"todo", "verify", "followup", "decision"}
STATUSES = {"open", "in_progress", "done", "blocked", "cancelled"}


def _now():
    return time.strftime("%Y-%m-%d")


#: 写者标识（进出口的写者归属台账；供 detect_uninstrumented 识别绕过出口的写者）
_WRITER = "pa.ledger"


def _shape(doc):
    """**PA 侧业务结构判据**（X-17② 批 2 · DS 拍①：判据留 PA 侧，不给出口加回调）。"""
    if not isinstance(doc.get("items"), list):
        return False, "items 需为 list"
    return True, ""


class TodoStore:
    def __init__(self, path=None):
        self.path = Path(path or os.getenv("PA_LEDGER_PATH", "data/v9/pa/ledger.json"))
        self.items = []
        self.load()

    def load(self):
        """**不存在 ⇒ 空账本；存在但不可用 ⇒ 抛 PAStateCorrupt**（不再静默回落空账本）。"""
        self.items = []
        if self.path.exists():
            self.items = read_state(self.path, _WRITER, _shape).get("items") or []
        return self

    def save(self):
        """**走统一出口**（X-17② 批 2）：跨进程锁 + 原子替换 + 坏状态拒绝写入。"""
        write_state(
            self.path,
            _WRITER,
            _shape,
            {"version": 1, "updated": _now(), "items": self.items},
            reason="pa.ledger.save",
        )
        return self

    def _next_id(self):
        used = {i.get("id") for i in self.items}
        n = 1
        while ("t%d" % n) in used:
            n += 1
        return "t%d" % n

    def add(self, title, kind="todo", note="", status="open", due=None):
        if kind not in KINDS:
            raise ValueError("unknown kind: %s" % kind)
        it = {
            "id": self._next_id(),
            "title": title,
            "kind": kind,
            "note": note,
            "status": status,
            "created": _now(),
            "due": due,
        }
        self.items.append(it)
        self.save()
        return it

    def set_status(self, item_id, status, note=""):
        if status not in STATUSES:
            raise ValueError("unknown status: %s" % status)
        for it in self.items:
            if it.get("id") == item_id:
                it["status"] = status
                if note:
                    it["note"] = note
                self.save()
                return it
        return None

    def open_items(self, kinds=None):
        ks = kinds or list(KINDS)
        return [i for i in self.items if i.get("status") not in ("done", "cancelled") and i.get("kind") in ks]

    def brief(self):
        lines = []
        for k in KINDS:
            items = self.open_items([k])
            if not items:
                continue
            lines.append("【%s】" % k)
            for it in items:
                lines.append("  - [%s] %s (%s)" % (it.get("id"), it.get("title"), it.get("created")))
        return "\n".join(lines) or "(无未结事项)"
