# V9 自学习机制排查报告（2026-08-29）

## 一、现状盘点

### 1. known_issues/known_patterns 链路 — ✅ 完整工作
- 沉淀: remember_issue(连续失败≥8 暂停时, guards/registry L429) + remember_pattern(任务完成 reason=completed 时, agent_gateway L2679)
- 检索: precision_inject search_candidates L107(多源含 memory)
- 注入: 【跨会话记忆】agent_gateway L3037 + 【精准上下文】precision_inject(相关性评分排序)
- 数据实证: user-mt0q7ws8 4 issues + 20 patterns; web_1783219071801 9 issues + 20 patterns

### 2. platform_insights 回流→注入 — ❌ 断链(概念不存在)
- 代码中**无 platform_insights** 模块/字段(全库 grep 0 命中)
- 设计文档曾提 metacognitive_agent.get_insights, 但那是独立 agent 洞察, 未接入 V9 主流程
- closed_loop/smart_core/unified_analyzer 均为独立模块,**未被 agent_gateway 引用**

### 3. 风格画像 — ❌ 断链(死代码)
- core/bin/learners/creator_learn.py: learn_content_styles() 只统计视频数(print), 不建画像
- data/xhs_profile* 存在(旧产物), 但无代码读取/更新/用于内容生成
- self_learning_coordinator 可导入但未被 V9 引用(route_handlers 独立路由)

### 4. 任务结果反馈 — ⚠️ 半断链(仅成功侧)
- 成功: _update_sag_feedback(passed=True) L4064/L1282 + _update_sag_edge_learning L596(edge 评分: 用+0.1/未用-0.05/30天*0.95)
- **失败: _save_state("failed") 路径(L1101/1362/1394)无任何 feedback 调用**
- 数据实证: sag_feedback 104 条(全成功), task_feedback 边 **0 条**(edge_learning 可能从未真正写边, 或表名/条件不匹配)

### 5. 过滤网参数 — ❌ 全硬编码
- precision_inject.py: 0.05/0.1/0.3/60/min_score=0.1/top_n=5 全部硬编码
- execution_policy.yaml 无 precision 相关配置(仅 compaction_threshold 0.8 相关)
- 无法按用户/任务类型调阈值、权重、衰减

## 二、断链点汇总

| # | 机制 | 状态 | 断链位置 |
|---|---|---|---|
| 1 | known_issues/patterns | ✅ 完整 | - |
| 2 | platform_insights | ❌ 不存在 | 无模块, closed_loop 未接入 |
| 3 | 风格画像 | ❌ 死代码 | creator_learn 只 print; 无读取/生成 |
| 4a | 任务成功反馈 | ✅ 工作 | L4064/L1282 + edge_learning |
| 4b | 任务失败反馈 | ❌ 缺失 | _save_state(failed) 无 feedback |
| 4c | edge_learning 落库 | ⚠️ 可疑 | task_feedback 边 0 条(可能未生效) |
| 5 | 过滤网参数 | ❌ 固定 | 硬编码, 未配置化 |

## 三、最小闭环方案(按价值排序)

### A. 失败反馈闭环(最高价值, 补 4b+4c)
在 _save_state("failed") / on_fail 路径加:
```python
# execute_agent_task.py _save_state 失败分支
if status == "failed":
    _update_sag_feedback(last_user_msg[:80], session_id, user_id, messages, passed=False)
    _update_sag_edge_learning("save_state_failed", session_id, user_id, messages)
```
- 失败也沉淀: known_issues(已有 remember_issue 但仅≥8连续) + SAG 负反馈(weight-0.05)
- 验证 task_feedback 边 > 0

### B. 过滤网参数配置化(补 5, 中价值)
precision_inject 读 execution_policy.yaml:
```yaml
precision_inject:
  vault_min_score: 0.05
  memory_min_score: 0.1
  keyword_weight: 0.3
  decay_days: 60
  top_n: 5
  token_budget: 750
```
- 函数签名加 config 参数, 默认值不变(向后兼容)

### C. 风格画像最小版(补 3, 低价值起步)
把任务报告的【可复用经验】小节沉淀为风格画像:
```python
# precision_inject.write_task_review 时顺带更新
def update_style_profile(user_id, report_text):
    # 提取 可复用经验 → 更新 data/projects/{uid}/style_profile.json
    # 注入时【风格画像】带入内容生成
```

### D. platform_insights(补 2, 明确取舍)
若需要: 新建 platform_insights 模块, 从 browser_local 的 monitor 数据回流
(发布成功/失败/互动数据 → insights), 注入时带平台洞察。当前可跳过(无数据源)。

## 四、建议实施顺序
1. A(失败反馈, 最小改动 2 处) → 立即验证 task_feedback 边增长
2. B(参数配置化, 3 处函数签名) → 可调优
3. C(风格画像, 复用已有复盘写入) → 渐进
4. D(platform_insights) → 待数据源确认后

,---,,# A+B 实施验证（2026-08-29）,,## A: 失败反馈闭环（已完成 + 验证）,- execute_agent_task.py _save_state(status="failed") 分支加:,  - _update_sag_feedback(passed=False) → SAG 负反馈(feedback_value=-1.0),  - _update_sag_edge_learning("save_state_failed") → 边缘降权,  - remember_issue → 失败沉淀 known_issues(用户级),- 验证: 模拟失败反馈落库成功 — steps_summary 记录 passed=False, feedback_value=-1.0,- 注意: 需 DATABASE_URL env(网关运行时已具备); extractor 代理无 env 时抛错被 except 吞(真实运行时容器已注册 OK),,## B: 过滤网参数配置化（已完成）,- execution_policy.yaml 新增 precision_inject 段:,  vault_min_score 0.05 / memory_min_score 0.1 / report_min_score 0.05 /,  keyword_weight 0.3 / decay_days 60 / min_score 0.1 / top_n 5 / token_budget 750,- precision_inject.py: _inject_cfg() 读配置(带缓存+reset);,  search_candidates/filter_and_rank/get_precision_context 全参数化, 默认值保持向后兼容,,## 测试,- test_precision_inject.py 14 项(新增 3: 配置读取/覆盖/默认保持),- test_failure_feedback.py 2 项(源码断言 failed 分支含反馈调用),- 全量回归 669 passed,
