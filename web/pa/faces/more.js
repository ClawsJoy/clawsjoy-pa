/* ClawsJoy PA v3 · 「更多 ▾」折叠收纳所（CW b2a5182 · 承 pm_997 §四 ／ pm_998 §二格① · 2026-10-04）
   收纳：① 做（轨迹 ／ 产出 ／ 文件）② 控（工具 ／ 模式 ／ 常驻）③ 设（系统 ／ 设置 ／ 私面）。
   口径：被折叠者皆**一步可达**（⛔ 丢功能）；同一面 ⛔ 平铺 ≥ 5 项（F6⑥ 首屏 ／ F6⑦ 抽屉内）。
   产出取**真源** GET /v9/plans/list（⛔ 编数 · L76）。 */

function paMore(open){
  const el = document.getElementById('paMorePanel'); if(!el) return;
  if(open){ el.removeAttribute('hidden'); if(typeof paLoadPlans === 'function') paLoadPlans(); }
  else { el.setAttribute('hidden',''); }
}
function paSettings(){
  paMore(true);
  const g = document.getElementById('paMoreGrpSet'); if(g) g.setAttribute('open','');   /* 三组默认收起 ⇒ 直达须先开组 */
  setTimeout(function(){
    const s = document.getElementById('paMoreSettings');
    if(s && s.scrollIntoView){ try{ s.scrollIntoView({block:'start'}); }catch(e){} }
  }, 60);
}

/* —— 产出 · 计划资产（源 GET /v9/plans/list · 真数据）＋ 长列表「能找」（承 pm_999 §二.2）——
   > 8 项之列表须有「搜索 ／ 筛选 ／ 分组」⇒ 本列表取「搜索 ＋ 种类筛」；
   计数行如实（显示 ／ 命中 ／ 共）⇒ ⛔ 假绿（L76：界面只读真读数）。全量存 paPlanAll（v3 专用）。 */
let paPlanAll = null;
/* ⭐ pm_刀16p §〇：「产出」面之 `GET /v9/plans/list` 已载 **`view=real|test|all`**
   （counts{before, real, test_trace}）⇒ ⭐ **默认 `view=real`**（否则 canary 测试痕满屏 · 承 pm_刀12p §一.2）。
   ⭐ 空 ≠ 缺 分显：view=real 而 0 项 ∧ test_trace>0 ⇒ 明标「真产出 0 · 测试痕 N 已滤」（⛔ 以空充缺）。 */
let paPlanView = 'real';
let paPlanCounts = null;
function paPlanViewSet(v){
  paPlanView = (['real','test','all'].indexOf(String(v)) >= 0) ? String(v) : 'real';
  return paLoadPlans();
}
/* ⛔ 动 pa.html（内容件）⇒ 三态选择器由本件**注入** #paPlanQ 之侧（幂等）。 */
function paPlanViewMount(){
  const q = document.getElementById('paPlanQ'); if(!q || !q.parentNode) return null;
  if(document.getElementById('paPlanView')) return document.getElementById('paPlanView');
  const sel = document.createElement('select');
  sel.id = 'paPlanView';
  sel.setAttribute('onchange', 'paPlanViewSet(this.value)');
  /* ⭐ pm_2095 裁⒟：屏上唯人话 ∧ 取值名（view=…）⇒ 本择之 `title`（可查 · ⛔ 丢真源 · 同 #paTaskLedgerSrc 之族）。 */
  sel.setAttribute('title', '取值：view=real ／ view=test ／ view=all');
  sel.innerHTML = '<option value="real">真产出</option>'
    + '<option value="test">测试痕</option>'
    + '<option value="all">全部</option>';
  sel.value = paPlanView;
  q.parentNode.insertBefore(sel, q.nextSibling);
  return sel;
}
function paPlanKinds(assets){
  const kEl = document.getElementById('paPlanKind'); if(!kEl || !assets) return;
  const cur = kEl.value || '';
  const ks = []; assets.forEach(function(a){ const k = String(a.kind || '—'); if(ks.indexOf(k) < 0) ks.push(k); });
  ks.sort();
  kEl.innerHTML = '<option value="">全部种类（' + ks.length + '）</option>'
    + ks.map(function(k){ return '<option value="' + paEsc(k) + '">' + paEsc(k) + '</option>'; }).join('');
  if(cur){ kEl.value = cur; if(kEl.value !== cur) kEl.value = ''; }
}
function paPlanHit(assets, q, kind){
  const ql = String(q || '').trim().toLowerCase();
  return assets.filter(function(a){
    if(kind && String(a.kind || '—') !== kind) return false;
    if(!ql) return true;
    const blob = [a.kind, a.session_id, a.file, a.ts].map(function(v){ return String(v == null ? '' : v); }).join(' ').toLowerCase();
    return blob.indexOf(ql) >= 0;
  });
}
function paPlanFilter(){ return paRenderPlans(); }
function paRenderPlans(){
  const box = document.getElementById('paMorePlans'); if(!box) return null;
  const srcEl = document.getElementById('paMorePlansSrc');
  const qEl = document.getElementById('paPlanQ'), kEl = document.getElementById('paPlanKind');
  const cntEl = document.getElementById('paPlanCnt');
  if(paPlanAll === null){
    if(srcEl){ srcEl.textContent = '来源：本机计划清单 · 未知（本机没应答）'; srcEl.title = '源：GET /v9/plans/list?view=' + paPlanView + ' · 未应答（照实 · 不编）'; }
    box.innerHTML = '<div>未知（后端未应答）</div>';
    /* ⭐ pm_1052 §二（甲）：未应答之义 ≠ 0 行之义 ⇒ ⛔ 一符套两义（承 L103）。
       本处义 ＝ 未应答 ⇒ 人话（原炸裸 「—」）。 */
    if(cntEl) cntEl.textContent = '未知（本机没应答）';
    return null;
  }
  const hit = paPlanHit(paPlanAll, qEl ? qEl.value : '', kEl ? kEl.value : '');
  const shown = hit.slice(0, 20);
  const pc = paPlanCounts || {};
  if(srcEl){
    srcEl.textContent = '来源：本机计划清单 · 共 ' + paPlanAll.length + ' 项（本页最多显示 20）'
      + ((pc.real != null) ? (' · 本机计数：真产出 ' + pc.real + ' ／ 测试痕 ' + pc.test_trace + ' ／ 全部 ' + pc.before) : ' · 计数未给（照实）');
    srcEl.title = '源：GET /v9/plans/list?view=' + paPlanView + ' · counts 键：real ／ test_trace ／ before';
  }
  if(!shown.length){
    /* ⭐ 空 ≠ 缺：真产出为 0 而测试痕非 0 ⇒ 明标「已滤」（⛔ 以空充缺） */
    const hint = (paPlanView === 'real' && pc.test_trace)
      ? ('真产出 0 项 · 测试痕 ' + pc.test_trace + ' 项已滤（切「测试痕」可见）')
      : (paPlanAll.length ? '筛选后 0 项（清空筛词即复原）' : '0 项（本机没这项）· 空态');
    box.innerHTML = '<div>' + hint + '</div>';
  } else {
    box.innerHTML = shown.map(function(a){
      const ts = (a.ts == null || a.ts === '') ? '—' : (PA_STAMP.fmt(a.ts) || '—');
      return '<div class="p" title="' + paEsc((a.session_id || '—') + ' · ' + (a.file || '')) + '">'
        + '<span class="k">' + paEsc(a.kind || '—') + '</span><span class="s">' + ts + '</span></div>';
    }).join('');
  }
  const st = {shown: shown.length, hit: hit.length, total: paPlanAll.length};
  if(cntEl) cntEl.textContent = '显示 ' + st.shown + ' ／ 命中 ' + st.hit + ' ／ 共 ' + st.total;
  return st;
}
async function paLoadPlans(){
  const box = document.getElementById('paMorePlans'); if(!box) return null;
  paPlanViewMount();
  let d = null;
  try{ const r = await fetch(API + '/v9/plans/list?view=' + encodeURIComponent(paPlanView), {cache:'no-store'}); if(r.ok) d = await r.json(); }catch(e){}
  paPlanAll = (d && Array.isArray(d.assets)) ? d.assets : null;
  paPlanCounts = (d && d.counts && typeof d.counts === 'object') ? d.counts : null;
  if(paPlanAll) paPlanKinds(paPlanAll);
  return paRenderPlans();
}

/* —— 模式条（MODES 8 项）：分两行 × ≤ 4（承 pm_998 §二格① 末句 · F6⑦）——
   renderModes（shell.js）写入 8 枚 button；此处**只重组容器**（⛔ 改 shell.js 本体 · ⛔ 改模式语义）。
   观察器幂等：首子元素已是 .mrow ⇒ 跳过（⛔ 死循环）。 */
function paGroupModes(){
  const box = document.getElementById('modes'); if(!box) return;
  const kids = Array.prototype.slice.call(box.children);
  if(!kids.length) return;
  if(kids[0] && kids[0].classList && kids[0].classList.contains('mrow')) return;
  const rows = [];
  for(let i = 0; i < kids.length; i += 4){ rows.push(kids.slice(i, i + 4)); }
  box.innerHTML = '';
  rows.forEach(function(r){
    const d = document.createElement('div'); d.className = 'mrow';
    r.forEach(function(k){ d.appendChild(k); });
    box.appendChild(d);
  });
  return rows.length;
}
(function(){
  function go(){ try{ paGroupModes(); }catch(e){} }
  if(document.readyState === 'loading'){ document.addEventListener('DOMContentLoaded', go); }
  else { go(); }
  setTimeout(go, 300); setTimeout(go, 1200);
  const box = document.getElementById('modes');
  if(box && window.MutationObserver){
    try{ new MutationObserver(go).observe(box, {childList:true}); }catch(e){}
  }
})();

