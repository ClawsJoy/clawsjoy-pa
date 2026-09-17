# -*- coding: utf-8 -*-
"""P4 接线测试: cu_learning schema/注册/委托(纯源码+轻行为)"""
import sys

sys.path.insert(0, ".")

_SRC_GH = open("core/lib/gateway_helpers.py", encoding="utf-8").read()
_SRC_TR = open("core/gateway/tool_router.py", encoding="utf-8").read()


def test_cu_learning_schema_present():
    from core.lib.gateway_helpers import _get_default_tools

    names = [t.get("function", {}).get("name") for t in _get_default_tools()]
    assert "cu_learning" in names
    schema = next(t for t in _get_default_tools() if t.get("function", {}).get("name") == "cu_learning")
    enum = schema["function"]["parameters"]["properties"]["action"]["enum"]
    assert {"start", "log_step", "complete", "count", "sop", "abort"} <= set(enum)
    assert "completion" in schema["function"]["parameters"]["properties"]


def test_cu_learning_registered():
    assert '"cu_learning": 2' in _SRC_TR, "优先级应为 2(写类编排)"
    assert "CuLearningPlugin" in _SRC_TR and '"cu_learning": CuLearningPlugin' in _SRC_TR
    assert "def _handle_cu_learning" in _SRC_GH
    assert "_TOOL_HANDLERS" not in _SRC_GH, "S4: 旧处理器表应移除(单轨 plugin)"


def test_cu_learning_handler_dispatch(tmp_path):
    """委托可用: start→step→count(纯本地目录)"""
    from core.lib.gateway_helpers import _handle_cu_learning

    d = str(tmp_path)
    r = _handle_cu_learning(
        {
            "action": "start",
            "task_id": "w1",
            "objective": "o",
            "completion": [{"check": "url_contains", "target": "ok"}],
            "plan_dir": d,
        }
    )
    assert r["success"] and r["plan_id"]
    pid = r["plan_id"]
    r2 = _handle_cu_learning(
        {
            "action": "log_step",
            "task_id": "w1",
            "plan_id": pid,
            "op": "click",
            "intent": "点发布",
            "ok": True,
            "plan_dir": d,
        }
    )
    assert r2["success"] and r2["stop"] is False
    r4 = _handle_cu_learning(
        {"action": "complete", "task_id": "w1", "plan_id": pid, "evidence": {"url": "https://x.com/ok"}, "plan_dir": d}
    )
    assert r4["ok"] is True, r4
    r3 = _handle_cu_learning({"action": "count", "task_key": "w1", "plan_dir": d})
    assert r3["success_runs"] == 1
