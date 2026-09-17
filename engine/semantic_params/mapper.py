"""自然语言到视频参数的语义映射"""

import re
from typing import Dict, Tuple


class SemanticParamMapper:
    """语义参数映射器"""

    # 参数语义映射
    PARAM_SEMANTICS = {
        "brightness": {
            "keywords": ["亮", "暗", "曝光", "亮度"],
            "increase": ["亮一点", "更亮", "加亮", "提高亮度"],
            "decrease": ["暗一点", "更暗", "降低亮度"],
            "range": (-0.5, 0.5),
            "default_step": 0.1,
        },
        "contrast": {
            "keywords": ["对比", "反差", "层次"],
            "increase": ["对比强一点", "更鲜明"],
            "decrease": ["对比弱一点", "柔和"],
            "range": (0.5, 1.5),
            "default_step": 0.1,
        },
        "saturation": {
            "keywords": ["饱和", "鲜艳", "颜色", "色彩"],
            "increase": ["更鲜艳", "色彩浓", "饱和度高"],
            "decrease": ["淡一点", "色彩淡", "饱和度低"],
            "range": (0, 2.0),
            "default_step": 0.15,
        },
        "sharpness": {
            "keywords": ["锐度", "清晰", "模糊"],
            "increase": ["更清晰", "锐化"],
            "decrease": ["柔化", "模糊一点"],
            "range": (0, 2.0),
            "default_step": 0.2,
        },
        "temperature": {
            "keywords": ["色温", "冷暖", "色调"],
            "increase": ["暖一点", "偏暖", "暖色调"],
            "decrease": ["冷一点", "偏冷", "冷色调"],
            "range": (0.8, 1.2),
            "default_step": 0.05,
        },
    }

    def parse(self, feedback: str) -> Dict:
        """解析自然语言反馈，返回参数调整"""
        result = {}

        for param, config in self.PARAM_SEMANTICS.items():
            value = self._extract_value(feedback, config)
            if value is not None:
                result[param] = value

        return result

    def _extract_value(self, feedback: str, config: Dict) -> float:
        """提取参数调整值"""
        feedback_lower = feedback.lower()

        # 判断方向
        direction = 0
        for inc in config.get("increase", []):
            if inc in feedback_lower:
                direction = 1
                break
        for dec in config.get("decrease", []):
            if dec in feedback_lower:
                direction = -1
                break

        if direction == 0:
            # 检查关键词
            for kw in config.get("keywords", []):
                if kw in feedback_lower:
                    direction = 1  # 默认增加
                    break

        if direction == 0:
            return None

        # 判断强度
        intensity = 1.0
        if "一点" in feedback or "稍微" in feedback or "微调" in feedback:
            intensity = 0.5
        elif "很多" in feedback or "非常" in feedback or "太" in feedback:
            intensity = 1.5
        elif "极度" in feedback or "最" in feedback:
            intensity = 2.0

        step = config.get("default_step", 0.1)
        value = direction * step * intensity

        # 限制范围
        min_val, max_val = config.get("range", (-1, 1))
        return max(min_val, min(max_val, value))


class FeedbackLearner:
    """反馈学习器 - 记住用户偏好"""

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.preferences = {}  # 用户偏好历史
        self.history = []  # 调整历史

    def record(self, feedback: str, adjustments: Dict, success: bool):
        """记录一次调整"""
        self.history.append(
            {
                "feedback": feedback,
                "adjustments": adjustments,
                "success": success,
                "timestamp": __import__("datetime").datetime.now().isoformat(),
            }
        )

        # 更新偏好（简单平均）
        for param, value in adjustments.items():
            if param not in self.preferences:
                self.preferences[param] = []
            self.preferences[param].append(value)

    def get_preference(self, param: str) -> float:
        """获取用户对该参数的偏好"""
        if param not in self.preferences or not self.preferences[param]:
            return 0
        return sum(self.preferences[param]) / len(self.preferences[param])


if __name__ == "__main__":
    mapper = SemanticParamMapper()

    tests = [
        "画面太暗了",
        "亮一点",
        "颜色太淡了，更鲜艳一些",
        "对比度不够，层次感差",
        "太模糊了，需要更清晰",
        "冷一点，现在偏暖",
    ]

    print("=== 语义参数映射测试 ===")
    for test in tests:
        result = mapper.parse(test)
        print(f"{test} → {result}")
