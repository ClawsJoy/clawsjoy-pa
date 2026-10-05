function setMode(m){
  const cfg = MODES[m];
  if(!cfg.on){ addMsg('sys', cfg.ic+' '+cfg.label+'：预留模式 —— 需接入 MCP Server / 流水线后启用（Blender、渲染农场等）。'); return; }
  state.mode = m; const t = activeThread(); t.mode = m; saveState();
  renderModes(); renderThread();
  $('modeTag').textContent = cfg.ic+' '+cfg.label;
  $('modeHint').textContent = cfg.hint;
  renderPermBadge();   /* PM-011 前置件：顶栏权限徽标改三态（⛔ 不再拿默认值当读数显示） */
  // 批171：通道**常显且醒目**（聊天=不出手／工作·开发=执行），并在聊天模式给出「一键切工作模式」
  const _mt = $('modelText');
  if(_mt){
    const _isPA = cfg.chan==='pa';
    _mt.textContent = _isPA ? '⛔ '+cfg.label+'（只商量 · 不出手）' : '✅ '+cfg.label+'（真执行 · '+cfg.perm+'）';
    _mt.className = 'chanbadge ' + (_isPA ? 'pa' : 'exec');
  }
  const _cs = $('chanSwitch');
  if(_cs){ _cs.style.display = (cfg.chan==='pa') ? 'inline-block' : 'none'; }
  const ph = { chat:'就事论事：目标 / 决策 / 口径 / 审美 / 在意的点…', work:'要办的活：文档、表格、浏览器、图文、演示…', dev:'要开发/修改/验证的代码或工程…' };
  $('input').placeholder = ph[m] || '描述你的目标…';
  if(cfg.chan==='pa'){ $('timeline').classList.remove('show'); stopPlanTimer(); }
}

/* ---- 线程 ---- */
function renderThreads(){
  /* 批192 · 缺陷修（批189 #1 的回归）：单线程化已删除 #threadList 元素，而本函数仍在往它写 innerHTML
     ⇒ 这里抛 TypeError，且因为发生在 **async 启动 IIFE** 里 = 未处理的 promise rejection
     ⇒ 页内 window error 监听**看不到**（这点让批191 的我误判成「插桩噪声」），
     而它**静默中断了整个启动**：其后的 setMode() 不执行（中栏空白，点模式按钮才渲染）、
     loadSide()/loadFiles() 不执行（左右栏停在静态占位，要手动点 ↻ 才出来）。
     修法：元素不存在即 return（单线程 = 无线程列表）；函数名保留，防别处调用报错。 */
  const _tl = $('threadList');
  if(!_tl) return;
  _tl.innerHTML = state.threads.map(t=>{
    const act = t.id===state.activeThread ? ' active' : '';
    return '<div class="th'+act+'" data-id="'+t.id+'"><span class="m">'+(MODES[t.mode]||MODES.chat).ic+'</span>'+
      '<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+esc(t.title)+'</span></div>';
  }).join('') || '<div class="fitem">（无线程）</div>';
  _tl.querySelectorAll('.th').forEach(el=>el.addEventListener('click',()=>{
    /* 批122 A：切线程后面板要跟着切沙箱（否则面板停在旧线程的沙箱，直到手动点 ↻）*/
    state.activeThread = el.dataset.id; saveState(); syncPaSession(); renderThreads(); renderThread(); setMode(activeThread().mode); renderTimeline(); loadFiles();
    /* 批187 · 缺陷4：切到别的线程时明示「谁在跑」，并保留停止按钮可用 */
    if (paRun.busy && paRun.threadId && paRun.threadId !== activeThread().id){
      const _rt=(state.threads.find(function(x){return x.id===paRun.threadId;})||{}).title||paRun.threadId;
      addMsg('sys','⏳ 线程「'+esc(_rt)+'」仍在执行（进度只显示在它自己的线程里）—— 可切回查看，或点「停止」取消它');
      setBusy(true);
    }
  }));
}
function renderThread(){
  const t = activeThread(); $('thread').innerHTML='';
  (t.msgs||[]).forEach(m=>{
    if(m.role==='tool'){ addLog(m.content, m.cls); }
    else addMsg(m.role==='user'?'user':'assistant', m.content, true, m.html);   // 批173：折叠块随历史重渲染
  });
  /* 批201 · F5 修复：交付卡片（.output-card / pptx 墙）此前**只插 DOM、不入 msgs** ⇒ 刷新后丢。
     这里从**已持久化的助手正文**重新探测产物路径并重渲染（正文本身就是持久化的事实来源，无需新字段）。
     renderOutputCard 内部做了去重（同 path 只留一张），因此重复调用 renderThread 不会堆积。*/
  try{
    (t.msgs||[]).forEach(function(m){
      if(m.role!=='tool' && m.role!=='user' && m.content){ detectOutputs(m.content).forEach(renderOutputCard); }
    });
  }catch(e){}
  $('thread').scrollTop = $('thread').scrollHeight;
}

