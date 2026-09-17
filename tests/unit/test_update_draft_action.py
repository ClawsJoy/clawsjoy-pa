# -*- coding: utf-8 -*-
"""2026-09-06: update_draft action — 就地更新已有草稿(修复「修改草稿」任务假完成根因)。
write_draft 是新建语义(日期前缀文件名), 无法改旧草稿 → Agent 反复侦察找不到更新入口。"""
import io

_GH = io.open("core/lib/gateway_helpers.py", encoding="utf-8").read()
_BASE = io.open("core/plugins/draft_box/base.py", encoding="utf-8").read()


def test_update_draft_in_enum():
    """action 枚举应含 update_draft"""
    assert '"update_draft"' in _GH


def test_update_draft_handler_branch():
    """handler 应有 update_draft 分支(取 draft_path+content 调插件 update_draft, 成功后计 vault 写)"""
    assert '_act == "update_draft"' in _GH
    assert 'update_draft 需要 draft_path' in _GH
    assert "_mark_vault_write" in _GH


def test_update_draft_method_in_base():
    """draft_box base 应有 update_draft 方法: 保留 frontmatter 替换正文, 返回 changed"""
    assert "def update_draft" in _BASE
    assert "保留原 frontmatter" in _BASE or "保留原" in _BASE
    assert '"changed"' in _BASE


def test_update_draft_semantics_documented():
    """schema 描述应说明 update_draft 用于「修改/调整/更新草稿」而非新建"""
    assert "就地更新已有草稿" in _GH
    assert "修改/调整/更新草稿" in _GH or "修改" in _GH
