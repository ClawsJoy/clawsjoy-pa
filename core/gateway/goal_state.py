"""#101 G6: 目标跨轮次持久化 — goal 生命周期（created/active/paused/complete）+ P1 增强

Harness create_goal 语义落地到 V9：
- .agent_state.json 增加 goal 字段（goal_id/objective/status/plan[]/started_at/updated_at）
- P1: Goal 实体新增 progress{}/history[]/source_turn/session_id/user_id
- P1: 权威存储 data/projects/{uid}/{sid}/clawsjoy_dev/goals/{goal_id}.json(独立文件)
      + SessionLog goal_event 事件双写(审计/回放)
- P1: 新增 update_goal_progress / get_goal_by_id / list_goals / archive_goal
- 任务开始时创建/激活 goal，完成时置 complete，重启后从磁盘恢复注入上下文
"""
import json
import time
import threading
from pathlib import Path
from datetime import datetime

# 内存态：user_id:session_id → goal dict（避免每次读写磁盘）
_goals = {}
_goal_lock = threading.Lock()
_goal_id_seq = 0   # P1: goal_id 单调序号(同秒/同毫秒创建防碰撞)

GOAL_STATUS = ("active", "paused", "complete", "failed", "archived")

# P1: goals 文件扫描根(测试可 monkeypatch 到 tmp)
_GOALS_ROOT = Path("data/projects")


def _state_file(user_id, session_id):
    return Path(f"data/projects/{user_id}/{session_id}/clawsjoy_dev/.agent_state.json")


def _load_state(user_id, session_id):
    try:
        f = _state_file(user_id, session_id)
        if f.exists() and f.read_text(encoding="utf-8").strip():
            return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_state(user_id, session_id, state):
    try:
        # 批221 修（DS-206-3 指认：本处原为**非原子直写** f.write_text ⇒ 与其它写者并发交错 ⇒
        # 两份 JSON 串接 ⇒ Extra data 损坏）。切到统一原子出口：按路径锁 + tmp + os.replace + 容错读。
        from core.gateway.state_json import update_json
        update_json(_state_file(user_id, session_id), lambda _d: (_d.clear(), _d.update(state)))
    except Exception as e:
        print(f"[GOAL_STATE] 落盘失败: {e}")


# ===== P1: 独立 goal 文件(权威层) =====

def _goal_dir(user_id, session_id):
    return _GOALS_ROOT / user_id / session_id / "clawsjoy_dev" / "goals"


def _goal_file(user_id, session_id, goal_id):
    return _goal_dir(user_id, session_id) / f"{goal_id}.json"


