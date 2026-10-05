# -*- coding: utf-8 -*-
u"""recipe —— 接线批三：乙-1..4 渲形（web/pa.html:113-116）＋ 乙-7 重书（:110）（一改一底）。

字面之据：CW 1239 §四／§五（逐字）＋ CW 1242 §三 ⒝（PM 1244 §二 定：:113 须存其内容 ⇒ 形 ＋ 「 —— 」 ＋ 其内容）。
⛔ 通用之器在 ../safe_edit.py；本件唯「本批之字面」。
用法：python -X utf8 -B <本件> <乙|all> [--apply]   （⛔ 无 --apply ⇒ 只演）
      python -X utf8 -B <本件> --verify            （由底回放 ／ 比对记录之「出」）
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import safe_edit as S

乙 = [("web/pa.html · 接线批三（乙-7 :110 重书 ＋ 乙-1..4 :113-116 渲形）", "web/pa.html", [
    ("sub", u'<p class="mnote">真读数须后端方有 ⇒ 未接之项显式标「未接（M1）」· ⛔ 冒真读数。</p>',
            u'<p class="mnote">真读数须后端方有 ⇒ 四态各明标（一处定形 · 承 core.js:73-77）：⒜ 未接 · 待办（M1） ｜ ⒝ ⛔ 不接（其 kind：红线 ／ 已转产品线 ／ 无后端面） ｜ ⒞ 不可达（特形 ＝ 回退支：后端应答在 · 唯键不在） ｜ ⭐ ⒟ 陈旧（数是真的 · 刻是旧的）· ⛔ 以「未接」一名盖之 · ⛔ 冒真读数。</p>'),
    ("sub", u'<span class="k">托盘</span><span>未接（M1） —— 常驻的是<b>壳与调度</b>，⛔ 模型</span>',
            u'<span class="k">托盘</span><span>⛔ 不接（无后端面：常驻的是壳与调度 · ⛔ 模型 · 真源 ＝ Electron 壳（HKCU\\...\\Run ／ 壳之菜单）· PA 后端 ⛔ 持此值 ⇒ ⛔ 冒真读数）</span>'),
    ("sub", u'<span class="k">自启</span><span>未接（M1） —— 默认开 ＋ 设置里一键关（首启问一次）</span>',
            u'<span class="k">自启</span><span>⛔ 不接（无后端面：其面已读（GET /v9/pa/resume · version 2026-10-05.2 · 22 键）· 唯不含自启之值（其键皆断点续）⇒ 真源 ＝ 壳 ／ 注册表（HKCU\\...\\Run）⇒ 候「壳行为之实做」立项 ⇒ 一并开面）</span>'),
    ("sub", u'<span class="k">关窗</span><span>未接（M1） —— 默认隐到托盘（≠退出）</span>',
            u'<span class="k">关窗</span><span>⛔ 不接（无后端面：真源 ＝ Electron 壳（默认隐到托盘 · ≠退出）· PA 后端 ⛔ 持此值）</span>'),
    ("sub", u'<span class="k">夜间整合</span><span>未接（M1） —— 轻量路径 · ⛔ 抢显卡（与出图互斥检测）</span>',
            u'<span class="k">夜间整合</span><span>⛔ 不接（无后端面：真源 ＝ Electron 壳 ／ 调度（轻量路径 · ⛔ 抢显卡 · 与出图互斥检测）· PA 后端 ⛔ 持此值（运行期之文 ＝ today.js:412））</span>'),
])]

补 = [("web/pa.html · 补正 :114（其内容须存 · 承 CW 1245 §二 ／ PM 1248 §二）", "web/pa.html", [
    ("sub", u'<span class="k">自启</span><span>⛔ 不接（无后端面：其面已读（GET /v9/pa/resume · version 2026-10-05.2 · 22 键）· 唯不含自启之值（其键皆断点续）⇒ 真源 ＝ 壳 ／ 注册表（HKCU\\...\\Run）⇒ 候「壳行为之实做」立项 ⇒ 一并开面）</span>',
            u'<span class="k">自启</span><span>⛔ 不接（无后端面：默认开 ＋ 设置里一键关（首启问一次）· 其面已读（GET /v9/pa/resume · version 2026-10-05.2 · 22 键）· 唯不含自启之值（其键皆断点续）⇒ 真源 ＝ 壳 ／ 注册表（HKCU\\...\\Run）⇒ 候「壳行为之实做」立项 ⇒ 一并开面）</span>'),
])]

EDITS = {"乙": 乙, "补": 补}
ORDER = ["乙", "补"]

# 何批之改 ⇒ 用何器之印（底 ⇒ 出 · 供 --verify 由底回放）
BASES = [
    ("乙", 0, "web/pa.html", "278af595116c100d", "18a586f33a23c3c3"),
    ("补", 0, "web/pa.html", "18a586f33a23c3c3", "457bfb72106b59cb"),
]

if __name__ == "__main__":
    raise SystemExit(S.cli(EDITS, ORDER, bases=BASES, title=u"接线批三 · 乙-1..4 渲形 ＋ 乙-7 重书（一改一底）"))
