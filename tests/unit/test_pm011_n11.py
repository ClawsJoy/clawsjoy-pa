# -*- coding: utf-8 -*-
r"""PM-011 N11 · 六键 10 处**专属反例门**（CW `b2a5182` · 2026-09-30）。

PM 2026-09-30 19:0x 裁：**批「动手改码」**（⛔ 不含重启）。
范围：`session_id` ／ `path` ／ `query` ／ `task_spec` ／ `temp_path` ／ `url` 六键
⇒ **统一 400**，文案统一形制 **`<路由>: 缺 <键>`**。

每处一齿（⛔ 不许搭车）：**缺该键**（⚠ 载荷**非空** —— 空载荷会被形状守卫先拦，
测不到本处）⇒ **400 ＋ 文案含路由 ＋ `缺 <键>`**；
反向臂：**好形状 ⇒ ⛔ 守卫不误伤**（同臂把 `status+body` 记进 `N11_ARM_OUT`，供两臂逐字比对）。

⛔ 本文件**不写生产面**：cwd 隔离 ＋ `_TOOL_METRICS_PATH` 指 tmp ＋ 下游写点全替身。
"""
from __future__ import annotations

import json
import os

import pytest
from flask import Flask

BAD_KEY = "缺 "


def _record(_id, _route, _status, _body):
    _p = os.environ.get("N11_ARM_OUT")
    if not _p:
        return
    with open(_p, "a", encoding="utf-8") as _f:
        _f.write(json.dumps({"id": _id, "route": _route, "status": _status, "body": _body}, ensure_ascii=False, sort_keys=True) + "\n")


