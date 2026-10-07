# -*- coding: utf-8 -*-
u'''「CMD 闪屏」之齿（pm_1862 ／ pm_1865 §三.1）—— 技术总监席 f202f89 · 2026-10-08。

以何形调用：
  python -X utf8 -B -m pytest tests/unit/test_flash_1862.py -q

本档所验（**皆静态可判** · ⛔ 起进程 ／ ⛔ 起停服务 —— 「可见窗 0」之终判归 PM 之四路复量）：
  正控 1：热路器之**窗隐出口**真在（`scripts/win_pa/_proc.py` 载得真源 ⇒ `run_hidden` 真跑成）；
  正控 2：任务之形 —— `install_win_pa.task_items()` 之二动作皆经**静默壳**
          （`wscript.exe` ＋ `静默启动.vbs`）· ⛔ 兜 `cmd` ／ ⛔ 裸 `python.exe`；
  正控 3：壳之件在 ∧ **纯 ASCII**（WSH 按机器 ANSI 页读 `.vbs` ⇒ 非 ASCII 必各机异解）；
  反控 4：逐热路器扫「裸 spawn」—— 造一处裸调之样件 ⇒ 扫描器**必咬**（⛔ 尺为瞎 · 承 11_实验室 K-74）；
  反控 5：真源之旗真**并**（`merge_flags` ⛔ 覆盖 ∧ ⛔ 丢既有旗）；
  反控 6：陈旧豁免 ⇒ 红（豁免表之每一条须仍**命中**热路器 —— ⛔ 使后世之豁免成空文）。
'''
import importlib.util
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WINPA = os.path.join(ROOT, "scripts", "win_pa")
AGENT = os.path.join(ROOT, "scripts", "agent_client")

#: 热路器 —— **可能由无控制台之父**起（任务宿主 `svchost` ／ `pa_update` 之 detached 器 ／
#:   网关之 detached 器）⇒ 凡 spawn **必带窗隐**（此即本档之尺）。
HOT = (
    "scripts/win_pa/_proc.py",
    "scripts/win_pa/netmachine_check.py",
    "scripts/win_pa/pa_update.py",
    "scripts/win_pa/install_win_pa.py",
    "scripts/win_pa/boot_resume.py",
    "scripts/win_pa/pa_nowindow.py",
    "scripts/agent_client/local_actions.py",
    "scripts/agent_client/computer_use.py",
)
#: ⛔ 入本案之件（**附因** · ⛔ 静默剔 —— 照实）：
NOT_HOT = {
    "scripts/win_pa/uninstall_pa.py":
        u"卸载器恒由**可见之控制台**起（开始菜单之 cmd）⇒ 子承其控制台 ⇒ ⛔ 新开窗之因；"
        u"其 `spawn_cleanup` 之 detached `cmd /c` ＋ 批内 `ping` 为**另案**（已报 PM · ⛔ 本批动）",
    "scripts/win_pa/installer_post.py":
        u"装程之尾（`install_pa.cmd` 之**可见控制台**下跑）⇒ 子承其控制台 ⇒ ⛔ 闪",
    "scripts/win_pa/make_payload.py": u"打包器（人于控制台手跑）",
    "scripts/win_pa/make_update.py": u"出包器（人于控制台手跑）",
    "scripts/win_pa/make_client_bundle.py": u"出包器（人于控制台手跑）",
    "scripts/win_pa/build_runtime.py": u"构建器（人于控制台手跑）",
}
#: 逐条**豁免**（明书之例外 · ⛔ 静默兜底）—— 其行须**逐字**命中此表方为合规。
EXEMPT = (
    (u"subprocess.Popen(cmd, **merge_flags(kw))",
     u"`_proc.py` 自身之**本地等价支**（`Popen` 之一面 · 同上）"),
    (u"subprocess.run(cmd, **merge_flags(kw))",
     u"`_proc.py` 自身之**本地等价支**（旗由其上一行之 `merge_flags` 并）"),
    (u"subprocess.run(cmd, **kw)",
     u"各器之**本地等价支**（上一行即 `creationflags` 之并 · 真源载不到时之退路）"),
    (u"subprocess.run(cmd).returncode",
     u"装器之 pip —— **用户须见其进度** ∧ 装器恒在**可见控制台**中 ⇒ ⛔ 闪（pm_1865 之一处例外）"),
)
SPAWN = re.compile(r"(?<![\w.])subprocess\s*\.\s*(run|Popen|call|check_output|check_call)\s*\(")
#: 窗隐之旗（**行内或续行**明载）—— 合规之第二路：`creationflags=` ＋ 三字之一。
#:  ⚠ ⛔ 认 `creationflags=0` 之**空旗**（⛔ 旗 ＝ 无旗 ⇒ 该行仍咬）。
HIDE_FLAG = re.compile(r"creationflags\s*=[^\n]*(CREATE_NO_WINDOW|\bNO_WINDOW\b|\bFLAGS\b)"
                       r"|(CREATE_NO_WINDOW|\bNO_WINDOW\b|\bFLAGS\b)[^\n]*creationflags\s*=")


