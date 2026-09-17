# ClawsJoy 架构

## 递梯子链路

OS 拦截/降级/纠正 → write_os_event() → events_default.jsonl
 → read_recent_os_events() → reflect(os_events) → GLM5.2 分析
 → system_hypothesis 写入 SAG → 编排 Agent 查询引用
 → 人工审核 → 执行修复 → 验证闭环

## 三个自增长闭环

- OS 事件闭环：拦截→采集→分析→hypothesis→修复→验证
- 精准投喂闭环：配置→注入→效率提升→新场景→元认知建议新规则
- 能力注册闭环：模板→自动生成工具列表→新增能力加配置

## 关键数据资产

| 资产 | 用途 |
|------|------|
| os_precision_feeds.yaml | 精准投喂规则 |
| os_capabilities.yaml | OS 能力注册表 |
| os_event_injection_points.yaml | OS 事件注入点 |
| events_default.jsonl | OS 事件日志 |
| code_entities | SAG 知识图谱 |
