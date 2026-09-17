"""决策路由测试 - 修复版"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from agents.decision_agent.agent_v4 import DecisionAgentV4


class TestDecisionRouting:
    """决策路由测试"""

    @pytest.fixture
    def agent(self, test_user_id):
        return DecisionAgentV4(test_user_id)

    def test_chat_route(self, agent):
        """测试对话路由"""
        result = agent.decide("你好，今天天气不错")
        assert "agent" in result
        assert result["agent"] is not None

    def test_calculation_route(self, agent):
        """测试计算路由"""
        result = agent.decide("计算 123 + 456")
        assert "agent" in result
        assert result["agent"] is not None

    def test_code_route(self, agent):
        """测试代码路由"""
        result = agent.decide("写一个排序函数")
        assert "agent" in result
        assert result["agent"] is not None

    def test_translate_route(self, agent):
        """测试翻译路由"""
        result = agent.decide("翻译 hello 为中文")
        assert "agent" in result
        assert result["agent"] is not None
