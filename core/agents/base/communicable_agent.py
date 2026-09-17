#!/usr/bin/env python3
"""CommunicableAgent v4.0 - 审计 + 可解释 + 联邦知识共享

v4.0 改动:
- 删除 recognize_emotion() + LLM（移到需要情感的业务Agent）
- 删除 get_emotion_response() + LLM（同上）
- 删除 collaborative_decision() + LLM（AgentCortex 已做）
- 删除 _call_llm()（最后一处LLM直调消除）
- 保留审计日志、可解释性、联邦知识共享
"""

import json
from collections import defaultdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.agents.base.base_agent import BaseAgent
from core.lib.unified_config import unified_config
from core.lib.federated_bus import federated_bus

class Emotion(Enum):
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    FEARFUL = "fearful"
    SURPRISED = "surprised"
    CONFUSED = "confused"
    NEUTRAL = "neutral"


class DecisionExplanation:
    def __init__(self, decision: str, reasons: List[str], confidence: float):
        self.decision = decision
        self.reasons = reasons
        self.confidence = confidence
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "decision": self.decision, "reasons": self.reasons,
            "confidence": self.confidence, "timestamp": self.timestamp.isoformat()
        }


class CommunicableAgent(BaseAgent):
    """通信基类 v4.0 - 审计 + 可解释 + 联邦"""

    VERSION = "4.0.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)

        # 情感历史（纯记录，不调LLM）
        self._emotion_history: List[Dict] = []
        self._current_emotion = Emotion.NEUTRAL

        # 联邦学习
        self._federated_knowledge: Dict = {}
        self._local_updates: List[Dict] = []
        self._privacy_threshold = 0.7
        self._knowledge_sharing_enabled = unified_config.get("federated.enabled", True)

        # 可解释性
        self._decision_history: List[DecisionExplanation] = []
        self._explanation_enabled = unified_config.get("explanation.enabled", True)

        # 审计
        self._audit_log: List[Dict] = []
        self._audit_enabled = unified_config.get("audit.enabled", True)
        self._audit_file = Path("logs/audit") / f"{self.name}_{self.user_id}.json"
        self._audit_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_audit_log()

        print(f"📡 [{self.name}] CommunicableAgent v{self.VERSION}")
        # 启动联邦监听
        self._start_federated_listener()

    def _start_federated_listener(self):
        """监听联邦知识更新"""
        def on_knowledge(data: Dict):
            if data.get("source") != self.name:
                key = data.get("key", "")
                if key:
                    value = federated_bus.get_knowledge(key)
                    if value:
                        self._federated_knowledge[key] = {
                            "value": value, "source": data["source"],
                            "received_at": datetime.now().isoformat()
                        }
        
        federated_bus.subscribe("knowledge.updated", on_knowledge)

    def share_knowledge(self, knowledge: Dict, privacy_level: float = 0.5) -> bool:
        """分享知识到联邦"""
        if not self._knowledge_sharing_enabled:
            return False
        if privacy_level < self._privacy_threshold:
            return False
        
        shared = 0
        for key, value in self._sanitize_knowledge(knowledge).items():
            federated_bus.put_knowledge(
                key=key, value=value, source=self.name,
                privacy=privacy_level,
                tags=[self.name, type(value).__name__]
            )
            shared += 1
        
        self._local_updates.append({
            "keys": list(knowledge.keys()),
            "shared_at": datetime.now().isoformat()
        })
        return shared > 0

    def query_federated_knowledge(self, query: str) -> List[Dict]:
        """查询联邦知识"""
        return federated_bus.query_knowledge(query)

    def get_federated_stats(self) -> Dict:
        return {
            **federated_bus.get_stats(),
            "local_updates": len(self._local_updates),
            "my_knowledge": len(self._federated_knowledge),
        }
    # ==================== 情感记录（纯数据，不调LLM） ====================

    def record_emotion(self, emotion: Emotion, confidence: float, text: str = ""):
        """记录情感 - 由外部（AgentCortex或业务Agent）传入"""
        if confidence > 0.3:
            self._current_emotion = emotion
        self._emotion_history.append({
            "text": text[:50], "emotion": emotion.value,
            "confidence": confidence, "timestamp": datetime.now().isoformat()
        })
        if len(self._emotion_history) > 100:
            self._emotion_history = self._emotion_history[-100:]

    @property
    def current_emotion(self) -> Emotion:
        return self._current_emotion

    def get_emotion_stats(self) -> Dict:
        stats = defaultdict(int)
        for r in self._emotion_history:
            stats[r["emotion"]] += 1
        return {
            "current": self._current_emotion.value,
            "history_count": len(self._emotion_history),
            "distribution": dict(stats),
        }

    # ==================== 联邦知识共享 ====================

    def share_knowledge(self, knowledge: Dict, privacy_level: float = 0.5) -> bool:
        if not self._knowledge_sharing_enabled or privacy_level < self._privacy_threshold:
            return False
        sanitized = self._sanitize_knowledge(knowledge)
        self.bus_publish("federated.knowledge", {
            "from": self.name, "knowledge": sanitized,
            "privacy_level": privacy_level, "timestamp": datetime.now().isoformat()
        })
        self._local_updates.append({
            "knowledge": sanitized, "privacy_level": privacy_level,
            "shared_at": datetime.now().isoformat()
        })
        return True

    def receive_knowledge(self, knowledge: Dict, from_agent: str) -> bool:
        if not self._knowledge_sharing_enabled or not knowledge:
            return False
        for key, value in knowledge.items():
            if key not in self._federated_knowledge:
                self._federated_knowledge[key] = []
            self._federated_knowledge[key].append({
                "value": value, "source": from_agent,
                "received_at": datetime.now().isoformat()
            })
        return True

    def _sanitize_knowledge(self, knowledge: Dict) -> Dict:
        sanitized = {}
        sensitive = {"user_id", "password", "token", "email", "phone"}
        for key, value in knowledge.items():
            sanitized[key] = "[REDACTED]" if key in sensitive else value
        return sanitized

    def get_federated_stats(self) -> Dict:
        return {
            "enabled": self._knowledge_sharing_enabled,
            "local_updates": len(self._local_updates),
            "received": len(self._federated_knowledge),
            "privacy_threshold": self._privacy_threshold,
        }

    # ==================== 可解释性 ====================

    def explain_decision(self, decision: str, reasons: List[str], confidence: float):
        if not self._explanation_enabled:
            return
        self._decision_history.append(
            DecisionExplanation(decision, reasons, confidence)
        )
        if len(self._decision_history) > 100:
            self._decision_history = self._decision_history[-100:]

    def get_decision_explanation(self, index: int = -1) -> Optional[Dict]:
        if not self._decision_history:
            return None
        idx = index if index >= 0 else len(self._decision_history) + index
        if 0 <= idx < len(self._decision_history):
            return self._decision_history[idx].to_dict()
        return None

    def get_all_explanations(self) -> List[Dict]:
        return [e.to_dict() for e in self._decision_history]

    # ==================== 审计 ====================

    def _load_audit_log(self):
        if self._audit_file.exists():
            try:
                self._audit_log = json.loads(self._audit_file.read_text())
            except Exception:
                self._audit_log = []

    def _save_audit_log(self):
        if not self._audit_enabled:
            return
        try:
            self._audit_file.write_text(
                json.dumps(self._audit_log, indent=2, ensure_ascii=False)
            )
        except Exception:
            pass

    def audit(self, action: str, details: Dict, result: str = "success"):
        if not self._audit_enabled:
            return
        self._audit_log.append({
            "timestamp": datetime.now().isoformat(),
            "agent": self.name, "user_id": self.user_id,
            "action": action, "details": details, "result": result,
        })
        if len(self._audit_log) > 1000:
            self._audit_log = self._audit_log[-1000:]
        if len(self._audit_log) % 10 == 0:
            self._save_audit_log()

    def get_audit_log(self, limit: int = 100, action_filter: str = None) -> List[Dict]:
        logs = self._audit_log[-limit:]
        if action_filter:
            logs = [l for l in logs if l["action"] == action_filter]
        return logs

    def get_audit_stats(self) -> Dict:
        from collections import Counter
        actions = Counter(l["action"] for l in self._audit_log)
        results = Counter(l["result"] for l in self._audit_log)
        return {
            "total_logs": len(self._audit_log),
            "actions": dict(actions), "results": dict(results),
        }

    def get_communication_stats(self) -> Dict:
        return {
            "emotion": self.get_emotion_stats(),
            "federated": self.get_federated_stats(),
            "audit": self.get_audit_stats(),
            "explanations": len(self._decision_history),
        }
