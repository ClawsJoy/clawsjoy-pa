# -*- coding: utf-8 -*-
u"""pm_1569 §五 之齿：`_ASK_CACHE` ／ `_LINE_CACHE` 之**淘汰**（满 ⇒ 逐最旧 · ⛔ 弃新）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_cache_evict_1569.py -q

病（pm_1569 §五 · 我一手读）：二缓存之存唯 `if len(cache) < cap`（全件 ⛔ 见 pop ／ clear ／ del）
  ⇒ 一旦满 ⇒ **新键永不入** ⇒ 复问恒 miss（且键含印 ⇒ 死键只增不减 ⇒ 满之速 ＝ 面之变率）
  ⇒ 「治了等于没治」之潜口（承 pm_1549 §一 之旨）。

判据：
  ⒜ 正控：注满 ⇒ 再注新键 ⇒ **新键在** ∧ **最旧之键出**（真 LRU · ⛔ 弃新）。
  ⒝ 命中提新：`_lru_put` 遇既有键 ⇒ 提为最新（否则降为 FIFO · ⛔ LRU）。
  ⒞ 反控（证病在）：旧形 `if len(cache) < cap: cache[k]=v` ⇒ 满后新键**⛔ 入**。
  ⒟ 二路皆过 `_lru_put`（`_ASK_CACHE` ∧ `_LINE_CACHE`）· 上限入常量（⛔ 字面）。
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tests.pa_src import gr_src  # noqa: E402

from core.pa import gateway_routes as GR  # noqa: E402


# ---------- ⒜ 正控：满 ⇒ 逐最旧 · 保新 ----------

def test_lru_put_evicts_oldest_keeps_new():
    c = {}
    for i in range(4):
        GR._lru_put(c, i, i, 4)
    assert len(c) == 4, c
    GR._lru_put(c, 99, 99, 4)
    assert 99 in c, u"满 ⇒ **新键须入**（⛔ 弃新 —— 本齿之的）"
    assert 0 not in c, u"最旧之键须出（0）"
    assert len(c) == 4, c


# ---------- ⒝ 命中提新（真 LRU · ⛔ FIFO）----------

def test_lru_put_hit_promotes():
    c = {}
    for i in range(3):
        GR._lru_put(c, i, i, 3)
    GR._lru_put(c, 0, 0, 3)          # 命中 ⇒ 提为最新
    GR._lru_put(c, 7, 7, 3)          # 满 ⇒ 逐「最旧」＝ 1（⛔ 0）
    assert 7 in c and 0 in c, c
    assert 1 not in c, u"提新后最旧 ＝ 1（⛔ 0）⇒ 真 LRU（⛔ FIFO）"


# ---------- ⒞ 反控：旧形之病（证病在）----------

def test_old_form_rejects_new_when_full():
    u"""反控：旧形 `if len(cache) < cap: cache[k]=v` ⇒ 满后新键**⛔ 入**（本齿钉病）。"""
    c = {}
    cap = 3
    for i in range(3):
        if len(c) < cap:
            c[i] = i
    if len(c) < cap:                 # ⛔ 旧形：满 ⇒ 竟「弃新」
        c[99] = 99
    assert 99 not in c, u"旧形之病：满 ⇒ 新键永不入（本齿钉之）"
    assert len(c) == cap


# ---------- ⒟ 二路皆过 _lru_put · 上限入常量 ----------

def test_both_caches_use_lru_put_source():
    src = gr_src()
    assert "_lru_put(_ASK_CACHE" in src, u"`_ASK_CACHE` 须过 `_lru_put`"
    assert "_lru_put(_LINE_CACHE" in src, u"`_LINE_CACHE` 须过 `_lru_put`（同族 · 一并）"
    assert "if len(_ASK_CACHE) < _ASK_CACHE_MAX" not in src, u"旧形须绝（⛔ 满则新键永不入）"
    assert "if len(_LINE_CACHE) < 3000" not in src, u"旧形须绝（`_LINE_CACHE`）"
    assert "_LINE_CACHE_MAX = 3000" in src, u"上限须入常量（⛔ 字面）"