"""技能懒加载管理器 - 按需加载技能，避免启动时全部加载"""

import importlib
import threading
from typing import Any, Dict, Optional


class SkillLazyLoader:
    """技能懒加载管理器 - 单例"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self):
        self._skills: Dict[str, Any] = {}
        self._loading: Dict[str, bool] = {}
        self._skill_names: list = []
        print("🔧 技能懒加载管理器已启动")

    def register_skill(self, skill_name: str):
        """注册技能名称（不加载）"""
        if skill_name not in self._skills and skill_name not in self._loading:
            self._skills[skill_name] = None
            self._skill_names.append(skill_name)

    def load_skill(self, skill_name: str) -> Optional[Any]:
        """按需加载技能"""
        if skill_name not in self._skills:
            self.register_skill(skill_name)

        if self._skills.get(skill_name) is not None:
            return self._skills[skill_name]

        if self._loading.get(skill_name):
            return None

        with self._lock:
            self._loading[skill_name] = True
            try:
                # 尝试加载技能模块
                module = importlib.import_module(f"skills.{skill_name}")
                if hasattr(module, "execute"):
                    self._skills[skill_name] = module
                    print(f"  ✅ 技能已加载: {skill_name}")
                else:
                    self._skills[skill_name] = None
            except Exception as e:
                print(f"  ❌ 技能加载失败 {skill_name}: {e}")
                self._skills[skill_name] = None
            finally:
                self._loading[skill_name] = False

        return self._skills[skill_name]

    def execute(self, skill_name: str, params: Dict = None) -> Dict:
        """执行技能（自动加载）"""
        skill = self.load_skill(skill_name)
        if skill and hasattr(skill, "execute"):
            return skill.execute(params or {})
        return {"success": False, "error": f"技能未找到或加载失败: {skill_name}"}

    def list_skills(self) -> list:
        """列出所有已注册技能（不触发加载）"""
        return self._skill_names.copy()

    def is_loaded(self, skill_name: str) -> bool:
        """检查技能是否已加载"""
        return self._skills.get(skill_name) is not None

    def unload_skill(self, skill_name: str):
        """卸载技能（释放内存）"""
        if skill_name in self._skills:
            del self._skills[skill_name]
        if skill_name in self._loading:
            del self._loading[skill_name]
        print(f"  🗑️ 技能已卸载: {skill_name}")


skill_lazy_loader = SkillLazyLoader()
