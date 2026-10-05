# -*- coding: utf-8 -*-
"""门：双模态件 `test_baidu_hybrid_e2e` 的**环境分类**（2026-09-20 · DS 831 裁①）。

口径：**环境不就绪 ⇒ skip（不是 fail）** —— 不就绪判据 ＝ 网络不可达 ／ 浏览器抛异常 ／
enumerate 返回 `success=False`；**环境就绪 ⇒ 真断言必跑**（不许「永远 skip」）。

该红格 ＋ 对照的对照：G3（enumerate 返回 `success=False`）在**旧口径**下必红（直接落 assert）、
在新口径下必 skip ⇒ 影子失配 > 0；G5 证明「就绪时真断言仍会红」（判据有齿，防「永远 skip」）。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "unit"))

import pytest  # noqa: E402
import test_browser_hybrid_integration as T  # noqa: E402
from core.tools import browser_hybrid_impl as B  # noqa: E402

QUERY = "ClawsJoy混合方案POC验证"
OK_ENUM = {
    "success": True,
    "count": 25,
    "items": [
        {"role": "button", "label": "百度一下", "id": 7},
        {"role": "input", "label": "搜索框", "id": 3},
    ],
}


def _fake_handle(enum_res):
    def h(payload):
        a = payload.get("action")
        if a == "enumerate":
            return enum_res
        if a == "fill":
            return {"success": True, "evidence": {"field_value": payload.get("value")}}
        if a == "click":
            return {"success": True, "evidence": {"url": "https://www.baidu.com/s?wd=" + QUERY, "head": ""}}
        return {"success": True}

    return h


def _old_body(handle):
    """**修前**的等价复现（只到第一条断言）：环境不就绪时旧口径会红。"""
    r = handle({"action": "enumerate", "url": "https://www.baidu.com", "page_id": "p_e2e"})
    assert r.get("success") and r.get("count", 0) >= 20, r.get("error") or r.get("count")
    return True


def _arm(monkeypatch, net_ok, handle):
    monkeypatch.setattr(T, "_net_ok", lambda: net_ok)
    monkeypatch.setattr(B, "handle", handle)


def test_net_down_skips(monkeypatch):
    _arm(monkeypatch, False, _fake_handle(OK_ENUM))
    with pytest.raises(pytest.skip.Exception):
        T.test_baidu_hybrid_e2e()


def test_browser_exception_skips(monkeypatch):
    def boom(payload):
        raise RuntimeError("no browser")

    _arm(monkeypatch, True, boom)
    with pytest.raises(pytest.skip.Exception):
        T.test_baidu_hybrid_e2e()


def test_enumerate_not_success_skips(monkeypatch):
    """该红格：enumerate 返回 success=False ⇒ 新口径 **skip**；旧口径同一夹具 **必红**。"""
    bad = {"success": False, "error": "browser degraded", "count": 0, "items": []}
    _arm(monkeypatch, True, _fake_handle(bad))
    with pytest.raises(pytest.skip.Exception):
        T.test_baidu_hybrid_e2e()
    with pytest.raises(AssertionError):          # 对照的对照
        _old_body(_fake_handle(bad))


def test_env_ready_runs_real_assertions(monkeypatch):
    """正控：环境就绪 ⇒ **真断言全跑完**（不 skip、不报错）。"""
    _arm(monkeypatch, True, _fake_handle(OK_ENUM))
    T.test_baidu_hybrid_e2e()                    # 不抛即通过


def test_env_ready_bad_count_still_red(monkeypatch):
    """有齿：环境就绪但**枚举数不足** ⇒ 仍必须红（防「永远 skip」）。"""
    _arm(monkeypatch, True, _fake_handle({"success": True, "count": 5, "items": []}))
    with pytest.raises(AssertionError):
        T.test_baidu_hybrid_e2e()
