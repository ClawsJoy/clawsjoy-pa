/* ---- 本机体检（只读 · 七面 · 一阶段）（CW b2a5182 · 2026-10-07 · 令 pm_1750 二 ／ pm_1753 一–二 ／ pm_1765 二–三）

   ⭐ 端（二 · 皆唯读 · 皆本机闸）：
     ⒜ `GET /v9/pa/sys/snapshot` —— 七面之合体（一屏 ＝ 一次取）；`?fresh=1` ⇒ 真扫。
     ⒝ `GET /v9/pa/sys/<面>` —— 单面（本面今唯用 ⒜ ⇒ 一屏一取 · ⛔ 七次）。
     远机 ⇒ 403（本面照实显「唯本机」—— ⛔ 装成空读数）。

   ⭐ 守（一阶段之四条 · 不可越）：
     唯读（⛔ 写盘 ／ ⛔ 改注册表 ／ ⛔ 起停服务 ／ ⛔ 提权静默）；⛔ 出机；
     去处唯「指路之辞」（⛔ 起进程 —— 一按即起 ＝ 二阶段 · ⛔ 本面）；
     屏上之字须可选中复制（textarea readonly ＋ 「全选复制」）。

   ⭐ 一处定形：五件套（人话 ／ 读数 ／ 源 ／ 结论 ／ 去处）之气皆由**后端之字段**成 ——
     读数 ／ 结论 ／ 去处 ⛔ 本面自算（承「读一处 · 动分端」之族）。
   ⚠ 用户面之字 ⛔ 含过程引用（抽屉之清洗器就地剥之 ⇒ 会留「（）」残 ⇒ 二处之字随刻而二）。 */
const PA_SYS_READ = '/v9/pa/sys/snapshot';
const PA_SYS_ORDER = ['disk', 'disk_c', 'windows', 'startup', 'perf', 'net', 'guard'];
const PA_SYS_V = {ok: '好', info: '知', warn: '须看', crit: '急', unknown: '未取'};
const PA_SYS_VC = {ok: 'ok', info: 'ok', warn: 'warn', crit: 'warn', unknown: 'unk'};
const PA_SYS_ST = {ok: '完整（七面皆取到）', partial: '部分取不得', unavailable: '皆取不得'};
const PA_SYS_OUTLET = '本器唯报（一阶段只读）：须动手者为二阶段之事 —— 本面 ⛔ 代你动。';

let paSysRun = {doc: null, err: '', busy: false, open: false};

