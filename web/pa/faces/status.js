/* ---- 批159 · P0-2：8 态可见化 + 超时阈值（后端已有 SSE heartbeat / progress / write_pending / cancel） ----
   判据（体检项 114 的检测清单思路）：状态由**后端事件**驱动，不由前端猜；
   「无事件时长」超过阈值必须变成可见提示（30s 提醒 / 90s 疑似卡住），避免「发了没反应」（HSR）。 */
const PA_STATE_DEF = {
  idle:      {ic:'○',  label:'就绪',     cls:'st-idle'},
  running:   {ic:'▶',  label:'正在执行', cls:'st-run'},
  model:     {ic:'⏳', label:'等待模型', cls:'st-wait'},
  tool:      {ic:'🔧', label:'等待工具', cls:'st-wait'},
  approval:  {ic:'✋', label:'等待审批', cls:'st-appr'},
  verifying: {ic:'🔍', label:'验证中',   cls:'st-run'},
  done:      {ic:'✅', label:'已完成',   cls:'st-ok'},
  failed:    {ic:'❌', label:'已失败',   cls:'st-err'},
  stopped:   {ic:'⏹', label:'已停止',   cls:'st-err'},
  /* M2-A · Step 3.1：**只增键** —— 阻断不再借 tool 态显示（既有 9 键一字未改） */
  blocked:   {ic:'⛔', label:'已阻断',   cls:'st-block'}
};
// 终态不再计时：已失败/已停止/已完成/就绪若继续累加「Ns」会误导成"还在跑"（自检发现：failed 态秒数一直跳）
const PA_TERMINAL = {idle:1, done:1, failed:1, stopped:1};
const PA_T_WARN_S = 30;    // 30s 无任何后端事件 ⇒ 显式提示
const PA_T_STALE_S = 90;   // 90s ⇒ 疑似卡住（提示可点停止）
let paRun = {state:'idle', t0:Date.now(), lastEvent:Date.now(), timer:null, note:'', threadId:null, busy:false, receipt:null, evidence:null};
let paRunSrc = '—（尚未收到后端事件）';   /* 裁③ · L76：本状态之真源标识（非空泛词） */
/* ===== P9 · BUG-1/BUG-2 三个小件（都在前端，但都以后端回执为准）===== */
function paLooksLikeKnowledgeQuestion(t){
  /* ⭐ L83 · 判据单源（承 pm_1005 §三）：问域之判**只留一处出口** = selfdesc.js 之 paAskClass。
     有统一判层 ⇒ **调用之**（⛔ 二处各判）；无（旧页 web/pa.html ⛔ 载 selfdesc.js）⇒ 回原启发式，⛔ 回退行为变。 */
  if(typeof paAskClass === 'function'){ try{ return paAskClass(t) === 'knowledge'; }catch(e){} }
  const s=String(t||'').trim(); if(!s) return false;
  if(/[?？]$/.test(s)) return true;
  return /(是什么|有哪些|有多少|多少|哪个|哪一个|哪家|是不是|有没有|能不能|结论|数据|数字|标准|要求|规定|政策|流程|范围)/.test(s);
}
async function paAskGate(text){
  try{
    /* pm_1096 §二.3（老板批 P11 · 承 L83 单源）：请求体补 session_id ＝ 本页线程 id
       （与 recordPaTurn 之既有同径 · ⛔ 自造键）。不补 ⇒ 后端 _last_user_before 落「最新会话」
       （picked_by:newest）⇒ 元问之「上一句」取自他会话，而屏上仍写「据：本会话」＝ 声明失实。 */
    let _sid=''; try{ const _t=(typeof activeThread==='function')?activeThread():null; _sid=(_t&&_t.id)?String(_t.id):''; }catch(e){ _sid=''; }
    const _q={user_id:curUser(),question:text,limit:5}; if(_sid) _q.session_id=_sid;
    const r=await fetch(API+'/v9/pa/ask',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify(_q)});
    const d=await r.json(); return (d&&d.ok)?d:null;
  }catch(e){ return null; }
}
async function recordPaTurn(sid,userText,assistantText,meta){
  /* 工作/开发模式的**落盘出口**：后端 /v9/pa/turn 只记不动手，回执给前端用来判断该不该说「已落盘」 */
  /* ⭐ pm 1184 §一.⒝（承 pm 1183 §五.3 ／ TD 1056 §五）：**档行源标三键由前端传** ——
     `origin`（闭合集：model ／ grounded ／ refused ／ unspecified · 词表一处定义在 core\pa\dialog.py）／
     `grounded`（bool ／ ⛔ 缺键 ＝ 未标）／ `answer_source`（后端原值：decision ／ knowledge ／ refused …）。
     ⚠ 后端**不冒**：调用方未声明 ⇒ 其落 `unspecified`（⛔ 冒 model ／ ⛔ 冒 grounded）⇒ 故**唯当知其实**方传
     （承「⛔ 以我之预期充文本之实」）；`meta` 缺 ／ 某键缺 ⇒ **不发该键**（行形照旧 · 向后兼容）。 */
  try{
    const _b={user_id:curUser(),session_id:sid,user_text:userText,assistant_text:assistantText,mode:(state&&state.mode)||''};
    if(meta && typeof meta==='object'){
      if(meta.origin) _b.origin=String(meta.origin);
      if(meta.grounded===true || meta.grounded===false) _b.grounded=meta.grounded;
      if(meta.answer_source) _b.answer_source=String(meta.answer_source);
    }
    const r=await fetch(API+'/v9/pa/turn',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify(_b)});
    const d=await r.json(); return (d&&d.ok)?d:null;
  }catch(e){ return null; }
}
function paSetState(k, note, src){
  if(!PA_STATE_DEF[k]) k='idle';
  const now=Date.now();
  if(k!==paRun.state) paRun.t0=now;
  paRun.state=k; paRun.lastEvent=now; paRun.note=note||'';
  if(src) paRunSrc=String(src);
  if(!paRun.timer) paRun.timer=setInterval(paRenderState, 1000);
  paRenderState();
}
function paBeat(note){ paRun.lastEvent=Date.now(); if(note) paRun.note=note; paRenderState(); }
function paRenderState(){
  const el=document.getElementById('runState'); if(!el) return;
  const d=PA_STATE_DEF[paRun.state]||PA_STATE_DEF.idle;
  let txt=d.ic+' '+d.label;
  // 批175：等待审批/请示要把「在等什么」显示在药丸上 ——
  // 此前 note 只进 title（鼠标悬停才看得到），老板从药丸上看不出「等的是确认」。
  // 只对 approval 生效（其余状态 note 仍只进 title，避免药丸变长）。
  if(paRun.state==='approval' && paRun.note){ txt += ' · ' + String(paRun.note).slice(0,28); }
  if(!PA_TERMINAL[paRun.state]){   // 批159：仅"进行中"的态才显示已耗时/无进展
    const secs=Math.round((Date.now()-paRun.t0)/1000);
    const quiet=Math.round((Date.now()-paRun.lastEvent)/1000);
    txt+=' '+secs+'s';
    if(quiet>=PA_T_STALE_S) txt+=' · ⚠ 疑似卡住'+quiet+'s（可点停止）';
    else if(quiet>=PA_T_WARN_S) txt+=' · 已 '+quiet+'s 无进展';
  }
  el.textContent=txt;
  el.className='runstate '+(d.cls||'');
  el.title='运行状态：'+d.label+(paRun.note?('（'+paRun.note+'）'):'');
  const srcEl=document.getElementById('runStateSrc');
  if(srcEl) srcEl.textContent='状态来源：'+paRunSrc;   /* 裁③ · L76：可见之真源标识（⛔ 悬停才见） */
}
function setBusy(on){ $('sendBtn').disabled=on; $('stopBtn').style.display=on?'inline-block':'none'; if(on){ $('connDot').textContent='● 处理中…'; } else { probeConn(); } }
/* 批196 · 本地浏览器：富状态 + 一键启动（老板：不能让老板自己去 PowerShell 起客户端）
   状态走 /v9/pa/local_client/status（含 client 类型与已连接秒数）；启动走 /v9/pa/local_client/start，
   命令由后端硬编码（页面只发 user_id）⇒ 页面无法把它指向别的账号/端口/程序。 */
