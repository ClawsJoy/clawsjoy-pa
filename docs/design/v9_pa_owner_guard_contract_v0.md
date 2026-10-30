# v9 · PA 写路由 owner 守卫契约 v0（PM-3406 §③B）

> 状态：**契约已定 ＋ 已落 ＋ 已验**｜取刻：2026-10-27 08:3x｜作：技术总监 `f202f89`（PD）
> 守卫：`core/pa/owner_guard.py`（新件）｜装点：`core/pa/gateway_routes.py` 之 `register_pa_routes`（一处）

## 一 契约三项（先契约 · 后 45/45）

### ⒈ 入参（`request` 何字段）

| 字段 | 用途 | 说明 |
|---|---|---|
| `request.remote_addr` | 环回判 | `127.*` ／ `::1` ／ `localhost` ／ `::ffff:127.*` ⇒ 本机 |
| `request.headers["Authorization"]` | 远端凭证 | 须 `Bearer <JWT>` |
| ~~`user_id`（body／query）~~ | ⛔ 本闸不读 | 归属一致性（body ↔ claims）由全局门 `core/lib/security_middleware.check_access` 管；本闸只判「有无合法 owner」 |

### ⒉ 判据（何谓 owner 合法）

1. **环回** ⇒ 合法（owner ＝ 本机）。`identity` 之 owner.json **不读**（⇒ 档坏不误伤本机；⛔ 铸新 id）。
2. **非环回** ⇒ 须同时：⒜ `Bearer` 非空；⒝ **二源验过**（`core.lib.auth_middleware.get_auth_manager().verify_jwt` ∨ `core.lib.auth_api.auth_manager.verify_token`）；⒞ claims 之 `user_id` 非空。
3. **显式关外证**：`AUTH_EXTERNAL_REQUIRE=0` ⇒ 与全局安全门同义放行（默认 `1`）。

⚠ **⛔ 环回-only**（按令）：远端持有效 JWT 者**放行** —— 不会坏远端 JWT 之路。
⚠ **二源皆认之由**：本仓现有两套 JWT（`auth_middleware` 之进程 secret ／ `auth_api` 之 `jwt.yaml` secret）；全局门用前者，登录口用后者 ⇒ 只认一源会断另一路。日后统一 ⇒ 删一支即可（一处）。

### ⒊ 反例（何时必 `403`）

| # | 反例 | rc |
|---|---|---|
| 1 | 非环回 ＋ 无 `Authorization` | **403** |
| 2 | 非环回 ＋ `Bearer` 坏／过期 | **403** |
| 3 | 非环回 ＋ 验过但 `user_id` 空 | **403** |
| 4 | （生产链）非环回 ＋ 无凭证 | 先被全局门 `401` 拦 ⇒ 二门同向 · 码不同 |

反例 4 照实：本闸之 `403` 在「裸 app」与「有坏 token」两景可复现；生产链上全局门先回 `401`。二者皆**拒**，⛔ 以 401 冒充 403（承 `L-21` 照实）。

## 二 落法（一处定形 · 45/45 动态覆盖）

| 件 | 改何 | 为何 | 印 |
|---|---|---|---|
| `core/pa/owner_guard.py` | 新件：`is_loopback` ／ `_bearer` ／ `_verify`（二源）／ `owner_ok` ／ `deny` ／ `install(bp)` | 守卫一处出 | — |
| `core/pa/gateway_routes.py` | `register_pa_routes` 内加 `owner_guard.install(bp)`（＋5 行含注释） | 45 条写路由原仅 4 条自判 | `f357f3c11f3953e8` ⇒ `a3e267c0153d56fd` |

⚠ **⛔ 逐路由改 41 处**：逐处加闸 ⇒ 五处判据 ⇒ 必歧，且与 CW 之 A2 抢同一文件。本闸挂**蓝图级** `before_request` ⇒ 写路由**动态**全覆盖（后加之路由亦自动受闸）。

## 三 验证（可跑）

### 3.1 测试

```
cd D:\clawsjoy_v9
python -m pytest tests/test_route_guard.py -q      # ⇒ 9 passed
```

| 项 | 果 |
|---|---|
| 写路由清单 | **45**（`app.url_map` 逐条：`pa_routes.*` ∧ POST/PUT/PATCH/DELETE） |
| 反例（逐条 403） | **45/45** |
| 正例（环回） | **45/45** ⇒ 200 |
| 正例（远端有效 JWT） | **45/45** ⇒ 200 |
| 相邻回归 | `test_pa_provider_keys_1613` ／ `test_sys_act_1852` ／ `test_attach_1852` ／ `test_v9_pa_update_1684` ／ `test_identity_1858` ／ `test_pa_grants_3407` ⇒ **74 passed** |

⚠ 测试之安全法：45 个 view 全换桩 ⇒ 闸不过才可能到桩（到即 200 ⇒ 暴露假绿），**⛔ 触真逻辑**。

### 3.2 反例 45 条（逐条 rc）

```
rc=403  /v9/pa/act
rc=403  /v9/pa/agent/invoke
rc=403  /v9/pa/archive
rc=403  /v9/pa/artifact/thumbs
rc=403  /v9/pa/ask
rc=403  /v9/pa/attach
rc=403  /v9/pa/audit/postcheck
rc=403  /v9/pa/audit/preflight
rc=403  /v9/pa/caliber/change
rc=403  /v9/pa/caliber/check
rc=403  /v9/pa/decision
rc=403  /v9/pa/deliver/mail
rc=403  /v9/pa/deliver/stop
rc=403  /v9/pa/diagnostics
rc=403  /v9/pa/dialog
rc=403  /v9/pa/dispatch
rc=403  /v9/pa/dispatch/chase
rc=403  /v9/pa/dispatch/receipt
rc=403  /v9/pa/env/research
rc=403  /v9/pa/feedback
rc=403  /v9/pa/feedback/<fid>/reply
rc=403  /v9/pa/ledger/add
rc=403  /v9/pa/ledger/done
rc=403  /v9/pa/ledger/revoke
rc=403  /v9/pa/lines/upsert
rc=403  /v9/pa/local_client/start
rc=403  /v9/pa/permission
rc=403  /v9/pa/plan
rc=403  /v9/pa/ppt/comments
rc=403  /v9/pa/profile
rc=403  /v9/pa/providers/key
rc=403  /v9/pa/proxy
rc=403  /v9/pa/proxy/approve
rc=403  /v9/pa/roster/probe
rc=403  /v9/pa/roster/scan
rc=403  /v9/pa/roster/upsert
rc=403  /v9/pa/sediment
rc=403  /v9/pa/session_model
rc=403  /v9/pa/steer
rc=403  /v9/pa/sys/act
rc=403  /v9/pa/threads
rc=403  /v9/pa/turn
rc=403  /v9/pa/update
rc=403  /v9/pa/vault/set
rc=403  /v9/pa/vault/sync
```

## 四 边界（照实）

1. 本闸 ⛔ 取代全局安全门；二者**同向**（本机放行 · 远端须证）。
2. 本闸只判「有无合法 owner」，⛔ 判「此 owner 可否动此资源」（按资源之细权 ⇒ 未做 · 另立项）。
3. `GET` 只读路由不在本闸面内（45 条写路由为准；`GET,POST` 之 `/v9/pa/session_model` 因含 POST ⇒ 在面内）。
4. 反例之 `403` 与全局门之 `401` 并存 ⇒ 已在 §一.3 照实。

（完 —— 本件末行 · LF 终 · ⛔ 悬）
