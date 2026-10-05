/* ClawsJoy PA v3 · 主面 ③ 任务（含派活栏）（CW b2a5182 · 承 pm_996 §三 ／ pm_997 §二 ／ pm_984 行为闸 · 2026-10-04）
   口径（L76）：每一状态旁须带**真源**；后端无此读数 ⇒ 显「未知 ／ 未接」，⛔ 合成状态 ／ ⛔ 以「忙」代状态 ／ ⛔ 藏失败态。
   真源（皆 GET · 只读）：/v9/pes/runs（run 投影）／ /v9/audit/approvals（待你裁）／ /v9/metrics/tool_flow（任务台账）
        ／ /v9/subtask/status（子任务池）／ /v9/pa/local_client/status（对端）／ /v9/pa/permission（凭据档）。
   行为闸（pm_984 §二）：受理门永不关（⛔ 置灰输入 ／ ⛔ 拒件）· 可打断 · 可闲聊 · 生效时点照实写。
   ⚠ 本面 2 栏：左「任务五态 ＋ 台账 ＋ 干预」／右「派活（席位 ／ 对端 ／ 在办 ／ 待验收 ／ 凭据）」—— 同件事之两面。 */

/* ===== 行为闸 · 先落：⛔ 置灰输入（承 pm_984 §二.1）=====
   status.js 之 setBusy(on) 会 `sendBtn.disabled = on` ⇒ 在办时输入被「关」⇒ 即拒件。
   本页（⭐ 承 pm 1203 §一：今唯 pa.html 一壳 ⇒ 旧「唯 v3 载入 ／ 旧 pa.html ⛔ 受影响」之界已反 —— 本件之改及于唯一壳）以**同签名**覆盖：保留停止键与探针，⛔ 不动发送键。
   ⚠ 刻意**不调**原 setBusy —— 调了就又置灰了。 */
(function(){
  window.setBusy = function(on){
    const btn = document.getElementById('sendBtn'), stop = document.getElementById('stopBtn'), dot = document.getElementById('connDot');
    if(stop) stop.style.display = on ? 'inline-block' : 'none';
    if(btn) btn.disabled = false;                      /* 受理门永不关 */
    if(dot && on) dot.textContent = '● 处理中…';
    if(!on && typeof probeConn === 'function'){ try{ probeConn(); }catch(e){} }
  };
})();

/* ⭐ pm_1046 §二.2（承 L85）：**首帧即改** —— ⛔ 让老板先见裸「—」再跳人话。
   静态占位在 pa.html:18（内容件 · ⛔ 本席动）⇒ 由本件（可动之 v3 面件中**最先载入**者 · 脚本序 19）于**解析期**执行。
   权威仍是 selfdesc.js 之 paSelfSrcPass（单源 · 承 L83）⇒ 若已在 ⇒ 直调之；未在 ⇒ 落同一人话字面量（照实报 · ⛔ 第二判据）。 */
(function(){
  function p0(){
    const el = document.getElementById('runStateSrc'); if(!el) return;
    if(typeof window.paSelfSrcPass === 'function'){ try{ window.paSelfSrcPass(); return; }catch(e){} }
    if(/^状态来源：\s*—\s*$/.test(String(el.textContent || ''))) el.textContent = '状态来源：本次未发请求';
  }
  p0();
  if(document.readyState === 'loading'){ document.addEventListener('DOMContentLoaded', p0); }
  try{ requestAnimationFrame(p0); }catch(e){}
})();

/* ===== 本页任务台账（受理即落一行 · 状态由后端事件改写 ⇒ ⛔ 前端猜）===== */
let paLocalTasks = [];
let paTaskSeq = 0;
const PA_TASK_五态 = {running:'在办', model:'在办', tool:'在办', verifying:'在办',
  approval:'待你裁', done:'已完成', failed:'失败', stopped:'已中止', blocked:'失败', idle:'受理'};
function paTaskAccept(text){
  let mode = 'chat';
  try{ if(typeof state !== 'undefined' && state && state.mode) mode = state.mode; }catch(e){}
  paTaskSeq += 1;
  paLocalTasks.unshift({
    id: 'PA-' + paTaskSeq,
    ts: new Date().toLocaleTimeString('zh-CN', {hour12:false}),
    text: String(text || '').slice(0, 40),
    state: '在办',
    note: '已接件 · 提交中',
    src: (mode === 'chat') ? 'POST /v9/pa/dialog' : 'POST /v9/agent/chat'
  });
  if(paLocalTasks.length > 20) paLocalTasks.pop();
  if(paV3Face === 'tasks') paRenderLocalTasks();
}
(function(){
  const origSend = window.paSend;
  if(typeof origSend === 'function'){
    window.paSend = function(){
      try{ paTaskAccept(document.getElementById('input') ? document.getElementById('input').value : ''); }catch(e){}
      return origSend.apply(this, arguments);
    };
  }
  const origState = window.paSetState;
  if(typeof origState === 'function'){
    window.paSetState = function(k, note, src){
      const r = origState.apply(this, arguments);
      try{
        const cur = paLocalTasks[0];
        if(cur){
          cur.state = PA_TASK_五态[k] || '未知';
          if(note) cur.note = String(note).slice(0, 50);
          if(src) cur.src = String(src);
          if(paV3Face === 'tasks') paRenderLocalTasks();
        }
      }catch(e){}
      return r;
    };
  }
})();

/* ===== 任务面读数 ===== */
function paRow(k, v, s, na){
  return '<div class="r"><span class="st">' + k + '</span><span class="v' + (na ? ' na' : '') + '">'
    + v + '</span><span class="s">' + (s || '') + '</span></div>';
}
function paEsc(s){ return String(s == null ? '' : s).replace(/[&<>"]/g, function(c){
  return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]; }); }
/* ⭐ pm_刀9 §二 ／ 刀11p §二.2：**刻须可读** —— 后端所给之刻（epoch 秒）⇒ 本地时分之逐字。
   ⛔ 前端自算「当前刻」顶「件之刻」（承 L76「刻须随值」· pm_刀11p §零）。 */
function paTsLocal(v){
  function z(n){ n = String(n); return n.length >= 2 ? n : ('0' + n); }
  try{
    if(v == null) return null;
    const n = (typeof v === 'number') ? v : parseFloat(v);
    if(!isFinite(n)) return null;
    const d = new Date(n * 1000);
    if(isNaN(d.getTime())) return null;
    return d.getFullYear() + '-' + z(d.getMonth() + 1) + '-' + z(d.getDate()) + ' '
      + z(d.getHours()) + ':' + z(d.getMinutes()) + ':' + z(d.getSeconds());
  }catch(e){ return null; }
}

/* ⭐ pm_1061 §二：以 `title` 补「屏上被截之槽」（零 CSS ／ 零控件 ／ **⛔ 硬改 `paRow` 之形**）。
   ⚠ 一手：`paRow`（本件 `:83–86`）唯三槽（`.st` ／ `.v` ／ `.s`）⇒ ⛔ 支持属性（⛔ 第四参）；
   而 `.tstates .r .v` ／ `.r .s` 皆 `nowrap ＋ overflow:hidden ＋ ellipsis`（`pa_v3.css:59–60`）⇒ 屏上被截。
   ⇒ 故于**渲染后**按「行名」（`.st` 之文）定位 ⇒ 只对既有二槽赋 `title`（⛔ 动文 ／ ⛔ 加元素 ／ ⛔ 触 CSS）。 */
function paAttachRowTitle(host, key, valTitle, srcTitle){
  if(!host) return 0;
  var n = 0, rows = host.querySelectorAll('.r');
  for(var i = 0; i < rows.length; i++){
    var st = rows[i].querySelector('.st');
    if(!st || String(st.textContent) !== key) continue;
    var v = rows[i].querySelector('.v');
    if(v && valTitle){ v.setAttribute('title', valTitle); n++; }
    var s = rows[i].querySelector('.s');
    if(s && srcTitle){ s.setAttribute('title', srcTitle); n++; }
  }
  return n;
}
/* ⭐ pm_1060 §三：失败之因上屏（承 L76 刻须随值 ／ L103 形与义分 ／ ⛔ 丢 ／ ⛔ 编）。
   真源 ＝ 后端子任务条目之 error 字段（一手核 core/gateway/subtask_executor.py：:110 落盘 ／ :224 与 :236 写因；
   API 由 :149 list_subtasks 原样返回条目）。⛔ 前端自造键（承 L102）。
   判据：status === 'failed' ∧ error 非空 ⇒ ⭐ 因（屏上 ＝ 截断之单行 ＋ 全文入 title（悬停可回）
        ＋ <details class="eng"> 折叠（展开可见 · 可复制 · ⛔ 静默丢））；
        status === 'failed' ∧ 无 error ⇒ 照实「（后端未给因）」（⛔ 编）。
   ⚠ 读回态（重启后 hydrate · 同件 :59–72）：条目内 ⛔ 无 task_id（真键 ＝ 同一 map 之键 · 后端未并入条目）
       ⇒ 本处照实落 '?'（⛔ 前端编）。
   ⚠ 同判据之第二落点（paSubtaskPop 之独立窗）⛔ 引本函数（另文档 · 另一 global）⇒ 内联重写（形同 · 值同 · 截断同 80）。
   ⭐ pm_1062 §三：扩至新态 ⭐ `pending`（待审）⇒ 同上族显因（标签「待审因」 · ⛔ 以「失败」称非失败之项 · 承 L103）。
   ⭐ pm_1063 §三：第二落点之**键名**对齐 —— 窗内原读 `task_spec`（⛔ 真键）⇒ 改 `spec` ＋ 「（无 spec）」＋ 40 字 ／ `title` 全文 ⇒ 与池逐条 **逐字同**。 */
var PA_SUB_ERR_SHOW = 80;
function paSubErrFold(id, raw, lbl){
  lbl = lbl || '失败因';
  return '<details class="eng" data-subtask="' + paEsc(id) + '">'
    + '<summary title="' + lbl + '原文（后端 error 字段 · 逐字 · ⛔ 截断）">' + lbl + '原文（全 ' + raw.length + ' 字 · 收起 · 展开可见）</summary>'
    + '<div class="engbody">' + paEsc(raw) + '</div></details>';
}
var PA_SUB_SPEC_SHOW = 40;
/* ⭐ pm_1061 §三：`spec` 之**真键**（一手核 `core/gateway/subtask_executor.py:133` 逐字 `"spec"` ⇒ 原引之 `task_spec` **⛔ 在后端条目**）。
   有 ⇒ 屏上 40 字（单行 · 折平空白）＋ 全文入 `title`（⛔ 加第 2 折叠 —— 撑 · 且 `spec` 后端已截 `200` ⇒ `title` 足可回）；
   ⛔ 无（`null` ／ `undefined` ／ 空 ／ 纯空白）⇒ 照实「（无 spec）」（⛔ 编 · 承 `L76`）。 */
function paSubSpecPart(s){
  var sp = (s && s.spec != null) ? String(s.spec).trim() : '';
  if(!sp) return ' · spec：（无 spec）';
  var flat = sp.replace(/\s+/g, ' ');
  return ' · <span title="spec 原文（后端 spec 字段 · 逐字 · ⛔ 截断）：' + paEsc(sp) + '">spec：'
    + paEsc(flat.slice(0, PA_SUB_SPEC_SHOW)) + (flat.length > PA_SUB_SPEC_SHOW ? '…' : '') + '</span>';
}
/* ⭐ pm_1062 §三：后端新终态 `pending`（待审 · ⛔ 假 failed）⇒ 池逐条须人话「待审」（⛔ 原样英文 ╱ ⛔ 当 failed）。
   真源 ＝ 后端 status 字段（一手：池含 sub_…_2 · pending）；⛔ 前端自造键（承 L102）丨⛔ 改他态之形（三）。 */
var PA_SUB_ST_CN = {pending:'待审'};
function paSubStatusCn(st){ return st ? (PA_SUB_ST_CN[st] || st) : '未知'; }
function paSubRowHtml(s){
  var id = (s && (s.task_id || s.id)) || '?';
  var stt = (s && s.status) || '';
  var html = '<div>' + paEsc(id) + ' · ' + paEsc(paSubStatusCn(stt))
    + paSubSpecPart(s);
  if(stt === 'failed' || stt === 'pending'){
    var lbl = (stt === 'pending') ? '待审因' : '失败因';
    var err = (s.error == null ? '' : String(s.error)).trim();
    if(err){
      var flat = err.replace(/\s+/g, ' ');
      html += ' · <span title="' + lbl + '（原文 · 屏上截断）：' + paEsc(err) + '">' + lbl + '：'
        + paEsc(flat.slice(0, PA_SUB_ERR_SHOW)) + (flat.length > PA_SUB_ERR_SHOW ? '…' : '') + '</span>'
        + paSubErrFold(id, err, lbl);
    }else{
      html += ' · ' + lbl + '：（后端未给因）';
    }
  }
  return html + '</div>';
}


/* ⭐ pm_1046 §二.3：任务台账之「测试痕」—— 名形判据**外置可配**（真源 ＝ pa/测试痕_清单.json 之「任务台账_测试名」）。
   ⛔ 前端硬编白名单（承 L83 单源 ／ L102 声明面≠执行面）：清单未取到 ／ 无该键 ／ 名形不命中 ⇒ **一条也不收**
   （fail-open 于真账 —— 承 pm_1045 §三 之界：真问永不被收起）。
   收取形 ＝ <details> 折叠（默认收起 · 展开可见 ⇒ ⛔ 静默丢）；summary 携判据与清单名（可回指）。 */
let paTtManifestCache = null, paTtManifestTried = false;
async function paTtManifestGet(){
  if(paTtManifestTried) return paTtManifestCache;
  paTtManifestTried = true;
  try{
    const r = await fetch('pa/测试痕_清单.json', {cache:'no-store'});
    paTtManifestCache = r.ok ? await r.json() : null;
  }catch(e){ paTtManifestCache = null; }
  return paTtManifestCache;
}
function paTtLedgerRule(mf){
  const o = mf && mf['任务台账_测试名'];
  const ps = (o && Array.isArray(o.patterns)) ? o.patterns : null;
  return (ps && ps.length) ? o : null;
}
function paTtIsTestName(name, rule){
  if(!rule) return false;
  const ps = rule.patterns;
  for(let i = 0; i < ps.length; i++){
    try{ if(new RegExp(ps[i]).test(String(name))) return true; }catch(e){}
  }
  return false;
}

/* —— 派活 · 护（承 `pm_1050 §二`）：按「派活」会真起执行循环（后端真跑工具 ／ 写沙箱）且本卡无「停止」钮
   ⇒ 用户面前置明标「未验（M1）」（⛔ 装成可用 · 承 `L102`）＋「⛔ 重复按」之戒。
   ⚠ 照实（我一手 · 见 `投递 1050 §三`）：`pm_1050` 之「看板看不见它 ⇒ 恒空」**不成立** ——
      `list_subtasks(user_id, session_id)` 按**两键**取（`routes\session.py:115`）；页内以本页之
      `user_id ＋ session_id` 取 ⇒ **看得见**（实测 `1 件 · sub_1791108488930_1 · failed`）；
      空读系**键不匹配**（缺参 ⇒ `default`）⇒ 故本标**⛔ 写**「恒空」，只写**成立**之事。
   ⛔ 遮挡既有「源」行（两者并存）；⛔ 撑首屏（唯本卡内两行）；⛔ 动共用件 ／ 后端文案。 */
function paEnsureSubGuard(){
  const has = document.getElementById('paSubUnverified');
  if(has) return has;
  const sub = document.querySelector('#paFaceTasks .subform');
  if(!sub || !sub.parentNode) return null;
  const w = document.createElement('div');
  w.id = 'paSubUnverified';
  w.setAttribute('data-verified', 'false');
  w.style.cssText = 'margin:2px 0 6px;padding:4px 8px;border-radius:6px;font-size:10.5px;line-height:1.7;'
    + 'color:var(--amber);background:rgba(210,153,29,.10);border:1px solid rgba(210,153,29,.45)';
  w.innerHTML = '⚠ 未验（M1）：按「派活」会真起执行循环（后端真跑工具 ／ 写沙箱 · 本卡无「停止 ／ 撤回」钮）⇒ ⛔ 重复按。'
    + '<br>本池读数按 <code>user_id</code> ＋ <code>session_id</code> 取（服务进程内存）⇒ 重启后可能空 · ⛔「池空」≠「未跑」。';
  sub.parentNode.insertBefore(w, sub);
  return w;
}

/* ===== 环境面 · agents 栏（武装四件 · 承 pm_刀7p ／ 刀3′）=====
   源（唯后端 · 只读）：GET /v9/pa/roster（count ／ by_level）＋ GET /v9/pa/roster?full=1（cards 逐卡字段）。
   五列（level ／ caps ／ invoke ／ cost ／ probe）**逐项全取后端**；⛔ 前端自造 ／ ⛔ 补齐。
   空 ／ 缺分显（承 pm_076 §一）：键不在 ∨ 空串 ⇒「缺」；键在且为 [] ⇒「空（后端 []）」。⛔ 以「空」代「缺」。
   ⛔ 密钥：本读 ⛔ 显任何密钥之值 ／ 长度 ／ 尾号 —— roster 片**无此键** ⇒ 标**回退支**（真源 ＝ GET /v9/pa/env 之 `secret_guard`），⛔ 编「有」。
   判据（承 刀7p §二「counts 与 cols 对不上 ⇒ 显红」）：
     ⒜ ro.count（声明）⟷ roF.cards.length（实） ／ ⒝ by_level 之归集 ⟷ 逐卡 access.level（两集须 ≡ · 承 pm_086）。
     ⛔ 前端补齐：不齐 ⇒ 显红 ＋ 明书差数。
   ⛔ 未在册者不显：本栏逐行源 ＝ 后端 cards ⇒ 后端无 ⇒ 自不显（⛔ 前端补行）。
   每项「点回真源」：`src` 逐字上屏 ＋ 点开**内联**取该卡之后端原文（同源 ／ 只读 ／ ⛔ 改 ／ ⛔ popup）。 */
