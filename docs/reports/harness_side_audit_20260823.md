# Harness 侧自检报告 — 项目总结 + 数据清单

> 日期：2026-08-23 | 依据：会话历史(含压缩摘要) + 工作区真实产物(git/goals/docs/tests/research)
> 说明：本报告盘点 Harness(本 agent 运行时)视角的工作记录，与「路1(V9 侧自检)」互为补充。

## 1. 讨论过的项目 / 任务

### 1.1 唯一主线项目：ClawsJoy OS V9 网关
- 核心代码 agent_gateway_enhanced.py(ClawsJoy Gateway v6.0, ~5400 行) + core/(网关/守卫/工具/会话日志)
- 工作台前端插件化子项目 clawsjoy-ai-extension/(MV3 TypeScript, 对话/SSE/设置/状态显示)

### 1.2 按时间线的主要任务批次

| 批次 | 内容 | 结论 |
|---|---|---|
| P0-P4 核心迭代 | 三通道收件箱(followup/steer/inject)、goal 持久化、并行工具(写串行 barrier)、回放、任务取消、上下文投影、审计通知、并发测试 | 全部落地 |
| V9 能力基准 | capability benchmark + 断点1(PROJECT_TREE) + P0 沙箱路径映射 + 断点2(强制策略切换) + stdout 截断 + 子代理 goal 继承 | 修复闭环 |
| 前端模块化重构(7步) | workbench.html 拆分为 9 个 JS 模块(chat/approval/subtask/discussion 等) | 完成, 线程隔离修复 |
| LLM 链路修复 | max_tokens 空输出、reasoning_content 压缩、_finalize_messages 唯一出口、计划死锁、goal 多轮 | DeepSeek 400 规则实证 |
| 本地浏览器操作(Manus 对齐) P1-P4 | WS 桥接扩展 → 15+ bug → 判定扩展 CDP 平台不可行 → 转向 Python 客户端(playwright 持久上下文) → 插件桥接改造(纯 UI) | 大方向转向, 见 §3 |
| 报告完整性 | write_file 截断检测(728 字节案例)、YouTube 平台配置 | 落地 |

### 1.3 其他讨论主题
- 守卫框架(11 守卫)、Turn 协议(前端完成/后端待写)、知乎人物页抓取研究(见 §3)
- 环境适配: WSL2 端口/网络、Windows svchost 冲突、DeepSeek 超时/配额

## 2. 关键数据点

### 2.1 规模(实测工作区)
| 指标 | 数值 |
|---|---|
| Python 文件 | 1290(排除 .venv/node_modules) |
| git 提交 | 1265 次(2026-08-01 至 08-23) |
| 测试文件 / 测试函数 | 134 / 664 |
| 全量回归 | 768 passed, 唯一失败=预存 flake test_p2_failure_records::test_outer_except_recorded |
| 设计文档 / 报告 | 8 / 37 |
| goal 文件 | 7(6 完成, 1 路1自检 active) |
| research 站点目录 | 10 |

### 2.2 实证结论(实验记录)
1. DeepSeek API 400 规则(实测): tool_calls/tool 配对完整、tool_calls 必须带 type、assistant(tool_calls) 必须带 reasoning_content(空串可) — _finalize_messages 唯一出口修复。
2. CDP Page.getTitle 已从协议移除(Chromium-1234 实测): 返回 -32601 wasn't found, 需 Runtime.evaluate document.title。
3. chrome.debugger MV3 SW 不可靠(实测): 半死会话(attach already-attached + sendCommand 永不回调), 15+ bug 修不完 → 平台层死路。
4. 小红书风控: 沙箱 IP 触发 安全限制 IP存在风险 300012; YouTube 沙箱可达, 真实提取视频标题+链接成功。
5. WSL2 网络: localhost:5005 转发可达; 192.168.3.11 共享 IP 不可达; Windows svchost 占用 5004 → WS 端口定 5005。
6. write_file 截断: 728 字节报告断在 URL → 4 条完整性启发式(未完成URL/围栏/表格/硬切)。
7. 知乎反爬: 纯 HTTP 客户端遇 zse-ck v4 JS 挑战(403), 无法绕过 → 佐证「真实浏览器」路线。

## 3. 知乎相关讨论与记录

### 3.1 真实抓取实验(2026-08-01, 有数据落盘)
- 文件: data/research/www.zhihu.com/analysis_john-18-20.md
- 目标: 知乎人物页 zhihu.com/people/john-18-20(简介/创作数/关注数/头像)
- 结果: 获取失败 — HTTP 403 + zse-ck v4 反爬 JS 挑战(需执行 JS 加密签名回写 Cookie; urllib/requests 无法绕过; 3 种请求策略全失败)
- 意义: 该记录是「扩展 CDP → Python 客户端真浏览器」路线转向的佐证之一

### 3.2 平台支持现状(zhihu 在 V9 浏览器方案中)
- 域名白名单: config/v9/execution_policy.yaml 含 zhihu.com
- Python 客户端内置配置 scripts/agent_client/platforms.py: zhihu {login_url, search_url, card_selector(.SearchResult-Card,.Card), login_cookie(z_c0)}
- 真机验证路径: 用户机扫码登录 z_c0 → search 提取知乎回答/文章(待真机执行; 知乎搜索页同为 JS 渲染, playwright wait_for 已覆盖)

## 4. 一句话总结

Harness 侧 23 天内围绕 ClawsJoy V9 网关完成 1265 次提交、664 个测试、两次大方向决策(扩展 CDP→Python 客户端、插件纯 UI 化), 核心经验: 一切以真实环境实测为准(DeepSeek 400 规则/CDP 协议缺失/风控/反爬), 知乎反爬记录与浏览器方案演进互为因果。
