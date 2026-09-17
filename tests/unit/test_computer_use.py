# -*- coding: utf-8 -*-
"""computer_use 白名单动作测试（2026-09-10，路径 C 前置）

契约:
  1. 动作白名单: 未知 op 一律拒绝
  2. 只读/写分级: 写动作必须显式 allow_write=true
  3. 不假成功: 运行时不可用时返回明确 error + 启用步骤, 绝不返回成功
  4. 探测结果结构化: helper 路径 + cua_repl 是否启用
"""
import os
import sys

sys.path.insert(0, ".")
import pytest

sys.path.insert(0, "scripts/agent_client")
import computer_use as CU


@pytest.fixture()
def fake_env(tmp_path, monkeypatch):
    """造一个假的 %LOCALAPPDATA% / %USERPROFILE% 环境。"""
    la = tmp_path / "LocalAppData"
    up = tmp_path / "UserProfile"
    helper_dir = (
        la
        / "OpenAI"
        / "Codex"
        / "runtimes"
        / "cua_node"
        / "deadbeef"
        / "bin"
        / "node_modules"
        / "@oai"
        / "cua"
        / "bin"
        / "windows"
    )
    helper_dir.mkdir(parents=True)
    helper = helper_dir / "codex-computer-use.exe"
    helper.write_bytes(b"MZ fake")
    (up / ".codex").mkdir(parents=True)
    monkeypatch.setenv("LOCALAPPDATA", str(la))
    monkeypatch.setenv("USERPROFILE", str(up))
    monkeypatch.delenv("PA_CUA_HELPER", raising=False)
    return {"helper": str(helper), "config": up / ".codex" / "config.toml"}


# ---- 1) 白名单 ----
def test_unknown_op_rejected():
    r = CU.computer_use({"op": "rm_rf_everything"})
    assert "error" in r and "不支持 op" in r["error"]


def test_missing_op_rejected():
    r = CU.computer_use({})
    assert "error" in r and "需要 op" in r["error"]


def test_envelope_action_key_ignored():
    """网关切下发 params 会带 action, 不得因此被拒"""
    r = CU.computer_use({"action": "computer_use", "op": "nope"})
    assert "不支持 op" in r["error"]  # 报的是 op 的问题, 不是 action 的问题


# ---- 2) 只读/写分级 ----
@pytest.mark.parametrize("op", ["click", "type_text", "press_key", "set_value", "launch_app", "activate_window"])
def test_write_ops_require_allow_write(op, fake_env):
    r = CU.computer_use({"op": op})
    assert "error" in r and "allow_write" in r["error"], r


def test_read_ops_do_not_require_allow_write(fake_env):
    """只读不因 allow_write 缺失被拒（会走到"运行时不可用", 但那是另一回事）"""
    r = CU.computer_use({"op": "list_windows"})
    assert "allow_write" not in str(r.get("error", ""))


def test_read_and_write_sets_disjoint_and_reasonable():
    assert set(CU.READ_OPS) & set(CU.WRITE_OPS) == set()
    for must in ("list_windows", "list_apps", "get_window_state", "get_screenshot"):
        assert must in CU.READ_OPS
    for must in ("click", "type_text", "press_key", "set_value", "launch_app", "activate_window"):
        assert must in CU.WRITE_OPS


# ---- 3) 不假成功 ----
def test_not_available_returns_error_not_success(fake_env):
    """helper 在但 cua_repl 未启用 -> 必须报错, 且给出启用步骤"""
    fake_env["config"].write_text("[mcp_servers.cua_repl]\ncommand = 'x'\nenabled = false\n", encoding="utf-8")
    r = CU.computer_use({"op": "list_windows"})
    assert "error" in r and "不可用" in r["error"]
    assert "how_to_enable" in r and len(r["how_to_enable"]) >= 3
    assert "result" not in r, "不可用时绝不能返回 result"


def test_missing_helper_reported(fake_env, monkeypatch):
    os.remove(fake_env["helper"])
    fake_env["config"].write_text("[mcp_servers.cua_repl]\nenabled = true\n", encoding="utf-8")
    r = CU.computer_use({"op": "list_windows"})
    assert "未找到 codex-computer-use.exe" in r["error"]


def test_helper_failure_is_not_success(fake_env, monkeypatch):
    """helper 存在且已启用, 但它自己报 ok:false -> 必须原样当失败"""
    fake_env["config"].write_text("[mcp_servers.cua_repl]\nenabled = true\n", encoding="utf-8")

    class P:
        returncode = 0
        stdout = b'{"id":1,"ok":false,"error":"failed to launch codex app-server: program not found"}'
        stderr = b""

    monkeypatch.setattr(CU.subprocess, "run", lambda *a, **k: P())
    r = CU.computer_use({"op": "list_windows"})
    assert "error" in r and "helper 拒绝" in r["error"]
    assert "result" not in r


# ---- 4) 探测 ----
def test_probe_shape(fake_env):
    fake_env["config"].write_text("[mcp_servers.cua_repl]\nenabled = true\n", encoding="utf-8")
    info = CU.probe()
    assert info["available"] is True
    assert info["helper"] == fake_env["helper"]
    assert info["cua_repl_enabled"] is True
    assert info["read_ops"] and info["write_ops"]


def test_probe_disabled_config(fake_env):
    fake_env["config"].write_text("[mcp_servers.cua_repl]\nenabled = false\n", encoding="utf-8")
    info = CU.probe()
    assert info["available"] is False and "未启用" in info["reason"]


def test_toml_parse_is_conservative(fake_env):
    """配置里没有该段 -> 当未启用（保守）"""
    fake_env["config"].write_text("[other]\nenabled = true\n", encoding="utf-8")
    ok, why = CU.cua_repl_enabled()
    assert ok is False and "没有" in why
