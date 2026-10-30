# -*- coding: utf-8 -*-
r"""CEO 2268 §二（「停用 ／ 卸载」之二径 ＋ 反控）之齿 —— pa_lifecycle.py（技术总监席 f202f89 · 2026-10-09）。

病（CEO 2268 §二 · 我一手复量 · 刻 2026-10-09T08:40）：本机注册之 \ClawsJoy* 任务 **12** 条；
  而既有卸器 scripts/win_pa/uninstall_win_pa.py 唯动 **2** 条（\ClawsJoy_PA_Boot ／ \ClawsJoy_PA_Start_Once）
  ⇒ 「卸载」后 \ClawsJoy* 余 **10** ⇒ 复扫 ⛔ 净 ⇒ 等于无径（承「⛔ 以 rc 0 代成」）。

判据：
  L1 器在 ／ 编译无 SyntaxWarning（⛔ 死字之警）
  L2 `--self-test` ⇒ rc 0 ∧ PASS（合成之名真跑全链：造 ⇒ 扫见 ⇒ 干跑⛔动 ⇒ 停用 ⇒ Disabled ⇒ 启用 ⇒ Enabled ⇒ 卸载 ⇒ 复扫净）
  L3 `扫` ⇒ rc 0 ∧ 报「面 n 条」＋「口径」＋ 印（二形）
  L4 反控（净之面）：`--prefix <⛔ 在>` 之 `复扫` ⇒ rc 0
  L5 反控（脏之面 · 真造真删）：造合成任务 ⇒ `复扫`（同前缀）⇒ rc 2 ／ 删之 ⇒ rc 0
  L6 反控（干跑 ⛔ 动）：造合成任务 ⇒ `卸载`（⛔ 无 --go）⇒ 仍在 ／ 删之
  L7 `--json` 之形（dry_run ／ rc ／ n）

⛔ 界：本测**唯触** \ClawsJoy_SELFTEST_*（合成 · 自清）；⛔ 触 12 条真任务（一字 ⛔ 动）· ⛔ 起服 · ⛔ 重启。

以何形调用（判通 ／ 断须附）：
  python -X utf8 -B -m pytest tests/unit/test_win_pa_lifecycle_2268.py -q
"""
from __future__ import annotations

import json
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "scripts" / "win_pa" / "pa_lifecycle.py"
BS = chr(92)
PFX = BS + "ClawsJoy_SELFTEST_T"


def _run(args, timeout=240):
    return subprocess.run([sys.executable, "-X", "utf8", "-B", str(TOOL)] + list(args),
                          capture_output=True, cwd=str(ROOT), timeout=timeout)


def _out(r):
    return (r.stdout or b"").decode("utf-8", "replace") + (r.stderr or b"").decode("utf-8", "replace")


def _guard(name):
    r"""守：唯 \ClawsJoy_SELFTEST_* 方得造 ／ 删（⛔ 触真任务）。"""
    assert name.startswith(BS + "ClawsJoy_SELFTEST_"), name


def _create(name):
    _guard(name)
    return subprocess.run(["schtasks", "/create", "/tn", name, "/tr", "cmd /c exit 0",
                           "/sc", "once", "/st", "23:59", "/f"], capture_output=True)


def _delete(name):
    _guard(name)
    subprocess.run(["schtasks", "/delete", "/tn", name, "/f"], capture_output=True)


def _live(name):
    _guard(name)
    return subprocess.run(["schtasks", "/query", "/tn", name], capture_output=True).returncode == 0


def test_L1_tool_present_and_compiles():
    assert TOOL.is_file() and TOOL.stat().st_size > 0, TOOL
    import py_compile
    py_compile.compile(str(TOOL), doraise=True)


def test_L2_self_test_passes():
    r = _run(["--self-test"])
    o = _out(r)
    assert r.returncode == 0, (r.returncode, o[-900:])
    assert "[self-test] PASS" in o, o[-500:]


def test_L3_scan_reports_face_caliber_stamp():
    r = _run([])
    o = _out(r)
    assert r.returncode == 0, (r.returncode, o[-600:])
    assert u"面" in o and u"口径" in o and u"md5[:16]" in o and u"sha16" in o, o[-800:]


def test_L4_rescan_clean_prefix_rc0():
    r = _run(["--prefix", PFX + "_NOPE", u"复扫"])
    assert r.returncode == 0, _out(r)[-600:]


def test_L5_rescan_dirty_prefix_rc2_then_clean():
    name = PFX + "_" + uuid.uuid4().hex[:8]
    assert _create(name).returncode == 0, u"⛔ 无权造合成任务 ⇒ 反控未跑"
    try:
        r = _run(["--prefix", name, u"复扫"])
        assert r.returncode == 2, _out(r)[-600:]
    finally:
        _delete(name)
    r2 = _run(["--prefix", name, u"复扫"])
    assert r2.returncode == 0, _out(r2)[-600:]


def test_L6_dry_run_does_not_delete():
    name = PFX + "_" + uuid.uuid4().hex[:8]
    assert _create(name).returncode == 0, u"⛔ 无权造合成任务 ⇒ 反控未跑"
    try:
        r = _run(["--prefix", name, u"卸载"])
        o = _out(r)
        assert r.returncode == 0, o[-600:]
        assert u"干跑" in o, o[-600:]
        assert _live(name), u"干跑竟删了任务（⛔）"
    finally:
        _delete(name)


def test_L7_json_shape():
    r = _run(["--json", "--prefix", PFX + "_NOPE", u"复扫"])
    d = json.loads(_out(r))
    assert d["dry_run"] is True and d["rc"] == 0 and d["n"] == 0, d
