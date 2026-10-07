/* ---- 首屏之「准备中 ／ 不可用」之面（CW b2a5182 · 2026-10-07 · pm_1617 五令 · 并 pm_1614 令一之外壳）
   pm 之立规（pm_1617 §一.3 ／ TD_1616 §一.3 · **要承**）：
     ⒜ 凡「等待」⇒ 必有「可见之提示 ＋ 进度（若可量）＋ 时长（估）」
     ⒝ 凡「不可用」⇒ 必有「因 ＋ 去处」
     ⒞ 凡提示 ⇒ 须在「用户当下看得见之处」（⛔ 藏于文档 ／ 聊天）
   病（老板之净机 · 一手）：首启 2–4 min（下 79 MB 向量模型）而页「一片静」⇒ 判「不能用」
     （老板之逐字：「状态一定是有提示的，不然我就遇到意味不能使用」）。
   真源 ＝ `GET /health`（后端自报 · **一处定形**）—— ⛔ 前端缓存之假态（F5 须复现同态 · 令五）。
   ⭐ 字段之逐字 ＝ **已对齐 TD `1616` 之一处定形**（`core/gateway/boot_progress.py` 之 `snapshot()`）——
      真源 `/health.boot`：`state` ／ `phase`（相序之机器码 · 见 `PA_PREP_PHASE`）／ `since_s` ／
      `phases_done` ／ `phases_total` ／ `progress` ／ `download{done_bytes,total_bytes,eta_s,note}` ／
      `failed{reason,hint}`；缺（旧后端）⇒ 回落 `/health.startup`（旧形 `progress` ／ `status` ／ `errors`）。
      缺者 ⇒ **明书「不可量」**（⛔ 造数）∧ ⛔ 以 `%` 充字节。
   ⛔ 本件 ⛔ 触 `core/**`（TD 之域 · 承界）。 */

const PA_PREP_POLL_MS  = 2000;    /* 取数之间隔（未就绪时） */
const PA_PREP_TICK_MS  = 1000;    /* 重渲之间隔（唯时间之变 ⇒ 秒数须跳） */
const PA_PREP_WATCH_MS = 15000;   /* 就绪后之巡（服务若停 ⇒ 令二之「因 ＋ 去处」须复现） */
const PA_PREP_MAX_TRIES = 90;     /* 有界（≈3 分钟 · 首启 2–4 min 之量级）⇒ 到点出「去处」 */

/* 步名 ／ `phase` ⇒ 人话（真源：core/lib/startup.py 之步名 ＋ TD 1616 之 phase 机器码 · ⛔ 造相 ／ ⛔ 造数）。
   ⛔ 在表 ⇒ **照实显原值**（承「界面态显真读数」· ⛔ 自造辞）。 */
const PA_PREP_PHASE = {
  /* ⭐ TD_1616 之相序（`core/gateway/boot.py` 之 `boot_progress.begin([...])` · 机器码逐字 · ⛔ 自造相名） */
  'http_listen': '正在监听端口（门已开）',
  'registries': '正在载入名录',
  'guards': '正在挂载守卫',
  'kb': '正在载入知识库',
  'vector_model_download': '正在准备向量模型（首启一次 · 约 79 MB）',
  'engine': '正在起引擎',
  'ready': '就绪',
  /* 旧 `startup.status` 之步名（旧后端 · 保兼容） */
  'import': '正在载入组件',
  '硬件检测': '正在检测硬件',
  'LLM就绪检查': '正在检查模型服务',
  'Agent池预热': '正在预热 Agent 池',
  '联邦知识加载': '正在载入联邦知识'
};
const PA_PREP_NOTE_WAIT = '首启一次约 2–4 分钟（下载约 79 MB 向量模型）· 期间页面可能暂不可用';
const PA_PREP_OUTLET = '去处：看服务窗口之日志 ∨ 重起服务（安装目录之「启动 ／ 停止」快捷）';

/* 图标（一处 · 各态）：⛔ 散在渲点。 */
const PA_PREP_ICON = {starting:'⏳', running:'⏳', restart:'🔁', done:'✅', failed:'❌', unreachable:'⚠'};

