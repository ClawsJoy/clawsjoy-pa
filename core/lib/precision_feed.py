#!/usr/bin/env python3
"""精准投喂（Precision Feed）数据资产加载模块

从 agent_gateway_enhanced.py 提取，保持函数签名和逻辑完全不变。
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

# 精准投喂缓存（全局单例）
_precision_feed_cache = {}

# hypothesis 缓存（_load_asset 内部用于 system_hypothesis 去重）
_hypothesis_cache: dict = {}  # key: str(max_items) -> {"data": str, "ts": float}

# learning_insight 缓存（_load_asset 内部用于 SelfUpgradingAgent 学习洞察去重）
_learning_cache: dict = {}  # key: str(max_items) -> {"data": str, "ts": float}


def _init_precision_feed_cache():
    """预加载精准投喂配置到缓存"""
    import yaml
    try:
        with open("config/os_precision_feeds.yaml", encoding="utf-8") as _f:
            _precision_feed_cache["feeds"] = yaml.safe_load(_f).get("feeds", [])
        print(f"[PRECISION_FEED] 预加载 {len(_precision_feed_cache['feeds'])} 条精准投喂规则")
    except Exception as e:
        print(f"[PRECISION_FEED] 预加载失败: {e}")
        _precision_feed_cache["feeds"] = []


def invalidate_precision_feed_cache():
    """使精准投喂缓存全部失效（供 GrowthEngine 规则更新后调用）"""
    _precision_feed_cache.clear()
    _hypothesis_cache.clear()
    _learning_cache.clear()
    print("[PRECISION_FEED] 缓存已失效（feeds / hypothesis / learning_insight）")


def _load_asset(source, params, user_id, session_id, step_number=0, _project_tree=None, task_name=None):
    """按 source 类型加载数据资产（step_number 支持渐进注入；task_name 变量驱动投喂 #41-3）"""
    step_number = step_number or 0
    base = Path(f"data/projects/{user_id}/{session_id}/clawsjoy_dev")

    if source == "PROJECT_TREE":
        return _project_tree or ""

    # #41 阶段3：变量驱动投喂 — 从任务描述提取变量
    _task_vars = None
    if task_name:
        try:
            from core.lib.task_vars import extract_task_vars
            _task_vars = extract_task_vars(task_name)
        except Exception:
            _task_vars = None

    if source == "world_model_summary":
        wm_path = base / ".agent_state.json"
        if wm_path.exists():
            wm = json.loads(wm_path.read_text(encoding="utf-8")).get("world_model", {})
            modules = wm.get("modules", {}) if isinstance(wm, dict) else {}
            if _task_vars is not None:
                try:
                    from core.lib.task_vars import filter_world_model_modules
                    modules = filter_world_model_modules(modules, _task_vars, params.get("top_modules", 30))
                except Exception:
                    modules = dict(list(modules.items())[:params.get("top_modules", 30)])
            else:
                modules = dict(list(modules.items())[:params.get("top_modules", 30)])
            return "\n".join(f"  {fp}: {(info.get('skeleton') or '')[:120]}" for fp, info in modules.items())

    if source == "world_model":
        wm_path = base / ".agent_state.json"
        if wm_path.exists():
            try:
                wm_data = json.loads(wm_path.read_text(encoding="utf-8"))
            except Exception:
                wm_data = None
            if _task_vars is not None and isinstance(wm_data, dict):
                # 变量驱动：只注入 world_model.modules 中相关模块
                try:
                    from core.lib.task_vars import filter_world_model_modules
                    wm_out = {"modules": filter_world_model_modules(
                        wm_data.get("world_model", {}).get("modules", {}),
                        _task_vars, params.get("top_modules", 30))}
                    wm_out["last_updated"] = wm_data.get("world_model", {}).get("last_updated", "")
                    base_chars = params.get("max_chars", 3000)
                    progressive_chars = min(base_chars + step_number * 500, base_chars * 3)
                    return json.dumps(wm_out, ensure_ascii=False, indent=2)[:progressive_chars]
                except Exception:
                    pass
            if isinstance(wm_data, dict):
                # 无变量/异常兜底：只注入 world_model 字段（替代整文件截断，省 token）
                wm_trim = {"world_model": wm_data.get("world_model", {}), "last_updated": wm_data.get("last_updated", "")}
                base_chars = params.get("max_chars", 3000)
                progressive_chars = min(base_chars + step_number * 500, base_chars * 3)
                return json.dumps(wm_trim, ensure_ascii=False, indent=2)[:progressive_chars]
            return ""
        return ""

    if source == "dependency_graph":
        dg_path = base / "data" / "dependency_graph.json"
        if dg_path.exists():
            dg_text = dg_path.read_text(encoding="utf-8")
            if _task_vars is not None:
                try:
                    from core.lib.task_vars import filter_dependency_graph
                    return filter_dependency_graph(dg_text, _task_vars, params.get("max_chars", 2000))
                except Exception:
                    pass
            return dg_text[:params.get("max_chars", 2000)]
        return ""

    if source == "manual":
        # 变量驱动按需注入：任务变量 → 匹配 manual 章节 → 只注入相关章节（非全量）
        try:
            from core.lib.sag_audit_bridge import query_entities
            _chapters = query_entities(entity_type="manual", limit=20) or []
            if not _chapters:
                return ""
            if _task_vars is not None:
                _kws = _task_vars.get("keywords", []) + _task_vars.get("tokens", []) + _task_vars.get("paths", [])
                _matched = []
                for _c in _chapters:
                    _name = str(_c.get("entity_name", ""))
                    if any(k.lower() in _name.lower() for k in _kws if k):
                        _matched.append(_c)
                if _matched:
                    _chapters = _matched
            # 渲染章节（每章名称 + 摘要签名，最多 max_chars）
            _max_chars = params.get("max_chars", 2000)
            _out_lines = []
            _cur_len = 0
            for _c in _chapters:
                _line = f"- {_c.get('entity_name', '')}: {str(_c.get('signature', ''))[:300]}"
                if _cur_len + len(_line) > _max_chars:
                    break
                _out_lines.append(_line)
                _cur_len += len(_line)
            return "\n".join(_out_lines) if _out_lines else ""
        except Exception as _man_err:
            print(f"[PRECISION_FEED] manual 注入失败: {_man_err}")
            return ""

    if source == "os_events":
        from core.lib.os_event_logger import read_recent_os_events
        events = read_recent_os_events(max_lines=params.get("max_lines", 20))
        return json.dumps(events, ensure_ascii=False, indent=2) if events else ""

    if source == "os_capabilities":
        try:
            import yaml
            caps_data = yaml.safe_load(open(Path(os.environ.get("PROJECT_ROOT", "")) / "config" / "os_capabilities.yaml", encoding="utf-8"))
            caps_list = caps_data.get("capabilities", [])
            filter_config = params.get("filter", {})
            if filter_config:
                domains = filter_config.get("domain", [])
                types = filter_config.get("type", [])
                if domains or types:
                    caps_list = [c for c in caps_list
                                 if c.get("domain") in domains
                                 or c.get("type") in types]
            return json.dumps(caps_list, ensure_ascii=False, indent=2)[:params.get("max_chars", 3000)]
        except Exception as e:
            logging.exception("os_capabilities 加载失败")
            return ""

    if source == "system_hypothesis":
        # 渐进注入：根据 step_number 逐步增加加载数量
        base_items = params.get("max_items", 5) or 5
        progressive_items = min(base_items + step_number, base_items + 15)
        _cache_key = f"{progressive_items}"
        _cached = _hypothesis_cache.get(_cache_key)
        if _cached and time.time() - _cached["ts"] < 30:
            logging.info("[CACHE HIT] system_hypothesis")
            return _cached["data"]
        try:
            import psycopg2
            pg = psycopg2.connect("postgresql://clawsjoy:clawsjoy_secret@localhost:5432/clawsjoy_dev")
            cur = pg.cursor()
            cur.execute("SELECT entity_name, signature FROM code_entities WHERE entity_type='system_hypothesis' ORDER BY created_at DESC LIMIT %s", (progressive_items,))
            rows = cur.fetchall()
            cur.close(); pg.close()
            result = "\n".join(f"  {r[0]}: {r[1]}" for r in rows) if rows else ""
            _hypothesis_cache[_cache_key] = {"data": result, "ts": time.time()}
            return result
        except Exception:
            return ""

    if source == "learning_insight":
        # SelfUpgradingAgent 反思结果（SAG entity_type='learning_insight'）自动注入
        # 渐进注入：step_number 越大加载越多（早期省 token，后期丰富上下文）
        base_items = params.get("max_items", 5) or 5
        progressive_items = min(base_items + step_number, base_items + 15)
        _cache_key = f"{progressive_items}"
        _cached = _learning_cache.get(_cache_key)
        if _cached and time.time() - _cached["ts"] < 30:
            logging.info("[CACHE HIT] learning_insight")
            return _cached["data"]
        # GrowthEngine 规则更新后自动通知精准投喂缓存刷新
        try:
            from core.lib.gateway_helpers import check_growth_rule_refresh
            check_growth_rule_refresh()
        except Exception:
            pass
        try:
            import psycopg2
            pg = psycopg2.connect(os.getenv("DATABASE_URL", "postgresql://clawsjoy:clawsjoy_secret@localhost:5432/clawsjoy_dev"))
            cur = pg.cursor()
            cur.execute(
                "SELECT entity_name, signature FROM code_entities WHERE entity_type='learning_insight' ORDER BY created_at DESC LIMIT %s",
                (progressive_items,),
            )
            rows = cur.fetchall()
            cur.close()
            pg.close()
            result = "\n".join(f"  {r[0]}: {r[1]}" for r in rows) if rows else ""
            _learning_cache[_cache_key] = {"data": result, "ts": time.time()}
            return result
        except Exception:
            return ""

    if source == "billing_summary":
        _sid = session_id or "default"
        billing_path = Path(f"data/projects/{user_id}/{_sid}/clawsjoy_dev/data/v8/billing_default.jsonl")
        if billing_path.exists():
            lines = billing_path.read_text(encoding="utf-8").split("\n")[-50:]
            result = "\n".join(lines)
            max_chars = params.get("max_chars", 1500)
            return result[-max_chars:] if len(result) > max_chars else result
        return ""

    if source == "current_plan_discussion":
        _task_state_file = Path(f"data/projects/{user_id}/{session_id}/.current_plan_task.json")
        if _task_state_file.exists():
            _ts = json.loads(_task_state_file.read_text(encoding="utf-8"))
            _tid = _ts.get("task_id", "")
            if _tid:
                try:
                    import psycopg2
                    pg = psycopg2.connect("postgresql://clawsjoy:clawsjoy_secret@localhost:5432/clawsjoy_dev")
                    cur = pg.cursor()
                    cur.execute("SELECT signature FROM code_entities WHERE entity_type='plan_discussion' AND entity_name=%s", (_tid,))
                    row = cur.fetchone()
                    cur.close(); pg.close()
                    return row[0] if row else ""
                except Exception: return ""
        return ""

    if source == "sag_dependency_chain":
        from core.lib.sag_chain_injector import SagChainInjector
        injector = SagChainInjector()
        return injector.inject_text(
            task_query=params.get("task_query", ""),
            chain=params.get("chain", ["task", "plan", "hypothesis", "capability"]),
            max_items=params.get("max_items", 5),
            max_chars=params.get("max_chars", 1500),
        )

    return ""