function paEnvCell(v){
  if(v === null || v === undefined) return {t:'缺（后端无此键）', na:true};
  var s = String(v).trim();
  if(!s) return {t:'缺（后端空串）', na:true};
  return {t:s, na:false};
}
function paEnvList(a){
  if(a === null || a === undefined) return {t:'缺（后端无此键）', na:true};
  if(!Array.isArray(a)) return {t:'缺（形非表）', na:true};
  if(!a.length) return {t:'空（后端 []）', na:true};
  return {t:a.join('；'), na:false};
}
function paEnvAgentsRows(host, ro, roF){
  if(!host) return 0;
  var cards = (roF && Array.isArray(roF.cards)) ? roF.cards : null;
  var declared = (ro && ro.count != null) ? ro.count : null;
  var bl = (ro && ro.by_level) ? ro.by_level : null;
  var nCards = cards ? cards.length : null;
  var badA = (declared === null || nCards === null || declared !== nCards);
  var setA = [], setB = [];
  if(bl && cards){
    Object.keys(bl).forEach(function(L){
      var ids = Array.isArray(bl[L]) ? bl[L] : [];
      ids.forEach(function(id){ setA.push(String(id) + '@' + String(L)); });
    });
    cards.forEach(function(c){
      var L = (c && c.access && c.access.level != null) ? String(c.access.level) : '（无）';
      setB.push(String((c && c.id) || '?') + '@' + L);
    });
    setA.sort(); setB.sort();
  }
  var badB = (setA.length !== setB.length) || (setA.join('|') !== setB.join('|'));
  var red = badA || badB;
  var verdict = '判 ⒜ 声明 ' + (declared === null ? '缺' : declared) + ' ⟷ 实 ' + (nCards === null ? '缺' : nCards)
    + (badA ? ' ✗' : ' ✓') + ' ／ ⒝ by_level 归集 ' + setA.length + ' ⟷ 逐卡 level ' + setB.length + (badB ? ' ✗' : ' ✓');
  if(!cards){
    host.insertAdjacentHTML('beforeend',
      '<div class="ch" style="margin-top:8px">环境面 · agents（武装四件）<span class="src">源：GET /v9/pa/roster?full=1</span></div>'
      + paRow('agents', '未知（后端未应答 ／ ⛔ 前端补齐）', '源：GET /v9/pa/roster?full=1'));
    return 0;
  }
  var colDefs = [
    ['level',  function(c){ return (c && c.access && c.access.level != null) ? String(c.access.level) : null; }],
    ['caps',   function(c){ return (c && Array.isArray(c.capabilities) && c.capabilities.length) ? c.capabilities.join('；') : null; }],
    ['invoke', function(c){ return (c && c.access && c.access.channel) ? String(c.access.channel) : null; }],
    ['cost',   function(c){ return (c && c.cost != null && String(c.cost).trim()) ? String(c.cost) : null; }],
    ['probe',  function(c){
        var v = (c && Array.isArray(c.verified)) ? c.verified : null;
        if(!v) return null;
        var ps = v.filter(function(x){ return /^\s*probe:/.test(String(x)); });
        return ps.length ? ps.join('；') : null;
      }]
  ];
  var have = colDefs.map(function(d){ return cards.filter(function(c){ return d[1](c) != null; }).length; });
  var reading = 'agents ' + cards.length + ' 件 · 五列齐：' + colDefs.map(function(d, i){ return d[0] + ' ' + have[i] + '／' + cards.length; }).join(' · ');
  var html = '<div class="ch" style="margin-top:8px">环境面 · agents（武装四件）'
    + '<span class="src">源：GET /v9/pa/roster ＋ ?full=1 · ⛔ 密钥唯「有／无」（本片无此键 ⇒ ' + PA_GAP.fallback('secret_guard') + '｜密钥有无之真源 ＝ GET /v9/pa/env 之 secret_guard）</span></div>'
    + '<div class="envjudge" data-axis="env-agents" data-red="' + (red ? '1' : '0') + '" data-declared="' + (declared === null ? '' : declared)
    + '" data-cols="' + cards.length + '" style="font-size:10.5px;line-height:1.7;color:' + (red ? '#f85149' : 'var(--sub)') + '">'
    + paEsc(reading) + '<br>' + paEsc(verdict)
    + (red ? ' ⚠ 显红：声明与实不齐 ⇒ ⛔ 前端补齐（承 刀7p §二）' : '') + '</div>';
  cards.forEach(function(c){
    var id = String((c && c.id) || '?');
    var lvl = (c && c.access && c.access.level != null) ? String(c.access.level) : '缺';
    var src = (c && c.source != null && String(c.source).trim()) ? String(c.source) : '缺（后端无 source）';
    var cap = paEnvList(c && c.capabilities);
    var inv = paEnvCell(c && c.access ? c.access.channel : null);
    var cost = paEnvCell(c && c.cost);
    var all = (c && Array.isArray(c.verified)) ? c.verified : null;
    var probes = all ? all.filter(function(x){ return /^\s*probe:/.test(String(x)); }) : null;
    var others = all ? all.filter(function(x){ return !/^\s*probe:/.test(String(x)); }) : null;
    var probeCell = (probes === null) ? '缺（后端无 verified）' : (probes.length ? probes.join('；') : '空（后端无 probe: 条）');
    html += '<details class="eng" data-agent="' + paEsc(id) + '">'
      + '<summary>' + paEsc(lvl + ' · ' + id + ' · ' + String((c && c.kind) || '缺') + ' · ' + src) + '</summary>'
      + '<div class="engbody">'
      + paRow('caps', paEsc(cap.t), '源：GET /v9/pa/roster?full=1#' + paEsc(id) + ' · 字段 capabilities', cap.na)
      + paRow('invoke', paEsc(inv.t), '源：GET /v9/pa/roster?full=1#' + paEsc(id) + ' · 字段 access.channel', inv.na)
      + paRow('cost', paEsc(cost.t), '源：GET /v9/pa/roster?full=1#' + paEsc(id) + ' · 字段 cost', cost.na)
      + paRow('probe', paEsc(probeCell), '源：GET /v9/pa/roster?full=1#' + paEsc(id) + ' · 字段 verified（probe: 条）· ⚠ 后端无逐次探活之「刻」⇒ 刻缺', (probes === null || !probes.length))
      + paRow('src', '<a href="javascript:void(0)" onclick="paEnvSrc(this,\'' + paEsc(id) + '\')" style="color:var(--blue)">' + paEsc(src) + ' ⧉</a>', '点开：内联取该卡之后端原文（只读 ／ 同源）')
      + ((others && others.length) ? paRow('验（非探活）', paEsc(others.join('；')), '源：GET /v9/pa/roster?full=1#' + paEsc(id) + ' · 字段 verified（非 probe: 条）') : '')
      + '</div></details>';
  });
  host.insertAdjacentHTML('beforeend', html);
  return cards.length;
}
/* 「点回真源」：内联揭示该卡之后端原文（⛔ popup ⇒ ⛔ popup 拦截之静默；再点即收）。 */
async function paEnvSrc(a, id){
  var body = (a && a.closest) ? a.closest('.engbody') : null;
  if(!body) return;
  var old = body.querySelector('.envraw');
  if(old){ var wasOpen = !old.hidden; if(old.parentNode) old.parentNode.removeChild(old); if(wasOpen) return; }
  var box = document.createElement('div');
  box.className = 'envraw';
  box.setAttribute('data-axis', 'env-agents-src');
  box.style.cssText = 'margin-top:4px;font-size:10px;color:var(--sub);white-space:pre-wrap;word-break:break-word;'
    + 'max-height:220px;overflow:auto;border-top:1px dashed var(--border);padding-top:3px';
  box.textContent = '取后端原文中…（GET /v9/pa/roster?full=1）';
  body.appendChild(box);
  var j = await paGetJson(API + '/v9/pa/roster?full=1');
  var card = (j && Array.isArray(j.cards)) ? j.cards.filter(function(c){ return String(c && c.id) === String(id); })[0] : null;
  var t = new Date().toLocaleTimeString('zh-CN', {hour12:false});
  box.textContent = '径：GET /v9/pa/roster?full=1 · 卡 id=' + id + ' · 取刻 ' + t + ' · 只读 · ⛔ 密钥唯「有／无」\n'
    + (card ? JSON.stringify(card, null, 2) : '（后端无此卡 · 如实记）');
}

