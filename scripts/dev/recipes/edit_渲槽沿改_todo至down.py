# -*- coding: utf-8 -*-
u"""recipe —— 渲槽沿改：today.js :199 ／ :204 之 `PA_GAP.todo ⇒ PA_GAP.down`（二处 · why 逐字 ⛔ 动 · 一改一底）。

字面之据（**机读** · ⛔ 手抄）：CW 之器 ——
  _pm/_cw_slot2.py  sha16 6fda731b13a20244 · OLD 须恰 2 次（:199 ／ :204 · 同行同文 ⇒ 本 recipe 以「前一行」为 ctx 使之唯一）
承：PM 1277 §一（裁一：`_sf===null` 之态须 `down`）／ CW 1278 §一（沿改已落 · 三物）。

底名之桥（承 PM 1258 §二「沿改之底 ＝ 本批之出」）：沿改之底 ＝ `today.js.before_7b90cfb8111bbc2e`（A 形）；
  本器（safe_edit）之底 ＝ `.before_7b90cfb8111bbc2e.today.js` ⇒ 以 CW 之底备之（名 ≡ 值）。
用法：python -X utf8 -B <本件> 沿改 [--apply]   （⛔ 无 --apply ⇒ 只演）
      python -X utf8 -B <本件> --verify
"""
import os
import subprocess
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import safe_edit as S

沿改 = [
    (u'web/pa/faces/today.js · 沿改（:199 ／ :204 · todo ⇒ down · why 逐字 ⛔ 动）', 'web/pa/faces/today.js', [
        ("sub",
         "    _sf ? (paSrcFaceValue(_fFile) || '（后端应答无 量 ⇒ 照实缺）')\n        : PA_GAP.todo('读源未给（GET /v9/pa/source_faces 未应答 ∨ 未载 ⇒ 照实）'),",
         "    _sf ? (paSrcFaceValue(_fFile) || '（后端应答无 量 ⇒ 照实缺）')\n        : PA_GAP.down('读源未给（GET /v9/pa/source_faces 未应答 ∨ 未载 ⇒ 照实）'),"),
        ("sub",
         "    _sf ? (paSrcFaceValue(_fDraw) || '（后端应答无 量 ⇒ 照实缺）')\n        : PA_GAP.todo('读源未给（GET /v9/pa/source_faces 未应答 ∨ 未载 ⇒ 照实）'),",
         "    _sf ? (paSrcFaceValue(_fDraw) || '（后端应答无 量 ⇒ 照实缺）')\n        : PA_GAP.down('读源未给（GET /v9/pa/source_faces 未应答 ∨ 未载 ⇒ 照实）'),"),
    ]),
]
EDITS = {"沿改": 沿改}
ORDER = ["沿改"]
BASES = [
    ('沿改', 0, 'web/pa/faces/today.js', '7b90cfb8111bbc2e', '0f968a4bd83feb68'),
]


def _bridge():
    u"""底名之桥：以 CW 之底（A 形）备 safe_edit 之底（名 ≡ 值）。"""
    for key, idx, rel, hb, hout in BASES:
        p = os.path.join(S.ROOT_DEFAULT, rel)
        bp = S.backup_path(p, hb)
        if os.path.exists(bp) and S.sha16(open(bp, "rb").read()) == hb:
            continue
        src = p + ".before_" + hb
        if os.path.exists(src) and S.sha16(open(src, "rb").read()) == hb:
            data = open(src, "rb").read()
        else:
            data = subprocess.run(["git", "-C", S.ROOT_DEFAULT, "cat-file", "blob", "HEAD:" + rel],
                                  capture_output=True, check=True).stdout
        assert S.sha16(data) == hb, (rel, "底之值 != 旧印", S.sha16(data), hb)
        open(bp, "wb").write(data)


if __name__ == "__main__":
    _bridge()
    sys.exit(S.cli(EDITS, ORDER, bases=BASES, title=u"渲槽沿改 · todo ⇒ down（:199 ／ :204）"))
