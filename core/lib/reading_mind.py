#!/usr/bin/env python3
"""阅读心智 - AgentCortex的知识摄入系统"""

import json, re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict, Counter


class ReadingMind:
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.data_dir = Path(f"data/mind/{user_id}")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._knowledge: List[Dict] = []
        self._concepts: Dict[str, List] = defaultdict(list)
        self._facts: Dict[str, str] = {}
        self._load()

    def _load(self):
        for fname, attr in [("knowledge.json", "_knowledge"), ("concepts.json", "_concepts"), ("facts.json", "_facts")]:
            f = self.data_dir / fname
            if f.exists():
                try:
                    data = json.loads(f.read_text())
                    setattr(self, attr, data if attr != "_concepts" else defaultdict(list, data))
                except Exception:
                    pass

    def _save(self):
        (self.data_dir / "knowledge.json").write_text(json.dumps(self._knowledge[-500:], indent=2, ensure_ascii=False))
        (self.data_dir / "concepts.json").write_text(json.dumps(dict(self._concepts), indent=2, ensure_ascii=False))
        (self.data_dir / "facts.json").write_text(json.dumps(self._facts, indent=2, ensure_ascii=False))

    def read(self, content: str, source: str = "用户输入") -> Dict:
        concepts = self._extract_concepts(content)
        facts = self._extract_facts(content)
        entry = {
            "content": content[:2000], "source": source,
            "concepts": concepts[:10], "facts": facts,
            "timestamp": datetime.now().isoformat(),
            "hash": str(hash(content))[:8],
        }
        self._knowledge.append(entry)
        for c in concepts:
            if entry["hash"] not in self._concepts[c]:
                self._concepts[c].append(entry["hash"])
        for f in facts:
            self._facts[f["key"]] = f["value"]
        self._save()
        return {"concepts_learned": len(concepts), "facts_learned": len(facts)}

    def recall(self, query: str, limit: int = 5) -> Dict:
        matched = []
        for concept, hashes in self._concepts.items():
            if concept.lower() in query.lower() or any(q.lower() in concept.lower() for q in query.split()):
                matched.append(concept)
        results = []
        seen = set()
        for c in matched[:10]:
            for h in self._concepts[c]:
                if h not in seen:
                    seen.add(h)
                    for e in self._knowledge:
                        if e.get("hash") == h:
                            results.append({"content": e["content"][:300], "source": e["source"], "concepts": e["concepts"][:5]})
                            break
        matched_facts = {k: v for k, v in self._facts.items() if k.lower() in query.lower() or any(q.lower() in k.lower() for q in query.split())}
        return {"relevant_concepts": matched[:10], "relevant_entries": results[:limit], "relevant_facts": matched_facts}

    def inject_context(self, query: str) -> str:
        r = self.recall(query, limit=3)
        parts = []
        if r["relevant_facts"]:
            parts.append("【已知】" + "; ".join(f"{k}={v}" for k, v in list(r["relevant_facts"].items())[:5]))
        if r["relevant_entries"]:
            parts.append("【相关】" + " | ".join(e["content"][:80] for e in r["relevant_entries"]))
        return "\n".join(parts) if parts else ""

    def _extract_concepts(self, text: str) -> List[str]:
        words = re.findall(r'[\u4e00-\u9fa5]{2,4}|[a-zA-Z]{3,}', text)
        stop = {'这个','那个','什么','怎么','一个','可以','我们','他们','不是','因为','所以','但是','如果','已经','还是','或者','没有'}
        freq = Counter(w for w in words if w not in stop and len(w) >= 2)
        return [w for w, _ in freq.most_common(20)]

    def _extract_facts(self, text: str) -> List[Dict]:
        facts = []
        # 邮箱
        for m in re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text):
            facts.append({"key": "邮箱", "value": m})
        # 日期
        for m in re.findall(r'(\d{1,2}月\d{1,2}日|\d{4}-\d{2}-\d{2})', text):
            facts.append({"key": "日期", "value": m})
        # 电话
        for m in re.findall(r'1[3-9]\d{9}', text):
            facts.append({"key": "电话", "value": m})
        # 人名职责
        for m in re.findall(r'([\u4e00-\u9fa5]{2,4})(?:负责|担任|做)([\u4e00-\u9fa5]{2,10})', text):
            facts.append({"key": f"{m[0]}的职责", "value": m[1]})
        # 产品/公司
        for prefix in ['公司', '产品', '团队', '项目']:
            for m in re.findall(rf'{prefix}[在是叫为名称]*\s*([\u4e00-\u9fa5\w]{{2,30}})', text):
                facts.append({"key": prefix, "value": m})
        # XX的YY是ZZ
        for m in re.findall(r'([\u4e00-\u9fa5]{2,4})的([\u4e00-\u9fa5]{2,6})[：:是为]+\s*([^。，\n]{2,30})', text):
            facts.append({"key": f"{m[0]}的{m[1]}", "value": m[2]})
        # 邮箱归属推断：如果同一段文字里有XX的职责，同时有邮箱，将邮箱关联到XX
        person_keys = [f for f in facts if '的职责' in f.get('key','')]
        email_facts = [f for f in facts if f.get('key') == '邮箱']
        if person_keys and email_facts:
            for pk in person_keys:
                person_name = pk['key'].replace('的职责','')
                for ef in email_facts:
                    facts.append({"key": f"{person_name}的邮箱", "value": ef["value"]})
        
        return facts[:20]

    def get_profile(self) -> Dict:
        return {
            "knowledge_size": len(self._knowledge),
            "concepts_count": len(self._concepts),
            "facts_count": len(self._facts),
            "top_concepts": sorted(self._concepts.items(), key=lambda x: len(x[1]), reverse=True)[:10],
        }


_instances: Dict[str, 'ReadingMind'] = {}

def get_mind(user_id: str = "default") -> ReadingMind:
    if user_id not in _instances:
        _instances[user_id] = ReadingMind(user_id)
    return _instances[user_id]
