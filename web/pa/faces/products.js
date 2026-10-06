/* ---- ② 产物预览: 从助手消息检测输出文件 → 嵌入式卡片 ---- */
function detectOutputs(text){
  const paths=[]; const re=/(data\/(?:reports|tmp)\/[^\s`"'，。]+?\.(?:md|txt|json|pptx))/g; let m;
  while((m=re.exec(text))){ if(!paths.includes(m[1])) paths.push(m[1]); }
  return paths.slice(0,5);
}
const _outputContent={};
/* M2-A · Step 3.2：产物卡 DOM 走**统一出口** paRenderCard('artifact', …)。
   三条与 Step 2 一致的纪律（不靠自觉）：
   1. **宿主显式传入 #thread**：产物卡按设计是**消息内联**的交付预览 —— 批201 起它随
      「**已持久化的助手正文**」重建（F5 语义），所以**不能**搬进不持久化的 #paCards；
      这也是 paRenderCard 唯一允许的显式宿主（见函数注释与 tests/pes/test_m2a_artifact_card.py）。
   2. **来源必须显式**：路径是**正文正则探测**得来 ⇒ 只传 `reported_source:'text_probe'`，
      卡上如实标「来源：正文探测（非核验）」——**不把探测当事实**（防「假成交」）。
   3. **核验字段一律不代填**：exists/sha256/bytes/verified_by/done_when_status 全部**不传**
      （未取到就不是事实）⇒ 卡上显示「未核验 / 未经验证者签署 / 没有契约，无法裁决完成」。
   读不到正文 ⇒ **不渲染空壳**（今天的行为原样保留）。 */
async function renderOutputCard(path){
  // 产物卡片分流：.pptx 不是文本产物，渲染成"缩略图墙"（灵犀导出的 14 页 PNG）
  // Step 3.2 归一说明：pptx 墙是**另一类卡**（缩略图 + 批注 + 重新导出），本步**未迁**（见笔记 §未迁）。
  if(/\.pptx$/i.test(String(path))){ return renderPptWall(path); }
  const t=activeThread(); let content=null;
  try{
    const r=await fetch(API+'/v9/sandbox/read',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({user_id:curUser(),session_id:t.id,path:path})});
    if(r.ok){ const d=await r.json(); if(d&&d.success) content=d.content||''; }
  }catch(e){}
  if(content===null) return;
  _outputContent[path]=content;   /* 正文缓存：卡上的「展开全文/下载」用它；不是 payload 字段，白名单不被污染 */
  // 批201 的去重已并入出口：paRenderCard 按（kind, 第一个必填字段）复用同卡，同一 path 只留一张
  const card=paRenderCard('artifact', {path:String(path), reported_source:'text_probe'}, $('thread'));
  const th=$('thread'); if(card&&th) th.scrollTop=th.scrollHeight;
  return card;
}
function downloadOutput(btn){
  const card=btn.closest('.output-card'); if(!card) return;
  const path=card.dataset.path; const content=_outputContent[path]||'';
  const blob=new Blob([content],{type:'text/markdown;charset=utf-8'});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a'); a.href=url; a.download=String(path).split('/').pop();
  document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
}

/* ---- ③ PPT 缩略图墙（C 块 2026-09-13）------------------------------------
   产物卡片识别 .pptx → 14 张缩略图 → 每页「这页的问题」批注。
   缩略图: 灵犀 wpp_export_slide_as_image 导出，清单见 web/ppt_thumbs/manifest.json。
   批注本轮只在前端生效（localStorage），落库留给后端批注接口。
   通道: 一律走 PA 的 /v9/pa/proxy（endpoint_guard 按 MCP 工具名分级），不直连 3890。 */
const PPT_THUMB_BASE='ppt_thumbs/';
const PPT_COMMENT_KEY='pa_ppt_comments_v1';
const _pptManifestCache={};
/* 批79 ctx 生产端：semanticCtx() 采集用的键（此前无人写入 → 运行时 ctx 恒空）*/
var _planStepIndex=0, _planStepTotal=0, PPT_DECK='';

function pptCommentsAll(){
  try{ return JSON.parse(localStorage.getItem(PPT_COMMENT_KEY)||'{}'); }catch(e){ return {}; }
}
function pptCommentsOf(deck){ const a=pptCommentsAll(); return a[deck]||[]; }
function addPptComment(deck,pageIndex,text){
  const rec={page_index:Number(pageIndex), comment:String(text||'').trim(), timestamp:new Date().toISOString()};
  if(!rec.comment) return null;
  const a=pptCommentsAll(); (a[deck]=a[deck]||[]).push(rec);
  try{ localStorage.setItem(PPT_COMMENT_KEY,JSON.stringify(a)); }catch(e){}
  /* 批69 C3 双写：后端为准 + localStorage 离线兜底（本地已写，POST 失败不影响本次交互）*/
  try{
    fetch(API+'/v9/pa/ppt/comments',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({deck:deck,page_index:rec.page_index,comment:rec.comment})})
      .then(function(r){ return r.ok?r.json():null; })
      .then(function(d){ if(d&&d.ok){ rec.backendAt=(d.comment||{}).at; } else if(d===null){ console.warn('批注后端写入未成功（已存本地兜底）'); } })
      .catch(function(e){ console.warn('批注后端不可达（已存本地兜底）',e); });
  }catch(e){}
  return rec;
}

/* 批69 C3：从后端拉批注并合并进本地（**后端为准**；不可达则静默保留 localStorage 兜底）*/
async function pptCommentsSyncFromBackend(deck,card){
  try{
    const r=await fetch(API+'/v9/pa/ppt/comments?deck='+encodeURIComponent(deck));
    if(!r.ok) return 0;
    const d=await r.json();
    if(!d||!d.ok||!Array.isArray(d.comments)||!d.comments.length) return 0;
    const a=pptCommentsAll(); const arr=Array.isArray(a[deck])?a[deck]:[];
    let n=0;
    d.comments.forEach(function(bc){
      const dup=arr.some(function(x){ return Number(x.page_index)===Number(bc.page_index) && String(x.comment)===String(bc.comment); });
      if(!dup){ arr.push({page_index:bc.page_index,comment:bc.comment,timestamp:bc.at,from:'backend'}); n++; }
    });
    if(n){ a[deck]=arr; try{ localStorage.setItem(PPT_COMMENT_KEY,JSON.stringify(a)); }catch(e){} if(card) renderPptComments(card); }
    return n;
  }catch(e){ return 0; }
}

/* PA 通道调灵犀 MCP（⭐ 我方闭环）：唯一入口 /v9/pa/proxy（不直连 3890）。
   ⚠ 名实之辨（pm_1123 §一.2 · 本线择 ⒝ 加注）：路径名 "proxy" 系历史名 ⇒ 实为**我方** MCP
   调用（body.path='/mcp/call' ⇒ 灵犀 3890 之 /mcp/call）⇒ ⛔ 非他方平台之代理（承 L186 名实须符）。 */
async function paMcp(name,args,timeout){
  const r=await fetch(API+'/v9/pa/proxy',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({user_id:curUser(),method:'POST',path:'/mcp/call',timeout:timeout||60,
      body:{name:name,args:args||{}}})});
  const d=await r.json().catch(function(){ return {}; });
  if(!r.ok||!d.ok) throw new Error((d&&(d.error||d.blocked_by))||('HTTP '+r.status));
  return d.data||{};
}

async function renderPptWall(path){
  const name=String(path).split('/').pop();
  const th=$('thread');
  const card=document.createElement('div');
  card.className='output-card ppt-card'; card.dataset.path=path; card.dataset.deck=name;
  card.innerHTML='<div class="oc-head"><span>📊</span><span class="oc-name">'+esc(name)+'</span>'+
    '<span class="oc-ai" style="font-size:10.5px;color:#7ee787;border:1px solid #2ea043;border-radius:5px;padding:0 6px">AI 辅助生成</span>'+
    '<span class="oc-path">'+esc(path)+'</span>'+
    '<button class="oc-toggle oc-reexport" onclick="exportDeckThumbs(this)">重新导出（灵犀）</button></div>'+
    '<div class="ppt-export-log"></div><div class="ppt-wall"></div><div class="ppt-cmt-panel"></div>';
  th.appendChild(card); th.scrollTop=th.scrollHeight;
  await loadPptWall(card);
  return card;
}

async function loadPptWall(card){
  const deck=card.dataset.deck, wall=card.querySelector('.ppt-wall');
  wall.innerHTML='<div class="ppt-loading">缩略图加载中…</div>';
  let man=_pptManifestCache[deck];
  if(!man){
    try{
      const r=await fetch(PPT_THUMB_BASE+'manifest.json',{cache:'no-store'});
      if(!r.ok) throw new Error('HTTP '+r.status);
      man=await r.json(); _pptManifestCache[deck]=man; PPT_DECK=deck;
    }catch(e){
      wall.innerHTML='<div class="ppt-loading">缩略图清单加载失败：'+esc(e.message)+'</div>';
      return;
    }
  }
  wall.innerHTML='';
  wall.dataset.deckManifest=String((man.pages||[]).length);
  wall.dataset.manifestDeck=String(man.deck||'');
  // 不说谎：清单目前只覆盖 V6 这一份 deck，卡片若指向别的 pptx 必须显式说明
  if(man.deck && String(man.deck)!==String(deck)){
    const warn=document.createElement('div'); warn.className='ppt-loading';
    warn.textContent='注：本卡片指向 '+deck+'，但缩略图清单当前只有「'+man.deck+'」（C 块探针范围）。';
    wall.appendChild(warn);
  }
  (man.pages||[]).forEach(function(p){ wall.appendChild(buildPptThumb(card,deck,p)); });
  renderPptComments(card);
  wall.dataset.thumbCount=String(wall.querySelectorAll('.ppt-thumb').length);
  pptCommentsSyncFromBackend(deck,card);   /* 批69 C3：后端批注合并（渲染后异步拉取，失败静默兜底）*/


/* 用后端返回的 url_base 重写墙上图片地址（唯一允许的图片地址来源） */
function applyThumbUrlBase(card, urlBase){
  if(!urlBase) return 0;
  let n=0;
  card.querySelectorAll('.ppt-thumb img').forEach(function(img){
    const m=/([^/]+)$/.exec(img.getAttribute('src')||'');
    if(m && m[1]){ img.src = urlBase + m[1]; n++; }
  });
  return n;
}
}

/* 批73 C1：把缩略图**字节**交给后端落盘，落哪儿由后端定；前端只用返回值拼 URL。
 本函数不出现任何文件系统路径（C: / UNC / /mnt/ / 绝对路径）——有静态防线守着。 */
async function uploadDeckThumbs(deck, files){
const r = await fetch(API+'/v9/pa/artifact/thumbs',{method:'POST',
  headers:{'Content-Type':'application/json'},
  body:JSON.stringify({user_id:curUser(), deck:deck, files:files||[]})});
const d = await r.json().catch(function(){ return {}; });
if(!r.ok || !d.ok) throw new Error((d&&d.error)||('HTTP '+r.status));
return d;                       /* {ok,count,url_base,manifest_url,pages} */
}

function buildPptThumb(card,deck,p){
  const fig=document.createElement('figure');
  fig.className='ppt-thumb'; fig.dataset.page=String(p.page_index); fig.dataset.title=p.title||'';
  const img=document.createElement('img');
  const _rel=String(p.png||'').replace(/^ppt_thumbs\//,'');
  img.src=PPT_THUMB_BASE+_rel; img.alt='P'+p.page_index+' '+(p.title||''); img.loading='lazy';
  img.onerror=function(){ fig.classList.add('img-missing'); };
  fig.appendChild(img);
  const cap=document.createElement('figcaption');
  cap.textContent='P'+String(p.page_index).padStart(2,'0')+' · '+(p.title||'');
  if(p.voiceover) cap.title=p.voiceover;
  fig.appendChild(cap);
  const btn=document.createElement('button');
  btn.className='ppt-cmt-btn'; btn.textContent='这页的问题';
  btn.onclick=function(){ togglePptCommentForm(fig,p); };
  fig.appendChild(btn);
  const list=document.createElement('div'); list.className='ppt-cmt-list';
  fig.appendChild(list);
  return fig;
}

function togglePptCommentForm(fig,p){
  const old=fig.querySelector('.ppt-cmt-form');
  if(old){ old.remove(); return; }
  const form=document.createElement('div'); form.className='ppt-cmt-form';
  const ta=document.createElement('textarea'); ta.rows=2;
  ta.placeholder='P'+p.page_index+' 有什么问题？'; ta.className='ppt-cmt-input';
  form.appendChild(ta);
  const ok=document.createElement('button'); ok.className='ppt-cmt-ok'; ok.textContent='提交批注';
  ok.onclick=function(){
    const card=fig.closest('.output-card');
    const rec=addPptComment(card.dataset.deck,p.page_index,ta.value);
    if(!rec){ ta.focus(); return; }
    form.remove();
    renderPptComments(card);
    card.querySelector('.ppt-cmt-panel').dataset.lastComment=JSON.stringify(rec);
    addLog('📝 P'+rec.page_index+' 批注：'+rec.comment,'ok',true);
  };
  form.appendChild(ok);
  fig.appendChild(form); ta.focus();
}

function renderPptComments(card){
  const deck=card.dataset.deck, items=pptCommentsOf(deck);
  card.querySelectorAll('.ppt-thumb').forEach(function(fig){
    const n=parseInt(fig.dataset.page,10);
    const list=fig.querySelector('.ppt-cmt-list');
    if(!list) return;
    list.innerHTML=items.filter(function(c){ return c.page_index===n; }).map(function(c){
      return '<div class="ppt-cmt-item"><span class="t">'+esc(String(c.timestamp).slice(11,19))+'</span>'+esc(c.comment)+'</div>';
    }).join('');
  });
  const panel=card.querySelector('.ppt-cmt-panel');
  if(!panel) return;
  panel.innerHTML='<div class="ppt-cmt-head">批注 <b class="ppt-cmt-n">'+items.length+'</b> 条'+
    (items.length?'':'（点每页「这页的问题」加一条）')+'</div>'+
    '<div class="ppt-cmt-all">'+items.map(function(c){
      return '<div class="ppt-cmt-row"><code>P'+String(c.page_index).padStart(2,'0')+'</code> '+esc(c.comment)+
             ' <span class="t">'+esc(c.timestamp)+'</span></div>';
    }).join('')+'</div>';
  card.dataset.commentCount=String(items.length);
}

/* C4 接线：识别 .pptx → 调灵犀导出（经 PA 通道）→ 缩略图墙刷新 */
async function exportDeckThumbs(btn){
  const card=btn.closest('.output-card');
  if(!card) return;
  const out=card.querySelector('.ppt-export-log');
  /* 渲染目录（承 pm_1385 §一 · 件④ ⓒ · 拔活硬编）：⛔ 前端自持径 —— 旧为开发机桌面之硬编
     （含盘符 ＋ 用户名）⇒ 净机必败。真源 ＝ 后端**一处出径** GET /v9/pa/env 之 `paths.render`
     （`core/pa/env_face.py` 之 `resolve_paths()` 之 `render` 键 —— ⭐ 引位置用「符号之锚」·
     ⛔ 手书行号 · 承 pm_1425 §二.2）＋ `paths_src.render`。取不到时二分（承 pm_1346 §二.1
     「身分不同者 ⛔ 同支」）：① 后端未应答 ⇒ `PA_GAP.down` ② 应答在而键为 null ⇒ `PA_GAP.todo`
     （附后端之为何）。⛔ 静默 ／ ⛔ 以字面径兜底（承 pm_1367 §二.1）。
     ⭐ 径之消费者之界（承 pm_1423 §二.3）：本面为径之**唯一**消费者（器取 · 唯本档取 env 之 `paths`）
     ⇒ **今形合法**（单一消费者 ⇒ 无漂之险）；⭐ 若他面亦取径（消费者 ≥ `2`）⇒ 须立 `window.PA_PATHS`
     （一处出 · 承 `PA_STAMP`）—— 闸 ＝ `tests/unit/test_pa_paths_single_consumer.py`。 */
  let base='', baseSrc='', baseGap='';
  try{
    const _r=await fetch(API+'/v9/pa/env',{cache:'no-store'});
    if(!_r.ok){ baseGap=PA_GAP.down('GET /v9/pa/env HTTP '+_r.status); }
    else{
      const _j=await _r.json();
      const _p=(_j&&_j.paths)||{}, _s=(_j&&_j.paths_src)||{};
      const _v=(_p.render==null)?'':String(_p.render);
      if(_v){ base=_v; baseSrc=String(_s.render==null?'':_s.render); }
      else{ baseGap=PA_GAP.todo(String(_s.render==null?'后端无 paths_src.render':_s.render)); }
    }
  }catch(e){ baseGap=PA_GAP.down('GET /v9/pa/env 未应答（'+String((e&&e.message)||e)+'）'); }
  if(!base){
    out.dataset.exportResult='no_render_dir';
    out.textContent=baseGap+' ⇒ 导出径取不到（fileName 须绝对）⇒ 导出中止 · ⛔ 字面兜底（承 pm_1385 §一）';
    addLog('⛔ 渲染目录取不到（GET /v9/pa/env 之 paths.render）⇒ 导出中止','warn',true);
    return;
  }
  const _last=base.slice(-1);
  const fbase=(_last==='/'||_last==='\\')?base:(base+'/');
  out.textContent='读取演示文稿信息…';
  let n=0, ok=0, fail=[];
  try{
    const info=await paMcp('wpp_get_presentation_info',{},30);
    const v=info.value||{};
    n=parseInt(v.slideCount,10)||0;
    out.textContent='演示文稿「'+(v.name||'?')+'」共 '+n+' 页，开始导出…';
    for(let i=1;i<=n;i++){
      const nn=String(i).padStart(2,'0');
      try{
        const r=await paMcp('wpp_export_slide_as_image',
          {slide:i,fileName:fbase+'v6_p'+nn+'.png',filterName:'PNG',width:1280,height:720},90);
        if(r.ok) ok++; else fail.push(i);
      }catch(e){ fail.push(i); }
      out.textContent='导出中 '+i+'/'+n+' … 成功 '+ok+'，失败 '+fail.length;
    }
    out.dataset.exportResult=ok+'/'+n;
    out.textContent='导出完成：成功 '+ok+'/'+n+(fail.length?('，失败页 '+fail.join(',')):'')+' → '+base+(baseSrc?('（源 '+baseSrc+'）'):'');
    card.querySelectorAll('.ppt-thumb img').forEach(function(im){
      const s=im.getAttribute('src').split('?')[0];
      im.setAttribute('src',s+'?t='+Date.now());
    });
    addLog('🖼 灵犀导出缩略图：成功 '+ok+'/'+n,'ok',true);
  }catch(e){
    out.dataset.exportResult='error';
    out.textContent='导出失败：'+e.message;
    addLog('🖼 灵犀导出失败：'+e.message,'warn',true);
  }
}

function receipt(text,cls){
  const r=$('tlReceipt'); if(!r) return;
  r.className='tl-receipt '+(cls||'ok'); r.style.display='block'; r.textContent=text;
  addLog('📋 '+text, cls==='ok'?'ok':'warn', true);
}
function _ensureLogToggle(){
  const t=$('thread'); if(!t||t.querySelector('.log-toggle')) return;
  const b=document.createElement('button'); b.className='log-toggle';
  const hid=t.classList.contains('hide-logs');
  b.textContent=hid?'▸ 执行过程（点击展开）':'▾ 执行过程（点击折叠）';
  b.onclick=()=>{ const h=t.classList.toggle('hide-logs'); b.textContent=h?'▸ 执行过程（点击展开）':'▾ 执行过程（点击折叠）'; };
  t.insertBefore(b, t.firstChild);
}
function paRunTid(){ return (paRun && paRun.threadId) || null; }
/* 批187 · 缺陷4：运行事件只写「发起线程」 */
function paRunLog(line, cls, store, title){ return addLog(line, cls, store, title, paRunTid()); }
/* pm_077 §一⒜：折叠键须由【同一公器】出（今日之病 ＝ 两处各拼串 ⇒ 必再分叉）。
   pm_077 §一⒞：键须含 `store` 之【分桶】—— 探针（`store === false`）自成一桶
   （⛔ 折上真交付之项 · ⛔ 顶其计数）；真交付（`true`）与【存量重渲染】（`undefined` ·
   `chat.js:52`）同桶（⇒ 存量照旧折上真项 · 承 pm_1132 §三.3 之界）。分桶判据唯此一处。 */
function paFoldKey(line, cls, store){ return 'log:' + line + '|' + (cls || '') + '|' + (store === false ? 'p' : 'r'); }
try{ window.paFoldKey = paFoldKey; }catch(e){}
/* pm_078 §二：探针行（`store === false`）须带【自测】之标轴 ⇒ 读者可辨
   （「自测之行 ≠ 真交付之行」· 承「弱保证 ≠ 真闸」之族 ⇒ ⛔ 以读者之猜补之）。
   同 `PA_LEDGER_AXIS` 之族形：正文追加 ＋ `data-axis` ＋ title（每入即重补 · 幂等）。
   ⚠ 追加文本须【前置空白】（否则 `paSelfMulPass` 之 `×N` 正则（`(?=\s|$)`）失配
   ⇒ 合并计数之擦【失灵】）。⛔ 入 `msgs`（其 `content` 取 `line` 原串 · ⛔ 取 DOM 文本）。 */
const PA_PROBE_TAG = '（自测 · ⛔ 真实交付）';
const PA_PROBE_TITLE = '我方自测之轮（⛔ 用户交付 · ⛔ 入 msgs）';
function paProbeTag(el, store){
  if(store !== false || !el) return;
  try{
    if(String(el.textContent || '').indexOf(PA_PROBE_TAG) < 0) el.appendChild(document.createTextNode(' ' + PA_PROBE_TAG));
    el.dataset.axis = 'probe';
    const t = String(el.title || '');
    if(t.indexOf(PA_PROBE_TITLE) < 0) el.title = (t ? (t + ' ｜ ') : '') + PA_PROBE_TITLE;
  }catch(e){}
}
function addLog(line, cls, store, title, tid){
  const t=$('thread');
  const th = tid ? (state.threads.find(function(x){return x.id===tid;}) || activeThread()) : activeThread();
  th.msgs=th.msgs||[];
  if (tid && th.id !== activeThread().id){ th.msgs.push({role:'tool', content:line, cls:cls||''}); saveState(); return; }
  _ensureLogToggle();
  // 2026-09-13: 同内容日志折叠成一条 + ×N（**不要求连续**）。
  // 实测一次讲义任务 38 条日志里绝大多数是「▶ 正在调研… / ✅ 查询知识库」**交替**重复 ——
  // 只折叠连续重复没用（相邻两行从来不相同），必须按内容归并。
  window.__logEls = window.__logEls || {};
  const _k = paFoldKey(line, cls, store);
  const _ent = window.__logEls[_k];
  if(_ent && _ent.el && t.contains(_ent.el)){
    _ent.n += 1; _ent.el.dataset.n = String(_ent.n);
    _ent.el.textContent = line + '   ×' + _ent.n;
    paProbeTag(_ent.el, store);
    t.appendChild(_ent.el);                      // 移到末尾：保持"最近发生"在下
    if(store){
      const lm = th.msgs.slice().reverse().find(m => m.role === 'tool' && m.__raw === line);
      if(lm){ lm.content = line + '   ×' + _ent.n; saveState(); }
      /* ⭐ pm_075 §一：折上**已有项**而 `msgs` 内**无同行**
         （前次系 `store=false` 之**探针**所建）⇒ 原实现**惟改既有项**
         ⇒ `lm` 缺 即**静默吞落**（无错 · 无痕 · 无回执）⇒ 与「凡用户
         可见之一轮 ⇒ 必有一行落盘」相抵（pm_1111 §一）。
         形与下主支同（content ⇐ line · __raw ⇐ line）⇒ 根因上补那一拼。 */
      else { th.msgs.push({role:'tool', content:line, cls:cls||'', __raw:line}); saveState(); }
    }
    t.scrollTop = t.scrollHeight; return;
  }
  const div=document.createElement('div'); div.className='tool-log '+(cls||''); div.textContent=line;
  div.dataset.raw=line; div.dataset.cls=cls||''; div.dataset.n='1';
  if(title) div.title=title;
  t.appendChild(div); t.scrollTop=t.scrollHeight;
  window.__logEls[_k] = {el: div, n: 1};
  paProbeTag(div, store);
  if(store){ th.msgs.push({role:'tool', content:line, cls:cls||'', __raw:line}); saveState(); }
}
