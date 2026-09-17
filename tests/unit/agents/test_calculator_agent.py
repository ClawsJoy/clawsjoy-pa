"""Calculator Agent 单元测试"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from agents.calculator_agent.agent_v4 import CalculatorAgentV4


class TestCalculatorAgentV4:
    """Calculator Agent V4 测试"""

    @pytest.fixture
    def agent(self, test_user_id):
        return CalculatorAgentV4(test_user_id)

    def test_basic_addition(self, agent):
        """测试加法"""
        result = agent.process("1 + 2")
        assert result["success"] is True
        assert "🔢 结果：**3**" in result["response"]

    def test_subtraction(self, agent):
        """测试减法"""
        result = agent.process("10 - 3")
        assert result["success"] is True
        assert "🔢 结果：**7**" in result["response"]

    def test_multiplication(self, agent):
        """测试乘法"""
        result = agent.process("5 * 6")
        assert result["success"] is True
        assert "🔢 结果：**30**" in result["response"]

    def test_division(self, agent):
        """测试除法"""
        result = agent.process("10 / 2")
        assert result["success"] is True
        # 10/2=5.0 会被转换为整数 5
        assert "🔢 结果：**5**" in result["response"]

    def test_scientific_sin(self, agent):
        """测试 sin 函数"""
        result = agent.process("sin(0)")
        assert result["success"] is True
        assert "0" in result["response"] or "0" in str(result["output_content"])

    def test_scientific_sqrt(self, agent):
        """测试 sqrt 函数"""
        result = agent.process("sqrt(16)")
        assert result["success"] is True
        assert "4" in result["response"] or "4" in str(result["output_content"])
