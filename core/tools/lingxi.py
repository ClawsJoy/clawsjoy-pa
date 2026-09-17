# -*- coding: utf-8 -*-
"""lingxi 工具(2026-09-11): PA 驱动灵犀(WPS-AI)桥(3890)的唯一入口, 按动作分级治理。

分级(对照 endpoint_guard 语义):
  - read: 查信息/渲染/导出(放行 + 记账)
  - write: 保存(放行 + 记账)
  - destructive: 删页(需老板在场授权, 否则拒绝)
"""
import json
import os
import urllib.error
import urllib.request

from core.tools.base import ToolPlugin

LINGXI_BASE = os.getenv("LINGXI_PROXY_BASE", "http://127.0.0.1:3890")


def _recent_artifact(ctx, within_s=1800):
    """批183 · C3：桥未就绪时，若沙箱里**刚刚**产出过 pptx/pdf，把路径一并返回。

    **不编造**：找不到就是 None —— 前端据此区分「产物已生成 · 预览待就绪」与「尚未渲染」。
    口径：沙箱内 30 分钟内修改过的 .pptx/.ppt/.pdf/.docx，取最新的一个；扫描有上限（防大沙箱卡顿）。
    """
    try:
        import os as _os
        import time as _time
        from pathlib import Path as _P

        try:
            from core.lib.gateway_helpers import _get_sandbox_base as _gsb

            _base = _P(_gsb(getattr(ctx, "user_id", "") or "default", getattr(ctx, "session_id", "") or "default"))
        except Exception:
            return None
        if not _base.is_dir():
            return None
        _dirs = [
            _base,
            _base / "data",
            _base / "data" / "tmp",
            _base / "data" / "reports",
            _base / "output",
            _base / "out",
        ]
        _now = _time.time()
        _seen = 0
        _best = None
        _best_age = None
        for _d in _dirs:
            if not _d.is_dir():
                continue
            for _root, _dn, _fn in _os.walk(str(_d)):
                for _f in _fn:
                    _seen += 1
                    if _seen > 2000:
                        break
                    if _os.path.splitext(_f)[1].lower() not in (".pptx", ".ppt", ".pdf", ".docx"):
                        continue
                    _p = _P(_root) / _f
                    try:
                        _age = _now - _p.stat().st_mtime
                    except Exception:
                        continue
                    if _age <= within_s and (_best_age is None or _age < _best_age):
                        _best, _best_age = _p, _age
                if _seen > 2000:
                    break
            if _seen > 2000:
                break
        return str(_best) if _best is not None else None
    except Exception:
        return None


def _preview_pending_payload(ctx, error_text):
    """批183（修正版）· C3 **语义分层**：五层各说各的话，UI 不再把它们压成一个「失败」。

    契约（枚举固定，UI 按字段消费）：
      task_status  : PARTIAL（有产物）/ BLOCKED（无产物，被 WPS 硬边界挡住）
      artifact     : {exists: bool, path: str|None}   —— **不编**：找不到就是 exists=False
      preview      : {status: PENDING|READY|FAILED, reason: str|None}
      verification : {status: NOT_APPLICABLE|PENDING|PASS|FAIL}
      completion   : {status: NOT_COMPLETE|COMPLETE}
      （另保留 success=False / ready=False / reason="preview_pending" / hint / error —— 兼容首版前端与既有消费方）
    """
    _art = _recent_artifact(ctx)
    return {
        # —— 五层语义 ——
        "task_status": "PARTIAL" if _art else "BLOCKED",
        "artifact": {"exists": bool(_art), "path": _art},
        "preview": {"status": "PENDING", "reason": "wps_taskpane_not_ready"},
        "verification": {"status": "NOT_APPLICABLE"},
        "completion": {"status": "NOT_COMPLETE"},
        # —— 兼容层 ——
        "success": False,
        "ready": False,
        "reason": "preview_pending",
        "degraded": True,
        "hint": "WPS 灵犀面板（TaskPane）未开或未登录 —— PA 无法自动开启（WPS 插件硬边界）；按引导卡片操作后重试",
        "error": error_text,
    }


ACTION_MAP = {
    "get_presentation_info": "wpp_get_presentation_info",
    "render_html_template": "wpp_render_html_template",
    "export_slide_as_image": "wpp_export_slide_as_image",
    "export_pdf": "wpp_export_pdf",
    "save": "wpp_save",
    "save_as": "wpp_save_as",
    "delete_slide": "wpp_delete_slide",
}

READ_ACTIONS = {"get_presentation_info", "render_html_template", "export_slide_as_image", "export_pdf"}
WRITE_ACTIONS = {"save", "save_as"}
DESTRUCTIVE_ACTIONS = {"delete_slide"}

