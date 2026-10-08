/* ---- 壳层（桌面程序本体）更新之面 —— 一处定形（CW b2a5182 · 2026-10-08 · pm_1886 ／ pm_1890 ／ pm_1897）
   一事（老板之令「净机 desktop 版本更新升级」）：⭐ **「载荷有新版本」⛔ 等于「壳有新版本」** ⇒ 用户面上
     **二路必分**（承「等待不可用必显形」＋「产出有痕有去处」）：
     ⒜ **内容版本**（载荷）⇒ `web/pa/faces/update.js` 之 `#paVerRow` ＋ `#paUpdGo`（既有）；
     ⒝ **桌面程序（壳）** ⇒ 本件之 `#paShellUpdGo` ＋ 「更多 ▾ → 系统」之一行。
   ⭐ 桥（**一处定形** · pm_1897 §一.1 ＝ TD_1895 §三.1 采我 `1887` 为底 · ⛔ 二份字面）：
     **名** ＝ `window.paShell.shellUpdateState()` ／ `shellUpdateInstall()` ／ `onShellUpdate(cb)`；
     **返** ＝ `{ok:true, phase, current, latest, progress}` ∨ `{ok:false, code, message}`；
     **态** ＝ `unsupported ／ idle ／ checking ／ available ／ downloading ／ downloaded ／ installing ／ failed`；
     **码** ＝ `no-updater ／ offline ／ check-failed ／ download-failed ／ verify-failed ／ install-failed ／ unknown`。
   ⭐⭐ 四裁（pm_1890 §一 ／ pm_1897 §一.2 · TD 已逐裁认）：
     ⒜ **拉为唯一真源**（`shellUpdateState()`）；`onShellUpdate` 唯作「唤我再拉一次」（⛔ 各自算态 ⇒ ⛔ 二真相）；
     ⒝ **码可查**（屏唯人话 · 码入 `title` ＋ 工程注记之折叠 —— 同 `#paPrep` 之族 · ⛔ 行话上屏 ∧ ⛔ 码丢）；
     ⒞ **二路 ⛔ 混**（本 chip ⟂ `#paUpdGo` · 可同时现 · 版行与壳态**各一句**）；
     ⒟ **无新版 ⛔ 占位**（顶栏唯「有新版」∨「失败」现 · 余入「更多 ▾」之一行 ⇒ ⛔ 藏死 · 承 `pa.html:41`）。
   ⭐ 文案（pm_1893 §二 准 ＋ pm_1897 §一.4 纳 DS 之见 · 二事**分名** · ⛔ 混叫「升级」）：
     无新版 ⇒ `桌面程序（壳）版本 X · 已是最新（与内容之版本无关）`；有新版 ⇒ 顶栏 `⬆ 桌面程序更新`；
     等待 ⇒ 「等你点一下，才继续」；失败 ⇒ 「没装坏 · 可重试 · 数据在」。
   ⚠ **行话 ⛔ 上屏**（pm_1886 §二.2 · 祖链判）：`electron-updater` ／ `NSIS` ／ `blockmap` ／ `quitAndInstall`
     ／ 端径 ／ 件号 —— 本件之**注释**可载（工程之据），**用户面之文**一字 ⛔ 载（齿钉之）。
   ⚠ 界：⛔ 本件 ⛔ 触 `shell/**`（TD 之域）∧ ⛔ 自渲 `#paPrep`（其渲唯 `startup.js` 一处 · 承「⛔ 二套面」）。
   ⚠ 桥 ⛔ 出网（TD_1895 §三.2⒜）：本件唯调壳之桥 ⇒ ⛔ 自取网。 */

/* 桥之名（一处：唯此处书字面 ⇒ 改则唯改此处 · 齿钉）。 */
const PA_SHU_BRIDGE = 'paShell';
const PA_SHU_FN_STATE = 'shellUpdateState';
const PA_SHU_FN_GO = 'shellUpdateInstall';
const PA_SHU_FN_ON = 'onShellUpdate';
const PA_SHU_POLL_MS = 30000;
/* 终态自退之阈 —— **与 `startup.js` 之 `PA_PREP_TERM_HOLD_MS` 同尺**（承 pm_1886 §二.3 · 齿钉）。 */
const PA_SHU_TERM_HOLD_MS = 20000;
/* 态之集（＝桥之冻结之集 · ⛔ 自造 ∧ ⛔ 少一 —— 齿钉）。 */
const PA_SHU_PHASES = ['unsupported', 'idle', 'checking', 'available', 'downloading',
                       'downloaded', 'installing', 'failed'];
