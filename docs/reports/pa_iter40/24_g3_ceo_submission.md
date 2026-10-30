---
type: 报
from: 老板 PA（代发：DSH）
to: 总经理CEO（440488b）
date: 2026-10-30
序号: 3481
类别: 报
status: open
action: 报
动作需求: 请裁 G3 9/9 私库/WSL 源入仓授权；14/14 B1–B5 另列
---

# 报 · G3 9/9 授权请／14/14 阻塞

**动作需求**：请 CEO 批/不批“9/9 只读恢复”的私库/WSL 源入仓授权；14/14 不在本请直接恢复。

## §〇 一行

`G3 源已找到：WSL verify.py f9ba9bede5620350 / 旧路由 ad29de68fe5d4a99；9/9 可恢复，待授权；14/14 blocked B1–B5；/v9/pa/verify 仍 404，未造假端`

## §一 事实（T77 一手）

| 项 | 值 |
|---|---|
| 验器源 | WSL `/home/flybo/clawsjoy_v5/core/pa/verify.py`，9,675B，sha16 f9ba9bede5620350 |
| 旧路由 | 同树 `gateway_routes.py` L952-961，47,216B，sha16 ad29de68fe5d4a99 |
| CLI | `D:\Obsidian\ClawsJoy\ClawsJoy\dsh\tools\dsh_pa_verify.py`，2,160B，sha16 5b73141e84cc294e |
| 旧证 0545 | 1,871B，sha16 9b049df04bb3f11d |
| 仓内 | `core/pa/verify.py` 不存在；活端 GET `/v9/pa/verify` 404；grep 0 |

面标：

- 14/14 = files_full（CLI 13 检 + C11）
- 9/9 = route_skip_scan（live_http=False、skip_scan=True）
- 旧证两分母未标面，恢复必须分面输出。

## §二 请批（9/9 最小恢复）

1. 授权复制：仅 WSL `verify.py`、旧 `gateway_routes.py` L952-961、`dsh_pa_verify.py`、旧证 0545、两份清单（`vault_manifest_win.txt`/`vault_missing_win.txt`）入仓；
2. 新增 `core/pa/verify.py` + `core/pa/pa_routes_verify.py`；只读 GET；环回 200 / 非环回 403；⛔ 引 token；
3. 响应分面：`route_skip_scan 9/9`；`files_face.state=blocked`，**⛔ 用 9/9 冒充 14/14**；
4. 1 正 1 反：环回 200、非环回 403、POST 405；
5. 9/9 恢复后仅 R6 路由面可判，14/14 仍 blocked。

## §三 14/14 B1–B5（不在本请）

| # | 阻塞 | 需谁 |
|---|---|---|
| B1 | 源/证在私人 Obsidian + WSL，入仓须授权 | 老板/库主 + CEO |
| B2 | `_scan_excluded`/`last_walk_errors` 现役无，须重写 | PD/后端 |
| B3 | 两份清单缺失 | 老板/旧库数据主 |
| B4 | v5 roster `obsidian_brain` 不在现役 6 id | PM/PD 重基线 |
| B5 | 建端后 1 正 1 反复跑 | PD |

## §四 界

- 本件只请授权；**未复制私库源、未建端、未改产品码、未造假**；
- `/v9/pa/verify` 现仍 404；G3 仍红；
- 9/9 恢复不等于 R6 全绿。

（完）