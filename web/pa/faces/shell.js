/* ---- 模式栏 ---- */
function renderModes(){
  $('modes').innerHTML = Object.entries(MODES).map(([k,m])=>{
    const act = k===state.mode ? ' active' : '';
    const res = m.on ? '' : ' reserved';
    return '<button class="mode'+act+res+'" data-mode="'+k+'" title="'+esc(m.hint)+'">'+
      '<span class="ic">'+m.ic+'</span>'+esc(m.label)+(m.on?'':' ·预留')+'</button>';
  }).join('');
  $('modes').querySelectorAll('.mode').forEach(b=>b.addEventListener('click',()=>setMode(b.dataset.mode)));
}
/* ---- PM-011 前置件（2026-09-30 · PM 裁「丙 的更严形态」）· 顶栏权限徽标**三态** ----------
   病：`data/v9/pa/permission.json` 与 `data/v9/pes/boss_grant.json` **都不存在**，
       顶栏却显示「权限: 标准」—— 那是**默认值假装成读数**
       （与 437 假绿 ／ 验收-B「沙箱不在 ⇒ 过期 0」／ `_jsonl_lines` 的 `0` 同族）。
   三态（PM §三）：⒜ 有真实授予文件 ⇒ 该档 ＋ 来源路径 ｜ ⒝ 无文件 ⇒ 明说「未授予（默认档）」
                   ｜ ⒞ 读不到 ⇒ 标「面不可读」。
   ⛔ 本组只做**显示分型**：⛔ 不合并变量、⛔ 不改任何生效语义（谁放行仍由后端判）。
   ⛔ 「模式要求」（`MODES[].perm`）与「账号授予」（授予文件）**语义不同** ⇒ 各自标注、互不顶替。 */
let paGrant = null;        /* 后端给的来源面 {pa:{path,exists},pes:{path,exists}} */
let paGrantLevel = null;   /* 后端给的档位（生效值；可能仍是默认值，由 grant 面说清来源） */
let paGrantErr;            /* undefined = 还没取；字符串 = 读不到的原因原文 */
function paPermBadge(modePerm, level, grant, err){
  var _s = function(v){ return (v===undefined||v===null||v==='') ? '—' : String(v); };
  var req = ' ｜ 模式要求: ' + _s(modePerm);
  if(!grant){
    if(err===undefined) return '权限: ⏳ 授予读数读取中（尚未取到）' + req;
    return '权限: ⚠ 面不可读（' + String(err).slice(0,60) + '）' + req;              /* ⒞ */
  }
  var srcs = [];
  if(grant.pa && grant.pa.exists) srcs.push(String(grant.pa.path||''));
  if(grant.pes && grant.pes.exists) srcs.push(String(grant.pes.path||''));
  if(!srcs.length) return '权限: 未授予（默认档「'+_s(level)+'」）' + req;          /* ⒝ */
  return '权限: '+_s(level)+'（来源：本机授予档）' + req;                    /* ⒜ */
}
function paPermBadgeTip(grant){
  if(!grant) return '';
  var srcs = [];
  if(grant.pa && grant.pa.exists) srcs.push(String(grant.pa.path||''));
  if(grant.pes && grant.pes.exists) srcs.push(String(grant.pes.path||''));
  return srcs.length ? ('来源：' + srcs.join(' ／ ')) : '';
}
function renderPermBadge(){
  var el = $('modePerm'); if(!el) return;
  var cfg = MODES[state.mode] || {};
  el.textContent = paPermBadge(cfg.perm, paGrantLevel, paGrant, paGrantErr);
  el.title = paPermBadgeTip(paGrant);
}
function fetchPaGrant(){
  return fetch(API+'/v9/pa/permission?user_id='+encodeURIComponent(curUser()))
    .then(function(r){ return r.json().then(function(d){ return {status:r.status,d:d}; })
                                          .catch(function(){ return {status:r.status,d:null}; }); })
    .then(function(x){
      var d = x.d;
      if(x.status!==200 || !d || d.ok===false){
        paGrant=null; paGrantLevel=null;
        paGrantErr=(d && (d.message||d.error)) || ('HTTP '+x.status);
      }else if(!d.grant){
        paGrant=null; paGrantLevel=d.level; paGrantErr='响应缺 grant 来源面（后端未升级？）';
      }else{
        paGrant=d.grant; paGrantLevel=d.level; paGrantErr=null;
        if(d.level && $('cfgPerm')) $('cfgPerm').value = d.level;
      }
      renderPermBadge();
    })
    .catch(function(e){ paGrant=null; paGrantLevel=null; paGrantErr=''+((e&&e.message)||e); renderPermBadge(); });
}
/* PM-011 · PA_BUILD（2026-09-30 · PM 批）：页面**自报构建指纹**。
   ⛔ 页面不内嵌自身 sha16（改了字节指纹必变，内嵌＝自欺）—— 指纹由**服务端**
   对「它实际发出去的那份 web/pa.html」现读现算，页面只显示。
   三态：拿不到 ⇒ 明说「读数不可得」（⛔ 不填占位符，与「0 看起来像读数」同族）。 */
function fetchPaBuild(){
  var el=$('paBuild');
  return fetch(API+'/v9/pa/build', {cache:'no-store'})
    .then(function(r){ return r.json().then(function(d){ return {status:r.status,d:d}; })
                                          .catch(function(){ return {status:r.status,d:null}; }); })
    .then(function(x){
      var d=x.d, good=(x.status===200 && d && d.ok!==false && d.sha16);
      window.PA_BUILD = good ? String(d.sha16) : null;
      try{ document.documentElement.setAttribute('data-pa-build', good?String(d.sha16):'unreadable'); }catch(e){}
      if(el){
        el.textContent = good ? ('构建 '+d.sha16) : ('构建 ⚠ 读数不可得（HTTP '+x.status+'）');
        el.title = good ? ('页面构建指纹（服务端对实际发出的 web/pa.html 现算）· '+d.bytes+' B · '+d.mtime+' · '+d.path)
                        : '构建指纹读数不可得（⛔ 不是「没有构建」，是读数拿不到）';
      }
    })
    .catch(function(e){ window.PA_BUILD=null;
      try{ document.documentElement.setAttribute('data-pa-build','unreadable'); }catch(_e){}
      if(el){ el.textContent='构建 ⚠ 读数不可得'; el.title=''+((e&&e.message)||e); } });
}
