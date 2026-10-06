# -*- coding: utf-8 -*-
u"""pm_1558 §三 裁 ⒜＋⒞ 之齿：WS 端口由网关端口**派生** ＋ 起前检占用 fail-loud。

裁二之判据（pm_1558 §三.3）：派生式须使 5102⇒5107（⛔ 变现役）∧ 5103⇒≠5107（⛔ 撞）。
"""
import socket
import sys

sys.path.insert(0, ".")
import core.lib.port_config as pc
from core.lib.v8 import browser_local as bl


def test_derived_from_gateway_port(monkeypatch):
    u"""派生：5002⇒5007（WSL 旧值）／ 5102⇒5107（＝旧固定值 · 现役不变）／ 5103⇒5108（错峰）。"""
    for gw, want in ((5002, 5007), (5102, 5107), (5103, 5108), (5104, 5109)):
        monkeypatch.setattr(pc, "gateway_port", (lambda g: (lambda: g))(gw))
        assert bl.ws_port() == want, gw


def test_two_instances_do_not_collide(monkeypatch):
    u"""二实例之派生值 ⛔ 撞（本件之的）。"""
    monkeypatch.setattr(pc, "gateway_port", lambda: 5102)
    a = bl.ws_port()
    monkeypatch.setattr(pc, "gateway_port", lambda: 5103)
    b = bl.ws_port()
    assert a == 5107 and b == 5108 and a != b


def test_offset_comes_from_policy(monkeypatch):
    monkeypatch.setattr(pc, "gateway_port", lambda: 5102)
    monkeypatch.setattr(bl, "_policy", lambda: {"browser_local": {"ws_port_offset": 9}})
    assert bl.ws_port() == 5111


def test_port_in_use_true_then_false():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    s.listen(1)
    port = s.getsockname()[1]
    try:
        assert bl._port_in_use("0.0.0.0", port) is True
    finally:
        s.close()
    assert bl._port_in_use("0.0.0.0", port) is False


def test_start_browser_ws_fail_loud_when_occupied(capsys, monkeypatch):
    u"""⒞：端口被占 ⇒ **当场显形** ∧ ⛔ 起线程（⛔ 静默失败 —— 旧病之形）。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    s.listen(1)
    port = s.getsockname()[1]
    monkeypatch.setattr(bl, "_browser_ws_thread", None)
    try:
        bl.start_browser_ws(host="127.0.0.1", port=port)
    finally:
        s.close()
    out = capsys.readouterr().out
    assert u"[BROWSER_LOCAL]" in out and u"⛔" in out and str(port) in out
    assert bl._browser_ws_thread is None