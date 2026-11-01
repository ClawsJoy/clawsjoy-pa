/* ---- 发送 ---- */
let abortCtrl=null;
/* P1-1：PA_RUN_API 固定 1；work/dev 单链只走 /v9/agent/runs（⛔ 旧 SSE 静默 fallback） */
var PA_RUN_API = 1;
var PA_LAST_RUN_KEY = 'pa.lastRun';
try{ window.PA_RUN_API = PA_RUN_API; }catch(e){}
/* ⭐ pm 1184 §一.⒜：canonical 拒答文之**真源 ＝ 后端**（`POST /v9/pa/ask` 之响应键 `refusal_canon`）
   ⇒ 本件**引用**之；本 `var` 退为**回落**（后端未开此键 ／ 无响应对象时用）· ⛔ 二处各写（承「一处口径」）。
   答话内 ⛔ 得出现「已完成 ／ 查不到」两形。 */
var PA_REFUSE_CANON = '本机无据 ⇒ 我不答此问。';
/* canonical 之气取：后端 `refusal_canon` 优先，缺则回落本件之文（真源一处 ⇒ 免「漂移之床」）。 */
function paRefusalCanon(g){
  const v = (g && typeof g.refusal_canon === 'string') ? g.refusal_canon : '';
  return v || PA_REFUSE_CANON;
}
/* 旧失实之辞之判（＝后端 `refusal_stale`「查不到（知识库里没有相关内容）」之词形）⇒ 作**旁证**。
   ⚠ 唯控「须以 canonical 代之」之处 · ⛔ 独断（承「以形判必漏」）；真源 ＝ selfdesc.js 之 `paSelfRefusal`
     （本页后载 ⇒ 运行时可取）；无它之旧页（web/pa.html）⇒ 回本处之内联形（与 status.js:27 之回落同法）。 */
