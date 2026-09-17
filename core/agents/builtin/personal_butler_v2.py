#!/usr/bin/env python3
"""Personal Butler V2 - Personal Butler V2 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import json
from pathlib import Path
from typing import Any, Dict, Optional

from core.agents.base.smart_agent import SmartAgent


class PersonalButlerV2(SmartAgent):
    """私人管家 - 用户入口"""

    name = "personal_butler_v2"
    description = "智能私人管家"
    type = "core"
    version = "2.0.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        self.preferences: Dict[str, Any] = {}
        self.user_context: Dict[str, Any] = {}
        self._load_user_data()
        print(f"👤 私人管家 已启动 for {user_id}")

    def _load_user_data(self):
        """加载用户数据"""
        user_dir = Path(f"data/users/{self.user_id}")
        pref_file = user_dir / "butler_preferences.json"
        if pref_file.exists():
            try:
                with open(pref_file) as f:
                    data = json.load(f)
                    self.preferences = data.get("preferences", {})
                    self.user_context = data.get("context", {})
            except Exception as e:
                print(f"加载用户数据失败: {e}")

    def _save_user_data(self):
        """保存用户数据"""
        user_dir = Path(f"data/users/{self.user_id}")
        user_dir.mkdir(parents=True, exist_ok=True)
        pref_file = user_dir / "butler_preferences.json"
        try:
            with open(pref_file, "w") as f:
                json.dump(
                    {"preferences": self.preferences, "context": self.user_context},
                    f,
                    indent=2,
                )
        except Exception as e:
            print(f"保存用户数据失败: {e}")

    def process(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        """处理用户请求"""
        print(f"[管家] 收到: {user_input}")

        # 更新上下文
        if context:
            self.user_context.update(context)
            self._save_user_data()

        # 调用决策 Agent
        result = self.http_call("decision_agent", user_input)
        print(f"[管家] 返回: {result}")

        # 记录交互到俱乐部
        self._record_interaction()

        return result

    def get_user_context(self) -> Dict:
        """获取用户上下文"""
        return self.user_context

    def get_preferences(self) -> Dict:
        """获取用户偏好"""
        return self.preferences

    def set_preference(self, key: str, value: Any) -> bool:
        """设置用户偏好"""
        self.preferences[key] = value
        self._save_user_data()
        return True

    def remember(self, key: str, value: Any) -> bool:
        """记住信息"""
        self.user_context[key] = value
        self._save_user_data()
        return True

    def recall(self, key: str) -> Optional[Any]:
        """回忆信息"""
        return self.user_context.get(key)

    def _record_interaction(self):
        """记录交互到俱乐部"""
        try:
            from core.butler_club.center import butler_club

            butler_club.record_interaction(self.user_id)
        except Exception as e:
            print(f"记录交互失败: {e}")

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "name": self.name,
            "version": self.version,
            "user_id": self.user_id,
            "preferences_count": len(self.preferences),
            "context_size": len(self.user_context),
        }

    def get_preference(self, key: str, default=None):
        """获取单个偏好"""
        return self.preferences.get(key, default)


personal_butler = PersonalButlerV2()
