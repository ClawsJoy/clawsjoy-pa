"""Analysis Agent 单元测试"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from agents.analysis_agent.agent_v4 import AnalysisAgentV4 as AnalysisAgentV4


class TestAnalysisAgentV4:
    """Analysis Agent V4 测试"""

    @pytest.fixture
    def agent(self, test_user_id):
        return AnalysisAgentV4(test_user_id)

    def test_analysis_without_data(self, agent):
        """测试无数据时的分析"""
        result = agent.process("分析销售数据")
        assert result is not None
        assert "response" in result
        assert result["response"] != ""

    def test_identify_type(self, agent):
        """测试类型识别"""
        assert agent._identify_type("销售数据分析") == "销售数据"
        assert agent._identify_type("用户行为分析") == "用户数据"
        assert agent._identify_type("财务报告") == "财务数据"
        assert agent._identify_type("普通问题") == "通用数据"