/* ---- 消息 ---- */
/* 批173 · 第2条拍板 ③：错误折叠块（纯函数，便于 node 单测） */
function paErrBlockHtml(meta, errText){
  const m=String(meta==null?'':meta), e=String(errText==null?'未知错误':errText);
  const rid=(m.match(/run_id=([^\s·）]+)/)||[])[1]||'';
  return '<details class="errfold"><summary>⛔ 执行中断'+esc(m)+'</summary><div class="errbody">'
    +'<pre>'+esc(e)+'</pre>'
    +(rid?('<button class="errcopy" onclick="paCopyText(\''+rid+'\')">复制 run_id</button>'):'<span style="font-size:11px;color:#8b949e">（本次错误未带 run_id）</span>')
    +'</div></details>';
}
function paCopyText(t){ try{ if(navigator.clipboard) navigator.clipboard.writeText(String(t)); }catch(e){} }
function addMsg(role, content, skipStore, html, tid){
  const t = $('thread');
  if (tid && tid !== activeThread().id){
    const _th = state.threads.find(function(x){return x.id===tid;});
    if (_th){ (_th.msgs = _th.msgs || []).push(html ? {role:role, content:content, html:html} : {role:role, content:content}); saveState(); }
    return null;   /* 非当前线程：只写它自己的历史，不污染当前视图 */
  }
  const div=document.createElement('div');
  if(role==='sys'){
    div.style.cssText='align-self:center;max-width:96%';
    div.innerHTML='<div class="bubble" style="font-size:11.5px;color:var(--sub);text-align:center;border-color:transparent;background:transparent">'+esc(content)+'</div>';
  } else {
    div.className='msg '+(role==='user'?'user':'');
    // 批173：带 html 的消息（错误折叠块）直接注入；否则按文本转义
    // 批176 · A1'：assistant 消息里出现知识库素材路径时渲染为可折叠胶囊（纯函数；无路径时行为不变）
    const _kbPaths = (role==='assistant' && !html) ? paKbExtractPaths(content) : [];
    if(_kbPaths.length && !paKbCache) paKbLoad(false);
    const _body = html ? html : (_kbPaths.length ? paKbCapsuleHtml(content, (paKbCache||{}).rows) : esc(content));  /* pm_1096 §二.1（老板批 P9）：答体 ⛔ 走 MD 渲染（承 批187 之反）—— paMdToHtml 会吃 * 等字；.bubble 已 white-space:pre-wrap ⇒ 换行不丢 */
    div.innerHTML='<div class="av">'+(role==='user'?'👤':'🤖')+'</div><div><div class="meta">'+
      (role==='user'?'你':'PA · '+(MODES[state.mode]||MODES.chat).label)+'</div><div class="bubble">'+_body+'</div></div>';
  }
  div.querySelectorAll('.mdcopy').forEach(function(b){ b.addEventListener('click', function(){ const pre=b.parentElement.nextElementSibling; const txt=pre?pre.textContent:''; try{ navigator.clipboard.writeText(txt); b.textContent='✅ 已复制'; setTimeout(function(){b.textContent='⧉ 复制';},1200);}catch(e){} }); });
  t.appendChild(div); t.scrollTop=t.scrollHeight;
  if(!skipStore && role!=='sys'){ const th=(tid ? (state.threads.find(function(x){return x.id===tid;}) || activeThread()) : activeThread()); th.msgs=th.msgs||[]; th.msgs.push(html ? {role, content, html} : {role, content});
    if(role==='user' && th.title==='新线程'){ th.title=String(content).slice(0,18); renderThreads(); }
    saveState(); }
  return div;
}
/* 语义阶段映射: 工具名 → 老板能懂的阶段(①语义步骤流) */
const STAGE_MAP={
  obsidian_knowledge:'调研',web_search:'调研',fetch_web:'调研',browse_web:'调研',query_index:'调研',table_extract:'调研',
  read_file:'读资料',list_dir:'读资料',search_files:'读资料',
  write_file:'写稿',wps_office:'出稿',
  pa_audit:'评审',
  lingxi:'出图/排版',
  execute_command:'执行',
  browser_local:'浏览器操作',playwright_browser:'浏览器操作',browser_hybrid:'浏览器操作'
};
function stageOf(tool){ return STAGE_MAP[tool]||'执行'; }
/* 子级动作语义映射(2026-09-11): 工具名→语义短语, 老板能懂(裸命令放 title hover 可查) */
const ACTION_SEMANTIC={
  obsidian_knowledge:'查询知识库', web_search:'搜索网络', fetch_web:'抓取网页', browse_web:'浏览网页', query_index:'查询索引', table_extract:'提取表格',
  read_file:'读取文件', list_dir:'查看目录', search_files:'搜索文件',
  write_file:'写入文件', wps_office:'处理文档',
  pa_audit:'评审校验',
  lingxi:'灵犀排版',
  execute_command:'执行操作',
  browser_local:'操作浏览器', playwright_browser:'操作浏览器', browser_hybrid:'操作浏览器',
  // 2026-09-13 补：未映射的工具会直接显示**裸工具名**（老板看到的就是裸命令感）
  lingxi_local_api:'灵犀接口', ds_chat:'通用网页对话', cu_learning:'学习操作',
  // pm_1125 §一.2：ds_chat 之显名去平台色彩（原带他方平台身份词）；内部键留（⛔ 改名以免断映射）· ⛔ 本名不得入「可代操作」文案
  wpp_render_full_deck:'渲染演示文稿', wpp_export_slide_as_image:'导出页面图片',
  wpp_slide_count:'核对页数', code_entity_extractor:'解析代码',
  run_command:'执行操作', shell:'执行操作', edit_file:'修改文件', write_large:'写入文件'
};
function semanticArg(tool, arg){
  const a=String(arg||'').toLowerCase();
  if(tool==='execute_command'){
    if(a.includes('awk')||a.includes('cat ')||a.includes('head ')||a.includes('tail ')||a.includes('grep')) return '读取文件内容';
    if(a.includes('ls ')||a.includes('wc ')||a.includes('find ')||a.includes('du ')) return '检查文件';
    if(a.includes('cp ')||a.includes('mv ')||a.includes('rm ')||a.includes('mkdir')) return '整理文件';
    if(a.includes('python')||a.includes('node ')) return '运行脚本';
    if(a.includes('cd ')) return '切换目录';
    // 2026-09-13 补：实测出现过的命令族，避免落到通用兜底
    if(a.includes('sed ')||a.includes('tee ')||a.includes('tr ')) return '编辑文本';
    if(a.includes('curl ')||a.includes('wget ')) return '取回数据';
    if(a.includes('jq ')||a.includes('sort ')||a.includes('uniq ')) return '整理数据';
    if(a.includes('git ')) return '版本操作';
    if(a.includes('pytest')||a.includes('compileall')) return '运行测试';
  }
  return null;
}

