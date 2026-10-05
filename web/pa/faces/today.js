/* ClawsJoy PA v3 · 主面环（≤5）＋ 今日上下文（CW b2a5182 · 承 pm_994 P1 ／ pm_996 ／ pm_997 精简 ／ pm_裁_主面环≤5 · 2026-10-05）
   口径（承 L76）：本屏每一读数须回指真源；后端无此读数 ⇒ 显式「未知 ／ 未接」，⛔ 编数。
   真源（皆 GET · 只读）：pa/ui_state.json（#paUiStateRow · status.js 已接）／ /v9/pa/context
        ／ /v9/pes/runs ／ /v9/audit/approvals ／ /v9/pa/threads ／ /api/v5/session/list ／ /v9/pa/build。
   ⚠ 主面环 8 ⇒ 3（pm_997 §二）⇒ 5（pm_裁_主面环≤5：今日上下文 ／ 会话 ／ 任务 ／ 环境 ／ 收口）；Alt+1…5
      （Ctrl+1…n 被浏览器占 ⇒ ⛔ 假称可用 · 承 pm_995 §五照实格）。 */

const PA_V3_FACES = [
  {id:'ctx',   label:'今日上下文'},
  {id:'chat',  label:'会话'},
  {id:'tasks', label:'任务'}
];
/* ⭐ pm_刀3 ／ 刀3′ ／ 刀7p ／ 刀13p ＋ pm_裁_主面环≤5：四新面之**账**归此
   —— 面之注入与渲染在 tasks.js（其为最早可动且掌派活之事体）；
   环内 ＝ 环境 ／ 收口（入 #faceTabs ＋ PA_V3_FACES）；环外 ＝ 产品线 ／ 开机（入「更多 ▾ · ④ 面」组）。
   本径只开一钩：`setFaceById` 后调对应面之取数器（缺钩 ⇒ 面空而不报错 · 照实）。 */
let paXFaceHooks = {};
let paV3Face = 'ctx';

/* ⭐ pm_裁_主面环≤5（承 pm_997 §二 之「8 ⇒ 3」）：环内 ／ 环外须各得其位 ——
   环内（PA_V3_FACES）＝ 今日上下文 ／ 会话 ／ 任务 ／ 环境 ／ 收口（5 面 · Alt+1…5）；
   环外（产品线 ／ 开机）＝ 注入「更多 ▾」之「④ 面」组（各一步可达 · ⛔ 丢功能）。
   ⛔ 动 pa.html（内容件 · 承 pm_1052／pm_1067）⇒ 环外之钮由 tasks.js 注入 #paMoreBody。 */
function paV3Dom(id){
  document.querySelectorAll('#faceTabs button, #paXMoreTabs button').forEach(function(b){
    b.setAttribute('aria-pressed', String(b.getAttribute('data-face') === id));
  });
  document.querySelectorAll('#faces .facePane').forEach(function(p){
    p.classList.toggle('on', p.getAttribute('data-face') === id);
  });
}
function setFaceById(id){
  if(!id) return;
  const i = PA_V3_FACES.map(function(x){ return x.id; }).indexOf(id);
  if(i < 0 && !document.querySelector('#faces .facePane[data-face="' + id + '"]')) return;
  paV3Face = String(id);
  paV3Dom(paV3Face);
  if(paV3Face === 'tasks' && typeof paLoadTasks === 'function'){ try{ paLoadTasks(); }catch(e){} }
  try{ if(paXFaceHooks && typeof paXFaceHooks[paV3Face] === 'function') paXFaceHooks[paV3Face](); }catch(e){}
}
function setFace(i){
  const f = PA_V3_FACES[i]; if(!f) return;
  setFaceById(f.id);
}
document.addEventListener('keydown', function(e){
  if(!e.altKey || e.ctrlKey || e.metaKey) return;
  const n = parseInt(e.key, 10);
  if(!isNaN(n) && n >= 1 && n <= PA_V3_FACES.length){ e.preventDefault(); setFace(n - 1); }
});

/* —— 展开 ／ 收起（首屏只留三行；明细按需展开 · 承 pm_997 §三）—— */
function paTodayToggle(which){
  const map = {profile:'paTodayProfileBody', pending:'paTodayPendingBody'};
  const el = document.getElementById(map[which]); if(!el) return;
  const btn = document.querySelector('.today .mline .x[aria-controls="' + map[which] + '"]');
  const open = el.hasAttribute('hidden');
  if(open){ el.removeAttribute('hidden'); } else { el.setAttribute('hidden',''); }
  if(btn) btn.setAttribute('aria-expanded', String(open));
}
function paSrcToggle(){
  const el = document.getElementById('paSrcList'), c = document.getElementById('paSrcCaret');
  if(!el) return;
  const open = el.hasAttribute('hidden');
  if(open){ el.removeAttribute('hidden'); } else { el.setAttribute('hidden',''); }
  if(c) c.textContent = open ? '▴' : '▾';
}

/* —— 今日上下文（真读数 · 无源 ⇒ 显「未接」）—— */
function paV3Txt(id, s){ const e = document.getElementById(id); if(e) e.textContent = s; }
async function paGetJson(path){
  try{ const r = await fetch(path, {cache:'no-store'}); if(!r.ok) return null; return await r.json(); }
  catch(e){ return null; }
}

/* ⭐ pm 17:47 令 §一～§三 ＋ pm 17:51 补令 —— 素材七面之三改（CW b2a5182 落 · 本刻）
   ① 平台轴：⛔ 代操作他方平台 ＝ **红线** ⇒ 改标「⛔ 不接（红线：⛔ 代操作他方平台）」（⛔ 标「未接」—— 以「未接」
      暗许「将来会接」＝ **软性虚诺**）｜并立「未接」二义：⒜「未接 · 待办（M1）」（以后会有）／
      ⒝「⛔ 不接 · 红线」（不会有）⇒ **面须述「为何」**（红线 ／ 缺源 ／ 不可达）。
   ② 作业轴：**两名分列** —— `作业（调度件）`（源 `GET /v9/pa/dispatch/history`）⟷ `作业（PES 运行）`（源 `GET /v9/pes/runs`）
      ⇒ ⛔ 一词盖两义（旧面以「作业 0 件」盖二域 ⇒ 老板见「3 件已收口」而面上无）。
   ③ 台账轴：**三本机账**（作业账 ／ 授权账 ／ 线账）⇒ ⭐ **四键同形读**（`at` ／ `刻之性` ／ `面之径逐字` ／ `印`）
      —— **一码读 · ⛔ 逐面特判**（特判必漂 · 承 pm 17:51 补令）｜⛔ 前端自算（逐面读其数）｜
      ⛔ 一词盖两义（「台账（机账）」⟷「PA 待办」＝ `context.counts.ledger` · 同名异域）｜**唯读**。
   ⚠ `pa.html` 之静态行 ＝ **内容件**（承 pm_1052 ／ pm_1067 ⇒ ⛔ 我动）⇒ 于**运行期认领**（按**签文本** · ⛔ 唯凭序）
     ＋ 补 **行级** id（`srcRow*` —— ⚠ 静态之 `id="srcChat"／"srcRuns"／"srcCtx"` 在**内层 `<span>`** 上 ⇒ ⛔ 当行用 · 否则误嵌）；
     ⛔ 改静态件 ／ ⛔ 改 `*.css`（内联样式代之）。 */