function paPrepNum(v){ return (typeof v === 'number' && isFinite(v)) ? v : null; }
function paPrepMB(n){ return (Math.round((n / 1048576) * 10) / 10) + ' MB'; }
/* ⭐ pm_1633 裁 ⒝（**一处定形** · ⛔ 二处各写）：`measured`（缓存件已见）而「总长」缺 ⇒ 辞
   「已下 X MB（总长不可量 —— 后端未给）」—— ⛔ 造数（⛔ 硬编 `79 MB`）∧ ⛔ 以 % 充字节。
   `total` 有（> 0）⇒ 返 ''（**其处自显「X / Y（%）」之条** —— 承 `1617` 令一）。
   ⚠ 语源 ＝ 后端 `download.note` 之族（`boot_progress.download_face` 之 `measured ∧ ⛔ total ⇒ note 空`）——
      **已量者须显** ⇒ 由本函补；⛔ 盖其后端之 `note`（**照实并列**）。 */
function paPrepMeasuredNote(done, total){
  const d = paPrepNum(done);
  if(d == null) return '';
  const t = paPrepNum(total);
  if(t != null && t > 0) return '';
  return '已下 ' + paPrepMB(d) + '（总长不可量 —— 后端未给）';
}
function paPrepEl(){ return document.getElementById('paPrep'); }
function paPrepVisible(){ const el = paPrepEl(); return !!(el && el.style.display !== 'none'); }

/* ⭐ **一处定形**（纯函数 · ⛔ DOM · ⛔ 各点各判）：`/health` 之回 ＋ 本地之钟 ⇒ 面之态。
   `h` ＝ `/health` 之 JSON（未答 ⇒ null）；`ctx` ＝ {elapsed_s, tries, http_status, was_ready}。
   回 {state, text, note, phase, done, total, eta_s, since_s, since_src, pct, can_bar, src}
   （`state` ∈ ready ／ starting ／ failed ／ unreachable）。 */
