# PA 迭代40 · T128 G3 7+2 新路径只读路由

- 代发：DSH（PA）｜执行：api-dev｜WIP=1
- 取刻：2026-10-30T16:09:31+08:00
- 裁决：**D-20261030-11b**（老板批新路径；非 9-9／14-14；旧 /v9/pa/verify 仍 404）
- 写域：core/pa/pa_routes_decision_perm.py、tests/unit/test_pa_verify_legacy_route.py、
  tests/baseline/route_baseline_v0.json、docs/pa/relations/DECISION_LEDGER.md、本件

## 一 端点契约

| 项 | 值 |
|---|---|
| 路径 | `GET /v9/pa/verify/legacy_7_2` |
| 环回 | **200**（唯本机） |
| 非环回 | **403** `{ok:false,error:"owner_required"}`（⛔ token） |
| 方法 | 唯 GET（POST ⇒ 405） |
| 实现 | 调 `core.pa.legacy_verify_face.run_legacy_7_2()`（产品包，⛔ import 顶层 legacy_verify） |
| 响应 | `{ok,version,face:'legacy_7_2',pass:7,fail:0,na:2,results[9]}` |
| 旧路径 | `GET /v9/pa/verify` **仍 404**（⛔ 占旧径） |
| 只读 | ⛔ 写账 ／ ⛔ 9/9 ／ ⛔ 14/14；face 漂移 ⇒ 200 但 ok=false |

## 二 一手实跑（test_client）

    NEW_STATUS 200
    NEW_SHAPE {"ok": true, "face": "legacy_7_2", "pass": 7, "fail": 0, "na": 2}
    NEW_N 9
    C10 ['PASS']
    C12C13 [('C12', 'N/A'), ('C13', 'N/A')]
    OLD_STATUS 404
    NONLOOP 403 owner_required

## 三 测试与工具

- `python -X utf8 -B -m pytest tests/unit/test_pa_verify_legacy_route.py -q`
  ⇒ **10 passed**（2.99s ／ 3.36s，两跑同数）
  - 正例：环回 200／face 7/0/2／results 9／无 token；真跑（不注入）C2/C10 PASS、C12/C13 N/A
  - 反例：非环回 403 owner_required（不调 run）；带 Authorization 仍 403；POST 405；
    旧 /v9/pa/verify 404；9/9 与 14/14 漂移 ⇒ 200 但 ok=false
- `python -X utf8 -B tools/route_diff.py --check tests/baseline/route_baseline_v0.json`
  ⇒ **RC0**（baseline=105 current=105 diff=0）
- `python -X utf8 -B tools/split_audit.py --check` ⇒ **RC0**（13 件 · 105 路由 diff=0）

## 四 径＋sha16

| 件 | sha16 | bytes |
|---|---|---|
| `core/pa/pa_routes_decision_perm.py` | `a135a862fe6c5957` | 20548 |
| `tests/unit/test_pa_verify_legacy_route.py` | `bbb8d01bb17b0852` | 4837 |
| `tests/baseline/route_baseline_v0.json` | `0a4d4fb6d3e323e5` | 9521 |
| `docs/pa/relations/DECISION_LEDGER.md` | `21f97c967cddbea3` | 2762 |

基线：count **105**，含 `{GET, /v9/pa/verify/legacy_7_2, pa_verify_legacy_7_2}`。

## 五 边界

- 未改旧路径、未建 9/9／14/14 面、未写账；唯新只读路由 ＋ 测试 ＋ 基线 ＋ D-11b ＋ 本件。
- 本路由只读；C2 活端 6 全等、C10 本包 walker 真扫、C12/C13 N/A（⛔ 计 PASS）。
- 现役 5102 进程需重启/重打后加载本路由（本单未重启产品进程）。
