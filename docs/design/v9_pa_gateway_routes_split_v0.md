# v9 · PA 网关路由拆分方案 v0（PM-3406 §②）

> 状态：**v0 方案**（② 本身 ⛔ 动产品码 · ⛔ 未拆；③B 之 owner 闸另落门面 ＋5 行 · 见契约）｜取刻：2026-10-27 08:3x｜作：技术总监 `f202f89`（PD）

## 〇 底稿与照实

| 项 | 一手读数 |
|---|---|
| 底稿 | `core/pa/gateway_routes.py` |
| 字节 | **275139** B |
| 行 | **4859** 行（LF） |
| sha16 | **`a3e267c0153d56fd`** |
| 路由 | **89** 条（ast 逐条配对；`Select-String '@bp\.route'` 亦 89；`path+methods` 去重后仍 89） |
| 写路由 | **45** 条（POST/PUT/PATCH/DELETE）——与 ③ 之基数 45 一致 |
| 模块级 def/assign | 142 名（含 1 个 `register_pa_routes` 容器） |

⚠ **计数歧异（照实）**：令与 `PM-3403` 皆称 **88** 条；本刻一手为 **89** 条（两法一致、无重复）。
⇒ 本方案按 **89/89** 出表，并请 PM 裁「以 89 为准」（或指出应剔之 1 条）。⛔ 以 88 硬凑（会丢 1 条 ⇒ 恰是令所戒之真风险）。

## 一 目标形态（不变量优先）

1. **单蓝图不变**：`gateway_routes.py` 仍建 `Blueprint("pa_routes", __name__)`，9 件各以 `register(bp, brain=None)` 挂入 ⇒ endpoint 名恒 `pa_routes.<func>`（89/89 不变），⛔ 9 个独立蓝图（会改 endpoint ＋ 断 `url_for`／能力面清单）。
2. **门面变薄**：`register_pa_routes(app, brain)` ＝ 建 bp → 逐件 `register(bp, brain)` → `app.register_blueprint(bp)` → `_set_capability_brief(app)` → `_set_pa_app(app)` → `return bp`。
3. **公共件**：`core/pa/_pa_gateway_common.py`（非蓝图件）—— `ok`／`err`、`_code_sha16`、`_data_dir`／`_core`、`_loopback`、身份归一、`_web_root`／`_frontend_build`、`session_model_of/clear`、惰算之门（`pa_faces()` 等）。
4. **closure 保留**：`brain` 由 `register(bp, brain)` 形参传入，路由函数仍闭包它（⛔ 全局态）。

## 二 十件（9 蓝图件 ＋ 1 公共件）

| # | 件 | 职责 | 路由数 | 估行 | ≤800 |
|---|---|---|---|---|---|
| 0 | `_pa_gateway_common.py` | 公共器（非蓝图） | — | **304** | ✅ |
| 1 | `pa_routes_chat.py` | 对话／线程／画像／沉淀／会话模型之取 | 12 | **716** | ✅ |
| 2 | `pa_routes_ask.py` | 问（KB 检索 ＋ 决断／死件之判） | 1 | **634** | ✅ |
| 3 | `pa_routes_kb.py` | 知识库映射面 | 1 | **231** | ✅ |
| 4 | `pa_routes_faces.py` | 检索面／素材面／UI 面／首跑面 | 4 | **627** | ✅ |
| 5 | `pa_routes_roster.py` | 席册／席位／环境／续面／供应商与会话模型 | 17 | **283** | ✅ |
| 6 | `pa_routes_dispatch.py` | 分派／回执／催收／投递 | 9 | **220** | ✅ |
| 7 | `pa_routes_proxy.py` | 线／代理／口径／审计／动手／steer | 12 | **381** | ✅ |
| 8 | `pa_routes_vault.py` | 库同步／到点／计划／拍板／归档／附件／今日 | 9 | **268** | ✅ |
| 9 | `pa_routes_ops.py` | 本机客户端／更新／账本／权限／构建／PPT／反馈／诊断／sys | 24 | **668** | ✅ |

