"""SAG 反馈与学习链 — 从 agent_gateway_enhanced.py 抽取"""

import logging
import json
from datetime import datetime
from pathlib import Path
from core.gateway.shared_state import _sag_index_cache

logger = logging.getLogger(__name__)

def _record_path_pattern(original, resolved, user_id="default", session_id="default"):
    """记录路径使用模式（成功或修正）"""
    _state_file = Path(f"data/projects/{user_id}/{session_id}/clawsjoy_dev/.agent_state.json")
    try:
        _state = json.loads(_state_file.read_text(encoding="utf-8")) if _state_file.exists() else {}
        _patterns = _state.get("known_patterns", [])
        if not isinstance(_patterns, list):
            _patterns = []
        _pattern_type = "correction" if original != resolved else "success"
        if not original:
            return  # 无效修正，不记录
        _patterns.append({
            "type": _pattern_type,
            "original": original,
            "resolved": resolved,
            "timestamp": datetime.now().isoformat()
        })
        _state["known_patterns"] = _patterns[-20:]
        _tmp = _state_file.with_suffix(".tmp")
        _tmp.write_text(json.dumps(_state, ensure_ascii=False, indent=2), encoding="utf-8")
        _tmp.replace(_state_file)
    except Exception:
        pass



def _build_code_edges(modules):
    """从 world_model.modules 线性 dict 推导图边（与 DB code_edges 表同构）：
    - contains: 文件 → 类/函数
    - imports:  文件 → 依赖模块
    - calls:    函数 → 被调用符号（依赖函数级 related，由 DB 层 _sync_code_edges 补充）
    返回 list[dict]: {source, target, type, file_path}
    """
    edges = []
    for _fp, _meta in (modules or {}).items():
        if not isinstance(_meta, dict):
            continue
        for _cls in _meta.get("classes", []) or []:
            edges.append({"source": _fp, "target": _cls, "type": "contains", "file_path": _fp})
        for _fn in _meta.get("functions", []) or []:
            edges.append({"source": _fp, "target": _fn, "type": "contains", "file_path": _fp})
        for _imp in _meta.get("imports", []) or []:
            edges.append({"source": _fp, "target": _imp, "type": "imports", "file_path": _fp})
    return edges



def _update_sag_feedback(task_name, session_id, user_id, messages, passed=True, verification=None):
    """任务完成后将结果作为 feedback 写入 SAG，更新相关实体/边的评分（#166 自学习闭环）。

    自学习评分更新：
    1. 从任务名/用户消息提取关键词（中文片段 + 文件名）
    2. 通过 SAG 全文检索相关实体
    3. 对命中的实体边调用 record_edge_feedback 更新权重（成功提高 / 失败降低）
    4. 将反馈记录入库 steps_summary（feedback 语义），返回更新边数
    """
    try:
        from core.lib.code_entity_extractor import extractor as _sag_extractor
        import re as _re_fb
        # 1. 提取关键词
        _fb_kws = set()
        _fb_text = (task_name or "") + " " + str(verification or "")
        for _m_fb in messages:
            if _m_fb.get("role") == "user":
                _fb_text += " " + str(_m_fb.get("content", ""))
        for _seg in _re_fb.findall(r'[一-鿿]{2,6}', _fb_text):
            _fb_kws.add(_seg)
        for _fn in _re_fb.findall(r'[\w]+/[\w\-./]+\.\w+', _fb_text):
            _fb_kws.add(_fn.split("/")[-1])
        _fb_kws = [k for k in list(_fb_kws) if k][:10]
        if not _fb_kws:
            _fb_kws = [str(task_name or "task")[:20]]
        # 2. 检索相关实体
        _fb_entities = []
        try:
            _fb_entities = _sag_extractor.query_fulltext_by_keywords(_fb_kws) or []
        except Exception:
            pass
        # 3. 更新边权重（成功提高 10%，失败降低 10%）
        _fb_updated = 0
        for _ent in _fb_entities[:10]:
            _ent_name = _ent.get("entity_name") or _ent.get("task_name") or ""
            _ent_path = _ent.get("file_path") or ""
            if not _ent_name:
                continue
            try:
                _sag_extractor.record_edge_feedback(
                    source_name=str(_ent_name)[:200],
                    target_name=str(_ent_path or "task")[:200],
                    edge_type="task_feedback",
                    used=bool(passed),
                )
                _fb_updated += 1
            except Exception:
                pass
        # 4. 反馈记录入库（steps_summary feedback 语义）
        _fb_summary = {
            "feedback_type": "task_completion",
            "feedback_value": 1.0 if passed else -1.0,
            "passed": bool(passed),
            "keywords": _fb_kws[:10],
            "entities_updated": _fb_updated,
            "verification": verification,
            "ts": datetime.now().isoformat(),
            "source": "self_learning",
        }
        try:
            _sag_extractor.store_step_summary(
                task_name="sag_feedback_%s_%s" % (session_id, datetime.now().strftime('%Y%m%d%H%M%S')),
                step_number=1,
                summary_json=_fb_summary,
            )
        except Exception:
            pass
        logger.info("[SAG_FEEDBACK] task=%s passed=%s updated=%d entities=%d" % (str(task_name)[:40], passed, _fb_updated, len(_fb_entities)))
        return _fb_updated
    except Exception as _e_fb:
        logger.info("[SAG_FEEDBACK] 更新失败: %s" % _e_fb)
        return 0



