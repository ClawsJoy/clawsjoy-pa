# V9 审批/工具机制 vs Harness 架构差距（根本性问题诊断）

> 日期: 2026-08-30
> 背景: 连续多轮"打补丁"（B4 v1→v2→v3、evaluate 提示、越权引导、TTL 调整）仍未根治 —
> Agent 反复犯同类错误（重复读文件、evaluate 做交互、read_file 读 vault、确认后二次拒绝）。
> 根因不在单个 bug，而在 V9 的**审批模型与工具边界设计与 harness 有本质差异**。

---

## 一、Harness 审批机制的本质（代码核实）

来源: packages/shell/tool-pwsh/src/index.ts + 系统提示

| 特性 | Harness 行为 | 为什么根本性 |
|---|---|---|
| **一次一审批** | 每个命令独立审批；批准后立即执行该命令 | 无"确认后二次拒绝"：批准 = 执行该次命令的唯一通行证 |
| **拒绝即最终** | "a denial is final — do not set sandbox_permissions" | Agent 必须换方案，不可能用同一操作反复弹审批 |
| **升级配对** | sandbox_permissions ⇔ justification 成对出现 | 升级必须说明"为什么这个命令需要更宽权限"，强制 Agent 思考 |
| **前置审批** | 审批在 execute 之前 resolve，失败即 fail-closed | 不存在"审批过了但执行层又拦"的双层矛盾 |
| **失败原因直通** | ToolCallError 直接带 message 回传 | Agent 立即看到为什么失败，不需要猜 |
| **真实内容** | read 返回完整文件；截断显式标记 | Agent 基于完整上下文决策，不靠 500 字符预览猜 |

---

## 二、V9 的根本缺陷（按严重度）

### D1【架构】审批与执行双层矛盾
- V9: ApprovalGuard 审批通过 → `_resume_bridge_after_approval` 执行 write_file → **插件不知道已批准** → 相似度保护二次拒绝（21%/8%）
- Harness: 批准 = 执行，无二次判断
- 后果: "确认写入但失败"循环、用户困惑"点确认没反应"
- 修复方向: 批准状态注入执行上下文（`ctx.approved_paths`），执行层只认批准，不再二次拒绝

### D2【架构】Agent 没有能力边界意识
- V9: 一个任务 10+ 工具，每个工具独立防护（write_file 相似度 / execute_command 越权 / browser_local evaluate 写保护 / search_files 模式白名单），**防护靠"检测+拦截"而非"能力边界"**
- Harness: 工具即边界——bash 就是 bash，没有"用 python -c 绕过 write_file 审批"的路径
- 后果: Agent 反复试错被拒工具（search_files×3、evaluate×6、read_file vault×4），每次都从错误消息里学
- 修复方向: **工具收敛**——execute_command 禁写沙箱文件（写必须走 write_file）、browser_local evaluate 恒只读（交互只有 click/fill）、read_file 恒沙箱内（vault 只有 obsidian_knowledge）。让"绕不过"成为默认，而不是"拦得住"成为目标

### D3【架构】跨轮状态无稳定锚
- V9: 重复读计数（B4 v1 goal_id → v2 objective → v3 时间窗）都因"每个用户消息新建 goal"而不稳
- Harness: 会话状态 = 真实文件系统 + 会话日志，Agent 读什么、做了什么一目了然，无需"猜 Agent 是否重复"
- 修复方向: 不做"Agent 行为猜测"，改做**工具结果去重**——同 path 同 fingerprint 的 read 在 bridge 内只执行一次并返回"已读过"（幂等化），而非事后计数拦截

### D4【数据】三份知识副本互相漂移
- V9: SOP 在 沙箱 docs/reports/ + vault SOPs/ + live docs/reports/ 三份，Agent 改一份漏两份（5005 清理正是如此）
- Harness: 单一事实来源（当前工作区）
- 修复方向: **vault 为唯一真源**，沙箱 docs/reports 改为 vault 的同步镜像（启动时 cp），Agent 写 SOP 只走 obsidian_knowledge

### D5【UX】审批卡片与执行解耦
- V9: 前端卡片 → 后端 `_handle_write_approval` → 执行 → 结果回填，链路长、TTL/残留/重复渲染问题层出
- Harness: 审批内联在工具调用里，一个请求一个结果
- 修复方向: 前端卡片只发"批准 id"，执行结果走 SSE 事件流回（已有基础设施），卡片生命周期与 pending 严格绑定

---

## 三、根本性改造方案（分阶段，不再打补丁）

### 阶段 1：审批语义对齐 harness（最小架构改动，收益最大）
1. **批准状态注入执行**：ApprovalGuard 批准后，把 `approved_paths[session_id]` 写入执行 ctx；write_file 执行时检查 ctx 批准 → 跳过相似度/截断二次拒绝。**批准即执行，执行层不再有独立判断**
2. **拒绝即最终**：write_pending 被拒后，同一 tool_call_id 不再可重试（前端按钮 disabled + 后端幂等拒绝），Agent 必须换方案
3. **前置展示完整内容**：审批卡片展示完整 content（非 500 字符 preview），用户基于完整内容决策——Harness 就是这样（justification + 完整命令）

### 阶段 2：工具边界收敛（消除"绕过"路径）
1. execute_command 禁写沙箱文件（检测 write 类命令 → 拒绝并提示"用 write_file"）——堵死 python -c open() 绕过
2. browser_local evaluate 恒只读（已做，强化消息）——交互只有 click/fill/upload
3. read_file 恒沙箱内（已做，vault 提示）——vault 只有 obsidian_knowledge(read)
4. search_files 从 minimal 白名单移除已做——但需让 Agent 在 schema 层面看不到被拒工具（模式过滤已做，强化）

### 阶段 3：单一知识源
1. vault 为 SOP 唯一真源；沙箱 docs/reports 启动时从 vault 同步（只读镜像）
2. Agent 写 SOP 只走 obsidian_knowledge(update_sop)；文档类写入（非 SOP）走沙箱
3. 移除"Agent 改沙箱 SOP 却不同步 vault"的漂移路径（5005 事件根因）

### 阶段 4：跨轮状态幂等化（替代计数拦截）
1. bridge 内同 path 同 fingerprint 的 read 幂等：首次执行，重复返回缓存结果 + "[已缓存]" 标记
2. 不再"猜测 Agent 是否重复读"，而是让重复读无害（不消耗预算、不污染上下文）
3. 探索止损保留（那是防止 LLM 迷失，与幂等化不冲突）

---

## 四、本次先落地的部分（阶段 1 + 阶段 2 的 1/2/4）

本轮实施范围（不扩大）：
1. D1: write_file 批准状态注入（`ctx.approved_paths`）——根除"确认后二次拒绝"
2. D2-1: execute_command 写沙箱文件拦截（python -c open()/heredoc > 等）→ 引导走 write_file
3. D2-2: browser_local evaluate 消息已强化（上轮）——本轮验证并留
4. D4: vault 同步脚本（`obsidian_knowledge(sync_sops)` 或启动钩子）

> 阶段 3/4 涉及数据迁移与 bridge 重构，需单独评估。先让审批语义和工具边界根本对齐，观察一轮任务效果。
