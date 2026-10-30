/* PA 窗 v1 / 1b-1 · 右栏 Now（CW b2a5182 · 2026-10-27 · 承 PRD v1 §3.2 ／ §4.5 ／ §7）
   三块：在跑 ／ 待你批 ／ 将出机。界：只接现有端点；⛔ 动后端 ／ ⛔ 新依赖 ／ ⛔ 假数据充真。
   真源：/v9/pes/runs（在跑）／ /v9/pa/today 行 1（待授权件 · 只读）／ /v9/pa/egress（404 ⇒ 未接）。
   L2 一键批 ／ L3 六位码仍只对本机草稿（未派 · 明书）——真件之批／否须 Phase 1 授权端。 */
(function(){
  'use strict';

  function esc(s){
    return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
    });
  }
  function st(){ return window.PA_WIN_STATE || (window.PA_WIN_STATE = {}); }
  function L(){ return window.PA_WIN_LIVE || {}; }
  function money(v){
    if(v == null || v === '') return '—';
    if(typeof v === 'number') return '¥' + v.toFixed(2);
    var s = String(v);
    return /^[¥￥]/.test(s) ? s : ('¥' + s);
  }

  function skeleton(){
    return '<div class="pa-skel sm" aria-label="正在读"><i style="width:80%"></i><i style="width:62%"></i></div>';
  }
  function errBox(key){
    var msg = window.paWinLiveErr ? window.paWinLiveErr(key) : '读不到';
    return '<div class="pa-empty warn">读不到：' + esc(msg)
      + '<button class="pa-btn pa-btn-ghost pa-retry" type="button" onclick="paWinLiveRefresh()">再读一次</button></div>';
  }

  function realRuns(){ return (window.paWinLiveRuns && window.paWinLiveRuns()) || []; }
  function localRuns(){ return st().runs || []; }

  function oneRun(r, local){
    var finished = r.state === 'done';
    var stopped = r.state === 'stopped';
    var running = !finished && !stopped;
    var pct = running ? (Number(r.pct) || 0) : 100;
    var go = r.id
      ? ' role="button" tabindex="0" onclick="paWinFocus(\'' + esc(r.id) + '\')"'
        + ' onkeydown="if(event.key===\'Enter\'||event.key===\' \'){event.preventDefault();paWinFocus(\'' + esc(r.id) + '\');}"'
      : '';
    var tag = local ? ' <span class="pa-tag">本机草稿</span>' : '';
    return '<div class="pa-run' + (stopped ? ' on-stop' : '') + '">'
      + '<div class="pa-run-t"' + go + ' title="点开看这一件（Focus）">' + esc(r.name) + tag + '</div>'
      + '<div class="pa-run-b"><div class="pa-bar sm"><i style="width:' + pct + '%"></i></div>'
      + '<span class="pa-pct">' + (finished ? '已完成' : (stopped ? '已停' : (pct + '%'))) + '</span>'
      + '<span class="pa-cost">' + esc(money(r.cost)) + '</span>'
      + (running
          ? '<button class="pa-btn pa-btn-mini" type="button" onclick="paWinStop()" title="停这一件">■</button>'
          : '<button class="pa-btn pa-btn-mini" type="button" disabled title="已完成 · 停只对在跑">■</button>')
      + '</div></div>';
  }

  function runningHtml(){
    var live = L();
    if(!live.at) return skeleton();
    var s = live.src ? live.src.runs : null;
    if(s && !s.ok) return errBox('runs');
    var rr = realRuns();
    var lr = localRuns();
    if(!rr.length && !lr.length){
      var deg = window.paWinLiveDeg ? window.paWinLiveDeg('runs') : '';
      return '<div class="pa-empty">' + esc(deg || '此刻没有在跑的事') + '</div>'
        + (deg ? '<div class="pa-hint">运行记录尚无落盘 · 这不是错</div>' : '');
    }
    return rr.map(function(r){ return oneRun(r, false); }).join('')
      + (lr.length ? '<div class="pa-now-sub">本机草稿 · 未派</div>'
        + lr.map(function(r){ return oneRun(r, true); }).join('') : '');
  }

  function realPending(){
    if(!window.paWinLivePending) return [];
    var a = window.paWinLivePending();
    return a || [];
  }
  function realApprovalHtml(a){
    return '<div class="pa-appr real"><div class="pa-appr-h">'
      + '<span class="pa-risk">' + esc(a['类'] || '待授权') + '</span>'
      + '<span class="pa-lv">只读</span></div>'
      + '<div class="pa-appr-w">' + esc(a['题'] || '一件等你点头的事') + '</div>'
      + '<div class="pa-appr-p">刻 ' + esc(a['刻'] || '—') + (a['id'] ? (' · 件 ' + esc(a['id'])) : '') + '</div>'
      + '<div class="pa-appr-note">批 ／ 否须授权端（Phase 1 后端）· 本屏只读，⛔ 假执行</div></div>';
  }

  function localApprovalHtml(a){
    var lv = a.level || 'L2';
    var locked = (st().lockedUntil || 0) > Date.now();
    var codeRow = lv === 'L3'
      ? '<div class="pa-code"><label for="paCode_' + esc(a.id) + '">6 位码</label>'
        + '<input id="paCode_' + esc(a.id) + '" data-code="' + esc(a.id) + '" inputmode="numeric" maxlength="6"'
        + ' placeholder="••••••" autocomplete="off"' + (locked ? ' disabled' : '') + '>'
        + '<span class="pa-code-note">' + (locked ? '试了 3 次，歇 5 分钟再来' : '码在你手机／本机确认器上') + '</span></div>'
      : '';
    var deny = lv === 'L4'
      ? '<button class="pa-btn pa-btn-ghost" type="button" disabled>已拒</button>'
      : '<button class="pa-btn pa-btn-ghost" type="button" onclick="paWinDeny(\'' + esc(a.id) + '\')">否</button>';
    return '<div class="pa-appr lv-' + esc(lv.toLowerCase()) + '">'
      + '<div class="pa-appr-h"><span class="pa-risk">' + esc(a.risk || '要你拍') + '</span>'
      + '<span class="pa-lv">' + esc(lv) + '</span></div>'
      + '<div class="pa-appr-w">' + esc(a.what) + '</div>'
      + '<div class="pa-appr-p">凭什么：' + esc(a.why || '—') + ' · 花 ' + esc(a.cost || '¥0.00') + '</div>'
      + (a.egress ? '<div class="pa-appr-e">出机：' + esc(a.egress) + '</div>' : '')
      + codeRow
      + '<div class="pa-appr-a">'
      + '<button class="pa-btn pa-btn-main" type="button"' + (locked ? ' disabled' : '')
      + ' onclick="paWinApprove(\'' + esc(a.id) + '\')">批</button>'
      + deny + '</div></div>';
  }

  function approvalsHtml(){
    var live = L();
    if(!live.at) return skeleton();
    var t = live.src ? live.src.today : null;
    if(t && !t.ok) return errBox('today');
    var out = '';
    var pending = realPending();
    if(pending.length) out += pending.map(realApprovalHtml).join('');
    else out += '<div class="pa-empty">无待拍</div>';
    var locals = st().approvals || [];
    if(locals.length){
      out += '<div class="pa-now-sub">本机草稿 · 未派</div>' + locals.map(localApprovalHtml).join('');
    }
    return out;
  }

  function egressHtml(){
    var live = L();
    if(!live.at) return skeleton();
    var e = live.egress;
    if(live.unwired && live.unwired.egress){
      return '<div class="pa-empty">将出机 · 未接（Phase 1 后端）</div>'
        + '<div class="pa-hint">占位端已撤出 live 面（⛔ 以未接充「无」）· ' + esc(live.unwired.egress) + '</div>';
    }
    if(e && !e.ok){
      return '<div class="pa-empty">将出机 · 未接（Phase 1 后端）</div>'
        + '<div class="pa-hint">本刻无出机之读数 · ' + esc(window.paWinLiveErr ? window.paWinLiveErr('egress') : '') + '</div>';
    }
    var es = (e && (e.items || e.egress)) || [];
    if(!es.length) return '<div class="pa-empty">没有要出机的东西</div>';
    return es.map(function(x){
      return '<div class="pa-eg"><span class="pa-eg-lv">' + esc(x.level || '—') + '</span>'
        + '<span class="pa-eg-to">' + esc(x.to || '—') + '</span>'
        + '<span class="pa-eg-ttl">' + esc(x.ttl || '—') + '</span></div>';
    }).join('');
  }

  window.paWinNowRender = function(){
    var el = document.getElementById('paWinNow');
    if(!el) return;
    var _drafts = (st().approvals || []).length;
    el.innerHTML = '<section class="pa-now-sec"><h3>在跑</h3>' + runningHtml() + '</section>'
      + '<section class="pa-now-sec"><h3>' + (_drafts ? '待你批' : '历史待授权（只读）') + '</h3>' + approvalsHtml() + '</section>'
      + '<section class="pa-now-sec"><h3>将出机</h3>' + egressHtml() + '</section>';
    var stopBtn = document.getElementById('paWinStop');
    if(stopBtn){
      var live = realRuns().some(function(r){ return r.state !== 'stopped' && r.state !== 'done'; })
        || localRuns().some(function(r){ return r.state !== 'stopped' && r.state !== 'done'; });
      stopBtn.disabled = !live;
      stopBtn.classList.toggle('live', live);
    }
    window.paWinEgressRefresh && window.paWinEgressRefresh();
  };

  /* ── 批 ／ 否 ／ 码（只对本机草稿；真件无写端 ⇒ 只读）── */
  window.paWinApprove = function(id){
    var s = st();
    var a = (s.approvals || []).filter(function(x){ return x.id === id; })[0];
    if(!a) return;
    if(a.level === 'L4'){ window.paWinSay('这件已拒 · 只能改方案再来'); return; }
    if(a.level === 'L3'){
      if((s.lockedUntil || 0) > Date.now()){
        window.paWinSay('码错了 3 次，歇 5 分钟再来');
        return;
      }
      var inp = document.querySelector('[data-code="' + id + '"]');
      var v = inp ? String(inp.value || '').replace(/\D/g, '') : '';
      if(v !== '123456'){
        s.codeFails = (s.codeFails || 0) + 1;
        if(s.codeFails >= 3){
          s.lockedUntil = Date.now() + 5 * 60 * 1000;
          s.codeFails = 0;
          window.paWinSay('码错了 3 次 · 歇 5 分钟再来');
        } else {
          window.paWinSay('码不对 · 还有 ' + (3 - s.codeFails) + ' 次');
        }
        window.paWinNowRender();
        return;
      }
      s.codeFails = 0;
    }
    s.approvals = (s.approvals || []).filter(function(x){ return x.id !== id; });
    s.runs = (s.runs || []).concat([{id:'r' + Date.now(), name:a.what, pct:2, cost:'¥0.00', state:'running'}]);
    window.paWinLedgerAdd('已批 · ' + a.what, '你', '¥0.00', '预记');
    window.paWinNowRender();
    window.paWinSay('好 · 本机草稿已在跑（未派真活）');
    backToInput();
    if(window.paWinRouteIs && window.paWinRouteIs('today')) window.paWinRenderRoute();
  };

  window.paWinDeny = function(id){
    var s = st();
    var a = (s.approvals || []).filter(function(x){ return x.id === id; })[0];
    if(!a) return;
    s.approvals = (s.approvals || []).filter(function(x){ return x.id !== id; });
    window.paWinLedgerAdd('已否 · ' + a.what, '你', '¥0.00', '未执行');
    window.paWinNowRender();
    window.paWinSay('好 · 这件不做了；账上记「已否」');
    backToInput();
  };

  /* 拍板之后焦点回输入框（PRD §8.14：⛔ 弹窗雨 · ⛔ 焦点丢失）*/
  function backToInput(){
    var el = document.getElementById('paCmdIn') || document.getElementById('paSummonIn');
    if(el){ try{ el.focus(); }catch(e){} }
  }

  window.paWinEgressShow = function(id){
    var e = (L().egress && (L().egress.items || L().egress.egress) || []).filter(function(x){ return x.id === id; })[0];
    if(!e) return;
    window.paWinSay('出机：' + (e.to || '—') + ' · 为什么：' + (e.why || '—') + ' · ' + (e.ttl || '') + ' 后删');
  };
})();
