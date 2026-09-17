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
 * 聊天/讨论模块 — 从 workbench.html 提取(拆分映射表步骤 7)
 * 依赖: window.agentLog / window.renderAgentOutput(agent-terminal) / window.escapeHtml(内联)
 *       window.__APP_STATE(discussionHistory/planState 变换) / atList 模块内
 * 内联 onclick: send/clearChat/insertAt/saveCurrentDiscussion/saveDiscussionRecordFromView/showDiscussionRecord/... → window 挂载
 */

  var atList = null   // @成员 弹出层(模块内状态)

async function clearChat() {
  if (!confirm('确定清空当前对话？将清除聊天显示、本地历史与后端会话上下文（不会删除你的文件）。')) return;
  const chatBox = document.getElementById('chatMessages');
  if (chatBox) {
    chatBox.innerHTML = '<div class="empty-hint">👋 欢迎使用 ClawsJoy v8<br>输入消息开始工作</div>';
  }
  const dc = document.getElementById('discussion-container');
  if (dc) { dc.innerHTML = ''; dc.style.display = 'none'; }
  localStorage.removeItem('v8_messages');
  const inp = document.getElementById('chatInput');
  if (inp) inp.value = '';
  try {
    await fetch(API + '/v9/session/clean', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: _curUser(), session_id: _curSession() })
    });
  } catch(e) { console.error('clean session failed:', e); }
}

