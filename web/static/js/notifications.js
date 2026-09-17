/**
 * 通知中心模块 — 从 workbench.html 提取(拆分映射表步骤 1)
 *
 * 依赖:
 *   - window.DSH_API(api-client.js, 先于本模块加载)
 *   - bell DOM(bellBadge/bellBtn/notifPanel/notifList)
 *
 * 自初始化(defer 于 DOM 解析后): 5s 轮询 + SSE 实时推送(审计告警 #8)。
 * 内联 onclick 依赖: toggleNotifPanel/markAllRead/loadNotifList/markNotifRead → window 挂载。
 */
(function (global) {
  'use strict'

  var notifShown = false
  var notifPollTimer = null
  var notifSSE = null
  var API = global.DSH_API || null

  function bellSetBadge(count) {
    var badge = document.getElementById('bellBadge')
    if (!badge) return
    if (count > 0) { badge.textContent = count > 99 ? '99+' : count; badge.classList.add('show') }
    else { badge.textContent = '0'; badge.classList.remove('show') }
  }

  async function pollNotifications() {
    if (!API) return
    try {
      var res = await API.notification.unreadCount()
      var d = res && res.data
      if (res && res.ok && d && d.data && typeof d.data.unread_count === 'number') {
        bellSetBadge(d.data.unread_count)
      }
    } catch (e) { /* 静默失败, 下次轮询重试 */ }
  }

  async function loadNotifList() {
    var list = document.getElementById('notifList')
    if (!list) return
    list.innerHTML = '<div class="notif-empty">加载中...</div>'
    try {
      var res = await API.notification.list(50, 0)
      var d = res && res.data
      if (!res || !res.ok || !d || !d.data) { list.innerHTML = '<div class="notif-empty">加载失败</div>'; return }
      var items = d.data.items || []
      if (!items.length) { list.innerHTML = '<div class="notif-empty">暂无通知</div>'; return }
      list.innerHTML = ''
      items.forEach(function (it) {
        var row = document.createElement('div')
        row.className = 'notif-item' + (it.read ? ' read' : ' unread')
        row.innerHTML =
          '<span class="notif-dot"></span>' +
          '<div class="notif-body">' +
            '<div class="notif-msg"></div>' +
            '<div class="notif-meta">' + (it.time || new Date((it.ts || 0) * 1000).toLocaleString()) + '</div>' +
          '</div>' +
          '<span class="notif-level ' + (it.level || 'info') + '">' + (it.level || 'info') + '</span>'
        row.querySelector('.notif-msg').textContent = it.message || ''
        row.dataset.id = it.id
        if (!it.read) {
          row.addEventListener('click', function () { markNotifRead(it.id) })
        }
        list.appendChild(row)
      })
      bellSetBadge(d.data.unread_count || 0)
    } catch (e) { list.innerHTML = '<div class="notif-empty">加载失败</div>' }
  }

  function toggleNotifPanel() {
    var panel = document.getElementById('notifPanel')
    if (!panel) return
    notifShown = !notifShown
    panel.classList.toggle('open', notifShown)
    if (notifShown) loadNotifList()
  }

  function markNotifRead(id) {
    // 乐观更新: 先改 UI, 再异步通知后端
    var row = document.querySelector('#notifList .notif-item[data-id="' + id + '"]')
    if (!row || !row.classList.contains('unread')) return   // 幂等: 已读直接跳过
    row.classList.remove('unread')
    row.classList.add('read')
    var badge = document.getElementById('bellBadge')
    var cur = parseInt(badge.textContent, 10)
    if (!isNaN(cur) && cur > 0) bellSetBadge(cur - 1)
    if (!API) return
    API.notification.read({ id: id }).then(function (res) {
      if (!res || !res.ok) throw new Error('HTTP ' + (res && res.error ? res.error.code : '?'))
    }).catch(function () {
      // 失败回滚
      row.classList.remove('read')
      row.classList.add('unread')
      var cur2 = parseInt(badge.textContent, 10)
      if (!isNaN(cur2)) bellSetBadge(cur2 + 1)
    })
  }

  function markAllRead() {
    var unreadRows = Array.prototype.slice.call(document.querySelectorAll('#notifList .notif-item.unread'))
    unreadRows.forEach(function (row) {
      row.classList.remove('unread')
      row.classList.add('read')
    })
    var prevBadge = parseInt(document.getElementById('bellBadge').textContent, 10) || 0
    bellSetBadge(0)
    if (!API) return
    API.notification.readAll({}).then(function (res) {
      if (!res || !res.ok) throw new Error('HTTP ' + (res && res.error ? res.error.code : '?'))
    }).catch(function () {
      unreadRows.forEach(function (row) {
        row.classList.remove('read')
        row.classList.add('unread')
      })
      bellSetBadge(prevBadge)
    })
  }

  // 点击面板外关闭(与原内联行为一致)
  document.addEventListener('click', function (e) {
    var panel = document.getElementById('notifPanel')
    var wrap = document.querySelector('.bell-wrap')
    if (notifShown && panel && wrap && !wrap.contains(e.target)) {
      notifShown = false
      panel.classList.remove('open')
    }
  })

  // ===== window 挂载(内联 onclick 依赖) =====
  global.toggleNotifPanel = toggleNotifPanel
  global.markAllRead = markAllRead
  global.loadNotifList = loadNotifList
  global.markNotifRead = markNotifRead
  global.pollNotifications = pollNotifications
  global.bellSetBadge = bellSetBadge

  // ===== 自初始化 =====
  function init() {
    if (!API) return
    pollNotifications()
    notifPollTimer = setInterval(pollNotifications, 5000)
    try {
      if (global.EventSource) {
        var base = (global.CLAWSJOY_API_BASE || (global.localStorage && global.localStorage.getItem('clawsjoy_api_base')) || '')
        notifSSE = new EventSource(base + '/v8/notifications/stream')
        notifSSE.onmessage = function (ev) {
          try {
            var n = JSON.parse(ev.data)
            if (n && n.id) {
              pollNotifications()           // 新通知 → 刷新红色 badge
              if (notifShown) loadNotifList() // 面板开着则实时刷新列表
            }
          } catch (e) {}
        }
        notifSSE.onerror = function () { /* 断开自动重连; 轮询 5s 兜底 */ }
      }
    } catch (e) {}
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init)
  } else {
    init()
  }
})(window)
