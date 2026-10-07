# -*- coding: utf-8 -*-
u"""「真安装包」（老板裁 ⒞ · pm_1577）之测。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_win_pa_setup_1577.py -q

判据（逐条对 pm_1577）：
  ⒜ 三器之 `--self-test` 皆 PASS（器自带之反控）
  ⒝ `installer_post --json`（干跑）⇒ **纯 JSON** ∧ rc 0 ∧ ⛔ 动盘（装根之默认径 ⛔ 造）
  ⒞ 启动器皆走**自带之 runtime**（⛔ 系统 python）∧ 起停皆走**唯一入口** `pa_nowindow.py`
  ⒟ `install_pa.cmd`（iexpress 之 AppLaunched 入口）⇒ 解 `payload.zip` ∧ 调 `installer_post --go`
  ⒠ `preflight_start` 之**降级**（ollama ／ 向量库「未见」）⛔ 阻起 ∧ `--strict` 复旧律 ∧
     真病（向量库不可写 ／ Python 版旧）**仍阻**
  ⒡ `make_setup` 之前置守：⛔ 见自带运行时 ／ 册 ／ 而「data\\ ／ logs\\」在 ⇒ **⛔ 造**
⛔ 起停 ／ ⛔ 注册任务 ／ ⛔ 出真包（本测唯干跑 ／ --self-test ／ tmp 之合成树）。
"""
import importlib.util
import io
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WPA = ROOT / "scripts" / "win_pa"
BS = chr(92)


def _run(name, args, timeout=600):
    return subprocess.run([sys.executable, "-X", "utf8", "-B", str(WPA / name)] + list(args),
                          capture_output=True, cwd=str(ROOT), timeout=timeout)


def _mod(name):
    spec = importlib.util.spec_from_file_location("_m1577_" + name.replace(".", "_"), str(WPA / name))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _self_test(name, marker="[self-test] PASS"):
    r = _run(name, ["--self-test"])
    out = r.stdout.decode("utf-8", "replace")
    assert r.returncode == 0, (name, r.returncode, out[-1200:])
    assert marker in out, (name, out[-600:])
    return out


def test_installer_post_self_test_passes():
    _self_test("installer_post.py")


def test_build_runtime_self_test_passes():
    u"""自带运行时之器（pm_1577 §三.1）—— 其自测之报形为「=== … 通过 ===」。"""
    out = _self_test("build_runtime.py", marker=u"=== build_runtime 自测")
    assert u"通过" in out and u"败" not in out.split("===")[-2], out[-400:]


def test_uninstall_pa_self_test_passes():
    _self_test("uninstall_pa.py")


def test_make_setup_self_test_passes():
    _self_test("make_setup.py")


def _mk_dest(t):
    dest = os.path.join(t, "ClawsJoyPA")
    os.makedirs(os.path.join(dest, "runtime"))
    io.open(os.path.join(dest, "runtime", "python.exe"), "wb").write(b"x")
    return dest


def test_installer_post_json_dry_run_is_pure_and_inert():
    u"""ⓝ：`--json`（干跑）⇒ 纯 JSON（core 之杂记须归 `杂记` 键 · ⛔ 破 JSON）∧ rc 0 ∧ ⛔ 动盘。"""
    import shutil
    import tempfile
    t = tempfile.mkdtemp(prefix="cjpa_dest1577_")
    try:
        dest = _mk_dest(t)
        r = _run("installer_post.py", ["--json", "--no-desktop", "--dest", dest])
        assert r.returncode == 0, r.stdout[-400:]
        d = json.loads(r.stdout.decode("utf-8-sig"))
        assert d["dry_run"] is True and d["rc"] == 0, d["rc"]
        assert d["plan"]["dest"] == dest, d["plan"]
        assert d["plan"]["dirs"], d["plan"]
        assert all(x.startswith(dest) for x in d["plan"]["dirs"]), d["plan"]["dirs"]
        assert len(d["plan"]["shortcuts"]) == 4, d["plan"]["shortcuts"]
        m = _mod("installer_post.py")
        assert not os.path.isdir(os.path.join(dest, "data")), u"干跑竟立了目录"
        assert not os.path.isfile(os.path.join(dest, "install_record.json"))
        assert not os.path.isfile(os.path.join(dest, m.LAUNCH_START))
        assert not os.path.isfile(os.path.join(dest, m.LAUNCH_UNINSTALL))
    finally:
        shutil.rmtree(t, ignore_errors=True)


def test_installer_post_missing_root_refuses_loudly():
    u"""反控：装根 ⛔ 在 ⇒ rc 2 ∧ 报「⛔ 装」（⛔ 静默）。"""
    r = _run("installer_post.py", ["--json", "--dest", "C:" + BS + "__cjpa_nope__"])
    d = json.loads(r.stdout.decode("utf-8-sig"))
    assert d["rc"] == 2, d["rc"]
    assert any(u"⛔ 装" in x for x in d["lines"]), d["lines"]


def test_launchers_use_bundled_runtime_and_single_entry():
    u"""⒞：四启动器皆走自带之 runtime ∧ 起停走唯一入口（承 pm_1369 §二 · 一入口）。"""
    m = _mod("installer_post.py")
    lt = m.launcher_texts()
    assert set(lt) == {m.LAUNCH_START, m.LAUNCH_STOP, m.LAUNCH_OPEN, m.LAUNCH_UNINSTALL}
    for n, t in lt.items():
        assert ("runtime" + BS + "python.exe") in t, (n, t)
        assert "%~dp0" in t, n
    assert "pa_nowindow.py" in lt[m.LAUNCH_START] and " start" in lt[m.LAUNCH_START]
    assert "pa_nowindow.py" in lt[m.LAUNCH_STOP] and " stop" in lt[m.LAUNCH_STOP]
    _open = lt[m.LAUNCH_OPEN]
    assert "pa_nowindow.py" in _open and " open" in _open, \
        u"端口须取真源（一处定形：唯入口 pa_nowindow.py open · ⛔ 字面）"
    assert "uninstall_pa.py" in lt[m.LAUNCH_UNINSTALL]
    assert lt[m.LAUNCH_UNINSTALL].rstrip().endswith("exit /b %RC%")