def _offenders(text):
    u"""⇒ 未被豁免之裸 spawn 之行表 `[(行号, 行文)]`（⛔ 空 ⇒ 静默）。

    一行「合规」之二路（余者咬）：
      ① 命中 `EXEMPT` 之**逐字**例外（本地等价支 ／ 装器之 pip 例外）；
      ② 该行**或其续行**明载窗隐之旗（`creationflags=` ＋ `CREATE_NO_WINDOW` ／ `NO_WINDOW` ／ `FLAGS`）。
    """
    lines = text.splitlines()
    out = []
    for i, ln in enumerate(lines, 1):
        if not SPAWN.search(ln):
            continue
        if any(e in ln for e, _why in EXEMPT):
            continue
        win = " ".join(lines[i - 1:i + 2])   # 本行 ＋ 续行（至多 2）—— 本仓之调用形皆在三行内
        if HIDE_FLAG.search(win):
            continue
        out.append((i, ln.strip()))
    return out


def _read(rel):
    return io.open(os.path.join(ROOT, rel), encoding="utf-8").read()


def _by_path(rel, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, rel))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ---------------------------------------------------------------- 反控 4：尺之牙
def test_reverse_control_scanner_bites_a_bare_spawn():
    u"""造一处**裸调** ⇒ 扫描器必咬；并造一处**已隐**之形 ⇒ ⛔ 咬（真阴／真阳皆验）。"""
    bare = u"def f():\n    r = subprocess.run(['nvidia-smi'], capture_output=True)\n    return r\n"
    got = _offenders(bare)
    assert len(got) == 1, u"尺为瞎：裸调未被咬 ⇒ %r" % (got,)
    assert got[0][0] == 2
    hidden = u"def f():\n    r = run_hidden(['nvidia-smi'], capture_output=True)\n    return r\n"
    assert _offenders(hidden) == [], u"假阳：已隐之形竟被咬"
    # ⚠ **空旗**（`creationflags=0`）⛔ 得充「已隐」—— 否则尺又瞎（承 K-74 之族）
    empty = u"def f():\n    r = subprocess.run(['nvidia-smi'], creationflags=0)\n    return r\n"
    assert len(_offenders(empty)) == 1, u"空旗竟被认作已隐 ⇒ 尺为瞎"
    # 真旗之形（行内）⇒ ⛔ 咬
    flagged = u"def f():\n    r = subprocess.run(['x'], creationflags=subprocess.CREATE_NO_WINDOW)\n"
    assert _offenders(flagged) == [], u"假阳：明载真旗之形被咬"
    # 真旗在**续行**（多行之 call）⇒ ⛔ 咬（续行须入判）
    multi = (u"def f():\n    r = subprocess.run(['x'],\n"
             u"                       creationflags=subprocess.CREATE_NO_WINDOW)\n")
    assert _offenders(multi) == [], u"续行之真旗 ⛔ 认 ⇒ 假阳"


def test_hot_path_spawns_are_all_window_hidden():
    u"""正控（本档之主力）：逐热路器 ⇒ ⛔ 有裸 spawn（豁免者除外）。"""
    bad = {}
    for rel in HOT:
        o = _offenders(_read(rel))
        if o:
            bad[rel] = o
    assert not bad, u"热路器之裸 spawn（必致无控制台之父下**新开**控制台窗）：%s" % bad