function paRefusalStale(t){
  if(typeof paSelfRefusal === 'function'){ try{ return paSelfRefusal(t); }catch(e){} }
  const s = String(t == null ? '' : t).trim();
  if(!s) return false;
  return (s.indexOf('查不到') === 0) || /知识库里没有相关内容/.test(s) || /库里无依据/.test(s);
}
try{ window.paRefusalCanon = paRefusalCanon; window.paRefusalStale = paRefusalStale; }catch(e){}
let lastVerify=null;      // verify_verdict 可视化（2026-09-13）：后端把核验结论挂在 SSE done payload 上
async function paSend(){
  const text=$('input').value.trim(); if(!text) return;
  addMsg('user', text); $('input').value=''; autoGrow(); setBusy(true);
  paSetState('running');                       // 批159：进执行态
  const cfg = MODES[state.mode], t = activeThread();
  /* 批187 · 缺陷4：单活动 run —— 别的线程在跑时不允许再发，避免多写者/取消错对象 */
  if (paRun.busy && paRun.threadId && paRun.threadId !== t.id){
    const _rt=(state.threads.find(function(x){return x.id===paRun.threadId;})||{}).title||paRun.threadId;
    addMsg('sys','⏳ 线程「'+esc(_rt)+'」正在执行 —— 请先点「停止」取消它，或等它结束后再发新任务');
    return;
  }
  paRun.threadId = t.id; paRun.busy = true;   /* 缺陷4：绑定发起线程 */
  paRun.receipt = null; paRun.evidence = null;   /* P9 · BUG-1：回执每轮清零，⛔ 不跨轮复用 */
  try{
    /* P9 · BUG-2：知识/事实问句先过「有据才答」闸（先检索、后作答）；
       库里无据 ⇒ **当场拒答**且⛔不进模型、⛔不进执行循环（没有据，就没有可编的空间）。 */
    let _askMeta = null;   /* ⭐ pm 1184 §一.⒝：本轮答之**源标**（知其实方传 · ⛔ 冒） */
    /* P2-6：多席/seats 前缀 ⇒ 跳过有据才答闸，直接执行（work/dev ⇒ runs） */
    if(paLooksLikeKnowledgeQuestion(text) && !_paRunsIsMultiSeat(text)){
      const g = await paAskGate(text);
      /* ⭐⭐ pm_1617 §二.3 ＝ pm_1614 §二.1（合办 · **一处定形**）：`gate.decision = not_applicable`
         （库根未接 ∨ 检索面为空）—— 闸判「拒答与否皆不成立」⇒ **显后端之 canon** ∧ **⛔ 落模型**。
         病（净机 · 老板之屏一手）：该支 `refused=false ∧ grounded=false` ⇒ 直落 `sendPA` ⇒ `/v9/pa/dialog`
           ⇒ 屏上现「模型调用失败：本机与云端皆不可用（[WinError 2] …）」（＝ pm_1614 §〇 之的）。
         ⚠ 字面**唯取后端**（`answer_canon` ⇒ `answer` ⇒ `verdict`）· ⛔ 前端自造文。
         ⚠ 二支之别（一手）：`gateway_routes.py:2565`（库根未接）**无** `answer_canon` ／
           `:2618`（检索面空）**有** ⇒ 故取三键之首个非空（全缺 ⇒ 明书「无字可显」· ⛔ 造辞）。 */
      if(g && g.gate && String(g.gate.decision || '') === 'not_applicable'){
        const _canon = [g.answer_canon, g.answer, g.verdict]
          .map(function(x){ return (typeof x === 'string') ? x.trim() : ''; })
          .filter(function(x){ return !!x; })[0] || '';
        const _r = (_canon || '（后端未给「不适用」之辞 ⇒ 如实无字可显 —— 见判据行）')
          + '\n\n（判据 /v9/pa/ask ｜ 检索面 '+((g.scope||[]).join(' / ')||'—')
          + ' ｜ 实搜 '+g.searched+' 件 ｜ 阈值 '+g.threshold+' ｜ 读数 '+g.read_at+'）'
          + '\n⛔ 本问未进模型：闸判「不适用」（检索面为空 ⇒ 拒答与否皆不成立）'
          + ' · 后端判词：' + (String(g.verdict||'').trim() || '（未给）')
          + ' · 见「判据」行。';
        try{ window.PASelfRouteLast = {
          label: {text: 'src: 本机不适用（检索面空 · 未调用模型）', key: '不适用', kind: 'self', model: ''},
          at: String(g.read_at || ''), url: '/v9/pa/ask'}; }catch(e){}
        addMsg('assistant', _r);
        /* 照实落盘（**⛔ 造标**）：`answer_source` 逐字取后端 `not_applicable`；`origin` **⛔ 冒** ——
           其封闭集（core/pa/dialog.py:39-42）唯 model ／ grounded ／ refused ／ unspecified
           ⇒ 无「不适用」之值 ⇒ 唯传 `answer_source` ＋ `grounded:false`（⇒ 行落 `unspecified` ＝ 照实「未标」）。 */
        paRun.receipt = await recordPaTurn(t.id, text, _r,
          {grounded:false, answer_source:(g.answer_source || 'not_applicable')});
        paSetState('done');
        return;
      }
      if(g && g.refused){
        /* ⭐ pm 1184 §一.⒜（承 pm 21:20 §二.处3）：canonical 引**后端** `g.refusal_canon`（真源）；
           后端之辞留其**径**（判据行）。
           ⚠ **守界**（TD 1056 §四 · pm 1184 §一.⒜）：⛔ **无条件**以 canonical 覆 `answer` ——
             `answer_source=decision_none` 之 `answer` 系**逐字之由**（「本机决策账无此条：…」）⇒ 替之则失据。
             ⇒ **唯当**后端 `answer` 为拒答之辞（＝canonical ∨ 旧失实之辞）∨ **空** ⇒ 以 canonical 书之；
               **余者原样引后端 `answer`**（此即逐字之由须载值之处）。 */
        const _canon = (typeof paRefusalCanon === 'function') ? paRefusalCanon(g) : PA_REFUSE_CANON;
        const _ans = (typeof g.answer === 'string') ? g.answer.trim() : '';
        const _isRefusal = (!_ans) || (_ans === _canon)
          || ((typeof paRefusalStale === 'function') ? paRefusalStale(_ans) : false);
        /* ⭐ pm_1542 §一（裁 · 一处定形）：拒答之**由** ⇒ 先引后端之 `verdict`（逐字之由 · 在而未被用）；
           缺 ⇒ 明书。⛔ 旧「（后端之辞 ⛔ 载入）」—— 其义反（后端之辞**恰已载入** · 承「说一用一」）。
           二支共用 `_why`（⛔ 二处各写）。 */
        const _verdict = (typeof g.verdict === 'string') ? g.verdict.trim() : '';
        const _why = _verdict ? ('后端判词：' + _verdict) : '后端未给逐字之由（唯 canonical）';
        const _r = (_isRefusal ? _canon : _ans)
          + '\n\n（判据 /v9/pa/ask ｜ 检索面 '+((g.scope||[]).join(' / ')||'—')
          + ' ｜ 实搜 '+g.searched+' 件 ｜ 阈值 '+g.threshold+' ｜ 读数 '+g.read_at+'）'
          + '\n⛔ 本问未进模型：'
          + (_isRefusal ? '库里无依据，按「有据才答」不答' : '本机账无此条 ⇒ 如实不答')
          + ' · ' + _why
          + ' · 见「判据」行。';
        /* ⭐ pm_1539 §二.1 ／ pm_1543 §二.⒜（承 pm_1483 §一 之同法 · 一处定形）：拒答轮**⛔ 经模型**
           （本机无据 ⇒ 未调用模型）⇒ 自落己标 ⇒ 屏上走径行为「本机无据（拒答 · 未调用模型）」，
           ⛔ `paRouteLine(null)` 之「src: —（后端未给）」伪行（该轮本无模型之径 ⇒ 无回执可给）。
           `kind:'self'` ⇒ ⛔ 入远端集 ⇒ 「出机」标 ⛔ 上（本机拒答**未出机**）。`at` 取后端之 `read_at`。 */
        try{ window.PASelfRouteLast = {
          label: {text: 'src: 本机无据（拒答 · 未调用模型）', key: '拒答', kind: 'self', model: ''},
          at: String(g.read_at || ''), url: '/v9/pa/ask'}; }catch(e){}
        addMsg('assistant', _r);
        paRun.receipt = await recordPaTurn(t.id, text, _r,   /* 拒答也要**真落盘**（照样拿回执）· ⭐ 并带源标（pm 1184 §一.⒝） */
          {origin:'refused', grounded:false, answer_source:(g.answer_source||'refused')});
        paSetState('done');
        return;
      }
      if(g && g.grounded){ paRun.evidence = g.evidence || [];      /* 有据：出处留给上下文面 */
        /* ⭐ pm 1184 §一.⒝：**有据之答**之档行源标（＝ pm 1184 §二 之表）⇒ 随本轮之 /v9/pa/dialog 带上 */
        _askMeta = {origin:'grounded', grounded:true, answer_source:(g.answer_source||'')}; }
    }
    if(cfg.chan==='pa') await sendPA(text, t, _askMeta);
    else { await startPlan(text); await sendAgent(t, text); }
  } finally {
    setBusy(false); paRun.busy = false; paRun.threadId = null;
    /* P9 · BUG-1（判据＝PM 006）：⛔ 不许无条件说「已落盘」——
       只有**后端回执**证明「会话 +行 ∧ events +1」才许说；否则**明说没落盘**。
       为什么：旧代码在 finally 里无条件加这句，而它只调了 saveState()（localStorage）
       ⇒ 后端一个字节没动却显示「已落盘」= 假绿（PM 实测：events/ledger/dialog 四项全未变）。 */
    try{
      saveState();
      const rc = paRun.receipt;
      if(rc && rc.recorded){
        addLog('💾 本轮已落盘（后端回执：会话 '+(rc.session_lines_before!=null?rc.session_lines_before:rc.session_lines)
               +'→'+(rc.session_lines_after!=null?rc.session_lines_after:rc.session_lines)+' 行 · events '
               +rc.events_lines_before+'→'+rc.events_lines_after+' 行 · '+(rc.session_path||'')+'）','ok',true,'P9 BUG-1');
      }else if(rc && (rc.events_readable===false || rc.session_readable===false)){
        /* P9 · BUG-1 补（2026-09-29 · PM 裁「该修」）：**读数不可得 ≠ 没落盘**。
           承「0 看起来像读数」：后端读不到文件时行数给的是 null（⛔ 不是 0）⇒ 前端必须
           **分开说** —— ⛔ 不许把「读不了」说成「没保存」，也⛔ 不许说成「已保存」。 */
        addLog('⚠ 本轮落盘读数不可得：后端读不到'+(rc.events_readable===false?'事件文件':'会话文件')
               +'（events_readable='+rc.events_readable+' · session_readable='+rc.session_readable
               +'）—— ⛔ 既不等于已保存，也不等于没保存','warn',true,'P9 BUG-1');
      }else{
        addLog('⚠ 本轮未落盘：后端无回执或无变化'+(rc?('（'+JSON.stringify(rc).slice(0,220)+'）'):'（未取得回执）')+' —— ⛔ 不等于已保存','warn',true,'P9 BUG-1');
      }
    }catch(e){}
    // 收尾：仍停在「进行中」的态 ⇒ 视为完成；失败/停止已由各自分支置位（不覆盖）
    if(['running','model','tool','verifying'].indexOf(paRun.state)>=0) paSetState('done');
  }
}
/* 聊天模式：PA 通道（不出手，纯商量） */
async function sendPA(text, t, meta){
  try{
    paSetState('model', '等待 PA 模型回复');   // 批159：请求发出到响应之间 = 等待模型
    paRunSrc='POST /v9/pa/dialog';   /* 裁③：真源标识 */
    /* ⭐ pm 1184 §一.⒝（承 pm 1183 §五.3 ／ TD 1056 §五）：**源标三键**随本轮带上 ——
       `origin` ／ `grounded` ／ `answer_source`（后端 `/v9/pa/dialog` 已认 `origin` 之键）。
       ⚠ 知其实方传（闸判有据 ⇒ grounded）；未知 ⇒ **不发键** ⇒ 后端落其默认 `model`（⛔ 前端冒真）。 */
    /* ⭐⭐ pm_1807 §一.3（PM 之裁 · 一行 · 本域）：**陪伴路须自带场合** —— 旧形无 `mode`
       ⇒ 后端 `pa_mode_name(None)` 归一为 `work` ⇒ ⭐ 陪伴通道拿到「**办事**」之场合栏
       ＝ 「页曰『陪伴』而提示曰『办事』」之根（技术总监一手逮 · `1805 §四.1`）。
       ⛔ 改后端缺省（「缺省 ＝ `work`」是**已明书之契约** · `selfdesc.js:2860` ⇒ 改之 ＝
       **静默改所有旧调用者之行为**）。
       ⭐ 值取**一处之源** `window.paChatMode()`（＝ `selfdesc.js` 之 `eff()` ＝ 由**通道**定：
          本路唯 `chan:'pa'` 可达 ⇒ `companion`）；旧页无该件 ⇒ **回落 `'chat'`**
          （＝ PM 之逐字裁；后端 `pa_mode_name` 亦归一为 `companion`）。
       ⭐ 二处同源：`selfdesc.js` 之 `wrapFetch` 见体已有 `mode` ⇒ **⛔ 覆**（幂等）。 */
    const _b = {user_id:curUser(), session_id:t.id, text:text, topic:null,
                mode: (typeof paChatMode === 'function' ? paChatMode() : 'chat')};
    /* ⭐ pm_1465 §二.1（说一用一）：本轮之模型 ⇒ **取用户所选**（自后端之表出 · `paModelSel` **一处出**）
       ⇒ ⛔ 硬编字面；⛔ 在表（表 ⛔ 得 ／ 值非实名）⇒ **⛔ 带此键** ⇒ 后端落会话档 ∨ 默认。 */
    const _mdl = paModelSel(); if(_mdl) _b.model = _mdl;
    /* ⭐ pm_1492 §二.1（通电 · 一处出）：本机事实族之标（⛔ 三处各判）—— 未得（旧页）⇒ ⛔ 带键 */
    try{ if(typeof paSelfFactFamily === 'function') _b.fact_family = paSelfFactFamily(text); }catch(e){}
    if(meta && typeof meta==='object'){
      if(meta.origin) _b.origin = String(meta.origin);
      if(meta.grounded===true || meta.grounded===false) _b.grounded = meta.grounded;
      if(meta.answer_source) _b.answer_source = String(meta.answer_source);
    }
    /* ⭐ pm_1853 §二.2ⓝ（承 pm_1847 §三）：附件之**本机端**：`attachments:[id]`（全部 · 本机指路）
       ⊕ `attach_out:[id]`（**逐件已勾** · 且类为「文」 ⇒ 方入体）—— 缺省 ⛔ 出机。
       ⛔ 前端自判（何者入体由 `core/pa/attach.py` 一处定形）。 */
    try{
      if(typeof paAttachIds === 'function'){
        const _ids = paAttachIds();
        if(_ids.length){ _b.attachments = _ids; _b.attach_out = paAttachOutIds(); }
      }
    }catch(e){}
    const r = await fetch(API+'/v9/pa/dialog', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(_b)});
    if(r.status===404){ addMsg('assistant','（PA 通道暂不可用：/v9/pa/dialog 未挂载）\n已记录：'+text+'\n（去处：确认服务版本 ∨ 看服务窗口之日志）'); paSetState('failed','PA 通道未挂载(404)'); return; }
    const d = await r.json().catch(function(){ return null; });
    /* ⭐ pm_1617 §二.2（令二 · 要）：不可用 ⇒ **因 ＋ 去处** —— 后端之人话（`LLM_UNAVAILABLE_TEXT`
       ＝「模型不可用：本机与云端皆未接（…）⇒ 请到「模型配置」配云端密钥，或装上本机模型。」
       · 已含因与去处）**逐字优先**；⛔ 唯书「失败」二字 ∧ ⛔ 裸异常上屏（原始因已入后端机器字段
       `last_error` · ⛔ 上屏 —— 承 TD `1612` 令三）。⛔ 前景 ⛔ 重说后端已书之因（免叠）。 */
    const _why = (d && (d.error || d.message)) ? String(d.error || d.message).trim() : '';
    if(!d || (!d.reply && _why)){
      addMsg('assistant', (_why || '（后端回执不可取：无回执 ∨ 体不可解）')
        + '\n（去处：设置 →「模型配置」配云端密钥 ∨ 装上本机模型；仍不成 ⇒ 看服务窗口之日志）');
      paSetState('failed', _why ? ('PA 通道：' + _why).slice(0, 48) : 'PA 通道无回复');
      return;
    }
    addMsg('assistant', d.reply || '（无回复）');
    /* ⭐ pm_2061 §三.1（物⒉ 禁辞之显形 · 面侧）：陪伴轴之回执若载 `channel.untrue_wording`
       ⇒ 渲**一处人话块**（⛔ 静默 · ⛔ 自造辞）；其工程之据入 `title`。端 ⛔ 给 ╱ 空表 ⇒ 一字 ⛔ 现。 */
    try{ paUntrueWordingRender(d); }catch(e){}
    paRun.receipt = d.persisted || null;   /* P9 · BUG-1：落盘回执**由后端给**，前端不复述 */
    paSetState('done');
  }catch(e){
    /* 令二：⛔ 裸异常 —— 逐字附「因（逐字）＋ 去处」。 */
    addMsg('assistant','PA 通道请求失败：'+((e && e.message) || e)
      + '\n（因：请求未达后端 ∨ 连接中断 · 见上字；去处：确认服务在跑 ∨ 看服务窗口之日志）');
    paSetState('failed','PA 通道请求失败（未达）');
  }
  loadSide();
}
/* PM-011（2026-09-30）· 响应**分型**：⛔ 不再拿一句话兜住所有载荷。
   现场（05:39）：「服务暂不可用」是 `d.error || 兜底` 兜出来的，而后端有**五种**载荷
   都不带 `error`：recovery.py:392 previous_done ／ :129 executing ／ :91 预算超限 ／
   entry.py:152 seed 门 block（有 reason 无 error）／ entry.py:99 seed_failed（有 message 无 error）
   ⇒ 五件不一样的事被压成同一句含糊话术。本函数**只分型，不写文案**（文案在各支里，便于判据逐支钉死）。 */
