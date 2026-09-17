# V9 多平台模拟真人浏览器客户端设计（Python + Playwright 持久上下文）

> 状态: 设计稿 — 确认后实施
> 前提: V9 agent 工作区前端插件化项目不变; 解决「多平台模拟人登入 + 操作」(参照 Manus: 云端/桌面真浏览器 + 扫码登录一次 + 持久复用)

## 1. 总体评估（为什么放弃扩展 CDP）

### 1.1 结论: 扩展 CDP 方向确认为死路（平台层, 非代码可修）

最终日志实证:
\`\`\`
[BL] attach already-attached tab= 654919299      ← attach 报"已附加"（旧会话）
[BL] exec 异常 action= search CDP 命令超时(未收到回调, 会话可能失效): Page.enable   ← sendCommand 永不回调
\`\`\`

- **半死会话**: attach 状态与实际 session 不同步; SW 休眠/唤醒后 chrome.debugger 会话悬空;
  sendCommand 回调在 SW 切换时丢失; 无可靠重建机制。
- 15+ 轮修复(Page.enable / main world / 上下文刷新 / 取值层数 / cdpSend 超时…)逐一被新问题击穿,
  根因是 **chrome.debugger API 在 MV3 Service Worker 中不适配长驻会话**——Manus 不用它, 用云端 playwright/puppeteer。
- 沙箱探针实证: 小红书搜索页纯 JS 渲染, 扩展的 Runtime.evaluate 在"半死会话"下连 Page.enable 都到不了。

### 1.2 保留的资产（V9 侧全部不动）

| 资产 | 位置 | 保留理由 |
|---|---|---|
| browser_local 工具 schema + _TOOL_REGISTRY 插件 | core/tools/browser_local.py | Agent 契约不变 |
| 审批/审计/发布历史/监控/回复队列 | core/lib/v8/browser_local.py | 安全与运营流不变 |
| user_id 归一化(_resolve_conn_user) | core/lib/v8/browser_local.py | web_xxx/user-mtxxx 映射仍需要 |
| WS 协议 hello/exec/result/state | bridge 同款 | 客户端直接复用 |
| WS 端口 5006 + 网关路由 | config/execution_policy.yaml, agent_gateway_enhanced.py | 不变 |
| ClawsJoy AI 插件(工作台前端) | clawsjoy-ai-extension/ | **项目不变**(对话/SSE/设置), 仅"本地浏览器"区改显示客户端状态 |

### 1.3 变更点: 执行后端换引擎

| 原(扩展 CDP) | 新(Python 客户端) |
|---|---|
| Chrome 扩展 chrome.debugger | **playwright 持久上下文**(真实 Chrome, headed) |
| SW 生命周期导致会话悬空 | **独立 Python 进程**, 无 MV3 限制 |
| Runtime.evaluate 隔离世界/上下文地狱 | **playwright 原生 main world 求值** |
| 内容需手动等渲染 | **locator.wait_for 原生等待 JS 渲染** |
| 登录态随 SW 丢失 | **user data dir 持久化**, 扫码一次永久复用 |
| 风控只能干等 | **headed 窗口用户可直接过验证** |

## 2. 架构

\`\`\`
┌─────────────────┐  HTTP/SSE   ┌──────────────────┐   WS(5006)   ┌──────────────────────────┐
│ ClawsJoy AI 插件 │◄──────────►│ V9 后端(Gateway)  │◄───────────►│ agent_client.py(用户机)   │
│ (工作台, 不变)    │            │ browser_local 工具 │             │  ├ ws_client(协议)        │
└─────────────────┘            │ 审批/审计/发布历史  │             │  ├ browser(playwright)   │
                               └──────────────────┘             │  ├ actions(8 动作)        │
                                                                │  └ platforms(yaml 适配)   │
                                                                └────────────┬─────────────┘
                                                                             │ launch
                                                                    ┌────────▼─────────────┐
                                                                    │ 真实 Chrome (headed)   │
                                                                    │ persistent context    │
                                                                    │ 登录态 + 人工过风控      │
                                                                    └──────────────────────┘
\`\`\`

## 3. 模块设计（scripts/agent_client/）

| 文件 | 职责 | 要点 |
|---|---|---|
| agent_client.py | 入口: 装配 + 事件循环 | 读 config → 启动浏览器 → 连 WS → 循环收 exec |
| ws_client.py | WS 协议 | 复用 bridge 协议: hello/exec/result/state/ping; 断线指数退避重连(无 SW 限制, 可靠) |
| browser.py | playwright 管理器 | launch_persistent_context(user_data_dir, headless=False); 首次自动打开登录页等扫码 |
| actions.py | 8 动作执行 | 见 §4 映射表; 每动作 try/except + 结果回传 |
| platforms.py | 平台适配器加载 | 从 config/platforms.yaml 读选择器/URL 模板 |
| config/platforms.yaml | 平台配置 | 登录/搜索 URL + 卡片/标题/链接选择器 |
| README.md | 用户启动说明 | 一键启动(bat/exe) + 首次扫码流程 |

**依赖**: python3 + playwright(pip install playwright && playwright install chromium) — 或打包 exe(用户零依赖)。

## 4. 动作映射（CDP → Playwright 原生）

| browser_local action | 扩展(CDP) — 已弃 | Python 客户端(playwright) |
|---|---|---|
| navigate | Page.navigate + evaluate title/url | page.goto(url, wait_until='domcontentloaded') + page.title()/page.url() |
| extract | Runtime.evaluate innerText(隔离世界/上下文地狱) | page.evaluate('document.body.innerText') / locator.inner_text() — **原生 main world** |
| screenshot | Page.captureScreenshot | page.screenshot(full_page=…) |
| scroll | evaluate scrollBy | page.evaluate('window.scrollBy(0, N)') 或 mouse.wheel |
| click | evaluate el.click() | page.locator(sel).click(timeout=…) |
| fill | evaluate set value+事件 | page.locator(sel).fill(text) — **原生 input/change 事件** |
| search | navigate + 手动等卡片(从未等到) | goto 搜索URL + **locator.wait_for(card_selector)** + 提取卡片标题/链接 |
| publish | evaluate 填表+点发布 | locator.fill + locator.click(选择器同平台配置) |

**核心可靠性质变**: playwright 的 wait_for 原生等待 JS 渲染(小红书瀑布流正是这类); 求值在页面 main world(无隔离世界问题); 事件由真实浏览器分派(填表/点击更接近真人)。

## 5. WS 协议（复用 + 2 条新增）

复用(与扩展一致):
\`\`\`
client→V9  hello  {user_id, tag:"python-client"}
V9→client  exec   {cmd_id, action, params}
client→V9  result {cmd_id, ok, data}
client→V9  state  {user_id, state:"busy|idle", url}
client→V9  closed {user_id}            # 客户端退出/浏览器关闭
\`\`\`

新增:
\`\`\`
client→V9  login_status {platform, logged_in:bool}   # V9/Agent 知道哪些平台已登录
client→V9  verify_required {platform, url}            # 触发风控 → V9 暂停并提示用户手动过验证
\`\`\`

V9 侧 browser_local 工具/审批/审计 **零改动** —— 客户端只是更可靠的执行者。

## 6. 平台适配（config/platforms.yaml，加平台=加配置）

\`\`\`yaml
xiaohongshu:
  login_url: "https://www.xiaohongshu.com"                # 扫码/密码登录页
  search_url: "https://www.xiaohongshu.com/search_result?keyword={q}"
  card_selector: "section.note-item, .note-item"
  link_selector: "a[href*='/explore/']"
  title_selector: "a[href*='/explore/'] .title, .title"
  publish: {title: "input[placeholder*=标题], .title-input", content: "textarea[placeholder*=正文], .note-editor", submit: "button:has-text(发布)"}
douyin:   {…}
bilibili: {…}
zhihu:    {…}
weibo:    {…}
\`\`\`

## 7. 风控与人机验证

- **headed 窗口常驻可见**: 滑块/验证码出现时用户直接在窗口操作(像正常上网), 客户端无需感知。
- **verify_required**: 客户端检测到验证页(URL/关键字启发式)或长时间无卡片 → 通知 V9 → Agent 提示用户"请完成页面上的验证后继续"。
- **真实 IP + 真实登录** = 模拟真人核心: 用户在自家网络跑客户端, IP 干净; 登录态为真实会话(非导出 Cookie)。

## 8. 安全

- 域名白名单仍由 V9 侧校验(不变); 客户端仅执行 V9 下发的 exec。
- 不导出/不转发 Cookie; 登录态只在用户机 user data dir。
- 发布等敏感动作仍走 V9 审批流(不变)。
- 客户端可加"仅接受来自 127.0.0.1:5006 的 WS"约束(防其他进程投毒)。

## 9. 用户流程（扫码一次, 之后全自动）

1. 首次: 双击 start_agent_client.bat(或 python agent_client.py) → 弹出真实 Chrome
2. 客户端自动打开小红书 → 用户扫码(30 秒) → 登录态存 ~/.clawsjoy/profiles/xiaohongshu/
3. 客户端连 V9 WS(5006) → login_status 上报 → Agent 即可用 browser_local
4. 之后每次: 启动客户端即复用登录态, 无需再登录; Agent 全自动

## 10. 迁移顺序（确认后实施）

| 步 | 内容 | 验证 |
|---|---|---|
| 1 | scripts/agent_client/ 骨架 + ws_client(hello/exec/result 往返) | 假动作回显 |
| 2 | browser.py 持久上下文 + actions: navigate/extract/screenshot/scroll | 真机打开百度/example |
| 3 | platforms.yaml + xiaohongshu search/card 提取(真机扫码后) | 前 10 条标题+链接 |
| 4 | login_status/verify_required 上报 | 未登录/风控提示 |
| 5 | click/fill/publish(复用审批流) | 发布审批 E2E |
| 6 | douyin/bilibili/zhihu/weibo 适配 | 各平台 search/extract |
| 7 | 打包 bat/exe + README + 插件侧边栏状态显示(可选, 插件项目主体不变) | 用户零操作 |

## 11. 与插件的关系（插件项目不变）

- ClawsJoy AI 插件(工作台/对话/SSE/设置) **零改动**。
- 插件"本地浏览器操作"开关区: 可选改为显示客户端连接状态(browserStatus 复用)或移除; 不阻塞。
- web/browser-extension 桥接扩展已删除; clawsjoy-ai-extension/src/bridge.ts 保留为备用或按确认移除。

## 12. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 用户机需装 Python/playwright | 打包 exe(playwright 内嵌 chromium)一键启动 |
| 平台 DOM 改版选择器失效 | platforms.yaml 集中配置, 改配置不改代码; 卡片提取多选择器兜底 |
| 风控升级 | headed 人工过验证 + verify_required 暂停提示 |
| WS 端口被占 | 端口可配置(默认 5006) |
| 多平台多登录态管理 | 每平台独立 user data dir 子目录 |

## 13. 验证计划

- 单元: actions 用 mock page; platforms.yaml 解析; ws_client 协议帧。
- 集成(真机): 扫码登录小红书 → search 考研复习 → 提取前 10 条标题+链接(用户机器, 沙箱 IP 被风控 300012 无法代验)。
- E2E: Agent 调 browser_local → 客户端执行 → 结果回传 → 审批流(发布)全链路。

### 12.2 agent_client 实施进度(步骤1-5)

- 步骤1-2 完成: scripts/agent_client/(ws_client/browser/actions/platforms/agent_client)
  + test_roundtrip.py ALL PASS(WS 往返 + navigate/extract/scroll + 卡片提取 fixture)。
  关键修复: playwright sync 非线程安全 → WS 线程只入队, 浏览器操作全在主线程。
- 步骤3: 小红书 search_url + 卡片选择器已配; 沙箱 IP 被风控(300012)无法直连,
  真机验证: 用户机器跑 agent_client.py --platform xiaohongshu 扫码后 search。
- 步骤4 完成: login_status 上报(cookie 启发式 check_login); 未登录 → login_required 拦截
  (search/publish/click/fill 门槛) + login_status False; 风控页 → verify_required 消息
  (页面关键字/URL 检测, search 早期快速检测不空等)。
- 步骤5 完成: click(locator.click)/fill(locator.fill)/publish(填表+点发布);
  发布审批流在 V9 侧(approve_browser 不变), 客户端仅执行审批后的 exec。
- test_step45.py ALL PASS(未登录/风控/click/fill/publish 全链路)。

### 12.3 V9 后端适配 Python 客户端(移除标签页残留)

- 问题: 后端 browser_local 连接模型仍带扩展「专属标签页」概念; 同 user 多连接
  (扩展 + python 客户端)时扩展可能覆盖/应答, Agent 报「无专属标签页」。
- 修复:
  1) register_ws_connection: 已有 python-client 连接时, 非 python(扩展)重连不覆盖;
  2) _resolve_conn_user: 连接模型=WS 连接存在即可执行 — 精确匹配优先, 无匹配时
     任意连接兜底(优先 python-client, 否则最近连接);
  3) _ws_handler_sync 接入 login_status(存连接 state)/verify_required(存 state + 告警);
  4) closed 语义改为客户端退出, 清理标签页注释。
- 覆盖: tests/unit/test_browser_local_p1.py +3(python 优先/任意连接兜底/handler 新消息)。

### 12.4 插件桥接改造: 移除主动 WS, 只做状态显示(2026-08-23)

- 根因: 扩展与 Python 客户端同连 5006 会互相干扰(tag 覆盖); 插件应纯 UI。
- 修复:
  1) 删除 clawsjoy-ai-extension/src/bridge.ts(全部 WS/CDP 逻辑);
     background.ts 只保留 sidePanel + browserStatus(HTTP 轮询 V9 /v9/browser/status);
  2) manifest 移除 debugger/tabs/alarms(CDP/标签页/keepalive 均归 Python 客户端);
  3) 插件设置「本地浏览器」改为状态显示: ✅ Python 客户端已连接 / ❌ 未检测到客户端
     + 启动客户端指引; 无授权开关/WS 配置;
  4) V9 新增 GET /v9/browser/status(browser_local.get_connection_info):
     {connected, client(优先 python-client), login_status, verify, state};
  5) Python 客户端是唯一 WS(5006)连接者。
- 后端保护(上一轮): register_ws_connection 已有 python-client 时扩展重连不覆盖。
- 覆盖: tests/unit/test_browser_local_p3.py 重写 6 个插件测试(无 WS/CDP/HTTP 状态/
  status 路由/agent_client 执行者/侧边栏状态显示)。

### 12.5 write_file 内容完整性校验(LLM 截断检测)

- 症状: LLM 生成 content 被截断(728 字节报告断在第 2 条笔记 URL, http 无结尾),
  write_file 正常落盘但内容不完整。
- 修复: core/tools/write_file.py 新增 _content_incomplete_hint(content), 完整写入后校验:
  ①末尾未完成 URL(裸协议/尾部斜杠/过短链接) ②代码围栏未闭合(``` 奇数)
  ③Markdown 表格未闭合(末非空行是表格行) ④无完整结尾(无换行+末行过短且无结尾符)。
  命中 → 写入成功但 result 附 warning「内容可能不完整…请检查或重新生成」,
  Agent 收到后重写完整内容。不阻止写入(避免误伤合法短内容)。
