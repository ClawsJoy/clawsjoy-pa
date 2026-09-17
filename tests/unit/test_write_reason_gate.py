# -*- coding: utf-8 -*-
"""2026-09-07: write_file 缺 reason 在桥接 agent 路径拦截(审批卡必带写理由)。
人工审核两次看到缺 reason 的根因: reason 缺失放行进审批卡。
守卫层保持宽容(卡内提示); 桥接 S3 门在 agent 路径强制 reason。"""
import sys

sys.path.insert(0, ".")
from core.gateway.shared_state import empty_arg_error


def test_shared_helper_original_semantics():
    """shared 层 write_file 只查 path(守卫层语义不变)"""
    assert empty_arg_error("write_file", {"path": "x"}) == ""
    assert empty_arg_error("write_file", {}) != ""


def test_bridge_has_reason_gate():
    """桥接 S3 门含 write_file reason 强制"""
    src = open("core/gateway/v9_bridge/tool_runner.py", encoding="utf-8").read()
    assert "write_file 缺少必填参数 reason" in src
    assert '_bfn == "write_file" and not _l5e' in src
    assert "请说明写该文件的理由" in src


def test_bridge_steer_text_mentions_reason():
    """空参引导文案提示 reason"""
    src = open("core/gateway/v9_bridge/tool_runner.py", encoding="utf-8").read()
    assert "reason" in src