function paRespReason(d){
  return String((d && (d.error || d.reason || d.message)) || '').trim();
}
function paRespKind(d){
  if(d === null || d === undefined || typeof d !== 'object') return 'noreceipt';
  if(d.success === true) return 'ok';
  if(d.status === 'busy') return 'busy';
  const why = paRespReason(d);
  if(d.success === false) return (why || d.blocked === true) ? 'rejected' : 'noreceipt';
  /* 无 success 字段：受理类是真回执（后端说「已受理／已确认」），⛔ 不是失败 */
  if(d.status === 'executing' || d.status === 'previous_done' || d.plan_status) return 'accepted';
  return why ? 'rejected' : 'noreceipt';
}

/* P0 产品面：陪伴 → /v9/pa/dialog；办事 → /v9/agent/runs。
   旧 /v9/agent/chat SSE 已删；⛔ 复制发送体，唯按模式分流。
   执行中再聊：⛔ 与长 run 抢同一模型；落明确排队，等 run 终止再发。 */
function _paHasActiveRun(){
  try{
    if(typeof paRun !== 'undefined' && paRun && paRun.busy) return true;
    if(window.paWinLiveRuns){
      var rs = window.paWinLiveRuns() || [];
      for(var i=0;i<rs.length;i++){
        var st = String(rs[i].state || '');
        if(st === 'running' || st === 'queued') return true;
      }
    }
  }catch(e){}
  return false;
}
function _paQueueChat(text, t){
  window.__paQueuedChat = window.__paQueuedChat || [];
  window.__paQueuedChat.push({text:String(text || ''), thread:t});
  try{ if(typeof addMsg === 'function') addMsg('sys', '⏳ 手头任务执行中：这条已排队，等它结束再发；⛔ 不跟长 run 抢模型'); }catch(e){}
  try{ if(typeof window.paWinSay === 'function') window.paWinSay('执行中 · 已排队，结束后自动发'); }catch(e){}
}
function _paDrainChat(){
  var q = window.__paQueuedChat || [];
  if(!q.length || _paHasActiveRun()) return;
  var item = q.shift();
  try{ if(typeof addMsg === 'function') addMsg('sys', '▶ 手头任务结束，发排队中的话'); }catch(e){}
  try{
    if(typeof sendPA === 'function') Promise.resolve(sendPA(item.text, item.thread, {})).catch(function(){});
  }catch(e){}
}
setInterval(_paDrainChat, 1000);

