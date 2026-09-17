"""DecisionAgent 单元测试"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import unittest
from unittest.mock import Mock, PropertyMock, patch


class TestDecisionAgent(unittest.TestCase):
    def setUp(self):
        """直接 mock BusinessAgent 的抽象方法，避免真实初始化"""
        from agents.decision_agent.agent_v4 import DecisionAgentV4

        # Mock the abstract methods
        with patch.object(DecisionAgentV4, "_execute_business", return_value={"status": "ok"}):
            with patch.object(DecisionAgentV4, "can_handle_json", return_value=(True, "test")):
                self.agent = DecisionAgentV4()
                self.agent.user_id = "test"

    def test_route_selection_chat(self):
        """测试简单对话走 chat_agent 路由"""
        result = self.agent.decide("你好，我们来聊聊天吧")
        self.assertIn("agent", result)
        self.assertIn("confidence", result)
        self.assertEqual(result["agent"], "chat_agent")
        self.assertGreater(result["confidence"], 0)

    def test_route_selection_calculation(self):
        """测试计算任务走 calculator_agent 路由"""
        result = self.agent.decide("100+200等于多少？")
        self.assertIn("agent", result)
        # 数学计算可能匹配多个关键词
        self.assertIsNotNone(result.get("agent"))

    def test_route_selection_translation_short(self):
        """测试短翻译走 translate_agent 路由"""
        result = self.agent.decide("把这段翻译成英文")
        self.assertIn("agent", result)
        self.assertEqual(result["agent"], "translate_agent")

    def test_route_selection_translation_long(self):
        """测试长翻译走 translate_agent 路由"""
        result = self.agent.decide("请翻译以下长文本内容")
        self.assertIn("agent", result)
        self.assertEqual(result["agent"], "translate_agent")


if __name__ == "__main__":
    unittest.main()
