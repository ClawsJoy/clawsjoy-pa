# -*- coding: utf-8 -*-
u"""更新之「跑」之态（**一处定形** · 与「根」绑定）—— 承 pm_1684 §四 契约（TD f202f89 · 2026-10-07）。

病（为何另立）：`POST /v9/pa/update` 起器（`scripts/win_pa/pa_update.py`）；器之第 ⑥⑧ 步
  **先停后换 ⇒ 再起** ⇒ **应答之服（网关）自停** ⇒ 端之「phase」**⛔ 可于其进程内**察终态。
  ⇒ 态须**落盘**（跨重启可读）∧ **与根绑定**（二根 ⛔ 互覆）—— 与 `update_check` 之态同处同族。
  ⚠ 承 `pm_1659 §二.1`（跨根污染）：`%LOCALAPPDATA%\\ClawsJoyPA\\update` 可为一机众根共处
     ⇒ 件名带「根之印」＋ 态中记 `root` ∧ 读时校（不符 ⇒ 视为无效 ⇒ 未跑）。

形（一处定形）＝ `FIELDS`：
  phase ∈ idle ／ running ／ **restart** ／ done ／ failed
    ⚠ `idle` 为本席之补：pm_1684 §四.1 之枚举唯三（running ／ done ／ failed），
      然「未曾跑」须有一值 —— 承「空 ⛔ 混 缺」⇒ 明书「未跑」，⛔ 充「成」。
    ⭐ `restart` 为 pm_1790 §二.2 之补（2026-10-08）：「停 → 换 → 起」之窗内，应答之服
      **已死** ⇒ 该相位**须落盘**方得跨进程可察（否则面**无从**显「正在重启」）。
  started_at ／ ended_at ／ from ／ to ／ note ／ note_why ／ files ／ root。

落处 ＝ `%LOCALAPPDATA%\\ClawsJoyPA\\update\\run-<根之印>.json`（与 `state-<根之印>.json` 同处）。
写方 ＝ 器（`pa_update.py` —— **唯器知情**：起 ⇒ running；终 ⇒ done ／ failed）；
读者 ＝ 端（`core/pa/gateway_routes.py::pa_update_run`）＋ 齿。

以何形调用（判通 ／ 断须附）：
  python -X utf8 -B -m pytest tests/unit/test_v9_pa_update_1684.py -q
"""
from __future__ import annotations

import io
import json
import os
import time

from core.lib import update_check as UC

#: 态之件名之干（一处定形）：`run-<根之印>.json`
STATE_STEM = u"run"
#: 相位之枚举（一处定形）
#:   ⭐ `restart`（pm_1790 §二.2）：器「停之前」落之（`restart()`）—— 由：停后服即死，
#:     该相位唯**落盘**方得跨进程可察（⛔ 唯内存）。
PHASES = (u"idle", u"running", u"restart", u"done", u"failed")
#: 「running」之陈阈（秒）—— 逾此而犹 running ⇒ 视「中断之未终」
#:   （承「取不得 ⛔ 充已知」：中断 ⇒ 明书 failed，⛔ 长挂 running 而面恒转）
STALE_S = 1800.0
#: 逐键（一处定形）—— 写读二方同此表
FIELDS = (u"phase", u"started_at", u"ended_at", u"from", u"to", u"note", u"note_why",
          u"files", u"root")


def state_name(root=None):
    u"""态之件名（一处定形）：`run-<根之印>.json`（二根 ⇒ 二件 ⇒ ⛔ 互覆）。"""
    return STATE_STEM + u"-" + UC.root_key(root) + u".json"


def state_path(root=None, env=None):
    u"""态之径（一处定形）：`update_check.out_dir()` ⊕ `state_name(root)`（同一夹 · 一处出）。"""
    return os.path.join(UC.out_dir(root, env), state_name(root))


def _read(root=None, env=None):
    u"""读态 ⇒ `dict | None`；未见 ／ 坏 ／ 根 ⛔ 符 ⇒ `None`（视为「未跑」）。"""
    p = state_path(root, env)
    try:
        with io.open(p, encoding=u"utf-8-sig") as fh:
            d = json.loads(fh.read())
    except Exception:                                         # noqa: BLE001 — 未见 ／ 坏 ⇒ 未跑
        return None
    if not isinstance(d, dict):
        return None
    r = d.get(u"root")
    if r and str(r) != UC.root_of(root):                      # 根不符 ⇒ 视为无效
        return None
    return d


