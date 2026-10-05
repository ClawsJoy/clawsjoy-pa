# -*- coding: utf-8 -*-
"""PA model provider registry v1 (PM 034 Sec-2 P0, 2026-10-05).

Data in one place: PROVIDERS[id] => id/label/kind/base_url/models[]/params/enabled.
Rules (PM 034 Sec-6 / credentials-as-boolean):
  * key is stored ONLY as an env-var NAME; the value lives in .env; screen shows a BOOLEAN.
  * this module is READ-ONLY: it never issues a request (remote calls belong to P2).
"""
import os

REGISTRY_VERSION = "2026-10-05.3"   # ★ §二.4：加 params.max_tokens ⇒ +1（承 L152）

PROVIDERS = {
    "local:ollama": {
        "id": "local:ollama", "label": "Local Ollama", "kind": "local",
        "base_url": "http://127.0.0.1:11434", "base_url_env": "OLLAMA_BASE_URL",
        # PM 037 §A.3：P0 唯显示 · 未生效（接线点 core/lib/llm_client.py:381）
        "base_url_wired": False,
        "base_url_note": "P0 唯显示 · 未生效（接线点 core/lib/llm_client.py:381）",
        "key_env": None, "command": None,
        "models": [
            {"id": "qwen2.5:7b-instruct-q4_0-gpu", "label": "Qwen2.5 7B (GPU)",
             "isDefault": True, "ctx": 8192},
        ],
        "params": {"num_ctx": int(os.getenv("CLAWSJOY_NUM_CTX", "8192")),
                   "max_tokens": int(os.getenv("CLAWSJOY_MAX_TOKENS", "1600"))},
        "enabled": True,
    },
    "remote:deepseek": {
        "id": "remote:deepseek", "label": "DeepSeek (remote)", "kind": "remote",
        "base_url": "https://api.deepseek.com", "base_url_env": "DEEPSEEK_ENDPOINT",
        "base_url_wired": False,
        "base_url_note": "P0 唯显示 · 未生效（接线点 core/lib/llm_client.py:381）",
        "key_env": "DEEPSEEK_API_KEY", "command": None,
        "models": [
            {"id": "deepseek-v4-flash", "label": "DeepSeek V4 Flash", "isDefault": True, "ctx": 65536},
            {"id": "deepseek-v4-pro", "label": "DeepSeek V4 Pro", "isDefault": False, "ctx": 65536},
        ],
        "params": {}, "enabled": True,
    },
}

# single source of the default model (clearing a session override falls back here)
DEFAULT_MODEL = {"provider": "local:ollama", "model": "qwen2.5:7b-instruct-q4_0-gpu",
                 "thinking": None}

# route label: LLMClient provider => local / remote (PM 034 Sec-3 b)
PROVIDER_KIND = {"ollama": "local", "deepseek": "remote", "glm": "remote", "anthropic": "remote"}


DEFAULT_MAX_TOKENS = 1600   # ★ §二.4：临时经验值（无据）⇒ 待以读数定（PM 042）


def default_max_tokens():
    """单源：默认 provider 之 params.max_tokens（⛔ 魔数散落）。"""
    pid = DEFAULT_MODEL.get("provider")
    v = (PROVIDERS.get(pid, {}).get("params") or {}).get("max_tokens")
    return int(v or DEFAULT_MAX_TOKENS)


def key_state(pid):
    """Credential state: configured / missing / not_required. Never returns a value."""
    env = PROVIDERS.get(pid, {}).get("key_env")
    if not env:
        return "not_required"
    return "configured" if (os.getenv(env) or "").strip() else "missing"


def public_view():
    """Read-only screen view: no values, boolean only, models[] per provider."""
    items = []
    for pid in PROVIDERS:
        p = PROVIDERS[pid]
        st = key_state(pid)
        items.append({
            "id": p["id"], "label": p["label"], "kind": p["kind"],
            "base_url": p.get("base_url", ""), "base_url_env": p.get("base_url_env") or "",
            "key_env": p.get("key_env") or "", "key_state": st,
            "key_configured": (st == "configured"),
            "models": p["models"], "params": p.get("params", {}),
            "enabled": bool(p.get("enabled")),
            "base_url_wired": bool(p.get("base_url_wired")),
            "base_url_note": p.get("base_url_note", ""),
        })
    return {"providers": items, "default": dict(DEFAULT_MODEL),
            "registry_version": REGISTRY_VERSION, "source": "core/pa/providers.py"}


def src_label(route):
    """Route label: 'src: <kind>:<model>' derived from the ACTUAL route (never guessed)."""
    if not isinstance(route, dict) or not route.get("provider"):
        return ""
    return "src: %s:%s" % (PROVIDER_KIND.get(str(route.get("provider")), "unknown"),
                           route.get("model") or "?")


# ---- fallback human note (PM 037 §A.2 ／ 034 §六) ----
# 回落 ⛔ 说成「正常」：用户面须为**人话**；reason 码仍随 route 上屏（可机检）。
FALLBACK_HUMAN = {"no_api_key": "未配置密钥",
                  "cloud_unavailable": "云端不可用",
                  "model_unavailable": "该模型不可用",
                  "empty_answer": "远端出了空答（非故障）"}


def fallback_note(route):
    """回落之用户面人话；⛔ 回落时 ⇒ ""。"""
    if not isinstance(route, dict) or not route.get("fell_back"):
        return ""
    reason = str(route.get("reason") or "unknown")
    # ★ 稿 A（P3）引入之 reason 形「empty_answer: <因与量>」⇒ 前缀归一
    #   承 L168：改度量 ⇒ 须查其溢出（本人之稿 A 亦然）
    if reason.startswith("empty_answer"):
        _det = reason.split(":", 1)[1].strip() if ":" in reason else ""
        return "已回落本机（因 %s%s）" % (
            FALLBACK_HUMAN["empty_answer"], ("：" + _det) if _det else "")
    return "已回落本机（因 %s）" % FALLBACK_HUMAN.get(reason, reason)