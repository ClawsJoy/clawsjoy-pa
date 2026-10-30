# -*- coding: utf-8 -*-
"""PM-3406 §③B ／ T50：PA 写路由 owner 守卫（现基线 55/55 ＋ 每条反例 rc）。

契约：docs/design/v9_pa_owner_guard_contract_v0.md（v0 记 45 条 · 2026-10-27）
守卫：core/pa/owner_guard.py（门面一处装 · 蓝图 before_request）

基线（T50 · 2026-10-30）：写路由 **55** 条（POST 53 ／ DELETE 1 ／ PATCH 1）。
  契约（45 条）之后新增 10 条写路由（notes 簇 9 ＋ self_intro 1）⇒ 旧断 ==45 已漂
  （属基线陈旧，**非**守卫失效；T44 一手已逐条证 55/55 反例 403、正例 200）。
  本件按**每条 rule 之合法写方法**发请求（⛔ 恒 POST —— 否则 /v9/pa/notes/<note_id>
  之 DELETE ／ PATCH 二 rule 在路由层先 405，误红且未验闸）。

安全：反例/正例皆把 55 个 view 换成桩（不触真逻辑）⇒ 断言只看闸之 rc。
"""
import os
import sys

import pytest
from flask import Flask

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.pa import owner_guard
from core.pa.gateway_routes import register_pa_routes


@pytest.fixture(scope="module")
def app():
    a = Flask("pa_route_guard_test")
    register_pa_routes(a, brain=None)
    # 全部 PA 端点 ⇒ 桩（闸不过才可能到此处 ⇒ 到即 200 暴露假绿）
    for rule in a.url_map.iter_rules():
        if str(rule.endpoint).startswith("pa_routes."):
            a.view_functions[rule.endpoint] = _stub
    return a


def _stub(**kwargs):
    return ("reached", 200)


def _write_rules(a):
    out = []
    for rule in a.url_map.iter_rules():
        if not str(rule.endpoint).startswith("pa_routes."):
            continue
        methods = sorted(m for m in (rule.methods or ()) if m not in ("HEAD", "OPTIONS"))
        if set(methods) & set(owner_guard.WRITE_METHODS):
            out.append(rule)
    return sorted(out, key=lambda r: (str(r), r.endpoint))


def _write_methods(rule):
    """该 rule 之**合法写方法**（升序；无写方法 ⇒ 空）。"""
    return sorted(m for m in (rule.methods or ())
                  if m not in ("HEAD", "OPTIONS") and m in owner_guard.WRITE_METHODS)


def _path(rule):
    p = str(rule)
    for arg in rule.arguments:
        p = p.replace("<%s>" % arg, "x")
    return p


def _call(client, rule, remote, token=""):
    """以**该 rule 之合法写方法**发（⛔ 恒 POST · T50）。

    405 之由（T44 一手）：routing 早于 before_request ⇒ 若以 POST 打
    DELETE ／ PATCH 之 rule，则未到闸已 405 ⇒ 只能证“方法不允”，不能证“闸拒”。
    """
    methods = _write_methods(rule)
    method = methods[0] if methods else "POST"
    headers = {"Authorization": "Bearer " + token} if token else {}
    return client.open(_path(rule), method=method, headers=headers,
                       environ_overrides={"REMOTE_ADDR": remote})


def test_write_route_inventory_is_55(app):
    """写路由清单 ＝ 现基线 **55**（T50 · 45→55）＋ 方法分布锁 POST 53 ／ DELETE 1 ／ PATCH 1。"""
    rules = _write_rules(app)
    dist = {}
    for rule in rules:
        for m in _write_methods(rule):
            dist[m] = dist.get(m, 0) + 1
    assert len(rules) == 55, [str(r) for r in rules]
    assert dist == {"POST": 53, "DELETE": 1, "PATCH": 1}, dist


def test_guard_registered_on_pa_routes_blueprint(app):
    funcs = app.before_request_funcs.get("pa_routes") or []
    assert any(getattr(f, "__name__", "") == "_owner_gate" for f in funcs)


def test_owner_ok_loopback_true():
    class _R:
        remote_addr = "127.0.0.1"
        headers = {}
    assert owner_guard.owner_ok(_R()) is True


def test_owner_ok_remote_without_token_false(monkeypatch):
    monkeypatch.delenv("AUTH_EXTERNAL_REQUIRE", raising=False)

    class _R:
        remote_addr = "10.9.9.9"
        headers = {}
    assert owner_guard.owner_ok(_R()) is False


def test_owner_ok_remote_bad_token_false(monkeypatch):
    monkeypatch.delenv("AUTH_EXTERNAL_REQUIRE", raising=False)

    class _R:
        remote_addr = "10.9.9.9"
        headers = {"Authorization": "Bearer not-a-token"}
    assert owner_guard.owner_ok(_R()) is False


def test_owner_ok_remote_valid_jwt_true(monkeypatch):
    monkeypatch.delenv("AUTH_EXTERNAL_REQUIRE", raising=False)
    from core.lib.auth_middleware import get_auth_manager

    tok = get_auth_manager().generate_jwt("u_guard_test")

    class _R:
        remote_addr = "10.9.9.9"
        headers = {"Authorization": "Bearer " + tok}
    assert owner_guard.owner_ok(_R()) is True


def test_55_write_routes_negative_all_403(app, monkeypatch):
    """反例（逐条）：非环回 ＋ 无凭证 ⇒ 403（按各 rule 合法写方法）。"""
    monkeypatch.delenv("AUTH_EXTERNAL_REQUIRE", raising=False)
    c = app.test_client()
    rows = []
    for rule in _write_rules(app):
        r = _call(c, rule, "10.9.9.9")
        rows.append((str(rule), _write_methods(rule), r.status_code))
    print("\n# 反例 %d 条（rc ／ 按各 rule 合法写方法）：" % len(rows))
    for p, ms, rc in rows:
        print("rc=%d  %-6s  %s" % (rc, "/".join(ms), p))
    assert len(rows) == 55
    assert all(rc == 403 for _, _, rc in rows), [x for x in rows if x[2] != 403]


def test_55_write_routes_positive_loopback(app):
    c = app.test_client()
    bad = []
    for rule in _write_rules(app):
        r = _call(c, rule, "127.0.0.1")
        if r.status_code != 200:
            bad.append((str(rule), _write_methods(rule), r.status_code))
    assert not bad, bad


def test_55_write_routes_positive_remote_jwt(app, monkeypatch):
    monkeypatch.delenv("AUTH_EXTERNAL_REQUIRE", raising=False)
    from core.lib.auth_middleware import get_auth_manager

    tok = get_auth_manager().generate_jwt("u_guard_test")
    c = app.test_client()
    bad = []
    for rule in _write_rules(app):
        r = _call(c, rule, "10.9.9.9", tok)
        if r.status_code != 200:
            bad.append((str(rule), _write_methods(rule), r.status_code))
    assert not bad, bad
