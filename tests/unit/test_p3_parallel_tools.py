"""P3 并行工具池回归测试: 配置 + 分组 + 串行 barrier + guard 串行 + 按序提交"""
import sys

sys.path.insert(0, ".")
import pytest


def test_policy_has_parallel_config():
    """P3: execution_policy.yaml 配置 max_parallel_tools=4 + exclusive_tools"""
    import yaml

    cfg = yaml.safe_load(open("config/v9/execution_policy.yaml", encoding="utf-8"))
    eb = cfg["execution_budget"]
    assert eb.get("max_parallel_tools") == 4, eb
    assert set(eb.get("exclusive_tools", [])) == {"write_file", "execute_command"}, eb
    # 运行时读取同一配置
    from core.gateway.shared_state import _load_v9_execution_policy

    eb2 = (_load_v9_execution_policy() or {}).get("execution_budget", {}) or {}
    assert int(eb2.get("max_parallel_tools", 4) or 0) == 4
    assert "execute_command" in (eb2.get("exclusive_tools") or [])


def test_split_pool_grouping_and_order():
    """P3: _v9_split_pool — 非 exclusive 未 deny → 并行; denied/exclusive → 串行且保序"""
    from core.gateway.v9_bridge.tool_runner import _v9_split_pool

    _excl = {"write_file", "execute_command"}
    items = [
        {"idx": 0, "btc": {}, "bfn": "read_file", "bargs": {}, "gdeny": None},
        {"idx": 1, "btc": {}, "bfn": "list_dir", "bargs": {}, "gdeny": None},
        {"idx": 2, "btc": {}, "bfn": "execute_command", "bargs": {}, "gdeny": None},
        {"idx": 3, "btc": {}, "bfn": "write_file", "bargs": {}, "gdeny": None},
        {"idx": 4, "btc": {}, "bfn": "read_file", "bargs": {}, "gdeny": {"reason": "拒绝"}},
        {"idx": 5, "btc": {}, "bfn": "search_files", "bargs": {}, "gdeny": None},
    ]
    par, ser = _v9_split_pool(items, _excl)
    assert [it["bfn"] for it in par] == ["read_file", "list_dir", "search_files"], par
    assert [it["bfn"] for it in ser] == ["execute_command", "write_file", "read_file"], ser
    # 串行组保模型调用顺序(idx 递增)
    _ids = [it["idx"] for it in ser]
    assert _ids == sorted(_ids), f"串行组应按模型调用顺序: {_ids}"


def test_bridge_source_pool_structure():
    """P3 源码级: bridge_loop 三段结构 — 串行 pre-guard → ThreadPool 并行/串行 → 按序提交"""
    src = open("agent_gateway_enhanced.py", encoding="utf-8").read()
    tr = open("core/gateway/v9_bridge/tool_runner.py", encoding="utf-8").read()
    assert "ThreadPoolExecutor" in tr, "应有 ThreadPool 并行执行"
    assert "max_parallel_tools" in tr, "应从 execution_policy 读并行上限"
    assert "exclusive_tools" in tr, "应读 exclusive 串行集合"
    assert "_v9_split_pool(" in tr, "应使用分组 helper"
    assert tr.index("run_pre_guards({") < tr.index("ThreadPoolExecutor"), "pre-guard 应先于并行执行"
    assert "for _it in pre_items:" in tr, "应按模型调用顺序提交"
    assert 'messages.append({"role": "tool", "tool_call_id": _btc.get("id", "")' in tr
    assert "_pre_terminal" in tr and "write_pending" in tr


def test_tool_router_consecutive_lock():
    """P3: 连续失败计数加锁(并行工具下多线程递增互斥)"""
    src = open("core/gateway/tool_router.py", encoding="utf-8").read()
    assert "_get_consecutive_lock" in src, "tool_router 应使用并发锁"
    assert "with _get_consecutive_lock():" in src
    # shared_state 提供锁
    ss = open("core/gateway/shared_state.py", encoding="utf-8").read()
    assert "def _get_consecutive_lock" in ss


def test_denied_tools_not_executed():
    """P3 源码级: denied 工具直接收集 deny 结果(不执行), 符合 '通过后才进并行池'"""
    src = open("core/gateway/v9_bridge/tool_runner.py", encoding="utf-8").read()
    assert '"guard_denied": True' in src, "denied 应有 guard_denied 标记"
    # 2026-09-13: 窗口 700→2000 —— _run_item 里加了缓存注释后 exec_tool_fn 被推出原窗口，
    # 断言意图(gdeny 判定先于执行)未变，属测试自身窗口过窄，非行为回归。
    _seg = src[src.index("def _run_item(_it):") : src.index("def _run_item(_it):") + 2000]
    assert _seg.index('_it["gdeny"] is not None') < _seg.index("exec_tool_fn"), "denied 应先返回不执行"


def test_exclusive_serial_barrier():
    """P3 源码级: exclusive 工具(写/命令)进串行组, 不与其他工具并行"""
    src = open("core/gateway/v9_bridge/tool_runner.py", encoding="utf-8").read()
    _seg = src[src.index("def _v9_split_pool") : src.index("def _v9_split_pool") + 700]
    assert 'it["bfn"] not in exclusive' in _seg, "并行组应排除 exclusive"
    assert 'it["bfn"] in exclusive' in _seg, "串行组应含 exclusive"
