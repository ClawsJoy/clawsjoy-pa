/* ---- M2-A · Step 2：统一展示出口 paRenderCard（三张卡共用）----------------------------
   设计稿 codex/2026-09-17-v9pes-m2a-visibility-closure-design.md §2.4 / §6 Step 2。
   三条纪律（不靠自觉，靠判据）：
   1. **只认白名单**：kind ∈ {approval, artifact, block}，每类只认自己的字段白名单。
      未知 kind ⇒ 不渲染；未知字段 ⇒ **丢弃 + console.warn**（不静默、不塞进 DOM）。
   2. **挂固定容器 #paCards**：**不散挂 #thread** —— 批221 现场：写 #thread 会被 renderThread 重画覆盖
      （同类事故见体检库 #8：降级提示被 setMode/renderThread 覆盖 ⇒ 静默降级）。
      **唯一例外（Step 3.2）**：**产物卡**是**消息内联**的交付预览（自批201 起随「持久化的助手正文」
      重建，F5 后仍在）⇒ 由调用方显式传宿主 #thread；搬进不持久化的 #paCards 会丢掉该语义。
      例外**只对 renderOutputCard 生效**；卡片模块自身仍不得触碰 #thread（静态判据钉死）。
   3. **不代填**：只做字符串化与「未记录 / 未核验」文案；**卡片字段一律不参与时间计算**
      —— 倒计时/耗时只能由后端给（设计稿 §2.1 revoke_window 纪律）。
      本模块**禁止 Date.now()/new Date()/setInterval()**，有静态反例测试钉死
      （tests/pes/test_m2a_frontend_outlet.py）。
   **卡片不持久化**（老板 2026-09-18 拍板：不持久化但必须标注）：本容器只反映本次页面会话
   收到的事实，刷新即清空；**不凭历史消息重造卡片**（防「假成交」：把旧正文重渲染成新证据）。 */