function paPrepView(h, ctx){
  const c  = (ctx && typeof ctx === 'object') ? ctx : {};
  const s  = (h && typeof h === 'object') ? h : null;
  const st = (s && s.startup && typeof s.startup === 'object') ? s.startup : {};
  /* ⭐ TD_1616 之真源：`/health.boot` ＝ `core/gateway/boot_progress.py` 之 `snapshot()`
     （`{state, phase, since_s, phase_since_s, phases_done, phases_total, phases[],
        failed{reason,hint}, download{measured,done_bytes,total_bytes,frac,eta_s,note}, progress}`）
     ⇒ **一处取**（唯本函读 `boot` · ⛔ 渲点 ／ 合一之判各读）∧ 缺（旧后端）⇒ 回落 `startup`（旧形）。 */
  const bt = (s && s.boot && typeof s.boot === 'object') ? s.boot : null;
  const dl = (bt && bt.download && typeof bt.download === 'object') ? bt.download : null;
  const bf = (bt && bt.failed && typeof bt.failed === 'object') ? bt.failed : null;
  const bst = bt ? String(bt.state || '') : '';
  const ready = (bst === 'ready') || (st.ready === true) || (!!s && String(s.status || '') === 'healthy');
  const phase = (bt && bt.phase) ? String(bt.phase)
              : (st.phase ? String(st.phase) : (st.status ? String(st.status) : ''));
  const done = (dl && paPrepNum(dl.done_bytes) != null) ? paPrepNum(dl.done_bytes) : paPrepNum(st.done_bytes);
  const total = (dl && paPrepNum(dl.total_bytes) != null) ? paPrepNum(dl.total_bytes) : paPrepNum(st.total_bytes);
  const eta = (dl && paPrepNum(dl.eta_s) != null) ? paPrepNum(dl.eta_s) : paPrepNum(st.eta_s);
  const bak = (bt && paPrepNum(bt.since_s) != null) ? paPrepNum(bt.since_s) : paPrepNum(st.since_s);
  const errs = Array.isArray(st.errors) ? st.errors.filter(function(x){ return String(x == null ? '' : x).trim(); }) : [];
  const raw  = String(st.state || '');
  const el   = paPrepNum(c.elapsed_s);
  const elR  = (el == null) ? null : Math.max(0, Math.round(el));
  const since = (bak == null) ? elR : Math.round(bak);
  const sinceSrc = (bak == null) ? (elR == null ? '' : 'page') : 'backend';
  const v = {state:'starting', text:'', note:'', phase:phase, done:done, total:total,
             eta_s:eta, since_s:since, since_src:sinceSrc, pct:null, can_bar:false, src:'GET /health'};
  if(!s){
    /* 未答（门未开之极境 ∨ 服务已停）—— 令四 ＋ 令二 */
    const net = (c.http_status == null);
    v.state = 'unreachable';
    v.text = c.was_ready
      ? ('服务未答（后端已不再回 /health ⇒ 可能已停' + (net ? '' : (' · HTTP ' + c.http_status)) + '）')
      : ('正在启动 ClawsJoy 服务…（后端未答' + (net ? '（连不上）' : (' · HTTP ' + c.http_status)) + '）');
    const tr = (typeof c.tries === 'number') ? c.tries : null;
    const bits = [];
    if(tr != null && !c.was_ready) bits.push('已重试 ' + tr + ' 次');
    if(elR != null) bits.push('已等 ' + elR + ' 秒');
    if(bits.length) v.text += '（' + bits.join(' · ') + '）';
    v.retry_out = (tr != null && tr >= PA_PREP_MAX_TRIES);
    v.note = c.was_ready ? PA_PREP_OUTLET : (PA_PREP_NOTE_WAIT + (v.retry_out ? (' · ' + PA_PREP_OUTLET) : ''));
    return v;
  }
  if(bst === 'failed' || bf || raw === 'failed' || raw === 'error' || errs.length){
    v.state = 'failed';
    const why = (bf && bf.reason) ? String(bf.reason)
              : (errs.length ? String(errs[0]) : (raw ? ('（后端态 ' + raw + ' · 后端未给因）') : '（后端未给因）'));
    v.text = '准备失败：' + why;
    v.note = ((bf && bf.hint) ? (String(bf.hint) + ' · ') : '') + PA_PREP_OUTLET;
    return v;
  }
  if(ready){ v.state = 'ready'; v.text = '已就绪（后端已可用）'; return v; }
  /* ⭐ `/health.boot` 在（TD_1616）⇒ 依之显「步 ＋ 字节 ＋ 时长」（谁有显谁 · ⛔ 造数 ／ ⛔ 以 % 充字节）。 */
  if(bt){
    const dN = paPrepNum(bt.phases_done), tN = paPrepNum(bt.phases_total);
    const _e2 = (since == null) ? '' : ('已等 ' + since + ' 秒' + (sinceSrc === 'page' ? '（本页计时 · 后端未给已耗）' : ''));
    const _ph2 = PA_PREP_PHASE[phase] || (phase ? ('当前步骤：' + phase) : '正在准备（后端未给步骤）');
    let t2 = '正在准备…（' + _ph2;
    if(total != null && total > 0 && done != null){
      v.can_bar = true;
      v.pct = Math.max(0, Math.min(100, Math.floor((done / total) * 100)));
      t2 += ' · 已下 ' + paPrepMB(done) + ' / ' + paPrepMB(total) + '（' + v.pct + '%）';
      if(eta != null) t2 += ' · 约还需 ' + Math.round(eta) + ' 秒';
      else if(_e2) t2 += ' · ' + _e2;
      if(dN != null && tN) t2 += ' · 步 ' + dN + '/' + tN;
    } else {
      const _pr2 = paPrepNum(bt.progress);
      const mn = paPrepMeasuredNote(done, total);
      if(mn) t2 += ' · ' + mn;
      if(_pr2 != null){ v.can_bar = true; v.pct = Math.max(0, Math.min(100, Math.round(_pr2))); }
      if(dN != null && tN) t2 += ' · 步 ' + dN + '/' + tN + ((v.pct == null) ? '' : ('（' + v.pct + '%）'));
      else if(_pr2 != null) t2 += ' · 后端步进度 ' + Math.round(_pr2) + '%（⛔ 字节不可量 —— 后端未给 done ／ total' + (mn ? ' · 已下者见上' : '') + '）';
      if(_e2) t2 += ' · ' + _e2;
      if(dl && dl.note) t2 += ' · ' + String(dl.note);
      if(v.pct == null && !_e2 && !mn) t2 += ' · 进度不可量（后端未给 done ／ total ／ 已耗）';
    }
    v.text = t2 + '）';
    v.note = PA_PREP_NOTE_WAIT;
    return v;
  }
  const ph = PA_PREP_PHASE[phase] || (phase ? ('当前步骤：' + phase) : '正在准备（后端未给步骤）');
  const _elTxt = (since == null) ? '' : ('已等 ' + since + ' 秒' + (sinceSrc === 'page' ? '（本页计时 · 后端未给已耗）' : ''));
  const _pr = paPrepNum(st.progress);
  let t = '正在准备…（' + ph;
  if(total != null && total > 0 && done != null){
    v.can_bar = true;
    v.pct = Math.max(0, Math.min(100, Math.floor((done / total) * 100)));
    t += ' · 已下 ' + paPrepMB(done) + ' / ' + paPrepMB(total) + '（' + v.pct + '%）';
    if(eta != null) t += ' · 约还需 ' + Math.round(eta) + ' 秒';
    else if(_elTxt) t += ' · ' + _elTxt;
  } else {
    if(_elTxt) t += ' · ' + _elTxt;
    if(_pr != null) t += ' · 后端步进度 ' + Math.round(_pr) + '%（⛔ 字节不可量 —— 后端未给 done ／ total）';
    else if(!_elTxt) t += ' · 进度不可量（后端未给 done ／ total ／ 已耗）';
  }
  v.text = t + '）';
  v.note = PA_PREP_NOTE_WAIT;
  return v;
}

