# -*- coding: utf-8 -*-
"""PA 第二大脑 · 笔记本（Notebook）层（P1，对标 NotebookLM）。

一笔记本 ＝ 一组来源（sources）＋ 对话 ＋ Studio 产出。
- 来源仍是 note（md/url/pdf/voice/screen 同一模型，文件是唯一真相）；
- 笔记本元数据落 workspace/notebooks.json（原子写）；note 以 notebook_id 归属；
- 问答/生成只检索本笔记本，⛔ 越界引用别本；
- 模型不可用 ⇒ 照实回落为「摘录」，⛔ 假装生成成功。
"""
from __future__ import annotations

import io
import ipaddress
import json
import os
import re
import socket
import uuid
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

from core.pa import notes as N

NB_ID_RE = re.compile(r"^nb-[0-9]{8}-[0-9]{6}-[0-9a-f]{6}$")
MAX_SOURCES = 200
MAX_URL_BYTES = 2 * 1024 * 1024
MAX_PDF_BYTES = 50 * 1024 * 1024
MAX_SOURCE_TEXT = 300 * 1024
STUDIO_KINDS = {
    "summary": "摘要",
    "faq": "常见问题",
    "study": "学习指南",
    "mindmap": "思维导图",
    "report": "报告",
    "flashcards": "闪卡",
    "quiz": "测验",
    "slides": "演示文稿",
    "datatable": "数据表格",
}


class NotebookError(Exception):
    pass


def _root(data_dir=None):
    return N.workspace_root(data_dir)


def _file(data_dir=None):
    p = _root(data_dir) / "notebooks.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _new_id():
    return "nb-" + datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]


def _safe_id(nb_id):
    nid = str(nb_id or "").strip()
    if not NB_ID_RE.match(nid):
        raise NotebookError("notebook id 不合法")
    return nid


def _load(data_dir=None):
    p = _file(data_dir)
    if not p.exists():
        return []
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        raise NotebookError("notebooks.json 损坏（未覆盖，先照实报）")
    if isinstance(raw, dict):
        raw = raw.get("notebooks")
    if not isinstance(raw, list):
        raise NotebookError("notebooks.json 形态不合（未覆盖）")
    return [x for x in raw if isinstance(x, dict) and NB_ID_RE.match(str(x.get("id") or ""))]


def _save(items, data_dir=None):
    p = _file(data_dir)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"version": 1, "notebooks": items}, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8", newline="\n")
    os.replace(tmp, p)


def _clean_title(t):
    return str(t or "").strip()[:120] or "未命名笔记本"


def _clean_emoji(e):
    s = str(e or "").strip()
    return s[:8] if s else "📘"


def _source_counts(data_dir=None):
    return {k: v for k, v in N.count_by_notebook(data_dir=data_dir).items() if k}


def list_notebooks(data_dir=None):
    items = _load(data_dir)
    counts = _source_counts(data_dir)
    out = []
    for x in items:
        d = dict(x)
        d["source_count"] = counts.get(d["id"], 0)
        out.append(d)
    out.sort(key=lambda d: str(d.get("updated") or ""), reverse=True)
    return out


def get(nb_id, data_dir=None):
    nid = _safe_id(nb_id)
    for x in _load(data_dir):
        if x.get("id") == nid:
            d = dict(x)
            d["source_count"] = _source_counts(data_dir).get(nid, 0)
            return d
    raise NotebookError("笔记本不存在")


def create(title, emoji="📘", description="", data_dir=None):
    items = _load(data_dir)
    now = _now()
    nb = {"id": _new_id(), "title": _clean_title(title), "emoji": _clean_emoji(emoji),
          "description": str(description or "").strip()[:400], "created": now, "updated": now}
    items.append(nb)
    _save(items, data_dir)
    nb["source_count"] = 0
    return nb


def update(nb_id, title=None, emoji=None, description=None, data_dir=None):
    nid = _safe_id(nb_id)
    items = _load(data_dir)
    for x in items:
        if x.get("id") != nid:
            continue
        if title is not None:
            x["title"] = _clean_title(title)
        if emoji is not None:
            x["emoji"] = _clean_emoji(emoji)
        if description is not None:
            x["description"] = str(description or "").strip()[:400]
        x["updated"] = _now()
        _save(items, data_dir)
        d = dict(x)
        d["source_count"] = _source_counts(data_dir).get(nid, 0)
        return d
    raise NotebookError("笔记本不存在")