- 覆盖: tests/unit/test_write_file_long.py +5(截断 URL/尾部斜杠/围栏表格/完整报告>1500字节无 warning/合法短内容不误报)。

### 12.6 YouTube 平台内置配置

- platforms.py 内置 youtube: login_url/search_url(results?search_query={q})/
  card_selector(ytd-video-renderer)/link_selector(a#video-title)/title_selector(#video-title)/
  login_cookie(SID/HSID/SSID); publish 占位(YouTube Studio 发布复杂, 后续)。
- 新增平台级 search_requires_login(默认 True): YouTube 搜索匿名可用 → False,
  未登录不拦 search(否则全局 search 门槛会挡住匿名搜索)。
- 实测(沙箱可达 YouTube): 搜「考研 英语」提取到真实视频标题+链接
  (如 户子谈考研英语 → youtube.com/watch?v=PH9MY3QiKjs)。

### 12.7 V9 工作区三问题修复(2026-08-23)

1. write_file 审批重复触发: _resume_bridge_after_approval 确认执行后未清除
   _pending_writes → 同一文件重复「待确认」。修复: 执行完成后按 pending.id 匹配 pop + 持久化清除。
2. 越权拦截误伤读操作: python3 -c 读文件被拦(重定向到 /tmp 命中「写入系统目录」;
   /home/ 无条件拦截)。修复: security.py 系统目录清单豁免 tmp(临时文件合法);
   sandbox_ops python3 -c/heredoc 分支仅当代码含写操作(open w/a/write/shutil)才拦 /home/ 或 ../。
3. 禁则误伤 _tmp_ 文件: ForbiddenGuard + sandbox_ops 对含 _tmp_/_gate_/_vfy/_fix 的任意命令拦截,
   读临时文件(cat/读 _tmp_zhihu_cookies.txt)被拦。修复: 只拦「执行临时脚本」
   (python/bash/node + 临时名 + .py/.js/.sh), 读/引用临时文件放行。
- 覆盖: tests/unit/test_workspace_guard_fixes.py(5 例: pending 清除/读放行/系统写仍拦/临时读放行/临时脚本仍拦)。

### 12.8 系统性排查(今天高频 bug): 递归误伤 + 审批残留

## 问题1 递归检测误伤(同 URL 不同 action 共用计数)
- 根因: core/gateway/path_utils._extract_tool_path 对 browser_local 的 url 只返回 URL
  不带 action → navigate(X)/search(X) 都映射到 X, 共用递归计数 → 5 次误拦。
- 系统性修复(非补丁): _extract_tool_path(args, tool_name) 加 tool_name 参数,
  tool_name=='browser_local' 时 key 含 action(browser_local:{action}:{url_or_selector}),
  同 URL 不同 action 各自独立计数; 两处调用点(execute_agent_task/RecursionGuard)传 tool_name。
- 回归: test_browser_local_same_url_different_action_not_shared(交错 navigate/search/extract
  同 URL 各 3 次不累计; 同 action 同 URL 连续 5 次才拦)。

## 问题2 审批重复触发(确认后又出现 + 点击无效)
- 根因(两条残留路径):
  1) _handle_write_approval 无幂等: pending 已被 resume 清除后, 前端重复点击 approve
     返回「不存在或已过期」→「点击无效」;
  2) _resume_bridge_after_approval 的 guard-deny 早返回不 pop pending → approved=True 残留
     → 卡片重复出现「待确认」。
