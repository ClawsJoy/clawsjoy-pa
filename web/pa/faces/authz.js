/* ---- PA-B1 · 授权面板 接线（2026-10-03 · CW b2a5182）：**在场授权**接上两个 0 命中端点 ----------
   病（设计稿 v9_pa_frontend_refactor_design.md §4.3「新增 授权面板 … 待接」／§4.4 第 11-12 条
       ／§6 阶段 B B1）：
     `/v9/pa/proxy/gate`(L0) · `/v9/pa/proxy/approve`(L2) 后端**在场**，`web/pa.html` **0 命中**
     ⇒ 老板看不到「现在到底授了什么、还剩多久、怎么撤」⇒ **够不着的能力**（与口径面板同病）。
   照设计稿 §4.2 三条纪律（不吞／不造／不复述）：
     ① 不吞：读不到 ⇒ 明说**读数不可得**（⛔ 不报「未授权」冒充读数 —— 两态必须分得开）；
     ② 不造：`expires_in` 是**后端读数**，本面板只显示 ＋ 手动刷新，⛔ 前端不倒计时；
              授权须**点名 path**（⛔ 前端不代填授权对象）；
     ③ 不复述：破坏性端点清单 ⛔ 前端硬编码，只显示后端 `paths` 原文。
   ⛔ 本步只接线：⛔ 不改后端语义、⛔ 不碰生效判定（谁放行仍由 `endpoint_guard.check()` 判）。 */
