# -*- coding: utf-8 -*-
"""table_extract 确定性工具(2026-09-07) — 读网页表格 → Markdown 表格, 1 次调用完成。

设计原则: 表格提取是固定流程, 不应该是 LLM loop(红果漫剧阶梯表 32 步烧 50 万 token 实证)。
通道:
  1) browser_local(用户真实浏览器, 复用登录态 — 飞书等登录墙内表格首选);
  2) playwright headless 兜底(无登录态, 适合公开 HTML table)。
提取策略:
  - 页面 HTML <table> → pandas.read_html → to_markdown(降级手写 MD);
  - 飞书/内嵌 sheet: JS 找资源请求里的 sheet 数据 API(performance entries), playwright
    同源 fetch(带 cookie)拿真实单元格 JSON → 防御性解析成行列 → MD; 无 API 退 DOM 网格文本。
返回 markdown; output_path 可选把 MD 落沙箱(供 read_file/write_note 衔接)。
"""
import json
import os
import urllib.parse

from core.tools.base import ToolPlugin

# ---------- 页面内 JS: 找表格 / 飞书 sheet 数据资源 ----------
_JS_EXTRACT = r"""(() => {
  const out = {tables: [], sheetApi: null, grids: []};
  // 1) HTML <table>
  document.querySelectorAll('table').forEach((t) => {
    const rows = [];
    t.querySelectorAll('tr').forEach((tr) => {
      const cs = [...tr.querySelectorAll('th,td')].map(c => (c.innerText || '').trim().replace(/\s+/g, ' '));
      if (cs.length) rows.push(cs);
    });
    if (rows.length) out.tables.push({html: t.outerHTML.slice(0, 120000), rows: rows});
  });
  // 2) sheet 数据资源(登录态下内嵌 sheet 单元格来自内部 API; 仅记录 URL 待同源 fetch)
  try {
    const entries = performance.getEntriesByType('resource').map(e => e.name);
    for (const n of entries) {
      if (/sheets|spreadsheet/.test(n) && /larkoffice|feishu/.test(n)) { out.sheetApi = n.slice(0, 600); break; }
    }
  } catch (e) {}
  // 3) 网格容器 innerText(登录态渲染后的表格区兜底)
  try {
    const seen = new Set();
    const cands = [...document.querySelectorAll('div,section')]
      .filter(d => (/(^|\s)(sheet|grid|table-content|spreadsheet|cell-container)/i.test(d.className || '')
                    || (d.getAttribute && d.getAttribute('role') === 'table')));
    cands.sort((a, b) => (b.innerText || '').length - (a.innerText || '').length);
    for (const c of cands.slice(0, 6)) {
      const txt = (c.innerText || '').trim();
      if (txt.length > 15 && !seen.has(txt)) { seen.add(txt); out.grids.push(txt.slice(0, 20000)); }
    }
  } catch (e) {}
  return JSON.stringify(out).slice(0, 60000);
})()"""

_JS_FETCH_SHEET = r"""(async () => {
  const url = window.__TE_SHEET_API__ || '';
  if (!url) return '';
  try {
    const r = await fetch(url, {credentials: 'include'});
    if (!r.ok) return 'HTTP ' + r.status;
    const t = await r.text();
    return t.slice(0, 200000);
  } catch (e) { return 'ERR ' + String(e).slice(0, 120); }
})()"""

_BS = chr(92)  # 反斜杠


def _rows_to_md(rows):
    """手写 MD 表格(无 pandas/tabulate 依赖时的降级)。"""
    if not rows:
        return ""
    lines = []
    for i, row in enumerate(rows):
        cells = [str(c).replace("|", _BS + "|").replace("\n", " ").replace("\r", " ").strip() for c in row]
        lines.append("| " + " | ".join(cells) + " |")
        if i == 0:
            lines.append("|" + "|".join(["---"] * max(len(cells), 1)) + "|")
    return "\n".join(lines)


def _html_to_md(html, rows):
    """优先 pandas.read_html → to_markdown; 失败降级手写 MD。"""
    try:
        import io

        import pandas as pd

        dfs = pd.read_html(io.StringIO(html))
        if dfs:
            md = dfs[0].to_markdown(index=False)
            if md and md.strip():
                return md
    except Exception:
        pass
    return _rows_to_md(rows)


def _cell_text(cell):
    if cell is None:
        return ""
    if isinstance(cell, (str, int, float, bool)):
        return str(cell)
    if isinstance(cell, dict):
        for k in ("text", "value", "str", "raw_text", "display"):
            if k in cell:
                v = cell[k]
                if isinstance(v, dict):
                    v = v.get("text") or v.get("value") or ""
                return str(v or "")
        return ""
    if isinstance(cell, list):
        flat = [str(c) for c in cell if not isinstance(c, (dict, list))]
        return ", ".join(flat)[:120]
    return ""


