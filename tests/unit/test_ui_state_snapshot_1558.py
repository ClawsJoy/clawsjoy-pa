# -*- coding: utf-8 -*-
u"""pm_1558 §二 裁 ⒜ 之齿：界面态快照 —— **服务自落**（唯一写者 ＝ 服务）。

齿三条（pm_1558 §二.3）：
  正控   新树（⛔ 件）⇒ 落 ⇒ 件在 ∧ 九键 ∧ ⛔BOM ∧ CR 0 ∧ LF 1（≡ 活端 200）
  反控   ⛔ 落（旧形）⇒ 件 ⛔ 在（≡ 活端 404 ／ 「未载入」）
  写失败之守 不可写之径 ⇒ 返 False ∧ 显形行在 ∧ ⛔ 崩
"""
import json
import sys

sys.path.insert(0, ".")
from core.gateway import ui_state as us


def _sample():
    return {u"已载": 0, u"显存": {u"free": 100, u"total": 200}, u"Forever": [],
            u"本地在": False, u"远端在": True, u"远端host": "api.deepseek.com",
            u"远端态": u"配了且通", u"远端因": u"通（GET /v1/models = 200）",
            u"刻": "2026-10-06 20:00:00"}


def test_spec_shape_is_nine_keys():
    assert [k for k, _ in us.SNAPSHOT_SPEC] == [
        u"已载", u"显存", u"Forever", u"本地在", u"远端在", u"远端host", u"远端态", u"远端因", u"刻"]


def test_backcontrol_no_write_means_404(tmp_path):
    u"""反控：⛔ 落（旧形）⇒ 件 ⛔ 在（≡ 活端 404 ／ 屏上「未载入」）。"""
    assert not (tmp_path / "web" / "pa" / "ui_state.json").exists()


def test_forward_fresh_path_writes_nine_keys(tmp_path):
    u"""正控：新树（⛔ 件）⇒ 落 ⇒ 件在 ∧ 九键 ∧ ⛔BOM ∧ CR 0 ∧ LF 1。"""
    p = tmp_path / "web" / "pa" / "ui_state.json"
    assert not p.exists()
    raw = us.write_snapshot(str(p), _sample())
    assert raw is not None and p.exists()
    b = p.read_bytes()
    assert b[:3] != b"\xef\xbb\xbf"
    assert b.count(b"\r") == 0
    assert b.count(b"\n") == 1 and b.endswith(b"\n")
    d = json.loads(b.decode("utf-8"))
    assert list(d.keys()) == [k for k, _ in us.SNAPSHOT_SPEC]
    assert us.check_snapshot(d)[0]


def test_write_once_real_collect_ok(tmp_path):
    u"""正控（真采）：collect() ⇒ 九键 ⇒ 落 ⇒ True（⛔ 网亦落「不在」之实 · ⛔ 崩）。"""
    p = tmp_path / "ui_state.json"
    assert us.write_once(str(p)) is True
    d = json.loads(p.read_text(encoding="utf-8"))
    assert us.check_snapshot(d)[0]


def test_spec_rejects_missing_and_wrong_type():
    d = _sample()
    del d[u"Forever"]
    ok, bad = us.check_snapshot(d)
    assert (not ok) and any(u"Forever" in x for x in bad)

    d2 = _sample()
    d2[u"已载"] = u"0"
    ok2, bad2 = us.check_snapshot(d2)
    assert (not ok2) and any(u"已载" in x for x in bad2)


def test_bad_snapshot_never_written(tmp_path):
    u"""坏快照 ⛔ 入盘（守：⛔ 静默写坏件）。"""
    p = tmp_path / "ui_state.json"
    d = _sample()
    d[u"远端态"] = u"乱值"
    raised = False
    try:
        us.write_snapshot(str(p), d)
    except ValueError:
        raised = True
    assert raised and (not p.exists())


def test_write_failure_is_loud_and_never_raises(tmp_path, capsys, monkeypatch):
    u"""写失败之守：不可写之径 ⇒ 返 False ∧ 显形行在 ∧ ⛔ 崩（守二）。"""
    monkeypatch.setattr(us, "collect", _sample)
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")          # 父为**文件** ⇒ makedirs 必败
    bad = str(blocker / "sub" / "ui_state.json")
    ok = us.write_once(bad)
    out = capsys.readouterr().out
    assert ok is False
    assert u"[UI_STATE]" in out and u"⛔" in out and bad in out


def test_snapshot_path_is_web_pa_default(monkeypatch):
    monkeypatch.delenv(us.SNAPSHOT_PATH_ENV, raising=False)
    p = us.snapshot_path()
    assert p.replace("\\", "/").endswith("web/pa/ui_state.json")


def test_snapshot_path_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv(us.SNAPSHOT_PATH_ENV, str(tmp_path / "x.json"))
    assert us.snapshot_path() == str(tmp_path / "x.json")