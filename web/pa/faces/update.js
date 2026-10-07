/* ---- 更新环节之可见之面（CW b2a5182 · 2026-10-07 · pm_1621 四条 · 承 TD_1620 之后端半）
   老板之令（逐字）：「现阶段我们作为内测，做好 `update` 环节」⇒ ⭐ 判：**「更新」最易被误判为「坏了」**
     （下载慢 ／ 替换中 ／ 需重启）⇒ 承 pm 之新规（pm_1617 §一.3）：**凡等待必有提示 ＋ 进度 ＋ 时长；
     凡不可用必有因 ＋ 去处；凡提示须在用户当下看得见之处** —— 此规于「更新」尤要。
   ⭐ **取数（一处）**：唯读 `/health`（既有端 · 与 `startup.js` 同源 ⇒ 一处取数）之 `update` 键 ——
      ⛔ 引未挂之 `/v9/pa/*`：面册闸（`tests/unit/test_pa_ui_faces.py`）以「面之源里所引 `/v9/pa/*` 须**已挂**」为判，
      旧稿书整字面 `'/v9/pa/update'` ⇒ 该端**今未挂** ⇒ 闸判「悬」为真（此面之依赖今未足）⇒ 本件唯依赖既有之端。
   ⚠ **端名与字段之逐字 ⇒ 候 TD `1620` 之报 ⇒ 唯改 `PA_UPD_SRC` ／ `paUpdFetch` 一处对齐**（pm_1621 §一.2）。
     所读字段（**与 `1616` 之进度读数同辞** —— 承 pm_1620 §二.3「更新环节共用 · 一处定形」）：
       `state`（idle ／ running ／ done ／ failed）｜`phase`（见 `PA_UPD_PHASE` 之键）｜
       `done_bytes` ／ `total_bytes` ／ `eta_s` ／ `since_s`｜`current` ／ `latest` ／ `available`｜
       `files_done` ／ `files_total`｜`error`（**人话** · ⛔ 原始异常 —— 原始因入机器字段 `last_error`，本件 ⛔ 读）。
   ⛔ 本件 ⛔ 触 `core/**`（TD 之域）∧ ⛔ 自渲 `#paPrep`（其渲唯 `startup.js` 一处 · 承「⛔ 二套面」）。
   ⛔ 本件 ⛔ 起停 ／ ⛔ 执行更新（发起归后端之「更新」入口 · 本件唯**显示**）。 */

/* ⚠ 更新态之取数（**一处**）：`/health`（既有端）之 `update` 键 —— ⛔ 引未挂之端（说见上）。
   ⚠ **候 TD_1620 之报：端名 ／ 字段 ⇒ 唯改本行 ＋ `paUpdFetch` 一处**。 */
const PA_UPD_SRC = '/health';
const PA_UPD_POLL_MS  = 30000;        /* 常态之巡 */
const PA_UPD_BUSY_MS  = 2000;         /* 更新进行中 ⇒ 密巡（进度须活） */

/* `phase` 机器码 ⇒ 人话（⛔ 在表 ⇒ 照实显原值 · 承「界面态显真读数」）。 */
const PA_UPD_PHASE = {
  'checking': '正在检查新版本',
  'download': '正在下载增量包',
  'downloading': '正在下载增量包',
  'verify': '正在校验（逐件 sha256）',
  'verifying': '正在校验（逐件 sha256）',
  'backup': '正在备份（可回滚）',
  'backing_up': '正在备份（可回滚）',
  'replace': '正在替换文件',
  'replacing': '正在替换文件',
  'restart': '需重启服务方可生效',
  'restarting': '正在重启服务',
  'done': '更新完成'
};
const PA_UPD_OUTLET = '去处：装根之「更新」入口重试 ∨ 看服务窗口之日志（⛔ 本页发起更新 ／ ⛔ 手改安装目录之件）';

