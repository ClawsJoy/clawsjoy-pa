# V9 Agent vs DeepSeek Harness 架构对比（同一模型 deepseek-v4-flash）

> 日期: 2026-08-30 | 模型相同, 行为差异巨大 — 差异在**工程架构**而非模型能力。
> 方法: 读 harness 源码(packages/shell, interaction, fs, subagent, llm/agent-loop) +
>       今天 V9 全链路修复实践 + 双环境实测。

---

## 一、工具集对比（能力边界）

| 维度 | Harness | V9 Agent |
|---|---|---|
| 工具数量 | **~15 个精简工具**（bash/read/write/edit/grep/glob/run_code/web_search/skill/subagent/ask_user/ralph/workflow/session_search） | **10+ 工具 + 模式白名单动态增减**（read_file/write_file/execute_command/list_dir/search_files/fetch_web/browse_web/browser_local/web_search/obsidian_knowledge） |
| 文件工具 | read/write/edit/grep/glob **各自独立、语义单一** | read_file/list_dir/search_files 混合；write_file 内含相似度/截断/行号/JS回滚 5 种保护 |
| **工具即边界** | 每个工具能力精确（bash 就 bash；fs 只有 read/write/edit；无"绕行"路径） | **边界靠检测拦截**：execute_command 可绕行写文件（python -c open）、browser_local evaluate 可做交互 → 需层层守卫补 |
| 搜索 | web_search 内置（bing/ddg 双源） | 今天刚加 web_search（Bing RSS 单源），fetch/browse 兜底 |
| 知识 | 无内置第二大脑（靠 session 持久化） | obsidian_knowledge（vault SOP/复盘/剪藏） |

**核心差异**: harness 是"**能力精确分层**"——Agent 只能用它有的工具做对应的事, 没有绕行可能。
V9 是"**能力全开 + 检测拦截**"——execute_command 什么都能干, 于是需要写守卫堵它（今天修的 python -c 绕过就是例子）。

---

## 二、审批机制对比（今天修复的核心）

| 维度 | Harness | V9（修复前 → 修复后） |
|---|---|---|
| 模型 | **一次一审批, 批准即执行**（approveEscalation: requestedMode+justification → approver） | 审批与执行双层: 确认后 write_file 又相似度拒绝（→ 已修: 批准即执行） |
| 拒绝 | **拒绝即最终**（"a denial is final", 无重试） | 拒绝后可换方案重试（合理）但之前过期假成功（→ 已修: write_expired） |
| 升级 | sandbox_permissions ⇔ justification **成对出现**, 强制说明理由 | 无升级概念; 所有写都审批（→ 已修: data/tmp 免审批分级） |
| 粒度 | 命令级/文件级独立审批, 沙箱内自由 | 之前 55次/h 轰炸（→ 已修: 分级 + TTL 300s + 卡片去重） |
| 权限模式 | workspace-write / danger-full-access **预设**（permission-presets） | 无预设, 只有"要审批/不要审批"两档 |
| 审计 | approval/resolved 事件广播 + 会话持久化 | _record_approval 落盘 ✓ |

**核心差异**: harness 审批是**工具调用内联的原子操作**——Agent 调 bash → 沙箱拒绝 → 同一调用带 justification 重试 → 用户一次批准 → 该命令立即执行。V9 之前是"卡片 → 后端 → 再执行"的分离链路, 产生 TTL/重复渲染/二次拒绝一堆问题。

---

## 三、执行循环与上下文管理

| 维度 | Harness | V9 |
|---|---|---|
| 循环 | dsh-agent-loop: LLM 调用 → 工具执行 → 结果回填 → 下一轮, **无工具数量上限**（受 token 预算约束） | _v9_bridge_loop: **32 工具/轮上限**, 5 轮/任务（total=160）→ Agent 常被预算打断 |
| 上下文 | 会话持久化(jsonl) + session_search 回溯; **不主动压缩**, 靠模型窗口 | message_assembler **主动压缩**(keep=8 热窗口 + 摘要), 压缩后 Agent 丢失细节（日志反复重读文件） |
| 目标 | 无内置 goal 系统（用户指令即目标） | goal 系统 + 目标隔离（每消息新建 goal → 跨轮状态锚不稳, 今天修的） |
| 工具结果 | 完整返回(截断有显式标记) | 2000 字符截断 + 摘要（"read_file 返回了摘要"日志出现多次）→ Agent 重读 |
| 预算 | 无"轮次上限", 超 token 自然停 | **轮次硬上限**(32×5), Agent 常"已达标轮上限, 以下为已有产出"半途输出 |

