# -*- coding: utf-8 -*-
u"""/health `update` 键之读数（**一处定形**）—— 承 pm_1640 §一.4 ＋ pm_1645 §二.1⒞
（技术总监席 f202f89 · 2026-10-07）。

律（承 pm_1640 §一.2「**读一处（/health）· 动分端（/v9/pa/*）**」）：
  ⒜ **`update` 之读数唯出 `/health`**（⛔ 新端）；
  ⒝ `/health` ＝ **只读之窗** ⇒ ⛔ 于其内出网 ∧ ⛔ 阻塞 ⇒ 本模块之态**落盘**
     （`state.json`），`face()` 唯**读文件**（数十字节之读）；
  ⒞ 刷新（出网）**唯二处调**：① 起服门后之守护（`start_periodic` —— 即刻一次 ＋ 每 `REFRESH_S`）
    ② 甲-P0 之器（`refresh` —— `scripts/win_pa/pa_update.py` 之流程内同步取一次）。

态（`face()` 之形 · 三态 ＋ 未查）：
  未查    ⇒ `{available: false, channel, manifest_url, note: "未查（起服门后自之）", note_why: ""}`
  取不得  ⇒ `{available: false, …, note: <人话>, note_why: <技术因>}`（承 `boot.download` 之族）
  已是最新 ⇒ `{available: false, current_version, latest_version, size_bytes, files, channel, checked_at, note: "已是最新"}`
  有新版  ⇒ `{available: true, …同上…, note: ""}`
  ⭐ 同版号之重发（pm_1848 §三.3）⇒ `{available: true, …, note: "有同版号之新册（重发）：<版> ｜ 戳 <装根> ⇒ <册>"}`
     —— 由：版号同 ≠ 物同；旧判唯比版号 ⇒ 重发被误书「已是最新」⇒ 页内之路**永不可达**。
     判据 ＝ 装根 `version.json` 之 `built_at` ⟷ 册之 `built_at`（戳**同** ⇒ 已是最新）。

⚠ 落处 ＝ `%LOCALAPPDATA%\\ClawsJoyPA\\update\\state-<根之印>.json`（与 `diagnostics.out_root` 同族）
  ⇒ **⛔ 入装根之 `data/`**（承 pm_1620 §三.8 之铁律：升级 ⛔ 动 `data/` —— 其印 ⛔ 变）。
⭐ **态与「根」绑定**（承 pm_1659 §二.1 —— 跨根污染 · CW 一手）：
  **按根分片**（件名带根之印 ⇒ 二根 ⛔ 互覆）∧ 态中记 `root` ∧ 读时以「今之根」校之
  （不符 ⇒ 视为无效 ⇒ 未查 ⇒ 重探）。由：沙箱 ／ 器 ／ 活端可共处同一 `LOCALAPPDATA`
  ⇒ 一文件 ⇒ 沙箱之探覆活端之态 ⇒ 活端渲「已是最新」＝「未知 ⛔ 充知」之面形。

以何形调用（判通 ／ 断须附）：
  python -X utf8 -B -m pytest tests/unit/test_win_pa_update_1645.py -q
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import threading
import time

from core.lib import build_info as BI
from core.lib import update_manifest as UM
from core.lib import update_source as US

#: 态之件名之干（**一处定形** · pm_1659 §二.1）：`state-<根之印>.json`
STATE_STEM = u"state"
#: 旧形（无根之绑）—— **⛔ 读**（免跨根之误）：CW_1663 一手之「污」即落此件。
LEGACY_STATE = u"state.json"
#: 守护之周（秒）—— 内测之节奏（面之轮询为 30 s ⇒ 此周够鲜 ∧ 出网够疏）
REFRESH_S = 300.0
_boot_lock = threading.Lock()
_started = False


def root_of(root=None):
    u"""今之根（**一处定形**）—— 规范化之绝对径（大小写 ／ 斜杠归一）⇒ ⛔ 空。"""
    return os.path.abspath(os.path.normcase(str(root or US.root_dir())))


def root_key(root=None):
    u"""根之印（**一处定形**）—— `root_of` 之 sha256 前 16 hex ⇒ 态之件名之凭。"""
    return hashlib.sha256(root_of(root).encode(u"utf-8")).hexdigest()[:16]


def state_name(root=None):
    u"""态之件名（**一处定形**）—— `state-<根之印>.json`（二根 ⇒ 二件 ⇒ ⛔ 互覆）。"""
    return STATE_STEM + u"-" + root_key(root) + u".json"


def out_dir(root=None, env=None):
    u"""态之落处（**一处定形**）：`%LOCALAPPDATA%\\ClawsJoyPA\\update`；无 ⇒ `<装根>/data/pa/update`。"""
    env = os.environ if env is None else env
    la = (env.get(u"LOCALAPPDATA") or u"").strip()
    if la:
        return os.path.join(la, u"ClawsJoyPA", u"update")
    return os.path.join(root or US.root_dir(), u"data", u"pa", u"update")


def state_path(root=None, env=None):
    u"""态之径（**一处定形**）：`out_dir()` ⊕ `state_name(root)`。"""
    return os.path.join(out_dir(root, env), state_name(root))


def _read_state(root=None, env=None):
    p = state_path(root, env)
    try:
        with io.open(p, encoding=u"utf-8-sig") as fh:
            d = json.loads(fh.read())
    except Exception:                                         # noqa: BLE001 — 未见 ／ 坏 ⇒ 未查
        return None
    if not isinstance(d, dict):
        return None
    r = d.get(u"root")
    if r and str(r) != root_of(root):                         # 根不符 ⇒ 视为无效
        return None
    return d


def _write_state(doc, root=None, env=None):
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


def face(root=None, env=None):
    u"""`/health.update` 之体（**纯读** —— 唯读盘之态 ＋ 源之声明 · ⛔ 出网）。"""
    env = os.environ if env is None else env
    src = US.load(root, env)
    _curd = BI.read(root)[0] or {}
    base = {"channel": src.get(u"channel"), "manifest_url": US.manifest_url(src),
            "current_version": _curd.get(u"version"),
            "current_built_at": _curd.get(u"built_at")}
    d = _read_state(root, env)
    if not d:
        base.update({"available": False, "latest_version": None, "latest_built_at": None,
                     "size_bytes": 0, "files": 0,
                     "checked_at": None, "note": u"未查（起服门后自之 ∨ 候甲-P0 之器）",
                     "note_why": u""})
        return base
    out = dict(base)
    for k in (u"available", u"latest_version", u"latest_built_at", u"size_bytes", u"files",
              u"checked_at", u"note", u"note_why"):
        out[k] = d.get(k)
    for k in (u"channel", u"manifest_url"):
        if d.get(k):
            out[k] = d[k]
    out[u"available"] = bool(out.get(u"available"))
    if out[u"available"] and _is_downgrade(out.get(u"current_version"), out.get(u"latest_version")):
        out[u"available"] = False
        out[u"note"] = u"已是最新"
        out[u"note_why"] = (u"source-old: 源端 %s 旧于本机 %s ⇒ 不降级"
                             % (out.get(u"latest_version"), out.get(u"current_version")))
    out[u"note"] = out.get(u"note") or u""
    out[u"note_why"] = out.get(u"note_why") or u""
    out[u"size_bytes"] = out.get(u"size_bytes") if isinstance(out.get(u"size_bytes"), int) else 0
    out[u"files"] = out.get(u"files") if isinstance(out.get(u"files"), int) else 0
    return out


def _version_key(v):
    u"""版号之比较键：数字段元组（`<major>.<minor>.<patch>` ⇒ `(major, minor, patch)`）；不可解 ⇒ `()`。"""
    parts = re.findall(r"\d+", str(v or ""))
    return tuple(int(x) for x in parts) if parts else ()


def _is_downgrade(current, latest):
    u"""`latest` 旧于 `current` ⇒ True（⛔ 以旧册充「更新」）。"""
    ck, lk = _version_key(current), _version_key(latest)
    return bool(ck and lk and lk < ck)


def refresh(root=None, env=None, timeout=None, now=None):
    u"""取一次清单 ⇒ 立态 ⇒ `face()`（**同步** —— ⛔ 抛）。器用 ／ 守护用。"""
    env = os.environ if env is None else env
    src = US.load(root, env)
    doc, note, why = UM.fetch(src, timeout=timeout or UM.FETCH_TIMEOUT)
    _curd = BI.read(root)[0] or {}
    cur = _curd.get(u"version")
    cur_stamp = _curd.get(u"built_at")
    d = {"checked_at": time.strftime(u"%Y-%m-%dT%H:%M:%S%z", time.localtime(now)) if now
         else time.strftime(u"%Y-%m-%dT%H:%M:%S%z"),
         "channel": src.get(u"channel"), "manifest_url": US.manifest_url(src),
         "current_version": cur, "current_built_at": cur_stamp,
         "latest_version": None, "latest_built_at": None, "size_bytes": 0, "files": 0,
         "available": False, "note": u"", "note_why": u""}
    d[u"root"] = root_of(root)
    if doc is None:
        d["note"] = note
        d["note_why"] = why
    else:
        t = UM.totals(doc)
        d["latest_version"] = doc.get(u"version")
        d["latest_built_at"] = doc.get(u"built_at")
        d["files"] = t["n"]
        d["size_bytes"] = t["bytes"]
        if doc.get(u"channel") != src.get(u"channel"):
            d["note"] = (u"清单之通道（%s）≠ 本机之通道（%s）⇒ 拒（⛔ 跨档）"
                         % (doc.get(u"channel"), src.get(u"channel")))
            d["note_why"] = u"channel"
        elif cur and str(cur) == str(doc.get(u"version")):
            # ⭐ pm_1848 §三.3：**同版号 ∧ 戳 ⛔ 同 ⇒ 重发** ⇒ available 须真
            #   （⛔ 以「available false」令页内之路**永不可达** —— 旧病）。
            doc_stamp = str(doc.get(u"built_at") or u"")
            if str(cur_stamp or u"") and doc_stamp and str(cur_stamp) == doc_stamp:
                d["note"] = u"已是最新"
            else:
                d["available"] = True
                d["note"] = (u"有同版号之新册（重发）：%s ｜ 戳 %s ⇒ %s"
                             % (cur, cur_stamp or u"⛔ 读", doc_stamp or u"⛔ 读"))
        elif _is_downgrade(cur, doc.get(u"version")):
            d["available"] = False
            d["note"] = u"已是最新"
            d["note_why"] = (u"source-old: 源端 %s 旧于本机 %s ⇒ 不降级"
                              % (doc.get(u"version"), cur))
        else:
            d["available"] = True
            d["note"] = u"" if cur else u"有新版（本机之版号 ⛔ 读 ⇒ 照实）"
    _p, wnote = _write_state(d, root, env)
    if wnote and not d["note"]:
        d["note"] = u"态 ⛔ 落盘（%s）" % wnote
    return face(root, env)


def _loop(root, env, interval):
    while True:
        try:
            refresh(root, env)
        except Exception:                                     # noqa: BLE001 — 守护 ⛔ 死
            pass
        time.sleep(max(30.0, float(interval)))


def start_periodic(root=None, env=None, interval=REFRESH_S):
    u"""门后起守护（**后台 · 唯一次 · ⛔ 阻门**）⇒ `bool`（是否起）。
    即刻一次（⇒ 门后数秒即有真读数）∧ 其后每 `interval` s。⛔ 抛。
    """
    global _started
    with _boot_lock:
        if _started:
            return False
        _started = True
    t = threading.Thread(target=_loop, args=(root, env, interval), daemon=True, name="update-check")
    t.start()
    return True