def test_exemptions_are_not_stale():
    u"""反控 6：豁免表之每条须仍命中某热路器 —— 陈旧豁免 ⇒ **红**（⛔ 空文）。"""
    joined = "\n".join(_read(r) for r in HOT)
    stale = [e for e, _w in EXEMPT if e not in joined]
    assert not stale, u"陈旧豁免（⛔ 命中任何热路器）：%s" % stale


# ---------------------------------------------------------------- 正控 1：窗隐出口
def test_win_pa_proc_is_real_and_merges_flags():
    u"""`scripts/win_pa/_proc.py`：真源载得 ＋ `run_hidden` 真跑 ＋ 旗真并。"""
    m = _by_path("scripts/win_pa/_proc.py", "_proc_flash_t")
    assert m.CORE_PROC is not None, u"真源 `core/pa/_proc.py` ⛔ 载得（窗隐无真源）"
    r = m.run_hidden([sys.executable, "-c", "print(7*6)"], capture_output=True, text=True)
    assert r.returncode == 0 and (r.stdout or "").strip() == "42", u"run_hidden 真跑：%r" % (r,)
    assert m.merge_flags({})["creationflags"] & m.NO_WINDOW
    _m = m.merge_flags({"creationflags": 0x08000000})["creationflags"]
    assert _m & m.NO_WINDOW and _m & 0x08000000, u"旗未并（或丢既有旗）：0x%x" % _m


def test_agent_client_spawns_use_the_same_exit():
    u"""agent_client 之二热路器：其 `run_hidden` 真指**真源**（⛔ 退本地等价）。"""
    for rel in ("scripts/agent_client/local_actions.py", "scripts/agent_client/computer_use.py"):
        m = _by_path(rel, "_ag_" + os.path.basename(rel))
        assert m._PROC is not None, u"%s：真源 ⛔ 载得（退路为瞎）" % rel


# ---------------------------------------------------------------- 正控 2／3：任务之形
def test_task_actions_go_through_the_silent_shell():
    u"""`task_items()` 之二动作：首 token ＝ `wscript.exe` ∧ 载**静默壳** ∧ ⛔ 裸 `cmd` ／ 裸 `python.exe`。"""
    m = _by_path("scripts/win_pa/install_win_pa.py", "_iwp_flash_t")
    items = m.task_items()
    assert {t["name"] for t in items} == {"\\ClawsJoy_PA_Boot", "\\ClawsJoy_PA_Start_Once"}
    for t in items:
        cmd = t["cmd"]
        assert cmd.split()[0].lower() == "wscript.exe", u"首 token ⛔ wscript：%s" % cmd
        assert "静默启动.vbs" in cmd, u"⛔ 经静默壳：%s" % cmd
        assert not any(x in cmd for x in (' "cmd" ', " cmd.exe ", '"cmd.exe"'))
        assert t["cmd"].startswith("wscript.exe //B "), cmd
        # 壳所起者须为**解释器 ＋ 脚本**（此二者之窗由壳之 SW_HIDE 隐）
        av = t["cmd_argv"]
        assert av[0].lower().endswith(("python.exe", "pythonw.exe")), av
        assert av[-1].endswith(("boot_resume.py", "start")), av


def test_silent_shell_file_exists_and_is_pure_ascii():
    u"""壳之件在 ∧ 纯 ASCII ∧ 其核心句仍**逐字**（`sh.Run(cmd, 0, True)` ＝ SW_HIDE）。"""
    p = os.path.join(WINPA, "静默启动.vbs")
    assert os.path.isfile(p), u"⛔ 在：%s" % p
    raw = io.open(p, "rb").read()
    assert raw, u"空件：%s" % p
    bad = [b for b in raw if b > 127]
    assert not bad, u".vbs 须**纯 ASCII**（WSH 按机器 ANSI 页读）⇒ 非 ASCII 字节 %d 枚" % len(bad)
    t = raw.decode("ascii")
    assert "sh.Run(cmd, 0, True)" in t, u"核心句之形变了（SW_HIDE ＋ 等其终）"
    assert "WScript.Arguments" in t
    assert "WScript.Quit" in t
