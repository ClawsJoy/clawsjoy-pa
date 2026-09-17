#!/usr/bin/env python3
"""FileAgent v5.0 - 文件管理"""

import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple

from core.agents.business.business_agent import BusinessAgent


class FileAgentV4(BusinessAgent):
    name = "file_agent_v4"
    description = "文件管理专家"
    version = "5.0.0"

    def __init__(self, user_id: str = "default"):
        super().__init__(user_id=user_id)
        print(f"📁 FileAgent v{self.version}")

    def can_handle_json(self, action: str, target: str) -> Tuple[bool, float]:
        return (True, 0.9)

    def _execute_business(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        t = user_input.lower()

        if any(kw in t for kw in ["读取", "读", "查看", "打开"]):
            return self._read(user_input)
        elif any(kw in t for kw in ["写入", "写", "创建", "保存"]):
            return self._write(user_input)
        elif any(kw in t for kw in ["列出", "列表", "目录", "ls"]):
            return self._list(user_input)
        elif any(kw in t for kw in ["删除", "移除", "rm"]):
            return self._delete(user_input)
        elif any(kw in t for kw in ["搜索", "查找"]):
            return self._search(user_input)
        return self._resp("📁 文件助手\n\n• 读取 /path/to/file\n• 写入 /path 内容\n• 列出 /path\n• 删除 /path\n• 搜索 关键词")

    def _read(self, user_input: str) -> Dict:
        path = self._extract_path(user_input)
        if not path:
            return self._resp("请指定文件路径")
        p = Path(path)
        if not p.exists():
            return self._resp(f"文件不存在: {path}")
        try:
            content = p.read_text(encoding='utf-8')
            return self._resp(f"📄 {path} ({len(content)}字符)\n\n{content[:2000]}")
        except Exception as e:
            return self._resp(f"读取失败: {e}")

    def _write(self, user_input: str) -> Dict:
        path = self._extract_path(user_input)
        content = user_input.split("，", 1)[-1].split(",", 1)[-1].strip()
        if not path:
            return self._resp("请指定文件路径和内容")
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding='utf-8')
            return self._resp(f"✅ 已写入 {path} ({len(content)}字符)")
        except Exception as e:
            return self._resp(f"写入失败: {e}")

    def _list(self, user_input: str) -> Dict:
        cleaned = re.sub(r'(列出|列表|目录|ls|文件)', '', user_input).strip()
        path = cleaned if cleaned and len(cleaned) > 1 else "."
        p = Path(path)
        if not p.exists():
            return self._resp(f"目录不存在: {path}")
        items = list(p.iterdir())[:50]
        lines = [f"📁 {path} ({len(items)}项)"] + [
            f"  {'📁' if i.is_dir() else '📄'} {i.name} ({i.stat().st_size}B)"
            for i in sorted(items, key=lambda x: (not x.is_dir(), x.name))
        ]
        return self._resp("\n".join(lines))

    def _delete(self, user_input: str) -> Dict:
        path = self._extract_path(user_input)
        if not path:
            return self._resp("请指定文件路径")
        p = Path(path)
        if not p.exists():
            return self._resp(f"文件不存在: {path}")
        try:
            p.unlink()
            return self._resp(f"🗑 已删除: {path}")
        except Exception as e:
            return self._resp(f"删除失败: {e}")

    def _search(self, user_input: str) -> Dict:
        query = re.sub(r'(搜索|查找|查询|找)', '', user_input).strip()
        if not query:
            return self._resp("请指定搜索关键词")
        results = [str(f) for f in Path(".").rglob(f"*{query}*") if f.is_file()][:20]
        if results:
            return self._resp(f"🔍 搜索「{query}」:\n" + "\n".join(f"  📄 {r}" for r in results))
        return self._resp(f"未找到包含「{query}」的文件")

    def _extract_path(self, text: str) -> str:
        m = re.search(r'["\']([^"\']+)["\']', text)
        if m:
            return m.group(1)
        m = re.search(r'[/\\]?[\w\-\._/\\]+', text)
        return m.group(0).strip() if m else ""

    def _resp(self, content: str, **kwargs) -> Dict:
        return {"success": True, "response": content, "output_content": content, **kwargs}


if __name__ == "__main__":
    agent = FileAgentV4("test")
    print(agent.process("列出 .")["response"][:300])
