# -*- coding: utf-8 -*-
u"""recipe —— 槽族批：tasks.js :762 之「源格手写态形」⇒ 去（一处定形 · 一改一底）。

字面之据（**机读** · ⛔ 手抄）：CW 之器 _pm/_cw_slot3.py · 其 OLD 由**底**取（⛔ 由报之文）。
承：pm 1263 §二（逮）／ pm 1279 §四（形）／ pm 1284 §四（令落 · **落手归 TD**）／ CW 1285 §二（改手）。

底名之桥（承 pm 1258 §二）：CW 之底 ＝ tasks.js.before_d3242e2a2fbf9b14（A 形）；本器之底 ＝ .before_d3242e2a2fbf9b14.tasks.js。
用法：python -X utf8 -B <本件> 槽族 [--apply]   （⛔ 无 --apply ⇒ 只演）
      python -X utf8 -B <本件> --verify
"""
import os
import subprocess
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import safe_edit as S

槽族 = [
    (u'web/pa/faces/tasks.js · :762（源格手写「回退支」⇒ 去 · 一处定形）', 'web/pa/faces/tasks.js', [
        ("sub",
         "'源：' + why + ' —— **回退支**（后端未给此键 ' + (key || why) + ' ⇒ 此刻不可达）≠ 空（承 pm_076 §一）', true);",
         "'源：' + why, true);"),
    ]),
]
EDITS = {"槽族": 槽族}
ORDER = ["槽族"]
BASES = [
    ('槽族', 0, 'web/pa/faces/tasks.js', 'd3242e2a2fbf9b14', 'fcf0bfddd808794e'),
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
    sys.exit(S.cli(EDITS, ORDER, bases=BASES, title=u"槽族批 · tasks.js :762（源格手写态形 ⇒ 去）"))
