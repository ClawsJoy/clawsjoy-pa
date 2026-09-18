# -*- coding: utf-8 -*-
"""X-21（2026-09-18 拍）：本机服务探测**不得走代理**。

背景（受控证据）：`config/.env` 注入 `HTTP_PROXY=http://127.0.0.1:7890`（为沙箱 yt-dlp
下载**有意保留**），而 `core/lib/llm_client.py` 的两处探测原先用**裸 `requests.get`**
（`trust_env` 默认 True）⇒ 连 `http://127.0.0.1:11434` 也被送去代理 ⇒ 代理未监听时
探测恒失败（pytest 输出里的 `ProxyError` 直证；同一类里 `:107` 却已设
`self._session.trust_env = False` ⇒ 类内自相矛盾）。

本文件的第 1 条判据是**关系**而非字面量：同一环境下 `_PROBE_SESSION` 必须通、
裸 `requests.get` 必须不通 —— 后者是**反例**，用来证明这套环境**能**咬住
「忘了绕代理」的写法（否则断言会空转，见 `L-18`）。
"""
import logging
import pathlib
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import requests

import core.lib.llm_client as llm_mod
from core.lib.llm_client import _PROBE_SESSION

_REPO = pathlib.Path(__file__).resolve().parents[2]


def _closed_port() -> int:
    """取一个**确定没人监听**的本机端口（绑了就关）。"""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _assert_port_closed(port: int) -> None:
    """前置自证：那个端口**确实**连不上（否则后面的「裸 get 必失败」会空转）。"""
    with pytest.raises(OSError):
        socket.create_connection(("127.0.0.1", port), timeout=1)


class _Resp:
    status_code = 200


class _Recorder:
    """记录被调用的 URL；命中即等于「走了这条通道」的**行为级**证据。"""

    def __init__(self, mode: str = "ok"):
        self.mode = mode
        self.urls = []

    def get(self, url, **kw):
        self.urls.append(url)
        if self.mode == "boom":
            raise RuntimeError("dead proxy")
        return _Resp()


class _TagsHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        body = b'{"models":[]}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture()
def fake_ollama():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _TagsHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield "http://127.0.0.1:%d" % srv.server_address[1]
    srv.shutdown()
    srv.server_close()


@pytest.fixture()
def dead_proxy_env(monkeypatch):
    """把环境代理指向一个**确定没人监听**的端口（并清掉 NO_PROXY）。"""
    port = _closed_port()
    _assert_port_closed(port)
    holder = "http://127.0.0.1:%d" % port
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        monkeypatch.setenv(key, holder)
    for key in ("NO_PROXY", "no_proxy"):
        monkeypatch.delenv(key, raising=False)
    return holder


def test_探测会话绕过_env_代理_而裸_get_会被串味(fake_ollama, dead_proxy_env):
    """① 关系判据：同一环境下「探测会话通」而「裸 get 不通」。"""
    url = fake_ollama + "/api/tags"
    assert _PROBE_SESSION.trust_env is False, "探测会话必须 trust_env=False"
    assert _PROBE_SESSION.get(url, timeout=5).status_code == 200
    # ② 反例（证明这套环境有牙）：裸 requests.get 会被 env 代理串味
    with pytest.raises(requests.exceptions.RequestException) as excinfo:
        requests.get(url, timeout=5)
    assert isinstance(
        excinfo.value,
        (requests.exceptions.ProxyError, requests.exceptions.ConnectionError),
    ), excinfo.value


def test_ensure_ollama_走探测会话而非裸_get(monkeypatch):
    """行为级接线证明：`_ensure_ollama` 必须命中 `_PROBE_SESSION`、且**不**命中裸 get。"""
    probe, bare = _Recorder(), _Recorder()
    monkeypatch.setattr(llm_mod, "_PROBE_SESSION", probe)
    monkeypatch.setattr(llm_mod.requests, "get", bare.get)
    llm_mod.LLMClient()._ensure_ollama()
    assert probe.urls == ["http://127.0.0.1:11434/api/tags"]
    assert bare.urls == [], "探测又走了裸 requests.get（会被 env 代理串味）"


def test_ollama_available_走探测会话_成功即_True(monkeypatch):
    """行为级：探测走 `_PROBE_SESSION`，200 ⇒ True。"""
    client = llm_mod.LLMClient()
    monkeypatch.setattr(client, "_ollama_checked", False)
    probe = _Recorder()
    monkeypatch.setattr(llm_mod, "_PROBE_SESSION", probe)
    assert client._ollama_available(timeout=0.5) is True
    assert probe.urls == [client.config.base_url + "/api/tags"]


def test_ollama_available_失败必须留_WARN(monkeypatch, caplog):
    """拍定 ②：失败路径必须**可观测**（此前是静默 `False`）。

    X-22 修后直证：这里用**实例调用**——改名前 `self._ollama_available` 是 `_init`
    的布尔实例属性，实例调用恒抛 `TypeError: 'bool' object is not callable`；
    改名后（属性 → `_ollama_probe_ok`）实例调用可达。
    """
    client = llm_mod.LLMClient()
    monkeypatch.setattr(client, "_ollama_checked", False)
    monkeypatch.setattr(llm_mod, "_PROBE_SESSION", _Recorder(mode="boom"))
    with caplog.at_level(logging.WARNING):
        assert client._ollama_available(timeout=0.5) is False
    assert any("探测异常" in rec.getMessage() for rec in caplog.records), caplog.text


def test_生产代码探测不得再用裸_requests_get():
    """静态防回潮（带**反空转下限**）：两处探测都走 `_PROBE_SESSION`，无裸调用。"""
    src = (_REPO / "core" / "lib" / "llm_client.py").read_text(encoding="utf-8")
    assert len(src) > 20000, "读取的源码过短 ⇒ 判据可能空转"
    assert "requests.get(" not in src, "仍在用裸 requests.get（会被 env 代理串味）"
    assert "_req.get(" not in src, "仍在用裸 _req.get（会被 env 代理串味）"
    assert src.count("_PROBE_SESSION.get(") == 2, "两处探测都应走 _PROBE_SESSION"


def test_X22_ollama_available_实例调用必须可达():
    """X-22 行为判据：方法名**不得**被同实例属性遮蔽（改名前此条必红）。

    改名前实况：`type(client._ollama_available) == bool`、直接调用抛
    `TypeError: 'bool' object is not callable` ⇒ `:256` 的
    `if self._ollama_available():` 恒抛，被外层 `except Exception`
    误归因为「云端 API 不可用」。取数件 `data/tmp/b5_work/x21/shadow_probe.txt`。
    """
    client = llm_mod.LLMClient()
    assert "_ollama_available" not in vars(client), "实例属性又盖住了同名方法（X-22 回潮）"
    assert callable(client._ollama_available), "实例上取不到可调用的探测方法"


def test_X22_缓存分支读的是新属性名(monkeypatch):
    """关系判据：`_ollama_checked=True` 时必须**读新属性**且**不再探测**。

    若把 `return self._ollama_probe_ok` 改回旧名，取到的是绑定方法（truthy）⇒
    `is True` 失败 ⇒ 红。
    """
    client = llm_mod.LLMClient()
    monkeypatch.setattr(client, "_ollama_checked", True)
    monkeypatch.setattr(client, "_ollama_probe_ok", True)
    probe = _Recorder(mode="boom")
    monkeypatch.setattr(llm_mod, "_PROBE_SESSION", probe)
    assert client._ollama_available(timeout=0.5) is True
    assert probe.urls == [], "命中缓存时不应再探测"
