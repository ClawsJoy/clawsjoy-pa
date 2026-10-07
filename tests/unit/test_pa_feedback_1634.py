# -*- coding: utf-8 -*-
u"""pm_1634（丙-P0 · 留言板 ＋ 一键诊断）之测 —— 技术总监席 f202f89 · 2026-10-07。

老板之批（逐字）：「批，增加留言板，先用局域网内测，但是客服 Agent 需要跟上」
⇒ 本件之尺（pm_1634 §三）：**⛔ 出机** ／ **脱敏** ／ **闭环** ／ **勾选默认 ⛔ 全选** ／
   **⛔ 恒虚之支**（⛔ 书「在线客服」）。

以何形调用（判通 ／ 断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_feedback_1634.py -q

判据：
  ⒜ 落点声明：`local` ＋ `outbound=False`（默认）∧ env 覆 ⇒ 记其出（`origin`）
  ⒝ 收件 ／ 取件：落本机（`件.json` ＋ `附件/`）∧ 列新者先 ∧ 读全
  ⒞ 逐项勾选：**缺省全 ⛔ 勾**（照实记 ⇒ ⛔ 默认带）
  ⒟ 拒件：无题 ／ 无文 ／ 附件名非法（路径穿越）⇒ `FeedbackError`（人话）
  ⒠ 客服席闭环：发 ⇒ 读 ⇒ 回话 ⇒ 读显（`state=replied`）
  ⒡ **⛔ 出机（硬）**：三模块源码**⛔ 引**网络之件（结构齿）
  ⒢ 脱敏：`sk-…` ／ 哨兵（env 之像密钥者）⇒ 掩
  ⒣ 诊断包：白名单五源 ∧ **哨兵 ⛔ 在包**（含 `data/` 之内容）∧ ⛔ 上传
  ⒤ 端面：`/v9/pa/feedback*` ／ `/v9/pa/diagnostics` 之真路（Flask 测试客）
"""
import io
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.lib import feedback_target as FT      # noqa: E402
from core.pa import diagnostics as DG           # noqa: E402
from core.pa import feedback_store as FS        # noqa: E402

SENTINEL = u"CJPA-SENTINEL-9f3a2b7c1d"


@pytest.fixture()
def fed(tmp_path, monkeypatch):
    u"""收件目录 ＝ tmp（⛔ 触真仓之 `data/`）—— 一处定形（`PA_FEEDBACK_DIR`）。"""
    d = tmp_path / "fb"
    monkeypatch.setenv(FT.ENV[u"dir"], str(d))
    monkeypatch.delenv(FT.ENV[u"mode"], raising=False)
    monkeypatch.delenv(FT.ENV[u"relay_url"], raising=False)
    return d


def test_target_one_place_default_local_no_outbound(fed):
    u"""(a) 默认 ＝ local ∧ 出机 False ∧ 提示照实（⛔ 自撰）。"""
    src = FT.load()
    assert src[u"mode"] == u"local" and src[u"outbound"] is False
    assert src[u"dir"] == str(fed)
    assert u"只存在你这台机器上" in FT.notice(src)
    assert FT.feedback_dir(None, src) == str(fed)


def test_notice_local_carries_outlet(fed):
    u"""(a) 我裁（pm_1647 §一.1）：常驻提示须含**去处**之半句（⛔ 唯言「⛔ 出机」而不言「如何到我方」）。
    —— 「凡不可用必有因 ＋ 去处」；面（web）唯取此字（CW 之齿 F1 证「⛔ 自撰」）。
    """
    assert u"只存在你这台机器上" in FT.NOTICE_LOCAL, FT.NOTICE_LOCAL
    assert u"⛔ 出机" in FT.NOTICE_LOCAL, FT.NOTICE_LOCAL
    assert (u"上门取" in FT.NOTICE_LOCAL) or (u"复制给我们" in FT.NOTICE_LOCAL), FT.NOTICE_LOCAL
    src = FT.load()
    assert FT.notice(src) == FT.NOTICE_LOCAL, FT.notice(src)
    assert u"上门取" in FT.face()[u"notice"], FT.face()[u"notice"]


