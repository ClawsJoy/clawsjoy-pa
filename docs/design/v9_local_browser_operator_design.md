> **已归档（批198 / 2026-09-16）：本文描述的「浏览器扩展 + 专属标签页」开启方式已被取代。**
>
> **现行做法**：唯一浏览器出口 = `core/tools/browser_runtime.py`（launch / 会话 / CDP 都在这里）；
> 本地浏览器由 **PA 页「🚀 启动本地浏览器」** 一键启动桌面 `agent_client`（命令硬编码，见 `core/pa/gateway_routes.py`）。
> 旧方式（扩展 + `chrome.tabs.create` + 注入桥）**只作历史参考**，照做会失败（全仓 `chrome.runtime.sendMessage` **0 命中**、无扩展目录）。
> 取代记录：金库 `归档/浏览器开启方式_旧_20260916.md`；陈旧引用扫描：`tools/knowledge_staleness_check.py`（批198）。
# V9 本地浏览器操作能力设计（对齐 Manus 插件核心架构）

> 状态: 设计调研完成 — 输出完整方案, 待确认后实施
> 目标: 让 V9 Agent 操作用户真实本地浏览器(复用登录态/Cookies/IP), 突破沙箱 headless 被登录墙/风控拦截的瓶颈

## 1. 问题与现状

| 现状 | 问题 |
|---|---|
| playwright_browser 在沙箱 headless Chromium 执行 | 小红书/抖音等平台登录墙 + IP 风控拦截, 无法调研真实内容 |
| 每次调用独立 launch(headless=True) | 无持久登录态/Cookies, 每次都是新访客 |
| 仅 open/content/click/fill/screenshot 5 个 action | 无法多步交互/滚动/发布 |

## 2. 技术选型（3 条候选路径对比）

| 方案 | 原理 | 优点 | 缺点 |
|---|---|---|---|
| A: chrome.debugger API (MV3) | 扩展用 chrome.debugger.attach 到自身标签页, 获 CDP 访问 | 无本地端口/无权限弹窗, 天然复用用户会话 | MV3 中 debugger 权限受限(需要用户手势, 不能 attach 其他扩展页) |
| B: 本地 WebSocket 桥接 (推荐) | 扩展后台 service worker 作为 WS 客户端连 V9 后端, V9 发 CDP 指令 | 架构清晰, V9 侧可做审批/审计/日志; 复用现有 SSE/通知基建 | 需用户开启时建立连接; 需处理 MV3 SW 生命周期 |
| C: Native Messaging (host 程序) | 扩展 ↔ 本地 Python/Node host 程序, host 起 CDP 服务 | 最强大(全 CDP), 可做系统级操作 | 需安装 host 程序, 分发复杂, 跨平台打包难 |

**选型: B(本地 WS 桥接) + A 的授权思路(用户手势开标签页)。** 理由: 对齐 Manus 插件(扩展持 WS 连后端), 无需安装本地程序, 复用 V9 已有 WS/SSE 基建, 且 V9 侧集中做授权/审计/安全。

### 2.1 双通道浏览器架构

```
┌─────────────┐        ┌──────────────────────┐        ┌─────────────────┐
│  V9 后端     │  WS    │  Chrome Extension      │  CDP  │  用户本地浏览器    │
│ (Flask)     │◄──────►│  (service worker)      │──────►│  (真实登录态/IP)  │
│  /v9/browser │        │  本地桥接器             │       │  小红书/抖音等     │
│  指令队列    │        └──────────────────────┘        └─────────────────┘
│  授权/审计    │
│  审批队列    │
└─────────────┘

┌────────────────────┐        ┌─────────────────────┐
│ 沙箱 headless 浏览器  │        │ 本地浏览器(新增)       │
│ (现有 playwright)    │        │ (browser_local_*)    │
│ 公开网页/无登录内容    │        │ 登录平台/需身份内容      │
└────────────────────┘        └─────────────────────┘
```

## 3. 架构设计

