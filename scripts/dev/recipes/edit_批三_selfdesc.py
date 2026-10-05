# -*- coding: utf-8 -*-
u"""recipe —— 落批三：selfdesc.js :1278 ／ :1341 之「尚未接入」⇒「未接」（异辞归一）。

承：pm 1297 §五.1｜pm 1302 §一（批三）｜CW 1300 §二（第三批 · 异辞归一）
字面之出 ＝ CW 器 _pm/_cw_p123.py 之 E5（尚未接入 ⇒ 未接 · 2 处）
CW 已改手落于工作树（改手印 cc32fa798827269b）⇒ 本件唯「回放核 ＋ 落手」⇒ ⛔ --apply（工作树今已含之）
用法：python -X utf8 -B <本件> --verify     （⛔ --apply：工作树已含其改）
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import safe_edit as S

A_OLD = "'尚未接入 ' + paSelfCount(sf) + '：'"
A_NEW = "'未接 ' + paSelfCount(sf) + '：'"
B_OLD = '面 ／ 尚未接入 '
B_NEW = '面 ／ 未接 '

批三 = [
    (u'selfdesc.js :1278 ／ :1341（尚未接入 ⇒ 未接 · 异辞归一）', 'web/pa/faces/selfdesc.js', [
        ("sub", A_OLD, A_NEW),
        ("sub", B_OLD, B_NEW),
    ]),
]
EDITS = {"批三": 批三}
ORDER = ["批三"]
BASES = [
    ('批三', 0, 'web/pa/faces/selfdesc.js', '61e4866a0b926748', 'cc32fa798827269b'),
]

if __name__ == "__main__":
    sys.exit(S.cli(EDITS, ORDER, bases=BASES, title=u"落批三 · selfdesc.js 尚未接入 ⇒ 未接"))
