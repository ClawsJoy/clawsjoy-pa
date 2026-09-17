"""工具 schema 按模式过滤: minimal 只给白名单工具(LLM 看不到 search_files 等), full 全给"""
import sys
sys.path.insert(0, ".")
import pytest

ALL_TOOLS = [
    {"function": {"name": n}} for n in (
        "read_file", "write_file", "list_dir", "search_files", "execute_command",
        "query_index", "fetch_web", "browse_web", "playwright_browser", "browser_local")
]


@pytest.fixture
def _modes(monkeypatch):
    import core.gateway.quota_manager as qm
    _cfg = {
        "minimal": ["read_file", "write_file", "execute_command", "list_dir", "fetch_web", "browse_web", "browser_local"],
        "full": ["read_file", "write_file", "execute_command", "list_dir", "search_files",
                 "query_index", "fetch_web", "browse_web", "playwright_browser", "browser_local"],
    }
    monkeypatch.setattr(qm, "_modes_config_cache", _cfg)
    monkeypatch.setattr(qm, "get_mode", lambda sid, hint="": "minimal")
    monkeypatch.setattr(qm, "get_mode_tools", lambda sid, hint="": _cfg["minimal"])
    yield qm


def _filter(tools, session="s1", msgs=None):
    import agent_gateway_enhanced as main
    return main._filter_tools_by_mode(tools, session, msgs or [{"role": "user", "content": "分析代码"}])


def test_minimal_filters_out_unavailable_tools(_modes):
    """minimal 模式: 保留 list_dir(只读安全, 目录探索); 仍隐藏 search_files/query_index/playwright"""
    out = _filter(ALL_TOOLS)
    names = {t["function"]["name"] for t in out}
    assert "search_files" not in names
    assert "list_dir" in names, "list_dir 只读安全, minimal 应保留"
    assert "query_index" not in names
    assert "playwright_browser" not in names
    # 白名单内工具保留
    for n in ("read_file", "write_file", "execute_command", "list_dir", "fetch_web", "browse_web"):
        assert n in names, n
    assert "browser_local" in names, "browser_local 只读调研安全, minimal 应保留"


def test_full_mode_keeps_all(_modes):
    """full 模式: 全部工具 schema"""
    import agent_gateway_enhanced as main
    import core.gateway.quota_manager as qm
    qm.get_mode = lambda sid, hint="": "full"
    qm.get_mode_tools = lambda sid, hint="": _modes._cfg["full"]
    out = main._filter_tools_by_mode(ALL_TOOLS, "s1", [{"role": "user", "content": "x"}])
    assert {t["function"]["name"] for t in out} == {t["function"]["name"] for t in ALL_TOOLS}


def test_write_file_always_kept_even_if_mode_lacks_it(_modes):
    """兜底: 模式配置缺 write_file 时仍保留(写审批依赖其 schema)"""
    import agent_gateway_enhanced as main
    import core.gateway.quota_manager as qm
    qm.get_mode_tools = lambda sid, hint="": ["read_file", "execute_command"]
    out = main._filter_tools_by_mode(ALL_TOOLS, "s1", [{"role": "user", "content": "x"}])
    names = {t["function"]["name"] for t in out}
    assert "write_file" in names, "write_file schema 必须保留(写审批)"
    assert "read_file" in names and "execute_command" in names


def test_mode_error_returns_tools_unchanged(monkeypatch):
    """get_mode 异常 → 原样返回(不误伤)"""
    import core.gateway.quota_manager as qm
    monkeypatch.setattr(qm, "get_mode", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    import agent_gateway_enhanced as main
    out = main._filter_tools_by_mode(ALL_TOOLS, "s1", [])
    assert out == ALL_TOOLS


def test_empty_mode_tools_returns_unchanged(_modes):
    """模式配置为空 → 原样返回"""
    import agent_gateway_enhanced as main
    import core.gateway.quota_manager as qm
    qm.get_mode_tools = lambda sid, hint="": []
    out = main._filter_tools_by_mode(ALL_TOOLS, "s1", [])
    assert out == ALL_TOOLS
