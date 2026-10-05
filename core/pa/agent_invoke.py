# -*- coding: utf-8 -*-
r"""PA 统一调用面（T2-刀7 ／ 刀7-正 · 2026-10-05 · 技术总监 f202f89）。

【本模块解决什么】
  「管理」≠「知道它存在」⇒ ＝ **能派 · 能盯 · 能收 · 能记**。
  ⚠ **刀7-正之更正（我一手读卡面而得）**：`GET /v9/pa/roster?full=1` 之卡**既存七键**
    `access ／ boundary ／ capabilities ／ cost ／ fragility ／ id ／ kind ／ name ／ next ／ role ／ verified`
    ⇒ ⭐ **本模块唯补二键**：`invoke`（怎么调）＋ `probe`（怎么验活）；
    ⛔ **重造 ／ ⛔ 更名 ／ ⛔ 覆写**（承令「既存七键只增不改」）。
  `caps` 一名**作废**（既存之名为 `capabilities` · 承令「面未钉＝缺 ⇒ 判卡之键须读卡面 `?full=1`」）。

【所补二键之形】
  invoke  CLI 命令行 ／ HTTP 端点 ／ ACP 会话 ／ SDK —— **逐字**（cli 者取 `shutil.which()` 之**全径**）
  probe   `--version` ／ `/health` ／ 一次最小调用 ＋ **实测读数与刻**
          （落件 `data/v9/pa/card_probes.json`；⛔ 填「可用」而无读数）

【刀7-② 统一调用面】`POST /v9/pa/agent/invoke {agent_id, task, mode, timeout_s}`
  ⇒ `{ok, agent_id, via, ms, out, 印}`（`印` 由路由以 `_code_sha16` **载器**）。
  三类执行器（⛔ 另造运输）：
    seat  本机席   ⇒ **复用** `core.pa.dispatch.SeatExecutor`（`paseo agent send` 之路）
    cli   本机 CLI ⇒ 起进程 ＋ **超时必带** ＋ `stdin=DEVNULL`（⛔ 交互式）
    api   云端     ⇒ provider `base_url` ＋ 密钥**唯从 `D:\paseo-home\config.json` 读**
  ⛔ **未在册之 agent ⇒ 拒调**（⛔ 静默兜底）；`agent_id` 缺 ⇒ 回**册**（可枚举）。

【红线】
  · **密钥唯布尔 · ⛔ 值**：值唯在 `_secret()` 之返回里活一瞬（仅供本进程发请求），
    ⛔ 入面 ／ ⛔ 入日志 ／ ⛔ 入事件；出口过 `_redact()` 归一。
  · **显卡**：RTX 2060 · 6 GB ⇒ 本地并发**排队**（`PA_INVOKE_LOCAL_CONCURRENCY`，默认 `1`）
    ＋ 记时长（承老板令「⛔ 烧卡」）。
  · **云端调用只用于我方域内之活**；⛔ 代操作他方平台。
  · 报数附「面之径逐字 ／ 滤 ／ 式 ／ 数 ／ 印」。
"""
import json
import os
import shutil
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from core.pa import _proc as _proc   # ⭐ 窗隐唯一出口（PM 2026-10-05 令 · ⛔ 各写 creationflags）
from urllib.parse import urlparse

INVOKE_VERSION = "2026-10-05.2"   # ★ 刀7-正：四件 ⇒ 二键（承 L152）
REPO_ROOT = Path(__file__).resolve().parents[2]
#: 与 `roster._path()` **同规**（`PA_DATA_DIR` ⇒ 可 stage；⛔ 两处各持一径）
_DATA_DIR = os.getenv("PA_DATA_DIR", "data/v9/pa")
PROBE_CACHE = Path(_DATA_DIR) / "card_probes.json"
CONFIG_JSON = r"D:\paseo-home\config.json"
PASEO_PS1 = r"D:\npm-global\paseo.ps1"

#: ⭐ 本模块**唯补**此二键（⛔ 重造既存七键）
CARD_KEYS_ADDED = ("invoke", "probe")

