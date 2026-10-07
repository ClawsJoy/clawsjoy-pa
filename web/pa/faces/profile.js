/* ---- 右栏 ---- */
function switchTab(btn, id){
  document.querySelectorAll('.tabs button').forEach(b=>b.classList.remove('active')); btn.classList.add('active');
  document.querySelectorAll('.pane').forEach(p=>p.classList.remove('active')); $(id).classList.add('active');
  if(id==='pane-collect') loadFieldsForm();
}
async function loadSide(){
  /* pm_1855 §三：显示名由一处（`paSyncUserChip`）写 —— ⛔ 直写机器号（旧形：`= curUser()`）。 */
  if(typeof paSyncUserChip === 'function'){ paSyncUserChip(); }else{ $('uidText').textContent = curUser(); }
  try{
    const r = await fetch(API+'/v9/pa/context?user_id='+encodeURIComponent(curUser()));
    if(r.ok){ const d=await r.json(); if(d.ok){ renderSide(d); return; } }
  }catch(e){}
  $('profileCards').innerHTML='<div class="card" style="color:var(--sub)">画像未加载（/v9/pa/context 无响应）。</div>';
  $('todoCards').innerHTML='<div class="card todo" style="color:var(--sub)">账本未加载（/v9/pa/context 无响应）。</div>';
}
const DOM_LABEL={decision:'决策',aesthetic:'审美',emotion:'情感',style:'风格',lesson:'教训',fact:'事实',product:'产品',channel:'通道'};
function renderSide(d){
  const pc=$('profileCards'); pc.innerHTML='';
  const order={decision:0,emotion:1,aesthetic:2,style:3,lesson:4,fact:5,product:6,channel:7};
  (d.profile||[]).slice().sort((a,b)=>(order[a.domain]??9)-(order[b.domain]??9)).forEach(e=>{
    const div=document.createElement('div');
    div.className='card'+(e.domain==='emotion'?' emotion':(e.domain==='aesthetic'?'':''));
    div.innerHTML='<div class="k">'+esc(DOM_LABEL[e.domain]||e.domain)+'</div>'+esc(e.value||'')+
      '<div style="color:#6e7681;font-size:10.5px;margin-top:3px">['+esc(e.confidence||'')+'] '+esc(e.date||'')+'</div>';
    pc.appendChild(div); });
  const tc=$('todoCards'); tc.innerHTML='';
  (d.ledger||[]).forEach(i=>{ const div=document.createElement('div'); div.className='todo-item';
    div.innerHTML='<span class="cb" onclick="doneTodo(\''+i.id+'\')"></span><span>'+esc(i.title||'')+(i.due?' <code>'+esc(i.due)+'</code>':'')+'</span>';
    div.style.margin='4px 11px'; tc.appendChild(div); });
}
async function doneTodo(id){
  try{ await fetch(API+'/v9/pa/ledger/done',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})}); loadSide(); }catch(e){}
}
let todoView='open';
function toggleTodoView(){ todoView = todoView==='open' ? 'done' : 'open'; $('todoViewBtn').textContent = todoView==='open' ? '看已完成' : '看待办'; todoView==='open' ? loadSide() : loadDoneTodos(); }
async function loadDoneTodos(){ const tc=$('todoCards'); tc.innerHTML=''; try{ const r=await fetch(API+'/v9/pa/ledger?user_id='+encodeURIComponent(curUser())); if(!r.ok) throw 0; const d=await r.json(); const items=(d.items||[]).filter(i=>i.status==='done'); if(!items.length){ tc.innerHTML='<div class="card todo" style="color:var(--sub)">暂无已完成项</div>'; return; } items.forEach(i=>{ const div=document.createElement('div'); div.className='todo-item done'; div.innerHTML='<span>'+esc(i.title||'')+(i.due?' <code>'+esc(i.due)+'</code>':'')+'</span>'; div.style.margin='4px 11px'; tc.appendChild(div); }); }catch(e){ tc.innerHTML='<div class="card todo" style="color:var(--sub)">账本加载失败</div>'; } }
