# -*- coding: utf-8 -*-
u'''recipe —— 落批一：pa.html :116（静 ≡ 动 逐字）＋ core.js :59（去数形 · 承 pm 1297 §三① ／ pm 1299）。

承：pm 1299（字面）｜pm 1302 §一（令：落手四件 · 批一 ＝ pa.html ＋ core.js 同批）。
其的：pa.html :116 之静文 ⇒ 与 today.js:413 之渲形**逐字≡**（title 载其由）；core.js :59 去「3」之数引。
用法：python -X utf8 -B <本件> 批一 [--apply]   （⛔ 无 --apply ⇒ 只演）
      python -X utf8 -B <本件> --verify
'''
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import safe_edit as S

批一 = [
    (u'pa.html :116（夜间整合 ⇒ 静 ≡ 动 逐字 ＋ title 载由）', 'web/pa.html', [
        ("sub",
         u'''          <div class="r"><span class="k">夜间整合</span><span>⛔ 不接（无后端面：真源 ＝ Electron 壳 ／ 调度（轻量路径 · ⛔ 抢显卡 · 与出图互斥检测）· PA 后端 ⛔ 持此值（运行期之文 ＝ today.js:412））</span></div>''',
         u'''          <div class="r"><span class="k">夜间整合</span><span title="真源 ＝ Electron 壳 ／ 调度（轻量路径 · ⛔ 抢显卡 · 与出图互斥检测）· PA 后端 ⛔ 持此值｜运行期之文见 today.js:413（paLoadToday 内）⇒ 本行静文 ≡ 其渲形（承 pm 1297 §三①）">未知 —— ⒜ 未接 · 待办（M1）｜为何未接：无源（夜间整合无后端面 · 承 pm 18:00 批一） · ⛔ 编</span></div>'''),
    ]),
    (u'core.js :59（其 3 行静态标 ⇒ 其属此三形之静态标）', 'web/pa/core.js', [
        ("sub",
         u'''其 3 行静态标**逐字抄此三形**''',
         u'''其属此三形之静态标**逐字抄此三形**'''),
    ]),
]
EDITS = {"批一": 批一}
ORDER = ["批一"]
BASES = [
    ('批一', 0, 'web/pa.html', '3026b32268a5b174', 'e2567f4393f33e26'),
    ('批一', 1, 'web/pa/core.js', '77976ddccd7c54e4', 'ddcd1b9372bc37da'),
]


if __name__ == "__main__":
    sys.exit(S.cli(EDITS, ORDER, bases=BASES, title=u"落批一 · pa.html ＋ core.js"))
