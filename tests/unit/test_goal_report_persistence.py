"""任务完成报告持久化回归测试: report 字段落盘(goal 记录) + history API 回传 + 兼容性

测试分层(保证无 jwt 依赖环境也可全绿):
- 纯 goal_state 行为测试: update_goal_report / complete_goal(report=) / 旧 goal 兼容 / list_goals
- 源码检查(不 import 网关): history 路由含 report / _write_turn_end 接线
- 网关行为测试: 需 jwt 模块(CI 环境有), 缺失时 pytest.importorskip 跳过
"""
import json
import sys

sys.path.insert(0, ".")
import pytest


@pytest.fixture(autouse=True)
def _iso(monkeypatch, tmp_path):
    """隔离: goal 内存 + 落盘路径 + SessionLog 注册表(与 test_p1_goal_persistence 同构)"""
    import core.gateway.goal_state as gs
    import core.gateway.session_log as sl

    monkeypatch.setattr(sl, "_logs", {})
    _orig_get = sl.get_session_log

    def _get_iso(sid, base_dir=None):
        return _orig_get(sid, base_dir=tmp_path)

    monkeypatch.setattr(sl, "get_session_log", _get_iso)
    monkeypatch.setattr(gs, "_goals", {})
    monkeypatch.setattr(gs, "_GOALS_ROOT", tmp_path)
    monkeypatch.setattr(gs, "_state_file", lambda u, s: tmp_path / u / s / "clawsjoy_dev" / ".agent_state.json")
    monkeypatch.setattr(gs, "_goal_dir", lambda u, s: tmp_path / u / s / "clawsjoy_dev" / "goals")
    yield tmp_path


def _goal_event_payloads(sid):
    from core.gateway.session_log import get_session_log

    out = []
    for ev in get_session_log(sid)._events:
        if ev.type == "goal_event":
            out.append(ev.payload)
    return out


# ================= 纯 goal_state 行为 =================


def test_update_goal_report_persists(tmp_path):
    """P1: update_goal_report → goal 记录含 report + 文件双写 + goal_event"""
    from core.gateway.goal_state import create_goal, update_goal_report

    g = create_goal("u1", "sess1", "写报告")
    g = update_goal_report("u1", "sess1", "已完成调研，报告草稿如下…")
    assert g["report"] == "已完成调研，报告草稿如下…"
    gf = tmp_path / "u1" / "sess1" / "clawsjoy_dev" / "goals" / f"{g['goal_id']}.json"
    assert json.loads(gf.read_text(encoding="utf-8"))["report"] == "已完成调研，报告草稿如下…"
    evs = _goal_event_payloads("sess1")
    assert any(e.get("action") == "report" and e.get("report_len") > 0 for e in evs), evs
    assert g["status"] == "active"  # 状态不变


def test_update_goal_report_empty_and_truncate(tmp_path):
    """空报告跳过; 超长截断到 8000"""
    from core.gateway.goal_state import create_goal, update_goal_report

    g = create_goal("u1", "sess2", "任务")
    assert update_goal_report("u1", "sess2", "   ") is None
    assert "report" not in g, "空报告不应写入 report 字段"
    g = update_goal_report("u1", "sess2", "x" * 12000)
    assert len(g["report"]) == 8000


def test_complete_goal_with_report(tmp_path):
    """complete_goal(report=...) → status complete + report 落盘 + 幂等保留"""
    from core.gateway.goal_state import complete_goal, create_goal

    g = create_goal("u1", "sess3", "重构", plan=["a", "b"])
    g = complete_goal("u1", "sess3", report="重构完成，验证通过。")
    assert g["status"] == "complete"
    assert g["report"] == "重构完成，验证通过。"
    gf = tmp_path / "u1" / "sess3" / "clawsjoy_dev" / "goals" / f"{g['goal_id']}.json"
    disk = json.loads(gf.read_text(encoding="utf-8"))
    assert disk["status"] == "complete" and disk["report"] == "重构完成，验证通过。"
    g2 = complete_goal("u1", "sess3")  # 幂等: 不带 report → 保留原 report
    assert g2["report"] == "重构完成，验证通过。"


