/**
 * 跨 session 复盘模块 — P2 goal 历史 + turn 事件展开
 *
 * 依赖:
 *   - window.DSH_API(api-client.js, goal.history) / window.__APP_STATE.userId
 *
 * 内联依赖: switchTab('goal-review') → window.loadGoalReview; nav-btn 由 workbench 导航注册。
 */
(function (global) {
  'use strict'

  var API = global.DSH_API || null

  function _esc(s) {
    var fn = global.escapeHtml || function (x) { return String(x) }
    return fn(s)
  }

  function _fmtTime(ts) {
    if (!ts) return '-'
    try { return new Date(ts * 1000).toLocaleString('zh-CN') } catch (e) { return String(ts) }
  }

  function _statusBadge(st) {
    var m = { active: ['🟢', '进行中'], complete: ['✅', '已完成'], archived: ['📦', '已归档'], paused: ['⏸', '已暂停'] }
    var b = m[st] || ['⚪', st || '未知']
    return '<span style="font-size:11px;padding:1px 8px;border-radius:10px;background:rgba(127,127,127,.15);color:' +
      (st === 'complete' ? '#3fb950' : st === 'active' ? '#3fb950' : '#8b949e') + '">' + b[0] + ' ' + _esc(b[1]) + '</span>'
  }

  function _progressBar(p) {
    p = p || {}
    var done = Number(p.done || 0)
    var total = Number(p.total || 1) || 1
    var pct = Math.max(0, Math.min(100, Math.round(done / total * 100)))
    return '<div style="height:6px;background:#30363d;border-radius:3px;overflow:hidden;margin:4px 0;">' +
      '<div style="height:100%;width:' + pct + '%;background:#1f6feb;"></div></div>' +
      '<div style="font-size:11px;color:#8b949e;">' + done + '/' + total + '（' + pct + '%）</div>'
  }

  async function loadGoalReview() {
    var box = document.getElementById('goalReviewList')
    if (!box) return
    var st = global.__APP_STATE || {}
    var userId = st.userId || (global.localStorage && global.localStorage.getItem('clawsjoy_user_id')) || 'default'
    var flt = document.getElementById('goalStatusFilter')
    var status = flt ? flt.value : ''
    box.innerHTML = '<div class="empty-hint">加载中…</div>'
    if (!API) { box.innerHTML = '<div class="empty-hint">API 客户端未加载</div>'; return }
    try {
      var res = await API.goal.history({ user_id: userId, limit: 100 })
      var d = res && res.data
      if (!res || !res.ok || !d) {
        box.innerHTML = '<div class="empty-hint">加载失败: ' + _esc((res && res.error && res.error.message) || '未知错误') + '</div>'
        return
      }
      var goals = (d.goals || []).filter(function (g) { return !status || g.status === status })
      if (!goals.length) {
        box.innerHTML = '<div class="empty-hint">暂无目标历史</div>'
        return
      }
      box.innerHTML = goals.map(function (g, i) {
        var turns = (g.turns || []).map(function (t) {
          return '<div class="tl-item" style="margin:4px 0;">' +
            '<div class="tl-icon">🔁</div>' +
            '<div class="tl-body">' +
              '<div class="tl-action">turn ' + t.turn_id + ' · ' + _esc(t.reason || '') + (t.reason_detail ? ' — ' + _esc(t.reason_detail) : '') + '</div>' +
              '<div class="tl-meta">' + _fmtTime(t.started_at) + ' · 🔧 ' + (t.tools || 0) + ' 工具 · ⚡ ' + (t.tokens || 0) + ' tokens</div>' +
            '</div></div>'
        }).join('')
        return '<div class="tl-item" style="cursor:pointer;" onclick="toggleGoalTurns(this)">' +
          '<div class="tl-icon">🎯</div>' +
          '<div class="tl-body">' +
            '<div class="tl-agent">' + _statusBadge(g.status) + ' · session ' + _esc(String(g.session_id || '').slice(-12)) + ' · goal ' + _esc(String(g.goal_id).slice(-8)) + '</div>' +
            '<div class="tl-action">' + _esc(g.objective || '') + '</div>' +
            _progressBar(g.progress) +
            '<div class="tl-meta">开始 ' + _fmtTime(g.started_at) + ' · 更新 ' + _fmtTime(g.updated_at) + '</div>' +
            '<div class="goal-turns" style="display:none;margin-top:6px;border-left:2px solid #30363d;padding-left:10px;">' +
              (turns || '<div class="empty-hint">无 turn 事件</div>') +
            '</div>' +
          '</div></div>'
      }).join('')
    } catch (e) {
      box.innerHTML = '<div class="empty-hint">加载失败: ' + _esc(e.message) + '</div>'
    }
  }

  function toggleGoalTurns(el) {
    var box = el && el.querySelector('.goal-turns')
    if (!box) return
    box.style.display = box.style.display === 'none' ? 'block' : 'none'
  }

  // ===== window 挂载(switchTab / 内联 onclick 依赖) =====
  global.loadGoalReview = loadGoalReview
  global.toggleGoalTurns = toggleGoalTurns

  // 自初始化: defer 模块挂载后等待 DOMContentLoaded(与 notifications.js 同构)
  function _init() {
    if (global.loadGoalReview) { /* 已挂载, 无需额外初始化 */ }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _init)
  } else {
    _init()
  }
})(window)
