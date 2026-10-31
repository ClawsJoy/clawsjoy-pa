# -*- coding: utf-8 -*-
"""PA 自有第二大脑 · note core（P0）

设计（docs/second_brain/01_第二大脑_note系统.md）：
- 正文 Markdown + YAML 风格 frontmatter；一篇一 .md；
- 索引 SQLite（FTS5 可选，LIKE 兜底）；
- 索引可重建；文件是唯一真相；
- 不依赖 Obsidian；可导入 md 目录。
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

MAX_BODY = 512 * 1024
MAX_TITLE = 200
DEFAULT_LIMIT = 50
MAX_LIMIT = 200
NOTE_ID_RE = re.compile(r"^[0-9]{8}-[0-9]{6}-[0-9a-f]{6}$")


class NoteError(Exception):
    pass


def workspace_root(data_dir=None):
    base = os.getenv("PA_WORKSPACE_DIR")
    if not base:
        base = os.path.join(data_dir or os.getenv("PA_DATA_DIR", "data/v9/pa"), "workspace")
    return Path(base)


def notes_dir(data_dir=None):
    return workspace_root(data_dir) / "notes"


def db_path(data_dir=None):
    return workspace_root(data_dir) / "index.sqlite"


def _now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _new_id():
    return datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]


def _clip(s, n):
    s = "" if s is None else str(s)
    return s if len(s) <= n else s[:n]


def _safe_id(note_id):
    nid = str(note_id or "").strip()
    if not NOTE_ID_RE.match(nid):
        raise NoteError("note id 不合法")
    return nid


def _render(meta, body):
    lines = ["---"]
    for k in ("id", "title", "tags", "created", "updated", "source", "source_path", "notebook_id"):
        if k not in meta:
            continue
        v = meta.get(k)
        if k == "tags":
            v = json.dumps(v or [], ensure_ascii=False)
        elif isinstance(v, str):
            v = json.dumps(v, ensure_ascii=False)
        lines.append("%s: %s" % (k, v))
    lines.append("---")
    lines.append("")
    lines.append(body or "")
    return "\n".join(lines).rstrip() + "\n"


def _parse(text):
    text = (text or "").lstrip("\ufeff")
    meta = {}
    body = text
    if text.startswith("---"):
        parts = text.split("\n---", 2)
        if len(parts) >= 2:
            head = parts[0][3:].strip("\n")
            rest = parts[1].lstrip("\n")
            meta = {}
            for line in head.splitlines():
                if ":" not in line:
                    continue
                k, v = line.split(":", 1)
                k = k.strip()
                v = v.strip()
                if not k:
                    continue
                if k == "tags":
                    try:
                        v = json.loads(v)
                    except Exception:
                        v = [x.strip() for x in v.strip("[]").split(",") if x.strip()]
                else:
                    try:
                        if v.startswith('"') and v.endswith('"'):
                            v = json.loads(v)
                    except Exception:
                        pass
                meta[k] = v
            body = rest.strip("\n")
    return meta, body


def _write_file(root, nid, meta, body):
    p = root / "notes" / (nid + ".md")
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".md.tmp")
    tmp.write_text(_render(meta, body), encoding="utf-8", newline="\n")
    os.replace(tmp, p)
    return p


def _conn(root):
    root.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(root / "index.sqlite"))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("""CREATE TABLE IF NOT EXISTS notes(
        id TEXT PRIMARY KEY, title TEXT, path TEXT, tags TEXT,
        created TEXT, updated TEXT, body TEXT, source TEXT, source_path TEXT,
        notebook_id TEXT DEFAULT '')""")
    _cols = [r[1] for r in c.execute("PRAGMA table_info(notes)").fetchall()]
    if "notebook_id" not in _cols:
        c.execute("ALTER TABLE notes ADD COLUMN notebook_id TEXT DEFAULT ''")
    try:
        c.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
            id UNINDEXED, title, body, tags)""")
    except sqlite3.OperationalError:
        pass
    c.commit()
    return c


