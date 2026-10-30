# -*- coding: utf-8 -*-
u"""legacy_verify/adapters/precision_inject_v9 之测（只读 · 语义反例）."""

import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from legacy_verify.adapters import precision_inject_v9 as A


class _FakePI:
    def __init__(self, vault="", cfg=None, files=None, resolver=None):
        self._vault = vault
        self._cfg = cfg or {}
        self._KNOWLEDGE_FILES = files or {}
        self._resolver = resolver

    def _vault_path(self):
        return self._vault

    def _obsidian_cfg(self):
        return self._cfg

    def _resolve_knowledge_path(self, key):
        return self._resolver(key) if self._resolver else None


# ---------- C7：顶层段 ＋ 静态四名 ＋ 反斜杠归一 ----------

def test_scan_excluded_legacy_semantics():
    assert A.legacy_scan_excluded("_冷区/x.md") is True
    assert A.legacy_scan_excluded("_垃圾箱/P/d.md") is True
    assert A.legacy_scan_excluded(".obsidian/x.md") is True
    assert A.legacy_scan_excluded("Templates/t.md") is True
    assert A.legacy_scan_excluded("工作区/SOPs/SOPs/a.md") is False
    assert A.legacy_scan_excluded("dsh/a.md") is False


def test_scan_excluded_top_level_only_not_any_segment():
    u"""PD A1：嵌套同名 ⛔ 多排（现役 _rel_excluded 任一段 → True 之漂移）。"""
    assert A.legacy_scan_excluded("工作区/_冷区/x.md") is False
    assert A.legacy_scan_excluded("工作区/" + chr(92) + "_冷区/x.md") is False


def test_scan_excluded_normalizes_backslash():
    u"""PD A2：Windows 反斜杠旧经归一 ⇒ top 命中；⛔ 原样喂现役 _rel_excluded。"""
    assert A.legacy_scan_excluded("Templates" + chr(92) + "t.md") is True


def test_scan_excluded_cases_all_match():
    cases = A.scan_excluded_cases()
    assert len(cases) == len(A.LEGACY_SCAN_CASES)
    assert all(v["ok"] for v in cases.values()), cases
    assert A.all_scan_cases_ok() is True


# ---------- C6：vault 根 / sops_dir ----------

def test_vault_root_or_none_empty_is_none(monkeypatch):
    monkeypatch.setattr(A, "_pi", lambda: _FakePI(vault=""))
    assert A.vault_root_or_none() is None
    monkeypatch.setattr(A, "_pi", lambda: _FakePI(vault="."))
    assert A.vault_root_or_none() is None
    monkeypatch.setattr(A, "_pi", lambda: _FakePI(vault=str(ROOT)))
    assert A.vault_root_or_none() == ROOT


def test_sops_dir_default_and_configured(monkeypatch):
    monkeypatch.setattr(A, "_pi", lambda: _FakePI(cfg={}))
    assert A.sops_dir() == "SOPs"
    monkeypatch.setattr(A, "_pi",
                        lambda: _FakePI(cfg={"sops_dir": "工作区/SOPs/SOPs"}))
    assert A.sops_dir() == "工作区/SOPs/SOPs"


# ---------- C9：base_url（真源 5102 · env 可覆） ----------

def test_base_url_env_override(monkeypatch):
    monkeypatch.setenv("PA_VERIFY_BASE", "http://127.0.0.1:9999/")
    assert A.base_url() == "http://127.0.0.1:9999"


def test_base_url_true_source_port_5102(monkeypatch):
    monkeypatch.delenv("PA_VERIFY_BASE", raising=False)
    url = A.base_url()
    assert urllib.parse.urlsplit(url).port == A.LEGACY_BASE_PORT == 5102, url


# ---------- C10：blocked（⛔ 空表假绿） ----------

def test_legacy_walk_ok_and_errors_is_list(tmp_path, monkeypatch):
    (tmp_path / "a.md").write_text("a", encoding="utf-8")
    monkeypatch.setattr(A, "_pi", lambda: _FakePI(vault=str(tmp_path)))
    rep = A.legacy_walk()
    assert rep["walker"] == "legacy_v5_tolerant" and rep["state"] == "ok"
    assert rep["file_count"] >= 1 and "a.md" in rep["files"]
    errs = A.legacy_walk_errors()
    assert isinstance(errs, list), u"C10 留痕面须为 list"
    assert errs == []


def test_legacy_walk_unset_vault_is_explicit(monkeypatch):
    monkeypatch.setattr(A, "_pi", lambda: _FakePI(vault=""))
    rep = A.legacy_walk()
    assert rep["state"] == "unset" and rep["file_count"] == 0
    assert rep["manifest_note"] == "vault 未接"


# ---------- C5：schema 兼容 sandbox_rel / rel ----------

def test_knowledge_files_sandbox_rel_schema_ok(tmp_path, monkeypatch):
    p = tmp_path / "doc.md"
    p.write_text("x", encoding="utf-8")
    fake = _FakePI(vault=str(tmp_path), cfg={"enabled": True},
                   files={"K": {"file": "K.md", "sandbox_rel": "doc.md"}},
                   resolver=lambda key: p)
    monkeypatch.setattr(A, "_pi", lambda: fake)
    got = A.knowledge_files_ok()
    assert got["K"]["exists"] is True
    assert "sandbox_rel" in got["K"]["schema"]
    assert "rel" not in got["K"]["schema"]
    assert A.all_knowledge_ok() is True


