# -*- coding: utf-8 -*-
u"""recipe --- 落 pa.html :110（引之射程与锚）。

承：pm 1330 §一（令 · 一件一 commit · 一改一底）｜pm 1328 §二.2｜pm 1309 §二.3｜CW 1329 §一
改手 ＝ CW（已落于工作树 · 印 678c97dae2944c5d）⇒ 本件唯「回放核 ＋ 落手」⇒ ⛔ --apply
底 ＝ pa.html.before_e2567f4393f33e26（24,696 B · 正形 · 名≡值 · ≡ HEAD blob 6d3200ff）｜出 ＝ 678c97dae2944c5d（24,767 B）
用法：python -X utf8 -B <本件> --verify
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import safe_edit as S

REL = 'web/pa.html'

SEQ = [
    ('pa.html :110 引 core.js:73-77 ⇒ 73-84（附锚）', REL, [
        ("sub",
         "一处定形 · 承 core.js:73-77）",
         "一处定形 · 承 core.js:73-84（锚：「四态（唯此一处）」之块 · 即 PA_STALE 之注））"),
    ]),
]
EDITS = {u"本件": SEQ}
ORDER = [u"本件"]
BASES = [
    ('本件', 0, REL, 'e2567f4393f33e26', '678c97dae2944c5d'),
]

if __name__ == "__main__":
    sys.exit(S.cli(EDITS, ORDER, bases=BASES, title=u"落 pa.html :110"))
