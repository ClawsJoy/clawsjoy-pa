# -*- coding: utf-8 -*-
u"""recipe --- 落序 1 · core.js 四支一改。

承：pm 1311 §一（令 · 一件一 commit）｜pm 1309 §二.1（#paDuty 静-only）｜pm 1297 §三②（器与名之分）
改手 ＝ CW（已落于工作树 · 印 fdac39967a3772b6）⇒ 本件唯「回放核 ＋ 落手」⇒ ⛔ --apply
底 ＝ core.js.before_ddcd1b9372bc37da（12608 B · 正形 · 名≡值 · ≡ HEAD blob）｜出 ＝ fdac39967a3772b6（13134 B）
用法：python -X utf8 -B <本件> --verify
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import safe_edit as S

REL = 'web/pa/core.js'

SEQ = [
    ('core.js 四支一改（:60 括注 ／ :73 注正 ／ :77 冠 ＋ 新 :78）', REL, [
        ("sub", '     运行期由 `today.js` 之 `paSrcWrite` **认领覆盖**（双保险 · ⛔ 二说 · 承 pm 18:00 §一）。 */', '     运行期由 `today.js` 之 `paSrcWrite` **认领覆盖**（双保险 · ⛔ 二说 · ⛔ 及 `#paDuty` 之静-only 三行（`pa.html:113`／`:114`／`:115`）—— 其无运行期写者 ⇒ 静文即唯一之说 · 承 pm 1297 §三③ · 承 pm 18:00 §一）。 */'),   # base 60-60 -> work 60-60
        ("sub", '/* ===== ⭐ 面之「陈旧」第四态 · **一处定形**（承 pm 19:05 令 §一 ／ pm_刀12p §〇 之三态 ＋ 本态）=====', '/* ===== ⭐ 面之「陈旧」第四态 · **名与义定于此**（渲形随位三辞 · ⛔ 一处之字面）（承 pm 19:05 令 §一 ／ pm_刀12p §〇 之三态 ＋ 本态 ／ pm 1297 §三②）====='),   # base 73-73 -> work 73-73
        ("sub", '   四态（唯此一处）：⒜ 未接 · 待办（M1）｜⒝ ⛔ 不接（红线）｜⒞ 不可达｜⭐ ⒟ **陈旧**（数是真的 · 刻是旧的）。', '   本处定其名与义 —— 四态（唯此一处）：⒜ 未接 · 待办（M1）｜⒝ ⛔ 不接（红线）｜⒞ 不可达｜⭐ ⒟ **陈旧**（数是真的 · 刻是旧的）。\n   器与名之分：⒜⒝⒞ ⇒ **有器**（`PA_GAP.todo/off/down` · 见上）；⭐ ⒟ 陈旧 ⇒ **唯「名与义」定于此** · 其渲形随位三辞（**值** ／ **组标·计数** ／ **画像行**）⇒ ⛔ 一处之字面（承 pm 1297 §三②）。'),   # base 77-77 -> work 77-78
    ]),
]
EDITS = {u"本批": SEQ}
ORDER = [u"本批"]
BASES = [
    ('本批', 0, REL, 'ddcd1b9372bc37da', 'fdac39967a3772b6'),
]

if __name__ == "__main__":
    sys.exit(S.cli(EDITS, ORDER, bases=BASES, title=u"落序 1 · core.js 四支一改"))
