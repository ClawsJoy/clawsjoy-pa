"""H1: _save_state 的 G4 审计复核段提取为模块函数"""
import sys, json
sys.path.insert(0, ".")
import pytest


def test_audit_cross_check_function_exists():
    """模块级 _audit_cross_check_save 存在且签名正确"""
    import inspect
    from core.gateway.execute_agent_task import _audit_cross_check_save
    sig = inspect.signature(_audit_cross_check_save)
    for p in ("messages", "session_id", "sub_task_id", "dw", "dw_res"):
        assert p in sig.parameters, f"缺参数 {p}"


def test_audit_cross_check_passes_empty():
    """空 messages（无声称）→ 通过（不误拦）"""
    from core.gateway.execute_agent_task import _audit_cross_check_save
    assert _audit_cross_check_save([], "sess_x") is True


def test_audit_cross_check_fake_write_rejected():
    """声称 write_file 但审计无记录 → 拒绝（返回 False）"""
    from core.gateway.execute_agent_task import _audit_cross_check_save
    # mock audit 模块让 read_audit_records 返回空
    import core.gateway.audit as AUDIT
    AUDIT.read_audit_records = lambda **kw: []
    messages = [{"role": "assistant", "tool_calls": [{"function": {"name": "write_file", "arguments": "{}"}}]}]
    assert _audit_cross_check_save(messages, "sess_x") is False


def test_save_state_shrunk():
    """_save_state 行数较原 397 减少（>30 行）"""
    import ast
    tree = ast.parse(open("core/gateway/execute_agent_task.py", encoding="utf-8").read())
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == "_save_state":
            assert n.end_lineno - n.lineno + 1 < 397 - 30, f"_save_state 仍过大: {n.end_lineno-n.lineno+1} 行"
            return
