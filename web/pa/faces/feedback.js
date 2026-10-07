/* ---- 留言板（丙-P0 之面 · 内测形）（CW b2a5182 · 2026-10-07 · pm_1635 ＋ pm_1641 §二 · 承 TD_1634 ／ 1639 之端）
   老板之批（逐字）：「批，增加留言板，先用局域网内测，但是客服 Agent 需要跟上」。
   ⭐ 三守（pm_1635 §二）：
     ⒜ **「⛔ 出机」之常驻明书 ⇒ 唯取后端 `notice` 之逐字**（⛔ 前端自撰其辞）；
     ⒝ **逐项勾选 ⇒ 唯取后端 `consent_buses`** ∧ **默认全关**（⛔ 一个「全选」之便键）；
     ⒞ **⛔ 书「在线客服」四字**（内测期 ⛔ 有）；**「回话」照今日原型之黄框**（其位在收件之上）。
   ⭐ 端（pm_1641 裁 ① 之新律「**读一处（`/health`）· 动分端（`/v9/pa/*`）**」）：
     读数（`notice` ／ `consent_buses` ／ 落点之径）⇒ `GET /health` 之 `feedback` 键
       —— ⚠ **⛔ 引 `/v9/pa/feedback/target`**（其形与 `/health.feedback` **同一处** 出 · 承 TD_1639 §四.1
       ＋ pm_1641 §一.3「面唯读 `/health`」）；
     动 ⇒ `POST /v9/pa/feedback`（收件）／ `GET /v9/pa/feedback`（取件之列）／ `GET /v9/pa/feedback/<id>`（详）。
   ⭐ 铁律：**本面 ⛔ 任何出站之件**（所发唯本机之端 —— 其证 ＝ 验收⒉ 之「真浏览器网络录」＋ 结构齿）。
   ⚠ ⛔ 触 `core/**`（TD 之域）∧ ⛔ `localStorage` 之态（承 pm_1617 令五：⛔ 前端缓存之假态）。 */
const PA_FB_READ = '/health';
const PA_FB_SEND = '/v9/pa/feedback';
const PA_FB_LIST = '/v9/pa/feedback';
const PA_FB_ITEM = '/v9/pa/feedback/';
const PA_FB_POLL_MS = 30000;
const PA_FB_OUTLET = '去处：重试 ∨ 看服务窗口之日志（安装目录之「启动 ／ 停止」快捷）';
/* 横幅（`#paPrep`）之回执时限 —— 已成 ⇒ 短（免恒挂 —— 承「⛔ 无等待亦挂」之反）；
   已败 ⇒ 长（够读完「因 ＋ 去处」）。 */
const PA_FB_BANNER_TTL_MS = 8000;
const PA_FB_BANNER_FAIL_MS = 30000;

/* 逐项勾选之人话（⛔ 在表 ⇒ **照实显原值** —— 承「界面态显真读数」· ⛔ 造相）。
   ⚠ 其项（`health` ／ `logs` ／ `env` ／ `diag`）之真源 ＝ 后端 `consent_buses`（⛔ 此处自造其项）。 */
const PA_FB_BUS = {health: '健康读数', logs: '日志尾', env: '环境摘要', diag: '诊断包'};