估行口径：路由函数体跨度 ＋ 其独占 helper 闭包跨度 ＋ 30 行（imports/胶水）；公共 helper 按「被 ≥2 件引用」归公共件并只计一次。

## 三 路由映射表（89/89 · 逐条归件）

| # | 行 | 跨度 | 方法 | 路径 | 函数 | 归件 |
|---|---|---|---|---|---|---|
| 1 | 2263 | 14 | GET | `/v9/pa/local_client/status` | `pa_local_client_status` | `pa_routes_ops.py` |
| 2 | 2279 | 31 | POST | `/v9/pa/local_client/start` | `pa_local_client_start` | `pa_routes_ops.py` |
| 3 | 2313 | 54 | POST | `/v9/pa/update` | `pa_update_run` | `pa_routes_ops.py` |
| 4 | 2369 | 48 | GET | `/v9/pa/context` | `pa_context` | `pa_routes_chat.py` |
| 5 | 2419 | 5 | GET | `/v9/pa/profile` | `pa_profile` | `pa_routes_chat.py` |
| 6 | 2426 | 17 | GET | `/v9/pa/profile/schema` | `pa_profile_schema` | `pa_routes_chat.py` |
| 7 | 2445 | 35 | POST | `/v9/pa/profile` | `pa_profile_write` | `pa_routes_chat.py` |
| 8 | 2482 | 7 | POST | `/v9/pa/sediment` | `pa_sediment` | `pa_routes_chat.py` |
| 9 | 2491 | 159 | POST | `/v9/pa/dialog` | `pa_dialog` | `pa_routes_chat.py` |
| 10 | 2652 | 21 | GET | `/v9/pa/dialog` | `pa_dialog_history` | `pa_routes_chat.py` |
| 11 | 2675 | 11 | GET | `/v9/pa/sessions` | `pa_sessions_list` | `pa_routes_chat.py` |
| 12 | 2688 | 78 | POST | `/v9/pa/turn` | `pa_turn_record` | `pa_routes_chat.py` |
| 13 | 2768 | 148 | POST | `/v9/pa/ask` | `pa_ask` | `pa_routes_ask.py` |
| 14 | 2918 | 19 | GET | `/v9/pa/threads` | `pa_threads_get` | `pa_routes_chat.py` |
| 15 | 2940 | 26 | GET | `/v9/pa/whoami` | `pa_whoami` | `pa_routes_chat.py` |
| 16 | 2968 | 14 | POST | `/v9/pa/threads` | `pa_threads_post` | `pa_routes_chat.py` |
| 17 | 2984 | 29 | GET | `/v9/pa/ledger` | `pa_ledger` | `pa_routes_ops.py` |
| 18 | 3015 | 148 | GET | `/v9/pa/cost` | `pa_cost` | `pa_routes_ops.py` |
| 19 | 3165 | 10 | POST | `/v9/pa/ledger/add` | `pa_ledger_add` | `pa_routes_ops.py` |
| 20 | 3177 | 7 | POST | `/v9/pa/ledger/done` | `pa_ledger_done` | `pa_routes_ops.py` |
| 21 | 3189 | 13 | POST | `/v9/pa/ledger/revoke` | `pa_ledger_revoke` | `pa_routes_ops.py` |
| 22 | 3204 | 23 | POST | `/v9/pa/dispatch` | `pa_dispatch` | `pa_routes_dispatch.py` |
| 23 | 3232 | 11 | GET | `/v9/pa/version` | `pa_version` | `pa_routes_roster.py` |
| 24 | 3246 | 6 | GET | `/v9/pa/providers` | `pa_providers` | `pa_routes_roster.py` |
| 25 | 3255 | 13 | GET | `/v9/pa/providers/key/token` | `pa_provider_key_token` | `pa_routes_roster.py` |
| 26 | 3270 | 33 | POST | `/v9/pa/providers/key` | `pa_provider_key` | `pa_routes_roster.py` |
| 27 | 3306 | 29 | GET/POST | `/v9/pa/session_model` | `pa_session_model` | `pa_routes_roster.py` |
| 28 | 3338 | 6 | POST | `/v9/pa/roster/scan` | `pa_roster_scan` | `pa_routes_roster.py` |
| 29 | 3350 | 10 | GET | `/v9/pa/seats` | `pa_seats` | `pa_routes_roster.py` |
| 30 | 3362 | 20 | GET | `/v9/pa/roster` | `pa_roster` | `pa_routes_roster.py` |
| 31 | 3384 | 9 | GET | `/v9/pa/roster/find` | `pa_roster_find` | `pa_routes_roster.py` |
| 32 | 3395 | 11 | GET | `/v9/pa/roster/<agent_id>` | `pa_roster_card` | `pa_routes_roster.py` |
| 33 | 3408 | 16 | POST | `/v9/pa/roster/upsert` | `pa_roster_upsert` | `pa_routes_roster.py` |
| 34 | 3435 | 11 | GET | `/v9/pa/env` | `pa_env` | `pa_routes_roster.py` |
| 35 | 3448 | 11 | GET | `/v9/pa/env/note` | `pa_env_note` | `pa_routes_roster.py` |
| 36 | 3461 | 10 | POST | `/v9/pa/env/research` | `pa_env_research` | `pa_routes_roster.py` |
| 37 | 3474 | 10 | GET | `/v9/pa/resume` | `pa_resume` | `pa_routes_roster.py` |
| 38 | 3487 | 23 | POST | `/v9/pa/agent/invoke` | `pa_agent_invoke` | `pa_routes_roster.py` |
| 39 | 3512 | 8 | POST | `/v9/pa/roster/probe` | `pa_roster_probe` | `pa_routes_roster.py` |
| 40 | 3523 | 21 | POST | `/v9/pa/dispatch/receipt` | `pa_dispatch_receipt` | `pa_routes_dispatch.py` |
| 41 | 3546 | 12 | GET | `/v9/pa/dispatch/receipt` | `pa_dispatch_receipt_get` | `pa_routes_dispatch.py` |
| 42 | 3560 | 9 | POST | `/v9/pa/dispatch/chase` | `pa_dispatch_chase` | `pa_routes_dispatch.py` |
| 43 | 3571 | 8 | GET | `/v9/pa/lines` | `pa_lines` | `pa_routes_proxy.py` |
| 44 | 3581 | 7 | POST | `/v9/pa/lines/upsert` | `pa_lines_upsert` | `pa_routes_proxy.py` |
| 45 | 3590 | 79 | POST | `/v9/pa/proxy` | `pa_proxy` | `pa_routes_proxy.py` |
| 46 | 3671 | 6 | GET | `/v9/pa/proxy/gate` | `pa_proxy_gate` | `pa_routes_proxy.py` |
| 47 | 3679 | 15 | POST | `/v9/pa/proxy/approve` | `pa_proxy_approve` | `pa_routes_proxy.py` |
| 48 | 3698 | 4 | GET | `/v9/pa/caliber` | `pa_caliber` | `pa_routes_proxy.py` |
| 49 | 3704 | 31 | POST | `/v9/pa/caliber/change` | `pa_caliber_change` | `pa_routes_proxy.py` |
| 50 | 3737 | 37 | POST | `/v9/pa/caliber/check` | `pa_caliber_check` | `pa_routes_proxy.py` |
| 51 | 3776 | 57 | POST | `/v9/pa/audit/preflight` | `pa_audit_preflight` | `pa_routes_proxy.py` |
| 52 | 3835 | 16 | POST | `/v9/pa/audit/postcheck` | `pa_audit_postcheck` | `pa_routes_proxy.py` |
| 53 | 3853 | 44 | POST | `/v9/pa/act` | `pa_act` | `pa_routes_proxy.py` |
| 54 | 3912 | 47 | POST | `/v9/pa/steer` | `pa_steer` | `pa_routes_proxy.py` |
| 55 | 3961 | 51 | GET | `/v9/pa/dispatch/history` | `pa_dispatch_history` | `pa_routes_dispatch.py` |
| 56 | 4014 | 17 | POST | `/v9/pa/vault/sync` | `pa_vault_sync` | `pa_routes_vault.py` |
| 57 | 4034 | 13 | GET | `/v9/pa/projects` | `pa_projects` | `pa_routes_vault.py` |
| 58 | 4050 | 9 | POST | `/v9/pa/plan` | `pa_plan` | `pa_routes_vault.py` |
| 59 | 4061 | 28 | POST | `/v9/pa/decision` | `pa_decision` | `pa_routes_vault.py` |
| 60 | 4091 | 28 | GET | `/v9/pa/decision/log` | `pa_decision_log` | `pa_routes_vault.py` |
| 61 | 4124 | 21 | POST | `/v9/pa/deliver/mail` | `pa_deliver_mail` | `pa_routes_dispatch.py` |
| 62 | 4149 | 24 | GET | `/v9/pa/deliver/mail` | `pa_deliver_mail_face` | `pa_routes_dispatch.py` |
| 63 | 4176 | 22 | GET | `/v9/pa/deliver/authz` | `pa_deliver_authz` | `pa_routes_dispatch.py` |
| 64 | 4201 | 7 | POST | `/v9/pa/deliver/stop` | `pa_deliver_stop` | `pa_routes_dispatch.py` |
| 65 | 4211 | 6 | GET | `/v9/pa/permission` | `pa_permission_get` | `pa_routes_ops.py` |
| 66 | 4220 | 24 | GET | `/v9/pa/grants` | `pa_grants_get` | `pa_routes_ops.py` |
| 67 | 4246 | 12 | GET | `/v9/pa/build` | `pa_build_get` | `pa_routes_ops.py` |
| 68 | 4260 | 16 | POST | `/v9/pa/permission` | `pa_permission_post` | `pa_routes_ops.py` |
| 69 | 4278 | 10 | GET | `/v9/pa/ppt/comments` | `pa_ppt_comments_get` | `pa_routes_ops.py` |
| 70 | 4290 | 19 | POST | `/v9/pa/ppt/comments` | `pa_ppt_comments_post` | `pa_routes_ops.py` |
| 71 | 4311 | 15 | POST | `/v9/pa/artifact/thumbs` | `pa_artifact_thumbs_post` | `pa_routes_ops.py` |
| 72 | 4328 | 11 | GET | `/v9/pa/source_faces` | `pa_source_faces` | `pa_routes_faces.py` |
| 73 | 4341 | 12 | GET | `/v9/pa/ui_faces` | `pa_ui_faces` | `pa_routes_faces.py` |
| 74 | 4355 | 12 | GET | `/v9/pa/first_run` | `pa_first_run` | `pa_routes_faces.py` |
| 75 | 4369 | 48 | POST | `/v9/pa/vault/set` | `pa_vault_set` | `pa_routes_faces.py` |
| 76 | 4418 | 41 | GET | `/v9/pa/kb_mapping` | `pa_kb_mapping` | `pa_routes_kb.py` |
| 77 | 4483 | 88 | POST | `/v9/pa/archive` | `pa_archive_post` | `pa_routes_vault.py` |
| 78 | 4573 | 23 | GET | `/v9/pa/archive/<archive_id>` | `pa_archive_get` | `pa_routes_vault.py` |
| 79 | 4641 | 6 | GET | `/v9/pa/feedback/target` | `pa_feedback_target` | `pa_routes_ops.py` |
| 80 | 4649 | 15 | POST | `/v9/pa/feedback` | `pa_feedback_submit` | `pa_routes_ops.py` |
| 81 | 4666 | 8 | GET | `/v9/pa/feedback` | `pa_feedback_list` | `pa_routes_ops.py` |
| 82 | 4676 | 7 | GET | `/v9/pa/feedback/<fid>` | `pa_feedback_item` | `pa_routes_ops.py` |
| 83 | 4685 | 11 | POST | `/v9/pa/feedback/<fid>/reply` | `pa_feedback_reply` | `pa_routes_ops.py` |
| 84 | 4698 | 19 | POST | `/v9/pa/diagnostics` | `pa_diagnostics_build` | `pa_routes_ops.py` |
| 85 | 4723 | 9 | GET | `/v9/pa/sys/snapshot` | `pa_sys_snapshot` | `pa_routes_ops.py` |
| 86 | 4734 | 13 | GET | `/v9/pa/sys/<panel>` | `pa_sys_panel` | `pa_routes_ops.py` |
| 87 | 4754 | 14 | POST | `/v9/pa/sys/act` | `pa_sys_act` | `pa_routes_ops.py` |
| 88 | 4774 | 21 | POST | `/v9/pa/attach` | `pa_attach` | `pa_routes_vault.py` |
| 89 | 4798 | 11 | GET | `/v9/pa/today` | `pa_today` | `pa_routes_vault.py` |

