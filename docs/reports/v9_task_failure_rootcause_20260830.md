# 知乎发布总结任务失败根因分析（2026-08-30）

> 任务: "总结本次知乎发布的不完善点，写进 SOP"
> 现象: Agent 5 轮 × 32 工具调用全部耗尽, 始终在翻 goal JSON / 目录遍历, 未完成 SOP 更新。
> 根因: 4 个系统性缺陷叠加, 不是 Agent 单方面"不努力"。

---

## 根因链

### R1【高】ForcedToolGuard 误判 — "完善"关键词误伤读工具
- `core/gateway/guards/registry.py` ForcedToolGuard 的 `_action_words = ["修改","修复","新增","重写","实现","完善","添加"]`
- 任务指令"总结**不完善**点"含"完善" → 被判定为"代码修改任务"
- 效果: `read_file`/`list_dir`/`search_files` 全被拒("当前任务要求代码修改，禁止仅使用读取工具")
- 后果: Agent 无法正常读文件 → 只能用 `execute_command awk/cat` 绕行 → 预算 5 倍消耗
- **证据**: 日志中 `list_dir( data/plans/...)` 和 `read_file( docs/reports/zhihu_publish_sop.md)` 均被此守卫拒绝

### R2【高】复盘记录不可达 — obsidian_knowledge read 不支持 Reviews
- `read_knowledge_file()` 只支持 4 个 SOP key + 避坑清单
- vault `Reviews/` 有完整复盘(`2026-08-30-8060425102_5.md` 等), 但 Agent 无法通过工具读取
- 后果: Agent 想找"上次发布漏了什么" → 只能翻 goal JSON(目标文本) 和日志 → 5 轮迷失
- **证据**: 日志 5 轮反复 `read_file( goals/goal_web_...json)` 十余次, 每个 goal 文件读 2-3 遍

### R3【中】任务上下文无复盘注入
- precision injection 只注入 vault 检索结果(SOP/避坑), 不注入最近 Reviews
- Agent 没有"上次发布复盘"的上下文锚点, 只能自己找且找不到

### R4【中】绕行放大
- R1 迫使 Agent 用 execute_command 读文件(awk/cat/python -c print)
- 每次绕行消耗 2 步预算, 且绕行结果未经 read_file 语义化(无缓存/去重)

---

## 根本性解决方案

### F1: ForcedToolGuard 关键词收窄 + 读工具永远可用
- 移除"完善"等文档类词; 或改为: 用户消息含修改词 **且** 明确指代码/文件(如"代码""函数""bug""模块")才禁读
- 根本原则(harness): **读工具永不禁用** — Agent 读文件是必要前置, 强制"直接写"是反模式
- 若任务确需写(如"写 SOP"), 审批卡片已提供保护, 无需禁读

### F2: obsidian_knowledge read 支持 Reviews(复盘)
- read 的 sop_key 支持 `Reviews/<文件名>`(去 .md), 返回复盘全文
- Agent 任务前可读上次复盘 → 不再翻 goal JSON

### F3: 任务上下文注入最近复盘
- precision injection 在检索结果中加入最近 2 条 Reviews(任务相关度排序)
- Agent 天然知道"上次发布发生了什么", 无需自己找

### F4: 读工具幂等/缓存(承接 D4 阶段4)
- bridge 内同 path 同 fingerprint 的 read 只执行一次, 重复返回缓存 + "[已缓存]"
- 消除"反复读同一 goal JSON"的预算浪费(不靠事后计数拦截, 靠幂等无害化)

---

## 实施范围(本轮)
1. F1: ForcedToolGuard 关键词修复 + 读工具放行原则
2. F2: read_knowledge_file 支持 Reviews
3. F3: precision injection 注入最近 Reviews
4. F4 列入下阶段(涉及 bridge 重构, 单独评估)
