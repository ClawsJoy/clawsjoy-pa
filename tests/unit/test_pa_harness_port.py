# -*- coding: utf-8 -*-
u"""PA HarnessPort v1 · H1：接口面 ＋ MockHarness ⇒ PA 侧 canonical RunRecord。

以何形调用：
  python -X utf8 -B -m pytest tests/unit/test_pa_harness_port.py -q

判据（可机检 · 承 62_PA_HarnessPort_v1.md）：
  ① **接口面**：probe ／ run ／ resume ／ cancel ／ stream ／ permissions ／ cost ／ audit ／ team? 齐；
     `MockHarness` 满足 `HarnessPort`（runtime_checkable）。
  ② **H1**：`MockHarness` 跑一任务 ⇒ canonical `RunRecord` 落 PA 侧 `RunLedger`（内存）；
     字段集 ≡ `RUN_RECORD_FIELDS`（§三 schema · H4 之基）；可 JSON 序列化（可交 PA 账）。
  ③ **显式不回放**：handle ／ harness_meta 之 `history_replay=False`（§四.4 · ⛔ 默认蒙混）。
  ④ **可选 team**：不支持须显式 `available=False` ＋ reason（⛔ 静默替身）。
  ⑤ **依赖边界**：harness 包源内 ⛔ dsh ／ paseo ／ obsidian import；core/pa 只可 import 本包 `port`。
  ⑥ **⛔ 假绿**：未知 run／session 显错；receipt 可验篡改；失败终态／成本／增量皆自 PA 账。
"""
import ast
import dataclasses
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa.harness import port as PORT  # noqa: E402
from core.pa.harness.mock import (  # noqa: E402
    MOCK_SESSION_FORMAT,
    MOCK_VERSION,
    MockHarness,
)

HARNESS_DIR = Path(PORT.__file__).resolve().parent

FORBIDDEN_IMPORT_ROOTS = {"dsh", "paseo", "obsidian"}

INTERNAL_PREFIX = "core.pa.harness"

TASK = u"把今天的待办汇总成一页"


# ---------- 小工厂 ----------

def _handle(harness=None, **spec_kw):
    h = harness or MockHarness()
    kw = {"task": TASK}
    kw.update(spec_kw)
    return h, h.run(kw)


def _record(run_id="pa-run-test0001", session_id="mock-sess-test", **over):
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


