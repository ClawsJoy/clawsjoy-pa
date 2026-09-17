(function (global) {
  'use strict'

  var __APP_STATE = global.__APP_STATE || {}
  var API = (global.CLAWSJOY_API_BASE || (global.localStorage && global.localStorage.getItem('clawsjoy_api_base')) || '')
  var userId = __APP_STATE.userId || ''
  var sessionId = __APP_STATE.sessionId || ''
  // 跨线程隔离修复: userId/sessionId 运行时读取(线程切换后快照不更新 → 串线)
  function _curUser() {
    return (__APP_STATE && __APP_STATE.userId) || (global.localStorage && global.localStorage.getItem('clawsjoy_user_id')) || userId
  }
  function _curSession() {
    return (__APP_STATE && __APP_STATE.sessionId) || (global.localStorage && global.localStorage.getItem('clawsjoy_session_id')) || sessionId
  }

/**
 * 审批卡模块 — 从 workbench.html 提取(拆分映射表步骤 5)
 * 依赖: window.agentLog(agent-terminal) / window.agentSend(chat) / window.escapeHtml
 * 内联 onclick + 卡片动态按钮依赖 → window 挂载
 */

function renderWriteConfirmCard(pw, reasonTextArg) {
  // 批136：出口类命令的**目标必须出现在卡片组件内**（批113 体检项：文案类判据按选择器，
  // 页面级 innerText 里有不算数）。reason 由后端单一来源给出（guards/base.ToolGuard.deny 的
  // reason，内容 = sandbox_util.exfil_note，含目标 URL）；前端**只渲染**，不拼路径、不造文案。
  const term = document.getElementById('agentTerminal');
  if (!term || !pw) return;
  // 2026-08-30 审核机制对齐 harness: 卡片按 pending id 唯一 —
  // 同 id 复用已有卡片(去重: SSE done + 普通响应双渲染只出一张); 不同 id 各自一张
  var cardId = 'writeConfirmCard_' + (pw.id || 'anon');
  var card = document.getElementById(cardId);
  if (!card) {
    card = document.createElement('div');
    card.id = cardId;
    card.style.cssText = 'margin:12px 0;padding:14px;border:1px solid #d2991d;border-radius:8px;background:#1c2128;font-family:Inter,sans-serif;';
    term.appendChild(card);
  } else {
    card.innerHTML = '';  // 复用同 id 卡片 → 刷新内容(不叠加第二张)
  }

  const head = document.createElement('div');
  head.style.cssText = 'color:#d2991d;font-weight:600;margin-bottom:8px;';
  head.textContent = '⏳ Agent 请求写入（需确认）';

  const path = document.createElement('div');
  path.style.cssText = 'color:#c9d1d9;margin-bottom:6px;font-family:monospace;';
  path.innerHTML = '📄 <b>' + escHtml(pw.path || '') + '</b>';

  card.appendChild(head);
  card.appendChild(path);

  // 批136：目标/理由行。三级取值，**都不改判定**：
  //   ① 后端 note（guards/base.ToolGuard.deny 的 reason，人话且含目标）—— 形如状态词(blocked/write_pending)
  //      的短值一律丢弃（实测工作台路径 reason='blocked'，渲染它只会误导）
  //   ② 从命令里**提取**目标 URL（渲染提取，不复制任何出口判据 —— 单一来源仍在 sandbox_util.exfil_note）
  //   ③ Agent 自述 reason
  var _STATUSY = { blocked: 1, write_pending: 1, default: 1, pending: 1 };
  var _note = (typeof reasonTextArg === 'string') ? reasonTextArg.trim() : '';
  if (_note.length < 12 || _STATUSY[_note.toLowerCase()]) _note = '';
  var _cmd = String((pw && (pw.command || pw.path)) || '');
  var _m = _cmd.match(/https?:\/\/[^\s'"`]+/);
  var _target = _m ? _m[0] : '';
  var _agentReason = (pw && pw.reason) ? String(pw.reason).trim() : '';
  var _lines = [];
  if (_note) _lines.push(_note);
  if (_target && (!_note || _note.indexOf(_target) < 0)) _lines.push('目标：' + _target);
  if (!_lines.length && _agentReason.length >= 12) _lines.push(_agentReason);
  if (_lines.length) {
    const why = document.createElement('div');
    why.id = 'writeConfirmReason';
    why.style.cssText = 'color:#d2991d;margin-bottom:6px;font-size:13px;line-height:1.5;word-break:break-all;';
    why.textContent = '⚠️ ' + _lines.join('　');
    card.appendChild(why);
  }

  if (pw.content_preview) {
    const label = document.createElement('div');
    label.style.cssText = 'color:#8b949e;font-size:12px;margin-bottom:4px;';
    label.textContent = '── 内容预览 ──';
    const pre = document.createElement('pre');
    pre.style.cssText = 'background:#0d1117;padding:10px;border-radius:6px;overflow-x:auto;white-space:pre-wrap;word-break:break-all;font-size:12px;max-height:200px;overflow-y:auto;color:#c9d1d9;';
    pre.textContent = pw.content_preview;
    card.appendChild(label);
    card.appendChild(pre);
  }

  const btns = document.createElement('div');
  btns.style.cssText = 'margin-top:10px;display:flex;gap:8px;';
  // 批153 · 三选项统一（仅本次 / 一直允许 / 不允许）—— 与 PA 页同一套：
  //   仅本次   → action=approve（照做，不记忆）
  //   一直允许 → action=always（照做 + 写 grants.yaml，下次同场景免问）
  //   不允许   → action=reject（Agent 调整方案）
  btns.innerHTML =
    '<button id="writeApproveBtn" style="background:#238636;color:#fff;border:none;border-radius:6px;padding:8px 18px;cursor:pointer;font-weight:600;">✅ 仅本次</button>' +
    '<button id="writeAlwaysBtn" style="background:#1f6feb;color:#fff;border:none;border-radius:6px;padding:8px 18px;cursor:pointer;font-weight:600;">♾️ 一直允许</button>' +
    '<button id="writeRejectBtn" style="background:#da3633;color:#fff;border:none;border-radius:6px;padding:8px 18px;cursor:pointer;font-weight:600;">❌ 不允许</button>';
  card.appendChild(btns);
  term.scrollTop = term.scrollHeight;

  // 2026-08-30: 按钮 id 也按 pending id 唯一(同 id 卡片复用后旧按钮不残留)
  card.querySelector('#writeApproveBtn').onclick = function() { sendWriteApproval(pw.id, 'approve', card); };
  card.querySelector('#writeAlwaysBtn').onclick = function() { sendWriteApproval(pw.id, 'always', card); };
  card.querySelector('#writeRejectBtn').onclick = function() { sendWriteApproval(pw.id, 'reject', card); };
}

async function sendWriteApproval(id, action, card) {
  // 只禁用当前卡片的按钮(2026-08-29 修复): 原禁用全部按钮, 多卡片时第一张确认后
  // 后续卡片的按钮全被禁用 → 点了无效(Agent 分片写多次触发多卡片时失效)
  const btns = card ? card.querySelectorAll('#writeApproveBtn,#writeAlwaysBtn,#writeRejectBtn') : [];
  btns.forEach(b => b.disabled = true);
  agentLog(action === 'approve' ? '👤 已确认写入（仅本次）'
           : (action === 'always' ? '👤 已确认写入（一直允许本场景）' : '👤 已拒绝写入'),
           action === 'approve' ? '#3fb950' : (action === 'always' ? '#1f6feb' : '#f85149'));
  try {
    const resp = await fetch(API + '/v9/agent/chat', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: _curUser(), session_id: _curSession(), model: 'deepseek-v4-flash',
        approve_write: { id: id, action: action },
        messages: window.__agentSendMessages || []
      })
    });
    const d = await resp.json();
    if (card && card.parentNode) card.parentNode.removeChild(card);
    if (d.status === 'write_confirmed') {
      const ok = !!(d.tool_result && d.tool_result.success);
      agentLog((ok ? '✅ ' : '❌ ') + 'write_file 已' + (ok ? '确认写入' : '写入失败'),
               ok ? '#3fb950' : '#f85149');
      if (d.tool_result && d.tool_result.error) agentLog('   ' + d.tool_result.error, '#8b949e');
      if (d.continue_messages && d.continue_messages.length) {
        window.__agentSendMessages = d.continue_messages;
      }
      window.__APP_STATE.agentRunning = false;
      agentSend(d.continue_messages);
    } else if (d.status === 'write_rejected') {
      agentLog('🤖 Agent 将调整方案', '#d2991d');
      window.__APP_STATE.agentRunning = false;
      agentSend(d.continue_messages);
    } else if (d.status === 'write_expired' || d.expired) {
      // 2026-08-30 对齐 harness: 审批 60s 过期 → 明确提示, 恢复 Agent 让重新发起写入
      agentLog('⚠️ 写入审批已过期（60 秒有效）。已让 Agent 重新发起写入。', '#d2991d');
      window.__APP_STATE.agentRunning = false;
      if (d.continue_messages && d.continue_messages.length) {
        window.__agentSendMessages = d.continue_messages;
        agentSend(d.continue_messages);
      } else if (window.__agentSendMessages && window.__agentSendMessages.length) {
        agentSend(window.__agentSendMessages);  // 复用原消息重新走一遍 → 重新触发 pending
      }
    } else {
      agentLog('❌ 确认失败: ' + (d.error || d.message || '未知'), '#f85149');
      window.__APP_STATE.agentRunning = false;
    }
  } catch (e) {
    agentLog('❌ 确认请求失败: ' + e.message, '#f85149');
    agentRunning = false;
  }
}

function renderPlanConfirmCard(plan) {
  const term = document.getElementById('term') || document.getElementById('agentTerminal');
  const card = document.createElement('div');
  card.style.cssText = 'background:#1c2128;border:1px solid #d29922;border-radius:8px;padding:14px;margin:8px 0;';
  const title = document.createElement('div');
  title.style.cssText = 'color:#d29922;font-weight:700;margin-bottom:8px;';
  title.textContent = '📋 检测到多文件/多意图任务，请确认计划';
  card.appendChild(title);

  const meta = document.createElement('div');
  meta.style.cssText = 'color:#8b949e;font-size:12px;margin-bottom:8px;';
  meta.textContent = '涉及 ' + (plan.files || []).length + ' 个文件，共 ' + plan.intents + ' 个修改意图';
  card.appendChild(meta);

  if (plan.files && plan.files.length > 0) {
    const fl = document.createElement('div');
    fl.style.cssText = 'color:#c9d1d9;font-size:13px;margin-bottom:8px;';
    fl.textContent = '文件：' + plan.files.join('、');
    card.appendChild(fl);
  }

  if (plan.plan) {
    const label = document.createElement('div');
    label.style.cssText = 'color:#8b949e;font-size:12px;margin-top:6px;';
    label.textContent = '── 计划说明 ──';
    const pre = document.createElement('pre');
    pre.style.cssText = 'background:#0d1117;padding:10px;border-radius:6px;overflow-x:auto;white-space:pre-wrap;word-break:break-all;font-size:12px;max-height:200px;overflow-y:auto;color:#c9d1d9;';
    pre.textContent = plan.plan;
    card.appendChild(label);
    card.appendChild(pre);
  }

  const btns = document.createElement('div');
  btns.style.cssText = 'margin-top:10px;display:flex;gap:8px;';
  btns.innerHTML =
    '<button id="planApproveBtn" style="background:#238636;color:#fff;border:none;border-radius:6px;padding:8px 18px;cursor:pointer;font-weight:600;">✅ 确认计划</button>' +
    '<button id="planRejectBtn" style="background:#da3633;color:#fff;border:none;border-radius:6px;padding:8px 18px;cursor:pointer;font-weight:600;">❌ 拒绝计划</button>';
  card.appendChild(btns);
  term.appendChild(card);
  term.scrollTop = term.scrollHeight;

  document.getElementById('planApproveBtn').onclick = function() { sendPlanApproval('approve', card); };
  document.getElementById('planRejectBtn').onclick = function() { sendPlanApproval('reject', card); };
}

async function sendPlanApproval(action, card) {
  const btns = document.querySelectorAll('#planApproveBtn,#planRejectBtn');
  btns.forEach(b => b.disabled = true);
  agentLog(action === 'approve' ? '👤 已确认计划' : '👤 已拒绝计划',
           action === 'approve' ? '#3fb950' : '#f85149');
  try {
    const resp = await fetch(API + '/v9/agent/chat', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: _curUser(), session_id: _curSession(), model: 'deepseek-v4-flash',
        approve_plan: { action: action },
        messages: window.__agentSendMessages || []
      })
    });
    const d = await resp.json();
    if (card && card.parentNode) card.parentNode.removeChild(card);
    if (d.status === 'plan_confirmed') {
      agentLog('📋 计划已确认，继续执行', '#3fb950');
      if (d.continue_messages && d.continue_messages.length) {
        window.__agentSendMessages = d.continue_messages;
      }
      window.__APP_STATE.agentRunning = false;
      agentSend(d.continue_messages);
    } else if (d.status === 'plan_rejected') {
      agentLog('🤖 Agent 将调整方案', '#d2991d');
      if (d.continue_messages && d.continue_messages.length) {
        window.__agentSendMessages = d.continue_messages;
      }
      window.__APP_STATE.agentRunning = false;
      agentSend(d.continue_messages);
    } else {
      agentLog('❌ 计划确认失败: ' + (d.error || d.message || '未知'), '#f85149');
      window.__APP_STATE.agentRunning = false;
    }
  } catch (e) {
    agentLog('❌ 计划确认请求失败: ' + e.message, '#f85149');
    agentRunning = false;
  }
}

