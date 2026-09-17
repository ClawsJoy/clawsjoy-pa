#!/usr/bin/env python3
"""文件处理智能体"""

import json
import os
from pathlib import Path
from typing import Dict, Optional

from api.skill_market import SecurityScanner
from core.agents.business.base_business_agent import BusinessAgent


class FileAgent(BusinessAgent):
    name = "file_agent"
    description = "文件操作助手"
    version = "1.0.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        self.work_dir = Path(f"data/users/{user_id}/files")
        self.work_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 FileAgent 已上线")

    def _execute_business(self, user_input: str, context: dict = None) -> dict:
        """业务逻辑实现 - BusinessAgent 要求"""
        return self.process(user_input, context)

    def process(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        print(f"[文件] 收到: {user_input}")

        if "列出" in user_input or "列表" in user_input:
            return self._list_files()
        elif "读取" in user_input or "查看" in user_input:
            return self._read_file(user_input)
        elif "保存" in user_input or "写入" in user_input:
            return self._save_file(user_input)
        elif "删除" in user_input:
            return self._delete_file(user_input)

        return {
            "success": False,
            "response": "文件操作：列出、读取、保存、删除",
            "agent": self.name,
            "user_id": self.user_id,
        }

    def _list_files(self) -> Dict:
        files = list(self.work_dir.glob("*"))
        file_list = [f.name for f in files if f.is_file()]
        return {
            "success": True,
            "response": f"📁 文件列表：{', '.join(file_list) if file_list else '空'}",
            "files": file_list,
            "agent": self.name,
            "user_id": self.user_id,
        }

    def _read_file(self, user_input: str) -> Dict:
        import re

        match = re.search(r"读取\s*(\S+)", user_input)
        if match:
            filename = match.group(1)
            file_path = self.work_dir / filename
            if file_path.exists():
                content = file_path.read_text()
                return {
                    "success": True,
                    "response": f"📄 {filename}:\n{content[:500]}",
                    "agent": self.name,
                    "user_id": self.user_id,
                }
            return {
                "success": False,
                "response": f"文件 {filename} 不存在",
                "agent": self.name,
                "user_id": self.user_id,
            }
        return {
            "success": False,
            "response": "请指定文件名，如「读取 test.txt」",
            "agent": self.name,
            "user_id": self.user_id,
        }

    def _save_file(self, user_input: str) -> Dict:
        import re

        # 匹配 "保存 文件名 内容" 或 "保存 文件名"
        match = re.search(r"保存\s+(\S+)(?:\s+(.+))?", user_input)
        if match:
            filename = match.group(1)
            content = match.group(2) if match.group(2) else ""

            # 如果没有提供内容，提示用户
            if not content:
                return {
                    "success": False,
                    "response": "请提供文件内容，如「保存 test.txt 内容」",
                    "agent": self.name,
                    "user_id": self.user_id,
                }

            # 1. 文件名安全检查
            if not self._safe_filename(filename):
                return {
                    "success": False,
                    "response": "❌ 文件名不安全",
                    "agent": self.name,
                    "user_id": self.user_id,
                }

            # 2. 内容安全扫描（如果是代码文件）
            if filename.endswith((".py", ".js", ".sh", ".php", ".rb", ".go")):
                scan_result = SecurityScanner.scan_skill(content)
                if not scan_result["safe"]:
                    return {
                        "success": False,
                        "response": f"❌ 文件内容不安全: {', '.join(scan_result['issues'])}",
                        "agent": self.name,
                        "user_id": self.user_id,
                    }

            # 3. 文件大小限制
            if len(content) > 10 * 1024 * 1024:  # 10MB
                return {
                    "success": False,
                    "response": "❌ 文件过大（超过10MB）",
                    "agent": self.name,
                    "user_id": self.user_id,
                }

            # 4. 保存文件
            file_path = self.work_dir / filename
            file_path.write_text(content)

            # 5. 审计日志
            self.audit("file_save", {"filename": filename, "size": len(content)})

            return {
                "success": True,
                "response": f"✅ 已保存 {filename}（已安全扫描）",
                "agent": self.name,
                "user_id": self.user_id,
            }
        return {
            "success": False,
            "response": "请指定文件名和内容，如「保存 test.txt 内容」",
            "agent": self.name,
            "user_id": self.user_id,
        }

    def _safe_filename(self, filename: str) -> bool:
        """检查文件名是否安全"""
        import re

        # 禁止路径遍历
        if ".." in filename or "/" in filename or "\\" in filename:
            return False
        # 只允许安全字符
        if not re.match(r"^[\w\-\.]+$", filename):
            return False
        # 禁止可执行文件扩展名
        dangerous_ext = [".exe", ".bat", ".cmd", ".sh", ".com"]
        if any(filename.lower().endswith(ext) for ext in dangerous_ext):
            return False
        return True

    def _delete_file(self, user_input: str) -> Dict:
        import re

        match = re.search(r"删除\s*(\S+)", user_input)
        if match:
            filename = match.group(1)
            file_path = self.work_dir / filename
            if file_path.exists():
                file_path.unlink()
                return {
                    "success": True,
                    "response": f"🗑️ 已删除 {filename}",
                    "agent": self.name,
                    "user_id": self.user_id,
                }
            return {
                "success": False,
                "response": f"文件 {filename} 不存在",
                "agent": self.name,
                "user_id": self.user_id,
            }
        return {
            "success": False,
            "response": "请指定文件名",
            "agent": self.name,
            "user_id": self.user_id,
        }