/* —— 界面态读数（v3 专用重排 ＋ 缩措辞 ＋ 警号）：承 pm_998 §二格② · pm_1006 §二 ——
   病：status.js 之 paLoadUiState 原文过长 ⇒ 「本地在 ／ 远端在」被省略号吞（实测 1280 屏）。
   治法：**采样刻置首**（⛔ 被截）＋ **缩修饰语**（「（快照 · ⛔ 实时）」⇒「（快照）」）；⛔ 省字段。
   一行须全可见：采样刻 ／ 显存 ／ 已载 ／ Forever ／ 本地在 ／ 远端在 ／ 源。
   ⭐ pm_1006 §二：`Forever` 取 **`N`（条数）**（名入 title · 可回指）＋ **警色**（N ≥ 1 ⇒ amber · 显存近枯 ⇒ red）
      其由：N ≥ 1 ＝ 有模型被永久钉显存（警号）；⛔ 只缩品牌（Forever 会变长 ⇒ 治表）。
   ⛔ 改 status.js 本体（旧页共用）；本包装仅 v3 页载入。 */
/* ⭐ 能力线（承 pm_1007 §一）：判据须有**可操作含义** ⇒ 取「出图（3.0–3.3 GB）还能不能跑」之上限。
   ⛔ 取圆整百分数（10%）：`看着差不多` 非行动线（承 L82 之族）。
   ⇒ 具名常量 ＋ 注释其由（承 L61：⛔ 写死清单 ⇒ 现读派生 ＋ 正面控制常量）｜值须报 PM。
   值 ＝ 3.3 GB 之 MiB 记法：3.3 × 1024 = 3379.2 ⇒ 取 3379 MiB（与快照 free 同量级 · 快照记作 MB）。 */
const PA_GPU_LINE_MIB = 3379;
/* 档（单源 · 承 L83）：red ＝ N ≥ 1 ∧ free < 能力线 ⇒ 出图 ⛔ 可能（警）；
   amber ＝ N ≥ 1 ∧ free ≥ 能力线 ⇒ 钉着但尚够（提示）；none ＝ N = 0 ⇒ 无色；
   unknown ＝ Forever 非数组 ∨ free 非数 ⇒ 显「未知」（⛔ 猜）；⛔ 无色（与「一切正常」无别 ＝ 假绿）· ⛔ 红（未证有钉 ＝ 假警报）。 */
function paGpuWarnClass(ui){
  const arr = (ui && Array.isArray(ui.Forever)) ? ui.Forever : null;
  if(!arr) return 'unknown';
  if(!arr.length) return 'none';
  const vr = (ui && ui['显存']) || {};
  const fre = Number(vr.free);
  if(!isFinite(fre)) return 'unknown';
  return (fre < PA_GPU_LINE_MIB) ? 'red' : 'amber';
}
function paGpuWarnColor(ui){
  const c = paGpuWarnClass(ui);
  if(c === 'none') return '';
  return (c === 'red') ? 'var(--red)' : 'var(--amber)';
}
function paGpuWarnWhy(ui){
  const c = paGpuWarnClass(ui);
  const vr = (ui && ui['显存']) || {};
  if(c === 'unknown') return '｜显存警号：未知（Forever 非数组 ∨ free 非数）⇒ ⛔ 猜';
  if(c === 'none') return '｜显存警号：无（Forever 0 项）';
  return '｜⚠ 显存警号：' + (c === 'red' ? '红' : '黄') + '（free ' + vr.free + ' MiB '
    + (c === 'red' ? '<' : '≥') + ' 能力线 ' + PA_GPU_LINE_MIB + ' MiB · 出图 3.0–3.3 GB）';
}

/* ⭐ 读数须自动跟上刷新（承 pm_1007 §二 · 取 ⒝ 轮询案）：每分钟**只读**轮询快照件
   （GET pa/ui_state.json · 静态件 · 160 B）⇒ 技总器 --落 一刷 ⇒ 屏上即变（⛔ 须用户手动重载）。
   守：采样刻照留（L76）｜轮询**只读静态件**（⛔ 轮询后端 API）｜⛔ 因轮询改任何状态｜
   页隐藏 ⇒ 跳过（省电）｜回前台 ⇒ 即刻补一次（visibilitychange · ⛔ 等 60 s）。 */
const PA_UI_STATE_POLL_MS = 60000;
(function(){
  let busy = false;
  async function tick(){
    if(busy || document.hidden) return;
    if(!document.getElementById('paUiStateRow')) return;
    if(typeof window.paLoadUiState !== 'function') return;
    busy = true;
    try{
      const d = await window.paLoadUiState();     /* 只读静态件 · 无副作用：仅 fetch ＋ 重画该行 */
      if(d){
        try{ if(typeof paSelfUiCache !== 'undefined') paSelfUiCache = d; }catch(e){}
        try{ if(typeof paPermGpuWarnRender === 'function') paPermGpuWarnRender(); }catch(e){}
      }
    }catch(e){}
    busy = false;
  }
  setInterval(tick, PA_UI_STATE_POLL_MS);
  /* ⭐ 回前台 ⇒ 即刻补齐（⛔ 等下一轮 60 s）：隐藏态不轮询（省电）· 转可见时补一次（仍只读静态件）。 */
  document.addEventListener('visibilitychange', function(){ if(!document.hidden) tick(); });
})();
/* ⭐ 可点之「原文」折叠（承 pm_1018 §二 ⓜ.2）：拆下之技术串 ⇒ 默认隐 · 展开可见（⛔ 丢信息）。 */
/* ⭐ pm_1045 §三：远端**三态**（真源 ＝ 快照之「远端态」／「远端因」；键归后端 ⇒ ⛔ 我自造 · 承 L102）。
   ⛔ 单以布尔「远端在」判 —— 布尔丢三态（用户 ⛔ 知「为何 ✗」）。
   ⚠ 键缺（旧快照）⇒ 「未知」 ＋ 入「缺键」名单（⛔ 猜 ／ ⛔ 静默退回布尔）。
   单源（承 L83）：顶栏 ／ 来源面（sources.js）／ 自述依据块（selfdesc.js）三处皆调此处。
   ⚠ 辨义（承 pm 1367 §二.3）：此处之「远端」＝ **宿主远端机**（快照之「远端态」）⇒ 与模型供应商
      `remote:deepseek`（＝租算力 · 见 paProvRowHtml）**非一物** ⇒ 二名分列（⛔ 一名二义）。 */
function paRemoteTri(d){
  var t = (d && typeof d['远端态'] === 'string') ? String(d['远端态']).trim() : '';
  return (t === '未配' || t === '配了但不通' || t === '配了且通') ? t : '';
}
function paRemoteText(d){
  var t = paRemoteTri(d);
  if(t === '配了且通')   return '✓通';
  if(t === '配了但不通') return '✗不通';
  if(t === '未配')       return '—未配';
  return '未知';
}
function paRemoteWhy(d){
  var w = (d && typeof d['远端因'] === 'string') ? String(d['远端因']).trim() : '';
  return w || '未知';
}
window.paRemoteTri = paRemoteTri; window.paRemoteText = paRemoteText; window.paRemoteWhy = paRemoteWhy;

