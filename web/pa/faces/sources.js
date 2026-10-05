/* ClawsJoy PA v3 · 来源声明（阶段 1 起步 · 承 pm_1033 §二 · CW b2a5182 · 2026-10-04）
   要旨：裁决轴从「问句像什么」换到「证据 ＋ 来源」。
   ⚠ 本件由 pa.html（**唯一壳 · 真源**）载入 —— ⭐ 承 pm 1203 §一（2026-10-05 · 副本 web/pa_v3.html 已删 · TD 716bc31）：旧「唯 v3 页载入 ⇒ 旧 pa.html ⛔ 受影响」之**界已反**（今唯 pa.html 一壳）（⛔ 动共用面件 chat.js ／ send.js ／ status.js ／ products.js ／ core.js）。
   ⚠ 本件 ⛔ 是面体（⛔ 注册进 pa/faces.json）—— 本件为**声明 ＋ 呈现层**。

   ⭐ 与问域判据（paAskDomain）之关系（pm_1033 §二 验收④ · 须写明）：
     paAskDomain 之判 ＝ **提示 ／ 加速**（预判该去哪一面取据），⛔ 闸 ——
     判 knowledge 只是「先去检索」；**未命中 ⇒ 回落模型**（承 pm_1032 §三.1）；⛔ 因判据拒答（承 L82）。

   四源（各：可用性 ／ 依据形 ／ 真源接口）——可用性須来自**真源**（⛔ 编）：
     ⓜ 本机自述 ⓝ 本机素材 ⓞ 模型 ⓟ 工具
   ⭐ 主面**按可用性呈现**（可用 ✓ ／ 部分可用 ／ 未接），⛔ 按问句呈现；未接者**明标未接**（承 pm_1024 §二 ／ L76）。
   ⭐ pm_1039 §三（2026-10-04）：本机素材之「依据形」改为**动态取真源**（面名 ＋ 逐面件数取 /v9/pa/ask 之
     scope ／ faces ／ searched）⇒ ⛔ 硬编「知识库 ＋ 收件箱」两类目录 ／ ⛔ 只报总数；并同步对账工具面（算径已通）。

   ⚠ 本件之读数：不自算 —— 模型之可用性取 web/pa/ui_state.json（本地在 ／ 远端态 ／ 远端因 ／ 刻）；
     检索面之命中率取 selfdesc.js 之留痕计数（真源 ＝ /v9/pa/ask 之返回）。
*/
const PA_SRC_DECL = [
  {k:'self', seq:'ⓜ', n:'本机自述', avail:'可用',
   by:'面册 ／ 工具流水 ／ 画像 ／ 权限档 ／ 界面快照（分节拼成 · 每节末行即其源）',
   src:'pa/faces.json ／ /v9/metrics/tool_flow ／ /v9/pa/context ／ /v9/pa/permission ／ /v9/pa/threads ／ /v9/pes/runs ／ pa/ui_state.json',
   note:'问「你 ／ 自我 ／ PA」之句 ⇒ 本面直答（⛔ 走检索 · ⛔ 调模型）'},
  {k:'local', seq:'ⓝ', n:'本机素材', avail:'部分可用',
   by:null,     /* ⭐ pm_1039 §三：本行改由 paSourceLocalBy() **动态取真源** ⇒ ⛔ 硬编目录名 */
   src:'/v9/pa/ask（grounded ／ evidence ／ searched ／ threshold ／ read_at）',
   note:'⚠ 逐面件数取真源（/v9/pa/ask 之 scope ／ faces ／ searched）：收件箱 ／ 知识库 ／ 文件 ／ 台账 ／ 台账·信通（后三面本批新接）；未接：平台 ／ 出图 ／ 记忆（M1 · 明标未接）⇒ ⛔ 装成可用；未命中 ⇒ 回落模型'},
  {k:'model', seq:'ⓞ', n:'模型', avail:'按快照',
   by:'对话答（未命中 ／ 域外之答 ⇒ 标「模型生成 · ⛔ 非本机素材」）',
   src:'/v9/pa/dialog（chan:pa）／ /v9/agent/chat（chan:agent）；可用性源 ＝ pa/ui_state.json 之「本地在」「远端态」「远端因」',
   note:'⚠ 本机小模型算精确值不可靠 ⇒ 涉算术 ／ 精确数字之答带如实标'},
  {k:'tool', seq:'ⓟ', n:'工具', avail:'部分可用',
   by:'执行循环（工作 ／ 开发模式之工具调用）＋ 精确计算（POST /api/tools/calc · 判据主源）',
   src:'/v9/agent/chat ／ /v9/pa/turn（落盘回执）',
   note:'⚠ 已通：精确计算（POST /api/tools/calc ⇒ 算术以工具值为准）；未接：技能面（13 技能 · 已转产品线）⇒ ⛔ 装成可用'}
];
function paSourceDecl(){ return PA_SRC_DECL.slice(); }
/* ⭐ pm_1047 §一 F-c（真 bug · 承 L76 如实面 ｜ L83 单源）：快照之键为 **「本地在」**（一手读九键：
   已载 ／ 显存 ／ Forever ／ 本地在 ／ 远端在 ／ 远端host ／ 远端态 ／ 远端因 ／ 刻）。
   ⚠ 本件旧写「本机在」⇒ 读不到 ⇒ 一律渲「未知」（老板 17:5x 亲见）。
   修：以「本地在」为主键（兼容旧名「本机在」）；⛔ 自造新键 —— 键归后端 · 承 L102。
   渲名不变（仍作「本机在 ✓」）—— 只改查找之键名。 */
