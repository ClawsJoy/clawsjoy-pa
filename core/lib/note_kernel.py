# -*- coding: utf-8 -*-
r"""note 内核 v1 —— 产品知识库（note）之内核（承 pm_1442 §二.2 ／ pm_1444 §二.2 之准）。

【为何立此】净机上「知识库」须**自带一副空骨架**（`<data_root>/kb`）—— ⛔ 指回开发机之
  `D:\Obsidian\...` 字面径（那是「装成已接」· 承 pm_1387 §二.3 之族）。故立此内核：
  **库根之解析 ／ 目录约定 ／ 最小 frontmatter ／ 六面**。

【内核三物 ⛔ 插件化】库根之解析 ／ 目录约定 ／ frontmatter ＝ **内核**（骨架 · 唯此一档）；
  **面 ／ 动作**（六者）走既有 `ToolPlugin` ＋ `_TOOL_REGISTRY`（见 `core/tools/note_kb.py`）。

【库根之序】**唯引** `core.lib.paths.vault_root()`（一处定形 · ⛔ 第二份判据）：
  env `PA_VAULT_DIR` ⇒ 配置 `paths.vault_root` ⇒ 内置 `<data_root>/kb`（**存在方用**）
  ⇒ 末选 `PA_VAULT_LEGACY`（唯组织版开）⇒ 全无 ⇒ `None` ＝「**未接（选目录）**」。

【六面】列 ／ 读 ／ 搜 ／ 新建 ／ 追加 ／ 改小节 —— ⛔ **删**（承 pm_1444 §二.2 之范）。

【态（一处定形 · ⛔ 崩 ／ ⛔ 静默）】
  `ok`            ＝ 有据（读 ／ 写 皆成）
  `未接（选目录）` ＝ 库根 ⛔ 得（⛔ 崩 · ⛔ 以空串 ／ 字面径兜底）
  `空库`           ＝ 库根在 ∧ 件数 0（**空 ≠ 缺** · 承 pm_1444 §二.2）
  `缺件`           ＝ 所引之件 ⛔ 在（∨ 所引之节 ⛔ 在）
  `已存在`         ＝ 新建之名已占（⛔ 覆写）
  `非法相对径`     ＝ 径之形 ⛔ 合（绝对径 ／ `..` ／ NUL ／ 越根）
  `参数⛔合`       ＝ 面 ／ 库名 ／ 件名 ⛔ 合

【写之形】唯 LF ／ UTF-8 ⛔ BOM ／ 目录唯 `os.makedirs`（件之内容唯本内核所造）｜**⛔ 删**。
【本内核 ⛔ 自评「已通过」】。
"""
from __future__ import annotations

import io
import os
import re
import time
from pathlib import Path

NOTE_VERSION = "2026-10-06.1"
ROOT_ENV = "PA_VAULT_DIR"
LEGACY_ENV = "PA_VAULT_LEGACY"

#: 目录约定（**一处定形**）—— 内置库 `<data_root>/kb` 之子目录
#: 与安装器同源自此：`scripts/win_pa/install_win_pa.py::kb_subdirs()` 即引本名（⛔ 二份字面）；
#: 并以测钉之（test_win_pa_install ／ test_note_kernel）。
SUBDIRS = ("notes", "sop", "reviews", "inbox", "drafts", "assets")
#: 最小 frontmatter 之键（序即出之序；余键按名附后）
FM_KEYS = ("title", "created", "updated", "tags")

EXT = ".md"
#: 六面（⛔ 删 —— 承 pm_1444 §二.2）
FACES = ("list", "read", "search", "create", "append", "edit_section")
MAX_NAME_LEN = 80
MAX_LIST = 500
MAX_HITS = 50
READ_CAP = 512 * 1024
#: 件名之形（⛔ 控符 ／ ⛔ 径分隔 ／ ⛔ Windows 之禁字）
NAME_RE = re.compile(r'^[^\x00-\x1f\\/:*?"<>|]+$')
_HEAD = re.compile(r"^([ \t]*)(#{1,6})[ \t]*(.+?)[ \t]*$")

