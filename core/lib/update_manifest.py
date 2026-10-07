# -*- coding: utf-8 -*-
u"""更新清单（`update_manifest.json`）之「一处定形」—— 承 pm_1620 §二.1⒜ ＋ pm_1645 §二 令一
（技术总监席 f202f89 · 2026-10-07）。

形（**唯五键** · `MANIFEST_FIELDS`）：
  version       本增量之版号（＝ 升级后装根 `version.json` 之 `version`）
  base_version  所基之版（客户端今版 —— ⛔ 合 ⇒ 由**应用器**裁）
  channel       通道（`internal` ／ `beta` ／ `stable` —— ⛔ 跨档取）
  built_at      造刻（ISO8601 ＋ 时区）
  files         逐件（**唯四键** · `FILE_FIELDS`）：`path` ／ `sha256` ／ `size` ／ `mode`
      path   ＝ **装根相对之径**（POSIX 之 `/` —— ⛔ 绝对 ／ 盘符 ／ `..` ／ 反斜杠 ／ 空段）
      sha256 ＝ 小写 hex64（`del` ⇒ 空串 —— **无件可校**）
      size   ＝ 字节（`del` ⇒ `0`）
      mode   ＝ `add`（新件）｜`mod`（改件）｜`del`（删件）

三守（承 pm_1620 §二.1⒟ ＋ §三.9）：
  ⒜ **⛔ 明文信任** —— 唯 `sha256` 为凭（**逐件校** ⇒ 一件 ⛔ 合 ⇒ 整体 ⛔ 落）
  ⒝ **⛔ 跨档** —— 清单之 `channel` ⛔ 合本机之通道 ⇒ 拒
  ⒞ **⛔ 半途** —— 件数 ／ 总字节须与清单**自述**合（`totals()` 之一处）

⚠ 本模块唯**形 ＋ 校 ＋ 取**（唯 `fetch()` 一次 `GET`）；**写** ／ **应用**归甲-P0 之二器
  （`scripts/win_pa/make_update.py` ／ `pa_update.py`）—— 二器之「形」**唯引本模块**（⛔ 二处各写）。

以何形调用（判通 ／ 断须附）：
  python -X utf8 -B -m pytest tests/unit/test_win_pa_update_1645.py -q
"""
from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
import urllib.request

from core.lib import update_source as US

MANIFEST_NAME = u"update_manifest.json"
MANIFEST_FIELDS = (u"version", u"base_version", u"channel", u"built_at", u"files")
FILE_FIELDS = (u"path", u"sha256", u"size", u"mode")
MODES = (u"add", u"mod", u"del")
CHANNELS = (u"internal", u"beta", u"stable")
#: 取清单之超时（秒）—— 一次 `GET`（⛔ 阻门 ∧ ⛔ 拖「已是最新」之答）
FETCH_TIMEOUT = 8.0
_HEX64 = re.compile(u"^[0-9a-f]{64}$")


#: URL 之径所须保之字（其余 ⇒ 百分号编码）—— HTTP 之径唯 ASCII 安全。
_URL_SAFE = u"/:?&=#%+,;@$!*'()~"


def ascii_url(u):
    u"""URL ⇒ **逐段百分号编码**（**一处定形**）。非 ASCII 之名（如 `scripts/win_pa/净机安装一页.md`）
    ⛔ 直投 `urllib` ⇒ `UnicodeEncodeError` ⇒ **下件中途而败**（本席一手 · 沙箱自验所逮）
    ⇒ 故取件之 URL 一律经此（⛔ 二处各拼）。
    """
    return urllib.parse.quote(str(u), safe=_URL_SAFE)


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def bad_path(p):
    u"""`path` 之守（**一处定形**）⇒ 非空之「因」∨ 空串（合）。"""
    if not isinstance(p, str) or not p:
        return u"空 ∨ 非字串"
    if p.startswith(u"/") or p.startswith(u"\\"):
        return u"绝对径 ／ UNC"
    if len(p) > 1 and p[1] == u":":
        return u"含盘符"
    if u"\\" in p:
        return u"含反斜杠（须 POSIX 之 /）"
    for seg in p.split(u"/"):
        if seg in (u"", u".", u".."):
            return u"含空 ／ `.` ／ `..` 之段"
    return u""


def canonical(doc):
    u"""清单之 canonical 形（**一处定形** —— 印之基）：键序定 ＋ 紧凑。"""
    return json.dumps(doc, ensure_ascii=False, sort_keys=True, separators=(u",", u":"))


def digest(doc):
    u"""清单之印（sha16）—— 器取之凭（「包须自证其出处」· 承 pm_1573 §二）。"""
    return sha256_bytes(canonical(doc).encode(u"utf-8"))[:16]


