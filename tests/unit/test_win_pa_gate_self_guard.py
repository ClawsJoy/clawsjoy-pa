# -*- coding: utf-8 -*-
u"""出包之闸之「自守」之齿（pm_1606 §二.2 ／ §二.4 ／ 组三 · 随下批之实质改）。

⒜ **活控**（组二）：`build_runtime.probe_start` 之探＝**真起服** ⇒ 服务会把界面态快照
   写进**载荷**（`core/gateway/ui_state.py:245-248`：env `CJ_UI_STATE` ∨ `<根>/web/pa/ui_state.json`）
   ⇒ **闸之自污**。本齿以假 exe ＋ 假「服务」跑 `probe_start`：
     正控 ⇒ `CJ_UI_STATE` 必在 env ∧ 快照 ⛔ 落载荷 ∧ 载荷之「⛔ 入包」之径 ＝ **0**；
     反控 ⇒ 抽去 `CJ_UI_STATE`（＝修前之形）⇒ 载荷**必**见 `web/pa/ui_state.json`
            （证本齿 ⛔ 空转）。
⒝ **静齿**：凡 `make_setup._gate(` 之调用 ⇒ 其后须有 `guard_dist(` 之**复读**
   （承「凡闸须自守其面」—— 首检在闸之**先** ⇒ ⛔ 以首检为已守）。
⒞ **净树之闸**（组四⒜）：`make_client_bundle.guard_tree` 之三口径（`M` ／ `??` ／ ignored）。
⒟ **载荷之 `.bak`**（组三）：载荷之面 ⛔ 留 `.bak` 之碎屑（免随 zip 入包 · pm_1602 §一.6）。

器取：`python -X utf8 -B -m pytest tests/unit/test_win_pa_gate_self_guard.py -q`
"""
from __future__ import annotations

import ast
import io
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WPA = ROOT / "scripts" / "win_pa"
sys.path.insert(0, str(WPA))
sys.path.insert(0, str(ROOT))

import build_runtime as B  # noqa: E402
import make_client_bundle as M  # noqa: E402
import make_setup as S  # noqa: E402


# ------------------------------------------------------------------ 组二 ⒜ 活控

class _Ret(object):
    def __init__(self, rc=0, out=u"", err=u""):
        self.returncode = rc
        self.stdout = out
        self.stderr = err


class _Resp(object):
    u"""拟 `urllib` 之响应（`with … as h: h.status` 之形）。"""
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _mk_payload(tmp):
    p = Path(tmp) / "payload"
    (p / "scripts" / "win_pa").mkdir(parents=True)
    (p / "scripts" / "win_pa" / "pa_nowindow.py").write_text("x=1\n", encoding="utf-8")
    (p / "runtime").mkdir()
    (p / "runtime" / "python.exe").write_bytes(b"")
    return str(p)


def _stub_run(payload, seen, drop_env=False):
    u"""拟 `run`：仿「服务」之写（与 `ui_state.snapshot_path()` 同义）＋ 收建之果。"""
    def _run(cmd, cwd=None, timeout=3600, env=None):
        env = dict(env or {})
        if drop_env:
            env.pop("CJ_UI_STATE", None)      # ＝修前之形（⛔ 设）
        seen["env"] = env
        seen["cmd"] = list(cmd)
        p = env.get("CJ_UI_STATE") or os.path.join(payload, "web", "pa", "ui_state.json")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        io.open(p, "w", encoding="utf-8").write("{}\n")
        seen["wrote"] = p
        return _Ret(0, u"[INFO] port 5199\n", u"")
    return _run


def _forbidden(payload):
    u"""载荷之「⛔ 入包」之径 —— 判据**同源** `make_setup.FORBIDDEN_TOP`（一处定形）。"""
    return [t for t in S.FORBIDDEN_TOP
            if os.path.exists(os.path.join(payload, t.replace("/", os.sep)))]


def test_probe_start_keeps_ui_state_out_of_payload(tmp_path, monkeypatch):
    u"""正控：`CJ_UI_STATE` 必在 env ∧ 快照 ⛔ 落载荷 ∧ 「⛔ 入包」之径 ＝ 0。"""
    payload = _mk_payload(tmp_path)
    seen = {}
    monkeypatch.setattr(B, "run", _stub_run(payload, seen))
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: _Resp())
    up, rows = B.probe_start("python.exe", payload)
    assert up is True, rows
    env = seen["env"]
    assert "CJ_UI_STATE" in env, u"⛔ 见 `CJ_UI_STATE`（闸之自污之修 · pm_1606 §二.2 ⒜）"
    wrote = os.path.abspath(seen["wrote"]).replace(os.sep, "/")
    root = os.path.abspath(payload).replace(os.sep, "/")
    assert not wrote.startswith(root + "/"), u"⛔ 快照落载荷：%s" % wrote
    assert _forbidden(payload) == [], u"⛔ 载荷之「⛔ 入包」之径 ⛔ 为 0：%s" % _forbidden(payload)


def test_probe_start_control_detects_the_pollution(tmp_path, monkeypatch):
    u"""反控（修前之形）：抽去 `CJ_UI_STATE` ⇒ 载荷**必**见 `web/pa/ui_state.json`（齿 ⛔ 空转）。"""
    payload = _mk_payload(tmp_path)
    seen = {}
    monkeypatch.setattr(B, "run", _stub_run(payload, seen, drop_env=True))
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: _Resp())
    up, _rows = B.probe_start("python.exe", payload)
    assert up is True
    assert _forbidden(payload) == ["web/pa/ui_state.json"], u"⛔ 反控 ⛔ 逮（齿疑空转）"


