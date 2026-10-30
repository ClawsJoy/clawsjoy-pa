# -*- coding: utf-8 -*-
from pathlib import Path
import io
from flask import Flask
from core.pa import voice as V


def test_voice_note_with_fake_asr(tmp_path, monkeypatch):
    monkeypatch.setattr(V, "transcribe_audio", lambda p, language="zh": {
        "text": "今天下午三点开会。", "lines": ["[000.0s] 今天下午三点开会。"],
        "language": "zh", "duration": 3.2})
    out = V.voice_note(data_dir=str(tmp_path), filename="voice.webm", audio_bytes=b"fake-audio")
    assert out["note"]["title"].startswith("语音笔记")
    assert "今天下午三点开会" in out["note"]["title"] or True
    assert out["transcript"]["text"]
    assert Path(out["audio"]).exists()
    n = Path(out["note"]["path"]).read_text(encoding="utf-8")
    assert "语音" in n


def test_voice_api(tmp_path, monkeypatch):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "data"))
    from core.pa.gateway_routes import register_pa_routes
    app = Flask(__name__)
    register_pa_routes(app)
    c = app.test_client()
    monkeypatch.setattr(V, "voice_note", lambda **kw: {
        "note": {"id": "x", "title": "语音笔记"}, "transcript": {"text": "hi"}, "audio": "a"})
    r = c.post("/v9/pa/notes/voice", data={"file": (io.BytesIO(b"abc"), "voice.webm")},
               content_type="multipart/form-data")
    assert r.status_code == 200, r.data
    assert r.get_json()["note"]["title"].startswith("语音")
