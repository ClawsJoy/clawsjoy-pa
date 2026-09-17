/**
 * ClawsJoy V9 API 客户端层
 *
 * 封装 workbench.html 的 32 个裸 fetch 端点（V5/V8/V9 混合）：
 * - 统一错误处理: 返回 { ok, data, error: { code, message } }
 * - SSE 流式单独封装(保持流式特性)
 * - 分类 API(chat/sandbox/roster/ledger/task/discussion/notification/other)
 *
 * 用途: 为后续状态 store 化 + 模块拆分打基础; workbench.html 逐步引用。
 * 加载方式: UMD 风格(挂 window.DSH_API + 支持 ES module)
 */
(function (global) {
  'use strict'

  // ===== baseURL 双模式配置(每次请求解析, 支持运行时切换) =====
  // 解析优先级: window.CLAWSJOY_API_BASE > localStorage('clawsjoy_api_base') > 默认(当前域相对路径)
  // 默认: 本地 workbench 同域(''); 云端: https://clawsjoy.com/api
  const _ls = (typeof localStorage !== 'undefined') ? localStorage : null
  function _resolveBase() {
    return (
      (typeof global !== 'undefined' && global.CLAWSJOY_API_BASE)
      || (_ls && _ls.getItem('clawsjoy_api_base'))
      || ''
    )
  }

  // ===== 鉴权头预留(自动附加, 从 localStorage 读取) =====
  // - session: X-Session-Id(会话上下文)
  // - token:   Authorization: Bearer <token>(云端模式必需; 本地可空)
  const AUTH_STORAGE_KEYS = {
    token: 'clawsjoy_token',
    session: 'clawsjoy_session_id',
    userId: 'clawsjoy_user_id',
  }
  function _authHeaders() {
    if (!_ls) return {}
    const headers = {}
    const token = _ls.getItem(AUTH_STORAGE_KEYS.token)
    const session = _ls.getItem(AUTH_STORAGE_KEYS.session)
    const userId = _ls.getItem(AUTH_STORAGE_KEYS.userId)
    if (token) headers['Authorization'] = 'Bearer ' + token
    if (session) headers['X-Session-Id'] = session
    if (userId) headers['X-User-Id'] = userId
    return headers
  }

  // ===== 核心 request: 统一错误处理 =====

  /**
   * 统一请求封装
   * @param {string} path - 端点路径(如 '/v9/sandbox/read')
   * @param {object} [opts] - { method, body, params }
   * @returns {Promise<{ok:boolean, data:any, error:{code:string,message:string}|null}>}
   */
  async function request(path, opts = {}) {
    const { method = 'GET', body, params } = opts
    let url = _resolveBase() + path
    if (params) {
      const qs = new URLSearchParams(
        Object.entries(params).filter(([, v]) => v !== undefined && v !== null)
      ).toString()
      if (qs) url += (url.includes('?') ? '&' : '?') + qs
    }
    try {
      const resp = await fetch(url, {
        method,
        headers: {
          ..._authHeaders(),
          ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        },
        body: body !== undefined ? JSON.stringify(body) : undefined,
      })
      if (!resp.ok) {
        return { ok: false, data: null, error: { code: 'HTTP_' + resp.status, message: resp.statusText || ('HTTP ' + resp.status) } }
      }
      let data
      const ct = resp.headers.get('content-type') || ''
      if (ct.includes('application/json')) {
        data = await resp.json()
      } else {
        data = await resp.text()
      }
      // 业务层失败(网关统一返回 {success:false, error})
      if (data && typeof data === 'object' && data.success === false) {
        return { ok: false, data, error: { code: data.error_code || 'API_ERROR', message: data.error || data.message || 'API 错误' } }
      }
      return { ok: true, data, error: null }
    } catch (e) {
      return { ok: false, data: null, error: { code: 'NETWORK', message: e && e.message ? e.message : String(e) } }
    }
  }

  // ===== SSE 流式请求(保持流式特性, 不吞事件) =====
  /**
   * SSE 流式请求: fetch + getReader 逐行解析 data: 事件
   * @param {string} path - 端点路径
   * @param {object} body - POST body
   * @param {object} handlers - { onEvent(evt), onDone(payload), onError(err) }
   * @returns {Promise<object>} 最终 payload(done 事件或 {success:false,error})
   */
  async function streamRequest(path, body, handlers = {}) {
    const { onEvent, onDone, onError } = handlers
    try {
      const resp = await fetch(_resolveBase() + path, {
        method: 'POST',
        headers: { ..._authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const ct = resp.headers.get('content-type') || ''
      if (!ct.includes('text/event-stream')) {
        // 非 SSE 响应(降级): 按 JSON 处理
        const data = await resp.json()
        if (data && data.success === false) {
          if (onError) onError({ code: 'API_ERROR', message: data.error || 'API 错误' })
          return data
        }
        if (onDone) onDone(data)
        return data
      }
      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buf = ''
      let donePayload = { success: true }
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        let idx
        while ((idx = buf.indexOf('\n')) >= 0) {
          const line = buf.slice(0, idx).trim()
          buf = buf.slice(idx + 1)
          if (!line.startsWith('data: ')) continue
          const payload = line.slice(6)
          if (payload === '[DONE]') {
            if (onDone) onDone(donePayload)
            return donePayload
          }
          let evt
          try { evt = JSON.parse(payload) } catch (e) { continue }
          if (evt.type === 'done') {
            donePayload = evt
            if (onDone) onDone(evt)
            return evt
          }
          if (onEvent) onEvent(evt) // start/progress/error 等中间事件
        }
      }
      if (onDone) onDone(donePayload)
      return donePayload
    } catch (e) {
      const err = { code: 'NETWORK', message: e && e.message ? e.message : String(e) }
      if (onError) onError(err)
      return { success: false, error: err.message }
    }
  }

  // ===== 分类 API =====

  // chat 类(2): /v5/execute + /api/v5/chat/stream(SSE)
  const chatApi = {
    /** V5 统一执行入口 */
    execute: (data) => request('/v5/execute', { method: 'POST', body: data }),
    /** V5 频道 SSE 流式 */
    stream: (data, handlers) => streamRequest('/api/v5/chat/stream', data, handlers),
  }

  // sandbox 类: /v9/sandbox/* + /v9/agent/chat
  const sandboxApi = {
    /** V9 Agent 桥接(流式/非流式由 stream 字段控制) */
    agentChat: (data) => request('/v9/agent/chat', { method: 'POST', body: data }),
    /** V9 Agent 桥接 SSE 流式 */
    agentChatStream: (data, handlers) => streamRequest('/v9/agent/chat', data, handlers),
    list: (data) => request('/v9/sandbox/list', { method: 'POST', body: data }),
    read: (data) => request('/v9/sandbox/read', { method: 'POST', body: data }),
    write: (data) => request('/v9/sandbox/write', { method: 'POST', body: data }),
    writeLarge: (data) => request('/v9/sandbox/write_large', { method: 'POST', body: data }),
    edit: (data) => request('/v9/sandbox/edit', { method: 'POST', body: data }),
    exec: (data) => request('/v9/sandbox/exec', { method: 'POST', body: data }),
    search: (data) => request('/v9/sandbox/search', { method: 'POST', body: data }),
    queryIndex: (data) => request('/v9/sandbox/query_index', { method: 'POST', body: data }),
    checkpoint: (data) => request('/v9/sandbox/checkpoint', { method: 'POST', body: data }),
    rollback: (data) => request('/v9/sandbox/rollback', { method: 'POST', body: data }),
  }

  // roster 类(5): /v8/roster/*
  const rosterApi = {
    list: (serverId = 'default') => request('/v8/roster/list', { params: { server_id: serverId } }),
    hire: (data) => request('/v8/roster/hire', { method: 'POST', body: data }),
    fire: (data) => request('/v8/roster/fire', { method: 'POST', body: data }),
    update: (data) => request('/v8/roster/update', { method: 'POST', body: data }),
    /** 暂停/恢复(动态端点) */
    setPaused: (data, paused) => request('/v8/roster/' + (paused ? 'pause' : 'resume'), { method: 'POST', body: data }),
  }

  // ledger 类(2): /v8/ledger/*
  const ledgerApi = {
    billing: (serverId = 'default') => request('/v8/ledger/billing', { params: { server_id: serverId } }),
    timeline: (serverId = 'default', limit = 30) => request('/v8/ledger/timeline', { params: { server_id: serverId, limit } }),
  }

  // task 类(4): /v8/task/* + /v9/task/* + /v9/subtask/*
  const taskApi = {
    list: (serverId = 'default', createdBy = '') => request('/v8/task/list', { params: { server_id: serverId, created_by: createdBy } }),
    /** V9 任务详情(动态 id) */
    get: (taskId, params) => request('/v9/task/' + taskId, { params }),
    saveProgress: (data) => request('/v9/task/save_progress', { method: 'POST', body: data }),
    /** 子任务创建(有界并发池) */
    subtaskCreate: (data) => request('/v9/subtask/create', { method: 'POST', body: data }),
    /** 子任务状态查询(GET) */
    subtaskStatus: (params) => request('/v9/subtask/status', { params }),
  }

  // discussion 类(3): /v8/discussions/*
  const discussionApi = {
    get: (id) => request('/v8/discussions/get', { params: { id } }),
    list: () => request('/v8/discussions/list'),
    save: (data) => request('/v8/discussions/save', { method: 'POST', body: data }),
  }

  // notification 类(4): /v8/notifications/*
  const notificationApi = {
    list: (limit = 50, offset = 0) => request('/v8/notifications', { params: { limit, offset } }),
    read: (data) => request('/v8/notifications/read', { method: 'POST', body: data }),
    readAll: (data) => request('/v8/notifications/read-all', { method: 'POST', body: data }),
    unreadCount: () => request('/v8/notifications/unread-count'),
  }

  // goal 类(1): P2 跨 session 复盘 — /v9/goal/history
  const goalApi = {
    /** 跨 session goal 历史(含 progress/status/时间 + 最近 turn 摘要) */
    history: (params) => request('/v9/goal/history', { params }),
  }

  // 其他(7): models/positions/balance/auto_fixes/session_clean
  const otherApi = {
    models: () => request('/v8/models/list'),
    positions: () => request('/v8/positions/list'),
    balance: () => request('/v9/balance'),
    autoFixes: () => request('/v9/auto_fixes'),
    autoFixApprove: (data) => request('/v9/auto_fixes/approve', { method: 'POST', body: data }),
    autoFixReject: (data) => request('/v9/auto_fixes/reject', { method: 'POST', body: data }),
    /** 会话清理(/clean 后端路由) */
    sessionClean: (data) => request('/v9/session/clean', { method: 'POST', body: data }),
  }

  // ===== 导出 =====
  const DSH_API = {
    request,
    streamRequest,
    chat: chatApi,
    sandbox: sandboxApi,
    roster: rosterApi,
    ledger: ledgerApi,
    task: taskApi,
    discussion: discussionApi,
    notification: notificationApi,
    goal: goalApi,
    other: otherApi,
  }

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = DSH_API
  }
  global.DSH_API = DSH_API
})(typeof window !== 'undefined' ? window : globalThis)