/* 失败之码（＝桥之冻结之集 · ⛔ 自造 ∧ ⛔ 少一 —— 齿钉）。 */
const PA_SHU_CODES = ['no-updater', 'offline', 'check-failed', 'download-failed',
                      'verify-failed', 'install-failed', 'unknown'];
/* 态 ⇒ 人话（用户面 · ⛔ 行话）。 */
const PA_SHU_PHASE_TXT = {
  unsupported: '本机是开发态 ⇒ 此处装不上桌面程序的更新（装好的正式版才有此能）',
  idle:        '已是最新（与内容之版本无关）',
  checking:    '正在查有无新版…',
  available:   '有新版本',
  downloading: '正在下载新版本',
  downloaded:  '新版本已下好 · 等你点一下才继续',
  installing:  '正在安装 · 别关窗',
  failed:      '更新没成'
};
/* 码 ⇒ 人话（⛔ 上屏 —— 唯入 `title` ／ 工程注记之折叠 · 裁 ⒝）。 */
const PA_SHU_CODE_TXT = {
  'no-updater':     '这一版桌面程序不带更新之能',
  offline:          '本机连不上网',
  'check-failed':   '查新版没查成',
  'download-failed':'下载没成',
  'verify-failed':  '校验没成',
  'install-failed': '安装没成',
  unknown:          '未明之故'
};
/* 去处（人话 · 唯二处：重试 ∨ 更多之系统行）。 */
const PA_SHU_OUTLET = '再点「⬆ 桌面程序更新」可重试 ∨ 「更多 ▾ → 系统」看细节';
/* 重启之**明书**（承 pm_1886 §一.2「重启前须明书」· TD_1895 §三.2⒝「由面出」）。 */
const PA_SHU_RESTART_NOTE = '点了之后：桌面程序会关掉并重开 · 本页会跟着重开（你的数据不动）';

function paShuBridge(){
  try{ return (typeof window !== 'undefined' && window[PA_SHU_BRIDGE]) ? window[PA_SHU_BRIDGE] : null; }
  catch(e){ return null; }
}
function paShuFn(name){
  const b = paShuBridge();
  try{ return (b && typeof b[name] === 'function') ? b[name].bind(b) : null; }catch(e){ return null; }
}
/* `unsupported` 之判（pm_1897 §一.5 ／ 我 `1887 §二.4` 之求）：`window.paShell` 在否 ＋ 其函在否。 */
function paShellUpdWhy(){
  const b = paShuBridge();
  if(!b) return 'browser';                                   /* 本页 ⛔ 在桌面程序内 */
  if(!paShuFn(PA_SHU_FN_STATE)) return 'old-shell';           /* 壳在 · 然 ⛔ 带此能 */
  return '';
}
function paShellUpdSupported(){ return paShellUpdWhy() === ''; }

function paShuNum(v){ return (typeof v === 'number' && isFinite(v)) ? v : null; }
function paShuHas(x, arr){ return arr.indexOf(String(x == null ? '' : x).trim()) >= 0; }
function paShuMB(n){
  const v = paShuNum(n);
  if(v == null) return '—';
  if(v >= 1048576) return (v / 1048576).toFixed(1) + ' MB';
  if(v >= 1024) return (v / 1024).toFixed(0) + ' KB';
  return v + ' B';
}
/* 「可点」之集（一处）：有新版 ⇒ 起更新；已下好 ⇒ 「重启并安装」；失败 ⇒ 重试。 */
function paShuCanStart(state){ return (state === 'available' || state === 'wait' || state === 'failed'); }
function paShuChipTxt(state){
  if(state === 'wait') return '⟳ 重启并安装（桌面程序）';
  if(state === 'failed') return '⬆ 桌面程序更新（没成 · 可重试）';
  if(state === 'running') return '正在更新桌面程序…';
  if(state === 'launching') return '已交给桌面程序安装…';
  return '⬆ 桌面程序更新';
}

