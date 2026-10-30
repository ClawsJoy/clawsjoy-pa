# -*- coding: utf-8 -*-
"""PA 网关路由 v0 → ②v1 拆件后之**兼容入口**。

实现已分：`pa_routes_common`（单蓝图 ＋ 公共面 ＋ 挂载入口）＋ 9 个 `pa_routes_*` 簇。
本件只留惰算门 `__getattr__`，并**全量再导出**旧名（≈60 测试与器以 `gateway_routes.<name>` 取用）。
⚠ 活值 `PA_CAPABILITY_BRIEF` ／ `_PA_APP` 由 `__getattr__` 直转公共件（⛔ 静态 import 之陈值）。
"""

import logging

logger = logging.getLogger(__name__)

from core.lib.paths import ws_root, vault_root
from core.pa.pa_routes_common import register_pa_routes
import logging
import os
import sys
import types
import time
from pathlib import Path
from flask import Blueprint, jsonify, request
from core.pa.pa_core import PaCore
from core.lib.paths import cmd_exe, org_enabled, path_forms, vault_root, ws_root
from core.pa import _proc as _proc   # ⭐ 窗隐唯一出口（PM 2026-10-05 令 · ⛔ 各写 creationflags）

from core.pa.pa_routes_common import (
    PA_ASK_DEADFILE_KW, PA_ASK_DEADFILE_LEDGER, PA_ASK_DECISION_ID_RE, PA_ASK_DECISION_KW,
    PA_ASK_MIN_SCORE, PA_CORPUS_NAME_BIGRAMS, PA_FACES_DEFAULT_MAX_BYTES, PA_FACES_MAX_BYTES,
    PA_FACES_MAX_FILES, PA_FACES_MIN_ROW, PA_FACES_MIN_SCORE, PA_FACES_SKIP,
    PA_FACES_SKIP_PREFIX, PA_FACES_VERSION, PA_FACE_ROLE, PA_KB_ASK_SCOPES,
    PA_SELFTEST_MARKS, PA_VAULT_ENV_KEY, PA_VAULT_ENV_NOTE, PaCore,
    Path, _CAP_BRIEF_METHODS, _LINE_CACHE, _LINE_CACHE_MAX,
    _PA_ROUTE_PREFIX, _UI_REPO, _ask_deadfile, _ask_decision,
    _bigrams, _cached_lines, _code_sha16, _core,
    _data_dir, _face_files, _face_root, _face_skip_name,
    _inter_fast, _is_under_path, _last_user_before, _loopback,
    _lru_put, _nows, _owner_corrupt_json, _pa_faces_tables,
    _pa_read_at, _proc, _rel_under, _set_capability_brief,
    _set_pa_app, build_capability_brief, err, logger,
    logging, ok, os, pa_ask_scan_specs,
    pa_faces, pa_faces_gate, pa_vault_face_files, pa_vault_state_code,
    time, vault_env_override,
)
from core.pa.pa_routes_roster_seats import (
    PA_FIRST_RUN_VERSION, _TELEMETRY_MARKS, _first_run_readout, _ollama_tri,
    _telemetry_scan, _uid_safe,
)
from core.pa.pa_routes_chat_engine import (
    PA_ASK_FORCE_KW, PA_ASK_META_KW, PA_ASK_META_NOT, PA_ASK_REFUSAL,
    PA_ASK_REFUSAL_STALE, PA_GATE_DECISIONS, PA_GATE_WHY, PA_KB_EMPTY_ANSWER,
    PA_KB_UNSET_VERDICT, PA_TURN_HUMAN, _ASK_CACHE, _ASK_CACHE_MAX,
    _ask_scope, _dialog_sessions, _jsonl_lines, _kb_root_str,
    _lines_delta, pa_ask_scan_stamp, pa_gate_view, pa_kb_search,
    pa_turn_human,
)
from core.pa.pa_routes_dispatch_flow import (
    LOCAL_CLIENT, LOCAL_CLIENT_COOLDOWN_S, LOCAL_CLIENT_GUARD, _REPO_AGENT_CLIENT,
    _client_python, _local_client_dir, _local_client_ws_url, cmd_exe,
    local_client_command, local_client_launchable, sys,
)
from core.pa.pa_routes_ledger_audit import (
    _identity, _uid_identity,
)
from core.pa.pa_routes_env_providers import (
    _frontend_build, _web_root,
)
from core.pa.pa_routes_faces_ui import (
    PA_SRC_FACES_VERSION, PA_UI_FACES_VERSION, UI_FACES_DIR, UI_FACES_MANIFEST,
    _src_face_readout, _src_faces_tables, _ui_face_files, _ui_face_requires,
    _ui_faces_readout, _ui_route_known, _ui_route_norm, _ui_route_set,
    pa_src_faces, pa_src_faces_gate,
)
from core.pa.pa_routes_dialog_threads import (
    PA_CHANNEL_CLAUSE, PA_MODE_CLAUSE, PA_NO_PROVIDER_TEXT, PA_SYSTEM,
    PA_SYSTEM_CLOSE, PA_SYSTEM_HEAD, PA_SYSTEM_TAIL, _LLM_PHASE,
    _session_binding, capability_brief, llm_brain, pa_app,
    pa_mode_name, pa_system_for, session_model_clear, session_model_of,
)
from core.pa.pa_routes_decision_perm import (
    _permission_grant_provenance,
)
from core.pa.pa_routes_content_caliber import (
    KB_FINGERPRINT, KB_FINGERPRINT_MAX_BYTES, KB_MAPPING_DEFAULT_SCOPE, KB_STATUSES,
    KB_STATUS_MIRRORED, KB_STATUS_MISSING, KB_STATUS_STALE, KB_STATUS_UNKNOWN,
    KB_STATUS_UNMIRRORED, _kb_fingerprint, _kb_safe_rel, build_kb_mapping,
)


