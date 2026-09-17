"""视频处理的语义参数映射"""

import re


class VideoParamMapper:
    """自然语言到视频处理参数的映射"""

    BRIGHTNESS_MAP = {
        "太暗": 0.15,
        "暗一点": 0.1,
        "亮一点": -0.1,
        "太亮": -0.15,
        "更亮": -0.1,
        "更暗": 0.1,
    }

    CONTRAST_MAP = {
        "对比度不够": 0.15,
        "对比度太高": -0.15,
        "增强对比": 0.1,
        "降低对比": -0.1,
    }

    SATURATION_MAP = {
        "颜色太淡": 0.2,
        "颜色太浓": -0.2,
        "更鲜艳": 0.15,
        "淡一点": -0.15,
    }

    def parse(self, user_input: str) -> dict:
        """解析自然语言反馈，返回参数调整"""
        params = {
            "brightness": 0,
            "contrast": 0,
            "saturation": 0,
            "feedback": user_input,
        }

        # 亮度
        for phrase, value in self.BRIGHTNESS_MAP.items():
            if phrase in user_input:
                params["brightness"] = value
                break

        # 对比度
        for phrase, value in self.CONTRAST_MAP.items():
            if phrase in user_input:
                params["contrast"] = value
                break

        # 饱和度
        for phrase, value in self.SATURATION_MAP.items():
            if phrase in user_input:
                params["saturation"] = value
                break

        return params


if __name__ == "__main__":
    mapper = VideoParamMapper()
    tests = ["画面太暗", "对比度不够", "颜色太淡"]
    for test in tests:
        result = mapper.parse(test)
        print(f"{test} → {result}")