async function paLoadTasks(){
  paEnsureSubGuard();
  const u = encodeURIComponent(curUser()), sid = encodeURIComponent(curSession());
  const runs = await paGetJson(API + '/v9/pes/runs?user_id=' + u);
  const appr = await paGetJson(API + '/v9/audit/approvals?user_id=' + u + '&session_id=' + sid);
  const mf   = await paGetJson(API + '/v9/metrics/tool_flow');
  const st   = await paGetJson(API + '/v9/subtask/status?user_id=' + u + '&session_id=' + sid);
  const lc   = await paGetJson(API + '/v9/pa/local_client/status?user_id=' + u);
  const pm   = await paGetJson(API + '/v9/pa/permission');
  /* ⭐ pm_1024 §二：**先查真源 · 有则接** —— 编队花名册（派活面席位）／派发历史（等待外部结果） */
  const ro   = await paGetJson(API + '/v9/pa/roster?user_id=' + u);
  const dh   = await paGetJson(API + '/v9/pa/dispatch/history?user_id=' + u);
  const roF  = await paGetJson(API + '/v9/pa/roster?full=1');
  const nSub0 = (st && Array.isArray(st.subtasks)) ? st.subtasks.length : null;

  /* —— 左栏 · 五态 ＋ 状态来源 —— */
  const nR = (runs && Array.isArray(runs.runs)) ? runs.runs.length : null;
  const nA = (appr && Array.isArray(appr.approvals)) ? appr.approvals.length : null;
  const stEl = document.getElementById('paTaskStates');
  const runLabel = (document.getElementById('runState') || {}).textContent || '未知';
  /* ⭐ pm_1046 §二.1（承 L103 形与义分）：⛔ 取 DOM 静态占位（初值「状态来源：—」⇒ 会漏出裸「—」）。
     此处无源态之义 ＝ **后端事件未到**（⛔ 顶栏之「本次未发请求」—— 形同而义不同）⇒ 用本处人话「后端事件：尚未到达」。
     有源 ⇒ 照抄真源（真源 ＝ #runStateSrc · 由 paRenderState ／ paSelfSrcPass 写 · ⛔ 本件自判）。 */
  const runSrcRaw = String(((document.getElementById('runStateSrc') || {}).textContent) || '');
  const runSrcVal = runSrcRaw.replace(/^状态来源：/, '').trim();
  const runSrcNo  = (!runSrcVal || runSrcVal.charAt(0) === '—'
                     || runSrcVal.indexOf('尚未收到后端事件') >= 0 || runSrcVal.indexOf('无请求源') >= 0
                     || runSrcVal === '本次未发请求');
  /* ⭐ pm_1051 §四：五态「在办」之值须与源同类（⛔ 一行两值相左）。
     本行值原＝本页运行态（#runState · 「○ 就绪」）；而同刻源行指向后端子任务池（可真 1 件）
     ⇒ 同屏打架（值「就绪」⟷源「1 件」）。改：**明标二义分列**（本页任务态 ｜ 后端子任务池 · 件数 ＋ 失败数照实）
     ⇒ ⛔ 改「源」行（并存）。⚠ 照实：⛔ 把本页运行态当成池之态，亦 ⛔ 把池之态顶替本页态。 */
  const nSubFail = (st && Array.isArray(st.subtasks))
    ? st.subtasks.filter(function(x){ return x && x.status === 'failed'; }).length : null;
  const inFlightPlain = '本页任务态：' + runLabel + ' ｜ 后端子任务池：'
    + (nSub0 === null ? '未知（后端未应答）'
       : (nSub0 + ' 件' + (nSub0 > 0 ? ('（失败 ' + (nSubFail === null ? '未知' : nSubFail) + '）') : '')));
  const inFlightVal = paEsc(inFlightPlain);
  /* ⭐ pm_1061 §二：值槽 ／ 源槽屏上皆被截（`nowrap ＋ ellipsis`）⇒ 备 `title`（⛔ 截 · 悬停可回）。
     ⭐ 值槽之 `title` ＝ 本行值之**全文** ＋（池内有失败条 ⇒ 逐条「task_id · 因：<全文>」）⇒ 在办行亦「携因」。 */
  const srcPlain = runSrcNo
    ? ('源：后端事件：尚未到达 ＋ GET /v9/subtask/status（子任务 ' + (nSub0 === null ? '未知' : nSub0 + ' 件') + '）')
    : ('源：' + runSrcVal + '（后端事件）＋ GET /v9/subtask/status（子任务 ' + (nSub0 === null ? '未知' : nSub0 + ' 件') + '）');
  const subFailNotes = (st && Array.isArray(st.subtasks)) ? st.subtasks.filter(function(x){
      return x && x.status === 'failed';
    }).map(function(x){
      const e = (x.error == null ? '' : String(x.error)).trim();
      return (x.task_id || x.id || '?') + ' · 因：' + (e || '（后端未给因）');
    }) : [];
  const inFlightTitle = inFlightPlain
    + (subFailNotes.length ? ('\n（池内失败条之因 · 全文）\n' + subFailNotes.join('\n')) : '');
  /* ⭐ pm_刀9 §〇 ＋ 刀11p §二：**态数须真态** —— ⛔ 以 `dispatch/history` 之**表长**充「等待外部结果」。
     真判据（后端 counts ／ 判据）：`to_seat 非空 ∧ stage ≠ 已收口`（后端 awaiting_receipt 即此）。
     ⚠ 后端旧版（未重启）⇒ 不发 counts ⇒ 面内按**同谓词**自 rows 派生，并**明标「面内派生」**（⛔ 手搓 · ⛔ 表长充态）。 */
  const dhCnt  = (dh && dh.counts) ? dh.counts : null;
  const dhRows = (dh && Array.isArray(dh.rows)) ? dh.rows : null;
  const dhTblN = (dh && dh.count != null) ? dh.count : null;
  const dhSeatN = (dhCnt && dhCnt.seat_axis != null) ? dhCnt.seat_axis
    : (dhRows ? dhRows.filter(function(x){ return String((x || {}).to_seat || '').trim() !== ''; }).length : null);
  const dhWaitN = (dhCnt && dhCnt.awaiting_receipt != null) ? dhCnt.awaiting_receipt
    : (dhRows ? dhRows.filter(function(x){
        return String((x || {}).to_seat || '').trim() !== '' && String((x || {}).stage || '') !== '已收口';
      }).length : null);
  const dhPoolN = dhRows ? dhRows.filter(function(x){ return String((x || {}).source || '') === 'subtask_pool'; }).length : null;
  const dhFilter = '滤：to_seat 非空 ∧ stage ≠ 已收口'
    + (dhCnt ? '（后端 counts.awaiting_receipt）' : ' ⇒ ⚠ 后端未发 counts ⇒ 面内按同谓词自 rows 派生（⛔ 手搓）');
  const dhSrcLine = '源：GET /v9/pa/dispatch/history（store_exists=' + (dh ? String(dh.store_exists) : '未知')
    + ' · 表长 ' + (dhTblN === null ? '未知' : dhTblN) + ' 行 ⊃ 池路行 ＋ 已终结行 ⇒ ⛔ 表长 ≠ 待回执数）｜' + dhFilter;
  /* ⭐ pm_刀11p §二.1：**受理**之「源」⛔ 写 `POST`（POST ＝ 写路 · ⛔ 读源）⇒ 明标「未接（无读源）」
     （⛔ 以 `0` 充「未接」）；本页计数照实另书（本页口径 · ⛔ 后端）。 */
  if(stEl) stEl.innerHTML =
    paRow('受理', PA_GAP.todo() + ' · 本页已接 ' + paLocalTasks.length + ' 件',
      '源：' + PA_GAP.todo('后端无「受理态」读面 —— POST /v9/pa/dialog ／ POST /v9/agent/chat 为写路（⛔ 读源）') + '｜本页计数 ＝ 本页已接（本页口径 · ⛔ 后端口径 · ⛔ 以 0 充未接）')
  + paRow('在办', inFlightVal, paEsc(srcPlain))
  + paRow('等待外部结果', (dhWaitN !== null)
        ? (dhWaitN === 0 ? '0 件（后端真判据下无待回执之件 · 空态 · 非故障）'
                         : dhWaitN + ' 件（席位轴 to_seat 之件 · 待外部回执；表长 ' + (dhTblN === null ? '未知' : dhTblN)
                           + ' ⊃ 池路 ' + (dhPoolN === null ? '未知' : dhPoolN) + ' ＋ 已终结）')
        : '未知（后端未应答）',
      dhSrcLine)
  + paRow('待你裁', (nA === null ? '未知（后端未应答 ／ 无参 ⇒ 400）' : (nA === 0 ? '0 件（后端 approvals: []）' : nA + ' 件')),
      '源：GET /v9/audit/approvals · 属会话 ' + paEsc(curSession()) + '（**本会话** · ⛔ 全局数）｜无参 ⇒ 400（⛔ 把错误渲染成 0）')
  + paRow('已完成', (nR === null ? '未知（后端未应答）' : (nR === 0 ? '0 件（后端 runs: []）' : nR + ' 件（state=done）')),
      '源：GET /v9/pes/runs（按 user_id 取 · ⛔ 会话轴 ⇒ ⛔ 与本会话之数互校）');

  /* —— 左栏 · 任务台账（源 /v9/metrics/tool_flow · 真数据）—— */
  const by = (mf && mf.stats && mf.stats.by_task) ? mf.stats.by_task : null;
  const keys = by ? Object.keys(by).sort(function(a, b){ return (by[b].count || 0) - (by[a].count || 0); }) : [];
  const ttMf = await paTtManifestGet();
  const ttRule = paTtLedgerRule(ttMf);
  /* ⭐ pm_刀9 §二 ＋ 刀11p §二.2：活面之数须附**刻** ＋ **窗**（源 stats.generated_at ／ stats.window_hours）
     —— ⛔ 无刻之数不可作据（承 L76）。⭐ 并标**会话归属**（by_task 之键 ＝ 会话 id · 承 刀11p §二.3）。 */
  const mfAtStr = (mf && mf.stats && mf.stats.generated_at != null) ? ('刻 ' + paTsLocal(mf.stats.generated_at))
    : '刻缺（后端未给 stats.generated_at）';
  const mfWinStr = (mf && mf.stats && mf.stats.window_hours != null) ? ('窗 ' + mf.stats.window_hours + ' h')
    : '窗缺（后端未给 stats.window_hours）';
  const mySid = String(curSession());
  const sessMark = function(k){ return String(k) + '（' + (String(k) === mySid ? '本会话' : '⛔ 非本会话') + '）'; };
  paV3Txt('paTaskLedgerSrc', (by ? ('源：GET /v9/metrics/tool_flow · ' + keys.length + ' 项 · ' + mfAtStr + ' · ' + mfWinStr
      + ' · 会话：' + (keys.map(sessMark).join(' ／ ') || '—') + '｜本会话 ＝ ' + mySid)
      : ('源：GET /v9/metrics/tool_flow · 未知（后端未应答）· ' + mfAtStr + ' · ' + mfWinStr))
    + '｜测试痕判据：' + (ttRule ? '清单已取（' + (ttRule.patterns.length) + ' 名形）' : '清单未取／无该键 ⇒ 一条也不收'));
  const lg = document.getElementById('paTaskLedger');
  if(lg){
    function rowOf(k){
      const r = by[k] || {};
      const own = (String(k) === mySid) ? '本会话' : '⛔ 非本会话';
      return '<div title="会话 ' + paEsc(String(k)) + '（' + own + '）· ' + paEsc(mfAtStr) + ' · ' + paEsc(mfWinStr)
        + ' · 源：GET /v9/metrics/tool_flow by_task[' + paEsc(String(k)) + ']">'
        + '会话 ' + paEsc(String(k).slice(0, 42)) + '（' + own + '）'
        + ' —— 工具 ' + (r.count == null ? '未知' : r.count) + ' 次 · 成 '
        + (r.success_rate == null ? '未知' : r.success_rate + '%') + ' · 均 ' + (r.avg_ms == null ? '未知' : r.avg_ms)
        + ' ms · ' + paEsc(mfAtStr) + ' · ' + paEsc(mfWinStr) + '</div>';
    }
    if(!keys.length){
      lg.innerHTML = '<div>0 项（后端未应答或空库 ⇒ 空态 · ⛔ 编）</div>';
    }else{
      const real = [], tst = [];
      keys.forEach(function(k){ (paTtIsTestName(k, ttRule) ? tst : real).push(k); });
      let html = real.length ? real.slice(0, 12).map(rowOf).join('')
                             : '<div>0 项（真任务 · 名形皆命中测试痕清单 ⇒ 全数入下）</div>';
      if(tst.length){
        html += '<details class="eng" data-tt="taskledger">'
          + '<summary title="判据（外置可配 · ' + paEsc('pa/测试痕_清单.json 之「任务台账_测试名」') + '）：'
          + paEsc(String((ttRule && ttRule.rule) || '')) + '">'
          + '🧪 测试痕 ' + tst.length + ' 项（名形命中清单 · 收起 · 展开可见 · ⛔ 丢）</summary>'
          + '<div>' + tst.map(rowOf).join('') + '</div></details>';
      }
      lg.innerHTML = html;
    }
  }

  /* —— 左栏 · 行为闸 ＋ 干预 —— */
  const g = document.getElementById('paTaskGates');
  if(g) g.innerHTML =
    '<div class="g"><b>受理门永不关</b>：任何时刻之输入皆受理（⛔ 置灰输入 ／ ⛔ 拒件 · ⛔「稍等一下」类文案）。'
    + '<br>输入分类（新任务 ／ 改令 ／ 追问 ／ 闲聊）' + PA_GAP.todo('后端无端点（须开读面 ⇒ 承批四）· 按真实意图分（⛔ 按「忙」分）') + '。</div>'
    + '<div class="g"><b>打断 · 生效时点照实</b>：排队中 ⇒ 即时作废；已在跑 ⇒ <b>下一步边界生效</b>（后端置取消标志 · ⛔ 硬杀）。'
    + '<div class="gr"><button onclick="paIntervene(\'改令\')" title="POST /v9/pa/steer（通道已在 ＝ shared_state.add_steer ／ drain_steer · 承 PM 1254）⇒ ⭐ 面不可达时明标「不可达」· ⛔ 静默">✏️ 改令</button>'
    + '<button onclick="paIntervene(\'中止\')" title="POST /v9/cancel/&lt;session_id&gt;（routes/session.py · 会话级协作取消 · 置位取消标志 ⇒ bridge_loop 下轮检查点退出 · ⛔ 硬杀）">⏹ 中止本线程（会话级 · 下一步边界生效）</button>'
    + '<button onclick="paIntervene(\'接管\')" disabled title="无此端点 —— 后端无「接管」之概念（gateway_routes.py 逐路名 0 命中）· ⭐ 待立项（须先定义：接谁的管 ／ 界在何 ／ 可否逆 ／ 是否触他方平台）">🤝 接管 · 待立项（须先定义）</button></div></div>'
    + '<div class="g"><b>交互不锁 · 执行排队</b>：并行 ＝ <b>编排并行 · 推理排队</b>（6 GB 单卡 · 并发 1）⇒ ⛔ 让用户以为「多模型并行」。</div>'
    + '<div class="g"><b>本页任务（后端事件改写 · ⛔ 前端猜）</b><div id="paLocalList"></div></div>';
  paRenderLocalTasks();

  /* —— 右栏 · 派活 —— */
  const nSub = (st && Array.isArray(st.subtasks)) ? st.subtasks.length : null;
  const rows = document.getElementById('paSeatRows');
  if(rows) rows.innerHTML =
    paRow('能力端点', (ro && ro.count != null)
        ? paEsc('编队花名册 ' + ro.count + ' 卡（' + ((ro.by_level && Object.keys(ro.by_level).length) ? Object.keys(ro.by_level).sort().join('／') : '—') + '）· ' + (((ro.rows || []).slice(0,3).map(function(x){ return x.name || x.id; }).join(' · ')) || '—'))
        : '未知（后端未应答）',
      '源：GET /v9/pa/roster（面名「能力端点册」 · 14 卡 · 派活前「谁能干」 · ⛔ 非组织席位册）｜⭐ 组织席位册 ＝ GET /v9/pa/seats（14 席 · 已接 · 见下「派席」）｜实时驻留态 ＝ GET /v9/pa/env 之 cols.agents（kind=seat）')
  + paRow('对端', lc ? paEsc((lc.client || '（未命名）') + ' · connected=' + lc.connected) : '未知（后端未应答）',
      '源：GET /v9/pa/local_client/status')
  + paRow('在办', (nSub === null ? '未知（后端未应答）' : nSub + ' 件'), '源：GET /v9/subtask/status')
  + paRow('待验收', (nA === null ? '未知（后端未应答）' : nA + ' 件'), '源：GET /v9/audit/approvals')
  + paRow('凭据在册', pm ? paEsc('权限档 ' + (pm.level || '未知') + ' · 授权档 ' +
      (pm.grant && pm.grant.pa ? (pm.grant.pa.exists ? '在' : '缺') : '?') + ' ／ ' +
      (pm.grant && pm.grant.pes ? (pm.grant.pes.exists ? '在' : '缺') : '?')) : '未知（后端未应答）',
      '源：GET /v9/pa/permission')
  + paRow('派活之路', '派席（带 to_seat）' + (dhSeatN === null ? '：未知' : ('：' + dhSeatN + ' 行'))
      + ' ｜ 派池（subtask_pool）' + (dhPoolN === null ? '：未知' : ('：' + dhPoolN + ' 行')),
      '源：GET /v9/pa/dispatch/history（两轴 · 逐行谓词）｜⭐ 本面「派池」钮 ＝ POST /v9/subtask/create（source=subtask_pool ⇒ 件 ⛔ 进席）｜⭐ 本面「派席」钮 ＝ POST /v9/pa/dispatch {task_text, to_seat}（席轴 ⇒ 投到席）');

  /* —— 右栏 · 环境面 · agents（五列 · 承 pm_刀7p ／ 刀3′）—— */
  paEnvAgentsRows(rows, ro, roF);

  /* ⭐ 刀11p §一：派活两钮（派池 ⟷ 派席）—— 静态壳不动，由本件于 DOM 上落。 */
  try{ await paSubRouteInit(); }catch(e){}

  /* —— 右栏 · 子任务池 —— */
  paV3Txt('paSubSrc', '源：GET /v9/subtask/status · ' + (nSub === null ? '未知（后端未应答）' : nSub + ' 件'));
  /* ⭐ pm_1061 §二：两处「在办」行（五态 ／ 池畔）皆补 `title` —— 值槽 ＝ 值全文 ＋（有失败条 ⇒ 因全文）
     ∧ 源槽 ＝ 源行全文（⛔ 截 · 悬停可回）。⚠ 只赋属性 ⇒ 零 CSS ／ 零控件 ／ ⛔ 动 `paRow` 之形（其 ⛔ 支持属性）。 */
  paAttachRowTitle(stEl, '在办', inFlightTitle, srcPlain);
  /* ⭐ 刀11p：新改之两行亦被 nowrap ＋ ellipsis 截 ⇒ 补 title（⛔ 截 · 悬停可回 · 零 CSS）。 */
  paAttachRowTitle(stEl, '受理', PA_GAP.todo() + ' · 本页已接 ' + paLocalTasks.length + ' 件',
    '源：' + PA_GAP.todo('后端无「受理态」读面 —— POST /v9/pa/dialog ／ POST /v9/agent/chat 为写路（⛔ 读源）') + '｜本页计数 ＝ 本页已接（本页口径 · ⛔ 后端口径 · ⛔ 以 0 充未接）');
  paAttachRowTitle(stEl, '等待外部结果',
    ((dhWaitN === null) ? '未知（后端未应答）' : (dhWaitN + ' 件（席位轴 to_seat 之件 · 待外部回执）')),
    dhSrcLine);
  paAttachRowTitle(rows, '在办',
    ('在办 ' + (nSub === null ? '未知（后端未应答）' : nSub + ' 件')
      + (subFailNotes.length ? ('\n（池内失败条之因 · 全文）\n' + subFailNotes.join('\n')) : '')),
    '源：GET /v9/subtask/status');
  const sl = document.getElementById('paSubtaskList');
  if(sl) sl.innerHTML = (nSub === null)
    ? '<div>未知（后端未应答）</div>'
    : (nSub === 0 ? '<div>0 件（后端 subtasks: []）· 空态</div>'
      : st.subtasks.map(paSubRowHtml).join(''));
  paEnsureSubPop();
}

/* —— 子代理面 · 独立窗口（承 pm_1024 §二.3）：⧉ 开新窗 ⇒ **只读同源**（GET /v9/subtask/status · ⛔ 改状态 · ⛔ 另起读数） —— */
function paEnsureSubPop(){
  try{
    var src = document.getElementById('paSubSrc'); if(!src) return;
    var head = src.parentNode; if(!head) return;
    if(document.getElementById('paSubPop')) return;
    var b = document.createElement('button');
    b.id = 'paSubPop'; b.type = 'button'; b.className = 'pachbtn'; b.textContent = '⧉';
    b.title = '独立窗口：只读同源 GET /v9/subtask/status（⛔ 改状态 · ⛔ 触模型）';
    b.setAttribute('aria-label', '子任务池 · 独立窗口（只读同源）');
    b.onclick = function(){ paSubtaskPop(); };
    head.appendChild(b);
  }catch(e){}
}
function paSubtaskPop(){
  var w = null;
  try{ w = window.open('', 'pa_subtask_pool', 'width=560,height=640'); }catch(e){ w = null; }
  if(!w){ try{ addLog('⧉ 独立窗口被浏览器拦下（⛔ 弹出未允）· 如实记', 'warn', true, '子代理面'); }catch(e){} return; }
  var u = encodeURIComponent(curUser()), sid = encodeURIComponent(curSession());
  var url = API + '/v9/subtask/status?user_id=' + u + '&session_id=' + sid;
  var html = '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
    + '<title>子任务池 · 独立窗口（只读同源）</title>'
    + '<style>body{background:#0d1117;color:#e6edf3;font:12.5px/1.7 ui-monospace,Consolas,monospace;margin:0;padding:14px}'
    + 'h1{font-size:13px;margin:0 0 6px}.src{color:#8b949e;font-size:11px;margin-bottom:10px;white-space:pre-wrap}'
    + '.r{border-bottom:1px dashed #30363d;padding:4px 0}.na{color:#8b949e}'
    + 'details.eng{margin-top:3px}details.eng>summary{cursor:pointer;font-size:11px;color:#8b949e;list-style:none}'
    + 'details.eng>summary::-webkit-details-marker{display:none}'
    + 'details.eng>.engbody{margin-top:2px;font-size:11px;color:#8b949e;white-space:pre-wrap;word-break:break-word}'
    + '</style></head><body>'
    + '<h1>子任务池（A31 实例层）· 独立窗口</h1>'
    + '<div class="src" id="src"></div><div id="list"></div>'
    + '<script>(function(){var url=' + JSON.stringify(url) + ';'
    + 'function esc(x){return String(x==null?"":x).replace(/[&<>"]/g,function(c){return ({"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;"})[c];});}'
    + 'function tick(){fetch(url,{cache:"no-store"}).then(function(r){return r.ok?r.json():null;}).catch(function(){return null;}).then(function(j){'
    + 'var s=document.getElementById("src"),l=document.getElementById("list");var at=new Date().toLocaleTimeString("zh-CN",{hour12:false});'
    + 'if(!j||!j.success){s.textContent="源：GET /v9/subtask/status · 读数刻 "+at+" · ⚠ 后端未应答 ⇒ 本窗按「未知」记";l.innerHTML="<div class=na>未知（后端未应答）</div>";return;}'
    + 'var a=(j.subtasks||[]);s.textContent="源：GET /v9/subtask/status（只读 · 同源）· 采样刻 "+at+" · "+a.length+" 件";'
    + 'var SCN={pending:"待审"};'
    + 'l.innerHTML=a.length?a.map(function(x){var id=x.task_id||x.id||"?";var st=x.status||"";var sp=(x.spec==null?"":String(x.spec)).trim();var sf=sp.replace(/\\s+/g," ");var h="<div class=r>"+esc(id)+" · "+esc(SCN[st]||st||"未知")+(sp?" · <span title=\\"spec 原文（后端 spec 字段 · 逐字 · ⛔ 截断）："+esc(sp)+"\\">spec："+esc(sf.slice(0,40))+(sf.length>40?"…":"")+"</span>":" · spec：（无 spec）");'
    + 'if(st==="failed"||st==="pending"){var lbl=(st==="pending")?"待审因":"失败因";var e=(x.error==null?"":String(x.error)).trim();if(e){var f=e.replace(/\\s+/g," ");h+=" · <span title=\\""+lbl+"（原文 · ⛔ 截断）："+esc(e)+"\\">"+lbl+"："+esc(f.slice(0,80))+(f.length>80?"…":"")+"</span><details class=eng><summary>"+lbl+"原文（全 "+e.length+" 字 · 收起 · 展开可见）</summary><div class=engbody>"+esc(e)+"</div></details>";}else{h+=" · "+lbl+"：（后端未给因）";}}return h+"</div>";}).join(""):"<div class=na>0 件（后端 subtasks: []）· 空态</div>";'
    + '});}tick();setInterval(tick,5000);})();</script></body></html>';
  try{ w.document.open(); w.document.write(html); w.document.close(); }
  catch(e){ try{ w.location.href = 'about:blank'; }catch(e2){} }
  try{ addLog('⧉ 已开独立窗口（只读同源 GET /v9/subtask/status · ⛔ 改状态）', 'ok', true, '子代理面'); }catch(e){}
}

function paRenderLocalTasks(){
  const el = document.getElementById('paLocalList'); if(!el) return;
  el.innerHTML = paLocalTasks.length
    ? paLocalTasks.slice(0, 6).map(function(t){
        return '<div>' + paEsc(t.id) + ' · <b>' + paEsc(t.state) + '</b> · ' + paEsc(t.note)
          + '<br><span style="opacity:.8">状态来源：' + paEsc(t.src) + ' · ' + paEsc(t.ts) + '（样张号域 · ⛔ 冒真凭据）</span></div>';
      }).join('')
    : '<div>本页未发起任务</div>';
}

/* —— 干预（中止 ＝ 真端点；改令 ＝ 准接（POST /v9/pa/steer）；接管 ＝ 待立项（须先定义））—— */
/* ⭐ 丙-3／丙-6：改令 ＝ 准接（POST /v9/pa/steer · 承 PM 1254 ／ TD 1082 §二）。
   ⚠ ⛔ 用 paGetJson（today.js 非 2xx ⇒ null ⇒ 与「不可达」同形 —— 空 ⛔ 混 缺）⇒ 本节自取 body（承 PM 1254 §二.⒉）。
   信封从蓝图（ok）· 键从族（missing ／ kind ／ route）：承 PM 1253 §二 裁一。
   queued:true ＝ 「已入队」（⛔ 「已生效」）⇒ 承 PM 1254 §二.⒊；⛔ 报 queued_count（通道唯 drain ⇒ 得数必先消费）。 */
