/**
 * Agent 聊天循环模块 — 从 workbench.html 提取(拆分映射表步骤 4)
 * 依赖: window.__APP_STATE(userId/sessionId/currentThread/agentRunning/agentAbort)
 *       window.escapeHtml(内联)/window.__agentAbort/window.__agentSendMessages
 *       window.renderWriteConfirmCard/renderAskCard/renderPlanConfirmCard(内联, 步骤 5 迁移)
 * 内联 onclick 依赖: agentSend/agentStop/continuePausedTask → window 挂载
 */
(function (global) {
  'use strict'

  var __APP_STATE = global.__APP_STATE || {}
  var API = (global.CLAWSJOY_API_BASE || (global.localStorage && global.localStorage.getItem('clawsjoy_api_base')) || '')
  var userId = __APP_STATE.userId || ''
  // 跨线程隔离修复: userId/sessionId/currentThread 不再用模块加载时快照 —
  // 线程切换(switchThread/newThread)只更新 __APP_STATE/localStorage, 快照不更新 → 请求串到旧线程/旧用户。
  // 改为运行时读取: 每次发请求/读历史前取当前值。
  var sessionId = __APP_STATE.sessionId || ''
  var currentThread = __APP_STATE.currentThread || (global.localStorage && global.localStorage.getItem('current_thread')) || ''
  function _curUser() {
    return (__APP_STATE && __APP_STATE.userId) || (global.localStorage && global.localStorage.getItem('clawsjoy_user_id')) || userId
  }
  function _curSession() {
    return (__APP_STATE && __APP_STATE.sessionId) || (global.localStorage && global.localStorage.getItem('clawsjoy_session_id')) || sessionId
  }
  function _curThread() {
    return (__APP_STATE && __APP_STATE.currentThread) || (global.localStorage && global.localStorage.getItem('current_thread')) || currentThread
  }


async function readSSEStream(resp) {
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  let donePayload = { success: true, tool_steps: [] };
  const seenRounds = new Set();
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buf.indexOf('\n')) >= 0) {
      const line = buf.slice(0, idx).trim();
      buf = buf.slice(idx + 1);
      if (!line.startsWith('data: ')) continue;
      const payload = line.slice(6);
      if (payload === '[DONE]') { return donePayload; }
      let evt;
      try { evt = JSON.parse(payload); } catch (e) { continue; }
      if (evt.type === 'done') {
        donePayload = evt;
        if (evt.tool_steps && evt.tool_steps.length) {
          for (const step of evt.tool_steps) {
            const key = step.round + ':' + step.tool + ':' + (step.arg || '').substring(0, 40);
            if (seenRounds.has(key)) continue;
            seenRounds.add(key);
            const _pp = step.reason === 'preview_pending'   // 批183 · C3：桥未就绪 = 降级状态（不是失败）
            const icon = _pp ? '⏳' : (step.success ? '✅' : '❌')
            const mark = step.escalated ? ' [越权已拦截]' : ''
            const argTxt = step.arg ? ' ' + String(step.arg).substring(0, 80) : ''
            const errTxt = _pp ? (' — 预览待 WPS 就绪' + (step.artifact && step.artifact.path ? ('（产物：' + step.artifact.path + '）') : '（本次未取到产物路径）'))
                                   : (step.error ? ' — ' + String(step.error).substring(0, 100) : '')
            agentLog(icon + ' ' + step.tool + '(' + argTxt + ')' + mark + errTxt, _pp ? '#d2991d' : (step.success ? '#3fb950' : '#f85149'))
            if (_pp) { if (typeof global.renderWpsReadyCard === 'function') global.renderWpsReadyCard(step.hint, step.artifact) }
            else if (step.ready === true && typeof global.clearWpsReadyCard === 'function') global.clearWpsReadyCard()
          }
        }
        if (evt.progress && typeof renderProgressBar === 'function') renderProgressBar(evt.progress);
        // P0-2: SSE done 事件 bridge_exhausted → 记录标记供 runAgentLoop 无条件 break
        if (evt.bridge_exhausted) {
          agentLog('⚠️ 已达单轮最大工具调用数（工具已由服务端执行）', '#d2991d');
          donePayload.bridge_exhausted = true;
        }
        // 任务2 v8: 流式 done 事件补状态卡片（write_pending/ask/plan/escalation）——
        // 此前只渲染 tool_steps/progress, 锚点A写审批状态被丢弃导致任务卡死
        if (evt.status === 'write_pending' && evt.pending_write && typeof renderWriteConfirmCard === 'function') {
          // 批136：把守卫的 reason（含目标 URL）一并交给卡片组件渲染
          renderWriteConfirmCard(evt.pending_write, evt.reason_detail || evt.reason || '');
        } else if (evt.status === 'ask' && evt.ask && typeof renderAskCard === 'function') {
          renderAskCard(evt.ask);
        } else if (evt.status === 'plan_pending' && typeof renderPlanConfirmCard === 'function') {
          renderPlanConfirmCard(evt.plan || {});
        } else if (evt.status === 'escalation_blocked') {
          agentLog('🚨 越权已拦截：' + ((evt.blocked && evt.blocked.reason) || ''), '#f85149');
        }
      } else if (evt.type === 'progress') {
        const steps = evt.tool_steps || [];
        for (const step of steps) {
          const key = step.round + ':' + step.tool + ':' + (step.arg || '').substring(0, 40);
          if (seenRounds.has(key)) continue;
          seenRounds.add(key);
          const _pp = step.reason === 'preview_pending'   // 批183 · C3：桥未就绪 = 降级状态（不是失败）
          const icon = _pp ? '⏳' : (step.success ? '✅' : '❌')
          const mark = step.escalated ? ' [越权已拦截]' : ''
          const argTxt = step.arg ? ' ' + String(step.arg).substring(0, 80) : ''
          const errTxt = _pp ? (' — 预览待 WPS 就绪' + (step.artifact && step.artifact.path ? ('（产物：' + step.artifact.path + '）') : '（本次未取到产物路径）'))
                                 : (step.error ? ' — ' + String(step.error).substring(0, 100) : '')
          agentLog(icon + ' ' + step.tool + '(' + argTxt + ')' + mark + errTxt, _pp ? '#d2991d' : (step.success ? '#3fb950' : '#f85149'))
          if (_pp) { if (typeof global.renderWpsReadyCard === 'function') global.renderWpsReadyCard(step.hint, step.artifact) }
          else if (step.ready === true && typeof global.clearWpsReadyCard === 'function') global.clearWpsReadyCard()
        }
        if (evt.progress && typeof renderProgressBar === 'function') renderProgressBar(evt.progress);
      } else if (evt.type === 'error') {
        donePayload = { success: false, error: evt.error || '流式响应错误' };
      } else if (evt.type === 'start') {
        agentLog('🔧 ' + (evt.message || '任务开始'), '#8b949e');
      }
    }
  }
  return donePayload;
}

