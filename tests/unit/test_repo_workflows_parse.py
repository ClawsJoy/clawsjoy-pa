# -*- coding: utf-8 -*-
u"""仓内 workflows 之齿（pm_1606 §二.4 ⒞ ／ ⒟ · 随下批之实质改）。

⒞ **解齿**：凡 `.github/workflows/*.yml` ⇒ 以 YAML 之器解之。
   由（pm_1587 §一）：`ci_windows.yml:45` 之 value 为 **plain scalar 而含 `: `**
     ⇒ YAML 解为「映射分隔」⇒ GitHub 报 `Invalid workflow file: …#L45` ∧
     `jobs total_count = 0`（**未及跑而败** —— ⛔ 测试之红）。
   ⚠ `PyYAML` ⛔ 在 ⇒ **显报「⛔ 得判」**（⛔ 静绿 · 承「凡断须以器取」）。
⒟ **支名之齿**：`on.push.branches`（若有）须含**本仓之默认支**。
   由（pm_1587 §一.4）：`ci.yml:5` 曾写 `[main]` ⟷ 本仓默认支 ＝ `master`
     ⇒ **恒 ⛔ 跑**（唯手触发 ／ PR 可跑）—— 同族之病。

器取：`python -X utf8 -B -m pytest tests/unit/test_repo_workflows_parse.py -q`
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WF_DIR = ROOT / ".github" / "workflows"
WF = sorted(str(p) for p in WF_DIR.glob("*.yml")) if WF_DIR.is_dir() else []
_PARAM = WF or ["<无>"]


def _yaml():
    u"""YAML 之器；⛔ 在 ⇒ `None`（**须显报「⛔ 得判」** · ⛔ 静绿）。"""
    try:
        import yaml
    except Exception:
        return None
    return yaml


def _need_yaml():
    y = _yaml()
    if y is None:
        pytest.fail(
            u"⛔ 得判：PyYAML ⛔ 在（器 ⛔ 得 ⇒ ⛔ 判绿 · 承「凡断须以器取」）；"
            u"`requirements.txt:7` 有 `pyyaml` ⇒ 装依即可硬判")
    return y


def _on(doc):
    u"""`on:` 之值 —— ⚠ YAML 1.1 把裸 `on` 解为**布尔 `True`**（PyYAML 之实 · 必两取）。"""
    if not isinstance(doc, dict):
        return None
    for k in ("on", True):
        if k in doc:
            return doc[k]
    return None


def _default_branch(repo):
    u"""本仓之默认支（⛔ 联网）—— 逐层回落（⛔ 得判 ⇒ 空返）。

    ⚠ 层（要）：CI 之 `actions/checkout` 为 **detached HEAD** ∧ 常 ⛔ `refs/remotes/origin/HEAD`
      ⇒ 唯取 `refs/remotes/origin/<master|main>` 方稳（⛔ 则本齿于 CI 假红 —— 同「闸不可自证」之族）。
    """
    def _sh(*args):
        return subprocess.run(["git", "-C", str(repo)] + list(args), capture_output=True)

    def _txt(r):
        return (r.stdout or b"").decode("utf-8", "replace").strip()

    r = _sh("symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if r.returncode == 0 and _txt(r):
        return _txt(r).split("/", 1)[-1]
    r = _sh("for-each-ref", "--format=%(refname:short)", "refs/remotes/origin/")
    if r.returncode == 0:
        hit = sorted({x.split("/", 1)[-1] for x in _txt(r).splitlines()
                      if "/" in x} & {"master", "main"})
        if len(hit) == 1:
            return hit[0]
    r = _sh("branch", "--list", "master", "main")
    if r.returncode == 0:
        names = sorted({x.strip().lstrip("*").strip() for x in _txt(r).splitlines() if x.strip()})
        names = [n for n in names if n]
        if len(names) == 1:
            return names[0]
    r = _sh("symbolic-ref", "--short", "HEAD")
    if r.returncode == 0 and _txt(r):
        return _txt(r)
    return None


def _branch_complaint(doc, db):
    u"""`on.push.branches` ⛔ 含默认支 ⇒ 返人话（否则 `None`）。"""
    if not db:
        return u"⛔ 得判：本仓之默认支 ⛔ 取（⛔ 判绿 · ⛔ 以 `master` 之字面代）"
    on = _on(doc)
    branches = None
    if isinstance(on, dict):
        push = on.get("push")
        if isinstance(push, dict):
            branches = push.get("branches")
    if branches is None:
        return None   # 该 workflow ⛔ 限支（如 `on: pull_request` 之空值）⇒ 无事
    if isinstance(branches, str):
        branches = [branches]
    if db in branches:
        return None
    return (u"`on.push.branches` = %r ⛔ 含本仓之默认支 %r ⇒ 该 workflow 于默认支之推上"
            u"**恒 ⛔ 触**（唯手触发 ／ PR 可跑）" % (branches, db))


def test_workflows_dir_is_not_empty():
    u"""前置：须有 `.github/workflows/*.yml`（⛔ 有 ⇒ 齿空转 ⇒ 假绿）。"""
    assert WF, u"⛔ 见 %s 之 *.yml ⇒ 本齿之面不在（⛔ 静默之绿）" % WF_DIR


@pytest.mark.parametrize("path", _PARAM)
def test_workflow_yaml_parses(path):
    u"""⒞ 解齿：以 YAML 之器解之（`PyYAML` ⛔ 在 ⇒ 显报「⛔ 得判」）。"""
    yaml = _need_yaml()
    txt = Path(path).read_text(encoding="utf-8")
    try:
        doc = yaml.safe_load(txt)
    except Exception as e:
        pytest.fail(u"⛔ YAML ⛔ 合（%s: %s）：%s" % (type(e).__name__, e, path))
    assert isinstance(doc, dict), u"⛔ 形 ⛔ 是（映射之顶）：%s ⇒ %r" % (path, type(doc))


@pytest.mark.parametrize("path", _PARAM)
def test_push_branches_include_default_branch(path):
    u"""⒟ 支名之齿：`on.push.branches`（若有）须含本仓之默认支（⛔ 则恒 ⛔ 跑）。"""
    yaml = _need_yaml()
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    why = _branch_complaint(doc, _default_branch(ROOT))
    assert why is None, u"%s：%s" % (path, why)


def test_yaml_tooth_detects_the_real_drift():
    u"""反控（pm_1587 §一.4 之实事）：`run:` 之 plain scalar 含 `: ` ⇒ 本齿**必逮**。"""
    yaml = _need_yaml()
    drift = (u"name: CI\n"
             u"on:\n"
             u"  push:\n"
             u"    branches: [master]\n"
             u"jobs:\n"
             u"  a:\n"
             u"    steps:\n"
             u"      - run: echo \"NOT covered on CI: real Ollama\"\n")
    with pytest.raises(Exception):
        yaml.safe_load(drift)


def test_branch_tooth_detects_the_real_drift():
    u"""反控（pm_1587 §一.4 之实事）：`branches: [main]` ⟷ 默认支 `master` ⇒ 本齿**必逮**。"""
    doc = {"on": {"push": {"branches": ["main"]}}}
    assert _branch_complaint(doc, "master") is not None
    # 正控：`[master]` ⇒ 无事（⛔ 假红）
    assert _branch_complaint({"on": {"push": {"branches": ["master"]}}}, "master") is None
    # 正控：不限支（无 `branches`）⇒ 无事
    assert _branch_complaint({"on": {"pull_request": None}}, "master") is None
    # 反控：默认支 ⛔ 得判 ⇒ 必报（⛔ 判绿）
    assert _branch_complaint({}, None) is not None