#!/usr/bin/env python3
"""WriterAgent v5.0 - 智慧型写作伙伴（核心写作能力）"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from core.agents.business.business_agent import BusinessAgent


class WriterAgentV4(BusinessAgent):
    """
    写作伙伴 - 核心写作能力

    能力矩阵：
    1. 灵感孵化 → 从创意到完整大纲
    2. 角色工坊 → 深度角色设计
    3. 章节创作 → 保持风格一致，推进情节
    4. 情节编织 → 多线叙事、转折点、情感高潮
    5. 对白打磨 → 符合角色身份的自然对白
    6. 场景构建 → 视觉化场景描述
    7. 风格迁移 → 模仿特定作家风格
    8. 智能润色 → 单章、指定章、整部润色
    9. 修改调整 → 修改内容、修改大纲
    10. 完成定稿 → 统计、总结、状态标记
    """

    name = "writer_agent_v4"
    description = "智慧型写作伙伴"
    version = "5.0.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)

        # ========== 会话 ==========
        self._session_id = None

        # ========== 创作状态（完整） ==========
        self._novel = {
            "title": "",
            "genre": "",
            "theme": "",
            "outline": "",
            "characters": [],
            "chapters": [],
            "scenes": [],
            "hooks": [],
            "plot_points": [],
            "current_chapter": 0,
            "status": "idle",
            "word_count": 0,
            "created_at": None,
            "updated_at": None,
        }

        # ========== 用户偏好（学习） ==========
        self._user_preferences = {
            "writing_style": "默认",
            "preferred_genre": "通用",
            "character_depth": "详细",
            "chapter_length": "medium",
            "auto_save": True,
        }

        # ========== 积木（乐高集成） ==========
        self._soul = None
        self._memory = None
        self._emotion = None
        self._semantic = None
        self._proactive = None

        # ========== LLM 配置 ==========
        self._llm_model = "qwen2.5:7b-instruct-q4_0-gpu"
        self._max_retries = 2

        # ========== 启动 ==========
        self._load_state()
        print(f"✍️ WriterAgent v{self.version} 已启动")
        print(f"   📖 当前状态: {self._novel['status']}")
        print(f"   📚 已写 {len(self._novel['chapters'])} 章")

    # ================================================================
    #  积木（懒加载）
    # ================================================================

    @property
    def soul(self):
        if self._soul is None:
            try:
                from core.lib.soul.soul_injector import SoulInjector

                self._soul = SoulInjector(self.user_id, "writer_agent")
            except Exception as e:
                print(f"[Writer] 加载灵魂注入器失败: {e}")
        return self._soul

    @property
    def memory(self):
        if self._memory is None:
            try:
                from core.lib.memory_layers import MemoryLayers

                self._memory = MemoryLayers()
            except Exception as e:
                print(f"[Writer] 加载记忆系统失败: {e}")
        return self._memory

    @property
    def emotion(self):
        if self._emotion is None:
            try:
                from engine.emotion import emotion_engine

                self._emotion = emotion_engine
            except Exception as e:
                print(f"[Writer] 加载情感引擎失败: {e}")
        return self._emotion

    @property
    def semantic(self):
        if self._semantic is None:
            try:
                from engine.semantic import semantic_engine

                self._semantic = semantic_engine
            except Exception as e:
                print(f"[Writer] 加载语义引擎失败: {e}")
        return self._semantic

    @property
    def proactive(self):
        if self._proactive is None:
            try:
                from core.lib.proactive_service import proactive_service

                self._proactive = proactive_service
            except Exception as e:
                print(f"[Writer] 加载主动服务失败: {e}")
        return self._proactive

    # ================================================================
    #  状态持久化
    # ================================================================
    def _load_state(self):
        """从 memory 和联邦知识恢复创作状态"""
        # 0. 从 memory/ 目录恢复（打底）
        self._load_from_memory_files()

        # 1. 从联邦知识恢复元数据
        self._load_from_federated()

        if not self._session_id or not self.memory:
            return

        try:
            states = self.memory.get_session_memory(self._session_id, limit=20)
            if not states:
                return

            for state_record in reversed(states):
                if not isinstance(state_record, dict):
                    continue

                assistant = state_record.get("assistant", {})

                # 新格式：JSON 字符串
                if isinstance(assistant, str):
                    try:
                        payload = json.loads(assistant)
                        novel_state = payload.get("state")
                        if novel_state and isinstance(novel_state, dict) and novel_state.get("chapters"):
                            if len(novel_state.get("chapters", [])) >= len(self._novel.get("chapters", [])):
                                self._novel = novel_state
                    except Exception:
                        pass
                    continue

                # 旧格式：字典
                if isinstance(assistant, dict):
                    novel_state = assistant.get("state") or assistant.get("novel_state")
                    if novel_state and isinstance(novel_state, dict) and novel_state.get("chapters"):
                        if len(novel_state.get("chapters", [])) >= len(self._novel.get("chapters", [])):
                            self._novel = novel_state
                    continue

                # 更旧格式
                if state_record.get("novel_state"):
                    novel_state = state_record.get("novel_state")
                    if isinstance(novel_state, dict) and novel_state.get("chapters"):
                        if len(novel_state.get("chapters", [])) >= len(self._novel.get("chapters", [])):
                            self._novel = novel_state

        except Exception as e:
            print(f"[Writer] 加载状态失败: {e}")

        if self._novel.get("chapters"):
            print(f"[Writer] ✅ 加载状态: {self._novel.get('title', '未命名')} ({len(self._novel.get('chapters', []))}章)")

    def _save_state(self):
        """保存创作状态到 memory 和联邦知识"""
        # 无条件保存到联邦知识（跨会话）
        self._save_to_federated()

        if not self._session_id:
            return

        # 清洗标题
        def _extract_clean_title() -> str:
            outline = self._novel.get("outline", "")
            if outline:
                lines = outline.split("\n")
                for line in lines[:20]:
                    if "标题" in line or "书名" in line:
                        match = re.search(r"[：:]\s*(.+?)(?=\s*$)", line)
                        if match:
                            candidate = match.group(1).strip()
                            if candidate and len(candidate) < 30 and "【" not in candidate:
                                return candidate
                    match = re.search(r"[《「『]([^》」』]+)[》」』]", line)
                    if match:
                        candidate = match.group(1).strip()
                        if candidate and len(candidate) < 30 and "【" not in candidate:
                            return candidate
            return "未命名作品"

        raw_title = self._novel.get("title", "")
        if "基于以下设定" in raw_title or "【小说大纲" in raw_title:
            self._novel["title"] = _extract_clean_title()

        has_content = self._novel.get("outline") or self._novel.get("chapters") or self._novel.get("status") != "idle"
        if not has_content:
            return

        self._novel["updated_at"] = datetime.now().isoformat()
        self._novel["word_count"] = self._count_words()

        title = self._novel.get("title", "未命名")[:30]
        chapters = len(self._novel.get("chapters", []))
        words = self._novel.get("word_count", 0)
        summary = f"{title} ({chapters}章, {words}字)"

        self._store_state(key="writer_state", business="novel", state=self._novel, summary=summary)

    def _save_to_federated(self):
        """同步到联邦知识"""
        if not self._novel.get("title") or self._novel.get("status") == "idle":
            return
        try:
            from core.lib.federated_bus import federated_bus

            federated_bus.put_knowledge(
                key=f"novel:{self._novel.get('title', '未命名')}",
                value={
                    "title": self._novel.get("title", ""),
                    "status": self._novel.get("status", "idle"),
                    "chapters": len(self._novel.get("chapters", [])),
                    "word_count": self._novel.get("word_count", 0),
                    "genre": self._novel.get("genre", ""),
                    "updated_at": self._novel.get("updated_at", ""),
                },
                source="writer_agent",
                tags=["novel", "writer_state"],
            )
        except Exception:
            pass

    def _save_to_session_file(self):
        """保存到 memory/ 目录的 session 文件"""
        from pathlib import Path

        session_file = Path("memory") / f"session_novel_{self.user_id}.json"
        entry = {
            "user": "writer_state",
            "assistant": json.dumps(
                {"version": "2.5", "business": "novel", "agent": self.name, "state": self._novel}, ensure_ascii=False
            ),
            "timestamp": datetime.now().isoformat(),
        }
        with open(session_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # ================================================================
    #  入口
    # ================================================================

    def process(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        if context and "session_id" in context:
            self._session_id = context["session_id"]
            self._load_state()

        return super().process(user_input, context)

    def can_handle_json(self, action: str, target: str) -> Tuple[bool, float]:
        return (True, 0.85)

    # ================================================================
    #  核心逻辑：感知 → 理解 → 决策 → 执行 → 学习
    # ================================================================

    def _execute_business(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        # skill 模式：直接调 LLM，跳过意图理解
        if context and context.get("skip_intent"):
            text = self._call_llm(user_input)
            return self._resp(text) if text else {"success": False, "response": ""}
        original = user_input

        # ========== 1. 感知层 ==========
        emotion_result = {}
        if self.emotion:
            try:
                emotion_result = self.emotion.analyze(user_input)
            except Exception as e:
                print(f"[Writer] 情感分析失败: {e}")

        semantic_result = None
        if self.semantic:
            try:
                semantic_result = self.semantic.understand(user_input)
            except Exception as e:
                print(f"[Writer] 语义理解失败: {e}")

        soul_context = {}
        if self.soul:
            try:
                soul_context = self.soul.inject(user_input)
            except Exception as e:
                print(f"[Writer] 灵魂注入失败: {e}")

        # ========== 2. 理解层 ==========
        intent = self._understand_intent(user_input, semantic_result, emotion_result)
        print(f"[Writer] 意图: {intent}")

        # ========== 3. 决策与执行 ==========
        handlers = {
            "start_novel": self._handle_start_novel,
            "continue": self._handle_continue,
            "new_chapter": self._handle_new_chapter,
            "character": self._handle_character,
            "scene": self._handle_scene,
            "plot": self._handle_plot,
            "hook": self._handle_hook,
            "dialogue": self._handle_dialogue,
            "polish": self._handle_polish,
            "style": self._handle_style,
            "modify": self._handle_modify,
            "outline": self._handle_outline,
            "complete": self._handle_complete,
            "write": self._handle_write,
        }

        handler = handlers.get(intent, self._handle_write)
        result = handler(user_input, semantic_result, emotion_result, soul_context)

        # ========== 4. 学习层 ==========
        self._learn(user_input, result, intent)
        self._save_state()

        # ========== 5. 响应 ==========
        return self._resp(result)

    # ================================================================
    #  意图理解
    # ================================================================

    def _understand_intent(self, user_input: str, semantic: Any, emotion: Dict) -> str:
        """由 LLM 理解意图，语义引擎优先，关键词降级"""
        text = user_input.lower()

        # 1. 尝试用语义引擎
        if semantic:
            try:
                if hasattr(semantic, "classify_intent"):
                    result = semantic.classify_intent(user_input)
                    if result:
                        return result
                elif hasattr(semantic, "understand"):
                    result = semantic.understand(user_input)
                    if result and isinstance(result, dict):
                        intent = result.get("intent")
                        if intent:
                            return intent
            except Exception as e:
                print(f"[Writer] 语义引擎意图识别失败: {e}")

        # 2. 尝试用 LLM
        try:
            intent_prompt = f"""分析用户对小说创作的意图，只输出一个单词。

