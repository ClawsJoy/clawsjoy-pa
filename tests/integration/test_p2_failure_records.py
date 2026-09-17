"""P2: 工具执行失败 [TOOL_EXEC] 分类 + agent_actions 失败记录(insert_agent_action)"""
import json
import os
import sys

sys.path.insert(0, ".")
from pathlib import Path

import pytest

os.environ.setdefault("DEEPSEEK_API_KEY", "test-key-for-p2")

from core.gateway.execute_agent_task import _execute_agent_task


class _FakeAdapter:
    """mock DeepSeekAdapter: 第一轮返回工具调用(no_such_tool), 触发工具执行失败"""

    def __init__(self, *a, **k):
        pass

    def execute_with_tools(self, **k):
        return {
            "success": True,
            "data": {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": "call_p2_1",
                                    "type": "function",
                                    "function": {
                                        "name": "no_such_tool",
                                        "arguments": '{"path": "x.txt"}',
                                    },
                                }
                            ],
                        }
                    }
                ]
            },
            "tokens": 3,
        }


class _ApiFailAdapter:
    """mock: LLM API 调用直接失败 -> LLM_API 路径"""

    def __init__(self, *a, **k):
        pass

    def execute_with_tools(self, **k):
        return {"success": False, "error": "API错误: 402 balance insufficient"}


@pytest.fixture()
def p2_env(monkeypatch, tmp_path):
    """隔离环境: mock 外部依赖, 捕获 insert_agent_action 调用"""
    import core.gateway.execute_agent_task as eat
    from core.lib import code_entity_extractor as cee
    from core.lib.v8.adapters import deepseek_adapter as dsa

    monkeypatch.setattr(dsa, "DeepSeekAdapter", _FakeAdapter)

    # 工具执行必失败
    def _boom(*a, **k):
        raise RuntimeError("no such tool: boom")

    monkeypatch.setattr(eat, "_execute_sandbox_tool", _boom)
    # 屏蔽 DB/外部副作用
    from core.lib import gateway_helpers as gh

    monkeypatch.setattr(gh, "recap_checkpoint", lambda *a, **k: "")
    monkeypatch.setattr(eat, "audit_agent_output", lambda *a, **k: [])
    monkeypatch.setattr(eat, "check_recursion", lambda *a, **k: ("ok", ""))
    monkeypatch.setattr(eat, "_validate_task_completion", lambda *a, **k: True)
    monkeypatch.setattr(eat, "_audit_cross_check_save", lambda *a, **k: True)
    monkeypatch.setattr(eat, "_get_task_done_when", lambda *a, **k: None)
    monkeypatch.setattr(
        eat,
        "get_mode_tools",
        lambda *a, **k: ["read_file", "write_file", "list_dir", "search_files", "execute_command", "query_index"],
    )
    # 捕获 agent_actions 写入
    calls = []

    class _Recorder:
        def insert_agent_action(self, **kw):
            calls.append(kw)

    monkeypatch.setattr(cee, "extractor", _Recorder())
    # 隔离 cwd, 避免污染工作区 data/
    monkeypatch.chdir(tmp_path)
    return calls


def _run(uid, sid, messages, adapter=None, p2_env=None):
    import core.gateway.execute_agent_task as eat
    from core.lib.v8.adapters import deepseek_adapter as dsa

    if adapter:
        dsa.DeepSeekAdapter = adapter
    return _execute_agent_task(uid, sid, messages, "mock-model", task_id=f"t_{sid}")


