#!/usr/bin/env python3
"""VideoIndexerAgent v4.2 - 精简稳定版（视频索引）"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import re
from typing import Dict, Optional, Tuple

from core.agents.business.business_agent import BusinessAgent


class VideoIndexerAgentV4(BusinessAgent):
    """视频索引 Agent - 精简稳定版"""

    name = "video_indexer_agent_v4"
    description = "智慧视频索引助手"
    version = "5.0.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        self._index = {}
        print(f"📹 VideoIndexerAgent v{self.version} 启动")

    def can_handle_json(self, action: str, target: str) -> Tuple[bool, float]:
        return (True, 0.85)

    def _execute_business(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        t = user_input.lower()
        
        if any(kw in t for kw in ["索引", "添加视频"]):
            return self._index_video(user_input)
        
        if any(kw in t for kw in ["搜索视频", "查找视频"]):
            return self._search_video(user_input)
        
        return self._resp("📹 输入「索引视频 教程」或「搜索视频 关键词」")

    # ================================================================
    #  索引视频
    # ================================================================

    def _index_video(self, user_input: str) -> Dict:
        content = re.sub(r'(索引视频|添加视频)', '', user_input).strip()
        if not content:
            content = "视频"
        
        result = self._call_llm(f"为「{content}」生成索引标签（关键词、分类、时长、人群）")
        return self._resp(f"📹 视频索引\n\n{result or self._index_template(content)}")

    def _index_template(self, content: str) -> str:
        return f"""
视频：{content}

🏷 标签：主题词、难度、场景
📂 分类：教程/娱乐/资讯
💡 提示：接入 Azure Video Indexer 可获得专业分析
"""

    # ================================================================
    #  搜索视频
    # ================================================================

    def _search_video(self, user_input: str) -> Dict:
        keyword = re.sub(r'(搜索视频|查找视频)', '', user_input).strip()
        if not keyword:
            return self._resp("请提供关键词。示例：搜索视频 Python教程")
        
        result = self._call_llm(f"推荐与「{keyword}」相关的视频类型和内容")
        return self._resp(f"🔍 视频搜索\n\n关键词：{keyword}\n\n{result or '推荐：教程类、讲解类、实战类'}")

    # ================================================================
    #  辅助
    # ================================================================
    def _resp(self, content: str, **kwargs) -> Dict:
        return {"success": True, "response": content, "output_content": content, **kwargs}


if __name__ == "__main__":
    agent = VideoIndexerAgentV4("test")
    print(agent.process("索引视频 Python教程")["response"])