PA_GATE_DISPLAY = ("model", "refuse")


def _fed_root():
    from core.pa import feedback_store as _fs
    return _fs.root_of(None)


def __getattr__(name):
    u"""模块级惰算（⛔ 顶层赋值 ⇒ ⛔ import 即定形）—— ⛔ 缓存。"""
    if name == "_FACE_WS":
        return ws_root()
    if name == "_FACE_VR":
        return vault_root()
    if name == "PA_FACES":
        return pa_faces()
    if name == "PA_FACES_GATE":
        return pa_faces_gate()
    if name == "PA_SRC_FACES":
        return pa_src_faces()
    if name == "PA_SRC_FACES_GATE":
        return pa_src_faces_gate()
    if name in ("PA_CAPABILITY_BRIEF", "_PA_APP"):

        from core.pa import pa_routes_common as _pc

        return getattr(_pc, name)

    raise AttributeError("module %r has no attribute %r" % (__name__, name))


# ── v0 之「可替面」保真（②v1 拆件后）─────────────────────
# v0 之单测以 `monkeypatch.setattr(gateway_routes, "<名>", 替身)` 注入；
# 拆件后该名之**真引用**在**簇件**内 ⇒ 唯改本件之 dict 不足以命中（代码仍读簇件之陈值）。
# ⇒ 本模块 `__setattr__` 扇出：改本件之一名 ⇒ **同改所有持有该名绑定之簇件**
#   （＝ v0 「一个模块一处绑定」之语义；monkeypatch 复原时同路扇回）。
# ⚠ 惟扇出**簇件实有之同名绑定**（`vars(m)` 之键），⛔ 无中生有。
_CLUSTER_MODULES = (
    "pa_routes_common", "pa_routes_roster_seats", "pa_routes_chat_engine",
    "pa_routes_dispatch_flow", "pa_routes_ledger_audit", "pa_routes_env_providers",
    "pa_routes_faces_ui", "pa_routes_dialog_threads", "pa_routes_decision_perm",
    "pa_routes_content_caliber",
)


def _cluster_owners():
    _out = {}
    for _short in _CLUSTER_MODULES:
        _m = sys.modules.get("core.pa." + _short)
        if _m is None:
            continue
        for _k in vars(_m):
            if _k.startswith("__"):
                continue
            _out.setdefault(_k, []).append(_m)
    return _out


_OWNERS = _cluster_owners()


class _FacadeModule(types.ModuleType):
    u"""门面模块：写一名 ⇒ 同步至簇件之同名绑定（v0 单模块语义之保真）。"""

    def __setattr__(self, name, val):
        super().__setattr__(name, val)
        for _m in _OWNERS.get(name, ()):
            if _m is not self:
                types.ModuleType.__setattr__(_m, name, val)


sys.modules[__name__].__class__ = _FacadeModule
