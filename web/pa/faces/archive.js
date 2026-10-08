/* ---- X-11 层 1：归档正文落服务端（老板/DS 2026-09-18 拍 A：Windows 起本机网关 + 端口 5102）------
   目的：**本地足迹与归档条数解耦** —— 归档正文搬到服务端 data/v9/pa/threads_<uid>.json，
   本地每条只留 5 键索引（id/title/archived_at/msg_count/server）。
   纪律（对应方案 §三；**每条都有测试判据**）：
   1. **不静默**：只搬「有正文且未标 server」的条目；没有就说没有（不假装搬过）；
   2. **先保底导出、再动数据**：迁移前**先落一份文件**当回滚锚点
      —— 上次的教训：没有基线 ⇒ 无法判定到底丢没丢数据；
   3. **服务端确认读回才改本地**：`ok && written >= n` 才替换；**否则本地一字不改**（不半途改）；
      服务端回 `ok` 但 written 不够 ⇒ **照样当失败**（假成交防线）；
   4. **只换正文、不删条目**：替换后 `state.archived` **条目数不变**（批221·A「不裁剪、不丢数据」）；
   5. **可回滚**：`PA_ARCHIVE_SERVER=false` ⇒ 整个迁移不跑（回旧的本地正文分支）；
   6. **不自动删除**：本区域**不得**出现 `.splice(`／`.pop(`／`.shift(`／`removeItem`／`setItem(`
      —— 唯一落盘出口是 `saveState()`（它有失败上报）。
   注：提示复用 `#paQuotaBanner`（页面唯一的可见横幅）——语义上是「存储相关提示」，**不影响 W-08 判据**。
      本区整段插在配额守卫区**之前**，不落在 W-08/W-09 的测试抽取区间内；为免抽取按字面量定位出错，
      这里**刻意不复述**那两个区块边界的原文（复述会把抽取起点提前到本注释，实测会让 6 条 W-08 判据变红）。 */
const PA_ARCHIVE_SERVER = true;                 /* 回滚位：置 false ⇒ 不迁移（回本地正文分支） */
const PA_ARCHIVE_API = '/v9/pa/archive';
const PA_ARCHIVE_INDEX_KEYS = ['id', 'title', 'archived_at', 'msg_count', 'server'];