def test_target_env_override_records_origin(fed, monkeypatch):
    u"""(a) env 覆 ⇒ `origin` 记其出 ∧ `relay` ＋ 空 url ⇒ 仍 ⛔ 出机（⛔ 假在线）。"""
    monkeypatch.setenv(FT.ENV[u"mode"], u"relay")
    src = FT.load()
    assert src[u"mode"] == u"relay" and src[u"origin"][u"mode"].startswith(u"env:")
    assert src[u"outbound"] is False, u"relay 而无 url ⇒ ⛔ 得送出（⛔ 假在线）"
    monkeypatch.setenv(FT.ENV[u"relay_url"], u"http://relay.local/x")
    assert FT.load()[u"outbound"] is True


def test_submit_list_read_and_default_consent(fed):
    u"""(b)+(c) 收件 ／ 列 ／ 读 ∧ 勾选缺省全 ⛔ 勾（照实记）。"""
    att = {u"name": u"截屏.png", u"b64": __import__(u"base64").b64encode(b"PNGDATA").decode(u"ascii")}
    fid, doc, rows = FS.submit(None, {u"title": u"起不来", u"body": u"点开一片白",
                                      u"contact": u"张三", u"attach": [att]})
    assert os.path.isfile(FS.item_json(None, fid))
    assert os.path.isfile(os.path.join(FS.attach_dir(None, fid), u"截屏.png"))
    assert doc[u"consent"] == {b: False for b in FS.CONSENT_BUSES}, u"缺省须全 ⛔ 勾"
    assert doc[u"schema"] == FS.SCHEMA and doc[u"target"][u"outbound"] is False
    assert rows

    fid2, _d2, _r2 = FS.submit(None, {u"title": u"第二件", u"body": u"x",
                                      u"consent": {u"logs": True}})
    lst = FS.list_items(None)
    assert [x[u"id"] for x in lst][:2] == [fid2, fid], u"列须新者先"
    assert lst[1][u"attach_n"] == 1 and lst[1][u"has_reply"] is False
    it = FS.read_item(None, fid)
    assert it[u"reply"] is None and it[u"title"] == u"起不来" and it[u"consent"][u"logs"] is False
    assert FS.read_item(None, u"20200101-000000-dead") is None


def test_submit_rejects_bad_input(fed):
    u"""(d) 拒件（人话 · 承「凡不可用必有因 ＋ 去处」）。"""
    for bad, kw in ((u"无题", {u"title": u"", u"body": u"x"}),
                    (u"无文", {u"title": u"x", u"body": u" "}),
                    (u"题过长", {u"title": u"x" * (FS.MAX_TITLE + 1), u"body": u"x"})):
        with pytest.raises(FS.FeedbackError):
            FS.submit(None, kw)
    with pytest.raises(FS.FeedbackError) as e:
        FS.submit(None, {u"title": u"t", u"body": u"b",
                         u"attach": [{u"name": u"..\\..\\evil.exe", u"b64": u""}]})
    assert u"附件之名非法" in str(e.value)
    with pytest.raises(FS.FeedbackError):
        FS.write_reply(None, u"20200101-000000-dead", u"在")


def test_reply_loop(fed):
    u"""(e) 客服席之闭环：发 ⇒ 读 ⇒ 回话 ⇒ 读显（照今日原型之黄框）。"""
    fid, _doc, _rows = FS.submit(None, {u"title": u"求助", u"body": u"模型下载卡住"})
    rows = FS.write_reply(None, fid, u"已收到，请看 logs 之尾", by=u"客服席")
    assert rows
    it = FS.read_item(None, fid)
    assert it[u"state"] == u"replied" and it[u"reply"][u"text"].startswith(u"已收到")
    assert it[u"reply"][u"by"] == u"客服席"
    assert FS.list_items(None)[0][u"has_reply"] is True


def test_no_network_in_modules():
    u"""(f) **⛔ 出机（硬）**：三模块之源码 ⛔ 引网络之件（结构齿 · ⛔ 赖人眼）。"""
    for mod in (FS, FT, DG):
        ok, hits = mod.source_scan()
        assert ok, (mod.__name__, hits)
    p = ROOT / u"core" / u"pa" / u"gateway_routes.py"
    txt = io.open(str(p), encoding=u"utf-8").read()
    blk = txt.split(u"丙-P0：留言板", 1)[1].split(u"    app.register_blueprint(bp)", 1)[0]
    for bad in (u"urllib", u"requests", u"socket", u"httpx", u"http.client"):
        assert bad not in blk, u"丙-P0 之端 ⛔ 得引 %s" % bad


