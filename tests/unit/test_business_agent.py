#!/usr/bin/env python3
"""测试 BusinessAgent 基类"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.agents.business.business_agent import BusinessAgent


class TestAgent(BusinessAgent):
    """测试用 Agent"""

    name = "test_agent"
    description = "测试智能体"
    version = "4.0.0"

    def can_handle_json(self, action: str, target: str) -> tuple:
        if action == "test" and target == "text":
            return True, 0.95
        return False, 0.0

    def _execute_business(self, user_input: str, context=None) -> dict:
        return {"success": True, "response": f"处理成功: {user_input}", "output_content": f"处理成功: {user_input}"}


def test_business_agent():
    """测试 BusinessAgent"""
    print("\n" + "=" * 50)
    print("测试 BusinessAgent 基类")

    agent = TestAgent(user_id="test_user")

    # 测试自然语言入口
    print("\n1. 测试 handle() 自然语言入口")
    result = agent.handle("你好")
    print(f"Result: {result.get('response', result.get('output_content'))}")
    assert result.get("success") == True

    # 测试 JSON 入口
    print("\n2. 测试 handle_json() JSON 入口")
    json_input = {"action": "test", "target": "text", "raw_input": "测试 JSON 输入", "user_id": "test_user"}
    result = agent.handle_json(json_input)
    print(f"Result: {result.get('output_content', result.get('response'))}")
    assert result.get("action") == "test"

    # 测试缓存
    print("\n3. 测试缓存")
    first = agent.process("重复消息")
    second = agent.process("重复消息")

    # 安全获取缓存统计
    cache_hits = agent._stats.get("cache_hits", 0)
    cache_misses = agent._stats.get("cache_misses", 0)
    total = cache_hits + cache_misses
    hit_rate = cache_hits / total if total > 0 else 0

    print(f"Cache hits: {cache_hits}, misses: {cache_misses}")
    print(f"Cache hit rate: {hit_rate:.0%}")
    assert cache_hits >= 1

    # 测试统计
    print("\n4. 测试统计")
    stats = agent.get_stats()
    print(f"Stats keys: {list(stats.keys())}")

    print("\n✅ BusinessAgent 测试通过")


if __name__ == "__main__":
    test_business_agent()