function renderAskCard(ask) {
  const term = document.getElementById('term') || document.getElementById('agentTerminal');
  const card = document.createElement('div');
  card.style.cssText = 'background:#1c2128;border:1px solid #58a6ff;border-radius:8px;padding:14px;margin:8px 0;';
  const title = document.createElement('div');
  title.style.cssText = 'color:#58a6ff;font-weight:700;margin-bottom:8px;';
  title.textContent = '❓ Agent 需要您决策';
  card.appendChild(title);

  if (ask.question) {
    const q = document.createElement('div');
    q.style.cssText = 'color:#c9d1d9;font-size:13px;margin-bottom:10px;';
    q.textContent = ask.question;
    card.appendChild(q);
  }

  const opts = document.createElement('div');
  opts.style.cssText = 'display:flex;flex-direction:column;gap:6px;';
  (ask.options || []).forEach((opt, i) => {
    const btn = document.createElement('button');
    btn.textContent = (i === 0 ? '✅ ' : '') + opt;
    btn.style.cssText = 'background:#1f6feb;color:#fff;border:none;border-radius:6px;padding:8px 14px;cursor:pointer;font-weight:600;text-align:left;';
    btn.onmouseover = function() { this.style.background = '#388bfd'; };
    btn.onmouseout = function() { this.style.background = '#1f6feb'; };
    btn.onclick = function() { sendAskChoice(opt, card); };
    opts.appendChild(btn);
  });
  card.appendChild(opts);
  term.appendChild(card);
  term.scrollTop = term.scrollHeight;
}

