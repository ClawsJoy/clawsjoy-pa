# -*- coding: utf-8 -*-
"""PA 待办/跟进账本(2026-09-10 v0): 事无巨细, 不丢不拖。

kind: todo(任务) | verify(待核实) | followup(跟进) | decision(决策待定)
"""
import json
import os
import time
from pathlib import Path

KINDS = {"todo", "verify", "followup", "decision"}
STATUSES = {"open", "in_progress", "done", "blocked", "cancelled"}


def _now():
    return time.strftime("%Y-%m-%d")


class TodoStore:
    def __init__(self, path=None):
        self.path = Path(path or os.getenv("PA_LEDGER_PATH", "data/v9/pa/ledger.json"))
        self.items = []
        self.load()

    def load(self):
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                self.items = data if isinstance(data, list) else data.get("items", [])
            except Exception:
                self.items = []
        return self

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"version": 1, "updated": _now(), "items": self.items}, ensure_ascii=False, indent=1),
            encoding="utf-8",
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
