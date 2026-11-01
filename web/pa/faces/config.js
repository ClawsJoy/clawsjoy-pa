/* ---- 运行配置 ---- */
function loadCfg(){ const c=JSON.parse(localStorage.getItem('pa_cfg')||'{}'); const set=(id,v)=>{const el=$(id); if(el&&v) el.value=v;}; set('cfgChan',c.chan); set('cfgAppr',c.appr);   /* PA-B1：⛔ 不再从 pa_cfg 回填权限档（真源＝后端，由 fetchPaGrant 落到同一 select） */ const cv=$('cfgVault'); if(cv&&typeof c.vault==='boolean') cv.checked=c.vault; paModelFill(c.model);   /* ⭐ pm_1465 §一：模型选单自后端之表出（⛔ 硬编选项）—— c.model 为**回填之请**（⛔ 在表 ⇒ 显形）；⛔ 再于此 `set('cfgModel')`：其项尚未立 ⇒ 赋之无据 */ fetchPaGrant(); fetchPaBuild();   /* PM-011：授予来源面 ＋ 构建指纹（PM 2026-09-30 批） */ }
/* ⭐ 模型选单 · **自后端之表出**（pm_1465 §一 · 老板已准 · 承 pm_1456 §三.3 之呈议）。
   源 ＝ `GET /v9/pa/providers` 之 `models_table[]`（core/pa/providers.py · **一处定形** · TD 1464）
   —— ⛔ 自拟其形 ∨ ⛔ 自造端点 ∨ ⛔ 硬编选项。
   ① 一项一物：<option value ＝ **实名（行 id）**>；字面 ＝ 「本机 ／ 云端 · label（可用：态）」。
   ② 「本机 ／ 云端」之别**须入目**（**置首** ⇒ 窄格亦见）：出机标唯云端之轮上 ⇒ 人须先知所择将出机（承红线之精神）。
   ③ `可用` 逐字照渲（后端六态 · ⛔ 前端自造辞）⇒ **净机无本机模型服务即于此显形**（⛔ 装成可选）。
   ④ 表 ⛔ 得（未应答 ／ 坏体 ／ 键 ⛔ 在）⇒ **显形**（PA_GAP 三态 · ⛔ 静默硬编回退 ⇒ 以旧别名充选）。
   ⑤ 所选之实名 ⇒ `paModelSel()` **一处出**（send.js ／ cards.js 皆取之 ⇒ **说一用一**）；
     ⛔ 在表内 ⇒ 返 "" ⇒ 请求体 ⛔ 带该键（后端落会话档 ∨ 默认 · 承「其名由后端出」）。
   ⑥ 回填之请**先归一、后比**（pm_1472 §二）：以**后端之表之归一**（行 `aliases[]` ／ 顶层 `model_aliases`）
     ⇒ 别名（如 `deepseek-v4-flash`）**归一为实名** ⇒ 命中即选中 —— ⛔ 静默落默认；⛔ 猜测（前缀剥 ／ 模糊比）。
   ⑦ ⛔ 命中（真未知名）⇒ **显形**（明书「表 ⛔ 含此名 ＋ 所按之默认」· 紧贴选单 ⇒ ⛔ 与「表未得」之态一名蔽二态）;
     **存者唯实名**（别名 ⛔ 存底 —— 归正后回写 `pa_cfg.model`）。
   ⑧ ⭐ **屏唯人话 · 端径入 `title`**（pm_1928 §一.1⒜ ／ §一.2）：四态之辞 ⛔ 载端径（`GET /v9/…`） ／ 端字段名（`models_table`）—— 二者入 `sel.title`（＝**工程之据之地** · 悬停可查）；得表后须清（⛔ 留旧态之据）。⇒ 用户面读作「模型表未应答（因）· 扫于刻」∧ 工程之据 ⛔ 丢（承「可查」之律）。 */
var paModelRows = null;   /* 后端之表（本轮之实）· null ＝ 未得 ⇒ paModelSel() 恒 "" */
var paModelKept = '';     /* 末次**得表**之所选（⛔ 被显形之空值抹去 ⇒ 存底 ⛔ 静默丢） */
function paModelKindTxt(k){ return (k === 'local') ? '本机' : ((k === 'remote') ? '云端' : '种类未给'); }
function paModelOptHtml(m){
  const o = m || {}, id = String(o.id || '');
  let t = paModelKindTxt(o.kind) + ' · ' + String(o.label || id || '—');
  if(o.isDefault) t += ' ★默认';
  if(o.loaded) t += ' · 已载';
  if(o['可用']) t += '（可用：' + String(o['可用']) + '）';
  return '<option value="' + paEsc(id) + '">' + paEsc(t) + '</option>';
}
function paModelState(sel, txt, tip){
  sel.innerHTML = '<option value="">' + paEsc(txt) + '</option>';
  sel.disabled = true;   /* 显形之态 ⛔ 可择（⛔ 以旧别名充选） */
  sel.title = String(tip || '');   /* ⭐ 工程之据之地（端径 ／ 键名 ／ 码）：**屏唯人话** · 此处可查（pm_1928 §一.1⒜ ／ §一.2 —— 承「可查 ⛔ 丢」） */
  paModelNote(sel, '');  /* 表未得之态 ⇒ 归正／未知名之注 ⛔ 留（二态须别） */
  return sel;
}
/* 归一表（**自后端之响应出** · ⛔ 前端硬编别名）：别名 ⇒ **实名**。
   ① 行级 `aliases[]`（行之所绑 ⇒ **优先**）② 顶层 `model_aliases`（唯当其所指**为表内实名** ⇒ 补之）。
   ⛔ 猜测（⛔ 前缀剥 ／ ⛔ 模糊比）：唯认后端所给之键值（承 pm_1472 §二.2）。 */
