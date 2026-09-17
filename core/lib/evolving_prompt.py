#!/usr/bin/env python3
"""自进化Prompt系统 - 随用户交互自动增长"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class EvolvingPrompt:
    """自索引自增长的prompt引擎"""
    
    def __init__(self, storage_dir: str = "data/evolving"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # 系统能力（从LLM建议中增长）
        self.capabilities: Dict[str, Dict] = {}
        
        # 翻译示例（从成功交互中学习）
        self.examples: List[Dict] = []
        
        # 用户专属词汇表
        self.user_terms: Dict[str, str] = {}
        
        self._load()
    
    def _load(self):
        for fname, attr in [
            ("capabilities.json", "capabilities"),
            ("examples.json", "examples"),
            ("user_terms.json", "user_terms"),
        ]:
            f = self.storage_dir / fname
            if f.exists():
                try:
                    setattr(self, attr, json.loads(f.read_text()))
                except Exception:
                    pass
    
    def _save(self):
        (self.storage_dir / "capabilities.json").write_text(
            json.dumps(self.capabilities, indent=2, ensure_ascii=False)
        )
        (self.storage_dir / "examples.json").write_text(
            json.dumps(self.examples[-100:], indent=2, ensure_ascii=False)
        )
        (self.storage_dir / "user_terms.json").write_text(
            json.dumps(self.user_terms, indent=2, ensure_ascii=False)
        )
    
    # ========== LLM建议新分类 → 系统采纳 ==========
    
    def learn_from_llm(self, suggestion: Dict, user_input: str, response: str):
        """LLM建议了新分类，系统学习并加入prompt"""
        
        # 1. 如果LLM建议了新分类
        new_cat = suggestion.get("suggest_new_category", "")
        if new_cat and new_cat not in self.capabilities:
            self.capabilities[new_cat] = {
                "name": new_cat,
                "created_from": user_input[:100],
                "created_at": datetime.now().isoformat(),
                "example_input": user_input[:200],
                "example_output": response[:200],
                "count": 1,
            }
            print(f"📝 [EvolvingPrompt] 学习新分类: {new_cat}")
        
        # 2. 更新已有分类的计数
        action = suggestion.get("action", "")
        if action in self.capabilities:
            self.capabilities[action]["count"] = self.capabilities[action].get("count", 0) + 1
            self.capabilities[action]["updated_at"] = datetime.now().isoformat()
        
        # 3. 保存成功交互为示例
        if response and len(response) > 10:
            self.examples.append({
                "input": user_input[:200],
                "output": response[:200],
                "action": action,
                "timestamp": datetime.now().isoformat(),
            })
        
        # 4. 提取用户专属词汇
        extracted = suggestion.get("extracted", {})
        for key, value in extracted.items():
            if isinstance(value, str) and len(value) >= 2:
                self.user_terms[key] = value
        
        self._save()
    
    # ========== 生成自进化的prompt片段 ==========
    
    def build_prompt_additions(self) -> str:
        """生成要注入LLM prompt的自进化内容"""
        parts = []
        
        # 1. 系统已有的分类（包含LLM建议新增的）
        if self.capabilities:
            lines = []
            for name, cap in sorted(self.capabilities.items(), 
                                     key=lambda x: x[1].get("count", 0), reverse=True):
                created = cap.get("created_from", "")[:60]
                count = cap.get("count", 0)
                lines.append(f"  {name}: {created} (使用{count}次)")
            parts.append("【系统能力分类 - 随使用自动增长】\n" + "\n".join(lines[:20]))
        
        # 2. 最近的翻译示例
        if self.examples:
            recent = self.examples[-5:]
            lines = []
            for e in recent:
                lines.append(f"  用户: {e['input'][:80]}")
                lines.append(f"  系统: {e['output'][:80]}")
                lines.append("")
            parts.append("【最近翻译示例】\n" + "\n".join(lines))
        
        # 3. 用户专属词汇
        if self.user_terms:
            terms = ", ".join(f"{k}={v}" for k, v in list(self.user_terms.items())[:10])
            parts.append(f"【用户词汇】{terms}")
        
        return "\n\n".join(parts) if parts else ""
    
    def get_stats(self) -> Dict:
        return {
            "capabilities_count": len(self.capabilities),
            "examples_count": len(self.examples),
            "user_terms_count": len(self.user_terms),
            "newest_capability": max(self.capabilities.items(), key=lambda x: x[1].get("created_at",""))[0] if self.capabilities else None,
        }


# 全局单例
evolving_prompt = EvolvingPrompt()