function paFbEsc(s){
  return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
function paFbBusLabel(b){
  const s = String(b);
  return PA_FB_BUS[s] ? PA_FB_BUS[s] : s;
}

/* ⭐ **一处定形**（纯函数 · ⛔ DOM）：`/health` 之回 ⇒ 落点之形（读数唯取 `feedback` 键 —— 承 pm_1641 裁 ①）。 */
function paFbTarget(h){
  const o = {state: 'unanswered', notice: '', buses: [], outbound: null,
             mode: '', channel: '', dir: '', resolved_dir: '', note: ''};
  const f = (h && typeof h === 'object' && h.feedback && typeof h.feedback === 'object') ? h.feedback : null;
  if(!f) return o;
  o.state = 'ok';
  o.notice = (f.notice == null) ? '' : String(f.notice).trim();
  o.outbound = (typeof f.outbound === 'boolean') ? f.outbound : null;
  o.mode = String(f.mode || ''); o.channel = String(f.channel || '');
  o.dir = String(f.dir || ''); o.resolved_dir = String(f.resolved_dir || '');
  o.note = (f.note == null) ? '' : String(f.note).trim();
  const bs = Array.isArray(f.consent_buses) ? f.consent_buses : [];
  o.buses = bs.map(function(x){ return String(x == null ? '' : x).trim(); })
              .filter(function(x){ return !!x; });
  return o;
}

/* ⭐ **一处定形**（**常驻明书** · pm_1635 §二.2）：唯取后端 `notice` 之逐字（⛔ 自撰其辞）；
   ⛔ 给 ⇒ **明书「后端未给」**（照实 · 承「未知 ⛔ 充知」）∧ 由 `paFbGate` 停发。 */
function paFbNoticeText(t){
  if(!t || t.state !== 'ok') return '留言板未答：后端未给落点之声明（⛔ 自撰 —— 候后端）';
  if(t.notice) return t.notice;
  return '后端未给「内容出机 ∨ 不出机」之明书 —— ⛔ 自撰（故停发：候后端）';
}

/* ⭐ **一处定形**（**可发之判**）：读数 ⇒ `notice`（⛔ 无 ⇒ 停发 · 因 ⛔ 知是否出机）∧
   `outbound === true` ⇒ ③ **同意之口**（其位先留 · 承 pm_1635 §二.2「将来接中转 ⇒ 其辞须变 ＋ 其同意之口」）。 */
function paFbGate(t, agreed, sending, form){
  if(sending) return {ok: false, why: '发送中…'};
  if(!t || t.state !== 'ok') return {ok: false, why: '留言板未答（后端未给落点之声明）⇒ ⛔ 发'};
  if(!t.notice) return {ok: false, why: '后端未给「出机」之明书 ⇒ 停发（候后端）'};
  /* ⭐ 形之判 ⇒ **照后端 `feedback_store.submit` 之实**（题必填 ∧ 文必填 —— 后端拒收之人话亦即此）——
     ⛔ 前端自拟其则 ∧ ⛔ 由后端之败来「教」用户（承「凡面之支须能真达」）。 */
  const _f = (form && typeof form === 'object') ? form : {};
  if(!String(_f.title == null ? '' : _f.title).trim()) return {ok: false, why: '题必填（后端之判：⛔ 题 ⇒ 拒收）'};
  if(!String(_f.body == null ? '' : _f.body).trim()) return {ok: false, why: '说明必填（后端之判：⛔ 文 ⇒ 拒收）'};
  if(t.outbound === true && !agreed) return {ok: false, why: '内容将出机 ⇒ 须先勾「同意出机」（其位先留）'};
  return {ok: true, why: ''};
}

/* 勾选之显（唯取 `consent_buses` · 逐项 ∧ 默认全关 —— ⛔ 自造其项 ／ ⛔ 一个「全选」之便键）。 */
function paFbBusTags(t, consent){
  const c = (consent && typeof consent === 'object') ? consent : {};
  const out = [];
  const bs = (t && Array.isArray(t.buses)) ? t.buses : [];
  for(let i = 0; i < bs.length; i++){
    out.push({bus: bs[i], label: paFbBusLabel(bs[i]) + '（此项将随件）', on: (c[bs[i]] === true)});
  }
  return out;
}

/* 「我之收件」之痕（唯本机之读数 —— 条数 ／ 最近之刻 ／ 落点之径 · ⛔ 造）。 */
function paFbItemsText(items, t){
  const its = Array.isArray(items) ? items : [];
  const d = (t && (t.resolved_dir || t.dir)) ? (t.resolved_dir || t.dir) : '';
  let s = '我之收件：' + its.length + ' 条';
  if(its.length && its[0] && its[0].at) s += '（最近 ' + String(its[0].at) + '）';
  s += ' · 落点 ' + (d || '（后端未给）');
  return s;
}

/* 回话之辞（照今日原型之黄框 · **唯取后端 `reply`** —— ⛔ 自造其辞；⛔ 有 ⇒ 空 ⇒ 黄框 ⛔ 显）。 */
function paFbReplyText(item){
  const r = (item && item.reply && typeof item.reply === 'object') ? item.reply : null;
  const tx = r ? String(r.text || '').trim() : '';
  if(!tx) return '';
  return '客服席回话（' + String(r.by || '客服席') + ' · ' + String(r.at || '') + '）：' + tx;
}

/* 发之三态（空 ／ 发送中 ／ 已成（落点之径）／ 已败（因 ＋ 去处）—— ⛔ 白屏 ∧ ⛔ 死路）。 */
function paFbSendText(st, t){
  if(!st || !st.state) return '';
  if(st.state === 'sending') return '发送中…';
  if(st.state === 'ok'){
    const d = (t && (t.resolved_dir || t.dir)) ? (t.resolved_dir || t.dir) : '';
    let s = '已落本机：' + (d ? (d + '/' + st.id) : String(st.id));
    if(st.at) s += '（' + String(st.at) + '）';
    if(st.hint) s += ' · ' + String(st.hint);
    return s;
  }
  if(st.state === 'fail') return '发送失败：' + (st.error || '（后端未给因）') + ' · ' + PA_FB_OUTLET;
  return '';
}

/* ---- 以下：态 ＋ 渲 ＋ 取数（**唯此处**写 `#paFeedback` 之内；幂等：⛔ 加节点 · 唯改文本 ／ 值 ／ 属性） ---- */
const paFbRun = {started: false, t: null, items: [], sel: null, send: null,
                 agreed: false, consent: {}, files: [], busy: false, poll: null, http: null,
                 bannerT: null, autoPicked: false};

function paFbEl(id){ return document.getElementById(id); }

function paFbConsentFromDom(){
  const out = {};
  const box = paFbEl('paFbBuses');
  if(!box) return out;
  const ins = box.querySelectorAll('input[type=checkbox][data-bus]');
  for(let i = 0; i < ins.length; i++){ out[ins[i].getAttribute('data-bus')] = !!ins[i].checked; }
  return out;
}

/* 形之读（唯读 DOM ⇒ 供 `paFbGate` 判「可发」—— ⛔ 另存态 ⇒ 免与「勾选 ／ 附件」之态纠缠）。 */
function paFbFormFromDom(){
  const a = paFbEl('paFbTitle'), b = paFbEl('paFbBody');
  return {title: a ? a.value : '', body: b ? b.value : ''};
}

function paFbRender(){
  const t = paFbRun.t;
  const nt = paFbEl('paFbNotice'); if(nt) nt.textContent = paFbNoticeText(t);
  /* ③ 同意之口（其位先留 —— 唯 `outbound === true` 方显） */
  const aw = paFbEl('paFbAgreeWrap');
  if(aw){
    const need = !!(t && t.state === 'ok' && t.outbound === true);
    aw.hidden = !need;
    if(need){
      const lb = paFbEl('paFbAgreeLb');
      if(lb) lb.textContent = '内容将出机（后端 `outbound=true`）⇒ 我同意此落点';
      const c = paFbEl('paFbAgree');
      if(c && c.checked !== paFbRun.agreed) c.checked = !!paFbRun.agreed;
    }
  }
  /* 勾选（⛔ 重建其项 ⇒ 唯「项之集合」变时重建；勾之态另同步 ⇒ 幂等） */
  const box = paFbEl('paFbBuses');
  if(box){
    const bs = (t && Array.isArray(t.buses)) ? t.buses : [];
    const sig = bs.join(',');
    if(box.getAttribute('data-sig') !== sig){
      box.innerHTML = bs.map(function(b){
        return '<label class="fb-bus"><input type="checkbox" data-bus="' + paFbEsc(b) + '">' +
               paFbEsc(paFbBusLabel(b) + '（此项将随件）') + '</label>';
      }).join('');
      box.setAttribute('data-sig', sig);
    }
    const ins = box.querySelectorAll('input[data-bus]');
    for(let i = 0; i < ins.length; i++){
      const on = !!(paFbRun.consent && paFbRun.consent[ins[i].getAttribute('data-bus')] === true);
      if(ins[i].checked !== on) ins[i].checked = on;
    }
  }
  const al = paFbEl('paFbAttList');
  if(al){
    const fs = Array.isArray(paFbRun.files) ? paFbRun.files : [];
    al.textContent = fs.length
      ? ('附件 ' + fs.length + ' 件：' + fs.map(function(f){ return String(f.name); }).join(' ／ '))
      : '（无附件）';
  }
  const g = paFbGate(t, paFbRun.agreed, paFbRun.busy, paFbFormFromDom());
  const st = paFbEl('paFbState');
  if(st) st.textContent = paFbRun.send ? paFbSendText(paFbRun.send, t) : (g.ok ? '' : g.why);
  const sb = paFbEl('paFbSend');
  if(sb){
    sb.disabled = !g.ok;
    sb.setAttribute('title', g.ok ? '发送 ⇒ POST /v9/pa/feedback（落**本机** · ⛔ 出站）' : g.why);
  }
  const li = paFbEl('paFbItems');
  if(li){
    const its = Array.isArray(paFbRun.items) ? paFbRun.items : [];
    let html = paFbEsc(paFbItemsText(its, t));
    for(let i = 0; i < its.length && i < 10; i++){
      const x = its[i] || {};
      html += '<div class="fb-item" data-fid="' + paFbEsc(String(x.id || '')) + '">' +
              paFbEsc(String(x.at || '') + ' · ' + String(x.title || '') +
                      '（' + (x.has_reply ? '有回话' : '无回话') + ' · 附件 ' +
                      ((x.attach_n == null) ? '—' : String(x.attach_n)) + '）') + '</div>';
    }
    if(li.getAttribute('data-sig') !== html){ li.innerHTML = html; li.setAttribute('data-sig', html); }
  }
  const rp = paFbEl('paFbReply');
  if(rp){
    const tx = paFbReplyText(paFbRun.sel);
    rp.hidden = !tx;
    if(tx && rp.textContent !== tx) rp.textContent = tx;
  }
  return t;
}

function paFbReadFiles(list, done){
  const out = []; let i = 0;
  function step(){
    if(i >= list.length){ done(out); return; }
    const f = list[i]; i += 1;
    const fr = new FileReader();
    fr.onload = function(){
      const s = String(fr.result || ''); const k = s.indexOf(',');
      out.push({name: String(f.name || ('附件' + i)), b64: (k >= 0 ? s.slice(k + 1) : '')});
      step();
    };
    fr.onerror = function(){ out.push({name: String(f.name || ('附件' + i)), b64: ''}); step(); };
    try{ fr.readAsDataURL(f); }catch(e){ out.push({name: String(f.name || ('附件' + i)), b64: ''}); step(); }
  }
  step();
}

async function paFbFetch(){
  let h = null;
  try{
    const r = await fetch(((typeof API !== 'undefined') ? API : '') + PA_FB_READ, {cache: 'no-store'});
    paFbRun.http = (r && r.status) ? r.status : 0;
    if(r && r.ok){ try{ h = await r.json(); }catch(e){ h = null; } }
  }catch(e){ h = null; paFbRun.http = 0; }
  paFbRun.t = paFbTarget(h);
  if(paFbRun.t.state === 'ok'){
    try{
      const r2 = await fetch(((typeof API !== 'undefined') ? API : '') + PA_FB_LIST, {cache: 'no-store'});
      const j2 = (r2 && r2.ok) ? await r2.json() : null;
      paFbRun.items = (j2 && Array.isArray(j2.items)) ? j2.items : [];
    }catch(e){ paFbRun.items = []; }
    /* ⭐ 回话之**自显**（承 pm_1635 §二.4「客服 Agent 须跟上」）：首取若最新件**已有回话** ∧
       未择 ⇒ 自取其详（唯 **1** 次 ⇒ ⛔ 每轮重取；⛔ 无回话则 ⛔ 取）。 */
    if(!paFbRun.autoPicked){
      paFbRun.autoPicked = true;
      const i0 = (paFbRun.items && paFbRun.items[0]) ? paFbRun.items[0] : null;
      if(i0 && i0.id && i0.has_reply && !paFbRun.sel){ await paFbOpenItem(i0.id); }
    }
  }
  paFbRender();
  return paFbRun.t;
}

async function paFbSend(){
  const t = paFbRun.t;
  const g = paFbGate(t, paFbRun.agreed, paFbRun.busy, paFbFormFromDom());
  if(!g.ok){ paFbRun.send = {state: 'fail', error: g.why}; paFbRender(); paFbFeedBanner(); return paFbRun.send; }
  const elT = paFbEl('paFbTitle'), elB = paFbEl('paFbBody');
  const consent = paFbConsentFromDom();
  paFbRun.consent = consent;
  paFbRun.busy = true; paFbRun.send = {state: 'sending'}; paFbRender(); paFbFeedBanner();
  let st = 0, j = null;
  try{
    const r = await fetch(((typeof API !== 'undefined') ? API : '') + PA_FB_SEND, {
      method: 'POST', cache: 'no-store', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({title: (elT ? elT.value : ''), body: (elB ? elB.value : ''),
                            kind: '反馈', consent: consent,
                            attach: (paFbRun.files || []).map(function(f){
                              return {name: f.name, b64: f.b64};
                            })})
    });
    st = (r && r.status) ? r.status : 0;
    try{ j = await r.json(); }catch(e){ j = null; }
  }catch(e){ st = 0; j = null; }
  paFbRun.busy = false;
  if(j && j.ok === true && j.id){
    paFbRun.send = {state: 'ok', id: String(j.id), at: String(j.at || ''), hint: String(j.hint || '')};
    paFbRun.files = []; paFbRun.sendOuted = true;
    const fEl = paFbEl('paFbFiles'); if(fEl) fEl.value = '';
    if(elT) elT.value = '';
    if(elB) elB.value = '';
    await paFbFetch();
  }else{
    paFbRun.send = {state: 'fail',
      error: ((j && (j.error || j.message)) ? String(j.error || j.message)
                                            : ('（后端未给因 · HTTP ' + st + '）'))};
  }
  paFbRender(); paFbFeedBanner();
  return paFbRun.send;
}

async function paFbOpenItem(fid){
  try{
    const r = await fetch(((typeof API !== 'undefined') ? API : '') + PA_FB_ITEM +
                          encodeURIComponent(String(fid)), {cache: 'no-store'});
    const j = (r && r.ok) ? await r.json() : null;
    paFbRun.sel = (j && j.item) ? j.item : null;
  }catch(e){ paFbRun.sel = null; }
  paFbRender();
  return paFbRun.sel;
}

/* ⭐ **一处定形**（横幅之读数 · pm_1635 §一.3「三面 ⇒ 一幅横幅」· ⛔ 三横幅）：本函唯**算**
   （纯函 · ⛔ DOM）；其渲归 `startup.js` 之 `paPrepRender` 一处 —— 唯经 `paPrepFeedFeedback` 投。
   反馈 → 横幅：发送中 ⇒ `running`；已成 ⇒ `done`（落点之径）；已败 ⇒ `failed`（因 ＋ 去处）。
   ⚠ 其位 ＝ **最低**优先级（put · `paPrepMerge` 之末判）⇒ 唯「他事皆无」时显。 */
function paFbBannerView(st, t){
  if(!st || !st.state) return null;
  const d = (t && (t.resolved_dir || t.dir)) ? (t.resolved_dir || t.dir) : '';
  if(st.state === 'sending') return {state: 'running', text: '正在发送留言…（落本机 · ⛔ 出机）', note: ''};
  if(st.state === 'ok') return {state: 'done',
      text: '留言已落本机：' + (d ? (d + '/' + String(st.id)) : String(st.id)),
      note: '内测 · ⛔ 出机：我们上门取 ∨ 你自己复给我们'};
  if(st.state === 'fail') return {state: 'failed',
      text: '留言未发出：' + (st.error || '（后端未给因）'), note: PA_FB_OUTLET};
  return null;
}

/* 投于横幅（**唯一之投入点** · ⛔ 自渲）；已成 ／ 已败 ⇒ 有时限（免恒挂）。 */
function paFbFeedBanner(){
  const v = paFbBannerView(paFbRun.send, paFbRun.t);
  if(paFbRun.bannerT){ try{ clearTimeout(paFbRun.bannerT); }catch(e){} paFbRun.bannerT = null; }
  if(typeof paPrepFeedFeedback === 'function') paPrepFeedFeedback(v);
  if(v && (v.state === 'done' || v.state === 'failed')){
    const ms = (v.state === 'done') ? PA_FB_BANNER_TTL_MS : PA_FB_BANNER_FAIL_MS;
    paFbRun.bannerT = setTimeout(function(){
      paFbRun.bannerT = null; paFbRun.send = null; paFbFeedBanner(); paFbRender();
    }, ms);
  }
  return v;
}

/* 「一步可达」（承 pm_997 §四 · 式同 `paSettings`）：开「更多」⇒ 开 ③ 组 ⇒ 滚到本面 ⇒ 焦点入「文」。 */
function paFbOpen(){
  if(typeof paMore === 'function'){ try{ paMore(true); }catch(e){} }
  const g = paFbEl('paMoreGrpSet'); if(g) g.setAttribute('open', '');
  setTimeout(function(){
    const s = paFbEl('paFeedback');
    if(s && s.scrollIntoView){ try{ s.scrollIntoView({block: 'start'}); }catch(e){} }
    const b = paFbEl('paFbBody'); if(b && b.focus){ try{ b.focus(); }catch(e){} }
  }, 60);
  return paFbEl('paFeedback');
}

function paFbBoot(){
  if(paFbRun.started) return;      /* 幂等 */
  paFbRun.started = true;
  const sb = paFbEl('paFbSend'); if(sb) sb.addEventListener('click', paFbSend);
  /* 形之变 ⇒ 重判「可发」（否则「题 ／ 文」输入后按钮恒灰 ⇒ 死路）。 */
  ['paFbTitle', 'paFbBody'].forEach(function(id){
    const e = paFbEl(id); if(e) e.addEventListener('input', function(){ paFbRender(); });
  });
  const fi = paFbEl('paFbFiles');
  if(fi) fi.addEventListener('change', function(ev){
    const fs = (ev && ev.target && ev.target.files) ? ev.target.files : [];
    paFbReadFiles(fs, function(out){ paFbRun.files = out; paFbRender(); });
  });
  const bx = paFbEl('paFbBuses');
  if(bx) bx.addEventListener('change', function(){ paFbRun.consent = paFbConsentFromDom(); paFbRender(); });
  const ag = paFbEl('paFbAgree');
  if(ag) ag.addEventListener('change', function(){ paFbRun.agreed = !!ag.checked; paFbRender(); });
  const it = paFbEl('paFbItems');
  if(it) it.addEventListener('click', function(ev){
    const n = (ev && ev.target && ev.target.closest) ? ev.target.closest('[data-fid]') : null;
    if(n) paFbOpenItem(n.getAttribute('data-fid'));
  });
  paFbFetch();
  paFbRun.poll = setInterval(paFbFetch, PA_FB_POLL_MS);
}

try{
  window.paFbTarget = paFbTarget; window.paFbNoticeText = paFbNoticeText;
  window.paFbGate = paFbGate; window.paFbBusTags = paFbBusTags;
  window.paFbItemsText = paFbItemsText; window.paFbReplyText = paFbReplyText;
  window.paFbSendText = paFbSendText; window.paFbBusLabel = paFbBusLabel;
  window.paFbRender = paFbRender; window.paFbFetch = paFbFetch; window.paFbSend = paFbSend;
  window.paFbOpenItem = paFbOpenItem; window.paFbBoot = paFbBoot; window.paFbRun = paFbRun;
  window.paFbBannerView = paFbBannerView; window.paFbFeedBanner = paFbFeedBanner;
  window.paFbFormFromDom = paFbFormFromDom; window.paFbOpen = paFbOpen;
}catch(e){}
if(document.readyState === 'loading'){ document.addEventListener('DOMContentLoaded', paFbBoot); }
else { paFbBoot(); }
