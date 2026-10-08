# -*- coding: utf-8 -*-
u'''齿：pm_1889 §三 ／ pm_1894 §一 之「落箱之刻**复核号**」（器在 `scripts/dev/投一步.py`）。

⭐ 离机 · 临时目录（器之 selftest 自持）⇒ ⛔ 触本仓 ／ ⛔ 触真箱 ／ ⛔ 触台账。
⚠ 一处定形：齿居器内（同源）⇒ 本件唯**挂**之（⛔ 另写一套断言 —— 免得漂）；
   ⭐ 且以**子进程**挂（器于导入期走 `sys.stdout.reconfigure` ⇒ ⛔ 直接 import）。
'''
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V9 = os.path.dirname(os.path.dirname(HERE))
_TOU = os.path.join(V9, 'scripts', 'dev', u'投一步.py')


def test_tou1_numgate_selftest():
    r = subprocess.run([sys.executable, '-X', 'utf8', '-B', _TOU, '--self-test'],
                       capture_output=True, text=True, encoding='utf-8', errors='replace',
                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    assert r.returncode == 0, r.stdout + r.stderr
    assert u'[总判] PASS' in r.stdout, r.stdout + r.stderr
    assert u'自证 7 号撞' in r.stdout, r.stdout + r.stderr
