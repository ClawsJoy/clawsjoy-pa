"""任务3: 子任务并发执行器（参照 V10 run.py + Manus 可视化）

- 有界并发: 全局 ThreadPoolExecutor(max_workers=3)
- 每子任务独立沙箱目录 + git 基线（task_spec.md 初始 commit）
- 审计合格后自动归档（git log 快照 + move 到 archive/subtasks/{task_id}），
  失败保留现场不清理
- 状态 dict per-session 加锁（前端轮询可视化）
"""
import os
import threading
import time
import json
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from core.gateway import _proc as _proc  # ⭐ 窗隐唯一出口（PM 2026-10-05 令 · ⛔ 各写 creationflags）

# 有界并发池（任务3: 2-3 并发上限）
_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="subtask")
_subtask_lock = threading.Lock()
_persist_lock = threading.Lock()  # ⭐ PM 2026-10-04（承 技总 955 §二）：护「读-改-写」文件（⛔ 只护内存 dict）
# {user:session -> {task_id -> entry}}
_subtasks = {}
_STATUS = ("queued", "running", "done", "failed")
# ⭐ T2-刀8 §五（2026-10-05 · PM 裁「准办」）：**池态落盘 ＋ 断点续 ＋ 停止／撤回**
#   ① `_BOOT_ID` ＝ 本进程之身份 ⇒ 水合时辨「**前进程遗留之在途件**」（⛔ 以「内存空」充「未跑」）
#   ② 在途 ⟷ 终态 **分列**（⛔ 抹平）；`cancel` 为**标志**（⛔ 硬杀 · 承面板自陈之界）
_BOOT_ID = "%d-%d" % (int(time.time()), os.getpid())
_INFLIGHT = ("queued", "running")
_TERMINAL = ("done", "failed", "pending", "cancelled", "withdrawn", "interrupted")
_STOP_MODES = ("cancel", "withdraw")

# ===== 委托深度预算(借鉴 Harness delegationDepth) =====
# 预防性加固: 当前无递归委派路径, 加防线防未来子任务内拆子任务导致递归风暴
_DEFAULT_MAX_DEPTH = 3  # 子任务最多 3 层, 第 4 层拒绝


class SubtaskDepthError(Exception):
    """子任务委派深度超限"""
    def __init__(self, depth, max_depth):
        self.depth = depth
        self.max_depth = max_depth
        super().__init__(
            f"subtask depth {depth} exceeds maxDepth {max_depth}，子任务委派深度超限"
        )


def resolve_depth(parent_depth=0):
    """子任务深度 = 父任务深度 + 1(与 Harness childDepth = parentDepth+1 对齐)"""
    try:
        return int(parent_depth or 0) + 1
    except (TypeError, ValueError):
        return 1


def check_depth(depth, max_depth=None):
    """校验深度: 超过 maxDepth 抛 SubtaskDepthError; 返回有效 depth"""
    _cap = max_depth if max_depth is not None else _DEFAULT_MAX_DEPTH
    _d = int(depth or 0)
    if _d > _cap:
        raise SubtaskDepthError(_d, _cap)
    return _d


