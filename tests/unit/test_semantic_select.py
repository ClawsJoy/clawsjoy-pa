# -*- coding: utf-8 -*-
"""P3: semantic_select 单测 — 提示词/选号映射/双检/vision 标注/解析(全部 mock, 不真调模型)"""
import sys
sys.path.insert(0, ".")

_ITEMS = [
    {"id": 1, "role": "button", "label": "百度一下"},
    {"id": 2, "role": "input", "label": "文本输入框"},
    {"id": 3, "role": "link", "label": "新闻"},
    {"id": 4, "role": "link", "label": "图片"},
]


def test_system_prompt_and_user_template():
    from core.tools import semantic_select as ss
    assert "只输出 1 个整数" in ss.SELECT_SYSTEM
    assert "占位文本只是示例内容" in ss.SELECT_SYSTEM
    user = ss.build_user_prompt("点击百度一下", "1|button|百度一下")
    assert "意图：点击百度一下" in user and "目标元素序号：" in user


def test_select_index_shuffle_mapping(monkeypatch):
    """打乱清单时显示序号→原始 id 映射正确"""
    from core.tools import semantic_select as ss
    from core.tools.a11y_dom import items_text
    seed = 5
    _text, order = items_text(_ITEMS, seed=seed)
    target_orig = 2  # id=2
    disp = order[target_orig]
    monkeypatch.setattr(ss, "ollama_generate", lambda *a, **k: str(disp))
    r = ss.select_index(_ITEMS, "找搜索输入框", seed=seed)
    assert r["ok"] and r["id"] == 2, r


def test_select_index_errors(monkeypatch):
    from core.tools import semantic_select as ss
    monkeypatch.setattr(ss, "ollama_generate", lambda *a, **k: "不确定")
    r = ss.select_index(_ITEMS, "点按钮")
    assert r["ok"] is False and "非整数" in r["error"]
    monkeypatch.setattr(ss, "ollama_generate", lambda *a, **k: "99")
    r2 = ss.select_index(_ITEMS, "点按钮")
    assert r2["ok"] is False and "越界" in r2["error"]


def test_double_check_agree_and_disagree(monkeypatch):
    from core.tools import semantic_select as ss
    from core.tools.a11y_dom import items_text
    seed = 7
    _text, order = items_text(_ITEMS, seed=seed)
    # 非输入类意图: checker 也选 id=2 → agree
    monkeypatch.setattr(ss, "ollama_generate", lambda *a, **k: str(order[2]))
    assert ss.double_check(_ITEMS, "打开「文本输入框」", agent_id=2, seed=seed)["agree"] is True
    # checker 选 id=1 → disagree(意图非输入类, 不触发引擎覆盖)
    monkeypatch.setattr(ss, "ollama_generate", lambda *a, **k: str(order[1]))
    dc = ss.double_check(_ITEMS, "点击百度一下", agent_id=2, seed=seed)
    assert dc["agree"] is False and dc["checker_id"] == 1


def test_input_intent_override(monkeypatch):
    """P3 实测: 输入类意图 + 模型误选非可编辑元素 + 唯一可编辑 → 引擎覆盖"""
    from core.tools import semantic_select as ss
    monkeypatch.setattr(ss, "ollama_generate", lambda *a, **k: "3")  # 模型乱选 新闻
    r = ss.select_index(_ITEMS, "在搜索框输入关键词")
    assert r["ok"] and r["id"] == 2 and r.get("fallback") == "input-intent-override", r
    # 非输入类意图不覆盖
    monkeypatch.setattr(ss, "ollama_generate", lambda *a, **k: "3")
    r2 = ss.select_index(_ITEMS, "打开「新闻」")
    assert r2["id"] == 3 and "fallback" not in r2, r2


def test_ask_vision_choice_parse(monkeypatch, tmp_path):
    from core.tools import semantic_select as ss
    assert ss.ask_vision_choice("百度一下", str(tmp_path / "no.png")) is None  # 文件不存在
    png = tmp_path / "x.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n000000000000000000000000000000000000")
    monkeypatch.setattr(ss, "ollama_generate", lambda *a, **k: "2")
    assert ss.ask_vision_choice("百度一下", str(png)) == 2
    monkeypatch.setattr(ss, "ollama_generate", lambda *a, **k: "no idea")
    assert ss.ask_vision_choice("百度一下", str(png)) is None


def test_draw_numbered_overlay(tmp_path):
    from core.tools import semantic_select as ss
    from PIL import Image
    src = tmp_path / "shot.png"
    Image.new("RGB", (200, 120), (255, 255, 255)).save(src)
    out = tmp_path / "ov.png"
    items = [{"id": 1, "x": 100, "y": 60, "w": 80, "h": 30},
             {"id": 2, "x": 20, "y": 20, "w": 60, "h": 20}]
    assert ss.draw_numbered_overlay(str(src), str(out), items) is True
    assert out.exists() and out.stat().st_size > 0


def test_impl_wires_double_check():
    src = open("core/tools/browser_hybrid_impl.py", encoding="utf-8").read()
    assert 'params.get("double_check")' in src, "act 应支持 double_check"
    assert 'params.get("fallback")' in src, "应支持 fallback=vision"
    assert "_vision_pick" in src, "应实现 vision 回退取号"
