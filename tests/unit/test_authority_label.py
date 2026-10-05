# -*- coding: utf-8 -*-
"""权威度标签门 · 反例门（P0-② 成对改 · 2026-09-28）

病（预红实测）：类别判据 `_reviews_sub_label()` 原先只看 rel **首段**
∈ {`SOPs`, `Pitfalls`}；而真源目录已改为**配置根**
（`obsidian.sops_dir` = `工作区/SOPs/SOPs`、`pitfalls_dir` = `开发区/ComputerUse/Pitfalls`）
⇒ 首段 = `工作区` / `开发区` ⇒ 一律落 `general`（权重 1.0）
⇒ `_VALTYPE_WEIGHT` 的 `SOPs 1.25` / `Pitfalls 1.2` **永不生效**。

判据（每条都能先失败）
  A 新根：配置根下的件 ⇒ 标 `SOPs` / `Pitfalls`（预红）
  B 端到端：真源 rel 经 `_reviews_sub_label` ⇒ 命中 1.25 / 1.2（预红）
  C 配置驱动：换一套配置根 ⇒ 标签跟着走（⛔ 不许写死 `工作区/...`）
  D 回落面：历史形态 `SOPs/`、`Pitfalls/` ＋ 复盘 `聊天区/复盘` ＋ 无关目录 仍按旧口径
"""
import sys

sys.path.insert(0, ".")

import core.gateway.precision_inject as P


def test_A_new_root_sops_and_pitfalls():
    assert P._reviews_sub_label("工作区/SOPs/SOPs/番茄推广SOP.md") == "SOPs"
    assert P._reviews_sub_label("开发区/ComputerUse/Pitfalls/避坑清单.md") == "Pitfalls"


def test_B_end_to_end_weights():
    for key, info in P._KNOWLEDGE_FILES.items():
        rel = P._sops_rel(info["file"])
        lab = P._reviews_sub_label(rel)
        assert lab == "SOPs", "%s rel=%s label=%s" % (key, rel, lab)
        assert P._VALTYPE_WEIGHT.get(lab, 1.0) == 1.25, (key, lab)
    pr = P._pitfalls_rel()
    assert P._reviews_sub_label(pr) == "Pitfalls", pr
    assert P._VALTYPE_WEIGHT.get(P._reviews_sub_label(pr), 1.0) == 1.2


def test_C_config_driven(monkeypatch):
    # 换一套配置根 ⇒ 标签必须跟着走（证明判据读配置，⛔ 非写死工作区/…）
    monkeypatch.setattr(P, "_obsidian_cfg", lambda: {"sops_dir": "X/S", "pitfalls_dir": "Y/P"})
    P._cfg_roots.cache_clear()
    try:
        assert P._reviews_sub_label("X/S/a.md") == "SOPs"
        assert P._reviews_sub_label("Y/P/b.md") == "Pitfalls"
        assert P._reviews_sub_label("工作区/SOPs/SOPs/a.md") == "general"
    finally:
        P._cfg_roots.cache_clear()


def test_D_legacy_and_others_unchanged():
    assert P._reviews_sub_label("SOPs/a.md") == "SOPs"
    assert P._reviews_sub_label("Pitfalls/避坑清单.md") == "Pitfalls"
    assert P._reviews_sub_label("聊天区/复盘/x.md") == "Reviews"
    assert P._reviews_sub_label("Reviews/x.md") == "Reviews"
    assert P._reviews_sub_label("Clippings/a.md") == "general"
    assert P._reviews_sub_label("") == "general"


def test_E_knowledge_rel_map_not_general():
    bad = {rel: P._reviews_sub_label(rel) for rel in P._knowledge_rel_map() if P._reviews_sub_label(rel) == "general"}
    assert bad == {}, "真源 rel 仍落 general: %r" % bad