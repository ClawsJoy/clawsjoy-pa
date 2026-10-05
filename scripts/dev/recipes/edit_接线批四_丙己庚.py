# -*- coding: utf-8 -*-
u"""recipe —— 接线批四：丙 ／ 己 ／ 庚（web/pa 四件 · 十处 ＋ 沿改二处 · 一改一底）。

字面之据（**机读** · ⛔ 手抄）：CW 之三器 ——
  _pm/_cw_p4edit.py  sha16 36f1c872e967a2b6 · E ＝ 10 处（丙-1..7 ／ 己-1..2 ／ core.js:63）
  _pm/_cw_p4fix.py   sha16 633d6eeee7170c6b · R  ＝ 2 处（paSteerPost 错支 ⇒ PA_GAP.down）
  _pm/_cw_p4fix2.py  sha16 a7e5412225bad48b · R2 ＝ 2 处（:519-520 沿改 · title 双身）
施之序：E（逐件）⇒ R（tasks.js）⇒ R2（tasks.js） —— 与 CW 三器之序 ≡。
承：PM 1261 §三（落手四须 · 件 4 ＋ 器 3）／ PM 1255 §四 ／ PM 1259 §三。

底名之桥（承 PM 1259 §三 ／ 1262 §四）：CW 器之底 ＝ `<件名>.before_<旧印>`；
  本器（safe_edit）之底 ＝ `.before_<旧印>.<件名>` ⇒ 以 HEAD blob（名 ≡ 值）备之；
  射程裁（全仓）后随「正名之批」归一（另批）。
用法：python -X utf8 -B <本件> 批四 [--apply]   （⛔ 无 --apply ⇒ 只演）
      python -X utf8 -B <本件> --verify
"""
import os
import subprocess
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import safe_edit as S

