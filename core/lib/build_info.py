# -*- coding: utf-8 -*-
u"""version.json -- 装根版本元数据之「一处定形」（承 pm_1628 §二.2 令二 · 技术总监席 f202f89 · 2026-10-07）。

病（PM 一手 · pm_1628 §二.2）：注册表 `DisplayVersion` 唯静态 `1.0`（`installer_post.py:42`）
  ⟷ 仓内版号另有真源（`core/lib/version.py:__version__` ≡ `pyproject.toml[project].version`）
  ⇒ 二源漂 ⇒ 「用户装的是哪一版」**⛔ 可答**（承「⛔ 静默 · 显真读数」）。

形（唯五键 · **一处定形**）＝ `FIELDS`：`version ／ commit ／ tree ／ built_at ／ channel`。
  写方 ＝ `scripts/win_pa/installer_post.py`（装时落 · 唯标准库 —— 净机之 runtime ⛔ 引 core）；
  读者 ＝ 本模块（端 ／ 齿）；写读二方之「形」由 `tests/unit/test_win_pa_version_1629.py` **以器核**（⛔ 人记）。

⚠ 本模块**⛔ 回落 · ⛔ 静默**：未见 ／ 不可读 ⇒ 照实报 `available=False` ＋ 其由
  （承「真读数 ⛔ ＝ 原始异常」；旧包装前无此件 ⇒ 明书「待甲-P0 之增量写入」）。

以何形调用（判通 ／ 断须附）：
  python -X utf8 -B -m pytest tests/unit/test_win_pa_version_1629.py -q
"""
from __future__ import annotations

import io
import json
import os

FILENAME = u"version.json"

#: 逐键（**一处定形**）—— 写方 ⛔ 另定此表；齿 `test_win_pa_version_1629` 以器核二方一致。
FIELDS = (u"version", u"commit", u"tree", u"built_at", u"channel")


def root_dir():
    u"""装根 ／ 仓根（**一处定形**）：本档 ＝ `<根>/core/lib/build_info.py` ⇒ 上溯三。
    ⚠ 同式于仓内与装根（装根亦为 `core/lib/build_info.py`）⇒ 一处出 · ⛔ 硬编本机径。
    """
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def path(root=None):
    u"""装根 `version.json` 之径（一处出）。"""
    return os.path.join(root or root_dir(), FILENAME)


def read(root=None):
    u"""读装根 `version.json` ⇒ `(dict | None, note)`；未见 ／ 坏 ⇒ `(None, 因)`（⛔ 静默）。"""
    p = path(root)
    if not os.path.isfile(p):
        return None, u"未见 %s（装前 ∨ 旧包 ⇒ 待甲-P0 之增量写入）" % FILENAME
    try:
        with io.open(p, encoding=u"utf-8-sig") as fh:
            d = json.loads(fh.read())
    except Exception as e:                                    # noqa: BLE001 — 照实报因
        return None, u"%s 读取败：%s: %s" % (FILENAME, type(e).__name__, e)
    if not isinstance(d, dict):
        return None, u"%s 非对象（%s）" % (FILENAME, type(d).__name__)
    return d, u""


def report(root=None):
    u"""端之报体（**一处出**）：有 ⇒ `available=True` ＋ 逐键（`FIELDS`）；无 ⇒ 照实报因。"""
    d, note = read(root)
    out = {"available": d is not None, "path": path(root)}
    if d is None:
        out["note"] = note
        for k in FIELDS:
            out[k] = None
        return out
    for k in FIELDS:
        out[k] = d.get(k)
    missing = [k for k in FIELDS if d.get(k) in (None, u"")]
    if missing:
        out["note"] = u"缺键：%s（照实报 · ⛔ 充）" % u"、".join(missing)
    else:
        out["note"] = note
    extra = sorted(k for k in d if k not in FIELDS)
    if extra:
        out["extra_keys"] = extra
    return out