/* 渲（**唯此一处**写 `#paPrep`）—— 幂等：⛔ 加节点 · 唯改文本 ／ 宽 ／ display。 */
function paPrepRender(v){
  const el = paPrepEl(); if(!el || !v) return v;
  el.setAttribute('data-state', v.state);
  el.style.display = (v.state === 'ready') ? 'none' : '';
  const ic = document.getElementById('paPrepIc');
  if(ic) ic.textContent = PA_PREP_ICON[v.state] || '⚠';
  const tx = document.getElementById('paPrepTx'); if(tx) tx.textContent = String(v.text || '');
  const bar = document.getElementById('paPrepBar');
  if(bar){
    bar.style.display = v.can_bar ? '' : 'none';
    const fill = bar.firstElementChild;
    if(fill && v.can_bar) fill.style.width = String(v.pct) + '%';
  }
  const nt = document.getElementById('paPrepNote'); if(nt) nt.textContent = String(v.note || '');
  return v;
}

/* 轮询之骨（一处）：t0 ／ 末回 ／ 试数 ／ 钟 —— ⛔ 前端缓存之假态（F5 须复现同态 · 令五）。 */
const paPrepRun = {started:false, t0:0, h:null, http:null, tries:0, miss:0,
                   wasReady:false, mode:'', poll:null, tick:null, last:null};

/* ⭐⭐ pm_1621 §二.4（要 · **一处定形**）：**一幅**横幅显二源之态 —— 「更新之态」∨「起服之态」
   （⛔ 二套面 · 承 pm_1621 §一.3）。序（高 ⇒ 低）：
     更新之「失败」⇒「需重启」⇒「进行中（下载 ／ 校验 ／ 备份 ／ 替换）」⇒「完成」
     ⇒ 起服之「失败」⇒「准备中」⇒「未答」。
   ⚠ 更新之「未答 ／ 已是最新 ／ 有新版」**⛔ 占**横幅（其位 ＝ 顶栏之版行 `#paVerRow`）——
     否则首屏恒挂一条非等待之语（承「凡等待必有提示」之反：⛔ 无等待亦挂）。 */
