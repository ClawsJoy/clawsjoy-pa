# -*- coding: utf-8 -*-
u"""kb 栏之测：库名 **自库根之实子目录出**（承 pm_1444 §二.2 ／ pm_1447 §二.2 之准）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_kb_col.py -q

判据：
  ⒜ 库名 ≡ 库根之实子目录（唯目录 · ⛔ 件 · ⛔ 隐 · 名序）
  ⒝ 库根 ⛔ 得 ⇒ 0 行 ∧ 明书「未接」——**反控**：CWD 有子目录亦 ⛔ 列（⛔ 以 `.` 充）
  ⒞ 库根在 ∧ 0 子目录 ⇒ 明书「空库」（**空 ≠ 缺**）
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import env_face as E  # noqa: E402


def test_kb_names_come_from_real_subdirs(tmp_path, monkeypatch):
    u"""⒜：名自实子目录 —— ⛔ 件 · ⛔ 隐 · 名序。"""
    root = tmp_path / "kbroot"
    root.mkdir()
    for d in ("内容工坊", "codex", "zzz-last", "_老板", ".hidden"):
        (root / d).mkdir()
    (root / "note.md").write_text("x", encoding="utf-8")
    monkeypatch.setenv("PA_VAULT_DIR", str(root))
    rows, note, key = E.kb_col()
    assert key == "kb" and note == "", (note, key)
    assert [r["name"] for r in rows] == ["_老板", "codex", "zzz-last", "内容工坊"], rows
    assert all(r["kind"] == "vault_dir" for r in rows)
    assert all(r["state"] for r in rows)


def test_kb_unset_root_is_not_fabricated(tmp_path, monkeypatch):
    u"""⒝：库根 ⛔ 得 ⇒ 0 行 ∧ 「未接」；**反控**：CWD 之子目录 ⛔ 列（⛔ 以组织物名 ／ `.` 充）。"""
    monkeypatch.delenv("PA_VAULT_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "should-not-appear").mkdir()
    rows, note, key = E.kb_col()
    assert rows == [], rows
    assert "未接" in note, note


def test_kb_empty_root_reports_empty_not_missing(tmp_path, monkeypatch):
    u"""⒞：库根在 ∧ 0 子目录 ⇒ 「空库」（空 ≠ 缺）。"""
    root = tmp_path / "kbroot"
    root.mkdir()
    monkeypatch.setenv("PA_VAULT_DIR", str(root))
    rows, note, key = E.kb_col()
    assert rows == [], rows
    assert "空库" in note, note