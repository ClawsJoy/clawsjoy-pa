# V10 Agent 内容生成质量提升设计方案

> 版本: v1.0 | 日期: 2026-08-07 | 依据: V10 第 4 轮回归测试（e2e_v10_r4_30t_report_fix1.json）
> 背景: git 误判已清零，但完成率仅 3.3%（1/30），22 个任务因"Agent 创建了文件但内容不达标"失败

---

## 1. 第 4 轮回归数据总览

| 指标 | 数值 |
|---|---|
| 总任务 | 30 |
| 完成（done） | 1（3.3%） |
| 语义失败（error，内容不达标） | 22（73.3%） |
| 创建异常（create_unexpected，反问误触发） | 7（23.3%） |
| git 误判 | 0（已清零） |
| 平均重试 | 约 1.27 次/任务，最大 3 次 |

22 个语义失败任务全部在节点级被 Verifier 判定失败（score 0.0 ~ 0.3，阈值 0.4），
无一进入最终验证环节；7 个创建异常是 plan() 反问机制误触发，未进入执行。

---

## 2. 22 个语义失败根因分布

### 2.1 按失败位置分类

| 类别 | 数量 | 占比 | 任务 |
|---|---|---|---|
| A. task1 即失败（后续节点全 blocked） | 15 | 68% | PC1/PC2/PC3/PC4/PC6/PC7/PC8/PC10、PF2/PF5/PF6/PF8/PF9/PF10、FA3 |
| B. 前面节点通过、后续节点失败 | 7 | 32% | PC5(task2)、PC9(task4)、PF3(task2)、PF4(task2)、PF7(task2)、FA1(task3)、RA2(task4) |
| C. 全部节点 done 但最终失败 | 0 | 0% | —（PC9/RA2 均止于最后一个节点） |

### 2.2 按根因子类分类（22 个语义失败 + 7 个创建异常）

**R1. Verifier 判定对象错位 —— 判定"输出文本"而非"真实产物"（约 12 个）**
- 节点 Verifier 对比的是 Agent 的 final 输出文本与步骤目标（verifier.py `_check_semantic`），
  不读取文件系统上的真实文件内容。
- Agent 只要"描述得像"即可得分：PC9 前 3 个节点全部 score=1.0 放行，
  但第 4 节点（真实产物核验）立即失败——"缺少 'Hello!' 字符串的返回"。
- 典型：PC1 要求 greet('world')→'Hello, world!'，Agent 只写 print('Hello, ClawsJoy!')，
  无 greet 函数，但输出文本描述"已实现 greet"。
- 证据：PC6"输出没有直接表明文件是否创建成功"、PF4"缺少文件实际存在的验证"、
  PF7"没有直接确认 backup 目录的存在"、PF10"未直接验证操作结果"。

**R2. done_when 质量差 —— Planner 生成条件模糊/错位（约 10 个）**
- plan() 默认 done_when = "task X 完成"（run.py L341）；LLM 自由生成的 done_when 也常为模糊文本。
- 部分节点目标被拆成"检查"而非"创建"："目标是检查 data/ 目录是否…"（PF2）、
  "目标是通过 ls 检查到 scripts/…"（PF9）——Verifier 依据错位目标判定必失败。
- done_when 缺少机器可验证的验收点（文件路径 + 符号名）。

**R3. 反馈不结构化 —— 重试盲目（15 个 A 类均受影响）**
- 重试反馈仅一句 deny_reason = "上次执行未满足条件：%s。实际产出：%s。请修正"（run.py L1850），
  未告诉 Agent"缺哪个符号、应如何实现、如何验证"。
- 15 个 A 类任务首节点失败后，重试仍在同一问题打转，最终 3 次重试耗尽。

**R4. 缺少 Few-shot Examples —— 抽象指令约束力不足（15 个 A 类 + PC5）**
- System Prompt 只有文字指令（run.py L1743-1751"代码生成质量标准"），无完整示例。
- 7B 级模型（qwen2.5:7b）对抽象指令执行力弱：PC5 实际写入了代码但 task2 出现
  "[AST] 代码块 #0 语法错误"，说明生成质量不稳定，需要"目标→正确产物→验证→final"示例引导。

**R5. 节点判定与最终判定标准不一致（PC9/RA2）**
- 节点 done 靠"文本语义"（Verifier 宽松放行），最终 done 靠"报告 vs 用户目标 + git 变更"
  （run.py L577/L2094 收紧），两层标准错位，Agent 以为完成了但最终不通过。

**R6. 反问误触发 —— readonly/analysis 任务被误判模糊（7 个）**
- plan() 模糊检测要求目标文本含"动作词 + 文件路径"（run.py L297-307），
  "列出目录结构/分析 CSV"等 readonly/analysis 任务天然不含 .py/.md 路径，被误判 need_clarification。