用户输入："{user_input}"

意图说明：
- complete: 用户询问进度/状态，或说"完成了吗"、"写到哪了"、"怎么样了"、"小说完成了吗"
- continue: 用户想继续写、接着写
- write: 用户想写新内容
- outline: 大纲相关
- character: 角色相关
- start_novel: 开始新小说
- polish: 润色优化

可选意图：start_novel, continue, new_chapter, character, scene, plot, hook, dialogue, polish, style, modify, outline, complete, write

输出（只输出一个词）："""
            response = self._call_llm(intent_prompt, task_type="intent")
            if response and response.strip() in [
                "start_novel",
                "continue",
                "new_chapter",
                "character",
                "scene",
                "plot",
                "hook",
                "dialogue",
                "polish",
                "style",
                "modify",
                "outline",
                "complete",
                "write",
            ]:
                return response.strip()
        except Exception as e:
            print(f"[Writer] LLM 意图识别失败: {e}")

        # 3. 降级：关键词匹配（状态查询优先）
        # 状态/进度查询
        if any(kw in text for kw in ["完成了吗", "写完了吗", "到哪了", "到哪一步", "进度", "状态", "好了吗", "怎么样了", "写了多少"]):
            return "complete"
        # 完成/定稿
        if any(kw in text for kw in ["完成", "定稿", "写完了", "发布"]):
            return "complete"
        # 继续/接着
        if any(kw in text for kw in ["继续", "接着写", "然后呢", "再写", "下一章", "新章节"]):
            return "continue"
        # 查询作品
        if any(kw in text for kw in ["小说", "作品", "故事", "写了什么", "在写什么"]):
            return "complete"
        # 创作开始
        if any(kw in text for kw in ["写小说", "创作小说", "开始写", "新小说", "写一个"]):
            return "start_novel"
        # 润色/优化
        if any(kw in text for kw in ["润色", "优化", "美化"]):
            return "polish"
        # 角色
        if any(kw in text for kw in ["角色", "人物", "主角", "配角"]):
            return "character"
        # 场景
        if any(kw in text for kw in ["场景", "环境", "背景"]):
            return "scene"
        # 情节
        if any(kw in text for kw in ["情节", "剧情", "转折", "冲突"]):
            return "plot"
        # 大纲
        if any(kw in text for kw in ["大纲", "框架", "结构"]):
            return "outline"
        # 修改
        if any(kw in text for kw in ["修改", "改成", "调整"]):
            return "modify"
        # 风格
        if any(kw in text for kw in ["风格", "模仿", "像"]):
            return "style"
        # 对白
        if any(kw in text for kw in ["对白", "对话", "台词"]):
            return "dialogue"
        # 钩子
        if any(kw in text for kw in ["钩子", "悬念", "伏笔"]):
            return "hook"

        return "write"

    # ================================================================
    #  意图处理器
    # ================================================================

    def _handle_start_novel(self, user_input: str, semantic: Any, emotion: Dict, soul: Dict) -> str:
        """① 灵感孵化 → 完整大纲"""
        topic = re.sub(r"^(写小说|创作小说|开始写小说|新小说)", "", user_input).strip()
        if not topic:
            topic = "一个动人的故事"

        genre = "通用"
        for g in ["科幻", "奇幻", "悬疑", "爱情", "动作", "喜剧", "悲剧", "史诗"]:
            if g in user_input:
                genre = g
                break

        self._novel["title"] = f"《{topic[:20]}》"
        self._novel["genre"] = genre
        self._novel["theme"] = topic
        self._novel["status"] = "outlining"

        prompt = f"""