async function send() {
  const input = document.getElementById('chatInput'), msg = input.value.trim();
  if (!msg) return;
  // /clean 会话清理指令（方案B: 前端拦截，不发给 V5/Agent）
  if (/^\/clean$/i.test(msg) || /^\/clear$/i.test(msg) || /^\/clearsession$/i.test(msg)) {
    input.value = '';
    clearChat();
    return;
  }
  addMessage('user', msg); input.value = ''; hideAtList();
  // 持久化消息到 localStorage
  try {
    const msgs = JSON.parse(localStorage.getItem('v8_messages') || '[]');
    msgs.push({ role: 'user', content: msg, time: Date.now() });
    localStorage.setItem('v8_messages', JSON.stringify(msgs.slice(-50)));
  } catch(e) {}

  // 检测 @ 提及，决定路由
  const atMatch = msg.match(/^@(\S+)/);
  const atName = atMatch ? atMatch[1].replace(/[,.，。!！?？:：]+$/, '') : '';
  const agentLabel = atName || '包工头';
  // ← 加在这里
  // /CLEAN_DISC 指令 — 清空讨论界面，不删文件
  if (/^\/CLEAN_DISC/i.test(msg)) {
    const dc = document.getElementById('discussion-container');
    if (dc) { dc.innerHTML = ''; dc.style.display = 'none'; }
    document.getElementById('chatInput').disabled = false;
    document.querySelector('.chat-input')?.classList.remove('disabled');
    __APP_STATE.planState = { status: '', plan: null };
    localStorage.setItem("__APP_STATE.planState", JSON.stringify(__APP_STATE.planState));
    return;
  }
  if (atName && (atName === '计划经理' || atName === '编排Agent')) {
    // 检测多 Agent 讨论指令：@计划经理 你们讨论一下 <主题>
    const discussionMatch = msg.match(/^@计划经理\s+你们讨论一下\s+(.+)/);
    if (discussionMatch) {
      __APP_STATE.planState = { status: 'agent_discussion', plan: __APP_STATE.planState.plan || { plan: [], _discussion: [] }, focus: discussionMatch[1].trim() };
      // 禁用输入框，显示讨论容器
      document.getElementById('chatInput').disabled = true;
      document.querySelector('.chat-input').classList.add('disabled');
      const dc = document.getElementById('discussion-container');
      if (dc) { dc.style.display = 'block'; dc.innerHTML = '<div class="discussion-header"><h3>🧠 多 Agent 讨论</h3><p>主题: ' + __APP_STATE.planState.focus + '</p></div>'; }
      // 清除非讨论消息
      const msgs = document.getElementById('chatMessages');
      const hints = msgs.querySelectorAll('.empty-hint');
      hints.forEach(h => h.remove());
    } else {
      __APP_STATE.planState = { status: 'discussing', plan: __APP_STATE.planState.plan || { plan: [], _discussion: [] } };
    }
  }
  // 频道 Agent：直接走 SSE 流式
    if (atName) {
    try {
      const resp = await fetch(API + '/api/v5/chat/stream', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(Object.assign(
          { message: msg, user_id: _curUser(), agent_name: agentLabel, session_id: 'web_' + _curUser() },
          (agentLabel === '计划经理' || agentLabel === '编排Agent') ? {
            current_plan: __APP_STATE.planState.plan || { plan: [], _discussion: [] },
            plan_status: __APP_STATE.planState.status,
            ...(__APP_STATE.planState.status === 'agent_discussion' ? { focus: __APP_STATE.planState.focus, agents: window._rosterAgents || [] } : {})
          } : {}
        ))
      });
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let replyText = '';
      const msgDiv = addMessage('agent', '', agentLabel);
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value);
        console.log('raw:', text);
	const lines = text.split('\n');
        console.log('lines:', lines);
	for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const d = JSON.parse(line.slice(6));
              // === Agent Discussion 模式 ===
              if (__APP_STATE.planState.status === 'agent_discussion') {
                if (d.type === 'token') {
                  // 逐 token 追加到对应 Agent 气泡
                  document.getElementById('discussion-container').style.display = 'block';
                  const dc = document.getElementById('discussion-container');
                  const agentKey = (d.agent || '').replace(/\s+/g, '-');
                  const r = d.round || 1;
                  let bubble = dc.querySelector('.discussion-message.round-' + r + '.agent-' + agentKey + ' .discussion-content');
                  if (!bubble) {
                    const div = document.createElement('div');
                    div.className = 'discussion-round round-' + r + ' agent-' + agentKey;
                    div.innerHTML = '<div class="discussion-agent-name">🤖 ' + escapeHtml(d.agent) + ' <span class="discussion-round-label">第 ' + r + ' 轮</span></div><div class="discussion-content"></div>';
                    div.classList.add('discussion-message');
                    dc.appendChild(div);
                    bubble = div.querySelector('.discussion-content');
                    if (!__APP_STATE.discussionHistory) __APP_STATE.discussionHistory = { rounds: [], participants: new Set(), history: [] };
                    __APP_STATE.discussionHistory.participants.add(d.agent);
                    __APP_STATE.discussionHistory.history.push({ type: 'round_start', round: r, agent: d.agent, time: Date.now() });
                  }
                  bubble.textContent += d.token || '';
                  dc.scrollTop = dc.scrollHeight;
                } else if (d.type === 'agent_output') {
                  document.getElementById('discussion-container').style.display = 'block';
                  renderAgentOutput(d.agent, d.content, d.round);
                  // 累积讨论数据
                  if (!__APP_STATE.discussionHistory) __APP_STATE.discussionHistory = { rounds: [], participants: new Set(), history: [] };
                  __APP_STATE.discussionHistory.participants.add(d.agent);
                  __APP_STATE.discussionHistory.rounds.push({ round: d.round || 1, agent: d.agent, content: d.content });
                  __APP_STATE.discussionHistory.history.push({ type: 'agent_output', round: d.round || 1, agent: d.agent, content: d.content, time: Date.now() });
                } else if (d.type === 'done' || d.done === true) {
                  renderDiscussionDone(d.consensus, d.decision, d.rounds);
                  // 保存完整讨论记录到 localStorage
                  try {
                    if (__APP_STATE.discussionHistory) {
                      __APP_STATE.discussionHistory.topic = __APP_STATE.planState.focus || '';
                      __APP_STATE.discussionHistory.consensus = !!d.consensus;
                      __APP_STATE.discussionHistory.decision = d.decision || '';
                      __APP_STATE.discussionHistory.rounds_count = d.rounds || 0;
                      __APP_STATE.discussionHistory.participants = [...discussionHistory.participants];
                      __APP_STATE.discussionHistory.time = Date.now();
                      const key = 'v8_discussion_' + Date.now();
                      localStorage.setItem(key, JSON.stringify(__APP_STATE.discussionHistory));
                      __APP_STATE.discussionHistory = null;
                      // 刷新讨论历史列表
                      const countEl = document.getElementById('discussionHistoryCount');
                      const listEl = document.getElementById('discussionHistoryList');
                      if (countEl) {
                        const keys = Object.keys(localStorage).filter(k => k.startsWith('v8_discussion_')).sort().reverse();
                        countEl.textContent = keys.length;
                        countEl.style.display = 'inline';
                      }
                      if (listEl) refreshDiscussionHistoryList();
                    }
                  } catch(e) { console.warn('save discussion failed', e); }
                  // 恢复输入
                  document.getElementById('chatInput').disabled = false;
                  document.querySelector('.chat-input').classList.remove('disabled');
                  __APP_STATE.planState = { status: '', plan: d.current_plan || null };
                  localStorage.setItem("__APP_STATE.planState", JSON.stringify(__APP_STATE.planState));
                  // 持久化共识结果到消息历史
                  try {
                    const ms = JSON.parse(localStorage.getItem("v8_messages") || "[]");
                    ms.push({ role: "agent", content: d.decision || '(无决策)', agent: '🧠 讨论共识', time: Date.now() });
                    localStorage.setItem("v8_messages", JSON.stringify(ms.slice(-50)));
                  } catch(e) {}
                  break;
                }
                continue;
              }
              // === 普通模式 ===
              if (d.done || d.type === 'done') {
                // Agent Discussion 共识结果处理（后端返回 {done, consensus, decision, rounds} 无 type 字段）
                if (d.consensus !== undefined) {
                  document.getElementById('discussion-container').style.display = 'block';
		  renderDiscussionDone(d.consensus, d.decision, d.rounds);
                  document.getElementById('chatInput').disabled = false;
		  document.querySelector('.chat-input').classList.remove('disabled');
                  __APP_STATE.planState = { status: '', plan: d.current_plan || null };
                  localStorage.setItem("__APP_STATE.planState", JSON.stringify(__APP_STATE.planState));
                  try {
                    const ms = JSON.parse(localStorage.getItem("v8_messages") || "[]");
                    ms.push({ role: "agent", content: d.decision || '(无决策)', agent: '🧠 讨论共识', time: Date.now() });
                    localStorage.setItem("v8_messages", JSON.stringify(ms.slice(-50)));
                  } catch(e) {}
                  break;
                }
                if ((d.plan_status === 'discussing' || d.plan_status === 'agent_discussion') && d.current_plan) {
                  __APP_STATE.planState = { status: 'discussing', plan: d.current_plan };
                  localStorage.setItem("__APP_STATE.planState", JSON.stringify(__APP_STATE.planState));
                } else if (d.plan_status === 'confirmed' && d.current_plan) {
                  __APP_STATE.planState = { status: 'confirmed', plan: d.current_plan };
                  localStorage.setItem("__APP_STATE.planState", JSON.stringify(__APP_STATE.planState));
                }
                // #189 方案B：else 分支不再清空 __APP_STATE.planState（仅 confirmed 或新任务时重置）
                try {
                  const msgs = JSON.parse(localStorage.getItem("v8_messages") || "[]");
                  msgs.push({ role: "agent", content: replyText, agent: agentLabel, time: Date.now() });
                  localStorage.setItem("v8_messages", JSON.stringify(msgs.slice(-50)));
                } catch(e) {}
                break;
              }
              replyText += d.chunk || '';
              console.log('chunk:', d.chunk, 'replyText:', replyText);
	      msgDiv.querySelector("span.msg-text").textContent = replyText;
      addDiscussBtn(msgDiv, replyText);
            } catch(e) {}
          }
    }
      }
      loadMembers(); loadTasks();
    } catch(e) { addMessage('agent', '出错了: ' + e.message, agentLabel); }
    return;
  }

  // 构建请求体
  const body = { raw_input: msg, user_id: _curUser(), session_id: 'web_' + _curUser(), server_id: 'default' };
  if (__APP_STATE.planState.status === 'discussing' && __APP_STATE.planState.plan) {
    body.plan_status = 'discussing';
    body.current_plan = __APP_STATE.planState.plan;
  } else if (__APP_STATE.planState.status === 'confirmed' && __APP_STATE.planState.plan) {
    body.plan_status = 'confirmed';
    body.current_plan = __APP_STATE.planState.plan;
    __APP_STATE.planState = { status: '', plan: null };
    localStorage.setItem("__APP_STATE.planState", JSON.stringify(__APP_STATE.planState));
  }

  try {
    const r = await fetch(API + '/v5/execute', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    const d = await r.json();
    const reply = d.response || d.output_content || d.message || '';
    const replyAgent = d.agent_name || agentLabel;
    if (reply) {
      const msgs = document.getElementById('chatMessages').children;
      if (msgs.length > 0) msgs[msgs.length - 1].remove();
      addMessage('agent', reply, replyAgent);
      try {
        const msgs = JSON.parse(localStorage.getItem('v8_messages') || '[]');
        msgs.push({ role: 'agent', content: reply, agent: replyAgent, time: Date.now() });
        localStorage.setItem('v8_messages', JSON.stringify(msgs.slice(-50)));
      } catch(e) {}
    }
    if (d.plan_status === 'discussing' && d.current_plan) {
      __APP_STATE.planState = { status: 'discussing', plan: d.current_plan };
      localStorage.setItem("__APP_STATE.planState", JSON.stringify(__APP_STATE.planState));
    } else if (d.status === 'executing') {
      __APP_STATE.planState = { status: '', plan: null };
      localStorage.setItem("__APP_STATE.planState", JSON.stringify(__APP_STATE.planState));
      addMessage('agent', '✅ 任务已启动（V9 异步执行中）', '系统');
    } else if (d.success && d.response && d.response.includes('📋')) {
      __APP_STATE.planState = { status: 'discussing', plan: { plan: d.tasks || [], _discussion: [] } };
      localStorage.setItem("__APP_STATE.planState", JSON.stringify(__APP_STATE.planState));
    }
    loadMembers(); loadTasks();
  } catch (e) { addMessage('agent', '出错了: ' + e.message); }
}

