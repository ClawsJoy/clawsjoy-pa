#!/usr/bin/env python3
"""测试 JSON 标准库"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.lib.json_builder import StandardJSONBuilder
from core.lib.json_serializer import LLMFriendlySerializer
from core.lib.json_standard import Action, Condition, StandardJSON, Workflow, WorkflowStep


def test_simple_json():
    """测试简单 JSON（纯扁平）"""
    print("\n" + "=" * 50)
    print("测试1: 简单 JSON（纯扁平）")

    builder = StandardJSONBuilder()
    json_obj = builder.simple("play", "media", "播放周杰伦的歌").with_keywords("周杰伦").with_user("alice").build()

    print(f"Action: {json_obj.action}")
    print(f"Target: {json_obj.target}")
    print(f"Keywords: {json_obj.keywords}")
    print(f"Is simple: {json_obj.is_simple()}")

    assert json_obj.action == "play"
    assert json_obj.target == "media"
    assert "周杰伦" in json_obj.keywords
    assert json_obj.is_simple() == True

    print("✅ 简单 JSON 测试通过")
    return json_obj


def test_workflow_json():
    """测试工作流 JSON（浅嵌套）"""
    print("\n" + "=" * 50)
    print("测试2: 工作流 JSON（浅嵌套）")

    builder = StandardJSONBuilder()
    json_obj = (
        builder.simple("workflow", "composite")
        .workflow("parallel")
        .add_step("analyze", "finance")
        .add_step("generate", "chart", depends_on=["analyze"])
        .merge_with("send", "email")
        .with_user("bob")
        .build()
    )

    print(f"Action: {json_obj.action}")
    print(f"Workflow mode: {json_obj.workflow.mode}")
    print(f"Steps count: {len(json_obj.workflow.steps)}")
    print(f"Is complex: {json_obj.is_complex()}")

    assert json_obj.action == "workflow"
    assert json_obj.workflow is not None
    assert len(json_obj.workflow.steps) == 2
    assert json_obj.workflow.steps[1].depends_on == ["analyze"]
    assert json_obj.is_complex() == True

    print("✅ 工作流 JSON 测试通过")
    return json_obj


def test_condition_json():
    """测试条件分支 JSON"""
    print("\n" + "=" * 50)
    print("测试3: 条件分支 JSON")

    builder = StandardJSONBuilder()
    json_obj = (
        builder.simple("analyze", "data")
        .condition("result.score", "gt", 0.8)
        .then("send", "email", recipient="boss@company.com")
        .else_("save", "draft")
        .with_user("carol")
        .build()
    )

    print(f"Condition field: {json_obj.condition.field}")
    print(f"Condition operator: {json_obj.condition.operator}")
    print(f"Then action: {json_obj.condition.then.action}")

    assert json_obj.condition is not None
    assert json_obj.condition.field == "result.score"
    assert json_obj.condition.operator == "gt"
    assert json_obj.condition.then.action == "send"

    print("✅ 条件分支 JSON 测试通过")
    return json_obj


def test_serialization():
    """测试序列化/反序列化"""
    print("\n" + "=" * 50)
    print("测试4: 序列化/反序列化")

    original = StandardJSONBuilder().simple("chat", "text", "你好").with_keywords("你好").with_user("test").build()

    serializer = LLMFriendlySerializer()

    simple_str = serializer.serialize(original)
    print(f"Simple serialized: {simple_str[:50]}...")

    compressed = serializer.compress_for_llm(original)
    print(f"Compressed: {compressed}")

    reconstructed = StandardJSON.from_dict(original.to_dict())
    assert reconstructed.action == original.action

    print("✅ 序列化测试通过")


if __name__ == "__main__":
    print("🧪 测试 JSON 标准库")

    test_simple_json()
    test_workflow_json()
    test_condition_json()
    test_serialization()

    print("\n" + "=" * 50)
    print("🎉 所有 JSON 标准库测试通过！")
