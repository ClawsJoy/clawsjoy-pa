# -*- coding: utf-8 -*-
u"""版号字面「书他处者，必与真源同 ∨ 入豁免册」之闸（承 pm_1821 §一.3 ／ pm_1849 §二.2）。

病（一手 · 承 pm_1846 §四.1）：产品版号在仓内「书他处」者四处，而旧齿
（tests/unit/test_version_single_source.py）唯咬「三档」（routes/static.py ／
core/web/health.py ／ core/routes/system_routes.py）⇒ `core/lib/version.py:8` 之**注文行**与
`core/lib/platform_client.py:55` 之**报名体**无齿咬 ⇒ 9.0.7 ⇒ 9.0.8 升号时注文行漏改
⇒ **该件首注自谎**（承「书他处之版，二者皆无 ⇒ 必漂」）。

判据：
  ⒈ 扫 `core/**` ＋ `scripts/**`（`*.py` ／ `*.toml`）之**我方版号族**字面 —— 族 ＝
     `__version__` 之 `<major>.` 前缀（**由真源取** · ⛔ 手写；族外者如子模块之 `1.0.0` 与本闸无涉）；
  ⒉ 其行须有「书版」之上下文（`version` ／ `__version__` ／ 版 ／ 升）；
  ⒊ 命中者 ⇒ **必 ≡ `__version__`**（「由真源取」之实）⇔ **在豁免册**
     `tests/baseline/version_literals_exempt.json`；
  ⒋ **陈旧豁免 ＝ 红**：册中每一 `(path, 字面)` 须**仍被逮** —— 否则删条目（承 name_shadowing 之例）；
  ⒌ **反控**：① 植入同族之假字面 ⇒ 必逮 ／ ② 真源改而字面未跟 ⇒ 必逮（＝升号漏改之复现）
     ／ ③ 册内之字面 ⇒ ⛔ 逮（豁免真生效 —— ⛔ 以「已入册」充「已咬」）。

界：本闸唯**字面之静观**（⛔ 真跑 ／ ⛔ 读装根 ／ ⛔ 改任何件）；真源 ＝ `core/lib/version.py`。
⚠ 范围之限（照实）：`pyproject.toml` 在仓根（⛔ 在 `SCAN_SCOPE` 内）⇒ 其一致由
`test_version_single_source.py` 咬（⛔ 本闸代庖）。
"""
import io
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.lib.version import __version__  # noqa: E402

EXEMPT_PATH = ROOT / "tests" / "baseline" / "version_literals_exempt.json"

#: 扫之根 —— 与豁免册之 `scan_scope` **须同**（判据断言之 ⇒ 防悄悄缩范围）
SCAN_SCOPE = ("core", "scripts")
#: 扫之件型
SUFFIXES = (".py", ".toml")
#: 「书版」之上下文（行内含其一即算）
CTX = (u"version", u"__version__", u"版", u"升")
#: 版号之形（三段数字 · 前后 ⛔ 接数字与点 ⇒ 免咬 `9.0.8.1` 之误）
LIT_RE = re.compile(r"(?<![\d.])(\d+\.\d+\.\d+)(?![\d.])")


def family(ver):
    u"""版号之族（`<major>.`）—— **由真源取**（⛔ 手写 `9.`）。"""
    return ver.split(".")[0] + "."


def scan_text(rel, text, ver):
    u"""单件之字面之逮 ⇒ [(rel, 行号, 字面, 行)]（反控之入口 —— ⛔ 唯盘）。"""
    fam = family(ver)
    out = []
    for lineno, line in enumerate(text.split(u"\n"), 1):
        if not any(c in line for c in CTX):
            continue
        for m in LIT_RE.finditer(line):
            if m.group(1).startswith(fam):
                out.append((rel, lineno, m.group(1), line.strip()))
    return out