function paSnapLocalOn(ui){
  if(!ui) return undefined;
  if(ui['本地在'] !== undefined && ui['本地在'] !== null) return ui['本地在'];
  return ui['本机在'];
}
function paSourceLive(){
  const ui = (typeof paSelfUiCache !== 'undefined' && paSelfUiCache) ? paSelfUiCache : null;
  const yn = function(v){
    if(v === true) return '✓';
    if(v === false) return '✗';
    const s = String(v == null ? '' : v).toLowerCase();
    if(s === 'true' || s === 'yes' || s === '✓') return '✓';
    if(s === 'false' || s === 'no' || s === '✗') return '✗';
    return '未知';
  };
  return {ui:ui, 本机在:(ui ? yn(paSnapLocalOn(ui)) : '未知'),
          远端在:(ui ? yn(ui['远端在']) : '未知'),
          /* ⭐ pm_1045 §三：加三态之两值（真源 ＝ 快照· ⛔ 前端算） */
          远端态:(ui ? ((typeof paRemoteTri === 'function') ? paRemoteTri(ui) : '') : ''),
          远端因:(ui ? ((typeof paRemoteWhy === 'function') ? paRemoteWhy(ui) : '未知') : '未取到'),
          刻:(ui ? String(ui['刻'] || '未知') : '未取到'),
          stat:(typeof paSelfAskStatGet === 'function') ? paSelfAskStatGet() : null};
}
function paSourceAvail(k, L){
  if(k === 'model'){
    return ('按快照 · 本机在 ' + L['本机在'] + ' · 远端 ' + (L['远端态'] || '未知') + '（因：' + L['远端因'] + '）（刻 ' + L['刻'] + '）');
  }
  for(let i=0;i<PA_SRC_DECL.length;i++){ if(PA_SRC_DECL[i].k === k) return PA_SRC_DECL[i].avail; }
  return '未知';
}
/* ⭐ pm_1039 §三：本机素材之「依据形」= **检索范围（逐面件数）** —— 取真源（⛔ 硬编目录名 ／ ⛔ 只报总数）。
   真源 ＝ POST /v9/pa/ask 响应之 scope ／ faces ／ searched（由 selfdesc.js 之 paSelfFacesRemember 记入）。
   ⚠ 本页尚未检索 ⇒ 如实说「本页尚未检索」（⛔ 编）。 */
