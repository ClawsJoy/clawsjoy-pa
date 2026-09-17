"""引擎统一接口测试"""

import pytest

from engine import engine


class TestEngineInterface:
    """引擎统一接口测试"""

    def test_engine_import(self):
        """测试引擎导入"""
        assert engine is not None

    def test_engine_has_semantic(self):
        """测试语义引擎存在"""
        assert hasattr(engine, "semantic")

    def test_engine_has_skill(self):
        """测试技能引擎存在"""
        assert hasattr(engine, "skill")

    def test_engine_has_event(self):
        """测试事件引擎存在"""
        assert hasattr(engine, "event")

    def test_engine_has_monitor(self):
        """测试监控引擎存在"""
        assert hasattr(engine, "monitor")

    def test_semantic_process(self):
        """测试语义处理"""
        result = engine.semantic.process("测试")
        assert result is not None

    def test_skill_process(self):
        """测试技能处理"""
        result = engine.skill.process("测试")
        assert result is not None
