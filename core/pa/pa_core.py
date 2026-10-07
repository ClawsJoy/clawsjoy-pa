# -*- coding: utf-8 -*-
"""PA 内核 v1(2026-09-10, 拍板选1后 MVP): 画像/账本/事件/对话/分派/审核 + vault 桥。

设计: 内核独立、纯逻辑、可测; 对话脑(LLM)与通道(语音/IM)是上层 adapter。
handle(action, payload) 唯一入口, 返回 JSON。
"""
import os
import sys
from pathlib import Path

from core.pa.dialog import DialogRuntime
from core.pa.dispatch import (DispatchRecord, SeatExecutor, StubExecutor, V9GatewayExecutor,
                              dispatch_and_review, make_contract)
from core.pa.events import EventLog
from core.pa.ledger import TodoStore
from core.pa.profile import ProfileStore
from core.pa.seed import purge as purge_legacy_seed


def _default_dir():
    return os.getenv("PA_DATA_DIR", "data/v9/pa")


class PaCore:
    def __init__(self, data_dir=None):
        self.dir = Path(data_dir or _default_dir())
        self.profile = ProfileStore(self.dir / "profile.json")
        self.ledger = TodoStore(self.dir / "ledger.json")
        self.events = EventLog(self.dir / "events.jsonl")
        self.dialog = DialogRuntime(str(self.dir / "sessions"))
        self.dispatch_rec = DispatchRecord(self.dir / "dispatch.jsonl")
        self.artifacts_dir = self.dir / "artifacts"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self._purge_legacy_seed()

    def _purge_legacy_seed(self):
        u"""清「已落之种子」（承 pm_1770 §二.1⒝⒞）—— 一次性 · 逐字比 · 留痕 · 幂等。

        ⚠ 昔之 `_ensure_seed`（首启**灌注**）⇒ **拔**（同件）：⛔ 再灌 —— 其为本席之私记
          （甬创 ／ OPC ／ WPS-AI 之属）⇒ 入用户之机 ＝ **以我方之记充机主之实**；
          且「空库之诚」：净机之面当「空 ⇒ 拒答（**设计**）」。
        此处唯「清」：老板之机（≥ `9.0.4`）已落种子 ⇒ **删码唯利新机**
          （其记仍在）⇒ 非清不可。
        ⚠ 清败 ⛔ 阻内核（PA 须能起）—— 然 **⛔ 静默**：以 stderr 显报（承「凡败须显」）。
        """
        try:
            n_p, n_l = purge_legacy_seed(self.profile, self.ledger, events=self.events)
        except Exception as e:                                    # noqa: BLE001 — 清败 ⛔ 阻内核
            sys.stderr.write("[pa] 清「已落之种子」⛔ 成：%s\n" % str(e)[:200])
            return
        if n_p or n_l:
            sys.stderr.write("[pa] 清「已落之种子」：画像 %d 条 ／ 账本 %d 条"
                             "（昔之灌注 ⇒ 已去）\n" % (n_p, n_l))

    # ---- actions ----
    def handle(self, action, payload=None):
        p = payload or {}
        try:
            if action == "context":
                return {"ok": True, "profile": self.profile.brief(), "ledger": self.ledger.brief()}
            if action == "profile_read":
                return {"ok": True, "entries": self.profile.active()}
            if action == "profile_sediment":
                e = self.profile.add(
                    p["domain"],
                    p["value"],
                    source=p.get("source", ""),
                    confidence=p.get("confidence", "medium"),
                    status=p.get("status", "confirmed"),
                )
                self.events.append(p["domain"], "sediment", {"value": p["value"]}, source=p.get("source", ""))
                return {"ok": True, "entry": e}
            if action == "profile_revise":
                e = self.profile.revise(p["id"], p["value"], source=p.get("source", ""), confidence=p.get("confidence"))
                if e:
                    self.events.append(e["domain"], "revise", {"value": p["value"]}, source=p.get("source", ""))
                return {"ok": True, "entry": e}
            if action == "profile_markdown":
                return {"ok": True, "markdown": self.profile.render_markdown()}
            if action == "todo_add":
                it = self.ledger.add(p["title"], kind=p.get("kind", "todo"), note=p.get("note", ""), due=p.get("due"))
                return {"ok": True, "item": it}
            if action == "todo_done":
                return {"ok": True, "item": self.ledger.set_status(p["id"], "done")}
            if action == "todo_revoke":
                it = self.ledger.revoke(p["id"], reason=p.get("reason", ""))
                if it is not None:
                    self.events.append("ledger", "revoke",
                                       {"id": p["id"], "title": it.get("title")},
                                       source=p.get("source", "pa/ledger/revoke"))
                return {"ok": True, "item": it}
            if action == "ledger_brief":
                return {"ok": True, "brief": self.ledger.brief()}
            # ---- 对话运行时 ----
            if action == "dialog_post":
                r = self.dialog.respond(
                    p["sid"],
                    p["text"],
                    topic=p.get("topic"),
                    brain=p.get("brain"),
                    profile_brief=p.get("profile_brief", self.profile.chat_brief(p.get("text", ""))),
                    ledger_brief=p.get("ledger_brief", ""),
                    # ⭐ PM 2026-10-05 22:34 §四⒝-2：源标之透传（⛔ 本层自造值 · ⛔ 覆盖后端之判）
                    origin=p.get("origin"), grounded=p.get("grounded"),
                    answer_source=p.get("answer_source"),
                )
                return {"ok": True, "dialog": r}
            if action == "dialog_context":
                s = self.dialog.session(p["sid"])
                return {"ok": True, "topic": s.latest_topic(), "history": s.history(p.get("n", 20))}
            # ---- 事件 ----
            if action == "events_tail":
                return {"ok": True, "events": self.events.tail(p.get("n", 50))}
            if action == "events_export":
                md = self.events.export_markdown(p.get("md_path"))
                return {"ok": True, "md": md}
            # ---- 分派 + 审核 ----
            if action == "dispatch":
                to_seat = str(p.get("to_seat") or "").strip()
                contract = make_contract(p["task_text"], to_seat=to_seat)
                ex = p.get("executor")
                if ex is None:
                    ex = SeatExecutor(to_seat) if to_seat else StubExecutor(str(self.artifacts_dir))
                result = ex.run(contract)
                row = dispatch_and_review(
                    contract, result, profile_brief=self.profile.brief(), record=self.dispatch_rec
                )
                return {"ok": True, "contract": contract, "result": result, "review": row}
            if action == "dispatch_v9":
                to_seat = str(p.get("to_seat") or "").strip()
                contract = make_contract(p["task_text"], to_seat=to_seat)
                ex = SeatExecutor(to_seat) if to_seat else V9GatewayExecutor(url=p.get("url"))
                result = ex.run(contract)
                row = dispatch_and_review(
                    contract, result, profile_brief=self.profile.brief(), record=self.dispatch_rec
                )
                return {"ok": True, "contract": contract, "result": result, "review": row}
            if action == "dispatch_history":
                return {"ok": True, "rows": self.dispatch_rec.rows}
            return {"ok": False, "error": "unknown action: %s" % action}
        except KeyError as e:
            return {"ok": False, "error": "missing payload field: %s" % e}
        except Exception as e:
            return {"ok": False, "error": "pa_core: %s" % str(e)[:200]}


def get_core():
    return PaCore()
