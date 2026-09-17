"""思维链推理增强"""

from typing import Dict, List, Any


class ReasoningChain:
    """思维链推理器"""
    
    @staticmethod
    def think_step_by_step(question: str, answer: str) -> str:
        """将答案转换为逐步推理"""
        # 检测数学问题
        if any(op in question for op in ['+', '-', '*', '/', '计算', '等于']):
            return ReasoningChain._math_reasoning(question, answer)
        # 检测逻辑问题
        elif any(word in question for word in ['如果', '那么', '因为', '所以', '推理']):
            return ReasoningChain._logic_reasoning(question, answer)
        return answer
    
    @staticmethod
    def _math_reasoning(question: str, answer: str) -> str:
        """数学推理步骤"""
        return f"""【推理步骤】
1. 分析问题：{question}
2. 确定运算方法
3. 逐步计算
4. 得出结果

【答案】{answer}"""
    
    @staticmethod
    def _logic_reasoning(question: str, answer: str) -> str:
        """逻辑推理步骤"""
        return f"""【逻辑推理】
前提条件分析
↓
逻辑推导
↓
得出结论

{answer}"""


reasoning_chain = ReasoningChain()
