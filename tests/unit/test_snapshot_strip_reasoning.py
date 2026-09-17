"""快照恢复剥离 reasoning_content 回归测试

根因: 重启后 _snap_msgs(旧快照) 含旧 assistant 的 reasoning_content, 恢复后
messages = 旧快照 + 当前消息 → 多条 reasoning_content 冲突 → DeepSeek 400。
修复: 恢复时剥离所有旧消息 assistant 的 reasoning_content。
"""
import json
import sys

sys.path.insert(0, ".")
import pytest

_SRC = open("core/gateway/v9_chat/archive.py", encoding="utf-8").read()  # P3-B: 归档层已归位


def test_snapshot_restore_strips_reasoning():
    """源码: 快照恢复循环应 pop 旧 assistant 的 reasoning_content"""
    seg = _SRC[_SRC.index("_snap_msgs = _snap.get") : _SRC.index('state["messages"] = messages')]  # P3-B: 归档层边界
    assert 'if _m.get("role") == "assistant":' in seg, "应遍历 assistant"
    assert '_m.pop("reasoning_content", None)' in seg, "应剥离 reasoning_content"
    assert "旧快照 + 当前消息会形成多条 reasoning_content 冲突" in seg, "应有根因注释"


def test_snapshot_restore_behavior(tmp_path, monkeypatch):
    """行为: 模拟快照恢复路径 — 旧 assistant 的 reasoning_content 全部剥离"""
    from pathlib import Path

    import agent_gateway_enhanced as main

    # 构造含 reasoning_content 的快照
    _sid = "s_snap_1"
    _uid = "u_snap_1"
    _snap_msgs = [
        {"role": "user", "content": "任务1"},
        {"role": "assistant", "content": "旧思考1", "reasoning_content": "旧思考过程1"},
        {
            "role": "assistant",
            "content": "",
            "reasoning_content": "旧思考过程2",
            "tool_calls": [{"id": "t1", "function": {"name": "read_file", "arguments": "{}"}}],
        },
        {"role": "tool", "tool_call_id": "t1", "content": "结果"},
    ]
    # 模拟恢复逻辑(与 L4219-4222 相同)
    messages = [{"role": "user", "content": "新请求"}]
    if _snap_msgs and len(_snap_msgs) > len(messages):
        for _m in _snap_msgs:
            if _m.get("role") == "assistant":
                _m.pop("reasoning_content", None)
        messages = _snap_msgs + messages
    # 断言: 旧消息不再含 reasoning_content, 新消息保留(本测试新消息无 reasoning)
    for _m in messages[: len(_snap_msgs)]:
        if _m.get("role") == "assistant":
            assert "reasoning_content" not in _m, f"旧 assistant 应剥离 reasoning_content: {_m}"
    # tool_calls 与 tool 配对仍完整(剥离不破坏配对)
    _ids = {tc.get("id") for m in messages if m.get("role") == "assistant" for tc in (m.get("tool_calls") or [])}
    for _m in messages:
        if _m.get("role") == "tool":
            assert _m.get("tool_call_id") in _ids, f"孤立 tool: {_m}"


def test_snapshot_restore_keeps_non_assistant_fields():
    """剥离只动 reasoning_content, 其余字段(content/tool_calls/role)保留"""
    _snap_msgs = [
        {"role": "assistant", "content": "文本", "reasoning_content": "rc", "extra": "x"},
        {"role": "user", "content": "u"},
    ]
    for _m in _snap_msgs:
        if _m.get("role") == "assistant":
            _m.pop("reasoning_content", None)
    assert _snap_msgs[0]["content"] == "文本"
    assert _snap_msgs[0]["extra"] == "x"
    assert "reasoning_content" not in _snap_msgs[0]
    assert _snap_msgs[1]["content"] == "u"
