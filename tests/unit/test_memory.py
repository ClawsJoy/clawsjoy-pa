"""跨 session 记忆持久层测试: 存储/加载/去重/上限淘汰/守卫触发写入/上下文格式"""
import sys

sys.path.insert(0, ".")
import pytest


@pytest.fixture(autouse=True)
def _mem_root(tmp_path, monkeypatch):
    """记忆落盘重定向到 tmp_path(不污染真实 data/projects)。"""
    import core.gateway.memory as mem

    monkeypatch.setattr(mem, "_MEMORY_ROOT", tmp_path)
    yield mem


# ===== 基础持久层 =====


def test_remember_and_load_roundtrip(_mem_root):
    """remember_issue/remember_pattern 落盘后可读回。"""
    assert _mem_root.remember_issue("u1", "连续失败execute_command: 权限不足") is not None
    assert _mem_root.remember_pattern("u1", "任务完成: 先验证再总结") is not None
    issues = _mem_root._load_memory("u1", "known_issues")
    patterns = _mem_root._load_memory("u1", "known_patterns")
    assert len(issues) == 1
    assert len(patterns) == 1
    assert issues[0]["content"] == "连续失败execute_command: 权限不足"


def test_user_isolation(_mem_root):
    """不同 user_id 记忆互不可见。"""
    _mem_root.remember_issue("u1", "问题A")
    _mem_root.remember_issue("u2", "问题B")
    assert len(_mem_root._load_memory("u1", "known_issues")) == 1
    assert _mem_root._load_memory("u1", "known_issues")[0]["content"] == "问题A"
    assert _mem_root._load_memory("u2", "known_issues")[0]["content"] == "问题B"


def test_dedup_updates_ts(_mem_root):
    """相同 content 去重: 条目数不变(ts 提前, 最新引用优先)。"""
    _mem_root.remember_issue("u1", "坑1")
    _mem_root.remember_issue("u1", "坑1")
    issues = _mem_root._load_memory("u1", "known_issues")
    assert len(issues) == 1


def test_cap_20_and_evict_oldest(_mem_root):
    """超 20 条按 ts 淘汰最旧, 只保留最新 20。"""
    for i in range(25):
        _mem_root.remember_issue("u1", f"坑{i:02d}")
    issues = _mem_root._load_memory("u1", "known_issues")
    assert len(issues) == 20
    contents = [e["content"] for e in issues]
    assert "坑00" not in contents  # 最旧的被淘汰
    assert "坑24" in contents  # 最新保留
    # ts 降序(最新在前)
    ts = [e.get("ts", 0) for e in issues]
    assert ts == sorted(ts, reverse=True)


def test_content_limit(_mem_root):
    """单条内容超 500 字符被截断。"""
    _mem_root.remember_issue("u1", "x" * 900)
    content = _mem_root._load_memory("u1", "known_issues")[0]["content"]
    assert len(content) <= 500


def test_empty_user_skipped(_mem_root):
    """无 user_id 不写记忆。"""
    assert _mem_root.remember_issue("", "坑") is None
    assert _mem_root._load_memory("", "known_issues") == []


def test_get_memory_context_format(_mem_root):
    """上下文格式: 「已知问题：」「已知模式：」按用户 spec。"""
    assert _mem_root.get_memory_context("u1") == ""  # 无记忆时为空
    _mem_root.remember_issue("u1", "同一URL重复抓取已拦截，请换源或搜索")
    _mem_root.remember_pattern("u1", "先验证再总结")
    ctx = _mem_root.get_memory_context("u1")
    assert "已知问题：" in ctx and "同一URL重复抓取已拦截" in ctx
    assert "已知模式：" in ctx and "先验证再总结" in ctx


def test_clear_memory(_mem_root):
    """clear_memory 可清单类或全部。"""
    _mem_root.remember_issue("u1", "坑1")
    _mem_root.remember_pattern("u1", "模式1")
    _mem_root.clear_memory("u1", "known_issues")
    assert _mem_root._load_memory("u1", "known_issues") == []
    assert len(_mem_root._load_memory("u1", "known_patterns")) == 1
    _mem_root.clear_memory("u1")
    assert _mem_root._load_memory("u1", "known_patterns") == []


def test_corrupt_file_tolerated(_mem_root):
    """损坏的 JSON 文件 → 读回空列表, 不抛异常。"""
    f = _mem_root._memory_file("u1", "known_issues")
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("{not json", encoding="utf-8")
    assert _mem_root._load_memory("u1", "known_issues") == []
    # 后续写入仍正常
    _mem_root.remember_issue("u1", "新坑")
    assert len(_mem_root._load_memory("u1", "known_issues")) == 1


# ===== 守卫触发写入 =====


def test_failure_pause_writes_issue(_mem_root, monkeypatch):
    """FailurePauseGuard 连续失败 8 次 → known_issues 沉淀(带 user_id)。"""
    import core.gateway.shared_state as ss

    ss._consecutive_failures.pop("s_m1", None)
    ss._paused_breakpoints.pop("s_m1", None)
    from core.gateway.guards.registry import FailurePauseGuard

    g = FailurePauseGuard()
    for i in range(8):
        g.check(
            {
                "tool": "execute_command",
                "result": {"success": False, "error": "权限不足"},
                "session_id": "s_m1",
                "user_id": "u_m1",
            }
        )
    issues = _mem_root._load_memory("u_m1", "known_issues")
    assert len(issues) == 1
    assert "execute_command" in issues[0]["content"]
    assert "权限不足" in issues[0]["content"]


def test_web_fetch_deny_writes_issue(_mem_root, monkeypatch):
    """WebFetchGuard 同 URL 第 4 次 deny → known_issues 沉淀。"""
    import core.gateway.execute_agent_task as eat

    monkeypatch.setattr(eat, "_recursion_tracker", {})
    from core.gateway.guards.registry import WebFetchGuard

    g = WebFetchGuard()
    denied = None
    for i in range(4):
        denied = g.check(
            {
                "tool": "fetch_web",
                "args": {"url": "https://a.com/x"},
                "session_id": "s_m2",
                "user_id": "u_m2",
            }
        )
    assert denied is not None
    issues = _mem_root._load_memory("u_m2", "known_issues")
    assert len(issues) == 1
    assert "同一URL" in issues[0]["content"] or "重复抓取" in issues[0]["content"]


def test_guard_first_call_no_memory(_mem_root, monkeypatch):
    """守卫首次正常调用不写记忆(未触发 deny/暂停), 主流程不受影响。"""
    import core.gateway.execute_agent_task as eat

    monkeypatch.setattr(eat, "_recursion_tracker", {})
    from core.gateway.guards.registry import WebFetchGuard

    g = WebFetchGuard()
    assert (
        g.check(
            {
                "tool": "fetch_web",
                "args": {"url": "https://a.com/x"},
                "session_id": "s_m3",
                "user_id": "u_m3",
            }
        )
        is None
    )
    assert _mem_root._load_memory("u_m3", "known_issues") == []
