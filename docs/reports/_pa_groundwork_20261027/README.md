# ②v1 拆件 · 完工记录（2026-10-27 · TD `f202f89`）

> 令：老板 `3436`（PA-010）／`3438`（PA-012）／`3439`（PA-013）｜PM `PM-3174`／`PM-3175` 之同线
> 判据器：`tools/route_diff.py`（本席扩源面 · 判据未改）｜基线：`tests/baseline/route_baseline_v0.json`

## 一 拓扑（实发行数 · 非估）

| 件 | 字节 | 行(LF) | 印16 | 路由 |
|---|---|---|---|---|
| `core/pa/pa_routes_common.py` | 39722 | 797 | `2b540953bd0bd014` | 0 |
| `core/pa/pa_routes_roster_seats.py` | 23450 | 480 | `7a19bd717d4d2ba4` | 14 |
| `core/pa/pa_routes_chat_engine.py` | 40044 | 703 | `d5d277609d9e3aae` | 7 |
| `core/pa/pa_routes_dispatch_flow.py` | 20738 | 433 | `6f25629545969c7f` | 16 |
| `core/pa/pa_routes_ledger_audit.py` | 23233 | 458 | `0cd59c6bcbeb4867` | 9 |
| `core/pa/pa_routes_env_providers.py` | 16191 | 330 | `3b8854f218c705c2` | 13 |
| `core/pa/pa_routes_faces_ui.py` | 24123 | 469 | `1399c7eb4acf6414` | 8 |
| `core/pa/pa_routes_dialog_threads.py` | 32683 | 595 | `0d965a85155fe696` | 7 |
| `core/pa/pa_routes_decision_perm.py` | 17155 | 348 | `ef339fd1b2b9efd4` | 10 |
| `core/pa/pa_routes_content_caliber.py` | 15550 | 340 | `3dba0579c9bec1b6` | 5 |
| `core/pa/gateway_routes.py（兼容门）` | 6499 | 160 | `4be636107d1b79e2` | 0 |

合 **89 路由**（`/v9/pa*`）· 十件皆有 `def register(bp)` × 1 · 单件最 **797** 行（≤800）· ⛔ 复建蓝图（`bp` 唯 `pa_routes_common`）。

## 二 判据（可跑 · 一手）

| 判据 | 果 |
|---|---|
| `python tools\route_diff.py --check tests\baseline\route_baseline_v0.json` | **rc 0** · `baseline=90 current=90 files=11 dupes=0` · `PASS（diff=0）` |
| `python tools\route_diff.py --self-test` | **PASS**（正控 0 ／ 反控删 2 ／ 反控方法 2） |
| `pytest tests/unit/test_pa_core.py` | **7 passed** |
| `pytest tests/test_route_guard.py` | **9 passed**（旧报 13 系误记 · 照实 9） |
| `pytest tests/unit/test_pa_grants_3407.py` | **14 passed** |
| 实机挂载 `register_pa_routes(Flask)` | **89 rules** |
| v0 模块面契约（157 个模块级名） | 新门面**缺 0** |

## 三 归属表（89/89 · 0 悬）

`route_ownership_v1.csv` —— 逐条：`序,rule,methods,endpoint,file,func,decorator_lineno`。
由**活路由表**（`app.url_map`）＋ 各簇 AST 交叉生成（⛔ 手列）⇒ 改一处、表自跟。

## 四 门面保真（拆件后 v0 语义之三个补）

1. **写名扇出**：`gateway_routes` 之 `__setattr__`（模块类 `_FacadeModule`）—— 改门面一名 ⇒ 同改**所有持有该名绑定之簇件**。
   由：v0 单测以 `monkeypatch.setattr(gateway_routes, …)` 注入替身；拆件后真引用在簇内，唯改门面不足以命中。
2. **活读唯一家**：`_PA_APP` ／ `PA_CAPABILITY_BRIEF` 之唯一家在 `pa_routes_common`；`capability_brief()`／`pa_app()` 改**露读**（旧静态 import ⇒ 恒陈值 ⇒ `pa_read` 六面皆拒 · 真病）。
3. **面册真源扩包**：`_ui_route_set()` 之无上下文回落实只扫本档 ⇒ 拆件后误判 20 条「悬」；改扫本包（`pa_routes_*.py` ＋ `gateway_routes.py`）。

## 五 余项（⛔ 本席未动测试 · 待裁）

**15 条测试**仍红，同族：皆以 `io.open(GR.__file__)` ／ `ROOT/"core"/"pa"/"gateway_routes.py"` 读**单档源**再数字面。
拆件后该档 160 行（兼容门）⇒ 字面在簇内。判意未变，唯**取源面**须由「单档」改为「本包」。

| 测件 | 条数 | 取源形 |
|---|---|---|
| `tests/unit/test_p9_jsonl_readable_gate.py` | 4 | `GR = ROOT/…/gateway_routes.py`（:37） |
| `tests/unit/test_pa_feedback_1634.py` | 1 | `io.open(p)`（:136） |
| `tests/unit/test_pa_first_run.py` | 1 | `read_text`（:145） |
| `tests/unit/test_pa_agent_chat_1859.py` | 1 | `io.open(GR.__file__)`（:245） |
| `tests/unit/test_pa_axis_1803.py` | 1 | `GW = ROOT/…`（:52） |
| `tests/unit/test_pa_cache_evict_1569.py` | 1 | `io.open(GR.__file__)`（:73） |
| `tests/unit/test_pa_capability_brief_1802.py` | 1 | `io.open(GR.__file__)`（:91） |
| `tests/unit/test_pa_gate_view.py` | 1 | `io.open(GR.__file__)`（:169） |
| `tests/unit/test_pa_kb_unset_no_cwd_scan.py` | 1 | `io.open(GR.__file__)` |
| `tests/unit/test_pa_receipt_read_at.py` | 1 | `io.open(GR.__file__)`（:82） |
| `tests/unit/test_pa_turn_human_2021.py` | 1 | `GR = ROOT/…`（:19） |
| `tests/unit/test_v9_pa_update_1684.py` | 1 | `read_text`（:195） |

**提议（待准）**：加 `tests/pa_src.py` 一函 `gr_src()`（拼本包源）＋ 上 12 档各改一行取源；**判据一字不改**、不改阈值、不删断言。

## 六 界

唯写：`core/pa/pa_routes_*.py` ／ `core/pa/gateway_routes.py` ／ `tools/route_diff.py`（取源面）／ `docs/reports|decisions/**` ／ `core/pa/_gen/**`。
⛔ 改测试（未准）· ⛔ 删路由 · ⛔ 重启 ／ 迁移 · ⛔ 出网 · ⛔ 动 `_pm\`。

### ①层锚

〔①〕`D:/codex-home/cli/AGENTS.md`〔②〕`D:/paseo-home/`〔③〕`D:\clawsjoy_v9\core\pa\**` ＋ `tools/route_diff.py` ＋ `tests/baseline/route_baseline_v0.json`

（完 —— 本件末行 · LF 终 · ⛔ 悬）
