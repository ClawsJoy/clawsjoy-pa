#!/usr/bin/env python3
# Planner Agent - 独立任务规划 Agent
#
# 职责：将用户输入拆解为可执行的 DAG 任务图，供编排器并行/串行调度。
#
# 核心方法：
#   1. plan(user_input)        -> 调 LLM 生成 DAG JSON（模板不匹配时）
#   2. _decompose(user_input)  -> 按模板拆解为 DAG JSON（模板匹配时）
#   3. _load_templates()       -> 从 config/orchestration/templates.yaml 加载模板
#
# 设计说明：
#   - 优先继承 BusinessAgentV2（编排升级基类）；当前代码库尚未提供该基类时
#     回退到 BusinessAgent（V4 业务基类），保证模块始终可导入。
#   - 不覆盖基类 process 模板方法，业务逻辑放在 _execute_business。
#   - 只新增本文件，不改动其他代码。
#
# @version: 1.0.0
# @author: ClawsJoy

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

try:
    # BusinessAgentV2 由编排升级子任务提供；缺失时回退 V4 业务基类
    from core.agents.business.business_agent_v2 import BusinessAgentV2 as _PlannerBase
    _BASE_CLASS = "BusinessAgentV2"
except ImportError:
    from core.agents.business.base_business_agent import BusinessAgent as _PlannerBase
    _BASE_CLASS = "BusinessAgent"

from core.lib.config_manager import config_manager
from core.lib.unified_config import unified_config

logger = logging.getLogger(__name__)

# 模板文件路径（相对项目根）
_TEMPLATES_PATH = Path("config/orchestration/templates.yaml")

# LLM 端点/模型默认值
_LLM_ENDPOINT_DEFAULT = "http://127.0.0.1:11434"
_MODEL_DEFAULT = "qwen2.5:7b"

# 通用 DAG 兜底模板：无模板匹配且 LLM 不可用时使用
_FALLBACK_DAG = {
    "template": "generic",
    "name": "通用任务",
    "parallel": False,
    "rollback": True,
    "nodes": [
        {
            "id": "analyze",
            "agent": "analysis_agent",
            "message": "分析需求: {user_input}",
            "depends_on": [],
            "optional": False,
            "rollback": "clear_cache",
        },
        {
            "id": "execute",
            "agent": "worker_agent",
            "message": "执行任务: {user_input}",
            "depends_on": ["analyze"],
            "optional": False,
            "rollback": "delete_temp",
        },
        {
            "id": "summarize",
            "agent": "writer_agent",
            "message": "汇总结果: {user_input}",
            "depends_on": ["execute"],
            "optional": True,
            "rollback": "delete_draft",
        },
    ],
}


