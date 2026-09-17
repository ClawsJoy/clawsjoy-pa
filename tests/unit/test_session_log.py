"""P2a: 会话事件溯源日志骨架测试"""
import sys, os, json
sys.path.insert(0, ".")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@127.0.0.1:5432/test")

import pytest
from pathlib import Path
from core.gateway.session_log import (
    SessionLog, SessionEvent, log_event, get_session_log,
    EV_ASSISTANT_MESSAGE, EV_TOOL_CALL, EV_TOOL_RESULT, EV_USER_MESSAGE,
)


@pytest.fixture(autouse=True)
def _clean(monkeypatch, tmp_path):
    import core.gateway.session_log as sl
    monkeypatch.setattr(sl, "_logs", {})
    # 隔离落盘目录: 清理真实 data/session_logs/ 残留
    _dir = Path("data/session_logs")
    if _dir.exists():
        for _f in _dir.glob("*.jsonl"):
            try:
                _f.unlink()
            except Exception:
                pass
    yield tmp_path
    if _dir.exists():
        for _f in _dir.glob("*.jsonl"):
            try:
                _f.unlink()
            except Exception:
                pass


def test_append_events_and_seq(tmp_path):
    """事件追加 + 序号递增"""
    log = SessionLog("s1", base_dir=tmp_path)
    e1 = log.append(EV_ASSISTANT_MESSAGE, {"content": "hi"})
    e2 = log.append(EV_TOOL_CALL, {"name": "read_file"})
    e3 = log.append(EV_TOOL_RESULT, {"call_id": "c1", "content": "ok"})
    assert [e.seq for e in log.events()] == [1, 2, 3]
    assert e1.session_id == "s1"
    assert e2.type == EV_TOOL_CALL


def test_file_written(tmp_path):
    """JSONL 落盘 + 重放恢复"""
    log = SessionLog("s2", base_dir=tmp_path)
    log.append(EV_ASSISTANT_MESSAGE, {"content": "hello"})
    log.append(EV_TOOL_CALL, {"name": "write_file", "arguments": {"path": "a.py"}})
    assert log.log_file.exists()
    lines = log.log_file.read_text(encoding="utf-8").strip().split(chr(10))
    assert len(lines) == 2
    # 重放: 新实例从文件恢复
    log2 = SessionLog("s2", base_dir=tmp_path)
    assert len(log2.events()) == 2
    assert log2.events()[0].payload["content"] == "hello"


def test_derive_messages_projection(tmp_path):
    """derive_messages 投影: user/assistant/tool_result, 其余事件不投影"""
    log = SessionLog("s3", base_dir=tmp_path)
    log.append(EV_USER_MESSAGE, {"content": "请写文件"})
    log.append(EV_ASSISTANT_MESSAGE, {"content": "", "tool_calls": [{"id": "c1"}]})
    log.append(EV_TOOL_CALL, {"name": "write_file"})
    log.append(EV_TOOL_RESULT, {"call_id": "c1", "content": "done"})
    msgs = log.derive_messages()
    assert len(msgs) == 3, f"应投影 3 条: {msgs}"
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"
    assert msgs[2]["role"] == "tool" and msgs[2]["tool_call_id"] == "c1"


def test_derive_filters_unexecuted_tool_calls(tmp_path):
    """P2b 修复: 终止时未执行的 tool_calls 从投影中过滤(防 DeepSeek 400)"""
    log = SessionLog("s_f", base_dir=tmp_path)
    log.append(EV_USER_MESSAGE, {"content": "task"})
    # 正常轮次: assistant + tool_result 配对
    log.append(EV_ASSISTANT_MESSAGE, {"content": "", "tool_calls": [{"id": "c1"}]})
    log.append(EV_TOOL_RESULT, {"call_id": "c1", "content": "ok"})
    # 最后一轮终止: assistant 有 tool_calls 但没执行(无 tool_result)
    log.append(EV_ASSISTANT_MESSAGE, {"content": "", "tool_calls": [{"id": "c2"}]})
    msgs = log.derive_messages()
    # 最后一条 assistant 不应再带 tool_calls
    last = msgs[-1]
    assert last["role"] == "assistant"
    assert "tool_calls" not in last, f"未执行的 tool_calls 应被过滤: {last}"
    # 正常轮次 tool_calls 保留
    assert msgs[1]["tool_calls"] == [{"id": "c1"}]
    assert msgs[2]["role"] == "tool" and msgs[2]["tool_call_id"] == "c1"


def test_derive_partial_filter_mixed_round(tmp_path):
    """P2b 修复: 同轮部分 tool_calls 有结果, 部分未执行 → 只保留有结果的"""
    log = SessionLog("s_g", base_dir=tmp_path)
    log.append(EV_ASSISTANT_MESSAGE, {"content": "", "tool_calls": [
        {"id": "c1"}, {"id": "c2"}]})
    log.append(EV_TOOL_RESULT, {"call_id": "c1", "content": "ok"})
    # c2 无结果(超限截断场景)
    msgs = log.derive_messages()
    assert msgs[0]["role"] == "assistant"
    assert msgs[0]["tool_calls"] == [{"id": "c1"}], f"应只保留有结果的 c1: {msgs[0]}"
    assert msgs[1]["tool_call_id"] == "c1"


def test_log_event_never_raises(tmp_path):
    """log_event 便捷写入不抛异常"""
    from core.gateway.session_log import log_event
    e = log_event("s4", EV_ASSISTANT_MESSAGE, {"content": "x"})
    assert e is not None and e.seq == 1


def test_seq_monotonic_on_reload(tmp_path):
    """重放后 seq 继续递增(不重置)"""
    log = SessionLog("s5", base_dir=tmp_path)
    log.append(EV_TOOL_CALL, {})
    log.append(EV_TOOL_CALL, {})
    log2 = SessionLog("s5", base_dir=tmp_path)
    e = log2.append(EV_TOOL_RESULT, {"call_id": "c"})
    assert e.seq == 3, f"重放后新事件 seq 应为 3: {e.seq}"


def test_double_write_does_not_affect_messages(tmp_path):
    """双写不影响现有 messages 行为(仅新增日志)"""
    # 模拟: 现有代码 messages.append + log_event 并行
    messages = []
    log = SessionLog("s6", base_dir=tmp_path)
    messages.append({"role": "assistant", "content": "hi"})
    log.append(EV_ASSISTANT_MESSAGE, {"content": "hi"})
    assert len(messages) == 1  # 原 messages 不变
    assert len(log.events()) == 1  # 日志独立记录
    assert messages[0]["content"] == log.events()[0].payload["content"]