def delete(nb_id, data_dir=None):
    """删笔记本 ⇒ 来源退回「未归档」，⛔ 删用户笔记。"""
    nid = _safe_id(nb_id)
    items = _load(data_dir)
    keep = [x for x in items if x.get("id") != nid]
    if len(keep) == len(items):
        raise NotebookError("笔记本不存在")
    moved = 0
    for n in N.list_notes(limit=N.MAX_LIMIT, data_dir=data_dir, notebook_id=nid):
        N.update(n["id"], data_dir=data_dir, notebook_id="")
        moved += 1
    _save(keep, data_dir)
    return {"id": nid, "deleted": True, "moved_sources": moved}


def sources(nb_id, data_dir=None, limit=MAX_SOURCES):
    get(nb_id, data_dir=data_dir)
    return N.list_notes(limit=limit, data_dir=data_dir, notebook_id=_safe_id(nb_id))


def add_text(nb_id, title, body, tags=None, data_dir=None, source="manual"):
    get(nb_id, data_dir=data_dir)
    return N.create(title, body, tags or [], data_dir=data_dir, source=source,
                    notebook_id=_safe_id(nb_id))


# ---------- 来源提取（URL / PDF） ----------

class _TextExtract(HTMLParser):
    BLOCK = {"p", "div", "section", "article", "li", "br", "h1", "h2", "h3", "h4", "tr", "pre"}
    SKIP = {"script", "style", "noscript", "svg"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.title = ""
        self._skip = 0
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in self.SKIP:
            self._skip += 1
        if tag == "title":
            self._in_title = True
        if tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        if tag == "title":
            self._in_title = False
        if tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._skip:
            return
        if self._in_title:
            self.title += data
            return
        self.parts.append(data)

    def text(self):
        t = "".join(self.parts)
        t = re.sub(r"[ \t\r\f\v]+", " ", t)
        t = re.sub(r"\n\s*\n\s*\n+", "\n\n", t)
        return t.strip()


def _host_is_public(host):
    if not host:
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except Exception:
            return False
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast
                or ip.is_reserved or ip.is_unspecified):
            return False
    return True


def _check_url(url):
    u = str(url or "").strip()
    if not u:
        raise NotebookError("网址为空")
    p = urlparse(u)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise NotebookError("只收 http/https 网址")
    if not _host_is_public(p.hostname):
        raise NotebookError("不收本机/内网地址（防打穿本机服务）")
    return u


def add_url(nb_id, url, data_dir=None):
    get(nb_id, data_dir=data_dir)
    u = _check_url(url)
    try:
        import requests
    except Exception:
        raise NotebookError("本机缺 requests，不能抓网页")
    try:
        r = requests.get(u, timeout=20, allow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0 (ClawsJoy PA notebook)"})
        r.raise_for_status()
        raw = r.content[:MAX_URL_BYTES]
        ctype = str(r.headers.get("content-type") or "").lower()
        if "pdf" in ctype or u.lower().endswith(".pdf"):
            return add_pdf(nb_id, u.rsplit("/", 1)[-1] or "source.pdf", raw, data_dir=data_dir)
        enc = r.encoding or r.apparent_encoding or "utf-8"
        html = raw.decode(enc, errors="replace")
    except NotebookError:
        raise
    except Exception as e:
        raise NotebookError("抓网页失败：%s: %s" % (type(e).__name__, str(e)[:120]))
    ex = _TextExtract()
    try:
        ex.feed(html)
    except Exception:
        pass
    text = ex.text()[:MAX_SOURCE_TEXT]
    if len(text) < 20:
        raise NotebookError("网页正文太少（可能是需登录/JS 渲染页）")
    title = (ex.title or "").strip() or urlparse(u).path.rsplit("/", 1)[-1] or u
    note = N.create(title[:120], text, ["网页"], data_dir=data_dir, source="url",
                    source_path=u, notebook_id=_safe_id(nb_id))
    return {"note": note, "chars": len(text), "url": u}


def add_pdf(nb_id, filename, data, data_dir=None):
    get(nb_id, data_dir=data_dir)
    raw = data or b""
    if len(raw) > MAX_PDF_BYTES:
        raise NotebookError("PDF 太大（上限 50 MB）")
    if not raw:
        raise NotebookError("空文件")
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(raw))
        parts, title = [], ""
        try:
            title = str((reader.metadata or {}).get("/Title") or "").strip()
        except Exception:
            title = ""
        for i, page in enumerate(reader.pages):
            if i >= 200:
                break
            try:
                parts.append(page.extract_text() or "")
            except Exception:
                continue
        text = "\n\n".join(x.strip() for x in parts if x and x.strip())[:MAX_SOURCE_TEXT]
    except Exception as e:
        raise NotebookError("读 PDF 失败：%s: %s" % (type(e).__name__, str(e)[:120]))
    if len(text) < 10:
        raise NotebookError("PDF 没抽到文字（可能是扫描件，需 OCR）")
    title = title or Path(filename or "source.pdf").stem
    root = _root(data_dir) / "sources" / _safe_id(nb_id)
    root.mkdir(parents=True, exist_ok=True)
    dst = root / (uuid.uuid4().hex[:10] + ".pdf")
    dst.write_bytes(raw)
    note = N.create(title[:120], text, ["PDF"], data_dir=data_dir, source="pdf",
                    source_path=str(dst), notebook_id=_safe_id(nb_id))
    return {"note": note, "chars": len(text), "path": str(dst)}