const PA_CARD_DEF = {
  approval: {cls:'pa-write-card',    required:['id'],       fields:['id','tool','target','reason','is_batch','items','expires_in_s','decisions','revoke_window']},
  artifact: {cls:'pa-artifact-card', alias:'output-card', required:['path'],     fields:['path','exists','sha256','bytes','verified_by','done_when_status','verdict','reported_source']},
  block:    {cls:'pa-block-card',    required:['block_id'], fields:['block_id','blocked_at','layer','reason','blocked_action','evidence_ref','unblock_hint','state_map_key']},
  wps_ready:{cls:'pa-wps-card',     required:['tool'],       fields:['tool','hint','artifact_path','task_status','preview_status','completion_status']}
};
/* 纯函数（node 可直接跑）：白名单过滤 + 未知字段清单 + 必填校验。**无 DOM、无时间。** */
function paCardFilter(kind, payload){
  const def = PA_CARD_DEF[kind];
  if(!def) return {ok:false, reason:'未知卡片类型 '+kind, data:null, unknown:[]};
  const src = (payload && typeof payload==='object') ? payload : {};
  const data={}, unknown=[];
  Object.keys(src).forEach(function(k){ if(def.fields.indexOf(k)>=0){ data[k]=src[k]; } else { unknown.push(k); } });
  for(let i=0;i<def.required.length;i++){
    const rk=def.required[i];
    if(data[rk]===undefined || data[rk]===null || data[rk]===''){
      return {ok:false, reason:'缺必填字段 '+rk, data:null, unknown:unknown};
    }
  }
  return {ok:true, reason:'', data:data, unknown:unknown};
}
/* 决策按钮文案 = **常量**（不由后端文本拼）；未知决策串一律不渲染 */
const PA_CARD_ACTS={approve:'✅ 仅本次', always:'♾️ 一直允许', reject:'❌ 不允许'};
const PA_CARD_BODY={
  approval:function(d){
    const cmd=(d.target==null)?'':String(d.target);
    const why=(d.reason==null||String(d.reason).trim()==='')?('等待老板确认：'+cmd.slice(0,80)):String(d.reason).trim();
    const acts=(Array.isArray(d.decisions)?d.decisions:Object.keys(PA_CARD_ACTS)).filter(function(a){ return !!PA_CARD_ACTS[a]; });
    /* M2-A · Step 3.3（方案 A）：`expires_in_s` / `revoke_window` 现在是**后端快照透传** ——
       ① 后端没给（null/undefined）⇒ 该行**不出现**（连「暂无」都不写，避免暗示它存在）；
       ② **仍禁止本地估算/递减**：本函数只把后端数字转成文本，不引入任何时间调用
          （`Date.now()`/`new Date()`/`setInterval()`/`getTime()` 已被静态反例钉死）；
       ③ 撤销窗口只在 `show===true` 且秒数可读时渲染 —— 写审批今天**未接 hold** ⇒ 恒不出现；
       is_batch / items 仍留后续步（批量卡是 M2-A 扩展，老板拍「不上本批」）。 */
    const ttl=(d.expires_in_s==null)?'':('<div class="pwc-ttl">⏱ 剩余 '+esc(String(d.expires_in_s))+' 秒（后端快照，不本地递减）</div>');
    const rw=d.revoke_window;
    const rwHtml=((rw&&rw.show===true&&rw.seconds_left!=null)
      ?('<div class="pwc-revoke">↩ 撤销窗口：剩余 '+esc(String(rw.seconds_left))+' 秒（后端快照）</div>') : '');
    return '<div class="pwc-head">⏳ Agent 请求写入（需确认）</div>'+
      '<div class="pwc-reason" id="paWriteReason">⚠️ '+esc(why)+'</div>'+
      (cmd?'<div class="pwc-cmd">'+esc(cmd.slice(0,220))+'</div>':'')+
      ttl+rwHtml+
      '<div class="pwc-btns">'+acts.map(function(a){ return '<button data-act="'+esc(a)+'">'+PA_CARD_ACTS[a]+'</button>'; }).join('')+'</div>';
  },
  /* M2-A · Step 3.2：产物卡。四条不许（设计稿 §2.2 / §4.1）——
     ① 默认态**未经核验**：读不到核验 ⇒ 写「未核验」，**不得**写「存在」；
     ② 来源必须显式：探测来的路径 ⇒ 「来源：正文探测（非核验）」，受控词表，未知不猜；
     ③ 不得升级 `claimed`：原样渲染成「agent 自报，未验证（claimed）」；
     ④ 不得出现「✅ 产物已生成」这类完成断言 —— 完成只有后端 verdict 能给。 */
  artifact:function(d){
    const path=String(d.path==null?'':d.path);
    const name=path.split('/').pop()||path;
    /* 受控词表：只认已知来源；未知/缺失 ⇒ 按「未记录（按未经核验处理）」——不猜、不美化 */
    const SRC={text_probe:'正文探测（非核验）'};
    const src=SRC[String(d.reported_source==null?'':d.reported_source)]||'未记录（按未经核验处理）';
    const by=(d.verified_by==null)?'':String(d.verified_by).trim();
    const DWS={unset:'未声明（unset）', claimed:'agent 自报，未验证（claimed）', verified:'已核验（verified）'};
    const dws=(d.done_when_status==null)?'未记录':(DWS[String(d.done_when_status)]||('未知取值 '+String(d.done_when_status)));
    /* 磁盘实况：**未知 ≠ 不存在**（P1 未知即未知） */
    const ex=(d.exists===true)?'存在（后端 record_artifact 判定）':((d.exists===false)?'不存在':'未核验');
    const vd=(d.verdict&&typeof d.verdict==='object')?d.verdict:null;
    const verified=(!!by || String(d.done_when_status)==='verified' || !!vd&&vd.state==='done');
    const rows=['路径：'+esc(path),'来源：'+esc(src),'磁盘实况：'+esc(ex),
                '验证者：'+esc(by?('已由 '+by+' 签署'):'未经验证者签署'),
                '完成判据：'+esc(dws),
                '完成裁决：'+esc(vd?((vd.state==null?'未记录':String(vd.state))+(vd.reason?('（'+String(vd.reason)+'）'):''))
                                  :'没有契约，无法裁决完成')];
    if(vd&&vd.next_action) rows.push('下一步：'+esc(String(vd.next_action)));
    /* 设计稿 §2.2：sha256/bytes **空 ⇒ 不显示该行**（不是显示「未知」） */
    if(d.sha256||d.bytes!=null){
      rows.splice(3,0,'内容指纹／大小：'+esc((d.sha256?(String(d.sha256).slice(0,12)+'…'):'未核验')
                                          +'／'+(d.bytes!=null?(String(d.bytes)+' 字节'):'未核验')));
    }
    return '<div class="oc-head"><span>📄</span><span class="oc-name">'+esc(name)+'</span>'
      +'<span class="oc-ai" style="font-size:10.5px;color:#7ee787;border:1px solid #2ea043;border-radius:5px;padding:0 6px">AI 辅助生成</span>'
      +'<span class="oac-ver">'+(verified?'已核验':'未经核验')+'</span><span class="oc-path">'+esc(path)+'</span>'
      +'<button class="oc-toggle" data-act="download">下载</button>'
      +'<button class="oc-toggle" data-act="toggle">展开全文</button></div>'
      +'<div class="oac-meta">'+rows.map(function(x){ return '<div>'+x+'</div>'; }).join('')+'</div>'
      +'<div class="oc-body"><div class="oac-note">正文预览：由前端读取（/v9/sandbox/read），'
      +'只证明「读得到」，不是交付证据。</div><pre data-oac-body="1"></pre></div>';
  },
  /* M2-A · Step 3.1：阻断卡。三个不许（设计稿 §2.3）——
     ① 不许把阻断渲染成 tool（语义修正在 SSE 分支：paSetState('blocked', …)）；
     ② 不许给「重试」当万能解 ⇒ **本卡不带任何动作按钮**（阻断分「可重试」与「需老板改授权」）；
     ③ 不许隐藏 unblock_hint 缺失 ⇒ 没替代路径就**明说**（防「假拒绝」）。 */
  block:function(d){
    const reason=(d.reason==null||String(d.reason).trim()==='')?'原因未记录':String(d.reason);
    const hint=(d.unblock_hint==null||String(d.unblock_hint).trim()==='')?'':String(d.unblock_hint);
    const rows=['阻断编号：'+esc(String(d.block_id))];
    if(d.blocked_action!=null) rows.push('被拦动作：'+esc(String(d.blocked_action)));
    rows.push('层：'+esc(d.layer==null?'未知层':String(d.layer)));
    rows.push(hint?('替代路径：'+esc(hint)):'无替代路径（未记录）');
    if(d.evidence_ref!=null) rows.push('证据：'+esc(String(d.evidence_ref)));
    if(d.blocked_at!=null) rows.push('阻断时刻（后端）：'+esc(String(d.blocked_at)));
    return '<div class="pbc-head">⛔ 已阻断（等待老板处理，不是错误）</div>'+
      '<div class="pbc-why">原因：'+esc(reason)+'</div>'+
      '<div class="pbc-meta">'+rows.map(function(x){ return '<div>'+x+'</div>'; }).join('')+'</div>';
  },
  /* M2A-07 ②-1（并入统一出口）：模板仍由批183 的**纯函数**出（不复制第二份文案），
     出口负责本类别的四条纪律：字段白名单、同 key 复用、宿主、标注；本函数**纯同步、无时间**。 */
  wps_ready:function(d){
    return paWpsReadyCardHtml(d.hint, d.artifact_path,
      {task_status:d.task_status, preview_status:d.preview_status, completion_status:d.completion_status});
  }
};
/* 每个 kind 的按钮绑定（DOM 侧；与 body 分开，便于纯函数单测） */
const PA_CARD_BIND={
  approval:function(card,d){
    card.querySelectorAll('button').forEach(function(b){
      b.addEventListener('click',function(){ paWriteDecide(d.id,b.getAttribute('data-act'),card); });
    });
  },
  /* 产物卡绑定（DOM 侧，非纯函数）：内容从 **_outputContent** 取（前端读取缓存），
     不是 payload 字段 ⇒ 白名单不被污染；缓存没有 ⇒ **明说未取到**（不等于文件不存在）。 */
  artifact:function(card,d){
    const path=String(d.path==null?'':d.path);
    card.setAttribute('data-path',path);   /* 兼容层：downloadOutput / 既有选择器仍按 .output-card[data-path] 工作 */
    const body=card.querySelector('.oc-body');
    const pre=body?body.querySelector('pre[data-oac-body]'):null;
    if(pre){
      const c=_outputContent[path];
      pre.textContent=(typeof c==='string')?c:'（正文未取到：/v9/sandbox/read 未返回内容 —— 这不代表文件不存在）';
    }
    card.querySelectorAll('button[data-act]').forEach(function(b){
      const a=b.getAttribute('data-act');
      if(a==='download'){ b.addEventListener('click',function(){ downloadOutput(b); }); }
      else if(a==='toggle'&&body){ b.addEventListener('click',function(){ body.classList.toggle('open'); }); }
    });
  },
  block:function(){},
  /* 就绪卡绑定（DOM 侧）：复制按钮走 data-act（**不内联 onclick**，与审批/产物卡同源）。 */
  wps_ready:function(card,d){
    card.querySelectorAll('button[data-act]').forEach(function(b){
      const a=b.getAttribute('data-act');
      if(a==='copy'){ b.addEventListener('click',function(){ paCopyText(b.getAttribute('data-copy')); }); }
    });
  }
};
/* M2-A · Step 3.2 续 / 老板 2026-09-18 拍板：卡片**加「不持久化」标注，不加持久化**。
   **文案逐类如实**（不逐类如实就是「假标注」）：
   - 宿主 `#paCards` 的卡（审批/阻断）：刷新即清空 ⇒ 用老板给定原文；
   - 产物卡宿主是 `#thread`（消息内联，批201 起 F5 后按**消息正文**重建）⇒ 写「刷新后消失」是**反的**；
     但正文本身存在 localStorage，**配额写失败时同样会消失** ⇒ 两句都写清。
   标注由出口 `paRenderCard` 以 `textContent` 追加（不拼 HTML）；**不得**塞进 PA_CARD_BODY
   （那是「事实行」区域，产物卡 body 有「不得出现完成断言」的判据）。 */