def _save_goal_file(goal):
    """权威存储: goals/{goal_id}.json(goal 内带 user_id/session_id 定位目录)"""
    uid = goal.get("user_id")
    sid = goal.get("session_id")
    if not uid or not sid or not goal.get("goal_id"):
        return
    try:
        f = _goal_file(uid, sid, goal["goal_id"])
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(goal, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[GOAL_STATE] goal 文件落盘失败: {e}")


def _load_goal_file(uid, sid, goal_id):
    try:
        f = _goal_file(uid, sid, goal_id)
        if f.exists() and f.read_text(encoding="utf-8").strip():
            return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None


def _log_goal_event(session_id, goal_id, action, payload=None):
    """P1: 写 SessionLog goal_event(审计/回放; 失败静默降级)"""
    try:
        from core.gateway.session_log import log_event
        _pl = {"goal_id": goal_id, "action": action}
        if payload:
            _pl.update(payload)
        log_event(session_id, "goal_event", _pl)
    except Exception:
        pass


def _persist_goal(user_id, session_id, goal, action, ev_payload=None):
    """P1 双写: goals 独立文件 + .agent_state.json(兼容旧读取) + SessionLog goal_event"""
    _save_goal_file(goal)
    _state = _load_state(user_id, session_id)
    _state["goal"] = goal
    _save_state(user_id, session_id, _state)
    _log_goal_event(session_id, goal.get("goal_id"), action, ev_payload)


def _new_goal_fields(goal, user_id, session_id, plan=None):
    """P1: 补齐 Goal 新字段(旧格式兼容; 已有值不动)"""
    goal.setdefault("progress", {"done": 0, "total": len(plan or []) or 1, "completed_steps": [], "pct": 0})
    goal.setdefault("history", [])
    goal.setdefault("source_turn", None)
    goal.setdefault("session_id", session_id)
    goal.setdefault("user_id", user_id)
    return goal


# ===== 已有接口(签名兼容) =====

def create_goal(user_id, session_id, objective, plan=None, task_id=None):
    """创建或刷新 active goal。

    目标隔离修复(2026-08-29): 旧逻辑"复用 active goal 并覆盖 objective"导致同一 session
    长期复用后多个任务目标互相污染(Agent 跑新任务却延续旧任务思维, 简单任务永不收敛)。
    新逻辑: 存在 active goal 且 objective 不同 → 先归档旧 goal(archived), 再建新 goal,
    保证每个新任务独立目标, 不残留旧目标上下文。
    """
    with _goal_lock:
        existing = _goals.get(f"{user_id}:{session_id}")
        now = time.time()
        _is_new_objective = existing is not None and str(existing.get("objective", ""))[:50] != str(objective or "")[:50]
        if existing and existing.get("status") == "active" and not _is_new_objective:
            # 同目标(续跑/重复) → 复用刷新
            existing = _new_goal_fields(existing, user_id, session_id, plan)
            existing["objective"] = objective[:300]
            existing["updated_at"] = now
            if plan:
                existing["plan"] = plan
            _goals[f"{user_id}:{session_id}"] = existing
            goal = existing
        else:
            # 新目标(或旧 goal 非 active) → 归档旧 active, 建新 goal(目标隔离)
            if existing and existing.get("status") == "active":
                existing["status"] = "archived"
                existing["updated_at"] = now
                existing.setdefault("note", "")
                existing["note"] = f"被新目标替换: {str(objective or '')[:60]}"
                _goals[f"{user_id}:{session_id}"] = existing
                try:
                    _persist_goal(user_id, session_id, existing, "status", {"status": "archived"})
                except Exception:
                    pass
            global _goal_id_seq
            _goal_id_seq += 1
            goal = _new_goal_fields({
                "goal_id": f"goal_{user_id}_{int(now * 1000)}_{_goal_id_seq}",
                "objective": objective[:300],
                "status": "active",
                "plan": plan or [],
                "task_id": task_id,
                "started_at": now,
                "updated_at": now,
            }, user_id, session_id, plan)
            _goals[f"{user_id}:{session_id}"] = goal
    # P1 双写: 独立文件 + .agent_state.json + goal_event
    _persist_goal(user_id, session_id, goal, "created",
                  {"objective": str(goal.get("objective", ""))[:200], "status": "active"})
    # R1 落盘检索编目：goal 注册进 SAG（DB 不可用时静默降级）
    try:
        from core.lib.sag_audit_bridge import register_entity
        register_entity("goal", str(goal.get("objective", ""))[:200], f"status={goal.get('status')}", str(session_id), [str(user_id), str(goal.get("goal_id", ""))])
    except Exception:
        pass
    return goal


def get_goal(user_id, session_id):
    """读取当前 goal（优先内存，其次磁盘恢复）"""
    key = f"{user_id}:{session_id}"
    with _goal_lock:
        if key in _goals:
            return _goals[key]
    # 磁盘恢复（重启后）: .agent_state.json → goals 独立文件
    _state = _load_state(user_id, session_id)
    goal = _state.get("goal")
    if goal and isinstance(goal, dict):
        goal = _new_goal_fields(goal, user_id, session_id)
        with _goal_lock:
            _goals[key] = goal
        return goal
    with _goal_lock:
        for g in _goals.values():
            if g.get("session_id") == session_id and g.get("user_id") == user_id:
                return g
    return None


def update_goal_status(user_id, session_id, status, note=None, report=None):
    """更新 goal 状态（complete/paused/failed/archived），并持久化

    report: 任务最终报告(LLM 总结/tool_steps 摘要)写入 goal 记录 —
    供 /v9/goal/history 跨设备/换浏览器恢复; 旧 goal 无该字段时前端按空处理。
    """
    if status not in GOAL_STATUS:
        return None
    key = f"{user_id}:{session_id}"
    with _goal_lock:
        goal = _goals.get(key)
    if goal is None:
        goal = get_goal(user_id, session_id)
    if goal is None:
        return None
    goal["status"] = status
    goal["updated_at"] = time.time()
    if note:
        goal["note"] = note[:300]
    if report:
        goal["report"] = str(report)[:8000]
    with _goal_lock:
        _goals[key] = goal
    # P1 双写 + 事件
    _persist_goal(user_id, session_id, goal, "status", {"status": status})
    return goal


def goal_context_injection(user_id, session_id, last_user_msg=""):
    """重启/新请求时生成 goal 恢复注入文本（供 v9_agent_chat 注入 system 消息）

    W3 修复(2026-08-30): 不限于 active goal — 用户"继续"深挖任务时 goal 可能被
    中途取消/新消息置为非 active, 但 objective 仍应注入(否则 Agent 丢失任务上下文,
    退化到"任务目标只有一句 hi")。active 全量注入; 非 active 注入"最近目标(可能已中断)"。
    """
    goal = get_goal(user_id, session_id)
    if not goal:
        return ""
    _active = goal.get("status") == "active"
    _status_label = goal.get("status", "active") if _active else "非active(最近目标, 可能已中断/被替换)"
    parts = [f"[系统] 当前目标（G6 持久化）：{goal.get('objective', '')[:200]}"]
    parts.append(f"目标状态：{_status_label}")
    # P1: 注入 progress 摘要
    _p = goal.get("progress") or {}
    if _p.get("total"):
        parts.append(f"目标进度：{_p.get('done', 0)}/{_p.get('total', 1)}（{_p.get('pct', 0)}%）")
    plan = goal.get("plan") or []
    if plan:
        plan_txt = "；".join(str(p)[:80] for p in plan[:8])
        parts.append(f"已确认计划：{plan_txt}")
    if goal.get("started_at"):
        parts.append(f"开始时间：{datetime.fromtimestamp(goal['started_at']).strftime('%m-%d %H:%M')}")
    return "\n".join(parts)


def complete_goal(user_id, session_id, report=None):
    """任务完成 → goal 置 complete（幂等）; report 为最终报告(可空)"""
    return update_goal_status(user_id, session_id, "complete", report=report)


def update_goal_report(user_id, session_id, report):
    """持久化任务报告(最终或阶段性, 如 max_tokens 摘要)到 goal 记录, 不改变状态。

    幂等: 同一 turn 多次调用只保留最新; 空报告直接跳过。
    """
    report = str(report or "").strip()[:8000]
    if not report:
        return None
    key = f"{user_id}:{session_id}"
    with _goal_lock:
        goal = _goals.get(key)
    if goal is None:
        goal = get_goal(user_id, session_id)
    if goal is None:
        return None
    goal["report"] = report
    goal["updated_at"] = time.time()
    with _goal_lock:
        _goals[key] = goal
    _persist_goal(user_id, session_id, goal, "report", {"report_len": len(report)})
    return goal


def cleanup_inactive_goals(max_age=86400 * 3):
    """清理过期非 active goal（3 天）"""
    now = time.time()
    with _goal_lock:
        for key, g in list(_goals.items()):
            if g.get("status") not in ("active",) and now - g.get("updated_at", 0) > max_age:
                _goals.pop(key, None)


# ===== P1 新增接口 =====

def update_goal_progress(user_id, session_id, done=None, total=None, step=None, turn_id=None):
    """P1: 更新 goal progress(done 绝对值/total 绝对值; step 记入 completed_steps; turn_id 记入 history+source_turn)。

    双写落盘 + goal_event("progress")。返回更新后 goal 或 None。
    """
    key = f"{user_id}:{session_id}"
    with _goal_lock:
        goal = _goals.get(key)
    if goal is None:
        goal = get_goal(user_id, session_id)
    if goal is None:
        return None
    _p = goal.setdefault("progress", {"done": 0, "total": 1, "completed_steps": [], "pct": 0})
    _prev_done = int(_p.get("done", 0) or 0)
    if done is not None:
        _p["done"] = max(0, int(done))
    if total is not None:
        _p["total"] = max(1, int(total))
    if step:
        _s = str(step)[:120]
        if _s not in _p.setdefault("completed_steps", []):
            _p["completed_steps"].append(_s)
    _t = int(_p.get("total", 1) or 1)
    _p["pct"] = max(0, min(100, int(round(_p.get("done", 0) * 100 / _t))))
    goal.setdefault("history", []).append({
        "ts": time.time(),
        "delta": f"done {_prev_done}->{_p.get('done', 0)}" + (f" [{step}]" if step else ""),
        "turn_id": turn_id,
    })
    if turn_id is not None:
        goal["source_turn"] = turn_id
    goal["updated_at"] = time.time()
    with _goal_lock:
        _goals[key] = goal
    _persist_goal(user_id, session_id, goal, "progress",
                  {"done": _p.get("done"), "total": _t, "pct": _p.get("pct")})
    return goal


def get_goal_by_id(goal_id):
    """P1: 跨 session 按 goal_id 读取(内存优先, 兜底扫 data/projects/*/*/clawsjoy_dev/goals/*.json)"""
    if not goal_id:
        return None
    with _goal_lock:
        for g in _goals.values():
            if g.get("goal_id") == goal_id:
                return g
    for f in _GOALS_ROOT.glob("*/*/clawsjoy_dev/goals/*.json"):
        try:
            g = json.loads(f.read_text(encoding="utf-8"))
            if g.get("goal_id") == goal_id:
                return g
        except Exception:
            pass
    return None


def list_goals(user_id, status=None, limit=20):
    """P1: 用户级目标列表(内存 + 该用户 goals 目录), 按 updated_at 倒序"""
    goals = []
    seen = set()
    with _goal_lock:
        for key, g in _goals.items():
            if key.startswith(f"{user_id}:") and g.get("goal_id") not in seen:
                goals.append(g)
                seen.add(g.get("goal_id"))
    _udir = _GOALS_ROOT / user_id
    try:
        for f in _udir.glob("*/clawsjoy_dev/goals/*.json"):
            try:
                g = json.loads(f.read_text(encoding="utf-8"))
                if g.get("goal_id") not in seen:
                    goals.append(g)
                    seen.add(g.get("goal_id"))
            except Exception:
                pass
    except Exception:
        pass
    if status:
        goals = [g for g in goals if g.get("status") == status]
    goals.sort(key=lambda g: g.get("updated_at", 0), reverse=True)
    return goals[:limit]


def archive_goal(user_id, session_id):
    """P1: complete 后归档 — 状态置 archived, 文件保留并移到 goals/archive/"""
    key = f"{user_id}:{session_id}"
    with _goal_lock:
        goal = _goals.get(key)
    if goal is None:
        goal = get_goal(user_id, session_id)
    if goal is None:
        return None
    goal["status"] = "archived"
    goal["updated_at"] = time.time()
    with _goal_lock:
        _goals[key] = goal
    _persist_goal(user_id, session_id, goal, "archived")
    # 文件保留: 移到 goals/archive/{goal_id}.json
    try:
        _src = _goal_file(user_id, session_id, goal["goal_id"])
        _dst = _goal_dir(user_id, session_id) / "archive" / f"{goal['goal_id']}.json"
        if _src.exists():
            _dst.parent.mkdir(parents=True, exist_ok=True)
            _src.rename(_dst)
    except Exception:
        pass
    return goal


def get_goal_by_session_id(session_id):
    """P1 内部: 按 session_id 定位当前 goal(供 turn_end 关联; 内存主查, 兜底扫文件)"""
    if not session_id:
        return None
    with _goal_lock:
        for key, g in _goals.items():
            if key.endswith(f":{session_id}"):
                return g
    try:
        for f in _GOALS_ROOT.glob("*/*/clawsjoy_dev/goals/*.json"):
            try:
                g = json.loads(f.read_text(encoding="utf-8"))
                if g.get("session_id") == session_id:
                    return g
            except Exception:
                pass
    except Exception:
        pass
    return None