function paSourceLocalBy(){
  let t = '', n = null;
  try{
    if(typeof paSelfFaceText === 'function' && typeof paSelfAskStat !== 'undefined'){
      t = paSelfFaceText(paSelfAskStat.lastScope, paSelfAskStat.lastFaces) || '';
      n = paSelfAskStat.lastSearched;
    }
  }catch(e){}
  return '检索面（真源 ＝ /v9/pa/ask 之 scope ／ faces ／ searched）：' + (t || '本页尚未检索')
    + ((n == null) ? '' : (' ｜ 共搜 ' + n + ' 件')) + '（原文 ⇒ 以「据 N 条」贴出）';
}
function paSourceDeclHtml(){
  const L = paSourceLive();
  const rows = PA_SRC_DECL.map(function(d){
    const av = paSourceAvail(d.k, L);
    const cls = (d.k === 'model') ? ((L['本机在'] === '✓' || L['远端态'] === '配了且通') ? 'ok' : 'na')
                                  : ((d.avail === '可用') ? 'ok' : 'na');
    return '<div class="a"><div class="q">' + d.seq + ' ' + paSelfEsc(d.n) + ' 【' + paSelfEsc(av) + '】</div><div class="t">'
      + '<div class="r"><span class="k">依据形</span><span class="s">' + paSelfEsc((d.k === 'local') ? paSourceLocalBy() : d.by) + '</span></div>'
      + '<div class="r"><span class="k">真源</span><span class="s">' + paSelfEsc(d.src) + '</span></div>'
      + '<div class="' + cls + '">' + paSelfEsc(d.note) + '</div></div></div>';
  }).join('');
  const st = L.stat;
  const statLine = st
    ? ('检索统计（本页会话）：命中 ' + st.hit + ' ｜ 未命中 ' + st.miss + ' ｜ 回落 ' + st.fallback
       + '（其中失败 ' + st.fallbackFail + '）｜ 未过闸 ' + st.direct
       + (st.t0 ? ('（起计 ' + st.t0 + '）') : '（本页尚未起计）'))
    : '检索统计：本页尚未发问';
  return '<div class="a" id="paSrcDeclBox"><div class="q">来源声明（四源 · 按可用性呈现）</div><div class="t">'
    + rows
    + '<div class="s">⭐ 与问域判据（paAskDomain）之关系：判据 ＝ 提示 ／ 加速（预判该去哪一面取据），⛔ 闸 —— 未命中 ⇒ 回落模型；⛔ 因判据拒答。</div>'
    + '<div class="s">' + paSelfEsc(statLine) + '</div>'
    + '<div class="s">未接者一律明标未接（⛔ 装成可用）；本清单之读数皆取真源（⛔ 自算）。</div>'
    + '</div></div>';
}
function paSourceStatRender(){
  const box = document.getElementById('paAboutBody'); if(!box) return null;
  const old0 = document.getElementById('paAskStatBox');
  if(old0 && old0.parentNode) old0.parentNode.removeChild(old0);
  if(typeof paSelfAskStatHtml === 'function'){
    const w = document.createElement('div'); w.innerHTML = paSelfAskStatHtml();
    if(w.firstChild) box.insertBefore(w.firstChild, box.firstChild);
  }
  return box;
}
function paSourceDeclRender(){
  const box = document.getElementById('paAboutBody'); if(!box) return null;
  const old = document.getElementById('paSrcDeclBox');
  if(old && old.parentNode) old.parentNode.removeChild(old);
  const w = document.createElement('div'); w.innerHTML = paSourceDeclHtml();
  if(w.firstChild) box.insertBefore(w.firstChild, box.firstChild);
  try{ paSourceStatRender(); }catch(e){}
  return box;
}
(function(){
  const inner = window.paAboutLoad;
  if(typeof inner !== 'function') return;
  window.paAboutLoad = async function(){
    const r = await inner.apply(this, arguments);
    try{ paSourceDeclRender(); }catch(e){}
    return r;
  };
})();
try{ window.paSourceDecl = paSourceDecl; }catch(e){}
try{ window.paSourceDeclHtml = paSourceDeclHtml; }catch(e){}
try{ window.paSourceLive = paSourceLive; }catch(e){}
try{ window.paSourceDeclRender = paSourceDeclRender; }catch(e){}
try{ window.paSourceStatRender = paSourceStatRender; }catch(e){}
