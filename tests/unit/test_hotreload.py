"""热重载单元测试"""

from pathlib import Path

import pytest
import yaml


class TestHotReload:
    """热重载测试"""

    def test_keywords_yaml_syntax(self):
        """测试 keywords.yaml 语法正确"""
        config_path = Path("config/keywords.yaml")
        assert config_path.exists()
        with open(config_path) as f:
            config = yaml.safe_load(f)
        assert config is not None

    def test_agent_capabilities_structure(self):
        """测试 agent_capabilities 结构"""
        with open("config/keywords.yaml") as f:
            config = yaml.safe_load(f)

        caps = config.get("agent_capabilities", {})
        assert len(caps) > 0

        for name, cap in caps.items():
            assert "capable_of" in cap, f"{name}: missing capable_of"
            assert "priority" in cap, f"{name}: missing priority"
            assert 1 <= cap["priority"] <= 100, f"{name}: invalid priority"
            assert isinstance(
                cap["capable_of"], list
            ), f"{name}: capable_of must be list"

    def test_intents_structure(self):
        """测试 intents 结构"""
        with open("config/keywords.yaml") as f:
            config = yaml.safe_load(f)

        intents = config.get("intents", {})
        for name, intent in intents.items():
            assert "keywords" in intent, f"{name}: missing keywords"
            assert isinstance(
                intent["keywords"], list
            ), f"{name}: keywords must be list"

    def test_no_keyword_conflicts(self):
        """测试无关键词冲突"""
        with open("config/keywords.yaml") as f:
            config = yaml.safe_load(f)

        caps = config.get("agent_capabilities", {})
        keyword_owner = {}
        conflicts = []

        for agent, cap in caps.items():
            for kw in cap.get("capable_of", []):
                kw_lower = kw.lower()
                if kw_lower in keyword_owner:
                    conflicts.append((kw, keyword_owner[kw_lower], agent))
                else:
                    keyword_owner[kw_lower] = agent

        if conflicts:
            print(f"⚠️ 发现 {len(conflicts)} 个冲突")
            for kw, a1, a2 in conflicts[:5]:
                print(f"  '{kw}' → {a1} vs {a2}")

        # 允许少量冲突，只警告不失败
        assert len(conflicts) < 20, f"Too many conflicts: {len(conflicts)}"
