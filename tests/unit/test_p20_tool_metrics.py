"""#20 性能指标统计回归测试: tool_flow 聚合(按工具/按任务 成功率/avg/P95)"""
import json
import sys

sys.path.insert(0, ".")
import pytest


@pytest.fixture(autouse=True)
def _iso(monkeypatch, tmp_path):
    """隔离: 指标文件路径(tmp_path) + SAG 落盘 no-op"""
    import sys
    import types

    import core.context.context_manager as cm

    _p = tmp_path / "tool_metrics.jsonl"
    monkeypatch.setattr(cm, "_TOOL_METRICS_PATH", str(_p))
    # 注入假 extractor 模块(SAG 落盘 no-op, 避免 DATABASE_URL 检查)
    _fake = types.ModuleType("core.lib.code_entity_extractor")
    _fake.extractor = types.SimpleNamespace(upsert_entity=lambda *a, **k: None)
    monkeypatch.setitem(sys.modules, "core.lib.code_entity_extractor", _fake)
    yield _p


def test_record_and_stats_by_tool(tmp_path):
    """记录多条后: 按工具统计 成功率/avg/P95"""
    import core.context.context_manager as cm

    # 成功 3 次(100/200/300ms) + 失败 1 次(400ms) → success_rate 75, avg 250, p95 400
    cm.record_tool_flow("read_file", {}, "success (100ms)", "u1", "s1")
    cm.record_tool_flow("read_file", {}, "success (200ms)", "u1", "s1")
    cm.record_tool_flow("read_file", {}, "success (300ms)", "u1", "s1")
    cm.record_tool_flow("read_file", {}, "file not found (400ms)", "u1", "s1")
    cm.record_tool_flow("execute_command", {}, "success (50ms)", "u1", "s1")
    st = cm.tool_flow_stats()
    assert st["total"] == 5, st
    rf = st["by_tool"]["read_file"]
    assert rf["count"] == 4 and rf["success"] == 3 and rf["fail"] == 1
    assert rf["success_rate"] == 75.0, rf["success_rate"]
    assert rf["avg_ms"] == 250.0, rf["avg_ms"]
    assert rf["p95_ms"] == 400, rf["p95_ms"]  # 4条升序 [100,200,300,400], idx=int(4*0.95)=3
    ec = st["by_tool"]["execute_command"]
    assert ec["success_rate"] == 100.0 and ec["avg_ms"] == 50.0


def test_stats_by_task(tmp_path):
    """按任务(session)聚合"""
    import core.context.context_manager as cm

    cm.record_tool_flow("read_file", {}, "success (100ms)", "u1", "sessA")
    cm.record_tool_flow("write_file", {}, "success (200ms)", "u1", "sessA")
    cm.record_tool_flow("read_file", {}, "fail x (300ms)", "u1", "sessB")
    st = cm.tool_flow_stats()
    a = st["by_task"]["sessA"]
    assert a["count"] == 2 and a["success"] == 2 and a["success_rate"] == 100.0
    b = st["by_task"]["sessB"]
    assert b["count"] == 1 and b["fail"] == 1 and b["success_rate"] == 0.0


def test_stats_window_filter(_iso):
    """窗口过滤: 旧记录不计入"""
    import time as _t

    import core.context.context_manager as cm

    cm.record_tool_flow("read_file", {}, "success (100ms)", "u1", "s1")
    # 手动追加一条 25h 前的记录
    with open(str(_iso), "a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "tool": "old_tool",
                    "session_id": "s_old",
                    "user_id": "u1",
                    "success": True,
                    "elapsed_ms": 999,
                    "ts": _t.time() - 25 * 3600,
                }
            )
            + chr(10)
        )
    st = cm.tool_flow_stats(window_hours=24)
    assert st["total"] == 1, st["total"]  # 只算最近 24h 的 1 条
    assert "old_tool" not in st["by_tool"]


def test_stats_exception_path(tmp_path):
    """异常路径也记录(exception: xxx (Nms)) → 计入 fail"""
    import core.context.context_manager as cm

    cm.record_tool_flow("execute_command", {}, "exception: boom (150ms)", "u1", "s1")
    st = cm.tool_flow_stats()
    ec = st["by_tool"]["execute_command"]
    assert ec["count"] == 1 and ec["fail"] == 1 and ec["success_rate"] == 0.0
    assert ec["avg_ms"] == 150.0


def test_stats_empty(tmp_path):
    """无数据: 空统计不报错"""
    import core.context.context_manager as cm

    st = cm.tool_flow_stats()
    assert st["total"] == 0 and st["by_tool"] == {} and st["by_task"] == {}


def test_parse_success_false_not_misjudged(tmp_path):
    """#20审核修复: 'success=False (Nms)' 不应被误判为成功"""
    import core.context.context_manager as cm

    cm.record_tool_flow("execute_command", {}, "success=False (150ms)", "u1", "s1")
    cm.record_tool_flow("execute_command", {}, "success (200ms)", "u1", "s1")
    st = cm.tool_flow_stats()
    ec = st["by_tool"]["execute_command"]
    # 第1条(success=False)算失败, 第2条(success ())算成功 → 50% 成功率
    assert ec["count"] == 2 and ec["success"] == 1 and ec["fail"] == 1, ec
    assert ec["success_rate"] == 50.0, ec["success_rate"]


def test_parse_success_with_space_prefix(tmp_path):
    """#20审核修复: 前缀空格的成功 summary 仍识别为成功"""
    import core.context.context_manager as cm

    cm.record_tool_flow("read_file", {}, "  success (80ms)", "u1", "s1")
    st = cm.tool_flow_stats()
    rf = st["by_tool"]["read_file"]
    assert rf["count"] == 1 and rf["success"] == 1, rf
