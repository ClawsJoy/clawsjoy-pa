# -*- coding: utf-8 -*-
u"""recipe —— 落批二·⒝：tasks.js :414 ／ :520 之「源格载 PA_GAP.todo( 之裹 ＋ 辨义」⇒ 去（值／源 双身 · 同批同改）。

承：pm 1297 §四（候选④）｜pm 1302 §一（批二 · 异处 ⇒ 可二 commit）｜pm 1305 §二.1（字面）
字面之出 ＝ CW 器 _pm/_cw_p123.py 之 OLD4 ／ NEW4（逐字取 · ⛔ 手抄）
本批以底 38b0802d37a6bcd9 重建 ⇒ 逐 sub 落（承 pm 1305 §二.2 之常则 · 二印并列）
用法：python -X utf8 -B <本件> 批二b [--apply]     （⛔ 无 --apply ⇒ 只演）
      python -X utf8 -B <本件> --verify
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import safe_edit as S

OLD4 = "'源：' + PA_GAP.todo('后端无「受理态」读面 —— POST /v9/pa/dialog ／ POST /v9/agent/chat 为写路（⛔ 读源）') + '｜本页计数 ＝ 本页已接（本页口径 · ⛔ 后端口径 · ⛔ 以 0 充未接）'"
NEW4 = "'源：后端无「受理态」读面 —— POST /v9/pa/dialog ／ POST /v9/agent/chat 为写路（⛔ 读源）｜本页计数 ＝ 本页已接（本页口径）'"

批二b = [
    (u'tasks.js :414 \u002f :520（源格去裹 ＋ 去辨义 · 值／源 双身）', 'web/pa/faces/tasks.js', [
        ("sub", '      ' + OLD4, '      ' + NEW4),
        ("sub", OLD4 + ');', NEW4 + ');'),
    ]),
]
EDITS = {"批二b": 批二b}
ORDER = ["批二b"]
BASES = [
    ('批二b', 0, 'web/pa/faces/tasks.js', '38b0802d37a6bcd9', 'de4fe0fdf7819045'),
]

if __name__ == "__main__":
    sys.exit(S.cli(EDITS, ORDER, bases=BASES, title=u"落批二·⒝ · tasks.js :414 ／ :520"))
