# -*- coding: utf-8 -*-
u"""recipe —— 渲槽修：why 归值格 · 源行 ＝ 源之径（∨ 空）（web/pa/faces/today.js · 三处 · 一改一底）。

字面之据（**机读** · ⛔ 手抄）：CW 之器 ——
  _pm/_cw_slot1.py  sha16 e6ec188e4c6be1ae · PAIRS ＝ 3 对（A 平台 ／ B 文件 ／ C 出图）
承：PM 1272 §二（why 归值格）／ PM 1275 §一（准其逐字）／ PM 1275 §一⒝（:191 源行 ＝ 空）。

底名之桥（承 PM 1259 §三 ／ 1262 §四）：CW 器之底 ＝ `today.js.before_24a5b3a8013b595a`（A 形）；
  本器（safe_edit）之底 ＝ `.before_<旧印>.today.js` ⇒ 以 CW 之底备之（名 ≡ 值）；
  射程裁（全仓）后随「正名之批」归一（另批）。
用法：python -X utf8 -B <本件> 渲槽 [--apply]   （⛔ 无 --apply ⇒ 只演）
      python -X utf8 -B <本件> --verify
"""
import os
import subprocess
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import safe_edit as S

渲槽 = [
    (u'web/pa/faces/today.js · 渲槽修（why 归值格 · 源行 ＝ 源之径∨空）', 'web/pa/faces/today.js', [
        ("sub",
         "  paSrcWrite('srcRowPlatform', '🌐 平台', PA_GAP.off('⛔ 代操作他方平台'),\n    '为何不接：⛔ 代操作他方平台 ＝ **红线**（⛔ 待办 · 不会有 ⇒ ⛔ 以「未接」暗许「将来会接」＝ 软性虚诺 · 承 pm 17:47 §二改①）');",
         "  /* ⚠ why 归**值格**（⛔ 源行）—— 源行之义 ＝ 源之径（承 today.js:111）；且「⛔ 以「未接」暗许「将来会接」＝ 软性虚诺」\n     属**辨义**类 ⇒ ⛔ 上屏（承 pm 1272 §三）。平台面 ⛔ 后端源 ⇒ 源行 ＝ **空**。出处 ＝ PM 17:47 §二改①。 */\n  paSrcWrite('srcRowPlatform', '🌐 平台', PA_GAP.off('⛔ 代操作他方平台'));"),
        ("sub",
         "  paSrcWrite('srcRowFile', '📄 文件',\n    _sf ? (paSrcFaceValue(_fFile) || '（后端应答无 量 ⇒ 照实缺）') : PA_GAP.todo(),\n    _sf ? paSrcFaceSrc(_sf, '文件', _fFile)\n        : '为何未接：读源未给（GET /v9/pa/source_faces 未应答 ∨ 未载 ⇒ 照实）',\n    !!(_sf && !_fFile));",
         "  paSrcWrite('srcRowFile', '📄 文件',\n    _sf ? (paSrcFaceValue(_fFile) || '（后端应答无 量 ⇒ 照实缺）')\n        : PA_GAP.todo('读源未给（GET /v9/pa/source_faces 未应答 ∨ 未载 ⇒ 照实）'),\n    paSrcFaceSrc(_sf, '文件', _fFile),\n    !!(_sf && !_fFile));"),
        ("sub",
         "  paSrcWrite('srcRowDraw', '🎨 出图',\n    _sf ? (paSrcFaceValue(_fDraw) || '（后端应答无 量 ⇒ 照实缺）') : PA_GAP.todo(),\n    _sf ? paSrcFaceSrc(_sf, '出图', _fDraw)\n        : '为何未接：读源未给（GET /v9/pa/source_faces 未应答 ∨ 未载 ⇒ 照实）',\n    !!(_sf && !_fDraw));",
         "  paSrcWrite('srcRowDraw', '🎨 出图',\n    _sf ? (paSrcFaceValue(_fDraw) || '（后端应答无 量 ⇒ 照实缺）')\n        : PA_GAP.todo('读源未给（GET /v9/pa/source_faces 未应答 ∨ 未载 ⇒ 照实）'),\n    paSrcFaceSrc(_sf, '出图', _fDraw),\n    !!(_sf && !_fDraw));"),
    ]),
]
EDITS = {"渲槽": 渲槽}
ORDER = ["渲槽"]
BASES = [
    ('渲槽', 0, 'web/pa/faces/today.js', '24a5b3a8013b595a', '7b90cfb8111bbc2e'),
]


def _bridge():
    u"""底名之桥：以 CW 器之底（A 形）或 HEAD blob 备 safe_edit 之底（名 ≡ 值）。"""
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
    sys.exit(S.cli(EDITS, ORDER, bases=BASES, title=u"渲槽修 · why 归值格 · 源行 ＝ 源之径（∨ 空）"))
