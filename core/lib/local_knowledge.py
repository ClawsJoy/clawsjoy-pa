#!/usr/bin/env python3
"""本地知识索引 - 扫描用户文件，建立知识图谱"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict


class LocalKnowledge:
    """本地知识索引器"""
    
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.data_dir = Path(f"data/knowledge/{user_id}")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._index: Dict = {}
        self._topics: Dict[str, List] = defaultdict(list)
        self._people: Dict[str, Dict] = {}
        self._projects: Dict[str, Dict] = {}
        self._load()
    
    def _load(self):
        idx_file = self.data_dir / "index.json"
        if idx_file.exists():
            try:
                self._index = json.loads(idx_file.read_text())
                self._topics = defaultdict(list, self._index.get("topics", {}))
                self._people = self._index.get("people", {})
                self._projects = self._index.get("projects", {})
            except Exception:
                pass
    
    def _save(self):
        self._index = {
            "topics": dict(self._topics),
            "people": dict(self._people),
            "projects": dict(self._projects),
            "updated": datetime.now().isoformat(),
        }
        (self.data_dir / "index.json").write_text(
            json.dumps(self._index, indent=2, ensure_ascii=False)
        )
    
    def scan_directory(self, path: str, depth: int = 2):
        """扫描目录，建立索引"""
        p = Path(path).expanduser()
        if not p.exists():
            return {"scanned": 0, "error": f"路径不存在: {path}"}
        
        scanned = 0
        for f in p.rglob("*"):
            if f.is_file() and f.suffix in ['.txt','.md','.py','.json','.csv','.pdf','.docx','.xlsx']:
                if len(f.relative_to(p).parts) > depth:
                    continue
                try:
                    self._index_file(f)
                    scanned += 1
                except Exception:
                    pass
        
        self._save()
        return {"scanned": scanned, "path": str(p)}
    
    def _index_file(self, filepath: Path):
        """索引单个文件"""
        try:
            content = filepath.read_text(encoding='utf-8', errors='ignore')[:5000]
        except Exception:
            return
        
        stat = filepath.stat()
        info = {
            "path": str(filepath),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "hash": hashlib.md5(str(filepath).encode()).hexdigest()[:8],
        }
        
        # 提取话题（关键词）
        words = self._extract_keywords(content)
        for w in words:
            self._topics[w].append(info["path"])
        
        # 提取人名
        import re
        names = re.findall(r'(?:联系人|作者|发送给|收件人|@)\s*[：:]\s*(\S{2,4})', content)
        names += re.findall(r'([\u4e00-\u9fa5]{2,4})\s*(?:的|说|问|写)', content)
        for name in set(names):
            if name not in self._people:
                self._people[name] = {"mentions": [], "files": []}
            self._people[name]["files"].append(str(filepath))
        
        # 提取项目名（文件夹名）
        project = filepath.parent.name
        if project not in ['.', '..', ''] and len(project) > 2:
            if project not in self._projects:
                self._projects[project] = {"files": [], "topics": []}
            self._projects[project]["files"].append(str(filepath))
    
    def _extract_keywords(self, text: str, top_n: int = 20) -> List[str]:
        """提取关键词"""
        import re
        # 简单词频统计
        words = re.findall(r'[\u4e00-\u9fa5]{2,4}|[a-zA-Z]{3,}', text)
        freq = defaultdict(int)
        stopwords = {'可以','这个','那个','什么','怎么','为什么','一个','我们','他们','不是','因为','所以','但是','如果','已经','还是','或者','没有','不过','只是','应该'}
        for w in words:
            if w.lower() not in stopwords and len(w) >= 2:
                freq[w] += 1
        return [w for w, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:top_n]]
    
    def query(self, query_str: str, limit: int = 10) -> Dict:
        """查询本地知识"""
        results = {"files": [], "people": [], "projects": [], "topics": []}
        
        # 匹配话题
        for topic, files in self._topics.items():
            if query_str.lower() in topic.lower():
                results["topics"].append({"topic": topic, "files": files[:5]})
        
        # 匹配人名
        for name, info in self._people.items():
            if query_str in name:
                results["people"].append({"name": name, **info})
        
        # 匹配项目
        for proj, info in self._projects.items():
            if query_str.lower() in proj.lower():
                results["projects"].append({"project": proj, **info})
        
        return results
    
    def get_profile(self) -> Dict:
        """获取用户知识画像"""
        return {
            "topics_count": len(self._topics),
            "people_count": len(self._people),
            "projects_count": len(self._projects),
            "top_topics": sorted(self._topics.items(), key=lambda x: len(x[1]), reverse=True)[:10],
            "top_people": list(self._people.keys())[:10],
            "top_projects": list(self._projects.keys())[:10],
            "last_updated": self._index.get("updated", "never"),
        }
    
    def inject_context(self, query: str) -> str:
        """为LLM注入本地知识上下文"""
        relevant = self.query(query, limit=5)
        parts = []
        
        if relevant["people"]:
            parts.append("相关联系人: " + ", ".join(p["name"] for p in relevant["people"][:3]))
        if relevant["projects"]:
            parts.append("相关项目: " + ", ".join(p["project"] for p in relevant["projects"][:3]))
        if relevant["topics"]:
            parts.append("相关话题: " + ", ".join(t["topic"] for t in relevant["topics"][:3]))
        
        return "\n".join(parts) if parts else ""


# 全局实例（按用户）
_instances: Dict[str, LocalKnowledge] = {}

def get_local_knowledge(user_id: str = "default") -> LocalKnowledge:
    if user_id not in _instances:
        _instances[user_id] = LocalKnowledge(user_id)
    return _instances[user_id]
