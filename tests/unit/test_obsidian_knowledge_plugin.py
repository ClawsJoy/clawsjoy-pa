# -*- coding: utf-8 -*-
"""S4: obsidian_knowledge 插件单轨接线(原 tool_router elif 已迁 handler)"""
import sys

sys.path.insert(0, ".")
import pytest


@pytest.fixture()
def tmp_vault(tmp_path, monkeypatch):
    """⑪(2026-09-13) hermetic vault: 自造 Pitfalls/避坑清单.md, 不依赖本机 vault 内容。

    原测试断言真实 vault 里存在 `Pitfalls/避坑清单.md` — 本机 vault 没有该文件
    (SOPs 下只有 平台发布工作流.md) → 环境依赖型失败。
    这里把 vault 根指到临时目录(core/gateway/precision_inject._vault_path 是
    _resolve_knowledge_path 的调用点, monkeypatch 模块属性即对 handler 生效)。
    """
    _pit = tmp_path / "Pitfalls"
    _pit.mkdir(parents=True, exist_ok=True)
    (_pit / "避坑清单.md").write_text(
        "# 避坑清单\n\n- 写文件必须带 reason\n- data/vault 无沙箱镜像, 读 vault 用 obsidian_knowledge\n" "- 高危命令/越权路径走审批\n",
        encoding="utf-8",
    )
    import core.gateway.precision_inject as _pi

    monkeypatch.setattr(_pi, "_vault_path", lambda: str(tmp_path))
    # 2026-09-28: 本 fixture 自造 `Pitfalls/避坑清单.md` ⇒ **配置也要钉住**。
    #   只钉 `_vault_path` 时，避坑清单的**目录**仍读本机 execution_policy.yaml 的
    #   `pitfalls_dir`（该值随 vault 布局变）⇒ 测试变成「本机配置内容依赖型」，
    #   本机把真件指回活区后当场现形。这里显式声明本 fixture 自己的布局。
    monkeypatch.setattr(
        _pi,
        "_obsidian_cfg",
        lambda: {
            "enabled": True,
            "sops_dir": "SOPs",
            "pitfalls_dir": "Pitfalls",
            "pitfalls_file": "避坑清单.md",
        },
    )
    return tmp_path


_GH = open("core/lib/gateway_helpers.py", encoding="utf-8").read()
_TR = open("core/gateway/tool_router.py", encoding="utf-8").read()


def test_obsidian_registered_via_plugin():
    from core.gateway.tool_router import _TOOL_REGISTRY

    assert "obsidian_knowledge" in _TOOL_REGISTRY
    assert "ObsidianKnowledgePlugin" in _TR and '"obsidian_knowledge": ObsidianKnowledgePlugin' in _TR
    assert "def _handle_obsidian_knowledge" in _GH, "handler 应存在于 gateway_helpers"


def test_legacy_dispatch_removed():
    """S4: _TOOL_HANDLERS / dispatch_tool 已移除; tool_router 无 obsidian elif"""
    assert "_TOOL_HANDLERS" not in _GH and "def dispatch_tool" not in _GH
    assert 'tool_name == "obsidian_knowledge"' not in _TR, "obsidian 不应再有手写 elif"


def test_obsidian_dispatch_via_router_read(tmp_vault):
    """经 _execute_sandbox_tool(插件路径)读避坑清单应成功(只读 vault)"""
    from core.gateway.tool_router import _execute_sandbox_tool

    r = _execute_sandbox_tool("obsidian_knowledge", {"action": "read", "sop_key": "避坑清单"}, "s4_u", "s4_s")
    assert r and r.get("success") is True and "避坑" in str(r.get("content") or "")[:200], str(r)[:150]


def test_obsidian_read_missing_file_reports_failure(tmp_vault):
    """⑪伴随(2026-09-13): 文件不存在 → success=False(不再伪装成"读到了空文件")

    旧行为 {`success: True, exists: False, content: ""`} = 掩盖型失败 —
    Agent 以为查过 SOP, 实际什么都没读到。
    """
    from core.gateway.tool_router import _execute_sandbox_tool

    r = _execute_sandbox_tool("obsidian_knowledge", {"action": "read", "sop_key": "SOPs/不存在的文件.md"}, "s4_u", "s4_s")
    assert r and r.get("success") is False, f"缺文件应明确失败: {str(r)[:150]}"