### 3.1 连接模型（插件作为 WS 客户端, V9 作为服务端）

- **V9 后端**: 新增 `/v9/browser/ws` WebSocket 端点(复用 flask-sock 或 gevent-websocket), 维护 `{user_id: [browser_conn]}` 连接表
- **扩展 service worker**: 页面加载时连 WS; 收到指令 → chrome.debugger.attach(自身标签) → CDP 执行 → 回传结果
- **心跳**: 30s ping/pong; 断线自动重连(指数退避)
- **MV3 生命周期**: SW 被回收时 WS 断开, 用 `chrome.alarms` 保活 + 用户开专属标签页时必然活着(见 §5)

### 3.2 指令协议（JSON over WS）

```json
// V9 → 扩展
{ "type": "exec", "cmd_id": "b1", "action": "navigate", "params": {"url": "https://www.xiaohongshu.com/..."} }

// 扩展 → V9
{ "type": "result", "cmd_id": "b1", "ok": true, "data": {"title": "...", "url": "..."} }
{ "type": "error", "cmd_id": "b1", "message": "登录态失效" }
{ "type": "state", "state": "connected|idle|busy", "url": "当前页" }
```

### 3.3 工具定义（新 ToolPlugin: browser_local）

| 工具 | action | 参数 | 说明 | 阶段 |
|---|---|---|---|---|
| browser_local_navigate | navigate | url | 打开 URL(用户可见标签页) | P1 |
| browser_local_extract | extract | selector? | 提取页面正文/指定元素 | P1 |
| browser_local_screenshot | screenshot | full_page? | 截图(回传缩略图) | P1 |
| browser_local_scroll | scroll | direction, amount | 滚动加载(抖音/小红书信息流) | P1 |
| browser_local_click | click | selector | 点击元素 | P2 |
| browser_local_fill | fill | selector, text | 填表 | P2 |
| browser_local_search | search | query, engine? | 平台内搜索 | P2 |
| browser_local_publish | publish | content, media? | 发布(需审批, P3) | P3 |
| browser_local_monitor | monitor | url, interval | 定时监控(后台轮询) | P4 |

注册: `core/tools/browser_local.py`(ToolPlugin 形态, 接入 _TOOL_REGISTRY, 与 playwright_browser 并列)。

## 4. 用户体验

### 4.1 专属标签页(Agent 工作区)
- 首次使用: 用户点击「连接本地浏览器」→ 扩展弹窗选择「开启 Agent 专属标签页」(chrome.tabs.create + 自动注入桥接)
- 该标签页 URL 栏显示 Agent 状态徽标(🟢 工作中 / 🔴 停止), 用户随时可见 Agent 正在访问的页面
- **关闭标签页 = 立即停止**: 扩展监听 tabs.onRemoved → 通知 V9 该连接失效 → Agent 工具调用返回「用户已停止」

### 4.2 实时监控
- 扩展每完成一个指令 → WS 回传 state + 当前 URL → V9 通过现有 SSE/notifications 推送前端
- Agent 终端实时显示「🖥️ 本地浏览器: 正在访问 xiaohongshu.com/note/xxx」

### 4.3 授权流程
- 首次: 弹窗说明权限范围(可浏览/可提取文本/可截图, 不可填密码/支付) → 用户点「授权」
- 授权存 chrome.storage.local: {enabled, scopes, whitelist, revoked_at}
- 撤销: 扩展弹窗一键撤销 → V9 连接失效, 所有 browser_local 工具拒绝

## 5. 安全模型

### 5.1 操作分级

| 级别 | 操作 | 策略 |
|---|---|---|
| 自动 | navigate / extract / screenshot / scroll | 直接执行(域名需在可访问集) |
| 需确认 | click / fill / search / publish | V9 审批队列(复用现有 write_pending/plan_pending 卡片机制) |
| 禁止 | 输入密码 / 支付 / 提交敏感表单 / 下载文件 | 扩展侧硬拒绝(不实现) + V9 守卫拦截 |

