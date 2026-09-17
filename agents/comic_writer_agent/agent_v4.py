#!/usr/bin/env python3
"""ComicWriterAgent v5.0 - 漫剧剧本创作专家"""

from typing import Dict, Optional, Tuple

from core.agents.business.business_agent import BusinessAgent


class ComicWriterAgentV4(BusinessAgent):
    name = "comic_writer_agent"
    description = "漫剧剧本创作专家"
    version = "5.0.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        print(f"🎬 ComicWriterAgent v{self.version}")

    def can_handle_json(self, action: str, target: str) -> Tuple[bool, float]:
        return (True, 0.85)

    def _execute_business(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        t = user_input.lower()

        if "大纲" in t or "故事梗概" in t:
            return self._outline(user_input)
        elif "人物" in t or "角色" in t:
            return self._characters(user_input)
        elif "分镜" in t or "剧本" in t:
            return self._storyboard(user_input)
        else:
            return self._full_pipeline(user_input)

    def _full_pipeline(self, user_input: str) -> Dict:
        """完整流水线：大纲→人物→小说→分镜剧本"""
        # 1. 大纲
        outline = self._call_llm(
            f"为漫剧创作故事大纲(200字内)，含核心冲突、三幕结构：\n\n{user_input}",
            task_type="outline"
        )
        if not outline:
            return self._resp("大纲生成失败")

        # 2. 人物
        characters = self._call_llm(
            f"基于大纲设计3-5个角色(姓名/性格/动机/关系)：\n\n{outline}",
            task_type="character"
        )

        # 3. 小说
        novel = self._call_llm(
            f"""创作短篇小说(1500-2000字)，要求画面感强、对话丰富。

大纲：{outline}
角色：{characters or '自行设计'}

要求：清晰的三幕结构、情感真实、适合改编漫剧""",
            task_type="novel"
        )
        if not novel:
            return self._resp("小说生成失败")

        # 4. 分镜剧本
        storyboard = self._to_storyboard(novel)
        if not storyboard:
            return self._resp(f"## 大纲\n{outline}\n\n## 小说\n{novel}\n\n(分镜转换失败)")

        return self._resp(
            f"## 📋 大纲\n{outline}\n\n"
            f"## 👥 角色\n{characters or '见小说'}\n\n"
            f"## 📖 小说(节选)\n{novel[:500]}...\n\n"
            f"## 🎬 分镜剧本\n{storyboard}"
        )

    def _outline(self, user_input: str) -> Dict:
        result = self._call_llm(
            f"为漫剧创作详细故事大纲，含核心冲突、三幕结构、情感高潮：\n\n{user_input}",
            task_type="outline"
        )
        return self._resp(f"## 📋 故事大纲\n\n{result}" if result else "大纲生成失败")

    def _characters(self, user_input: str) -> Dict:
        result = self._call_llm(
            f"设计漫剧角色(3-5个)，含姓名/年龄/外貌/性格/动机/关系/弧光：\n\n{user_input}",
            task_type="character"
        )
        return self._resp(f"## 👥 角色设定\n\n{result}" if result else "角色设计失败")

    def _storyboard(self, user_input: str) -> Dict:
        novel = user_input
        if len(novel) < 100:
            # 用户给的是主题，先生成小说
            novel = self._call_llm(
                f"创作短篇小说(1000-1500字)，画面感强：\n\n{user_input}",
                task_type="novel"
            )
        storyboard = self._to_storyboard(novel)
        return self._resp(storyboard or "分镜转换失败")

    def _to_storyboard(self, novel: str) -> str:
        """小说→分镜剧本，带格式校验和重试"""
        prompt = f"""将小说转换为漫剧分镜剧本：

【规则】
1. 分为3集，每集3-5个分镜
2. 每个分镜格式必须为：
### 分镜X | 景别(特写/近景/中景/全景) | 角度(俯视/平视/仰视)
画面：[画面描述]
对话：[角色名]: [台词]
情感：[情感标注]
3. 每集结尾有集末钩子

【小说】
{novel[:4000]}

输出："""

        for attempt in range(2):
            result = self._call_llm(prompt, task_type="storyboard")
            if result and "### 分镜" in result:
                return f"## 🎬 分镜剧本\n\n{result}"
            prompt += "\n\n【重要】每个分镜必须以 ### 分镜X | 景别 | 角度 开头"

        return ""

    def _resp(self, content: str, **kwargs) -> Dict:
        return {"success": True, "response": content, "output_content": content, **kwargs}


if __name__ == "__main__":
    agent = ComicWriterAgentV4("test")
    print(agent.process("AI觉醒")["response"][:300])
