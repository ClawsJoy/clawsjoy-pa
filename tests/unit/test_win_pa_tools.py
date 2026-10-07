# -*- coding: utf-8 -*-
"""⭐ 三缺 ②：win_pa 五器之自测（承 pm_1382 §二.2 ②）。

五器之界（pm_1382 §二.1 裁）：4 py ＋ 1 ps1
  preflight_start.py ／ pa_nowindow.py ／ probe_alive.py ／ boot_resume.py ＋ check_win_pa.ps1
（bat ＝ 壳 · xml ＝ 任务定义 ⇒ ⛔ 入「器」之数）

以何形调用（判通 ／ 断须附）：
  python -X utf8 -B -m pytest tests/unit/test_win_pa_tools.py -q
⛔ 起停：本测唯 py_compile ／ 只读子进程（--self-test ／ --json 干跑）—— ⛔ 起服 ／ ⛔ 删任务。
"""
import io
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WPA = ROOT / "scripts" / "win_pa"
PY_TOOLS = ("preflight_start.py", "pa_nowindow.py", "probe_alive.py", "boot_resume.py")
PS_TOOLS = ("check_win_pa.ps1",)
TOOLS = PY_TOOLS + PS_TOOLS


def _run(args, timeout=180, env=None):
    return subprocess.run([sys.executable, "-X", "utf8", "-B"] + args,
                          capture_output=True, cwd=str(ROOT), timeout=timeout, env=env)


def test_five_tools_exist_and_are_exactly_five():
    for n in TOOLS:
        p = WPA / n
        assert p.is_file() and p.stat().st_size > 0, n
    assert len(TOOLS) == 5 and len(PY_TOOLS) == 4 and len(PS_TOOLS) == 1


def test_py_tools_compile():
    import py_compile
    for n in PY_TOOLS:
        py_compile.compile(str(WPA / n), doraise=True)


def test_pa_nowindow_has_preflight_gate():
    """⭐ 起服唯经 preflight（rc != 0 ⇒ ⛔ 起）—— 承 pm_1369 §二 裁（唯一入口）。"""
    src = io.open(WPA / "pa_nowindow.py", encoding="utf-8").read()
    assert "preflight_start.py" in src
    assert "preflight not passed" in src and "NOT starting" in src


def test_preflight_ollama_shows_human_reason_and_fix_door():
    """⭐ 探活显形（承 pm_1369 §三.2 · 我 30b523c）：⛔ 只退 rc ⇒ 须人话之因 ＋ 修之门。"""
    src = io.open(WPA / "preflight_start.py", encoding="utf-8").read()
    assert "装 Ollama" in src
    assert "拉权重" in src


def test_tool_self_tests_pass():
    for n in ("preflight_start.py", "probe_alive.py"):
        r = _run(["scripts/win_pa/" + n, "--self-test"])
        assert r.returncode == 0, (n, r.returncode, r.stdout[-400:], r.stderr[-400:])


def test_uninstaller_self_test_passes():
    r = _run(["scripts/win_pa/uninstall_win_pa.py", "--self-test"])
    assert r.returncode == 0, (r.returncode, r.stdout[-400:])


def test_uninstaller_dry_run_declares_two_tasks_without_data():
    r = _run(["scripts/win_pa/uninstall_win_pa.py", "--json"])
    assert r.returncode == 0, (r.returncode, r.stderr[-400:])
    data = json.loads(r.stdout.decode("utf-8"))
    names = [i["name"] for i in data["items"]]
    assert len(names) == 2, names
    assert all("data" not in n.lower() for n in names), names
    assert data["dry_run"] is True


def test_uninstaller_absent_task_reports_nothing_to_remove():
    """ⓓ 反控：未注册 ⇒ 报「无物可卸」∧ rc 0（⛔ 崩）—— 唯干跑。"""
    env = dict(os.environ, PA_UNINSTALL_TASKS=os.sep + "ClawsJoy_PA_SELFTEST_NOPE")
    r = _run(["scripts/win_pa/uninstall_win_pa.py"], env=env)
    out = r.stdout.decode("utf-8", "replace")
    assert r.returncode == 0, (r.returncode, out[-400:])
    assert "无物可卸" in out


def test_start_bat_is_thin_shell():
    """⭐ 收口（承 pm_1369 §二 裁 · 我 6b41f14）：bat 唯转 pa_nowindow.py（⛔ 自起 ／ ⛔ 二入口）。"""
    s = io.open(WPA / "start_win_pa.bat", encoding="utf-8", errors="replace").read()
    pys = [ln.strip() for ln in s.splitlines() if ln.strip().lower().startswith("python")]
    assert pys, "start_win_pa.bat ⛔ 有 python 调用"
    for ln in pys:
        assert "pa_nowindow.py" in ln, ln


def test_check_ps1_declares_param_and_port():
    s = io.open(WPA / "check_win_pa.ps1", encoding="utf-8", errors="replace").read()
    assert "param(" in s and "$Port" in s


def test_shims_do_not_hardcode_dev_path():
    r"""⭐ 净机自足（pm_1450 §二.2）：器之壳 ⛔ **硬编开发机之径**。

    由：包在净机下解到他处 ⇒ `cd /d <main-repo>` ⛔ 得 ⇒
    后续 `python scripts\win_pa\*.py` ⛔ 得⇒ **装必败**。
    形：取**本件位置**（bat ⇒ `%~dp0..\..` · ps1 ⇒ `$PSScriptRoot`）。
    反控：本件亦不许出现 `clawsjoy_build` （同族：二台之根各异）。
    """
    for f in ("install_win_pa.bat", "uninstall_win_pa.bat", "start_win_pa.bat", "stop_win_pa.bat",
              "check_win_pa.ps1"):
        s = io.open(WPA / f, encoding="utf-8", errors="replace").read()
        assert "clawsjoy_v9" not in s, f
        assert "clawsjoy_build" not in s, f
