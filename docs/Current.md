# ClawsJoy PA · Current（单一现状源）

> 本文件只写**现在是什么**：版本、默认、已验路径、明确未做。  
> 历史报告、工单、验收单只作归档，不再作为“现状”引用。  
> 迭代目标参考：docs/reports/PA_MATURITY_REVIEW_20261101.md（同步副本 D:ObsidianClawsJoy）  
> 更新：2026-11-01

## 版本

- 仓库版本：**9.2.2**（pyproject.toml / core/lib/version.py / shell/package.json）
- 安装版：**9.2.2**（本机 5103 /health healthy）
- 旧文档中的 9.0.36 / 9.0.76 / 9.2.0 均视为历史，不是当前版本

## 默认运行面

| 项 | 当前值 |
|---|---|
| 桌面壳 | Electron shell/ |
| 后端 | Flask，core/pa/pa_routes_* |
| 安装端口 | 5103（开发仓 5102） |
| PA 默认模型 | 本地 Ollama qwen2.5:7b-instruct-q4_0-gpu |
| 第二本地引擎 | localm（OpenAI /v1，8642），手动选择，不默认 |
| 云模型 | DeepSeek remote，仅显式选择；需要 PA 供应商密钥 |
| DSH | dsh 0.1.5-rc.1；headless；独立 DeepSeek key（data\dsh.env），不继承 PA 供应商密钥 |
| Postgres | 16，容器 clawsjoy-postgres，本机 5432 |
| Redis | 7，容器 clawsjoy-redis，6379 |

## 已验路径（本机，2026-11-01）

- /health 返回 9.2.2 healthy
- PA 本地对话走 Ollama；可手动切 localm
- localm 动态模型：qwen2.5-7b-instruct-q4_0-gpu、qwen2.5vl-7b；已载状态上屏
- 第二大脑 / Notebook / Studio 跟随所选模型
- /v9/agent/runs 受理、轮询、取消、刷新恢复
- runtime status：Ollama / localm / DSH；同模型双载警告
- benchmark：TTFT / tok/s（附口径）/ VRAM
- DSH 任务卡：RunRecord + 轨迹 + 独立 key 字段
- Postgres 6 张表；Redis PONG

## 明确未做 / 未验

- **一张产品面**：window.js 新窗与旧 8 模式壳仍并存；旧 DOM、旧 CSS、旧 composer 未删
- **一条发送链**：work/dev 走 /v9/agent/runs，但 send.js 仍保留 /v9/agent/chat SSE 分支；cards.js 仍有该端点调用路径
- **RunService 未接产品主路径**：文件头自述不接路由/DSH/聊天
- **五分钟首胜未成为首页**：first_run 仍是工程自述；Today 空态不是“选文件夹→问本周笔记→带出处/待办”
- **记忆四套**：PaCore JSON、notes、notebooks、前端 localStorage；未收口为一个产品入口
- **仓库卫生**：侧车 .before_* 与临时 .tmp_* 已移出主树到隔离区；仍有非临时/用户文件未清
- **文档单源**：本文件之前，版本与路线散落在多份 report；旧报告未标归档
- **DSH 本地 provider**：未支持；DSH 长任务仍需要云端 provider key
- **GEO / 链上 / 发币**：非目标，未做

## 当前整理顺序（承审查）

1. 卫生闸（已做第 0 步：移出 .before_* / .tmp_*，补 .gitignore）
2. 一张产品面：新窗唯一默认，旧 8 模式进回退旗
3. 一条发送链：产品只留 dialog + agent/runs；删 SSE 静默路径
4. RunService 接办事主路径
5. 记忆一个入口：Today / Summon 只打 notes + notebooks
6. 重做首跑：选文件夹 → 本周笔记 → 三条出处 + 待办
7. 薄路由门 + 本文件持续更新

## 不拆的资产

- grants 读面/授权面、owner_guard、本机密钥
- /v9/agent/runs 的 queued / cancel / restore 契约
- 本地优先与 fail-closed 语义
