# -*- coding: utf-8 -*-
u"""install_tasks_silent.py —— 装期「计划任务之形」之静默之记（承 pm_1896 §二.3⒞ · 归 9.0.11）。

为何另立一器（⛔ 并入 install_win_pa.py）：
  install_win_pa.py 有一道**产品级**之守 —— 其 --self-test 之**反控 4**：「源 ⛔ 含非读之 open」
  ⇒ 该器**永**唯立目录 · ⛔ 写任何文件（承 pm_1384 §三.4 ⓒ）。我一手踩过此坑（曾加 --log-file
  而被其自证逮 · 已全撤）⇒「装期之全文之记」唯能落于**另器**（本器）。
  ⭐ 而其**任务之逻辑**仍**一处定形**：本器唯 import install_win_pa 而调其 plan() ／
     render_and_maybe_apply(..., register_tasks=True) ⇒ ⛔ 另写一遍
     （承 pm_1896 §二.3⒞「与 register_tasks 一处定形」）。
  ⚠ 本器之**源形之齿**（⛔ 含计划任务之器之名 ／ ⛔ 含子进程模块之名 ／ ⛔ 触 rc 档之名）**不在**本档
    之自证里（自指 ⇒ 扫描器必自逮）—— 其唯在 tests/unit/test_install_tasks_silent_1896.py。

为何静默（NSIS nsExec）：
  nsExec::ExecToStack 捕 stdout **有长度之限** ∧ 唯交付 rc ⇒ 全文之记须由**被调器**落档；
  ⛔ 经 cmd ／ .cmd（必得控制台窗 ⇒ 破「可见窗 0」之尺 · 承 pm_1865 §二.1）。

三守：
  ⒜ **⛔ 写 rc 档** —— rc 唯由**装器侧**（tasks.nsh 之 $0 ＝ 本器之退出码）落 ⇒ **一源**（⛔ 二源）；
  ⒝ **⛔ 吞错** —— 内层之败须**逐字入记**（含 traceback）∧ ⛔ 上抛（上抛 ＝ 装器得非 0 而**无记**）；
  ⒞ **⛔ 阻装** —— 任何败皆唯**记 ＋ 返回 rc**（⛔ 挂 ／ ⛔ 异码）—— 用户得壳为先（承 pm_1896 §二.3⒞）。

用法：
  python -X utf8 -B scripts\\win_pa\\install_tasks_silent.py --go [--log-file <路径>]
  python -X utf8 -B scripts\\win_pa\\install_tasks_silent.py --self-test
退出码：＝ install_win_pa 之 rc（0 ＝ 正常 ｜ 2 ＝ 前置不足 ∨ 立目录失败）｜3 ＝ 入口错
"""
from __future__ import annotations

import io
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
BS = chr(92)
VERSION = 1

#: 记之档（tasks.nsh 恒以 --log-file 明给 ⇒ 此唯手跑之默认）—— 与壳之 shell.log 同处。
DEFAULT_LOG = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
                           "ClawsJoyPA", "shell", "install_tasks.log")


class _Tee(object):
    u"""屏 ＋ 一档 双写。⚠ 记之败 ⛔ 阻装（⛔ 上抛）∧ ⛔ 吞错（原样把字数返给调用者）。"""

    def __init__(self, a, b):
        self._a = a
        self._b = b

    def write(self, s):
        for _x in (self._a, self._b):
            try:
                _x.write(s)
            except Exception:                                        # noqa: BLE001
                pass
        return len(s)

    def flush(self):
        for _x in (self._a, self._b):
            try:
                _x.flush()
            except Exception:                                        # noqa: BLE001
                pass

    def reconfigure(self, *a, **k):
        return None

    def isatty(self):
        return False


def _inner():
    u"""载 install_win_pa（**一处定形** —— ⛔ 本器另写任务之逻辑 ／ ⛔ 另写前置闸）。"""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import importlib
    return importlib.import_module("install_win_pa")


