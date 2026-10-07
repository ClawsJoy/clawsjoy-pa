# -*- coding: utf-8 -*-
u"""留言板之「收件 ／ 取件 ／ 回话」（**一处定形** · 承 pm_1634 §二.1~§二.3 · 技术总监席 f202f89 · 2026-10-07）。

老板之批（逐字 · pm_1634 §〇）：「批，增加留言板，先用局域网内测，但是客服 Agent 需要跟上」
⇒ 本模块 ＝ 板之**后端落点**（三动：收件 ／ 取件 ／ 回话）：

  收件  用户之「题 ＋ 文 ＋ 附件 ＋ 逐项勾选」⇒ 落**本机**之收件目录
        `data/pa/feedback/<刻>.json`（**一处定形** 之 schema）＋ `…/<刻>/附件/<名>`；
  取件  客服席读之（`list_items` ／ `read_item`）—— 内测期：我上门取 ∨ 用户贴到板 ∨ 用户复制诊断包；
  回话  客服席之回话落 `…/<刻>/回话.json`（照今日原型之黄框）⇒ 板上显（`read_item` 之 `reply`）。

铁律（承 pm_1634 §三.2 ＋ `feedback_target`）：
  * **⛔ 任何网络发送**（本模块**⛔ 引** socket ／ urllib ／ requests ／ http.client ／ httpx ——
    其「⛔ 出机」由 `feedback_target.outbound()` 判 ∧ 由结构齿（源码扫）守）。
  * **⛔ 出机**（内测期）：落点唯本机之目录（`mode=relay` 时**亦⛔**由此模块发 —— 发归将来之「发送」一处）。
  * **脱敏**：入件之文先过 `scrub()`（密钥形 ⇒ 掩）；诊断包之脱敏见 `core/pa/diagnostics.py`。
  * **勾选默认 ⛔ 全选**（`CONSENT_BUSES` 逐项 ⇒ 缺省全 False ∧ **照实记**）。
"""
from __future__ import annotations

import base64
import io
import json
import os
import re
import time

from core.lib import feedback_target as FT

#: 件之 schema（**一处定形** · 面（web）唯读之 —— ⛔ 二处各写）
SCHEMA = u"pa.feedback/1"

#: 逐项勾选之项（**一处定形**）—— **默认全 ⛔ 勾**（承 pm_1634 §二.1 ＋ 红线四条「⛔ 默认带」）
CONSENT_BUSES = (u"health", u"logs", u"env", u"diag")

MAX_TITLE = 120
MAX_BODY = 20000
MAX_ATTACH_N = 10
MAX_ATTACH_BYTES = 8 * 1024 * 1024

#: 密钥之形（**一处定形** —— `scrub` 唯此一处判）：sk-… ／ Bearer … ／ key=… ／ AKIA…
_SECRET_RE = (
    re.compile(u"(?i)\\b(sk-[A-Za-z0-9_\\-]{6,})"),
    re.compile(u"(?i)\\b(bearer\\s+[A-Za-z0-9._\\-]{6,})"),
    re.compile(u"(?i)\\b((?:api[_-]?key|token|secret|password|passwd|pwd)\\s*[=:]\\s*)([^\\s,;\"']{6,})"),
    re.compile(u"\\b(AKIA[0-9A-Z]{12,})"),
)
#: env 之中「像密钥」之键（⇒ 其值作哨兵 ⇒ 一律掩）—— 一处定形
_SECRET_KEY_RE = re.compile(u"(?i)(key|token|secret|password|passwd|pwd|credential)")


class FeedbackError(Exception):
    u"""入件之拒（**人话** ⇒ 面之 400 · 承「凡不可用必有因 ＋ 去处」）。"""


def new_id(now=None):
    u"""件号（**一处定形**）：`<刻>-<4hex>` —— 可排序 ∧ 唯一（同秒亦 ⛔ 撞）。"""
    ts = time.strftime(u"%Y%m%d-%H%M%S", time.localtime(now if now is not None else time.time()))
    return u"%s-%s" % (ts, base64.b16encode(os.urandom(2)).decode(u"ascii").lower())


def root_of(root=None):
    u"""收件根（**一处定形**）—— 唯自 `feedback_target` 出（⛔ 本模块另拼）。"""
    return FT.feedback_dir(root)


def item_dir(root, fid):
    return os.path.join(root_of(root), str(fid))


def item_json(root, fid):
    return os.path.join(item_dir(root, fid), u"件.json")


def reply_json(root, fid):
    return os.path.join(item_dir(root, fid), u"回话.json")


def attach_dir(root, fid):
    return os.path.join(item_dir(root, fid), u"附件")


