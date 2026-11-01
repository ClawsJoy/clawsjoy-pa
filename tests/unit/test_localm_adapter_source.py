# -*- coding: utf-8 -*-
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENTRY = ROOT / "core" / "gateway" / "v9_chat" / "entry.py"


def test_localm_adapter_uses_openai_tools():
    src = ENTRY.read_text(encoding="utf-8")
    assert "class _LocalMAdapter" in src
    assert "localm:" in src
    assert "/v1/chat/completions" in src
    assert "tools or []" in src
    assert '_route.get("provider") == "local:localm"' in src
