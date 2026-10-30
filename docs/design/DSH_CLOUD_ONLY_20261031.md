# DSH 本地 provider 结论（2026-10-31）

## 事实

- `DSH_HOME=D:\dsh-home`
- `profiles/headless` 仅：`cordis.patch.yml` / `cordis.yml` / `package.json` / `pnpm-workspace.yaml`
- 无 `provider` / `baseURL` / `ollama` / `openai` 配置
- `--dump-config`：`agent-default-model` = `provider: deepseek-official` / `model: deepseek-flash`

## 结论

- DSH 当前**没有现成本地 provider**；只能 cloud deepseek。
- PA 无 key 时 `model=dsh` 已 400 `dsh_requires_key`，不排队跑失败。
- 要做“PA+DSH 本地”，需给 DSH 写 provider 插件/适配；不是配置一行可完成。

## PA 侧行为

- 本地 Ollama runner 正常（无 key）。
- DSH runner 走 `dsh --profile headless` 子进程；无 key 明确失败。
- 不在 UI 默认暴露 DSH；避免用户误点。
