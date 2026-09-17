"""意图路由器单元测试

修复(测试污染): 原模块级 sys.modules['engine.semantic'] mock 注入会污染
全局——全量跑时前序测试若已真实加载 engine.semantic/smart_intent_router,
mock 注入失效 -> route 用真实语义引擎 -> intent 变 None(chat/code/translate 失败)。
改为 setUpClass 注入 + tearDownClass 恢复, 类测试结束不残留。
同时防御 INTENT_TO_AGENT 类变量被 reload_config 覆盖(快照恢复)。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import unittest
from unittest.mock import MagicMock


class TestIntentRouter(unittest.TestCase):
    """意图路由测试(mock engine 隔离, 类级注入+恢复)"""

    @classmethod
    def setUpClass(cls):
        # 保存原 engine 模块状态(全量顺序下可能已被真实加载)
        cls._orig_engine = sys.modules.get('engine')
        cls._orig_semantic = sys.modules.get('engine.semantic')
        # 注入 mock(sandbox engine 残缺时 import smart_intent_router 必需)
        cls._mock_semantic = MagicMock()

        def _understand_side_effect(message):
            # 按输入返回对应 intent(精确断言需要: 不同消息路由到不同 agent)
            _msg = str(message or "")
            _r = MagicMock()
            if "100" in _msg or "+" in _msg:
                _r.intent = "math"
            elif "翻译" in _msg:
                _r.intent = "translate"
            elif "天气" in _msg:
                _r.intent = "weather"
            else:
                _r.intent = "chat"
            _r.confidence = 0.9
            return _r

        cls._mock_semantic.understand.side_effect = _understand_side_effect
        cls._mock_engine_semantic = MagicMock()
        cls._mock_engine_semantic.semantic_engine = cls._mock_semantic
        sys.modules['engine'] = MagicMock()
        sys.modules['engine.semantic'] = cls._mock_engine_semantic

        from core.lib.smart_intent_router import SmartIntentRouter
        cls.RouterCls = SmartIntentRouter
        # INTENT_TO_AGENT 类变量快照(防 reload_config 覆盖导致反推 intent=None)
        cls._intent_snapshot = dict(SmartIntentRouter.INTENT_TO_AGENT)

    @classmethod
    def tearDownClass(cls):
        # 恢复 engine 模块, 不污染其他测试
        if cls._orig_semantic is not None:
            sys.modules['engine.semantic'] = cls._orig_semantic
        elif 'engine.semantic' in sys.modules:
            del sys.modules['engine.semantic']
        if cls._orig_engine is not None:
            sys.modules['engine'] = cls._orig_engine
        elif 'engine' in sys.modules:
            del sys.modules['engine']
        # 恢复 INTENT_TO_AGENT 类变量
        try:
            cls.RouterCls.INTENT_TO_AGENT = cls._intent_snapshot
        except Exception:
            pass

    def setUp(self):
        self.router = self.RouterCls()

    def tearDown(self):
        # 每个测试后恢复类变量(防御本类测试内部改动)
        self.RouterCls.INTENT_TO_AGENT = dict(self._intent_snapshot)

    def test_math_intent(self):
        """测试数学意图识别(精确断言: 映射到 calculator_agent)"""
        result = self.router.route("100+200")
        self.assertIsNotNone(result)
        self.assertIn('intent', result)
        self.assertIn('agent', result)
        self.assertEqual(result['agent'], 'calculator_agent', f"math 应映射 calculator_agent: {result}")

    def test_translate_intent(self):
        """测试翻译意图(精确断言: 映射到 translate_agent)"""
        result = self.router.route("翻译这段话")
        self.assertIsNotNone(result)
        self.assertIn('agent', result)
        self.assertEqual(result['agent'], 'translate_agent', f"translate 应映射 translate_agent: {result}")

    def test_weather_intent(self):
        """测试天气意图(精确断言: 映射到 weather_skill)"""
        result = self.router.route("今天天气怎么样")
        self.assertIsNotNone(result)
        self.assertIn('agent', result)
        self.assertEqual(result['agent'], 'weather_skill', f"weather 应映射 weather_skill: {result}")


if __name__ == '__main__':
    unittest.main()
