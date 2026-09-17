"""
方言学习引擎 v2.0
任何方言 → 主动学习 → 越用越懂

回路：
1. 方言→普通话（词库查表）
2. 向量语义检索回复（零LLM）
3. 未命中→LLM兜底→自动学入向量库
4. 不懂就问→正则提取→学入词库
"""
import json, re, subprocess
from pathlib import Path
from typing import Tuple, Optional
from datetime import datetime


class DialectLearningEngine:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.db_path = Path(f"data/dialects/{user_id}.json")
        self.reply_path = Path(f"data/dialects/{user_id}_replies.json")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.vocabulary = self._load_vocabulary()
        self.reply_templates = self._load_replies()
        self.action_templates = self._load_actions()
        self.unknown_words = []

    def _load_vocabulary(self) -> dict:
        if self.db_path.exists():
            data = json.loads(self.db_path.read_text())
            return data.get("vocabulary", data)
        return {}

    def _save_vocabulary(self):
        data = {"vocabulary": self.vocabulary, "version": "2.0"}
        self.db_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def _load_actions(self) -> dict:
        path = Path(f"data/dialects/{self.user_id}_actions.json")
        if path.exists():
            return json.loads(path.read_text())
        return {}

    def _save_actions(self):
        path = Path(f"data/dialects/{self.user_id}_actions.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.action_templates, ensure_ascii=False, indent=2))

    def _load_replies(self) -> dict:
        if self.reply_path.exists():
            return json.loads(self.reply_path.read_text())
        return {}

    def _save_replies(self):
        self.reply_path.write_text(json.dumps(self.reply_templates, ensure_ascii=False, indent=2))

    def learn(self, dialect_text: str, mandarin_meaning: str, dialect_type: str = "未知"):
        now = datetime.now().isoformat()
        if dialect_text in self.vocabulary:
            info = self.vocabulary[dialect_text]
            if isinstance(info, dict):
                info["confidence"] = min(1.0, info.get("confidence", 0.5) + 0.1)
                info["use_count"] = info.get("use_count", 0) + 1
        else:
            self.vocabulary[dialect_text] = {
                "standard": mandarin_meaning, "dialect_type": dialect_type,
                "learned_at": now, "use_count": 1, "confidence": 0.7, "source": "user_taught"
            }
        self._save_vocabulary()
        if dialect_text in self.unknown_words:
            self.unknown_words.remove(dialect_text)

    def learn_reply(self, trigger: str, dialect_reply: str, previous: str = ""):
        # 去重：已存在则只更新
        if trigger in self.reply_templates:
            self.reply_templates[trigger]["use_count"] += 1
            self.reply_templates[trigger]["learned_at"] = datetime.now().isoformat()
            self._save_replies()
            return
        
        self.reply_templates[trigger] = {
            "reply": dialect_reply, "learned_at": datetime.now().isoformat(), "use_count": 0
        }
        self._save_replies()
        full_text = f"{previous} {trigger}".strip() if previous else trigger
        try:
            from core.lib.vector_bank import vector_bank
            vector_bank.add(
                collection=f"dialect_replies_{self.user_id}",
                text=full_text,
                metadata={"trigger": trigger, "reply": dialect_reply, "previous": previous}
            )
        except:
            pass

    def learn_action(self, trigger: str, action_type: str, target: str):
        """学习动作/联系人"""
        self.action_templates[trigger] = {
            "action": action_type,
            "target": target,
            "type": "contact" if action_type in ("电话", "手机", "号码", "联系方式") else "action",
            "learned_at": __import__('datetime').datetime.now().isoformat(),
            "use_count": 0
        }
        self._save_actions()

    def get_action(self, text: str) -> dict:
        """查找动作触发器"""
        if text in self.action_templates:
            return self.action_templates[text]
        for trigger, info in sorted(self.action_templates.items(), key=lambda x: -len(x[0])):
            if trigger in text or text.rstrip('了吗的啦呢吧') in trigger.rstrip('了吗的啦呢吧'):
                return info
        return {}

    def get_reply(self, text: str, previous: str = "") -> str:
        if text in self.reply_templates:
            self.reply_templates[text]["use_count"] += 1
            self._save_replies()
            return self.reply_templates[text]["reply"]
        full_text = f"{previous} {text}".strip() if previous else text
        try:
            from core.lib.vector_bank import vector_bank
            results = vector_bank.search(
                collection=f"dialect_replies_{self.user_id}", query=full_text, limit=3
            )
            if results and results[0].get("score", 0) > 0.5:
                reply = results[0].get("metadata", {}).get("reply", "")
                if reply:
                    return reply
        except:
            pass
        for trigger, info in sorted(self.reply_templates.items(), key=lambda x: -len(x[0])):
            if trigger in text or text.rstrip('了吗的啦呢吧') in trigger.rstrip('了吗的啦呢吧'):
                info["use_count"] += 1
                self._save_replies()
                return info["reply"]
        return ""

    def understand(self, text: str) -> Tuple[str, bool]:
        result = text
        if text in self.vocabulary:
            info = self.vocabulary[text]
            return (info["standard"] if isinstance(info, dict) else info), True
        for word, info in sorted(self.vocabulary.items(), key=lambda x: -len(x[0])):
            std = info["standard"] if isinstance(info, dict) else info
            if word in result:
                result = result.replace(word, std)
                if isinstance(info, dict):
                    info["use_count"] = info.get("use_count", 0) + 1
        has_unknown = False
        for frag in re.findall(r'[\u4e00-\u9fff]{2,4}', text):
            if frag not in self.vocabulary and frag not in {"你好","谢谢","再见","我","你","他","是","的","了","什么","怎么","为什么","哪里"}:
                has_unknown = True
                self.unknown_words.append(frag)
        self._save_vocabulary()
        return result, not has_unknown

    def express(self, mandarin_text: str) -> str:
        reply = self.get_reply(mandarin_text)
        if reply:
            return reply
        result = mandarin_text
        for word, info in sorted(self.vocabulary.items(), key=lambda x: -len(x[0])):
            std = info["standard"] if isinstance(info, dict) else info
            if std in result and std != word:
                result = result.replace(std, word)
                if isinstance(info, dict):
                    info["use_count"] = info.get("use_count", 0) + 1
        self._save_vocabulary()
        return result

    def has_pending_questions(self) -> bool:
        return len(self.unknown_words) > 0

    def ask_clarification(self) -> str:
        if self.unknown_words:
            return f"🤔 刚才你说的「{self.unknown_words[0]}」是什么意思？用普通话告诉我吧~"
        return ""

    def learn_from_conversation(self, user_reply: str, dialect_type: str = "未知"):
        for p in [r'(?:就是|意思是|指的是|叫)\s*(.+?)(?:的意思|的|了)?$', r'(.+?)的(?:意思|含义)']:
            m = re.search(p, user_reply)
            if m and self.unknown_words:
                meaning = m.group(1).strip()
                word = self.unknown_words.pop(0)
                self.learn(word, meaning, dialect_type)
                return word, meaning
        return None, None

    def stats(self) -> dict:
        return {
            "user_id": self.user_id,
            "vocabulary_size": len(self.vocabulary),
            "reply_templates": len(self.reply_templates),
        }
