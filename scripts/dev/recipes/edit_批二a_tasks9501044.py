# -*- coding: utf-8 -*-
u'''recipe —— 落批二·⒜：tasks.js :950 ／ :1044 之「源格辨义」⇒ 去（一处定形 · :758 ／ :762 之同族）。

承：pm 1297 §三④（候选四处）｜pm 1302 §一（批二 · 异处 ⇒ 可二 commit）｜pm 1285 §二（辨义 ⛔ 上屏）。
其的：源格之文 ≡ 源之径（⛔ 手写「不可达 ≠ 未接」之辨义 ⇒ 一处定形）。
用法：python -X utf8 -B <本件> 批二a [--apply]   （⛔ 无 --apply ⇒ 只演）
      python -X utf8 -B <本件> --verify
'''
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import safe_edit as S

批二a = [
    (u'tasks.js :950（环境面 · 源格去辨义）', 'web/pa/faces/tasks.js', [
        ("sub",
         u"""    if(top) top.innerHTML = paRow('环境面', PA_GAP.down('GET /v9/pa/env 未应答'), '面：GET /v9/pa/env —— **不可达** ≠ **未接**', true);""",
         u"""    if(top) top.innerHTML = paRow('环境面', PA_GAP.down('GET /v9/pa/env 未应答'), '面：GET /v9/pa/env', true);"""),
    ]),
    (u'tasks.js :1044（产品线 · 源格去辨义）', 'web/pa/faces/tasks.js', [
        ("sub",
         u"""    if(head) head.innerHTML = paRow('产品线', PA_GAP.down('未应答'), '面：GET /v9/pa/lines —— **不可达** ≠ **未接**', true);""",
         u"""    if(head) head.innerHTML = paRow('产品线', PA_GAP.down('未应答'), '面：GET /v9/pa/lines', true);"""),
    ]),
]
EDITS = {"批二a": 批二a}
ORDER = ["批二a"]
BASES = [
    ('批二a', 0, 'web/pa/faces/tasks.js', 'd59658db8b6ba0d4', 'dcfdeb2f8a7a8e8c'),
    ('批二a', 1, 'web/pa/faces/tasks.js', 'dcfdeb2f8a7a8e8c', '38b0802d37a6bcd9'),
]


if __name__ == "__main__":
    sys.exit(S.cli(EDITS, ORDER, bases=BASES, title=u"落批二·⒜ · tasks.js :950／:1044"))