- 影响任务：FA2/FA4/FA5/RA1/RA3/RA4/RA5。

### 2.3 根因链路图

```
用户目标
   │
   ▼
plan() LLM 拆解 ──R2──▶ done_when 模糊/错位
   │                        │
   ▼                        ▼
task_spec.md 说明书      Agent 执行（仅文字指令，无示例 ──R4）
   │                        │
   ▼                        ▼
节点 Verifier 判定"输出文本"──R1──▶ 描述好≠做到，宽松放行
   │                        │
   │                        ▼
   │                   重试反馈仅一句 deny_reason ──R3──▶ 盲目重试 3 次耗尽
   ▼
最终判定（报告 vs 目标）──R5──▶ 与节点标准错位
```

---

## 3. 设计方案

### 3.1 说明书驱动升级（Spec-Driven，解决 R2/R5）

**目标**：done_when 从"模糊文本"升级为"机器可验证的验收条件"，说明书成为唯一验收依据。

1. **done_when 规范化（规则引擎，不依赖 LLM）**
   - plan() 拆解完成后，用规则从用户目标提取 `{文件路径, 函数/类/变量名, 内容关键字}`，
     生成三类机器可验证条件（优先级递减）：
     - `check:python_symbol=<path>|<symbol>`：AST 提取文件中函数/类定义，与符号清单比对（代码类任务）
     - `check:file_exists=<path>`：文件存在且 size>0（文件类任务）
     - `check:contains=<path>|<substring>`：文件包含指定内容（配置/内容类任务）
   - 禁止默认"task X 完成"；LLM 生成的 done_when 仅为候选，规则引擎最终裁决。
2. **task_spec.md 增加 acceptance 段**
   - 每个节点写入 `acceptance:` 子段：必含符号清单、验证命令模板、验收文件路径。
   - Agent 启动时强制解析（复用 run.py L1490 已有说明书读取机制），
     把 acceptance 注入 System Prompt，作为"必须逐项勾选"的清单。
3. **节点/最终判定标准统一**
   - 节点 done 判定 = 该节点所有 check 条件通过（规则检查器，不依赖 LLM）。
   - 最终验证 = 各节点 check 汇总全部通过 + git 变更文件覆盖声明的目标文件；
     移除"报告 vs 用户目标"的独立 LLM 最终判定（run.py L577），消除两层标准错位。

### 3.2 Few-shot Examples（解决 R4）

**目标**：给 7B 模型具体可模仿的"目标→产物→验证→final"完整闭环示例。

在 System Prompt 的 `_codegen_hint`（run.py L1743）之后追加 3 个完整示例：

- **示例 1（代码函数类）**：目标"创建 hello.py 实现 greet('world')→'Hello, world!'"
  → 正确 write_file 调用（含 greet 函数定义，无 print 占位）
  → 验证命令 `python3 -c "from hello import greet; print(greet('world'))"`
  → final 报告必须引用
  验证命令的 stdout（必须包含目标返回值），证明"真实产物"达标而非仅描述。
- **示例 2（文件创建类）**：目标"创建 logs/ 目录和 app.log 文件，内容写一行 'start'"
  → 正确 write_file/execute_command 调用 → 验证命令 `ls -la logs/ && cat logs/app.log`
  → final 报告引用验证输出（目录存在 + 文件内容为 start）。
- **示例 3（分析报告类）**：目标"分析 CSV 并输出结论"
  → 读取文件 → 输出结论 → 落盘 report.md → final 报告引用 report.md 路径。

示例均遵循统一模板：`目标 → 工具调用序列（写文件→验证）→ final 报告（引用验证证据）`。
预计增加 prompt 约 800~1200 token，在可控范围。

### 3.3 结构化验证反馈（Structured Verification Feedback，解决 R1/R3）

**目标**：Verifier 从"看描述打分"改为"看真实产物+给具体修复指引"，重试从盲目改为定向。

1. **判定对象切换为真实产物**
   - Verifier 判定前，从 done_when 解析目标文件路径，读取文件真实内容 + AST 提取符号清单，
     一并注入 LLM 判定 prompt（对比对象 = 真实产物 vs 目标，而非 Agent 描述 vs 目标）。
   - 新增内置规则检查器 `check:python_symbol`：AST 提取函数/类定义，与目标符号比对，
     缺符号直接失败（不依赖 LLM，确定性判定）。
