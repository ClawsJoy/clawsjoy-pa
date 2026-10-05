# -*- coding: utf-8 -*-
u"""recipe —— 正辞批 · core.js :59（其 4 行静态标 ⇒ 其 3 行静态标）（一改一底）。

字面之据（**机读** · ⛔ 手抄）：由**底**（<件>.before_e761e9205e3868f7）与**现读之件**机构 ⇒ OLD/NEW。
承：pm 1287 §〇／§一（正辞 4 ⇒ 3）／ pm 1288 §一（重申 · 数 ＝ 3）／ CW 1288 §一（改手）。
数之据：静区之逐字抄三形者唯 pa.html :224（不可达）／ :226（⛔ 不接）／ :228（不可达）⇒ 3 行。

底名之桥（承 pm 1258 §二）：CW 之底 ＝ core.js.before_e761e9205e3868f7（A 形）；本器之底 ＝ .before_e761e9205e3868f7.core.js。
用法：python -X utf8 -B <本件> 正辞 [--apply]   （⛔ 无 --apply ⇒ 只演）
      python -X utf8 -B <本件> --verify
"""
import os
import subprocess
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import safe_edit as S

正辞 = [
    (u'web/pa/core.js · :59（静态壳之注：「其 4 行静态标」⇒「其 3 行静态标」）', 'web/pa/core.js', [
        ("sub",
         '   ⚠ 静态壳（`pa.html` · ⭐ 唯一壳 —— 承 pm 1203 §一：副本 `web/pa_v3.html` 已于 2026-10-05 删 · TD 716bc31）⛔ 调 JS ⇒ 其 4 行静态标**逐字抄此三形**（无 JS 兜底）；',
         '   ⚠ 静态壳（`pa.html` · ⭐ 唯一壳 —— 承 pm 1203 §一：副本 `web/pa_v3.html` 已于 2026-10-05 删 · TD 716bc31）⛔ 调 JS ⇒ 其 3 行静态标**逐字抄此三形**（无 JS 兜底）；'),
    ]),
]
EDITS = {"正辞": 正辞}
ORDER = ["正辞"]
BASES = [
    ('正辞', 0, 'web/pa/core.js', 'e761e9205e3868f7', '77976ddccd7c54e4'),
]


def _bridge():
    u"""底名之桥：以 CW 之底（A 形）备 safe_edit 之底（名 ≡ 值）。"""
    for key, idx, rel, hbb, hout in BASES:
        p = os.path.join(S.ROOT_DEFAULT, rel)
        bp = S.backup_path(p, hbb)
        if os.path.exists(bp) and S.sha16(open(bp, "rb").read()) == hbb:
            continue
        src = p + ".before_" + hbb
        if os.path.exists(src) and S.sha16(open(src, "rb").read()) == hbb:
            data = open(src, "rb").read()
        else:
            data = subprocess.run(["git", "-C", S.ROOT_DEFAULT, "cat-file", "blob", "HEAD:" + rel],
                                  capture_output=True, check=True).stdout
        assert S.sha16(data) == hbb, (rel, "底之值 != 旧印", S.sha16(data), hbb)
        open(bp, "wb").write(data)


if __name__ == "__main__":
    _bridge()
    sys.exit(S.cli(EDITS, ORDER, bases=BASES, title=u"正辞批 · core.js :59（其 4 行静态标 ⇒ 其 3 行静态标）"))