def test_scrub_masks_secrets(monkeypatch):
    u"""(f) 脱敏：形（`sk-…` ／ `key=…`／`Bearer …`／`AKIA…`）＋ 哨兵逐字掩。"""
    monkeypatch.setenv(u"PA_DEMO_API_KEY", SENTINEL)
    s = FS.scrub(u"a sk-abcdef123456 b api_key=zzzzzzzz c Bearer qqqqqqqq d AKIAIOSFODNN7EXAMPLE "
                 u"e " + SENTINEL, FS.sentinels())
    for leak in (u"sk-abcdef123456", u"zzzzzzzz", u"qqqqqqqq", u"AKIAIOSFODNN7EXAMPLE", SENTINEL):
        assert leak not in s, (leak, s)
    assert s.count(u"***") >= 5


def test_diag_pack_whitelist_and_sentinel(tmp_path, monkeypatch):
    u"""(g) 诊断包：白名单五源 ∧ 哨兵（env ＋ 日志 ＋ `data/`）**⛔ 在包** ∧ ⛔ 上传。"""
    monkeypatch.setenv(u"PA_DEMO_TOKEN", SENTINEL)
    root = tmp_path / "pa"
    (root / "logs").mkdir(parents=True)
    (root / "data").mkdir()
    io.open(str(root / "logs" / "gateway.log"), u"w", encoding=u"utf-8").write(
        u"boot ok\nsecret token=%s\n" % SENTINEL)
    io.open(str(root / "data" / "secret.txt"), u"w", encoding=u"utf-8").write(u"USERDATA " + SENTINEL)
    io.open(str(root / "version.json"), u"w", encoding=u"utf-8").write(
        json.dumps({u"version": u"9.0.0", u"channel": u"internal"}))
    zp, rows = DG.build(root=str(root), health={u"status": u"healthy", u"note": u"token=%s" % SENTINEL},
                        port=5102, out_root_dir=str(tmp_path / "out"))
    assert rows and os.path.isfile(zp)
    names = DG.members(zp)
    for want in (u"README.txt", u"version.json", u"装根清单.txt", u"health.json", u"环境.txt"):
        assert want in names, names
    import zipfile
    with zipfile.ZipFile(zp) as z:
        blob = b""
        for n in z.namelist():
            blob += z.read(n)
    t = blob.decode(u"utf-8", u"replace")
    assert SENTINEL not in t, u"哨兵 ⛔ 得入包（env ／ 日志 ／ data/ 皆须脱）"
    assert u"USERDATA" not in t, u"`data/` 之内容 ⛔ 得入包"
    assert u"9.0.0" in t
    assert DG.out_root(str(root)).endswith(os.path.join(u"ClawsJoyPA", u"diag"))


