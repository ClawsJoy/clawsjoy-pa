"""简化版对话引擎 - 确保基本功能"""

import requests
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class UnifiedChatEngine:
    def __init__(self):
        self.llm_url = "http://localhost:5012/chat"
        logger.info("✅ 简化版 ChatEngine 初始化")

    def execute(self, message: str, user_id: str = "guest") -> Dict:
        logger.info(f"处理: {message[:50]}...")
        
        try:
            resp = requests.post(
                self.llm_url,
                json={"message": message},
                timeout=60,
                headers={"Content-Type": "application/json"}
            )
            
            if resp.status_code == 200:
                result = resp.json()
                response = result.get("response", "")
                return {
                    "success": True,
                    "response": response,
                    "agent": "simple_engine",
                    "user_id": user_id
                }
            else:
                return {"success": False, "response": f"错误: {resp.status_code}", "agent": "error", "user_id": user_id}
        except Exception as e:
            return {"success": False, "response": str(e), "agent": "error", "user_id": user_id}


chat_engine = UnifiedChatEngine()
