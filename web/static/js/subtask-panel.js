(function (global) {
  'use strict'

  var __APP_STATE = global.__APP_STATE || {}
  var API = (global.CLAWSJOY_API_BASE || (global.localStorage && global.localStorage.getItem('clawsjoy_api_base')) || '')
  var userId = __APP_STATE.userId || ''
  var sessionId = __APP_STATE.sessionId || ''
  // 跨线程隔离修复: userId/sessionId 运行时读取
  function _curUser() {
    return (__APP_STATE && __APP_STATE.userId) || (global.localStorage && global.localStorage.getItem('clawsjoy_user_id')) || userId
  }
  function _curSession() {
    return (__APP_STATE && __APP_STATE.sessionId) || (global.localStorage && global.localStorage.getItem('clawsjoy_session_id')) || sessionId
  }

/**
 * 子任务面板模块 — 从 workbench.html 提取(拆分映射表步骤 6)
 * 依赖: window.agentLog(agent-terminal) / window.__APP_STATE
 * 内联 onclick: createSubtask/agentSendAsync → window 挂载
 */

async function createSubtask() {
  const input = document.getElementById('subtaskInput');
  const spec = input ? input.value.trim() : '';
  if (!spec) return;
  if (input) input.value = '';
  document.getElementById('subtaskPanel').style.display = 'block';
  try {
    await fetch(API + '/v9/subtask/create', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: _curUser(), session_id: _curSession(), task_spec: spec })
    });
  } catch(e) { console.error('subtask create failed:', e); }
  pollSubtasks();
}

async function pollSubtasks() {
  try {
    // GET + query（状态查询无副作用，符合 /v9/task/status 惯例；后端读 request.args）
    const resp = await fetch(API + '/v9/subtask/status?user_id=' + encodeURIComponent(userId) + '&session_id=' + encodeURIComponent(sessionId));
    const d = await resp.json();
    if (d.success) renderSubtasks(d.subtasks || []);
    const hasActive = (d.subtasks || []).some(t => t.status === 'queued' || t.status === 'running');
    clearTimeout(_subtaskPollTimer);
    if (hasActive) _subtaskPollTimer = setTimeout(pollSubtasks, 2000);
  } catch(e) { console.error('subtask poll failed:', e); }
}

function renderSubtasks(tasks) {
  const panel = document.getElementById('subtaskPanel');
  const list = document.getElementById('subtaskList');
  if (!panel || !list) return;
  if (tasks.length > 0) panel.style.display = 'block';
  const ICONS = { queued: '⏳', running: '🔄', done: '✅', failed: '❌' };
  const COLORS = { queued: '#8b949e', running: '#58a6ff', done: '#3fb950', failed: '#f85149' };
  list.innerHTML = tasks.slice().reverse().map(t => {
    const icon = ICONS[t.status] || '⏳';
    const color = COLORS[t.status] || '#8b949e';
    const err = t.error ? '<div style="color:#f85149; font-size:11px; margin-top:3px;">' + String(t.error).substring(0, 120) + '</div>' : '';
    const arch = t.archived_path ? '<div style="color:#8b949e; font-size:10px; margin-top:2px;">📦 ' + String(t.archived_path).substring(0, 90) + '</div>' : '';
    return '<div style="background:#161b22; border:1px solid #21262d; border-radius:6px; padding:8px 12px;">' +
      '<div style="display:flex; align-items:center; gap:8px;">' +
      '<span style="font-size:13px;">' + icon + '</span>' +
      '<span style="color:' + color + '; font-weight:600; font-size:12px;">' + t.status + '</span>' +
      '<span style="color:#c9d1d9; font-size:12px; flex:1; word-break:break-all;">' + String(t.spec || '').substring(0, 80) + '</span>' +
      '<span style="color:#8b949e; font-size:11px;">' + t.task_id + '</span>' +
      '</div>' + err + arch + '</div>';
  }).join('');
}

async function loadTasks() {
  try {
    const r = await fetch(API + '/v8/task/list?server_id=default&created_by=' + userId);
    const tasks = await r.json();
    const container = document.getElementById('chatMessages');
    container.querySelectorAll('.task-card').forEach(el => el.remove());
    const card = document.createElement('div');
    card.className = 'msg agent task-card';
    let html = '<b>📋 任务看板</b><br>';
    const emoji = { 'pending': '⏳', 'running': '🔄', 'done': '✅', 'reviewed': '✔️', 'failed': '❌' };
    for (const t of tasks.slice(-4)) {
      html += `${emoji[t.status] || '❓'} ${t.title || '无标题'} → @${t.assigned_to || '待分配'}<br>`;
    }
    const lastTask = localStorage.getItem('last_task_id');
    if (lastTask && lastTask.startsWith('async_')) {
      try {
        const tr = await fetch(API + '/v9/task/' + lastTask + '?user_id=' + userId + '&session_id=' + sessionId);
        const td = await tr.json();
        if (td.success && td.status !== 'not_found') {
          html += '<br><b>🤖 Agent 工作区</b><br>';
          html += `${td.status === 'done' ? '✅' : '🔄'} 最近任务: ${td.status || '未知'}<br>`;
        }
      } catch (e) { }
    }
    card.innerHTML = html; container.appendChild(card);
  } catch (e) { }
}

async function agentSendAsync() {
  const input = document.getElementById('agentInput'), task = input.value.trim();
  if (!task) return;
  const taskId = 'async_' + Date.now().toString(36);
  agentLog('🔗 后台任务 ' + taskId.substring(0, 12) + ' 已启动', '#1f6feb');
  input.value = '';
  try {
    const resp = await fetch(API + '/v9/agent/chat', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ async: true, task_id: taskId, user_id: _curUser(), session_id: _curSession(), model: 'deepseek-v4-flash', messages: [{ role: 'system', content: '你是 ClawsJoy 的 AI 助手。' }, { role: 'user', content: task }] })
    });
    const d = await resp.json();
    if (d.success) { localStorage.setItem('last_task_id', taskId); agentLog('⏳ 后台执行中，可关闭页面，稍后查看结果', '#d2991d'); pollTaskResult(taskId); }
    else agentLog('❌ 启动失败: ' + (d.error || '未知'), '#f85149');
  } catch (e) { agentLog('❌ 网络错误', '#f85149'); }
}

async function pollTaskResult(taskId, retryCount = 0) {
  if (retryCount > 20) { agentLog('⏰ 后台任务超时，请检查任务状态', '#f85149'); return; }
  try {
    const resp = await fetch(API + '/v9/task/' + taskId + '?user_id=' + userId + '&session_id=' + sessionId);
    const d = await resp.json();
    if (d.success) {
      if (d.status === 'done') { agentLog('✅ 后台任务完成', '#3fb950'); if (d.content) agentLog('🤖 ' + d.content, '#c9d1d9'); return; }
      if (d.status === 'failed') { agentLog('❌ 后台任务失败: ' + (d.content || '未知错误'), '#f85149'); return; }
    }
    setTimeout(() => pollTaskResult(taskId, retryCount + 1), 3000);
  } catch (e) { setTimeout(() => pollTaskResult(taskId, retryCount + 1), 5000); }
}

  // ===== window 挂载(内联 onclick / 其他模块依赖) ===== 

  global.createSubtask = createSubtask
  global.pollSubtasks = pollSubtasks
  global.renderSubtasks = renderSubtasks
  global.loadTasks = loadTasks
  global.agentSendAsync = agentSendAsync
  global.pollTaskResult = pollTaskResult
})(window)
