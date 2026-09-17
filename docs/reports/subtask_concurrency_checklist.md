# 子任务并发七轮调试经验 Checklist

> 生成时间: 2026-08-16 | 基于 v1-v7 实测 commit 历史（cd5ea12 → c23ce43）
> 适用范围: 任何"多线程 + 沙箱 + 文件操作"场景（子任务池/并行执行器/多 Agent 工作区）

---

## 一、七层问题清单

### L1 线程内变量未初始化（v1）

- **现象**: live 3 子任务全部 failed，错误 "cannot access local variable '_dw_res' where it is not associated with a value"
- **根因**: `_audit_cross_check_save(..., _dw, _dw_res)` 无条件引用 `_dw_res`，但仅在 `_dw` 非空（配置了 done_when）时赋值。普通任务 session 有 done_when → 不触发；**子任务 session 无 done_when → UnboundLocalError**
- **修复 commit**: `a58a609`（初始化 `_dw_res = None`）
- **验证方法**: live 创建 3 子任务观察状态（v1 全 failed → v2 进入执行阶段）
- **单测为何没抓到**: subtask_executor 单测 mock 了 `_execute_agent_task`，不触发真实 `_save_state` 的 done_when 段；真实执行路径只在 live 暴露

### L2 提示词路径语义误导（v2）

- **现象**: 沙箱出现嵌套目录 `subtasks/{id}/subtasks/{id}/result.md`
- **根因**: system prompt 说"你的工作目录是独立子任务沙箱（subtasks/{task_id}）"——LLM 把 `subtasks/{id}` 当**相对路径前缀**，而沙箱 base 已是 `subtasks/{id}` → 双重嵌套 → 工具路径错误 → LLM 反复重试
- **修复 commit**: `74e5893`（prompt 明确"当前沙箱根 = ., 写相对路径，不要加 subtasks/ 前缀"）
- **验证方法**: live 实测检查沙箱目录结构（不再出现嵌套）
- **单测为何没抓到**: LLM 对 prompt 的理解是运行时行为，单测无法模拟；路径解析单测用固定参数，不涉及 LLM 生成的路径

### L3 验证链与执行链目录不一致（v3）

- **现象**: write/read 均成功，但任务卡"超过最大轮次"——日志显示 VerificationChain passed=False + 审计复核"强制继续"
- **根因**: `run_verification_chain` 的 `base_dir` 写死 `data/projects/{uid}/{sid}` + `project_root="clawsjoy_dev"` → 查共享沙箱根；子任务文件在 `subtasks/{tid}/` 下 → `collect_written_files` 找不到 → step1_write.passed=False → 审计复核要求 write 失败记录 → 无 → 强制继续 → 死循环
- **修复 commit**: `9d35c2e`（sandbox_base 非 None 时 base_dir=subtasks/ 目录 + project_root=task_id）
- **验证方法**: live 日志 VerificationChain report 检查 step1_write.passed
- **单测为何没抓到**: 单测 mock `_execute_agent_task`，不触发真实 VerificationChain 调用；base_dir 参数传递只在真实执行暴露

### L4 路径锚点与 git 钩子不一致（v4，静态分析发现）

- **现象**: 静态分析（未跑实测）发现——git 钩子 `_sandbox_git_pre_write/post_write` 用共享 `_get_sandbox_base`（子任务 git 永不记录产出）；`_resolve_path` 分支 A 用固定 `parts[-3]/[-2]` 提取 uid/sid（子任务 base 多 2 层取错为 clawsjoy_dev/subtasks）
- **根因**: 多处代码硬编码"base = data/projects/{uid}/{sid}/clawsjoy_dev"假设，子任务 base 多 `subtasks/{tid}` 层即破坏
- **修复 commit**: `4cef848`（P1 两项：git 钩子加 sandbox_base 透传 + `data/projects/` 锚点定位 uid/sid + `_normalize_path` base_override）
- **验证方法**: 路径对照表 + test_subtask_path.py（4 用例）+ test_subtask_git_hooks.py（2 用例）
- **单测为何没抓到**: 既有 `_resolve_path` 单测只用共享 base（3 层路径），没覆盖子任务 base（5 层）；git 钩子测试不检查 cwd 参数

### L5 验证链 .py 限制 + 复核无审计项（v5）

- **现象**: 路径修复后 write/read 成功，但任务仍超轮次——日志 `content: 声称失败但审计无对应失败记录` 循环
- **根因**: ① `collect_written_files` git diff 检测只认 `.py` 文件 → 子任务写 `output_1.md` 不被 step1 识别 → claimed=False；② `cross_check_completion` 全项复核，VerificationChain 对非代码任务 step2/3 自动 passed=True 但审计无 execute_command 记录 → 复核失败
- **修复 commit**: `e7c4a8d`（去 .py 限制 + 只复核审计中出现的工具项）
- **验证方法**: live VerificationChain report 检查 step1_write.passed=True；单测验证复核跳过无审计项但保留 write 防线
- **单测为何没抓到**: ① collect_written_files 单测用 .py fixture（共享代码任务语义）；② 复核单测用共享 session 的真实审计（有 execute_command 记录），没模拟子任务"只 write 无 compile/run"的审计形态