function paUiEngDetails(raw){
  try{
    var d = document.createElement('details');
    d.className = 'eng';
    d.innerHTML = '<summary>原文</summary><div class="engbody"></div>';
    d.querySelector('.engbody').textContent = String(raw == null ? '' : raw);
    return d;
  }catch(e){ return null; }
}
(function(){
  var orig = window.paLoadUiState;
  if(typeof orig !== 'function') return;
  window.paLoadUiState = async function(){
    var d = await orig.apply(this, arguments);
    /* ⭐⭐ 令 1789 §五：本行 **⛔ 入 `PA_STALE` 射程**（昔之病 · 我一手逮）——
       其「刻」＝ **服务启动时落一次**（`core/gateway/ui_state.py`：唯一写者 ＝ 服务 · 启动时落一次）
       ⇒ **天生只会越来越旧** ⇒ 服务一启、过阈（5 min）**必报「已陈旧」**；
       且「↻ 刷新」（`paRefreshLive`）**⛔ 重取此行** ⇒ 乃**永不消之假警**。
       ⛔ 以「已陈旧 · 请刷新」诱发用户点一个**不可能有效**之刷新（承「⛔ 不实之辞入屏」）。
       正解 ＝ **标其源之性**（静态）：「源为服务启动快照 · 非实时」（其文本 ／ 标题在渲处书 · 见下 `采样刻 …（服务启动时之快照）`）。 */
    try{
      var el = document.getElementById('paUiStateRow');
      /* ⭐ 快照读不到（F2 网络 ／ F3a 坏体）⇒ 用户面只留人话；「因」入 title ／ data-raw ／ 可点注记（承 pm_1018 §二 ⓜ.2 ／ pm_1012 §四 令③）。 */
      if(el && !d){
        var rawMiss = String(el.textContent || '');
        var humanMiss = '快照读不到 · 版本或暂不可用 ⇒ 本行按「未知」记（⛔ 实时读数）';
        el.textContent = humanMiss;
        el.title = rawMiss;
        el.setAttribute('data-raw', rawMiss);
        el.setAttribute('data-ui-state', 'missing');
        /* ⭐ pm_1024 §一.4 ＋ L85：未知态须与正常态视觉可分 ⇒ 着黄（⛔ 无色＝「已证无异常」） */
        el.style.color = 'var(--amber)';
        el.setAttribute('data-unknown-color', 'amber');
        if(!el.__engNote){ var dm = paUiEngDetails(rawMiss); if(dm){ el.appendChild(dm); el.__engNote = rawMiss; } }
        return d;
      }
      if(d && el){
        var vr = d['显存'] || {};
        /* ⭐ 键齐校验（承 pm_1018 §二 ⓜ.1）：缺键 ／ 类型不对 ⇒ 该字段显「未知」（⛔ 显 undefined ／ NaN）；
           并标采样刻（pm_1018 §二 我加①：「未知」是合法态 · 「undefined」不是 —— 承 L76 ／ L85）。 */
        function num2(v){ return (typeof v === 'number' && isFinite(v)) ? String(v) : '未知'; }
        function chk2(v){ return (v === undefined || v === null || v === '') ? '未知' : String(v); }
        var miss = [];
        if(!(typeof d['刻'] === 'string' && d['刻'])) miss.push('刻');
        if(!(typeof vr.free === 'number' && isFinite(vr.free))) miss.push('显存.free');
        if(!(typeof vr.total === 'number' && isFinite(vr.total))) miss.push('显存.total');
        if(!(typeof d['已载'] === 'number' && isFinite(d['已载']))) miss.push('已载');
        if(!(typeof d['本地在'] === 'boolean')) miss.push('本地在');
        if(!(typeof d['远端在'] === 'boolean')) miss.push('远端在');
        if(!paRemoteTri(d)) miss.push('远端态');   /* ⭐ pm_1045 §三：新键（旧快照无）⇒ 入缺键名单 */
        el.setAttribute('data-ui-missing', miss.join('／'));
        el.setAttribute('data-ui-state', miss.length ? 'partial' : 'ok');
        /* ⭐ 承 pm_1006 §二：取「Forever N ＋ title 全名 ＋ 警色」——
           其由：N（条数）＝ 关键读数（N ≥ 1 ＝ 有模型被永久钉显存）；名字属明细 ⇒ 入 title（可回指）。
           ⛔ 只缩品牌区 ＝ 治表：Forever 随模型数变长（承 L82 之族：须按「会变之面」设计）。
           ⚠ N 现读快照之 Forever 条目数（⛔ 前端自算 · 承 L76）。
           警色（承 pm_1007 §一 · 取能力线）：N ≥ 1 ∧ free < 3379 MiB ⇒ red；N ≥ 1 ∧ free ≥ 3379 MiB ⇒ amber。 */
        var fArr = Array.isArray(d.Forever) ? d.Forever : null;
        var fN = fArr ? fArr.length : -1;
        var fName = fArr ? (fN ? fArr.join(' / ') : '无') : '未知';   /* ⭐ pm_1064 §三（承 L132）：`Forever 0 项` ⇒ 与 `:143` 同义同词「无」（⛔ 裸 `—`） */
        var fShow = (fN < 0) ? '未知' : String(fN);   /* ⭐ pm_1053 §三 ＋ pm_1064 §三：该位惟表**数值**（同行「已载 0」同制）⇒ ⛔ 裸 `—`；`fN < 0` 已另支「未知」⇒ 无三义之歧（承 L132）。⭐ `fN === 0 ? '0'` 系**空转支**（`String(0) === '0'`）⇒ 删（值不变 · 承 L136 逐条定性） */
        /* ⭐ 承 pm_1007 §一：⛔ 圆整百分数 ⇒ 取能力线；判据单源 paGpuWarnClass（承 L83）。 */
        var wcls = paGpuWarnClass(d);
        var warn = paGpuWarnColor(d);
        function yn(v){ return v === true ? '✓' : (v === false ? '✗' : '未知'); }
        function esc(x){ return String(x == null ? '' : x).replace(/[&<>"]/g, function(c){
          return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]; }); }
        /* 未知须与正常可分（承 L85）：partial ⇒ 行着黄（☝ 无色）；ok ⇒ 清色（☝ 残留）。 */
        el.style.color = miss.length ? 'var(--amber)' : '';
        el.removeAttribute('data-unknown-color');
        el.innerHTML = esc('采样刻 ' + chk2(d['刻']) + '（服务启动时之快照 · 非实时 ⇒ 刷此无效） · 显存 ' + num2(vr.free) + '/' + num2(vr.total) + ' MB · 已载 '
            + num2(d['已载']) + ' · Forever ')
          + '<b style="font-weight:600' + (warn ? (';color:' + warn) : '') + '">' + esc(fShow) + '</b>'
          + esc(' · 本地在 ' + yn(d['本地在']) + ' · 远端 ' + paRemoteText(d) + ' · 源：界面快照')
          + (miss.length ? ('<b data-unknown="1" style="font-weight:600;color:var(--amber)">'
              + esc(' · ⚠ 缺键 ' + miss.length + ' 项 ⇒ 未知') + '</b>') : '');
        el.title = '界面态快照（只读 · web/pa/ui_state.json · 由技总器 --落 写 · 快照非实时 ⇒ ⛔ 当实时读）'
          + '｜Forever 全名（' + fN + ' 项）：' + fName
          + ((fN >= 1) ? '｜⚠ 有模型被永久钉显存（keep_alive −1 哨兵）⇒ 出图（3.0–3.3 GB）此刻可能失败；处置见平台面（WSL · ⛔ 我方动）' : '')
          + paGpuWarnWhy(d)
          + '｜远端态：' + (paRemoteTri(d) || '未知（快照无「远端态」键）') + '｜远端因：' + paRemoteWhy(d);
        el.setAttribute('data-forever-n', String(fN));
        el.setAttribute('data-forever-warn', String(fN >= 1));
        el.setAttribute('data-forever-class', wcls);
        el.setAttribute('data-gpu-line-mib', String(PA_GPU_LINE_MIB));
        el.setAttribute('data-full', '采样刻 ' + (d['刻'] || '未知') + '（快照 · ⛔ 实时）· 显存 ' + vr.free + '/' + vr.total
          + ' MB · 已载 ' + d['已载'] + ' · Forever ' + fName + '（' + fN + ' 项）· 本地在 ' + d['本地在']
          + ' · 远端态 ' + (paRemoteTri(d) || '未知') + '（因 ' + paRemoteWhy(d) + '）· 源 web/pa/ui_state.json（只读）');
        el.setAttribute('data-remote-state', paRemoteTri(d) || '未知');
        /* ⭐ pm_1024 §一.4：`partial` ⇒ 缺键明细**可展开**（⛔ 丢信息 · ⛔ undefined）。 */
        try{
          var oldD = el.querySelector('details[data-unknown-detail]');
          if(oldD) oldD.parentNode.removeChild(oldD);
          if(miss.length){
            el.setAttribute('data-unknown-color', 'amber');
            var dd = paUiEngDetails('缺键明细（' + miss.length + ' 项）：' + miss.join('  ／  '));
            if(dd){ dd.setAttribute('data-unknown-detail', '1'); el.appendChild(dd); }
          }
        }catch(e){}
      }
    }catch(e){}
    return d;
  };
})();

/* —— 栏位状态复位（v3 首屏三块 ⇒ 顶栏 ／ 左栏 ／ 右栏 皆须可见）——
   drawer.js 之 paApplyPanels 会按 localStorage 之 pa_panels 加 body.hide-top 等类；
   旧页面里若曾收起顶栏 ／ 右栏 ⇒ 新页首屏会被隐藏（＝看着白）⇒ 本页复位（⛔ 改 drawer.js 本体）。 */
(function(){
  try{
    localStorage.setItem('pa_panels', JSON.stringify({left:true, right:true, top:true}));
    document.body.classList.remove('hide-top','hide-left','hide-right');
  }catch(e){}
})();

/* Esc 关闭 · 点遮罩关闭 */
document.addEventListener('keydown', function(e){ if(e.key === 'Escape') paMore(false); });
document.addEventListener('click', function(e){
  const el = document.getElementById('paMorePanel');
  if(el && !el.hasAttribute('hidden') && e.target === el) paMore(false);
});

/* —— 文件 · 长列表「能找」（承 pm_999 §二.2）—— v3 专用包装（⛔ 动共用件 faces/files.js）
   files.js 之 loadFiles 写 #fileList；此处只「读后筛」（⛔ 改其本体 ｜ ⛔ 改其数据）；
   计数行如实（显示 ／ 共）⇒ 观察器幂等（只改 style.display ⇒ ⛔ 触发 childList ⇒ ⛔ 死循环）。 */
let paFileStat = null;
function paFileFilter(){
  const box = document.getElementById('fileList'); if(!box) return null;
  const qEl = document.getElementById('paFileQ'), cntEl = document.getElementById('paFileCnt');
  const rows = Array.prototype.filter.call(box.children, function(e){
    return e.classList && e.classList.contains('fitem');
  });
  /* ⭐ pm_1052 §二（甲）：本处义 ＝ 应答但 0 行⇒ 照实报数（⛔ 裸「—」、⛔ 与「未应答」同词）。 */
  if(!rows.length){ if(cntEl) cntEl.textContent = '显示 0 ／ 共 0'; paFileStat = null; return null; }
  const ql = String((qEl && qEl.value) || '').trim().toLowerCase();
  let hit = 0;
  rows.forEach(function(r){
    const t = String(r.getAttribute('title') || r.textContent || '').toLowerCase();
    const ok = !ql || t.indexOf(ql) >= 0;
    r.style.display = ok ? '' : 'none';
    if(ok) hit++;
  });
  paFileStat = {hit: hit, total: rows.length, q: ql};
  if(cntEl) cntEl.textContent = '显示 ' + hit + ' ／ 共 ' + rows.length;
  return paFileStat;
}
(function(){
  function go(){ try{ paFileFilter(); }catch(e){} }
  const box = document.getElementById('fileList');
  if(box && window.MutationObserver){ try{ new MutationObserver(go).observe(box, {childList:true}); }catch(e){} }
  if(document.readyState === 'loading'){ document.addEventListener('DOMContentLoaded', go); } else { go(); }
  setTimeout(go, 600); setTimeout(go, 2500); setTimeout(go, 6000);
})();

/* ===== 面 A · 模型供应商（pm_1087 §三 · P0 只读上屏）＝「谁出字」
         面 B · 执行层 agent 名册（pm_1088 §二 Q0 ／ pm_1089 修正：读**既有** `/v9/pa/roster`）＝「谁干活」
   CW b2a5182 · 2026-10-05 · 唯 pa.html 载入本条 ⇒ ⛔ 动共用件一字（chat.js ／ selfdesc.js 皆未碰）。
   两令共守之界：⛔ 切换模型（候 P1）｜⛔ 连接 agent（候 Q1）｜⛔ 直连远端 ／ 直起进程 ／ 直连 agent（须过网关）
                 ｜⛔ 自动信任 ／ 自动安装｜⛔ 凭据入屏（唯布尔）｜⛔ 越域改 core/**。
   ⛔ 冒充真读数（L76）：后端无此读数 ⇒ **明标「未接」**，⛔ 以硬编表充数。
   ⛔ 自造键（L102）：键名依规格所拟（后端另件 `_to_td_034` ／ `_to_td_035`）⇒ 读具**容错**
      （多候选键 · 命中即**报所用之键**）⇒ 后端定稿后只须对齐此处**一处**。 */

