/* ---- 启动 ---- */
(async function(){
  // 批171 · 入口可达性：**恢复上次模式**（此前 pa_state 只写不读 ⇒ 「记住选择」实际不生效，
  // 每次刷新都回到「聊天=不出手」⇒ 用户以为"没有能执行任务的入口"）。线程自己的 mode 优先（切换线程时会再 setMode）。
  try{
    const _saved = JSON.parse(localStorage.getItem('pa_state')||'{}');
    if(_saved && MODES[_saved.mode] && MODES[_saved.mode].on){ state.mode = _saved.mode; }
  }catch(e){}
  await loadThreads();
/* 批189 · #2：PA 单线程 ⇒ 启动时收敛为**唯一会话**（保留最近活跃那条，其余留在后端作只读历史） */
function paCollapseToSingleThread(){
  try{
    if(!state.threads || !state.threads.length) return;
    if(state.threads.length > 1){
      const keep = state.threads.find(function(x){ return x.id===state.activeThread; }) || state.threads[0];
      /* 批219·A 修（老板报「刷新后旧会话没了」的真凶）：旧代码 state.threads=[keep] 是**内存+写盘同时硬裁**
         ⇒ 被裁会话**直接丢失**。单线程口径**不等于**要丢数据 ⇒ 一律**先归档再收敛**。 */
      const _drop = state.threads.filter(function(x){ return x.id!==keep.id; });
      state.archived = (state.archived||[]).concat(_drop.map(function(x){ return Object.assign({}, x, {archived_at:new Date().toISOString()}); }));
      state.threads = [keep]; state.activeThread = keep.id; saveState();
      console.log('[PA_SINGLE_THREAD] 会话数收敛为 1（保留 ' + keep.id + '，归档 ' + _drop.length + ' 条不删除）');
    }
  }catch(e){}
}
  paCollapseToSingleThread();
  /* W-08：收敛之后再测一次（读的是收敛后的实际体积）；走 _boot ⇒ 失败也 fail-loud（批192 口径）。 */
  _boot("paQuotaGuard", PA_FACES.guard("archive", paQuotaGuard));
  _boot("paMigrateArchiveToServer", PA_FACES.guard("archive", paMigrateArchiveToServer));   /* X-11 层 1：有正文才动作；先保底导出；服务端确认读回才改本地 */
  /* 批192 · 缺陷修：启动步骤**逐步 fail-loud** —— 一个 null 写入（如 #threadList）曾静默中断整段启动，
     且因是 promise rejection 而页内无感。现在每步独立捕获并显式报告（控制台 + 页面内 sys 消息）。 */
  function _bootErr(step, e){
    try{ console.error("[PA_BOOT] " + step + " 失败：" + ((e && e.message) || e)); }catch(_e0){}
    try{ addMsg("sys", "⚠ 启动步骤「" + step + "」失败：" + ((e && e.message) || e)); }catch(_e1){}
  }
  function _boot(step, fn){
    let r = null;
    try{ r = fn(); }catch(e){ _bootErr(step, e); return; }
    if(r && typeof r.catch === "function"){ r.catch(function(e){ _bootErr(step, e); }); }
  }
  _boot("panels", PA_FACES.guard("drawer", paApplyPanels));   /* 批193：先应用折叠状态，避免加载后跳一下 */
  _boot("renderModes", PA_FACES.guard("shell", renderModes));
  _boot("renderThreads", PA_FACES.guard("chat", renderThreads));
  _boot("setMode", PA_FACES.guard("chat", function(){ setMode(state.mode); }));
  _boot("syncPaSession", PA_FACES.guard("session", syncPaSession));
  if(!(activeThread().msgs||[]).length){ addMsg('sys','PA v0.2 —— 聊天=就事论事（画像/审美/情感沉淀，不出手）｜工作=办公类 computer use｜项目开发=代码（高权限）。线程与项目文件已可用。'); }
  _boot("loadSide", PA_FACES.guard("profile", loadSide));
  _boot("loadFiles", PA_FACES.guard("files", loadFiles));
  _boot("loadCfg", PA_FACES.guard("config", loadCfg));
  _boot("renderKbPanel", PA_FACES.guard("session", renderKbPanel));
  _boot("renderCaliberPanel", PA_FACES.guard("caliber", renderCaliberPanel));   /* PM-011 · N1：口径面板接线（读/改/检 各一调用点） */
  _boot("renderPermPanel", PA_FACES.guard("authz", renderPermPanel));   /* PA-B1：授权面板接线（在场授权读/授/撤 ＋ 改档，各一调用点） */
  _boot("paKbPrime", PA_FACES.guard("session", paKbPrime));
  _boot("probeConn", PA_FACES.guard("status", probeConn));
  _boot("paLoadUiState", PA_FACES.guard("status", paLoadUiState));   /* 裁② · pm_990 §三：界面态快照只读上屏 */
  _boot("paLoadPesBlocks", PA_FACES.guard("cards", paLoadPesBlocks));   /* M2-A Step 3.1：阻断卡接只读投影（空库时静默，不渲染假卡） */
  _boot("paKeyInit", PA_FACES.guard("keys", paKeyInit));   /* pm_1652 令一（密钥面）：页面首载领令牌（唯 Cookie · ⛔ 值）＋ 读名册（唯 /v9/pa/providers） */
  setInterval(probeConn, 15000);
})();
