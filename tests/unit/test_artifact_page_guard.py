# -*- coding: utf-8 -*-
"""2026-09-08: 假完成守卫 — 编号页产物(PPT大纲 P1..Pn)缺页禁止 goal complete"""
import re
import sys

sys.path.insert(0, ".")
import pytest


def test_page_missing_detected():
    """真实产物场景: P1-P8 在、P9-P15 缺 → 缺页清单"""
    body = "# 大纲\n## P1 封面\n## P2 现状\n## P8 路径一\n"
    task = "P1 P2 P8 P9 P15 大纲"
    pages = sorted({int(x) for x in re.findall(r"(?<![A-Z])P(\d{1,2})(?!\d)", task)})
    missing = [("P%d" % pg) for pg in pages if not re.search(r"^#{1,4}[ \t]*P" + str(pg) + r"\b", body, re.M)]
    assert missing == ["P9", "P15"]


def test_complete_pages_no_missing():
    body = "# 大纲\n## P1 封面\n## P9 结尾\n"
    task = "P1 P9"
    pages = sorted({int(x) for x in re.findall(r"(?<![A-Z])P(\d{1,2})(?!\d)", task)})
    missing = [("P%d" % pg) for pg in pages if not re.search(r"^#{1,4}[ \t]*P" + str(pg) + r"\b", body, re.M)]
    assert missing == []


def test_bridge_has_artifact_guard():
    src = open("core/gateway/completion_guard.py", encoding="utf-8").read()
    assert "def _artifact_incomplete_pages" in src
    assert "禁止标记完成" in src
    assert "缺页: " in src
    main_src = open("core/gateway/turn_protocol.py", encoding="utf-8").read()  # P3-A: _write_turn_end 已归位
    assert "ARTIFACT_GUARD" in main_src