def _state(user_id, session_id):
    key = f"{user_id}:{session_id}"
    with _subtask_lock:
        # ⭐ PM 2026-10-04（承 技总 954 §二.1）：首次访问即从 .agent_state.json 读回（否则「已落盘」亦丢）
        if key not in _subtasks:
            _subtasks[key] = {}
            try:
                _hyd = Path("data/projects") / user_id / session_id / ".agent_state.json"
                if _hyd.is_file():
                    _hsub = (json.loads(_hyd.read_text(encoding="utf-8")) or {}).get("subtasks") or {}
                    if isinstance(_hsub, dict):
                        for _tid, _ent in _hsub.items():
                            if isinstance(_ent, dict):
                                _subtasks[key][_tid] = dict(_ent)
                                # ⭐ PM 2026-10-04（承 CW 1060 §四.2.⒜）：落盘 map 之键 ⛔ 并回条目 ⇒ 读回后前端落 `?`
                                _subtasks[key][_tid]["task_id"] = _tid
                                # ⭐ T2-刀8 §五：**前进程之在途件** ⇒ 照实记「中断」（⛔ 假 done · ⛔ 静默当空）
                                _e2 = _subtasks[key][_tid]
                                if (_e2.get("status") in _INFLIGHT
                                        and str(_e2.get("boot_id") or "") != _BOOT_ID):
                                    _e2["status"] = "interrupted"
                                    _e2["interrupted_at"] = time.time()
                                    _e2["error"] = ((str(_e2.get("error") or "")
                                                     + " | 进程中断（boot 变更 ⇒ 前进程未收口）⇒ 照实记「未完成」·"
                                                       " ⛔ 假 done · ⛔ 自动重跑（须 POST /v9/subtask/resume）").strip(" |"))
            except Exception as _he:
                print("[SUBTASK_HYDRATE] 读回失败（⛔ 静默）：%s: %s" % (type(_he).__name__, _he))
        return _subtasks.setdefault(key, {})


