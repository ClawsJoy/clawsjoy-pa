# Agent 操作手册（agent_manual.md）

> 定位：ClawsJoy V9 工具说明书 — 告诉 Agent「该怎么做」。与 BRIEF.md（任务说明书）互补：
> BRIEF 说「做什么」，本手册说「用什么工具、怎么确认、怎么算完成」。
> 本手册已注册进 SAG（entity_type=manual），可用 query_index(query, entity_type='manual') 按需检索。

---

## 1. 工具清单

### 1.1 read_file — 读取文件
| 项 | 说明 |
|---|---|
| 用途 | 读取文件内容 / 定位函数 / 搜索代码 |
| 参数 | path（必填）、function（定位函数）、search（搜内容）、lines_start/lines_end、verify_line+verify_expected |
| 适用 | 探索代码、验证写入结果、按函数名定位 |
| 禁用 | 禁止用 grep/cat/head/tail 读文件（系统拦截，改用 read_file 的 search 参数）；同一文件禁止反复分段读取（读取上限 5/10，超过熔断）|

### 1.2 write_file — 写入文件
| 项 | 说明 |
|---|---|
| 用途 | 创建/修改文件 |
| 参数 | path（必填，clawsjoy_dev/ 前缀）、content（完整内容）、line（按行修改）|
| 适用 | 所有写操作；>500 行文件自动 full_write |
| 禁用 | 写前必须经确认（锚点A）；禁止用 execute_command heredoc 绕过确认；禁止 open() 直接写沙箱外文件 |

### 1.3 execute_command — 执行命令
| 项 | 说明 |
|---|---|
| 用途 | 运行命令 / 脚本 / 验证 |
| 参数 | command（必填）|
| 适用 | py_compile 语法检查、运行验证、git diff、heredoc 脚本 |
| 禁用 | 高危系统命令（rm -rf /、mkfs、dd 裸设备等，锚点B 硬禁止）；越权路径（/etc、/home 等）；写入系统目录 |

### 1.4 query_index — SAG 代码实体查询（统一检索入口）
| 项 | 说明 |
|---|---|
| 用途 | 查代码结构 / 历史上下文 / 运行时落盘记录 |
| 参数 | query（关键词）、entity_type（可选，新增）、limit（可选）|
| 适用 | 理解代码优先于 read_file；连续 3 次空结果熔断，改用 read_file 分段扫描 |
| **entity_type 参数（R1 新增）** | 指定后查 SAG 非代码实体：`audit_event`（工具审计）/ `goal`（任务目标）/ `escalation`（越权记录）/ `snapshot`（上下文快照）/ `manual`（本手册）|
| 用法示例 | `query_index(query='审计', entity_type='audit_event')`；`query_index(query='', entity_type='goal')` 查全部目标 |
| 禁用 | 同一 query 连续 3 次空 → 熔断（还剩 N 次预警后强制换 read_file）|

### 1.5 search_files — 搜索文件名
| 项 | 说明 |
|---|---|
| 用途 | 按文件名搜索 |
| 参数 | query（文件名关键词）、path（可选，默认 clawsjoy_dev）|
| 适用 | 不确定文件位置时；只搜文件名不搜内容 |
| 禁用 | 搜代码内容（用 read_file 的 search）；连续 3 次空结果熔断（还剩 N 次预警）|

### 1.6 list_dir — 列出目录
| 项 | 说明 |
|---|---|
| 用途 | 查看目录内容 |
| 参数 | path（可选）|
| 适用 | 探索目录结构（项目树已自动注入，通常无需）|
| 禁用 | 大量重复调用（配额 3 次）；minimal 模式禁用 |

---

## 2. 执行纪律（#101 Harness G1-G3）

### 2.1 todo 进度显式化（G1）
- 长任务（多文件/多步骤）开始前列 todo 清单：`[ ] 步骤1 ...`；每完成一步更新为 `[x]` 并附证据（文件+行号）
- 汇报标注 `【进度】N/M`；todo 与系统 tool_steps（服务端执行记录）对齐才算进度真实

### 2.2 计划确认强制（G2）
- **≥2 个文件 或 ≥3 个修改意图**（同文件连续修改合并计 1 意图）→ 必须先列计划等确认（系统返回 plan_pending），禁止直接执行
- 计划格式：涉及文件 + 修改点 + 影响评估 + 验证方式；被拒后调整方案重新提出
- 单文件单意图不触发，直接执行

