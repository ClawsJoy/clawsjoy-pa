# -*- coding: utf-8 -*-
import io
from pathlib import Path
from flask import Flask
from core.pa import screen as S


def test_screen_note_fake(tmp_path, monkeypatch):
    monkeypatch.setattr(S.V, "transcribe_audio", lambda p, language="zh": {
        "text": "打开设置，点击导出。", "lines": ["[000.0s] 打开设置，点击导出。"],
        "language": "zh", "duration": 8.0})
    monkeypatch.setattr(S, "keyframes", lambda p, d, **kw: [])
    out = S.screen_note(data_dir=str(tmp_path), filename="s.webm", video_bytes=b"fake-video")
    assert out["note"]["title"].startswith("录屏笔记")
    assert Path(out["video"]).exists()
    assert "录屏" in Path(out["note"]["path"]).read_text(encoding="utf-8")


def test_screen_api(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "data"))
    from core.pa.gateway_routes import register_pa_routes
    app = Flask(__name__)
    register_pa_routes(app)
    c = app.test_client()
    monkeypatch.setattr(S, "screen_note", lambda **kw: {
        "note": {"id": "x", "title": "录屏笔记"}, "transcript": {"text": "hi"},
        "frames": [], "video": "v", "duration": 1})
    r = c.post("/v9/pa/notes/screen", data={"file": (io.BytesIO(b"abc"), "s.webm")},
               content_type="multipart/form-data")
    assert r.status_code == 200, r.data
    assert r.get_json()["note"]["title"].startswith("录屏")
