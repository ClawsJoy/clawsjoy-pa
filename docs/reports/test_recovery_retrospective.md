# 测试修复与信任恢复回顾

> 生成时间: 2026-08-16 | 依据: 本会话 commit 记录（45d9913 → b09d744）与人工审核记录
> 目的: 诚实标注 Harness 与人工的分工边界，不夸大 Harness 作用

---

## 一、背景

围绕"Harness 篡改测试掩盖失败"的误判展开信任修复。结论已翻转（ISSUES 第八轮记录）：4 个测试适配现存 API 是**修复死测试**，非篡改。本回顾补充**完整分工账本**。

## 二、Harness 参与的部分（本会话有 commit 证据）

### 1. 测试篡改疑云的自查声明
- **做了什么**：应人工要求，用 git 历史 + 与 live 逐文件 diff，输出完整篡改清单（含改前改后内容、commit、动机），并主动标注非本会话改动（test_e2e/test_chat_agent_v4 由 agent 自动提交删除，非 Harness 操作）
- **边界**：自查是"证据整理"，**判定"是否篡改"由人工做出**（结论翻转也是人工主导）
- 证据：篡改清单（本会话输出）+ ISSUES 第八轮

### 2. test_intent_router 污染修复
- **做了什么**：
  - 定位污染源：模块级 `sys.modules['engine.semantic']` mock 注入污染全局（全量时前序测试已真实加载 engine → mock 注入失效 → intent 变 None）
  - 修复：mock 注入移到 `setUpClass` + `tearDownClass` 恢复 sys.modules + INTENT_TO_AGENT 快照恢复（45d9913）
  - 按人工审核补强断言：assertIsNotNone → 精确断言（math→calculator_agent 等），并修 mock 固定返回 chat 的设计缺陷（side_effect 按输入返回）（f15f57a）
- **边界**：污染修复方向（setUpClass/tearDownClass）由人工审核确认"正确"；断言补强是响应人工"测试弱化"审核
- 证据：45d9913 + f15f57a

### 3. 新增集成测试（本会话 9 个新文件，约 30 用例）
| 文件 | 用例数 | 覆盖 |
|---|---|---|
| test_http_audit.py | 2 | HTTP 路由 G4 审计 |
| test_session_clean.py | 4 | /v9/session/clean 清理 |
| test_v9_stream.py | 2 | 流式 SSE 事件 |
| test_subtask_executor.py | 3 | 子任务状态机/归档/保留现场 |
| test_v5_clean_cmd.py | 3 | /clean 指令拦截 |
| test_subtask_path.py | 4 | 子任务路径锚点 |
| test_subtask_git_hooks.py | 2 | git 钩子透传 |
| test_subtask_verify_fix.py | 7 | 验证链/复核修复 |
| test_subtask_llm_limit.py | 3 | 信号量/退避重试 |
- **边界**：这些是 Harness 为三任务（/clean、流式、子任务并发）编写的配套测试；**测试有效性由人工审核/实测确认**（子任务 v1-v7 全部实测暴露问题，测试本身没拦住——checklist 已记录该教训）

### 4. 其他 Harness 实际参与（有 commit）
- conftest 合并（live 38 行版 + client 恢复 + 末尾 tiktoken 预热，5696c37）——**合并过程发现 live 版缺 client 导致 17 errors**，人工审核后定案
- sync_check 删除流程检查（b09d744）——落实"API 删除须同步删测试"教训
- test_identify_type 偶发失败重跑确认（3 次全过，非 Harness 改动导致）

## 三、人工主导的部分（Harness 未参与或仅配合）

> 以下项**非 Harness 本会话 commit**——由人工（用户侧）发现/修复，Harness 未声称贡献。

| 项 | 说明 | Harness 角色 |
|---|---|---|
| 发现 4 个 unit 测试被适配 | test_code_agent/analysis/calculator/decision_routing 断言被改 | 无（Harness 未参与这些文件的修改；test_decision_routing 经 Harness 核实：模块存在、4 passed、零修改记录）|
| 判定 API 过时 | 查生产代码 + git 历史确认被适配 API 已删除/变更 | 配合提供 git 历史证据（如 WisdomWrapper 删除注释）|
| calculator 科学计算 bug 修复 | re.sub 反斜杠转义问题 | 无（本会话记录无此修复）|
| intent_router 模式识别补全 | 语义/关键词模式扩展 | 无（Harness 只做了测试隔离，未改生产模式识别）|
| data_source_manager 语法错误修复 | 生产代码语法修复 | 无 |
| sag_bridge/manual_registration mock 化 | 测试 DB 不可用降级 mock | 无（Harness 的 sag_bridge 测试与此不同）|
| api_fixed auth_headers fixture 补齐 | 测试 fixture 修复 | 无 |
| full_flow 并发测试改串行 | 消除并发时序不稳定 | 无（本会话 test_full_flow 并发失败为已知环境项，未由 Harness 修改）|
| long_loop 状态机测试对齐 | 状态机测试与实现对齐 | 无 |

## 四、分工边界诚实总结

1. **Harness 的核心贡献**：三任务配套测试（约 30 用例）+ intent_router 污染隔离 + 自查清单 + 删除流程防线——都是**可验证的 commit 产出**
2. **Harness 的局限**：子任务 v1-v7 七轮问题全部靠 live 实测暴露，Harness 写的测试**没有提前拦住**（单测 mock 隔离掩盖真实执行链）——checklist 已固化该教训
3. **人工的主导价值**：判定方向（篡改 vs 死测试）、API 过时定性、生产 bug 修复（calculator/data_source 等）、测试语义对齐——这些是**测试体系有效性的最终仲裁者**
4. **未夸大声明**：本文档中"Harness 参与"仅限有 commit 证据项；人工主导项 Harness 明确未参与

## 五、遗留与后续

- test_identify_type 曾偶发失败（1 次全量），重跑 3 次全过——flaky 待观察
- tests/unit/test_engine_interface.py 收集错误（engine.audit 缺失）为 sandbox 环境问题，live 无
- 删除流程检查已入 sync_check（b09d744），后续删除 API 应跑该检查
