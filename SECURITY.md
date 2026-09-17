# Security Policy

## Supported Versions

ClawsJoy 当前处于活跃开发阶段。以下版本会获得安全更新：

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |

## Reporting a Vulnerability

我们认真对待安全问题。如发现安全漏洞，请**不要**在公开渠道（Issue、讨论区、PR）直接披露，而应私下报告：

1. 发送邮件到维护者邮箱（见仓库主页联系方式），标题注明 `[SECURITY]`。
2. 在邮件中描述：
   - 漏洞类型与影响范围；
   - 复现步骤（尽量最小化、可执行）；
   - 受影响的版本与运行环境；
   - 你认为可能的修复方向（可选）。
3. 收到报告后，我们会在 **7 个工作日**内回复确认，并给出处理计划。

在漏洞修复并发布前，请对漏洞细节保密，避免影响其他使用者。

## Security Best Practices（部署建议）

- 项目使用 `.env` 存放敏感配置（API Key 等），该文件已被 `.gitignore` 排除，请勿提交到仓库。
- 对外暴露服务时，请将网关置于反向代理（如 Nginx）之后，并启用 HTTPS。
- 按最小权限原则管理用户与会话，定期轮换 API Key。
- 如使用沙箱命令执行能力，请确保运行环境已做权限隔离，避免未授权文件操作。
- 关注上游依赖（PostgreSQL 驱动、Flask 等）的安全公告，及时升级 `requirements.txt` 中的版本。
