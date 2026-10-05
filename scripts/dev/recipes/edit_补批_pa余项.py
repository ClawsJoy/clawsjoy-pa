# -*- coding: utf-8 -*-
u"""recipe —— 补批：pa.html 余项（五处「读数中…」⇒ 无 JS 兜底 ＋ :227 二行 · 一改一底）。

字面之据（**机读** · ⛔ 手抄）：CW 之表 _pm/_cw_lit3.py 之 PAIRS（5 对 · 由现读之件机构）。
承：pm 1284 §三.⒈（五处准改 · 须明「无 JS」）／ §三.⒉（:227 准并二行 · 两名分列）／
    pm 1286 §三（:221 之「7 面」⛔ 变 —— 面数 ≠ 行数）／ pm 1286 §五（令落件）。
⚠ 类（n ／ n na）⛔ 动（守 pm 1284 §一）｜:227 之二行 id 为运行期幂等所必需（CW 之表 NOTE）。

底（本器 · B 形）：.before_559edaf3b7a70713.pa.html（由 safe_edit 之 make_backup 自建 · 取自读）。
用法：python -X utf8 -B <本件> 补批 [--apply]   （⛔ 无 --apply ⇒ 只演）
      python -X utf8 -B <本件> --verify
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import safe_edit as S

补批 = [
    (u'web/pa.html · 补批（:221 ／ :223 ／ :225 ／ :227 ／ :229）', 'web/pa.html', [
        ("sub",
         '    <div class="srcsum" id="paSrcSummary" onclick="paSrcToggle()" title="本机全上下文＝素材库（只索引）；点开看逐面读数">素材 7 面 ⇒ <b id="paSrcSum">读数中…</b> <span class="caret" id="paSrcCaret">▾</span></div>',
         '    <div class="srcsum" id="paSrcSummary" onclick="paSrcToggle()" title="本机全上下文＝素材库（只索引）；点开看逐面读数">素材 7 面 ⇒ <b id="paSrcSum">⚠ 无 JS：无读数（须运行期）</b> <span class="caret" id="paSrcCaret">▾</span></div>'),
        ("sub",
         '      <div class="it">💬 会话（含席）<span class="n" id="srcChat">读数中…</span></div>',
         '      <div class="it">💬 会话（含席）<span class="n" id="srcChat">⚠ 无 JS：无读数（须运行期）</span></div>'),
        ("sub",
         '      <div class="it">🧾 台账（机账）<span class="n na">读数中…（三本机账：dispatch/history ／ deliver/authz ／ lines）</span></div>',
         '      <div class="it">🧾 台账（机账）<span class="n na">⚠ 无 JS：无读数（须运行期 · 三本机账：dispatch/history ／ deliver/authz ／ lines）</span></div>'),
        ("sub",
         '      <div class="it">🧰 作业<span class="n" id="srcRuns">读数中…</span></div>',
         '      <div class="it" id="srcRowDispatch">🧰 作业（调度件）<span class="n">⚠ 无 JS：无读数（须运行期）</span></div>\n      <div class="it" id="srcRowRuns">🧰 作业（PES 运行）<span class="n" id="srcRuns">⚠ 无 JS：无读数（须运行期）</span></div>'),
        ("sub",
         '      <div class="it">🧠 记忆自身·二次提取<span class="n" id="srcCtx">读数中…</span></div>',
         '      <div class="it">🧠 记忆自身·二次提取<span class="n" id="srcCtx">⚠ 无 JS：无读数（须运行期）</span></div>'),
    ]),
]
EDITS = {"补批": 补批}
ORDER = ["补批"]
BASES = [
    ('补批', 0, 'web/pa.html', '559edaf3b7a70713', '3026b32268a5b174'),
]


if __name__ == "__main__":
    sys.exit(S.cli(EDITS, ORDER, bases=BASES, title=u"补批 · pa.html 余项（五处无 JS 兜底 ＋ :227 二行）"))