### L6 内容核验关键词误判（v6）

- **现象**: step1_write passed=True 后仍超轮次——report 显示 step4_content "目标关键词命中 2/8，少于 4"
- **根因**: `content_verify` 关键词提取把任务**指令词**当内容关键词：spec 提取出 [请用, write_file, 工具写入文件, output_, 内容为, 子任务, 输出, 写完后确认完成] 8 个，子任务输出 "子任务3输出 值=3" 只命中 2 个 → `_need=8//2=4` 失败；且长连续中文 token（"工具写入文件"）精确匹配漏过滤 + write_file 英文 token 触发文件名相关性误判
- **修复 commit**: `14524ef`（noise/action 扩展 + 子串包含过滤）
- **验证方法**: 单测 content_verify 对子任务 spec 简单输出通过 + 空文件仍拦截
- **单测为何没抓到**: 单测 fixture 任务描述简洁（无指令词堆积），没模拟真实 spec 的"请用 write_file 工具写入文件 ... 写完后确认完成"指令句式；阈值边界（len//2）对短内容输出敏感

### L7 数据路径非致命缺陷（v7）

- **现象**: 主链路 done+归档成功后，日志 3 个告警——PosixPath 序列化失败 / subtasks str item assignment / task_progress integer 类型错误
- **根因**: ① `store_step_summary` json.dumps 遇 Path 对象；② .agent_state.json 的 subtasks 字段为 str 时 item assignment 失败；③ update_task_progress 调用方把 file_path 传入 step_number
- **修复 commit**: `c23ce43`（default=str / subtasks 类型重置 / step_number int 防御）
- **验证方法**: 全量测试 + live 日志复查（告警消失）
- **单测为何没抓到**: ① SAG store 单测不触达 DB 序列化路径；② subtasks 标记单测用结构干净的 .agent_state.json；③ update_task_progress 单测用正确类型参数

---

## 二、通用化原则（多线程 + 沙箱 + 文件操作）

| # | 原则 | 对应层 |
|---|---|---|
| 1 | **线程内变量初始化**：异步执行路径的局部变量必须在所有分支前初始化（尤其"配置存在才赋值"的变量）| L1 |
| 2 | **路径语义单一来源**：prompt/工具/验证链/归档必须共享同一路径基（相对 vs 绝对、前缀 vs 根）；任何"工作目录是 X"的提示词都可能被 LLM 当相对前缀 | L2/L4 |
| 3 | **验证链与执行链同目录**：验证器（检查文件存在/git diff）必须指向执行器实际写入的目录 | L3/L5 |
| 4 | **复核只核对真实发生的事**：审计复核只匹配审计记录中出现的工具；"声称了但没执行"与"执行了但审计丢"要区分 | L5 |
| 5 | **关键词/阈值对简单任务宽容**：内容核验的指令词过滤 + 子串匹配，避免简单输出任务误判 | L6 |
| 6 | **序列化/类型防御**：数据落盘路径加 default=str、字段类型防护、SQL 参数强转 | L7 |

---

## 三、下次做类似功能（如子任务池扩容）标准验证流程

1. **单元测试（隔离 mock）**：执行器状态机（queued/running/done/failed）、独立沙箱、归档/保留现场、路由——mock `_execute_agent_task` 与 `read_audit_records`（避免 audit 全局状态污染）
2. **静态路径对照表**：画出 git init / 文件写入 / git 钩子 / 验证链 / 归档五条路径的目录，确认一致（尤其 base 多层级时）
3. **真实执行引擎单任务**：不经 gateway 直接调 `_execute_agent_task`（sandbox_base 独立目录），验证 done_when/验证链/审计复核完整路径
4. **live 单任务**：确认无日志告警（重点：UnboundLocalError/路径嵌套/验证失败/序列化）
5. **live 并发 2-3 任务（错峰 5-6s）**：验证并行启动、独立沙箱不互相覆盖、git 基线含产出
6. **live 归档/保留现场检查**：done → archive/subtasks/{tid} 含产出 + git_log_snapshot；failed → 现场保留不清理
7. **日志噪音复查**：grep 关键告警词（UnboundLocal/PosixPath/item assignment/integer/复核未通过）
8. **全量回归 + 提交**：确认测试基线（当前 149 passed / 5 known-env）无回归

> 核心教训: 七轮全部靠 live 实测暴露——单测的 mock 隔离掩盖了真实执行链（LLM 路径理解、验证链参数、审计记录形态、数据落盘）的问题。下次测试设计要补"真实执行引擎路径"（第 3 步），而非只 mock。
