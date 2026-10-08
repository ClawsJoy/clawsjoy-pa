# -*- coding: utf-8 -*-
u"""本机身份之「铸」与「归一」 —— pm_1858 令（§一 ／ §二）· 9.0.11 首件 · 技术总监席 f202f89 · 2026-10-08。

【一句话】身份由**装根**铸一次（`<data_dir>/owner.json`）；浏览器之 localStorage 值唯
**客户端标签**（hint）—— 凡按 `user_id` 归档之处，一律归一到 owner。

【为什么（一手之实）】本机 `data/v9/pa` 曾积 **16** 枚 id：老板真身份 1 枚
（`threads_web_1790773805388.json` · `197397 B`）＋ 我之验跑空壳 15 枚（各 `289 B`）。
铸它的**不是机器**，是**每一个浏览器上下文**（身份落 localStorage）⇒ 换浏览器 ／ 清站点数据 ／
无痕 ⇒ 又生一新 id ⇒ 「本机线程」随之清零。

【形】`owner.json = {schema, id, created_at, source, claimed_from?}`：
  · 在 ⇒ **恒用它**（⛔ 再铸 · ⛔ 被任何 hint 覆盖）；
  · 不在 ⇒ **认领**（下）∨ 铸 `owner_<uuid4-hex12>` ⇒ **原子写**（承 pm_1846 §五.3：器之写亦须原子）。

【认领（pm_1858 §三 · 要紧：⛔ 丢史）】`owner.json` 未立 ∧ hint 为**客户端标签**（`web_*`）∧
其 threads 件在且 `threads` **非空** ⇒ **认其为 owner**（`id` 即该旧值 · ⛔ 另铸 —— 免得史失联）。
余者（无 hint ／ 件缺 ／ **空壳**）⇒ 铸新 owner ∧ ⛔ 以盘上最新之 `threads_web_*.json` 充之
（⛔ 窃他人之史）；旧件**留底入 `_legacy/`**（⛔ 删 · 可回退）。

【安全律（pm_1858 §四.1 · ⛔ 破）】`owner.json` 既立 ⇒ 恒以它为准（⛔ 静默变别人 ／ ⛔ 变 `default`）；
⛔ 由远机定身份 —— 认领唯本机（由路由层把 `_loopback` 之后果传进来：hint 唯本机之请求携）。

【界（本轮）】客户端标签（`web_*`）归一；**余者直通**（`u1` 式兼容之值 · 承 pm_1858 §四.3 旧齿之保）。
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from pathlib import Path

from core.pa.state_out import write_state

OWNER_FILE = "owner.json"
OWNER_SCHEMA = "pa.owner/1"
LEGACY_DIR = "_legacy"
OWNER_PREFIX = "owner_"
CLIENT_PREFIX = "web_"
SOURCE_MINTED = "minted"
SOURCE_CLAIMED = "claimed_from_client"
DISPLAY_DEFAULT = u"本机"
PROFILE_FILE = "profile.json"

#: 画像里可作「名」之键（有**实**方取 · ⛔ 编）
NAME_KEYS = (u"称呼", u"名", u"昵称", u"display_name")

#: 写者标识（进出口的写者归属台账；供 detect_uninstrumented 识别绕过出口的写者）
_WRITER = "pa.identity"


class OwnerCorrupt(Exception):
    u"""`owner.json` **存在但不可用**（读不动 ／ JSON 非法 ／ 结构不符）⇒ fail-loud。

    ⛔ 静默回落 `None` ／ 另铸 —— 那是**静默变成别人**（承 pm_1858 §四.1⒜）。
    """

    def __init__(self, path, reason):
        self.path = str(path)
        self.reason = str(reason)
        super().__init__(u"本机身份档不可用，拒绝按空身份继续：%s（%s）" % (self.path, self.reason))


def _root(data_dir):
    return Path(str(data_dir or os.getenv("PA_DATA_DIR", "data/v9/pa")))


def owner_path(data_dir):
    return _root(data_dir) / OWNER_FILE


def legacy_dir(data_dir):
    return _root(data_dir) / LEGACY_DIR


def threads_path(data_dir, uid):
    return _root(data_dir) / ("threads_%s.json" % str(uid))


def is_client_label(v):
    u"""客户端标签之判 —— `web_<ms>`（唯形制：`web/pa/faces/session.js::ensureUserId`）。"""
    s = str(v or "")
    return s.startswith(CLIENT_PREFIX) and len(s) > len(CLIENT_PREFIX)


def _shape(doc):
    u"""身份档之业务结构判据（`schema` ／ `id` 皆须非空 str —— ⛔ 半截之档）。"""
    if not isinstance(doc.get("id"), str) or not doc.get("id"):
        return False, u"id 需为非空 str"
    if not isinstance(doc.get("schema"), str) or not doc.get("schema"):
        return False, u"schema 需为非空 str"
    return True, ""


def _stamp(now=None):
    return time.strftime("%Y%m%d-%H%M%S", time.localtime(time.time() if now is None else float(now)))


def read_owner(data_dir):
    u"""读 owner 档：**不存在 ⇒ `None`**；存在但不可用 ⇒ 抛 `OwnerCorrupt`（⛔ 回落 `None`）。

    ⚠ 此处**不走** `StateFile.read`：它遇坏件会**隔离移走** ⇒ 下一次调用就另铸一个新身份
    （＝静默变成别人）。身份档之坏须**原地留着** ∧ 每次调用皆 fail-loud，等人来修。
    """
    p = owner_path(data_dir)
    if not p.exists():
        return None
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        raise OwnerCorrupt(p, u"读不动 ／ JSON 非法（%s）" % type(e).__name__)
    ok, why = _shape(doc if isinstance(doc, dict) else {})
    if not ok:
        raise OwnerCorrupt(p, why)
    return doc


def _mint_id():
    return OWNER_PREFIX + uuid.uuid4().hex[:12]


def _write_owner(data_dir, doc):
    u"""**原子写**（跨进程锁 ＋ 原子替换 —— 走统一出口 `core/pa/state_out`）。"""
    return write_state(owner_path(data_dir), _WRITER, _shape, doc, reason="pa.identity.ensure_owner")


def threads_state_of(data_dir, uid):
    u"""该 id 之 threads 件 ⇒ `True`（有件 ∧ **有史**）／ `False`（有件 ∧ **空壳**）／ `None`（**无件**）。

    ⚠ 读不动之件 ⇒ 视同**有史**（保守：宁可认领，⛔ 以空壳待之而弃史）。
    """
    p = threads_path(data_dir, uid)
    if not p.exists():
        return None
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return True
    t = doc.get("threads") if isinstance(doc, dict) else None
    if isinstance(t, list) and not t:
        return False
    return True


def _legacy_target(data_dir, name):
    u"""`_legacy/` 之下一个**不撞名**之落点（撞 ⇒ 加刻）。"""
    d = legacy_dir(data_dir)
    d.mkdir(parents=True, exist_ok=True)
    dst = d / name
    if dst.exists():
        dst = d / ("%s.%s" % (name, _stamp()))
    return dst


_SIDECARS = (".lock", ".writes.jsonl")


def keep_legacy(data_dir, src):
    u"""**留底**（copy · ⛔ 动原）入 `_legacy/` ⇒ 落点 ∨ `None`（承 pm_1858 §三.2：留底可回退 · ⛔ 删）。"""
    src = Path(str(src))
    if not src.exists():
        return None
    try:
        dst = _legacy_target(data_dir, src.name)
        dst.write_bytes(src.read_bytes())
        for _suf in _SIDECARS:
            _side = Path(str(src) + _suf)
            if _side.exists():
                _legacy_target(data_dir, _side.name).write_bytes(_side.read_bytes())
    except Exception:
        return None
    return dst


def move_legacy(data_dir, src):
    u"""**移入** `_legacy/`（原处移走 · 承 pm_1858 §三.4 空壳之清）⇒ 落点 ∨ `None`。"""
    src = Path(str(src))
    if not src.exists():
        return None
    try:
        dst = _legacy_target(data_dir, src.name)
        os.replace(str(src), str(dst))
    except Exception:
        return None
    for _suf in _SIDECARS:
        _side = Path(str(src) + _suf)
        if _side.exists():
            try:
                os.replace(str(_side), str(_legacy_target(data_dir, _side.name)))
            except Exception:
                pass
    return dst


def migrate(data_dir, owner_id, old_id=None):
    u"""旧式 threads 件 ⇒ 认领后之**归位**（pm_1858 §三.2）。

    判据（逐条可核）：① 新名之件与旧件**逐字节**同（`sha256` 等）；② 件数 ／ 字节数**照旧**
    （⛔ 改一字）；③ 旧件**留底在 `_legacy/`**（⛔ 删 · 可回退）。

    ⚠ 认领之实（§三.1）⇒ `owner_id ≡ old_id` ⇒ 二层名**同** ⇒ 活件**一字不动**，唯留底；
    异名（防御之路）⇒ 先落新名 ＋ 校 sha，方移旧件（⛔ 未校先移）。
    """
    oid = str(old_id or owner_id)
    src = threads_path(data_dir, oid)
    dst = threads_path(data_dir, owner_id)
    out = {"旧": oid, "新": str(owner_id), "件": src.name, "同名": str(src) == str(dst),
           "字节": 0, "sha256": "", "留底": None, "移": False}
    if not src.exists():
        return out
    b = src.read_bytes()
    out["字节"] = len(b)
    out["sha256"] = hashlib.sha256(b).hexdigest()
    if str(src) == str(dst):
        _keep = keep_legacy(data_dir, src)
        out["留底"] = str(_keep) if _keep else None
        return out
    dst.parent.mkdir(parents=True, exist_ok=True)
    _tmp = Path(str(dst) + ".new")
    _tmp.write_bytes(b)
    os.replace(str(_tmp), str(dst))
    if hashlib.sha256(dst.read_bytes()).hexdigest() != out["sha256"]:
        raise OwnerCorrupt(dst, u"归位后之件与旧件 sha256 ⛔ 同 ⇒ 拒（⛔ 冒险移走旧件）")
    for _suf in _SIDECARS:
        _side = Path(str(src) + _suf)
        if _side.exists():
            try:
                Path(str(dst) + _suf).write_bytes(_side.read_bytes())
            except Exception:
                pass
    _mv = move_legacy(data_dir, src)
    out["留底"] = str(_mv) if _mv else None
    out["移"] = bool(_mv)
    return out


def sweep_shells(data_dir, keep=()):
    u"""空壳之清（pm_1858 §三.4）：`threads_web_*.json` 且 `threads == []` 者 ⇒ **移入 `_legacy/`**。

    `keep` 之 id ⛔ 动（本 owner ／ 本次之 hint 之活件）。⇒ 逐条 `{件, 字节, 移}`。
    """
    root = _root(data_dir)
    if not root.is_dir():
        return []
    kept = set(str(x) for x in keep if x)
    out = []
    for p in sorted(root.glob("threads_web_*.json")):
        uid = p.name[len("threads_"):-len(".json")]
        if uid in kept:
            continue
        if threads_state_of(data_dir, uid) is not False:
            continue
        try:
            n = p.stat().st_size
        except Exception:
            n = 0
        _mv = move_legacy(data_dir, p)
        out.append({"件": p.name, "字节": n, "移": bool(_mv)})
    return out


def unclaimed_legacy(data_dir, owner_id=None):
    u"""**未认领之旧史**（⛔ 窃 ／ ⛔ 静默）：非空 ∧ ⛔ 本 owner 之 `threads_web_*.json` ⇒ 逐条 `{件, 字节}`。

    由：hint 未携（新机器 ／ 无痕 ／ 面未改）⇒ 铸新 owner ⇒ 盘上之旧史**仍在**（⛔ 动它）
    —— 须**看得见**（否则用户只见「会话没了」，不知史在盘上 —— 承「空 ⛔ 混 缺」）。
    """
    root = _root(data_dir)
    if not root.is_dir():
        return []
    own = str(owner_id or "")
    out = []
    for p in sorted(root.glob("threads_web_*.json")):
        uid = p.name[len("threads_"):-len(".json")]
        if uid == own or threads_state_of(data_dir, uid) is not True:
            continue
        try:
            n = p.stat().st_size
        except Exception:
            n = 0
        out.append({"件": p.name, "字节": n})
    return out


def ensure_owner(data_dir, hint=None, now=None):
    u"""本机 owner 之**唯取**（铸 ／ 认领 ／ 恒用既有）⇒ owner doc（幂等 · 二次调用同值）。

    认出之实另附二键（⛔ 入盘）：`迁移`（`migrate` 之逐条事实）／ `清壳`（`sweep_shells` 之逐条事实）。
    """
    cur = read_owner(data_dir)
    if cur is not None:
        return cur
    h = str(hint or "").strip()
    claim = bool(is_client_label(h)) and threads_state_of(data_dir, h) is True
    doc = {"schema": OWNER_SCHEMA, "created_at": _stamp(now),
           "source": (SOURCE_CLAIMED if claim else SOURCE_MINTED)}
    if claim:
        doc["id"] = h
        doc["claimed_from"] = h
    else:
        doc["id"] = _mint_id()
    _write_owner(data_dir, doc)
    out = dict(doc)
    out[u"迁移"] = migrate(data_dir, doc["id"], old_id=(h if claim else None))
    out[u"清壳"] = sweep_shells(data_dir, keep=(doc["id"],))
    return out


def resolve(data_dir, hint=None, now=None):
    u"""hint（客户端标签）⇒ **本机 owner 之 id**（pm_1858 §二.2 · 归一）。

    · 客户端标签（`web_*`）⇒ 归一（首见 ⇒ 认领 ∨ 铸；owner 既立 ⇒ **恒返它** —— ⛔ 由 hint 定归属）；
    · 余者（`u1` 式兼容之值 ／ 空 ／ 非法）⇒ **直通**（本轮兼容 · 承 pm_1858 §四.3 旧齿之保）。
    """
    h = str(hint or "").strip()
    if not is_client_label(h):
        return h
    return str(ensure_owner(data_dir, hint=h, now=now)["id"])


def display_of(data_dir):
    u"""面上之显示名（**人话**）⇒ `(名, 源)`；源 ∈ `{profile, default, unreadable}`。

    ⛔ 内部缩写 ／ 机器号上屏（承 pm_1858 §二.3）：画像有「名」之**实** ⇒ 其名；
    ⛔ 无 ⇒ 「本机」（人话 · ⛔ 编）。画像件读不动 ⇒ 名照「本机」而**源照实书 unreadable**
    （承「空 ⛔ 混 缺」：读不到 ⛔ 书「未接」）。
    """
    p = _root(data_dir) / PROFILE_FILE
    if not p.exists():
        return DISPLAY_DEFAULT, "default"
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return DISPLAY_DEFAULT, "unreadable"
    if not isinstance(doc, dict):
        return DISPLAY_DEFAULT, "unreadable"
    for e in (doc.get("entries") or []):
        if not isinstance(e, dict):
            continue
        if str(e.get("status") or "") in ("revised", "deprecated"):
            continue
        if str(e.get("domain") or "") != "fact":
            continue
        if str(e.get("key") or "") not in NAME_KEYS:
            continue
        v = str(e.get("value") or "").strip()
        if v:
            return v, "profile"
    return DISPLAY_DEFAULT, "default"