def _classify_task_type(task_name) -> str:
    # 按任务名称分类任务类型，用于精准投喂策略选择
    # 返回类型:
    #   - modification:     代码/文件修改类任务（写入、重构、实现）
    #   - troubleshooting:  故障排查/修复类任务（报错、bug、异常）
    #   - analysis:         分析/评估类任务（报告、审查、对比）
    #   - discussion:       讨论/咨询类任务（默认兜底）
    if not task_name:
        return "discussion"
    name = str(task_name).lower()
    # 排查/修复类（优先：修复 bug 类任务归 troubleshooting）
    if any(k in name for k in (
        "排查", "报错", "异常", "失败", "故障", "崩溃", "调试", "定位",
        "bug", "debug", "error", "exception", "traceback",
    )):
        return "troubleshooting"
    # 修改类：明确改动动词
    if any(k in name for k in (
        "修改", "改动", "更改", "变更", "改写", "写入", "新增", "添加", "删除",
        "重构", "实现", "开发", "编写", "创建", "替换", "迁移", "更新",
        "implement", "add", "create", "modify", "update", "refactor",
        "write", "delete", "remove", "rename",
    )):
        return "modification"
    # 分析类
    if any(k in name for k in (
        "分析", "评估", "报告", "总结", "对比", "审查", "审计", "调研", "检查",
        "review", "analy", "report", "summary", "compare", "audit",
    )):
        return "analysis"
    # 兜底：讨论/咨询类
    return "discussion"