var paSrcState = null;
function paSrcEsc(v){ return String(v == null ? '' : v).replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
function paSrcFind(list, sign){
  const its = list.querySelectorAll('.it');
  for(let i = 0; i < its.length; i++){ if(String(its[i].textContent || '').indexOf(sign) >= 0) return its[i]; }
  return null;
}
/* 认领静态**行**（补**行级** id `srcRow*`）；**幂等**（已认领 ⇒ 直过）。⛔ 唯凭序 ⇒ 按**签文本**认。 */
function paSrcClaim(){
  const list = document.getElementById('paSrcList');
  if(!list) return {ok:false, why:'#paSrcList 不在（左栏素材面未载）'};
  const map = [['💬','srcRowChat'], ['📄','srcRowFile'], ['🧾','srcRowLedger'], ['🌐','srcRowPlatform'], ['🎨','srcRowDraw'], ['🧠','srcRowCtx']];
  const bad = [];
  map.forEach(function(p){
    if(document.getElementById(p[1])) return;
    const el = paSrcFind(list, p[0]);
    if(el) el.id = p[1]; else bad.push(p[1] + '(签 ' + p[0] + ' 未获)');
  });
  if(!document.getElementById('srcRowRuns')){
    const el = paSrcFind(list, '🧰');
    if(el) el.id = 'srcRowRuns'; else bad.push('srcRowRuns(签 🧰 未获)');
  }
  return bad.length ? {ok:false, why:('认领 ⛔ 齐：' + bad.join(' · '))} : {ok:true};
}
/* 写**一行**（标签 ＋ 值 ＋ **源之径（独立一行）**）—— 内联样式（⛔ 动 *.css）。 */
function paSrcWrite(id, label, value, srcLine, bad){
  const el = document.getElementById(id); if(!el) return null;
  el.style.flexWrap = 'wrap';
  el.innerHTML = '<span>' + paSrcEsc(label) + '</span>'
    + '<span class="n"' + (bad ? ' style="color:#f85149"' : '') + '>' + paSrcEsc(value) + '</span>'
    + (srcLine ? '<span style="flex:0 0 100%;font-size:10px;line-height:1.5;color:var(--sub);opacity:.9">' + paSrcEsc(srcLine) + '</span>' : '');
  return el;
}
/* 增**一行**（幂等 · 插于 beforeId 之前）；用于②「两名分列」。 */
function paSrcEnsureRow(beforeId, newId, label, value, srcLine){
  let el = document.getElementById(newId);
  if(!el){
    const anchor = document.getElementById(beforeId);
    if(!anchor || !anchor.parentNode) return null;
    el = document.createElement('div'); el.className = 'it'; el.id = newId;
    anchor.parentNode.insertBefore(el, anchor);
  }
  return paSrcWrite(newId, label, value, srcLine, false);
}
/* ⭐ 台账轴之**四键同形读**（承 pm 17:51 补令）：`at` ／ `刻之性` ／ `面之径逐字` ／ `印`
   —— **一码读 · ⛔ 逐面特判**（特判必漂）｜⛔ 四键齐 ⇒ **显红 ＋ 报 PM**（⛔ 静默降级）；
   缺 `at` ⇒ 明书「刻缺」（⛔ 以屏刻充数刻 · 承 `L76`）｜`印` ＝ **器之印**（⛔ 唯信其名 · 须核其印 · 承我 1161 §四）。 */
function paLedgerFold(name, j, fallbackSrc, numFn){
  const K = ['at', '刻之性', '面之径逐字', '印'];
  const g = {}, miss = [];
  K.forEach(function(k){
    const v = (j && j[k] != null && String(j[k]) !== '') ? String(j[k]) : '';
    g[k] = v; if(!v) miss.push(k);
  });
  return {
    name: name, miss: miss,
    value: j ? ((numFn && numFn(j)) || '（后端应答无该读数 ⇒ 照实缺）') : PA_GAP.down('后端无应答'),
    src: g['面之径逐字'] || (fallbackSrc || '⚠ 后端未给 `面之径逐字`'),
    srcKey: !!g['面之径逐字'],
    at: g['at'] || null,
    atTxt: g['at'] || '⚠ 刻缺（后端未给 `at` ⇒ ⛔ 以屏刻充数刻 · 承 L76）',
    stamp: g['印'] || '⚠ 印缺',
    xing: g['刻之性'] || null
  };
}
/* ⭐ 素材面之读（承 pm 20:16 §三.⒞：源 ＝ GET /v9/pa/source_faces · 按「名」取 · ⛔ 硬编码）
   ——— 逐面：name ／ role ／ kind ／ 聚合之式（数须附式）／ 量 ／ 行之数 ／ rows ／ 缺根 ／ 印（本面之印 · pm 20:34 裁）；
   顶层：at（取数刻）／ 印（面册之印 · 全印）／ 印器（器之印）／ faces_version。
   ⚠ 印两键并存：有本面印 ⇒ 显本面印 ／ 无 ⇒ 回落全印（逐字照旧 · 两态皆照实 · pm 20:28 §二 ①）。
   ⚠ 两轨两名：本面之名（文件 ／ 出图）≠ 检索面 PA_FACES 之名（文件·产出）⇒ 两名分列（承 pm 20:16 裁二.⒜ 之「对映」）。
   ⛔ 缺读源 ／ 缺面 ／ 缺键 ⇒ 照实（PA_GAP · ⛔ 编 ／ ⛔ 以屏刻充数刻）。 */
function paSrcFaceOf(sf, name){
  if(!sf || !Array.isArray(sf.faces)) return null;
  for(let i = 0; i < sf.faces.length; i++){
    if(sf.faces[i] && sf.faces[i].name === name) return sf.faces[i];
  }
  return null;
}
function paSrcFaceValue(f){
  if(!f || typeof f['量'] !== 'number') return null;
  let s = f['量'] + ((f.kind === 'files') ? ' 件' : ' 张');
  if(typeof f['行之数'] === 'number'){
    s += (f.kind === 'dirs') ? (' · ' + f['行之数'] + ' 目录（按目录聚合）') : (' · ' + f['行之数'] + ' 根');
  }
  if(Array.isArray(f['缺根']) && f['缺根'].length) s += ' ⚠ 缺根 ' + f['缺根'].length;
  return s;
}
function paSrcFaceSrc(sf, name, f){
  return '源：GET /v9/pa/source_faces（按名取 ⇒ 名「' + name + '」）'
    + (f ? ('｜role ' + (f.role || '?') + ' · kind ' + (f.kind || '?')
            + '｜聚合之式：' + (f['聚合之式'] || '⚠ 后端未给 聚合之式')) : '')
    + '｜取数刻 ' + PA_STAMP.fmt((sf && sf.at) ? sf.at : '⚠ 刻缺（后端未给 at ⇒ ⛔ 以屏刻充数刻 · 承 L76）')
    + ((f && f['印']) ? ('｜本面之印 ' + f['印'])
                       : ('｜面册之印（全印 · ⛔ 逐面） ' + ((sf && sf['印']) ? sf['印'] : '⚠ 印缺')))
    + '｜器之印 ' + ((sf && sf['印器']) ? sf['印器'] : '⚠ 印器缺')
    + '｜⛔ 检索面（PA_FACES 之「文件·产出」）≠ 本面 ⇒ 两轨两名分列';
}
/* ②③ 之渲染 ＋ 左栏摘要（⛔ 手搓数：三本机账之数皆取各自后端响应）。 */
async function paLoadSrcFaces(o){
  const srcOk = paSrcClaim();
  if(!srcOk.ok){ paV3Txt('paSrcSum', '素材面认领 ⛔ 成：' + srcOk.why + '（⛔ 静默降级 ⇒ 报 PM）'); return srcOk; }
  /* ① 一词之性质（⛔ 以「未接」盖「红线」） */
  /* ⚠ why 归**值格**（⛔ 源行）—— 源行之义 ＝ 源之径（承 today.js:111）；且「⛔ 以「未接」暗许「将来会接」＝ 软性虚诺」
     属**辨义**类 ⇒ ⛔ 上屏（承 pm 1272 §三）。平台面 ⛔ 后端源 ⇒ 源行 ＝ **空**。出处 ＝ PM 17:47 §二改①。 */
  paSrcWrite('srcRowPlatform', '🌐 平台', PA_GAP.off('⛔ 代操作他方平台'));
  /* ⭐ 素材面两行（承 pm 20:16 §三.⒞）：自 GET /v9/pa/source_faces 取（⛔ 硬编码 · ⛔ 手搓数）。
     ⛔ 缺读源 ／ 缺面 ⇒ 照实「⒜ 未接 · 待办（M1）＋ 为何未接」—— 读源一落 ⇒ 自动转绿（⛔ 装绿）。 */
  const _sf = (o && o.sf) || null;
  const _fFile = paSrcFaceOf(_sf, '文件');
  const _fDraw = paSrcFaceOf(_sf, '出图');
  paSrcWrite('srcRowFile', '📄 文件',
    _sf ? (paSrcFaceValue(_fFile) || '（后端应答无 量 ⇒ 照实缺）')
        : PA_GAP.down('读源未给（GET /v9/pa/source_faces 未应答 ∨ 未载 ⇒ 照实）'),
    paSrcFaceSrc(_sf, '文件', _fFile),
    !!(_sf && !_fFile));
  paSrcWrite('srcRowDraw', '🎨 出图',
    _sf ? (paSrcFaceValue(_fDraw) || '（后端应答无 量 ⇒ 照实缺）')
        : PA_GAP.down('读源未给（GET /v9/pa/source_faces 未应答 ∨ 未载 ⇒ 照实）'),
    paSrcFaceSrc(_sf, '出图', _fDraw),
    !!(_sf && !_fDraw));
  /* ② 作业轴：两名分列（⛔ 一词盖两义） */
  const cD = (o.d && o.d.counts) ? o.d.counts : null;
  const fD = paLedgerFold('作业账', o.d, 'data\\v9\\pa\\dispatch.jsonl', null);
  paSrcEnsureRow('srcRowRuns', 'srcRowDispatch', '🧰 作业（调度件）',
    cD ? ('rows ' + cD.rows + ' · 已收口 ' + cD.closed + ' · 待外部回执 ' + cD.awaiting_receipt + ' · 席轴 ' + cD.seat_axis + ' ／ 池路 ' + cD.no_seat_axis)
       : (o.d ? '（后端应答无 counts ⇒ 照实缺）' : PA_GAP.down('后端无应答')),
    '源：GET /v9/pa/dispatch/history ｜ 面之径 ' + fD.src + ' ｜ 刻 ' + fD.atTxt);
  paSrcWrite('srcRowRuns', '🧰 作业（PES 运行）', (o.nR === null) ? PA_GAP.down('后端无应答') : (o.nR + ' 件'),
    '源：GET /v9/pes/runs ｜ 刻 ' + ((o.runs && o.runs.generated_at) || '⚠ 刻缺（后端未给 generated_at）'));
  /* ③ 台账轴（机账 · 三本）⇒ 一码读四键（⛔ 逐面特判）｜⛔ 一词盖两义 */
  const books = [
    paLedgerFold('作业账', o.d, 'data\\v9\\pa\\dispatch.jsonl', function(j){ const c = j && j.counts; return c ? ('rows ' + c.rows + ' · 已收口 ' + c.closed) : null; }),
    paLedgerFold('授权账', o.a, 'data\\v9\\pa\\deliver_authz.jsonl', function(j){ const u = j && j['用途之数']; return (j && j['行数'] != null) ? (j['行数'] + ' 行' + (u ? (' · 业务 ' + u['业务'] + ' ／ 探针 ' + u['探针']) : '')) : null; }),
    paLedgerFold('线账', o.l, 'data\\v9\\pa\\dispatch.jsonl × data\\v9\\pa\\receipts.jsonl', function(j){ const c = j && j.counts; return (j && j.count != null) ? (j.count + ' 线 · 已收口 ' + (c ? c['已收口'] : '?') + ' ／ 未 ' + (c ? c['未收口'] : '?')) : null; })
  ];
  const missAll = [];
  books.forEach(function(b){ if(b.miss.length) missAll.push(b.name + ' 缺 ' + b.miss.join(' ／ ')); });
  paSrcWrite('srcRowLedger', '🧾 台账（机账）',
    books.map(function(b){ return b.name + ' ' + b.value; }).join(' ｜ ')
      + (missAll.length ? (' ⚠ 四键 ⛔ 齐（' + missAll.join(' · ') + '）⇒ 已报 PM · ⛔ 静默降级') : ''),
    '⛔ ≠ `context.counts.ledger`（＝ **PA 待办** · 同名异域 ⇒ 两名分列）｜源（皆 GET · 唯读 · 逐面读其数）：'
      + books.map(function(b){ return b.name + ' ⇒ ' + b.src + '（' + b.stamp + ' · 刻 ' + b.atTxt + '）'; }).join(' ｜ '),
    missAll.length > 0);
  /* 左栏摘要（素材七面 ⇒ 一行） */
  paV3Txt('paSrcSum', '会话 ' + (o.nThr === null ? PA_GAP.down() : o.nThr + ' 条')
    + ' · 作业 调度 ' + (cD ? cD.rows : PA_GAP.down()) + ' ／ PES ' + (o.nR === null ? PA_GAP.down() : o.nR)
    + ' · 台账 ' + books.length + ' 本' + (missAll.length ? '（⚠ 四键 ⛔ 齐）' : '')
    + ' · 记忆 ' + (o.nLine === null ? PA_GAP.down() : o.nLine + ' 行')
    + ' · 素材面 ' + (_sf ? ('2 面（文件 ' + (_fFile ? (paSrcFaceValue(_fFile) || '缺量') : '缺') + ' ／ 出图 ' + (_fDraw ? (paSrcFaceValue(_fDraw) || '缺量') : '缺') + ' · 刻 ' + PA_STAMP.fmt(_sf.at || '刻缺') + '）') : PA_GAP.todo())
    + ((_sf && _fFile && _fDraw) ? '' : (' ／ ' + (_sf ? '待办 ' : '缺 ') + (2 - ((_fFile ? 1 : 0) + (_fDraw ? 1 : 0))) + ' 面'))
    + ' ＋ ⒝ ' + PA_GAP.off() + ' 1（平台 · 红线）');
  /* ⭐ pm 19:05 令 §一：活面之数 ⇒ 同屏附「取数刻」＋逾阈显陈旧（第四态）。
     ⛔ 以屏刻充数刻（承 L76）—— 后端未给 `at` 者 ⇒ 照实「⚠ 取数刻未给」（承 pm 19:05 §四界：报 PM 转 TD）。 */
  if(window.PA_STALE){
    var _lAt = null, _lMiss = false;
    books.forEach(function(b){
      if(b.at){ var _t = Date.parse(String(b.at).replace(' ', 'T')); if(_lAt === null || _t < Date.parse(String(_lAt).replace(' ', 'T'))) _lAt = b.at; }
      else _lMiss = true;
    });
    PA_STALE.mark(document.getElementById('srcRowChat'), null, '会话（源 GET /v9/pa/threads · 后端未给取数刻）');
    /* ⭐ pm 1346 §二.2（枚举同族）：素材**二面**之取数刻（`sf.at`）已上屏（源行 · `paSrcFaceSrc`）
       ⇒ 同族 ⇒ 须标（旧唯五 `srcRow*` ＋ 三 `*Src` 有标 ⇒ 此二行漏 · ⛔ 只补「#paUiStateRow」一处）。 */
    PA_STALE.mark(document.getElementById('srcRowFile'), (_sf && _sf.at) ? _sf.at : null, '素材面·文件（GET /v9/pa/source_faces）');
    PA_STALE.mark(document.getElementById('srcRowDraw'), (_sf && _sf.at) ? _sf.at : null, '素材面·出图（GET /v9/pa/source_faces）');
    PA_STALE.mark(document.getElementById('srcRowLedger'), _lMiss ? null : _lAt, '台账（机账 · 三本之最旧取数刻）');
    PA_STALE.mark(document.getElementById('srcRowDispatch'), (o.d && o.d.at) ? o.d.at : null, '作业（调度件 · GET /v9/pa/dispatch/history）');
    PA_STALE.mark(document.getElementById('srcRowRuns'), (o.runs && o.runs.generated_at) ? o.runs.generated_at : null, '作业（PES 运行 · GET /v9/pes/runs）');
    PA_STALE.mark(document.getElementById('srcRowCtx'), null, '记忆自身（源 GET /v9/pa/context · 后端未给取数刻）');
    PA_STALE.tick();
  }
  paSrcState = {ok:true, books: books, cD: cD, missAll: missAll};
  return paSrcState;
}
/* 画像之「刻」判据（承 `L76`：刻须随值 · 承 `pm_1049 §二.1`）：mtime 距今 > 24 h ⇒ 明标「已陈旧 N 天」；
   ⛔ 静默：判不出 ⇒ 回 `null`（调用处须显「未知」）。 */
function paTodayAged(t){
  const ms = Date.parse(String(t || '').replace(' ', 'T'));
  if(isNaN(ms)) return null;
  const d = Date.now() - ms;
  if(d <= 24 * 3600 * 1000) return {stale: false, days: 0};
  return {stale: true, days: Math.floor(d / 86400000)};
}
/* 画像摘要 → 已定（事实）／待裁（提案）两分节（承 `pm_1049 §二.2`：⛔ 混列）。
   判据：句内 `(提案)` 之标（后端所给之「状态」轴）⇒ 待裁；余者 ⇒ 已定。 */
function paTodayBrief(brief){
  const fact = [], prop = [];
  let dom = '';
  String(brief || '').split('\n').forEach(function(raw){
    const h = raw.match(/^\u3010\s*([^\u3011]+?)\s*\u3011\s*$/);
    if(h){ dom = h[1]; return; }
    const t = raw.trim(); if(!t) return;
    let body = t.replace(/^-\s*/, '');
    let conf = '';
    const cm = body.match(/\[(high|medium|low)\]/i);
    if(cm){ conf = cm[1].toLowerCase(); body = body.replace(/\[(high|medium|low)\]/ig, '').trim(); }
    let st = '';
    if(/\(提案\)/.test(body)){ st = '提案'; body = body.replace(/\(提案\)/g, '').trim(); }
    let dt = '';
    const dm = body.match(/\((20\d\d-\d\d-\d\d)\)\s*$/);
    if(dm){ dt = dm[1]; body = body.replace(/\((20\d\d-\d\d-\d\d)\)\s*$/, '').trim(); }
    (st ? prop : fact).push({dom: dom, body: body, conf: conf, st: st, dt: dt});
  });
  return {fact: fact, prop: prop};
}
const PA_CONF_CN = {high: '高', medium: '中', low: '低'};
/* 渲染：两轴**形不同**（承 `pm_1049 §二.3`）—— 置信轴＝灰字「置信 高」；状态轴＝琥珀粗体「状态 提案 · 待裁」。 */
function paTodayBriefHtml(brief, stat){
  const g = paTodayBrief(brief);
  function esc(v){ return String(v == null ? '' : v).replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
  function row(it){
    const tags = [];
    if(it.conf) tags.push('<span style="color:#8b949e">置信 ' + esc(PA_CONF_CN[it.conf] || it.conf) + '</span>');
    if(it.st)   tags.push('<span style="color:#d29922;font-weight:600">状态 提案 · 待裁</span>');
    if(it.dt)   tags.push('<span style="color:#6e7681">记录 ' + esc(it.dt) + '</span>');
    return '  - [' + esc(it.dom || '—') + '] ' + esc(it.body) + (tags.length ? ' ｜ ' + tags.join(' ｜ ') : '');
  }
  const out = [];
  const S = stat || null;
  /* ⭐ pm_刀22p：**同屏唯一个「已定」之数** —— 正标题之数取**后端真源**（`GET /v9/pa/profile` 之 `status` 轴）；
     brief 之行（面内派生）**降为附注**（⛔ 与正标题争位 · ⛔ 并存而不标差异）。承「两集须 ≡」＋「少而可信」。 */
  out.push('<b>【已定 · 事实】</b>' + (S ? (S.conf + ' 条') : PA_GAP.down('后端未应答'))
    + ' —— 真源：GET /v9/pa/profile · status=confirmed（⛔ 面内派生）');
  out.push('<b>【待裁 · 提案】</b>' + (S ? (S.prop + ' 条') : PA_GAP.down('后端未应答'))
    + ' —— 真源：GET /v9/pa/profile · status=proposed'
    + (S && S.pend != null ? (' · 第二源 context.counts.pending ' + S.pend + ' 条' + (S.pend === S.prop ? ' ≡' : ' ⚠ ⛔ 齐（显红）')) : ' ⚠ 缺第二源')
    + '（⛔ 面内派生）');
  out.push('');
  const bad = !!(S && (S.conf !== g.fact.length || S.prop !== g.prop.length));
  out.push('（附注 · 面内派生 · brief 之行）无「(提案)」标 ' + g.fact.length + ' 行 ／ 带「(提案)」标 ' + g.prop.length + ' 行'
    + (S ? (bad ? ' ⇒ ⚠ **两源 ⛔ 齐**（⛔ 当「已定」· 真数见上二行）' : ' ⇒ 与后端 status 轴 ≡')
         : ' ⇒ ⚠ 后端未应答 ⇒ ⛔ 可对')
    + ' ｜ ⛔ 后端 status=proposed 若未落此标 ⇒ 本处显 0（**未下 ⇔ 真 0 ⇔ 不可辨** · 承 pm_刀10）');
  out.push('· 无「(提案)」标之行（' + g.fact.length + '）：');
  if(g.fact.length){ g.fact.forEach(function(it){ out.push(row(it)); }); } else { out.push('  （无）'); }
  out.push('· 带「(提案)」标之行（' + g.prop.length + '）：');
  if(g.prop.length){ g.prop.forEach(function(it){ out.push(row(it)); }); } else { out.push('  （无）'); }
  return out.join('\n');
}
async function paLoadToday(){
  const el = document.getElementById('paToday'); if(!el) return null;
  const u = encodeURIComponent(curUser());
  const sid = encodeURIComponent(curSession());
  const now = new Date().toLocaleTimeString('zh-CN', {hour12:false});
  const ctx  = await paGetJson(API + '/v9/pa/context?user_id=' + u);
  const runs = await paGetJson(API + '/v9/pes/runs?user_id=' + u);
  const appr = await paGetJson(API + '/v9/audit/approvals?user_id=' + u + '&session_id=' + sid);
  const thr  = await paGetJson(API + '/v9/pa/threads?user_id=' + u);
  const sess = await paGetJson(API + '/api/v5/session/list');
  const bld  = await paGetJson(API + '/v9/pa/build');
  /* ⭐ pm_刀10 §一：**待裁** 之真源 ＝ 画像 `status="proposed"`（⛔ 以 brief 行数 − 节头数 充） */
  const prof = await paGetJson(API + '/v9/pa/profile');
  /* ⭐ 台账轴（机账）之三本 —— 源已在（承 pm 17:47 令 §二改③）；四键同形之读在 paLedgerFold（⛔ 逐面特判）。 */
  const bkDispatch = await paGetJson(API + '/v9/pa/dispatch/history');
  const bkAuthz    = await paGetJson(API + '/v9/pa/deliver/authz?limit=200&usage=all');
  const bkLines    = await paGetJson(API + '/v9/pa/lines');
  const bkSrcFaces = await paGetJson(API + '/v9/pa/source_faces');
  /* ⭐ pm_1061 §五：上屏「实到 `num_ctx`」（真源 ＝ **本函数同一** `GET /v9/pa/context` 之新键 `num_ctx` ⇒ 单源 · ⛔ 另取 ／ ⛔ 硬编 · 承 `L83` ／ `L102`）。
     ＋ 明标「超此值 ⇒ 本机截断」（承「⛔ 静默截断」）｜⭐ 真窗键（如 `context_length`）后端**未落** ⇒ **只报 `num_ctx`**（⛔ 编真窗）。
     ⭐ 用**既有行内文案**（`#paTodayWhen` ＝ `.today .h .when` · `pa_v3.css:28` ⛔ `nowrap` ／ ⛔ `overflow:hidden` ⇒ 可容）
       —— ⛔ 加控件 ／ ⛔ 加行 ／ ⛔ 动 `pa.html`（内容件 · 老板批）。⛔ 无该键 ⇒ 照实「未知」（⛔ 显旧值）。 */
  const nctx = (ctx && ctx.num_ctx != null) ? String(ctx.num_ctx) : '';

  /* ① 画像（源 /v9/pa/context） */
  const brief = (ctx && typeof ctx.brief === 'string') ? ctx.brief : null;
  const nLine = brief ? brief.split('\n').filter(function(x){return x.trim();}).length : null;
  const secs = brief ? (brief.match(/^\u3010/gm) || []).length : null;
  /* 画像件之「刻 ＋ 件」（承 `pm_1049 §二.1`）：径为前端常量 · 值（mtime／sha16／path）由后端现算（GET /v9/pa/build） */
  const pmeta = await paGetJson(API + '/v9/pa/build?file=' + encodeURIComponent('../data/v9/pa/profile.json'));
  const pstamp = (pmeta && pmeta.exists) ? String(pmeta.mtime || '') : '';
  const paged = pstamp ? paTodayAged(pstamp) : null;
  const psplit = paTodayBrief(brief);
  /* ⭐ pm_刀10 §一.3：**屏刻须取数刻并显陈旧度** —— 本行 ＝ 「本屏读数（前端取刻）」＋
     「画像件刻（后端现算之 mtime）」＋ 陈旧度；⛔ 以「本屏读数刻」顶「件之刻」（承 L76 ／ 刀11p §零）。 */
  paV3Txt('paTodayWhen', '本屏读数 ' + now + ' ｜ 画像件刻 ' + (pstamp || '未知')
    + (paged && paged.stale ? ('（⚠ 已陈旧 ' + paged.days + ' 天）') : '')
    + ' ｜ 上下文窗 num_ctx ' + (nctx ? (nctx + '（本次 · 为上限 ⇒ 超此值 本机截断 · ⛔ 静默 · 源 GET /v9/pa/context）') : '未知（后端未应答 ／ 无该键 ⇒ ⛔ 编）'));
  /* ⭐ pm_刀10 §一：**`confirmed` ／ `proposed` 两态分列** ＋ 「待裁」数 ＝ `proposed`（后端 status 轴）。
     ⚠ 病（PM 实测）：旧面以「brief 非空行数 − 节头数」充「已定」⇒ 显 12，后端 status 轴实 8；
        「待裁」旧显 0，实 4。⇒ 真数取 `GET /v9/pa/profile` 之 `entries[].status`（承 L83 单源）；
        面内派生之数**并存并明标**；两数 ⛔ 齐 ⇒ **显「两源 ⛔ 齐」**（承 pm_086「两集须 ≡ ∧ 两向皆报」）。 */
  let nConf = null, nProp = null, nRev = null, nEnt = null;
  if(prof && Array.isArray(prof.entries)){
    nEnt = prof.entries.length;
    nConf = prof.entries.filter(function(x){ return x && x.status === 'confirmed'; }).length;
    nProp = prof.entries.filter(function(x){ return x && x.status === 'proposed'; }).length;
    nRev  = prof.entries.filter(function(x){ return x && x.status === 'revised'; }).length;
  }
  /* ⭐ pm_刀16p §二.1：「待裁」之**两源须 ≡** —— ① `GET /v9/pa/profile` 之 `status=proposed`（nProp）
     ② `GET /v9/pa/context` 之 `counts.pending`（nPendCtx）｜两源 ⛔ 等 ⇒ **显红**（⛔ 取其一掩之 · 承 pm_086）。 */
  /* ⭐ pm 1346 §二.1：**「后端未应答」⟷「应答在 · 唯键不在」须分形** —— 承 core.js:65「回退支」＝不可达之**特形**
     ⇒ 其文须与「无此面」分形（⛔ 同形 ⇒ 读方必误）；旧守 `pendOk` 一括二形 ⇒ 同支出二辞（此处「不可达」⟷ 源行「回退支」＝二说）。
     据须**可判**：`ctx` 之在否 ⇔ `counts.pending` 之键之在否。 */
  const ctxOk = !!ctx;
  const nPendCtx = (ctxOk && ctx.counts && typeof ctx.counts.pending === 'number') ? ctx.counts.pending : null;
  const pendOk = (nPendCtx !== null);
  const pendGap = pendOk ? null : (ctxOk ? PA_GAP.fallback('context.counts.pending') : PA_GAP.down('后端未应答'));
  const statOk = (nConf !== null);
  const xBad = (statOk && (nConf !== psplit.fact.length || nProp !== psplit.prop.length))
            || (statOk && pendOk && nPendCtx !== nProp);
  paV3Txt('paTodayProfile', brief
    ? (nLine + ' 行（式：brief 非空行数 · 含 ' + (secs === null ? '未知' : secs) + ' 节头）'
       + ' · 已定 ' + (statOk ? (nConf + ' 条') : PA_GAP.down()) + ' ／ 待裁 ' + (statOk ? (nProp + ' 条') : PA_GAP.down())
       + '（源：GET /v9/pa/profile · status 轴）'
       + ' · 面内派生（brief 文）：无「(提案)」标 ' + psplit.fact.length + ' 行 ／ 带标 ' + psplit.prop.length + ' 行'
       + (xBad ? ' ⚠ 两源 ⛔ 齐（承 pm_刀22p：⛔ 当「已定」）' : '')
       + ' · 待裁之两源：profile ' + (statOk ? (nProp + ' 条') : PA_GAP.down())
       + ' ⟷ context.counts.pending ' + (pendOk ? (nPendCtx + ' 条') : pendGap)
       + ((statOk && pendOk) ? (nPendCtx === nProp ? ' ≡' : ' ⚠ ⛔ 齐（显红）') : ' ⚠ 缺一源')
       + ' · 单例（本机 1 个客户）')
    : '未知（后端未应答 ／ 无读数）');
  paV3Txt('paTodayProfileSrc', '源：GET /v9/pa/context（brief）｜已定 ／ 待裁 之真源：GET /v9/pa/profile（字段 status · '
    + (statOk ? ('实 entries ' + nEnt + ' ⇒ confirmed ' + nConf + ' ／ proposed ' + nProp + ' ／ revised ' + nRev) : '**' + PA_GAP.down('后端未应答') + '**')
    + '）｜⛔ 不以「行数 − 节数」自算充之（承 pm_刀10）｜待裁之第二源：GET /v9/pa/context 之 counts.pending（'
    + (pendOk ? (nPendCtx + ' 条') : '**' + pendGap + '**')
    + '）｜两源不等 ⇒ 显红（承 pm_刀16p §二.1）｜画像件 '
    + ((pmeta && pmeta.exists) ? (String(pmeta.path || '') + '（sha16 ' + String(pmeta.sha16 || '未知') + '）') : '未知（GET /v9/pa/build 未应答）')
    + ' ｜ 采样刻 ' + (pstamp || '未知（GET /v9/pa/build 未应答）')
    + (paged && paged.stale ? '（⚠ 已陈旧 ' + paged.days + ' 天）' : ''));
  const ptxtEl = document.getElementById('paTodayProfileText');
  if(ptxtEl){ ptxtEl.innerHTML = brief ? paTodayBriefHtml(brief, statOk ? {conf: nConf, prop: nProp, revised: nRev, entries: nEnt, pend: nPendCtx} : null) : '（后端未应答 ⇒ 无摘要可显 · ⛔ 不编）'; }
  paV3Txt('srcCtx', brief ? (nLine + ' 行（非空 · 含节头）') : PA_GAP.down('后端未应答'));

  /* ② 待你裁（源 /v9/audit/approvals ＋ /v9/pes/runs） */
  const nA = (appr && Array.isArray(appr.approvals)) ? appr.approvals.length : null;
  const nR = (runs && Array.isArray(runs.runs)) ? runs.runs.length : null;
  paV3Txt('paTodayPending',
    (nA === null ? PA_GAP.down('后端未应答') : (nA === 0 ? '0 件（后端 approvals: []）' : nA + ' 件'))
    + '（式：approvals[] 长 · **审批**待审 ⛔ ≠ 画像「待裁」' + (statOk ? ('＝ ' + nProp + ' 条') : '＝ ' + PA_GAP.down()) + '）'
    + ' · runs ' + (nR === null ? PA_GAP.down() : nR + ' 件'));
  paV3Txt('paTodayPendingSrc',
    '源：GET /v9/audit/approvals（session_id=' + curSession() + '）｜GET /v9/pes/runs'
    + (runs && runs.generated_at ? ('（**数之刻** ' + runs.generated_at + '）') : '（⚠ 后端未给 generated_at ⇒ 刻缺 · ⛔ 以屏刻充数刻）'));
  /* ⭐ pm 1346 §二.2（枚举同族）：本行亦持后端取数刻（`runs.generated_at`）而上屏（上行「数之刻」）⇒ 同族 ⇒ 须标。 */
  if(window.PA_STALE){ PA_STALE.mark(document.getElementById('paTodayPendingSrc'), (runs && runs.generated_at) ? runs.generated_at : null, '待你裁（源 GET /v9/pes/runs）'); PA_STALE.tick(); }
  paV3Txt('srcRuns', (nR === null) ? PA_GAP.down() : (nR + ' 件'));

  /* ③ 昨夜整合：无真源 ⇒ 明说未接（⛔ 编） */
  paV3Txt('paTodayNight', '未知 —— ' + PA_GAP.todo('无源（夜间整合无后端面 · 承 pm 18:00 批一）') + ' · ⛔ 编');

  /* 系统区：构建（源 /v9/pa/build）＋ 降级面（后端自报 ⇒ 显式列出 · ⛔ 藏失败） */
  paV3Txt('paTodayBuild', (bld && bld.sha16) ? (bld.sha16 + '（' + bld.bytes + ' B · mtime ' + (bld.mtime || '—') + '）') : '未知（后端未应答）');
  const deg = (runs && Array.isArray(runs.degradations)) ? runs.degradations : [];
  const dEl = document.getElementById('paTodayDeg');
  if(dEl) dEl.innerHTML = deg.length
    ? '<div class="deg">⚠ 后端自报降级 ' + deg.length + ' 条（如实列出 · ⛔ 藏）：'
      + deg.map(function(d){ return '<br>· <code>' + String(d.code || '') + '</code> —— ' + String(d.message || ''); }).join('') + '</div>'
    : '';

  /* 左栏 来源面：会话（源 /v9/pa/threads）＋ 摘要 1 行（承 pm_997 §四.2） */
  let nThr = null;
  if(thr){ nThr = Array.isArray(thr) ? thr.length : (Array.isArray(thr.threads) ? thr.threads.length : null); }
  paV3Txt('srcChat', (nThr === null) ? PA_GAP.down() : (nThr + ' 条'));
  const nSess = (sess && Array.isArray(sess.sessions)) ? sess.sessions.length : null;
  /* ⭐ 素材七面之三改（①②③ · 承 pm 17:47 令 ＋ 17:51 补令）⇒ 渲染 ＋ 左栏摘要皆在其内 */
  await paLoadSrcFaces({runs: runs, nR: nR, nThr: nThr, nLine: nLine, d: bkDispatch, a: bkAuthz, l: bkLines, sf: bkSrcFaces});

  /* 会话面头：后端会话史（源 /api/v5/session/list）—— 真数据（⛔ 编） */
  paV3Txt('paChatHistSrc', '本机线程 ' + (nThr === null ? PA_GAP.down() : nThr + ' 条') + ' · 后端会话史 '
    + (nSess === null ? PA_GAP.down('GET /api/v5/session/list 未应答') : nSess + ' 条（源 GET /api/v5/session/list）'));
  return {ctx: !!ctx, runs: !!runs, appr: !!appr, sess: !!sess, bld: !!bld};
}

/* ⭐ pm 19:05 令 §一⒞：刷新之**显式入口**（⛔ 自轮询）—— 重取活面之数 ＋ 刻前移 ＋ 陈旧消。
   ⒟ 反控：刷新后 ⇒ 陈旧消 ＋ 刻前移（与「静置逾阈 ⇒ 必显陈旧」成对 · 两向皆可机械验）。 */
async function paRefreshLive(){
  try{
    if(window.PA_STALE) PA_STALE.clear();
    await paLoadToday();
    try{ if(typeof paLoadEnvFace === 'function') await paLoadEnvFace(); }catch(e){}
    try{ if(typeof paLoadLinesFace === 'function') await paLoadLinesFace(); }catch(e){}
    try{ if(typeof paLoadResumeFace === 'function') await paLoadResumeFace(); }catch(e){}
    if(window.PA_STALE) PA_STALE.tick();
  }catch(e){ return false; }
  return true;
}
if(window.PA_STALE) PA_STALE.onRefresh(paRefreshLive);
window.paRefreshLive = paRefreshLive;

function paInitToday(){
  if(window.PA_FACES && PA_FACES.on && PA_FACES.on('today') === false) return;   /* 面闸（faces.json） */
  setFace(0);
  paLoadToday();
}
if(document.readyState === 'loading'){ document.addEventListener('DOMContentLoaded', paInitToday); }
else { paInitToday(); }

/* ⭐ pm_1052 §二（乙）：`#paAboutWhen` 之**静态占位**（`pa.html:143` 之裸「—」 · **内容件 ⛔ 我动**）
   ⇒ 由**最早可动之 v3 面件**（本件：`pa.html` 脚本序第 `325` 行 · 前于 `tasks`(326)⁄`more`(327)⁄`selfdesc`(328)⁄`sources`(329)）于**解析期**覆盖为人话。
   展开「更多」后 ⇒ `selfdesc.js` 之 `paAboutLoad()` 照旧写**「本屏读数 <刻>」**（⛔ 二判 · 本处只补**无读数之首帧**）。
   ① 只改文案（⛔ 加控件 · 首屏控件数不变）；② 只在原值＝裸「—」时覆盖（⛔ 盖真值）。 */
(function(){
  /* ⭐ pm_1052 §二：`pa.html`（**内容件 ⛔ 我动**）之**静态「—」占位**共三处
     ⇒ 由**最早可动之 v3 面件**（本件 · 脚本序第 `325` 行，前于 `tasks`(326)⁄`more`(327)⁄`selfdesc`(328)⁄`sources`(329)）
     于**解析期**按**各按各义**覆盖为人话（⛔ 一词套全部 · 承 `L103`）：
       `#paAboutWhen` ⇒ 尚无读数（展开「更多」即取）   （真源：`selfdesc.js` 之 `paAboutLoad()`）
       `#paPlanCnt`   ⇒ 尚未取（展开「更多」即取）   （真源：`more.js` 之 `paRenderPlans()`；计划列表由**面板开而取** `more.js:8`）
       `#paFileCnt`   ⇒ 尚未取（列表载入即显）       （真源：`more.js` 之 `paFileFilter()`；文件列表**随页载入**）
     ⛔ 二判；⛔ 盖真值（**唯原值 ≡ 裸「—」时才覆**）；⛔ 加控件（只赋 `textContent`）。 */
  var COVER = [
    ['paAboutWhen', '尚无读数（展开「更多」即取）'],
    ['paPlanCnt',   '尚未取（展开「更多」即取）'],
    ['paFileCnt',   '尚未取（列表载入即显）']
  ];
  function cover(){
    var miss = 0;
    for(var i = 0; i < COVER.length; i++){
      var el = document.getElementById(COVER[i][0]);
      if(!el){ miss++; continue; }
      if(String(el.textContent || '').replace(/\s+/g, '') === '—') el.textContent = COVER[i][1];
    }
    window.paCoverStat = {n: COVER.length, miss: miss, done: COVER.length - miss};
    return miss;
  }
  if(cover() && document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', cover);
  }
})();

/* ⭐ pm_1067 §二（我裁 · 承 L142 ／ L103）：`pa.html`（**内容件 ⛔ 我动**）之两处**过期文案**
   ⇒ 由本件（**最早可动之 v3 面件** · 脚本序第 `325` 行 · 前于 tasks ／ more ／ selfdesc ／ sources）
     于**解析期**「**渲染层覆盖**」（⛔ 待展开 · ⛔ 加控件 · 只换文案）：
     ① `:124`（`#paMorePerm` 之 mnote 之 <b>）—— 旧「写（每次问）」与 `selfdesc.js` 之权限层
        「② 写（主面每次问 ／ 派活路免审批）」**同屏相左**（声明 ⟷ 执行须符 · 承 L142）⇒ 覆盖为同向之形；
     ② `:139`（`#paMoreAbout` 之 mnote 之一文本节点）—— 旧「（该闸只看「知识库 ＋ 收件箱」⇒ 退化成
        知识库机器人）」**已过期**（今检索面之实况见 `POST /v9/pa/ask` 之 scope ／ faces）⇒ 覆盖为真。
     `:126`（`.phead`）系 **准留**（PM 裁 · 其义仍真：那确是**画像素材面**之计数）⇒ ⛔ 动。
   ⚠ 唯原值 ≡ 旧串时覆盖（⛔ 盖真值）；原串仍在 `pa.html` 盘上（⛔ 我动内容件 ⇒ 漂移之险已报）。 */
(function(){
  var OLD_B = '读（全局）／ 写（每次问）／ 外发（默认关）／ 凭据（只取布尔）';
  var NEW_B = '读（全局）／ 写（主面每次问 ／ 派活路免审批）／ 外发（默认关）／ 凭据（只取布尔）';
  var OLD_A = '（该闸只看「知识库 ＋ 收件箱」⇒ 退化成知识库机器人）';
  var NEW_A = '（⛔ 以检索闸之答代本面板读数 · 检索面之实况另见左栏「来源面」）';
  function coverPerm(){
    var sec = document.getElementById('paMorePerm');
    if(!sec) return 0;
    var b = sec.querySelector('p.mnote b');
    if(!b) return 0;
    if(String(b.textContent || '') === OLD_B){ b.textContent = NEW_B; return 1; }
    return 0;
  }
  function coverAbout(){
    var sec = document.getElementById('paMoreAbout');
    if(!sec) return 0;
    var p = sec.querySelector('p.mnote');
    if(!p) return 0;
    for(var i = 0; i < p.childNodes.length; i++){
      var n = p.childNodes[i];
      if(n.nodeType === 3 && String(n.data).indexOf(OLD_A) >= 0){
        n.data = String(n.data).replace(OLD_A, NEW_A);
        return 1;
      }
    }
    return 0;
  }
  function run(){
    var r = [coverPerm(), coverAbout()];
    window.paCover1067 = {perm: r[0], about: r[1]};
    return r[0] + r[1];
  }
  if(run() !== 2 && document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', run);
  }
})();