function paModelAliasMap(rows, d){
  const ids = {}, m = {};
  rows.forEach(function(r){ const id = String((r || {}).id || ''); if(id) ids[id] = true; });
  const top = (d && typeof d.model_aliases === 'object' && d.model_aliases) || {};
  Object.keys(top).forEach(function(k){ const v = String(top[k] || ''); if(ids[v]) m[k] = v; });
  rows.forEach(function(r){
    const id = String((r || {}).id || ''), al = (r && Array.isArray(r.aliases)) ? r.aliases : [];
    al.forEach(function(x){ const k = String(x || ''); if(k && ids[id]) m[k] = id; });
  });
  return m;
}
/* 回填之请 ⇒ 实名：① 逐字命中表内实名 ② 别名归一 ③ ⛔ 命中 ⇒ ""（未知名 · 显形用）。 */
function paModelResolve(rows, amap, want){
  const w = String(want || '');
  if(!w) return {id: '', via: ''};
  for(let i = 0; i < rows.length; i++){ if(String((rows[i] || {}).id) === w) return {id: w, via: 'id'}; }
  if(amap[w]) return {id: amap[w], via: 'alias'};
  return {id: '', via: ''};
}
/* 归正／未知名之**显形**（pm_1472 §二.1 ／ §三.1）：**唯此一处**出注，紧贴模型选单
   —— ⛔ 入 select 之项文（免与「表未得」之态一名蔽二态· 二态共用一个注位）。 */
