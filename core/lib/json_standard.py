"""标准化 JSON v1.1 - 2.5层混合设计"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid


def generate_id() -> str:
    return uuid.uuid4().hex[:8]


@dataclass
class StandardJSON:
    """标准化 JSON 核心结构 - 80%扁平 + 20%嵌套"""
    
    # ========== 1. 核心字段（永远扁平）==========
    version: str = "1.1"
    session_id: str = field(default_factory=generate_id)
    user_id: str = ""
    thread_id: str = field(default_factory=generate_id)
    turn: int = 0
    raw_input: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # ========== 2. 意图字段（扁平）==========
    action: str = "chat"      # play/search/generate/schedule/translate/calculate/chat
    target: str = "text"      # media/code/image/info/task/text/number
    keywords: List[str] = field(default_factory=list)
    confidence: float = 0.95
    
    # ========== 3. 输出字段（扁平）==========
    output_type: str = "text"   # text/image/video/link/code
    output_content: str = ""
    output_data: Dict[str, Any] = field(default_factory=dict)
    
    # ========== 4. 状态字段（扁平）==========
    status: str = "pending"     # pending/processing/completed/failed
    next: str = "continue"      # continue/done/wait
    
    # ========== 5. 可选嵌套（仅在复杂场景）==========
    params: Dict[str, Any] = field(default_factory=dict)           # 业务参数
    workflow: Optional['Workflow'] = None                          # 多步骤工作流
    condition: Optional['Condition'] = None                        # 条件分支
    metadata: Dict[str, Any] = field(default_factory=dict)         # 扩展元数据
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        result = {
            "version": self.version,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "thread_id": self.thread_id,
            "turn": self.turn,
            "raw_input": self.raw_input,
            "timestamp": self.timestamp,
            "action": self.action,
            "target": self.target,
            "keywords": self.keywords,
            "confidence": self.confidence,
            "output_type": self.output_type,
            "output_content": self.output_content,
            "output_data": self.output_data,
            "status": self.status,
            "next": self.next,
            "params": self.params,
            "metadata": self.metadata
        }
        
        if self.workflow:
            result["workflow"] = self.workflow.to_dict()
        if self.condition:
            result["condition"] = self.condition.to_dict()
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'StandardJSON':
        """从字典创建"""
        return cls(
            version=data.get("version", "1.1"),
            session_id=data.get("session_id", generate_id()),
            user_id=data.get("user_id", ""),
            thread_id=data.get("thread_id", generate_id()),
            turn=data.get("turn", 0),
            raw_input=data.get("raw_input", ""),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            action=data.get("action", "chat"),
            target=data.get("target", "text"),
            keywords=data.get("keywords", []),
            confidence=data.get("confidence", 0.95),
            output_type=data.get("output_type", "text"),
            output_content=data.get("output_content", ""),
            output_data=data.get("output_data", {}),
            status=data.get("status", "pending"),
            next=data.get("next", "continue"),
            params=data.get("params", {}),
            workflow=Workflow.from_dict(data["workflow"]) if "workflow" in data else None,
            condition=Condition.from_dict(data["condition"]) if "condition" in data else None,
            metadata=data.get("metadata", {})
        )
    
    def is_simple(self) -> bool:
        """判断是否为简单任务（无嵌套）"""
        return self.workflow is None and self.condition is None
    
    def is_complex(self) -> bool:
        """判断是否为复杂任务（有嵌套）"""
        return self.workflow is not None or self.condition is not None


@dataclass
class WorkflowStep:
    """工作流步骤"""
    action: str
    target: str
    depends_on: List[str] = field(default_factory=list)  # 依赖的步骤ID
    params: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "action": self.action,
            "target": self.target,
            "depends_on": self.depends_on,
            "params": self.params
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'WorkflowStep':
        return cls(
            action=data.get("action", ""),
            target=data.get("target", "text"),
            depends_on=data.get("depends_on", []),
            params=data.get("params", {})
        )


@dataclass
class Workflow:
    """工作流定义"""
    mode: str = "sequential"  # sequential / parallel / dag
    steps: List[WorkflowStep] = field(default_factory=list)
    merge: Optional[WorkflowStep] = None  # 合并步骤
    
    def to_dict(self) -> Dict:
        result = {
            "mode": self.mode,
            "steps": [s.to_dict() for s in self.steps]
        }
        if self.merge:
            result["merge"] = self.merge.to_dict()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Workflow':
        return cls(
            mode=data.get("mode", "sequential"),
            steps=[WorkflowStep.from_dict(s) for s in data.get("steps", [])],
            merge=WorkflowStep.from_dict(data["merge"]) if "merge" in data else None
        )


@dataclass
class Condition:
    """条件分支"""
    field: str  # 判断字段
    operator: str  # eq/gt/lt/contains
    value: Any
    then: 'Action'  # 满足时执行
    else_: Optional['Action'] = None  # 不满足时执行
    
    def to_dict(self) -> Dict:
        result = {
            "field": self.field,
            "operator": self.operator,
            "value": self.value,
            "then": self.then.to_dict()
        }
        if self.else_:
            result["else"] = self.else_.to_dict()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Condition':
        return cls(
            field=data.get("field", ""),
            operator=data.get("operator", "eq"),
            value=data.get("value"),
            then=Action.from_dict(data.get("then", {})),
            else_=Action.from_dict(data["else"]) if "else" in data else None
        )


@dataclass
class Action:
    """单个动作"""
    action: str
    target: str
    params: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "action": self.action,
            "target": self.target,
            "params": self.params
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Action':
        return cls(
            action=data.get("action", ""),
            target=data.get("target", "text"),
            params=data.get("params", {})
        )