const PA_CARD_PERSIST_NOTE = {
  approval: 'ⓘ 本卡片不持久化，刷新后消失；记录见消息日志。',
  block:    'ⓘ 本卡片不持久化，刷新后消失；记录见消息日志。',
  artifact: 'ⓘ 本卡片本身不持久化：刷新后按该条消息正文重建；若本地写入失败（存储配额），会与消息一起消失。',
  wps_ready: 'ⓘ 本卡片不持久化，刷新后消失；记录见消息日志。'
};
function paSyncCardsHint(){
  try{
    const host=document.getElementById('paCards'), hint=document.getElementById('paCardsHint');
    if(hint) hint.classList.toggle('show', !!(host && host.children.length));
  }catch(e){}
}
function paDismissCard(card){
  try{ if(card&&card.parentNode) card.parentNode.removeChild(card); }catch(e){}
  paSyncCardsHint();
}
/* 唯一渲染出口：卡片只经这里进 DOM（三张卡共用）。返回卡片元素；被拒时返回 null 并 warn。
   host（可选，**Step 3.2 新增**）：显式宿主元素；省略 ⇒ 默认容器 #paCards。
   **只允许产物卡传 #thread**（消息内联 + 批201 F5 重建语义，见 renderOutputCard 注释）；
   其它卡传显式宿主属于越界，会连同「卡片模块不得触碰 #thread」的静态判据一起红。 */