- 修复: ①approve 幂等(pending 已清除 → 返回 write_confirmed 而非报错);
  ②resume 的 guard-deny 路径也清除 pending。
- 回归: test_write_approve_idempotent(pending 已清除时 approve 返回已确认)。

## 问题3/4(待处理, 本轮未做)
- 工具轮次上限 16 太紧: 建议 browser_local 类操作单独计数或提高上限(execution_policy)。
- Agent 行为引导: 系统提示明确「优先 browser_local, 不写临时脚本」— 待设计提示词。

### 12.9 问题3/4 修复(工具轮次上限 + 行为引导)

## 问题3 工具轮次 16 → 32
- execution_policy.yaml execution_budget.max_total_tools: 16 → 32(浏览器多步操作需 30+);
  agent_gateway_enhanced 代码默认值 16 → 32(与 yaml 一致)。
- 回归: tests/unit/test_max_total_tools.py 断言更新为 32。

## 问题4 Agent 行为引导
- config/prompts/agent_system.md 新增「本地浏览器操作（browser_local 优先）」段:
  需登录态/风控平台内容调研必须用 browser_local; 禁止写临时 python 脚本抓取(会被禁则拦);
  search 自动提取卡片(标题+链接); 同 URL 不同 action 各自计数不误伤。
- 回归: tests/unit/test_browser_local_p3.py::test_system_prompt_prefers_browser_local。

