# ClawsJoy

ClawsJoy 是一个面向 AI 开发者的多 Agent 协同网关，通过统一路由、AST 代码注入与元认知监控，让多个大模型 Agent 在同一工作区里协作完成代码生成、任务编排与知识沉淀。

## 核心特性

- **多 Agent 协同**：内置决策路由（DecisionAgentV4）与统一执行入口，自动将对话、计算、代码、翻译等请求分发给最合适的 Agent，支持花名册模型探活与动态调度。
- **大文件 AST 注入**：基于代码实体提取与 AST 补丁（`core/lib/test_ast_patcher.py`、`code_entity_extractor`），让 Agent 在上下文中精准感知代码结构，按锚点一次性替换，告别碎片化读取。
- **统一网关与记忆系统**：`agent_gateway_enhanced.py` 提供 `/v5/execute`、`/health`、`/metrics`、`/session`、`/memory` 等 REST 接口，支持跨会话记忆存取与任务进度断点续跑。
- **元认知与 SAG 知识图谱**：周期性监控 OS 事件并触发元认知分析，代码实体统一入库 SAG（Semantic Agent Graph），支持语义检索与关联上下文召回。
- **一键容器化部署**：多阶段构建的 Dockerfile 将依赖与源码分离，镜像体积可控，一条命令即可拉起网关服务。

## 快速开始

使用项目根目录提供的 Dockerfile 一键构建并运行网关：

```bash
# 构建镜像
docker build -t clawsjoy-gateway .

# 运行网关（默认监听 8000 端口）
docker run -p 8000:8000 clawsjoy-gateway
```

启动后可访问健康检查接口验证服务状态：

```bash
curl http://localhost:8000/health
```

也可以不使用 Docker，直接在本地运行：

```bash
# 安装依赖
pip install -r requirements.txt

# 启动网关
python3 agent_gateway_enhanced.py
```

## API 快速示例

向统一执行入口发送一个任务：

```bash
curl -X POST http://localhost:8000/v5/execute \\
  -H "Content-Type: application/json" \\
  -d '{"raw_input": "写一个排序函数", "user_id": "guest"}'
```

创建会话并查看健康状态：

```bash
curl -X POST http://localhost:8000/session/create \\
  -H "Content-Type: application/json" \\
  -d '{"user_id": "guest"}'

curl http://localhost:8000/health
```

查看全部可用端点：

```bash
curl http://localhost:8000/endpoints
```

## 项目结构

```
clawsjoy_dev/
├── agent_gateway_enhanced.py   # 网关主入口：统一路由、REST API、任务编排
├── core/
│   └── lib/                    # 核心库：AST 注入、代码实体提取、元认知、
│                               #   硬件探测、启动管理、SAG/花名册引擎
├── config/                     # 系统配置与注册表（能力、精准投喂、
│                               #   事件注入点、可用模型等 YAML）
├── tests/                      # 测试套件：网关路由、决策路由等
├── web/                        # Web 路由与静态资源（含移动端页面）
├── requirements.txt            # Python 依赖清单
└── Dockerfile                  # 多阶段容器化构建
```

各目录职责说明：

- `core/lib/`：核心业务库，包含 AST 补丁器、代码实体提取器、OS 事件日志、元认知分析、硬件探测、启动管理器以及 SAG / 花名册引擎。
- `config/`：系统运行时配置，以 YAML 注册表形式管理 OS 能力、精准投喂、事件注入点与可用模型。
- `tests/`：自动化测试，覆盖网关路由、决策路由等关键路径。
- `web/`：面向浏览器的路由与静态页面，包含移动端适配。

## 测试指南

运行网关路由测试验证核心功能：

```bash
python3 -m pytest tests/integration/test_gateway_routes.py -v
```

运行全部测试：

```bash
python3 -m pytest tests/ -v
```

## 环境变量