请为一篇小说创作完整大纲：

主题：{topic}
体裁：{genre}

要求：
1. 三幕结构（开端-发展-高潮-结局）
2. 主要角色（至少2个，含姓名、性格、动机）
3. 核心冲突
4. 故事主线
5. 情感主题
6. 预计章节数

输出格式：Markdown
"""
        outline = self._call_llm(prompt)
        self._novel["outline"] = outline
        self._novel["status"] = "outlining"
        self._novel["created_at"] = datetime.now().isoformat()
        self._save_state()

        return f"""
## 📋 小说大纲：《{topic[:20]}》

**体裁**：{genre}

{outline}

---

💡 **下一步建议：**
- 输入「继续写第一章」开始创作
- 输入「角色」设计角色细节
- 输入「修改大纲」调整框架
"""

    def _handle_continue(self, user_input: str, semantic: Any, emotion: Dict, soul: Dict) -> str:
        """② 继续创作"""
        if self._novel["status"] == "idle":
            return "请先输入「写小说」开始创作。"

        chapter_num = self._novel["current_chapter"] + 1
        current_text = self._get_current_text()

        direction = ""
        if "写" in user_input and len(user_input) > 5:
            direction = f"用户希望：{user_input}"

        prompt = f"""
继续写第{chapter_num}章：

