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
/* ⭐⭐ pm_1693 §四.2 裁（**量级自适应 · 一处定形**）：昔之 `x MB`（一位小数）⇒ `16978 B` 渲「约 0 MB」
   ⇒ **看着像「什么都没有」**（用户会误判 —— 承「面须唯人话」）⇒ 今：
     `≥ 1 MB` ⇒ `X.X MB`（一位小数）／ `≥ 1 KB` ⇒ `N KB`（整数）／ 否则 ⇒ `N B`（整数）；
     **`0` ∨ 非数 ⇒ 「未知」**（**⛔ 书「0」** —— 「0 B」＝「什么都没有」之误读 · 承「未知 ⛔ 充知」）。
   ⚠ 本函为 `startup.js` ／ `update.js` **共用**（⛔ 二处各写 · 齿在）。 */
function paPrepMB(n){
  const v = paPrepNum(n);
  if(v == null || v <= 0) return '未知';
  if(v >= 1048576) return (Math.round((v / 1048576) * 10) / 10) + ' MB';
  if(v >= 1024) return Math.round(v / 1024) + ' KB';
  return Math.round(v) + ' B';
}
/* ⭐ pm_1633 裁 ⒝ ＋ pm_1638 裁（**去重**）（**一处定形** · ⛔ 二处各写）：`measured`（缓存件已见）
   而「总长」缺 ⇒ **读数归前端 ∧ 「由」归后端**（⛔ 二音 ∧ ⛔ 无声）：
     ⒜ `note` 非空 ⇒ 本函出「已下 X MB · <note 之逐字>」（后端之辞照实并列 —— 前端 ⛔ 再造其由）；
     ⒝ `note` 空（后端未给 ⇒ 回落）⇒ 本函补**前端之辞**（读数 ＋ 其由 —— 见下行之字面）。
   `total` 有（> 0）⇒ 返 ''（**其处自显「X / Y（%）」之条** —— 承 `1617` 令一）。
   ⛔ 造数（⛔ 硬编 `79 MB`）∧ ⛔ 以 % 充字节。
   ⚠ 已用 `note` ⇒ 调用处 ⛔ 再并列（`dln && !mn` —— 防二音）；`measured=false` 之由（`note` 非空
      而 ⛔ 本函所辖）⇒ 仍由调用处照实并列。 */
