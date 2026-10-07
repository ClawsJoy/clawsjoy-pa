# -*- coding: utf-8 -*-
u'''环境面之「探之辞」（pm_1854 §二 ＝ pm_1831 §候 · 本档之 TCP 探）—— 技术总监席 f202f89 · 2026-10-08。

以何形调用：
  python -X utf8 -B -m pytest tests/unit/test_env_probe_wording_1854.py -q

正控（事之实）：
  1. port_state 之三态照实：在听 ⇒ up ／ 拒连 ⇒ down ／ 逾时 ／ 他错 ⇒ unreadable；
  2. 探之辞 **三物齐**：读数 ＋ 据（件 ／ 取刻 ／ 何处来）＋ 去处（标 ／ 端）。

反控（器之牙）：
  3. ⛔ 内部缩写上屏：读数含 up ／ down ／ 端名 ／ 源档之径 ／ 「未接」／「尚无后端读数」⇒ 必咬；
  4. ⛔ 一名蔽二态：三态之读数须互异（「读不到」⛔ 书「不在跑」／⛔ 书「未接」）；
  5. 探不动（源炸）⇒ 读数 ＝ 读不到 ＋ 载因（⛔ 静默以「不在跑」充之）。
'''
import socket
import types

import pytest

from core.pa import agent_scan as A
from core.pa import env_face as E


# ---------------------------------------------------------------- 器（我控之口 · ⛔ 依真 5102）
def _listen():
    u'''开一口**真在听** ⇒ (sock, port)。'''
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    s.listen(1)
    return s, s.getsockname()[1]


def _closed_port():
    u'''开而复闭 ⇒ 该口**必拒连**。'''
    s, p = _listen()
    s.close()
    return p


class _FakeSock(object):
    def __init__(self, exc):
        self._exc = exc

    def settimeout(self, t):
        pass

    def connect(self, addr):
        raise self._exc

    def close(self):
        pass


def _patch_socket(monkeypatch, exc):
    u'''把 A 之 socket 换成只会抛 exc 之 stub ⇒ 逾时 ／ 他错可**定证**（⛔ 依真网）。'''
    shim = types.SimpleNamespace(timeout=TimeoutError,
                                 socket=lambda *a, **k: _FakeSock(exc))
    monkeypatch.setattr(A, 'socket', shim)


@pytest.fixture()
def _services(monkeypatch):
    u'''SERVICES ⇒ 我控之口（唯一件 · 在听）⇒ 探之辞可逐态证。'''
    s, p = _listen()
    monkeypatch.setattr(A, 'SERVICES',
                        [{'id': 'probe_x', 'name': u'试服务', 'kind': 'local_service',
                          'host': '127.0.0.1', 'port': p, 'level': 'L2', 'channel': 'HTTP'}])
    yield p
    s.close()


def _ports():
    items, _note, _tag = E.resources_col()
    return [i for i in items if str(i.get('id', '')).startswith('port')]


# ---------------------------------------------------------------- 正控
def test_port_state_three_ways(monkeypatch):
    u'''正控 1：三态照实 —— 在听 ⇒ up ／ 拒连 ⇒ down ／ 逾时 ／ 他错 ⇒ unreadable（⛔ 混）。'''
    s, p = _listen()
    try:
        assert A.port_state('127.0.0.1', p) == 'up'
    finally:
        s.close()
    assert A.port_state('127.0.0.1', _closed_port()) == 'down'
    _patch_socket(monkeypatch, TimeoutError(u'探针：逾时'))
    assert A.port_state('127.0.0.1', 1) == 'unreadable'
    monkeypatch.undo()
    _patch_socket(monkeypatch, OSError(u'探针：名不可解'))
    assert A.port_state('127.0.0.1', 1) == 'unreadable'


def test_probe_item_has_three_things(_services):
    u'''正控 2：三物齐 —— 读数 ＋ 据（件 ／ 取刻 ／ 何处来）＋ 去处（标 ／ 端）。'''
    ps = _ports()
    assert len(ps) == 1, ps
    it = ps[0]
    assert it['state'] == E.PROBE_READOUT['up'], it
    ju = it[u'据']
    assert ju[u'件'] == '127.0.0.1:%d' % _services, ju
    assert ju[u'取刻'] and ju[u'何处来'], ju
    q = it[u'去处']
    assert q[u'标'] and q[u'端'], q
    assert it['src'] == '127.0.0.1:%d' % _services, it


# ---------------------------------------------------------------- 反控
def test_no_internal_shorthand_on_screen(_services):
    u'''反控 3：读数 ⛔ 含 up ／ down ／ 端名 ／ 源档之径 ／ 「未接」／「尚无后端读数」。'''
    st = _ports()[0]['state']
    for bad in ('up', 'down', '127.0.0.1', 'agent_scan', u'未接', u'尚无后端读数', u'来自'):
        assert bad not in st, (bad, st)


def test_three_states_never_collapsed():
    u'''反控 4：一名 ⛔ 蔽二态 —— 三态之读数须互异 ∧ 读不到 ⛔ 书「未接」。'''
    r = E.PROBE_READOUT
    assert len({r['up'], r['down'], r['unreadable']}) == 3, r
    assert u'未接' not in r['unreadable'], r


def test_probe_unreadable_is_loud(monkeypatch, _services):
    u'''反控 5：探不动 ⇒ 读数 ＝ 读不到 ＋ 载因（⛔ 静默以「不在跑」充之）。'''
    def _boom(host, port):
        raise RuntimeError(u'探针：源炸')

    monkeypatch.setattr(A, 'port_state', _boom)
    ps = _ports()
    assert len(ps) == 1, ps
    it = ps[0]
    assert it['state'] == E.PROBE_READOUT['unreadable'], it
    assert u'探针' in (it[u'据'].get(u'因') or ''), it
