#!/usr/bin/env python3
"""JSON Capable Mixin - 标准化 JSON 处理能力"""

from typing import Dict, Any, Optional, Tuple, Union, List  # 添加 List
from abc import abstractmethod
from datetime import datetime

from core.lib.json_standard import StandardJSON, Workflow, Condition
from core.lib.json_builder import StandardJSONBuilder
from core.lib.json_serializer import LLMFriendlySerializer


class JSONCapableMixin:
    """
    标准化 JSON 处理能力混入类
    
    为 Agent 添加:
    1. JSON 序列化/反序列化
    2. 简单/复杂任务自动判断
    3. 工作流执行
    4. 条件分支处理
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._json_serializer = LLMFriendlySerializer()
        self._json_builder = StandardJSONBuilder()
        
    # ========== 能力声明（子类实现）==========
    
    def can_handle_json(self, action: str, target: str) -> Tuple[bool, float]:
        """
        判断是否能处理该 action+target
        子类必须实现
        返回: (能否处理, 置信度)
        """
        # 默认实现：尝试从原有 can_handle 推断
        if hasattr(self, 'can_handle'):
            # 调用原有的 can_handle（如果存在）
            result = self.can_handle(f"{action} {target}")
            if isinstance(result, dict):
                return result.get('can', False), result.get('confidence', 0.5)
            elif isinstance(result, bool):
                return result, 0.8 if result else 0.0
        return False, 0.0
    
    # ========== JSON 入口 ==========
    
    def handle_json(self, json_input: Union[Dict, str, StandardJSON]) -> Dict:
        """
        处理标准化 JSON 输入（主入口）
        
        自动判断:
        - 简单任务 → 扁平处理
        - 工作流 → 步骤执行
        - 条件分支 → 分支执行
        """
        import json
        # 1. 解析输入
        if isinstance(json_input, str):
            json_input = json.loads(json_input)
        
        if isinstance(json_input, dict):
            standard_json = StandardJSON.from_dict(json_input)
        else:
            standard_json = json_input
        
        # 2. 检查能力
        can, confidence = self.can_handle_json(
            standard_json.action, 
            standard_json.target
        )
        
        if not can:
            return self._json_error_response(
                standard_json, 
                f"无法处理 {standard_json.action}/{standard_json.target}"
            )
        
        # 3. 根据复杂度分发
        if standard_json.workflow:
            return self._execute_workflow(standard_json)
        elif standard_json.condition:
            return self._execute_condition(standard_json)
        else:
            return self._execute_simple(standard_json)
    
    # ========== 简单任务执行（纯扁平）==========
    
    def _execute_simple(self, json_obj: StandardJSON) -> Dict:
        """执行简单任务 - 80% 场景"""
        
        # 构建输入
        if json_obj.raw_input:
            user_input = json_obj.raw_input
        else:
            user_input = " ".join(json_obj.keywords) if json_obj.keywords else f"{json_obj.action} {json_obj.target}"
        
        # 调用原有处理逻辑
        if hasattr(self, 'process'):
            result = self.process(user_input, {"json_context": json_obj.to_dict()})
        elif hasattr(self, '_execute_business'):
            result = self._execute_business(user_input, {"json_context": json_obj.to_dict()})
        else:
            result = {"success": False, "response": "Agent 没有 process 或 _execute_business 方法"}
        
        # 包装为标准化响应
        return self._to_standard_response(json_obj, result)
    
    def _execute_simple_batch(self, json_objects: List[StandardJSON]) -> List[Dict]:
        """批量执行简单任务 - 矩阵化优化"""
        # 批量处理
        results = []
        for obj in json_objects:
            result = self._execute_simple(obj)
            results.append(result)
        
        return results        
           

    # ========== 工作流执行（浅嵌套）==========
    def _execute_workflow(self, json_obj: StandardJSON) -> Dict:
        """执行工作流 - 15% 场景"""
        
        workflow = json_obj.workflow
        results = {}
        
        if workflow.mode == "sequential":
            # 顺序执行
            for step in workflow.steps:
                result = self._execute_workflow_step(step, results)
                results[step.action] = result
        
        elif workflow.mode == "parallel":
        
            # 并行执行（简化版，实际可用线程池）
            for step in workflow.steps:
                result = self._execute_workflow_step(step, results)
                results[step.action] = result

        # 合并步骤
        if workflow.merge:
            merge_result = self._execute_workflow_step(workflow.merge, results)
            results["merged"] = merge_result
        
        # 构建响应
        return self._to_standard_response(
            json_obj,
            {
                "success": True,
                "output_content": self._format_workflow_results(results),
                "output_data": {"step_results": results}
            }
        )
    
    def _execute_workflow_step(self, step, context: Dict) -> Dict:
        """执行单个工作流步骤"""
        
        # 构建子任务的 JSON
        step_json = StandardJSON(
            action=step.action,
            target=step.target,
            params=step.params,
            raw_input=f"{step.action} {step.target}"
        )
        
        # 递归调用
        return self._execute_simple(step_json)
    
   
    # ========== 条件分支执行 ==========
    
    def _execute_condition(self, json_obj: StandardJSON) -> Dict:
        """执行条件分支 - 5% 场景"""
        
        condition = json_obj.condition
        
        # 获取判断值
        if condition.field.startswith("result."):
            # 从之前结果中获取
            field_name = condition.field.split(".")[1]
            value = getattr(json_obj, field_name, None)
        else:
            value = getattr(json_obj, condition.field, None)
        
        # 判断条件
        satisfied = self._evaluate_condition(value, condition.operator, condition.value)
        
        # 执行对应分支
        if satisfied:
            action = condition.then
        else:
            action = condition.else_
        
        if not action:
            return self._json_error_response(json_obj, "条件分支无可用动作")
        
        # 执行动作
        result_json = StandardJSON(
            action=action.action,
            target=action.target,
            params=action.params,
            raw_input=json_obj.raw_input
        )
        
        return self._execute_simple(result_json)
    
    def _evaluate_condition(self, value: Any, operator: str, target: Any) -> bool:
        """评估条件"""
        if operator == "eq":
            return value == target
        elif operator == "gt":
            return value > target
        elif operator == "lt":
            return value < target
        elif operator == "contains":
            return target in value if value else False
        elif operator == "in":
            return value in target if target else False
        return False
    
    # ========== 响应构建 ==========
    
    def _to_standard_response(self, request: StandardJSON, result: Dict) -> Dict:
        """转换为标准化响应"""
        
        # 如果结果已经是标准化格式
        if "version" in result and "action" in result:
            return result
        
        # 包装结果
        return {
            "version": "1.1",
            "session_id": request.session_id,
            "user_id": request.user_id,
            "thread_id": request.thread_id,
            "turn": request.turn + 1,
            "raw_input": request.raw_input,
            "timestamp": datetime.now().isoformat(),
            "action": request.action,
            "target": request.target,
            "keywords": request.keywords,
            "confidence": request.confidence,
            "output_type": result.get("output_type", "text"),
            "output_content": result.get("output_content", result.get("response", "")),
            "output_data": result.get("output_data", result),
            "status": result.get("status", "completed"),
            "next": result.get("next", "done"),
            "params": request.params,
            "metadata": result.get("metadata", {})
        }
    
    def _json_error_response(self, request: StandardJSON, error_msg: str) -> Dict:
        """构建错误响应"""
        return {
            "version": "1.1",
            "session_id": request.session_id,
            "user_id": request.user_id,
            "thread_id": request.thread_id,
            "turn": request.turn + 1,
            "raw_input": request.raw_input,
            "timestamp": datetime.now().isoformat(),
            "action": request.action,
            "target": request.target,
            "keywords": request.keywords,
            "confidence": 0.1,
            "output_type": "text",
            "output_content": f"❌ {error_msg}",
            "output_data": {"error": error_msg},
            "status": "failed",
            "next": "wait",
            "params": request.params
        }
    
    def _format_workflow_results(self, results: Dict) -> str:
        """格式化工作流结果"""
        lines = []
        for step, result in results.items():
            content = result.get("output_content", result.get("response", ""))
            if content:
                lines.append(f"📌 {step}: {content[:100]}")
        return "\n".join(lines) if lines else "工作流执行完成"