const PA_UPD_BUSY = {downloading:1, verifying:1, backing_up:1, replacing:1};
let paPrepUpd = null;   /* 更新面之末回（由 update.js 之 paPrepFeedUpdate 投 · ⛔ 本件自取） */
function paPrepFeedUpdate(v){ paPrepUpd = (v && typeof v === 'object') ? v : null; paPrepPaint(); }
function paPrepMerge(a, b){
  const u = (b && typeof b === 'object') ? b : null;
  if(u){
    if(u.state === 'failed') return u;
    if(u.state === 'restart') return u;
    if(u.state === 'running' && PA_UPD_BUSY[u.phase]) return u;
    if(u.state === 'done') return u;
  }
  return a;
}

function paPrepPaint(){
  const v = paPrepView(paPrepRun.h, {elapsed_s:(Date.now() - paPrepRun.t0) / 1000,
        tries:paPrepRun.tries, http_status:paPrepRun.http, was_ready:paPrepRun.wasReady});
  paPrepRun.last = v;
  const face = paPrepMerge(v, paPrepUpd);   /* 二源 ⇒ 一处判（⛔ 二套面） */
  paPrepRender(face);
  return face;
}
function paPrepSetInterval(ms, mode){
  if(paPrepRun.mode === mode) return;
  if(paPrepRun.poll) clearInterval(paPrepRun.poll);
  paPrepRun.mode = mode;
  paPrepRun.poll = setInterval(paPrepFetch, ms);
}
async function paPrepFetch(){
  let st = 0, h = null;
  try{
    const r = await fetch(((typeof API !== 'undefined') ? API : '') + '/health', {cache:'no-store'});
    st = (r && r.status) ? r.status : 0;
    if(r && r.ok){ try{ h = await r.json(); }catch(e){ h = null; } }
  }catch(e){ st = 0; h = null; }
  paPrepRun.h = h; paPrepRun.http = h ? null : (st || null);
  paPrepRun.tries += 1;
  if(h === null && paPrepRun.wasReady){
    /* 曾就绪 ⇒ 单次未答 ⛔ 即报（免抖）；连缺 2 次方显（令二之「服务已停」） */
    paPrepRun.miss += 1;
    if(paPrepRun.miss < 2){ paPrepRender({state:'ready'}); return paPrepRun.last; }
  }
  const v = paPrepPaint();
  if(v.state === 'ready'){
    paPrepRun.miss = 0;
    if(!paPrepRun.wasReady) paPrepRun.wasReady = true;
    paPrepSetInterval(PA_PREP_WATCH_MS, 'watch');
    return v;
  }
  if(!paPrepRun.wasReady && paPrepRun.tries >= PA_PREP_MAX_TRIES){
    paPrepSetInterval(PA_PREP_WATCH_MS, 'idle');   /* 有界 ⇒ 停取数（横幅留「去处」· 钟仍跳） */
  }
  return v;
}
function paPrepTickClock(){ if(paPrepVisible()) paPrepPaint(); }
function paPrepBegin(){
  if(paPrepRun.started) return;                    /* 幂等：⛔ 二次起（免双钟 ／ 双轮询） */
  paPrepRun.started = true; paPrepRun.t0 = Date.now();
  paPrepRun.tick = setInterval(paPrepTickClock, PA_PREP_TICK_MS);
  paPrepFetch();
  paPrepSetInterval(PA_PREP_POLL_MS, 'fast');
}
try{ window.paPrepView = paPrepView; window.paPrepRender = paPrepRender;
     window.paPrepPaint = paPrepPaint; window.paPrepBegin = paPrepBegin;
     window.paPrepFetch = paPrepFetch; window.paPrepRun = paPrepRun;
     window.PA_PREP_PHASE = PA_PREP_PHASE; window.paPrepMerge = paPrepMerge;
     window.paPrepFeedUpdate = paPrepFeedUpdate; window.paPrepUpd = function(){ return paPrepUpd; }; }catch(e){}
/* 自起（⛔ 候 boot.js —— 首屏须「JS 一跑即显」· 承令一「⛔ 白屏」之反）。 */
if(document.readyState === 'loading'){ document.addEventListener('DOMContentLoaded', paPrepBegin); }
else { paPrepBegin(); }
