/* ClawsJoy PA v3 · 自述面 ＋ 权限四层（CW b2a5182 · 承 pm_1000 ／ pm_1001 ／ pm_1012 · 2026-10-04）
   病（老板之证 · pm_1000 §〇）：问「自我介绍」「你有哪些工具可以使用，列一下」⇒ 走 /v9/pa/ask 之「有据才答」
   ⇒ 该闸之检索范围过窄 ⇒ 答「查不到」／泛套话 ⇒ ⭐ 退化成知识库机器人（⛔ PA）。
   ⚠ 更新（pm_1047 §二.4）：原注释写死「只搜知识库＋收件箱」⇒ 误导读码者（PM 今晚几乎据此误判）；
     今检索范围 ＝ **五面**（收件箱 ／ 知识库 ／ 文件 ／ 台账 ／ 台账·信通），真源 ＝ POST /v9/pa/ask 之 scope ／ faces ／ searched ⇒ ⛔ 前端硬编（承 L102）。
   治法（前端 · ⛔ 动平台网关）：命中「自述类」⇒ ⛔ 调 /v9/pa/ask ⇒ 改读**本机自述来源**拼答。
   ⭐ pm_1012（对话可靠性 · 三令）：① 上屏文案分层（用户面只说人话 · 工程注记默认隐藏 · 禁词表可机验）
     ② 兜底改「三类路由」（自述 ／ 本机素材 ／ 域外 · ⛔ 一律自述）③ 失败态人话（⛔ 裸异常串上屏）。
   来源：web/pa/faces.json（面册）／ /v9/metrics/tool_flow（工具流水）／ /v9/pa/context（画像）
        ／ /v9/pa/permission（权限档）／ /v9/pa/threads（会话面）／ /v9/pes/runs（作业面）／ web/pa/ui_state.json（快照）。
   口径（L76）：读数类 ⇒ 标来源；口径类（身份自述 ／ 读·外发·凭据三层）⇒ 明标「本机固定口径」⇒ ⛔ 冒充真读数。
   ⚠ 本件由 pa.html（**唯一壳 · 真源**）载入 —— ⭐ 承 pm 1203 §一（2026-10-05 · 副本 web/pa_v3.html 已删 · TD 716bc31）：旧「唯 v3 页载入 ⇒ 旧 pa.html ⛔ 受影响」之**界已反**（今唯 pa.html 一壳 ⇒ 本件之改**及于唯一壳**）（⛔ 动共用面件 send.js ／ status.js ／ products.js）。
   ⚠ 件体（承 pm_1002 §三 补① · 取 (b)）：本件**⛔ 不是面体** —— 本件为**回答层件**：在 paSend 最外层拦
     「自述类」问句、以本机来源拼答 ⇒ **⛔ 注册进 pa/faces.json**（⛔ 假装一面 · 面册仍 22 面）。
   ⚠ 自述之判为**规则表 ＋ 模式**（⛔ 语义模型）⇒ 判定依据默认隐藏于「来源 ／ 详情」（承 L76 如实）。
   ⚠ 误判可退（承 pm_1002 §三 补②）：句首加「检索：」或「@ask」再发 ⇒ **强制走知识检索**（⛔ 硬吞）。
   ⭐ 两轴之分（pm_1067 §四 · 承 L83 ／ L151）：**前端** `paAskDomain`（`self ／ local ／ world ／ other`）
      管**自述 ／ 本机 ／ 世界**；**后端** `/v9/pa/ask` 之 `ask_domain`（`meta ／ retrieve`）管**路由**
      ⇒ 两轴各管其段 · ⛔ 二处各判同一物；元问（指代 ／ 重复 ／ 上文）⇒ 前端**放行**（⛔ 判 self ／ ⛔ 拼答）。
   ⚠ 兜底（承 pm_1003 §二 · 立 L82 · 改 pm_1012 §三）：知识检索回拒答 ⇒ ⛔ 上屏「查不到」 ⇒ 按问域给**人话**。
   ⚠ 禁词表（用户面 · 可机验 · pm_1012 §二）：pm_ 数字 ／ L ＋ 两位数字 ／ § ／ 兜底闸 ／ 启发式 ／ 判层 ／ 留痕 ／
     候批 ／ 另立件 ／ 报我 ／ 拼答 ／ 真源清单 ／ 反例门 ／ 探针 ／ 重发 ⇒ 默认态用户面命中须为 0。
   ⚠ 本版之由（承 L80 · 前值 b19b3657e00e754b ⇒ 本版）：pm_1012 三令 —— ① 上屏文案分层（工程注记默认隐藏）
     ② 兜底改三类路由（⛔ 一律自述）③ 失败态人话（⛔ 裸异常串上屏）；另包装净化共用件之「探针」一词上屏。
*/

/* ================= 一 · 自述类之判（A28 Jev：由意图分类分 · ⛔ 由「忙」分）=================
   ⚠ 规则表 ＋ 模式（承 status.js 之 paLooksLikeKnowledgeQuestion 同族之坦白）：命中须**自指**（你 ／ 自我 ／ PA），
     ⛔ 拦普通任务句（例「帮我看看这个文件的权限」⇒ 前置排除）。 */
const PA_SELF_PAT = [
  ['who',   /自我介绍|介绍一下你|介绍下你|你是谁|你叫什么|你的身份|你是什么(东西|角色)/],
  ['env',   /环境感知|你的环境|你能感知|你的感知|障碍|你的局限|你的限制|你的短板|做不了什么|画像|记忆|记得|记住(什么|了)|知道什么/],
  ['read',  /环境读数|显存|你现在的状态|你的状态|资源(情况|读数)/],
  ['tools', /你有哪些工具|有哪些工具|工具(有哪|清单|列表)|你能用哪些工具|可用工具/],
  ['perm',  /你的权限|权限边界|权限与边界|权限四层|你能读什么|能读什么|能写什么|可读权限/],
  ['plug',  /插件|扩展(能力|包)|面册|有哪些面/],
  ['seat',  /agent|智能体|子代理|子任务|席位|可调用|调你|调我|谁能调|谁在调|谁可以调|指派|派活|派单/],
  ['cmp',   /对比|对照|差距|muse|dots|竞品/],
  ['can',   /你能做什么|你会做什么|你能干什么|你能做哪些|你有什么能力|你有哪些能力|你的能力|你的功能/]
];
function paSelfKey(text){
  const s = String(text == null ? '' : text).trim();
  if(!s || s.length > 120) return null;
  /* 自指之判：须为「对 PA 说」——含你 ／ 自我 ／ PA，或本身即自述短语（权限边界 ／ 环境感知 ／ 自我介绍 …）。
     ⛔ 反例：普通任务句（「帮我看看这个文件的权限」／「把这个文件重命名」）⇒ ⛔ 拦。 */
  if(!/(你|自我|PA|pa|权限(与|和)?边界|权限四层|自我介绍|环境感知|有哪些工具|能做(什么|哪些)|能读什么|能写什么)/.test(s)) return null;
  if(/^(帮我|请帮我|麻烦你?帮|替我|给我|把这|把这个)/.test(s)) return null;
  for(let i=0;i<PA_SELF_PAT.length;i++){ if(PA_SELF_PAT[i][1].test(s)) return PA_SELF_PAT[i][0]; }
  return null;
}
const PA_SELF_Q = {
  who:'我是谁', can:'我能做什么', tools:'我有哪些工具', env:'环境感知与障碍',
  read:'环境读数', perm:'权限与边界',
  plug:'插件与面', seat:'可调用的 agent', cmp:'对照与差距'
};
const PA_SELF_NEEDS = {
  who:['ctx'], can:['faces'], tools:['flow'], read:['ui'],
  env:['ctx','thr','runs','perm','flow','ui'],
  perm:['perm','thr','runs','ctx','ui'],
  plug:['faces'], seat:['sub','roster','seats','env'], cmp:[]
};

/* ================= 二 · 取来源（只读 · ⛔ 自造）================= */
function paSelfJson(path){
  return fetch(path, {cache:'no-store'}).then(function(r){ return r.ok ? r.json() : null; }).catch(function(){ return null; });
}
let paSelfUiCache = null;   /* 最近所读之快照（承 pm_1006 §三：供「权限」面同步取用 · ⛔ 二次拉） */
async function paSelfSrc(keys){
  const need = {};
  (keys || []).forEach(function(k){ (PA_SELF_NEEDS[k] || []).forEach(function(n){ need[n] = 1; }); });
  const u = encodeURIComponent(curUser());
  const P = {
    faces: 'pa/faces.json',
    flow:  API + '/v9/metrics/tool_flow',
    ctx:   API + '/v9/pa/context?user_id=' + u,
    perm:  API + '/v9/pa/permission?user_id=' + u,
    thr:   API + '/v9/pa/threads?user_id=' + u,
    runs:  API + '/v9/pes/runs?user_id=' + u,
    sub:   API + '/v9/subtask/status?user_id=' + u + '&session_id=' + encodeURIComponent((function(){ try{ return curSession(); }catch(e){ return 'default'; } })()),
    ui:    'pa/ui_state.json',
    roster: API + '/v9/pa/roster?user_id=' + u,
    seats: API + '/v9/pa/seats',
    env:   API + '/v9/pa/env'
  };
  const out = {}, ks = Object.keys(need);
  for(let i=0;i<ks.length;i++){ out[ks[i]] = await paSelfJson(P[ks[i]]); }
  if(out.ui) paSelfUiCache = out.ui;
  return out;
}
function paSelfFaces(d){
  const fs = (d && Array.isArray(d.faces)) ? d.faces : null;
  if(!fs) return null;
  const op = fs.filter(function(f){ return f.open !== false; });
  const pv = fs.filter(function(f){ return f.open === false; });
  return {total: fs.length, open: op, priv: pv};
}
function paSelfFlow(d){
  const st = (d && d.stats) || null; if(!st) return null;
  const bt = st.by_tool || {}, bj = st.by_task || {};
  /* ⭐ pm_1003 §三：自检占位名（no_such_tool* ／ cw_keyprobe）⛔ 冒充工具 ⇒ 剔出工具名，另记其数（承 L76） */
  const all = Object.keys(bt);
  const probe = all.filter(function(k){ return /^(no_such_tool|cw_keyprobe)/.test(k); });
  let probeCalls = 0; probe.forEach(function(k){ probeCalls += ((bt[k] || {}).count || 0); });
  const rows = all.filter(function(k){ return !/^(no_such_tool|cw_keyprobe)/.test(k); })
    .map(function(k){ const v = bt[k] || {}; return {k:k, n:v.count||0, r:v.success_rate, ms:v.avg_ms}; });
  rows.sort(function(a,b){ return b.n - a.n; });
  return {hours: st.window_hours, total: st.total, tools: rows, nTask: Object.keys(bj).length, at: st.generated_at, probe: probe, probeCalls: probeCalls};
}
function paSelfSrcFaces(){
  const out = {read:[], miss:[], off:[], unreach:[], note:''};
  const box = document.getElementById('paSrcList');
  if(!box){ out.note = '来源面清单未载入（左栏来源面不在）'; return out; }
  const its = box.querySelectorAll('.it');
  for(let i=0;i<its.length;i++){
    /* ⭐ pm 17:47 §二改①：「未接」须分二义 ⇒ 三桶 —— ⒜未接·待办 ／ ⒝⛔不接·红线 ／ 不可达（后端此刻不在）。
       ⛔ 以「未接」盖「红线」（软性虚诺）· ⛔ 把「不可达」读成「未接」（承 pm_刀12p §〇：三态分显）。 */
    const t = String(its[i].textContent || '').replace(/\s+/g, ' ').trim();
    if(/不接/.test(t)) out.off.push(t);
    else if(/不可达/.test(t)) out.unreach.push(t);
    else if(/未接/.test(t)) out.miss.push(t);
    else out.read.push(t);
  }
  return out;
}
function paSelfPermRows(){
  const lv = (function(){ try{ return paSelfGrantLevel(); }catch(e){ return undefined; } })();
  let grant = null; try{ grant = paSelfGrant(); }catch(e){}
  let has = null;
  if(grant) has = !!((grant.pa && grant.pa.exists) || (grant.pes && grant.pes.exists));
  const lvtxt = (lv === undefined || lv === null) ? '未知（未取到）' : String(lv);
  return [
    {n:'①', k:'读（全局开）',   v:'本机全上下文', s:'本机固定口径'},
    {n:'②', k:'写（主面每次问 ／ 派活路免审批）',   v:'主面写须你点头；派活（子任务）之写免审批（老板 2026-10-04 批）· 越权写仍由锚点B 拦', s:'本机固定口径'},
    {n:'③', k:'外发（默认关）', v:'发布 ／ 上传 ／ 外发须你显式点头', s:'本机固定口径'},
    {n:'④', k:'凭据（只取布尔）', v:'只报「已配 ／ 未配」· ⛔ 不读值', s:'本机固定口径'},
    {n:'⑤', k:'权限档（读数）', v:lvtxt + (has === null ? '' : (has ? '（已授予）' : '（未授予 ⇒ 用默认档）')), s:'GET /v9/pa/permission'}
  ];
}

/* ⭐ 显存警号（承 pm_1006 §三 · pm_1007 §一）：N ≥ 1 ＝ 有模型被永久留在显存里
   ⇒ 出图（3.0–3.3 GB）能否跑须判；判据 ＝ **能力线**（PA_GPU_LINE_MIB ＝ 3379 MiB）· ⛔ 圆整百分数。
   ⚠ 处置属本机模型服务侧（⛔ 我方动「卸载」· 承 10-01 认错之族）。 */
function paSelfForeverN(ui){
  return (ui && Array.isArray(ui.Forever)) ? ui.Forever.length : -1;
}
/* ⭐ 承 pm_1007 §一 ＋ L83（判据单源）：⛔ 本处重判（旧法 ＝ free/total < 10% 之圆整百分数）
   —— 一律调用 more.js 之 paGpuWarnColor（能力线 3379 MiB 之唯一出口）；
   无该件 ⇒ 回空串（宁可无色 · ⛔ 与单源打架）。 */
function paSelfGpuLine(){
  try{ return (typeof PA_GPU_LINE_MIB === 'number') ? PA_GPU_LINE_MIB : null; }catch(e){ return null; }
}
function paSelfGpuWarnColor(ui){
  try{ if(typeof paGpuWarnColor === 'function') return paGpuWarnColor(ui); }catch(e){}
  return '';
}
/* 人话版警号（用户面 · ⛔ 机制词）：一句 ＋ 一句处置边界 */
function paSelfGpuWarn(ui){
  const n = paSelfForeverN(ui);
  if(n < 1) return '';
  const vr = (ui && ui['显存']) || {};
  const nz = function(v){ return (v === undefined || v === null) ? '未知' : String(v); };
  const line = paSelfGpuLine();
  const fre = Number(vr.free);
  const verdict = (line === null || !isFinite(fre)) ? '可能失败（可用显存未知）'
    : (fre < line ? '可能失败' : '暂时还能跑');
  return '⚠ 有 ' + n + ' 个模型被永久留在显存里（' + (ui.Forever || []).join(' ／ ') + '）'
    + ' ⇒ 出图' + verdict + '（当前可用显存 ' + nz(vr.free) + ' / ' + nz(vr.total) + ' MB）'
    + '。处置见本机模型服务侧 —— ⛔ 我不会自动动它。';
}
/* 警号之工程注记（入折叠处） */
function paSelfGpuEng(ui){
  const n = paSelfForeverN(ui);
  if(n < 1) return '';
  const vr = (ui && ui['显存']) || {};
  const line = paSelfGpuLine();
  return '显存警号判据：Forever 条目数 N ＝ ' + n + '（现读快照 · ⛔ 前端自算）｜能力线 PA_GPU_LINE_MIB ＝ '
    + (line === null ? '未知' : line + ' MiB') + '（单源 more.js · 承 L83）｜free ＝ ' + vr.free + ' ／ total ＝ ' + vr.total
    + '｜N ≥ 1 ∧ free < 能力线 ⇒ 红；N ≥ 1 ∧ free ≥ 能力线 ⇒ 黄；未知 ⇒ 黄并明写（承 L85）。';
}

/* ---- 来源之小包（shell.js 之 paGrant ／ paGrantLevel 为全局词法绑定 ⇒ 读之须包 try）---- */
function paSelfGrant(){ try{ return paGrant; }catch(e){ return null; } }
function paSelfGrantLevel(){ try{ return paGrantLevel; }catch(e){ return undefined; } }
function paSelfBusy(){ try{ return !!paRun.busy; }catch(e){ return false; } }  /* status.js 之 paRun 为脚本级词法绑定 ⇒ ⛔ window.paRun */
function paSelfEsc(s){ return String(s == null ? '' : s).replace(/[&<>"]/g, function(c){
  return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]; }); }
function paSelfYN(v){ return v === true ? '✓' : (v === false ? '✗' : '未知'); }
function paSelfAt(v){ try{ return (typeof v === 'number' && isFinite(v)) ? new Date(v * 1000).toLocaleString('zh-CN', {hour12:false}) : (v == null ? '未知' : String(v)); }catch(e){ return '未知'; } }

/* ================= 〇 · 工程注记（用户面只说人话 · 承 pm_1012 §一 ／ §二）=================
   ⭐ 用户面（默认态）⇒ 只人话；工程注记（判定依据 ／ 件号 ／ 律号 ／ 机制说明 ／ 留痕 ／ 候选）⇒ **默认隐藏**，
     入「来源 ／ 详情」折叠处可展开（⛔ 丢信息）。判据：默认态用户面 innerText ⇒ 禁词命中 ＝ 0。 */
const PA_ENG_WORDS = /pm_\d+|L\d{2}|§|兜底闸|启发式|判层|留痕|候批|另立件|报我|拼答|真源清单|反例门|探针|重发/;
/* ⭐ 令③之族（承 pm_1012 §四）：裸异常 ／ 工程标识之词（用户面 ⛔ 出现）⇒ 存量消息 ／ 运行记录里
   若夹带之，同样入工程注记（原文照录 · ⛔ 丢信息）。⛔ 与「能力边界之人话」混同。 */
const PA_ENG_ERR = /fetch|Failed|TypeError|undefined|\[object|查不到|XMLHttpRequest|Expected property name|Unexpected token|in JSON at position|is not valid JSON|SyntaxError|NetworkError/;   /* ⭐ 末项承 pm_1013：旧拒答话术（「查不到」）之运行记录亦入注记（⛔ 上屏）；⭐ 技术串类（承 pm_1018 §二 ⓜ.3）：XMLHttpRequest ／ Expected property name ／ JSON 解析串 ／ Unexpected token ／ SyntaxError ／ NetworkError ⇒ 亦入注记 */
/* ⭐ 源之分标（承 pm_1013 §二）：域外之答（`domain = world ／ other`）之**源**须明标于用户面。
   三态（PM 逐字）：本机素材（据 N 条）／模型生成（⛔ 非本机素材）／超出本机素材范围（未答）。
   其由 ＝ 承 pm_1005 §二（「据」与「答」分面而标 ⇒ ⛔ 让用户以为「模型说」＝「本机有据」）。 */
let paSelfLbl = null;   /* 待贴之源标（模型通道之答 · 由 paSend 包装置 · 由 addMsg 包装取） */

let paSelfFb = null;     /* ⭐ pm_1032 §三.1：本轮「检索未命中 ⇒ 回落模型」之凭据（由 paAskGate 包装置 · 由 addMsg 包装取 · 一轮一清） */
let paSelfMetaAns = null;/* ⭐ pm_1067 §四：本轮「元问（ask_domain=meta）」之后端答复（由 paAskGate 包装置 · 由 sendPA 包装取 · 一轮一清） */
let paSelfRefusalDone = false; /* ⭐ pm_1073 §二.1 同族：拒答轮之「模型路败」已出拒答 ⇒ 待顶栏回正（send.js:76 之后置 failed 须被收尾扳回） */
let paSelfRoundPersisted = false; /* ⭐ pm_1111 §二：四族「就地作答」之落盘闸（本轮是否已落盘 · 一轮一清 · ⛔ 跨轮复用 · 承 L76） */
let paSelfLastUser = ''; /* ⭐ pm_1031 §二：最近一条用户行（算术如实标之判据须看「问」） */
let paSelfLastReqSrc = '';  /* ⭐ pm_1031 §三.2：最近一次请求之源（供「失败支亦須带源」回指） */

/* ⭐ pm_1031 §二（算术須如实标注）：本机 7B 小模型算精确值不可靠（PM 一手：R1/R2 算错 · 2/4）
   ⇒ 凡「问句涉算术 ／ 精确数字」∧「答体含数字」 ⇒ 用户面加一枚**如实标**（⛔ 裸给数字）。
   ⚠ 宽严之界：須**问**具算术意图（单位＋动作词）∧ **答**含数字 ⇒ 二者兼备才标（⛔ 见数字就标 ⇒ 噪音）。 */
const PA_ARITH_Q = /(?:[0-9０-９]|[一二三四五六七八九十百千万零两])\s*(?:元|块|角|分|个|只|人|组|件|小时|分钟|天|米|公里|斤|升|折|%|％)/;
const PA_ARITH_INT = /(?:涨|降|打|折|平均|除以|乘以|加上|减去|共|总|余|每组|每人|多少|几只|几个|几组|几件|几元|鸡兔|同笼|算式|计算|算一算|求)/;
/* ⭐ pm_1042 §二.1（PM 一手 · `W3` 被误贴「算术未复核」）：**字数 ／ 篇幅约束**⛔ 当算术。
   病：写作题「写一个不超过 15 字的邮件标题」因其中「一个」命中量词表（`一` ＋ `个`）⇒ 判「算术」⇒ 用户见「算术不可信」。
   令（照 PM）：⒜ 排除「`N` 字 ／ 不超过 `N` 字 ／ `N` 字符」等**字数约束** ⒝ 以**算式之形**（数字 ＋ 算子 ＋ 数字）为主判据。
   ⚠ 界：`N 字` 之排除**只在无算式之形时**生效（「算一下 1+2，不超过 5 个字」仍算算术 ⇒ 两判据并立）。 */
const PA_ARITH_CNT = /(?:[0-9０-９]|[一二三四五六七八九十百千万零两])\s*(?:个字|字符|字|词|句|行|段)/;
const PA_ARITH_SHAPE = /[0-9０-９][^0-9０-９\n]{0,3}[+\-*/xX×÷＊][^0-9０-９\n]{0,3}[0-9０-９]/;
function paSelfArithQ(s){
  const t = String(s == null ? '' : s);
  if(PA_ARITH_SHAPE.test(t)) return true;          /* 算式之形 ⇒ 算术（主判据） */
  if(PA_ARITH_CNT.test(t)) return false;           /* 字数 ／ 篇幅约束 ⛔ 当算术（pm_1042 §二.1） */
  return PA_ARITH_Q.test(t) && PA_ARITH_INT.test(t);
}
try{ window.paSelfArithQ = paSelfArithQ; }catch(e){}
const PA_ARITH_NOTE = '⚠ 本机小模型 · 算术与精确数字请复核（⛔ 表示此处数字不宜直接采信）';
function paSelfArithNote(q, a){
  const s = String(q == null ? '' : q), t = String(a == null ? '' : a);
  if(!s || !t) return '';
  if(!paSelfArithQ(s)) return '';   /* ⭐ pm_1042 §二.1：收窄（字数约束 ⛔ 当算术 · 算式之形为主） */
  if(!/[0-9０-９]/.test(t)) return '';
  if(t.indexOf(PA_ARITH_NOTE) >= 0) return '';
  return PA_ARITH_NOTE;
}

/* ⭐ pm_1038 §三.1（无式之算术答 ⇒ 须标「未复核」）：承 pm_1038 §二（真答无式 ⇒ 复核无标 ⇒ 工具⛔ 触）
   ⇒ 「模型给一个无式之错数」永不触工具 ⇒ 用户见「算术请复核」之**泛标**而误以为已核 ⇒ ⛔ 假安心。
   故：算术类问（PA_ARITH_Q 命中）∧ 答体**无可判之式** ⇒ 用户面**单列**明标（⛔ 泛标顶替）＋ 读数盒单列一格。
   ⚠ 界（照实）：本标**只**表「本格未经任何核」（⛔ 表其对 ∨ 错 · ⛔ 猜「应有值」· ⛔ 强改答体一字）。 */
const PA_UNC_MARK = '⚠ 本格未能复核（';
const PA_UNC_TAIL = '）· 本机与工具皆⛔ 核 ⇒ 本机小模型之算术数字不宜直接采信'
  + ' ⇒ 可把算式单独发我（如 200×1.1×0.9）· 我照工具算（判据主源 POST /api/tools/calc）。';
/* ⭐ pm_1074 §二.ⓝ：上行之自示例原作 `200*1.1*0.9` ⇒ 经 MD 吞 `*` ⇒ 屏上 `（如 2001.10.9）`（用户照拄即得错串）⇒ 今改 `×`（与下方 `paSelfMulSafe` 同形 · 双保险）。 */
const PA_UNC_EXPR = /[0-9０-９][^0-9０-９\n]{0,3}[+\-*/xX＊][^0-9０-９\n]{0,3}[0-9０-９]/;
function paSelfHasExprRaw(a){
  /* 先归一（全角 × ÷ − ＝ ． ％ ／ 全角数字 ⇒ 半角）再看「有式之形」；
     含字母 ／ 单位 ／ 汉字之式**亦**算「有式之形」（只是本机⛔ 判读 ⇒ 其由须照实分面）。 */
  try{ return PA_UNC_EXPR.test(paSelfChkNorm(a)); }
  catch(e){ return PA_UNC_EXPR.test(String(a == null ? '' : a)); }
}
function paSelfUnchkNote(q, a, seen){
  const s = String(q == null ? '' : q), t = String(a == null ? '' : a);
  if(!s || !t) return null;
  if(!paSelfArithQ(s)) return null;                    /* ⭐ pm_1042 §二.1：同上收窄 —— ⛔ 写作题被贴 */
  if(!/[0-9０-９]/.test(t)) return null;               /* 答体无数字 ⇒ 无「精确数字」可核 */
  if(seen > 0) return null;                             /* 有**可判之式** ⇒ 复核已尽职（标 ∨ 静默） */
  const why = paSelfHasExprRaw(t) ? '答体之式本机⛔ 判读（含字母 ／ 单位 ／ 汉字）' : '答体未给算式';
  const u = PA_UNC_MARK + why + PA_UNC_TAIL;
  const e = '答体复核（未复核 · pm_1038 §三.1）：本问为算术类问 ∧ 答体无可判之式（' + why + '）'
    + '\n⇒ 本机复核与工具径皆⛔ 触发（承 pm_1038 §二：无标 ⇒ ⛔ 触工具）⇒ ⛔ 泛标顶替（⛔ 让用户以为已核）。'
    + '\n⚠ 如实：本格之数字**未经任何核**（⛔ 表示其对 ∨ 错）⇒ 请以他法复核。';
  return {u:u, e:e, why:why};
}
try{ window.paSelfUnchkNote = paSelfUnchkNote; }catch(e){}
try{ window.paSelfHasExprRaw = paSelfHasExprRaw; }catch(e){}
try{ window.paSelfChkSeenGet = function(){ return paSelfChkSeen; }; }catch(e){}

/* ⭐ pm_1034 §四②（精确计算之前端可办之部）：**答体自洽复核**（⛔ 不算答案 · 只核答体自己写出的式）
   病（PM 一手 · R3）：答写「200 × 1.1 × 0.9 = 210.8」—— 算式对而结果错 ⇒ 用户照单全收。
   工具径之现状（我一手 · 本批报单 §一）：/api/skills/execute 对 13 技能**逐条 500**
     （真因：core/routes/skill_routes.py:33 取到之 skill_loader 为 None ⇒ AttributeError）；
     库内**有**安全算器（core/lib/safe_calculator.py · AST · ⛔ eval），而**无 HTTP 径**
     ⇒ 真工具在「库」不在「径」⇒ 已报 PM 转产品线；本复核＝过渡之**保守自查**
     （承 L76 如实面 · ⛔ 替代工具 · ⛔ 冒充权威）。
   宽严之界（⛔ 假读数）：式内**只许** 数字 ／ `+ - * / ( ) .` 与空白（全角 × ÷ − ＝ ． ％
     与全角数字先归一）⇒ 式内出现字母 ／ 单位 ／ 汉字（如「10x2」「200元 × 1.1」）
     或括号不配 ／ 数被截断（如千分位「1,234」）⇒ **弃而不判**（⛔ 猜 ⇒ ⛔ 误标好答）。
   判据：|本机重算 − 答体所写| > 该处**所示小数位**所能解释之量（承「四舍五入⛔ 当错」）
     ⇒ 出一条「疑不符」（⛔ 改答体一字 · 原式原值照留于答中）。 */
const paSelfChkStat = {n:0, bad:0, mq:0, nr:0, last:''};
const PA_CHK_NORM = {'×':'*','✕':'*','÷':'/','−':'-','–':'-','—':'-','＝':'=','．':'.','％':'%'};
const PA_CHK_FW = {'０':'0','１':'1','２':'2','３':'3','４':'4','５':'5','６':'6','７':'7','８':'8','９':'9'};
function paSelfChkNorm(s){
  const t = String(s == null ? '' : s).replace(/\u3000/g, ' ');
  return t.replace(/[×✕÷−–—＝．％０-９]/g, function(c){
    return (PA_CHK_NORM[c] != null) ? PA_CHK_NORM[c] : (PA_CHK_FW[c] || c);
  });
}
function paSelfChkR(v){ return String(Math.round(v * 1e6) / 1e6); }
/* 只含 数字 ／ 运算符 ／ 括号 ／ 空白 之式 ⇒ 求值（⛔ eval · 递归下降 · 残缺即抛） */
function paSelfChkEval(s){
  let i = 0;
  const ws = function(){ while(i < s.length && (s[i] === ' ' || s[i] === '\t')) i++; };
  const atom = function(){
    ws(); const st = i;
    while(i < s.length && /[0-9.]/.test(s[i])) i++;
    const t = s.slice(st, i);
    if(!/^[0-9]*\.?[0-9]+$/.test(t)) throw new Error('num');
    return parseFloat(t);
  };
  const unary = function(){
    ws();
    if(s[i] === '+'){ i++; return unary(); }
    if(s[i] === '-'){ i++; return -unary(); }
    if(s[i] === '('){ i++; const v = expr(); ws(); if(s[i] !== ')') throw new Error('paren'); i++; return v; }
    return atom();
  };
  const term = function(){
    let v = unary();
    for(;;){ ws(); const c = s[i];
      if(c === '*'){ i++; v = v * unary(); } else if(c === '/'){ i++; v = v / unary(); } else return v; }
  };
  const expr = function(){
    let v = term();
    for(;;){ ws(); const c = s[i];
      if(c === '+'){ i++; v = v + term(); } else if(c === '-'){ i++; v = v - term(); } else return v; }
  };
  const v = expr();
  ws();
  if(i !== s.length) throw new Error('tail');
  if(typeof v !== 'number' || !isFinite(v)) throw new Error('inf');
  return v;
}
const PA_CHK_EQ = /([0-9][0-9 \t+\-*/().]{2,}[0-9)])[ \t]*=[ \t]*([0-9]+(?:\.[0-9]+)?)/;
/* ⭐ pm_1042 §二.2（PM 一手 · `R3`）：旧法之式内**出现单位 ／ 汉字 ／ 字母**即弃判 ⇒ 答体「210.6 元；算式：200 × 1.1 × 0.9。」
   之式⛔ 判读 ∧ 工具⛔ 触 ⇒ 错值 `210.6` 溜过。令：取「数字-算子」之**最长连续段**（归一后天然剥掉单位 ／ 汉字 ／ 字母）
   ⇒ 再交本机复核 ＋ 工具。
   ⚠ 宽严之界（⛔ 误标好答）：⒜ 只取**空白分隔之算子**者 —— ⇒ `1280×720` ／ `2026-10-04` 类⛔ 判（非算式）；
   ⒝ 只在答体**无 `=`** 时启用（有 `=` ⇒ 尽归上判，⛔ 双报）；⒞ 其「报值」须为**量词之值**（数与单位相邻）
   且**不在该段内** ∧ **不等于该段之任一算子数**（⇒ 「原价 200 元 ⇒ 200 * 1.1 * 0.9」⛔ 误标）。 */
const PA_CHK_RUN = /[0-9][0-9.]*(?:\s+[+\-*/]\s+[0-9][0-9.]*)+/g;
const PA_CHK_VAL = /([0-9]+(?:\.[0-9]+)?)\s*(元|块|角|分|个|只|人|组|件|小时|分钟|天|米|公里|斤|升|折|%|％)/g;
function paSelfChkRuns(t){
  const out = []; const re = new RegExp(PA_CHK_RUN.source, 'g'); let m, n = 0;
  while((m = re.exec(t)) !== null){
    if(m.index === re.lastIndex) re.lastIndex++;
    if(++n > 60) break;
    const run = m[0].replace(/[ \t]+/g, ' ').trim();
    if((run.match(/[0-9]/g) || []).length < 2) continue;
    let v; try{ v = paSelfChkEval(run); }catch(e){ continue; }
    out.push({run:run, index:m.index, end:m.index + m[0].length, len:m[0].length, v:v});
  }
  return out;
}
function paSelfChkReported(t, a, b, operands){
  const re = new RegExp(PA_CHK_VAL.source, 'g'); let m, n = 0;
  while((m = re.exec(t)) !== null){
    if(m.index === re.lastIndex) re.lastIndex++;
    if(++n > 40) break;
    if(m.index >= a && m.index < b) continue;                 /* 段内 ⇒ ⛔ 当报值 */
    const v = parseFloat(m[1]);
    if(!isFinite(v)) continue;
    if(operands && operands.indexOf(v) >= 0) continue;         /* 系该段之算子数 ⇒ ⛔ 当报值（承 ⒞） */
    return {num:v, raw:m[1] + m[2]};
  }
  return null;
}

/* ⭐ pm_1035 §三（必补一格）：**同一答体内「同量多值」** —— ⛔ 猜哪个对 · 只作「标」。
   病（真实病例 · R4）：`7个零件；9人9小时可做9个零件。` ⇒ **一句两值**；而现法只判 `式 = 值` ⇒ 漏。
   宽严之界（⛔ 假读数）：
     ⒜ 只判**「量词＋名词」同形**者 —— **裸量词**（`件` ／ `个` ／ `人`）⛔ 判
        ⇒ 免得「共搜 28 件」与「命中 5 件」这类**同单位不同指**被误标；
     ⒝ 该数须**独立成词**（前后紧邻者非 数字 ／ 运算符 ／ `=` ／ 括号）⇒ 免得「7个零件×2 = 14个零件」
        这类**换算**被误标（值与值之间有算子 ＝ 换算，非矛盾）。
   ⚠ 已知误标面（照实 · 报 PM）：子集式（如「共 5 个席位，其中 3 个席位已接」）**会**被标
     ⇒ ⛔ 猜对错，故仍只作「标」。
   ⚠ 自逮（本回合 · 离线单测）：`R4` 首轮**未标** ⇒ 因尾段曾用 `[^\s]*`（无空白之句 ⇒ 吞尽全句
     ⇒ 后随之量词**永不独立成配**）⇒ 改为**至多两汉字**之**有界名词**（`[\u4e00-\u9fa5]{0,2}`）。 */
const PA_QV_PAT = /([0-9]+(?:\.[0-9]+)?)[ \t]*(小时|分钟|公里|个|只|条|张|页|台|份|名|位|件|人|组|元|块|角|分|天|米|斤|升|次|步|轮|席|枚|款|类|项|种)([\u4e00-\u9fa5]{0,2})/g;
const PA_QV_STOP = '可能是得而又再共总约均即则还也都就只每要须需做为等及或与和在有无不未了的依应据由使至多更最';
const PA_QV_OP = /[0-9+\-*/().=×÷＝≈<>]/;
function paSelfSameQty(t){
  const out = [], byKey = Object.create(null);
  const re = new RegExp(PA_QV_PAT.source, 'g');
  let m, n = 0;
  while((m = re.exec(t)) !== null){
    if(m.index === re.lastIndex) re.lastIndex++;
    if(++n > 120) break;
    const tail = m[3] || '';
    let noun = '';
    for(let k = 0; k < tail.length && k < 3; k++){
      const c = tail.charAt(k);
      if(!/[\u4e00-\u9fa5]/.test(c)) break;          /* 非汉字 ⇒ 名词止 */
      if(PA_QV_STOP.indexOf(c) >= 0) break;          /* 停用字（可 ／ 做 ／ 共 …）⇒ 名词止 */
      noun += c;
      if(noun.length >= 2) break;
    }
    if(!noun) continue;                              /* 承 ⒜：裸量词 ⇒ ⛔ 判 */
    const before = (m.index > 0) ? t.charAt(m.index - 1) : '';
    const tailStart = m.index + m[0].length - tail.length;
    const after = t.charAt(tailStart + noun.length);
    if(PA_QV_OP.test(before) || PA_QV_OP.test(after)) continue;   /* 承 ⒝：贴算子 ／ `=` ⇒ ⛔ 判 */
    const key = m[2] + noun, v = String(parseFloat(m[1]));
    const e = byKey[key] || (byKey[key] = {key:key, vals:[]});
    if(e.vals.indexOf(v) < 0) e.vals.push(v);
  }
  for(const k in byKey){ if(byKey[k].vals.length > 1) out.push(byKey[k]); }
  if(out.length) paSelfChkStat.mq += out.length;
  return out.slice(0, 2);
}
try{ window.paSelfSameQty = paSelfSameQty; }catch(e){}

/* ⭐ pm_1042 §三：答体自陈字数（如「15字」）之如实标 —— ⛔ 当读数（承「⛔ 以模型自陈当读数」）。
   只在问句含字数约束（「N 字」）时出（⛔ 泛贴 ⇒ 噪音）；本机⛔ 核字数
   （「实际字数」无单一指称 ⇒ 自动比对必是猜 ⇒ ⛔ 造第二条判据）。只入注记，⛔ 上屏当读数。 */
const PA_WC_SELF = /([0-9０-９]{1,4})\s*字/;
function paSelfWcNote(q, a){
  const s = String(q == null ? '' : q), t = String(a == null ? '' : a);
  if(!s || !t) return '';
  if(!/[0-9０-９]\s*字/.test(s)) return '';     /* 问句须含「N 字」之约束 */
  const m = t.match(PA_WC_SELF);
  if(!m) return '';
  return '答体自陈字数「' + m[0] + '」＝ 模型自陈（⛔ 本机读数 · 本机⛔ 核字数）⇒ 严格之字数请以正文为准。';
}
/* ⭐ pm_1036 §一／§二（**算径已通** · 工具 ＝ 判据**主源**）：把答体所写之式交**工具**算
   （POST /api/tools/calc ⇒ SafeCalculator · AST 白名单 · ⛔ eval）⇒ **工具值为主**；
   本机复核（paSelfArithCheck）**退为「标」** —— 工具答到即以工具值**就地升级**（⛔ 双报同一错）；
   工具不可达 ⇒ 保留「复核标」（其串已明标「⛔ 非工具」· ⛔ 以复核冒充工具）。
   ⚠ 界：工具侧⛔ 收 函数 ／ 逗号 ／ 单位 ／ 汉字 ⇒ 故**只交**本机已归一之**纯算式**（lhs）。
   ⚠ 界：本段**只**在「复核已标」时触发（⛔ 无标不扰 · ⛔ 造第二条判据）。 */
const PA_TOOL_CALC = '/api/tools/calc';
const PA_CHK_ATTRIB_BASE = '标 · 本机前端对读 · ⛔ 非工具 · ⛔ 我⛔ 替你判对错';
const PA_CHK_ATTRIB_TOOL = '工具 · /api/tools/calc（判据主源） · ⛔ 我⛔ 替你判对错';
let paSelfLastEq = null;   /* 侧道：本回**首个可判之式**（⛔ 判对错 ⇒ 只作数 · 供工具径） */
let paSelfChkSeen = 0;      /* ⭐ pm_1038 §三.1：本回 paSelfArithCheck 所见**可判之式**之数 */
const paSelfToolStat = {n:0, ok:0, miss:0, diff:0, last:'', lastAt:''};
function paSelfChkMark(attrib, eqText, mqTexts){
  const parts = [];
  if(eqText) parts.push(eqText);
  const m = mqTexts || [];
  for(let i = 0; i < m.length; i++){ if(m[i]) parts.push(m[i]); }
  if(!parts.length) return '';
  return '⚠ 复核（' + attrib + '）：' + parts.join(' ｜ ') + ' ⇒ 请复核。';
}
function paSelfToolCalc(expr){
  const ex = String(expr == null ? '' : expr);
  if(!ex) return Promise.resolve(null);
  let p;
  try{ p = fetch(PA_TOOL_CALC, {method:'POST', headers:{'Content-Type':'application/json'},
                                body: JSON.stringify({expr:ex})}); }
  catch(e){ return Promise.resolve(null); }
  return Promise.resolve(p).then(function(r){ return r.json(); }).then(function(d){
    if(!d || d.ok !== true) return null;
    const v = Number(d.value);
    return isFinite(v) ? v : null;
  }).catch(function(){ return null; });
}
/* 就地升级：用户面之「复核标」⇒ 换成**工具值**（工具为主源）；不可达 ⇒ ⛔ 动（留复核标）。 */
function paSelfToolUpgrade(div, ar, q){
  if(!div || !q || !ar) return;
  const oldU = ar.u || '', mqTexts = ar.mqTexts || [];
  paSelfToolCalc(q.lhs).then(function(tv){
    const now = new Date().toLocaleTimeString('zh-CN', {hour12:false});
    paSelfToolStat.n++; paSelfToolStat.lastAt = now;
    if(tv == null){
      paSelfToolStat.miss++;
      paSelfToolStat.last = '工具不可达 ⇒ 留复核标（' + q.disp + '）';
      return;
    }
    paSelfToolStat.ok++;
    const toolBad = (Math.abs(tv - q.saidNum) > q.tolNum);
    const chkBad = !!ar.eqText;
    let eqText;
    if(toolBad){
      eqText = '答体所写式「' + q.disp + '」与其自报值不符（工具算得 ' + paSelfChkR(tv) + ' ／ 其自报 ' + q.said + '）';
      paSelfToolStat.last = '工具逮「' + q.disp + '」＝ ' + paSelfChkR(tv) + ' ／ 其报 ' + q.said;
      if(chkBad){ paSelfToolStat.last += '（复核同向 ⇒ ⛔ 不双报）'; }
      else { paSelfToolStat.diff++; paSelfToolStat.last += '（复核未标 ⇒ 工具独逮）'; }
    } else {
      eqText = '';
      if(chkBad){ paSelfToolStat.diff++; paSelfToolStat.last = '⚠ 相左：复核标而工具判该式无误（' + q.disp + '）⇒ 报 PM'; }
      else { paSelfToolStat.last = '工具确认该式无误（' + q.disp + '）'; }
    }
    const newU = paSelfChkMark(PA_CHK_ATTRIB_TOOL, eqText, mqTexts);
    paSelfMarkSwap(div, oldU, newU);
  }).catch(function(e){
    paSelfToolStat.n++; paSelfToolStat.miss++;
    paSelfToolStat.last = '工具调用异常：' + String((e && e.message) || e);
  });
}
/* 同一条气泡内**就地替换**标串（⛔ 增删答体一字）＋ 注记留痕 ＋ 存档同步（⛔ 显示 ≢ 存档）。 */
function paSelfMarkSwap(div, oldU, newU){
  let hit = null;
  try{
    const root = div.querySelector('.bubble') || div;
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
    let n;
    while((n = w.nextNode())){ if(n.nodeValue && n.nodeValue.indexOf(oldU) >= 0){ hit = n; break; } }
    if(!hit){
      const w2 = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
      let k;
      while((k = w2.nextNode())){ if(k.nodeValue && k.nodeValue.indexOf('本机前端对读') >= 0){ hit = k; break; } }
      if(hit && !newU){ hit.nodeValue = ''; hit = null; }
    }
    if(hit){
      if(newU === '' && hit.nodeValue.indexOf(oldU) >= 0){ hit.nodeValue = hit.nodeValue.replace(oldU, ''); }
      else if(hit.nodeValue.indexOf(oldU) >= 0){ hit.nodeValue = hit.nodeValue.replace(oldU, newU); }
      else if(newU){ hit.nodeValue = newU; }
      else { hit.nodeValue = ''; }
    } else if(newU){
      const b = div.querySelector('.bubble') || div;
      const d2 = document.createElement('div');
      d2.className = 'paToolMark';
      d2.textContent = newU;
      b.appendChild(d2);
    }
  }catch(e){}
  try{
    const eb = div.querySelector('details.eng .engbody');
    if(eb){
      const t = paSelfToolStat;
      eb.textContent = eb.textContent + '\n工具径读数（/api/tools/calc · 判据主源）：' + t.last
        + ' ｜ 计：工具答 ' + t.ok + ' ／ 不可达 ' + t.miss + ' ／ 与复核相左 ' + t.diff + '（刻 ' + t.lastAt + '）';
    }
  }catch(e){}
  try{
    if(!oldU || typeof activeThread !== 'function') return;
    const th = activeThread(), arr = th && th.msgs;
    const m = arr && arr[arr.length-1];
    if(m && m.role === 'assistant' && typeof m.content === 'string' && m.content.indexOf(oldU) >= 0){
      m.content = m.content.replace(oldU, newU);
      if(typeof saveState === 'function') saveState();
    }
  }catch(e){}
}
try{ window.paSelfToolCalc = paSelfToolCalc; }catch(e){}
try{ window.paSelfToolStat = paSelfToolStat; }catch(e){}
try{ window.paSelfChkMark = paSelfChkMark; }catch(e){}
try{ window.paSelfLastEq = function(){ return paSelfLastEq; }; }catch(e){}

function paSelfArithCheck(a, q){
  const raw = String(a == null ? '' : a);
  const qs = String(q == null ? '' : q);   /* ⭐ pm_1042 §二.2：可选之问句（供归因 · ⛔ 改答体） */
  paSelfChkSeen = 0;
  if(!raw) return null;
  const t = paSelfChkNorm(raw);   /* ⚠ 先归一再看「=」：全角「＝」与半角同义（自逮：早退曾吞全角式） */
  /* ⭐ pm_1035 §三：同量多值**无 `=` 亦可判** ⇒ 早退去掉，式路改由下方 while 之闸自守。 */
  const mq = paSelfSameQty(t);
  const re = new RegExp(PA_CHK_EQ.source, 'g');
  const bad = [];
  let m, n = 0, firstEq = null;   /* ⭐ pm_1036：本回首个**可判之式**（⛔ 判对错） */
  while((t.indexOf('=') >= 0) && ((m = re.exec(t)) !== null)){
    if(m.index === re.lastIndex) re.lastIndex++;
    if(++n > 4) break;
    const lhs = m[1].replace(/[ \t]+/g, ' ').trim(), said = m[2];
    /* ⭐ 显示形取**原文之式**（归一为 1:1 逐字符映射 ⇒ 索引同）＋ 乘除号还原：
       ⚠ 自逮（真页实测）：若直显归一形（`*` ／ `/`），用户面经 MD 渲染 ⇒ `*` 被吃成斜体
       （现场见「式「200  1.1  0.9」」）⇒ 用户看不懂 ⇒ 故取原形并还原 × ／ ÷。 */
    const disp = raw.slice(m.index, m.index + m[1].length).replace(/[ \t]+/g, ' ').trim()
                   .replace(/\*/g, '×').replace(/\//g, '÷');
    const prev = (m.index > 0) ? t.charAt(m.index - 1) : '';
    if(/[0-9,.)]/.test(prev)) continue;            /* 数被截断（千分位 ／ 前接数字）⇒ 弃而不判 */
    let _d = 0;                                  /* ⭐ 式起于未闭合之（半角）括号内 ⇒ 截得之式⛔ 原文 ⇒ 弃（自逮） */
    for(let _k = 0; _k < m.index; _k++){ const _c = t.charAt(_k); if(_c === '(') _d++; else if(_c === ')' && _d > 0) _d--; }
    if(_d > 0) continue;
    if(!/[+\-*/]/.test(lhs)) continue;             /* 无运算符 ⇒ 非算式（「第 2 = 3」类） */
    let v;
    try{ v = paSelfChkEval(lhs); }catch(e){ continue; }   /* 式含他物 ／ 残缺 ⇒ 弃而不判（⛔ 猜） */
    const rhs = parseFloat(said);
    if(!isFinite(rhs)) continue;
    paSelfChkStat.n++;
    paSelfChkSeen++;
    const dot = said.indexOf('.');
    const tol = Math.max((dot >= 0) ? 0.5 * Math.pow(10, -(said.length - dot - 1)) : 0.5,
                         1e-9 * Math.abs(v));       /* 承「四舍五入⛔ 当错」：容差按答体所示位数给 */
    const _ok = Math.abs(v - rhs) <= tol;
    if(!firstEq) firstEq = {lhs:lhs, disp:disp, said:said, saidNum:rhs, got:paSelfChkR(v), tolNum:tol, ok:_ok};
    if(_ok) continue;
    paSelfChkStat.bad++;
    if(bad.length < 2) bad.push({lhs:lhs, disp:disp, got:paSelfChkR(v), said:said, tol:paSelfChkR(tol)});
  }
  /* ⭐ pm_1042 §二.2：**无 `=`** 之答体 ⇒ 取「数字-算子」之**最长连续段**（剥单位 ／ 汉字 ／ 字母）
     ⇒ 与本答体之**量词报值**对读 ⇒ 不符则出「式不符」标（承：只作标 · ⛔ 替你判对错）。 */
  if(!firstEq && t.indexOf('=') < 0){
    const runs = paSelfChkRuns(t);
    if(runs.length){
      let best = runs[0];
      for(let i = 1; i < runs.length; i++){ if(runs[i].len > best.len) best = runs[i]; }
      const operandNums = (best.run.match(/[0-9]+(?:\.[0-9]+)?/g) || []).map(function(x){ return parseFloat(x); });
      const rv = paSelfChkReported(t, best.index, best.end, operandNums);
      if(rv){
        paSelfChkStat.n++; paSelfChkSeen++;
        const dispR = best.run.replace(/\*/g, '×').replace(/\//g, '÷');
        const tolR = Math.max(0.5, 1e-9 * Math.abs(best.v));
        const okR = Math.abs(best.v - rv.num) <= tolR;
        firstEq = {lhs:best.run, disp:dispR, said:String(rv.num), saidNum:rv.num,
                   got:paSelfChkR(best.v), tolNum:tolR, ok:okR, mode:'run'};
        paSelfChkStat.nr2 = (paSelfChkStat.nr2 || 0) + 1;
        if(!okR){
          paSelfChkStat.bad++;
          if(bad.length < 2) bad.push({lhs:best.run, disp:dispR, got:paSelfChkR(best.v), said:String(rv.num), tol:paSelfChkR(tolR)});
        }
      }
    }
  }
  paSelfLastEq = firstEq;   /* ⭐ pm_1036：交工具径（⛔ 判对错 ⇒ 只作数） */
  if(!bad.length && !mq.length) return null;
  const b0 = bad.length ? bad[0] : null;
  /* ⭐ pm_1035 §二（你之裁 · 留但降级为「标」）：措辞只许写「答体所写式与其自报值不符」
     —— ⛔ 写「答案错」（复核⛔ 判对错 · **工具径才是判据主源** · 承 L83 单源 · 我 ⛔ 双报同一错）。 */
  const mark = [];
  const eqText = b0 ? ('答体所写式「' + b0.disp + '」与其自报值不符（本机前端重算 ' + b0.got + ' ／ 其自报 ' + b0.said + '）') : '';
  if(eqText) mark.push(eqText);
  const mqTexts = [];
  for(let i = 0; i < mq.length; i++){
    mqTexts.push('同量多值：答体对「' + mq[i].key + '」写出 ' + mq[i].vals.length + ' 个不同数值（' + mq[i].vals.join(' ／ ') + '）');
  }
  for(let i = 0; i < mqTexts.length; i++) mark.push(mqTexts[i]);
  if(b0){ paSelfChkStat.last = b0.disp + ' ⇒ 重算 ' + b0.got + ' ／ 其报 ' + b0.said; }
  else if(mq.length){ paSelfChkStat.last = mq[0].key + ' ⇒ ' + mq[0].vals.join(' ／ '); }
  const u = paSelfChkMark(PA_CHK_ATTRIB_BASE, eqText, mqTexts);
  const e = '答体复核（⛔ 改答体一字 · 原式原值照留于答中）：式不符 ' + paSelfChkStat.bad + ' 条 ／ 同量多值 ' + paSelfChkStat.mq + ' 处'
          + '（本次 ' + bad.length + ' ／ ' + mq.length + ' · 本页累计已核 ' + paSelfChkStat.n + ' 条式）'
          + bad.map(function(x){ return '\n式「' + x.disp + '」（重算式「' + x.lhs + '」）本机前端重算 = ' + x.got + ' ／ 答体所写 = ' + x.said + '（容差 ' + x.tol + '）'; }).join('')
          + mq.map(function(x){ return '\n同量「' + x.key + '」之值：' + x.vals.join(' ／ '); }).join('')
          + '\n⚠ 界限（⛔ 假读数）：式内含字母 ／ 单位 ／ 汉字者⛔ 判；**裸量词**（件 ／ 个 ／ 人）⛔ 判；'
          + '数与「算子 ／ =」紧邻者⛔ 判（换算非矛盾）⇒ 本标⛔ 覆盖全部不一致'
          + '；工具径：POST /api/tools/calc（判据主源）｜技能面仍未实装（已转产品线）。';
  return {u:u, e:e, eqText:eqText, mqTexts:mqTexts, eq0:firstEq};
}
try{ window.paSelfArithCheck = paSelfArithCheck; }catch(e){}
try{ window.paSelfChkEval = paSelfChkEval; }catch(e){}
try{ window.paSelfChkStat = paSelfChkStat; }catch(e){}
try{ window.paSelfChkNorm = paSelfChkNorm; }catch(e){}
/* ⭐ pm_1033 §一 ⓞ（留痕读数）：把「检索命中 ／ 未命中 ／ 回落」做成**可见读数**（自述面 · 关于 PA）
   ⇒ ⛔ 让回落把检索面之病**盖住**（承「⛔ 假绿」）。计数**只在本页会话内**（⛔ 冒充历史累计）；
   真源 ＝ /v9/pa/ask 之返回（grounded ／ refused）＋前端之回落动作；逐条留最近一问之去向。 */
const paSelfAskStat = {t0:'', hit:0, miss:0, fallback:0, fallbackFail:0, askFail:0, direct:0, lastQ:'', lastRoute:'', lastAt:'',
  lastScope:[], lastFaces:null, lastSearched:null, lastFacesAt:'', lastFacesRead:'', lastKbRoot:'',
  lastFacesMissing:null, lastFacesSkipped:null,
  lastJudge:null, lastArchiveHits:null, lastAnswerSource:''};
function paSelfAskStatGet(){
  const s = paSelfAskStat;
  return {t0:s.t0, hit:s.hit, miss:s.miss, fallback:s.fallback, fallbackFail:s.fallbackFail,
          askFail:s.askFail, direct:s.direct, lastQ:s.lastQ, lastRoute:s.lastRoute, lastAt:s.lastAt,
          chk:paSelfChkStat.n, chkBad:paSelfChkStat.bad, chkNr:paSelfChkStat.nr,
          lastScope:paSelfAskStat.lastScope, lastFaces:paSelfAskStat.lastFaces, lastSearched:paSelfAskStat.lastSearched,
          lastKbRoot:paSelfAskStat.lastKbRoot,
          lastFacesMissing:paSelfAskStat.lastFacesMissing, lastFacesSkipped:paSelfAskStat.lastFacesSkipped,
          lastJudge:paSelfAskStat.lastJudge, lastArchiveHits:paSelfAskStat.lastArchiveHits,
          lastAnswerSource:paSelfAskStat.lastAnswerSource};
}
function paSelfAskBump(kind, q, note){
  if(!paSelfAskStat.t0){ paSelfAskStat.t0 = new Date().toLocaleTimeString('zh-CN', {hour12:false}); }
  try{ if(typeof paSelfAskStat[kind] === 'number') paSelfAskStat[kind]++; }catch(e){}
  if(kind !== 'fallbackFail'){
    if(q != null) paSelfAskStat.lastQ = String(q).slice(0, 60);
    paSelfAskStat.lastRoute = String(note == null ? kind : note);
    paSelfAskStat.lastAt = new Date().toLocaleTimeString('zh-CN', {hour12:false});
  }
  try{ if(typeof paSourceStatRender === 'function') paSourceStatRender(); }catch(e){}
  return paSelfAskStatGet();
}
/* ⭐ pm_1102 §二.3：`label_hits` ⇒ **诊断态**（⛔ 常驻用户面）—— 落「更多 ▾ · ③ 设 · 关于 PA」诊断区，
   并**逐标签分列**（承 L186：⛔ 以一族之一员概全族）。档之值取**本会话**（`activeThread().paMode`
   ⇒ 缺则继承 `localStorage.pa_chat_mode` ⇒ 缺则 `companion`）；回执之 mode ／ `label_hits` 取
   **后端回执**（承 L76 · ⛔ 前端自说）。 */
function paSelfModeDiagHtml(){
  var d = null;
  try{ d = (typeof window.paChatModeDiag === 'function') ? window.paChatModeDiag() : null; }catch(e){ d = null; }
  if(!d) return '<div class="s">场合拨杆（诊断）：尚无本页数据（对话件未加载）。</div>';
  var THREE = ["\u7ed3\u8bba\uff1a", "\u9ed8\u8ba4\u9879\uff1a", "\u53ef\u9009\u9879\uff1a"];
  var hits = d.labelHits, byLabel = d.hitsByLabel || {};
  var inHit = function(k){ return !!(hits && typeof hits.indexOf === 'function' && hits.indexOf(k) >= 0); };
  var per = THREE.map(function(k){ return k + (hits == null ? '?' : (inHit(k) ? '命中' : '未中')); }).join(' ／ ');
  var acc = THREE.map(function(k){ return k + (typeof byLabel[k] === 'number' ? byLabel[k] : 0); }).join(' ／ ');
  var sameTxt = (d.same === true) ? '✓ 与档同' : ((d.same === false) ? '⚠ ≠ 档' : '（尚无对账）');
  return '<div class="s">⭐ 场合拨杆（诊断 · 本会话）：' + paSelfEsc(d.modeLabel || d.mode || '—')
    + '（会话 ' + paSelfEsc(d.sessionId || '—') + ' · ' + (d.threadStored ? '会话自存' : '继承上次') + '）'
    + ' ｜ 回执 mode：' + paSelfEsc(d.receiptModeLabel || d.receiptMode || '—') + ' ' + sameTxt
    + '（刻 ' + paSelfEsc(d.at || '刻未记') + '）</div>'
    + '<div class="s">模板标签（诊断 · 本轮 · 逐列 · 承 L186）：' + paSelfEsc(per) + '</div>'
    + '<div class="s">模板标签（诊断 · 本页累计 · 已收 ' + paSelfEsc(String(d.rounds == null ? 0 : d.rounds)) + ' 轮 · 逐列）：' + paSelfEsc(acc)
    + '　（真源：/v9/pa/dialog 回执 route.label_hits ⇒ ⛔ 常驻用户面）</div>';
}
function paSelfAskStatHtml(){
  const s = paSelfAskStat;
  const r = function(n, v, d){
    return '<div class="r"><span class="n">' + paSelfEsc(String(v == null ? 0 : v)) + '</span><span class="k">'
      + paSelfEsc(n) + '</span><span class="s">' + paSelfEsc(d) + '</span></div>';
  };
  return '<div class="a" id="paAskStatBox"><div class="q">检索统计读数（本页会话 · ⛔ 非历史累计）</div><div class="t">'
    + r('检索命中（有据 ⇒ 贴据）', s.hit, '真源：/v9/pa/ask 之 grounded:true')
    + r('检索未命中（无据）', s.miss, '真源：/v9/pa/ask 之 refused ／ grounded:false')
    + r('回落模型（未命中 ⇒ 转 /v9/pa/dialog）', s.fallback, '其中失败 ' + s.fallbackFail + ' 次（模型 ／ 通道不可达）')
    + r('未过闸直问模型（分类 other）', s.direct, '真源：paAskDomain 判 other ⇒ ⛔ 打 /v9/pa/ask')
    + r('闸自身失败（未取得回报）', s.askFail, '真源：/v9/pa/ask 请求异常 ⇒ 按 other 路走')
    /* ⚠ 自逮（真页读数 · 2026-10-04）：此行原写 s.chkBad ／ s.chk（意图取 paSelfAskStat）
       ⇒ 而该二键在 paSelfAskStat 上并不存在 ⇒ About 面出「undefined ／ undefined」（正禁词之族）
       ⇒ 改读算器自身之 paSelfChkStat。 */
    + r('答体复核（式不符 ／ 同量多值 ／ 已核）', paSelfChkStat.bad + ' ／ ' + paSelfChkStat.mq + ' ／ ' + paSelfChkStat.n, '真源：答体自陈之式与量 ⇒ 本机前端对读（⛔ 非工具 · 判据主源见工具径）')
    /* ⭐ pm_1038 §三.1：**单列一格** —— 算术类问 ∧ 答体无可判之式 ⇒ 「未复核」之数（⛔ 混入上一行）。 */
    + r('算术问而未复核（答体无可判之式）', paSelfChkStat.nr, '真源：算术类问 ∧ 答体无可判之式 ⇒ 本机与工具皆⛔ 核（⛔ 泛标顶替）')
    + (s.lastQ
        ? ('<div class="s">起计刻 ' + paSelfEsc(s.t0 || '本页尚未起计') + ' ｜ 最近一问「' + paSelfEsc(s.lastQ) + '」⇒ ' + paSelfEsc(s.lastRoute || '去向未判') + '（' + paSelfEsc(s.lastAt || '刻未记') + '）</div>')
        : ('<div class="s">起计刻 ' + paSelfEsc(s.t0 || '本页尚未起计') + ' ｜ 最近一问：本页尚未发问</div>'))
    + '<div class="s">⭐ 回落不掩病：未命中数照记（⛔ 因答成功而不计）；本行可回指：请到「更多 ▾ · ③ 设 · 关于 PA」重读。</div>'
    + '<div class="s">检索面（最近一次 · 源 /v9/pa/ask 之 scope ／ faces ／ searched）：'
      + paSelfEsc(paSelfFaceText(paSelfAskStat.lastScope, paSelfAskStat.lastFaces) || '未检（本页尚未检索）')
      + ' ｜ ' + (paSelfAskStat.lastSearched == null
          ? '共搜：本页尚未检索'
          : ('共搜 ' + paSelfEsc(paSelfAskStat.lastSearched) + ' 件（刻 ' + paSelfEsc(paSelfAskStat.lastFacesAt || '刻未记') + '）'))
      + '</div>'
    + '<div class="s">' + paSelfEsc(paSelfJudgeLine()) + '</div>'
    + paSelfModeDiagHtml()
    + '</div></div>';
}
try{ window.paSelfAskStatGet = paSelfAskStatGet; }catch(e){}
try{ window.paSelfAskBump = paSelfAskBump; }catch(e){}
try{ window.paSelfAskStatHtml = paSelfAskStatHtml; }catch(e){}

/* ⭐ pm_1032 §三.4（判据透明度）：分流之**理由**（命中哪个词）⇒ 可回指（用户可自查为何走此径）。 */
function paSelfWhy(text){
  const s = String(text == null ? '' : text), out = [];
  let k = null, l = null;
  try{ k = s.match(new RegExp(PA_ASK_KNOW.source, 'g')); }catch(e){}
  try{ l = s.match(new RegExp(PA_LOCAL_PAT.source, 'g')); }catch(e){}
  if(k && k.length) out.push('问句词表命中「' + k.slice(0,3).join(' ／ ') + '」');
  out.push((l && l.length) ? ('本机词表命中「' + l.slice(0,3).join(' ／ ') + '」⇒ 判本机素材类')
                           : '本机词表未命中 ⇒ 判域外类');
  return out.join(' ｜ ');
}
/* ⭐ pm_1067 §三 ⒝（承 pm_1066 §一）：源之分标旁须带**采样刻**（素材面在长 ⇒ 同问之据随刻变）
   ⇒ 刻取本回响应之 judge.face_snapshot_at ∨ judge_at（⛔ 前端自造刻 · 承 L76）；本轮开头清空（⛔ 跨轮串刻）。 */
let paSelfTagAt = '';
function paSelfTag(kind, n){
  var at = paSelfTagAt ? (' · 采于 ' + paSelfTagAt) : '';
  if(kind === 'local') return '📎 源之分标：本机素材（据 ' + ((n == null || n === '') ? '—' : n) + ' 条）' + at;
  if(kind === 'localmiss') return '📎 源之分标：本机素材（未命中）' + at;
  /* ⭐ pm_1076 §三（承 L103 形与义分 · L142 声明⟷执行须符）：本态 ⛔ 单标 ——
     闸之判（**本机无据 ⇒ 拒答**）∧ 其后**回落模型且模型真答** ⇒ 二者**两段并标**：
     ⛔ 只留「拒答」（用户以为没答）／ ⛔ 只留「由模型作答」（用户以为本机有据）。
     ⚠ 本 kind 唯 `addMsg` 包装之 `if(fbf)` 支调用 —— `fbf` ⇒ 闸 `refused` 已真（见 `paAskGate` 包装 :1897–1919）⇒ 无「未过闸」之歧（承 L135）。 */
  if(kind === 'fallback') return '📎 源之分标：闸：本机无据（拒答）→ 已回落模型 ⇒ 由模型作答（⛔ 非本机素材）' + at;
  if(kind === 'none')  return '📎 源之分标：超出本机素材范围（未答）' + at;
  if(kind === 'ctx')     return '📎 源之分标：按本会话上一句答 · ⛔ 检索面' + at;
  if(kind === 'ctxmiss') return '📎 源之分标：本会话无可读上一句';
  /* ⭐ pm_1073 §二.1（承 L103 形与义分）：拒答 ＝ **正果**（承「有据才答」）⇒ 其标须自成一格
     （⛔ 借 'none' 之「超出本机素材范围」—— 那是**域判**，非「有据才答」之果 ／ ⛔ 借 'localmiss' —— 那是**面判**）。 */
  if(kind === 'refuse')  return '📎 源之分标：本机无据 ⇒ 拒答（⛔ 我编）' + at;
  /* ⭐ pm_1070 §三：词表缺 ⇒ 整轮「不可判」（⛔ 引 · ⛔ 静默放行）—— 后端 `_last_user_before` 已真排自测痕（前端 ⛔ 最后防线 · 承 L83）。 */
  if(kind === 'undec')   return '📎 源之分标：不可判 —— 自测痕词表未取到';
  if(kind === 'nil') return '';
  return '📎 源之分标：模型生成（⛔ 非本机素材）' + at;
}
try{ window.paSelfTag = paSelfTag; }catch(e){}
function paEngHit(s){ return PA_ENG_WORDS.test(String(s == null ? '' : s)); }
function paEngHtml(eng){
  const t = String(eng == null ? '' : eng).trim();
  if(!t) return '';
  return '<details class="eng"><summary>来源 ／ 详情</summary><div class="engbody">' + paSelfEsc(t) + '</div></details>';
}
/* 把「原始报错」类词换成人话（⛔ 裸异常串上屏 · 承 pm_1012 §四 令③） */
function paHumanizeErr(s){
  let t = String(s == null ? '' : s);
  if(!/Failed to fetch|NetworkError|TypeError|\[object |undefined/.test(t)) return t;
  t = t.split('Failed to fetch').join('连不上后端')
       .split('NetworkError').join('网络中断')
       .replace(/TypeError[^\s，。；、）]*/g, '类型错误')
       .replace(/\[object [^\]]*\]/g, '（不可读对象）')
       .split('undefined').join('未知');
  return t;
}
/* ⭐ 存量消息之文案分层（显示层 · ⛔ 动存档 · pm_1012 §一/§二）：此前各轮所存之消息里，
   用户面夹带工程语（件号 ／ 律号 ／ 机制词）⇒ **按行**分出：含工程词之行入折叠注记，余者留用户面；
   原文一字不改地留在注记里（⛔ 丢信息）。存档（localStorage 之 pa_state）⛔ 动 —— 只改「怎么显示」。 */
function paSelfLegacySplit(s){
  const t = String(s == null ? '' : s);
  if(!paEngHit(t) && !PA_ENG_ERR.test(t)) return null;
  const lines = t.split('\n');
  const u = [], e = [];
  lines.forEach(function(x){ ((paEngHit(x) || PA_ENG_ERR.test(x)) ? e : u).push(x); });
  let U = u.join('\n').trim();
  if(!U) U = '（这条既有消息整条都是工程注记 —— 点「来源 ／ 详情」看原文。）';
  return {u:U, e:'（既有消息之工程注记 · 原文照录）\n' + t};
}
/* ⭐ 存量运行记录之分层（显示层 · pm_1012 §一）：此前各轮所存之运行记录里含工程语
   ⇒ 用户面只留**首个工程词之前**的那段（例「✅ 已受理」），原文整条入 title（悬停可见 · ⛔ 丢信息）；
   存档一字不改 —— 若整条以工程词开头 ⇒ 只显一句中性提示。 */
function paLogHuman(line){
  const t = String(line == null ? '' : line);
  if(!paEngHit(t) && !PA_ENG_ERR.test(t)) return null;
  const m = t.match(PA_ENG_WORDS) || t.match(PA_ENG_ERR);
  let head = m ? t.slice(0, m.index) : '';
  head = head.replace(/[\s\u00b7\uFF5C|\u3001\uFF0C,\uFF1A:\uFF0F\/\u2014-]+$/, '').trim();
  if(head.length < 2) head = '\u26a0 \u65e2\u6709\u8fd0\u884c\u8bb0\u5f55';
  return head + '\uFF08\u5DE5\u7A0B\u6CE8\u8BB0\u89C1\u4E0B\u65B9\u300C\u539F\u6587\u300D\uFF09';
}
/* ⭐ 运行记录之注记（承 pm_1013 §三 · 显示层）：存量（存档回放）之运行记录**不经** addLog 包装 ⇒
   此处补一道扫：凡 `.tool-log` 含禁词 ／ 裸异常词 ／ 旧拒答话术（「查不到」）⇒ 用户面只留人话头段，
   原文整条入 `title`（悬停可回指）＋ `data-raw`（机读回指）＋ 折叠注记（可点）。⛔ 丢信息 ／ ⛔ 动存档。 */
function paEngNoteEl(raw){
  const d = document.createElement('details');
  d.className = 'eng';
  d.innerHTML = '<summary>原文</summary><div class="engbody"></div>';
  d.querySelector('.engbody').textContent = String(raw == null ? '' : raw);
  return d;
}
/* ⭐ 内部计数之形（`×N`）之判与清（承 pm_1026 §一 令① ／ pm_1028 §一.1）：
   生成点在共用件（products.js:298 写 DOM · :302 写存档），放大点在 chat.js:52
   （重渲染**再喂**已含 `×N` 之存档文本 ⇒ 键变 ⇒ 重复行 ／ 单元素叠成 `×A ×B`）
   ⇒ ⛔ 我动共用件 ⇒ 于 v3 专用件①最外层剥（键稳）②收尾擦（用户面 ⛔ 见）。
   计数 ⛔ 丢 ⇒ 入 data-n ＋ title ＋ 折叠注记（承 L76）。
   ⚠ 之形须**前置空白**（⛔ 误伤 `1280×720` 之尺寸记法）。 */
const PA_MUL_RE = /[ \t\u3000]×\d+(?=\s|$)/g;
function paSelfMulHit(s){ return /(?:^|\s)×\d+(?=\s|$)/.test(String(s == null ? '' : s)); }
function paSelfMulClean(s){
  return String(s == null ? '' : s).replace(PA_MUL_RE, '').replace(/[ \t\u3000]{2,}/g, ' ').trim();
}
function paSelfMulPass(){
  const t = document.getElementById('thread'); if(!t) return 0;
  const els = t.querySelectorAll('.tool-log'); let n = 0;
  for(let i=0;i<els.length;i++){
    const el = els[i];
    const s = String(el.textContent || '');
    if(!paSelfMulHit(s)) continue;
    const mul = (s.match(/(?:^|\s)×(\d+)(?=\s|$)/) || [, ''])[1];
    const clean = paSelfMulClean(s) || s.trim();
    const hum = paLogHuman(clean);
    const note = String(el.__engNote || el.dataset.raw || clean);
    el.__engNote = note;
    el.textContent = (hum ? hum : clean);
    el.setAttribute('data-raw', note);
    el.setAttribute('data-n', mul);
    if(el.dataset.mulBase === undefined) el.dataset.mulBase = String(el.title || '');
    el.title = (el.dataset.mulBase ? (el.dataset.mulBase + ' ｜ ') : '') + '合并计数 本轮 ×' + mul;
    if(!el.querySelector('details.eng')) el.appendChild(paEngNoteEl(note + '\n（合并计数：本轮 ×' + mul + '）'));
    n++;
  }
  return n;
}
try{ window.paSelfMulPass = paSelfMulPass; }catch(e){}

/* ⭐ 测试痕（承 pm_1027 §二 · pm_1029 §二.① · **改 pm_1031 §三.3**）与「一键收起／展开」：
   本线程之语料经**真页真发**入真账（⛔ 删真账 ／ ⛔ 改历史）⇒ 显示层补标 ＋ 可一键收起。
   ⭐ pm_1031 §三.3 之裁 —— **改「全线程标痕」为「清单外置 ＋ 新行默不标」**：
     ⓜ 标痕清单**外置**：`web/pa/测试痕_清单.json`（记「已标到哪一轮 ／ 哪一条」）⇒ 页面**只读**（⛔ 页面自算）。
     ⓝ **新行默认 ⛔ 标**（**fail-open 于真问**）：一条 user 行入 `.ttround` ⇒ 須
        ① 活动线程 ≡ 清单之 `thread_id` ② 其序（1 基）≤ `mark_upto_user_index` ③ 末条锚点符
     ⇒ ⭐ **老板之真问永不被收起**（真问必在清单上界**之外**）。
     ⚠ 清单**未取到** ／ 线程不符 ／ 锚点不符 ⇒ **一条也不标**（⛔ 收起 —— ⛔ 冒「真问被吞」之险）。
   收起 ＝ 显示层隐藏（⛔ 删账 ／ ⛔ 动存档）：以「轮」为单元（一条 `.msg.user` ＋ 其后至下一条 user 之行）。 */
let paSelfTTCollapsed = true;
let paSelfTTManifest = null;      /* 外置清单（⛔ 页面自算） */
let paSelfTTLoading = false;
let paSelfTTTryAt = 0;
const PA_TT_MANIFEST = 'pa/测试痕_清单.json';
async function paSelfTTManifestLoad(force){
  if(paSelfTTManifest && !force) return paSelfTTManifest;
  const d = await paSelfJson(PA_TT_MANIFEST);
  if(d && typeof d === 'object') paSelfTTManifest = d;
  else if(force) paSelfTTManifest = null;
  return paSelfTTManifest;
}
function paSelfTTEnsure(){
  if(paSelfTTManifest || paSelfTTLoading) return;
  if(Date.now() - paSelfTTTryAt < 5000) return;
  paSelfTTTryAt = Date.now(); paSelfTTLoading = true;
  paSelfTTManifestLoad(true).then(function(){ paSelfTTLoading = false; try{ paSelfTestTracePass(); }catch(e){} },
                                   function(){ paSelfTTLoading = false; });
}
function paSelfTTRowText(el){
  if(!el) return '';
  let c = null; try{ c = el.cloneNode(true); }catch(e){ return ''; }
  const sp = c.querySelectorAll('.ttrace');
  for(let i=0;i<sp.length;i++){ if(sp[i].parentNode) sp[i].parentNode.removeChild(sp[i]); }
  const bx = c.querySelector('.bubble') || c;
  return String(bx.textContent || '');
}
function paSelfTTBound(){
  const m = paSelfTTManifest; if(!m) return null;
  const tid = String(m.thread_id || '');
  if(tid){
    let cur = '';
    try{ cur = (typeof curSession === 'function') ? String(curSession()) : ''; }catch(e){ cur = ''; }
    if(cur && cur !== tid) return null;                 /* 线程不符 ⇒ ⛔ 标 */
  }
  const upto = Number(m.mark_upto_user_index);
  if(!isFinite(upto) || upto <= 0) return null;
  return {upto:upto, anchor:m.anchor_last || null, thread:tid};
}
function paSelfTTMarkedIndexes(ms){
  const b = paSelfTTBound(); if(!b) return null;
  if(b.anchor && b.anchor.head){
    const k = Number(b.anchor.index);
    if(isFinite(k) && k >= 1 && k <= ms.length){
      if(paSelfTTRowText(ms[k-1]).indexOf(String(b.anchor.head)) < 0) return null;   /* 锚点不符 ⇒ 清单已不描述本线程 ⇒ ⛔ 标 */
    }
  }
  const out = [], n = Math.min(b.upto, ms.length);
  for(let i=1;i<=n;i++) out.push(i);
  return out;
}
function paSelfTestTraceApply(){
  const t = document.getElementById('thread'); if(!t) return null;
  const ms = t.querySelectorAll('.msg.user');
  const mark = paSelfTTMarkedIndexes(ms);
  const kids = t.children; let cur = null, testRounds = 0, testRows = 0, realRounds = 0, rows = 0, uidx = 0;
  for(let i=0;i<kids.length;i++){
    const el = kids[i];
    if(!el.classList || el.classList.contains('ttracebar') || el.classList.contains('selfwait')) continue;
    rows++;
    const isUser = el.classList.contains('msg') && el.classList.contains('user');
    if(isUser){
      uidx++;
      const ok = !!(mark && mark.indexOf(uidx) >= 0);
      cur = ok ? el : null;
      if(ok) testRounds++; else realRounds++;
    }
    if(cur){ if(!el.classList.contains('ttround')) el.classList.add('ttround'); testRows++; }
    else if(el.classList.contains('ttround')) el.classList.remove('ttround');
  }
  if(!mark){ if(t.classList.contains('tthide')) t.classList.remove('tthide'); }
  else if(paSelfTTCollapsed){ if(!t.classList.contains('tthide')) t.classList.add('tthide'); }
  else if(t.classList.contains('tthide')) t.classList.remove('tthide');
  return {rows:rows, testRounds:testRounds, testRows:testRows, realRounds:realRounds,
          hidden:(!!mark && paSelfTTCollapsed), noManifest:!mark};
}
function paSelfTestTraceBar(st){
  const t = document.getElementById('thread'); if(!t) return null;
  let b = document.getElementById('paTestTraceBar');
  const show = !!(st && st.testRows > 0);
  if(!show){ if(b && b.parentNode) b.parentNode.removeChild(b); return null; }
  if(!b){
    b = document.createElement('div'); b.id = 'paTestTraceBar'; b.className = 'ttracebar';
    const sp = document.createElement('span'); sp.className = 'ttinfo';
    const btn = document.createElement('button'); btn.className = 'ttbtn'; btn.type = 'button';
    btn.addEventListener('click', function(){ paSelfTTCollapsed = !paSelfTTCollapsed; try{ paSelfTestTracePass(); }catch(e){} });
    b.appendChild(sp); b.appendChild(btn);
    t.insertBefore(b, t.firstChild);
  }
  const sp = b.querySelector('.ttinfo'), btn = b.querySelector('.ttbtn');
  const m = paSelfTTManifest || {};
  const want = '🧪 测试痕 ' + ((st && st.testRows) || 0) + ' 行' + (paSelfTTCollapsed ? '已收起' : '已展开')
    + '（真问 ' + ((st && st.realRounds) || 0) + ' 轮 · 源 #thread 行 ' + ((st && st.rows) || 0)
    + ' · 清单上界 ' + ((m.mark_upto_user_index == null) ? '—' : m.mark_upto_user_index) + '）';
  const wtxt = paSelfTTCollapsed ? '展开' : '收起';
  if(sp && sp.textContent !== want) sp.textContent = want;
  if(btn && btn.textContent !== wtxt) btn.textContent = wtxt;
  const wt = '测试痕为显示层补标（语料为 CW ／ PM 之测试输入 · 2026-10-04）；清单外置：' + PA_TT_MANIFEST
    + '（记「已标到哪一条」）⇒ 新行默认 ⛔ 标（真问永不被收起）｜收起 ⛔ 删账（存档一字未动）';
  if(b.title !== wt) b.title = wt;
  return b;
}
function paSelfTestTracePass(){
  const t = document.getElementById('thread');
  if(!t) return {bar:0, marks:0, rows:0, testRows:0, realRounds:0, hidden:true, noManifest:true};
  paSelfTTEnsure();
  const ms = t.querySelectorAll('.msg.user');
  const mark = paSelfTTMarkedIndexes(ms);
  let marks = 0, unmarked = 0;
  for(let i=0;i<ms.length;i++){
    const ok = !!(mark && mark.indexOf(i+1) >= 0);
    const has = !!ms[i].querySelector('.ttrace');
    if(ok && !has){
      const sp = document.createElement('span');
      sp.className = 'ttrace';
      sp.textContent = '🧪 测试痕';
      sp.title = '本问为语料测试输入（清单点名：' + PA_TT_MANIFEST + ' · 序 ' + (i+1) + '）· ⛔ 非老板之真问（存档未改 · 仅显示层补标）';
      const bx = ms[i].querySelector('.bubble') || ms[i];
      bx.appendChild(sp);
      marks++;
    } else if(!ok && has){
      const sp = ms[i].querySelector('.ttrace');
      if(sp && sp.parentNode) sp.parentNode.removeChild(sp);
      unmarked++;
    }
  }
  const st = paSelfTestTraceApply();
  const bar = paSelfTestTraceBar(st) ? 1 : 0;
  return {bar:bar, marks:marks, unmarked:unmarked, userRows:ms.length, testRows:(st?st.testRows:0),
          realRounds:(st?st.realRounds:0), rows:(st?st.rows:0), hidden:(st?st.hidden:false),
          noManifest:!!(st && st.noManifest), manifest:!!paSelfTTManifest,
          upto:(paSelfTTManifest && paSelfTTManifest.mark_upto_user_index) || null};
}
try{ window.paSelfTestTracePass = paSelfTestTracePass; }catch(e){}
try{ window.paSelfTTSet = function(v){ paSelfTTCollapsed = !!v; return paSelfTestTracePass(); }; }catch(e){}
try{ window.paSelfTTGet = function(){ return paSelfTTCollapsed; }; }catch(e){}
try{ window.paSelfTTManifestLoad = paSelfTTManifestLoad; }catch(e){}
try{ window.paSelfTTMf = function(v){ if(arguments.length){ paSelfTTManifest = (v === null ? null : v); } return paSelfTTManifest; }; }catch(e){}

function paEngCleanThread(){
  const t = document.getElementById('thread'); if(!t) return 0;
  const els = t.querySelectorAll('.tool-log');
  let n = 0;
  for(let i=0;i<els.length;i++){
    const el = els[i];
    if(el.__engNote){   /* 已识：合并路径会 textContent 重置 ⇒ 注记须补回 */
      if(!el.querySelector('details.eng')){ el.appendChild(paEngNoteEl(el.__engNote)); n++; }
      continue;
    }
    const s = el.textContent || '';
    if(!paEngHit(s) && !PA_ENG_ERR.test(s)) continue;
    const mul = (s.match(/(?:^|\s)×(\d+)(?=\s|$)/) || [, ''])[1];
    const body = paSelfMulClean(s);
    const h = paLogHuman(body); if(!h) continue;
    el.title = (el.title ? (el.title + ' ｜ ') : '') + body + (mul ? (' ｜ 合并计数 本轮 ×' + mul) : '');
    el.setAttribute('data-raw', body);
    el.__engNote = body;
    el.textContent = h;
    el.appendChild(paEngNoteEl(body + (mul ? ('\n（合并计数：本轮 ×' + mul + '）') : '')));
    n++;
  }
  return n;
}
try{ window.paEngCleanThread = paEngCleanThread; }catch(e){}

/* ⭐ 「更多 ▾」抽屉之过程引用清理（pm_1012 §二 · 显示层）：抽屉里有些说明句尾挂「承 pm_xxxx §x」／「（L76）」
   这类**过程引用** —— 用户面只留人话，被剥下的原文整段入「来源 ／ 详情」（⛔ 丢信息）。
   ⚠ 只剥过程引用（承 ／ 件号 ／ 律号）—— 「真源：GET …」这类**来源行照留**（PM 令：各面须标真源名）。 */
const PA_ENG_SEG = [
  /\s*[·\uFF5C|]\s*承\s*pm_\d+[^\uFF0C\u3002\uFF1B\uFF09)\u300D]*/g,
  /\s*承\s*pm_\d+[^\uFF0C\u3002\uFF1B\uFF09)\u300D]*/g,
  /\s*[·\uFF5C|]?\s*[(\uFF08][^()\uFF08\uFF09]*\bpm_\d+[^()\uFF08\uFF09]*[)\uFF09]/g,
  /\s*[·\uFF5C|]\s*[(\uFF08]?\s*L\d{2}\s*[)\uFF09]?/g,
  /\s*[(\uFF08][^()\uFF08\uFF09]*\bL\d{2}\b[^()\uFF08\uFF09]*[)\uFF09]/g,
  /\s*[·\uFF5C|]\s*承\s*L\d{2}[^\uFF0C\u3002\uFF1B\uFF09)\u300D]*/g
];
function paEngStrip(s){
  let t = String(s == null ? '' : s);
  for(let i=0;i<PA_ENG_SEG.length;i++) t = t.replace(PA_ENG_SEG[i], '');
  return t.replace(/[ \t]{2,}/g, ' ').replace(/[ \t]+([\uFF09)\uFF0C\u3002\uFF1B\u3001])/g, '$1').trim();
}
function paEngCleanDrawer(){
  const root = document.getElementById('paMorePanel'); if(!root) return null;
  const hits = [];
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
  let node;
  while((node = walker.nextNode())){
    const t = node.nodeValue || '';
    if(!paEngHit(t)) continue;
    const pe = node.parentElement;
    if(pe && pe.closest && pe.closest('details[data-engskip]')) continue;
    if(pe && pe.closest && pe.closest('details.eng')) continue;
    hits.push({node:node, before:t, after:paEngStrip(t)});
  }
  for(let i=0;i<hits.length;i++){
    const h = hits[i];
    h.node.nodeValue = (h.after && !paEngHit(h.after)) ? h.after : '';
  }
  if(hits.length){
    const d = document.createElement('details');
    d.className = 'msub';
    d.setAttribute('data-engskip', '1');
    d.innerHTML = '<summary>来源 ／ 详情（抽屉之过程注记 · 原文照录）</summary><div class="t">'
      + paSelfEsc(hits.map(function(h){ return h.before.trim(); }).filter(function(x){ return !!x; }).join('\n')) + '</div>';
    (document.getElementById('paMoreBody') || root).appendChild(d);
  }
  return hits.length;
}
/* ⭐ pm_1074 §二.ⓜⓝ（承 §一 之更正：真病 ＝ **渲染漏** · ⛔ 判读漏）：
   `session.js:131` 之 `*〔非*〕*` 规则 ⇒ `<em>` 会**吃掉算式之乘号**（现场：`200 * 1.1 * 0.9 = 210.6`
   ⇒ 屏上 `200  1.1  0.9 = 210.6` ⇒ 算子不见）；`PA_UNC_TAIL` 之自示例同病。
   同族先例：本件 `:542–543` 之 `disp` 已转 `×` ⁄ `÷`（唯未罩此二处）⇒ 照其形**收口**（⛔ 新立机制）。
   ⚠ 判据（承 pm_1078 §三：**换判据** · ⛔ 一刀切 · ⛔ 扩到字母之全量）—— 二支**并**：
     **甲（宽松 · 既有）**：识别式吹入两侧之空格 ⁄ `\t`（⛔ 换行）⇒ 以**最近之非空白邻字**判 —— **左**为数值 ⁄ `)` ∧ **右**为数值 ⁄ `(` ⇒ 转 `×`（且空格**随之被吞**，故空格形与改前同形）。
     **乙（紧凑 · 新增）**：`*` 之**两侧皆无空白** ∧ **至少一侧**为数值（`0-9`）⁄ 括号 ⇒ 转 `×`。
     ⇒ 故：`200 * 1.1 * 0.9` ／ `200*1.1*0.9` ／ `(1+2)*(3+4)`（甲）／ `2*x`（乙 · 左值）／ `x*2`（乙 · 右值）⇒ **皆转**；
       `*强调*` ⁄ `**粗**`（两侧皆非数值）／ `2 * x`（有空白 ⇒ 乙 ⛔ 中 · 甲亦 ⛔ 中）／ `x*y`（两侧皆字母）⇒ **⛔ 转** ⇒ 仍按 MD 渲。
     ⚠ 照实之界（承 §三 之表 · ⛔ 自决）：`2 * x` ／ `x*y` ⇒ **⛔ 转**（存异备案 · 低优 · 罕见）。
     ⚠ 照实之界（我一手补 · ⛔ 自决）：`3*重要*` 型（`*` 紧邻数值 ∧ 其右为汉字）⇒ 乙**命中**（左值）⇒ 会转；属所令判据之果（罕见）⇒ 照报，若你判须收 ⇒ 另立格。
   ⚠ 只改**显示**：本函数唯造 html ⇒ 存底（`th.msgs` ⁄ `localStorage` ⁄ `details.eng` 之原文）**一字不动**（承 pm_1071 之同族）。
   ⚠ 网关：弃**后视**（`lookbehind` 于旧引擎不可用 ⇒ 旧版曾致「静默不改」）⇒ 改**逐字符**判（`charAt` ＋ `replace` 之回调）
     ⇒ ⛔ 依赖引擎之新旧（承 `L123`：弃判须配退路）｜异常 ⇒ **静默不改**（⛔ 引全件解析失败）。 */
const PA_MUL_STAR = /[ \t]*\*[ \t]*/g;
function paSelfMulSafe(s){
  const t = String(s == null ? '' : s);
  if(t.indexOf('*') < 0) return t;
  try{
    return t.replace(PA_MUL_STAR, function(m, off, whole){
      const A = off > 0 ? whole.charAt(off - 1) : '';
      const B = off + m.length < whole.length ? whole.charAt(off + m.length) : '';
      const isNum = function(c){ return (c >= '0' && c <= '9') || (c >= '０' && c <= '９'); };
      const isPar = function(c){ return c === ')' || c === '）' || c === '(' || c === '（'; };
      if((isNum(A) || A === ')' || A === '）') && (isNum(B) || B === '(' || B === '（')) return ' × ';
      if(m === '*' && (isNum(A) || isPar(A) || isNum(B) || isPar(B))) return ' × ';
      return m;
    });
  }catch(e){ return t; }
}
try{ window.paSelfMulSafe = paSelfMulSafe; }catch(e){}
function paSelfSayHtml(user, eng){
  const u = paSelfMulSafe(String(user == null ? '' : user));
  let h = '';
  try{ h = (typeof paMdToHtml === 'function') ? paMdToHtml(u) : paSelfEsc(u); }
  catch(e){ h = paSelfEsc(u); }
  return h + paEngHtml(eng);
}

/* ================= 二之后 · 判之器（承 pm_1002 §三 补② ＋ pm_1003 ＋ pm_1012）=================
   ⭐ 误判可退（补②）：句首「检索：」／「@ask」⇒ 强制走正常 /v9/pa/ask（⛔ 硬吞）。
   ⚠ 前缀须带冒号（或 @ask ／ @检索 自带）⇒ ⛔ 误伤普通句（例「检索一下知识库」不算强制）。 */
const PA_SELF_FORCE = /^\s*(?:@\s*(?:ask|检索)\s*[:：]?\s*|(?:强制)?检索\s*[:：]\s*)/i;
function paSelfForce(text){
  const s = String(text == null ? '' : text);
  const m = s.match(PA_SELF_FORCE);
  if(!m) return null;
  const rest = s.slice(m[0].length).trim();
  if(!rest) return null;
  return {pre:m[0].trim(), rest:rest};
}
/* ⭐ pm_1067 §四：元问（指代 ／ 重复 ／ 上文）之**放行判** —— 词表与后端同形
   （`core/pa/gateway_routes.py` 之 `PA_ASK_META_KW` · 承 L123）；限长同后端（≤ 40）。
   ⚠ 本判**只管「⛔ 吞」**（前端自述层须放行）⇒ ⛔ 判其域（路由之轴归后端 · 承 L83）。 */
const PA_ASK_META_KW = ['上一条', '上一句', '上一问', '前一句', '刚才', '原样重复', '重复一遍', '再说一遍', '我问的是什么', '我问了什么', '第几问', '你说过'];
function paSelfIsMeta(text){
  const s = String(text == null ? '' : text).trim();
  if(!s || s.length > 40) return false;
  for(let i = 0; i < PA_ASK_META_KW.length; i++){ if(s.indexOf(PA_ASK_META_KW[i]) >= 0) return true; }
  return false;
}
try{ window.paSelfIsMeta = paSelfIsMeta; }catch(e){}
/* ⭐ 本机自有物（承 pm_1003 §三 · 治「PA 说不了自己」之根）：问「本机自有之物」之句，
   ⛔ 须自带「你 ／ 自我 ／ PA」（例「有哪些插件」「可调用的 agent 有哪些」）⇒ 仍归自述类。
   ⚠ 此表为**本机自有物之闭集**（键 ≡ 我方来源面），⛔ 「靠给说法加词」；余者归后端判层（另立件候批）。 */
const PA_SELF_OWN = /插件|面册|有哪些面|agent|智能体|子代理|子任务|席位|工具/;
function paSelfOwnAsk(s){
  if(!PA_SELF_OWN.test(s)) return false;
  return /[?？]\s*$/.test(s) || /(有哪些|有什么|有几个|有几条|有多少|是什么|多少|吗|呢)/.test(s);
}
/* ⭐ 命中规则（补② ⒜）：一段可核 —— 键 ／ 说明 ／ 正则（键序 ≡ PA_SELF_PAT） */
function paSelfRuleTable(){
  const D = {who:'身份自述', can:'能力清单', tools:'工具清单', plug:'插件与面', seat:'可调用的 agent',
             cmp:'对照与差距', env:'环境感知与障碍', read:'环境读数', perm:'权限与边界'};
  return PA_SELF_PAT.map(function(p){ return {k:p[0], re:String(p[1]), d:D[p[0]] || ''}; });
}
/* 规则表面板（入「关于 PA」之折叠处 · ⛔ 默认态用户面） */
function paSelfRuleHtml(){
  const t = paSelfRuleTable();
  return '<details class="msub" data-engskip="1"><summary>判定规则（本机自述规则表 · 一段可核）</summary>'
    + '<div class="t">' + paSelfEsc(t.map(function(r){ return r.k + ' ｜ ' + r.d + ' ｜ ' + r.re; }).join('\n')) + '</div>'
    + '<div class="t">误判可退：句首加「检索：」或「@ask」再发 ⇒ 强制走知识检索（⛔ 硬吞）'
    + '｜本件为回答层件（⛔ 面体 · ⛔ 入册）｜后端判层路由 ⇒ 另立件候批</div></details>';
}
/* ⭐ 多键之判（同一问可命中多节 ⇒ 逐节拼答 · ⛔ 只取首中） */
function paSelfKeys(text){
  const s = String(text == null ? '' : text).trim();
  if(!s || s.length > 120) return [];
  /* 自指之判：须为「对 PA 说」——含你 ／ 自我 ／ PA，或本身即自述短语（权限边界 ／ 环境感知 ／ 自我介绍 …）。
     ⛔ 反例：普通任务句（「帮我看看这个文件的权限」／「把这个文件重命名」）⇒ ⛔ 拦。 */
  if(!/(你|自我|PA|pa|权限(与|和)?边界|权限四层|自我介绍|环境感知|有哪些工具|能做(什么|哪些)|能读什么|能写什么)/.test(s) && !paSelfOwnAsk(s)) return [];
  if(/^(帮我|请帮我|麻烦你?帮|替我|给我|把这|把这个)/.test(s)) return [];
  const out = [];
  for(let i=0;i<PA_SELF_PAT.length;i++){ if(PA_SELF_PAT[i][1].test(s)) out.push(PA_SELF_PAT[i][0]); }
  return out;
}
function paSelfKey(text){ const a = paSelfKeys(text); return a.length ? a[0] : null; }
/* 兜底模式（拒答 ⇒ 属自身域者，逐节拼答） */
const PA_SELF_FB_PAT = [
  ['plug',  /插件|plugin|扩展(能力|包)|面册/],
  ['seat',  /agent|智能体|子代理|子任务|席位|可调用/],
  ['cmp',   /对比|对照|差距|muse|dots|竞品/],
  ['tools', /工具/],
  ['perm',  /权限|授权|边界|能读|能写|外发|凭据/],
  ['read',  /显存|读数|状态|资源/],
  ['env',   /环境|感知|障碍|局限|记忆|上下文|画像/],
  ['which', /是谁|自我介绍|身份|叫什么/],
  ['can',   /能做什么|能做哪些|功能|能力/]
];
function paSelfFbKeys(q){
  const s = String(q == null ? '' : q).trim();
  const keys = [];
  for(let i=0;i<PA_SELF_FB_PAT.length;i++){
    const k = PA_SELF_FB_PAT[i][0];
    if(!PA_SELF_FB_PAT[i][1].test(s)) continue;
    if(k === 'which'){ if(keys.indexOf('who') < 0) keys.push('who'); continue; }
    if(keys.indexOf(k) < 0) keys.push(k);
  }
  return keys;
}
function paSelfRefusal(s){
  const t = String(s == null ? '' : s).trim();
  /* ⭐ pm_1073 §二.1（承 L123「两端表须同形」／ L83 单源）：辨「拒答」之词形须与后端**同一形** ——
     后端 `PA_SYSTEM`（core/pa/gateway_routes.py:47）明令「无命中时**只许**说『查不到』」，
     且 `PA_ASK_REFUSAL`（:208）＝「查不到（知识库里没有相关内容）」⇒ 故其形 ＝ **以「查不到」起首**。
     ⚠ 原式 `/^\s*查不到[：:]/` 只认「查不到：」⇒ **漏**「查不到。」（对话脑之实返 · 我一手见 N2 ／ X1）
       ⇒ 本令补「起首」一格（⛔ 新词表 ／ ⛔ 泛指三字 —— 唯**起首**者算，免误伤句中引用）。 */
  return t.indexOf('查不到') === 0
      || /知识库里没有相关内容/.test(t) || /库里无依据/.test(t);
}
/* ⭐ pm 21:20 §二（承 pm 20:56 §三.1 ／ §三.3）：**回落支之呈现闸**。
   判据（**结构性**）＝「闸已拒 ∧ 无本机据」—— ⛔ 以词形为唯一之闸（词形仅**旁证**）。
   形：本机**是非问**（对「事实 ／ 状态 ／ 账 ／ 决策」之族）⇒ 模型之断言 ⛔ 上答话 ／ 改书 canonical 拒答；
      ∨ 模型之辞含「已完成 ／ 查不到」族 ⇒ 亦拦（旁证 · ⛔ 单凭 · 承「以形判必漏」）。 */
const PA_FACT_MARK = /台账|账|决策|任务|作业|交付|回执|发布|项目|方案|文件|数据|记录|会话|席位|模型|接口|脚本|本机|我方|信通|T\d/;
const PA_STATE_ASK = /(完成|做完|做好|办好|办完|收口|交付|发布|落行|落盘|存在|是不是|有没有|是否|在不在|对不对|了没|成没成|好没好)/;
const PA_DENY_WORD = /(已完成|已办完|已收口|已交付|搞定了|已经好了|查不到|没查到|没有查到)/;
const PA_YN_MARK = /是不是|是否|有没有|能不能|在不在|对不对|了没|了吗|成没成|好没好|行不行|有无/;
function paSelfFactYN(s){
  const t = String(s == null ? '' : s).trim();
  if(!t) return false;
  if(!PA_FACT_MARK.test(t)) return false;                 /* 须涉「事实／状态／账／决策」之族 */
  if(!PA_STATE_ASK.test(t)) return false;                 /* 须为是非／状态之形（⛔「方案怎么改？」之商量形） */
  if(/[？?]\s*$/.test(t)) return true;                    /* 问句形 ⇒ 是非／状态之问 */
  return PA_YN_MARK.test(t);                              /* ⛔ 无问号者须含是非之标记（承 pm 21:20 §三：⛔ 以「非知识问」漏过） */
}
function paSelfModelAssertForbidden(q, a){
  if(paSelfFactYN(q)) return true;                                    /* 判据（结构）：本机事实族之是非问 */
  const _q = String(q == null ? '' : q);
  if(!PA_FACT_MARK.test(_q)) return false;                           /* ⛔ 非本机事实族 ⇒ ⛔ 以词形独断（承「以形判必漏」） */
  return PA_DENY_WORD.test(String(a == null ? '' : a));              /* 旁证（词形）· 仅于本机事实族之问内作旁证 */
}
try{ window.paSelfFactYN = paSelfFactYN; window.paSelfModelAssertForbidden = paSelfModelAssertForbidden; }catch(e){}
function paSelfEvidText(s){
  const m = String(s == null ? '' : s).match(/（判据[^）]*）/);
  return m ? m[0] : '';
}

/* ================= 三 · 拼答（用户面只人话 ＋ 工程注记分面 · ⛔ 泛套话 ／ ⛔ 编能力）=================
   ⭐ 每节回 {u, e}：u ＝ 用户面人话（默认可见）｜e ＝ 工程注记（默认隐藏 · 入「来源 ／ 详情」）。 */
async function paSelfCompose(key, pre){
  const d = pre || await paSelfSrc([key]);
  const U = [], E = [];
  if(key === 'who'){
    const ctx = d.ctx, brief = (ctx && typeof ctx.brief === 'string') ? ctx.brief : null;
    const nL = brief ? brief.split('\n').filter(function(x){ return x.trim(); }).length : null;
    const nS = brief ? (brief.match(/^\u3010/gm) || []).length : null;
    U.push('ClawsJoy PA —— 你的私人 PA（本机单例 · 只有你一位主人）');
    U.push('· 我能：陪伴 ／ 商量 ／ 积累 ／ 分派 ／ 代理审核（⛔ 知识库问答机器人）。');
    U.push('· 形态：三栏工作台 · 主面三格（今日上下文 ／ 会话 ／ 任务）。');
    U.push('· 画像：' + (brief ? (nL + ' 行 · ' + nS + ' 节') : '未知（后端未应答）')
      + ' —— 由本机全上下文（跨会话 · 跨席位 ／ 文件 ／ 台账 ／ 平台 ／ 作业 ／ 出图 ／ 记忆自身）摘要而成，⛔ 只从聊天里收集。');
    U.push('· 身份说明是本机固定口径；画像为实时读数。');
    U.push('源：本机画像 GET /v9/pa/context');
    E.push('判据：身份自述 ＝ 口径 · 前端常量（后端无此读数 ⇒ ⛔ 冒充真读数 · 承 pm_1000 §二）；画像 ＝ 真源读数。');
  }
  if(key === 'can'){
    const f = paSelfFaces(d.faces);
    if(!f){
      U.push('面册读数暂时取不到（本机面册未应答）⇒ 这一项先按「未知」记。');
      U.push('源：GET /web/pa/faces.json（未应答 · ⛔ 未知）');
      E.push('面册读不到 ⇒ ⛔ 编（承 L76）。');
      return {u:U.join('\n'), e:E.join('\n')};
    }
    U.push('我能做什么（本机面册 · 实时读数）');
    U.push('· 共 ' + f.total + ' 面 —— 开放 ' + f.open.length + ' · 私面 ' + f.priv.length);
    U.push('· 开放面（' + f.open.length + '）：' + f.open.map(function(x){ return x.title || x.id; }).join(' ／ '));
    U.push('· 主面环：今日上下文 ／ 会话 ／ 任务（含派活栏）');
    U.push('· 私面（' + f.priv.length + ' · 仅在浏览器内校验）：' + f.priv.map(function(x){ return (x.title || x.id) + '(' + x.id + ')'; }).join(' ／ '));
    U.push('· 判 ／ 编 ／ 派：产物卡带判据（判了什么 ／ 依据哪件 ／ 置信 ／ 是否降级）｜目标条 ＋ 阶段条（可断点 ／ 回滚 ／ 交人）｜派活栏（席位 ／ 对端 ／ 在办 ／ 待验收 ／ 凭据）。');
    U.push('源：GET /web/pa/faces.json（每面开放旗 · 一处开关关全体私面）');
    E.push('私面为客户端闸（非 JS 取件仍见骨架）⇒ ⛔ 入开源仓（承 pm_995 §四）。\n私面 id：' + f.priv.map(function(x){ return x.id; }).join(' ／ '));
  }
  if(key === 'tools'){
    const fl = paSelfFlow(d.flow);
    if(!fl){
      U.push('工具流水暂时取不到（本机工具流水未应答）⇒ 这一项先按「未知」记。');
      U.push('源：GET /v9/metrics/tool_flow（未应答 · ⛔ 未知）');
      E.push('工具流水读不到 ⇒ ⛔ 编（承 L76）。');
      return {u:U.join('\n'), e:E.join('\n')};
    }
    const top = fl.tools.slice(0, 5);
    U.push('我有哪些工具（本机工具流水 · 近 ' + fl.hours + ' 小时）');
    U.push('· 合计 ' + fl.total + ' 次调用 · 工具 ' + fl.tools.length + ' 种 · 任务名 ' + fl.nTask + ' 条');
    U.push('· 已剔除 ' + fl.probe.length + ' 个自检占位名（' + fl.probeCalls + ' 次调用）—— 它们不是真工具，不计入上面。');
    U.push('· 按次数前 ' + top.length + '：' + top.map(function(t){
      return t.k + ' ' + t.n + ' 次（成率 ' + t.r + '% · 均 ' + t.ms + ' ms）'; }).join('；'));
    U.push('· 全部工具（' + fl.tools.length + '）：' + fl.tools.map(function(t){ return t.k; }).join(' ／ '));
    U.push('· 本机 6 GB 单卡 · 推理并发 1 ⇒ 对话不排队，执行任务排队。');
    U.push('源：GET /v9/metrics/tool_flow（读数时刻 ' + paSelfAt(fl.at) + '）');
    E.push('已剔自检占位名（原表名：' + (fl.probe.join(' ／ ') || '（无）') + ' · 共 ' + fl.probeCalls
      + ' 次）—— ⛔ 以占位名冒充工具（承 pm_1003 §三 · L76）。');
  }
  if(key === 'env'){
    const ctx = d.ctx, brief = (ctx && typeof ctx.brief === 'string') ? ctx.brief : null;
    const nL = brief ? brief.split('\n').filter(function(x){ return x.trim(); }).length : null;
    const nThr = (function(){ const t = d.thr; if(!t) return null;
      return Array.isArray(t) ? t.length : (Array.isArray(t.threads) ? t.threads.length : null); })();
    const nRun = (d.runs && Array.isArray(d.runs.runs)) ? d.runs.runs.length : null;
    const fl = paSelfFlow(d.flow), pm = d.perm, ui = d.ui, sf = paSelfSrcFaces();
    U.push('环境感知与障碍（如实 · ⛔ 泛泛一句）');
    U.push('已接（能读到）：');
    U.push('· 会话面 ' + (nThr === null ? PA_GAP.down('无读数') : nThr + ' 条') + ' · 作业面 ' + (nRun === null ? PA_GAP.down('无读数') : nRun + ' 件') + ' · 记忆自身 ' + (nL === null ? PA_GAP.down() : nL + ' 行'));
    U.push('· 界面快照：采样刻 ' + (ui && ui['刻'] ? ui['刻'] : '未知') + '（约每小时一轮）');
    U.push('· 权限档 ' + (pm && pm.level ? pm.level : '未知') + ' · 工具流水 ' + (fl ? (fl.nTask + ' 任务 ／ ' + fl.tools.length + ' 工具') : PA_GAP.down()));
    U.push('未接 ' + paSelfCount(sf) + '：');
    U.push('· 画像素材面（左栏「来源面」· ⛔ 检索面）' + PA_GAP.todo() + '：' + (sf.miss.length ? sf.miss.join(' ／ ') : '（无）'));
    U.push('· ⭐ ⒝ ⛔ 不接（红线）：' + (sf.off.length ? sf.off.join(' ／ ') : '（无）'));
    U.push('· ⚠ 不可达（后端此刻不在）：' + (sf.unreach.length ? sf.unreach.join(' ／ ') : '（无）'));
    U.push('· 操作：改令：准接 · POST /v9/pa/steer｜接管：待立项 · 须先定义｜真实平台面 ⛔ 不接（红线）｜夜间整合：无后端面');
    U.push('障碍：');
    U.push('· 检索面（逐面件数 · 源 /v9/pa/ask 之 scope ／ faces ／ searched · ⛔ 画像素材面）：'
      + (paSelfFaceText(paSelfAskStat.lastScope, paSelfAskStat.lastFaces) || '本页尚未检索')
      + (paSelfAskStat.lastSearched == null
          ? ' ｜ 共搜：本页尚未检索 ⇒ ⛔ 本面板不硬编目录名。'
          : (' ｜ 共搜 ' + paSelfAskStat.lastSearched + ' 件（刻 ' + (paSelfAskStat.lastFacesAt || '刻未记')
             + '）⇒ ⛔ 本面板不硬编目录名。')));
    { /* ⭐ pm_1040 §四 ／ pm_1041 §三：面之定义（收什么 · 一行）＋ 面之状态（缺根 ／ 跳件） */
      const dt = paSelfFaceDefText(paSelfAskStat.lastScope, paSelfAskStat.lastKbRoot);
      if(dt) U.push('· 面之定义（收什么）：' + dt);
      const ft = paSelfFaceFlagText(paSelfAskStat.lastFaces, paSelfAskStat.lastFacesMissing, paSelfAskStat.lastFacesSkipped);
      if(ft) U.push('· ' + ft);
      const dn = paSelfFaceDefNote(paSelfAskStat.lastScope, paSelfAskStat.lastKbRoot, paSelfAskStat.lastFaces,
                                   paSelfAskStat.lastFacesMissing, paSelfAskStat.lastFacesSkipped);
      if(dn) E.push(dn);
      const fn = paSelfFaceFlagNote(paSelfAskStat.lastFaces, paSelfAskStat.lastFacesMissing, paSelfAskStat.lastFacesSkipped);
      if(fn) E.push(fn);
    }
    U.push('· 显存 6 GB · 单卡 · 推理并发 1 ⇒ 对话不排队，执行任务排队。');
    U.push('· 界面快照非实时（最多陈旧约 1 小时）。');
    U.push('· 私面只在浏览器内校验（不代表数据已隔离）。');
    U.push('源：上列各径（逐条）｜已接 ／ 未接面与左栏「来源面」（＝画像素材面）同源 · 检索面另列于「检索面」行');
    E.push('未接清单源：#paSrcList（与左栏「来源面」同源）｜接线余项 M1（记债 · 承 pm_997 §四）。');
    E.push('⭐ 检索范围之数字回指（承 pm_1039 §三 · ⛔ 硬编）：字段 scope ／ faces ／ searched ⇒ '
      + (paSelfFaceText(paSelfAskStat.lastScope, paSelfAskStat.lastFaces) || '本页尚未检索')
      + (paSelfAskStat.lastSearched == null
          ? ' ｜ 共搜：本页尚未检索 ｜ 读：本页尚未检索 ｜ 刻：本页尚未检索'
          : (' ｜ 共搜 ' + paSelfAskStat.lastSearched + ' ｜ 读 ' + (paSelfAskStat.lastFacesRead || '刻未记')
             + ' ｜ 刻 ' + (paSelfAskStat.lastFacesAt || '刻未记')))
      + '（真源 ＝ POST /v9/pa/ask 之响应 · ⛔ 前端写死目录名）');
  }
  if(key === 'read'){
    const ui = d.ui;
    if(!ui){
      U.push('环境读数暂时取不到（界面快照读不到）⇒ 这一项先按「未知」记，⛔ 不猜。');
      U.push('源：web/pa/ui_state.json（只读快照 · 未应答）');
      E.push('快照读不到 ⇒ 明说「未知」· ⛔ 编（承 L76）。');
      return {u:U.join('\n'), e:E.join('\n')};
    }
    const vr = ui['显存'] || {};
    const fv = Array.isArray(ui.Forever) ? (ui.Forever.length ? ui.Forever.join(' ／ ') : '无') : '未知';
    const nz = function(v){ return (v === undefined || v === null) ? '未知' : String(v); };
    U.push('环境读数（只读快照）');
    U.push('· 已载 ' + nz(ui['已载']) + ' · 显存 ' + nz(vr.free) + '/' + nz(vr.total) + ' MB · 被永久留存的模型 ' + fv
      + ' · 本地在 ' + paSelfYN(ui['本地在']) + ' · 远端 ' + paRemText(ui)
      + (ui['远端host'] ? '（' + ui['远端host'] + '）' : ''));
    U.push('· 远端因 ' + paRemWhy(ui) + '（源：快照「远端因」· ⛔ 前端编 · pm_1045 §三）');
    U.push('· 采样刻 ' + nz(ui['刻']) + '（约每小时一轮）');
    const gw = paSelfGpuWarn(ui);
    if(gw) U.push('· ' + gw);
    U.push('源：web/pa/ui_state.json（只读快照 · 非实时）');
    E.push(paSelfGpuEng(ui));
    E.push('快照由技总器 --落 写 · ⛔ 前端自算 ／ ⛔ 直读 nvidia-smi（承 pm_990 §三）。');
  }
  if(key === 'perm'){
    const sf = paSelfSrcFaces();
    U.push('权限与边界（五层 · 如实）');
    paSelfPermRows().forEach(function(r){ U.push(r.n + ' ' + r.k + '：' + r.v); });
    U.push('已接 ' + sf.read.length + ' 面 ／ 未接 ' + sf.miss.length + ' 面 ／ ⛔ 不接（红线）' + sf.off.length + ' 面（＝画像素材面 · 与左栏「来源面」同源 · ⛔ 检索面）：');
    U.push('· 已接：' + (sf.read.length ? sf.read.join(' ／ ') : '（无）'));
    U.push('· ' + PA_GAP.todo() + '：' + (sf.miss.length ? sf.miss.join(' ／ ') : '（无）'));
    U.push('· ⭐ ⒝ ⛔ 不接（红线）：' + (sf.off.length ? sf.off.join(' ／ ') : '（无）'));
    U.push('· ⚠ 不可达：' + (sf.unreach.length ? sf.unreach.join(' ／ ') : '（无）'));
    U.push('· 检索面（源 POST /v9/pa/ask 之 scope ／ faces · ⛔ 画像素材面）：' + paSelfAskFaceBody());
    U.push('· 面之差：「文件」在来源面（＝画像素材面）标未接；但工作区文件面另有来源'
      + '（更多 ▾ · ① 做 · 文件 ⇒ 真数据 25 项）⇒ 二者面不同 · ⛔ 混为一谈。');
    U.push('· 私面（admin ／ registry_dashboard ／ web_summary）只在浏览器内校验。');
    U.push('⛔ 不读 .credentials.yaml ／ Cookies ／ token 的值（只报已配 ／ 未配）｜⛔ 不外发（默认关）。');
    U.push('源：权限档 GET /v9/pa/permission ｜ 前面四层为本机固定口径');
    const gwp = paSelfGpuWarn(d.ui);
    if(gwp) U.push('· ' + gwp);
    E.push('①–④ 为「口径 · 前端常量」（后端无此读数 ⇒ ⛔ 冒充）· 承 L81 ／ L74｜面清单 GET /web/pa/faces.json'
      + '｜私面闸 ＝ 客户端闸（承 pm_995 §四）。' + (gwp ? ('\n' + paSelfGpuEng(d.ui)) : ''));
  }
  if(key === 'plug'){
    const f = paSelfFaces(d.faces);
    U.push('插件与面（本机面册 · 实时读数）');
    if(!f){
      U.push('面册读数暂时取不到（本机面册未应答）⇒ 这一项先按「未知」记。');
      U.push('源：GET /web/pa/faces.json（未应答 · ⛔ 未知）');
      E.push('面册读不到 ⇒ ⛔ 编（承 L76）。');
      return {u:U.join('\n'), e:E.join('\n')};
    }
    U.push('· 本机共 ' + f.total + ' 面 —— 开放 ' + f.open.length + ' · 私面 ' + f.priv.length);
    U.push('· 开放面（' + f.open.length + '）：' + f.open.map(function(x){ return x.title || x.id; }).join(' ／ '));
    U.push('· 本机没有引用任何上游界面包（静态页：外部脚本 ／ 请求 ／ 图片来源皆 0）。');
    U.push('· 本机另有一份只读的界面组件目录（41 个 · 未打包进来 · ⛔ 入仓）。');
    U.push('源：GET /web/pa/faces.json（面册读数）');
    E.push('界面引用三档（口径 · 前端常量 · 承 pm_973 §五）：档 A 直引其形（照引 ／ 自写）｜档 B 引接口 ＋ 自写｜档 C ⛔ 引（品牌 ／ 遥测 ／ 云默认）；上游包数 41 为「口径 · 前端常量」（⛔ 前端真源）。');
  }
  if(key === 'seat'){
    const st = d.sub, ro = d.roster, se = d.seats, ev = d.env;
    /* ⭐ pm_刀13p §二 ＋ 刀8p §〇：**旧句已过期** —— 组织席位册之真源已落（GET /v9/pa/seats · TD 刀8 §一）
       ＋ 实时驻留态在 GET /v9/pa/env 之 cols.agents（kind=seat）⇒ ⛔ 再书「⛔ 无 HTTP 真源」。 */
    const seatCols = (ev && ev.cols && Array.isArray(ev.cols.agents))
      ? ev.cols.agents.filter(function(x){ return x && x.kind === 'seat'; }) : null;
    let seatLive = ev ? PA_GAP.todo('后端无此键 cols.agents（GET /v9/pa/env）') : PA_GAP.down('GET /v9/pa/env 未应答');
    if(seatCols){
      const byState = {};
      seatCols.forEach(function(x){ const k = String((x && x.state) || '未知'); byState[k] = (byState[k] || 0) + 1; });
      seatLive = seatCols.length + ' 席 · 驻留态 ' + Object.keys(byState).sort().map(function(k){ return k + ' ' + byState[k]; }).join(' ／ ');
    }
    const seatNames = (se && Array.isArray(se.rows))
      ? se.rows.slice(0, 20).map(function(x){ return String((x && x.name) || (x && x.id) || '?'); }).join(' ／ ') : '—';
    const nSub = (st && Array.isArray(st.subtasks)) ? st.subtasks.length : null;
    U.push('可调用的 agent（席位 ／ 子代理）');
    U.push('· 子代理面：' + (nSub === null ? PA_GAP.down('无读数') : (nSub + ' 件')) + '（实时读数）');
    U.push('· 组织席位册：' + (se && se.count != null ? (se.count + ' 席') : '未知（后端未应答）')
      + '（源 GET /v9/pa/seats · 面名「' + String((se && se.面名) || '组织席位册') + '」）· 实时驻留：' + seatLive
      + '｜名册：' + seatNames);
    U.push('· 编队花名册（可调用之外脑 ／ 工人）：' + (ro && ro.count != null ? (ro.count + ' 卡（' + ((ro.by_level && Object.keys(ro.by_level).length) ? Object.keys(ro.by_level).sort().join('／') : '—') + '）· ' + (((ro.rows || []).slice(0,4).map(function(x){ return x.name || x.id; }).join(' · ')) || '—')) : '未知（后端未应答）') + '（实时读数）');
    U.push('· 派活提交：本批未实际调用（会真起子任务 · 须经演示批）。');
    U.push('· 中止：需要真实会话号（现无在办 ⇒ 无对可验）。');
    U.push('源：GET /v9/subtask/status（子代理读数）｜GET /v9/pa/roster（**能力端点册**）｜GET /v9/pa/seats（**组织席位册** · 面名分列）｜GET /v9/pa/env 之 cols.agents（**实时驻留态**）');
    E.push('⭐ **自纠**（承 pm_1024 §二 · 先查真源）：前版云「席位无前端真源」（所查三径 /v9/agents ⇒ 404 ／ /v9/pa/seats ⇒ 404 ／ /v8/roster/list ⇒ 200 空）—— ⚠ **非真源** ⇒ 此读**误**；真源为 GET /v9/pa/roster（编队花名册 · 200 · 见上读数）⇒ **已接**（承 tasks.js）。⚠ **本刻再纠**：上句「组织席位 14 席仍 ⛔ 无 HTTP 真源 ⇒ 明标未接」**已过期** —— TD 刀8 §一 已落 `GET /v9/pa/seats`（面名「组织席位册」· 本刻实测 count=14）＋ `GET /v9/pa/env` 之 `cols.agents`（`kind=seat`）携实时驻留态 ⇒ **本面已改接**（承 pm_刀13p §二：⛔ 两说并存）。派活干跑 · 中止须真 sid（承 pm_998 §二 格③）。');
  }
  if(key === 'cmp'){
    U.push('对照与差距（逐轴「它有 ／ 我有 ／ 差」· 如实）');
    U.push('  ① 常驻执行面：它有常驻执行 ／ 虚拟计算机 ｜ 我有本机执行内核 ＋ 本机工具 ｜ 差：⛔ 虚拟计算机');
    U.push('  ② 跨应用记忆：它有 ｜ 我有本机全上下文 ＋ 单画像（跨会话跨席）｜ 差：⛔ 跨设备');
    U.push('  ③ 夜间整合·晨起通知：它有 ｜ 我有夜间整合 ＋ 晨报 ｜ 差：⛔ 移动端通知');
    U.push('  ④ 主动研究：它有 ｜ 我有 GEO 研究席 ／ 工作流实验室 ｜ 差：⛔ 生态');
    U.push('  ⑤ 授权边界：它有 ｜ 我有权限五层 ＋ 凭据只取布尔 ＋ 外发默认关 ｜ 这一项我更强');
    U.push('· 我独有的：结果可回指来源 ／ 跨会话跨席单一画像 ／ 派活组织层（席位 ／ 回执 ／ 验收 ／ 凭据）／ 本机单机位');
    U.push('· 差距照实（还没做）：虚拟计算机 · 移动端 · 生态（⛔ 只讲优势）');
    U.push('源：本机对照件（固定口径 · ⛔ 实时读数）');
    E.push('对照件为「口径 · 前端常量」· 承 pm_1003 §三｜⛔ 前端真源 ⇒ 待后端判层路由（另立件候批）｜权限五层承 L81。');
  }
  return {u:U.join('\n'), e:E.join('\n')};
}
function paSelfCount(sf){
  if(!sf) return '（清单未载入）';
  return '（已接 ' + sf.read.length + ' · ⒜ 未接 · 待办（M1） ' + sf.miss.length
    + ' · ⛔ 不接（红线）' + sf.off.length + ' · 不可达 ' + sf.unreach.length + '）';
}
async function paSelfSections(keys){
  const d = await paSelfSrc(keys);
  const U = [], E = [];
  for(let i=0;i<keys.length;i++){
    try{
      const r = await paSelfCompose(keys[i], d);
      if(r.u) U.push(r.u);
      if(r.e) E.push(r.e);
    }catch(e){
      U.push('读取本机自述数据失败。');
      E.push('读取失败（' + keys[i] + '）：' + String((e && e.message) || e));
    }
  }
  return {u:U.join('\n\n'), e:E.join('\n')};
}
/* ================= 三之后 · 据上屏（承 pm_1005 §二 · L76 · 改 pm_1012 §二）=================
   ⭐ 据 ＝ 检索到的原文 · 答 ＝ 模型生成 ⇒ **分面而标**（⛔ 混同）。用户面只写「据」与来源名；
   阈值 ／ 判据 ／ grounded 之机制词入工程注记。 */
/* ⭐ pm_1039 §三（**检索范围须从后端取** · ⛔ 硬编 ／ ⛔ 写死「两类目录」）：
   真源 ＝ `POST /v9/pa/ask` 之响应三字段 —— `scope`（**面名表**）／ `faces`（**每面件数**）／ `searched`（共搜）。
   ⚠ 其由（承 L76 ／ L102「声明面 ≠ 执行面」）：改前本件与 `status.js` 写死「知识库 ＋ 收件箱」，
     而后端 `scope` 早已为**五面** ⇒ 声明与执行不符。
   ⚠ 界：⛔ 编数 —— 面名表里之面若 `faces` 无其数 ⇒ 该面标「—」（⛔ 猜 ／ ⛔ 只报总数）。 */
/* ⭐ pm_1040 §四：**面之定义**（逐面之「根」＋「收什么」）—— 附于「逐面件数」之后（承「可回指」）。
   ⚠ 本表 ＝ **声明层**（真源 ＝ core\pa\gateway_routes.py 之 PA_FACES ／ PA_FACES_SKIP ／ 每件尺寸闸）。
     根里 `@kb` ⇒ 取**本响应之 `kb_root`**（⛔ 硬编根）；本页未检索 ⇒ 以「知识库根」代（如实 · ⛔ 编）。
   ⚠ ⛔ 撑首屏：用户面**只一行**（`paSelfFaceDefText`）；全细（skip 清单 ／ 尺寸闸 ／ `0` 件之两因）入**注记**。 */
const PA_FACE_DEF = [
  ['收件箱',   '@kb\\收件箱',                        '知识库根之「收件箱」（*.md · 递归）', 'md', '知识库根', '2 MiB'],
  ['知识库',   '@kb\\知识库',                        '知识库根之「知识库」（*.md · 递归）', 'md', '知识库根', '2 MiB'],
  ['文件',     'D:\\paseo-workspace',                '工作区（*.md ／ *.txt · 递归 · 排除内部目录）', 'md／txt', '工作区', '2 MiB'],
  ['台账',     'D:\\paseo-workspace\\_auto\\deliver', '仅一式：老板令台账_v1.md（另二式在该根下⛔存在 ⇒ glob 已收窄）', '老板令台账', '_auto', '16 MiB'],
  ['台账·信通', '@kb\\内容工坊\\02_协作\\信通',        '仅一式：投递台账.csv', '投递台账.csv', '信通', '16 MiB']
];
const PA_FACES_SKIP_TXT = '_auto ／ _tmp ／ _tools ／ _seats ／ _pm ／ _cdp_profile ／ _out ／ node_modules ／ __pycache__ ／ .git 等';
function paSelfFaceCap(nm){
  for(let i=0;i<PA_FACE_DEF.length;i++){ if(PA_FACE_DEF[i][0] === nm) return PA_FACE_DEF[i][5]; }
  return '';
}
function paSelfFaceDefRow(nm, kb, full){
  for(let i=0;i<PA_FACE_DEF.length;i++){
    const d = PA_FACE_DEF[i];
    if(d[0] !== nm) continue;
    /* ⭐ pm_1041 §三 之裁：用户面**一行**（只留「收什么」＋**短式代全径**）；全细（全径）入注记。 */
    if(!full) return nm + '＝' + d[4] + '·' + d[3];
    let root = d[1];
    if(root.indexOf('@kb') === 0){ root = kb ? (kb + root.slice(3)) : ('知识库根' + root.slice(3)); }
    return nm + '＝' + root + '（' + d[2] + '）';
  }
  return nm + '＝（本件未声明 · ⛔ 编一个根）';   /* ⛔ 编（承 L76） */
}
function paSelfFaceDefText(scope, kb){
  const sc = (scope && scope.length) ? scope : [];
  if(!sc.length) return '';
  return sc.map(function(nm){ return paSelfFaceDefRow(nm, kb, false); }).join(' ｜ ');
}
function paSelfFaceDefNote(scope, kb, faces, missing, skipped){
  const sc = (scope && scope.length) ? scope : [];
  if(!sc.length) return '';
  const rows = sc.map(function(nm){
    return paSelfFaceDefRow(nm, kb, true) + '　每件尺寸闸 ' + (paSelfFaceCap(nm) || '2 MiB');
  }).join('\n    ');
  const zeros = sc.filter(function(nm){ return faces && faces[nm] === 0; });
  const miss = (missing && missing.length) ? missing.slice() : [];
  const sk = [];
  try{
    if(skipped && typeof skipped === 'object'){
      Object.keys(skipped).forEach(function(k){ if(skipped[k] > 0) sk.push(k + ' ' + skipped[k]); });
    }
  }catch(e){}
  return '面之定义（声明层 · 真源 ＝ core\\pa\\gateway_routes.py 之 PA_FACES ／ PA_FACES_SKIP ／ PA_FACES_MAX_BYTES）：\n    ' + rows
    + '\n    · 排除目录（按「相对根」判）：' + PA_FACES_SKIP_TXT
    + '\n    · 逐面尺寸闸（照后端）：文件 ／ 收件箱 ／ 知识库 ＝ 2 MiB；台账类 ＝ 16 MiB ⇒ 单件超闸 ⇒ ⛔ 收且 ⛔ 计件'
    + (zeros.length ? ('\n    · 本次为 0 之面：' + zeros.join(' ／ ') + ' ⇒ ⚠ 须以 faces_missing ／ faces_skipped 辨因（⛔ 读作「无料」）') : '')
    + '\n    · ⭐ 真源字段（本响应）：faces_missing ＝ ' + JSON.stringify(miss) + ' ｜ faces_skipped ＝ ' + JSON.stringify(skipped || {})
    + '\n    ⚠ 本表为**声明层**（承 L102 声明面 ≠ 执行面）：后端若于响应加 `face_defs` 字段 ⇒ 我一行可接（⛔ 前端硬编 · 已转产品线）。';
}
/* ⭐ pm_1041 §四：**面之状态**（缺根 ／ 跳件）—— 「0 件」两因之上屏明标（⛔ 只显示 0 件）。 */
function paSelfFaceFlagText(faces, missing, skipped){
  const parts = [];
  const miss = (missing && missing.length) ? missing.slice() : [];
  if(miss.length) parts.push('缺根 ' + miss.length + ' 面（' + miss.join(' ／ ') + ' ⇒ 其「0 件」⛔ 读作「无料」）');
  let n = 0, ks = [];
  try{
    if(skipped && typeof skipped === 'object'){
      Object.keys(skipped).forEach(function(k){ if(skipped[k] > 0){ ks.push(k + ' ' + skipped[k]); n += skipped[k]; } });
    }
  }catch(e){}
  if(n) parts.push('跳件 ' + n + ' 件（' + ks.join(' ／ ') + ' · 超每件尺寸闸 ⇒ ⛔ 计件）');
  if(!parts.length) return '';
  return '⚠ 面之状态（取自本次响应）：' + parts.join(' ｜ ');
}
function paSelfFaceFlagNote(faces, missing, skipped){
  const t = paSelfFaceFlagText(faces, missing, skipped);
  if(!t) return '';
  return '面之状态（真源 ＝ 本响应之 faces_missing ／ faces_skipped · ⛔ 前端自算）：\n    · faces_missing ＝ '
    + JSON.stringify((missing && missing.length) ? missing : [])
    + ' ⇒ 该面之根**不存在** ⇒ 其「0 件」之义 ＝ **无根**（⛔ 「无料」）'
    + '\n    · faces_skipped ＝ ' + JSON.stringify(skipped || {})
    + ' ⇒ 该面有件**因超尺寸闸而未计件**（⛔ 静默 ⇒ 本面板明标）';
}
function paSelfFaceText(scope, faces){
  const sc = (scope && scope.length) ? scope : [];
  const fm = (faces && typeof faces === 'object') ? faces : null;
  const names = sc.length ? sc.slice() : (fm ? Object.keys(fm) : []);
  if(!names.length) return '';
  return names.map(function(nm){
    const v = (fm && fm[nm] != null) ? fm[nm] : '—';
    return nm + ' ' + v + ' 件';
  }).join(' ／ ');
}
/* ⭐ pm_1065 §三 ⒝（面名分列 · ⛔ 抹平）：同屏曾以「📄 文件 未接（M1）」（**画像素材面** · 源 #paSrcList 之静态面册）
   与「文件 93 件」（**检索面** · 源 POST /v9/pa/ask 之 scope ／ faces）并列 ⇒ 读者误读为**同物相冲**。
   二者面不同（同一词「文件」指两物）⇒ 本处以**面之名**标其属（承 L135「同名不同物」之同族）。
   真源：检索面之件数取本回应（⛔ 硬编）；画像素材面之清单取左栏「来源面」（#paSrcList）。 */
function paSelfAskFaceBody(){
  const t = paSelfFaceText(paSelfAskStat.lastScope, paSelfAskStat.lastFaces);
  if(!t) return '本页尚未检索 ⇒ 此处 ⛔ 硬编。';
  return t + '（共搜 ' + (paSelfAskStat.lastSearched == null ? '刻未记' : (paSelfAskStat.lastSearched + ' 件'))
    + ' · 刻 ' + (paSelfAskStat.lastFacesRead || paSelfAskStat.lastFacesAt || '刻未记') + '）';
}
/* 记住最近一次检索之面读数（供「关于 PA ／ 环境与障碍」与读数盒回指 · ⛔ 硬编）。 */
function paSelfFacesRemember(g){
  if(!g) return;
  try{
    if(g.scope && g.scope.length) paSelfAskStat.lastScope = g.scope.slice();
    if(g.faces && typeof g.faces === 'object') paSelfAskStat.lastFaces = g.faces;
    if(g.searched != null) paSelfAskStat.lastSearched = g.searched;
    if(g.kb_root) paSelfAskStat.lastKbRoot = String(g.kb_root);   /* ⭐ pm_1040 §四：根取本响应（⛔ 硬编） */
    if(g.faces_missing && g.faces_missing.length) paSelfAskStat.lastFacesMissing = g.faces_missing.slice();
    else paSelfAskStat.lastFacesMissing = [];
    if(g.faces_skipped && typeof g.faces_skipped === 'object') paSelfAskStat.lastFacesSkipped = g.faces_skipped;
    paSelfAskStat.lastFacesAt = new Date().toLocaleTimeString('zh-CN', {hour12:false});
    paSelfAskStat.lastFacesRead = String(g.read_at || '');
  }catch(e){}
}
/* ⭐ pm_1067 §三（承 pm_1066 §一 · 承 L152）：判据之刻与值 —— 真源 ＝ /v9/pa/ask 之 `judge` 键
   （threshold ／ faces_version ／ faces_count ／ faces_files_total ／ face_snapshot_at ／ judge_at）、
   `archive_hits`（档案面之命中 ⇒ ⛔ 作据 · 承 L154）与 `answer_source`（答源 · **后端九值** —— `decision` ／ `decision_none` ／ `decision_store_unreadable` ／ `context` ／ `context_missing` ／ `not_applicable` ／ `archive_only` ／ `refused` ／ `knowledge` · 逐值之义见 `paSelfAnswerSourceText`；⚠ `archive_only` 支之后端 `answer` 为**拒答原辞** ⇒ 若直上屏即失实（pm 1179 §四 · 待批五 ⒝-1 归一））。
   ⛔ 前端硬编 ／ ⛔ 造值（缺键 ⇒ 照实「未给」）。 */
function paSelfJudgeOf(g){
  const j = (g && typeof g.judge === 'object' && g.judge) ? g.judge : {};
  const s = (g && typeof g === 'object') ? g : {};
  return {
    thr:  (j.threshold != null) ? j.threshold : ((s.threshold != null) ? s.threshold : null),
    ver:  j.faces_version ? String(j.faces_version) : '',
    cnt:  (j.faces_count != null) ? j.faces_count : null,
    tot:  (j.faces_files_total != null) ? j.faces_files_total : null,
    snap: j.face_snapshot_at ? String(j.face_snapshot_at) : '',
    at:   j.judge_at ? String(j.judge_at) : ((s.read_at != null) ? String(s.read_at) : '')
  };
}
function paSelfJudgeText(g){
  const j = paSelfJudgeOf(g);
  let t = '判据 ' + (j.thr == null ? '（本次不适用）' : j.thr) + ' ／ 面册 ' + (j.ver || '版本未给')
    + ' · 采于 ' + ((j.snap || j.at) || '刻未给');
  if(j.cnt != null) t += '（面 ' + j.cnt + ' 枚 · 件 ' + (j.tot == null ? '—' : j.tot) + '）';
  return t + '｜源 /v9/pa/ask 之 judge';
}
function paSelfArchiveText(g){
  const a = (g && Array.isArray(g.archive_hits)) ? g.archive_hits : null;
  if(!a || !a.length) return '';
  return '档案面另有 ' + a.length + ' 条（⛔ 作据 —— 那是我们之报述，⛔ 世界之实）';
}
function paSelfAnswerSourceText(g){
  const s = (g && g.answer_source) ? String(g.answer_source) : '';
  if(!s) return '';
    const M = {knowledge:'本机素材有据 ⇒ 贴据 ＋ 模型作答',
             archive_only:'档中有中（档案面另有）· 而闸判 ⛔ 成据 ⇒ 拒答（⛔ 「无据」之直书 · ⛔ 「知识库无」）',
             context:'按本会话上一句答 · ⛔ 检索面', context_missing:'本会话无可读上一句 ⇒ 如实不答',
             refused:'库里无依据 ⇒ 按「有据才答」不答',
             not_applicable:'不适用（检索面为空 ⇒ 拒答与否皆不成立）',
             decision:'本机决策账有据 ⇒ 逐字照录（⛔ 模型生成）',
             decision_none:'本机决策账无此条 ⇒ 如实不答（⛔ 不编）',
             decision_store_unreadable:'决策账不可读 ⇒ 如实不答（⛔ 不编）'};
  return '答源 ' + s + '（' + (M[s] || '⛔ 未识之值 ⇒ 照实') + '）';
}
/* ⭐ pm 1184 §一.⒞（承 §二 之定名）：**档行源标之渲** —— 使「模型断言」vs「有据之答」在**档 ／ 会话视图**
   一望可辨。真源 ＝ 档行自身之 `origin`（后端加性键 · TD 1056 §五 ／ 词表在 core\pa\dialog.py:39-42）。
   ⚠ **以 `origin` 为准**（pm 1184 §二 · ⛔ 预设 `src`）；行无 `origin`（改名之先所写之旧行）⇒ **不显标**
     （⛔ 以 `src` 冒充 —— 那是「一名二义」之源，且旧 `src` 与响应之走径标同字）。⛔ 未识之值**照实**显。 */
const PA_ORIGIN_TEXT = {model:'模型生成（⛔ 非本机素材）', grounded:'本机有据（账 ／ 素材之直读）',
                        refused:'闸拒（本机无据 ⇒ 不答）', unspecified:'未标（写者未声明 · ⛔ 当作有据）'};
const PA_ORIGIN_COLOR = {model:'#f59e0b', grounded:'#3fb950', refused:'#58a6ff', unspecified:'#8b949e'};
function paSelfOriginBadgeHtml(row){
  const o = (row && typeof row.origin === 'string') ? String(row.origin) : '';
  if(!o) return '';
  const E = function(s){ return String(s == null ? '' : s).replace(/[&<>"]/g, function(ch){ return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[ch]; }); };
  const _own = function(m, k){ return Object.prototype.hasOwnProperty.call(m, k); };
  const c = _own(PA_ORIGIN_COLOR, o) ? PA_ORIGIN_COLOR[o] : '#8b949e';
  const tx = _own(PA_ORIGIN_TEXT, o) ? PA_ORIGIN_TEXT[o] : '⛔ 未识之值 ⇒ 照实';
  const g = (row && typeof row.grounded === 'boolean') ? (row.grounded ? '有据' : '无据') : '未标';
  const as = (row && row.answer_source) ? String(row.answer_source) : '';
  return '<div class="pa-src-line" style="color:' + c + ';font-size:11px;margin:0 0 2px 0">［源 ' + E(o)
    + ' · ' + E(tx) + ' · grounded ' + g + (as ? (' · answer_source ' + E(as)) : '') + '］</div>\n';
}
try{ window.paSelfOriginBadgeHtml = paSelfOriginBadgeHtml; window.PA_ORIGIN_TEXT = PA_ORIGIN_TEXT; }catch(e){}
/* 记住本回之判据 ／ 档案面命中 ／ 答源（供分标之采样刻与「关于 PA」回指 · ⛔ 硬编） */
function paSelfJudgeRemember(g){
  try{
    const j = paSelfJudgeOf(g);
    paSelfTagAt = (j.snap || j.at || '');
    paSelfAskStat.lastJudge = (g && typeof g.judge === 'object' && g.judge) ? g.judge : null;
    paSelfAskStat.lastArchiveHits = (g && Array.isArray(g.archive_hits)) ? g.archive_hits : null;
    paSelfAskStat.lastAnswerSource = (g && g.answer_source) ? String(g.answer_source) : '';
  }catch(e){}
}
/* 「关于 PA」之判据行（回指 · ⛔ 造值） */
function paSelfJudgeLine(){
  if(!paSelfAskStat.lastJudge && !paSelfAskStat.lastAnswerSource){
    return '判据：本页尚未检索（源 /v9/pa/ask 之 judge）';
  }
  const g = {judge:paSelfAskStat.lastJudge, archive_hits:paSelfAskStat.lastArchiveHits || [],
             answer_source:paSelfAskStat.lastAnswerSource || '', read_at:paSelfAskStat.lastFacesRead || ''};
  let t = paSelfJudgeText(g);
  const as = paSelfAnswerSourceText(g); if(as) t += ' ｜ ' + as;
  const ar = paSelfArchiveText(g); if(ar) t += ' ｜ ' + ar;
  return t;
}
function paSelfEvidBlock(g){
  const U = [], E = [];
  const scope = ((g && g.scope) || []).join(' ／ ') || '—';
  const faceT = paSelfFaceText(g && g.scope, g && g.faces);   /* ⭐ pm_1039 §三：逐面件数 */
  if(g && g.n > 0){
    U.push('── 依据（以下是这次检索到的原文）──');
    U.push('📎 据 ' + g.n + ' 条 ｜ 检索范围（逐面件数 · 源 /v9/pa/ask）：' + (faceT || scope) + ' ｜ 共搜 ' + g.searched + ' 件');
    U.push(paSelfJudgeText(g));                                  /* ⭐ pm_1067 §三 ⒜ */
    const _arcU = paSelfArchiveText(g); if(_arcU) U.push(_arcU);  /* ⭐ pm_1067 §三 ⒞ */
    const defT = paSelfFaceDefText(g && g.scope, g && g.kb);   /* ⭐ pm_1040 §四：附「面之定义」一行 */
    if(defT) U.push('面之定义（收什么）：' + defT);
    const flagT = paSelfFaceFlagText(g && g.faces, g && g.miss, g && g.skip);   /* ⭐ pm_1041 §四 */
    if(flagT) U.push(flagT);
    for(let i=0;i<Math.min(g.n,6);i++){
      const e = g.ev[i]; let s = '';
      if(typeof e === 'string') s = e;
      else if(e && typeof e === 'object') s = e.text || e.snippet || e.content || e.title || e.path || JSON.stringify(e);
      U.push(' ' + (i+1) + '. ' + String(s).replace(/\s+/g, ' ').slice(0, 120));
    }
    if(g.n > 6) U.push(' …（余 ' + (g.n - 6) + ' 条）');
    U.push('※ 上面那段话由模型生成；这几条是它依据的原文。');
    E.push('判据：/v9/pa/ask ｜ grounded:true ｜ 阈值 ' + g.thr + ' ｜ 读数 ' + (g.read || '—')
      + ' ｜ evidence 共 ' + g.n + ' 条（此处只列前 6）· ⭐ 答由模型生成 ⇒ ⛔ 与据混同（承 pm_1005 §二）。'
      + '\n⭐ 检索范围之数字回指（承 pm_1039 §三 · ⛔ 硬编）：字段 scope ／ faces ／ searched ⇒ '
      + (faceT || '—') + ' ｜ 共搜 ' + g.searched + ' ｜ 读数 ' + (g.read || '—')
      + '\n' + paSelfFaceDefNote(g && g.scope, g && g.kb, g && g.faces, g && g.miss, g && g.skip)
      + ((paSelfFaceFlagNote(g && g.faces, g && g.miss, g && g.skip)) ? ('\n' + paSelfFaceFlagNote(g && g.faces, g && g.miss, g && g.skip)) : '')
      + '\n' + paSelfJudgeText(g)
      + ((paSelfAnswerSourceText(g)) ? (' ｜ ' + paSelfAnswerSourceText(g)) : '')
      + ((paSelfArchiveText(g)) ? (' ｜ ' + paSelfArchiveText(g)) : ''));   /* ⭐ pm_1067 §三 */
  } else {
    U.push(paSelfJudgeText(g));                                  /* ⭐ pm_1067 §三 ⒜ */
    U.push('📎 这一次没有取到依据（本机检索里没有可用原文）。',
           '※ 若下面还有一段话，那是模型自己说的，不是本机原文。');
    E.push('判据：/v9/pa/ask ｜ grounded:false ｜ 检索范围 ' + scope + ' ｜ 逐面 ' + (faceT || '—') + ' ｜ 实搜 '
      + ((g && g.searched) == null ? '—' : g.searched) + ' 件 ｜ 阈值 ' + ((g && g.thr) == null ? '—' : g.thr)
      + ' ｜ 读数 ' + ((g && g.read) || '—') + '｜⛔ 以模型自述充据（承 pm_1005 §二）。'
      + '\n' + paSelfJudgeText(g)
      + ((paSelfAnswerSourceText(g)) ? (' ｜ ' + paSelfAnswerSourceText(g)) : '')
      + ((paSelfArchiveText(g)) ? (' ｜ ' + paSelfArchiveText(g)) : ''));
  }
  return {u:U.join('\n'), e:E.join('\n')};
}
/* ================= 三之后二 · 拒答之人话分域（承 pm_1012 §三 令②）=================
   ⭐ 三类路由：自述类 ⇒ 本机来源拼答；本机素材类 ⇒ 「本机素材里没查到」＋ 三条下一步；
   域外类 ⇒ 「超出本机素材范围」＋ 下一步。⛔ 再以「未接：该面尚无真源」作通用兜底（该句只属自述类之缺节）。 */
async function paSelfAside(q, cls, g){
  const n = (g && g.searched != null) ? g.searched : null;
  const scope = ((g && g.scope) || []).join(' ／ ') || '—';
  const faceT = paSelfFaceText(g && g.scope, g && g.faces);   /* ⭐ pm_1039 §三：逐面件数 */
  const thr = (g && g.threshold != null) ? g.threshold : '—';
  const read = (g && g.read_at) || '—';
  const eng = '判据：/v9/pa/ask ｜ 问域 ' + cls + ' ｜ 检索范围 ' + scope + ' ｜ 逐面 ' + (faceT || '—') + ' ｜ 实搜 ' + n
    + ' 件 ｜ 阈值 ' + thr + ' ｜ 读数 ' + read + ' ｜ 原拒答 ⛔ 上屏（承 L76 · pm_1012 §三）。';
  if(cls === 'self'){
    const keys = paSelfFbKeys(q);
    if(keys.length){
      const sec = await paSelfSections(keys);
      if(sec.u) return {u:sec.u, e:sec.e + '\n' + eng};
    }
    return {u:'这一项我还没有接入 —— 本机暂时没有可答此问的读数。可：① 换种说法再问 ② 让我联网检索。', e:eng};
  }
  if(cls === 'local'){
    return {u:'本机素材里没查到（共搜 ' + (n == null ? '—' : n) + ' 件：' + (faceT || '—') + '）⇒ 可：① 换种说法再问 ② 联网检索 ③ 我记一笔（待接入）。', e:eng};
  }
  return {u:'这句话超出本机素材的范围 —— 本机没有可用的资料可查。可：① 联网检索 ② 把相关文件给我。', e:eng};
}

/* ================= 四 · 「关于 PA」一屏（同表 · ⛔ 新增主面 · 承 pm_1000 §二.3）=================
   ⚠ 本屏在「更多 ▾ · ③ 设」内（默认收起）⇒ ⛔ 默认态用户面；工程注记仍入折叠处（⛔ 逐字平铺）。 */
const PA_SELF_ORDER = ['who','can','tools','plug','seat','cmp','env','read','perm'];
async function paAboutLoad(force){
  const box = document.getElementById('paAboutBody'); if(!box) return null;
  const when = document.getElementById('paAboutWhen');
  box.innerHTML = '<div class="t">读数中…</div>';
  const d = await paSelfSrc(PA_SELF_ORDER);
  const rows = [];
  for(let i=0;i<PA_SELF_ORDER.length;i++){
    const k = PA_SELF_ORDER[i];
    let c = {u:'', e:''};
    try{ c = await paSelfCompose(k, d); }catch(e){ c = {u:'读取本机自述数据失败。', e:'原始错误：' + String((e && e.message) || e)}; }
    rows.push({k:k, u:c.u, e:c.e});
  }
  box.innerHTML = paSelfRuleHtml() + rows.map(function(r){
    return '<div class="a"><div class="q">' + paSelfEsc(PA_SELF_Q[r.k]) + '</div><div class="t">'
      + paSelfEsc(r.u) + paEngHtml(r.e) + '</div></div>';
  }).join('');
  box.setAttribute('data-loaded', '1');
  if(when) when.textContent = '本屏读数 ' + new Date().toLocaleTimeString('zh-CN', {hour12:false}) + ' · 每条末行即其来源';
  return rows;
}
function paAbout(){
  paMore(true);
  const g = document.getElementById('paMoreGrpSet'); if(g) g.setAttribute('open','');
  try{ paAboutLoad(); }catch(e){}
  setTimeout(function(){
    const s = document.getElementById('paMoreAbout');
    if(s && s.scrollIntoView){ try{ s.scrollIntoView({block:'start'}); }catch(e){} }
  }, 60);
}

/* ================= 五 · 权限（四层）面板（承 pm_1001 §二）================= */
/* ⭐ 权限面之显存警号（承 pm_1006 §三）：N ≥ 1 ⇒ 一句人话；⛔ 自造 —— 现读快照（先取缓存） */
function paPermGpuWarnRender(){
  const el = document.getElementById('paPermGpuWarn'); if(!el) return;
  const put = function(ui){
    const tx = paSelfGpuWarn(ui);
    el.textContent = tx || '';
    el.style.display = tx ? '' : 'none';
    el.style.color = tx ? paSelfGpuWarnColor(ui) : '';
    el.title = (tx && paSelfGpuEng(ui)) || '';
  };
  if(paSelfUiCache){ put(paSelfUiCache); return; }
  paSelfJson('pa/ui_state.json').then(function(u){ if(u) paSelfUiCache = u; put(paSelfUiCache); });
}
function paPermRender(){
  const l = document.getElementById('paPermLayers');
  if(l){
    l.innerHTML = paSelfPermRows().map(function(r){
      return '<div class="r"><span class="n">' + paSelfEsc(r.n) + '</span><span class="k">' + paSelfEsc(r.k)
        + '</span><span class="v">' + paSelfEsc(r.v) + '</span><span class="s">来源：' + paSelfEsc(r.s) + '</span></div>';
    }).join('');
  }
  const f = document.getElementById('paPermFaces'), fs = document.getElementById('paPermFacesSrc');
  const sf = paSelfSrcFaces();
  if(f){
    f.innerHTML = '<div class="ok"><b>画像素材面 · 已读 ' + sf.read.length + ' 面</b>：' + paSelfEsc(sf.read.join(' ／ ') || '（无）') + '</div>'
      + '<div class="na">画像素材面 · ' + PA_GAP.todo() + ' ' + sf.miss.length + ' 面：' + paSelfEsc(sf.miss.join(' ／ ') || '（无）') + '</div>'
      + '<div class="na">⭐ 画像素材面 · ⒝ ⛔ 不接（红线） ' + sf.off.length + ' 面：' + paSelfEsc(sf.off.join(' ／ ') || '（无）') + '</div>'
      + '<div class="na">⚠ 不可达 ' + sf.unreach.length + ' 面：' + paSelfEsc(sf.unreach.join(' ／ ') || '（无）') + '</div>'
      + '<div class="ok"><b>检索面（源 POST /v9/pa/ask · ⛔ 画像素材面）</b>：' + paSelfEsc(paSelfAskFaceBody()) + '</div>'
      + '<div>⚠ 面之差：「文件」在来源面（＝画像素材面）标未接；工作区文件面另有来源 <code>POST /v9/sandbox/list</code>'
      + '（更多 ▾ · ① 做 · 文件 ⇒ 真数据 25 项）⇒ 二者面不同 · ⛔ 混为一谈。</div>'
      + '<div class="na" id="paPermGpuWarn" style="display:none"></div>';
  }
  if(fs) fs.textContent = '来源：#paSrcList（左栏「画像素材面」· ⛔ 检索面）｜检索面另列：POST /v9/pa/ask';
  paPermGpuWarnRender();
  const ex = document.getElementById('paPermExceptBody');
  if(ex){
    ex.innerHTML = '<div>⛔ 不读值之三类：<code>.credentials.yaml</code> ／ <code>Cookies</code> ／ <code>token</code> ⇒ 只报「已配 ／ 未配」。</div>'
      + '<div>⛔ 外发：发布 ／ 上传 ／ 外发默认关（须你显式点头）。</div>'
      + '<div>私面（<code>admin</code> ／ <code>registry_dashboard</code> ／ <code>web_summary</code>）：仅在浏览器内校验 · ⛔ 入开源仓。</div>'
      + '<div>⚠ 这不是服务端隔离：非 JS 取件（curl 等）仍能看到页面骨架。</div>'
      + '<details class="msub" data-engskip="1"><summary>来源 ／ 详情</summary><div class="t">凭据只取布尔承 L74｜私面闸承 pm_995 §四（客户端闸 · 非服务端闸）。</div></details>';
  }
  return sf;
}

/* ================= 六 · 接线上屏（⛔ 动共用面件 send.js ／ status.js ／ products.js）=================
   拦截点＝paSend 之最外层（自述类须在「有据才答」闸之前 ⇒ 否则先被 /v9/pa/ask 拒答为「查不到」）。
   与 tasks.js 之 paSend 包装共存：非自述类 ⇒ 原链一字不动（⛔ 丢功能）。 */
(function(){
  const inner = window.paSend;
  if(typeof inner !== 'function') return;
  const SRC = '本机自述来源';
  window.paSend = async function(){
    const inp = document.getElementById('input');
    const text = inp ? String(inp.value || '').trim() : '';
    paSelfTagAt = '';   /* ⭐ pm_1067 §三 ⒝：采样刻**一轮一清**（⛔ 跨轮串刻 · 承 L76） */
    paSelfRoundPersisted = false;   /* ⭐ pm_1111 §二：落盘闸同为一轮一清（见 §六·六 paSelfLocalRecord） */
    /* ⭐ 误判可退（pm_1002 §三 补②）：句首「检索：」／「@ask」⇒ 强制走正常 /v9/pa/ask（⛔ 硬吞） */
    const fo = paSelfForce(text);
    if(fo){
      if(inp) inp.value = fo.rest;
      try{ addLog('↩ 按你的前缀，本问直接走知识检索（跳过本机自述）', 'ok', true, '强制前缀'); }catch(e){}
      return inner.apply(this, arguments);
    }
    /* ⭐ pm_1067 §四（承 L151 ／ 技总 968 §四 · 承 L83）：元问（指代 ／ 重复 ／ 上文 —— 词表与后端
       PA_ASK_META_KW 同形）须**放行送达后端**（⛔ 判 self ／ ⛔ 本机自述层拼答）⇒ 路由之轴
       （ask_domain：meta ／ retrieve）归后端。⚠ 两轴各管其段：前端 paAskDomain
       （self ／ local ／ world ／ other）管自述 ／ 本机 ／ 世界 ⇒ 本段只做「⛔ 吞」之拦（⛔ 做域判）。 */
    if(paSelfIsMeta(text)){
      try{ addLog('↩ 元问（指代 ／ 重复 ／ 上文）⇒ 放行送达后端（本机自述层 ⛔ 拦）', 'ok', true, '元问放行'); }catch(e){}
      return inner.apply(this, arguments);
    }
    const keys = paSelfKeys(text);
    if(!keys.length){
      /* ⭐ 源之分标（承 pm_1013 §二）：非自述类 ⇒ 问域 `other`（域外 ／ 非知识问）之答走**对话通道**
         （模型生成）⇒ 贴「模型生成（⛔ 非本机素材）」；`local` ／ `world` 由闸定（见 addMsg 之 gateInfo 支）。 */
      let dom0 = null; try{ dom0 = paAskDomain(text); }catch(e){}
      paSelfLbl = (dom0 === 'other') ? paSelfTag('model', null) : null;
      if(dom0 === 'other'){ try{ paSelfAskBump('direct', text, '分类 other ⇒ 直走 /v9/pa/dialog（未过检索闸）'); }catch(e){} }
      try{ return await inner.apply(this, arguments); }
      finally { paSelfLbl = null; }   /* 一轮一清（⛔ 跨轮复用 ⇒ ⛔ 贴错） */
    }
    const busy0 = paSelfBusy();
    addMsg('user', text);
    if(inp) inp.value = '';
    try{ if(typeof autoGrow === 'function') autoGrow(); }catch(e){}
    addLog('✅ 已受理 · 按「本机自述」直接回答（' + keys.map(function(k){ return PA_SELF_Q[k]; }).join(' ＋ ') + '）· 未调用模型 · 未走知识检索'
      + (busy0 ? '（在办任务不受影响）' : ''), 'ok', true, '本机自述（回答层）');
    if(!busy0 && typeof setBusy === 'function'){ try{ setBusy(true); }catch(e){} }
    if(!busy0 && typeof paSetState === 'function'){ try{ paSetState('running', '读取本机自述数据', SRC); }catch(e){} }
    let sec = {u:'', e:''};
    try{ sec = await paSelfSections(keys); }
    catch(e){ sec = {u:'读取本机自述数据失败。', e:'原始错误：' + String((e && e.message) || e)}; }
    const ans = sec.u;
    addMsg('assistant', ans, false, paSelfSayHtml(ans, sec.e), undefined);
    try{
      const t = (typeof activeThread === 'function') ? activeThread() : null;
      /* ⭐ pm 1184 §一.⒝：本机自述之答 ＝ **本机有据**（源 paSelfSrc · ⛔ 模型 ／ ⛔ 拒答）。 */
      if(t && typeof recordPaTurn === 'function'){ paRun.receipt = await recordPaTurn(t.id, text, ans, {origin:'grounded', grounded:true}); }
      const rc = paRun.receipt;
      if(rc && rc.recorded){ addLog('💾 本轮已落盘（后端回执 · 既有出口 POST /v9/pa/turn）', 'ok', true, 'P9 BUG-1'); }
      else { addLog('⚠ 本轮落盘读数不可得 ／ 未落盘：后端无回执 —— ⛔ 不等于已保存', 'warn', true, 'P9 BUG-1'); }
    }catch(e){}
    if(!busy0 && typeof paSetState === 'function'){ try{ paSetState('done', '自述已回答', SRC); }catch(e){} }
    if(!busy0 && typeof setBusy === 'function'){ try{ setBusy(false); }catch(e){} }
    try{ if(typeof saveState === 'function') saveState(); }catch(e){}
    return ans;
  };
})();

/* ================= 六 · 4 · 去重 ／ 合并 （承 pm_1018 §二 ⓝ · 前置包装）=================
   ⭐ 裁：在办时同问 ⇒ **仍受理**（承 A32：受理门永不关 ⇒ ⛔ 灰钮 ／ ⛔ 拒件）；
     但 ⛔ 两件平行 ⇒ 本件**并入**在办之那件，并回执明说（⛔ 静默吞）。
   判据：真鼠标双击 ⇒ 平行件数 ⛔ 增 2 ∧ `#sendBtn.disabled` 仍 false。
   ⚠ 本层为**前置**（拦于一切分流之前）⇒ 自述 ／ 知识 ／ 对话 三路皆受约束。 */
const paSelfInflight = Object.create(null);
let paSelfQn = 0;
let paSelfLastSub = null;
(function(){
  const inner = window.paSend;
  if(typeof inner !== 'function') return;
  window.paSend = async function(){
    const inp = document.getElementById('input');
    const text = inp ? String(inp.value || '').trim() : '';
    /* ⭐ 双击之实况（pm_1018 ⓝ 之判据）：首击发送后，输入框**同步清空** ⇒ 次击所见 text ⽕ ''。
       故：若只按输入框判 ⇒ 合并闸 ⛔ 触发（即「静默吞」）。
       补：空输入 ∧ 近期（≤ 1500 ms）提交之同问仍在办 ⇒ 亦判「已并入」（回执照给）。 */
    let dup = null;
    if(text && paSelfInflight[text]) dup = paSelfInflight[text];
    else if(!text && paSelfLastSub && paSelfInflight[paSelfLastSub.text]
            && (Date.now() - paSelfLastSub.at) <= 1500) dup = paSelfInflight[paSelfLastSub.text];
    if(dup){
      const run = dup;
      const msg = '同一问已有一件在办（' + run.id + '）⇒ 本件已并入，不再另起一件。';
      try{ addMsg('assistant', msg, false, (typeof paSelfSayHtml === 'function')
            ? paSelfSayHtml(msg, '合并回执·同问在办 ' + run.id + '（起于 ' + run.at + '）') : undefined, undefined); }catch(e){}
      try{ if(inp) inp.value = ''; }catch(e){}
      try{ if(typeof autoGrow === 'function') autoGrow(); }catch(e){}
      try{ addLog('🔗 同一问已有一件在办 ⇒ 本次并入（⛔ 不另起一件）', 'ok', true, '去重合并'); }catch(e){}
      return null;
    }
    if(text){ paSelfQn++; paSelfInflight[text] = {id:'#' + paSelfQn, at:new Date().toLocaleTimeString('zh-CN', {hour12:false})};
              paSelfLastSub = {text:text, at:Date.now()}; }
    try{ return await inner.apply(this, arguments); }
    finally{ if(text) delete paSelfInflight[text]; }
  };
})();

/* ================= 六 · 五 · 判据单源（承 pm_1005 §三 ＋ pm_1012 §三 令②）=================
   ⭐ 问域之判**只此一处出口**：paAskDomain(text) ⇒ 'self' ｜ 'local' ｜ 'world' ｜ 'other'
     （'self' ＝ 自述类；'local' ＝ 本机素材类；'world' ＝ 域外类）。
   ⭐ status.js 之 paLooksLikeKnowledgeQuestion **调用 paAskClass**（＝ paAskDomain 之兼容壳 · ⛔ 二处各判）。 */
const PA_ASK_KNOW = /[？?]\s*$|是什么|有哪些|哪一个|哪家|是不是|有没有|能不能|几条|几个|几项|多少|哪个|哪里|哪些|谁|何时|结论|数据|数字|标准|要求|规定|政策|流程|范围|规则|区别|意味着/;
/* ⭐ 本机 ／ 我方之事之词表（前端近似 · 真正解在后端判层 · 记债候批） */
const PA_LOCAL_PAT = /台账|平台|工坊|内容|项目|方案|稿|发布|交付|回执|账|数据|文件|作业|会话|记录|计划|素材|知识库|本机|我方|本台|vault|脚本|接口|模型|出图|席位/;
function paAskDomain(text){
  const s = String(text == null ? '' : text).trim();
  if(!s) return 'other';
  if(paSelfForce(s)) return 'knowledge';           /* 强制前缀 ⇒ 必走知识检索 */
  try{ if(paSelfKeys(s).length) return 'self'; }catch(e){}
  /* ⭐ pm 21:20 §三.⒝（裁：三形皆须禁）：本机「事实／状态／账／决策」之是非问 **必经闸** ——
     ⛔ 以「非知识问」直落模型（那会产出**无标之模型答** · 更险 · 承「弱保证 ≠ 真闸」）。
     判据 ＝ paSelfFactYN（结构 · ⛔ 词形独断）；此处只改**路由之判**（⛔ 改答体）。 */
  if(paSelfFactYN(s)) return 'local';
  if(PA_ASK_KNOW.test(s)) return PA_LOCAL_PAT.test(s) ? 'local' : 'world';
  return 'other';
}
function paAskClass(text){
  const d = paAskDomain(text);
  return d === 'self' ? 'self' : ((d === 'local' || d === 'world') ? 'knowledge' : 'other');
}
try{ window.paAskDomain = paAskDomain; }catch(e){}
try{ window.paAskClass = paAskClass; }catch(e){}

/* ================= 六 · 六 · 兜底 ／ 失败态 ／ 共用件之包装（承 pm_1003 §二 · pm_1005 · pm_1012 §三/§四）=================
   ⭐ 兜底（改 pm_1012 §三）：知识检索回拒答 ⇒ ⛔ 上屏「查不到」 ⇒ **按问域**给人话：
     自述类 ⇒ 本机来源拼答｜本机素材类 ⇒ 「本机素材里没查到」＋ 三条下一步｜域外类 ⇒ 「超出本机素材范围」＋ 下一步。
   ⭐ 失败态（pm_1012 §四 令③）：任何取数失败 ⇒ 用户面只有一句人话 ＋ 一个下一步；裸异常串入工程注记。
   ⚠ 皆为**包装**（⛔ 改共用件 chat.js ／ send.js ／ status.js ／ products.js 一字；status.js 唯单源化一处 · 已明令）。 */
function paSelfFailText(s){
  const t = String(s == null ? '' : s);
  if(/^⏹\s*本轮/.test(t.trim()) && /已中止/.test(t)){
    return {u:'⏹ 本轮已中止（你点了「停止」，或页面取消了这次请求）—— 不是失败，也不是完成；要结果请再发一次。',
            e:'原始提示：' + t};
  }
  if(/Failed to fetch|NetworkError|TypeError|连不上后端|网络不可达|通道请求失败|后端未应答/i.test(t)){
    /* ⭐ 令②（承 pm_1026 §二 ／ pm_1028 §一.1）：失败态须给可行动之因与法 ——
       其「因」取真源快照（pa/ui_state.json 之「本地在」「远端在」）⇒ ⛔ 编；
       ⛔ 自动载模型；⛔ 以「重试即好」为劝（承 L76）。 */
    const ui = paSelfUiCache || null;
    const loc = ui ? paSelfYN(ui['本地在']) : '未知';
    /* ⭐ pm_1045 §三：远端 ⛔ 只取布尔 —— 改读快照「远端态」（三态）／「远端因」（可回指） */
    const rt = paRemTri(ui);
    const rshow = paRemText(ui);
    const rwhy = paRemWhy(ui);
    const both = (loc === '✓' && rt === '配了且通');
    const cause = both
      ? '这题需要模型：本机模型与远端 API 皆在（快照：本地在 ✓ · 远端态 配了且通）⇒ 本次请求本身出错'
      : '这题需要模型：本机模型未载 ／ 未应答（源：快照「本地在 ' + loc + '」） ∧ 远端 ' + rshow
        + '（源：快照「远端态 ' + rshow + '」·「远端因 ' + rwhy + '」）';
    const acts = '① 检查网络 ／ 代理 ② 需要时我可载本机模型（默认 5 分钟后自卸 · 须你准 · ⛔ 我不会自动载）';
    return {u:'⚠ 这次没送到 —— ' + cause + '。顶栏读数：本地在 ' + loc + ' · 远端 ' + rshow
              + '（源 pa/ui_state.json · 刻 ' + (ui ? String(ui['刻'] || '未知') : '未取到') + '）⇒ ' + acts + '。',
            e:'原始报错：' + t};
  }
  if(/PA\s*通道暂不可用|未挂载/.test(t)){
    /* ⭐ 补（pm_1031 §二 令② 同族）：回落之两路皆不通（检索未命中 ∧ 通道 404）⇒ 也是「没送到」，
       ⛔ 贴「由模型作答」之标（那会让用户以为模型说了话）（承 L76）。 */
    return {u:'⚠ 这次没送到 —— 后端说「PA 对话通道暂不可用」（404：接口未挂载）；检索侧亦未命中 ⇒ 两路皆不通。可：① 再发一次 ② 把本句发我，我查后端通道挂载。',
            e:'原始返回：' + t};
  }
  return null;
}
(function(){
  let lastQ = '', aside = null, gateInfo = null;
  /* ⭐ pm_1073 §二.1 之补（判据见 §二.3）：拒答轮亦须**真落盘**（承 send.js:28 之同法）——
     本路（闸已拒答 ⇒ 回落模型 ⇒ 模型路败 ／ 模型亦辞）被本层**劫持** ⇒ 绕过 send.js:28 之 `recordPaTurn`
     ⇒ `paRun.receipt` 恒 null ⇒ finally 出「⚠ 本轮未落盘：后端无回执或无变化（未取得回执）」
     ＝ ⭐ **误标**（实为「**未调**落盘口」· ⛔ 非「后端无回执」 · 承 pm_1073 §二.3）。
     法：本条自记回执；其未落地前**押下**该行（⛔ 以「模型路之败」当「未落盘」），落地后按**真回执**出一行。 */
  let paSelfRefusalGate = null;
  function paSelfRefusalReceiptLine(rc){
    if(rc && rc.recorded){
      addLog('💾 本轮已落盘（后端回执：会话 ' + (rc.session_lines_before != null ? rc.session_lines_before : rc.session_lines)
        + '→' + (rc.session_lines_after != null ? rc.session_lines_after : rc.session_lines) + ' 行 · events '
        + rc.events_lines_before + '→' + rc.events_lines_after + ' 行 · ' + (rc.session_path || '') + '）', 'ok', true, 'P9 BUG-1');
    } else {
      addLog('⚠ 本轮未落盘：后端无回执或无变化（未取得回执） —— ⛔ 不等于已保存', 'warn', true, 'P9 BUG-1');
    }
  }
  function paSelfRefusalRecord(sid, q, ans, meta){
    if(typeof recordPaTurn !== 'function' || !sid) return;
    const gate = {done:false, held:false};
    paSelfRefusalGate = gate;
    const settle = function(rc){
      if(gate.done) return;
      gate.done = true;
      if(paSelfRefusalGate === gate) paSelfRefusalGate = gate.held ? null : gate;
      if(gate.held){ try{ paSelfRefusalReceiptLine(rc); }catch(e){} }
    };
    setTimeout(function(){ if(!gate.done){ gate.held = true; settle(null); } }, 12000);  /* 12 s 未回 ⇒ 照实「未落盘」（⛔ 静默丢行） */
    return Promise.resolve().then(function(){ return recordPaTurn(sid, q, ans, meta); })
      .then(function(rc){ settle(rc); return rc; }, function(){ settle(null); return null; });
  }
  /* ⭐ pm_1111 §二（老板令：四族亦须真落盘 ／ 承 L142 声明⟷执行须符 ／ L76 源随值）：
     本层（paSend 最外层 ／ addMsg 包装 ／ sendPA 包装）会在**达后端之前**就地作答 ——
     自述（paSelfSections）／元问（paSelfMetaAns）／闸拒（fbf）／失败态（paSelfFailText）。
     前二者已各取回执；⭐ **失败态支**（及 `aside` 支）原本**无落盘口** ⇒ 该轮 `POST /v9/pa/dialog`
     未被调 ⇒ 后端无由记 ⇒ 盘上无此行（技总 989 之 47 轮中 `23` 条「失败兜底」即此）。
     形：唯**落盘**（⛔ 改答体 ／ ⛔ 改路由 ／ ⛔ 以镜像充数）；出口复用 `paSelfRefusalRecord`
     （同一闸：押下「本轮未落盘」行 ⇒ 得**真回执**再出行 · 承 L83 单源）＋ 写回 `paRun.receipt`。 */
  function paSelfLocalRecord(q, ans, meta){
    if(paSelfRoundPersisted) return null;
    let sid = null;
    try{ const t = (typeof activeThread === 'function') ? activeThread() : null; sid = t ? t.id : null; }catch(e){}
    if(!sid || typeof recordPaTurn !== 'function') return null;
    paSelfRoundPersisted = true;
    const p = paSelfRefusalRecord(sid, q, ans, meta);
    if(p && typeof p.then === 'function'){
      p.then(function(rc){ try{ if(rc) paRun.receipt = rc; }catch(e){} }, function(){});
    }
    return p;
  }
  const origGate = window.paAskGate;
  if(typeof origGate === 'function'){
    window.paAskGate = async function(text){
      lastQ = String(text == null ? '' : text);
      /* ⭐ pm_1073 §二.2 之补（**我一手逮** · 承 L142 声明⟷执行须符 ／ L135 排「同名不同物」）：
         ⚠ 共用件 `status.js:32-38` 之请求体**无 `session_id`** ⇒ 后端 `_last_user_before`
           （`gateway_routes.py:402-405`）落「**最新会话**」（`picked_by:'newest'`）。
           而我一手见（2026-10-05 07:2x · 本页真值）：本页 `activeThread()` ＝ ⭐ `pa_muuej0u0`
           ⟷ 盘上最新会话 ＝ ⭐ `session_pa_mu6fxm7z.jsonl`（mtime 07:08:56）⇒ **二者非同物**
           ⇒ 元问之「上一句」取自**他会话**，而屏上仍写「据：本会话 <sid>」＝ ⭐ **声明失实**（承 L142）。
         法（唯本层 · ⛔ 动共用件 ／ ⛔ 动后端）：本回之 `/v9/pa/ask` 体**补 `session_id` ＝ 本页线程 id**
           （⛔ 改他字段 · ⛔ 改响应）；其口径与 `recordPaTurn`（status.js:43）之既有同（皆带 `session_id`）⇒ **单源**
           （承 L83）；本页线程 id 亦**只此一处取**（`activeThread().id` · ⛔ 另造）。
         ⚠ 此补**宜上收**至 `status.js`（甲类 · 须老板批）⇒ 我入报，⛔ 自擅动（承 L133）。
         ⚠ 仅**本回**改 `fetch`（调用前装 ／ 得报即卸）；命中判据窄（唯 `/v9/pa/ask` ∧ 体为串 ∧ 无 `session_id`）。 */
      /* ⭐ pm_1096 §二.3（老板批 P11 · 承 L83 单源）：本层原以「抦 fetch 补 session_id」兜共用件；
         今 `status.js:32-38` 已**就地**补 `session_id`（与 `recordPaTurn` 同径）⇒ ⭐ **攤兜**（唯真源一处 · ⛔ 两存）。
         ⚠ 本层只留 `lastQ` 记账与「转交」（⛔ 判域 · ⛔ 拼答）。 */
      const g = await origGate.apply(this, arguments);
      aside = null; gateInfo = null;
      if(g){
        /* ⭐ pm_1067 §四（承 L151）：元问 ⇒ 后端走**会话路**（ask_domain=meta）⇒ 此处只**转交**
           （⛔ 判域 ／ ⛔ 拼答 · 路由之轴归后端）；由 sendPA 包装照实上屏（⛔ 调模型）。 */
        if(g.ask_domain === 'meta'){
          try{ paSelfJudgeRemember(g); }catch(e){}
          paSelfMetaAns = {answer:g.answer, source:g.answer_source, prev:g.context_prev,
                           ctx:g.context_meta, judge:g.judge, at:g.read_at, q:lastQ};
          const out2 = {};
          for(const fk2 in g){ try{ out2[fk2] = g[fk2]; }catch(e){} }
          out2.refused = false; out2.grounded = false;
          return out2;
        }
        try{ paSelfFacesRemember(g); }catch(e){}   /* ⭐ pm_1039 §三：面读数取自本响应（⛔ 硬编） */
        try{ paSelfJudgeRemember(g); }catch(e){}   /* ⭐ pm_1067 §三：判据 ／ 档案面命中 ／ 答源 */
        if(g.grounded === true){
          try{ paSelfAskBump('hit', lastQ, '有据 ⇒ 贴据＋模型作答（/v9/pa/dialog）'); }catch(e){}
          gateInfo = {n:(g.evidence || []).length, scope:g.scope, faces:g.faces, searched:g.searched,
                      thr:g.threshold, read:g.read_at, kb:g.kb_root,
                      miss:(g.faces_missing || []), skip:(g.faces_skipped || {}), ev:(g.evidence || []),
                      judge:g.judge, archive_hits:g.archive_hits, answer_source:g.answer_source,
                      refusal_canon:g.refusal_canon, refusal_stale:g.refusal_stale,
                      verdict:g.verdict, domain:g.ask_domain};
        } else if(g.grounded === false || g.refused){
          if(g.refused){
            /* ⭐ pm 21:20 §三（裁：三形皆须禁）＋ §二.处2（档亦带标）：
               ⭐ 本机「事实／状态／账／决策」之是非问 ∧ 闸已拒 ⇒ ⛔ 回落模型。
               由（三条）：⒜ 回落之模型答即对本机事实作断言（承 §三.⒜ ⛔）；
                 ⒝ 该答由**后端**写档（`dialog.py` 之 `s.post("assistant", reply)`）⇒ **档无标**（承 §二.处2）；
                 ⒞ 保 `refused=true` ⇒ 共用件 send.js 之闸支就地出 canonical 拒答
                    ＋ 经 `recordPaTurn`（POST /v9/pa/turn）落盘 ⇒ **档带标**（承 L83 单源出口）。
               ⚠ 非「事实／状态／账／决策」之族（闲聊 ／ 商量 ／ 域外知识）**仍回落**（pm_1032 §三.1 之令未废）。 */
            if(paSelfFactYN(lastQ)){
              try{ paSelfAskBump('miss', lastQ, '本机事实族之是非问 ∧ 无据 ⇒ 保拒答 ⛔ 回落（承 pm 21:20 §三）'); }catch(e){}
              paSelfLbl = null; paSelfFb = null;
              return g;
            }
            /* ⭐ pm_1032 §三.1（承 L82「拒答即兜底」）：检索未命中 ⇒ **回落模型**。
               ⛔ 就地拒答（旧行为：一律「超出本机素材范围」⇒ 而模型其实能答 ⇒ 20%之题被误拒）。
               形：本包装**只改返回值**（refused:false）⇒ 共用件 send.js 之闸分流自然落入 sendPA（/v9/pa/dialog）
               ⇒ ⛔ 动 send.js 一字；失败态仍由既有「因＋法」出口兜。 */
            try{ paSelfAskBump('miss', lastQ, '检索未命中（无据）'); }catch(e){}
            try{ paSelfAskBump('fallback', lastQ, '未命中 ⇒ 回落模型（/v9/pa/dialog）'); }catch(e){}
            let dm = null; try{ dm = paAskDomain(lastQ); }catch(e){}
            paSelfFb = {q:lastQ, domain:dm, why:paSelfWhy(lastQ),
                        scope:((g.scope || []).join(' ／ ') || '—'),
                        facesText:(paSelfFaceText(g.scope, g.faces) || '—'),
                        defsText:(paSelfFaceDefText(g.scope, g.kb_root) || '—'),
                        miss:(g.faces_missing || []), skip:(g.faces_skipped || {}),
                        searched:(g.searched == null ? '—' : g.searched),
                        thr:(g.threshold == null ? '—' : g.threshold),
                        read:(g.read_at || '—'),
                        judge:g.judge, archive_hits:g.archive_hits, answer_source:g.answer_source, verdict:g.verdict,
                        refusal_canon:g.refusal_canon, refusal_stale:g.refusal_stale};
            paSelfLbl = null;
            const out = {};
            for(const fk in g){ try{ out[fk] = g[fk]; }catch(e){} }
            out.refused = false; out.grounded = false; out.fallbackToModel = true;
            return out;
          } else {
            try{ paSelfAskBump('miss', lastQ, '检索未命中（grounded:false）'); }catch(e){}
          gateInfo = {n:0, scope:g.scope, faces:g.faces, searched:g.searched, thr:g.threshold, read:g.read_at, ev:[],
                        judge:g.judge, archive_hits:g.archive_hits, answer_source:g.answer_source, verdict:g.verdict,
                        refusal_canon:g.refusal_canon, refusal_stale:g.refusal_stale};
          }
        }
      }
      if(!g){ try{ paSelfAskBump('askFail', lastQ, '闸未取得回报 ⇒ 按 other 路走'); }catch(e){} }
      return g;
    };
  }
  const origAdd = window.addMsg;
  if(typeof origAdd === 'function'){
    window.addMsg = function(role, content, skipStore, html, tid){
      if(role === 'user'){ paSelfLastUser = String(content == null ? '' : content); }
      if(role === 'assistant' && !html){
        const raw = String(content == null ? '' : content);
        const an = paSelfArithNote(paSelfLastUser, raw);   /* pm_1031 §二：算术如实标 */
        const ar = paSelfArithCheck(raw, paSelfLastUser);   /* pm_1034 §四② ＋ pm_1042 §二.2（带问句） */
        const seen = paSelfChkSeen;         /* ⭐ pm_1038 §三.1：本回**可判之式**之数 */
        const unc = paSelfUnchkNote(paSelfLastUser, raw, seen);  /* 算术类问 ∧ 无可判之式 ⇒ 「未复核」标 */
        if(unc) paSelfChkStat.nr++;
        const eqT = paSelfLastEq;           /* ⭐ pm_1036：本回首个可判之式 ⇒ 交**工具径**（判据主源） */
        const self2 = this;
        const emit = function(){                 /* 原样转发 ＋ 工具答到后就地升级（⛔ 变时序） */
          const d = origAdd.apply(self2, arguments);
          try{ if(ar && eqT) paSelfToolUpgrade(d, ar, eqT); }catch(e){}
          return d;
        };
        const wa = function(s){ return (an ? (an + '\n') : '') + s + (ar ? ('\n' + ar.u) : '') + (unc ? ('\n' + unc.u) : ''); };
        const wcE = paSelfWcNote(paSelfLastUser, raw);   /* ⭐ pm_1042 §三：自陈字数 · 只入注记 */
        const say = function(u, e){ return paSelfSayHtml(u, (e ? e : '') + (ar ? ar.e : '') + (unc ? unc.e : '') + (wcE ? ('\n' + wcE) : '')); };
        const fbf = paSelfFb; paSelfFb = null;             /* 一轮一清（⛔ 跨轮复用 ⇒ ⛔ 贴错标） */
        const fx = paSelfFailText(raw);            /* 令③：失败态人话（⛔ 裸异常串上屏） */
        /* ⭐ pm_1073 §二.1（承 L103 形与义分 ／ L142 声明⟷执行须符 ／ L76 源随值）：本回「有据才答」闸
           **已判拒答**（`fbf` 在 · 后端 `answer_source ∈ {refused, archive_only}`）者 ⇒ 用户面**须显拒答**
           （照后端 `verdict` 逐字），⛔ 不许把「模型路之败」或「模型之辞」渲成
           「**这题需要模型 … 本次请求本身出错**」—— 该二句皆**谎**（后端 200 且已判 ⇒ 拒答即**正果** · 承 L150）。
           ⚠ 两路仍可分（承 pm_1073 §三 Ⅳ · pm_1032 §三.1 之**回落令未废**）：模型**实答**（其辞非拒答词形）
             ⇒ 落下方 `fbf` 支照旧（贴「由模型作答」 · K5 之形）。 */
        if(fbf && (fx || paSelfRefusal(raw))){
          paSelfLbl = null;
          try{ paSelfAskBump(fx ? 'refusalOnModelFail' : 'refusalOnModelDecline', null, ''); }catch(e){}
          /* ⭐ pm_1073 §二.1 同族（承 L76 源随值 ／ L142 声明⟷执行须符）：模型路若**败**，共用件 send.js:76
             已置 `failed`（其形是「❌ 已失败」）—— 而本回之**果**是**拒答**（正果）且**已落盘**
             ⇒ 顶栏若仍报「已失败」，即与屏上之答**相左**（同一「误类」）。故按实置 `done`，
             源改回**本条之真源** `/v9/pa/ask`（⛔ 留 `POST /v9/pa/dialog` —— 那条路已败）。
             ⚠ 模型路之败**不隐**：入注记（见下 E2 之首行）· 承 L76「⛔ 丢」。
             ⚠ **此处⛔ 置**（我一手见：`send.js:76` 之 `paSetState('failed',…)` 在 `addMsg` **之后** ⇒ 就地置必被盖回）
               ⇒ 只**立旗**，由本层之 `sendPA` 包装**收尾**时扳回（承 L124 量具／时序须实读）。 */
          if(fx){ paSelfRefusalDone = true; }
          const arcU = paSelfArchiveText(fbf);
          const U2 = [];
          U2.push(paSelfTag('refuse', null));
          U2.push('本机无据 ⇒ 拒答（⛔ 我编）。');
          if(fbf.verdict) U2.push('后端判词：' + fbf.verdict);
          U2.push(paSelfJudgeText(fbf));
          if(arcU && (!fbf.verdict || String(fbf.verdict).indexOf('档案面另有') < 0)) U2.push(arcU);
          U2.push('⛔ 本问不予编答 —— 库里无依据 ⇒ 按「有据才答」不答（后端 200 · 拒答即正果）。');
          const E2 = [];
          E2.push('判据：/v9/pa/ask ｜ grounded:false ｜ refused:true ｜ answer_source:' + (fbf.answer_source || '—')
            + ' ｜ 问域（前端轴）' + (fbf.domain || '—'));
          E2.push('检索侧读数（源 /v9/pa/ask）：范围 ' + fbf.scope + ' ｜ 逐面 ' + (fbf.facesText || '—')
            + ' ｜ 实搜 ' + fbf.searched + ' 件 ｜ 阈值 ' + fbf.thr + ' ｜ 读数 ' + fbf.read);
          E2.push(paSelfJudgeText(fbf));
          if(arcU) E2.push(arcU);
          if(fbf.why) E2.push('分流判据（可回指）：' + fbf.why);
          E2.push(fx
            ? ('⚠ 模型路之读数（⛔ 不作答 · ⛔ 不改上判）：' + fx.e)
            : ('⚠ 模型路之辞（⛔ 不作据 —— 其形即后端所令之「无命中只许说查不到」）：' + raw));
          E2.push('⚠ 本层所改唯**呈现**（⛔ 改路由 ／ ⛔ 改后端值）· 承 pm_1073 §二.1；'
            + '模型路之试（pm_1032 §三.1 之回落）**仍在**（承 pm_1073 §三 Ⅳ）。');
          E2.push('原问：' + fbf.q);
          const U2s = U2.join('\n');
          let _sid = null;
          try{ const _t2 = (typeof activeThread === 'function') ? activeThread() : null; _sid = _t2 ? _t2.id : null; }catch(e){}
          /* ⭐ pm 1184 §一.⒝：拒答轮之档行 ⇒ `origin=refused` ／ `grounded=false` ／ `answer_source` 取后端原值。 */
          try{ paSelfRefusalRecord(_sid, fbf.q, U2s, {origin:'refused', grounded:false, answer_source:(fbf.answer_source||'refused')}); }catch(e){}
          return emit.call(this, 'assistant', U2s, skipStore, say(U2s, E2.join('\n')), tid);
        }
        if(fx){
          paSelfLbl = null;
          if(fbf){ try{ paSelfAskBump('fallbackFail', null, ''); }catch(e){} }
          const fe = fx.e + (fbf ? ('\n检索侧读数（/v9/pa/ask）：范围 ' + fbf.scope + ' ｜ 逐面 ' + (fbf.facesText || '—') + ' ｜ 实搜 ' + fbf.searched
            + ' 件 ｜ 阈值 ' + fbf.thr + ' ｜ 读数 ' + fbf.read + ' ｜ 问域 ' + (fbf.domain || '—')
            + ' ⇒ 未命中 ⇒ 本已按「回落模型」转出，而模型亦不可达（承 pm_1032 §三.1）。') : '');
          try{ paSelfLocalRecord(paSelfLastUser, fx.u); }catch(e){}   /* ⭐ pm_1111 §二：失败态亦须真落盘（⛔ 以「未调落盘口」当「未落盘」） */
          return emit.call(this, 'assistant', fx.u, skipStore, paSelfSayHtml(fx.u, fe), tid);
        }
        if(fbf){
          /* ⭐ pm_1032 §三.1/2/4：检索未命中 ⇒ 模型作答 ⇒ 用户面标「源之分标」（回落）＋判据回指。 */
          paSelfLbl = null;
          const tl = paSelfTag('fallback', null);
          const _arcF = paSelfArchiveText(fbf);
          /* ⭐ pm 21:20 §二.处1/处3：闸已拒 ∧ 无本机据 ⇒ ⛔ 引模型对本机事实之断言。
             ⛔ 以词形为唯一之闸；canonical 拒答文之真源 ＝ send.js 之 `PA_REFUSE_CANON`（⛔ 二处各写）。 */
          const _forbid = paSelfModelAssertForbidden(fbf.q, raw);
          /* ⭐ pm 1184 §一.⒜：canonical 引**后端** `fbf.refusal_canon`（真源）；本件之 `PA_REFUSE_CANON` 唯**回落**。 */
          const _canon = (typeof paRefusalCanon === 'function') ? paRefusalCanon(fbf)
            : ((typeof PA_REFUSE_CANON === 'string') ? PA_REFUSE_CANON : '⚠ 拒答文缺（⛔ 静默）');
          const au = tl + '\n' + (_forbid ? _canon : wa(raw)) + (_arcF ? ('\n\n' + _arcF) : '');
          const fe = (_forbid ? ('⚠ 模型之辞（⛔ 作据 · 已拦下 · 承 pm 21:20 §二.处1/处3）：' + raw + '\n') : '')
            + '本问先过「有据才答」闸（/v9/pa/ask）⇒ ⭐ 闸判 **本机无据（拒答）**'
            + '（承 pm_1076 §三：与答体**两段并标** · ⛔ 单标）⇒ 已按 pm_1032 §三.1 **回落模型**'
            + '（POST /v9/pa/dialog · 分流同一出口 paAskDomain）⇒ 此处之答由模型生成（⛔ 非本机素材）。'
            + '\n检索侧读数（逐面件数 · 源 /v9/pa/ask 之 scope ／ faces ／ searched）：范围 ' + fbf.scope
            + ' ｜ 逐面 ' + (fbf.facesText || '—') + ' ｜ 实搜 ' + fbf.searched + ' 件 ｜ 阈值 ' + fbf.thr + ' ｜ 读数 ' + fbf.read
            + '\n' + paSelfJudgeText(fbf)
            + ((paSelfAnswerSourceText(fbf)) ? (' ｜ ' + paSelfAnswerSourceText(fbf)) : '')
            + (_arcF ? ('\n' + _arcF) : '')
            + ((fbf.verdict) ? ('\n后端判词：' + fbf.verdict) : '')
            + '\n分流判据（可回指 · 承 pm_1032 §三.4）：问域 ' + (fbf.domain || '—') + ' ｜ ' + (fbf.why || '—')
            + '\n原问：' + fbf.q;
          return emit.call(this, 'assistant', au, skipStore, say(au, fe), tid);
        }
        if(aside && paSelfRefusal(raw)){
          const a = aside; aside = null;
          const ev = paSelfEvidText(raw);
          const dmk = (a && a.domain);
          const kind = (dmk === 'local') ? 'localmiss' : ((dmk === 'self') ? 'nil' : 'none');
          const tl = paSelfTag(kind, null);
          const au = (tl ? (tl + '\n') : '') + a.u;
          try{ paSelfLocalRecord(paSelfLastUser, au); }catch(e){}   /* ⭐ pm_1111 §二：本地作答（本机素材未命中）亦须落盘 */
          return emit.call(this, 'assistant', au, skipStore, paSelfSayHtml(au, a.e + (ev ? ('\n原读数：' + ev) : '')), tid);
        }
        if(gateInfo){
          const g = gateInfo; gateInfo = null;
          const b = paSelfEvidBlock(g);
          const tag = paSelfTag(g.n > 0 ? 'local' : 'model', g.n);
          const full = tag + '\n' + wa(raw) + '\n\n' + b.u;
          return emit.call(this, 'assistant', full, skipStore, say(full, b.e), tid);
        }
        /* ⭐ pm 22:34 §一.E ／ §四（CW 办「拒答话术」）＋ 承 pm 21:20 §二.处3 ＋ ⭐ pm 1184 §三：
           ⛔ 载入**后端 ／ 模型之拒答原辞**（「查不到（知识库里没有相关内容）」＝**「知识库」之辞** ——
           而闸实扫**八面**（`g.scope`）⇒ 该辞**失实**）⇒ 概书 canonical；原辞留**径**（注记）。
           ⭐ **今退为「兜底校验」**（pm 1184 §三）：后端已自出 canonical（`refusal_canon`）⇒ 本支
             **唯于`raw` 仍为拒答之旧辞时**方动（判 ＝ `paSelfRefusal(raw)` · 词形**旁证**）；
             ⛔ 概覆 —— 后端之正辞 ／ 逐字之由（如 `decision_none`）皆**不触**本支（守界 · 承 §一.⒜）。
           ⚠ 位次：本支**须在** `paSelfLbl` ／ `paSelfLegacySplit` 之前 —— 二者会把「查不到…」
             渲成「模型生成」或「整条工程注记」（我一手见 · 皆非 canonical ⇒ 承「一处口径」）。
           ⚠ canonical 之真源 ＝ send.js 之 `PA_REFUSE_CANON`（⛔ 二处各写 · 承 L83）。 */
        if(paSelfRefusal(raw)){
          paSelfLbl = null;
          const _cn = (typeof PA_REFUSE_CANON === 'string') ? PA_REFUSE_CANON : '本机无据 ⇒ 我不答此问。';
          const _cu = wa(_cn);
          return emit.call(this, 'assistant', _cu, skipStore,
            say(_cu, '⚠ 后端 ／ 模型之拒答**原辞**（⛔ 载入答话 · 承 pm 22:34 §一.E「载径 ⛔ 载值」）：' + raw), tid);
        }
        if(paSelfLbl){
          const l = paSelfLbl; paSelfLbl = null;
          const full = l + '\n' + wa(raw);
          return emit.call(this, 'assistant', full, skipStore, say(full, null), tid);
        }
        const lg = paSelfLegacySplit(raw);
        if(lg) return emit.call(this, 'assistant', wa(lg.u), skipStore, say(wa(lg.u), lg.e), tid);
        const hu = paHumanizeErr(raw);
        if(hu !== raw) return emit.call(this, 'assistant', wa(hu), skipStore, undefined, tid);
        if(an || ar || unc) return emit.call(this, 'assistant', wa(raw), skipStore, (html ? html : say(wa(raw), null)), tid);
      }
      return origAdd.apply(this, arguments);
    };
  }
  const origLog = window.addLog;
  if(typeof origLog === 'function'){
    window.addLog = function(line, cls, store, title, tid){
      /* ⭐ pm_1073 §二.1/§二.3：拒答轮之「未落盘」行须依**真回执** —— 该轮之回执为**自记**
         （见 paSelfRefusalRecord）⇒ 其未落地前**押下**此二行（⛔ 以「模型路之败」当「未落盘」）；
         落地后由 paSelfRefusalReceiptLine 出真行；曾押过者，此后再来即**丢**（⛔ 二行相左）。 */
      if(paSelfRefusalGate && String(line).indexOf('本轮未落盘') >= 0){
        if(paSelfRefusalGate.done){ paSelfRefusalGate = null; return undefined; }
        paSelfRefusalGate.held = true; return undefined;
      }
      const l = paHumanizeErr(line);
      const hum = paLogHuman(l);
      if(hum){
        const r = origLog.call(this, hum, cls, store, (title ? (title + ' \uff5c ') : '') + String(l), tid);
        /* pm_1013 §三 之补：既有运行记录里被剥下的原文 ⇒ 附**可点**之「原文」折叠（⛔ 只挂 title 悬停）。
           合并路径（同内容 ×N）会 textContent 重置 ⇒ 由 paEngCleanThread 之 __engNote 支补回。 */
        try{
          const ent = window.__logEls && window.paFoldKey && window.__logEls[window.paFoldKey(hum, cls, store)];
          const el = ent && ent.el;
          if(el && !el.__engNote && !el.querySelector('details.eng') && String(el.textContent || '').indexOf(hum) === 0){
            el.__engNote = String(l);
            el.setAttribute('data-raw', String(l));
            el.appendChild(paEngNoteEl(l));
          }
        }catch(e){}
        return r;
      }
      return origLog.call(this, l, cls, store, title, tid);
    };
  }
  /* ⭐ ×N 漏屏之修（承 pm_1026 §一 令① ／ pm_1028 §一.1）：最外层再包一道 ——
     ① 入口剥（⛔ 让共用件之合并键把 `×N` 当内容 ⇒ 键稳 · ⛔ 重复行）；② 出口擦（每记一条即扫）。
     ⛔ 动共用件 products.js（生成点：298 写 DOM · 302 写存档）与 chat.js（再喂点：52）一字。 */
  /* ⭐ pm_1071 §二（承 L133 ／ L76 ）：`send.js` 之落盘回执行呈
     `💾 本轮已落盘（… 会话 <前>→<后> 行 · events <前>→<后> 行 …）`
     ⇒ 其轴不同（events ＝ **全局事件面** ⟷ 会话 ＝ **本会话**）⇒ 用户可能误读为「本会话」。
     ⇒ ⭐ **渲染层补注**：⛔ 动共用件 `send.js` ／ ⛔ 改存档 —— 唯补**显示**（textContent 子节点 ＋ title ＋ data-axis）；
     传给共用件之 `line` 一字不改（⇒ `th.msgs` ／ `localStorage` 所得仍原串、可回指）。
     ⚠ 合路（products.js:298 之 `×N`）会重置 textContent ⇒ 故补注**每次入此支即重补**（幂等 · ⛔ 重复）。 */
  const PA_LEDGER_AXIS_TAG = '（events ＝ 全局事件面 · ⛔ 本会话）';
  const PA_LEDGER_AXIS_TITLE = 'events ＝ 全局事件面（各会话共用 · 含归档之读）· ⛔ 本会话';
  function paLedgerAxisHit(s){ return String(s).indexOf('已落盘（') >= 0 && /events\s*\d+→\d+\s*行/.test(String(s)); }
  const origLogMul = window.addLog;
  if(typeof origLogMul === 'function'){
    window.addLog = function(line, cls, store, title, tid){
      const raw0 = String(line == null ? '' : line);
      const mul0 = (raw0.match(/(?:^|\s)×(\d+)(?=\s|$)/) || [, ''])[1];
      const clean0 = mul0 ? paSelfMulClean(raw0) : raw0;
      const ttl = mul0 ? ((title ? (title + ' ｜ ') : '') + '合并计数 本轮 ×' + mul0) : title;
      /* ⭐ pm_077 §一（正法 · 已撤 pm_076 §二 之绕法）：探针（`store === false`）之轮 ⛔ 计
         —— 其核在共用件 `products.js` 之折叠键 ⇒ ⭐ 按键之**分桶**（探针自成一桶 ·
         `paFoldKey(line, cls, store)`）⇒ ⛔ 由外动全局表（绕法动全局表 · 异常路下真表
         或 ⛔ 复 ⇒ 动面之状态 · 承 L161）。本层 ⛔ 再「暂置空表」。 */
      const r = origLogMul.call(this, clean0, cls, store, ttl, tid);
      try{ paSelfMulPass(); }catch(e){}
      try{
        if(paLedgerAxisHit(raw0)){
          const ent = window.__logEls && window.paFoldKey && window.__logEls[window.paFoldKey(clean0, cls, store)];
          const el = ent && ent.el;
          if(el){
            if(String(el.textContent || '').indexOf(PA_LEDGER_AXIS_TAG) < 0){
              el.appendChild(document.createTextNode(' ' + PA_LEDGER_AXIS_TAG));   /* ⛔ 重写 textContent（免毁子节点 · 如 `details.eng`） */
            }
            el.dataset.axis = 'global';
            /* ⛔ 盖写 title：合路（products.js:298）后 paSelfMulPass 已把
               「合并计数 本轮 ×N」写入 title ⇒ 此处只**追加**（⛔ 丢信息 · 幂等）。 */
            const _pt = String(el.title || '');
            if(_pt.indexOf(PA_LEDGER_AXIS_TITLE) < 0){
              el.title = (_pt ? (_pt + ' ｜ ') : '') + PA_LEDGER_AXIS_TITLE;
            }
          }
        }
      }catch(e){}
      return r;
    };
  }
  /* ⭐ pm_1044 §四（承 L85 ／ L76）：无源态须说人话 —— ⛔ 裸「—」。
     我一手定位之两处「裸 —」：ⓜ 静态占位 `#runStateSrc` 初值「状态来源：—」（`pa.html:18`；
     `paRenderState` 未跑时它就在上面）ⓝ `status.js:22` 之 `paRunSrc` 默认「—（尚未收到后端事件）」。
     ⇒ 修（唯 v3 专用件 · ⛔ 改 `pa.html` ／ `status.js`）：
         ① `paSelfNoSrcV` ：认「无源诸形」（空 ／ 以 `—` 开头 ／ 含「尚未收到后端事件」 ／ 含「无请求源」）
         ② `paSelfSrcPass` ：凡无源诸形 ⇒ 统一渲染「本次未发请求」（⛔ 动 `paRunSrc` 本身 · 只改显示）
         ③ 包 `paRenderState`：每次渲染后过一遍；④ 载入即跑一次（修静态占位）
     并办（照实 · 非本令所提）：`/v9/pa/ask` 之路**从不置 `paRunSrc`**（`send.js:21` 只调 `paAskGate`）
       ⇒ 若不补，问过知识题后顶栏会**误说**「本次未发请求」 ⇒ 包 `paAskGate` 置「POST /v9/pa/ask」。 */
  const PA_NO_SRC_TEXT = '本次未发请求';
  function paSelfNoSrcV(s){
    const v = (s == null ? '' : String(s)).trim();
    if(!v) return true;
    if(v === PA_NO_SRC_TEXT) return false;
    return v.charAt(0) === '—' || v.indexOf('尚未收到后端事件') >= 0 || v.indexOf('无请求源') >= 0;
  }
  function paSelfSrcPass(){
    const el = document.getElementById('runStateSrc'); if(!el) return null;
    const val = String(el.textContent || '').replace(/^状态来源：/, '').trim();
    if(paSelfNoSrcV(val)){ el.textContent = '状态来源：' + PA_NO_SRC_TEXT; return 'no-src'; }
    return 'ok';
  }
  window.paSelfNoSrcV = paSelfNoSrcV;
  window.paSelfSrcPass = paSelfSrcPass;
  const origRender = window.paRenderState;
  if(typeof origRender === 'function'){
    window.paRenderState = function(){
      const r = origRender.apply(this, arguments);
      try{ paSelfSrcPass(); }catch(e){}
      return r;
    };
  }
  const origAskGate = window.paAskGate;
  if(typeof origAskGate === 'function'){
    window.paAskGate = async function(){
      try{ paRunSrc = 'POST /v9/pa/ask'; }catch(e){}
      return await origAskGate.apply(this, arguments);
    };
  }
  function paSelfSrcInit(){ try{ paSelfSrcPass(); }catch(e){} }
  if(document.readyState === 'loading'){ document.addEventListener('DOMContentLoaded', paSelfSrcInit); }
  else { paSelfSrcInit(); }
  const origSet = window.paSetState;
  if(typeof origSet === 'function'){
    window.paSetState = function(k, note, src){
      /* ⭐ pm_1031 §三.2（承 L76 ／ L83）：状态 ／ 源 須同步 —— 共用件 status.js:52 之 `if(src) paRunSrc=...`
         只覆盖 ／ 不落空 ⇒ **不带源之调用使源落后于状态**（send.js:71/76/129/135 ／ cards.js:239/303）。
         修：记最近一次**请求**之源；凡「失败」支未带源 ⇒ 接着最近请求之源（⛔ 沉默留旧源 ⇒ 让用户以为源＝现态）。
         ⚠ 形之定（我一手量 · pm_1033 §四 之前）：本帧之源串**不可加长** —— 顶栏「如实读数」行调客宽：
         源 = 「POST /v9/pa/dialog」（160 px）⇒ uis 707 / 606 px ⇒ sw＝cw（⛔ 省略）；加「（就地置位）」（226 px）⇒ uis 540 px ⇒ **sw 556 > cw 540 ⇒ 省略号**。
         ⇒ 故：有请求源 ⇒ 原样（⛔ 加尾）；无请求源 ⇒ 短形「（就地置位 · 无请求源）」（183 px · uis 583 > 556 ⇒ 合）。
         ⚠ 此段系 pm_1031 ／ pm_1044 之**原法**（**只补 `failed` 一支**）⇒ 已由下方 `pm_1059 §二.①` **扩展为「凡不带源者皆补」**
           （⛔ 回改历史 · 此处只加一格指路行 ⇒ 免下一个读码者被旧法误导 · 承 pm_1047 之同族）。 */
      const s0 = (src == null ? '' : String(src)).trim();
      if(s0) paSelfLastReqSrc = s0;
      let use = src;
      if(!s0){
        /* ⭐ pm_1059 §二.①（承 L76「源须随值」）：共用件 status.js:52 之 `if(src) paRunSrc=…` **只覆盖 ／ 不落空**
           ⇒ **凡不带源之调用，皆使源落后于状态**（send.js:7/29/61/67/71/75/76/114/121/129/135/141/156/159/186/202/213/220/228/246/254/258/263/281
            ／ cards.js:239/303）。原法（pm_1031 ／ pm_1044）**只补 `k === 'failed'` 一支** ⇒ 本令扩至**凡不带源者皆补**：
           取「当前之真源」＝ `paRunSrc` 之现值（＝最近一次真发之径 ⇒ send.js:68/115/175 直置之值亦在）⇒
           无 ⇒ 退回「最近一次带源调用之值」⇒ 两者皆无（＝本页确未发过请求）⇒ 人话「本次未发请求」（⛔ 裸「—」）。
           ⚠ 形之定（承 pm_1033 §四 之量 · ⛔ 破）：所补之串**恒等于**已在屏者（或更短）⇒ 顶栏行宽**不增** ／ 控件**不增**。
           ⚠ 带源者（`s0` 真）⇒ **原链一字不动**（承「⛔ 动原行为」）。 */
        let cur = '';
        try{ cur = (typeof paRunSrc === 'string') ? String(paRunSrc).trim() : ''; }catch(e){ cur = ''; }
        use = (cur && !paSelfNoSrcV(cur)) ? cur : (paSelfLastReqSrc || PA_NO_SRC_TEXT);
      }
      return origSet.call(this, k, (note == null ? note : paHumanizeErr(note)), use);
    };
  }
  /* 共用件 status.js 之「探针」一词（本机浏览器未连时上屏）⇒ 由 v3 专用件净化（⛔ 改共用件） */
  const origProbe = window.probeConn;
  if(typeof origProbe === 'function'){
    window.probeConn = async function(){
      const r = await origProbe.apply(this, arguments);
      try{
        const el = document.getElementById('connDot');
        if(el && paEngHit(el.textContent || '')){
          el.title = el.textContent;
          el.textContent = '● 本地浏览器未连（自检时刻 ' + new Date().toLocaleTimeString('zh-CN', {hour12:false}) + '）';
        }
      }catch(e){}
      return r;
    };
  }
})();

/* ⭐ pm_1067 §四（承 L151 ／ L83）：元问（ask_domain=meta）之**上屏器** —— 后端已给真源
   （answer ＝ 本会话上一句之原文 ∨ answer_source=context_missing ⇒ 如实不答）⇒ 此处**照实上屏**
   （⛔ 调模型 ／ ⛔ 前端拼答），并交回执（recordPaTurn · 既有出口）。
   ⚠ 唯 ask_domain === 'meta' 时接管 ⇒ 其余一切原链一字不动（承「⛔ 动原行为」）。 */
(function(){
  const orig = window.sendPA;
  if(typeof orig !== 'function') return;
  /* ⭐ pm_1069 §四（承 L83 单源 ／ L102 ／ L123 ／ L159）：自测痕之判 **⛔ 前端自持词表**
     ⇒ 取真源 `GET /v9/pa/context` 之 `selftest_marks`（＝后端 `PA_SELFTEST_MARKS` · 判据同源）；
     判据同后端 = **子串任意位**（⛔ 句首限定）；取不到 ⇒ 照实「未取到词表」 ∧ ⛔ 本地表兜（兜则两表又漂 ⇒ 宁不兜）。 */
  let paSelfMarks = null;   /* null ＝ 未取到（⛔ 兜）／ 数组 ＝ 已取到真源 */
  async function paSelfMarksLoad(){
    try{
      const d = await paSelfJson(API + '/v9/pa/context?user_id=' + encodeURIComponent(curUser()));
      const a = (d && Array.isArray(d.selftest_marks))
        ? d.selftest_marks.filter(function(x){ return typeof x === 'string' && x; }) : null;
      paSelfMarks = (a && a.length) ? a : null;
      return paSelfMarks;
    }catch(e){ paSelfMarks = null; return null; }
  }
  function paSelfIsSelfTest(t){
    const s = String(t == null ? '' : t).trim();
    if(!s || !paSelfMarks) return false;   /* 词表未取到 ⇒ ⛔ 兜（承 pm_1069 §四 Ⅱ） */
    for(let i = 0; i < paSelfMarks.length; i++){ if(s.indexOf(paSelfMarks[i]) >= 0) return true; }
    return false;
  }
  try{ window.paSelfMarksGet = function(){ return paSelfMarks; }; }catch(e){}
  try{ window.paSelfMarksLoad = paSelfMarksLoad; }catch(e){}
  /* ⭐ pm_1068 §二 ／ §三 ／ §四：`answer_source==='context'` ⇒ 答体**逐字** ＝ 后端 `answer`
     （⛔ 包装 ／ ⛔ 拼「查不到」／ ⛔ 掺模型句）；自测痕 ⇒ 判「无可读上一句」（⛔ 引用）；
     `context_meta` 四值（session_id ／ read_at ／ picked_by ／ reason）上屏（值取后端 · ⛔ 硬编）。 */
  function render(m){
    const cm = (m && m.ctx && typeof m.ctx === 'object') ? m.ctx : {};
    const at = (m && m.at) ? String(m.at) : '';
    const sid = cm.session_id ? String(cm.session_id) : '';
    const pick = cm.picked_by ? String(cm.picked_by) : '';
    const ans = String((m && m.answer) == null ? '' : m.answer);
    const marksMissing = !paSelfMarks;   /* ⭐ pm_1070 §三：词表缺 ⇒ 本轮「不可判」（⛔ 引其句） */
    const undec = (m && m.source === 'context') && !!ans && marksMissing;
    const trace = (m && m.source === 'context') && paSelfIsSelfTest(ans);
    const miss = !m || m.source !== 'context' || !ans || trace || undec;
    const L = [];
    if(!miss){
      L.push(paSelfTag('ctx'));
      L.push(ans);                                    /* ⭐ 逐字（⛔ 增一字） */
      L.push('源：本会话 ' + (at || '刻未给') + '（⛔ 检索面 · ⛔ 模型）');
    } else if(undec){
      L.push(paSelfTag('undec'));
      L.push('⛔ 引（本轮不判其是否为自测痕）。');
    } else {
      L.push(paSelfTag('ctxmiss'));
      L.push('如实不答。');
      if(trace) L.push('（最近一句为本机自测记录 ⇒ ⛔ 引作你之上一句。）');
    }
    L.push('据：本会话 ' + (sid || '未给') + ' · 上一句之刻 ' + (at || '未给') + ' ／ picked_by=' + (pick || '未给'));
    const e = [];
    e.push('判据：/v9/pa/ask ｜ ask_domain:meta ｜ answer_source:' + ((m && m.source) || '未给')
      + ' ｜ grounded:false ｜ refused:false ｜ 读数 ' + (at || '未给'));
    e.push(paSelfJudgeText({judge:(m && m.judge) || null, read_at:at}));
    e.push('本答之原文 ＝ 后端 answer（⛔ 前端包装 ／ ⛔ 拼「查不到」／ ⛔ 掺模型句 · 承 pm_1068 §二）；'
      + '答源之轴归后端（ask_domain：meta ／ retrieve · 承 L151 · 与前端 paAskDomain 分轴 · ⛔ 二处各判同一物）。');
    if(trace) e.push('⚠ 后端所给之「上一句」经本层判为**自测痕**（端到端自检 ／ （自测） 类）⇒ 未引作你之上一句'
      + '（⛔ 作答 · 承 pm_1068 §四 ／ L138）；其出处见后端 context_meta。');
    if(!paSelfMarks) e.push('⚠ 自测痕词表未取到（真源 GET /v9/pa/context 之 selftest_marks）⇒ ⭐ 本轮判**不可判**'
      + '（⛔ 引其句 ／ ⛔ 静默放行 · 承 pm_1070 §三 ／ L159）；后端 `_last_user_before` 本已排自测痕'
      + '（前端 ⛔ 最后防线 · 承 L83）。');
    const bits = [];
    if(pick) bits.push('picked_by ' + pick);
    if(sid) bits.push('会话 ' + sid);
    if(cm.skipped_self != null) bits.push('略过本问 ' + cm.skipped_self + ' 次');
    if(cm.path) bits.push('件 ' + cm.path);
    if(cm.reason) bits.push('因 ' + cm.reason);
    if(bits.length) e.push('context_meta：' + bits.join(' ／ '));
    return {u:L.join('\n'), e:e.join('\n')};
  }
  /* ⭐ pm_1073 §二.1 同族：拒答轮之顶栏收尾 —— 须在共用件 `send.js` 之 catch ／ finally **之后**跑
     （send.js:76 于 addMsg 之后置 'failed'；其 finally 只见 'failed' ⇒ ⛔ 扳）⇒ 唯此处（其外之包装）可收尾。 */
  function paSelfRefusalStatePass(){
    if(!paSelfRefusalDone) return;
    paSelfRefusalDone = false;
    try{ paSetState('done', '拒答已出（模型路不可达 · 读数见注记）', 'POST /v9/pa/ask'); }catch(e){}
  }
  window.sendPA = async function(text, t){
    const m = paSelfMetaAns; paSelfMetaAns = null;
    if(!m){ const r = await orig.apply(this, arguments); paSelfRefusalStatePass(); return r; }
    if(!paSelfMarks){ try{ await paSelfMarksLoad(); }catch(e){} }
    paSelfTagAt = '';   /* ⭐ 元问之刻已由「源：本会话 <刻>」行担 ⇒ ⛔ 分标再挂采样刻（免二处各表一刻） */
    const r = render(m);
    try{ paSetState('done', '元问已回答（后端会话路）', 'POST /v9/pa/ask'); }catch(e){}
    try{ addMsg('assistant', r.u, false, paSelfSayHtml(r.u, r.e), undefined); }catch(e){}
    try{
      const tt = (t && t.id) ? t : ((typeof activeThread === 'function') ? activeThread() : null);
      /* ⭐ pm 1184 §一.⒝：元问之答源取**后端原值**（`context` ⇒ 本会话有据 ／ `context_missing` ⇒ 闸拒）。 */
      if(tt && typeof recordPaTurn === 'function'){ paRun.receipt = await recordPaTurn(tt.id, text, r.u,
        (m && m.source === 'context') ? {origin:'grounded', grounded:true, answer_source:'context'}
        : (m && m.source === 'context_missing') ? {origin:'refused', grounded:false, answer_source:'context_missing'} : null); }
    }catch(e){}
    return r.u;
  };
})();

/* ================= 六 · 5 · 恢复态之「中断未记录」标（承 pm_1018 §二 ⓞ · 显示层）=================
   ⭐ 页面刷新 ／ 重载会打断在办之轮 ⇒ 存量回放后，末条若是「只有问 ／ 无答」之用户消息 ⇒
     该轮**未完成**且**未留中断痕** ⇒ 补一标（⛔ 留孤问无标）。
   ⚠ 在办中（paRun.busy）⛔ 标（那时「无答」是正常等答）丨⛔ 动存档（只改怎么显示）丨幂等：先撤旧标 ⇒ 再按现态重计 ⇒ 无变则⛔ 动 DOM（免观察器死循环）。 */
/* ⭐ pm_1045 §三 · 单源引用：远端三态之实体在 more.js（顶栏面 · 先载）⇒ 本件只引用（⛔ 二处各判 · 承 L83）。 */
function paRemTri(u){ try{ return (typeof paRemoteTri === 'function') ? paRemoteTri(u) : ''; }catch(e){ return ''; } }
function paRemText(u){ try{ return (typeof paRemoteText === 'function') ? paRemoteText(u) : '未知'; }catch(e){ return '未知'; } }
function paRemWhy(u){ try{ return (typeof paRemoteWhy === 'function') ? paRemoteWhy(u) : '未知'; }catch(e){ return '未知'; } }

function paSelfInterruptPass(){
  const t = document.getElementById('thread'); if(!t) return null;
  const ms = t.querySelectorAll('.msg');
  if(!ms.length) return {marked:0, orphan:false};
  const last = ms[ms.length-1];
  const isUser = !!(last.classList && last.classList.contains('user'));
  const want = isUser && !paSelfBusy();
  const cur = last.querySelector(':scope > .intr');
  if(want && !cur){
    const el = document.createElement('div');
    el.className = 'intr';
    el.style.cssText = 'margin-top:6px;font-size:12px;line-height:1.5;color:var(--amber,#f59e0b)';
    el.textContent = '⚠ 此问未完成 · 中断未记录 —— 页面刷新 ／ 重载打断了这一轮。可再发一次。';
    el.setAttribute('data-intr', '1');
    last.appendChild(el);
    return {marked:1, orphan:true};
  }
  if(!want){
    const all = t.querySelectorAll('.intr');
    for(let i=0;i<all.length;i++){ all[i].parentNode.removeChild(all[i]); }
  }
  return {marked:0, orphan:!!cur};
}
try{ window.paSelfInterruptPass = paSelfInterruptPass; }catch(e){}

/* ================= 六 · 6 · 占位答复（桩体）之净化（承 pm_1029 §二.② ／ pm_1030 §四）=================
   ⭐ 定位结论（我一手）：「（桩答）这是对话通道的答复」**不在产品树内**（全树 78,392 件 · 0 命中；data 目录 0 命中）。
   它是 **CW 自测桩之响应体**（e2e1020.cjs:104 ／ e2e1020b.cjs:54 ／ e2e1020c.cjs:23 ／ e2e1024s.cjs 之 fetch 桩）
   ⇒ 页面**如实渲染**⇒ **并入存档**（localStorage.pa_state 之 4 条 assistant 行）⇒ 每次回放都上屏。
   ⇒ 前端之责任：**对答复体做占位 ／ 空话校验**（⛔ 照单全收 · 承 L76）。
   形：用户面 ⇒ 一句「因＋法」（⛔ 出现「桩答」二字）；原文 ⇒ 入工程注记（⛔ 丢信息 ／ ⛔ 删账）。
   幂等：改后命中消失（data-stub 标记）⇒ 观察器自止。 */
function paSelfStubHit(s){
  const x = String(s == null ? '' : s);
  return /（桩答）|这是对话通道的答复|（桩）/.test(x);
}
function paSelfStubText(){
  return '⚠ 本轮没有可用答复：这条是**占位文本**（⛔ 不是模型的回答 · ⛔ 也不是本机素材）。'
    + '\n可：① 再发一次 ② 若本机模型未载 ⇒ 首次发问会触发载入（约 40 s · 载入后 5 分钟自卸）';
}
function paSelfStubPass(){
  const t = document.getElementById('thread'); if(!t) return 0;
  const els = t.querySelectorAll('.msg:not(.user)'); let n = 0;   /* 共用件 addMsg 之 assistant 行实为 `.msg`（无 `assistant` 类）⇒ 选 `.msg:not(.user)` */
  for(let i=0;i<els.length;i++){
    const el = els[i];
    if(el.getAttribute('data-stub') === '1') continue;
    const bx = el.querySelector('.bubble') || el;
    const raw = String(bx.textContent || '');
    if(!paSelfStubHit(raw)) continue;
    const kids = bx.childNodes;
    for(let k=kids.length-1;k>=0;k--){ const nd = kids[k];
      if(!(nd.nodeType === 1 && nd.tagName === 'DETAILS')) bx.removeChild(nd); }
    const p = document.createElement('div'); p.className = 'stubfix'; p.textContent = paSelfStubText();
    bx.insertBefore(p, bx.firstChild);
    bx.setAttribute('data-raw', raw);
    bx.appendChild(paEngNoteEl('原答复（占位 ／ 桩体 · 我一手取自本页存档）：\n' + raw));
    el.setAttribute('data-stub', '1'); n++;
  }
  return n;
}
try{ window.paSelfStubHit = paSelfStubHit; }catch(e){}
try{ window.paSelfStubPass = paSelfStubPass; }catch(e){}

/* ================= 六 · 7 · 冷启首问之「载入中」真状态（承 pm_1030 §二 令①）=================
   病：web/pa/faces/send.js:69 之 fetch(API+'/v9/pa/dialog') **无 signal ／ 无超时**（对比 :116 之 /v9/agent/chat 用 abortCtrl.signal）
     ⇒ 无界等待；而冷态（本机模型需现载 ≈ 37.2 s）下用户面只有状态行一句「等待 PA 模型回复」⇒ 像「静默丢」。
   解（⛔ 动共用件 send.js）：v3 侧包 window.sendPA ⇒ 于 #thread 内插一行**不入存档**之真状态行（已等 N s ＋ 因 ＋ 上限），落定即撤；超上限 ⇒ 转「因＋法」（⛔ 静默 · ⛔ 以忙代状态）。
   ⛔ 自动载模型：本行只报「本次请求会**触发**载入」（Ollama 于 generate 时自载）⇒ ⛔ 说成「我自动载了」。 */
let paSelfWaitBoundMs = 130000;
function paSelfWaitBoundSet(ms){ paSelfWaitBoundMs = Math.max(500, Number(ms) || 130000); return paSelfWaitBoundMs; }
function paSelfWaitRow(){
  const t = document.getElementById('thread'); if(!t) return null;
  const el = document.createElement('div');
  el.className = 'msg assistant selfwait'; el.setAttribute('data-wait', '1');
  el.innerHTML = '<div class="av">⏳</div><div><div class="meta">PA · 等待模型</div>'
    + '<div class="bubble"><div class="wsec"></div></div></div>';
  t.appendChild(el); t.scrollTop = t.scrollHeight;
  return el;
}
function paSelfWaitPaint(el, secs, over){
  if(!el || !el.parentNode) return;
  const box = el.querySelector('.wsec'); if(!box) return;
  const txt = over
    ? ('⚠ 等了 ' + secs + ' 秒仍无回复 —— 因：本机模型未载（首次载入约 40 s · 上限 ' + Math.round(paSelfWaitBoundMs/1000) + ' s）或后端未应答。'
       + '\n法：① 再等片刻（载入完成即出答） ② 看顶栏「本地在」确认模型在不在 ③ 需要时可请我载本机模型（默认 5 分钟后自卸 · 须你准 · ⛔ 我不会自动载）')
    : ('⏳ 已发问 · 等待本机模型回复 —— 已等 ' + secs + ' 秒'
       + '\n因：本次请求会**触发**本机模型载入（未载时首次约 40 s）；载入后 5 分钟自卸。上限 ' + Math.round(paSelfWaitBoundMs/1000) + ' s。');
  if(box.textContent !== txt) box.textContent = txt;
  el.setAttribute('data-wait-secs', String(secs));
  el.setAttribute('data-wait-over', over ? '1' : '0');
}
(function(){
  const inner = window.sendPA;
  if(typeof inner !== 'function') return;
  window.sendPA = async function(){
    const pr = paSelfWaitRow();
    const t0 = Date.now();
    let iv = null;
    if(pr){
      paSelfWaitPaint(pr, 0, false);
      iv = setInterval(function(){
        const secs = Math.round((Date.now() - t0) / 1000);
        paSelfWaitPaint(pr, secs, (Date.now() - t0) >= paSelfWaitBoundMs);
      }, 1000);
    }
    try{ return await inner.apply(this, arguments); }
    finally{
      if(iv) clearInterval(iv);
      try{ if(pr && pr.parentNode) pr.parentNode.removeChild(pr); }catch(e){}
    }
  };
})();
try{ window.paSelfWaitBoundSet = paSelfWaitBoundSet; }catch(e){}

/* ================= 七 · 面板随抽屉开而刷（首开才拉；⛔ 每次开都拉）================= */
(function(){
  const mv = window.paMore;
  if(typeof mv === 'function'){
    window.paMore = function(open){
      const r = mv.apply(this, arguments);
      if(open){
        try{ paEngCleanDrawer(); }catch(e){}
        try{ paPermRender(); }catch(e){}
        try{
          const b = document.getElementById('paAboutBody');
          if(b && !b.getAttribute('data-loaded')) paAboutLoad();
        }catch(e){}
      }
      return r;
    };
  }
  function go(){ try{ paSelfMulPass(); }catch(e){} try{ paEngCleanDrawer(); }catch(e){} try{ paPermRender(); }catch(e){} try{ paSelfTestTracePass(); }catch(e){} try{ paSelfInterruptPass(); }catch(e){} try{ paSelfStubPass(); }catch(e){} if(!paSelfUiCache){ try{ paSelfJson('pa/ui_state.json').then(function(u){ if(u) paSelfUiCache = u; }); }catch(e){} } }
  if(document.readyState === 'loading'){ document.addEventListener('DOMContentLoaded', go); } else { go(); }
  setTimeout(go, 900); setTimeout(go, 3200);
})();

/* ⭐ 运行记录注记之补扫（承 pm_1013 · 显示层）：`#thread` 之变更即扫（防存档回放绕过包装）。
   只在「有命中」时改 DOM ⇒ 改后不再命中 ⇒ 观察器自止（⛔ 死循环）。 */
(function(){
  let tid = null;
  function run(){ tid = null; try{ paSelfMulPass(); }catch(e){} try{ paEngCleanThread(); }catch(e){} try{ paSelfTestTracePass(); }catch(e){} try{ paSelfInterruptPass(); }catch(e){} try{ paSelfStubPass(); }catch(e){} }
  function boot(){
    const t = document.getElementById('thread'); if(!t) return;
    try{ new MutationObserver(function(){ if(tid) return; tid = setTimeout(run, 150); })
          .observe(t, {childList:true, subtree:true, characterData:true}); }catch(e){}
    run();
  }
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
  window.addEventListener('load', function(){ setTimeout(boot, 800); });
})();

/* ⭐ 画像面板「状态 ＋ 来源指印」（承 pm_1099 §三.3 · P12/P13 之我面 · 承 pm_1092 §五.1）。
   profile.js 系甲类（本令未解除）⇒ 不改；本件**包装** window.renderSide：原渲染之后，
   以 /v9/pa/profile 之**全量生效条目**（含 status=proposed）重渲 #profileCards，逐条附
   [状态] ＋ 来源指印 ⇒ 使「哪些还没确认」可见（承 L76：状态／来源取后端回执，⛔ 前端自说）。 */
(function(){
  var PA_ST_LABEL = { confirmed:"已确认", proposed:"待确认", revised:"已修正", deprecated:"已弃" };
  var PA_ST_COLOR = { confirmed:"#3fb950", proposed:"#d29922", revised:"#8b949e", deprecated:"#8b949e" };
  var PA_DOM_LABEL = { decision:"决策", aesthetic:"审美", emotion:"情感", style:"风格", lesson:"教训", fact:"事实", product:"产品", channel:"通道" };
  var PA_DOM_ORDER = { decision:0, emotion:1, aesthetic:2, style:3, lesson:4, fact:5, product:6, channel:7 };
  function paStEsc(x){ return String(x == null ? "" : x).replace(/[&<>"]/g, function(c){
      return ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;" })[c]; }); }
  function paRenderProfileStatus(){
    var pc = document.getElementById("profileCards"); if(!pc) return;
    /* ⭐ pm_1105 §一.1：起窗卡**优先** —— 本路（`GET /v9/pa/profile`）⛔ 覆盖之。
       由（桩页实证 · 本件之真冲突）：起窗时 `GET /v9/pa/context` 败 ⇒ 本线器画「启动中 ／ 真故障」卡；
       而本函数只取 `/v9/pa/profile` ⇒ **该路未必同败** ⇒ 一取到即 `pc.innerHTML=""` 重渲 ⇒ **旧 12 卡盖掉起窗卡**
       ⇒ 用户读不到「重连中」（⛔ 用户可见之谎：看上去「已就绪」）。故：`data-pa-ctx` 已置者一律让位。
       （`data-pa-ctx` 唯本线之起窗卡所置；试成之正渲路径 ⛔ 置它 ⇒ 正路不受影响。） */
    if(pc.getAttribute("data-pa-ctx")) return;
    fetch(API + "/v9/pa/profile?user_id=" + encodeURIComponent(curUser()))
      .then(function(r){ return r.ok ? r.json() : null; })
      .then(function(j){
        if(!j || !j.ok || !Array.isArray(j.entries)) return;      /* 读不到 ⇒ 保留原渲染（⛔ 清空） */
        var list = j.entries.slice().sort(function(a, b){
          var x = PA_DOM_ORDER[a.domain], y = PA_DOM_ORDER[b.domain];
          return (x == null ? 9 : x) - (y == null ? 9 : y); });
        pc.setAttribute("data-pa-status", "1");
        pc.innerHTML = "";
        list.forEach(function(e){
          var div = document.createElement("div");
          div.className = "card" + (e.domain === "emotion" ? " emotion" : "");
          div.setAttribute("data-entry-id", e.id || "");
          div.setAttribute("data-entry-status", e.status || "");
          div.innerHTML = "<div class=\"k\">" + paStEsc(PA_DOM_LABEL[e.domain] || e.domain)
            + "<span class=\"pa-st\" style=\"float:right;font-size:10px;font-weight:400;color:" + (PA_ST_COLOR[e.status] || "#8b949e") + "\">"
            + paStEsc(PA_ST_LABEL[e.status] || e.status || "?") + "</span></div>"
            + paStEsc(e.value || "")
            + "<div style=\"color:#6e7681;font-size:10.5px;margin-top:3px\">[" + paStEsc(e.confidence || "") + "] " + paStEsc(e.date || "") + "</div>"
            + "<div class=\"pa-src\" style=\"color:#6e7681;font-size:10.5px;margin-top:2px\">来源：" + paStEsc(e.source || "—")
            + (e.supersedes ? " · 替 " + paStEsc(e.supersedes) : "") + "</div>";
          pc.appendChild(div);
        });
      })
      .catch(function(){});
  }
  function paHookProfileStatus(){
    if(typeof window.renderSide === "function" && !window.renderSide.__paStatusWrap){
      var orig = window.renderSide;
      var wrapped = function(){ var r = orig.apply(this, arguments); try{ paRenderProfileStatus(); }catch(e){} return r; };
      wrapped.__paStatusWrap = 1;
      window.renderSide = wrapped;
    }
  }
  function paProfileStatusGo(){ paHookProfileStatus(); try{ paRenderProfileStatus(); }catch(e){} }
  if(document.readyState === "loading"){ document.addEventListener("DOMContentLoaded", paProfileStatusGo); }
  else { paProfileStatusGo(); }
  setTimeout(paProfileStatusGo, 1000); setTimeout(paProfileStatusGo, 3300);
})();

/* ⭐ 场合拨杆「陪伴 ／ 办事」（承 pm_1100 §三 · 后端 P7 之**单源** · ⛔ 动共用件）。
   背景：后端 `PA_MODE_CLAUSE` 按显式 `mode` 组装系统提示（`core\pa\gateway_routes.py:44`），
   缺省 ⇒ `work`。故前端**必须**给出唯一来源，否则「陪伴 ／ 办事」无源可依。
   ⛔ 动 send.js（共用件）⇒ 本件以**包装 `window.fetch`** 把 `mode` 注入 `POST /v9/pa/dialog` 之体
   （承本线既有手法：`paAskGate` 之包装 · `/v9/pa/ask` 回 `refused` ⇒ 转 dialog）。
   ⭐ 四要件（令 §三）：⒈ 屏上可见此刻哪档（本栏常驻 composer 之顶）⒉ 值透传体之 `mode`
   ⒊ 回执之 `mode` ⟷ 拨杆值**须一致**（⛔ 不一致即谎 ⇒ 屏上显「✓／⚠」成对）
   ⒋ 读数取**后端回执**（承 L76 · ⛔ 前端自说）。 */
(function(){
  var KEY = "pa_chat_mode";
  var VAL = { companion: { label:"陪伴", hint:"自然口语 · 陪着说" },
              work:      { label:"办事", hint:"结论先行 · 给建议" } };
  var cur = null;                       /* 本地缓存（无会话时之退路 · 默认 companion） */
  var last = null;                      /* 最近一轮**后端回执**之归一 mode（null ＝ 尚无） */
  var lastReq = null;                   /* 该轮请求所用之 mode（与 last 对账 ⇒ ✓／⚠） */
  var lastHits = null;                  /* 该轮回执 route.label_hits（数组 ∨ null） */
  var lastAt = '';                      /* 该轮回执之刻（本机） */
  var stat = { rounds:0, hits:{} };     /* 本页会话累计 · 逐标签（承 L186） */
  var THREE = ["\u7ed3\u8bba\uff1a", "\u9ed8\u8ba4\u9879\uff1a", "\u53ef\u9009\u9879\uff1a"];
  function norm(v){
    v = String(v == null ? "" : v).trim().toLowerCase();
    if(VAL[v]) return v;
    if(v === "陪伴") return "companion";
    if(v === "办事") return "work";
    return null;
  }
  function readL(){ try{ var v = norm(localStorage.getItem(KEY)); return v || null; }catch(e){ return null; } }
  function saveL(v){ try{ localStorage.setItem(KEY, v); }catch(e){} }
  /* ⭐ pm_1107 §一裁2（准修 · 一行）：⚠ `activeThread()` **带副作用** —— `session.js:381`
     `if(!state.threads.length) newThread(true)` ⇒ 而 `boot.js:9` 之 `await loadThreads()` **未完成前**
     `state.threads` 尚空 ⇒ 此处一调即 ⭐ **建新会话**（且 `newThread` 内 `saveState()` 落盘）
     ⇒ 其后 `loadThreads()` 读到之本地态**已是新号** ⇒ ⭐ **每次载入新会话**（老板所说「记不住」之根）。
     **实证**（`pm_1106 §四.3` · `Debugger` 断点取栈）：`go → mount → paint → paChatMode → eff → threadMode → AT`
     ⇒ `activeThread`（`session.js:381`）⇒ `newThread`（`:413`）。
     ⇒ 故：**表空 ⇒ ⛔ 调之**（返 `null` ⇒ 上层回落 `localStorage`）。载入期本无会话可读；
     `loadThreads()` 落定后 `state.threads` 非空 ⇒ ⭐ **正路一字不动**。 */
  function AT(){
    try{
      if(typeof activeThread !== "function") return null;
      if(typeof state === "undefined" || !state || !(state.threads || []).length) return null;
      return activeThread();
    }catch(e){ return null; }
  }
  function threadMode(){ var t = AT(); return norm(t && t.paMode); }
  /* ⭐ pm_1102 §二.1：档 ＝ **会话属性** —— 会话自存优先 ⇒ 否则**继承上次**（localStorage）
     ⇒ 否则默认 `companion`（老板令「聊天 ＝ 陪伴」）。⛔ 后端之判（`pa_mode_name` 仍归一之唯一）。 */
  function eff(){ return threadMode() || readL() || "companion"; }
  window.paChatMode = function(){ return eff(); };
  window.paChatModeLastReceipt = function(){ return last; };
  window.paSetChatMode = function(v){
    v = norm(v); if(!v) return;
    var t = AT(); if(t) t.paMode = v;             /* ⭐ 会话属性（随会话 · 入 localStorage.pa_state） */
    cur = v; saveL(v);                             /* ⭐ 继承源（新会话承上次） */
    try{ if(typeof saveState === "function") saveState(); }catch(e){}
    paint();
  };
  /* ⭐ pm_1102 §二.3：诊断读数（供「更多 ▾ · 关于 PA」诊断区 · ⛔ 常驻用户面） */
  window.paChatModeDiag = function(){
    var t = AT();
    return { mode: eff(), modeLabel: VAL[eff()].label,
             sessionId: (t && t.id) ? String(t.id) : null,
             threadStored: !!threadMode(), globalStored: readL(),
             receiptMode: last, receiptModeLabel: last ? VAL[last].label : null,
             requestedMode: lastReq, same: last ? (lastReq === last) : null,
             labelHits: lastHits, rounds: stat.rounds, hitsByLabel: stat.hits, at: lastAt };
  };

  function paint(){
    var v = window.paChatMode();
    [["paModeBtnCompanion","companion"],["paModeBtnWork","work"]].forEach(function(pr){
      var b = document.getElementById(pr[0]); if(!b) return;
      var on = (pr[1] === v);
      b.style.background = on ? "#1f6feb" : "transparent";
      b.style.color      = on ? "#0d1117" : "#8b949e";
      b.style.borderColor= on ? "#1f6feb" : "#30363d";
      b.setAttribute("data-on", on ? "1" : "0");
    });
    var h = document.getElementById("paModeHintText");
    if(h) h.textContent = "· " + VAL[v].hint;
    var sEl = document.getElementById("paModeSession");
    if(sEl){
      var _t = AT();
      sEl.textContent = "会话 " + ((_t && _t.id) ? String(_t.id) : "—") + "（" + (threadMode() ? "自存" : "继承") + "）";
    }
    try{ document.documentElement.setAttribute("data-pa-chat-mode", v); }catch(e){}
  }
  function paintReceipt(backRaw, reqRaw, hits, requested){
    last = norm(backRaw);
    lastReq = norm(requested) || norm(reqRaw);
    lastAt = new Date().toLocaleTimeString('zh-CN', {hour12:false});
    lastHits = (hits == null) ? null : (Array.isArray(hits) ? hits.slice(0) : hits);
    /* ⭐ 本页累计 · 逐标签（承 L186：⛔ 以一族之一员概全族）—— ⛔ 混入用户面（诊断用） */
    if(last != null || lastHits != null){
      stat.rounds++;
      THREE.forEach(function(k){
        if(lastHits && typeof lastHits.indexOf === 'function' && lastHits.indexOf(k) >= 0){
          stat.hits[k] = (stat.hits[k] || 0) + 1;
        }
      });
    }
    var el = document.getElementById("paModeReceipt"); if(!el) return;
    var req = lastReq;
    if(!last){
      el.textContent = "回执 mode：—（后端未给）";
      el.style.color = "#6e7681";
      el.title = "本轮后端回执里没有可识别之 mode ⇒ ⛔ 前端自说（承 L76）";
      return;
    }
    var same = (req === last);
    el.textContent = (same ? "✓ " : "⚠ ") + "回执 mode：" + VAL[last].label
      + (same ? "（与拨杆同）" : " ≠ 拨杆「" + (req ? VAL[req].label : "?") + "」");
    el.style.color = same ? "#3fb950" : "#d29922";
    el.title = (same ? "后端回执之 mode 与拨杆值一致（成对之证）"
                     : "⚠ 后端回执之 mode 与拨杆值**不一致** ⇒ 视同谎（承 pm_1100 §三 要件 3）")
      + " ｜ route.label_hits（诊断 · 逐标签）："
      + THREE.map(function(k){
          return k + ((lastHits && typeof lastHits.indexOf === 'function' && lastHits.indexOf(k) >= 0) ? "命中" : "未中");
        }).join(" ／ ");
  }
  function btn(id, label){
    return '<button id="' + id + '" data-pa-mode="' + (id === "paModeBtnCompanion" ? "companion" : "work") + '"'
      + ' style="cursor:pointer;border-radius:7px;padding:2px 10px;font-size:11px;font-weight:700;'
      + 'height:auto;line-height:1.6;background:transparent;color:#8b949e;border:1px solid #30363d">'
      + label + "</button>";
  }
  function mount(){
    var c = document.querySelector(".composer"); if(!c) return;
    if(document.getElementById("paModeBar")) { paint(); return; }
    var bar = document.createElement("div");
    bar.id = "paModeBar";
    bar.setAttribute("data-src", "pm_1100 §三 · 场合拨杆（selfdesc.js 包装 · ⛔ 动共用件）");
    bar.style.cssText = "display:flex;align-items:center;gap:6px;margin:0 0 7px;font-size:11px;color:#6e7681;flex-wrap:wrap";
    bar.innerHTML = '<span style="color:#8b949e">场合</span>'
      + btn("paModeBtnCompanion", "陪伴") + btn("paModeBtnWork", "办事")
      + '<span id="paModeHintText" style="color:#6e7681"></span>'
      + '<span id="paModeSession" style="color:#6e7681"></span>'
      + '<span id="paModeReceipt" style="margin-left:auto;color:#6e7681">回执 mode：—（尚未有本轮）</span>';
    c.insertBefore(bar, c.firstChild);
    Array.prototype.forEach.call(bar.querySelectorAll("button[data-pa-mode]"), function(b){
      b.addEventListener("click", function(){ window.paSetChatMode(b.getAttribute("data-pa-mode")); });
    });
    paint();
  }
  /* ⭐ 透传：POST /v9/pa/dialog 之体补 `mode`（仅当体未自带 ⇒ 幂等 · ⛔ 覆盖后端/他件所给） */
  function wrapFetch(){
    if(typeof window.fetch !== "function" || window.fetch.__paModeWrap) return;
    var _of = window.fetch;
    var f = function(u, o){
      var url = String((u && u.url) ? u.url : u);
      var m = String((o && o.method) || "GET").toUpperCase();
      if(m === "POST" && url.indexOf("/v9/pa/dialog") >= 0 && o && typeof o.body === "string"){
        var reqMode = null, o2 = o;
        try{
          var b = JSON.parse(o.body);
          if(b && typeof b === "object" && b.mode === undefined){
            reqMode = window.paChatMode(); b.mode = reqMode;
            o2 = {}; for(var k in o){ if(Object.prototype.hasOwnProperty.call(o, k)) o2[k] = o[k]; }
            o2.body = JSON.stringify(b);
          } else if(b && b.mode !== undefined){ reqMode = norm(b.mode) || String(b.mode); }
        }catch(e){}
        var p = _of.call(this, u, o2);
        if(reqMode){
          try{
            p.then(function(r){
              try{ if(r && typeof r.clone === "function"){
                r.clone().json().then(function(j){
                  paintReceipt(j && j.mode, reqMode,
                               (j && j.route && j.route.label_hits) ? j.route.label_hits : null, reqMode);
                }).catch(function(){});
              } }catch(e){}
            }).catch(function(){});
          }catch(e){}
        }
        return p;
      }
      return _of.apply(this, arguments);
    };
    f.__paModeWrap = 1;
    window.fetch = f;
  }
  /* ⭐ pm_1102 §二.1：切会话 ⇒ 拨杆随之。切线程之钩子在共用件 `chat.js:36`
     （`state.activeThread=…; renderThreads(); …`）⇒ ⛔ 动共用件 ⇒ **包装 `window.renderThreads`**
     （切线程必跑它）⇒ 其后重绘拨杆（承本线包装手法：`paAskGate` ／ `paAboutLoad`）。
     并包装 `newThread` ⇒ 新会话**继承上次**档（源 ＝ localStorage.pa_chat_mode）。 */
  function wrapThreadHooks(){
    if(typeof window.renderThreads === "function" && !window.renderThreads.__paModeWrap){
      var _rt = window.renderThreads;
      var rt = function(){ var r = _rt.apply(this, arguments); try{ paint(); }catch(e){} return r; };
      rt.__paModeWrap = 1; window.renderThreads = rt;
    }
    if(typeof window.newThread === "function" && !window.newThread.__paModeWrap){
      var _nt = window.newThread;
      var nt = function(){
        var t = _nt.apply(this, arguments);
        try{
          var l = readL();
          if(t && norm(t.paMode) === null && l){
            t.paMode = l;
            try{ if(typeof saveState === "function") saveState(); }catch(e){}
          }
          paint();
        }catch(e){}
        return t;
      };
      nt.__paModeWrap = 1; window.newThread = nt;
    }
  }
  function go(){ wrapFetch(); wrapThreadHooks(); mount(); }
  if(document.readyState === "loading"){ document.addEventListener("DOMContentLoaded", go); } else { go(); }
  setTimeout(go, 1000); setTimeout(go, 3300); setTimeout(go, 6000);
})();

/* ⭐ pm_1105 §一.1（准改）：起窗用户面 ——「启动中 ／ 正在重连」⟷「真故障」须**可辨**
   （承 1104 §四 之现态面：`profile.js:7-15` 四因同坠一卡 · 无超时 · ⛔ 重试）。
   手法：**包装 `window.loadSide`**（⛔ 动共用件 `profile.js`）—— 唯**取数**（重试 ＋ 超时）归本件，
   **渲染仍归** `renderSide`（⛔ 复制其渲染逻辑）。
   ⒈ 试 `GET /v9/pa/context`，单次超时 `6 s`（`AbortController`）· 败 ⇒ `1 s` 后退避重试，共 `3` 试。
   ⒉ 试成 ⇒ `renderSide(d)` 正渲 ∧ ⛔ 上屏任何卡（＝验收态 ⒜）。
   ⒊ 试尽 ⇒ ⭐ **两段并标**之卡 ＋ **带刻**（重试刻 ／ 已试次 ／ 最后成功刻）：
      网络类（抛 ／ 超时）⇒「**启动中 ／ 正在重连**（刚起服约需 40–60 s）」为主 ＋ 次段「若持续 ⇒ 真故障」；
      HTTP 状态类（如 `500`）⇒「**真故障**（后端答 N）」为主 ＋ 次段「若刚起服 ⇒ 或亦为起窗」。
   ⚠ **上界（承 `pm_1107 §一裁1` 之改）**：`pm_1105` 之「`3` 试 ⇒ 上界 `20 s`」**不足覆盖冷启**
   （技术总监实测 `37.306 s`）⇒ 裁为 ⭐ **两段 · 上界 ≥ `45 s`**：
   ⒜ **前 `20 s` 静默重试**（⛔ 上屏 —— 此刻多半只是冷启）｜⒝ **后 `25 s` 出起窗卡 ＋ 持续重试**
      （成 ⇒ 换 `12` 卡）。`45 s` 之后 ⇒ ⛔ 停，唯将退避拉长（`1 s ⇒ 5 s`）**续试**（仍可自愈 ⇒ ⛔ 再须手刷）。 */
(function(){
  var QUIET_MS = 20000;      /* 前段：静默（⛔ 上屏） */
  var TOTAL_MS = 45000;      /* 上界：此后退避拉长（仍续试 ⇒ 成即换 `12` 卡） */
  var GAP_MS = 1000;         /* 试间隔 */
  var GAP_LONG_MS = 5000;    /* 上界后之退避（⭐ 封顶 ⇒ 承 `pm_1109 §一裁1`：「退避封顶 `5 s` ⇒ 已符」） */
  var TIMEOUT_MS = 6000;     /* 单次超时 */
  var LATE_MS = 120000;      /* ⭐ `pm_1109 §一裁1⒝`：逾 `2 min` 仍败 ⇒ 卡上追「可能是真故障」 */
  var lastOkAt = "";
  function nowHMS(){ try{ return new Date().toLocaleTimeString("zh-CN", {hour12:false}); }catch(e){ return ""; } }
  function e2(x){ return String(x == null ? "" : x).replace(/[&<>"]/g, function(c){
      return ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;" })[c]; }); }
  function sleep(ms){ return new Promise(function(res){ setTimeout(res, ms); }); }
  /* 一次试 ⇒ 归一为 {kind:'ok'|'net'|'status'|'body', data?, status?}（⛔ 抛） */
  function fetchOnce(){
    var ctl = (typeof AbortController === "function") ? new AbortController() : null;
    var timer = null;
    if(ctl){ timer = setTimeout(function(){ try{ ctl.abort(); }catch(e){} }, TIMEOUT_MS); }
    var opt = ctl ? { signal: ctl.signal } : undefined;
    function done(v){ if(timer){ clearTimeout(timer); timer = null; } return v; }
    return fetch(API + "/v9/pa/context?user_id=" + encodeURIComponent(curUser()), opt).then(function(r){
      if(!r || !r.ok) return done({ kind:"status", status:(r && r.status) || 0 });
      return r.json().then(function(j){
        return done((j && j.ok) ? { kind:"ok", data:j } : { kind:"body", status:r.status });
      }, function(){ return done({ kind:"body", status:r.status }); });
    }, function(err){
      return done({ kind:"net", err:String((err && err.name) || err) });
    });
  }
  /* ⭐ `pm_1109 §一裁1`（两守）：⒜ 卡带 ⭐ **已等秒数 ＋ 下次重试秒数**（⛔ 静默轮转 —— 用户须看得见
     「仍在试 ∧ 隔多久再试」）｜⒝ 逾 `LATE_MS`（`2 min`）仍败 ⇒ 追一句「**可能是真故障**（看顶栏 ／ 更多）」。
     ⚠ 由：不硬止（`pm_1109` 准）之代价 ＝ 用户可能「等而不觉」⇒ 故须**把等化作可读之数**（承 `L76` 真源上屏）。 */
  function paintCard(kind, tries, status, waitedMs, nextGapMs){
    var pc = document.getElementById("profileCards"); if(!pc) return;
    var fault = (kind === "status");
    var waited = Math.round((waitedMs || 0) / 1000);
    var nxt = Math.round((nextGapMs || 0) / 1000);
    var primary = fault
      ? ("真故障：后端答 " + e2(status) + "（⛔ 起窗所致）")
      : "启动中 ／ 正在重连（刚起服约需 40–60 s）";
    var second = fault
      ? "若刚起服（约 40–60 s）⇒ 或亦为起窗 ⇒ 稍后重试；持续如此 ⇒ 须人管"
      : "若持续如此（远超 40–60 s）⇒ 真故障（须人管）";
    var late = (waitedMs >= LATE_MS)
      ? ('<div style="color:#d29922;font-size:10.5px;margin-top:2px">⏱ 已等逾 2 min 仍连不上 ⇒ '
         + '可能是真故障（看顶栏 ／ 更多）</div>')
      : "";
    pc.setAttribute("data-pa-ctx", fault ? "fault" : "reconnecting");
    pc.innerHTML = '<div class="card" style="color:var(--sub)">' + primary
      + '<div style="color:#6e7681;font-size:10.5px;margin-top:3px">已等 ' + e2(waited) + ' s ｜ 已试 '
      + e2(tries) + ' 次 ｜ 下次重试 ~' + e2(nxt) + ' s ｜ 最后成功刻 ' + e2(lastOkAt || "本页尚未成功")
      + ' ｜ 此卡刻 ' + e2(nowHMS()) + '</div>'
      + '<div style="color:#8b949e;font-size:10.5px;margin-top:2px">' + second
      + '｜真源：GET /v9/pa/context（重试由本机包装 · ⛔ 后端未接）</div>'
      + late + '</div>';
    var tc = document.getElementById("todoCards");
    if(tc && String(tc.textContent || "").indexOf("\u8d26\u672c\u672a\u52a0\u8f7d") >= 0){
      tc.innerHTML = '<div class="card todo" style="color:var(--sub)">'
        + (fault ? ("账本：真故障（后端 " + e2(status) + "）") : "账本：启动中 ／ 正在重连")
        + '<div style="color:#6e7681;font-size:10.5px;margin-top:3px">已等 ' + e2(waited) + ' s ｜ 下次重试 ~'
        + e2(nxt) + ' s ｜ 刻 ' + e2(nowHMS()) + '</div></div>';
    }
  }
  function go(){
    if(typeof window.loadSide !== "function" || window.loadSide.__paCtxRetryWrap) return;
    var wrapped = async function(){
      try{ var u = document.getElementById("uidText"); if(u) u.textContent = curUser(); }catch(e){}
      var kind = "net", status = 0, tries = 0, painted = false, t0 = Date.now();
      for(;;){
        tries += 1;
        var v = await fetchOnce();
        if(v.kind === "ok"){
          lastOkAt = nowHMS();
          /* ⭐ 后段成 ⇒ **让位卡退回**（摘 `data-pa-ctx` ⇒ `paRenderProfileStatus` 之让位闸随之放行）
             ⇒ 其后 `renderSide` 之正渲即可画出 `12` 卡（承 `pm_1107 §一裁1⒝`）。 */
          if(painted){ try{ var pc = document.getElementById("profileCards"); if(pc) pc.removeAttribute("data-pa-ctx"); }catch(e){} }
          try{ renderSide(v.data); }catch(e){}
          return;
        }
        kind = v.kind; status = v.status || 0;
        var el = Date.now() - t0;
        var gap = (el < TOTAL_MS) ? GAP_MS : GAP_LONG_MS;
        /* ⒜ 前段静默（⛔ 上屏）｜⒝ `QUIET_MS` 一到 ⇒ 出卡 ∧ 此后**逐试刷新**
           （**已等** ／ 次数 ／ **下次重试** ⇒ 逐值皆出 · 承 `pm_1109 §一裁1⒜`）。 */
        if(el >= QUIET_MS){ paintCard(kind, tries, status, el, gap); painted = true; }
        await sleep(gap);
      }
    };
    wrapped.__paCtxRetryWrap = 1;
    window.loadSide = wrapped;
  }
  /* ⭐ 装钩**须先于 `boot.js`**（⛔ 靠 DOMContentLoaded 之赛跑）：`boot.js:46` 作
     `PA_FACES.guard("profile", loadSide)` ⇒ 而 `core.js:22` 之 guard 系**取值即绑**
     （`return fn.apply(null, arguments)`）⇒ 我之包装若未及装，boot 持**原件** ⇒ **起窗重试根本不跑**。
     桩页实证（同一份代码 · 两次跑）：A4 成（`data-pa-ctx=reconnecting`）／A2 败（真页仍出旧文案
     「画像未加载（/v9/pa/context 无响应）。」∧ `data-pa-ctx` 恒 `null`）⇒ ⭐ **赛跑之证**。
     本件（`selfdesc.js` ＝ 第 `21` 个 `<script>`）**解析先于** `boot.js`（第 `22`）⇒ 此处**同步装钩** ⇒ 恒先。 */
  try{ go(); }catch(e){}
  if(document.readyState === "loading"){ document.addEventListener("DOMContentLoaded", go); } else { go(); }
  setTimeout(go, 800); setTimeout(go, 2500); setTimeout(go, 5000);
  /* 供报数（⛔ 用户面）：重试之界与最后成功刻 */
  try{ window.paCtxRetryInfo = function(){ return { quietMs:QUIET_MS, totalMs:TOTAL_MS, gapMs:GAP_MS,
      gapLongMs:GAP_LONG_MS, timeoutMs:TIMEOUT_MS, firstCardAtMs:QUIET_MS, lastOkAt:lastOkAt }; }; }catch(e){}
})();

/* ================= 六 · 7 · 会话历史（真源清单 · 点开即续）（承 pm_1111 §二 之裁 1 · 技总 989 之新面）=================
   面 ＝ `GET /v9/pa/sessions`（薄别名）⇒ `{ok, store, sessions:[{session_id, lines, bytes, mtime, path, lines_readable}]}`
   ⭐ 真源之裁（承 pm_1109 附）：历史之真源 ＝ **盘上** `data\v9\pa\sessions\*.jsonl`（append-only）
     ⟷ ⛔ 页面态镜像 `threads_web_*.json` 之 `archived`（易失快照）⇒ 本清单取自前者的薄别名（⛔ 从镜像取）。
   「续」＝ 取该会话之历史（`GET /v9/pa/dialog?session_id=<sid>&n=<N>` 之 `history`）⇒ 落到本页线程
     （`state.activeThread` ＋ `th.msgs`）⇒ 调**既有** `renderThread()` 重渲 ⇒ 此后之新问即续写该会话
     （`/v9/pa/dialog` 与 `recordPaTurn` 皆带 `session_id` · 承 L83 单源出口）。
   ⚠ 唯**读 ＋ 切换**：⛔ 删 ／ ⛔ 改盘上件 ／ ⛔ 动共用件（chat.js ／ session.js 一字未动 —— 只调其既有全局函数）。 */
(function(){
  const PANEL_ID = 'paMoreGrpHist';
  const LIST_ID = 'paHistList';
  function hEsc(s){ return String(s == null ? '' : s).replace(/[&<>"]/g, function(c){ return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]; }); }
  function fmtTime(s){ const t = String(s || ''); return t.length >= 16 ? t.slice(5, 16) : t; }
  async function rows(){
    try{ const r = await fetch(API + '/v9/pa/sessions', {cache:'no-store'}); const d = await r.json();
      return (d && d.ok && Array.isArray(d.sessions)) ? d.sessions : null; }catch(e){ return null; }
  }
  /* 点开即续：真源取历史 ⇒ 落本页线程 ⇒ 重渲（⛔ 另造渲染 · ⛔ 自造键 —— 径皆既有出口） */
  async function resume(sid){
    const s = String(sid || ''); if(!s) return {ok:false, why:'无 session_id'};
    const r = await fetch(API + '/v9/pa/dialog?session_id=' + encodeURIComponent(s) + '&n=60', {cache:'no-store'});
    const d = await r.json();
    const hist = (d && Array.isArray(d.history)) ? d.history : [];
    if(!hist.length) return {ok:false, why:'该会话无可读之行（空会话 ／ 后端未回）', n:0};
    let t = null; try{ t = state.threads.find(function(x){ return x.id === s; }); }catch(e){}
    if(!t){ t = {id:s, title:'（真源）' + s, mode:'chat', msgs:[]}; try{ state.threads.push(t); }catch(e){} }
    /* ⭐ pm 1184 §一.⒞：**档行源标随行渲出**（会话视图 ＝ 档读者所据之处）——
       真源 ＝ 行自身之 `origin`（⛔ 前端自算 ／ ⛔ 预设 `src`）；以 `html` 交付 ⇒ 绕开本件 addMsg 包装之
       「呈现改写」支（其唯对 `!html` 者生效）⇒ 旧档原文照渲。 */
    t.msgs = hist.map(function(m){
      const role = (String(m.role) === 'user') ? 'user' : 'assistant';
      const txt = String(m.text == null ? '' : m.text);
      if(role !== 'assistant'){ return {role:role, content:txt}; }
      const _bg = paSelfOriginBadgeHtml(m);
      return _bg ? {role:role, content:txt, html:_bg + hEsc(txt)} : {role:role, content:txt};
    });
    try{ state.activeThread = s; }catch(e){}
    try{ if(typeof saveState === 'function') saveState(); }catch(e){}
    try{ if(typeof syncPaSession === 'function') syncPaSession(); }catch(e){}
    try{ if(typeof renderThread === 'function') renderThread(); }catch(e){}
    return {ok:true, n:hist.length};
  }
  async function paint(){
    const body = document.getElementById('paMoreBody'); if(!body) return 'no-host';
    let box = document.getElementById(PANEL_ID);
    if(!box){
      box = document.createElement('details');
      box.className = 'mgrp'; box.id = PANEL_ID;
      box.innerHTML = '<summary>④ 续 · 会话历史（真源：盘上 <code>data\\v9\\pa\\sessions</code> · ⛔ 页态镜像）'
        + '<button id="paHistReload" style="margin-left:6px;font-size:11px">↻ 刷新</button></summary>'
        + '<div id="' + LIST_ID + '" style="padding:6px 1px;font-size:12px;line-height:1.75">…</div>';
      body.appendChild(box);
      const rb = box.querySelector('#paHistReload');
      if(rb) rb.addEventListener('click', function(ev){ ev.preventDefault(); ev.stopPropagation(); paint(); });
      box.addEventListener('click', function(ev){
        const el = (ev.target && ev.target.closest) ? ev.target.closest('[data-resume]') : null;
        if(!el) return;
        ev.preventDefault(); ev.stopPropagation();
        const sid = el.getAttribute('data-resume');
        const st = document.getElementById(LIST_ID);
        resume(sid).then(function(r2){
          try{ if(typeof addLog === 'function') addLog(r2.ok
            ? ('📂 已续：' + sid + '（真源取 ' + r2.n + ' 行 ⇒ 此后新问续写该会话）')
            : ('⚠ 未续：' + sid + '（' + r2.why + '）'), r2.ok ? 'ok' : 'warn', true, '会话历史（真源）'); }catch(e){}
          if(st) st.setAttribute('data-last', (r2.ok ? 'ok:' : 'fail:') + sid);
        });
      });
    }
    const listEl = document.getElementById(LIST_ID); if(!listEl) return 'no-list';
    const rs = await rows();
    if(!rs){ listEl.innerHTML = '<span style="color:var(--amber,#f59e0b)">⚠ 取不到真源清单（GET /v9/pa/sessions 未回 ／ 起窗中）—— 可点 ↻ 再试</span>'; return 'no-data'; }
    listEl.innerHTML = rs.map(function(x){
      const sid = String(x.session_id || '');
      const mark = /^pa_selftest/.test(sid) ? ' <span data-axis="probe" style="color:#8b949e">（自测痕 · ⛔ 真实使用）</span>' : '';
      return '<div style="display:flex;gap:6px;align-items:baseline">'
        + '<button data-resume="' + hEsc(sid) + '" style="font-size:11px">续</button>'
        + '<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + hEsc(sid) + mark + '</span>'
        + '<span style="color:#8b949e;font-size:11px">' + (x.lines == null ? '—' : x.lines) + ' 行 · ' + hEsc(fmtTime(x.mtime)) + '</span></div>';
    }).join('') || '<span style="color:#8b949e">（0 件）</span>';
    return 'ok:' + rs.length;
  }
  try{ window.paHistPaint = paint; }catch(e){}
  try{ window.paHistResume = resume; }catch(e){}
  function go(){ try{ paint(); }catch(e){} }
  try{ if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', go); else go(); }catch(e){}
  setTimeout(go, 1200); setTimeout(go, 3000);
  try{ document.addEventListener('click', function(ev){ const t2 = ev.target; if(t2 && t2.id === 'paMoreBtn'){ setTimeout(go, 60); } }, true); }catch(e){}
  /* 供报数（⛔ 用户面）：清单之面与行数 */
  try{ window.paHistInfo = function(){ const b = document.getElementById(PANEL_ID); const l = document.getElementById(LIST_ID);
    return { panel: !!b, rows: l ? l.querySelectorAll('[data-resume]').length : -1, last: l ? l.getAttribute('data-last') : null,
             at: (typeof activeThread === 'function' && activeThread()) ? activeThread().id : null,
             src: API + '/v9/pa/sessions' }; }; }catch(e){}
})();

/* ================= 七 · PA-4 人话回执 ＋ PA-3 停手卡（承 pm_1115 · 唯本件 · ⛔ 动共用件）=================
   ⭐ pm_1115 §序：先 PA-4（可查账）⇒ 再 PA-3（停手）｜两件皆以**包装**落（承本线手法 · ⛔ 动共用件）。
   ⛔ 一字不动：send.js ／ cards.js ／ archive.js ／ products.js ／ status.js ／ pa.html（唯本件 = selfdesc.js）。 */
(function(){
  var SRC = 'pm_1115 §一／§二（本件包装 · ⛔ 动共用件）';
  function Q(id){ try{ return document.getElementById(id); }catch(e){ return null; } }
  function H(s){ return String(s == null ? '' : s).replace(/[&<>"]/g, function(c){ return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]; }); }
  function p2(n){ n = String(n); return n.length >= 2 ? n : ('0' + n); }
  function nowStr(){
    try{ var d = new Date();
      return d.getFullYear() + '-' + p2(d.getMonth()+1) + '-' + p2(d.getDate()) + ' ' + p2(d.getHours()) + ':' + p2(d.getMinutes()) + ':' + p2(d.getSeconds()); }
    catch(e){ return '\u2014'; }
  }
  function modeName(){
    try{ var m = (typeof state !== 'undefined' && state) ? String(state.mode || '') : '';
      var c = (typeof MODES !== 'undefined' && MODES[m]) ? MODES[m] : null;
      return { key:m, label:(c ? String(c.label || m) : (m || '\u2014')), chan:(c ? String(c.chan || '') : '') }; }
    catch(e){ return { key:'', label:'\u2014', chan:'' }; }
  }
  function srcOf(){ try{ return (typeof paRunSrc === 'string' && paRunSrc) ? String(paRunSrc) : '\u2014\uff08\u5c1a\u672a\u6536\u5230\u540e\u7aef\u4e8b\u4ef6\uff09'; }catch(e){ return '\u2014'; } }
  function rcOf(){ try{ return (typeof paRun === 'object' && paRun && paRun.receipt) ? paRun.receipt : null; }catch(e){ return null; } }

  /* ---------- 7.1 主面回执区：#tlReceipt **移**主面（承 pm_1115 §一.3 · ⛔ 两存）---------- */
  var HOST_ID = 'paReceiptMain';
  function ensureHost(){
    var chat = Q('paFaceChat'); if(!chat) return null;
    var host = Q(HOST_ID);
    if(!host){
      host = document.createElement('div');
      host.id = HOST_ID;
      host.setAttribute('data-src', SRC);
      host.style.cssText = 'margin:0 0 7px';
      var hr = document.createElement('div');
      hr.id = 'paHumanReceipt';
      hr.style.cssText = 'font-size:12px;line-height:1.7;color:#8b949e;border:1px solid #30363d;border-radius:7px;padding:6px 10px;background:#0d1117';
      hr.textContent = '\u56de\u6267\uff1a\u672c\u8f6e\u5c1a\u672a\u6709\u8bb0\u5f55\u3002';
      host.appendChild(hr);
      var th = Q('thread');
      if(th && th.parentNode === chat){ chat.insertBefore(host, th); } else { chat.appendChild(host); }
    }
    var tr = Q('tlReceipt');
    if(tr && tr.parentNode !== host){ host.appendChild(tr); }   /* ⭐ DOM 移 ⇒ 一处（⛔ 复制 · ⛔ 两存） */
    return host;
  }

  /* ---------- 7.2 人话回执合成器（由既有出口合成 · ⛔ 另造子系统 · 承 pm_1115 §一.1）---------- */
  function lastLogs(n){
    try{ var els = document.querySelectorAll('#thread .tool-log'); var out = [];
      for(var i = Math.max(0, els.length - (n || 12)); i < els.length; i++){ out.push(String(els[i].textContent || '').replace(/\s+/g, ' ').trim()); }
      return out; }catch(e){ return []; }
  }
  function pickLog(re){ var a = lastLogs(14); for(var i = a.length - 1; i >= 0; i--){ if(re.test(a[i])) return a[i]; } return ''; }
  function judgeText(){
    try{ var els = document.querySelectorAll('#thread .msg .bubble');
      for(var i = els.length - 1; i >= 0 && i >= els.length - 6; i--){
        var m = String(els[i].textContent || '').match(/\u5224\u636e\s*\/v9\/pa\/ask[^\n]{0,140}/); if(m) return m[0];
      } }catch(e){}
    return '';
  }
  function costText(){
    var rc = rcOf();
    if(rc && typeof rc === 'object'){
      var got = [];
      ['wall_s','elapsed_s','bytes','tokens','cost_cny'].forEach(function(k){ if(rc[k] != null) got.push(k + '=' + rc[k]); });
      if(got.length) return got.join(' \u00b7 ');
    }
    return '\u672a\u53d6\u5f97\uff08\u5019\u540e\u7aef\u8865 wall_s \uff0f bytes \uff0f tokens \u00b7 \u627f pm_1115 \u00a7\u4e00.1 \u21d2 \u524d\u7aef \u26d4 \u4f30\u7b97\uff09';
  }
  function whoText(){
    var l = pickLog(/\u5df2\u786e\u8ba4\u5199\u5165\uff08/);
    if(l){ var m = l.match(/\u5df2\u786e\u8ba4\u5199\u5165\uff08(.+?)\uff09/);
      return '\u8001\u677f \u00b7 \u9009\u9879\u300c' + (m ? m[1] : '\u2014') + '\u300d \u00b7 \u523b ' + nowStr() + '\uff08\u540e\u7aef\u56de\u6267 \u00b7 \u627f pm_1115 \u00a7\u4e8c.5\uff09'; }
    if(pickLog(/\u5df2\u62d2\u7edd\u5199\u5165/)) return '\u8001\u677f \u00b7 \u5df2\u62d2\u7edd\uff08\u26d4 \u672a\u5199\u5165\uff09';
    var wr = pickLog(/\u7b49\u5f85\u6388\u6743\uff1a/);
    if(wr) return '\u23f3 \u5f85\u8001\u677f\u62cd\u677f\uff08' + wr.replace(/^.*\u7b49\u5f85\u6388\u6743\uff1a/, '') + '\uff09';
    return '\u672a\u6d89\u53ca\uff08\u672c\u8f6e\u65e0\u5199\u5165\u6388\u6743\uff09';
  }
  function receiptText(){ var tr = Q('tlReceipt'); return tr ? String(tr.textContent || '').trim() : ''; }
  function rcLines(){
    var rt = receiptText();
    var log = pickLog(/^[\u25b6\u2705\u274c\u26d4\u23f3\ud83d\udca1\ud83d\udccb\u23f9\ud83d\udc64\ud83d\udcbe\ud83e\uddf9\ud83d\udd0d]/);
    var did = srcOf() + (log ? (' \uff5c ' + log) : '') + (rt ? (' \uff5c ' + rt) : '');
    var tail = '\u672c\u8f6e\u5df2\u7ed3\u675f\uff08\u7ec6\u8282\u89c1\u300c\u5de5\u7a0b\u6ce8\u8bb0\u300d\uff09';
    if(pickLog(/\u7b49\u5f85\u6388\u6743\uff1a/) || pickLog(/\u5f85\u4f60\u88c1/) || pickLog(/\u5f85\u62cd\u677f/)) tail = '\u7b49\u4f60\u62cd\u677f\u540e\u7ee7\u7eed';
    else if(pickLog(/^\u274c|\u4efb\u52a1\u4e2d\u65ad|\u672a\u843d\u76d8\u8bfb\u6570\u4e0d\u53ef\u5f97/)) tail = '\u53ef\u91cd\u8bd5 \uff0f \u5148\u770b\u5de5\u7a0b\u6ce8\u8bb0';
    /* ⭐ pm_刀11p §零：本轮回执合成器若引「那件」之行（⚙ T1 交付回执）⇒ 抽其**件之刻**上屏（⛔ 只报「本轮」刻）。 */
    var piece = null;
    try{
      var pl = pickLog(/\u4ef6\u4e4b\u523b/);
      var pm2 = pl ? pl.match(/\u4ef6\u4e4b\u523b\s*([0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2})/) : null;
      piece = pm2 ? pm2[1] : null;
    }catch(e){ piece = null; }
    return [
      '\u00b7 \u505a\u4e86\u4ec0\u4e48\uff1a' + did,
      '\u00b7 \u51ed\u4ec0\u4e48\uff1a' + (judgeText() || '\u672a\u53d6\u5f97\uff08\u672c\u8f6e\u65e0\u77e5\u8bc6\u68c0\u7d22\u4e4b\u636e \u00b7 \u26d4 \u524d\u7aef\u4e0d\u7f16\uff09'),
      '\u00b7 \u82b1\u4e86\u591a\u5c11\uff1a' + costText()
        + (piece ? ('\uff08本轮 \u00b7 那件\uff08' + piece + '\uff09\u4e4b\u4ee3\u4ef7\u89c1\u300c结\u8bba\u300d\u884c \u00b7 \u5c5e那件\uff09') : ''),
      '\u00b7 \u8c01\u6279\u7684\uff1a' + whoText(),
      '\u00b7 \u7ed3\u8bba\uff1a' + (rt || log || did.slice(0, 80)),
      '\u00b7 \u4e0b\u4e00\u6b65\uff1a' + tail
    ];
  }
  function rcRefresh(){
    var host = ensureHost(); if(!host) return;
    var hr = Q('paHumanReceipt'); if(!hr) return;
    var _piece = null;
    try{
      var _pl = pickLog(/\u4ef6\u4e4b\u523b/);
      var _pm = _pl ? _pl.match(/\u4ef6\u4e4b\u523b\s*([0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2})/) : null;
      _piece = _pm ? _pm[1] : null;
    }catch(e){ _piece = null; }
    hr.textContent = '\ud83d\udccb \u672c\u8f6e\u56de\u6267\uff08\u4eba\u8bdd\u7248 \u00b7 \u672c\u8f6e\u8bfb\u6570\u523b ' + nowStr()
      + (_piece ? (' \uff5c \u7ed3\u8bba\u6240\u5f15\u4e4b\u4ef6\u4e4b\u523b ' + _piece) : ' \uff5c \u672c\u8f6e\u65e0\u4ef6\u4e4b\u523b')
      + '\uff09\n' + rcLines().join('\n');
    hr.title = '\u672c\u5757\u7531\u65e2\u6709\u56de\u6267\u884c\u5408\u6210\uff08\u26d4 \u53e6\u9020\u5b50\u7cfb\u7edf\uff09\u00b7 \u771f\u6e90\uff1a\u8d70\u5f84\u6807 \uff0f \u540e\u7aef\u56de\u6267 \uff0f \u4f1a\u8bdd\u65e5\u5fd7\uff5c' + SRC;
  }

  /* ---------- 7.3 内部读数 ⇒ 工程注记（用户面改人话 · 承 pm_1115 §一.2）---------- */
  var LEDGER_RE = /\u672c\u8f6e\u5df2\u843d\u76d8\uff08/;
  function ledgerPass(){
    try{
      var els = document.querySelectorAll('#thread .tool-log');
      for(var i = 0; i < els.length; i++){
        var el = els[i]; if(el.__paLedgerHuman) continue;
        var raw = String(el.getAttribute('data-raw') || el.textContent || '');
        if(!LEDGER_RE.test(raw)) continue;
        el.__paLedgerHuman = 1;
        var n = (el.dataset && el.dataset.n && el.dataset.n !== '1') ? ('   \u00d7' + el.dataset.n) : '';
        el.textContent = '\u2705 \u672c\u8f6e\u5df2\u5b58\u6863' + n;
        el.setAttribute('data-pa-user', '\u2705 \u672c\u8f6e\u5df2\u5b58\u6863');
        var d = document.createElement('details');
        d.className = 'eng';
        d.innerHTML = '<summary>\u5de5\u7a0b\u6ce8\u8bb0</summary><div class="engbody"></div>';
        d.querySelector('.engbody').textContent = raw + '\n\uff08\u771f\u6e90\uff1a\u540e\u7aef POST /v9/pa/turn \u56de\u6267 \u00b7 \u26d4 \u7528\u6237\u9762\uff09';
        el.appendChild(d);
      }
    }catch(e){}
  }

  /* ---------- 7.4 PA-3 停手卡：approval 卡升级（承 pm_1115 §二.1／§二.2）---------- */
  /* ⭐ pm_1117 §一.1：可撤销性改「二段文案」（按**动作之时相**）——
     ⓜ 事前（未批）：未批即未动 ⇒ 此刻反悔 ＝ 什么都不发生（此即真「可撤」）
     ⓝ 事后（已批）：不可撤销（已出手）｜唯可再发更正 ∨ 撤回之路径：<逐字 · 无则「无」>
     ⛔ 「revoke_window 恒不出现」非缺实现 ⇒ 是缺**按时相**之文案（⛔ 留一个永不出现之格）。
     ⭐ 乙／丙 档（改规矩 ／ 可回改）之撤为**真** ⇒ 准接 hold：后端若给
       revoke_window（show===true ∧ 秒数可读）⇒ 照显倒计时（⛔ 本地递减）。 */
  function undoPath(src, extra){
    try{
      if(extra && extra.undo) return String(extra.undo);
      var t = String(((src && src.tool) || '') + ' ' + ((src && src.target) || ''));
      if(/permission|grants|profile\.json|档|授权|权限|画像/.test(t))
        return '同面板回改（改权限档 ⇒ 再提交一次 ／ 授权 ⇒ 点「撤销授权」）';
      return '无';
    }catch(e){ return '无'; }
  }
  function revText(src, extra, phase){
    var rw = src && src.revoke_window;
    var win = (rw && rw.show === true && rw.seconds_left != null) ? String(rw.seconds_left) : null;
    if(phase === 'after'){
      if(win != null) return '已出手 · 后端撤销窗仍在：剩余 ' + win + ' 秒（后端快照 · ⛔ 本地递减）';
      return '不可撤销（已出手）｜唯可再发更正 ∨ 撤回之路径：' + undoPath(src, extra);
    }
    if(win != null) return '未批即未动（后端撤销窗已开：剩余 ' + win + ' 秒 · 后端快照）';
    return '未批即未动 —— 此刻反悔 ＝ 什么都不发生';
  }
  function stopCardEnrich(card, src, extra){
    if(!card || card.querySelector('.pa-stopx')) return;
    try{ card.__paSrc = src; }catch(e){}
    var rel = ['approve','always','reject'].filter(function(a){ return (src && Array.isArray(src.decisions)) ? src.decisions.indexOf(a) >= 0 : true; });
    var box = document.createElement('div');
    box.className = 'pa-stopx';
    box.setAttribute('data-src', SRC);
    box.style.cssText = 'margin-top:6px;font-size:11.5px;line-height:1.75;color:#8b949e;border-top:1px dashed #30363d;padding-top:5px';
    var rows = [
      ['\u505a\u4ec0\u4e48', (src && (src.target || src.command || src.path)) ? String(src.target || src.command || src.path).slice(0, 200) : '\u672a\u8bb0\u5f55'],
      ['\u901a\u9053', (extra && extra.channel) ? String(extra.channel) : (srcOf() + '\uff08\u672c\u8f6e\u8d70\u5f84 \u00b7 \u771f\u6e90\uff09')],
      ['\u4ee3\u4ef7', (extra && extra.cost) ? String(extra.cost) : '\u672a\u8bb0\u5f55\uff08\u540e\u7aef\u672a\u7ed9\uff1a\u94b1 \uff0f \u65f6 \uff0f \u52a8\u8c01\u7684\u7269\uff09'],
      ['\u53ef\u64a4\u9500\u6027', revText(src, extra, 'before')],
      ['\u6388\u6743\u4e4b\u6c42', '\u987b\u300c\u8001\u677f\u300d\u4eb2\u6279\uff08\u70b9\u4e0b\u4e09\u94ae\u4e4b\u4e00\uff1a' + rel.join(' \uff0f ') + '\uff09\uff1b\u7f3a \u21d2 \u505c\uff08\u26d4 \u4ee3\u586b \u00b7 \u627f authz.js:108\uff09'],
      ['\u523b', nowStr()]
    ];
    box.innerHTML = rows.map(function(r){ return '<div><b>' + H(r[0]) + '</b>\uff1a' + H(r[1]) + '</div>'; }).join('');
    card.appendChild(box);
  }
  var origCard = window.paRenderCard;
  if(typeof origCard === 'function'){
    var w = function(kind, payload, host){
      if(kind !== 'approval') return origCard.apply(this, arguments);
      var src = {}, extra = {};
      if(payload && typeof payload === 'object'){
        Object.keys(payload).forEach(function(k){ if(k.indexOf('pa_') === 0){ extra[k.slice(3)] = payload[k]; } else { src[k] = payload[k]; } });
      }
      var card = origCard.call(this, kind, src, host);
      try{ if(card) stopCardEnrich(card, src, extra); }catch(e){}
      return card;
    };
    w.__paWrap = 1; window.paRenderCard = w;
  }

  /* ---------- 7.5 停手卡之共用面（固定浮层 · 一屏之内 · 承 pm_1115 §二）---------- */
  function stopAsk(o){
    var id = 'paStopAsk';
    var old = Q(id); if(old && old.parentNode) old.parentNode.removeChild(old);
    var box = document.createElement('div');
    box.id = id;
    box.setAttribute('data-src', SRC);
    box.style.cssText = 'position:fixed;left:50%;transform:translateX(-50%);bottom:16px;z-index:9999;max-width:min(720px,92vw);'
      + 'background:#161b22;border:1px solid #d29922;border-radius:10px;box-shadow:0 8px 30px rgba(0,0,0,.5);'
      + 'padding:10px 14px;font-size:12.5px;line-height:1.8;color:#c9d1d9';
    var rows = (o.rows || []).map(function(r){ return '<div><b>' + H(r[0]) + '</b>\uff1a' + H(r[1]) + '</div>'; }).join('');
    var btns = '<button id="' + id + 'Ok" style="font-weight:700">' + H(o.okLabel || '\u786e\u8ba4') + '</button>';
    if(o.alwaysLabel) btns += '<button id="' + id + 'Al">' + H(o.alwaysLabel) + '</button>';
    btns += '<button id="' + id + 'No">' + H(o.cancelLabel || '\u53d6\u6d88') + '</button>';
    box.innerHTML = '<div style="font-weight:700;color:#d29922;margin-bottom:4px">' + H(o.title || '\u505c\u624b') + '</div>'
      + '<div>' + rows + '</div>'
      + '<div style="margin-top:8px;display:flex;gap:8px;justify-content:flex-end">' + btns + '</div>';
    document.body.appendChild(box);
    var done = false;
    function close(){ try{ if(box.parentNode) box.parentNode.removeChild(box); }catch(e){} }
    function act(kind, fn, msg, cls){
      if(done) return; done = true; close();
      try{ if(fn) fn(); }catch(e){}
      try{ if(typeof addLog === 'function') addLog(msg + '：' + (o.title || ''), cls, o.persistMsg === false ? false : true, SRC); }catch(e){}
    }
    Q(id + 'Ok').addEventListener('click', function(){ act('ok', o.onOk, '\ud83d\udc64 \u5df2\u6279\u51c6\uff08\u505c\u624b\u5361\uff09', 'ok'); });
    if(o.alwaysLabel) Q(id + 'Al').addEventListener('click', function(){ act('always', o.onAlways || o.onOk, '\ud83d\udc64 \u5df2\u6279\u51c6\uff08\u505c\u624b\u5361 \u00b7 \u672c\u4f1a\u8bdd\u4e00\u76f4\u5141\u8bb8\uff09', 'ok'); });
    Q(id + 'No').addEventListener('click', function(){ act('no', o.onCancel, '\u21a9 \u5df2\u53d6\u6d88\uff08\u505c\u624b\u5361\uff09', 'warn'); });
    return box;
  }
  try{ window.paStopAsk = stopAsk; }catch(e){}

  /* ---------- 7.6 A5：删除 ⇒ 停手卡（替 window.confirm · 承 pm_1115 §二.4）---------- */
  var origCleanup = window.paArchiveCleanup;
  var _cleaning = false;
  if(typeof origCleanup === 'function'){
    var w = function(){
      if(_cleaning) return origCleanup.apply(this, arguments);
      var st = null; try{ st = (typeof paArchiveStats === 'function') ? paArchiveStats() : null; }catch(e){ st = null; }
      if(!st || !st.total) return origCleanup.apply(this, arguments);   /* \u65e0\u53ef\u6e05\u7406 \u21d2 \u8d70\u539f\u4ef6\uff08\u5176\u81ea\u62a5 0 \u6761\uff09 */
      var self = this, args = arguments;
      stopAsk({
        title: '\u26d4 \u505c\u624b\uff1a\u624b\u52a8\u6e05\u7406\u5f52\u6863\uff08\u4e0d\u53ef\u64a4\u9500\uff09',
        rows: [
          ['\u505a\u4ec0\u4e48', '\u5220\u9664\u672c\u673a\u5f52\u6863\u4e2d\u6700\u65e9\u7684 ' + st.remove + ' \u6761\uff08\u5f52\u6863\u5171 ' + st.total + ' \u6761 \u00b7 \u5220\u540e\u4fdd\u7559 ' + (st.keep || 0) + ' \u6761\uff09'],
          ['\u901a\u9053', '\u672c\u673a localStorage\uff08\u26d4 \u4e0d\u7ecf\u7f51\u7edc\uff09'],
          ['\u4ee3\u4ef7', '\u94b1 0 \u00b7 \u65f6 \u5373\u65f6 \u00b7 \u52a8\u8c01\u7684\u7269\uff1a\u4f60\u672c\u673a\u4e4b\u5f52\u6863\uff08' + st.remove + ' \u6761\uff09'],
          ['\u53ef\u64a4\u9500\u6027', '\u26d4 \u4e0d\u53ef\u64a4\u9500\uff08\u5220\u5373\u5931 \u00b7 \u552f\u53ef\u5148\u300c\u5bfc\u51fa\u5f52\u6863 JSON\u300d\u5907\u4efd\uff09'],
          ['\u6388\u6743\u4e4b\u6c42', '\u987b\u300c\u8001\u677f\u300d\u4eb2\u6279\uff1b\u7f3a \u21d2 \u505c'],
          ['\u523b', nowStr()]
        ],
        okLabel: '\ud83e\uddf9 \u786e\u8ba4\u5220\u9664',
        cancelLabel: '\u274c \u53d6\u6d88',
        onOk: function(){
          _cleaning = true;
          var oc = window.confirm, swapped = false;
          try{ if(/\[native code\]/.test(String(oc))){ window.confirm = function(){ return true; }; swapped = true; } }catch(e){}
          try{ return origCleanup.apply(self, args); }
          finally{ try{ if(swapped) window.confirm = oc; }catch(e){} _cleaning = false; }
        }
      });
      return false;
    };
    w.__paWrap = 1; window.paArchiveCleanup = w;
  }

  /* ---------- 7.7 A1：执行通道 ⇒ 停手卡（唯「出手」路 · 承 pm_1115 §二.4）---------- */
  var origSendAgent = window.sendAgent;
  var agentGrant = null;   /* null = \u672a\u6279 \uff0f 'once' \uff0f 'session' */
  if(typeof origSendAgent === 'function'){
    var w = function(){
      var mdl = modeName();
      if(mdl.chan !== 'agent') return origSendAgent.apply(this, arguments);
      if(agentGrant === 'session') return origSendAgent.apply(this, arguments);
      if(agentGrant === 'once'){ agentGrant = null; return origSendAgent.apply(this, arguments); }
      var self = this, args = arguments;
      return new Promise(function(resolve, reject){
        stopAsk({
          title: '\u26d4 \u505c\u624b\uff1a\u5373\u5c06\u300c\u51fa\u624b\u300d\uff08\u6267\u884c\u901a\u9053\uff09',
          rows: [
            ['\u505a\u4ec0\u4e48', '\u628a\u672c\u8f6e\u4ea4\u529e\u7ed9\u6267\u884c\u5faa\u73af\uff08' + mdl.label + '\u6863 \u21d2 \u4f1a\u8c03\u5de5\u5177\u52a8\u624b\uff09'],
            ['\u901a\u9053', srcOf() + '\uff08\u771f\u6e90\u8d70\u5f84\uff09\u00b7 \u573a\u5408\uff1a' + mdl.label],
            ['\u4ee3\u4ef7', '\u672a\u8bb0\u5f55\uff08\u540e\u7aef\u672a\u7ed9\uff1a\u94b1 \uff0f \u65f6 \uff0f \u52a8\u8c01\u7684\u7269\uff09'],
            ['\u53ef\u64a4\u9500\u6027', '\u672a\u8bb0\u5f55 \u2014\u2014 \u6267\u884c\u4e2d\u552f\u53ef\u70b9\u300c\u505c\u6b62\u300d\uff08POST /v9/cancel \u00b7 \u4f1a\u8bdd\u7ea7 \u00b7 \u4e0b\u4e00\u6b65\u8fb9\u754c\u751f\u6548\uff09'],
            ['\u6388\u6743\u4e4b\u6c42', '\u987b\u300c\u8001\u677f\u300d\u4eb2\u6279\uff1b\u7f3a \u21d2 \u505c\uff08\u672c\u5361\u5373\u662f\uff09'],
            ['\u523b', nowStr()]
          ],
          okLabel: '\u2705 \u672c\u6b21\u6267\u884c',
          alwaysLabel: '\u267e\ufe0f \u672c\u4f1a\u8bdd\u4e00\u76f4\u5141\u8bb8',
          cancelLabel: '\u274c \u53d6\u6d88',
          onOk: function(){ agentGrant = 'once'; try{ resolve(origSendAgent.apply(self, args)); }catch(e){ reject(e); } },
          onAlways: function(){ agentGrant = 'session'; try{ resolve(origSendAgent.apply(self, args)); }catch(e){ reject(e); } },
          onCancel: function(){
            try{ if(typeof setBusy === 'function') setBusy(false);
                 if(typeof paSetState === 'function') paSetState('stopped', '\u8001\u677f\u53d6\u6d88\uff08\u505c\u624b\u5361 \u00b7 \u26d4 \u672a\u51fa\u624b\uff09'); }catch(e){}
            resolve(undefined);
          }
        });
      });
    };
    w.__paWrap = 1; window.sendAgent = w;
  }

  /* ---------- 7.8 挂载 ＋ 观察（⛔ 动共用件 ⇒ 唯观察 ＋ 重放）---------- */
  function pass(){ try{ ledgerPass(); }catch(e){} try{ rcRefresh(); }catch(e){} }
  function hook(){
    ensureHost(); pass();
    try{
      var th = Q('thread');
      if(th && !th.__paObs){
        th.__paObs = new MutationObserver(function(){ pass(); });
        th.__paObs.observe(th, {childList:true, subtree:true, characterData:true});
      }
      var chat = Q('paFaceChat');
      if(chat && !chat.__paObs2){
        chat.__paObs2 = new MutationObserver(function(){ try{ ensureHost(); }catch(e){} });
        chat.__paObs2.observe(chat, {childList:true});
      }
      var tr = Q('tlReceipt');
      if(tr && !tr.__paObs){
        tr.__paObs = new MutationObserver(function(){ try{ rcRefresh(); }catch(e){} });
        tr.__paObs.observe(tr, {childList:true, characterData:true, subtree:true});
      }
    }catch(e){}
    try{
      if(typeof window.receipt === 'function' && !window.receipt.__paWrap){
        var o = window.receipt;
        var wr = function(){ var r = o.apply(this, arguments); try{ rcRefresh(); }catch(e){} return r; };
        wr.__paWrap = 1; window.receipt = wr;
      }
    }catch(e){}
  }
  try{ if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', hook); else hook(); }catch(e){}
  setTimeout(hook, 900); setTimeout(hook, 2600); setTimeout(hook, 5200);
  try{ document.addEventListener('click', function(ev){ var t2 = ev.target; if(t2 && t2.id === 'paMoreBtn'){ setTimeout(hook, 60); } }, true); }catch(e){}

  /* 供报数（⛔ 用户面）：本件之面与包裹态 */
  try{ window.paRcInfo = function(){
    var tr = Q('tlReceipt');
    return { host: !!Q(HOST_ID), human: !!Q('paHumanReceipt'),
      tlReceiptParent: (tr && tr.parentNode) ? String(tr.parentNode.id || tr.parentNode.className || '') : 'none',
      tlReceiptVisible: !!(tr && tr.style && tr.style.display !== 'none'),
      ledgerRewritten: document.querySelectorAll('#thread .tool-log[data-pa-user]').length,
      cardWrapped: !!window.paRenderCard.__paWrap, cleanupWrapped: !!window.paArchiveCleanup.__paWrap,
      agentWrapped: !!window.sendAgent.__paWrap, grant: agentGrant,
      src: srcOf(), mode: modeName().key, chan: modeName().chan, at: nowStr() }; }; }catch(e){}
  /* ---------- 7.6b 乙档：改档 ／ 改授权 ⇒ 留痕（谁 ／ 刻 ／ 改了什么档 · 承 pm_1115 §二.4 ／ §二.5）---------- */
  ;[['paPermGrant','授权'],['paPermRevoke','撤销授权'],['paPermSetLevel','改权限档']].forEach(function(pair){
    var name = pair[0], label = pair[1];
    var o = window[name];
    if(typeof o !== 'function' || o.__paWrap) return;
    var w = function(){
      var args = arguments, detail = '';
      try{
        if(name === 'paPermSetLevel'){ var e = Q('ppLevel'); detail = '\u6863=' + String((args[0] != null ? args[0] : (e ? e.value : '')) || '\u2014'); }
        else if(name === 'paPermGrant'){ var f = args[0] || ((typeof paPermReadForm === 'function') ? paPermReadForm() : null);
          detail = 'path=' + String((f && f.path) || '\u2014') + ' \u00b7 ttl=' + String((f && f.ttl_s) || '\u2014'); }
      }catch(e){}
      var say = function(outcome){ try{ if(typeof addLog === 'function') addLog('\ud83d\udcdd \u7559\u75d5\uff1a' + label + (detail ? ('\uff08' + detail + '\uff09') : '') + ' \u00b7 ' + outcome + ' \u00b7 \u523b ' + nowStr(), outcome === '\u5df2\u751f\u6548' ? 'ok' : 'warn', true, SRC); }catch(e2){} };
      var r;
      try{ r = o.apply(this, args); }
      catch(err){ say('\u26a0 \u629b\u9519\uff08\u672a\u751f\u6548\uff09'); throw err; }
      try{ Promise.resolve(r).then(function(res){ say((res && res.ok === false) ? '\u26a0 \u672a\u751f\u6548' : '\u5df2\u751f\u6548'); },
                                  function(){ say('\u26a0 \u672a\u53d6\u5f97\u56de\u6267'); }); }catch(e3){}
      return r;
    };
    w.__paWrap = 1; window[name] = w;
  });
  try{ document.addEventListener('DOMContentLoaded', function(){ try{ hook(); }catch(e){} }); }catch(e){}

  /* ---------- 7.6c ⭐ pm_1117 §一.1：可撤销性之**事后**段（时相之另一半）----------
     ⓝ 事后（已批）：不可撤销（已出手）｜唯可再发更正 ∨ 撤回之路径：<逐字 · 无则「无」>
     承 7.4 之二段：卡上（未批）＝ ⓜ；此处（已批）＝ 事后之面 ⇒ 落**回执行**（⛔ 改卡体 · ⛔ 动 cards.js）。
     ⚠ 包装须幂等（__paWrap）；其调用点为按名取（cards.js:126）⇒ 包装可被见。 */
  var origDecide = window.paWriteDecide;
  if(typeof origDecide === 'function' && !origDecide.__paWrap){
    var wdec = function(id, action, card){
      var r = origDecide.apply(this, arguments);
      try{
        if(action === 'approve' || action === 'always'){
          var src = {}; try{ src = (card && card.__paSrc) || {}; }catch(e){}
          addLog('↩ 可撤销性（事后 · ' + (action === 'always' ? '一直允许' : '仅本次') + '）：'
                 + revText(src, {}, 'after'), 'warn', true, SRC);
        }
      }catch(e){}
      return r;
    };
    wdec.__paWrap = 1; window.paWriteDecide = wdec;
  }
})();

/* ================= 八 · T1 交付面（承 pm_071 ／ pm_070 §三 · 唯本件 · ⛔ 动共用件）=================
   pm_070 §三 之判据：① 交办 ⇒ 计划上屏（与 POST /v9/pa/plan 同源）② 停手卡（授权点必停）
     ④ 回执上屏（四件 ＋ 人话 · 读数取后端）⑥ 失败回执上屏（停在哪一步 ＋ 报给谁）。
   pm_071 之三硬条：一 弱保证须自标「弱」（⛔ 以弱充强）｜二 task_id 须由「交办 ＋ 收件人 ＋ 正文散列」
     复算（⛔ 随机 ／ ⛔ 时间戳 ／ ⛔ 前端自增）｜三 面上须显「停手收件人」（明写字段 · 默认 本人）。
   接口（PM 定形 · pm_071 §四）：POST /v9/pa/deliver/mail
     · 体 ＝ {user_id, task_id, decision_id, to:[…], subject, body_md}
     · 缺 decision_id ∨ 其 ⛔ 在 decision_log ⇒ 403 fail-closed｜重放同 task_id ⇒ 返既有回执
   ⭐ 后端**已接**（GET ⇒ 405 ⇒ 径已接 · pm_072 §一）⇒ 判据 ④／⑥ 皆可走**实调级**（⛔ 桩）：
     ④ 以真 decision ＋ self-addressed 真发；⑥ 以第三人 ∨ 错 decision_id 真打 ⇒ 403。
   ⭐ 回执四件取**后端**（receipt['人话'] ∨ 结构化中文键）—— ⛔ 前端自说（承 pm_1115 §一.1）。
   ⭐ pm_073 §一：探针 ／ 自测 ⇒ **⛔ 入 msgs**（经 API 所驱者之 `say` 传 `false`）；⚠ pm_073 §三：`stop_to` 唯面有真值方传（T1.1）。
   ⛔ 不动 web/pa.html（pm_071 §七 界：唯 web/pa/faces/*.js）⇒ 面板由本件**自挂载**。 */
(function(){
  var SRC = 'pm_071 §一／§二 ＋ pm_072 §一 ＋ pm_073 §一／§三 ＋ pm_刀11p ＋ pm_刀15p ／ 刀15p-补 ／ 刀16p（四件填满 · 件之刻 · 报给谁取 deliver/stop · $/件 · 引哪封来信 · 人工步数 · 本件 ⛔ 动共用件）';
  var PANEL = 'paT1Panel';
  var ID = { task:'paT1Task', body:'paT1Body', to:'paT1To', subject:'paT1Subject', stop:'paT1StopTo',
             echo:'paT1StopToEcho', back:'paT1Backend', tid:'paT1Tid',
             refNo:'paT1RefNo', refSha:'paT1RefSha', onestep:'paT1OneStep', steps:'paT1Steps',
             dec:'paT1Decision', decSrc:'paT1DecSrc',
             plan:'paT1Plan', rc:'paT1Receipt', out:'paT1Out' };
  function Q(i){ try{ return document.getElementById(i); }catch(e){ return null; } }
  function H(s){ return String(s == null ? '' : s).replace(/[&<>"]/g, function(c){
    return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]; }); }
  function p2(n){ n = String(n); return n.length >= 2 ? n : ('0' + n); }
  function nowStr(){
    try{ var d = new Date();
      return d.getFullYear() + '-' + p2(d.getMonth()+1) + '-' + p2(d.getDate()) + ' '
           + p2(d.getHours()) + ':' + p2(d.getMinutes()) + ':' + p2(d.getSeconds()); }
    catch(e){ return '\u2014'; } }
  function uid(){ try{ return (typeof curUser === 'function') ? String(curUser()) : 'default'; }catch(e){ return 'default'; } }
  function sid(){ try{ return (typeof curSession === 'function') ? String(curSession()) : 'default'; }catch(e){ return 'default'; } }
  function modeKey(){ try{ return (typeof state !== 'undefined' && state) ? String(state.mode || 'chat') : 'chat'; }catch(e){ return 'chat'; } }
  function val(i){ var e = Q(i); return e ? String(e.value == null ? '' : e.value) : ''; }
  /* ⭐ pm_073 §一：真交付（用户点击所驱）⇒ 入 msgs；探针 ／ 自测 ／ 复验（器 ／ API 所驱）⇒ 唯入活动线程面（⛔ 入 msgs）。 */
  var probeRun = false;
  function say(msg, cls){ try{ if(typeof addLog === 'function') addLog(msg, cls || 'ok', !probeRun, SRC); }catch(e){} }
  var BTN = 'font-size:11px;padding:2px 9px;border-radius:6px;border:1px solid var(--border);'
          + 'background:rgba(88,166,255,.12);color:var(--text);cursor:pointer;line-height:1.9';
  var INP = 'width:100%;background:var(--card2);border:1px solid var(--border);color:var(--text);'
          + 'border-radius:6px;font-size:11.5px;padding:3px 6px;font-family:inherit';
  var SUB = 'color:var(--sub)';

  /* ---------- 8.1 ⭐ 硬条二：task_id 之穗（纯 sha256 · ⛔ 随机 ／ ⛔ 时间戳 ／ ⛔ 前端自增）----------
     定形（**两端须逐字复算** —— PM 落后端时以此为准）：
       body_sha256 = sha256_hex( utf8(body_md) )                        // 小写 64 位
       canonical   = task.strip() + "\n" + to.join(",") + "\n" + body_sha256
       task_id     = "t1-" + sha256_hex( utf8(canonical) ).slice(0,16)
     ⛔ 不含 user_id ／ 刻 ／ 随机数（承 pm_071 §四：幂等键 ＝ hash(交办 ＋ 收件人 ＋ 正文散列)）。 */
  function utf8Bytes(s){
    s = String(s == null ? '' : s);
    var out = [], i, c, c2, cp;
    for(i = 0; i < s.length; i++){
      c = s.charCodeAt(i);
      if(c < 0x80){ out.push(c); }
      else if(c < 0x800){ out.push(0xC0 | (c >> 6), 0x80 | (c & 63)); }
      else if(c >= 0xD800 && c <= 0xDBFF && i + 1 < s.length){
        c2 = s.charCodeAt(i + 1);
        if(c2 >= 0xDC00 && c2 <= 0xDFFF){
          cp = 0x10000 + ((c - 0xD800) << 10) + (c2 - 0xDC00);
          out.push(0xF0 | (cp >> 18), 0x80 | ((cp >> 12) & 63), 0x80 | ((cp >> 6) & 63), 0x80 | (cp & 63));
          i++;
        } else { out.push(0xE0 | (c >> 12), 0x80 | ((c >> 6) & 63), 0x80 | (c & 63)); }
      } else { out.push(0xE0 | (c >> 12), 0x80 | ((c >> 6) & 63), 0x80 | (c & 63)); }
    }
    return out;
  }
  function rotr(x, n){ return (x >>> n) | (x << (32 - n)); }
  var K = [0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
  function sha256hex(s){
    var msg = utf8Bytes(s);
    var HS = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
    var lb = msg.length;
    msg.push(0x80);
    while(msg.length % 64 !== 56) msg.push(0);
    var bl = lb * 8, hi = Math.floor(bl / 4294967296), lo = bl >>> 0;
    msg.push((hi >>> 24) & 255, (hi >>> 16) & 255, (hi >>> 8) & 255, hi & 255);
    msg.push((lo >>> 24) & 255, (lo >>> 16) & 255, (lo >>> 8) & 255, lo & 255);
    var w = new Array(64), i, off;
    for(off = 0; off < msg.length; off += 64){
      for(i = 0; i < 16; i++){
        w[i] = (msg[off+i*4] << 24) | (msg[off+i*4+1] << 16) | (msg[off+i*4+2] << 8) | (msg[off+i*4+3]);
      }
      for(i = 16; i < 64; i++){
        var s0 = rotr(w[i-15],7) ^ rotr(w[i-15],18) ^ (w[i-15] >>> 3);
        var s1 = rotr(w[i-2],17) ^ rotr(w[i-2],19) ^ (w[i-2] >>> 10);
        w[i] = (w[i-16] + s0 + w[i-7] + s1) | 0;
      }
      var a=HS[0],b=HS[1],c=HS[2],d=HS[3],e=HS[4],f=HS[5],g=HS[6],h=HS[7];
      for(i = 0; i < 64; i++){
        var S1 = rotr(e,6) ^ rotr(e,11) ^ rotr(e,25);
        var ch = (e & f) ^ (~e & g);
        var t1 = (h + S1 + ch + K[i] + w[i]) | 0;
        var S0 = rotr(a,2) ^ rotr(a,13) ^ rotr(a,22);
        var mj = (a & b) ^ (a & c) ^ (b & c);
        var t2 = (S0 + mj) | 0;
        h=g; g=f; f=e; e=(d + t1)|0; d=c; c=b; b=a; a=(t1 + t2)|0;
      }
      HS[0]=(HS[0]+a)|0; HS[1]=(HS[1]+b)|0; HS[2]=(HS[2]+c)|0; HS[3]=(HS[3]+d)|0;
      HS[4]=(HS[4]+e)|0; HS[5]=(HS[5]+f)|0; HS[6]=(HS[6]+g)|0; HS[7]=(HS[7]+h)|0;
    }
    return HS.map(function(x){ return ('00000000' + (x >>> 0).toString(16)).slice(-8); }).join('');
  }
  function taskIdOf(task, to, body){
    var toArr = Array.isArray(to) ? to : String(to == null ? '' : to).split(/[;,\s]+/).filter(function(x){ return !!x; });
    var bodySha = sha256hex(String(body == null ? '' : body));
    var canon = String(task == null ? '' : task).trim() + '\n' + toArr.join(',') + '\n' + bodySha;
    return 't1-' + sha256hex(canon).slice(0, 16);
  }

  /* ---------- 8.2 面之数据 ---------- */
  var lastPlan = null, lastPlanTask = '', decisionId = '', lastTaskId = '',
      lastStage = '', lastHttp = null, receiptKind = 'none', backendState = '探测中…';
  /* ⭐ pm_刀15p-补 §一.1：**人工步数 ≤ 2**（交办 1 步 ＋ 授权 1 步）—— 本器只**数人点了几下**（⛔ 推算 · ⛔ 编）。 */
  var paT1Steps = 0, lastStopDoc = null;
  function setSteps(n, why){
    paT1Steps = (typeof n === 'number' && n >= 0) ? n : 0;
    var e = Q(ID.steps);
    if(e){
      e.textContent = paT1Steps + '／2' + (paT1Steps > 2 ? ' ⚠ 超' : '');
      e.style.color = (paT1Steps > 2) ? 'var(--amber)' : '';
      e.title = '人工步数（承 pm_刀15p-补 §一.1：交办 1 ＋ 授权 1 · 目标 ≤ 2）' + (why ? (' · ' + why) : '');
    }
    return paT1Steps;
  }
  function bumpStep(why){ return setSteps(paT1Steps + 1, why); }
  function stopTo(){ var v = val(ID.stop).trim(); return v || '本人'; }
  function stopToRaw(){ return val(ID.stop).trim(); }
  /* ⭐ pm_刀16p §〇：**引哪封来信**（C1「原来信之件」之落点）—— 面入参 ⇒ 后端填 `凭什么.引哪封来信`。 */
  function refOf(){
    return { '件号': val(ID.refNo).trim(), 'sha16': val(ID.refSha).trim() };
  }
  function refHas(r){ r = r || refOf(); return !!(r['件号'] || r['sha16']); }
  function refLine(r){
    r = r || refOf();
    if(!refHas(r)) return '缺（未附原信 ⇒ ⛔ 装已附 · 后端回执同显「缺」）';
    return '件号 ' + (r['件号'] || '（缺）') + ' ／ sha16 ' + (r['sha16'] || '（缺）');
  }
  /* ⭐ pm_刀15p §一③ ＋ pm_刀16p §一.4：**花了多少** ＋ **$/件** —— 读数皆后端取（⛔ 前端估 · ⛔ 数 token）。 */
  function numOr(v, unit){
    if(v == null) return '未取得';
    if(typeof v === 'number') return (String(v) + (unit || ''));
    return String(v);
  }
  function spendLine(rc){
    var s = (rc && rc['花了多少']) || null;
    if(!s) return '未取得（后端未给 `花了多少` 键）';
    var b = s['bytes'] || {};
    return 'wall_s ' + numOr(s['wall_s'], ' 秒') + ' · 入 ' + numOr(b['in'], ' B') + ' ／ 出 ' + numOr(b['out'], ' B')
      + ' · ' + numOr(s['money']) + ' ' + String(s['currency'] || 'CNY')
      + (s['source'] ? (' · 源 ' + String(s['source'])) : '')
      + (s['读数之器'] ? (' · 器 ' + String(s['读数之器'])) : '');
  }
  function costLine(rc){
    var c = (rc && rc['成本']) || null;
    if(!c) return '未取得（后端未给 `成本` 键）';
    return '单价 ' + numOr(c['单价_元每件']) + ' ' + String(c['币'] || 'CNY') + ' ／ 件 · 总 ' + numOr(c['总花费_元'])
      + ' · 件数 ' + numOr(c['件数']) + '（口径 ' + String(c['口径'] || '—') + '）'
      + (c['本地_远端'] ? (' · ' + String(c['本地_远端'])) : '')
      + (c['tokens'] == null ? (' · tokens 无（' + String(c['tokens_之由'] || '未取得') + '）') : (' · tokens ' + c['tokens']));
  }
  /* ⭐ pm_073 §三（T1.1）：`stop_to` 入参 —— ⛔ 必填；**唯面有真值方传** ⇒ 缺省由后端自解「本人」
     （⛔ 传 `本人` 字面 ⇒ 会把后端之**正确默认**顶掉 · 我 1129 前向接线之隐病 · 自逮）。 */
  function payloadOf(tid, b){
    var p = { user_id: uid(), task_id: tid, decision_id: decId(),
              to: b.to, subject: b.subject, body_md: b.body_md };
    var st = stopToRaw();
    if(st) p.stop_to = st;
    /* ⭐ pm_刀16p §〇：`in_reply_to`（后端 deliver 已收 ⇒ 填回执之 `凭什么.引哪封来信`）。 */
    var r = refOf();
    if(refHas(r)) p.in_reply_to = { '件号': r['件号'], 'sha16': r['sha16'] };
    return p;
  }
  /* ⭐ pm_刀16p §一.3：**停手之留痕**取后端 `POST /v9/pa/deliver/stop`（「报给谁」恒有字段 · ⛔ 前端自说）。 */
  async function stopTrace(stage, tid, b){
    var body = { user_id: uid(), task_id: tid || '', stage: stage || '交付',
                 subject: (b && b.subject) || '', to: (b && b.to) || [] };
    var st = stopToRaw();
    if(st) body.stop_to = st;
    try{
      var r = await fetch(API + '/v9/pa/deliver/stop', { method:'POST', cache:'no-store',
        headers:{ 'Content-Type':'application/json' }, body: JSON.stringify(body) });
      var d = await r.json().catch(function(){ return null; });
      lastStopDoc = (d && typeof d === 'object') ? d : null;
      return lastStopDoc;
    }catch(e){ lastStopDoc = null; return null; }
  }
  function decId(){ var v = val(ID.dec).trim(); return v || decisionId; }
  function setDecision(id){ var e = Q(ID.dec); if(e) e.value = String(id == null ? '' : id); decisionId = String(e ? e.value : '').trim(); return decisionId; }
  /* ⭐ pm_072 §一.1：面须能**读** PM 落的真拍板（⛔ 本面造号 —— 真拍板写 data\ 属 PM 之界） */
  var decLoaded = false;
  var BLOCK_LABEL = { input:'参数闸（缺参 · 400）', decision_gate:'拍板闸（decision_id · 403 fail-closed）',
                      idem:'幂等闸（同 task_id 异文 · 409）', recipient_scope:'收件人闸（甲形限域 · 403）',
                      credentials:'凭据闸（502）', send:'发送（502）' };
  async function loadDecision(force){
    var el = Q(ID.dec), src = Q(ID.decSrc);
    if(!el) return null;
    if(!force && (decLoaded || el.value.trim())) return el.value.trim();
    try{
      var r = await fetch(API + '/v9/pa/decision/log', { cache:'no-store' });
      var d = await r.json().catch(function(){ return null; });
      var rows = ((d && d.decisions) || []).filter(function(x){ return x && x.decision === '采纳' && x.id; });
      decLoaded = true;
      if(!rows.length){
        if(src) src.textContent = '后端 log 无「采纳」之拍板（HTTP ' + r.status + '）⇒ 照实（⛔ 前端编号）';
        return null;
      }
      var last = rows[rows.length - 1];
      if(!el.value.trim()){
        el.value = String(last.id);
        if(src) src.textContent = '后端 log 最新「采纳」：' + String(last.id) + '（人 ' + String(last.user_id || '—')
          + ' · 阶段 ' + String(last.stage || '—') + '）· 件之刻 ' + paSelfAt(last.ts)
          + '（后端 decision_log 之 ts 下发 · ⛔ 前端 nowStr 顶件刻 · 承 pm_刀11p §二.4）';
      }
      return el.value.trim();
    }catch(e){
      if(src) src.textContent = '读 log 未送达（' + String((e && e.message) || e) + '）⇒ ⛔ 前端编号';
      return null;
    }
  }
  /* ⭐ 回执行之「四件」须为**人话**：优先取后端「人话」行；无则回退结构化中文键（逐键对齐后端 build_receipt） */
  function flat(v){
    if(v == null) return '';
    if(typeof v !== 'object') return String(v);
    if(Object.prototype.toString.call(v) === '[object Array]'){
      var o = [], i; for(i = 0; i < v.length; i++){ var x = flat(v[i]); if(x) o.push(x); }
      return o.join(' ／ ');
    }
    var p = [];
    for(var k in v){ if(!Object.prototype.hasOwnProperty.call(v, k)) continue;
      var y = v[k]; if(y == null || y === '') continue;
      p.push(k + ' ' + flat(y)); }
    return p.join(' ／ ');
  }
  function humanOf(d){
    var rr = (d && (d.receipt || d.receipt_four)) || d || {};
    return String(rr['人话句'] || (rr['人话'] && flat(rr['人话'])) || d.human || d.human_text || '');
  }
  function deliverBody(){
    var to = val(ID.to).split(/[;,\s]+/).filter(function(x){ return !!x; });
    var task = val(ID.task).trim() || lastPlanTask;
    var subject = val(ID.subject).trim() || task.slice(0, 24);
    var body = val(ID.body); if(!body) body = task;
    var r = refOf();
    return { task: task, to: to, subject: subject, body_md: body,
             refNo: r['件号'], refSha: r['sha16'] };
  }

  /* ---------- 8.3 判据 1：交办 ⇒ 计划上屏 ---------- */
  function renderPlan(d){
    lastPlan = d || null;
    var host = Q(ID.plan); if(!host) return;
    var steps = (d && Array.isArray(d.steps)) ? d.steps : [];
    if(!steps.length){
      host.innerHTML = '<div style="color:var(--amber)">\u26a0 \u540e\u7aef\u672a\u7ed9\u8ba1\u5212'
        + '\uff08POST /v9/pa/plan \u672a\u56de \u2228 \u7a7a steps\uff09\u21d2 \u7167\u5b9e'
        + '\uff08\u26d4 \u524d\u7aef\u4e0d\u7f16\u6b65\u9aa4\uff09</div>';
      return;
    }
    var rows = steps.map(function(s, i){
      return '<div style="display:flex;gap:8px;padding:2px 0;border-bottom:1px dashed rgba(48,54,61,.55)">'
        + '<span style="flex:0 0 16px;color:var(--sub)">' + (i+1) + '</span>'
        + '<span style="flex:0 0 76px">' + H(s.stage) + '</span>'
        + '<span style="flex:1;min-width:0">' + H(s.label)
        + (s.produces ? ' \u00b7 <span style="' + SUB + '">\u4ea7\u51fa ' + H(s.produces) + '</span>' : '')
        + (s.verify   ? ' \u00b7 <span style="' + SUB + '">\u9a8c\u6536 ' + H(s.verify) + '</span>' : '')
        + (s.owner    ? ' \u00b7 <span style="' + SUB + '">\u627f\u63a5 ' + H(s.owner) + '</span>' : '')
        + '</span></div>';
    }).join('');
    host.innerHTML = '<div style="margin:4px 0 2px"><b>\u8ba1\u5212</b>\uff1a\u5171 <b>' + steps.length + '</b> \u6b65'
      + ' <span style="' + SUB + '">\uff08\u6e90 POST /v9/pa/plan \u00b7 task_type ' + H((d && d.task_type) || '\u2014')
      + ' \u00b7 source ' + H((d && d.source) || '\u2014') + '\uff09</span></div>'
      + rows
      + '<div style="margin-top:4px"><b>\u62cd\u677f\u70b9</b>\uff1a\u4ea4\u4ed8\uff08\u53d1\u4fe1\uff09\u524d \u2014\u2014 '
      + '\u987b\u8001\u677f\u4eb2\u6279\uff08POST /v9/pa/decision \u843d decision_id\uff09\uff1b'
      + '<span style="' + SUB + '">plan \u56de\u6267\u672a\u7ed9\u300c\u62cd\u677f\u70b9\u300d\u5b57\u6bb5 \u21d2 '
      + '\u6b64\u636e\u63a5\u53e3\u5b9a\u5f62\uff08pm_071 \u00a7\u56db\uff1a\u7f3a decision_id \u21d2 403 fail-closed\uff09'
      + '\uff0c\u26d4 \u524d\u7aef\u4e0d\u7f16</span></div>';
  }
  async function doPlan(probe){
    probeRun = (probe === true);
    var out = Q(ID.out);
    var task = val(ID.task).trim();
    if(!task){ if(out) out.textContent = '\u8ba1\u5212\uff1a\u26d4 \u4ea4\u529e\u4e3a\u7a7a \u21d2 \u672a\u63d0\u4ea4\uff08\u26d4 \u5f00\u7a7a\u4ef6\uff09'; return; }
    lastStage = 'plan';
    if(out) out.textContent = '\u8ba1\u5212\uff1a\u8bf7\u6c42\u4e2d\u2026\uff08POST /v9/pa/plan\uff09';
    try{
      var r = await fetch(API + '/v9/pa/plan', { method:'POST', cache:'no-store',
        headers:{ 'Content-Type':'application/json' },
        body: JSON.stringify({ user_id: uid(), session_id: sid(), task: task, mode: modeKey() }) });
      lastHttp = r.status;
      var d = await r.json().catch(function(){ return null; });
      if(!d || d.ok === false){
        renderPlan(null);
        if(out) out.textContent = '\u8ba1\u5212\uff1a\u540e\u7aef\u672a\u7ed9\uff08HTTP ' + r.status
          + (d && d.error ? (' \u00b7 ' + d.error) : '') + '\uff09\u21d2 \u7167\u5b9e';
        return;
      }
      lastPlanTask = task;
      renderPlan(d);
      if(out) out.textContent = '\u8ba1\u5212\uff1a\u5df2\u51fa ' + ((d.steps || []).length) + ' \u6b65\uff08HTTP '
        + r.status + '\uff09\u00b7 \u523b ' + nowStr();
      say('\ud83d\uddc2 T1 \u5df2\u51fa\u8ba1\u5212\uff1a' + ((d.steps || []).length) + ' \u6b65\uff08POST /v9/pa/plan\uff09', 'ok');
    }catch(e){
      renderPlan(null);
      if(out) out.textContent = '\u8ba1\u5212\uff1a\u8bf7\u6c42\u672a\u9001\u8fbe\uff08' + String((e && e.message) || e)
        + '\uff09\u21d2 \u26d4 \u4e0d\u7b49\u4e8e\u65e0\u8ba1\u5212';
    }
  }

  /* ---------- 8.4 拍板（授权点之前半）：POST /v9/pa/decision ---------- */
  async function doAdopt(probe){
    probeRun = (probe === true);
    var out = Q(ID.out);
    var task = val(ID.task).trim() || lastPlanTask;
    if(!task){ if(out) out.textContent = '\u62cd\u677f\uff1a\u26d4 \u65e0\u4ea4\u529e \u21d2 \u672a\u62cd\u677f'; return; }
    lastStage = 'decision';
    if(out) out.textContent = '\u62cd\u677f\uff1a\u8bf7\u6c42\u4e2d\u2026\uff08POST /v9/pa/decision \u00b7 \u91c7\u7eb3\uff09';
    try{
      var r = await fetch(API + '/v9/pa/decision', { method:'POST', cache:'no-store',
        headers:{ 'Content-Type':'application/json' },
        body: JSON.stringify({ user_id: uid(), session_id: sid(), decision:'\u91c7\u7eb3',
          node:'\u4ea4\u4ed8', stage:'\u4ea4\u4ed8', note:'T1 \u4ea4\u529e \u00b7 \u53d1\u4fe1\u524d\u62cd\u677f\uff08\u672c\u9762\uff09', task: task }) });
      lastHttp = r.status;
      var d = await r.json().catch(function(){ return null; });
      var rec = d && d.decision;
      if(!d || d.ok === false || !rec || !rec.id){
        if(out) out.textContent = '\u62cd\u677f\uff1a\u540e\u7aef\u672a\u7ed9 decision_id\uff08HTTP ' + r.status
          + '\uff09\u21d2 \u7167\u5b9e\uff08\u26d4 \u524d\u7aef\u7f16\u53f7\uff09';
        return;
      }
      decisionId = String(rec.id);
      setDecision(decisionId);
      var _ds = Q(ID.decSrc); if(_ds) _ds.textContent = '本面自拍（POST /v9/pa/decision）· 件之刻 '
        + ((rec && rec.ts != null) ? paSelfAt(rec.ts) : ('缺（后端未给 ts）⇒ 本轮读数刻 ' + nowStr())) + '（承 pm_刀11p §二.4）';
      if(out) out.textContent = '\u62cd\u677f\uff1a\u5df2\u843d decision_log \u00b7 id ' + decisionId
        + '\uff08HTTP ' + r.status + '\uff09\u00b7 \u523b ' + nowStr();
      say('\ud83d\uddc2 T1 \u5df2\u62cd\u677f\uff08\u91c7\u7eb3\uff09\uff1adecision_id ' + decisionId, 'ok');
    }catch(e){
      if(out) out.textContent = '\u62cd\u677f\uff1a\u8bf7\u6c42\u672a\u9001\u8fbe\uff08' + String((e && e.message) || e) + '\uff09\u21d2 \u26d4 \u672a\u62cd\u677f';
    }
  }

  /* ---------- 8.5 判据 2：停手卡（⭐ 硬条一 弱保证自标「弱」）---------- */
  /* ---------- 8.5 判据 2：停手卡（⭐ 硬条一 弱保证自标「弱」）---------- */
  function doDeliver(probe){
    probeRun = (probe === true);
    var out = Q(ID.out);
    var b = deliverBody();
    if(!b.task){ if(out) out.textContent = '交付：⛔ 无交办 ⇒ 未发'; return Promise.resolve(); }
    if(!b.to.length){ if(out) out.textContent = '交付：⛔ 收件人为空 ⇒ 未发（⛔ 开空件）'; return Promise.resolve(); }
    if(!decId()){
      /* ⭐ 判据 6 之止步（前端之弱保证 · 未批即止）⇒ 亦出**失败回执**（⛔ 只留一句 out）。
         ⭐ pm_刀16p §一.3：`报给谁` 取**后端** `POST /v9/pa/deliver/stop` 之字段（⛔ 前端自说）。 */
      var tid0 = taskIdOf(b.task, b.to, b.body_md);
      if(out) out.textContent = '交付：⛔ 未拍板（无 decision_id）⇒ 前端不发（「前端之弱保证」）· 正在落「停手」留痕…';
      return stopTrace('拍板（T1 发信之授权点 · 未批 ⇒ 止）', tid0, b).then(function(sd){
        var who = (sd && sd['报给谁']) ? String(sd['报给谁']) : stopTo();
        var whoAxis = (sd && sd['报给谁之面']) ? ('后端 deliver/stop · ' + String(sd['报给谁之面'])) : '本面之「停手收件人」字段';
        showFail('拍板（T1 发信之授权点 · 未批 ⇒ 止）', who, whoAxis,
          '未拍板（无 decision_id）—— 前端之弱保证（未批 ⇒ 不发）；'
          + '真闸在后端（发信路由内 · 缺 decision_id ⇒ 403 fail-closed）', tid0);
        if(out) out.textContent = '交付：⛔ 未拍板（无 decision_id）⇒ 前端不发'
          + '（「前端之弱保证」）· 后端此路将 403 fail-closed · 已出失败回执 · 报给 ' + who
          + (sd ? ('（后端 deliver/stop · 留痕径 ' + String((sd['留痕'] && sd['留痕']['面之径逐字']) || '—') + '）') : '');
        say('🗂 T1 交付止步：未拍板 ⇒ 前端不发（弱保证）· 报给 ' + who, 'warn');
      });
    }
    var tid = taskIdOf(b.task, b.to, b.body_md);
    openAuthzCard(tid, b, false);
    return Promise.resolve();
  }
  /* ⭐ 授权卡（＝**授权点** · 承 pm_刀15p-补 §二）：整段发信唯此人点「本次发送」一下。 */
  function openAuthzCard(tid, b, needAdopt){
    var out = Q(ID.out);
    var ask = window.paStopAsk;
    if(typeof ask !== 'function' || !Q('paStopAsk')){
      if(out) out.textContent = '交付：⛔ 停手卡不可用（paStopAsk 未就绪）⇒ 未发（fail-closed）';
      return;
    }
    lastTaskId = tid; lastStage = 'deliver';
    ask({
      title: '⛔ 停手：即将以你名义发信（T1 交付）',
      rows: [
        ['做什么', '发信给 ' + b.to.join(', ') + '（主题：' + b.subject + '）'],
        ['凭什么', refLine()],
        ['通道', 'POST /v9/pa/deliver/mail（我方闭环 · 后端真闸）'],
        ['代价', '未取得（后端于**发后**之回执给 wall_s ／ bytes ／ tokens ／ $/件 ⇒ ⛔ 前端估）'],
        ['报给谁', stopTo() + '（停手时由后端 POST /v9/pa/deliver/stop 定 · 其「报给谁」恒有字段）'],
        ['可撤销性', '未批即未动 —— 此刻后悔 ＝ 什么都不发生'],
        ['弱保证', '未批 ⇒ 前端不发（前端之弱保证）⇔ 后端拒执（真闸 · 在发信路由内）'],
        ['授权', needAdopt ? '本卡即授权点 ⇒ 点「本次发送」落真拍板（POST /v9/pa/decision）再发' : ('decision_id ' + decId())],
        ['人工步数', String(paT1Steps) + '／2（点本卡 ⇒ ' + String(paT1Steps + 1) + '）'],
        ['引哪封来信', refLine()],
        ['task_id', tid],
        ['刻', nowStr()]
      ],
      okLabel: '✅ 本次发送',
      cancelLabel: '❌ 取消',
      persistMsg: !probeRun,
      onOk: function(){
        bumpStep('授权（停手卡）');
        if(needAdopt){ adoptThenSend(tid, b); return; }
        send(tid, b);
      },
      onCancel: function(){
        stopTrace('授权点（老板取消 ⇒ 未授权 ⇒ ⛔ 未发）', tid, b).then(function(sd){
          var who = (sd && sd['报给谁']) ? String(sd['报给谁']) : stopTo();
          var axis = (sd && sd['报给谁之面']) ? ('后端 deliver/stop · ' + String(sd['报给谁之面'])) : '本面之「停手收件人」字段';
          showFail('授权点（老板取消 ⇒ 未授权 ⇒ ⛔ 未发）', who, axis,
            '老板点了「❌ 取消」⇒ 未授权 ⇒ ⛔ 未发（此刻后悔 ＝ 什么都不发生）', tid);
          if(out) out.textContent = '交付：已取消（未批即未动 · ⛔ 未发）· 停手留痕之「报给谁」' + who
            + '（面：' + axis + '）';
        });
      }
    });
  }
  /* ⭐ pm_刀15p-补 §一.1：一句话交办 ⇒ 止于**授权点**（⛔ 自动写拍板 —— 以你名义那一下须人点）。 */
  async function adoptThenSend(tid, b){
    var out = Q(ID.out);
    await doAdopt(probeRun);
    if(!decId()){ if(out) out.textContent = '交付：⛔ 授权未落（后端未给 decision_id）⇒ 未发（fail-closed）'; return; }
    send(tid, b);
  }
  async function doOneStep(probe){
    probeRun = (probe === true);
    var out = Q(ID.out);
    var task = val(ID.task).trim();
    if(!task){ if(out) out.textContent = '一句话交办：⛔ 交办为空 ⇒ 未提交（⛔ 开空件）'; return; }
    bumpStep('交办（一句话交办）');
    await doPlan(probe);
    if(!lastPlan || !((lastPlan.steps || []).length)){
      if(out) out.textContent = '一句话交办：⛔ 后端未给计划 ⇒ 停在授权点之前（⛔ 前端编步骤）'; return;
    }
    var b = deliverBody();
    if(!b.to.length){ if(out) out.textContent = '一句话交办：⛔ 收件人为空 ⇒ 未到授权点'; return; }
    /* ⭐ 面已载**真拍板**（后端 decision_log）⇒ 本步 ⛔ 另写（承 pm_072 §一.1：拍板写 data\\ 属老板）。 */
    var needAdopt = !decId();
    openAuthzCard(taskIdOf(b.task, b.to, b.body_md), b, needAdopt);
  }

  /* ---------- 8.6 判据 4 ／ 6：交付 ＋ 回执（读数取后端）---------- */
  async function send(tid, b){
    var out = Q(ID.out);
    lastTaskId = tid; lastStage = 'deliver';
    if(out) out.textContent = '\u4ea4\u4ed8\uff1a\u53d1\u9001\u4e2d\u2026\uff08POST /v9/pa/deliver/mail\uff09\u00b7 task_id ' + tid;
    try{
      var r = await fetch(API + '/v9/pa/deliver/mail', { method:'POST', cache:'no-store',
        headers:{ 'Content-Type':'application/json' },
        body: JSON.stringify(payloadOf(tid, b)) });
      lastHttp = r.status;
      var d = await r.json().catch(function(){ return null; });
      renderReceipt(r.status, d, tid, null);
    }catch(e){
      renderReceipt(0, null, tid, String((e && e.message) || e));
    }
  }
  function fourItems(src){
    src = src || {};
    var rows;
    var hl = src['人话'];
    if(Object.prototype.toString.call(hl) === '[object Array]' && hl.length){
      /* ⭐ pm_刀16p §一.1：后端「人话」行之**标**固定（`· 做了什么：` 等）⇒ 只剥**固定前缀**
         （⛔ 按「首个冒号」切 —— 后端行内**多冒号** ⇒ 按首冒号切会把值切丢）。 */
      var PREF = ['做了什么：', '凭什么：', '花了多少：', '谁批的：', '引哪封来信：', '停在哪一步：'];
      rows = hl.map(function(s){
        s = String(s == null ? '' : s).replace(/^[\s·•]+/, '');
        var i, k;
        for(i = 0; i < PREF.length; i++){ k = PREF[i];
          if(s.indexOf(k) === 0) return [k.replace(/：$/, ''), s.slice(k.length)];
        }
        var j = s.indexOf('：');
        if(j > 0 && j <= 12) return [s.slice(0, j).trim(), s.slice(j + 1)];
        return ['四件', s];
      });
    } else {
      var want = [['做了什么', ['做了什么','did','did_text','what','action']],
                  ['凭什么',   ['凭什么','why','basis','evidence']],
                  ['花了多少', ['花了多少','cost','cost_text','spend']],
                  ['谁批的',   ['谁批的','who','approved_by','authz']]];
      rows = want.map(function(p){
        var v = null, i, x;
        for(i = 0; i < p[1].length; i++){ x = src[p[1][i]]; if(x != null && x !== ''){ v = x; break; } }
        return [p[0], (v == null) ? '未取得（后端未给此件）' : flat(v)];
      });
    }
    /* ⭐ 引哪封来信 ／ $/件：缺则补（⛔ 只报四件而漏此二要件 · 承 pm_刀15p §一②③ ＋ pm_刀16p §一.4） */
    function has(re){ var ok = false; for(var i = 0; i < rows.length; i++){ if(re.test(rows[i][0])){ ok = true; break; } } return ok; }
    var basis = src['凭什么'] || null;
    var ir = (basis && typeof basis === 'object') ? basis['引哪封来信'] : null;
    if(!has(/引哪封来信/) && ir) rows.push(['引哪封来信', flat(ir)]);
    if(!has(/成本|\$|\/件/)) rows.push(['$/件', costLine(src)]);
    if(!has(/谁批的/) && src['谁批的']) rows.push(['谁批的', flat(src['谁批的'])]);
    return rows;
  }
  function engDetails(host, d, netErr){
    try{
      var b = host.querySelector('.engbody');
      if(b) b.textContent = (d == null) ? ('\uff08\u65e0\u4f53 \u00b7 netErr ' + String(netErr || '') + '\uff09')
                                        : JSON.stringify(d, null, 2).slice(0, 4000);
    }catch(e){}
  }
  function failHTML(stageLbl, who, whoAxis, why, tid, blockedBy){
    return '<div style="color:var(--amber)"><b>\u5931\u8d25\u56de\u6267</b></div>'
      + '<div><b>停在哪一步</b>：' + H(stageLbl) + (blockedBy ? ('　<b>闸</b>：' + H(BLOCK_LABEL[blockedBy] || blockedBy)) : '') + '</div>'
      + '<div><b>\u62a5\u7ed9\u8c01</b>\uff1a' + H(who) + '\uff08\u505c\u624b\u6536\u4ef6\u4eba \u00b7 \u53d6\u81ea' + H(whoAxis) + '\uff09</div>'
      + '<div><b>\u56e0</b>\uff1a' + H(why) + '</div>'
      + '<div><b>task_id</b>\uff1a' + H(tid || '\u2014') + '\u3000<b>decision_id</b>\uff1a' + H(decisionId || '\u2014') + '</div>'
      + '<div style="' + SUB + '">\u523b ' + nowStr() + ' \u00b7 \u26d4 \u672a\u542b\u51ed\u636e\uff08\u6388\u6743\u7801\u503c\u4e0d\u5165\u5c4f \u00b7 \u627f pm_071 \u00a7\u56db\uff09</div>';
  }
  function showFail(stageLbl, who, whoAxis, why, tid){
    var host = Q(ID.rc); if(!host) return;
    receiptKind = 'fail';
    host.innerHTML = failHTML(stageLbl, who, whoAxis, why, tid);
  }
  function renderReceipt(http, d, tid, netErr){
    var host = Q(ID.rc); if(!host) return;
    var good = (!netErr) && http >= 200 && http < 300 && d && d.ok !== false && d.success !== false;
    if(good){
      receiptKind = 'ok';
      var human = humanOf(d);
      var rco = (d && (d.receipt || d.receipt_four)) || d || {};
      var rows = fourItems(d.receipt || d.receipt_four || d);
      /* ⭐ pm_刀11p §零 ／ pm_刀16p §一.2：**每件自带「件之刻」** —— 取后端回执自带之「刻」
         （回执不可逆 · 其刻 ＝ 真发之刻）⛔ 以屏上「本轮」刻冒充（实测差 ≈ 4h20m）。 */
      var pieceAt = rco['刻'] ? String(rco['刻']) : null;
      host.innerHTML = '<div style="color:var(--green)"><b>回执（后端 · HTTP ' + http + '）</b>'
        + (human ? ('　' + H(human)) : '') + '</div>'
        + rows.map(function(x){ return '<div><b>' + H(x[0]) + '</b>：' + H(x[1]) + '</div>'; }).join('')
        + '<div><b>件之刻（后端回执 · ⛔ 本轮刻）</b>：' + H(pieceAt || '缺（后端回执未给「刻」）')
        + '　<span style="' + SUB + '">本轮读数刻 ' + nowStr() + '</span></div>'
        + '<div><b>花了多少（真读数）</b>：' + H(spendLine(rco)) + '</div>'
        + '<div><b>$/件</b>：' + H(costLine(rco)) + '</div>'
        + '<div style="' + SUB + '">task_id ' + H(tid) + ' · 真源：POST /v9/pa/deliver/mail 回执'
        + '（四件 ＋ 引哪封来信 ＋ 件之刻 ＋ $/件 皆后端取 · ⛔ 前端估）'
        + ((d && d['印']) ? (' · 印 ' + H(d['印'])) : '') + '</div>'
        + '<details class="eng"><summary>工程注记（回执 JSON 原文 · ⛔ 用户面）</summary><div class="engbody"></div></details>';
      say('🗂 T1 交付回执（后端）：' + (human || '已回')
        + ' · 件之刻 ' + (pieceAt || '缺（后端未给）') + ' · task_id ' + String(tid), 'ok');
    } else {
      receiptKind = 'fail';
      var rc = (d && (d.receipt || d.receipt_four)) || null;
      var pol = (d && d.policy) || null;
      var stl = (d && d['授权留痕']) || null;
      var why = netErr ? ('请求未送达（' + netErr + '）· ⛔ 不等于未发')
        : ('HTTP ' + http + (d && d.error ? (' · ' + d.error) : '')
           + (http === 403 ? ' ⇒ 后端 fail-closed（真闸）'
              : (http === 404 ? ' ⇒ 后端路由未接（器未接之证）'
                 : (http === 409 ? ' ⇒ 幂等拒（task_id 已用于另一交办）' : ''))));
      /* ⭐ 判据 ⑥：停在哪一步 ＋ 报给谁 —— **取后端**（回执 ∨ 留痕行 ∨ policy.stop_to · ⛔ 前端自说） */
      var stage = (rc && rc['停在哪一步']) || BLOCK_LABEL[(d && d.blocked_by) || ''] || '交付';
      var whoB = (rc && rc['报给谁']) || (stl && stl['报给谁'])
              || (pol && pol.stop_to) || (d && (d.stop_to || d.report_to || d.notify)) || '';
      var whoAxisB = (rc && rc['报给谁']) ? '后端回执'
              : ((stl && stl['报给谁']) ? '后端 deliver/mail 留痕行'
                 : ((pol && pol.stop_to) ? '后端 policy.stop_to' : ''));
      var hasBackendWho = !!String(whoB || '');
      var who = hasBackendWho ? String(whoB) : stopTo();
      host.innerHTML = failHTML(String(stage), who,
          hasBackendWho ? whoAxisB : '本面之「停手收件人」字段',
          why, tid, (d && d.blocked_by) || '')
        + '<div><b>件之刻（后端回执）</b>：' + H(rc && rc['刻'] ? String(rc['刻']) : '无（此路未到回执行）') + '</div>'
        + '<div><b>$/件</b>：' + H(rc ? costLine(rc) : '无回执（此路未到回执行 ⇒ 未取得）') + '</div>'
        + '<details class="eng"><summary>工程注记（回执 JSON 原文 · ⛔ 用户面）</summary><div class="engbody"></div></details>';
      say('🗂 T1 交付失败回执：停在「' + String(stage) + '」· 报给 ' + who + ' · ' + why, 'warn');
    }
    engDetails(host, d, netErr);
  }

  /* ---------- 8.7 面之自挂载（⛔ 动 pa.html ⇒ 由本件建 ＋ 幂等）---------- */
  function fmtTaskId(){
    var el = Q(ID.tid); if(!el) return;
    var b = deliverBody();
    if(!b.task || !b.to.length){ el.textContent = '\u2014\uff08\u987b\u5148\u586b \u4ea4\u529e \uff0b \u6536\u4ef6\u4eba\uff09'; return; }
    el.textContent = taskIdOf(b.task, b.to, b.body_md);
  }
  function fmtEcho(){
    var e = Q(ID.echo); if(e) e.textContent = stopTo();
  }
  function probeBackend(){
    var el = Q(ID.back); if(!el) return;
    try{
      fetch(API + '/v9/pa/deliver/mail', { method:'GET', cache:'no-store' })
        .then(function(r){
          backendState = (r.status === 404) ? '\u540e\u7aef\u672a\u63a5\uff08HTTP 404\uff09\u21d2 \u4ea4\u4ed8\u5fc5\u8d70\u5931\u8d25\u8def'
            : (r.status === 405 ? '\u540e\u7aef\u5df2\u63a5\uff08\u552f POST \u00b7 HTTP 405\uff09'
            : ('HTTP ' + r.status + '\uff08\u7167\u5b9e\uff09'));
          if(el) el.textContent = backendState;
        })
        .catch(function(){ backendState = '\u63a2\u6d4b\u5931\u8d25\uff08\u672a\u9001\u8fbe\uff09'; if(el) el.textContent = backendState; });
    }catch(e){ backendState = '\u63a2\u6d4b\u629b\u9519\uff08' + String(e && e.message || e) + '\uff09'; if(el) el.textContent = backendState; }
  }
  function build(){
    var face = Q('paFaceTasks'); if(!face) return null;
    var box = Q(PANEL);
    if(box) return box;
    box = document.createElement('details');
    box.id = PANEL;
    box.setAttribute('data-src', SRC);
    box.style.cssText = 'flex:0 0 auto;border-top:1px solid var(--border);background:rgba(88,166,255,.03);'
      + 'max-height:52%;overflow:auto';
    box.innerHTML =
      '<summary style="cursor:pointer;padding:5px 14px;font-size:11.5px;color:var(--sub)">'
      + '\ud83d\uddc2 <b style="color:var(--text)">T1 \u4ea4\u4ed8\u9762</b>\uff08\u53d1\u4fe1 \u00b7 \u6211\u65b9\u95ed\u73af\uff09'
      + '\u00b7 \u505c\u624b\u6536\u4ef6\u4eba\uff1a<b id="' + ID.echo + '" style="color:var(--text)">\u672c\u4eba</b>'
      + '\u3000<span style="opacity:.8">\u540e\u7aef\uff1a<span id="' + ID.back + '">\u63a2\u6d4b\u4e2d\u2026</span></span></summary>'
      + '<div style="padding:6px 14px 10px;font-size:11.5px;line-height:1.75">'
      + '<div>\u26a0 <b>\u5f31\u4fdd\u8bc1</b>\uff1a\u672a\u6279 \u21d2 \u524d\u7aef\u4e0d\u53d1\uff08<b>\u524d\u7aef\u4e4b\u5f31\u4fdd\u8bc1</b>\uff09'
      + ' \u27f7 <b>\u540e\u7aef\u62d2\u6267</b>\uff08\u771f\u95f8 \u00b7 \u5728\u53d1\u4fe1\u8def\u7531\u5185\uff09\u2014\u2014 \u5f31\u4fdd\u8bc1 \u2260 \u771f\u95f8\uff08\u627f pm_071 \u00a7\u4e09\uff09\u3002</div>'
      + '<div style="' + SUB + '">\u4f53\uff1aPOST /v9/pa/deliver/mail {user_id, task_id, decision_id, to, subject, body_md}'
      + ' \u00b7 \u7f3a decision_id \u21d2 403 fail-closed \u00b7 \u91cd\u653e\u540c task_id \u21d2 \u8fd4\u65e2\u6709\u56de\u6267</div>'
      + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin:6px 0">'
      + '<textarea id="' + ID.task + '" rows="2" placeholder="\u2460 \u4ea4\u529e\uff08\u81ea\u7136\u8bed\u8a00 \u00b7 \u4e00\u53e5\u8bdd\uff09" style="' + INP + '"></textarea>'
      + '<textarea id="' + ID.body + '" rows="2" placeholder="\u6b63\u6587 body_md\uff08\u7559\u7a7a \u21d2 \u53d6\u4ea4\u529e\uff09" style="' + INP + '"></textarea>'
      + '<label style="' + SUB + '">\u6536\u4ef6\u4eba to\uff08\u591a\u4eba\u7528\u9017\u53f7\u5206\u9694 \u00b7 \u63d0\u4ea4\u65f6\u81ea\u52a8\u5f52\u4e00\u4e3a\u5217\u8868\uff09<input id="' + ID.to + '" style="' + INP + '"></label>'
      + '<label style="' + SUB + '">\u4e3b\u9898 subject<input id="' + ID.subject + '" style="' + INP + '"></label>'
      + '<label style="grid-column:1/3;color:var(--amber)">⭐ 停手收件人（默认 本人 · ⛔ 默认「无收件人」）'
      + '<input id="' + ID.stop + '" placeholder="本人（留空即本人）" style="' + INP + '"></label>'
      + '<label style="' + SUB + '">引哪封来信 · 件号（凭什么 · C1）<input id="' + ID.refNo + '" placeholder="原信之件号（留空 ⇒ 回执显「缺」）" style="' + INP + '"></label>'
      + '<label style="' + SUB + '">引哪封来信 · sha16<input id="' + ID.refSha + '" placeholder="原信 sha16（留空 ⇒ 显「缺」）" style="' + INP + '"></label>'
      + '<label style="grid-column:1/3;' + SUB + '">decision_id（拍板 · 真拍板由后端 log 读 · ⛔ 本面编号）'
      + '<input id="' + ID.dec + '" placeholder="d…（可点下方「取最新拍板」）" style="' + INP + '"></label>'
      + '<div style="grid-column:1/3;' + SUB + '">拍板来源：<span id="' + ID.decSrc + '">未取</span>'
      + ' <button id="paT1DecBtn" style="' + BTN + '">⟳ 取最新拍板（读 log）</button></div>'
      + '</div>'
      + '<div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">'
      + '<button id="' + ID.onestep + '" style="' + BTN + ';border-color:var(--green);color:var(--green)">⚡ 一句话交办（1 步）</button>'
      + '<span style="' + SUB + '">人工步数：<b id="' + ID.steps + '">0／2</b>（交办 1 ＋ 授权 1 · 目标 ≤ 2 · 手点三钮 ⇒ 超）</span>'
      + '</div>'
      + '<div style="display:flex;gap:6px;flex-wrap:wrap">'
      + '<button id="paT1PlanBtn" style="' + BTN + '">① 出计划</button>'
      + '<button id="paT1AdoptBtn" style="' + BTN + '">② 拍板（采纳）</button>'
      + '<button id="paT1DeliverBtn" style="' + BTN + '">③ 交付（发信）</button>'
      + '</div>'
      + '<div id="' + ID.out + '" class="out"></div>'
      + '<div style="' + SUB + '">task_id\uff08\u9884\u89c8 \u00b7 \u4e24\u7aef\u53ef\u590d\u7b97\uff09\uff1a<span id="' + ID.tid + '">\u2014</span></div>'
      + '<div id="' + ID.plan + '"></div>'
      + '<div id="' + ID.rc + '"></div>'
      + '</div>';
    var two = face.querySelector('.twocol');
    if(two && two.parentNode === face) face.insertBefore(box, two.nextSibling); else face.appendChild(box);
    try{
      Q('paT1PlanBtn').addEventListener('click', function(){ bumpStep('出计划（手点）'); doPlan(false); });
      Q('paT1AdoptBtn').addEventListener('click', function(){ bumpStep('拍板（手点）'); doAdopt(false); });
      Q('paT1DeliverBtn').addEventListener('click', function(){ doDeliver(false); });
      var os = Q(ID.onestep); if(os) os.addEventListener('click', function(){ doOneStep(false); });
      [ID.task, ID.body, ID.to, ID.refNo, ID.refSha].forEach(function(i){ var e = Q(i); if(e) e.addEventListener('input', fmtTaskId); });
      var st = Q(ID.stop); if(st) st.addEventListener('input', fmtEcho);
      var db = Q('paT1DecBtn'); if(db) db.addEventListener('click', function(){ loadDecision(true); });
      var de = Q(ID.dec); if(de) de.addEventListener('input', function(){ decisionId = String(de.value || '').trim(); });
    }catch(e){}
    fmtEcho(); fmtTaskId(); probeBackend(); loadDecision(false); setSteps(0, '初始');
    return box;
  }
  function go(){ try{ build(); }catch(e){} }
  try{ if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', go); else go(); }catch(e){}
  setTimeout(go, 900); setTimeout(go, 2600); setTimeout(go, 5200);
  try{ document.addEventListener('click', function(ev){ var t2 = ev.target;
    if(t2 && (t2.id === 'paMoreBtn' || (t2.closest && t2.closest('#faceTabs')))){ setTimeout(go, 60); } }, true); }catch(e){}

  /* 供报数（⛔ 用户面）：本面之面与读数（真源：HTTP ／ 后端体） */
  try{ window.paT1 = {
    info: function(){
      var pl = Q(ID.plan), rc = Q(ID.rc);
      return { mounted: !!Q(PANEL), backend: backendState,
        steps: (lastPlan && Array.isArray(lastPlan.steps)) ? lastPlan.steps.length : -1,
        human_steps: paT1Steps,
        plan_task: lastPlanTask || null,
        plan_dom_rows: pl ? pl.querySelectorAll('div').length : -1,
        decision_id: decisionId || null, task_id: lastTaskId || null,
        to: val(ID.to), stop_to: stopTo(), ref_no: val(ID.refNo), ref_sha: val(ID.refSha),
        decision_input: val(ID.dec), stop_echo: Q(ID.echo) ? String(Q(ID.echo).textContent) : null,
        tid_preview: Q(ID.tid) ? String(Q(ID.tid).textContent) : null,
        last_http: lastHttp, last_stage: lastStage || null, receipt_kind: receiptKind,
        last_stop_doc: lastStopDoc ? { '报给谁': lastStopDoc['报给谁'], '报给谁之面': lastStopDoc['报给谁之面'],
                                       '何刻': lastStopDoc['何刻'], '停在哪一步': lastStopDoc['停在哪一步'] } : null,
        receipt: rc ? String(rc.textContent || '').slice(0, 900) : null,
        stop_card_open: !!Q('paStopAsk'), at: nowStr() };
    },
    /* ⭐ API（器 ／ 复验）所驱 ⇒ probe=true ⇒ ⛔ 入 msgs（承 pm_073 §一） */
    plan: function(){ return doPlan(true); }, adopt: function(){ return doAdopt(true); },
    deliver: function(){ return doDeliver(true); }, onestep: function(){ return doOneStep(true); },
    stopTrace: function(stage){ var b = deliverBody(); return stopTrace(stage || '交付', taskIdOf(b.task, b.to, b.body_md), b); },
    refOf: refOf, spendLine: spendLine, costLine: costLine, fourItems: fourItems,
    setSteps: setSteps, steps: function(){ return paT1Steps; },
    wire: function(){ var b = deliverBody(); return payloadOf(taskIdOf(b.task, b.to, b.body_md), b); },
    taskIdOf: taskIdOf, sha256hex: sha256hex, stopTo: stopTo, stopToRaw: stopToRaw, decId: decId, setDecision: setDecision, loadDecision: loadDecision, mount: build, probe: probeBackend, src: SRC
  }; }catch(e){}
})();