function paArchiveHasBody(e){ return !!(e && Array.isArray(e.msgs) && e.msgs.length); }
function paArchiveIndex(e){
  /* 只出 5 键索引 —— **按 PA_ARCHIVE_INDEX_KEYS 构造**（键表本身是判据，不靠人手抄对）。
     **未知即未知**：archived_at 取不到就留 null，不兜底成「现在」。 */
  const src = {
    id: (e && e.id != null) ? e.id : null,
    title: (e && e.title != null) ? e.title : null,
    archived_at: (e && e.archived_at != null) ? e.archived_at : null,
    msg_count: (e && Array.isArray(e.msgs)) ? e.msgs.length : ((e && e.msg_count) || 0),
    server: true
  };
  const out = {};
  PA_ARCHIVE_INDEX_KEYS.forEach(function(k){ out[k] = src[k]; });
  return out;
}
function paArchivePending(){
  const ar = (state && Array.isArray(state.archived)) ? state.archived : [];
  const pend = ar.filter(function(e){ return paArchiveHasBody(e) && !(e && e.server); });
  return { items:pend, pending:pend.length, total:ar.length,
           withBody:ar.filter(paArchiveHasBody).length };
}
function paArchiveBackupFile(){
  /* 保底导出（回滚锚点）：**落成文件**——不写 localStorage（写本地正是要解决的问题）。 */
  try{
    const blob = new Blob([JSON.stringify(state, null, 1)], {type:'application/json'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'pa_state_premigrate_' + Date.now() + '.json';
    document.body.appendChild(a);
    a.click();
    setTimeout(function(){ URL.revokeObjectURL(url); }, 1000);
    return a.download;
  }catch(e){ return null; }
}
function paArchiveMigrateFail(msg, backup){
  const full = '⚠ ' + msg + '（本地未改，正文仍在本地）'
    + (backup ? '；已先存回滚文件 ' + backup : '；回滚文件未生成，请先手动导出 pa_state');
  try{ console.warn('[PA][ARCHIVE_SERVER] ' + full); }catch(_e1){}
  try{ paQuotaNotice(full); }catch(_e2){}
  try{ addMsg('sys', full); }catch(_e3){}
  return full;
}
async function paMigrateArchiveToServer(){
  if(!PA_ARCHIVE_SERVER) return { skipped:'switch_off' };
  const p = paArchivePending();
  if(!p.pending) return { pending:0, withBody:p.withBody, total:p.total, backup:null, migrated:0 };
  const backup = paArchiveBackupFile();          /* **先**落回滚锚点 */
  const items = p.items.map(function(e){
    return { id:e.id, title:(e.title != null ? e.title : null),
             archived_at:(e.archived_at != null ? e.archived_at : null),
             msgs:e.msgs, plan:(e.plan === undefined ? null : e.plan) };
  });
  let r = null;
  try{
    const resp = await fetch(API + PA_ARCHIVE_API, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ user_id:curUser(), items:items })
    });
    r = await resp.json();
    if(!resp.ok || !r || r.ok !== true) throw new Error((r && r.error) || ('HTTP ' + resp.status));
  }catch(err){
    const full = paArchiveMigrateFail('归档正文迁移失败：' + ((err && err.message) || err), backup);
    return { error:full, migrated:0, pending:p.pending, backup:backup };
  }
  if(!(r.written >= items.length)){               /* 假成交：说 ok 但写的条数不够 */
    const full = paArchiveMigrateFail('归档正文迁移未完成：服务端回执 written=' + r.written
      + ' < 应写 ' + items.length, backup);
    return { error:full, migrated:0, pending:p.pending, backup:backup };
  }
  const ids = {};
  items.forEach(function(it){ ids[String(it.id)] = true; });
  state.archived = (state.archived || []).map(function(e){
    return (e && ids[String(e.id)]) ? paArchiveIndex(e) : e;   /* **只换内容，不增不减** */
  });
  saveState();
  const done = '✅ 归档正文已迁移到服务端（本地只留索引）：' + items.length + ' 条'
    + '；回滚文件 ' + (backup || '（未生成）');
  try{ console.log('[PA][ARCHIVE_SERVER] ' + done); }catch(_e1){}
  try{ addMsg('sys', done); }catch(_e2){}
  return { migrated:items.length, pending:0, backup:backup, total:(state.archived || []).length };
}
/* ---- W-08 · 产品侧配额守卫（老板 2026-09-18 拍：W-08/W-09/W-10 三件提级、同批、各自版本内）------
   现场实测根因：`pa_state` 撑到配额上限 ⇒ `setItem` 抛 `QuotaExceededError` ⇒ **写入被拒**
   ⇒ 刷新后读不到 ⇒ 用户看到的是「消息日志消失」（不是渲染问题，是**存储写入失败**）。
   三条纪律：
   1. **阈值是常量**（`PA_QUOTA_GUARD_BYTES`，便于调）：不散落魔数；
   2. **只提示、不自动删**：老板 批221·A 已拍「归档不设上限、不裁剪（不丢数据优先）」
      ⇒ 裁剪规则**仍属老板判断**（W-09）⇒ 本函数**不删任何数据**，只做可见性 + 计数 + 指向既有导出出口；
   3. **不静默、也不吵**：超限 / 写入已被拒 ⇒ 进 UI（W-10：原实现只有 console.warn，
      写 `#modeHint` 又会被 setMode 重画覆盖 ⇒ 用户看不到）。
   **不推断**：只报可从数据算出的数（字节、归档条数）；**不写「还能撑几天」**这类估算。 */