async function executeToolCall(name, args, rawArgs) {
  const base = { method: 'POST', headers: { 'Content-Type': 'application/json' } };
  const body = { user_id: _curUser(), session_id: _curSession(), ...args };
  // write_file 长内容走独立字段，不经过 JSON 序列化
  if (name === 'write_file' && rawArgs) {
    try {
      let contentMatch = rawArgs.match(/"content":\s*"([\s\S]*?)"(,\s*"|}$)/);
      if (contentMatch) {
        body.content = contentMatch[1];  // 原始 content，不经过 JSON 转义
      }
    } catch(e) {}
  }
  const endpoints = {
    read_file: '/v9/sandbox/read', write_file: '/v9/sandbox/write',
    list_dir: '/v9/sandbox/list', search_files: '/v9/sandbox/search',
    execute_command: '/v9/sandbox/exec', edit_file: '/v9/sandbox/edit',
    query_index: '/v9/sandbox/query_index', write_large: '/v9/sandbox/write_large'
  };
  // write_file 长内容自动路由到 write_large
  if (name === 'write_file' && body.raw_arguments && body.raw_arguments.length > 3000) {
    return await fetch(API + '/v9/sandbox/write_large', { ...base, body: JSON.stringify({ user_id: _curUser(), session_id: _curSession(), path: body.path, raw_arguments: body.raw_arguments }) }).then(r => r.json());
  }
  if (!endpoints[name]) return { success: false, error: '未知工具: ' + name };
  return await fetch(API + endpoints[name], { ...base, body: JSON.stringify(body) }).then(r => r.json());
}

async function agentSend(continueMsgs) {
  const input = document.getElementById('agentInput');
  const task = input.value.trim();
  // 审批/选择回传后继续：continueMsgs 为后端回传的完整消息上下文，跳过输入校验
  if (continueMsgs && continueMsgs.length > 0) {
    __APP_STATE.agentRunning = true; __APP_STATE.agentAbort = false;
    const _sb1 = document.getElementById('agentStopBtn'); if (_sb1) _sb1.style.display = 'inline-block';
    document.getElementById('agentStopBtn').style.display = 'inline-block';
    let messages = continueMsgs.slice();
    window.__agentSendMessages = messages;
    runAgentLoop(messages);
    return;
  }
  if (!task || __APP_STATE.agentRunning) return;
  if (task.toUpperCase() === '/CLEAN') {
    localStorage.removeItem('agent_logs_' + _curThread());
    document.getElementById('agentTerminal').innerHTML = '<div style="color:#58a6ff;">🤖 ClawsJoy Agent 就绪。输入任务开始。</div>';
    input.value = ''; return;
  }
  input.value = '';
  __APP_STATE.agentRunning = true; __APP_STATE.agentAbort = false;
  document.getElementById('agentStopBtn').style.display = 'inline-block';
  agentLog('👤 ' + task, '#58a6ff');

  // 2026-09-07: 移除误导性「恢复上次对话上下文」死代码 — 该块只打日志从未真正注入,
  // 且让用户误以为上下文被恢复(真实机制在后端会话日志, 任务边界已由后端隔离)。
  // 每个新任务都是干净的 [system, user] 请求, 由后端按 POST 推进任务边界。
  let messages = [
    { role: 'system', content: '你是 ClawsJoy 的 AI 助手。根据用户任务自动判断角色。每次开始工作时，第一句话声明角色，格式：🔄 以XX身份工作。你可以操作文件系统——读取、写入、搜索文件。遇到任务先分析，再动手。每次只做一件事，做完看结果再决定下一步。' },
    { role: 'user', content: task }
  ];
  // #102 键点A：全局挂载 messages，供 approve 请求携带上下文
  window.__agentSendMessages = messages;
  runAgentLoop(messages);
}

async function runAgentLoop(messages) {
  // Goal 驱动多 turn: 续跑标记(仅本循环内有效; max_tokens+goal 未完成 → 下一轮 POST 带 continue_goal)
  let _goalContinue = false;
  // task 从消息中推导（agentSend 本地变量在 continuation 路径不可见）
  let task = '';
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].role === 'user') { task = String(messages[i].content || '').slice(0, 200); break; }
  }
  let maxLoops = 200;
  while (!__APP_STATE.agentAbort && maxLoops > 0) {
    const lastMsg = messages[messages.length - 1];
    const isReadOnly = lastMsg && lastMsg.tool_calls && lastMsg.tool_calls.every(t => ['read_file','list_dir','search_files'].includes(t.function.name));
    if (!isReadOnly) maxLoops--;
    try {
      // #1 协作取消: 挂 AbortController(停止按钮 abort 中断 SSE 流)
      window.__agentAbort = new AbortController();
      const resp = await fetch(API + '/v9/agent/chat', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        signal: window.__agentAbort.signal,
        body: JSON.stringify({ user_id: _curUser(), session_id: _curSession(), model: 'deepseek-v4-flash', messages, stream: true, continue_goal: _goalContinue })
      });
      // 任务2 流式: SSE 响应实时解析（progress 事件逐条渲染 tool_steps + 进度条），done 事件组装最终 d；非流式 JSON fallback
      let d = null;
      const _ct = (resp.headers.get('content-type') || '');
      if (_ct.includes('text/event-stream')) {
        d = await readSSEStream(resp);
      } else {
        d = await resp.json();
      }
      if (!d.success) {
        const errMsg = d.error || '';
        let friendlyMsg = '😵 服务暂时不可用，请稍后重试';
        if (errMsg.includes('未配置') || errMsg.includes('API Key') || errMsg.includes('Key丢失')) {
          friendlyMsg = '🤖 服务暂未配置，请在设置中填入 API 密钥';
        } else if (errMsg.includes('超时') || errMsg.includes('timeout')) {
          friendlyMsg = '⏳ AI 服务响应超时，请稍后重试';
        } else if (errMsg.includes('余额') || errMsg.includes('balance') || errMsg.includes('quota')) {
          friendlyMsg = '💰 API 余额不足，请充值后继续';
        } else if (errMsg.includes('网络') || errMsg.includes('Network') || errMsg.includes('connect')) {
          friendlyMsg = '🌐 网络连接失败，请检查网络后重试';
        } else if (errMsg.includes('API错误: 400')) {
          friendlyMsg = '📦 上下文过大，已自动压缩。请继续当前任务。';
	} else if (errMsg.includes('503') || errMsg.includes('500')) {
          friendlyMsg = '🏥 AI 服务繁忙，请稍后重试';
        }
        agentLog('❌ ' + friendlyMsg, '#f85149');
        if (errMsg) agentLog('   （' + errMsg + '）', '#8b949e');
        // 1258 行改为：
        const historyKey = 'agent_history_' + _curThread();
        const historyStr = JSON.stringify({ task: task, messages: messages });
        if (historyStr.length > 2 * 1024 * 1024) {
          // 超过 2MB，只保留最近 100 条消息
          const trimmed = { task: task, messages: messages.slice(-100) };
          localStorage.setItem(historyKey, JSON.stringify(trimmed));
        } else {
          localStorage.setItem(historyKey, historyStr);
        }
        break;
      }

      // V8 tasks use separate polling

      // 批223：**入口 seed 门短路状态**（沙箱未 seed / seed 标记与内容不符 ⇒ 后端在 ROUND/LLM 之前短路）
      if (d.status === 'blocked' && d.blocked) {
        agentLog('⛔ ' + (d.reason || '沙箱未绑定主体项目（seed 门拦截）'), '#f85149');
        if (d.blocked_goal) agentLog('   已落盘 blocked goal：' + d.blocked_goal, '#8b949e');
        return;
      }

      // 批191 · 修（承 pm_1402 §三）：seed 门**失败**（entry.py:99 `status:"seed_failed"`）——
      //   后端在 ROUND 前短路，载荷**无 `d.data`** ⇒ 若落到下方 `d.data.choices[0]` 即 TypeError。
      //   故须先拦并**显其因**（⛔ 静默 · 承四态「缺则显因」）。
      if (d.status === 'seed_failed') {
        agentLog('⛔ ' + (d.message || '会话 sandbox seed 失败（查 V9_SEED_SOURCE / 磁盘）'), '#f85149');
        return;
      }

      // seed 门「审批回执豁免」（entry.py:121 `status:"approval_exempt"`）——
      //   回执是同一 run 的延续 ⇒ ⛔ 当错误 · ⛔ 静默（如该值真达前端，照实记一行后停，⛔ 落 `d.data` 而崩）。
      if (d.status === 'approval_exempt') {
        agentLog('ℹ️ seed 门豁免（审批回执延续）', '#8b949e');
        return;
      }

      // 批189 · #6：PA 单线程 ⇒ 后端只允许一个活动 run（并发第二发返回 busy）
      if (d.status === 'busy') {
        agentLog('⏳ ' + (d.reason || '已有任务正在执行（PA 单线程）'), '#d2991d');
        return;
      }

      if (d.status === 'initializing') {
        agentLog('🔧 ' + d.message, '#d2991d');
        setTimeout(() => agentSend(), 3000);
        return;
      }

      // #104 键点B：越权拦截（一律拒绝，无审批放行）
      if (d.status === 'escalation_blocked') {
        if (d.tool_steps && d.tool_steps.length > 0) {
          for (const step of d.tool_steps) {
            const isEsc = !!step.escalated;
            const icon = isEsc ? '⚠️' : (step.success ? '✅' : '❌');
            const mark = isEsc ? ' [越权已拦截]' : '';
            const argTxt = step.arg ? ' ' + String(step.arg).substring(0, 80) : '';
            const errTxt = step.error ? ' — ' + String(step.error).substring(0, 100) : '';
            agentLog(icon + ' ' + step.tool + '(' + argTxt + ')' + mark + errTxt,
                     isEsc ? '#f85149' : (step.success ? '#3fb950' : '#f85149'));
          }
        }
        if (d.blocked) {
          const b = d.blocked;
          const reason = b.reason || '越权操作';
          const target = b.path || b.command || '';
          agentLog('🚨 越权已拦截：' + reason + ' → ' + String(target).substring(0, 120), '#f85149');
          agentLog('🔒 已强制拉回沙箱（clawsjoy_dev/），Agent 将调整方案', '#d2991d');
        }
        // 断点2: 越权被拒后立即引导换路径 — 注入拉回消息并继续循环(原 return 停住, LLM 无法换路径)
        if (d.data && d.data.choices && d.data.choices[0] && d.data.choices[0].message) {
          const escMsg = d.data.choices[0].message.content || '';
          if (escMsg) {
            agentLog('🤖 ' + escMsg, '#c9d1d9');
            messages.push({ role: 'assistant', content: escMsg });
          }
        }
        continue;
      }

      // #102 键点A：写操作等待确认
      if (d.status === 'write_pending') {
        if (d.tool_steps && d.tool_steps.length > 0) {
          for (const step of d.tool_steps) {
            const isPend = !!step.pending;
            const icon = isPend ? '⏳' : (step.success ? '✅' : '❌');
            const mark = isPend ? ' [待确认]' : '';
            const argTxt = step.arg ? ' ' + String(step.arg).substring(0, 80) : '';
            const errTxt = (!isPend && step.error) ? ' — ' + String(step.error).substring(0, 100) : '';
            agentLog(icon + ' ' + step.tool + '(' + argTxt + ')' + mark + errTxt,
                     isPend ? '#d2991d' : (step.success ? '#3fb950' : '#f85149'));
          }
        }
        if (d.pending_write) {
          renderWriteConfirmCard(d.pending_write, d.reason_detail || d.reason || '');
        }
        return; // 暂停循环，等老板点卡片按钮后继续
      }

      // #101 G2 计划确认强制：多文件/多意图任务先列计划等确认
      if (d.status === 'plan_pending') {
        if (d.tool_steps && d.tool_steps.length > 0) {
          for (const step of d.tool_steps) {
            const isPlan = !!step.plan_pending;
            const icon = isPlan ? '📋' : (step.success ? '✅' : '❌');
            const mark = isPlan ? ' [待确认计划]' : '';
            const argTxt = step.arg ? ' ' + String(step.arg).substring(0, 80) : '';
            const errTxt = (!isPlan && step.error) ? ' — ' + String(step.error).substring(0, 100) : '';
            agentLog(icon + ' ' + step.tool + '(' + argTxt + ')' + mark + errTxt,
                     isPlan ? '#d2991d' : (step.success ? '#3fb950' : '#f85149'));
          }
        }
        if (d.plan_pending_info) {
          renderPlanConfirmCard(d.plan_pending_info);
        }
        return; // 暂停循环，等老板点计划卡片按钮后继续
      }

      // #101 G3 ask 式提问通道：Agent 用结构化提问请求老板决策
      if (d.status === 'ask') {
        if (d.data && d.data.choices && d.data.choices[0] && d.data.choices[0].message) {
          agentLog('🤖 ' + (d.data.choices[0].message.content || ''), '#c9d1d9');
        }
        if (d.ask) {
          renderAskCard(d.ask);
        }
        return; // 暂停循环，等老板选择选项后继续
      }

      const msg = d.data.choices[0].message;
      // Turn 协议 Step3: reason 完整渲染。兼容旧 payload(无 reason 时按 bridge_exhausted 推断)。
      let turnReason = d.reason;
      if (!turnReason) {
        turnReason = d.bridge_exhausted ? 'max_tokens' : (msg.content ? 'completed' : 'need_more');
      }
      if (turnReason === 'completed') {
        if (msg.content) {
          if (msg.content.includes('📋 方案')) { agentLog(renderPlanButtons(msg.content), '#c9d1d9'); }
          else { agentLog('🤖 ' + msg.content, '#c9d1d9'); }
        }
        agentLog('✅ 任务完成', '#3fb950');
        localStorage.setItem('agent_history_' + _curThread(), JSON.stringify({ task: task, messages: messages }));
        break;
      }
      if (turnReason === 'max_tokens') {
        if (msg.content) {
          agentLog('🤖 ' + msg.content, '#c9d1d9');
          agentLog('⚠️ 已达轮次上限，以下为已有产出', '#d2991d');
        } else {
          // max_tokens 空产出修复: content 为空 → 显示 tool_steps 摘要而非"已有产出"
          const _sumTxt = buildToolStepsSummary(d.tool_steps);
          if (_sumTxt) {
            agentLog('🤖 ' + _sumTxt, '#c9d1d9');
            agentLog('⚠️ 已达轮次上限（已按工具调用汇总产出）', '#d2991d');
          } else {
            agentLog('⚠️ 已达轮次上限，未产生有效产出，请重新描述需求', '#d2991d');
          }
        }
        // Goal 驱动多 turn: goal 未完成且未达上限 → 自动开新 turn 继续(下一轮 POST 带 continue_goal)
        const _gi = d.goal_info || {};
        if (_gi.goal_active && !_gi.goal_complete && (_gi.turn || 0) < (_gi.max_turns || 5)) {
          _goalContinue = true;
          agentLog('🔄 第 ' + ((_gi.turn || 0) + 1) + ' 轮继续执行（目标进度 ' + (_gi.goal_done || 0) + '/' + (_gi.goal_total || 1) + '）', '#d2991d');
          messages = messages.concat([{ role: 'user', content: '[系统] 继续执行当前目标，请基于已有进度继续，不要重复已完成步骤。' }]);
          localStorage.setItem('agent_history_' + _curThread(), JSON.stringify({ task: task, messages: messages }));
          continue; // 复用现有 while 循环 → 下一轮 POST
        }
        _goalContinue = false;
        localStorage.setItem('agent_history_' + _curThread(), JSON.stringify({ task: task, messages: messages }));
        break;
      }
      if (turnReason === 'need_more' || turnReason === 'empty_reply') {
        agentLog('⚠️ 模型未产出有效内容，请重新描述需求或稍后重试', '#d2991d');
        localStorage.setItem('agent_history_' + _curThread(), JSON.stringify({ task: task, messages: messages }));
        break;
      }
      if (turnReason === 'error') {
        agentLog('❌ 执行出错: ' + (d.reason_detail || d.error || '未知错误'), '#f85149');
        agentLog('💡 请重新描述需求或稍后重试', '#d2991d');
        localStorage.setItem('agent_history_' + _curThread(), JSON.stringify({ task: task, messages: messages }));
        break;
      }
      if (turnReason === 'cancelled') {
        agentLog('⏹ 任务已取消（协作取消）', '#d2991d');
        localStorage.setItem('agent_history_' + _curThread(), JSON.stringify({ task: task, messages: messages }));
        break;
      }
      // P2: 空内容判断 — 无 content 且无 tool_calls → 提示重试, 不判完成(兼容无 reason 旧 payload)
      if (!msg.content && (!msg.tool_calls || msg.tool_calls.length === 0) && !d.bridge_exhausted) {
        agentLog('⚠️ 模型未产出有效内容，请重新描述需求或稍后重试', '#d2991d');
        localStorage.setItem('agent_history_' + _curThread(), JSON.stringify({ task: task, messages: messages }));
        break;
      }
      if (msg.content) {
        if (msg.content.includes('📋 方案')) {
          agentLog(renderPlanButtons(msg.content), '#c9d1d9');
        } else {
          agentLog('🤖 ' + msg.content, '#c9d1d9');
        }
      }

      // #101 渲染后端桥接执行的工具步骤（tool_steps 回传）
      if (msg.tool_steps && msg.tool_steps.length > 0) {
        for (const step of msg.tool_steps) {
          const _pp = step.reason === 'preview_pending'   // 批183 · C3：桥未就绪 = 降级状态（不是失败）
          const icon = _pp ? '⏳' : (step.success ? '✅' : '❌')
          const argTxt = step.arg ? ' ' + String(step.arg).substring(0, 80) : ''
          const errTxt = _pp ? (' — 预览待 WPS 就绪' + (step.artifact && step.artifact.path ? ('（产物：' + step.artifact.path + '）') : '（本次未取到产物路径）'))
                                 : (step.error ? ' — ' + String(step.error).substring(0, 100) : '')
          agentLog(icon + ' ' + step.tool + '(' + argTxt + ')' + errTxt, _pp ? '#d2991d' : (step.success ? '#3fb950' : '#f85149'))
          if (_pp) { if (typeof global.renderWpsReadyCard === 'function') global.renderWpsReadyCard(step.hint, step.artifact) }
          else if (step.ready === true && typeof global.clearWpsReadyCard === 'function') global.clearWpsReadyCard()
        }
      }
      // #101 G1 进度显式化：后端回传 progress → 渲染进度条 + 步骤清单
      // Goal 驱动多 turn: 优先按 goal 级进度(done/total)显示, 附 turn 徽标
      if (d.progress) {
        const _gip = d.goal_info || {};
        if (_gip.goal_total) {
          renderProgressBar({ done: _gip.goal_done, total: _gip.goal_total, step_index: _gip.turn, total_steps: _gip.max_turns, goal_turn: true });
        } else {
          renderProgressBar(d.progress);
        }
      }

      // P0-1 防重复：后端跑满 8 轮/工具数超限时 bridge_exhausted=true，工具已由服务端执行。
      // 必须无条件 break（在残留 tool_calls 的 continue 判断之前），否则 stale messages 死循环重发。
      if (d.bridge_exhausted) {
        agentLog('⚠️ 已达单轮最大工具调用数（工具已由服务端执行）', '#d2991d');
        localStorage.setItem('agent_history_' + _curThread(), JSON.stringify({ task: task, messages: messages }));
        break;
      }
      // 桥接模式防重复执行：done payload 的 assistant message 残留 tool_calls 时，
      // 工具已由服务端执行（d.tool_steps 非空），前端不再客户端重复执行，直接进入下一轮。
      // P0-1 双保险：exhausted 时绝不进入此处。
      if (d.tool_steps && d.tool_steps.length > 0 && msg.tool_calls && msg.tool_calls.length > 0 && !d.bridge_exhausted) {
        continue;
      }

      if (!msg.tool_calls || msg.tool_calls.length === 0) {
        agentLog('✅ 任务完成', '#3fb950');
        localStorage.setItem('agent_history_' + _curThread(), JSON.stringify({ task: task, messages: messages }));
        break;
      }

      messages.push({ role: 'assistant', content: msg.content || '', tool_calls: msg.tool_calls });
      if (msg.reasoning_content) messages[messages.length - 1].reasoning_content = msg.reasoning_content;

      for (const tool of msg.tool_calls) {
        let args;
        const raw = tool.function.arguments;
        try {
          args = JSON.parse(raw);
          args.raw_arguments = raw;
        } catch(e) {
          // P1: 前端不提取，整段 raw_arguments 传给网关
          if (raw.includes('"command"')) {
            args = { raw_arguments: raw };
          } else {
            const pathMatch = raw.match(/"path"\s*:\s*"([^"]+)"/);
            const lineMatch = raw.match(/"line"\s*:\s*(\d+)/);
            const contentMatch = raw.match(/"content"\s*:\s*"([\s\S]*?)(?:"\s*}\s*$|"\s*,\s*"line|"\s*,\s*"path)/);
            args = {
              path: pathMatch ? pathMatch[1] : '',
              line: lineMatch ? parseInt(lineMatch[1]) : 0,
              content: contentMatch ? contentMatch[1] : '',
              command: '',
              raw_arguments: raw
            };
          }
        }

        if (tool.function.name === 'write_file') {
          if (!args.path) { agentLog('⚠️ write_file path 为空，跳过', '#d2991d'); continue; }
        } else if (tool.function.name === 'execute_command') {
          // P1: args 已在上方处理，直接放行
        } else {
          try {
            args = JSON.parse(tool.function.arguments);
            args.raw_arguments = tool.function.arguments;
          } catch(e2) {
            let fixed = tool.function.arguments;
            let strategies = [
              () => {
                let s = fixed;
                if (s.split('"').length % 2 === 0) { s += '"'; }
                s = s.replace(/\n/g, '\\n').replace(/\r/g, '\\r').replace(/\t/g, '\\t');
                return s;
              },
              () => {
                let s = fixed;
                let contentIdx = s.indexOf('"content":');
                if (contentIdx > 0) {
                  let afterContent = s.substring(contentIdx + 11);
                  let endQuote = afterContent.indexOf('",');
                  if (endQuote > 0) {
                    let contentEnd = contentIdx + 11 + endQuote;
                    s = s.substring(0, contentEnd + 2) + '}';
                  }
                }
                return s;
              },
              () => {
                let pathMatch = fixed.match(/"path":\s*"([^"]+)"/);
                let contentStart = fixed.indexOf('"content":');
                if (pathMatch && contentStart > 0) {
                  let contentValue = fixed.substring(contentStart + 12, fixed.lastIndexOf('"'));
                  let args = { path: pathMatch[1], content: contentValue };
                  let lineMatch = fixed.match(/"line":\s*(\d+)/);
                  if (lineMatch) { args.line = parseInt(lineMatch[1]); }
                  return JSON.stringify(args);
                }
                return fixed;
              }
            ];
            let parsed = false;
            for (let strategy of strategies) {
              try {
                args = JSON.parse(strategy());
                args.raw_arguments = tool.function.arguments;
                parsed = true;
                break;
              } catch(e3) {}
            }
            if (!parsed) { agentLog('❌ 工具参数 JSON 解析失败，跳过此步骤', '#f85149'); continue; }
          }
        }

        agentLog('🔧 ' + tool.function.name + '(' + JSON.stringify(args) + ')', '#d2991d');
        // P2 本地浏览器实时状态: 执行前提示(操作可见性)
        if (tool.function.name === 'browser_local') {
          const _ba = args.action || '';
          const _bt = _ba === 'fill' ? ('填写 ' + (args.selector || '')) : _ba === 'click' ? ('点击 ' + (args.selector || '')) : _ba === 'search' ? ('搜索 ' + (args.query || '')) : _ba;
          agentLog('🖥️ 正在操作本地浏览器: ' + _bt, '#a371f7');
        }
        let result, retries = 3;
        while (retries > 0) {
          result = await executeToolCall(tool.function.name, args, tool.function.arguments);
          const errMsg = typeof result.error === 'string' ? result.error : (result.error?.message || '');
          if (result.success || errMsg.startsWith('未知工具')) break;
          retries--;
          if (retries > 0) agentLog('🔄 重试中... (' + retries + '次剩余)', '#d2991d');
        }
        let toolResult = JSON.stringify(result);
        try {
          let tr = JSON.parse(toolResult);
          if (tr.content && typeof tr.content === 'string' && tr.content.length > 2000) {
            tr.content = tr.content.substring(0, 2000) + '\n... (内容已截断，共 ' + tr.content.length + ' 字符)';
            toolResult = JSON.stringify(tr);
          }
        } catch(e) {}
        agentLog('📤 ' + toolResult.substring(0, 500), '#8b949e');
        // P2 本地浏览器: 敏感操作触发审批卡 → 暂停循环等用户确认
        if (tool.function.name === 'browser_local' && result && result.pending) {
          if (typeof renderBrowserConfirmCard === 'function') {
            agentLog('🖥️ ' + (result.action || '') + ' 需要确认：' + (result.reason || ''), '#a371f7');
            renderBrowserConfirmCard({ op_id: result.op_id, action: result.action, reason: result.reason, params: result.params });
          } else {
            agentLog('🖥️ 浏览器操作待确认: ' + (result.reason || ''), '#a371f7');
          }
          window.__APP_STATE.agentRunning = false;
          return; // 暂停循环, 等审批回传后 agentSend(continue_messages) 继续
        }
        if (tool.function.name === 'edit_file' && !result.success && result.error && result.error.includes('FIM match failed')) {
          toolResult = JSON.stringify({ error: "edit_file failed. Please use write_file with the full file content.", hint: "write_file(path, full_content)" });
        }
        messages.push({ role: 'tool', tool_call_id: tool.id, content: toolResult });
        if (tool.function.name === 'write_file' || tool.function.name === 'write_large') {
          try {
            let tr = JSON.parse(toolResult);
            if (tr.auto_fixed === false) {
              messages.push({ role: "system", content: `[系统] write_file 写入失败，网关自动修复也失败。你必须用 python3 heredoc 方式重新写入，不要再调 write_file 或 execute_command。

python3 << PYEOF
content = """..."""
with open("目标文件", "w") as f:
    f.write(content)
PYEOF` });
            }
          } catch(e) {}
        }
      }
      refreshFileTree();
    } catch (e) {
      if (e && e.name === 'AbortError') { agentLog('⏹ 已取消', '#d2991d'); break; }
      agentLog('❌ 错误: ' + e.message, '#f85149'); break;
    }
  }
  if (maxLoops === 0) {
    agentLog('⚠ 达到最大循环次数，当前进度：', '#d2991d');
    let ps = getProgressSummary(messages);
    if (ps.filesRead.length) agentLog('  📄 已读: ' + ps.filesRead.join(', '), '#8b949e');
    if (ps.filesModified.length) agentLog('  ✏ 已修改: ' + ps.filesModified.join(', '), '#8b949e');
    agentLog('  📊 已执行: ' + messages.length + '轮', '#8b949e');
    localStorage.setItem('agent_pause_' + _curThread(), JSON.stringify({ task: task, messages: messages }));
    const div = document.createElement('div');
    div.style.cssText = 'margin-top:10px;display:flex;gap:8px;';
    div.innerHTML = '<button id="btnContinue" style="background:#238636;color:#fff;border:none;border-radius:6px;padding:8px 16px;cursor:pointer;">▶ 继续任务(25轮)</button><button id="btnCancel" style="background:#30363d;color:#c9d1d9;border:none;border-radius:6px;padding:8px 16px;cursor:pointer;">✕ 放弃</button>';
    document.getElementById('agentTerminal').appendChild(div);
    document.getElementById('btnContinue').onclick = function() {
      const saved = JSON.parse(localStorage.getItem('agent_pause_' + _curThread()));
      if (saved && saved.messages) {
        div.remove();
        agentLog('▶ 继续执行...', '#d2991d');
        __APP_STATE.agentRunning = true;
        document.getElementById('agentStopBtn').style.display = 'inline-block';
        saved.messages.push({
          role: 'system',
          content: '【任务中断恢复】之前的任务因达到循环上限被暂停。已完成: ' + (saved.progress || '未知') + '。请从断点继续，不要重复已完成步骤。如果目标代码已处于期望状态，直接验证并汇报。'
        });
        continuePausedTask(saved.messages);
      }
    };
    document.getElementById('btnCancel').onclick = function() {
      localStorage.removeItem('agent_pause_' + _curThread()); div.remove(); agentLog('✕ 任务已放弃', '#8b949e'); __APP_STATE.agentRunning = false; document.getElementById('agentStopBtn').style.display = 'none';
    };
    return;
  }
  __APP_STATE.agentRunning = false;
  document.getElementById('agentStopBtn').style.display = 'none';
}