/* ⭐ **一处定形**（纯函数 · ⛔ DOM）：更新端之回 ＋ 本地之钟 ⇒ 面之态。
   `u` ＝ 端之 JSON（未答 ⇒ null）；`ctx` ＝ {elapsed_s, http_status, health_version}。
   回 {state, phase, text, note, can_bar, pct, done, total, eta_s, since_s, since_src,
       current, latest, available, files_done, files_total, rolled_back, src}
   （`state` ∈ unanswered ／ latest ／ available ／ running ／ restart ／ done ／ failed）。 */
function paUpdView(u, ctx){
  const c  = (ctx && typeof ctx === 'object') ? ctx : {};
  const o  = (u && typeof u === 'object') ? u : null;
  const el = paPrepNum(c.elapsed_s);
  const elR = (el == null) ? null : Math.max(0, Math.round(el));
  const v = {state:'unanswered', phase:'', text:'', note:'', can_bar:false, pct:null,
             done:null, total:null, eta_s:null, since_s:null, since_src:'',
             current:'', latest:'', available:null, files_done:null, files_total:null,
             rolled_back:null, src:PA_UPD_SRC};
  if(!o){
    v.text = '更新面未答（' + PA_UPD_SRC + ' 之 update 未给' + (c.http_status ? (' · HTTP ' + c.http_status) : ' · 连不上') + '）';
    v.note = '⛔ 不等于「已是最新」（承「未知 ⛔ 充知」· 字段候 TD_1620 之报）';
    return v;
  }
  const ss = function(x){ return (x == null) ? '' : String(x).trim(); };
  const bak = paPrepNum(o.since_s);
  v.phase = ss(o.phase);
  v.current = ss(o.current) || ss(c.health_version);
  v.latest = ss(o.latest);
  v.available = (typeof o.available === 'boolean') ? o.available : null;
  v.done = paPrepNum(o.done_bytes); v.total = paPrepNum(o.total_bytes);
  v.eta_s = paPrepNum(o.eta_s);
  v.files_done = paPrepNum(o.files_done); v.files_total = paPrepNum(o.files_total);
  v.rolled_back = (typeof o.rolled_back === 'boolean') ? o.rolled_back : null;
  v.since_s = (bak == null) ? elR : Math.round(bak);
  v.since_src = (bak == null) ? (elR == null ? '' : 'page') : 'backend';
  const raw = ss(o.state);
  const err = ss(o.error) || ss(o.message);
  /* ⛔ 原始异常入屏：唯取 `error` ／ `message`（后端之人话）；⛔ 读 `last_error` ／ `traceback`。 */
  if(raw === 'failed' || raw === 'error' || err){
    v.state = 'failed';
    v.text = '更新失败' + (err ? ('：' + err) : '（后端未给因）');
    v.note = (v.rolled_back === true ? ('已回滚至 ' + (ss(o.rollback_to) || '上一版本') + ' —— ')
              : (v.rolled_back === false ? '⛔ 未回滚（须人工处置）—— '
                 : '回滚之状未给 —— '))
           + PA_UPD_OUTLET;
    return v;
  }
  const busy = (raw === 'running') || !!PA_UPD_BUSY[v.phase];
  if(busy){
    v.state = 'running';
    const ph = PA_UPD_PHASE[v.phase] || (v.phase ? ('当前步骤：' + v.phase) : '正在更新（后端未给步骤）');
    /* ⭐ pm_1633 裁 ⒝（一处定形 · 与 `startup.js` 共本函）：`measured ∧ ⛔ total` ⇒ 显「已下 X MB（总长不可量）」 */
    const mn = paPrepMeasuredNote(v.done, v.total);
    let t = '正在更新…（' + ph;
    if(v.total != null && v.total > 0 && v.done != null){
      v.can_bar = true;
      v.pct = Math.max(0, Math.min(100, Math.floor((v.done / v.total) * 100)));
      t += ' · 已下 ' + paPrepMB(v.done) + ' / ' + paPrepMB(v.total) + '（' + v.pct + '%）';
      if(v.eta_s != null) t += ' · 约还需 ' + Math.round(v.eta_s) + ' 秒';
      else if(v.since_s != null) t += ' · 已等 ' + v.since_s + ' 秒';
    } else if(v.files_total != null && v.files_total > 0 && v.files_done != null){
      v.can_bar = true;
      v.pct = Math.max(0, Math.min(100, Math.floor((v.files_done / v.files_total) * 100)));
      t += ' · 已 ' + v.files_done + ' / ' + v.files_total + ' 件（' + v.pct + '%）';
      if(mn) t += ' · ' + mn;
      if(v.since_s != null) t += ' · 已等 ' + v.since_s + ' 秒';
    } else if(v.since_s != null){
      t += ' · 已等 ' + v.since_s + ' 秒' + (v.since_src === 'page' ? '（本页计时 · 后端未给已耗）' : '');
      t += (mn ? (' · ' + mn) : ' · 进度不可量（后端未给 done ／ total）');
    } else {
      t += (mn ? (' · ' + mn) : ' · 进度不可量（后端未给 done ／ total ／ 已耗）');
    }
    v.text = t + '）';
    v.note = '更新中请勿关闭服务窗口' + (v.available === null ? '（更新源头之可得性后端未给）' : '');
    return v;
  }
  if(raw === 'done' || v.phase === 'done'){
    v.state = 'done';
    v.text = '更新完成' + (v.latest ? ('：已升至 ' + v.latest) : '');
    v.note = '去处：按 F5 刷新本页看新版本';
    return v;
  }
  if(raw === 'restart' || v.phase === 'restart' || v.phase === 'restarting'){
    v.state = 'restart';
    v.text = (v.phase === 'restarting' ? '正在重启服务…' : '更新已就位 ⇒ **需重启服务**方可生效');
    v.note = '重启中页面会短暂断开，随后自动恢复（本页会自动重试）';
    return v;
  }
  if(v.available === true){
    v.state = 'available';
    v.text = '有新版 ' + (v.latest || '（版本号未给）') + (v.current ? ('（当前 ' + v.current + '）') : '')
           + (v.total != null ? (' · 约 ' + paPrepMB(v.total) + '（' + (v.files_total != null ? (v.files_total + ' 件 ') : '') + '增量）') : '');
    v.note = '去处：装根之「更新」入口（⛔ 本页发起 —— 起停归后端壳）';
    return v;
  }
  if(v.available === false){
    v.state = 'latest';
    v.text = '已是最新' + (v.current ? ('（当前 ' + v.current + '）') : '');
    return v;
  }
  v.state = 'unanswered';
  v.text = '更新面未给「有新版 ∨ 已是最新」（端之回缺 `available`）'
         + (v.current ? (' · 当前版本 ' + v.current) : '');
  v.note = '⛔ 不以「未给」充「已是最新」（承「未知 ⛔ 充知」· 候 TD 1620 之字段）';
  return v;
}

