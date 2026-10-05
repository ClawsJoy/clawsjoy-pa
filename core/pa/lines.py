# -*- coding: utf-8 -*-
r"""PA 产品线模型（T2-刀4 缺之四 · 2026-10-05 · 技术总监 f202f89）。

【本模块解决什么】`ledger` 唯**散待办**（一条一条）⇒ 老板问「**未完成的产品线**」**无对象**。
⇒ 立 `product_line = {线名, 席, 件集[], 状态, 下一拍}` ＋ 面 `GET /v9/pa/lines`。

【真源（⛔ 自造 ／ ⛔ 凭印象）】
  · `data/v9/pa/dispatch.jsonl` 之**席轴行**（含 `to_seat`）＋ `core.pa.receipts` 之四段态
    ⇒ **一条线 ＝ 一个受件之席**（席 ＝ 线之执行面）；线名取**席位册**之「归口」（⛔ 猜）
  · 可选**落件** `data/v9/pa/lines.json`（人手补之名／下一拍；⛔ 覆派生之数）

【判据（刀4 §五.5）】`GET /v9/pa/lines` 出 **≥1** 条**真线**。
"""
import json
import os
import time
from pathlib import Path

LINES_VERSION = "2026-10-05.1"
DEFAULT_THRESHOLD_MIN = int(os.getenv("PA_CHASE_AFTER_MIN", "30"))


def _data_dir():
    return Path(os.getenv("PA_DATA_DIR", "data/v9/pa"))


def lines_path():
    return _data_dir() / "lines.json"


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _seat_titles():
    """席位册之「归口」（⛔ 硬编 · ⛔ 猜）。"""
    try:
        from core.pa import roster as R
        return {str(s.get("id")): ((s.get("governance") or {}).get("归口") or s.get("name") or "")
                for s in R.seats()}
    except Exception:
        return {}


def load_overlay():
    """人手补之落件（线名／下一拍／额外件集）。⛔ 覆派生之数 —— 唯**补**。"""
    p = lines_path()
    if not p.exists():
        return {}
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out = {}
    for ln in (doc.get("lines") or []):
        if isinstance(ln, dict) and ln.get("线名"):
            out[str(ln["线名"])] = ln
    return out


def save_overlay(doc):
    p = lines_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(doc, ensure_ascii=False, indent=2).encode("utf-8")
    tmp = str(p) + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(payload)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, str(p))
    return {"path": str(p), "sha16": __import__("hashlib").sha256(payload).hexdigest()[:16]}


def upsert(line):
    """补一条线之**人手认识**（线名 ／ 下一拍 ／ 备注）；⛔ 覆派生之件集与状态。"""
    if not isinstance(line, dict) or not str(line.get("线名") or "").strip():
        return {"ok": False, "error": "线需要非空「线名」"}
    p = lines_path()
    try:
        doc = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"version": 1, "lines": []}
    except Exception:
        doc = {"version": 1, "lines": []}
    rows = doc.setdefault("lines", [])
    for i, r in enumerate(rows):
        if str(r.get("线名")) == str(line["线名"]):
            merged = dict(r)
            merged.update({k: v for k, v in line.items() if v is not None})
            rows[i] = merged
            break
    else:
        rows.append(dict(line))
    doc["updated"] = _now()
    info = save_overlay(doc)
    return {"ok": True, "线名": line["线名"], **info}


def derive(threshold_min=None):
    """**派生**之线（一条 ＝ 一个受件之席）。⛔ 起停 ／ ⛔ 网。"""
    thr = DEFAULT_THRESHOLD_MIN if threshold_min is None else float(threshold_min)
    from core.pa import receipts as RC

    idx, dbad = RC.dispatch_index()
    states = {t: RC.state(t) for t in idx}
    titles = _seat_titles()
    by_seat = {}
    for t, st in states.items():
        seat = str(st.get("to_seat") or "").strip()
        if not seat:
            continue
        by_seat.setdefault(seat, []).append(st)

    now = time.time()
    rows = []
    for seat, items in sorted(by_seat.items()):
        open_items = [x for x in items if x["stage"] != "已收口"]
        closed = [x for x in items if x["stage"] == "已收口"]
        ages = []
        for x in open_items:
            ref = x.get("last_at") or x.get("stage_at")
            try:
                ages.append((now - time.mktime(time.strptime(ref, "%Y-%m-%d %H:%M:%S"))) / 60.0)
            except Exception:
                pass
        over = [a for a in ages if a > thr]
        if not open_items:
            状态, 下一拍 = "已收口", "无（全收口）"
        elif over:
            状态, 下一拍 = "未收口", "**催收**（超阈 %.1f 分 > %s 分 ⇒ `POST /v9/pa/dispatch/chase`）" % (max(over), thr)
        else:
            状态, 下一拍 = "未收口", "候回执（未超阈）"
        线名 = titles.get(seat) or ("席 %s" % seat)
        row = {
            "线名": 线名, "席": seat,
            "件集": [{"件号": x["task_id"], "stage": x["stage"], "刻": x.get("last_at"),
                      "催": x.get("chase_count", 0)} for x in sorted(items, key=lambda y: str(y.get("last_at") or ""))],
            "状态": 状态, "下一拍": 下一拍,
            "未收口": len(open_items), "已收口": len(closed),
            "最近刻": max([str(x.get("last_at") or "") for x in items] or [""]),
            "源": "dispatch.jsonl × receipts.jsonl",
        }
        rows.append(row)
    派生坏行 = dbad
    return rows, 派生坏行


def face(threshold_min=None, include_overlay=True):
    """`GET /v9/pa/lines` —— **产品线**之面（≥1 条真线 ⇒ 方有对象可问）。"""
    rows, dbad = derive(threshold_min)
    over = load_overlay() if include_overlay else {}
    seen = set()
    for r in rows:
        seen.add(r["线名"])
        o = over.get(r["线名"]) or {}
        if o.get("下一拍"):
            r["下一拍"] = str(o["下一拍"])
            r["下一拍源"] = "人手"
    extra = []
    if include_overlay:
        for name, o in over.items():
            if name in seen:
                continue
            extra.append({"线名": name, "席": o.get("席"), "件集": o.get("件集") or [],
                          "状态": o.get("状态") or "未明（人手之线 · ⛔ 派生表无据）",
                          "下一拍": o.get("下一拍") or "未明", "未收口": None, "已收口": None,
                          "最近刻": None, "源": "lines.json（人手）"})
    rows.extend(extra)
    return {"at": _now(), "version": LINES_VERSION, "count": len(rows),
            "lines": rows,
            "counts": {"线": len(rows), "未收口": len([r for r in rows if r.get("状态") == "未收口"]),
                       "已收口": len([r for r in rows if r.get("状态") == "已收口"])},
            "source": {"派生": str(_data_dir() / "dispatch.jsonl") + " × " + str(_data_dir() / "receipts.jsonl"),
                       "人手": str(lines_path())},
            "面之径逐字": "派生 ＝ " + str(_data_dir() / "dispatch.jsonl") + " × " + str(_data_dir() / "receipts.jsonl") + " ／ 人手 ＝ " + str(lines_path()),
            "刻之性": "读时（活面：本面逐次读 dispatch.jsonl ／ receipts.jsonl ／ lines.json ⇒ 数随刻变 · ⛔ 冻结面）",
            "bad_lines": dbad,
            "note": "一条线 ＝ 一个**受件之席**（席 ＝ 线之执行面）；线名取席位册「归口」（⛔ 猜）",
            "shape": {"product_line": ["线名", "席", "件集", "状态", "下一拍"]}}