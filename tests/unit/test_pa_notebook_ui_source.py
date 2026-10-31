# -*- coding: utf-8 -*-
"""P1 笔记本前端静态断言：三栏布局／加来源／限定问答／Studio／无 prompt。"""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "web" / "pa.html"
BRAIN = ROOT / "web" / "pa" / "faces" / "brain.js"
CSS = ROOT / "web" / "pa" / "notebook.css"


def _read(p):
    return p.read_text(encoding="utf-8")


def test_page_wires_notebook_assets():
    page = _read(PAGE)
    assert 'href="pa/notebook.css' in page
    assert 'src="pa/faces/brain.js' in page
    assert page.find('brain.js') < page.find('boot.js')


def test_notebook_three_columns_and_actions():
    src = _read(BRAIN)
    for cls in ('pa-nb-left', 'pa-nb-main', 'pa-nb-right'):
        assert cls in src, cls
    for fn in ('paNbCreateSave', 'paNbAddTextSave', 'paNbAddUrlSave', 'paNbAddPdf',
               'paNbAsk', 'paNbStudioGen', 'paNbSaveStudio', 'paNbDeleteNotebook',
               'paNbToggleSel', 'paNbSelAll', 'paNbNewNoteOpen'):
        assert 'window.' + fn + ' =' in src, fn
    assert "note_ids" in src
    assert "pa-nb-tile" in src
    assert "/outputs" in src
    for fn in ("paNbSourceDialog", "paNbSrcTab", "paNbStudioConfig", "paNbCfgFmt", "paNbEditSource",
               "paNbOrganizeOpen", "paNbOrganizeRun", "paNbOrgApply", "paNbClassifyOne"):
        assert fn in src, fn
    assert "summary" in src and "keywords" in src
    assert "pa-nb-drop" in src
    assert "window.prompt" not in src
    for ep in ('/v9/pa/notebooks', '/sources/text', '/sources/url', '/sources/pdf', '/ask', '/studio'):
        assert ep in src, ep


def test_notebook_scoped_ask_and_citations():
    src = _read(BRAIN)
    assert "paNbCiteChips" in src
    assert "[note:" in src
    assert "NB.chat" in src
    assert "答案只引用勾选来源" in src


def test_studio_kinds_and_honest_fallback():
    src = _read(BRAIN)
    for k in ('summary', 'faq', 'study', 'mindmap'):
        assert k in src, k
    assert "模型暂不可用" in src
    assert "不是模型生成" in src


def test_window_route_uses_notebook_mount():
    win = _read(ROOT / "web" / "pa" / "faces" / "window.js")
    assert "window.paBrainHtml" in win
    assert "window.paBrainMount" in win


def test_notebook_css_hides_right_rail_on_brain():
    css = _read(CSS)
    assert 'body[data-pa-route="brain"] .pa-now' in css
    assert '.pa-nb [hidden]' in css


@pytest.mark.skipif(shutil.which("node") is None, reason="node 不在")
def test_node_check_brain():
    p = subprocess.run(["node", "--check", str(BRAIN)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=30)
    assert p.returncode == 0, (p.stdout, p.stderr)