async function sendAgent(t, userText){
  const _utext = (typeof userText === 'string') ? userText : '';
  let _chan = 'agent';
  try{
    const _m = (typeof MODES !== 'undefined' && state && MODES[state.mode]) ? MODES[state.mode] : null;
    if(_m && _m.chan) _chan = _m.chan;
  }catch(e){}
  if(_chan === 'pa'){
    if(_paHasActiveRun()){ _paQueueChat(_utext, t); return {queued:true}; }
    if(typeof sendPA === 'function') return await sendPA(_utext, t, {});
  }
  return await sendAgentViaRuns(t, _utext);
}

/* ===== P0-3：/v9/agent/runs 异步执行（work/dev） ===== */
function _paRunUuid(){
  try{ if(window.crypto && typeof crypto.randomUUID === 'function') return crypto.randomUUID(); }catch(e){}
  return 'pa-'+Date.now()+'-'+Math.random().toString(16).slice(2);
}
function _paRunTail(runId){
  return String(runId||'').slice(-8);
}
function _paRunReceiptLine(runId,secs){
  return '耗时 '+secs+' s · 本地模型 0 元 · run_id '+_paRunTail(runId);
}
function _paApplyRunState(d){
  const s=String((d&&d.state)||'');
  if(s==='queued') paSetState('queued','排队第'+(Number((d&&d.position)||1)||1));
  else if(s==='running') paSetState((d&&d.cancel_requested)?'stopping':'running',(d&&d.cancel_requested)?'停止中…':'执行中');
  else if(s==='done') paSetState('done');
  else if(s==='failed') paSetState('failed',String((d&&d.error)||'失败').slice(0,60));
  else if(s==='cancelled') paSetState('cancelled','已取消');
}
async function _paPollRun(runId,t,userText){
  let delay=500;
  while(true){
    let r,d;
    try{
      r=await fetch(API+'/v9/agent/runs/'+encodeURIComponent(runId)+'?after_seq='+encodeURIComponent(paRun.afterSeq||0),{cache:'no-store'});
      d=await r.json().catch(function(){return null;});
    }catch(e){
      addMsg('assistant','⚠ 执行轮询失败：'+((e&&e.message)||e));
      paSetState('failed','轮询失败'); return;
    }
    if(!r.ok || !d || d.ok===false){
      const _e=(d&&(d.error||d.code))||('HTTP '+r.status);
      addMsg('assistant','❌ 执行状态查询失败：'+_e);
      paSetState('failed',String(_e).slice(0,60)); return;
    }
    paRun.afterSeq=Number((d.next_after_seq!=null?d.next_after_seq:paRun.afterSeq)||0);
    _paApplyRunState(d);
    const st=String(d.state||'');
    if(st==='done'){
      let content='';
      const out=d.output||{};
      if(out && typeof out==='object') content=String(out.content||'');
      else if(typeof out==='string') content=out;
      const _rid=String(d.run_id||runId);
      const _secs=Math.max(0,Math.round((Date.now()-(paRun.startedAt||Date.now()))/1000));
      const _rcpt=_paRunReceiptLine(_rid,_secs);
      let _seatsOut=[];
      if(out && Array.isArray(out.seats)) _seatsOut=out.seats;
      if(_seatsOut.length){
        addMsg('assistant','各席结论：\n'+_seatsOut.map(function(s){
          return '· '+String((s&&s.seat)||'')+'：'+String((s&&s.content)||'').slice(0,300);
        }).join('\n'),false,null,paRunTid());
      }
      if(content){
        addMsg('assistant',content+'\n\n—— '+_rcpt,false,null,paRunTid());
        try{ detectOutputs(content).forEach(renderOutputCard); }catch(e){}
        /* 回执：每 run 仅落一次（刷新恢复的终态不进来；此处 guard 防重复） */
        if(paRun._receiptRunId!==_rid){
          paRun.receipt=await recordPaTurn(t.id,userText,content,{origin:'local',run_id:_rid});
          paRun._receiptRunId=_rid;
        }
      }else{
        addMsg('assistant','✅ 执行完成（后端无文本输出）\n—— '+_rcpt);
      }
      paSetState('done','耗时 '+_secs+'s · 本地 0 元 · run_id '+_paRunTail(_rid));
      paRun.runId=null; paRun.afterSeq=0; return;
    }
    if(st==='failed'){
      const _why=String(d.error||''), _code=String(d.code||'');
      const _tail=_paRunTail(d.run_id||runId);
      addMsg('assistant','❌ 执行失败'+(_code?('（'+_code+'）'):'')+'：'+(_why||'（后端未给原因）')+'\n（run_id 尾 '+_tail+'）');
      paSetState('failed',(_why||'执行失败').slice(0,60)); paRun.runId=null; return;
    }
    if(st==='cancelled'){
      const _tail=_paRunTail(d.run_id||runId);
      addMsg('assistant','⏹ 执行已取消：'+String(d.reason||'用户停止')+'\n（run_id 尾 '+_tail+'）');
      paSetState('cancelled','已取消'); paRun.runId=null; paRun.afterSeq=0; return;
    }
    await new Promise(function(res){ setTimeout(res,delay); });
    delay=1000;
  }
}