/* ===== 批78 选项a：带上下文的语义阶段（纯函数，可脱离浏览器验）=====
   ctx 四源中本批用前三源：工具入参 arg / 计划步骤 / 会话已知产物。
   铁律：**取不到上下文一律 return null**，由调用点的原有三级兜底回落固定短语 —— 绝不返回空串或抛错。 */
function semanticStage(tool, arg, ctx){
  try{
    ctx = ctx || {};
    const a = String(arg||'');
    const short = function(x, n){ x = String(x||''); return x.length > (n||24) ? x.slice(0, (n||24)) + '…' : x; };
    const step = (ctx.stepIndex && ctx.stepTotal) ? ('第 ' + ctx.stepIndex + '/' + ctx.stepTotal + ' 步') : (ctx.stepIndex ? ('第 ' + ctx.stepIndex + ' 步') : '');
    const join = function(core){ return step ? (step + '：' + core) : core; };

    // ① 稿件渲染/导出类：带页码 + 页标题（会话产物源）
    const pageNo = (function(){ const m = /(?:^|\D)(\d{1,3})(?:\D|$)/.exec(a.replace(/\.(pptx|png|jpg)/gi,'')); return m ? m[1] : ''; })();
    const title = ctx.pageTitle ? short(ctx.pageTitle, 16) : '';
    const pageStr = pageNo ? ('第 ' + pageNo + ' 页' + (title ? ('：' + title) : '')) : (title || '');
    if(/render|export|thumb|slide/i.test(tool)){
      const verb = /delete/i.test(tool) ? '删除' : (/export|thumb/i.test(tool) ? '导出' : '渲染');
      if(pageStr) return join(verb + pageStr);
      if(ctx.deck) return join(verb + ' ' + short(ctx.deck, 20));
      return null;
    }
    // ② 文件类：带文件名
    if(/read_file|write_file|edit_file|list_dir|search_files/.test(tool)){
      const m = /([^\/\s]+\.(md|txt|json|py|html|js|pptx|png|yaml|yml))/.exec(a);
      const f = m ? short(m[1], 28) : '';
      const verb = /write_file|edit_file/.test(tool) ? '写入' : (/list_dir/.test(tool) ? '查看目录' : (/search_files/.test(tool) ? '搜索' : '读取'));
      if(f) return join(verb + ' ' + f);
      // 批85 断点②修：目录类 arg（无扩展名，如 list_dir 的 data/reports）此前必然回落。
      // 补一条分支：arg 里没有可识别文件名时，退而用「路径原文」做语义（不写死路径，直接引用 arg）。
      const _p = /([^\s"'<>|;]{2,80})/.exec(a);
      if(_p){ const _pp = short(_p[1], 28); if(_pp) return join(verb + ' ' + _pp); }
      return null;
    }
    // ③ 网络/检索类：带关键词
    if(/web_search|fetch_web|browse_web/.test(tool)){
      const m = /["']([^"']{2,40})["']/.exec(a);
      const kw = m ? short(m[1], 20) : '';
      if(kw) return join('搜索「' + kw + '」');
      return null;
    }
    // ④ 命令类：沿用既有命令族分流，只额外叠加「第几步」
    if(tool === 'execute_command'){
      const base = semanticArg(tool, arg);
      return base ? join(base) : null;
    }
    // ⑤ 其余工具：能拿到步数就带步数，否则回落
    if(step) return step + '：' + (ACTION_SEMANTIC[tool] || '执行操作');
    return null;
  }catch(e){ return null; }   // 纯函数：任何异常都回落，不抛
}

/* ctx 采集：任何一项取不到就留空（不抛错、不阻塞） */
function semanticCtx(tool, arg){
  const c = {};
  try{ if(typeof _planStepIndex !== 'undefined' && _planStepIndex){ c.stepIndex = _planStepIndex; } }catch(e){}
  try{ if(typeof _planStepTotal !== 'undefined' && _planStepTotal){ c.stepTotal = _planStepTotal; } }catch(e){}
  try{ if(typeof PPT_DECK !== 'undefined' && PPT_DECK){ c.deck = PPT_DECK; } }catch(e){}
  try{
    const m = _pptManifestCache && Object.keys(_pptManifestCache)[0];
    if(m){ const man = _pptManifestCache[m]; if(man && man.deck){ c.deck = c.deck || man.deck; }
      /* 批80：按工具入参里的 page_index 去 manifest.pages[] 查 title（缺失/无匹配一律降级，不抛）*/
      if(man && Array.isArray(man.pages)){
        const _mm = /"page_index"\s*:\s*(\d{1,3})/.exec(String(arg||'')) || /\bpage\D{0,4}(\d{1,3})\b/.exec(String(arg||''));
        const _pn = _mm ? parseInt(_mm[1],10) : 0;
        if(_pn){ const _hit = man.pages.find(function(x){ return Number(x.page_index) === _pn; });
          if(_hit && _hit.title){ c.pageTitle = String(_hit.title); } }
      }
    }
  }catch(e){}
  return c;
}

/* ---- ①③ 时间轴 + 拍板 ---- */
const BUCKET_MAP = {
  obsidian_knowledge:'调研',web_search:'调研',fetch_web:'调研',browse_web:'调研',query_index:'调研',table_extract:'调研',
  read_file:'调研',list_dir:'调研',search_files:'调研',
  write_file:'写稿',wps_office:'写稿',
  pa_audit:'评审',
  lingxi:'出图/排版',
  execute_command:'执行',
  browser_local:'执行',playwright_browser:'执行',browser_hybrid:'执行'
};
function bucketOf(tool){ return BUCKET_MAP[tool]||'执行'; }

let planTimer = null, boardTarget = null, pendingDecision = null;
function planOf(t){ if(!t.plan) t.plan = {task:'', steps:[], startedAt:null}; return t.plan; }
function boardNode(){ const pl=planOf(activeThread()); return pl.steps.find(s=>s.id===boardTarget)||null; }
function fmtElapsed(ms){ const s=Math.max(0,Math.floor((ms||0)/1000)); const m=Math.floor(s/60); return m+':'+String(s%60).padStart(2,'0'); }
/* 2026-09-13「回执即判据」：节点 done 必须有回执，不是跑过就算完成。
   实测事故：3 个节点永远 future、而**根本没做**的「交付」却打了勾（0:00）。
   判据：① 有 produces 的节点 —— 必须出现写类工具的成功回执，否则标「未核验」(琥珀)，不打勾；
        ② 无 produces 的节点 —— 有任一成功动作回执即可打勾；
        ③ 一条回执都没有 —— 一律「未核验」，绝不打勾。
   注：真正的产物存在性核验必须由后端 verifier 算（见 Codex 移植 P0 表）；前端这一版只负责**不再说谎**。 */
const WRITE_TOOLS = new Set(['write_file','write_large','edit_file','execute_command','obsidian_knowledge']);
function finalizeNode(s){
  if(s.status==='done'||s.status==='unverified') return;
  const ev=(s.evidence||[]);
  const okEv=ev.filter(e=>e.ok);
  s.status = (okEv.length && (!s.produces || okEv.some(e=>e.writes))) ? 'done' : 'unverified';
  if(s.startedAt){ s.elapsed=(s.elapsed||0)+(Date.now()-s.startedAt); s.startedAt=null; }
}
function nodeEvidenceLine(s){
  if(s.status!=='unverified') return '';
  const why = !(s.evidence||[]).length ? '无执行回执'
            : (s.produces ? '无产物回执（产出 '+s.produces+' 未见写入）' : '无可信回执');
  return '<div class="tl-verify">⚠ 未核验：'+esc(why)+'</div>';
}

async function startPlan(task){
  const t=activeThread();
  let steps=[];
  try{
    const r=await fetch(API+'/v9/pa/plan',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({user_id:curUser(),session_id:t.id,task:task,mode:state.mode})});
    if(r.ok){ const d=await r.json(); if(d.ok&&Array.isArray(d.steps)&&d.steps.length){
      const _seen=new Set(); const raw=d.steps.filter(s=>{ if(_seen.has(s.stage)) return false; _seen.add(s.stage); return true; });
      // 2026-09-13: 接后端 plan 的 produces/verify/owner（decision.py 五元组）
      // —— 此前只用 stage/label，老板看不到「谁干、产出什么、怎么算完成」。
      steps=raw.map((s,i)=>({id:'n'+i,stage:s.stage,label:s.label,
        produces:s.produces||'', verify:s.verify||'', owner:s.owner||'',
        status:'future',actions:[],startedAt:null,elapsed:0,decision:null})); } }
  }catch(e){}
  if(!steps.length){ steps=['调研','写稿','出图/排版','评审','交付'].map((s,i)=>({id:'n'+i,stage:s,label:s,status:'future',actions:[],startedAt:null,elapsed:0,decision:null})); }
  if(steps.length && steps[steps.length-1].stage!=='交付'){ steps.push({id:'n'+steps.length,stage:'交付',label:'交付产物',status:'future',actions:[],startedAt:null,elapsed:0,decision:null}); }
  const pl=planOf(t); pl.task=task; pl.steps=steps; pl.startedAt=Date.now();
  saveState(); renderTimeline(); startPlanTimer();
  return steps;
}

function renderTimeline(){
  const tl=$('timeline'); if(!tl) return;
  const t=activeThread(); const pl=planOf(t);
  if(!pl.steps||!pl.steps.length||(MODES[state.mode]||MODES.chat).chan!=='agent'){ tl.classList.remove('show'); return; }
  tl.classList.add('show');
  if(pl.startedAt) $('tlElapsed').textContent='已耗时 '+fmtElapsed(Date.now()-pl.startedAt);
  $('tlTask').textContent=pl.task||'';
  $('tlNodes').innerHTML=pl.steps.map(s=>{
    const dot=s.rolled?'↩':(s.status==='done'?'✓':(s.status==='unverified'?'!':(s.status==='current'?'●':'○')));
    const cls=s.rolled?'rolled':s.status;
    const acts=(s.actions||[]).slice(-3).map(a=>'<div class="'+(a.ok?'ok':'err')+'">'+(a.ok?'✓':'✗')+' '+esc(a.tool)+' '+esc(String(a.arg||'').slice(0,26))+'</div>').join('');
    const dec=s.decision?'<div class="tl-dec">已拍板:'+esc(s.decision)+'</div>':'';
    return '<div class="tl-node '+cls+'" data-id="'+s.id+'">'+
      '<div class="tl-top"><span class="tl-dot">'+dot+'</span><span class="tl-stage">'+esc(s.stage)+'</span></div>'+
      '<div class="tl-label">'+esc(s.label)+'</div>'+
      '<div class="tl-time">'+fmtElapsed(s.elapsed||0)+(s.status==='current'?' ·进行中':'')+'</div>'+
      _metaLine(s)+nodeEvidenceLine(s)+
      (acts?'<div class="tl-actions">'+acts+'</div>':'')+dec+'</div>';
  }).join('');
  $('tlNodes').querySelectorAll('.tl-node').forEach(el=>el.addEventListener('click',()=>openBoard(el.dataset.id)));
}

function _metaLine(s){
  const bits=[];
  if(s.produces) bits.push('<b>产出</b> '+esc(s.produces));
  if(s.verify) bits.push('<b>验收</b> '+esc(s.verify));
  if(s.owner) bits.push('<b>承接</b> '+esc(s.owner));
  return bits.length?'<div class="tl-meta">'+bits.join('<br>')+'</div>':'';
}
function startPlanTimer(){ stopPlanTimer(); planTimer=setInterval(()=>{ const pl=planOf(activeThread()); if(pl.startedAt){ const e=$('tlElapsed'); if(e) e.textContent='已耗时 '+fmtElapsed(Date.now()-pl.startedAt); } },1000); }
function stopPlanTimer(){ if(planTimer){ clearInterval(planTimer); planTimer=null; } }

function tickPlan(tool,arg,ok){
  const t=activeThread(); const pl=planOf(t);
  if(!pl.steps||!pl.steps.length) return;
  const bucket=bucketOf(tool);
  try{ _planStepTotal = pl.steps.length; }catch(e){}
  let node=pl.steps.find(s=>s.stage===bucket);
  if(!node){ node=pl.steps.find(s=>s.stage==='未分类'); if(!node){ node={id:'n'+pl.steps.length, stage:'未分类', label:'其他动作', status:'future', actions:[], startedAt:null, elapsed:0, decision:null}; const li=pl.steps.length-1; if(li>=0 && pl.steps[li].stage==='交付'){ pl.steps.splice(li,0,node); } else { pl.steps.push(node); } } }
  try{ const _ix = pl.steps.indexOf(node); if(_ix >= 0){ _planStepIndex = _ix + 1; } }catch(e){}
  pl.steps.forEach(s=>{ if(s.status==='current'&&s!==node) finalizeNode(s); });
  if(node.status==='future'||node.rolled){ node.status='current'; node.rolled=false; if(!node.startedAt) node.startedAt=Date.now(); }
  (node.actions=node.actions||[]).push({tool:tool,arg:arg,ok:ok});
  (node.evidence=node.evidence||[]).push({tool:tool,arg:arg,ok:ok,writes:WRITE_TOOLS.has(tool)});
  if(ok && WRITE_TOOLS.has(tool)) pl.has_write=true;      // 任务级：是否出现过写类回执
  renderTimeline();
}

function _renderVerifyLine(){
  if(!lastVerify) return;
  const v=lastVerify.verdict;
  const map={PASS:['✅ 核验通过','ok'], FAIL:['⚠ 核验未通过','err'],
             NOT_APPLICABLE:['◻ 本次无需核验（纯问答/只读/免闸类型）','stage']};
  const hit=map[v]||['◻ 核验未执行','warn'];
  const extra=(v==='FAIL'&&lastVerify.failures&&lastVerify.failures.length)?('：'+lastVerify.failures[0]):'';
  addLog(hit[0]+extra, hit[1], true, 'verify_verdict='+v);
  receipt(hit[0], v==='FAIL'?'err':'ok');
}
function onTaskDone(){
  const t=activeThread(); const pl=planOf(t);
  if(pl.steps&&pl.steps.length){
    pl.steps.forEach(s=>{ if(s.status==='current'||s.status==='future') finalizeNode(s); });
    renderTimeline();
    // 交付节点：只有本任务真的出现过写类回执才打勾；否则如实标「未核验」并给一句人话
    const last=pl.steps[pl.steps.length-1];
    // verify_verdict 可视化 + 交付节点与核验结论对齐（FAIL 一律不打勾）
    _renderVerifyLine();
    if(lastVerify && lastVerify.verdict==='FAIL' && last) last.status='unverified';
    if(last && last.status==='unverified'){
      receipt(pl.has_write
        ? '交付未经核验：有写入动作，但没有产物核验证据（后端 verifier 待接）'
        : '本次执行没有检测到任何写类产物 —— 交付未经核验', 'err');
    } else if(pl.has_write){
      receipt('交付动作已完成（产物核验由后端 verifier 判定）', 'ok');
    }
  }
  stopPlanTimer();
  const lastDone=pl.steps.slice().reverse().find(s=>s.status==='done');
  if(lastDone) openBoard(lastDone.id);
}

function openBoard(nodeId){
  const pl=planOf(activeThread()); const node=pl.steps.find(s=>s.id===nodeId); if(!node) return;
  boardTarget=nodeId;
  $('tlBoardStage').textContent=node.stage+' · '+node.label;
  $('tlBoard').style.display='flex';
}

function paDecide(decision){
  const node=boardNode(); if(!node) return;
  pendingDecision=decision;
  const noteBox=$('tlNote');
  if(decision==='小改'){ $('tlNoteInput').value=''; $('tlNoteInput').placeholder='改什么？(小改必填)'; noteBox.style.display='flex'; }
  else if(decision==='退回'){ $('tlNoteInput').value=''; $('tlNoteInput').placeholder='退回：重做本步 / 换思路重做（选一个或写原因）'; noteBox.style.display='flex'; }
  else if(decision==='大改'){ $('tlNoteInput').value=''; $('tlNoteInput').placeholder='大改方向（可选）'; noteBox.style.display='flex'; }
  else { noteBox.style.display='none'; confirmDecision(decision,''); }
}
function paDecideConfirm(){
  const note=$('tlNoteInput').value.trim();
  if(pendingDecision==='小改'&&!note){ receipt('⚠ 小改必须填「改什么」，不填不提交。','rev'); return; }
  $('tlNote').style.display='none';
  confirmDecision(pendingDecision,note);
}
function paDecideCancel(){ $('tlNote').style.display='none'; pendingDecision=null; }

async function confirmDecision(decision,note){
  const t=activeThread(); const pl=planOf(t); const node=boardNode(); if(!node) return;
  try{
    await fetch(API+'/v9/pa/decision',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({user_id:curUser(),session_id:t.id,node:node.id,stage:node.stage,decision:decision,note:note,task:pl.task})});
  }catch(e){}
  node.decision=decision;
  if(decision==='采纳'){ node.status='done'; finalizeNode(node); receipt('✅ 已采纳「'+node.stage+' · '+node.label+'」—— 已记录 decision_log，交付。','ok'); }
  else if(decision==='暂缓'){ receipt('⏸ 已暂缓「'+node.stage+'」—— 已挂起，等老板后续指示。','rev'); }
  else {
    node.status='current'; node.rolled=true;
    const ni=pl.steps.indexOf(node);
    pl.steps.forEach((s,si)=>{ if(si>ni){ s.status='future'; s.decision=null; } });
    receipt('↩ 已'+decision+'「'+node.stage+(note?'：'+note:'')+'」—— 已通知 PA 修改。','rev');
    sendReviseToPA(decision,note,node);
  }
  pendingDecision=null;
  renderTimeline();
  $('tlBoard').style.display='none';
}

function sendReviseToPA(decision,note,node){
  const t=activeThread();
  const act={小改:'老板拍板小改，只改指定点，其余不动。',大改:'老板拍板大改，较大范围调整后重新执行。',退回:'老板拍板退回，本步重新执行。'}[decision]||'老板要求修改。';
  const text='老板拍板：'+act+(note?(' 老板原话：'+note):'')+' —— 针对步骤「'+node.stage+'·'+node.label+'」。请修改后重新交付。';
  addMsg('user','[修改指令] '+text);
  setBusy(true);
  sendAgent(t, text).finally(()=>setBusy(false));
}
