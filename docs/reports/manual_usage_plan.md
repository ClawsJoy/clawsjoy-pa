# 「说明书用了但 Agent 不用」— 指示牌 + 按需注入方案

> 日期：2026-08-15
> 背景：R3/R4 已将 agent_manual.md 入库（编目✅ + 检索✅），但实证显示 Agent 从未主动 query manual。
> 依据：tool_flow 0 次 manual 调用 / agent_system.md 无引导 / precision_feed 不引用

---

## 〇、实证结论（先查了 Agent 是否会用）

| 检查项 | 结果 | 证据 |
|---|---|---|
| Agent 主动 query manual | ❌ 0 次 | tool_flow 中 manual 相关 0 条 |
| query_index 总调用 | 1 次（测试触发）| audit_event 中 query_index 仅 1 条 |
| agent_system.md 引导 | ❌ 无 | 只说「query_index 查 SAG」，无 entity_type='manual' |
| precision_feed 引用 manual | ❌ 无 | 变量驱动投喂未打通 |

**结论**：书的编目和检索都做好了，但：①没有指示牌（Agent 不知道有书）②没有按需注入（OS 不按任务把相关章节送到 Agent 面前）。两件事都没做，Agent 自然不用。

---

## 一、方案：三件事补齐

### 1. Prompt 指示牌（S，立刻见效）

在 agent_system.md 工具段加一句：

```
- 工具使用规范查询：执行写操作/验证/报告前，若不确定怎么做，先 query_index(query=任务关键词, entity_type='manual') 查阅操作手册对应章节。
```

**效果**：Agent 知道有书、知道怎么借。成本：1 行 prompt，零代码。

### 2. 变量驱动按需注入（M，核心）

precision_feed._load_asset 增加 manual 分支：

```python
if source == "manual":
    vars_ = extract_task_vars(task_name)  # #41 阶段3 已有
    chapters = query_entities(entity_type='manual', limit=20)
    matched = [c for c in chapters if any(v in c['entity_name'] for v in vars_['keywords'] + vars_['tokens'])]
    return render_matched(matched)  # 只注入命中的章节文本
```

**效果**：写任务 → 注入「工具清单 + 禁则清单」；验证任务 → 注入「完成标准」；不相关章节不注入。token 可控（对比全量 156 行）。

### 3. 禁则清单工具层硬约束（M，长期）

把禁则从 prompt 移到工具执行器（像锚点A/B 一样系统级拦截）：

| 禁则 | 现位置 | 目标位置 |
|---|---|---|
| 禁止 _*.py 脚本 | manual §4.1 | tool_router 拦截（_execute_sandbox_tool 检查路径）|
| 禁止 json.load/dump 改配置 | manual §4.2 | sandbox_write 拦截（content 含 json.dump 特征）|
| 禁止 open() 绕过写文件 | manual §4.3 | execute_command 拦截（open(*,'w') 模式）|
| 禁止高危命令 | manual §4.4 | security.py 已有（锚点B）|

**效果**：软约束（prompt 提醒）→ 硬约束（系统拒绝），与锚点A/B 同级。

---

## 二、优先级建议

| 优先级 | 项 | 工作量 | 理由 |
|---|---|---|---|
| P0 | Prompt 指示牌（§1）| S | 1 行改动，Agent 立刻知道有书 |
| P1 | 变量驱动按需注入（§2）| M | 解决「全量注入=没有指示牌」的根本问题 |
| P2 | 禁则硬约束（§3）| M | 长期可靠性，需评估误拦风险 |

---

## 三、风险与边界

| 风险 | 缓解 |
|---|---|
| 指示牌加了但 Agent 仍不查 | 指示牌放工具段显眼位置 + 禁则硬约束兜底（P2）|
| 按需注入匹配不准 | 变量驱动已有兜底：无匹配时退回全量或空 |
| 禁则硬约束误拦 | 逐条评估（_*.py 明确、json.dump 特征明确、open 写需谨慎）|

---

## 四、验收标准

1. agent_system.md 含 manual 查询引导，Agent 在不确定时主动 query_index(entity_type='manual')
2. 写任务时注入「工具清单+禁则清单」章节，验证任务时注入「完成标准」章节（非全量）
3. 禁则清单至少 _*.py 一条在工具层硬拦截（执行 _*.py 返回拒绝）
