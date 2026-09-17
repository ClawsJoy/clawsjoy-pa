"""V9 跨线程隔离修复回归测试

根因: chat.js 模块级 sessionId/currentThread 是加载时快照, 线程切换(switchThread/newThread)
只更新 __APP_STATE/localStorage, 快照不更新 → 请求串到旧线程(3379), 恢复旧线程历史。
修复: 改为运行时读取 _curSession()/_curThread()。
"""
import sys

sys.path.insert(0, ".")
import pytest

_CHAT = open("web/static/js/chat.js", encoding="utf-8").read()


def test_runtime_helpers_exist():
    """chat.js 应有 _curSession/_curThread 运行时读取助手"""
    assert "function _curSession()" in _CHAT
    assert "function _curThread()" in _CHAT
    assert (
        "__APP_STATE.sessionId" in _CHAT and "clawsjoy_session_id" in _CHAT
    ), "_curSession 应读 __APP_STATE + localStorage"
    assert (
        "__APP_STATE.currentThread" in _CHAT and "current_thread" in _CHAT
    ), "_curThread 应读 __APP_STATE + localStorage"


def test_no_snapshot_in_requests():
    """请求体不应再用模块快照 sessionId(应运行时读取)"""
    # 请求体都应走 _curSession()
    assert "session_id: _curSession()" in _CHAT
    # 不应再有裸 session_id: sessionId 请求
    assert "session_id: sessionId" not in _CHAT, "请求体不应再用快照 sessionId"


def test_history_keys_use_runtime_thread():
    """localStorage 历史键应走 _curThread() 而非快照 currentThread"""
    assert "'agent_history_' + _curThread()" in _CHAT
    assert "'agent_pause_' + _curThread()" in _CHAT
    assert "'agent_logs_' + _curThread()" in _CHAT
    assert "'agent_history_' + currentThread" not in _CHAT, "历史键不应再用快照 currentThread"


def test_cancel_uses_runtime_session():
    """取消请求也应走 _curSession()"""
    assert "encodeURIComponent(_curSession())" in _CHAT


def test_user_id_runtime_read():
    """userId 也应运行时读取(线程切换后不串到旧用户沙箱)"""
    _APPROVAL = open("web/static/js/approval.js", encoding="utf-8").read()
    _SUBTASK = open("web/static/js/subtask-panel.js", encoding="utf-8").read()
    _DISCUSSION = open("web/static/js/discussion.js", encoding="utf-8").read()
    # chat.js
    assert "function _curUser()" in _CHAT
    assert "user_id: _curUser()" in _CHAT
    assert "user_id: userId" not in _CHAT, "chat.js 不应有 user_id: userId 残留"
    # approval.js
    assert "function _curUser()" in _APPROVAL
    assert "user_id: _curUser()" in _APPROVAL
    assert "user_id: userId" not in _APPROVAL, "approval.js 不应有残留"
    # subtask-panel.js
    assert "function _curUser()" in _SUBTASK
    assert "user_id: _curUser()" in _SUBTASK
    assert "user_id: userId" not in _SUBTASK, "subtask-panel.js 不应有残留"
    # discussion.js
    assert "function _curUser()" in _DISCUSSION
    assert "user_id: _curUser()" in _DISCUSSION
    assert "user_id: userId" not in _DISCUSSION, "discussion.js 不应有残留"
    assert "'web_' + _curUser()" in _DISCUSSION, "discussion 拼接也应运行时读取"
