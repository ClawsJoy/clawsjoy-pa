"""引擎管理器 - 统一管理所有原子引擎"""

import importlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class EngineManager:
    """引擎管理器"""

    def __init__(self):
        self.engines: Dict[str, Any] = {}
        self._discover_engines()

    def _discover_engines(self):
        """发现所有引擎"""
        engine_dir = Path(__file__).parent

        for subdir in engine_dir.iterdir():
            if not subdir.is_dir() or subdir.name.startswith("_"):
                continue
            if subdir.name in ["base", "lib", "events", "generator", "workflows"]:
                continue

            try:
                module = importlib.import_module(f"engine.{subdir.name}.core")
                # 查找引擎实例
                for name in dir(module):
                    if name.endswith("_engine") and not name.startswith("_"):
                        engine = getattr(module, name)
                        self.engines[subdir.name] = engine
                        print(f"   ✅ 发现引擎: {subdir.name}")
            except Exception as e:
                print(f"   ⚠️ 跳过 {subdir.name}: {e}")

    def get(self, name: str) -> Optional[Any]:
        """获取引擎"""
        return self.engines.get(name)

    def list(self) -> List[str]:
        """列出所有引擎"""
        return list(self.engines.keys())

    def reload_all(self) -> Dict:
        """重载所有引擎"""
        results = {}
        for name, engine in self.engines.items():
            if hasattr(engine, "reload"):
                try:
                    results[name] = engine.reload()
                except Exception as e:
                    results[name] = {"error": str(e)}
            else:
                results[name] = {"message": "No reload method"}
        return results

    def get_all_stats(self) -> Dict:
        """获取所有引擎统计"""
        stats = {}
        for name, engine in self.engines.items():
            if hasattr(engine, "get_stats"):
                try:
                    stats[name] = engine.get_stats()
                except Exception as e:
                    stats[name] = {"error": "Cannot get stats"}
        return stats


engine_manager = EngineManager()