async function paSteerPost(sid, text, kind){
  try{
    const r = await fetch(API + '/v9/pa/steer', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({session_id: sid, text: text, kind: kind, user_id: curUser()})});
    let d = null;
    try{ d = await r.json(); }catch(e){ d = null; }
    if(r.ok && d && d.ok === true){ return {ok:true, d:d}; }
    /* 400 之三支须可辨（⛔ 以「提交失败」一辞盖之）—— 承 PM 1254 §二.⒉ */
    if(d && d.kind === 'missing_param'){ return {ok:false, why:'缺参（' + (((d.missing || []).join(' ／ ')) || '?') + '）'}; }
    if(d && d.kind === 'over_limit'){ return {ok:false, why:'超限（text ' + (d.text_len == null ? '?' : d.text_len) + ' ＞ ' + (d.allowed_max == null ? '?' : d.allowed_max) + ' 字）'}; }
    if(d && d.kind === 'bad_value'){ return {ok:false, why:'值非法（kind ＝ ' + kind + ' · 后端仅受 ' + JSON.stringify(d.allowed || []) + '）'}; }
    if(r.ok){ return {ok:false, why: PA_GAP.down('HTTP ' + r.status + ' · 回执无 ok ⇒ 信封不合（承 PM 1253 §二）')}; }
    return {ok:false, why: PA_GAP.down('HTTP ' + r.status + (d ? '' : ' · ⛔ 未取得回执体'))};
  }catch(e){
    return {ok:false, why: PA_GAP.down('请求未送达：' + String((e && e.message) || e) + ' · ⛔ 不等于已入队')};
  }
}
async function paIntervene(kind){
  const sid = curSession();
  const out = document.getElementById('paSubOut');
  /* 接管 ＝ 待立项（须先定义）⇒ 钮 disabled（⛔ 静默 · 其由在 title · 承 PM 1254 §三） */
  if(kind === '接管'){ if(out) out.textContent = '接管：无此端点（后端无「接管」之概念）⇒ 待立项（须先定义）· ⛔ 未发送'; return; }
  if(kind === '改令'){
    if(!out) return;
    const text = String((window.prompt('改令 · 下一步指导（≤500 字 · POST /v9/pa/steer）') || '')).trim();
    if(!text){ out.textContent = '改令：内容为空 ⇒ ⛔ 未发送（⛔ 开空件）'; return; }
    out.textContent = '改令：提交中…（POST /v9/pa/steer）';
    const res = await paSteerPost(sid, text, '改令');
    if(!res.ok){ out.textContent = '改令：' + res.why; return; }
    out.textContent = '改令：已入队 · 下一轮生效（通道 consumer ＝ 每轮 drain 即清 · ' + String(res.d.inject_point || '?') + '）'
      + '｜后端 ' + String(res.d.at || '?') + ' · 印 ' + String(res.d['印'] || '?');
    return;
  }
  try{
    const r = await fetch(API + '/v9/cancel/' + encodeURIComponent(sid), {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'});
    const d = await r.json().catch(function(){ return null; });
    if(out) out.textContent = '中止：' + (d && d.success ? ('已置取消标志（' + (d.session_id || sid) + '）· 下一步边界生效')
      : ('后端未确认（HTTP ' + r.status + '）· 如实记'));
  }catch(e){
    if(out) out.textContent = '中止：请求未送达（' + String((e && e.message) || e) + '）· ⛔ 不等于已中止';
  }
}

/* —— 派活 · 提交（真端点 POST /v9/subtask/create · 深度预算 ≤ 3）—— */
async function paSubtaskSubmit(){
  const inp = document.getElementById('paSubInput'), out = document.getElementById('paSubOut');
  const spec = inp ? String(inp.value || '').trim() : '';
  if(!spec){ if(out) out.textContent = '派活：内容为空 ⇒ 未提交（⛔ 不开空件）'; return; }
  if(out) out.textContent = '派活：提交中…（POST /v9/subtask/create）';
  try{
    const r = await fetch(API + '/v9/subtask/create', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({user_id: curUser(), session_id: curSession(), task_spec: spec, depth: 0})});
    const d = await r.json().catch(function(){ return null; });
    if(out) out.textContent = '派活回执：' + (d ? JSON.stringify(d).slice(0, 220) : ('HTTP ' + r.status + ' · ⛔ 未取得回执'));
    if(d && d.success && inp) inp.value = '';
  }catch(e){
    if(out) out.textContent = '派活：请求未送达（' + String((e && e.message) || e) + '）· ⛔ 不等于已派';
  }
  paLoadTasks();
}

/* ===== 派活 之 两路：**派池** ⟷ **派席**（⛔ 以「派活」一词盖两义 · 承 pm_刀8p §二 ／ 刀11p §一）=====
   实读（一手）：`web\pa.html:284` 明书「POST /v9/subtask/create」＝ **池路**（落账 source=subtask_pool）
   ⇒ 在「A30 组织层 · 席位」屏按「派活」，件 **⛔ 进席**。
   席路（已通）＝ `POST /v9/pa/dispatch {task_text, to_seat}` ⇒ 落 to_seat 行（席轴）。
   ⇒ 两钮**分标**：派池（既有钮 · 改标）⟷ 派席（本件新钮 · 带席 · 真投到席）。
   ⚠ 界：`pa.html` ＝ **壳**（⛔ 本席动）⇒ 钮之改标 ＋ 新钮 ＋ 席选 **皆由本件于 DOM 上落**（承 1050「本卡内」之法）；
     ⛔ 另起新壳。席之真源 ＝ `GET /v9/pa/seats`（**组织席位册** · ⛔ 手搓 · ⛔ 凭印象）。 */
async function paSubRouteInit(){
  try{
    const btn = document.getElementById('paSubSend');
    const form = (btn && btn.parentNode) ? btn.parentNode : null;
    if(!btn || !form) return 0;
    btn.textContent = '派池';
    btn.title = '池路：POST /v9/subtask/create（落账 source=subtask_pool · ⛔ 进席）；「派席」钮在其下（投到席 · 席轴）';
    let box = document.getElementById('paSubRoute');
    if(!box){
      box = document.createElement('div');
      box.id = 'paSubRoute';
      box.setAttribute('data-axis', 'subroute');
      box.style.cssText = 'margin:4px 0 2px;font-size:10.5px;line-height:1.75;color:var(--sub)';
      const l1 = document.createElement('div');
      l1.appendChild(document.createTextNode('派席（投到席 · 席轴）⟷ 派池（有界并发池 · ⛔ 进席）　席：'));
      const sel = document.createElement('select');
      sel.id = 'paSeatSel';
      sel.title = '席之真源：GET /v9/pa/seats（组织席位册）';
      const sb = document.createElement('button');
      sb.id = 'paSeatSend';
      sb.type = 'button';
      sb.textContent = '派席';
      sb.title = '席路：POST /v9/pa/dispatch {task_text, to_seat}（真投到席）';
      sb.onclick = paSeatSubmit;
      l1.appendChild(sel); l1.appendChild(document.createTextNode(' ')); l1.appendChild(sb);
      const l2 = document.createElement('div');
      l2.style.cssText = 'font-size:10px;opacity:.92';
      l2.textContent = '源：GET /v9/pa/seats（组织席位册 · ⛔ 手搓）｜「派池」＝ POST /v9/subtask/create（source=subtask_pool）｜「派席」＝ POST /v9/pa/dispatch {task_text, to_seat}（落 to_seat 行 · 投到席）';
      box.appendChild(l1); box.appendChild(l2);
      form.parentNode.insertBefore(box, form.nextSibling);
    }
    const sel = document.getElementById('paSeatSel');
    const j = await paGetJson(API + '/v9/pa/seats');
    const rows = (j && Array.isArray(j.rows)) ? j.rows : null;
    if(sel){
      const sig = rows ? (rows.length + ':' + rows.map(function(s){ return String((s && s.id) || ''); }).join(',')) : 'nosrc';
      if(sel.dataset.sig !== sig){
        sel.innerHTML = '';
        if(!rows){
          const o = document.createElement('option'); o.value = ''; o.textContent = PA_GAP.down('席册：GET /v9/pa/seats 未应答');
          sel.appendChild(o);
        }else{
          rows.forEach(function(s){
            const o = document.createElement('option');
            o.value = String((s && s.id) || '');
            o.textContent = String((s && s.id) || '?') + ' · ' + String((s && s.name) || '（未命名）');
            sel.appendChild(o);
          });
        }
        sel.dataset.sig = sig;
      }
      if(box) box.dataset.seats = rows ? String(rows.length) : 'nosrc';
    }
    return rows ? rows.length : 0;
  }catch(e){ return 0; }
}
async function paSeatSubmit(){
  const inp = document.getElementById('paSubInput'), out = document.getElementById('paSubOut');
  const sel = document.getElementById('paSeatSel');
  const spec = inp ? String(inp.value || '').trim() : '';
  const seat = sel ? String(sel.value || '').trim() : '';
  if(!spec){ if(out) out.textContent = '派席：内容为空 ⇒ 未提交（⛔ 不开空件）'; return; }
  if(!seat){ if(out) out.textContent = '派席：未选席 ⇒ 未提交（⛔ 静默兜底）；席之真源 GET /v9/pa/seats'; return; }
  if(out) out.textContent = '派席：提交中…（POST /v9/pa/dispatch · to_seat=' + seat + '）';
  try{
    const r = await fetch(API + '/v9/pa/dispatch', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({user_id: curUser(), task_text: spec, to_seat: seat})});
    const d = await r.json().catch(function(){ return null; });
    if(out) out.textContent = '派席回执：' + (d ? JSON.stringify(d).slice(0, 240) : ('HTTP ' + r.status + ' · ⛔ 未取得回执'));
    if(d && (d.ok || d.success) && inp) inp.value = '';
  }catch(e){
    if(out) out.textContent = '派席：请求未送达（' + String((e && e.message) || e) + '）· ⛔ 不等于已派';
  }
  paLoadTasks();
}

/* ===== 四新面（环境 ／ 产品线 ／ 开机 ／ 收口）（承 pm_刀3 ／ 刀3′ ／ 刀7p ／ 刀13p ／ 刀14p）=====
   出处（老板令）：「PA先具备本机扫描 agent 的能力……PA 如何去管理才是重点」＋「产品形态是否完善」。
     `pa.html` ＝ **内容件**（⛔ 我动 · 承 pm_1052 ／ pm_1067）⇒ 四新面由**本件于解析期注入**其 DOM
     （承本件 `paSubRouteInit` `:661` 之注法 · ⛔ 另起新壳）；`today.js` 已开钩 `paXFaceHooks` ＋ `setFace` 后调之。
   口径（承 L76 ／ pm_刀12p §〇／§一）：面之上文**全取后端**（⛔ 手搓）；三态分显
     **未接**（后端无此面 ／ 无此键）⟷ **不可达**（后端此刻不在 ／ 未应答）⟷ **真 0**；**空 ≠ 缺**；
     密钥唯「有／无」（⛔ 值 ／ ⛔ 长度 ／ ⛔ 尾号）；每项可**点回真源**（`src` 逐字 ＋ 点开取后端原文）；
     每读数附 **面 ／ 滤 ／ 式 ／ 数**（`面` ＝ 接口径逐字）。 */

function paXTwo(a, b){
  return '<div style="display:flex;gap:14px;align-items:flex-start">'
    + '<div style="flex:1 1 0;min-width:0">' + a + '</div>'
    + '<div style="flex:1 1 0;min-width:0">' + b + '</div></div>';
}
function paXUnreached(id, label, why){
  var e = document.getElementById(id);
  if(e) e.innerHTML = paRow(label, PA_GAP.down('后端此刻不在 ／ 未应答'),
    '源：' + why + ' —— **不可达**（此刻不在）≠ **未接**（后端无此面 · 承 pm_刀12p §〇）', true);
}
function paXMissing(id, label, why, key){
  var e = document.getElementById(id);
  if(e) e.innerHTML = paRow(label, PA_GAP.fallback(key || why), '源：' + why, true);
}

const PA_XFACE = [
  ['env',     '环境',   '环境感知面 · 四栏（agents ／ kb ／ tools ／ resources）· 源 GET /v9/pa/env', true],
  ['lines',   '产品线', '产品线面（线名 ／ 席 ／ 件集 ／ 状态 ／ 下一拍）· 源 GET /v9/pa/lines', false],
  ['resume',  '开机',   '开机面（断点续：上次断点 ／ 离线区间 ／ 攒件 ／ 续办 ／ 幂等跳过 ／ 失败件）· 源 GET /v9/pa/resume', false],
  ['receipt', '收口',   '收口面（四段 ＋ 回执四件（件号／席／果／印）＋ 催数 · 每件自带件之刻）· 源 GET ／ POST /v9/pa/dispatch/receipt', true]
];
/* ⭐ pm_裁_主面环≤5：true ⇒ 入主面环（#faceTabs ＋ PA_V3_FACES）；false ⇒ 入「更多 ▾」之「④ 面」组
   （注入 #paMoreBody · 各一步可达）。⛔ 丢功能：两者**皆建 pane**（data-face 逐字不变 ⇒ 旧 DOM 之引 ⛔ 破）。 */
function paXOpenFace(id){
  try{ if(typeof setFaceById === 'function'){ setFaceById(id); } }catch(e){}
  try{ if(typeof paMore === 'function'){ paMore(false); } }catch(e){}   /* 面开 ⇒ 收抽屉（⛔ 挡面） */
}
function paXMoreHost(){
  var body = document.getElementById('paMoreBody');
  if(!body) return null;
  var box = document.getElementById('paXMoreFaces');
  if(!box){
    box = document.createElement('details');
    box.className = 'mgrp'; box.id = 'paXMoreFaces'; box.open = true;
    box.innerHTML = '<summary>④ 面 · 产品线 ／ 开机（主面环 ≤5 ⇒ 此折叠 · 各一步可达）</summary>'
      + '<section class="msec" id="paXMoreTabs" style="display:flex;gap:8px;flex-wrap:wrap;padding:6px 0 2px"></section>'
      + '<p class="mnote">源：<code>GET /v9/pa/lines</code>（产品线）｜<code>GET /v9/pa/resume</code>（开机）。'
      + '此二面 ⛔ 占主面环（承 pm_裁_主面环≤5）· ⛔ 丢功能（pane 与 data-face 一字未删）。</p>';
    body.insertBefore(box, body.firstChild);
  }
  return document.getElementById('paXMoreTabs');
}

const PA_XFACE_SKEL = {
  env:
    '<div class="ch">环境面 · 顶栏（版 ／ 刻 ／ 印 ／ 守卫 ／ 调度）<span class="src" id="paEnvTopSrc">读数中…</span></div>'
  + '<div class="tstates" id="paEnvTop"></div>'
  + '<div class="ch">环境面 · counts ⟷ cols 对表<span class="src">⛔ 手搓 · 不齐 ⇒ 显红（承 刀3′ §二）</span></div>'
  + '<div class="tstates" id="paEnvJudge"></div>'
  + '<div class="ch">agents 栏（组织席位册 ＋ 能力端点册）<span class="src" id="paEnvColSrc-agents">读数中…</span></div>'
  + '<div class="tstates" id="paEnvCol-agents"></div>'
  + '<div class="ch">kb 栏（知识库）<span class="src" id="paEnvColSrc-kb">读数中…</span></div>'
  + '<div class="tstates" id="paEnvCol-kb"></div>'
  + '<div class="ch">tools 栏（器）<span class="src" id="paEnvColSrc-tools">读数中…</span></div>'
  + '<div class="tstates" id="paEnvCol-tools"></div>'
  + '<div class="ch">resources 栏（模型 ／ 端口 ／ num_ctx ／ GPU ／ 磁盘）<span class="src" id="paEnvColSrc-resources">读数中…</span></div>'
  + '<div class="tstates" id="paEnvCol-resources"></div>',
  lines:
    '<div class="ch">产品线面 · 逐线<span class="src" id="paLinesSrc">读数中…</span></div>'
  + '<div class="tstates" id="paLinesHead"></div>'
  + '<div id="paLinesList"></div>',
  resume:
    '<div class="ch">开机面 · 断点续<span class="src" id="paResumeSrc">读数中…</span></div>'
  + '<div class="tstates" id="paResumeHead"></div>'
  + '<div class="ch">上次断点 ／ 攒件 ／ 跳过 ／ 失败件</div>'
  + '<div class="tstates" id="paResumeLeft"></div>'
  + '<div class="ch">未竟 ／ 只读对表 ／ 数之式</div>'
  + '<div class="tstates" id="paResumeRight"></div>',
  receipt:
    '<div class="ch">收口面 · 四段〔已派 ⇒ 已收 ⇒ 在做 ⇒ 已收口〕<span class="src" id="paRcptSrc">读数中…</span></div>'
  + '<div class="tstates" id="paRcptBoard"></div>'
  + '<div class="ch">收口面 · 逐件（件号 ／ 席 ／ 果 ／ 印 ＋ 自带「件之刻」）<span class="src" id="paRcptListSrc">读数中…</span></div>'
  + '<div id="paRcptList"></div>'
  + '<div class="ch">武装 · 调用 <span class="src">POST /v9/pa/agent/invoke（三类执行器：seat ／ cli ／ api）</span></div>'
  + '<div class="subform"><select id="paInvSel" title="被调者之真源：POST /v9/pa/agent/invoke {}（agent_id 空 ⇒ 回册）"></select>'
  + '<input id="paInvTask" placeholder="交给该执行器的一句话（mode=auto）">'
  + '<button id="paInvGo" onclick="paInvokeNow()">调用</button></div>'
  + '<div class="out" id="paInvOut"></div>'
  + '<div class="ch">⭐ 一键出件槽位（Consumer 线 · 填两空 ⇒ 【出件】⇒ 卡上点一下即发）<span class="src" id="paSlotSrc">读数中…</span></div>'
  + '<div class="subform" style="flex-wrap:wrap;gap:6px">'
  + '<input id="paSlotTo" placeholder="① 对象 · 收件人（空 ⇒ 本人；多人用逗号分隔，提交时自动归一为列表）" oninput="paSlotJudgeRender()">'
  + '<input id="paSlotAsk" placeholder="② 旧事 · 一句话（催什么）" style="min-width:300px">'
  + '<input id="paSlotRef" placeholder="③ 原信 · 件号（可空）">'
  + '<button id="paSlotGo" onclick="paSlotOut()">④ 出件</button>'
  + '<span style="color:var(--sub)">人工步数 <b id="paSlotSteps">0／2</b></span></div>'
  + '<div class="tstates" id="paSlotJudge"></div>'
  + '<div class="out" id="paSlotOut"></div>'
};

