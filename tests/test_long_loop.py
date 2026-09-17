"""长线任务状态机冒烟测试"""
import pytest
from core.lib.v8.long_loop_state_machine import (
    LongLoopStateMachine, STATE_IDLE, STATE_PLANNING, STATE_EXECUTING, STATE_VERIFYING,
    STATE_COMPRESSING, STATE_RETRIEVING, STATE_ERROR, STATE_DONE, STATE_PAUSED
)

class FakeOrchestrator:
    def plan(self, user_input, user_id, server_id="default"):
        return {"tasks": [{"title": "step1"}, {"title": "step2"}]}
    def execute_task(self, task_data):
        pass

@pytest.fixture
def sm():
    return LongLoopStateMachine("test_task", "sess", "user", FakeOrchestrator())

def test_full_lifecycle(sm):
    sm._transition(STATE_PLANNING)
    assert sm.state == STATE_PLANNING
    sm._transition(STATE_EXECUTING)
    assert sm.state == STATE_EXECUTING
    sm._transition(STATE_VERIFYING)
    assert sm.state == STATE_VERIFYING
    sm._transition(STATE_COMPRESSING)
    assert sm.state == STATE_COMPRESSING
    sm._transition(STATE_RETRIEVING)
    assert sm.state == STATE_RETRIEVING
    sm._transition(STATE_EXECUTING)
    assert sm.state == STATE_EXECUTING
    sm._transition(STATE_DONE)
    assert sm.state == STATE_DONE

def test_illegal_transition(sm):
    sm._transition(STATE_PLANNING)
    sm._transition(STATE_EXECUTING)
    with pytest.raises(ValueError):
        sm._transition(STATE_IDLE)

def test_pause_resume(sm):
    sm._transition(STATE_PLANNING)
    sm._transition(STATE_EXECUTING)
    sm.pause()
    assert sm.state == STATE_PAUSED
    sm.resume()
    assert sm.state == STATE_EXECUTING

def test_error_rollback(sm):
    sm._transition(STATE_PLANNING)
    sm._transition(STATE_EXECUTING)
    for _ in range(4):
        sm._transition(STATE_ERROR)
        sm._enter_error()
        assert sm.state == STATE_EXECUTING
    # 第 5 次达到阈值，放弃执行
    sm._transition(STATE_ERROR)
    sm._enter_error()
    assert sm.state == STATE_DONE

def test_write_checkpoint(sm):
    sm._transition(STATE_PLANNING)
    cp = sm._write_checkpoint(1, {"test": True})
    assert cp["step_number"] == 1
    assert cp["state"] == STATE_PLANNING
    assert cp["extra"]["test"] is True
