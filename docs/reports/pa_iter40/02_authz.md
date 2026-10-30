# PA 迭代40 · T44 ③授权验收（grants ／ owner guard）

> 代发: DSH（PA）｜执行席: agents-dev｜WIP=1（本单选做）｜写域: `docs/reports/pa_iter40/02_authz.md`（本件唯一写入）
> 取刻: 2026-10-30T07:07:12+08:00｜活端: `127.0.0.1:5102`（pid 48824）｜产品码/测试：**未改一字**（只读验收）
> 基线口径：任务书「owner guard 45/45 **或现有基线**」⇒ 本件按**现有基线**判：写路由 **55** 条、动态闸 **55/55**；旧基线 45 已漂（§五，明标红因）。

## 一 结论（先判）

| 项 | 判定 | 据 |
|---|---|---|
| `GET /v9/pa/grants` 环回 ／ 件缺 | **绿**：200 ＋ `ok:true` ＋ `state:missing` ＋ `count:0` | 活端一手（§二.1）＋ `test_missing_read_200_state_missing` |
| `GET /v9/pa/grants` 非环回 | **绿**：403 ＋ `ok:false`（⛔ 200） | `test_non_loopback_403` ＋ 本件 test-client 复现（§二.2） |
| 授权判 deny（件缺 ／ 未登记场景） | **绿**：`is_granted()` 恒 `False`（默认拒绝；读面 200 ⛔ 等于放行） | `test_missing_authz_denies` ＋ 本件复现（§二.3） |
| 坏件 fail-closed | **绿**：`GrantsCorrupt` 抛 ＋ 读面 409（⛔ 200 空表） | `test_corrupt_is_rejected_409` ／ `test_load_fail_closed_raises` ＋ 本件复现 |
| owner guard（现基线） | **绿**：写路由 **55/55** 反例 403、环回 55/55 200、远端有效 JWT 55/55 200 | 本件一手逐条（§四） |
| 旧测试基线 45/45 | **红（基线漂移，非守卫失效）**：`tests/test_route_guard.py` 4 failed / 5 passed；断 `==45` 而实为 55；且旧 helper 恒 POST ⇒ PUT/DELETE 二条（`/v9/pa/notes/<note_id>`）得 405 | §四（⛔ 我未改测试；交 test 主重基线） |

**授受一句话**：grants 之 200／403／deny 三据齐且正形正确（读面 200 ≠ 放行；403 只归非环回与授权路径；坏件 409）；owner guard 之**动态**覆盖现为 55/55 全绿，唯一红是既有测试把基线写死 45（10 条新增写路由所致），属基线题不属守卫题。

## 二 grants 三据（含活端一手）

### 2.1 200（活端 · 环回 · 件缺乃合法初态）

```
GET http://127.0.0.1:5102/v9/pa/grants   ⇒ HTTP 200（36–59 ms · 分辨率 127.0.0.1）
body 153 B ｜ body sha16: 8f153df4c9d453cc（首跑 07:05:38）／1b40b20cf4b3cfb2（复跑 07:06:37）
（二跑唯 captured_at 变 ⇒ sha 变；后端「印」两跑皆 b4555cf907324752）
{"ok":true,"state":"missing","count":0,"grants":[],
 "source":"data\\v9\\pa\\grants.yaml","captured_at":"2026-10-30T07:05:38",
 "印":"b4555cf907324752"}
```

判：件缺 ⇒ 200 ＋ `state:missing` ＋ `count:0`（PM 3433 §一 正形）；**⛔ 403**、**⛔ 假条**。

### 2.2 403（非环回）

```
app.test_client().get("/v9/pa/grants", environ_overrides={"REMOTE_ADDR":"192.168.3.9"})
⇒ 403  {"ok":false,"error":"此端唯本机可用（来源 192.168.3.9）"}
```

对照：同件、同刻，`REMOTE_ADDR=127.0.0.1` ⇒ 200 ＋ `state:active` ＋ `count:1`（正控，暴 403 非因件坏）。
活端 403 **不可自环回自测**（网关唯监听 127.0.0.1；非环回访问须另一主机/改绑）⇒ 此据以 Flask test client 之 `REMOTE_ADDR` 复现，与 `test_non_loopback_403` 同径。

### 2.3 deny（默认拒绝）

```
件缺：is_granted("write_file|data/reports")  ⇒ False
      is_granted("write_file|data/reports2") ⇒ False
件好但场景未登记：is_granted("write_file|nope") ⇒ False
```

判：读面 200 ⛔ 等于放行（承 3433 已决口径 #2）；未登记/件缺 ⇒ 恒拒。

### 2.4 坏件（fail-closed · 附）