LINGXI_SCHEMA = {
    "type": "function",
    "function": {
        "name": "lingxi",
        "description": "调用灵犀(WPS-AI)桥生成/编辑 PPT：查文档信息、渲染 HTML 模板、导出图片/PDF、保存、删页。",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": sorted(ACTION_MAP.keys()) + ["wait_for_bridge", "verify_slidecount"],
                    "description": "动作; wait_for_bridge=轮询等桥就绪; verify_slidecount=磁盘页数复核(独立核验)",
                },
                "args": {"type": "object", "description": "传给灵犀工具的参数字典"},
                "timeout": {"type": "integer", "description": "wait_for_bridge 超时秒数(默认30)"},
                "expected": {"type": "integer", "description": "verify_slidecount 期望页数(可选, 给则返回 matches)"},
            },
            "required": ["action"],
        },
    },
}


class LingxiPlugin(ToolPlugin):
    name = "lingxi"
    schema = LINGXI_SCHEMA

    def _token(self):
        try:
            with urllib.request.urlopen(LINGXI_BASE + "/kv/all", timeout=5) as r:
                d = json.loads(r.read().decode("utf-8", "replace"))
            return (d or {}).get("items", {}).get("wpsAiMcpBridgeToken", "")
        except Exception:
            return ""

    def _call(self, tool_name, args, timeout=240):
        body = json.dumps({"name": tool_name, "args": args or {}}).encode("utf-8")
        req = urllib.request.Request(
            LINGXI_BASE + "/mcp/call",
            data=body,
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + self._token()},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))

    def execute(self, args, ctx):
        action = str(args.get("action") or "").strip()
        if action == "wait_for_bridge":
            import time as _time

            timeout = float(args.get("timeout") or 30)
            deadline = _time.time() + timeout
            waited = 0.0
            while _time.time() < deadline:
                try:
                    r = self._call("wpp_get_presentation_info", {})
                    if r.get("ok"):
                        return {
                            "success": True,
                            "data": r,
                            "level": "read",
                            "ready": True,
                            "waited_s": round(waited, 1),
                        }
                except Exception:
                    pass
                _time.sleep(2)
                waited += 2
            # 批183 · C3：桥未就绪是**可区分的降级状态**（reason=preview_pending），不是「失败」
            return _preview_pending_payload(
                ctx,
                "灵犀 MCP 未就绪（TaskPane 未开/未登录）。请在 WPS 打开灵犀面板 → 开启 MCP → 重试。PA 无法自动开启（WPS 插件硬边界）。",
            )
        if action == "verify_slidecount":
            r = self._call("wpp_get_presentation_info", {})
            if r.get("ok"):
                v = r.get("value") or {}
                actual = v.get("slideCount")
                expected = args.get("expected")
                return {
                    "success": True,
                    "data": r,
                    "level": "read",
                    "slideCount": actual,
                    "matches": (expected is None) or (actual == expected),
                    "expected": expected,
                }
            # 批183 · C3：同上 —— 复核失败也是「桥未就绪」这一类降级状态
            return _preview_pending_payload(ctx, "get_presentation_info 失败(桥未就绪), 无法复核页数")
        tool_name = ACTION_MAP.get(action)
        if not tool_name:
            return {"success": False, "error": "未知 lingxi 动作: %r, 可用: %s" % (action, sorted(ACTION_MAP))}
        if action in DESTRUCTIVE_ACTIONS:
            try:
                from core.pa import endpoint_guard as G

                st = G.gate_state(getattr(ctx, "user_id", "") or "")
                if not st.get("approved"):
                    return {"success": False, "error": "破坏性动作 %s 需老板在场授权(endpoint_guard.approve_destructive)" % action}
            except Exception as e:
                return {"success": False, "error": "治理检查失败: %s" % str(e)[:120]}
        try:
            _call_args = args.get("args") or {}
            if action == "render_html_template":
                _call_args = dict(_call_args)
                _call_args.setdefault("preview", False)  # 强制插入(非预览弹窗), 否则不落页
                _call_args.setdefault("templateName", "studio")  # 必填模板名, 兜底 studio
            r = self._call(tool_name, _call_args)
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")[:200]
            return {"success": False, "error": "灵犀桥 HTTP %s: %s" % (e.code, raw)}
        except Exception as e:
            return {"success": False, "error": str(e)[:200]}
        ok = bool(r.get("ok"))
        level = "destructive" if action in DESTRUCTIVE_ACTIONS else ("write" if action in WRITE_ACTIONS else "read")
        return {"success": ok, "data": r, "level": level}
