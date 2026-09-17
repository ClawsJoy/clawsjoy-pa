/**
 * 时间线 + LLM 回放模块 — 从 workbench.html 提取(拆分映射表步骤 2)
 *
 * 依赖:
 *   - window.DSH_API(api-client.js) / window.__APP_STATE.sessionId(回放默认会话)
 *   - window.escapeHtml(内联定义, 模块 defer 后可用)
 *
 * 内联 onclick 依赖: loadReplay(回放按钮) → window 挂载; loadTimeline 由 switchTab 调用。
 */
(function (global) {
  'use strict'

  var API = global.DSH_API || null

  function _esc(s) {
    var fn = global.escapeHtml || function (x) { return String(x) }
    return fn(s)
  }

  async function loadTimeline() {
    if (!API) return
    try {
      var res = await API.ledger.timeline('default', 30)
      var events = res && res.data
      if (!res || !res.ok || !events || !events.length) {
        document.getElementById('timelineContent').innerHTML = '<div class="empty-hint">暂无事件</div>'
        return
      }
      document.getElementById('timelineContent').innerHTML = events.map(function (e) {
        var icon = (e.action || '').indexOf('bug') >= 0 ? '🐛' : (e.action || '').indexOf('代码') >= 0 ? '💻' : (e.action || '').indexOf('图') >= 0 ? '🎨' : '📋'
        return '<div class="tl-item">' +
          '<div class="tl-icon">' + icon + '</div>' +
          '<div class="tl-body">' +
            '<div class="tl-agent">' + (e.position === '程序员' ? '👨‍💻' : e.position === '设计师' ? '👩‍🎨' : '📊') + ' ' + (e.agent || e.agent_name || '') + ' · ' + (e.position || '') + '</div>' +
            '<div class="tl-action">' + (e.summary || e.reason || '') + '</div>' +
            '<div class="tl-meta">' + new Date(e.timestamp).toLocaleString('zh-CN') + ' · <span class="tl-status ' + e.status + '">' + ((e.status || 'completed') === 'completed' ? '完成' : e.status) + '</span> · $' + (e.cost || 0).toFixed(4) + '</div>' +
          '</div>' +
        '</div>'
      }).join('')
    } catch (e) {
      document.getElementById('timelineContent').innerHTML = '<div class="empty-hint">加载失败: ' + e.message + '</div>'
    }
  }

  async function loadReplay() {
    var st = global.__APP_STATE || {}
    var sessionId = st.sessionId || ''
    var inp = document.getElementById('replaySessionInput')
    if (inp && !inp.value.trim()) inp.value = sessionId
    var sid = (inp ? inp.value : sessionId).trim()
    var box = document.getElementById('replayContent')
    if (!box) return
    box.innerHTML = '<div class="empty-hint">▶ 回放中: ' + _esc(sid) + ' …</div>'
    if (!API) { box.innerHTML = '<div class="empty-hint">API 客户端未加载</div>'; return }
    try {
      var res = await API.request('/v9/replay/' + encodeURIComponent(sid), { params: { verify: '1' } })
      var d = res && res.data
      if (!res || !res.ok || !d || d.error) {
        box.innerHTML = '<div class="empty-hint">回放失败: ' + _esc((d && d.error) || (res && res.error ? res.error.code : '?')) + '</div>'
        return
      }
      var v = d.verify || {}
      var vBadge = v.ok ? '<span style="color:#3fb950">✅ 校验通过</span>'
        : '<span style="color:#f85149">❌ 校验失败: ' + _esc(Object.keys(v.checks || {}).filter(function (k) { return !v.checks[k] }).join(',')) + '</span>'
      var head = '<div style="font-size:12px;color:var(--sub);padding:8px 10px;border-bottom:1px solid var(--line,#333);">' +
        'session=' + _esc(d.session_id) + ' · ' + d.count + ' 条消息 · ' + (d.events || 0) + ' 事件 · ' + vBadge +
        (d.at_turn != null ? ' · at_turn=' + d.at_turn : '') + '</div>'
      var msgs = (d.messages || []).map(function (m, i) {
        var role = m.role === 'user' ? '👤 user' : m.role === 'assistant' ? '🤖 assistant' : '🔧 tool'
        var tcs = m.tool_calls ? ' [' + m.tool_calls.map(function (t) { return (t.function || {}).name || '' }).filter(Boolean).join(', ') + ']' : ''
        var c = String(m.content || '')
        var body = c.length > 300 ? c.slice(0, 300) + '…' : c
        var meta = m.role === 'tool' ? ' · ' + _esc(String(m.tool_call_id || '').slice(0, 8)) : ''
        return '<div class="tl-item"><div class="tl-icon">' + role[0] + '</div><div class="tl-body">' +
          '<div class="tl-agent">#' + i + ' · ' + role + _esc(tcs + meta) + '</div>' +
          '<div class="tl-action" style="white-space:pre-wrap;font-size:12px;word-break:break-all;">' + _esc(body) + '</div></div>'
      }).join('')
      box.innerHTML = head + (msgs || '<div class="empty-hint">暂无消息</div>')
    } catch (e) {
      box.innerHTML = '<div class="empty-hint">回放失败: ' + _esc(e.message) + '</div>'
    }
  }

  // ===== window 挂载(内联 onclick / switchTab 依赖) =====
  global.loadTimeline = loadTimeline
  global.loadReplay = loadReplay
})(window)