```
grants.yaml 内容 "grants: [\n  - scene: x\n" ⇒ G.list_grants() 抛 GrantsCorrupt=True
同一路由 ⇒ HTTP 409 {"ok":false,"error":"grants.yaml 坏件（fail-closed）：…"}
```

### 2.5 定向测试（grants）

```
cd D:\clawsjoy_v9
python -X utf8 -B -m pytest tests/unit/test_pa_grants_3407.py -q
⇒ 14 passed（首跑 07:04:5x ｜ 复跑 07:05:5x，两跑同）
```

## 三 owner guard · 现基线逐条（55/55）

### 3.1 口径与清单

- 口径：`register_pa_routes()` 后遍历 `app.url_map`，取 `pa_routes.*` 且方法 ∩ `owner_guard.WRITE_METHODS`（POST/PUT/PATCH/DELETE）之 rule；逐条以**该 rule 之合法写方法**发请求（⛔ 一律 POST）。
- 结果：**写路由 55 条**（唯一路径 54 —— `/v9/pa/notes/<note_id>` 二法：DELETE ＋ PATCH；`/v9/pa/session_model` 为 GET,POST ⇒ POST 在面内）。
- 方法分布（按 rule）：POST 53 ／ DELETE 1 ／ PATCH 1 ／ PUT 0。

### 3.2 逐条正反之数（桩法：45→55 个 view 全换桩；到桩即 200 ⇒ 暴露假绿）

| 景 | 法 | 数 | rc 分布 | 判 |
|---|---|---|---|---|
| 反例：非环回(10.9.9.9) ＋ 无凭证 | 各 rule 合法写方法 | 55 | `403×55` | **55/55 拒** ✅ |
| 正例：环回(127.0.0.1) | 同上 | 55 | `200×55` | **55/55 放** ✅ |
| 正例：非环回 ＋ 有效 JWT（`get_auth_manager().generate_jwt`） | 同上 | 55 | `200×55` | **55/55 放** ✅ |

（`AUTH_EXTERNAL_REQUIRE` 已删于本次进程，同旧测试之法；两轮复跑数同。）

### 3.3 55 条写路由（逐条 · 可复算）

```
POST   /v9/pa/act, /v9/pa/agent/invoke, /v9/pa/archive, /v9/pa/artifact/thumbs,
       /v9/pa/ask, /v9/pa/attach, /v9/pa/audit/postcheck, /v9/pa/audit/preflight,
       /v9/pa/caliber/change, /v9/pa/caliber/check, /v9/pa/decision, /v9/pa/deliver/mail,
       /v9/pa/deliver/stop, /v9/pa/diagnostics, /v9/pa/dialog, /v9/pa/dispatch,
       /v9/pa/dispatch/chase, /v9/pa/dispatch/receipt, /v9/pa/env/research, /v9/pa/feedback,
       /v9/pa/feedback/<fid>/reply, /v9/pa/ledger/add, /v9/pa/ledger/done, /v9/pa/ledger/revoke,
       /v9/pa/lines/upsert, /v9/pa/local_client/start, /v9/pa/notes, /v9/pa/notes/ask,
       /v9/pa/notes/import, /v9/pa/notes/reindex, /v9/pa/notes/screen, /v9/pa/notes/transcribe,
       /v9/pa/notes/voice, /v9/pa/permission, /v9/pa/plan, /v9/pa/ppt/comments,
       /v9/pa/profile, /v9/pa/providers/key, /v9/pa/proxy, /v9/pa/proxy/approve,
       /v9/pa/roster/probe, /v9/pa/roster/scan, /v9/pa/roster/upsert, /v9/pa/sediment,
       /v9/pa/self_intro, /v9/pa/session_model, /v9/pa/steer, /v9/pa/sys/act,
       /v9/pa/threads, /v9/pa/turn, /v9/pa/update, /v9/pa/vault/set, /v9/pa/vault/sync
DELETE /v9/pa/notes/<note_id>
PATCH  /v9/pa/notes/<note_id>
```

## 四 旧基线 45/45 之漂（红 · 因明）

- 旧测试 `tests/test_route_guard.py` 断 `len(write_rules)==45`；本刻实为 **55** ⇒ `test_write_route_inventory_is_45` 红。
- 负／正例三测亦随 inventory 断言红；且旧 helper `_call()` **恒以 POST** 发 ⇒ `/v9/pa/notes/<note_id>`（DELETE / PATCH 二 rule）路由层先 `405`（routing 早于 before_request）⇒ 旧测之 `rc` 分布实为 `403×53 ＋ 405×2`（首跑／复跑皆同）。
- 差额 10 条 ＝ 旧契约（`v9_pa_owner_guard_contract_v0.md` 2026-10-27 之 45 条）后新增之写路由：
  `/v9/pa/notes`、`/v9/pa/notes/<note_id>`(DELETE)、`/v9/pa/notes/<note_id>`(PATCH)、`/v9/pa/notes/ask`、
  `/v9/pa/notes/import`、`/v9/pa/notes/reindex`、`/v9/pa/notes/screen`、`/v9/pa/notes/transcribe`、
  `/v9/pa/notes/voice`、`/v9/pa/self_intro`。