/* —— 走径标（pm_1087 §三.2）：本答走哪一源 ⇒ 读数取**后端回执** · ⛔ 前端自说 —— */
/* ⭐「本机 / 远端」之二集（**一处定形**）：`paRouteFromObj` 之支 ／ 「出机」之判（红线）**共此一处**
   ⇒ ⛔ 二份字面（改一漏一 ⇒ 红线漏显 ＝ 假阴）。 */
const PA_ROUTE_REMOTE_KINDS = ['remote', 'api', '远端'];
const PA_ROUTE_LOCAL_KINDS  = ['local', 'local_model', '本机'];
function paRouteIsRemote(kind){
  return PA_ROUTE_REMOTE_KINDS.indexOf(String(kind == null ? '' : kind).trim().toLowerCase()) >= 0;
}
function paRouteIsLocal(kind){
  return PA_ROUTE_LOCAL_KINDS.indexOf(String(kind == null ? '' : kind).trim().toLowerCase()) >= 0;
}
function paRouteFromObj(v){
  if(!v || typeof v !== 'object') return '';
  const kind  = String(v.kind || v.type || v.route || '').trim().toLowerCase();
  const model = String(v.model || v.model_id || v.modelId || '').trim();
  const prov  = String(v.provider || v.provider_id || v.vendor || '').trim();
  if(!model && !prov) return '';
  if(paRouteIsLocal(kind)) return 'src: local:' + (model || '—');
  if(paRouteIsRemote(kind)) return 'src: remote:' + (prov || '—') + ':' + (model || '—');
  return 'src: ' + (prov ? (prov + ':') : '') + (model || '—') + '（kind 未给）';
}
/* 回执 ⇒ 结构化之（kind ／ model）（键之候选 ≡ `paRouteFromObj` 之面 · **一处定形**）——
   供「出机」之判（唯此二值 · ⛔ 全文 · 承 ⛔ 自造键）。 */
function paRouteMeta(v){
  if(!v || typeof v !== 'object') return {kind: '', model: ''};
  return {kind : String(v.kind || v.type || v.route || '').trim().toLowerCase(),
          model: String(v.model || v.model_id || v.modelId || '').trim()};
}
/* 串形之回执（`src: remote:prov:model` ／ `src: local:model`）⇒ kind 唯取首段 ∧ model 唯取末段；
   `—` ＝ 占位（`paRouteFromObj` 之式）⇒ 视同「后端未给」。 */
function paRouteMetaText(text){
  const s = String(text || '').replace(/^src:\s*/, '');
  const parts = s.split(':');
  const k = String(parts[0] || '').trim().toLowerCase();
  let m = String(parts.length > 1 ? parts[parts.length - 1] : '').trim();
  if(m === '—') m = '';
  if(paRouteIsRemote(k)) return {kind: 'remote', model: m};
  if(paRouteIsLocal(k))  return {kind: 'local',  model: m};
  return {kind: '', model: ''};
}
function paRouteLabel(rec){
  if(!rec || typeof rec !== 'object') return null;
  const keys = ['answer_route', 'route', 'model_route', 'router', 'answer_src'];
  for(let i = 0; i < keys.length; i++){
    const v = rec[keys[i]];
    if(v == null) continue;
    if(typeof v === 'object'){
      const t = paRouteFromObj(v);
      if(t){ const m = paRouteMeta(v); return {text: t, key: keys[i], kind: m.kind, model: m.model}; }
    }
    else {
      const s = String(v).trim();
      if(s){
        const t = (s.indexOf('src:') === 0 ? s : ('src: ' + s));
        const m = paRouteMetaText(t);
        return {text: t, key: keys[i], kind: m.kind, model: m.model};
      }
    }
  }
  const prov = rec.provider || rec.provider_id;
  const mdl  = rec.model || rec.answer_model || rec.model_id;
  if(prov || mdl){
    const t = paRouteFromObj({kind: (rec.kind || rec.answer_kind), provider: prov, model: mdl});
    if(t) return {text: t, key: 'provider/model（扁平二键）',
                  kind : String(rec.kind || rec.answer_kind || '').trim().toLowerCase(),
                  model: String(mdl || '').trim()};
  }
  return null;
}
function paRouteTake(){
  let box = null;
  try{ box = window.PASelfRouteLast || null; }catch(e){}
  try{ window.PASelfRouteLast = null; }catch(e){}   /* 一轮一清（⛔ 跨轮串标 · 承 L76） */
  return box;
}
/* 无回执 ⇒ **明标「后端未给」**；⛔ 省此标 —— 省之则用户以为「本机有据」（承 pm_1076 §三 之族）。 */
function paRouteLine(box){
  const at = (box && box.at) ? PA_STAMP.fmt(box.at) : '';
  const L  = (box && box.label) ? box.label : null;
  if(!L) return '🔌 走径：src: —（后端未给）' + (at ? (' · 采于 ' + at) : '');
  return '🔌 走径：' + L.text + '（键 ' + L.key + (at ? (' · 采于 ' + at) : '') + '）';
}
/* ⭐⭐ 「出机」之标（承 pm_1454 §一 ／ §二）：**唯**本轮经云端（`kind ∈ 远端集`）⇒ 有；
   本机模型之轮 **⛔ 上**（⛔ 恒挂）。实名**取回执**（`label.model` · ⛔ 前端硬编 ⇒ 其名由后端出）。
   缺（回执无 `model`）⇒ 「后端未给」之明标（承 `paRouteLine` 之上式 · ⛔ 空 ／ ⛔ 以猜之名充）。 */
function paLeavesLine(box){
  const L = (box && box.label) ? box.label : null;
  if(!L || !paRouteIsRemote(L.kind)) return null;
  return '本轮经云端 · 内容将出机 · 模型 ' + (String(L.model || '').trim() || '（后端未给）');
}
/* ⭐⭐ pm_1812 §二.1（主件 · 去壳）：**工程话 ⛔ 用户面** ——
   ⒝ 走径之键 ＋ ⒜ 云端之告（**原文**）⇒ 皆入**折叠**「本轮来源（技术细节）」（⛔ 删真源 · 承 pm_1012 §二）；
   ⒜ 之**人话**另出一句（唯首次 ∨ 通道切换后 · 见 `paCloudNotice`）＋ 一枚**常驻小标** `🔌 云端`。
   ⚠ 本层唯改「**怎么显示**」—— `paRouteLine` ／ `paLeavesLine` 之**逐字** ∧ kind 之二集 ∧ 探针皆一字不动
     （承「一处定形」· 旧齿之字面仍钉 · 唯位改「人话面 ⇄ 折叠面」）。 */
function paCloudBadge(box){
  const L = (box && box.label) ? box.label : null;
  return (L && paRouteIsRemote(L.kind)) ? '🔌 云端' : '';
}
function paEngLines(box){
  const L = [];
  const out = paLeavesLine(box);        /* ⒜ 原文（唯远端 ⇒ 有 · ⛔ 改字） */
  if(out) L.push(out);
  L.push(paRouteLine(box));             /* ⒝ 走径之键 */
  return L;
}
function paNoteHtml(notice){
  return notice ? ('<div class="paclnote">' + paEsc(notice) + '</div>') : '';
}
/* 折叠之壳（**一处定形** —— ⛔ 各点各拼）：常驻小标（唯远端）＋「本轮来源（技术细节）」。
   ⚠ summary 之辞**须与** `selfdesc.js` 之「来源 ／ 详情」**可辨** —— 一条答里可能有两处折叠
     （彼 ＝ 判据 ／ 检索读数；此 ＝ 走径 ／ 云端）⇒ 同名则用户不知那是二条什么（承 pm_1813 §二.3 之病）。 */
const PA_SHELL_SUM = '本轮来源（技术细节）';
function paShellHtml(box, engExtra){
  const badge = paCloudBadge(box);
  const extra = engExtra || [];
  /* ⭐ 存量重渲（`box` 缺 · 其工程行已由 `paLegacyRouteTakeText` ／ `paLegacyRoutePull` 摘出）
     ⇒ **⛔ 再添**同族之行 —— 否则折叠里会出现二条走径（`src: —（后端未给）` 之伪行 · 承 pm_1076 §三）。 */
  const hasRoute  = extra.some(function(x){ return x.indexOf('🔌 走径：') === 0; });
  const hasLeaves = extra.some(function(x){ return x.indexOf('本轮经云端 · ') === 0; });
  const lines = [];
  if(!hasLeaves){ const o = paLeavesLine(box); if(o) lines.push(o); }
  if(!hasRoute) lines.push(paRouteLine(box));
  const body  = lines.concat(extra).join('\n');
  return (badge ? ('<span class="pacloude" title="本轮经云端模型 ⇒ 内容将出机（读数取后端回执 · ⛔ 前端自说）">' + badge + '</span>') : '')
    + '<details class="eng paroute" data-pa-route="1"><summary>' + PA_SHELL_SUM
    + '</summary><div class="engbody">' + paEsc(body) + '</div></details>';
}
/* ⒜ 之**人话** —— 唯**首次 ∨ 通道切换后**出一句（⛔ 每轮都喊 ⇒ 喊了等于没喊 · 承 pm_1812 §一.⒜）。
   ⚠ 唯**本轮真有过回执**（`box` 在）方出 —— 存量重渲（无回执）**⛔ 造此句**（免一 F5 即冒一句 · 承 L76）。 */
let paCloudSaid = null;   /* null ／ 'remote' ／ 'local'（上次所告之通道 · 一处定形） */
function paCloudNotice(box){
  if(!box) return '';
  const L = (box && box.label) ? box.label : null;
  const now = (L && paRouteIsRemote(L.kind)) ? 'remote' : 'local';
  const first = (paCloudSaid !== now);
  paCloudSaid = now;
  /* ⚠ 唯**远端**之轮方喊此句 —— 本机之轮（local ／ 本机模型）**内容 ⛔ 出机** ⇒ 喊之 ＝ **不实之辞入屏**
     （承「⛔ 不实之辞入屏」· 我一手逮：旧形对本机之轮亦喊「内容将出机」）。 */
  if(now !== 'remote') return '';
  return first ? '（提醒：本轮内容会发给云端模型 · 内容将出机。此提醒只在首次 ／ 切换通道后出现一次。）' : '';
}
/* ⭐ 存量消息之**工程行**（旧存档把走径 ／ 云端行**平铺**在正文里 · 承 pm_1012 §二 · ⛔ 丢信息）：
   摘出 ⇒ 入折叠；用户面一行不动（原文照录 · ⛔ 删）。 */