对表口径：`(path, methods, func)` 三元组；89 行逐条有归属 ⇒ `89/89`，缺失 ＝ 0。

## 四 v1 执行序（六拍后 · 由我报期）

1. 先落 `_pa_gateway_common.py`（纯搬运 · 不改语义）⇒ 跑全量 pytest 取基线；
2. 逐件搬（一件一提交）：每件后跑 `route_inventory` 对表（89/89）＋ 该件相关测试；
3. 门面收敛（`gateway_routes.py` 只留门面 ＋ 惰算门）；
4. 启动 smoke（`rc=0`）＋ 全量 pytest；
5. 回滚点：git 提交 ＋ `.before_<印16>`（⛔ 删旧底 · 承界）。

## 五 判据（可跑 · v0 已备）

| # | 判据 | 口径 |
|---|---|---|
| 1 | 路由不丢 | `route_inventory`（ast ／ url_map 二法）`89/89`，diff ＝ 0 |
| 2 | 每件估行 | ≤ 800（本表最大 `pa_routes_chat.py` 716） |
| 3 | endpoint 不变 | `pa_routes.<func>` 89/89 |
| 4 | 启动 smoke | `rc=0` |
| 5 | 印不飘 | 各路由 `印` 值抽检（见 §六.2） |

## 六 风险与不变量（v1 必验）

