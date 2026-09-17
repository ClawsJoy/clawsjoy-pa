#!/usr/bin/env python3
"""TranslateAgent v5.0 - 多语言翻译助手

支持:
- 自动语言检测
- 20+语言互译
- 批量翻译
- 专业术语保持
"""

import re
from typing import Dict, Optional, Tuple

from core.agents.business.business_agent import BusinessAgent


class TranslateAgentV4(BusinessAgent):
    """翻译 Agent v5.0"""

    name = "translate_agent_v4"
    description = "多语言翻译助手"
    version = "5.0.0"

    LANGUAGES = {
        "zh": "中文", "zh-CN": "简体中文", "zh-TW": "繁体中文",
        "en": "英语", "ja": "日语", "ko": "韩语",
        "fr": "法语", "de": "德语", "es": "西班牙语",
        "ru": "俄语", "pt": "葡萄牙语", "it": "意大利语",
        "ar": "阿拉伯语", "hi": "印地语", "th": "泰语",
        "vi": "越南语", "nl": "荷兰语", "pl": "波兰语",
        "tr": "土耳其语", "sv": "瑞典语",
    }

    # 常见用语快速翻译（无需调LLM）
    QUICK_MAP = {
        ("hello", "中文"): "你好",
        ("hello", "日语"): "こんにちは",
        ("hello", "韩语"): "안녕하세요",
        ("hello", "法语"): "Bonjour",
        ("hello", "德语"): "Hallo",
        ("hello", "西班牙语"): "Hola",
        ("谢谢", "英语"): "Thank you",
        ("谢谢", "日语"): "ありがとう",
        ("谢谢", "韩语"): "감사합니다",
        ("谢谢", "法语"): "Merci",
        ("再见", "英语"): "Goodbye",
        ("再见", "日语"): "さようなら",
        ("再见", "韩语"): "안녕히 가세요",
        ("是", "英语"): "Yes",
        ("是", "日语"): "はい",
        ("不", "英语"): "No",
        ("不", "日语"): "いいえ",
        ("我爱你", "英语"): "I love you",
        ("我爱你", "日语"): "愛してる",
        ("我爱你", "法语"): "Je t'aime",
        ("早上好", "英语"): "Good morning",
        ("晚安", "英语"): "Good night",
    }

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        print(f"🌐 TranslateAgent v{self.version} | {len(self.LANGUAGES)}种语言")

    def can_handle_json(self, action: str, target: str) -> Tuple[bool, float]:
        return (True, 0.9)

    # ====================================================================
    #  核心
    # ====================================================================

    def _execute_business(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        text, target_lang, source_lang = self._parse_input(user_input)

        if not text:
            return self._resp(
                "请提供要翻译的内容。例如：\n"
                "• 翻译 hello 成中文\n"
                "• hello 用日语怎么说\n"
                "• 把 Good morning 翻译成法语"
            )

        # 快速翻译（无需LLM）
        quick = self.QUICK_MAP.get((text.strip().lower(), target_lang))
        if quick:
            return self._resp(f"🌐 {text} → {quick}（{target_lang}）")

        # LLM翻译
        return self._llm_translate(text, target_lang, source_lang)

    # ====================================================================
    #  解析
    # ====================================================================

    def _parse_input(self, user_input: str) -> Tuple[str, str, str]:
        """解析用户输入，提取文本、目标语言、源语言"""
        text = user_input.strip()
        target_lang = "中文"
        source_lang = "auto"

        # 模式1: 翻译 XXX 成/到 YYY
        m = re.search(r'翻译\s*(.+?)\s*[成到]\s*(.+)', text)
        if m:
            raw_text = m.group(1).strip()
            target_lang = self._match_lang(m.group(2).strip())
            return raw_text, target_lang, source_lang

        # 模式2: 把 XXX 翻译成 YYY
        m = re.search(r'把\s*(.+?)\s*翻译[成为]*\s*(.+)', text)
        if m:
            return m.group(1).strip(), self._match_lang(m.group(2).strip()), source_lang

        # 模式3: XXX 用/用 YYY 怎么说/怎么讲
        m = re.search(r'(.+?)\s*用\s*(.+?)\s*怎[么样]', text)
        if m:
            return m.group(1).strip(), self._match_lang(m.group(2).strip()), source_lang

        # 模式4: XXX 的 YYY 是什么
        m = re.search(r'(.+?)\s*的\s*(.+?)\s*是[什么啥]?', text)
        if m:
            candidate_lang = self._match_lang(m.group(2).strip())
            if candidate_lang != "中文" or m.group(2).strip() in self.LANGUAGES.values():
                return m.group(1).strip(), candidate_lang, source_lang

        # 模式5: translate XXX to YYY
        m = re.search(r'translate\s+(.+?)\s+to\s+(.+)', text, re.IGNORECASE)
        if m:
            return m.group(1).strip(), self._match_lang(m.group(2).strip()), source_lang

        # 模式6: 纯文本，检测源语言，目标默认中文
        # 去掉"翻译"等引导词
        cleaned = re.sub(
            r'^(翻译|翻译成|译成|转成|转换成|请|帮我|一下)\s*', '', text
        )
        if cleaned and len(cleaned) < 200:
            # 检测是否为非中文
            if self._detect_chinese(cleaned) < 0.3:
                return cleaned, "中文", "auto"
            else:
                return cleaned, "英语", "auto"

        return text, target_lang, source_lang

    def _match_lang(self, lang_str: str) -> str:
        """模糊匹配语言名称"""
        lang_str = lang_str.strip().lower()

        # 精确匹配
        for code, name in self.LANGUAGES.items():
            if lang_str == name or lang_str == code or lang_str == code.lower():
                return name

        # 模糊匹配
        for code, name in self.LANGUAGES.items():
            if name in lang_str or lang_str in name:
                return name

        # 常见别名
        aliases = {
            "英文": "英语", "日文": "日语", "韩文": "韩语", "法文": "法语",
            "德文": "德语", "俄文": "俄语", "西语": "西班牙语",
            "english": "英语", "japanese": "日语", "korean": "韩语",
            "french": "法语", "german": "德语", "spanish": "西班牙语",
            "russian": "俄语", "chinese": "中文",
        }
        if lang_str in aliases:
            return aliases[lang_str]

        return "中文"

    # ====================================================================
    #  LLM翻译
    # ====================================================================

    def _llm_translate(self, text: str, target_lang: str,
                       source_lang: str = "auto") -> Dict:
        """调用LLM翻译"""
        source_hint = ""
        if source_lang != "auto":
            source_hint = f"从{source_lang}"

        prompt = f"""请将以下内容{source_hint}翻译成{target_lang}。

要求：
- 保持原意，不添加不删除
- 专业术语保持准确
- 只输出翻译结果，不要解释

原文：{text}

翻译结果："""

        result = self._call_llm(prompt, task_type="translate")
        if result and len(result.strip()) > 0:
            return self._resp(f"🌐 翻译结果（{target_lang}）：\n\n{result.strip()}")

        return self._resp("翻译失败，请重试。")

    # ====================================================================
    #  批量翻译
    # ====================================================================

    def translate_batch(self, texts: list, target_lang: str = "中文") -> Dict:
        """批量翻译"""
        if not texts:
            return self._resp("请提供要翻译的内容列表")

        joined = "\n---\n".join([f"[{i+1}] {t}" for i, t in enumerate(texts)])
        prompt = f"将以下{len(texts)}段内容翻译成{target_lang}，保持编号和分隔符：\n\n{joined}"

        result = self._call_llm(prompt, task_type="translate", max_tokens=4096)
        if result:
            return self._resp(f"🌐 批量翻译（{target_lang}）：\n\n{result}")

        return self._resp("批量翻译失败")

    # ====================================================================
    #  辅助
    # ====================================================================

    def _detect_chinese(self, text: str) -> float:
        """检测中文字符比例"""
        if not text:
            return 0.0
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        return chinese_chars / len(text)

    def _resp(self, content: str, **kwargs) -> Dict:
        return {"success": True, "response": content, "output_content": content, **kwargs}

    def get_stats(self) -> Dict:
        return {
            "name": self.name,
            "version": self.version,
            "languages": len(self.LANGUAGES),
            "quick_translations": len(self.QUICK_MAP),
        }


if __name__ == "__main__":
    agent = TranslateAgentV4("test")
    tests = [
        "翻译 hello 成中文",
        "hello 用日语怎么说",
        "把 Good morning 翻译成法语",
        "我爱你 的 韩语 是什么",
        "translate world to spanish",
    ]
    for t in tests:
        print(f"\n📥 {t}")
        print(agent.process(t)["response"][:150])
