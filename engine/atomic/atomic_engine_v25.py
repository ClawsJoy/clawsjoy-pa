# engine/atomic/atomic_engine_v25.py - 改造版
"""原子引擎 v2.5 - 基于 StandardJSON 协议"""

import uuid
import logging
from datetime import datetime
from typing import Dict, Union, Optional

from core.lib.json_standard import StandardJSON, Workflow, Condition
from core.lib.json_builder import StandardJSONBuilder

logger = logging.getLogger(__name__)


class AtomicEngineV25:
    """原子引擎 - 唯一入口，全程使用 StandardJSON"""
    VERSION = "2.5"

    def __init__(self):
        self._bridge = None
        self._init_bridge()
        logger.info(f"⚛️ 原子引擎 v{self.VERSION} 启动 (StandardJSON)")

    def _init_bridge(self):
        try:
            from core.lib.v25_unified_bridge import v25_bridge
            self._bridge = v25_bridge
        except Exception as e:
            logger.warning(f"统一桥梁初始化失败: {e}")
            self._bridge = None

    # ========== 统一入口 ==========

    def process(self, input_data: Union[str, Dict, StandardJSON]) -> Dict:
        """统一处理入口"""
        try:
            # 1. 统一解析为 StandardJSON
            if isinstance(input_data, str):
                request = StandardJSONBuilder().simple("chat", "text", input_data).build()
            elif isinstance(input_data, StandardJSON):
                request = input_data
            elif isinstance(input_data, dict):
                request = StandardJSON.from_dict(input_data)
            else:
                return {"error": "不支持的类型", "status": "failed"}

            # 2. 路由执行
            result = self._route(request)

            # 3. 返回字典（兼容现有接口）
            return self._to_response_dict(request, result)

        except Exception as e:
            logger.error(f"原子引擎处理失败: {e}", exc_info=True)
            return {
                "version": self.VERSION,
                "output_content": f"处理失败: {str(e)}",
                "status": "failed",
                "error": str(e)
            }

    # ========== 路由 ==========

    def _route(self, request: StandardJSON) -> Dict:
        """根据 action 路由到处理器"""
        handlers = {
            "chat":        self._handle_agent,
            "code":        self._handle_agent,
            "write":       self._handle_agent,
            "calculate":   self._handle_agent,
            "translate":   self._handle_agent,
            "analyze":     self._handle_agent,
            "file":        self._handle_agent,
            "orchestrate": self._handle_agent,
            "memory":      self._handle_memory,
            "tool":        self._handle_tool,
            "skill":       self._handle_skill,
        }

        handler = handlers.get(request.action, self._handle_agent)
        try:
            return handler(request)
        except Exception as e:
            logger.error(f"处理器 {request.action} 失败: {e}", exc_info=True)
            return {"success": False, "error": str(e), "response": f"处理失败: {e}"}

    # ========== Agent 处理器（通用） ==========

    def _handle_agent(self, request: StandardJSON) -> Dict:
        """通用Agent调用"""
        agent_map = {
            "chat":        "chat_agent",
            "code":        "code_agent",
            "write":       "writer_agent",
            "calculate":   "calculator_agent",
            "translate":   "translate_agent",
            "analyze":     "analysis_agent",
            "file":        "file_agent",
            "orchestrate": "orchestrator",
        }

        agent_name = agent_map.get(request.action, "chat_agent")
        return self._call_agent(agent_name, request)

    def _call_agent(self, agent_name: str, request: StandardJSON) -> Dict:
        """统一Agent调用"""
        try:
            from core.agents.wisdom.wisdom_factory import wisdom_factory
            agent = wisdom_factory.get_wisdom_agent(agent_name, request.user_id or "default")
            if not agent:
                return {"success": False, "error": f"Agent {agent_name} 不可用"}

            # Agent通过 JSONCapableMixin 处理 StandardJSON
            if hasattr(agent, 'handle_json'):
                return agent.handle_json(request)
            elif hasattr(agent, 'process'):
                return agent.process(request.raw_input, {
                    "session_id": request.session_id,
                    "user_id": request.user_id
                })
        except Exception as e:
            logger.error(f"调用Agent {agent_name} 失败: {e}")
            return {"success": False, "error": str(e)}

    # ========== Memory处理器 ==========

    def _handle_memory(self, request: StandardJSON) -> Dict:
        if self._bridge:
            params = request.params
            user_id = request.user_id or "default"
            if request.target == "remember":
                return self._bridge.remember(user_id, params.get("key"), params.get("value"), request.session_id)
            elif request.target == "recall":
                return self._bridge.recall(user_id, params.get("key"), request.session_id)
        return {"error": "记忆系统不可用"}

    # ========== Tool处理器 ==========

    def _handle_tool(self, request: StandardJSON) -> Dict:
        if self._bridge:
            params = request.params
            return self._bridge.execute_tool(
                request.user_id or "default",
                params.get("tool", ""),
                params.get("tool_params", {}),
                request.session_id
            )
        return {"error": "工具系统不可用"}

    # ========== Skill处理器 ==========

    def _handle_skill(self, request: StandardJSON) -> Dict:
        try:
            from core.lib.skill_recommender import skill_recommender
            params = request.params
            action = params.get("skill_action", "list")
            if action == "list":
                return skill_recommender.get_available_skills()
            elif action == "install":
                return skill_recommender.install(params.get("skill_name", ""), request.user_id)
            else:
                return skill_recommender.recommend(request.raw_input, request.user_id)
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ========== 响应构建 ==========

    def _to_response_dict(self, request: StandardJSON, result: Dict) -> Dict:
        """将结果包装为兼容的字典格式"""
        response = {
            "version": self.VERSION,
            "session_id": request.session_id,
            "user_id": request.user_id,
            "thread_id": request.thread_id,
            "turn": request.turn + 1,
            "raw_input": request.raw_input,
            "timestamp": datetime.now().isoformat(),
            "action": request.action,
            "target": request.target,
            "status": "completed" if result.get("success", True) else "failed",
            "output_content": result.get("response", result.get("output_content", "")),
            "output_data": {},
        }

        # 安全拷贝 output_data
        for key in ["agent", "intent", "memories_used", "routed", "detected_emotion"]:
            if key in result:
                response["output_data"][key] = result[key]

        return response

    def get_capabilities(self) -> Dict:
        return {
            "version": self.VERSION,
            "name": "atomic_engine_v25_standard_json",
            "handlers": ["chat", "code", "write", "memory", "tool", "skill",
                        "calculate", "translate", "analyze", "file", "orchestrate"]
        }


# 全局实例
atomic_engine = AtomicEngineV25()
