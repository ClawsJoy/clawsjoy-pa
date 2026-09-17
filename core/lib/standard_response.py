#!/usr/bin/env python3
"""标准化 JSON 响应构建器 v1.0

统一所有组件（Agent、管家、网关）的响应格式
基于 unified_intent_parser 的设计规范
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class StandardResponse:
    """标准化响应数据类"""
    version: str = "1.0"
    session_id: str = ""
    user_id: str = ""
    thread_id: str = ""
    turn: int = 0
    raw_input: str = ""
    timestamp: str = ""
    action: str = "chat"
    target: str = "text"
    keywords: List[str] = field(default_factory=list)
    confidence: float = 0.95
    params: Dict = field(default_factory=dict)
    output_type: str = "text"
    output_content: str = ""
    output_data: Dict = field(default_factory=dict)
    status: str = "completed"
    next: str = "done"
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "version": self.version,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "thread_id": self.thread_id,
            "turn": self.turn,
            "raw_input": self.raw_input,
            "timestamp": self.timestamp or datetime.now().isoformat(),
            "action": self.action,
            "target": self.target,
            "keywords": self.keywords,
            "confidence": self.confidence,
            "params": self.params,
            "output_type": self.output_type,
            "output_content": self.output_content,
            "output_data": self.output_data,
            "status": self.status,
            "next": self.next
        }


class ResponseBuilder:
    """标准化响应构建器
    
    使用示例:
        # Agent 返回成功响应
        return ResponseBuilder.success(
            raw_input="播放周杰伦的歌",
            user_id="alice",
            action="play",
            target="media",
            output_content="正在播放《七里香》"
        )
        
        # Agent 返回错误响应
        return ResponseBuilder.error(
            raw_input="xxx",
            user_id="alice",
            error_msg="未找到该歌曲",
            confidence=0.3
        )
    """
    
    ACTIONS = ["play", "search", "generate", "schedule", "translate", "calculate", "chat"]
    TARGETS = ["media", "code", "image", "info", "task", "text", "number"]
    OUTPUT_TYPES = ["text", "image", "video", "link", "code"]
    
    @classmethod
    def _generate_id(cls) -> str:
        return uuid.uuid4().hex[:8]
    
    @classmethod
    def create(cls, **kwargs) -> Dict:
        """创建标准化响应"""
        response = StandardResponse(**kwargs)
        if not response.session_id:
            response.session_id = cls._generate_id()
        if not response.thread_id:
            response.thread_id = cls._generate_id()
        if not response.timestamp:
            response.timestamp = datetime.now().isoformat()
        return response.to_dict()
    
    @classmethod
    def success(cls,
                raw_input: str,
                user_id: str,
                action: str,
                target: str,
                output_content: str,
                keywords: List[str] = None,
                output_data: Dict = None,
                confidence: float = 0.95,
                session_id: str = None,
                thread_id: str = None,
                turn: int = 0,
                output_type: str = "text",
                status: str = "completed",
                next_action: str = "done",
                **kwargs) -> Dict:
        """构建成功响应"""
        
        # 验证枚举值
        if action not in cls.ACTIONS:
            action = "chat"
        if target not in cls.TARGETS:
            target = "text"
        if output_type not in cls.OUTPUT_TYPES:
            output_type = "text"
            
        return cls.create(
            session_id=session_id or cls._generate_id(),
            thread_id=thread_id or cls._generate_id(),
            turn=turn + 1,
            raw_input=raw_input,
            user_id=user_id,
            timestamp=datetime.now().isoformat(),
            action=action,
            target=target,
            keywords=keywords or [],
            confidence=confidence,
            output_type=output_type,
            output_content=output_content,
            output_data=output_data or {},
            status=status,
            next=next_action,
            **kwargs
        )
    
    @classmethod
    def error(cls,
              raw_input: str,
              user_id: str,
              error_msg: str,
              action: str = "chat",
              target: str = "text",
              confidence: float = 0.1,
              session_id: str = None,
              thread_id: str = None,
              turn: int = 0,
              **kwargs) -> Dict:
        """构建错误响应"""
        return cls.create(
            session_id=session_id or cls._generate_id(),
            thread_id=thread_id or cls._generate_id(),
            turn=turn + 1,
            raw_input=raw_input,
            user_id=user_id,
            timestamp=datetime.now().isoformat(),
            action=action,
            target=target,
            keywords=[],
            confidence=confidence,
            output_type="text",
            output_content=f"❌ {error_msg}",
            output_data={"error": error_msg},
            status="failed",
            next="wait",
            **kwargs
        )
    
    @classmethod
    def from_request(cls, request_json: Dict) -> Dict:
        """从请求中提取标准化响应（透传或创建新响应）"""
        # 如果已经是标准化格式，直接返回
        if "version" in request_json and "action" in request_json:
            return request_json
        
        # 否则创建基础响应
        return cls.create(
            raw_input=request_json.get("message", ""),
            user_id=request_json.get("user_id", "guest"),
            action="chat",
            target="text"
        )
    
    @classmethod
    def from_parser(cls, parser_result: Dict, output_content: str, 
                    output_data: Dict = None) -> Dict:
        """从意图解析器结果构建完整响应"""
        result = parser_result.copy()
        result["output_content"] = output_content
        result["output_data"] = output_data or {}
        result["status"] = "completed"
        result["next"] = "done"
        result["timestamp"] = datetime.now().isoformat()
        return result


# 全局单例
response_builder = ResponseBuilder()