/* ⭐⭐ 一处：桥之回 ⇒ 面之视图（⛔ DOM · 供齿之直调）。`local` ＝ 面之短告（唯一点之后 · ⛔ 态）。 */
function paShellUpdView(r, local, ctx){
  const now = (paShuNum(ctx && ctx.now) != null) ? ctx.now : Date.now();
  const v = {state:'unsupported', phase:'unsupported', code:'', current:'', latest:'',
             progress:null, pct:null, can_bar:false, can_start:false, text:'', note:'',
             term_deadline:null, term_key:'', why:paShellUpdWhy()};
  if(v.why){
    const b = paShuBridge();
    v.text = b ? '这一版桌面程序不带更新之能（须先装一次新版桌面程序）'
               : '本页在浏览器里打开 ⇒ 桌面程序之更新不在此处';
    v.note = '真源：桌面程序本体（唯在桌面程序内有此能）';
    return v;
  }
  /* 拉之回（唯一真源）。 */
  if(r && r.ok === false){
    v.state = 'failed'; v.phase = 'failed';
    v.code = paShuHas(r.code, PA_SHU_CODES) ? String(r.code) : 'unknown';
    v.can_start = true;
    v.text = '更新没成 —— 没装坏 · 可重试 · 数据在';
    v.note = (PA_SHU_CODE_TXT[v.code] || PA_SHU_CODE_TXT.unknown) + ' · ' + PA_SHU_OUTLET;
    return v;
  }
  const ph = (r && r.ok === true && paShuHas(r.phase, PA_SHU_PHASES)) ? String(r.phase).trim() : 'idle';
  v.phase = ph;
  v.current = (r && r.current != null) ? String(r.current) : '';
  v.latest = (r && r.latest != null) ? String(r.latest) : '';
  const pr = (r && r.progress && typeof r.progress === 'object') ? r.progress : null;
  const tot = pr ? paShuNum(pr.total) : null;
  if(tot && tot > 0){
    const done = paShuNum(pr.done) || 0;
    v.progress = {done:done, total:tot};
    v.pct = Math.max(0, Math.min(100, Math.round(done * 100 / tot)));
    v.can_bar = true;
  }
  if(ph === 'downloading' || ph === 'installing') v.state = 'running';
  else if(ph === 'downloaded') v.state = 'wait';
  else if(ph === 'available') v.state = 'available';
  else if(ph === 'failed') v.state = 'failed';
  else if(ph === 'unsupported') v.state = 'unsupported';
  else v.state = 'quiet';
  v.can_start = paShuCanStart(v.state);
  /* 面之短告（唯一点之后 · 20 s 自退）：壳之真态**已明**（在办 ／ 败）⇒ 短告 ⛔ 盖之
     （拉为唯一真源）；余者（可升 ／ 已下好待点 ／ 已是最新）⇒ 短告现 ∧ ⛔ 可点
     （免得「点二次 ⇒ 交壳二回」）—— 到期（20 s）⇒ 自退 ∧ 真态复现（⛔ 长锁）。 */
  if(local && local.kind === 'launching' && v.state !== 'running' && v.state !== 'failed'){
    v.state = 'launching'; v.phase = 'launching'; v.can_start = false;
    v.text = '已交给桌面程序安装 · 请别关窗（本页会跟着重开）';
    v.note = PA_SHU_RESTART_NOTE;
    v.term_deadline = (paShuNum(local.at) != null ? local.at : now) + PA_SHU_TERM_HOLD_MS;
    v.term_key = 'shu|launching';
    return v;
  }
  /* 文案（人话 · 二事分名 ⇒ 一句必带「桌面程序」）。 */
  if(v.state === 'available'){
    v.text = '桌面程序有新版本' + (v.latest ? ('（' + v.latest + '）') : '') + '可更新 · 等你点一下，才继续';
    v.note = '更新的是桌面程序本体（与内容之版本无关）· 唯由你之点';
  } else if(v.state === 'running' && ph === 'downloading'){
    v.text = '正在更新桌面程序 · 正在下载新版本'
           + (v.progress ? ('（已下 ' + paShuMB(v.progress.done) + ' ／ ' + paShuMB(v.progress.total) + '）') : '');
    v.note = '下载中 ⇒ 可继续用 · 别关窗';
  } else if(v.state === 'running'){
    v.text = '正在更新桌面程序 · 正在安装 · 别关窗';
    v.note = PA_SHU_RESTART_NOTE;
  } else if(v.state === 'wait'){
    v.text = '桌面程序之新版本已下好 · 等你点「重启并安装」才继续';
    v.note = PA_SHU_RESTART_NOTE;
  } else if(ph === 'checking'){
    v.text = '正在查桌面程序有无新版…';
  } else if(ph === 'unsupported'){
    v.text = PA_SHU_PHASE_TXT.unsupported;
  } else {
    v.text = '桌面程序（壳）版本 ' + (v.current || '—（桌面程序未给）') + ' · 已是最新（与内容之版本无关）';
  }
  return v;
}

