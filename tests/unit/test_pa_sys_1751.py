# -*- coding: utf-8 -*-
u"""本机体检（只读 · 七面）之测 —— 承 pm_1750 §二 ／ §四 ／ pm_1751 §二–§四 ／ pm_1753 §二。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_sys_1751.py -q

判据（令 pm_1750 §二.2 ／ §四 ＋ pm_1751 §二 ／ §四 ＋ pm_1753 §二）：
  ⒜ 五件套 —— 每项 `人话 ＋ 读数 ＋ 源 ＋ 结论 ＋ 去处`（＋ `needs_admin`）；每面 `verdict_text` ⛔ 空
  ⒝ 去处之界 —— 一阶段 `kind` 唯 `guide ／ none`（「打开某页」＝ 二阶段 ⇒ ⛔ 起进程）
  ⒞ 四证 —— ⛔ 写盘 ／ ⛔ 改注册表（唯 `KEY_READ`）／ ⛔ 起停服务 ／ ⛔ 提权静默
  ⒟ ⛔ 出机 —— 扫之全程本机（哨兵：封 `socket` 之全族 ⇒ 仍须跑得通）
  ⒠ 本机闸 —— 唯 `127.0.0.1`；远机 ⇒ `403`；未识之面 ⇒ `400`
  ⒡ 照实 —— 取不得 ⇒ `unknown` ＋ 照实之因 ＋ 人去处 ＋ `needs_admin`；⛔ 落 0 ／ ⛔ 空串冒真值
  ⒢ 有界 —— 递归之深与件皆遵 `WALK_MAX_DEPTH` ／ `WALK_MAX_FILES`
  ⒣ 反控 —— 清之险 ⛔ 含「安全」之辞（pm_1753 §二.1）
  ⒤ 监听之三形 —— `127.x`（唯本机）／ `0.0.0.0`（`::`）（全域）／ 他面 ⇒ 三辞各对（pm_1765 §二.4）
"""
from __future__ import annotations

import inspect
import io
import os
import re
import socket
import sys
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import gateway_routes as G  # noqa: E402
from core.pa import sys_face as SF  # noqa: E402

_VERDICTS = {"ok", "warn", "crit", "info", "unknown"}
_KINDS = {"guide", "none"}


@pytest.fixture(autouse=True)
def _fresh():
    SF.reset_cache()
    yield
    SF.reset_cache()


@pytest.fixture()
def client():
    app = Flask(__name__)
    G.register_pa_routes(app)
    app.config["TESTING"] = True
    return app.test_client()


def _local(c, path):
    return c.get(path, environ_base={"REMOTE_ADDR": "127.0.0.1"})


# ⒜ 五件套 ＋ ⒝ 去处之界 ------------------------------------------------------
def test_七面皆成且五件套齐():
    u"""⒜ ＋ ⒝：七面皆回 `ok`；每项五件套齐；每面 `verdict_text` ⛔ 空；`去处.kind` 唯 `guide ／ none`。"""
    for pid in SF.PANELS:
        doc = SF.build(pid, fresh=True)
        assert doc.get("ok") is True, pid
        assert doc.get("panel") == pid
        assert isinstance(doc.get("verdict_text"), str) and doc["verdict_text"].strip(), pid
        assert doc.get("state") in ("ok", "partial", "unavailable"), pid
        assert doc.get("verdict") in _VERDICTS, pid
        items = doc.get("items")
        assert isinstance(items, list) and items, pid
        for it in items:
            for key in ("id", u"人话", u"读数", u"源", u"结论", u"去处", "needs_admin"):
                assert key in it, (pid, key, it)
            assert it[u"结论"] in _VERDICTS, (pid, it)
            assert str(it[u"人话"]).strip() and str(it[u"读数"]).strip() and str(it[u"源"]).strip(), (pid, it)
            assert it[u"去处"].get("kind") in _KINDS, (pid, it)   # 一阶段 ⛔ 起进程
            assert isinstance(it["needs_admin"], bool), (pid, it)


def test_快照与单面同源():
    u"""`snapshot` 之七面 ≡ 单面之七（⛔ 二套读者）。"""
    snap = SF.snapshot(fresh=True)
    assert snap.get("ok") is True
    assert [p.get("panel") for p in snap["panels"]] == list(SF.PANELS)
    assert isinstance(snap.get("text"), str) and snap["text"].strip()   # 可选中复制之纯文本
    for p in snap["panels"]:
        one = SF.build(p["panel"])
        assert sorted(one.keys()) == sorted(p.keys()), p["panel"]
        assert one["state"] == p["state"], p["panel"]


