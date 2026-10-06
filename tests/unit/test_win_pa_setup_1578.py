# -*- coding: utf-8 -*-
u"""安装器之壳（pm_1578 即刻办）之测：三症之**根**与**防**。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_win_pa_setup_1578.py -q

三症（老板之屏 · 我一手复现）：
  ⅌ 控制台中文皆乱码   ⅍ cmd 把中文字节当命令（`@?` ⁄ `搻` ⁄ `ClawsJoy`）
  ⅎ 一快捷建立败（ps1 之编码）
根（**同一族**）：★ cmd.exe 依**控制台之码页**解 `.cmd` 之**字节**；★ PS 5.1 依 **ANSI** 解
  无 BOM 之 UTF-8 `.ps1`；两处皆因「UTF-8 之 CJK 字节 ↔ DBCS 错配」而**吞字节**
  （Windows 之 DBCS 解于次字节非法时**吞二字节** ⇒ 吞 `\r` （行碎）⁄ `^`（转义破）⁄ `'`（引号缺））。

本测之齿：
  正控：新形之 `.cmd` ⁄ `.ps1` 尽 ASCII ＋ 真台（936）跑 ⇒ ⛔ 错 ∧ 至 `[3/3]`；新形之 ps1 ＋
        UTF-8 JSON 建快捷 ⇒ 成 ∧ 目标逐字对
  反控：旧形（.cmd 之 UTF-8 CJK ⁄ .ps1 之 UTF-8 无 BOM）⇒ 必乱 ∧ 必败
⛔ 触老板之台（唯 tmp）｜⛔ 起服｜⛔ 出真包。
"""
import ctypes
import ctypes.wintypes as W
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WPA = ROOT / "scripts" / "win_pa"
BS = chr(92)


def _mod(name):
    spec = importlib.util.spec_from_file_location("_m1578_" + name.replace(".", "_"), str(WPA / name))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _run(name, args, timeout=600):
    return subprocess.run([sys.executable, "-X", "utf8", "-B", str(WPA / name)] + list(args),
                          capture_output=True, cwd=str(ROOT), timeout=timeout)


def _self_test(name, marker="[self-test] PASS"):
    r = _run(name, ["--self-test"])
    out = r.stdout.decode("utf-8", "replace")
    assert r.returncode == 0, (name, r.returncode, out[-1200:])
    assert marker in out, (name, out[-600:])
    return out


# ── 真台（隐之控制台 · 本机之默认码页 936）之器 ──────────────────────────────
k32 = ctypes.WinDLL("kernel32", use_last_error=True)


class _SI(ctypes.Structure):
    _fields_ = [("cb", W.DWORD), ("lpReserved", W.LPWSTR), ("lpDesktop", W.LPWSTR),
                ("lpTitle", W.LPWSTR), ("dwX", W.DWORD), ("dwY", W.DWORD),
                ("dwXSize", W.DWORD), ("dwYSize", W.DWORD), ("dwXCountChars", W.DWORD),
                ("dwYCountChars", W.DWORD), ("dwFillAttribute", W.DWORD), ("dwFlags", W.DWORD),
                ("wShowWindow", W.WORD), ("cbReserved2", W.WORD),
                ("lpReserved2", ctypes.POINTER(ctypes.c_byte)), ("hStdInput", W.HANDLE),
                ("hStdOutput", W.HANDLE), ("hStdError", W.HANDLE)]


class _PI(ctypes.Structure):
    _fields_ = [("hProcess", W.HANDLE), ("hThread", W.HANDLE),
                ("dwProcessId", W.DWORD), ("dwThreadId", W.DWORD)]


class _COORD(ctypes.Structure):
    _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]


class _RECT(ctypes.Structure):
    _fields_ = [("Left", ctypes.c_short), ("Top", ctypes.c_short),
                ("Right", ctypes.c_short), ("Bottom", ctypes.c_short)]


class _CSBI(ctypes.Structure):
    _fields_ = [("dwSize", _COORD), ("dwCursorPosition", _COORD), ("wAttributes", ctypes.c_ushort),
                ("srWindow", _RECT), ("dwMaximumWindowSize", _COORD)]


def _read_console(pid, width=240):
    k32.FreeConsole()
    if not k32.AttachConsole(W.DWORD(pid)):
        return None
    h = k32.CreateFileW("CONOUT$", 0x40000000 | 0x80000000, 3, None, 3, 0, None)
    if h == W.HANDLE(-1).value:
        k32.FreeConsole()
        return None
    info = _CSBI()
    if not k32.GetConsoleScreenBufferInfo(W.HANDLE(h), ctypes.byref(info)):
        k32.FreeConsole()
        return None
    rows = []
    for y in range(0, info.dwCursorPosition.Y + 2):
        buf = ctypes.create_unicode_buffer(width)
        got = W.DWORD(0)
        k32.ReadConsoleOutputCharacterW(W.HANDLE(h), buf, width, _COORD(0, y), ctypes.byref(got))
        rows.append(buf[:got.value].rstrip())
    k32.CloseHandle(W.HANDLE(h))
    k32.FreeConsole()
    return "\n".join(rows)