def _upsert(c, meta):
    nid = meta["id"]
    c.execute("""INSERT OR REPLACE INTO notes
        (id,title,path,tags,created,updated,body,source,source_path,notebook_id)
        VALUES(?,?,?,?,?,?,?,?,?,?)""",
              (nid, meta.get("title", ""), meta.get("path", ""),
               json.dumps(meta.get("tags") or [], ensure_ascii=False),
               meta.get("created", ""), meta.get("updated", ""),
               meta.get("body", ""), meta.get("source", ""), meta.get("source_path", ""),
               meta.get("notebook_id") or ""))
    try:
        c.execute("DELETE FROM notes_fts WHERE id=?", (nid,))
        c.execute("INSERT INTO notes_fts(id,title,body,tags) VALUES(?,?,?,?)",
                  (nid, meta.get("title", ""), meta.get("body", ""),
                   " ".join(meta.get("tags") or [])))
    except sqlite3.OperationalError:
        pass
    c.commit()


def _row_to_note(r, with_body=False):
    d = {"id": r["id"], "title": r["title"] or "", "tags": json.loads(r["tags"] or "[]"),
         "created": r["created"] or "", "updated": r["updated"] or "",
         "source": r["source"] or "", "path": r["path"] or "",
         "notebook_id": (r["notebook_id"] if "notebook_id" in r.keys() else "") or ""}
    if with_body:
        d["body"] = r["body"] or ""
    return d


def create(title, body="", tags=None, data_dir=None, source="manual", source_path="",
           notebook_id=""):
    root = workspace_root(data_dir)
    title = _clip((title or "").strip() or "未命名", MAX_TITLE)
    body = _clip(body or "", MAX_BODY)
    tags = [str(t).strip()[:40] for t in (tags or []) if str(t).strip()][:20]
    nid = _new_id()
    now = _now()
    meta = {"id": nid, "title": title, "tags": tags, "created": now, "updated": now,
            "source": source or "manual", "source_path": source_path or "",
            "notebook_id": notebook_id or ""}
    p = _write_file(root, nid, meta, body)
    meta["path"] = str(p)
    meta["body"] = body
    c = _conn(root)
    try:
        _upsert(c, meta)
    finally:
        c.close()
    return {"id": nid, "title": title, "tags": tags, "created": now, "updated": now,
            "source": meta["source"], "path": str(p), "notebook_id": notebook_id or ""}


def _read(root, nid, with_body=True):
    p = root / "notes" / (nid + ".md")
    if not p.exists():
        raise NoteError("note 不存在")
    meta, body = _parse(p.read_text(encoding="utf-8", errors="replace"))
    meta["id"] = nid
    meta["path"] = str(p)
    meta["body"] = body
    meta.setdefault("title", p.stem)
    meta.setdefault("tags", [])
    return meta


def get(nid, data_dir=None):
    root = workspace_root(data_dir)
    nid = _safe_id(nid)
    m = _read(root, nid)
    return {"id": nid, "title": m.get("title", ""), "tags": m.get("tags") or [],
            "created": m.get("created", ""), "updated": m.get("updated", ""),
            "source": m.get("source", ""), "path": m.get("path", ""),
            "source_path": m.get("source_path", ""), "body": m.get("body", ""),
            "notebook_id": m.get("notebook_id", "") or ""}


