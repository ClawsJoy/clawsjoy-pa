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
    if(act['kind'] === 'guide' && act['label']){
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

function paSysRender(){
  const box = document.getElementById('paSys');
  if(!box) return;
  const r = paSysRun;
  let h = '';
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
    + '<div style="font-size:10.5px;color:var(--sub)">本器全程 ⛔ 出机 ／ ⛔ 写 ／ ⛔ 提权（须授权之项已标「须授权」—— 本器 ⛔ 自提权）。</div>'
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

try{
  window.paSysOpen = paSysOpen; window.paSysScan = paSysScan; window.paSysCopy = paSysCopy;
  window.paSysFetch = paSysFetch; window.paSysRender = paSysRender; window.PA_SYS_ORDER = PA_SYS_ORDER;
}catch(e){}