def run(log_path, dry=False):
    u"""真跑 ⇒ rc（**永不**上抛 —— 见文首 ⒝ ／ ⒞）。记之档 ⛔ 开 ⇒ 唯屏 ＋ 落警（⛔ 阻）。"""
    _old = sys.stdout
    _fh = None
    try:
        _d = os.path.dirname(os.path.abspath(log_path))
        if _d and not os.path.isdir(_d):
            os.makedirs(_d, exist_ok=True)
        _fh = io.open(log_path, "w", encoding="utf-8")
    except Exception as _e:                                          # noqa: BLE001 — 照实：唯屏 ＋ 落警
        sys.stderr.write(u"[tasks-silent] ⚠ 记之档 ⛔ 开（%s: %s）⇒ 唯屏\n"
                         % (type(_e).__name__, str(_e)[:120]))
        _fh = None
    if _fh is not None:
        sys.stdout = _Tee(_old, _fh)
    try:
        print(u"[tasks-silent] 记之档 ＝ %s" % log_path)
        print(u"[tasks-silent] 形 ＝ install_win_pa 之任务之路（register_tasks=True%s）"
              % (u"" if dry else u" · --go"))
        _m = _inner()
        _p = _m.plan(False, os.path.join(_m.ROOT, "wheel"), None)
        _rc, _lines = _m.render_and_maybe_apply(_p, dry, True)
        for _x in _lines:
            print(_x)
        print(u"[tasks-silent] rc ＝ %s（rc 之档由装器侧落 —— ⛔ 二源）" % _rc)
        return int(_rc)
    except Exception as _e:                                          # noqa: BLE001 — ⛔ 吞错：逐字入记
        print(u"[tasks-silent] ⛔ 内层之败：%s: %s" % (type(_e).__name__, str(_e)[:200]))
        try:
            traceback.print_exc(file=sys.stdout)
        except Exception:                                            # noqa: BLE001
            pass
        return 2
    finally:
        try:
            sys.stdout.flush()
        except Exception:                                            # noqa: BLE001
            pass
        sys.stdout = _old
        if _fh is not None:
            try:
                _fh.close()
            except Exception:                                        # noqa: BLE001
                pass


def main(argv):
    args = list(argv)
    if "--help" in args or "-h" in args:
        print(__doc__)
        return 0
    if "--self-test" in args:
        return self_test()
    log_path = DEFAULT_LOG
    for _i, _a in enumerate(args):
        if _a == "--log-file" and _i + 1 < len(args):
            log_path = args[_i + 1]
            break
    dry = "--go" not in args
    return run(log_path, dry=dry)


