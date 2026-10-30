# -*- coding: utf-8 -*-
u"""PA HarnessPort v1 · H2：`DshHarness`（`dsh --profile headless <task>` ⇒ PA 侧 canonical RunRecord）。

以何形调用：
  python -X utf8 -B -m pytest tests/unit/test_pa_harness_dsh.py -q

判据（可机检 · 承 62_PA_HarnessPort_v1.md §五 H2 ＋ task-9）：
  ① probe ＝ `shutil.which("dsh")` ＋ `dsh --version`（缺 ⇒ available=False · ⛔ 谎报）；
  ② run ＝ `dsh --profile headless <task>`：cwd ／ timeout ／ env 照 spec；capture stdout／stderr；
     canonical `RunRecord` 落 PA 账（harness="dsh" · status ok／failed · cost 0 · harness_meta 只
     profile／rc／stderr_tail）；⛔ 解析 DSH 会话格式；
  ③ resume 显式 `history_replay=False`（headless 无历史 · ⛔ 假回放）；
  ④ cancel／stream／permissions／cost／audit／team 按 port 语义（未知 id 显错）；
  ⑤ 边界：源内 ⛔ dsh／paseo／obsidian import、⛔ 第三方 import、⛔ shell=True、子进程唯
     `core.pa._proc.run_hidden`（窗隐出口）；测试以注入 runner 替身 ⇒ ⛔ 真跑模型。
"""
import ast
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa.harness import dsh as DSH  # noqa: E402
from core.pa.harness import port as PORT  # noqa: E402
from core.pa.harness.dsh import DSH_META_FIELDS, DshHarness, DshUnavailable  # noqa: E402

DSH_SRC = Path(DSH.__file__).resolve()

EXE = "C:/fake/bin/dsh.exe"

FORBIDDEN_IMPORT_ROOTS = {"dsh", "paseo", "obsidian"}


class FakeRunner:
    u"""`_proc.run_hidden` 之替身（记 call · ⛔ 真起进程）。"""

    def __init__(self, rc=0, stdout="", stderr="", exc=None):
        self.rc = rc
        self.stdout = stdout
        self.stderr = stderr
        self.exc = exc
        self.calls = []

    def __call__(self, cmd, **kw):
        self.calls.append((list(cmd), dict(kw)))
        if self.exc is not None:
            raise self.exc
        return SimpleNamespace(returncode=self.rc, stdout=self.stdout, stderr=self.stderr)

    @property
    def last(self):
        return self.calls[-1]


def _harness(runner, **kw):
    kw.setdefault("exe", EXE)
    return DshHarness(runner=runner, **kw)


def _run(harness, **spec_kw):
    kw = {"task": u"跑一个无关模型的小任务"}
    kw.update(spec_kw)
    return harness.run(kw)


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


# ---------- ① probe ----------

def test_probe_uses_which_and_version(monkeypatch):
    seen = {}

    def _which(name):
        seen["name"] = name
        return EXE

    monkeypatch.setattr(DSH.shutil, "which", _which)
    runner = FakeRunner(rc=0, stdout="dsh 0.1.5-rc.1\nextra\n", stderr="")
    harness = DshHarness(runner=runner, env={"DSH_PROBE_ENV": "1"})
    probe = harness.probe()
    assert seen["name"] == "dsh", u"probe 须 `shutil.which('dsh')`"
    assert probe.harness == "dsh" and probe.available is True
    assert probe.version == "dsh 0.1.5-rc.1", probe.version
    assert probe.at and probe.meta["exe"] == EXE and probe.meta["rc"] == 0
    cmd, kw = runner.last
    assert cmd == [EXE, "--version"], cmd
    assert kw["timeout"] == DSH.DSH_PROBE_TIMEOUT
    assert kw["capture_output"] is True and kw["text"] is True
    assert kw["env"]["DSH_PROBE_ENV"] == "1"
    assert kw.get("shell") in (None, False), u"⛔ shell"


def test_probe_missing_dsh_is_unavailable_and_run_refuses(monkeypatch):
    monkeypatch.setattr(DSH.shutil, "which", lambda name: None)

    def _boom(cmd, **kw):
        raise AssertionError(u"⛔ 起进程（dsh 缺）")

    harness = DshHarness(runner=_boom)
    probe = harness.probe()
    assert probe.available is False and probe.version == ""
    assert probe.meta["exe"] == ""
    assert "which" in probe.detail, probe.detail

    with pytest.raises(DshUnavailable):
        harness.run({"task": "t"})
    assert harness.ledger.count() == 0, u"未跑 ⇒ ⛔ 造假记录"