(function(){
  var TABS = document.getElementById('faceTabs'), HOST = document.getElementById('faces');
  if(!TABS || !HOST) return;
  var proto = TABS.querySelector('button[data-face]');
  if(!proto) return;
  var added = [], btns = {}, outIds = [];
  PA_XFACE.forEach(function(f){
    var id = f[0], label = f[1], title = f[2], ring = (f[3] !== false);
    if(ring && typeof PA_V3_FACES !== 'undefined' && !PA_V3_FACES.some(function(x){ return x.id === id; })){
      PA_V3_FACES.push({id: id, label: label});
    }
    if(HOST.querySelector('.facePane[data-face="' + id + '"]')) return;
    var b = document.createElement('button');
    b.className = proto.className;
    b.setAttribute('role', 'tab');
    b.setAttribute('aria-pressed', 'false');
    b.setAttribute('data-face', id);
    b.title = title;
    b.textContent = label;
    b.onclick = function(){ paXOpenFace(id); };
    btns[id] = b;
    if(ring){ TABS.appendChild(b); }
    else { b.setAttribute('data-ring', 'out'); outIds.push(id); var mh0 = paXMoreHost(); (mh0 || TABS).appendChild(b); }
    var pane = document.createElement('div');
    pane.className = 'facePane';
    pane.setAttribute('data-face', id);
    pane.setAttribute('data-axis', 'xface-' + id);
    pane.innerHTML = '<div class="twocol"><div class="col">' + (PA_XFACE_SKEL[id] || '') + '</div></div>';
    HOST.appendChild(pane);
    added.push(id);
  });
  paXFaceHooks.env = paLoadEnvFace;
  paXFaceHooks.lines = paLoadLinesFace;
  paXFaceHooks.resume = paLoadResumeFace;
  paXFaceHooks.receipt = function(){ paSlotLoad(); paLoadRcptFace(); };
  window.paXFaceInjected = added;
  /* ⭐ pm_裁_主面环≤5：环 ／ 更多 之实册（供报数 · ⛔ 手搓）＋ 兜底归位（#paMoreBody 若晚于本件） */
  function rehome(){
    var mh = paXMoreHost(); if(!mh) return 0;
    var n = 0;
    outIds.forEach(function(id){ var b = btns[id]; if(b && b.parentNode !== mh){ mh.appendChild(b); n++; } });
    return n;
  }
  window.paXFaceRing = PA_XFACE.filter(function(f){ return f[3] !== false; }).map(function(f){ return f[0]; });
  window.paXFaceMore = outIds.slice();
  window.paXFaceRehome = rehome;
  setTimeout(function(){ try{ rehome(); }catch(e){} }, 300);
  setTimeout(function(){ try{ rehome(); }catch(e){} }, 1500);
})();

/* —— 环境面 · 逐项行（形：name ／ state ／ kind·readable·scope ＋ src 逐字 ＋ 点开取原文）—— */
function paEnvItemRow(col, it){
  var id  = String((it && it.id) || '?');
  var nm  = (it && it.name != null && String(it.name).trim()) ? String(it.name) : id;
  var kind= (it && it.kind != null && String(it.kind).trim()) ? String(it.kind) : null;
  var rd  = (it && it.readable != null && String(it.readable).trim()) ? String(it.readable) : null;
  var sc  = (it && it.scope != null && String(it.scope).trim()) ? String(it.scope) : null;
  var st  = (it && it.state != null && String(it.state).trim()) ? String(it.state) : null;
  var src = (it && it.src != null && String(it.src).trim()) ? String(it.src) : null;
  var sha = (it && it.sha16 != null && String(it.sha16).trim()) ? String(it.sha16) : null;
  var ap  = (it && it.approved != null) ? String(it.approved) : null;
  var miss = [];
  if(kind === null) miss.push('kind');
  if(rd === null) miss.push('readable');
  if(sc === null) miss.push('scope');
  if(src === null) miss.push('src');
  if(sha === null) miss.push('sha16');
  if(st === null) miss.push('state');
  var tip = 'id：' + id + '\nkind：' + (kind || '缺（后端无 kind）') + '\nreadable：' + (rd || '缺（后端无 readable）')
    + '\nscope：' + (sc || '缺（后端无 scope）') + '\napproved：' + (ap || '缺（后端无 approved）')
    + '\nsrc 逐字：' + (src || '缺（后端无 src）') + '\nsha16：' + (sha || '缺（后端无 sha16）')
    + '\n面：GET /v9/pa/env · cols.' + col + '\n键缺：' + (miss.length ? miss.join(' ／ ') : '无');
  return '<div class="r" data-ecol="' + paEsc(col) + '" data-eid="' + paEsc(id) + '">'
    + '<span class="st" title="' + paEsc(tip) + '">' + paEsc(nm) + '</span>'
    + '<span class="v' + (st === null ? ' na' : '') + '" title="' + paEsc(tip) + '">' + paEsc(st === null ? '缺（后端无 state）' : st) + '</span>'
    + '<span class="s" title="' + paEsc(tip) + '">' + paEsc((kind || '缺 kind') + ' ／ ' + (rd || '缺 readable') + ' ／ ' + (sc || '缺 scope')) + ' ｜ '
    + '<a href="javascript:void(0)" onclick="paEnvItemSrc(this,\'' + paEsc(col) + '\',\'' + paEsc(id) + '\')" style="color:var(--blue)">'
    + paEsc(src || '缺（后端无 src）') + ' ⧉</a></span></div>';
}
/* 「点回真源」：内联揭示该项之后端原文（同源 ／ 只读 ／ ⛔ popup ⇒ ⛔ 拦截之静默；再点即收）。 */
async function paEnvItemSrc(a, col, id){
  var host = (a && a.closest) ? a.closest('.tstates') : null;
  if(!host) return;
  var key = String(col) + ':' + String(id);
  var old = host.querySelector('.envraw[data-for="' + key.replace(/"/g, '') + '"]');
  if(old){ if(old.parentNode) old.parentNode.removeChild(old); return; }
  var box = document.createElement('div');
  box.className = 'envraw';
  box.setAttribute('data-for', key);
  box.style.cssText = 'font-size:10px;color:var(--sub);white-space:pre-wrap;word-break:break-word;'
    + 'max-height:200px;overflow:auto;border-top:1px dashed var(--border);padding-top:3px';
  box.textContent = '取后端原文中…（GET /v9/pa/env）';
  host.appendChild(box);
  var j = await paGetJson(API + '/v9/pa/env');
  var arr = (j && j.cols && Array.isArray(j.cols[col])) ? j.cols[col] : null;
  var it = arr ? arr.filter(function(x){ return String(x && x.id) === String(id); })[0] : null;
  var t = new Date().toLocaleTimeString('zh-CN', {hour12:false});
  box.textContent = '面：GET /v9/pa/env · cols.' + col + ' · id=' + id + ' · 取刻 ' + t
    + ' · 只读 · ⛔ 密钥唯「有／无」\n' + (it ? JSON.stringify(it, null, 2) : '（后端无此项 · 如实记）');
}

/* —— 环境面（四栏）：取数 ＋ 渲染（唯后端 · 只读）—— */
async function paLoadEnvFace(){
  var at0 = new Date().toLocaleTimeString('zh-CN', {hour12:false});
  var j = await paGetJson(API + '/v9/pa/env');
  var top = document.getElementById('paEnvTop');
  var topSrc = document.getElementById('paEnvTopSrc');
  var jd = document.getElementById('paEnvJudge');
  var COLS = ['agents','kb','tools','resources'];
  if(topSrc) topSrc.textContent = '面：GET /v9/pa/env（只读四栏）· 后端自报刻 ' + ((j && j.at) ? String(j.at) : '未知') + ' · 前端取刻 ' + at0;
  if(!j){
    if(top) top.innerHTML = paRow('环境面', PA_GAP.down('GET /v9/pa/env 未应答'), '面：GET /v9/pa/env —— **不可达** ≠ **未接**', true);
    COLS.forEach(function(c){ paXUnreached('paEnvCol-' + c, c, 'GET /v9/pa/env'); });
    if(jd) jd.innerHTML = paRow('对表', PA_GAP.down('未应答 ⇒ ⛔ 判不齐'), '面：GET /v9/pa/env', true);
    return 0;
  }
  var counts = j.counts || null, cols = j.cols || null;
  var sg = j.secret_guard || null, sch = j.scheduler || null, srcs = j.sources || null;
  var bd = j.agents_breakdown || null;
  if(window.PA_STALE){ PA_STALE.mark(document.getElementById('paEnvTopSrc'), j.at ? j.at : null, '环境面（GET /v9/pa/env）'); PA_STALE.tick(); }
  var rows = [];
  rows.push(paRow('版', paEsc(String(j.env_version || '缺（后端无 env_version）')), '面：GET /v9/pa/env · 字段 env_version'));
  rows.push(paRow('刻', paEsc(String(j.at || '缺（后端无 at）')), '面：GET /v9/pa/env · 字段 at（后端自报 · ⛔ 前端 now 顶替 · 承 L76）'));
  rows.push(paRow('印（逐栏 sha16）', paEsc(JSON.stringify(j.sha16 || null)), '面：GET /v9/pa/env · 字段 sha16 —— 印须载器（承 PM 089 §二）'));
  rows.push(paRow('密钥守卫', (sg ? ('hits ' + (sg.hits == null ? '缺' : sg.hits) + ' ／ self_hit ' + (sg.self_hit == null ? '缺' : sg.self_hit)) : '缺（后端无 secret_guard）'),
    '面：GET /v9/pa/env · 字段 secret_guard —— ⭐ 密钥唯「有／无」：本面 ⛔ 显值 ／ ⛔ 显长度 ／ ⛔ 显尾号', !sg));
  rows.push(paRow('调度', (sch ? ('enabled=' + sch.enabled + ' ／ every_s ' + (sch.every_s == null ? '缺' : sch.every_s)) : '缺（后端无 scheduler）'),
    '面：GET /v9/pa/env · 字段 scheduler（' + ((sch && sch.note) ? String(sch.note) : '后端无 note') + '）', !sch));
  rows.push(paRow('scope 释义', paEsc(String(j.scope_legend || '缺（后端无 scope_legend）')), '面：GET /v9/pa/env · 字段 scope_legend'));
  if(srcs) COLS.forEach(function(c){
    rows.push(paRow('实源·' + c, paEsc(String(srcs[c] || ('缺（后端无 sources.' + c + '）'))), '面：GET /v9/pa/env · 字段 sources.' + c + '（逐字）'));
  });
  if(top) top.innerHTML = rows.join('');

  var jr = [], red = false;
  COLS.forEach(function(c){
    var decl = (counts && counts[c] != null) ? counts[c] : null;
    var arr = (cols && Array.isArray(cols[c])) ? cols[c] : null;
    var n = arr ? arr.length : null;
    var bad = (decl === null || n === null || decl !== n);
    if(bad) red = true;
    jr.push(paRow(c, (decl === null ? '缺' : decl) + ' ⟷ ' + (n === null ? '缺' : n) + (bad ? ' ✗' : ' ✓'),
      '面：GET /v9/pa/env · counts.' + c + ' ⟷ cols.' + c + '.length' + (bad ? ' ⇒ ⚠ 显红：⛔ 前端补齐（承 刀3′ §二）' : ''), bad));
  });
  if(bd){
    var seatN = (cols && Array.isArray(cols.agents)) ? cols.agents.filter(function(x){ return x && x.kind === 'seat'; }).length : null;
    var bdSeat = (bd['组织席位册'] == null) ? null : bd['组织席位册'];
    var badB = (seatN === null || bdSeat === null || seatN !== bdSeat);
    if(badB) red = true;
    jr.push(paRow('席位册 声明⟷实', (bdSeat === null ? '缺' : bdSeat) + ' ⟷ ' + (seatN === null ? '缺' : seatN) + (badB ? ' ✗' : ' ✓'),
      '面：agents_breakdown.组织席位册 ⟷ cols.agents(kind=seat).length', badB));
  } else {
    jr.push(paRow('席位册 声明⟷实', PA_GAP.fallback('agents_breakdown'), '面：GET /v9/pa/env · 字段 agents_breakdown', true));
  }
  var ro = await paGetJson(API + '/v9/pa/roster');
  var envAg = (cols && Array.isArray(cols.agents)) ? cols.agents : null;
  var roRows = (ro && Array.isArray(ro.rows)) ? ro.rows : null;
  if(envAg && roRows){
    var setEnv = envAg.filter(function(x){ return x && x.kind !== 'seat'; }).map(function(x){ return String(x.id); }).sort();
    var setRo  = roRows.map(function(x){ return String(x.id); }).sort();
    var eq = setEnv.join('|') === setRo.join('|');
    var onlyEnv = setEnv.filter(function(x){ return setRo.indexOf(x) < 0; });
    var onlyRo  = setRo.filter(function(x){ return setEnv.indexOf(x) < 0; });
    if(!eq) red = true;
    jr.push(paRow('agents 两源', setEnv.length + ' ⟷ ' + setRo.length + (eq ? ' ✓ 两集 ≡' : ' ✗ 两集 ⛔ 等'),
      '两集须 ≡ ∧ 两向皆报（承 pm_086）：env.cols.agents(kind≠seat) ⟷ GET /v9/pa/roster · '
      + '仅 env [' + (onlyEnv.join(' ／ ') || '无') + '] ／ 仅 roster [' + (onlyRo.join(' ／ ') || '无') + ']', !eq));
  } else if(roRows === null){
    jr.push(paRow('agents 两源', ro === null ? PA_GAP.down('GET /v9/pa/roster 未应答') : PA_GAP.fallback('rows'), '面：GET /v9/pa/roster', true));
  }
  if(bd) jr.push(paRow('两个 14 之分列', '组织席位册 ' + (bd['组织席位册'] == null ? '缺' : bd['组织席位册']) + ' ／ 能力端点册 ' + (bd['能力端点册'] == null ? '缺' : bd['能力端点册']),
    '承 刀8p §一：`GET /v9/pa/roster`（无 kind）所回者自题面名「' + String((ro && ro['面名']) || '缺') + '」；`GET /v9/pa/seats` 所回者 ＝ 组织席位册（kind=seat）⇒ 两名分列，⛔ 一词盖两义', !bd));
  jr.push(paRow('判', red ? '⚠ 显红（有栏不齐）' : '全齐 ✓', '本表之判据：⛔ 手搓 ／ ⛔ 补齐；不齐 ⇒ 显红', red));
  if(jd) jd.innerHTML = jr.join('');

  var CAP = 20;
  COLS.forEach(function(c){
    var host = document.getElementById('paEnvCol-' + c);
    var sEl  = document.getElementById('paEnvColSrc-' + c);
    var arr = (cols && Array.isArray(cols[c])) ? cols[c] : null;
    var decl = (counts && counts[c] != null) ? counts[c] : '缺';
    if(sEl) sEl.textContent = '面：GET /v9/pa/env · cols.' + c + ' · 数 ' + (arr ? arr.length : '缺')
      + '（counts.' + c + ' ＝ ' + decl + '）' + (srcs && srcs[c] ? (' · 实源 ' + String(srcs[c])) : '');
    if(!host) return;
    if(!arr){ paXMissing('paEnvCol-' + c, c, 'GET /v9/pa/env · 字段 cols.' + c + ' 不在', 'cols.' + c); return; }
    if(!arr.length){ host.innerHTML = paRow(c, '空（后端「cols.' + c + '」为 []）', '面：GET /v9/pa/env · **空 ≠ 缺**（承 pm_076 §一）', true); return; }
    var head = (c === 'tools' && arr.length > CAP)
      ? paRow('（显前 ' + CAP + ' ／ 共 ' + arr.length + '）', '⛔ 非全量',
          '本栏共 ' + arr.length + ' 件 ⇒ 显前 ' + CAP + ' 件（**面之数 ＝ counts.' + c + ' ＝ ' + decl + '** · ⛔ 以「显前之数」充总 · 承 刀12p §一.2 之同族病）')
      : '';
    host.innerHTML = head + arr.slice(0, (c === 'tools' ? CAP : arr.length)).map(function(it){ return paEnvItemRow(c, it); }).join('');
  });
  window.paEnvFace = {at: at0, at0: j.at, counts: counts, red: red, nAgents: (cols && cols.agents) ? cols.agents.length : null};
  return red ? -1 : 1;
}

/* —— 产品线面（源 GET /v9/pa/lines）—— */
async function paLoadLinesFace(){
  var at0 = new Date().toLocaleTimeString('zh-CN', {hour12:false});
  var j = await paGetJson(API + '/v9/pa/lines');
  var head = document.getElementById('paLinesHead');
  var sEl  = document.getElementById('paLinesSrc');
  var list = document.getElementById('paLinesList');
  if(sEl) sEl.textContent = '面：GET /v9/pa/lines · 后端自报刻 ' + ((j && j.at) ? String(j.at) : '未知') + ' · 前端取刻 ' + at0;
  if(!j){
    if(head) head.innerHTML = paRow('产品线', PA_GAP.down('未应答'), '面：GET /v9/pa/lines —— **不可达** ≠ **未接**', true);
    if(list) list.innerHTML = '';
    return 0;
  }
  var counts = j.counts || null;
  if(window.PA_STALE){ PA_STALE.mark(document.getElementById('paLinesSrc'), j.at ? j.at : null, '产品线面（GET /v9/pa/lines）'); PA_STALE.tick(); }
  if(head) head.innerHTML = [
    paRow('线数', paEsc(String(j.count == null ? '缺' : j.count)), '面：GET /v9/pa/lines · 字段 count'),
    paRow('未收口 ／ 已收口', paEsc((counts && counts['未收口'] != null ? counts['未收口'] : '缺') + ' ／ ' + (counts && counts['已收口'] != null ? counts['已收口'] : '缺')),
      '面：GET /v9/pa/lines · 字段 counts.未收口 ／ counts.已收口'),
    paRow('版 ／ 印', paEsc(String(j.version || '缺') + ' ／ ' + String(j['印'] || '缺')), '面：GET /v9/pa/lines · 字段 version ／ 印'),
    paRow('形（product_line）', paEsc((j.shape && Array.isArray(j.shape.product_line)) ? j.shape.product_line.join(' ／ ') : '缺（后端无 shape.product_line）'),
      '面：GET /v9/pa/lines · 字段 shape.product_line（后端自报之形 · ⛔ 前端自造形）'),
    paRow('源', paEsc(j.source ? (String(j.source['人手'] || '缺') + ' ＋ ' + String(j.source['派生'] || '缺')) : '缺（后端无 source）'), '面：GET /v9/pa/lines · 字段 source'),
    paRow('口径', paEsc(String(j.note || '缺（后端无 note）')), '面：GET /v9/pa/lines · 字段 note')
  ].join('');
  var lines = Array.isArray(j.lines) ? j.lines : null;
  if(!list) return 0;
  if(!lines){ list.innerHTML = '<div class="tstates">' + paRow('线', PA_GAP.fallback('lines'), '面：字段 lines', true) + '</div>'; return 0; }
  if(!lines.length){ list.innerHTML = '<div class="tstates">' + paRow('（无）', '空（后端 lines: []）', '面：字段 lines · **空 ≠ 缺**', true) + '</div>'; return 0; }
  list.innerHTML = lines.map(function(L){
    var nm   = String((L && L['线名']) || '缺（后端无线名）');
    var seat = String((L && L['席']) || '缺');
    var stt  = String((L && L['状态']) || '缺');
    var nxt  = String((L && L['下一拍']) || '缺');
    var nOpen= (L && L['未收口'] != null) ? L['未收口'] : null;
    var nCls = (L && L['已收口'] != null) ? L['已收口'] : null;
    var last = String((L && L['最近刻']) || '缺');
    var pieces = (L && Array.isArray(L['件集'])) ? L['件集'] : null;
    var body = [
      paRow('席', paEsc(seat), '面：GET /v9/pa/lines · 字段 席（受件之席 ＝ 线之执行面）'),
      paRow('状态', paEsc(stt), '面：字段 状态'),
      paRow('未收口 ／ 已收口', paEsc((nOpen == null ? '缺' : nOpen) + ' ／ ' + (nCls == null ? '缺' : nCls)), '面：字段 未收口 ／ 已收口'),
      paRow('最近刻', paEsc(last), '面：字段 最近刻（承 L76：刻须随值）'),
      paRow('下一拍', paEsc(nxt), '面：字段 下一拍 —— ⭐ 此即「PA 告诉我未完成之产品线」之唯一面'),
      paRow('源', paEsc(String((L && L['源']) || '缺')), '面：字段 源')
    ].join('');
    var ph = pieces ? pieces.map(function(p){
      return paRow('件 ' + String((p && p['件号']) || '?'), paEsc(String((p && p.stage) || '缺')),
        '件之刻 ' + paEsc(String((p && p['刻']) || '缺')) + ' · 催 ' + paEsc(String((p && p['催'] != null) ? p['催'] : '缺')) + ' · 面：字段 件集[]（每件自带件之刻 · 承 刀11p §零）');
    }).join('') : paRow('件集', '缺（后端无 件集）', '面：字段 件集', true);
    return '<details class="eng" data-line="' + paEsc(nm) + '"' + ((nOpen === null || nOpen > 0) ? ' open' : '') + '>'
      + '<summary>' + paEsc(nm + ' · 席 ' + seat + ' · ' + stt + ' · 未收口 ' + (nOpen == null ? '缺' : nOpen)) + '</summary>'
      + '<div class="engbody"><div class="tstates">' + body + '</div><div class="tstates">' + ph + '</div></div></details>';
  }).join('');
  window.paLinesFace = {at: at0, count: j.count, n: lines.length};
  return lines.length;
}

/* —— 开机面（源 GET /v9/pa/resume）—— */
function paXDelta(a, b){
  var ta = Date.parse(String(a || '').replace(' ', 'T')), tb = Date.parse(String(b || '').replace(' ', 'T'));
  if(isNaN(ta) || isNaN(tb)) return null;
  var s = Math.round((tb - ta) / 1000);
  if(s < 0) return null;
  var h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), ss = s % 60;
  return h + 'h' + m + 'm' + ss + 's';
}
async function paLoadResumeFace(){
  var at0 = new Date().toLocaleTimeString('zh-CN', {hour12:false});
  var j = await paGetJson(API + '/v9/pa/resume');
  var sEl = document.getElementById('paResumeSrc');
  if(sEl) sEl.textContent = '面：GET /v9/pa/resume · 后端自报刻 ' + ((j && j.at) ? String(j.at) : '未知') + ' · 前端取刻 ' + at0;
  if(!j){
    paXUnreached('paResumeHead', '开机面', 'GET /v9/pa/resume');
    paXUnreached('paResumeLeft', '上次断点', 'GET /v9/pa/resume');
    paXUnreached('paResumeRight', '未竟', 'GET /v9/pa/resume');
    return 0;
  }

  if(window.PA_STALE){ PA_STALE.mark(document.getElementById('paResumeSrc'), j.at ? j.at : null, '开机面（GET /v9/pa/resume）'); PA_STALE.tick(); }
  var head = document.getElementById('paResumeHead');
  var br = j['上次断点'] || null;
  var offline = br ? paXDelta(br.prev_boot_at, br.last_boot_at) : null;
  if(head) head.innerHTML = [
    paRow('版 ／ 器', paEsc(String(j.version || '缺') + ' ／ ' + String(j['器'] || '缺')), '面：GET /v9/pa/resume · 字段 version ／ 器（器 ＝ 本路由之码之 sha16）'),
    paRow('印', paEsc(String(j['印'] == null ? '缺' : j['印'])), '面：字段 印 ｜ 由：' + String(j['印之由'] || '缺')),
    paRow('面', 'GET /v9/pa/resume（只读）', '面：本路由自述')
  ].join('');
  var left = document.getElementById('paResumeLeft');
  var right = document.getElementById('paResumeRight');
  var L = [];
  L.push(paRow('上次断点·state', paEsc(br ? String(br.state || '缺') : '缺（后端无 上次断点）'), '面：字段 上次断点.state'));
  L.push(paRow('last_boot_at', paEsc(br ? String(br.last_boot_at || '缺') : '缺'), '面：字段 上次断点.last_boot_at（后端自报之刻）'));
  L.push(paRow('prev_boot_at', paEsc(br ? String(br.prev_boot_at || '缺') : '缺'), '面：字段 上次断点.prev_boot_at'));
  L.push(paRow('离线区间', offline ? (offline + '（面内派生：prev_boot_at ⇒ last_boot_at）') : '缺（两刻不可解 ⇒ ⛔ 编）',
    '面：由 上次断点.prev_boot_at ⇒ last_boot_at 面内相减（**派生之数 · 明标** · ⛔ 后端无此键）'));
  L.push(paRow('水印 sha16', paEsc(br ? String(br.sha16 || '缺') : '缺'), '面：字段 上次断点.sha16'));
  L.push(paRow('done.inbox ／ done.mail', paEsc(br ? (String((br.done || {}).inbox) + ' ／ ' + String((br.done || {}).mail)) : '缺'), '面：字段 上次断点.done（两路已完成之计数）'));
  L.push(paRow('攒件数', paEsc(String(j['攒件数'] == null ? '缺' : j['攒件数'])), '面：字段 攒件数 —— 出：' + String((j['数之出'] || {})['攒件数／续办数／失败件'] || '缺')));
  L.push(paRow('幂等跳过数', paEsc(String(j['幂等跳过数'] == null ? '缺' : j['幂等跳过数'])), '面：字段 幂等跳过数 —— 出：' + String((j['数之出'] || {})['幂等跳过数'] || '缺')));
  var fails = Array.isArray(j['失败件']) ? j['失败件'] : null;
  L.push(paRow('失败件', fails === null ? '缺（后端无 失败件）' : (fails.length ? (fails.length + ' 件') : '0 件（后端 []）'),
    '面：字段 失败件 · ' + (fails && fails.length ? JSON.stringify(fails).slice(0, 300) : '空 ≠ 缺'), fails === null));
  if(left) left.innerHTML = L.join('');

  var R = [];
  var wj = j['未竟'] || null;
  if(wj){
    Object.keys(wj).forEach(function(k){
      var arr = Array.isArray(wj[k]) ? wj[k] : null;
      R.push(paRow('未竟·' + k, arr ? (arr.length + ' 件') : '缺（形非表）',
        '面：字段 未竟.' + k + ' · ' + (arr && arr.length ? arr.map(function(x){ return String((x && (x.id || x.title)) || '?'); }).slice(0, 8).join(' ／ ') : '空'), !arr));
    });
  } else { R.push(paRow('未竟', PA_GAP.fallback('未竟'), '面：字段 未竟', true)); }
  var tb = j['只读对表'] || null;
  R.push(paRow('只读对表', tb ? (tb.same ? '两读同 ✓（diff 0）' : ('⚠ diff ' + (Array.isArray(tb.diff) ? tb.diff.length : '缺') + ' 处')) : '缺（后端无 只读对表）',
    '面：字段 只读对表 · ' + (tb ? String(tb.src || '') : ''), !tb));
  var sz = j['数之式'] || null;
  R.push(paRow('数之式·面', paEsc(sz ? String(sz['面'] || '缺') : '缺'), '面：字段 数之式.面'));
  R.push(paRow('数之式·滤', paEsc(sz ? String(sz['滤'] || '缺') : '缺'), '面：字段 数之式.滤'));
  R.push(paRow('数之式·式', paEsc(sz ? String(sz['式'] || '缺') : '缺'), '面：字段 数之式.式'));
  R.push(paRow('数之式·数', paEsc(sz ? String(sz['数'] || '缺') : '缺'), '面：字段 数之式.数 —— ⭐「所明之数」（承 刀13p §三：附面／滤／式／数）'));
  if(right) right.innerHTML = R.join('');
  window.paResumeFace = {at: at0, n未竟: wj ? Object.keys(wj).length : null, same: tb ? tb.same : null};
  return 1;
}

