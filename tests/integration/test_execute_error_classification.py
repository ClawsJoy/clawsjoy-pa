"""P1: _execute_agent_task 结构化错误分类"""
import sys

sys.path.insert(0, ".")
import pytest

from core.gateway.execute_agent_task import _classify_exception, _struct_error


def test_struct_error_shape():
    """_struct_error 返回 {code, message, detail}"""
    e = _struct_error("NETWORK", "连接失败", {"retry": 2})
    assert e["code"] == "NETWORK"
    assert e["message"] == "连接失败"
    assert e["detail"] == {"retry": 2}
    # message 截断 300
    long = _struct_error("X", "m" * 500)
    assert len(long["message"]) == 300


def test_classify_network():
    """网络异常 -> NETWORK"""
    for exc in (ConnectionError("network is unreachable"), TimeoutError("timeout")):
        assert _classify_exception(exc) == "NETWORK", exc
    assert _classify_exception(Exception("Failed to establish a new connection")) == "NETWORK"


def test_classify_llm_api():
    """LLM API 特征 -> LLM_API"""
    for msg in ("API错误: 400", "api key 未配置", "balance insufficient", "quota exceeded", "429 Too Many"):
        assert _classify_exception(Exception(msg)) == "LLM_API", msg


def test_classify_json():
    """JSON 解析 -> TOOL_ARGS"""
    assert _classify_exception(Exception("JSONDecodeError: Expecting value")) == "TOOL_ARGS"
    assert _classify_exception(ValueError("invalid json parse")) == "TOOL_ARGS"


def test_classify_default():
    """未知异常 -> UNKNOWN"""
    assert _classify_exception(Exception("some random failure")) == "UNKNOWN"
    assert _classify_exception(Exception()) == "UNKNOWN"
