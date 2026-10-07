/* ---- 更新环节之可见之面（CW b2a5182 · 2026-10-07 · pm_1621 四条 · 承 TD_1620 之后端半）
   老板之令（逐字）：「现阶段我们作为内测，做好 `update` 环节」⇒ ⭐ 判：**「更新」最易被误判为「坏了」**
     （下载慢 ／ 替换中 ／ 需重启）⇒ 承 pm 之新规（pm_1617 §一.3）：**凡等待必有提示 ＋ 进度 ＋ 时长；
     凡不可用必有因 ＋ 去处；凡提示须在用户当下看得见之处** —— 此规于「更新」尤要。
   ⭐ **取数（一处）**：**读** 唯 `/health`（既有端 · 与 `startup.js` 同源 ⇒ 一处取数）之 `update` 键 ⇒ 得「可得性」；
      **动** 唯 `POST /v9/pa/update` ⇒ 得「跑」之相位 ＋ 起一支 ⇒ ⭐「**读一处 · 动分端**」（pm_1641 裁 ①）。
   ⭐⭐ **本件之新（pm_1691 令 ⇒ 面内之「更新」按钮）**：端已挂（TD `c5a41ff`）⇒ 昔之注「⛔ 引未挂之 `/v9/pa/*`」**今正**：
      该端**已挂** ⇒ 面册闸（`tests/unit/test_pa_ui_faces.py`）之「悬」仍空（引之正当 —— 承「凡面之支须能真达」）。
   ⭐⭐ **端名与字段之逐字 ⇒ 已对齐 `TD_1644 §三.1`**（2026-10-07 落 · 承 pm_1621 §一.2「字段 ⛔ 自造」／
      pm_1641 §一.3「唯改其读键」）：读（**逐字**）`available`｜`current_version`｜`latest_version`｜
      `size_bytes`（**清单之真数** —— TD §三.3「⛔ 硬编」）｜`note`（**后端之辞**：三态之「已是最新」／
      「未接」／「取不得」**皆由 `note` 之逐字承** ⇒ 本面 **照书** · ⛔ 自造其由 —— 承 pm_1638 之裁）｜
      `channel` ／ `checked_at` ／ `manifest_url`（**候裁**：本面今 ⛔ 显 —— ⛔ 擅自加辞）。
     ⚠ **进度之诸键**（`state` ／ `phase` ／ `done_bytes` ／ `total_bytes` ／ `eta_s` ／ `since_s` ／
      `files_done` ／ `files_total` ／ `rolled_back` ／ `rollback_to`）⇒ **`/health.update` 之白名单 ⛔ 给**
      （一手核 `core/lib/update_check.py` 之 `face()` ⇒ 唯 9 键 · ⛔ 含 `phase` ／ `root`）⇒ 「跑」之相位唯
      `POST /v9/pa/update` 给（`phase` ／ `from` ／ `to` ／ `started_at` ／ `ended_at` ／ `note` ／ `files`）；
      细分之进度（`done_bytes` 等）**今仍 ⛔ 给** ⇒ 其支 **照实报**（⛔ 擅删 ／ ⛔ 造数 —— 乃 pm_1621 令二之的）。
     `error`（**人话** · ⛔ 原始异常 —— 原始因入机器字段 `last_error` ／ `note_why` ⇒ 本件 ⛔ 读）。
   ⛔ 本件 ⛔ 触 `core/**`（TD 之域）∧ ⛔ 自渲 `#paPrep`（其渲唯 `startup.js` 一处 · 承「⛔ 二套面」）。
   ⛔ 本件 ⛔ 起停（器之起停归后端）∧ **`start` 唯由用户之点**（pm_1691 §二.2）—— 本件唯**显示** ＋ 承其点。 */

/* ⚠ **读**（一处）：`/health`（既有端）之 `update` 键 —— 可得性之真源（⛔ 第二读源）。 */
const PA_UPD_SRC = '/health';
/* ⭐⭐ **动**（一处 · 契约承 pm_1684 §四）：`POST /v9/pa/update` ——
   `{"action":"status"}` ⇒ **唯读**（轮询用 · ⛔ 副作用）｜`{"action":"start"}` ⇒ 起一支（**唯由用户之点**）。 */
