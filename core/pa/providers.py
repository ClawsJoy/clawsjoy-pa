# -*- coding: utf-8 -*-
"""PA model provider registry v1 (PM 034 Sec-2 P0, 2026-10-05).

Data in one place: PROVIDERS[id] => id/label/kind/base_url/models[]/params/enabled.
  enabled is DERIVED (pm_1380): the registry value is only the DEFAULT;
  the truth is env CLAWSJOY_PA_PROVIDERS_DISABLED (CSV, empty => all on).
Rules (PM 034 Sec-6 / credentials-as-boolean):
  * key is stored ONLY as an env-var NAME; the value lives in .env; screen shows a BOOLEAN.
  * this module is READ-ONLY: it never issues a request (remote calls belong to P2).
"""
import os

REGISTRY_VERSION = "2026-10-06.2"   # ⭐ pm_1447 §二.2：deepseek 正名 ⇒ deepseek-flash（旧名 ＝ 别名）；⭐ pm_1380 §一：enabled 自 env 派生（⛔ 硬编）＋ 屏上附源

PROVIDERS = {
    "local:ollama": {
        "id": "local:ollama", "label": "Local Ollama", "kind": "local",
        "base_url": "http://127.0.0.1:11434", "base_url_env": "OLLAMA_BASE_URL",
        # PM 037 §A.3：P0 唯显示 · 未生效（接线点 core/lib/llm_client.py:103 base_url 默认 · ⛔ 自 env 读 ⇒ 未生效；用 at :158 ／ :422 ／ :543）
        "base_url_wired": False,
        "base_url_note": "P0 唯显示 · 未生效（接线点 core/lib/llm_client.py:103 base_url 默认 · ⛔ 自 env 读；用 at :158 ／ :422 ／ :543）",
        "key_env": None, "command": None,
        "models": [
            {"id": "qwen2.5:7b-instruct-q4_0-gpu", "label": "Qwen2.5 7B (GPU)",
             "isDefault": True, "ctx": 8192},
        ],
        "params": {"num_ctx": int(os.getenv("CLAWSJOY_NUM_CTX", "8192")),
                   "max_tokens": int(os.getenv("CLAWSJOY_MAX_TOKENS", "1600"))},
        "enabled": True,   # 默认（⛔ 真源 · 真源 ＝ env CLAWSJOY_PA_PROVIDERS_DISABLED）
    },
    "remote:deepseek": {
        "id": "remote:deepseek", "label": "DeepSeek (remote)", "kind": "remote",
        "base_url": "https://api.deepseek.com", "base_url_env": "DEEPSEEK_ENDPOINT",
        "base_url_wired": False,
        "base_url_note": "P0 唯显示 · 半真（env DEEPSEEK_ENDPOINT 已接 core/lib/llm_client.py:582 ／ 注册表 base_url 未读 ⇒ 候 P2 二分）",
        # ⭐ pm_1447 §二.2 正名：实名 ＝ `deepseek-flash`（GET /models 之实名 · 2026-10-06 器取）；
        #    旧名 `deepseek-v4-flash` 仍为**可通之别名**（⛔ 径删 —— 屏 ／ 旧件仍引之）。
        "key_env": "DEEPSEEK_API_KEY", "command": None,
        "models": [
            {"id": "deepseek-flash", "label": "DeepSeek V4 Flash", "isDefault": True, "ctx": 65536,
             "aliases": ["deepseek-v4-flash"]},   # ⭐ pm_1447 §二.2：旧名仍为**可通之别名**（器取实证 · 1-token 复证）
            {"id": "deepseek-v4-pro", "label": "DeepSeek V4 Pro", "isDefault": False, "ctx": 65536},
        ],
        "params": {}, "enabled": True,   # 默认（⛔ 真源 · 真源 ＝ env CLAWSJOY_PA_PROVIDERS_DISABLED）
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


ENABLED_ENV = "CLAWSJOY_PA_PROVIDERS_DISABLED"


def disabled_ids():
    """⭐ 停用之 id 列（pm_1380 §一「立（轻形）」）—— env CLAWSJOY_PA_PROVIDERS_DISABLED（CSV · 空 ⇒ 皆启）。

    ⛔ 注册表之字面 enabled 沦为**默认**（⛔ 真源）—— 承 pm_1377 §三（写了不生效 ∧ 一名蔽二态）。"""
    raw = os.getenv(ENABLED_ENV) or ""
    return tuple(x.strip() for x in raw.split(",") if x.strip())


def is_enabled(pid):
    """⭐ 启用之**派生** ＋ 其**源之述**（⛔ 一名蔽二态）—— 返回 (bool, src)。

    ⚠ 「齿」（resolve() 遇 disabled ⇒ 拒）随 P2 立项（pm_1380 §一）⇒ 屏上须附源以⛔ 冒「已生效」。"""
    if pid in disabled_ids():
        return False, "停用（源 env %s · 齿随 P2）" % ENABLED_ENV
    if bool((PROVIDERS.get(pid) or {}).get("enabled")):
        return True, "启用（默认 · ⛔ 未列于 env %s）" % ENABLED_ENV
    return False, "注册表默认 enabled=False"


# ---------------------------------------------------------------- P2 ③：模型名「一处判」
# 承 pm_1447 §二.3③ ／ pm_1449 §二.2：**唯此处**判「模型名」——
#   ⓜ 剥前缀（`remote:` ／ `local:` ／ `ollama:` ／ `deepseek:` ／ `glm:` ／ `anthropic:`）
#   ⓝ 别名 ⇒ 实名（自注册表 `models[].aliases` 出 · **与实名同格**）
#   ⓞ 白名单 ⇒ **唯注册表之实名**（⛔ 自由字串 · 后端验 · pm_1449 §二.1）
# ⚠ 「名之归源」（V8 ↔ PA 之二源 · `config/v8/**` ／ `core/lib/llm_client.py`）
#   ⇒ **另案**（pm_1449 §二.2）—— 本块唯治 PA 侧之入参归一。
MODEL_PREFIXES = ("remote:", "local:", "ollama:", "deepseek:", "glm:", "anthropic:")


def split_prefix(name):
    """剥前缀（可叠 ⇒ 循环剥）⇒ (前缀, 裸名)。无名 ⇒ ("", "")。"""
    s = str(name or "").strip()
    pre = ""
    while True:
        for _p in MODEL_PREFIXES:
            if s.lower().startswith(_p):
                pre += s[:len(_p)]
                s = s[len(_p):].strip()
                break
        else:
            return pre, s


def known_models():
    """白名单：注册表之**实名**（一处出 · ⛔ 手拟第二表）。"""
    out = []
    for pid in PROVIDERS:
        for m in PROVIDERS[pid].get("models") or []:
            if m.get("id") and m["id"] not in out:
                out.append(m["id"])
    return tuple(out)


def model_aliases():
    """别名 ⇒ 实名（自注册表 `models[].aliases` 出 · 一处定形）。"""
    out = {}
    for pid in PROVIDERS:
        for m in PROVIDERS[pid].get("models") or []:
            for a in m.get("aliases") or []:
                out[str(a)] = m.get("id")
    return out


def resolve_model(name):
    """归一 ＋ 白名单 ⇒ **注册表之实名** ∨ None（⛔ 自由字串）。

    大小写归一 ⇒ 回**注册表之实名**（⛔ 回入参之原字面 —— 免「名不对表」）。
    """
    _pre, bare = split_prefix(name)
    if not bare:
        return None
    _known = known_models()
    if bare in _known:
        return bare
    _al = model_aliases()
    if bare in _al:
        return _al[bare]
    _low = bare.lower()
    for _m in _known:
        if _low == _m.lower():
            return _m
    for _k, _v in _al.items():
        if _low == _k.lower():
            return _v
    return None


def public_view():
    """Read-only screen view: no values, boolean only, models[] per provider."""
    items = []
    for pid in PROVIDERS:
        p = PROVIDERS[pid]
        st = key_state(pid)
        en, en_src = is_enabled(pid)
        items.append({
            "id": p["id"], "label": p["label"], "kind": p["kind"],
            "base_url": p.get("base_url", ""), "base_url_env": p.get("base_url_env") or "",
            "key_env": p.get("key_env") or "", "key_state": st,
            "key_configured": (st == "configured"),
            "models": p["models"], "params": p.get("params", {}),
            "enabled": en,
            "enabled_src": en_src,
            "base_url_wired": bool(p.get("base_url_wired")),
            "base_url_note": p.get("base_url_note", ""),
        })
    return {"providers": items, "default": dict(DEFAULT_MODEL),
            # ⭐ P2 ③：前端取名之**单源**（⛔ 前端硬编 · pm_1449 §二.1④）
            "known_models": list(known_models()), "model_aliases": model_aliases(),
            "registry_version": REGISTRY_VERSION, "source": "core/pa/providers.py"}


def src_label(route):
    """Route label: 'src: <kind>:<model>' derived from the ACTUAL route (never guessed)."""
    if not isinstance(route, dict) or not route.get("provider"):
        return ""
    return "src: %s:%s" % (PROVIDER_KIND.get(str(route.get("provider")), "unknown"),
                           route.get("model") or "?")


def route_kind(route):
    u"""走径之 `kind`（`local` ／ `remote`）—— **一处定形**（与 `src_label` 同源 `PROVIDER_KIND`）。

    承 pm_1460 §一（裁）：回执**必给** `kind` ——
      由：前端「出机」之标（红线 · 「本轮经云端 · 内容将出机」）
      **唯** `kind ∈ 远端集` 时上屏 ⇒ `kind` ⛔ 给 ⇒ 标 ⛔ 上
      ⇒ **红线恰于 M4 演示（走云端）时失效**。
    戒：⛔ 以 `model` 名反推（那是「猜」 · 承「⛔ 前端猜」之族）—— 真源唯 `provider`。
    未识之 provider ⇒ `"unknown"`（同 `src_label` 之形 ⇒ 前端二集皆不中 ⇒ 照实显「kind 未给」）。
    """
    if not isinstance(route, dict) or not route.get("provider"):
        return ""
    return PROVIDER_KIND.get(str(route.get("provider")), "unknown")


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