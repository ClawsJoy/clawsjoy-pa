#!/usr/bin/env python3
"""
BusinessAgent v4.1 - LLM-First 业务基类

特点:
1. 缓存、批处理优化（保留）
2. 模型选择由 LLM 评估
3. 任务分解由 LLM 完成
4. 主动建议由 LLM 生成
5. 6GB 显存优化
"""

from typing import Dict, Optional, Any, Tuple, List
from abc import abstractmethod
import hashlib
import time
import re
import json
from datetime import datetime
from core.agents.base.smart_agent import SmartAgent
from core.agents.base.mixins.json_capable_mixin import JSONCapableMixin
from core.lib.federated.federated_learning import federated_learning
from core.lib.performance.optimizer import cache_manager, batch_processor, model_selector


class BusinessAgent(SmartAgent, JSONCapableMixin):
    # 🔧 所有 Agent 共享同一个记忆实例（跨 Agent 记忆共享）
    _shared_memory = None

    @classmethod
    def _get_shared_memory(cls):
        """获取共享的记忆实例"""
        if cls._shared_memory is None:
            try:
                from core.lib.memory_layers import MemoryLayers
                cls._shared_memory = MemoryLayers()
                print("🧠 BusinessAgent: 共享记忆实例已创建")
            except Exception as e:
                print(f"🧠 BusinessAgent: 共享记忆创建失败: {e}")
                cls._shared_memory = None
        return cls._shared_memory

    @property
    def memory(self):
        """返回共享的记忆实例（所有 Agent 共享）"""
        return self._get_shared_memory()



    @property
    def soul(self):
        if self._soul is None:
            try:
                from core.lib.soul.soul_injector import SoulInjector
                self._soul = SoulInjector(self.user_id, self.name)
            except Exception as e:
                print(f"[BusinessAgent] 加载灵魂注入器失败: {e}")
                self._soul = None
        return self._soul

    @property
    def context(self):
        if self._context is None:
            try:
                from core.lib.context_learner import ContextLearner
                self._context = ContextLearner()
            except Exception as e:
                print(f"[BusinessAgent] 加载上下文学习器失败: {e}")
                self._context = None
        return self._context

    def get_common_blocks(self) -> Dict:
        """获取所有通用积木（用于调试）"""
        return {
            "semantic": self.semantic is not None,
            "emotion": self.emotion is not None,
            "memory": self.memory is not None,
            "soul": self.soul is not None,
            "context": self.context is not None,
        }
    # ========== 缓存（保留）==========

    def _get_cache_key(self, user_input: str, context: Dict = None) -> str:
        key = user_input[:200]
        if context:
            key += str(sorted(context.items()))[:100]
        return hashlib.md5(key.encode()).hexdigest()

    def _get_from_cache(self, key: str) -> Optional[Dict]:
        if key in self._response_cache:
            self._stats["cache_hits"] += 1
            return self._response_cache[key]
        self._stats["cache_misses"] += 1
        return None

    def _save_to_cache(self, key: str, result: Dict):
        self._response_cache[key] = result
        if len(self._response_cache) > self._CACHE_SIZE:
            oldest = next(iter(self._response_cache))
            del self._response_cache[oldest]

    # ========== 批处理（保留）==========

    def add_to_batch(self, user_input: str, callback=None):
        self._pending_tasks.append({"input": user_input, "callback": callback, "timestamp": time.time()})
        if len(self._pending_tasks) >= self._BATCH_SIZE:
            self._process_batch()

    def _process_batch(self):
        if not self._pending_tasks:
            return

        batch = self._pending_tasks[:self._BATCH_SIZE]
        self._pending_tasks = self._pending_tasks[self._BATCH_SIZE:]

        inputs = [t["input"] for t in batch]
        if hasattr(self, '_execute_batch'):
            results = self._execute_batch(inputs)
        else:
            results = [self._execute_business(inp, None) for inp in inputs]

        self._stats["batch_processed"] += len(batch)

        for task, result in zip(batch, results):
            if task["callback"]:
                task["callback"](result)

        return results

    # ========== LLM-First 模型选择 ==========

    def _select_model(self, user_input: str) -> str:
        """根据输入复杂度选择模型"""
        from core.lib.llm_client import llm_client
        return llm_client.select_model(user_input)

    def _call_llm(self, prompt: str, model: str = None, task_type: str = "default") -> str:
        """委托给统一LLM客户端"""
        from core.lib.llm_client import llm_client
        return llm_client.generate(
            prompt=prompt,
            model=model,
            temperature=self._get_temperature(task_type),
            max_tokens=self._get_max_tokens(task_type),
            task_type=task_type
        )

    def _select_model(self, user_input: str) -> str:
        from core.lib.llm_client import llm_client
        return llm_client.select_model(user_input)

    def _get_temperature(self, task_type: str = "default") -> float:
        """根据任务类型返回温度"""
        if task_type == "intent":
            return 0.1
        elif task_type in ("code", "review", "analyze"):
            return 0.2
        return 0.7

    def _get_max_tokens(self, task_type: str = "default") -> int:
        """根据任务类型返回 max_tokens"""
        configs = {
            "outline": 4096,
            "chapter": 2048,
            "character": 2048,
            "polish": 8192,
            "intent": 50,
        }
        return configs.get(task_type, 2048)

    # ========== 核心方法 ==========

    def can_handle_json(self, action: str, target: str) -> Tuple[bool, float]:
        return False, 0.0

    @abstractmethod
    def _execute_business(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        pass

    def process(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        # 🔧 自动加载用户记忆，注入到上下文
        if context is None:
            context = {}
        
        shared_mem = self._get_shared_memory()
        if shared_mem:
            try:
                memories = []
                # 1. 获取长期记忆（包含用户名字等永久信息）
                long_term = shared_mem.get_long_term_memory(limit=10)
                if long_term:
                    memories.extend(long_term)
                # 2. 如果有 session_id，获取会话记忆
                session_id = context.get("session_id")
                if session_id:
                    session_mem = shared_mem.get_session_memory(session_id, limit=5)
                    if session_mem:
                        memories.extend(session_mem)
                if memories:
                    context["memories"] = memories
            except Exception as e:
                print(f"[BusinessAgent] 记忆加载失败: {e}")       
        # 如果有 memory 属性（共享实例），也保存到 context
        if hasattr(self, 'memory') and self.memory:
            context["_has_memory"] = True

        self._stats["total_interactions"] = self._stats.get("total_interactions", 0) + 1
        cache_key = hashlib.md5(f"{self.user_id}:{user_input}:{self.name}".encode()).hexdigest()

        cached = cache_manager.get(cache_key)
        if cached:
            self._stats["cache_hits"] = self._stats.get("cache_hits", 0) + 1
            return cached
        self._stats["cache_misses"] = self._stats.get("cache_misses", 0) + 1

        result = self._execute_business(user_input, context)
        cache_manager.set(cache_key, result)

        return result

    def handle(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        return self.process(user_input, context)

    def get_stats(self) -> Dict:
        stats = super().get_stats() if hasattr(super(), 'get_stats') else {}
        cache_hits = self._stats.get('cache_hits', 0)
        cache_misses = self._stats.get('cache_misses', 0)
        total = cache_hits + cache_misses
        cache_hit_rate = cache_hits / total if total > 0 else 0

        stats.update({
            "business": self._stats,
            "cache_hit_rate": cache_hit_rate,
            "cache_hits": cache_hits,
            "cache_misses": cache_misses
        })
        return stats

    # ========== 主动建议（由 LLM 生成）==========

    def _get_proactive_suggestions(self, user_input: str = None) -> list:
        """由 LLM 生成主动建议"""
        if not user_input:
            return []

        prompt = f"""根据用户历史对话，生成 2-3 条主动建议。

用户最近说：{user_input[:200]}

输出格式：每条建议一行，不要编号。
"""
        try:
            response = self._call_llm(prompt)
            if response:
                suggestions = [s.strip() for s in response.split('\n') if s.strip()]
                return suggestions[:3]
        except:
            pass

        return ["💡 有什么我可以帮您的吗？"]

    # ========== 任务分解（由 LLM 完成）==========

    def decompose_task(self, task: str, context: Dict = None) -> Dict:
        """由 LLM 动态分解任务"""
        prompt = f"""将以下任务分解为子任务，输出 JSON。

任务：{task}

输出格式：
{{"sub_tasks": [{{"id": 1, "action": "analyze", "target": "data", "description": "描述", "depends_on": []}}], "mode": "sequential"}}

可用的 action: analyze, generate, search, calculate, translate, chat, write, review, fix

只输出 JSON：
"""
        try:
            response = self._call_llm(prompt)
            if response:
                match = re.search(r'\{.*\}', response, re.DOTALL)
                if match:
                    result = json.loads(match.group())
                    if result.get("sub_tasks"):
                        return result
        except Exception as e:
            print(f"[DEBUG] 任务分解失败: {e}")

        # 降级：单任务
        return {"sub_tasks": [{"id": 1, "action": "process", "target": "task", "description": task, "depends_on": []}], "mode": "simple"}

    def execute_decomposed_task(self, decomposition: Dict, context: Dict = None) -> Dict:
        """执行分解后的任务"""
        results = []
        sub_tasks = decomposition.get("sub_tasks", [])
        mode = decomposition.get("mode", "sequential")

        if mode == "sequential":
            for task in sub_tasks:
                result = self._execute_sub_task_with_agent(task, context)
                results.append(result)
        elif mode == "parallel":
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(sub_tasks)) as executor:
                futures = {executor.submit(self._execute_sub_task_with_agent, task, context): task for task in sub_tasks}
                for future in concurrent.futures.as_completed(futures):
                    results.append(future.result())

        return self._merge_results(results)

    def _execute_sub_task_with_agent(self, task: Dict, context: Dict = None) -> Dict:
        action = task.get("action", "chat")
        target = task.get("target", "text")
        description = task.get("description", "")

        agent_mapping = {
            ("analyze", "data"): "analysis_agent",
            ("generate", "code"): "code_agent",
            ("calculate", "number"): "calculator_agent",
            ("translate", "text"): "translate_agent",
        }

        agent_name = agent_mapping.get((action, target), "chat_agent")
        sub_input = description if description else f"{action} {target}"

        try:
            from core.agents.wisdom.wisdom_factory import wisdom_factory
            sub_agent = wisdom_factory.get_wisdom_agent(agent_name, self.user_id)
            if sub_agent:
                result = sub_agent.process(sub_input)
                return {
                    "task_id": task.get("id"),
                    "action": action,
                    "target": target,
                    "agent": agent_name,
                    "success": result.get("success", False),
                    "output": result.get("response", result.get("output_content", "")),
                }
        except Exception as e:
            print(f"[DEBUG] 子任务执行失败: {e}")

        return {"task_id": task.get("id"), "action": action, "target": target, "agent": agent_name, "success": False, "output": f"执行失败: {e}"}

    def _merge_results(self, results: List[Dict]) -> Dict:
        success_count = sum(1 for r in results if r.get("success", False))
        total_count = len(results)

        outputs = []
        for r in results:
            content = r.get("output", "")
            if content:
                outputs.append(content)

        return {
            "success": success_count == total_count,
            "total_sub_tasks": total_count,
            "successful_sub_tasks": success_count,
            "results": results,
            "merged_output": "\n\n".join(outputs) if outputs else "",
        }

    # ========== 联邦学习 ==========

    def share_experience(self, experience: Dict):
        if not self._federated_enabled:
            return
        knowledge = {f"{experience.get('type', 'general')}": experience.get('result', '')}
        federated_learning.share_knowledge(self.name, knowledge, experience.get('confidence', 0.5))

    def query_peers(self, query: str) -> List[Dict]:
        if not self._federated_enabled:
            return []
        return federated_learning.query_knowledge(self.name, query)

        # ========== 统一记忆存储 ==========

    def _store_state(self, key: str, business: str, state: Dict, summary: str = "") -> bool:
        """
        统一记忆存储 - 子类调用此方法保存状态
        Args:
            key: 记忆键名，如 "writer_state"
            business: 业务域，如 "novel", "film", "code"
            state: 实际状态数据
            summary: 摘要（供其他 Agent 发现用）
        Returns:
            bool: 是否保存成功
        """
        if not self._session_id:
            return False
        if not self.memory:
            return False

        from datetime import datetime

        payload = {
            "version": "2.5",
            "business": business,
            "agent": getattr(self, 'name', 'unknown'),
            "capability": getattr(self, 'capability', 'unknown'),
            "state": state,
            "summary": summary or self._generate_summary(state),
            "timestamp": datetime.now().isoformat()
        }

        try:
            self.memory.add_session_memory(
                self._session_id,
                key,
                json.dumps(payload, ensure_ascii=False)
            )
            print(f"[{getattr(self, 'name', 'unknown')}] 💾 状态已保存: {key} ({business})")
            return True
        except Exception as e:
            print(f"[{getattr(self, 'name', 'unknown')}] 保存失败: {e}")
            return False

    def _generate_summary(self, state: Dict) -> str:
        """生成摘要（子类可覆盖）"""
        if not state:
            return ""
        title = state.get("title", "")
        if title:
            return title[:50]
        return ""

    def discover_agents(self, business: str = None, exclude_self: bool = True) -> List[Dict]:
        """
        发现同 session 中的其他 Agent
        Args:
            business: 过滤业务域，如 "novel", "film", "code"
            exclude_self: 是否排除自己
        Returns:
            List[Dict]: 发现的 Agent 列表
        """
        result = []
        if not self._session_id or not self.memory:
            return result

        try:
            memories = self.memory.get_session_memory(self._session_id, limit=50)
            current_agent = getattr(self, 'name', 'unknown')
            import json
            seen = set()  # ← 添加去重集合
            
            for mem in memories:
                if not isinstance(mem, dict):
                    continue

                assistant = mem.get("assistant", {})

                # 如果是 JSON 字符串，解析为字典
                if isinstance(assistant, str):
                    try:
                        assistant = json.loads(assistant)
                    except:
                        continue

                if not assistant:
                    continue

                agent_name = assistant.get("agent", "unknown")
                if exclude_self and agent_name == current_agent:
                    continue
                # ← 去重检查
                if agent_name in seen:
                    continue
                seen.add(agent_name)
                
                biz = assistant.get("business", "unknown")
                if business and biz != business:
                    continue

                if assistant.get("state"):
                    result.append({
                        "agent": agent_name,
                        "business": biz,
                        "capability": assistant.get("capability", "unknown"),
                        "summary": assistant.get("summary", ""),
                        "state": assistant.get("state", {}),
                        "timestamp": assistant.get("timestamp", "")
                    })
        except Exception as e:
            print(f"[{getattr(self, 'name', 'unknown')}] 发现 Agent 失败: {e}")

        return result