2. **失败反馈结构化（JSON 回灌）**
   - 判定失败时返回结构化 JSON（替代现有单句 deny_reason）：
     ```json
     {
       "passed": false,
       "missing": ["greet"],                       // 缺失符号清单
       "errors": ["file_utils.py 未创建"],          // 具体错误
       "evidence": {"file": "hello.py", "symbols_found": ["print"], "content_head": "..."},
       "fix_hint": "在 hello.py 中定义 def greet(name): return 'Hello, ' + name + '!'"
     }
     ```
   - 复用 run.py L1861-1862 已有的反馈回灌通道，将结构化 JSON 作为下一轮 user message，
     Agent 直接知道缺什么、怎么改、怎么验证。
3. **证据链要求（Evidence Chain）**
   - final 前强制要求 Agent 提供验证证据：对代码类任务必须执行
     `python3 -c "from <file> import <symbol>; print(<symbol>(<arg>))"` 并引用 stdout；
     对文件类任务必须执行 `ls`/`cat` 并引用输出。
   - 证据缺失 = 未达 done_when（由 check 条件裁决，不靠 LLM 猜测）。

### 3.4 反问误触发修复（解决 R6）

- plan() 模糊检测前先做任务类型识别：目标含"列出/查看/分析/统计/比较/只读/目录结构"等词
  → 判定 readonly/analysis 类型，跳过"文件路径"硬要求。
- readonly/analysis 任务 done_when 统一为 `check:file_exists=<sandbox>/report.md`（报告落盘非空），
  不要求代码变更（与 run.py L2057-2058 已有分类逻辑对齐）。

### 3.5 实施顺序（低风险优先）

| 阶段 | 改动 | 位置 | 风险 |
|---|---|---|---|
| P0 | 反问放宽（3.4） | run.py plan() | 低，独立可测 |
| P0 | check:python_symbol 检查器（3.3-1） | engine/workflow/verifier.py + run.py _check_done_when | 低，确定性逻辑 |
| P1 | done_when 规范化规则引擎（3.1-1） | run.py plan() | 中，需回归 |
| P1 | Few-shot 注入（3.2） | run.py _codegen_hint | 低，Prompt 模板 |
| P1 | 结构化反馈 JSON（3.3-2/3） | verifier.py + run.py L1850 | 中，需回归 |
| P2 | 节点/最终判定标准统一（3.1-3） | run.py L577/L2094 | 中高，最后实施 |

---

## 4. 方案可行性与预期提升

### 4.1 可行性评估

| 维度 | 评估 |
|---|---|
| 技术可行性 | 高。全部复用现有机制（task_spec.md 说明书读取、deny_reason 回灌通道、_check_done_when 分支、git 变更核验）；check: 前缀判定框架已存在（run.py L1999-2041） |
| 模型约束 | 7B 模型语义判定不稳 → 方案核心用**规则检查器**（AST 符号比对/文件存在/包含）承担确定性验收，LLM 仅作辅助；这正是 V5/V8/V9 教训的直接应对——不依赖 Prompt 约束，靠引擎硬校验 |
| 改动量 | 引擎侧约 300~500 行（run.py + verifier.py），Prompt 模板约 100 行；无架构变更 |
| 回归成本 | 需第 5 轮 30 任务回归验证；P0 改动可先行单独验证（7 个反问任务 + PC 类代码任务） |
| 风险 | LLM 语义判定仍是长尾风险（复杂任务）；few-shot 增加 token 成本；统一判定标准可能暴露更多真实失败（短期完成率可能先降后升，属正常现象） |

### 4.2 预期提升幅度（对照第 4 轮 3.3%）

| 失败类别 | 数量 | 预期挽救 | 挽救数 | 依据 |
|---|---|---|---|---|
| D. 反问误触发 | 7 | 70~85% | 5~6 | readonly 任务简单，放宽反问后大概率完成 |
| A. task1 失败 | 15 | 60~75% | 9~11 | done_when 规范化 + 结构化反馈 + few-shot 直击根因 |
| B. 后续节点失败 | 7 | 50~70% | 4~5 | check 检查器 + 证据链要求 + few-shot 修正语法/证据 |
| 完成基线 | 1 | — | 1 | 现有 PF1 |

- **保守预期**：完成 14~17 / 30（47%~57%），较 3.3% 提升 14~16 倍
- **乐观预期**：完成 18~21 / 30（60%~70%），较 3.3% 提升 18~20 倍
- **不变量**：本轮修复不依赖 git 判定（已清零），提升全部来自内容质量链路，可直接对照第 5 轮回归验证

### 4.3 验证指标

第 5 轮回归重点观察：
1. 完成率（目标 ≥ 50%）
2. 语义失败中"缺少符号/验证证据"类占比（应显著下降）
3. 节点重试次数（结构化反馈后重试应更少且更有效，平均重试 < 1.0）
4. create_unexpected 清零
5. PC1（greet 案例）作为最小可复现用例先行验证

---

*本文档为设计方案，未修改任何业务代码。*
