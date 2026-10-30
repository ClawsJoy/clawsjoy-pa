# -*- coding: utf-8 -*-
u"""PA HarnessPort v1 · H2b：`FileRunLedger`（PA 自有真账 · append-only JSONL ＋ fsync ＋ 回读自验）。

以何形调用：
  python -X utf8 -B -m pytest tests/unit/test_pa_harness_store.py -q

判据（可机检 · 承 task-10 ／ 62_PA_HarnessPort_v1.md）：
  ① 落盘：一行 canonical JSON（字段 ≡ port.RUN_RECORD_FIELDS）＋ `os.fsync` 真调；
  ② 回读：新实例 `reload` 得同 record（receipt_sha16 自验；坏行 ／ 被改 ／ 重复 run_id ⇒ 显错）；
  ③ append-only：既有字节不改 ／ 中途追加为前缀延长；重复 run_id ⛔ 写；
  ④ **单写者**：一文件一实例；他者已改 ⇒ 偏移守卫显错（须 reload 再写）；
  ⑤ H2b：fake dsh run ⇒ 文件 1 行 ⇒ reload 同 record ⇒ 再 run ⇒ 第 2 行；⛔ 真跑模型；
  ⑥ 测试恒用 tmp 路径（⛔ 写仓 ／ ⛔ 写用户数据）。
"""
import ast
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa.harness import port as PORT  # noqa: E402
from core.pa.harness import store as STORE  # noqa: E402
from core.pa.harness.dsh import DshHarness  # noqa: E402
from core.pa.harness.mock import MockHarness  # noqa: E402
from core.pa.harness.store import (  # noqa: E402
    DEFAULT_LEDGER_BASENAME,
    LEDGER_PATH_ENV,
    FileRunLedger,
    FileRunLedgerError,
    LedgerCorrupt,
    default_ledger_path,
)

STORE_SRC = Path(STORE.__file__).resolve()

EXE = "C:/fake/bin/dsh.exe"

FORBIDDEN_IMPORT_ROOTS = {"dsh", "paseo", "obsidian"}


class FakeRunner:
    u"""`_proc.run_hidden` 之替身（记 call · ⛔ 真起进程）。"""

    def __init__(self, rc=0, stdout="", stderr=""):
        self.rc = rc
        self.stdout = stdout
        self.stderr = stderr
        self.calls = []

    def __call__(self, cmd, **kw):
        self.calls.append((list(cmd), dict(kw)))
        return SimpleNamespace(returncode=self.rc, stdout=self.stdout, stderr=self.stderr)


def _record(run_id="pa-run-store0001", session_id="mock-sess-store", **over):
    kw = {
        "run_id": run_id,
        "harness": "mock",
        "session_id": session_id,
        "model": "mock-model",
        "cwd": "D:/ws",
        "started_at": "2026-10-27T10:00:00+08:00",
        "ended_at": "2026-10-27T10:00:01+08:00",
        "status": "ok",
        "cost": PORT.Cost(tokens=3, cny=0.0, turns=1),
        "artifacts": (),
        "harness_meta": {"k": "v"},
    }
    kw.update(over)
    return PORT.RunRecord(**kw)


def _lines(path):
    return path.read_text(encoding="utf-8").splitlines()


