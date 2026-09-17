# -*- coding: utf-8 -*-
"""PA 事件日志(2026-09-10 v0): 对话决策/偏好自动沉淀 -> 追加事件; 可导出 md 到 vault。

原则: 写事件不覆盖; 事件是画像/账本的上游(重放可重建)。
"""
import json
import os
import time
from pathlib import Path


class EventLog:
    def __init__(self, path=None):
        self.path = Path(path or os.getenv("PA_EVENTS_PATH", "data/v9/pa/events.jsonl"))
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, domain, kind, payload=None, source=""):
        row = {
            "seq": self._next_seq(),
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "domain": domain,
            "kind": kind,
            "source": source,
            "payload": payload or {},
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row

    def _next_seq(self):
        n = 0
        if self.path.exists():
            for _ in open(self.path, encoding="utf-8"):
                n += 1
        return n + 1

    def tail(self, n=50):
        out = []
        if not self.path.exists():
            return out
        for ln in open(self.path, encoding="utf-8"):
            try:
                out.append(json.loads(ln))
            except Exception:
                continue
        return out[-n:]

    def export_markdown(self, md_path=None):
        rows = self.tail(500)
        lines = ["# PA 事件日志(自动维护)", "", "> 对话决策/偏好沉淀事件; 画像与账本由这些事件驱动。", ""]
        for r in rows:
            p = r.get("payload") or {}
            pv = p.get("value", "")
            lines.append(
                "- %s [%s/%s] %s%s"
                % (
                    r.get("ts"),
                    r.get("domain"),
                    r.get("kind"),
                    str(pv)[:160],
                    (" (src: %s)" % r.get("source")) if r.get("source") else "",
                )
            )
        md = "\n".join(lines)
        if md_path:
            Path(md_path).parent.mkdir(parents=True, exist_ok=True)
            Path(md_path).write_text(md, encoding="utf-8")
        return md
