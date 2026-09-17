"""方言助手 - 为 Agent 提供方言理解能力"""

import json
from pathlib import Path
from typing import Dict, Tuple


class DialectHelper:
    """方言处理助手"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self._words = self._load_words()

    def _get_path(self) -> Path:
        return Path(f"data/profile/{self.user_id}.json")

    def _load_words(self) -> Dict:
        """加载用户方言词库"""
        path = self._get_path()
        if path.exists():
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save(self):
        """保存方言词库"""
        path = self._get_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self._words, f, indent=2, ensure_ascii=False)

    def learn_direct(self, dialect_word: str, meaning: str):
        """直接学习方言词"""
        self._words[dialect_word] = meaning
        self._save()
        print(f"[方言] 学习: {dialect_word} = {meaning}")

    def to_standard(self, text: str) -> Tuple[str, bool]:
        """方言 → 普通话"""
        result = text
        converted = False
        for dialect, standard in self._words.items():
            if dialect in result:
                result = result.replace(dialect, standard)
                converted = True
        return result, converted

    def to_dialect(self, text: str) -> Tuple[str, bool]:
        """普通话 → 方言"""
        result = text
        converted = False
        for dialect, standard in self._words.items():
            if standard in result:
                result = result.replace(standard, dialect)
                converted = True
        return result, converted

    def has_dialect(self, text: str) -> bool:
        """检测是否包含方言词"""
        for dialect in self._words.keys():
            if dialect in text:
                return True
        return False


def get_dialect_helper(user_id: str) -> DialectHelper:
    """获取方言助手实例"""
    return DialectHelper(user_id)