def test_probe_nonzero_rc_or_empty_version_is_unavailable():
    runner = FakeRunner(rc=1, stdout="", stderr="bad\n")
    probe = _harness(runner).probe()
    assert probe.available is False and probe.version == ""
    assert "rc=1" in probe.detail, probe.detail

    silent = _harness(FakeRunner(rc=0, stdout="\n", stderr="")).probe()
    assert silent.available is False, u"无版本读数 ⇒ ⛔ 充可用"


# ---------- ② run：命令 ／ env ／ cwd ／ timeout ／ canonical 记录 ----------

def test_H2_fake_run_command_env_cwd_timeout_and_canonical_record(monkeypatch):
    monkeypatch.setenv("DSH_INHERITED_ENV", "keep")
    runner = FakeRunner(rc=0, stdout="hello out\n", stderr="warn line\n")
    ledger = PORT.RunLedger()
    harness = DshHarness(ledger=ledger, exe=EXE, runner=runner, env={"DSH_TEST_ENV": "1"})
    handle = harness.run(PORT.RunSpec(
        task="do it now", cwd="D:/work", tools=("read_file",), permission_level="L2",
        timeout=7.5, model="dsh-test-model",
    ))

    cmd, kw = runner.last
    assert cmd == [EXE, "--profile", "headless", "do it now"], cmd
    assert kw["cwd"] == "D:/work"
    assert kw["timeout"] == 7.5
    assert kw["capture_output"] is True and kw["text"] is True
    assert kw["encoding"] == "utf-8" and kw["errors"] == "replace"
    assert "shell" not in kw or kw["shell"] in (None, False), u"⛔ shell=True"
    env = kw["env"]
    assert env is not os.environ and env["DSH_TEST_ENV"] == "1"
    assert env["DSH_INHERITED_ENV"] == "keep", u"env 须叠于本进程之上"
    assert any(k.upper() == "PATH" for k in env), u"⛔ 断 PATH"

    assert ledger.count() == 1, u"H2：记录须落 PA 侧"
    rec = ledger.get(handle.run_id)
    d = rec.to_dict()
    assert tuple(d) == PORT.RUN_RECORD_FIELDS, u"字段集 ／ 序须同 PA 账 schema"
    assert d["harness"] == "dsh" and d["status"] == "ok"
    assert d["model"] == "dsh-test-model" and d["cwd"] == "D:/work"
    assert d["session_id"] == handle.session_id
    assert d["session_id"].startswith("dsh-headless-"), u"headless 无原生 id ⇒ PA 侧代 id（明标）"
    assert d["cost"] == {"tokens": 0, "cny": 0.0, "turns": 1}, d["cost"]
    assert d["artifacts"] == []
    assert set(d["harness_meta"]) == set(DSH_META_FIELDS), d["harness_meta"]
    assert d["harness_meta"]["profile"] == "headless"
    assert d["harness_meta"]["rc"] == 0
    assert "warn" in d["harness_meta"]["stderr_tail"]
    assert rec.receipt_sha16 == PORT.sha16(rec.payload())
    assert handle.history_replay is False, u"headless ⛔ 假回放"

    events = harness.stream(handle.run_id)
    kinds = [e.kind for e in events]
    assert kinds[0] == "start" and kinds[-1] == "done", kinds
    assert "stdout" in kinds and "stderr" in kinds, kinds
    assert [e.seq for e in events] == list(range(1, len(events) + 1))
    assert all(e.run_id == handle.run_id for e in events)
    assert "hello out" in [e.text for e in events if e.kind == "stdout"][0]
    assert handle.stream == events

    assert ledger.dump() == [rec.to_dict()]
    assert json.loads(json.dumps(ledger.dump(), ensure_ascii=False)) == ledger.dump()


