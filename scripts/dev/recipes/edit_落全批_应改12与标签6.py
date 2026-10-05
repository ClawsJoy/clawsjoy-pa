# -*- coding: utf-8 -*-
u"""recipe —— 落全批：应改 12 ＋ 标签正形 6（web/pa 四件 · 18 行 ／ 20 对 · 一改一底）。

字面之据（**机读** · ⛔ 手抄）：CW 之器 ——
  _pm/_cw_b5fix.py  sha16 132fa575ef1b13db · JOBS ＝ 4 件 ／ 20 对（collect 1 ／ session 2 ／ tasks 3 ／ selfdesc 14）
承：PM 1279 §四（令落全批 · 应改 12 ＋ 标签 · `:1282` 用终形 ⒜′）／ CW 1280 §一（三物）。

底名之桥（承 PM 1259 §三 ／ 1262 §四）：CW 器之底 ＝ `<件名>.before_<旧印>`（A 形）；
  本器（safe_edit）之底 ＝ `.before_<旧印>.<件名>` ⇒ 以 CW 之底备之（名 ≡ 值）；
  射程裁（全仓）后随「正名之批」归一（另批）。
用法：python -X utf8 -B <本件> 全批 [--apply]   （⛔ 无 --apply ⇒ 只演）
      python -X utf8 -B <本件> --verify
"""
import os
import subprocess
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import safe_edit as S

全批 = [
    (u'web/pa/faces/collect.js · 应改 06', 'web/pa/faces/collect.js', [
        ("sub",
         "setCollectMsg('后端不可达')",
         "setCollectMsg(PA_GAP.down('后端'))"),
    ]),
    (u'web/pa/faces/session.js · 应改 40／41', 'web/pa/faces/session.js', [
        ("sub",
         "_fail:'未接（后端已应答但非 ok · HTTP '+r.status+'）',",
         "_fail: PA_GAP.todo('后端已应答但非 ok · HTTP '+r.status),"),
        ("sub",
         "_fail:'不可达（后端此刻不在 ／ 请求失败）',",
         "_fail: PA_GAP.down('后端此刻不在 ／ 请求失败'),"),
    ]),
    (u'web/pa/faces/tasks.js · 应改 48／52／54', 'web/pa/faces/tasks.js', [
        ("sub",
         "o.textContent = '席册不可达（GET /v9/pa/seats 未应答）';",
         "o.textContent = PA_GAP.down('席册：GET /v9/pa/seats 未应答');"),
        ("sub",
         "paRow('对表', '不可达（未应答 ⇒ ⛔ 判不齐）', '面：GET /v9/pa/env', true)",
         "paRow('对表', PA_GAP.down('未应答 ⇒ ⛔ 判不齐'), '面：GET /v9/pa/env', true)"),
        ("sub",
         "o.textContent = '册不可达（POST /v9/pa/agent/invoke {} 未应答）';",
         "o.textContent = PA_GAP.down('册：POST /v9/pa/agent/invoke {} 未应答');"),
    ]),
    (u'web/pa/faces/selfdesc.js · 应改 6 ＋ 标签 6（12）', 'web/pa/faces/selfdesc.js', [
        ("sub",
         "(nThr === null ? '不可达 ／ 无读数' : nThr + ' 条')",
         "(nThr === null ? PA_GAP.down('无读数') : nThr + ' 条')"),
        ("sub",
         "(nRun === null ? '不可达 ／ 无读数' : nRun + ' 件')",
         "(nRun === null ? PA_GAP.down('无读数') : nRun + ' 件')"),
        ("sub",
         "(nL === null ? '不可达' : nL + ' 行')",
         "(nL === null ? PA_GAP.down() : nL + ' 行')"),
        ("sub",
         "(fl ? (fl.nTask + ' 任务 ／ ' + fl.tools.length + ' 工具') : '不可达')",
         "(fl ? (fl.nTask + ' 任务 ／ ' + fl.tools.length + ' 工具') : PA_GAP.down())"),
        ("sub",
         "(nSub === null ? '不可达 ／ 无读数' : (nSub + ' 件'))",
         "(nSub === null ? PA_GAP.down('无读数') : (nSub + ' 件'))"),
        ("sub",
         "'· ⚠ 不可达（后端此刻不在 ⇒ ⛔ ≠ 未接）：'",
         "'· ⚠ 不可达（后端此刻不在）：'"),
        ("sub",
         "'· ⚠ 不可达（⛔ ≠ 未接 · 承 pm_刀12p §〇）：'",
         "'· ⚠ 不可达：'"),
        ("sub",
         '\'<div class="na">⚠ 不可达（⛔ ≠ 未接） \'',
         '\'<div class="na">⚠ 不可达 \''),
        ("sub",
         "'· ⭐ ⒝⛔不接（**红线** ⇒ ⛔ 待办 · 不会有）：'",
         "'· ⭐ ⒝ ⛔ 不接（红线）：'"),
        ("sub",
         "'· 操作：改令（准接 · POST /v9/pa/steer）｜接管（待立项 · 须先定义）｜真实平台面（⛔ 不接 · 红线）｜夜间整合（无后端面）'",
         "'· 操作：改令：准接 · POST /v9/pa/steer｜接管：待立项 · 须先定义｜真实平台面 ⛔ 不接（红线）｜夜间整合：无后端面'"),
        ("sub",
         "'· ⭐ ⒝⛔不接（红线 ⇒ ⛔ 待办）：'",
         "'· ⭐ ⒝ ⛔ 不接（红线）：'"),
        ("sub",
         "' · ⒜未接·待办 '",
         "' · ⒜ 未接 · 待办（M1） '"),
        ("sub",
         "' · ⛔不接（红线）'",
         "' · ⛔ 不接（红线）'"),
        ("sub",
         '\'<div class="na">⭐ 画像素材面 · ⒝⛔不接（红线 ⇒ ⛔ 待办） \'',
         '\'<div class="na">⭐ 画像素材面 · ⒝ ⛔ 不接（红线） \''),
    ]),
]
EDITS = {"全批": 全批}
ORDER = ["全批"]
BASES = [
    ('全批', 0, 'web/pa/faces/collect.js', '4a7e589d9350dd27', '255714c7530125e8'),
    ('全批', 1, 'web/pa/faces/session.js', '41af3ce898ee0638', '06ec3a228899757f'),
    ('全批', 2, 'web/pa/faces/tasks.js', '9d8af7b22e11b6e8', 'd3242e2a2fbf9b14'),
    ('全批', 3, 'web/pa/faces/selfdesc.js', '073f1b0f05171914', '61e4866a0b926748'),
]


def _bridge():
    u"""底名之桥：以 CW 器之底（A 形）备 safe_edit 之底（名 ≡ 值）。"""
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
    sys.exit(S.cli(EDITS, ORDER, bases=BASES, title=u"落全批 · 应改 12 ＋ 标签 6（四件 · 20 对）"))
