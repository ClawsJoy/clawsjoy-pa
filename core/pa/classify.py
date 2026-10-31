# -*- coding: utf-8 -*-
"""第二大脑 · 笔记自动整理（摘要＋关键词＋归类建议）。"""
from __future__ import annotations

import json
import re
import threading
import time

from core.pa import notes as N
from core.pa import notebooks as NB

MAX_TEXT = 3000
STOP = set("""的 了 和 是 在 我 有 就 不 人 都 一 一个 上 也 很 到 说 要 去 你 会 着 没有 看 好 自己 这
我们 你们 他们 这个 那个 这些 那些 可以 需要 因为 所以 但是 如果 然后 以及 还有 就是 不是 什么
进行 相关 方面 问题 情况 内容 资料 来源 笔记 客户 已经 通过 目前 主要 一种 一些""".split())
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_\-]{2,}|[\u4e00-\u9fff]+")


def _clean(s, n=160):
    s = re.sub(r"[#*>\u005b\u005d\u0028\u0029]", " ", str(s or ""))
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n]


def _fallback_summary(title, body):
    text = _clean(body, 4000)
    if not text:
        return _clean(title, 120) or "（空笔记）"
    parts = re.split(r"(?<=[。！？!?；;])", text)
    out = ""
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if len(out) + len(p) > 150 and out:
            break
        out += p
        if len(out) >= 60:
            break
    return _clean(out or text, 180)


def _tokens(text):
    out = []
    for m in TOKEN_RE.finditer(str(text or "")):
        s = m.group(0)
        if re.match(r"^[A-Za-z]", s):
            out.append(s.lower())
            continue
        if len(s) <= 4:
            out.append(s)
            continue
        for n in (2, 3, 4):
            for i in range(0, len(s) - n + 1):
                out.append(s[i:i + n])
    return out


def fallback_keywords(title, body, tags=None, limit=8):
    out = []
    for t in (tags or []):
        t = str(t).strip()
        if t and t not in STOP and t not in out:
            out.append(t)
    text = (str(title or "") + "。" + str(body or "")).strip()
    try:
        import jieba.analyse as ja
        for w in ja.extract_tags(text, topK=max(limit * 2, 12)):
            w = str(w).strip()
            if len(w) >= 2 and not w.isdigit() and w not in STOP and w not in out:
                out.append(w)
            if len(out) >= limit:
                break
        return out[:limit]
    except Exception:
        pass
    scores = {}
    for tok in _tokens(str(title or "") * 3 + " " + str(body or "")):
        if tok in STOP or len(tok) < 2:
            continue
        scores[tok] = scores.get(tok, 0) + 1
    rows = sorted(scores.items(), key=lambda kv: (-kv[1], -len(kv[0])))
    for k, _ in rows:
        if any(k in x or x in k for x in out):
            continue
        out.append(k)
        if len(out) >= limit:
            break
    return out