const PA_UPD_POST = '/v9/pa/update';
const PA_UPD_POLL_MS  = 30000;        /* 常态之巡 */
const PA_UPD_BUSY_MS  = 2000;         /* 更新进行中 ⇒ 密巡（进度须活） */
/* 已终之跑（`done` ／ `failed`）显报之窗（秒）：逾 ⇒ 归 `/health` 之真读数（⛔ 长挂「需重启」＝ 面之假）。
   ⭐ pm_1693 §四.3 裁准 ＝ `3600`（一时）· **一处定形**（⛔ 散数 —— 阈唯此一处 · 齿在）。 */
const PA_UPD_RECENT_S = 3600;

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
  'done': '更新完成',
  'running': '后端在跑（⛔ 给细分步骤）'
};
/* 日志之径（**一处** · 逐字取壳之同辞）：壳侧「因 ＋ 去处」即书此（`shell/update.js` ／ `shell/identity.js`）。 */
const PA_UPD_LOG = '%LOCALAPPDATA%\\ClawsJoyPA\\shell\\shell.log';
const PA_UPD_OUTLET = '去处：再点「更新」重试 ∨ 看服务窗口之日志（壳内：' + PA_UPD_LOG + '）';
/* ⚠ 「去处」之二形（**一处定形**）：`FAIL` ⇒ 可**再点**（按钮在）；`SELF` ⇒ 此刻**无可点之钮** ⇒ 唯本页自巡
   （⛔ 指「点按钮」而 ⛔ 有其钮 —— 承「凡面之支须能真达」之对偶：⛔ 指不可达之路）。 */
const PA_UPD_OUTLET_SELF = '去处：本页会自动重试（重读可得性）∨ 看服务窗口之日志（壳内：' + PA_UPD_LOG + '）';

/* 时戳之差（秒）：`"%Y-%m-%dT%H:%M:%S%z"` ⇒ 已过之秒（后端之刻为本地时 ⇒ 截前十九字按本地解）。
   ⛔ 解 ⇒ `null`（照实 —— ⛔ 以 0 充「刚刚」）。 */
function paUpdAgeS(ts){
  if(!ts) return null;
  const t = Date.parse(String(ts).slice(0, 19).replace('T', ' '));
  if(isNaN(t)) return null;
  return Math.max(0, Math.floor((Date.now() - t) / 1000));
}

/* ⭐ **一处定形**（纯函数 · ⛔ DOM）：更新端之回 ＋ 本地之钟 ⇒ 面之态。
   `u` ＝ 端之 JSON（未答 ⇒ null）；`ctx` ＝ {elapsed_s, http_status, health_version}。
   回 {state, phase, text, note, bnote, can_bar, pct, done, total, prog_total, eta_s, since_s,
       since_src, current, latest, available, files_done, files_total, rolled_back, src}
   （`state` ∈ unanswered ／ latest ／ unchecked ／ available ／ running ／ restart ／ done ／ failed；
     ⭐ `unchecked` ＝ 「`available === false` 而**后端未自书「已是最新」**」之第四态 ——
     其字面 **照书后端之 `note`**（如「取清单 ⛔ 得：…」／「未接（甲-P0）」）· ⛔ 冒「已是最新」。） */
