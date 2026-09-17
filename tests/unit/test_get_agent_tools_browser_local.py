"""_get_agent_tools() 应包含 browser_local schema 回归测试

根因: _TOOL_REGISTRY 有 browser_local(10 个), 但 _get_agent_tools()/_get_default_tools()
硬编码 11 个 schema 缺 browser_local → Agent 看不到该工具 → 退回沙箱 curl。
修复: _get_default_tools() 追加 _get_browser_local_schema()(从工具插件导入, 单一来源)。
"""
import sys

sys.path.insert(0, ".")
import pytest


def test_get_agent_tools_has_browser_local():
    """_get_agent_tools() 应包含 browser_local"""
    from core.lib.gateway_helpers import _get_agent_tools

    tools = _get_agent_tools()
    names = {t.get("function", {}).get("name", "") for t in tools if t}
    assert "browser_local" in names, "Agent 工具集应含 browser_local"


def test_browser_local_schema_actions():
    """browser_local schema 应含 publish/monitor 等 action(非仅 P1 只读)"""
    from core.lib.gateway_helpers import _get_agent_tools

    tools = _get_agent_tools()
    bl = next((t for t in tools if t and t.get("function", {}).get("name") == "browser_local"), None)
    assert bl is not None, "缺 browser_local schema"
    action_enum = str(bl["function"]["parameters"]["properties"]["action"])
    for a in (
        "navigate",
        "extract",
        "screenshot",
        "scroll",
        "click",
        "fill",
        "search",
        "upload",
        "publish",
        "monitor_start",
    ):
        assert a in action_enum, "schema 缺 action: " + a


def test_default_tools_no_none():
    """_get_default_tools() 无 None(导入失败防御)"""
    from core.lib.gateway_helpers import _get_default_tools

    tools = _get_default_tools()
    assert all(t is not None for t in tools), "不应有 None"
    assert "browser_local" in {t["function"]["name"] for t in tools if t}


def test_single_source_schema():
    """browser_local schema 单一来源: 与工具插件 BROWSER_LOCAL_SCHEMA 一致"""
    from core.lib.gateway_helpers import _get_agent_tools
    from core.tools.browser_local import BROWSER_LOCAL_SCHEMA

    tools = _get_agent_tools()
    bl = next((t for t in tools if t and t.get("function", {}).get("name") == "browser_local"), None)
    assert bl == BROWSER_LOCAL_SCHEMA, "应复用插件 schema(防漂移)"
