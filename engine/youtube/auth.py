"""YouTube OAuth 认证 - 安全处理 API 密钥"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from engine.lib.logger import engine_logger


class YouTubeAuth:
    """YouTube API 认证管理器"""

    def __init__(self):
        self.credentials = None
        self.authenticated = False
        self._load_credentials()

    def _load_credentials(self):
        """从安全位置加载凭证"""
        # 优先从环境变量读取
        api_key = os.environ.get("YOUTUBE_API_KEY")
        if api_key:
            self.credentials = {"api_key": api_key}
            self.authenticated = True
            engine_logger.get().info("🔑 YouTube API 已从环境变量加载")
            return

        # 从安全配置文件读取
        cred_file = Path("config/secrets/youtube_credentials.json")
        if cred_file.exists():
            try:
                with open(cred_file, "r") as f:
                    self.credentials = json.load(f)
                    self.authenticated = True
                    engine_logger.get().info("🔑 YouTube API 已从配置文件加载")
                    return
            except Exception as e:
                pass

        engine_logger.get().warning("⚠️ YouTube API 凭证未配置")

    def get_api_key(self) -> Optional[str]:
        """获取 API Key"""
        if self.credentials:
            return self.credentials.get("api_key")
        return os.environ.get("YOUTUBE_API_KEY")

    def is_authenticated(self) -> bool:
        return self.authenticated

    def get_auth_url(self) -> str:
        """获取 OAuth 授权 URL"""
        client_id = self.credentials.get("client_id") if self.credentials else None
        if not client_id:
            client_id = os.environ.get("YOUTUBE_CLIENT_ID")

        redirect_uri = "http://localhost:5002/youtube/oauth2callback"

        return f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope=https://www.googleapis.com/auth/youtube.upload"

    def get_stats(self) -> Dict:
        return {
            "authenticated": self.authenticated,
            "has_credentials": self.credentials is not None,
        }


youtube_auth = YouTubeAuth()
