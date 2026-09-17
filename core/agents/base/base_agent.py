#!/usr/bin/env python3
"""BaseAgent v4.0 - 安全边界 + 法律合规 + 伦理 + 永久记忆

v4.0 改动:
- 删除 greet/farewell/thank/apologize 四个社交方法（移到 chat_agent）
- 删除 _call_llm（不再需要）
- 保留安全/法律/伦理检查（核心职责）
- 保留永久记忆系统
- handle() 简化为纯安全检查包装
"""

import hashlib
import json
import time
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.lib.config_helper import get_data_root


# ========== 安全边界定义 ==========

class SafetyLevel(Enum):
    SAFE = "safe"
    CAUTION = "caution"
    DANGEROUS = "dangerous"
    FORBIDDEN = "forbidden"


class LegalStatus(Enum):
    COMPLIANT = "compliant"
    RESTRICTED = "restricted"
    VIOLATION = "violation"


class BaseAgent(ABC):
    """基础智能体 v4.0 - 安全底线 + 记忆基础设施"""

    VERSION = "4.0.0"

    name: str = "base_agent"
    description: str = "基础智能体"
    creator: str = "ClawsJoy"

    def __init__(self, user_id: str = "default", agent_id: Optional[str] = None):
        self.user_id = user_id
        self.agent_id = agent_id or f"{self.name}_{int(time.time())}"
        self.birth_time = datetime.now()
        self.last_active = self.birth_time

        # 记忆
        self._permanent_memory: Dict = {}
        self._session_memory: Dict = {}
        self._moral_memory: List[Dict] = []

        # 统计
        self._stats = {
            "born": self.birth_time.isoformat(),
            "total_interactions": 0,
            "safety_violations": 0,
            "legal_checks": 0,
            "ethical_decisions": 0,
        }

        self._init_identity()
        self._load_permanent_memory()
        self._init_safety_boundaries()
        self._init_legal_boundaries()
        self._init_ethical_principles()

        print(f"🧬 [{self.name}] BaseAgent v{self.VERSION} | "
              f"{len(self._forbidden_actions)}条禁令 | "
              f"{len(self._permanent_memory)}条永久记忆")

    # ==================== 身份 ====================

    def _init_identity(self):
        self._identity = {
            "name": self.name, "type": "AI Assistant",
            "creator": self.creator, "version": self.VERSION,
            "purpose": "协助用户完成任务，遵守安全和法律边界",
            "limitations": [
                "不能执行危险操作", "不能违反法律法规",
                "不能伤害生命", "不能泄露敏感信息",
            ],
        }

    def who_am_i(self) -> Dict:
        return {
            "identity": self._identity,
            "capabilities": getattr(self, '_capabilities', []),
            "forbidden": self._forbidden_actions,
            "moral_standards": list(self._ethical_principles.keys()),
        }

    # ==================== 安全检查 ====================

    def _init_safety_boundaries(self):
        self._safety_rules = {
            "no_harm": "不能执行可能造成伤害的操作",
            "no_dangerous_code": "不能执行危险代码",
            "no_system_modify": "不能修改系统文件",
            "no_unauthorized_access": "不能未经授权访问",
            "no_data_destruction": "不能删除用户数据",
        }
        self._forbidden_actions = [
            "delete_system_files", "execute_unknown_code",
            "access_private_data", "bypass_security",
            "ddos_attack", "hack_attempt", "steal_credentials",
        ]

    def check_safety(self, action: str, context: Dict = None) -> Tuple[SafetyLevel, str]:
        action_lower = action.lower()
        for forbidden in self._forbidden_actions:
            if forbidden in action_lower:
                self._stats["safety_violations"] += 1
                return SafetyLevel.FORBIDDEN, f"操作被禁止: {forbidden}"
        danger_keywords = ["删除", "delete", "rm", "format", "drop", "truncate"]
        for kw in danger_keywords:
            if kw in action_lower:
                return SafetyLevel.DANGEROUS, f"检测到危险操作: {kw}"
        for rule, desc in self._safety_rules.items():
            if rule in action_lower:
                return SafetyLevel.CAUTION, f"需要谨慎: {desc}"
        return SafetyLevel.SAFE, "操作安全"

    def safe_guard(self, action: str, context: Dict = None) -> bool:
        level, reason = self.check_safety(action, context)
        if level == SafetyLevel.FORBIDDEN:
            print(f"🛡 [{self.name}] 拒绝: {reason}")
            return False
        if level == SafetyLevel.DANGEROUS:
            print(f"⚠ [{self.name}] 危险: {reason}")
            return False
        if level == SafetyLevel.CAUTION:
            print(f"⚡ [{self.name}] 谨慎: {reason}")
        return True

    # ==================== 法律检查 ====================

    def _init_legal_boundaries(self):
        self._legal_principles = {
            "privacy": "保护用户隐私", "copyright": "尊重知识产权",
            "no_fraud": "不协助诈骗", "no_illegal_content": "不生成违法内容",
        }
        self._illegal_keywords = [
            "诈骗", "欺诈", "黑客", "入侵", "毒品", "赌博",
            "暴力", "恐怖", "侵犯隐私",
        ]

    def check_legality(self, action: str, context: Dict = None) -> Tuple[LegalStatus, str]:
        for kw in self._illegal_keywords:
            if kw in action.lower():
                self._stats["legal_checks"] += 1
                return LegalStatus.VIOLATION, f"可能违法: {kw}"
        return LegalStatus.COMPLIANT, "合规"

    def legal_check(self, action: str) -> bool:
        status, reason = self.check_legality(action)
        if status == LegalStatus.VIOLATION:
            print(f"⚖ [{self.name}] 拒绝: {reason}")
            return False
        return True

    # ==================== 伦理检查 ====================

    def _init_ethical_principles(self):
        self._ethical_principles = {
            "respect_life": "尊重和保护生命",
            "do_no_harm": "不造成伤害",
            "human_dignity": "维护人类尊严",
            "fairness": "公平对待所有人",
        }

    def ethical_check(self, action: str, impact: Dict = None) -> Tuple[bool, str]:
        life_kw = ["自杀", "杀人", "伤害", "虐待"]
        for kw in life_kw:
            if kw in action.lower():
                return False, f"违反生命伦理: {kw}"
        dignity_kw = ["侮辱", "歧视", "贬低"]
        for kw in dignity_kw:
            if kw in action.lower():
                return False, f"违反尊严原则: {kw}"
        self._stats["ethical_decisions"] += 1
        return True, "符合伦理"

    # ==================== 永久记忆 ====================

    def _get_memory_file(self) -> Path:
        memory_key = hashlib.md5(
            f"{self.user_id}_{self.name}".encode()
        ).hexdigest()[:16]
        memory_dir = Path(get_data_root()) / "permanent_memory"
        memory_dir.mkdir(parents=True, exist_ok=True)
        return memory_dir / f"{memory_key}.json"

    def _get_fallback_memory_files(self) -> List[Path]:
        """方案A: key 失效(历史 user_id 变更)时, 收集所有同 name 的记忆文件。

        根因: key = md5(user_id_name)[:16] 把 user_id 烙进文件名, user_id 变化即"丢记忆"。
        fallback 合并加载: 精确 key 不存在时, 把所有含本 agent 记忆的文件都纳入(不丢历史)。
        """
        memory_dir = Path(get_data_root()) / "permanent_memory"
        if not memory_dir.exists():
            return []
        found = []
        try:
            for _f in sorted(memory_dir.glob("*.json")):
                try:
                    _data = json.loads(_f.read_text(encoding="utf-8"))
                    if any(isinstance(_v, dict) and _v.get("agent") == self.name
                           for _v in _data.values()):
                        found.append(_f)
                except Exception:
                    continue
        except Exception:
            pass
        return found

    def _load_permanent_memory(self):
        memory_file = self._get_memory_file()
        _merged = {}
        if memory_file.exists():
            try:
                _merged.update(json.loads(memory_file.read_text(encoding="utf-8")))
            except Exception:
                pass
        # 方案A: 精确 key 未命中时合并所有同 name 历史文件(恢复旧 user_id 的记忆)
        if not _merged:
            for _f in self._get_fallback_memory_files():
                try:
                    _data = json.loads(_f.read_text(encoding="utf-8"))
                    _merged.update(_data)
                except Exception:
                    continue
        self._permanent_memory = _merged

    def _save_permanent_memory(self):
        try:
            self._get_memory_file().write_text(
                json.dumps(self._permanent_memory, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            print(f"⚠ 保存记忆失败: {e}")

    def remember_forever(self, key: str, value: Any, importance: int = 5):
        self._permanent_memory[key] = {
            "value": value, "importance": importance,
            "timestamp": datetime.now().isoformat(), "agent": self.name,
        }
        self._save_permanent_memory()

    def recall_forever(self, key: str) -> Optional[Any]:
        mem = self._permanent_memory.get(key)
        return mem["value"] if mem else None

    def forget_forever(self, key: str) -> bool:
        if key in self._permanent_memory:
            del self._permanent_memory[key]
            self._save_permanent_memory()
            return True
        return False

    def get_all_memories(self) -> Dict:
        return {
            "permanent": self._permanent_memory,
            "session": self._session_memory,
            "moral": self._moral_memory[-10:],
        }

    def remember_moral_lesson(self, situation: str, lesson: str):
        self._moral_memory.append({
            "situation": situation, "lesson": lesson,
            "learned_at": datetime.now().isoformat(),
        })

    # ==================== 核心处理 ====================

    @abstractmethod
    def process(self, user_input: str, context: Dict = None) -> Dict:
        pass

    def handle(self, user_input: str, context: Dict = None) -> Dict:
        """处理入口 - 自动安全检查"""
        if not self.safe_guard(user_input, context):
            return {"success": False, "error": "安全拒绝",
                    "response": "抱歉，我无法执行这个操作，因为它可能不安全。"}
        if not self.legal_check(user_input):
            return {"success": False, "error": "法律拒绝",
                    "response": "抱歉，我无法执行这个操作，因为它可能违反法律法规。"}
        ethical_ok, reason = self.ethical_check(user_input)
        if not ethical_ok:
            return {"success": False, "error": reason,
                    "response": f"抱歉，{reason}。"}

        self._stats["total_interactions"] += 1
        self.last_active = datetime.now()

        result = self.process(user_input, context)

        self._session_memory[user_input[:50]] = result.get("response", "")[:100]
        if len(self._session_memory) > 100:
            items = list(self._session_memory.items())
            self._session_memory = dict(items[-100:])

        return result

    # ==================== 状态 ====================

    def get_status(self) -> Dict:
        return {
            "identity": self.who_am_i(),
            "stats": self._stats,
            "memory_count": {
                "permanent": len(self._permanent_memory),
                "session": len(self._session_memory),
                "moral": len(self._moral_memory),
            },
        }

    def health_check(self) -> Dict:
        return {
            "status": "healthy", "agent": self.name,
            "version": self.VERSION, "user_id": self.user_id,
            "active_time": (datetime.now() - self.birth_time).total_seconds(),
            "interactions": self._stats["total_interactions"],
        }
