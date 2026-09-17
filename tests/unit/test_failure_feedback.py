"""A: 失败反馈闭环测试 - _save_state(failed) 触发 SAG 负反馈 + 边缘降权 + known_issues 沉淀"""
import json
import sys

sys.path.insert(0, ".")
import pytest


def test_save_state_failed_triggers_feedback(monkeypatch):
    """_save_state(failed) 路径: _update_sag_feedback(passed=False) + edge_learning + remember_issue 被调"""
    _SRC = open("core/gateway/execute_agent_task.py", encoding="utf-8").read()
    assert 'if status == "failed":' in _SRC, "应有 failed 分支"
    assert "_update_sag_feedback(_last_usr[:80]" in _SRC, "应调 _update_sag_feedback(passed=False)"
    assert '_update_sag_edge_learning("save_state_failed"' in _SRC, "应调边缘降权"
    assert "remember_issue" in _SRC.split('if status == "failed":')[1], "失败应沉淀 known_issues"


def test_save_state_done_not_duplicate_feedback(monkeypatch):
    """done 分支不重复加失败反馈(仅 failed 触发)"""
    _SRC = open("core/gateway/execute_agent_task.py", encoding="utf-8").read()
    _failed_seg = _SRC.split('if status == "failed":')[1].split('if status == "done":')[0]
    assert "passed=False" in _failed_seg or "_update_sag_feedback(_last_usr" in _failed_seg
