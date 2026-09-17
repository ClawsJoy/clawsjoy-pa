"""主动学习引擎 - 识别不确定样本，主动请求标注"""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from engine.lib.logger import engine_logger


class ActiveLearningEngine:
    def __init__(self):
        self.uncertainty_threshold = 0.6
        self.pending_requests = []
        self.approved_samples = []
        self.request_file = Path("data/active_learning_requests.json")
        self._load()
        engine_logger.get().info("🎯 主动学习引擎已初始化")

    def _load(self):
        if self.request_file.exists():
            with open(self.request_file, "r") as f:
                data = json.load(f)
                self.pending_requests = data.get("pending", [])
                self.approved_samples = data.get("approved", [])

    def _save(self):
        with open(self.request_file, "w") as f:
            json.dump(
                {
                    "pending": self.pending_requests,
                    "approved": self.approved_samples,
                    "updated_at": datetime.now().isoformat(),
                },
                f,
                indent=2,
            )

    def request_label(
        self, query: str, predicted_intent: str, confidence: float, reason: str = ""
    ) -> Dict:
        request = {
            "id": len(self.pending_requests) + 1,
            "query": query,
            "predicted_intent": predicted_intent,
            "confidence": confidence,
            "reason": reason,
            "created_at": datetime.now().isoformat(),
            "status": "pending",
        }
        self.pending_requests.append(request)
        self._save()
        engine_logger.get().info(f"   📋 请求标注: {query[:50]}...")
        return request

    def approve_label(self, request_id: int, correct_intent: str) -> Dict:
        for request in self.pending_requests:
            if request["id"] == request_id:
                request["status"] = "approved"
                request["correct_intent"] = correct_intent
                request["approved_at"] = datetime.now().isoformat()
                self.approved_samples.append(
                    {
                        "query": request["query"],
                        "intent": correct_intent,
                        "source": "active_learning",
                    }
                )
                self._save()
                return request
        return {"error": "Request not found"}

    def get_pending_requests(self) -> List[Dict]:
        return [r for r in self.pending_requests if r["status"] == "pending"]

    def get_approved_samples(self) -> List[Dict]:
        return self.approved_samples

    def process(self, input_data: Any = None, **kwargs) -> Any:
        """处理输入 - 统一接口"""
        if input_data is None:
            return self.get_stats()
        if isinstance(input_data, dict):
            action = input_data.get("action", "request")
            if action == "request":
                return self.request_label(
                    input_data.get("query", ""),
                    input_data.get("predicted_intent", "unknown"),
                    input_data.get("confidence", 0.5),
                    input_data.get("reason", ""),
                )
            elif action == "approve":
                return self.approve_label(
                    input_data.get("request_id", 0),
                    input_data.get("correct_intent", ""),
                )
        return self.get_stats()

    def get_stats(self) -> Dict:
        return {
            "pending_requests": len(
                [r for r in self.pending_requests if r["status"] == "pending"]
            ),
            "approved_samples": len(self.approved_samples),
        }


active_learning_engine = ActiveLearningEngine()