STATE_OK = "ok"
STATE_NO_ROOT = "未接（选目录）"
STATE_EMPTY = "空库"
STATE_MISSING = "缺件"
STATE_EXISTS = "已存在"
STATE_BADREL = "非法相对径"
STATE_BADARG = "参数⛔合"


def now_ts():
    return time.strftime("%Y-%m-%d %H:%M:%S")


# ------------------------------------------------------------------ 库根之解析（唯引真源）
def kroot():
    """库根 ⇒ `Path` ∨ `None`（**未接（选目录）**）。唯引 `paths.vault_root()`（一处定形）。"""
    try:
        from core.lib.paths import vault_root as _vr
        r = _vr()
    except Exception:
        return None
    return Path(str(r)) if r else None


def kroot_src():
    """库根之**真源之述**（逐源探之 · ⛔ 复制其判据 —— 唯问 `paths.py` 自身）。"""
    if (os.environ.get(ROOT_ENV) or "").strip():
        return "env " + ROOT_ENV
    try:
        from core.lib.paths import _config_vault_root as _cv
        if _cv():
            return "配置 paths.vault_root（首启引导 ／ 设置）"
    except Exception:
        pass
    try:
        from core.lib.paths import _builtin_kb as _bk
        if _bk():
            return "内置 <data_root>/kb（存在方用）"
    except Exception:
        pass
    try:
        from core.lib.paths import org_path as _op
        if _op(LEGACY_ENV):
            return "末选 env " + LEGACY_ENV + "（组织版开）"
    except Exception:
        pass
    return STATE_NO_ROOT


def kroot_state():
    """⇒ `(root|None, 真源之述, 态)` —— 态唯 `ok` ∨ `未接（选目录）`。"""
    r = kroot()
    s = kroot_src()
    return r, s, (STATE_OK if r is not None else STATE_NO_ROOT)


# ------------------------------------------------------------------ 目录约定
def subdirs(root=None):
    """六约定目录之逐项（**在 ∨ 缺）** —— ⛔ 立目录（唯报）。"""
    r = kroot() if root is None else Path(root)
    out = []
    for n in SUBDIRS:
        p = (r / n) if r is not None else None
        out.append({"name": n, "path": (str(p) if p is not None else None),
                    "exists": bool(p is not None and p.is_dir())})
    return out


# ------------------------------------------------------------------ 最小 frontmatter
def fm_parse(text):
    """⇒ `(meta: dict, body: str)`。⛔ 首行 `---` 之块 ⇒ `({}, 原文)`。"""
    s = str(text or "")
    if not s.startswith("---"):
        return {}, s
    lines = s.split("\n")
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() in ("---", "..."):
            end = i
            break
    if end is None:
        return {}, s
    meta = {}
    for ln in lines[1:end]:
        if ln.strip().startswith("#") or ":" not in ln:
            continue
        k, v = ln.split(":", 1)
        k = k.strip()
        if k:
            meta[k] = v.strip()
    return meta, "\n".join(lines[end + 1:])


def fm_dump(meta):
    """⇒ frontmatter 块（含末 `\\n`）。`FM_KEYS` 先行 · 余键按名附后 · 空值 ⛔ 出。"""
    lines = ["---"]
    seen = set()
    for k in FM_KEYS + tuple(sorted(meta or {})):
        if k in seen:
            continue
        seen.add(k)
        v = (meta or {}).get(k)
        if v not in (None, ""):
            lines.append("%s: %s" % (k, v))
    lines.append("---")
    return "\n".join(lines) + "\n"


def _tags_str(tags):
    if tags in (None, ""):
        return None
    if isinstance(tags, (list, tuple, set)):
        items = [str(x).strip() for x in tags if str(x).strip()]
    else:
        items = [x.strip() for x in re.split(r"[,，]", str(tags)) if x.strip()]
    return ("[" + ", ".join(items) + "]") if items else None


def make_doc(title, body="", tags=None, created=None, updated=None):
    """⇒ 最小 frontmatter ＋ 正文（LF 终）。"""
    _at = now_ts()
    meta = {"title": title or "", "created": created or _at, "updated": updated or _at}
    _t = _tags_str(tags)
    if _t:
        meta["tags"] = _t
    return fm_dump(meta) + str(body or "")


