# -*- coding: utf-8 -*-
u"""pm_1616 之测：起服「准备中」之可读读数（态 / 相 / 量 / 失败显形）。

以何形调用（判通 / 断须附）：
  python -X utf8 -B -m pytest tests/unit/test_boot_progress_1616.py -q

判据：
  ⒜ 态三：begin ⇒ starting；mark_ready ⇒ ready；fail ⇒ failed ＋ 因 ＋ 去处
  ⒝ 相：入相 ⇒ 前相自动 done；done / total ⇒ progress 单调
  ⒞ 量：量不得 ⇒ note 明书「不可量」（⛔ 猜）；量得 ⇒ frac ＋ eta
  ⒟ 齿：⛔ 知总长 ⇒ ⛔ 出 eta（⛔ 猜）
  ⒠ 端：GET /health 载 boot（门开即可答 · ⛔ 等重初始化）
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.gateway import boot_progress as BP  # noqa: E402


@pytest.fixture(autouse=True)
def _reset():
    BP.boot_progress.reset()
    yield
    BP.boot_progress.reset()


def test_states_and_progress():
    u"""(a)+(b)：态与相。"""
    s = BP.boot_progress.snapshot()
    assert s["state"] == "starting" and s["phases_total"] == 0
    BP.boot_progress.begin(["http_listen", "kb", "ready"])
    BP.boot_progress.set_phase("http_listen")
    s = BP.boot_progress.snapshot()
    assert s["phases_total"] == 3 and s["phase"] == "http_listen"
    assert s["phases"][0]["state"] == "running" and s["progress"] == 0
    assert s["since_s"] is not None and s["phase_since_s"] is not None
    BP.boot_progress.set_phase("kb")
    s = BP.boot_progress.snapshot()
    assert s["phases"][0]["state"] == "done" and s["phases"][1]["state"] == "running"
    assert s["progress"] == 33
    BP.boot_progress.mark_ready()
    s = BP.boot_progress.snapshot()
    assert s["state"] == "ready" and s["progress"] == 100 and s["phase"] == "ready"


def test_phase_not_in_plan_is_appended():
    u"""(b) 齿：相 ⛔ 在序 ⇒ 照实追加（⛔ 静默丢）。"""
    BP.boot_progress.begin(["a"])
    BP.boot_progress.set_phase("b")
    s = BP.boot_progress.snapshot()
    assert [x["name"] for x in s["phases"]] == ["a", "b"]
    assert s["phases_total"] == 2


def test_fail_carries_reason_and_hint():
    u"""(a) 失败必附「因 ＋ 去处」（承「凡不可用必有因＋去处」）。"""
    BP.boot_progress.begin(["kb"])
    BP.boot_progress.fail("下向量模型失败（断网）", "联网后重启 · 或看 logs")
    s = BP.boot_progress.snapshot()
    assert s["state"] == "failed"
    assert s["failed"]["reason"] and s["failed"]["hint"]


def test_download_unmeasurable_when_absent(tmp_path, monkeypatch):
    u"""(c) 量不得 ⇒ 明书「不可量」。"""
    monkeypatch.delenv(BP.ONNX_TOTAL_ENV, raising=False)
    d = BP.download_face(str(tmp_path / "nope.tar.gz"), None, None)
    assert d["measured"] is False and d["done_bytes"] is None
    assert "不可量" in d["note"]


def test_download_measured_frac_and_eta(tmp_path, monkeypatch):
    u"""(c) 量得 ⇒ done / total / frac / eta。"""
    f = tmp_path / "onnx.tar.gz"
    f.write_bytes(b"x" * 500)
    d = BP.download_face(str(f), 1000, 10)
    assert d["measured"] is True and d["done_bytes"] == 500 and d["total_bytes"] == 1000
    assert d["frac"] == 0.5 and d["eta_s"] == 10
    f.write_bytes(b"x" * 1000)
    d2 = BP.download_face(str(f), 1000, 10)
    assert d2["note"] == "已毕（缓存件齐）" and d2["eta_s"] is None


def test_download_no_total_no_eta(tmp_path, monkeypatch):
    u"""(d) 齿：⛔ 知总长 ⇒ total 为 None ∧ ⛔ 出 eta（⛔ 猜）。"""
    monkeypatch.delenv(BP.ONNX_TOTAL_ENV, raising=False)
    f = tmp_path / "onnx.tar.gz"
    f.write_bytes(b"x" * 500)
    d = BP.download_face(str(f), None, 10)
    assert d["total_bytes"] is None and d["eta_s"] is None and d["frac"] is None


def test_health_carries_boot():
    u"""(e) 端：GET /health 载 boot（唯读内存之态）。"""
    from flask import Flask

    from core.routes.system_routes import system_bp

    app = Flask(__name__)
    app.register_blueprint(system_bp)
    r = app.test_client().get("/health")
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    assert "boot" in d
    for k in ("state", "phase", "since_s", "progress", "phases", "download", "failed"):
        assert k in d["boot"], k
    assert d["boot"]["state"] in ("starting", "ready", "failed")
