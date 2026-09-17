"""文件工具插件 — 合并 list_dir + search_files"""

from core.tools.base import ToolPlugin


class ListDirPlugin(ToolPlugin):
    name = "list_dir"
    quota = 3  # list_dir 配额限制为 3 次

    def execute(self, args: dict, ctx) -> dict:
        base = ctx.base
        target = ctx.resolve_path(base, args.get("path", "."))
        # P0 沙箱路径映射: 只读回退项目根(桥接路径与 HTTP 同规)
        _read_source = "sandbox"
        if not target.exists():
            try:
                from core.lib.gateway_helpers import _resolve_project_root_read
                _fb = _resolve_project_root_read(str(args.get("path", ".")), target, getattr(ctx, "user_id", ""), getattr(ctx, "session_id", ""))
                if _fb is not None and _fb.exists():
                    target = _fb
                    _read_source = "project_root"
            except Exception:
                pass
        if not target.exists():
            return {"success": True, "files": [], "dirs": [], "source": _read_source, "hint": "目录不存在"}
        files = [p.name for p in target.iterdir() if p.is_file()][:20]
        dirs = [p.name for p in target.iterdir() if p.is_dir()]
        return {"success": True, "files": files, "dirs": dirs, "source": _read_source}

    def validate(self, args: dict) -> bool:
        return True


class SearchFilesPlugin(ToolPlugin):
    name = "search_files"
    quota = 5

    def execute(self, args: dict, ctx) -> dict:
        base = ctx.base
        path = ctx.resolve_path(base, args.get("path", "clawsjoy_dev"))
        # P0 沙箱路径映射: 只读回退项目根(桥接路径与 HTTP 同规)
        _read_source = "sandbox"
        if not path.exists():
            try:
                from core.lib.gateway_helpers import _resolve_project_root_read
                _fb = _resolve_project_root_read(str(args.get("path", "clawsjoy_dev")), path, getattr(ctx, "user_id", ""), getattr(ctx, "session_id", ""))
                if _fb is not None and _fb.exists():
                    path = _fb
                    _read_source = "project_root"
            except Exception:
                pass
        query = args.get("query", "").lower()
        hits = []
        if path.exists():
            for p in path.rglob("*"):
                if p.is_file():
                    try:
                        rel = str(p.relative_to(base)).lower()
                    except Exception:
                        rel = str(p).lower()
                    if not query or query in rel or query in p.name:
                        hits.append(rel)
                if len(hits) >= 20:
                    break
        # P1 检索熔断降级：连续空结果 → 预警 + 熔断强制降级（对齐 HTTP 路径 #192）
        _sid = getattr(ctx, "session_id", "") or ""
        _empty_cache = getattr(ctx, "search_empty_cache", None)
        if _sid and _empty_cache is not None:
            if not hits:
                _n = _empty_cache.get(_sid, 0) + 1
                _empty_cache[_sid] = _n
                if _n >= 3:
                    return {
                        "success": True, "results": [], "melted": True,
                        "hint": "search_files 连续 3 次空结果，已熔断。请改用 list_dir 或 read_file 分段扫描目标目录。",
                    }
                return {
                    "success": True, "results": hits, "melted": False,
                    "hint": f"search_files 连续 {_n} 次空结果，还剩 {3 - _n} 次后熔断；建议改用 list_dir 或 read_file 定向读取。",
                }
            else:
                _empty_cache[_sid] = 0
        return {"success": True, "results": hits, "source": _read_source}

    def validate(self, args: dict) -> bool:
        return True
