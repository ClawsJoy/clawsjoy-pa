# -*- coding: utf-8 -*-
"""9.0.93：安装版 5103 / 开发版 5102 的隔离与 IPC sender 闸（静态回归）。"""
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _port_from_yaml(p):
    text = p.read_text(encoding="utf-8")
    lines = text.splitlines()
    in_gateway = False
    for line in lines:
        s = line.strip()
        if s == "gateway:" and line.startswith("  "):
            in_gateway = True
            continue
        if in_gateway and s.startswith("port:"):
            return int(s.split(":", 1)[1].strip())
        if in_gateway and s and not line.startswith("    "):
            in_gateway = False
    raise AssertionError("no services.gateway.port in %s" % p)


def test_repo_and_payload_ports_are_split():
    assert _port_from_yaml(ROOT / "config" / "system" / "system_unified.yaml") == 5102
    payload = ROOT / "dist" / "pa_shell" / "payload"
    cfg = payload / "config" / "system" / "system_unified.yaml"
    if cfg.exists():
        assert _port_from_yaml(cfg) == 5103
        exe = payload / "runtime" / "python.exe"
        pl = payload / "scripts" / "win_pa" / "port_lite.py"
        if exe.exists() and pl.exists():
            out = subprocess.check_output([str(exe), str(pl), "--root", str(payload)], text=True).strip()
            assert out.splitlines()[-1] == "5103"


def test_release_script_pins_port():
    p = ROOT / "scripts" / "win_pa" / "release_pa.ps1"
    s = p.read_text(encoding="utf-8")
    assert "--gateway-port $Port" in s
    assert "$Port = 5103" in s
    assert "make_payload.py" in s


def test_dev_launcher_isolates_data():
    s = (ROOT / "scripts" / "win_pa" / "start_dev.ps1").read_text(encoding="utf-8")
    assert "PA_DATA_DIR" in s and "data-dev" in s


def test_shell_has_ipc_guard_and_no_auto_kill():
    s = (ROOT / "shell" / "main.js").read_text(encoding="utf-8")
    assert "ipcSenderTrusted" in s
    assert "E_SENDER" in s
    assert "clearStaleGateway" not in s
    assert "execFileSync" not in s


def test_smoke_script_covers_both_ports():
    s = (ROOT / "scripts" / "win_pa" / "smoke_dual_ports.ps1").read_text(encoding="utf-8")
    assert "5103" in s and "5102" in s
    assert "build.path" in s