function addDiscussBtn(div, text) {
  if (div.querySelector('.discuss-btn') || !text || !String(text).trim()) return;
  const btn = document.createElement('button');
  btn.className = 'discuss-btn';
  btn.textContent = '💬 发起讨论';
  btn.onclick = function () {
    const clean = String(text).replace(/\s+/g, ' ').trim();
    const summary = clean.slice(0, 50) + (clean.length > 50 ? '…' : '');
    const input = document.getElementById('chatInput');
    input.value = '@计划经理 你们讨论一下 ' + summary;
    send();
  };
  div.appendChild(btn);
}

function addMessage(type, text, tag) {
  const container = document.getElementById('chatMessages');
  const hint = container.querySelector('.empty-hint');
  if (hint) hint.remove();
  const div = document.createElement('div');
  div.className = 'msg ' + type;
  if (tag) { const t = document.createElement('div'); t.className = 'tag'; t.textContent = '🤖 ' + tag; div.appendChild(t); }
  if (text === '') {
    const span = document.createElement('span');
    span.className = 'msg-text';
    div.appendChild(span);
  } else {
    div.appendChild(document.createTextNode(text));
  }
  if (text === '') div.lastChild.classList.add('msg-text');
  // 💬 发起讨论：Agent 回复气泡上的讨论入口（复用 send() 中 348 行 agent_discussion 分支）
  if (type === 'agent') addDiscussBtn(div, text);
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return div;
}