DEFAULT_TIMEOUT = int(os.getenv("PA_INVOKE_TIMEOUT", "120"))
MAX_TIMEOUT = int(os.getenv("PA_INVOKE_MAX_TIMEOUT", "600"))
#: ⚠ RTX 2060 · 6144 MiB ⇒ 本地并发上限（1~2 · 承老板令「⛔ 烧卡」）
LOCAL_LIMIT = max(1, min(2, int(os.getenv("PA_INVOKE_LOCAL_CONCURRENCY", "1"))))

# ============================ 二键之真源（逐卡） ============================
#: `probe` 之形：cli ＝ 全径 ＋ `--version`；http ＝ 端点；tcp ＝ 端口；cdp ＝ 浏览器真态
PROBES = {
    "ds_chat":          {"kind": "cdp",  "match": "chat.deepseek.com"},
    "lingxi":           {"kind": "http", "method": "GET", "url": "http://127.0.0.1:3890/mcp/status"},
    "lingxi_local_api": {"kind": "http", "method": "POST", "url": "http://127.0.0.1:5102/v9/pa/proxy", "body": {}},
    "blender":          {"kind": "cli",  "bin": "blender", "args": ["--version"]},
    "local_vlm":        {"kind": "http", "method": "GET", "url": "http://127.0.0.1:11434/api/tags"},
    "v9_agent":         {"kind": "http", "method": "GET", "url": "http://127.0.0.1:5102/v9/agent/chat"},
    "codex":            {"kind": "cli",  "bin": "codex",  "args": ["--version"]},
    "pi":               {"kind": "cli",  "bin": "pi",     "args": ["--version"]},
    "dsh":              {"kind": "cli",  "bin": "dsh",    "args": ["--version"]},
    "claude":           {"kind": "cli",  "bin": "claude", "args": ["--version"]},
    "ollama":           {"kind": "http", "method": "GET", "url": "http://127.0.0.1:11434/api/version"},
    "paseo_daemon":     {"kind": "tcp",  "host": "127.0.0.1", "port": 6767},
    "v9_gateway":       {"kind": "http", "method": "GET", "url": "http://127.0.0.1:5102/health"},
}

#: `invoke` 之形（`cli` 者之全径于**运行时**取；⛔ 硬编路径）
INVOKES = {
    "ds_chat":          {"via": "cdp",         "text": "CDP http://127.0.0.1:9222 ⇒ 线程 https://chat.deepseek.com/a/chat/s/49ad7381-f83b-4745-af63-0ce63c7f2ed1（L1 浏览器 UI · ⛔ 无程序接口）"},
    "lingxi":           {"via": "mcp",         "text": "MCP http://127.0.0.1:3890（Bearer）⇒ tools/call"},
    "lingxi_local_api": {"via": "local_http",  "text": "POST /v9/pa/proxy {path:/doc-snapshot|/doc-restore|/fetch-web}"},
    "blender":          {"via": "desktop",     "text": "blender-mcp 1.9.1 ＋ headless CLI（addon 拒 background ⇒ 需 GUI/xvfb/WSLg）"},
    "local_vlm":        {"via": "local_http",  "text": "POST http://127.0.0.1:11434/api/generate {model:qwen2.5vl:7b}"},
    "v9_agent":         {"via": "local_http",  "text": "POST http://127.0.0.1:5102/v9/agent/chat（本机进程内 · 带 tools）"},
    "codex":            {"via": "cli",         "bin": "codex", "args": ["exec"]},
    "pi":               {"via": "cli",         "bin": "pi",    "args": []},
    "dsh":              {"via": "cli",         "bin": "dsh",   "args": []},
    "claude":           {"via": "unreachable", "text": "⛔ 不在位（`shutil.which` 空 · L0）"},
    "ollama":           {"via": "local_http",  "text": "POST http://127.0.0.1:11434/api/chat"},
    "paseo_daemon":     {"via": "local_http",  "text": "HTTP 127.0.0.1:6767（paseo daemon · ⛔ 根路由）"},
    "v9_gateway":       {"via": "local_http",  "text": "HTTP 127.0.0.1:5102（本网关）"},
}

#: 云端 provider（**真源** ＝ `D:\paseo-home\config.json` 之 `agents.providers`）
API_PROVIDERS = {
    "codex-deepseek": {"label": "Codex (DeepSeek)", "base_key": "OPENAI_BASE_URL",
                       "key_key": "OPENAI_API_KEY", "path": "/chat/completions"},
    "dsh":            {"label": "DSH (DeepSeek)", "base_key": None, "key_key": "DEEPSEEK_API_KEY",
                       "base_url": "https://api.deepseek.com", "path": "/chat/completions"},
}

