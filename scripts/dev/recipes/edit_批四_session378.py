# -*- coding: utf-8 -*-
u"""recipe --- 落批四 · session.js :378。

承：pm 1313 §一（令 · 一批三件 · 三 commit · 异件）｜pm 1310 §二
改手 ＝ CW（已落于工作树 · 印 29b6792229adbf3e）⇒ 本件唯「回放核 ＋ 落手」⇒ ⛔ --apply
底 ＝ session.js.before_06ec3a228899757f（28164 B · 正形 · 名≡值 · ≡ HEAD blob）｜出 ＝ 29b6792229adbf3e（28127 B）
用法：python -X utf8 -B <本件> --verify
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import safe_edit as S

REL = 'web/pa/faces/session.js'

SEQ = [
    ('session.js :378 _fail 去辨义尾（⛔ ≠ 不可达 ／ ⛔ ≠ 空）', REL, [
        ("sub", "  host.innerHTML = paKbPanelHtml(paKbCache||{rows:[],counts:{}, _fail:'尚未取（展开本面板即取 · ⛔ ≠ 不可达 ／ ⛔ ≠ 空）', degraded:'尚未加载（展开时按只读接口拉取，不刷新页面）'}, {open:open});", "  host.innerHTML = paKbPanelHtml(paKbCache||{rows:[],counts:{}, _fail:'尚未取（展开本面板即取）', degraded:'尚未加载（展开时按只读接口拉取，不刷新页面）'}, {open:open});"),   # base 378-378 -> work 378-378
    ]),
]
EDITS = {u"本批": SEQ}
ORDER = [u"本批"]
BASES = [
    ('本批', 0, REL, '06ec3a228899757f', '29b6792229adbf3e'),
]

if __name__ == "__main__":
    sys.exit(S.cli(EDITS, ORDER, bases=BASES, title=u"落批四 · session.js :378"))