function showAtList() {
  if (atList) return;
  atList = document.createElement('div'); atList.className = 'at-list';
  fetch(API + '/v8/roster/list?server_id=default').then(r => r.json()).then(members => {
    atList.innerHTML = members.length
      ? members.map(m => `<div onmousedown="event.preventDefault()" onclick="insertAt('${m.name}')">${m.position === '程序员' ? '👨‍💻' : m.position === '设计师' ? '👩‍🎨' : '📊'} ${m.name} · ${m.position}</div>`).join('')
      : '<div style="color:var(--sub)">暂无成员</div>';
  });
  document.querySelector('.chat-input').appendChild(atList);
}

function hideAtList() { if (atList) { atList.remove(); atList = null; } }

function insertAt(name) {
  const input = document.getElementById('chatInput'), val = input.value, lastAt = val.lastIndexOf('@');
  input.value = val.substring(0, lastAt) + '@' + name + ' ';
  hideAtList(); input.focus();
}

function renderDiscussionDone(consensus, decision, rounds) {
  const dc = document.getElementById('discussion-container');
  if (!dc) return;
  const statusIcon = consensus ? '✅' : '⚠️';
  const statusText = consensus ? '已达成共识' : '未达成共识（使用兜底决策）';
  const panel = document.createElement('div');
  panel.className = 'discussion-done-panel';
  panel.innerHTML = '<div class="discussion-consensus-header">' + statusIcon + ' ' + statusText + '</div>' +
    '<div class="discussion-consensus-body">' +
    '<div class="discussion-decision-label">📋 最终决策</div>' +
    '<div class="discussion-decision-content">' + escapeHtml(decision||'') + '</div>' +
    '<div class="discussion-rounds-info">共进行了 <strong>' + (rounds||0) + '</strong> 轮讨论</div></div>' +
    '<button class="discussion-save-btn" onclick="saveCurrentDiscussion()" style="margin:12px;padding:8px 16px;background:var(--green);color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px;">💾 保存到历史</button>';
  dc.appendChild(panel);
  dc.scrollTop = dc.scrollHeight;
}

