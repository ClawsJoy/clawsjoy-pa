#!/usr/bin/env python3
"""统一对话引擎 v2.0 - 基于统一LLM客户端 + 持久化记忆"""

import json
import logging
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

from core.lib.llm_client import llm_client
from core.lib.vector_knowledge_center import vector_knowledge_center
from core.lib.unified_config import unified_config

logger = logging.getLogger(__name__)


class PersistentMemory:
    """内嵌持久化记忆"""

    def __init__(self, storage_dir="data/memories"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def get_user_info(self, user_id: str) -> Dict:
        user_file = self.storage_dir / f"{user_id}.json"
        if user_file.exists():
            try:
                with open(user_file, 'r') as f:
                    data = json.load(f)
                    return {
                        'name': data.get('name', ''),
                        'preferences': data.get('preferences', [])
                    }
            except Exception:
                pass
        return {'name': '', 'preferences': []}

    def load_context(self, user_id: str, last_n: int = 5) -> str:
        user_file = self.storage_dir / f"{user_id}.json"
        if not user_file.exists():
            return ""
        try:
            with open(user_file, 'r') as f:
                data = json.load(f)
            conversations = data.get('conversations', [])
            if not conversations:
                return ""
            context = "【历史对话】\n"
            for conv in conversations[-last_n:]:
                context += f"用户: {conv.get('user', '')}\n"
                context += f"助手: {conv.get('assistant', '')}\n"
            return context
        except Exception:
            return ""

    def save_conversation(self, user_id: str, user_msg: str, assistant_msg: str):
        user_file = self.storage_dir / f"{user_id}.json"
        data = {}
        if user_file.exists():
            try:
                with open(user_file, 'r') as f:
                    data = json.load(f)
            except Exception:
                pass
        if 'conversations' not in data:
            data['conversations'] = []
        data['conversations'].append({
            'user': user_msg[:200],
            'assistant': assistant_msg[:200],
            'timestamp': datetime.now().isoformat()
        })
        if len(data['conversations']) > 50:
            data['conversations'] = data['conversations'][-50:]
        with open(user_file, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def save(self, user_id: str, data: dict):
        """保存用户记忆数据到 JSON 文件"""
        user_file = self.storage_dir / f"{user_id}.json"
        try:
            with open(user_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"PersistentMemory.save failed for user {user_id}: {e}")

    def load(self, user_id: str) -> dict:
        """从 JSON 文件加载用户记忆数据，失败时返回空 dict 保证无副作用"""
        user_file = self.storage_dir / f"{user_id}.json"
        if not user_file.exists():
            return {}
        try:
            with open(user_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"PersistentMemory.load failed for user {user_id}: {e}")
            return {}


class UnifiedChatEngine:
    """统一对话引擎 - 基于 llm_client"""

    def __init__(self):
        self.llm = llm_client
        self.llm_model = "qwen2:1.5b-instruct"
        self.conversations: Dict[str, List[Dict]] = defaultdict(list)
        self.user_profiles: Dict[str, Dict] = defaultdict(dict)
        self._cache: Dict[str, tuple] = {}
        self._cache_ttl = 300
        self.persistent_memory = PersistentMemory()
        logger.info("✅ ChatEngine v2.0 初始化完成")

    # ====================================================================
    #  缓存
    # ====================================================================

    def _cache_get(self, key: str) -> Optional[str]:
        import time
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return value
            del self._cache[key]
        return None

    def _cache_set(self, key: str, value: str):
        import time
        self._cache[key] = (value, time.time())
        if len(self._cache) > 500:
            oldest = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest]

    # ====================================================================
    #  用户信息提取
    # ====================================================================

    def _extract_user_info(self, user_id: str, message: str):
        profile = self.user_profiles.get(user_id, {})
        name_match = re.search(r'我叫([^，,。]+)', message)
        if name_match:
            profile['name'] = name_match.group(1).strip()
        pref_match = re.search(r'我喜欢([^，,。]+)', message)
        if pref_match:
            if 'preferences' not in profile:
                profile['preferences'] = []
            profile['preferences'].append(pref_match.group(1).strip())
        self.user_profiles[user_id] = profile

    def _load_persistent_memory(self, user_id: str):
        user_info = self.persistent_memory.get_user_info(user_id)
        if user_info.get('name'):
            self.user_profiles[user_id]['name'] = user_info['name']
        if user_info.get('preferences'):
            self.user_profiles[user_id]['preferences'] = user_info['preferences']

    # ====================================================================
    #  上下文构建
    # ====================================================================

    def _build_context(self, user_id: str, message: str,
                       standard_json: Dict = None) -> str:
        history = self.conversations.get(user_id, [])
        profile = self.user_profiles.get(user_id, {})
        user_info = self.persistent_memory.get_user_info(user_id)
        parts = []

        if standard_json:
            params = standard_json.get("params", {})
            context = params.get("context", {})
            soul_context = context.get("soul", {})
            if soul_context and soul_context.get("user_known"):
                parts.append(soul_context.get("user_known"))

        known_name = None
        for source in [profile, user_info]:
            if source.get("name") and not known_name:
                known_name = source.get("name")
                parts.append(f"用户姓名: {known_name}")

        prefs = []
        if profile.get("preferences"):
            prefs.extend(profile["preferences"])
        if user_info.get("preferences"):
            prefs.extend(user_info["preferences"])
        if prefs:
            parts.append(f"用户偏好: {', '.join(set(prefs))}")

        for h in history[-6:]:
            parts.append(f"{h['role']}: {h['content']}")

        parts.append(f"用户: {message}")
        return "\n".join(parts)

    # ====================================================================
    #  主执行入口
    # ====================================================================

    def execute(self, message: Union[str, Dict],
                user_id: str = "guest") -> Dict:
        # 解析输入
        raw_input = ""
        standard_json = None
        params = {}

        if isinstance(message, str):
            raw_input = message
        else:
            standard_json = message
            raw_input = standard_json.get("raw_input",
                                          message.get("message", ""))
            params = standard_json.get("params", {})
            user_id = standard_json.get("user_id", user_id)

        if not raw_input:
            raw_input = message.get("raw_input", "") if isinstance(message, dict) else str(message)

        # 提取上下文
        context = params.get("context", {})
        memories = context.get("memories", [])
        emotion = context.get("emotion", {})
        soul = context.get("soul", {})

        # 构建增强消息
        enhanced_message = raw_input
        if memories:
            memory_text = "\n".join(
                [f"【记忆】{m.get('user', '')[:50]}" for m in memories[-3:]]
            )
            enhanced_message = f"{enhanced_message}\n\n{memory_text}"
        if emotion and emotion.get("dominant_emotion"):
            enhanced_message = f"[情绪: {emotion['dominant_emotion']}] {enhanced_message}"
        if soul and soul.get("user_known"):
            enhanced_message = f"{soul['user_known']} {enhanced_message}"

        logger.info(f"处理 {user_id}: {raw_input[:40]}...")

        # 加载持久化记忆
        self._load_persistent_memory(user_id)

        # 构建上下文
        context_str = self._build_context(user_id, enhanced_message, standard_json)

        # 意图识别
        from core.lib.config_driven_router import config_router
        intent_result = config_router.route(raw_input)
        intent = intent_result.get('intent', 'chat')

        # 检查缓存
        is_simple = len(raw_input) < 80 and "我叫" not in raw_input and "喜欢" not in raw_input
        if is_simple:
            cached = self._cache_get(raw_input)
            if cached:
                logger.info(f"⚡ 缓存命中: {raw_input[:30]}")
                return self._build_response(
                    standard_json=standard_json,
                    output_content=cached,
                    output_data={"cached": True, "agent": "cached"}
                )

        # ========== 使用统一 LLM 客户端 ==========
        try:
            response = self.llm.generate(
                prompt=context_str,
                model=self.llm_model,
                temperature=0.7,
                max_tokens=256,
                task_type="chat"
            )
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            return self._build_response(
                standard_json=standard_json,
                output_content="服务暂时不可用，请稍后重试",
                status="failed",
                output_data={"error": str(e)}
            )

        if not response:
            return self._build_response(
                standard_json=standard_json,
                output_content="抱歉，我暂时无法处理。",
                status="failed",
                output_data={"error": "empty_response"}
            )

        # 保存历史
        self.conversations[user_id].append({"role": "user", "content": raw_input})
        self.conversations[user_id].append({"role": "assistant", "content": response})
        if len(self.conversations[user_id]) > 20:
            self.conversations[user_id] = self.conversations[user_id][-20:]

        # 持久化
        self.persistent_memory.save_conversation(user_id, raw_input, response)

        # 缓存
        if is_simple:
            self._cache_set(raw_input, response)

        return self._build_response(
            standard_json=standard_json,
            output_content=response,
            output_data={
                "agent": "chat_engine",
                "intent": intent,
                "memories_used": len(memories)
            }
        )

    # ====================================================================
    #  响应构建
    # ====================================================================

    def _build_response(self, standard_json: Dict, output_content: str,
                        status: str = "completed",
                        output_data: Dict = None) -> Dict:
        if output_data is None:
            output_data = {}

        if standard_json:
            return {
                "version": "2.5",
                "session_id": standard_json.get("session_id"),
                "user_id": standard_json.get("user_id"),
                "thread_id": standard_json.get("thread_id"),
                "turn": standard_json.get("turn", 0) + 1,
                "raw_input": standard_json.get("raw_input", ""),
                "timestamp": datetime.now().isoformat(),
                "action": standard_json.get("action", "chat"),
                "target": standard_json.get("target", "text"),
                "keywords": standard_json.get("keywords", []),
                "confidence": standard_json.get("confidence", 0.85),
                "params": standard_json.get("params", {}),
                "output_type": "text",
                "output_content": output_content,
                "output_data": output_data,
                "status": status,
                "next": "done"
            }
        else:
            return {
                "version": "2.5",
                "session_id": None,
                "user_id": "guest",
                "thread_id": None,
                "turn": 0,
                "raw_input": "",
                "timestamp": datetime.now().isoformat(),
                "action": "chat",
                "target": "text",
                "keywords": [],
                "confidence": 0.5,
                "params": {},
                "output_type": "text",
                "output_content": output_content,
                "output_data": output_data,
                "status": status,
                "next": "done"
            }

    def _add_reasoning_chain(self, question: str, answer: str) -> str:
        if any(op in question for op in ['+', '-', '*', '/', '计算', '等于']):
            return f"【解题步骤】\n1. 分析问题：{question}\n2. 逐步计算\n3. 得出结果\n\n{answer}"
        if any(word in question for word in ['如果', '那么', '因为', '所以', '推理']):
            return f"【逻辑推理】\n前提条件分析\n    ↓\n逻辑推导\n    ↓\n得出结论\n\n{answer}"
        return answer

    def _get_agent_instance(self, agent_name: str):
        """动态获取Agent（通过 agent_v4）"""
        try:
            mod = __import__(f"agents.{agent_name}.agent_v4", fromlist=["*"])
            for attr in dir(mod):
                if attr.endswith("V4") and hasattr(getattr(mod, attr), 'process'):
                    return getattr(mod, attr)()
        except ImportError:
            pass
        return None


chat_engine = UnifiedChatEngine()