const PA_QUOTA_GUARD_BYTES = 4 * 1024 * 1024;   /* 4 MiB：浏览器 ~5 MB 上限之前提前告警 */
/* W-09 按条数提示阈值（唯一常量）。老板/DS 2026-09-18 拍：**维持 100**
   （早提示更安全 / 零行为变化 / 已提为常量便于调）。
   ⚠ 口径：**主判据是字节**（PA_QUOTA_GUARD_BYTES），条数与字节**不对应** ⇒ 本条只是**辅助**提示。 */
const PA_ARCHIVE_HINT_COUNT = 100;              /* W-09 按条数提示：归档到这条线就在横幅里提醒（**只提示**，不裁剪） */
let PA_LAST_SAVE_BYTES = null;                  /* 上次写盘的字节数（模块变量：**不进 state**，不给存档增重） */
function paQuotaBytes(raw){
  /* 口径＝**UTF-8 字节**（与测试侧/DSH 线口径对齐，便于对账）。
     如实标注：浏览器 DOM storage 配额口径并不公开保证按 UTF-8 计 ⇒ 本值只作**提前告警的近似**，
     真值以 setItem 是否抛 QuotaExceededError 为准。 */
  try{ if(typeof TextEncoder !== 'undefined') return new TextEncoder().encode(raw).length; }catch(e){}
  return raw.length * 2;   /* 退化口径（无 TextEncoder）：UTF-16 码元 → 字节 */
}
function paQuotaUsage(){
  let raw = ''; try{ raw = localStorage.getItem('pa_state') || ''; }catch(e){ raw = ''; }
  const bytes = paQuotaBytes(raw);
  const archived = (state && Array.isArray(state.archived)) ? state.archived.length : 0;
  return { bytes:bytes, threshold:PA_QUOTA_GUARD_BYTES, over:bytes >= PA_QUOTA_GUARD_BYTES,
           archived:archived, saveError:(state && state._saveError) || null };
}
function paQuotaNotice(text){
  /* 只写专用横幅；**不写 #modeHint**（会被 setMode 重画覆盖）。text 走 textContent ⇒ 不注入 HTML。 */
  try{
    const banner = document.getElementById('paQuotaBanner');
    const span = document.getElementById('paQuotaText');
    if(!banner || !span) return false;
    span.textContent = text || '';
    banner.classList.toggle('show', !!text);
    return !!text;
  }catch(e){ return false; }
}
function paQuotaWarnText(bytes){
  const archived = (state && Array.isArray(state.archived)) ? state.archived.length : 0;
  return '⚠ 存储接近上限（'+bytes+' 字节 / 阈值 '+PA_QUOTA_GUARD_BYTES+'）：新建会话/归档可能不生效。'
       + '你可以：① 归档旧会话（先「导出归档 JSON」备份，导出不删数据）；② 清理历史。'
       + '当前已归档 '+archived+' 条（最早的可清理；本版不会自动删除 —— 裁剪规则待老板拍）。';
}
function paArchiveHintText(n){
  /* W-09 按条数提示：把「归档已经很多」变成**看得见**的一句（原实现只在 console + 线程消息里）。
     只报能算出的数（条数、可清理量），**不推断**「还能撑多久」。 */
  return '⚠ 本地归档已 '+n+' 条（提示阈值 '+PA_ARCHIVE_HINT_COUNT+' 条）：存储接近上限时新建会话/归档可能不生效。'
       + '你可以：① 「导出归档 JSON」备份（只读、不删数据）；② 「手动清理归档」（需要你二次确认，本版不会自动删除）。';
}
function paQuotaGuard(){
  /* 启动即测一次：**提前告警**，不等到写失败才发现（W-08）。 */
  const u = paQuotaUsage();
  try{ console.log('[PA][QUOTA] pa_state '+u.bytes+' 字节 / 阈值 '+u.threshold+'；archived '+u.archived+' 条'
                   + (u.saveError ? '；上次写入失败：'+u.saveError : '')); }catch(e){}
  if(u.saveError) return paQuotaNotice('⚠ 本地写入已被拒绝（'+u.saveError+'）。本次新内容刷新后可能不生效：'
       + '请先「导出归档 JSON」备份，再清理历史（本版不自动删）。');
  if(u.over) return paQuotaNotice(paQuotaWarnText(u.bytes));
  if(u.archived >= PA_ARCHIVE_HINT_COUNT) return paQuotaNotice(paArchiveHintText(u.archived));
  return paQuotaNotice('');
}
function saveState(){
  /* 批219 修：**写入失败必须上报**（原来静默 ⇒ 用户以为存了）。不用 addMsg（可能回调 saveState ⇒ 递归）。 */
  try{
    const _j = JSON.stringify(state);
    /* W-08 提前告警：**先廉价预筛再算字节**（saveState 在热路径上，每次 addMsg/工具行都会调）。
       UTF-8 字节数 ≤ 3 × UTF-16 码元数 恒成立 ⇒ `3*len < 阈值` 时真字节数必然也小于阈值
       （**不会漏报**），此时直接用码元数当保守下界，省掉一次全量编码。 */
    PA_LAST_SAVE_BYTES = (_j.length * 3 >= PA_QUOTA_GUARD_BYTES) ? paQuotaBytes(_j) : _j.length;
    localStorage.setItem('pa_state', _j); state._saveError=null;
  }
  catch(e){
    state._saveError=String(e).slice(0,140);
    try{ console.warn('[PA] 本地会话写入失败（刷新后可能丢失）:', e); }catch(_){}
    try{ const el=document.getElementById('modeHint'); if(el){ el.textContent='⚠ 本地存储写入失败：本次会话刷新后可能丢失'; } }catch(_){}
    /* W-10：失败提示**必须进 UI**（不只 Console）——专用横幅，不会被 setMode 重画覆盖。 */
    try{ paQuotaNotice('⚠ 本地写入已被拒绝（'+state._saveError+'）。本次新内容刷新后可能不生效：'
                       + '请先「导出归档 JSON」备份，再清理历史（本版不自动删除）。'); }catch(_){}
  }
  /* 接近阈值（但还没写失败）也要提前告警 */
  try{
    if(!state._saveError && PA_LAST_SAVE_BYTES != null && PA_LAST_SAVE_BYTES >= PA_QUOTA_GUARD_BYTES){
      paQuotaNotice(paQuotaWarnText(PA_LAST_SAVE_BYTES));
    }
  }catch(_){}
  syncThreads();
}
async function syncThreads(){ /* 批189 · #3：POST /v9/pa/threads 已关闭（单线程）⇒ 改为 no-op；状态落 localStorage（前端）+ 会话日志（后端权威） */ }
/* 批221 · DS-206-4：**读取侧容错解析** —— 整文件 JSON.parse 失败时抢救**第一段完整 JSON**（括号配平）。
   返回 {ok,data,salvaged,dropped,reason}；**失败不静默**（走降级分支）。 */