# ============================ 本地并发闸（⛔ 烧卡） ============================
_LOCAL_SEM = threading.BoundedSemaphore(LOCAL_LIMIT)
_STAT_LOCK = threading.Lock()
_STATS = {"limit": LOCAL_LIMIT, "active": 0, "peak": 0, "waited": 0, "runs": 0}


def stats():
    with _STAT_LOCK:
        return dict(_STATS)


def _sha16(b):
    import hashlib
    return hashlib.sha256(b).hexdigest()[:16]


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _which(binname):
    try:
        return shutil.which(binname) or ""
    except Exception:
        return ""


def _run(cmd, timeout):
    """起进程（**超时必带** · `stdin=DEVNULL` ⇒ ⛔ 交互式）。返回 (rc, out, ms)。"""
    t0 = time.time()
    try:
        r = _proc.run_hidden(cmd, capture_output=True, timeout=timeout,
                           stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return None, "TIMEOUT（%ss 到）" % timeout, int((time.time() - t0) * 1000)
    except Exception as e:
        return None, "起进程失败：%s" % type(e).__name__, int((time.time() - t0) * 1000)
    out = ((r.stdout or b"") + (r.stderr or b"")).decode("utf-8", "replace").strip()
    return r.returncode, out, int((time.time() - t0) * 1000)


def _http(method, url, body=None, timeout=10, headers=None):
    """(status|None, text, ms)。唯只读／本机探；⛔ 例外外溢。"""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    h = {"Content-Type": "application/json"}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(6000).decode("utf-8", "replace"), int((time.time() - t0) * 1000)
    except urllib.error.HTTPError as e:
        return e.code, (e.read() or b"")[:600].decode("utf-8", "replace"), int((time.time() - t0) * 1000)
    except Exception as e:
        return None, type(e).__name__, int((time.time() - t0) * 1000)


def _tcp(host, port, t=3):
    s = socket.socket()
    s.settimeout(t)
    try:
        s.connect((host, port))
        return True
    except Exception:
        return False
    finally:
        s.close()

# ============================ probe（实测读数 ＋ 刻） ============================
def probe_card(cid):
    """逐卡之**实测**探（⛔ 填「可用」）。返回 `{status, probe, reading, rc, ms, at}`。"""
    spec = PROBES.get(cid)
    at = _now()
    if not spec:
        return {"status": "缺", "probe": "", "reading": "缺（本表 ⛔ 载此卡之探法）", "rc": None, "ms": 0, "at": at}
    kind = spec["kind"]
    if kind == "cli":
        path = _which(spec["bin"])
        if not path:
            return {"status": "absent", "probe": "%s --version" % spec["bin"],
                    "reading": "缺（`shutil.which` 空 · ⛔ 不在位）", "rc": None, "ms": 0, "at": at}
        rc, out, ms = _run([path] + list(spec.get("args") or ["--version"]), timeout=30)
        first = out.splitlines()[0].strip() if out else ""
        return {"status": ("ok" if rc == 0 else "err"),
                "probe": "%s %s" % (path, " ".join(spec.get("args") or ["--version"])),
                "reading": (first[:200] if first else "（无输出）"), "rc": rc, "ms": ms, "at": at}
    if kind == "http":
        st, txt, ms = _http(spec["method"], spec["url"], spec.get("body"), timeout=10)
        return {"status": ("ok" if st else "absent"),
                "probe": "%s %s" % (spec["method"], spec["url"]),
                "reading": "HTTP %s ｜ %s" % (st, (txt or "")[:220].replace("\n", " ")),
                "rc": st, "ms": ms, "at": at}
    if kind == "tcp":
        okp = _tcp(spec["host"], spec["port"])
        return {"status": ("ok" if okp else "absent"), "probe": "TCP %s:%s" % (spec["host"], spec["port"]),
                "reading": ("端口开" if okp else "端口闭"), "rc": (0 if okp else 1), "ms": 0, "at": at}
    if kind == "cdp":
        st, txt, ms = _http("GET", "http://127.0.0.1:9222/json/list", timeout=8)
        if st != 200:
            return {"status": "absent", "probe": "GET http://127.0.0.1:9222/json/list",
                    "reading": "缺（CDP %s）" % txt, "rc": st, "ms": ms, "at": at}
        try:
            tgs = json.loads(txt)
        except Exception:
            tgs = []
        hit = [t for t in tgs if spec["match"] in str(t.get("url") or "")]
        return {"status": ("ok" if hit else "absent"), "probe": "GET http://127.0.0.1:9222/json/list",
                "reading": ("命中 target %d ／ 共 %d" % (len(hit), len(tgs)) if hit
                            else "无 `%s` 之 target（该刻 · 共 %d）" % (spec["match"], len(tgs))),
                "rc": st, "ms": ms, "at": at}
    return {"status": "缺", "probe": "", "reading": "缺（探法未识：%s）" % kind, "rc": None, "ms": 0, "at": at}


def probe_api(pid):
    """云端 provider 之**最小调用**探（⛔ 烧 token：`max_tokens=1`）。"""
    base, key, model = _secret(pid)
    at = _now()
    spec = API_PROVIDERS.get(pid) or {}
    url = (base or "").rstrip("/") + spec.get("path", "/chat/completions")
    if not (base and key):
        return {"status": "缺", "probe": "POST %s" % url,
                "reading": "缺（base_url ／ key：key_set=%s）" % bool(key), "rc": None, "ms": 0, "at": at}
    st, txt, ms = _http("POST", url, {"model": model, "messages": [{"role": "user", "content": "1"}],
                                      "max_tokens": 1, "stream": False},
                        timeout=30, headers={"Authorization": "Bearer %s" % key})
    return {"status": ("ok" if st and st < 400 else "err"), "probe": "POST %s" % url,
            "reading": "HTTP %s ｜ %s" % (st, _redact(txt, key)[:200].replace("\n", " ")),
            "rc": st, "ms": ms, "at": at}


def refresh_probes(cards=None, with_api=False):
    """**唯此处**触实测；果 ⇒ 落件（`card_probes.json`）。⛔ 面只读缓存。"""
    if cards is None:
        from core.pa import roster as R
        cards = R.load().get("cards", [])
    out = {}
    for c in cards:
        cid = c.get("id")
        if cid:
            out[cid] = probe_card(cid)
    if with_api:
        for pid in API_PROVIDERS:
            out["api:%s" % pid] = probe_api(pid)
    doc = {"at": _now(), "version": INVOKE_VERSION, "source": "core/pa/agent_invoke.py",
           "surface": str(PROBE_CACHE), "count": len(out), "cards": out}
    try:
        PROBE_CACHE.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(doc, ensure_ascii=False, indent=2).encode("utf-8")
        tmp = str(PROBE_CACHE) + ".tmp"
        with open(tmp, "wb") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, str(PROBE_CACHE))
        doc["path"] = str(PROBE_CACHE)
        doc["sha16"] = _sha16(payload)
    except Exception as e:
        doc["path"] = ""
        doc["err"] = "落件失败（⛔ 静默）：%s" % type(e).__name__
    return doc


