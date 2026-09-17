# -*- coding: utf-8 -*-
"""file_center 工具(2026-09-11): PA 独立核验交付物落盘(存在+大小), 不信桥自报 applied:true。"""
import os
import re

from core.tools.base import ToolPlugin

FILE_CENTER_SCHEMA = {
    "type": "function",
    "function": {
        "name": "file_center",
        "description": "独立核验文件是否真实落盘: 检查 Windows 路径(如 C:/Users/flybo/Desktop/xxx.pdf)是否存在及大小。用于导出后验收(不信桥自报 applied:true)。",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["stat", "list"], "description": "stat=单文件; list=目录列表"},
                "path": {"type": "string", "description": "文件或目录路径(Windows 或 /mnt/c 均可)"},
            },
            "required": ["action", "path"],
        },
    },
}


def _to_linux(path):
    p = str(path or "").strip().replace("\\", "/")
    m = re.match(r"^([A-Za-z]):/(.*)$", p)
    if m:
        return "/mnt/%s/%s" % (m.group(1).lower(), m.group(2))
    return p


class FileCenterPlugin(ToolPlugin):
    name = "file_center"
    schema = FILE_CENTER_SCHEMA

    def execute(self, args, ctx):
        action = str(args.get("action") or "").strip()
        path = _to_linux(args.get("path"))
        if action == "stat":
            try:
                st = os.stat(path)
                return {
                    "success": True,
                    "exists": True,
                    "size": st.st_size,
                    "mtime": int(st.st_mtime),
                    "is_file": os.path.isfile(path),
                    "path": path,
                }
            except FileNotFoundError:
                return {"success": True, "exists": False, "size": 0, "error": "文件不存在: " + path}
            except Exception as e:
                return {"success": False, "error": str(e)[:200]}
        if action == "list":
            try:
                names = sorted(os.listdir(path))[:60]
                return {"success": True, "count": len(names), "items": names, "path": path}
            except Exception as e:
                return {"success": False, "error": str(e)[:200]}
        return {"success": False, "error": "未知 file_center 动作: %r" % action}