/* ===== P0-4b：刷新恢复 lastRun（run_id/session_id/at） ===== */
function _paThreadForSession(sid){
  try{ if(typeof activeThread==='function'){ const a=activeThread(); if(a && a.id===sid) return a; } }catch(e){}
  try{
    if(typeof state!=='undefined' && state && state.threads){
      for(let i=0;i<state.threads.length;i++){ if(state.threads[i] && state.threads[i].id===sid) return state.threads[i]; }
    }
  }catch(e){}
  return {id:sid, msgs:[]};
}
function _paRestoreRead(){
  try{
    const raw=localStorage.getItem(PA_LAST_RUN_KEY);
    if(!raw) return null;
    const d=JSON.parse(raw);
    return (d && d.run_id) ? d : null;
  }catch(e){ return null; }
}
async function paRestoreLastRun(){
  if(typeof PA_RUN_API!=='undefined' && Number(PA_RUN_API)===0) return;
  const rec=_paRestoreRead(); if(!rec || !rec.run_id) return;
  try{
    const r=await fetch(API+'/v9/agent/runs/'+encodeURIComponent(rec.run_id),{cache:'no-store'});
    if(r.status===404){
      try{ localStorage.removeItem(PA_LAST_RUN_KEY); }catch(e){}
      return;                                  // 未知/404 ⇒ 清 key
    }
    const d=await r.json().catch(function(){return null;});
    if(!r.ok || !d || d.ok===false) return;    // 其他错误：留 key，下次刷新再试
    paRun.runId=rec.run_id; paRun.afterSeq=0; paRun.threadId=rec.session_id || '';
    paRunSrc='GET /v9/agent/runs/'+rec.run_id+'（刷新恢复）';
    _paApplyRunState(d);
    if(d.state==='queued' || d.state==='running'){
      const t=_paThreadForSession(rec.session_id);
      if(!paRun.startedAt) paRun.startedAt=Date.now();
      await _paPollRun(rec.run_id,t,'');       // queued/running ⇒ 续 poll
    }
    /* done/failed/cancelled：仅状态行显示上次终态，⛔ 重复 addMsg/recordPaTurn */
  }catch(e){ /* 网络未达：留 key，下次刷新再试 */ }
}

