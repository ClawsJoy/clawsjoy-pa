# V9 架构审查报告（基于代码实证）

> 日期：2026-08-15
> 方法：只读代码分析（agent_gateway_enhanced.py 路由层 / core/gateway 18 模块 / core/lib/v8/routes 4 蓝图 / core/tools 6 插件）
> 依据：路由表、import 关系、执行链追踪、全局状态审计、前后端协议比对
> 目的：修正 v9_state_review.md（前版基于文档，本版基于代码）

---

## 一、路由层总览（agent_gateway_enhanced.py）

### 1.1 V9 路由（22 条）

| 路由 | 行号 | 职责 | 实现 |
|---|---|---|---|
| /v9/task/save_progress | 276 | 保存任务进度 | 主文件内 |
| /v9/task/set_mode | 304 | 设置工具模式 | 主文件内 |
| /v9/task/status | 333 | 查询任务状态 | 主文件内 |
| /v9/sandbox/checkpoint | 912 | git checkpoint | 主文件内 |
| /v9/sandbox/rollback | 947 | git rollback | 主文件内 |
| /v9/sandbox/read | 967 | 读文件 | sandbox_ops handler |
| /v9/sandbox/list | 977 | 列目录 | 主文件内 |
| /v9/sandbox/search | 1031 | 搜文件 | 主文件内 |
| /v9/sandbox/query_index | 1063 | 查 SAG | 主文件内 |
| /v9/sandbox/exec | 1068 | 执行命令 | 主文件内 |
| /v9/sandbox/edit | 1073 | 编辑文件 | 主文件内 |
| /v9/user/balance | 1077 | 用户余额 | 主文件内 |
| /v9/glm/balance | 1157 | GLM 余额 | 主文件内 |
| /v9/auto_fixes | 1181 | 自动修复 | 主文件内 |
| /v9/auto_fixes/approve | 1201 | 批准修复 | 主文件内 |
| /v9/auto_fixes/reject | 1219 | 拒绝修复 | 主文件内 |
| /v9/balance | 1237 | 平台余额 | 主文件内 |
| /v9/plans/list | 1311 | 计划列表 | 主文件内 |
| /v9/agent/chat | 1492 | V9 核心桥接 | 主文件内（约1600行） |
| /v9/sandbox/write | 动态 | 写文件 | sandbox_write.register_write_routes |
| /v9/sandbox/write_large | 动态 | 大文件写 | 同上 |
| /v9/sandbox/write_begin/finalize | 动态 | 分段写 | 同上 |

### 1.2 路由注册方式（三套并存）

| 方式 | 位置 | 路由 |
|---|---|---|
| @app.route 装饰器 | 主文件 | 大部分 V9+V5 |
| register_write_routes(app) | 模块级调用 975 行 | write 系列 |
| register_*_routes(app) | 主文件多处 | v8 蓝图 |

**发现**：v8 roster 蓝图在 213 和 639 行各注册一次 → 重复注册（Flask 可能抛 endpoint 覆盖错误或静默覆盖，需实测）。

---

## 二、core/gateway/ 18 模块职责与耦合

### 2.1 模块清单（按耦合度）

| 模块 | core imports | 职责 | 评价 |
|---|---|---|---|
| archive.py | 0 | 消息归档 | 独立 |
| inject_filter.py | 0 | 网关注入过滤 | 独立 |
| quota_manager.py | 0 | 工具配额 | 独立 |
| path_utils.py | 1 | 路径解析 | 低耦合 |
| registry.py | 1 | 注册表 | 低耦合 |
| state_persist.py | 1 | 状态持久化 | 低耦合 |
| context_validator.py | 2 | 假完成校验 | 中 |
| message_assembler.py | 2 | 消息压缩 | 中 |
| os_monitor.py | 2 | OS 事件 | 中 |
| sag_feedback.py | 2 | SAG 反馈 | 中 |
| sandbox_git.py | 4 | 沙箱 git | 中 |
| v5_execute.py | 5 | v5 路由 | 中 |
| sandbox_write.py | 5 | 写文件路由 | 中 |
| tool_router.py | 6 | 工具统一路由 | 高 |
| chat_stream.py | 12 | 聊天流 | 高（v8 历史） |
| execute_agent_task.py | 15 | V9 后台主循环 | 高（核心） |
| sandbox_ops.py | 18 | 沙箱操作合集 | 最高（大杂烩） |
| shared_state.py | - | 全局共享状态 | 被6+模块依赖 |

### 2.2 隐藏耦合（代码实证）

**C1. shared_state 模块级可变状态（线程不安全源）**
- _session_write_tracker / _session_git_tracker / _session_tool_tracker / _search_file_cache / _fake_done_count 等 dict 无锁
- **_consecutive_reads / _consecutive_lists 是模块级整数（44-45 行）**：多线程并发请求共享，配额计数串扰（A 请求影响 B 请求）

**C2. sandbox_ops 循环依赖**
- sandbox_ops.py:1359（#104b 工具层防线）在函数内延迟 import agent_gateway_enhanced
- 形成 agent_gateway -> sandbox_ops -> agent_gateway 循环，靠延迟 import 规避

**C3. v8 roster 双注册**
- 主文件 213 + 639 行都调 register_roster_routes(app)

### 2.3 重复代码路径（执行链）

| 工具 | 路径A（桥接） | 路径B（前端直连） | 风险 |
|---|---|---|---|
| read_file | tool_router->ReadFilePlugin | /v9/sandbox/read handler | 双实现 |
| write_file | tool_router->WriteFilePlugin | /v9/sandbox/write handler | 双实现 |
| execute_command | tool_router->ExecuteCommandPlugin | /v9/sandbox/exec | 双实现 |
| list_dir | tool_router->ListDirPlugin | /v9/sandbox/list | 双实现 |
| search_files | tool_router->SearchFilesPlugin | /v9/sandbox/search | 双实现 |
| query_index | tool_router->QueryIndexPlugin | /v9/sandbox/query_index | 双实现 |