def scrub(text, extra=None):
    u"""脱敏（**一处定形**）：密钥之形 ⇒ `***`；`extra` ＝ 哨兵（env 之像密钥者之值）—— 逐字掩。"""
    s = text if isinstance(text, str) else (u"" if text is None else str(text))
    for v in (extra or []):
        v = str(v or u"")
        if len(v) >= 6:
            s = s.replace(v, u"***")
    s = _SECRET_RE[0].sub(u"***", s)
    s = _SECRET_RE[1].sub(u"***", s)
    s = _SECRET_RE[2].sub(lambda m: m.group(1) + u"***", s)
    s = _SECRET_RE[3].sub(u"***", s)
    return s


def sentinels(env=None):
    u"""env 之中「像密钥」之值（哨兵 · 供脱敏之正控）—— 一处定形。"""
    env = os.environ if env is None else env
    out = []
    for k, v in (env.items() if hasattr(env, u"items") else []):
        if _SECRET_KEY_RE.search(str(k)) and isinstance(v, str) and len(v) >= 8:
            out.append(v)
    return out


def _safe_name(name):
    u"""附件之名（**一处定形**）：唯**裸名** ∧ ⛔ 路径分隔 ∧ ⛔ `..` ∧ 唯白名单之字 —— 否则**拒**。
    ⚠ ⛔ 静默「取其基名」（承「⛔ 静默失败」）：带径 ／ 带 `..` 者 ⇒ 照实拒 ＋ 人话。
    """
    raw = str(name or u"").strip()
    if (not raw) or (u"/" in raw) or (u"\\" in raw) or (u".." in raw):
        raise FeedbackError(u"附件之名非法（含路径 ／ 上级引用：%s）—— 请重选其件" % raw[:40])
    n = raw.lstrip(u".")
    if not n:
        raise FeedbackError(u"附件之名非法（空）—— 请重选其件")
    if not re.match(u"^[\\w\\u4e00-\\u9fa5][\\w\\u4e00-\\u9fa5.\\-]{0,80}$", n):
        raise FeedbackError(u"附件之名非法（%s）—— 唯中文 ／ 字母 ／ 数字 ／ 点 ／ 连字" % n[:40])
    return n


def _norm_consent(raw):
    u"""逐项勾选之归一 ⇒ `{bus: bool}` —— **缺省全 False**（⛔ 默认带 · 照实记其原值）。"""
    raw = raw if isinstance(raw, dict) else {}
    out = {}
    for b in CONSENT_BUSES:
        out[b] = bool(raw.get(b))
    return out


