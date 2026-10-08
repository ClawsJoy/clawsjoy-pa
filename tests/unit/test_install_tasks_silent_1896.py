# -*- coding: utf-8 -*-
u'''齿：pm_1896 §二.3⒞ 之「装期任务之形之静默之记」（器在 `scripts/win_pa/install_tasks_silent.py`）。

以何形调用：
  python -X utf8 -B -m pytest tests/unit/test_install_tasks_silent_1896.py -q

判据：
  ⒈ **源形**（⚠ 自指 ⇒ ⛔ 能居器内之自证 ⇒ 唯在此处）：器源 ⛔ 含
     ⒜ rc 档之名（rc 唯装器侧之一源 ⇒ ⛔ 二源）
     ⒝ 计划任务之器之名（任务之逻辑须唯 `install_win_pa` 一处定形 ⇒ ⛔ 本器另写）
     ⒞ 子进程模块之名（本器 ⛔ 起任何子 ⇒ 静默之根）；
  ⒉ **真跑**（**唯实方能充证** —— 干跑 · 记落临时目录）：rc ∈ {0,2} ∧ 记在 ∧ 记见
     `install_win_pa` 之行（`[install]`）∧ ⛔ 真注册（无 `[task] … -> rc=`）∧ ⛔ 设键（无 `[env]`）；
  ⒊ **自证**：器之 `--self-test` ⇒ rc 0 ∧ `[self-test] PASS`。
⭐ 离机 · 临时目录 ⇒ ⛔ 触真任务 ／ ⛔ 触本仓 ／ ⛔ 触 %LOCALAPPDATA%（唯随临时目录）。
'''
import io
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
V9 = os.path.dirname(os.path.dirname(HERE))
_TOOL = os.path.join(V9, 'scripts', 'win_pa', 'install_tasks_silent.py')
#: 禁字面（反控之的 · 一处定形）
_NEEDLES = ('install_tasks.rc', 'schtasks', 'subprocess', 'shell=True', 'os.system')


def _src():
    return io.open(_TOOL, encoding='utf-8', errors='replace').read()


def _hits(src):
    u'''源里之禁字面（喂假源 ⇒ 须逮 —— 反控之器）。'''
    return [w for w in _NEEDLES if w in src]


def _run(args, **kw):
    return subprocess.run([sys.executable, '-X', 'utf8', '-B', _TOOL] + list(args),
                          capture_output=True, text=True, encoding='utf-8', errors='replace',
                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), **kw)


def test_source_has_no_forbidden_literals():
    u'''源形：⛔ 触 rc 档 ／ ⛔ 重写任务之逻辑 ／ ⛔ 起子进程。'''
    got = _hits(_src())
    assert got == [], got


def test_detector_has_teeth():
    u'''反控：喂植入之假源 ⇒ 必逮（⛔ 无齿之闸 ＝ 假绿）。'''
    fake = 'subprocess.run(["schtasks", "/query"])\nopen("install_tasks.rc", "w")\n'
    assert sorted(_hits(fake)) == ['install_tasks.rc', 'schtasks', 'subprocess'], _hits(fake)
    assert _hits('import os\nprint(os.name)\n') == [], u'反控：净源竟被判禁'


def test_dry_run_writes_log_and_registers_nothing():
    u'''真跑（干跑）：记落临时目录 ∧ 见 install_win_pa 之行 ∧ ⛔ 真注册 ／ ⛔ 设键。'''
    with tempfile.TemporaryDirectory(prefix='tasks_silent_t_') as d:
        lp = os.path.join(d, 'sub', 'install_tasks.log')          # 子目录 ⇒ 兼证自建
        r = _run(['--log-file', lp])
        assert r.returncode in (0, 2), (r.returncode, r.stdout, r.stderr)
        assert os.path.isfile(lp), u'（未 --go ⇒ 干跑之径）记之档须落'
        txt = io.open(lp, encoding='utf-8', errors='replace').read()
        assert u'[install]' in txt, txt                           # ⭐ 一处定形之证
        assert u'rc ＝' in txt, txt
        assert u'[env]' not in txt, txt                           # 干跑 ⛔ 设键
        assert not re.search(u'\\[task\\] .*-> rc=', txt), txt       # 干跑 ⛔ 真注册


def test_selftest_passes():
    u'''器之自证（4 反控 ＋ 3 正控）—— 以**子进程**挂之（⛔ 直 import：其改 sys.stdout）。'''
    r = _run(['--self-test'])
    assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
    assert u'[self-test] PASS' in r.stdout, r.stdout + r.stderr