def test_缓存之信():
    u"""第二次取 ⇒ `cached=True` ＋ `age_s >= 0`（⛔ 以缓存冒新读）。"""
    SF.build("disk", fresh=True)
    again = SF.build("disk")
    assert again.get("cached") is True
    assert isinstance(again.get("age_s"), (int, float)) and again["age_s"] >= 0


# ⒠ 本机闸 -------------------------------------------------------------------
def test_本机闸_唯本机(client):
    assert _local(client, "/v9/pa/sys/snapshot").status_code == 200
    assert _local(client, "/v9/pa/sys/disk").status_code == 200
    r = client.get("/v9/pa/sys/snapshot", environ_base={"REMOTE_ADDR": "192.168.3.44"})
    assert r.status_code == 403, r.get_data(as_text=True)[:200]
    r2 = client.get("/v9/pa/sys/disk", environ_base={"REMOTE_ADDR": "10.0.0.7"})
    assert r2.status_code == 403


def test_未识之面_四百(client):
    r = _local(client, "/v9/pa/sys/nope")
    assert r.status_code == 400
    assert r.get_json().get("ok") is False


def test_端之印载器(client):
    u"""印 ＝ `_code_sha16(路由, 真源模块)` ⇒ 非空之 16 位（承 `1018 §一`）。"""
    j = _local(client, "/v9/pa/sys/disk").get_json()
    assert isinstance(j.get(u"印"), str) and re.fullmatch(r"[0-9a-f]{16}", j[u"印"]), j.get(u"印")


def test_面册闸_端已在册():
    u"""pm_1751 §一.4⒞：面之所引须在既有路由集内 ⇒ 本端须「在」（⛔ 悬）。"""
    rs = G._ui_route_set()
    assert "/v9/pa/sys/snapshot" in rs
    assert G._ui_route_known("/v9/pa/sys/snapshot", rs) is True
    assert G._ui_faces_readout().get(u"悬") == {}
# ⒞ 四证（源之扫 · ⛔ 写 ／ ⛔ 改注册表 ／ ⛔ 起停服务 ／ ⛔ 提权静默） --------------
_FORBIDDEN = (
    (r"open\([^)]*['\"]w[ab+']?", u"写盘（open 之写模式）"),
    (r"open\([^)]*['\"]a[+']?", u"写盘（open 之追加模式）"),
    (r"os\.(mkdir|makedirs|remove|unlink|rmdir|rename|replace|chmod|truncate)\s*\(", u"写盘（os 之写族）"),
    (r"shutil\.(rmtree|move|copy|copy2|copyfile|make_archive)\s*\(", u"写盘（shutil 之写族）"),
    (r"winreg\.(SetValue|SetValueEx|CreateKey|CreateKeyEx|DeleteKey|DeleteValue|SaveKey|RestoreKey)", u"改注册表"),
    (r"(Start-Service|Stop-Service|Restart-Service|Set-Service|sc\s+(start|stop|config)|net\s+(start|stop))", u"起停服务"),
    (r"(runas|RunAs|ShellExecute)", u"提权"),
    (r"shell\s*=\s*True", u"shell=True（拼命令）"),
)


def test_四证_源之扫():
    u"""⒞：`sys_face.py` 之源 ⛔ 含写盘 ／ 改注册表 ／ 起停服务 ／ 提权之辞；且须用 `KEY_READ`（唯读）。"""
    src = inspect.getsource(SF)
    hits = [(why, pat) for pat, why in _FORBIDDEN if re.search(pat, src)]
    assert hits == [], hits
    assert "KEY_READ" in src, u"注册表之读须明书 KEY_READ"
    assert "run_hidden" in src, u"子进程须经 core/pa/_proc 之唯一出口"


def test_四证_起程之口唯一():
    u"""⒞：⛔ 本模块直调 `subprocess`（须经 `core/pa/_proc`）。"""
    src = inspect.getsource(SF)
    assert not re.search(r"(?<!\w)subprocess\.", src), u"⛔ 直调 subprocess"
    assert not re.search(r"(?<!\w)Popen\s*\(", src), u"⛔ 直调 Popen"


