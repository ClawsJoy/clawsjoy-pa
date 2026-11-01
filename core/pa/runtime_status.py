# -*- coding: utf-8 -*-
u"""PA runtime status（P0）：聚合 Ollama / LocaLM / DSH 的真实状态。

原则：
  · 只读探活，不发模型请求；超时短，失败照实报；
  · ⛔ 用「注册表自称」冒充可用；
  · 一项失败不影响其它项（partial 也要可读）。
"""
from __future__ import annotations

import os
import time


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _model_key(name):
    u"""模型名归一键：忽略 localm: 前缀、标点与大小写差异（qwen2.5:… ≡ qwen2.5-…）。"""
    import re
    s = str(name or "").strip().lower()
    if s.startswith("localm:"):
        s = s[len("localm:"):]
    return re.sub(r"[^a-z0-9]+", "", s)


def _http_json(url, timeout=1.8):
    import requests
    try:
        r = requests.get(url, timeout=timeout)
        data = r.json() if r.content else {}
        return {"ok": r.status_code == 200, "status": r.status_code, "data": data, "error": ""}
    except Exception as e:
        return {"ok": False, "status": 0, "data": None,
                "error": "%s: %s" % (type(e).__name__, str(e)[:160])}


def _ollama_view():
    base = (os.getenv("OLLAMA_BASE_URL") or "http://127.0.0.1:11434").rstrip("/")
    tags = _http_json(base + "/api/tags")
    ps = _http_json(base + "/api/ps")
    models = []
    if tags.get("ok"):
        models = [str(m.get("name") or m.get("model") or "") for m in
                  ((tags.get("data") or {}).get("models") or []) if (m.get("name") or m.get("model"))]
    loaded = []
    if ps.get("ok"):
        loaded = [str(m.get("name") or m.get("model") or "") for m in
                  ((ps.get("data") or {}).get("models") or []) if (m.get("name") or m.get("model"))]
    available = bool(tags.get("ok"))
    state = "在" if available and models else ("空" if available else "未接")
    detail = ("%s/api/tags 通 · %d 个模型" % (base, len(models)) if available
              else "%s 未应答（%s）" % (base, tags.get("error") or "?"))
    return {"id": "local:ollama", "label": "Ollama", "kind": "local",
            "base_url": base, "available": available, "state": state,
            "models": models, "loaded": loaded, "detail": detail,
            "source": "GET /api/tags + /api/ps"}


def _localm_view():
    base = (os.getenv("LOCALM_BASE_URL") or "http://127.0.0.1:8642").rstrip("/")
    health = _http_json(base + "/health")
    models_resp = _http_json(base + "/v1/models")
    health_data = health.get("data") or {}
    models = []
    if models_resp.get("ok"):
        models = [str(m.get("id") or "") for m in
                  ((models_resp.get("data") or {}).get("data") or []) if m.get("id")]
    available = bool(health.get("ok"))
    loaded_model = str(health_data.get("model") or "")
    loaded = bool(health_data.get("loaded")) and bool(loaded_model)
    state = "在" if available else "未接"
    detail = (("health 通 · model=%s · loaded=%s · /v1/models %d 个"
               % (loaded_model or "未载", str(loaded).lower(), len(models)))
              if available else "%s/health 未应答（%s）" % (base, health.get("error") or "?"))
    return {"id": "local:localm", "label": "LocaLM", "kind": "local",
            "base_url": base, "available": available, "state": state,
            "models": models, "loaded": ([loaded_model] if loaded else []),
            "model": loaded_model or None, "loaded_bool": loaded,
            "detail": detail, "source": "GET /health + /v1/models"}


def _dsh_view():
    try:
        from core.pa.harness.dsh import DshHarness
        probe = DshHarness().probe()
        return {"id": "harness:dsh", "label": "DSH", "kind": "harness",
                "available": bool(probe.available), "state": "在" if probe.available else "未接",
                "version": str(probe.version or ""), "detail": str(probe.detail or ""),
                "source": "dsh --version"}
    except Exception as e:
        return {"id": "harness:dsh", "label": "DSH", "kind": "harness",
                "available": False, "state": "未接",
                "version": "", "detail": "%s: %s" % (type(e).__name__, str(e)[:160]),
                "source": "dsh --version"}


def runtime_view():
    items = []
    for fn in (_ollama_view, _localm_view, _dsh_view):
        try:
            items.append(fn())
        except Exception as e:
            items.append({"id": fn.__name__, "label": fn.__name__, "available": False,
                          "state": "未接", "models": [], "loaded": [],
                          "detail": "%s: %s" % (type(e).__name__, str(e)[:160])})
    warnings = []
    _seen = {}
    for _it in items:
        if _it.get("kind") != "local":
            continue
        for _m in (_it.get("loaded") or []):
            _key = _model_key(_m)
            if not _key:
                continue
            if _key in _seen and _seen[_key][0] != _it.get("id"):
                warnings.append("同一模型同时载入 %s 与 %s：%s（6GB VRAM 可能互抢）"
                                % (_seen[_key][0], _it.get("id"), _m))
            else:
                _seen[_key] = (_it.get("id"), str(_m))
    return {"ok": True, "at": _now(), "items": items, "warnings": warnings,
            "source": "core/pa/runtime_status.py（只读探活）"}
