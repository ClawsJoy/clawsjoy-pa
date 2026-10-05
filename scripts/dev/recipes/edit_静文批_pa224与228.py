# -*- coding: utf-8 -*-
u"""recipe —— 静文批：pa.html :224 ／ :228 之态形逐字（⒜ 未接 ⇒ 不可达 · 二处 · 一改一底）。

字面之据（**机读** · ⛔ 手抄）：CW 1283 §二 之逐字（今 ⇒ 新）。
承：PM 1281 §四（裁 :224 过期 · CW 出字面 · TD 落件）／ PM 1282 §三①（字面之定 ＝ 今刻 · ⛔ 再候）。

底（本器 · B 形）：.before_457bfb72106b59cb.pa.html（名 ≡ 值 · 由 safe_edit 之 make_backup 自建 · 取自读）。
用法：python -X utf8 -B <本件> 静文 [--apply]   （⛔ 无 --apply ⇒ 只演）
      python -X utf8 -B <本件> --verify
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import safe_edit as S

静文 = [
    (u'web/pa.html · :224 ／ :228（⒜ 未接 ⇒ 不可达 · 态形逐字）', 'web/pa.html', [
        ("sub",
         '<div class="it">📄 文件<span class="n na">⒜ 未接 · 待办（M1）｜为何未接：无源（范围未定 · 候 PM 裁）</span></div>',
         '<div class="it">📄 文件<span class="n na">不可达（读源未给（GET /v9/pa/source_faces 未应答 ∨ 未载 ⇒ 照实））</span></div>'),
        ("sub",
         '<div class="it">🎨 出图<span class="n na">⒜ 未接 · 待办（M1）｜为何未接：无源（候 GPU 合取 · 与描互斥）</span></div>',
         '<div class="it">🎨 出图<span class="n na">不可达（读源未给（GET /v9/pa/source_faces 未应答 ∨ 未载 ⇒ 照实））</span></div>'),
    ]),
]
EDITS = {"静文": 静文}
ORDER = ["静文"]
BASES = [
    ('静文', 0, 'web/pa.html', '457bfb72106b59cb', '559edaf3b7a70713'),
]

if __name__ == "__main__":
    sys.exit(S.cli(EDITS, ORDER, bases=BASES, title=u"静文批 · pa.html :224 ／ :228（⒜ 未接 ⇒ 不可达）"))
