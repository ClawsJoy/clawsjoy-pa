# -*- coding: utf-8 -*-
u"""pm_1684 §四 之齿：`POST /v9/pa/update` 之端 ＋ `core/lib/update_run.py` 之「跑」之态
（TD f202f89 · 2026-10-07）。契约见 pm_1684 §四.1。

判据（正 ／ 反控）：
  E1 唯读（`status` ／ 缺 action）⇒ 200 ∧ `phase=idle`（明书「未跑」—— 空 ⛔ 混 缺）
  E2 反控：未知 action ⇒ 400；非本机（REMOTE_ADDR 非环回）⇒ 403（⛔ 外网）
  E3 正控：`start` ⇒ 200 ∧ `phase=running` ∧ **起一器**（argv **逐字列全**：器之径 ＋
       `--root <根> --go --json --no-restart` —— ⭐ pm_1799 §二.3⒜：「停／起服务」归壳）
  E4 ⭐反控（幂等）：再 `start`（犹 running）⇒ **⛔ 起第二支**（spawn 计数 ⛔ 增）
  E5 正控：器终为成（`finish(rc=0)`）⇒ `status` ⇒ `done`（跨「停→换→起」之可察）
  E6 反控：器终为败（`finish(rc=2)`）⇒ `status` ⇒ `failed` ∧ 明书（⛔ 冒「成」）
  E7 ⭐反控：`running` 而逾陈阈 ⇒ `failed`（明书「中断」—— ⛔ 长挂 running 而面恒转）
  E8 ⭐态与「根」绑定：他根之态 ⇒ 本根**⛔ 见**（承 pm_1659 §二.1 之跨根）
  E9 ⭐真 HTTP（werkzeug · 127.0.0.1 之实套接）：`status` ⇒ 200 ∧ `idle`；`start` ⇒ `running`
       （正控）；未知 action ⇒ 400（反控）—— 「真 HTTP 之正反控」之实（⛔ 唯 test_client 之自证）
  E10 一处定形：唯端出「调器」之 argv（本档之源扫 —— 值 ⛔ 硬编）

以何形调用（判通 ／ 断须附）：
  python -X utf8 -B -m pytest tests/unit/test_v9_pa_update_1684.py -q
"""
from __future__ import annotations

import json
import sys
import threading
import time
import urllib.request
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tests.pa_src import gr_src  # noqa: E402

from core.lib import update_run as UR          # noqa: E402
from core.lib import update_source as US       # noqa: E402
from core.pa.gateway_routes import register_pa_routes  # noqa: E402


@pytest.fixture()
def env(tmp_path, monkeypatch):
    u"""温床：态落 `%LOCALAPPDATA%` 之临时处（⛔ 动真盘）＋ 器之起以桩录之（⛔ 真起器）。"""
    lam = tmp_path / "LA"
    lam.mkdir()
    monkeypatch.setenv("LOCALAPPDATA", str(lam))
    UR.clear(US.root_dir())
    spawned = []

    class _P:
        pid = 4242

    def _stub(argv, **kw):
        spawned.append({"argv": list(argv), "kw": dict(kw)})
        return _P()

    monkeypatch.setattr("core.pa.gateway_routes._proc.popen_hidden", _stub)
    app = Flask(__name__)
    register_pa_routes(app)
    try:
        yield app, spawned, lam
    finally:
        UR.clear(US.root_dir())


def _post(c, action):
    return c.post("/v9/pa/update", json={"action": action})


def test_E1_status_idle(env):
    app, _sp, _la = env
    c = app.test_client()
    r = c.post("/v9/pa/update", json={"action": "status"})
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    assert d["ok"] is True and d["phase"] == "idle", d
    assert u"未跑" in d["note"], d
    r2 = c.post("/v9/pa/update")          # 缺 action ⇒ 同唯读
    assert r2.get_json()["phase"] == "idle"


def test_E2_negative_guards(env):
    app, _sp, _la = env
    c = app.test_client()
    assert _post(c, "bogus").status_code == 400
    far = app.test_client().post("/v9/pa/update", json={"action": "status"},
                                 environ_overrides={"REMOTE_ADDR": "10.9.9.9"})
    assert far.status_code == 403, far.get_data(as_text=True)


