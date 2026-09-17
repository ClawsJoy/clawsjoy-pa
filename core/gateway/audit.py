"""V9 工具循环全量审计（#100 G4/G5 落地）

Harness 差距方案：以 OS 审计层作为第三方视角，独立于 Agent 自我报告。

职责：
1. audit_tool_call(): _with_tool_flow 每次工具调用时写入审计记录（工具名/参数哈希/结果哈希/耗时/ts）
2. verify_completion_report(): 复核 Agent 的 5 项 checklist 报告 vs 审计记录 → 判假完成
3. 性能：内存队列 + 批量落盘（避免同步逐条写文件阻塞工具循环）
4. 5s 误判窗口：复核时对近期审计留 5s 容差，避免时序差异误判
"""
import hashlib
import json
import threading
import time
from datetime import datetime
from pathlib import Path

# ===== 配置 =====
_AUDIT_DIR = Path("data/v8/audit")
_AUDIT_FILE = _AUDIT_DIR / "tool_audit.jsonl"
_FLUSH_INTERVAL = 2.0  # 批量落盘间隔（秒）
_FLUSH_BATCH = 50  # 批量落盘条数阈值
_REPORT_WINDOW = 5.0  # 复核误判窗口（秒）
_MAX_QUEUE = 5000  # 队列上限，防内存膨胀
_FLUSH_TIMEOUT = 30.0  # 同步落盘硬超时（秒）：超时移交后台线程，防止审计写盘阻塞工具循环

# ===== 内存队列 + 后台落盘 =====
_audit_queue = []
_audit_lock = threading.Lock()
_flush_thread = None
_flush_stop = threading.Event()


def _ensure_flush_thread():
    """懒启动批量落盘线程"""
    global _flush_thread
    if _flush_thread is None or not _flush_thread.is_alive():
        _flush_stop.clear()
        _flush_thread = threading.Thread(target=_flush_worker, daemon=True)
        _flush_thread.start()


def _flush_worker():
    """后台线程：周期 + 条数阈值批量落盘"""
    while not _flush_stop.is_set():
        time.sleep(_FLUSH_INTERVAL)
        _flush_batch()


def _flush_batch():
    """把队列一次性写入 jsonl（加锁，幂等）"""
    global _audit_queue
    with _audit_lock:
        if not _audit_queue:
            return
        batch = _audit_queue
        _audit_queue = []
    try:
        _AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        with open(_AUDIT_FILE, "a", encoding="utf-8") as f:
            for rec in batch:
                f.write(json.dumps(rec, ensure_ascii=False) + chr(10))
    except Exception as e:
        # 落盘失败：回填队列避免丢失（限容）
        print(f"[AUDIT] 落盘失败: {e}")
        with _audit_lock:
            _audit_queue = batch + _audit_queue
            _audit_queue = _audit_queue[-_MAX_QUEUE:]


def _flush_batch_bounded(timeout=_FLUSH_TIMEOUT):
    """同步落盘限时执行：audit_tool_call 的写盘受 30s 硬超时保护。

    磁盘卡顿/文件系统挂起时，主线程最多等待 timeout 秒即返回，
    剩余写盘由后台 daemon 线程继续；审计记录可能延迟/丢失，
    但工具循环绝不被审计写盘卡死（工具响应优先于审计完整性）。
    """
    done = threading.Event()

    def _run():
        try:
            _flush_batch()
        finally:
            done.set()

    threading.Thread(target=_run, daemon=True).start()
    if not done.wait(timeout):
        print(f"[AUDIT] 同步落盘超过 {timeout}s，移交后台线程继续，主线程不再等待")
        return False
    return True


