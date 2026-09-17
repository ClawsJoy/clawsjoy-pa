"""write_file 长内容写入测试: 3000+ 字符报告完整落盘(修复 2000 截断)"""
import json
import sys

sys.path.insert(0, ".")
import pytest


class _Ctx:
    """最小 ToolContext 桩(write_file 需要的字段)"""

    def __init__(self, base):
        self.base = base
        self.messages = []
        self.consecutive_reads = {}
        self.consecutive_lists = {}
        self.last_read_fingerprints = {}
        self.user_id = "u1"
        self.session_id = "s1"
        self.recap_checkpoint = lambda *a, **k: None
        self.task_name_async = "t"
        self.round = 1
        self.update_world_model = lambda *a, **k: 0
        self.sandbox_git_pre_write = lambda *a, **k: None
        self.sandbox_git_post_write = lambda *a, **k: None
        self.git_status = lambda *a, **k: {}
        self.policy = {"retry": {"js_rollback_limit": 3}}
        self.js_rollback_count = {}

    def resolve_path(self, base, p):
        from pathlib import Path

        _p = p
        if _p.startswith("clawsjoy_dev/"):
            _p = _p[len("clawsjoy_dev/") :]
        return base / _p


def test_write_md_3000_chars_full(tmp_path):
    """3000+ 字符 .md 报告 → 完整落盘(不再被 2000 截断拒绝)"""
    from core.tools.write_file import WriteFilePlugin

    base = tmp_path / "clawsjoy_dev"
    base.mkdir(parents=True)
    ctx = _Ctx(base)
    content = "# 测试报告\n\n" + ("正文段落内容" * 400)  # ~2800+ 字符
    assert len(content) > 2000

    r = WriteFilePlugin().execute({"path": "data/reports/长报告.md", "content": content}, ctx)
    assert r.get("success") is True, r
    f = base / "data" / "reports" / "长报告.md"
    assert f.exists()
    written = f.read_text(encoding="utf-8")
    assert len(written) == len(content), f"写入长度 {len(written)} != 原文 {len(content)}"
    assert "正文段落内容" in written


def test_write_md_10000_chars_full(tmp_path):
    """~10000 字符报告 → 完整落盘"""
    from core.tools.write_file import WriteFilePlugin

    base = tmp_path / "clawsjoy_dev"
    base.mkdir(parents=True)
    ctx = _Ctx(base)
    content = "# 长报告\n\n" + ("段落内容" * 2500)  # ~10000 字符
    assert len(content) > 8000

    r = WriteFilePlugin().execute({"path": "data/out/长报告.md", "content": content}, ctx)
    assert r.get("success") is True, r
    written = (base / "data" / "out" / "长报告.md").read_text(encoding="utf-8")
    assert len(written) == len(content)


def test_write_over_20000_rejected_with_segment_hint(tmp_path):
    """>20000 字符仍拒绝, 但提示分段而非 heredoc(保留安全边界)"""
    from core.tools.write_file import WriteFilePlugin

    base = tmp_path / "clawsjoy_dev"
    base.mkdir(parents=True)
    ctx = _Ctx(base)
    content = "# 超大\n\n" + ("x" * 20100)
    assert len(content) > 20000

    r = WriteFilePlugin().execute({"path": "data/big.md", "content": content}, ctx)
    assert r.get("success") is False
    assert "20000" in r.get("error", "")
    assert "分段" in r.get("error", "")
    assert "heredoc" not in r.get("error", "")


def test_write_python_any_length_allowed(tmp_path):
    """.py 文件不受长度限制(heredoc 语义保留给 Python)"""
    from core.tools.write_file import WriteFilePlugin

    base = tmp_path / "clawsjoy_dev"
    base.mkdir(parents=True)
    ctx = _Ctx(base)
    content = "# -*- coding: utf-8 -*-\n\n" + ("# comment\n" * 3000)  # >20000
    r = WriteFilePlugin().execute({"path": "script.py", "content": content}, ctx)
    assert r.get("success") is True, r
    assert (base / "script.py").exists()