def test_E3_start_positive(env):
    app, sp, _la = env
    r = _post(app.test_client(), "start")
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    assert d["phase"] == "running", d
    assert len(sp) == 1, sp
    argv = sp[0]["argv"]
    # ⭐ pm_1799 §二.3⒜（**逐字列全** · ⛔ 唯尾四）：页内之路**须**带 `--no-restart`
    #   （「停／起服务」归壳）—— 昔之「默认起」（器自停自起）在净机恒败：正控 ⛔ 过 ⇒ 回滚 ⇒ rc=2。
    assert argv[1:4] == ["-X", "utf8", "-B"], argv
    assert argv[4].replace("\\", "/").endswith("scripts/win_pa/pa_update.py"), argv
    assert argv[0].lower().endswith("python.exe") or "python" in argv[0].lower(), argv
    assert argv[5:] == ["--root", str(US.root_dir()), "--go", "--json", "--no-restart"], argv
    assert sp[0]["kw"].get("cwd") == US.root_dir()
    # 落盘之态亦为 running（跨重启可读）
    assert UR.phase(US.root_dir())["phase"] == "running"


def test_E4_idempotent_no_second(env):
    app, sp, _la = env
    c = app.test_client()
    assert _post(c, "start").get_json()["phase"] == "running"
    assert _post(c, "start").get_json()["phase"] == "running"
    assert len(sp) == 1, u"已在跑 ⇒ ⛔ 起第二支"


def test_E5_done_after_finish(env):
    app, _sp, _la = env
    c = app.test_client()
    UR.begin(US.root_dir(), from_version="9.0.1")
    UR.finish(US.root_dir(), rc=0, to_version="9.0.2")
    d = _post(c, "status").get_json()
    assert d["phase"] == "done" and d["to"] == "9.0.2", d
    assert "9.0.1" in d["note"] and "9.0.2" in d["note"], d


def test_E6_failed_after_finish(env):
    app, _sp, _la = env
    c = app.test_client()
    UR.begin(US.root_dir(), from_version="9.0.1")
    UR.finish(US.root_dir(), rc=2)
    d = _post(c, "status").get_json()
    assert d["phase"] == "failed", d
    assert u"回滚" in d["note"], d


def test_E7_stale_running_becomes_failed(env):
    app, _sp, _la = env
    st = UR.state_path(US.root_dir())
    import io
    import os
    os.makedirs(os.path.dirname(st), exist_ok=True)
    old = time.strftime(u"%Y-%m-%dT%H:%M:%S%z", time.localtime(time.time() - UR.STALE_S - 60))
    io.open(st, "w", encoding="utf-8", newline="").write(json.dumps(
        {"phase": "running", "started_at": old, "root": UR.UC.root_of(US.root_dir())},
        ensure_ascii=False))
    d = _post(app.test_client(), "status").get_json()
    assert d["phase"] == "failed" and d["note_why"] == "stale", d


def test_E8_state_bound_to_root(env, tmp_path):
    _app, _sp, _la = env
    other = tmp_path / "other_root"
    other.mkdir()
    UR.begin(str(other))
    assert UR.phase(US.root_dir())["phase"] == "idle", u"他根之态 ⇒ 本根 ⛔ 见"
    assert UR.phase(str(other))["phase"] == "running"
    # 件名带根之印 ⇒ 二根二件
    assert UR.state_name(US.root_dir()) != UR.state_name(str(other))
    assert UR.UC.root_key(US.root_dir()) in UR.state_path(US.root_dir())


def test_E9_real_http_round_trip(env):
    u"""真套接（werkzeug · 127.0.0.1）—— ⛔ 唯 test_client 之自证。"""
    from werkzeug.serving import make_server
    app, sp, _la = env
    srv = make_server("127.0.0.1", 0, app, threaded=True)
    port = srv.server_port
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        def _call(action):
            body = json.dumps({"action": action}).encode("utf-8")
            req = urllib.request.Request("http://127.0.0.1:%d/v9/pa/update" % port, data=body,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        st, d = _call("status")
        assert st == 200 and d["phase"] == "idle", d
        st, d = _call("start")
        assert st == 200 and d["phase"] == "running", d
        assert len(sp) == 1
        with pytest.raises(urllib.error.HTTPError) as ei:
            _call("bogus")
        assert ei.value.code == 400, ei.value
    finally:
        srv.shutdown()


def test_E10_argv_one_source():
    u"""一处定形：唯端出「调器」之 argv（源扫本档 —— ⛔ 手列）。"""
    src = gr_src()
    assert src.count('u"scripts", u"win_pa", u"pa_update.py"') == 1, u"调器之径唯 1 处"
    assert src.count('u"--go", u"--json"') == 1, u"器参唯 1 处"
