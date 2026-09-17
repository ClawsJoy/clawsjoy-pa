"""完整资讯服务模块 - 集成所有第三方 API"""

import os
import requests
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()


class NewsService:
    """统一资讯服务"""
    
    def __init__(self):
        # 网易 API
        self.netease_url = os.getenv("NETEASE_API_URL", "https://api.163.com")
        self.api_key = os.getenv("NETEASE_API_KEY", "")
        
        # IT之家 API
        self.ithome_url = os.getenv("ITHOME_API_URL", "https://api.ithome.com")
        
        # 热搜 API
        self.hotsearch_url = os.getenv("HOTSEARCH_API_URL", "https://api.hotsearch.com")
        self.trending_url = os.getenv("TRENDING_API_URL", "https://api.trending.com")
        
        # 体育 API
        self.sports_url = os.getenv("SPORTS_API_URL", "https://api.sports.com")
        
        # AI API
        self.ai_url = os.getenv("AI_API_URL", "https://api.ai.com")
        
        # 互联网 API
        self.internet_url = os.getenv("INTERNET_API_URL", "https://api.internet.com")
        
        self.enabled = bool(self.api_key)
        print("✅ 完整资讯服务已启用" if self.enabled else "⚠️ 资讯服务未配置")
    
    def _fetch(self, url: str, params: dict = None) -> dict:
        """通用请求"""
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            pass
        return {}
    
    def _parse_response(self, data: dict, limit: int) -> list:
        """解析响应数据"""
        if data.get("code") == 200:
            newslist = data.get("result", {}).get("newslist", [])
            return newslist[:limit]
        return []
    
    # ========== 网易系列 ==========
    def get_netease_news(self, category: str = "internet", limit: int = 10) -> List[Dict]:
        """获取网易新闻（互联网/科技）"""
        url = f"{self.netease_url}/{category}"
        data = self._fetch(url, {"limit": limit})
        return self._parse_response(data, limit)
    
    def get_internet_news(self, limit: int = 10) -> List[Dict]:
        """互联网资讯"""
        return self.get_netease_news("internet", limit)
    
    def get_tech_news(self, limit: int = 10) -> List[Dict]:
        """科技资讯"""
        return self.get_netease_news("tech", limit)
    
    # ========== IT之家系列 ==========
    def get_ithome_news(self, category: str = "news", limit: int = 10) -> List[Dict]:
        """IT之家新闻"""
        url = f"{self.ithome_url}/{category}"
        data = self._fetch(url, {"limit": limit})
        return self._parse_response(data, limit)
    
    def get_ai_news(self, limit: int = 10) -> List[Dict]:
        """人工智能资讯"""
        url = f"{self.ai_url}/news"
        data = self._fetch(url, {"limit": limit})
        return self._parse_response(data, limit)
    
    def get_science_news(self, limit: int = 10) -> List[Dict]:
        """科学探索"""
        url = f"{self.ithome_url}/science"
        data = self._fetch(url, {"limit": limit})
        return self._parse_response(data, limit)
    
    # ========== 热搜系列 ==========
    def get_hot_search(self, limit: int = 10) -> List[Dict]:
        """全网热搜榜"""
        data = self._fetch(self.hotsearch_url, {"limit": limit})
        if data.get("code") == 200:
            return data.get("result", {}).get("list", [])[:limit]
        return []
    
    def get_trending(self, limit: int = 10) -> List[Dict]:
        """头条热搜榜"""
        data = self._fetch(self.trending_url, {"limit": limit})
        if data.get("code") == 200:
            return data.get("result", {}).get("list", [])[:limit]
        return []
    
    # ========== 体育 ==========
    def get_sports_news(self, limit: int = 10) -> List[Dict]:
        """体育资讯"""
        data = self._fetch(self.sports_url, {"limit": limit})
        return self._parse_response(data, limit)
    
    # ========== 综合搜索 ==========
    def search(self, keyword: str, limit: int = 10) -> List[Dict]:
        """综合搜索"""
        all_results = []
        
        # 从多个源搜索
        sources = [
            ("互联网", self.get_internet_news(5)),
            ("科技", self.get_tech_news(5)),
            ("AI", self.get_ai_news(5)),
            ("科学", self.get_science_news(5)),
        ]
        
        for source_name, results in sources:
            for r in results:
                if keyword.lower() in r.get("title", "").lower():
                    r["source_category"] = source_name
                    all_results.append(r)
        
        return all_results[:limit]
    
    # ========== 获取所有资讯 ==========
    def get_all_news(self, limit: int = 5) -> Dict:
        """获取所有分类资讯"""
        return {
            "internet": self.get_internet_news(limit),
            "tech": self.get_tech_news(limit),
            "ai": self.get_ai_news(limit),
            "science": self.get_science_news(limit),
            "hot": self.get_hot_search(limit),
            "trending": self.get_trending(limit),
            "sports": self.get_sports_news(limit),
        }


news_service = NewsService()