function paUpdView(u, ctx){
  const c  = (ctx && typeof ctx === 'object') ? ctx : {};
  const o  = (u && typeof u === 'object') ? u : null;
  const ss = function(x){ return (x == null) ? '' : String(x).trim(); };
  /* ⭐⭐ 「跑」之相位（`POST /v9/pa/update` 之回 · pm_1684 §四 契约）：`idle ／ running ／ done ／ failed`。
     ⚠ 与 `/health.update` **二物**：彼唯「可得性」，此唯「跑」⇒ `running` ／ `done` ／ `failed` 之相由此出
       （⛔ 于 `/health` 之白名单 —— 一手核 `core/lib/update_check.py::face()`）。 */
  const run   = (c.run && typeof c.run === 'object') ? c.run : null;
  const rph   = run ? ss(run.phase) : '';
  const rnote = run ? ss(run.note) : '';
  const rfrom = run ? ss(run.from) : '';
  const rto   = run ? ss(run.to) : '';
  const rver  = (rto && rto !== rfrom) ? (rfrom ? (rfrom + ' ⇒ ' + rto) : ('⇒ ' + rto)) : '';
  const rsince = run ? paUpdAgeS(run.started_at) : null;
  const rage   = run ? paUpdAgeS(run.ended_at) : null;
  /* 「动」在跑（∨ 本页已知在跑而端此刻未答 —— 服务自停之窗 ⇒ ⛔ 回落「未答」，照实显「进行中」）。 */
  const rlive  = (c.run_live === true) || (rph === 'running');
  /* 已终之跑 ⇒ 唯「近事」显（逾 `PA_UPD_RECENT_S` ⇒ 归 `/health` 之真读数 —— ⛔ 长挂旧事）。 */
  const rfresh = (rph === 'running') || (rage != null && rage <= PA_UPD_RECENT_S);
  const el = paPrepNum(c.elapsed_s);
  const elR = (el == null) ? null : Math.max(0, Math.round(el));
  const v = {state:'unanswered', phase:'', text:'', note:'', bnote:'', can_bar:false, pct:null,
             done:null, total:null, prog_total:null, eta_s:null, since_s:null, since_src:'',
             current:'', latest:'', available:null, files_done:null, files_total:null,
             rolled_back:null, can_start:false, src:PA_UPD_SRC};
  if(!o){
    if(rlive){
      v.state = 'running'; v.phase = 'running';
      v.since_s = (rsince != null) ? rsince : elR;
      v.since_src = (rsince != null) ? 'backend' : (elR == null ? '' : 'page');
      v.text = '更新进行中…（服务正在重启之窗内 —— 二端此刻俱未答'
             + (v.since_s != null ? (' · 已等 ' + v.since_s + ' 秒') : '') + '）';
      v.note = '本页会自动重试（无需你操作 —— 面之自动重试）· ⛔ 充「已完成」';
      return v;
    }
    v.text = '更新面未答（' + PA_UPD_SRC + ' 之 update 未给' + (c.http_status ? (' · HTTP ' + c.http_status) : ' · 连不上') + '）';
    v.note = '⛔ 不等于「已是最新」（承「未知 ⛔ 充知」）｜' + PA_UPD_OUTLET_SELF;
    return v;
  }
  const bak = paPrepNum(o.since_s);
  v.phase = ss(o.phase);
  /* ⭐ 键名 ⇒ **逐字取 `TD_1644 §三.1`**（一处对齐 · 见件首）—— ⛔ 旧拟名 `current` ／ `latest`（**臆造**）。 */
  v.current = ss(o.current_version) || ss(c.health_version);
  v.latest = ss(o.latest_version);
  v.available = (typeof o.available === 'boolean') ? o.available : null;
  v.bnote = ss(o.note);                       /* 后端之辞（**照书** · ⛔ 自造 —— 承 pm_1638 之裁） */
  const sz = paPrepNum(o.size_bytes);         /* 清单之真数（TD §三.3：⛔ 硬编「0.6 MB」） */
  v.total = (sz != null && sz > 0) ? sz : null;
  v.done = paPrepNum(o.done_bytes); v.prog_total = paPrepNum(o.total_bytes);
  v.eta_s = paPrepNum(o.eta_s);
  v.files_done = paPrepNum(o.files_done); v.files_total = paPrepNum(o.files_total);
  v.rolled_back = (typeof o.rolled_back === 'boolean') ? o.rolled_back : null;
  v.since_s = (bak == null) ? elR : Math.round(bak);
  v.since_src = (bak == null) ? (elR == null ? '' : 'page') : 'backend';
  /* ⭐⭐ 「动」之相 ⇒ 面之态（**先于可得性** —— 跑起来之后，「有新版」已非当下之要）。
     `can_start` ＝ `available === true` ∧ ⛔ 在跑（按钮之位 ⇒ 唯此处出 —— 承「凡面之支须能真达」）。 */
  v.can_start = (v.available === true) && !rlive;
  if(rlive){
    v.state = 'running'; v.phase = 'running';
    v.since_s = (rsince != null) ? rsince : elR;
    v.since_src = (rsince != null) ? 'backend' : (elR == null ? '' : 'page');
    v.text = '正在更新…（' + (PA_UPD_PHASE[v.phase] || v.phase)
           + (v.since_s != null ? (' · 已等 ' + v.since_s + ' 秒') : '')
           + (v.since_src === 'page' ? ' · 本页计时' : '') + '）';
    v.note = '进度不可量（后端 ⛔ 给细分步骤 ／ 已下之量 —— ⛔ 造数）· 更新中请勿关闭服务窗口'
           + '；服务会短暂重启，本页会自动重试';
    return v;
  }
  if(rph === 'done' && rfresh){
    v.state = 'done';
    v.text = '更新已完成' + (rver ? ('：' + rver) : '') + ' · 已就绪';
    v.note = (rnote ? (rnote + ' ／ ') : '')
           + '服务已自重启；若本页仍旧 ⇒ 需重启本页（按 F5 刷新）· 本页会自动重试';
    return v;
  }
  if(rph === 'failed' && rfresh){
    v.state = 'failed';
    v.text = '更新失败' + (rnote ? ('：' + rnote) : '（后端未给因）');
    v.note = '回滚之数与旧版之号**唯后端之辞为凭**（⛔ 自造 ／ ⛔ 猜）· ' + PA_UPD_OUTLET;
    return v;
  }
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
    /* ⭐ pm_1633 裁 ⒝（一处定形 · 与 `startup.js` 共本函）：`measured ∧ ⛔ total` ⇒ 显「已下 X MB（总长不可量）」。
       ⚠ pm_1638 裁（去重）：**其辞唯 `startup.js` 一处** —— 本面 **⛔ 传 `note`**（更新回之字段名
          候 TD `1620` 之报 ⇒ 唯改本行一处加第三参 ⇒ 承 pm_1621 §一.2「字段 ⛔ 自造」）⇒ 本面走 ⒝ 之回落。 */
    const mn = paPrepMeasuredNote(v.done, v.prog_total);
    let t = '正在更新…（' + ph;
    if(v.prog_total != null && v.prog_total > 0 && v.done != null){
      v.can_bar = true;
      v.pct = Math.max(0, Math.min(100, Math.floor((v.done / v.prog_total) * 100)));
      t += ' · 已下 ' + paPrepMB(v.done) + ' / ' + paPrepMB(v.prog_total) + '（' + v.pct + '%）';
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
    v.note = '去处：点本行右侧之「更新」按钮（本页发起 · 器之起停归后端）';
    return v;
  }
  if(v.available === false){
    /* ⭐⭐ **⛔ 以 `available === false` 充「已是最新」**（承「未知 ⛔ 充知」· pm_1629 之守）。
       `false` 有**二义**（TD_1644 §三.1 ⒜⒞ ＋ §三.3）：**已是最新**（其 `note` 逐字书之）∨
       **取不得 ／ 未接**（`note` 照实，如今之「取清单 ⛔ 得：<url>」）⇒ 唯后端**自书**「已是最新」
       方书之；否则 **照书后端之 `note`**（⛔ 前端自造 ／ ⛔ 冒「已是最新」—— 此即 2026-10-07 真活端所逮之 **假报**）。 */
    if(v.bnote === '已是最新'){
      v.state = 'latest';
      v.text = '已是最新' + (v.current ? ('（当前 ' + v.current + '）') : '');
      return v;
    }
    v.state = 'unchecked';
    v.text = v.bnote ? v.bnote : '更新读数 ⛔ 得（后端 ⛔ 给因）';
    v.note = '⛔ 非「已是最新」（承「未知 ⛔ 充知」）｜' + PA_UPD_OUTLET_SELF;
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
  /* 版本之真源（**一处** · pm_1641 裁 ①「读一处（`/health`）· 动分端（`/v9/pa/*`）」）：
     ⒜ `/health.build.version`（装根之版 —— 装时方生）⇒ 有则用之；
     ⒝ 缺（装前 ／ 旧包 ⇒ `build.available=false`）⇒ 回落 `/health.version`（进程之版）。
     ⛔ 前端写死 ∧ ⛔ 引 `/v9/pa/*`（机器 ／ 运维之端 —— ⛔ 供面）。先取本件之末回，缺 ⇒ 取 `startup.js` 之末回。 */
  try{
    const h = (paUpdRun && paUpdRun.h) ? paUpdRun.h
            : ((typeof paPrepRun !== 'undefined') ? paPrepRun.h : null);
    if(!h) return '';
    const bv = (h.build && h.build.version) ? String(h.build.version).trim() : '';
    if(bv) return bv;
    return h.version ? String(h.version) : '';
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
  else if(st === 'unchecked') t += ' · ' + ((v && v.bnote) ? v.bnote : '更新读数 ⛔ 得');
  else if(st === 'running') t += ' · 更新中（' + ((v.since_s != null) ? ('已等 ' + v.since_s + ' 秒')
    : (PA_UPD_PHASE[v.phase] || v.phase || '进行中')) + '）';
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

/* ⭐⭐ 面内之「更新」按钮（pm_1691 令 · §二.1）：**唯 `can_start` 时现** ——
   `can_start` ＝ `available === true` ∧ ⛔ 在跑（承「凡面之支须能真达」：⛔ available ⇒ 按钮 ⛔ 出）。
   文案之数**唯后端**（`latest_version` ／ `size_bytes` · ⛔ 自造 ／ ⛔ 硬编版号）。 */
function paUpdBtnRender(v){
  const el = document.getElementById('paUpdGo'); if(!el) return v;
  const on = !!(v && v.can_start);
  el.style.display = on ? '' : 'none'; el.disabled = !on;
  if(on){
    el.textContent = '⬆ 更新到 ' + (v.latest || '新版')
                   + (v.total != null ? ('（约 ' + paPrepMB(v.total) + '）') : '');
    el.title = '点 ⇒ POST ' + PA_UPD_POST + ' 体 {"action":"start"}（唯本机 · 唯由你之点）';
  }
  return v;
}

/* 轮询（一处）：常态 30 s ／ 进行中 2 s —— 与 startup.js 之横幅**同源共显**（⛔ 二套面）。 */
const paUpdRun = {started:false, t0:0, poll:null, mode:'', last:null, h:null, u:null, run:null, live:false, http:null};
function paUpdApply(){
  const v = paUpdView(paUpdRun.u, {elapsed_s:(Date.now() - paUpdRun.t0)/1000,
        http_status:paUpdRun.http, health_version:paUpdCurFromHealth(),
        run:paUpdRun.run, run_live:paUpdRun.live});
  paUpdRun.last = v;
  paUpdVerRender(v);
  paUpdBtnRender(v);
  if(typeof paPrepFeedUpdate === 'function') paPrepFeedUpdate(v);   /* ⇒ 横幅（一处渲 · 承「⛔ 二套面」） */
  return v;
}
function paUpdSetInterval(ms, mode){
  if(paUpdRun.mode === mode) return;
  if(paUpdRun.poll) clearInterval(paUpdRun.poll);
  paUpdRun.mode = mode; paUpdRun.poll = setInterval(paUpdFetch, ms);
}
/* ⭐ 「动」端之调（**一处**）：`action` 唯二值 —— `status`（唯读 · 轮询）／`start`（唯由用户之点）。 */
async function paUpdPost(action){
  let st = 0, j = null;
  try{
    const r = await fetch(((typeof API !== 'undefined') ? API : '') + PA_UPD_POST,
                          {method:'POST', cache:'no-store', headers:{'Content-Type':'application/json'},
                           body: JSON.stringify({action:action})});
    st = (r && r.status) ? r.status : 0;
    if(r && r.ok){ try{ j = await r.json(); }catch(e){ j = null; } }
  }catch(e){ st = 0; j = null; }
  return {st:st, j:(j && typeof j === 'object') ? j : null};
}
async function paUpdFetch(){
  let st = 0, h = null, u = null;
  try{
    const r = await fetch(((typeof API !== 'undefined') ? API : '') + PA_UPD_SRC, {cache:'no-store'});
    st = (r && r.status) ? r.status : 0;
    if(r && r.ok){ try{ h = await r.json(); }catch(e){ h = null; } }
  }catch(e){ st = 0; h = null; }
  /* ⛔ 充知：`/health` 无 `update` 键（**TD 之今版已挂此键** ⇒ 此支唯备于旧后端）⇒ 面书「未答」（⛔ 不等于「已是最新」）。 */
  u = (h && h.update && typeof h.update === 'object') ? h.update : null;
  /* ⭐⭐ 「跑」之相位（**唯读** —— `status` · ⛔ 副作用 · 承 pm_1691 §二.2 令二要件）：
     ⚠ 此端 ⛔ 答（未挂 ／ 服务重启之窗）⇒ `run` **留空**（⛔ 充）∧ `live` **守末知** ⇒ `!o` 时照实显「进行中」。 */
  const p = await paUpdPost('status');
  let run = null;
  if(p.j){
    const ph = String(p.j.phase || '').trim();
    if(ph === 'idle'){ paUpdRun.live = false; }
    else { run = p.j; paUpdRun.live = (ph === 'running'); }
  }
  paUpdRun.h = h; paUpdRun.u = u; paUpdRun.http = u ? null : (st || null);
  paUpdRun.run = run;
  const v = paUpdApply();
  paUpdSetInterval((v.state === 'running' || v.state === 'restart') ? PA_UPD_BUSY_MS : PA_UPD_POLL_MS,
                   (v.state === 'running' || v.state === 'restart') ? 'busy' : 'idle');
  return v;
}
/* ⭐⭐ 起一支（**唯由用户之点** · pm_1691 §二.2）：幂等 —— ⛔「可起」⇒ ⛔ 发（⛔ 起第二支）。 */
async function paUpdGo(){
  const v = paUpdRun.last;
  if(!v || !v.can_start) return v;                 /* 幂等：⛔ 起第二支 */
  paUpdRun.live = true;
  const p = await paUpdPost('start');
  if(p.j){ paUpdRun.run = p.j; paUpdRun.live = (String(p.j.phase || '').trim() === 'running'); }
  paUpdSetInterval(paUpdRun.live ? PA_UPD_BUSY_MS : PA_UPD_POLL_MS, paUpdRun.live ? 'busy' : 'idle');
  return paUpdApply();
}
function paUpdBegin(){
  if(paUpdRun.started) return;      /* 幂等 */
  paUpdRun.started = true; paUpdRun.t0 = Date.now();
  paUpdFetch();
  paUpdSetInterval(PA_UPD_POLL_MS, 'idle');
}
try{ window.paUpdView = paUpdView; window.paUpdVerText = paUpdVerText; window.paUpdVerRender = paUpdVerRender;
     window.paUpdFetch = paUpdFetch; window.paUpdBegin = paUpdBegin; window.PA_UPD_PHASE = PA_UPD_PHASE;
     window.paUpdRun = paUpdRun; window.paUpdCurFromHealth = paUpdCurFromHealth;
     window.paUpdBtnRender = paUpdBtnRender; window.paUpdAgeS = paUpdAgeS; window.paUpdGo = paUpdGo; }catch(e){}
if(document.readyState === 'loading'){ document.addEventListener('DOMContentLoaded', paUpdBegin); }
else { paUpdBegin(); }
