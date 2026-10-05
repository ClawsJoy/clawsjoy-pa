# -*- coding: utf-8 -*-
r"""PA 收口之道（T2-刀4 · 2026-10-05 · 技术总监 f202f89）。

【本模块解决什么】件**派得出、回不来** ⇒ 立**回执面** ＋ **四段 stage 真流转** ＋ **催收循环**。

【缺之一 回执面】`POST /v9/pa/dispatch/receipt` ＋ `GET /v9/pa/dispatch/receipt?task_id=`
  · **拒未在册之 `task_id`**（册 ＝ `data/v9/pa/dispatch.jsonl`；⛔ 静默兜底）
  · 回**回执四件**：`件号 ／ 席 ／ 果 ／ 印`

【缺之二 四段之盯】`STAGES = 已派 ⇒ 已收 ⇒ 在做 ⇒ 已收口`（**每段有刻**）
  · `state(task_id)` ＝ 派生之真源：**无回执 ⇒ 已派**（派时即已派）；有 ⇒ 末次回执之段
  · **只进不退**（stage ⛔ 回退 · 承「时间不可逆」）—— 回退 ⇒ **拒**（⛔ 静默改）

【缺之三 催收】`chase(threshold_min, max_n)`：`stage != 已收口` ∧ 距末次刻 > 阈 ⇒ 催 **一次**
  · **走回执面同路之运输**（**复用** `dispatch.SeatExecutor` · ⛔ 另造）
  · **限次**（`chase_count(task_id) < max_n`；达上限 ⇒ 跳过并报「已达上限」· ⛔ 无限催）
  · 催之台账 ＝ **本模块之 `receipts.jsonl`**（`kind=chase` · 含刻／rc／件之径 ⇒ ⛔「投了不记」）

【真源与形】
  台账 `data/v9/pa/receipts.jsonl`（append-only 单行；追加后**读回校验** ⇒ 假成交必抛）
  行形：`{kind: stage|chase, task_id, to_seat, 果, 印, stage, note, by, ts, epoch, rc?, piece?}`

【红线】⛔ 代操作他方平台（upload／save／publish 恒人点）；⛔ 静默；删除须归因。
"""
import json
import os
import time
from pathlib import Path

RECEIPT_VERSION = "2026-10-05.1"

#: 四段（**序**不可逆 ⇒ 只进不退）
STAGES = ("已派", "已收", "在做", "已收口")
STAGE_ORDER = {s: i for i, s in enumerate(STAGES)}

#: 催收之默认（阈 `30` 分 · 限 `2` 次 —— 承令「⛔ 无限催」）
CHASE_AFTER_MIN = int(os.getenv("PA_CHASE_AFTER_MIN", "30"))
CHASE_MAX = int(os.getenv("PA_CHASE_MAX", "2"))
CHASE_TIMEOUT = int(os.getenv("PA_CHASE_TIMEOUT", "180"))


def _data_dir():
    return Path(os.getenv("PA_DATA_DIR", "data/v9/pa"))


def rc_path():
    return _data_dir() / "receipts.jsonl"


def dp_path():
    return Path(os.getenv("PA_DISPATCH_PATH", "data/v9/pa/dispatch.jsonl"))


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _load_rows(path):
    """单行读（坏行**计数 ＋ 报 stderr** · ⛔ 静默 · ⛔ 以坏充空）。"""
    rows, bad = [], 0
    p = Path(path)
    if not p.exists():
        return rows, bad
    import sys as _sys
    for no, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except Exception as e:
            bad += 1
            _sys.stderr.write("[receipts] %s 第 %d 行不可解析（%s）——跳过\n" % (p.name, no, type(e).__name__))
            continue
        if not isinstance(r, dict) or not str(r.get("task_id") or "").strip():
            bad += 1
            _sys.stderr.write("[receipts] %s 第 %d 行结构不符——跳过\n" % (p.name, no))
            continue
        rows.append(r)
    return rows, bad


