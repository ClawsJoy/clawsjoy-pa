# V9 跨沙箱线程隔离排查报告

> 状态: 排查完成 — 已定位根因(前端会话脱钩), 附修复方案

## 1. 结论

**不存在后端跨沙箱线程文件访问。** 根因在前端: chat.js 模块级 sessionId/currentThread 是加载时快照, 线程切换后不更新 → 请求发到旧线程(3379)的 session, 恢复旧线程历史。

## 2. 沙箱路径锚定(检查项 1) — OK 正常

- _get_sandbox_base(user_id, session_id) (gateway_helpers.py L449) → data/projects/{uid}/{sid}/clawsjoy_dev, 全部工具共用
- 实测 live data/session_logs/: session_1783388196051.jsonl(6051) 与 session_1783593903379.jsonl(3379) 两个独立文件, 内容互不污染
- 后端所有路径(任务快照/会话日志/goal/memory)均以 {uid}/{sid} 为前缀, 无硬编码/相对路径逃逸

## 3. 会话记忆恢复(检查项 2) — 前端脱钩

「已恢复上次对话上下文」来源: localStorage['agent_history_' + currentThread] (chat.js L143)

### 根因链路
```
1. chat.js 模块顶部(加载时): var sessionId = __APP_STATE.sessionId  ← 快照
                              var currentThread = __APP_STATE.currentThread  ← 快照
2. 用户切线程: switchThread()/newThread() 更新 __APP_STATE + localStorage,
   但 chat.js 的模块局部 sessionId/currentThread 不变
3. agentSend() 读模块局部 currentThread → agent_history_3379(旧线程历史)
4. runAgentLoop() 用模块局部 sessionId → POST /v9/agent/chat 带 session_id=3379
5. 后端在 3379 沙箱执行 → 回复 3379 内容 → 前端显示 3379 回复
```

## 4. 跨线程文件访问(检查项 3) — 无泄漏

- 工具调用(read_file/list_dir)经 _resolve_path(base, path) 锚定 sandbox_base
- _resolve_project_root_read 只读回退有白名单(项目根内 + 无 .git)
- EscapeGuard 阻止绝对路径/系统路径逃逸(已有测试覆盖)
- 吸收 Harness 未破坏沙箱机制(路径推导仍基于 {uid}/{sid})

## 5. 修复方案

chat.js 所有发请求/读历史处改为运行时读取 __APP_STATE/localStorage, 不用模块快照:

```js
// chat.js: 新增运行时读取助手(替代模块顶部快照)
function _curSession() {
  return (__APP_STATE && __APP_STATE.sessionId) || (global.localStorage && global.localStorage.getItem('clawsjoy_session_id')) || ''
}
function _curThread() {
  return (__APP_STATE && __APP_STATE.currentThread) || (global.localStorage && global.localStorage.getItem('current_thread')) || ''
}
// 替换:
//   sessionId      → _curSession()   (L93/111/181/... 所有请求体)
//   currentThread  → _curThread()    (L132/143/210/322/... 所有 localStorage 键)
```

或在 switchThread/newThread 里回写 chat.js 变量(若挂到 window)。推荐前者(无全局状态)。

## 6. 复现验证建议

1. 浏览器开 2 个线程(3379 / 6051), 各发一个不同任务
2. 切到 6051 发新任务 → 修复前会恢复/回复 3379 内容
3. 修复后: 请求体 session_id 应为 6051, 历史键 agent_history_session_...6051

## 7. 待办

- [ ] chat.js 模块快照 → 运行时读取(修复核心)
- [ ] 回归: 线程切换后请求/历史/文件树均指向新线程