/* —— 收口面（源 GET ／ POST /v9/pa/dispatch/receipt）—— */
async function paLoadRcptFace(){
  var at0 = new Date().toLocaleTimeString('zh-CN', {hour12:false});
  var j = await paGetJson(API + '/v9/pa/dispatch/receipt');
  var bEl = document.getElementById('paRcptBoard');
  var sEl = document.getElementById('paRcptSrc');
  var lEl = document.getElementById('paRcptList');
  var lsEl= document.getElementById('paRcptListSrc');
  if(sEl) sEl.textContent = '面：GET /v9/pa/dispatch/receipt · 后端自报刻 ' + ((j && j.at) ? String(j.at) : '未知') + ' · 前端取刻 ' + at0;
  if(!j){
    paXUnreached('paRcptBoard', '收口面', 'GET /v9/pa/dispatch/receipt');
    if(lEl) lEl.innerHTML = '';
    return 0;
  }
  var byStage = j.by_stage || null, stages = Array.isArray(j.stages) ? j.stages : ['已派','已收','在做','已收口'];
  var cp = j.chase_policy || null;
  var b = [];
  stages.forEach(function(sg){
    b.push(paRow(sg, (byStage && byStage[sg] != null) ? (byStage[sg] + ' 件') : PA_GAP.fallback('by_stage.' + sg),
      '面：GET /v9/pa/dispatch/receipt · 字段 by_stage.' + sg, !(byStage && byStage[sg] != null)));
  });
  b.push(paRow('总件数 ／ 在册', paEsc(String(j.count == null ? '缺' : j.count) + ' ／ ' + String(j.registry_count == null ? '缺' : j.registry_count)),
    '面：字段 count ／ registry_count（store_exists＝' + String(j.store_exists) + '）'));
  b.push(paRow('催策', cp ? ('距末次刻 > ' + cp.after_min + ' min ⇒ 催 · 限 ' + cp.max + ' 次') : '缺（后端无 chase_policy）',
    '面：字段 chase_policy（' + (j.store ? ('store ' + String(j.store)) : '后端无 store') + '）', !cp));
  b.push(paRow('印 ／ 版', paEsc(String(j['印'] || '缺') + ' ／ ' + String(j.version || '缺')), '面：字段 印 ／ version'));
  b.push(paRow('四段之序', paEsc(stages.join(' ⇒ ')), '面：字段 stages —— 四段**只进不退**（承 刀4）'));
  if(bEl) bEl.innerHTML = b.join('');

  var states = Array.isArray(j.states) ? j.states : null;
  if(lsEl) lsEl.textContent = '面：GET /v9/pa/dispatch/receipt · 字段 states[] · 数 ' + (states ? states.length : '缺')
    + ' · 每件自带「件之刻」（stage_at ／ transitions[].at）';
  if(!lEl) return 0;
  if(!states){ lEl.innerHTML = '<div class="tstates">' + paRow('件', PA_GAP.fallback('states'), '面：字段 states', true) + '</div>'; return 0; }
  if(!states.length){ lEl.innerHTML = '<div class="tstates">' + paRow('（无）', '空（后端 states: []）', '面：字段 states · **空 ≠ 缺**', true) + '</div>'; return 0; }
  lEl.innerHTML = states.map(function(S){
    var tid = String((S && S.task_id) || '?');
    var seat = (S && S.to_seat != null && String(S.to_seat).trim()) ? String(S.to_seat) : null;
    var stage = String((S && S.stage) || '缺');
    var stageAt = (S && S.stage_at) ? String(S.stage_at) : null;
    var lastAt = (S && S.last_at) ? String(S.last_at) : null;
    var chase = (S && S.chase_count != null) ? S.chase_count : null;
    var tr = Array.isArray(S && S.transitions) ? S.transitions : [];
    var last = tr.length ? tr[tr.length - 1] : null;
    var guo = (last && last['果'] != null && String(last['果']).trim()) ? String(last['果']) : null;
    var yin = (last && last['印'] != null && String(last['印']).trim()) ? String(last['印']) : null;
    var inReg = (S && S.in_registry != null) ? String(S.in_registry) : '缺';
    var rows2 = [
      paRow('席', seat ? paEsc(seat) : '缺（后端无 to_seat ⇒ ⛔ 非席轴件）', '面：字段 states[].to_seat（空 ⇒ 池路件 · ⛔ 编「未派」）', !seat),
      paRow('段', paEsc(stage), '面：字段 states[].stage'),
      paRow('件之刻', paEsc(stageAt || '缺（后端无 stage_at）'), '面：字段 states[].stage_at —— ⭐ **每件自带件之刻**（⛔ 以「本轮」刻充件刻 · 承 刀11p §零）', !stageAt),
      paRow('末次刻', paEsc(lastAt || '缺'), '面：字段 states[].last_at'),
      paRow('果', guo ? paEsc(guo) : PA_GAP.fallback('果'), '面：字段 states[].transitions[].果', !guo),
      paRow('印', yin ? paEsc(yin) : PA_GAP.fallback('印'), '面：字段 states[].transitions[].印 —— 印须载器（承 PM 089 §二）', !yin),
      paRow('催数', chase == null ? '缺（后端无 chase_count）' : String(chase), '面：字段 states[].chase_count · 催策 after_min ' + (cp ? cp.after_min : '缺') + ' ／ max ' + (cp ? cp.max : '缺'), chase == null),
      paRow('在册', paEsc(inReg), '面：字段 states[].in_registry —— ⛔ 未在册者拒收口（承 刀4）')
    ].join('');
    var th = tr.length ? tr.map(function(T){
      return paRow('段 ' + String((T && T.stage) || '?'), paEsc(String((T && T.at) || '缺')),
        '果 ' + paEsc(String((T && T['果']) || '缺')) + ' · 印 ' + paEsc(String((T && T['印']) || '缺'))
        + ' · by ' + paEsc(String((T && T.by) || '缺')) + ' · 面：字段 transitions[]'
        + (T && T.note ? ('\n注：' + String(T.note)) : ''));
    }).join('') : paRow('段', '无（后端 transitions: [] ⇒ 已派 · 派时即已派）', '面：字段 transitions[]', true);
    return '<details class="eng" data-task="' + paEsc(tid) + '"' + (seat ? ' open' : '') + '>'
      + '<summary>' + paEsc(tid + ' · 席 ' + (seat || '（无）') + ' · ' + stage + ' · 件之刻 ' + (stageAt || '缺') + ' · 催 ' + (chase == null ? '缺' : chase)) + '</summary>'
      + '<div class="engbody"><div class="tstates">' + rows2 + '</div><div class="tstates">' + th + '</div></div></details>';
  }).join('');
  paInvFill();
  window.paRcptFace = {at: at0, count: j.count, states: states.length};
  return states.length;
}

/* —— 武装 · 调用（POST /v9/pa/agent/invoke · 三类执行器 seat ／ cli ／ api）——
   ⚠ 被调者之册由 `agent_id 空 ⇒ 回册` 取（可枚举 · ⛔ 手搓 · ⛔ 未在册者拒调）。 */
