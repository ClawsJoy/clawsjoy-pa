# -*- coding: utf-8 -*-
"""vault 落盘清洗回归（2026-09-13 事故）。

事故：`write_note(append=True)` 一段以 `---`（markdown 分隔线）开头的正文，
被 `_clean_vault_text` 的 frontmatter 剥离整段切掉 —— 中间内容静默丢失，
工具仍返回 success + verified(bytes/lines)，调用方无法发现。
实测：讲义 V7 因此掉了整节 P11–P13，而交付说明和待拍板项都在引用它。
"""
import sys

sys.path.insert(0, ".")
from core.gateway.precision_inject import _clean_vault_text, _looks_like_frontmatter


def test_leading_hr_with_later_hr_keeps_content():
    """事故形态：以 --- 开头、后面又有一个 --- → 一个字都不能少。"""
    text = "---\n\n## 第三段\n\nP11 安全：权限分三档\n\nP12 七条上限\n\n" "---\n\n## 结尾\n\nP14 三件事"
    out = _clean_vault_text(text, title="")
    assert "P11" in out and "P12" in out and "P14" in out
    assert len(out) == len(text)


def test_real_frontmatter_is_still_stripped():
    """真 frontmatter 仍必须剥离（工具会自动生成，留着会双 frontmatter）。"""
    text = "---\ntype: note\ncreated: 2026-09-13\ntags:\n  - pa\n---\n\n# 标题\n\n正文"
    out = _clean_vault_text(text, title="")
    assert out.startswith("# 标题")
    assert "type: note" not in out


def test_prose_with_colon_is_not_frontmatter():
    """正文里带半角冒号也不能被误判成 frontmatter。"""
    text = "---\n\n第 1 点:\n内容甲\n\n---\n\n尾巴"
    out = _clean_vault_text(text, title="")
    assert "内容甲" in out


def test_unclosed_or_far_closing_hr_is_not_frontmatter():
    """块过长（>30 行才闭合）或根本没有闭合 --- → 不按 frontmatter 处理。"""
    long_block = "---\n" + "\n".join("line %d" % i for i in range(40)) + "\n---\n尾部"
    out = _clean_vault_text(long_block, title="")
    assert "line 0" in out and "尾部" in out
    assert "line 5" in _clean_vault_text("---\n" + "\n".join("line %d" % i for i in range(40)), title="")


def test_looks_like_frontmatter_directly():
    assert _looks_like_frontmatter(["type: note", "created: 2026-09-13"]) is True
    assert _looks_like_frontmatter(["tags:", "  - pa", "  - v9"]) is True
    assert _looks_like_frontmatter([]) is False
    assert _looks_like_frontmatter(["P11 安全：权限分三档"]) is False
    assert _looks_like_frontmatter(["## 第三段", "正文一句"]) is False


def test_title_heading_still_deduped():
    out = _clean_vault_text("# 我的笔记\n\n正文", title="我的笔记")
    assert out == "正文"