class PlannerAgent(_PlannerBase):
    # 独立 Planner Agent：将用户输入拆解为 DAG 任务图
    #
    # 优先级：模板匹配 -> LLM 生成 -> 通用兜底。
    # 生成结果统一为 DAG JSON：
    #   {
    #     "template": "video_production",
    #     "name": "视频制作",
    #     "parallel": true,
    #     "rollback": true,
    #     "nodes": [{"id", "agent", "message", "depends_on", "optional", "rollback"}],
    #     "edges": [["dep", "node_id"], ...],
    #     "_meta": {"source", "planner", "ts"}
    #   }

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        # 保留基类 name，缺省时使用 planner_agent
        self.name = getattr(self, "name", None) or "planner_agent"
        self._templates: Dict[str, Dict[str, Any]] = {}
        self._templates_loaded_at = 0.0
        self._dag_cache: Dict[str, Dict[str, Any]] = {}
        self._load_templates()

    # ========== 公共 API ==========

    def plan(self, user_input: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        # 生成 DAG JSON。
        # 优先级：模板匹配 -> LLM 生成 -> 通用兜底。
        text = (user_input or "").strip()
        if not text:
            return dict(_FALLBACK_DAG)

        # 相同输入直接复用，避免重复调 LLM
        cache_key = self._cache_key(text)
        if cache_key in self._dag_cache:
            return self._dag_cache[cache_key]

        dag = None
        source = "none"

        # 1. 模板拆解
        dag, matched_key = self._decompose(text)
        if dag:
            source = "template:" + matched_key

        # 2. LLM 生成
        if not dag:
            dag = self._llm_plan(text, context or {})
            source = "llm"

        # 3. 通用兜底
        if not dag:
            dag = self._build_fallback_dag(text)
            source = "fallback"

        dag["_meta"] = {
            "source": source,
            "planner": self.name,
            "base_class": _BASE_CLASS,
            "ts": time.time(),
        }
        self._dag_cache[cache_key] = dag
        return dag

    # ========== 模板拆解 ==========

    def _decompose(self, user_input: str) -> Tuple[Optional[Dict[str, Any]], str]:
        # 按模板拆解用户输入。
        # 返回 (dag_dict, template_key)；无匹配时返回 (None, "")。
        text = (user_input or "").strip()
        if not text:
            return None, ""

        best_key, best_score = "", 0
        for key, tpl in self._templates.items():
            triggers = tpl.get("triggers") or []
            score = 0
            for trig in triggers:
                if trig and trig in text:
                    score += 1
            if score > best_score:
                best_key, best_score = key, score

        if not best_key:
            return None, ""
        dag = self._template_to_dag(best_key, self._templates[best_key], text)
        return dag, best_key

    def _template_to_dag(self, key: str, tpl: Dict[str, Any], user_input: str) -> Dict[str, Any]:
        # 将模板转换为 DAG JSON（nodes + edges）。
        nodes: List[Dict[str, Any]] = []
        edges: List[List[str]] = []
        for idx, task in enumerate(tpl.get("tasks") or []):
            node_id = task.get("name") or "task_%d" % idx
            depends = list(task.get("depends_on") or [])
            node = {
                "id": node_id,
                "agent": task.get("agent", "worker_agent"),
                "message": self._format_message(task.get("message", ""), user_input),
                "depends_on": depends,
                "optional": bool(task.get("optional", False)),
                "rollback": task.get("rollback", ""),
            }
            for dep in depends:
                edges.append([dep, node_id])
            nodes.append(node)

        return {
            "template": key,
            "name": tpl.get("name", key),
            "description": tpl.get("description", ""),
            "parallel": bool(tpl.get("parallel", False)),
            "rollback": bool(tpl.get("rollback", False)),
            "nodes": nodes,
            "edges": edges,
        }

    # ========== 模板加载 ==========

    def _load_templates(self) -> Dict[str, Dict[str, Any]]:
        # 从 config/orchestration/templates.yaml 加载模板。
        # 模板缺失/解析失败不阻断运行，置空后回退 LLM/兜底 DAG。
        path = _TEMPLATES_PATH
        if not path.exists():
            logger.warning("模板文件不存在: %s", path)
            self._templates = {}
            return self._templates

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            templates = data.get("templates") or {}
            self._templates = templates if isinstance(templates, dict) else {}
            self._templates_loaded_at = time.time()
        except Exception as e:
            logger.error("加载模板失败 %s: %s", path, e)
            self._templates = {}
        return self._templates

    # ========== LLM 生成 DAG ==========

    def _llm_plan(self, user_input: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # 调用 LLM 生成 DAG JSON；失败返回 None。
        prompt = self._build_llm_prompt(user_input, context)
        endpoint = unified_config.get("llm.endpoint", _LLM_ENDPOINT_DEFAULT)
        try:
            model = config_manager.get_model()
        except Exception:
            model = _MODEL_DEFAULT

        try:
            import requests

            resp = requests.post(
                "{0}/api/generate".format(endpoint.rstrip("/")),
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.2, "num_predict": 1500},
                },
                timeout=60,
            )
            if resp.status_code != 200:
                logger.warning("LLM 规划 HTTP %s: %s", resp.status_code, resp.text[:200])
                return None
            payload = resp.json()
            raw = payload.get("response") or payload.get("text") or ""
            return self._parse_dag_json(raw)
        except Exception as e:
            logger.error("LLM 规划失败: %s", e)
            return None

    def _build_llm_prompt(self, user_input: str, context: Dict[str, Any]) -> str:
        # 构造 LLM 规划 Prompt，要求输出 DAG JSON。
        template_hint = ""
        if self._templates:
            names = ", ".join(sorted(self._templates.keys()))
            template_hint = "可参考模板 key: {0}".format(names)

        prompt = (
            "你是任务规划器。请把用户需求拆解为 DAG 任务图，只输出 JSON，不要解释。\n"
            "JSON 结构：\n"
            '{"template": "<模板key或custom>", "name": "<任务名>", "parallel": true/false, '
            '"rollback": true/false, "nodes": [{"id": "<节点id>", "agent": "<agent名>", '
            '"message": "<任务描述，可含 {user_input}>", "depends_on": ["<依赖节点id>"], '
            '"optional": true/false, "rollback": "<回滚动作>"}], '
            '"edges": [["<依赖id>", "<节点id>"]]}'

            "2. agent 字段从已有 agent 中选用（如 analysis_agent/video_agent/writer_agent/"
            "worker_agent/vision_agent）。\n"
            "3. 可并行任务之间不要互相依赖。\n"
            "4. 必须包含 edges 数组，与 nodes 的 depends_on 保持一致。\n"
        )
        prompt += template_hint + "\n"
        prompt += "用户需求：" + user_input + "\n"
        prompt += "额外上下文：" + json.dumps(context, ensure_ascii=False)[:500] + "\n"
        prompt += "输出 JSON："
        return prompt

    # ========== 工具方法 ==========

    def _parse_dag_json(self, raw: str) -> Optional[Dict[str, Any]]:
        # 解析 LLM 返回文本中的 JSON，解析失败返回 None。
        if not raw:
            return None
        text = raw.strip()
        # 去除 markdown 代码围栏
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        try:
            dag = json.loads(text)
        except Exception:
            # 尝试截取第一个 { 到最后一个 }
            start, end = text.find("{"), text.rfind("}")
            if start >= 0 and end > start:
                try:
                    dag = json.loads(text[start : end + 1])
                except Exception:
                    return None
            else:
                return None
        if not isinstance(dag, dict) or not dag.get("nodes"):
            return None
        return dag

    def _format_message(self, template: str, user_input: str) -> str:
        # 将模板消息中的 {user_input} 占位符替换为实际输入。
        try:
            return template.format(user_input=user_input)
        except Exception:
            return template.replace("{user_input}", user_input)

    def _build_fallback_dag(self, user_input: str) -> Dict[str, Any]:
        # 构造通用兜底 DAG。
        dag = json.loads(json.dumps(_FALLBACK_DAG))
        for node in dag.get("nodes", []):
            node["message"] = self._format_message(node.get("message", ""), user_input)
        dag["edges"] = [["analyze", "execute"], ["execute", "summarize"]]
        return dag

    def _cache_key(self, user_input: str) -> str:
        # 生成缓存 key（去空白、统一小写）。
        return " ".join(user_input.split()).lower()[:200]

    # ========== 业务模板方法（基类 process 自动调用） ==========

    def _execute_business(self, user_input: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        # 业务入口：调用 plan 并包装为统一结果结构。
        dag = self.plan(user_input, context or {})
        return {
            "success": True,
            "action": "plan",
            "dag": dag,
            "output_content": "已生成 DAG 任务图（{0} 节点，来源 {1}）".format(
                len(dag.get("nodes", [])), dag.get("_meta", {}).get("source", "unknown")
            ),
            "response": json.dumps(dag, ensure_ascii=False),
        }


# 模块级便捷入口：供编排器直接调用
def create_planner(user_id: str = "default") -> PlannerAgent:
    return PlannerAgent(user_id=user_id)
