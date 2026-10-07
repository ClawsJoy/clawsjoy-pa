# -*- coding: utf-8 -*-
r"""pm_1694 §二 令⒜ 之齿 —— 「引 `core` 之齿」须可跑（⛔ 因外部之态而死）。

以何形调用：
  cd D:\clawsjoy_v9
  python -X utf8 -B -m pytest tests/unit/test_vector_center_guard_1694.py -q -p no:cacheprovider

判据：
  G1 反控（昔之病 · 必可复现）：造「异形之仓」（`<cwd>/data/vector_kb/chroma.sqlite3` 为异形 sqlite）
     ⇒ 裸 chromadb 直连 ⇒ **抛**（＝ 沙箱之仓果异 · 否则此齿空转）；而 `import core` ⇒ **rc 0**
     （修前：rc 1 ＋ traceback 载 `'RustBindingsAPI' object has no attribute 'bindings'`）
     ∧ `available is False` ∧ `connect_error` **载原文**（照实 · ⛔ 静默）。
  G2 正控：本仓之 cwd ⇒ `import core` rc 0 ∧ `available is True` ∧ 五集合可数。
  G3 端到端（PM 之实 · 要）：以「异形之仓」之沙箱为 cwd 跑 `tests/unit/test_pa_update_face_1691.py`
     ⇒ **全绿**（修前：其族败 · 「16 败 ／ 2 过」）。
  G4 界：不可用时取集合 ⇒ `RuntimeError` 载原文；`_forget_half_started()` ⇒ chromadb 之登记
     **⛔ 载本径**（否则其 `stop()` 之 `del self.bindings` ＝ PM 报之错）。
"""
from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FACE_TOOTH = ROOT / "tests" / "unit" / "test_pa_update_face_1691.py"
DB_NAME = "chroma.sqlite3"


def _odd_sandbox(base: Path) -> Path:
    """造「异形之仓」之沙箱（cwd）：其 `data/vector_kb/<DB>` 为异形 sqlite。"""
    d = base / "data" / "vector_kb"
    d.mkdir(parents=True, exist_ok=True)
    p = d / DB_NAME
    con = sqlite3.connect(str(p))
    con.execute("create table collections (id text, name text)")
    con.commit()
    con.close()
    return base


def _py(args, cwd):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    return subprocess.run([sys.executable, "-X", "utf8", "-B"] + list(args),
                          capture_output=True, cwd=str(cwd), env=env, timeout=300)


# ---------- G1 反控（昔之病） ----------

def test_G1_odd_db_import_core_still_ok(tmp_path):
    sb = _odd_sandbox(tmp_path)
    r0 = _py(["-c", "import chromadb,sys;chromadb.PersistentClient(path=sys.argv[1])",
              str(sb / "data" / "vector_kb")], cwd=sb)
    assert r0.returncode != 0, u"沙箱之仓须为异形（否则此齿空转）"

    r = _py(["-c",
             "import core;from core.lib.vector_knowledge_center import vector_knowledge_center as v;"
             "print('AV',v.available);print('ERR',v.connect_error)"], cwd=sb)
    out = (r.stdout or b"").decode("utf-8", "replace")
    assert r.returncode == 0, u"import core 须成（修前必 rc 1）：%s" % out[-700:]
    assert "AV False" in out, out[-400:]
    err = [x for x in out.splitlines() if x.startswith("ERR ")]
    assert err and err[0][4:].strip(), u"须照实录其因（⛔ 静默）：%s" % out[-400:]


# ---------- G2 正控 ----------

def test_G2_repo_db_available():
    r = _py(["-c",
             "import core;from core.lib.vector_knowledge_center import vector_knowledge_center as v;"
             "print('AV',v.available);print('N',len(v.collections));print('ERR',v.connect_error)"],
            cwd=ROOT)
    out = (r.stdout or b"").decode("utf-8", "replace")
    assert r.returncode == 0, out[-700:]
    assert "AV True" in out, out[-400:]
    assert "N 5" in out, out[-400:]


# ---------- G3 端到端（PM 之实） ----------

def test_G3_face_tooth_green_in_odd_sandbox(tmp_path):
    if not FACE_TOOTH.is_file():
        pytest.skip(u"面之齿 ⛔ 在（他树 ⇒ 跳）")
    sb = _odd_sandbox(tmp_path)
    r = _py(["-m", "pytest", str(FACE_TOOTH), "-q", "-p", "no:cacheprovider",
             "--basetemp=%s" % (tmp_path / "pt")], cwd=sb)
    out = ((r.stdout or b"") + (r.stderr or b"")).decode("utf-8", "replace")
    assert r.returncode == 0, out[-900:]
    assert "failed" not in out, out[-600:]
    assert "passed" in out, out[-600:]
    assert "bindings" not in out, u"⛔ 复见昔之错（半启之 system 未被抹）"


# ---------- G4 界 ----------

def test_G4_unavailable_collections_raise_with_cause():
    from core.lib.vector_knowledge_center import _UnavailableCollections

    c = _UnavailableCollections("XX: YY")
    with pytest.raises(RuntimeError) as ei:
        c["skills"]
    assert "XX: YY" in str(ei.value)
    with pytest.raises(RuntimeError):
        c.get("skills")
    assert "skills" not in c and list(c.items()) == []


def test_G4b_forget_half_started_drops_registry(tmp_path):
    from chromadb.api.shared_system_client import SharedSystemClient as S

    from core.lib.vector_knowledge_center import VectorKnowledgeCenter

    v = VectorKnowledgeCenter.__new__(VectorKnowledgeCenter)
    v.persist_dir = tmp_path / "kb"
    v.persist_dir.mkdir()
    key = str(v.persist_dir)
    S._identifier_to_system[key] = "SENTINEL"
    S._identifier_to_refcount[key] = 1
    try:
        v._forget_half_started()
        assert key not in S._identifier_to_system, u"半启之 system 须被抹"
        assert key not in S._identifier_to_refcount
    finally:
        S._identifier_to_system.pop(key, None)
        S._identifier_to_refcount.pop(key, None)
