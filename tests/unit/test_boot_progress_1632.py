# -*- coding: utf-8 -*-
u"""pm_1632 §二 之测：向量模型之**总长之真源**（一次 HEAD 取 Content-Length）。

病（CW 一手 · pm_1631）：全仓**无人设** `PA_ONNX_TOTAL_BYTES`（`rg` 命中唯二 · 皆在
`boot_progress.py` 自身）∧ `set_download()` ⛔ 传 `total_bytes` ⇒ 生产 `total_bytes ≡ null`
⇒ 面之「按字节之条」支**恒 ⛔ 可达**（＝ 许之能而 ⛔ 至）；且 `measured=true ∧ total 缺`
⇒ `note` 空 ⇒ 面**静默**略去「已下 X MB」（弃已量之真读数）⇒ ⭐ 本件裁 ⒜ 治之。

以何形调用（判通 / 断须附）：
  python -X utf8 -B -m pytest tests/unit/test_boot_progress_1632.py -q

判据：
  ⒜ 真源：`onnx_model_url()` ≡ 库内之常量（一处定形 · ⛔ 硬编）∧ `onnx_cache_path()` 同源
  ⒝ 正控：HEAD 得 ⇒ 真字节（以本机临端之定长件验 · ⛔ 赖公网）
  ⒞ 反控：死端 ／ 无址 ／ 无 Content-Length ⇒ `total=None` ∧ `note` ＝「总长不可量（后端未给）」
         ∧ ⛔ 抛（⛔ 阻准备）
  ⒟ 唯一次：重入 `start_download_probe` ⇒ False（⛔ 每相各取）
  ⒠ ⛔ 阻门：探为**后台线程**（调用即刻返 · 即死端亦 ⛔ 阻）
  ⒡ ⛔ 擦：`set_download()` 传 ⛔ 传 total ⇒ 探得者存（一处定形）
  ⒢ 面：`/health` 之 `boot.download` 载 `note`（承「界面态显真读数」· ⛔ 静默略去）
"""
import sys
import threading
import time
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


def _serve(tmp_path, n_bytes):
    u"""本机临端（⛔ 赖公网）—— `SimpleHTTPRequestHandler` 之 `do_HEAD` 自报 Content-Length。"""
    import http.server
    import socketserver

    (tmp_path / "onnx.tar.gz").write_bytes(b"x" * n_bytes)
    handler = lambda *a, **k: http.server.SimpleHTTPRequestHandler(*a, directory=str(tmp_path), **k)  # noqa: E731
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, u"http://127.0.0.1:%d/onnx.tar.gz" % httpd.server_address[1]


def test_model_url_is_library_constant():
    u"""(a) 真源：址唯自（唯 ≡）库内之常量 —— 一处定形（⛔ 硬编 ／ ⛔ 二处各写）。"""
    lib = pytest.importorskip(u"chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2")
    assert BP.onnx_model_url() == str(lib.ONNXMiniLM_L6_V2.MODEL_DOWNLOAD_URL)
    assert BP.onnx_cache_path() == str(lib.ONNXMiniLM_L6_V2.DOWNLOAD_PATH
                                    / lib.ONNXMiniLM_L6_V2.ARCHIVE_FILENAME)


def test_head_yields_true_bytes(tmp_path):
    u"""(b) 正控：一次 HEAD ⇒ 真字节（附 note 空）。"""
    httpd, url = _serve(tmp_path, 4096)
    try:
        tot, note = BP.probe_total_bytes(url, timeout=5.0)
        assert tot == 4096, (tot, note)
        assert note == u""
    finally:
        httpd.shutdown()


def test_head_dead_end_and_no_url_and_no_length(tmp_path):
    u"""(c) 反控：死端 ／ 无址 ／ 无 Content-Length ⇒ None ＋ 人话（⛔ 抛）。"""
    tot, note = BP.probe_total_bytes(u"http://127.0.0.1:1/onnx.tar.gz", timeout=0.5)
    assert tot is None and u"总长不可量" in note, (tot, note)
    tot2, note2 = BP.probe_total_bytes(u" ", timeout=0.5)
    assert tot2 is None and u"总长不可量" in note2, (tot2, note2)
    assert note2 == BP.UNMEASURABLE_TOTAL_NOTE + u"（⛔ 知模型址）"
    # 无 Content-Length 者（本机之 204 应答）
    import http.server
    import socketserver

    class _NoLen(http.server.BaseHTTPRequestHandler):
        def do_HEAD(self):                                        # noqa: N802
            self.send_response(200)
            self.end_headers()

        def log_message(self, *a):                                # noqa: N802,A003
            return

    httpd = socketserver.TCPServer(("127.0.0.1", 0), _NoLen)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        tot3, note3 = BP.probe_total_bytes(u"http://127.0.0.1:%d/x" % httpd.server_address[1], timeout=5.0)
        assert tot3 is None and note3 == BP.UNMEASURABLE_TOTAL_NOTE, (tot3, note3)
    finally:
        httpd.shutdown()