def self_test():
    u"""自证（离机 · 唯本机干跑 —— ⛔ 出网 ／ ⛔ 改机 ／ ⛔ 真注册）。

    ⚠ 源形之齿另在 tests/unit/test_install_tasks_silent_1896.py（自指 ⇒ 此处 ⛔ 能扫已源）。
    """
    import shutil
    import tempfile

    fails = []

    def rd(p):
        try:
            return io.open(p, encoding="utf-8", errors="replace").read()
        except Exception:                                            # noqa: BLE001
            return None

    tmp = tempfile.mkdtemp(prefix="tasks_silent_")
    try:
        # 正控 1：真源之干跑（**唯实方能充证**）⇒ rc ∈ {0,2} ∧ 记在 ∧ 记见 install_win_pa 之行
        lp = os.path.join(tmp, "a", "install_tasks.log")             # ⭐ 兼证：记档之目录自建
        rc1 = run(lp, dry=True)
        txt1 = rd(lp) or u""
        if rc1 not in (0, 2):
            fails.append(u"正控 1：干跑 rc ＝ %r（应 0 ／ 2）" % rc1)
        if not txt1:
            fails.append(u"正控 1：记之档未落（%s）" % lp)
        else:
            if u"[install]" not in txt1:
                fails.append(u"正控 1：记 ⛔ 见 install_win_pa 之行（「一处定形」⛔ 证）")
            if u"rc ＝" not in txt1:
                fails.append(u"正控 1：记 ⛔ 载 rc 之行")
        # 反控 1：干跑 ⇒ ⛔ 真注册（真注册唯现「[task] <名> -> rc=」之行）
        if u"[task]" in txt1 and u"-> rc=" in txt1:
            fails.append(u"反控 1：干跑竟真注册（记含 [task] -> rc=）")
        # 反控 2：干跑 ⇒ ⛔ 设键（库根）
        if u"[env]" in txt1:
            fails.append(u"反控 2：干跑竟设键（⛔ 动机）")

        # 正控 2：幂等 —— 跑二遍 ⇒ 档**不增**（w 截断 ⇒ ⛔ 追加）
        n1 = os.path.getsize(lp)
        rc2 = run(lp, dry=True)
        n2 = os.path.getsize(lp)
        if rc2 != rc1:
            fails.append(u"正控 2：二跑 rc 不一（%r ↔ %r）" % (rc1, rc2))
        if n2 > n1:
            fails.append(u"正控 2：二跑档增（%d → %d ⇒ 疑追加 ⛔ 截断）" % (n1, n2))

        # 反控 3（要紧）：内层之败 ⇒ rc ＝ 2 ∧ **逐字入记**（含 traceback）∧ ⛔ 上抛
        _orig = globals()["_inner"]
        lp2 = os.path.join(tmp, "boom.log")

        def _boom():
            raise RuntimeError(u"反控：内层之败")
        globals()["_inner"] = _boom
        try:
            rc3 = run(lp2, dry=True)
        finally:
            globals()["_inner"] = _orig
        txt2 = rd(lp2) or u""
        if rc3 != 2:
            fails.append(u"反控 3：内层败之 rc ＝ %r（应 2 —— ⛔ 上抛 ／ ⛔ 阻装）" % rc3)
        if u"RuntimeError" not in txt2:
            fails.append(u"反控 3：记 ⛔ 载败之因（⛔ 吞错）")
        if u"Traceback" not in txt2:
            fails.append(u"反控 3：记 ⛔ 载 traceback")

        # 反控 4：记之档 ⛔ 开（喂一「目录」当档）⇒ ⛔ 上抛 ∧ 仍返回 rc（⛔ 阻装）
        _d = os.path.join(tmp, "adir")
        os.makedirs(_d, exist_ok=True)
        try:
            rc4 = run(_d, dry=True)
        except Exception as _e:                                      # noqa: BLE001
            fails.append(u"反控 4：记 ⛔ 开时上抛（%s）" % type(_e).__name__)
            rc4 = None
        if rc4 not in (0, 2):
            fails.append(u"反控 4：记 ⛔ 开时 rc ＝ %r（应 0 ／ 2 —— ⛔ 阻装）" % rc4)

        # 正控 3：_Tee 之双写 ＋ 容忍 reconfigure ／ isatty ＋ 一侧之败 ⛔ 累及另一侧
        _ba, _bb = io.StringIO(), io.StringIO()
        _t = _Tee(_ba, _bb)
        _t.write(u"甲乙")
        _t.flush()
        if _ba.getvalue() != u"甲乙" or _bb.getvalue() != u"甲乙":
            fails.append(u"正控 3：_Tee ⛔ 双写")
        if _t.reconfigure() is not None or _t.isatty() is not False:
            fails.append(u"正控 3：_Tee ⛔ 容忍 reconfigure ／ isatty")

        class _Boom(object):
            def write(self, s):
                raise IOError(u"反控")

            def flush(self):
                raise IOError(u"反控")

        _t2 = _Tee(_ba, _Boom())
        if _t2.write(u"丙") != 1:
            fails.append(u"正控 3：_Tee 之返 ⛔ 为字数")
        if _ba.getvalue() != u"甲乙丙":
            fails.append(u"正控 3：一侧之败竟累及另一侧（%r）" % _ba.getvalue())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(u"[self-test] %s" % (u"PASS（4 反控 ＋ 3 正控）" if not fails else u"FAIL"))
    for _f in fails:
        print(u"  [FAIL] %s" % _f)
    return 0 if not fails else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