小说：{self._novel['title']}
体裁：{self._novel['genre']}
前文：{current_text[:800] if current_text else '（这是第一章）'}

{direction}

要求：
1. 保持前文的风格和语气
2. 推进情节发展
3. 本章应有完整的起承转合
4. 字数：800-1500字
5. 以「## 第{chapter_num}章：」开头
"""
        chapter = self._call_llm(prompt)

        self._novel["chapters"].append(
            {
                "number": chapter_num,
                "title": self._extract_title(chapter),
                "content": chapter,
                "summary": self._extract_summary(chapter),
                "created_at": datetime.now().isoformat(),
            }
        )
        self._novel["current_chapter"] = chapter_num
        self._novel["status"] = "writing"
        self._update_stats()
        self._save_state()

        return f"""
{chapter}

---

📊 **进度更新**
- 当前章节：第{chapter_num}章
- 总字数：约 {self._count_words()} 字
- 输入「继续」写下一章
- 输入「修改」调整本章内容
"""

    def _handle_new_chapter(self, user_input: str, semantic: Any, emotion: Dict, soul: Dict) -> str:
        """③ 新建章节"""
        chapter_num = len(self._novel["chapters"]) + 1

        title = re.sub(r"^(新章节|下一章)", "", user_input).strip()
        if not title:
            title = f"第{chapter_num}章"

        prompt = f"""
为小说《{self._novel['title'] or '未命名'}》创作新章节：

章节标题：{title}
前文概要：{self._get_summary()}

要求：
1. 自然承接前文
2. 推动故事发展
3. 800-1500字
"""
        chapter = self._call_llm(prompt)

        self._novel["chapters"].append(
            {
                "number": chapter_num,
                "title": title,
                "content": chapter,
                "summary": self._extract_summary(chapter),
                "created_at": datetime.now().isoformat(),
            }
        )
        self._novel["current_chapter"] = chapter_num
        self._novel["status"] = "writing"
        self._save_state()

        return f"""
{chapter}

---

✅ 第{chapter_num}章「{title}」已生成
📊 总字数：约 {self._count_words()} 字
"""

    def _handle_character(self, user_input: str, semantic: Any, emotion: Dict, soul: Dict) -> str:
        """④ 角色工坊"""
        import re

        name_match = re.search(r"角色\s*([^\s，,。.]+)", user_input)
        character_name = name_match.group(1) if name_match else None

        existing_characters = self._novel.get("characters", [])
        existing_names = [c.get("name", "") for c in existing_characters if c.get("name")]
        existing_profiles = "\n".join(
            [f"- {c.get('name', '未命名')}: {c.get('profile', '')[:200]}..." for c in existing_characters]
        )

        is_organize = any(kw in user_input.lower() for kw in ["整理", "现有", "稳定"])
        is_record = any(kw in user_input.lower() for kw in ["录入", "正式录入", "添加", "加入"])

        if is_organize and existing_names:
            prompt = f"""
小说《{self._novel.get('title', '未命名')}》已有以下角色：

{existing_profiles}

用户需求：{user_input}

请基于以上已有角色，深化和完善他们的档案。
- 补充细节：性格深度、背景故事、弧光
- 保持角色名字不变
- 不要新增角色
- 输出格式：Markdown
"""
            result = self._call_llm(prompt)
            for i, c in enumerate(self._novel["characters"]):
                if c.get("name") in existing_names:
                    self._novel["characters"][i]["profile"] = result
                    self._novel["characters"][i]["updated_at"] = datetime.now().isoformat()

        elif is_record:
            prompt = f"""
小说《{self._novel.get('title', '未命名')}》已有角色：{', '.join(existing_names) if existing_names else '暂无'}

