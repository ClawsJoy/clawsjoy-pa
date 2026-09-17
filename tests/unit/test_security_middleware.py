# -*- coding: utf-8 -*-
"""2026-09-08 GPT-6 阶段0 P0-3/P0-4: 安全中间件纯判定 — 沙箱限环回 + 外部强制认证(过渡)"""
import sys

sys.path.insert(0, ".")
import pytest

import core.lib.security_middleware as sm
from core.lib.security_middleware import check_access


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "unit-test-secret-0123456789abcdef")
    yield


def test_loopback_sandbox_allowed():
    assert check_access("/v9/sandbox/read", "127.0.0.1", body={"path": "x"}) == (None, None)


def test_external_sandbox_forbidden():
    code, err = check_access("/v9/sandbox/read", "203.0.113.9", body={"path": "x"})
    assert code == 403 and "仅允许本机环回" in err


def test_external_agent_requires_auth():
    code, err = check_access("/v9/agent/chat", "203.0.113.9")
    assert code == 401


def test_external_valid_token_passes():
    from core.lib.auth_middleware import get_auth_manager

    tok = get_auth_manager().generate_jwt("web_ext1")
    code, err = check_access("/v9/agent/chat", "203.0.113.9", auth_header="Bearer " + tok, body={"user_id": "web_ext1"})
    assert code is None


def test_external_user_id_mismatch_403():
    from core.lib.auth_middleware import get_auth_manager

    tok = get_auth_manager().generate_jwt("web_real")
    code, err = check_access("/v9/agent/chat", "203.0.113.9", auth_header="Bearer " + tok, body={"user_id": "web_evil"})
    assert code == 403 and "不符" in err


def test_claims_injects_user_id():
    from core.lib.auth_middleware import get_auth_manager

    tok = get_auth_manager().generate_jwt("web_auto")
    body = {"messages": []}
    code, err = check_access("/v9/agent/chat", "203.0.113.9", auth_header="Bearer " + tok, body=body)
    assert code is None
    assert body.get("user_id") == "web_auto"