def test_probe_is_one_shot_and_non_blocking(tmp_path):
    u"""(d)+(e) 唯一次（重入 ⇒ False）∧ 后台（即死端亦 ⛔ 阻调用）。"""
    t0 = time.time()
    assert BP.boot_progress.start_download_probe(u"http://192.0.2.1/onnx.tar.gz", timeout=5.0) is True
    assert time.time() - t0 < 1.0, u"⛔ 阻门（须即刻返）"
    assert BP.boot_progress.start_download_probe(u"http://192.0.2.1/onnx.tar.gz") is False


def test_probe_fills_total_and_set_download_keeps_it(tmp_path):
    u"""(f)+(g) 探得 ⇒ 补真源；`set_download` ⛔ 擦之；⛔ 得 ⇒ note 明书（⛔ 静默）。"""
    httpd, url = _serve(tmp_path, 2048)
    f = tmp_path / "onnx.tar.gz"
    try:
        assert BP.boot_progress.start_download_probe(url, timeout=5.0) is True
        for _ in range(50):
            if BP.boot_progress.snapshot()[u"download"][u"total_bytes"]:
                break
            time.sleep(0.1)
        BP.boot_progress.set_phase(u"vector_model_download")
        BP.boot_progress.set_download(str(f))                    # ⛔ 传 total ⇒ ⛔ 擦探得者
        d = BP.boot_progress.snapshot()[u"download"]
        assert d[u"total_bytes"] == 2048 and d[u"done_bytes"] == 2048
        assert d[u"frac"] == 1.0 and d[u"note"] == u"已毕（缓存件齐）"
    finally:
        httpd.shutdown()

    BP.boot_progress.reset()
    assert BP.boot_progress.start_download_probe(u"http://127.0.0.1:1/x", timeout=0.5) is True
    for _ in range(50):
        if BP.boot_progress.snapshot()[u"download"][u"note"]:
            break
        time.sleep(0.1)
    BP.boot_progress.set_download(str(f))                        # 量得 ／ ⛔ 知总长
    d2 = BP.boot_progress.snapshot()[u"download"]
    assert d2[u"done_bytes"] == 2048 and d2[u"total_bytes"] is None and d2[u"frac"] is None
    assert d2[u"note"] == BP.UNMEASURABLE_TOTAL_NOTE, d2


def test_download_face_note_when_total_unknown(tmp_path, monkeypatch):
    u"""(g) 齿：有量⛔总长 ⇒ note ＝ 明书（⛔ 静默略去）—— 纯函数之面。"""
    monkeypatch.delenv(BP.ONNX_TOTAL_ENV, raising=False)
    f = tmp_path / "onnx.tar.gz"
    f.write_bytes(b"x" * 512)
    d = BP.download_face(str(f), None, 10)
    assert d[u"measured"] is True and d[u"total_bytes"] is None and d[u"frac"] is None
    assert d[u"note"] == BP.UNMEASURABLE_TOTAL_NOTE, d
    d2 = BP.download_face(str(f), None, 10, u"总长不可量（后端未给）（URLError）")
    assert d2[u"note"] == u"总长不可量（后端未给）（URLError）", d2


def test_health_download_carries_note():
    u"""(h) 端：`/health` 之 `boot.download` 载 `note`（唯一读数面 · ⛔ 副作用）。"""
    from flask import Flask

    from core.routes.system_routes import system_bp

    app = Flask(__name__)
    app.register_blueprint(system_bp)
    r = app.test_client().get("/health")
    assert r.status_code == 200, r.get_data(as_text=True)
    dl = r.get_json()[u"boot"][u"download"]
    for k in (u"measured", u"path", u"done_bytes", u"total_bytes", u"frac", u"eta_s", u"note"):
        assert k in dl, k
