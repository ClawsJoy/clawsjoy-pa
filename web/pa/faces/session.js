
async function loadThreads(){
  /* 批199 · 缺陷修（批189 #3 的回归）：以前这里 `state = d` 用**后端副本整体覆盖本地**；而批189 #3 把
     syncThreads() 改成 no-op（POST /v9/pa/threads 已 410）⇒ 后端副本**永远停在旧快照** ⇒ 刷新后「新消息丢、
     旧消息还在」。**批219 契约迁移（老板 2026-09-16 拍板 A）**：该「同 id 比条数」写法已作废，见下方 A 口径实现。*/
  let _remote=null, _local=null;
  try{ const r=await fetch(API+'/v9/pa/threads?user_id='+encodeURIComponent(curUser()));
       if(r.ok){ const d=await r.json(); if(d && Array.isArray(d.threads) && d.threads.length){ _remote=d; } } }catch(e){}
  let _degraded=null;
  try{
    const _raw=localStorage.getItem('pa_state');
    const _lp=paParseStateTolerant(_raw);
    if(_lp.ok && _lp.data && Array.isArray(_lp.data.threads) && _lp.data.threads.length){ _local=_lp.data; if(_lp.salvaged){ console.warn('[PA] 本地记录已损坏，抢救出第一段（丢弃 '+_lp.dropped+' 字符）'); } }
    else if(_raw && !_lp.ok){ _degraded=_lp.reason||'解析失败'; }
  }catch(e){ _degraded='读取本地记录异常：'+String(e).slice(0,60); }
  /* 批219 修：**本地优先、后端只补历史**（旧逻辑以后端旧快照为骨架 ⇒ 本地那份一旦缺失就整页回退旧快照）。 */
  if(_degraded){
    /* 批221 · DS-206-5/6：解析失败 ⇒ 降级：**清空 #thread**（防旧 DOM 残留造成"假正常 UI"）＋**可见提示**；
       **绝不 fallback 后端老线程**。断言见 tools/pa_degraded_e2e.py（坏状态不得产生假正常 UI）。 */
    /* 批221 修③（E2E 三次抓到）：#thread 与 #modeHint 都会被启动后续流程重画/改写
       ⇒ 走**正规渲染路径**：造一个**只含警示消息**的降级线程，让 renderThread 自己画（无旧内容 ⇒ 无"假正常"）。 */
    state = { threads: [{ id:'pa_degraded', title:'⚠ 降级模式', mode:(state&&state.mode)||undefined,
                          msgs:[{ role:'sys', content:'⚠ 本地会话记录损坏，已进入降级模式：未加载任何历史（避免显示假正常内容）。原因：'+_degraded+'；建议导出 pa_state 后清理。' }] }],
              activeThread:'pa_degraded', mode:(state&&state.mode)||undefined, _degraded:_degraded };
    /* 批221 修（反例 E2E 抓到）：降级时 activeThread=null ⇒ addMsg 会抛错并被吞掉 ⇒ **静默降级**。
       ⇒ 降级提示**直接写 DOM**（不依赖 addMsg / 不依赖任何线程存在）。 */
    /* 批221 修②（E2E 二次抓到）：写 #thread 会被启动后续的 renderThread 重画覆盖
       ⇒ 提示改写到**不会被重画的持久元素 #modeHint**（外加 console）。 */
    try{
      const hint=document.getElementById('modeHint');
      if(hint){ hint.textContent='⚠ 本地会话记录损坏：已进入降级模式（未加载任何历史）。原因：'+_degraded+'；建议导出 pa_state 后清理。'; }
      const el=document.getElementById('thread');
      if(el){ el.setAttribute('data-degraded', '1'); }
    }catch(_e){}
    console.warn('[PA][DEGRADED] 会话读取降级：'+_degraded);
    return;
  }
  if(_local){
    state = _local;
    if(_remote){
      const _add=(_remote.threads||[]).filter(function(rt){ return !(state.threads||[]).some(function(x){ return x.id===rt.id; }); });
      if(_add.length){ state.threads=(state.threads||[]).concat(_add); state._remoteFilled=_add.length; }
    }
    if(!(state.threads||[]).some(function(x){ return x.id===state.activeThread; })){
      const _old=state.activeThread; state.activeThread=(state.threads[0]||{}).id;
      try{ addMsg('sys','⚠ 上次的活动线程（'+_old+'）不在本地记录中，已切回最近线程；旧内容可在后端历史查看。'); }catch(_){}
    }
  } else if(_remote){
    state=_remote;
    if(!(state.threads||[]).some(function(x){ return x.id===state.activeThread; })){ state.activeThread=(state.threads[0]||{}).id; }
    try{ addMsg('sys','⚠ 本地会话记录为空（未落盘或被清理），已载入后端历史快照（只读）。'); }catch(_){}
  }
}
/* PM-011 · N9（CEO 裁 (a)：本机即信任域）：PA 前端的"我是谁"此前**没有任何生产者** ——
   curUser() 的三条回落里，前两条恒假（pa.html 不写 __APP_STATE.userId；启动时 syncPaSession()
   造出的那个 __APP_STATE 只有 sessionId 一个键），第三条写死老板 id
   => **没有 localStorage 的浏览器一打开 PA 就以老板主体发请求**（改权限档 / /mcp/call / skip_quota 文件操作）。
   现在身份收敛到**一个生产者**：与 workbench 同一把钥匙（localStorage.clawsjoy_user_id）、
   同一形制（web_<Date.now()>），并把同一个值**同时**写进内存（__APP_STATE.userId）与落盘
   => 内存 <-> 落盘恒等（不许分叉）。
   不回落老板 id；任何 panic 态也不回落"别人" —— 造不出可落盘身份时，本会话仍持一个
   **显式可见**的临时身份（#uidText 渲染的就是它），不静默变成 default 主体。*/
