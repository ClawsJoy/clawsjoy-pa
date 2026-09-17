"""语义理解引擎 v8.0 - 增强版（优先级链 + 熔断 + 指标）"""

from datetime import datetime
from typing import Any, Dict, List

from engine.lib.logger import engine_logger
from engine.semantic.engine_config import engine_config


class IntentResult:
    """语义理解结果 - 增强版"""

    def __init__(
        self,
        intent: str,
        confidence: float,
        entities: dict = None,
        source: str = "unknown",
        engine: str = "",
        raw_text: str = "",
        latency_ms: float = 0,
        metadata: dict = None,
    ):
        self.intent = intent
        self.confidence = confidence
        self.entities = entities or {}
        self.source = source
        self.engine = engine
        self.raw_text = raw_text
        self.latency_ms = latency_ms
        self.metadata = metadata or {}
        self.timestamp = datetime.now()

    def __repr__(self):
        return f"IntentResult({self.intent}, {self.confidence:.2f}, {self.engine}, {self.latency_ms:.0f}ms)"


class SemanticEngine:
    """语义理解引擎 v8.0 - 增强版"""

    def __init__(self):
        self._engines: List[Any] = []
        self._circuit_breakers = {}  # 熔断器
        self._total_requests = 0
        self._success_requests = 0
        self._init_engines()
        engine_logger.get().info("🧠 语义理解引擎 v8.0 增强版已初始化")

    def _init_engines(self):
        engine_classes = [
            ("llm", "LLMEngine"),
            ("vector", "VectorEngine"),
            ("config", "ConfigEngine"),
            ("rule", "RuleEngine"),
        ]

        for module_name, class_name in engine_classes:
            try:
                module = __import__(
                    f"engine.semantic.engines.{module_name}_engine",
                    fromlist=[class_name],
                )
                engine_class = getattr(module, class_name)
                engine = engine_class()
                self._engines.append(engine)
                self._circuit_breakers[engine.name] = {"failures": 0, "open": False}
                engine_logger.get().info(
                    f"   ✅ {engine.name} (priority={engine.priority})"
                )
            except Exception as e:
                engine_logger.get().warning(f"   ⚠️ {module_name} 加载失败: {e}")

        self._engines.sort(key=lambda e: e.priority)

    def _is_circuit_open(self, engine_name: str) -> bool:
        cb = self._circuit_breakers.get(engine_name, {})
        if cb.get("open", False):
            return True
        return False

    def _record_failure(self, engine_name: str):
        cb = self._circuit_breakers.get(engine_name, {"failures": 0})
        cb["failures"] += 1
        if cb["failures"] >= 10:
            cb["open"] = True
            engine_logger.get().warning(f"🔌 熔断器触发: {engine_name}")
        self._circuit_breakers[engine_name] = cb

    def _record_success(self, engine_name: str):
        cb = self._circuit_breakers.get(engine_name, {"failures": 0})
        cb["failures"] = max(0, cb["failures"] - 1)
        if cb["failures"] < 5:
            cb["open"] = False
        self._circuit_breakers[engine_name] = cb

    def understand(self, text: str) -> IntentResult:
        import time

        start_time = time.time()
        self._total_requests += 1

        if not text:
            return IntentResult("unknown", 0.0, source="empty", latency_ms=0)

        for engine in self._engines:
            if not engine.is_available():
                continue
            if self._is_circuit_open(engine.name):
                engine_logger.get().warning(f"⏭️ 跳过熔断引擎: {engine.name}")
                continue

            try:
                engine_start = time.time()
                intent, confidence, metadata = engine.understand(text)
                engine_latency = (time.time() - engine_start) * 1000

                if confidence >= 0.3 and intent != "unknown":
                    self._record_success(engine.name)
                    self._success_requests += 1
                    return IntentResult(
                        intent=intent,
                        confidence=confidence,
                        source=engine.name,
                        engine=engine.name,
                        raw_text=text,
                        latency_ms=engine_latency,
                        metadata=metadata,
                    )
                else:
                    self._record_failure(engine.name)
            except Exception as e:
                engine_logger.get().warning(f"引擎 {engine.name} 失败: {e}")
                self._record_failure(engine.name)
                continue

        return IntentResult(
            "unknown", 0.0, source="none", latency_ms=(time.time() - start_time) * 1000
        )

    def reload(self) -> Dict:
        for engine in self._engines:
            if hasattr(engine, "reload"):
                engine.reload()
        return {"success": True, "message": "Semantic engine reloaded"}

    def get_engines_status(self) -> Dict:
        status = {}
        for engine in self._engines:
            caps = engine.get_capabilities()
            caps["circuit_breaker"] = self._circuit_breakers.get(engine.name, {})
            if hasattr(engine, "get_stats"):
                caps["stats"] = engine.get_stats()
            status[engine.name] = caps
        return status

    def get_stats(self) -> Dict:
        success_rate = (
            self._success_requests / self._total_requests
            if self._total_requests > 0
            else 0
        )
        return {
            "status": "active",
            "version": "8.0.0",
            "total_requests": self._total_requests,
            "success_requests": self._success_requests,
            "success_rate": f"{success_rate:.2%}",
            "engines": self.get_engines_status(),
        }

    def health_check(self) -> Dict:
        return {
            "name": "semantic_engine",
            "version": "8.0.0",
            "status": "healthy",
            "engines_count": len(self._engines),
            "total_requests": self._total_requests,
        }

    def process(self, input_data: Any, **kwargs) -> Any:
        return self.understand(str(input_data))


semantic_engine = SemanticEngine()
