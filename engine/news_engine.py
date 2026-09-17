"""新闻引擎 - 天行数据 API（新版）"""

import os
import requests
from typing import Dict, List
from dotenv import load_dotenv

load_dotenv()


class NewsEngine:
    """新闻资讯引擎"""
    
    name = "news_engine"
    version = "1.0.0"
    
    def __init__(self):
        self.base_url = "https://apis.tianapi.com"
        self.api_key = os.getenv("TIAN_API_KEY", "")
        self.enabled = bool(self.api_key)
        
        # 数据源配置
        self.sources = {
            "toutiao_hot": {"endpoint": "/toutiaohot/index", "name": "头条热搜", "data_path": "result.list"},
            "network_hot": {"endpoint": "/networkhot/index", "name": "全网热搜", "data_path": "result.list"},
            "it": {"endpoint": "/it/index", "name": "IT资讯", "data_path": "result.newslist"},
            "ai": {"endpoint": "/ai/index", "name": "AI资讯", "data_path": "result.newslist"},
            "keji": {"endpoint": "/keji/index", "name": "科技资讯", "data_path": "result.newslist"},
            "sicprobe": {"endpoint": "/sicprobe/index", "name": "科学探索", "data_path": "result.newslist"},
            "internet": {"endpoint": "/internet/index", "name": "互联网", "data_path": "result.newslist"},
        }
        
        if self.enabled:
            print(f"✅ 新闻引擎已启用")
        else:
            print("⚠️ 新闻引擎未配置，请设置 TIAN_API_KEY")
    
    def _get_nested_value(self, data: dict, path: str):
        """获取嵌套字典的值"""
        keys = path.split('.')
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key, {})
            else:
                return []
        return value if isinstance(value, list) else []
    
    def fetch(self, source_key: str, limit: int = 10) -> List[Dict]:
        """获取数据"""
        if not self.enabled:
            return []
        
        source = self.sources.get(source_key)
        if not source:
            return []
        
        url = f"{self.base_url}{source['endpoint']}"
        params = {"key": self.api_key}
        
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 200:
                    result = self._get_nested_value(data, source["data_path"])
                    return result[:limit] if isinstance(result, list) else []
                else:
                    print(f"API 错误: {data.get('msg')}")
        except Exception as e:
            print(f"获取失败 {source_key}: {e}")
        return []
    
    # 便捷方法
    def get_toutiao_hot(self, limit=10):
        """头条热搜"""
        return self.fetch("toutiao_hot", limit)
    
    def get_network_hot(self, limit=10):
        """全网热搜"""
        return self.fetch("network_hot", limit)
    
    def get_it(self, limit=10):
        """IT资讯"""
        return self.fetch("it", limit)
    
    def get_ai(self, limit=10):
        """AI资讯"""
        return self.fetch("ai", limit)
    
    def get_keji(self, limit=10):
        """科技资讯"""
        return self.fetch("keji", limit)
    
    def get_sicprobe(self, limit=10):
        """科学探索"""
        return self.fetch("sicprobe", limit)
    
    def get_internet(self, limit=10):
        """互联网"""
        return self.fetch("internet", limit)
    
    # 兼容旧接口名称
    def get_hot(self, limit=10):
        return self.get_network_hot(limit)
    
    def get_trending(self, limit=10):
        return self.get_toutiao_hot(limit)
    
    def get_news(self, limit=10):
        return self.get_toutiao_hot(limit)
    
    def get_tech(self, limit=10):
        return self.get_keji(limit)
    
    def get_science(self, limit=10):
        return self.get_sicprobe(limit)
    
    def get_all(self, limit=5) -> Dict:
        """获取所有源数据"""
        result = {}
        for key in self.sources:
            result[key] = self.fetch(key, limit)
        return result
    
    def list_sources(self) -> List[Dict]:
        """列出所有数据源"""
        return [{"key": k, "name": v["name"]} for k, v in self.sources.items()]


news_engine = NewsEngine()