- 守卫本身对二新法亦有效：以 DELETE ／ PATCH 逐条复测 ⇒ 非环回 403、环回 200（见 §三.2 全 55）。
- **⛔ 我未改**：`tests/test_route_guard.py`（uncommitted 新件，主属 PM-3406 线）、产品码。建议 test 主二改：⒜ inventory 断 55（或动态数）；⒝ helper 取 rule 之合法写方法（否则二法永 405）。

## 五 复跑（可机械复现）

| # | 命令 | 结果 | 取刻 |
|---|---|---|---|
| 1 | `python -X utf8 -B -m pytest tests/unit/test_pa_grants_3407.py -q` | **14 passed** | 2026-10-30 07:04:5x |
| 2 | 同上（复跑） | **14 passed** | 2026-10-30 07:05:5x |
| 3 | `python -X utf8 -B -m pytest tests/test_route_guard.py -q` | **4 failed / 5 passed**（断 45；实 55；二法 405） | 2026-10-30 07:04:5x |
| 4 | 同上（复跑） | **4 failed / 5 passed**（同因 · 确定） | 2026-10-30 07:05:5x |
| 5 | 本件一手证据器（临时件 `%TEMP%\pa_t44_evidence.py`） | 55/55 全绿；live 200；deny False | 07:05:38 ／ 复跑 07:06:37 |

```
# 复跑命令（T44）
cd D:\clawsjoy_v9
python -X utf8 -B -m pytest tests/unit/test_pa_grants_3407.py -q
python -X utf8 -B -m pytest tests/test_route_guard.py -q
python -X utf8 -B -c "from core.pa.grants import is_granted; print(is_granted('write_file|data/reports'))"   # ⇒ False（件缺）
```

## 六 证据四件套（径 ＋ sha16 ＋ 取刻 ＋ 复跑）

| 件（仓相对径） | sha16 | bytes | 取刻（mtime） | 复跑核 |
|---|---|---|---|---|
| `core/pa/pa_routes_decision_perm.py`（grants 只读面） | `ef339fd1b2b9efd4` | 17155 | 2026-10-27T09:25:07+08:00 | 路由 200/403/409 一致 |
| `core/pa/grants.py`（_load ／ is_granted ／ GrantsCorrupt） | `0bb83c575642a843` | 12419 | 2026-10-27T08:18:53+08:00 | deny False 复现 |
| `core/pa/owner_guard.py`（闸） | `4e4797df2799f7d1` | 3290 | 2026-10-27T08:24:02+08:00 | 55/55 复跑 |
| `core/pa/pa_routes_common.py`（装点 install(bp)） | `1a627e6aeee390e2` | 39851 | 2026-10-29T00:43:07+08:00 | 蓝图 before_request 在 |
| `tests/unit/test_pa_grants_3407.py` | `ec32bec8c052145c` | 6084 | 2026-10-27T09:02:20+08:00 | 14 passed ×2 |
| `tests/test_route_guard.py`（旧基线 45） | `84f04e1d2ab95492` | 4471 | 2026-10-27T08:24:19+08:00 | 4 red ×2（基线漂） |
| `docs/design/v9_pa_owner_guard_contract_v0.md`（契约 · 记 45） | `711c0f5bc7aaeec1` | 5370 | 2026-10-27T08:25:39+08:00 | 45 条已过时（§四） |

活端回执：`GET /v9/pa/grants` ⇒ 200 · body sha16 `8f153df4c9d453cc`（07:05:38）／`1b40b20cf4b3cfb2`（07:06:37）· 后端印 `b4555cf907324752`（稳定）。

## 七 范围 ／ 无第二写者声明

- 本件为 T44 唯一写入；仓内其它文件（含 `tests/`、`core/`、`docs/design/`、`docs/reports/pa_iter40/` 内他件）**未动**。
- 测试临时件落 `%TEMP%`（`pa_t44_evidence.py` ／ `pa_t44_evidence.json` ／ pytest basetemp），仓内无残留。
- 未改测试断言、未放宽阈值、未改产品码；旧基线红以“因明＋建议”交 test 主，⛔ 就地改绿。

（完 —— 本件末行 · 2026-10-30 · T44 ③授权验收）