# ------------------------------------------------------------------ 径之守护
def safe_rel(rel):
    """相对径之守护 ⇒ `(rel|None, 态)`。⛔ 绝对径 ／ ⛔ `..` ／ ⛔ NUL。"""
    raw = str(rel or "").strip()
    if not raw or "\x00" in raw:
        return None, STATE_BADREL
    s = raw.replace("\\", "/")
    # ⚠ 绝对形 **须在去斜杠之前判**（我一手速得：旧版先 `strip("/")` ⇒ `"/abs.md"` 被静默化为相对径）
    if s.startswith("/") or s.startswith("//") or re.match(r"^[A-Za-z]:", s):
        return None, STATE_BADREL
    s = s.strip("/")
    if not s:
        return None, STATE_BADREL
    parts = [p for p in s.split("/") if p not in ("", ".")]
    if not parts or any(p == ".." for p in parts):
        return None, STATE_BADREL
    return "/".join(parts), STATE_OK


def rel_path(rel, root=None):
    """⇒ `(Path|None, 态, 述)` —— 兼守「⛔ 越根」。"""
    r = kroot() if root is None else Path(root)
    if r is None:
        return None, STATE_NO_ROOT, "库根 ⛔ 得（" + kroot_src() + "）"
    _rel, st = safe_rel(rel)
    if st != STATE_OK:
        return None, st, "径之形 ⛔ 合：%r" % (rel,)
    p = r / _rel
    try:
        if os.path.commonpath([os.path.abspath(str(r)), os.path.abspath(str(p))]) != os.path.abspath(str(r)):
            return None, STATE_BADREL, "径越库根：%r" % (rel,)
    except Exception:
        return None, STATE_BADREL, "径 ⛔ 判：%r" % (rel,)
    return p, STATE_OK, _rel


def _safe_name(name):
    s = str(name or "").strip()
    if not s:
        return None
    if s.lower().endswith(EXT):
        base = s[:-len(EXT)]
    else:
        base, s = s, s + EXT
    if not NAME_RE.match(base) or len(base) > MAX_NAME_LEN:
        return None
    return s


def _read_text(p):
    b = Path(p).read_bytes()[:READ_CAP]
    return b.decode("utf-8", "replace")


