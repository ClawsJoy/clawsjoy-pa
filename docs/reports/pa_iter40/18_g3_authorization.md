# PA 迭代40 · T80 G3 9/9 恢复授权包

- 代发: DSH（PA）｜主: lead｜WIP=1
- 取刻: 2026-10-30
- 依据: T77 `17_g3_source.md`（b96eee4d9153592d）；T48 R6/G3
- 目的: 请老板/CEO 批“9/9 只读恢复”的授权范围；14/14 不在此包直接恢复

## 一 两个面

| 面 | 判 | 源 | 依赖 |
|---|---|---|---|
| 9/9 route_skip_scan | **可恢复（待授权）** | WSL verify.py `f9ba9bede5620350`；旧路由 `ad29de68fe5d4a99` | 私库/WSL 取件授权；owner_guard 现成 |
| 14/14 files_full | **blocked B1–B5** | 同上 + CLI `5b73141e84cc294e` + 旧证 `9b049df04bb3f11d` | B2 旧依赖、B3 清单数据、B4 roster、B5 复跑 |

## 二 9/9 最小恢复规格

- 新增 `core/pa/verify.py`（源 f9ba9bede5620350 起，按现役路径/依赖适配）；
- 新增 `core/pa/pa_routes_verify.py`：仅 GET `/v9/pa/verify`；
- 环回 `is_loopback` ⇒ 200；非环回 ⇒ 403 `owner_required`；
- **⛔ 引 token**；只读，不写盘，不发起 live HTTP；
- 响应分面：`face=route_skip_scan`，`pass/total=9/9`；`files_face.state=blocked`，不把 9/9 冒充 14/14；
- 1 正 1 反：环回 200 + 非环回 403；POST ⇒ 405。

## 三 14/14 的 B1–B5

| # | 阻塞 | 需谁 |
|---|---|---|
| B1 | 源/证在私人 Obsidian 库 + WSL 旧树；入仓须授权 | 老板/库主 + CEO |
| B2 | 旧依赖 `_scan_excluded`/`last_walk_errors` 现役无，须重写 | PD/后端 |
| B3 | `vault_manifest_win.txt`/`vault_missing_win.txt` 缺失 | 老板/旧库数据主 |
| B4 | v5 roster `obsidian_brain` 不在现役 6 id | PM/PD 重基线 |
| B5 | 建端后 1 正 1 反复跑 | PD |

## 四 请授权/请办

1. 批 9/9 只读恢复：允许复制 WSL `verify.py` 与旧路由到仓，按 §二 适配；
2. 批/不批 14/14 源与数据入仓；B2/B3/B4 另派；
3. 授权取件人：DSH/PD；范围仅 verify.py/路由/CLI/旧证/两份清单；
4. 明确 9/9 恢复后 R6 只升到“路由面绿”，不把 files_full 冒绿。

## 五 界

- 本包只申请，**未复制私库源、未建端、未改产品码、未造假**；
- `/v9/pa/verify` 现仍 404；G3 仍红。

（完）