# ⒟ ⛔ 出机（哨兵：封 socket 之全族 ⇒ 须仍跑得通） ------------------------------
def test_出机之哨兵(monkeypatch):
    u"""⒟：扫之全程 ⛔ 出机 —— 封 `socket` 全族 ⇒ `snapshot` 仍须真跑通（⛔ 抛）。"""
    calls = []

    def _boom(*a, **k):
        calls.append(a)
        raise AssertionError(u"⛔ 出机：本器 ⛔ 许创建／连接套接字")

    for name in ("socket", "create_connection", "socketpair"):
        if hasattr(socket, name):
            monkeypatch.setattr(socket, name, _boom, raising=False)
    monkeypatch.setattr(socket, "getaddrinfo", _boom, raising=False)
    SF.reset_cache()
    snap = SF.snapshot(fresh=True)
    assert snap.get("ok") is True
    assert len(snap.get("panels") or []) == len(SF.PANELS)
    assert calls == [], calls


# ⒡ 照实（取不得 ⇒ unknown ＋ 因 ＋ 人去处 ＋ needs_admin） ----------------------
def test_照实_psutil缺(monkeypatch):
    u"""⒡：`psutil` 缺 ⇒ ⛔ 冒充真值 ⇒ `unknown` ＋ 照实之因 ＋ 人去处 ＋ `needs_admin`。"""
    monkeypatch.setattr(SF, "psutil", None, raising=True)
    doc = SF.build("disk", fresh=True)
    assert doc["state"] == "unavailable"
    assert doc["verdict"] == "unknown"
    assert doc["verdict_text"].strip(), u"⛔ 一片未知（须一句人话）"
    for it in doc["items"]:
        assert it[u"结论"] == "unknown"
        assert u"取不得" in it[u"读数"]
        assert it["needs_admin"] is True
        assert it[u"去处"].get("kind") == "guide"


def test_照实_系统读败不掩(monkeypatch):
    u"""⒡：系统读败（`rc != 0`）⇒ `unknown` ＋ 明书之因 ＋ 人去处（⛔ 落 0 ／ ⛔ 空串）。"""
    monkeypatch.setattr(SF, "_ps_json", lambda *a, **k: (None, u"rc=1"))
    SF.reset_cache()
    for pid in ("windows", "guard", "startup"):
        doc = SF.build(pid, fresh=True)
        assert doc["verdict_text"].strip(), pid
        unk = [i for i in doc["items"] if i[u"结论"] == "unknown"]
        assert unk, pid
        for it in unk:
            assert u"取不得" in it[u"读数"], (pid, it)
            assert it[u"去处"].get("kind") == "guide", (pid, it)


def test_unknown之数入句(monkeypatch):
    u"""pm_1753 §二.2⒞：有取不得者 ⇒ 句末照实报其数（⛔ 以「未见异常」盖之）。"""
    monkeypatch.setattr(SF, "_ps_json", lambda *a, **k: (None, u"rc=1"))
    SF.reset_cache()
    doc = SF.build("windows", fresh=True)
    assert u"取不得" in doc["verdict_text"], doc["verdict_text"]


# ⒢ 有界（深与件） -----------------------------------------------------------
def test_有界_递归之深(tmp_path):
    u"""⒢：逾 `WALK_MAX_DEPTH` 之层 ⛔ 计入（有界 ⇒ ⛔ 无限递归）。"""
    d = tmp_path
    for i in range(SF.WALK_MAX_DEPTH + 3):
        d = d / ("l%d" % i)
    d.mkdir(parents=True)
    (d / "deep.bin").write_bytes(b"x" * 4096)
    top = (tmp_path / "top.bin")
    top.write_bytes(b"y" * 128)
    total, files, _trunc = SF._dir_size(str(tmp_path), SF.time.monotonic() + 5.0)
    assert files == 1, files                     # 唯顶层之件（深处者 ⛔ 计）
    assert total == 128, total
    assert _trunc is True                        # 逾深 ⇒ 照实标「有界之数」


def test_有界_逾窗即止(tmp_path):
    u"""⒢：窗已过 ⇒ 即止（⛔ 无限等）。"""
    (tmp_path / "a.bin").write_bytes(b"z" * 32)
    total, files, trunc = SF._dir_size(str(tmp_path), SF.time.monotonic() - 1.0)
    assert trunc is True
    assert files == 0 and total == 0