### 5.2 域名白名单/黑名单
- 白名单(默认): 用户授权时选的平台域(如 xiaohongshu.com, douyin.com, bilibili.com...)
- 黑名单(硬): 银行/支付/邮箱/云盘类域(config/v9/browser_policy.yaml)
- 守卫: 新增 BrowserLocalGuard(pre-guard) — navigate 前检查 url host ∈ 白名单 ∧ ∉ 黑名单

### 5.3 敏感操作硬禁止
- 扩展侧: 不实现 password/fill(password)/支付点击 API
- V9 侧: fill 的 text 含密码/卡号等关键词 → 拦截; publish 必走审批

## 6. 与现有能力复用

| 现有组件 | 复用点 |
|---|---|
| ToolPlugin + _TOOL_REGISTRY | browser_local 以插件形态接入, 与 playwright_browser 并列 |
| 审批卡片(write_pending/plan_pending) | click/fill/publish 复用确认流程 |
| SSE/notifications | 实时状态推送前端 |
| SessionLog | browser 操作事件审计(浏览器_操作/结果) |
| execution_policy.yaml | browser_local 配额/超时/白名单配置 |
| core/lib/collaboration_ws.py | WS 连接管理骨架(需扩展为双向指令) |

## 7. 分阶段实施路线图

| 阶段 | 范围 | 交付物 | 验收 |
|---|---|---|---|
| P1 | 只读调研 | 扩展骨架 + WS 连接 + navigate/extract/screenshot/scroll + 专属标签页 + 域名白名单 | 小红书/抖音能提取公开内容, 用户可见标签页 |
| P2 | 交互 | click/fill/search + 审批卡片 + 实时状态推送 | 能搜索/滚动/填搜索框 |
| P3 | 发布 | publish + 敏感操作审批 + 发布审计 | 能发笔记/视频(用户逐次确认) |
| P4 | 自动化运营 | monitor + 定时任务 + 回复队列 | 定时监控/自动回复(用户授权范围内) |

## 8. 关键风险与缓解

| 风险 | 缓解 |
|---|---|
| MV3 service worker 生命周期 | 专属标签页常开 + chrome.alarms 保活; SW 回收时 WS 重连 |
| chrome.debugger 需要用户手势 | attach 在用户点击「连接」时发起(满足 MV3 手势要求) |
| 登录态泄漏 | 扩展本地 chrome.debugger 不转发 Cookies 给 V9; V9 只收 DOM/截图 |
| 风控(平台检测自动化) | 模拟真人节奏(随机延迟/滚动速度); 用户可限速 |
| 发布误操作 | P3 强制逐次审批 + 发布前截图确认 |

## 9. 待确认问题

1. 扩展分发: 内部加载(unpacked) vs Chrome Web Store? (P1 先 unpacked)
2. WS 端点: 复用现有 Flask 端口 vs 独立端口? (建议同端口 /browser/ws)
3. 目标平台优先顺序: 小红书 → 抖音 → B站 → 知乎?
4. P1 是否包含「已登录平台切换账号」支持?

## 10. 下一步(确认后)

1. 扩展骨架(exam-prep-extension 同仓库 or 新目录 web/browser-extension/)
2. V9 后端 /v9/browser/ws + BrowserLocalGuard + browser_policy.yaml
3. core/tools/browser_local.py + 审批接入
4. P1 端到端: 小红书浏览 + 提取 + 截图

## 11. WS 传输实现注记(2026-08-23 排障实录)

### 11.1 传输方式: websockets.sync(同步 serve)

- 网关内 WS 服务用 websockets.sync.server.serve + serve_forever() 起独立 daemon 线程
  (core/lib/v8/browser_local.start_browser_ws), 与 Flask app.run(threaded=True) 兼容。
- 原 asyncio.run(_serve()) 在 Flask threading 线程中 event loop 不处理连接 → 握手即断, 已弃用。
- 已实测: 同步 serve 在真实网关(nohup 后台 + Flask threaded)中 accept/握手/收发全部正常。

