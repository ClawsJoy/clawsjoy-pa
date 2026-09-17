"""query_index 工具插件（#238 + #241 + 熔断恢复）"""

import time
import warnings

from core.gateway.shared_state import _query_melt_cache
from core.tools.base import ToolPlugin


class QueryIndexPlugin(ToolPlugin):
    name = "query_index"
    quota = 10

    def execute(self, args: dict, ctx) -> dict:
        _code_indexer = ctx.code_indexer
        messages = ctx.messages
        user_id = ctx.user_id
        session_id = ctx.session_id
        _query_empty_cache = ctx.query_empty_cache

        # #SAG 统计：query_index 调用时 filter_net.json total_queries + 1（H-json污染防护：原子写，避免并发截断清空）
        try:
            import json as _json_fn
            import tempfile as _tmp_fn

            _fn_path = Path("core/lib/filter_net.json")
            if _fn_path.exists():
                _fn_data = _json_fn.loads(_fn_path.read_text(encoding="utf-8"))
                if not isinstance(_fn_data, dict):
                    _fn_data = {"version": 1, "rules": [], "stats": {}}
            else:
                _fn_data = {"version": 1, "rules": [], "stats": {}}
            _fn_stats = _fn_data.setdefault("stats", {})
            _fn_stats["total_queries"] = _fn_stats.get("total_queries", 0) + 1
            # 原子写：写临时文件再替换，避免 "w" 先截断后 dump 失败导致清空
            _fd, _tmp_path = _tmp_fn.mkstemp(dir=str(_fn_path.parent), suffix=".tmp")
            with open(_tmp_path, "w", encoding="utf-8") as _f:
                _json_fn.dump(_fn_data, _f, ensure_ascii=False, indent=2)
            import os as _os_fn

            _os_fn.replace(_tmp_path, _fn_path)
        except Exception:
            try:
                import os as _os_fn2

                _os_fn2.unlink(_tmp_path)
            except Exception:
                pass
        import re as _re
        import warnings

        warnings.filterwarnings("ignore", category=SyntaxWarning)
        query = args.get("query", "")
        # R1 P1b 统一检索入口：entity_type 参数 → 查 SAG 非代码实体（审计/越权/快照/goal/manual）
        _entity_type = args.get("entity_type", "") or ""
        if _entity_type:
            try:
                from core.lib.sag_audit_bridge import query_entities

                _sag_rows = query_entities(entity_type=_entity_type, query=query or None, limit=args.get("limit", 20))
                if not _sag_rows:
                    return {
                        "success": True,
                        "query": query,
                        "entity_type": _entity_type,
                        "results": [],
                        "source": "sag",
                    }
                _results = [
                    {
                        "entity_type": r.get("entity_type", ""),
                        "entity_name": r.get("entity_name", ""),
                        "signature": r.get("signature", ""),
                        "file_path": r.get("file_path", ""),
                        "related": r.get("related_entities", []),
                    }
                    for r in _sag_rows
                ]
                return {
                    "success": True,
                    "query": query,
                    "entity_type": _entity_type,
                    "results": _results,
                    "source": "sag",
                }
            except Exception as _sag_err:
                return {"success": False, "error": f"SAG 检索失败: {_sag_err}"}
        if _code_indexer is None or not _code_indexer._keyword_index:
            return {"success": False, "error": "代码索引尚未初始化"}
        # 关键词匹配
        results = []
        query_lower = query.lower()
        for filepath, keywords in _code_indexer._keyword_index.items():
            match_score = 0
            for kw in keywords:
                if kw.lower() in query_lower or query_lower in kw.lower():
                    match_score += 1
            if match_score > 0:
                # 获取 AST 解析结果
                blocks = _code_indexer.parse_file(filepath)
                results.append(
                    {
                        "file": "clawsjoy_dev/" + filepath,
                        "keywords": keywords,
                        "match_score": match_score,
                        "blocks": blocks[:20],
                    }
                )
        # #81 过滤网自学习：query_index 侧按 code_edges.weight 加权排序（使用越频繁节点越靠前）
        try:
            from core.lib.code_entity_extractor import extractor as _edge_ext_q

            _edge_rows_q = _edge_ext_q.get_edges(entity_name=None, project_id="default", limit=5000)
            _edge_weight_q = {}
            for _r_edge in _edge_rows_q:
                for _k_edge in ("target_name", "source_name"):
                    _n_edge = str(_r_edge.get(_k_edge, "") or "")
                    if _n_edge:
                        _w_edge = float(_r_edge.get("weight") or 0.0)
                        _edge_weight_q[_n_edge] = max(_edge_weight_q.get(_n_edge, 0.0), _w_edge)
                        _base_q = _n_edge.split("/")[-1]
                        if _base_q and len(_base_q) > 3:
                            _edge_weight_q[_base_q] = max(_edge_weight_q.get(_base_q, 0.0), _w_edge)
            for _res_q in results:
                _f_q = str(_res_q.get("file", ""))
                _res_q["sag_weight"] = max(
                    _edge_weight_q.get(_f_q, 0.0),
                    _edge_weight_q.get(_f_q.replace("clawsjoy_dev/", ""), 0.0),
                    _edge_weight_q.get(str(_f_q).split("/")[-1], 0.0),
                )
        except Exception:
            for _res_q in results:
                _res_q["sag_weight"] = 0.0
        results.sort(key=lambda x: (x["sag_weight"], x["match_score"]), reverse=True)
        _qkey_melt = f"melt_{session_id}_{query}"
        _melt_count = _query_melt_cache.get(_qkey_melt, 0)
        _has_any_score = any(r.get("match_score", 0) > 0 for r in results)
        # #SAG 统计：本次查询返回结果 → successful_retrievals +1，返回空 → ignored_retrievals +1
        try:
            import json as _json_fn2

            _fn_path2 = "core/lib/filter_net.json"
            _fn_data2 = _json_fn2.load(open(_fn_path2, encoding="utf-8"))
            _fn_stats2 = _fn_data2.setdefault("stats", {})
            if results:
                _fn_stats2["successful_retrievals"] = _fn_stats2.get("successful_retrievals", 0) + 1
            else:
                _fn_stats2["ignored_retrievals"] = _fn_stats2.get("ignored_retrievals", 0) + 1
            _json_fn2.dump(_fn_data2, open(_fn_path2, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        except Exception:
            pass
        # #SAG 注入：检测同一 query 连续 3 次返回空 → 停止搜索，强制换方式
        _qkey_empty = f"empty_{session_id}_{query}"
        # 熔断恢复：5分钟后自动重置计数
        _ts_key = f"{_qkey_empty}_ts"
        if _ts_key in _query_empty_cache and time.time() - _query_empty_cache[_ts_key] > 300:
            _query_empty_cache[_qkey_empty] = 0
            del _query_empty_cache[_ts_key]
        if not results:
            _empty_count = _query_empty_cache.get(_qkey_empty, 0) + 1
            _query_empty_cache[_qkey_empty] = _empty_count
            _query_empty_cache[_ts_key] = time.time()
            if _empty_count >= 3:
                return {
                    "success": True,
                    "query": query,
                    "results": [],
                    "empty_repeat": True,
                    "hint": "同一 query 连续 3 次返回空，已熔断。请换一种方式（改用 read_file 分段扫描目标文件）",
                }
            # P1 检索熔断降级：熔断前"还剩 N 次"预警
            return {
                "success": True,
                "query": query,
                "results": [],
                "empty_repeat": False,
                "hint": f"同一 query 连续 {_empty_count} 次返回空，还剩 {3 - _empty_count} 次后熔断；建议改用 read_file 的 search 参数或分段扫描。",
            }
        else:
            _query_empty_cache[_qkey_empty] = 0
            _query_empty_cache[_ts_key] = time.time()