def _parse_json(text):
    s = str(text or "").strip()
    fence = chr(96) * 3
    s = re.sub("^" + fence + "(?:json)?|" + fence + "$", "", s, flags=re.M).strip()
    m = re.search(r"\{.*\}", s, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except Exception:
        return None
    if not isinstance(d, dict):
        return None
    summary = _clean(d.get("summary"), 300)
    kws = d.get("keywords")
    if isinstance(kws, str):
        kws = [x.strip() for x in re.split(r"[,，、;；\s]+", kws) if x.strip()]
    if not isinstance(kws, list):
        kws = []
    kws = [str(x).strip()[:40] for x in kws if str(x).strip()][:12]
    topic = _clean(d.get("topic"), 40)
    return {"summary": summary, "keywords": kws, "topic": topic}


def classify_note(nid, data_dir=None, llm_fn=None):
    note = N.get(nid, data_dir=data_dir)
    title = note.get("title", "")
    body = (note.get("body") or "")[:MAX_TEXT]
    tags = note.get("tags") or []
    try:
        existing = N.distinct_categories(data_dir=data_dir)[:12]
    except Exception:
        existing = []
    prompt = ("只输出一行 JSON（不要 markdown、不要解释）："
              '{"summary":"1-2 句摘要","keywords":["5-8 个关键词"],"topic":"一个归类名"}\n'
              "要求：摘要与关键词只依据来源；关键词用名词短语；归类名不超过 12 字。\n"
              "已有标签（优先复用，别为同义概念另造新名）：%s\n"
              "标题：%s\n标签：%s\n正文：\n%s"
              % ("、".join(existing) or "（暂无）", title, "、".join(tags), body))
    model_ok, why, parsed = False, "", None
    try:
        raw = (llm_fn or N.llm_generate)(prompt)
        parsed = _parse_json(raw)
        model_ok = bool(parsed and parsed.get("summary"))
        if not model_ok:
            why = "模型未按 JSON 返回"
    except Exception as e:
        why = type(e).__name__
    if not model_ok:
        parsed = {"summary": _fallback_summary(title, body),
                  "keywords": fallback_keywords(title, body, tags),
                  "topic": _clean(title, 16) or "未分类"}
    N.update(nid, data_dir=data_dir, summary=parsed["summary"], keywords=parsed["keywords"],
             category=parsed["topic"], category_auto=True)
    return {"id": nid, "title": title, "summary": parsed["summary"],
            "keywords": parsed["keywords"], "topic": parsed["topic"],
            "model_ok": model_ok, "why": why}


def _score_notebook(nb, keywords, summary, topic):
    blob = "%s %s" % (nb.get("title", ""), nb.get("description", ""))
    toks = set(_tokens(blob))
    score = 0
    for k in keywords:
        if k in blob:
            score += 3
        elif k in toks:
            score += 1
    for t in _tokens(summary)[:20]:
        if t in toks:
            score += 0.2
    return score


def suggest_notebook(result, data_dir=None):
    nbs = NB.list_notebooks(data_dir=data_dir)
    best, best_score = None, 0.0
    for nb in nbs:
        sc = _score_notebook(nb, result.get("keywords") or [], result.get("summary") or "",
                             result.get("topic") or "")
        if sc > best_score:
            best, best_score = nb, sc
    if best and best_score >= 3:
        return {"notebook_id": best["id"], "title": best.get("title", ""), "score": best_score,
                "new": False}
    return {"notebook_id": "", "title": result.get("topic") or "未分类", "score": best_score,
            "new": True}


def classify_many(ids, data_dir=None, limit=8, llm_fn=None):
    out = []
    for nid in list(ids or [])[:max(1, int(limit or 8))]:
        try:
            r = classify_note(nid, data_dir=data_dir, llm_fn=llm_fn)
        except Exception as e:
            r = {"id": nid, "error": "%s: %s" % (type(e).__name__, str(e)[:120])}
        if "error" not in r:
            r["suggestion"] = suggest_notebook(r, data_dir=data_dir)
        out.append(r)
    return out


# ---------- 一键整理全部：后台任务 + 自动标签聚类 ----------

_JOB_LOCK = threading.Lock()
_JOB = {"running": False, "total": 0, "done": 0, "current": "", "error": "",
        "started": "", "finished": "", "categories": {}, "succeeded": 0, "failed": 0}


def _snapshot():
    with _JOB_LOCK:
        return dict(_JOB)


def organize_status():
    return _snapshot()


def _jaccard(a, b):
    A, B = set(a or []), set(b or [])
    if not A or not B:
        return 0.0
    return len(A & B) / float(len(A | B))


def _cluster(results):
    """按关键词重叠把笔记聚成标签；单个笔记的簇最后并入「其他」。"""
    clusters = []
    for r in results:
        if r.get("error"):
            continue
        kws = list(r.get("keywords") or [])
        topic = str(r.get("topic") or "").strip()
        best, best_score = None, 0.0
        for c in clusters:
            sc = _jaccard(kws, c["keywords"])
            if topic and c["name"] and (topic in c["name"] or c["name"] in topic):
                sc += 0.25
            if sc > best_score:
                best, best_score = c, sc
        if best is not None and best_score >= 0.18:
            best["items"].append(r)
            best["keywords"] = list(set(best["keywords"]) | set(kws))[:40]
            best["topics"][topic] = best["topics"].get(topic, 0) + 1
        else:
            clusters.append({"name": topic or (kws[0] if kws else "其他"),
                             "keywords": kws, "items": [r],
                             "topics": {topic: 1} if topic else {}})
    for c in clusters:
        if c["topics"]:
            c["name"] = max(c["topics"].items(), key=lambda kv: kv[1])[0]
        c["name"] = _clean(c["name"], 24) or "其他"
    # 单篇簇并入「其他」，保证标签下有多篇关联文件
    final = {}
    for c in clusters:
        name = c["name"] if len(c["items"]) >= 2 else "其他"
        final.setdefault(name, {"name": name, "items": []})
        final[name]["items"].extend(c["items"])
    return list(final.values())


def _apply_categories(results, data_dir=None):
    groups = _cluster(results)
    counts = {}
    for g in groups:
        name = g["name"]
        for r in g["items"]:
            try:
                N.update(r["id"], data_dir=data_dir, category=name, category_auto=True)
                r["category"] = name
            except Exception:
                r["category"] = ""
        counts[name] = len(g["items"])
    return counts


def organize_sync(ids, data_dir=None, llm_fn=None):
    """同步版（测试/CLI）：逐条整理后再聚类写回 category。"""
    results = []
    for nid in list(ids or []):
        try:
            results.append(classify_note(nid, data_dir=data_dir, llm_fn=llm_fn))
        except Exception as e:
            results.append({"id": nid, "error": "%s: %s" % (type(e).__name__, str(e)[:120])})
    counts = _apply_categories(results, data_dir=data_dir)
    return {"results": results, "categories": counts}


def _run_all(ids, data_dir, llm_fn):
    results, ok, failed = [], 0, 0
    try:
        for i, nid in enumerate(ids):
            with _JOB_LOCK:
                _JOB["current"] = nid
            try:
                r = classify_note(nid, data_dir=data_dir, llm_fn=llm_fn)
                results.append(r)
                ok += 1
            except Exception as e:
                failed += 1
                results.append({"id": nid, "error": "%s: %s" % (type(e).__name__, str(e)[:120])})
            with _JOB_LOCK:
                _JOB["done"] = i + 1
                _JOB["succeeded"] = ok
                _JOB["failed"] = failed
        counts = _apply_categories(results, data_dir=data_dir)
        with _JOB_LOCK:
            _JOB["categories"] = counts
            _JOB["running"] = False
            _JOB["current"] = ""
            _JOB["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    except Exception as e:
        with _JOB_LOCK:
            _JOB["running"] = False
            _JOB["error"] = "%s: %s" % (type(e).__name__, str(e)[:200])
            _JOB["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")


def organize_all(data_dir=None, llm_fn=None, only_uncategorized=False):
    """启动一键整理全部；已有一个在跑时直接返回其状态。"""
    global _JOB
    with _JOB_LOCK:
        if _JOB.get("running"):
            return dict(_JOB)
        rows = N.list_notes(data_dir=data_dir, limit=200)
        if only_uncategorized:
            ids = [x["id"] for x in rows if not (x.get("category") or "").strip()]
        else:
            ids = [x["id"] for x in rows]
        _JOB = {"running": bool(ids), "total": len(ids), "done": 0, "current": "",
                "error": "", "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "finished": "",
                "categories": {}, "succeeded": 0, "failed": 0,
                "only_uncategorized": bool(only_uncategorized)}
    if ids:
        threading.Thread(target=_run_all, args=(ids, data_dir, llm_fn), daemon=True).start()
    return _snapshot()