def _persist_state(user_id, session_id):
    """把该 session 的 _subtasks(含深度/状态/因) 落盘到 .agent_state.json 之 subtasks 字段

    ⭐ PM 2026-10-04（承 技总 954 §二.1 ＋ 955 §二）：① 跨平台（Windows ⛔ `fcntl` ⇒ 原为静默空转之根因）
    ② 原子写（`tmp` ＋ `os.replace` ⇒ 读者 ⛔ 撞半写 ⇒ 免「全池凭空消失」）
    ③ 进程内锁（护读-改-写）④ 失败印一行（⛔ 静默）
    """
    _st_file = Path("data/projects") / user_id / session_id / ".agent_state.json"
    try:
        with _persist_lock:
            _st_file.parent.mkdir(parents=True, exist_ok=True)
            _data = {}
            if _st_file.is_file():
                try:
                    _raw = _st_file.read_text(encoding="utf-8")
                    _data = json.loads(_raw) if _raw.strip() else {}
                except Exception:
                    _data = {}
            if not isinstance(_data, dict):
                _data = {}
            _sub_map = _data.get("subtasks")
            if not isinstance(_sub_map, dict):
                _sub_map = {}
                _data["subtasks"] = _sub_map
            st = _state(user_id, session_id)
            with _subtask_lock:
                for _tid, _e in st.items():
                    _sub_map[_tid] = {
                        "status": _e.get("status", "queued"),
                        "depth": _e.get("depth", 0),
                        "created_at": _e.get("created_at"),
                        "error": _e.get("error"),
                        "finished_at": _e.get("finished_at"),
                        "spec": _e.get("spec"),   # ⭐ PM 2026-10-04（承 CW 1060 §四.2.⒝）：前端引 `spec`（⛔ `task_spec`）⇒ 须落
                        "result": _e.get("result"),
                        # ⭐ T2-刀8 §五：**在途/停止/中断**之键（⛔ 落则重启后无从辨）
                        "boot_id": _e.get("boot_id"),
                        "cancel": bool(_e.get("cancel")),
                        "cancel_at": _e.get("cancel_at"),
                        "stop_mode": _e.get("stop_mode"),
                        "stop_by": _e.get("stop_by"),
                        "stop_reason": _e.get("stop_reason"),
                        "pending_stop": bool(_e.get("pending_stop")),
                        "interrupted_at": _e.get("interrupted_at"),
                        "resumed_at": _e.get("resumed_at"),
                        "resume_n": _e.get("resume_n"),
                    }
            _tmp = _st_file.with_name(_st_file.name + ".tmp")
            _tmp.write_text(json.dumps(_data, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(str(_tmp), str(_st_file))
    except Exception as _e:  # ⭐ PM 2026-10-04：⛔ 静默（原 pass 吞一切 ⇒ 表面「重启即空」）
        print("[SUBTASK_PERSIST] 落盘失败（⛔ 静默）：%s: %s" % (type(_e).__name__, _e))


def _record_dispatch(user_id, session_id, task_id, status, objective, error=None, depth=None,
                     to_seat=None, stage=None):
    """池路派发记录（承 技总 955 §三：形复用 `DispatchRecord` · ⛔ 新造）
    ⭐ 池路另补四键：user_id ／ session_id ／ depth ／ source（⛔ `verdict` ／ `reasons` —— 此路无「审」⇒ ⛔ 塞假值）
    ⭐ 2026-10-05（T2-刀1 ②）：**只增** `to_seat` ／ `stage`（初值 `queued`）—— ⛔ 删旧键。
    """
    try:
        from core.pa.dispatch import DispatchRecord

        row = {
            "task_id": task_id,
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "objective": str(objective or "")[:200],
            "user_id": user_id,
            "session_id": session_id,
            "depth": depth,
            "status": status,
            "source": "subtask_pool",
            "to_seat": to_seat,
            "stage": (stage or status or "queued"),
        }
        if error:
            row["error"] = str(error)[:300]
        DispatchRecord().add(row)
    except Exception as _e:
        print("[SUBTASK_DISPATCH] 派发记录写入失败（⛔ 静默）：%s: %s" % (type(_e).__name__, _e))


def submit(user_id, session_id, task_spec, model="deepseek-v4-flash", depth=0, max_depth=None):
    """提交子任务到有界线程池，返回 task_id

    委托深度预算(预防性加固): depth 超过 maxDepth(默认 3) 抛 SubtaskDepthError。
    depth 持久化到 .agent_state.json(重启不丢)。
    """
    _d = check_depth(depth, max_depth)
    st = _state(user_id, session_id)
    task_id = "sub_%d_%d" % (int(time.time() * 1000), len(st) + 1)
    entry = {
        "task_id": task_id, "status": "queued", "spec": task_spec[:200],
        "created_at": time.time(), "started_at": None, "finished_at": None,
        "result": "", "error": "", "archived_path": "", "git_log": "",
        "depth": _d,  # 委托深度(持久化)
        "boot_id": _BOOT_ID, "cancel": False, "pending_stop": False,  # ⭐ T2-刀8 §五
    }
    with _subtask_lock:
        st[task_id] = entry
    _persist_state(user_id, session_id)
    _record_dispatch(user_id, session_id, task_id, "queued", task_spec, depth=_d)  # ⭐ 写点一（承 955 §三）
    _executor.submit(_run, user_id, session_id, task_id, task_spec, model)
    return task_id


def list_subtasks(user_id, session_id):
    """返回该 session 全部子任务状态（加锁快照，供前端轮询）"""
    st = _state(user_id, session_id)
    with _subtask_lock:
        return [dict(v) for v in sorted(st.values(), key=lambda e: e.get("created_at", 0))]


def _git(cmd, cwd):
    _proc.run_hidden(["git"] + cmd, cwd=str(cwd), capture_output=True, timeout=30)


def _run(user_id, session_id, task_id, task_spec, model):
    entry = _state(user_id, session_id)[task_id]
    entry["boot_id"] = _BOOT_ID   # ⭐ T2-刀8 §五：本件之 boot（水合时据此辨「前进程遗留」）
    # ⭐ T2-刀8 §五：**置标志**之收口（⛔ 硬杀 ⇒ 于安全点收口 · 承面板自陈之界）
    if entry.get("cancel") or entry.get("status") in ("cancelled", "withdrawn"):
        entry["status"] = ("withdrawn" if str(entry.get("stop_mode")) == "withdraw" else "cancelled")
        entry["finished_at"] = entry.get("finished_at") or time.time()
        _persist_state(user_id, session_id)
        _record_dispatch(user_id, session_id, task_id, entry["status"], entry.get("spec"),
                         error="置标志后未起跑 ⇒ %s" % entry["status"], depth=entry.get("depth"))
        return
    entry["status"] = "running"
    entry["started_at"] = time.time()
    # ===== 审批隔离声明(借鉴 Harness: 子代理 approval 固定 'never') =====
    # 子任务写操作不经主任务 bridge_loop 锚点A 审批——安全写直接执行、越权写
    # 由锚点B确定性拒绝(不弹审批)。执行前清 _pending_writes[sub_session] 防残留审批态。
    # #76 反依赖解耦: 从 V9Context 容器取清理服务(不 import agent_gateway_enhanced, 防循环依赖)
    try:
        from core.os.context import get_v9_context
        _pw_cleaner = get_v9_context().get_opt("pending_writes_cleaner")
        if _pw_cleaner is not None:
            _sub_sess = f"{session_id}_{task_id}"  # 子任务独立会话 key(与主任务隔离)
            _pw_cleaner(_sub_sess)
    except Exception:
        pass
    sub_dir = None
    try:
        # 1) 独立沙箱: data/projects/{uid}/{sid}/clawsjoy_dev/subtasks/{task_id}/
        base = Path("data/projects") / user_id / session_id / "clawsjoy_dev"
        sub_dir = base / "subtasks" / task_id
        sub_dir.mkdir(parents=True, exist_ok=True)
        spec_path = sub_dir / "task_spec.md"
        spec_path.write_text("# 子任务 " + task_id + "\n\n" + task_spec + "\n", encoding="utf-8")
        # 2) git 基线: init + 初始 commit（task_spec.md 后立即提交）
        _git(["init"], sub_dir)
        _git(["add", "."], sub_dir)
        _git(["commit", "-m", "subtask baseline: " + task_id], sub_dir)

        # 3) 执行: 复用 _execute_agent_task（sandbox_base 指向独立目录 + sub_task_id 隔离状态）
        from core.gateway.execute_agent_task import _execute_agent_task
        # #4 子代理继承: 父任务 goal_id + 简要上下文(前 200 字), 不继承完整 messages(安全隔离)
        _parent_goal_id = None
        _sub_messages = [
            {"role": "system", "content":
             "你是 ClawsJoy 的子任务执行 Agent。你的工作目录是当前沙箱根目录（'.'），工具调用时写相对路径即可，"
             "例如 write_file(path='result.md')。**不要**在路径前加 subtasks/ 或任何前缀——"
             "subtasks/ 是父级共享目录，写它会落到错误的嵌套位置。完成子任务并调用工具写入产出文件，完成标准由任务描述定义。"},
            {"role": "user", "content": task_spec},
        ]
        try:
            from core.gateway.goal_state import get_goal_by_session_id
            _pg = get_goal_by_session_id(session_id)
            if _pg and _pg.get("goal_id"):
                _parent_goal_id = _pg.get("goal_id")
                _inherit_ctx = (f"[系统] 继承父任务目标：{str(_pg.get('objective', ''))[:200]}"
                                f"（goal_id={_parent_goal_id}）。请围绕该目标完成子任务。")
                _sub_messages.insert(0, {"role": "system", "content": _inherit_ctx})
        except Exception:
            pass
        _done_box = {}

        def _on_done(tid, uid, sid, output):
            _done_box["output"] = output or ""

        def _on_fail(tid, uid, sid, reason):
            _done_box["error"] = reason or "任务失败"
            # ⭐ PM 2026-10-04（承 技总 957 §三 ⒜）：待审（`WRITE_PENDING`）⛔ 当 `failed`
            _rs = str(reason or "")
            if ("WRITE_PENDING" in _rs) or ("待审批" in _rs) or ("写入待审" in _rs):
                _done_box["pending"] = True

        _execute_agent_task(
            user_id, session_id,
            _sub_messages,
            model, task_id, sub_task_id=task_id,
            on_done=_on_done, on_fail=_on_fail, sandbox_base=sub_dir,
            parent_goal_id=_parent_goal_id,
        )

        # ⭐ T2-刀8 §五：起跑后置标志 ⇒ 收口为 cancelled（⛔ 归档 · ⛔ 冒 done）
        if entry.get("cancel"):
            entry["status"] = ("withdrawn" if str(entry.get("stop_mode")) == "withdraw" else "cancelled")
            entry["finished_at"] = time.time()
            entry["error"] = ((str(entry.get("error") or "")
                               + " | 置标志后收口（⛔ 硬杀 · 承面板自陈之界）").strip(" |"))
            return
        if _done_box.get("pending"):
            # ⭐ PM 2026-10-04：照实落「待审」态（⛔ 假 `failed`）
            entry["status"] = "pending"
            entry["error"] = _done_box.get("error", "")[:500]
            entry["finished_at"] = time.time()
            return
        if _done_box.get("error"):
            entry["status"] = "failed"
            entry["error"] = _done_box["error"][:500]
            entry["finished_at"] = time.time()
            # 失败保留现场：不归档不清理
            return

        # 4) 审计合格（_execute_agent_task 内部 _save_state 已做 H8 防假完成复核）→ 归档
        entry["result"] = _done_box.get("output", "")[:500]
        _archive(user_id, session_id, task_id, sub_dir, entry)
        entry["status"] = "done"
        entry["finished_at"] = time.time()
    except Exception as _e:
        entry["status"] = "failed"
        entry["error"] = str(_e)[:500]
        entry["finished_at"] = time.time()
        # 失败保留现场
    finally:
        # ⭐ PM 2026-10-04（承 技总 955 §四）：终态须落盘（原唯 `submit` 一处 ⇒ 磁盘恒 `queued`）
        #   并与池路派发记录**同点**（一行补 ⇒ 两病同销）
        try:
            _persist_state(user_id, session_id)
            _record_dispatch(user_id, session_id, task_id, entry.get("status"), entry.get("spec"),
                             error=entry.get("error"), depth=entry.get("depth"))
        except Exception as _fe:
            print("[SUBTASK_FINAL] 终态落盘/记录失败（⛔ 静默）：%s: %s" % (type(_fe).__name__, _fe))


# ============================== ⭐ T2-刀8 §五：停止 ／ 撤回 ／ 断点续 ==============================
def stop(user_id, session_id, task_id, mode="cancel", by="", reason=""):
    """**置标志**之停止／撤回（⛔ 硬杀 —— 承面板自陈之界）。

    · `queued`（未起跑）⇒ 态**即转**（`cancelled` ／ `withdrawn`）；`_run` 起跑前见标志即收口。
    · `running`（已起跑）⇒ **唯置标志**（`cancel=True` ＋ `pending_stop=True`），态**仍 `running`**
      —— 由 `_run` 于**安全点**收口（⛔ 谎称已停 · ⛔ 中途硬杀）。
    · 终态 ⇒ **拒**（⛔ 撤回终态 · 承「删除须归因」）。
    """
    m = str(mode or "cancel").strip()
    if m not in _STOP_MODES:
        return {"ok": False, "error": "mode 须 ∈ %s（收 %r）" % ("／".join(_STOP_MODES), m)}
    st = _state(user_id, session_id)
    with _subtask_lock:
        e = st.get(str(task_id))
        if e is None:
            return {"ok": False, "error": "⛔ 无此 task_id（该 session 之池）：%s" % task_id}
        frm = str(e.get("status") or "queued")
        if frm not in _INFLIGHT:
            return {"ok": False, "error": "**已终态**（%s）⇒ ⛔ 撤回（承「删除须归因」）" % frm}
        e["cancel"] = True
        e["cancel_at"] = time.time()
        e["stop_mode"] = m
        e["stop_by"] = str(by or "")
        e["stop_reason"] = str(reason or "")
        if frm == "queued":
            e["status"] = ("withdrawn" if m == "withdraw" else "cancelled")
            e["finished_at"] = time.time()
            applied = True
        else:
            e["pending_stop"] = True
            applied = False
        to = str(e.get("status"))
    _persist_state(user_id, session_id)
    _record_dispatch(user_id, session_id, task_id, to, st.get(str(task_id), {}).get("spec"),
                     error="stop mode=%s by=%s" % (m, by), depth=st.get(str(task_id), {}).get("depth"))
    return {"ok": True, "task_id": str(task_id), "mode": m, "from": frm, "to": to,
            "置标志": True, "硬杀": False, "即时生效": applied,
            "注": ("未起跑 ⇒ 态即转" if applied else
                   "已起跑 ⇒ 唯置标志，态仍 %s；由 _run 于安全点收口（⛔ 谎称已停）" % to)}


def _full_spec(user_id, session_id, task_id):
    """全规格之真源 ＝ 沙箱 `task_spec.md`（池内 `spec` **唯前 200 字** ⇒ ⛔ 充全量）。"""
    p = Path("data/projects") / user_id / session_id / "clawsjoy_dev" / "subtasks" / task_id / "task_spec.md"
    if not p.is_file():
        return None
    try:
        t = p.read_text(encoding="utf-8")
    except Exception:
        return None
    head = "# 子任务 " + task_id + "\n\n"
    return t[len(head):].rstrip("\n") if t.startswith(head) else t


def resume(user_id, session_id, task_id=None, model="deepseek-v4-flash"):
    """**断点续**：把 `interrupted`（或前进程遗留之在途）件**重投**池。

    ⚠ **只续有「全规格」者** —— 池内 `spec` 唯前 `200` 字 ⇒ ⛔ 以截断之规格充全量（照实拒续）。
    """
    st = _state(user_id, session_id)
    tids = [str(task_id)] if task_id else [t for t, e in sorted(st.items())
                                           if str(e.get("status")) in ("interrupted",)]
    done, blocked = [], []
    for t in tids:
        with _subtask_lock:
            e = st.get(t)
            if e is None:
                blocked.append({"task_id": t, "why": "⛔ 无此 task_id"})
                continue
            # ⭐ T2-刀8 §五 收口（2026-10-05）：态验**无条件**
            #   ⚠ 旧形 `... and not task_id:` ⇒ 给了 `task_id` 即**跳过**态验
            #     ⇒ `running`／`done`（有全规格者）可被**重投**（终态被绕）
            if str(e.get("status")) not in ("interrupted",):
                blocked.append({"task_id": t, "why": "态 %s ⇒ ⛔ 续（唯 interrupted）" % e.get("status")})
                continue
        spec = _full_spec(user_id, session_id, t)
        if not spec:
            blocked.append({"task_id": t, "why": "⛔ **缺全规格**（沙箱 task_spec.md 缺 · 池内 spec 唯前 200 字 ⇒ ⛔ 充全量）"})
            continue
        with _subtask_lock:
            e["status"] = "queued"
            e["cancel"] = False
            e["pending_stop"] = False
            e["error"] = ""
            e["finished_at"] = None
            e["resumed_at"] = time.time()
            e["resume_n"] = int(e.get("resume_n") or 0) + 1
            e["boot_id"] = _BOOT_ID
        _persist_state(user_id, session_id)
        _record_dispatch(user_id, session_id, t, "queued", spec, depth=e.get("depth"))
        _executor.submit(_run, user_id, session_id, t, spec, model)
        done.append(t)
    return {"ok": True, "resumed": done, "blocked": blocked,
            "counts": {"resumed": len(done), "blocked": len(blocked)}}


def _archive(user_id, session_id, task_id, sub_dir, entry):
    """归档前保留 git log 快照，move 到 archive/subtasks/{task_id}"""
    snapshot = {"task_id": task_id, "ts": time.time(), "git_log": ""}
    try:
        r = _proc.run_hidden(["git", "log", "--oneline", "-n", "30"], cwd=str(sub_dir),
                           capture_output=True, timeout=30)
        snapshot["git_log"] = r.stdout.decode("utf-8", "ignore").strip()
        entry["git_log"] = snapshot["git_log"][:500]
        (sub_dir / "git_log_snapshot.json").write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as _e:
        snapshot["snapshot_error"] = str(_e)
    try:
        archive_dir = Path("data/projects") / user_id / session_id / "clawsjoy_dev" / "archive" / "subtasks"
        archive_dir.mkdir(parents=True, exist_ok=True)
        archived = archive_dir / task_id
        if sub_dir.exists():
            shutil.move(str(sub_dir), str(archived))
            entry["archived_path"] = str(archived)
    except Exception as _e:
        entry["error"] = (entry.get("error") or "") + ("; 归档失败: " + str(_e))
