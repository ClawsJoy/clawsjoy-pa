# -*- coding: utf-8 -*-
u"""②v1 拆件后之「取源面」唯一入口（2026-10-27 · 技术总监席 f202f89）。

**为何有本件**：拆件前，「一处定形」之齿皆按**单档**扫 `core/pa/gateway_routes.py`
（见各齿之「源扫本档」注）。拆件后该档只余 160 行兼容门 ⇒ 字面入 9 簇 ＋ 1 公共 ⇒
齿仍真、唯**取源面**失。本件把取源面由「单档」改为「**本包**」，**判意不变**：

  · 计数 ／ 包含类齿 ⇒ `gr_src()`：全包拼接（固定序）
  · 切片类齿       ⇒ `gr_src_file(anchor)`：取含锚之**单件**（保原切片语义）

⛔ 本件不改任何阈值 ／ 断言 ／ 反控；唯提供取源。
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PA_DIR = ROOT / "core" / "pa"


def gr_files():
    u"""固定序：`pa_routes_*.py`（名序）⇒ `gateway_routes.py`（门面 · 居末）。"""
    return sorted(PA_DIR.glob("pa_routes_*.py")) + [PA_DIR / "gateway_routes.py"]


def gr_src():
    u"""本包源之拼接（件间空一行 · 序固定 ⇒ 可复现）。"""
    return "\n".join(p.read_text(encoding="utf-8") for p in gr_files())


def gr_src_file(anchor):
    u"""取**含 `anchor` 之单件**源；多件皆含 ⇒ 取含之最多次者（定义所在），并列 ⇒ 名序首。"""
    hits = []
    for p in gr_files():
        t = p.read_text(encoding="utf-8")
        n = t.count(anchor)
        if n:
            hits.append((n, p.name, t))
    if not hits:
        raise AssertionError(u"取源失败：本包无此锚 —— %r" % (anchor,))
    hits.sort(key=lambda x: (-x[0], x[1]))
    return hits[0][2]
