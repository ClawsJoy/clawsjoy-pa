"""引擎管理器 - 分层管理所有引擎"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class EngineManager:
    """引擎管理器 - 四层分类管理"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self._load_config()
        self._engines = {}
        self._load_engines()
        print(f"🔧 引擎管理器已初始化 (共 {len(self._engines)} 个引擎)")

    def _load_config(self):
        config_path = Path("config/engine_layers.yaml")
        if config_path.exists():
            with open(config_path) as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = {}

    def _load_engines(self):
        """加载所有引擎"""
        engine_names = []
        for layer in [
            "expression_layer",
            "decision_layer",
            "orchestration_layer",
            "execution_layer",
        ]:
            layer_config = self.config.get(layer, {})
            engines = layer_config.get("engines", [])
            engine_names.extend(engines)

        for name in engine_names:
            try:
                module = __import__(f"engine.{name}.core", fromlist=[f"{name}_engine"])
                if hasattr(module, f"{name}_engine"):
                    self._engines[name] = getattr(module, f"{name}_engine")
                    print(f"  ✅ 加载引擎: {name}")
                else:
                    print(f"  ⚠️ 引擎 {name} 未找到实例")
            except Exception as e:
                print(f"  ❌ 引擎 {name} 加载失败: {e}")

    def get_engine(self, name: str):
        """获取引擎"""
        return self._engines.get(name)

    def get_layer_engines(self, layer: str) -> List:
        """获取某层的所有引擎"""
        layer_config = self.config.get(layer, {})
        engines = []
        for name in layer_config.get("engines", []):
            if name in self._engines:
                engines.append(self._engines[name])
        return engines

    def get_all_engines(self) -> Dict:
        return self._engines

    def execute_chain(self, message: str, user_id: str, context: dict = None) -> dict:
        """
        执行引擎链 - 按优先级调用各层引擎处理消息

        Args:
            message: 用户消息
            user_id: 用户ID
            context: 上下文信息

        Returns:
            处理结果字典
        """
        context = context or {}

        # 按优先级获取引擎执行顺序
        priority_map = self.config.get("engine_priority", {})

        # 获取所有引擎并按优先级排序
        all_engines = self.get_all_engines()
        sorted_engines = sorted(all_engines.items(), key=lambda x: priority_map.get(x[0], 999))

        # 依次执行每个引擎（使用 handle 方法）
        for engine_name, engine in sorted_engines:
            if hasattr(engine, "handle"):
                try:
                    result = engine.handle(message, user_id, context)
                    if result and result.get("success"):
                        return result
                except Exception as e:
                    print(f"引擎 {engine_name} 执行失败: {e}")

        # 如果没有引擎处理，返回默认响应
        return {
            "success": False,
            "response": "无法处理您的请求，请稍后重试",
            "agent": "fallback",
            "user_id": user_id,
        }


engine_manager = EngineManager()