function _paRunsContextTask(t,userText){
  /* P1-2：最近 8 条 user/assistant；排除当前 userText 重复；每条截 800 字；当前任务保留。 */
  const cur=String(userText||'');
  let msgs=[];
  try{
    msgs=((t&&t.msgs)||[]).filter(function(m){
      return m && (m.role==='user' || m.role==='assistant');
    }).filter(function(m){
      return !(m.role==='user' && String(m.content||'').trim()===cur.trim());
    }).slice(-8);
  }catch(e){ msgs=[]; }
  const lines=msgs.map(function(m){
    const role=(m.role==='user')?'老板：':'PA：';
    return role+String(m.content||'').slice(0,800);
  }).filter(function(x){ return x.replace(/^(老板：|PA：)\s*/, '') !== ''; });
  const tail='【当前任务】'+cur;
  /* 本地小模型对「老板/PA」相对称谓易答成 PA ⇒ 有上下文时明示「老板即用户」；当前任务原文保留 */
  const hint=lines.length ? '\n（对话说明：老板即用户本人）' : '';
  return lines.length ? ('【最近对话（上下文）】\n'+lines.join('\n')+'\n'+tail+hint) : tail;
}
function _paRunsIsMultiSeat(text){
  return /^\s*(?:多席|seats)\s*[:：]/i.test(String(text||''));
}
function _paRunsParseSeats(text){
  /* P2-5：用户输入前缀「多席:PM,PD 」/「多席：PM,PD 」/「seats:PM,PD 」⇒ seats，task 去前缀。 */
  const s=String(text||'');
  const m=s.match(/^\s*(?:多席|seats)\s*[:：]\s*([A-Za-z,\s，]+?)(?:\s+|$)([\s\S]*)$/i);
  if(!m) return {seats:[], task:s};
  const allowed={PM:1,PD:1,CW:1,TD:1}, seats=[];
  m[1].split(/[,，\s]+/).forEach(function(x){
    const seat=String(x||'').trim().toUpperCase();
    if(allowed[seat] && seats.indexOf(seat)<0 && seats.length<3) seats.push(seat);
  });
  if(!seats.length) return {seats:[], task:s};
  return {seats:seats, task:String(m[2]||'').trim()};
}
async function sendAgentViaRuns(t,userText){
  const _cid=_paRunUuid();
  const _parsed=_paRunsParseSeats(userText);
  const _taskBase=_parsed.task;
  const _body={user_id:curUser(),session_id:t.id,task:_paRunsContextTask(t,_taskBase),client_request_id:_cid};
  if(_parsed.seats.length) _body.seats=_parsed.seats;
  const _mdl=paModelSel(); if(_mdl) _body.model=_mdl;
  paRun.runId=null; paRun.afterSeq=0; paRun.startedAt=Date.now(); paRun._receiptRunId=null;
  paRunSrc='POST /v9/agent/runs';
  paSetState('running','提交执行中…');
  try{
    const r=await fetch(API+'/v9/agent/runs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(_body)});
    const d=await r.json().catch(function(){return null;});
    if(r.status===429){ addMsg('assistant','⏳ 执行队列已满（queue_full）：稍后再试'); paSetState('failed','队列已满'); return; }
    if(!r.ok || !d || !d.ok || !d.run_id){
      const _why=(d&&(d.error||d.code))||('HTTP '+r.status);
      addMsg('assistant','❌ 提交执行失败：'+_why);
      paSetState('failed',String(_why).slice(0,60)); return;
    }
    paRun.runId=d.run_id;
    /* P0-4b：lastRun 供刷新恢复（终态/停止后保留，唯 404 清） */
    try{ localStorage.setItem(PA_LAST_RUN_KEY, JSON.stringify({run_id:d.run_id,session_id:t.id,at:Date.now()})); }catch(e){}
    _paApplyRunState(d);
    await _paPollRun(d.run_id,t,_taskBase);
  }catch(e){
    addMsg('assistant','⚠ 提交执行失败：'+((e&&e.message)||e));
    paSetState('failed','提交失败');
  }
}
async function paCancelRun(runId){
  paRunSrc='POST /v9/agent/runs/'+runId+'/cancel';
  try{
    const r=await fetch(API+'/v9/agent/runs/'+encodeURIComponent(runId)+'/cancel',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reason:'user_stop'})});
    const d=await r.json().catch(function(){return null;});
    if(!r.ok || !d || d.ok===false){
      addMsg('assistant','⚠ 停止请求失败：'+(((d&&(d.error||d.code))||('HTTP '+r.status)))); return;
    }
    paSetState('stopping','停止中…');
    addMsg('sys','⏹ 已发送停止请求：'+(d.cancel_requested?'等待执行收口…':'已取消'));
  }catch(e){
    addMsg('assistant','⚠ 停止请求失败：'+((e&&e.message)||e));
  }
}