def ask(nb_id, question, limit=6, data_dir=None, llm_fn=None, note_ids=None):
    get(nb_id, data_dir=data_dir)
    ids = None
    if note_ids is not None:
        allowed = {x["id"] for x in sources(nb_id, data_dir=data_dir)}
        ids = [str(x) for x in note_ids if str(x) in allowed]
        if not ids:
            raise NotebookError("没有勾选本笔记本的来源")
    return N.ask(question, data_dir=data_dir, limit=limit, llm_fn=llm_fn,
                 notebook_id=_safe_id(nb_id), note_ids=ids)


# ---------- Studio ----------

def _snippets(nb_id, data_dir=None, cap=2400, note_ids=None):
    rows = sources(nb_id, data_dir=data_dir)
    if note_ids is not None:
        allowed = {str(x) for x in note_ids}
        rows = [x for x in rows if str(x.get("id")) in allowed]
    out = []
    for i, n in enumerate(rows, 1):
        full = N.get(n["id"], data_dir=data_dir)
        body = (full.get("body") or "").strip()
        out.append({"n": i, "id": n["id"], "title": n.get("title", ""),
                    "body": body[:cap], "source": n.get("source", "")})
    return out


def _cite_list(items):
    return [{"id": x["id"], "title": x["title"], "snippet": x["body"][:240], "n": x["n"]} for x in items]


def _fallback(kind, nb, items):
    head = "## %s（模型暂不可用 · 以下为摘录）\n\n" % STUDIO_KINDS.get(kind, kind)
    if kind == "summary":
        lines = ["- [%d] %s：%s" % (x["n"], x["title"], re.sub(r"\s+", " ", x["body"])[:160]) for x in items]
        return head + "\n".join(lines)
    if kind == "mindmap":
        lines = ["- %s" % nb.get("title", "笔记本")]
        lines += ["  - [%d] %s" % (x["n"], x["title"]) for x in items]
        return head + "\n".join(lines)
    if kind == "flashcards":
        lines = ["### 卡 %d" % x["n"] + "\n问：" + x["title"] + "\n答：" + re.sub(r"\s+", " ", x["body"])[:180] + " [%d]" % x["n"]
                 for x in items]
        return head + "\n\n".join(lines)
    if kind == "quiz":
        lines = ["%d. %s\nA. 是\nB. 否\n答案：A\n解析：见来源 [%d]" % (i, x["title"], x["n"])
                 for i, x in enumerate(items, 1)]
        return head + "\n\n".join(lines)
    if kind == "slides":
        lines = ["## 第 %d 页 %s\n- %s [%d]" % (i, x["title"], re.sub(r"\s+", " ", x["body"])[:120], x["n"])
                 for i, x in enumerate(items, 1)]
        return head + "\n\n".join(lines)
    if kind == "datatable":
        lines = ["| 主题 | 要点 | 出处 |", "|---|---|---|"]
        lines += ["| %s | %s | [%d] |" % (x["title"], re.sub(r"\s+", " ", x["body"])[:80], x["n"]) for x in items]
        return head + "\n".join(lines)
    return head + "模型不可用，未生成内容。来源：" + "、".join("[%d] %s" % (x["n"], x["title"]) for x in items)