const PA_LEG_DIV = /<div class="paroute(?:[^"]*)"[^>]*>([\s\S]*?)<\/div>/g;
const PA_LEG_TXT = /^\s*(?:🔌 走径：[^\n]*|本轮经云端 · [^\n]*)\s*$/;
function paUnesc(s){
  return String(s == null ? '' : s).replace(/&lt;/g, '<').replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, '&');
}
function paLegacyRoutePull(html){
  const got = [];
  const rest = String(html || '').replace(PA_LEG_DIV, function(_m, inner){ got.push(paUnesc(inner)); return ''; });
  return {html:rest, eng:got};
}
function paLegacyRouteTakeText(content){
  const t = String(content == null ? '' : content);
  if(t.indexOf('🔌 走径：') < 0 && t.indexOf('本轮经云端 · ') < 0) return null;
  const keep = [], eng = [];
  t.split('\n').forEach(function(x){ (PA_LEG_TXT.test(x) ? eng : keep).push(x); });
  if(!eng.length) return null;
  return {text:keep.join('\n').replace(/^[\n\s]+/, ''), eng:eng};
}
/* 纯文之路（无 html · `send.js` 之答）⇒ 造壳 ＋ 转义正文（并**复刻** `chat.js` 之 KB 胶囊渲 · ⛔ 丢功能）。 */
function paPlainHtml(shell, text){
  let body = null;
  try{
    if(typeof paKbExtractPaths === 'function' && typeof paKbCapsuleHtml === 'function'){
      const paths = paKbExtractPaths(text);
      if(paths.length){
        try{ if(typeof paKbLoad === 'function' && !paKbCache) paKbLoad(false); }catch(e){}
        body = paKbCapsuleHtml(text, (paKbCache || {}).rows);
      }
    }
  }catch(e){ body = null; }
  if(body == null) body = paEsc(text);
  return body + shell;
}
try{ window.paRouteLabel = paRouteLabel; window.paRouteLine = paRouteLine;
     window.paShellHtml = paShellHtml; window.paCloudNotice = paCloudNotice; }catch(e){}

/* 回执探针（**被动** · ⛔ 改行为）：唯记 `/v9/pa/dialog|turn|ask` 之**走径** ⇒ 供上屏。
   ⭐ P0 修（pm_1467 §一.3 · 式⒈「探针前置」）：原实现**返原始 `p`** ⇒ 探针之 `resp.clone().json()`
     微任务排在调用方 `await r.json()` 续段**之后** ⇒ `addMsg` 先跑 ⇒ `paRouteTake()` 取 `null`
     ⇒ **甲（假阴）**真云端轮 ⛔ 上「出机」标；且标签残留至下一轮 ⇒ 误取 ⇒ **乙（假阳）**本机轮挂云端标。
     修：返回之 promise **须待 label 置毕方 resolve**（`probe.then(… ⇒ resp)`）⇒ 调用方之 `await`
     续段 ⛔ 得先于 label 之置 ⇒ 竞态根除 ∧ 乙（残留之源）随之除。⛔ 改答体：唯以 `resp.clone()`
     读探针，原 `resp` 归调用方（承「被动 · ⛔ 改行为」）。 */
(function(){
  if(typeof window.fetch !== 'function') return;
  const orig = window.fetch;
  window.fetch = function(u, o){
    const url = String((u && u.url) ? u.url : u);
    const p = orig.apply(this, arguments);
    if(!/\/v9\/pa\/(dialog|turn|ask)(\?|$)/.test(url)) return p;
    return p.then(function(resp){
      let probe = Promise.resolve();   /* ⛔ 探针自身之败 ⛔ 阻答体（⛔ 改行为） */
      try{
        if(resp && typeof resp.clone === 'function'){
          probe = resp.clone().json().then(function(j){
            try{
              const L = paRouteLabel(j);
              if(L) window.PASelfRouteLast = {label: L, at: String((j && (j.read_at || j.at)) || ''), url: url};
            }catch(e){}
          }, function(){});
        }
      }catch(e){}
      return probe.then(function(){ return resp; });
    });
  };
})();

/* ⭐⭐ 答体之**去壳**（pm_1812 §二.1 ⒜⒝）：挂在共用件 `addMsg` **之下**（本件早于 selfdesc.js 载入
   ⇒ 其包装在外）⇒ ⛔ 动 selfdesc.js ／ chat.js 一字（承「⛔ 动原行为」）。
   四处旧病与今治：
     ⒜ 云端之告（每轮必现）⇒ **首次 ∨ 通道切换**一句 ＋ **常驻小标**；原文入折叠（⛔ 删真源）。
     ⒝ 走径之键 ⇒ ⛔ 用户面（入折叠）。
     ⒞ 存量消息（`data-pa-route` 之 html ／ 走径行开头之纯文）⇒ 摘入折叠（**重渲之幂等** ·
        承 pm_1539 §二.1 ／ pm_1543 §二.⒜ —— ⛔ 行倍增）。
     ⒟ 存量重渲**无本轮回执** ⇒ **原样**（⛔ 造 `src: —（后端未给）` 之伪行 · 承 pm_1076 §三）。 */
(function(){
  const orig = window.addMsg;
  if(typeof orig !== 'function') return;
  window.addMsg = function(role, content, skipStore, html, tid){
    if(role !== 'assistant') return orig.apply(this, arguments);
    const box     = paRouteTake();                     /* 一轮一清（⛔ 取二次） */
    const hasMark = (typeof html === 'string') && html.indexOf('data-pa-route') >= 0;
    const lp = ((typeof html === 'string') && html && !hasMark) ? paLegacyRoutePull(html) : null;
    const lt = (typeof content === 'string') ? paLegacyRouteTakeText(content) : null;
    const legEng = (lp ? lp.eng : []).concat(lt ? lt.eng : []);
    /* ⒟ 存量重渲（无回执 ∧ 无存量工程行）⇒ 原样（⛔ 伪行 · ⛔ 添字）。 */
    if(!box && !legEng.length) return orig.apply(this, arguments);
    const notice = paCloudNotice(box);
    const shell  = paShellHtml(box, legEng);
    if(typeof html === 'string' && html){
      const body = (lp ? lp.html : html);
      const out  = (hasMark || !(box || legEng.length)) ? body : (body + shell);
      return orig.call(this, role, (lt ? lt.text : content), skipStore, paNoteHtml(notice) + out, tid);
    }
    const text = lt ? lt.text : String(content == null ? '' : content);
    return orig.call(this, role, text, skipStore, paNoteHtml(notice) + paPlainHtml(shell, text), tid);
  };
})();