def test_run_default_timeout_and_cwd_inherit():
    runner = FakeRunner(rc=0, stdout="")
    harness = _harness(runner, default_timeout=33.0)
    handle = _run(harness)
    cmd, kw = runner.last
    assert cmd[1:3] == ["--profile", "headless"]
    assert kw["timeout"] == 33.0, u"spec.timeout=0 ⇒ 取 adapter 缺省"
    assert kw["cwd"] is None, u"spec.cwd 空 ⇒ 继承本进程 cwd"

    kinds = [e.kind for e in harness.stream(handle.run_id)]
    assert kinds == ["start", "done"], u"无输出 ⇒ ⛔ 造 stdout／stderr 事件"


# ---------- ③ 失败 ／ 超时 ／ 起进程失败：仍落 PA 账 ----------

def test_run_nonzero_rc_records_failed():
    runner = FakeRunner(rc=2, stdout="", stderr="boom\n")
    harness = _harness(runner)
    handle = _run(harness)
    rec = harness.ledger.get(handle.run_id)
    d = rec.to_dict()
    assert d["status"] == "failed", d
    assert d["harness_meta"]["rc"] == 2
    assert "boom" in d["harness_meta"]["stderr_tail"]
    kinds = [e.kind for e in harness.stream(handle.run_id)]
    assert kinds[-1] == "error" and "stderr" in kinds, kinds
    assert harness.ledger.count() == 1, u"失败亦须落账"


def test_run_timeout_records_failed_with_explicit_marker():
    cmd = [EXE, "--profile", "headless", "t"]
    exc = subprocess.TimeoutExpired(cmd, 7.5, output="partial out", stderr="slow net")
    runner = FakeRunner(exc=exc)
    harness = _harness(runner)
    handle = _run(harness, timeout=7.5)
    rec = harness.ledger.get(handle.run_id)
    d = rec.to_dict()
    assert d["status"] == "failed", d
    assert d["harness_meta"]["rc"] is None
    assert "TIMEOUT" in d["harness_meta"]["stderr_tail"], d["harness_meta"]
    assert "slow net" in d["harness_meta"]["stderr_tail"]
    kinds = [e.kind for e in harness.stream(handle.run_id)]
    assert "stdout" in kinds and kinds[-1] == "error", kinds
    assert harness.ledger.count() == 1


def test_run_spawn_error_records_failed():
    runner = FakeRunner(exc=FileNotFoundError("no dsh binary"))
    harness = _harness(runner)
    handle = _run(harness)
    d = harness.ledger.get(handle.run_id).to_dict()
    assert d["status"] == "failed", d
    assert d["harness_meta"]["rc"] is None
    assert "FileNotFoundError" in d["harness_meta"]["stderr_tail"]
    assert [e.kind for e in harness.stream(handle.run_id)][-1] == "error"
    assert harness.ledger.count() == 1


def test_run_rejects_empty_task_and_accepts_mapping():
    harness = _harness(FakeRunner(rc=0, stdout=""))
    handle = harness.run({"task": "mapped task"})
    assert harness.ledger.get(handle.run_id).status == "ok"
    with pytest.raises(ValueError):
        harness.run({"task": "   "})


# ---------- ④ resume ／ cancel ／ 未知 id ----------

def test_resume_declares_no_history_replay():
    harness = _harness(FakeRunner(rc=0, stdout=""))
    first = _run(harness)
    resumed = harness.resume(first.session_id)
    assert resumed.history_replay is False, u"headless 无历史 ⇒ 显式 False"
    assert resumed.session_id == first.session_id and resumed.run_id != first.run_id
    assert harness.ledger.count() == 1, u"resume 只续柄 ⇒ ⛔ 假落记录"

    follow = _run(harness, resume_id=first.session_id)
    rec = harness.ledger.get(follow.run_id)
    assert rec.session_id == first.session_id
    assert rec.harness_meta["profile"] == "headless"
    assert harness.ledger.count() == 2

    with pytest.raises(PORT.UnknownSession):
        harness.resume("dsh-sess-nope")
    with pytest.raises(PORT.UnknownSession):
        harness.run({"task": "t", "resume_id": "dsh-sess-nope"})


def test_cancel_and_unknown_ids_are_explicit():
    harness = _harness(FakeRunner(rc=0, stdout=""))
    handle = _run(harness)
    assert harness.cancel(handle.run_id) is False, u"同步 run ⇒ 已结束（⛔ 谎报已停）"
    resumed = harness.resume(handle.session_id)
    assert harness.cancel(resumed.run_id) is False, u"续柄亦无在跑窗口"
    for bad in ("pa-run-nope", ""):
        with pytest.raises(PORT.UnknownRun):
            harness.cancel(bad)
        with pytest.raises(PORT.UnknownRun):
            harness.stream(bad)
        with pytest.raises(PORT.UnknownRun):
            harness.cost(bad)
        with pytest.raises(PORT.UnknownRun):
            harness.audit(bad)