def test_tool_failure_toolexec_recorded(p2_env):
    """工具失败: [TOOL_EXEC] 前缀 + 工具名 + agent_actions(failed, {code,message})"""
    uid, sid = "p2u1", "p2s1"
    _run(uid, sid, [{"role": "user", "content": "测试任务"}], p2_env=p2_env)
    calls = p2_env
    assert calls, "应调用 insert_agent_action"
    rec = calls[-1]
    assert rec["tool_name"] == "failed", f"tool_name 应为 failed: {rec['tool_name']}"
    result = json.loads(rec["result"])
    assert result["code"] == "TOOL_EXEC", f"code 应为 TOOL_EXEC: {result}"
    assert "no_such_tool" in result["message"], f"message 应含工具名: {result['message']}"
    assert rec["file_type"] == "task_failure"
    # state_file 落盘含 [TOOL_EXEC] 前缀
    st = Path("data") / "projects" / uid / sid / ".task_state.json"
    assert st.exists(), f"state_file 应存在: {st}"
    raw = st.read_text(encoding="utf-8")
    data = json.loads(raw)
    assert data["status"] == "failed"
    assert "[TOOL_EXEC]" in data["content"], f"content 应含 [TOOL_EXEC]: {data['content']}"
    assert "no_such_tool" in data["content"]


def test_api_failure_llm_api_recorded(p2_env):
    """LLM API 失败: agent_actions(failed, {code:LLM_API})"""
    uid, sid = "p2u2", "p2s2"
    _run(uid, sid, [{"role": "user", "content": "测试任务"}], adapter=_ApiFailAdapter, p2_env=p2_env)
    calls = p2_env
    assert calls, "应调用 insert_agent_action"
    rec = calls[-1]
    assert rec["tool_name"] == "failed"
    result = json.loads(rec["result"])
    assert result["code"] == "LLM_API", f"code 应为 LLM_API: {result}"
    assert "402" in result["message"]


def test_outer_except_recorded(p2_env, monkeypatch):
    """外层兜底: 未知异常 -> UNKNOWN 也写入 agent_actions

    ⑤(2026-09-13) 换故障注入点: 原 patch `eat._finalize_messages` 抛异常已**不可达** —
    工具执行失败分支(execute_agent_task.py:1666-1674)记完 TOOL_EXEC 直接 return,
    函数已退出 → 之后的 finalize/外层 except(`:1711`)都不会走到(探针实测 finalize 调用 0 次,
    记录码恒为 TOOL_EXEC)。改为在**必然经过**的 _save_state 链上注入:
    让工具执行成功(流程继续) + _validate_task_completion 抛错 → 冒泡到外层 except → UNKNOWN。
    """
    import core.gateway.execute_agent_task as eat

    uid, sid = "p2u3", "p2s3"
    # 工具执行改成功(否则 1674 提前 return, 到不了 _save_state)
    monkeypatch.setattr(eat, "_execute_sandbox_tool", lambda *a, **k: {"success": True, "content": "ok"})

    _n = {"calls": 0}

    def _boom(*a, **k):
        # 只炸第一次: 外层 except 里还会再调一次 _save_state("failed")
        # (execute_agent_task.py:1716), 若继续抛错会越出函数、UNKNOWN 记录写不下来
        _n["calls"] += 1
        if _n["calls"] == 1:
            raise ValueError("random boom outside tool loop")
        return True

    monkeypatch.setattr(eat, "_validate_task_completion", _boom)  # 覆盖 fixture 的 True
    _run(uid, sid, [{"role": "user", "content": "测试任务"}], p2_env=p2_env)
    calls = p2_env
    assert calls, "应调用 insert_agent_action"
    rec = calls[-1]
    assert rec["tool_name"] == "failed"
    result = json.loads(rec["result"])
    assert result["code"] in ("UNKNOWN", "TOOL_ARGS"), f"code: {result}"


def test_failure_record_never_crashes(p2_env):
    """insert_agent_action 抛异常不阻断主流程(降级忽略)"""
    import core.gateway.execute_agent_task as eat
    from core.lib import code_entity_extractor as cee

    class _BoomRecorder:
        def insert_agent_action(self, **kw):
            raise RuntimeError("db down")

    cee.extractor = _BoomRecorder()
    # 工具失败路径本身不崩
    _run("p2u4", "p2s4", [{"role": "user", "content": "测试任务"}], p2_env=p2_env)
    # 若 exec 正常返回或按失败路径归档, 均视为通过(不抛)
    assert True