def _write_text(p, text):
    """唯 LF ／ UTF-8 ⛔ BOM（⛔ 新造件之内容唯本内核所出）。"""
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    with io.open(str(p), "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def _doc_item(p, root):
    try:
        st = os.stat(str(p))
    except Exception:
        return None
    try:
        text = _read_text(p)
    except Exception:
        text = ""
    meta, _body = fm_parse(text)
    rel = str(p.relative_to(root)).replace(os.sep, "/")
    return {"rel": rel, "name": p.name,
            "sub": rel.split("/")[0] if "/" in rel else "",
            "title": meta.get("title") or p.stem,
            "meta": meta, "bytes": st.st_size,
            "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime))}


def _all_notes(root, sub=None):
    out = []
    names = [sub] if sub else list(SUBDIRS)
    for n in names:
        d = root / n
        if not d.is_dir():
            continue
        for dp, dns, fns in os.walk(str(d)):
            dns[:] = [x for x in dns if not x.startswith(".")]
            for fn in sorted(fns):
                if not fn.endswith(EXT) or fn.startswith("."):
                    continue
                out.append(Path(dp) / fn)
    return out


# ------------------------------------------------------------------ 六面
def face_list(root=None, sub=None, limit=MAX_LIST):
    r, src, st = kroot_state() if root is None else (Path(root), "给定", STATE_OK)
    if r is None:
        return {"ok": False, "state": STATE_NO_ROOT, "why": "库根 ⛔ 得（" + src + "）", "items": []}
    if sub and sub not in SUBDIRS:
        return {"ok": False, "state": STATE_BADARG, "why": "库名 ⛔ 合：%r（约定：%s）" % (sub, "/".join(SUBDIRS)), "items": []}
    if not r.is_dir():
        return {"ok": False, "state": STATE_MISSING, "why": "库根 ⛔ 在：%s" % r, "items": []}
    allf = _all_notes(r, sub)
    items = [x for x in (_doc_item(p, r) for p in allf) if x]
    items.sort(key=lambda x: x["mtime"], reverse=True)
    if not items:
        return {"ok": True, "state": STATE_EMPTY, "why": "空库（0 件 · 承「空 ≠ 缺」）",
                "root": str(r), "src": src, "items": []}
    _lim = max(1, min(int(limit or MAX_LIST), MAX_LIST))
    return {"ok": True, "state": STATE_OK, "why": "列 %d 件（库 %s）" % (len(items), src),
            "root": str(r), "src": src, "total": len(items),
            "truncated": len(items) > _lim, "items": items[:_lim]}


def face_read(rel, root=None):
    p, st, why = rel_path(rel, root)
    if p is None:
        return {"ok": False, "state": st, "why": why, "rel": str(rel or "")}
    if not p.is_file():
        return {"ok": False, "state": STATE_MISSING, "why": "件 ⛔ 在：%s" % why, "rel": why}
    text = _read_text(p)
    meta, body = fm_parse(text)
    return {"ok": True, "state": STATE_OK, "why": "读成（%d B）" % len(text.encode("utf-8")),
            "rel": why, "path": str(p), "meta": meta, "body": body, "text": text,
            "truncated": Path(p).stat().st_size > READ_CAP}


def face_search(q, root=None, limit=MAX_HITS):
    s = str(q or "").strip()
    if not s:
        return {"ok": False, "state": STATE_BADARG, "why": "问之形 ⛔ 合（空）", "hits": []}
    r, src, st0 = kroot_state() if root is None else (Path(root), "给定", STATE_OK)
    if r is None:
        return {"ok": False, "state": STATE_NO_ROOT, "why": "库根 ⛔ 得（" + src + "）", "hits": []}
    if not r.is_dir():
        return {"ok": False, "state": STATE_MISSING, "why": "库根 ⛔ 在：%s" % r, "hits": []}
    _q = s.lower()
    hits = []
    for p in _all_notes(r):
        try:
            text = _read_text(p)
        except Exception:
            continue
        _low = text.lower()
        c = _low.count(_q)
        if c <= 0:
            continue
        i = _low.find(_q)
        ln = text[:i].count("\n") + 1
        line = text.split("\n")[ln - 1].strip() if ln - 1 < len(text.split("\n")) else ""
        it = _doc_item(p, r) or {}
        it.update({"count": c, "line": ln, "text": line[:160]})
        hits.append(it)
    hits.sort(key=lambda x: (-x["count"], x["rel"]))
    if not hits:
        return {"ok": True, "state": STATE_EMPTY, "why": "0 中（库 %s）" % src, "root": str(r), "hits": []}
    _lim = max(1, min(int(limit or MAX_HITS), MAX_HITS))
    return {"ok": True, "state": STATE_OK, "why": "%d 件中（库 %s）" % (len(hits), src),
            "root": str(r), "total": len(hits), "truncated": len(hits) > _lim, "hits": hits[:_lim]}


def face_create(sub, name, title=None, body="", tags=None, root=None):
    r, src, st0 = kroot_state() if root is None else (Path(root), "给定", STATE_OK)
    if r is None:
        return {"ok": False, "state": STATE_NO_ROOT, "why": "库根 ⛔ 得（" + src + "）"}
    if sub not in SUBDIRS:
        return {"ok": False, "state": STATE_BADARG, "why": "库名 ⛔ 合：%r（约定：%s）" % (sub, "/".join(SUBDIRS))}
    _n = _safe_name(name)
    if not _n:
        return {"ok": False, "state": STATE_BADARG, "why": "件名 ⛔ 合：%r" % (name,)}
    if not r.is_dir():
        return {"ok": False, "state": STATE_MISSING, "why": "库根 ⛔ 在：%s" % r}
    p = r / sub / _n
    if p.exists():
        return {"ok": False, "state": STATE_EXISTS, "why": "件已在（⛔ 覆写）：%s/%s" % (sub, _n)}
    _write_text(p, make_doc(title or Path(_n).stem, body, tags))
    return {"ok": True, "state": STATE_OK, "why": "新建：%s/%s" % (sub, _n),
            "rel": "%s/%s" % (sub, _n), "path": str(p),
            "doc": _doc_item(p, r)}


def face_append(rel, text, root=None):
    if not str(text or ""):
        return {"ok": False, "state": STATE_BADARG, "why": "所加之文 ⛔ 合（空）"}
    p, st, why = rel_path(rel, root)
    if p is None:
        return {"ok": False, "state": st, "why": why}
    if not p.is_file():
        return {"ok": False, "state": STATE_MISSING, "why": "件 ⛔ 在（追加以外 ⇒ 唯新建）：%s" % why}
    old = _read_text(p)
    meta, body = fm_parse(old)
    _add = str(text)
    new_body = body.rstrip("\n") + ("\n" if body.strip() else "") + _add.rstrip("\n") + "\n"
    meta["updated"] = now_ts()
    _write_text(p, fm_dump(meta) + new_body)
    return {"ok": True, "state": STATE_OK, "why": "追加 %d 字" % len(_add),
            "rel": why, "path": str(p), "bytes_after": os.path.getsize(str(p))}


def face_edit_section(rel, heading, text, root=None):
    """改**小节**：以 `#…<heading>` 之**首中**为界 ⇒ 其体（至下一个同级∨更高级之题 ∨ 文末）换之。"""
    h = str(heading or "").strip()
    if not h or text is None:
        return {"ok": False, "state": STATE_BADARG, "why": "节名 ∨ 新文 ⛔ 合"}
    p, st, why = rel_path(rel, root)
    if p is None:
        return {"ok": False, "state": st, "why": why}
    if not p.is_file():
        return {"ok": False, "state": STATE_MISSING, "why": "件 ⛔ 在：%s" % why}
    meta, body = fm_parse(_read_text(p))
    lines = body.split("\n")
    start, lvl = None, 0
    for i, ln in enumerate(lines):
        m = _HEAD.match(ln)
        if m and m.group(3).strip() == h:
            start, lvl = i, len(m.group(2))
            break
    if start is None:
        return {"ok": False, "state": STATE_MISSING, "why": "节 ⛔ 在：%s" % h, "rel": why}
    end = len(lines)
    for j in range(start + 1, len(lines)):
        m = _HEAD.match(lines[j])
        if m and len(m.group(2)) <= lvl:
            end = j
            break
    new = lines[:start + 1] + str(text).rstrip("\n").split("\n") + ([""] if end < len(lines) else [])
    new_body = "\n".join(new + lines[end:]) if end < len(lines) else "\n".join(new)
    meta["updated"] = now_ts()
    _write_text(p, fm_dump(meta) + new_body.rstrip("\n") + "\n")
    return {"ok": True, "state": STATE_OK, "why": "改节：%s（体 %d 行）" % (h, end - start - 1),
            "rel": why, "path": str(p), "section": h}


def face(action, **kw):
    """面之**唯一入口**（插件之口 · 承 pm_1442 §二.2）。⇒ `{ok, state, why, …}`。"""
    a = str(action or "").strip()
    if a == "list":
        return face_list(root=kw.get("root"), sub=kw.get("sub"), limit=kw.get("limit") or MAX_LIST)
    if a == "read":
        return face_read(kw.get("rel"), root=kw.get("root"))
    if a == "search":
        return face_search(kw.get("q"), root=kw.get("root"), limit=kw.get("limit") or MAX_HITS)
    if a == "create":
        return face_create(kw.get("sub"), kw.get("name"), title=kw.get("title"),
                           body=kw.get("body") or "", tags=kw.get("tags"), root=kw.get("root"))
    if a == "append":
        return face_append(kw.get("rel"), kw.get("text"), root=kw.get("root"))
    if a == "edit_section":
        return face_edit_section(kw.get("rel"), kw.get("heading"), kw.get("text"), root=kw.get("root"))
    return {"ok": False, "state": STATE_BADARG,
            "why": "面 ⛔ 知：%r（六面：%s）" % (a, " ／ ".join(FACES))}