用户需求：{user_input}

请提取用户输入中的角色信息，为每个角色生成完整档案。
- 如果角色已存在，更新其档案
- 如果角色不存在，创建新角色
- 输出格式：Markdown，每个角色用 ## 分隔
"""
            result = self._call_llm(prompt)

            import re

            names_in_result = re.findall(r"##\s*([^\n]+)", result)
            for name in names_in_result:
                name = name.strip()
                if name:
                    found = False
                    for i, c in enumerate(self._novel["characters"]):
                        if c.get("name") == name:
                            self._novel["characters"][i]["profile"] = result
                            self._novel["characters"][i]["updated_at"] = datetime.now().isoformat()
                            found = True
                            break
                    if not found:
                        self._novel["characters"].append(
                            {"name": name, "profile": result, "created_at": datetime.now().isoformat()}
                        )

        else:
            prompt = f"""
小说《{self._novel.get('title', '未命名')}》已有角色：{', '.join(existing_names) if existing_names else '暂无'}
用户需求：{user_input if '角色' not in user_input else '主要角色'}

请设计一个新角色，不要与已有角色重复。
要求：
1. 姓名、年龄、外貌特征
2. 性格特点（优点、缺点、习惯、口头禅）
3. 核心动机
4. 背景故事
5. 角色弧光
6. 与其他角色的关系
7. 在故事中的作用

输出格式：Markdown
"""
            result = self._call_llm(prompt)

            if character_name:
                self._novel["characters"].append(
                    {"name": character_name, "profile": result, "created_at": datetime.now().isoformat()}
                )
            else:
                self._novel["characters"].append({"profile": result, "created_at": datetime.now().isoformat()})

        self._update_stats()
        self._save_state()

        return f"""
🎭 角色设定

{result}

---

💡 输入「继续深化」或告诉我想调整什么。
"""

    def _handle_scene(self, user_input: str, semantic: Any, emotion: Dict, soul: Dict) -> str:
        """⑤ 场景构建"""
        prompt = f"""
为小说《{self._novel['title'] or '未命名'}》构建场景：

用户要求：{user_input}

要求：
1. 地点和时间
2. 场景氛围（通过光线、声音、温度、气味营造）
3. 在场角色
4. 主要事件
5. 场景在故事中的作用

输出格式：Markdown
"""
        result = self._call_llm(prompt)
        self._novel["scenes"].append({"content": result, "created_at": datetime.now().isoformat()})
        self._update_stats()
        self._save_state()

        return f"""
🏗️ 场景构建

{result}

---

💡 输入「继续深化」丰富细节。
"""

    def _handle_plot(self, user_input: str, semantic: Any, emotion: Dict, soul: Dict) -> str:
        """⑥ 情节编织"""
        prompt = f"""
为小说《{self._novel['title'] or '未命名'}》设计情节节点：

用户要求：{user_input}

要求：
1. 主要冲突
2. 关键转折点
3. 情感高潮
4. 结局走向
5. 多线交织（如有）

输出格式：Markdown
"""
        result = self._call_llm(prompt)
        self._novel["plot_points"].append({"content": result, "created_at": datetime.now().isoformat()})
        self._update_stats()
        self._save_state()

        return f"""
🎯 情节设计

{result}

---

💡 输入「继续深化」增强张力。
"""

    def _handle_hook(self, user_input: str, semantic: Any, emotion: Dict, soul: Dict) -> str:
        """⑦ 钩子设计"""
        prompt = f"""
为小说《{self._novel['title'] or '未命名'}》设计钩子（悬念/伏笔）：

用户要求：{user_input}

要求：
1. 吸引力强
2. 与主线相关
3. 可回收
4. 类型：悬念/伏笔/转折/揭秘
5. 建议埋设章节

输出格式：Markdown
"""
        result = self._call_llm(prompt)
        self._novel["hooks"].append({"content": result, "created_at": datetime.now().isoformat()})
        self._update_stats()
        self._save_state()

        return f"""
🪝 钩子设计

{result}

---

💡 输入「继续深化」优化钩子。
"""

    def _handle_dialogue(self, user_input: str, semantic: Any, emotion: Dict, soul: Dict) -> str:
        """⑧ 对白打磨"""
        prompt = f"""
根据用户要求生成或优化对白：

用户要求：{user_input}
小说体裁：{self._novel['genre']}

要求：
1. 符合角色身份和性格
2. 推动情节发展
3. 自然、有节奏
4. 潜台词（话里有话）

输出格式：标准剧本对白格式
"""
        result = self._call_llm(prompt)
        return f"""
🎙️ 对白设计

{result}

---