**核心差异**: harness 让 Agent **自然收敛**（上下文真实 + 无预算打断）; V9 用**外部强制**（压缩 + 轮次上限）——外部强制反而制造了"重读文件/半途产出"等新问题。

---

## 四、失败处理与自我修正

| 维度 | Harness | V9 |
|---|---|---|
| 失败反馈 | ToolCallError **带 message 直通**, Agent 立即看到原因 | 之前失败原因不注入（→ 已修: 确认后失败注入指引） |
| 递归防护 | 无（工具边界天然防绕行） | check_recursion 按 tool+path 计数, 需防误伤（今天修 evaluate/web_search key） |
| 迷失检测 | 无专门机制（工具少 + 上下文真实 → 不易迷失） | 探索止损 + 漂移检测（今天加）——因为工具多 + 上下文压缩导致容易迷失 |
| 重试 | Agent 自行决定（看到错误自己改） | 之前自动重试 + 反复弹审批（→ 已修） |

---

## 五、知识沉淀（第二大脑）

| 维度 | Harness | V9 |
|---|---|---|
| 模型 | 会话持久化 + subagent 报告; 无跨任务知识库 | Obsidian vault: SOPs/Reviews/Pitfalls/Clippings 四类 |
| 自动沉淀 | 无（用户主动组织） | **自动**: 任务完成写复盘 + 抓取即剪藏 + 踩坑自动入避坑清单 |
| 检索 | session_search（会话内） | precision injection（任务词 → vault 多源检索注入） |
| 单一真源 | 天然（单工作区） | 今天修: vault 唯一真源, 沙箱镜像单向同步 |

**V9 在知识沉淀上领先 harness**——这是 V9 为"持续运营型"场景设计的好处（harness 偏"单次任务型"）。

---

## 六、根因总结：为什么同一模型行为差异大

### 根因 1【架构】能力边界 vs 能力全开
harness 工具**少而精确**（15 个），Agent 行为被工具边界塑造；V9 工具**多而重叠**（execute_command 万能），Agent 有无数绕行路径 → 需要海量守卫补洞（今天修了 15+ 个守卫缺陷）。

### 根因 2【架构】内联审批 vs 分离审批
harness 审批是工具调用的一部分（一次一决）；V9 审批是独立链路（卡片→后端→执行）→ 产生 TTL/重复/二次拒绝。

### 根因 3【架构】自然收敛 vs 外部强制
harness 无轮次上限 + 上下文真实 → Agent 自然完成；V9 32×5 预算 + 压缩 → Agent 被强制打断/丢失上下文 → 重读、迷失。

### 根因 4【环境】单一事实源 vs 多副本
harness 单工作区；V9 沙箱/vault/live 三副本 → 漂移（今天修单一真源）。

### 根因 5【定位】单次任务 vs 持续运营
harness 偏"一次对话完成一个任务"；V9 偏"长期运营账号/知识积累"——V9 的 goal/复盘/剪藏是优势，但复杂度也带来守卫负担。

---

## 七、V9 可借鉴的根治方向（非补丁）

| 方向 | 借鉴 harness | 落地 |
|---|---|---|
| 1. 工具收敛 | execute_command 禁写文件（写只能 write_file） | 今天已做（python -c 写检测），可进一步禁 heredoc 写 |
| 2. 审批内联化 | 审批作为工具调用参数（justification 内联） | 长期: 卡片 → 工具参数内联 |
| 3. 轮次上限柔性化 | 不用硬 32×5, 改 token 预算自然停 | 中期: 调大或改 token-based |
| 4. 上下文真实化 | 减少主动压缩, 依赖模型窗口 + 会话回溯 | 中期: read 缓存幂等化替代压缩 |
| 5. 单一真源已修 | vault 唯一 | ✓ 今天完成 |