def load_probes():
    try:
        with open(PROBE_CACHE, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


# ============================ 二键之装配（唯 `invoke` ＋ `probe`） ============================
def _invoke_text(cid):
    spec = INVOKES.get(cid) or {"via": "none", "text": ""}
    if spec.get("via") == "cli":
        path = _which(spec.get("bin") or "")
        if not path:
            return "缺（`shutil.which` 空 · ⛔ 不在位）"
        return " ".join([path] + list(spec.get("args") or []) + ["\"<task>\""])
    return spec.get("text") or ""


def via_of(cid):
    """内部：卡之执行路（`seat` ／ `cli` ／ `api` ／ 其余 ⇒ 照实未核）。"""
    return str((INVOKES.get(cid) or {}).get("via") or "none")


def enrich_map(cards=None):
    """逐卡之**二键**（⛔ 网 ／ ⛔ 子进程 —— 唯读 `card_probes.json` 之缓存）。

    ⛔ 既存七键**一概不进**本表（承令「只增不改」）。
    """
    if cards is None:
        from core.pa import roster as R
        cards = R.load().get("cards", [])
    probes = (load_probes().get("cards") or {})
    out = {}
    for c in cards:
        cid = c.get("id")
        if not cid:
            continue
        out[cid] = {
            "invoke": _invoke_text(cid),
            "probe": probes.get(cid) or {"status": "缺", "reading": "缺（⛔ 未探 · 先 POST /v9/pa/roster/probe）",
                                          "at": None},
        }
    return out


def attach(doc):
    """给 `summary()` 之行补**二键**（`setdefault` ⇒ ⛔ 覆既有键）。"""
    if not isinstance(doc, dict) or not isinstance(doc.get("rows"), list):
        return doc
    try:
        m = enrich_map()
    except Exception:
        return doc
    for r in doc["rows"]:
        if isinstance(r, dict) and r.get("id") in m:
            for k in CARD_KEYS_ADDED:
                r.setdefault(k, m[r["id"]][k])
    return doc


def attach_cards(cards):
    """给**卡面**（`?full=1`）之卡补**二键**（`setdefault` ⇒ ⛔ 覆既有七键）。"""
    if not isinstance(cards, list):
        return cards
    try:
        m = enrich_map(cards)
    except Exception:
        return cards
    for c in cards:
        if isinstance(c, dict) and c.get("id") in m:
            for k in CARD_KEYS_ADDED:
                c.setdefault(k, m[c["id"]][k])
    return cards


#: ⭐ T2-刀14（2026-10-05）：`model` 之解 —— `dsh` provider 之 `models` ＝ `null`
#   ⇒ 旧形恒空 ⇒ 实测真网络 HTTP 400「you passed .」（真 `request_id`）
#   ⇒ ⛔ 以空 model 充「已接」。今解：① 环境变量 `PA_INVOKE_API_MODEL` ② 自身 `models`
#   ③ ⭐ **同 base 之兄弟 provider**（唯从 `config.json` 借真值 · ⛔ 硬编模型名）④ 空 ⇒ 照实「缺」。
def _first_model(v):
    """provider 自身之 `models[0].id`（空 ⇒ `""`）。"""
    try:
        return str(((v.get("models") or [{}])[0] or {}).get("id") or "")
    except Exception:
        return ""


def _model_for(doc, pid, base):
    """→ `(model, model_src)`；`model_src` ∈ `env / own / sibling:<pid> / 缺`。"""
    provs = ((doc.get("agents") or {}).get("providers") or {})
    env_m = (os.getenv("PA_INVOKE_API_MODEL") or "").strip()
    if env_m:
        return env_m, "env"
    own = provs.get(pid) or {}
    m = _first_model(own)
    if m:
        return m, "own"
    bh = urlparse(base or "").netloc
    if bh:
        for opid, ospec in API_PROVIDERS.items():
            if opid == pid:
                continue
            ov = provs.get(opid) or {}
            oenv = (ov.get("env") or {}) if isinstance(ov, dict) else {}
            ob = oenv.get(ospec["base_key"]) if ospec.get("base_key") else ospec.get("base_url")
            if ob and urlparse(ob).netloc == bh:
                om = _first_model(ov)
                if om:
                    return om, "sibling:%s" % opid
    return "", "缺"


# ============================ 册（可枚举）＋ 解析 ============================
def api_agents():
    """云端 api 之 agent（**真源** ＝ `config.json`；**唯布尔**入面 · ⛔ 值）。"""
    try:
        with open(CONFIG_JSON, encoding="utf-8-sig") as fh:
            doc = json.load(fh)
    except Exception:
        return []
    provs = ((doc.get("agents") or {}).get("providers") or {})
    out = []
    for pid, spec in API_PROVIDERS.items():
        v = provs.get(pid) or {}
        env = (v.get("env") or {}) if isinstance(v, dict) else {}
        base = env.get(spec["base_key"]) if spec.get("base_key") else spec.get("base_url")
        key = env.get(spec["key_key"])
        model, model_src = _model_for(doc, pid, base)
        out.append({
            "id": "api:%s" % pid, "provider": pid, "name": spec["label"],
            "kind": "api_provider", "from": "api",
            "invoke": "POST %s%s" % ((base or "").rstrip("/"), spec["path"]),
            "probe": (load_probes().get("cards") or {}).get("api:%s" % pid)
                     or {"status": "缺", "reading": "缺（⛔ 未探 · POST /v9/pa/roster/probe?with_api=1）", "at": None},
            "base_url": base or "", "key_env": spec["key_key"], "key_set": bool(key),
            "model": model, "model_src": model_src, "approved": True, "scope": "本机",
        })
    return out


def registry():
    """**册** ＝ 卡（能力端点）∪ 席 ∪ 云端 api。⛔ 未在此者 ⇒ 拒调。"""
    from core.pa import roster as R
    cards = R.load().get("cards", [])
    em = enrich_map(cards)
    rows = []
    for c in cards:
        r = {"id": c.get("id"), "name": c.get("name"), "kind": c.get("kind"), "from": "card",
             "invoke": (em.get(c.get("id")) or {}).get("invoke"),
             "probe": (em.get(c.get("id")) or {}).get("probe")}
        rows.append(r)
    probes = (load_probes().get("cards") or {})
    for s in R.seats():
        sid = s.get("id")
        rows.append({"id": sid, "name": s.get("name"), "kind": "seat", "from": "seat",
                     "invoke": "powershell -File %s agent send %s --prompt-file <件> --no-wait" % (PASEO_PS1, sid),
                     "probe": probes.get(sid) or {"status": "ok",
                                                  "reading": "在册（%s）" % ((s.get("access") or {}).get("source")),
                                                  "at": _now()}})
    rows.extend(api_agents())
    return rows


def resolve(agent_id):
    """→ (entry, err)。**未在册 ⇒ 拒调**（⛔ 静默兜底）。"""
    aid = str(agent_id or "").strip()
    if not aid:
        return None, "agent_id 空 ⇒ 拒调（⛔ 静默兜底）"
    for r in registry():
        if aid == str(r.get("id")) or aid == str(r.get("provider") or ""):
            return r, ""
    return None, "⛔ **未在册之 agent ⇒ 拒调**：%s（册 ＝ POST /v9/pa/agent/invoke 不带 agent_id）" % aid


def _entry_via(entry):
    """册行 ⇒ 执行路（⚠ ⛔ 以 `id` 之形猜 · 唯查真源表）。"""
    if entry.get("from") == "seat":
        return "seat"
    if entry.get("from") == "api":
        return "api"
    return via_of(str(entry.get("id") or ""))

# ============================ 密钥（唯布尔入面 · ⛔ 值） ============================
def _secret(pid):
    """**内部**取 base_url ＋ key ＋ model（key 唯此一处活一瞬 · ⛔ 返回值外泄）。

    ⛔ 本函数之返回**绝不**进任何面／日志／事件（承令「第一红线」）。
    """
    spec = API_PROVIDERS.get(pid)
    if not spec:
        return "", "", ""
    try:
        with open(CONFIG_JSON, encoding="utf-8-sig") as fh:
            doc = json.load(fh)
    except Exception:
        return "", "", ""
    v = (((doc.get("agents") or {}).get("providers") or {}).get(pid) or {})
    env = (v.get("env") or {}) if isinstance(v, dict) else {}
    base = env.get(spec["base_key"]) if spec.get("base_key") else spec.get("base_url")
    key = env.get(spec["key_key"]) or ""
    model, _msrc = _model_for(doc, pid, base)
    return (base or ""), key, model


def _redact(s, key):
    """**出口归一**：凡本进程所持之密钥 ⇒ 一律 `<redacted>`（⛔ 判据 3 之保证）。"""
    t = str(s or "")
    if key and len(key) > 6 and key in t:
        t = t.replace(key, "<redacted>")
    return t


def _gpu_used_mib():
    try:
        r = _proc.run_hidden(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                           capture_output=True, timeout=8, stdin=subprocess.DEVNULL)
        return int((r.stdout or b"").decode().strip().splitlines()[0])
    except Exception:
        return None


# ============================ 三类执行器（⛔ 另造运输） ============================
def _exec_seat(entry, task, timeout_s):
    """**复用**既有席之路（`core.pa.dispatch.SeatExecutor` ⇒ `paseo agent send`）。"""
    from core.pa.dispatch import SeatExecutor, make_contract

    seat = str(entry.get("id") or "")
    c = make_contract(str(task), to_seat=seat)
    ex = SeatExecutor(seat, timeout=timeout_s)
    r = ex.run(c)
    # ⭐ T2-刀4（PM 之令「凡派件须落台账 · ⛔ 投了不记」）：与 `/v9/pa/dispatch` **同行形**。
    try:
        from core.pa.dispatch import DispatchRecord, dispatch_and_review

        dispatch_and_review(c, r, record=DispatchRecord())
    except Exception:
        pass
    return {"ok": bool(r.get("ok")), "via": "seat", "rc": r.get("rc"),
            "out": {"task_id": c.get("task_id"), "stage": r.get("stage"),
                    "piece": r.get("artifact"), "capture": r.get("capture"),
                    "summary": r.get("summary"), "cmd": r.get("cmd")},
            "error": (None if r.get("ok") else r.get("error") or r.get("summary"))}


def _exec_cli(entry, task, timeout_s):
    """本机 CLI：起进程 ＋ **超时必带** ＋ `stdin=DEVNULL`（⛔ 交互式）。"""
    cid = str(entry.get("id") or "")
    spec = INVOKES.get(cid) or {}
    path = _which(spec.get("bin") or "")
    if not path:
        return {"ok": False, "via": "cli", "error": "缺（`shutil.which` 空 · ⛔ 不在位）"}
    cmd = [path] + list(spec.get("args") or []) + [str(task)]
    rc, out, ms = _run(cmd, timeout_s)
    return {"ok": (rc == 0), "via": "cli", "rc": rc, "ms": ms,
            "out": {"cmd": " ".join(cmd), "stdout": out[-4000:]},
            "error": (None if rc == 0 else "rc=%s（⛔ 交互式：stdin=DEVNULL · 超时 %ss）" % (rc, timeout_s))}


def _exec_api(entry, task, timeout_s):
    """云端 api：`base_url` ＋ 密钥**唯从 `config.json` 读**（⛔ 代操作他方平台）。"""
    pid = str(entry.get("provider") or "")
    spec = API_PROVIDERS.get(pid) or {}
    base, key, model = _secret(pid)
    if not (base and key):
        return {"ok": False, "via": "api",
                "error": "缺（base_url ／ key：%s ⇒ key_set=%s）" % (pid, bool(key))}
    url = base.rstrip("/") + spec.get("path", "/chat/completions")
    payload = {"model": model, "messages": [{"role": "user", "content": str(task)}],
               "max_tokens": int(os.getenv("PA_INVOKE_API_MAX_TOKENS", "256")), "stream": False}
    st, txt, ms = _http("POST", url, payload, timeout=timeout_s,
                        headers={"Authorization": "Bearer %s" % key})
    txt = _redact(txt, key)
    if not st or st >= 400:
        return {"ok": False, "via": "api", "rc": st, "ms": ms,
                "out": {"url": url, "model": model, "body": txt[:600]},
                "error": "HTTP %s（body 已过 `<redacted>` 归一）" % st}
    try:
        doc = json.loads(txt)
        ch = ((doc.get("choices") or [{}])[0].get("message") or {})
        content = ch.get("content") or ch.get("reasoning_content") or ""
        usage = doc.get("usage") or {}
        mid = doc.get("model")
    except Exception:
        content, usage, mid = txt[:2000], {}, ""
    return {"ok": bool(content), "via": "api", "rc": st, "ms": ms,
            "out": {"url": url, "model": mid or model, "content": content[:4000],
                    "usage": {k: usage.get(k) for k in ("prompt_tokens", "completion_tokens", "total_tokens")}},
            "error": (None if content else "回执空答（⛔ 非故障 · 照实报）")}


def _exec_probe(entry, timeout_s):
    """**机制之证**：走**同一** `_run` 路跑该卡之探命令（⛔ 烧 token ／ ⛔ 烧卡）。"""
    cid = str(entry.get("id") or "")
    spec = PROBES.get(cid) or {}
    if spec.get("kind") != "cli":
        return {"ok": False, "via": "probe",
                "error": "本卡之探非 CLI 路（kind=%s）⇒ 用 mode=auto" % spec.get("kind")}
    path = _which(spec.get("bin") or "")
    if not path:
        return {"ok": False, "via": "probe", "error": "缺（`shutil.which` 空）"}
    rc, out, ms = _run([path] + list(spec.get("args") or ["--version"]), timeout_s)
    return {"ok": (rc == 0), "via": "probe", "rc": rc, "ms": ms,
            "out": {"cmd": "%s %s" % (path, " ".join(spec.get("args") or ["--version"])),
                    "stdout": out[:800]},
            "error": (None if rc == 0 else "rc=%s" % rc)}


# ============================ 统一调用 ============================
_LOCAL_VIAS = ("cli", "local_http", "local_model", "mcp", "desktop")


def invoke(agent_id, task="", mode="auto", timeout_s=None):
    """统一调用：`{ok, agent_id, via, ms, out}`（`印` 由路由**载器**后补）。

    ⛔ 未在册 ⇒ 拒调；`agent_id` 空 ⇒ 回**册**（可枚举 · 供「知有哪些」）。
    """
    t0 = time.time()
    aid = str(agent_id or "").strip()
    if not aid:
        reg = registry()
        return {"ok": False, "agent_id": "", "via": None, "ms": 0,
                "out": {"registry": reg, "count": len(reg),
                        "note": "⛔ agent_id 空 ⇒ 回册（可枚举）"},
                "error": "agent_id 空 ⇒ 拒调（本回即「册」）"}
    entry, err = resolve(aid)
    if err:
        return {"ok": False, "agent_id": aid, "via": None,
                "ms": int((time.time() - t0) * 1000), "out": {"error": err}, "error": err}
    via = _entry_via(entry)
    mode = (mode or "auto").strip()
    if mode != "auto" and mode != via and not (mode == "probe" and via == "cli"):
        return {"ok": False, "agent_id": aid, "via": via, "ms": int((time.time() - t0) * 1000),
                "out": {"requested_mode": mode},
                "error": "mode `%s` 与卡之 `via=%s` 不合 ⇒ 拒调（⛔ 静默兜底）" % (mode, via)}
    try:
        to = int(timeout_s or DEFAULT_TIMEOUT)
    except Exception:
        to = DEFAULT_TIMEOUT
    to = max(1, min(MAX_TIMEOUT, to))

    gated, res = False, None
    if via in _LOCAL_VIAS:
        gated = True
        with _STAT_LOCK:
            if _STATS["active"] >= LOCAL_LIMIT:
                _STATS["waited"] += 1
        _LOCAL_SEM.acquire()
        with _STAT_LOCK:
            _STATS["active"] += 1
            _STATS["peak"] = max(_STATS["peak"], _STATS["active"])
    try:
        gpu0 = _gpu_used_mib() if gated else None
        if mode == "probe":
            res = _exec_probe(entry, to)
        elif via == "seat":
            res = _exec_seat(entry, task, to)
        elif via == "cli":
            res = _exec_cli(entry, task, to)
        elif via == "api":
            res = _exec_api(entry, task, to)
        else:
            res = {"ok": False, "via": via,
                   "error": "本卡之 `via=%s` ⛔ 有自动之路（L1 UI ／ 需 GUI ／ 未接）⇒ 照实「未核」" % via}
        if gated:
            res["local_gate"] = {"limit": LOCAL_LIMIT, "vram_used_mib_before": gpu0,
                                 "vram_used_mib_after": _gpu_used_mib(),
                                 "waited": stats()["waited"]}
    finally:
        if gated:
            with _STAT_LOCK:
                _STATS["active"] -= 1
                _STATS["runs"] += 1
            _LOCAL_SEM.release()

    ms = int((time.time() - t0) * 1000)
    res.setdefault("ms", ms)
    res["ms"] = int(res.get("ms") or ms)
    res["agent_id"] = aid
    res["entry"] = {"id": entry.get("id"), "kind": entry.get("kind"), "from": entry.get("from"),
                    "invoke": entry.get("invoke")}
    res["invoke_version"] = INVOKE_VERSION
    res["gated"] = gated
    return res


def face():
    """面之总览（只读）：册 ＋ 二键 ＋ 并发闸之态。"""
    rows = registry()
    return {"version": INVOKE_VERSION, "at": _now(),
            "surface": str(Path(__file__).resolve()),
            "count": len(rows), "agents": rows,
            "local_gate": stats(),
            "probe_cache": {"path": str(PROBE_CACHE),
                            "at": (load_probes() or {}).get("at"),
                            "sha16": (load_probes() or {}).get("sha16")},
            "note": "云端密钥**唯布尔**（key_set）· ⛔ 值；probe 须 POST /v9/pa/roster/probe 刷新"}