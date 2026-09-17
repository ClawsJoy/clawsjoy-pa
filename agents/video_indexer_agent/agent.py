#!/usr/bin/env python3
"""视频索引智能体 - 智能版"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from core.agents.business.business_agent_v2 import BusinessAgentV2


class VideoIndexerAgent(BusinessAgentV2):
    """视频索引智能体 - 支持视频分析、索引、搜索"""

    name = "video_indexer_agent"
    description = "视频索引与智能分析"
    version = "3.0.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        self.index_path = Path(f"data/users/{user_id}/video_index.json")
        self._load_index()
        print(f"📇 VideoIndexerAgent v{self.version} 已上线")

    def _load_index(self):
        """加载视频索引"""
        if self.index_path.exists():
            with open(self.index_path, encoding="utf-8") as f:
                self.index = json.load(f)
        else:
            self.index = {}

    def _save_index(self):
        """保存视频索引"""
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(self.index, f, indent=2)

    def _execute_business(self, user_input: str, context: dict = None) -> dict:
        return self.process(user_input, context)

    def process(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        """处理视频索引请求"""
        print(f"[视频索引] 分析: {user_input[:50]}...")

        input_lower = user_input.lower()

        # 使用语义引擎理解意图
        if hasattr(self, "call_engine"):
            result = self.call_engine("semantic", "understand", user_input)
            if result:
                intent = result.intent
                print(f"[视频索引] 语义意图: {intent}")

        if "索引" in input_lower or "index" in input_lower:
            return self._index_video(user_input)
        if "搜索" in input_lower or "search" in input_lower:
            return self._search_video(user_input)
        if "分析" in input_lower or "analyze" in input_lower:
            return self._analyze_video(user_input)
        if "列表" in input_lower or "list" in input_lower:
            return self._list_videos()

        return self._help()

    def _index_video(self, user_input: str) -> Dict:
        """索引视频"""
        import re

        path_match = re.search(r"(?:索引|index)[：:]?\s*(.+?)$", user_input)

        if path_match:
            video_path = path_match.group(1).strip()
            video_id = hashlib.md5(video_path.encode()).hexdigest()[:8]
            self.index[video_id] = {"path": video_path, "indexed_at": datetime.now().isoformat(), "status": "indexed"}
            self._save_index()
            return {"success": True, "response": f"✅ 已索引视频: {video_path}", "agent": self.name, "user_id": self.user_id}

        return {
            "success": True,
            "response": f"📊 已索引 {len(self.index)} 个视频",
            "agent": self.name,
            "user_id": self.user_id,
        }

    def _search_video(self, user_input: str) -> Dict:
        """搜索视频"""
        import re

        keyword_match = re.search(r"(?:搜索|search)[：:]?\s*(.+?)$", user_input)

        if keyword_match:
            keyword = keyword_match.group(1).strip()
            results = [v for v in self.index.values() if keyword in v.get("path", "")]

            if results:
                summary = f"🔍 找到 {len(results)} 个视频:\n" + "\n".join([f"- {r['path']}" for r in results])
                return {"success": True, "response": summary, "agent": self.name, "user_id": self.user_id}
            else:
                return {
                    "success": True,
                    "response": f"未找到包含 '{keyword}' 的视频",
                    "agent": self.name,
                    "user_id": self.user_id,
                }

        return {"success": True, "response": "请输入搜索关键词，例如：搜索 风景", "agent": self.name, "user_id": self.user_id}

    def _analyze_video(self, user_input: str) -> Dict:
        """分析视频内容"""
        import re

        path_match = re.search(r"(?:分析|analyze)[：:]?\s*(.+?)$", user_input)

        if path_match:
            video_path = path_match.group(1).strip()
            # 使用视觉引擎分析（如果有）
            analysis = "视频分析中..."
            if hasattr(self, "call_engine"):
                try:
                    result = self.call_engine("vision", "analyze", video_path)
                    if result:
                        analysis = result.get("description", "分析完成")
                except Exception:
                    pass

            return {"success": True, "response": f"🎥 视频分析结果: {analysis}", "agent": self.name, "user_id": self.user_id}

        return {"success": True, "response": "请指定要分析的视频路径", "agent": self.name, "user_id": self.user_id}

    def _list_videos(self) -> Dict:
        """列出所有索引的视频"""
        if not self.index:
            return {"success": True, "response": "暂无索引的视频", "agent": self.name, "user_id": self.user_id}

        summary = f"📹 共 {len(self.index)} 个索引视频:\n"
        for vid, info in list(self.index.items())[:10]:
            summary += f"- {info.get('path', vid)}\n"

        return {"success": True, "response": summary, "agent": self.name, "user_id": self.user_id}

    def _help(self) -> Dict:
        """帮助信息"""
        return {
            "success": True,
            "response": "🎬 视频索引功能：\n• 索引视频：索引 /path/to/video.mp4\n• 搜索视频：搜索 关键词\n• 分析视频：分析 /path/to/video.mp4\n• 列表视频：列表",
            "agent": self.name,
            "user_id": self.user_id,
        }
