# -*- coding: utf-8 -*-
u"""pm_1628 §二.1 令一（卸载器 exe）之齿 —— 「应用与功能」之卸载项 = **exe**（技术总监席 f202f89 · 2026-10-07）。

一事：`make_uninstaller.py` 于**构建期**以 csc 编 `卸载ClawsJoyPA.exe`（每用户 · ⛔ 提权）；
  `installer_post.uninstall_program()` ⇒ exe 在取 exe，⛔ 在兜底 `.cmd`（仍可卸 · ⛔ 断）。

以何形调用（判通 ／ 断须附）：
  python -X utf8 -B -m pytest tests/unit/test_win_pa_uninstaller_1628.py -q

判据：
  ⒜ 器之 `--self-test` ⇒ rc 0 ∧ PASS
  ⒝ 正控：干跑 ⇒ rc 0 ∧ ⛔ 编出 exe ∧ 印「干跑」（⛔ 动盘）
  ⒞ 反控：`--csc <⛔ 在>` ⇒ rc 2 ∧ **人话之因**（⛔ 静默）｜装根 ⛔ 在 ⇒ rc 2
  ⒟ 一处定形：`make_uninstaller.EXE_NAME` ≡ `installer_post.UNINSTALL_EXE`
  ⒠ 正反控：`uninstall_program` —— exe 在 ⇒ exe；拔之 ⇒ `.cmd`（兜底）
  ⒡ 正控（csc 在则真编）：exe 为 **PE ∧ 子系统 = GUI(2)** ∧ 含 **CLR（mscoree）**（＝ 无窗之窗程序）
⛔ 起停 ｜ ⛔ 跑 exe（其有确认框 ＋ 真卸）｜⛔ 触净机。
"""
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WPA = ROOT / "scripts" / "win_pa"
if str(WPA) not in sys.path:
    sys.path.insert(0, str(WPA))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _mod(name):
    spec = importlib.util.spec_from_file_location("_m1628u_" + name.replace(".", "_"), str(WPA / name))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _run(args, timeout=300):
    return subprocess.run([sys.executable, "-X", "utf8", "-B", str(WPA / "make_uninstaller.py")] + list(args),
                          capture_output=True, cwd=str(ROOT), timeout=timeout)


def _tree(t):
    os.makedirs(os.path.join(t, "runtime"), exist_ok=True)
    with io.open(os.path.join(t, "runtime", "python.exe"), "wb") as fh:
        fh.write(b"x")
    return t


def test_self_test_passes():
    u"""⒜：器自带之反控（⛔ 离机 · ⛔ 编译）。"""
    r = _run(["--self-test"])
    out = r.stdout.decode("utf-8", "replace")
    assert r.returncode == 0, (r.returncode, out[-800:])
    assert "[self-test] PASS" in out, out[-400:]


def test_正控_干跑不落件():
    u"""⒝：干跑 ⇒ rc 0 ∧ ⛔ 编出 exe（⛔ 动盘）。"""
    t = tempfile.mkdtemp(prefix="cjpa_un1628_")
    try:
        _tree(t)
        r = _run(["--dest", t])
        out = r.stdout.decode("utf-8", "replace")
        assert r.returncode == 0, (r.returncode, out[-600:])
        m = _mod("make_uninstaller.py")
        assert not os.path.isfile(os.path.join(t, m.EXE_NAME)), u"干跑竟编了 exe"
        assert u"干跑" in out, out[-400:]
    finally:
        shutil.rmtree(t, ignore_errors=True)


def test_反控_无csc与无装根皆人话():
    u"""⒞：前置 ⛔ 足 ⇒ rc 2 ∧ 因（⛔ 静默）。"""
    t = tempfile.mkdtemp(prefix="cjpa_un1628n_")
    try:
        _tree(t)
        r = _run(["--go", "--dest", t, "--csc", "C:" + chr(92) + "__nope__" + chr(92) + "csc.exe"])
        out = r.stdout.decode("utf-8", "replace")
        assert r.returncode == 2 and u"⛔ 在" in out, (r.returncode, out[-400:])
        r2 = _run(["--go", "--dest", "C:" + chr(92) + "__cjpa_nope__"])
        out2 = r2.stdout.decode("utf-8", "replace")
        assert r2.returncode == 2 and u"⛔ 见装根" in out2, (r2.returncode, out2[-400:])
    finally:
        shutil.rmtree(t, ignore_errors=True)


