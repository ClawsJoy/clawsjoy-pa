"""Code Agent 单元测试"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from agents.code_agent.agent_v4 import CodeAgentV4 as CodeAgentV4


class TestCodeAgentV4:
    """Code Agent V4 测试"""

    @pytest.fixture
    def agent(self, test_user_id):
        return CodeAgentV4(test_user_id)

    @pytest.fixture
    def sample_code(self):
        return '''
def hello():
    print("hello world")

def add(a, b):
    return a + b
'''

    @pytest.fixture
    def sample_code_with_issues(self):
        return '''
def unsafe():
    eval(input())
    for i in range(10):
        for j in range(10):
            print(i*j)
    try:
        result = 1/0
    except Exception:
        pass
'''

    def test_analyze_code_basic(self, agent, sample_code):
        """测试基本代码分析"""
        result = agent.process("分析代码\n" + sample_code)
        assert result["success"] is True

    def test_analyze_code_with_issues(self, agent, sample_code_with_issues):
        """测试问题代码分析"""
        result = agent.process("分析代码\n" + sample_code_with_issues)
        assert result["success"] is True

    def test_deep_review(self, agent, sample_code):
        """测试深度审查"""
        result = agent.process("审查代码\n" + sample_code)
        assert result["success"] is True

    def test_format_code(self, agent):
        """测试代码格式化"""
        bad_code = "def hello():print('hello')"
        result = agent.process("修复代码\n" + bad_code)
        assert result["success"] is True

    def test_generate_code(self, agent):
        """测试代码生成"""
        result = agent.process("写一个加法函数")
        assert result["success"] is True