💡 输入「继续深化」打磨节奏。
"""

    def _handle_polish(self, user_input: str, semantic: Any, emotion: Dict, soul: Dict) -> str:
        """⑨ 智能润色 - 支持单章、指定章、整部"""
        text = user_input.lower()

        if any(kw in text for kw in ["整部", "全书", "全部", "所有章节", "整本", "全本"]):
            return self._polish_full_novel(user_input)

        import re

        chapter_match = re.search(r"第(\d+)章", user_input)
        if chapter_match:
            chapter_num = int(chapter_match.group(1))
            return self._polish_chapter(user_input, chapter_num)

        return self._polish_current_chapter(user_input)

    def _polish_current_chapter(self, user_input: str) -> str:
        """润色当前章节"""
        chapters = self._novel.get("chapters", [])
        if not chapters:
            return "📝 还没有章节可以润色。先写一些内容吧。"

        current = chapters[-1]
        instruction = re.sub(r"^(润色|优化)", "", user_input).strip()
        if not instruction:
            instruction = "优化语言表达"

        prompt = f"""
润色以下章节，保持情节和角色完全不变：

【当前章节】
{current.get('content', '')}

【润色要求】
{instruction}

【要求】
- 保持原意和情节不变
- 优化语言表达
- 去除冗余
- 保持风格一致
- 只输出润色后的内容
"""
        result = self._call_llm(prompt, task_type="polish")
        if result:
            chapters[-1]["content"] = result
            chapters[-1]["summary"] = result[:100] + "..."
            self._save_state()
            return f"""
✨ 第{chapters[-1].get('number', '?')}章润色完成

{result}
"""
        return "❌ 润色失败，请重试。"

    def _polish_chapter(self, user_input: str, chapter_num: int) -> str:
        """润色指定章节"""
        chapters = self._novel.get("chapters", [])
        target = None
        for c in chapters:
            if c.get("number") == chapter_num:
                target = c
                break
        if not target:
            return f"❌ 未找到第{chapter_num}章。"

        instruction = re.sub(r"^(润色|优化)", "", user_input).strip()
        if not instruction:
            instruction = "优化语言表达"

        prompt = f"""
润色以下章节，保持情节和角色完全不变：

【第{chapter_num}章】
{target.get('content', '')}

【润色要求】
{instruction}

【要求】
- 保持原意和情节不变
- 优化语言表达
- 去除冗余
- 保持风格一致
- 只输出润色后的内容
"""
        result = self._call_llm(prompt, task_type="polish")
        if result:
            target["content"] = result
            target["summary"] = result[:100] + "..."
            self._save_state()
            return f"""
✨ 第{chapter_num}章润色完成

{result}
"""
        return "❌ 润色失败，请重试。"

    def _polish_full_novel(self, user_input: str) -> str:
        """整部小说润色"""
        chapters = self._novel.get("chapters", [])
        if not chapters:
            return "📝 还没有内容可以润色。先写一些章节吧。"

        full_text = self._get_current_text()
        instruction = re.sub(r"^(润色|优化|整部|全书|全部|所有章节|整本|全本)", "", user_input).strip()
        if not instruction:
            instruction = "统一格式、优化语言、去除重复"

        prompt = f"""
请润色整部小说，保持情节、角色、结构完全不变：

【原文】
{full_text}

【润色要求】
{instruction}

【严格要求】
- 保持所有角色名字不变
- 保持故事主线不变
- 保持章节结构不变
- 统一格式：每章标题为「第X章：标题」
- 优化语言表达
- 去除重复内容
- 输出完整润色后的小说
"""
        result = self._call_llm(prompt, task_type="polish", num_predict=8192)
        if result:
            new_chapters = self._parse_chapters_from_text(result)
            if new_chapters:
                self._novel["chapters"] = new_chapters
                self._save_state()
                return f"""
✨ 整部小说润色完成！

共 {len(new_chapters)} 章已更新。

{result[:500]}...
"""
            return f"""
✨ 润色完成，但未能解析章节结构。

{result}
"""
        return "❌ 润色失败，请重试。"

    def _parse_chapters_from_text(self, text: str) -> List[Dict]:
        """从润色后的文本中解析章节"""
        import re

        chapters = []
        pattern = r"##\s*第(\d+)章[：:]\s*([^\n]*)\n(.*?)(?=##\s*第\d+章|$)"
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            for num, title, content in matches:
                chapters.append(
                    {
                        "number": int(num),
                        "title": f"第{num}章：{title.strip()}" if title.strip() else f"第{num}章",
                        "content": content.strip(),
                        "summary": content.strip()[:100] + "...",
                        "created_at": datetime.now().isoformat(),
                    }
                )
        return chapters

    def _handle_style(self, user_input: str, semantic: Any, emotion: Dict, soul: Dict) -> str:
        """⑩ 风格迁移"""
        style_match = re.search(r"模仿\s*([^\s，,。.]+)\s*风格", user_input)
        if style_match:
            style = style_match.group(1)
            self._user_preferences["writing_style"] = style
            self._save_state()
            return f"✅ 已切换写作风格：{style}"

        return """
🎨 风格迁移

支持风格：
- 海明威（简洁、硬朗）
- 张爱玲（细腻、冷峻）
- 村上春树（孤独、轻盈）
- 鲁迅（深刻、犀利）
- 金庸（豪迈、古典）

