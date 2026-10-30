"""状态持久化模块 — 从 agent_gateway_enhanced.py 抽取"""

import logging
import json
from pathlib import Path
from core.gateway.shared_state import (
    retrieval_cache_file,
    _query_cache,
    _retry_cache,
    _search_empty_cache,
)

logger = logging.getLogger(__name__)

def _safe_serialize_state(state: dict) -> str:
    """安全序列化 state，逐字段隔离，定位崩溃字段"""
    import json as _json, re as _re
    
    for key, value in state.items():
        try:
            _json.dumps({key: value}, ensure_ascii=False)
        except Exception as e:
            logger.info(f"[V9] 崩溃字段: {key}, 错误: {e}, 类型: {type(value).__name__}, 前80字符: {str(value)[:80]!r}")
    
    safe_state = {}
    for key, value in state.items():
        if isinstance(value, str):
            s = value
            s = _re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', s)
            max_len = 200 if key == 'last_task' else 2000 if '.content' in key else 10000 if key == 'world_model' else 500
            safe_state[key] = s[:max_len]
        elif isinstance(value, dict):
            if key == 'world_model':
                safe_state[key] = value
            else:
                _serialized = json.dumps(value, ensure_ascii=False, default=str)
                safe_state[key] = (_serialized[:10000] + "...<TRUNCATED>") if len(_serialized) > 10000 else _serialized
        elif isinstance(value, list):
            clean_list = []
            for v in value[:10]:
                if isinstance(v, dict):
                    clean_list.append({k: str(v2)[:200] if isinstance(v2, str) else v2 for k, v2 in v.items()})
                elif isinstance(v, str):
                    clean_list.append(v[:500])
                else:
                    clean_list.append(v)
            safe_state[key] = clean_list
        elif isinstance(value, (int, float, bool, type(None))):
            safe_state[key] = value
        else:
            _serialized = json.dumps(value, ensure_ascii=False, default=str)
            safe_state[key] = (_serialized[:10000] + "...<TRUNCATED>") if len(_serialized) > 10000 else _serialized
    
    try:
        return _json.dumps(safe_state, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.info(f"[V9] 最终序列化失败: {e}，使用 repr 兜底")
        fallback = {k: repr(v) if not isinstance(v, (str, int, float, bool, type(None))) else v for k, v in safe_state.items()}
        return _json.dumps(fallback, ensure_ascii=False, indent=2)


def _persist_state(state: dict, state_file: Path) -> bool:
    """持久化 state 到文件，内部做完整异常处理和诊断日志。

    批221 修（DS-206-3 指认：本处原为**非原子直写** ⇒ 多写者交错 ⇒ Extra data 损坏）：
    统一走 core.gateway.state_json.update_json（按路径锁 + tmp + os.replace + 容错读）。
    """
    try:
        from core.gateway.state_json import update_json as _uj_sp
        _uj_sp(state_file, lambda _d: (_d.clear(), _d.update(state)))
        return True
    except Exception as e:
        logger.info(f"[V9] 状态持久化失败: {e}, 异常类型: {type(e).__name__}")
        import json as _json, traceback
        traceback.print_exc()
        for k, v in state.items():
            if isinstance(v, str):
                try:
                    _json.dumps({k: v}, ensure_ascii=False)
                except Exception as _je:
                    logger.info(f"[V9] 崩溃字段: {k}, 错误: {_je}, 前100字符: {v[:100]!r}")
                    break
        return False


def _persist_retrieval_cache():
    """检索缓存落盘：{session_id: {query_cache, empty_cache, retry_cache}}"""
    try:
        from pathlib import Path as _Path
        import json as _json
        _cache_file = _Path(retrieval_cache_file())
        _cache_file.parent.mkdir(parents=True, exist_ok=True)
        _data = {}
        _all_sids = set(_query_cache) | set(_search_empty_cache) | set(_retry_cache)
        for _sid in _all_sids:
            _data[str(_sid)] = {
                "query_cache": _query_cache.get(_sid, {}),
                "empty_cache": _search_empty_cache.get(_sid, 0),
                "retry_cache": _retry_cache.get(_sid, {}),
            }
        _tmp = _cache_file.with_suffix(".json.tmp")
        with open(_tmp, "w", encoding="utf-8") as _f:
            _json.dump(_data, _f, ensure_ascii=False, indent=2, default=str)
        _tmp.replace(_cache_file)
        logger.info(f"[RETRIEVAL_CACHE] 检索缓存已落盘 -> {_cache_file} ({len(_data)} sessions)")
    except Exception as _e:
        logger.info(f"[RETRIEVAL_CACHE] 落盘失败: {_e}")


def _load_retrieval_cache():
    """启动时从 data/v8/retrieval_cache.json 恢复检索缓存"""
    global _query_cache, _search_empty_cache, _retry_cache
    try:
        from pathlib import Path as _Path
        import json as _json
        _cache_file = _Path(retrieval_cache_file())
        if not _cache_file.exists():
            logger.info("[RETRIEVAL_CACHE] 无持久化缓存文件，跳过恢复")
            return
        with open(_cache_file, "r", encoding="utf-8") as _f:
            _data = _json.load(_f)
        if not isinstance(_data, dict):
            return
        for _sid, _rec in _data.items():
            if not isinstance(_rec, dict):
                continue
            _qc = _rec.get("query_cache") or {}
            _ec = _rec.get("empty_cache") or 0
            _rc = _rec.get("retry_cache") or {}
            if isinstance(_qc, dict) and _qc:
                _query_cache.setdefault(_sid, {}).update(_qc)
            if isinstance(_ec, (int, float)):
                _search_empty_cache[_sid] = int(_ec)
            if isinstance(_rc, dict) and _rc:
                _retry_cache.setdefault(_sid, {}).update(_rc)
        logger.info(f"[RETRIEVAL_CACHE] 已恢复 {len(_data)} 个 session 检索缓存")
    except Exception as _e:
        logger.info(f"[RETRIEVAL_CACHE] 恢复失败: {_e}")




