# -*- coding: utf-8 -*-
u"""recipe --- 落批四 · selfdesc.js :1415。

承：pm 1313 §一（令 · 一批三件 · 三 commit · 异件）｜pm 1310 §二
改手 ＝ CW（已落于工作树 · 印 15a7709eaf67533a）⇒ 本件唯「回放核 ＋ 落手」⇒ ⛔ --apply
底 ＝ selfdesc.js.before_cc32fa798827269b（293564 B · 正形 · 名≡值 · ≡ HEAD blob）｜出 ＝ 15a7709eaf67533a（293542 B）
用法：python -X utf8 -B <本件> --verify
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import safe_edit as S

REL = 'web/pa/faces/selfdesc.js'

SEQ = [
    ('selfdesc.js :1415 短标去长形（⒜ 未接 · 待办（M1） ⇒ 未接）', REL, [
        ("sub", "  return '（已接 ' + sf.read.length + ' · ⒜ 未接 · 待办（M1） ' + sf.miss.length", "  return '（已接 ' + sf.read.length + ' · 未接 ' + sf.miss.length"),   # base 1415-1415 -> work 1415-1415
    ]),
]
EDITS = {u"本批": SEQ}
ORDER = [u"本批"]
BASES = [
    ('本批', 0, REL, 'cc32fa798827269b', '15a7709eaf67533a'),
]

if __name__ == "__main__":
    sys.exit(S.cli(EDITS, ORDER, bases=BASES, title=u"落批四 · selfdesc.js :1415"))