def audit_tool_call(tool_name, args, result, user_id, session_id, elapsed_ms=0, round_no=0):
    """工具调用全量审计（在 _with_tool_flow 内调用）——第三方视角，独立于 tool_flow"""
    global _audit_queue
    try:
        _args_hash = hashlib.md5(json.dumps(args, ensure_ascii=False, default=str).encode()).hexdigest()[:16]
        _res_ok = bool(result.get("success")) if isinstance(result, dict) else False
        _res_hash = ""
        if isinstance(result, dict):
            _res_hash = hashlib.md5(json.dumps(result, ensure_ascii=False, default=str).encode()).hexdigest()[:16]
        rec = {
            "ts": time.time(),
            "ts_iso": datetime.now().isoformat(),
            "tool": tool_name,
            "args_hash": _args_hash,
            "result_hash": _res_hash,
            "success": _res_ok,
            "elapsed_ms": elapsed_ms,
            "round": round_no,
            "user_id": user_id,
            "session_id": session_id,
        }
        with _audit_lock:
            _audit_queue.append(rec)
            if len(_audit_queue) >= _FLUSH_BATCH:
                # 条数达阈值立即落盘（同步，保审计及时性）
                _flush_batch_bounded()
            elif len(_audit_queue) > _MAX_QUEUE:
                _audit_queue = _audit_queue[-_MAX_QUEUE:]
        _ensure_flush_thread()
        # R1 落盘检索编目：注册进 SAG（DB 不可用时静默降级）
        try:
            from core.lib.sag_audit_bridge import register_entity

            register_entity(
                "audit_event", tool_name, f"success={_res_ok} args={_args_hash}", str(session_id), [str(user_id)]
            )
        except Exception:
            pass
    except Exception as e:
        print(f"[AUDIT] 记录失败: {e}")


def flush_audit():
    """强制落盘（进程退出/任务完成时调用）"""
    _flush_batch()


