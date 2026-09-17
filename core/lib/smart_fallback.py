#!/usr/bin/env python3
"""智能 Fallback - 上下文感知引导 + 能力推荐 + 多轮记忆"""

from typing import Optional, List, Dict
from core.lib.llm_client import llm_client


def smart_fallback(agent_name: str, user_input: str, description: str = "",
                   capabilities: List[str] = None, history: List[str] = None,
                   user_profile: Dict = None) -> str:
    """生成上下文感知的引导回复

    Args:
        agent_name: 当前Agent名称
        user_input: 用户输入
        description: Agent能力描述
        capabilities: Agent具体能力列表
        history: 最近对话历史
        user_profile: 用户画像 {name, preferences, level}
    """

    # 构建丰富的上下文
    context_parts = []

    # 用户画像
    if user_profile:
        if user_profile.get("name"):
            context_parts.append(f"用户姓名: {user_profile['name']}")
        if user_profile.get("level"):
            context_parts.append(f"用户等级: {user_profile['level']}")
        if user_profile.get("preferences"):
            prefs = user_profile["preferences"]
            if isinstance(prefs, list):
                context_parts.append(f"用户偏好: {', '.join(prefs[:5])}")

    # 对话历史
    if history:
        recent = history[-3:]
        context_parts.append("最近对话:")
        for h in recent:
            context_parts.append(f"  {h}")

    # Agent能力
    cap_text = ""
    if capabilities:
        cap_text = f"\n我的能力包括：{'、'.join(capabilities[:8])}"
        if len(capabilities) > 8:
            cap_text += f"等共{len(capabilities)}项能力"

    context_str = "\n".join(context_parts) if context_parts else ""

    # 根据用户输入类型选择不同策略
    input_type = _classify_input(user_input)

    if input_type == "vague":
        guide_style = "用户输入过于简短模糊，请用具体例子引导用户说明需求。"
    elif input_type == "out_of_scope":
        guide_style = f"用户需求超出了我的能力范围。{cap_text}\n请友好地说明我能做什么，并引导用户调整需求。"
    elif input_type == "incomplete":
        guide_style = "用户指令不完整，请询问缺失的关键信息（如具体内容、格式、长度等）。"
    elif input_type == "error":
        guide_style = "用户之前的操作可能出错了，请先表达理解，然后给出排查建议或替代方案。"
    else:
        guide_style = "请理解用户意图，如果无法直接处理，用问句引导用户重新描述。"

    prompt = f"""{context_str}
用户说: "{user_input}"

我是 {agent_name}，{description}。{cap_text}

{guide_style}

要求:
- 不要用"我不知道"、"无法处理"等否定表达
- 给出2-3个具体可操作的建议
- 使用友好、鼓励的语气
- 如果合适，用问句引导用户

输出（直接回复用户，2-4句话）："""

    try:
        reply = llm_client.generate(
            prompt=prompt,
            model="qwen2.5:7b-instruct-q4_0-gpu",
            temperature=0.7,
            max_tokens=150,
            timeout=15,
            task_type="fallback"
        )
        if reply and len(reply.strip()) > 5:
            return reply.strip()
    except Exception:
        pass

    # 降级：基于能力的智能引导
    if capabilities:
        examples = _pick_examples(capabilities[:4])
        return f"💡 我可以帮你{examples}。你想试试哪个？"
    return f"💡 请告诉我更具体的信息，我会尽力帮你。比如：你想让我做什么？"


def smart_help(agent_name: str, capabilities: list,
               examples: List[str] = None) -> str:
    """生成能力说明"""
    if not capabilities:
        return f"💡 我是 {agent_name}，有什么可以帮你的？"

    caps = "、".join(capabilities[:6])
    result = f"💡 我是 {agent_name}，可以帮你 {caps}"

    if len(capabilities) > 6:
        result += f"等共{len(capabilities)}项能力"

    if examples:
        result += f"\n\n试试对我说：\n" + "\n".join(f"  • {e}" for e in examples[:3])

    result += "\n\n需要我做什么？"
    return result


def _classify_input(user_input: str) -> str:
    """分类用户输入类型"""
    t = user_input.strip()
    if len(t) <= 3:
        return "vague"
    if any(kw in t for kw in ["报错", "错误", "失败", "不行", "没用", "坏了"]):
        return "error"
    if any(kw in t for kw in ["帮我", "能不能", "可以", "怎么做", "如何"]):
        return "incomplete"
    if any(kw in t for kw in ["画", "视频", "音乐", "游戏", "打电话"]):
        return "out_of_scope"
    return "general"


def _pick_examples(capabilities: List[str]) -> str:
    """从能力中挑选示例表述"""
    example_map = {
        "聊天": "陪你聊天解闷",
        "写代码": "帮你写代码",
        "翻译": "翻译各种语言",
        "分析": "分析数据或文本",
        "计算": "帮你算数学题",
        "写文章": "写文章、故事、报告",
        "搜索": "搜索你需要的信息",
        "记忆": "记住你说过的重要信息",
    }
    picked = []
    for cap in capabilities:
        for key, example in example_map.items():
            if key in cap and example not in picked:
                picked.append(example)
                break
    if not picked:
        picked = [f"{capabilities[0]}" if capabilities else "处理你的需求"]
    return "、".join(picked[:3])
