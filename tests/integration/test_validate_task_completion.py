"""H1: _save_state 任务类型校验段提级为 _validate_task_completion"""
import sys
sys.path.insert(0, ".")
import pytest


def test_function_exists_and_signature():
    """模块级函数存在，签名含 messages/session_id/sub_task_id"""
    import inspect
    from core.gateway.execute_agent_task import _validate_task_completion
    sig = inspect.signature(_validate_task_completion)
    for p in ("messages", "session_id", "sub_task_id"):
        assert p in sig.parameters


def test_general_task_without_write_rejected(monkeypatch):
    """通用任务无写入 → 拒绝（返回 False）"""
    from core.gateway.execute_agent_task import _validate_task_completion
    monkeypatch.setattr("core.gateway.execute_agent_task._has_git_diff", lambda: False)
    messages = [{"role": "user", "content": "做一个分析"}]
    assert _validate_task_completion(messages, "sess_x") is False
    monkeypatch.setattr("core.gateway.execute_agent_task._has_git_diff", lambda: True)
    assert _validate_task_completion(messages, "sess_x") is True


def test_save_state_shrunk_further():
    """_save_state 再缩短（任务校验段 45 行移出）"""
    import ast
    tree = ast.parse(open("core/gateway/execute_agent_task.py", encoding="utf-8").read())
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == "_save_state":
            size = n.end_lineno - n.lineno + 1
            assert size < 350, f"_save_state 仍 {size} 行"
            return
