# ClawsJoy 说明书驱动 × 落盘检索 统一体系设计方案

> 日期：2026-08-15
> 定位：回答"说明书驱动推进如何 + Harness 图书馆模式落地"——先体检数据，再设计统一体系
> 原则：写实（以落盘体检为据）、可执行（分优先级落地）、Harness 式（说明书先行 + 全量落盘可检索）

---

## 〇、结论先行

**说明书驱动推进情况**：BRIEF 是说明书（任务说明书），agent_system.md 是执行说明书（纪律已 G1-G6 落地），但：

| 维度 | Harness | ClawsJoy 现状 | 差距 |
|---|---|---|---|
| 任务说明书 | 逐条对应任务 | BRIEF.md ✅ | 已具备 |
| 执行纪律 | G1-G3 硬约束 | ✅ 已落地（plan_pending/ask/进度条）| 已具备 |
| 第三方验证 | 审计复核 | ✅ G4 已落地 | 已具备 |
| **工具说明书** | 独立工具手册 | ❌ 无（只有 agent_system.md 工具段）| **缺失** |
| **运行时记录可检索** | 全量落盘 + SAG 编目 | ⚠️ 落盘了但大多不可检索 | **最大差距** |
| **统一检索入口** | 单一 query | ❌ 只有 query_index（覆盖 tool_flow/keyword 等）| **缺失** |

**核心结论**：V9 的执行纪律已经到位（G1-G6），但"图书馆"还差两件事——**编目不全**（审计/越权/快照/goal 未注册进 SAG）和**说明书不齐**（无工具说明书）。本方案先编目（让 Agent 借得到书），再补说明书（告诉 Agent 有哪些书）。

---

## 一、落盘数据体检（实证）

### 1.1 当前可检索 vs 只落盘不可检索

