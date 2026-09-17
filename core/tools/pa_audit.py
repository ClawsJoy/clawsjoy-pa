# -*- coding: utf-8 -*-
"""pa_audit 工具(2026-09-11): PA 验收(确定性审核)的唯一入口。

- preflight: 渲染前字段级审核(容量/字体/诚实标注/关键数字/字号阶梯)
- postcheck: 渲染后像素审核(留白/色数/字号/边缘)
"""
from core.tools.base import ToolPlugin

PA_AUDIT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "pa_audit",
        "description": "PPT 确定性验收: preflight(渲染前字段级审核, 返回 pass/fail/issue) / postcheck(渲染后 PNG 像素审核)。",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["preflight", "postcheck"], "description": "动作"},
                "pages": {"type": "array", "description": "preflight: 页 spec 数组(每项含 layout/data/palette 等)"},
                "png_dir": {
                    "type": "string",
                    "description": "postcheck: PNG 目录(如 /mnt/c/Users/flybo/Desktop/wpsai_v2_render)",
                },
                "prefix": {"type": "string", "description": "postcheck: PNG 文件名前缀(默认 ppc_P)"},
            },
            "required": ["action"],
        },
    },
}


class PaAuditPlugin(ToolPlugin):
    name = "pa_audit"
    schema = PA_AUDIT_SCHEMA

    def execute(self, args, ctx):
        from core.pa.audit import postcheck, preflight

        action = str(args.get("action") or "").strip()
        if action == "preflight":
            pages = args.get("pages") or []
            issues = preflight(pages)
            fails = [i for i in issues if i[1] == "fail"]
            warns = [i for i in issues if i[1] == "warn"]
            return {
                "success": True,
                "pass": not fails,
                "pages": len(pages),
                "fail_count": len(fails),
                "warn_count": len(warns),
                "issues": issues,
            }
        if action == "postcheck":
            png_dir = str(args.get("png_dir") or "").strip()
            prefix = str(args.get("prefix") or "ppc_P")
            if not png_dir:
                return {"success": False, "error": "postcheck 需要 png_dir"}
            rep = postcheck(png_dir, prefix, "")
            issues = rep.get("issues") or []
            return {"success": True, "pass": not issues, "pixels": len(rep.get("pixels") or []), "issues": issues}
        return {"success": False, "error": "未知 pa_audit 动作: %r" % action}