示例：模仿 海明威 风格写一段
"""

    def _handle_modify(self, user_input: str, semantic: Any, emotion: Dict, soul: Dict) -> str:
        """⑪ 修改内容"""
        instruction = re.sub(r"^(修改|改成|调整)", "", user_input).strip()
        if not instruction:
            return "请说明要修改什么。"

        name_match = re.search(r"([^\s，,。.]+)\s*改成\s*([^\s，,。.]+)", instruction)
        if name_match:
            old_name, new_name = name_match.group(1), name_match.group(2)
            for char in self._novel["characters"]:
                if char.get("name") == old_name:
                    char["name"] = new_name
                    self._save_state()
                    return f"✅ 已将角色名从「{old_name}」改为「{new_name}」"
            return f"❌ 未找到角色「{old_name}」"

        current = self._get_current_text()[:1500]
        prompt = f"""
根据用户要求修改内容：

要求：{instruction}
当前内容：{current}

要求：
1. 精准修改
2. 保持整体结构不变
3. 只输出修改后的内容
"""
        modified = self._call_llm(prompt)
        return f"✏️ 修改完成\n\n{modified}"

    def _handle_outline(self, user_input: str, semantic: Any, emotion: Dict, soul: Dict) -> str:
        """⑫ 大纲优化"""
        prompt = f"""
优化小说大纲：

标题：{self._novel['title'] or '未命名'}
当前大纲：{self._novel['outline'][:500] if self._novel['outline'] else '无'}

用户要求：{user_input}

要求：
1. 三幕结构清晰
2. 主线明确
3. 关键节点突出
4. 节奏合理

输出格式：Markdown
"""
        outline = self._call_llm(prompt)
        self._novel["outline"] = outline
        self._save_state()

        return f"""
📋 大纲已更新

{outline}
"""

    def _handle_complete(self, user_input: str, semantic: Any, emotion: Dict, soul: Dict) -> str:
        """⑬ 完成定稿 - 只标记状态和统计，不导出"""
        total = len(self._novel["chapters"])
        words = self._count_words()

        if total < 3:
            return f"""
📝 目前只写了 {total} 章（约 {words} 字），还不够完整。

💡 建议：
- 继续写直到至少 3 章
- 或者告诉我「强制完成」
"""

        self._novel["status"] = "completed"
        self._save_state()
        # 发布事件
        self._publish_novel_completed()
        return f"""
🎉 小说完成！

标题：{self._novel['title']}
体裁：{self._novel['genre']}
章节：{total} 章
字数：约 {words} 字

📊 **统计**
- 角色：{len(self._novel['characters'])} 个
- 场景：{len(self._novel['scenes'])} 个
- 情节节点：{len(self._novel['plot_points'])} 个
- 钩子：{len(self._novel['hooks'])} 个

💡 **下一步：**
- 输入「修改」继续完善
- 系统会将完成状态通知 orchestrator
"""

    def _handle_write(self, user_input: str, semantic: Any, emotion: Dict, soul: Dict) -> str:
        """⑭ 通用写作"""
        prompt = f"""
根据用户要求写作：

要求：{user_input}
风格：{self._user_preferences.get('writing_style', '默认')}

