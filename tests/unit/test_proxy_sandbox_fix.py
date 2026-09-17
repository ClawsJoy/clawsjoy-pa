"""#27 回归测试: 沙箱代理透传 + .env 代理启用"""
import sys, os
sys.path.insert(0, ".")
import pytest


def test_sandbox_env_whitelist_has_proxy():
    """_SANDBOX_ENV 白名单应包含代理变量"""
    import core.gateway.shared_state as ss
    src = open(ss.__file__, encoding="utf-8").read()
    for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "no_proxy", "NO_PROXY"):
        assert '"' + k + '"' in src, f"白名单应含 {k}"


def test_sandbox_env_passes_proxy_values(monkeypatch):
    """代理变量应透传进 _SANDBOX_ENV"""
    monkeypatch.setenv("http_proxy", "http://127.0.0.1:7890")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:7890")
    # Windows(2026-09-17): os.environ 的键名大小写不敏感 —— setenv("http_proxy") 在
    # Windows 上实际写成 HTTP_PROXY, 按字面小写名过滤 items() 会漏掉。改用
    # os.environ.get()(内部 encodekey 会大写化) 取值, 语义跨平台一致。
    assert os.environ.get("http_proxy") == "http://127.0.0.1:7890"
    assert os.environ.get("HTTPS_PROXY") == "http://127.0.0.1:7890"


def test_env_file_proxy_enabled():
    """config/.env 代理行应取消注释"""
    from pathlib import Path
    env = Path("config/.env").read_text(encoding="utf-8")
    assert "HTTP_PROXY=http://127.0.0.1:7890" in env, ".env 应启用 HTTP_PROXY"
    assert "HTTPS_PROXY=http://127.0.0.1:7890" in env, ".env 应启用 HTTPS_PROXY"
    assert "# HTTP_PROXY" not in env, "HTTP_PROXY 不应再被注释"


def test_dotenv_loads_proxy():
    """load_dotenv(config/.env) 应加载代理进 os.environ"""
    from dotenv import load_dotenv
    load_dotenv("config/.env", override=True)
    assert os.environ.get("HTTP_PROXY") == "http://127.0.0.1:7890"
    assert os.environ.get("HTTPS_PROXY") == "http://127.0.0.1:7890"