async function sendAskChoice(choice, card) {
  agentLog('👤 选择: ' + choice, '#3fb950');
  if (card && card.parentNode) card.parentNode.removeChild(card);
  try {
    const msgs = (window.__agentSendMessages || []).slice();
    msgs.push({ role: 'user', content: '我选择：' + choice });
    const resp = await fetch(API + '/v9/agent/chat', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: _curUser(), session_id: _curSession(), model: 'deepseek-v4-flash',
        messages: msgs
      })
    });
    const d = await resp.json();
    if (d.status === 'ask') {
      agentLog('🤖 ' + ((d.data && d.data.choices && d.data.choices[0] && d.data.choices[0].message && d.data.choices[0].message.content) || ''), '#c9d1d9');
      if (d.ask) renderAskCard(d.ask);
      return;
    }
    window.__agentSendMessages = d.continue_messages || msgs;
    agentRunning = false;
    agentSend(d.continue_messages || msgs);
  } catch (e) {
    agentLog('❌ 选项回传失败: ' + e.message, '#f85149');
    agentRunning = false;
  }
}

function renderPlanButtons(text) {
  if (typeof text !== 'string') return text;
  const plans = text.match(/📋\s*方案([A-Z])[：:][^\n]*/g);
  if (!plans) return text;
  let html = text.replace(/</g, '&lt;').replace(/>/g, '&gt;');
  plans.forEach(plan => {
    const letter = plan.match(/方案([A-Z])/)[1];
    const btn = `<span class="plan-btn" style="display:inline-block;background:#1f6feb;color:#fff;padding:8px 16px;border-radius:6px;cursor:pointer;margin:4px;font-weight:600;" onmouseover="if(!this.dataset.sel)this.style.background='#388bfd'" onmouseout="if(!this.dataset.sel)this.style.background='#1f6feb'" onclick="selectPlan(this)" data-letter="${letter}">${plan.replace(/</g,'&lt;')} → 选择此方案</span>`;
    html = html.replace(plan.replace(/</g,'&lt;'), btn);
  });
  return html;
}

