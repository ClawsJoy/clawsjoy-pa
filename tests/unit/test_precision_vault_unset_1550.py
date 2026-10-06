# -*- coding: utf-8 -*-
"""pm_1550 §二 齿：库根「未接（选目录）」之守（写 ∧ 读 · 一处定形）。

病（PM 一手 · 真跑）：未接 ⇒ `_vault_path()` 返 `""` ⇒ `Path("")` ≡ `Path(".")`
  ⇒ ⒜ 写面 `mkdir` 于 **CWD**（用户数据落程序目录）∧ ⒝ 读面 `os.walk(CWD)`（**假有据**）。
契约（pm_1550 §二.5）：
  正控（未接 ⇒ 写面 ⛔ 造 ⛔ 写 ∧ 读面 `0` 件 ＋ 显形）
  反控（**旧形** ⇒ 必造 ∧ 必拾 ＝ 证病在）
  他控（已接 ⇒ 逐字不变）
  穷扫（`_vault_guard` 之消费点数 ＝ 登记数 ∧ `_vault_path()` 之消费点唯 1 处派生）
"""
import ast
import re
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, ".")
ROOT = Path(__file__).resolve().parents[2]
PI_REL = "core/gateway/precision_inject.py"

# ⭐ 穷扫登记（消费点数 ＝ 11 · 一处定形）：改本模块之守 ⇒ 此表与本文件同步改（齿即拦）。
EXPECTED_GUARD_FACES = (
    u"读面：_scan_vault",
    u"写面：_reviews_write_dir",
    u"读面：_reviews_read_dirs",
    u"写面：write_task_review",
    u"写面：write_vault_note",
    u"写面：append_pitfall",
    u"读面：sync_knowledge_to_sandbox",
    u"读面：_resolve_knowledge_path",
    u"读面：read_knowledge_file(Reviews/)",
    u"读面：list_knowledge_files",
    u"写面：update_sop",
)
WRITE_RE = re.compile(r"write_text_lf\(|\.write_text\(|write_bytes\(|_os_note\.open")
CFG = {
    "enabled": True,
    "reviews_dir": "Reviews",
    "sops_dir": "SOPs",
    "pitfalls_dir": "Pitfalls",
    "write_on_complete": True,
    "append_pitfalls": True,
    "pitfalls_file": u"避坑清单.md",
}


@pytest.fixture
def _unset(monkeypatch, tmp_path):
    """库根**未接**之机：`vault_root()` ⇒ None（⛔ env ∧ ⛔ 配置 ∧ ⛔ 内置 kb）。"""
    import core.gateway.precision_inject as pi

    monkeypatch.setattr(pi, "vault_root", lambda: None)
    monkeypatch.setattr(pi, "_obsidian_cfg", lambda: dict(CFG))
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    (cwd / u"证据_标记.md").write_text(
        "---" + chr(10) + "tags: [" + u"证据" + "]" + chr(10) + "---" + chr(10) + u"# 证据_标记" + chr(10),
        encoding="utf-8",
    )
    monkeypatch.chdir(cwd)
    return cwd


# ---------- 正控 ----------
def test_unset_write_faces_do_not_touch_cwd(_unset, capsys):
    u"""未接 ⇒ 写面 ⛔ 造目录 ⛔ 写件（⛔ 落 CWD）＋ 须**显形**。"""
    import core.gateway.precision_inject as pi

    cwd = _unset
    before = sorted(p.name for p in cwd.iterdir())
    assert pi.write_task_review(u"u", u"s", u"t1", u"标题", u"## 做了什么" + chr(10) + u"正文内容足够长的一段") is None
    assert pi.write_vault_note(u"标题", u"内容足够长足够长足够长的一段") is None
    assert pi.append_pitfall(u"一个足够长的坑记述内容") is None
    assert pi.update_sop(u"平台发布工作流", u"小节", u"正文足够长的一段") is None
    assert pi._reviews_write_dir() is None
    after = sorted(p.name for p in cwd.iterdir())
    assert after == before, u"未接 ⇒ 写面 ⛔ 造目录 ⛔ 写件（今 CWD: %s）" % after
    assert not (cwd / u"聊天区").exists(), u"⛔ 落 CWD（旧病之产物）"
    out = capsys.readouterr().out
    assert u"未接（选目录）" in out, u"未接须显形（⛔ 静默吞）: %r" % out


def test_unset_read_faces_return_zero(_unset, capsys):
    u"""未接 ⇒ 读面 `0` 件（⛔ 把 CWD 当库根 ⇒ 假有据）＋ 须**显形**。"""
    import core.gateway.precision_inject as pi

    assert pi._scan_vault() == []
    assert pi.search_vault(u"证据_标记", limit=5) == []
    assert pi.list_knowledge_files() == []
    assert pi.sync_knowledge_to_sandbox() == []
    assert pi._reviews_read_dirs() == []
    assert pi._resolve_knowledge_path(u"Reviews/任意") is None
    assert pi.read_knowledge_file(u"Reviews/2026-01-01-x") is None
    assert pi.read_knowledge_file(u"微信公众号/有.md") is None
    out = capsys.readouterr().out
    assert u"未接（选目录）" in out, u"未接须显形（⛔ 静默吞）: %r" % out


