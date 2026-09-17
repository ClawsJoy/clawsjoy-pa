---
type: design
tags: [Harness, 自学习, 自动落盘, 模式库, 评估]
created: 2026-09-05
status: draft-待确认
---

# Harness 自动落盘 + 自学习闭环 — 实现方案评估

> 实查依据: DSH 源码 packages/hooks(hook-protocol: HookInvocation{turn, point: PreToolUse/Stop…}, 按次调用/可 detached) 与 packages/goal(GoalOperation 含 complete + GoalChangeMeta); 本会话可用通道已验证(vault write_vault_note 原子写 + Harness专栏 4 篇在库)。

## 1. 可行性结论

- **部分可行(分层)**: DSH 平台确有 hook 协议与 goal 完成事件, 但均为 **host 配置面**(hooks 由宿主注册 handler, goal change 事件在 host 层), **会话内 agent 无法自注册完成 hook**。
- 对「Harness 每次任务完成后自动落盘」, 现实可用触发器三层:
  1) **目标收尾纪律(主通道)**: 每个目标(goal)固定末步 todo『closure: 修复报告+自学习』; 完成目标前执行 helper——与 canary 纪律同级, 可靠但依赖纪律。
  2) **异步完成信号(增强)**: 后台 subagent 结算时运行时会向父 agent 推送完成通知 → 该通知即『子任务完成』hook, 可在收到后自动执行落盘(无需等人工)。
  3) **平台级(远期/可选)**: 由用户/宿主按 hook-protocol 注册 host hook(如 point=Stop 后调用落盘脚本), 脱离 agent 纪律; 需在 host 配置层实施。

## 2. hook 触发方案(推荐组合)

- 交付物: sandbox 放 `harness_closure/` 脚本 + 模板(已在 Harness专栏/Templates)。
- 触发: 目标创建时自动追加末 todo『落盘 closure』(沿用 goal→todo 的每轮纪律); 收到后台 subagent 完成通知且涉及修复时, 立即跑 closure(修复报告 + 自学习候选)。
- 幂等: 每次 closure 先读 Harness专栏/修复报告 是否已含同主题文件(文件名含主题+日期去重), 已有则不重写。

## 3. 自学习挖掘流程

1. 输入: Harness专栏/修复报告/*.md(问题/根因/修复/验证/经验) + 会话/governance 记录。
2. 挖掘: 用 workflow/subagent(LLM)按统一 schema 产出候选模式: {pattern_key, title, root_cause, fix, verify, counterexample, evidence:[报告链接], tags}。
3. 合并去重(见 §5) → 保留/新建模式条目。
4. 呈现: 模式库 md + 索引; 计数与最新日期随证据追加更新。
5. 复核: 每次收敛后(如 S 系列末)人/主 agent 确认新增模式质量(防幻觉: 每条必须带 evidence 双链, 无证据不收录)。

## 4. 模式库结构(按模式主题, 非按日期)

Harness专栏/自学习/
- INDEX.md — 全库模式索引(pattern_key → 文件 → 计数 → 最新日期)
- .patterns.json — 机器注册表: {key, title, embedding, file, count, last_updated}(去重与检索用)
- <pattern-slug>.md — 每模式一文件: frontmatter(type: harness-learning + pattern_key + count + last_updated) + 定义 + 证据表(每条: 来源报告+根因→修复→验证→反例)

理由: 模式跨日期复现(如 TOCTOU/补丁效应会多轮出现), 按日期会产生重复文件 → 主题文件 + 追加证据行 + 计数递增。

## 5. 去重策略(判断『相同模式已存在』)

1. pattern_key 规范化: 中文锚词 kebab(如 atomic-write / patch-effect / fake-complete)。
2. 语义去重: 本地 nomic-embed-text(127.0.0.1:11434) 对 {root_cause+fix} 编码, 与 .patterns.json 存量比较: 余弦 ≥0.88 → 视为相同 → **更新既有条目**(追加 evidence 行、count+1、更新 last_updated/反例), 不新建文件; <0.88 → 新建。
3. 无嵌入服务时降级: pattern_key 精确匹配 或 LLM 单问二分类(与候选 top3 是否同模式)。
4. 覆盖式防误并: 若 LLM 复核认为不同但余弦≥阈值 → 拆新 key(记录人工裁决位)。

## 6. 与既有资产衔接
- 已有: Harness专栏/修复报告 4 篇(含 R/L/S 汇总) + 自学习 1 篇(修复模式提取, 8 行表) → 首次挖掘以 5 篇为种子, 迁移进 .patterns.json 并去重(避免与既有表重复)。
- V9 互操作: INDEX.md/.patterns.json 可被 obsidian_knowledge search/read 检索; V9 修复前可查 pattern_key。

## 7. 落地步骤(确认后实施)

P1 closure helper + goal todo 纪律(自动写修复报告; 模板已就绪) — 半天
P2 模式注册表(.patterns.json) + 嵌入去重 + 挖掘 workflow(subagent schema) — 1 天
P3 首次种子挖掘: 现有 4 修复报告 + 治理/诊断 → 生成模式库+INDEX+反例 — 半天
P4 后台通知 hook 消费 + 幂等防重 + 每轮回归(canary) — 1 天

验收: 修复轮结束 → 报告自动落盘; 同类修复第二次 → 自学习同条目 count+1 而非重复文件; 全量回归绿。
