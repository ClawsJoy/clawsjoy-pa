# -*- coding: utf-8 -*-
"""PA 验收器官测试（2026-09-10，t7/t9）

核心契约:
  1. 内容合规: 内部批注(待核实/口径/大纲/以官方文件等)出现在对客户可见字段 → fail（硬门槛）
  2. t22 的 6 页泄漏模式必须全部被拦
  3. 原有排版检查不回归
  4. 规则从画像读(profile_forbidden_marks)
  5. 审核从脚本变器官: /v9/pa/audit/preflight 可 HTTP 调
"""
import sys

sys.path.insert(0, ".")
import pytest
from flask import Flask

from core.pa import audit as A


# ---- 内容合规: t22 六页泄漏模式逐一拦 ----
@pytest.mark.parametrize(
    "field,text",
    [
        ("body", "按实际投资额计（口径待核实 #9）"),
        ("items", "待核实 #3\n待核实 #4\n待核实 #5"),
        ("rows", "P8直投（待核实 #6）| 揭榜课题（待核实 #7）"),
        ("subtitle", "口径待核实 #2 / #8"),
        ("footer", "△ 政策口径以官方文件为准（数字待核实）"),
        ("mainText", "大纲 V0.9 · 数字待核实"),
    ],
)
def test_internal_annotation_leak_fails(field, text):
    """t22 的 6 页泄漏模式, 任意一条进可见字段都必须 fail"""
    pages = [{"layout": "content", "data": {field: text, "title": "x"}}]
    issues = A.content_compliance(pages)
    fails = [x for x in issues if x[1] == "fail"]
    assert fails, (field, text, issues)
    assert "内部批注泄漏" in fails[0][2]


def test_clean_content_passes():
    pages = [{"layout": "content", "data": {"title": "机会", "body": "五方联合兜底：政府+园区+银行+保险+高校"}}]
    assert A.content_compliance(pages) == []


def test_internal_note_field_is_not_scanned():
    """note/source 是内部字段, 本来就该带标记, 不能误伤"""
    pages = [{"layout": "content", "data": {"title": "x", "note": "口径待核实 #1"}}]
    assert A.content_compliance(pages) == []


def test_preflight_includes_compliance():
    pages = [{"layout": "content", "data": {"title": "x", "body": "（待核实 #9）"}}]
    issues = A.preflight(pages)
    assert any(x[1] == "fail" and "内部批注泄漏" in x[2] for x in issues)


def test_preflight_existing_checks_still_work():
    """原有检查不回归: 未知 layout 仍 fail"""
    pages = [{"layout": "nonsense", "data": {}}]
    issues = A.preflight(pages)
    assert any(x[1] == "fail" and "不在白名单" in x[2] for x in issues)


def test_profile_forbidden_marks():
    entries = [{"value": "禁止出现「内部机密」"}, {"value": "不得含「审计稿」"}]
    marks = A.profile_forbidden_marks(entries)
    assert "内部机密" in marks and "审计稿" in marks
    # 能从画像抽出的标记, 参与内容合规
    pages = [{"layout": "content", "data": {"title": "x", "body": "这是内部机密"}}]
    issues = A.content_compliance(pages, extra_marks=marks)
    assert any("内部机密" in x[2] for x in issues)


# ---- 路由: 审核从脚本变器官 ----
@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    app = Flask(__name__)
    from core.pa.gateway_routes import register_pa_routes

    register_pa_routes(app)
    return app.test_client()


def test_route_preflight_blocks_leak(client):
    pages = [
        {"layout": "content", "data": {"title": "机会", "body": "（口径待核实 #9）"}},
        {"layout": "content", "data": {"title": "路径", "body": "选一个场景立项"}},
    ]
    r = client.post("/v9/pa/audit/preflight", json={"pages": pages})
    d = r.get_json()
    assert r.status_code == 200
    assert d["ok"] is True and d["pass"] is False and d["fail_count"] >= 1


def test_route_preflight_requires_pages(client):
    assert client.post("/v9/pa/audit/preflight", json={}).status_code == 400


def test_route_postcheck_requires_paths(client):
    assert client.post("/v9/pa/audit/postcheck", json={}).status_code == 400