| 数据区 | 落盘位置 | 落盘 | SAG 编目 | 检索入口 | 体检结论 |
|---|---|---|---|---|---|
| tool_flow 流水 | code_entities(tool) 20 条 | ✅ | ✅ | query_tool_flow | ✅ 可检索 |
| 代码实体 | code_entities 28227 条（16 种类型）| ✅ | ✅ | query_index | ✅ 可检索 |
| os_events | data/v8/events_default.jsonl 69KB | ✅ | ❌ | read_recent_os_events | ⚠️ 半可检索 |
| 审计记录 | data/v8/audit/tool_audit.jsonl | ⚠️ 未生成 | ❌ | ❌ | ❌ 不可检索 |
| 越权记录 | .agent_state.json[escalations] | ✅（0 条当前）| ❌ | ❌ | ❌ 不可检索 |
| 上下文快照 | data/v8/context_snapshots/（1 个）| ✅ | ❌ | ❌（只能 read_file）| ❌ 不可检索 |
| goal 状态 | .agent_state.json[goal] | ⚠️ 当前无 | ❌ | ❌（仅内存）| ❌ 不可检索 |
| ISSUES.md | docs/reports/ISSUES.md 9KB | ✅ | ❌ | ❌ | ❌ 不可检索 |
| 假完成日志 | data/fake_completion_log.json 6.5KB | ✅ | ❌ | ❌ | ❌ 不可检索 |
| 总结报告 | docs/reports/*.md | ✅ | ❌ | ❌ | ❌ 不可检索 |

**体检结论**：10 类落盘数据中，只有 2 类真正可检索（tool_flow + 代码实体），其余 8 类"只落盘不可检索"。

### 1.2 根因

1. **SAG 只有代码实体索引**：code_entities 表按代码结构设计（file_path/line_number/signature），非代码数据（审计/越权/快照）无对应 schema 习惯
2. **注册缺失**：audit.py / goal_state.py / _record_escalation 只写文件，未调用 extractor.upsert_entity
3. **检索入口单一**：query_index 只查 keyword_index（代码实体），无"查全部落盘"的统一接口
4. **审计未触发**：tool_audit.jsonl 不存在——说明 audit_tool_call 的落盘路径在沙箱/live 未实际写入（或路径权限问题，需验证）

---

## 二、目标架构：图书馆四要素

```
┌─────────────────────────────────────────────────────┐
│                ClawsJoy 知识图书馆                    │
├──────────────┬──────────────┬───────────────────────┤
│ 藏书（数据）  │ 编目（SAG）   │ 检索（入口）            │
├──────────────┼──────────────┼───────────────────────┤
│ 说明书区       │ entity_type:  │ query_index 统一入口    │
│  BRIEF/手册   │  manual       │  + 变量驱动投喂         │
│ 流水区        │  tool/keyword │  query_tool_flow       │
│  tool_flow   │  ...          │                        │
│ 审计区        │  audit_event  │  query_audit (新)      │
│  tool_audit  │              │                        │
│ 越权区        │  escalation   │  query_escalation(新)  │
│  越权记录     │              │                        │
│ 归档区        │  snapshot     │  query_snapshot (新)   │
│  上下文快照   │              │                        │
│ 目标区        │  goal         │  query_goal (新)       │
├──────────────┴──────────────┴───────────────────────┤
│ 借书规则：上下文三层（热窗口/滚动摘要/SAG 快照）        │
│ 读者：Agent（query_index / read_file / 变量驱动投喂）  │
└─────────────────────────────────────────────────────┘
```

**设计要点**（对齐 Harness 插件式思想）：

1. **每个数据区 = 一个 SAG entity_type**（注册即编目，upsert_entity 天然支持任意类型）
2. **每个 entity_type = 一个检索函数**（query_xxx，统一签名）
3. **说明书 = manual 类型实体**（BRIEF/agent_manual 注册，Agent 可查询）
4. **统一入口 query_index 扩展**：支持 entity_type 过滤（查代码 or 审计 or 全部）

---

## 三、落地计划（分优先级）

### P1a：审计/越权/快照/goal 注册进 SAG（编目）

**改动点**：

| 数据 | 注册时机 | entity_type | 落点函数 |
|---|---|---|---|
| 审计记录 | audit_tool_call 内 | audit_event | core/lib/sag_audit_bridge.py（新）|
| 越权记录 | _record_escalation 内 | escalation | 同上 |
| 上下文快照 | _snapshot_to_sag 内 | snapshot | 同上 |
| goal 状态 | create_goal/update_goal 内 | goal | 同上 |
| 说明书 | 启动时 | manual | 同上 |

**SAG 实体字段映射**（对齐 code_entities 现有 schema）：

```
audit_event:  entity_name=tool_name, signature=args_hash+result_hash+success, file_path=session_id, related_entities=[user_id]
escalation:   entity_name=tool, signature=reason, file_path=target, related_entities=[session_id,action]
snapshot:     entity_name=key, signature=summary 摘要, file_path=snapshot_path
goal:         entity_name=objective[:80], signature=status, file_path=session_id, related_entities=[goal_id]
manual:       entity_name=doc 名称, signature=内容摘要, file_path=doc 路径
```

### P1b：统一检索入口（query_index 扩展）

**query_index 增加 entity_type 参数**：

```
query_index(query='审计', entity_type='audit_event')   # 查审计
query_index(query='越权', entity_type='escalation')    # 查越权
query_index(query='快照', entity_type='snapshot')      # 查快照
query_index(query='目标', entity_type='goal')          # 查 goal
query_index(query='...')                               # 默认查代码（兼容现状）
```

**实现**：query_index 现有 keyword_index 是内存索引（代码实体）；扩展为可查 DB（psycopg2 直接 SELECT entity_type=xxx）。

### P2：工具说明书 agent_manual.md

**内容结构**（整合 agent_system.md 纪律 + 工具规范 + 完成标准 + 输出格式）：

```
# Agent 操作手册（agent_manual.md）
## 1. 任务说明书（承接 BRIEF）
## 2. 执行纪律（G1-G3：todo/计划确认/ask）
## 3. 工具说明书
   3.1 read_file：什么时候用/参数/禁用
   3.2 write_file：什么时候用/确认/禁用
   3.3 execute_command：白名单/heredoc/禁用
   3.4 query_index：查什么/entity_type 过滤
   3.5 search_files / list_dir / query_sag
## 4. 完成标准（5 项 checklist + 审计复核）
## 5. 输出格式规范（报告/进度/diff/ask）
## 6. 禁则清单（汇总 agent_system.md 分散条款）
```

**注册方式**：agent_manual.md 注册为 SAG manual 实体（启动时 upsert），Agent 通过 query_index(entity_type='manual') 按需查——避免全量注入占用 token（与 #41 变量驱动投喂一致）。

---

## 四、检索接口设计（统一签名）

```python
# core/lib/sag_audit_bridge.py（新模块）
def register_entity(entity_type, entity_name, signature, file_path, related_entities=None, project_id='default'):
    """通用 SAG 注册：所有落盘数据编目的唯一入口"""
    from core.lib.code_entity_extractor import extractor
    extractor.upsert_entity({
        'entity_type': entity_type,
        'entity_name': entity_name,
        'signature': signature,
        'file_path': file_path,
        'related_entities': related_entities or [],
    }, project_id)

def query_entities(entity_type=None, query=None, limit=20):
    """统一检索：按 entity_type + 关键词过滤，查 SAG"""
    # 实现：psycopg2 SELECT ... WHERE entity_type=? AND (entity_name/signature LIKE ?)
```

**与现有机制的关系**：
- `register_entity` 在 audit.py / goal_state.py / _record_escalation / _snapshot_to_sag 中**各加一行调用**（侵入最小）
- `query_entities` 供 query_index 扩展 + 元认知/os_monitor 使用
- 检索结果进 SAG → 自动被变量驱动投喂（#41 阶段3）按相关性取用 → 闭环

---

## 五、风险与边界

| 风险 | 缓解 |
|---|---|
| SAG 写入放大（每次审计都 upsert）| 批量注册：audit 队列落盘时合并 upsert（与 _flush_batch 同频）|
| DB 依赖（DATABASE_URL 未配置时）| register_entity 降级为仅写文件（现状行为不变），SAG 可用时再注册 |
| entity_type 膨胀 | 白名单控制：仅 5 类（audit_event/escalation/snapshot/goal/manual）|
| 检索性能 | query_entities 带 LIMIT + 索引（entity_type+entity_name 组合）|
| 说明书注入成本 | 按需查询（变量驱动），不全量注入 |

---

## 六、验收标准

1. `query_index(query='审计', entity_type='audit_event')` 返回审计记录（live 实测）
2. audit_tool_call 触发后，code_entities 出现 audit_event 类型实体
3. _record_escalation 触发后，出现 escalation 实体
4. goal 创建/完成时，出现 goal 实体且状态可查
5. agent_manual.md 注册为 manual 实体，Agent 可查询到工具规范
6. 全量测试通过 + 浏览器 E2E 回归无破坏

---

## 七、工作量评估

| 项 | 工作量 | 依赖 |
|---|---|---|
| P1a: sag_audit_bridge.py + 4 处注册 | S | 无 |
| P1b: query_index entity_type 扩展 | S | P1a |
| P2: agent_manual.md + 注册 | S | 无 |
| 测试（注册+检索+回归）| S | P1a/P1b |
| 合计 | M（约 300-400 行 + 1 份文档）| — |

---

## 八、与既有成果的衔接

- **G4 审计**：audit_tool_call 已落盘 → 补一行 register_entity 即编目
- **G6 goal**：goal_state 已落盘 → 补注册即编目
- **#41 三层上下文**：SAG 快照已写文件 → 补注册即编目（"被挤入 SAG"的资产现在可真检索）
- **变量驱动投喂**：检索结果按任务变量裁剪 → 自动只用相关记录，token 可控
- **发布流程**：同步后重启，sync_check.sh 验证

**一句话总结**："说明书 + 全量落盘 + SAG 编目 + 统一检索"——这正是 Harness 图书馆模式；ClawsJoy 已具备藏书与借书规则，缺的是编目（P1a）与统一检索卡（P1b），以及工具说明书（P2）。
