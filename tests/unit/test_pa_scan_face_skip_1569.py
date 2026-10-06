# -*- coding: utf-8 -*-
u"""pm_1569 §四 之齿：扫面之剔（目录名通配 `ptmp*` ＋ 件名前缀族）＋ `searched` 之**唯一件数** ＋ 角色分列。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_scan_face_skip_1569.py -q

病（pm_1569 §四 · 我一手器取）：
  ⒈ 旧剔唯 `e.name in PA_FACES_SKIP`（精确名）⇒ `--basetemp` 落根面之新名（`ptmp1564` …）**漏剔**
     ⇒ 测试 fixture 入检索面 ⇒ 抖印 ∧ 假有据之口。
  ⒉ 旧剔唯目录名 `_auto` ⇒ 根面（工作区 · 递归）之「我方报告 ／ 派件集」同族件**漏剔**（95 件中 32 件）。
  ⒊ `searched` 计「扫次」⇒ 同件二面（如 `_交付` 2 件）**双计** ⇒ 件数说谎。

判据：
  ⒜ 剔之准随族：`_face_skip_name` ＝ 精确名 ∨ 通配形（`ptmp*`）；⛔ 一刀切（知识件须留）。
  ⒝ 前缀族：我方报件（`回执_` ／ `作战单_` ／ `作废_` ／ `发表_` …）剔；知识件（`调研报告` ／ `会议纪要` …）留。
  ⒞ `searched` ＝ **唯一件数** ∧ `searched_roles`（作据 N ／ 只索引 M 分列）∧ `searched_scans`（原扫次）在。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import gateway_routes as GR  # noqa: E402


# ---------- ⒜ 剔之准：目录名（精确 ∨ 通配）----------

def test_face_skip_name_forms():
    assert GR._face_skip_name(u"ptmp1569") is True, u"--basetemp 残渣之形须剔（pm_1569 §四.1）"
    assert GR._face_skip_name(u"ptmp_of_pytest") is True, u"通配形皆剔"
    assert GR._face_skip_name(u"_auto") is True, u"精确名仍剔（⛔ 退）"
    assert GR._face_skip_name(u"知识库") is False, u"知识面 ⛔ 剔（⛔ 一刀切）"


def test_ptmp_dir_pruned(tmp_path):
    d = tmp_path / u"ws"
    (d / u"ptmp1569").mkdir(parents=True)
    (d / u"ptmp1569" / u"fx.md").write_text(u"x\n", encoding="utf-8")
    (d / u"知识.md").write_text(u"y\n", encoding="utf-8")
    names = {p.name for p in GR._face_files(d, (u"*.md",))}
    assert u"fx.md" not in names, u"ptmp* 之残渣须剔（⛔ 入面 ⇒ 抖印）"
    assert u"知识.md" in names, u"知识件须留"


# ---------- ⒝ 剔之准：件名之前缀族（我方报件 ⇒ 剔 · 知识件 ⇒ 留）----------

def test_report_prefix_family_pruned(tmp_path):
    d = tmp_path / u"ws"
    d.mkdir()
    for n in (u"回执_甲.md", u"作战单_乙.md", u"作废_丙.md", u"发表_丁.md", u"派单_戊.md"):
        (d / n).write_text(u"x\n", encoding="utf-8")
    keep = (u"调研报告.md", u"会议纪要.md", u"项目经理_角色卡.md")
    for n in keep:
        (d / n).write_text(u"y\n", encoding="utf-8")
    names = {p.name for p in GR._face_files(d, (u"*.md",))}
    assert names == set(keep), names


# ---------- ⒞ `searched` 唯一件数 ＋ 角色分列 ----------

@pytest.fixture()
def kb(tmp_path):
    d = tmp_path / u"vault"
    (d / u"收件箱").mkdir(parents=True)
    (d / u"收件箱" / u"角色卡.md").write_text(u"老板叫什么名字：唯一之件\n", encoding="utf-8")
    return d


def test_searched_unique_and_roles(monkeypatch, kb):
    monkeypatch.setattr(GR, "vault_root", lambda: kb)
    monkeypatch.setattr(GR, "ws_root", lambda: None)
    monkeypatch.setattr(GR, "org_enabled", lambda: False)
    monkeypatch.setattr(GR, "_LINE_CACHE", {})
    res = GR.pa_kb_search(u"老板叫什么名字", kb, limit=5)
    for k in (u"searched", u"searched_scans", u"searched_roles"):
        assert k in res, k
    assert sum(res[u"searched_roles"].values()) == res[u"searched"], res
    assert res[u"searched"] <= res[u"searched_scans"], res


def test_nokb_early_return_new_keys():
    r = GR.pa_kb_search(u"老板叫什么名字", u"")
    assert r.get(u"no_kb_root") is True
    assert u"searched_scans" in r and u"searched_roles" in r
    assert r[u"searched"] == 0

# ---------- 守一（pm_1571 §二.2）：剔之判**唯对件名** · ⛔ 按路径之任一段 ----------

def test_prefix_family_judges_basename_not_dirname(tmp_path):
    u"""守一：**目录名**合族 ⇒ ⛔ 剔其子树（其内真知识须留）；**件名**合族 ⇒ 剔。"""
    d = tmp_path / u"ws"
    (d / u"方案_知识目录").mkdir(parents=True)
    (d / u"方案_知识目录" / u"真知识.md").write_text(u"x\n", encoding="utf-8")
    (d / u"方案_件.md").write_text(u"y\n", encoding="utf-8")
    names = {p.name for p in GR._face_files(d, (u"*.md",))}
    assert names == {u"真知识.md"}, names


# ---------- 守二（pm_1571 §二.2）：族表一处定形 ∧ **钉其内容** ----------

def test_prefix_family_pinned_single_source():
    u"""守二：新增族 ⇒ 本齿**红** ⇒ 须明书 ＋ 报 PM（⛔ 静增 · 免「面之量」不可回指）。"""
    assert GR.PA_FACES_SKIP_PREFIX == (
        u"作废_", u"回执_", u"作战单_", u"发表_", u"投递_", u"派单_", u"请求_", u"申请_",
        u"讲解_", u"对表_", u"点选表_", u"素材_", u"方案_", u"设计方案_", u"外采集_",
        u"外线风险登记_"), GR.PA_FACES_SKIP_PREFIX
    assert len(GR.PA_FACES_SKIP_PREFIX) == 16, len(GR.PA_FACES_SKIP_PREFIX)
    assert u"ptmp*" in GR.PA_FACES_SKIP