def run_in_hidden_console(workdir, cmd_path, wait=1.8):
    u"""在**隐之真台**（本机之默认码页）里跑一件 .cmd，还其屏之文。
    ⭐ 此即「净机之代」：控制台之码页与老板之台同個 ⇒ cmd 解 .cmd 之字节之法同。"""
    si = _SI()
    si.cb = ctypes.sizeof(si)
    si.dwFlags = 0x1
    si.wShowWindow = 0
    pi = _PI()
    cl = ctypes.create_unicode_buffer(u'cmd /c "%s"' % cmd_path)
    if not k32.CreateProcessW(None, cl, None, None, False, 0x10, None, workdir,
                              ctypes.byref(si), ctypes.byref(pi)):
        pytest.skip(u"⛔ 得真台（CreateProcess err=%d）⇒ 本机之代 · 未验之项" % ctypes.get_last_error())
    time.sleep(wait)
    txt = None
    last = 0
    for _ in range(10):
        txt = _read_console(pi.dwProcessId)
        if txt:
            break
        last = ctypes.get_last_error()
        time.sleep(0.5)
    k32.TerminateProcess(pi.hProcess, 0)
    k32.CloseHandle(pi.hProcess)
    k32.CloseHandle(pi.hThread)
    if txt is None:
        pytest.skip(u"⛔ 读台（AttachConsole 被拒）⇒ 本机之代 · 本件未验")
    return txt


# ── 正控：新形 ──────────────────────────────────────────────────────

def test_installer_post_self_test_passes():
    _self_test("installer_post.py")


def test_make_setup_self_test_passes():
    _self_test("make_setup.py")


def test_pa_msg_self_test_passes():
    _self_test("pa_msg.py")


def test_launchers_ascii_and_prologue():
    m = _mod("installer_post.py")
    lt = m.launcher_texts()
    assert set(lt) == {m.LAUNCH_START, m.LAUNCH_STOP, m.LAUNCH_OPEN, m.LAUNCH_UNINSTALL}
    for name, t in lt.items():
        bad = sorted({c for c in t if ord(c) > 127})
        assert not bad, (name, bad)
        assert t.startswith(m.CMD_PROLOGUE), name
        assert t.count("\n") == t.count("\r\n"), name
    assert "chcp 65001" in m.CMD_PROLOGUE


def test_install_pa_cmd_ascii_and_same_prologue():
    u"""入口之字节尽 ASCII ∧ 其头 ≡ CMD_PROLOGUE（**一处定形** · ⛔ 二源）。"""
    m = _mod("installer_post.py")
    b = (WPA / "install_pa.cmd").read_bytes()
    assert not [x for x in b if x > 127], (WPA / "install_pa.cmd")
    txt = b.decode("ascii")
    assert txt.startswith(m.CMD_PROLOGUE)
    assert txt.count("\n") == txt.count("\r\n")
    for needle in ("installer_post.py", "payload.zip", "tar -xf", "Expand-Archive", "chcp 65001"):
        assert needle in txt, needle


def test_sed_text_is_ascii():
    m = _mod("make_setup.py")
    sed = m.sed_text("C:" + BS + "stage" + BS, "C:" + BS + "out" + BS + "X.exe")
    assert not sorted({c for c in sed if ord(c) > 127})


def test_ps_lnk_script_ascii_and_specs():
    m = _mod("installer_post.py")
    assert not sorted({c for c in m.PS_LNK_SCRIPT if ord(c) > 127})
    assert ",0" not in m.PS_LNK_SCRIPT
    spec = m.shortcut_specs("C:" + BS + "x")
    assert len(spec) == 7
    assert len({r["lnk"] for r in spec}) == 7
    for r in spec:
        assert not r["icon"].endswith(",0")
        assert r["icon"].endswith("python.exe")
        assert r["target"].endswith(".cmd")


def _q(s):
    return u"'" + str(s).replace(u"'", u"''") + u"'"