def _err(_r):
    _j = _r.get_json() or {}
    return _j.get("error") or ""


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _sb = tmp_path / "sb"
    (_sb / "clawsjoy_dev").mkdir(parents=True, exist_ok=True)
    (_sb / "clawsjoy_dev" / "a.txt").write_text("hello-n11\n", encoding="utf-8")

    import core.lib.gateway_helpers as _gh
    import core.gateway.sandbox_ops as _so
    import core.gateway.sandbox_write as _sw
    import core.context.context_manager as _cm

    monkeypatch.setattr(_gh, "_get_sandbox_base", lambda uid, sid: _sb)
    monkeypatch.setattr(_so, "_get_sandbox_base", lambda uid, sid: _sb)
    monkeypatch.setattr(_sw, "_get_sandbox_base", lambda uid, sid: _sb)
    # 指标面指 tmp（否则落 PROJECT_ROOT ⇒ 生产写）
    monkeypatch.setattr(_cm, "_TOOL_METRICS_PATH", str(tmp_path / "_metrics.jsonl"), raising=False)
    # 下游写点替身（⛔ 不碰 profile/ledger/git）
    for _m in (_so, _sw):
        monkeypatch.setattr(_m, "_record_path_pattern", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(_sw, "_sandbox_git_pre_write", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(_sw, "_sandbox_git_post_write", lambda *a, **k: "", raising=False)
    monkeypatch.setattr(_sw, "_update_world_model", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(_sw, "_git_status", lambda *a, **k: [], raising=False)

    _st = {"escalations": [{"timestamp": "2026-08-22T07:40:00", "tool": "write_file", "target": "/etc/hosts", "reason": "x", "action": "blocked"}]}
    (_sb / ".agent_state.json").write_text(json.dumps(_st, ensure_ascii=False), encoding="utf-8")

    _app = Flask(__name__)
    _app.config["PROPAGATE_EXCEPTIONS"] = False
    import routes.sandbox as _rs
    import routes.audit as _ra
    import routes.session as _rsess
    import routes.metrics as _rm

    _app.register_blueprint(_rs.bp)
    _app.register_blueprint(_ra.bp)
    _app.register_blueprint(_rsess.bp)
    _app.register_blueprint(_rm.bp)
    _sw.register_write_routes(_app)
    return _app.test_client(), _sb, tmp_path


def _fire(_c, _id, _route, _method, _kw, _want_key):
    _r = _c.get(_route) if _method == "get" else _c.post(_route, json=_kw)
    _j = _r.get_json()
    _record(_id, _route, _r.status_code, _j)
    return _r, _j


# ==================== 齿 1-3 · routes/audit.py（session_id） ====================

def test_n11_01_audit_escalations_missing_session(env):
    _c = env[0]
    _r, _j = _fire(_c, "01", "/v9/audit/escalations?user_id=u1", "get", None, None)
    assert _r.status_code == 400, "须 400（实测 %s）：%s" % (_r.status_code, _r.data[:200])
    assert "v9/audit/escalations" in _err(_r) and "缺 session_id" in _err(_r), _err(_r)


def test_n11_02_audit_tool_flow_missing_session(env):
    _c = env[0]
    _r, _j = _fire(_c, "02", "/v9/audit/tool_flow", "get", None, None)
    assert _r.status_code == 400, "须 400（实测 %s）" % _r.status_code
    assert "v9/audit/tool_flow" in _err(_r) and "缺 session_id" in _err(_r), _err(_r)


def test_n11_03_audit_approvals_missing_session(env):
    _c = env[0]
    _r, _j = _fire(_c, "03", "/v9/audit/approvals?user_id=u1", "get", None, None)
    assert _r.status_code == 400, "须 400（实测 %s）" % _r.status_code
    assert "v9/audit/approvals" in _err(_r) and "缺 session_id" in _err(_r), _err(_r)


# ==================== 齿 4-6 · core/gateway/sandbox_ops.py ====================

def test_n11_04_sandbox_read_missing_path(env):
    _c = env[0]
    _r, _j = _fire(_c, "04", "/v9/sandbox/read", "post", {"user_id": "u", "session_id": "s"}, None)
    assert _r.status_code == 400, "须 400（实测 %s）：%s" % (_r.status_code, _r.data[:200])
    assert "v9/sandbox/read" in _err(_r) and "缺 path" in _err(_r), _err(_r)


def test_n11_05_sandbox_edit_missing_path(env):
    _c = env[0]
    _r, _j = _fire(_c, "05", "/v9/sandbox/edit", "post", {"user_id": "u", "session_id": "s"}, None)
    assert _r.status_code == 400, "须 400（实测 %s）" % _r.status_code
    assert "v9/sandbox/edit" in _err(_r) and "缺 path" in _err(_r), _err(_r)


def test_n11_06_sandbox_query_index_missing_query(env):
    _c = env[0]
    _r, _j = _fire(_c, "06", "/v9/sandbox/query_index", "post", {"user_id": "u", "session_id": "s"}, None)
    assert _r.status_code == 400, "须 400（实测 %s）" % _r.status_code
    assert "v9/sandbox/query_index" in _err(_r) and "缺 query" in _err(_r), _err(_r)


# ==================== 齿 7-9 · core/gateway/sandbox_write.py ====================

def test_n11_07_sandbox_write_missing_path(env):
    _c = env[0]
    _r, _j = _fire(_c, "07", "/v9/sandbox/write", "post", {"user_id": "u", "session_id": "s", "content": "x"}, None)
    assert _r.status_code == 400, "须 400（实测 %s）：%s" % (_r.status_code, _r.data[:200])
    assert "v9/sandbox/write" in _err(_r) and "缺 path" in _err(_r), _err(_r)


def test_n11_08_write_finalize_missing_path(env):
    _c = env[0]
    _r, _j = _fire(_c, "08", "/v9/sandbox/write_finalize", "post", {"user_id": "u", "session_id": "s", "temp_path": "/x"}, None)
    assert _r.status_code == 400, "须 400（实测 %s）" % _r.status_code
    assert "v9/sandbox/write_finalize" in _err(_r) and "缺 path" in _err(_r), _err(_r)


def test_n11_09_write_finalize_missing_temp_path(env):
    _c = env[0]
    _r, _j = _fire(_c, "09", "/v9/sandbox/write_finalize", "post", {"user_id": "u", "session_id": "s", "path": "clawsjoy_dev/c.txt"}, None)
    assert _r.status_code == 400, "须 400（实测 %s）" % _r.status_code
    assert "v9/sandbox/write_finalize" in _err(_r) and "缺 temp_path" in _err(_r), _err(_r)


# ==================== 齿 10-12 · session / metrics（含 400 侧文案统一） ====================

def test_n11_10_subtask_create_missing_task_spec(env):
    _c = env[0]
    _r, _j = _fire(_c, "10", "/v9/subtask/create", "post", {"user_id": "u", "session_id": "s"}, None)
    assert _r.status_code == 400, "须 400（实测 %s）" % _r.status_code
    assert "v9/subtask/create" in _err(_r) and "缺 task_spec" in _err(_r), _err(_r)


def test_n11_11_fetch_missing_url(env):
    _c = env[0]
    _r, _j = _fire(_c, "11", "/v9/fetch", "get", None, None)
    assert _r.status_code == 400, "须 400（实测 %s）" % _r.status_code
    assert "v9/fetch" in _err(_r) and "缺 url" in _err(_r), _err(_r)


def test_n11_12_preempt_missing_session_wording_unified(env):
    """⭐ N11 名单内的 **400 侧** 文案统一（原 `缺少 session_id` ⇒ `<路由>: 缺 session_id`）。"""
    _c = env[0]
    _r, _j = _fire(_c, "12", "/v9/preempt", "post", {}, None)
    assert _r.status_code == 400, "须 400（实测 %s）" % _r.status_code
    assert _err(_r) == "v9/preempt: 缺 session_id", _err(_r)


# ==================== 反向臂 · 好形状 ⇒ ⛔ 守卫不误伤 ====================

def test_n11_r01_escalations_good_shape(env):
    _c = env[0]
    _r, _j = _fire(_c, "r01", "/v9/audit/escalations?user_id=u1&session_id=s1", "get", None, None)
    assert _r.status_code == 200, _r.status_code
    assert _j.get("success") is True and len(_j.get("escalations") or []) == 1, _j


def test_n11_r02_tool_flow_good_shape(env):
    _c = env[0]
    _r, _j = _fire(_c, "r02", "/v9/audit/tool_flow?session_id=s1", "get", None, None)
    assert _r.status_code == 200 and _j.get("success") is True, (_r.status_code, _j)


def test_n11_r03_approvals_good_shape(env):
    _c = env[0]
    _r, _j = _fire(_c, "r03", "/v9/audit/approvals?user_id=u1&session_id=s1", "get", None, None)
    assert _r.status_code == 200 and _j.get("success") is True, (_r.status_code, _j)


def test_n11_r04_sandbox_read_good_shape(env):
    _c = env[0]
    _r, _j = _fire(_c, "r04", "/v9/sandbox/read", "post", {"user_id": "u", "session_id": "s", "path": "clawsjoy_dev/a.txt"}, None)
    assert _r.status_code == 200, "好形状 ⛔ 不该被守卫拦（实测 %s）：%s" % (_r.status_code, _r.data[:200])
    assert "缺 path" not in _err(_r), _err(_r)


def test_n11_r05_sandbox_edit_good_shape(env):
    _c = env[0]
    _r, _j = _fire(_c, "r05", "/v9/sandbox/edit", "post", {"user_id": "u", "session_id": "s", "path": "clawsjoy_dev/a.txt", "prompt": "hello-n11", "suffix": "HELLO-N11"}, None)
    assert _r.status_code != 400, "好形状 ⛔ 不该被守卫拦（实测 %s）：%s" % (_r.status_code, _r.data[:200])
    assert "缺 path" not in _err(_r), _err(_r)


def test_n11_r06_sandbox_query_index_good_shape(env):
    _c = env[0]
    _r, _j = _fire(_c, "r06", "/v9/sandbox/query_index", "post", {"user_id": "u", "session_id": "s", "query": "hello"}, None)
    assert _r.status_code != 400, "好形状 ⛔ 不该被守卫拦（实测 %s）" % _r.status_code
    assert "缺 query" not in _err(_r), _err(_r)


def test_n11_r07_sandbox_write_good_shape(env):
    _c = env[0]
    _r, _j = _fire(_c, "r07", "/v9/sandbox/write", "post", {"user_id": "u", "session_id": "s", "path": "clawsjoy_dev/b.txt", "content": "hi"}, None)
    assert _r.status_code != 400, "好形状 ⛔ 不该被守卫拦（实测 %s）：%s" % (_r.status_code, _r.data[:200])
    assert "缺 path" not in _err(_r), _err(_r)


def test_n11_r08_write_finalize_good_shape(env):
    _c, _sb, _tmp = env
    _tmpf = _tmp / "tmpfile.txt"
    _tmpf.write_text("fin\n", encoding="utf-8")
    _r, _j = _fire(_c, "r08", "/v9/sandbox/write_finalize", "post", {"user_id": "u", "session_id": "s", "path": "clawsjoy_dev/c.txt", "temp_path": str(_tmpf)}, None)
    assert _r.status_code != 400, "好形状 ⛔ 不该被守卫拦（实测 %s）：%s" % (_r.status_code, _r.data[:200])
    assert "缺 path" not in _err(_r) and "缺 temp_path" not in _err(_r), _err(_r)


def test_n11_r09_subtask_create_good_shape(env, monkeypatch):
    _c = env[0]
    import core.gateway.subtask_executor as _se

    monkeypatch.setattr(_se, "resolve_depth", lambda _d: 1, raising=False)
    monkeypatch.setattr(_se, "submit", lambda *a, **k: "tid-n11", raising=False)
    _r, _j = _fire(_c, "r09", "/v9/subtask/create", "post", {"user_id": "u", "session_id": "s", "task_spec": "do x"}, None)
    assert _r.status_code != 400, "好形状 ⛔ 不该被守卫拦（实测 %s）：%s" % (_r.status_code, _r.data[:200])
    assert "缺 task_spec" not in _err(_r), _err(_r)


def test_n11_r10_fetch_good_shape(env, monkeypatch):
    _c = env[0]
    import core.tools.fetch_web as _fw

    monkeypatch.setattr(_fw.FetchWebPlugin, "execute", lambda self, args, ctx: {"success": True, "url": "https://example.com/x", "content": "abc", "truncated": False, "length": 3})
    _r, _j = _fire(_c, "r10", "/v9/fetch?url=https://example.com/x", "get", None, None)
    assert _r.status_code == 200 and _j.get("success") is True, (_r.status_code, _j)


def test_n11_r11_preempt_good_shape(env):
    _c = env[0]
    _r, _j = _fire(_c, "r11", "/v9/preempt", "post", {"session_id": "s1", "reason": "r"}, None)
    assert _r.status_code == 200 and _j.get("success") is True, (_r.status_code, _j)
