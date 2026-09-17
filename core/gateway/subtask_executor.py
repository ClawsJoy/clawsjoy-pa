"""任务3: 子任务并发执行器（参照 V10 run.py + Manus 可视化）

- 有界并发: 全局 ThreadPoolExecutor(max_workers=3)
- 每子任务独立沙箱目录 + git 基线（task_spec.md 初始 commit）
- 审计合格后自动归档（git log 快照 + move 到 archive/subtasks/{task_id}），
  失败保留现场不清理
- 状态 dict per-session 加锁（前端轮询可视化）
"""
import threading
import time
import json
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# 有界并发池（任务3: 2-3 并发上限）
_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="subtask")
_subtask_lock = threading.Lock()
# {user:session -> {task_id -> entry}}
_subtasks = {}
_STATUS = ("queued", "running", "done", "failed")

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
        return _subtasks.setdefault(key, {})


def _persist_state(user_id, session_id):
    """把该 session 的 _subtasks(含 depth) 落盘到 .agent_state.json 的 subtasks 字段

    委托深度预算持久化: 重启后 depth 不丢(审计/追踪可见); 文件锁防并发写。
    """
    try:
        import fcntl as _fcntl
        _st_file = Path("data/projects") / user_id / session_id / ".agent_state.json"
        _st_file.parent.mkdir(parents=True, exist_ok=True)
        with open(_st_file, "a+", encoding="utf-8") as _f:
            _fcntl.flock(_f.fileno(), _fcntl.LOCK_EX)
            try:
                _f.seek(0)
                _raw = _f.read()
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
                    }
            _f.seek(0)
            _f.truncate()
            _f.write(json.dumps(_data, ensure_ascii=False, indent=2))
            _f.flush()
            _fcntl.flock(_f.fileno(), _fcntl.LOCK_UN)
    except Exception:
        pass  # 落盘失败不阻断子任务执行


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
    }
    with _subtask_lock:
        st[task_id] = entry
    _persist_state(user_id, session_id)
    _executor.submit(_run, user_id, session_id, task_id, task_spec, model)
    return task_id


def list_subtasks(user_id, session_id):
    """返回该 session 全部子任务状态（加锁快照，供前端轮询）"""
    st = _state(user_id, session_id)
    with _subtask_lock:
        return [dict(v) for v in sorted(st.values(), key=lambda e: e.get("created_at", 0))]


def _git(cmd, cwd):
    subprocess.run(["git"] + cmd, cwd=str(cwd), capture_output=True, timeout=30)


def _run(user_id, session_id, task_id, task_spec, model):
    entry = _state(user_id, session_id)[task_id]
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

        _execute_agent_task(
            user_id, session_id,
            _sub_messages,
            model, task_id, sub_task_id=task_id,
            on_done=_on_done, on_fail=_on_fail, sandbox_base=sub_dir,
            parent_goal_id=_parent_goal_id,
        )

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


def _archive(user_id, session_id, task_id, sub_dir, entry):
    """归档前保留 git log 快照，move 到 archive/subtasks/{task_id}"""
    snapshot = {"task_id": task_id, "ts": time.time(), "git_log": ""}
    try:
        r = subprocess.run(["git", "log", "--oneline", "-n", "30"], cwd=str(sub_dir),
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
