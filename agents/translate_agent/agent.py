from core.agents.business.business_agent_v2 import BusinessAgentV2
#!/usr/bin/env python3
"""翻译智能体 - 增强版（多语言互译）"""

import re
from typing import Dict, List, Optional

from core.agents.business.base_business_agent import BusinessAgent
from core.lib.smart_adapter import smart_adapter


class TranslateAgent(BusinessAgentV2):
    name = "translate_agent"
    description = "多语言智能翻译"
    version = "3.0.0"

    # 完整语言映射
    # 从配置文件加载语言映射
    LANG_MAP = {
        "中文": "zh",
        "英文": "en",
        "日文": "ja",
        "韩文": "ko",
        "法文": "fr",
        "德文": "de",
    }

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        self.translation_history = []
        print(f"🌐 翻译智能体 v3.0 已上线")

    def _execute_business(self, user_input: str, context: dict = None) -> dict:
        """业务逻辑实现 - BusinessAgent 要求"""
        return self.process(user_input, context)

    def _extract_text(self, text: str) -> Optional[str]:
        """提取待翻译文本"""
        patterns = [
            r"翻译(?:成\w+)?\s+(.+)$",
            r"译成\w+\s+(.+)$",
            r"translate\s+(.+)$",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _extract_batch_texts(self, text: str) -> List[str]:
        """提取批量文本"""
        lines = text.split("\n")
        texts = []
        for line in lines:
            if line.strip() and not line.startswith(("批量", "翻译")):
                texts.append(line.strip())
        return texts

    def _translate(self, text: str, target: str) -> str:
        """执行翻译"""
        try:
            prompt = f"""请将以下文本翻译成{target}，只输出翻译结果，不要任何解释：

原文：{text}

翻译结果："""
            result = smart_adapter.generate(prompt, auto_select=True).strip()
            # 记录历史
            self.translation_history.append(
                {
                    "original": text,
                    "translated": result,
                    "target": target,
                    "timestamp": __import__("time").time(),
                }
            )
            # 保留最近50条
            if len(self.translation_history) > 50:
                self.translation_history = self.translation_history[-50:]
            return result
        except Exception as e:
            return f"[翻译失败] {text}"

    def _batch_translate(self, texts: List[str]) -> List[Dict]:
        """批量翻译"""
        results = []
        for text in texts:
            translated = self._translate(text, "zh")
            results.append({"original": text, "translated": translated})
        return results

    def _detect_language(self, text: str) -> str:
        """检测语言"""
        for lang, code in self.LANG_MAP.items():
            if len(lang) <= 4:
                continue
        return "未知"

    def _build_response(self, result: str, original: str, target_lang: str) -> Dict:
        """构建响应"""
        return {
            "success": True,
            "response": f"🌐 {target_lang}：{result}",
            "original": original,
            "translated": result,
            "target_language": target_lang,
            "agent": self.name,
            "user_id": self.user_id,
        }

    def _batch_response(self, results: List[Dict]) -> Dict:
        """批量翻译响应"""
        summary = f"📚 批量翻译完成，共 {len(results)} 条：\n"
        for r in results:
            summary += f"• {r['original'][:30]} → {r['translated'][:30]}\n"
        return {
            "success": True,
            "response": summary,
            "results": results,
            "agent": self.name,
            "user_id": self.user_id,
        }

    def _help(self) -> Dict:
        """帮助信息"""
        return {
            "success": True,
            "response": f"🌐 翻译功能：\n• 说「翻译 Hello」\n• 说「把你好翻译成英文」\n• 说「批量翻译」\n支持 {len(self.LANG_MAP)} 种语言",
            "supported_languages": list(self.LANG_MAP.keys()),
            "agent": self.name,
            "user_id": self.user_id,
        }