/* ================== 附件（本机端 · pm_1853 §二.2ⓝ ／ 承 pm_1847 §三）==================
   约：① 取件复用**原生** `<input type=file multiple>`（⛔ 桥、⛔ 自造选件器）；
       ② 唯送本机端 `POST /v9/pa/attach`（`multipart` · 字段 `files`）；
       ③ 逐件勾（**默认关**）且仅「文」可入体 —— 图 ／ 档恒 ⛔ 入体（唯本机指路）；
       ④ 明书：已勾 ⇒ 「此件内容将随本轮出机」；未勾 ⇒ 「只给本机指路」。
   ♠ ⛔ 绝对径上屏（唯名 ＋ 类 ＋ 字节 ＋ sha16）。本模块之表片名用 ASCII（⛔ 中文标识符）。 */
var PA_ATTACH_URL = '/v9/pa/attach';
var paAttachRecs = [];        /* [{id, name, bytes, sha16, kind, path, out}] */
var paAttachBusy = false;

function paAttachPick(){
  try{ var f = document.getElementById('paAttachFiles'); if(f){ f.value = ''; f.click(); } }catch(e){}
}
function paAttachIds(){ return paAttachRecs.map(function(r){ return r.id; }); }
function paAttachOutIds(){
  return paAttachRecs.filter(function(r){ return r.out === true && r.kind === '文'; })
    .map(function(r){ return r.id; });
}
function paAttachClear(){ paAttachRecs = []; paAttachRender(); }
function paAttachToggle(id, on){
  for(var i = 0; i < paAttachRecs.length; i++){
    if(paAttachRecs[i].id === id){ paAttachRecs[i].out = (on === true); }
  }
  paAttachRender();
}
async function paAttachOnPick(inp){
  if(paAttachBusy) return;
  var fs = []; try{ fs = Array.prototype.slice.call((inp && inp.files) || []); }catch(e){ fs = []; }
  if(!fs.length) return;
  var box = document.getElementById('paAttachList');
  if(box){ box.style.display = ''; box.textContent = '正在收下（唯本机 · 不外发）…'; }
  paAttachBusy = true;
  try{
    var fd = new FormData();
    for(var i = 0; i < fs.length; i++){ fd.append('files', fs[i], fs[i].name || '未名'); }
    var r = await fetch(((typeof API !== 'undefined') ? API : '') + PA_ATTACH_URL,
      {method: 'POST', cache: 'no-store', body: fd});
    var j = null; try{ j = await r.json(); }catch(e){ j = null; }
    var list = (j && j.ok && Array.isArray(j['附件'])) ? j['附件'] : null;
    if(!list){
      var why = (j && (j.error || j['因'])) ? String(j.error || j['因'])
        : ('端未答可读之果（HTTP ' + r.status + '）');
      if(box) box.textContent = '收不下：' + why;
      paAttachBusy = false;
      return;
    }
    for(var k = 0; k < list.length; k++){
      var a = list[k] || {};
      paAttachRecs.push({id: String(a['id'] || ''), name: String(a['名'] || ''),
                         bytes: a['字节'], sha16: String(a['sha16'] || ''),
                         kind: String(a['类'] || ''), path: String(a['落点'] || ''), out: false});
    }
    var skipped = (j && j['略']) || [];
    if(skipped.length && box){
      box.textContent = '有几件没收下：' + skipped.map(function(x){
        return String(x['名'] || '') + '（' + String(x['因'] || '') + '）'; }).join(' ／ ');
    }
  }catch(e){
    if(box) box.textContent = '收不下（' + ((e && e.message) || '连不上本机之端') + '）';
  }
  paAttachBusy = false;
  paAttachRender();
}
function paAttachRender(){
  var box = document.getElementById('paAttachList');
  if(!box) return;
  box.innerHTML = '';
  if(!paAttachRecs.length){ box.style.display = 'none'; return; }
  box.style.display = '';
  var head = document.createElement('div');
  head.textContent = '附件 ' + paAttachRecs.length + ' 件（已存本机 · 缺省不外发）';
  box.appendChild(head);
  paAttachRecs.forEach(function(r){
    var row = document.createElement('div');
    row.style.marginTop = '2px';
    var cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.checked = (r.out === true);
    cb.disabled = (r.kind !== '文');
    cb.setAttribute('title', (r.kind === '文')
      ? '勾上 ⇒ 此件内容将随本轮出机（发给云端模型）'
      : '类为「' + r.kind + '」⇒ 恒 ⛔ 入体（唯给本机指路）');
    cb.onclick = function(){ paAttachToggle(r.id, cb.checked); };
    row.appendChild(cb);
    var sp = document.createElement('span');
    sp.style.marginLeft = '4px';
    sp.textContent = r.name + '（' + r.kind + ' · ' + (r.bytes == null ? '—' : r.bytes) + ' 字节）'
      + (r.out ? ' —— 此件内容将随本轮出机' : ' —— 只给本机指路');
    row.appendChild(sp);
    box.appendChild(row);
  });
  var foot = document.createElement('div');
  foot.style.marginTop = '3px';
  var clr = document.createElement('span');
  clr.className = 'chip';
  clr.textContent = '清空';
  clr.onclick = function(){ paAttachClear(); };
  foot.appendChild(clr);
  box.appendChild(foot);
}
try{ window.paAttachPick = paAttachPick; window.paAttachOnPick = paAttachOnPick;
     window.paAttachIds = paAttachIds; window.paAttachOutIds = paAttachOutIds; }catch(e){}

