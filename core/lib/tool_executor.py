#!/usr/bin/env python3
"""Tool 执行器 - 统一执行 Tool 能力"""

import subprocess
import json
from pathlib import Path
from typing import Dict, Any


class ToolExecutor:
    """Tool 执行器"""

    def __init__(self):
        self.tools = {
            "file_tools": self._file_tools,
            "network_tools": self._network_tools,
            "search_tools": self._search_tools,
        }

    def execute(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行 Tool"""
        if tool_name not in self.tools:
            return {"success": False, "error": f"Tool '{tool_name}' 不存在"}

        try:
            return self.tools[tool_name](params)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _file_tools(self, params: Dict) -> Dict:
        """文件操作工具"""
        action = params.get("action", "list")
        path = params.get("path", ".")

        if action == "list":
            try:
                p = Path(path)
                if not p.exists():
                    return {"success": False, "error": f"路径不存在: {path}"}
                files = [str(f) for f in p.iterdir()][:20]
                return {"success": True, "files": files, "count": len(files)}
            except Exception as e:
                return {"success": False, "error": str(e)}

        if action == "read":
            try:
                p = Path(path)
                if not p.exists():
                    return {"success": False, "error": f"文件不存在: {path}"}
                content = p.read_text(encoding='utf-8')
                return {"success": True, "content": content}
            except Exception as e:
                return {"success": False, "error": str(e)}

        return {"success": False, "error": f"未知操作: {action}"}

    def _network_tools(self, params: Dict) -> Dict:
        """网络请求工具"""
        action = params.get("action", "get")
        url = params.get("url", "")

        if not url:
            return {"success": False, "error": "请提供 URL"}

        try:
            import requests
            if action == "get":
                resp = requests.get(url, timeout=10)
                return {
                    "success": True,
                    "status": resp.status_code,
                    "content": resp.text[:500]
                }
            if action == "head":
                resp = requests.head(url, timeout=10)
                return {
                    "success": True,
                    "status": resp.status_code,
                    "headers": dict(resp.headers)
                }
            return {"success": False, "error": f"未知操作: {action}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _search_tools(self, params: Dict) -> Dict:
        """搜索工具"""
        query = params.get("query", "")
        path = params.get("path", ".")

        if not query:
            return {"success": False, "error": "请提供搜索关键词"}

        try:
            p = Path(path)
            if not p.exists():
                return {"success": False, "error": f"路径不存在: {path}"}

            results = []
            for f in p.rglob("*"):
                if query.lower() in f.name.lower():
                    results.append(str(f))
                    if len(results) >= 10:
                        break

            # 文件名搜索无结果时，回退到文件内容搜索
            content_results = []
            if not results:
                for f in p.rglob("*"):
                    if not f.is_file() or f.suffix not in ('.tsx', '.ts', '.js', '.jsx', '.go', '.py', '.md', '.sql', '.yaml', '.yml', '.json', '.html', '.css'):
                        continue
                    try:
                        content = f.read_text(encoding="utf-8")
                        if query in content:
                            content_results.append(str(f))
                            if len(content_results) >= 10:
                                break
                    except Exception:
                        pass

            return {
                "success": True,
                "results": results if results else content_results,
                "count": len(results) if results else len(content_results),
                "search_type": "filename" if results else "content" if content_results else "none",
                "hint": "搜索文件名使用 search_files。搜索文件内容请使用 read_file(path='...', search='关键词')。"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# 全局实例
tool_executor = ToolExecutor()

# P0: 收编注册到 V9Context 容器(零行为变化 — 容器持有同一实例, 业务代码仍直接 import tool_executor)
try:
    from core.os.context import get_v9_context as _get_v9_ctx_te
    _get_v9_ctx_te().provide("tool_executor", tool_executor)
except Exception as _te_ctx_err:
    print(f"[TOOL_EXECUTOR] P0 容器收编失败(不影响运行): {_te_ctx_err}")