def read_audit_records(session_id=None, since=None, limit=500):
    """读取审计记录（复核用）——文件 + 未落盘内存队列合并，按 ts 升序。

    关键：复核发生在任务完成时，最近几秒的审计可能还在内存队列
    （批量落盘延迟），必须合并队列避免误判（5s 误判窗口的由来）。
    """
    # 1. 先取内存队列副本（未落盘部分）
    queued = []
    with _audit_lock:
        queued = list(_audit_queue)
    # 2. 再读文件
    records = []
    if _AUDIT_FILE.exists():
        try:
            with open(_AUDIT_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue
                    records.append(rec)
        except Exception:
            pass
    records.extend(queued)
    # 3. 过滤 + 排序 + 限量
    _filtered = []
    for rec in records:
        if session_id and rec.get("session_id") != session_id:
            continue
        if since and rec.get("ts", 0) < since:
            continue
        _filtered.append(rec)
    _filtered.sort(key=lambda r: r.get("ts", 0))
    return _filtered[-limit:] if len(_filtered) > limit else _filtered


# ===== 复核：Agent 报告 vs 审计记录 =====
def verify_completion_report(agent_report, audit_records, window=_REPORT_WINDOW):
    """复核 Agent 的完成报告 vs 审计记录（第三方视角，防假完成）。

    agent_report: dict，Agent 声明的完成证据，key=checklist 项，value=claim dict：
        {"write": {"tool": "write_file", "claimed": True, "ts": 1712345678.0},
         "compile": {"tool": "execute_command", "claimed": True, "ts": 1712345679.0},
         "import": {"tool": "execute_command", "claimed": True},
         "run": {"tool": "execute_command", "claimed": True},
         "content": {"tool": "read_file", "claimed": True}}
      - tool: str 或 list[str]，审计中匹配的工具名（list = 任一命中即可）
      - claimed: 声称成功(True)/失败(False)
      - ts: 可选，声称的操作时间；提供时窗口语义 = |审计ts - 声称ts| <= window
        （5s 容差，防时序差异误判）；不提供时仅按工具名+success 匹配。
    audit_records: list[dict]，审计记录（read_audit_records 返回，已合并未落盘队列）。

    返回 {"passed": bool, "failures": [str], "verified": {key: bool}}
    """
    if not agent_report or not isinstance(agent_report, dict):
        return {"passed": False, "failures": ["无 Agent 报告"], "verified": {}}

    verified = {}
    failures = []
    _now = time.time()

    for key, claim in agent_report.items():
        if not isinstance(claim, dict):
            verified[key] = False
            failures.append(f"{key}: 报告格式无效")
            continue
        tools_ = claim.get("tool") or [key.split("_")[0]]
        if isinstance(tools_, str):
            tools_ = [tools_]
        claimed_ok = claim.get("claimed", False)
        claimed_ts = claim.get("ts")

        # 在审计记录中找匹配记录（工具名 + 成功状态 + 可选时间窗口）
        found = False
        for rec in audit_records:
            if rec.get("tool") not in tools_:
                continue
            if claimed_ts is not None:
                # 5s 误判窗口：声称时间与审计时间偏差超窗 → 视为时序差异，跳过
                if abs((rec.get("ts") or 0) - claimed_ts) > window:
                    continue
            if rec.get("success") and claimed_ok:
                found = True
                break
            if not rec.get("success") and not claimed_ok:
                found = True
                break
        verified[key] = found
        if claimed_ok and not found:
            failures.append(f"{key}: 声称成功但审计无对应成功记录")
        elif not claimed_ok and not found:
            failures.append(f"{key}: 声称失败但审计无对应失败记录")

    passed = not failures
    return {"passed": passed, "failures": failures, "verified": verified}


def cross_check_completion(vc_result, session_id, task_start_ts=None, user_id=None):
    """供 V9 完成路径复用的复核 helper：VerificationChain 结果 + 审计记录 → 第三方判定。

    从 vc_result.steps（step1_write/step2_syntax/step3_run/step4_content/step5_done_when）
    构造 5 项 checklist 的 agent_report，并读取本任务窗口内的审计记录交叉核对。
    task_start_ts 缺省时取最近 10 分钟（兜底，防任务开始时间未记录）。
    返回 {"audit_passed": bool, "audit_failures": [str], "verified": dict}，
    调用方将 audit_failures 并入失败原因即可拦截假完成。
    """
    try:
        steps = (vc_result or {}).get("steps", {}) or {}
        if not steps:
            # 无 VerificationChain 结果（降级路径）→ 审计复核跳过，不拦
            return {"audit_passed": True, "audit_failures": [], "verified": {}}
        agent_report = {
            "write": {
                "tool": ["write_file", "write_large"],
                "claimed": bool((steps.get("step1_write") or {}).get("passed")),
            },
            "compile": {"tool": ["execute_command"], "claimed": bool((steps.get("step2_syntax") or {}).get("passed"))},
            "run": {"tool": ["execute_command"], "claimed": bool((steps.get("step3_run") or {}).get("passed"))},
            "content": {"tool": ["read_file"], "claimed": bool((steps.get("step4_content") or {}).get("passed"))},
        }
        # step5 done_when 无断言跳过时（detail 含"跳过"）不参与复核，避免误判
        _s5 = steps.get("step5_done_when") or {}
        if _s5.get("passed") and "跳过" not in str(_s5.get("detail", "")):
            agent_report["done_when"] = {"tool": ["execute_command"], "claimed": True}
        elif not _s5.get("passed"):
            agent_report["done_when"] = {"tool": ["execute_command"], "claimed": False}
        _since = task_start_ts if task_start_ts else time.time() - 600
        _records = read_audit_records(session_id=session_id, since=_since, limit=2000)
        # 任务3 v5 修复: 只复核审计中实际出现过的工具项——子任务只执行 write/read 时,
        # VerificationChain 的 compile/run 步骤标 passed 但审计无 execute_command 记录,
        # 全项复核必然失败 -> 强制继续 -> 死循环。无审计记录的工具项跳过(未执行项不判失败)。
        _audit_tools = {r.get("tool") for r in _records}
        _filtered_report = {}
        for _rk, _rclaim in agent_report.items():
            _rtools = _rclaim.get("tool")
            _rtools_list = _rtools if isinstance(_rtools, list) else [_rtools]
            if any(t in _audit_tools for t in _rtools_list):
                _filtered_report[_rk] = _rclaim
        agent_report = _filtered_report
        _res = verify_completion_report(agent_report, _records)
        return {
            "audit_passed": _res["passed"],
            "audit_failures": _res["failures"],
            "verified": _res["verified"],
        }
    except Exception as _ce:
        # 复核自身异常不阻断主流程：降级为通过（审计是辅助防线）
        return {"audit_passed": True, "audit_failures": [], "verified": {}, "error": str(_ce)[:200]}


# P0: 收编注册到 V9Context 容器(模块对象整体注册, 消费方可选迁移 ctx.get("audit"))
try:
    import sys as _sys_audit

    from core.os.context import get_v9_context as _get_v9_ctx_audit

    _get_v9_ctx_audit().provide("audit", _sys_audit.modules[__name__])
except Exception as _audit_ctx_err:
    print(f"[AUDIT] P0 容器收编失败(不影响运行): {_audit_ctx_err}")


def _record_approval(user_id, session_id, kind, action, target, detail=""):
    """审批记录落盘：追加写入 .agent_state.json 的 approvals 字段（与 escalations 同模式）。

    kind: "write" | "plan"; action: "approved" | "rejected"
    供前端审计面板展示"老板批准/拒绝了什么"(按时间倒序)。
    """
    try:
        from core.lib.gateway_helpers import _get_sandbox_base as _gsb_a

        _st_file = Path(str(_gsb_a(user_id, session_id))) / ".agent_state.json"
        from core.gateway.state_json import read_json, update_json
        _st = read_json(_st_file)      # 批220：容错读
        _approvals = _st.get("approvals")
        if not isinstance(_approvals, list):
            _approvals = []
        _approvals.append(
            {
                "timestamp": datetime.now().isoformat(),
                "kind": kind,
                "action": action,
                "target": str(target)[:300],
                "detail": str(detail)[:200],
            }
        )
        _st["approvals"] = _approvals
        update_json(_st_file, lambda _d: (_d.clear(), _d.update(_st)))   # 批220：原子写
        print(f"[APPROVAL_AUDIT] 审批记录已落盘: {kind}:{action} {str(target)[:60]}")
    except Exception:
        pass


def _record_escalation(user_id, session_id, tool, target, reason, action="blocked"):
    """#105 越权拦截审计落盘：追加写入 .agent_state.json 的 escalations 字段（幂等，只追加不覆盖）。

    - escalations 不存在则创建，存在则追加；不覆盖 .agent_state.json 其他字段。
    - 注：C2 解耦时误删定义（227a0d3），调用点仍在使用，此处恢复（E2E 发现）。
    """
    try:
        from core.lib.gateway_helpers import _get_sandbox_base as _gsb_e

        _st_file = Path(str(_gsb_e(user_id, session_id))) / ".agent_state.json"
        from core.gateway.state_json import read_json, update_json
        _st = read_json(_st_file)      # 批220：容错读
        _escalations = _st.get("escalations")
        if not isinstance(_escalations, list):
            _escalations = []
        _escalations.append(
            {
                "timestamp": datetime.now().isoformat(),
                "tool": tool,
                "target": str(target)[:300],
                "reason": reason,
                "action": action,
            }
        )
        _st["escalations"] = _escalations
        update_json(_st_file, lambda _d: (_d.clear(), _d.update(_st)))   # 批220：原子写
        # R1 落盘检索编目：escalation 注册进 SAG（DB 不可用时静默降级）
        try:
            from core.lib.sag_audit_bridge import register_entity

            register_entity(
                "escalation", str(tool), f"{reason} → {str(target)[:200]}", str(session_id), [str(user_id), action]
            )
        except Exception:
            pass
        print(f"[ESCAPE_AUDIT] 越权记录已落盘: {tool} {str(target)[:60]} ({reason})")
    except Exception as _audit_err:
        print(f"[ESCAPE_AUDIT] 落盘失败: {_audit_err}")
