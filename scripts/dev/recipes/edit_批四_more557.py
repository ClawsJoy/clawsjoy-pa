# -*- coding: utf-8 -*-
u"""recipe --- 落批四 · more.js :557。

承：pm 1313 §一（令 · 一批三件 · 三 commit · 异件）｜pm 1310 §二.1｜pm 1272 §三
改手 ＝ CW（已落于工作树 · 印 123e739e23b0192e）⇒ 本件唯「回放核 ＋ 落手」⇒ ⛔ --apply
底 ＝ more.js.before_85ef9759d18b35db（42795 B · 正形 · 名≡值 · ≡ HEAD blob）｜出 ＝ 123e739e23b0192e（42868 B）
用法：python -X utf8 -B <本件> --verify
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import safe_edit as S

REL = 'web/pa/faces/more.js'

SEQ = [
    ('more.js :557 去括注（辨义移入 title · ⛔ 上屏）', REL, [
        ("sub", '        : \'<div class="r"><span class="k">0 项</span><span>后端 providers: [] ⇒ 照实报 0（⛔ 与「未接」同词）</span></div>\')', '        : \'<div class="r"><span class="k">0 项</span><span title="⛔ 与「未接」同词（辨义 · ⛔ 上屏 · 承 pm 1272 §三 · 承 pm 1310 §二.1）">后端 providers: [] ⇒ 照实报 0</span></div>\')'),   # base 557-557 -> work 557-557
    ]),
]
EDITS = {u"本批": SEQ}
ORDER = [u"本批"]
BASES = [
    ('本批', 0, REL, '85ef9759d18b35db', '123e739e23b0192e'),
]

if __name__ == "__main__":
    sys.exit(S.cli(EDITS, ORDER, bases=BASES, title=u"落批四 · more.js :557"))