function paRenderCard(kind, payload, host){
  const r=paCardFilter(kind,payload);
  if(!r.ok){ console.warn('[PA][CARD] 拒绝渲染 kind='+kind+'：'+r.reason); return null; }
  if(r.unknown.length) console.warn('[PA][CARD] kind='+kind+' 丢弃未知字段：'+r.unknown.join(', '));
  if(!(host && host.appendChild)) host=document.getElementById('paCards');
  if(!host){ console.warn('[PA][CARD] 缺容器 #paCards ⇒ 卡片未渲染（不回落 #thread：会被 renderThread 覆盖）'); return null; }
  const def=PA_CARD_DEF[kind];
  const key=String(r.data[def.required[0]]);
  let card=null;
  for(let i=0;i<host.children.length;i++){
    const ch=host.children[i];
    if(ch.getAttribute('data-card-kind')===kind && ch.getAttribute('data-card-key')===key){ card=ch; break; }
  }
  if(!card){
    card=document.createElement('div');
    card.className=def.cls+(def.alias?(' '+def.alias):'');   /* alias 兼容层：产物卡仍挂 .output-card（CSS / 既有选择器） */
    card.setAttribute('data-card-kind',kind); card.setAttribute('data-card-key',key);
    if(kind==='approval') card.id='paWriteCard_'+key;   /* 兼容旧 id（批153 起沿用） */
    host.appendChild(card);
  }
  card.innerHTML=PA_CARD_BODY[kind](r.data);
  PA_CARD_BIND[kind](card,r.data);
  /* 「不持久化」标注（老板 2026-09-18 拍）：innerHTML 每次重画 ⇒ 标注随之重建（无需去重）。
     textContent 写入 ⇒ 文案不进 HTML 解析路径。 */
  const _note=PA_CARD_PERSIST_NOTE[kind];
  if(_note){
    const _n=document.createElement('div');
    _n.className='pa-card-note'; _n.setAttribute('data-card-note','persist'); _n.textContent=_note;
    card.appendChild(_n);
  }
  if(host.id==='paCards') paSyncCardsHint();   /* 提示行只描述 #paCards 的内容（产物卡在 #thread） */
  try{ if(card.scrollIntoView) card.scrollIntoView({block:'nearest',behavior:'smooth'}); }catch(e){}
  return card;
}

