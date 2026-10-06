# -*- coding: utf-8 -*-
u"""P2 \u2462 ／ \u2463 之测：模型名\u300c\u4e00\u5904\u5224\u300d\uff08\u5f52\u4e00 \uff0b \u767d\u540d\u5355\uff09\uff0b \u5bc6\u94a5\u552f\u5e03\u5c14\u3002

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_providers_model_names.py -q

判据：
  \u24dc 剥前缀（可叠 \u00b7 大小写归一 \u21d2 回注册表之实名）
  \u24dd 别名 \u21d2 实名（旧名 `deepseek-v4-flash` 仍通 \u00b7 pm_1447 \u00a7\u4e8c.2）
  \u24de **反控**：未识之名 \u21d2 None（\u26d4 自由字串 \u2014\u2014 \u26d4 以入参原字面充结果）
  \u24df 白名单 \u2261 注册表之实名（一处出 \u00b7 \u26d4 手拟第二表）
  \u24e0 (P2 \u2463) 密钥唯布尔：`public_view()` 之任何字段 \u26d4 载密钥值
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import providers as P  # noqa: E402


def test_prefix_strip_and_case_normalize():
    u"""\u24dc：前缀（可叠）\uff0b 大小写 \u21d2 回注册表之实名。"""
    assert P.split_prefix("remote:deepseek:deepseek-flash") == ("remote:deepseek:", "deepseek-flash")
    assert P.split_prefix("  Local:abc  ") == ("Local:", "abc")
    assert P.resolve_model("deepseek:deepseek-flash") == "deepseek-flash"
    assert P.resolve_model("REMOTE:DeepSeek-Flash") == "deepseek-flash"
    assert P.resolve_model("remote:" + P.known_models()[0]) == P.known_models()[0]


def test_alias_maps_to_real_name():
    u"""\u24dd：别名 \u21d2 实名（旧名仍通 \u21d2 \u26d4 原字面回吐）。"""
    assert P.resolve_model("deepseek-v4-flash") == "deepseek-flash"
    assert P.resolve_model("DEEPSEEK-V4-FLASH") == "deepseek-flash"
    assert P.resolve_model("local:qwen2.5:7b-instruct-q4_0-gpu") == "qwen2.5:7b-instruct-q4_0-gpu"


def test_unknown_is_rejected_not_echoed():
    u"""\u24de 反控：未识之名 \u21d2 None（\u26d4 自由字串 \u00b7 \u26d4 回吐入参）。"""
    for bad in ("gpt-4", "deepseek-v4.1-flash", "", "   ", "deepseek:", None):
        assert P.resolve_model(bad) is None, bad


def test_whitelist_is_registry_real_names():
    u"""\u24df：白名单 \u2261 注册表之实名（一处出 \u00b7 \u26d4 手拟）。"""
    ids = [m["id"] for pid in P.PROVIDERS for m in (P.PROVIDERS[pid].get("models") or [])]
    assert P.known_models() == tuple(ids)
    for m in P.known_models():
        assert P.resolve_model(m) == m


def test_public_view_never_carries_key_value(monkeypatch):
    u"""\u24e0 (P2 \u2463)：密钥唯布尔 \u2014\u2014 值 \u26d4 入屏（以哨兵值证）。"""
    sentinel = "sk-" + "SENTINEL" + "-1450"
    monkeypatch.setenv("DEEPSEEK_API_KEY", sentinel)
    blob = json.dumps(P.public_view(), ensure_ascii=False)
    assert sentinel not in blob
    for it in P.public_view()["providers"]:
        assert isinstance(it["key_configured"], bool)
        assert it["key_state"] in ("configured", "missing", "not_required")
    assert "DEEPSEEK_API_KEY" in blob   # 名入屏（布尔之据） \u00b7 值 \u26d4 入屏


def test_known_models_exposed_for_frontend():
    u"""\u24df\u2032：`known_models` ／ `model_aliases` 入屏（前端取名之单源 \u00b7 \u26d4 前端硬编）。"""
    pv = P.public_view()
    assert pv["known_models"] == list(P.known_models())
    assert pv["model_aliases"] == P.model_aliases()