| 变量名             | 说明                     | 默认值     |
| ------------------ | ------------------------ | ---------- |
| `PYTHONUNBUFFERED` | 日志即时输出             | `1`        |
| `PYTHONDONTWRITEBYTECODE` | 不生成 `__pycache__` | `1` |

更多配置项请参考 `config/` 目录下的 YAML 文件。

## 参与贡献

欢迎提交 Issue 与 Pull Request。建议遵循以下流程：

1. Fork 本仓库并创建功能分支。
2. 提交代码前运行 `tests/` 下的相关测试。
3. 提交 PR 时附上改动说明与测试结果。

## V9 北极星（North Star）

> **在用户授权边界内，代表用户在其数字环境中观察、操作、调用资源、完成任务并对结果负责。**

**批169 修正（GPT 复核）**：原句「运行在老板本地电脑上的个人执行代理」把**主执行环境**当成了**能力边界**。两点加注：
1. **本地电脑是 PA 的主执行环境，不应成为 PA 的能力边界**（数字环境 = 本地 + 远端 + 浏览器 + 服务/Agent 资源）。
2. **V9 的目标不是 Computer Use，而是 Computer Agency** —— 「会操作电脑」是手段，「在边界内对结果负责地完成任务」才是目标。

**修正记录（批165）**：旧措辞「PA 的大方向 = 用户本地电脑的**任何操作能力**」⇒ 新措辞把重心放在 **「授权边界内」+「代表老板完成本地任务」**：**能力不是目的；在边界内替老板把事情做完才是。**

### North Star 结构

    North Star
    └── Local Digital Agency
        ├── L1 Observe       能不能看到 / 读取电脑世界
        ├── L2 Manipulate    能不能创建 / 修改 / 删除数字对象
        ├── L3 Control       能不能点击 / 输入 / 拖拽 / 提交 / 操作 GUI
        ├── L4 Delegate      能不能把工作交给合适的 Agent / Tool / Service
        └── L5 Orchestrate   能不能把多个动作 / Agent / 工具组织成闭环

> 注：「**调 Agent**」不是电脑操作本身，而是 PA 对**执行资源**的控制；**L5 才是「很多只手一起干活」**。

### 角色定义（任何新技术进来，只问一句「它补哪一层」）

| 组件 | 角色 | 补哪一层 |
|---|---|---|
| **DSH** | Agent Runtime | L4 / L5 |
| **Paseo** | Execution / Orchestration Runtime | L5 |
| **Browser** | Control Surface | L3 |
| **Computer Use** | Control Surface | L3 |
| **Verifier** | Truth Layer | 横跨 L2–L5 |
| **Approval** | Authority Boundary | 横跨 L2–L5 |
| **Frontend** | World Projection | 展示层（L1–L5 的投影） |

### 怎么开始（任务入口 —— 2026-09-15 真浏览器实测）

| 入口 | 在哪 | 关键提醒 |
|---|---|---|
| **PA 页**（推荐） | `/web/pa.html` 底部输入框 | **默认是「💬 聊天」模式 ⇒ 只商量、不出手**。要 PA 真动手，必须先切到 **「🛠️ 工作」** 或 **「⌨️ 项目开发」**（输入框右上角有通道徽章与「切到工作模式」按钮） |
| **工作台页** | `/web/dashboard/workbench.html` → 顶部 **「🤖 Agent 工作区」** | 任务框（「描述任务...」）在此面板内；同一页的「发消息或指令...」是**团队频道讨论**，不是任务入口 |
| DSH 自己的界面 | `:3080` | **与 V9 前端各自独立**（DSH = Agent Runtime；V9 = 控制平面），不是 V9 任务入口 |

> 完整的「入口 × 能力矩阵」（含写确认卡/状态显示/通道）见 `V9总任务书` §15.5。

**判据**：**答不出「它补哪一层」⇒ 暂不做**（这就是元层收口的用法）。

## 许可证

本项目使用 [MIT License](LICENSE) 开源，详见 [LICENSE](LICENSE) 文件。