# ------------------------------------------------------------------ 组二 ⒝ 静齿

def _gate_offenders(src):
    u"""凡 `_gate(` 之调用而**其后** ⛔ `guard_dist(` 之复读者 ⇒ 逐处点名。"""
    tree = ast.parse(src)
    outs = []
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        gates = [c.lineno for c in ast.walk(fn) if isinstance(c, ast.Call)
                 and isinstance(c.func, ast.Name) and c.func.id == "_gate"]
        guards = [c.lineno for c in ast.walk(fn) if isinstance(c, ast.Call)
                  and isinstance(c.func, ast.Name) and c.func.id == "guard_dist"]
        for g in gates:
            if not [x for x in guards if x > g]:
                outs.append((fn.name, g))
    return outs


def test_every_gate_call_is_followed_by_a_guard_reread():
    u"""决定之齿：`make_setup.build` 之 `_gate` 之后必有 `guard_dist` 之复读。"""
    src = (WPA / "make_setup.py").read_text(encoding="utf-8")
    bad = _gate_offenders(src)
    assert not bad, (u"⛔ 凡 `_gate` 之调用 ⇒ 其后须有 `guard_dist` 之复读"
                     u"（凡闸须自守其面 · pm_1606 §二.2）：%s" % bad)


def test_gate_tooth_detects_a_gate_without_a_reread():
    u"""反控：构造「有闸而 ⛔ 守」之源 ⇒ 本齿**必逮**（⛔ 空转之绿）。"""
    drift = (u"def build(d):\n"
             u"    ok = guard_dist(d)\n"
             u"    _g_ok, _g_rows = _gate(d)\n"
             u"    return 0\n")
    assert _gate_offenders(drift) == [("build", 3)]
    good = (u"def build(d):\n"
            u"    ok = guard_dist(d)\n"
            u"    _g_ok, _g_rows = _gate(d)\n"
            u"    ok2 = guard_dist(d)\n"
            u"    return 0\n")
    assert _gate_offenders(good) == []


# ------------------------------------------------------------------ 组四 ⒜ 净树之闸

def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo)] + list(args), capture_output=True)


@pytest.fixture
def grepo(tmp_path):
    r = tmp_path / "r"
    (r / "core").mkdir(parents=True)
    (r / "core" / "ok.py").write_text("x=1\n", encoding="utf-8")
    (r / ".gitignore").write_text("*.bak\n", encoding="utf-8")
    _git(r, "init", "-q")
    _git(r, "add", "-A")
    _git(r, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "i")
    return r


def test_guard_tree_clean_is_ok(grepo):
    ok, rows = M.guard_tree(str(grepo), [])
    assert ok, rows


def test_guard_tree_flags_a_tracked_change(grepo):
    (grepo / "core" / "ok.py").write_text("x=2\n", encoding="utf-8")
    ok, rows = M.guard_tree(str(grepo), [])
    assert not ok and any("core/ok.py" in r for r in rows), rows


def test_guard_tree_flags_a_deletion(grepo):
    _git(grepo, "rm", "-q", "core/ok.py")
    ok, rows = M.guard_tree(str(grepo), [])
    assert not ok and any("core/ok.py" in r for r in rows), rows


def test_guard_tree_flags_an_untracked_stray(grepo):
    (grepo / "core" / "new.py").write_text("y=1\n", encoding="utf-8")
    ok, rows = M.guard_tree(str(grepo), [])
    assert not ok and any("core/new.py" in r for r in rows), rows


def test_guard_tree_allows_untracked_dist(grepo):
    u"""正控：未跟踪而**唯 `dist/`** ⇒ 可（＝出包之产物 · ⛔ 假红）。"""
    (grepo / "dist").mkdir()
    (grepo / "dist" / "out.bin").write_bytes(b"x")
    ok, rows = M.guard_tree(str(grepo), [])
    assert ok, rows


def test_guard_tree_flags_an_ignored_bak_inside_the_payload(grepo):
    u"""口径 ⒞（组三之的）：`*.bak` 之碎屑（被忽略而实在）∧ 在载荷之内 ⇒ **止**。"""
    (grepo / "core" / "x.py.bak").write_text("z\n", encoding="utf-8")
    ok, rows = M.guard_tree(str(grepo), ["core/x.py.bak"])
    assert not ok and any("x.py.bak" in r for r in rows), rows
    ok2, rows2 = M.guard_tree(str(grepo), ["core/ok.py"])
    assert ok2, rows2          # 正控：⛔ 在载荷之表 ⇒ ⛔ 计（⛔ 假红）


def test_guard_tree_fails_loud_outside_a_repo(tmp_path, monkeypatch):
    u"""反控：「⛔ 得判」（非仓）⇒ **按拒论**（⛔ 判绿）。"""
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    d = tmp_path / "norepo"
    d.mkdir()
    ok, rows = M.guard_tree(str(d), [])
    assert not ok and any(u"⛔ 得判" in r for r in rows), rows


# ------------------------------------------------------------------ 组三 载荷之 .bak

def test_payload_face_has_no_bak_dregs():
    u"""载荷之面 ⛔ 含 `.bak` 之碎屑（如 `core/lib/chat_engine.py.bak_060732` · pm_1602 §一.6）。"""
    files = M._payload_files(str(ROOT))
    bad = [f for f in files if ".bak" in os.path.basename(f).lower()]
    assert not bad, u"⛔ 载荷之面含 `.bak` 之碎屑 %d：%s" % (len(bad), bad[:10])
