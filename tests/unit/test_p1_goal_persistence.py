"""P1 Goal 持久化回归测试: progress/history/source_turn + 独立 goals/ 文件 + goal_event 双写 + 新接口"""
import json
import sys

sys.path.insert(0, ".")
import pytest


@pytest.fixture(autouse=True)
def _iso(monkeypatch, tmp_path):
    """隔离: goal 内存 + 落盘路径 + SessionLog 注册表"""
    import core.gateway.goal_state as gs
    import core.gateway.session_log as sl

    monkeypatch.setattr(sl, "_logs", {})
    # 磁盘隔离: 注册表默认落 data/session_logs/ 会跨 run 累积(JSONL 重放) → 注入 tmp_path
    _orig_get = sl.get_session_log

    def _get_iso(sid, base_dir=None):
        return _orig_get(sid, base_dir=tmp_path)

    monkeypatch.setattr(sl, "get_session_log", _get_iso)
    monkeypatch.setattr(gs, "_goals", {})
    monkeypatch.setattr(gs, "_GOALS_ROOT", tmp_path)

    def _sf(u, s):
        return tmp_path / u / s / "clawsjoy_dev" / ".agent_state.json"

    def _gd(u, s):
        return tmp_path / u / s / "clawsjoy_dev" / "goals"

    monkeypatch.setattr(gs, "_state_file", _sf)
    monkeypatch.setattr(gs, "_goal_dir", _gd)
    yield tmp_path


def _goal_event_payloads(sid):
    from core.gateway.session_log import get_session_log

    out = []
    for ev in get_session_log(sid)._events:
        if ev.type == "goal_event":
            out.append(ev.payload)
    return out


def test_create_goal_new_fields_and_dual_write(tmp_path):
    """P1: create_goal 带 progress/history/source_turn/session_id; goals 独立文件 + goal_event"""
    from core.gateway.goal_state import create_goal

    g = create_goal("u1", "sess1", "写报告", plan=["调研", "成稿", "校对"], task_id="t1")
    assert g["goal_id"].startswith("goal_u1_")
    assert g["progress"] == {"done": 0, "total": 3, "completed_steps": [], "pct": 0}, g["progress"]
    assert g["history"] == []
    assert g["source_turn"] is None
    assert g["session_id"] == "sess1" and g["user_id"] == "u1"
    # 独立文件
    gf = tmp_path / "u1" / "sess1" / "clawsjoy_dev" / "goals" / f"{g['goal_id']}.json"
    assert gf.exists(), "goals/{goal_id}.json 应落盘"
    disk = json.loads(gf.read_text(encoding="utf-8"))
    assert disk["objective"] == "写报告" and disk["progress"]["total"] == 3
    # .agent_state.json 兼容保留
    state = json.loads((tmp_path / "u1" / "sess1" / "clawsjoy_dev" / ".agent_state.json").read_text(encoding="utf-8"))
    assert state["goal"]["goal_id"] == g["goal_id"]
    # goal_event
    evs = _goal_event_payloads("sess1")
    assert any(e.get("action") == "created" and e.get("goal_id") == g["goal_id"] for e in evs), evs


def test_update_goal_progress(tmp_path):
    """P1: progress 更新 → pct/completed_steps/history/source_turn + 双写 + 事件"""
    from core.gateway.goal_state import create_goal, update_goal_progress

    g = create_goal("u1", "sess2", "重构模块", plan=["p1", "p2", "p3", "p4", "p5"])
    g = update_goal_progress("u1", "sess2", done=2, total=5, step="s1", turn_id=7)
    p = g["progress"]
    assert p["done"] == 2 and p["total"] == 5 and p["pct"] == 40, p
    assert p["completed_steps"] == ["s1"]
    assert g["source_turn"] == 7
    assert g["history"][-1]["turn_id"] == 7 and g["history"][-1]["delta"].startswith("done 0->2")
    # 文件同步
    gf = tmp_path / "u1" / "sess2" / "clawsjoy_dev" / "goals" / f"{g['goal_id']}.json"
    assert json.loads(gf.read_text(encoding="utf-8"))["progress"]["pct"] == 40
    evs = _goal_event_payloads("sess2")
    assert any(e.get("action") == "progress" and e.get("pct") == 40 for e in evs), evs
    # 幂等去重 step
    g = update_goal_progress("u1", "sess2", done=2, step="s1", turn_id=8)
    assert g["progress"]["completed_steps"] == ["s1"], "重复 step 不追加"


