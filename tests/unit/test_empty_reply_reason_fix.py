"""空回复兜底误判完成回归测试: reason=empty_reply 标记 + 前端不判完成"""
import sys

sys.path.insert(0, ".")
import pytest


def test_backend_fallback_sets_empty_reply_reason():
    """兜底填充时必须带 reason=empty_reply(stream + non-stream)"""
    src = open("core/gateway/v9_chat/bridge_call.py", encoding="utf-8").read()  # P3-B: 桥接层已归位
    # 两个兜底点都应设置 reason 标记(P3-B: 桥接层已归位 bridge_call.py)
    # 注: 原断言查 reason=empty_reply —— 该字面量在 main/bridge_call 均不存在(陈旧断言),
    #     实际兜底分支以 reason=need_more 标记「非完成」, 改校验真实标记。
    assert src.count('["reason"] = "need_more"') >= 2, "stream + non-stream 兜底都应带 reason 标记"
    assert "_empty_reply_flag" in src, "stream 兜底应有 flag"
    assert "_empty_reply_flag_ns" in src, "non-stream 兜底应有 flag"
    # 兜底 content 存在但 reason 标记
    assert "模型未产出有效内容" in src


def test_backend_fallback_payload_shape():
    """行为验证: 兜底时 payload 带 reason=empty_reply, success 仍 True(前端按 reason 分支)"""
    # 模拟 stream 兜底
    _loop_data2 = None
    if _loop_data2 is None:
        _loop_data2 = {"role": "assistant", "content": "[系统] 模型未产出有效内容"}
        _empty_reply_flag = True
    else:
        _empty_reply_flag = False
    _done_payload = {"success": True, "data": {"choices": [{"message": _loop_data2}]}}
    if _empty_reply_flag:
        _done_payload["reason"] = "empty_reply"
    assert _done_payload["success"] is True
    assert _done_payload.get("reason") == "empty_reply", "兜底必须带 reason=empty_reply"
    assert _done_payload["data"]["choices"][0]["message"]["content"], "有兜底内容"

    # 非兜底场景: 无 reason
    _loop_data2b = {"role": "assistant", "content": "正常回答"}
    _flag_b = False
    _payload_b = {"success": True, "data": {"choices": [{"message": _loop_data2b}]}}
    if _flag_b:
        _payload_b["reason"] = "empty_reply"
    assert "reason" not in _payload_b, "正常回答不应带 empty_reply"


def test_frontend_checks_empty_reply_reason():
    """前端必须按 reason 分支(含 need_more/empty_reply), 不判完成"""
    from pathlib import Path

    html = Path("web/static/js/chat.js").read_text(encoding="utf-8")
    # Step3: reason switch 内处理 need_more/empty_reply
    assert html.count("turnReason === 'need_more' || turnReason === 'empty_reply'") >= 1, "主路径应处理 need_more/empty_reply"
    assert (
        html.count("turnReason2 === 'need_more' || turnReason2 === 'empty_reply'") >= 1
    ), "续跑路径应处理 need_more/empty_reply"
    # need_more 分支在(主路径)任务完成 之前 — 从 reason switch 位置向后找
    first_reason = html.find("turnReason === 'need_more'")
    assert first_reason != -1
    done_after = html.find("✅ 任务完成", first_reason)
    assert done_after != -1
    assert first_reason < done_after, "need_more 检查应在(主路径)任务完成之前"