function paExportArchive(){
  /* 批221·A：导出**全部归档**为 JSON 文件（"不丢数据"的兜底交付物）。 */
  try{
    const blob = new Blob([JSON.stringify({exported_at:new Date().toISOString(), archived:state.archived||[], threads:state.threads||[]}, null, 1)], {type:'application/json'});
    const a=document.createElement('a'); a.href=URL.createObjectURL(blob);
    a.download='pa_archive_'+Date.now()+'.json'; document.body.appendChild(a); a.click();
    setTimeout(function(){ URL.revokeObjectURL(a.href); a.remove(); }, 1500);
    return true;
  }catch(e){ console.warn('[PA] 导出失败:', e); return false; }
}

/* ---- W-09 手动清理入口（老板 2026-09-18 拍：**不自动裁** + 手动清理 + 可导出回溯 ----
   为什么放在守卫区域**之外**：守卫（W-08/W-10）是**只读提示**，有静态判据钉死「不得出现任何删除动作」；
   删除只能走这里，且**唯一触发路径 = 老板点按钮**（无自动/定时/超限触发）。
   三条纪律：
   1. **先可回溯、再删**：确认框写明不可撤销 + 建议先「导出归档 JSON」；
   2. **一次只清最早 N 条**（PA_ARCHIVE_CLEAN_BATCH），**不提供「全清」** —— 全清不是清理，是丢数据；
   3. **删了什么要留痕**：被删项的 id / archived_at 记进消息日志（内容本身不可恢复，**不谎称可还原**）。 */
