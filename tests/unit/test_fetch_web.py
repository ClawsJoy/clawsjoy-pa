"""fetch_web 插件单测: URL 校验 / SSRF 内网拦截 / 大小限制 / 超时 / 重定向 / 内容提取"""
import sys

sys.path.insert(0, ".")
import pytest

from core.tools.fetch_web import FETCH_TIMEOUT, MAX_REDIRECTS, MAX_RESPONSE_BYTES, FetchWebPlugin


def test_fetch_timeout_is_30s():
    """超时应为 30s(theverge 等慢站点 20s 不够)"""
    assert FETCH_TIMEOUT == 30


class _Raw:
    def __init__(self, body):
        self._b = body

    def read(self, n=-1):
        if n is None or n < 0:
            out, self._b = self._b, b""
            return out
        out, self._b = self._b[:n], self._b[n:]
        return out


class _FakeResp:
    def __init__(self, status_code=200, headers=None, body=b"", raise_on=None):
        self.status_code = status_code
        self.headers = headers or {"Content-Type": "text/html; charset=utf-8"}
        self._body = body
        self._raise_on = raise_on
        self.closed = False

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    @property
    def raw(self):
        if self._raise_on:
            raise self._raise_on
        return _Raw(self._body)


@pytest.fixture
def plugin():
    return FetchWebPlugin()


def _run(plugin, url, monkeypatch, resp=None, raise_exc=None, seq=None):
    """mock requests.get; seq: 多个响应依次返回(重定向链)。"""
    import requests as _r

    def _fake_get(*a, **kw):
        if seq is not None:
            return seq.pop(0)
        if raise_exc:
            raise raise_exc
        return resp

    monkeypatch.setattr(_r, "get", _fake_get)
    return plugin.execute({"url": url}, object())


# ===== URL 校验(纯逻辑, 无网络) =====


def test_missing_url(plugin):
    r = plugin.execute({}, object())
    assert not r["success"] and "url" in r["error"]


def test_url_too_long(plugin, monkeypatch):
    r = _run(plugin, "https://x.com/" + "a" * 3000, monkeypatch)
    assert not r["success"] and "maximum length" in r["error"]


def test_unsupported_scheme(plugin, monkeypatch):
    r = _run(plugin, "ftp://example.com/file", monkeypatch)
    assert not r["success"] and "scheme" in r["error"]


def test_credentials_rejected(plugin, monkeypatch):
    r = _run(plugin, "https://user:pass@example.com/", monkeypatch)
    assert not r["success"] and "credentials" in r["error"]


# ===== SSRF 内网拦截(纯逻辑) =====


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1/admin",
        "https://localhost/",
        "https://10.0.0.8/",
        "https://192.168.1.1/",
        "https://169.254.169.254/latest/meta-data/",
    ],
)
def test_private_host_blocked(plugin, url, monkeypatch):
    r = _run(plugin, url, monkeypatch)
    assert not r["success"] and "内网" in r["error"], r


# ===== 成功抓取 =====


def test_fetch_html_strips_tags(plugin, monkeypatch):
    resp = _FakeResp(body=b"<html><body><h1>Title</h1><script>alert(1)</script><p>Hello &amp; world</p></body></html>")
    r = _run(plugin, "https://example.com/", monkeypatch, resp=resp)
    assert r["success"]
    assert "Title" in r["content"] and "Hello & world" in r["content"]
    assert "alert" not in r["content"]  # script 已剔除
    assert r["status_code"] == 200


def test_fetch_text_passthrough(plugin, monkeypatch):
    resp = _FakeResp(headers={"Content-Type": "text/plain"}, body=b"plain text body")
    r = _run(plugin, "https://example.com/a.txt", monkeypatch, resp=resp)
    assert r["success"] and r["content"] == "plain text body"


def test_fetch_unsupported_content_type(plugin, monkeypatch):
    resp = _FakeResp(headers={"Content-Type": "image/png"}, body=b"\x89PNG")
    r = _run(plugin, "https://example.com/a.png", monkeypatch, resp=resp)
    assert not r["success"] and "content type" in r["error"]


# ===== 大小限制 =====


def test_response_size_limit(plugin, monkeypatch):
    resp = _FakeResp(body=b"x" * (MAX_RESPONSE_BYTES + 1000))
    r = _run(plugin, "https://example.com/big", monkeypatch, resp=resp)
    assert r["success"]
    assert r["truncated"] is True
    assert len(r["content"]) <= MAX_RESPONSE_BYTES


# ===== 超时 =====


def test_timeout(plugin, monkeypatch):
    import requests as _r

    r = _run(plugin, "https://example.com/slow", monkeypatch, raise_exc=_r.exceptions.Timeout("timed out"))
    assert not r["success"] and "timeout" in r["error"].lower()


# ===== 重定向 =====


def test_cross_origin_redirect_blocked(plugin, monkeypatch):
    seq = [
        _FakeResp(status_code=302, headers={"Location": "https://other.example.com/", "Content-Type": "text/html"}),
    ]
    r = _run(plugin, "https://example.com/start", monkeypatch, seq=seq)
    assert not r["success"] and "cross-origin" in r["error"], r


def test_redirect_to_private_blocked(plugin, monkeypatch):
    seq = [
        _FakeResp(status_code=302, headers={"Location": "http://127.0.0.1/evil", "Content-Type": "text/html"}),
    ]
    r = _run(plugin, "https://example.com/start", monkeypatch, seq=seq)
    # 跨源重定向先于 SSRF 检查被拒(安全上同样拦截)
    assert not r["success"], r
    assert "redirect" in r["error"] or "内网" in r["error"], r


def test_redirect_hop_limit(plugin, monkeypatch):
    seq = [
        _FakeResp(status_code=302, headers={"Location": "https://example.com/step%d" % i, "Content-Type": "text/html"})
        for i in range(MAX_REDIRECTS + 2)
    ]
    r = _run(plugin, "https://example.com/start", monkeypatch, seq=seq)
    assert not r["success"] and "redirects" in r["error"], r


def test_same_origin_redirect_followed(plugin, monkeypatch):
    seq = [
        _FakeResp(status_code=302, headers={"Location": "https://example.com/final", "Content-Type": "text/html"}),
        _FakeResp(body=b"<p>final page</p>"),
    ]
    r = _run(plugin, "https://example.com/start", monkeypatch, seq=seq)
    assert r["success"] and r["url"] == "https://example.com/final"
    assert "final page" in r["content"]