/* P0-3：paStop 在 runs 路径必须 POST /v9/agent/runs/{id}/cancel（不能只 abort）；
   cards.js 之后加载，故在 DOMContentLoaded 后包装（旧 SSE 路径无 runId ⇒ 仍走原 paStop）。 */
(function(){
  function wrapStop(){
    if(typeof window.paStop === 'function' && !window.paStop.__paRunsWrapped){
      var _orig = window.paStop;
      window.paStop = function(){
        var _rid = (typeof paRun !== 'undefined' && paRun && paRun.runId) ? String(paRun.runId) : '';
        var _flag = (typeof PA_RUN_API === 'undefined') ? 1 : Number(PA_RUN_API);
        if(_rid && _flag !== 0){ paCancelRun(_rid); return; }
        return _orig.apply(this, arguments);
      };
      window.paStop.__paRunsWrapped = true;
    }
  }
  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded', function(){ setTimeout(wrapStop, 0); });
  }else{ setTimeout(wrapStop, 0); }
  try{ window.__paRunsWrapStop = wrapStop; }catch(e){}
})();

/* P0-4b：页面初始化恢复 lastRun（终端/未知在 paRestoreLastRun 内处理）。 */
(function(){
  function init(){
    if(typeof PA_RUN_API !== 'undefined' && Number(PA_RUN_API)===0) return;
    if(typeof paRestoreLastRun === 'function'){ setTimeout(paRestoreLastRun, 0); }
  }
  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded', function(){ setTimeout(init, 0); });
  }else{ setTimeout(init, 0); }
  try{ window.paRestoreLastRun = paRestoreLastRun; }catch(e){}
})();
