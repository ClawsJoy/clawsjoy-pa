# Contributing to ClawsJoy

感谢你愿意为 ClawsJoy 贡献代码！以下是参与贡献的流程与规范，请在提交前阅读。

## 目录

- [开发环境](#开发环境)
- [代码规范](#代码规范)
- [提交规范](#提交规范)
- [Pull Request 流程](#pull-request-流程)
- [测试要求](#测试要求)
- [问题报告](#问题报告)

## 开发环境

```bash
# 1. Fork 本仓库并克隆到本地
git clone https://your-fork/clawsjoy.git
cd clawsjoy

# 2. 创建虚拟环境并安装依赖
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 开发/测试依赖

# 3. 启动网关（默认监听 8000 端口）
python3 agent_gateway_enhanced.py
```

> 提示：也可以使用 Docker 构建运行，参考 `Dockerfile`。

## 代码规范

- Python 版本：3.13+。
- 遵循 PEP 8 风格；行宽建议不超过 120 字符。
- 注释与文档字符串使用中文或英文均可，但同一文件内保持一致。
- 新增配置请优先使用 `config/` 下的 YAML 注册表，并在 `core/lib/config_schema.py` 中补充 Schema 校验。
- 修改网关入口 `agent_gateway_enhanced.py` 时，注意保持路由按域拆分到对应 Blueprint，避免单文件持续膨胀。
- 提交前运行 `python3 -m py_compile` 检查语法。

## 提交规范

建议遵循 [Conventional Commits](https://www.conventionalcommits.org/) 提交信息格式：

```
<type>(<scope>): <subject>

<body>

<footer>
```

常用 type：

- `feat`：新功能
- `fix`：缺陷修复
- `docs`：文档变更
- `refactor`：重构（不改变外部行为）
- `test`：测试相关
- `chore`：构建、依赖、工具等杂项
- `perf`：性能优化

示例：

```
fix(gateway): 修复会话恢复时上下文丢失问题

当任务中断恢复时，工作区上下文未正确合并到新会话，
导致 Agent 丢失已完成步骤。现统一从 .agent_state.json
恢复任务进度并重建上下文。

Closes #123
```

## Pull Request 流程

1. 从 `main` 分支创建功能分支：`git checkout -b feat/your-feature`。
2. 完成改动并运行相关测试（见下文）。
3. 提交信息遵循 [提交规范](#提交规范)。
4. 推送分支并创建 Pull Request，标题简述改动内容。
5. PR 描述中说明：
   - 改动目的与背景；
   - 改动涉及的文件与模块；
   - 测试方式与结果；
   - 关联 Issue（如有）。
6. 等待维护者 review，根据反馈修改后重新推送即可。

CI（`.github/workflows/ci.yml`）会在 push / PR 时自动运行测试，请确保通过后再请求合并。

## 测试要求

- 任何代码改动都应附带或更新测试，覆盖至少一条关键路径。
- 测试使用 `pytest`，位于 `tests/` 目录。

```bash
# 运行全部测试
python3 -m pytest tests/ -v

# 运行单个测试文件
python3 -m pytest tests/integration/test_gateway_routes.py -v
```

> 如果环境无 pytest，可退化为 `python3` 断言式冒烟测试，但 PR 中需说明原因。

## 问题报告

提交 Issue 时请包含：

- 环境信息（Python 版本、操作系统、是否 Docker）。
- 复现步骤（尽量最小化）。
- 期望行为与实际行为的差异。
- 相关日志或报错堆栈（注意脱敏：不要提交 API Key、.env 内容等敏感信息）。

## 行为准则

请阅读 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)，参与本项目即表示你同意遵守其中的约定。