function saveCurrentDiscussion() {
  // 保存当前讨论到服务器
  if (!window._discussionHistory) {
    // 尝试从 __APP_STATE.discussionHistory 全局变量获取
    if (typeof __APP_STATE.discussionHistory !== 'undefined' && __APP_STATE.discussionHistory) {
      window._discussionHistory = __APP_STATE.discussionHistory;
    } else {
      alert('没有可保存的讨论数据');
      return;
    }
  }
  const data = window._discussionHistory;
  if (!data || (!data.topic && !data.decision)) {
    alert('没有可保存的讨论数据');
    return;
  }
  fetch(API + '/v8/discussions/save', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      topic: data.topic || '',
      consensus: !!data.consensus,
      decision: data.decision || '',
      rounds_count: data.rounds_count || data.rounds?.length || 0,
      participants: Array.isArray(data.participants) ? data.participants : [],
      rounds: data.rounds || [],
      history: data.history || [],
      time: Date.now()
    })
  })
  .then(r => r.json())
  .then(res => {
    if (res.success) {
      const btn = event?.target || document.querySelector('.discussion-save-btn');
      if (btn) { btn.textContent = '✅ 已保存'; btn.style.opacity = '0.6'; btn.disabled = true; }
      refreshDiscussionHistoryList();
    }
  })
  .catch(() => {});
}

function showDiscussionRecordFromApi(index) {
  const rec = _apiDiscussionsCache[index];
  if (!rec) return;
  // 尝试加载完整记录
  const recordId = rec.id || '';
  if (recordId) {
    fetch(API + '/v8/discussions/get?id=' + encodeURIComponent(recordId))
      .then(r => r.json())
      .then(data => {
        if (data.success && data.record) {
          _displayDiscussionRecord(data.record);
        } else {
          _displayDiscussionRecord(rec);
        }
      })
      .catch(() => _displayDiscussionRecord(rec));
  } else {
    _displayDiscussionRecord(rec);
  }
}