def test_ends_flask(fed, tmp_path):
    u"""(h) 端面之真路（Flask 测试客 · ⛔ 拦截 · ⛔ 打桩）。"""
    from flask import Flask

    from core.pa.gateway_routes import register_pa_routes

    app = Flask(__name__)
    register_pa_routes(app)
    c = app.test_client()

    r = c.get(u"/v9/pa/feedback/target")
    assert r.status_code == 200
    t = r.get_json()
    assert t[u"ok"] is True and t[u"outbound"] is False and u"只存在你这台机器上" in t[u"notice"]
    assert t[u"consent_buses"] == list(FS.CONSENT_BUSES) and t[u"resolved_dir"] == str(fed)

    import base64
    r = c.post(u"/v9/pa/feedback", json={u"title": u"端面之件", u"body": u"经端提交",
                                         u"attach": [{u"name": u"a.txt",
                                                      u"b64": base64.b64encode(b"hi").decode(u"ascii")}]})
    assert r.status_code == 200, r.get_data(as_text=True)
    fid = r.get_json()[u"id"]
    assert r.get_json()[u"outbound"] is False and r.get_json()[u"attach_n"] == 1

    r = c.post(u"/v9/pa/feedback", json={u"title": u"", u"body": u"x"})
    assert r.status_code == 400 and u"题目" in r.get_json()[u"error"]

    r = c.get(u"/v9/pa/feedback")
    assert r.status_code == 200 and r.get_json()[u"items"][0][u"id"] == fid

    assert c.get(u"/v9/pa/feedback/%s" % fid).status_code == 200
    assert c.get(u"/v9/pa/feedback/nope-not-here").status_code == 404

    r = c.post(u"/v9/pa/feedback/%s/reply" % fid, json={u"text": u"收到", u"by": u"客服席"})
    assert r.status_code == 200 and r.get_json()[u"replied"] is True
    it = c.get(u"/v9/pa/feedback/%s" % fid).get_json()[u"item"]
    assert it[u"reply"][u"text"] == u"收到" and it[u"state"] == u"replied"

    r = c.post(u"/v9/pa/diagnostics", json={})
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    assert d[u"uploaded"] is False and os.path.isfile(d[u"pack"]) and d[u"bytes"] > 0
    assert u"README.txt" in d[u"members"]

def test_read_one_place_health_carries_feedback(fed):
    u"""(i) 我裁（pm_1640 §一.2）：**面之读数唯 `/health`** —— 落点声明之形**唯自一处**
    （`feedback_target.face()`）⇒ `/health.feedback` ≡ `/v9/pa/feedback/target`（⛔ 二处各写）。
    """
    from flask import Flask

    from core.pa.gateway_routes import register_pa_routes

    app = Flask(__name__)
    register_pa_routes(app)
    tgt = app.test_client().get(u"/v9/pa/feedback/target").get_json()
    tgt.pop(u"ok", None)

    from core.routes.system_routes import system_bp
    app2 = Flask(__name__)
    app2.register_blueprint(system_bp)
    h = app2.test_client().get(u"/health").get_json()
    assert u"feedback" in h, sorted(h.keys())
    assert h[u"feedback"] == tgt, (h[u"feedback"], tgt)
    assert h[u"feedback"][u"outbound"] is False
    assert u"只存在你这台机器上" in h[u"feedback"][u"notice"]
    assert h[u"feedback"][u"consent_buses"] == list(FS.CONSENT_BUSES)


def test_diag_health_member_is_json_object_with_note_why(tmp_path):
    u"""(g2) 我裁（pm_1643 §一.2）：诊断包之 `health.json` ⇒ **一 JSON 对象**（`json.loads` **一次**即得
    `dict` —— ⛔ 双重编码）∧ 机器面之因（`boot.download.note_why`）**⛔ 丢**。
    正控：所传 `/health` 之键（尤 `note` ／ `note_why`）逐字在包之对象中。
    反控（**我自逮之旧病**）：旧稿 ＝ `json.dumps(scrub(json.dumps(...)))` ⇒ 件为「JSON **字串**」
      ⇒ 客服席直读即败（其 `type` 为 `str` · ⛔ `dict`）。
    """
    import zipfile
    root = tmp_path / "pa_h"
    root.mkdir()
    h = {u"status": u"healthy",
         u"boot": {u"download": {u"measured": True, u"done_bytes": 83178821, u"total_bytes": None,
                                 u"frac": None, u"eta_s": None,
                                 u"note": u"总长不可量（后端未给）", u"note_why": u"TimeoutError"}}}
    zp, rows = DG.build(root=str(root), health=h, port=5102, out_root_dir=str(tmp_path / "out_h"))
    assert os.path.isfile(zp), rows
    with zipfile.ZipFile(zp) as z:
        doc = json.loads(z.read(u"health.json").decode(u"utf-8"))
    assert isinstance(doc, dict), u"`health.json` 须为**对象**（⛔ 双重编码）：%r" % type(doc)
    dl = doc[u"boot"][u"download"]
    assert dl[u"note_why"] == u"TimeoutError", dl
    assert dl[u"note"] == u"总长不可量（后端未给）", dl
    assert dl[u"done_bytes"] == 83178821, dl
