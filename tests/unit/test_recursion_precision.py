"""递归检测精准化回归: echo A vs echo B 不重复; 同 key 连续 5 次(auto_pause_threshold)触发; path 完整匹配; browser_local URL/selector 递归 key"""
import sys
sys.path.insert(0, ".")
import pytest


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    import core.gateway.execute_agent_task as eat
    import core.gateway.shared_state as ss
    monkeypatch.setattr(eat, "_recursion_tracker", {})
    monkeypatch.setattr(ss, "_recursion_tracker", {})
    yield


def _call(task_id, tool, args):
    from core.gateway.path_utils import _extract_tool_path
    from core.gateway.execute_agent_task import check_recursion
    _p = _extract_tool_path(args, tool)
    return check_recursion(task_id, tool, _p)


def test_command_different_args_not_duplicate():
    """echo "=== core ===" 与 echo "=== config ===" 不同命令 → 不触发重复(warn/pause 均无)"""
    assert _call("t1", "execute_command", {"command": "echo \"=== core ===\""})[0] == "ok"
    assert _call("t1", "execute_command", {"command": "echo \"=== config ===\""})[0] == "ok", "不同命令不应计为重复"
    assert _call("t1", "execute_command", {"command": "echo \"=== data ===\""})[0] == "ok"


def test_command_same_five_times_pause():
    """echo "A" 连续 5 次(auto_pause_threshold) → 第 2 次 warn, 第 5 次 pause"""
    statuses = [_call("t2", "execute_command", {"command": "echo A"})[0] for _ in range(5)]
    assert statuses == ["ok", "warn", "warn", "warn", "pause"], statuses


def test_command_prefix_100_rule():
    """前 100 字符相同 → 视为重复(长命令规则); 不同则不算"""
    _c1 = "ls -la " + "d" * 110 + "_AAA"   # 长度 >100, 尾部不同
    _c2 = "ls -la " + "d" * 110 + "_BBB"   # 与 _c1 前 100 字符相同(尾部不同)
    assert len(_c1) > 100 and len(_c2) > 100
    assert _c1[:100] == _c2[:100], "前置应相同"
    r1 = _call("t3", "execute_command", {"command": _c1})
    r2 = _call("t3", "execute_command", {"command": _c2})
    assert r1[0] == "ok"
    assert r2[0] == "warn", "前 100 字符相同应计为重复"
    # 前 100 不同 → 不算
    _c3 = "grep foo " + "z" * 100 + " tail"
    assert _call("t3", "execute_command", {"command": _c3})[0] == "ok", "不同命令重置计数"


def test_read_path_full_match():
    """read_file: 完整 path 匹配 — a.py vs b.py 不重复(各自独立); a.py 连续 5 次触发"""
    assert _call("t4", "read_file", {"path": "a.py"})[0] == "ok"
    assert _call("t4", "read_file", {"path": "b.py"})[0] == "ok", "不同 path 不应重复(且不互相计数)"
    # 连续同 path: 第 2 次 warn, 第 5 次 pause
    statuses = [_call("t5", "read_file", {"path": "a.py"})[0] for _ in range(5)]
    assert statuses == ["ok", "warn", "warn", "warn", "pause"], statuses


def test_browser_local_different_urls_not_duplicate():
    """browser_local: 不同 URL 的 navigate 各自计数, 不误伤(<no-path> 修复) — 3 个不同 URL 全 ok"""
    for i in range(1, 4):
        st = _call("tb1", "browser_local", {"action": "navigate", "url": "https://www.xiaohongshu.com/note/%d" % i})[0]
        assert st == "ok", "第 %d 个不同 URL 不应触发重复: %s" % (i, st)


def test_browser_local_same_url_five_times_pause():
    """browser_local: 同 URL 连续 5 次才拦(阈值=5)"""
    statuses = [_call("tb2", "browser_local",
                     {"action": "navigate", "url": "https://www.xiaohongshu.com/note/9"})[0] for _ in range(5)]
    assert statuses == ["ok", "warn", "warn", "warn", "pause"], statuses


def test_browser_local_selector_key():
    """browser_local: 不同 selector 各自计数; 同 selector 累计"""
    assert _call("tb3", "browser_local", {"action": "click", "selector": ".btn-a"})[0] == "ok"
    assert _call("tb3", "browser_local", {"action": "click", "selector": ".btn-b"})[0] == "ok", "不同 selector 不误伤"
    assert _call("tb3", "browser_local", {"action": "extract", "selector": ".note-content"})[0] == "ok"
    # 同 selector 连续 5 次 → 第 5 次 pause
    statuses = [_call("tb4", "browser_local",
                     {"action": "fill", "selector": "input", "text": "x"})[0] for _ in range(5)]
    assert statuses == ["ok", "warn", "warn", "warn", "pause"], statuses