def list_notes(q="", data_dir=None, limit=DEFAULT_LIMIT, notebook_id=None):
    root = workspace_root(data_dir)
    limit = max(1, min(int(limit or DEFAULT_LIMIT), MAX_LIMIT))
    nb = None if notebook_id is None else str(notebook_id or "")
    c = _conn(root)
    try:
        q = (q or "").strip()
        if not q:
            if nb is None:
                rows = c.execute("SELECT * FROM notes ORDER BY updated DESC LIMIT ?", (limit,)).fetchall()
            else:
                rows = c.execute("SELECT * FROM notes WHERE notebook_id=? ORDER BY updated DESC LIMIT ?",
                                 (nb, limit)).fetchall()
            return [_row_to_note(r) for r in rows]
        rows = []
        try:
            terms = [t for t in re.split(r"\s+", q) if t]
            fts_q = " ".join('"' + t.replace('"', '') + '"' for t in terms)
            if nb is None:
                rows = c.execute("""SELECT n.* FROM notes_fts f JOIN notes n ON n.id=f.id
                                    WHERE notes_fts MATCH ? ORDER BY rank LIMIT ?""",
                                 (fts_q, limit)).fetchall()
            else:
                rows = c.execute("""SELECT n.* FROM notes_fts f JOIN notes n ON n.id=f.id
                                    WHERE notes_fts MATCH ? AND n.notebook_id=? ORDER BY rank LIMIT ?""",
                                 (fts_q, nb, limit)).fetchall()
        except sqlite3.OperationalError:
            rows = []
        if not rows:
            like = "%" + q + "%"
            if nb is None:
                rows = c.execute("""SELECT * FROM notes WHERE title LIKE ? OR body LIKE ? OR tags LIKE ?
                                    ORDER BY updated DESC LIMIT ?""", (like, like, like, limit)).fetchall()
            else:
                rows = c.execute("""SELECT * FROM notes WHERE (title LIKE ? OR body LIKE ? OR tags LIKE ?)
                                    AND notebook_id=? ORDER BY updated DESC LIMIT ?""",
                                 (like, like, like, nb, limit)).fetchall()
        if not rows and len(q) > 3:
            # 中文自然问句无空格：用 2 字片段召回，再按命中数排序。
            grams = []
            for i in range(len(q) - 1):
                g = q[i:i + 2]
                if re.search(r"[\s，。？！、,.;:!?]", g):
                    continue
                if g not in grams:
                    grams.append(g)
            scored = {}
            for g in grams[:8]:
                like = "%" + g + "%"
                sql = "SELECT * FROM notes WHERE (title LIKE ? OR body LIKE ? OR tags LIKE ?)"
                params = [like, like, like]
                if nb is not None:
                    sql += " AND notebook_id=?"
                    params.append(nb)
                sql += " LIMIT 200"
                for r in c.execute(sql, params).fetchall():
                    scored[r["id"]] = scored.get(r["id"], 0) + 1
            if scored:
                rows = c.execute("SELECT * FROM notes WHERE id IN (%s)" % ",".join("?" * len(scored)),
                                 tuple(scored.keys())).fetchall()
                rows = sorted(rows, key=lambda r: (-scored.get(r["id"], 0), r["updated"] or ""))[:limit]
        return [_row_to_note(r) for r in rows]
    finally:
        c.close()


def count_by_notebook(data_dir=None):
    root = workspace_root(data_dir)
    c = _conn(root)
    try:
        rows = c.execute("SELECT notebook_id, COUNT(*) AS n FROM notes GROUP BY notebook_id").fetchall()
        return {str(r["notebook_id"] or ""): int(r["n"]) for r in rows}
    finally:
        c.close()


def update(nid, title=None, body=None, tags=None, data_dir=None, notebook_id=None):
    root = workspace_root(data_dir)
    nid = _safe_id(nid)
    m = _read(root, nid)
    if title is not None:
        m["title"] = _clip((title or "").strip() or m.get("title", "未命名"), MAX_TITLE)
    if body is not None:
        m["body"] = _clip(body or "", MAX_BODY)
    if tags is not None:
        m["tags"] = [str(t).strip()[:40] for t in (tags or []) if str(t).strip()][:20]
    if notebook_id is not None:
        m["notebook_id"] = str(notebook_id or "")
    m["updated"] = _now()
    p = _write_file(root, nid, m, m.get("body", ""))
    m["path"] = str(p)
    c = _conn(root)
    try:
        _upsert(c, m)
    finally:
        c.close()
    return {"id": nid, "title": m.get("title", ""), "tags": m.get("tags") or [],
            "created": m.get("created", ""), "updated": m["updated"], "path": str(p),
            "notebook_id": m.get("notebook_id", "") or ""}


def delete(nid, data_dir=None):
    root = workspace_root(data_dir)
    nid = _safe_id(nid)
    p = root / "notes" / (nid + ".md")
    if p.exists():
        p.unlink()
    c = _conn(root)
    try:
        c.execute("DELETE FROM notes WHERE id=?", (nid,))
        try:
            c.execute("DELETE FROM notes_fts WHERE id=?", (nid,))
        except sqlite3.OperationalError:
            pass
        c.commit()
    finally:
        c.close()
    return {"id": nid, "deleted": True}


