# -*- coding: utf-8 -*-
r"""recipe —— pm_1575 §三：安装页 §六.5 与 `5b` 之辞之洽（一改一底 · 本件之树 ＝ 本件所在之仓）。

字面之据（器取 · ⛔ 手抄）：
  ⒜ 码（副本）：`core/gateway/ui_state.py` ⇒ `write_once()` 落 `<root>/web/pa/ui_state.json`（服务启动前一次 ·
     `boot.py` 之 `write_once_bounded`）；成 ⇒ 印「已落」／败 ⇒ 印「⛔ 落 … 界面将显「未载入」（已知貌）」。
  ⒝ 前端之触发：`web/pa/faces/more.js` ⇒ `if(el && !d)` ⇒ 「快照读不到 · 版本或暂不可用 ⇒ 本行按「未知」记」；
     `status.js` ⇒ `if(!r.ok)` ⇒ 404 ／ 坏体 ⇒ 返 null ⇒ `!d` ⇒ 该行出。**唯「取不到」一因**（⛔ 版本 ／ ⛔ 陈旧）。
  ⒞ 我一手之控（真跑 · 副本之码）：
     正控（新树 · ⛔ 目录 ⛔ 件 · 可写）⇒ `write_once` True ＋「已落 … 247 B」＋ 件在 ∧ 九键 ∧ ⛔BOM ∧ CR 0 ∧ 末 LF
       ⇒ GET 200 ⇒ `!d` ⛔ 入 ⇒ 该行 **⛔ 出**。
     反控（同树 · icacls deny W）⇒ `write_once` False ＋「⛔ 落（PermissionError …）—— 界面将显「未载入」」＋ 件 ⛔ 在
       ⇒ GET 404 ⇒ `!d` ⇒ 该行 **出**。
  ⇒ 判：§六.5 之因「这台机器还没存过这个文件」＝ **1558 前之旧常路**（今服务自落已成 ⇒ 起完服务该件恒在）
     ⇒ 与 `5b` **⛔ 洽**（今之真因唯：写失败 ／ 落未及 6 s）⇒ 正之（承 PM 1575 §三.2）。
根：本器所改之树 ＝ 本件所在之仓（root=ROOT）。
用法：python -X utf8 -B <本件> doc [--apply]（⛔ 无 --apply ⇒ 只演）
      python -X utf8 -B <本件> --verify
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import safe_edit as S

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))

_OLD5 = (u'5. **顶上出现一条黄色小字：「快照读不到 · 版本或暂不可用 ⇒ 本行按「未知」记」，旁边还有一个「⚠ 取数刻未给」。**_⇒ 正常。_\n'
         u'   这台机器还没存过「界面态快照」这个文件，程序就**照实说一句「不知道」**，⛔ 不是装坏。\n'
         u'   （它**不会**把不知道的东西写成「正常」。）')

_NEW5 = (u'5. **顶上若出现一条黄色小字：「快照读不到 · 版本或暂不可用 ⇒ 本行按「未知」记」，旁边还有一个「⚠ 取数刻未给」。**\n'
         u'   **起完服务之后，这一行不该再出现** —— 程序在**开始服务之前**就会自己把「界面态快照」这个文件落好（见 5b）。\n'
         u'   如果**仍然**看到 ⇒ 多半是**那个文件没写进去**（装到了需要管理员权限的目录）⇒ 照 5b 看服务窗口那一行；⛔ 不是装坏。\n'
         u'   （它**不会**把不知道的东西写成「正常」。）')

_OLD179 = u'   （看不到这一条也**没关系** —— 不做这一步，第 5 条那种「未知」之貌依然是正常。）'

_NEW179 = u'   （第 5 条那种「未知」之貌 —— **起完服务之后不该再看到**；若看到 ⇒ 即上面所列之二支之一，照其办即可。）'

doc = [
    (u'scripts/win_pa/净机安装一页.md · §六.5 与 5b 之洽', 'scripts/win_pa/净机安装一页.md', [
        ("sub", _OLD5, _NEW5),
        ("sub", _OLD179, _NEW179),
    ]),
]

EDITS = {"doc": doc}
ORDER = ["doc"]
BASES = []


if __name__ == "__main__":
    sys.exit(S.cli(EDITS, ORDER, bases=BASES, title=u"pm_1575 §三 · 安装页 §六.5 之正 · 核（doc）", root=ROOT))