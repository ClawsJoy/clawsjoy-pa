/* PA 窗 v1 / 1a · 任务卡 ＋ 回执（CW b2a5182 · 2026-10-27 · 承 PRD v1 §3.3 ／ §4.6 ／ §4.7）
   界：静态壳（mock）；⛔ 动后端 ／ ⛔ 新依赖 ／ ⛔ 删旧 faces。
   七问（§4.7）：做了什么 ／ 凭什么 ／ 谁做的 ／ 花了多少 ／ 动了什么 ／ 出了什么机 ／ 可否退。 */
(function(){
  'use strict';

  function esc(s){
    return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
    });
  }

  /* 步骤态：done ／ doing ／ todo ／ fail ⇒ 点色（绿／蓝／灰／红） */
  function stepDot(st){
    var m = {done:'pa-s-done', doing:'pa-s-doing', todo:'pa-s-todo', fail:'pa-s-fail'};
    return '<i class="pa-dot-s ' + (m[st] || 'pa-s-todo') + '"></i>';
  }

  /* Focus 任务卡：目标 ／ 副（谁·何时·预算）／ 步骤 ／ 进度 ／ 花费 ／ 停 ／ 回执 */
  window.paWinTaskCardHtml = function(task){
    var t = task || {};
    var steps = t.steps || [];
    var done = 0;
    steps.forEach(function(s){ if(s.state === 'done') done++; });
    var pct = t.pct != null ? t.pct : (steps.length ? Math.round(done * 100 / steps.length) : 0);
    pct = Math.max(0, Math.min(100, Number(pct) || 0));
    var isDone = !!(t.done || t.receipt) || pct >= 100;
    var stopBtn = isDone
      ? '<button class="pa-btn pa-btn-stop" type="button" disabled title="已完成 · 停只对在跑">已完成</button>'
      : '<button class="pa-btn pa-btn-stop" type="button" onclick="paWinStop()" title="停（Ctrl+.）">■ 停</button>';
    var rows = steps.map(function(s){
      return '<li class="pa-step">' + stepDot(s.state)
        + '<span class="pa-step-n">' + esc(s.name) + '</span>'
        + '<span class="pa-step-e">' + esc(s.ev || '') + '</span></li>';
    }).join('');

    var foot = t.receipt
      ? window.paWinReceiptHtml(t.receipt)
      : '<div class="pa-tc-foot"><span class="pa-sub">' + esc(t.footNote || '做完了就出回执 · 每一问都能落到账上') + '</span>'
        + '<button class="pa-btn pa-btn-main" type="button" onclick="paWinFinish()"'
        + ' title="这一件做完了 ⇒ 出回执（七问）">做完了 · 出回执</button></div>';

    return '<section class="pa-tc" id="paWinTaskCard" aria-label="在办之事">'
      + '<header class="pa-tc-h"><h2>' + esc(t.goal || '一件事') + '</h2>'
      + '<div class="pa-tc-sub">' + esc(t.who || '你') + ' · ' + esc(t.when || '刚起')
      + ' · 预算 ' + esc(t.budget || '¥0.00') + '</div></header>'
      + '<div class="pa-tc-prog"><div class="pa-bar"><i style="width:' + pct + '%"></i></div>'
      + '<span class="pa-pct">' + (isDone ? '已完成' : (pct + '%')) + '</span>'
      + '<span class="pa-cost">' + esc(t.cost || '¥0.00') + '</span>'
      + stopBtn + '</div>'
      + '<ol class="pa-steps">' + rows + '</ol>'
      + foot
      + '</section>';
  };

  /* 回执：七问 ＋ 哈希短 ＋ 导出 */
  window.paWinReceiptHtml = function(r){
    var q = r || {};
    var items = [
      ['做了什么', q.did], ['凭什么', q.why], ['谁做的', q.who],
      ['花了多少', q.cost], ['动了什么', q.touched], ['出了什么机', q.egress],
      ['可否退', q.undo]
    ];
    var rows = items.map(function(it){
      return '<li class="pa-rq"><span class="pa-rq-k">' + esc(it[0]) + '</span>'
        + '<span class="pa-rq-v">' + esc(it[1] || '—') + '</span></li>';
    }).join('');
    return '<div class="pa-receipt" id="paWinReceipt">'
      + '<div class="pa-rc-h">回执 <span class="pa-hash" title="本条之指纹（短）">' + esc(q.sha16 || '—') + '</span>'
      + '<button class="pa-btn pa-btn-ghost" type="button" onclick="paWinExportReceipt()">导出</button></div>'
      + '<ul class="pa-rqs">' + rows + '</ul>'
      + '<div class="pa-rc-f">前一条指纹 <span class="pa-hash">' + esc(q.prev || '—') + '</span></div>'
      + '</div>';
  };

  /* 回执之 mock（1a · 一件做完才有）—— 七问逐条有落，⛔ 空答 */
  window.paWinMockReceipt = function(task){
    var t = task || {};
    var steps = t.steps || [];
    var done = 0;
    steps.forEach(function(s){ if(s.state === 'done') done++; });
    var prev = (window.PA_WIN_STATE && window.PA_WIN_STATE.ledger && window.PA_WIN_STATE.ledger[0])
      ? window.PA_WIN_STATE.ledger[0].hash : '';
    var sha = window.paWinHash
      ? window.paWinHash((t.goal || '') + '|' + (t.cost || '') + '|' + (t.when || ''))
      : '—';
    return {
      sha16: sha,
      prev: prev || '—',
      did: '把「' + (t.goal || '这件事') + '」做完了；' + steps.length + ' 步里成了 ' + done + ' 步',
      why: '你点头之后才动的 · 只用你给的东西 · 没自己加戏',
      who: (t.who || '你') + '点名的那一席',
      cost: (t.cost || '¥0.00') + '（账上已记一行）',
      touched: '只在报告目录动了 ' + Math.max(1, steps.length) + ' 件；原件一件没删',
      egress: '没出机；东西都在这台机器上',
      undo: '能退：报告目录那几件删掉就回原样'
    };
  };

  /* 步骤之 mock（1a 静态 · 由 window.js 取用） */
  window.paWinMockSteps = function(pct){
    var p = pct == null ? 32 : Math.max(0, Math.min(100, pct));
    /* 步骤态随进度走（⛔ 100% 了还留「正在做」—— 那是假态）*/
    var done, doing;
    if(p >= 100){ done = 4; doing = -1; }
    else if(p >= 75){ done = 3; doing = 3; }
    else if(p >= 25){ done = 2; doing = 2; }
    else { done = 1; doing = 1; }
    var N = ['读懂要办的事','拆成可做的几步','把该做的做完','收尾与回执'];
    var E = ['已记 3 条要点','拆出 4 步','进度 ' + p + '%',''];
    var out = [];
    for(var i = 0; i < 4; i++){
      var st = i < done ? 'done' : (i === doing ? 'doing' : 'todo');
      out.push({name: i === 2 ? (st === 'doing' ? '正在做第 3 步' : N[i]) : N[i],
                state: st, ev: st === 'todo' ? '' : E[i]});
    }
    return out;
  };
})();