def totals(doc):
    u"""自述之总数（**一处出**）：件数 ／ 三类之数 ／ 下载字节（`del` ⛔ 计）。"""
    fl = (doc or {}).get(u"files") or []
    add = mod = dele = 0
    nbytes = 0
    for e in fl:
        if not isinstance(e, dict):
            continue
        m = e.get(u"mode")
        if m == u"add":
            add += 1
        elif m == u"mod":
            mod += 1
        elif m == u"del":
            dele += 1
        if m in (u"add", u"mod"):
            s = e.get(u"size")
            if isinstance(s, int) and not isinstance(s, bool) and s > 0:
                nbytes += s
    return {"n": len(fl), "add": add, "mod": mod, "del": dele, "bytes": nbytes}


def validate(doc):
    u"""校清单之形 ⇒ `(ok, probs)`（probs ＝ 人话之逐条 · ⛔ 静默）。"""
    probs = []
    if not isinstance(doc, dict):
        return False, [u"清单非对象（%s）" % type(doc).__name__]
    for k in MANIFEST_FIELDS:
        if k not in doc:
            probs.append(u"缺键：%s" % k)
    extra = sorted(k for k in doc if k not in MANIFEST_FIELDS)
    if extra:
        probs.append(u"多键：%s" % u"、".join(extra))
    for k in (u"version", u"base_version", u"channel", u"built_at"):
        v = doc.get(k)
        if not isinstance(v, str) or not v.strip():
            probs.append(u"%s 须为非空字串（今 %r）" % (k, v))
    ch = doc.get(u"channel")
    if isinstance(ch, str) and ch.strip() and ch not in CHANNELS:
        probs.append(u"通道非常：%s（唯 %s）" % (ch, u"／".join(CHANNELS)))
    fl = doc.get(u"files")
    if not isinstance(fl, list):
        probs.append(u"files 须为列表（今 %s）" % type(fl).__name__)
        return False, probs
    seen = set()
    for i, e in enumerate(fl):
        tag = u"files[%d]" % i
        if not isinstance(e, dict):
            probs.append(u"%s 非对象" % tag)
            continue
        ek = sorted(k for k in e if k not in FILE_FIELDS)
        if ek:
            probs.append(u"%s 多键：%s" % (tag, u"、".join(ek)))
        p = e.get(u"path")
        bp = bad_path(p)
        if bp:
            probs.append(u"%s.path %s（%r）" % (tag, bp, p))
        elif p in seen:
            probs.append(u"%s.path 重（%s）" % (tag, p))
        else:
            seen.add(p)
        m = e.get(u"mode")
        if m not in MODES:
            probs.append(u"%s.mode 非常：%r（唯 %s）" % (tag, m, u"／".join(MODES)))
        s = e.get(u"size")
        if isinstance(s, bool) or not isinstance(s, int) or s < 0:
            probs.append(u"%s.size 须为非负之整数（今 %r）" % (tag, s))
        h = e.get(u"sha256")
        if m == u"del":
            if h not in (u"", None):
                probs.append(u"%s（del）之 sha256 须为空串（今 %r）" % (tag, h))
            if isinstance(s, int) and not isinstance(s, bool) and s != 0:
                probs.append(u"%s（del）之 size 须为 0（今 %r）" % (tag, s))
        elif not (isinstance(h, str) and _HEX64.match(h)):
            probs.append(u"%s.sha256 须为小写 hex64（今 %r）" % (tag, h))
    return (not probs), probs


def fetch(src, timeout=FETCH_TIMEOUT):
    u"""取清单（**唯此一处出网**）⇒ `(doc | None, note, why)`；⛔ 得 ／ 形 ⛔ 合 ⇒ `None` ＋ 因。
    ⚠ ⛔ 抛（调用者据 `note` ／ `why` 照实报 —— 承「凡不可用必有因 ＋ 去处」）。
    """
    url = ascii_url(US.manifest_url(src))
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method=u"GET"), timeout=timeout) as r:
            raw = r.read()
    except Exception as e:                                    # noqa: BLE001 — 照实报因
        return None, u"取清单 ⛔ 得：%s" % url, type(e).__name__
    try:
        doc = json.loads(raw.decode(u"utf-8-sig"))
    except Exception as e:                                    # noqa: BLE001 — 照实报因
        return None, u"清单 ⛔ 解（%s）" % url, type(e).__name__
    ok, probs = validate(doc)
    if not ok:
        return None, u"清单之形 ⛔ 合（%s）：%s" % (url, u"；".join(probs[:4])), u"shape"
    return doc, u"", u""


def fetch_file(src, path, timeout=FETCH_TIMEOUT):
    u"""取一件（**一处出** —— `update_source.package_url` 拼之）⇒ `(bytes | None, note, why)`。"""
    url = url_for(src, path)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method=u"GET"), timeout=timeout) as r:
            return r.read(), u"", u""
    except Exception as e:                                    # noqa: BLE001 — 照实报因
        return None, u"取件 ⛔ 得：%s" % url, type(e).__name__


def url_for(src, path):
    u"""件之取处（**一处出** —— ⛔ 本模块另拼；非 ASCII ⇒ 编码，见 `ascii_url`）。"""
    return ascii_url(US.package_url(src, path))