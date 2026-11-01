/* ---- 密钥（模型供应商 · 唯落本机 · ⛔ 值入屏）（CW b2a5182 · 2026-10-07 · pm_1652 令一 ·
   承 TD `50663ef` 之端 ＋ pm_1652 §一.2 守四）
   老板之授权（逐字）：「放手去做，那么等完善了，我再去净机测试」；
   完善态之判⒊（pm_1651 §二）：**密钥可「填 ／ 换 ／ 清」**（旧唯手改 `config/.env` ⇒ 界面之缺）。

   ⭐ 端（三 · 逐字 · 承 TD_1639 §一）：
     ⒜ **领令牌** `GET /v9/pa/providers/key/token` —— 唯本机（环回）⇒ 唯以 `Set-Cookie` 下
        （`HttpOnly` ／ `SameSite=Strict` ／ `Path` 限）⇒ **⛔ 入回体**（JS 读之不得）；
     ⒝ **落 ／ 清** `POST /v9/pa/providers/key`（体 `{provider, key}`；`key` 空 ／ `null` ⇒ **清**）
        ⇒ 回执**唯布尔 ＋ 面之辞**（`action` ／ `key_state` ／ `key_configured`）∧ **⛔ 值**；
     ⒞ **读数** `GET /v9/pa/providers`（既有端 · 只读）—— 名册 ＋ `key_env` ／ `key_state` ／
        `key_configured`（**唯布尔**）⇒ 界面之态之**唯一**源（承「**读一处**（`/v9/pa/providers`）·
        **动分端**（`/v9/pa/providers/key`）」· 承 pm_1641 §一.2 之新律）。

   ⭐ 守（硬 · pm_1652 §一.2 守四 ＋ §二.1）：
     ⒜ **唯落本机唯一处**（后端之 `config/.env` —— 本面唯出端 · ⛔ 自写件）；
     ⒝ **界面唯布尔**（已配 ／ 未配 ／ 不需 —— ⛔ 值 · ⛔ 掩码之首尾 —— 连 `sk-****` 之形亦 ⛔）；
     ⒞ **⛔ 值入屏 ／ ⛔ 值入 `console` ／ ⛔ 值入报错之文 ／ ⛔ 值入仓 ／ ⛔ 值入载荷**；
     ⒟ **令牌唯 Cookie 走**（⛔ 入本面之仓 —— 本面唯知「领否 ／ 何时过期」，⛔ 知值）。
   ⚠ ⛔ 触 `core/**`（TD 之域）∧ ⛔ 起停 ∧ ⛔ 出机（唯环回之端）。 */
const PA_KEY_READ = '/v9/pa/providers';
const PA_KEY_TOKEN = '/v9/pa/providers/key/token';
const PA_KEY_WRITE = '/v9/pa/providers/key';
/* 令牌之寿之安全边 —— 后端给 `expires_in`（今 180 s）⇒ 本面早 `SKEW` 视为失效（先重领 · ⛔ 静默败）。 */
const PA_KEY_SKEW_MS = 10000;
const PA_KEY_OUTLET = '去处：刷新本页重试（F5）∨ 看服务窗口之日志';

let paKeyRun = {rows: [], read_at: '', state: 'unread', sel: '', busy: false,
                tok_ok: false, tok_at: 0, tok_st: 0, msg: ''};