def test_get_goal_by_id_cross_session(tmp_path):
    """P1: get_goal_by_id 跨 session(先内存, 再磁盘扫描)"""
    from core.gateway.goal_state import create_goal, get_goal_by_id

    g = create_goal("u1", "sessA", "目标A")
    # 内存命中
    assert get_goal_by_id(g["goal_id"])["objective"] == "目标A"
    # 模拟重启: 清内存 → 磁盘扫描命中
    import core.gateway.goal_state as gs

    monkeypatch_clear = gs._goals.clear()
    assert get_goal_by_id(g["goal_id"])["objective"] == "目标A", "重启后应从 goals 文件恢复"
    assert get_goal_by_id("no_such_goal") is None


def test_list_goals_filter_and_limit(tmp_path):
    """P1: list_goals 按用户/状态过滤 + limit"""
    from core.gateway.goal_state import create_goal, list_goals, update_goal_status

    create_goal("u1", "sessX", "目标X")
    create_goal("u1", "sessY", "目标Y")
    create_goal("u2", "sessZ", "别人的")
    update_goal_status("u1", "sessY", "complete")
    gs_u1 = list_goals("u1")
    assert len(gs_u1) == 2, f"u1 应有 2 个: {[g['objective'] for g in gs_u1]}"
    assert list_goals("u1", status="complete")[0]["objective"] == "目标Y"
    assert all(g["user_id"] == "u2" for g in list_goals("u2"))
    assert len(list_goals("u1", limit=1)) == 1


def test_archive_goal(tmp_path):
    """P1: archive_goal → 状态 archived + 文件移到 goals/archive/ + 事件"""
    from core.gateway.goal_state import archive_goal, create_goal

    g = create_goal("u1", "sessA1", "归档目标")
    g = archive_goal("u1", "sessA1")
    assert g["status"] == "archived"
    arch = tmp_path / "u1" / "sessA1" / "clawsjoy_dev" / "goals" / "archive" / f"{g['goal_id']}.json"
    assert arch.exists(), "归档文件应保留在 goals/archive/"
    assert json.loads(arch.read_text(encoding="utf-8"))["status"] == "archived"
    assert any(e.get("action") == "archived" for e in _goal_event_payloads("sessA1"))


def test_turn_end_associates_goal(tmp_path):
    """P1 核心: _write_turn_end 带 goal_id + progress delta; progress 随轮推进; completed → 补齐+complete"""
    import agent_gateway_enhanced as main
    from core.gateway.goal_state import create_goal
    from core.gateway.session_log import get_session_log

    g = create_goal("u1", "sess_t", "部署上线", plan=["a", "b", "c", "d", "e"])
    # 轮1: max_tokens, 3 工具 → done 0->3 (60%)
    main._write_turn_end("sess_t", 42, 100, "max_tokens", "继续", 3)
    g1 = create_goal("u1", "sess_t", "部署上线")  # 复用 active goal
    assert g1["progress"]["done"] == 3 and g1["progress"]["pct"] == 60, g1["progress"]
    assert g1["source_turn"] == 42
    # turn_end 事件带 goal_id + progress_delta
    turn_ends = [ev.payload for ev in get_session_log("sess_t")._events if ev.type == "turn_end"]
    assert turn_ends and turn_ends[0].get("goal_id") == g["goal_id"], turn_ends
    assert turn_ends[0]["progress_delta"] == {"done": 3, "total": 5, "pct": 60}, turn_ends[0]
    # 轮2: completed → done 补齐 5 (100%) + goal complete
    main._write_turn_end("sess_t", 43, 50, "completed", "全部完成", 2)
    from core.gateway.goal_state import get_goal_by_id

    g2 = get_goal_by_id(g["goal_id"])
    assert g2["progress"]["done"] == 5 and g2["progress"]["pct"] == 100, g2["progress"]
    assert g2["status"] == "complete"