function ensureUserId(){
  var _uid = '';
  try{ _uid = (window.__APP_STATE && window.__APP_STATE.userId) || localStorage.getItem('clawsjoy_user_id') || ''; }catch(e){ _uid = ''; }
  if(!_uid){
    _uid = 'web_' + Date.now();
    try{ localStorage.setItem('clawsjoy_user_id', _uid); }catch(e){}
  }
  try{ window.__APP_STATE = window.__APP_STATE || {}; window.__APP_STATE.userId = _uid; }catch(e){}
  return _uid;
}
function curUser(){ return ensureUserId(); }
/* 批122 A：pa 页自己就是会话所有者 —— 面板与聊天必须看同一个沙箱。
   聊天用 activeThread().id 发 /v9/agent/chat；这里把同一个值同步进 __APP_STATE.sessionId，
   curSession() 优先读它 ⇒ 面板 sid === 聊天 sid。
   **刻意不再回落 localStorage.clawsjoy_session_id**：那个键是 workbench 页写进同源 localStorage 的，
   正是"pa 面板显示的是 workbench 沙箱"的污染源（批121 实测）。*/
function syncPaSession(){ try{ window.__APP_STATE = window.__APP_STATE || {}; window.__APP_STATE.sessionId = activeThread().id; }catch(e){} return curSession(); }
function curSession(){ try{ return (window.__APP_STATE&&window.__APP_STATE.sessionId) || (state&&state.activeThread) || 'default'; }catch(e){ return 'default'; } }
function esc(s){ const d=document.createElement('div'); d.textContent=String(s==null?'':s); return d.innerHTML; }
/* ===== 批183 · C3/C1：WPS 灵犀未就绪的降级与引导（纯函数块 BEGIN；node 单测按标记抽取，勿依赖 DOM）===== */
const PA_WPS_STEPS = ['打开 WPS（文字/演示任一）', '点右下角「灵犀」面板', '在面板里开启 MCP（桥）', '回到这里点「重试」'];
function paIsPreviewPending(step){ return !!(step && step.reason==='preview_pending'); }
function paWpsReadyCardHtml(hint, artifact, state){
  const _h = String(hint || 'WPS 灵犀面板（TaskPane）未开或未登录 —— PA 无法自动开启（WPS 插件硬边界）');
  const _steps = PA_WPS_STEPS.map(function(s,i){ return '<li>'+(i+1)+'. '+esc(s)+'</li>'; }).join('');
  const _copy = 'WPS 灵犀就绪操作：' + PA_WPS_STEPS.map(function(s,i){ return (i+1)+'. '+s; }).join('；');
  const _art = artifact ? ('<div class="wpsart">产物：'+esc(String(artifact))+'</div>') : '<div class="wpsart wpsnone">本次未取到产物路径（不假报「已生成」；产物也可能在 WPS 侧）</div>';
  return '<div class="wpscard"><div class="wpshead">⏳ 预览待 WPS 就绪 —— 这不是任务失败</div>'
    + '<div class="wpshint">'+esc(_h)+'</div>'
    + '<div class="wpsstate">'+esc(paWpsStateLine(state))+'</div>'
    + '<ul class="wpssteps">'+_steps+'</ul>'+_art
    + '<button class="wpscopy" data-act="copy" data-copy="'+esc(_copy)+'">⧉ 复制操作步骤</button>'
    + '</div>';
}
function paPreviewPendingVisual(step){
  const _st = step || {};
  // 批183（修正版）· 五字段语义分层：artifact 现为 {exists, path}
  const _a = (_st.artifact && typeof _st.artifact === 'object') ? _st.artifact : {exists: false, path: null};
  const _art = (_a.exists && _a.path) ? String(_a.path) : '';
  const _task = String(_st.task_status || (_art ? 'PARTIAL' : 'BLOCKED'));
  const _prev = String((_st.preview && _st.preview.status) || 'PENDING');
  const _comp = String((_st.completion && _st.completion.status) || 'NOT_COMPLETE');
  return {
    degraded: true, icon: '⏳', cls: 'warn', artifact: _art, showCard: true,
    task_status: _task, preview_status: _prev, completion_status: _comp,
    text: _art ? ('产物已生成 · 预览待 WPS 就绪（' + _art + '）') : '本次未取到产物路径 · 等 WPS 灵犀就绪后重试',
  };
}
function paWpsStateLine(state){
  const _s = state || {};
  return '任务：' + String(_s.task_status || 'BLOCKED') + ' · 预览：' + String(_s.preview_status || 'PENDING')
    + ' · 完成：' + String(_s.completion_status || 'NOT_COMPLETE');
}
/* ===== 批183 · 纯函数块 END ===== */
/* ===== 批187 · P1 第0步：Markdown 智能渲染（纯函数块 BEGIN；node 单测按标记抽取，勿依赖 DOM）
   安全契约（不可破）：
     ① 先 esc() 整段（保住既有 XSS 线），再做**白名单标记替换** —— 永不把原文直接注入；
     ② 围栏代码块内容**永不解析**（只高亮/转义）；
     ③ 链接协议白名单 http/https/mailto（javascript:/data: 一律降级为纯文本）；
     ④ 输出只含白名单标签：h1-h4/p/ul/ol/li/strong/em/code/pre/blockquote/hr/table/thead/tbody/tr/th/td/a/br。
   小白友好：表格可横向滚动、代码块可复制、标题有层级、长文超限降级为纯文本（防卡顿）。
   ===== */