function paKeyEsc(s){
  return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/* ⭐ **一处定形**（纯函 · ⛔ DOM）：三态之人话 —— **唯取后端之布尔**（`key_configured`）⇒ 缺则依
   `key_state`（`configured` ／ `missing` ／ `not_required`）⇒ 皆缺 ⇒ 「态未给」（⛔ 猜「已配」）。 */
function paKeyStateText(kstate, configured){
  const s = String(kstate == null ? '' : kstate);
  if(configured === true) return '已配';
  if(s === 'not_required') return '不需（无密钥项）';
  if(configured === false) return '未配';
  if(s === 'configured') return '已配';
  if(s === 'missing') return '未配';
  return '态未给';
}

/* ⭐ **一处定形**（纯函）：常驻明书 —— 唯述「值之处」；其 `env` 之名取后端（`key_env`）⇒ ⛔ 自造其名。
   ⚠ 后端 ⛔ 给名 ⇒ 照实（⛔ 猜 ／ ⛔ 以「不需」概一切）。
   ⭐⭐ **用户面禁词 ＝ 0**（承 pm_1012 §一 ／ §二 · 判据 ＝ `selfdesc.js:193` 之 `PA_ENG_WORDS`）⇒
      本函之出 ⛔ 含 `pm_<数>` ／ `§` 等过程引用 —— **由**（我一手之实 · 2026-10-07）：抽屉之清洗器
      `paEngCleanDrawer`（`selfdesc.js:1048`）就地把 `#paMorePanel` 内之文案之引剥去，而**其径 ＝
      直改文字节之 `nodeValue`**（`:1063`）⇒ 凡以 `textContent` 为 spy 者**逮之不得**（我之器曾误判为「谜」）；
      且其剥后**留「（）」残** ⇒ 用户面之字**随刻而二**（⛔ 一处定形）⇒ 故其引**唯留源码**（本件 L2 ／ L15），⛔ 入屏。 */
function paKeyNoticeTip(p){
  if(!p) return '源：GET /v9/pa/providers（只读）';
  const env = String(p.key_env == null ? '' : p.key_env);
  return '源：GET /v9/pa/providers · 密钥之行：' + (env || '（未给）')
       + ' · 落处：本机 .env';
}
function paKeyNoticeText(p){
  if(!p || !p.id) return '密钥：先选供应商 —— 本面唯显「已配 ／ 未配 ／ 不需」（⛔ 值 · ⛔ 掩码）。';
  const env = String(p.key_env == null ? '' : p.key_env);
  if(!env) return '此供应商不需密钥（如本机 Ollama）⇒ 本面不可填 ／ 清。';
  /* ⭐ 密钥面之「不出机」**准留**（承 PM 2081 §二.3 ／ PM 2084 §一 · 照录 TD 2082 §三.2 之别义一句）：
     钥之「不出机」＝ 其值唯落你这台机器（更严之保）
     内容之「不外发」＝ ⛔ 送给他人（本机之内可存）
     ⇒ 二辞别义 · ⛔ 一名蔽二事（⛔ 与「内容 ／ 留言 ／ 附件」之族混一 · 免后手误改）。 */
  return '所填之密钥只落本机一处 · 不上屏 ／ 不留掩码 ／ 不写日志 ／ 不出机。';
}

/* ⭐ **一处定形**（纯函）：`GET /v9/pa/providers` 之 `providers[]` ⇒ 本面之行（**唯取后端 · ⛔ 造项**）。 */
function paKeyOpts(providers){
  const arr = Array.isArray(providers) ? providers : [];
  return arr.map(function(p){
    const o = p || {};
    const env = String(o.key_env == null ? '' : o.key_env);
    return {id: String(o.id == null ? '' : o.id),
            label: String(o.label || o.id || '—'),
            key_env: env,
            key_state: String(o.key_state == null ? '' : o.key_state),
            key_configured: (typeof o.key_configured === 'boolean') ? o.key_configured : null,
            need: !!env};
  }).filter(function(x){ return !!x.id; });
}

/* ⭐ **一处定形**（纯函）：可写否 —— `key_env` 在 ⇒ 可（⛔ 在 ⇒ 「不需」⇒ 停）。 */
function paKeyWritable(p){ return !!(p && p.id && p.key_env); }

/* ⭐ **一处定形**（纯函 · 形之判）：`clearing` 收「清 ⇒ 二次确认」**之后**之果（确认在 UI · ⛔ 此函）。
   ⚠ 其 `why` **⛔ 含值**（值 ⛔ 入此函 —— 承守⒞）。 */
function paKeyGate(p, raw, clearing){
  if(!p || !p.id) return {ok: false, act: null, why: '先选供应商'};
  if(!p.key_env) return {ok: false, act: null, why: '此供应商不需密钥（如本机 Ollama）'};
  if(clearing) return {ok: true, act: 'cleared', why: ''};
  if(!String(raw == null ? '' : raw).trim())
    return {ok: false, act: null, why: '密钥 ⛔ 空（填 ／ 换须有值；清 ⇒ 用「清」键）'};
  return {ok: true, act: 'set', why: ''};
}

/* ⭐ **一处定形**（纯函）：POST 之体 —— 清 ⇒ `key: null`（承后端之判「`key` 空 ／ `null` ⇒ 清」）。
   ⚠ 本函 **唯此一处**触值（其果直入 `JSON.stringify` ⇒ 入端 · ⛔ 入屏）。 */
function paKeyBody(p, raw, clearing){
  return {provider: ((p && p.id) || ''), key: (clearing ? null : String(raw == null ? '' : raw))};
}

/* ⭐ **一处定形**（纯函）：回执之人话 —— 唯取后端之 `action` ／ `key_state` ／ `key_configured`
   （⛔ 自造态 · ⛔ 含值）。 */
function paKeyMsgText(res, p){
  const o = res || {};
  const act = (o.action === 'cleared') ? '已清' : '已落';
  const nm = (p && (p.label || p.id)) || String(o.provider || '—');
  const env = (p && p.key_env) || String(o.key_env || '');
  return act + '：' + nm + ' ⇒ 态 '
       + paKeyStateText(o.key_state, o.key_configured);
}

/* ⭐ **一处定形**（纯函）：失败之面（**人话 ＋ 去处** · pm_1652 §二.1）—— ⚠ 值 ⛔ 入此函。 */
function paKeyErrFace(status, error){
  const s = Number(status || 0);
  const e = String(error == null ? '' : error).trim();
  if(s === 403) return '令牌失效（一次性令牌过期 ／ 已用）⇒ 重领令牌后再试；仍败 ⇒ ' + PA_KEY_OUTLET;
  if(s === 404 || s === 501) return '密钥界面之端本机还没挂（' + s + '）⇒ 不等于「密钥坏」';
  if(!s) return '连不上本机服务 ⇒ 看服务窗口是否在运行（不等于「密钥坏」）';
  return '密钥没落成（' + s + '）' + (e ? ('：' + e) : ' ⇒ 照实（本机没给因）') + '｜' + PA_KEY_OUTLET;
}

/* ⭐ **一处定形**（纯函）：读数之面（**照实** —— 承 L103 ／ L1052「未应答之义 ≠ 0 行之义」）。 */
function paKeyReadFace(status, j){
  const s = Number(status || 0);
  if(!s) return '连不上本机服务（供应商清单未答）⇒ 看服务窗口是否在运行';
  if(s === 404 || s === 501) return '供应商清单之端本机还没挂（' + s + '）⇒ 照实（不当「无供应商」）';
  if(!(j && j.ok === true)) return '供应商清单回了 ' + s + ' 而不合形（不当 0 项）';
  if(!Array.isArray(j.providers)) return '供应商清单回了 200 而无清单体（不猜 ／ 不当 0 项）';
  return '';
}

/* ---------- DOM（⛔ 纯函以上既毕 —— 以下凡触 DOM） ---------- */

function paKeyEl(id){ return document.getElementById(id); }

function paKeySel(){
  const arr = Array.isArray(paKeyRun.rows) ? paKeyRun.rows : [];
  for(let i = 0; i < arr.length; i++){
    if(arr[i] && arr[i].id === paKeyRun.sel) return arr[i];
  }
  return null;
}

/* 领令牌（**页面首载** ⇒ 令一）—— ⚠ 唯置 Cookie（`HttpOnly`）⇒ 本面唯记「领否 ＋ 何时过期」（⛔ 值）。 */
async function paKeyArc(){
  let st = 0, j = null;
  try{
    const r = await fetch(((typeof API !== 'undefined') ? API : '') + PA_KEY_TOKEN,
                          {cache: 'no-store', credentials: 'same-origin'});
    st = (r && r.status) ? r.status : 0;
    try{ j = await r.json(); }catch(e){ j = null; }
  }catch(e){ st = 0; j = null; }
  const ttl = (j && j.ok === true && Number(j.expires_in) > 0) ? Number(j.expires_in) : 0;
  paKeyRun.tok_ok = (ttl > 0);
  paKeyRun.tok_at = Date.now() + ttl * 1000;
  paKeyRun.tok_st = st;
  return paKeyRun.tok_ok;
}

function paKeyTokFresh(){
  return !!(paKeyRun.tok_ok && (paKeyRun.tok_at - Date.now()) > PA_KEY_SKEW_MS);
}

/* select 之填（**幂等**：唯「项之集合」变时重建 —— 承 bdb6392 之哨 ⇒ F5 ／ 重渲 ⛔ 倍增）。 */
function paKeyFill(){
  const sel = paKeyEl('paKeyProv');
  if(!sel) return;
  const rows = Array.isArray(paKeyRun.rows) ? paKeyRun.rows : [];
  const sig = rows.map(function(r){ return r.id; }).join(',');
  if(sel.getAttribute('data-sig') !== sig){
    sel.innerHTML = rows.map(function(r){
      return '<option value="' + paKeyEsc(r.id) + '">'
           + paKeyEsc(r.label + '（' + r.id + '）') + '</option>';
    }).join('');
    sel.setAttribute('data-sig', sig);
  }
  if(!paKeySel() && rows.length) paKeyRun.sel = rows[0].id;
  if(sel.value !== paKeyRun.sel) sel.value = paKeyRun.sel;
}

/* 渲（**幂等** · ⛔ 值 · ⛔ 掩码）。 */
function paKeyPaint(){
  paKeyFill();
  const p = paKeySel();
  const nt = paKeyEl('paKeyNotice');
  if(nt){
    nt.textContent = (paKeyRun.state === 'unread') ? '密钥之去处明书：读数中…' : paKeyNoticeText(p);
    nt.title = paKeyNoticeTip(p);
  }
  const now = paKeyEl('paKeyNow');
  if(now) now.textContent = p ? ('态 ' + paKeyStateText(p.key_state, p.key_configured)) : '态 —（未选）';
  const msg = paKeyEl('paKeyMsg');
  if(msg){ msg.textContent = paKeyRun.msg ? String(paKeyRun.msg) : ''; msg.title = paKeyRun.msg ? '' : ''; }
  const bSet = paKeyEl('paKeySet'), bClr = paKeyEl('paKeyClear');
  const w = paKeyWritable(p);
  if(bSet){
    bSet.textContent = (p && p.key_configured === true) ? '换' : '填';
    bSet.disabled = !(w && !paKeyRun.busy);
    bSet.setAttribute('title', w ? ('填 ／ 换 ⇒ POST /v9/pa/providers/key（唯落本机 · ⛔ 值上屏）')
                                 : '此供应商 ⛔ 需密钥（如本机 Ollama）');
  }
  if(bClr){
    bClr.disabled = !(w && p && p.key_configured === true && !paKeyRun.busy);
    bClr.setAttribute('title', (w && p && p.key_configured === true)
      ? '清 ⇒ 二次确认 ∧ POST（key: null）—— 删其行'
      : '唯「已配」方可清（后端之布尔）');
  }
  return p;
}

function paKeyPick(id){
  paKeyRun.sel = String(id == null ? '' : id);
  paKeyRun.msg = '';
  paKeyPaint();
  return paKeySel();
}

async function paKeyLoad(){
  const at = new Date().toLocaleString('zh-CN', {hour12: false});
  let st = 0, j = null;
  try{
    const r = await fetch(((typeof API !== 'undefined') ? API : '') + PA_KEY_READ, {cache: 'no-store'});
    st = (r && r.status) ? r.status : 0;
    try{ j = await r.json(); }catch(e){ j = null; }
  }catch(e){ st = 0; j = null; }
  paKeyRun.read_at = at;
  const face = paKeyReadFace(st, j);
  if(face){
    paKeyRun.state = 'bad'; paKeyRun.rows = []; paKeyRun.sel = ''; paKeyRun.msg = face;
  }else{
    paKeyRun.state = 'ok';
    paKeyRun.rows = paKeyOpts(j.providers);
    if(!paKeySel()) paKeyRun.sel = paKeyRun.rows.length ? paKeyRun.rows[0].id : '';
  }
  paKeyPaint();
  return paKeyRun.rows;
}

/* 落 ／ 清（`clearing` 真 ⇒ 先二次确认）。⚠ 值唯经 `paKeyBody` 入体；发毕**即清框**。 */
async function paKeySend(clearing){
  const p = paKeySel();
  const el = paKeyEl('paKeyVal');
  const raw = el ? String(el.value == null ? '' : el.value) : '';
  const g = paKeyGate(p, raw, clearing);
  if(!g.ok){ paKeyRun.msg = '⛔ ' + g.why; paKeyPaint(); return null; }
  if(clearing){
    const nm = (p && (p.label || p.id)) || '—';
    let yes = false;
    if(typeof window !== 'undefined' && window.confirm){
      yes = window.confirm('清「' + nm + '」之密钥行（' + (p.key_env || '—') + '）？\n\n'
                         + '此动删后端 .env 之其行 ⇒ 该供应商即不可用（可再填）。继续？');
    }
    if(!yes){ paKeyRun.msg = '清：已取消（⛔ 未发端）'; paKeyPaint(); return null; }
  }
  paKeyRun.busy = true;
  paKeyRun.msg = clearing ? '清中…（唯落本机）' : '落中…（唯落本机）';
  paKeyPaint();
  if(!paKeyTokFresh()) await paKeyArc();
  let st = 0, j = null;
  try{
    const r = await fetch(((typeof API !== 'undefined') ? API : '') + PA_KEY_WRITE, {
      method: 'POST', cache: 'no-store', credentials: 'same-origin',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(paKeyBody(p, raw, clearing))
    });
    st = (r && r.status) ? r.status : 0;
    try{ j = await r.json(); }catch(e){ j = null; }
  }catch(e){ st = 0; j = null; }
  paKeyRun.busy = false;
  if(el) el.value = '';                       /* ⭐ 值之清（⛔ 留屏 · ⛔ 留于 DOM） */
  if(j && j.ok === true){
    paKeyRun.msg = paKeyMsgText(j, p) + ((j.落 && j.落.件) ? ('｜件 ' + String(j.落.件)) : '');
  }else{
    paKeyRun.msg = paKeyErrFace(st, (j && (j.error || j.message)) ? String(j.error || j.message) : '');
  }
  await paKeyLoad();
  paKeyPaint();
  return j;
}

/* ---- P3-2：外部运行时 · DSH 向导（只读检测 ＋ 路径保存；本地不支持明书） ---- */
function paDshEl(id){ return document.getElementById(id); }
function paDshEsc(v){
  return String(v == null ? '' : v).replace(/[&<>"']/g, function(c){
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
  });
}
function paDshSetStatus(t){ var el=paDshEl('paDshStatus'); if(el) el.textContent=String(t == null ? '' : t); }
let paDshLast = null;
let paDshBusy = false;

function paDshBtn(id, show){ var b = paDshEl(id); if(b) b.hidden = !show; }
function paDshBusySet(v){
  paDshBusy = !!v;
  var b = paDshEl('paDshBtnRetry'); if(b) b.disabled = !!v;
  var s = paDshEl('paDshPathSaveBtn'); if(s) s.disabled = !!v;
}
function paDshLoad(force){
  if(paDshBusy) return Promise.resolve(null);
  paDshBusySet(true);
  paDshSetStatus(force
    ? '重新检测中…（只探测 dsh 可执行文件，不安装、不执行任务）'
    : '读数中…（GET /v9/pa/runtimes/dsh）');
  return fetch(API + '/v9/pa/runtimes/dsh', {cache: 'no-store'})
    .then(function(r){ return r.json().then(function(j){ return {status: r.status, j: j}; }); })
    .then(function(x){
      var d = x.j || {};
      if(x.status !== 200 || d.ok !== true){
        paDshSetStatus('检测失败（' + x.status + '）：' + (d.error || '后端未给因'));
        paDshBtn('paDshBtnCloud', false);
        paDshBtn('paDshBtnLocal', false);
        paDshBusySet(false);
        return d;
      }
      paDshLast = d;
      var found = d.found === true;
      var src = {env:'环境变量 PA_DSH_PATH', saved:'已保存路径', which:'PATH 中 dsh', none:'—'}[d.source] || (d.source || '—');
      paDshSetStatus(found
        ? ('已找到 DSH：' + (d.path || '—') + '（' + (d.version || '版本未给') + '）· 来源：' + src + ' · 只探测到文件，尚未配置')
        : '未找到 DSH 可执行文件 —— 可装后点「重新检测」，或点「填写 dsh 路径」指到本机 dsh；本地 provider 当前不支持。');
      var body = paDshEl('paDshBody');
      if(body){
        body.innerHTML =
          '<div class="pa-dsh-row">路径：' + paDshEsc(d.path || '—') + '</div>'
          + '<div class="pa-dsh-row">版本：' + paDshEsc(d.version || '—') + ' · 来源：' + paDshEsc(src) + '</div>'
          + '<div class="pa-dsh-row">云端 API：' + (d.cloud_supported === true ? '支持' : '不支持') + '（DSH 独立 key）· key：'
          + (d.key_present === true ? '✓ 已配（DSH 独立）' : '未配（在下方「DSH 云端 key」单独填；PA 供应商密钥不喂 DSH）') + '</div>'
          + '<div class="pa-dsh-row">本地模型：<b>当前不支持</b>（DSH 本地 provider 未支持；PA 本地 Ollama 已可用' + (d.local_supported === true ? ' · 后端 local_supported=true 与向导口径冲突' : '') + '）</div>'
          + '<div class="pa-dsh-row">Node：' + (d.node_present === true ? '已安装' : '未安装（装 DSH 需 Node）') + '</div>'
          + (found ? '<div class="pa-dsh-row" style="color:var(--sub)">下一步：点「配置云端」＝ 切到 DeepSeek 并打开密钥框（只切 ／ 只开，不发送）；点「使用本地」＝ 只看现状说明。</div>' : '');
      }
      paDshBtn('paDshBtnCloud', found);
      paDshBtn('paDshBtnLocal', found);
      var steps = paDshEl('paDshSteps');
      if(steps){
        var arr = Array.isArray(d.install_steps) ? d.install_steps : [];
        steps.innerHTML = arr.map(function(s){ return '<li>' + paDshEsc(s) + '</li>'; }).join('');
      }
      paDshBusySet(false);
      return d;
    })
    .catch(function(e){
      paDshSetStatus('检测失败（未达本机服务）：' + ((e && e.message) || e));
      paDshBtn('paDshBtnCloud', false);
      paDshBtn('paDshBtnLocal', false);
      paDshBusySet(false);
    });
}
function paDshRetry(){ if(paDshBusy) return; return paDshLoad(true); }
function paDshPath(){
  var row = paDshEl('paDshPathRow'); if(!row) return;
  row.hidden = false;
  var msg = paDshEl('paDshPathMsg'); if(msg) msg.textContent = '';
  var inp = paDshEl('paDshPathIn');
  if(inp){
    if(!inp.value && paDshLast && paDshLast.path) inp.value = String(paDshLast.path);
    try{ inp.focus(); if(inp.select) inp.select(); }catch(e){}
  }
}
function paDshPathCancel(){
  var row = paDshEl('paDshPathRow'); if(row) row.hidden = true;
  var msg = paDshEl('paDshPathMsg'); if(msg) msg.textContent = '';
}
function paDshPathSave(){
  if(paDshBusy) return;
  var inp = paDshEl('paDshPathIn');
  var p = inp ? String(inp.value == null ? '' : inp.value).trim() : '';
  var msg = paDshEl('paDshPathMsg');
  if(!p){
    if(msg) msg.textContent = '请先填 dsh 可执行文件的绝对路径（例：D:\\npm-global\\dsh.CMD）';
    try{ if(inp) inp.focus(); }catch(e){}
    return;
  }
  paDshBusySet(true);
  if(msg) msg.textContent = '保存并探测中…';
  return fetch(API + '/v9/pa/runtimes/dsh/path', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({path: p})
  }).then(function(r){ return r.json().then(function(j){ return {status: r.status, j: j}; }); })
    .then(function(x){
      if(x.status !== 200 || !x.j || x.j.ok !== true){
        var why = (x.j && (x.j.error || x.j.code)) || '后端未给因';
        if(msg) msg.textContent = '没保存成（' + x.status + '）：' + why + ' —— 路径须为本机真实存在的 dsh 可执行文件';
        paDshBusySet(false);
        return;
      }
      if(msg) msg.textContent = '已保存：' + (x.j.path || p);
      paDshBusySet(false);
      var row = paDshEl('paDshPathRow'); if(row) row.hidden = true;
      return paDshLoad(true);
    })
    .catch(function(e){
      if(msg) msg.textContent = '没保存成（连不上本机服务）：' + ((e && e.message) || e);
      paDshBusySet(false);
    });
}
async function paDshCloud(){
  var inp = paDshEl('paDshKeyIn');
  if(inp){
    try{ inp.scrollIntoView({block:'center'}); inp.focus(); }catch(e){}
  }
  paDshSetStatus('云端：DSH 使用自己的独立 key；请在下方的「DSH 云端 key」填写（不是上方 PA 供应商密钥）。填完点「填 DSH key」，PA 会把它写入 dsh.env 并只传给 DSH 子进程。');
}
async function paDshKeySave(){
  var inp = paDshEl('paDshKeyIn');
  var msg = paDshEl('paDshKeyMsg');
  var key = inp ? String(inp.value == null ? '' : inp.value).trim() : '';
  if(!key){ if(inp) inp.focus(); if(msg) msg.textContent = '先粘贴 DSH 的 DeepSeek API key（sk-…）'; return; }
  if(msg) msg.textContent = '写入 DSH 独立凭据…';
  try{
    var r = await fetch(API + '/v9/pa/harness/key', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({key: key})});
    var d = await r.json().catch(function(){ return null; });
    if(!r.ok || !d || d.ok === false){
      if(msg) msg.textContent = '写入失败：' + String((d && (d.message || d.error)) || ('HTTP ' + r.status));
      return;
    }
    if(inp) inp.value = '';
    if(msg) msg.textContent = '已写入 DSH 独立凭据（不回显）';
    return paDshLoad(true);
  }catch(e){ if(msg) msg.textContent = '写入失败：' + String((e && e.message) || e); }
}
async function paDshKeyClear(){
  var msg = paDshEl('paDshKeyMsg');
  try{
    await fetch(API + '/v9/pa/harness/key', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({clear: true})});
    if(msg) msg.textContent = '已清 DSH 独立凭据';
    return paDshLoad(true);
  }catch(e){ if(msg) msg.textContent = '清除失败：' + String((e && e.message) || e); }
}
function paDshLocal(){
  paDshSetStatus('本地：PA 自己的本地 Ollama 已可用（在「模型配置」里选它即可）；DSH 的本地 provider 目前未支持 —— 向导不假装可用，也不替你安装。只想本机对话时，不用 DSH。');
}

function paKeyOpen(){
  if(typeof paMore === 'function'){ try{ paMore(true); }catch(e){} }
  const g = paKeyEl('paMoreGrpSet'); if(g) g.setAttribute('open', '');
  setTimeout(function(){
    const s = paKeyEl('paKeys');
    if(s && s.scrollIntoView){ try{ s.scrollIntoView({block: 'start'}); }catch(e){} }
    const v = paKeyEl('paKeyVal'); if(v && v.focus){ try{ v.focus(); }catch(e){} }
  }, 60);
  return paKeyEl('paKeys');
}

/* 页面首载（`boot.js` 之 `_boot` —— 令一「页面首载领令牌」）：先领令牌，再读名册。 */
function paKeyInit(){
  paKeyArc();
  return paKeyLoad();
}
