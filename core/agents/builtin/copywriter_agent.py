#!/usr/bin/env python3
"""Copywriter Agent - Copywriter Agent 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

import random
from typing import Dict, Optional

from core.agents.base.smart_agent import SmartAgent


class CopywriterAgent(SmartAgent):
    """文案专家 Agent"""

    name = "copywriter_agent"
    description = "文案创作专家"
    type = "core"

    def on_init(self):
        """初始化"""
        self.log("文案专家 Agent 初始化完成")

    def process(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        """处理用户请求"""
        self._update_stats()

        # 简单响应
        if "广告语" in user_input or "slogan" in user_input.lower():
            response = self._generate_slogan(user_input)
        elif "产品描述" in user_input or "产品介绍" in user_input:
            response = self._generate_product_desc(user_input)
        elif "朋友圈" in user_input or "社交媒体" in user_input:
            response = self._generate_social_post(user_input)
        else:
            response = self._help_message()

        self.record_interaction(user_input, response)

        return {"success": True, "response": response, "user_id": self.user_id}

    def _generate_slogan(self, user_input: str) -> str:
        """生成广告语"""
        templates = [
            "智能{product}，开启{benefit}新体验",
            "{product}，{feature}之选",
            "让{product}，成就{value}",
        ]

        product = "产品"
        if "产品是" in user_input:
            product = user_input.split("产品是")[-1].strip()[:20]

        benefit = "美好"
        feature = "智能"
        value = "不凡"

        template = random.choice(templates)
        return template.format(
            product=product, benefit=benefit, feature=feature, value=value
        )

    def _generate_product_desc(self, user_input: str) -> str:
        """生成产品描述"""
        templates = [
            "全新{product}，采用{tech}技术，带来{benefit}的体验。",
            "{product}，{feature}升级，{benefit}触手可及。",
        ]

        product = "产品"
        if "产品是" in user_input:
            product = user_input.split("产品是")[-1].strip()[:20]

        template = random.choice(templates)
        return template.format(
            product=product, tech="AI", feature="智能", benefit="卓越"
        )

    def _generate_social_post(self, user_input: str) -> str:
        """生成社交媒体文案"""
        templates = [
            "🔥 新品来袭！{product}，{feature}体验\n#好物分享",
            "💡 推荐一款好物：{product}\n{benefit}，值得拥有！",
        ]

        product = "好物"
        if "产品是" in user_input:
            product = user_input.split("产品是")[-1].strip()[:20]

        template = random.choice(templates)
        return template.format(product=product, feature="智能", benefit="品质生活")

    def _help_message(self) -> str:
        """帮助信息"""
        return """我是文案专家，可以帮你：
📝 写广告语 - 说"写个广告语"
📝 产品描述 - 说"产品描述"
📝 朋友圈文案 - 说"朋友圈文案"

试试告诉我你的需求！"""
