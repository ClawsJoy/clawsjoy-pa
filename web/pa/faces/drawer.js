/* ---- 抽屉 ---- */
/* ---- 批193 · 三栏显式折叠（老板提议）：默认显示、按钮常显、状态持久化 ----
   宽屏：行内收起/展开（中栏 .chat-col flex:1 自动占满）；窄屏(<1000px)：仍走浮层抽屉（原行为不动）。*/
function paPanels(){ try{ return JSON.parse(localStorage.getItem('pa_panels')||'{}')||{}; }catch(e){ return {}; } }
function paApplyPanels(){
  var p=paPanels();
  document.body.classList.toggle('hide-left', p.left===false);
  document.body.classList.toggle('hide-right', p.right===false);
  document.body.classList.toggle('hide-top', p.top===false);
  var lb=$('drawerLeftBtn'), rb=$('drawerRightBtn');
  if(lb) lb.classList.toggle('off', p.left===false);
  if(rb) rb.classList.toggle('off', p.right===false);
}
function paSetPanel(which, on){
  var p=paPanels(); p[which]=!!on;
  try{ localStorage.setItem('pa_panels', JSON.stringify(p)); }catch(e){}
  paApplyPanels();
}
function togglePanel(which){ var p=paPanels(); paSetPanel(which, p[which]===false); }
function toggleTop(){ togglePanel('top'); }
function toggleDrawer(which){
  if(window.innerWidth<=1000){   /* 窄屏：浮层抽屉（原行为）*/
    var el=which==='left'?document.querySelector('.left'):document.querySelector('.side');
    el.classList.toggle('drawer-open');
    $('drawerMask').classList.toggle('show', !!document.querySelector('.left.drawer-open,.side.drawer-open'));
    return;
  }
  togglePanel(which==='left'?'left':'right');
}
function closeDrawers(){ document.querySelectorAll('.left,.side').forEach(el=>el.classList.remove('drawer-open')); $('drawerMask').classList.remove('show'); }
/* 批193 · 口径 A：审批/请示到达 ⇒ 自动滚动到卡片 + 高亮描边（侧栏折叠不会挡住中栏卡片）*/
function paFlashApproval(el){
  try{
    if(!el) return;
    el.classList.add('pa-flash');
    if(el.scrollIntoView) el.scrollIntoView({block:'center',behavior:'smooth'});
    setTimeout(function(){ el.classList.remove('pa-flash'); }, 2800);
  }catch(e){}
}
