# -*- coding: utf-8 -*-
"""2026-09-06: vault 写类 action 计入写入追踪器(防「改 vault 草稿」假完成)。
根因: 只有 write_file/edit_file/execute_command 更新 _session_write_tracker,
obsidian_knowledge 的 write_draft/write_note/update_sop/append_pitfall 不进 tracker →
「改草稿」任务只搜到文件就 ✅完成 被放行。修复后 vault 写必须计 vault_write_count。"""
import sys

sys.path.insert(0, ".")

_GH = open("core/lib/gateway_helpers.py", encoding="utf-8").read()
_GW = open("core/gateway/completion_guard.py", encoding="utf-8").read()


def test_vault_write_marker_defined():
    """_handle_obsidian_knowledge 内应定义 _mark_vault_write 并在写类 action 调用"""
    assert "_mark_vault_write" in _GH
    assert "vault_write_count" in _GH
    # 四个写类 action 成功分支都应标记
    seg = _GH[_GH.index("def _handle_obsidian_knowledge") :]
    for act in ("update_sop", "append_pitfall", "write_draft", "write_note"):
        # 每个 action 分支内应有 _mark_vault_write 调用(粗略: 分支块含该调用)
        i = seg.find('_act == "%s"' % act)
        assert i >= 0, "%s 分支存在" % act
        block = seg[i : i + 1500]
        assert "_mark_vault_write" in block, "%s 分支调用 _mark_vault_write" % act


def test_fake_done_gate_counts_vault_write():
    """假完成判定用任务局部写入扫描: 写入类工具(含 vault 写工具)计数 + _has_write 兜底"""
    i = _GW.find("_WRITE_TOOLS_FC = (")
    assert i >= 0
    block = _GW[i : i + 400]
    # 写入类工具集合含 vault 写(update_draft/write_draft/write_note/mark_published)
    assert "update_draft" in block and "write_draft" in block
    assert "_needs_fake_check" in _GW
    # 不再用裸 commit_count 硬门槛(任务局部扫描替代 session 累积 tracker)
    assert "_has_sandbox_commit" not in _GW


def test_tracker_schema_has_vault_key():
    """tracker 初始化 lambda 应含 vault_write_count 键(helper 内)"""
    assert '"vault_write_count": 0' in _GH


def test_write_note_success_marks_tracker():
    """write_note 成功返回分支在 return 前调用 _mark_vault_write"""
    seg = _GH[_GH.index('if _act == "write_note"') :]
    assert "_mark_vault_write(_wn_p, _act)" in seg[:1200]