1. **`brain` closure**：由 `register(bp, brain)` 传参保；⛔ 改全局。
2. **`_code_sha16` 印**：主路 `inspect.getsource(func)` 与所在文件无关 ⇒ 印应不变；
   但 fallback 分支读 `__file__`（整模块字节）⇒ 搬迁后该分支之印**必变** ⇒ v1 须逐条抽检「主路可用」（⛔ 落 fallback）。
3. **惰算门 `__getattr__`**：模块级 `__getattr__` 只对外读者生效（内读者 `LOAD_GLOBAL` 直查 `__dict__`）；
   ⇒ 拆后 `PA_FACES` ／ `PA_SRC_FACES` 之**内读者一律改调** `pa_faces()` ／ `pa_src_faces()`（common 供），`__getattr__` 留 common。
4. **无循环 import**：common ⛔ import 任何路由件；路由件只 import common ＋ 既有 core 模块。
5. **蓝图单例**：9 件共用同一 `bp` ⇒ 端点名不变；⛔ 各自 `Blueprint(...)`。

## 七 与 ③ 之关系

owner 守卫落**门面一处**（`bp.before_request`）⇒ 45 条写路由动态全覆盖，拆件**不影响**守卫；
反之，拆件后若按件各装守卫 ⇒ 五处判据 ⇒ 必歧（⛔ 取）。

（完 —— 本件末行 · LF 终 · ⛔ 悬）
