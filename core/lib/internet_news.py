"""互联网资讯模块 - 集成外部 API"""

import os
import requests
from typing import List, Dict
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class InternetNews:
    """互联网资讯获取"""
    
    def __init__(self):
        # 从环境变量读取配置
        self.api_key = os.getenv("NEWS_API_KEY", "")
        self.api_url = os.getenv("NEWS_API_URL", "https://api.example.com")
        self.hot_url = os.getenv("NEWS_HOT_URL", f"{self.api_url}/hot")
        self.trending_url = os.getenv("NEWS_TRENDING_URL", f"{self.api_url}/trending")
        self.science_url = os.getenv("NEWS_SCIENCE_URL", f"{self.api_url}/science")
        
        self.enabled = bool(self.api_key and self.api_url != "https://api.example.com")
        
        if self.enabled:
            print(f"✅ 互联网资讯已启用 (API: {self.api_url})")
        else:
            print("⚠️ 互联网资讯未配置，请设置 NEWS_API_KEY 和 NEWS_API_URL")
    
    def get_hot_search(self, limit: int = 10) -> List[Dict]:
        """获取全网热搜榜"""
        if not self.enabled:
            return [{"title": "请配置 NEWS_API_KEY 和 NEWS_API_URL", "tip": "在 .env 中设置"}]
        
        try:
            response = requests.get(
                self.hot_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("list", [])[:limit]
        except Exception as e:
            print(f"获取热搜失败: {e}")
        return []
    
    def get_trending_news(self, limit: int = 10) -> List[Dict]:
        """获取头条热搜榜"""
        if not self.enabled:
            return []
        
        try:
            response = requests.get(
                self.trending_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("list", [])[:limit]
        except Exception as e:
            print(f"获取头条失败: {e}")
        return []
    
    def get_science_news(self, limit: int = 10) -> List[Dict]:
        """获取科学探索资讯"""
        if not self.enabled:
            return []
        
        try:
            response = requests.get(
                self.science_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("list", [])[:limit]
        except Exception as e:
            print(f"获取科学资讯失败: {e}")
        return []
    
    def search_news(self, keyword: str, limit: int = 10) -> List[Dict]:
        """搜索相关资讯"""
        if not self.enabled:
            return []
        
        try:
            response = requests.get(
                f"{self.api_url}/search",
                params={"q": keyword, "limit": limit},
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])
        except Exception as e:
            print(f"搜索资讯失败: {e}")
        return []


internet_news = InternetNews()
