# -*- coding: utf-8 -*-
u"""recipe —— 落账归一：投一步.py 之 recv 归一为台账之名（别名只作「入」）。

承：pm 1298 §二（裁）｜pm 1302 §四.2（令：其件 ＝ 同域 · 唯另 commit）｜CW 1300 §五.5（二名一事之核）
其的：SEATS 之二键（别名）唯作「入」；落行之 recv 取台账之正规名（CANON 一处）⇒ ⛔ 二名入账。
用法：python -X utf8 -B <本件> 落账归一 [--apply]     （⛔ 无 --apply ⇒ 只演）
      python -X utf8 -B <本件> --verify
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import safe_edit as S

REL = 'scripts/dev/投一步.py'

落账归一 = [
    ('投一步.py（docstring ＋ CANON ＋ main ＋ 自证 5 · 六 sub 一气落）', REL, [
        ("sub", '  ⚠ 席名（2026-10-06 承 pm 1294 §三 · 并收）：CW 席之**台账名** ＝ 「CodexWindows线」（⛔ SEATS 之「V9工程师·全史席」）\n    ⇒ 二键并存 · **以台账之名为准**（投 CW 之件 ⇒ --to CodexWindows线 · 免 --to-id）。', '  ⚠ 席名（2026-10-06 承 pm 1294 §三 · 并收 ／ pm 1298 §二 · 落账归一）：CW 席之**台账名** ＝ 「CodexWindows线」\n    （⛔ SEATS 之「V9工程师·全史席」）⇒ 二键并存（**别名只作「入」** ⇒ 投 CW 之件免 --to-id）\n    ⇒ ⭐⭐ **落行须归一为台账之名**（CANON：V9工程师·全史席 ⇒ CodexWindows线）⇒ ⛔ 别名入账。'),
        ("sub", '    u"CodexWindows线": "b2a5182",\n}', '    u"CodexWindows线": "b2a5182",\n}\n\n# 2026-10-06 承 pm 1298 §二（**落账归一**）｜pm 1302 §四.2（令）：\n# 别名只作「入」⇒ **落行之 recv 须归一为台账之名**（⛔ 二名入账 ⇒ 扫 CW 之件必漏）。\nCANON = {\n    u"V9工程师·全史席": u"CodexWindows线",\n}'),
        ("sub", '    name = a.name or os.path.basename(a.src)', '    recv = CANON.get(a.to, a.to)\n    name = a.name or os.path.basename(a.src)'),
        ("sub", '    print(u"【投一步】%s ｜ 件 ＝ %s ｜ 席 ＝ %s（%s）｜ 号 ＝ %s ／ 日 ＝ %s ／ 类 ＝ %s"\n          % (u"演（⛔ 落盘 · 加 --go 真办）" if dry else u"真办", name, a.to, tid, a.num, date, a.cat))', '    print(u"【投一步】%s ｜ 件 ＝ %s ｜ 席 ＝ %s（%s）｜ 号 ＝ %s ／ 日 ＝ %s ／ 类 ＝ %s"\n          % (u"演（⛔ 落盘 · 加 --go 真办）" if dry else u"真办", name, a.to, tid, a.num, date, a.cat))\n    if recv != a.to:\n        print(u"落账之名（归一）＝ %s（别名「%s」唯作入 · ⛔ 入账 · 承 pm 1298 §二）" % (recv, a.to))'),
        ("sub", '                      (u"② 落行", lambda: step_land(a.num, date, a.sender, a.to, name, a.cat,', '                      (u"② 落行", lambda: step_land(a.num, date, a.sender, recv, name, a.cat,'),
        ("sub", '    print(u"[总判] %s" % (u"PASS" if ok else u"FAIL"))', '    print(u"[自证 5 席名归一（承 pm 1298 §二 ／ pm 1302 §四.2 · 别名 ⛔ 入账）]")\n    res(u"SEATS 二键 ⇔ 同 id（别名只作入）", SEATS.get(u"V9工程师·全史席") == SEATS.get(u"CodexWindows线"), True)\n    res(u"CANON 归一台账之名", CANON.get(u"V9工程师·全史席"), u"CodexWindows线")\n    res(u"CANON 幂等", CANON.get(u"CodexWindows线", u"CodexWindows线"), u"CodexWindows线")\n    print(u"[总判] %s" % (u"PASS" if ok else u"FAIL"))'),
    ]),
]
EDITS = {u"落账归一": 落账归一}
ORDER = [u"落账归一"]
BASES = [
    (u'落账归一', 0, REL, '4675fefe1eac7af7', '10aef7b1a3677592'),
]

if __name__ == "__main__":
    sys.exit(S.cli(EDITS, ORDER, bases=BASES, title=u"落账归一 · 投一步.py recv 归一为台账之名"))
