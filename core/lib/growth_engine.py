#!/usr/bin/env python3
"""
增量增长引擎 - 示例/规则/schema三层自动增长
每次LLM成功后自动拆解注入三个桶
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List


class GrowthEngine:
    """三层增量：示例→规则→schema"""
    
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.root = Path(f"data/users/{user_id}/growth")
        self.root.mkdir(parents=True, exist_ok=True)
        
        # 三个桶
        self.examples_file = self.root / "examples.jsonl"   # 示例库
        self.rules_file = self.root / "rules.jsonl"         # 规则库
        self.schema_file = self.root / "schema.json"        # schema定义
    
    # ========== 增长：LLM成功后自动拆解 ==========
    
    def grow(self, user_input: str, llm_output: dict, result: str):
        """
        LLM成功处理后调用
        自动拆解为示例+规则+schema，三层同步增长
        """
        action = llm_output.get("action", "")
        extracted = llm_output.get("extracted", {})
        confidence = llm_output.get("confidence", 0.5)
        
        if confidence < 0.7:
            return  # 不够自信的，不纳入增长
        
        # 1. 增量示例：用户怎么说→LLM怎么理解
        self._add_example(user_input, action, extracted, result[:200])
        
        # 2. 增量规则：触发模式→处理动作→提取字段
        if extracted:
            self._add_rule(user_input, action, list(extracted.keys()))
        
        # 3. 增量schema：action需要哪些字段
        self._extend_schema(action, list(extracted.keys()))
    
    # ========== 示例层 ==========
    
    def _add_example(self, user_input: str, action: str, extracted: dict, result: str):
        """追加一条示例"""
        example = {
            "query_form": user_input[:200],      # 用户怎么说
            "action": action,                     # LLM判断的类型
            "extracted": extracted,               # LLM提取的字段
            "result_preview": result[:150],       # 处理结果预览
            "timestamp": datetime.now().isoformat(),
        }
        with open(self.examples_file, 'a') as f:
            f.write(json.dumps(example, ensure_ascii=False) + '\n')
    
    def get_examples(self, user_input: str, limit: int = 3) -> str:
        """检索相关示例，返回prompt片段"""
        examples = self._search_examples(user_input, limit)
        if not examples:
            return ""
        
        lines = ["【参考示例 - 类似情况之前这样处理】"]
        for i, ex in enumerate(examples, 1):
            lines.append(
                f"{i}. 用户说\"{ex['query_form'][:80]}\" "
                f"→ action={ex['action']}, "
                f"提取={json.dumps(ex['extracted'], ensure_ascii=False)[:100]}"
            )
        return "\n".join(lines)
    
    def _search_examples(self, query: str, limit: int) -> List[dict]:
        """检索示例 - 向量语义匹配"""
        if not self.examples_file.exists():
            return []
        
        # 用向量相似度
        try:
            import numpy as np
            from core.lib.vector_bank import get_vector_bank
            vbank = get_vector_bank(self.user_id)
            query_vec = vbank._embed(query)
            
            scored = []
            for line in self._read_tail(self.examples_file, 200):
                try:
                    ex = json.loads(line)
                    ex_vec = vbank._embed(ex.get("query_form", ""))
                    sim = float(np.dot(query_vec, ex_vec) / 
                               (np.linalg.norm(query_vec) * np.linalg.norm(ex_vec) + 1e-8))
                    scored.append((sim, ex))
                except Exception:
                    pass
            scored.sort(key=lambda x: x[0], reverse=True)
            return [e for _, e in scored[:limit]]
        except Exception:
            pass
        
        # 降级：关键词
        results = []
        query_lower = query.lower()
        for line in self._read_tail(self.examples_file, 200):
            try:
                ex = json.loads(line)
                if any(w in ex.get("query_form","").lower() for w in query_lower.split() if len(w)>=2):
                    results.append(ex)
            except Exception: pass
        return results[:limit]
    
    # ========== 规则层 ==========
    
    def _add_rule(self, user_input: str, action: str, fields: List[str]):
        """追加或更新规则"""
        rule = {
            "pattern": self._extract_pattern(user_input),  # 触发模式
            "action": action,
            "fields": fields,
            "confidence": 1,
            "timestamp": datetime.now().isoformat(),
        }
        
        # 检查是否已有相似规则，有则更新计数
        existing = self._find_similar_rule(rule["pattern"], action)
        if existing:
            existing["count"] = existing.get("count", 1) + 1
            existing["timestamp"] = rule["timestamp"]
            # 字段合并
            for f in fields:
                if f not in existing["fields"]:
                    existing["fields"].append(f)
            self._rewrite_rules()
        else:
            rule["count"] = 1
            with open(self.rules_file, 'a') as f:
                f.write(json.dumps(rule, ensure_ascii=False) + '\n')
    
    def get_rules(self, user_input: str, limit: int = 3) -> str:
        """检索相关规则"""
        rules = self._search_rules(user_input, limit)
        if not rules:
            return ""
        
        lines = ["【适用规则】"]
        for r in rules:
            lines.append(
                f"  {r['pattern']} → {r['action']} "
                f"(需提取: {', '.join(r['fields'][:5])}, 使用{r.get('count',1)}次)"
            )
        return "\n".join(lines)
    
    def _extract_pattern(self, text: str) -> str:
        """从用户输入中提取触发模式"""
        # 简化：用LLM做这件事
        # 当前版本：取前几个有意义的词
        words = text.replace("帮我", "").replace("请", "").strip()
        return words[:40] if words else text[:40]
    
    def _find_similar_rule(self, pattern: str, action: str) -> dict:
        if not self.rules_file.exists():
            return None
        for line in self._read_tail(self.rules_file, 100):
            try:
                r = json.loads(line)
                if r.get("action") == action and r.get("pattern")[:20] == pattern[:20]:
                    return r
            except Exception:
                pass
        return None
    
    def _search_rules(self, query: str, limit: int) -> List[dict]:
        if not self.rules_file.exists():
            return []
        try:
            import numpy as np
            from core.lib.vector_bank import get_vector_bank
            vbank = get_vector_bank(self.user_id)
            query_vec = vbank._embed(query)
            
            scored = []
            for line in self._read_tail(self.rules_file, 200):
                try:
                    r = json.loads(line)
                    r_vec = vbank._embed(r.get("pattern",""))
                    sim = float(np.dot(query_vec, r_vec) / 
                               (np.linalg.norm(query_vec) * np.linalg.norm(r_vec) + 1e-8))
                    scored.append((sim, r))
                except Exception: pass
            scored.sort(key=lambda x: x[0], reverse=True)
            return [e for _, e in scored[:limit]]
        except Exception: pass
        
        results = []
        query_lower = query.lower()
        for line in self._read_tail(self.rules_file, 200):
            try:
                r = json.loads(line)
                if any(w in r.get("pattern","").lower() for w in query_lower.split() if len(w)>=2):
                    results.append(r)
            except Exception: pass
        results.sort(key=lambda x: x.get("count",0), reverse=True)
        return results[:limit]
    
    def _rewrite_rules(self):
        """重写规则文件（合并更新后）"""
        if not self.rules_file.exists():
            return
        rules = []
        for line in self._read_tail(self.rules_file, 500):
            try:
                rules.append(json.loads(line))
            except Exception:
                pass
        # 去重保留最新
        seen = {}
        for r in rules:
            key = f"{r.get('action')}:{r.get('pattern')[:30]}"
            seen[key] = r
        self.rules_file.write_text(
            '\n'.join(json.dumps(v, ensure_ascii=False) for v in seen.values()) + '\n'
        )
    
    # ========== Schema层 ==========
    
    def _extend_schema(self, action: str, fields: List[str]):
        """扩展action的字段定义"""
        schema = {}
        if self.schema_file.exists():
            schema = json.loads(self.schema_file.read_text())
        
        if action not in schema:
            schema[action] = {"fields": [], "created": datetime.now().isoformat()}
        
        for f in fields:
            if f not in schema[action]["fields"]:
                schema[action]["fields"].append(f)
        
        schema[action]["updated"] = datetime.now().isoformat()
        self.schema_file.write_text(json.dumps(schema, indent=2, ensure_ascii=False))
    
    def get_schema(self, action: str = None) -> dict:
        if not self.schema_file.exists():
            return {}
        schema = json.loads(self.schema_file.read_text())
        if action:
            return schema.get(action, {})
        return schema
    
    # ========== 三层联合注入 ==========
    
    def inject_all(self, user_input: str) -> str:
        """三层联合注入prompt"""
        parts = []
        
        examples = self.get_examples(user_input)
        if examples:
            parts.append(examples)
        
        rules = self.get_rules(user_input)
        if rules:
            parts.append(rules)
        
        return "\n\n".join(parts) if parts else ""
    
    # ========== 辅助 ==========
    
    def _read_tail(self, filepath: Path, n: int) -> list:
        try:
            lines = filepath.read_text().strip().split('\n')
            return lines[-n:]
        except Exception:
            return []
    
    def stats(self) -> dict:
        examples = len(self._read_tail(self.examples_file, 9999)) if self.examples_file.exists() else 0
        rules = len(self._read_tail(self.rules_file, 9999)) if self.rules_file.exists() else 0
        schema = len(self.get_schema()) if self.schema_file.exists() else 0
        return {"examples": examples, "rules": rules, "schema_actions": schema}


_engines: Dict[str, GrowthEngine] = {}

def get_growth(user_id: str = "default") -> GrowthEngine:
    if user_id not in _engines:
        _engines[user_id] = GrowthEngine(user_id)
    return _engines[user_id]