def studio(nb_id, kind="summary", data_dir=None, llm_fn=None, max_sources=12, note_ids=None,
           options=None):
    nb = get(nb_id, data_dir=data_dir)
    kind = str(kind or "summary")
    if kind not in STUDIO_KINDS:
        raise NotebookError("不支持的 Studio 类型")
    items = _snippets(nb_id, data_dir=data_dir, note_ids=note_ids)[:max_sources]
    if not items:
        raise NotebookError("先加来源，再生成")
    chunks = "\n\n---\n\n".join("[note:%s] %s\n%s" % (x["id"], x["title"], x["body"]) for x in items)
    instr = {
        "summary": "用 6-10 条要点总结这些来源；每条末尾用 [note:<id>] 标出处（必须保留 note: 前缀，id 照抄）；开头一句总览。",
        "faq": "生成 8 组常见问题与答案（Q:/A:）；答案只用来源内容，末尾用 [note:<id>] 标出处（必须保留 note: 前缀）。",
        "study": "生成学习指南：核心概念、3 个易错点、5 个复习问题；用 [note:<id>] 标出处（必须保留 note: 前缀）。",
        "mindmap": "生成层级思维导图（Markdown 嵌套列表，根为笔记本名，二层为来源主题）；不要编造来源外内容；需要标来源时用 [note:<id>]。",
        "report": "生成一份结构化报告：背景／关键发现（5-8 条）／证据／风险与建议；每条发现后用 [note:<id>] 标出处。",
        "flashcards": "生成 12 张闪卡；每张严格三行：第一行 ### 卡 N，第二行 问：…，第三行 答：…；答末尾用 [note:<id>] 标出处。",
        "quiz": "生成 8 道单选题；每题 4 个选项、正确答案、一句解析，末尾用 [note:<id>] 标出处。",
        "slides": "生成 8 页演示文稿大纲；每页：## 第 N 页 标题，下接 3-5 条要点；关键事实用 [note:<id>] 标出处。",
        "datatable": "用 Markdown 表格总结来源中的事实：列＝主题｜要点｜出处；只写来源里有的内容，出处列用 [note:<id>]。",
    }[kind]
    opt = options if isinstance(options, dict) else {}
    extra = ""
    if opt.get("format"):
        extra += "输出格式：%s。\n" % str(opt.get("format"))[:120]
    if opt.get("language"):
        extra += "输出语言：%s。\n" % str(opt.get("language"))[:40]
    if opt.get("focus"):
        extra += "请重点：%s。\n" % str(opt.get("focus"))[:600]
    prompt = ("你是 PA 第二大脑的 Studio。只依据下面来源，不要编造；%s\n%s\n笔记本：%s\n\n来源：\n%s\n"
              % (instr, extra, nb.get("title", ""), chunks))
    model_ok, why, md = False, "", ""
    try:
        md = (llm_fn or N.llm_generate)(prompt)
        model_ok = bool(str(md or "").strip())
    except Exception as e:
        why = type(e).__name__
    md = str(md or "").strip()
    if not model_ok or md.startswith("模型不可用") or "LLM_UNAVAILABLE" in md:
        md = _fallback(kind, nb, items)
        model_ok = False
    return {"kind": kind, "title": "%s · %s" % (nb.get("title", "笔记本"), STUDIO_KINDS[kind]),
            "markdown": md[:12000], "model_ok": model_ok, "why": why,
            "citations": _cite_list(items), "notebook_id": nb_id}


def recent_outputs(nb_id, data_dir=None, limit=6):
    """最近 Studio 产出（落在本笔记本的 note，标签含 Studio）。"""
    get(nb_id, data_dir=data_dir)
    out = []
    for n in sources(nb_id, data_dir=data_dir):
        tags = [str(t) for t in (n.get("tags") or [])]
        if "Studio" not in tags and str(n.get("source") or "") != "ai":
            continue
        out.append({"id": n["id"], "title": n.get("title", ""), "updated": n.get("updated", ""),
                    "kind": next((t for t in tags if t != "Studio"), "Studio")})
    out.sort(key=lambda x: str(x.get("updated") or ""), reverse=True)
    return out[:limit]


def save_output(nb_id, title, body, kind="summary", data_dir=None):
    get(nb_id, data_dir=data_dir)
    tags = ["Studio", STUDIO_KINDS.get(kind, kind)]
    return N.create(title or "Studio 产出", body, tags, data_dir=data_dir, source="ai",
                    notebook_id=_safe_id(nb_id))