/* M2-A · Step 3.1：阻断卡接**只读投影**接口（Step 1：GET /v9/pes/runs）。
   三条纪律：
   1. **只读**：本函数只 GET，不写任何状态；
   2. **取不到不当「全绿」**：接口不可用 / success=false / 有 degradations ⇒ **只 warn，不渲染假卡**；
      `runs` 为空 ⇒ 不渲染卡片，也**不显示任何「正常」标记**（空 ≠ 全绿，见未闭 M2A-02）；
   3. **字段不代填**：投影已按冻结表给白名单字段，本函数**只搬运**（多余字段由 paRenderCard warn 出来）。 */
async function paLoadPesBlocks(){
  try{
    const r=await fetch(API+'/v9/pes/runs?user_id='+encodeURIComponent(curUser())+'&limit=50');
    if(!r.ok){ console.warn('[PA][PES] 投影接口不可用：HTTP '+r.status+' ⇒ 不渲染任何阻断卡（不用「取不到」冒充「无阻断」）'); return; }
    const d=await r.json();
    if(!d||!d.success){ console.warn('[PA][PES] 投影 success=false：'+((d&&d.error)||'未知')+' ⇒ 不渲染任何阻断卡'); return; }
    const deg=d.degradations||[];
    deg.forEach(function(g){ console.warn('[PA][PES] 降级信号 '+(g&&g.code)+'：'+((g&&g.message)||'')); });
    let n=0, first=null;
    (d.runs||[]).forEach(function(run){
      const b=run&&run.blocked; if(!b) return;
      const card=paRenderCard('block', b);
      if(card){ n++; if(!first) first=b; }
    });
    if(first){   /* 状态药丸也跟着进阻断态（键来自后端 state_map_key；未知键不猜，只 warn） */
      const k=String(first.state_map_key||'blocked');
      if(PA_STATE_DEF[k]) paSetState(k, first.reason||'');
      else console.warn('[PA][PES] state_map_key 未知：'+k+'（不猜，保持原状态）');
    }
    if(!(d.runs||[]).length) console.log('[PA][PES] 投影 runs 为空（无 run 记录）—— 不渲染卡片，也不视为「全绿」');
    console.log('[PA][PES] 阻断卡渲染 '+n+' 张（投影 runs='+(d.runs||[]).length+'，降级信号 '+deg.length+' 条）');
  }catch(e){ console.warn('[PA][PES] 投影请求异常：'+(e&&e.message)); }
}
function renderPaWriteCard(pw, note){
  if(!pw) return null;
  const _cmd=String(pw.command||pw.path||'');
  const _why=(note&&String(note).trim())?String(note).trim():('等待老板确认：'+_cmd.slice(0,80));
  /* M2-A · Step 2：DOM 迁到统一出口 paRenderCard('approval', ...)，只传白名单字段。
     M2-A · Step 3.3（方案 A）：expires_in_s / revoke_window 改**透传后端快照**；
     后端没给（undefined）⇒ **显式 null**（未知即未知；禁止本地估算倒计时 —— 时间调用被静态反例钉死）。 */
  const _payload={ id:pw.id, tool:pw.tool, target:_cmd, reason:_why,
                   expires_in_s:(pw.expires_in_s===undefined?null:pw.expires_in_s),
                   revoke_window:(pw.revoke_window===undefined?null:pw.revoke_window),
                   decisions:['approve','always','reject'] };
  if(pw.batch!==undefined) _payload.is_batch=pw.batch;
  if(pw.items!==undefined) _payload.items=pw.items;
  const card=paRenderCard('approval', _payload);
  if(!card) return null;
  paFlashApproval(card);   /* 批193：自动滚到卡片 + 高亮描边（口径 A：审批在中栏）*/
  receipt('⏳ 有写入等待你拍板','warn');
  return card;
}
async function paWriteDecide(id, action, card){
  if(card) card.querySelectorAll('button').forEach(function(b){ b.disabled=true; });
  addLog(action==='reject'?'👤 已拒绝写入':(action==='always'?'👤 已确认写入（一直允许本场景）':'👤 已确认写入（仅本次）'),
         action==='reject'?'warn':'ok', true);
  try{
    /* ⭐ pm_1465 §二.1（说一用一）：`model` ⇒ **用户所选**（**一处出** `paModelSel` · ⛔ 硬编字面）。 */
    const _wb={user_id:curUser(),session_id:activeThread().id,
        approve_write:{id:id,action:action},messages:window.__paSendMessages||[]};
    const _wm=paModelSel(); if(_wm) _wb.model=_wm;
    const r=await fetch(API+'/v9/agent/chat',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify(_wb)});
    const d=await r.json().catch(function(){ return {}; });
    if(d.status==='write_confirmed'){
      const ok=!!(d.tool_result&&d.tool_result.success);
      const _err=(d.tool_result&&d.tool_result.error)?('：'+d.tool_result.error):'';
      addLog((ok?'✅ ':'❌ ')+'写入'+(ok?'已执行':'失败'+_err), ok?'ok':'err', true);
      receipt(ok?'✅ 写入已执行':'❌ 写入失败', ok?'ok':'err');
      paDismissCard(card);
      if(action==='always') addLog('♾️ 已记住该场景（grants.yaml），下次免问','ok',true);
      if(d.continue_messages&&d.continue_messages.length){
        window.__paSendMessages=d.continue_messages; await sendAgent(activeThread());
      }
    } else if(d.status==='write_rejected'){
      addLog('↩ 已拒绝，Agent 将调整方案','warn',true); receipt('已拒绝该写入','rev');
      paDismissCard(card);
    } else {
      addLog('⚠️ 确认未生效：'+(d.message||d.error||'未知响应'),'err',true);
      receipt('确认未生效（后端未确认）','err');
    }
  }catch(e){ addLog('确认请求失败：'+e.message,'err',true); }
}
function paStop(){
  // 2026-09-13 修 bug #7（中断语义统一）：此前只 abort 前端 fetch —— 后端桥接循环**继续跑**
  // （实测浏览器关闭后仍跑了 35s），即「能停只停前端」。
  // 现在同时置后端取消标志（POST /v9/cancel/<session_id>），桥接循环在下一个检查点退出。
  /* 批187 · 缺陷4：取消「发起线程」，不是当前选中线程 */
  const _t = { id: paRun.threadId || activeThread().id };
  const _tn = (state.threads.find(function(x){return x.id===_t.id;})||{}).title || _t.id;
  try{ fetch(API+'/v9/cancel/'+encodeURIComponent(_t.id),{method:'POST'}).catch(()=>{}); }catch(e){}
  if(abortCtrl) abortCtrl.abort();
  paRunLog('⏹ 已停止：已通知后端取消线程「'+esc(_tn)+'」','warn',true); setBusy(false);
  paSetState('stopped', '老板手动停止（已通知取消：'+_tn+'）');   // 批159 · 批187 缺陷4 写明线程
}