function selectPlan(btn) {
  document.querySelectorAll('.plan-btn').forEach(b => { b.style.background = '#1f6feb'; b.dataset.sel = ''; });
  btn.style.background = '#238636'; btn.dataset.sel = '1'; selectedPlanBtn = btn;
  document.getElementById('agentInput').value = '选择方案' + btn.dataset.letter + '，按此方案执行';
  agentLog('📋 已选择方案' + btn.dataset.letter + '，点击执行按钮开始', '#3fb950');
}

// ===== P2 本地浏览器操作审批卡 =====
function renderBrowserConfirmCard(op) {
  const term = document.getElementById('agentTerminal');
  if (!term || !op) return;
  const card = document.createElement('div');
  card.id = 'browserConfirmCard';
  card.style.cssText = 'margin:12px 0;padding:14px;border:1px solid #6f42c1;border-radius:8px;background:#1c2128;';
  const head = document.createElement('div');
  head.style.cssText = 'color:#a371f7;font-weight:600;margin-bottom:8px;';
  head.textContent = '🖥️ 本地浏览器操作需确认：' + (op.action || '');
  card.appendChild(head);
  const detail = document.createElement('div');
  detail.style.cssText = 'color:#c9d1d9;font-size:13px;margin-bottom:6px;word-break:break-all;';
  detail.textContent = (op.reason || '') + '  ' + JSON.stringify(op.params || {}).slice(0, 200);
  card.appendChild(detail);
  // P3 发布: 展示完整待发布内容(标题/正文/标签/配图)
  if (op.action === 'publish' && op.params) {
    const p = op.params;
    const pre = document.createElement('div');
    pre.style.cssText = 'background:#0d1117;padding:10px;border-radius:6px;font-size:12px;color:#c9d1d9;white-space:pre-wrap;word-break:break-all;max-height:240px;overflow-y:auto;border-left:2px solid #6f42c1;';
    let txt = '';
    if (p.platform) txt += '🌐 平台: ' + p.platform + '\n';
    if (p.title) txt += '📌 标题: ' + p.title + '\n';
    if (p.content) txt += '📝 正文: ' + p.content + '\n';
    if (p.tags && p.tags.length) txt += '🏷 标签: ' + (Array.isArray(p.tags) ? p.tags.join(' #') : p.tags) + '\n';
    if (p.images && p.images.length) txt += '🖼 配图: ' + (Array.isArray(p.images) ? p.images.length + ' 张' : p.images) + '\n';
    pre.textContent = txt || '无内容';
    card.appendChild(pre);
    const warn = document.createElement('div');
    warn.style.cssText = 'color:#f85149;font-size:12px;margin-top:6px;';
    warn.textContent = '⚠ 确认后将在你的真实账号发布此内容，请仔细核对。';
    card.appendChild(warn);
  }
  const hint = document.createElement('div');
  hint.style.cssText = 'color:#8b949e;font-size:12px;margin-bottom:8px;';
  hint.textContent = 'Agent 将操作你的本地浏览器。确认后继续，拒绝则 Agent 调整方案。';
  card.appendChild(hint);
  const btns = document.createElement('div');
  btns.style.cssText = 'margin-top:10px;display:flex;gap:8px;';
  btns.innerHTML =
    '<button id="browserApproveBtn" style="background:#238636;color:#fff;border:none;border-radius:6px;padding:8px 18px;cursor:pointer;font-weight:600;">✅ 确认执行</button>' +
    '<button id="browserRejectBtn" style="background:#da3633;color:#fff;border:none;border-radius:6px;padding:8px 18px;cursor:pointer;font-weight:600;">❌ 拒绝</button>';
  card.appendChild(btns);
  term.appendChild(card);
  term.scrollTop = term.scrollHeight;
  document.getElementById('browserApproveBtn').onclick = function() { sendBrowserApproval(op.op_id, 'approve', card); };
  document.getElementById('browserRejectBtn').onclick = function() { sendBrowserApproval(op.op_id, 'reject', card); };
}

