# -*- coding: utf-8 -*-
"""9.0.10 首件 · 序隔离 —— 「全跑 ＝ 单跑之和」(⛔ 假红 ∧ ⛔ 假绿)。

一手归因(承 pm_1852 §四.1): 全跑 9 条「全跑红 ／ 单跑绿」= 二类**进程级共享态**残留 ——

  ⒜ `core/gateway/precision_inject.py:201` `_cfg_roots` ＝ `functools.lru_cache(maxsize=1)`
     ⇒ 首次调用者之 `_obsidian_cfg()` 结果**钉死全会话**。全跑时先有真配置调用者
     ⇒ 缓存 = 真根(`工作区/SOPs/SOPs` 向) ⇒ 之后 `test_precision_inject.py` 之
     `_iso` 猴补 `_obsidian_cfg` 对 `_sops_rel`/`_pitfalls_rel` **无效**(走缓存)
     ⇒ 解析路径落 tmp vault 之外 ⇒ 6 条 precision_inject ＋ 2 条知识面用例红。
  ⒝ `core/gateway/shared_state.py:646` `_preempt_requests`/`_preempt_starve` ＝ 进程级共享队列
     ⇒ `tests/unit/test_pm011_n11.py:261` 经 `POST /v9/preempt`(缺省 `priority=5` ／
     `requester=boss`)为 session `s1` 登记后**未清** ⇒ 后继 `test_workspace_guard_fixes.py:223`
     的 `_execute_sandbox_tool("web_search", {}, "u1", "s1")` 被「prio 5 抢占」⇒ 1 条红。

修复 ＝ `tests/conftest.py::_order_isolation`(**每用例前后**还原会话级共享态 · ⛔ 改断言)。

本件之齿(承 pm_1852 §四.1):
  正控 —— **同件连跑二遍 ⇒ 果同**(`test_Z_正控_...` parametrize 二遍 · 皆须得同一净读)。
  反控 —— **造污 ⇒ 必咬**(`test_P_造污者...` 留痕 ⇒ 后继 `test_R2_...` 之「入口应净」必红)。
          ⚠ 咬之亲验: `CJ_NO_ORDER_ISOLATION=1` 跑本件 ⇒ 隔离关 ⇒ `R2` ／ `Z` 系红。
"""
import pytest


def _queues():
    from core.gateway import shared_state as ss

    return ss._preempt_requests, ss._preempt_starve


def _real_roots():
    """真源(⛔ 不写死): 由 `_obsidian_cfg()` 现算 —— 配置变则期望随之。"""
    from core.gateway import precision_inject as pi

    _c = pi._obsidian_cfg()
    _s = str(_c.get("sops_dir") or "SOPs").strip("/")
    _p = str(_c.get("pitfalls_dir") or "Pitfalls").strip("/")
    return (_s, _p)


def test_R1_入口_共享队列应净():
    """反控(入口腿 · 本文件第 1 件): 入口须是「净」的。

    若隔离失效(前序文件之残留带进来) ⇒ 此处必红。
    """
    _reqs, _starve = _queues()
    assert _reqs == {}, "入口 preempt 队列应净: %r" % (_reqs,)
    assert _starve == {}, "入口防饿死计数应净: %r" % (_starve,)


def test_P_造污者_留痕并自证已污():
    """造污者(⛔ 不自清): 仿 `test_pm011_n11.py:261` ＋ 以真配置暖 `_cfg_roots`。"""
    from core.gateway import precision_inject as pi
    from core.gateway.shared_state import peek_preempt, request_preempt

    request_preempt("s1", priority=5, reason="序隔离反控之造污")  # 路由缺省 prio=5
    _reqs, _ = _queues()
    assert peek_preempt("s1") is not None and _reqs.get("s1"), "造污应留痕"

    pi._cfg_roots.cache_clear()
    _got = pi._cfg_roots()  # ⛔ 未猴补 ⇒ 缓存 = 真配置根
    assert _got == _real_roots(), "造污应把 `_cfg_roots` 暖成真配置根: %r" % (_got,)


def test_R2_受污者_队列净且猴补生效(monkeypatch):
    """反控(受污腿): 造污者之后一件 —— 隔离应已清其残留; 且猴补须**真生效**。

    隔离关(`CJ_NO_ORDER_ISOLATION=1`) ⇒ 二断言皆红 ⇒ **齿咬**。
    """
    _reqs, _starve = _queues()
    assert _reqs == {}, "受污者应见净队列(隔离应清造污者之残留): %r" % (_reqs,)
    assert _starve == {}, "防饿死计数应净: %r" % (_starve,)

    from core.gateway import precision_inject as pi

    monkeypatch.setattr(
        pi,
        "_obsidian_cfg",
        lambda: {"enabled": True, "sops_dir": "SOPs", "pitfalls_dir": "Pitfalls", "pitfalls_file": "避坑清单.md"},
    )
    assert pi._sops_rel("平台发布工作流.md") == "SOPs/平台发布工作流.md", "猴补应生效(缓存 ⛔ 钉死旧根)"
    assert pi._pitfalls_rel() == "Pitfalls/避坑清单.md", "避坑清单亦随猴补之目录"


@pytest.mark.parametrize("遍", [1, 2], ids=["第一遍", "第二遍"])
def test_Z_正控_同件连跑二遍果同(遍):
    """正控: 同一件连跑二遍 ⇒ 果同(皆得「与真源一致」之净读)。"""
    from core.gateway import precision_inject as pi

    _reqs, _starve = _queues()
    assert _reqs == {} and _starve == {}, "二遍皆须见净入口态"
    assert pi._cfg_roots() == _real_roots(), "二遍皆须与真源一致"


def test_Z2_正控_抢占判据二遍同():
    """正控(续): 同一「净」场景连跑二遍 ⇒ 判据同(⛔ 前遍之痕影响后遍)。"""
    from core.gateway.shared_state import drain_preempt, peek_preempt

    _out = []
    for _ in range(2):
        assert peek_preempt("s1") is None, "净队列 ⇒ ⛔ 有残留请求"
        _out.append(drain_preempt("s1", current_priority=1, current_tool="web_search"))
    assert _out == [None, None], "二遍皆应「无抢占」: %r" % (_out,)