def _append(path, row):
    """追加一行：**先自检 → 单行追加 → 读回校验**（假成交红线 ⇒ 不一致必抛）。"""
    if not isinstance(row, dict) or not str(row.get("task_id") or "").strip():
        raise ValueError("回执行须为含非空 task_id 之对象（拒写）")
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row, ensure_ascii=False)
    blob = (line + "\n").encode("utf-8")
    with open(p, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(line + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    if not p.read_bytes().endswith(blob):
        raise RuntimeError("回执追加未生效（读回不一致）：%s" % p)
    return row


# ============================ 册（在册之 task_id） ============================
def dispatch_index():
    """`dispatch.jsonl` 之索引（task_id ⇒ **末行**）。⛔ 凭印象。"""
    rows, bad = _load_rows(dp_path())
    idx = {}
    for r in rows:
        idx[str(r["task_id"])] = r
    return idx, bad


def known(task_id):
    idx, _ = dispatch_index()
    return str(task_id or "").strip() in idx


# ============================ 四段之态 ============================
def receipts_of(task_id):
    rows, _ = _load_rows(rc_path())
    t = str(task_id or "").strip()
    return [r for r in rows if str(r.get("task_id")) == t]


def state(task_id):
    """派生之真源：**无回执 ⇒ 已派**（派时即已派）＋ 四段之刻 ＋ 催之数。"""
    t = str(task_id or "").strip()
    idx, _ = dispatch_index()
    base = idx.get(t)
    rs = receipts_of(t)
    trans = [r for r in rs if r.get("kind", "stage") == "stage"]
    chases = [r for r in rs if r.get("kind") == "chase"]
    cur = "已派"
    cur_at = (base or {}).get("ts")
    for r in trans:
        s = str(r.get("stage") or "")
        if s in STAGE_ORDER and STAGE_ORDER[s] >= STAGE_ORDER.get(cur, 0):
            cur, cur_at = s, r.get("ts")
    return {
        "task_id": t, "in_registry": base is not None, "to_seat": (base or {}).get("to_seat"),
        "stage": cur, "stage_at": cur_at,
        "stage_src": ("回执" if trans else "派时"),
        "transitions": [{"stage": r.get("stage"), "at": r.get("ts"), "by": r.get("by"),
                         "果": r.get("果"), "印": r.get("印"), "note": r.get("note")} for r in trans],
        "chase_count": len(chases),
        "chases": [{"at": r.get("ts"), "rc": r.get("rc"), "piece": r.get("piece")} for r in chases],
        "last_at": (rs[-1].get("ts") if rs else (base or {}).get("ts")),
        "注": "无回执 ⇒ 已派（派时即已派）· 只进不退",
    }


def states_all():
    idx, _ = dispatch_index()
    return {t: state(t) for t in idx}


def overlay_history(rows):
    """给 `dispatch/history` 之行**补四段之 stage**（＋ `stage_src`）⇒ 盯得住。

    ⛔ 破既有键之外形：`stage` **按四段真走**（承刀4 缺之二）；另加 `stage_src` 载其据。
    """
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        try:
            st = state(r.get("task_id"))
        except Exception:
            continue
        r["stage"] = st["stage"]
        r["stage_at"] = st["stage_at"]
        r["stage_src"] = st["stage_src"]
        r["chase_count"] = st["chase_count"]
    return rows


# ============================ 回执（收） ============================
def record(task_id, to_seat="", 果="", 印="", stage="已收", note="", by=""):
    """收一次回执（**拒未在册** · ⛔ 静默兜底 · ⛔ 回退）。"""
    t = str(task_id or "").strip()
    if not t:
        return {"ok": False, "error": "task_id 空 ⇒ 拒收（⛔ 静默兜底）"}
    idx, bad = dispatch_index()
    base = idx.get(t)
    if base is None:
        return {"ok": False, "task_id": t, "error":
                "⛔ **未在册之 task_id ⇒ 拒收**：%s（册 ＝ `data/v9/pa/dispatch.jsonl` · 现 %d 张 · 坏行 %d）"
                % (t, len(idx), bad)}
    s = str(stage or "").strip()
    if s not in STAGE_ORDER:
        return {"ok": False, "task_id": t, "error": "stage 须 ∈ %s（收 `%s`）" % ("／".join(STAGES), s)}
    seat_row = str(base.get("to_seat") or "").strip()
    seat_in = str(to_seat or "").strip()
    if seat_row and seat_in and seat_row != seat_in:
        return {"ok": False, "task_id": t, "to_seat": seat_in,
                "error": "**席不符**：册载 `%s` · 回执称 `%s` ⇒ 拒收（⛔ 静默兜底）" % (seat_row, seat_in)}
    cur = state(t)
    if STAGE_ORDER[s] < STAGE_ORDER.get(cur["stage"], 0):
        return {"ok": False, "task_id": t, "stage": cur["stage"],
                "error": "**回退**：现 `%s` ⇒ 收 `%s` 为退（四段只进不退 · ⛔ 静默改）" % (cur["stage"], s)}
    row = {"kind": "stage", "task_id": t, "to_seat": seat_in or seat_row, "果": str(果 or "")[:2000],
           "印": str(印 or ""), "stage": s, "note": str(note or "")[:1000], "by": str(by or ""),
           "ts": _now(), "epoch": time.time()}
    try:
        _append(rc_path(), row)
    except Exception as e:
        return {"ok": False, "task_id": t, "error": "回执落账失败（⛔ 静默）：%s" % type(e).__name__}
    st = state(t)
    quad = {"件号": t, "席": st.get("to_seat"), "果": row["果"], "印": row["印"] or None}
    return {"ok": True, "task_id": t, "stage": st["stage"], "stage_at": st["stage_at"],
            "回执四件": quad, "四件齐": all(quad[k] not in (None, "") for k in quad),
            "state": st}


# ============================ 催（收之缺） ============================
def _chase_piece(task_id, to_seat, stage, age_min, n, max_n):
    return ("---\ntype: 催收\nfrom: PA（V9 · /v9/pa/dispatch/chase）\nto_seat: %s\ntask_id: %s\nat: %s\n---\n\n"
            "## 一 为何催\n\n件 `%s` 之 `stage` 仍为 **%s**（距末次刻约 **%.1f 分** > 阈）⇒ 请回执。\n\n"
            "## 二 怎么回\n\n`POST /v9/pa/dispatch/receipt {task_id, to_seat, 果, 印, stage, note}`\n"
            "四段 ＝ 已派 ⇒ 已收 ⇒ 在做 ⇒ 已收口（每段有刻）。\n\n"
            "## 三 本催之限\n\n这是第 **%d/%d** 次催（达上限即停 · ⛔ 无限催）。\n"
            "⛔ 平台动作（upload／save／publish 恒人点）。\n") % (
        to_seat, task_id, _now(), task_id, stage, age_min, n, max_n)


def chase(threshold_min=None, max_n=None, dry=False):
    """催收一轮：`stage != 已收口` ∧ 超阈 ⇒ 催一次（**限次** · 同路运输）。"""
    thr = CHASE_AFTER_MIN if threshold_min is None else float(threshold_min)
    mx = CHASE_MAX if max_n is None else int(max_n)
    now = time.time()
    cands, chased, skipped = [], [], []
    for t, st in sorted(states_all().items()):
        if st["stage"] == "已收口":
            continue
        if not st.get("to_seat"):
            continue
        ref = st.get("last_at") or st.get("stage_at")
        age = None
        if ref:
            try:
                age = (now - time.mktime(time.strptime(ref, "%Y-%m-%d %H:%M:%S"))) / 60.0
            except Exception:
                age = None
        cands.append({"task_id": t, "to_seat": st["to_seat"], "stage": st["stage"],
                      "age_min": (round(age, 1) if age is not None else None)})
        if age is None:
            skipped.append({"task_id": t, "why": "无刻可算 ⇒ 不催（⛔ 以缺充足）"})
            continue
        if age <= thr:
            skipped.append({"task_id": t, "why": "未超阈（%.1f ≤ %s 分）" % (age, thr)})
            continue
        if st["chase_count"] >= mx:
            skipped.append({"task_id": t, "why": "**已达上限**（%d/%d）⇒ 停催" % (st["chase_count"], mx)})
            continue
        if dry:
            skipped.append({"task_id": t, "why": "dry-run（⛔ 未真催）"})
            continue
        from core.pa.dispatch import SeatExecutor, make_contract

        seat = st["to_seat"]
        text = _chase_piece(t, seat, st["stage"], age, st["chase_count"] + 1, mx)
        c = make_contract(text, to_seat=seat)
        c["task_id"] = "chase_%s_%d" % (t, int(now))
        try:
            r = SeatExecutor(seat, timeout=CHASE_TIMEOUT).run(c)
        except Exception as e:
            skipped.append({"task_id": t, "why": "催之投递未起（%s）" % type(e).__name__})
            continue
        try:
            _append(rc_path(), {"kind": "chase", "task_id": t, "to_seat": seat,
                                "果": "", "印": "", "stage": st["stage"],
                                "note": "催 %d/%d" % (st["chase_count"] + 1, mx),
                                "by": "PA(chase)", "ts": _now(), "epoch": time.time(),
                                "rc": r.get("rc"), "piece": r.get("artifact"),
                                "n": st["chase_count"] + 1})
        except Exception as e:
            skipped.append({"task_id": t, "why": "催已投而未落账（⛔ 静默）：%s" % type(e).__name__})
            continue
        chased.append({"task_id": t, "to_seat": seat, "stage": st["stage"], "age_min": round(age, 1),
                       "n": st["chase_count"] + 1, "rc": r.get("rc"), "piece": r.get("artifact"),
                       "stage_now": r.get("stage")})
    return {"ok": True, "at": _now(), "threshold_min": thr, "max_n": mx, "dry": bool(dry),
            "candidates": cands, "chased": chased, "skipped": skipped,
            "counts": {"candidates": len(cands), "chased": len(chased), "skipped": len(skipped)},
            "store": str(rc_path())}


def face(task_id=None, limit=50):
    """只读面：`task_id` 给 ⇒ 该件之四段；不给 ⇒ 全表之态。"""
    rows, bad = _load_rows(rc_path())
    idx, dbad = dispatch_index()
    if task_id:
        st = state(task_id)
        return {"at": _now(), "version": RECEIPT_VERSION, "task_id": str(task_id),
                "in_registry": st["in_registry"], "state": st,
                "receipts": receipts_of(task_id)[-limit:],
                "store": str(rc_path()), "store_exists": rc_path().is_file(),
                "bad_lines": bad, "registry_count": len(idx), "registry_bad": dbad,
                "stages": list(STAGES),
                "verdict": ("在册" if st["in_registry"] else "⛔ **不在册**（册 ＝ dispatch.jsonl）")}
    sts = sorted(states_all().values(), key=lambda x: str(x.get("last_at") or ""), reverse=True)
    return {"at": _now(), "version": RECEIPT_VERSION, "count": len(sts), "states": sts[:limit],
            "by_stage": {s: len([x for x in sts if x["stage"] == s]) for s in STAGES},
            "store": str(rc_path()), "store_exists": rc_path().is_file(),
            "bad_lines": bad, "registry_count": len(idx), "registry_bad": dbad,
            "stages": list(STAGES), "chase_policy": {"after_min": CHASE_AFTER_MIN, "max": CHASE_MAX}}