### 11.2 端口冲突根因(5004 → 5006)

- 症状: 扩展 WS 握手失败(connection closed during handshake / Empty reply)。
- 排查过程: 网关 sync serve 起在 0.0.0.0:5004 且日志显示 connection open(101 已发出),
  但客户端收不到响应; 192.168.3.11:5004 从 WSL2 握手成功, 127.0.0.1:5004 失败。
- 根因: Windows 侧 svchost(服务宿主)占用 0.0.0.0:5004, 抢占 WSL2 localhost 转发,
  Windows Chrome 的 localhost:5004 与共享 IP 192.168.3.11:5004 均落到该 svchost(Empty reply)。
- 修复: V9 WS 端口改为 5006(Windows 侧空闲)。实测 Windows localhost:5006 → 101 握手成功。
- 结论: 本环境(WSL2 localhost 转发)下扩展用 ws://localhost:5006 即可; 勿用 192.168.3.11
  (共享 IP 场景 Windows 到 WSL2 不通, 会超时)。

### 11.3 测试同步化

- 同步重写后, 测试 FakeConn.send 由 async def 改为同步 def(p1/p2/p3/p4 共 8 处)。

### 11.4 连接 user_id 归一化(web_xxx vs user-mtxxx)

- 症状: 扩展连接注册 user=web_xxx, Agent 调 browser_local 用 user_id=user-mtxxx,
  is_connected 精确匹配失败 → 返回「未连接」/ ConnectionReset。
- 修复(方案 C, 单机版): 新增 _resolve_conn_user(user_id) — 精确匹配优先, 否则任意
  现存连接兜底(仅 1 个连接时); execute/审批(pending_browser_op/approve_browser_op)/
  _send/is_connected/connection_state 全部经其归一化; 审计/发布历史仍按 Agent 原始 user_id。
- 覆盖: tests/unit/test_browser_local_p5.py(4 例: 连接视角/执行流/无连接/审批流)。

### 11.5 tool_router 分发修复(browser_local 分支)

- 症状: Agent 调 browser_local → AttributeError: 'NoneType' object has no attribute 'get'。
- 根因: core/gateway/tool_router._execute_sandbox_tool 网络工具分支只含
  fetch_web/browse_web/playwright_browser, browser_local 不匹配任何分支 → 返回 None →
  调用方 result.get() 崩 NoneType。
- 修复: 网络工具分支加入 browser_local(fetch_web/browse_web/playwright_browser/browser_local),
  ctx 正确携带 user_id/session_id → BrowserLocalPlugin 正常收发。
- 覆盖: tests/unit/test_browser_local_p5.py(分发 ctx 传参 + 未知工具仍报错)。

### 11.6 CDP Page 域修复(Page.getTitle 已被协议移除)

- 症状: 扩展 navigate 报 {'code':-32601, 'message':"'Page.getTitle' wasn't found"},
  Page.enable 后仍复现(08:31 live 实测)。
- 根因: 现代 Chrome/Chromium 的 CDP 协议已移除 Page.getTitle(Chromium-1234 协议域实测
  方法列表无 getTitle, 协议文档标记 Deprecated)。Page.enable 只解决域未启用问题,
  对已移除的方法无效。
- 修复:
  1) execCdp attach 后统一 Page.enable(Page.navigate/captureScreenshot 需要);
  2) 标题获取改用 Runtime.evaluate {expression: 'document.title', returnByValue: true}。
- 覆盖: tests/unit/test_browser_local_p3.py::test_extension_cdp_page_enable
  (断言 Page.enable 顺序 + 不再调用 Page.getTitle + 使用 document.title)。

### 11.7 扩展授权 scope 补全(click/fill/search)

