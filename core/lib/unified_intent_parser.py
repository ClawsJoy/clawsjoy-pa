"""统一意图解析器 - 标准化 JSON v2.0（增强版）"""

import yaml
import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from string import Template
from typing import Dict, Any, Optional, List, Tuple

from core.lib.llm_client import llm_client


class UnifiedIntentParser:
    """统一意图解析器 - 输出标准化 JSON，关键词+LLM双路解析"""

    ACTIONS = ["play", "search", "generate", "schedule", "translate", "calculate", "chat", "analyze", "write", "remember", "recall"]
    TARGETS = ["media", "code", "image", "info", "task", "text", "number", "memory"]
    OUTPUT_TYPES = ["text", "image", "video", "link", "code"]
    STATUSES = ["pending", "processing", "completed", "failed"]
    NEXT_ACTIONS = ["continue", "done", "wait"]

    # 关键词匹配规则（快速路径，不调LLM）
    KEYWORD_RULES: List[Tuple[List[str], str, str, float]] = [
        (["代码", "编程", "写函数", "算法", "debug", "修复", "写一个"], "generate", "code", 0.90),
        (["翻译", "translate"], "translate", "text", 0.90),
        (["计算", "等于", "加", "减", "乘", "除", "算", "数学"], "calculate", "number", 0.90),
        (["分析", "统计", "趋势", "数据", "报告"], "analyze", "data", 0.85),
        (["写小说", "创作小说", "写故事", "写文章", "撰写", "写作"], "write", "text", 0.85),
        (["画图", "画画", "生成图", "图片", "图像"], "generate", "image", 0.85),
        (["视频", "剪辑", "制作视频", "短视频"], "generate", "media", 0.85),
        (["搜索", "查找", "找一下", "查一下"], "search", "info", 0.85),
        (["记住", "保存", "记一下", "记忆"], "remember", "memory", 0.90),
        (["回忆", "记得", "查询", "之前"], "recall", "memory", 0.85),
        (["待办", "提醒", "日程", "安排"], "schedule", "task", 0.85),
        (["播放", "放首歌", "音乐"], "play", "media", 0.85),
    ]

    def __init__(self, spec_path="config/prompt/unified_spec.yaml"):
        self.spec = self._load_spec(spec_path)
        self.llm = llm_client
        self.llm_model = "qwen2.5:7b-instruct-q4_0-gpu"
        self.prompt_template = self._load_prompt_template()

    def _load_spec(self, path: str) -> Dict:
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f)
        except Exception:
            return {}

    def _load_prompt_template(self) -> Template:
        prompt_path = Path("prompts/unified_intent.prompt")
        if prompt_path.exists():
            with open(prompt_path, 'r') as f:
                return Template(f.read())
        else:
            default_template = """
分析以下用户输入，输出 JSON 格式的意图解析结果。

用户输入：${raw_prompt}

可用动作：play, search, generate, schedule, translate, calculate, chat, analyze, write, remember, recall
可用目标：media, code, image, info, task, text, number, memory

输出格式：
{"action": "动作", "target": "目标", "keywords": ["关键词"], "confidence": 0.0-1.0}

只输出 JSON，不要其他内容。
"""
            return Template(default_template)

    def _generate_session_id(self) -> str:
        return str(uuid.uuid4())[:8]

    # ====================================================================
    #  主解析入口（双路：关键词快速路径 + LLM深度解析）
    # ====================================================================

    def parse(self, raw_input: str, user_id: str = "default",
              thread_id: str = None, session_id: str = None) -> Dict[str, Any]:
        """解析用户输入，输出标准化 JSON"""

        if not session_id:
            session_id = self._generate_session_id()
        if not thread_id:
            thread_id = self._generate_session_id()

        action = "chat"
        target = "text"
        keywords = []
        confidence = 0.5
        method = "default"

        # 第1步：关键词快速匹配（不调LLM，毫秒级）
        kw_action, kw_target, kw_conf, kw_keywords = self._keyword_match(raw_input)
        if kw_conf >= 0.85:
            action = kw_action
            target = kw_target
            confidence = kw_conf
            keywords = kw_keywords
            method = "keyword"

        # 第2步：关键词置信度不够，调LLM深度解析
        if method == "default":
            llm_result = self._llm_parse(raw_input)
            if llm_result:
                action = llm_result.get("action", action)
                target = llm_result.get("target", target)
                keywords = llm_result.get("keywords", keywords)
                confidence = llm_result.get("confidence", confidence)
                method = "llm"

        # 第3步：校验枚举值
        if action not in self.ACTIONS:
            action = "chat"
        if target not in self.TARGETS:
            target = "text"

        return {
            "version": "1.0",
            "session_id": session_id,
            "user_id": user_id,
            "thread_id": thread_id,
            "turn": 0,
            "raw_input": raw_input,
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "target": target,
            "keywords": keywords,
            "confidence": confidence,
            "params": {"parse_method": method},
            "output_type": "text",
            "output_content": "",
            "output_data": {},
            "status": "pending",
            "next": "continue"
        }

    # ====================================================================
    #  关键词匹配
    # ====================================================================

    def _keyword_match(self, text: str) -> Tuple[str, str, float, List[str]]:
        """关键词快速匹配，返回(action, target, confidence, keywords)"""
        t = text.lower()
        for keywords, action, target, confidence in self.KEYWORD_RULES:
            matched = [kw for kw in keywords if kw in t]
            if matched:
                return action, target, confidence, matched
        return "chat", "text", 0.0, []

    # ====================================================================
    #  LLM深度解析
    # ====================================================================

    def _llm_parse(self, raw_input: str) -> Optional[Dict]:
        """调用LLM进行意图解析"""
        prompt = self.prompt_template.substitute(raw_prompt=raw_input)

        try:
            result = self.llm.generate(
                prompt=prompt,
                model=self.llm_model,
                temperature=0.3,
                max_tokens=512,
                timeout=30,
                task_type="intent"
            )
            if result:
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    intent_data = json.loads(json_match.group())
                    if intent_data.get("action") or intent_data.get("target"):
                        return intent_data
        except Exception as e:
            print(f"LLM意图解析失败: {e}")

        return None

    # ====================================================================
    #  Agent路由
    # ====================================================================

    def get_agent_name(self, standardized_json: Dict) -> str:
        """根据标准化 JSON 获取 Agent 名称"""
        route_map = self.spec.get('route_map', {})
        action = standardized_json.get("action", "chat")
        target = standardized_json.get("target", "text")

        key = f"{action}_{target}"
        if key in route_map:
            return route_map[key]

        # 降级：按action映射
        action_map = {
            "generate": {"code": "code_agent", "image": "vision_agent",
                         "media": "video_agent", "text": "writer_agent"},
            "analyze": "analysis_agent",
            "translate": "translate_agent",
            "calculate": "calculator_agent",
            "search": "chat_agent",
            "remember": "memory_agent",
            "recall": "memory_agent",
            "schedule": "butler_agent",
            "play": "audio_agent",
            "write": "writer_agent",
            "chat": "chat_agent",
        }
        mapped = action_map.get(action, "chat_agent")
        if isinstance(mapped, dict):
            return mapped.get(target, "chat_agent")
        return mapped

    # ====================================================================
    #  响应构建
    # ====================================================================

    def complete(self, standardized_json: Dict, output_type: str,
                 output_content: str, output_data: Dict = None) -> Dict:
        """标记任务完成"""
        standardized_json["output_type"] = output_type
        standardized_json["output_content"] = output_content
        standardized_json["output_data"] = output_data or {}
        standardized_json["status"] = "completed"
        standardized_json["next"] = "done"
        return standardized_json

    def fail(self, standardized_json: Dict, error_msg: str) -> Dict:
        """标记任务失败"""
        standardized_json["status"] = "failed"
        standardized_json["output_content"] = error_msg
        standardized_json["next"] = "wait"
        return standardized_json


unified_parser = UnifiedIntentParser()