/* ---- 渲（**唯此一处**写壳之诸件 —— 顶栏 chip ＋ 「更多」之行 ＋ 工程注记） ---- */
function paShellUpdRender(v){
  v = v || paShellUpdView(null, null, null);
  const doc = (typeof document !== 'undefined') ? document : null;
  /* ⒜ 顶栏 chip：唯「有新版」∨「失败」∨「在办」现（裁 ⒟ · ⛔ 常驻占位）。 */
  const chip = doc ? doc.getElementById('paShellUpdGo') : null;
  if(chip){
    const on = (v.state !== 'quiet' && v.state !== 'unsupported');
    chip.style.display = on ? '' : 'none';
    chip.disabled = !v.can_start;
    if(on){
      chip.textContent = paShuChipTxt(v.state);
      /* ⭐⭐ pm_1909 §二.2 之一加（我之补 · 认）：**可升**态之 `title` 须载「有新版本 X ⇒
         点一下 ⇒ 交桌面程序去下装」＋**去处** ⇒ 使「点了会怎样」**可查**（承 pa.html:41 之律）。
         其数（版号）唯取自桥之回（v.latest ⇒ ⛔ 硬编 · 齿钉）∧ ⛔ 行话上屏。 */
      const mid = (v.state === 'available')
        ? ('有新版本' + (v.latest ? ('（' + v.latest + '）') : '') + ' ⇒ 点一下 ⇒ 交桌面程序去下载并安装 ·'
           + ' 去处：详情在「更多 ▾ → 系统」那一行 · ')
        : '';
      chip.title = '更新桌面程序本体（与内容之版本无关）· 唯由你之点 · ' + mid + PA_SHU_RESTART_NOTE
                 + (v.code ? (' ｜ 码：' + v.code) : '');
    }
  }
  /* ⒝ 「更多 ▾ → 系统」之一行（常显 · 可查 —— 裁 ⒟）。 */
  const row = doc ? doc.getElementById('paShellVer') : null;
  if(row){
    row.textContent = v.why
      ? (v.why === 'browser' ? '本页在浏览器里 ⇒ 此处装不上桌面程序的更新'
                            : '这一版桌面程序不带更新之能')
      : ((v.current || '—（桌面程序未给）') + ' · ' + PA_SHU_PHASE_TXT[v.phase]
         + (v.latest && v.state === 'available' ? ('（' + v.latest + '）') : ''));
    row.title = '真源：桌面程序本体（唯在桌面程序内有此能）· ' + PA_SHU_RESTART_NOTE
              + (v.code ? (' ｜ 码：' + v.code) : '');
  }
  /* ⒞ 工程注记之折叠（裁 ⒝：**码可查** · 屏上 ⛔ 载）。 */
  const eng = doc ? doc.getElementById('paShellUpdEng') : null;
  if(eng){
    const parts = [];
    parts.push('态：' + v.phase + '（面之视图：' + v.state + '）');
    parts.push('码：' + (v.code || '（无）'));
    if(v.why) parts.push('此能之判：' + (v.why === 'browser' ? '本页 ⛔ 在桌面程序内' : '桌面程序 ⛔ 带此能'));
    parts.push('取数：拉为唯一真源 · 常态每 ' + Math.round(PA_SHU_POLL_MS / 1000) + ' s 一次');
    eng.textContent = parts.join(' ｜ ');
  }
  return v;
}

