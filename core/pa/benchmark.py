# -*- coding: utf-8 -*-
u"""PA 引擎 benchmark（P1-3）：对 Ollama / LocaLM 做同题、短输出的只读测量。

指标：
  · TTFT：首 token/首块到达的毫秒数（流式实测）
  · tok/s：Ollama 用 eval_count / eval_duration；LocaLM 无 usage 时用流块数估算，并显式标注来源
  · VRAM：nvidia-smi 前后 MiB（本机 NVIDIA；无则 None，不假装 0）
严格：只走本机；失败照实报；不切默认、不写模型配置。
"""
from __future__ import annotations

import json
import os
import subprocess
import time

from core.pa import _proc

DEFAULT_PROMPT = "用一句中文回答：什么是本地推理？"
DEFAULT_MAX_TOKENS = 64


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _vram_mib():
    try:
        r = _proc.run_hidden(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                             capture_output=True, timeout=8, stdin=subprocess.DEVNULL)
        return int((r.stdout or b"").decode().strip().splitlines()[0])
    except Exception:
        return None


def _base(engine):
    if engine == "localm":
        return (os.getenv("LOCALM_BASE_URL") or "http://127.0.0.1:8642").rstrip("/")
    return (os.getenv("OLLAMA_BASE_URL") or "http://127.0.0.1:11434").rstrip("/")


def _err(engine, model, msg, t0):
    return {"ok": False, "engine": engine, "model": model, "error": str(msg)[:500],
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1), "at": _now()}


def bench_ollama(model, prompt=DEFAULT_PROMPT, max_tokens=DEFAULT_MAX_TOKENS, timeout=180):
    import requests
    t0 = time.perf_counter()
    before = _vram_mib()
    ttft = None
    text = ""
    final = {}
    try:
        payload = {"model": model, "prompt": prompt, "stream": True,
                   "keep_alive": "5m",
                   "options": {"temperature": 0, "num_predict": int(max_tokens)}}
        with requests.post(_base("ollama") + "/api/generate", json=payload,
                           stream=True, timeout=timeout) as r:
            if r.status_code != 200:
                return _err("ollama", model, "HTTP %s" % r.status_code, t0)
            for line in r.iter_lines():
                if not line:
                    continue
                try:
                    d = json.loads(line.decode("utf-8") if isinstance(line, bytes) else line)
                except Exception:
                    continue
                chunk = d.get("response") or ""
                if chunk and ttft is None:
                    ttft = (time.perf_counter() - t0) * 1000
                text += chunk
                if d.get("done"):
                    final = d
                    break
        elapsed = (time.perf_counter() - t0) * 1000
        after = _vram_mib()
        eval_count = int(final.get("eval_count") or 0)
        eval_ns = int(final.get("eval_duration") or 0)
        tok_s = (eval_count / (eval_ns / 1e9)) if eval_count and eval_ns else None
        return {"ok": True, "engine": "ollama", "model": model,
                "ttft_ms": round(ttft, 1) if ttft is not None else None,
                "tok_s": round(tok_s, 2) if tok_s else None,
                "tok_s_source": "eval_count/eval_duration" if tok_s else "unavailable",
                "tokens": eval_count or None, "elapsed_ms": round(elapsed, 1),
                "vram_before_mib": before, "vram_after_mib": after,
                "vram_delta_mib": (after - before) if (before is not None and after is not None) else None,
                "answer": text[:500], "at": _now()}
    except Exception as e:
        return _err("ollama", model, "%s: %s" % (type(e).__name__, e), t0)


def bench_localm(model, prompt=DEFAULT_PROMPT, max_tokens=DEFAULT_MAX_TOKENS, timeout=180):
    import requests
    t0 = time.perf_counter()
    before = _vram_mib()
    ttft = None
    text = ""
    chunks = 0
    usage = {}
    try:
        payload = {"model": str(model).replace("localm:", ""),
                   "messages": [{"role": "user", "content": prompt}],
                   "max_tokens": int(max_tokens), "temperature": 0, "stream": True}
        with requests.post(_base("localm") + "/v1/chat/completions", json=payload,
                           stream=True, timeout=timeout) as r:
            if r.status_code != 200:
                return _err("localm", model, "HTTP %s" % r.status_code, t0)
            for line in r.iter_lines():
                if not line:
                    continue
                raw = line.decode("utf-8") if isinstance(line, bytes) else line
                if raw.startswith("data:"):
                    raw = raw[5:].strip()
                if raw == "[DONE]":
                    break
                try:
                    d = json.loads(raw)
                except Exception:
                    continue
                if d.get("usage"):
                    usage = d.get("usage") or usage
                delta = ((d.get("choices") or [{}])[0].get("delta") or {})
                chunk = delta.get("content") or ""
                if chunk:
                    if ttft is None:
                        ttft = (time.perf_counter() - t0) * 1000
                    chunks += 1
                    text += chunk
        elapsed = (time.perf_counter() - t0) * 1000
        after = _vram_mib()
        usage_tokens = int((usage or {}).get("completion_tokens") or 0)
        tokens = usage_tokens or chunks
        gen_ms = elapsed - (ttft or 0)
        tok_s = (tokens / (gen_ms / 1000)) if tokens and gen_ms > 0 else None
        return {"ok": True, "engine": "localm", "model": model,
                "ttft_ms": round(ttft, 1) if ttft is not None else None,
                "tok_s": round(tok_s, 2) if tok_s else None,
                "tok_s_source": "usage.completion_tokens" if usage_tokens else "stream_chunks(est)",
                "tokens": tokens or None, "elapsed_ms": round(elapsed, 1),
                "vram_before_mib": before, "vram_after_mib": after,
                "vram_delta_mib": (after - before) if (before is not None and after is not None) else None,
                "answer": text[:500], "at": _now()}
    except Exception as e:
        return _err("localm", model, "%s: %s" % (type(e).__name__, e), t0)


def run(engine, model=None, prompt=None, max_tokens=DEFAULT_MAX_TOKENS, timeout=180):
    engine = str(engine or "").strip().lower()
    if engine not in ("ollama", "localm"):
        return {"ok": False, "error": "engine 须为 ollama 或 localm", "at": _now()}
    if not model:
        from core.pa.providers import default_model_of
        model = default_model_of("local:localm" if engine == "localm" else "local:ollama")
    if engine == "localm":
        return bench_localm(model, prompt or DEFAULT_PROMPT, max_tokens, timeout)
    return bench_ollama(model, prompt or DEFAULT_PROMPT, max_tokens, timeout)
