"""注册表初始化 — 从 agent_gateway_enhanced.py 抽取

启动时遍历 config/ 下所有注册表 YAML，统一入库 SAG。
"""

import logging
import json
import os
import yaml
from pathlib import Path
from core.lib.precision_feed import _init_precision_feed_cache

logger = logging.getLogger(__name__)


def _init_registries():
    """启动时遍历 config/ 下所有注册表 YAML，统一入库 SAG（幂等：ON CONFLICT DO UPDATE）"""
    _registry_map = [
        ("config/os_capabilities.yaml",          "capabilities",       "os_capability",      "id"),
        ("config/os_precision_feeds.yaml",        "feeds",              "precision_feed",     "id"),
        ("config/os_event_injection_points.yaml", "injection_points",   "injection_point",    "id"),
        ("config/v8/available_models.yaml",       "models",             "available_model",    "value"),
    ]
    import yaml
    from core.lib.code_entity_extractor import extractor
    _total = 0
    for _yaml_path, _top_key, _entity_type, _id_field in _registry_map:
        try:
            with open(_yaml_path) as f:
                data = yaml.safe_load(f)
            items = data.get(_top_key, [])
            for item in items:
                _id = item.get(_id_field)
                if not _id:
                    continue
                extractor.upsert_entity({
                    "entity_type": _entity_type,
                    "entity_name": f"{_entity_type}::{_id}",
                    "signature": json.dumps(item, ensure_ascii=False),
                    "file_path": _yaml_path,
                })
                # 打通 os_capabilities.yaml → Agent tools：os_capability 同步以 tool 实体入库（同样 signature）
                if _entity_type == "os_capability":
                    extractor.upsert_entity({
                        "entity_type": "tool",
                        "entity_name": f"tool::{_id}",
                        "signature": json.dumps(item, ensure_ascii=False),
                        "file_path": _yaml_path,
                    })
            _total += len(items)
            logger.info(f"[REGISTRY] {_yaml_path} \u2192 {len(items)} \u6761 {_entity_type} \u5df2\u5165\u5e93")
        except Exception as e:
            logger.info(f"[REGISTRY] {_yaml_path} \u5165\u5e93\u5931\u8d25: {e}")
    logger.info(f"[REGISTRY] \u603b\u8ba1\u5165\u5e93 {_total} \u6761\u6ce8\u518c\u8868\u8bb0\u5f55")
    # 扫描 config/orchestration/templates.yaml 入库 SAG（plan_template：拆解模板库积累）
    _template_yaml = "config/orchestration/templates.yaml"
    try:
        with open(_template_yaml) as _f:
            _tmpl_data = yaml.safe_load(_f) or {}
        _tmpl_total = 0
        for _tmpl_name, _tmpl_body in (_tmpl_data.get("templates", {}) or {}).items():
            if not _tmpl_name:
                continue
            extractor.upsert_entity({
                "entity_type": "plan_template",
                "entity_name": "plan_template::{}".format(_tmpl_name),
                "signature": json.dumps(_tmpl_body, ensure_ascii=False),
                "file_path": _template_yaml,
            })
            _tmpl_total += 1
        logger.info("[REGISTRY] {} -> {} \u6761 plan_template \u5df2\u5165\u5e93".format(_template_yaml, _tmpl_total))
    except Exception as e:
        logger.info("[REGISTRY] {} \u5165\u5e93\u5931\u8d25: {}".format(_template_yaml, e))
    # 扫描 engine/ 下 Python 模块入库 SAG（project_id=default，与 search_with_hyperedges 默认查询一致）
    _engine_dir = "engine"
    _engine_total = 0
    try:
        for _root, _dirs, _files in os.walk(_engine_dir):
            for _fname in sorted(_files):
                if not _fname.endswith(".py"):
                    continue
                _fpath = os.path.join(_root, _fname)
                try:
                    with open(_fpath, encoding="utf-8") as _f:
                        _content = _f.read()
                    extractor.extract_and_upsert(_fpath, _content, project_id="default")
                    _engine_total += 1
                except Exception as _e:
                    logger.info(f"[ENGINE_SAG] {_fpath} 入库失败: {_e}")
        logger.info(f"[ENGINE_SAG] engine/ 共入库 {_engine_total} 个 Python 模块")
    except Exception as _e:
        logger.info(f"[ENGINE_SAG] 扫描 engine/ 失败: {_e}")
    # 扫描 tasks.json 任务定义
    _task_json_paths = [
        "config/tasks.json",
        "config/v8/tasks.json",
        "data/orchestration/tasks.json",
    ]
    for _task_path in _task_json_paths:
        if Path(_task_path).exists():
            from engine.orchestration.task_manager import TaskManager
            TaskManager.register_tasks_from_json(_task_path)
    # 扫描 keywords.yaml 入库 SAG（作为关键词统一入口）
    _keyword_yaml = "config/keywords.yaml"
    try:
        with open(_keyword_yaml) as _f:
            _kw_data = yaml.safe_load(_f)
        _kw_total = 0
        # intents 节点：遍历每个意图的关键词
        for _intent_name, _intent_data in _kw_data.get("intents", {}).items():
            for _kw in _intent_data.get("keywords", []):
                extractor.upsert_entity({
                    "entity_type": "keyword",
                    "entity_name": _kw,
                    "signature": json.dumps({"intent": _intent_name, "category": "intent", "name": _intent_data.get("name", "")}, ensure_ascii=False),
                    "file_path": _keyword_yaml,
                })
                _kw_total += 1
        # extractors 节点：遍历每个提取器的关键词
        for _ext_name, _ext_data in _kw_data.get("extractors", {}).items():
            for _kw in _ext_data.get("keywords", []):
                extractor.upsert_entity({
                    "entity_type": "keyword",
                    "entity_name": _kw,
                    "signature": json.dumps({"intent": _ext_name, "category": "extractor", "name": _ext_data.get("name", "")}, ensure_ascii=False),
                    "file_path": _keyword_yaml,
                })
                _kw_total += 1
        # task_detection 节点：遍历每个检测子类的关键词
        for _detect_cat, _kw_list in _kw_data.get("task_detection", {}).items():
            for _kw in _kw_list:
                extractor.upsert_entity({
                    "entity_type": "keyword",
                    "entity_name": _kw,
                    "signature": json.dumps({"intent": _detect_cat, "category": "task_detection"}, ensure_ascii=False),
                    "file_path": _keyword_yaml,
                })
                _kw_total += 1
        logger.info(f"[REGISTRY] {_keyword_yaml} \u2192 {_kw_total} \u6761 keyword \u5df2\u5165\u5e93")
    except Exception as e:
        logger.info(f"[REGISTRY] {_keyword_yaml} \u5165\u5e93\u5931\u8d25: {e}")
    # 预加载精准投喂配置到缓存
    # Agent 启动自检：标记硬编码旧任务脚本为 EXPIRED
    _legacy_scripts = [
        "_do_cleanup.py", "_edit_script.py", "_fix_1416.py",
        "_fix_collapsed.py", "_install_decomp.py", "_patch_feeds_v2.py",
        "_patch_init_registries.py",
    ]
    from engine.orchestration.task_manager import task_manager, TaskStatus
    from datetime import datetime
    # 检查 plan_legacy_ 前缀是否已存在
    _legacy_plan_dir = Path("data/orchestration")
    _existing = list(_legacy_plan_dir.glob("plan_legacy_*.json"))
    if not _existing:
        # 创建 legacy 计划
        _tasks_data = [
            {"name": s, "agent": "system", "action": "expire", "params": {}}
            for s in _legacy_scripts
        ]
        _plan = task_manager.create_plan(
            name="legacy_cleanup",
            description="旧任务脚本过期标记（自动自检）",
            tasks=_tasks_data,
        )
        # 改写 plan.id 以包含 legacy 前缀，便于后续检查
        _plan.id = f"plan_legacy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        # 逐个标记 EXPIRED
        _now = datetime.now()
        _count = 0
        for _t in _plan.tasks:
            _t.status = TaskStatus.EXPIRED
            _t.expired_at = _now
            _t.skip_reason = "旧任务脚本已废弃，标记为 EXPIRED"
            _count += 1
        # 重新保存计划（含过期标记）
        task_manager._save_plan(_plan)
        logger.info(f"[SELF_CHECK] 标记 {_count} 个旧任务为 EXPIRED")
    else:
        logger.info(f"[SELF_CHECK] plan_legacy_ 已存在 ({_existing[0].stem})，跳过创建")
    _init_precision_feed_cache()
    # #87 dependency_graph.json → SAG（幂等：upsert_entity ON CONFLICT DO UPDATE）
    try:
        _graph_file = Path("core/lib/dependency_graph.json")
        if _graph_file.exists():
            _graph = json.loads(_graph_file.read_text(encoding="utf-8"))
            _edge_total = 0
            for _src, _imps in (_graph or {}).items():
                for _imp in list(dict.fromkeys(_imps or []))[:30]:
                    extractor.upsert_entity({
                        "entity_type": "dependency_edge",
                        "entity_name": f"edge::{_src}::{_imp}",
                        "signature": json.dumps({"source": _src, "target": _imp, "type": "imports"}, ensure_ascii=False),
                        "file_path": f"core/lib/{_src}",
                    })
                    _edge_total += 1
            logger.info(f"[REGISTRY] dependency_graph.json → {_edge_total} 条 dependency_edge 已入库")
    except Exception as e:
        logger.info(f"[REGISTRY] dependency_graph.json 入库失败: {e}")
    _load_sag_index_cache()


def _load_sag_index_cache():
    """将 code_entities 全量数据预加载到内存 dict

    key: entity_name
    value: {entity_type, file_path, signature, related_entities}
    """
    global _sag_index_cache
    try:
        import psycopg2
        from core.lib.code_entity_extractor import extractor
        conn = psycopg2.connect(extractor.db_url)
        cur = conn.cursor()
        cur.execute(
            "SELECT entity_name, entity_type, file_path, signature, related_entities "
            "FROM code_entities"
        )
        _cache = {}
        for _name, _etype, _fpath, _sig, _rel in cur.fetchall():
            _cache[_name] = {
                "entity_type": _etype,
                "file_path": _fpath,
                "signature": _sig,
                "related_entities": _rel or [],
            }
        cur.close()
        conn.close()
        _sag_index_cache = _cache
        logger.info(f"[SAG_INDEX] 预加载 {len(_sag_index_cache)} 条 code_entities 到内存")
    except Exception as e:
        logger.info(f"[SAG_INDEX] 预加载失败: {e}")
        _sag_index_cache = {}


