# -*- coding: utf-8 -*-
"""wps_office 工具: PA 生成 PPT/Word 的统一入口(2026-09-10, provider=wpsai 落地)。

Provider 策略(按优先级自动选择):
  1. WPS_AI_URL(env) -> wpsai: 真实桌面 WPS(Windows) + 灵犀AI(WPS-AI) MCP 桥,
                        预设模板排版(cover/content/closing), 实证 WPS build 28505 可用
  2. WPS_MCP_URL(env) -> mcp: 社区 wps-mcp-server(FastMCP, 文件级 python-pptx 路线) [待接入客户端]
  3. WPS_CLI(env)     -> cli: 本地 WPS 命令行 [待接入]
  4. python-pptx      -> 确定性降级生成(无 WPS 环境兜底)     [可用]

wpsai 前置(调用前必须满足, 否则明确报错不假成功):
  - 网关可达 WPS-AI proxy(同机 127.0.0.1:3890 或 ssh -L 转发), env WPS_AI_URL/WPS_AI_TOKEN
  - WPS 演示正打开且【已保存】的空白演示文稿(1 页)作为工作区(灵犀拒绝未保存临时文档)
  - 生成期间保持 WPS 前台/不切宿主; 每调用 25s 超时, 首败即停
md 约定与 python-pptx 兜底一致: 顶层 '#' 或 '## P?N' 一页一条; 每条 bullet 压至 <=120 字
"""
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from core.tools.base import ToolPlugin

WPS_OFFICE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "wps_office",
        "strict": True,
        "description": (
            "用 WPS/office 引擎生成或编辑文档(PPT/Word)。输入 markdown 大纲文件与目标格式, "
            "输出排版后的文件。优先真 WPS 排版(wpsai: 真实 WPS 预设模板 / mcp / cli); "
            "无 WPS 环境时确定性降级 python-pptx, 保证不溢出、结构完整。"
        ),
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "action": {"type": "string", "enum": ["pptx_from_md", "docx_from_md"], "description": "动作"},
                "md_path": {"type": "string", "description": "源 markdown 文件(沙箱相对路径)"},
                "out_path": {"type": "string", "description": "输出文件路径(默认 data/reports/同名 .pptx/.docx)"},
                "provider": {"type": "string", "description": "可选强制: auto/wpsai/mcp/cli/pptx"},
            },
            "required": ["action", "md_path"],
        },
    },
}

_MAX_BULLET = 120
_MAX_LINES = 8


def _detect_provider(forced="auto"):
    if forced and forced != "auto":
        return forced
    if os.getenv("WPS_AI_URL"):
        return "wpsai"
    if os.getenv("WPS_MCP_URL"):
        return "mcp"
    if os.getenv("WPS_CLI"):
        return "cli"
    return "pptx"


# ---------- md -> deck plan (纯函数, 双路线共用) ----------


def plan_from_md(text):
    """把 md 切成页: [{'title': str, 'lines': [str,...]}]; '#'/'## P?N' 起新页。"""
    pages = []
    cur = None
    for ln in text.splitlines():
        s = ln.strip()
        m2 = re.match(r"^##\s*P?(\d*)\s*(.*)$", s)
        m1 = re.match(r"^#\s*(.*)$", s)
        m = m2 or m1
        if m and (s.startswith("##") or s.startswith("# ")):
            if cur:
                pages.append(cur)
            t = m.group(2) if m2 else m.group(1)
            t = re.sub(r"^(P?\d+)\s*[｜|]?\s*", "", (t or "").strip())
            cur = {"title": (t or s.lstrip("# ").strip())[:80], "lines": []}
        elif cur is not None and s and not s.startswith("#"):
            cur["lines"].append(s)
    if cur:
        pages.append(cur)
    return pages


def _clean_lines(lines):
    out = []
    for b in lines:
        b2 = re.sub(r"^[-•*>\s]*", "", b).strip()
        if b2 and len(out) < _MAX_LINES:
            out.append(b2[:_MAX_BULLET])
    return out


def _template_kind(index, total, page):
    title = page["title"]
    if index == 1:
        return "cover-split"
    if index == total and re.search(r"谢谢|结尾|Q\s*&\s*A|下一步|行动|收尾", title):
        return "closing-thanks"
    return "content-sidebar"