def _import_roots(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots, internal = set(), []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
                if alias.name.startswith("core."):
                    internal.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
            if node.module.startswith("core."):
                internal.append(node.module)
    return roots, internal


# ---------- ① 路径 ／ 写盘 ／ fsync ----------

def test_default_path_uses_env_overrides(monkeypatch, tmp_path):
    monkeypatch.delenv(LEDGER_PATH_ENV, raising=False)
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    assert default_ledger_path() == tmp_path / "pa" / DEFAULT_LEDGER_BASENAME, default_ledger_path()

    explicit = tmp_path / "custom" / "runs.jsonl"
    monkeypatch.setenv(LEDGER_PATH_ENV, str(explicit))
    assert default_ledger_path() == explicit


def test_append_writes_one_canonical_jsonl_line_with_fsync(tmp_path, monkeypatch):
    calls = []
    real_fsync = STORE.os.fsync

    def _spy(fd):
        calls.append(fd)
        return real_fsync(fd)

    monkeypatch.setattr(STORE.os, "fsync", _spy)
    path = tmp_path / "runs.jsonl"
    ledger = FileRunLedger(path)
    assert not path.exists(), u"init ⛔ 立空件（首 append 方落）"

    rec = _record()
    ledger.append(rec)
    assert path.exists()
    lines = _lines(path)
    assert len(lines) == 1, lines
    assert lines[0] == PORT.canonical_json(rec.to_dict()), u"行须为 canonical JSON（键序定）"
    assert json.loads(lines[0]) == rec.to_dict()
    assert calls, u"落账须 fsync（⛔ 只停页缓存）"
    assert ledger.count() == 1
    assert ledger.describe()["path"] == str(path)
    assert ledger.describe()["last_receipt_sha16"] == rec.receipt_sha16


def test_parent_dirs_created_lazily_on_append(tmp_path):
    path = tmp_path / "deep" / "nested" / "runs.jsonl"
    ledger = FileRunLedger(path)
    assert not path.parent.exists() and not path.exists()
    ledger.append(_record())
    assert path.exists()


def test_fsync_false_skips_fsync(tmp_path, monkeypatch):
    def _boom(fd):
        raise AssertionError(u"fsync=False 时 ⛔ 调 fsync")

    monkeypatch.setattr(STORE.os, "fsync", _boom)
    path = tmp_path / "runs.jsonl"
    ledger = FileRunLedger(path, fsync=False)
    ledger.append(_record())
    assert len(_lines(path)) == 1
    assert FileRunLedger(path).count() == 1


# ---------- ② 回读 ／ receipt 自验 ／ 坏行显错 ----------

def test_reload_new_instance_reads_same_records(tmp_path):
    path = tmp_path / "runs.jsonl"
    ledger = FileRunLedger(path)
    r1 = _record(run_id="pa-run-a", session_id="s1")
    r2 = _record(run_id="pa-run-b", session_id="s1")
    ledger.append(r1)
    ledger.append(r2)

    fresh = FileRunLedger(path)
    assert fresh.records() == (r1, r2), u"回读须得同 record"
    assert fresh.count() == 2
    assert fresh.get("pa-run-a") == r1
    assert fresh.by_session("s1") == (r1, r2)
    assert fresh.dump() == [r1.to_dict(), r2.to_dict()]
    assert fresh.describe()["offset"] == path.stat().st_size


def test_append_preserves_existing_bytes(tmp_path):
    path = tmp_path / "runs.jsonl"
    ledger = FileRunLedger(path)
    ledger.append(_record(run_id="pa-run-a"))
    mid = path.read_bytes()
    assert json.loads(_lines(path)[0])
    ledger.append(_record(run_id="pa-run-b"))
    assert path.read_bytes().startswith(mid), u"append-only：既有字节 ⛔ 改"
    assert [json.loads(x)["run_id"] for x in _lines(path)] == ["pa-run-a", "pa-run-b"]


def test_duplicate_run_id_rejected_without_write(tmp_path):
    path = tmp_path / "runs.jsonl"
    ledger = FileRunLedger(path)
    rec = _record(run_id="pa-run-dup")
    ledger.append(rec)
    before = path.read_bytes()
    with pytest.raises(ValueError):
        ledger.append(rec)
    assert path.read_bytes() == before, u"重复被拒 ⇒ ⛔ 落半行"
    assert ledger.count() == 1
    assert len(_lines(path)) == 1


def test_append_rejects_non_record(tmp_path):
    ledger = FileRunLedger(tmp_path / "runs.jsonl")
    with pytest.raises(ValueError):
        ledger.append({"run_id": "x"})


def test_receipt_tamper_caught_on_reload(tmp_path):
    path = tmp_path / "runs.jsonl"
    FileRunLedger(path).append(_record(run_id="pa-run-tamper"))

    doc = json.loads(_lines(path)[0])
    doc["receipt_sha16"] = "0" * 16
    path.write_text(json.dumps(doc, ensure_ascii=False) + "\n", encoding="utf-8")
    with pytest.raises(LedgerCorrupt) as ei:
        FileRunLedger(path)
    assert ei.value.line_no == 1
    assert "receipt" in str(ei.value), str(ei.value)


def test_field_tamper_without_new_receipt_is_corrupt(tmp_path):
    path = tmp_path / "runs.jsonl"
    FileRunLedger(path).append(_record(run_id="pa-run-field"))
    doc = json.loads(_lines(path)[0])
    doc["status"] = "failed"
    path.write_text(json.dumps(doc, ensure_ascii=False) + "\n", encoding="utf-8")
    with pytest.raises(LedgerCorrupt):
        FileRunLedger(path)


def test_corrupt_json_and_shape_lines_are_explicit(tmp_path):
    path = tmp_path / "runs.jsonl"
    path.write_text("not-json\n", encoding="utf-8")
    with pytest.raises(LedgerCorrupt) as ei:
        FileRunLedger(path)
    assert ei.value.line_no == 1

    path.write_text("[1, 2]\n", encoding="utf-8")
    with pytest.raises(LedgerCorrupt):
        FileRunLedger(path)

    doc = _record().to_dict()
    path.write_text(PORT.canonical_json(doc) + "\n{}\n", encoding="utf-8")
    with pytest.raises(LedgerCorrupt) as ei2:
        FileRunLedger(path)
    assert ei2.value.line_no == 2

    dirty = dict(doc)
    dirty["session_format"] = "v4"
    path.write_text(PORT.canonical_json(dirty) + "\n", encoding="utf-8")
    with pytest.raises(LedgerCorrupt) as ei3:
        FileRunLedger(path)
    assert "session_format" in str(ei3.value), str(ei3.value)


def test_blank_lines_tolerated(tmp_path):
    path = tmp_path / "runs.jsonl"
    rec = _record()
    path.write_text(PORT.canonical_json(rec.to_dict()) + "\n\n\n", encoding="utf-8")
    ledger = FileRunLedger(path)
    assert ledger.count() == 1 and ledger.get(rec.run_id) == rec


def test_duplicate_run_id_in_file_is_corrupt(tmp_path):
    path = tmp_path / "runs.jsonl"
    rec = _record()
    line = PORT.canonical_json(rec.to_dict()) + "\n"
    path.write_text(line + line, encoding="utf-8")
    with pytest.raises(LedgerCorrupt):
        FileRunLedger(path)


# ---------- ③ 单写者：一文件一实例 ＋ 偏移守卫 ----------

def test_single_writer_offset_guard(tmp_path):
    path = tmp_path / "runs.jsonl"
    a = FileRunLedger(path)
    b = FileRunLedger(path)
    a.append(_record(run_id="pa-run-a"))
    assert len(_lines(path)) == 1

    with pytest.raises(FileRunLedgerError) as ei:
        b.append(_record(run_id="pa-run-b"))
    assert "单写者" in str(ei.value), str(ei.value)
    assert len(_lines(path)) == 1, u"违约 ⛔ 静默续写"

    b.reload()
    b.append(_record(run_id="pa-run-b"))
    assert [json.loads(x)["run_id"] for x in _lines(path)] == ["pa-run-a", "pa-run-b"]

    with pytest.raises(FileRunLedgerError):
        a.append(_record(run_id="pa-run-c"))
    a.reload()
    a.append(_record(run_id="pa-run-c"))
    assert [json.loads(x)["run_id"] for x in _lines(path)] == ["pa-run-a", "pa-run-b", "pa-run-c"]
    assert FileRunLedger(path).count() == 3


# ---------- ④ H2b：fake dsh run → 1 行 → reload 同 record → 再 run → 2 行 ----------

def test_H2b_dsh_fake_run_lands_file_and_reloads(tmp_path):
    path = tmp_path / "runs.jsonl"
    ledger = FileRunLedger(path)
    runner = FakeRunner(rc=0, stdout="ok out\n", stderr="warn\n")
    harness = DshHarness(ledger=ledger, exe=EXE, runner=runner)
    assert isinstance(ledger, PORT.RunLedger), u"DshHarness 须收 port.RunLedger 之注入"

    h1 = harness.run({"task": "task one"})
    lines1 = _lines(path)
    assert len(lines1) == 1, lines1
    doc1 = json.loads(lines1[0])
    assert doc1["run_id"] == h1.run_id and doc1["harness"] == "dsh"
    assert set(doc1) == set(PORT.RUN_RECORD_FIELDS), u"canonical 字段集须同 PA 账 schema"
    assert lines1[0] == PORT.canonical_json(doc1), u"行须为 canonical JSON（键序定）"

    loaded = FileRunLedger(path)
    assert loaded.count() == 1
    rec1 = loaded.get(h1.run_id)
    assert rec1.to_dict() == doc1, u"回读须得同 record（receipt 自验亦过）"
    assert rec1.receipt_sha16 == doc1["receipt_sha16"]

    h2 = harness.run({"task": "task two"})
    lines2 = _lines(path)
    assert len(lines2) == 2, lines2
    loaded2 = FileRunLedger(path)
    assert [r.run_id for r in loaded2.records()] == [h1.run_id, h2.run_id]
    assert json.loads(lines2[1])["run_id"] == h2.run_id

    raw = path.read_text(encoding="utf-8")
    assert "session_format" not in raw, u"DSH 私有格式 ⛔ 入 canonical 行（H4）"
    assert len(runner.calls) == 2
    assert runner.calls[0][0][1:3] == ["--profile", "headless"], runner.calls[0][0]
    assert sorted(p.name for p in tmp_path.iterdir()) == ["runs.jsonl"], u"只写 tmp 之账件"


def test_mock_harness_can_use_file_ledger(tmp_path):
    path = tmp_path / "runs.jsonl"
    harness = MockHarness(ledger=FileRunLedger(path))
    handle = harness.run({"task": "m"})
    assert FileRunLedger(path).get(handle.run_id).run_id == handle.run_id


# ---------- ⑤ 明示 ／ 边界 ----------

def test_describe_and_exceptions(tmp_path):
    path = tmp_path / "runs.jsonl"
    ledger = FileRunLedger(path)
    assert ledger.describe()["runs"] == 0 and ledger.describe()["last_run_id"] == ""
    ledger.append(_record(run_id="pa-run-z"))
    d = ledger.describe()
    assert d["runs"] == 1 and d["last_run_id"] == "pa-run-z"
    assert d["offset"] == path.stat().st_size

    assert issubclass(FileRunLedgerError, PORT.HarnessError)
    assert issubclass(LedgerCorrupt, FileRunLedgerError)
    err = LedgerCorrupt(path, 7, "坏")
    assert err.line_no == 7 and str(path) == err.path and "坏" in str(err)


def test_store_source_boundary_no_forbidden_imports_no_model_no_vault():
    src = STORE_SRC.read_text(encoding="utf-8")
    roots, internal = _import_roots(STORE_SRC)
    assert not (roots & FORBIDDEN_IMPORT_ROOTS), roots & FORBIDDEN_IMPORT_ROOTS
    assert roots - set(sys.stdlib_module_names) - {"core"} == set(), u"⛔ 第三方 import：%s" % roots
    assert set(internal) <= {"core.pa.harness.port"}, internal
    assert "subprocess" not in src and "socket" not in src, u"真账 ⛔ 起进程 ／ 触网"
    assert "os.fsync" in src and "O_APPEND" in src, u"落盘须 append ＋ fsync"
    assert DEFAULT_LEDGER_BASENAME == "harness_runs.jsonl"
    assert LEDGER_PATH_ENV == "PA_HARNESS_LEDGER_PATH"
    assert "data/v9/pa" in src
    assert "vault_root(" not in src and "PA_VAULT_DIR" not in src, u"真账 ⛔ 触 vault"
