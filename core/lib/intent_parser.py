#!/usr/bin/env python3
"""Intent Parser - Intent Parser 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""自然语言意图解析器 - 增强版"""


class IntentParser:
    INTENT_PATTERNS = {
        "脚本生成": {
            "keywords": [
                "生成脚本",
                "写脚本",
                "视频脚本",
                "脚本创作",
                "帮我写脚本",
                "写一个脚本",
            ],
            "skills": ["youtube_agent"],
            "priority": 30,
        },
        "内容日历": {
            "keywords": [
                "日历",
                "排期",
                "内容日历",
                "查看日历",
                "发布日历",
                "内容排期",
            ],
            "skills": ["director_agent"],
            "priority": 25,
        },
        "生产状态": {
            "keywords": ["生产状态", "制作进度", "进度查询", "状态", "当前进度"],
            "skills": ["director_agent"],
            "priority": 25,
        },
        "导演策划": {
            "keywords": ["策划", "导演", "内容规划", "拍摄计划", "系列策划"],
            "skills": ["director_agent"],
            "priority": 25,
        },
        "脚本生成": {
            "keywords": [
                "生成脚本",
                "写脚本",
                "视频脚本",
                "脚本创作",
                "帮我写脚本",
                "写一个脚本",
            ],
            "skills": ["youtube_agent"],
            "priority": 30,
        },
        "内容日历": {
            "keywords": [
                "日历",
                "排期",
                "内容日历",
                "查看日历",
                "发布日历",
                "内容排期",
            ],
            "skills": ["director_agent"],
            "priority": 25,
        },
        "生产状态": {
            "keywords": ["生产状态", "制作进度", "进度查询", "状态", "当前进度"],
            "skills": ["director_agent"],
            "priority": 25,
        },
        "导演策划": {
            "keywords": ["策划", "导演", "内容规划", "拍摄计划", "系列策划"],
            "skills": ["director_agent"],
            "priority": 25,
        },
        "脚本生成": {
            "keywords": [
                "生成脚本",
                "写脚本",
                "视频脚本",
                "脚本创作",
                "帮我写脚本",
                "写一个脚本",
            ],
            "skills": ["youtube_agent"],
            "priority": 30,
        },
        "内容日历": {
            "keywords": [
                "日历",
                "排期",
                "内容日历",
                "查看日历",
                "发布日历",
                "内容排期",
            ],
            "skills": ["director_agent"],
            "priority": 25,
        },
        "生产状态": {
            "keywords": ["生产状态", "制作进度", "进度查询", "状态", "当前进度"],
            "skills": ["director_agent"],
            "priority": 25,
        },
        "导演策划": {
            "keywords": ["策划", "导演", "内容规划", "拍摄计划", "系列策划"],
            "skills": ["director_agent"],
            "priority": 25,
        },
        "脚本生成": {
            "keywords": [
                "生成脚本",
                "写脚本",
                "视频脚本",
                "脚本创作",
                "帮我写脚本",
                "写一个脚本",
            ],
            "skills": ["youtube_agent"],
            "priority": 30,
        },
        "内容日历": {
            "keywords": [
                "日历",
                "排期",
                "内容日历",
                "查看日历",
                "发布日历",
                "内容排期",
            ],
            "skills": ["director_agent"],
            "priority": 25,
        },
        "生产状态": {
            "keywords": ["生产状态", "制作进度", "进度查询", "状态", "当前进度"],
            "skills": ["director_agent"],
            "priority": 25,
        },
        "导演策划": {
            "keywords": ["策划", "导演", "内容规划", "拍摄计划", "系列策划"],
            "skills": ["director_agent"],
            "priority": 25,
        },
        "代码编写": {
            "keywords": [
                "写代码",
                "编程",
                "代码",
                "python",
                "java",
                "javascript",
                "函数",
                "算法",
                "开发",
                "写个程序",
                "帮我写",
                "代码能力",
            ],
            "skills": ["code_agent"],
            "priority": 30,
        },
        "天气查询": {
            "keywords": [
                "天气",
                "气温",
                "预报",
                "温度",
                "下雨",
                "晴天",
                "阴天",
                "气象",
                "会不会下雨",
                "今天天气",
            ],
            "skills": ["weather_skill", "weather"],
            "priority": 25,
        },
        "翻译": {
            "keywords": [
                "翻译",
                "译成",
                "怎么读",
                "英文怎么说",
                "中文翻译",
                "translate",
            ],
            "skills": ["translate_agent", "translate"],
            "priority": 20,
        },
        "计算": {
            "keywords": [
                "计算",
                "加法",
                "减法",
                "乘法",
                "除法",
                "加",
                "减",
                "乘",
                "除",
                "等于",
                "多少",
                "求和",
            ],
            "skills": ["calculator", "math"],
            "priority": 25,
        },
        "名字记忆": {
            "keywords": ["我叫", "名字叫", "称为", "我是", "我的名字是"],
            "skills": ["chat_agent"],
            "priority": 15,
        },
        "名字查询": {
            "keywords": ["我叫什么", "我的名字", "我名字", "我叫啥", "我是谁"],
            "skills": ["chat_agent"],
            "priority": 20,
        },
        "问候": {
            "keywords": [
                "你好",
                "您好",
                "hi",
                "hello",
                "在吗",
                "早上好",
                "晚上好",
                "下午好",
            ],
            "skills": ["chat_agent"],
            "priority": 10,
        },
        "感谢": {
            "keywords": ["谢谢", "感谢", "多谢", "thanks", "thx"],
            "skills": ["chat_agent"],
            "priority": 10,
        },
        "视频制作": {
            "keywords": ["视频", "漫剧", "制作", "生成视频", "做视频"],
            "skills": ["manju_maker", "complete_video_maker"],
        },
        "数学计算": {
            "keywords": ["计算", "加法", "乘法", "统计", "加", "减", "乘", "除"],
            "skills": ["add", "multiply", "statistics"],
        },
        "文本处理": {
            "keywords": ["大小写", "反转", "文字", "字符串", "文本"],
            "skills": ["to_upper", "reverse", "count_words"],
        },
        "日程管理": {
            "keywords": ["提醒", "日程", "会议", "待办", "任务", "计划"],
            "skills": ["add_event", "set_reminder", "add_todo"],
        },
        "视频上传": {
            "keywords": ["上传", "发布", "分享视频"],
            "skills": ["video_uploader"],
        },
        "添加字幕": {
            "keywords": ["字幕", "添加字幕", "加字幕"],
            "skills": ["add_subtitles"],
        },
    }

    @classmethod
    def parse(cls, user_input: str) -> dict:
        user_input_lower = user_input.lower()

        # 按优先级匹配
        for intent, config in cls.INTENT_PATTERNS.items():
            for keyword in config["keywords"]:
                if keyword in user_input_lower:
                    return {
                        "intent": intent,
                        "skills": config["skills"],
                        "confidence": 1.0,
                        "message": f"识别到{intent}意图",
                    }

        # 默认返回
        return {
            "intent": "general",
            "skills": ["get_time"],
            "confidence": 0.3,
            "message": "未识别明确意图，执行默认操作",
        }

    @classmethod
    def get_intent(cls, user_input: str) -> str:
        return cls.parse(user_input)["intent"]


intent_parser = IntentParser()