function _displayDiscussionRecord(rec) {
  // 切换到聊天 tab
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.getElementById('tab-chat').classList.add('active');
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  const chatBtn = document.querySelector('.nav-btn[data-tab="chat"]');
  if (chatBtn) chatBtn.classList.add('active');
  const dc = document.getElementById('discussion-container');
  if (!dc) return;
  dc.style.display = 'block';
  dc.innerHTML = '<div class="discussion-header"><h3>📜 历史讨论: ' + escapeHtml(rec.topic || '') + '</h3><p>' + new Date(rec.timestamp || rec.time).toLocaleString() + ' · 👥 ' + escapeHtml((rec.participants || []).join(', ')) + '</p></div>';
  // 渲染各轮讨论
  const history = rec.history || [];
  history.forEach(h => {
    if (h.type === 'agent_output' && h.content) {
      const bubble = document.createElement('div');
      bubble.className = 'discussion-round round-' + (h.round||1) + ' agent-' + (h.agent||'').replace(/\s+/g, '-') + ' discussion-message';
      bubble.innerHTML = '<div class="discussion-agent-name">🤖 ' + escapeHtml(h.agent) + ' <span class="discussion-round-label">第 ' + (h.round||1) + ' 轮</span></div><div class="discussion-content">' + escapeHtml(h.content) + '</div>';
      dc.appendChild(bubble);
    }
  });
  // 渲染 consensus 面板 + 保存按钮
  if (rec.decision) {
    const panel = document.createElement('div');
    panel.className = 'discussion-done-panel';
    panel.innerHTML = '<div class="discussion-consensus-header">' + (rec.consensus ? '✅ 已达成共识' : '⚠️ 未达成共识（使用兜底决策）') + '</div>' +
      '<div class="discussion-decision-label">📋 最终决策</div>' +
      '<div class="discussion-decision-content">' + escapeHtml(rec.decision) + '</div>' +
      '<div class="discussion-rounds-info">共进行了 <strong>' + (rec.rounds || 0) + '</strong> 轮讨论</div>' +
      '<button class="discussion-save-btn" onclick="saveDiscussionRecordFromView()" style="margin:12px;padding:8px 16px;background:var(--green);color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px;">💾 保存到历史</button>';
    dc.appendChild(panel);
  }
  dc.scrollTop = dc.scrollHeight;
}

function saveDiscussionRecordFromView() {
  // 从当前显示的讨论容器中提取数据
  const dc = document.getElementById('discussion-container');
  if (!dc) return;
  const headerEl = dc.querySelector('.discussion-header h3');
  const topic = headerEl ? headerEl.textContent.replace('📜 历史讨论: ', '') : '';
  const decisionEl = dc.querySelector('.discussion-decision-content');
  const decision = decisionEl ? decisionEl.textContent : '';
  const consensusHeader = dc.querySelector('.discussion-consensus-header');
  const consensus = consensusHeader ? consensusHeader.textContent.includes('✅') : false;
  const roundsInfo = dc.querySelector('.discussion-rounds-info');
  const roundsMatch = roundsInfo ? roundsInfo.textContent.match(/(\d+)/) : null;
  const rounds = roundsMatch ? parseInt(roundsMatch[1]) : 0;
  // 提取参与者
  const participants = [];
  dc.querySelectorAll('.discussion-agent-name').forEach(el => {
    const name = el.textContent.replace(/🤖\s*/, '').replace(/\s*第.*轮/, '').trim();
    if (name && !participants.includes(name)) participants.push(name);
  });
  // 提取历史
  const history = [];
  dc.querySelectorAll('.discussion-message').forEach(el => {
    const agentEl = el.querySelector('.discussion-agent-name');
    const contentEl = el.querySelector('.discussion-content');
    if (agentEl && contentEl) {
      history.push({
        type: 'agent_output',
        agent: agentEl.textContent.replace(/🤖\s*/, '').replace(/\s*第.*轮/, '').trim(),
        content: contentEl.textContent,
        round: 1
      });
    }
  });
  const data = { topic, consensus, decision, rounds_count: rounds, participants, history, time: Date.now() };
  fetch(API + '/v8/discussions/save', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(data)
  })
  .then(r => r.json())
  .then(res => {
    if (res.success) {
      const btn = dc.querySelector('.discussion-save-btn');
      if (btn) { btn.textContent = '✅ 已保存'; btn.style.opacity = '0.6'; btn.disabled = true; }
      refreshDiscussionHistoryList();
    }
  })
  .catch(() => {});
}

