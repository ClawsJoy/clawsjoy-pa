# -*- coding: utf-8 -*-
u"""_proc.py —— `scripts/win_pa` 层之**窗隐唯一出口**（Windows）。

由（承 pm_1865 §二.1 ／ pm_1862 · 老板「CMD 闪屏」老病）：
  真凶 ＝ **无控制台之父**（计划任务之宿主 `svchost.exe` ／ `DETACHED_PROCESS` 之器）
  起**控制台子系统**之子（`cmd.exe` ／ `python.exe` ／ `nvidia-smi.exe` …）
  ⇒ Windows **新开**一个控制台（`conhost.exe` ＋ 窗）⇒ 屏上一闪。
  一手（pm_1862 §一 ＋ 我 1863 之五形实测）：裸 `nvidia-smi` 4/4 见窗 ／
  同 argv 并 `CREATE_NO_WINDOW` ⇒ 0 ／ 裸 `cmd` 3/3 ／ 裸 `schtasks` 3/3。

  ⭐ 任务动作之形（我一手 · `D:\\pa_tmp\\flash1865_taskform.py` · 自 `pythonw` 之父采「新见之可见窗」）：
    甲 裸 `cmd /c …`（旧动作）⇒ **2 见**（正控 ／ 探器能见窗）｜乙 `wscript ＋ 静默壳` ⇒ **0 见**；
    丙 壳之**孙**裸调 ⇒ **2 见** ⇒ ⭐ **壳唯护其直系之子** —— 壳与窗隐旗**非**可互替；
    丁 `pythonw` 内裸调 ⇒ 2 见（机理仍在 ／ ⛔ 探器已瞎）。
    ⚠ 并测：壳之子 `GetConsoleWindow()==0` ∧ `sys.stdout is None`（无控制台 ∧ 无 stdio）。

律（**一处定形** · ⛔ 逐处手写 `creationflags` · 承 `core/pa/_proc.py` 之族）：
  凡 `scripts/win_pa/**` 之 subprocess ⇒ 皆调本器（`run_hidden` ／ `popen_hidden`）。

真源 ＝ `core/pa/_proc.py`（同物）—— 本器**按文件路径载之**（⛔ `from core.pa import _proc`：
  `core/pa/__init__.py` 会拉 `pa_core` ＋ 向量库 ⇒ 实测 ≈ 1.6 s ＋ 配置／向量库初始化 ⇒
  本层器意在「环境未就位亦可跑」⇒ 与 `boot_resume.py:94-122` 同一形）。
  载不到 ⇒ **本地等价**（同一表达式 · 并落警 · ⛔ 静默）。

用法：
  python -X utf8 scripts\\win_pa\\_proc.py --self-test
"""
import importlib.util
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
V9 = os.path.dirname(os.path.dirname(_HERE))
#: 窗隐之旗（唯 Windows 有 ⇒ 非 Windows 退化 0 · ⛔ 平台判断散在 call site）。
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _load_core_proc():
    u"""按**文件路径**载 `core/pa/_proc.py`（真源 · ⛔ 拉整包）；载不到 ⇒ `None`（并落警）。"""
    p = os.path.join(V9, "core", "pa", "_proc.py")
    try:
        spec = importlib.util.spec_from_file_location("_pa_proc_hidden", p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        if callable(getattr(m, "run_hidden", None)) and callable(getattr(m, "popen_hidden", None)):
            return m
        sys.stderr.write(u"⚠ 窗隐真源形不符（缺 run_hidden／popen_hidden）：%s\n" % p)
    except Exception as e:                                              # noqa: BLE001 — 照实报因
        sys.stderr.write(u"⚠ 窗隐真源载入失败（%s: %s）：%s" + chr(10)
                         % (type(e).__name__, str(e)[:120], p))
    return None


CORE_PROC = _load_core_proc()


def merge_flags(kw):
    u"""把 `CREATE_NO_WINDOW` **并**进 `kw["creationflags"]`（⛔ 覆盖 · ⛔ 丢）—— 一处定形。"""
    kw["creationflags"] = int(kw.get("creationflags", 0) or 0) | NO_WINDOW
    return kw


def run_hidden(cmd, **kw):
    u"""`subprocess.run` 之窗隐替身（签名同 · 唯 `creationflags` 恒并 `CREATE_NO_WINDOW`）。"""
    if CORE_PROC is not None:
        return CORE_PROC.run_hidden(cmd, **kw)
    return subprocess.run(cmd, **merge_flags(kw))


def popen_hidden(cmd, **kw):
    u"""`subprocess.Popen` 之窗隐替身。"""
    if CORE_PROC is not None:
        return CORE_PROC.popen_hidden(cmd, **kw)
    return subprocess.Popen(cmd, **merge_flags(kw))


def _self_test():
    u"""就地正反控（⛔ 触盘 ／ ⛔ 起停服务）；rc 0 ＝ 皆过。

    ⚠ 本器**量不到「窗」**（那须 PM 之探器 · 见 1862 §三）⇒ 此处所验者 ＝
      **旗之真并** ＋ **二支路皆活**（真源支 ／ 本地等价支）；
      「可见窗 0」之终判归 PM 之四路复量（⛔ 本器自评「已通过」）。
    """
    global CORE_PROC
    fails = []
    sp = [sys.executable, "-c", "print(41+1)"]
    # 正控 1：真源支 —— run_hidden 真跑（rc 0 ＋ stdout 逐字 "42"）。
    if CORE_PROC is None:
        fails.append(u"正控1：core/pa/_proc.py 未载得（真源缺失）")
    else:
        a = run_hidden(sp, capture_output=True, text=True)
        if a.returncode != 0 or (a.stdout or "").strip() != "42":
            fails.append(u"正控1：run_hidden 真跑 rc=%s out=%r" % (a.returncode, (a.stdout or "")[:40]))
    # 正控 2：旗之真并（空 kw ／ 已有他旗 ⇒ 皆并 · ⛔ 覆盖）。
    if merge_flags({})["creationflags"] & NO_WINDOW != NO_WINDOW:
        fails.append(u"正控2a：merge_flags(空) 未并 NO_WINDOW")
    _m = merge_flags({"creationflags": 0x08000000})["creationflags"]
    if _m & NO_WINDOW != NO_WINDOW or _m & 0x08000000 != 0x08000000:
        fails.append(u"正控2b：merge_flags 未并（或丢掉既有旗）")
    # 反控 3：**本地等价支**（拆掉真源）亦真跑成 —— ⛔ 得 ⇒ 退路是瞎的。
    _keep, CORE_PROC = CORE_PROC, None
    try:
        b = run_hidden(sp, capture_output=True, text=True)
        if b.returncode != 0 or (b.stdout or "").strip() != "42":
            fails.append(u"反控3：本地等价支 rc=%s out=%r" % (b.returncode, (b.stdout or "")[:40]))
    finally:
        CORE_PROC = _keep
    for ln in (fails or [u"皆过"]):
        print(u"[%s] %s" % ("FAIL" if fails else "OK", ln))
    return 2 if fails else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(_self_test())
    print(u"_proc: 真源=%s NO_WINDOW=0x%x" % (CORE_PROC is not None, NO_WINDOW))
    sys.exit(0)
