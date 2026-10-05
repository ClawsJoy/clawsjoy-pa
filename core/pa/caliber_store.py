# -*- coding: utf-8 -*-
"""口径卡 · 外置 store + 生命周期 + 留痕（P7 · CW 2026-09-29）

为什么：原实现把 CALIBER 写死在 core/pa/caliber.py ⇒ **改口径 = 改源码**：
无 owner、无 updated、无改前值 ⇒ 「口径变更单」没有落点（PM R2/R6 悬空）。

真源 / 留痕:
  store  data/v9/pa/caliber.json          当前生效卡片（唯一真源）
  log    data/v9/pa/caliber_changes.jsonl **append-only**，每次变更一条，含改前值
  seed   core/pa/caliber.py::CALIBER      仅在 store 不存在时回落，⛔ 不覆盖已有 store

纪律:
  - 写前先记改前值（prev_status / prev_note）⇒ 回答「改前是什么」
  - id / status / owner / why 缺一项即拒（fail-loud，⛔ 不给默认值）
  - 原子写（tmp + os.replace）；只增不删
  - store 损坏 ⇒ CaliberStoreCorrupt（⛔ 不静默回种子）
"""
import json
import os
from datetime import datetime
from pathlib import Path

STATUSES = ("confirmed", "unverified", "pending")

# 可改字段集（P8）：⛔ 与留痕字段集必须对齐 —— 可改就必须有 prev_
MUTABLE_FIELDS = ("status", "owner", "note", "pattern", "topic", "supersedes")


def _touched_fields(rec):
    """本次请求**出现**的可改字段集（判据的驱动面 = 请求里的字段，⛔ 不是「留痕里凑出来的字段」）。"""
    t = {"status"}  # status 恒为必填 ⇒ 恒在面内
    for f in MUTABLE_FIELDS:
        if isinstance(rec, dict) and f in rec and rec[f] is not None:
            t.add(f)
    return t


def audit_prev_coverage(rec, entry):
    """⭐ P8 判据（可机检）：对本次请求里出现的**每个**可改字段，
    留痕条目里必须存在 `prev_<字段>`。返回缺失列表 —— ⛔ 空列表才算过，⛔ 不许只判「有条目」。"""
    return [f for f in sorted(_touched_fields(rec)) if ("prev_" + f) not in (entry or {})]


def _build_entry(rec, cid, op, owner, why, before, card, ts):
    """留痕条目：逐字段写 prev_<f> / new_<f>；缺 prev_ ⇒ 当场抛（fail-loud）。"""
    entry = {"ts": ts, "id": cid, "op": op, "owner": owner, "why": why}
    for f in sorted(_touched_fields(rec)):
        entry["prev_" + f] = (before or {}).get(f)
        entry["new_" + f] = card.get(f)
    missing = audit_prev_coverage(rec, entry)
    if missing:
        raise CaliberStoreError("留痕缺 prev_：%s（P8 判据）" % ",".join(missing))
    return entry


class CaliberStoreError(ValueError):
    """输入不合法 ⇒ 拒收（不是内部错）。"""