// max_tokens 空产出修复: 从 tool_steps 提取产出摘要(与后端 _build_tool_steps_summary 同构, 不调 LLM)
  // 批183 · C1：WPS 灵犀（TaskPane）未就绪的**就绪引导卡片** —— 可一键复制操作步骤；桥就绪后自动消失。
  function renderWpsReadyCard(hint, artifact) {
    try {
      var host = document.getElementById('agentLog') || document.querySelector('.agent-log') || document.body
      if (!host) return
      clearWpsReadyCard()
      var steps = ['打开 WPS（文字/演示任一）', '点右下角「灵犀」面板', '在面板里开启 MCP（桥）', '回到这里点「重试」']
      var esc = global.escapeHtml || function (s) { return String(s == null ? '' : s) }
      var copyTxt = 'WPS 灵犀就绪操作：' + steps.map(function (s, i) { return (i + 1) + '. ' + s }).join('；')
      var d = document.createElement('div')
      d.id = 'wpsReadyCard'
      d.style.cssText = 'border:1px solid #9e6a03;border-radius:8px;background:#2d2411;padding:8px 10px;margin:6px 0;font-size:12px;color:#c9d1d9'
      d.innerHTML = '<div style="color:#d29922;margin-bottom:4px">⏳ 预览待 WPS 就绪 —— 这不是任务失败</div>'
        + '<div style="margin-bottom:6px">' + esc(hint || 'WPS 灵犀面板（TaskPane）未开或未登录 —— PA 无法自动开启（WPS 插件硬边界）') + '</div>'
        + '<ol style="margin:0 0 6px 18px;padding:0">' + steps.map(function (s) { return '<li>' + esc(s) + '</li>' }).join('') + '</ol>'
        + (artifact ? '<div style="color:#8b949e;font-family:monospace;margin-bottom:6px">产物：' + esc(artifact) + '</div>'
                     : '<div style="color:#d29922;margin-bottom:6px">本次未取到产物路径（不假报「已生成」；产物也可能在 WPS 侧）</div>')
        + '<button data-wpscopy="1" style="font-size:11px;padding:2px 8px;border-radius:6px;border:1px solid #9e6a03;background:#161b22;color:#d29922;cursor:pointer">⧉ 复制操作步骤</button>'
      var btn = d.querySelector('button[data-wpscopy]')
      if (btn) btn.onclick = function () { try { navigator.clipboard.writeText(copyTxt) } catch (e) {} }
      host.appendChild(d)
    } catch (e) {}
  }
  function clearWpsReadyCard() {
    try { var old = document.getElementById('wpsReadyCard'); if (old && old.parentNode) old.parentNode.removeChild(old) } catch (e) {}
  }
  global.renderWpsReadyCard = renderWpsReadyCard
  global.clearWpsReadyCard = clearWpsReadyCard