/* 顶栏之版行（令一 · 常显 · ⛔ 占横幅）：当前版本之真源 ＝ `/health.version`（⛔ 前端写死）。 */
function paUpdCurFromHealth(){
  /* 版本之真源 ＝ `/health.version`（⛔ 前端写死）：先取本件之末回，缺 ⇒ 取 `startup.js` 之末回。 */
  try{
    const h = (paUpdRun && paUpdRun.h) ? paUpdRun.h
            : ((typeof paPrepRun !== 'undefined') ? paPrepRun.h : null);
    return (h && h.version) ? String(h.version) : '';
  }catch(e){ return ''; }
}
function paUpdVerText(v){
  const cur = (v && v.current) ? v.current : paUpdCurFromHealth();
  if(!cur) return '版本 —（后端未给）· 更新面未答';
  let t = '版本 ' + cur;
  const st = v ? v.state : 'unanswered';
  if(st === 'available') t += ' · ⬆ 有新版 ' + (v.latest || '（版本号未给）')
    + (v.total != null ? ('（约 ' + paPrepMB(v.total) + '）') : '');
  else if(st === 'latest') t += ' · 已是最新';
  else if(st === 'running') t += ' · 更新中（' + (PA_UPD_PHASE[v.phase] || v.phase || '进行中') + '）';
  else if(st === 'restart') t += ' · 待重启生效';
  else if(st === 'done') t += ' · 已更新至 ' + (v.latest || cur);
  else if(st === 'failed') t += ' · 更新失败（见上）';
  else t += ' · 更新面未答（' + PA_UPD_SRC + ' 之 update 未给 · ⛔ 非「已是最新」）';
  return t;
}
function paUpdVerRender(v){
  const el = document.getElementById('paVerRow'); if(!el) return v;
  el.textContent = paUpdVerText(v);
  const st = v ? v.state : 'unanswered';
  el.style.color = (st === 'available') ? 'var(--amber)'
    : (st === 'failed' ? 'var(--red)' : (st === 'done' ? 'var(--green)' : ''));
  return v;
}