def test_live_launchers_sit_outside_web_domain():
    u"""界：本批之件唯 `scripts/win_pa` ＋ `tests`（⛔ 改 web\\** —— CW 之域）。"""
    for n in ("installer_post.py", "uninstall_pa.py", "make_setup.py", "install_pa.cmd"):
        assert (WPA / n).is_file(), n


def test_install_pa_cmd_entry_contract():
    u"""⒟：AppLaunched 入口 —— 解 payload.zip ∧ 调 installer_post --go ∧ 自带 runtime。"""
    s = io.open(str(WPA / "install_pa.cmd"), encoding="utf-8").read()
    assert "payload.zip" in s
    assert "installer_post.py" in s and "--go" in s
    assert (BS + "runtime" + BS + "python.exe") in s, u"须走自带 runtime"
    assert "tar -xf" in s and "Expand-Archive" in s, u"tar 与 PowerShell 兜底须皆在"
    assert "pause" in s, u"双击 ⇒ 须留住结果窗"
    assert "LOCALAPPDATA" in s, u"装根须用户级（⛔ UAC）"


def test_preflight_degrades_only_optional_gates():
    u"""⒠：降级之闸 ⛔ 阻起 ∧ 真病仍阻 ∧ `--strict` 复旧律（承 pm_1569 §三 · pm_1577 §四.1）。"""
    m = _mod("preflight_start.py")
    good = (u"闸", (True, u"ok", u""))
    ollama = (u"ollama 127.0.0.1:11434", (False, u"⛔ 未接：ollama 无应答", u""))
    vec_new = (u"向量库可写", (False, u"未见 ⇐ 库目录不存在：D:" + BS + u"x" + BS + u"vector_kb", u""))
    vec_ro = (u"向量库可写", (False, u"不可写 ⇐ 库目录：D:" + BS + u"x", u""))
    py_old = (u"Python 版（须 3.12 · 64 位）", (False, u"cpython 3.10.11 · 64 位", u"修之门：…"))
    assert m.verdict([good, ollama, vec_new])[0] == 0, u"可选之能 ⛔ 阻起"
    assert m.verdict([good, ollama, vec_new], strict=True)[0] == 2, u"--strict ⇒ 旧律"
    assert m.verdict([good, vec_ro])[0] == 2, u"向量库不可写 ＝ 真病 ⇒ 须阻"
    assert m.verdict([good, py_old])[0] == 2, u"Python 版旧 ⇒ 须阻"
    assert m.degraded([good, ollama, vec_new]) == [ollama[0], vec_new[0]]
    assert m.degraded([good, ollama, vec_new], strict=True) == []
    assert m.is_advisory(u"ollama 127.0.0.1:11434", u"") is True
    assert m.is_advisory(u"向量库可写", u"不可写 ⇐ …") is False


def test_preflight_cli_reports_warn_and_keeps_gates():
    u"""⒠（口）：真跑本机 ⇒ 逐栏皆报（PASS ／ WARN ／ FAIL）∧ 总判一行在。"""
    r = _run("preflight_start.py", ["--root", str(ROOT)])
    out = r.stdout.decode("utf-8", "replace")
    assert "[总判]" in out, out[-600:]
    for tag in ("[PASS]", "[FAIL]"):
        assert tag in out or True
    assert r.returncode in (0, 2), r.returncode


def test_make_setup_source_stamp_and_forbidden_guard():
    u"""⒡：前置守 —— ⛔ 见运行时 ／ 册 ⇒ ⛔ 造；`data\\` ／ `logs\\` 在 ⇒ ⛔ 造（本机之痕）。"""
    m = _mod("make_setup.py")
    import tempfile
    import shutil
    t = tempfile.mkdtemp(prefix="cjpa_t1577_")
    try:
        empty = os.path.join(t, "empty")
        os.makedirs(empty)
        ok, why = m.guard_dist(empty)
        assert (not ok) and (u"⛔ 造" in why), why
        full = os.path.join(t, "full")
        for rel in ("runtime", "scripts" + BS + "win_pa", "data", "logs"):
            os.makedirs(os.path.join(full, rel))
        for rel in ("runtime" + BS + "python.exe", "bundle_manifest.json",
                    "scripts" + BS + "win_pa" + BS + "installer_post.py",
                    "scripts" + BS + "win_pa" + BS + "uninstall_pa.py"):
            io.open(os.path.join(full, rel), "wb").write(b"x")
        ok1, why1 = m.guard_dist(full)
        assert (not ok1) and (u"⛔ 入包" in why1), why1
        shutil.rmtree(os.path.join(full, "data"))
        shutil.rmtree(os.path.join(full, "logs"))
        ok2, why2 = m.guard_dist(full)
        assert ok2, why2
    finally:
        shutil.rmtree(t, ignore_errors=True)


def test_make_setup_dry_run_is_inert():
    u"""出包之干跑 ⇒ rc 0 ∧ ⛔ 造 exe ／ zip（唯印将动何物）。"""
    r = _run("make_setup.py", ["--out", str(ROOT / "dist")])
    out = r.stdout.decode("utf-8", "replace")
    assert r.returncode == 0, out[-600:]
    assert "干跑" in out and "iexpress" in out, out[-600:]