### 2.3 ask 式提问通道（G3）
- 遇到授权/方案选择/歧义 → 用 ask 结构明确提问，禁止默默继续或替老板做主
- 格式严格可解析：`【ask】问题描述` + 每行一个选项 `选项A：xxx` / `Option A: xxx`；推荐项放第一行（前端标 ✅）

---

## 3. 完成标准（5 项 checklist）

修改类任务全部满足才可报完成：

| # | 检查项 | 验证方式 |
|---|---|---|
| 1 | 写入成功 | write_file 返回 success=True；read_file 确认内容已落盘 |
| 2 | 语法检查 | `python3 -m py_compile <file>` 通过 |
| 3 | 导入测试 | 模块可正常 import，无导入错误 |
| 4 | 功能验证 | 逻辑断言/实际运行通过（python3 -c 或 heredoc）|
| 5 | done_when 满足 | 系统断言通过（若有配置）|

- 任一失败 → 重试修复（最多 3 次）；全部通过才输出 `✅ 任务完成`
- 系统会做第三方审计复核（G4）：Agent 声称的 5 项 vs 审计记录交叉核对，不符 → 判假完成
- 禁止降级条款：不得以「仅输出计划」「口头确认」「部分完成」替代实际修改

---

## 4. 禁则清单

### 4.1 禁止执行 _*.py 脚本
- `core/lib/_*.py` 等以下划线开头的文件是测试/临时脚本（vfy_*.py、_tmp_*.py、_gate_test*.py），**禁止执行、禁止修改**
- 禁止把它们当任务目标写入或运行

### 4.2 禁止 json.load/dump 编辑配置文件
- 禁止用 json.load/dump 直接改写共享配置（filter_net.json、.agent_state.json、config/*.yaml 等）
- 这些文件由系统管理；需改配置走系统接口或说明理由请求人工处理

### 4.3 禁止绕过工具直接 open() 写文件
- 禁止 python3 -c / heredoc 里 open(path, 'w') 直接写沙箱文件（绕过 write_file 确认）
- 所有写操作必须走 write_file/write_large（锚点A 确认）；heredoc 仅用于执行脚本逻辑，不用于写文件

### 4.4 其他硬禁
- 禁止读取系统路径（/etc、/home、os.walk('/') 等，锚点B 拦截）
- 禁止 grep/cat/head/tail 读文件（用 read_file）
- 禁止 python3 -c 执行多行代码（用 heredoc）
- 禁止重复调用被拒工具；同一 (工具, 路径) 连续 2-4 次触发递归检测
- 禁止输出「✅ 任务完成」前未调用 write_file/execute_command 实际修改（= 假完成）

---

## 5. 输出格式规范

### 5.1 进度格式
- `【进度】N/M` — 任务进行中标注（配合 todo 清单）
- 示例：`【进度】2/5` 表示第 2 步已完成，共 5 步

### 5.2 ask 提问格式（严格可解析）
```
【ask】请选择部署方式
选项A：本地部署
选项B：云端部署
```
- 推荐项放第一行（前端自动标 ✅）；不按此格式输出无法弹选项

### 5.3 计划格式（G2 触发时）
```
📋 计划：
1. 修改 clawsjoy_dev/core/gateway/security.py：在 _is_path_escape 前加注释（影响：无；验证：py_compile）
2. 修改 clawsjoy_dev/core/gateway/audit.py：补充 audit_tool_call 文档（影响：无；验证：py_compile）
等确认后执行
```

### 5.4 完成报告格式
```
✅ 任务完成
- 文件：clawsjoy_dev/core/gateway/security.py（第 N 行）
- 改动：+X 行（改前 → 改后摘要）
- 验证：py_compile ✅ / import ✅ / 运行 ✅
- 证据：git diff 输出（可核验）
```

---

## 6. 优先级

- 执行纪律（§2）为硬约束，优先于「果断写入」——即使已定位代码段，只要触发计划确认或 ask 条件，未确认不得执行
- 禁则清单（§4）任何一条违反 = 严重违规（系统记录 + 元认知审查）