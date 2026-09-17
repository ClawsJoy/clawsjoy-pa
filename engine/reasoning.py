"""推理引擎 v3.0 - 智能决策核心"""

from typing import Dict, List, Optional


class ReasoningEngine:
    """推理引擎 - 负责智能决策"""
    
    def __init__(self):
        print("🔧 reasoning 引擎已初始化")
        self.version = "3.0.0"
    
    def decide(self, request: Dict) -> Dict:
        """
        做出决策
        
        Args:
            request: {
                "input": 用户输入,
                "context": 上下文,
                "user_id": 用户ID,
                "available_agents": 可用Agent列表
            }
        
        Returns:
            {
                "decision": "A" | "B" | "C",
                "confidence": 0.0-1.0,
                "reasoning": ["理由1", "理由2"],
                "framework": {}  # 可选，提供给编排层的框架
            }
        """
        user_input = request.get("input", "")
        context = request.get("context", {})
        
        input_lower = user_input.lower()
        reasoning = []
        
        # 复杂度评估
        is_complex = self._is_complex_task(user_input)
        # 多意图检测
        has_multiple_intents = self._has_multiple_intents(user_input)
        # 是否需要编排
        needs_orchestration = is_complex or has_multiple_intents
        
        if needs_orchestration:
            reasoning.append("任务复杂度高，需要多步处理")
            if has_multiple_intents:
                reasoning.append("检测到多个子任务，需要编排协作")
            
            # 识别任务类型，生成框架
            framework = self._build_framework(user_input)
            
            return {
                "decision": "C",
                "confidence": 0.85 if is_complex else 0.75,
                "reasoning": reasoning,
                "framework": framework
            }
        
        # 简单单步任务判断
        if self._is_calculation(user_input):
            reasoning.append("数学计算任务，可直接执行")
            return {"decision": "B", "confidence": 0.95, "reasoning": reasoning, "framework": {}}
        
        if self._is_translation(user_input):
            reasoning.append("翻译任务，可直接执行")
            return {"decision": "B", "confidence": 0.90, "reasoning": reasoning, "framework": {}}
        
        # 默认对话
        reasoning.append("简单对话任务")
        return {"decision": "A", "confidence": 0.80, "reasoning": reasoning, "framework": {}}
    
    def _is_complex_task(self, text: str) -> bool:
        """判断是否为复杂任务"""
        complex_keywords = ["分析", "总结", "报告", "研究", "调研", "评估", "规划"]
        text_lower = text.lower()
        return any(kw in text_lower for kw in complex_keywords)
    
    def _has_multiple_intents(self, text: str) -> bool:
        """检测是否有多个意图"""
        intent_keywords = ["分析", "写", "总结", "翻译", "计算", "查找"]
        text_lower = text.lower()
        found = [kw for kw in intent_keywords if kw in text_lower]
        return len(found) >= 2
    
    def _is_calculation(self, text: str) -> bool:
        """判断是否为计算任务"""
        calc_indicators = ["计算", "加", "减", "乘", "除", "等于", "多少", "求和", "平均"]
        return any(ind in text for ind in calc_indicators)
    
    def _is_translation(self, text: str) -> bool:
        """判断是否为翻译任务"""
        return "翻译" in text.lower()
    
    def _build_framework(self, user_input: str) -> Dict:
        """为编排层构建任务框架"""
        framework = {
            "type": "analysis_and_writing",
            "steps": [],
            "requires": []
        }
        
        if "分析" in user_input:
            framework["steps"].append({
                "name": "analysis",
                "agent": "analysis_agent",
                "action": "分析数据"
            })
            framework["requires"].append("analysis_result")
        
        if "写" in user_input or "总结" in user_input:
            framework["steps"].append({
                "name": "writing",
                "agent": "writer_agent",
                "action": "撰写报告",
                "depends_on": "analysis_result"
            })
        
        return framework


reasoning_engine = ReasoningEngine()
