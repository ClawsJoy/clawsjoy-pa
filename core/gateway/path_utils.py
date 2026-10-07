"""路径工具模块 — 从 agent_gateway_enhanced.py 抽取"""

import logging
from pathlib import Path
from core.lib.gateway_helpers import _get_sandbox_base

logger = logging.getLogger(__name__)

def _resolve_main_repo(user_id, session_id):
    """定位正本仓库根：模块在正本则返回自身，在沙箱副本则向上找正本 git 根"""
    try:
        _mod_dir = Path(__file__).resolve().parent
        _here_repo = None
        for _p in [_mod_dir] + list(_mod_dir.parents):
            if (_p / ".git").exists():
                _here_repo = _p
                break
        if _here_repo is None:
            return None
        if "data/projects" not in _here_repo.as_posix():
            return _here_repo
        # 模块在沙箱副本（data/projects 之下）：向上找正本 git 根
        for _p in _here_repo.parents:
            if (_p / ".git").exists():
                return _p
    except Exception:
        pass
    return None



def _extract_tool_path(args, tool_name=None):
    """从工具参数中提取路径标识，供递归检测使用(递归 canonicalize = 工具名 + 完整参数)。

    递归精准化:
    - browser_local(tool_name 显式传入): key 含 action — 同 URL 不同 action 不共用计数
      (navigate(X) / search(X) / extract(X) / click(X) 各自独立计数, 修复 URL 级误伤)
    - execute_command: 取完整 command 前缀 100 字符 — echo "A" 与 echo "B" 是不同命令
    - read_file/list_dir 等: 取完整 path(已有)
    - 网络工具(fetch_web/browse_web/playwright_browser): URL 作为递归标识
    """
    if not isinstance(args, dict):
        return "<no-path>"
    # browser_local: 递归 key 含 action(同 URL 不同 action 不共用计数)
    if tool_name == "browser_local":
        _act = str(args.get("action") or "")
        _url = str(args.get("url") or "").strip()
        _sel = str(args.get("selector") or "").strip()
        _scope = _url or _sel
        # evaluate 修复: expression 前 50 字符作为递归标识 —
        # 不同探测脚本共用 'browser_local:evaluate' 会被误判为同一路径重复(递归计数误伤)
        # 字段兼容: expression / code / expr(Agent 实际用 expr, 2026-08-29 现场确认)
        if _act == "evaluate":
            # B5(2026-08-30): 函数探针(箭头函数/function 开头)共享前 50 字符(如 (() => { const progress...
            # 会被误判为同一路径重复 → 追加 expression 短 hash(不同探针 hash 不同, 同探针重复仍累计)
            _expr_full = str(args.get("expression") or args.get("code") or args.get("expr") or "").strip()
            if not _expr_full:
                return "browser_local:evaluate"
            _expr = _expr_full[:50]
            _is_probe = _expr_full.startswith("(() =>") or _expr_full.startswith("function(") or _expr_full.startswith("(function") or _expr_full.startswith("async ")
            if _is_probe:
                try:
                    import hashlib as _hl
                    _h = _hl.md5(_expr_full.encode("utf-8")).hexdigest()[:8]
                    return "browser_local:evaluate:%s:%s" % (_expr, _h)
                except Exception:
                    pass
            return "browser_local:evaluate:%s" % _expr
        # extract 同理: expr 字段参与递归 key(不同探测不共用)
        if _act in ("extract", "click", "fill"):
            _expr2 = str(args.get("expr") or args.get("selector") or args.get("text") or "").strip()[:50]
            return "browser_local:%s:%s" % (_act, _expr2) if _expr2 else "browser_local:%s" % _act
        return ("browser_local:%s:%s" % (_act, _scope)) if _scope else ("browser_local:%s" % _act)
    for key in ("path", "file_path", "target", "filename", "file"):
        val = args.get(key)
        if val:
            return str(val)
    # 网络工具(fetch_web/browse_web/playwright_browser): URL 作为递归标识 —
    # 不同 URL 各自计数, 避免全部落在 "<no-path>" 上被误判为同一路径重复
    url = args.get("url")
    if url:
        return str(url).strip()
    # web_search(2026-08-30): query 作为递归标识 — 不同搜索词各自计数,
    # 避免所有 web_search 落在 "<no-path>" 被误判递归(日志: 5 次搜索即触发暂停)
    _q = args.get("query")
    if _q:
        return "web_search:" + str(_q).strip()[:100]
    # obsidian_knowledge(2026-08-31): action + 目标 作为递归标识 —
    # 原全部落在 "<no-path>" → 5 次 obsidian_knowledge 被误判递归循环(日志:
    # "对同一路径 <no-path> 的 obsidian_knowledge 重复操作已达 5 次" → Agent 合法调用被杀 → 反复重试)
    if tool_name == "obsidian_knowledge":
        _act = str(args.get("action") or "").strip()
        _tgt = str(args.get("sop_key") or args.get("query") or args.get("platform") or args.get("title") or args.get("draft_path") or args.get("pitfall") or "").strip()[:100]
        return ("obsidian:" + _act + (":" + _tgt if _tgt else "")) if _act else "obsidian:<unknown>"
    cmd = args.get("command")
    if cmd:
        return str(cmd).strip()[:100]
    return "<no-path>"



