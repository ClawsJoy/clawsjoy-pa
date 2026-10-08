/* ---- 项目文件（沙箱） ---- */
/* 批122 C：把"在看哪个沙箱"显示出来 —— source + path 都来自响应（前端不拼路径，守 C1 契约）*/
function renderFileSource(d){
  const el=$('fileSrc'); if(!el) return;
  const src = (d && d.source) ? String(d.source) : '';
  const p = (d && d.path) ? String(d.path) : '';
  /* ⭐ pm_2061 §二.2（裁⒉）：平文唯人话 —— 端之 `source` ＋ 端径（含盘符径）⇒ 入 `title`（工程之据之地 · ⛔ 删真源 · 承 P2「可寻得」）。 */
  el.textContent = '来源：本机工作区文件（悬停本行见路径）';
  el.title = (src ? ('来源：' + src + '\n') : '来源未知\n') + (p || '');
}
async function loadFiles(){
  const box=$('fileList'); box.innerHTML='<div class="fitem">…</div>';
  try{
    /* 批122 A：与聊天同一个 sid（curSession() === __APP_STATE.sessionId === activeThread().id）*/
    const r = await fetch(API+'/v9/sandbox/list', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({user_id:curUser(), session_id:curSession(), path:'.', skip_quota:true})});
    const d = await r.json();
    renderFileSource(d);
    /* 批122 B：后端把 files / dirs 分成两个字段返回，面板此前只取 files ⇒ 目录永远不显示 */
    const nameOf = x => (typeof x==='string' ? x : ((x && (x.name||x.path)) || '?'));
    const dirs = Array.isArray(d.dirs) ? d.dirs.map(x=>({n:nameOf(x), isDir:true})) : [];
    const files = Array.isArray(d.files) ? d.files.map(x=>({n:nameOf(x), isDir:false})) : [];
    const items = (dirs.length||files.length) ? dirs.concat(files)
      : (d.items || d.entries || d.data || []).map(x=>({n:nameOf(x), isDir:(typeof x==='object' && !!(x.is_dir||x.type==='dir'))}));
    if(!items.length){ box.innerHTML='<div class="fitem">（空或需在沙箱会话中）</div>'; return; }
    box.innerHTML = items.slice(0,60).map(x=>
      '<div class="fitem" title="'+esc(String(x.n))+'">'+(x.isDir?'📁 ':'📄 ')+esc(String(x.n).split('/').pop())+'</div>'
    ).join('');
  }catch(e){ box.innerHTML='<div class="fitem">文件面板待接线（/v9/sandbox/list）</div>'; }
}
