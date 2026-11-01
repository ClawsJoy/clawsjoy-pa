# -*- coding: utf-8 -*-
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WIN = ROOT / "web" / "pa" / "faces" / "window.js"
FACES = ROOT / "web" / "pa" / "faces.json"
PAGE = ROOT / "web" / "pa.html"


def test_new_window_is_default_with_legacy_flag():
    src = WIN.read_text(encoding="utf-8")
    assert "ui === 'legacy'" in src
    assert "qq === '0'" in src
    assert "return true;   /* 产品默认：新窗唯一默认 */" in src
    assert "paWinV2Migrated" in src


def test_faces_register_new_surfaces():
    d = json.loads(FACES.read_text(encoding="utf-8"))
    ids = {f.get("id") for f in d.get("faces", [])}
    for x in ("window", "summon", "live", "brain"):
        assert x in ids
    assert d.get("updated") == "2026-11-01"


def test_pa_html_keeps_legacy_dom_and_new_hook():
    src = PAGE.read_text(encoding="utf-8")
    assert 'id="paWin"' in src
    assert 'class="main"' in src
    assert 'id="paWin" hidden' in src

def test_cards_use_runs_approval_not_chat():
    cards = (ROOT / "web" / "pa" / "faces" / "cards.js").read_text(encoding="utf-8")
    assert "/v9/agent/runs/approval" in cards
    assert "/v9/agent/chat" not in cards


def test_routes_expose_runs_approval():
    src = (ROOT / "routes" / "v9_chat.py").read_text(encoding="utf-8")
    assert '"/v9/agent/runs/approval"' in src
    assert "def v9_agent_runs_approval()" in src

def test_new_window_reads_agent_runs_and_cancels():
    live = (ROOT / "web" / "pa" / "faces" / "live.js").read_text(encoding="utf-8")
    win = (ROOT / "web" / "pa" / "faces" / "window.js").read_text(encoding="utf-8")
    assert "agent_runs:'/v9/agent/runs'" in live
    assert "LIVE.agent_runs" in live
    assert "paCancelRun(_rid)" in win

def test_new_window_has_first_win_notes_card():
    win = (ROOT / "web" / "pa" / "faces" / "window.js").read_text(encoding="utf-8")
    assert "从笔记开始" in win
    assert "paWinFirstWin" in win
    assert "/v9/pa/notes/ask" in win
    assert "出处" in win

def test_first_win_has_timeout():
    win = (ROOT / "web" / "pa" / "faces" / "window.js").read_text(encoding="utf-8")
    assert "AbortController" in win
    assert "20000" in win
    assert "20 秒内没有回执" in win