function refreshDiscussionHistoryList() {
  // 优先从 API 加载，localStorage 兜底
  fetch(API + '/v8/discussions/list')
    .then(r => r.json())
    .then(data => {
      if (data.success && data.records && data.records.length > 0) {
        _renderDiscussionList(data.records, true);
      } else {
        _renderDiscussionListFromLocal();
      }
    })
    .catch(() => _renderDiscussionListFromLocal());
}

function _renderDiscussionListFromLocal() {
  try {
    const keys = Object.keys(localStorage).filter(k => k.startsWith('v8_discussion_')).sort().reverse();
    const listEl = document.getElementById('discussionHistoryList');
    if (!listEl) return;
    if (keys.length === 0) { listEl.innerHTML = '<div class="empty-hint">暂无讨论记录</div>'; return; }
    listEl.innerHTML = keys.map(key => {
      try {
        const rec = JSON.parse(localStorage.getItem(key));
        if (!rec) return '';
        const timeStr = new Date(rec.time || parseInt(key.replace('v8_discussion_',''))).toLocaleString();
        const topic = rec.topic || '(无主题)';
        const participants = (rec.participants || []).join(', ') || '未知';
        const decisionPreview = (rec.decision || '').slice(0, 60);
        return '<div class="discussion-history-item" style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:12px;margin-bottom:8px;cursor:pointer;" onclick="showDiscussionRecord(\'' + key + '\')">' +
          '<div style="font-size:11px;color:var(--sub);">' + timeStr + '</div>' +
          '<div class="discussion-history-topic">' + escapeHtml(topic) + '</div>' +
          '<div class="discussion-history-meta">👥 ' + escapeHtml(participants) + ' · ' + (rec.rounds_count || 0) + ' 轮' +
          (rec.consensus ? ' · ✅ 共识' : ' · ⚠️ 未共识') + '</div>' +
          '<div style="font-size:11px;color:var(--sub);margin-top:2px;">📋 ' + escapeHtml(decisionPreview) + (rec.decision && rec.decision.length > 60 ? '...' : '') + '</div>' +
          '</div>';
      } catch(e) { return ''; }
    }).join('');
  } catch(e) {}
}

function _renderDiscussionList(records, fromApi) {
  _apiDiscussionsCache = records || [];
  const listEl = document.getElementById('discussionHistoryList');
  if (!listEl) return;
  if (!records || records.length === 0) {
    _renderDiscussionListFromLocal();
    return;
  }
  listEl.innerHTML = records.map(rec => {
    const timeStr = rec.timestamp ? new Date(rec.timestamp).toLocaleString() : '';
    const topic = rec.topic || '(无主题)';
    const participants = (rec.participants || []).join(', ') || '未知';
    const decisionPreview = (rec.decision || '').slice(0, 60);
    return '<div class="discussion-history-item" style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:12px;margin-bottom:8px;cursor:pointer;" onclick="showDiscussionRecordFromApi(' + (records.indexOf(rec)) + ')">' +
      '<div style="font-size:11px;color:var(--sub);">' + timeStr + '</div>' +
      '<div class="discussion-history-topic">' + escapeHtml(topic) + '</div>' +
      '<div class="discussion-history-meta">👥 ' + escapeHtml(participants) + ' · ' + (rec.rounds || 0) + ' 轮' +
      (rec.consensus ? ' · ✅ 共识' : ' · ⚠️ 未共识') + '</div>' +
      '<div style="font-size:11px;color:var(--sub);margin-top:2px;">📋 ' + escapeHtml(decisionPreview) + (rec.decision && rec.decision.length > 60 ? '...' : '') + '</div>' +
      '</div>';
  }).join('');
  // 更新计数徽章
  const countEl = document.getElementById('discussionHistoryCount');
  if (countEl && records.length > 0) { countEl.textContent = records.length; countEl.style.display = 'inline'; }
}

