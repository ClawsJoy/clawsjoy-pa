/* PA 窗 v1 / 1a · 壳（CW b2a5182 · 2026-10-27 · 承 PRD v1 §3 ／ §4 ／ §9）
   四形态：Summon ／ Today ／ Focus ／ Now（右栏）。路由 ＋ 开关 PA_WIN_V1。
   界（硬）：静态壳（mock 数据）；⛔ 动后端 ／ ⛔ 新依赖 ／ ⛔ 删旧 faces；开关关 ⇒ 旧三面**一字不变**。 */
(function(){
  'use strict';

  var ROUTES = ['today', 'brain', 'browser', 'agents', 'ledger', 'vault', 'doors'];
  var LABEL = {today:'今天', brain:'脑', browser:'网', agents:'席', ledger:'账', vault:'库', doors:'门'};
  /* 图标：inline SVG（⏔ emoji —— 截图曾回落成汉字，与 label 重字）。icon 20 ＋ label 10，64px 内不裁。 */
  var SVG = {
    today:'<svg viewBox="0 0 20 20" width="20" height="20" aria-hidden="true" focusable="false"><rect x="2.75" y="4.25" width="14.5" height="12.5" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M2.75 8h14.5M6.75 2.75v3M13.25 2.75v3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="7" cy="11.2" r=".9" fill="currentColor"/></svg>',
    agents:'<svg viewBox="0 0 20 20" width="20" height="20" aria-hidden="true" focusable="false"><circle cx="7.2" cy="7" r="2.6" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M2.6 16.2c0-2.5 2-4.2 4.6-4.2s4.6 1.7 4.6 4.2" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M13.1 5.1c1.2 0 2.1 1 2.1 2.2s-.9 2.2-2.1 2.2M14.3 12.4c1.9.3 3.2 1.7 3.2 3.8" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
    ledger:'<svg viewBox="0 0 20 20" width="20" height="20" aria-hidden="true" focusable="false"><path d="M5 2.8h10v14.4l-2.5-1.6-2.5 1.6-2.5-1.6L5 17.2z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M7.6 7h4.8M7.6 10.2h4.8M7.6 13.2h3" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>',
    brain:'<svg viewBox="0 0 20 20" width="20" height="20" aria-hidden="true" focusable="false"><path d="M7.2 3.5c1.2 0 2.1.8 2.3 1.9.3-.6.9-1 1.6-1 1.1 0 1.9.9 1.9 2 1.3.2 2.2 1.2 2.2 2.5 0 .7-.3 1.3-.8 1.8.5.5.8 1.2.8 1.9 0 1.4-1.1 2.5-2.5 2.5-.5 0-1-.2-1.4-.5-.4.9-1.3 1.5-2.3 1.5-1 0-1.9-.6-2.3-1.5-.4.3-.9.5-1.4.5C5.1 15.1 4 14 4 12.6c0-.7.3-1.4.8-1.9-.5-.5-.8-1.1-.8-1.8 0-1.3.9-2.3 2.2-2.5 0-1.1.9-2 2-2z" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/><path d="M10 5.5v9M7.2 8.2c.8.2 1.4.8 1.6 1.6M12.8 8.2c-.8.2-1.4.8-1.6 1.6" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>',
    browser:'<svg viewBox="0 0 20 20" width="20" height="20" aria-hidden="true" focusable="false"><circle cx="10" cy="10" r="7" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M3 10h14M10 3c2.2 2 3.3 4.5 3.3 7s-1.1 5-3.3 7c-2.2-2-3.3-4.5-3.3-7S7.8 5 10 3z" fill="none" stroke="currentColor" stroke-width="1.2"/></svg>',
    vault:'<svg viewBox="0 0 20 20" width="20" height="20" aria-hidden="true" focusable="false"><rect x="2.8" y="3.2" width="14.4" height="4" rx="1" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M4.2 7.2v8.3c0 .8.6 1.3 1.3 1.3h9c.7 0 1.3-.5 1.3-1.3V7.2" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M8 10.4h4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
    doors:'<svg viewBox="0 0 20 20" width="20" height="20" aria-hidden="true" focusable="false"><path d="M4.6 17.2V3.6c0-.5.4-.9.9-.9h9c.5 0 .9.4.9.9v13.6" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M3.4 17.2h13.2" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="12.7" cy="10.2" r=".9" fill="currentColor"/></svg>'
  };
  var ICON = SVG;

  function $(x){ return document.getElementById(x); }
  function esc(s){
    return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
    });
  }

  /* ── 开关：?ui=legacy ／ ?paWin=0 回退；默认新窗（P0 产品面） ── */
  window.paWinFlagOn = function(){
    try{
      var q = new URLSearchParams(location.search);
      var ui = q.get('ui');
      var qq = q.get('paWin');
      if(ui === 'legacy' || qq === '0'){ localStorage.setItem('paWinV1','0'); return false; }
      if(ui === 'window' || qq === '1'){ localStorage.setItem('paWinV1','1'); return true; }
      /* 9.2.2 之前每个 boot 都把默认值 false 写进 localStorage；
         首次升级清除旧默认一次，避免“永远回不到新窗”。 */
      if(localStorage.getItem('paWinV2Migrated') !== '1'){
        localStorage.removeItem('paWinV1');
        localStorage.setItem('paWinV2Migrated','1');
      }
      if(localStorage.getItem('paWinV1') === '1') return true;
      if(localStorage.getItem('paWinV1') === '0') return false;
    }catch(e){}
    return true;   /* 产品默认：新窗唯一默认 */
  };
  window.paWinSetFlag = function(on){
    try{ localStorage.setItem('paWinV1', on ? '1' : '0'); }catch(e){}
  };

  /* dev 径：仅 `?dev=1` 显（不记住 · 用户面默认不见）。 */
  window.paWinDevOn = function(){
    try{ return new URLSearchParams(location.search).get('dev') === '1'; }catch(e){ return false; }
  };

  /* ── mock（1a 静态 · PRD §3.2 之数与行一致）── */
  window.PA_WIN_MOCK = {
    todo: [
      {t:'把上周的账导一份', due:'今天 18:00', who:'你'},
      {t:'定 v1 之四件取舍', due:'今天 20:00', who:'你'},
      {t:'回项目经理之三问', due:'明天 10:00', who:'你'}
    ],
    waiting: [
      {t:'等你点头：云上起一台', who:'内容制作席', since:'等了 2 小时'},
      {t:'等你给一句口径', who:'技术总监', since:'等了 40 分钟'}
    ],
    running: [
      {id:'r1', name:'②v1 拆件', pct:32, cost:'¥0.00', state:'running'}
    ],
    approve: [
      {id:'a1', level:'L2', risk:'出机', what:'云上起一台做试验', why:'本地跑不动', cost:'¥2.40', egress:'方案与样例数据 · 给云服务商 · 试验完 1 小时删'}
    ],
    egress: [],
    ledger: [
      {at:'09:12', who:'你', what:'批了「v1 拆件」', cost:'¥0.00', hash:'3f9c1a7e', prev:'b21d84c0'},
      {at:'09:05', who:'技术总监', what:'交了拆件稿', cost:'¥0.12', hash:'b21d84c0', prev:'7a55e2d1'},
      {at:'08:47', who:'你', what:'否了「全站重排」', cost:'¥0.00', hash:'7a55e2d1', prev:'c4e019bb'},
      {at:'08:30', who:'项目经理', what:'报了晨会三问', cost:'¥0.03', hash:'c4e019bb', prev:'9d3ba6f2'},
      {at:'08:02', who:'你', what:'开了今天', cost:'¥0.00', hash:'9d3ba6f2', prev:'00000000'}
    ]
  };

  /* 1b-1：起手全空 —— 真数由 live.js 取；mock 只留给显式演示，⛔ 混入真屏。 */
  window.PA_WIN_STATE = {
    runs: [],
    approvals: [],
    egress: [],
    ledger: [],
    route: 'today',
    stopAt: 0,
    codeFails: 0,
    lockedUntil: 0
  };

  /* ── 账：加一行（带前一条指纹短 · PRD §8.10）── */
  window.paWinLedgerAdd = function(what, who, cost, tag){
    var s = window.PA_WIN_STATE;
    var prev = s.ledger.length ? s.ledger[0].hash : '';
    var now = new Date();
    var t = ('0' + now.getHours()).slice(-2) + ':' + ('0' + now.getMinutes()).slice(-2);
    var hash = paWinHash(t + '|' + (what || '') + '|' + (prev || ''));
    s.ledger.unshift({at:t, who:who || '你', what:what, cost:cost || '¥0.00',
                      hash:hash, prev:prev, tag:tag || ''});
    if(s.route === 'ledger' || s.route === 'today') window.paWinRenderRoute();
    return hash;
  };

  /* 指纹（1a 为前端短指纹；真账在后端，Phase 1 接线） */
  function paWinHash(s){
    var h = 0x811c9dc5;
    for(var i = 0; i < s.length; i++){
      h ^= s.charCodeAt(i);
      h = (h * 0x01000193) >>> 0;
    }
    return ('00000000' + h.toString(16)).slice(-8);
  }
  window.paWinHash = paWinHash;

  /* ── 一句话（轻提示 · ⛔ 弹窗雨）── */
  var sayTimer = null;
  window.paWinSay = function(msg){
    var el = $('paWinSay');
    if(!el) return;
    el.textContent = msg;
    el.classList.add('on');
    if(sayTimer) clearTimeout(sayTimer);
    sayTimer = setTimeout(function(){ el.classList.remove('on'); }, 2600);
  };

  window.paWinEgressRefresh = function(){
    var n = (window.PA_WIN_STATE.egress || []).length;
    var el = $('paWinEgress');
    if(!el) return;
    el.textContent = n ? ('将出机 ' + n) : '本地 · 未出机';
    el.classList.toggle('warn', n > 0);
  };

  /* ── 右栏收放（窄屏可收 · PRD §8.15）── */
  window.paWinNowToggle = function(){
    var off = document.body.classList.toggle('pa-now-off');
    var b = $('paNowBtn');
    if(b) b.setAttribute('aria-pressed', off ? 'false' : 'true');
    window.paWinSay(off ? '右栏收起了' : '右栏回来了');
  };

  /* ── 壳 ── */
  function shellHtml(){
    var rail = ROUTES.map(function(r, i){
      return '<button class="pa-rail-b" type="button" data-r="' + r + '" onclick="paWinGo(\'' + r + '\')"'
        + ' title="' + esc(LABEL[r]) + '（Alt+' + (i + 1) + '）">'
        + '<span class="ic">' + ICON[r] + '</span><span class="lb">' + esc(LABEL[r]) + '</span></button>';
    }).join('');
    return '<header class="pa-top">'
      + '<span class="pa-who"><i class="pa-live"></i>老板 · 本机</span>'
      + '<nav class="pa-modes" role="tablist" aria-label="三态"><button class="on" type="button">陪伴</button>'
      + '<button type="button">办事</button><button type="button">审计</button></nav>'
      + '<span class="pa-egress" id="paWinEgress">本地 · 未出机</span>'
      + '<button class="pa-btn pa-btn-ghost" id="paWinUpdateBtn" type="button" onclick="paWinUpdate()" title="更新：检查并安装（沿用旧更新器 · 含不降级守卫）">更新</button>'
      + '<button class="pa-btn pa-btn-ghost" id="paWinMoreBtn" type="button" onclick="paWinMore()" title="更多：反馈／体检／自述／文件／产出／模式（沿用旧面收纳层）">更多 ▾</button>'
      + '<button class="pa-btn pa-btn-ghost" id="paWinCfgBtn" type="button" onclick="paWinConfig()" title="设置：模型／权限／配置（沿用旧面之设置层）">⚙ 设置</button>'
      + '<button class="pa-btn pa-btn-ghost" id="paWinKeyBtn" type="button" onclick="paWinKeys()" title="密钥：模型供应商（沿用旧面之密钥层）">🔑 密钥</button>'
      + '<button class="pa-btn pa-btn-ghost" id="paNowBtn" type="button" onclick="paWinNowToggle()" aria-pressed="true" title="右栏：收起 ／ 展开">右栏</button>'
      + '<button class="pa-btn pa-btn-stop" id="paWinStop" type="button" onclick="paWinStop()" disabled title="停（Ctrl+.）">■ 停</button>'
      + '<button class="pa-btn pa-btn-ghost" id="paBtnLegacy" type="button" onclick="paWinLegacy()" title="回旧面（仅 dev）" hidden>旧面</button>'
      + '</header>'
      + '<div class="pa-body"><nav class="pa-rail" aria-label="五个去处">' + rail + '</nav>'
      + '<main class="pa-stage" id="paWinStage" tabindex="-1"></main>'
      + '<aside class="pa-now" id="paWinNow" aria-label="右栏"></aside></div>'
      + '<div id="paWinAttachHost" style="position:fixed;left:240px;right:340px;bottom:150px;z-index:60;max-height:150px;overflow:auto;font-size:11.5px;color:var(--sub)"></div>'
      + '<div class="pa-say" id="paWinSay" role="status" aria-live="polite"></div>';
  }

  function summonHtml(){
    return '<div class="pa-summon" id="paSummon" hidden>'
      + '<div class="pa-summon-row">'
      + '<input id="paSummonIn" type="text" placeholder="说一句话，或拖一件东西进来…" autocomplete="off" aria-label="说一句话" onkeydown="if(event.key===\'Enter\' && !event.shiftKey){event.preventDefault();paWinSummonSend();}">'
      + '<div class="pa-chips"><button type="button" onclick="paWinMode(\'陪\')">陪</button>'
      + '<button type="button" onclick="paWinMode(\'办\')">办</button>'
      + '<button type="button" onclick="paWinMode(\'查\')">查</button></div></div>'
      + '<div class="pa-summon-hint" style="font-size:11px;color:var(--sub);margin-top:4px;line-height:1.4">多席：多席:PM,PD …</div>'
      + '<div class="pa-summon-foot"><span><span class="pa-summon-send" style="cursor:pointer;text-decoration:underline dotted" onclick="paWinSummonSend()">⏎ 发</span> · Esc 收</span><span id="paSummonAtt">附件 0</span></div></div>';
  }

  window.paWinMode = function(m){ window.paWinSummonMode = m; window.paWinSay('这一句按「' + m + '」办'); };

  /* 设置／密钥：唯调旧面已存之层（paSettings ／ paKeyOpen）——
     `#paMorePanel` z-index 120 > `#paWin` 70 ⇒ 直接盖在新窗之上；⛔ 复制第二套密钥/模型逻辑。 */
  /* 更新：唯调旧更新器（paUpdFetch ／ paUpdGo）—— 检查／降级守卫／回滚全在其内；
     本窗只显示其结论，⛔ 复制第二套更新状态机。 */
  window.paWinUpdate = async function(){
    try{
      if(typeof window.paUpdFetch === 'function'){ await window.paUpdFetch(); }
      var v = window.paUpdRun && window.paUpdRun.last;
      if(v && v.can_start){
        window.paWinSay('开始更新…');
        if(typeof window.paUpdGo === 'function'){ await window.paUpdGo(); }
        v = window.paUpdRun && window.paUpdRun.last;
        window.paWinSay((v && (v.text || v.bnote)) || '更新已发起');
        return;
      }
      window.paWinSay((v && (v.text || v.bnote)) || '更新状态未得（旧更新面未答）');
    }catch(e){ window.paWinSay('更新 ⛔ 成：' + ((e && e.message) || e)); }
  };
  window.paWinMore = function(){
    try{ if(typeof window.paMore === 'function'){ window.paMore(true); return; } }
    catch(e){}
    window.paWinSay('旧收纳层未载（paMore 不在）');
  };
  window.paWinConfig = function(){
    try{ if(typeof window.paSettings === 'function'){ window.paSettings(); return; } }
    catch(e){}
    window.paWinSay('设置层未载（旧面 paSettings 不在）');
  };
  window.paWinKeys = function(){
    try{ if(typeof window.paKeyOpen === 'function'){ window.paKeyOpen(); return; } }
    catch(e){}
    window.paWinSay('密钥层未载（旧面 paKeyOpen 不在）');
  };

  /* ── 路由渲染 ── */
  /* Focus 不是一条路由 —— 它是「舞台被一张任务卡占着」（body.pa-focus）。
     若只按 st.route 判，任何重渲染都会把任务卡打回 Today（真 bug，已修）。 */
  window.paWinRouteIs = function(r){
    if(r === 'focus') return document.body.classList.contains('pa-focus');
    return window.PA_WIN_STATE.route === r;
  };

  window.paWinGo = function(r){
    if(ROUTES.indexOf(r) < 0) r = 'today';
    window.PA_WIN_STATE.route = r;
    document.body.classList.toggle('pa-focus', false);
    var rail = document.querySelectorAll('.pa-rail-b');
    for(var i = 0; i < rail.length; i++) rail[i].classList.toggle('on', rail[i].getAttribute('data-r') === r);
    if(window.paWinLiveEnsure && (r === 'agents' || r === 'ledger' || r === 'vault' || r === 'doors')){
      window.paWinLiveEnsure(15000);
    }
    window.paWinRenderRoute();
  };

  window.paWinRenderRoute = function(){
    var st = window.PA_WIN_STATE;
    var stage = $('paWinStage');
    if(!stage) return;

    /* Focus 态：舞台让给任务卡（⛔ 按 route 重画 Today）*/
    if(document.body.classList.contains('pa-focus') && st.currentTask){
      stage.innerHTML = window.paWinTaskCardHtml(st.currentTask);
      if(window.paWinNowRender) window.paWinNowRender();
      var hF = stage.querySelector('h1, h2');
      if(hF) hF.setAttribute('tabindex', '-1');
      return;
    }

    var r = st.route;
    document.body.setAttribute('data-pa-route', r);
    if(r !== 'browser' && window.paBrowserHide) window.paBrowserHide();
    if(r === 'today') stage.innerHTML = todayHtml();
    else if(r === 'brain'){
      stage.innerHTML = (window.paBrainHtml ? window.paBrainHtml() : brainHtml());
      if(window.paBrainMount) window.paBrainMount(); else paBrainLoad('');
    }
    else if(r === 'browser'){ stage.innerHTML = browserHtml(); paBrowserMount(); }
    else if(r === 'ledger') stage.innerHTML = ledgerHtml();
    else if(r === 'agents') stage.innerHTML = agentsHtml();
    else if(r === 'vault') stage.innerHTML = vaultHtml();
    else stage.innerHTML = doorsHtml();
    if(window.paWinNowRender) window.paWinNowRender();
    var h = stage.querySelector('h1, h2');
    if(h) h.setAttribute('tabindex', '-1');
  };

  /* ── 第二大脑（P0）：真 API /v9/pa/notes；列表/搜索/记一笔/编辑/删除 ── */
  var paBrainEditId = null;
  var paBrainTimer = null;
  function paBrainApi(){ return (typeof API !== 'undefined') ? API : ''; }
  function brainHtml(){
    return '<h1 class="pa-h1">第二大脑</h1>'
      + '<div class="pa-cmd">'
      + '<input id="paBrainQ" type="search" placeholder="搜笔记：标题、正文、标签…" autocomplete="off" aria-label="搜笔记" oninput="paBrainSearch(this.value)">'
      + '<button class="pa-btn pa-btn-main" type="button" onclick="paBrainNew()">记一笔</button>'
      + '<button id="paBrainMic" class="pa-btn pa-btn-ghost" type="button" onclick="paBrainVoiceToggle()" title="语音记：本地录音，本地转写">🎤 语音记</button>'
      + '<button id="paBrainScreen" class="pa-btn pa-btn-ghost" type="button" onclick="paScreenPick()" title="录屏：本地录窗口/屏幕，本地转写">🎬 录屏</button>'
      + '<button class="pa-btn pa-btn-ghost" type="button" onclick="paBrainImport()" title="导入一个本地 md 目录">导入 md 目录</button>'
      + '</div>'
      + '<div class="pa-cmd" style="margin-top:8px">'
      + '<input id="paBrainAskIn" type="text" placeholder="问第二大脑：这周记了什么？客户说了什么？" autocomplete="off" onkeydown="if(event.key===\'Enter\')paBrainAsk()">'
      + '<button class="pa-btn pa-btn-ghost" type="button" onclick="paBrainAsk()">问</button>'
      + '</div>'
      + '<div id="paBrainAnswer" hidden style="margin:10px 0;padding:12px;border:1px solid var(--line);border-radius:8px;background:var(--card);white-space:pre-wrap;font-size:13px;line-height:1.7"></div>'
      + '<div id="paBrainForm" hidden style="margin:10px 0;padding:12px;border:1px solid var(--line);border-radius:8px;background:var(--card)">'
      + '<input id="paBrainTitle" type="text" placeholder="标题" style="width:100%;box-sizing:border-box;margin-bottom:8px;padding:8px;background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:6px">'
      + '<input id="paBrainTags" type="text" placeholder="标签，用逗号分隔" style="width:100%;box-sizing:border-box;margin-bottom:8px;padding:8px;background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:6px">'
      + '<textarea id="paBrainBody" rows="8" placeholder="正文…" style="width:100%;box-sizing:border-box;margin-bottom:8px;padding:8px;background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:6px;resize:vertical"></textarea>'
      + '<button class="pa-btn pa-btn-main" type="button" onclick="paBrainSave()">保存</button> '
      + '<button class="pa-btn pa-btn-ghost" type="button" onclick="paBrainCancel()">取消</button>'
      + '<button id="paBrainDel" class="pa-btn pa-btn-ghost" type="button" onclick="paBrainDelete()" hidden>删除</button>'
      + '<span id="paBrainEditHint" class="pa-hint" style="margin-left:8px"></span>'
      + '</div>'
      + '<div id="paBrainList" class="pa-brain-list" style="margin-top:10px"></div>'
      + '<div id="paBrainStatus" class="pa-hint" style="margin-top:8px">正在读第二大脑…</div>';
  }
  function paBrainMsg(t){ var e=$('paBrainStatus'); if(e){ e.textContent=t; } }
  function paBrainRender(list){
    var box=$('paBrainList'); if(!box) return;
    if(!list || !list.length){ box.innerHTML='<div class="pa-hint" style="padding:12px 0">还没有笔记。点「记一笔」，或导入一个本地 md 目录。</div>'; return; }
    box.innerHTML = list.map(function(n){
      var tags = (n.tags || []).slice(0,5).map(function(t){ return '<span class="pa-chip">' + esc(t) + '</span>'; }).join(' ');
      return '<div class="pa-brain-item" onclick="paBrainOpen(\'' + esc(n.id) + '\')">'
        + '<div style="font-weight:600">' + esc(n.title || '未命名') + '</div>'
        + '<div class="pa-hint" style="margin-top:2px">' + esc(n.updated || '') + (tags ? ' · ' + tags : '') + '</div>'
        + '</div>';
    }).join('');
  }
  window.paBrainSearch = function(q){
    if(paBrainTimer) clearTimeout(paBrainTimer);
    paBrainTimer = setTimeout(function(){ paBrainLoad(q); }, 220);
  };
  window.paBrainLoad = function(q){
    paBrainMsg('正在读第二大脑…');
    return fetch(paBrainApi() + '/v9/pa/notes?limit=50&q=' + encodeURIComponent(q || ''), {cache:'no-store'})
      .then(function(r){ return r.json(); })
      .then(function(d){
        if(!d || d.ok !== true) throw new Error((d && (d.error || d.message)) || 'API 未答');
        paBrainRender(d.notes || []);
        paBrainMsg('共 ' + (d.notes || []).length + ' 条 · 源 /v9/pa/notes');
      })
      .catch(function(e){ paBrainMsg('读不到：' + ((e && e.message) || e)); });
  };
  function paBrainMedia(n){
    var old=document.getElementById('paBrainMedia'); if(old) old.remove();
    var sp=String((n && n.source_path) || '');
    if(!sp) return;
    var isVid=/\.(webm|mp4|mkv|mov)$/i.test(sp);
    var isAud=/\.(wav|mp3|m4a|ogg|opus)$/i.test(sp);
    if(!isVid && !isAud) return;
    var f=$('paBrainForm'); if(!f) return;
    var b=document.createElement('button'); b.id='paBrainMedia'; b.type='button';
    b.className='pa-btn pa-btn-ghost'; b.style.marginLeft='6px';
    b.textContent=isVid ? '▶ 打开录屏' : '▶ 打开录音';
    b.title=sp;
    b.onclick=function(){
      try{
        if(window.paShell && window.paShell.openPath){
          window.paShell.openPath(sp).then(function(d){
            if(!d || !d.ok) paBrainMsg('打不开：' + ((d && (d.error || d.message)) || '未知'));
          }).catch(function(e){ paBrainMsg('打不开：' + ((e && e.message) || e)); });
        } else { paBrainMsg('仅桌面壳可打开本地文件'); }
      }catch(e){ paBrainMsg('打不开：' + ((e && e.message) || e)); }
    };
    f.appendChild(b);
  }
  window.paBrainNew = function(){
    paBrainEditId = null;
    var m0=document.getElementById('paBrainMedia'); if(m0) m0.remove();
    var f=$('paBrainForm'); if(f) f.hidden=false;
    var t=$('paBrainTitle'); if(t){ t.value=''; t.focus(); }
    var g=$('paBrainTags'); if(g) g.value='';
    var b=$('paBrainBody'); if(b) b.value='';
    var h=$('paBrainEditHint'); if(h) h.textContent='新笔记';
    var d0=$('paBrainDel'); if(d0) d0.hidden=true;
  };
  window.paBrainCancel = function(){
    var f=$('paBrainForm'); if(f) f.hidden=true;
    paBrainEditId = null;
  };
  window.paBrainOpen = function(id){
    return fetch(paBrainApi() + '/v9/pa/notes/' + encodeURIComponent(id), {cache:'no-store'})
      .then(function(r){ return r.json(); })
      .then(function(d){
        if(!d || d.ok !== true) throw new Error((d && (d.error || d.message)) || '读不到');
        var n=d.note || {};
        paBrainEditId = n.id;
        var f=$('paBrainForm'); if(f) f.hidden=false;
        $('paBrainTitle').value = n.title || '';
        $('paBrainTags').value = (n.tags || []).join(', ');
        $('paBrainBody').value = n.body || '';
        var h=$('paBrainEditHint'); if(h) h.textContent='编辑 ' + (n.updated || '');
        var d0=$('paBrainDel'); if(d0) d0.hidden=false;
        paBrainMedia(n);
      })
      .catch(function(e){ paBrainMsg('打不开：' + ((e && e.message) || e)); });
  };
  window.paBrainAsk = function(){
    var q = $('paBrainAskIn') ? $('paBrainAskIn').value.trim() : '';
    if(!q){ if($('paBrainAskIn')) $('paBrainAskIn').focus(); return; }
    var box=$('paBrainAnswer');
    if(box){ box.hidden=false; box.textContent='问第二大脑…'; }
    return fetch(paBrainApi() + '/v9/pa/notes/ask', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({q:q})})
      .then(function(r){ return r.json(); })
      .then(function(d){
        if(!d || d.ok !== true) throw new Error((d && (d.error || d.message)) || '没有回答');
        if(box){
          box.textContent = d.answer || '（无回答）';
          var cs = d.citations || [];
          if(cs.length){
            var line=document.createElement('div'); line.style.marginTop='8px'; line.textContent='出处：';
            box.appendChild(line);
            cs.forEach(function(c){
              var b=document.createElement('button'); b.type='button'; b.className='pa-chip'; b.style.marginRight='6px';
              b.textContent=c.title || c.id; b.onclick=function(){ window.paBrainOpen(c.id); };
              box.appendChild(b);
            });
          }
        }
      })
      .catch(function(e){ if(box){ box.hidden=false; box.textContent='问不到：' + ((e && e.message) || e); } });
  };

  /* ── 屏幕录播 P0：自选源 + 电脑声音可选 + 麦克风开关 → 本地转写/关键帧 → note ── */
  var paScreenRec = null, paScreenChunks = [], paScreenStream = null, paScreenTimer = null, paScreenSec = 0;
  var paScreenMicTrack = null, paScreenSrcs = [];
  var paScreenMaxSec = 1800;
  var paScreenWarned = false;
  window.paScreenPick = function(){
    if(!window.paShell || typeof window.paShell.screenSources !== 'function'){ paBrainMsg('屏幕录播仅在桌面壳可用'); return; }
    paBrainMsg('读取屏幕/窗口…');
    window.paShell.screenSources().then(function(d){
      if(!d || !d.ok){ paBrainMsg('读不到屏幕：' + ((d && (d.error || d.message)) || '未知')); return; }
      paScreenSrcs = d.sources || [];
      if(!paScreenSrcs.length){ paBrainMsg('没有可录的屏幕/窗口'); return; }
      var ov=document.createElement('div'); ov.id='paScreenPick';
      ov.style.cssText='position:fixed;inset:0;z-index:500;background:rgba(0,0,0,.72);display:flex;align-items:center;justify-content:center;padding:24px';
      var cards=paScreenSrcs.map(function(s,i){
        return '<div class="pa-screen-card" onclick="paScreenChoose(' + i + ')">'
          + (s.thumbnail ? '<img src="' + s.thumbnail + '" alt="">' : '<div style="height:110px;display:flex;align-items:center;justify-content:center;color:var(--sub)">无预览</div>')
          + '<div style="margin-top:6px;font-size:12px">' + esc(s.name) + '</div></div>';
      }).join('');
      ov.innerHTML='<div style="max-width:900px;width:100%;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px">'
        + '<div style="display:flex;align-items:center;margin-bottom:8px"><b>选一个窗口/屏幕</b>'
        + '<button class="pa-btn pa-btn-ghost" style="margin-left:auto" onclick="paScreenClose()">取消</button></div>'
        + '<div style="margin:0 0 10px;display:flex;gap:16px;font-size:12px;color:var(--sub)">'
        + '<label><input type="checkbox" id="paScreenAudio"> 电脑声音（系统音频）</label>'
        + '<label><input type="checkbox" id="paScreenMicChk" checked> 麦克风</label></div>'
        + '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px;max-height:58vh;overflow:auto">' + cards + '</div>'
        + '<div class="pa-hint" style="margin-top:10px">只录你选的窗口/屏幕 · 本地处理 · 电脑声音可选 · 麦克风可关</div></div>';
      document.body.appendChild(ov);
      paBrainMsg('选一个窗口/屏幕开始录');
    }).catch(function(e){ paBrainMsg('读不到屏幕：' + ((e && e.message) || e)); });
  };
  window.paScreenClose = function(){ var o=document.getElementById('paScreenPick'); if(o) o.remove(); };
  window.paScreenChoose = function(i){
    var src=paScreenSrcs[i]; if(!src){ return; }
    var wantAudio=!!(document.getElementById('paScreenAudio') && document.getElementById('paScreenAudio').checked);
    var wantMic=!!(document.getElementById('paScreenMicChk') && document.getElementById('paScreenMicChk').checked);
    window.paScreenClose();
    var sel = (window.paShell && window.paShell.screenSelect)
      ? window.paShell.screenSelect(src.id, wantAudio) : Promise.resolve({ok:true});
    sel.then(function(){
      return navigator.mediaDevices.getDisplayMedia({video:{frameRate:15}, audio:true});
    }).then(function(vs){
      if(!wantMic){ paScreenMicTrack=null; return vs; }
      return navigator.mediaDevices.getUserMedia({audio:true}).then(function(as){
        var mt=as.getAudioTracks()[0] || null;
        if(mt){ vs.addTrack(mt); paScreenMicTrack=mt; } else { paScreenMicTrack=null; }
        return vs;
      }).catch(function(){ paScreenMicTrack=null; return vs; });
    }).then(function(stream){ paScreenBegin(stream); })
      .catch(function(e){ paBrainMsg('录屏未开始：' + ((e && e.message) || e)); });
  };
  window.paScreenToggleMic = function(){
    if(!paScreenMicTrack) return false;
    paScreenMicTrack.enabled = !paScreenMicTrack.enabled;
    return paScreenMicTrack.enabled === true;
  };
  function paScreenBegin(stream){
    paScreenStream = stream; paScreenChunks = [];
    var rec = new MediaRecorder(stream);
    paScreenRec = rec;
    rec.ondataavailable = function(e){ if(e.data && e.data.size) paScreenChunks.push(e.data); };
    rec.onstop = function(){
      var blob = new Blob(paScreenChunks, {type: rec.mimeType || 'video/webm'});
      paScreenChunks = [];
      try{ stream.getTracks().forEach(function(t){ t.stop(); }); }catch(e){}
      paScreenStream = null; paScreenRec = null; paScreenMicTrack = null;
      if(paScreenTimer){ clearInterval(paScreenTimer); paScreenTimer = null; }
      var bar = document.getElementById('paScreenBar'); if(bar) bar.remove();
      try{ if(window.paShell && paShell.recHide) paShell.recHide(); }catch(e){}
      if(!blob.size){ paBrainMsg('没有录到内容'); return; }
      paBrainMsg('录屏已停止 · 本地转写/关键帧中…');
      var fd = new FormData(); fd.append('file', blob, 'screen.webm');
      fetch(paBrainApi() + '/v9/pa/notes/screen', {method:'POST', body:fd})
        .then(function(r){ return r.json(); })
        .then(function(d){
          if(!d || d.ok !== true) throw new Error((d && (d.error || d.message)) || '处理失败');
          paBrainMsg('已存入第二大脑：' + ((d.note && d.note.title) || '录屏笔记'));
          return window.paBrainLoad('');
        })
        .catch(function(e){ paBrainMsg('录屏处理失败：' + ((e && e.message) || e)); });
    };
    rec.start(1000);
    try{ if(window.paShell && paShell.recShow) paShell.recShow(); }catch(e){}
    paScreenSec = 0; paScreenWarned = false;
    var bar = document.createElement('div'); bar.id = 'paScreenBar';
    bar.style.cssText = 'position:fixed;left:50%;bottom:18px;transform:translateX(-50%);z-index:520;background:#2b0b0b;border:1px solid #a33;border-radius:999px;padding:8px 14px;display:flex;gap:10px;align-items:center;color:#fff;font-size:12px;box-shadow:0 8px 24px rgba(0,0,0,.4)';
    bar.innerHTML = '<span style="color:#ff6b6b">● 录屏</span><span id="paScreenTimer">00:00</span><button class="pa-btn pa-btn-stop" type="button" onclick="paScreenStop()">停止</button>';
    document.body.appendChild(bar);
    paScreenTimer = setInterval(function(){
      paScreenSec++;
      var m = ('0' + Math.floor(paScreenSec / 60)).slice(-2), ss = ('0' + (paScreenSec % 60)).slice(-2);
      var e = document.getElementById('paScreenTimer'); if(e) e.textContent = m + ':' + ss;
      if(paScreenSec >= paScreenMaxSec - 60 && !paScreenWarned){ paScreenWarned = true; paBrainMsg('录屏还剩 1 分钟（30 分钟上限）'); }
      if(paScreenSec >= paScreenMaxSec){ paBrainMsg('已达 30 分钟上限，自动停止'); window.paScreenStop(); }
    }, 1000);
    paBrainMsg('录屏中 · 上限 30 分钟 · 再点「停止」结束');
  }
  window.paScreenStop = function(){
    try{ if(paScreenRec && paScreenRec.state !== 'inactive'){ paScreenRec.stop(); } }catch(e){}
  };

  var paMicRec = null, paMicChunks = [], paMicStream = null;
  window.paBrainVoiceToggle = function(){
    if(paMicRec && paMicRec.state === 'recording'){ try{ paMicRec.stop(); }catch(e){} return; }
    if(!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia){
      paBrainMsg('本窗不支持录音（无 mediaDevices）'); return;
    }
    paBrainMsg('请允许麦克风…');
    navigator.mediaDevices.getUserMedia({audio:true}).then(function(stream){
      paMicStream = stream; paMicChunks = [];
      var mr = new MediaRecorder(stream);
      paMicRec = mr;
      mr.ondataavailable = function(e){ if(e.data && e.data.size) paMicChunks.push(e.data); };
      mr.onstop = function(){
        var b=$('paBrainMic'); if(b){ b.textContent='🎤 语音记'; b.classList.remove('on'); }
        var blob = new Blob(paMicChunks, {type: mr.mimeType || 'audio/webm'});
        paMicChunks = [];
        try{ if(paMicStream) paMicStream.getTracks().forEach(function(t){ t.stop(); }); }catch(e){}
        paMicStream = null; paMicRec = null;
        if(!blob.size){ paBrainMsg('没有录到声音'); return; }
        paBrainMsg('转写中…（本地 whisper，不上传）');
        var fd = new FormData();
        fd.append('file', blob, 'voice.webm');
        fetch(paBrainApi() + '/v9/pa/notes/voice', {method:'POST', body:fd})
          .then(function(r){ return r.json(); })
          .then(function(d){
            if(!d || d.ok !== true) throw new Error((d && (d.error || d.message)) || '转写失败');
            paBrainMsg('已存入第二大脑：' + ((d.note && d.note.title) || '语音笔记'));
            return window.paBrainLoad('');
          })
          .catch(function(e){ paBrainMsg('转写失败：' + ((e && e.message) || e)); });
      };
      mr.start(1000);
      var b=$('paBrainMic'); if(b){ b.textContent='⏹ 停止'; b.classList.add('on'); }
      paBrainMsg('录音中… 再点「停止」结束');
    }).catch(function(e){ paBrainMsg('麦克风不可用：' + ((e && e.message) || e)); });
  };
  window.paBrainQuick = function(text){
    var body=String(text || '').trim(); if(!body) return Promise.resolve();
    var title=body.replace(/^记[:：]\s*/, '').slice(0, 30) || '随手记';
    return fetch(paBrainApi() + '/v9/pa/notes', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({title:title, body:body, tags:['随手记']})})
      .then(function(r){ return r.json(); })
      .then(function(d){
        if(!d || d.ok !== true) throw new Error((d && (d.error || d.message)) || '记不下');
        window.paWinSay('已记入第二大脑');
        if(window.PA_WIN_STATE && window.PA_WIN_STATE.route === 'brain') window.paBrainLoad('');
        return d;
      })
      .catch(function(e){ window.paWinSay('记不下：' + ((e && e.message) || e)); });
  };
  window.paBrainImport = function(){
    if(!window.paShell || typeof window.paShell.pickDirectory !== 'function'){
      paBrainMsg('导入 md 目录仅在桌面壳可用'); return;
    }
    paBrainMsg('请选择 md 目录…');
    return window.paShell.pickDirectory().then(function(d){
      if(!d || !d.ok){
        paBrainMsg(d && d.canceled ? '已取消' : ('选目录失败：' + ((d && (d.error || d.message)) || '未知')));
        return null;
      }
      paBrainMsg('导入中…');
      return fetch(paBrainApi() + '/v9/pa/notes/import', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({path:d.path})})
        .then(function(r){ return r.json(); })
        .then(function(j){
          if(!j || j.ok !== true) throw new Error((j && (j.error || j.message)) || '导入失败');
          paBrainMsg('导入 ' + (j.imported || 0) + ' 件，跳过 ' + (j.skipped || 0) + ' 件');
          return window.paBrainLoad('');
        });
    }).catch(function(e){ paBrainMsg('导入失败：' + ((e && e.message) || e)); });
  };
  window.paBrainSave = function(){
    var title=$('paBrainTitle') ? $('paBrainTitle').value.trim() : '';
    var body=$('paBrainBody') ? $('paBrainBody').value : '';
    var tags=($('paBrainTags') ? $('paBrainTags').value : '').split(',').map(function(s){ return s.trim(); }).filter(Boolean);
    if(!title){ title = (body || '').slice(0, 30) || '未命名'; }
    var url = paBrainApi() + '/v9/pa/notes' + (paBrainEditId ? '/' + encodeURIComponent(paBrainEditId) : '');
    var method = paBrainEditId ? 'PATCH' : 'POST';
    paBrainMsg('保存中…');
    return fetch(url, {method:method, headers:{'Content-Type':'application/json'}, body:JSON.stringify({title:title, body:body, tags:tags})})
      .then(function(r){ return r.json(); })
      .then(function(d){
        if(!d || d.ok !== true) throw new Error((d && (d.error || d.message)) || '保存失败');
        window.paBrainCancel();
        return window.paBrainLoad($('paBrainQ') ? $('paBrainQ').value : '');
      })
      .catch(function(e){ paBrainMsg('保存失败：' + ((e && e.message) || e)); });
  };
  window.paBrainDelete = function(){
    if(!paBrainEditId) return;
    if(!window.confirm('删除这条笔记？')) return;
    return fetch(paBrainApi() + '/v9/pa/notes/' + encodeURIComponent(paBrainEditId), {method:'DELETE'})
      .then(function(r){ return r.json(); })
      .then(function(d){ if(!d || d.ok !== true) throw new Error('删除失败'); window.paBrainCancel(); return window.paBrainLoad(''); })
      .catch(function(e){ paBrainMsg('删除失败：' + ((e && e.message) || e)); });
  };


  /* ── 内置浏览器 P0（只读＋存 note）── */
  var paBrowserLast = null;
  var paReaderAsr = false;
  var paReaderAsrTimer = null;
  var paReaderAsrClockTimer = null;
  var paReaderAsrStartMs = 0;
  var paReaderAsrBaseTime = 0;
  var paReaderAsrEndAt = 0;
  function browserHtml(){
    return '<h1 class="pa-h1">浏览器</h1>'
      + '<div class="pa-cmd" style="flex-wrap:nowrap;gap:4px">'
      + '<button class="pa-btn pa-btn-ghost" type="button" onclick="paBrowserBack()" title="后退">←</button>'
      + '<button class="pa-btn pa-btn-ghost" type="button" onclick="paBrowserForward()" title="前进">→</button>'
      + '<button class="pa-btn pa-btn-ghost" type="button" onclick="paBrowserReload()" title="刷新">↻</button>'
      + '<input id="paBrowserUrl" type="text" placeholder="https://…" autocomplete="off" style="min-width:0;flex:1" onkeydown="if(event.key===\'Enter\')paBrowserGo()">'
      + '<button class="pa-btn pa-btn-main" type="button" onclick="paBrowserGo()">打开</button>'
      + '<button class="pa-btn pa-btn-ghost" type="button" onclick="paBrowserRead()" title="读取当前页正文">读页</button>'
      + '<button class="pa-btn pa-btn-ghost" type="button" onclick="paBrowserSave()" title="预览并保存当前页/当前视频">存到脑</button>'
      + '<button class="pa-btn pa-btn-ghost" type="button" onclick="paBrowserClose()" title="关闭当前页">✕</button>'
      + '</div>'
      + '<div id="paBrowserStatus" class="pa-hint" style="margin:4px 0 2px">只读 P0 · 远程页无 Node · 登录态留本机</div>';
  }
  function paBrowserMsg(t){ var e=$('paBrowserStatus'); if(e) e.textContent=t; }
  window.paBrowserMount = function(){
    if(!window.paShell || typeof window.paShell.browserShow !== 'function'){
      paBrowserMsg('内置浏览器仅在桌面壳可用'); return;
    }
    var stage=$('paWinStage'); if(!stage) return;
    var r=stage.getBoundingClientRect();
    var b={x:Math.round(r.left), y:Math.round(r.top+104), width:Math.round(r.width), height:Math.max(120, Math.round(r.height-104))};
    window.paShell.browserShow({bounds:b}).then(function(d){
      if(d && d.ok){ paBrowserMsg('浏览器已就绪 · 输入网址开始'); }
      else { paBrowserMsg('浏览器 ⛔ 起：' + ((d && (d.error || d.message)) || '未知')); }
    }).catch(function(e){ paBrowserMsg('浏览器 ⛔ 起：' + ((e && e.message) || e)); });
  };
  window.paBrowserHide = function(){
    try{ if(window.paShell && window.paShell.browserHide){ window.paShell.browserHide(); } }catch(e){}
  };
  window.paBrowserFullscreen = function(){
    try{
      if(window.paShell && window.paShell.browserFullscreen){
        window.paShell.browserFullscreen().then(function(d){
          if(d && d.ok){ paBrowserMsg(d.fullscreen ? '全屏 · Esc 退出' : '已退出全屏'); }
        });
      }
    }catch(e){}
  };
  window.paBrowserClose = function(){
    try{ if(window.paShell && window.paShell.browserClose){ window.paShell.browserClose(); } }catch(e){}
    paBrowserLast=null;
    var el=$('paBrowserUrl'); if(el) el.value='';
    paBrowserMsg('当前页已关闭');
  };
  window.paBrowserGo = function(){
    var el=$('paBrowserUrl'); var u=el ? String(el.value || '').trim() : '';
    if(!u){ if(el) el.focus(); return; }
    if(!/^https?:\/\//i.test(u)) u='https://' + u;
    if(el) el.value=u;
    paBrowserMsg('载入 ' + u + ' …');
    window.paShell.browserGo(u).then(function(d){
      if(!d || !d.ok) paBrowserMsg('载入失败：' + ((d && (d.error || d.message)) || '未知'));
      else paBrowserMsg('已载入 · 可读当前页或存 note');
    }).catch(function(e){ paBrowserMsg('载入失败：' + ((e && e.message) || e)); });
  };
  function _fmtT(sec){
    sec=Math.max(0,Math.floor(Number(sec)||0));
    return ('0'+Math.floor(sec/60)).slice(-2)+':'+('0'+(sec%60)).slice(-2);
  }
  function _asrTimeline(lines, base){
    var out=[];
    (lines || []).forEach(function(line){
      var m=String(line||'').match(/^\[([\d.]+)s\]\s*(.*)$/);
      if(!m){ if(String(line||'').trim()) out.push(String(line).trim()); return; }
      var t=Number(m[1]||0)+Number(base||0);
      out.push('['+_fmtT(t)+'] '+String(m[2]||'').trim());
    });
    return out.join('\n');
  }
  window.paBrowserRead = function(){
    paBrowserMsg('读当前页…');
    return window.paShell.browserRead().then(function(d){
      if(!d || !d.ok){ paBrowserMsg('读不到：' + ((d && d.error) || '未知')); return; }
      paBrowserLast = d.page || {};
      try{ window.paShell.browserHide(); }catch(e){}
      paBrowserReader(paBrowserLast);
      paBrowserMsg('已提取：' + (paBrowserLast.title || '(无标题)') + ' · 见下方预览');
      return paBrowserLast;
    }).catch(function(e){ paBrowserMsg('读不到：' + ((e && e.message) || e)); });
  };
  function paBrowserReader(p){
    var old=document.getElementById('paBrowserReader'); if(old) old.remove();
    var ov=document.createElement('div'); ov.id='paBrowserReader';
    ov.style.cssText='position:fixed;inset:56px 0 0 64px;z-index:450;background:var(--bg);display:flex;flex-direction:column;padding:12px 18px 10px;box-sizing:border-box;overflow:hidden';
    var v=p.video;
    var hasV=!!(v && v.src);
    var meta=hasV
      ? ('当前视频 · 时长 ' + _fmtT(v.duration) + ' · 进度 ' + _fmtT(v.currentTime))
      : (p.selection ? ('已选中 ' + p.selection.length + ' 字') : '整页文本');
    var cap=p.captions || {};
    var capLen=String(cap.text || '').trim().length;
    ov.innerHTML='<div style="display:flex;align-items:center;gap:10px;flex:none"><b>读页预览</b>'
      + '<span class="pa-hint" style="margin-left:auto;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + esc(p.title || '(无标题)') + '</span>'
      + '<button class="pa-btn pa-btn-ghost" type="button" onclick="paBrowserReaderClose()">返回浏览</button></div>'
      + '<div class="pa-hint" style="margin:4px 0 6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:none">' + esc(p.url || '') + '</div>'
      + '<div class="pa-hint" style="margin-bottom:4px;flex:none">' + meta + '</div>'
      + '<div class="pa-hint" style="margin-bottom:4px;flex:none" id="paReaderCaption">字幕：' + (capLen ? (cap.source || '页面字幕') + ' · ' + capLen + ' 字' : '无（可点下方「语音转字幕」）') + '</div>'
      + (hasV ? '<button class="pa-btn pa-btn-ghost" type="button" id="paReaderAsr" onclick="paBrowserAsrToggle()" style="align-self:flex-start;margin-bottom:6px;flex:none">🎙 用当前视频声音转字幕</button>' : '')
      + '<div id="paReaderAsrLive" style="display:none;flex:none;margin-bottom:6px;border:1px solid #a33;background:#2b0b0b;border-radius:8px;padding:8px 10px;max-height:150px;overflow:auto;font-size:12.5px;color:#fff">'
      + '<div style="display:flex;gap:8px;align-items:center;margin-bottom:4px"><span style="color:#ff6b6b">●</span><b id="paReaderAsrTitle">录音中</b><span id="paReaderAsrClock" style="font-variant-numeric:tabular-nums">00:00</span><span id="paReaderAsrHint" class="pa-hint" style="color:#bbb;margin-left:auto">正在录当前视频声音…</span></div>'
      + '<div id="paReaderAsrText" style="white-space:pre-wrap;line-height:1.6;color:#f2d7d7">等待实时字幕…</div></div>'
      + (hasV
          ? '<div style="display:flex;gap:18px;font-size:12px;margin-bottom:8px;flex:none">'
            + '<label><input type="radio" name="paReaderMode" value="video" checked onchange="paReaderModeChange()"> 只存当前视频信息</label>'
            + '<label><input type="radio" name="paReaderMode" value="page" onchange="paReaderModeChange()"> 连整页正文一起存</label></div>'
          : '')
      + '<div id="paReaderTextHint" class="pa-hint" style="margin-bottom:4px;flex:none"></div>'
      + '<div id="paReaderText" style="flex:1;min-height:80px;white-space:pre-wrap;overflow:auto;border:1px solid var(--line);border-radius:8px;padding:10px;background:var(--card);font-size:12.5px;line-height:1.65"></div>'
      + '<div style="display:flex;gap:8px;align-items:center;margin-top:8px;flex:none">'
      + '<button class="pa-btn pa-btn-main" type="button" onclick="paBrowserReaderSave()">存到第二大脑</button>'
      + '<span id="paReaderMsg" class="pa-hint"></span></div>';
    document.getElementById('paWin').appendChild(ov);
    paReaderModeChange();
  }
  window.paReaderModeChange = function(){
    var p=paBrowserLast || {}; var v=p.video;
    var modeEl=document.querySelector('input[name="paReaderMode"]:checked');
    var mode=modeEl ? modeEl.value : (v ? 'video' : 'page');
    var hint=document.getElementById('paReaderTextHint'); var tx=document.getElementById('paReaderText');
    if(!tx) return;
    var cap=String((p.captions && (p.captions.timeline || p.captions.text)) || '').trim();
    if(v && mode==='video'){
      if(hint) hint.textContent='只保存：页面标题/URL · 当前视频时长/进度 · 字幕 · 页面简介；推荐不会保存。';
      tx.textContent = '当前视频：' + (v.src || '') + '\n\n字幕：\n' + (cap || '（无字幕，可点「语音转字幕」）') + '\n\n页面简介：\n' + (p.description || '(无简介)');
      tx.style.opacity='.8';
    } else {
      if(hint) hint.textContent='整页正文预览（' + String((p.mainText || p.text || '').length) + ' 字）：';
      tx.style.opacity='1';
      tx.textContent=String(p.mainText || p.text || '').slice(0,20000) + (cap ? ('\n\n===== 字幕 =====\n' + cap) : '');
    }
  };
  function paReaderAsrLive(title, hint, text){
    var box=document.getElementById('paReaderAsrLive'); if(!box) return;
    box.style.display='block';
    if(title){ var t=document.getElementById('paReaderAsrTitle'); if(t) t.textContent=title; }
    if(hint !== undefined){ var h=document.getElementById('paReaderAsrHint'); if(h) h.textContent=hint; }
    if(text !== undefined){ var e=document.getElementById('paReaderAsrText'); if(e){ e.textContent=text; e.scrollTop=e.scrollHeight; } }
  }
  function paReaderAsrClockTick(){
    var e=document.getElementById('paReaderAsrClock'); if(!e) return;
    var sec=Math.max(0,Math.floor((Date.now()-paReaderAsrStartMs)/1000));
    e.textContent=('0'+Math.floor(sec/60)).slice(-2)+':'+('0'+(sec%60)).slice(-2);
    if(paReaderAsrEndAt && Date.now() >= paReaderAsrEndAt){ paReaderAsrEndAt=0; if(paReaderAsr){ window.paBrowserAsrToggle(); } }
  }
  window.paBrowserAsrPoll = function(){
    if(!paReaderAsr || !window.paShell || !window.paShell.browserAsrPoll) return;
    window.paShell.browserAsrPoll().then(function(d){
      if(!d || !d.ok){
        paReaderAsrLive('识别失败', (d && (d.error || d.message)) || '未知', '仍在录音，可继续播放视频或点停止。');
        return;
      }
      var state=d.state || {};
      var elapsed=Math.max(0,Math.floor((Date.now()-paReaderAsrStartMs)/1000));
      if(state.ended){ paReaderAsrEndAt=0; if(paReaderAsr){ window.paBrowserAsrToggle(); } return; }
      if(state.paused && elapsed >= 3){ paReaderAsrLive('视频已暂停', '仍在处理已录音频', '继续转写已捕获的音频；如一直无字可点停止。'); }
      if(Number(d.size||0) === 0 && elapsed >= 8){ paReaderAsrLive('没有抓到音频', '已录 ' + elapsed + ' 秒', '可能视频已结束/跨域/静音；点停止或换视频。'); return; }
      if(!d.transcript) return;
      var txt=String(d.transcript.text || '').trim();
      if(!txt){
        paReaderAsrLive('录音中', '已录 ' + elapsed + ' 秒 · 等待识别…', '（还没识别到文字，继续播放视频）');
        return;
      }
      var timeline=_asrTimeline(d.transcript.lines || [], paReaderAsrBaseTime);
      paBrowserLast.captions={ text: txt, timeline: timeline, source: '语音转写（实时）', lines: d.transcript.lines || [], base: paReaderAsrBaseTime };
      var cc=document.getElementById('paReaderCaption');
      if(cc) cc.textContent='字幕：语音转写（实时） · ' + txt.length + ' 字';
      paReaderModeChange();
      paReaderAsrLive('实时字幕', txt.length + ' 字 · 每 5 秒更新', timeline || txt);
      var msg=document.getElementById('paReaderMsg');
      if(msg) msg.textContent='录音中 · 实时字幕 ' + txt.length + ' 字';
    }).catch(function(e){
      paReaderAsrLive('识别失败', '网络/转写异常', String((e && e.message) || e));
    });
  };
  window.paBrowserAsrToggle = function(){
    var btn=document.getElementById('paReaderAsr'); var msg=document.getElementById('paReaderMsg');
    if(!window.paShell || !window.paShell.browserAsrStart){ if(msg) msg.textContent='仅桌面壳可用'; return; }
    if(paReaderAsr){
      paReaderAsr=false;
      if(paReaderAsrTimer){ clearInterval(paReaderAsrTimer); paReaderAsrTimer=null; }
      if(paReaderAsrClockTimer){ clearInterval(paReaderAsrClockTimer); paReaderAsrClockTimer=null; }
      paReaderAsrEndAt=0;
      if(btn){ btn.disabled=true; btn.textContent='转写中…'; }
      window.paShell.browserAsrStop().then(function(d){
        if(btn){ btn.disabled=false; btn.textContent='🎙 用当前视频声音转字幕'; }
        if(!d || !d.ok){ if(msg) msg.textContent='转写失败：' + ((d && (d.error || d.message)) || '未知'); return; }
        var tr=d.transcript || {};
        var txt=String(tr.text || '').trim();
        if(txt){
          var timeline=_asrTimeline(tr.lines || [], paReaderAsrBaseTime);
          paBrowserLast.captions={ text: txt, timeline: timeline, source: '语音转写', lines: tr.lines || [], base: paReaderAsrBaseTime };
          var cc=document.getElementById('paReaderCaption');
          if(cc) cc.textContent='字幕：语音转写 · ' + txt.length + ' 字';
          paReaderModeChange();
          paReaderAsrLive('转写完成', txt.length + ' 字', timeline || txt);
          if(msg) msg.textContent='已转写 ' + txt.length + ' 字';
        } else { paReaderAsrLive('转写完成', '没有识别到文字', '请确认视频在播放、有声音。'); if(msg) msg.textContent='没有识别到文字'; }
      }).catch(function(e){ if(btn){ btn.disabled=false; btn.textContent='🎙 用当前视频声音转字幕'; } if(msg) msg.textContent='转写失败：' + ((e && e.message) || e); });
    } else {
      window.paShell.browserAsrStart().then(function(d){
        if(!d || !d.ok){ if(msg) msg.textContent='录不了：' + ((d && (d.error || d.message)) || '未知'); return; }
        paReaderAsr=true;
        paReaderAsrStartMs=Date.now();
        paReaderAsrBaseTime=Number(d.at || 0);
        var remain=Number(d.duration || 0) - Number(d.at || 0);
        paReaderAsrEndAt = remain > 0 ? (Date.now() + remain * 1000 + 1200) : 0;
        if(btn) btn.textContent='⏹ 停止并转写字幕';
        if(msg) msg.textContent='录音中 · 实时字幕见上方卡片';
        paReaderAsrLive('录音中', '正在采集当前视频音轨…', '等待实时字幕…');
        if(paReaderAsrClockTimer) clearInterval(paReaderAsrClockTimer);
        paReaderAsrClockTick();
        paReaderAsrClockTimer=setInterval(paReaderAsrClockTick, 1000);
        if(paReaderAsrTimer) clearInterval(paReaderAsrTimer);
        paReaderAsrTimer=setInterval(function(){ window.paBrowserAsrPoll(); }, 5000);
        setTimeout(function(){ window.paBrowserAsrPoll(); }, 2500);
      }).catch(function(e){ if(msg) msg.textContent='录不了：' + ((e && e.message) || e); });
    }
  };
  window.paBrowserReaderClose = function(){
    try{ if(paReaderAsr && window.paShell && window.paShell.browserAsrStop) window.paShell.browserAsrStop(); }catch(e){}
    if(paReaderAsrTimer){ clearInterval(paReaderAsrTimer); paReaderAsrTimer=null; }
    if(paReaderAsrClockTimer){ clearInterval(paReaderAsrClockTimer); paReaderAsrClockTimer=null; }
    paReaderAsrEndAt=0;
    paReaderAsr=false;
    var o=document.getElementById('paBrowserReader'); if(o) o.remove();
    try{ window.paBrowserMount(); }catch(e){}
  };
  window.paBrowserReaderSave = function(){
    var p=paBrowserLast; if(!p){ return; }
    var msg=document.getElementById('paReaderMsg');
    var modeEl=document.querySelector('input[name="paReaderMode"]:checked');
    var mode=modeEl ? modeEl.value : (p.video ? 'video' : 'page');
    var title, body;
    if(p.video && mode==='video'){
      title='视频：' + (p.title || '未命名').slice(0,60);
      body='页面：' + (p.url||'') + '\n标题：' + (p.title||'') + '\n当前视频：' + p.video.src
        + '\n时长：' + _fmtT(p.video.duration) + '\n当前进度：' + _fmtT(p.video.currentTime);
      if(p.captions && (p.captions.timeline || p.captions.text)) body += '\n\n字幕（' + (p.captions.source || '页面') + '）：\n' + String(p.captions.timeline || p.captions.text).slice(0,20000);
      else body += '\n\n字幕：无'; 
      if(p.description) body += '\n\n页面简介：\n' + p.description.slice(0,4000);
      if(p.selection) body += '\n\n选中文字：\n' + p.selection.slice(0,4000);
    } else {
      title='网页：' + (p.title || p.url || '未命名').slice(0,60);
      body=(p.url||'') + '\n\n' + (p.selection || p.mainText || p.text || '').slice(0,20000);
      if(p.captions && (p.captions.timeline || p.captions.text)) body += '\n\n===== 字幕 =====\n' + String(p.captions.timeline || p.captions.text).slice(0,20000);
    }
    if(msg) msg.textContent='保存中…';
    return fetch((typeof API !== 'undefined' ? API : '') + '/v9/pa/notes', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({title:title, body:body, tags:[p.video ? '网页视频' : '网页']})})
      .then(function(r){ return r.json(); })
      .then(function(d){
        if(!d || d.ok !== true) throw new Error((d && (d.error || d.message)) || '存不下');
        if(msg) msg.textContent='已存：' + title;
      }).catch(function(e){ if(msg) msg.textContent='存不下：' + ((e && e.message) || e); });
  };
  window.paBrowserSave = function(){ return window.paBrowserRead(); };
  window.paBrowserBack = function(){ try{ window.paShell.browserBack(); }catch(e){} };
  window.paBrowserForward = function(){ try{ window.paShell.browserForward(); }catch(e){} };
  window.paBrowserReload = function(){ try{ window.paShell.browserReload(); }catch(e){} };
  window.addEventListener('resize', function(){
    try{ if(window.PA_WIN_STATE && window.PA_WIN_STATE.route === 'browser' && window.paBrowserMount) window.paBrowserMount(); }catch(e){}
  });

  function todayHtml(){
    var cards = (window.paWinTodayCards ? window.paWinTodayCards() : {html:'', counts:{}});
    return '<h1 class="pa-h1">今天</h1>'
      + '<div class="pa-cards">' + cards.html + '</div>'
      + '<section class="pa-card pa-firstwin" data-card="firstwin" style="margin:10px 0;padding:14px 16px;border:1px solid var(--line);border-radius:10px;background:var(--card)">'
      + '<h2 class="pa-card-h" style="margin:0 0 4px">从笔记开始</h2>'
      + '<div style="color:var(--sub);font-size:12px;line-height:1.6">问本周记下的东西，拿回带出处的答案；没有笔记就先在下面记一笔。</div>'
      + '<div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap">'
      + '<button class="pa-btn pa-btn-main" type="button" onclick="paWinFirstWin()">问本周笔记</button>'
      + '<button class="pa-btn pa-btn-ghost" type="button" onclick="paWinFirstPick()">选文件夹导入</button></div>'
      + '<div id="paWinFirstWinOut" style="margin-top:8px;font-size:13px;line-height:1.65;white-space:pre-wrap"></div>'
      + '</section>'
      + '<div class="pa-cmd">'
      + '<input id="paCmdIn" type="text" placeholder="说一句话，或拖一件东西进来…" autocomplete="off" aria-label="命令带">'
      + '<button class="pa-btn pa-btn-ghost" id="paWinAttachBtn" type="button" onclick="paWinAttachPick()" title="附件：唯存本机 · 缺省不外发；要随本轮出机须逐件勾">📎</button>'
      + '<button class="pa-btn pa-btn-main" type="button" onclick="paWinCmdSend()">发</button></div>'
      + '<div class="pa-hint">本地对话 · 结果与回执来自后端；失败照实 · 出机须授权</div>';
  }

  window.paWinAttachPick = function(){
    try{
      var list = document.getElementById('paAttachList');
      var host = document.getElementById('paWinAttachHost');
      if(list && host && list.parentNode !== host){ host.appendChild(list); }
      if(typeof window.paAttachPick === 'function'){ window.paAttachPick(); return; }
    }catch(e){}
    window.paWinSay('附件入口未载（paAttachPick 不在）');
  };

  window.paWinCmdSend = async function(){
    var el = $('paCmdIn');
    var v = el ? String(el.value || '').trim() : '';
    if(!v) { if(el) el.focus(); return; }
    el.value = '';
    if(/^记\s*[:：]/.test(v)){ return window.paBrainQuick(v); }
    return window.paWinSendReal(v);
  };

  /* 真发送桥（高风险 · 一处定形）：
     旧页 #input → 旧 paSend() → /v9/pa/dialog / 执行链 / 落盘回执；
     ⛔ 复制发送体；新窗只取旧线程最后一条 assistant 回显。 */
  function replyBox(){
    var box = document.getElementById('paWinReply');
    if(box) { box.hidden = false; return box; }
    box = document.createElement('div');
    box.id = 'paWinReply';
    box.style.cssText = 'position:fixed;left:240px;right:340px;bottom:96px;z-index:65;white-space:pre-wrap;'
      + 'padding:10px 12px;border:1px solid var(--line);border-radius:8px;background:var(--card);'
      + 'font-size:13px;line-height:1.65;max-height:38vh;overflow:auto;box-shadow:0 8px 24px rgba(0,0,0,.35)';
    (document.getElementById('paWin') || document.body).appendChild(box);
    return box;
  }
  window.paWinReplyClear = function(){ var b=document.getElementById('paWinReply'); if(b){ b.hidden=true; b.textContent=''; } };

  /* P0 五分鐘首勝：從筆記問本週，帶出處；⛔ 假空態 ／ ⛔ 無據作答。 */
  window.paWinFirstPick = async function(){
    var out = document.getElementById('paWinFirstWinOut');
    if(!out) return;
    if(!window.paShell || typeof window.paShell.pickDirectory !== 'function'){
      out.textContent = '选文件夹需在桌面 PA 内使用（当前页没有本机目录选择桥）。';
      return;
    }
    var pick = null;
    try{ pick = await window.paShell.pickDirectory(); }catch(e){ pick = null; }
    if(!pick || pick.ok !== true || !pick.path){ out.textContent = '未选择文件夹。'; return; }
    out.textContent = '导入中…（仅本机 Markdown）';
    try{
      var r = await fetch((typeof API !== 'undefined' ? API : '') + '/v9/pa/notes/import', {
        method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({path:pick.path}), cache:'no-store'});
      var d = await r.json().catch(function(){ return null; });
      if(!r.ok || !d || d.ok === false){
        out.textContent = '导入失败：' + String((d && (d.message || d.error)) || ('HTTP ' + r.status));
        return;
      }
      var n = d.imported != null ? d.imported : (d.count != null ? d.count : '');
      out.textContent = '已导入' + (n === '' ? '' : (' ' + n + ' 篇')) + '；现在可以问本周笔记。';
    }catch(e){ out.textContent = '导入失败：' + String((e && e.message) || e); }
  };

  window.paWinFirstWin = async function(){
    var out = document.getElementById('paWinFirstWinOut');
    if(!out) return;
    out.textContent = '正在检索本机笔记…';
    var body = {q:'这周记了什么？', limit:3};
    try{ if(typeof paModelSel === 'function'){ var m=paModelSel(); if(m) body.model=m; } }catch(e){}
    var ctl = null, timer = null;
    try{
      try{
        ctl = new AbortController();
        timer = setTimeout(function(){ try{ ctl.abort(); }catch(e){} }, 20000);
      }catch(e){ ctl = null; }
      var r = await fetch((typeof API !== 'undefined' ? API : '') + '/v9/pa/notes/ask', {
        method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body),
        cache:'no-store', signal: ctl ? ctl.signal : undefined});
      var d = await r.json().catch(function(){ return null; });
      if(!r.ok || !d || d.ok === false){
        out.textContent = '问不到：' + String((d && (d.message || d.error)) || ('HTTP ' + r.status));
        return;
      }
      var cits = Array.isArray(d.citations) ? d.citations : [];
      var txt = String(d.answer || '').trim();
      if(!txt && !cits.length){
        out.textContent = '还没有可引用的笔记。先在下面记一笔（例如：今天记：…），再来问。';
        return;
      }
      var esc = function(s){ return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); };
      var todoLines = [];
      cits.forEach(function(c){
        String(c.snippet || '').split(/\n+/).forEach(function(line){
          var s = line.replace(/^[-*\d.\s]+/, '').trim();
          if(s && /待办|TODO|下一步|截止|需要跟/.test(s) && todoLines.length < 3) todoLines.push(s);
        });
      });
      out.innerHTML = '<div>' + esc(txt) + '</div>'
        + (cits.length ? '<div style="margin-top:6px;color:var(--sub);font-size:12px">出处：'
          + cits.map(function(c){ return esc(c.title || c.id || ''); }).join(' ／ ') + '</div>' : '')
        + '<div style="margin-top:6px;color:var(--sub);font-size:12px">待办：'
          + (todoLines.length ? todoLines.map(function(x){ return '· ' + esc(x); }).join('<br>') : '出处中未显式标出（照实）')
          + '</div>'
        + '<div style="margin-top:4px;color:var(--sub);font-size:11px">模型：' + esc(d.model || '默认') + '</div>';
    }catch(e){
      out.textContent = (e && e.name === 'AbortError')
        ? '问不到：20 秒内没有回执（模型可能未就绪／被占）；可稍后重试或换本地 Ollama 模型。'
        : ('问不到：' + String((e && e.message) || e));
    }finally{
      if(timer) clearTimeout(timer);
    }
  };

  window.paWinSendReal = async function(text){
    var box = replyBox();
    box.hidden = false; box.textContent = '发送中…（尚未受理）';
    var oldIn = document.getElementById('input');
    if(!oldIn){ window.paWinSay('旧发送入口 #input 不在'); if(box) box.textContent='旧发送入口不在'; return; }
    if(typeof window.paSend !== 'function'){ window.paWinSay('旧 paSend 未载'); if(box) box.textContent='旧发送链未载'; return; }
    oldIn.value = text;
    var _sb = document.getElementById('paWinStop'); if(_sb){ _sb.disabled = false; }
    window.__paWinSendStopped = false;
    window.__paWinStopResolve = null;
    window.paWinSay('发送中…（尚未受理）');
    try{
      var _sendP;
      if(typeof window.sendAgent === 'function' && typeof activeThread === 'function'){
        var _t = activeThread();
        if(typeof addMsg === 'function') addMsg('user', text);
        if(typeof setBusy === 'function') setBusy(true);
        if(typeof paSetState === 'function') paSetState('running');
        if(typeof paRun === 'object' && paRun){ paRun.busy = true; paRun.threadId = _t.id; }
        _sendP = window.sendAgent(_t, text).finally(function(){
          if(typeof setBusy === 'function') setBusy(false);
          if(typeof paRun === 'object' && paRun){ paRun.busy = false; paRun.threadId = null; }
        });
      } else {
        oldIn.value = text;
        _sendP = window.paSend();
      }
      _sendP.catch(function(){});
      var _stopP = new Promise(function(res){ window.__paWinStopResolve = res; });
      var _slow = new Promise(function(res){ setTimeout(function(){ res('__timeout'); }, 30000); });
      var _race = await Promise.race([_sendP, _stopP, _slow]);
      if(_race === '__timeout'){
        window.__paWinStopResolve = null;
        if(box) box.textContent = '30s 内未到后端（请求可能未发出）—— 请回主聊天页重发';
        window.paWinSay('未到后端');
        var sbT = document.getElementById('paWinStop'); if(sbT){ sbT.disabled = true; }
        return;
      }
      if(window.__paWinSendStopped){
        window.__paWinStopResolve = null;
        return;
      }
      window.__paWinStopResolve = null;
    }
    catch(e){ if(_sb){ _sb.disabled = true; } window.paWinSay('发送 ⛔ 成'); box.textContent = '发送失败：' + ((e && e.message) || e); return; }
    var reply = '';
    try{
      var nodes = document.querySelectorAll('#thread .msg');
      for(var i = nodes.length - 1; i >= 0; i--){
        var b = nodes[i].querySelector && nodes[i].querySelector('.bubble');
        if(b){ reply = String(b.innerText || b.textContent || '').trim(); break; }
      }
    }catch(e){}
    var run = (typeof paRun !== 'undefined') ? paRun : null;
    var state = run ? (run.state || '') : '';
    var rec = run && run.receipt ? ' · 回执：有' : ' · 回执：未给';
    if(_sb){ _sb.disabled = true; }
    box.textContent = (reply || '（旧线程未取到回文）') + '\n\n— ' + (state || '状态未给') + rec;
    window.paWinSay(state === 'done' ? '回已到' : ('状态：' + (state || '未给')));
    try{ if(window.paWinLiveRefresh) window.paWinLiveRefresh(); }catch(e){}
  };

  /* P2-9：Summon 真发（唯调 paWinSendReal；⛔ 造第二发送体） */
  window.paWinSummonSend = function(){
    var inp = document.getElementById('paSummonIn');
    var v = inp ? String(inp.value || '').trim() : '';
    if(!v){ if(inp) inp.focus(); return; }
    if(inp) inp.value = '';
    var s = document.getElementById('paSummon');
    if(s){ s.hidden = true; s.classList.remove('on'); }
    try{ if(typeof window.paWinSummonClose === 'function') window.paWinSummonClose(false); }catch(e){}
    return window.paWinSendReal(v);
  };

  /* 计划卡（⛔ 直接执行 · PRD §8.4）*/
  window.paWinPlan = function(txt){
    var st = window.PA_WIN_STATE;
    var id = 'p' + Date.now();
    var risk = /云|上传|发布|发到|发给|外发|公众号|知乎|小红书|删除|付款|转账/.test(txt) ? 'L3' : 'L2';
    st.approvals.unshift({
      id: id, level: risk, risk: risk === 'L3' ? '高风险' : '要你拍',
      what: txt, why: '你刚说的一句', cost: '¥0.00',
      egress: risk === 'L3' ? '出什么：带样例数据 ｜ 给谁：云服务商 ｜ 为什么：为了试跑一遍 ｜ 多久删：完事 1 小时内删' : ''
    });
    st.route = 'today';
    window.paWinRenderRoute();
    var rail = document.querySelectorAll('.pa-rail-b');
    for(var i = 0; i < rail.length; i++) rail[i].classList.toggle('on', rail[i].getAttribute('data-r') === 'today');
    window.paWinSay('出了计划卡 · 在右边等你点头');
    if(window.paWinNowRender) window.paWinNowRender();
  };

  /* ── 停（≤1s · PRD §8.8）── */
  window.paWinStop = function(){
    /* 先解旧窗口之等待（即使 paRun 未 busy/请求未发，也必须能停）。 */
    if(window.__paWinStopResolve){
      window.__paWinSendStopped = true;
      try{ window.__paWinStopResolve(); }catch(e){}
      window.__paWinStopResolve = null;
      var sb0 = document.getElementById('paWinStop'); if(sb0){ sb0.disabled = true; }
      var rb0 = document.getElementById('paWinReply'); if(rb0){ rb0.hidden = false; rb0.textContent = '已停（等待/未发）'; }
      window.paWinSay('已停（等待/未发）');
      try{ if(typeof window.paStop === 'function') window.paStop(); }catch(e){}
      return;
    }
    /* 产品真任务：先取消 RunService 的 run（/v9/agent/runs/{id}/cancel），⛔ 只 abort 前端。 */
    var _rid = '';
    try{
      if(typeof paRun !== 'undefined' && paRun && paRun.runId) _rid = String(paRun.runId);
      if(!_rid && window.paWinLiveRuns){
        var _live = window.paWinLiveRuns() || [];
        for(var _i=0; _i<_live.length; _i++){
          var _st = String(_live[_i].state || '');
          if(_st === 'running' || _st === 'queued'){ _rid = String(_live[_i].id || ''); break; }
        }
      }
    }catch(e){}
    if(_rid && typeof window.paCancelRun === 'function'){
      window.paCancelRun(_rid);
      var _sb1 = document.getElementById('paWinStop'); if(_sb1){ _sb1.disabled = true; }
      var _rb1 = document.getElementById('paWinReply');
      if(_rb1){ _rb1.hidden = false; _rb1.textContent = '停止请求已发（run ' + _rid.slice(-8) + '）'; }
      window.paWinSay('停止请求已发 · 等后端收口');
      return;
    }
    /* 旧链路兜底：先停旧 paRun（/v9/cancel ＋ abort），再走本地演示态。 */
    try{
      if(typeof paRun !== 'undefined' && paRun.busy && typeof window.paStop === 'function'){
        window.paStop();
        window.__paWinSendStopped = true;
        try{ if(window.__paWinStopResolve){ window.__paWinStopResolve(); window.__paWinStopResolve = null; } }catch(e){}
        var sb = document.getElementById('paWinStop'); if(sb){ sb.disabled = true; }
        var rb = document.getElementById('paWinReply');
        if(rb){ rb.hidden = false; rb.textContent = '已停（真任务）'; }
        window.paWinSay('已停（真任务）');
        return;
      }
    }catch(e){}
    var st = window.PA_WIN_STATE;
    var t = st.currentTask;
    if(t && (t.done || t.receipt || Number(t.pct || 0) >= 100)){
      window.paWinSay('这一件已完成 · 停只对在跑');
      return;
    }
    var running = (st.runs || []).filter(function(r){ return r.state === 'running'; });
    var t0 = (window.performance && performance.now) ? performance.now() : Date.now();
    running.forEach(function(r){ r.state = 'stopped'; });
    var dt = ((window.performance && performance.now) ? performance.now() : Date.now()) - t0;
    window.paWinPerf = window.paWinPerf || {};
    window.paWinPerf.stopMs = Math.round(dt * 10) / 10;
    if(running.length){
      window.paWinLedgerAdd('停了「' + (running[0].name || '在跑之事') + '」', '你', '¥0.00', '已停');
      window.paWinSay('已停');
    } else {
      window.paWinSay('没有在跑的');
    }
    if(window.paWinNowRender) window.paWinNowRender();
    if(window.paWinRouteIs('focus')) window.paWinRenderRoute();
  };

  /* ── 完成（PRD §3.3 · 卡底出回执）—— 与「停」分明：停 = 中止，完成 = 收尾 ── */
  window.paWinFinish = function(){
    var st = window.PA_WIN_STATE;
    var t = st.currentTask;
    if(!t) { window.paWinSay('没有正看着的一件'); return; }
    var i = -1;
    (st.runs || []).forEach(function(r, k){ if(i < 0 && r.name === t.goal) i = k; });
    if(i >= 0){ st.runs[i].state = 'done'; st.runs[i].pct = 100; }
    t.pct = 100;
    t.steps = window.paWinMockSteps(100);
    if(window.paWinMockReceipt) t.receipt = window.paWinMockReceipt(t);
    window.paWinLedgerAdd('做完了「' + t.goal + '」', '你', t.cost || '¥0.00', '已完');
    window.paWinRenderRoute();
    if(window.paWinNowRender) window.paWinNowRender();
    window.paWinSay('做完了 · 回执在下面');
  };

  /* ── 账（1b-1 真数 · PRD §3.4 ／ §8.10）──
     后端账（/v9/pa/ledger ／ /v9/pa/cost）只读；本机动作单列，明书「未入库」。 */
  function realHash(r){
    var note = String((r && r.note) || '');
    var m = note.match(/件散列\s*([0-9a-fA-F]{8,64})/);
    return m ? m[1] : '';
  }
  function fmtInt(n){
    try{ return Number(n || 0).toLocaleString('zh-CN'); }catch(e){ return String(n || 0); }
  }
  function errText(key){
    if(window.paWinLiveErr) return window.paWinLiveErr(key);
    var s2 = (window.PA_WIN_LIVE && window.PA_WIN_LIVE.src) ? window.PA_WIN_LIVE.src[key] : null;
    return s2 ? (s2.error || ('HTTP ' + s2.status)) : '还没读到';
  }

  function ledgerHtml(){
    var L = window.PA_WIN_LIVE || {};
    var led = L.ledger, cost = L.cost;
    var costLine;
    if(cost && cost.ok){
      var tk = (cost.tokens && cost.tokens['合计']);
      var mn = (cost.money && cost.money['合计']);
      costLine = '今账：' + fmtInt(tk) + ' tokens · ¥'
        + (mn == null ? '—' : Number(mn).toFixed(2)) + ' · ' + fmtInt(cost['轮数']) + ' 轮';
    } else {
      costLine = '花费：' + errText('cost');
    }
    var realBody;
    if(!led || !led.ok){
      realBody = '<div class="pa-empty warn">读不到后端账：' + esc(errText('ledger'))
        + '<button class="pa-btn pa-btn-ghost pa-retry" type="button" onclick="paWinLiveRefresh()">再读一次</button></div>';
    } else if(!(led.items || []).length){
      realBody = '<div class="pa-empty">后端账上还没有记下的事。</div>';
    } else {
      realBody = (led.items || []).map(function(r, i){
        var h = realHash(r);
        var st = String(r.status || '');
        return '<div class="pa-lg" onclick="paWinLedgerOpenReal(' + i + ')" tabindex="0" role="button"'
          + ' onkeydown="if(event.key===\'Enter\')paWinLedgerOpenReal(' + i + ')">'
          + '<span class="pa-lg-t">' + esc(String(r.created || '').slice(5)) + '</span>'
          + '<span class="pa-lg-a">' + esc(r.title || '') + '</span>'
          + '<span class="pa-lg-c">' + esc(st === 'done' ? '已完' : (st || '—')) + '</span>'
          + '<span class="pa-lg-h" title="件散列（后端记）">' + esc(h || '无指纹') + '</span></div>';
      }).join('');
    }
    var locals = (window.PA_WIN_STATE.ledger || []).map(function(r, i){
      return '<div class="pa-lg local" onclick="paWinLedgerOpen(' + i + ')" tabindex="0" role="button"'
        + ' onkeydown="if(event.key===\'Enter\')paWinLedgerOpen(' + i + ')">'
        + '<span class="pa-lg-t">' + esc(r.at) + '</span>'
        + '<span class="pa-lg-a">' + esc(r.what) + '</span>'
        + '<span class="pa-lg-c">' + esc(r.cost) + '</span>'
        + '<span class="pa-lg-h" title="本机链指纹（未入库）">' + esc(r.hash) + '</span></div>';
    }).join('');
    return '<h1 class="pa-h1">账</h1>'
      + '<div class="pa-sum">' + esc(costLine) + '</div>'
      + '<div class="pa-lg-hd"><span>立</span><span>事</span><span>态</span><span>指纹</span></div>'
      + '<div class="pa-lgs">' + realBody + '</div>'
      + '<h2 class="pa-h2">本机动作 <span class="pa-tag">未入库</span></h2>'
      + '<div class="pa-lgs">' + (locals || '<div class="pa-empty">这一会儿还没有本机动作。</div>') + '</div>'
      + '<div class="pa-hint">后端账只读；本机动作带链指纹、明书未入库 · 点一行看明细 ｜ ' + chainLine() + '</div>'
      + '<div id="paLedgerDetail"></div>';
  }

  /* 本机链核：逐行 prev 须等于下一行 hash（⛔ 后端账 · 后端不带链）。 */
  function chainLine(){
    var rows = window.PA_WIN_STATE.ledger || [];
    var broken = 0;
    for(var i = 0; i < rows.length; i++){
      var nxt = rows[i + 1];
      if(nxt && rows[i].prev !== nxt.hash) broken++;
      if(!nxt && rows[i].prev) broken++;
    }
    return '本机链 ' + rows.length + ' 行 · ' + (broken ? ('⚠ ' + broken + ' 处断') : '复算 一致');
  }

  window.paWinLedgerOpenReal = function(i){
    var d = (window.PA_WIN_LIVE && window.PA_WIN_LIVE.ledger) || {};
    var r = (d.items || [])[i];
    var box = $('paLedgerDetail');
    if(!r || !box) return;
    box.innerHTML = '<div class="pa-rc-open"><div class="pa-rc-h">' + esc(r.title || '')
      + ' <span class="pa-hash">' + esc(realHash(r) || '无指纹') + '</span></div>'
      + '<ul class="pa-rqs">'
      + '<li class="pa-rq"><span class="pa-rq-k">件号</span><span class="pa-rq-v">' + esc(r.id || '—') + '</span></li>'
      + '<li class="pa-rq"><span class="pa-rq-k">状态</span><span class="pa-rq-v">' + esc(r.status || '—') + '</span></li>'
      + '<li class="pa-rq"><span class="pa-rq-k">立</span><span class="pa-rq-v">' + esc(r.created || '—') + '</span></li>'
      + '<li class="pa-rq"><span class="pa-rq-k">期</span><span class="pa-rq-v">' + esc(r.due || '—') + '</span></li>'
      + '<li class="pa-rq"><span class="pa-rq-k">用途</span><span class="pa-rq-v">' + esc(r['用途'] || '—') + '</span></li>'
      + '<li class="pa-rq"><span class="pa-rq-k">注</span><span class="pa-rq-v">' + esc(r.note || '—') + '</span></li>'
      + '</ul><div class="pa-hint">后端账不带链指纹；件散列随件走。本机动作之链见上。</div></div>';
  };

  window.paWinLedgerOpen = function(i){
    var r = (window.PA_WIN_STATE.ledger || [])[i];
    var box = $('paLedgerDetail');
    if(!r || !box) return;
    box.innerHTML = '<div class="pa-rc-open"><div class="pa-rc-h">' + esc(r.what)
      + ' <span class="pa-hash">' + esc(r.hash) + '</span></div>'
      + '<ul class="pa-rqs">'
      + '<li class="pa-rq"><span class="pa-rq-k">什么时候</span><span class="pa-rq-v">' + esc(r.at) + '</span></li>'
      + '<li class="pa-rq"><span class="pa-rq-k">谁做的</span><span class="pa-rq-v">' + esc(r.who) + '</span></li>'
      + '<li class="pa-rq"><span class="pa-rq-k">花了多少</span><span class="pa-rq-v">' + esc(r.cost) + '</span></li>'
      + '<li class="pa-rq"><span class="pa-rq-k">前一条指纹</span><span class="pa-rq-v">' + esc(r.prev || '—') + '</span></li>'
      + '<li class="pa-rq"><span class="pa-rq-k">复算</span><span class="pa-rq-v">' + (paWinHash(r.at + '|' + (r.what || '') + '|' + (r.prev || '')) === r.hash ? '一致 · 指纹可自证' : '不一致 · 有改动') + '</span></li>'
      + '</ul>'
      + '<button class="pa-btn pa-btn-ghost" type="button" onclick="paWinExportLedger()">导出</button></div>';
  };

  window.paWinExportLedger = function(){
    var L = (window.PA_WIN_LIVE && window.PA_WIN_LIVE.ledger) || {};
    var payload = {
      源:'GET /v9/pa/ledger',
      取刻:(window.PA_WIN_LIVE && window.PA_WIN_LIVE.at) || '',
      后端账:(L && L.items) || [],
      本机动作:window.PA_WIN_STATE.ledger || []
    };
    paWinDownload('账.json', JSON.stringify(payload, null, 2));
  };
  window.paWinExportReceipt = function(){
    var t = window.PA_WIN_STATE.currentTask || {};
    paWinDownload('回执.json', JSON.stringify(t.receipt || t, null, 2));
  };
  function paWinDownload(name, text){
    try{
      var b = new Blob([text], {type:'application/json'});
      var a = document.createElement('a');
      a.href = URL.createObjectURL(b); a.download = name;
      document.body.appendChild(a); a.click();
      setTimeout(function(){ URL.revokeObjectURL(a.href); a.remove(); }, 500);
      window.paWinSay('已导出 ' + name);
    }catch(e){ window.paWinSay('这台机器不让下载 · 复制上面的字即可'); }
  }

  /* ── 只读投影：席 ／ 库 ／ 门（PRD §4.8 · 缺者显「未接」）── */
  /* ⭐ PA v1.1 S2b（承迭代单 §二 S2）：**席**面接真源 `GET /v9/pa/registry`（20 卡 ·
     active 2 ／ pending 18）—— 取数在 live.js（端表一处），本处唯渲。
     判据：① 20 卡逐张照实（⛔ 手搓 ／ ⛔ mock 充真）；② counts 取后端，逐卡复点，⛔ 齐 ⇒ 明书；
           ③ 四类 self ／ seat ／ cli ／ ssh 逐类实点（源内无 ssh ⇒ 0 · ⛔ 装作有）；
           ④ pending 显「待入册」∧ **不可派**（后端 `dispatchable` 非 true ⇒ 不可派；
              pending 即便后端误标 true 亦按本面之判据压为不可派 —— 承迭代单 §二 S2）；
           ⑤ 本面无批准 ／ 无写 ／ 无派活之钮（只读投影 · ⛔ 本版不做批准写）。
     ⚠ 缺字段显「未接」，⛔ 假数（迭代单 §三）。 */
  var AG_KINDS = [
    {k:'self', t:'自身'},
    {k:'seat', t:'席'},
    {k:'cli',  t:'CLI'},
    {k:'ssh',  t:'SSH'}
  ];
  function agAt(v){
    var s = String(v == null ? '' : v);
    var m = s.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/);
    if(m) return m[2] + '-' + m[3] + ' ' + m[4] + ':' + m[5];
    return s;
  }
  function agVal(v){
    return (v == null || v === '') ? '未接' : String(v);
  }
  function agErr(){
    var L = window.PA_WIN_LIVE || {};
    var R = L.registry;
    if(R && typeof R === 'object'){
      if(R.message) return String(R.message);
      if(R.error) return String(R.error);
    }
    return errText('registry');
  }
  function agCard(c){
    c = c || {};
    var st = String(c.status == null ? '' : c.status);
    var pend = (st === 'pending');
    var active = (st === 'active');
    /* ④ pending ⛔ 可派：本面之判据压一道 —— 后端 dispatchable 非 true ∨ 非 active ⇒ 不可派 */
    var disp = (c.dispatchable === true) && active && !pend;
    var statusTxt = active ? '在册' : (pend ? '待入册' : (st || '未接'));
    var statusColor = active ? 'var(--green)' : (pend ? 'var(--amber)' : 'var(--sub)');
    var last = (c.probe_at != null && c.probe_at !== '')
      ? agAt(c.probe_at)
      : agAt(c.enriched_at);
    var name = (c.name == null || c.name === '') ? agVal(c.id) : String(c.name);
    var meta = '<span>成本 ' + esc(agVal(c.cost)) + '</span>'
      + '<span>边界 ' + esc(agVal(c.boundary)) + '</span>'
      + '<span>脆性 ' + esc(agVal(c.fragility)) + '</span>'
      + '<span>上次 ' + esc(last || '未接') + '</span>';
    return '<article class="pa-agx"'
      + ' data-id="' + esc(c.id) + '" data-kind="' + esc(c.kind) + '"'
      + ' data-status="' + esc(st) + '" data-dispatchable="' + (disp ? '1' : '0') + '"'
      + ' aria-label="' + esc(name + ' · ' + statusTxt + ' · ' + (disp ? '可派' : '不可派')) + '"'
      + ' style="border:1px solid var(--border);border-radius:10px;padding:9px 11px;'
      + 'margin:0 0 8px;background:var(--card2);min-width:0">'
      + '<div style="display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;min-width:0">'
      + '<b style="font-size:13px;font-weight:600;overflow-wrap:anywhere">' + esc(name) + '</b>'
      + '<span style="font-size:11px;color:var(--sub);border:1px solid var(--border);'
      + 'border-radius:999px;padding:0 7px;white-space:nowrap">' + esc(agVal(c['class'])) + '</span>'
      + '<span style="font-size:11px;color:' + statusColor + ';border:1px solid ' + statusColor + ';'
      + 'border-radius:999px;padding:0 7px;white-space:nowrap">' + esc(statusTxt) + '</span>'
      + '<span style="font-size:11px;color:' + (disp ? 'var(--green)' : 'var(--sub)') + ';'
      + 'border:1px dashed ' + (disp ? 'rgba(63,185,80,.5)' : 'var(--border)') + ';'
      + 'border-radius:999px;padding:0 7px;white-space:nowrap">' + (disp ? '可派' : '不可派') + '</span>'
      + '</div>'
      + '<div style="display:flex;gap:4px 12px;flex-wrap:wrap;font-size:11.5px;color:var(--sub);'
      + 'line-height:1.55;margin-top:4px;min-width:0">' + meta + '</div>'
      + (c.history_session_id
          ? '<div style="font-size:11px;color:var(--sub);opacity:.8;margin-top:2px"'
            + ' title="会话历史（只读）">前史 ' + esc(String(c.history_session_id).slice(0, 8))
            + (c.session_format ? ' · ' + esc(String(c.session_format)) : '') + '</div>'
          : '')
      + '</article>';
  }
  window.paWinAgentsState = function(){
    var L = window.PA_WIN_LIVE || {};
    var R = L.registry || {};
    var cards = Array.isArray(R.cards) ? R.cards : [];
    var kinds = {};
    AG_KINDS.forEach(function(x){ kinds[x.k] = 0; });
    var nActive = 0, nPending = 0;
    cards.forEach(function(c){
      var k = String((c && c.kind) || '');
      if(kinds[k] != null) kinds[k]++;
      var st = String((c && c.status) || '');
      if(st === 'active') nActive++;
      if(st === 'pending') nPending++;
    });
    return {
      total: cards.length, active: nActive, pending: nPending, kinds: kinds,
      dispatchable: cards.filter(function(c){ return c && c.dispatchable === true && String(c.status) === 'active'; }).length,
      counts: R.counts || null, state: R.state || null, source: R.source || '',
      generated_at: R.generated_at || null
    };
  };
  function agentsHtml(){
    var L = window.PA_WIN_LIVE || {};
    var head = '<h1 class="pa-h1">席</h1>';
    if(!L.at){
      return head + '<div class="pa-skel" aria-label="正在读"><i style="width:82%"></i>'
        + '<i style="width:64%"></i><i style="width:74%"></i></div>';
    }
    var src = (L.src || {}).registry;
    var R = L.registry;
    if(!src || !src.ok || !R || R.ok === false){
      return head + '<div class="pa-empty warn">读不到席册：' + esc(agErr())
        + '<button class="pa-btn pa-btn-ghost pa-retry" type="button" onclick="paWinLiveRefresh()">再读一次</button></div>'
        + '<div class="pa-hint" title="源：GET /v9/pa/registry">只读 · 不派活 ／ 不批准</div>';
    }
    var cards = Array.isArray(R.cards) ? R.cards : [];
    var counts = (R.counts && typeof R.counts === 'object') ? R.counts : {};
    var S = window.paWinAgentsState();
    var cTotal = (counts.total != null) ? Number(counts.total) : S.total;
    var cActive = (counts.active != null) ? Number(counts.active) : S.active;
    var cPending = (counts.pending != null) ? Number(counts.pending) : S.pending;
    var mism = (cTotal !== S.total) || (cActive !== S.active) || (cPending !== S.pending);
    var chips = '<div class="pa-kinds">'
      + '<span class="pa-kind" title="counts.total（后端实点）"><b>' + esc(cTotal) + '</b> 卡</span>'
      + '<span class="pa-kind" title="counts.active（后端实点）"><b>' + esc(cActive) + '</b> 在册</span>'
      + '<span class="pa-kind" title="counts.pending（后端实点）"><b>' + esc(cPending) + '</b> 待入册</span>'
      + AG_KINDS.map(function(x){
          var n = S.kinds[x.k] || 0;
          return '<span class="pa-kind' + (n ? '' : ' off') + '"'
            + ' title="逐卡实点（kind=' + x.k + '）"><b>' + n + '</b> ' + x.t + '</span>';
        }).join('')
      + '</div>';
    var body = cards.length
      ? cards.map(agCard).join('')
      : '<div class="pa-empty">席册还是空的（源内 0 卡）。</div>';
    var took = agAt(R.generated_at);
    var sub = '<div class="pa-sum">只读 · 不派活 ／ 不批准 ｜ 待入册者不可派'
      + (took ? (' ｜ 取数 ' + esc(took)) : '') + '</div>';
    var note = mism
      ? ('⚠ 计数与逐卡不符（后端 ' + esc(cTotal + '/' + cActive + '/' + cPending)
         + '，逐卡 ' + S.total + '/' + S.active + '/' + S.pending + '）')
      : '';
    return head + sub + chips + body
      + (note ? '<div class="pa-hint">' + note + '</div>' : '')
      + '<div class="pa-hint" title="源：GET /v9/pa/registry · 只读端 · 缺字段显「未接」">'
      + '四类逐卡实点 ｜ 缺的显「未接」</div>';
  }
  function vaultHtml(){
    var L = window.PA_WIN_LIVE || {};
    var th = L.threads, v = L.vault;
    var sess = (th && th.ok) ? ((th.local_sessions || []).length + (th.threads || []).length) : null;
    var rows = [
      {t:'对话记录', lv: sess == null ? '未接' : '本机', n: sess == null ? '—' : (sess + ' 条'), off: sess == null},
      {t:'账与指纹', lv:'本机', n:'见「账」', off:false},
      {t:'云上备份', lv:'未接', n:'—', off:true}
    ];
    var html = rows.map(function(x){
      return '<div class="pa-vt' + (x.off ? ' off' : '') + '"><span>' + esc(x.t) + '</span>'
        + '<span>' + esc(x.lv) + '</span><span>' + esc(x.n) + '</span></div>';
    }).join('');
    var note = (v && v.ok)
      ? '只读 · 东西在本机，出机要你点头'
      : '只读 · 本机能读的已列；库册端未接（Phase 1 后端）';
    return '<h1 class="pa-h1">库</h1>' + html + '<div class="pa-hint">' + esc(note) + '</div>';
  }
  function doorsHtml(){
    var L = window.PA_WIN_LIVE || {};
    var g = L.grants, pm = L.permission;
    var rows = [];
    if(g && g.ok){
      var missing = String(g.state || '') === 'missing' || !(g.grants || []).length;
      rows.push({s:'授权册', lv: missing ? '默认拒绝' : ((g.count || 0) + ' 条'),
                 t: missing ? '未配置（默认拒绝）' : '已配置', off: missing});
    } else {
      rows.push({s:'授权册', lv:'未接', t: errText('grants'), off:true});
    }
    if(pm && pm.ok){
      rows.push({s:'权限级', lv: pm.level || '—', t:'本机', off:false});
    } else {
      rows.push({s:'权限级', lv:'未接', t: errText('permission'), off:true});
    }
    rows.push({s:'改文件 · 只在报告目录', lv:'L2', t:'长期', off:false});
    rows.push({s:'跑云端 · 要先问', lv:'L3', t:'一次一码', off:false});
    var html = rows.map(function(x){
      return '<div class="pa-dr' + (x.off ? ' off' : '') + '"><span>' + esc(x.s) + '</span><span>' + esc(x.lv) + '</span>'
        + '<span>' + esc(x.t) + '</span><span class="pa-sub">' + (x.off ? '未接' : '撤 ⇒ 找我') + '</span></div>';
    }).join('');
    return '<h1 class="pa-h1">门</h1>' + html + '<div class="pa-hint">门只在有风险的地方出现</div>';
  }

  /* ── 焦点：一件事 ── */
  window.paWinFocus = function(id){
    var st = window.PA_WIN_STATE;
    var pool = (st.runs || []).concat((window.paWinLiveRuns && window.paWinLiveRuns()) || []);
    var run = pool.filter(function(r){ return r.id === id; })[0] || pool[0];
    if(!run) { window.paWinSay('没有在跑的事'); return; }
    var task = {
      goal: run.name, who:'你', when:'刚起', budget:'¥2.00',
      pct: run.pct, cost: run.cost,
      steps: window.paWinMockSteps(run.pct)
    };
    if(run.state === 'done'){
      task.pct = 100; task.steps = window.paWinMockSteps(100);
      if(window.paWinMockReceipt) task.receipt = window.paWinMockReceipt(task);
    }
    st.currentTask = task;
    document.body.classList.add('pa-focus');
    var stage = $('paWinStage');
    if(stage) stage.innerHTML = window.paWinTaskCardHtml(task);
    if(window.paWinNowRender) window.paWinNowRender();
  };

  /* ── 命令面板（Ctrl+K）── */
  window.paWinPaletteToggle = function(){
    var el = $('paWinPalette');
    if(!el) return;
    if(!el.hidden){ el.hidden = true; return; }
    el.hidden = false;
    var inp = $('paPaletteIn');
    if(inp){ inp.value = ''; inp.focus(); }
  };
  window.paWinPaletteGo = function(){
    var inp = $('paPaletteIn');
    var q = inp ? String(inp.value || '').trim() : '';
    var map = {'今天':'today','席':'agents','账':'ledger','库':'vault','门':'doors'};
    if(map[q]) window.paWinGo(map[q]);
    else window.paWinSay('没找着 · 试「今天」「账」「席」');
    var el = $('paWinPalette'); if(el) el.hidden = true;
  };

  /* ── 旧面（一步可达 · 旧 DOM 一字未删）── */
  window.paWinLegacy = function(){
    document.body.classList.remove('pa-win-on');
    var w = $('paWin'); if(w){ w.hidden = true; w.setAttribute('aria-hidden', 'true'); }
    window.paWinSetFlag(false);
    try{ if(typeof window.paMore === 'function') window.paMore(true); }catch(e){}
  };

  /* ── 挂载 ── */
  window.paWinMount = function(){
    var w = $('paWin');
    if(!w) return false;
    if(!w.__built){
      w.innerHTML = shellHtml() + summonHtml() + '<div class="pa-palette" id="paWinPalette" hidden>'
        + '<input id="paPaletteIn" type="text" placeholder="去「今天」「席」「账」「库」「门」…"'
        + ' onkeydown="if(event.key===\'Enter\')paWinPaletteGo()">'
        + '<div class="pa-palette-h">Enter 去 · Esc 关</div></div>';
      w.__built = true;
    }
    window.paWinSummonBindKeys();
    var lb = $('paBtnLegacy');
    if(lb) lb.hidden = !window.paWinDevOn();
    var first = window.paWinFlagOn();
    window.paWinSetFlag(first);
    if(!first) return false;
    document.body.classList.add('pa-win-on');
    w.hidden = false;
    w.setAttribute('aria-hidden', 'false');
    window.paWinGo('today');
    if(window.paWinLiveRefresh) window.paWinLiveRefresh();
    return true;
  };

  /* 入口：旧面之「更多」里加一行（⛔ 改旧 DOM 结构 · 只追加一节）*/
  function addMoreEntry(){
    var body = $('paMoreBody');
    if(!body || body.querySelector('#paMoreWinV1')) return;
    var sec = document.createElement('details');
    sec.className = 'mgrp';
    sec.id = 'paMoreWinV1';
    sec.innerHTML = '<summary>④ 新窗 v1（试看 · 静态）</summary>'
      + '<section class="msec"><h6>新窗 v1</h6>'
      + '<div class="msrc">一屏说清今天：四卡 ＋ 一句话 ＋ 右栏。现在是静态试看（数是真的样子，事是假的）。</div>'
      + '<div style="margin-top:8px"><button class="pa-btn pa-btn-main" type="button" onclick="paWinEnter()">进新窗试看</button>'
      + ' <span class="pa-sub">随时可回旧面</span></div></section>';
    body.appendChild(sec);
  }
  window.paWinEnter = function(){
    window.paWinSetFlag(true);
    if(!window.paWinMount()) location.reload();
  };

  function boot(){
    var on = window.paWinMount();
    addMoreEntry();
    if(!on){
      /* 关态：只为「更多」里那一行服务 ⇒ 旧面其余不动 */
      document.body.classList.remove('pa-win-on');
    }
  }
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();