async function paInvFill(){
  var sel = document.getElementById('paInvSel'); if(!sel) return 0;
  var reg = null;
  try{
    var r = await fetch(API + '/v9/pa/agent/invoke', {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'});
    var d = await r.json().catch(function(){ return null; });
    reg = (d && d.out && Array.isArray(d.out.registry)) ? d.out.registry : null;
  }catch(e){ reg = null; }
  var sig = reg ? (reg.length + ':' + reg.map(function(x){ return String(x && x.id); }).join(',')) : 'nosrc';
  if(sel.dataset.sig !== sig){
    sel.innerHTML = '';
    if(!reg){
      var o = document.createElement('option'); o.value = ''; o.textContent = PA_GAP.down('册：POST /v9/pa/agent/invoke {} 未应答');
      sel.appendChild(o);
    } else {
      reg.forEach(function(x){
        var op = document.createElement('option');
        op.value = String((x && x.id) || '');
        op.textContent = String((x && x.id) || '?') + ' · ' + String((x && x.kind) || '缺') + ' · ' + String((x && x.name) || '');
        sel.appendChild(op);
      });
    }
    sel.dataset.sig = sig;
  }
  sel.title = '被调者之真源：POST /v9/pa/agent/invoke {}（agent_id 空 ⇒ 回册 · 可枚举）· 册之数 ' + (reg ? reg.length : '缺');
  return reg ? reg.length : 0;
}
async function paInvokeNow(){
  var sel = document.getElementById('paInvSel'), inp = document.getElementById('paInvTask'), out = document.getElementById('paInvOut');
  var id = sel ? String(sel.value || '').trim() : '';
  var task = inp ? String(inp.value || '').trim() : '';
  if(!id){ if(out) out.textContent = '调用：未选执行器 ⇒ 未提交（⛔ 静默兜底）· 真源 POST /v9/pa/agent/invoke {} 之 out.registry'; return; }
  if(out) out.textContent = '调用：提交中…（POST /v9/pa/agent/invoke · agent_id=' + id + ' · mode=auto）';
  try{
    var r = await fetch(API + '/v9/pa/agent/invoke', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({agent_id: id, task: task, mode:'auto'})});
    var d = await r.json().catch(function(){ return null; });
    if(out) out.textContent = '调用回执（HTTP ' + r.status + '）：' + (d
      ? JSON.stringify({ok: d.ok, agent_id: d.agent_id, via: d.via, ms: d.ms, '印': d['印'], error: d.error,
          out: (typeof d.out === 'string') ? d.out.slice(0, 320) : d.out}).slice(0, 800)
      : '⛔ 未取得回执');
  }catch(e){
    if(out) out.textContent = '调用：请求未送达（' + String((e && e.message) || e) + '）· ⛔ 不等于未执行';
  }
}

/* ===== T2-刀18p：Consumer 线之**一键出件槽位**（把「问老板一句」降为「请老板点一下」）=====
   形（承令）：① 对象（空 ⇒ 本人）② 旧事（一句话）③ 原信（件号 · 可空）④ 【出件】
   ⇒ 【出件】**⛔ 不直接发** ⇒ 落「待批」（**停手卡**）⇒ ⭐ **老板点一下即发**（(乙) 形：提醒 ＋ 转交 ＋ 人点）。
   ⛔ 我不代发 · ⛔ 我不代拍板（授权点须人点 · 承 pm_刀18p §一）。
   ⭐ 白名单（`PA_MAIL_ALLOW_TO`）：槽位**须显**「此对象不在白名单 ⇒ 须先准发」。真源（⛔ 前端造）：
     ⒈ `GET /v9/pa/deliver/authz` 之 `报给谁`（＝ 本人 ／ face.stop_to）—— **只读**读得（量：众数）；
     ⒉ `POST /v9/pa/deliver/mail` 响应之 `policy.allow_to`（＝ {本人} ∪ `PA_MAIL_ALLOW_TO` 之**全表**）—— 首次出件后得；
     ⒊ 二者皆无 ⇒ 显「未取得」（⛔ 造）。
   ⭐ 读数皆后端取（⛔ 手搓）：四件 ／ 件之刻 ／ $/件 ／ 报给谁 ／ 停在哪一步 —— 皆取回执与留痕。 */
var paSlotSt = { allow: null, allowSrc: null, who: null, whoSrc: null, whoN: 0, usage: null,
                 steps: 0, lastDoc: null, lastHttp: null, judge: null, at: null };
function paSlotQ(i){ try{ return document.getElementById(i); }catch(e){ return null; } }
function paSlotVal(i){ var e = paSlotQ(i); return e ? String(e.value == null ? '' : e.value).trim() : ''; }
function paSlotStep(n, why){
  if(typeof n === 'number' && n >= 0) paSlotSt.steps = n;
  var e = paSlotQ('paSlotSteps');
  if(e) e.textContent = paSlotSt.steps + '\uff0f2' + (paSlotSt.steps > 2 ? ' \u26a0 \u8d85' : '');
  var s = paSlotQ('paSlotJudge');
  if(s) paSlotJudgeRender();
  return paSlotSt.steps;
}
function paSlotBump(why){ return paSlotStep(paSlotSt.steps + 1, why); }

/* —— 白名单之读（**只读** · ⛔ 造）：源 ＝ `GET /v9/pa/deliver/authz` 之 `报给谁` —— */
/* —— ⭐ 用途（探针 ⇒ ⛔ 业务 · 承 PM 刀20 §二 ／ 刀25 §二「**以果判**」）——
   ⭐ 真源（**单源** · **⛔ 前端自持**）＝ `GET /v9/pa/deliver/authz?usage=all` 之
   `用途之数 { 业务 ／ 全量 ／ 探针 }` ／ `用途之判据`（后端逐字）／ `rows[].用途`（后端读时标）。
   ⚠ 我 `1162` 自速：前端旧持一份判据词表（「以名判」）⇒ 后端 `刀25` 改「以果判」后 ⇒ 前端之映
     ⛔ 齐（旧映 业务 0 ／ 探针 25 ⟷ 后端 业务 2 ／ 探针 23）⇒ 承 `pm_1067 §五.③`
     「前端 ⛔ 自持一份 ⇒ 两表必漂」之族 ⇒ **词表已删**（⛔ 再自判）。
   ⭐ 校验 ⇒ 唯**后端自洽之复核**（⛔ 前端映）：`业务 ＋ 探针 ＝ 全量` ∧ `rows 皆带 用途` ∧ `用途 ∈ {业务, 探针}`。
   ⭐ 枚举值（逐字 · 承 PM `1155` §四「⛔ 使人猜」）：⭐ **取后端 `usage_认`**（⛔ 前端硬编）。
     ⚠ 我 `1155` §四所述「⛔ 英文 `probe`」**已过期**（TD `刀21 §三` 落 `USAGE_ALIASES`）⇒ 我本刻实测：
       `usage=probe ⇒ 23 行` ／ `usage=business ⇒ 2 行`（⛔ 安静假空）。 */
async function paSlotLearn(){
  var j = await paGetJson(API + '/v9/pa/deliver/authz?limit=50&usage=all');
  var rows = (j && Array.isArray(j.rows)) ? j.rows : null;
  if(!rows){ paSlotSt.whoSrc = '未取得（GET /v9/pa/deliver/authz 未应答）'; return null; }
  /* ⭐ 单源 ＝ 后端（`用途之数` ＋ `rows[].用途`）；⛔ 前端判据（已删 · 承 pm_1067 §五.③ 之族）。 */
  var bk = (j && j['用途之数']) || null;
  var nAll = rows.length;
  var keyed = rows.filter(function(r){ return r && r['用途'] != null; });
  var nBiz = keyed.filter(function(r){ return String(r['用途']) === '业务'; }).length;
  var nProbe = keyed.filter(function(r){ return String(r['用途']) === '探针'; }).length;
  var nOther = keyed.length - nBiz - nProbe;
  var sB = (bk && typeof bk['业务'] === 'number') ? bk['业务'] : nBiz;
  var sP = (bk && typeof bk['探针'] === 'number') ? bk['探针'] : nProbe;
  var sA = (bk && typeof bk['全量'] === 'number') ? bk['全量'] : nAll;
  var bad = (keyed.length !== nAll) || (nBiz + nProbe !== nAll) || (nOther !== 0)
            || (bk ? (sB !== nBiz || sP !== nProbe || sA !== nAll) : false);
  paSlotSt.usage = {
    biz: sB, probe: sP, all: sA, keyed: keyed.length, other: nOther, bad: bad,
    /* ⭐ 枚举（后端 `usage_认` 逐字 ⇒ ⛔ 前端硬编 · 承 PM `1155` §四 ／ 我 `1162` §三.3 之照实） */
    认: (j && Array.isArray(j['usage_认']) && j['usage_认'].length) ? j['usage_认'].slice() : null,
    src: bk ? 'GET /v9/pa/deliver/authz?usage=all 之 `用途之数`（后端真源 · ⛔ 前端自持判据）'
            : '⚠ 响应无 `用途之数`（后端未载 `刀20 §二`）⇒ 唯以 `rows[].用途` 自数',
    judge: (j && j['用途之判据']) ? String(j['用途之判据']) : null,
    key: (keyed.length === nAll) ? ('rows[].用途（后端读时标 · 全 ' + nAll + ' 行皆带）')
                                 : ('⚠ 唯 ' + keyed.length + ' ／ ' + nAll + ' 行带 `用途`') };
  paSlotSt.usageMap = {};
  keyed.forEach(function(r){
    var t = String((r && (r['件号'] || r['task_id'])) || '');
    if(t) paSlotSt.usageMap[t] = String(r['用途']);
  });
  var use = nBiz ? rows.filter(function(r){ return String(r['用途']) === '业务'; }) : rows;
  var cnt = {};
  use.forEach(function(r){
    var w = (r && r['报给谁'] != null) ? String(r['报给谁']).trim() : '';
    if(w) cnt[w] = (cnt[w] || 0) + 1;
  });
  paSlotSt.whoN = nAll;
  var ks = Object.keys(cnt).sort(function(a, b){ return cnt[b] - cnt[a]; });
  paSlotSt.who = ks.length ? ks[0] : null;
  paSlotSt.whoSrc = 'GET /v9/pa/deliver/authz?usage=all · rows ' + nAll
    + '（业务 ' + sB + ' ／ 探针 ' + sP + ' · ' + (bk ? '后端 `用途之数`' : '⚠ 后端未给 `用途之数`') + '）'
    + (ks.length ? (' · 报给谁 众数（' + cnt[ks[0]] + ' 行 · ' + (nBiz ? '取业务行' : '⚠ 无业务行 ⇒ 取全量') + '）') : ' · 无「报给谁」值');
  return paSlotSt.who;
}
/* —— 判「此对象是否在白名单」（⛔ 前端造 · 无据即「未取得」）—— */
function paSlotVerdict(obj){
  var o = String(obj == null ? '' : obj).trim();
  var allow = paSlotSt.allow;
  if(allow && allow.length){
    var inA = allow.indexOf(o) >= 0 || (!o && allow.indexOf(paSlotSt.who) >= 0);
    return { ok: inA, known: true, table: allow,
      txt: inA ? ('\u2705 \u5728\u5141\u8bb8\u8868\u5185\uff08\u6e90\uff1aPOST /v9/pa/deliver/mail \u54cd\u5e94 policy.allow_to \u00b7 ' + allow.length + ' \u6761\uff09')
               : ('\u26d4 \u6b64\u5bf9\u8c61\u4e0d\u5728\u5141\u8bb8\u8868 \u21d2 \u987b\u5148\u51c6\u53d1\uff08\u589e `PA_MAIL_ALLOW_TO` \u00b7 \u2b50 \u8be5\u589e\u4ea6\u987b\u8001\u677f\u70b9\uff09') };
  }
  if(!o){
    return { ok: !!paSlotSt.who, known: !!paSlotSt.who, table: null,
      txt: '\u5bf9\u8c61\u7a7a \u21d2 \u89e3\u300c\u672c\u4eba\u300d' + (paSlotSt.who
        ? (' = ' + paSlotSt.who + '\uff08\u6e90 deliver/authz \u00b7 \u62a5\u7ed9\u8c01\uff09')
        : ' \u00b7 \u26a0 \u672c\u4eba\u672a\u53d6\u5f97\uff08\u6e90 deliver/authz \u672a\u5e94\u7b54\uff09\u21d2 \u26d4 \u524d\u7aef\u9020') };
  }
  if(paSlotSt.who){
    if(o === paSlotSt.who) return { ok: true, known: true, table: null,
      txt: '\u2705 \uff1d \u672c\u4eba\uff08\u6e90 deliver/authz \u00b7 \u62a5\u7ed9\u8c01\uff09\u00b7 \u5728\u518c' };
    return { ok: false, known: false, table: null,
      txt: '\u26a0 \u6b64\u5bf9\u8c61 \u26d4 \u5df2\u77e5\u4e4b\u672c\u4eba\uff08' + paSlotSt.who + '\uff09\u21d2 **\u53ef\u80fd\u4e0d\u5728\u767d\u540d\u5355** \u21d2 '
         + '\u987b\u5148\u51c6\u53d1\uff08\u589e `PA_MAIL_ALLOW_TO` \u00b7 \u2b50 \u8be5\u589e\u4ea6\u987b\u8001\u677f\u70b9\uff09\u00b7 '
         + '\u5141\u8bb8\u8868\u5168\u91cf **\u672a\u53d6\u5f97**\uff08\u540e\u7aef\u552f\u4e8e deliver/mail \u54cd\u5e94\u4e4b policy.allow_to \u7ed9\u4e4b \u00b7 \u26d4 \u524d\u7aef\u9020\uff09' };
  }
  return { ok: false, known: false, table: null,
    txt: '\u5141\u8bb8\u8868 **\u672a\u53d6\u5f97**\uff08\u6e90\u7f3a\uff1adeliver/authz \u672a\u5e94\u7b54 \u2227 \u5c1a\u65e0 deliver/mail \u54cd\u5e94 \u00b7 \u26d4 \u524d\u7aef\u9020\uff09' };
}
function paSlotJudgeRender(){
  var host = paSlotQ('paSlotJudge'); if(!host) return 0;
  var to = paSlotVal('paSlotTo');
  var ask = paSlotVal('paSlotAsk'), ref = paSlotVal('paSlotRef');
  var v = paSlotVerdict(to);
  var R = [];
  R.push(paRow('\u2460 \u5bf9\u8c61', to ? paEsc(to) : ('\u7a7a \u21d2 \u672c\u4eba' + (paSlotSt.who ? ('\uff08' + paEsc(paSlotSt.who) + '\uff09') : '\uff08\u672c\u4eba\u672a\u53d6\u5f97\uff09')),
    '\u69fd\u4f4d\u2460\uff1a\u6536\u4ef6\u4eba\uff08\u7a7a \u21d2 \u672c\u4eba \u00b7 \u672c\u4eba\u4e4b\u771f\u6e90 \uff1d deliver/authz \u4e4b \u300c\u62a5\u7ed9\u8c01\u300d\uff09', !to && !paSlotSt.who));
  R.push(paRow('\u767d\u540d\u5355\u5224', paEsc(v.txt), '\u5224\u636e\uff1aallow_to\uff08\uff1d {\u672c\u4eba} \u222a PA_MAIL_ALLOW_TO\uff09\u00b7 \u26d4 \u524d\u7aef\u9020 \u00b7 \u627f pm_\u520018p \u00a7\u4e00', !v.known));
  R.push(paRow('\u5141\u8bb8\u8868', paSlotSt.allow ? paEsc(paSlotSt.allow.join(' \uff0f ')) : '\u672a\u53d6\u5f97\uff08\u540e\u7aef\u552f\u4e8e deliver/mail \u54cd\u5e94\u4e4b policy.allow_to \u7ed9\u4e4b \u00b7 \u26d4 \u524d\u7aef\u9020\uff09',
    '\u6e90\uff1a' + paEsc(paSlotSt.allowSrc || '\u7f3a\uff08\u5c1a\u65e0 deliver/mail \u54cd\u5e94\uff09'), !paSlotSt.allow));
  R.push(paRow('\u672c\u4eba\uff08\u62a5\u7ed9\u8c01\uff09', paSlotSt.who ? paEsc(paSlotSt.who) : '\u672a\u53d6\u5f97',
    '\u6e90\uff1a' + paEsc(paSlotSt.whoSrc || '\u7f3a') + ' \u00b7 rows ' + paSlotSt.whoN, !paSlotSt.who));
  var U = paSlotSt.usage;
  R.push(paRow('用途（探针 ⇒ ⛔ 业务）', U ? ('业务 ' + U.biz + ' 行 ／ 探针 ' + U.probe + ' 行（全 ' + U.all + ' 行）') : '未取得',
    (U ? ('真源：' + U.src + (U.key ? (' ／ ' + U.key) : '')) : '源缺')
    + (U ? (' · 自洽复核（⛔ 前端映）：业务 ＋ 探针 ＝ ' + (U.biz + U.probe) + ' ／ 全 ' + U.all
            + ' ∧ 带 `用途` ' + U.keyed + ' 行 ∧ 他值 ' + U.other + ' ⇒ ' + (U.bad ? '⚠ **后端 ⛔ 自洽**（显红）' : '≡')) : '')
    + (U && U.judge ? (' · 判据（后端逐字）：' + paEsc(U.judge)) : '')
    + (U ? (' · 枚举值（后端 `usage_认` 逐字 · ⛔ 前端硬编）：' + (U.认 ? U.认.join(' ／ ') : '⚠ 后端未给 `usage_认`')) : '')
    , !U || (U ? U.bad : false)));
  R.push(paRow('\u4eba\u5de5\u6b65\u6570', paSlotSt.steps + '\uff0f2' + (paSlotSt.steps > 2 ? ' \u26a0 \u8d85' : ''),
    '\u5224\u636e\uff08\u627f pm_\u520018p \u00a7\u4e09 \uff0f \u520015p-\u8865 \u00a7\u4e00.1\uff09\uff1a\u586b\u4e24\u7a7a \u21d2 \u3010\u51fa\u4ef6\u3011 1 \u6b65 \uff0b \u5361\u4e0a\u70b9 1 \u6b65 \u21d2 \u2264 2\uff08\u26d4 \u63a8\u7b97\uff09', paSlotSt.steps > 2));
  R.push(paRow('\u672b\u6b21\u51fa\u4ef6', paSlotSt.lastHttp == null ? '\u672c\u8f6e\u5c1a\u672a\u51fa\u4ef6' : ('HTTP ' + paSlotSt.lastHttp),
    '\u6e90\uff1aPOST /v9/pa/deliver/mail\uff08\u672c\u9762\u6240\u9a71 \u00b7 \u672a\u51fa \u21d2 \u65e0\u8bfb\u6570\uff09', paSlotSt.lastHttp == null));
  R.push(paRow('\u63a7\u4ef6', (ask ? ('\u2461 \u65e7\u4e8b ' + (ask.length > 24 ? (ask.slice(0, 24) + '\u2026') : ask)) : '\u2461 \u65e7\u4e8b \u7a7a \u21d2 \u26d4 \u672a\u63d0\u4ea4')
    + ' \u00b7 ' + (ref ? ('\u2462 \u539f\u4fe1 ' + ref) : '\u2462 \u539f\u4fe1 \u672a\u586b\uff08\uff1d\u540e\u7aef\u56de\u6267\u663e\u300c\u7f3a\u300d\u00b7 \u26d4 \u88c5\u5df2\u9644\uff09'),
    '\u69fd\u4f4d\u2461 \u65e7\u4e8b\uff08\u4e00\u53e5\u8bdd\uff09\uff0f \u69fd\u4f4d\u2462 \u539f\u4fe1\uff08\u4ef6\u53f7 \u00b7 \u53ef\u7a7a\uff09', !ask));
  host.innerHTML = R.join('');
  paSlotSt.judge = v; paSlotSt.at = new Date().toLocaleString('zh-CN', {hour12:false});
  var s = paSlotQ('paSlotSrc');
  if(s) s.textContent = '\u9762\uff1a\u672c\u9762\u4e3a\u8bfb\u6570\uff08deliver/authz \u53ea\u8bfb\uff09\uff0b\u5f00\u5361\uff1b\u53d1\u4fe1\u552f\u7ecf POST /v9/pa/deliver/mail \u00b7 \u672c\u9762\u53d6\u523b ' + paSlotSt.at
    + ' \u00b7 \u5361 \uff1d \u505c\u624b\u5361\uff08\u5f85\u6279\uff09\uff1a\u672c\u9762 \u26d4 \u4ee3\u53d1 \u00b7 \u26d4 \u4ee3\u62cd\u677f';
  return R.length;
}
/* —— task_id 之公器（T1 面之 paT1 · ⛔ 本面重造散列）—— */
function paSlotTaskId(task, toArr, body){
  try{
    if(window.paT1 && typeof window.paT1.taskIdOf === 'function') return window.paT1.taskIdOf(task, toArr, body);
  }catch(e){}
  return null;   /* \u26d4 \u524d\u7aef\u9020\u53f7 \u2014\u2014 \u516c\u5668\u672a\u5c31\u7eea \u21d2 \u7167\u5b9e null\uff08\u540e\u7aef\u5fc5\u62d2 \u00b7 fail-closed\uff09 */
}
async function paSlotLatestDecision(){
  try{
    var d = await paGetJson(API + '/v9/pa/decision/log');
    var rows = ((d && d.decisions) || []).filter(function(x){ return x && x.decision === '\u91c7\u7eb3' && x.id; });
    return rows.length ? String(rows[rows.length - 1].id) : null;
  }catch(e){ return null; }
}
/* —— ④ 【出件】：**唯落「待批」** ⇒ 开停手卡（⛔ 不直发）—— */
function paSlotOut(){
  var out = paSlotQ('paSlotOut');
  var ask = paSlotVal('paSlotAsk');
  var ref = paSlotVal('paSlotRef');
  var to  = paSlotVal('paSlotTo');
  if(!ask){ if(out) out.textContent = '\u51fa\u4ef6\uff1a\u26d4 \u2461 \u65e7\u4e8b\u4e3a\u7a7a \u21d2 \u672a\u63d0\u4ea4\uff08\u26d4 \u5f00\u7a7a\u4ef6\uff09'; return; }
  var toList = to ? to.split(/[;,\s]+/).filter(function(x){ return !!x; }) : [];
  if(!toList.length){
    if(paSlotSt.who) toList = [paSlotSt.who];
    else { if(out) out.textContent = '\u51fa\u4ef6\uff1a\u26d4 \u2460 \u5bf9\u8c61\u7a7a \u2227 \u672c\u4eba\u672a\u53d6\u5f97\uff08\u6e90 deliver/authz \u4e4b \u62a5\u7ed9\u8c01\uff09\u21d2 \u8bf7\u586b\u5bf9\u8c61\uff08\u26d4 \u524d\u7aef\u9020\u300c\u672c\u4eba\u300d\uff09'; return; }
  }
  var subject = '\u3010PA \u00b7 \u4e00\u952e\u51fa\u4ef6\u3011' + ask.slice(0, 40);
  var b = { to: toList, subject: subject, body_md: ask, refNo: ref };
  var tid = paSlotTaskId(ask, toList, ask);
  paSlotStep(1, '\u4ea4\u529e\uff08\u4e00\u952e\u51fa\u4ef6\uff09');
  paSlotOpenCard(tid, b);
}
async function paSlotOpenCard(tid, b){
  var out = paSlotQ('paSlotOut');
  var ask = (typeof window.paStopAsk === 'function') ? window.paStopAsk : null;
  if(!ask){ if(out) out.textContent = '\u51fa\u4ef6\uff1a\u26d4 \u505c\u624b\u5361\u4e0d\u53ef\u7528\uff08paStopAsk \u672a\u5c31\u7eea\uff09\u21d2 \u672a\u53d1\uff08fail-closed\uff09'; return; }
  var v = paSlotVerdict(b.to[0]);
  var dec = await paSlotLatestDecision();
  ask({
    title: '\u26d4 \u5f85\u6279\uff1a\u5373\u5c06\u4ee5\u4f60\u540d\u4e49\u53d1\u51fa\u4e00\u5c01\uff08\u4e00\u952e\u51fa\u4ef6 \u00b7 Consumer \u7ebf\uff09',
    rows: [
      ['\u2460 \u5bf9\u8c61', b.to.join(', ') + (paSlotVal('paSlotTo') ? '' : '\uff08\u7a7a \u21d2 \u672c\u4eba\uff09')],
      ['\u2461 \u65e7\u4e8b', b.body_md],
      ['\u2462 \u539f\u4fe1', b.refNo || '\u672a\u586b\uff08\u21d2 \u540e\u7aef\u56de\u6267\u663e\u300c\u7f3a\u300d\u00b7 \u26d4 \u88c5\u5df2\u9644\uff09'],
      ['\u767d\u540d\u5355\u5224', v.txt],
      ['\u901a\u9053', 'POST /v9/pa/deliver/mail\uff08\u6211\u65b9\u95ed\u73af \u00b7 \u540e\u7aef\u771f\u95f8\uff09'],
      ['\u6388\u6743', dec ? ('\u540e\u7aef decision/log \u6700\u65b0\u300c\u91c7\u7eb3\u300d' + dec + '\uff08\u26d4 \u672c\u9762\u7f16\u53f7\uff09\u00b7 \u2b50 \u4ee5\u4f60\u540d\u4e49\u4e4b\u90a3\u4e00\u4e0b \uff1d \u672c\u5361\u70b9\u4e00\u4e0b\uff08\u4eba\u70b9\uff09')
              : '\u540e\u7aef decision/log \u65e0\u300c\u91c7\u7eb3\u300d\u21d2 \u51fa\u4ef6\u5fc5 403\uff08fail-closed \u00b7 \u627f pm_072 \u00a7\u56db\uff09'],
      ['\u62a5\u7ed9\u8c01', (paSlotSt.who || '\u672a\u53d6\u5f97') + '\uff08\u6e90 deliver/authz \u00b7 \u62a5\u7ed9\u8c01\uff09'],
      ['\u53ef\u64a4\u9500\u6027', '\u672a\u70b9\u5373\u672a\u52a8 \u2014\u2014 \u6b64\u523b\u540e\u6094 \uff1d \u4ec0\u4e48\u90fd\u4e0d\u53d1\u751f'],
      ['\u5f31\u4fdd\u8bc1', '\u672a\u70b9 \u21d2 \u524d\u7aef\u4e0d\u53d1\uff08\u524d\u7aef\u4e4b\u5f31\u4fdd\u8bc1\uff09\u21d4 \u540e\u7aef\u62d2\u6267\uff08\u771f\u95f8\uff09'],
      ['\u4eba\u5de5\u6b65\u6570', paSlotSt.steps + '\uff0f2\uff08\u70b9\u672c\u5361 \u21d2 ' + (paSlotSt.steps + 1) + '\uff09'],
      ['task_id', tid || '\u26d4 \u672a\u53d6\u5f97\uff08\u516c\u5668 paT1 \u672a\u5c31\u7eea\uff09\u21d2 \u540e\u7aef\u5fc5 400'],
      ['\u523b', new Date().toLocaleString('zh-CN', {hour12:false})]
    ],
    okLabel: '\u2705 \u51c6\u53d1\uff08\u672c\u6b21\u53d1\u9001\uff09',
    cancelLabel: '\u274c \u4e0d\u51fa',
    persistMsg: false,
    onOk: function(){ paSlotBump('\u6388\u6743\uff08\u505c\u624b\u5361\uff09'); paSlotSend(tid, b); },
    onCancel: function(){
      if(out) out.textContent = '\u51fa\u4ef6\uff1a\u5df2\u64a4\uff08\u672a\u70b9\u5373\u672a\u52a8 \u00b7 \u26d4 \u672a\u53d1\uff09\u00b7 \u4eba\u5de5\u6b65\u6570 ' + paSlotSt.steps + '\uff0f2';
    }
  });
}
async function paSlotSend(tid, b){
  var out = paSlotQ('paSlotOut');
  if(!tid){ if(out) out.textContent = '\u51fa\u4ef6\uff1a\u26d4 task_id \u672a\u53d6\u5f97 \u21d2 \u672a\u63d0\u4ea4\uff08\u26d4 \u524d\u7aef\u9020\u53f7 \u00b7 fail-closed\uff09'; return; }
  var dec = await paSlotLatestDecision();
  if(out) out.textContent = '\u51fa\u4ef6\uff1a\u63d0\u4ea4\u4e2d\u2026\uff08POST /v9/pa/deliver/mail\uff09\u00b7 task_id ' + tid;
  var payload = { user_id: (typeof curUser === 'function') ? String(curUser()) : 'default',
                  task_id: tid, decision_id: dec || '', to: b.to, subject: b.subject, body_md: b.body_md };
  if(b.refNo) payload.in_reply_to = { '\u4ef6\u53f7': b.refNo, 'sha16': '' };
  try{
    var r = await fetch(API + '/v9/pa/deliver/mail', { method:'POST', cache:'no-store',
      headers:{ 'Content-Type':'application/json' }, body: JSON.stringify(payload) });
    paSlotSt.lastHttp = r.status;
    var d = await r.json().catch(function(){ return null; });
    paSlotSt.lastDoc = d;
    await paSlotLearn();   /* ⭐ 出件后重取（用途之映须新鲜 · ⛔ 以旧映自判） */
    paSlotRenderReceipt(r.status, d, tid);
    paSlotJudgeRender();
  }catch(e){
    paSlotSt.lastHttp = 0; paSlotSt.lastDoc = null;
    if(out) out.textContent = '\u51fa\u4ef6\uff1a\u8bf7\u6c42\u672a\u9001\u8fbe\uff08' + String((e && e.message) || e) + '\uff09\u00b7 \u26d4 \u4e0d\u7b49\u4e8e\u672a\u53d1';
    paSlotJudgeRender();
  }
}
/* —— 回执上屏（四件 ／ 件之刻 ／ $/件 ／ 报给谁 —— 皆后端取 · ⛔ 手搓）—— */
function paSlotRenderReceipt(http, d, tid){
  var out = paSlotQ('paSlotOut'); if(!out) return 0;
  var pol = (d && d.policy) || null;
  if(pol && Array.isArray(pol.allow_to)){
    paSlotSt.allow = pol.allow_to.slice();
    paSlotSt.allowSrc = 'POST /v9/pa/deliver/mail \u54cd\u5e94 policy.allow_to\uff08\u91cf ' + paSlotSt.allow.length + '\uff09';
  }
  var rc = (d && (d.receipt || d.receipt_four)) || null;
  var cst = (rc && rc['\u6210\u672c']) || null;
  var sp  = (rc && rc['\u82b1\u4e86\u591a\u5c11']) || null;
  var wh  = (rc && rc['\u8c01\u6279\u7684']) || null;
  var L = [];
  var bkU = (paSlotSt.usageMap && paSlotSt.usageMap[tid]) || null;   /* 后端 rows[].用途；⛔ 在册 ⇒ 未知 */
  if(rc && bkU === '探针') L.push('<b style="color:var(--amber)">⚠ 探针（⛔ 业务样本）</b>：后端 rows[].用途 ＝ ' + paEsc(bkU) + ' · 承 PM 刀20 §二');
  if(rc && !bkU) L.push('<span style="color:var(--sub)">用途：未知（本件未在本轮读取之列 ⇒ ⛔ 前端自判 · 承 pm_1067 §五.③）</span>');
  if(rc && !(d && d.ok === false)){
    L.push('<b>\u56de\u6267\uff08\u540e\u7aef \u00b7 HTTP ' + paEsc(String(http)) + '\uff09</b>');
    var hl = rc['\u4eba\u8bdd'];
    if(Object.prototype.toString.call(hl) === '[object Array]'){
      hl.forEach(function(s){ L.push('\u00b7 ' + paEsc(String(s).replace(/^[\s\u00b7\u2022]+/, ''))); });
    }
    L.push('<b>\u4ef6\u4e4b\u523b</b>\uff1a' + paEsc(rc['\u523b'] != null ? String(rc['\u523b']) : '\u7f3a\uff08\u540e\u7aef\u56de\u6267\u672a\u7ed9\u300c\u523b\u300d\uff09'));
    L.push('<b>\u82b1\u4e86\u591a\u5c11\uff08\u771f\u8bfb\u6570\uff09</b>\uff1a' + paEsc(sp
      ? ('wall_s ' + sp['wall_s'] + ' \u00b7 \u5165 ' + ((sp['bytes'] || {})['in']) + ' B \uff0f \u51fa ' + ((sp['bytes'] || {})['out'])
         + ' B \u00b7 ' + sp['money'] + ' ' + (sp['currency'] || '') + (sp['\u8bfb\u6570\u4e4b\u5668'] ? (' \u00b7 \u5668 ' + sp['\u8bfb\u6570\u4e4b\u5668']) : ''))
      : '\u672a\u53d6\u5f97\uff08\u540e\u7aef\u672a\u7ed9\u300c\u82b1\u4e86\u591a\u5c11\u300d\uff09'));
    L.push('<b>$/\u4ef6</b>\uff1a' + paEsc(cst
      ? ('\u5355\u4ef7 ' + cst['\u5355\u4ef7_\u5143\u6bcf\u4ef6'] + ' ' + (cst['\u5e01'] || '') + ' \uff0f \u4ef6 \u00b7 \u603b ' + cst['\u603b\u82b1\u8d39_\u5143']
         + ' \u00b7 \u4ef6\u6570 ' + cst['\u4ef6\u6570'] + '\uff08\u53e3\u5f84 ' + (cst['\u53e3\u5f84'] || '\u2014') + '\uff09')
      : '\u672a\u53d6\u5f97\uff08\u540e\u7aef\u672a\u7ed9\u300c\u6210\u672c\u300d\uff09'));
    L.push('<b>\u8c01\u6279\u7684</b>\uff1a' + paEsc(wh
      ? ((wh['\u4eba'] || '\u2014') + ' \u00b7 ' + (wh['decision_id'] || '\u2014') + ' \u00b7 ' + (wh['decision'] || '\u2014')
         + ' \u00b7 ts ' + (wh['ts'] == null ? '\u7f3a' : wh['ts']))
      : '\u672a\u53d6\u5f97'));
    L.push('<span style="color:var(--sub)">task_id ' + paEsc(String(tid || '\u2014'))
      + ' \u00b7 \u771f\u6e90 POST /v9/pa/deliver/mail \u56de\u6267\uff08\u56db\u4ef6 \uff0b \u5f15\u54ea\u5c01\u6765\u4fe1 \uff0b \u4ef6\u4e4b\u523b \uff0b $/\u4ef6 \u7686\u540e\u7aef\u53d6\uff09'
      + ((d && d['\u5370']) ? (' \u00b7 \u5370 ' + paEsc(d['\u5370'])) : '') + '</span>');
  } else {
    var blocked = (d && d.blocked_by) || '';
    var stage = (rc && rc['\u505c\u5728\u54ea\u4e00\u6b65']) || blocked || '\u4ea4\u4ed8';
    var whoB = (rc && rc['\u62a5\u7ed9\u8c01']) || (pol && pol.stop_to) || '';
    L.push('<b style="color:var(--amber)">\u5931\u8d25\u56de\u6267\uff08\u540e\u7aef \u00b7 HTTP ' + paEsc(String(http)) + '\uff09</b>');
    L.push('<b>\u505c\u5728\u54ea\u4e00\u6b65</b>\uff1a' + paEsc(String(stage)) + (blocked ? ('\uff08\u95f8 ' + paEsc(String(blocked)) + '\uff09') : ''));
    L.push('<b>\u62a5\u7ed9\u8c01</b>\uff1a' + paEsc(whoB || paSlotSt.who || '\u672a\u53d6\u5f97'));
    L.push('<b>\u56e0</b>\uff1a' + paEsc(String((d && d.error) || '\u672a\u53d6\u5f97')));
    L.push('<b>$/\u4ef6</b>\uff1a' + paEsc(cst ? ('\u5355\u4ef7 ' + cst['\u5355\u4ef7_\u5143\u6bcf\u4ef6'] + ' ' + (cst['\u5e01'] || '') + ' \uff0f \u4ef6') : '\u65e0\u56de\u6267\uff08\u6b64\u8def\u672a\u5230\u56de\u6267\u884c\uff09'));
    L.push('<span style="color:var(--sub)">task_id ' + paEsc(String(tid || '\u2014')) + ' \u00b7 \u771f\u6e90 POST /v9/pa/deliver/mail\uff08\u62d2\u4ea6\u7559\u75d5\uff09</span>');
  }
  out.innerHTML = L.join('<br>');
  return L.length;
}
/* —— 进收口面即读（只读）—— */
async function paSlotLoad(){
  await paSlotLearn();
  return paSlotJudgeRender();
}
try{ window.paSlot = {
  info: function(){
    return { steps: paSlotSt.steps, allow: paSlotSt.allow, allow_src: paSlotSt.allowSrc,
      who: paSlotSt.who, who_src: paSlotSt.whoSrc, who_rows: paSlotSt.whoN,
      usage: paSlotSt.usage,
      judge: paSlotSt.judge ? { ok: paSlotSt.judge.ok, known: paSlotSt.judge.known, txt: paSlotSt.judge.txt } : null,
      last_http: paSlotSt.lastHttp, mounted: !!paSlotQ('paSlotJudge'), at: paSlotSt.at };
  },
  learn: paSlotLearn, judge: paSlotJudgeRender, verdict: paSlotVerdict,
  taskId: paSlotTaskId, receipt: paSlotRenderReceipt, out: paSlotOut,
  setSteps: paSlotStep, steps: function(){ return paSlotSt.steps; },
  src: 'pm_\u520018p \u00a7\u4e00\uff08\u4e00\u952e\u51fa\u4ef6\u69fd\u4f4d\uff09'
}; }catch(e){}