def _sheet_json_to_md(text):
    """防御性解析飞书 sheet 数据 JSON → MD(递归找「数组的数组」表格结构)。"""
    if not text or str(text).startswith(("HTTP ", "ERR ")):
        return None
    try:
        data = json.loads(text)
    except Exception:
        return None
    best = None  # (rows, cols, rows_data)

    def walk(node):
        nonlocal best
        if isinstance(node, list) and node:
            if all(isinstance(x, list) for x in node):
                rows = []
                ok = True
                for sub in node:
                    cells = []
                    for cell in sub:
                        cells.append(_cell_text(cell))
                    rows.append(cells)
                if ok and rows:
                    cols = max((len(r) for r in rows), default=0)
                    if best is None or (len(rows), cols) > (best[0], best[1]):
                        best = (len(rows), cols, rows)
            for x in node:
                walk(x)
        elif isinstance(node, dict):
            for v in node.values():
                walk(v)

    walk(data)
    if best and best[2]:
        return _rows_to_md(best[2])
    return None


def _clean_grid_text(txt):
    """去零宽字符/控制符, 去空白行; 返回有效行列表。"""
    _bad = {0x200B, 0x200C, 0x200D, 0xFEFF}
    out = []
    for ln in (txt or "").split("\n"):
        s = "".join(ch for ch in ln if ord(ch) not in _bad and ord(ch) not in range(0x00, 0x20))
        s = s.strip()
        if len(s) >= 2:
            out.append(s)
    return out


