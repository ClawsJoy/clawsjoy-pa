# Organic Approval E2E（2026-11-01）

> 目标：真模型产生 write_file tool call → pending → /v9/agent/runs/approval 批准 → 写入 → 回执。
> 环境：dev 5102（源码）；LocaLM 8642；model=qwen2.5-7b-instruct-q4_0-gpu。

## 结果

- auth: user_id=approval-organic2 / session_id=approval-organic2
- model: localm:qwen2.5-7b-instruct-q4_0-gpu
- tool call id: call_949a859c3eac4fcb96be51d3
- 首次响应 status: write_pending
- pending path: approval_organic.txt
- pending content: hello organic approval
- 审批：POST /v9/agent/runs/approval，action=approve
- 审批响应：status=write_confirmed，success=true
- 写入文件：D:\clawsjoy_v9\data\projects\approval-organic2\approval-organic2\clawsjoy_dev\approval_organic.txt
- 文件内容：hello organic approval

## 关键点

1. tool call 不是人工种子；是 LocaLM 模型真实返回的 tool_calls。
2. pending 由真实 write gate 创建，不是直接写 _pending_writes。
3. 批准经产品 runs/approval 路由。
4. 写入后 pending 清除，返回 write_confirmed。

## 边界

- 本次在 dev 5102 源码验证；安装版需 9.4.5 打包后才带 LocaLM adapter。
- 不是 Ollama 路径；Ollama 未安装。
- 审批卡 UI 未点；验证的是 API 路由与 agent/approval 链。