def _template_args(kind, page):
    lines = _clean_lines(page["lines"])
    body = "\n".join(lines)
    if kind == "cover-split":
        # 封面: 标题留大, 副题取第一条 bullet(有 '|' 则取其后半)
        subtitle = ""
        if lines:
            subtitle = lines[0]
            if "|" in subtitle:
                subtitle = subtitle.split("|", 1)[1].strip()
        return {"title": page["title"], "subtitle": subtitle[:_MAX_BULLET]}
    if kind == "closing-thanks":
        return {"title": page["title"], "subtitle": lines[0] if lines else ""}
    return {"title": page["title"], "body": body}


# ---------- wpsai 驱动(HTTP 桥, 协议实证自 proxy-server.js) ----------


def _wpsai_base():
    return os.getenv("WPS_AI_URL", "http://127.0.0.1:3890").rstrip("/")


def _wpsai_token():
    return os.getenv("WPS_AI_TOKEN", "")


def _wpsai_http(method, path, body=None, timeout=25):
    url = _wpsai_base() + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    tok = _wpsai_token()
    if tok:
        headers["Authorization"] = "Bearer " + tok
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"ok": False, "error": raw[:300]}
    except Exception as e:
        return -1, {"ok": False, "error": "WPS-AI 连接失败: %s" % str(e)[:150]}


def _wpsai_call(name, args, timeout=25):
    st, body = _wpsai_http("POST", "/mcp/call", {"name": name, "args": args}, timeout=timeout)
    return st, body


def _win_path(linux_path):
    """把 /mnt/c /mnt/d 相对输出路径翻译成 Windows 路径(供 WPS 写盘)。"""
    p = str(linux_path).replace("/", "\\")
    if p.startswith("\\mnt\\c\\"):
        return "C:" + p[len("\\mnt\\c") :]
    if p.startswith("\\mnt\\d\\"):
        return "D:" + p[len("\\mnt\\d") :]
    return ""


def _require_alive():
    st, body = _wpsai_http("GET", "/mcp/status")
    if st != 200 or not body.get("ok") or not body.get("pluginAlive"):
        return False, "WPS-AI proxy/plugin 不在线(status=%s): 请确认 WPS 打开且 MCP 服务开启" % st
    return True, ""


def _require_clean_workspace():
    """要求 WPS 演示打开且已保存的空白工作区(<=2 页且正文为空), 避免误写真实文件。"""
    st, body = _wpsai_call("wpp_get_presentation_info", {})
    if st != 200 or not body.get("ok"):
        return False, body.get("error") or "未检测到打开的 WPS 演示(请先 Ctrl+S 保存空白演示文稿并保持前台)"
    info = body.get("value") or {}
    if info.get("saved") is False:
        return False, "当前演示未保存: 灵犀拒绝未落盘临时文档, 请先在 WPS 演示里 Ctrl+S 保存"
    total = int(info.get("slideCount") or 0)
    if total < 1 or total > 2:
        return False, "工作区应只有 1 张空白页(当前 %d 页): 请新建并保存空白演示文稿" % total
    for i in range(1, total + 1):
        st2, b2 = _wpsai_call("wpp_read_slide", {"index": i})
        shapes = ((b2.get("value") or {}).get("shapes") or []) if b2.get("ok") else []
        for s in shapes:
            if (s.get("text") or "").strip():
                return False, "工作区第 %d 页含已有内容, 请新建空白演示文稿避免误写" % i
    return True, {"initial": total}


