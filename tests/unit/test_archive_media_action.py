# -*- coding: utf-8 -*-
"""2026-09-07: obsidian_knowledge archive_media action — 媒体归档(Agent 不需要 vault 物理路径)。"""
import io

_GH = io.open("core/lib/gateway_helpers.py", encoding="utf-8").read()
_BASE = io.open("core/plugins/draft_box/base.py", encoding="utf-8").read()


def test_archive_media_in_enum():
    assert '"archive_media"' in _GH


def test_archive_media_handler():
    """handler 有 archive_media 分支(files+platform → 插件 archive_media)"""
    assert '_act == "archive_media"' in _GH
    assert "archive_media 需要 files" in _GH
    assert "_mark_vault_write" in _GH


def test_handler_resolves_sandbox_base():
    """相对路径修复: handler 把沙箱 base resolve 成绝对路径再拼文件, 不依赖运行 cwd"""
    assert "Path(_gsb_am(user_id, session_id)).resolve()" in _GH
    assert "_sb_am / _amfp" in _GH


def test_archive_media_method():
    """draft_box 有 archive_media 方法(复制到 assets, 返回 vault 相对路径)"""
    assert "def archive_media" in _BASE
    assert '"vault_rel"' in _BASE
    assert "草稿箱" in _BASE
    assert 'sandbox_base: str = ""' in _BASE


def test_method_resolves_relative_via_sandbox_base():
    """相对路径修复: base.py 方法签名带 sandbox_base, 相对源文件拼 sandbox_base(兜底 cwd)"""
    assert 'Path(sandbox_base) if sandbox_base else Path(".")' in _BASE
    assert "Path.cwd() / src" in _BASE


def test_desc_guides_archive():
    """工具描述说明媒体归档用 archive_media 不要找路径"""
    assert "archive_media(2026-09-07)" in _GH
    assert "不要读源码找路径" in _GH or "不需要知道 vault 物理路径" in _GH