function buildToolStepsSummary(steps) {
  if (!steps || steps.length === 0) return '';
  const ok = steps.filter(s => s.success);
  let sum = '已完成 ' + steps.length + ' 个工具调用，成功 ' + ok.length + ' 个。';
  if (ok.length > 0) {
    const lastOk = ok[ok.length - 1];
    const finding = String(lastOk.result || lastOk.arg || '').substring(0, 160);
    if (finding) sum += '关键发现：' + finding;
  }
  return sum;
}

function renderProgressBar(progress) {
  if (!progress || typeof progress.done !== 'number') return;
  const key = progress.done + '/' + progress.total;
  if (key === _lastProgressKey) return; // 同一进度不重复渲染
  _lastProgressKey = key;
  const term = document.getElementById('term') || document.getElementById('agentTerminal');
  const bar = document.createElement('div');
  bar.style.cssText = 'background:#1c2128;border:1px solid #30363d;border-radius:8px;padding:10px 14px;margin:8px 0;';
  const pct = progress.total > 0 ? Math.min(100, Math.round(progress.done / progress.total * 100)) : 0;
  const label = document.createElement('div');
  label.style.cssText = 'color:#8b949e;font-size:12px;margin-bottom:6px;';
  // Goal 驱动多 turn: goal_turn=true 时显示轮次徽标(第 N/max_turns 轮)
  label.textContent = '📊 目标进度 ' + progress.done + '/' + progress.total + '（' + pct + '%）' + (progress.goal_turn && progress.step_index ? ' · 第 ' + progress.step_index + '/' + (progress.total_steps || progress.total) + ' 轮' : (progress.step_index ? ' · 步骤 ' + (progress.step_index) + '/' + (progress.total_steps || progress.total) : ''));
  bar.appendChild(label);
  const track = document.createElement('div');
  track.style.cssText = 'background:#30363d;border-radius:4px;height:8px;overflow:hidden;';
  const fill = document.createElement('div');
  fill.style.cssText = 'background:#1f6feb;border-radius:4px;height:100%;width:' + pct + '%;transition:width .3s;';
  track.appendChild(fill);
  bar.appendChild(track);
  term.appendChild(bar);
  term.scrollTop = term.scrollHeight;
}