def _ps_file(script_text, encoding, extra=()):
    fd, ps1 = tempfile.mkstemp(prefix="cjpa_t_", suffix=".ps1")
    os.close(fd)
    try:
        with io.open(ps1, "w", encoding=encoding, newline="") as fh:
            fh.write(script_text)
        return subprocess.run(["powershell", "-NoProfile", "-NonInteractive",
                               "-ExecutionPolicy", "Bypass", "-File", ps1] + list(extra),
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
    finally:
        os.remove(ps1)


def _old_style_ps(root, out, names):
    u"""旧形：.ps1 之字面含 CJK（无 BOM 之 UTF-8 写）—— 即当日之壳。"""
    ps = [u"$sh = New-Object -ComObject WScript.Shell"]
    for name, target, desc in names:
        lnk = os.path.join(out, name + u".lnk")
        ps.append(u"$s = $sh.CreateShortcut(%s)" % _q(lnk))
        ps.append(u"$s.TargetPath = %s" % _q(os.path.join(root, target)))
        ps.append(u"$s.WorkingDirectory = %s" % _q(root))
        ps.append(u"$s.Description = %s" % _q(desc))
        ps.append(u"$s.IconLocation = %s" % _q(os.path.join(root, u"runtime", u"python.exe") + u",0"))
        ps.append(u"$s.Save()")
    return u"\r\n".join(ps) + u"\r\n"



def _short_tmp(tag):
    u"""短沙箱：窗之路径上限 260 字 ⇒ tmp_path 太深时快捷之名必溢。"""
    base = os.path.join(tempfile.gettempdir(), "cjpa1578")
    os.makedirs(base, exist_ok=True)
    return tempfile.mkdtemp(prefix=tag + "_", dir=base)


SPECS = ((u"启动 ClawsJoy PA", u"启动ClawsJoyPA.cmd", u"起 PA 网关（无窗）"),
         (u"停止 ClawsJoy PA", u"停止ClawsJoyPA.cmd", u"停 PA 网关"),
         (u"打开 ClawsJoy PA 页面", u"打开ClawsJoyPA页面.cmd", u"在默认浏览器开 PA 页面"),
         (u"卸载 ClawsJoy PA", u"卸载ClawsJoyPA.cmd", u"卸载（data 保留）"))


def test_new_ps1_json_makes_shortcuts_verbatim(tmp_path):
    tmp_path = _short_tmp("test_new_ps1_j")
    u"""正控：新形（ASCII .ps1 ＋ UTF-8 JSON）⇒ 成 ∧ 目标 ⁄ 说明 **逐字对**（CJK 不变）。"""
    m = _mod("installer_post.py")
    root = os.path.join(tmp_path, "root")
    out = os.path.join(tmp_path, "out")
    os.makedirs(root, exist_ok=True)
    os.makedirs(out, exist_ok=True)
    spec = [{"lnk": os.path.join(out, n + u".lnk"), "target": os.path.join(root, t),
             "workdir": root, "desc": d, "icon": os.path.join(root, u"runtime", u"python.exe")}
            for n, t, d in SPECS]
    fd, sj = tempfile.mkstemp(prefix="cjpa_t_", suffix=".json")
    os.close(fd)
    try:
        with io.open(sj, "w", encoding="utf-8", newline="") as fh:
            fh.write(json.dumps(spec, ensure_ascii=False))
        r = _ps_file(m.PS_LNK_SCRIPT, "utf-8-sig", ["-Spec", sj])
        assert r.returncode == 0, (r.returncode, r.stderr[-400:])
        back = json.loads(r.stdout.strip())
        assert isinstance(back, list) and len(back) == len(spec)
        for want in spec:
            got = [b for b in back if b["lnk"] == want["lnk"]]
            assert got, want["lnk"]
            b = got[0]
            assert b["target"] == want["target"], (b["target"], want["target"])
            assert b["workdir"] == want["workdir"]
            assert b["desc"] == want["desc"], (b["desc"], want["desc"])
            assert m._icon_path(b["icon"]) == want["icon"], b["icon"]
            assert os.path.isfile(want["lnk"])
    finally:
        os.remove(sj)


def test_old_ps1_utf8_nobom_fails(tmp_path):
    tmp_path = _short_tmp("test_old_ps1_u")
    u"""反控：旧形（UTF-8 无 BOM 之 .ps1 含 CJK）⇒ **必敗**（证病在 · PS 5.1 依 ANSI 解）。"""
    root = os.path.join(tmp_path, "root")
    out = os.path.join(tmp_path, "out")
    os.makedirs(root, exist_ok=True)
    os.makedirs(out, exist_ok=True)
    r = _ps_file(_old_style_ps(root, out, SPECS), "utf-8")
    assert r.returncode != 0, (r.returncode, r.stdout[-200:])
    assert u"字符串缺少终止符" in (r.stderr or u"") or u"missing the terminator" in (r.stderr or u"")
    assert not [f for f in os.listdir(out) if f.endswith(".lnk")]


# ── 真台（本机默认码页）下之正 ⁄ 反二控 ──────────────────────────────────

#: 旧形（当日之头 · UTF-8 无 BOM · 含 CJK）—— 其错自 `rem ⭐` 行起（我一手：前行以 `。` 收 ∧ 下行含非 ASCII ⇒ 行碎）
_OLD_HEAD_LINES = [
    u"@echo off",
    u"setlocal EnableExtensions",
    u"rem ============================================================",
    u"rem  ClawsJoyPA-Setup.exe（iexpress 自解压）之 AppLaunched 入口（承 pm_1577 §二.3 ／ §三.3）",
    u"rem",
    u"rem  位次：iexpress 把本件 ＋ payload.zip 解到 TEMP 之 IXP 夹 ⇒ 以本目录为 CWD 跑本件。",
    u"rem        ⭐ 故本件：ⓐ tar 解 payload.zip 入装根  ⓑ 以**自带之 runtime** 跑 installer_post.py",
    u"rem",
    u"echo BANNER-OLD",
    u"pause",
    u"endlocal & exit /b 0",
]


def _old_head_bytes():
    return b"\r\n".join(l.encode("utf-8") for l in _OLD_HEAD_LINES) + b"\r\n"


def _mk_sandbox(base, cmd_bytes, name="install_pa.cmd"):
    sb = os.path.join(base, "sb")
    os.makedirs(sb, exist_ok=True)
    with io.open(os.path.join(sb, name), "wb") as fh:
        fh.write(cmd_bytes)
    import zipfile
    with zipfile.ZipFile(os.path.join(sb, "payload.zip"), "w") as z:
        z.writestr("scripts/win_pa/x.txt", "hi")
    return sb


def test_new_install_pa_cmd_is_clean_on_gbk_console(tmp_path):
    u"""正控：真台（本机默认码页 · 936）跑新形之 `install_pa.cmd` ⇒
    ⛔「不是内部或外部命令」之行碎 ∧ ⛔ 乱码 ∧ 跑至 `[3/3]`。
    ⭐ 注：`[2/3]` 处的 `runtime\\python.exe` 故意⛔ 存（⛔ 借系统 python）⇒ 其 rc 非 0 属常。"""
    sb = _mk_sandbox(str(tmp_path), (WPA / "install_pa.cmd").read_bytes())
    dest = os.path.join(str(tmp_path), "dest")
    old = os.environ.get("CJPA_DEST")
    os.environ["CJPA_DEST"] = dest
    try:
        txt = run_in_hidden_console(sb, os.path.join(sb, "install_pa.cmd"))
    finally:
        if old is None:
            os.environ.pop("CJPA_DEST", None)
        else:
            os.environ["CJPA_DEST"] = old
    assert "[1/3] unpacking program + bundled runtime" in txt, txt[:600]
    assert "[2/3] creating folders / shortcuts" in txt, txt[:600]
    assert "[3/3] result rc=" in txt, txt[:600]
    assert u"语法不正确" not in txt, txt[:600]
    assert u"不是内部或外部命令" not in txt, txt[:600]
    assert u"应当在" not in txt


def test_bundled_python_prints_cjk_on_gbk_console(tmp_path):
    u"""正控（守三之据）：真台（936）下，自带 Python 之 CJK 辞 ⇒ ⛔ 乱
    （写走 WriteConsoleW · ⛔ 依码页）—— 此即「cmd 之字面尽 ASCII ∧ 人话之辞交 Python」之据。
    ⭐ 以系统 python 代之（同 CPython 之 WindowsConsoleIO · 其法同一）。"""
    base = _short_tmp("test_py_cjk")
    sb = os.path.join(base, "sb")
    os.makedirs(sb, exist_ok=True)
    script = os.path.join(sb, "hi.py")
    with io.open(script, "w", encoding="utf-8", newline="") as fh:
        fh.write(u"import sys\nsys.stdout.reconfigure(encoding='utf-8', errors='replace')\n"
                 u"print(u'CJK-A \\u4e2d\\u6587 B')\n")
    with io.open(os.path.join(sb, "t.cmd"), "wb") as fh:
        fh.write(b"@echo off\r\nchcp 65001 >nul\r\n"
                 + (u'"%s" -X utf8 "%s"\r\npause\r\n' % (sys.executable, script)).encode("ascii"))
    txt = run_in_hidden_console(sb, os.path.join(sb, "t.cmd"), wait=2.0)
    assert u"\u4e2d\u6587" in txt, txt[:400]


def test_old_style_cmd_breaks_on_gbk_console(tmp_path):
    u"""反控：同台跑旧形（UTF-8 之 CJK 在 .cmd 里）⇒ **必出行碎之错**（证病在）。"""
    b = _old_head_bytes()
    assert any(x > 127 for x in b) and not b.startswith(b"\xef\xbb\xbf")
    sb = _mk_sandbox(str(tmp_path), b, name="old_form.cmd")
    txt = run_in_hidden_console(sb, os.path.join(sb, "old_form.cmd"))
    assert u"不是内部或外部命令" in txt, txt[:600]
    assert ("'m'" in txt) or (u"搻" in txt), txt[:600]
