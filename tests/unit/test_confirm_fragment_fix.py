"""write_file 确认后写入失败(1行截断)修复测试: content 持久化/恢复 + 片段引导"""
import sys

sys.path.insert(0, ".")
import pytest


def test_persist_pending_includes_content():
    """持久化 pending 含完整 content(≤100KB), 跨轮恢复不丢"""
    _SRC = open("core/gateway/write_gate.py", encoding="utf-8").read()
    # R3(2026-08-30): 持久化字段集含 content(单件与批量 items 均保留完整内容 ≤100KB)
    assert '"content"' in _SRC and "100 * 1024" in _SRC, "持久化应含 content 且限长100KB"
    assert '"id", "tool", "path", "content_preview", "ts", "reason", "command", "batch"' in _SRC, "R3 字段集含 reason/batch"


def test_restore_pending_brings_content():
    """恢复 pending 带回 content(确认用完整内容)"""
    _SRC = open("core/gateway/write_gate.py", encoding="utf-8").read()  # P3-A: _v9_restore_pending_writes 已归位
    assert '"content": _pw_saved.get("content", "")' in _SRC, "恢复应带回 content"


def test_write_file_approved_bypasses_similarity(tmp_path, monkeypatch):
    """对齐 harness: 文件已批准(is_file_approved) → 相似度低也放行(确认即执行, 不二次拒绝)"""
    import core.tools.write_file as wf_mod
    from core.gateway.shared_state import clear_approved_files, mark_file_approved
    from core.tools.write_file import WriteFilePlugin

    NL = chr(10)
    target = tmp_path / "zhihu_article_fanqie.md"
    target.write_text("旧内容第一行" + NL + "旧内容第二行" + NL + "旧内容第三行", encoding="utf-8")

    # 未批准 → 相似度低拒绝
    class Ctx:
        base = tmp_path

        def resolve_path(self, base, p):
            return base / p

        messages = []
        user_id = "u1"
        session_id = "s_appr"
        consecutive_reads = {}
        consecutive_lists = {}
        last_read_fingerprints = {}
        recap_checkpoint = None
        task_name_async = ""
        round = 1
        update_world_model = lambda *a, **k: None
        sandbox_git_pre_write = lambda *a, **k: None
        sandbox_git_post_write = lambda *a, **k: None
        git_status = lambda *a, **k: None
        policy = {}
        js_rollback_count = {}

    r = WriteFilePlugin().execute({"path": "zhihu_article_fanqie.md", "content": "全新文章" + NL * 30}, Ctx())
    assert r.get("success") is False, "未批准时相似度低应拒绝: " + str(r)
    # 批准后 → 放行
    clear_approved_files("s_appr")
    mark_file_approved("s_appr", str(target))
    r2 = WriteFilePlugin().execute({"path": "zhihu_article_fanqie.md", "content": "全新文章" + NL * 30}, Ctx())
    assert r2.get("success") is True, "已批准应跳过相似度拒绝: " + str(r2)
    clear_approved_files("s_appr")


def test_write_file_fragment_hint():
    """write_file 相似度拒绝时提示用 line 模式(不重复提交片段)"""
    _SRC = open("core/tools/write_file.py", encoding="utf-8").read()
    assert "hint" in _SRC.split("如果确认需要覆盖请分步写入")[1] or "line 参数精确修改" in _SRC, "应有 line 模式提示"