def test_turn_end_attaches_goal_when_already_complete(tmp_path):
    """P1 修复: goal 已被 ✅ 路径 complete 后, turn_end 仍带 goal_id + progress delta(不跳过)"""
    import agent_gateway_enhanced as main
    from core.gateway.goal_state import create_goal, get_goal_by_id, update_goal_status
    from core.gateway.session_log import get_session_log

    g = create_goal("u1", "sess_done", "已完成任务", plan=["a", "b"])
    update_goal_status("u1", "sess_done", "complete")  # 模拟 ✅ 路径先 complete
    main._write_turn_end("sess_done", 55, 80, "max_tokens", "工具执行后收尾", 3)
    # turn_end 事件必须带 goal_id + progress_delta
    turn_ends = [ev.payload for ev in get_session_log("sess_done")._events if ev.type == "turn_end"]
    assert turn_ends and turn_ends[-1].get("goal_id") == g["goal_id"], turn_ends
    assert turn_ends[-1]["progress_delta"]["done"] == 3, turn_ends[-1]
    # progress 仍推进(不被 complete 状态跳过)
    g2 = get_goal_by_id(g["goal_id"])
    assert g2["progress"]["done"] == 3, g2["progress"]


def test_goal_context_injection_progress(tmp_path):
    """P1: goal_context_injection 注入 progress 摘要"""
    from core.gateway.goal_state import create_goal, goal_context_injection, update_goal_progress

    create_goal("u1", "sess_ctx", "写文档", plan=["草稿", "定稿"])
    update_goal_progress("u1", "sess_ctx", done=1, total=2, turn_id=9)
    txt = goal_context_injection("u1", "sess_ctx")
    assert "目标进度：1/2（50%）" in txt, txt
    assert "当前目标（G6 持久化）：写文档" in txt


def test_compat_old_apis(tmp_path):
    """P1 兼容: create_goal/get_goal/update_goal_status/complete_goal 签名与行为不变"""
    from core.gateway.goal_state import GOAL_STATUS, complete_goal, create_goal, get_goal, update_goal_status

    g = create_goal("u9", "sess_c", "旧接口目标", plan=["s"])
    assert get_goal("u9", "sess_c")["goal_id"] == g["goal_id"]
    u = update_goal_status("u9", "sess_c", "paused", note="老板暂停")
    assert u["status"] == "paused" and u["note"] == "老板暂停"
    assert get_goal("u9", "sess_c")["status"] == "paused"
    assert complete_goal("u9", "sess_c")["status"] == "complete"
    assert "active" in GOAL_STATUS and "archived" in GOAL_STATUS
    assert update_goal_status("u9", "sess_c", "bogus") is None


def test_exec_turn_end_goal_association():
    """P1 源码级: execute_agent_task 的 _write_exec_turn_end 也关联 goal"""
    src = open("core/gateway/execute_agent_task.py", encoding="utf-8").read()
    assert "get_goal_by_session_id(_sid)" in src, "exec 路径应定位 goal"
    assert "progress_delta" in src and "complete_goal" in src
    # bridge 路径 turn_end 事件应带 goal_id
    src2 = open("core/gateway/turn_protocol.py", encoding="utf-8").read()  # P3-A: _write_turn_end 已归位
    assert "_goal_info" in src2 and "progress_delta" in src2
