"""合成数据生成器 - 无数据时生成训练样本"""

import json
import random
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from engine.lib.logger import engine_logger


class SyntheticGenerator:
    """合成数据生成器"""

    def __init__(self):
        self.templates = self._load_templates()
        self.generated_data = {}
        self.data_file = Path("data/synthetic_training.json")
        engine_logger.get().info("🎲 合成数据生成器已初始化")

    def _load_templates(self) -> Dict:
        return {
            "code": {
                "templates": [
                    "写一个{function}函数",
                    "帮我写{code_type}代码",
                    "实现{algorithm}算法",
                ],
                "variables": {
                    "function": ["排序", "查找", "计算", "解析"],
                    "code_type": ["Python", "JavaScript", "Java"],
                    "algorithm": ["快速排序", "二分查找", "递归"],
                },
            },
            "weather": {
                "templates": [
                    "{city}天气怎么样",
                    "今天{city}气温多少",
                    "{city}会下雨吗",
                ],
                "variables": {"city": ["北京", "上海", "广州", "深圳", "杭州"]},
            },
            "translate": {
                "templates": [
                    "把{text}翻译成{target_lang}",
                    "翻译{text}到{target_lang}",
                ],
                "variables": {
                    "text": ["hello", "good morning", "thank you"],
                    "target_lang": ["中文", "英文", "日文"],
                },
            },
            "calculate": {
                "templates": ["{a}{operator}{b}等于多少", "计算{a}{operator}{b}"],
                "variables": {
                    "a": list(range(1, 50)),
                    "b": list(range(1, 50)),
                    "operator": ["+", "-", "*", "/", "加", "减", "乘", "除"],
                },
            },
            "greeting": {
                "templates": ["{greeting}"],
                "variables": {"greeting": ["你好", "您好", "hi", "hello", "在吗"]},
            },
            "name_set": {
                "templates": ["我叫{name}", "名字叫{name}", "我是{name}"],
                "variables": {"name": ["张三", "李四", "王五", "赵六"]},
            },
        }

    def generate(self, intent: str, count: int = 10) -> List[str]:
        if intent not in self.templates:
            return []
        config = self.templates[intent]
        generated = []
        for _ in range(count):
            template = random.choice(config["templates"])
            filled = template
            for var_name, var_values in config["variables"].items():
                placeholder = f"{{{var_name}}}"
                if placeholder in filled:
                    value = random.choice(var_values)
                    filled = filled.replace(placeholder, str(value))
            generated.append(filled)
        return generated

    def generate_all(self, samples_per_intent: int = 20) -> Dict[str, List[str]]:
        result = {}
        for intent in self.templates.keys():
            result[intent] = self.generate(intent, samples_per_intent)
        self.generated_data = result
        with open(self.data_file, "w") as f:
            json.dump(
                {
                    "generated_at": datetime.now().isoformat(),
                    "data": result,
                    "stats": {k: len(v) for k, v in result.items()},
                },
                f,
                indent=2,
            )
        engine_logger.get().info(
            f"   ✅ 生成 {sum(len(v) for v in result.values())} 条合成数据"
        )
        return result

    def process(self, input_data: Any = None, **kwargs) -> Any:
        """处理输入 - 统一接口"""
        if input_data is None:
            return self.get_stats()
        if isinstance(input_data, str):
            return self.generate(input_data, kwargs.get("count", 5))
        if isinstance(input_data, dict):
            intent = input_data.get("intent", "code")
            count = input_data.get("count", 10)
            return self.generate(intent, count)
        return self.get_stats()

    def get_stats(self) -> Dict:
        return {
            "intents": len(self.templates),
            "generated": sum(len(v) for v in self.generated_data.values()),
        }


synthetic_generator = SyntheticGenerator()
