# -*- coding: utf-8 -*-
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "routes" / "v9_chat.py"


def test_localm_runner_is_wired():
    src = SRC.read_text(encoding="utf-8")
    assert "def _run_localm(" in src
    assert 'model_in.startswith("localm:")' in src
    assert "return _run_localm(record, _cancel_evt)" in src
    assert "cancel_evt.is_set()" in src