def _import_roots(path):
    u"""单件之 (外部根集, harness 包内部 import 模块名列表) —— AST 取（⛔ 字面扫）。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots, internal = set(), []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
                if alias.name.startswith(INTERNAL_PREFIX):
                    internal.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
            if node.module.startswith(INTERNAL_PREFIX):
                internal.append(node.module)
    return roots, internal


# ---------- ① 接口面 ----------

def test_interface_surface_complete():
    missing = [m for m in PORT.HARNESS_METHODS if not callable(getattr(MockHarness, m, None))]
    assert not missing, u"MockHarness 缺接口方法：%s" % missing
    assert PORT.HARNESS_METHODS[-1] == "team", u"team 为可选面（居末）"
    assert isinstance(MockHarness(), PORT.HarnessPort)


def test_interface_is_importable_from_port_only():
    u"""core/pa 只 import 本包之 `port`：包 `__init__` ⛔ 隐式拉 adapter。"""
    from core.pa import harness as hp

    assert hasattr(hp, "HarnessPort") and issubclass(hp.HarnessError, Exception)
    assert not hasattr(hp, "MockHarness"), u"adapter（mock）⛔ 由包 __init__ 隐式引入（§四.1 ／ H5）"


def test_canonical_schema_frozen():
    u"""H4 之基：PA 账 schema 一字不差（换 adapter ／ session 版本皆 ⛔ 改）。"""
    assert PORT.RUN_RECORD_FIELDS == (
        "run_id", "harness", "session_id", "model", "cwd", "started_at", "ended_at",
        "status", "cost", "artifacts", "receipt_sha16", "harness_meta",
    )
    assert PORT.RUN_STATUSES == ("ok", "failed", "cancelled")
    assert PORT.PA_HARNESS_PORT_VERSION == "v1"


# ---------- ② H1：MockHarness 跑一任务 ⇒ canonical RunRecord 落 PA 侧 ----------

def test_H1_mock_run_lands_canonical_runrecord_pa_side():
    ledger = PORT.RunLedger()
    harness = MockHarness(ledger=ledger)
    assert harness.ledger is ledger, u"须落**注入**之 PA 账（⛔ 另立私账）"

    handle = harness.run(PORT.RunSpec(task=TASK, cwd="D:/ws", tools=("read_file", "write_file"),
                                        permission_level="L2", timeout=30, model="mock-x"))
    assert isinstance(handle, PORT.RunHandle)
    assert handle.run_id.startswith("pa-run-"), handle.run_id
    assert handle.session_id.startswith("mock-sess-"), handle.session_id
    assert handle.harness == "mock"
    assert handle.history_replay is False, u"不回放历史须显式 False（§四.4）"
    assert handle.stream and all(isinstance(e, PORT.StreamEvent) for e in handle.stream)

    assert ledger.count() == 1, u"RunRecord 未落 PA 侧"
    rec = ledger.get(handle.run_id)
    assert isinstance(rec, PORT.RunRecord)

    d = rec.to_dict()
    assert tuple(d) == PORT.RUN_RECORD_FIELDS, u"字段集 ／ 序须同 §三 schema"
    assert d["run_id"] == handle.run_id
    assert d["harness"] == "mock"
    assert d["session_id"] == handle.session_id
    assert d["model"] == "mock-x", d["model"]
    assert d["cwd"] == "D:/ws", d["cwd"]
    assert d["status"] == "ok", d
    assert d["cost"] == {"tokens": len(TASK), "cny": 0.0, "turns": 1}, d["cost"]
    assert d["artifacts"] == []
    assert isinstance(d["harness_meta"], dict) and d["harness_meta"]
    assert d["harness_meta"]["session_format"] == MOCK_SESSION_FORMAT
    assert d["harness_meta"]["history_replay"] is False
    assert rec.receipt_sha16 == PORT.sha16(rec.payload()), u"receipt 须为 canonical payload 之 sha16"

    # PA 账之形可直接序列化（交 PA ledger／vault 之前提）
    raw = json.dumps(d, ensure_ascii=False)
    assert json.loads(raw) == d


def test_run_spec_coercion_and_validation():
    spec = PORT.RunSpec.from_any({"task": "t", "cwd": "c", "tools": ["a"], "permission_level": "L2",
                                  "timeout": 5, "model": "m", "resume_id": ""})
    assert spec.tools == ("a",), spec.tools
    assert spec.to_dict()["timeout"] == 5.0
    assert tuple(PORT.RunSpec(task="t").to_dict()) == PORT.RUN_SPEC_FIELDS

    with pytest.raises(ValueError):
        PORT.RunSpec(task="   ")
    with pytest.raises(ValueError):
        PORT.RunSpec(task="t", timeout=-1)
    with pytest.raises(ValueError):
        PORT.RunSpec.from_any({"cwd": "c"})
    with pytest.raises(ValueError):
        PORT.RunSpec.from_any({"task": "t", "bogus": 1})
    with pytest.raises(ValueError):
        MockHarness().run({"task": "  "})


# ---------- ③ 探 ／ 门 ／ 团队（可选 · 须显式） ----------

def test_probe_permissions_team_are_honest():
    harness = MockHarness()
    probe = harness.probe()
    assert isinstance(probe, PORT.ProbeResult)
    assert probe.available is True and probe.version == MOCK_VERSION
    assert probe.harness == "mock" and probe.at, probe
    assert probe.meta["external"] is False

    perm = harness.permissions()
    assert isinstance(perm, PORT.PermissionState)
    assert perm.level and perm.gates, perm
    assert set(perm.gates.values()) <= set(PORT.PERMISSION_GATES), perm.gates
    assert perm.pending == (), u"mock 无待批 ⇒ ⛔ 造待批"

    team = harness.team()
    assert isinstance(team, PORT.TeamState)
    assert team.available is False and team.reason, u"可选能力不支持须显式（⛔ 静默替身）"
    assert issubclass(PORT.UnsupportedCapability, PORT.HarnessError)


# ---------- ④ 增量 ／ 成本 ／ 审计（皆自 PA 账） ----------

def test_stream_cost_audit_consistent_with_pa_ledger():
    harness, handle = _handle()
    rec = harness.ledger.get(handle.run_id)

    events = list(harness.stream(handle.run_id))
    assert len(events) >= 2, events
    assert [e.seq for e in events] == list(range(1, len(events) + 1)), u"seq 须单调"
    assert all(e.run_id == handle.run_id for e in events)
    kinds = [e.kind for e in events]
    assert kinds[0] == "start" and kinds[-1] == "done", kinds
    assert set(kinds) <= set(PORT.STREAM_KINDS)
    assert list(harness.stream(handle.run_id)) == events, u"增量读取须只读快照"

    assert harness.cost(handle.run_id) == rec.cost
    audit = harness.audit(handle.run_id)
    assert isinstance(audit, PORT.AuditResult)
    assert audit.run_id == rec.run_id and audit.status == rec.status
    assert audit.receipt_sha16 == rec.receipt_sha16, u"审计之印 ⛔ 另取"
    assert audit.artifacts == rec.artifacts
    assert audit.harness_meta == dict(rec.harness_meta)
    assert audit.to_dict()["receipt_sha16"] == rec.receipt_sha16


def test_failure_path_records_failed_status():
    harness = MockHarness(fail=True)
    handle = harness.run({"task": TASK})
    rec = harness.ledger.get(handle.run_id)
    assert rec.status == "failed", rec.status
    assert rec.to_dict()["status"] == "failed"
    assert [e.kind for e in harness.stream(handle.run_id)][-1] == "error", u"失败须有 error 增量"
    assert rec.harness_meta["fail"] is True


# ---------- ⑤ 续会话（显式不回放） ----------

def test_resume_declares_no_history_replay():
    harness, handle = _handle()
    resumed = harness.resume(handle.session_id)
    assert isinstance(resumed, PORT.RunHandle)
    assert resumed.session_id == handle.session_id, u"续之 session 须同"
    assert resumed.run_id != handle.run_id
    assert resumed.history_replay is False, u"不回放须显式 False"
    assert harness.ledger.count() == 1, u"resume 只续柄 ⇒ ⛔ 假落 RunRecord"

    follow = harness.run(PORT.RunSpec(task=u"继续", resume_id=handle.session_id))
    rec = harness.ledger.get(follow.run_id)
    assert rec.session_id == handle.session_id
    assert rec.harness_meta["resume_from"] == handle.run_id, rec.harness_meta
    assert rec.harness_meta["history_replay"] is False
    assert harness.ledger.count() == 2

    with pytest.raises(PORT.UnknownSession):
        harness.resume("mock-sess-nope")
    with pytest.raises(PORT.UnknownSession):
        harness.run(PORT.RunSpec(task="t", resume_id="mock-sess-nope"))


def test_cancel_and_unknown_ids_are_explicit():
    harness, handle = _handle()
    assert harness.cancel(handle.run_id) is False, u"同步 mock 之已知 run 必已结束 ⇒ ⛔ 谎报已停"
    for bad in ("pa-run-nope", ""):
        with pytest.raises(PORT.UnknownRun):
            harness.cancel(bad)
        with pytest.raises(PORT.UnknownRun):
            harness.stream(bad)
        with pytest.raises(PORT.UnknownRun):
            harness.cost(bad)
        with pytest.raises(PORT.UnknownRun):
            harness.audit(bad)


# ---------- ⑥ canonical 账（receipt ／ 校验 ／ 账本） ----------

def test_runrecord_receipt_tamper_evident_and_schema_validated():
    rec = _record()
    assert rec.receipt_sha16 == PORT.sha16(rec.payload())
    assert _record().receipt_sha16 == rec.receipt_sha16, u"同料 ⇒ 同印（canonical 键序）"
    assert _record(status="failed").receipt_sha16 != rec.receipt_sha16, u"改字段须改印"

    good = _record(receipt_sha16=rec.receipt_sha16)
    assert good.receipt_sha16 == rec.receipt_sha16
    with pytest.raises(ValueError):
        _record(receipt_sha16="0" * 16)
    with pytest.raises(ValueError):
        _record(receipt_sha16="short")
    with pytest.raises(ValueError):
        _record(status="done")
    with pytest.raises(ValueError):
        _record(cost={"tokens": 1})

    with pytest.raises(dataclasses.FrozenInstanceError):
        rec.status = "failed"

    mutated = _record(harness_meta={"k": "v", "extra": 1})
    assert mutated.receipt_sha16 != rec.receipt_sha16, u"harness_meta 亦入印"


def test_runledger_canonical_store():
    ledger = PORT.RunLedger()
    assert ledger.count() == 0 and ledger.latest() is None
    assert ledger.records() == () and ledger.dump() == []

    r1 = _record(run_id="pa-run-a", session_id="s1")
    r2 = _record(run_id="pa-run-b", session_id="s1")
    r3 = _record(run_id="pa-run-c", session_id="s2")
    for r in (r1, r2, r3):
        ledger.append(r)
    assert ledger.records() == (r1, r2, r3), u"账序须保"
    assert ledger.count() == 3 and ledger.latest() == r3
    assert ledger.get("pa-run-a") == r1
    assert ledger.has("pa-run-b") is True and ledger.has("pa-run-x") is False
    assert ledger.by_session("s1") == (r1, r2)
    assert ledger.by_session("nope") == ()
    assert ledger.dump() == [r1.to_dict(), r2.to_dict(), r3.to_dict()]
    assert json.loads(json.dumps(ledger.dump(), ensure_ascii=False)) == ledger.dump()

    with pytest.raises(ValueError):
        ledger.append(r1)
    with pytest.raises(ValueError):
        ledger.append({"run_id": "pa-run-x"})
    with pytest.raises(PORT.UnknownRun):
        ledger.get("pa-run-nope")
    with pytest.raises(ValueError):
        PORT.RunLedger(records=[r1, _record(run_id="pa-run-a")])


def test_mock_harness_ledger_isolation_and_injection():
    a, b = MockHarness(), MockHarness()
    ha = a.run({"task": "a"})
    hb = b.run({"task": "b"})
    assert a.ledger.count() == 1 and b.ledger.count() == 1
    assert a.ledger.get(ha.run_id).run_id != b.ledger.get(hb.run_id).run_id

    shared = PORT.RunLedger()
    c = MockHarness(ledger=shared)
    hc = c.run({"task": "c"})
    assert shared.count() == 1 and shared.get(hc.run_id).run_id == hc.run_id

    with pytest.raises(ValueError):
        MockHarness(ledger={})


# ---------- ⑦ 依赖边界（H1 ／ H5 之齿） ----------

def test_harness_sources_have_no_dsh_paseo_obsidian_import():
    files = sorted(HARNESS_DIR.glob("*.py"))
    names = {p.name for p in files}
    assert {"__init__.py", "port.py", "mock.py", "dsh.py"} <= names, names
    for path in files:
        roots, internal = _import_roots(path)
        leaked = sorted(roots & FORBIDDEN_IMPORT_ROOTS)
        assert not leaked, (path.name, leaked)
        if path.name == "port.py":
            assert internal == [], u"接口件 ⛔ import 任何 core.*（dependency inversion 之界）"
        else:
            # adapter 只可引接口 ＋ 窗隐唯一出口 `core.pa._proc`（⛔ 引别 core 件 · ⛔ 第三方）
            assert set(internal) <= {"core.pa.harness.port", "core.pa._proc"}, (path.name, internal)


def test_mock_run_writes_no_files():
    before = sorted(p.name for p in HARNESS_DIR.iterdir())
    harness, handle = _handle()
    harness.ledger.get(handle.run_id)
    after = sorted(p.name for p in HARNESS_DIR.iterdir())
    assert after == before, u"H1 之 mock ⛔ 写盘（内存账）"
