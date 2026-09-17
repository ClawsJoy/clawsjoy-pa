#!/usr/bin/env python3
"""WeatherAgent v5.0 - 天气查询"""

import re
import json
import random
from typing import Dict, Optional, Tuple
from datetime import datetime

from core.agents.business.business_agent import BusinessAgent


class WeatherAgentV4(BusinessAgent):
    """天气助手 - 查询天气信息"""

    name = "weather_agent_v4"
    description = "智能天气助手"
    version = "5.0.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        print(f"🌤️ WeatherAgent v{self.version} 启动")

    def can_handle_json(self, action: str, target: str) -> Tuple[bool, float]:
        return (True, 0.9)

    def _execute_business(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        """执行天气查询"""
        # 提取城市
        city = self._extract_city(user_input)
        
        if not city:
            return self._resp("📍 请告诉我你想查询哪个城市的天气？")
        
        # 调用天气 API（这里用模拟数据）
        weather = self._get_weather(city)
        
        return self._resp(f"""
🌤️ **{city} 天气**

🌡️ 温度: {weather['temp']}°C
💧 湿度: {weather['humidity']}%
🌬️ 风速: {weather['wind']} km/h
☀️ 天气: {weather['condition']}

📅 更新时间: {weather['time']}
""")

    def _extract_city(self, text: str) -> Optional[str]:
        """提取城市名"""
        cities = ['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '南京', 
                  '重庆', '西安', '天津', '苏州', '郑州', '长沙', '东莞', '青岛']
        
        for city in cities:
            if city in text:
                return city
        
        if '天气' in text:
            return None
        
        return None

    def _get_weather(self, city: str) -> Dict:
        """获取天气（模拟数据）"""
        conditions = ['晴', '多云', '阴', '小雨', '中雨', '大雨', '雷阵雨', '雪']
        
        return {
            'city': city,
            'temp': round(random.uniform(-5, 35), 1),
            'humidity': random.randint(30, 90),
            'wind': round(random.uniform(0, 20), 1),
            'condition': random.choice(conditions),
            'time': datetime.now().strftime('%Y-%m-%d %H:%M')
        }

    def _resp(self, content: str, **kwargs) -> Dict:
        """标准响应格式"""
        return {"success": True, "response": content, "output_content": content, **kwargs}


if __name__ == "__main__":
    agent = WeatherAgentV4("test")
    result = agent.process("北京天气怎么样")
    print(result.get("response", ""))