def write(doc, root=None, env=None):
    u"""落态（**原子** —— 同卷 `os.replace`）⇒ `(径, note)`；⛔ 成 ⇒ 照实报（⛔ 抛）。"""
    p = state_path(root, env)
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = p + u".new"
        with io.open(tmp, u"w", encoding=u"utf-8", newline=u"") as fh:
            fh.write(json.dumps(doc, ensure_ascii=False, indent=1))
        os.replace(tmp, p)
        return p, u""
    except Exception as e:                                    # noqa: BLE001 — 照实报因
        return p, u"%s: %s" % (type(e).__name__, e)


def _now():
    return time.strftime(u"%Y-%m-%dT%H:%M:%S%z", time.localtime())


def _epoch(ts):
    u"""`"%Y-%m-%dT%H:%M:%S%z"` 之刻 ⇒ epoch（截前十九字 · 本地时区自洽）；⛔ 解 ⇒ `None`。"""
    if not ts:
        return None
    try:
        return time.mktime(time.strptime(str(ts)[:19], u"%Y-%m-%dT%H:%M:%S"))
    except Exception:                                         # noqa: BLE001 — 照实续
        return None


def _version(root=None):
    u"""今之版：装根 `version.json` 优先 ⇒ 回落 `core/lib/version.py` —— ⛔ 猜（取不得 ⇒ None）。"""
    try:
        from core.lib import build_info as BI
        v = (BI.read(root)[0] or {}).get(u"version")
        if v:
            return str(v)
    except Exception:                                         # noqa: BLE001 — 照实续
        pass
    try:
        from core.lib.version import __version__ as _v
        return str(_v)
    except Exception:                                         # noqa: BLE001 — 照实续
        return None


def begin(root=None, from_version=None, env=None):
    u"""器之起：落 `running`（`from` ＝ 今之版）⇒ `(径, note)`。

    ⭐ **幂等**（pm_1790 §二.3）：本函**二处**皆调 —— 端（`POST /v9/pa/update` · 起器之前）
      与器（`pa_update.main` · 起之后）。昔器再调 ⇒ **覆** `from` ／ `started_at` ⇒
      「起时 `from=9.0.4`、终态 `from=9.0.6`（＝ `to`）」之**不可考**（病之实：器之
      `_version(root)` 读**新盘** ⇒ 起讫二刻同名）。
      ⇒ 今：**已在跑（`running` ／ `restart` ∧ ⛔ 陈）⇒ 唯更相位为 `running`，
      ⛔ 动 `from` ／ `started_at`**（承 §二.3「`from` 须起时定死」）。
    """
    prev = _read(root, env) or {}
    ph = str(prev.get(u"phase") or u"")
    if ph in (u"running", u"restart"):
        ts = _epoch(prev.get(u"started_at"))
        if ts is not None and (time.time() - ts) <= STALE_S:
            doc = dict(prev)
            doc[u"phase"] = u"running"
            if not doc.get(u"from") and from_version is not None:
                doc[u"from"] = from_version
            doc[u"root"] = UC.root_of(root)
            return write(doc, root, env)
    doc = {u"phase": u"running", u"started_at": _now(), u"ended_at": None,
           u"from": from_version if from_version is not None else _version(root),
           u"to": None, u"note": u"更新中", u"note_why": u"", u"files": None,
           u"root": UC.root_of(root)}
    return write(doc, root, env)