/* ⭐ **一处定形**（本面之视图 ⇒ 渲 ＋ 投横幅）：唯此一处 —— ⛔ 散在各支（承「⛔ 二套面」）。
   渲写给 `#paShellUpdGo` ／ `#paShellVer` ／ `#paShellUpdEng`（`paShellUpdRender`）；
   投横幅给 `startup.js` 之 `paPrepFeedShell`（其渲唯 `startup.js` 一处 —— ⛔ 本件 ⛔ 触 `#paPrep`）。 */
function paShuPublish(v){
  paShuRun.last = v;
  paShellUpdRender(v);
  if(typeof paPrepFeedShell === 'function') paPrepFeedShell(v);   /* ⇒ 横幅（一处渲 · ⛔ 二套面） */
  return v;
}
/* ---- 取数（**拉** · 唯此一源） ---- */
const paShuRun = {started:false, t0:0, poll:null, last:null, local:null};
async function paShellUpdFetch(){
  let r = null;
  const f = paShuFn(PA_SHU_FN_STATE);
  if(f){
    try{ r = await f(); }catch(e){ r = {ok:false, code:'unknown', message:String(e && e.message)}; }
  }
  /* 短告之命（一处判）：壳之真态**已明**（在办 ／ 败）⇒ 短告退 ∧ 逾阈（20 s）⇒ 退。 */
  if(paShuRun.local){
    const lv = paShellUpdView(r, paShuRun.local, null);
    if(lv.state !== 'launching') paShuRun.local = null;
    else if(lv.term_deadline != null && Date.now() >= lv.term_deadline) paShuRun.local = null;
  }
  paShuRun.t0 = Date.now();
  return paShuPublish(paShellUpdView(r, paShuRun.local, null));
}
function paShuSetInterval(ms){
  if(paShuRun.poll) clearInterval(paShuRun.poll);
  paShuRun.poll = setInterval(paShellUpdFetch, ms);
}
/* ⭐ 点「⬆ 桌面程序更新」／「⟳ 重启并安装」—— **唯由用户之点**（⛔ 静默装 · pm_1886 §一.2）。 */
async function paShellUpdGo(){
  const f = paShuFn(PA_SHU_FN_GO);
  const v0 = paShuRun.last;
  if(!f || !v0 || !v0.can_start){ return v0; }        /* 幂等：⛔ 非「可点」⇒ ⛔ 发 */
  let r = null;
  try{ r = await f(); }catch(e){ r = {ok:false, code:'unknown', message:String(e && e.message)}; }
  if(r && r.ok === false){
    return paShuPublish(paShellUpdView({ok:false, code:r.code, message:r.message}, null, null));
  }
  paShuRun.local = {kind:'launching', at:Date.now()};      /* 短告（20 s 自退） */
  return await paShellUpdFetch();
}
function paShellUpdBegin(){
  if(paShuRun.started) return;                  /* 幂等 */
  paShuRun.started = true; paShuRun.t0 = Date.now();
  /* 推唯作「唤我再拉一次」（裁 ⒜ · ⛔ 各自算态）。 */
  const on = paShuFn(PA_SHU_FN_ON);
  if(on){ try{ on(function(){ paShellUpdFetch(); }); }catch(e){} }
  paShellUpdFetch();
  paShuSetInterval(PA_SHU_POLL_MS);
}
try{ window.paShellUpdView = paShellUpdView; window.paShellUpdRender = paShellUpdRender;
     window.paShellUpdFetch = paShellUpdFetch; window.paShellUpdGo = paShellUpdGo;
     window.paShellUpdBegin = paShellUpdBegin; window.paShellUpdSupported = paShellUpdSupported;
     window.paShellUpdWhy = paShellUpdWhy; window.paShuRun = paShuRun;
     window.PA_SHU_PHASES = PA_SHU_PHASES; window.PA_SHU_CODES = PA_SHU_CODES;
     window.PA_SHU_TERM_HOLD_MS = PA_SHU_TERM_HOLD_MS; window.PA_SHU_POLL_MS = PA_SHU_POLL_MS; }catch(e){}
if(typeof document !== 'undefined'){
  if(document.readyState === 'loading'){ document.addEventListener('DOMContentLoaded', paShellUpdBegin); }
  else { paShellUpdBegin(); }
}
