# 管理员指南

## 花名册管理
- 前端 UI 聘用/解雇 Agent
- 模型配置：Ollama 本地 / DeepSeek 云端
- 未配 model 默认 Ollama 本地

## 模型降级
- DeepSeek API key 为空时自动降级 Ollama
- 花名册模型每小时自动探活，退役模型标记 deprecated

## 开机自启
- PostgreSQL：crontab @reboot
- 网关：crontab @reboot（延迟 15 秒等 PostgreSQL 就绪）

## 数据资产
- events_default.jsonl：OS 事件日志
- code_entities：SAG 知识图谱，110 条 system_hypothesis