const PA_ARCHIVE_CLEAN_BATCH = 100;   /* 一次手动清理「最早 N 条」 */
function paArchiveStats(){
  /* 只读：给确认框与日志用的计数（不碰数据）。 */
  const total = (state && Array.isArray(state.archived)) ? state.archived.length : 0;
  const n = Math.min(PA_ARCHIVE_CLEAN_BATCH, total);
  return { total: total, remove: n, keep: total - n, batch: PA_ARCHIVE_CLEAN_BATCH };
}
function paArchiveCleanup(){
  try{
    const st = paArchiveStats();
    if(!st.total){ addLog('🧹 没有可清理的归档（0 条）', 'warn', true); return false; }
    const ok = window.confirm(
      '手动清理归档（不可撤销）' + String.fromCharCode(10) + String.fromCharCode(10)
      + '当前归档：' + st.total + ' 条' + String.fromCharCode(10)
      + '本次删除：最早的 ' + st.remove + ' 条' + String.fromCharCode(10)
      + '清理后保留：' + (st.keep ? ('最新 ' + st.keep + ' 条')
                          : '0 条（即全部归档，本次会清空归档）')
      + String.fromCharCode(10) + String.fromCharCode(10)
      + '建议先点「导出归档 JSON」备份（只读、不删数据）。' + String.fromCharCode(10)
      + '确认删除这 ' + st.remove + ' 条？'
    );
    if(!ok){ addLog('🧹 已取消手动清理（未删除任何数据）', 'warn', true); return false; }
    const removed = state.archived.slice(0, st.remove).map(function(x){
      return { id:(x && x.id) || null, archived_at:(x && x.archived_at) || null };
    });
    /* 只有老板在确认框里点了「确定」才会到这里 —— 这是全仓**唯一**的归档删除点。 */
    state.archived = state.archived.slice(st.remove);
    saveState();
    console.log('[PA][ARCHIVE] 手动清理最早 ' + st.remove + ' 条（保留 ' + st.keep + ' 条）：' + JSON.stringify(removed));
    addLog('🧹 已手动清理最早的 ' + st.remove + ' 条归档（保留 ' + st.keep + ' 条）。'
         + '⚠ 被删内容不可恢复；本条日志留有被删项的 id / 时间戳', 'warn', true);
    paQuotaGuard();   /* 清理后立刻复算并更新横幅 */
    return true;
  }catch(e){ console.warn('[PA][ARCHIVE] 手动清理失败:', e); return false; }
}
function paParseStateTolerant(raw){
  if(!raw || raw==='null'){ return {ok:false, data:null, reason:'本地记录为空'}; }
  try{ return {ok:true, data:JSON.parse(raw)}; }catch(e){}
  try{
    let depth=0, ins=false, esc=false, cut=-1;
    for(let i=0;i<raw.length;i++){
      const ch=raw[i];
      if(ins){ if(esc){esc=false;} else if(ch===String.fromCharCode(92)){esc=true;} else if(ch==='"'){ins=false;} continue; }
      if(ch==='"'){ ins=true; continue; }
      if(ch==='{'){ depth++; }
      else if(ch==='}'){ depth--; if(depth===0){ cut=i+1; break; } }
    }
    if(cut>0){ const d=JSON.parse(raw.slice(0,cut)); return {ok:true, data:d, salvaged:true, dropped:(raw.length-cut)}; }
  }catch(e2){}
  return {ok:false, data:null, reason:'本地记录解析失败（内容损坏）'};
}