def test_evaluate_probes_distinct_hash():
    """B5: 不同函数探针(同前缀)不误判为重复; 同探针重复仍累计"""
    from core.gateway.path_utils import _extract_tool_path as _etp
    from core.gateway.execute_agent_task import check_recursion as _cr
    # 两个探针前 50 字符相同(都是 (() => { const progress = ...), 但 hash 不同
    _p1 = "(() => { const progress = [...document.querySelectorAll('a')].map(x => x.text) })()"
    _p2 = "(() => { const progress = [...document.querySelectorAll('button')].map(x => x.title) })()"
    assert _p1[:50] == _p2[:50], "前置应相同(复现误判场景)"
    k1 = _etp({"action": "evaluate", "expr": _p1}, "browser_local")
    k2 = _etp({"action": "evaluate", "expr": _p2}, "browser_local")
    assert k1 != k2, "不同探针 hash 应不同: %s vs %s" % (k1, k2)
    # 同探针连续 5 次 → 仍触发 pause(递归检测不失效)
    statuses = [_cr("tb5", "browser_local", k1)[0] for _ in range(5)]
    assert statuses == ["ok", "warn", "warn", "warn", "pause"], statuses
    # 非探针表达式保持前 50 字符规则
    assert _etp({"action": "evaluate", "expr": "document.title"}, "browser_local") == "browser_local:evaluate:document.title"


def test_sandbox_read_blocks_mnt_with_read_message():
    """B3: 读沙箱外(/mnt)报读取而非写入"""
    from core.gateway.sandbox_util import _check_sandbox_read as _csr
    for cmd in (
        'cat "/mnt/d/Obsidian/ClawsJoy/ClawsJoy/SOPs/番茄推广SOP.md" 2>/dev/null | head -120',
        "find / -name 'x.mp4' 2>/dev/null",
        "grep -r foo /mnt/c/Users/ 2>&1",
    ):
        err = _csr(cmd)
        assert err and "读取" in err, f"应报读取文案: {cmd!r} -> {err}"
    # 项目内读不受影响
    assert _csr("cat data/fanqie/tasks.json") is None
    assert _csr("sed -n '1,30p' data/fanqie/draft_weiren.md") is None


def test_browser_local_no_no_path():
    """browser_local 各动作递归 key 不再落 <no-path>(extract/click/fill/scroll 有独立 key)"""
    from core.gateway.path_utils import _extract_tool_path as _etp
    assert _etp({"action": "extract"}, "browser_local") == "browser_local:extract"
    assert _etp({"action": "scroll", "direction": "down"}, "browser_local") == "browser_local:scroll"
    assert _etp({"action": "click", "selector": ".a"}, "browser_local") == "browser_local:click:.a"
    assert _etp({"action": "navigate", "url": "https://x.com/1"}, "browser_local") == "browser_local:navigate:https://x.com/1"
    assert "<no-path>" not in [
        _etp({"action": "extract"}, "browser_local"),
        _etp({"action": "scroll"}, "browser_local"),
        _etp({"action": "click", "selector": ".a"}, "browser_local"),
        _etp({"action": "fill", "selector": "input"}, "browser_local"),
        _etp({"action": "navigate", "url": "https://x.com/2"}, "browser_local"),
    ]


def test_extract_tool_path_canonical():
    """canonicalize: command → 完整前缀 100; path → 完整值; 空 → <no-path>"""
    from core.gateway.path_utils import _extract_tool_path
    assert _extract_tool_path({"command": "echo hello world"}) == "echo hello world"
    long_cmd = "echo " + "x" * 150
    assert _extract_tool_path({"command": long_cmd}) == long_cmd[:100]
    assert _extract_tool_path({"path": "core/gateway/session_log.py"}) == "core/gateway/session_log.py"
    assert _extract_tool_path({}) == "<no-path>"


def test_browser_local_same_url_different_action_not_shared():
    """browser_local: 同 URL 不同 action 不共用计数(navigate(X) vs search(X) vs extract(X) 独立)"""
    X = "https://www.xiaohongshu.com/note/9"
    # 交错 navigate/search/extract 同一 URL, 各 3 次 → 均不触发重复(不同 action 各自计数)
    for _ in range(3):
        assert _call("tb5", "browser_local", {"action": "navigate", "url": X})[0] == "ok", "navigate 不应累计到 search"
        assert _call("tb5", "browser_local", {"action": "search", "query": "q", "url": X})[0] == "ok", "search 不应累计到 navigate"
        assert _call("tb5", "browser_local", {"action": "extract", "url": X})[0] == "ok", "extract 不应累计"
    # 同 action 同 URL 连续 5 次才拦(navigate 单独累计)
    statuses = [_call("tb6", "browser_local", {"action": "navigate", "url": X})[0] for _ in range(5)]
    assert statuses == ["ok", "warn", "warn", "warn", "pause"], statuses