# ---------- 反控（证病在） ----------
def test_old_form_would_pollute_cwd(_unset):
    u"""旧形 `Path(_vault_path())` ⇒ `Path('.')` ⇒ 必造目录于 CWD ∧ 必拾 CWD 之件。"""
    import core.gateway.precision_inject as pi

    cwd = _unset
    assert pi._vault_path() == "", u"未接之形 ＝ 空串（旧法之根因）"
    old_root = Path(pi._vault_path())
    assert old_root == Path("."), u"`Path('')` ≡ `Path('.')`"
    (old_root / u"聊天区" / u"复盘").mkdir(parents=True, exist_ok=True)
    (old_root / u"聊天区" / u"复盘" / u"x.md").write_text(u"# x", encoding="utf-8")
    assert (cwd / u"聊天区" / u"复盘" / u"x.md").exists(), u"旧形 ⇒ 必造于 CWD"
    picked = list(pi._walk_vault_md(old_root, set(pi._exclude_dirs())))
    assert any(p.name == u"证据_标记.md" for p in picked), u"旧读形 ⇒ 必拾 CWD 之件（假有据）"


# ---------- 他控（已接 ⇒ 逐字不变） ----------
def test_connected_behaviour_unchanged(monkeypatch, tmp_path):
    import core.gateway.precision_inject as pi

    vault = tmp_path / "vault"
    for sub in ("Reviews", "SOPs", "Pitfalls"):
        (vault / sub).mkdir(parents=True, exist_ok=True)
    (vault / "SOPs" / "a.md").write_text(u"# A" + chr(10) + u"番茄推广流程", encoding="utf-8")
    monkeypatch.setattr(pi, "_vault_path", lambda: str(vault))
    monkeypatch.setattr(pi, "_obsidian_cfg", lambda: dict(CFG))
    assert pi._vault_root_or_none() == vault
    assert [n["name"] for n in pi._scan_vault()] == ["a"]
    w = pi.write_task_review(u"u", u"s", u"t1", u"标题", u"## 做了什么" + chr(10) + u"正文内容足够长的一段")
    assert w is not None and Path(w).parent == vault / "Reviews" and Path(w).exists()


# ---------- 穷扫 ＋ 登记 ----------
def test_guard_faces_single_and_exhaustive():
    u"""消费点数 ＝ 登记数；且 `_vault_path()` 之调用唯 1 处（`_vault_root_or_none` 之派生）。"""
    src = (ROOT / PI_REL).read_text(encoding="utf-8")
    faces = tuple(re.findall(r'_vault_guard\("([^"]+)"\)', src))
    assert sorted(faces) == sorted(EXPECTED_GUARD_FACES), (
        u"守之面集 ≠ 登记（漏守 ∨ 多守）：%s" % sorted(set(faces) ^ set(EXPECTED_GUARD_FACES)))
    calls = [n for n in ast.walk(ast.parse(src))
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "_vault_path"]
    assert len(calls) == 1, u"`_vault_path()` 之消费点须唯 1（派生处）· 今 %d" % len(calls)


def test_no_other_module_consumes_vault_path():
    u"""全仓（core/tools/scripts）⛔ 别有 `_vault_path` 之引进者（旧 API ⇒ CWD 漏）。"""
    bad = []
    for d in ("core", "tools", "scripts"):
        base = ROOT / d
        if not base.is_dir():
            continue
        for p in base.rglob("*.py"):
            if "__pycache__" in p.parts:
                continue
            t = p.read_text(encoding="utf-8", errors="replace")
            if "precision_inject import _vault_path" in t or "pi._vault_path" in t:
                bad.append(p.relative_to(ROOT).as_posix())
    assert not bad, u"须走 `_vault_guard`（⛔ 以 CWD 为库根）：%s" % bad


def test_registry_evidence_points_at_real_writes():
    u"""登记表不许说谎：`vault_write_faces.yaml` 之 evidence 行**须真为写调用**（旧行号已腐）。"""
    reg = yaml.safe_load((ROOT / "config" / "v9" / "vault_write_faces.yaml").read_text(encoding="utf-8"))
    lines = (ROOT / PI_REL).read_text(encoding="utf-8").split(chr(10))
    n = 0
    for w in reg["writers"]:
        if w["module"] != PI_REL:
            continue
        for f in w["faces"]:
            for e in f["evidence"]:
                path, ln = e.rsplit(":", 1)
                assert path == PI_REL
                assert WRITE_RE.search(lines[int(ln) - 1]), u"evidence 未指真写调用: %s ⇒ %r" % (e, lines[int(ln) - 1].strip())
                n += 1
    assert n == 4, u"precision_inject 之写面 evidence 数须为 4（今 %d）" % n