def import_dir(path, data_dir=None, notebook_id=""):
    src = Path(path).expanduser()
    if not src.exists() or not src.is_dir():
        raise NoteError("导入目录不存在")
    root = workspace_root(data_dir)
    c = _conn(root)
    imported, skipped = 0, 0
    try:
        for p in sorted(src.rglob("*.md")):
            try:
                rel = str(p.relative_to(src))
                key = str(p.resolve())
                if c.execute("SELECT 1 FROM notes WHERE source_path=?", (key,)).fetchone():
                    skipped += 1
                    continue
                meta, body = _parse(p.read_text(encoding="utf-8", errors="replace"))
                title = str(meta.get("title") or p.stem)[:MAX_TITLE]
                tags = meta.get("tags") if isinstance(meta.get("tags"), list) else []
                nid = _new_id()
                now = _now()
                nm = {"id": nid, "title": title, "tags": tags[:20], "created": now,
                      "updated": now, "source": "import", "source_path": key,
                      "notebook_id": notebook_id or ""}
                fp = _write_file(root, nid, nm, body)
                nm["path"] = str(fp); nm["body"] = body
                _upsert(c, nm)
                imported += 1
            except Exception:
                skipped += 1
        return {"ok": True, "imported": imported, "skipped": skipped, "source": str(src),
                "notebook_id": notebook_id or ""}
    finally:
        c.close()


def reindex(data_dir=None):
    root = workspace_root(data_dir)
    c = _conn(root)
    seen = set()
    try:
        c.execute("DELETE FROM notes")
        try:
            c.execute("DELETE FROM notes_fts")
        except sqlite3.OperationalError:
            pass
        for p in sorted((root / "notes").glob("*.md")):
            nid = p.stem
            if not NOTE_ID_RE.match(nid):
                continue
            meta, body = _parse(p.read_text(encoding="utf-8", errors="replace"))
            meta["id"] = nid
            meta["path"] = str(p)
            meta["body"] = body
            meta.setdefault("title", nid)
            meta.setdefault("tags", [])
            _upsert(c, meta)
            seen.add(nid)
        return {"ok": True, "indexed": len(seen)}
    finally:
        c.close()


def llm_generate(prompt, system_prompt=None, max_tokens=1200, timeout=90):
    """一处出口：走 provider 默认路由；异常上抛，由调用方照实回落（⛔ 假装模型可用）。"""
    from core.pa.providers import default_route
    from core.lib.llm_client import LLMClient
    route, _ = default_route()
    return LLMClient().generate(prompt, model=route.get("model"), max_tokens=max_tokens, timeout=timeout,
                                system_prompt=system_prompt or "你是 PA 的第二大脑。只依据给定资料，不编造。")


def _llm_answer(prompt):
    return llm_generate(prompt, system_prompt="你是 PA 的第二大脑问答。只依据给定笔记回答，不编造。",
                        max_tokens=900, timeout=60)


def ask(question, data_dir=None, limit=6, llm_fn=None, notebook_id=None):
    """带出处的第二大脑问答：检索 note → 模型总结 → 返回 citations。

    notebook_id 非 None 时只检索该笔记本（⛔ 越界引用别本）。
    """
    q = (question or "").strip()
    if not q:
        raise NoteError("问题为空")
    rows = list_notes(q=q, data_dir=data_dir, limit=max(1, min(int(limit or 6), 10)),
                      notebook_id=notebook_id)
    if not rows:
        return {"answer": "没有找到相关笔记。先记一笔，或换一个关键词。", "citations": [], "notes": []}
    citations, chunks = [], []
    for n in rows:
        full = get(n["id"], data_dir=data_dir)
        body = (full.get("body") or "").strip()
        snippet = body[:1200]
        citations.append({"id": n["id"], "title": n.get("title", ""), "snippet": snippet[:240],
                          "updated": n.get("updated", ""), "notebook_id": n.get("notebook_id", "")})
        chunks.append("[note:%s] %s\n%s" % (n["id"], n.get("title", ""), snippet))
    prompt = ("你是 PA 的第二大脑。只根据下面笔记回答，不要编造；"
              "每条结论后用 [note:<id>] 标出处；没有依据就说没有依据。\n\n"
              "问题：%s\n\n笔记：\n%s\n" % (q, "\n\n---\n\n".join(chunks)))
    answer = ""
    try:
        answer = (llm_fn or _llm_answer)(prompt)
    except Exception as e:
        answer = ""
        _why = type(e).__name__
    answer = (answer or "").strip()
    if not answer or answer.startswith("模型不可用") or "LLM_UNAVAILABLE" in answer:
        answer = "找到 %d 条相关笔记（模型暂不可用，先给摘录）：\n\n" % len(rows)
        answer += "\n\n".join("- [note:%s] %s：%s" % (c["id"], c["title"], c["snippet"]) for c in citations)
    return {"answer": answer[:6000], "citations": citations,
            "notes": [{"id": c["id"], "title": c["title"], "updated": c["updated"]} for c in citations]}
