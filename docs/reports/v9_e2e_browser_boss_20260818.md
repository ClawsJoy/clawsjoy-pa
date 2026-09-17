# ClawsJoy V9 Agent 端到端验证报告（Harness 浏览器模拟老板）

- **日期**: 2026-08-18
- **方式**: Playwright 真实浏览器（headless Chromium），非 mock
- **被测环境**: 沙箱网关 http://localhost:5003（ClawsJoy Gateway v6.0，P0-P2 全量代码 + 本次修复）
- **工作台**: web/dashboard/workbench.html（路由 /workbench）
- **场景**: 模拟老板在 V9 工作区下达受控任务 -> 观察进度/工具调用 -> 出现审批卡时确认 -> 验证任务完成

---

## 一、任务是否完成 [通过]

| 项 | 结果 |
|---|---|
| 任务 | 用 write_file 创建 boss_e2e.txt（内容：E2E验证成功 2026-08-18），写完后用 read_file 读取确认 |
| 文件创建 | 找到 data/projects/{user}/.../clawsjoy_dev/boss_e2e.txt |
| 内容校验 | 含 E2E验证成功 2026-08-18（content_ok=True） |
| 前端完成态 | 终端显示 任务完成（done=true） |
| 总耗时 | 11.2 秒（从发送到完成） |

### 浏览器端完整时间线（终端实录）
1. 用户任务已发送（老板在 Agent 工作区输入 + 回车）
2. 任务开始执行（SSE start 事件）
3. 执行进度 0/16（0%）（进度条渲染）
4. write_file(boss_e2e.txt) - 等待老板确认写入（审批门拦截）
5. 执行进度 1/16（6%）
6. 审批卡出现：Agent 请求写入（需确认）+ 文件路径 + 内容预览 + 确认写入/拒绝 按钮
7. 已确认写入（老板点击确认）
8. write_file 已确认写入（服务端执行成功）
9. 任务开始执行（审批后桥接续跑）
10. 执行进度 0/16（0%）
11. read_file(boss_e2e.txt)（Agent 按要求读取确认）
12. 执行进度 1/16（6%）· 步骤 1/8
13. 任务完成

---

## 二、前端显示是否正常

| 检查项 | 结果 | 说明 |
|---|---|---|
| workbench 加载 | 通过 | /workbench HTTP 200，133KB 页面正常 |
| Agent 工作区 | 通过 | 点击 Agent 工作区 打开模态，输入框可用 |
| 消息渲染 | 通过 | 用户消息/Agent 消息/工具步骤逐行 agentLog |
| 进度条 | 通过 | 执行进度 N/M（P%）· 步骤 x/y 每次工具后实时更新 |
| 工具调用痕迹 | 通过 | write_file/read_file 带 成功/失败 图标与参数 |
| 审批卡 | 通过 | 写入审批卡含路径+内容预览+确认/拒绝按钮；点击后禁用防重复 |
| 审批后继续 | 通过 | 确认后自动续跑桥接循环（read_file 验证 -> 任务完成） |
| 网络请求 | 通过 | 3 次 POST /v9/agent/chat（任务/审批/续跑）+ sandbox list + balance |

---

## 三、V9 行为是否合理

1. 写操作审批门控生效 - V9 检测到 write_file 时暂停执行，产出审批卡等待老板，不擅自写盘。
2. 审批内容透明 - 审批卡展示目标路径与内容预览，老板可判断。
3. 审批后按原计划继续 - 确认写入后自动续跑，执行 read_file 验证，最后声明任务完成。
4. 沙箱隔离 - 文件写入 data/projects/{user}/{session}/clawsjoy_dev/ 沙箱根目录。
5. 行为偏差（本次修复前）：
   - 审批确认后报 待确认的写操作不存在或已过期（后端状态未落库）
   - 审批后不再续跑，卡死在审批卡（前端 continuation 缺失）
   - 续跑时 DeepSeek 400 insufficient tool messages（事件日志投影缺 tool result）
   - 以上 3 项已修复，复测通过。

---

## 四、前端问题清单

| # | 问题 | 状态 | 说明 |
|---|---|---|---|
| F1 | /static/js/agent_discussion_sse.js 404 | 已修复 | workbench.html 引用根路径 /static/js/，实际文件在 web/static/js/；改为 /web/static/js/agent_discussion_sse.js（/web/<path> 路由 200） |
| F2 | 审批后 agentSend() 因输入框已清空而直接 return，循环不续跑 | 已修复 | agentSend 增加 continueMsgs 参数 + runAgentLoop 提取；write/plan/ask 三处回传 continue_messages |
| F3 | 桥接 done payload 残留 tool_calls 时前端重复客户端执行工具（write_file 死循环） | 已修复 | d.tool_steps 非空且 msg.tool_calls 非空时 continue 跳过客户端执行 |
| F4 | 进度条检测 | 观察 | 进度条为内联样式 div 无 class；E2E 改用文本 执行进度 检测通过，无功能问题 |

---

## 五、V9 行为偏差清单

| # | 偏差 | 严重度 | 修复 |
|---|---|---|---|
| B1 | 审批状态未落库：ApprovalGuard 返回 write_pending，但 bridge_loop 未写 _pending_writes[session_id]（P1 收尾 4b 误删状态写入块）-> 老板确认必失败 | 高 | 恢复状态写入：_pending_writes[session_id] = pending_write + 落盘 + 并发锁；plan_pending 同恢复 |
| B2 | 审批后续跑断裂：前端 agentSend 依赖输入框内容，审批回传后无法继续 | 高 | 后端 reject 分支补 continue_messages；前端 agentSend(continueMsgs) 直接续跑 |
| B3 | 事件日志投影缺 tool result：确认后的写执行未记入 session_log，P2b derive_messages 产生无结果 tool_call -> DeepSeek 400 | 高 | _resume_bridge_after_approval 补 log_event(tool_call + tool_result) |

---

## 六、修复代码位置

- agent_gateway_enhanced.py：
  - bridge_loop write_pending/plan_pending 分支：恢复 _pending_writes/_plan_pending 状态写入（~L1943-1956）
  - _handle_write_approval reject 分支：返回 continue_messages（~L1575）
  - _resume_bridge_after_approval：确认后执行补记 session_log tool_call + tool_result（~L1640-1655）
- web/dashboard/workbench.html：
  - agentSend(continueMsgs) + 提取 runAgentLoop(messages)（~L1355）
  - write/plan/ask 三处回传 agentSend(d.continue_messages)（~L1784/1868/1941）
  - 桥接模式防重复客户端执行（~L1560）
  - /static/js/ -> /web/static/js/（~L2543）
- tests/integration/test_frontend_protocol.py：split 适配 agentSend( 新签名

---

## 七、回归

- 全量测试：387 passed, 0 failed（tests/unit + tests/integration）
- E2E 复测：11.2s 完成，done=true / file_found=true / content_ok=true / console_errors=[]
- 验证报告见 _e2e.txt，截图见 _e2e_boss_screenshot.png

## 八、待办提示

1. 需将 agent_gateway_enhanced.py / web/dashboard/workbench.html / tests/integration/test_frontend_protocol.py 同步到 live（/home/flybo/clawsjoy_v5）并重启网关（用户手动）。
2. 沙箱 config 端口改动（clawsjoy.yaml 5003 / system_unified.yaml 5003）确认是否保留。
