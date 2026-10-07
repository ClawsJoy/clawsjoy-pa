# -*- coding: utf-8 -*-
u'''齿：pm_1877 之计划任务「形」自检 ＋ 迁移（器在 `scripts/win_pa/task_migrate.py`）。

⭐ 离机 · 假跑器 ＋ 临时目录 ⇒ ⛔ 触真任务 ／ ⛔ 触本仓（器之 selftest 自持）。
⚠ 一处定形：齿居器内（同源）⇒ 本件唯**挂**之（⛔ 另写一套断言 —— 免得漂）。
'''
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V9 = os.path.dirname(os.path.dirname(HERE))
_WIN_PA = os.path.join(V9, 'scripts', 'win_pa')
if _WIN_PA not in sys.path:
    sys.path.insert(0, _WIN_PA)


def test_task_migrate_selftest():
    import task_migrate as tm
    assert tm.selftest() == 0
