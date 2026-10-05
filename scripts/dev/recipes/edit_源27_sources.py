# -*- coding: utf-8 -*-
u"""recipe --- 落 sources.js :27（归定形之调 · 一处定形）。

承：pm 1324 §一（令 · 一件一 commit · 一改一底）｜pm 1323 §三.1｜pm 1321 §二.1｜CW 1322 §二.2
改手 ＝ CW（已落于工作树 · 印 5f3448f197e23260）⇒ 本件唯「回放核 ＋ 落手」⇒ ⛔ --apply
底 ＝ sources.js.before_6e4b67852390b4c3（9932 B · 正形 · 名≡值 · ≡ HEAD blob 3f702354）｜出 ＝ 5f3448f197e23260（9929 B）
用法：python -X utf8 -B <本件> --verify
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import safe_edit as S

REL = 'web/pa/faces/sources.js'

SEQ = [
    ('sources.js :27 归定形之调（⛔ 不接:平台 ⇒ PA_GAP.off(⛔ 代操作他方平台)）', REL, [
        ("sub",
         "；⛔ 不接：平台（红线 · ⛔ 代操作他方平台）⇒ ⛔ 装成可用；",
         "；' + PA_GAP.off('⛔ 代操作他方平台') + '：平台 ⇒ ⛔ 装成可用；"),
    ]),
]
EDITS = {u"本件": SEQ}
ORDER = [u"本件"]
BASES = [
    ('本件', 0, REL, '6e4b67852390b4c3', '5f3448f197e23260'),
]

if __name__ == "__main__":
    sys.exit(S.cli(EDITS, ORDER, bases=BASES, title=u"落 sources.js :27"))