/* —— 面 A · 模型供应商（只读 · P0）：设置面（#pane-cfg · 运行配置）内新起一节 —— */
function paProvMount(){
  const host = document.getElementById('pane-cfg');
  if(!host) return null;
  let box = document.getElementById('paProvBox');
  if(box) return box;
  box = document.createElement('div');
  box.className = 'duty';
  box.id = 'paProvBox';
  box.style.marginTop = '10px';
  box.style.paddingTop = '8px';
  box.style.borderTop = '1px dashed rgba(48,54,61,.7)';
  box.innerHTML = '<div class="sysrow" style="justify-content:space-between">'
    + '<b>模型供应商（面 A · 只读 · P0）</b>'
    + '<span class="chip" onclick="paVendorScan()" title="重取 GET /v9/pa/providers（只读 · ⛔ 切换）">↻ 重扫</span></div>'
    + '<div class="msrc" id="paProvSrc">未扫</div>'
    + '<div id="paProvRows"></div>';
  host.appendChild(box);
  return box;
}
function paProvRowHtml(p){
  const o = p || {};
  const name = String(o.label || o.id || '—');
  const id   = String(o.id || '');
  const kind = String(o.kind || '');
  /* ⭐ 辨义（承 pm 1367 §二.3）：本栏之「远端」＝**模型供应商（租算力）** ⇒ 二名分列 ——
     ⛔ 与「🌐 平台」栏（红线 · ⛔ 代操作他方平台）混 ／ ⛔ 与宿主远端机之「远端态」（未配 ／ 配了但不通 ／ 配了且通）同物。 */
  const kindTxt = (kind === 'local') ? '本机' : ((kind === 'remote') ? '远端（租算力）' : (kind || '未给'));
  let mtxt;
  if(!Array.isArray(o.models)) mtxt = '未给';
  else if(!o.models.length) mtxt = '0 个（本机清单为空）';
  else mtxt = o.models.map(function(m){
    const mm = m || {};
    let s = String(mm.label || mm.id || '—');
    if(mm.isDefault) s += '★默认';
    if(mm.ctx) s += '·ctx' + mm.ctx;
    return s;
  }).join(' ／ ');
  /* ⭐ 密钥（承 pm 1367 §二.1 · 正 **假阴**）：真源 ＝ 平字段 `key_env` ／ `key_state` ／ `key_configured`
     （core/pa/providers.py:78-79）⇒ 旧读 `o.key.*`（子对象 · 后端 ⛔ 出）⇒ 恒「未给」 ＝ 假阴 ⇒ 正之。
     ⚠ 三态 ⛔ 一名蔽二态：`not_required`（无密钥项）⟷ `missing` 须分形（承「一名一义」）。 */
  const ken    = String(o.key_env == null ? '' : o.key_env);
  const kstate = String(o.key_state == null ? '' : o.key_state);
  const ktxt = (typeof o.key_configured === 'boolean')
    ? (o.key_configured ? '✓已配' : ((kstate === 'not_required') ? '—不需（无此项）' : '—未配'))
    : ((kstate === 'configured') ? '✓已配' : ((kstate === 'missing') ? '—未配'
      : ((kstate === 'not_required') ? '—不需（无此项）' : '未给')));
  /* ⭐ 启用之「源」（承 pm_1385 §二 · ⛔ 一名蔽二态）：`enabled`（布尔）唯态 ⇒ 附 `enabled_src`
     （后端之源自陈 · core/pa/providers.py:82-90）：env 停用 ⟷ 注册表默认停 ⟷ 默认启用 ⛔ 同辞。
     ⚠ 印随值（⛔ 前端自断其源）：后端之源自陈已含态辞者 ⇒ 逐字照渲（⛔ 重说 ⇒ 免「停用（源 停用（源…））」之叠）；
     未含 ⇒ 「态（源 …）」；`enabled_src` ⛔ 出（旧后端）⇒ 源段显「未给」（⛔ 假称「默认」）。 */
  const enSrc = String(o.enabled_src == null ? '' : o.enabled_src);
  const enTxt = (typeof o.enabled === 'boolean')
    ? ((enSrc && enSrc.indexOf(o.enabled ? '启用' : '停用') === 0)
        ? enSrc
        : ((o.enabled ? '启用' : '停用') + '（源 ' + (enSrc || '未给') + '）'))
    : '未给';
  /* ⭐ 根（承 pm 1367 §二.2）：后端出 `base_url` ／ `base_url_env` ／ `base_url_wired`（布尔）＋ `base_url_note`
     ⇒ 旧面 **零字符渲及** ⇒ 须显（⛔ 静默吞其值）｜⚠ `False` ＝「唯显示 · 未生效」⇒ ⛔ 以一名蔽之；
     ⛔ 前端亦 ⛔ 自断「env 已置」（后端 ⛔ 出此读数）⇒ 唯照其值 ＋ 其注（印随值）。 */
  const burl  = String(o.base_url == null ? '' : o.base_url);
  const benv  = String(o.base_url_env == null ? '' : o.base_url_env);
  const bnote = String(o.base_url_note == null ? '' : o.base_url_note);
  const wTxt = (typeof o.base_url_wired === 'boolean')
    ? (o.base_url_wired ? '✓已生效' : '—未生效（唯显示）') : '未给';
  return '<div class="r" data-provider="' + paEsc(id || name) + '"><span class="k">' + paEsc(name) + '</span><span>'
    + paEsc(kindTxt) + ' ／ id ' + paEsc(id || '—') + ' ／ ' + paEsc(enTxt)
    + ' ／ 密钥 ' + paEsc(ktxt) + (ken ? ('（名 ' + paEsc(ken) + '）') : '')
    + '<br>模型表：' + paEsc(mtxt)
    + '<br>根 ' + paEsc(burl || '未给') + (benv ? ('（env ' + paEsc(benv) + '）') : '') + ' · ' + paEsc(wTxt)
    + (bnote ? ('｜注：' + paEsc(bnote)) : '')
    + '</span></div>';
}
async function paVendorScan(){
  const box = paProvMount(); if(!box) return null;
  const srcEl = document.getElementById('paProvSrc');
  const rowsEl = document.getElementById('paProvRows');
  const at = new Date().toLocaleString('zh-CN', {hour12: false});
  if(srcEl){ srcEl.title = '源：GET /v9/pa/providers'; srcEl.textContent = '来源：本机模型清单 · 扫于 ' + at + ' …'; }
  let st = 0, d = null, err = null;
  try{ const r = await fetch(API + '/v9/pa/providers', {cache: 'no-store'}); st = r.status; if(r.ok) d = await r.json(); }
  catch(e){ err = e; }
  let out;
  if(err){
    out = {state: 'unreachable'};
    if(srcEl) srcEl.textContent = '来源：本机模型清单 · 未应答 · 扫于 ' + at;
    if(rowsEl) rowsEl.innerHTML = '<div class="r"><span class="k">未应答</span><span>'
      + '本机没回（' + paEsc(String((err && err.message) || err)) + '）⇒ 不等于「没有供应商」'
      + '（承 L103 ／ L1052：未应答之义 ≠ 0 行之义）</span></div>';
  } else if(st === 404 || st === 501){
    out = {state: 'not_implemented', status: st};
    if(srcEl) srcEl.textContent = '来源：本机模型清单 · 这一面本机没挂 · 扫于 ' + at;
    if(rowsEl) rowsEl.innerHTML = '<div class="r"><span class="k">' + PA_GAP.tag('down') + '</span><span>'
      + '后端<b>' + PA_GAP.fallback('providers') + '</b>此读数（HTTP ' + st + '）⇒ 候 _to_td_034。本面板已就位：后端一接 ⇒ 本节即亮（⛔ 硬编充数）。'
      + '</span></div>';
  } else if(st !== 200 || !d){
    out = {state: 'bad', status: st};
    if(srcEl) srcEl.textContent = '来源：本机模型清单 · 回了不可解之体 · 扫于 ' + at;
    if(rowsEl) rowsEl.innerHTML = '<div class="r"><span class="k">坏体</span><span>HTTP ' + st
      + ' · 体不可解 ⇒ 如实报（⛔ 当 0 行）</span></div>';
  } else {
    const arr = Array.isArray(d) ? d : (Array.isArray(d.providers) ? d.providers : (Array.isArray(d.items) ? d.items : null));
    if(!arr){
      out = {state: 'shape', keys: Object.keys(d || {})};
      if(srcEl) srcEl.textContent = '来源：本机模型清单 · 应答（形状未给）· 扫于 ' + at;
      if(rowsEl) rowsEl.innerHTML = '<div class="r"><span class="k">形状</span><span>应答 200 而无 providers[] ⇒ 键：'
        + paEsc(Object.keys(d || {}).join(' ／ ') || '（无）') + '（⛔ 猜 ／ ⛔ 当 0 行）</span></div>';
    } else {
      const def = d.default || d.defaults || null;
      const defTxt = (def && (def.provider || def.model))
        ? (String(def.provider || '—') + ' ／ ' + String(def.model || '—') + (def.thinking ? (' ／ 思考 ' + String(def.thinking)) : ''))
        : '未给（⛔ 猜本机）';
      out = {state: 'ok', n: arr.length, def: defTxt};
      if(srcEl) srcEl.textContent = '来源：本机模型清单 · ' + arr.length + ' 项 · 默认 ' + defTxt + ' · 扫于 ' + at;
      if(rowsEl) rowsEl.innerHTML = (arr.length
        ? arr.map(function(x){ return paProvRowHtml(x); }).join('')
        : '<div class="r"><span class="k">0 项</span><span title="与「未接」不同词（辨义）">本机清单为空 ⇒ 照实报 0</span></div>')
        + '<div class="foot" title="逐行探法：GET /v9/pa/providers（读本机注册表 · 本页唯显示）">逐行探法：本机注册表 · 本页唯显示｜密钥：唯布尔（值不入屏）｜本段不切换</div>'
      + '｜⚠ 辨义：本栏「远端」＝模型供应商（租算力），与「🌐 平台」栏（红线 · 不代操作他方平台）二名分列；与宿主远端机之「远端态」（未配 ／ 配了但不通 ／ 配了且通）亦非一物</div>';
    }
  }
  const el = document.getElementById('paProvBox');
  if(el) el.setAttribute('data-state', out.state);
  try{ paRuntimeScan(); }catch(e){}
  try{ paHarnessScan(); }catch(e){}
  return out;
}


/* —— 引擎状态（P0 · 只读）：Ollama / LocaLM / DSH 的真实探活 —— */
function paRuntimeMount(){
  const host = document.getElementById('pane-cfg');
  if(!host) return null;
  let box = document.getElementById('paRuntimeBox');
  if(box) return box;
  box = document.createElement('div');
  box.className = 'duty';
  box.id = 'paRuntimeBox';
  box.style.marginTop = '10px';
  box.style.paddingTop = '8px';
  box.style.borderTop = '1px dashed rgba(48,54,61,.7)';
  box.innerHTML = '<div class="sysrow" style="justify-content:space-between">'
    + '<b>引擎状态（只读 · 真实探活）</b>'
    + '<span><span class="chip" onclick="paBenchRun(\'localm\')" title="POST /v9/pa/benchmark（localm）">测 localm</span> '
    + '<span class="chip" onclick="paBenchRun(\'ollama\')" title="POST /v9/pa/benchmark（Ollama）">测 Ollama</span> '
    + '<span class="chip" onclick="paRuntimeScan()" title="GET /v9/pa/runtime/status（只读）">↻ 重扫</span></span></div>'
    + '<div class="msrc" id="paRuntimeSrc">未扫</div>'
    + '<div id="paRuntimeRows"></div>'
    + '<div class="msrc" id="paBenchRows"></div>';
  host.appendChild(box);
  return box;
}
async function paRuntimeScan(){
  const box = paRuntimeMount(); if(!box) return null;
  const srcEl = document.getElementById('paRuntimeSrc');
  const rowsEl = document.getElementById('paRuntimeRows');
  const at = new Date().toLocaleString('zh-CN', {hour12: false});
  if(srcEl) srcEl.textContent = '来源：本机只读探活 · 扫于 ' + at + ' …';
  let st = 0, d = null, err = null;
  try{ const r = await fetch(API + '/v9/pa/runtime/status', {cache: 'no-store'}); st = r.status; if(r.ok) d = await r.json(); }
  catch(e){ err = e; }
  const esc = (typeof paEsc === 'function') ? paEsc : String;
  if(err){
    if(srcEl) srcEl.textContent = '来源：本机只读探活 · 未应答 · 扫于 ' + at;
    if(rowsEl) rowsEl.innerHTML = '<div class="r"><span class="k">未应答</span><span>'
      + esc(String((err && err.message) || err)) + ' ⇒ 未应答 ≠ 没有引擎</span></div>';
    return null;
  }
  if(st !== 200 || !d || !Array.isArray(d.items)){
    if(srcEl) srcEl.textContent = '来源：本机只读探活 · 回体不可解（HTTP ' + st + '）· 扫于 ' + at;
    if(rowsEl) rowsEl.innerHTML = '<div class="r"><span class="k">坏体</span><span>HTTP ' + st + ' ⇒ 照实报（⛔ 当 0 项）</span></div>';
    return null;
  }
  if(srcEl) srcEl.textContent = '来源：本机只读探活 · ' + d.items.length + ' 项 · 扫于 ' + at;
  if(rowsEl) rowsEl.innerHTML = d.items.map(function(it){
    const o = it || {};
    const state = String(o.state || (o.available ? '在' : '未接'));
    const models = Array.isArray(o.models) ? o.models : [];
    const loaded = Array.isArray(o.loaded) ? o.loaded : [];
    let m = models.length ? ('模型 ' + models.join(' ／ ')) : '模型未给';
    if(loaded.length) m += ' · 已载 ' + loaded.join(' ／ ');
    return '<div class="r" data-runtime="' + esc(String(o.id || '')) + '"><span class="k">'
      + esc(String(o.label || o.id || '—')) + '</span><span>'
      + esc(state) + (o.version ? (' · ' + esc(String(o.version))) : '')
      + (o.base_url ? (' · ' + esc(String(o.base_url))) : '')
      + '<br>' + esc(String(o.detail || '')) + '<br>' + esc(m) + '</span></div>';
  }).join('')
    + ((Array.isArray(d.warnings) && d.warnings.length)
      ? d.warnings.map(function(w){ return '<div class="r" style="color:#d2991d"><span class="k">⚠</span><span>' + esc(String(w)) + '</span></div>'; }).join('')
      : '')
    + '<div class="foot" title="GET /v9/pa/runtime/status（只读探活 · 不发模型请求）">只读探活 · 不切换、不载模型｜状态来自本机服务应答｜未载模型会照实显示</div>';
  return d;
}


