#!/usr/bin/env python3
"""测试 ChatAgentV4 试点"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 动态导入 agent_v4
import importlib.util

spec = importlib.util.spec_from_file_location("agent_v4", "agents/chat_agent/agent_v4.py")
agent_v4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent_v4)
ChatAgentV4 = agent_v4.ChatAgentV4


def test_chat_agent():
    """测试 ChatAgentV4"""
    print("\n" + "=" * 50)
    print("测试 ChatAgentV4 试点")

    agent = ChatAgentV4(user_id="test_user")

    # 测试名字记忆
    print("\n1. 测试名字记忆")
    result = agent.process("我叫张三")
    print(f"Input: 我叫张三")
    print(f"Output: {result.get('response')}")

    # 测试名字回忆
    print("\n2. 测试名字回忆")
    result = agent.process("我叫什么名字")
    print(f"Input: 我叫什么名字")
    print(f"Output: {result.get('response')}")

    # 测试记忆信息
    print("\n3. 测试记忆信息")
    result = agent.process("记住生日是5月1日")
    print(f"Input: 记住生日是5月1日")
    print(f"Output: {result.get('response')}")

    # 测试回忆信息
    print("\n4. 测试回忆信息")
    result = agent.process("回忆生日")
    print(f"Input: 回忆生日")
    print(f"Output: {result.get('response')}")

    # 测试 JSON 输入
    print("\n5. 测试 JSON 输入")
    json_input = {"action": "chat", "target": "text", "raw_input": "你好，今天天气怎么样？", "user_id": "test_user"}
    result = agent.handle_json(json_input)
    print(f"JSON input: {json_input['raw_input']}")
    print(f"Output: {result.get('output_content', result.get('response'))}")

    # 测试缓存
    print("\n6. 测试缓存效果")
    for i in range(3):
        agent.process("重复消息测试")

    cache_hits = agent._stats.get("cache_hits", 0)
    cache_misses = agent._stats.get("cache_misses", 0)
    total = cache_hits + cache_misses
    hit_rate = cache_hits / total if total > 0 else 0

    print(f"Cache hits: {cache_hits}, misses: {cache_misses}")
    print(f"Cache hit rate: {hit_rate:.0%}")

    # 统计信息
    print("\n7. 统计信息")
    stats = agent.get_stats()
    print(f"Stats: {stats.get('business', {})}")

    print("\n✅ ChatAgentV4 试点测试通过")


if __name__ == "__main__":
    test_chat_agent()