const PA_PERM_API = { gate:'/v9/pa/proxy/gate', approve:'/v9/pa/proxy/approve', perm:'/v9/pa/permission', grants:'/v9/pa/grants' };
const PA_PERM_LEVELS = ['只读','标准','高(需确认)'];
let paPermLoaded = false;
let paPermGate = null;   /* null = 还没取 ／ {__error} = 读不到 ／ {approved,expires_in,paths} = 后端原文 */
let paPermGrants = null; /* 长期授权（grants）之态：null = 还没取 ／ {__error} ／ {state,count,grants,source} —— state 四态 active ／ none ／ missing ／ corrupt（PM 3413） */
function paPermEl(id){ try{ return document.getElementById(id); }catch(e){ return null; } }
function paPermUnavailable(what, err){
  return '<div class="cb-degraded">⚠ '+esc(what)+'读数不可得：'+esc(String(err))
    +'（⛔ 这不是「没有授权」—— 读不到与没授过必须分得开）</div>';
}
function paPermLevelHtml(){
  const s=function(v){ return (v===undefined||v===null||v==='')?'—':String(v); };
  if(paGrantErr===undefined) return '<span class="cbna">⏳ 授予读数读取中（尚未取到）</span>';
  if(paGrantErr) return '<span class="cbna">⚠ 面不可读（'+esc(String(paGrantErr).slice(0,80))+'）</span>';
  if(!paGrant) return '<span class="cbna">⚠ 后端未给 grant 来源面（前端 ⛔ 不猜档位来源）</span>';
  const srcs=[];
  if(paGrant.pa && paGrant.pa.exists) srcs.push(esc(String(paGrant.pa.path||'')));
  if(paGrant.pes && paGrant.pes.exists) srcs.push(esc(String(paGrant.pes.path||'')));
  if(!srcs.length) return '<span title="凭据档之真源">未授予（默认档「'+esc(s(paGrantLevel))+'」· 不是「读到了只读」）</span>';
  return '<span title="来源 '+esc(srcs.join(' ／ '))+'">✅ '+esc(s(paGrantLevel))+'</span>';
}
function paPermPathsHtml(paths){
  const a=Array.isArray(paths)?paths:[];
  if(!a.length) return '<span class="cbna">（授权目录为空 —— 空 ≠ 读数不可得）</span>';
  return a.map(function(p){ return '<code>'+esc(String(p))+'</code>'; }).join(' · ');
}
function paPermGateHtml(){
  if(paPermGate===null || paPermGate===undefined) return '<div class="cbmeta">⏳ 尚未取（展开时按只读接口拉取，不刷新页面）</div>';
  if(paPermGate.__error) return paPermUnavailable('在场授权', paPermGate.__error);
  const g=paPermGate;
  if(g.approved!==true) return '<div class="cbmeta" title="approved=false">未授权 · 授权范围：'+paPermPathsHtml(g.paths)+'</div>';
  return '<div class="cbmeta"><span class="cb-confirmed"><b>✅ 已授权</b></span> · 剩余 <b>'+esc(String(g.expires_in))
    +'</b> s（本机读数 · 不自行倒计时，要新值请点刷新）· 授权范围：'+paPermPathsHtml(g.paths)+'</div>';
}
function paPermGrantsHtml(){
  /* 长期授权（`grants`）之只读面：⭐ 三态必分（PM 3413 §一.2）——
     `missing`（件不在）／ 空表 ⇒ **「未配置（默认拒绝）」**；`corrupt` ⇒ 坏件（⛔ 当空）。
     ⛔ 本面板 ⛔ 以「没有授权」之说法顶替「未配置」（那会把「未配置」与「零条」混成一态）。 */
  if(paPermGrants===null || paPermGrants===undefined) return '<div class="cbmeta">⏳ 尚未取（展开时按只读接口拉取）</div>';
  if(paPermGrants.__error) return paPermUnavailable('长期授权', paPermGrants.__error);
  const st=String(paPermGrants.state||'');
  if(st==='corrupt') return '<div class="cb-degraded">⚠ 授权档坏件（fail-closed）：⛔ 当「未配置」之外一律不认 —— 详情见后端 error</div>';
  if(st==='missing' || st==='none' || !Number(paPermGrants.count||0)){
    return '<div class="cbmeta" title="来源 '+esc(String(paPermGrants.source||''))+'">未配置（默认拒绝）'
      +'—— 本机无长期授权 ⇒ 每次写入须老板在审批卡确认</div>';
  }
  const rows=(paPermGrants.grants||[]).map(function(g){
    const u=Number(g&&g.uses||0);
    const when=(g&&g.last_used_at)?String(g.last_used_at):'从未使用';
    return '<div class="cbmeta"><code>'+esc(String(g&&g.scene||''))+'</code> · 用 '
      +esc(String(u))+' 次 · 末用 '+esc(when)+'</div>';
  }).join('');
  return '<div class="cbmeta">✅ 已配置 '+esc(String(paPermGrants.count))+' 条（来源 '+esc(String(paPermGrants.source||''))+'）</div>'+rows;
}
function paPermSummaryText(){
  if(paGrantErr) return '权限档 ⚠ 面不可读 · 在场授权 '+(paPermGate&&paPermGate.approved?'有效 '+paPermGate.expires_in+'s':'无');
  const lv=(paGrantLevel===undefined||paGrantLevel===null)?'—':String(paGrantLevel);
  const has=(paGrant && ((paGrant.pa&&paGrant.pa.exists) || (paGrant.pes&&paGrant.pes.exists)));
  const lvtxt=has?lv:('未授予（默认档 '+lv+'）');
  const gtxt=(paPermGate===null||paPermGate===undefined)?'⏳ 未取':(paPermGate.__error?'⚠ 读不到':(paPermGate.approved?('有效 '+paPermGate.expires_in+'s'):'无'));
  return '权限档 '+lvtxt+' · 在场授权 '+gtxt;
}
function paPermPanelHtml(doc, opts){
  const o=opts||{}, loaded=!!(doc&&doc.__loaded);
  let h='<details class="cbpanel"'+(o.open?' open':'')+'><summary>🔐 授权面板 · '
    +esc(loaded?paPermSummaryText():'尚未加载（展开时按只读接口拉取，不刷新页面）')+'</summary>';
  if(!loaded) return h+'</details>';
  h+='<div class="cbmeta" title="真源：本机 data/v9/pa/permission.json">权限档：'+paPermLevelHtml()
    +' <button class="cbrefresh" onclick="paPermLoad(true)">刷新</button></div>';
  h+='<div class="cbform"><div class="cbrow"><select id="ppLevel"><option value="">（未选档）</option>'
    +PA_PERM_LEVELS.map(function(l){ return '<option value="'+esc(l)+'">'+esc(l)+'</option>'; }).join('')
    +'</select><button class="cbsubmit" onclick="paPermSetLevel()">写入并回读校验</button></div>'
    +'<div id="ppLevelMsg" class="cbout"></div></div>';
  h+='<div class="cbform"><b>在场授权（会话级 · 破坏性端点）</b>'+paPermGateHtml()+'</div>';
  h+='<div class="cbform"><b>长期授权（本机档 · 默认拒绝）</b>'+paPermGrantsHtml()+'</div>';
  h+='<div class="cbform"><input id="ppPath" placeholder="path（点名要授权的端点，如 /kv/clear）">'
    +'<div class="cbrow"><input id="ppTtl" placeholder="ttl_s（留空 ⇒ 后端默认 1800）">'
    +'<input id="ppNote" placeholder="note（授权理由，可留空）">'
    +'<button class="cbsubmit" onclick="paPermGrant()">授权</button>'
    +'<button class="cbcheck" onclick="paPermRevoke()">撤销授权</button></div>'
    +'<div id="ppGateMsg" class="cbout"></div></div>';
  return h+'</details>';
}
function renderPermPanel(){
  const host=paPermEl('permPanel'); if(!host) return;
  const open=(host.getAttribute('data-open')==='1');
  host.innerHTML=paPermPanelHtml({__loaded:paPermLoaded},{open:open});
  const det=host.querySelector?host.querySelector('details'):null;
  if(det&&det.addEventListener){ det.addEventListener('toggle', function(){ host.setAttribute('data-open', det.open?'1':'0'); if(det.open) paPermLoad(false); }); }
}
function paPermGateUrl(){ return API+PA_PERM_API.gate+'?user_id='+encodeURIComponent(curUser()); }
async function paPermLoad(force){
  const host=paPermEl('permPanel'); if(!host) return null;
  if(paPermLoaded && !force){ renderPermPanel(); return paPermGate; }
  try{ await fetchPaGrant(); }catch(e){}          /* 权限档与顶栏**同一真源**（⛔ 不另开一路取数） */
  try{
    const r=await fetch(paPermGateUrl(),{cache:'no-store'});
    let d=null; try{ d=await r.json(); }catch(e){ d=null; }
    if(r.status!==200 || !d || d.ok===false) paPermGate={__error:((d&&(d.message||d.error))||('HTTP '+r.status))};
    else paPermGate={approved:d.approved===true, expires_in:d.expires_in, paths:d.paths};
  }catch(e){ paPermGate={__error:''+((e&&e.message)||e)}; }
  try{                                   /* 长期授权：⛔ 与「在场授权」混 —— 二源二义 */
    const rg=await fetch(API+PA_PERM_API.grants,{cache:'no-store'});
    let dg=null; try{ dg=await rg.json(); }catch(e){ dg=null; }
    if(dg && dg.state) paPermGrants={state:dg.state, count:dg.count, grants:(dg.grants||[]), source:dg.source};
    else paPermGrants={__error:((dg&&(dg.message||dg.error))||('HTTP '+rg.status))};
  }catch(e){ paPermGrants={__error:''+((e&&e.message)||e)}; }
  paPermLoaded=true; renderPermPanel(); return paPermGate;
}
function paPermReadForm(){
  const v=function(id){ const el=paPermEl(id); return el?String(el.value==null?'':el.value).trim():''; };
  return {path:v('ppPath'), ttl_s:v('ppTtl'), note:v('ppNote')};
}
async function paPermPost(body){
  const r=await fetch(API+PA_PERM_API.approve,{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify(Object.assign({user_id:curUser()}, body))});
  let d=null; try{ d=await r.json(); }catch(e){ d=null; }
  if(r.status!==200 || !d || d.ok===false) return {ok:false, status:r.status, error:((d&&(d.message||d.error))||('HTTP '+r.status))};
  return {ok:true, status:r.status, data:d};
}
async function paPermGrant(form){
  const f=form||paPermReadForm();
  const out=paPermEl('ppGateMsg');
  const say=function(html){ if(out) out.innerHTML=html; return html; };
  if(!f.path){ say('<div class="cb-degraded">⛔ 未点名 path ⇒ 不提交（前端 ⛔ 不代填授权对象）</div>'); return {ok:false, error:'missing_path', sent:false}; }
  let ttl=null;
  if(String(f.ttl_s||'').trim()){
    ttl=Number(f.ttl_s);
    if(!isFinite(ttl) || ttl<=0){ say('<div class="cb-degraded">⛔ ttl_s 不是正数 ⇒ 不提交（⛔ 不猜）</div>'); return {ok:false, error:'bad_ttl', sent:false}; }
  }
  const body={path:f.path, note:f.note}; if(ttl) body.ttl_s=ttl;
  let res=null;
  try{ res=await paPermPost(body); }
  catch(e){ say('<div class="cb-degraded">⚠ 未取得回执：'+esc(''+((e&&e.message)||e))+'（⛔ 不等于「没授权」）</div>'); return {ok:false, sent:true}; }
  if(!res.ok){ say('<div class="cb-degraded">⚠ 后端拒收（HTTP '+esc(String(res.status))+'）：'+esc(String(res.error))+'（原样可见，⛔ 不吞）</div>'); return res; }
  say('✅ 已授权：'+paPermPathsHtml(res.data&&res.data.paths));
  await paPermLoad(true);
  return res;
}
async function paPermRevoke(){
  const out=paPermEl('ppGateMsg');
  const say=function(html){ if(out) out.innerHTML=html; return html; };
  let res=null;
  try{ res=await paPermPost({revoke:true}); }
  catch(e){ say('<div class="cb-degraded">⚠ 未取得回执：'+esc(''+((e&&e.message)||e))+'（⛔ 不等于「没撤销」）</div>'); return {ok:false, sent:true}; }
  if(!res.ok){ say('<div class="cb-degraded">⚠ 后端拒收（HTTP '+esc(String(res.status))+'）：'+esc(String(res.error))+'</div>'); return res; }
  say('✅ 已撤销（后端 revoked=true）');
  await paPermLoad(true);
  return res;
}
async function paPermSetLevel(level){
  const el=paPermEl('ppLevel');
  const want=String(level==null?(el?el.value:''):level);
  const out=paPermEl('ppLevelMsg');
  const say=function(html){ if(out) out.innerHTML=html; return html; };
  if(!want){ say('<div class="cb-degraded">⛔ 未选档 ⇒ 不提交（白名单 '+esc(PA_PERM_LEVELS.join('/'))+'）</div>'); return {ok:false, sent:false}; }
  if(PA_PERM_LEVELS.indexOf(want)<0){ say('<div class="cb-degraded">⛔ 档不在白名单（'+esc(PA_PERM_LEVELS.join('/'))+'）⇒ 不提交</div>'); return {ok:false, sent:false}; }
  let r=null;
  try{ r=await fetch(API+PA_PERM_API.perm,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:curUser(),level:want})}); }
  catch(e){ say('<div class="cb-degraded">⚠ 未取得回执：'+esc(''+((e&&e.message)||e))+'（⛔ 不等于「没改」）</div>'); return {ok:false, sent:true}; }
  let d=null; try{ d=await r.json(); }catch(e){ d=null; }
  if(r.status!==200 || !d || d.ok===false){
    const msg=(d&&(d.message||d.error))||('HTTP '+r.status);
    say('<div class="cb-degraded">⚠ 后端拒收（HTTP '+esc(String(r.status))+'）：'+esc(String(msg))+' ⇒ 按后端真值回读（⛔ 界面不留假值）</div>');
    await paPermLoad(true);
    return {ok:false, status:r.status, error:msg};
  }
  say('✅ 已写后端：'+esc(String(d.level==null?want:d.level))+'（回读见上行「权限档」）');
  await paPermLoad(true);
  return {ok:true, resp:d};
}
/* ---- PA-B1 · 授权面板 接线 END ---- */