# -*- coding: utf-8 -*-
"""local_actions 白名单动作测试（2026-09-10）
Linux 上可测：路径校验/参数拒绝/非 Windows 优雅失败（不假装成功）。
"""
import os
import sys

sys.path.insert(0, "scripts/agent_client")
import local_actions as L
import pytest


def test_allowed_exts_pass_on_desktop(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_LOCAL_DIRS", str(tmp_path))
    f = tmp_path / "a.pptx"
    f.write_text("x", encoding="utf-8")
    ok, err = L.validate_path(str(f))
    assert ok, err


@pytest.mark.parametrize("name", ["evil.sh", "run.exe", "script.py", "x.bat", "x"])
def test_disallowed_exts_rejected(tmp_path, monkeypatch, name):
    monkeypatch.setenv("AGENT_LOCAL_DIRS", str(tmp_path))
    f = tmp_path / name
    f.write_text("x", encoding="utf-8")
    ok, err = L.validate_path(str(f))
    assert not ok and "扩展名" in err


def test_path_outside_whitelist_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_LOCAL_DIRS", str(tmp_path / "allowed"))
    other = tmp_path / "other"
    other.mkdir(parents=True, exist_ok=True)
    f = other / "a.pdf"
    f.write_text("x", encoding="utf-8")
    ok, err = L.validate_path(str(f))
    assert not ok and "目录不在白名单" in err


def test_traversal_rejected(tmp_path, monkeypatch):
    """../ 穿越到白名单外应被拒（realpath 归一后比较）"""
    allowed = tmp_path / "allowed"
    allowed.mkdir(parents=True, exist_ok=True)
    outside = tmp_path / "secret.pdf"
    outside.write_text("x", encoding="utf-8")
    monkeypatch.setenv("AGENT_LOCAL_DIRS", str(allowed))
    ok, err = L.validate_path(str(allowed / ".." / "secret.pdf"))
    assert not ok, "路径穿越未被拦截: %s" % err


def test_empty_path_rejected():
    ok, err = L.validate_path("")
    assert not ok and "必填" in err


def test_open_document_rejects_extra_params(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_LOCAL_DIRS", str(tmp_path))
    f = tmp_path / "a.pptx"
    f.write_text("x", encoding="utf-8")
    r = L.open_document({"path": str(f), "cmd": "calc.exe"})
    assert "error" in r and "不接受参数" in r["error"]


def test_open_document_non_windows_graceful(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_LOCAL_DIRS", str(tmp_path))
    f = tmp_path / "a.pptx"
    f.write_text("x", encoding="utf-8")
    r = L.open_document({"path": str(f)})
    if sys.platform == "win32":
        assert "opened" in r
    else:
        assert "error" in r and "仅支持 Windows" in r["error"], r


def test_close_wps_rejects_custom_proc():
    r = L.close_wps({"proc": "explorer.exe"})
    assert "error" in r and "不接受参数" in r["error"]


def test_close_wps_non_windows_graceful():
    r = L.close_wps({})
    if sys.platform == "win32":
        assert "closed" in r
    else:
        assert "error" in r and "仅支持 Windows" in r["error"], r


def test_lingxi_mcp_never_fakes_success():
    r = L.lingxi_mcp({})
    assert ("error" in r) or ("config_dirs" in r)  # 有配置就报目录，没有就明确报错


def test_dispatch_strips_envelope_action():
    """网关下发的 params 带 "action"(完整 args), dispatch 必须摘掉后转发"""
    r = L.dispatch("open_document", {"action": "open_document", "path": ""})
    assert "path 必填" in r["error"], r  # 未因多余 action 键被拒


def test_dispatch_rejects_mismatched_action():
    r = L.dispatch("open_document", {"action": "close_wps", "path": "x.pdf"})
    assert "不一致" in r["error"], r


def test_dispatch_unknown():
    assert "unknown local action" in L.dispatch("nope", {})["error"]


def test_local_actions_registry():
    assert L.LOCAL_ACTIONS == {"open_document", "close_wps", "lingxi_mcp", "computer_use"}


# --- 回归: 网关白名单漂移事故 (2026-09-10) ---------------------------------
# 事故: 新增 3 个本地动作时只改了 schema enum, 漏改 execute() 内手写的 valid 集合,
# 导致动作通过 schema 校验后死在运行时校验(unsupported action), 端到端全断。
# 契约: 客户端 LOCAL_ACTIONS ⊆ 网关 VALID_ACTIONS ⊆ schema enum, 三者必须一致。
def test_gateway_whitelist_matches_schema_enum():
    from core.tools.browser_local import BROWSER_LOCAL_SCHEMA, VALID_ACTIONS

    enum = set(BROWSER_LOCAL_SCHEMA["function"]["parameters"]["properties"]["action"]["enum"])
    assert set(VALID_ACTIONS) == enum, "运行时白名单与 schema enum 漂移: %s" % (enum ^ set(VALID_ACTIONS))


def test_client_local_actions_accepted_by_gateway():
    from core.tools.browser_local import VALID_ACTIONS

    missing = set(L.LOCAL_ACTIONS) - set(VALID_ACTIONS)
    assert not missing, "客户端本地动作网关不认(会报 unsupported action): %s" % sorted(missing)


def test_core_local_system_actions_equals_client():
    """PA 路由 /v9/pa/act 的放行集合必须等于客户端白名单(否则 PA 派不下去或派了没人认)"""
    from core.tools.browser_local import LOCAL_SYSTEM_ACTIONS, VALID_ACTIONS

    assert set(LOCAL_SYSTEM_ACTIONS) == set(L.LOCAL_ACTIONS)
    assert set(LOCAL_SYSTEM_ACTIONS) <= set(VALID_ACTIONS)
