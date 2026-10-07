# -*- coding: utf-8 -*-
u"""port_lite 之「等价」之齿（承 pm_1595 §二 · 令三 「一处定形」 ／ 令二 「⛔ 拉栈」）。

由：`port_lite.py` 于**薄径**（启动器 ／ 状态 ／ 开页面）自读真源之一小口 ——
  ⛔ 经 `core.lib.port_config`（其**必连带** `core/__init__` ⇒ `chromadb` ／ 向量库）。
「自读」之险 ＝ **二源漂**（真源之二读者各持一份 ⇒ 改一处而彼处静默旧 —— L-14 族）
⇒ 故以器锁三事：⒈ 键链 ／ 主机 ／ 径 ⇔ 应用之出口（⛔ 二源）；
  ⒉ 薄径之值 ⇔ `gateway_port()`（逐字同）；⒊ 薄径之进程 ⛔ 载 `core`（⛔ 拉栈 ／ ⛔ 争库）。

器取：`python -X utf8 -B -m pytest tests/unit/test_win_pa_port_lite.py -q`
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WPA = ROOT / "scripts" / "win_pa"
sys.path.insert(0, str(WPA))
sys.path.insert(0, str(ROOT))

import port_lite as PL  # noqa: E402


def test_thin_reader_mirrors_the_official_exit():
    u"""⒈ 一处定形：键链 ／ 主机 ⇒ 皆 ⇔ `core.lib.port_config`（⛔ 二源各写一份）。"""
    from core.lib import port_config as PC
    assert u".".join(PL.SOURCE_KEY) == PC.SOURCE_KEY, (PL.SOURCE_KEY, PC.SOURCE_KEY)
    assert PL.CLIENT_HOST == PC.CLIENT_HOST, (PL.CLIENT_HOST, PC.CLIENT_HOST)


def test_thin_value_equals_gateway_port(monkeypatch):
    u"""⒉ 薄径之值 ⇔ `gateway_port()` ∧ 页面之址 ⇔ `gateway_base_url()`（**器取**）。"""
    monkeypatch.delenv(u"V9_URL", raising=False)
    from core.lib import port_config as PC
    assert PL.read_port(str(ROOT)) == int(PC.gateway_port())
    assert PL.page_url(str(ROOT)) == PC.gateway_base_url() + PL.PAGE_PATH


def test_thin_path_does_not_pull_core(tmp_path):
    u"""⒊ 决定之齿：薄径之进程 ⛔ 载 `core`（⛔ 连带 chromadb ／ 向量库 ／ ⛔ 与之争库）。"""
    probe = tmp_path / u"probe_thin.py"
    probe.write_bytes((
        u"import runpy, sys\n"
        u"sys.path.insert(0, %r)\n"
        u"sys.argv = ['port_lite.py', '--root', %r]\n"
        u"try:\n"
        u"    runpy.run_path(%r, run_name='__main__')\n"
        u"except SystemExit:\n"
        u"    pass\n"
        u"sys.stderr.write('CORE_LOADED=%%s\\n' %% ('core' in sys.modules))\n"
        % (str(WPA), str(ROOT), str(WPA / u"port_lite.py"))).encode(u"utf-8"))
    r = subprocess.run([sys.executable, u"-X", u"utf8", u"-B", str(probe)],
                       capture_output=True, text=True, encoding=u"utf-8",
                       errors=u"replace", cwd=str(ROOT), timeout=120)
    assert u"CORE_LOADED=False" in (r.stderr or u""), (r.returncode, r.stdout, r.stderr)
    assert (r.stdout or u"").strip().isdigit(), (r.returncode, r.stdout, r.stderr)
