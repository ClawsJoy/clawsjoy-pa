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
     ⛔ 在表内 ⇒ 返 "" ⇒ 请求体 ⛔ 带该键（后端落会话档 ∨ 默认 · 承「其名由后端出」）。 */
var paModelRows = null;   /* 后端之表（本轮之实）· null ＝ 未得 ⇒ paModelSel() 恒 "" */
var paModelKept = '';     /* 末次**得表**之所选（⛔ 被显形之空值抹去 ⇒ 存底 ⛔ 静默丢） */
function paModelKindTxt(k){ return (k === 'local') ? '本机' : ((k === 'remote') ? '云端' : '种类未给'); }
function paModelOptHtml(m){
  const o = m || {}, id = String(o.id || '');
  let t = paModelKindTxt(o.kind) + ' · ' + String(o.label || id || '—');
  if(o.isDefault) t += ' ★默认';
  if(o['可用']) t += '（可用：' + String(o['可用']) + '）';
  return '<option value="' + paEsc(id) + '">' + paEsc(t) + '</option>';
}
function paModelState(sel, txt){
  sel.innerHTML = '<option value="">' + paEsc(txt) + '</option>';
  sel.disabled = true;   /* 显形之态 ⛔ 可择（⛔ 以旧别名充选） */
  return sel;
}
function paModelRender(sel, st, d, at, err, prev){
  const rows = (d && Array.isArray(d.models_table)) ? d.models_table : null;
  if(err){ paModelRows = null; return paModelState(sel, PA_GAP.down('GET /v9/pa/providers 未应答（' + err + '）· 扫于 ' + at)); }
  if(st !== 200 || !d){ paModelRows = null; return paModelState(sel, PA_GAP.down('GET /v9/pa/providers 未回 200（HTTP ' + st + '）· 扫于 ' + at)); }
  if(!rows){ paModelRows = null; return paModelState(sel, PA_GAP.fallback('models_table') + ' · 扫于 ' + at); }
  if(!rows.length){ paModelRows = null; return paModelState(sel, '后端 models_table 照实 0 行（扫于 ' + at + '）'); }
  paModelRows = rows; sel.disabled = false;
  sel.innerHTML = rows.map(paModelOptHtml).join('');
  /* 择值之序：**回填之请**（在表）⇒ 后端之 `default.model` ⇒ 首行（⛔ 前端自拟默认）。 */
  const want = String(prev || ''), dft = String(((d || {}).default || {}).model || '');
  let hasW = false, hasD = false;
  rows.forEach(function(m){ const id = String((m || {}).id || ''); if(id === want) hasW = true; if(id === dft) hasD = true; });
  sel.value = hasW ? want : (hasD ? dft : String((rows[0] || {}).id || ''));
  paModelKept = String(sel.value || '');
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
    .catch(function(e){ addMsg('sys','⚠ 权限档未取得回执：'+((e&&e.message)||e)+' ⇒ 后端是否已改**未知**（⛔ 不等于「没改」）'); fetchPaGrant(); });
}
