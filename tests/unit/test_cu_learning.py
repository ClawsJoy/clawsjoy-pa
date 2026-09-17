# -*- coding: utf-8 -*-
"""P4 单测: cu_learning 学习循环/SOP 生成器(纯逻辑, tmp 目录, 不碰 vault/浏览器)"""
import sys
import json
import os

sys.path.insert(0, ".")
from core.tools import cu_learning_impl as cu


def test_classify_failure():
    assert cu.classify_failure("act click 失败: Timeout 30000ms") == "超时"
    assert cu.classify_failure("安全验证 请完成下方验证") == "风控"
    assert cu.classify_failure("双检不一致(agent=1 checker=2)") == "选择错"
    assert cu.classify_failure("元素不可见且重定位失败(DOM 已变)") == "选择器失效"
    assert cu.classify_failure("Page.fill: Error: Element is not editable") == "执行错"
    assert cu.classify_failure("仍歧义请 ask 老板") == "歧义"


def test_plan_start_log_and_stop_rules(tmp_path):
    d = str(tmp_path)
    plan = cu.start_plan(d, "t1", "打开新闻", completion=[{"check": "url_contains", "target": "news"}])
    pid = plan["plan_id"]
    # 同一意图连续 3 次失败(单步重试上限2)→ 停止(同一意图规则优先)
    st = None
    for i in range(3):
        st = cu.log_step(d, "t1", pid, {"intent": "点击新闻", "ok": False, "error": "Page.click: Timeout"})
    assert st["stop"] is True and "同一意图" in st["stop_reason"], st
    assert st["by_intent_fail"].get("点击新闻") == 3, st["by_intent_fail"]
    # 三个不同意图连续失败 → 连续 3 步规则
    plan2 = cu.start_plan(d, "t2", "x")
    pid2 = plan2["plan_id"]
    st2 = None
    for intent in ("填搜索框", "点按钮", "提交"):
        st2 = cu.log_step(d, "t2", pid2, {"intent": intent, "ok": False, "error": "fill 失败: Timeout"})
    assert st2["stop"] is True and "连续 3 步失败" in st2["stop_reason"], st2
    # 交错失败累计>3(无 3 连) → 累计规则
    plan3 = cu.start_plan(d, "t2b", "y")
    pid3 = plan3["plan_id"]
    st3 = None
    seq = [("a", False), ("b", True), ("c", False), ("d", True), ("e", False), ("f", True), ("g", False), ("h", True), ("i", False), ("j", False), ("k", False)]
    for intent, ok in seq:
        st3 = cu.log_step(d, "t2b", pid3, {"intent": intent, "ok": ok, "error": "" if ok else "失败x"})
    assert st3["stop"] is True and "累计失败" in st3["stop_reason"], st3
    # 失败分类计数
    assert any(c in st2["categories"] for c in ("超时", "执行错"))


def test_completion_gate_blocks_fake(tmp_path):
    """防假完成: completion 条件无证据 → complete 拒绝"""
    d = str(tmp_path)
    plan = cu.start_plan(d, "t3", "搜索并进入结果",
                         completion=[{"check": "url_contains", "target": "wd=", "note": "URL 含查询"},
                                     {"check": "text_visible", "target": "结果", "note": "页面出现结果"}])
    pid = plan["plan_id"]
    res = cu.complete_run(d, "t3", pid, evidence={"url": "https://www.baidu.com/"})
    assert res["ok"] is False and "无证据" in res["reason"], res
    res2 = cu.complete_run(d, "t3", pid, evidence={"url": "https://www.baidu.com/s?wd=x", "head": "百度为您找到相关结果"})
    assert res2["ok"] is True and res2["success_runs"] == 1, res2


def test_sop_ready_after_two_successes(tmp_path):
    d = str(tmp_path)
    rows = [
        {"intent": "打开搜索页", "action": "goto", "ok": True, "sel": "", "role": "", "label": ""},
        {"intent": "点击「新闻」", "action": "click", "ok": True, "sel": "a:nth-of-type(1)",
         "role": "link", "label": "新闻", "verify_note": "url 进入 news"},
    ]
    for i in range(2):
        plan = cu.start_plan(d, "flow-%d" % i, "打开新闻", task_key="open-news",
                             completion=[{"check": "url_contains", "target": "news"}],
                             extra={"target_url": "https://www.baidu.com"})
        pid = plan["plan_id"]
        for r in rows:
            cu.log_step(d, "flow-%d" % i, pid, r)
        res = cu.complete_run(d, "flow-%d" % i, pid, evidence={"url": "https://news.baidu.com/"})
        assert res["ok"] is True, res
    assert cu.count_successes(d, "open-news") == 2
    md = cu.build_sop(d, "open-news")
    assert "type: cu-sop" in md and "success_runs: 2" in md
    assert "## 前置" in md and "## 步骤" in md and "## 失败已知" in md
    assert "点击「新闻」" in md and "role=link" in md and "a:nth-of-type(1)" in md
    assert "target_url: https://www.baidu.com" in md


def test_telemetry(tmp_path):
    """P5 遥测: 成功率/耗时/失败分类"""
    d = str(tmp_path)
    for i in range(2):
        plan = cu.start_plan(d, "s%d" % i, "ok任务", task_key="tk",
                             completion=[{"check": "url_contains", "target": "x"}],
                             extra={})
        cu.log_step(d, "s%d" % i, plan["plan_id"], {"intent": "a", "ok": True})
        res = cu.complete_run(d, "s%d" % i, plan["plan_id"], evidence={"url": "https://x.com/x"})
        assert res["ok"]
    bad = cu.start_plan(d, "f1", "失败任务", task_key="tk")
    cu.log_step(d, "f1", bad["plan_id"], {"intent": "b", "ok": False, "error": "安全验证滑块", "category": "风控"})
    cu.abort_plan(d, "f1", bad["plan_id"], "风控")
    st = cu.telemetry(d)
    assert st["total_runs"] == 3 and st["success_runs"] == 2 and st["fail_runs"] == 1, st
    assert 0.0 < st["success_rate"] <= 1.0
    assert st["categories"].get("风控") == 1, st["categories"]
    assert st["duration_avg_s"] >= 0


def test_run_action_dispatch(tmp_path):
    d = str(tmp_path)
    r = cu.run_action({"action": "start", "task_id": "ta", "objective": "o", "plan_dir": d})
    assert r["success"] and r["plan_id"]
    pid = r["plan_id"]
    r2 = cu.run_action({"action": "log_step", "task_id": "ta", "plan_id": pid,
                        "op": "click", "ok": True, "intent": "点", "plan_dir": d})
    assert r2["success"] and r2["stop"] is False
    # 无 completion 条件(空列表) → 允许完成(证据门禁仅当有条件时强制)
    r3 = cu.run_action({"action": "complete", "task_id": "ta", "plan_id": pid,
                        "evidence": {"url": "x"}, "plan_dir": d})
    assert r3["success"] is True, r3
    r3b = cu.run_action({"action": "count", "task_key": "ta", "plan_dir": d})
    assert r3b["success_runs"] == 1
    r4 = cu.run_action({"action": "bogus", "plan_dir": d})
    assert r4["success"] is False
