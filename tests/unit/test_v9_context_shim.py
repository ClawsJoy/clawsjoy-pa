"""P0: V9Context shim 验证 — 单例收编后业务 import 零改动"""
import os
import sys

sys.path.insert(0, ".")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

import pytest

from core.os.context import V9Context, get_v9_context


@pytest.fixture(autouse=True)
def _preserve_extractor():
    """保留全局单例(不重置 — 模块已加载注册), 仅对 extractor override 做恢复。"""
    ctx = get_v9_context()
    orig_ext = ctx.get_opt("extractor")
    yield
    if orig_ext is not None:
        ctx.provide_override("extractor", orig_ext)
    else:
        ctx._services.pop("extractor", None)


def test_extractor_proxy_forwards():
    """extractor proxy 转发到容器内实例(provide 后 proxy 转发属性, 不触发真实 DB 构造)"""
    from core.lib.code_entity_extractor import extractor

    ctx = get_v9_context()

    class _Fake:
        db_url = "fake://x"
        fake_marker = True

    ctx.provide_override("extractor", _Fake())
    assert ctx.has("extractor")
    assert extractor.db_url == "fake://x"
    assert extractor.fake_marker is True


def test_extractor_override_via_container():
    """测试可通过容器 override 替换 extractor(无需 monkeypatch sys.modules)"""
    from core.lib.code_entity_extractor import extractor

    ctx = get_v9_context()

    class _Fake:
        pass

    f1 = _Fake()
    f1.db_url = "v1"
    f2 = _Fake()
    f2.db_url = "v2"
    ctx.provide_override("extractor", f1)
    assert extractor.db_url == "v1"
    ctx.provide_override("extractor", f2)
    assert extractor.db_url == "v2"


def test_ledger_registered():
    """ledger 单例已注册进容器且同一实例"""
    from core.lib.v8.ledger import ledger

    ctx = get_v9_context()
    assert ctx.has("ledger")
    assert ctx.get("ledger") is ledger


def test_roster_engine_registered():
    """roster_engine 已注册且同一实例"""
    from core.lib.v8.roster_engine import roster_engine

    ctx = get_v9_context()
    assert ctx.get("roster_engine") is roster_engine


def test_tool_executor_registered():
    """tool_executor 已注册且同一实例"""
    from core.lib.tool_executor import tool_executor

    ctx = get_v9_context()
    assert ctx.get("tool_executor") is tool_executor


def test_audit_module_registered():
    """audit 模块对象已注册(可 ctx.get('audit') 调用函数)"""
    from core.gateway import audit

    ctx = get_v9_context()
    m = ctx.get("audit")
    assert m is audit
    assert hasattr(m, "audit_tool_call") and hasattr(m, "cross_check_completion")


def test_shared_state_registered():
    """shared_state 收编 27 项且引用一致"""
    import core.gateway.shared_state as ss

    ctx = get_v9_context()
    d = ctx.get("shared_state")
    assert len(d) == 26  # P2c: messages 单例已删(由 session_log 替代)
    assert "messages" not in d
    assert d["_session_failed"] is ss._session_failed
    assert d["_consecutive_reads"] is ss._consecutive_reads


def _non_class_msg(bad):
    """辅助: 非类键名单 → 报错文案(空则返回 '')"""
    return ("注册表存在非类值: " + ", ".join(bad)) if bad else ""


def test_tool_registry_registered():
    """⑫(2026-09-13) 注册表与模块级一致 + 含必需工具集(**超集断言**)

    旧断言用全等集合 → 每次有意新增工具(wps_office/lingxi/pa_audit/file_center)都判红,
    变成"新增工具必须先改测试"的假耦合。改为: 必需集 ⊆ 注册表 + 值类型自证。
    """
    from core.gateway.tool_router import _TOOL_REGISTRY

    ctx = get_v9_context()
    reg = ctx.get("tool_registry")
    assert reg is _TOOL_REGISTRY
    _required = {
        "read_file",
        "write_file",
        "list_dir",
        "search_files",
        "execute_command",
        "query_index",
        "fetch_web",
        "browse_web",
        "playwright_browser",
        "browser_local",
        "browser_hybrid",
        "cu_learning",
        "obsidian_knowledge",
        "web_search",
        "table_extract",
    }
    _missing = _required - set(reg.keys())
    assert not _missing, f"注册表缺必需工具: {sorted(_missing)}"
    # 防"幽灵注册"(键存在但无插件类): 值必须是类
    _not_class = [k for k, v in reg.items() if not isinstance(v, type)]
    assert not _non_class_msg(_not_class), _non_class_msg(_not_class)