def submit(root, payload, now=None, env=None):
    u"""收件 ⇒ `(fid, doc, rows)`；入件不合 ⇒ `FeedbackError`（人话 · 承「凡不可用必有因」）。"""
    p = payload if isinstance(payload, dict) else {}
    title = str(p.get(u"title") or u"").strip()
    body = str(p.get(u"body") or u"").strip()
    if not title:
        raise FeedbackError(u"请填「题目」—— 一句话说清你遇到的问题（必填）")
    if len(title) > MAX_TITLE:
        raise FeedbackError(u"题目过长（%d > %d）—— 请精简" % (len(title), MAX_TITLE))
    if not body:
        raise FeedbackError(u"请填「说明」—— 必填；可含操作步骤 ／ 期望 ／ 实际")
    if len(body) > MAX_BODY:
        raise FeedbackError(u"说明过长（%d > %d）—— 请精简" % (len(body), MAX_BODY))
    raw_attach = p.get(u"attach") if isinstance(p.get(u"attach"), list) else []
    if len(raw_attach) > MAX_ATTACH_N:
        raise FeedbackError(u"附件过多（%d > %d 件）" % (len(raw_attach), MAX_ATTACH_N))
    sen = sentinels(env)
    fid = new_id(now)
    d = item_dir(root, fid)
    os.makedirs(d, exist_ok=True)
    rows = [u"[feedback] 收件 %s" % fid]
    names = []
    if raw_attach:
        os.makedirs(attach_dir(root, fid), exist_ok=True)
        for i, a in enumerate(raw_attach):
            a = a if isinstance(a, dict) else {}
            nm = _safe_name(a.get(u"name") or (u"附件%d" % (i + 1)))
            try:
                raw = base64.b64decode(str(a.get(u"b64") or u""), validate=False)
            except Exception:                                     # noqa: BLE001 — 照实拒
                raise FeedbackError(u"附件「%s」之解码败 —— 请重选其件" % nm)
            if len(raw) > MAX_ATTACH_BYTES:
                raise FeedbackError(u"附件「%s」过大（%.1f MB > %d MB）" % (nm, len(raw) / 1048576.0,
                                                                        MAX_ATTACH_BYTES // 1048576))
            with io.open(os.path.join(attach_dir(root, fid), nm), u"wb") as fh:
                fh.write(raw)
            names.append(nm)
            rows.append(u"    [附件] %s（%d 字节）" % (nm, len(raw)))
        rows.append(u"    ⇒ 已落 %s（⛔ 出机）" % attach_dir(root, fid))
    doc = {
        u"schema": SCHEMA,
        u"id": fid,
        u"at": time.strftime(u"%Y-%m-%dT%H:%M:%S%z", time.localtime(now if now is not None else time.time())),
        u"title": scrub(title, sen),
        u"body": scrub(body, sen),
        u"contact": scrub(str(p.get(u"contact") or u"").strip(), sen),   # 自愿填（称呼 ／ 回信方式）
        u"kind": str(p.get(u"kind") or u"反馈").strip()[:20],
        u"consent": _norm_consent(p.get(u"consent")),                     # 逐项勾选 · 默认全 False
        u"attach": names,
        u"target": {u"mode": FT.load(root)[u"mode"], u"channel": FT.load(root)[u"channel"],
                    u"outbound": FT.load(root)[u"outbound"]},
        u"state": u"open",
    }
    with io.open(item_json(root, fid), u"w", encoding=u"utf-8", newline=u"") as fh:
        fh.write(json.dumps(doc, ensure_ascii=False, indent=1))
    rows.append(u"    件 ＝ %s（勾选：%s）" % (item_json(root, fid),
                                           u"；".join(u"%s=%s" % (k, v) for k, v in doc[u"consent"].items())))
    return fid, doc, rows


def list_items(root, limit=50):
    u"""取件之列（新者先）⇒ `[{id, at, title, kind, attach_n, state, has_reply}]`（⛔ 正文全载）。"""
    base = root_of(root)
    out = []
    if not os.path.isdir(base):
        return out
    def _key(nm):
        try:
            return (os.path.getmtime(os.path.join(base, nm)), nm)
        except OSError:
            return (0.0, nm)

    for nm in sorted(os.listdir(base), key=_key, reverse=True):
        fp = os.path.join(base, nm, u"件.json")
        if not (os.path.isfile(fp) and os.path.isdir(os.path.join(base, nm))):
            continue
        try:
            d = json.loads(io.open(fp, encoding=u"utf-8").read())
        except Exception:                                         # noqa: BLE001 — 照实跳（⛔ 崩）
            out.append({u"id": nm, u"broken": True})
            continue
        out.append({u"id": d.get(u"id") or nm, u"at": d.get(u"at") or u"", u"title": d.get(u"title") or u"",
                    u"kind": d.get(u"kind") or u"", u"attach_n": len(d.get(u"attach") or []),
                    u"state": d.get(u"state") or u"", u"has_reply": os.path.isfile(reply_json(root, nm))})
        if len(out) >= int(limit):
            break
    return out


def read_item(root, fid):
    u"""取件之全 ⇒ `item ＋ reply`（未见 ⇒ `None`）。"""
    fp = item_json(root, fid)
    if not os.path.isfile(fp):
        return None
    d = json.loads(io.open(fp, encoding=u"utf-8").read())
    rp = reply_json(root, fid)
    d[u"reply"] = json.loads(io.open(rp, encoding=u"utf-8").read()) if os.path.isfile(rp) else None
    return d


def write_reply(root, fid, text, by=u"客服席", now=None):
    u"""回话（客服席 ⇒ 落 `回话.json` · 照今日原型之黄框）⇒ `rows`；件未见 ⇒ `FeedbackError`。"""
    if not os.path.isdir(item_dir(root, fid)):
        raise FeedbackError(u"件 ⛔ 见（%s）—— 请核其号" % fid)
    t = scrub(str(text or u"").strip(), sentinels())
    if not t:
        raise FeedbackError(u"回话为空 —— 请写点什么（⛔ 空回）")
    doc = {u"schema": SCHEMA, u"id": fid, u"by": str(by or u"客服席")[:40],
           u"at": time.strftime(u"%Y-%m-%dT%H:%M:%S%z", time.localtime(now if now is not None else time.time())),
           u"text": t}
    with io.open(reply_json(root, fid), u"w", encoding=u"utf-8", newline=u"") as fh:
        fh.write(json.dumps(doc, ensure_ascii=False, indent=1))
    ip = item_json(root, fid)
    try:
        it = json.loads(io.open(ip, encoding=u"utf-8").read())
        it[u"state"] = u"replied"
        with io.open(ip, u"w", encoding=u"utf-8", newline=u"") as fh:
            fh.write(json.dumps(it, ensure_ascii=False, indent=1))
    except Exception:                                             # noqa: BLE001 — 照实不崩（回话已落）
        pass
    return [u"[feedback] 回话 %s ⇒ %s" % (fid, reply_json(root, fid))]


def source_scan(path=None):
    u"""结构齿（**一处定形** · 借 `feedback_target.source_scan`）：本模块 ⛔ 引网络之件。"""
    return FT.source_scan(path or os.path.abspath(__file__))