- 症状: Agent 调 click/fill/search 报 scope_denied(P2 交互已实现但授权 scopes 未含)。
- 修复: popup 连接时基础 scopes 合并 navigate/extract/screenshot/scroll/click/fill/search,
  background.js getAuth 默认 scopes 同步; publish 仍单独授权(不进基础集)。
- 兼容: 旧安装已存 auth(老 scopes)点「连接」即自动补齐, 无需手动撤销重授权。
- 覆盖: tests/unit/test_browser_local_p3.py::test_extension_scopes_include_interactions。

### 11.8 browser_local 递归检测 <no-path> 误伤修复

- 症状: 不同 URL/selector 的 browser_local 操作被当成同一路径重复, 数次即被递归检测拦下。
- 根因: core/gateway/path_utils._extract_tool_path 对 browser_local 仅通用 url 检查,
  extract/click/fill/scroll 无 url 时全部落 "<no-path>" 互相碰撞; 且 exec 路径
  check_recursion 阈值硬编码 3(配置 auto_pause_threshold=5 未生效)。
- 修复:
  1) _extract_tool_path 按 action 处理 — navigate/search 用 url; extract/scroll/click/fill
     无 url 时用 selector(前缀 browser_local:), 再无则用动作名, 杜绝 <no-path>;
  2) execute_agent_task.check_recursion 读 execution_policy.yaml 阈值(默认 5), 与 bridge 一致。
- 覆盖: tests/unit/test_recursion_precision.py(不同 URL/selector 不误伤、同 key ×5 pause、
  无 <no-path>); test_guard_s5_stateful.py 阈值 3→5 同步。

### 11.9 extract 空修复(CDP 逐 frame 求值)

- 症状: 扩展 extract 返回空, 但浏览器 Console 有内容 — 内容可能在 iframe,
  默认执行上下文(主 frame)求值取不到。
- 修复: background.js 新增 extractPageText — 主 frame 默认上下文先试; 空则
  Runtime.enable 收 executionContextCreated 事件维护 frameId→contextId 映射,
  Page.getFrameTree 取 frame 树, 逐 frame 带 contextId 求值, 取有内容的 frame。
- 实测(Chromium): 主 frame body 空 + iframe 有内容 → 旧默认求值返回空,
  frame-walk 取到 iframe 内容。
- 覆盖: tests/unit/test_browser_local_p3.py::test_extension_extract_frame_walk。

### 11.10 browser_local extract 空 — 系统性诊断(2026-08-23)

#### 现场事实(用户观测)
1. 浏览器 Console 手动 document.body.innerText 有内容(标题可见)
2. CDP Runtime.evaluate 经扩展返回空/undefined
3. 手动 chrome.debugger.sendCommand 也返回 undefined(回调不触发)
4. 专属标签页已登录(头像可见)
5. tabId 从 654919240 → 654919243(标签页曾被关过)

#### 根因(代码逐点核对)
- **会话失效**: tabId 变化(事实5)说明标签页被关过; SW 休眠期间 chrome.tabs.onRemoved
  不触发 → currentTabId 仍指向旧 tab; attach 到已关闭 tab 失败被 catch 吞掉(原实现
  `catch (e) {}` 静默忽略) → 后续 sendCommand 回调永不触发(事实3)→ 挂起/空(事实2)。
- **cdpSend 无超时**: chrome.debugger 会话失效时回调可能永不触发, Promise 永不 settle,
  V9 侧表现为 browser_local 超时(此前 50-113s)。
- **无诊断日志**: 无法区分 指令未到/attach 失败/求值返回异常, 只能黑盒猜。
- **fill 硬拦截遗留**: checkScope 仍无条件拒 fill(P1 只读遗留), 与 P2 开放 fill 冲突。
- **SPA 水合**: 小红书内容懒加载, navigate 后立即 extract 可能取到空 body。

#### 修复
- attach 错误分类: already attached=可用; tab 不存在=会话失效(重置 currentTabId 报错);
  其他=detach 后重 attach 一次。