def test_一处定形_exe之名():
    u"""⒟：exe 之名唯二处（器 ⟷ 安装之后置）⇒ 以器核（⛔ 二处漂）。"""
    mu = _mod("make_uninstaller.py")
    ip = _mod("installer_post.py")
    assert mu.EXE_NAME == ip.UNINSTALL_EXE, (mu.EXE_NAME, ip.UNINSTALL_EXE)


def test_正反控_卸载器之取():
    u"""⒠：exe 在 ⇒ 取 exe（人验之口）；拔之 ⇒ `.cmd`（兜底 · 仍可卸）。"""
    t = tempfile.mkdtemp(prefix="cjpa_un1628p_")
    try:
        _tree(t)
        ip = _mod("installer_post.py")
        assert ip.uninstall_program(t)[1] == u"cmd", u"⛔ 在 exe ⇒ 须兜底 cmd"
        with io.open(os.path.join(t, ip.UNINSTALL_EXE), "wb") as fh:
            fh.write(b"x")
        p, kind = ip.uninstall_program(t)
        assert kind == u"exe" and p == os.path.join(t, ip.UNINSTALL_EXE), (p, kind)
        vals = {k: v for k, _t, v in ip.uninstall_values(t)}
        assert vals[u"UninstallString"].strip(u'"') == p, vals[u"UninstallString"]
        # 静默之口（pm_1632 §五.1 我一手核之修）：exe 在 ⇒ 引之 ＋ `--yes`（**⛔ 弹框**）；
        #   旧貌恒指 `.cmd`（其有 pause ⇒ 与「静默」之名 ⛔ 符）。
        assert vals[u"QuietUninstallString"] == u'"' + p + u'" --yes', vals[u"QuietUninstallString"]
        os.remove(p)                                              # 反控：拔 exe ⇒ 兜底 .cmd
        assert ip.quiet_uninstall_program(t) == u'"' + os.path.join(t, ip.LAUNCH_UNINSTALL) + u'"', \
            ip.quiet_uninstall_program(t)
    finally:
        shutil.rmtree(t, ignore_errors=True)


def _pe(path):
    b = io.open(path, "rb").read()
    assert b[:2] == b"MZ", u"非 PE"
    off = int.from_bytes(b[0x3C:0x40], "little")
    assert b[off:off + 4] == b"PE\0\0", u"无 PE 头"
    opt = off + 24
    return b, int.from_bytes(b[opt:opt + 2], "little"), int.from_bytes(b[opt + 68:opt + 70], "little")


def test_正控_真编且为GUI托管件():
    u"""⒡：csc 在 ⇒ 真编 ⇒ **PE ∧ 子系统 GUI(2) ∧ 含 CLR**（＝ 无控制台之托管窗程序）。
    ⚠ 唯编 ／ 唯读字节 —— **⛔ 跑**（其有确认框 ＋ 真卸）。"""
    mu = _mod("make_uninstaller.py")
    csc, _n = mu.find_csc()
    if not csc:
        return                                    # 本机无 csc ⇒ 器已明书兜底（⛔ 假绿之由在 self-test）
    t = tempfile.mkdtemp(prefix="cjpa_un1628b_")
    try:
        _tree(t)
        rc, rows = mu.build(t, dry=False)
        assert rc == 0, rows
        exe = os.path.join(t, mu.EXE_NAME)
        assert os.path.isfile(exe) and os.path.getsize(exe) > 1024
        b, magic, sub = _pe(exe)
        assert magic in (0x10b, 0x20b), hex(magic)
        assert sub == 2, u"子系统须 GUI(2)（无控制台之窗）实=%s" % sub
        assert b"mscoree" in b, u"须为 CLR 托管件（csc 之出）"
    finally:
        shutil.rmtree(t, ignore_errors=True)
