# -*- coding: utf-8 -*-
"""PPT 批注落库（2026-09-13 批67，C2 纯后端）。

背景：批注此前只落浏览器 localStorage（键 pa_ppt_comments_v1），刷新在、换机器/清缓存就没了，
且后端完全不知道批注存在（发布清单无法引用）。

设计取舍：
  - 沿用既有 jsonl 留痕风格（与 events.jsonl / live_accumulation.jsonl 一致），不引入 DB；
  - 追加写、不覆盖（批注是事件流，不是状态），重复提交同一条也不去重（保留原始意图）；
  - base_dir 由调用方传入（路由传 _data_dir()），**存储层不自己猜路径** ——
    这样 live/sandbox 各自落到自己的目录，与本项目「后端决定落盘位置」的一贯做法一致。

读方（当场定，体检项 2）：
  ① 前端加载批注时读（GET /v9/pa/ppt/comments）—— **属 C3 批次，本批尚未落地**；
  ② 发布清单/审计回溯时读同一 jsonl。
  ⚠ 本批只落了后端；在 C3 把前端接上之前，GET 端点的**自动读方数量为 0**，
     即处于体检项 2 留痕侧三态的第①态「写了没人读」。此状态已在交付文件中如实标注。
"""
import json
import os
import time

FILENAME = "ppt_comments.jsonl"


def _path(base_dir):
    d = os.path.join(base_dir, "pa") if os.path.basename(str(base_dir).rstrip("/")) != "pa" else str(base_dir)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, FILENAME)


def add_comment(base_dir, deck, page_index, comment, ts=None):
    """追加一条批注；返回落盘的记录（含 at）。参数非法时抛 ValueError（不静默丢）。"""
    if not str(comment or "").strip():
        raise ValueError("comment 不能为空")
    try:
        page = int(page_index)
    except (TypeError, ValueError):
        raise ValueError("page_index 必须是整数")
    rec = {
        "at": ts or time.strftime("%Y-%m-%dT%H:%M:%S"),
        "deck": str(deck or ""),
        "page_index": page,
        "comment": str(comment).strip(),
    }
    p = _path(base_dir)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def list_comments(base_dir, deck=None, limit=500):
    """读回批注；文件不存在返回空列表（不报错）。坏行跳过并计数，不整体失败（体检项 31）。"""
    p = _path(base_dir)
    if not os.path.exists(p):
        return []
    out, bad = [], 0
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                bad += 1
                continue
            if deck and rec.get("deck") != deck:
                continue
            out.append(rec)
    return out[-limit:]
