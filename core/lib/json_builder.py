# core/lib/json_builder.py
#!/usr/bin/env python3
"""标准化 JSON 构建器 - 流式 API"""

from typing import Dict, Any, List, Optional
from core.lib.json_standard import StandardJSON, Workflow, WorkflowStep, Condition, Action


class StandardJSONBuilder:
    """标准化 JSON 构建器 - 流式 API"""
    
    def __init__(self):
        self._json = StandardJSON()
    
    def simple(self, action: str, target: str, raw_input: str = "") -> 'StandardJSONBuilder':
        """简单任务 - 纯扁平"""
        self._json.action = action
        self._json.target = target
        self._json.raw_input = raw_input
        return self
    
    def with_keywords(self, *keywords) -> 'StandardJSONBuilder':
        self._json.keywords = list(keywords)
        return self
    
    def with_params(self, **params) -> 'StandardJSONBuilder':
        self._json.params = params
        return self
    
    def with_user(self, user_id: str, session_id: str = None) -> 'StandardJSONBuilder':
        self._json.user_id = user_id
        if session_id:
            self._json.session_id = session_id
        return self
    
    def workflow(self, mode: str = "sequential") -> 'WorkflowBuilder':
        """创建工作流（返回子构建器）"""
        from core.lib.json_builder import WorkflowBuilder
        wb = WorkflowBuilder(self, mode)
        self._json.workflow = wb._workflow
        return wb
    
    def condition(self, field: str, operator: str, value: Any) -> 'ConditionBuilder':
        """创建条件分支（返回子构建器）"""
        from core.lib.json_builder import ConditionBuilder
        cb = ConditionBuilder(self, field, operator, value)
        self._json.condition = cb._condition
        return cb
    
    def build(self) -> StandardJSON:
        return self._json


class WorkflowBuilder:
    """工作流构建器"""
    
    def __init__(self, parent: StandardJSONBuilder, mode: str):
        self._parent = parent
        self._workflow = Workflow(mode=mode)
    
    def add_step(self, action: str, target: str, depends_on: List[str] = None) -> 'WorkflowBuilder':
        step = WorkflowStep(
            action=action,
            target=target,
            depends_on=depends_on or []
        )
        self._workflow.steps.append(step)
        return self
    
    def merge_with(self, action: str, target: str) -> 'StandardJSONBuilder':
        self._workflow.merge = WorkflowStep(action=action, target=target)
        return self._parent
    
    def end(self) -> StandardJSONBuilder:
        return self._parent


class ConditionBuilder:
    """条件分支构建器"""
    
    def __init__(self, parent: StandardJSONBuilder, field: str, operator: str, value: Any):
        self._parent = parent
        self._condition = Condition(
            field=field,
            operator=operator,
            value=value,
            then=Action(action="", target="")
        )
    
    def then(self, action: str, target: str, **params) -> 'ConditionBuilder':
        self._condition.then = Action(action=action, target=target, params=params)
        return self
    
    def else_(self, action: str, target: str, **params) -> 'StandardJSONBuilder':
        self._condition.else_ = Action(action=action, target=target, params=params)
        return self._parent
    
    def end(self) -> StandardJSONBuilder:
        return self._parent


# 使用示例
def build_examples():
    builder = StandardJSONBuilder()
    
    # 示例1: 简单任务（纯扁平）
    simple = builder.simple("play", "media", "播放周杰伦的歌")\
                   .with_keywords("周杰伦")\
                   .with_user("alice")\
                   .build()
    
    # 示例2: 工作流（浅嵌套）
    workflow = builder.simple("workflow", "composite")\
                     .workflow("parallel")\
                     .add_step("analyze", "finance")\
                     .add_step("generate", "chart", depends_on=["analyze"])\
                     .merge_with("send", "email")\
                     .build()
    
    # 示例3: 条件分支
    conditional = builder.simple("analyze", "data")\
                        .condition("result.score", "gt", 0.8)\
                        .then("send", "email", recipient="boss@company.com")\
                        .else_("save", "draft")\
                        .build()
    
    return simple, workflow, conditional