def _grid_text_to_md(txt):
    """网格 innerText → MD。多空格/制表符分隔列时按列还原, 否则单列表格保序。"""
    lines = _clean_grid_text(txt)
    if len(lines) < 2:
        return ""  # 无有效内容(登录墙/空 sheet 常见: 仅 0/0 或标题)
    import re as _re_g

    split_rows = [_re_g.split(r"[ \t]{2,}", ln) for ln in lines]
    multi_col = sum(1 for r in split_rows if len(r) >= 2)
    if multi_col >= max(2, len(split_rows) // 2):
        return _rows_to_md(split_rows)
    return _rows_to_md([[ln] for ln in lines])


def _parse_js_result(txt):
    """解析 evaluate 返回(可能包多层 JSON 字符串)。"""
    if not txt:
        return None
    s = str(txt).strip()
    for _ in range(8):
        if not s:
            return None
        if s.startswith("{") or s.startswith("["):
            try:
                return json.loads(s)
            except Exception:
                return None
        if s[0] == '"':
            try:
                s = json.loads(s)
            except Exception:
                return None
        else:
            return None
    return None


def _compose_markdown(tables, grids, sheet_md=None):
    parts = []
    for i, tb in enumerate(tables or []):
        md = _html_to_md(tb.get("html", "") or "", tb.get("rows") or [])
        if md and md.strip():
            parts.append("### 网页表格 " + str(i + 1) + "\n\n" + md)
    if sheet_md:
        parts.append("### 内嵌表格(数据接口)\n\n" + sheet_md)
    for gi, g in enumerate(grids or []):
        md = _grid_text_to_md(g)
        if md and md.strip():
            parts.append("### 网格内容 " + str(gi + 1) + "\n\n" + md)
    return "\n\n".join(parts)


def _extract_via_playwright(url, wait_ms=8000, timeout=45, sheet_token="", user_id="", session_id=""):
    """playwright headless 通道(公开页面/无登录态)。返回 {success, markdown, ...}。"""
    # 批197：浏览器**唯一出口**（原来这里自己 launch ⇒ 与其它两处各起一个）
    from core.tools import browser_runtime as _brt

    with _brt.browser_ctx() as browser:
        page = None
        try:
            page = browser.new_page()
            try:
                page.goto(url, wait_until="load", timeout=30000)
            except Exception:
                pass
            page.wait_for_timeout(int(wait_ms))
            js_pre = "window.__TE_TOKEN__=" + json.dumps(sheet_token or "") + ";"
            raw = page.evaluate(js_pre + "(" + _JS_EXTRACT + ")")
            parsed = raw if isinstance(raw, dict) else _parse_js_result(str(raw))
            parsed = parsed or {}
            tables = parsed.get("tables") or []
            grids = parsed.get("grids") or []
            sheet_md = None
            sheet_api = parsed.get("sheetApi")
            if sheet_api and ("larkoffice" in url or "feishu" in url):
                try:
                    page.evaluate("window.__TE_SHEET_API__=" + json.dumps(sheet_api) + ";")
                    txt = page.evaluate(_JS_FETCH_SHEET)
                    sheet_md = _sheet_json_to_md(txt or "")
                except Exception:
                    sheet_md = None
            markdown = _compose_markdown(tables, grids, sheet_md)
            if not markdown.strip():
                body = ""
                try:
                    body = page.inner_text("body")[:300]
                except Exception:
                    pass
                return {"success": False, "error": "页面未检测到表格(HTML table/内嵌 sheet 均无内容), 可能需登录态。页面线索: " + body[:180]}
            return {
                "success": True,
                "markdown": markdown,
                "tables": len(tables) + (1 if sheet_md else 0),
                "source": "playwright",
                "sheet_api": sheet_api or "",
            }
        finally:
            try:
                if page is not None:
                    page.close()
                browser.close()
            except Exception:
                pass


def extract_tables(url, wait_ms=8000, sheet_token="", user_id="", session_id="", timeout=45):
    """确定性表格提取主入口。browser_local(登录态) 优先, playwright 兜底。"""
    from core.lib.gateway_helpers import _is_private_host

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return {"success": False, "error": "仅支持 http/https URL"}
    if _is_private_host(parsed.hostname or ""):
        return {"success": False, "error": "localhost/内网地址不允许访问"}

    # ---- 通道1: browser_local(用户真实浏览器, 复用登录态) ----
    if user_id:
        try:
            from core.lib.v8 import browser_local as _bl

            nav = _bl.execute(
                user_id, "navigate", {"url": url, "wait_ms": int(wait_ms)}, timeout=timeout, session_id=session_id
            )
            if nav and nav.get("success"):
                js_pre = "window.__TE_TOKEN__=" + json.dumps(sheet_token or "") + ";"
                ev = _bl.execute(
                    user_id,
                    "evaluate",
                    {"expr": js_pre + "(" + _JS_EXTRACT + ")"},
                    timeout=timeout,
                    session_id=session_id,
                )
                inner = ""
                try:
                    inner = (ev.get("data") or {}).get("result") or ""
                except Exception:
                    inner = ""
                parsed_js = _parse_js_result(inner)
                if parsed_js is not None:
                    md = _compose_markdown(parsed_js.get("tables") or [], parsed_js.get("grids") or [])
                    if md.strip():
                        return {
                            "success": True,
                            "markdown": md,
                            "tables": len(parsed_js.get("tables") or []),
                            "source": "browser_local(登录态)",
                            "sheet_api": parsed_js.get("sheetApi") or "",
                        }
        except Exception:
            pass  # 回退 playwright

    # ---- 通道2: playwright headless ----
    return _extract_via_playwright(
        url, wait_ms=wait_ms, timeout=timeout, sheet_token=sheet_token, user_id=user_id, session_id=session_id
    )


# ---------- 插件注册 ----------
TABLE_EXTRACT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "table_extract",
        "strict": True,
        "description": (
            "确定性读取网页表格并转 Markdown 表格(一次调用完成, 不要用多步 browser_local 循环去拆表)。"
            "自动: 1) 优先用登录态浏览器(browser_local)打开 url; 2) 检测页面 HTML 表格与飞书/内嵌 sheet"
            "(含 sheet 数据接口抓取); 3) pandas 解析成 Markdown。返回 markdown 字段(多个表格分节)。"
            "适用: 飞书阶梯激励表/活动表、榜单、任何 HTML table 页。配合 write_note 把 markdown 落盘。"
            "仅 http/https 公网, 禁止内网。"
        ),
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "url": {"type": "string", "description": "目标页面 URL(含表格, http/https)"},
                "sheet": {
                    "type": "string",
                    "description": "可选: 飞书 wiki 页内嵌表格的 sheet token(如 WIVqs3MgxhD2qktU0OecSbvZnSd), 帮助定位",
                },
                "wait_ms": {"type": "integer", "description": "可选: 页面加载后等待毫秒(默认 8000, SPA/飞书建议 ≥8000)"},
            },
            "required": ["url"],
        },
    },
}


class TableExtractPlugin(ToolPlugin):
    name = "table_extract"
    quota = 5
    schema = TABLE_EXTRACT_SCHEMA

    def execute(self, args: dict, ctx) -> dict:
        url = str((args or {}).get("url") or "").strip()
        if not url:
            return {"success": False, "error": "table_extract 需要 url"}
        user_id = getattr(ctx, "user_id", "") or ""
        session_id = getattr(ctx, "session_id", "") or ""
        sheet = str((args or {}).get("sheet") or "").strip()
        try:
            wait_ms = int(args.get("wait_ms") or 8000)
        except (TypeError, ValueError):
            wait_ms = 8000
        r = extract_tables(url, wait_ms=wait_ms, sheet_token=sheet, user_id=user_id, session_id=session_id)
        if r.get("success"):
            md = r.get("markdown") or ""
            r["markdown_head"] = md[:200]
            r["markdown_len"] = len(md)
            r["chars"] = len(md)
        return r
