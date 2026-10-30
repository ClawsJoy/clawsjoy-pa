"""T125：core/pa/legacy_verify_face 产品化 7+2 之测.

判据：
  · run_legacy_7_2() 真跑 ⇒ face='legacy_7_2'、pass=7/fail=0/na=2、9 条齐；
  · C2 读活端 5102 恰 6 全等（dev14 / 端点不可用 ⇒ FAIL）；C10 本包容错 walker 真 PASS；
  · C12/C13 N/A（⛔ 9/9）；⛔ import 顶层 legacy_verify ／ ⛔ WSL ／ ⛔ 建路由。
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa.legacy_verify_face import face as F  # noqa: E402
from core.pa.legacy_verify_face import run_legacy_7_2  # noqa: E402
from core.pa.legacy_verify_face import walker as W  # noqa: E402

IDS = [cid for cid, _fn in F.CHECKS]
PASS_IDS = ("C1", "C2", "C5", "C6", "C7", "C10", "C9")
NA_IDS = ("C12", "C13")
PKG = ROOT / "core" / "pa" / "legacy_verify_face"


def _res(cid, status):
    return {"id": cid, "status": status, "evidence": {}}


def _plan():
    p = {cid: "PASS" for cid in PASS_IDS}
    p.update({cid: "N/A" for cid in NA_IDS})
    return p


# ---------- 真跑（验收 7/0/2） ----------


# 集成测：需真实 vault/活端 5102；CI 门禁以 -m "not integration" 排除（本地默认仍跑）。
@pytest.mark.integration
def test_real_run_returns_7_2():
    doc = run_legacy_7_2()
    assert doc["face"] == "legacy_7_2"
    assert (doc["pass"], doc["fail"], doc["na"]) == (7, 0, 2), doc
    assert [r["id"] for r in doc["results"]] == IDS
    st = {r["id"]: r["status"] for r in doc["results"]}
    assert st["C2"] == "PASS" and st["C10"] == "PASS"
    assert st["C12"] == "N/A" and st["C13"] == "N/A"
    assert doc["pass"] != 9, "7+2 ⛔ 9/9"


def test_injected_profile_7_2():
    checks = {cid: (lambda c=cid, s=_plan()[cid]: _res(c, s)) for cid in IDS}
    doc = F.run_legacy_7_2(checks=checks)
    assert (doc["pass"], doc["fail"], doc["na"]) == (7, 0, 2), doc


# ---------- C2：活端 6 全等 ----------


def _live(ids, count=None):
    return {"ok": True, "count": len(ids) if count is None else count, "rows": [{"id": i} for i in ids]}


def _defaults():
    return F._roster_default_ids()


def test_c2_live_six_exact_pass(monkeypatch):
    monkeypatch.setattr(F, "_fetch_live_roster", lambda url=F.LIVE_ROSTER_URL, timeout=5: (_live(_defaults()), ""))
    got = F.check_c2()
    assert got["status"] == "PASS", got
    assert got["evidence"]["url"] == "http://127.0.0.1:5102/v9/pa/roster"
    assert got["evidence"]["count"] == 6 and got["evidence"]["exact_eq"] is True


def test_c2_dev14_fail(monkeypatch):
    ids = _defaults() + [f"dev_{i}" for i in range(8)]
    monkeypatch.setattr(F, "_fetch_live_roster", lambda url=F.LIVE_ROSTER_URL, timeout=5: (_live(ids), ""))
    got = F.check_c2()
    assert got["status"] == "FAIL" and got["evidence"]["count"] == 14
    assert got["evidence"]["exact_eq"] is False


def test_c2_unavailable_fail(monkeypatch):
    monkeypatch.setattr(
        F, "_fetch_live_roster", lambda url=F.LIVE_ROSTER_URL, timeout=5: (None, f"活端不可用：URLError（{url}）")
    )
    got = F.check_c2()
    assert got["status"] == "FAIL"
    assert "活端不可用" in got["evidence"]["error"]


def test_c2_subset_not_equal_fail(monkeypatch):
    ids = _defaults()[:5] + ["extra"]
    monkeypatch.setattr(F, "_fetch_live_roster", lambda url=F.LIVE_ROSTER_URL, timeout=5: (_live(ids), ""))
    assert F.check_c2()["status"] == "FAIL"


# ---------- C7 / C5 / C6 / C9 ----------


def test_c7_cases_pass():
    got = F.check_c7()
    assert got["status"] == "PASS" and not got["evidence"]["mismatch"], got
    cases = got["evidence"]["cases"]
    assert cases["工作区/_冷区/x.md"] == {"expected": False, "actual": False, "ok": True}
    assert cases["Templates" + chr(92) + "t.md"]["actual"] is True


def test_c5_sandbox_rel_schema(monkeypatch, tmp_path):
    p = tmp_path / "a.md"
    p.write_text("x", encoding="utf-8")
    monkeypatch.setattr(
        F,
        "_knowledge_files_ok",
        lambda: {"K": {"schema": ["sandbox_rel"], "path": str(p), "exists": True, "resolve_error": ""}},
    )
    got = F.check_c5()
    assert got["status"] == "PASS" and got["evidence"]["schema_compatible"] is True


def test_c6_vault_sops(monkeypatch, tmp_path):
    root = tmp_path / "vault"
    (root / "工作区" / "SOPs" / "SOPs").mkdir(parents=True)
    monkeypatch.setattr(F, "_vault_root_or_none", lambda: root)
    monkeypatch.setattr(F, "_sops_dir", lambda: "工作区/SOPs/SOPs")
    got = F.check_c6()
    assert got["status"] == "PASS" and got["evidence"]["exists"] is True


def test_c6_unset_vault_fail(monkeypatch):
    monkeypatch.setattr(F, "_vault_root_or_none", lambda: None)
    monkeypatch.setattr(F, "_sops_dir", lambda: "SOPs")
    assert F.check_c6()["status"] == "FAIL"


def test_c9_fail_on_5002(monkeypatch):
    monkeypatch.setattr(F, "_base_url", lambda: "http://127.0.0.1:5002")
    monkeypatch.setattr(F, "_health_status", lambda url, timeout=5: 200)
    monkeypatch.setattr(F, "_newest_source_mtime", lambda: 100)
    monkeypatch.setattr(F, "_proc_started_after", lambda n: (200.0, ""))
    assert F.check_c9()["status"] == "FAIL"


def test_c9_fail_unhealthy(monkeypatch):
    monkeypatch.setattr(F, "_base_url", lambda: "http://127.0.0.1:5102")
    monkeypatch.setattr(F, "_health_status", lambda url, timeout=5: "ERR:URLError")
    monkeypatch.setattr(F, "_newest_source_mtime", lambda: 100)
    monkeypatch.setattr(F, "_proc_started_after", lambda n: (200.0, ""))
    assert F.check_c9()["status"] == "FAIL"


# ---------- C10：本包 walker ----------


def test_c10_uses_own_walker(tmp_path, monkeypatch):
    (tmp_path / "a.md").write_text("a", encoding="utf-8")
    monkeypatch.setattr(F, "_vault_root_or_none", lambda: tmp_path)
    got = F.check_c10()
    assert got["status"] == "PASS", got
    assert got["evidence"]["file_count"] >= 1
    assert got["evidence"]["walker"] == W.WALKER_ID


def test_c10_unset_vault_fail(monkeypatch):
    monkeypatch.setattr(F, "_vault_root_or_none", lambda: None)
    assert F.check_c10()["status"] == "FAIL"


def test_walker_preserves_read_on_mid_iter_oserror(tmp_path, monkeypatch):
    d = tmp_path / "d"
    d.mkdir()
    (d / "x.md").write_text("x", encoding="utf-8")
    real = W.os.scandir

    class _Boom:
        def __init__(self, first):
            self.first, self.n = first, 0

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

    monkeypatch.setattr(W.os, "scandir", _fake)
    rep = W.walk(tmp_path)
    assert "d/x.md" in rep["files"], rep["files"]
    assert rep["error_count"] == 1


def test_walker_scandir_error_keeps_siblings(tmp_path, monkeypatch):
    (tmp_path / "a.md").write_text("a", encoding="utf-8")
    bad = tmp_path / "bad"
    bad.mkdir()
    (tmp_path / "b.md").write_text("b", encoding="utf-8")
    real = W.os.scandir

    def _fake(path):
        if str(path).replace(chr(92), "/").endswith("/bad"):
            raise PermissionError("拒（注入）")
        return real(path)

    monkeypatch.setattr(W.os, "scandir", _fake)
    rep = W.walk(tmp_path)
    assert "a.md" in rep["files"] and "b.md" in rep["files"]
    assert rep["error_count"] == 1


# ---------- C12/C13 N/A ----------


def test_c12_c13_na_not_pass():
    for cid, fn in (("C12", F.check_c12), ("C13", F.check_c13)):
        got = fn()
        assert got["id"] == cid and got["status"] == "N/A"
        assert got["evidence"]["not_pass"] is True


# ---------- 边界：⛔ import 顶层 legacy_verify / ⛔ WSL / ⛔ 建路由 ----------


def _pkg_sources():
    return sorted(PKG.glob("*.py"))


def test_no_top_level_legacy_verify_import():
    import re

    pat = re.compile(r"^\s*(?:from|import)\s+legacy_verify\b", re.MULTILINE)
    for p in _pkg_sources():
        src = p.read_text(encoding="utf-8")
        assert not pat.search(src), (p.name, "⛔ import 顶层 legacy_verify")


def test_no_wsl_reference():
    for p in _pkg_sources():
        assert "wsl" not in p.read_text(encoding="utf-8").lower(), p.name


def test_no_route_registration():
    for p in _pkg_sources():
        src = p.read_text(encoding="utf-8")
        assert "add_url_rule" not in src and "Blueprint(" not in src
        assert "Flask(" not in src


def test_face_shape_keys():
    doc = run_legacy_7_2()
    assert set(doc) == {"face", "pass", "fail", "na", "results"}
    assert all(set(r) == {"id", "status", "evidence"} for r in doc["results"])
