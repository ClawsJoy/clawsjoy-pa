# -*- coding: utf-8 -*-
"""P2: browser_hybrid 接线测试 — schema/注册/SSRF/委托(实现单元, 不依赖真实浏览器)"""
import sys

sys.path.insert(0, ".")

_SRC_GH = open("core/lib/gateway_helpers.py", encoding="utf-8").read()
_SRC_TR = open("core/gateway/tool_router.py", encoding="utf-8").read()
_SRC_IMPL = open("core/tools/browser_hybrid_impl.py", encoding="utf-8").read()


def test_browser_hybrid_schema_present():
    from core.lib.gateway_helpers import _get_default_tools

    names = [t.get("function", {}).get("name") for t in _get_default_tools()]
    assert "browser_hybrid" in names, names
    schema = next(t for t in _get_default_tools() if t.get("function", {}).get("name") == "browser_hybrid")
    enum = schema["function"]["parameters"]["properties"]["action"]["enum"]
    assert {"enumerate", "click", "fill", "observe", "close", "press"} <= set(enum)
    assert schema["function"]["parameters"]["additionalProperties"] is False


def test_browser_hybrid_registered():
    """browser_hybrid 应入 tool_router 注册表 + 优先级 + gateway_helpers 处理器表"""
    assert '"browser_hybrid": 3' in _SRC_TR, "优先级应为 3(浏览器自动化)"
    assert "BrowserHybridPlugin" in _SRC_TR, "注册表应含插件类"
    assert '"browser_hybrid": BrowserHybridPlugin' in _SRC_TR
    assert "def _handle_browser_hybrid" in _SRC_GH, "handler 保留"
    assert "_TOOL_HANDLERS" not in _SRC_GH, "S4: 旧处理器表应移除(单轨 plugin)"


def test_browser_hybrid_ssrf_blocked():
    """SSRF: localhost/内网 url 应被拒绝且不启动浏览器"""
    from core.tools.browser_hybrid_impl import handle

    r = handle({"action": "enumerate", "url": "http://127.0.0.1:8080/admin", "page_id": "p_t1"})
    assert r["success"] is False and ("内网" in r["error"] or "localhost" in r["error"]), r
    r2 = handle({"action": "enumerate", "url": "file:///etc/passwd", "page_id": "p_t1"})
    assert r2["success"] is False and "http" in r2["error"], r2


def test_browser_hybrid_param_validation():
    from core.tools.browser_hybrid_impl import handle

    assert handle({"action": "bogus"})["success"] is False
    assert handle({"action": "enumerate", "page_id": "../evil path"})["success"] is False, "page_id 应被拒绝"
    # 未 enumerate 就 act → 引导性错误
    r = handle({"action": "click", "page_id": "p_none", "index": 1})
    assert r["success"] is False and "enumerate" in r["error"], r


def test_impl_uses_a11y_dom_label_policy():
    """实现应复用 P1 标签策略(稳定描述/占位内容化字段)"""
    assert "from core.tools.a11y_dom import" in _SRC_IMPL or "from core.tools import a11y_dom" in _SRC_IMPL
    assert "placeholder_content" in _SRC_IMPL
    assert "stable_label" in _SRC_IMPL
    assert "role-desc" in _SRC_IMPL
    # 坐标只存不进 LLM 清单文本
    assert '"x": bb.get("x")' in _SRC_IMPL


def test_items_text_no_coords():
    """items_text 只含 序号|role|label(坐标不进提示词)"""
    from core.tools.a11y_dom import items_text

    items = [{"role": "button", "label": "百度一下"}, {"role": "input", "label": "文本输入框"}]
    text, _ = items_text(items)
    assert "|button|百度一下" in text and "|input|文本输入框" in text
    assert "x=" not in text and "sel" not in text