### 12.10 知乎发布设置操作增强(2026-08-23)

## 调研结果(真实登录编辑器 zhuanlan.zhihu.com/write 实测)
- 编辑器: https://zhuanlan.zhihu.com/write(需登录; cookies 注入后沙箱可达, 用户 John Lv 5)。
- 标题: TEXTAREA placeholder「请输入标题（最多 100 个字）」; 正文: DraftEditor [contenteditable="true"]。
- **封面 input**: input[type=file] accept=".jpeg, .jpg, .png"(窄图片集);
  **正文插图 input**: accept="image/webp,image/jpg,image/jpeg,image/png,image/avif,image/heic"(宽集);
  **文档 input**: accept=".pdf,.md,.txt,.ppt,.pptx,.xlsx,.xls,.docx,.doc,.webp,..."(附件)。
  → 封面/正文/文档 三个 file input 靠 accept 特征区分(修复 set_input_files 选错 input)。
- 发布设置面板: 「发布设置」按钮打开, 含「添加封面/添加文章封面」label(UploadPicture-wrapper);
  话题输入为面板内裸 input(点击后输入 → 下拉选项), 声明为 checkbox, 发布按钮存在。
  (话题/声明精确 selector 需真机面板完全渲染后校准, 已配置化+启发式兜底)

## 实现
1. extract 加 include_hidden 参数: 返回隐藏/下拉/弹层/选项列表元素的属性+文本
   (去重 key 含 accept, 隐藏容器附 options 文本) — 发布设置调研不再只读可见文本。
2. publish 增强:
   - cover(封面路径)/images(正文插图) 经 _pick_upload_input 按 accept 特征区分上传, 不误伤;
   - topics: click 话题输入 → fill → 等下拉 → 点第一个匹配(或 Enter);
   - declaration: 声明 checkbox 按参数勾选/取消;
   - 返回 cover_uploaded/image_uploaded/topics_added/declaration。
3. schema: BROWSER_LOCAL_SCHEMA 加 include_hidden/cover 参数, platform enum 加 youtube。
4. platforms.yaml/zhihu.publish: cover_input/image_input/topic_input/topic_option/declaration。

## 覆盖
- scripts/agent_client/tests/test_publish_settings.py(fixture: 3 file input 区分/隐藏下拉/话题/声明) ALL PASS。