function paModelNote(sel, txt){
  if(!sel || !sel.parentNode) return;
  let n = document.getElementById('cfgModelNote');
  if(!n){
    n = document.createElement('span'); n.id = 'cfgModelNote';
    n.style.cssText = 'display:block;font-size:10.5px;line-height:1.5;margin-top:2px;color:#d2991d';
    sel.parentNode.appendChild(n);
  }
  n.textContent = String(txt || '');
  n.style.display = txt ? '' : 'none';
}
/* 存底之归正（pm_1472 §三.2）：**别名 ⛔ 存** —— 归正后回写 `pa_cfg.model`（唯既有之 model 键 · ⛔ 造新键 · ⛔ 静默改他键）。 */
function paModelPersist(id){
  try{
    const raw = localStorage.getItem('pa_cfg'); if(!raw) return;
    const c = JSON.parse(raw) || {};
    if(typeof c.model !== 'string' || !c.model || c.model === id) return;
    c.model = String(id || ''); localStorage.setItem('pa_cfg', JSON.stringify(c));
  }catch(e){}
}
function paModelRender(sel, st, d, at, err, prev){
  const rows = (d && Array.isArray(d.models_table)) ? d.models_table : null;
  if(err){ paModelRows = null; return paModelState(sel, PA_GAP.down('模型表未应答（' + err + '）· 扫于 ' + at), 'GET /v9/pa/providers 未应答：' + err); }
  if(st !== 200 || !d){ paModelRows = null; return paModelState(sel, PA_GAP.down('模型表未回成（服务之回 ' + st + '）· 扫于 ' + at), 'GET /v9/pa/providers 未回 200（HTTP ' + st + '）'); }
  if(!rows){ paModelRows = null; return paModelState(sel, PA_GAP.fallback('模型表') + ' · 扫于 ' + at, 'GET /v9/pa/providers 之回 ⛔ 载此键 models_table'); }
  if(!rows.length){ paModelRows = null; return paModelState(sel, '模型表照实 0 行（扫于 ' + at + '）', 'GET /v9/pa/providers 之 models_table 照实 0 行'); }
  paModelRows = rows; sel.disabled = false; sel.title = '';   /* 得表 ⇒ 前一态之工程之据须清（⛔ 留旧态之 title） */
  sel.innerHTML = rows.map(paModelOptHtml).join('');
  /* 择值之序：**回填之请**（先归一 · 在表）⇒ 后端之 `default.model` ⇒ 首行（⛔ 前端自拟默认）。 */
  const want = String(prev || '').trim(), dft = String(((d || {}).default || {}).model || '');
  const amap = paModelAliasMap(rows, d), hit = paModelResolve(rows, amap, want);
  /* ⭐ 默认通道与模型须同源：旧存底可能是本机 qwen，而今默认通道已 remote:deepseek
     ⇒ 存底之模型若属**另一 provider** ⇒ 不采用（否则 qwen 名被发给 DeepSeek API ⇒ 400）。 */
  const dftProv = String(((d || {}).default || {}).provider || '');
  let crossProv = false, crossProvId = '';
  if(hit.id && dftProv){
    const hrow = rows.filter(function(m){ return String((m || {}).id) === hit.id; })[0] || {};
    if(hrow.provider_id && String(hrow.provider_id) !== dftProv){
      crossProv = true; crossProvId = String(hrow.provider_id || '');
    }
  }
  let hasD = false;
  rows.forEach(function(m){ if(String((m || {}).id) === dft) hasD = true; });
  const pick = hit.id || (hasD ? dft : String((rows[0] || {}).id || ''));
  sel.value = pick;
  paModelKept = String(sel.value || '');   /* **名实同一**：kept 亦为实名（⛔ 落旧别名） */
  if(hit.via === 'alias'){
    paModelNote(sel, '原选「' + want + '」（别名）⇒ 已归正为「' + pick + '」');
    paModelPersist(pick);
  } else if(hit.via === 'id'){
    paModelNote(sel, crossProv ? ('已选非默认通道 ' + crossProvId + ' ⇒ 本会话走「' + pick + '」；默认仍是 ' + dftProv) : '');
    if(crossProv) paModelPersist(pick);
  } else if(String(want || '').trim()) {
    paModelNote(sel, '后端之表 ⛔ 含此名「' + want + '」⇒ 已按下之默认「' + pick + '」（⛔ 静默）');
  } else {
    paModelNote(sel, '');
  }
  return sel;
}
function paModelFill(prev){
  const sel = document.getElementById('cfgModel');
  if(!sel) return null;
  const at = new Date().toTimeString().slice(0, 8);
  return fetch(API + '/v9/pa/providers', {cache: 'no-store'})
    .then(function(r){ return r.json().catch(function(){ return null; }).then(function(d){ return {st: r.status, d: d}; }); })
    .then(function(x){ return paModelRender(sel, x.st, x.d, at, '', prev); })
    .catch(function(e){ return paModelRender(sel, 0, null, at, String((e && e.message) || e), prev); });
}
/* ⭐ 所选之**实名**（**一处出**）：唯表内之行 ⇒ 返其 id；⛔ 则 ""（承「白名单守之」· 后端落默认 ∨ 会话档）。 */
function paModelSel(){
  const sel = document.getElementById('cfgModel');
  if(!sel || !paModelRows) return '';
  const v = String(sel.value || '');
  for(let i = 0; i < paModelRows.length; i++){ if(String((paModelRows[i] || {}).id) === v) return v; }
  return '';
}

function saveCfg(){
  /* PA-B1 · 授权面板（2026-10-03 · CW b2a5182）：**改档单源 ＝ 后端**。
     病（本刻一手读原文）：本函数此前 `console.warn` 静默 —— 后端拒收（409 坏状态 / 非法档）时
     界面仍显示新值 ⇒ **假绿**（改了不生效，用户看不到）；且成功也不回读 ⇒ 顶栏与配置可长期不一致。
     承 core/pa/permission.py 抬头（2026-09-11 设计）：「只能经 /v9/pa/permission 写入」。
     ⛔ 现在：`pa_cfg` 不再存 perm（消第二真源）· 失败**可见**并**回读后端真值**（⛔ 界面不留假值）。 */
  const permEl=$('cfgPerm'); const perm=permEl?String(permEl.value||''):'';
  const cfg={chan:$('cfgChan').value,model:(paModelSel()||paModelKept),appr:$('cfgAppr').value,vault:$('cfgVault').checked};   /* ⭐ pm_1465 §一：model 唯**表内之实名** ⇒ 显形之态 ⛔ 存空值（存底 ⛔ 静默丢 · ⛔ 硬编回退） */
  localStorage.setItem('pa_cfg',JSON.stringify(cfg));
  if(!perm) return;
  fetch(API+'/v9/pa/permission',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:curUser(),level:perm})})
    .then(function(r){ return r.json().then(function(d){ return {status:r.status,d:d}; }).catch(function(){ return {status:r.status,d:null}; }); })
    .then(function(x){
      var d=x.d;
      if(x.status!==200 || !d || d.ok===false){
        var msg=(d&&(d.message||d.error))||('HTTP '+x.status);
        addMsg('sys','⚠ 权限档后端拒收（HTTP '+x.status+'）：'+msg+' ⇒ 按后端真值回读（⛔ 界面不留假值）');
      }
      fetchPaGrant();   /* 回读：顶栏徽标 ／ 授权面板 ／ 本下拉 同源同步 */
    })
    .catch(function(e){ addMsg('sys','⚠ 权限档未取得回执：'+((e&&e.message)||e)+' ⇒ 后端是否已改未知（⛔ 不等于「没改」）'); fetchPaGrant(); });
}