def scan(ver=None, root=None):
    u"""全扫 ⇒ 逮得者（唯读 · ⛔ 写任何件）。"""
    ver = ver or __version__
    base_root = Path(root or ROOT)
    out = []
    for scope in SCAN_SCOPE:
        for dirpath, dirnames, filenames in os.walk(str(base_root / scope)):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for fn in sorted(filenames):
                if not fn.endswith(SUFFIXES):
                    continue
                full = Path(dirpath) / fn
                rel = full.relative_to(base_root).as_posix()
                text = io.open(str(full), encoding="utf-8", errors="replace").read()
                out.extend(scan_text(rel, text, ver))
    return out


def exemptions():
    u"""豁免册 ⇒ (全册, {(path, 字面)})。"""
    d = json.loads(io.open(str(EXEMPT_PATH), encoding="utf-8").read())
    keys = set()
    for e in d[u"entries"]:
        for lit in e[u"literals"]:
            keys.add((e[u"path"], lit))
    return d, keys


def drift(ver=None, root=None):
    u"""应同步而未同步者（＝ 字面 ⛔ ≡ 真源 ∧ ⛔ 在册）。"""
    _, keys = exemptions()
    want = ver or __version__
    return [h for h in scan(ver=ver, root=root)
            if h[2] != want and (h[0], h[2]) not in keys]


def test_scope_matches_register():
    u"""扫之根须与册所书同（防「悄悄缩范围」＝ 假绿之邻）。"""
    d, _ = exemptions()
    assert tuple(d[u"scan_scope"]) == SCAN_SCOPE, (d[u"scan_scope"], SCAN_SCOPE)


def test_scan_is_not_empty():
    u"""⛔ 空 ≠ 缺：全无逮得 ⇒ 器坏（本仓必有同族字面 · 承「空 ⛔ 混 缺」）。"""
    hits = scan()
    assert hits, u"扫描器零命中 ⇒ 本闸 ⛔ 可信"


def test_every_product_literal_is_single_source_or_registered():
    u"""⭐ 主判：同族之「书版」字面 ⇒ 必 ≡ 真源 ∨ 在册。"""
    bad = drift()
    assert not bad, (u"「书他处之版」未与真源同且未入豁免册（升号漏改即此）："
                     + repr([(h[0], h[1], h[2]) for h in bad]))


def test_no_stale_exemption():
    u"""⭐ 陈旧豁免 ＝ 红：册内之 (path, 字面) 若不再现 ⇒ 必删（承 name_shadowing 之例）。"""
    _, keys = exemptions()
    found = set((h[0], h[2]) for h in scan())
    stale = sorted(k for k in keys if k not in found)
    assert not stale, u"陈旧豁免（条目所记字面已不再现 ⇒ 必删）：" + repr(stale)


def test_teeth_fake_literal_is_caught():
    u"""反控一：同族之假字面 ⇒ 必逮；真源之引 ⇒ ⛔ 误逮。"""
    fake = u'return jsonify({"service": "X", "version": "9.9.9"})'
    assert scan_text(u"fake/x.py", fake, __version__), u"反控失败：假字面未被逮"
    ok = u'return jsonify({"service": "X", "version": __version__})'
    assert scan_text(u"fake/x.py", ok, __version__) == [], u"反控失败：真源之引被误逮"


def test_teeth_bump_without_following_bites():
    u"""反控二：真源升而字面未跟 ⇒ 必逮（＝ 9.0.7 ⇒ 9.0.8 注文行漏改之复现）。"""
    got = set((h[0], h[2]) for h in drift(ver=u"9.9.9"))
    assert (u"core/lib/version.py", __version__) in got, got
    assert (u"core/lib/platform_client.py", __version__) in got, got


def test_teeth_registered_literal_is_exempt():
    u"""反控三：册内之字面 ⇒ ⛔ 逮（豁免真生效 —— ⛔ 以「已入册」充「已咬」）。"""
    got = set((h[0], h[2]) for h in drift(ver=u"9.9.9"))
    assert (u"scripts/win_pa/pa_update.py", u"9.0.7") not in got, got
    assert (u"scripts/win_pa/make_payload.py", u"9.0.1") not in got, got