function showDiscussionRecord(key) {
  try {
    const rec = JSON.parse(localStorage.getItem(key));
    if (!rec) return;
    // 切换到聊天 tab
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.getElementById('tab-chat').classList.add('active');
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    const chatBtn = document.querySelector('.nav-btn[data-tab="chat"]');
    if (chatBtn) chatBtn.classList.add('active');
    const dc = document.getElementById('discussion-container');
    if (!dc) return;
    dc.style.display = 'block';
    dc.innerHTML = '<div class="discussion-header"><h3>📜 历史讨论: ' + escapeHtml(rec.topic || '') + '</h3><p>' + new Date(rec.time).toLocaleString() + ' · 👥 ' + escapeHtml((rec.participants || []).join(', ')) + '</p></div>';
    // 渲染各轮讨论
    const history = rec.history || [];
    history.forEach(h => {
      if (h.type === 'agent_output' && h.content) {
        const bubble = document.createElement('div');
        bubble.className = 'discussion-round round-' + (h.round||1) + ' agent-' + (h.agent||'').replace(/\s+/g, '-') + ' discussion-message';
        bubble.innerHTML = '<div class="discussion-agent-name">🤖 ' + escapeHtml(h.agent) + ' <span class="discussion-round-label">第 ' + (h.round||1) + ' 轮</span></div><div class="discussion-content">' + escapeHtml(h.content) + '</div>';
        dc.appendChild(bubble);
      }
    });
    // 渲染 consensus 面板 + 保存按钮
    if (rec.decision) {
      const panel = document.createElement('div');
      panel.className = 'discussion-done-panel';
      panel.innerHTML = '<div class="discussion-consensus-header">' + (rec.consensus ? '✅ 已达成共识' : '⚠️ 未达成共识（使用兜底决策）') + '</div>' +
        '<div class="discussion-decision-label">📋 最终决策</div>' +
        '<div class="discussion-decision-content">' + escapeHtml(rec.decision) + '</div>' +
        '<div class="discussion-rounds-info">共进行了 <strong>' + (rec.rounds_count || 0) + '</strong> 轮讨论</div>' +
        '<button class="discussion-save-btn" onclick="saveDiscussionRecordFromView()" style="margin:12px;padding:8px 16px;background:var(--green);color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px;">💾 保存到历史</button>';
      dc.appendChild(panel);
    }
    dc.scrollTop = dc.scrollHeight;
  } catch(e) { console.warn('show discussion failed', e); }
}

  // ===== window 挂载(内联 onclick / 其他模块依赖) ===== 

  global.clearChat = clearChat
  global.send = send
  global.addDiscussBtn = addDiscussBtn
  global.addMessage = addMessage
  global.showAtList = showAtList
  global.hideAtList = hideAtList
  global.insertAt = insertAt
  global.renderDiscussionDone = renderDiscussionDone
  global.saveCurrentDiscussion = saveCurrentDiscussion
  global.showDiscussionRecordFromApi = showDiscussionRecordFromApi
  global._displayDiscussionRecord = _displayDiscussionRecord
  global.saveDiscussionRecordFromView = saveDiscussionRecordFromView
  global.refreshDiscussionHistoryList = refreshDiscussionHistoryList
  global._renderDiscussionListFromLocal = _renderDiscussionListFromLocal
  global._renderDiscussionList = _renderDiscussionList
  global.showDiscussionRecord = showDiscussionRecord
})(window)
