# -*- coding: utf-8 -*-
u"""recipe —— 底链批 · tasks.js :758（源格手写态形 ⇒ 去 · 一处定形）（一改一底）。

字面之据（**机读** · ⛔ 手抄）：由**底**（<件>.before_fcf0bfddd808794e）与**现读之件**机构 ⇒ OLD/NEW。
承：pm 1287 §二（裁 :758 ＝ 同法修）／ pm 1288 §二.⒊（另批落）／ CW 1288 §二（改手 · 二处同形）。
底链之序（承 CW 1288 §二）：d3242e2a2fbf9b14 ─▶ fcf0bfddd808794e（:762 · 已落 2a8803c）─▶ 本批（:758）。

底名之桥（承 pm 1258 §二）：CW 之底 ＝ tasks.js.before_fcf0bfddd808794e（A 形）；本器之底 ＝ .before_fcf0bfddd808794e.tasks.js。
用法：python -X utf8 -B <本件> 底链 [--apply]   （⛔ 无 --apply ⇒ 只演）
      python -X utf8 -B <本件> --verify
"""
import os
import subprocess
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import safe_edit as S

底链 = [
    (u'web/pa/faces/tasks.js · :758（paXUnreached 之「源格手写态形 ＋ 辨义」⇒ 去 · 一处定形）', 'web/pa/faces/tasks.js', [
        ("sub",
         "    '源：' + why + ' —— **不可达**（此刻不在）≠ **未接**（后端无此面 · 承 pm_刀12p §〇）', true);",
         "    '源：' + why, true);"),
    ]),
]
EDITS = {"底链": 底链}
ORDER = ["底链"]
BASES = [
    ('底链', 0, 'web/pa/faces/tasks.js', 'fcf0bfddd808794e', 'd59658db8b6ba0d4'),
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
    sys.exit(S.cli(EDITS, ORDER, bases=BASES, title=u"底链批 · tasks.js :758（源格手写态形 ⇒ 去 · 一处定形）"))