const PA_MD_MAX = 40000;
function paMdEsc(s){ return esc(String(s==null?'':s)); }
function paMdInline(t){
  let x = String(t==null?'':t);
  x = x.replace(/\x60([^\x60]+)\x60/g, function(_, c){ return '<code>'+c+'</code>'; });
  x = x.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  x = x.replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>');
  x = x.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+|mailto:[^)\s]+)\)/g,
                '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
  x = x.replace(/\[([^\]]+)\]\(([^)]*)\)/g, '$1');   /* 非白名单协议 ⇒ 只留文字 */
  return x;
}
function paMdTable(rows){
  const head = rows[0], body = rows.slice(1);
  let h = '<div class="mdtable"><table><thead><tr>';
  head.forEach(function(c){ h += '<th>'+paMdInline(c)+'</th>'; });
  h += '</tr></thead><tbody>';
  body.forEach(function(r){
    h += '<tr>';
    for (let i=0;i<head.length;i++){ h += '<td>'+paMdInline(r[i]===undefined?'':r[i])+'</td>'; }
    h += '</tr>';
  });
  return h + '</tbody></table></div>';
}
function paMdToHtml(text){
  const raw = String(text==null?'':text);
  if (!raw.trim()) return '';
  if (raw.length > PA_MD_MAX) return '<p>'+paMdEsc(raw)+'</p>';   /* 超长 ⇒ 纯文本降级 */
  const src = paMdEsc(raw).replace(/\r\n/g, '\n');
  const lines = src.split('\n');
  const out = [];
  let i = 0, list = null, para = [];
  const flushPara = function(){ if (para.length){ out.push('<p>'+paMdInline(para.join('<br>'))+'</p>'); para = []; } };
  const closeList = function(){ if (list){ out.push(list==='ul' ? '</ul>' : '</ol>'); list = null; } };
  while (i < lines.length){
    const ln = lines[i];
    if (/^\s*```/.test(ln)){                                    /* 围栏代码块：内容不解析 */
      flushPara(); closeList();
      const lang = ln.replace(/^\s*```/, '').trim();
      const buf = [];
      i++;
      while (i < lines.length && !/^\s*```/.test(lines[i])){ buf.push(lines[i]); i++; }
      i++;
      out.push('<div class="mdcode"><div class="mdcodebar"><span>'+paMdEsc(lang||'code')+'</span><button class="mdcopy" type="button">⧉ 复制</button></div><pre>'+buf.join('\n')+'</pre></div>');
      continue;
    }
    const h = ln.match(/^(#{1,4})\s+(.*)$/);
    if (h){ flushPara(); closeList(); out.push('<h'+h[1].length+'>'+paMdInline(h[2])+'</h'+h[1].length+'>'); i++; continue; }
    if (/^\s*(---+|\*\*\*+)\s*$/.test(ln)){ flushPara(); closeList(); out.push('<hr>'); i++; continue; }
    if (/^\s*(?:>|&gt;)\s?/.test(ln)){ flushPara(); closeList(); out.push('<blockquote>'+paMdInline(ln.replace(/^\s*(?:>|&gt;)\s?/, ''))+'</blockquote>'); i++; continue; }
    if (/^\s*\|.*\|\s*$/.test(ln) && i+1 < lines.length && /^\s*\|[\s:|-]+\|\s*$/.test(lines[i+1])){
      flushPara(); closeList();
      const rows = [];
      while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])){
        const cells = lines[i].trim().replace(/^\||\|$/g, '').split('|').map(function(c){ return c.trim(); });
        if (!/^[\s:|-]+$/.test(lines[i].trim().replace(/^\||\|$/g,''))) rows.push(cells);
        i++;
      }
      if (rows.length) out.push(paMdTable(rows));
      continue;
    }
    const ul = ln.match(/^\s*[-*+]\s+(.*)$/);
    const ol = ln.match(/^\s*\d+[.)]\s+(.*)$/);
    if (ul || ol){
      flushPara();
      const kind = ul ? 'ul' : 'ol';
      if (list !== kind){ closeList(); out.push(kind==='ul' ? '<ul>' : '<ol>'); list = kind; }
      out.push('<li>'+paMdInline((ul||ol)[1])+'</li>');
      i++; continue;
    }
    if (!ln.trim()){ flushPara(); closeList(); i++; continue; }
    para.push(ln);
    i++;
  }
  flushPara(); closeList();
  return out.join('');
}
/* ===== 批187 · MD 渲染纯函数块 END ===== */
/* ---- 批183 · C3/C1 接线（依赖 DOM；纯函数在上一块）---- */
/* M2-A · M2A-07 ②-1（DS 2026-09-18 拍「并入统一出口」）：
   就绪卡**不再自建 DOM、不再散挂 #thread**（批221 同族事故：写 #thread 会被 renderThread 重画清掉）
   ⇒ 改走唯一出口 paRenderCard('wps_ready', …)：宿主固定容器 #paCards、字段走白名单、
   同 key 复用（key='tool'：同名工具同时只该有一张）、「不持久化」标注由出口追加。
   本函数只做**载荷整形**（后端 step ⇒ 受控字段），**不产 DOM、不产文案**（文案仍由批183 纯函数出）。 */
function paWpsReadyCardRender(tool, hint, artifact, state){
  const _s=state||{};
  return paRenderCard('wps_ready', {
    tool:(tool==null?'':String(tool)),
    hint:(hint==null?null:String(hint)),
    artifact_path:(artifact==null?'':String(artifact)),
    task_status:(_s.task_status==null?null:String(_s.task_status)),
    preview_status:(_s.preview_status==null?null:String(_s.preview_status)),
    completion_status:(_s.completion_status==null?null:String(_s.completion_status))
  });
}
/* 桥就绪（ready===true）⇒ 引导卡自动消失（**语义不变**，DS 拍）；移除**一律**走 paDismissCard（连带同步提示行）。
   注意：去重键是 `tool` ⇒ 同时**可能有多张**就绪卡（多个工具各一张）⇒ 必须**全清**；
   只清第一张会留残卡，那就不是「自动消失」了。 */
function paWpsReadyCardClear(){
  const host=document.getElementById('paCards'); if(!host) return;
  host.querySelectorAll('[data-card-kind="wps_ready"]').forEach(function(card){ paDismissCard(card); });
}
/* ===== 批176 · 知识库↔沙箱映射纯函数块 BEGIN（node 单测按标记抽取；本块内**不得**依赖 DOM）===== */
const PA_KB_STATUSES = ['已镜像','过期','缺失','未镜像','未知'];   /* P9 验收-B：三态里的「不适用」也要能显示 */
function paKbStatusClass(st){ return st==='已镜像' ? 'kb-ok' : (st==='过期' ? 'kb-stale' : (st==='缺失' ? 'kb-miss' : 'kb-none')); }
function paKbNeedsMirror(st){ return st!=='已镜像'; }
function paKbShort(p, n){ const s=String(p==null?'':p); const k=(n||34); return s.length<=k ? s : ('…'+s.slice(-k)); }
function paKbCopyBtn(text){
  return '<button class="kbcopy" data-copy="'+esc(text)+'" title="复制路径：'+esc(text)+'" onclick="paKbCopy(this)">⧉</button>';
}
function paKbMirrorBtn(kbPath){
  return '<button class="kbmirror" data-kb="'+esc(kbPath)+'" title="生成「请把该素材镜像到沙箱」的请求（只填进输入框，不自动执行）" onclick="paKbRequestMirror(this)">请求镜像</button>';
}
function paKbRowsHtml(rows){
  if(!rows || !rows.length) return '<div class="kb-empty">（无映射数据：知识库范围为空或不可读）</div>';
  let h='<table class="kbtable"><thead><tr><th>知识库（主语）</th><th>沙箱映射</th><th>状态</th></tr></thead><tbody>';
  rows.forEach(function(r){
    const st=r.status||'未镜像';
    const kbPath=r.kb_path||''; const sbPath=r.sandbox_path||'';
    h+='<tr class="kbrow '+paKbStatusClass(st)+'">'
      + '<td class="kbpath">'+esc(paKbShort(kbPath,42))+paKbCopyBtn(r.kb_abs||kbPath)+'</td>'
      + '<td class="kbpath">'+(sbPath?esc(paKbShort(sbPath,42))+paKbCopyBtn(sbPath):'—')+'</td>'
      + '<td class="kbstatus" title="'+esc(r.reason||'')+'"><span class="kbstate">'+esc(st)+'</span>'
      + (paKbNeedsMirror(st)?(' '+paKbMirrorBtn(kbPath)):'')+'</td></tr>';   // 批176：按钮并入「状态」列，表保持任务书要求的三列
  });
  return '<div class="kbscroll">'+h+'</tbody></table></div>';
}
function paKbCountsHtml(counts, total, truncated, fail){
  const c=counts||{}; const parts=[];
  PA_KB_STATUSES.forEach(function(st){ if(c[st]) parts.push(st+' '+c[st]); });
  /* P9 · BUG-4：⛔ 不留「共 ? 项」占位符 —— 取不到就**说清为什么**（三态口径：未知 也是一态）
     ⭐ pm_刀12p §〇：**三态分显** —— 未接（后端无此面）⟷ 不可达（后端此刻不在 ／ 请求失败）⟷ 真 0。
     ⚠ 病（PM 实测 · 停服窗）：`paKbLoad` 之捕获支落 `counts:{}` ＋ 无 `total` ⇒ 本处显
       「暂无数据（项数未知：接口未给 total）」⇒ 老板把「产品刚才停机」读成「这块没做」。
     ⇒ ⛔ 以「暂无数据」盖「不可达」；两因分书（fetch 抛 ⇒ 不可达 ；后端非 ok ⇒ 未接）。 */
  if(fail){ return String(fail); }
  const tail=(total==null)?'（项数未知：接口未给 total ⇒ 明说未知，⛔ 不填占位符）':('（共 '+total+' 项）');
  const body=(parts.length?parts.join(' · '):(total===0?'真 0（后端 total=0）':'暂无数据（后端已应答 · counts 空）'));
  return body + (truncated?' · 已截断':'') + tail;
}
function paKbPanelHtml(doc, opts){
  const o=opts||{}; const d=doc||{};
  const rows=d.rows||[]; const deg=d.degraded||'';
  let h='<details class="kbpanel"'+(o.open?' open':'')+'><summary>📚 知识库映射 · '+esc(paKbCountsHtml(d.counts,d.total,d.truncated,d._fail))+'</summary>';
  h+='<div class="kbmeta">范围 '+esc(d.scope||'')+' · 知识库 '+esc(d.kb_root||'—')+' · 沙箱 '+esc(d.sandbox_root||'—')
    +' · <span class="kb-ro">只读</span> <button class="kbrefresh" onclick="paKbLoad(true)">刷新</button></div>';
  if(deg) h+='<div class="kb-degraded">⚠ '+esc(deg)+'</div>';
  h+=paKbRowsHtml(rows)+'</details>';
  return h;
}
function paKbRootForms(){
  /* 前缀一律由**后端**给（C1：前端 ⛔ 不写死文件系统路径）----
     来源 ① /v9/pa/kb_mapping 的 kb_root_forms ／ kb_root；② 兜底：由 rows 的 kb_abs 反推根。
     ⛔ 两形态（本机 Win 形态 与 WSL 挂载形态）都要能认 —— 由后端算，前端只消费。 */
  const d=(function(){ try{ return paKbCache||{}; }catch(e){ return {}; } })();
  const out=[];
  const push=function(p){
    let v=String(p==null?'':p);
    while(v.length && (v.charAt(v.length-1)==='/' || v.charAt(v.length-1)==="\\")) v=v.slice(0,-1);
    if(v && out.indexOf(v)<0) out.push(v);
  };
  const forms=d.kb_root_forms||[];
  for(let i=0;i<forms.length;i++) push(forms[i]);
  push(d.kb_root);
  const rows=d.rows||[];
  for(let i=0;i<rows.length;i++){
    const a=String((rows[i]||{}).kb_abs||''); const rp=String((rows[i]||{}).kb_path||'');
    if(a && rp){
      /* 分隔符常不同（kb_path 用斜杠 / ， kb_abs 用反斜杠）⇒ 归一后再比，⛔ 否则反推恒失败（实测：曾恒返空） */
      const S=String.fromCharCode(92);
      const k=a.split(S).join('/').lastIndexOf(rp.split(S).join('/'));
      if(k>0) push(a.slice(0,k));
    }
  }
  return out;
}
function paKbExtractPaths(text, roots){
  /* 文本里出现的知识库路径 → 链接化前缀。前缀由后端给（上函数）；⛔ 前端不写死路径。
     无前缀时返回空（宁可不链接，⛔ 不用写死的前缀猜）。 */
  const s=String(text==null?'':text); const out=[]; const seen={};
  let pres=roots;
  if(!pres || !pres.length){ pres=(typeof paKbRootForms==='function') ? paKbRootForms() : []; }
  if(!pres || !pres.length) return out;
  const isStop=function(c){ return c===' '||c==='\t'||c==='\n'||c==='\r'||c===""||c==="'"||c==='<'||c==='>'||c==='('||c===')'||c==='，'||c==='。'||c==='；'; };
  for(let i=0;i<pres.length;i++){
    const pre=String(pres[i]||''); if(!pre) continue;
    let idx=0;
    while((idx=s.indexOf(pre, idx))>=0){
      let j=idx+pre.length;
      while(j<s.length && !isStop(s.charAt(j))) j++;
      if(j>idx+pre.length){ const v=s.slice(idx,j); if(!seen[v]){ seen[v]=1; out.push(v); } }
      idx=j+1;
    }
  }
  const rr=/收件箱\/[^\s"'<>()，。；]+\.md/g; let m;
  while((m=rr.exec(s))!==null){ const v=m[0]; if(!seen[v]){ seen[v]=1; out.push(v); } }
  return out;
}
function paKbStatusFor(kbPath, rows){
  const t=String(kbPath==null?'':kbPath); const list=rows||[];
  for(let i=0;i<list.length;i++){ const r=list[i]||{};
    const rp=String(r.kb_path||''); const ra=String(r.kb_abs||''); const rn=String(r.name||'');
    if(t===rp || (ra&&t===ra) || (rp&&t.endsWith('/'+rp)) || (rn&&t.endsWith('/'+rn))){
      return {status:r.status||'未知', sandbox:r.sandbox_path||'', reason:r.reason||''};
    }
  }
  return null;
}
function paKbCapsuleHtml(text, rows){
  const paths=paKbExtractPaths(text);
  if(!paths.length) return esc(text);
  let h='';
  paths.forEach(function(p){
    const hit=paKbStatusFor(p, rows);
    const st=hit?hit.status:'未知'; const sb=hit?hit.sandbox:'';
    h+='<details class="kbcapsule"><summary>📚 '+esc(paKbShort(p,40))+' → 📁 '+(sb?esc(paKbShort(sb,40)):'（沙箱路径未知）')
      +' <span class="kbstatus '+paKbStatusClass(st)+'">'+esc(st)+'</span></summary>'
      +'<div class="kbbody">知识库：'+esc(p)+paKbCopyBtn(p)
      +'<br>沙箱：'+esc(sb||'—')+(sb?paKbCopyBtn(sb):'')
      +(hit&&hit.reason?('<br>判据：'+esc(hit.reason)):'')
      +(paKbNeedsMirror(st)?('<br>'+paKbMirrorBtn(p)):'')
      +'</div></details>';
  });
  return h+'<div class="kbraw">'+esc(text)+'</div>';
}
/* ===== 批176 纯函数块 END ===== */
/* ---- 批176 · A2′ 面板接线（依赖 DOM；纯函数在上一块）---- */
let paKbCache=null;
function paKbApiUrl(){
  return API+'/v9/pa/kb_mapping?user_id='+encodeURIComponent(curUser())
    +'&session_id='+encodeURIComponent(curSession())+'&scope='+encodeURIComponent('收件箱')+'&limit=100';
}
async function paKbLoad(force){
  const host=document.getElementById('kbPanel'); if(!host) return;
  if(paKbCache && !force) return;
  try{
    const r=await fetch(paKbApiUrl()); const d=await r.json();
    paKbCache = (d && d.ok) ? d
      : {rows:[],counts:{}, _fail:'未接（后端已应答但非 ok · HTTP '+r.status+'）',
         degraded:'映射接口不可用：'+((d&&d.error)||r.status)};
  }catch(e){ paKbCache={rows:[],counts:{}, _fail:'不可达（后端此刻不在 ／ 请求失败）', degraded:'映射接口请求失败：'+e.message}; }
  renderKbPanel();
}
async function paKbPrime(){
  /* 首屏预热：把后端给的脑根前缀先拿到（胶囊链接化要用）。只读接口，⛔ 不改任何一侧。 */
  try{
    const r=await fetch(paKbApiUrl()); const d=await r.json();
    if(d && d.ok && !paKbCache) paKbCache=d;
  }catch(e){}
}
function renderKbPanel(){
  const host=document.getElementById('kbPanel'); if(!host) return;
  const open = host.getAttribute('data-open')==='1';
  host.innerHTML = paKbPanelHtml(paKbCache||{rows:[],counts:{}, _fail:'尚未取（展开本面板即取 · ⛔ ≠ 不可达 ／ ⛔ ≠ 空）', degraded:'尚未加载（展开时按只读接口拉取，不刷新页面）'}, {open:open});
  const det = host.querySelector('details');
  if(det){ det.addEventListener('toggle', function(){ host.setAttribute('data-open', det.open?'1':'0'); if(det.open) paKbLoad(false); }); }
}
function paKbCopy(btn){ const t=btn.getAttribute('data-copy')||''; try{ if(navigator.clipboard) navigator.clipboard.writeText(t); }catch(e){} receipt('已复制路径：'+String(t).slice(0,60),'ok'); }
function paKbRequestMirror(btn){
  const kb=btn.getAttribute('data-kb')||''; const inp=document.getElementById('input');
  if(inp){ inp.value='请把知识库素材镜像到沙箱：'+kb; inp.focus(); }
  receipt('已生成镜像请求（未执行，需你确认）：'+String(kb).slice(0,60),'warn');
}
function $(id){ return document.getElementById(id); }
function activeThread(){
  if(!state.threads.length) newThread(true);
  let t = state.threads.find(t=>t.id===state.activeThread);
  if(!t){ t = state.threads[0]; state.activeThread = t.id; }
  return t;
}
function newThread(silent){
  /* 批219·A（老板 2026-09-16 拍板：**保持 PA 单线程口径**）——同步到 live（真源）。
     旧实现 state.threads.unshift(t) 会并存第 2 条线程，随后 paCollapseToSingleThread() 又把它裁掉
     （内存+写盘同时裁 ⇒ 旧会话直接丢）。新口径：同时只保留 1 个会话；「新建会话」= 当前会话**移交本地归档**（不删）。 */
  const id = 'pa_' + Date.now().toString(36);
  const cur = (state.threads||[]).find(function(x){ return x.id===state.activeThread; });
  if(cur && (cur.msgs||[]).length){   /* 批223 修：**只归档有消息的会话** —— 空线程无内容可丢；
        旧「总是归档」会让 E2E 每跑一次多一条空归档 ⇒ archived 膨胀到 837 条 ⇒ localStorage 撑爆 ⇒ newThread/saveState 失效 */
    state.archived = (state.archived||[]).concat([Object.assign({}, cur, {archived_at:new Date().toISOString()})]);
    /* 批219 修（我上一版引入的丢失点）：**不得静默裁剪归档** —— 上限调高到 50，且**裁剪必须可见**（console + 页面提示）。
       真到写不进时，由 saveState() 的失败上报负责（不静默）。 */
        /* 批221·A（老板拍板）：**归档不设上限、不裁剪** —— "不丢数据"优先。
       溢出（>PA_ARCHIVE_HINT_COUNT 条）改为：①可见提示（写入活动线程 msgs，随渲染存活）②提供导出函数。
       若 localStorage 真的写不进，由 saveState() 的失败上报兜底（不静默）。 */
    if((state.archived||[]).length > PA_ARCHIVE_HINT_COUNT){
      try{ console.warn('[PA] 归档已 '+state.archived.length+' 条，建议导出（paExportArchive()）'); }catch(_e){}
      try{
        const _at=(state.threads||[]).find(function(x){ return x.id===state.activeThread; });
        const _mark='归档已超过 '+PA_ARCHIVE_HINT_COUNT+' 条';
        /* W-09：提示不再指「去控制台跑函数」（用户看不见控制台），改指**横幅上的两个按钮**。 */
        if(_at && !(_at.msgs||[]).some(function(m){ return (m.content||'').indexOf(_mark)>=0; })){
          _at.msgs=(_at.msgs||[]).concat([{role:'sys', content:'⚠ 本地归档已超过 '+PA_ARCHIVE_HINT_COUNT+' 条（'+state.archived.length+'）。为保证不丢，请点横幅上的「导出归档 JSON」备份；如需腾空间，可点「手动清理归档」（需你二次确认，不会自动删除）。'}]);
        }
      }catch(_e2){}
    }
  }
  const t = { id, title:'新线程', mode:state.mode, msgs:[] };
  state.threads = [t]; state.activeThread = id; saveState(); syncPaSession();
  if(!silent){ renderThreads(); renderThread(); addMsg('sys','新线程已建立（'+MODES[state.mode].label+'）'); loadFiles(); }  /* 批122 A：新线程=新沙箱，面板立刻跟随 */
  return t;
}