function paPrepMeasuredNote(done, total, note){
  const d = paPrepNum(done);
  if(d == null) return '';
  const t = paPrepNum(total);
  if(t != null && t > 0) return '';
  const n = (note == null) ? '' : String(note).trim();
  if(n) return '已下 ' + paPrepMB(d) + ' · ' + n;
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
      const dln = (dl && dl.note) ? String(dl.note) : '';
      const mn = paPrepMeasuredNote(done, total, dln);
      if(mn) t2 += ' · ' + mn;
      if(_pr2 != null){ v.can_bar = true; v.pct = Math.max(0, Math.min(100, Math.round(_pr2))); }
      if(dN != null && tN) t2 += ' · 步 ' + dN + '/' + tN + ((v.pct == null) ? '' : ('（' + v.pct + '%）'));
      else if(_pr2 != null) t2 += ' · 后端步进度 ' + Math.round(_pr2) + '%（⛔ 字节不可量 —— 后端未给 done ／ total' + (mn ? ' · 已下者见上' : '') + '）';
      if(_e2) t2 += ' · ' + _e2;
      if(dln && !mn) t2 += ' · ' + dln;   /* 唯本函 ⛔ 用者（measured=false 之由等）照实并列 —— ⛔ 二音 */
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
/* ⭐⭐ pm_1808 §二.3（要）：横幅之**终态** ⛔ 长挂 —— `done` 之「显报窗」（`update.js` 之
   `PA_UPD_RECENT_S` ＝ 3600 s · 承 pm_1693 §四.3）⛔ 动；本处只加**面之自动退**：终态入屏 ⇒
   逾 `PA_PREP_TERM_HOLD_MS` ⇒ 自隐（其数仍在 `#paVerRow` 与折叠处 ⇒ ⛔ 丢信息）。
   一手之证（PM · 老板屏）：更新毕（约 00:48）四十余分钟仍挂「✅ 更新已完成 · 已就绪」。
   一处定形：本阈唯此一处（⛔ 散数）。 */
const PA_PREP_TERM_HOLD_MS = 20000;
let paPrepTermT = null;
/* ⭐⭐ pm_1813 §三（要 · 一手逮）：上版之阈**形同虚设** —— 本页之钟（`paPrepTickClock` · 1 s）每跳
   皆重渲 ⇒ 旧形「每次入此支即重设钟」⇒ **钟恒被重置 · 终态永不自退**（我一手：更新毕于 00:48，
   至 01:50 仍挂「✅ 更新已完成 · 已就绪」，而其 `data-state` 正 ＝ `done`）。
   ⇒ 治：阈之起算唯取**终态首次入屏之刻**（`paPrepTermAt` · 一处定形）；重渲只**读**它，⛔ 重置。
   ⚠ 逾阈之判**每渲皆查**（钟被环境所扰亦不失退 —— ⛔ 只靠 `setTimeout`）。 */
let paPrepTermAt = 0;
function paPrepRender(v){
  const el = paPrepEl(); if(!el || !v) return v;
  el.setAttribute('data-state', v.state);
  el.style.display = (v.state === 'ready') ? 'none' : '';
  /* pm_1808 §二.3 ／ pm_1813 §三：终态（done）⇒ 逾阈自退；非终态 ⇒ 清账 ＋ 撤钟（免误隐在办之相）。 */
  if(v.state === 'done'){
    if(!paPrepTermAt) paPrepTermAt = Date.now();          /* 终态**首次**入屏 ⇒ 起算（⛔ 重渲重置） */
    const _left = PA_PREP_TERM_HOLD_MS - (Date.now() - paPrepTermAt);
    if(_left <= 0){ el.style.display = 'none'; }
    else if(!paPrepTermT){
      paPrepTermT = setTimeout(function(){ paPrepTermT = null;
        const _e2 = paPrepEl(); if(_e2) _e2.style.display = 'none'; }, _left);
    }
  } else {
    paPrepTermAt = 0;
    if(paPrepTermT){ clearTimeout(paPrepTermT); paPrepTermT = null; }
  }
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
/* ⭐⭐ pm_1693 §四.1 裁（**准改**）：⭐ **`running` 须占横幅** —— 更新乃长时之等待（数秒至数十秒 ∧ 其间服会停）
   ⇒ 承「凡等待必有提示 ＋ 进度 ＋ 时长」（**唯版行 ＋ 按钮 ⛔ 够**）。
   ⚠ **二控**（pm 裁 · ⛔ 越）：**唯增 `running`** —— `idle` ／ `done` ／ `failed` **⛔ 增**（后二之占横幅乃
     `paPrepMerge` 之下二支 —— **既有之支** · pm_1693 §一.4 所认之七景 ⒟⒠ ⇒ 与本表**无涉**：本表唯「相位」）。
   ⚠ 本表 ＝ **更新之相位**（⛔ 起服之相位 —— 起服之相在 `PA_PREP_PHASE`）⇒ **二表 ⛔ 交**（正反控之齿在）。 */
const PA_UPD_BUSY = {running:1, downloading:1, verifying:1, backing_up:1, replacing:1};
let paPrepUpd = null;   /* 更新面之末回（由 update.js 之 paPrepFeedUpdate 投 · ⛔ 本件自取） */
function paPrepFeedUpdate(v){ paPrepUpd = (v && typeof v === 'object') ? v : null; paPrepPaint(); }
let paPrepFb = null;    /* 反馈面之末回（由 feedback.js 之 paPrepFeedFeedback 投 · ⛔ 本件自取 · pm_1635 §一.3） */
function paPrepFeedFeedback(v){ paPrepFb = (v && typeof v === 'object') ? v : null; paPrepPaint(); }
function paPrepMerge(a, b, c){
  const u = (b && typeof b === 'object') ? b : null;
  if(u){
    if(u.state === 'failed') return u;
    if(u.state === 'restart') return u;
    if(u.state === 'running' && PA_UPD_BUSY[u.phase]) return u;
    if(u.state === 'done') return u;
  }
  /* ⭐ pm_1635 §一.3（三面 ⇒ **一幅横幅** · ⛔ 三横幅）：反馈之「成 ／ 败」＝ **最低**优先级 ——
     唯「起服已就绪（横幅本应收）」时方占 ⇒ ⛔ 凌于起服之「准备中 ／ 失败」（其判在上）∧
     ⛔ 凌于更新之诸态（上列已判）⇒ 免「更新要重启 ∧ 一条留言回执盖之」。 */
  const f = (c && typeof c === 'object') ? c : null;
  if(f && f.state && a && a.state === 'ready') return f;
  return a;
}

function paPrepPaint(){
  const v = paPrepView(paPrepRun.h, {elapsed_s:(Date.now() - paPrepRun.t0) / 1000,
        tries:paPrepRun.tries, http_status:paPrepRun.http, was_ready:paPrepRun.wasReady});
  paPrepRun.last = v;
  const face = paPrepMerge(v, paPrepUpd, paPrepFb);   /* 三源 ⇒ 一处判（⛔ 三套面 · pm_1635 §一.3） */
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
try{ window.paPrepFeedFeedback = paPrepFeedFeedback;
     window.paPrepFb = function(){ return paPrepFb; }; }catch(e){}
/* 自起（⛔ 候 boot.js —— 首屏须「JS 一跑即显」· 承令一「⛔ 白屏」之反）。 */
if(document.readyState === 'loading'){ document.addEventListener('DOMContentLoaded', paPrepBegin); }
else { paPrepBegin(); }