class CaliberStoreCorrupt(RuntimeError):
    def __init__(self, path, msg):
        super().__init__("%s: %s" % (path, msg))
        self.path = str(path)


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class CaliberStore:
    def __init__(self, data_dir="data/v9/pa"):
        self.dir = Path(data_dir)
        self.path = self.dir / "caliber.json"
        self.log_path = self.dir / "caliber_changes.jsonl"

    # ---- 读 ----
    def seed_cards(self):
        from core.pa.caliber import CALIBER

        out = []
        for c in CALIBER:
            d = dict(c)
            d.setdefault("owner", None)
            d.setdefault("updated", None)
            d.setdefault("supersedes", None)
            d.setdefault("change_count", 0)
            out.append(d)
        return out

    def load(self):
        """返回 {"source": "store"|"seed", "cards": [...]}。"""
        if not self.path.is_file():
            return {"source": "seed", "cards": self.seed_cards()}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as e:
            raise CaliberStoreCorrupt(self.path, "JSON 解析失败: %s" % e)
        cards = raw.get("cards") if isinstance(raw, dict) else raw
        if not isinstance(cards, list):
            raise CaliberStoreCorrupt(self.path, "cards 不是列表")
        for c in cards:
            if not isinstance(c, dict) or not c.get("id") or not c.get("status"):
                raise CaliberStoreCorrupt(self.path, "卡片缺 id/status: %r" % (c,))
            if c["status"] not in STATUSES:
                raise CaliberStoreCorrupt(self.path, "非法 status: %r" % c["status"])
            c.setdefault("owner", None)
            c.setdefault("updated", None)
            c.setdefault("supersedes", None)
            c.setdefault("change_count", 0)
        return {"source": "store", "cards": cards}

    def cards(self):
        return self.load()["cards"]

    def get(self, cid):
        for c in self.cards():
            if c.get("id") == cid:
                return c
        return None

    def summary(self):
        out = []
        for c in self.cards():
            out.append({
                "id": c["id"], "topic": c.get("topic"), "status": c["status"],
                "note": c.get("note"), "owner": c.get("owner"),
                "updated": c.get("updated"), "supersedes": c.get("supersedes"),
                "change_count": c.get("change_count", 0),
            })
        return out

    def counts(self):
        s = {"confirmed": 0, "unverified": 0, "pending": 0}
        for c in self.cards():
            s[c["status"]] = s.get(c["status"], 0) + 1
        return s

    def history(self, cid=None):
        if not self.log_path.is_file():
            return []
        recs = []
        for ln in self.log_path.read_text(encoding="utf-8", errors="replace").splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                o = json.loads(ln)
            except Exception:
                continue
            if cid is None or o.get("id") == cid:
                recs.append(o)
        return recs

    # ---- 写 ----
    def _atomic(self, text):
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = str(self.path) + ".tmp_p7"
        with open(tmp, "wb") as f:
            f.write(text.encode("utf-8"))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.path)

    def apply_change(self, rec):
        """口径变更单。rec: {id, status, owner, why, note?, pattern?, supersedes?, op?}"""
        if not isinstance(rec, dict):
            raise CaliberStoreError("变更单必须是对象")
        cid = (rec.get("id") or "").strip()
        op = (rec.get("op") or "update").strip()
        status = (rec.get("status") or "").strip()
        owner = (rec.get("owner") or "").strip()
        why = (rec.get("why") or "").strip()
        if not cid:
            raise CaliberStoreError("缺 id")
        if status not in STATUSES:
            raise CaliberStoreError("status 必须是 %s" % "/".join(STATUSES))
        if not owner:
            raise CaliberStoreError("缺 owner（谁负责复认）—— ⛔ 不给默认值")
        if not why:
            raise CaliberStoreError("缺 why（为什么改）—— ⛔ 不给默认值")
        if op not in ("update", "add"):
            raise CaliberStoreError("op 只能是 update/add")

        st = self.load()
        cards = st["cards"]
        idx = None
        for i, c in enumerate(cards):
            if c.get("id") == cid:
                idx = i
                break
        # ⚠ 改前值必须是**独立快照**：下面会就地把卡片改掉，
        #    若直接引用同一对象，留痕里的 prev_* 会被自己覆盖（= 记不到改前）。
        before = dict(cards[idx]) if idx is not None else None
        if op == "update" and before is None:
            raise CaliberStoreError("update 找不到卡片: %s" % cid)
        if op == "add" and before is not None:
            raise CaliberStoreError("add 但卡片已存在: %s" % cid)

        if before is None:
            card = {
                "id": cid, "topic": rec.get("topic"), "status": status,
                "pattern": rec.get("pattern"), "note": rec.get("note"),
                "owner": owner, "updated": _now(),
                "supersedes": rec.get("supersedes"), "change_count": 1,
            }
            cards.append(card)
        else:
            # 就地改**列表里的那个对象**（不是副本），否则写回的还是旧值
            card = cards[idx]
            if rec.get("note") is not None:
                card["note"] = rec["note"]
            if rec.get("pattern") is not None:
                card["pattern"] = rec["pattern"]
            if rec.get("topic") is not None:
                card["topic"] = rec["topic"]
            card["status"] = status
            card["owner"] = owner
            card["updated"] = _now()
            card["supersedes"] = rec.get("supersedes") or card.get("supersedes")
            card["change_count"] = int(card.get("change_count") or 0) + 1

        entry = _build_entry(rec, cid, op, owner, why, before, card, card["updated"])

        self._atomic(json.dumps({"cards": cards}, ensure_ascii=False, indent=2) + "\n")
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return {"ok": True, "change": entry, "card": card}
