"""R3/R4: agent_manual.md 注册进 SAG（entity_type=manual）"""
import sys, os
sys.path.insert(0, ".")
import pytest


def test_manual_file_exists():
    """说明书文件存在且含关键章节"""
    from pathlib import Path
    p = Path("config/prompts/agent_manual.md")
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    for sec in ["## 1. 工具清单", "## 2. 执行纪律", "## 3. 完成标准",
                "## 4. 禁则清单", "## 5. 输出格式规范"]:
        assert sec in text, f"缺少章节 {sec}"


def test_manual_contains_entity_type_doc():
    """说明书含 query_index entity_type 参数说明"""
    text = open("config/prompts/agent_manual.md", encoding="utf-8").read()
    assert "entity_type" in text
    assert "audit_event" in text and "goal" in text and "escalation" in text and "snapshot" in text


def test_register_manual_degrades_without_db(monkeypatch):
    """DB 不可用 → register_manual 不抛异常（mock _get_extractor 强制 None）"""
    from core.lib import sag_audit_bridge as SAB
    monkeypatch.setattr(SAB, "_get_extractor", lambda: None)
    ok = SAB.register_manual()
    assert ok is False

def test_section_extraction_regex():
    """章节提取正则正确识别手册标题"""
    import re
    text = open("config/prompts/agent_manual.md", encoding="utf-8").read()
    sections = re.findall(r"^##\s+(.+)$", text, re.MULTILINE)
    assert any("工具清单" in s for s in sections)
    assert any("禁则清单" in s for s in sections)
    assert any("完成标准" in s for s in sections)