批四 = [
    (u'web/pa/core.js · 庚（core.js:63 · off 增默认参）', 'web/pa/core.js', [
        ("sub",
         "  off:  function(why){ return '⛔ 不接（红线' + (why ? ('：' + why) : '') + '）'; },",
         "  off:  function(why, kind){ return '⛔ 不接（' + (kind || '红线') + (why ? ('：' + why) : '') + '）'; },"),
    ]),
    (u'web/pa/faces/tasks.js · 丙-1..6 ＋ R ＋ R2', 'web/pa/faces/tasks.js', [
        ("sub",
         "      '源：' + PA_GAP.todo('无读源') + ' —— POST /v9/pa/dialog ／ POST /v9/agent/chat 为**写路**（⛔ 读源）⇒ 后端无「受理态」读面｜本页计数 ＝ 本页已接（⛔ 后端口径 · ⛔ 以 0 充未接）')",
         "      '源：' + PA_GAP.todo('后端无「受理态」读面 —— POST /v9/pa/dialog ／ POST /v9/agent/chat 为写路（⛔ 读源）') + '｜本页计数 ＝ 本页已接（本页口径 · ⛔ 后端口径 · ⛔ 以 0 充未接）')"),
        ("sub",
         "    + '<br>输入分类（新任务 ／ 改令 ／ 追问 ／ 闲聊）' + PA_GAP.todo('无端点（按真实意图分，⛔ 不按「忙」分）') + '。</div>'",
         "    + '<br>输入分类（新任务 ／ 改令 ／ 追问 ／ 闲聊）' + PA_GAP.todo('后端无端点（须开读面 ⇒ 承批四）· 按真实意图分（⛔ 按「忙」分）') + '。</div>'"),
        ("sub",
         '    + \'<div class="gr"><button onclick="paIntervene(\\\'改令\\\')" disabled title="\' + PA_GAP.todo(\'无改令端点\') + \'">✏️ 改令 · \' + PA_GAP.todo() + \'</button>\'',
         '    + \'<div class="gr"><button onclick="paIntervene(\\\'改令\\\')" title="POST /v9/pa/steer（通道已在 ＝ shared_state.add_steer ／ drain_steer · 承 PM 1254）⇒ ⭐ 面不可达时明标「不可达」· ⛔ 静默">✏️ 改令</button>\''),
        ("sub",
         '    + \'<button onclick="paIntervene(\\\'中止\\\')" title="POST /v9/cancel/&lt;session_id&gt;（routes/session.py:37 · 会话级协作取消 ·置位取消标志 ⇒ bridge_loop 下轮检查点退出 · ⛔ 硬杀）">⏹ 中止本线程（会话级 · 下一步边界生效）</button>\'',
         '    + \'<button onclick="paIntervene(\\\'中止\\\')" title="POST /v9/cancel/&lt;session_id&gt;（routes/session.py · 会话级协作取消 · 置位取消标志 ⇒ bridge_loop 下轮检查点退出 · ⛔ 硬杀）">⏹ 中止本线程（会话级 · 下一步边界生效）</button>\''),
        ("sub",
         '    + \'<button onclick="paIntervene(\\\'接管\\\')" disabled title="\' + PA_GAP.todo(\'无接管端点\') + \'">🤝 接管 · \' + PA_GAP.todo() + \'</button></div></div>\'',
         '    + \'<button onclick="paIntervene(\\\'接管\\\')" disabled title="无此端点 —— 后端无「接管」之概念（gateway_routes.py 逐路名 0 命中）· ⭐ 待立项（须先定义：接谁的管 ／ 界在何 ／ 可否逆 ／ 是否触他方平台）">🤝 接管 · 待立项（须先定义）</button></div></div>\''),
        ("sub",
         "/* —— 干预（中止 ＝ 真端点；改令 ／ 接管 ＝ 未接）—— */\nasync function paIntervene(kind){\n  if(kind === '改令' || kind === '接管'){ return; }\n  const sid = curSession();\n  const out = document.getElementById('paSubOut');\n  try{\n    const r = await fetch(API + '/v9/cancel/' + encodeURIComponent(sid), {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'});\n    const d = await r.json().catch(function(){ return null; });\n    if(out) out.textContent = '中止：' + (d && d.success ? ('已置取消标志（' + (d.session_id || sid) + '）· 下一步边界生效')\n      : ('后端未确认（HTTP ' + r.status + '）· 如实记'));\n  }catch(e){\n    if(out) out.textContent = '中止：请求未送达（' + String((e && e.message) || e) + '）· ⛔ 不等于已中止';\n  }\n}",
         "/* —— 干预（中止 ＝ 真端点；改令 ＝ 准接（POST /v9/pa/steer）；接管 ＝ 待立项（须先定义））—— */\n/* ⭐ 丙-3／丙-6：改令 ＝ 准接（POST /v9/pa/steer · 承 PM 1254 ／ TD 1082 §二）。\n   ⚠ ⛔ 用 paGetJson（today.js 非 2xx ⇒ null ⇒ 与「不可达」同形 —— 空 ⛔ 混 缺）⇒ 本节自取 body（承 PM 1254 §二.⒉）。\n   信封从蓝图（ok）· 键从族（missing ／ kind ／ route）：承 PM 1253 §二 裁一。\n   queued:true ＝ 「已入队」（⛔ 「已生效」）⇒ 承 PM 1254 §二.⒊；⛔ 报 queued_count（通道唯 drain ⇒ 得数必先消费）。 */\nasync function paSteerPost(sid, text, kind){\n  try{\n    const r = await fetch(API + '/v9/pa/steer', {method:'POST', headers:{'Content-Type':'application/json'},\n      body: JSON.stringify({session_id: sid, text: text, kind: kind, user_id: curUser()})});\n    let d = null;\n    try{ d = await r.json(); }catch(e){ d = null; }\n    if(r.ok && d && d.ok === true){ return {ok:true, d:d}; }\n    /* 400 之三支须可辨（⛔ 以「提交失败」一辞盖之）—— 承 PM 1254 §二.⒉ */\n    if(d && d.kind === 'missing_param'){ return {ok:false, why:'缺参（' + (((d.missing || []).join(' ／ ')) || '?') + '）'}; }\n    if(d && d.kind === 'over_limit'){ return {ok:false, why:'超限（text ' + (d.text_len == null ? '?' : d.text_len) + ' ＞ ' + (d.allowed_max == null ? '?' : d.allowed_max) + ' 字）'}; }\n    if(d && d.kind === 'bad_value'){ return {ok:false, why:'值非法（kind ＝ ' + kind + ' · 后端仅受 ' + JSON.stringify(d.allowed || []) + '）'}; }\n    return {ok:false, why:'不可达（HTTP ' + r.status + (d ? '' : ' · ⛔ 未取得回执体') + '）'};\n  }catch(e){\n    return {ok:false, why:'不可达（请求未送达：' + String((e && e.message) || e) + '）· ⛔ 不等于已入队'};\n  }\n}\nasync function paIntervene(kind){\n  const sid = curSession();\n  const out = document.getElementById('paSubOut');\n  /* 接管 ＝ 待立项（须先定义）⇒ 钮 disabled（⛔ 静默 · 其由在 title · 承 PM 1254 §三） */\n  if(kind === '接管'){ if(out) out.textContent = '接管：无此端点（后端无「接管」之概念）⇒ 待立项（须先定义）· ⛔ 未发送'; return; }\n  if(kind === '改令'){\n    if(!out) return;\n    const text = String((window.prompt('改令 · 下一步指导（≤500 字 · POST /v9/pa/steer）') || '')).trim();\n    if(!text){ out.textContent = '改令：内容为空 ⇒ ⛔ 未发送（⛔ 开空件）'; return; }\n    out.textContent = '改令：提交中…（POST /v9/pa/steer）';\n    const res = await paSteerPost(sid, text, '改令');\n    if(!res.ok){ out.textContent = '改令：' + res.why; return; }\n    out.textContent = '改令：已入队 · 下一轮生效（通道 consumer ＝ 每轮 drain 即清 · ' + String(res.d.inject_point || '?') + '）'\n      + '｜后端 ' + String(res.d.at || '?') + ' · 印 ' + String(res.d['印'] || '?');\n    return;\n  }\n  try{\n    const r = await fetch(API + '/v9/cancel/' + encodeURIComponent(sid), {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'});\n    const d = await r.json().catch(function(){ return null; });\n    if(out) out.textContent = '中止：' + (d && d.success ? ('已置取消标志（' + (d.session_id || sid) + '）· 下一步边界生效')\n      : ('后端未确认（HTTP ' + r.status + '）· 如实记'));\n  }catch(e){\n    if(out) out.textContent = '中止：请求未送达（' + String((e && e.message) || e) + '）· ⛔ 不等于已中止';\n  }\n}"),
        ("sub",
         "    return {ok:false, why:'不可达（HTTP ' + r.status + (d ? '' : ' · ⛔ 未取得回执体') + '）'};",
         "    if(r.ok){ return {ok:false, why: PA_GAP.down('HTTP ' + r.status + ' · 回执无 ok ⇒ 信封不合（承 PM 1253 §二）')}; }\n    return {ok:false, why: PA_GAP.down('HTTP ' + r.status + (d ? '' : ' · ⛔ 未取得回执体'))};"),
        ("sub",
         "    return {ok:false, why:'不可达（请求未送达：' + String((e && e.message) || e) + '）· ⛔ 不等于已入队'};",
         "    return {ok:false, why: PA_GAP.down('请求未送达：' + String((e && e.message) || e) + ' · ⛔ 不等于已入队')};"),
        ("sub",
         "  paAttachRowTitle(stEl, '受理', PA_GAP.todo('无读源') + ' —— 本页已接 ' + paLocalTasks.length + ' 件（本页口径）',",
         "  paAttachRowTitle(stEl, '受理', PA_GAP.todo() + ' · 本页已接 ' + paLocalTasks.length + ' 件',"),
        ("sub",
         "    '源：' + PA_GAP.todo('无读源') + ' —— POST /v9/pa/dialog ／ POST /v9/agent/chat 为写路（⛔ 读源）⇒ 后端无「受理态」读面｜本页计数 ＝ 本页已接（⛔ 后端口径 · ⛔ 以 0 充未接）');",
         "    '源：' + PA_GAP.todo('后端无「受理态」读面 —— POST /v9/pa/dialog ／ POST /v9/agent/chat 为写路（⛔ 读源）') + '｜本页计数 ＝ 本页已接（本页口径 · ⛔ 后端口径 · ⛔ 以 0 充未接）');"),
    ]),
    (u'web/pa/faces/sources.js · 己-1..2', 'web/pa/faces/sources.js', [
        ("sub",
         "   note:'⚠ 逐面件数取真源（/v9/pa/ask 之 scope ／ faces ／ searched）：收件箱 ／ 知识库 ／ 文件 ／ 台账 ／ 台账·信通（后三面本批新接）；未接：平台 ／ 出图 ／ 记忆（M1 · 明标未接）⇒ ⛔ 装成可用；未命中 ⇒ 回落模型'},",
         "   note:'⚠ 逐面件数取真源（/v9/pa/ask 之 scope ／ faces ／ searched）：收件箱 ／ 知识库 ／ 文件 ／ 台账 ／ 台账·信通；⭐ 本批新接：出图（检索面名 ＝ 文件·产出）／ 记忆（检索面名 ＝ 梦中月水中花）；⛔ 不接：平台（红线 · ⛔ 代操作他方平台）⇒ ⛔ 装成可用；未命中 ⇒ 回落模型'},"),
        ("sub",
         "   note:'⚠ 已通：精确计算（POST /api/tools/calc ⇒ 算术以工具值为准）；未接：技能面（13 技能 · 已转产品线）⇒ ⛔ 装成可用'}",
         "   note:'⚠ 已通：精确计算（POST /api/tools/calc ⇒ 算术以工具值为准）；' + PA_GAP.off('', '已转产品线') + '：技能面（13 技能）⇒ ⛔ 装成可用'}"),
    ]),
    (u'web/pa/faces/selfdesc.js · 丙-7', 'web/pa/faces/selfdesc.js', [
        ("sub",
         "    U.push('· 操作：改令 ／ 接管（无接口 ⇒ 置灰）｜真实平台面｜夜间整合');",
         "    U.push('· 操作：改令（准接 · POST /v9/pa/steer）｜接管（待立项 · 须先定义）｜真实平台面（⛔ 不接 · 红线）｜夜间整合（无后端面）');"),
    ]),
]
EDITS = {"批四": 批四}
ORDER = ["批四"]
BASES = [
    ("批四", 0, 'web/pa/core.js', '2504ad307af24615', 'e761e9205e3868f7'),
    ("批四", 1, 'web/pa/faces/tasks.js', '53c72c537ef7612d', '9d8af7b22e11b6e8'),
    ("批四", 2, 'web/pa/faces/sources.js', '8089eac70480f613', '6e4b67852390b4c3'),
    ("批四", 3, 'web/pa/faces/selfdesc.js', 'febf7f6145bb802e', '073f1b0f05171914'),
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
    sys.exit(S.cli(EDITS, ORDER, bases=BASES, title=u"接线批四 · 丙／己／庚（四件 · 十处 ＋ 沿改二处）"))
