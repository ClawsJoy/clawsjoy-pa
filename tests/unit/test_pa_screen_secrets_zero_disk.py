# -*- coding: utf-8 -*-
u"""P2 \u2463\uff08\u5bc6\u94a5\u552f\u5e03\u5c14\uff09\uff0b P2 \u2464\uff08\u96f6\u843d\u76d8\uff09\u4e4b\u6d4b\u2014\u2014 \u4e8c\u8005\u7686\u300c\u6838 \uff0b \u660e\u4e66\u300d\u3002

\u4ee5\u4f55\u5f62\u8c03\u7528\uff08\u5224\u901a\uff0f\u65ad\u987b\u9644\uff09\uff1a
  python -X utf8 -B -m pytest tests/unit/test_pa_screen_secrets_zero_disk.py -q

\u5224\u636e\uff1a
  \u24dc (P2 \u2463) \u5c4f\u4e0a\u552f\u5e03\u5c14\uff1a`/v9/pa/providers` \u4e4b\u5e94\u7b54 \u26d4 \u8f7d\u5bc6\u94a5\u503c\uff08\u4ee5\u54e8\u5175\u503c\u8bc1\uff09
  \u24dd (P2 \u2463) \u540d\u5165\u5c4f\uff08\u5e03\u5c14\u4e4b\u636e\uff09\u2014\u2014 `key_env` \uff0b `key_state` \u5b57\u9762
  \u24de (P2 \u2464) \u9519\u4f53\u552f\u6458\u8981\uff1a`_err_digest` \u21d2 \u72b6\u6001 \uff0b \u7c7b \uff0b \u957f\u5ea6\uff08\u26d4 \u539f\u6587\uff09
  \u24df (P2 \u2464) 4xx \u4e4b\u7ec8\u62a5\u4e0d\u542b\u9519\u4f53\u539f\u6587\uff08\u4e00\u624b\u8dd1 `_call_openai_compatible`\uff09
"""
import sys
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.lib import llm_client as LC  # noqa: E402
from core.pa.gateway_routes import register_pa_routes  # noqa: E402

SENTINEL = "sk-" + "SENTINEL" + "-1450"


def test_providers_route_screen_carries_no_key_value(tmp_path, monkeypatch):
    u"""\u24dc \uff0b \u24dd\uff1a\u5bc6\u94a5\u552f\u5e03\u5c14\uff08\u503c \u26d4 \u5165\u5c4f \u00b7 \u540d \u21d2 \u5165\u5c4f\uff09\u3002"""
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))
    monkeypatch.setenv("DEEPSEEK_API_KEY", SENTINEL)
    app = Flask(__name__)
    register_pa_routes(app)
    r = app.test_client().get("/v9/pa/providers")
    assert r.status_code == 200, r.status_code
    assert SENTINEL not in r.get_data(as_text=True)
    d = r.get_json()
    deep = [p for p in d["providers"] if p["id"] == "remote:deepseek"][0]
    assert deep["key_env"] == "DEEPSEEK_API_KEY"
    assert deep["key_configured"] is True and deep["key_state"] == "configured"


def test_err_digest_never_carries_body_text():
    u"""\u24de\uff1a\u9519\u4f53 \u21d2 \u72b6\u6001 \uff0b \u957f\u5ea6 \uff0b \u7c7b\uff08\u26d4 \u539f\u6587\uff09\u3002"""
    class _R:
        status_code = 400
        text = '{"error":{"message":"SECRET-BODY-1450"}}'

    d = LC._err_digest(_R())
    assert "SECRET-BODY-1450" not in d
    assert d == "HTTP 400 \u00b7 \u4f53 %d B \u00b7 json" % len(_R.text)

    class _R2:
        status_code = 503
        text = "SECRET-plain-1450"

    d2 = LC._err_digest(_R2())
    assert "SECRET-plain-1450" not in d2 and d2.endswith("\u00b7 text")

    class _R3:
        status_code = 200
        text = ""

    assert LC._err_digest(_R3()).endswith("\u00b7 empty")


def test_call_4xx_raises_without_error_body(monkeypatch):
    u"""\u24df\uff1a4xx \u4e4b\u7ec8\u62a5 \u26d4 \u542b\u9519\u4f53\u539f\u6587\uff08\u96f6\u843d\u76d8\u4e4b\u6838\uff09\u3002"""
    c = LC.LLMClient()

    class _Sess:
        def post(self, *a, **k):
            class _R:
                status_code = 400
                text = '{"error":"SECRET-BODY-1450"}' + SENTINEL

                def json(self):
                    return {}
            return _R()

    monkeypatch.setattr(c, "_session", _Sess())
    monkeypatch.setattr(c, "config", LC.LLMConfig(max_retries=1))
    with pytest.raises(Exception) as _ei:
        list(c._call_openai_compatible("hi", "deepseek-flash", 0.1, 16, 5, False, None, api_key="k"))
    _msg = str(_ei.value)
    assert "SECRET-BODY-1450" not in _msg and SENTINEL not in _msg, _msg
    assert "HTTP 400" in _msg, _msg