"""LLM 引擎 - 首次预热60秒，稳定输出，认知系统所有组件"""

import json
import re
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from engine.semantic.engines.base import BaseEngine


class LLMEngine(BaseEngine):
    """
    LLM 引擎 - 最智能，认知系统所有组件

    设计哲学:
    1. 首次预热60秒（模型加载到GPU）
    2. 稳定输出，不被击穿（熔断器+重试）
    3. 认知系统：从配置动态加载所有Agent/技能/话本
    """

    def __init__(self):
        self._name = "llm"
        self._priority = 1
        self._enabled = False
        self._ready = False
        self._warming_up = False
        self._warmup_status = "未启动"
        self._model = "qwen2.5:7b-instruct-q4_0-gpu"
        self._client = None
        self._system_context = None
        self._circuit_breaker = {"failures": 0, "open_until": 0}
        self._confidence_threshold = 0.7
        self._init()

    @property
    def name(self) -> str:
        return self._name

    @property
    def priority(self) -> int:
        return self._priority

    def _build_system_context(self) -> str:
        """构建系统上下文 - 让LLM认知整个系统"""
        context_parts = []

        # 1. 从 intents 加载
        try:
            from core.lib.unified_config import unified_config

            intents = unified_config.get("keywords.intents", {})
            if intents:
                intent_list = "\n".join(
                    [
                        f"    - {name}: {', '.join(config.get('keywords', [])[:5])}"
                        for name, config in list(intents.items())[:20]
                    ]
                )
                context_parts.append(f"系统意图:\n{intent_list}")
        except Exception as e:
            pass

        # 2. 从 agent_capabilities 加载
        try:
            from core.lib.unified_config import unified_config

            caps = unified_config.get("keywords.agent_capabilities", {})
            if caps:
                agent_list = "\n".join(
                    [
                        f"    - {name}: {', '.join(config.get('capable_of', [])[:3])}"
                        for name, config in list(caps.items())[:20]
                    ]
                )
                context_parts.append(f"可用Agent:\n{agent_list}")
        except Exception as e:
            pass

        # 3. 从 skills 目录加载
        skills_dir = Path("skills")
        if skills_dir.exists():
            skills = [d.name for d in skills_dir.iterdir() if d.is_dir() and not d.name.startswith("_")]
            if skills:
                context_parts.append(f"原子技能: {', '.join(skills[:30])}")

        # 4. 从 agents 目录加载
        agents_dir = Path("agents")
        if agents_dir.exists():
            agents = [d.name for d in agents_dir.iterdir() if d.is_dir() and not d.name.startswith("_")]
            if agents:
                context_parts.append(f"专业Agent: {', '.join(agents[:20])}")

        return "\n\n".join(context_parts)

    def _init(self):
        """初始化LLM引擎 - 使用智能适配器"""
        try:
            import requests

            self._client = requests.Session()

            # 使用智能适配器获取推荐模型
            try:
                from core.lib.smart_adapter import smart_adapter

                # 检测任务类型
                task_type = smart_adapter.detect_task_type("通用对话")
                # 获取适配器推荐的模型
                model_config = smart_adapter.get_recommended_model(task_type)
                if model_config:
                    self._model = model_config.get("model", self._model)
                    print(f"✅ 智能适配器推荐模型: {self._model}")
            except Exception as e:
                pass

            resp = self._client.get("http://localhost:11434/api/tags", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                model_names = [m["name"] for m in models]

                # 检查模型是否可用
                if self._model in model_names:
                    self._enabled = True
                    print(f"✅ LLM 引擎已启用: {self._model}")
                    print(f"   正在构建系统上下文...")
                    self._system_context = self._build_system_context()
                    print(f"   系统上下文已加载")
                    self._warmup_async()
                else:
                    # 尝试其他模型
                    fallback_models = [
                        "llama3.2:3b",
                        "qwen2.5:7b-instruct-q4_0-gpu",
                        "deepseek-coder:6.7b",
                    ]
                    for fb in fallback_models:
                        if fb in model_names:
                            self._model = fb
                            self._enabled = True
                            print(f"✅ LLM 引擎使用备用模型: {self._model}")
                            self._system_context = self._build_system_context()
                            self._warmup_async()
                            return
                    print(f"⚠️ 模型不可用，请安装: ollama pull {self._model}")
            else:
                print("⚠️ Ollama 服务未响应")
        except Exception as e:
            print(f"⚠️ LLM 引擎初始化失败: {e}")

    def _warmup_async(self):
        """异步预热（不阻塞启动）"""
        if self._warming_up:
            return
        self._warming_up = True
        threading.Thread(target=self._warmup, daemon=True).start()

    def _warmup(self):
        """预热模型（首次60秒）"""
        self._warmup_status = "预热中"
        print(f"🔥 LLM 引擎预热中（首次约 30-60 秒）...")
        start = time.time()
        try:
            self._call_llm("你好", timeout=60)
            self._ready = True
            elapsed = time.time() - start
            self._warmup_status = f"已完成，耗时 {elapsed:.1f} 秒"
        except Exception as e:
            print(f"⚠️ LLM 引擎预热失败: {e}")
        finally:
            self._warming_up = False
        self._warmup_status = "未启动"

    def _call_llm(self, text: str, timeout: int = 10) -> Optional[Tuple[str, float]]:
        """调用LLM，带熔断器"""
        # 熔断器检查
        if self._circuit_breaker["open_until"] > time.time():
            return None

        prompt = f"""
{self._system_context}

用户输入: {text}

请分析用户意图，返回JSON格式:
{{"intent": "意图名称", "confidence": 0.0-1.0}}
"""

        try:
            response = self._client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self._model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 128},
                },
                timeout=timeout,
            )
            if response.status_code == 200:
                # 重置熔断器
                self._circuit_breaker["failures"] = 0
                result = response.json()
                text_result = result.get("response", "")
                json_match = re.search(r"\{[^{}]*\}", text_result)
                if json_match:
                    data = json.loads(json_match.group())
                    intent = data.get("intent", "unknown")
                    confidence = min(data.get("confidence", 0.5), 0.95)
                    return intent, confidence
        except Exception as e:
            # 记录失败
            self._circuit_breaker["failures"] += 1
            if self._circuit_breaker["failures"] >= 3:
                self._circuit_breaker["open_until"] = time.time() + 60
                print(f"⚠️ LLM 熔断器触发，冷却60秒")

        return None

    def is_available(self) -> bool:
        return self._enabled and self._ready

    def is_warming(self) -> bool:
        return self._warming_up

    def understand(self, text: str) -> Tuple[str, float, Dict]:
        """LLM理解 - 最智能"""
        if not self.is_available():
            return (
                "unknown",
                0.0,
                {"error": "LLM not ready", "warming": self._warming_up},
            )

        start_time = time.time()
        result = self._call_llm(text, timeout=10)
        latency = (time.time() - start_time) * 1000

        if result:
            intent, confidence = result
            if confidence >= self._confidence_threshold:
                return (
                    intent,
                    confidence,
                    {"latency_ms": latency, "source": "llm", "model": self._model},
                )

        return "unknown", 0.0, {"source": "llm", "error": "low confidence or failed"}

    def refresh_context(self) -> Dict:
        """刷新系统上下文（配置变更时调用）"""
        self._system_context = self._build_system_context()
        return {"success": True, "context_length": len(self._system_context)}

    def get_stats(self) -> Dict:
        return {
            "name": self.name,
            "priority": self.priority,
            "enabled": self._enabled,
            "ready": self._ready,
            "warming": self._warming_up,
            "model": self._model,
            "circuit_breaker_open": self._circuit_breaker["open_until"] > time.time(),
        }

    def get_warmup_status(self) -> str:
        """获取预热状态"""
        if self._ready:
            return "已就绪"
        if self._warming_up:
            return "预热中"
        return "未启动"

    def get_capabilities(self) -> Dict:
        return self.get_stats()


llm_engine = LLMEngine()