def test_knowledge_files_rel_fallback_ok(tmp_path, monkeypatch):
    p = tmp_path / "docs" / "rel.md"
    p.parent.mkdir(parents=True)
    p.write_text("x", encoding="utf-8")
    fake = _FakePI(vault=str(tmp_path), cfg={"enabled": True},
                   files={"K2": {"file": "K2.md", "rel": "docs/rel.md"}},
                   resolver=lambda key: None)
    monkeypatch.setattr(A, "_pi", lambda: fake)
    got = A.knowledge_files_ok()
    assert got["K2"]["exists"] is True, got
    assert Path(got["K2"]["path"]) == p


def test_knowledge_files_missing_is_false(tmp_path, monkeypatch):
    fake = _FakePI(vault=str(tmp_path), cfg={"enabled": True},
                   files={"K": {"file": "K.md", "sandbox_rel": "nope.md"}},
                   resolver=lambda key: None)
    monkeypatch.setattr(A, "_pi", lambda: fake)
    got = A.knowledge_files_ok()
    assert got["K"]["exists"] is False
    assert A.all_knowledge_ok() is False


# ---------- legacy_walker：保已读 / 错误入册 / 清单补面 ----------

from legacy_verify.adapters import legacy_walker as LW  # noqa: E402


def test_walker_normal_tree_and_skip(tmp_path):
    (tmp_path / "a.md").write_text("a", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.md").write_text("b", encoding="utf-8")
    skip_dir = tmp_path / "_冷区"
    skip_dir.mkdir()
    (skip_dir / "c.md").write_text("c", encoding="utf-8")
    rep = LW.walk(tmp_path)
    assert rep["state"] == "ok"
    assert rep["files"] == ["a.md", "sub/b.md"], rep["files"]
    assert rep["error_count"] == 0
    assert LW.last_walk_errors() == []


def test_walker_scandir_oserror_preserves_siblings(tmp_path, monkeypatch):
    (tmp_path / "a.md").write_text("a", encoding="utf-8")
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "x.md").write_text("x", encoding="utf-8")
    (tmp_path / "b.md").write_text("b", encoding="utf-8")
    real = LW.os.scandir

    def _fake(path):
        if str(path).replace(chr(92), "/").endswith("/bad"):
            raise PermissionError("被拒（注入）")
        return real(path)

    monkeypatch.setattr(LW.os, "scandir", _fake)
    rep = LW.walk(tmp_path)
    assert "a.md" in rep["files"] and "b.md" in rep["files"], rep["files"]
    assert "bad/x.md" not in rep["files"]
    assert rep["error_count"] == 1, rep
    errs = LW.last_walk_errors()
    assert isinstance(errs, list) and errs[0]["error"] == "PermissionError", errs
    assert "bad" in errs[0]["path"]


def test_walker_mid_iter_oserror_keeps_already_read(tmp_path, monkeypatch):
    d = tmp_path / "d"
    d.mkdir()
    (d / "x.md").write_text("x", encoding="utf-8")
    real = LW.os.scandir

    class _Boom:
        def __init__(self, first):
            self.first = first
            self.n = 0

        def __iter__(self):
            return self

        def __next__(self):
            if self.n == 0:
                self.n = 1
                return self.first
            raise OSError("EIO（注入）")

        def close(self):
            pass

    def _fake(path):
        it = real(path)
        if str(path).replace(chr(92), "/").endswith("/d"):
            return _Boom(next(it))
        return it

    monkeypatch.setattr(LW.os, "scandir", _fake)
    rep = LW.walk(tmp_path)
    assert "d/x.md" in rep["files"], u"已读之件 ⛔ 整棵丢：%r" % (rep["files"],)
    assert rep["error_count"] == 1, rep


def test_walker_manifest_supplements_missing_read(tmp_path, monkeypatch):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "x.md").write_text("x", encoding="utf-8")
    manifest = tmp_path / "manifest.txt"
    manifest.write_text("docs/x.md" + chr(10) + "nope.md" + chr(10), encoding="utf-8")
    real = LW.os.scandir

    def _fake(path):
        if str(path).replace(chr(92), "/").endswith("/docs"):
            raise PermissionError("被拒（注入）")
        return real(path)

    monkeypatch.setattr(LW.os, "scandir", _fake)
    rep = LW.walk(tmp_path, manifest=manifest)
    assert "docs/x.md" in rep["files"], rep
    assert rep["supplemented"] == ["docs/x.md"], rep
    assert "nope.md" not in rep["files"]
    assert rep["error_count"] == 1


def test_walker_manifest_missing_is_optional_not_error(tmp_path):
    (tmp_path / "a.md").write_text("a", encoding="utf-8")
    rep = LW.walk(tmp_path, manifest=tmp_path / "no_manifest.txt")
    assert rep["error_count"] == 0, rep
    assert rep["supplemented"] == [] and rep["manifest_note"] == ""


# ---------- 边界：⛔ 建端 · ⛔ 产品 import legacy_verify ----------

def test_legacy_layer_has_no_endpoint_registration():
    q = (ROOT / "legacy_verify" / "run_quick.py").read_text(encoding="utf-8")
    a = (ROOT / "legacy_verify" / "adapters" / "precision_inject_v9.py").read_text(encoding="utf-8")
    for src in (q, a):
        assert "add_url_rule" not in src
        assert "Blueprint(" not in src
        assert "/v9/pa/verify" not in src


def test_product_does_not_import_legacy_verify():
    core = ROOT / "core"
    bad = []
    for p in core.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "legacy_verify" in txt:
            bad.append(p.relative_to(ROOT).as_posix())
    assert bad == [], u"产品 ⛔ import legacy_verify：%s" % bad