def _load_asset_step_aware(source, params, user_id, session_id, step_number, task_name, _project_tree=None):
    """步骤感知的精准投喂加载

    - step_number == 0 (核心规划层): 加载全量数据资产
    - step_number > 0 (执行步骤): 只加载精简摘要版本
    - 自动注入前面步骤的摘要到结果中
    """
    # 按任务类型筛选投喂源：source 所属 feed 配置的 task_types 不匹配当前任务类型时跳过
    task_type = _classify_task_type(task_name)
    feeds = _precision_feed_cache.get("feeds", [])
    related_feeds = [
        f for f in feeds
        if any(i.get("source") == source for i in f.get("inject", []))
    ]
    allowed_types = set()
    for f in related_feeds:
        allowed_types.update(f.get("task_types") or [])
    if allowed_types and task_type not in allowed_types:
        logging.info(
            f"[PRECISION_FEED] step_aware: source={source} 与任务类型 {task_type} 不匹配"
            f"（允许: {sorted(allowed_types)}），跳过投喂"
        )
        return ""

    is_core = (step_number == 0)
    logging.info(f"[PRECISION_FEED] step_aware: source={source}, step={step_number}, is_core={is_core}")

    if is_core:
        # 核心规划层：加载全量资产（#41-3 传 task_name 变量驱动裁剪）
        result = _load_asset(source, params, user_id, session_id, step_number, _project_tree, task_name=task_name)
    else:
        # 执行步骤：精简加载，限制输出量（#41-3 传 task_name 变量驱动裁剪）
        summary_params = dict(params)
        summary_params["max_chars"] = summary_params.get("max_chars", 500)
        summary_params["max_lines"] = summary_params.get("max_lines", 5)
        summary_params["top_modules"] = summary_params.get("top_modules", 5)
        result = _load_asset(source, summary_params, user_id, session_id, step_number, _project_tree, task_name=task_name)

    # 查询前面步骤的摘要并注入
    try:
        from core.lib.code_entity_extractor import CodeEntityExtractor
        extractor = CodeEntityExtractor()
        summaries = extractor.query_step_summaries(task_name)
        if summaries:
            step_summary_lines = ["\n[前面步骤摘要]"]
            for s in summaries:
                step_num = s.get("step_number", "?")
                summary_json = s.get("summary_json", "")
                created = s.get("created_at", "")
                # 截取前 200 字符避免过长
                brief = str(summary_json)[:200]
                step_summary_lines.append(f"  Step {step_num}: {brief}")
                if created:
                    step_summary_lines[-1] += f"  ({created})"
            step_summary_text = "\n".join(step_summary_lines)
            result = (result + step_summary_text) if result else step_summary_text
            logging.info(f"[PRECISION_FEED] 注入 {len(summaries)} 条步骤摘要")
    except Exception as e:
        logging.warning(f"[PRECISION_FEED] query_step_summaries 失败: {e}")

    return result or ""