async function probeConn(){
  const el=$('connDot'), btn=$('connStart');
  try{
    const r=await fetch(API+'/v9/pa/local_client/status?user_id='+encodeURIComponent(curUser()));
    const d=await r.json();
    if(d && d.connected){
      const _age=(typeof d.age_s==='number')?Math.round(d.age_s):null;
      el.textContent='● 本地浏览器已连（'+(d.client||'client')+(_age!==null?('，'+_age+'s'):'')+'）';
      el.style.color='var(--green)';
      if(btn) btn.style.display='none';
      return true;
    }
    /* P9 · BUG-4：状态要**可复核** —— 带探针端点与本地读数时刻（⛔ 不是前端自己猜） */
    el.textContent='● 本地浏览器未连（探针 /v9/pa/local_client/status · '+new Date().toLocaleTimeString('zh-CN',{hour12:false})+'）';
    el.title='后端返回 connected=false ⇒ 客户端未连；可点「启动本地浏览器」';
    el.style.color='var(--amber)';
    if(btn) btn.style.display=(d && d.launchable===false)?'none':'inline-block';
    return false;
  }catch(e){
    el.textContent='● 连接未知';
    el.style.color='var(--sub)';
    if(btn) btn.style.display='none';
    return false;
  }
}
async function paStartLocalClient(){
  const btn=$('connStart');
  if(btn){ btn.style.display='none'; }
  addLog('🚀 正在请求启动本地浏览器客户端…','stage',true,'批196');
  try{
    const r=await fetch(API+'/v9/pa/local_client/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:curUser()})});
    const d=await r.json().catch(function(){ return {}; });
    if(d && d.started){ addLog('🚀 已启动（Windows 侧 agent_client）—— 等它连上，状态会自动更新','ok',true,'批196'); }
    else if(d && d.already){ addLog('✅ 客户端已在连接中，无需重复启动','ok',true,'批196'); }
    else if(d && d.cooldown){ addLog('⏳ 刚启动过（'+d.cooldown+'s 后可再试），先等它连上','warn',true,'批196'); }
    else { addLog('⚠ 未能启动：'+((d&&d.error)||'未知原因')+'；可手动运行桌面 agent_client','warn',true,'批196'); }
  }catch(e){
    addLog('⚠ 启动请求失败：'+e.message,'err',true,'批196');
  }
  for(let i=0;i<10;i++){
    await new Promise(function(res){ setTimeout(res,2000); });
    const _c=await probeConn();
    if(_c){ addLog('✅ 本地浏览器已连接','ok',true,'批196'); return; }
  }
  addLog('⚠ 20 秒内仍未连上：看 Windows 侧是否弹出客户端窗口或它的控制台报错','warn',true,'批196');
  await probeConn();
}

/* 裁② · pm_990 §三 ／ pm_993：界面态**只读上屏** —— 读 web/pa/ui_state.json（技总器 --落 写的一行 JSON）。
   ⛔ 前端自算 ／ ⛔ 直读 nvidia-smi ／ ⛔ 自造数据源；读不到 ⇒ 明说「未知」，⛔ 猜（L76）。
   ⚠ 快照非实时（刷新约每小时一轮）⇒ 「采样刻」必须写在界面上（⛔ 省）。 */
async function paLoadUiState(){
  const el = document.getElementById('paUiStateRow'); if(!el) return null;
  const U = 'web/pa/ui_state.json';
  try{
    const r = await fetch('pa/ui_state.json', {cache:'no-store'});
    if(!r.ok){ el.textContent = '如实读数：快照读不到（' + U + ' · HTTP ' + r.status + '）· ⛔ 未知'; return null; }
    const d = await r.json();
    const vr = (d && d['显存']) || {};
    const chk = (v)=> (v===undefined || v===null) ? '未知' : String(v);
    const num = (v)=> (typeof v==='number' && isFinite(v)) ? String(v) : '未知';
    const fv = (d && Array.isArray(d.Forever)) ? (d.Forever.length ? d.Forever.join('/') : '—') : '未知';
    el.textContent = '如实读数（只读快照 ' + U + '）：已载 ' + num(d && d['已载'])
      + ' · 显存 ' + num(vr.free) + '/' + num(vr.total) + ' MB'
      + ' · Forever ' + fv
      + ' · 本地在 ' + chk(d && d['本地在']) + ' · 远端在 ' + chk(d && d['远端在'])
      + '（' + chk(d && d['远端host']) + '）'
      + ' · 采样刻 ' + chk(d && d['刻']) + '（快照 · ⛔ 实时）';
    return d;
  }catch(e){
    el.textContent = '如实读数：快照读不到（' + U + ' · ' + String((e && e.message) || e) + '）· ⛔ 未知';
    return null;
  }
}
