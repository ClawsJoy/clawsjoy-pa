"""本地代码库管理 - 让 Agent 理解用户的项目"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any


class CodeRepository:
    """本地代码库管理器"""
    
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.base_path = Path(f"data/code_repo/{user_id}")
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.index_file = self.base_path / "index.json"
        self._load_index()
    
    def _load_index(self):
        """加载代码索引"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    self.index = json.load(f)
            except:
                self.index = {"projects": {}, "files": {}, "last_scan": None}
        else:
            self.index = {"projects": {}, "files": {}, "last_scan": None}
    
    def _save_index(self):
        """保存代码索引"""
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2, ensure_ascii=False)
    
    def add_project(self, project_path: str, name: str = None) -> Dict:
        """添加项目到代码库"""
        path = Path(project_path).resolve()
        if not path.exists():
            return {"success": False, "error": f"路径不存在: {project_path}"}
        
        project_name = name or path.name
        project_id = hashlib.md5(str(path).encode()).hexdigest()[:8]
        
        # 扫描项目结构
        files = self._scan_project(path)
        
        self.index["projects"][project_id] = {
            "name": project_name,
            "path": str(path),
            "added_at": datetime.now().isoformat(),
            "file_count": len(files),
            "languages": self._detect_languages(files),
            "main_files": self._find_main_files(files)
        }
        
        # 索引文件
        for file_path, info in files.items():
            self.index["files"][file_path] = info
        
        self.index["last_scan"] = datetime.now().isoformat()
        print(f"[DEBUG] 保存索引到: {self.index_file}")
        self._save_index()
        print(f"[DEBUG] 索引已保存，文件数: {len(self.index['files'])}")
        return {
            "success": True,
            "project_id": project_id,
            "name": project_name,
            "file_count": len(files)
        }
    
    def _scan_project(self, path: Path) -> Dict:
        """扫描项目文件"""
        files = {}
        extensions = ['.py', '.js', '.java', '.go', '.rs', '.cpp', '.c', '.h', '.ts']
        
        for file_path in path.rglob("*"):
            if file_path.is_file() and file_path.suffix in extensions:
                # 跳过隐藏目录和常见忽略目录
                if any(part.startswith('.') for part in file_path.parts):
                    continue
                if any(part in ['node_modules', '__pycache__', 'target', 'dist'] for part in file_path.parts):
                    continue
                
                rel_path = str(file_path.relative_to(path))
                stat = file_path.stat()
                files[rel_path] = {
                    "path": rel_path,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "language": file_path.suffix[1:] if file_path.suffix else "txt"
                }
        
        return files
    
    def _detect_languages(self, files: Dict) -> List[str]:
        """检测项目使用的语言"""
        languages = set()
        for info in files.values():
            lang = info.get("language")
            if lang:
                languages.add(lang)
        return list(languages)
    
    def _find_main_files(self, files: Dict) -> List[str]:
        """查找主文件"""
        main_patterns = ['main.py', 'index.js', 'app.py', 'Main.java', 'main.go']
        main_files = []
        for pattern in main_patterns:
            if pattern in files:
                main_files.append(pattern)
        return main_files
    
    def get_project(self, project_id: str = None) -> Dict:
        """获取项目信息"""
        if project_id:
            return self.index["projects"].get(project_id, {})
        return self.index["projects"]
    
    def search_code(self, query: str, project_id: str = None) -> List[Dict]:
        """在代码库中搜索"""
        results = []
        query_lower = query.lower()

        # files 结构: {project_id: {file_path: info}}
        files_dict = self.index.get("files", {})
        
        # 如果指定了项目，只搜索该项目
        if project_id:
            files_dict = {project_id: files_dict.get(project_id, {})}
        
        for pid, project_files in files_dict.items():
            for file_path, info in project_files.items():
                if query_lower in file_path.lower():
                    results.append({
                        "file": file_path,
                        "type": "filename",
                        "language": info.get("language"),
                        "project_id": pid
                    })
                if len(results) >= 20:
                    break
            if len(results) >= 20:
                break

        return results[:20]   

    def get_file_content(self, project_id: str, file_path: str) -> Optional[str]:
        """获取文件内容"""
        project = self.index["projects"].get(project_id)
        if not project:
            return None
        
        full_path = Path(project["path"]) / file_path
        if full_path.exists() and full_path.is_file():
            try:
                return full_path.read_text(encoding='utf-8')
            except:
                return None
        return None
    
    def list_projects(self) -> List[Dict]:
        """列出所有项目"""
        return [
            {
                "id": pid,
                "name": p["name"],
                "path": p["path"],
                "file_count": p["file_count"]
            }
            for pid, p in self.index["projects"].items()
        ]
    
    def remove_project(self, project_id: str) -> bool:
        """移除项目"""
        if project_id in self.index["projects"]:
            del self.index["projects"][project_id]
            # 清理相关文件索引
            self.index["files"] = {
                k: v for k, v in self.index["files"].items()
                if not v.get("path", "").startswith(project_id)
            }
            self._save_index()
            return True
        return False

    def get_files(self, project_id: str) -> List[str]:
        """获取项目文件列表"""
        project = self.get_project(project_id)
        if not project:
            return []
        
        # 从索引中获取文件列表
        if project_id in self.index.get("files", {}):
            files_dict = self.index["files"][project_id]
            return list(files_dict.keys())
        return []

def get_code_repo(user_id: str = "default") -> CodeRepository:
    return CodeRepository(user_id)
