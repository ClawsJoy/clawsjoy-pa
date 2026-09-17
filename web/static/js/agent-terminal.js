/**
 * Agent 终端渲染模块 — 从 workbench.html 提取(拆分映射表步骤 3)
 * 依赖: window.__APP_STATE.currentThread(回退 localStorage) / agentTerminal DOM
 * 内联/其他模块依赖 agentLog(94 处)/renderAgentOutput → window 挂载
 * 批190: 增加智能渲染 —— 模型产出（以「🤖 」开头的行）交给 window.mdToHtml（web/static/js/md.js 单源），
 *        工具/状态/错误行仍是纯文本；判据见 isAgentMd，任一不满足即回退纯文本（宁可少渲染，不可错渲染）。
 */
(function (global) {
  'use strict'

  function _curThread() {
    var st = global.__APP_STATE || {}
    return st.currentThread || (global.localStorage && global.localStorage.getItem('current_thread')) || ''
  }

  function _mdReady() { return typeof global.mdToHtml === 'function' }

  /* 批190 · 判据（保守，四道闸）：
     ① 前缀「🤖 」= 模型产出（chat.js 全部产出点都带这个前缀）；
     ② 含「📋 方案」= 方案按钮 HTML，交给 renderPlanButtons；
     ③ 含 HTML 标签 = 调用方自己传了 HTML，当 Markdown 会转义坏掉；
     ④ md.js 未加载 = 回退纯文本（未观察到 ≠ 通过，不能装作渲染了）。 */
  function isAgentMd(text) {
    var s = String(text == null ? '' : text)
    if (s.indexOf('🤖 ') !== 0) return false
    if (s.indexOf('📋 方案') >= 0) return false
    if (/<[a-zA-Z][^>]*>/.test(s)) return false
    return _mdReady()
  }

  /* 终端单行元素（agentLog 与「回放历史日志」共用，避免两处渲染不一致）*/
  function agentLineEl(text, color) {
    var line = document.createElement('div')
    line.style.color = color || '#c9d1d9'
    var s = String(text == null ? '' : text)
    if (s.indexOf('📋 方案') >= 0 && typeof global.renderPlanButtons === 'function') {
      line.innerHTML = global.renderPlanButtons(s)
      line.style.whiteSpace = 'normal'
    } else if (isAgentMd(s)) {
      line.className = 'mdbody'
      line.innerHTML = global.mdToHtml(s.replace(/^🤖\s*/, ''))
    } else {
      line.textContent = text
    }
    return line
  }

function agentLog(text, color = '#c9d1d9') {
  const term = document.getElementById('agentTerminal');
  if (!term) return;
  term.appendChild(agentLineEl(text, color));
  term.scrollTop = term.scrollHeight;
  let logs = JSON.parse(localStorage.getItem('agent_logs_' + currentThread) || '[]');
  logs.push({ text, color, time: Date.now() });
  if (logs.length > 300) logs = logs.slice(-300);
  localStorage.setItem('agent_logs_' + currentThread, JSON.stringify(logs));
}

function renderAgentOutput(agent, content, round) {
  const dc = document.getElementById('discussion-container');
  if (!dc) return;
  const bubble = document.createElement('div');
  bubble.className = 'discussion-round round-' + (round||1) + ' agent-' + (agent||'').replace(/\s+/g, '-');
  const body = _mdReady() ? global.mdToHtml(content) : escapeHtml(content);
  bubble.innerHTML = '<div class="discussion-agent-name">🤖 ' + escapeHtml(agent) + ' <span class="discussion-round-label">第 ' + (round||1) + ' 轮</span></div><div class="discussion-content mdbody">' + body + '</div>';
  bubble.classList.add('discussion-message');
  dc.appendChild(bubble);
  dc.scrollTop = dc.scrollHeight;
}

  // ===== window 挂载 =====
  global.agentLog = agentLog
  global.agentLineEl = agentLineEl
  global.isAgentMd = isAgentMd
  global.renderAgentOutput = renderAgentOutput
})(window)
