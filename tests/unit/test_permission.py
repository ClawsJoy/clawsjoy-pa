# -*- coding: utf-8 -*-
"""块1(能改)专测 + 验收（2026-09-11）

验收：
  组1 老板改 cfgPerm -> 后端 permission.json 生效
  组2 PA 不能自改权限/分级（write_file 被拒）
  组3 现有功能不变（不在此文件，由其它测试覆盖）
"""
import sys

sys.path.insert(0, ".")

import pytest
from flask import Flask

from core.gateway.guards.registry import ForbiddenGuard
from core.pa.gateway_routes import register_pa_routes
from core.pa.permission import LEVELS, PermissionStore


# ---- 组1：权限档读写 + 白名单 ----
def test_store_default():
    ps = PermissionStore("/tmp/pa_test_perm_nonexistent.json")
    assert ps.get() == "标准"


def test_store_set_and_get(tmp_path):
    p = str(tmp_path / "permission.json")
    ps = PermissionStore(p)
    assert ps.set("高(需确认)", "boss").get("ok") is True
    # 重新实例化读回（模拟后端持久化）
    ps2 = PermissionStore(p)
    assert ps2.get() == "高(需确认)"


def test_store_reject_unknown_level(tmp_path):
    ps = PermissionStore(str(tmp_path / "permission.json"))
    r = ps.set("超管", "boss")
    assert r.get("ok") is False
    assert "权限档必须是" in r.get("error", "")


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    app = Flask(__name__)
    register_pa_routes(app)
    return app.test_client()


def test_route_permission_roundtrip(client):
    # 默认
    r = client.get("/v9/pa/permission?user_id=u1")
    assert r.get_json()["ok"] is True and r.get_json()["level"] == "标准"
    # 老板改档
    r = client.post("/v9/pa/permission", json={"user_id": "u1", "level": "只读"})
    assert r.get_json()["ok"] is True
    # 读回生效
    r = client.get("/v9/pa/permission?user_id=u1")
    assert r.get_json()["level"] == "只读"


def test_route_permission_reject_bad_value(client):
    r = client.post("/v9/pa/permission", json={"user_id": "u1", "level": "超管"})
    assert r.status_code == 400
    assert r.get_json()["ok"] is False


# ---- 组2：PA 不能自改规则（write_file 直写 permission.json 被 ForbiddenGuard 拒） ----
def test_forbidden_guard_blocks_permission_json():
    g = ForbiddenGuard()
    res = g.check({"tool": "write_file", "args": {"path": "data/v9/pa/permission.json", "content": "{}"}})
    assert res is not None and res.get("deny") is True
    assert res.get("status") == "forbidden"


def test_forbidden_guard_blocks_permission_json_deep_path():
    g = ForbiddenGuard()
    res = g.check({"tool": "write_file", "args": {"path": "/mnt/d/whatever/permission.json", "content": "{}"}})
    assert res is not None and res.get("deny") is True