def _resolve_path(base, path):
    """路径解析——复用已有的逻辑"""
    path_str = str(path)
    
    # 双重拼接检测：clawsjoy_dev 出现两次 → 调用 _normalize_path 修正
    if path_str.count("clawsjoy_dev/") > 1 or "data/projects/" in path_str:
        # 任务3 修复: 用 data/projects/ 锚点定位 uid/sid（固定 parts[-3]/[-2] 在子任务 base
        # 多 2 层 subtasks/{tid} 时会取错为 clawsjoy_dev/subtasks）
        _base_str = str(base).replace(chr(92), "/")  # Windows: str(Path) 用反斜杠, 统一成正斜杠再解析
        user_id = "default"
        session_id = "default"
        if "data/projects/" in _base_str:
            try:
                _segs = _base_str.split("data/projects/", 1)[1].split("/")
                if len(_segs) >= 2:
                    user_id = _segs[0]
                    session_id = _segs[1]
            except Exception:
                pass
        else:
            _parts = _base_str.split("/")
            user_id = _parts[-3] if len(_parts) >= 3 else "default"
            session_id = _parts[-2] if len(_parts) >= 2 else "default"
        # 子任务独立沙箱: base_override 保证归一化结果落在子任务目录而非共享根
        return _normalize_path(path_str, user_id, session_id, base_override=base)
    
    path_obj = Path(path)
    if path_obj.is_absolute() or str(path).startswith("data/projects/"):
        return path_obj
    project_root = "clawsjoy_dev"
    try:
        state_file = base / ".agent_state.json"
        if state_file.exists():
            import json as _json
            project_root = _json.loads(state_file.read_text(encoding="utf-8")).get("project_root", "clawsjoy_dev")
    except Exception:
        pass
    # #92 修复：base 恒为沙箱根（data/projects/{uid}/{sid}/clawsjoy_dev），
    # 显式 clawsjoy_dev/ 前缀必须先剥离再拼接，否则双重 clawsjoy_dev 导致 ENOENT
    _rel = str(path)
    if _rel == project_root or _rel == f"{project_root}/":
        return base
    if _rel.startswith(f"{project_root}/"):
        _rel = _rel[len(project_root) + 1:]
    # 文件隔离修复: subtask base 下, 路径仍含 subtasks/{tid}(clawsjoy_dev/subtasks/... 或
    # 裸 subtasks/...) → 对齐到 base(剥掉该段防双重嵌套)
    _off_sub = _subtask_offset(base)
    if _off_sub:
        _rel_s = _rel.replace(chr(92), "/")
        _off_marker = _off_sub + "/"
        if _off_marker in _rel_s or _rel_s.endswith(_off_sub):
            _after = _rel_s.split(_off_sub, 1)[1].lstrip("/")
            if _after.startswith("clawsjoy_dev/"):
                _after = _after[len("clawsjoy_dev/"):]
            return base / _after if _after else base
        # 一致性修复: 路径以 subtasks/ 开头但指向 OTHER 子任务(taskAB ≠ taskA) →
        # 与 _normalize_path 的"主沙箱绝对路径保持"对齐, 解析到主沙箱而非拼回 base 双重嵌套。
        # 主沙箱根 = base 去掉 /subtasks/{tid} 段(_resolve_path 无 uid/sid 参数, 从 base 推导)。
        if _rel_s.startswith("subtasks/"):
            _main_base_res = Path(str(base).replace(chr(92), "/").split(_off_sub, 1)[0].rstrip("/"))
            return _main_base_res / _rel_s
    if _rel.startswith(".") or "/" not in _rel:
        return base / _rel
    # 自动补全：相对路径直接拼在沙箱根下（base 已是 clawsjoy_dev）
    return base / _rel
# ===== 异步引擎结束 =====
_query_melt_cache = {}  # 查询循环熔断计数器
_query_empty_cache = {}  # 同一 query 连续返回空计数器