function paSysEsc(s){
  return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/* 结论之气 ⇒ 色（一处定形 · ⛔ 各面自造）。 */
/* ⭐⭐ pm_1853 §二.2ⓜ（承 pm_1847 §一）：三态「去处」—— `guide`（唯指路之辞）／
   `act`（本器可真跑）／ `none`（本器唯报）。可跑之二源（⃔ 各面自拼）：
     一类「开系统页」（后端 `os.startfile`）／ 二类「清我司自己之物（白名单桶）」。
   ⚠ 二表皆**对拍后端**（`core/pa/sys_act.py` 之 `SETTINGS_TARGETS` ／ `CLEAN_BUCKETS`）—— ⃔ 传字面。
   ⚠ 守：缺省 ⛔ 危险（先取预案）∨ 逐次 token（TTL 120 s）∨ 红钮**二次确认**∨
     回执示**撤之径** ∨ 陪伴轴（`paChatMode()==='companion'`）⇒ ⛔ 触发（端亦拒）。 */
const PA_SYS_ACT_URL = '/v9/pa/sys/act';
var PA_SYS_ACT_PAGE = {                 /* 系统页之字面 ⇒ 端之白名单键 */
  'ms-settings:storagesense': 'storagesense',
  'ms-settings:windowsupdate': 'windowsupdate',
  'ms-settings:startupapps': 'startupapps',
  'windowsdefender://': 'defender'
};
var PA_SYS_ACT_BUCKET = {               /* 桶之**人话**（用户所见）⇒ 端之桶名 */
  '旧备份（回滚之靠山）': '装位/update/backup',
  '暂存（旧包）': '装位/update/stage',
  '诊断包': '装位/diag',
  '壳之日志': '装位/shell'
};
var paSysActReg = [];                   /* 本次渲之可跑项（下标 ⇒ {act,target,人话,label}） */
var paSysActRun = {};                   /* 键 ⇒ {busy,plan,token,ttl,err,receipt,confirm} */

function paSysActOf(it){
  var a = (it && it['去处']) || {};
  if(String(a['kind'] || '') !== 'guide') return null;
  var t = String(a['target'] || '');
  if(t && PA_SYS_ACT_PAGE[t]) return {act: 'open_settings', target: PA_SYS_ACT_PAGE[t]};
  var b = PA_SYS_ACT_BUCKET[String((it && it['人话']) || '')];
  if(b) return {act: 'clean', target: b};
  return null;
}
function paSysActRegNew(it, a){
  paSysActReg.push({act: a.act, target: a.target, 人话: String((it && it['人话']) || ''),
                    label: String(((it && it['去处']) || {})['label'] || '')});
  return paSysActReg.length - 1;
}
function paSysActAxis(){
  try{ return (typeof paChatMode === 'function' && paChatMode() === 'companion') ? 'chat' : 'sys'; }
  catch(e){ return 'sys'; }
}
async function paSysActPost(body){
  try{
    const base = ((typeof API !== 'undefined') ? API : '');
    body.axis = paSysActAxis();
    const r = await fetch(base + PA_SYS_ACT_URL, {method: 'POST', cache: 'no-store',
      headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
    let j = null; try{ j = await r.json(); }catch(e){ j = null; }
    if(!j) return {ok: false, error: '端未答（HTTP ' + r.status + '）'};
    return j;
  }catch(e){ return {ok: false, error: '取不得（' + ((e && e.message) || '连不上本机之端') + '）'}; }
}
function paSysActPaint(k){
  const el = document.getElementById('paSysActBox_' + k);
  if(el) el.innerHTML = paSysActBoxHtml(k);
}
function paSysActBoxHtml(k){
  const st = paSysActRun[k];
  if(!st) return '';
  const E = paSysEsc;
  let h = '';
  if(st.err) h += '<div style="font-size:11px;color:var(--amber)">' + E(st.err) + '</div>';
  if(st.receipt){
    const r = st.receipt, rc = r['回执'] || {};
    h += '<div style="font-size:11.5px;color:var(--text)">回执：' + E(String(rc['果'] || '—'))
      + ' · 件 ' + E(String(rc['件号'] == null ? '—' : rc['件号']))
      + (r['幂等'] ? '（幂等回 · 同一次授权，⛔ 二动）' : '') + '</div>';
    if(r['字节'] != null) h += '<div style="font-size:10.5px;color:var(--sub)">动了 ' + E(String(r['字节'])) + ' 字节</div>';
    const kept = r['留之件'] || [];
    if(kept.length) h += '<div style="font-size:10.5px;color:var(--sub)">留了最近一份：' + E(kept.join(' ／ ')) + '</div>';
    if(r['撤之径']) h += '<div style="font-size:10.5px;color:var(--blue)">要撤回 ⇒ ' + E(String(r['撤之径'])) + '</div>';
    const bad = r['败之件'] || [];
    if(bad.length) h += '<div style="font-size:10.5px;color:var(--amber)">未成之件：'
      + E(bad.map(function(x){ return String(x['径'] || '') + '（' + String(x['因'] || '') + '）'; }).join(' ／ ')) + '</div>';
    h += '<div style="margin-top:3px"><span class="chip" onclick="paSysActClose(' + k + ')">知道了</span></div>';
    return h;
  }
  if(st.busy) return h + '<div style="font-size:11px;color:var(--sub)">正在向后端要预案…</div>';
  if(!st.plan) return h;
  const p = st.plan;
  h += '<div style="font-size:11.5px;color:var(--text)">预案：' + E(String(p['人话'] || '')) + '</div>';
  h += '<div style="font-size:11px;color:var(--text)">要做：' + E(String(p['件数']))
    + ' 件 · 合计 ' + E(String(p['合计人话'] || '—'))
    + ' · 险级 ' + E(String(p['险级'] || '—'))
    + (p['须管理员'] ? ' · 须管理员' : '') + '</div>';
  if(p['须留最近一份']) h += '<div style="font-size:10.5px;color:var(--sub)">须留最近一份（回滚之靠山）</div>';
  const rows = p['逐条'] || [];
  if(rows.length){
    const show = rows.slice(0, 8).map(function(x){ return '· ' + String(x['径'] || '') + '（' + String(x['字节'] == null ? 0 : x['字节']) + ' 字节）'; }).join('\n');
    h += '<div style="font-size:10.5px;color:var(--sub);white-space:pre-wrap;word-break:break-word">逐件（前 ' + Math.min(rows.length, 8)
      + ' ／ 共 ' + rows.length + '）：\n' + E(show) + '</div>';
  }
  if(p['去哪看']) h += '<div style="font-size:10.5px;color:var(--sub)">去哪看：' + E(String(p['去哪看'])) + '</div>';
  if(st.ttl) h += '<div style="font-size:10.5px;color:var(--sub)">本授权之窗 ' + E(String(st.ttl)) + ' s（过了要重取预案）</div>';
  if(p['须管理员']){
    h += '<div style="font-size:11px;color:var(--amber)">须管理员 ⇒ 本器 ⛔ 自提权 —— 请你自己去点（上「去哪看」）。</div>';
  }else if(st.confirm){
    h += '<div style="margin-top:4px"><span class="chip" style="color:#fca5a5" onclick="paSysActGo(' + k + ')">⚠ 再点一次 ⇒ 真动（'
      + E(String(p['件数'])) + ' 件）</span> <span class="chip" onclick="paSysActCancel(' + k + ')">算了</span></div>';
  }else{
    h += '<div style="margin-top:4px"><span class="chip" style="color:#fca5a5" onclick="paSysActArm(' + k + ')">真动（须点两下才动）</span>'
      + ' <span class="chip" onclick="paSysActClose(' + k + ')">收起</span></div>';
  }
  return h;
}
function paSysActClose(k){ delete paSysActRun[k]; paSysActPaint(k); }
function paSysActCancel(k){ if(paSysActRun[k]) paSysActRun[k].confirm = false; paSysActPaint(k); }
function paSysActArm(k){ if(paSysActRun[k]) paSysActRun[k].confirm = true; paSysActPaint(k); }
async function paSysActPlan(k){
  const it = paSysActReg[k]; if(!it) return;
  const st = paSysActRun[k] = paSysActRun[k] || {};
  if(st.plan && !st.receipt){ st.confirm = true; paSysActPaint(k); return; }
  st.busy = true; st.err = ''; st.receipt = null; paSysActPaint(k);
  const j = await paSysActPost({act: it.act, target: it.target, dry_run: true});
  st.busy = false;
  if(j && j.ok && j['预案']){ st.plan = j['预案']; st.token = j['token']; st.ttl = j['ttl_s']; }
  else st.err = (j && (j.error || j['因'])) ? String(j.error || j['因']) : '后端未答可读之果';
  paSysActPaint(k);
}
async function paSysActGo(k){
  const it = paSysActReg[k], st = paSysActRun[k];
  if(!it || !st || !st.token) return;
  st.busy = true; st.err = ''; st.confirm = false; paSysActPaint(k);
  const j = await paSysActPost({act: it.act, target: it.target, dry_run: false, token: st.token});
  st.busy = false;
  if(j && j.ok) st.receipt = j;
  else st.err = (j && (j.error || j['因'])) ? String(j.error || j['因']) : '后端未答可读之果';
  paSysActPaint(k);
}
try{ window.paSysActPlan = paSysActPlan; window.paSysActArm = paSysActArm; window.paSysActGo = paSysActGo;
     window.paSysActCancel = paSysActCancel; window.paSysActClose = paSysActClose; }catch(e){}

function paSysV(v){
  const k = String(v == null ? '' : v);
  return {t: PA_SYS_V[k] || k || '未取', c: PA_SYS_VC[k] || 'unk'};
}
function paSysVColor(c){
  if(c === 'warn') return 'var(--amber)';
  if(c === 'unk') return 'var(--sub)';
  return 'var(--green)';
}

function paSysItemsHtml(panel){
  const its = (panel && panel.items) || [];
  if(!its.length) return '<div style="font-size:11px;color:var(--sub)">本面 ⛔ 得任何读数。</div>';
  const out = [];
  for(let i = 0; i < its.length; i++){
    const it = its[i] || {};
    const act = it['去处'] || {};
    const v = paSysV(it['结论']);
    let h = '<div style="border-top:1px dashed rgba(48,54,61,.55);padding:5px 0">'
      + '<div style="font-size:11.5px;color:var(--text)"><b>' + paSysEsc(it['人话'] || '（无名）') + '</b>'
      + ' <span style="font-size:10.5px;color:' + paSysVColor(v.c) + '">[' + paSysEsc(v.t) + ']</span>'
      + (it['needs_admin'] ? ' <span style="font-size:10.5px;color:var(--amber)">[须授权]</span>' : '')
      + '</div>'
      + '<div style="font-size:11.5px;color:var(--text);white-space:pre-wrap;word-break:break-word;user-select:text">'
      + paSysEsc(it['读数'] || '—') + '</div>'
      + '<div style="font-size:10.5px;color:var(--sub)">源：' + paSysEsc(it['源'] || '—') + '</div>';
    if(it['清之险']) h += '<div style="font-size:10.5px;color:var(--sub)">清之险：' + paSysEsc(it['清之险']) + '</div>';
    if(it['可否清']) h += '<div style="font-size:10.5px;color:var(--sub)">可否清：' + paSysEsc(it['可否清']) + '</div>';
    const _a = paSysActOf(it);
    if(_a){
      /* pm_1853 §二.2ⓜ：可真跑 ⇒ **一颗可点之「去处」**（先看预案）；后端之辞 ⇒ `title`（⛔ 丢信息）。 */
      const _k = paSysActRegNew(it, _a);
      h += '<div style="font-size:10.5px;color:var(--blue)">去处：'
        + '<span class="chip" id="paSysActChip_' + _k + '" onclick="paSysActPlan(' + _k + ')" title="'
        + paSysEsc(act['label'] || '') + '">'
        + ((_a.act === 'open_settings') ? '打开（本器代你开这一页）' : '清一清（先看预案）')
        + '</span></div>'
        + '<div id="paSysActBox_' + _k + '" style="margin-top:3px"></div>';
    }else if(act['kind'] === 'guide' && act['label']){
      h += '<div style="font-size:10.5px;color:var(--blue)">去处：' + paSysEsc(act['label']) + '</div>';
    }else if(act['kind'] === 'none'){
      h += '<div style="font-size:10.5px;color:var(--sub)">去处：本器唯报（一阶段只读 —— ⛔ 代你动）</div>';
    }
    h += '</div>';
    out.push(h);
  }
  return out.join('');
}

function paSysPanelHtml(p){
  const v = paSysV(p && p.verdict);
  const st = String((p && p.state) || '');
  return '<div style="border:1px solid var(--border);border-radius:9px;padding:7px 9px;margin-bottom:7px;background:var(--card2)">'
    + '<div style="display:flex;gap:7px;align-items:baseline;flex-wrap:wrap">'
    + '<b style="font-size:12px;color:var(--text)">' + paSysEsc((p && (p.title || p.panel)) || '') + '</b>'
    + '<span style="font-size:10.5px;color:' + paSysVColor(v.c) + '">[' + paSysEsc(v.t) + ']</span>'
    + '<span style="font-size:10.5px;color:var(--sub)">态：' + paSysEsc(PA_SYS_ST[st] || st || '—') + '</span>'
    + '<span style="font-size:10.5px;color:var(--sub)">'
    + ((p && p.cached) ? ('缓存 ' + paSysEsc(String(p.age_s)) + ' s 前') : '本次真扫') + '</span>'
    + '</div>'
    + '<div style="font-size:11px;color:var(--text);white-space:pre-wrap;word-break:break-word">结论：'
    + paSysEsc((p && p.verdict_text) || '—') + '</div>'
    + paSysItemsHtml(p)
    + ((p && p.note) ? ('<div style="font-size:10.5px;color:var(--sub)">注：' + paSysEsc(p.note) + '</div>') : '')
    + '</div>';
}

/* ⭐⭐ pm_1853 §一.2 ／ pm_1855 §三.2：首屏收起之读数之**去处** ——
   状态行之原字（`#runStateSrc` ／ `#paUiStateRow`，由 `status.js` 写）∨ 本机身份之原值
   （`web_…` · `paUserRaw()`）。⛔ 丢真源（原字仍在 DOM ／ 本面可得）∨ ⛔ 二处各存。 */
function paSysFoldReadingsHtml(){
  function txt(id){ try{ const e = document.getElementById(id); return e ? String(e.textContent || '') : ''; }catch(e){ return ''; } }
  const rs = txt('runStateSrc'), ui = txt('paUiStateRow');
  let uid = ''; try{ if(typeof paUserRaw === 'function') uid = paUserRaw(); }catch(e){}
  if(!rs && !ui && !uid) return '';
  let rows = '';
  if(uid) rows += '<div style="font-size:11px;color:var(--text)">本机身份：' + paSysEsc(uid)
    + '<span style="font-size:10.5px;color:var(--sub)">（本机唯一之会话归属键 · ⛔ 静默回落默认 ／ 他人 —— 见「关于 PA → 判定规则」）</span></div>';
  if(rs) rows += '<div style="font-size:10.5px;color:var(--sub)">' + paSysEsc(rs) + '</div>';
  if(ui) rows += '<div style="font-size:10.5px;color:var(--sub)">' + paSysEsc(ui) + '</div>';
  return '<div style="border:1px solid var(--border);border-radius:9px;padding:7px 9px;margin-bottom:7px;background:var(--card2)">'
    + '<div style="font-size:11.5px;color:var(--text)">本页顶栏之原读数'
    + '<span style="font-size:10.5px;color:var(--sub)">（首屏已收起 ⇒ 原字收此 · ⛔ 丢）</span></div>'
    + rows + '</div>';
}

function paSysRender(){
  const box = document.getElementById('paSys');
  if(!box) return;
  const r = paSysRun;
  let h = '';
  h += paSysFoldReadingsHtml();
  paSysActReg = [];                     /* 本次渲之可跑项 ⇒ 下标重算（⛔ 跨次漂） */
  if(r.err){
    h += '<div style="font-size:11.5px;color:var(--amber);white-space:pre-wrap;word-break:break-word">取不得之报：'
      + paSysEsc(r.err) + '<br>' + paSysEsc(PA_SYS_OUTLET) + '</div>';
  }
  if(!r.doc){
    h += '<div style="font-size:11px;color:var(--sub)">'
      + (r.busy ? '正在本机体检（唯读 · 有界 6 s）…'
                : '点「🩺 本机体检」取一次（唯本机 · ⛔ 出机 ／ ⛔ 写 ／ ⛔ 提权）。')
      + '</div>';
    box.innerHTML = h;
    return;
  }
  const d = r.doc;
  const ps = d.panels || [];
  const v = paSysV(d.verdict);
  const by = {};
  for(let i = 0; i < ps.length; i++) by[String((ps[i] || {}).panel || '')] = ps[i];
  const order = PA_SYS_ORDER.slice();
  for(let i = 0; i < ps.length; i++){
    const k = String((ps[i] || {}).panel || '');
    if(order.indexOf(k) < 0) order.push(k);
  }
  h += '<div style="display:flex;gap:7px;align-items:baseline;flex-wrap:wrap">'
    + '<b style="font-size:12.5px;color:var(--text)">本机体检（只读 · 七面）</b>'
    + '<span style="font-size:10.5px;color:' + paSysVColor(v.c) + '">[' + paSysEsc(v.t) + ']</span>'
    + '<span style="font-size:10.5px;color:var(--sub)">态：' + paSysEsc(PA_SYS_ST[d.state] || d.state || '—') + '</span>'
    + '</div>'
    + '<div style="font-size:11.5px;color:var(--text);white-space:pre-wrap;word-break:break-word">结论：'
    + paSysEsc(d.verdict_text || '—') + '</div>'
    + '<div style="font-size:10.5px;color:var(--sub)">取于 ' + paSysEsc(d.generated_at || '—')
    + '（耗 ' + paSysEsc(String(d.elapsed_s)) + ' s' + (d.cached ? ' · 皆缓存' : ' · 本次真扫')
    + '）｜源：' + paSysEsc(d.source_note || '—') + '</div>'
    + '<div style="font-size:10.5px;color:var(--sub)">本器一阶段全程 ⛔ 出机 ／ ⛔ 写 ／ ⛔ 提权（本面纯读）；清删类之真动仅经「去处」之红钮（逐次授权 · 二次确认 · 可撤）—— 须授权之项已标「须授权」（本器 ⛔ 自提权）。</div>'
    + '<div style="margin-top:6px">';
  for(let i = 0; i < order.length; i++) h += paSysPanelHtml(by[order[i]]);
  h += '</div>'
    + '<div style="border:1px solid var(--border);border-radius:9px;padding:7px 9px;background:var(--card2)">'
    + '<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">'
    + '<b style="font-size:12px;color:var(--text)">本机体检（文本）</b>'
    + '<span style="font-size:10.5px;color:var(--sub)">这一段就是上面七面读数之纯文本 —— 可全选后复制（唯前端 · ⛔ 写盘）。</span>'
    + '<span class="chip" onclick="paSysCopy()" title="全选这段文本并试着复制到剪贴板（唯前端 · ⛔ 写盘）">全选复制</span>'
    + '<span id="paSysFlash" style="font-size:10.5px;color:var(--green)"></span>'
    + '</div>'
    + '<textarea id="paSysText" readonly rows="14" spellcheck="false" '
    + 'style="width:100%;margin-top:5px;background:var(--bg);border:1px solid var(--border);color:var(--text);'
    + 'border-radius:7px;font-size:11px;line-height:1.55;padding:6px 8px;'
    + 'font-family:ui-monospace,Consolas,monospace;resize:vertical;user-select:text" '
    + 'title="可全选（Ctrl+A）后复制"></textarea>'
    + '</div>';
  box.innerHTML = h;
  const ta = document.getElementById('paSysText');
  if(ta) ta.value = String(d.text || '');
}

function paSysWhen(){
  const el = document.getElementById('paSysWhen');
  if(!el) return;
  const d = paSysRun.doc;
  el.textContent = d ? ('取于 ' + (d.generated_at || '—') + (d.cached ? '（缓存）' : '（真扫）'))
                     : (paSysRun.err ? '取不得' : (paSysRun.busy ? '读取中…' : '未取'));
}

async function paSysFetch(fresh){
  if(paSysRun.busy) return;
  paSysRun.busy = true;
  paSysRun.err = '';
  paSysRender();
  paSysWhen();
  const base = ((typeof API !== 'undefined') ? API : '');
  let msg = '';
  try{
    const r = await fetch(base + PA_SYS_READ + (fresh ? '?fresh=1' : ''), {cache: 'no-store'});
    let j = null;
    try{ j = await r.json(); }catch(e){ j = null; }
    if(j && j.ok === true && j.panels){
      paSysRun.doc = j;
    }else if(r.status === 403){
      msg = '唯本机可用（本页 ⛔ 由本机打开 ⇒ 端拒之）'
        + ((j && j.error) ? ('：' + j.error) : '') + '。';
    }else{
      msg = '端未答可读之果（HTTP ' + r.status + '）'
        + ((j && j.error) ? ('：' + j.error) : '') + ' —— ⛔ 不等于「七面皆好」。';
    }
  }catch(e){
    msg = '取不得（' + ((e && e.message) ? e.message : '连不上本机之端') + '）—— ⛔ 不等于「七面皆好」。';
  }
  paSysRun.busy = false;
  if(msg) paSysRun.err = msg;
  paSysRender();
  paSysWhen();
}

function paSysOpen(){
  const box = document.getElementById('paSys');
  const chip = document.getElementById('paSysOpen');
  paSysRun.open = !paSysRun.open;
  if(box) box.style.display = paSysRun.open ? '' : 'none';
  if(chip) chip.textContent = paSysRun.open ? '🩺 收起体检' : '🩺 本机体检';
  if(!paSysRun.open) return;
  if(!paSysRun.doc && !paSysRun.busy) paSysFetch(false);
  else paSysRender();
}

function paSysScan(){
  paSysRun.open = true;
  const box = document.getElementById('paSys');
  if(box) box.style.display = '';
  const chip = document.getElementById('paSysOpen');
  if(chip) chip.textContent = '🩺 收起体检';
  paSysFetch(true);
}

function paSysFlash(t){
  const el = document.getElementById('paSysFlash');
  if(el) el.textContent = String(t || '');
}

function paSysCopy(){
  const ta = document.getElementById('paSysText');
  if(!ta){ paSysFlash('先取一次（点「🩺 本机体检」）'); return; }
  try{ ta.focus(); ta.select(); }catch(e){}
  let done = false;
  try{
    if(navigator.clipboard && navigator.clipboard.writeText){
      navigator.clipboard.writeText(String(ta.value || ''))
        .then(function(){ paSysFlash('已复制 —— 可到聊天框 ／ 留言板粘给我们'); },
              function(){ paSysFlash('已全选 —— 请按 Ctrl+C 复制'); });
      done = true;
    }
  }catch(e){}
  if(!done) paSysFlash('已全选 —— 请按 Ctrl+C 复制');
}

/* ⭐ pm_1801 §一（主件 · 一步可达）：顶栏之「🩺 本机体检」入口 ⇒ **一处定形**于此。
   由：老板「一头撞上（不知道它在）」⇒ 旧入口唯在「更多 ▾ → ③ 设」之内 ＝ 二级菜单。
   本函数唯做三件（皆**已存之能** · ⛔ 新造）：开「更多」⇒ 开 ③ 组 ⇒ 展开体检面 ＋ 滚入视口。
   ⛔ 取数（取数唯由 `paSysFetch` ⇒ 展开即取 · 幂等）；⛔ 写；⛔ 出机。再点 ⇒ 收起（幂等）。 */
function paSysTopOpen(){
  const box = document.getElementById('paSys');
  const shown = !!(box && box.style.display !== 'none');
  if(paSysRun.open && shown){ paSysOpen(); return; }   /* 已开 ⇒ 再点收起 */
  try{ if(typeof paMore === 'function') paMore(true); }catch(e){}
  try{ const g = document.getElementById('paMoreGrpSet'); if(g) g.setAttribute('open',''); }catch(e){}
  if(!paSysRun.open) paSysOpen();
  try{
    const s = document.getElementById('paMoreSysFace');
    if(s && s.scrollIntoView) s.scrollIntoView({block:'start'});
  }catch(e){}
}

try{
  window.paSysOpen = paSysOpen; window.paSysScan = paSysScan; window.paSysCopy = paSysCopy;
  window.paSysTopOpen = paSysTopOpen;
  window.paSysFetch = paSysFetch; window.paSysRender = paSysRender; window.PA_SYS_ORDER = PA_SYS_ORDER;
}catch(e){}