/* 轮询（一处）：常态 30 s ／ 进行中 2 s —— 与 startup.js 之横幅**同源共显**（⛔ 二套面）。 */
const paUpdRun = {started:false, t0:0, poll:null, mode:'', last:null, h:null, u:null, http:null};
function paUpdApply(){
  const v = paUpdView(paUpdRun.u, {elapsed_s:(Date.now() - paUpdRun.t0)/1000,
        http_status:paUpdRun.http, health_version:paUpdCurFromHealth()});
  paUpdRun.last = v;
  paUpdVerRender(v);
  if(typeof paPrepFeedUpdate === 'function') paPrepFeedUpdate(v);   /* ⇒ 横幅（一处渲 · 承「⛔ 二套面」） */
  return v;
}
function paUpdSetInterval(ms, mode){
  if(paUpdRun.mode === mode) return;
  if(paUpdRun.poll) clearInterval(paUpdRun.poll);
  paUpdRun.mode = mode; paUpdRun.poll = setInterval(paUpdFetch, ms);
}
async function paUpdFetch(){
  let st = 0, h = null, u = null;
  try{
    const r = await fetch(((typeof API !== 'undefined') ? API : '') + PA_UPD_SRC, {cache:'no-store'});
    st = (r && r.status) ? r.status : 0;
    if(r && r.ok){ try{ h = await r.json(); }catch(e){ h = null; } }
  }catch(e){ st = 0; h = null; }
  /* ⛔ 充知：`/health` 无 `update` 键（今之后端即此）⇒ 面书「未答」（⛔ 不等于「已是最新」）。 */
  u = (h && h.update && typeof h.update === 'object') ? h.update : null;
  paUpdRun.h = h; paUpdRun.u = u; paUpdRun.http = u ? null : (st || null);
  const v = paUpdApply();
  paUpdSetInterval((v.state === 'running' || v.state === 'restart') ? PA_UPD_BUSY_MS : PA_UPD_POLL_MS,
                   (v.state === 'running' || v.state === 'restart') ? 'busy' : 'idle');
  return v;
}
function paUpdBegin(){
  if(paUpdRun.started) return;      /* 幂等 */
  paUpdRun.started = true; paUpdRun.t0 = Date.now();
  paUpdFetch();
  paUpdSetInterval(PA_UPD_POLL_MS, 'idle');
}
try{ window.paUpdView = paUpdView; window.paUpdVerText = paUpdVerText; window.paUpdVerRender = paUpdVerRender;
     window.paUpdFetch = paUpdFetch; window.paUpdBegin = paUpdBegin; window.PA_UPD_PHASE = PA_UPD_PHASE;
     window.paUpdRun = paUpdRun; window.paUpdCurFromHealth = paUpdCurFromHealth; }catch(e){}
if(document.readyState === 'loading'){ document.addEventListener('DOMContentLoaded', paUpdBegin); }
else { paUpdBegin(); }