let paBenchBusy = false;
async function paBenchRun(engine){
  if(paBenchBusy) return null;
  const out = document.getElementById('paBenchRows');
  const esc = (typeof paEsc === 'function') ? paEsc : String;
  paBenchBusy = true;
  if(out) out.textContent = '跑 ' + engine + ' benchmark…（会真实载入/推理，约数秒）';
  let body = {engine: engine, max_tokens: 48};
  try{
    const c = JSON.parse(localStorage.getItem('pa_cfg') || '{}');
    const m = String((c && c.model) || '');
    if(m && ((engine === 'localm') === m.startsWith('localm:'))) body.model = m;
  }catch(e){}
  try{
    const r = await fetch(API + '/v9/pa/benchmark', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(body), cache:'no-store'});
    const d = await r.json().catch(function(){ return null; });
    if(!r.ok || !d || d.ok === false){
      if(out) out.innerHTML = '<span style="color:#d2991d">benchmark 失败：' + esc(String((d && (d.message || d.error)) || ('HTTP ' + r.status))) + '</span>';
      return null;
    }
    const vram = (d.vram_before_mib == null) ? 'n/a' : (d.vram_before_mib + ' → ' + d.vram_after_mib + ' MiB');
    const delta = (d.vram_delta_mib == null) ? '' : ('（Δ ' + (d.vram_delta_mib >= 0 ? '+' : '') + d.vram_delta_mib + '）');
    if(out) out.innerHTML = '<div class="r"><span class="k">' + esc(String(d.engine || engine)) + '</span><span>'
      + 'TTFT ' + (d.ttft_ms == null ? 'n/a' : esc(String(d.ttft_ms)) + ' ms')
      + ' · tok/s ' + (d.tok_s == null ? 'n/a' : esc(String(d.tok_s)))
      + ' · tokens ' + (d.tokens == null ? 'n/a' : esc(String(d.tokens)))
      + ' · 耗时 ' + (d.elapsed_ms == null ? 'n/a' : esc(String(d.elapsed_ms)) + ' ms')
      + '<br>VRAM ' + esc(vram) + esc(delta)
      + '<br>口径：' + esc(String(d.tok_s_source || ''))
      + (d.answer ? ('<br>答：' + esc(String(d.answer).slice(0, 240))) : '')
      + '</span></div>';
    return d;
  }catch(e){
    if(out) out.innerHTML = '<span style="color:#d2991d">benchmark 未完成：' + esc(String((e && e.message) || e)) + '</span>';
    return null;
  }finally{ paBenchBusy = false; }
}


/* —— DSH 任务卡 / RunRecord / 轨迹（P1-4） —— */
function paHarnessMount(){
  const host = document.getElementById('pane-cfg');
  if(!host) return null;
  let box = document.getElementById('paHarnessBox');
  if(box) return box;
  box = document.createElement('div');
  box.className = 'duty';
  box.id = 'paHarnessBox';
  box.style.marginTop = '10px';
  box.style.paddingTop = '8px';
  box.style.borderTop = '1px dashed rgba(48,54,61,.7)';
  box.innerHTML = '<div class="sysrow" style="justify-content:space-between">'
    + '<b>DSH 任务卡（RunRecord / 轨迹）</b>'
    + '<span class="chip" onclick="paHarnessScan()" title="GET /v9/pa/harness/runs">↻ 刷新</span></div>'
    + '<div class="msrc" id="paHarnessSrc">未扫</div>'
    + '<div style="display:flex;gap:6px;margin:4px 0">'
    + '<input id="paHTask" type="text" placeholder="给 DSH 的任务，例如：只回答 OK" style="flex:1;min-width:0;background:#0d1117;border:1px solid #30363d;color:#d7dde7;border-radius:4px;padding:4px 6px">'
    + '<button class="chip" id="paHRunBtn" onclick="paHarnessRun()" title="POST /v9/pa/harness/run（唯本机 · 会真实执行）">运行</button></div>'
    + '<div class="msrc" style="color:#d2991d" title="DSH headless 会执行任务，可能改动文件/跑命令；请只给可信任务">⚠ 会真实执行 DSH headless，请只给可信任务</div>'
    + '<div id="paHarnessRows"></div>';
  host.appendChild(box);
  return box;
}
function _paHEsc(s){ return (typeof paEsc === 'function') ? paEsc(String(s == null ? '' : s)) : String(s == null ? '' : s); }
async function paHarnessScan(){
  const box = paHarnessMount(); if(!box) return null;
  const src = document.getElementById('paHarnessSrc');
  const rows = document.getElementById('paHarnessRows');
  const at = new Date().toLocaleString('zh-CN', {hour12:false});
  if(src) src.textContent = '来源：PA harness 账 · 扫于 ' + at + ' …';
  try{
    const r = await fetch(API + '/v9/pa/harness/runs?limit=20', {cache:'no-store'});
    const d = await r.json().catch(function(){ return null; });
    if(!r.ok || !d) throw new Error('HTTP ' + r.status);
    const arr = Array.isArray(d.runs) ? d.runs : [];
    if(src) src.textContent = '来源：PA harness 账 · ' + arr.length + ' 条 · 扫于 ' + at;
    if(!rows) return d;
    rows.innerHTML = arr.length ? arr.map(function(x){
      const ev = Array.isArray(x.events) ? x.events : [];
      const meta = x.harness_meta || {};
      const title = x.task || '(旧记录无 task sidecar)';
      return '<div class="r" data-run="' + _paHEsc(x.run_id) + '"><span class="k">' + _paHEsc(x.status) + '</span><span>'
        + _paHEsc(title)
        + '<br>' + _paHEsc(x.run_id) + ' · ' + _paHEsc(x.started_at || '') + ' → ' + _paHEsc(x.ended_at || '')
        + ' · rc=' + _paHEsc(meta.rc) + ' · receipt ' + _paHEsc(x.receipt_sha16 || '')
        + (meta.stderr_tail ? ('<br>stderr: ' + _paHEsc(meta.stderr_tail)) : '')
        + '<br><details><summary>轨迹 ' + ev.length + ' 步</summary>'
        + (ev.length ? ev.map(function(e){ return '<div style="margin:2px 0"><b>' + _paHEsc(e.kind) + '</b> ' + _paHEsc(e.text || '') + '</div>'; }).join('') : '<div>无轨迹（旧记录未存 events）</div>')
        + '</details></span></div>';
    }).join('') : '<div class="r"><span class="k">0 条</span><span>目前没有 DSH run 记录</span></div>';
    return d;
  }catch(e){
    if(src) src.textContent = '来源：PA harness 账 · 未应答 · 扫于 ' + at;
    if(rows) rows.innerHTML = '<div class="r"><span class="k">未应答</span><span>' + _paHEsc((e && e.message) || e) + ' ⇒ 不等于没有记录</span></div>';
    return null;
  }
}
async function paHarnessRun(){
  const inp = document.getElementById('paHTask');
  const btn = document.getElementById('paHRunBtn');
  const rows = document.getElementById('paHarnessRows');
  const task = String((inp && inp.value) || '').trim();
  if(!task){ if(inp) inp.focus(); return null; }
  if(btn) btn.disabled = true;
  if(rows) rows.innerHTML = '<div class="r"><span class="k">运行中</span><span>DSH headless 执行中，完成后刷新任务卡…</span></div>';
  try{
    const r = await fetch(API + '/v9/pa/harness/run', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({task: task, timeout: 120}), cache:'no-store'});
    const d = await r.json().catch(function(){ return null; });
    if(!r.ok || !d || d.ok === false){
      if(rows) rows.innerHTML = '<div class="r"><span class="k">失败</span><span>' + _paHEsc(String((d && (d.message || d.error)) || ('HTTP ' + r.status))) + '</span></div>';
    }
    if(inp) inp.value = '';
    await paHarnessScan();
    return d;
  }catch(e){
    if(rows) rows.innerHTML = '<div class="r"><span class="k">失败</span><span>' + _paHEsc((e && e.message) || e) + '</span></div>';
    return null;
  }finally{ if(btn) btn.disabled = false; }
}

/* —— 面 B · 执行层 agent 名册（只读 · Q0）
   ⭐ pm_1089 修正：数据源 ＝ **既有** `GET /v9/pa/roster`（＋`?full=1`）⇒ ⛔ 自造 `/v9/pa/agents`（该名已撤）。
   名册真源 ＝ core/pa/roster.py（2026-09-10 老板定调：「能调度【市面上所有 agent】」；通用底座＝ computer use）。
   接入分级 L4＞L3＞L2＞L1＞L0 ＝ 「适配更多主流 agent」之轴（承该件 docstring 逐字）。
   纪律（该件逐字）：verified ／ boundary ／ fragility 须**实测来源**；未验证标 unverified，⛔ 写「应该可以」。 */