# ---------- ⑤ 门 ／ 成本 ／ 审计 ／ team（可选面） ----------

def test_permissions_cost_audit_team_semantics():
    harness = _harness(FakeRunner(rc=0, stdout="ok\n"))
    handle = _run(harness)
    rec = harness.ledger.get(handle.run_id)

    perm = harness.permissions()
    assert isinstance(perm, PORT.PermissionState)
    assert perm.harness == "dsh" and perm.level == "headless"
    assert perm.pending == (), u"headless 非交互 ⇒ ⛔ 造假待批"
    assert set(perm.gates.values()) <= set(PORT.PERMISSION_GATES)
    assert perm.gates.get("run") == "allow"

    assert harness.cost(handle.run_id) == rec.cost
    assert harness.cost(handle.run_id).to_dict() == {"tokens": 0, "cny": 0.0, "turns": 1}

    audit = harness.audit(handle.run_id)
    assert isinstance(audit, PORT.AuditResult)
    assert audit.receipt_sha16 == rec.receipt_sha16 and audit.status == rec.status
    assert audit.artifacts == rec.artifacts == ()
    assert audit.harness_meta == dict(rec.harness_meta)
    assert audit.to_dict()["receipt_sha16"] == rec.receipt_sha16

    team = harness.team()
    assert isinstance(team, PORT.TeamState)
    assert team.available is False and team.reason, u"可选能力不支须显式"


# ---------- ⑥ PA ledger 接线点（注入即共用） ----------

def test_ledger_hook_injection_and_canonical_shape():
    shared = PORT.RunLedger()
    harness = DshHarness(ledger=shared, exe=EXE, runner=FakeRunner(rc=0, stdout=""))
    handle = _run(harness)
    assert shared.count() == 1 and shared.get(handle.run_id).run_id == handle.run_id
    dumped = shared.dump()
    assert len(dumped) == 1
    assert tuple(dumped[0]) == PORT.RUN_RECORD_FIELDS
    assert set(dumped[0]["harness_meta"]) == set(DSH_META_FIELDS)
    assert json.loads(json.dumps(dumped, ensure_ascii=False)) == dumped

    with pytest.raises(ValueError):
        DshHarness(ledger={})


# ---------- ⑦ 边界（源静态可判 · ⛔ 真跑模型） ----------

def test_source_boundary_no_forbidden_imports_no_shell_no_session_parse():
    src = DSH_SRC.read_text(encoding="utf-8")
    roots, internal = _import_roots(DSH_SRC)
    assert not (roots & FORBIDDEN_IMPORT_ROOTS), (roots & FORBIDDEN_IMPORT_ROOTS)
    assert roots - set(sys.stdlib_module_names) - {"core"} == set(), u"⛔ 第三方 import：%s" % roots
    assert set(internal) <= {"core.pa", "core.pa.harness.port"}, internal
    # `from core.pa import _proc` 只许取窗隐出口一名（⛔ 夹带别 core 件）
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "core.pa":
            assert [a.name for a in node.names] == ["_proc"], [a.name for a in node.names]
        if isinstance(node, ast.ImportFrom) and node.module == "core.pa.harness.port":
            assert node.names, u"接口件须有名可引"
    assert "_proc.run_hidden" in src, u"子进程须经窗隐唯一出口"
    assert "subprocess.run(" not in src and "subprocess.Popen(" not in src
    assert "shell=True" not in src, u"⛔ shell=True"
    assert "--profile" in src and "headless" in src
    assert "v3" not in src and "v4" not in src, u"⛔ 解析 DSH 会话版本"
    assert "session_format" not in src, u"⛔ 会话格式 ⛔ 进 canonical 域"


def test_package_init_does_not_export_adapter():
    from core.pa import harness as hp

    assert not hasattr(hp, "DshHarness"), u"adapter ⛔ 由包 __init__ 隐式引入（§四.1 ／ H5）"
    assert hasattr(hp, "HarnessPort")
