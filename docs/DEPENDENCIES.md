# 系统依赖

## 运行时依赖

| 组件 | 用途 | 配置位置 |
|------|------|---------|
| Python 3.13 | 运行环境 | `.venv/` |
| Flask | 网关框架 | `agent_gateway_enhanced.py` 之 `app = Flask(__name__)` |
| PostgreSQL | SAG 知识图谱 + 平台数据 | `localhost:5432` |
| Ollama | 本地 LLM 推理 | `localhost:11434` |
| DeepSeek API | 云端 LLM 推理 | `.env` 中 DEEPSEEK_API_KEY |
| GLM5.2 API | 元认知深度分析 | `.env` 中 GLM_API_KEY |
| fastText | 意图分类 | `models/intent_classifier.bin` |
| ChromaDB | 向量存储 | `data/vector_db/` |

## 配置依赖

| 文件 | 用途 | 缺失时影响 |
|------|------|-----------|
| `.env` | 环境变量 | 网关无法启动 |
| `config/os_precision_feeds.yaml` | 精准投喂规则 | 投喂失效，Agent 效率下降 |
| `config/os_capabilities.yaml` | 能力注册表 | 元认知分析缺少能力参考 |
| `config/os_event_injection_points.yaml` | OS 事件注入点 | OS 异常静默，无法自检 |
| `config/prompts/agent_system.md` | 执行 Agent Prompt | Agent 行为退化 |
| `config/prompts/meta_cognition_system.yaml` | 元认知 Prompt | 元认知分析不准确 |
| `config/prompts/orchestration_agent.yaml` | 编排 Prompt | 编排计划缺少历史参考 |

## 数据依赖

| 路径 | 用途 | 缺失时影响 |
|------|------|-----------|
| `data/v8/roster_default.json` | 花名册 | @ 路由失效 |
| `data/v8/events_default.jsonl` | OS 事件日志 | 元认知无数据可分析 |
| `data/v8/billing_default.jsonl` | 计费流水 | 账单查询失效 |
| `data/code_index/` | 代码索引 | SAG 语义搜索失效 |
| `.agent_state.json` | 会话状态 | 任务上下文丢失 |
