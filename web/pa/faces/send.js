/* ---- 发送 ---- */
let abortCtrl=null;
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
    if(paLooksLikeKnowledgeQuestion(text)){
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

/* 工作/开发：执行通道（复用现有 /v9/agent/chat 循环） */
async function sendAgent(t, userText){
  /* P9 BUG-1 修 (2026-10-03): 本函数原本【没有】text 形参, 而出口回执那行引用了 text
     => ReferenceError: text is not defined => 被 catch 归成「连不上后端（网络不可达）」(归因错),
     且该轮【永不落盘】(/v9/pa/turn 未被调用). 修法: 显式收下 user_text; 续跑无新话时给空串. */
  const _utext = (typeof userText === 'string') ? userText : '';
  const cfg = MODES[state.mode];
  let sys = { chat:'你是老板的 PA。', work:'你是老板的 PA，工作模式：办公类 computer use（文档/表格/浏览器/图文/演示），工具用完汇报产物与待核实项。', dev:'你是老板的 PA，项目开发模式（权限最高）：处理代码与工程任务，明确每步做了什么与边界。' }[state.mode] || '你是老板的 PA。';
  sys += '\n[AI 标识] 凡你写稿/出件（write_file/wps_office/lingxi 之产物）⇒ 头须带一行显式标识「本内容由 AI 辅助生成」；⛔ 不得提供、执行或教任何「去标识」之功能。';
  const pl0 = planOf(t);
  if(pl0.steps && pl0.steps.length){ sys += '\n[任务计划] 按此顺序执行：'+pl0.steps.map((s,i)=>(i+1)+'.'+s.stage+':'+s.label).join(' ')+'。每步完成即汇报，交付前自查，不要跳过步骤。'; }
  const hist = (t.msgs||[]).filter(m=>m.role==='user'||m.role==='assistant').slice(-30).map(m=>({role:m.role, content:m.content}));
  const msgs = [{role:'system', content:sys}].concat(hist);
  abortCtrl = new AbortController();
  try{
    paSetState('model', '已提交，等待模型返回');   // 批159：请求发出 → 首个事件之前 = 等待模型
    paRunSrc='POST /v9/agent/chat';   /* 裁③：真源标识 */
    /* ⭐ pm_1465 §二.1：`model` ⇒ **用户所选**（**一处出** `paModelSel`）—— ⛔ 硬编 `deepseek-v4-flash`
       （旧硬编 ＝ 别名 ⇒ 与屏之实名**二形** ＝ 违「说一用一」· 承 pm_1447 §二.2 之正名）。 */
    const _ab = {user_id:curUser(), session_id:t.id, messages:msgs, stream:true};
    const _am = paModelSel(); if(_am) _ab.model = _am;
    const resp = await fetch(API+'/v9/agent/chat', {method:'POST', headers:{'Content-Type':'application/json'}, signal:abortCtrl.signal,
      body: JSON.stringify(_ab)});
    let d; const ct = resp.headers.get('content-type')||'';
    if(ct.includes('text/event-stream')) d = await readSSE(resp); else d = await resp.json();
    /* 批189 · #6：后端单活动 run ⇒ busy 要有中性文案（不是「失败」）*/
    if(d && d.status==='busy'){ addMsg('assistant','⏳ '+(d.reason||'已有任务正在执行（PA 单线程）')+'\n\n'+(d.hint||'')); paSetState('idle','已有任务在跑'); return; }
    /* PM-011-BLOCK-START */
    {
      const _kind = paRespKind(d);
      const _why = paRespReason(d);
      if(_kind === 'rejected'){
        /* ⓜ 后端明确拒绝 ⇒ 文案**必含后端原文** */
        addMsg('assistant','⛔ 后端拒绝本次任务：'+(_why||'（后端未给 reason）'));
        paSetState('failed', _why.slice(0,60));
        return;
      }
      if(_kind === 'noreceipt'){
        /* ⓝ 无回执 ⇒ **必说「未取得回执」**，⛔ 不得出现任何后端原文 */
        addMsg('assistant','⚠ 未取得回执：后端没有返回可读结果（⛔ 不等于「已保存」，也不等于「已失败」）—— 请重试，或把本次时刻发我查后端日志');
        paSetState('failed','未取得回执');
        return;
      }
      if(_kind === 'accepted'){
        /* 受理类：后端说「已受理」⇒ ⛔ 不许报成失败 */
        addMsg('assistant','ℹ️ 已被后端受理：'+(d.message||d.reply||'任务已接受')+'\n\n（⛔ 不是失败；结果稍后在下面对话里出现）');
        paSetState('running','已受理');
        return;
      }
    }
    /* PM-011-BLOCK-END */
    const msg = (((d.data||{}).choices||[])[0]||{}).message||{};
    if(msg.content){ addMsg('assistant', msg.content, false, null, paRunTid()); detectOutputs(msg.content).forEach(renderOutputCard);
      /* P9 · BUG-1：工作模式走 /v9/agent/chat（通用执行通道，不写 PA 记录）⇒ 这里补一条**真记录**并取回执 */
      paRun.receipt = await recordPaTurn(t.id, _utext, msg.content, {origin:'model', answer_source:'model'}); }   /* ⭐ pm 1184 §一.⒝：工作／开发路之模型答 ⇒ origin=model */
  }catch(e){
    /* PM-011 §五（PM 2026-09-30 裁）：⛔ 不许把 AbortError 与其他异常**一起静默吞掉** ——
       「静默吞异常」与「后端静默」同族：两者都让失败**看起来像什么都没发生**。
       中止 = `PA_STATE_DEF.stopped` 既有键，⛔ 不是失败。 */
    if(e.name==='AbortError'){
      addMsg('assistant','⏹ 本轮已中止（你点了「停止」／页面取消了这次请求）—— ⛔ 不等于失败，也⛔ 不等于已完成；要结果请重发。');
      paSetState('stopped','本轮已中止');
    } else {
      addMsg('assistant','⚠ 连不上后端（网络不可达）：'+e.message);
      paSetState('failed','连不上：'+e.message);
    }
  }
}
async function readSSE(resp){
  const reader=resp.body.getReader(); const dec=new TextDecoder(); let buf=''; let payload={success:true};
  const seen=new Set(); let sawDone=false; let _sawError=null; let _errShown=false; let _errMeta='';   // 批172：错误定位信息
  let _sawAsk=false;   // 批175：区分「ask 请示收尾」（正常）与「流被中断」——只有后者该落 failed
  while(true){
    const {done,value}=await reader.read(); if(done)break;
    buf+=dec.decode(value,{stream:true}); let i;
    while((i=buf.indexOf('\n'))>=0){
      const line=buf.slice(0,i).trim(); buf=buf.slice(i+1);
      if(!line.startsWith('data: '))continue;
      const raw=line.slice(6); if(raw==='[DONE]')return payload;
      let evt; try{evt=JSON.parse(raw);}catch(e){continue;}
      paRunSrc='SSE '+(evt.type||evt.status||'event')+' @/v9/agent/chat';   /* 裁③：取后端事件名为真源 */
      // 2026-09-13 修: 后端 type=error 此前被静默丢弃 —— 老板看到的是「进度刷一屏后什么都不发生」。
      // 实测事故: _v9_bridge_loop 抛 UnboundLocalError(长输出被 max_tokens 截断时触发) → 前端零提示、无交付。
      // 批159 · P0-2：心跳=「后端还活着」的证据 —— 重置无事件计时（此前 pa.html 完全忽略 heartbeat）
      if(evt.type==='heartbeat'){ paBeat(); continue; }
      if(evt.type==='error'){
        _sawError=String(evt.error||'未知错误');
        // 批172：错误必须**可定位** —— 带上 run_id / stage / 时刻（此前只有一句 Python 原文，
        // 报告给 DSH 也无法归因；后端本批已把 run_id/stage 放进 error 事件）。
        _errMeta=(evt.run_id? '（run_id='+evt.run_id+(evt.stage?(' · '+evt.stage):'')+'）' : '')
                 + '［'+new Date().toLocaleTimeString('zh-CN',{hour12:false})+'］';
        paSetState('failed', _sawError.slice(0,60));   // 批159：后端报错 ⇒ 8 态里的「已失败」
        paRunLog('⛔ 后端执行中断'+_errMeta+'：'+_sawError, 'err', true, 'SSE type=error');
        // 必须**当场**渲染：流尾常是 [DONE]，而 [DONE] 会让本函数提前 return，
        // 任何放在循环之后的收尾代码都不会执行(2026-09-13 浏览器实测发现)。
        if(!_errShown){
          _errShown=true;
          receipt('任务中断'+_errMeta+'：'+_sawError, 'err');
          // 批173 · 第2条拍板 ③：错误**默认折叠**（summary 带 stage+时刻；展开含完整文本 + run_id + 一键复制）
          addMsg('assistant', '⚠️ 任务中断（后端报错，不是没反应）'+_errMeta+'：'+_sawError, false,
            paErrBlockHtml(_errMeta, _sawError)+'<div style="margin-top:6px;color:#8b949e">可「再试一次」；若要我定位，展开上面折叠块并把 run_id 一起发我。</div>');
        }
        continue;
      }
      // 批153 · R2：PA 页写确认入口 —— 后端 write_pending 事件（无 type 字段，只有 status）
      // 此前 pa.html 没有消费者 ⇒ 从 PA 页发的带写任务会「停住但界面不说」。
      if(evt.status==='write_pending' && evt.pending_write){
        paSetState('approval', evt.reason_detail||evt.reason||'');   // 批159：等待审批
        renderPaWriteCard(evt.pending_write, evt.reason_detail||evt.reason||'');
        continue;
      }
      /* 批175 · 假失败修复（前端侧）：ask = 后端「请示收尾」，是**正常结束**，不是失败。
         后端 response_guard.py 的 ask 分支把 {status:'ask', ask:{question,options}} 放进终态载荷，
         bridge_call 再以 type=done 下发（工作台 chat.js 早已消费同一字段，PA 页此前完全没认 ⇒ 请示被显示成「❌ 已失败」）。
         状态键用既有的 approval（8 态契约锁定，不私自扩键）。 */
      if(evt.status==='ask'){
        _sawAsk=true;
        const _askQ=String((evt.ask&&(evt.ask.question||evt.ask.text))||evt.reason_detail||'').slice(0,80);
        paSetState('approval', '等待确认：'+_askQ);
        paRunLog('⏳ 等待老板确认（请示收尾）：'+_askQ, 'warn', true, 'SSE status=ask');
        paFlashApproval($("thread") && $("thread").lastElementChild);   /* 批193：请示到达也高亮最后一条 */
        if(evt.type!=='done') continue;   // 纯 ask 事件：等 done 载荷来时再走原有收尾
      }
      if(evt.type==='progress'||evt.type==='done'){
        // 批159：progress ⇒ 正在执行（有后端事件 = 没卡住）
        if(evt.type==='progress'){ paSetState('running'); }
        if(evt.type==='done'){ payload=evt; sawDone=true;
          /* 批189 · #5：压缩可见（后端在 done 载荷回传 compact）*/
          /* 批191 · #5 补完：压缩可见（后端在 _compress_messages 单源上报 ⇒ done 载荷带 compact）。
           反例硬化（老板新规则：关键改动必须跑反例样本）：dropped 必须是**数字**且在 (0, ∞) ——
           此前 `dropped > 0` 对 true / "3" 这类脏值也成立 ⇒ 会渲染「已压缩 true 条」。 */
        try{ const _ck=evt.compact; if(_ck && typeof _ck.dropped==='number' && isFinite(_ck.dropped) && _ck.dropped > 0){ addLog('🗜 已压缩 '+_ck.dropped+' 条上下文（保留 '+_ck.kept+' 条）','ok',true,'batch191 #5补完'); } }catch(e){}
          if(evt.status==='ask'){ /* 批175：请示收尾保持「等待确认」，不进入交付核验 */ }
          else if(evt.verify_verdict!==undefined){ paSetState('verifying'); }   // 批159：有核验结论 ⇒ 验证中
          // 核验结论（后端在 done payload 里给）：让「完成」不再黑盒
          if(evt.verify_verdict!==undefined){
            lastVerify={verdict:evt.verify_verdict, checked:evt.verify_checked,
                        failures:evt.verify_failures||[]}; } }
        let _stage=null;
        (evt.tool_steps||[]).forEach(s=>{ const k=s.round+':'+s.tool; if(seen.has(k))return; seen.add(k);
          const _sg=stageOf(s.tool);
          if(_sg!==_stage){ _stage=_sg; paRunLog('▶ 正在'+_sg+'…', 'stage', true); }
          // 2026-09-13：兜底从 s.tool（裸工具名）改为通用语义短语 ——
          // 老板看到「执行操作」远好于看到「browser_local」「wpp_render_full_deck」。
          const _sem=semanticStage(s.tool,s.arg,semanticCtx(s.tool,s.arg))||semanticArg(s.tool,s.arg)||ACTION_SEMANTIC[s.tool]||'执行操作';
          const _raw=s.tool+' '+String(s.arg||'').slice(0,60);
          const _res=(s.result&&typeof s.result==='object')?s.result:null;
          /* ⭐ pm_2061 §三.1⒝⒞（物⒈ 真迹）：回了什么（**唯取端之 `result`**）＋ 可否退（**唯照实**）。
             端 ⛔ 给回 ⇒ 摘要段 ⛔ 现（⛔ 造辞 ╱ ⛔ 补数）；其逐字回（前 120 字）入 `title`（工程之据之地）。 */
          const _stepSum=paStepSummary(s.result);
          const _stepSuf=(_stepSum ? (' · '+_stepSum) : '') + ' ' + paStepUndoText(s.tool);
          const _stepTip=_raw+((s.result!=null && String(s.result).trim())
                             ? (' ｜ 端之回（逐字 · 前 120 字）：'+String(s.result).replace(/\s+/g,' ').trim().slice(0,120))
                             : '');
          if(_res&&_res.blocked){
            /* M2-A · Step 3.1（语义修正）：阻断**不再借 `tool` 态**显示（设计稿 §2.3 三个不许之①）。
               事实来源 = 该次工具结果的 `reason` / `suggestion`（guard 原文，非前端编造）；
               `blocked_at` 传 null（后端未给 ⇒ 不显示本地时间，禁止前端造时刻）。 */
            paSetState('blocked', '已拦截外发（'+_sem+'）');
            paRunLog('⛔ 已拦截外发：'+(s.result.reason||'L4 隐私禁止'), 'err', true, _raw);
            addLog('💡 '+(s.result.suggestion||'脱敏后重试'), 'warn', true, _raw);
            paRenderCard('block', {block_id:'toolstep:'+_raw, blocked_at:null, layer:'Guard',
              reason:(s.result.reason||'L4 隐私禁止'), blocked_action:_sem, evidence_ref:null,
              unblock_hint:((s.result.suggestion&&String(s.result.suggestion).trim())?String(s.result.suggestion):null),
              state_map_key:'blocked'});
          }
          else if(_res&&_res.pending){ paSetState('approval', '等待授权：'+_sem); paRunLog('⏳ 等待授权：'+(s.result.reason||'需老板确认'), 'warn', true, _raw); }
          else if(_res&&paIsPreviewPending(_res)){
            // 批183 · C3：桥未就绪 = 可区分的**降级状态**（不是失败）⇒ 中性文案 + 就绪引导卡片；**不显示 ❌**
            const _vis=paPreviewPendingVisual(_res);
            paSetState('tool', '预览待 WPS 就绪（'+_sem+'）');
            paRunLog(_vis.icon+' '+_vis.text+'（'+_sem+'）', _vis.cls, true, _raw);
            paWpsReadyCardRender(s.tool, _res.hint, _vis.artifact, _vis);
          }
          // 批183 · C3：桥就绪（ready===true）⇒ 引导卡片自动消失
          else { paSetState('tool', '正在跑工具：'+_sem); paRunLog((s.success?'  ✅ ':'  ❌ ')+_sem+_stepSuf, s.success?'ok':'err', true, _stepTip); if(_res&&_res.ready===true) paWpsReadyCardClear(); }
          tickPlan(s.tool, s.arg, s.success); });
        if(evt.type==='done' && evt.status!=='ask') onTaskDone();   // 批175：请示不是交付 —— 跑交付核验会报「交付未经核验」= 新的假警报
      }
    }
  }
  if(!sawDone && !_sawAsk) onTaskDone();   // 批175：请示收尾不跑交付核验（同上）
  // 兜底：流被直接关断(没等到 [DONE]、也没有 done 事件)时也要说清楚，不能静默
  if(_sawError && !_errShown){
    _errShown=true;
    receipt('任务中断'+_errMeta+'：'+_sawError, 'err');
    addMsg('assistant', '⚠️ 任务中断（后端报错，不是没反应）'+_errMeta+'：'+_sawError, false,
      paErrBlockHtml(_errMeta, _sawError));
  } else if(!sawDone && _sawAsk){
    // 批175：ask 收尾 = 正常请示（后端同 run 已留 turn_end reason=ask）⇒ 不得落 failed
    receipt('本次是「请示收尾」：等老板确认后继续（不是失败）', 'warn');
  } else if(!sawDone){
    receipt('本次执行结束但没有交付结果（流被中断）', 'err');
    paSetState('failed', '流被中断（无 done 事件）');   // 批159
  }
  return payload;
}
/* 批153 · R2：写确认卡（PA 页）—— 三选项与工作台卡片统一：仅本次 / 一直允许 / 不允许。
   判据(体检项 114 检测清单 C1-C4)：结论必须由 HTTP 状态码 + 后端回执 + 产物共同支撑，
   前端文案只作待验证信号。always = 照做并写 grants.yaml（下次同场景免问）。
   实现见 cards.js:paWriteDecide ＋ 后端 grants.py（本文件不含实现 · 勿在此重复造器）。 */

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
  if(box){ box.style.display = ''; box.textContent = '正在收下（唯本机 · ⛔ 出机）…'; }
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
  head.textContent = '附件 ' + paAttachRecs.length + ' 件（已存本机 · 缺省 ⛔ 出机）';
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
