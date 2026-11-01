/* PA 窗 v1 / 1b-1 · 真数接线（CW b2a5182 · 2026-10-27 · 承 PRD v1 §7 ／ 令 3444）
   界（硬）：只接现有端点；⛔ 动后端 ／ ⛔ 新依赖 ／ ⛔ 假数据充真 ／ ⛔ 删旧面。
   三态：空（端点 ok 且无件 ⇒ 「—」＋人话）／ 错（非 200 或抛错 ⇒ 人话＋因＋再读）／
        降级（degradations[] 或 today 行「缺」⇒ 明书，⛔ 空白充好）。
   端点（本刻一手探 · 2026-10-27 10:1x）：
     /v9/pa/today 200（一处定形 · 内含 context／ledger／pes.runs／threads 之数）
     /v9/pes/runs 200（runs:[] ＋ degradations:[registry_file_missing]）
     /v9/pa/threads 200 ／ /v9/pa/context 200
     /v9/audit/approvals 400（需 session_id；且唯载已决历史 ⇒ ⛔ 充「待审」）
     /v9/pa/roster 200 ／ /v9/pa/seats 200 ／ /v9/pa/ledger 200 ／ /v9/pa/cost 200
     /v9/pa/grants 200（state:missing）／ /v9/pa/permission 200 ／ /v9/pa/build 200
     /v9/pa/vault 404 ／ /v9/pa/stop 404 ／ /v9/pa/egress 404 ⇒ 未接（Phase 1）
*/
(function(){
  'use strict';

  var T = 5000;
  var EP = {
    today:'/v9/pa/today', runs:'/v9/pes/runs', agent_runs:'/v9/agent/runs',
    threads:'/v9/pa/threads',
    context:'/v9/pa/context', approvals:'/v9/audit/approvals',
    roster:'/v9/pa/roster', seats:'/v9/pa/seats', ledger:'/v9/pa/ledger',
    cost:'/v9/pa/cost', grants:'/v9/pa/grants', permission:'/v9/pa/permission',
    build:'/v9/pa/build', vault:'/v9/pa/vault', registry:'/v9/pa/registry'
  };
  /* ⭐ 占位端：后端 Phase 1 未落 ⇒ ⛔ 入 live 端表（入表即面册判「悬」＝假已接）。
     只留一句人话，取数一律不走。 */
  var UNWIRED = { stop:'停 · 后端未接（Phase 1）', egress:'出机 · 后端未接（Phase 1）' };
  var CORE = ['today', 'runs', 'context', 'threads'];

  var LIVE = window.PA_WIN_LIVE = {
    at:'', stamp:0, status:'idle', src:{},
    today:null, runs:null, agent_runs:null, threads:null, context:null, approvals:null,
    roster:null, seats:null, ledger:null, cost:null, grants:null,
    permission:null, build:null, vault:null, stop:null, egress:null,
    registry:null, unwired: UNWIRED
  };

  function stamp(){
    var d = new Date();
    function p(n){ return ('0' + n).slice(-2); }
    return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate())
      + ' ' + p(d.getHours()) + ':' + p(d.getMinutes()) + ':' + p(d.getSeconds());
  }
  function nowMs(){
    return (window.performance && performance.now) ? performance.now() : Date.now();
  }
  function errOf(s){
    if(!s) return '还没读到';
    if(s.error) return s.error;
    if(s.status && s.status !== 200) return 'HTTP ' + s.status;
    return '读不到';
  }
  window.paWinLiveErr = function(key){
    if(UNWIRED[key]) return UNWIRED[key];
    return errOf(LIVE.src[key]);
  };

  function getJSON(url, key){
    var ctl = null;
    try{ if(window.AbortController) ctl = new AbortController(); }catch(e){}
    var t0 = nowMs();
    var timer = null;
    var opt = {credentials:'same-origin', headers:{'Accept':'application/json'}, cache:'no-store'};
    if(ctl) opt.signal = ctl.signal;
    if(ctl){
      timer = setTimeout(function(){ try{ ctl.abort(); }catch(e){} }, T);
    }
    return fetch(url, opt)
      .then(function(r){
        return r.text().then(function(txt){ return {status:r.status, txt:txt}; });
      })
      .then(function(x){
        var j = null;
        try{ j = JSON.parse(x.txt); }catch(e){}
        var ok = (x.status === 200) && !!j && (j.ok !== false) && (j.success !== false);
        LIVE.src[key] = {
          ok:ok, status:x.status, ms:Math.round(nowMs() - t0), at:stamp(), url:url,
          error: ok ? '' : (x.status !== 200 ? ('HTTP ' + x.status)
                   : (j ? '后端说没成' : '返回不是可读的 JSON'))
        };
        return j;
      })
      .catch(function(e){
        var ab = e && (e.name === 'AbortError');
        LIVE.src[key] = {
          ok:false, status:0, ms:Math.round(nowMs() - t0), at:stamp(), url:url,
          error: ab ? ('超时 ' + (T / 1000) + ' 秒') : ((e && e.message) || '读不到')
        };
        return null;
      })
      .then(function(j){
        if(timer) clearTimeout(timer);
        return j;
      });
  }

  var busy = null;
  window.paWinLiveRefresh = function(){
    if(busy) return busy;
    if(!LIVE.at) LIVE.status = 'loading';
    render();
    var keys = Object.keys(EP);
    busy = Promise.all(keys.map(function(k){
      return getJSON(EP[k], k).then(function(j){ LIVE[k] = j; });
    })).then(function(){
      busy = null;
      var okN = 0, coreN = 0;
      CORE.forEach(function(k){ if(LIVE.src[k] && LIVE.src[k].ok) okN++; coreN++; });
      LIVE.status = (okN === 0) ? 'error' : (okN === coreN ? 'ok' : 'partial');
      LIVE.at = stamp();
      LIVE.stamp = Date.now();
      render();
      return LIVE;
    });
    return busy;
  };

  window.paWinLiveEnsure = function(maxAgeMs){
    var age = LIVE.stamp ? (Date.now() - LIVE.stamp) : 1e9;
    if(age <= (maxAgeMs || 15000)) return Promise.resolve(LIVE);
    return window.paWinLiveRefresh();
  };

  function render(){
    try{
      if(window.paWinRenderRoute && document.getElementById('paWinStage')){
        var w = document.getElementById('paWin');
        if(!w || w.hidden) return;
        window.paWinRenderRoute();
      }
      if(window.paWinNowRender && document.getElementById('paWinNow')) window.paWinNowRender();
      if(window.paWinLiveRender) window.paWinLiveRender();
    }catch(e){}
  }
  window.paWinLiveRender = window.paWinLiveRender || null;

  /* —— 归一：run ／ 今日行 ／ 件 —— */
  function normRun(r){
    r = r || {};
    var pct = r.progress;
    if(pct == null) pct = r.pct;
    if(pct == null && r.total) pct = Math.round((Number(r.done || 0) * 100) / Number(r.total || 1));
    return {
      id:String(r.run_id || r.id || ''),
      name:String(r.goal || r.name || r.title || '一件在跑的事'),
      pct:Math.max(0, Math.min(100, Number(pct || 0))),
      cost:(r.cost != null ? r.cost : (r.cost_cny != null ? r.cost_cny : '—')),
      state:String(r.state || r.status || 'running'),
      real:true
    };
  }
  window.paWinLiveRuns = function(){
    var out = [], seen = {};
    function add(list){
      (list || []).forEach(function(r){
        var n = normRun(r);
        if(!n.id || seen[n.id]) return;
        seen[n.id] = 1; out.push(n);
      });
    }
    if(LIVE.src.runs && LIVE.src.runs.ok) add((LIVE.runs && LIVE.runs.runs) || []);
    if(LIVE.src.agent_runs && LIVE.src.agent_runs.ok) add((LIVE.agent_runs && LIVE.agent_runs.runs) || []);
    if(!out.length && !(LIVE.src.runs && LIVE.src.runs.ok) && !(LIVE.src.agent_runs && LIVE.src.agent_runs.ok)) return null;
    return out;
  };
  window.paWinLiveTodayRow = function(seq){
    var st2 = LIVE.src.today;
    if(!st2 || !st2.ok) return null;
    var t = LIVE.today || {};
    var rows = t['行'] || [];
    for(var i = 0; i < rows.length; i++){ if(Number(rows[i]['序']) === Number(seq)) return rows[i]; }
    return null;
  };
  window.paWinLiveTodayRows = function(){
    var st2 = LIVE.src.today;
    if(!st2 || !st2.ok) return null;
    return (LIVE.today && LIVE.today['行']) || [];
  };
  window.paWinLivePending = function(){
    var r = window.paWinLiveTodayRow(1);
    return (r && r['件']) ? r['件'] : [];
  };
  window.paWinLiveDeg = function(key){
    var st2 = LIVE.src[key];
    if(!st2 || !st2.ok) return '';
    var s = LIVE[key] || {};
    var d = s.degradations || [];
    if(!d.length) return '';
    var out = [];
    d.forEach(function(x){
      var c = String((x && x.code) || '');
      if(c === 'registry_file_missing') out.push('运行记录尚无落盘 ⇒ 没有可显示的在跑');
      else out.push(String((x && x.message) || c || '降级'));
    });
    return out.join('；');
  };

  /* 首读：等壳挂好（window.js boot 亦会调一次 · 幂等） */
  function boot(){
    if(window.paWinFlagOn && !window.paWinFlagOn()) return;
    if(!document.getElementById('paWin')) return;
    window.paWinLiveRefresh();
    setInterval(function(){
      if(document.hidden) return;
      if(window.paWinFlagOn && !window.paWinFlagOn()) return;
      window.paWinLiveRefresh();
    }, 60000);
  }
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else setTimeout(boot, 0);
})();