async function sendBrowserApproval(opId, action, card) {
  const btns = document.querySelectorAll('#browserApproveBtn,#browserRejectBtn');
  btns.forEach(b => b.disabled = true);
  agentLog(action === 'approve' ? '👤 已确认浏览器操作' : '👤 已拒绝浏览器操作',
           action === 'approve' ? '#3fb950' : '#f85149');
  try {
    const resp = await fetch(API + '/v9/agent/chat', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: _curUser(), session_id: _curSession(), model: 'deepseek-v4-flash',
        approve_browser: { op_id: opId, action: action },
        messages: window.__agentSendMessages || []
      })
    });
    const d = await resp.json();
    if (card && card.parentNode) card.parentNode.removeChild(card);
    if (d.status === 'browser_confirmed') {
      agentLog('✅ 浏览器操作已执行', '#3fb950');
      if (d.result && d.result.data) agentLog('   ' + JSON.stringify(d.result.data).slice(0, 200), '#8b949e');
    } else if (d.status === 'browser_rejected') {
      agentLog('🤖 已拒绝，Agent 将调整方案', '#d2991d');
    } else {
      agentLog('❌ 确认失败: ' + (d.error || d.message || '未知'), '#f85149');
    }
    if (d.continue_messages && d.continue_messages.length) {
      window.__agentSendMessages = d.continue_messages;
      window.__APP_STATE.agentRunning = false;
      agentSend(d.continue_messages);
    } else {
      window.__APP_STATE.agentRunning = false;
    }
  } catch (e) {
    agentLog('❌ 确认请求失败: ' + e.message, '#f85149');
    window.__APP_STATE.agentRunning = false;
  }
}

  // ===== window 挂载(内联 onclick / 其他模块依赖) =====

  global.renderWriteConfirmCard = renderWriteConfirmCard
  global.sendWriteApproval = sendWriteApproval
  global.renderPlanConfirmCard = renderPlanConfirmCard
  global.sendPlanApproval = sendPlanApproval
  global.renderAskCard = renderAskCard
  global.sendAskChoice = sendAskChoice
  global.renderPlanButtons = renderPlanButtons
  global.selectPlan = selectPlan
  global.renderBrowserConfirmCard = renderBrowserConfirmCard
  global.sendBrowserApproval = sendBrowserApproval
})(window)
