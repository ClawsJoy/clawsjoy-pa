# -*- coding: utf-8 -*-
u"""本机管理（二阶段 · 授权之动作）之测 —— 承 pm_1852 §四.2（准形 ＝ pm_1847 §一）。

以何形调用：
  python -X utf8 -B -m pytest tests/unit/test_sys_act_1852.py -q

判据（令 pm_1847 §一.4／§一.6 ＋ pm_1852 §四.2）：
  ⒜ 二段 —— `dry_run` 缺省 ⇒ **唯回预案**（⛔ 动一物）＋ 一次性 `token`（TTL `120 s`）；
     真跑须 `token`。
  ⒝ 齿五 —— ⛔ `token` ⇒ 拒 ／ 过期 ⇒ 拒 ／ 非白名单 ⇒ 拒 ／ 远机 ⇒ `403` ／ 同 `token` 二次 ⇒ 幂等。
  ⒞ 守四 —— ⛔ 提权静默 ／ 可撤（入 `_trash` · ⛔ 直 `unlink`）／ 幂等 ／ 审计（`sys_act.jsonl`）。
  ⒟ 我加三条 —— 缺省 ⛔ 危险 ／ 清之险三档（⛔「安全」之辞）／ 回执 ⛔ 载本机**绝对径**。
  ⒠ 伴轴 —— `axis="chat"` ⇒ **恒拒**。
  ⒡ 三类 —— 非白名单之 `act` ／ `target` ⇒ 恒 `none`（⛔ 动手）。
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import gateway_routes as G  # noqa: E402
from core.pa import sys_act as SA  # noqa: E402

_ABS = re.compile(r"[A-Za-z]:[\\/]")


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    u"""把**装位**与**仓根**皆指 tmp —— 真盘之 `data/tmp` ／ 真装位 ⛔ 触。"""
    la = tmp_path / "LocalAppData"
    (la / "ClawsJoyPA").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LOCALAPPDATA", str(la))
    monkeypatch.delenv("ProgramData", raising=False)
    monkeypatch.setattr(SA, "_repo_root", lambda: str(tmp_path / "repo"))
    SA.reset_tokens()
    yield tmp_path
    SA.reset_tokens()


@pytest.fixture()
def client():
    app = Flask(__name__)
    G.register_pa_routes(app)
    app.config["TESTING"] = True
    return app.test_client()


def _bucket(tmp, segs):
    p = tmp / "LocalAppData" / "ClawsJoyPA" / Path(*segs)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _mk(p, name, data=b"x", mtime=None):
    f = p / name
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(data)
    if mtime is not None:
        os.utime(f, (mtime, mtime))
    return f


# ⒜ 二段：缺省 ⇒ 唯回预案 ------------------------------------------------
def test_缺省唯回预案_不动一物(_iso):
    b = _bucket(_iso, ("update", "stage"))
    f = _mk(b, "old.zip", b"12345")
    out = SA.act(act="clean", target=u"装位/update/stage", data_dir=str(_iso))
    assert out["ok"] is True and out["dry_run"] is True
    assert out["token"] and out["ttl_s"] == SA.TOKEN_TTL_S
    p = out["预案"]
    assert p["件数"] == 1 and p["合计"] == 5 and p["险级"] == SA.RISK_UNVERIFIED
    assert p["须管理员"] is False and p["逐条"] == [{"径": "old.zip", "字节": 5}]
    assert f.exists(), u"预案 ⛔ 动一物"


def test_缺省之险_不含安全之辞(_iso):
    _bucket(_iso, ("diag",))
    out = SA.act(act="clean", target=u"装位/diag", data_dir=str(_iso))
    assert u"安全" not in out["预案"]["险级"], u"⛔ 出「安全」之辞"


# ⒝ 齿五 ----------------------------------------------------------------
def test_无token_则拒(_iso):
    _bucket(_iso, ("diag",))
    out = SA.act(act="clean", target=u"装位/diag", dry_run=False, token=u"", data_dir=str(_iso))
    assert out["ok"] is False and out["code"] == 403 and u"token" in out[u"因"]


def test_过期则拒(_iso):
    b = _bucket(_iso, ("diag",))
    _mk(b, "a.log", b"x")
    s = SA.act(act="clean", target=u"装位/diag", data_dir=str(_iso), now=1000.0)
    out = SA.act(act="clean", target=u"装位/diag", dry_run=False, token=s["token"],
                 data_dir=str(_iso), now=1000.0 + SA.TOKEN_TTL_S + 1)
    assert out["ok"] is False and out["code"] == 403 and u"过期" in out[u"因"]


def test_非白名单之act则拒(_iso):
    out = SA.act(act="rm_rf", target=u"装位/diag", data_dir=str(_iso))
    assert out["ok"] is False and out["code"] == 400 and u"非白名单" in out[u"因"]


def test_非白名单之target则拒(_iso):
    for tgt in (u"用户文档", u"装位/../..", u"C:/Windows", u""):
        out = SA.act(act="clean", target=tgt, data_dir=str(_iso))
        assert out["ok"] is False and out["code"] == 400, tgt


def test_远机则403(client, _iso):
    r = client.post("/v9/pa/sys/act", json={"act": "clean", "target": u"装位/diag"},
                    environ_base={"REMOTE_ADDR": "10.0.0.5"})
    assert r.status_code == 403, r.status_code


def test_本机可达且回预案(client, _iso):
    _bucket(_iso, ("diag",))
    r = client.post("/v9/pa/sys/act", json={"act": "clean", "target": u"装位/diag"},
                    environ_base={"REMOTE_ADDR": "127.0.0.1"})
    assert r.status_code == 200 and r.get_json()["dry_run"] is True


def test_同token二次_幂等(_iso):
    b = _bucket(_iso, ("update", "stage"))
    _mk(b, "a.zip", b"aaaa", mtime=1000)
    _mk(b, "b.zip", b"bbbb", mtime=2000)
    s = SA.act(act="clean", target=u"装位/update/stage", data_dir=str(_iso), now=5000.0)
    one = SA.act(act="clean", target=u"装位/update/stage", dry_run=False, token=s["token"],
                 data_dir=str(_iso), now=5000.0)
    two = SA.act(act="clean", target=u"装位/update/stage", dry_run=False, token=s["token"],
                 data_dir=str(_iso), now=5000.0)
    assert one["ok"] and one["幂等"] is False
    assert two["ok"] and two["幂等"] is True, u"同 token 二次 ⇒ 回首次之回执"
    assert two["字节"] == one["字节"] and two["回执"][u"件号"] == one["回执"][u"件号"]
    tr = list((b / SA.TRASH_DIRNAME).rglob("*.zip"))
    assert len(tr) == 2, u"⛔ 二删（回收应仍唯 2 件）: %r" % (tr,)


# ⒞ 守四 ----------------------------------------------------------------
def test_可撤_入回收_不直删(_iso):
    b = _bucket(_iso, ("diag",))
    _mk(b, "n1.log", b"111")
    _mk(b, "sub/n2.log", b"2222")
    s = SA.act(act="clean", target=u"装位/diag", data_dir=str(_iso), now=7000.0)
    out = SA.act(act="clean", target=u"装位/diag", dry_run=False, token=s["token"],
                 data_dir=str(_iso), now=7000.0)
    assert out["ok"] is True and out["字节"] == 7
    assert not list(b.glob("*.log")), u"原处 ⛔ 留"
    tr = b / SA.TRASH_DIRNAME
    got = sorted(str(p.relative_to(tr)).replace(os.sep, "/") for p in tr.rglob("*.log"))
    assert len(got) == 2 and any(g.endswith("n1.log") for g in got) and any("sub/n2.log" in g for g in got), got
    assert out["撤之径"] and SA.TRASH_DIRNAME in out["撤之径"]


def test_须留最近一份(_iso):
    b = _bucket(_iso, ("update", "backup"))
    _mk(b, "old.zip", b"o", mtime=1000)
    _mk(b, "new.zip", b"nn", mtime=9000)
    s = SA.act(act="clean", target=u"装位/update/backup", data_dir=str(_iso), now=8000.0)
    assert s["预案"]["件数"] == 1 and s["预案"][u"留之件"] == ["new.zip"]
    out = SA.act(act="clean", target=u"装位/update/backup", dry_run=False, token=s["token"],
                 data_dir=str(_iso), now=8000.0)
    assert (b / "new.zip").exists(), u"最近一份须留"
    assert not (b / "old.zip").exists()


def test_审计落盘(_iso):
    b = _bucket(_iso, ("diag",))
    _mk(b, "a.log", b"x")
    s = SA.act(act="clean", target=u"装位/diag", data_dir=str(_iso), now=9000.0)
    SA.act(act="clean", target=u"装位/diag", dry_run=False, token=s["token"], data_dir=str(_iso), now=9000.0)
    p = Path(str(_iso)) / "sys_act.jsonl"
    assert p.exists(), u"审计须落盘"
    rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert rows and rows[-1]["act"] == "clean" and rows[-1][u"果"] and rows[-1]["target"] == u"装位/diag"
    assert rows[-1]["印"] == s["印"]


def test_须管理员则拒_不提权静默(_iso, monkeypatch):
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.setenv("ProgramData", str(_iso / "ProgramData"))
    root = _iso / "ProgramData" / "ClawsJoyPA" / "diag"
    root.mkdir(parents=True, exist_ok=True)
    (root / "a.log").write_bytes(b"x")
    s = SA.act(act="clean", target=u"装位/diag", data_dir=str(_iso))
    assert s["预案"]["须管理员"] is True
    out = SA.act(act="clean", target=u"装位/diag", dry_run=False, token=s["token"], data_dir=str(_iso))
    assert out["ok"] is False and out["code"] == 403 and u"管理员" in out[u"因"]
    assert (root / "a.log").exists(), u"⛔ 提权静默 ⇒ ⛔ 动"


# ⒟ 回执 ⛔ 载绝对径 ------------------------------------------------------
def test_回执不载本机绝对径(_iso):
    b = _bucket(_iso, ("diag",))
    _mk(b, "a.log", b"x")
    plan = SA.act(act="clean", target=u"装位/diag", data_dir=str(_iso), now=11000.0)
    out = SA.act(act="clean", target=u"装位/diag", dry_run=False, token=plan["token"],
                 data_dir=str(_iso), now=11000.0)
    blob = json.dumps(out, ensure_ascii=False)
    assert not _ABS.search(blob), u"回执 ⛔ 载绝对径: %s" % blob[:300]
    assert u"去哪看" in out["撤之径"] or u"装位" in out["撤之径"]


def test_一类开页_白名单定字面(_iso, monkeypatch):
    seen = []
    monkeypatch.setattr(SA.os, "startfile", lambda t: seen.append(t), raising=False)
    monkeypatch.setattr(SA.os, "name", "nt")
    bad = SA.act(act="open_settings", target="calc", data_dir=str(_iso))
    assert bad["ok"] is False and bad["code"] == 400
    ok = SA.act(act="open_settings", target="storagesense", data_dir=str(_iso))
    assert ok["ok"] is True
    run = SA.act(act="open_settings", target="storagesense", dry_run=False, token=ok["token"],
                 data_dir=str(_iso))
    assert run["ok"] is True and seen == ["ms-settings:storagesense"], seen


# ⒠ 陪伴轴 --------------------------------------------------------------
def test_陪伴轴恒拒(_iso):
    out = SA.act(act="clean", target=u"装位/diag", axis="chat", data_dir=str(_iso))
    assert out["ok"] is False and out["code"] == 403 and u"陪伴" in out[u"因"]


# ⒡ 三类 ----------------------------------------------------------------
def test_三类恒不动(_iso):
    u"""用户文档 ／ 注册表 ／ 服务起停 ⇒ 恒 `none`（⛔ 入白名单）。"""
    for tgt in (u"用户文档", u"注册表", u"服务起停", u"卸载"):
        assert SA.buckets().get(tgt) is None
        out = SA.act(act="clean", target=tgt, data_dir=str(_iso))
        assert out["ok"] is False and out["code"] == 400
