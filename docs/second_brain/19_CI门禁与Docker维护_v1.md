# CI 门禁与 Docker 维护（2026-10-30）

## 已定

- P0/P1/P2 完成；P3 全仓格式化按约定不做。
- Dockerfile 已固定 Python 3.12，修正行继续符双反斜杠；`.dockerignore` 排 data/models/证据/legacy。
- 主 CI 分为门禁：changed-lint、PA 门禁测试、Windows static、Docker Build。
- 门禁测试 51 passed / 2 integration deselected；本地 53 passed。
- `test_real_*` 已标 integration，需本机活端/vault，不在 GitHub 门禁跑。
- legacy 基线：ruff 32,437 errors；black 1,321 files would reformat。
- Ratchet：新改动必须过 changed-lint；legacy 只准降不准涨；禁止全仓 `ruff --fix` / `black .` 清债。
- CI：`cf678d2` 的 CI Gate / Windows 双绿；`d91f9f6` Docker Build 绿。
- 本地 Docker Engine 29.4.1 已恢复；本地 `clawsjoy-gateway:9.0.51` 1.88GB 构建成功。

## 待决/未做

- 全仓 legacy lint/test 未清零，仍是 advisory/manual。
- P3 全仓 black 重排未做，也不建议和功能混做。

## 证据

- `docs/ci/CI_GATE.md`
- `docs/ci/legacy_baseline_20261030.json`
- `docs/reports/pa_iter40/`
- `tools/ci_legacy_metrics.py`