实证：write_file 两条链分别出 bug 且独立修复（#100 修 WriteFilePlugin，#98 修 sandbox_write）→ 双实现 = 双倍维护 + 行为漂移。

---

## 三、core/lib/v8/routes/ 4 蓝图

| 蓝图 | 路由数 | 注册位置 | 评价 |
|---|---|---|---|
| roster.py | 10 | 主文件 213/639（两次）| 重复注册 |
| billing.py | 2 | 主文件 641 | 正常 |
| task.py | 3 | 待查 | 正常 |
| v8_misc.py | 多 | 待查 | 正常 |

问题：非 Flask Blueprint，是 register_*_routes(app) 直接改路由表，无命名空间隔离。roster 双注册可能抛 endpoint 覆盖错误。

---

## 四、core/tools/ 6 插件

| 插件 | 职责 | 状态 |
|---|---|---|
| base.py | 基类 | 正常 |
| read_file.py | 读文件 | 正常 |
| write_file.py | 写文件 | #98/#100 已修 |
| execute_command.py | 执行命令 | 含沙箱检查 |
| file_tools.py | list_dir+search | 正常 |
| query_index.py | SAG 查询 | 正常 |

执行链：_execute_sandbox_tool（@_with_tool_flow）-> 分支 -> 插件.execute(args, _ToolContext(base, _resolve_path))。
- 插件层 ctx 注入，无直接 import -> 解耦良好
- 但 _ToolContext 字段少，部分依赖在 router 组装时注入

---

## 五、桥接循环状态管理（线程安全）

### 5.1 桥接循环
- _tool_steps = 函数局部变量（2200 行）-> 每请求独立，线程隔离正常
- messages = 请求参数 -> 请求隔离
- **_pending_writes = 模块级 dict 无锁**：2258 写 / 1440 读改写 / 2288 pop，并发竞态

### 5.2 pending 并发行为

| 场景 | 行为 | 风险 |
|---|---|---|
| 单请求 pending->approve | 顺序执行 | 正常 |
| 双请求同 session | 后写覆盖前 pending | 丢失 |
| approve 与主循环并发 | 读写竞争 | 竞态 |
| pending 无 TTL | 只在 approve/reject 时 pop | 泄漏 |

实证：_pending_writes 无 TTL 清理（方案提过 60s 未实现），崩溃/重启后残留。

---

## 六、前后端协议一致性

### 6.1 状态字段
| 前端处理 | 后端返回 | 一致 |
|---|---|---|
| write_pending | 有 | 一致 |
| write_confirmed | 有 | 一致 |
| write_rejected | 有 | 一致 |
| escalation_blocked | 有 | 一致 |
| initializing | 有 | 一致 |
| executing | 无（plan_status 分支用）| 死分支 |
| approved/rejected | 有 | 前端未处理 |

### 6.2 工具端点
- 前端调用的 read/list/search/exec/edit/query_index/write/write_large 后端全部注册
- checkpoint/rollback 后端有前端不用（冗余）

---

## 七、核心结论（修正版）

### 7.1 真正解耦
- archive/inject_filter/quota_manager/path_utils/registry/state_persist：独立
- core/tools 插件：ctx 注入，干净
- _tool_steps：函数局部，线程隔离

### 7.2 隐藏耦合
| # | 耦合 | 位置 | 影响 |
|---|---|---|---|
| C1 | shared_state 模块级整数配额 | 44-45 行 | 并发串扰 |
| C2 | sandbox_ops->agent_gateway 延迟 import | sandbox_ops:1359 | 循环依赖 |
| C3 | v8 roster 双注册 | 213+639 | 路由冲突 |
| C4 | 工具双实现 | router vs sandbox | 双倍维护 |
| C5 | _pending_writes 无锁无TTL | 主文件31 | 竞态+泄漏 |

### 7.3 重复/死代码
- 工具 6 项双实现
- roster 双注册
- 前端 executing 死分支

### 7.4 桥接循环线程安全
- _tool_steps/messages 请求隔离
- _pending_writes 无锁竞态
- tracker dict 无锁
- pending 无 TTL

### 7.5 前后端协议
- 核心状态一致
- executing 死分支 + approved/rejected 未处理

---

## 八、优先级建议（代码实证）

### P0
1. C1 并发配额：_consecutive_reads/_consecutive_lists 改 per-session dict 或 threading.local
2. C3 roster 双注册：删 213 重复，保留 639
3. C4 工具单实现：桥接统一走 _execute_sandbox_tool，HTTP handler 薄封装

### P1
4. C5 pending 锁+TTL：threading.Lock + 60s 清理
5. tracker 锁：写操作加锁
6. 会话恢复：pending 落盘

### P2
7. C2 循环依赖：_detect_sys_escape 移到独立 security 模块
8. sandbox_ops 拆分
9. 前端死分支清理

---

## 九、与 v9_state_review.md 差异

| 项 | 前版 | 本版 |
|---|---|---|
| 会话恢复 P0 | 已列 | 代码确认缺 |
| 异步任务 P0 | 已列 | 代码确认同步阻塞 |
| 并发配额 | 未提 | 新增发现 |
| roster 双注册 | 未提 | 新增发现 |
| 工具双实现 | 未提 | 新增发现 |
| pending 无锁 | 部分 | 代码确认竞态 |