# ⒣ 反控：清之险 ⛔ 含「安全」之辞 --------------------------------------------
def test_反控_清之险无一安全之辞():
    u"""pm_1753 §二.1：清之险唯 `未验 ／ 须授权 ／ 建议清` ⇒ ⛔ 「安全」之辞。"""
    SF.reset_cache()
    doc = SF.build("disk_c", fresh=True)
    risks = [it.get(u"清之险") for it in doc["items"] if it.get(u"清之险")]
    assert risks, u"disk_c 须有清之险之项"
    for r in risks:
        assert u"安全" not in r, r
        assert (u"未验" in r) or (u"须授权" in r) or (u"建议清" in r), r
    src = inspect.getsource(SF)
    for bad in (u"可安全", u"安全清除", u"安全地清", u"放心清"):
        assert bad not in src, bad
    # 「一阶段 ⛔ 判可清」之守 —— `可否清` 唯书「待二阶段 ／ 非本器之事」
    for it in doc["items"]:
        if u"可否清" in it:
            assert u"待二阶段" in it[u"可否清"] or u"非本器之事" in it[u"可否清"], it[u"可否清"]


def test_反控_防木马之界():
    u"""pm_1750 §四.2：⛔ 承诺「能杀 ／ 已清」—— 面内须明书本器之界。"""
    SF.reset_cache()
    doc = SF.build("guard", fresh=True)
    blob = doc["text"] + u"".join(it[u"读数"] for it in doc["items"])
    assert u"⛔ 杀毒" in blob or u"⛔ 是杀毒" in blob, blob[:200]
    for it in doc["items"]:
        low = it[u"读数"]
        assert u"已清" not in low and u"木马已" not in low



# ⒤ 反控：监听之三形（pm_1765 §二.4⒞） --------------------------------------
def test_反控_监听三形之辞各对():
    u"""pm_1765 §二.4：喂三形之 `laddr` ⇒ 三辞各对（⛔ 恒「未见」之假阴 ∧ ⛔ 恒「唯本机」之假辞）。"""
    assert SF._listen_shape(u"127.0.0.1") == "local"
    assert SF._listen_shape(u"::1") == "local"
    assert SF._listen_shape(u"0.0.0.0") == "any"
    assert SF._listen_shape(u"::") == "any"
    assert SF._listen_shape(u"10.0.0.5") == "iface"
    cases = [
        ([("127.0.0.1", 5102)], u"唯本机", "ok"),
        ([("0.0.0.0", 5102)], u"全域", "warn"),
        ([("::", 5102)], u"全域", "warn"),
        ([("192.168.3.11", 5102)], u"他面", "warn"),
        ([], u"未见任何 5102 之监听", "info"),
    ]
    for rows, want, want_v in cases:
        txt, lv, guide = SF._listen_verdict(rows)
        assert want in txt, (rows, txt)
        assert lv == want_v, (rows, lv)
        assert str(guide).strip(), rows
        if rows:                       # 有监听 ⇒ ⛔ 报「未见」（假阴）
            assert u"未见" not in txt, (rows, txt)


def test_反控_全域之绑入面(monkeypatch):
    u"""pm_1765 §二.2：实绑 `0.0.0.0` ⇒ 面须报「全域」（⛔ 「未见（服务或未起）」之假阴）。"""
    if SF.psutil is None:
        pytest.skip(u"psutil 缺 ⇒ 本齿不适用")

    class _L(object):
        def __init__(self, ip, port):
            self.ip, self.port = ip, port

    class _C(object):
        def __init__(self, ip, port):
            self.laddr = _L(ip, port)
            self.raddr = None
            self.status = SF.psutil.CONN_LISTEN
            self.pid = 1

    monkeypatch.setattr(SF.psutil, "net_connections",
                        lambda **k: [_C("0.0.0.0", 5102)])
    SF.reset_cache()
    doc = SF.build("net", fresh=True)
    it = [i for i in doc["items"] if i["id"] == "net:ours"][0]
    assert u"0.0.0.0:5102" in it[u"读数"], it[u"读数"]
    assert u"全域" in it[u"读数"], it[u"读数"]
    assert it[u"结论"] == "warn", it
    assert u"未见" not in it[u"读数"], it[u"读数"]
    SF.reset_cache()


def test_反控_防火墙有怎么开之人话():
    u"""pm_1765 §三.2：`guard:fw` 之处去须有「怎么开」之人话（⛔ 唯「请到安全中心」）。"""
    SF.reset_cache()
    doc = SF.build("guard", fresh=True)
    it = [i for i in doc["items"] if i["id"] == "guard:fw"][0]
    lab = (it[u"去处"] or {}).get("label") or u""
    assert u"逐个网络打开" in lab, lab
    assert u"防火墙和网络保护" in lab, lab