def _pptx_from_md_wpsai(pages, out_path):
    """真 WPS 排版: 预检 -> 逐页 apply_template -> 删工作区空白页 -> save_as。"""
    ok, msg = _require_alive()
    if not ok:
        return {"success": False, "error": msg}
    ok, msg = _require_clean_workspace()
    if not ok:
        return {"success": False, "error": msg}
    initial = msg["initial"]

    win_out = _win_path(out_path)
    if not win_out:
        win_out = os.getenv("WPS_AI_OUT_DIR", "C:\\Users\\flybo\\Desktop") + "\\" + Path(out_path).name

    total = len(pages)
    try:
        for i, page in enumerate(pages, 1):
            kind = _template_kind(i, total, page)
            args = _template_args(kind, page)
            args["templateName"] = kind
            st, body = _wpsai_call("wpp_apply_template", args)
            if st != 200 or not body.get("ok"):
                return {"success": False, "error": "第 %d 页模板失败: %s" % (i, body.get("error") or ("HTTP %d" % st))}
        for _ in range(initial):
            _wpsai_call("wpp_delete_slide", {"index": 1})
        st, body = _wpsai_call("wpp_save_as", {"path": win_out, "format": "pptx"})
        if st != 200 or not body.get("ok"):
            return {"success": False, "error": "另存失败: %s" % (body.get("error") or ("HTTP %d" % st))}
    except Exception as e:
        return {"success": False, "error": "wpsai 排版中断: %s" % str(e)[:200]}

    mirrored = _win_path(out_path) != ""
    return {
        "success": True,
        "wps_path": win_out,
        "mirrored": mirrored,
        "out_path": str(out_path) if mirrored else "",
        "provider": "wpsai",
        "pages": total,
    }


def _pptx_from_md(md_path, out_path):
    """确定性降级: python-pptx(结构完整: bullet<=120 字, 每页<=8 条)。"""
    from pptx import Presentation

    text = Path(md_path).read_text(encoding="utf-8")
    pages = plan_from_md(text)
    prs = Presentation()
    for i, page in enumerate(pages or [], 1):
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        try:
            slide.shapes.title.text = page["title"][:80] or ("P%d" % i)
        except Exception:
            pass
        body = slide.placeholders[1].text_frame
        body.clear()
        first = True
        for b in _clean_lines(page["lines"]):
            para = body.paragraphs[0] if first else body.add_paragraph()
            first = False
            para.text = b
            para.level = 1
    prs.save(out_path)
    return out_path, len(pages)


def execute_wps_office(action, md_path, out_path="", provider="auto", base=""):
    """确定性入口(供插件与上层直接调用)。返回 {success, out_path, provider, pages|error}。"""
    md_path = str(md_path or "")
    if not md_path:
        return {"success": False, "error": "wps_office 需要 md_path"}
    if base:
        cand = Path(str(base)) / md_path
        if cand.exists():
            md_path = str(cand)
    if not Path(md_path).exists():
        return {"success": False, "error": "源文件不存在: %s" % md_path}
    prov = _detect_provider(provider)
    if not out_path:
        stem = Path(md_path).stem
        out_path = "data/reports/%s.%s" % (stem, "pptx" if action == "pptx_from_md" else "docx")
    if action != "pptx_from_md":
        return {"success": False, "error": "docx_from_md 待接入; 当前仅 pptx_from_md"}
    try:
        if prov == "pptx":
            out, n = _pptx_from_md(md_path, out_path)
            return {"success": True, "out_path": str(out), "provider": "python-pptx", "pages": n}
        if prov == "wpsai":
            text = Path(md_path).read_text(encoding="utf-8")
            pages = plan_from_md(text)
            if not pages:
                return {"success": False, "error": "md 无页面结构(需要 '#' 或 '## P?N' 标题)"}
            return _pptx_from_md_wpsai(pages, out_path)
        return {
            "success": False,
            "error": "provider=%s 需要真实 WPS 环境(WPS-AI MCP 桥或 wps-mcp-server/WPS_CLI); "
            "headless Linux 无 WPS, 请设 WPS_AI_URL/WPS_AI_TOKEN 或改用 provider=pptx 兜底" % prov,
        }
    except Exception as e:
        return {"success": False, "error": "wps_office 失败: %s" % str(e)[:200]}


class WpsOfficePlugin(ToolPlugin):
    name = "wps_office"
    quota = 5
    schema = WPS_OFFICE_SCHEMA

    def execute(self, args: dict, ctx) -> dict:
        action = str((args or {}).get("action") or "")
        md_path = str((args or {}).get("md_path") or "")
        out_path = str((args or {}).get("out_path") or "")
        provider = str((args or {}).get("provider") or "auto")
        base = getattr(ctx, "base", None)
        return execute_wps_office(action, md_path, out_path=out_path, provider=provider, base=str(base) if base else "")