def test_write_normal_short_content_still_works(tmp_path):
    """短内容不受影响"""
    from core.tools.write_file import WriteFilePlugin

    base = tmp_path / "clawsjoy_dev"
    base.mkdir(parents=True)
    ctx = _Ctx(base)
    r = WriteFilePlugin().execute({"path": "notes.txt", "content": "short"}, ctx)
    assert r.get("success") is True, r
    assert (base / "notes.txt").read_text(encoding="utf-8") == "short"


def _write(ctx, path, content):
    from core.tools.write_file import WriteFilePlugin

    return WriteFilePlugin().execute({"path": path, "content": content}, ctx)


def test_truncated_mid_url_returns_warning(tmp_path):
    """LLM 截断: 内容末尾是未完成的 URL(http 无结尾) → 写入成功但返回 warning"""
    from core.tools.write_file import _content_incomplete_hint

    base = tmp_path / "clawsjoy_dev"
    base.mkdir(parents=True)
    ctx = _Ctx(base)
    # 复现用户场景: 728 字节报告截断在第 2 条笔记 URL(http 开头无结尾)
    truncated = "# 考研复习小红书笔记\n\n" "1. 考研数学基础班: https://www.xiaohongshu.com/explore/abc123\n" "2. 英语高频词汇: http"
    hint = _content_incomplete_hint(truncated)
    assert hint, "截断内容应检测出 warning"
    r = _write(ctx, "data/reports/truncated.md", truncated)
    assert r["success"], r
    assert "warning" in r and "不完整" in r["warning"], "应返回 warning 提示 Agent 重新生成"
    # 落盘的就是截断内容(不伪造), warning 让 Agent 重写
    assert (base / "data/reports/truncated.md").read_text(encoding="utf-8") == truncated


def test_truncated_trailing_slash_url_warning(tmp_path):
    """截断在 /explore/ 后无 ID → warning"""
    from core.tools.write_file import _content_incomplete_hint

    base = tmp_path / "clawsjoy_dev"
    base.mkdir(parents=True)
    ctx = _Ctx(base)
    content = "# 报告\n\n1. 笔记: https://www.xiaohongshu.com/explore/"
    assert _content_incomplete_hint(content), "/explore/ 尾部无 ID 应检测"
    r = _write(ctx, "data/reports/r2.md", content)
    assert r["success"] and "warning" in r


def test_unclosed_fence_and_table_warning(tmp_path):
    """代码围栏未闭合 / 表格未闭合 → warning"""
    from core.tools.write_file import _content_incomplete_hint

    assert _content_incomplete_hint("# a\n```py\nprint(1)")  # ``` 奇数
    assert _content_incomplete_hint("| 平台 | 标题 |\n|---|---|\n| 小红书 | x")  # 表格行结尾


def test_complete_report_no_warning(tmp_path):
    """完整报告(>1500 字节, 正常结尾) → 无 warning"""
    base = tmp_path / "clawsjoy_dev"
    base.mkdir(parents=True)
    ctx = _Ctx(base)
    rows = "\n".join(
        "%d. **笔记%d**: https://www.xiaohongshu.com/explore/note%d —— 标题%d。%s"
        % (i, i, i, i, "这是一条关于考研复习的完整笔记标题与链接说明, 内容足够长以确保报告超过1500字节, 覆盖多行描述。" * 2)
        for i in range(1, 11)
    )
    content = "# 考研复习小红书前10条笔记\n\n%s\n\n**结论**: 以上为前10条真实笔记。\n" % rows
    assert len(content.encode("utf-8")) > 1500, "报告应 >1500 字节(实际 %d)" % len(content.encode("utf-8"))
    from core.tools.write_file import _content_incomplete_hint

    assert _content_incomplete_hint(content) == "", "完整报告不应有 warning"
    r = _write(ctx, "data/reports/full.md", content)
    assert r["success"] and "warning" not in r, r
    written = (base / "data/reports/full.md").read_text(encoding="utf-8")
    assert len(written.encode("utf-8")) > 1500, "完整落盘应 >1500 字节"


def test_short_legit_doc_no_warning(tmp_path):
    """合法短内容(带结尾标点/换行) → 不误报"""
    from core.tools.write_file import _content_incomplete_hint

    assert _content_incomplete_hint("短内容。") == ""
    assert _content_incomplete_hint("short\n") == ""
    assert _content_incomplete_hint("完成。\n") == ""