- cdpSend 加 10s 超时: 回调不触发 → 显式报错(不再无限挂起)。
- handleMsg 执行前 chrome.tabs.get 校验标签页存在, 失效重置并返回明确错误。
- [BL] 前缀 console.log: exec 收/发、attach 结果、extract 响应结构、exceptionDetails、
  全空日志(SW Console 可查)。
- extractPageText 两轮重试(第二轮前等 800ms 水合) + iframe 逐 frame(上节 §11.9)。
- 移除 checkScope 的 fill 硬拦截(敏感内容仍由服务端 browser_local 硬拒密码/支付)。

#### 使用诊断日志
1. chrome://extensions → 扩展详情 → 勾选『检查视图: service worker』(或 Inspect)。
2. 重新加载扩展后发任务, SW Console 看 [BL] 前缀日志:
   - 无『收到 exec』→ WS 链路问题(看 WS onopen/onmessage)
   - 有『收到 exec』无『execCdp』→ scope/标签页校验拦截
   - 有『attach FAIL tab 不存在』→ 标签页关闭, 需重新开启
   - 有『CDP 命令超时』→ 会话失效, 扩展会自动 detach 重试
   - 有『exceptionDetails』→ 页面 JS 异常, 看详情
   - 有『extract 全空』→ 内容确不在 DOM(动态渲染/需滚动/被风控)

#### 覆盖
- tests/unit/test_browser_local_p3.py: cdpSend 超时/attach 分类/标签页校验/诊断日志/fill 放开。

### 11.11 extract 空根因确认: CDP 求值需切页面 main world context

- 决定性证据: Console document.body.innerText 有内容, CDP Runtime.evaluate 空
  → debugger 可能落在扩展隔离 world(非页面 main world), 且同 frame 多上下文时
  按 frameId 单键存储会互相覆盖(隔离 world 覆盖 main world)。
- 修复:
  1) 上下文跟踪改为 contextId → {frameId, isDefault, name} 存全量
     (executionContextCreated 的 auxData.isDefault=true 即页面 main world);
  2) extractPageText 候选 = 所有上下文, 排序 isDefault=true 优先 + 主 frame 在前,
     Runtime.evaluate 带 contextId 指定 main world 求值(与 Console 一致);
  3) [BL] 日志输出找到的 main world contextId(验证用)。
- 实测(Chromium): isDefault=true 上下文(主 frame + iframe)正确识别, 隔离 world
  isDefault=false; 主 frame 优先求值返回与 Console 一致的笔记标题。
- 覆盖: tests/unit/test_browser_local_p3.py::test_extension_extract_main_world_context。

### 11.12 extract 空根因确认: 缓存的 contextId 在页面导航后过期

- 证据: 标签页手动 Console 有内容, CDP 用缓存的 contextId 返回空;
  navigate/search 会销毁旧 execution context 创建新 context, 缓存 contextId 失效
  (实测跨文档导航后旧 contextId 求值报 'Cannot find context with specified id')。
- 修复: extractPageText 每次调用前强制刷新上下文 —
  1) Runtime.disable + 2) runtimeCtxByTab.delete(tabId) 清缓存 +
  3) Runtime.enable 重新收 executionContextCreated + 4) 用最新收集的
  main world context 求值, 不复用跨导航的旧 contextId。
- 实测(Chromium HTTP 跨文档导航): 旧 contextId=1 求值空(err=Cannot find context);
  disable+enable 重收集 contextId=2, 求值取到页面 B 内容。
- 覆盖: tests/unit/test_browser_local_p3.py::test_extension_extract_context_refresh。

### 12. 桥接扩展合并进 ClawsJoy AI 插件(2026-08-23)

#### 目标
- 用户只装一个扩展(ClawsJoy AI 助手); 本地浏览器操作是插件内置能力(设置里开关)
- 一个 WS 连接 + 一套授权; 无「桥接」概念暴露