const PA_ROSTER_LEVELS = [
  ['L4', '原生 API／SDK'],
  ['L3', 'MCP'],
  ['L2', '文档／应用级接口'],
  ['L1', 'UI 自动化'],
  ['L0', '不可接入']
];
let paRosterLast = null;   /* 前次扫之卡（id ⇒ 指纹）⇒ 供「本机复扫」比差 */

function paRosterMount(){
  const host = document.getElementById('pane-cfg');
  if(!host) return null;
  let box = document.getElementById('paRosterBox');
  if(box) return box;
  box = document.createElement('div');
  box.className = 'duty';
  box.id = 'paRosterBox';
  box.style.marginTop = '10px';
  box.style.paddingTop = '8px';
  box.style.borderTop = '1px dashed rgba(48,54,61,.7)';
  box.innerHTML = '<div class="sysrow" style="justify-content:space-between">'
    + '<b>本机 agent 名册（面 B · 只读 · Q0）</b>'
    + '<span class="chip" onclick="paRosterScan()" title="重取 GET /v9/pa/roster?full=1 并与前次比差（只读 · ⛔ 连接）">↻ 本机复扫</span></div>'
    + '<div class="msrc" id="paRosterSrc">未扫</div>'
    + '<div id="paRosterRows"></div>';
  host.appendChild(box);
  return box;
}
function paRosterListHtml(title, arr, isVer){
  if(!Array.isArray(arr)) return '<div>' + paEsc(title) + '：未给</div>';
  if(!arr.length) return '<div>' + paEsc(title) + '：0 条'
    + (isVer ? '（⭐ unverified —— 按名册纪律，⛔ 写「应该可以」）' : '') + '</div>';
  return '<div>' + paEsc(title) + '（' + arr.length + '）：'
    + arr.map(function(x){ return '· ' + paEsc(String(x)); }).join('<br>') + '</div>';
}
function paRosterCardHtml(c){
  const o = c || {};
  const id = String(o.id || '—');
  const name = String(o.name || id);
  const kind = String(o.kind || '未给');
  const role = String(o.role || '未给');
  const acc = o.access || {};
  const lv = String(acc.level || '未给');
  const ch = String(acc.channel || '未给');
  const en = String(acc.entry || '未给');
  const caps = Array.isArray(o.capabilities) ? o.capabilities : null;
  const capTxt = caps ? (caps.length ? caps.join(' ／ ') : '0 项') : '未给';
  const ver = Array.isArray(o.verified) ? o.verified : null;
  const bou = Array.isArray(o.boundary) ? o.boundary : null;
  const fra = Array.isArray(o.fragility) ? o.fragility : null;
  const raw = String(o.state || o.status || '');
  const unseen = (raw === 'missing' || raw === '未见');
  const unver = (!ver || !ver.length);
  const n = function(a){ return a ? a.length : 0; };
  return '<div class="r" data-card="' + paEsc(id) + '" data-level="' + paEsc(lv) + '"'
    + ' data-card-state="' + paEsc(raw || (unver ? 'unverified' : 'ok')) + '"'
    + (unseen ? ' style="opacity:.6"' : '') + '><span class="k">' + paEsc(lv) + '</span><span>'
    + '<b>' + paEsc(name) + '</b> ／ ' + paEsc(kind) + ' ／ ' + paEsc(role)
    + (unseen ? ' ／ <b>—未见</b>' : '')
    + (unver ? ' ／ <b>unverified</b>' : '')
    + '<br>能力：' + paEsc(capTxt)
    + '<br>来路：通道 ' + paEsc(ch) + ' ／ 入口 ' + paEsc(en)
    + '<br><details class="eng"><summary>实测 ' + n(ver) + ' ／ 边界 ' + n(bou) + ' ／ 脆弱 ' + n(fra) + '（点开）</summary><div class="engbody">'
    + paRosterListHtml('实测 verified（＝探法之据）', ver, true)
    + paRosterListHtml('边界 boundary', bou)
    + paRosterListHtml('脆弱 fragility', fra)
    + (o.cost ? ('<div>成本 cost：' + paEsc(String(o.cost)) + '</div>') : '')
    + '</div></details></span></div>';
}
async function paRosterScan(){
  const box = paRosterMount(); if(!box) return null;
  const srcEl = document.getElementById('paRosterSrc');
  const rowsEl = document.getElementById('paRosterRows');
  const at = new Date().toLocaleString('zh-CN', {hour12: false});
  if(srcEl) srcEl.textContent = '源：GET /v9/pa/roster?full=1 · 扫于 ' + at + ' …';
  let st = 0, d = null, err = null;
  try{ const r = await fetch(API + '/v9/pa/roster?full=1', {cache: 'no-store'}); st = r.status; if(r.ok) d = await r.json(); }
  catch(e){ err = e; }
  let out;
  if(err || st !== 200 || !d || !Array.isArray(d.cards)){
    out = {state: (err ? 'unreachable' : 'bad'), status: st};
    if(srcEl) srcEl.textContent = '源：GET /v9/pa/roster?full=1 · ' + (err ? '未应答' : ('HTTP ' + st)) + ' · 扫于 ' + at;
    if(rowsEl) rowsEl.innerHTML = '<div class="r"><span class="k">' + (err ? '未应答' : '坏体') + '</span><span>'
      + (err ? ('后端未回（' + paEsc(String((err && err.message) || err)) + '）') : ('HTTP ' + st + ' · 体不可解'))
      + ' ⇒ ⛔ 不等于「本机没有 agent」（承 L103 ／ L1052：未应答之义 ≠ 0 行之义）</span></div>';
  } else {
    const cards = d.cards;
    const byId = {};
    cards.forEach(function(c){ byId[String((c && c.id) || '')] = c; });
    const ids = Object.keys(byId);
    const first = !paRosterLast;
    const added = [], changed = [], gone = [];
    let unseen = 0, unver = 0;
    ids.forEach(function(k){
      const o = byId[k] || {};
      const raw = String(o.state || o.status || '');
      if(raw === 'missing' || raw === '未见') unseen++;
      if(!Array.isArray(o.verified) || !o.verified.length) unver++;
      if(first) return;
      const fp = JSON.stringify(o);
      if(!(k in paRosterLast)) added.push(k);
      else if(paRosterLast[k] !== fp) changed.push(k);
    });
    if(!first){ Object.keys(paRosterLast).forEach(function(k){ if(!(k in byId)) gone.push(k); }); }
    const byLv = {};
    PA_ROSTER_LEVELS.forEach(function(pp){ byLv[pp[0]] = []; });
    ids.forEach(function(k){ const lv = String(((byId[k] || {}).access || {}).level || '未给'); (byLv[lv] = byLv[lv] || []).push(k); });
    const snap = {};
    ids.forEach(function(k){ snap[k] = JSON.stringify(byId[k]); });
    paRosterLast = snap;
    out = {state: 'ok', n: cards.length, added: added.length, changed: changed.length, gone: gone.length, unseen: unseen, unverified: unver, first: first};
    if(srcEl) srcEl.textContent = '源：GET /v9/pa/roster?full=1 · ' + cards.length + ' 卡（'
      + PA_ROSTER_LEVELS.map(function(pp){ return pp[0] + ' ' + ((byLv[pp[0]] || []).length); }).join(' ／ ') + '）· 扫于 ' + at
      + (first ? '｜首次读 ⇒ ⛔ 比差（候下次复扫）'
               : ('｜复扫比差：新增 ' + added.length + ' ／ 变更 ' + changed.length + ' ／ 消失 ' + gone.length))
      + ' ／ 未见 ' + unseen + ' ／ unverified ' + unver;
    let html = '';
    PA_ROSTER_LEVELS.forEach(function(pp){
      const ks = byLv[pp[0]] || [];
      html += '<div class="sysrow"><b>' + paEsc(pp[0]) + ' · ' + paEsc(pp[1]) + '</b>'
        + '<span class="msrc" style="margin:0">' + ks.length + ' 卡</span></div>';
      html += ks.length ? ks.map(function(k){ return paRosterCardHtml(byId[k]); }).join('')
        : '<div class="r"><span class="k">—</span><span>本格 0 卡（该级暂无卡）</span></div>';
    });
    html += '<div class="foot">逐行来路／探法：卡之 <code>access.channel</code> ＋ <code>access.entry</code> ＝ 来路；'
      + '<code>verified[]</code> 各条 ＝ 实测来源（名册纪律：未验证标 unverified · ⛔ 写「应该可以」）。<br>'
      + '本机扫描器 ＋ 握手在<b>后端</b>（候 _to_td_035 修正版）⇒ 本页唯重取 ＋ 比差'
      + '（⛔ 前端直起进程 ／ ⛔ 自动信任 ／ ⛔ 凭据入屏）｜本段 ⛔ 连接（候 Q1）</div>';
    if(rowsEl) rowsEl.innerHTML = html;
  }
  const el = document.getElementById('paRosterBox');
  if(el) el.setAttribute('data-state', out.state);
  if(el && out.state === 'ok') el.setAttribute('data-levels', PA_ROSTER_LEVELS.map(function(pp){ return pp[0]; }).join(','));
  return out;
}

/* —— 挂载与触发：进「更多」即扫（懒加载 · 承 paLoadPlans 之形）＋ 各节自备「↻ 重扫」—— */
(function(){
  function mount(){ try{ paProvMount(); }catch(e){} try{ paRosterMount(); }catch(e){} }
  if(document.readyState === 'loading'){ document.addEventListener('DOMContentLoaded', mount); } else { mount(); }
  setTimeout(mount, 400);
  const orig = window.paMore;
  if(typeof orig === 'function'){
    window.paMore = function(open){
      const r = orig.apply(this, arguments);
      if(open){ try{ paVendorScan(); }catch(e){} try{ paRosterScan(); }catch(e){} }
      return r;
    };
  }
})();
