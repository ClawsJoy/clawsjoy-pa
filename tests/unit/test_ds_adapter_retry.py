# -*- coding: utf-8 -*-
"""#14 回归: DeepSeek adapter 重试指数退避(源码分析 + 逻辑模拟)"""
import sys

sys.path.insert(0, ".")


def test_retry_loop_in_source():
    """execute_with_tools 源码含重试循环 + 指数退避"""
    src = open("core/lib/v8/adapters/deepseek_adapter.py", encoding="utf-8").read()
    assert "_max_retries = 3" in src, "缺 3 次重试"
    assert "2 * (2 ** _attempt_rt)" in src, "缺指数退避 2/4/8"
    assert "DS_RETRY" in src, "缺重试日志"
    assert "timeout=(30, 180 if thinking else 60)" in src, "超时配置保留"
    # 4xx 不重试
    assert "status_code >= 400 and resp.status_code < 500 and resp.status_code != 429" in src, "4xx 应不重试"


def test_backoff_sequence():
    """退避序列: 2/4/8"""
    waits = [2 * (2**i) for i in range(3)]
    assert waits == [2, 4, 8], waits


def test_retry_logic_simulation():
    """模拟: 第3次成功 → 返回成功; 3次失败 → 返回错误"""
    # 第3次成功
    calls = {"n": 0}

    def post():
        calls["n"] += 1
        if calls["n"] < 3:
            raise Exception("timed out")
        return {"status": 200, "usage": {"total_tokens": 10}}

    # 模拟 adapter 循环逻辑
    last_err = ""
    for attempt in range(3):
        try:
            r = post()
            if r["status"] == 200:
                result = {"success": True, "tokens": r["usage"]["total_tokens"]}
                break
        except Exception as e:
            last_err = str(e)
            if attempt < 2:
                w = 2 * (2**attempt)
    else:
        result = {"success": False, "error": f"重试3次仍失败: {last_err}"}
    assert result["success"] is True and calls["n"] == 3, result
    # 3次都失败
    calls2 = {"n": 0}

    def post2():
        calls2["n"] += 1
        raise Exception("timed out always")

    last_err2 = ""
    for attempt in range(3):
        try:
            post2()
        except Exception as e:
            last_err2 = str(e)
    result2 = {"success": False, "error": f"重试3次仍失败: {last_err2}"}
    assert result2["success"] is False and calls2["n"] == 3, result2
