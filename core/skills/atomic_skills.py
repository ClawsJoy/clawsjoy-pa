#!/usr/bin/env python3
"""Atomic Skills - Atomic Skills 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import datetime
import json
import random
import re
from typing import Dict, Optional


class AtomicSkills:
    """原子技能处理器"""

    # 方言映射表
    DIALECT_MAP = {
        "粤语": {"你好": "你好", "谢谢": "唔该", "再见": "再见", "我是": "我係"},
        "上海话": {"你好": "侬好", "谢谢": "谢谢", "再见": "再会", "我是": "吾是"},
        "四川话": {"你好": "你好", "谢谢": "谢了", "再见": "拜拜", "我是": "我是"},
        "东北话": {"你好": "你好", "谢谢": "谢谢啊", "再见": "再见", "我是": "咱是"},
        "宁波话": {
            "你好": "侬好",
            "谢谢": "谢谢",
            "再见": "再会",
            "累死了": "要死嘞",
            "什么": "啥",
            "哪里": "阿里",
        },
    }

    # 天气城市列表
    WEATHER_CITIES = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "西安"]

    @classmethod
    def detect(cls, user_input: str) -> Optional[Dict]:
        """检测并执行原子技能"""
        user_lower = user_input.lower()

        # 1. 天气查询
        weather_match = re.search(r"([\u4e00-\u9fa5]{2,3})天气", user_input)
        if weather_match:
            city = weather_match.group(1)
            return cls.weather(city)

        if "天气" in user_input and "怎么样" in user_input:
            return cls.weather("北京")

        # 2. 方言转换
        dialect_match = re.search(r"用(.{2,3})说(.+)", user_input)
        if dialect_match:
            dialect = dialect_match.group(1)
            text = dialect_match.group(2)
            return cls.dialect(dialect, text)

        if "粤语" in user_input:
            return cls.dialect("粤语", user_input)

        # 3. 计算器
        calc_match = re.search(r"(\d+[\+\-\*\/]\d+)", user_input)
        if calc_match:
            return cls.calculator(calc_match.group(1))

        if "计算" in user_input:
            num_match = re.search(r"(\d+)\s*[\+\-\*\/]\s*(\d+)", user_input)
            if num_match:
                return cls.calculator(f"{num_match.group(1)}+{num_match.group(2)}")

        # 4. 时间日期
        if "时间" in user_input or "几点" in user_input:
            return cls.current_time()
        if "日期" in user_input or "今天" in user_input:
            return cls.current_date()

        return None

    @classmethod
    def weather(cls, city: str) -> Dict:
        """模拟天气查询"""
        weather_conditions = ["晴 ☀️", "多云 ⛅", "阴 ☁️", "小雨 🌧️", "中雨 ☔", "雪 ❄️"]
        return {
            "skill": "weather",
            "city": city,
            "result": f"{city}天气：{random.choice(weather_conditions)} {random.randint(-5, 35)}°C",
        }

    @classmethod
    def dialect(cls, dialect: str, text: str) -> Dict:
        """方言转换"""
        dialect_map = cls.DIALECT_MAP.get(dialect, {})
        converted = "".join(dialect_map.get(c, c) for c in text)
        return {
            "skill": "dialect",
            "dialect": dialect,
            "original": text,
            "converted": converted,
        }

    @classmethod
    def calculator(cls, expression: str) -> Dict:
        """简单计算器"""
        try:
            # 安全计算
            result = eval(expression)
            return {"skill": "calculator", "expression": expression, "result": result}
        except Exception as e:
            return {
                "skill": "calculator",
                "expression": expression,
                "error": "无法计算",
            }

    @classmethod
    def current_time(cls) -> Dict:
        """当前时间"""
        now = datetime.datetime.now()
        return {"skill": "time", "result": now.strftime("%H:%M:%S")}

    @classmethod
    def current_date(cls) -> Dict:
        """当前日期"""
        now = datetime.datetime.now()
        return {"skill": "date", "result": now.strftime("%Y年%m月%d日 %A")}