参与贡献请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)；报告安全漏洞请阅读 [SECURITY.md](SECURITY.md)；社区行为准则见 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。

## 返回值契约（批175 立：两处契约写死，防复发）

假失败事故（批101 起悬案，批175 定位并修复）的本质是**两处契约各自「看起来对」，合起来必崩**：

| 函数 | 契约 | 硬规则 |
|---|---|---|
| `core/gateway/v9_bridge/response_guard.py::_run_response_guard` | **决策 dict**：`{final_resp, empty_retry, normal_complete, empty_reply_count, no_think}` | **任何分支都不得 `return (`**（旧 7 元组形态）；ask / plan_pending 这类「有终态载荷」的分支要把载荷放进 `final_resp` |
| `agent_gateway_enhanced.py::_v9_bridge_loop` | **7 元组**：`(messages, tool_steps, bridge_exhausted, final_resp, tokens, None, None)` | `final_resp` 非 None 时必须把**整个元组**交回（`make_stream_response` 按 7 元组解包），不得只 `return` 载荷 |

违反后果（实测）：ask（正常请示）收尾时抛 `TypeError: tuple indices must be integers or slices, not str` 或 `ValueError: too many values to unpack (expected 7)` ⇒ 桥接线程/流生成器崩 ⇒ SSE 发 `error` ⇒ PA 页把**正常请示**显示成「❌ 已失败」= **假失败**。

回归门：`tests/unit/test_p175_ask_contract.py`（含静态门：函数体内不得再出现 `return (`）。反例样本与检测清单 F1–F3 见体检库 §十四。

## 留痕纪律（批176 立：stderr 重定向必须成对还原）

- **任何** `sys.stderr = <重定向>` 都必须包在 `try/finally` 里还原（反例现场：`core/agents/cortex.py::_get_ft_model`）。
  反例后果：异常路径跳过还原 ⇒ 该进程**全局 `sys.stderr` 永久变 `/dev/null`** ⇒ 之后所有 `print(..., file=sys.stderr)` 的 traceback（`[BRIDGE_ERROR]` / `[SSE_ERROR]`）被静默丢弃。
  实测：批101–175 五批「后端日志干干净净、`[SSE_ERROR]`=0」的真因就是它；批176 修复后**同一路径立刻落痕**（A/B 对照：0 → 1+完整 traceback）。
- **判据**：留痕验的是「**日志里有没有**」，不是「代码里写没写」。查法：`grep -c "\[BRIDGE_ERROR\]\|\[SSE_ERROR\]" logs/gateway.log`（>0 才算有）。

## 只读接口：知识库 ↔ 沙箱映射（批176 副指标 A）

`GET /v9/pa/kb_mapping?user_id=<uid>&session_id=<sid>&scope=收件箱&limit=100`

- 主语是**知识库**：三列 = 知识库路径 → 沙箱映射路径 → 状态（`已镜像` / `过期` / `缺失` / `未镜像`）；`counts`/`total`/`truncated`/`degraded` 一并返回。
- **只读**：只 `stat`，不写知识库、不写沙箱、不改 mtime（N1–N6 零噪音的前置）。`scope` 只接受 vault 内相对子路径（`..` 穿越 ⇒ 400）。
- 「缺失」只在存在镜像记录（沙箱 `.kb_mirror.json`）时出现；无记录 + 无副本 = 「未镜像」（不混用）。
- 前端：PA 页 `📚 知识库映射` 折叠面板（默认折叠、原地展开、路径可复制、非「已镜像」行有「请求镜像」按钮——只填请求不自动执行）+ agent 消息里的素材路径渲染为可折叠胶囊。

> 注（批175 如实标注）：本树 README **缺**批174 的「产品原则（批174 立）」一节（该节目前只在 dev 检出）——属 dev/live 文档分叉，留待副指标 B 的 sha 对齐批次一并处理。
