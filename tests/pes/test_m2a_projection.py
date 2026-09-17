# -*- coding: utf-8 -*-
"""M2-A Step 1 · 只读投影层：**空库不 500** + **P3 无写权（AST）** + 三条反例。

设计稿：``codex/2026-09-17-v9pes-m2a-visibility-closure-design.md`` §4.2 / §6 Step 1。
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

from flask import Flask

from core.pa.pes_projection import project_runs
from core.pes import contract as pes_contract
from core.pes.run_registry import RunRegistry

ROOT = Path(__file__).resolve().parents[2]
_PROJ = ROOT / "core" / "pa" / "pes_projection.py"

#: 写函数（设计稿 §4.2 P3 的禁用清单，含 reconcile —— 它会写审计流）
_WRITE_FUNCS = {
    "_append", "register_run", "update_from_source", "verify_artifact",
    "record_artifact", "mark_claimed", "hold", "release", "update_runtime",
    "reduce", "save", "reconcile",
}
_FS_WRITES = {"write_text", "write_bytes", "mkdir", "unlink", "touch", "rename", "replace"}


def _tree():
    return ast.parse(_PROJ.read_text(encoding="utf-8"))


def _reg(pes_dir):
    return RunRegistry(pes_dir / "runs.jsonl")


def _proj(pes_dir, **kw):
    return project_runs(runs_path=pes_dir / "runs.jsonl",
                        contracts_dir=pes_dir / "contracts", **kw)


def _contract_for(pes_dir, run_id, **over):
    d = pes_dir / "contracts"
    d.mkdir(parents=True, exist_ok=True)
    c = dict(pes_contract.CONTRACT_DEFAULTS)
    c["task_id"] = run_id
    c.update(over)
    (d / (run_id + ".json")).write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    return c


# ---------------- P3：无写权（AST 钉死） ----------------
def test_P3_投影层不import也不调用任何写函数():
    """**机械**钉死「投影层无写权」，不靠自觉。"""
    t = _tree()
    imported = set()
    for n in ast.walk(t):
        if isinstance(n, ast.ImportFrom):
            imported |= {a.asname or a.name for a in n.names}
        elif isinstance(n, ast.Import):
            imported |= {(a.asname or a.name).split(".")[0] for a in n.names}
    assert imported & _WRITE_FUNCS == set()
    called = {n.func.attr for n in ast.walk(t)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert called & _WRITE_FUNCS == set()
    assert called & _FS_WRITES == set()


def test_P3_投影层不得以写模式打开文件():
    bad = []
    for n in ast.walk(_tree()):
        if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "open":
            modes = [a.value for a in n.args if isinstance(a, ast.Constant)]
            modes += [k.value.value for k in n.keywords
                      if k.arg == "mode" and isinstance(k.value, ast.Constant)]
            if any(isinstance(m, str) and any(c in m for c in "wa+") for m in modes):
                bad.append(ast.dump(n)[:120])
    assert bad == []


# ---------------- DoD ①：空库不 500 ----------------
def test_DoD1_空库返回空数组加降级信号且不抛异常(pes_dir):
    out = _proj(pes_dir)
    assert out["success"] is True
    assert out["runs"] == []
    assert [d["code"] for d in out["degradations"]] == ["registry_file_missing"]
    assert out["generated_at"]


# ---------------- DoD ③：三条反例 ----------------
def test_反例1_无契约不得判完成(pes_dir):
    _reg(pes_dir).register_run("r1", session_id="s1", state="done")
    out = _proj(pes_dir)
    v = out["runs"][0]["verdict"]
    assert v["state"] == "not_done"
    assert v["reason"] == "no_contract"
    assert "contract_missing" in [d["code"] for d in out["degradations"]]


def test_反例2_claimed不得出现done(pes_dir):
    art = {"path": "x.md", "exists": True, "sha256": "a" * 8, "bytes": 3}
    _reg(pes_dir).register_run("r2", session_id="s1", state="done",
                               done_when_status="claimed", artifact=art)
    _contract_for(pes_dir, "r2", done_when_status="claimed", artifact=art)
    run = _proj(pes_dir)["runs"][0]
    assert run["verdict"]["state"] == "not_done"
    assert run["verdict"]["reason"] == "claimed_only"
    assert run["artifact"]["done_when_status"] == "claimed"   # 原样渲染，不升级


def test_反例3_分母为0时不得出现percent键(pes_dir):
    _reg(pes_dir).register_run("r3", session_id="s1")
    _contract_for(pes_dir, "r3", steps_total=0, steps_done=2)
    pr = _proj(pes_dir)["runs"][0]["progress"]
    assert "percent" not in pr
    assert pr["mismatch"] is True


# ---------------- P1：未知即未知 ----------------
def test_P1_未取到产物时字段是null而不是false(pes_dir):
    _reg(pes_dir).register_run("r5", session_id="s1")   # 无契约 ⇒ 无产物来源
    art = _proj(pes_dir)["runs"][0]["artifact"]
    assert art["path"] is None and art["exists"] is None and art["sha256"] is None
    assert art["bytes"] is None
    assert art["done_when_status"] == "unset"          # 已知值，保留


def test_P1_契约空哨兵翻译成null但保留上游明确判过的false(pes_dir):
    _reg(pes_dir).register_run("r6", session_id="s1")
    _contract_for(pes_dir, "r6")                        # 默认契约：path="" / exists=False
    art = _proj(pes_dir)["runs"][0]["artifact"]
    assert art["path"] is None and art["sha256"] is None
    assert art["exists"] is False                       # 上游明确判过，不是我的兜底


# ---------------- 阻断卡骨架 / 审批卡不臆造 ----------------
def test_阻断行投影出blocked且未接线字段为null(pes_dir):
    _reg(pes_dir).register_run("r7", session_id="s1", state="blocked",
                               last_error={"message": "未 seed ⇒ 不得盘点", "tool": "write_note"})
    run = _proj(pes_dir)["runs"][0]
    assert run["blocked"]["reason"] == "未 seed ⇒ 不得盘点"
    assert run["blocked"]["blocked_action"] == "write_note"
    assert run["blocked"]["state_map_key"] == "blocked"
    assert run["blocked"]["layer"] is None and run["blocked"]["unblock_hint"] is None
    assert run["approval"] is None      # session 级实源与 run 无共同键 ⇒ 不臆造关联


def test_非阻断行不渲染阻断卡(pes_dir):
    _reg(pes_dir).register_run("r8", session_id="s1", state="running")
    assert _proj(pes_dir)["runs"][0]["blocked"] is None


# ---------------- 过滤 / 上限 / 接口 ----------------
def test_会话过滤与上限(pes_dir):
    r = _reg(pes_dir)
    r.register_run("a", session_id="s1")
    r.register_run("b", session_id="s2")
    assert [x["run_id"] for x in _proj(pes_dir, session_id="s1")["runs"]] == ["a"]
    assert len(_proj(pes_dir, limit=0)["runs"]) == 1      # 下限 1，不返回全量


def test_接口层_空库不500并给出同一形状(pes_dir, monkeypatch):
    import core.pa.pes_projection as proj

    monkeypatch.setattr(proj, "DEFAULT_RUNS_PATH", pes_dir / "runs.jsonl")
    app = Flask(__name__)
    from routes.pes import bp

    app.register_blueprint(bp)
    resp = app.test_client().get("/v9/pes/runs")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["runs"] == []
    assert body["degradations"][0]["code"] == "registry_file_missing"