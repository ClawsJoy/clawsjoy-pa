# -*- coding: utf-8 -*-
u"""recipe —— 席名并收（SEATS ⇒ 加台账名别名「CodexWindows线」· 二名一事之并收）。

承：pm 1294 §三（**核而并收** · 二名一事：SEATS 之「V9工程师·全史席」⟷ 台账之「CodexWindows线」）
    ｜pm 1290 §五（一件一器）｜pm 1292 §四（一批一 commit）。
其的：⛔ 二名致误 ⇒ 二键并存 · **以台账之名为准**（投 CW 之件 ⇒ --to CodexWindows线 · 免 --to-id）。
用法：python -X utf8 -B <本件> 席名并收 [--apply]   （⛔ 无 --apply ⇒ 只演）
      python -X utf8 -B <本件> --verify
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import safe_edit as S

席名并收 = [
    (u'投一步.py（SEATS ⇒ 加别名键 ＋ docstring 之注）', 'scripts/dev/投一步.py', [
        ("sub",
         u'SEATS = {\n    u"项目经理": "b136893",\n    u"技术总监": "f202f89",\n    u"V9工程师·全史席": "b2a5182",\n}',
         u'SEATS = {\n    u"项目经理": "b136893",\n    u"技术总监": "f202f89",\n    u"V9工程师·全史席": "b2a5182",\n    # 2026-10-06 承 pm 1294 §三（**核而并收** · 二名一事）：台账内 CW 席之名 ≡ 「CodexWindows线」\n    # （我一手核 · 全 1,540 行：发件 384 ／ 收件 78 ／ 全册 ⛔ 见「V9工程师·全史席」）。\n    # ⇒ 并收为**别名键**（**台账之名为准** ⇒ 投 CW 之件免 --to-id · ⛔ 二名致误）。\n    u"CodexWindows线": "b2a5182",\n}'),
        ("sub",
         u'  python -X utf8 -B scripts\\dev\\投一步.py --self-test   # 自证（含 **反控**：醒必败 ⇒ 须返非零）',
         u'  python -X utf8 -B scripts\\dev\\投一步.py --self-test   # 自证（含 **反控**：醒必败 ⇒ 须返非零）\n  ⚠ 席名（2026-10-06 承 pm 1294 §三 · 并收）：CW 席之**台账名** ＝ 「CodexWindows线」（⛔ SEATS 之「V9工程师·全史席」）\n    ⇒ 二键并存 · **以台账之名为准**（投 CW 之件 ⇒ --to CodexWindows线 · 免 --to-id）。'),
    ]),
]
EDITS = {"席名并收": 席名并收}
ORDER = ["席名并收"]
BASES = [
    ('席名并收', 0, 'scripts/dev/投一步.py', '17d94ba4c27864f8', '9be0af5e07d62e85'),
]


if __name__ == "__main__":
    sys.exit(S.cli(EDITS, ORDER, bases=BASES, title=u"席名并收 · 投一步.py"))
