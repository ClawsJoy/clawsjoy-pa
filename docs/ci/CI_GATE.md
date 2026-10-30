# CI Gate 与 legacy 欠账基线

## 1. 现在绿的是什么

- changed-lint：只检查本次变更的 Python 文件（ruff + black）
- pa-gate-tests：51 个环境无关测试，-m "not integration"
- Windows CI：win_pa 静态检查
- Docker Build：Linux runner 构建 clawsjoy-gateway

## 2. 现在没绿的是什么

- 全仓 legacy ruff：32,437 errors
- 全仓 black：1,321 files would reformat
- 全仓 legacy tests：未作为门禁，advisory/manual

> 这些都是历史欠账，不是 9.0.51/7+2 引入的。

## 3. Ratchet 规则

1. 新改动必须过 changed-lint；
2. 新文件不得新增 legacy 违规；
3. legacy 总数只能降，不能涨；
4. 刷新基线：python -X utf8 -B tools/ci_legacy_metrics.py
5. 禁止用全仓 ruff --fix / black . 一次清债；
6. 禁止把 legacy advisory 设为 required。

## 4. P3 边界

- 不做全仓格式化；
- 只对本次触碰文件做 black；
- 全仓 black 重排另立 PR，不与功能混。

## 5. 基线文件

- 数字：docs/ci/legacy_baseline_20261030.json
- 工具：tools/ci_legacy_metrics.py（只读）