#### 合并结构
| 原(独立 browser-extension) | 合并后(clawsjoy-ai-extension) |
|---|---|
| web/browser-extension/background.js(444行) | src/bridge.ts(桥接逻辑 JS→TS 移植) + src/background.ts(装配) |
| web/browser-extension/popup.js/html | src/sidebar/index.ts + index.html(设置弹窗「本地浏览器操作」开关) |
| web/browser-extension/manifest.json | clawsjoy-ai-extension/manifest.json(加 debugger/tabs/alarms 权限) |

#### 关键点
- WS 协议不变: hello{user_id} → exec → result; userId 用 V9 设置里的 userId(appStore.settings.userId),
  后端 bridgeUserId 持久化(与 browser_local 的 user_id 归一化配合)。
- 授权: 设置弹窗开关 → background browserConnect 合并 BASE_SCOPES(含 click/fill/search,
  publish 单独) → 单 WS 连接; browserDisconnect 撤销 + 关标签页。
- 保留全部修复: WS/5006、Page.enable、document.title、main world + frame 求值、上下文刷新、
  cdpSend 超时、attach 分类、标签页校验、[BL] 日志、keepalive alarms、WS 地址可配置。
- chat 走 SSE(原有), 浏览器指令走单 WS(合并后一个连接)。
- web/browser-extension/ 目录已删除。

#### 覆盖
- tests/unit/test_browser_local_p3.py 扩展测试全部指向新文件(bridge.ts/manifest/sidebar)。
- 新增 test_extension_merged_single_package(无独立目录 + 开关存在)。

### 12.1 extract 空最终根因: chrome.debugger 回调取值多一层

- 决定性证据(用户实测): chrome.debugger.sendCommand Runtime.evaluate 返回
  {"result":{"description":"840","type":"number","value":840}} — 回调参数 = CDP
  响应的 result 字段(比原生少一层信封), 取值应为 r.result.value(两层);
  原代码 r.result.result.value(三层) → undefined → 空。
- 影响: extractPageText/tryEval、navigate title/url、click/fill、publish、search 全部
  取值多一层 → 一直空(此前 Page.enable/main world/上下文刷新均为正确协议层, 但取值错)。
- 修复: bridge.ts 所有 Runtime.evaluate 结果解析 result.result.value → result.value,
  exceptionDetails 由 result.exceptionDetails → 顶层 exceptionDetails(同样少一层)。
- 实测(Chromium 模拟 chrome.debugger 形态): 旧解析 None, 新解析取到内容;
  数字场景 cb2={"result":{"type":"number","value":840,"description":"840"}} 与用户证据一致。
- 覆盖: tests/unit/test_browser_local_p3.py::test_extension_runtime_evaluate_parse_depth。

---

## 附 · 现行方式（批202 补，指向真正在用的东西）

- **唯一出口**：`core/tools/browser_runtime.py`（launch / 会话 / **CDP** 都在这里）；产品树内不允许第二处 `chromium.launch(`（门内 `tests/unit/test_p197_browser_exit.py` 拦截）。
- **CDP 真同源模式（当值）**：起**长驻专用实例** `bash tools/start_dedicated_chrome.sh`（`--remote-debugging-port=9222 --user-data-dir=C:\Users\flybo\.clawsjoy\chrome_cdp`）后，`export CLAWSJOY_BROWSER_CDP=http://127.0.0.1:9222` ⇒ `connect_over_cdp` 连它；**连不上明确报错、绝不静默回退 launch**。
- **不需要 portproxy**：WSL 为 mirrored 网络（WSL `127.0.0.1` 直达 Windows `127.0.0.1`，实测可连；宿主 IP `192.168.3.11:9222` 实测不通）⇒ CDP 只绑本机。
- **真机 L3 复跑**：`CLAWSJOY_BROWSER_CDP=http://127.0.0.1:9222 python3 tools/p202_cdp_l3.py`。
- 本文上半部分描述的「浏览器扩展 + 专属标签页」**已废弃**（无扩展目录、`chrome.runtime.sendMessage` 0 命中）。