要求：
1. 语言流畅、自然
2. 表达清晰
3. 只输出内容，不要解释
"""
        result = self._call_llm(prompt)
        return result

    # ================================================================
    #  学习层
    # ================================================================

    def _learn(self, user_input: str, result: str, intent: str):
        """从交互中学习"""
        if "风格" in user_input.lower() and "模仿" in user_input.lower():
            style_match = re.search(r"模仿\s*([^\s，,。.]+)", user_input)
            if style_match:
                self._user_preferences["writing_style"] = style_match.group(1)

        for g in ["科幻", "奇幻", "悬疑", "爱情", "动作", "喜剧"]:
            if g in user_input:
                self._user_preferences["preferred_genre"] = g

        if self.soul:
            try:
                self.soul.update_relationship(user_input, result)
            except Exception as e:
                print(f"[Writer] 学习失败: {e}")

    # ================================================================
    #  辅助方法
    # ================================================================

    def _get_current_text(self) -> str:
        chapters = self._novel.get("chapters", [])
        if not chapters:
            return self._novel.get("outline", "")
        return "\n\n".join([c.get("content", "") for c in chapters])

    def _get_summary(self) -> str:
        chapters = self._novel.get("chapters", [])
        if not chapters:
            return "（尚未开始写作）"
        return "\n".join([f"- 第{c['number']}章：{c.get('title', '')}" for c in chapters[-3:]])

    def _extract_title(self, text: str) -> str:
        match = re.search(r"##\s*(第\d+章[：:]\s*.+)", text)
        if match:
            return match.group(1).strip()
        match = re.search(r"第\d+章[：:]\s*(.+)", text)
        if match:
            return match.group(1).strip()
        return f"第{len(self._novel['chapters']) + 1}章"

    def _extract_summary(self, text: str) -> str:
        lines = text.split("\n")
        if len(lines) > 3:
            return " ".join(lines[:3])[:100] + "..."
        return text[:100]

    def _count_words(self) -> int:
        text = self._get_current_text()
        return len(text.replace("\n", "").replace(" ", ""))

    def _get_llm_config(self, task_type: str) -> Dict:
        configs = {
            "outline": {"num_predict": 4096},
            "chapter": {"num_predict": 2048},
            "character": {"num_predict": 2048},
            "polish": {"num_predict": 1024},
            "intent": {"num_predict": 50},
            "default": {"num_predict": 2048},
        }
        return configs.get(task_type, configs["default"])

    def _publish_novel_completed(self):
        """发布小说完成事件"""
        try:
            from core.lib.event_bus import event_bus

            event_data = {
                "session_id": self._session_id,
                "user_id": self.user_id,
                "title": self._novel.get("title", "未命名"),
                "chapters": len(self._novel.get("chapters", [])),
                "word_count": self._count_words(),
                "genre": self._novel.get("genre", "未指定"),
                "characters": len(self._novel.get("characters", [])),
                "timestamp": datetime.now().isoformat(),
            }
            event_bus.publish("novel_completed", event_data)
            print(f"[Writer] 📢 发布事件: novel_completed - {event_data['title']}")
        except Exception as e:
            print(f"[Writer] 发布事件失败: {e}")

    def _load_from_memory_files(self) -> bool:
        """从 memory/ 目录的 session JSON 文件恢复（最可靠的 fallback）"""
        from pathlib import Path

        memory_dir = Path("memory")
        if not memory_dir.exists():
            return False

        session_files = sorted(memory_dir.glob("session_novel_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)

        for sf in session_files:
            try:
                data = json.loads(sf.read_text(encoding="utf-8"))
                if not isinstance(data, list):
                    continue

                for item in reversed(data):
                    assistant = item.get("assistant", "")
                    state = None
                    need_clean = False

                    # 新格式：JSON 字符串（title 干净）
                    if isinstance(assistant, str) and "state" in assistant:
                        try:
                            payload = json.loads(assistant)
                            state = payload.get("state") or payload.get("novel_state")
                        except Exception:
                            pass

                    # 旧格式：字典（title 需要清理）
                    if isinstance(assistant, dict):
                        state = assistant.get("state") or assistant.get("novel_state")
                        need_clean = True

                    # 统一加载
                    if state and isinstance(state, dict) and state.get("chapters"):
                        self._novel = state
                        if need_clean:
                            self._clean_title()
                        self._session_id = sf.stem
                        print(
                            f"[Writer] ✅ 从文件恢复: {self._novel.get('title', '未命名')} ({len(self._novel.get('chapters', []))}章)"
                        )
                        return True
            except Exception:
                continue

        return False

    def _clean_title(self):
        """清理脏标题，从第一章提取真实标题"""
        title = self._novel.get("title", "")
        if "基于以下设定" in title or "【小说大纲" in title or "小说大纲" in title:
            chapters = self._novel.get("chapters", [])
            if chapters:
                text = chapters[0].get("content", "")
                m = re.search(r"第[一二三四五六七八九十\d]+章\s*(.+)", text)
                if m:
                    self._novel["title"] = m.group(1).strip()[:30]
                else:
                    clean = text.replace("#", "").replace("*", "").strip()[:30]
                    self._novel["title"] = clean if clean else "未命名"

    def _load_from_federated(self):
        """从联邦知识恢复创作状态"""
        try:
            from core.lib.federated_bus import federated_bus

            novels = federated_bus.query_knowledge("novel:", limit=5)
            if novels:
                latest = novels[0]
                val = latest.get("value", {})
                if isinstance(val, dict) and val.get("title"):
                    self._novel["title"] = val.get("title", "")
                    self._novel["status"] = val.get("status", "idle")
                    self._novel["genre"] = val.get("genre", "")
                    self._novel["word_count"] = val.get("word_count", 0)
                    self._novel["updated_at"] = val.get("updated_at", "")
                    print(f"[Writer] 📚 从联邦知识恢复: {self._novel['title']} ({val.get('chapters',0)}章)")
        except Exception:
            pass

    def _resp(self, content: str, **kwargs) -> Dict:
        return {"success": True, "response": content, "output_content": content, **kwargs}

    def _update_stats(self):
        """更新统计信息"""
        self._novel["word_count"] = self._count_words()
        self._novel["updated_at"] = datetime.now().isoformat()
        self._novel["character_count"] = len(self._novel.get("characters", []))
        self._novel["scene_count"] = len(self._novel.get("scenes", []))
        self._novel["hook_count"] = len(self._novel.get("hooks", []))
        self._novel["plot_count"] = len(self._novel.get("plot_points", []))
        self._save_state()


if __name__ == "__main__":
    agent = WriterAgentV4("test")
    print("=" * 50)
    print("WriterAgent 核心写作能力测试")
    print("=" * 50)

    result = agent.process("写小说 关于AI觉醒", {"session_id": "test_session"})
    print(result.get("response"))