def _update_sag_edge_learning(task_name, session_id, user_id, messages):
    """#81 过滤网自学习：任务完成后分析 Agent 是否使用了注入的 SAG 节点，更新 code_edges 评分。

    评分规则（委托 code_entity_extractor.update_edge_learning）：
    - 使用了注入节点 → used_count += 1, weight += 0.1
    - 未使用 → ignored_count += 1, weight -= 0.05
    - 长期未使用 → weight 衰减（默认 30 天 *0.95）

    使用判定：注入实体名出现在 assistant 输出（content / tool_calls 参数）中，
    或 Agent 调用了 query_index（SAG 检索入口）。
    """
    try:
        import re as _re_learn
        from core.lib.code_entity_extractor import extractor as _learn_extractor

        # 1. 收集注入的 SAG 内容（system 消息中含 SAG 相关标记）
        _injected_text = ""
        for _m in messages:
            if _m.get("role") != "system":
                continue
            _c = str(_m.get("content", "") or "")
            if any(_tag in _c for _tag in ("sag_context", "sag_task_subgraph", "[SAG]", "query_index", "知识图谱")):
                _injected_text += _c + "\n"

        # 2. 提取实体名：文件路径 basename + 显式 entity_name 标记
        _entity_names = set()
        for _fn in _re_learn.findall(r"[\w\-./]+\.(?:py|md|yaml|yml|json|txt|sh|toml|cfg|ini)\b", _injected_text):
            _basename = _fn.split("/")[-1].strip()
            if len(_basename) > 3:
                _entity_names.add(_basename)
        for _en in _re_learn.findall(r"entity_name[\"':：=\s]*([\w\-./]+)", _injected_text):
            _en_b = _en.strip().split("/")[-1]
            if len(_en_b) > 2:
                _entity_names.add(_en_b)
        if not _entity_names:
            logger.info(f"[SAG_LEARN] #81 未提取到注入节点: task={str(task_name)[:40]}")
            return 0

        # 3. 汇总 assistant 输出（content + tool_calls）
        _used_text = ""
        for _m in messages:
            if _m.get("role") != "assistant":
                continue
            _used_text += str(_m.get("content", "") or "") + "\n"
            for _tc in (_m.get("tool_calls") or []):
                _f = _tc.get("function", {}) or {}
                _used_text += str(_f.get("name", "")) + " " + str(_f.get("arguments", "")) + "\n"

        # 4. 判定使用：实体名被引用，或调用了 query_index 检索 SAG
        _used_names = set()
        _has_query_index = "query_index" in _used_text
        for _name in _entity_names:
            if _name in _used_text or _has_query_index:
                _used_names.add(_name)

        # 5. 更新 code_edges 评分（used += 0.1 / ignored -= 0.05 / 长期衰减）
        _updated = _learn_extractor.update_edge_learning(
            entity_names=list(_entity_names),
            used_entity_names=list(_used_names),
            project_id="default",
        )
        logger.info(f"[SAG_LEARN] #81 task={str(task_name)[:40]} 注入节点={len(_entity_names)} "
              f"使用={len(_used_names)} 更新边={_updated}")
        return _updated
    except Exception as _e_learn:
        logger.info(f"[SAG_LEARN] #81 过滤网自学习失败: {_e_learn}")
        return 0




def get_sag_index(entity_name: str = None):
    """查询 SAG 索引，优先查内存缓存，miss 才查 DB

    Args:
        entity_name: 实体名；None 时返回全量 dict

    Returns:
        dict | None: 单个实体 {entity_type, file_path, signature, related_entities}
                     或全量 {entity_name: {...}}
    """
    if entity_name is None:
        return _sag_index_cache
    if entity_name in _sag_index_cache:
        return _sag_index_cache[entity_name]
    # 内存 miss → 查 DB（并回填缓存）
    try:
        import psycopg2
        from core.lib.code_entity_extractor import extractor
        conn = psycopg2.connect(extractor.db_url)
        cur = conn.cursor()
        cur.execute(
            "SELECT entity_name, entity_type, file_path, signature, related_entities "
            "FROM code_entities WHERE entity_name=%s",
            (entity_name,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            _entry = {
                "entity_type": row[1],
                "file_path": row[2],
                "signature": row[3],
                "related_entities": row[4] or [],
            }
            _sag_index_cache[row[0]] = _entry
            return _entry
        return None
    except Exception as e:
        logger.info(f"[SAG_INDEX] DB 查询失败: {e}")
        return None