def restart(root=None, to_version=None, note=None, env=None):
    u"""器之「**停前**」之相位：落 `restart` ⇒ `(径, note)`（pm_1790 §二.2）。

    由（一手之病 · 老板所见「版本更新无效」）：`restart` 之相位昔**唯在器之内存** ⇒
      器第 ⑥ 步停网关 ⇒ 应答之服**即死** ⇒ 面（`POST /v9/pa/update` 之 `action:status`）
      **无从**问 ⇒ 那约 40 s 之空窗，面唯能显「更新面未答」。
    ⇒ **停之前先落盘**（`restart` ＋ `from` ／ `to` ／ `started_at`）⇒ 新进程起后**续读**之
      ⇒ 相位**跨进程可察** ⇒ 面方得显「正在重启（已等 Ns）」。

    ⚠ `started_at` ／ `from` **沿用起态**（⛔ 覆 —— 承 §二.3「起时定死」）；`to` 唯在
      显式给时落（＝ 清单之版 · 起讫可考）。
    """
    d = _read(root, env) or {}
    doc = dict(d)
    if not doc.get(u"started_at"):
        doc[u"started_at"] = _now()
    if not doc.get(u"from"):
        doc[u"from"] = _version(root)
    if to_version is not None:
        doc[u"to"] = to_version
    doc[u"phase"] = u"restart"
    doc[u"ended_at"] = None
    doc[u"note"] = note or (u"更新已就位 · 正在重启服务（%s ⇒ %s）"
                            % (doc.get(u"from") or u"（旧包）", doc.get(u"to") or u"?"))
    doc[u"root"] = UC.root_of(root)
    return write(doc, root, env)


def finish(root=None, rc=0, note=None, note_why=u"", to_version=None, env=None):
    u"""器之终：落 `done`（rc==0）／ `failed`（余）＋ `to`（今之版）⇒ `(径, note)`。"""
    d = _read(root, env) or {}
    frm = d.get(u"from")
    # ⭐ pm_1790 §二.3：`to` 若已定（起态之 `restart()` 所落 ＝ 清单之版）⇒ **沿用**
    #   （⛔ 以今之盘号覆之 —— 与 `from` 同理：一旦定死，终态 ⛔ 改）。
    to = to_version if to_version is not None else (d.get(u"to") or _version(root))
    ph = u"done" if int(rc) == 0 else u"failed"
    if note is None:
        if int(rc) == 0:
            note = (u"已是最新（%s）" % to) if (frm and to and str(frm) == str(to)) \
                else (u"完成：%s ⇒ %s" % (frm or u"（旧包）", to or u"?"))
        else:
            note = u"未成（rc=%d）—— 若已动盘 ⇒ 器已回滚至 %s" % (int(rc), frm or u"原态")
    doc = dict(d)
    doc.update({u"phase": ph, u"ended_at": _now(), u"to": to, u"note": note,
                u"note_why": note_why or u"", u"root": UC.root_of(root)})
    return write(doc, root, env)


def clear(root=None, env=None):
    u"""清态（复为「未跑」）—— 唯齿用（⛔ 端 ／ 器）。"""
    p = state_path(root, env)
    try:
        os.remove(p)
    except OSError:
        pass
    return p


def phase(root=None, env=None, now=None):
    u"""端之报体（**纯读** —— 唯读盘之态 · ⛔ 出网）：`{ok, phase, note, note_why, …}`。

    「未曾跑」⇒ `phase="idle"`（明书「未跑」，⛔ 充「成」）；
    「running」而逾 `STALE_S` ⇒ 报 `failed`（明书「疑中断」—— 承「取不得 ⛔ 充已知」）。
    """
    d = _read(root, env)
    out = {"ok": True, "phase": u"idle", "note": u"未跑（本机未曾起更新）", "note_why": u"",
           "started_at": None, "ended_at": None, "from": None, "to": None, "files": None}
    if not d:
        return out
    ph = str(d.get(u"phase") or u"idle")
    out[u"phase"] = ph if ph in PHASES else u"idle"
    for k in (u"started_at", u"ended_at", u"from", u"to", u"files"):
        out[k] = d.get(k)
    out[u"note"] = d.get(u"note") or u""
    out[u"note_why"] = d.get(u"note_why") or u""
    # ⭐ `restart` 亦须罩陈阈（pm_1790 §二.2）：⛔ 长挂「正在重启」而面恒转。
    if out[u"phase"] in (u"running", u"restart"):
        ts = _epoch(d.get(u"started_at"))
        t = time.time() if now is None else float(now)
        if ts is not None and (t - ts) > STALE_S:
            out[u"phase"] = u"failed"
            out[u"note"] = u"更新中断（逾 %.0f s 未见终态）—— 请复看 ／ 重试" % STALE_S
            out[u"note_why"] = u"stale"
    return out
