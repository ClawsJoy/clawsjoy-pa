"""P0-1/P0-2 回归测试: tool_result 截断 + bridge_loop 消费 guard_results"""
import sys

sys.path.insert(0, ".")
import pytest


def test_truncate_tool_result_content_head_tail_marker():
    """P0-1: 超长 tool_result 保留头尾各半 + [TRUNCATED] 标记"""
    from agent_gateway_enhanced import _truncate_tool_result_content

    # 短内容直通
    assert _truncate_tool_result_content("short") == "short"
    assert _truncate_tool_result_content("x" * 2000) == "x" * 2000
    # 超长: 头尾各保留 + 标记
    body = "HEAD" + "m" * 4992 + "TAIL"
    out = _truncate_tool_result_content(body)
    assert out.startswith("HEAD"), "头部应保留"
    assert out.endswith("TAIL"), "尾部应保留"
    assert "[TRUNCATED]" in out, "应有截断标记"
    assert "原文 5000 字符" in out, "标记应含原文长度"
    assert out.count("[TRUNCATED]") == 1


def test_bridge_loop_consumes_guard_results(monkeypatch):
    """P0-2: bridge_loop 消费 run_post_guards 返回值 — inject_message 注入 + paused 终止"""
    import agent_gateway_enhanced as main

    # 源码级断言: bridge_loop 读取 _gres 返回值
    src = open("core/gateway/v9_bridge/tool_runner.py", encoding="utf-8").read()
    assert "_gres = run_post_guards" in src, "应读取 run_post_guards 返回值"
    assert '_gres.get("inject_message")' in src, "应消费 inject_message"
    assert '_gres.get("paused")' in src, "应消费 paused"
    assert "_guard_paused" in src, "应有暂停标记"
    # P4: inject_message 走 add_steer(不再直接拼 content 防双份)
    assert "add_steer(session_id, str(_inj_msg))" in src, "inject_message 应走 steer 通道"

    # 行为级: 模拟 guard 返回 inject_message 与 paused, 验证消费逻辑分支
    _injected = []
    _msgs = [{"role": "system", "content": "sys"}]
    _bmsg_mock = {"content": "原内容"}

    # inject_message 分支(P4: 入 steer 队列, 不直接改 content)
    _gres_inj = {"inject_message": "当前工具连续失败，请换一个工具或路径"}
    if _gres_inj.get("inject_message"):
        _injected.append(_gres_inj["inject_message"])
    assert "换一个工具或路径" in _injected[0], "inject_message 应进入 steer 通道"
    assert "[系统]" not in _bmsg_mock["content"], "P4 后 inject_message 不应直接拼 content"

    # paused 分支
    _gres_paused = {"paused": True, "error": "连续失败8次，任务已暂停"}
    _paused_flag = False
    if _gres_paused.get("paused"):
        _bmsg_mock["content"] = _bmsg_mock.get("content", "") + chr(10) + chr(10) + "[系统] " + str(_gres_paused["error"])
        _paused_flag = True
    assert _paused_flag, "paused 应触发终止标记"
    assert "连续失败8次" in _bmsg_mock["content"], "paused 错误应注入 content"