def test_old_goal_without_report_compat(tmp_path):
    """兼容: 旧 goal 无 report 字段 → 不报错, 不显示"""
    from core.gateway.goal_state import create_goal, get_goal, update_goal_report, update_goal_status

    g = create_goal("u1", "sess4", "老任务")
    assert "report" not in g, "创建时不默认加 report 字段(兼容旧格式)"
    g = update_goal_status("u1", "sess4", "complete")
    assert "report" not in g
    gf = tmp_path / "u1" / "sess4" / "clawsjoy_dev" / "goals" / f"{g['goal_id']}.json"
    assert "report" not in json.loads(gf.read_text(encoding="utf-8"))
    update_goal_report("u1", "sess4", "   ")  # 空 → 跳过
    assert "report" not in get_goal("u1", "sess4")


def test_list_goals_carries_report(tmp_path):
    """list_goals 返回带 report 的记录(供 history API)"""
    from core.gateway.goal_state import complete_goal, create_goal, list_goals

    create_goal("u1", "sess5", "任务五")
    complete_goal("u1", "sess5", report="五号任务完成报告")
    goals = list_goals("u1")
    assert len(goals) == 1 and goals[0]["report"] == "五号任务完成报告"


# ================= 源码检查(不 import 网关, 任意环境可跑) =================


def test_history_route_includes_report():
    """v9_goal_history 响应应含 report 字段(旧 goal 为空串)"""
    src = open("routes/session.py", encoding="utf-8").read()
    seg = src[src.index("def v9_goal_history()") :]
    assert '"report": str(_g.get("report") or "")[:8000]' in seg, "history 响应应含 report"


def test_write_turn_end_wires_report():
    """_write_turn_end 应调用 update_goal_report 落盘报告(不改状态)"""
    src = open("core/gateway/turn_protocol.py", encoding="utf-8").read()  # P3-A: _write_turn_end 已归位
    _s = src.index("def _write_turn_end")
    try:
        _e = src.index("\ndef ", _s + 10)  # 下一个顶层 def(可能已是文件末尾)
    except ValueError:
        _e = len(src)
    seg = src[_s:_e]
    assert 'update_goal_report(_g.get("user_id") or "", session_id, report)' in seg
    assert '"report": str(report)[:500]' in seg, "turn_end 审计事件应带 report(截断)"


def test_bridge_loop_computes_report():
    """桥接收敛点应计算 _turn_report(优先 _bmsg_final.content, 其次 tool_steps 摘要)并传给 _write_turn_end — 已归位 response_builder"""
    src = open("core/gateway/v9_bridge/response_builder.py", encoding="utf-8").read()
    assert '_turn_report = str(_bmsg_final.get("content") or "").strip()' in src
    assert "build_tool_steps_summary_fn(tool_steps)" in src
    assert "report=_turn_report or None" in src


# ================= 网关行为(需 jwt; 缺失时跳过) =================


def test_write_turn_end_persists_report(tmp_path):
    """_write_turn_end(report=...) → goal 报告持久化 + complete + 审计事件带 report"""
    pytest.importorskip("jwt")
    import agent_gateway_enhanced as main
    from core.gateway.goal_state import create_goal, get_goal

    create_goal("u1", "sess6", "调研任务", plan=["调研", "成稿"])
    main._write_turn_end(
        "sess6",
        turn_id=1,
        tokens=100,
        reason="completed",
        detail="assistant 有内容且无待执行 tool_calls",
        tools_n=2,
        report="调研完成：已收集 12 份资料并成稿。",
    )
    g2 = get_goal("u1", "sess6")
    assert g2["status"] == "complete"
    assert g2["report"] == "调研完成：已收集 12 份资料并成稿。"
    from core.gateway.session_log import get_session_log

    te = [ev.payload for ev in get_session_log("sess6")._events if ev.type == "turn_end"]
    assert te and te[0].get("report", "").startswith("调研完成")
    assert len(te[0]["report"]) <= 500


def test_write_turn_end_without_report_keeps_old(tmp_path):
    """无 report 的 turn_end 不覆盖已有报告"""
    pytest.importorskip("jwt")
    import agent_gateway_enhanced as main
    from core.gateway.goal_state import create_goal, get_goal, update_goal_report

    create_goal("u1", "sess7", "任务")
    update_goal_report("u1", "sess7", "阶段报告A")
    main._write_turn_end("sess7", turn_id=1, tokens=10, reason="max_tokens", detail="已达上限", tools_n=3)  # 无 report
    assert get_goal("u1", "sess7")["report"] == "阶段报告A"