function getProgressSummary(messages) {
  let filesRead = [...new Set(messages.filter(m => m.tool_calls).flatMap(m => m.tool_calls.filter(tc => tc.function.name === 'read_file').map(tc => JSON.parse(tc.function.arguments).path)))];
  let filesModified = [...new Set(messages.filter(m => m.tool_calls).flatMap(m => m.tool_calls.filter(tc => tc.function.name === 'write_file').map(tc => JSON.parse(tc.function.arguments).path)))];
  let summary = [];
  if (filesRead.length) summary.push('已读文件: ' + filesRead.join(', '));
  if (filesModified.length) summary.push('已修改: ' + filesModified.join(', '));
  summary.push('总轮次: ' + messages.length);
  return { filesRead, filesModified, text: summary.join('; ') };
}

function agentStop() {
  __APP_STATE.agentAbort = true;
  const _sb = document.getElementById('agentStopBtn'); if (_sb) _sb.style.display = 'none';
  // #1 协作取消: 通知服务端(置位取消标志, bridge_loop 下轮检查点退出) + 中断 SSE 流
  try { if (window.__agentAbort) window.__agentAbort.abort(); } catch (e) {}
  try { fetch(API + '/v9/cancel/' + encodeURIComponent(_curSession()), { method: 'POST' }).catch(function(){}); } catch (e) {}
  agentLog('⏹ 已发送停止请求，等待服务端协作退出…', '#d2991d');
}

