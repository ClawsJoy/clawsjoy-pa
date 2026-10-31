# -*- coding: utf-8 -*-
"""来源标签（对标 Gemini Notebook 的 label 视图）。

- 标签是分组的壳；空标签也要存在，所以单独存 workspace/labels.json；
- note.category 是来源属于哪个标签（单标签，对应 NotebookLM 的「移至」）；
- 删除标签不删来源，只把来源退回未分类。
"""
from __future__ import annotations

import json
import os
import time

from core.pa.notes import workspace_root
from core.pa import notes as N


def _path(data_dir=None):
    return workspace_root(data_dir) / "labels.json"


def _read(data_dir=None):
    p = _path(data_dir)
    if not p.exists():
        return []
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    labels = d.get("labels") if isinstance(d, dict) else d
    if not isinstance(labels, list):
        return []
    out = []
    for x in labels:
        if isinstance(x, str):
            out.append({"name": x, "created": ""})
        elif isinstance(x, dict) and x.get("name"):
            out.append({"name": str(x["name"])[:60], "created": x.get("created", "")})
    return out


def _write(labels, data_dir=None):
    p = _path(data_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"labels": labels}, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    os.replace(tmp, p)


def list_labels(data_dir=None):
    return _read(data_dir)


def names(data_dir=None):
    return [x["name"] for x in _read(data_dir)]


def add(name, data_dir=None):
    name = str(name or "").strip()[:60]
    if not name:
        raise ValueError("标签名不能为空")
    labels = _read(data_dir)
    for x in labels:
        if x["name"] == name:
            return x
    x = {"name": name, "created": time.strftime("%Y-%m-%dT%H:%M:%S")}
    labels.append(x)
    _write(labels, data_dir=data_dir)
    return x


def rename(old, new, data_dir=None):
    old = str(old or "").strip()
    new = str(new or "").strip()[:60]
    if not old or not new:
        raise ValueError("标签名不能为空")
    labels = _read(data_dir)
    found = False
    for x in labels:
        if x["name"] == old:
            x["name"] = new
            found = True
    if not found:
        labels.append({"name": new, "created": time.strftime("%Y-%m-%dT%H:%M:%S")})
    _write(labels, data_dir=data_dir)
    for n in N.list_notes(data_dir=data_dir, limit=200):
        if str(n.get("category") or "") == old:
            N.update(n["id"], data_dir=data_dir, category=new)
    return {"old": old, "new": new}


def delete(name, data_dir=None):
    name = str(name or "").strip()
    labels = [x for x in _read(data_dir) if x["name"] != name]
    _write(labels, data_dir=data_dir)
    n = 0
    for note in N.list_notes(data_dir=data_dir, limit=200):
        if str(note.get("category") or "") == name:
            N.update(note["id"], data_dir=data_dir, category="", category_auto=False)
            n += 1
    return {"deleted": name, "cleared": n}
