# -*- coding: utf-8 -*-
u"""pm_1684 §一 之齿：`pa_update.probe_health` 之**端口与「根」绑定** ＋ **身份对证**
（TD f202f89 · 2026-10-07）。

病（本席一手所逮 · 承 pm_1684 §一）：昔 `port = gateway_port()` 经 `unified_config`，
  其按 **CWD** 解 `config/system/system_unified.yaml` ⇒ 器自他处起（沙箱副本 · 端口 8994）
  而 CWD 在活端之树 ⇒ 竟探 `5102`（**活端之答**）⇒ 「他根之健康」充「本根之正控」
  ＝「未知 ⛔ 充已知」之族（正控假绿；反则活端不答 ⇒ 假红 · 无端回滚）。

判据（正 ／ 反控）：
  P1 ⭐⭐正控（**根绑** · 复现昔之险）：CWD 在一「端口 5102 之树」∧ 探他根（端口 P）
      ⇒ **须探 P**（唯 P 之桩答 · 其 `version` 逐字见于 rows）—— 昔之码此处探 5102 ⇒ 红。
  P2 ⭐反控（身份）：桩答之 `build.path` ⛔ 本根 ⇒ **拒**（⛔ 以他根之健康充本根）
  P3 正控：桩答之 `build.path` ＝ 本根 ⇒ **过**
  P4 反控：根之端口 ⛔ 可读（无真源）⇒ **拒**（fail-loud · 明书去处；⛔ 回落字面 5102）
  P5 显式 `port` ⇒ 优先（供齿 ／ 试 · ⛔ 经真源）

以何形调用（判通 ／ 断须附）：
  python -X utf8 -B -m pytest tests/unit/test_win_pa_probe_health_1684.py -q
"""
from __future__ import annotations

import importlib.util
import json
import os
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WIN_PA = ROOT / "scripts" / "win_pa"
if str(WIN_PA) not in sys.path:
    sys.path.insert(0, str(WIN_PA))


def _load_pa_update():
    spec = importlib.util.spec_from_file_location("pa_update_1684", str(WIN_PA / "pa_update.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PU = _load_pa_update()


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class _Stub(BaseHTTPRequestHandler):
    payload = {}

    def do_GET(self):                                          # noqa: N802
        body = json.dumps(type(self).payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):                                 # 静默
        pass


def _serve(payload, port):
    _Stub.payload = payload
    srv = HTTPServer(("127.0.0.1", port), _Stub)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    return srv


def _mkroot(base, name, port):
    r = base / name
    (r / "config" / "system").mkdir(parents=True)
    cfg = r / "config" / "system" / "system_unified.yaml"
    cfg.write_text(u"services:\n  gateway:\n    host: 0.0.0.0\n    port: %d\n" % port,
                   encoding="utf-8")
    (r / "version.json").write_text(json.dumps({"version": "9.0.3"}), encoding="utf-8")
    return r


def test_P1_port_bound_to_root(tmp_path, monkeypatch):
    u"""P1：CWD 在「5102 之树」∧ 探他根（端口 P）⇒ 须探 P（唯 P 之桩答）。"""
    port = _free_port()
    R = _mkroot(tmp_path, "R", port)
    C = _mkroot(tmp_path, "C", 5102)                            # 伪活端之树（旧码会探它）
    srv = _serve({"status": "healthy", "version": "STUB-P1",
                  "build": {"available": True, "path": str(R / "version.json")}}, port)
    old = os.getcwd()
    try:
        os.chdir(str(C))                                       # 复现昔之险：CWD 之配置为 5102
        ok, rows = PU.probe_health(str(R), wait_s=5.0)
    finally:
        os.chdir(old)
        srv.shutdown()
    assert ok is True, rows
    assert any("STUB-P1" in r for r in rows), rows              # 证其**真探 P**（⛔ 5102）


def test_P2_identity_reject(tmp_path):
    u"""P2：他根之健康 ⇒ 拒（build.path ⛔ 本根）。"""
    port = _free_port()
    R = _mkroot(tmp_path, "R", port)
    other = tmp_path / "other" / "version.json"
    srv = _serve({"status": "healthy", "version": "9.0.1",
                  "build": {"available": True, "path": str(other)}}, port)
    try:
        ok, rows = PU.probe_health(str(R), wait_s=5.0)
    finally:
        srv.shutdown()
    assert ok is False, rows
    assert any(u"⛔ 本根" in r for r in rows), rows


def test_P3_identity_ok(tmp_path):
    u"""P3：本根之健康（build.path ＝ 本根/version.json）⇒ 过。"""
    port = _free_port()
    R = _mkroot(tmp_path, "R", port)
    srv = _serve({"status": "healthy", "version": "9.0.3",
                  "build": {"available": True, "path": str(R / "version.json")}}, port)
    try:
        ok, rows = PU.probe_health(str(R), wait_s=5.0)
    finally:
        srv.shutdown()
    assert ok is True, rows
    assert any("9.0.3" in r for r in rows), rows


def test_P4_port_unreadable_fail_loud(tmp_path):
    u"""P4：无真源 ⇒ 拒（⛔ 回落字面 5102）。"""
    R = tmp_path / "bare"
    R.mkdir()
    (R / "version.json").write_text("{}", encoding="utf-8")
    ok, rows = PU.probe_health(str(R), wait_s=1.0)
    assert ok is False, rows
    assert any(u"端口取不得" in r for r in rows), rows


def test_P5_explicit_port_wins(tmp_path):
    u"""P5：显式 port ⇒ 优先（⛔ 经真源）。"""
    port = _free_port()
    R = tmp_path / "noconfig"
    R.mkdir()
    (R / "version.json").write_text("{}", encoding="utf-8")
    srv = _serve({"status": "healthy", "version": "STUB-P5"}, port)   # 无 build ⇒ 身份 ⛔ 究
    try:
        ok, rows = PU.probe_health(str(R), port=port, wait_s=5.0)
    finally:
        srv.shutdown()
    assert ok is True, rows
    assert any("STUB-P5" in r for r in rows), rows