def _subtask_offset(base) -> str:
    """subtask base offset: returns "subtasks/{tid}" when base is .../clawsjoy_dev/subtasks/{tid}, else empty.

    File-isolation fix: in a subtask the LLM often writes paths carrying
    subtasks/{tid} (it learns the dir from the system prompt). If
    _normalize_path only strips the clawsjoy_dev/ prefix, the subtasks/{tid}
    segment survives and is re-joined onto sub_base ->
    subtasks/{tid}/subtasks/{tid} double nesting (file lands in the wrong
    place, though still inside the thread). Separately, when base is already
    a subtask dir, an absolute path pointing at the main sandbox would be
    wrongly redirected INTO the subtask (cross-thread files unreachable).
    """
    try:
        _b = str(base).replace(chr(92), "/")
        _marker = "/clawsjoy_dev/"
        if _marker not in _b:
            return ""
        _after = _b.split(_marker, 1)[1].strip("/")
        if not _after or not _after.startswith("subtasks/"):
            return ""
        return _after  # e.g. "subtasks/taskA"
    except Exception:
        return ""


def _normalize_path(filepath: str, user_id: str, session_id: str, base_override=None) -> Path:
    """规范化路径，自动处理 LLM 的错误双重拼接

    任务3: base_override 可选覆盖（子任务独立沙箱 base，避免归一化回共享沙箱根）
    文件隔离修复: subtask base 下, 含 subtasks/{tid} 的路径对齐到 base(不双重嵌套);
    显式指向主沙箱的绝对路径保持指向主沙箱(不重定向进子任务)。
    """
    base = base_override or _get_sandbox_base(user_id, session_id)
    _off = _subtask_offset(base)  # "" or "subtasks/taskA"
    filepath_str = str(filepath)
    if ".git" in str(filepath).split("/"):
        raise ValueError("禁止操作 .git 目录")
    _fp_norm = filepath_str.replace(chr(92), "/")
    # 0) explicit absolute path to the MAIN sandbox (not this subtask): keep it
    #    pointing at the main sandbox instead of redirecting into the subtask.
    if _off and "/clawsjoy_dev/" in _fp_norm and (_off + "/") not in _fp_norm and not _fp_norm.endswith(_off):
        _main_base = _get_sandbox_base(user_id, session_id)
        _inner = _fp_norm.split("/clawsjoy_dev/", 1)[1]
        return _main_base / _inner
    # 1) 统一处理各种路径格式 → clawsjoy_dev/xxx
    # 处理绝对路径 /home/<user>/.../clawsjoy_dev/xxx
    if "/clawsjoy_dev/" in filepath_str:
        filepath_str = "clawsjoy_dev/" + filepath_str.split("/clawsjoy_dev/", 1)[1]
    # 处理 data/projects/.../clawsjoy_dev/xxx
    elif "data/projects/" in filepath_str and "/clawsjoy_dev/" in filepath_str:
        filepath_str = "clawsjoy_dev/" + filepath_str.split("/clawsjoy_dev/", 1)[1]
    # 处理只有文件名没有前缀的情况
    elif not filepath_str.startswith("clawsjoy_dev/") and not filepath_str.startswith("/"):
        # 如果路径看起来像项目内的文件，自动加前缀
        if "." in filepath_str.split("/")[-1]:
            filepath_str = "clawsjoy_dev/" + filepath_str
    if filepath_str.count("clawsjoy_dev/") > 1:
        parts = filepath_str.split("clawsjoy_dev/")
        filepath_str = "clawsjoy_dev/" + parts[-1]
    elif filepath_str.startswith("data/projects/"):
        parts = filepath_str.split("clawsjoy_dev/")
        if len(parts) > 1:
            filepath_str = "clawsjoy_dev/" + parts[-1]
    # 1.5) subtask offset alignment: strip the subtasks/{tid} segment when the
    #      filepath carries it and base is that same subtask (no double nesting).
    if _off:
        _fp_s = filepath_str.replace(chr(92), "/")
        _off_marker2 = _off + "/"
        if _off_marker2 in _fp_s or _fp_s.endswith(_off):
            _after = _fp_s.split(_off, 1)[1]
            _after = _after.lstrip("/")
            if _after.startswith("clawsjoy_dev/"):
                _after = _after[len("clawsjoy_dev/"):]
            return base / _after
    # 剥掉 clawsjoy_dev/ 前缀，避免 base 和 filepath_str 双重拼接
    if filepath_str == "clawsjoy_dev" or filepath_str == "clawsjoy_dev/":
        filepath_str = ""
    elif filepath_str.startswith("clawsjoy_dev/"):
        filepath_str = filepath_str[len("clawsjoy_dev/"):]
    return base / filepath_str



def _format_path_for_agent(path: str) -> str:
    """统一输出 clawsjoy_dev/xxx 格式的路径给 Agent"""
    if not path:
        return path
    if path.startswith("clawsjoy_dev/") and path.count("clawsjoy_dev/") == 1:
        return path
    if path.count("clawsjoy_dev/") > 1:
        return "clawsjoy_dev/" + path.split("clawsjoy_dev/")[-1]
    if "/clawsjoy_dev/" in path:
        return "clawsjoy_dev/" + path.split("/clawsjoy_dev/", 1)[1]
    if not path.startswith("/") and "clawsjoy_dev/" not in path:
        return "clawsjoy_dev/" + path
    return path