async function continuePausedTask(messages) {
  // Goal 驱动多 turn: 续跑标记(仅本循环内有效)
  let _goalContinue2 = false;
  let maxLoops = 200;
  while (!__APP_STATE.agentAbort && maxLoops > 0) {
    maxLoops--;
    try {
      // #1 协作取消: continuePausedTask 同挂 AbortController
      window.__agentAbort = new AbortController();
      const resp = await fetch(API + '/v9/agent/chat', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        signal: window.__agentAbort.signal,
        body: JSON.stringify({ user_id: _curUser(), session_id: _curSession(), model: 'deepseek-v4-flash', messages, continue_goal: _goalContinue2 })
      });
      const d = await resp.json();
      if (!d.success) {
        const errMsg = d.error || '';
        let friendlyMsg = '😵 服务暂时不可用，请稍后重试';
        if (errMsg.includes('未配置') || errMsg.includes('API Key') || errMsg.includes('Key丢失')) {
          friendlyMsg = '🤖 服务暂未配置，请在设置中填入 API 密钥';
        } else if (errMsg.includes('超时') || errMsg.includes('timeout')) {
          friendlyMsg = '⏳ AI 服务响应超时，请稍后重试';
        } else if (errMsg.includes('余额') || errMsg.includes('balance') || errMsg.includes('quota')) {
          friendlyMsg = '💰 API 余额不足，请充值后继续';
        } else if (errMsg.includes('网络') || errMsg.includes('Network') || errMsg.includes('connect')) {
          friendlyMsg = '🌐 网络连接失败，请检查网络后重试';
        } else if (errMsg.includes('503') || errMsg.includes('500')) {
          friendlyMsg = '🏥 AI 服务繁忙，请稍后重试';
        }
        agentLog('❌ ' + friendlyMsg, '#f85149');
        if (errMsg) agentLog('   （' + errMsg + '）', '#8b949e');
        localStorage.setItem('agent_history_' + _curThread(), JSON.stringify({ task: task, messages: messages }));
        break;
      }

      const msg = d.data.choices[0].message;
      // Turn 协议 Step3: reason 完整渲染(兼容旧 payload 按 bridge_exhausted 推断)
      let turnReason2 = d.reason;
      if (!turnReason2) {
        turnReason2 = d.bridge_exhausted ? 'max_tokens' : (msg.content ? 'completed' : 'need_more');
      }
      if (turnReason2 === 'completed') {
        if (msg.content) agentLog('🤖 ' + msg.content, '#c9d1d9');
        agentLog('✅ 任务完成', '#3fb950');
        localStorage.setItem('agent_history_' + _curThread(), JSON.stringify({ task: task, messages: messages }));
        break;
      }
      if (turnReason2 === 'max_tokens') {
        if (msg.content) {
          agentLog('🤖 ' + msg.content, '#c9d1d9');
          agentLog('⚠️ 已达轮次上限，以下为已有产出', '#d2991d');
        } else {
          // max_tokens 空产出修复: content 为空 → 显示 tool_steps 摘要而非"已有产出"
          const _sumTxt2 = buildToolStepsSummary(d.tool_steps);
          if (_sumTxt2) {
            agentLog('🤖 ' + _sumTxt2, '#c9d1d9');
            agentLog('⚠️ 已达轮次上限（已按工具调用汇总产出）', '#d2991d');
          } else {
            agentLog('⚠️ 已达轮次上限，未产生有效产出，请重新描述需求', '#d2991d');
          }
        }
        // Goal 驱动多 turn: goal 未完成且未达上限 → 自动开新 turn 继续
        const _gi2 = d.goal_info || {};
        if (_gi2.goal_active && !_gi2.goal_complete && (_gi2.turn || 0) < (_gi2.max_turns || 5)) {
          _goalContinue2 = true;
          agentLog('🔄 第 ' + ((_gi2.turn || 0) + 1) + ' 轮继续执行（目标进度 ' + (_gi2.goal_done || 0) + '/' + (_gi2.goal_total || 1) + '）', '#d2991d');
          messages = messages.concat([{ role: 'user', content: '[系统] 继续执行当前目标，请基于已有进度继续，不要重复已完成步骤。' }]);
          localStorage.setItem('agent_history_' + _curThread(), JSON.stringify({ task: task, messages: messages }));
          continue; // 复用现有 while 循环 → 下一轮 POST
        }
        _goalContinue2 = false;
        localStorage.setItem('agent_history_' + _curThread(), JSON.stringify({ task: task, messages: messages }));
        break;
      }
      if (turnReason2 === 'need_more' || turnReason2 === 'empty_reply') {
        agentLog('⚠️ 模型未产出有效内容，请重新描述需求或稍后重试', '#d2991d');
        localStorage.setItem('agent_history_' + _curThread(), JSON.stringify({ task: task, messages: messages }));
        break;
      }
      if (turnReason2 === 'error') {
        agentLog('❌ 执行出错: ' + (d.reason_detail || d.error || '未知错误'), '#f85149');
        localStorage.setItem('agent_history_' + _curThread(), JSON.stringify({ task: task, messages: messages }));
        break;
      }
      if (turnReason2 === 'cancelled') {
        agentLog('⏹ 任务已取消（协作取消）', '#d2991d');
        localStorage.setItem('agent_history_' + _curThread(), JSON.stringify({ task: task, messages: messages }));
        break;
      }
      // P2: 空内容判断(兼容无 reason 旧 payload)
      if (!msg.content && (!msg.tool_calls || msg.tool_calls.length === 0) && !d.bridge_exhausted) {
        agentLog('⚠️ 模型未产出有效内容，请重新描述需求或稍后重试', '#d2991d');
        localStorage.setItem('agent_history_' + _curThread(), JSON.stringify({ task: task, messages: messages }));
        break;
      }
      if (msg.content) agentLog('🤖 ' + msg.content, '#c9d1d9');

      if (!msg.tool_calls || msg.tool_calls.length === 0) {
        agentLog('✅ 任务完成', '#3fb950');
        localStorage.setItem('agent_history_' + _curThread(), JSON.stringify({ task: task, messages: messages }));
        break;
      }

      messages.push({ role: 'assistant', content: msg.content || '', tool_calls: msg.tool_calls });

      for (const tool of msg.tool_calls) {
        let args;
        const raw = tool.function.arguments;
        try {
          args = JSON.parse(raw);
          args.raw_arguments = raw;
        } catch(e) {
          // P1: 前端不提取，整段 raw_arguments 传给网关
          if (raw.includes('"command"')) {
            args = { raw_arguments: raw };
          } else {
            const pathMatch = raw.match(/"path"\s*:\s*"([^"]+)"/);
            const lineMatch = raw.match(/"line"\s*:\s*(\d+)/);
            const contentMatch = raw.match(/"content"\s*:\s*"([\s\S]*?)(?:"\s*}\s*$|"\s*,\s*"line|"\s*,\s*"path)/);
            args = {
              path: pathMatch ? pathMatch[1] : '',
              line: lineMatch ? parseInt(lineMatch[1]) : 0,
              content: contentMatch ? contentMatch[1] : '',
              command: '',
              raw_arguments: raw
            };
          }
        }

        if (tool.function.name === 'write_file') {
          if (!args.path) { agentLog('⚠️ write_file path 为空，跳过', '#d2991d'); continue; }
        } else if (tool.function.name === 'execute_command') {
          // P1: args 已在上方处理，直接放行
        } else {
          try {
            args = JSON.parse(tool.function.arguments);
            args.raw_arguments = tool.function.arguments;
          } catch(e2) {
            let fixed = tool.function.arguments;
            let strategies = [
              () => {
                let s = fixed;
                if (s.split('"').length % 2 === 0) { s += '"'; }
                s = s.replace(/\n/g, '\\n').replace(/\r/g, '\\r').replace(/\t/g, '\\t');
                return s;
              },
              () => {
                let s = fixed;
                let contentIdx = s.indexOf('"content":');
                if (contentIdx > 0) {
                  let afterContent = s.substring(contentIdx + 11);
                  let endQuote = afterContent.indexOf('",');
                  if (endQuote > 0) {
                    let contentEnd = contentIdx + 11 + endQuote;
                    s = s.substring(0, contentEnd + 2) + '}';
                  }
                }
                return s;
              },
              () => {
                let pathMatch = fixed.match(/"path":\s*"([^"]+)"/);
                let contentStart = fixed.indexOf('"content":');
                if (pathMatch && contentStart > 0) {
                  let contentValue = fixed.substring(contentStart + 12, fixed.lastIndexOf('"'));
                  let args = { path: pathMatch[1], content: contentValue };
                  let lineMatch = fixed.match(/"line":\s*(\d+)/);
                  if (lineMatch) { args.line = parseInt(lineMatch[1]); }
                  return JSON.stringify(args);
                }
                return fixed;
              }
            ];
            let parsed = false;
            for (let strategy of strategies) {
              try {
                args = JSON.parse(strategy());
                args.raw_arguments = tool.function.arguments;
                parsed = true;
                break;
              } catch(e3) {}
            }
            if (!parsed) { agentLog('❌ 工具参数 JSON 解析失败，跳过此步骤', '#f85149'); continue; }
          }
        }

        agentLog('🔧 ' + tool.function.name + '(' + JSON.stringify(args) + ')', '#d2991d');
        const result = await executeToolCall(tool.function.name, args, tool.function.arguments);
        agentLog('📤 ' + JSON.stringify(result).substring(0, 300), '#8b949e');
        const maxLen = tool.function.name === 'read_file' ? 2000 : 500;
        messages.push({ role: 'tool', tool_call_id: tool.id, content: JSON.stringify(result).substring(0, maxLen) });
        if (messages.length > 50) {
          const systemMsg = messages.filter(m => m.role === 'system');
          messages = [...systemMsg, ...messages.slice(-30)];
        }

        if (tool.function.name === 'write_file' || tool.function.name === 'write_large') {
          try {
            let tr = JSON.parse(JSON.stringify(result));
            if (tr.auto_fixed === false) {
              messages.push({ role: "system", content: `[系统] write_file 写入失败，网关自动修复也失败。你必须用 python3 heredoc 方式重新写入，不要再调 write_file 或 execute_command。

python3 << PYEOF
content = """..."""
with open("目标文件", "w") as f:
    f.write(content)
PYEOF` });
            }
          } catch(e) {}
        }
      }
      refreshFileTree();
    } catch (e) {
      if (e && e.name === 'AbortError') { agentLog('⏹ 已取消', '#d2991d'); break; }
      agentLog('❌ 错误: ' + e.message, '#f85149'); break;
    }
  }

  if (maxLoops === 0) {
    agentLog('⚠ 达到最大循环次数，当前进度：', '#d2991d');
    let ps = getProgressSummary(messages);
    if (ps.filesRead.length) agentLog('  📄 已读: ' + ps.filesRead.join(', '), '#8b949e');
    if (ps.filesModified.length) agentLog('  ✏ 已修改: ' + ps.filesModified.join(', '), '#8b949e');
    agentLog('  📊 已执行: ' + messages.length + '轮', '#8b949e');

    const progressData = {
      original_task: (messages.find(m => m.role === 'user') || {}).content || '未知任务',
      completed_steps: [
        ...ps.filesRead.map(f => ({action: 'read_file', file: f})),
        ...ps.filesModified.map(f => ({action: 'write_file', file: f}))
      ],
      pending_steps: ['验证测试'],
      total_rounds: messages.length
    };
    localStorage.setItem('agent_pause_' + _curThread(), JSON.stringify({ messages: messages, progress: ps.text }));

    fetch(API + '/v9/task/save_progress', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ user_id: _curUser(), session_id: _curSession(), progress: progressData })
    }).catch(() => {});

    const div = document.createElement('div');
    div.style.cssText = 'margin-top:10px;display:flex;gap:8px;';
    div.innerHTML = '<button id="btnContinue2" style="background:#238636;color:#fff;border:none;border-radius:6px;padding:8px 16px;cursor:pointer;">▶ 继续任务(25轮)</button><button id="btnCancel2" style="background:#30363d;color:#c9d1d9;border:none;border-radius:6px;padding:8px 16px;cursor:pointer;">✕ 放弃</button>';
    document.getElementById('agentTerminal').appendChild(div);

    document.getElementById('btnContinue2').onclick = function() {
      const saved = JSON.parse(localStorage.getItem('agent_pause_' + _curThread()));
      if (saved && saved.messages) {
        div.remove();
        agentLog('▶ 继续执行...', '#d2991d');
        __APP_STATE.agentRunning = true;
        document.getElementById('agentStopBtn').style.display = 'inline-block';
        continuePausedTask(saved.messages);
      }
    };
    document.getElementById('btnCancel2').onclick = function() {
      localStorage.removeItem('agent_pause_' + _curThread());
      div.remove();
      agentLog('✕ 任务已放弃', '#8b949e');
      __APP_STATE.agentRunning = false;
      document.getElementById('agentStopBtn').style.display = 'none';
    };
    return;
  }

  __APP_STATE.agentRunning = false;
  document.getElementById('agentStopBtn').style.display = 'none';
}

  // ===== window 挂载(内联 onclick / 其他模块依赖) =====
  global.agentSend = agentSend
  global.agentStop = agentStop
  global.continuePausedTask = continuePausedTask
  global.runAgentLoop = runAgentLoop
  global.readSSEStream = readSSEStream
  global.executeToolCall = executeToolCall
  global.renderProgressBar = renderProgressBar
  global.getProgressSummary = getProgressSummary
})(window)
