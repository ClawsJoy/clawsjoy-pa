# -*- coding: utf-8 -*-
"""PA 事件日志(2026-09-10 v0): 对话决策/偏好自动沉淀 -> 追加事件; 可导出 md 到 vault。

原则: 写事件不覆盖; 事件是画像/账本的上游(重放可重建)。

读侧口径（X-16 余项 · 2026-09-18 拍）: append-only 的**坏行不抛**（不像状态文件那样 fail-loud），
但必须**可见** —— 跳过该行 + 计数（`corrupt_lines`）+ 写 stderr；其余历史保留。
理由: 坏行不会导致后续覆盖（没有「读不动就当空基线再写」这条链），故按「可见降级」处置（经验库 L-08）。
"""
import json
import os
import sys
import time
from pathlib import Path


class EventLog:
    def __init__(self, path=None):
        self.path = Path(path or os.getenv("PA_EVENTS_PATH", "data/v9/pa/events.jsonl"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.corrupt_lines = 0

    def _report(self, msg):
        """坏行必须**可见**（计数 + stderr）；**不抛** —— append-only 的坏行不影响其余行。"""
        self.corrupt_lines += 1
        try:
            sys.stderr.write("[events] %s\n" % msg)
        except Exception:
            pass

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
        for no, ln in enumerate(open(self.path, encoding="utf-8"), 1):
            if not ln.strip():
                continue
            try:
                row = json.loads(ln)
            except Exception as e:
                self._report("第 %d 行不可解析（%s）—— 已跳过该行，其余历史保留" % (no, type(e).__name__))
                continue
            if not isinstance(row, dict):
                self._report("第 %d 行结构不符（须为 JSON 对象）—— 已跳过该行，其余历史保留" % no)
                continue
            out.append(row)
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
