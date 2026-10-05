# -*- coding: utf-8 -*-
"""本机执行层 agent 扫描器 v2（PM 035 Q0 + 036 修正 + 037 §B.4 · 2026-10-05。

只读：PATH（which ＋ 全径 --version）／ 服务端口（TCP 探）／ home ／ npm 全局。
⛔ 不起会话；⛔ 不自动安装／信任；凭据 ⛔ 入卡。
果 ⇒ 灌**既有** roster（core/pa/roster.py）之卡形（PM 036：复用 /v9/pa/roster · ⛔ 新造接口）。

我一手之证（2026-10-05）：Windows 之 `.CMD` shim **裸名**调 subprocess 必 `WinError 2`
（`CreateProcess` 不补 `.CMD`）⇒ 须取 `shutil.which()` 之**全径**再调。

我一手之证二（PM 037 §B.4 · 阱）：`roster.upsert` 之局部并为 `{k: v for k, v in card.items() if v is not None}`
⇒ **`[]` ≠ `None`** ⇒ 空表会**覆盖**手填认识 ⇒ 本器对**既有卡**只并扫描能证之字段
（`access` ／ `verified`（只增）／ `kind` ／ `name` ／ `source`），⛔ 写 `role` ／ `capabilities` ／
`boundary` ／ `fragility` ／ `cost` ／ `next`；**新卡** ⇒ 可整卡写。
"""
import hashlib, json, os, shutil, socket, subprocess, time
from core.pa import _proc as _proc   # ⭐ 窗隐唯一出口（PM 2026-10-05 令 · ⛔ 各写 creationflags）

from core.pa import roster as _roster  # 单一真源：四种权 ＋ 席位册之径（⛔ 两处各持一表）

SCAN_VERSION = "2026-10-05.3"
TIMEOUT = 8

CANDIDATES = [
    {"id": "codex", "name": "Codex CLI", "kind": "coding_agent_cli", "command": ["codex"],
     "npm": "@openai/codex", "home": r"D:\codex-home", "level": "L2", "channel": "CLI (npm global)"},
    {"id": "pi", "name": "Pi Agent", "kind": "coding_agent_cli", "command": ["pi"],
     "npm": "@earendil-works/pi-coding-agent", "home": r"D:\paseo-home", "level": "L2",
     "channel": "CLI (npm global)"},
    {"id": "dsh", "name": "DeepSeek Harness", "kind": "coding_agent_cli", "command": ["dsh"],
     "npm": "@deepseek-ai/dsh", "home": r"~/.dsh", "level": "L2",
     "channel": "CLI (npm global) / claimed ACP"},
    {"id": "claude", "name": "Claude Code", "kind": "coding_agent_cli", "command": ["claude"],
     "npm": "@anthropic-ai/claude-code", "home": r"~/.claude", "level": "L0", "channel": ""},
]
SERVICES = [
    {"id": "ollama", "name": "Ollama (local model service)", "kind": "local_service",
     "host": "127.0.0.1", "port": 11434, "level": "L2", "channel": "HTTP"},
    {"id": "paseo_daemon", "name": "Paseo daemon", "kind": "local_service",
     "host": "127.0.0.1", "port": 6767, "level": "L2", "channel": "HTTP"},
    # PM 037 §C 第 30 号之令：服务面之源 ⛔ 唯常见端口表 ⇒ 并取**配置声明之端口**
    #（我一手探：5102 开 · V9 网关）
    {"id": "v9_gateway", "name": "V9 gateway", "kind": "local_service",
     "host": "127.0.0.1", "port": 5102, "level": "L2", "channel": "HTTP"},
]
CAPS_SOURCES = [r"D:\paseo-home\config.json"]  # 能力位唯取**声明处** · ⛔ 猜

LEVEL_BASIS = ("L4 native API/SDK > L3 MCP/ACP handshake > L2 doc/app entry (CLI, HTTP) "
               "> L1 UI automation > L0 unreachable")
UNVERIFIED = "Q0: existence+version only => boundary/fragility untested (unverified)"

# PM 037 §B.4：既有卡 ⇒ 只并扫描**能证**之字段；⛔ 传 `role`/`capabilities`/
# `boundary`/`fragility`/`cost`/`next`（`[]` ≠ `None` ⇒ 空表会抹掉手填之认识）。
SCAN_WRITABLE = ("id", "name", "kind", "access", "source")
SCAN_HAND_ONLY = ("role", "capabilities", "boundary", "fragility", "cost", "next")

# ---- T2-刀2（2026-10-05）：席位册（真源 ＝ `paseo agent ls --json`）＋ WSL 侧之扫 ----
SEAT_SOURCE = "paseo agent ls --json"
PASEO_TIMEOUT = 60

#: 席位之四权归口（**逐席附据** · ⛔ 装已证 —— 无据者书「未明」）
SEAT_GOVERNANCE = {
    "b136893": {"归口": "项目管理（PM）", "写码": "未明", "起停": True, "部署": True,
                "裁决复核": True, "据": "PM 090 §三「起停（我办）」＋ 诸令「落归我」＋ 诸裁"},
    "f202f89": {"归口": "内容工坊线（技术总监）", "写码": True, "起停": False, "部署": False,
                "裁决复核": "未明", "据": "诸稿（088／092／101）＋ 090 §四「起停（我办）」"},
    "b2a5182": {"归口": "V9 线（全史席 · CW）", "写码": True, "起停": True, "部署": "未明",
                "裁决复核": "未明", "据": "097 §二（`watch_ds.mjs` 之起停归 CW）＋ 诸 CW 稿"},
    "20a688e": {"归口": "审计线（V9 审计师）", "写码": "未明", "起停": "未明", "部署": "未明",
                "裁决复核": True, "据": "097 §一 四权分立之「复核（DSH-W）」"},
    "440488b": {"归口": "总经理（CEO）", "写码": "未明", "起停": "未明", "部署": "未明",
                "裁决复核": True, "据": "097 §一 四权分立之「裁决」＋ 老板之裁"},
}


def governance_source():
    """四权归口之**面之径逐字 ＋ 印**（T2-刀14 §二.7）。

    由：`/v9/pa/seats` 之 `governance` 逐席有值，而**其源无面** ⇒ 后人无从核
    （承 PM 099 §二「面须钉 · ⛔ 宽面」）⇒ 本函即其「钉」。
    """
    p = os.path.abspath(__file__)
    try:
        sha = hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
    except Exception:
        sha = ""
    return {"面之径逐字": p, "表": "SEAT_GOVERNANCE", "印": sha,
            "判据": "逐席附据（`据` 键）· **无据者书「未明」**（⛔ 装已证）",
            "注": "弱据（仅 `paseo agent ls --json` 之 name）者标 `**弱据**`"}


def _which(cmds):
    for c in cmds:
        p = shutil.which(c)
        if p:
            return p
    return ""


def _version(path):
    try:
        r = _proc.run_hidden([path, "--version"], capture_output=True, timeout=TIMEOUT)
    except Exception as e:
        return "", "err:%s" % type(e).__name__
    out = ((r.stdout or b"") + (r.stderr or b"")).decode("utf-8", "replace").strip()
    return (out.splitlines()[0].strip() if out else ""), ("rc 0" if r.returncode == 0 else "rc:%d" % r.returncode)


def _port(host, port):
    s = socket.socket()
    s.settimeout(2)
    try:
        s.connect((host, port))
        return True
    except Exception:
        return False
    finally:
        s.close()


def _npm_installed():
    npm = shutil.which("npm")
    out, root = {}, ""
    if not npm:
        return out, root
    try:
        root = _proc.run_hidden([npm, "root", "-g"], capture_output=True, timeout=TIMEOUT).stdout.decode("utf-8", "replace").strip()
    except Exception:
        return out, root
    if not os.path.isdir(root):
        return out, root
    for e in os.scandir(root):
        if not e.is_dir():
            continue
        if e.name.startswith("@"):
            for s in os.scandir(e.path):
                if s.is_dir():
                    out["%s/%s" % (e.name, s.name)] = s.path
        else:
            out[e.name] = e.path
    return out, root


def _declared():
    """能力位唯取声明处（Paseo config 之 params）· ⛔ 猜。"""
    out = {}
    for p in CAPS_SOURCES:
        try:
            with open(p, encoding="utf-8-sig") as f:
                provs = ((json.load(f).get("agents") or {}).get("providers") or {})
        except Exception:
            continue
        for pid, prov in provs.items():
            if isinstance(prov, dict) and isinstance(prov.get("params"), dict):
                out[pid] = {"caps": dict(prov["params"]), "src": p}
    return out


def probe():
    """原始探读数（供卡之 `verified` 引其探法）。"""
    npm_inst, root = _npm_installed()
    rows = []
    for c in CANDIDATES:
        path = _which(c["command"])
        ver, vst = _version(path) if path else ("", "")
        home = os.path.expanduser(c["home"])
        rows.append({"id": c["id"], "cmd": c["command"][0], "path": path,
                     "npm_ok": bool(npm_inst.get(c["npm"])), "npm_path": npm_inst.get(c["npm"], ""),
                     "home": home, "home_ok": os.path.isdir(home),
                     "version": ver, "version_probe": vst, "status": ("ok" if path else "absent")})
    return {"rows": rows,
            "services": [{"id": s["id"], "host": s["host"], "port": s["port"],
                          "status": ("ok" if _port(s["host"], s["port"]) else "absent")} for s in SERVICES],
            "npm_root": root, "scan_at": time.strftime("%Y-%m-%d %H:%M:%S"), "scan_version": SCAN_VERSION}


def scan_cards():
    """扫描之果 ⇒ roster 卡（PM 036 §二）。"""
    pr = probe()
    rows = {r["id"]: r for r in pr["rows"]}
    svcs = {s["id"]: s for s in pr["services"]}
    decl = _declared()
    cards = []
    for c in CANDIDATES:
        r = rows[c["id"]]
        absent = (r["status"] != "ok")
        v = [] if absent else ["probe:version `%s --version` (full path %s) => `%s` (%s)"
                               % (c["command"][0], r["path"], r["version"] or "n/a", r["version_probe"])]
        if r["npm_ok"]:
            v.append("probe:npm -g `%s` installed at %s" % (c["npm"], r["npm_path"]))
        if r["home_ok"]:
            v.append("probe:home dir exists %s" % r["home"])
        if c["id"] == "dsh" and decl.get("dsh"):
            v.append("declared:Paseo config %s => params %s (NOT handshake-verified)"
                     % (decl["dsh"]["src"], json.dumps(decl["dsh"]["caps"], ensure_ascii=False)))
        if absent:
            note = ("PATH / npm -g / home all negative => not reachable on this host; recorded as absent "
                    "(NOT 'does not exist'). " + UNVERIFIED)
            level = "L0"
        else:
            note = ("basis: %s. `%s` resolves to %s and answers --version => process-level entry, not UI "
                    "automation => L2. Not raised to L3 (no handshake probe) nor L4 (no native API/SDK "
                    "probe). %s" % (LEVEL_BASIS, c["command"][0], r["path"], UNVERIFIED))
            level = c["level"]
        cards.append({"id": c["id"], "name": c["name"], "kind": c["kind"],
                      "role": "execution-layer agent on this host", "capabilities": [],
                      "access": {"level": level, "channel": ("" if absent else c["channel"]),
                                 "entry": ("" if absent else (r["path"] or r["npm_path"])), "note": note},
                      "source": ("" if absent else ("PATH:%s" % r["path"] if r["path"] else "npm:%s" % r["npm_path"])),
                      "verified": v, "boundary": [], "fragility": [], "cost": "",
                      "next": ["Q1: handshake + capability probe (fills boundary/fragility)"]})
    for s in SERVICES:
        up = (svcs[s["id"]]["status"] == "ok")
        note = (("basis: %s. TCP connect %s:%d => open => HTTP process-level entry => L2. PATH-only scan "
                 "would MISS this one (no shim). %s" % (LEVEL_BASIS, s["host"], s["port"], UNVERIFIED))
                if up else UNVERIFIED)
        cards.append({"id": s["id"], "name": s["name"], "kind": s["kind"],
                      "role": "local service on this host", "capabilities": [],
                      "access": {"level": (s["level"] if up else "L0"), "channel": (s["channel"] if up else ""),
                                 "entry": (("%s:%d" % (s["host"], s["port"])) if up else ""), "note": note},
                      "source": (("PORT:%s:%d" % (s["host"], s["port"])) if up else ""),
                      "verified": (["probe:TCP connect %s:%d => open" % (s["host"], s["port"])] if up else []),
                      "boundary": [], "fragility": [], "cost": "",
                      "next": ["Q1: service handshake (fills boundary/fragility)"]})
    # ⭐ T2-刀2.1（2026-10-05）：**跨机**之 WSL 侧（⛔ 冒充本机 · 承 Dots §5）
    try:
        cards.extend(wsl_cards())
    except Exception as e:
        cards.append({"id": "dsh_wsl", "name": "DeepSeek Harness（WSL 侧）",
                      "kind": "coding_agent_cli", "role": "跨机执行器（WSL）",
                      "capabilities": [],
                      "access": {"level": "L0", "channel": "", "entry": "",
                                 "note": "跨机探失败（⛔ 静默）：%s" % type(e).__name__},
                      "source": "", "verified": [], "boundary": [], "fragility": [],
                      "cost": "", "next": ["Q1: 跨机通道之授权"]})
    return {"cards": cards, "npm_root": pr["npm_root"], "scan_at": pr["scan_at"],
            "scan_version": SCAN_VERSION, "source": "core/pa/agent_scan.py"}


# ---- 席位册 ＋ WSL（T2-刀2 · 2026-10-05）------------------------------------
def _paseo(args, timeout=PASEO_TIMEOUT):
    """调 `paseo`：唯取 `shutil.which()` 之**全径**（Windows `.CMD` shim 之阱 —— 本模块首注）。

    返回 (doc|None, err, sha16)。
    """
    p = shutil.which("paseo")
    if not p:
        return None, "paseo ⛔ 在 PATH（shutil.which）", ""
    try:
        r = _proc.run_hidden([p] + list(args), capture_output=True, timeout=timeout)
    except Exception as e:
        return None, "调起失败：%s" % type(e).__name__, ""
    raw = r.stdout or b""
    sha = hashlib.sha256(raw).hexdigest()[:16] if raw else ""
    if r.returncode != 0:
        return None, "rc=%s ／ stderr=%s" % (
            r.returncode, (r.stderr or b"")[:160].decode("utf-8", "replace")), sha
    try:
        return json.loads(raw.decode("utf-8", "replace")), "", sha
    except Exception as e:
        return None, "JSON 解析失败：%s" % type(e).__name__, sha


def seats_from_paseo():
    """席位册之**真源**：`paseo agent ls --json` ⇒ 每席一卡（⛔ 硬编 ／ ⛔ 凭印象）。

    返回 (cards, err, sha16_of_raw)。
    """
    doc, err, sha = _paseo(["agent", "ls", "--json"])
    if not isinstance(doc, list):
        return [], (err or "非数组"), sha
    rights = tuple(getattr(_roster, "GOVERNANCE_RIGHTS", ()))
    out = []
    for s in doc:
        if not isinstance(s, dict):
            continue
        sid = str(s.get("shortId") or s.get("id") or "").strip()
        if not sid:
            continue
        gov = dict(SEAT_GOVERNANCE.get(sid) or {})
        if "归口" not in gov:
            gov["归口"] = str(s.get("name") or "未明")
            gov["据"] = "paseo agent ls --json 之 name（**弱据** · ⛔ 装已证）"
        for _r in rights:  # ★ T2-刀14 §二.7：逐席**四权齐**（无据 ⇒ 「未明」· ⛔ 装已证）
            gov.setdefault(_r, "未明")
        held = [r for r in rights if gov.get(r) is True]
        out.append({
            "id": sid, "name": s.get("name"), "kind": "seat",
            "role": "PA 席（%s）" % (s.get("name") or sid),
            "capabilities": held, "governance": gov,
            "access": {"level": "L2", "channel": "paseo agent send", "entry": sid,
                       "note": "真源 `paseo agent ls --json`；投递唯 `paseo agent send`"},
            "verified": ["probe:`paseo agent ls --json` ⇒ shortId=%s provider=%s status=%s"
                         % (sid, s.get("provider"), s.get("status")),
                         "probe:cwd=%s" % s.get("cwd")],
            "boundary": [], "fragility": [], "cost": "",
            "next": ["Q1: 四权之据须逐席补（「未明」者 ⛔ 装已证）"],
            "source": SEAT_SOURCE, "state": str(s.get("status") or ""),
            "cwd": s.get("cwd"), "provider": s.get("provider"),
            "thinking": s.get("thinking"), "created": s.get("created"),
            "sha16": hashlib.sha256(json.dumps(s, ensure_ascii=False, sort_keys=True)
                                    .encode("utf-8")).hexdigest()[:16],
        })
    return out, "", sha


def wsl_probe(with_version=True):
    """WSL 侧之探（**跨机** · 承 Dots §5）：发行 ／ `dsh` 在位 ／ 版本。返回 (rows, err)。"""
    w = shutil.which("wsl")
    if not w:
        return {}, "wsl.exe ⛔ 在 PATH"
    rows = {}
    try:
        r = _proc.run_hidden([w, "-l", "-q"], capture_output=True, timeout=30)
        rows["distros"] = [x.strip() for x in
                           (r.stdout or b"").decode("utf-16-le", "replace").splitlines() if x.strip()]
        rows["distros_rc"] = r.returncode
    except Exception as e:
        rows["distros"], rows["distros_rc"] = [], "err:%s" % type(e).__name__
    for cmd, key in (("command -v dsh", "dsh_path"), ("dsh --version", "dsh_version")):
        if key == "dsh_version" and not (with_version and rows.get("dsh_path")):
            continue
        try:
            r = _proc.run_hidden([w, "sh", "-lc", cmd], capture_output=True, timeout=60)
            val = (r.stdout or b"").decode("utf-8", "replace").strip()
            rows[key] = val.splitlines()[0] if (val and key == "dsh_version") else val
            rows[key + "_rc"] = r.returncode
        except Exception as e:
            rows[key], rows[key + "_rc"] = "", "err:%s" % type(e).__name__
    return rows, ("" if rows.get("dsh_path") else "dsh ⛔ 在位")


def wsl_cards():
    """WSL 侧之卡（**跨机** · ⛔ 冒充本机）。"""
    rows, err = wsl_probe()
    present = bool(rows.get("dsh_path"))
    note = ("跨机（WSL）⇒ 须**显式通道**（`wsl.exe`）；⛔ 冒充本机可读。"
            if present else "跨机（WSL）之判据未过：%s" % (err or ""))
    return [{
        "id": "dsh_wsl", "name": "DeepSeek Harness（WSL 侧）",
        "kind": "coding_agent_cli", "role": "跨机执行器（WSL）",
        "capabilities": [],
        "access": {"level": ("L2" if present else "L0"),
                   "channel": ("wsl.exe ⇒ dsh" if present else ""),
                   "entry": ("WSL:%s" % rows.get("dsh_path") if present else ""),
                   "note": note, "distros": rows.get("distros"),
                   "dsh_version": rows.get("dsh_version")},
        "source": ("WSL:%s" % rows.get("dsh_path")) if present else "",
        "verified": (["probe:`wsl.exe -l -q` ⇒ %s" % ",".join(rows.get("distros") or []),
                      "probe:`wsl sh -lc command -v dsh` ⇒ %s" % rows.get("dsh_path"),
                      "probe:`wsl sh -lc dsh --version` ⇒ %s" % rows.get("dsh_version")]
                     if present else []),
        "boundary": [], "fragility": [], "cost": "",
        "next": ["Q1: 跨机通道之授权（承 Dots §5：本机访问须另行授权）"],
    }]


def save_seat_roster(seats=None, roster_mod=None):
    """席位册之**落件**（真源之落件 ⇒ 源在则凭在）。原样 ＋ fsync ＋ 原子替换。"""
    err, sha = "", ""
    if seats is None:
        seats, err, sha = seats_from_paseo()
    if roster_mod is None:
        from core.pa import roster as roster_mod
    at = time.strftime("%Y-%m-%d %H:%M:%S")
    doc = {"at": at, "source": SEAT_SOURCE, "source_sha16": sha,
           "scan_version": SCAN_VERSION, "count": len(seats),
           "counts": {"seats": len(seats)}, "seats": seats}
    path = roster_mod.seat_roster_path()
    payload = json.dumps(doc, ensure_ascii=False, indent=2).encode("utf-8")
    tmp = path + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(payload)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    return {"path": path, "count": len(seats), "at": at, "err": err,
            "sha16": hashlib.sha256(payload).hexdigest()[:16], "source_sha16": sha}


def _merge_existing(old, new):
    """既有卡：只并扫描**能证**之字段（PM 037 §B.4）。⛔ 传手填之栏。"""
    out = {k: new.get(k) for k in SCAN_WRITABLE if new.get(k) not in (None, "")}
    prev = list(old.get("verified") or [])
    for line in (new.get("verified") or []):
        if line not in prev:
            prev.append(line)
    out["verified"] = prev
    return out


def scan_and_upsert(roster_mod=None):
    """扫描 ⇒ 灌**既有** roster.upsert（⛔ 另立表）；既有卡 ⇒ **只增不减**。"""
    if roster_mod is None:
        from core.pa import roster as roster_mod
    out = scan_cards()
    getter = getattr(roster_mod, "get", None)
    results, modes = [], {}
    for c in out["cards"]:
        old = None
        if callable(getter):
            try:
                old = getter(c["id"])
            except Exception:
                old = None
        if old:
            results.append(roster_mod.upsert(_merge_existing(old, c)))
            modes[c["id"]] = "existing:merge"
        else:
            results.append(roster_mod.upsert(dict(c)))
            modes[c["id"]] = "new:full"
    out["upsert"] = results
    out["upsert_modes"] = modes
    # ⭐ T2-刀2.2（2026-10-05）：席位册之**落件**（真源 ＝ `paseo agent ls --json`）
    try:
        _seats, _serr, _ssha = seats_from_paseo()
        out["seat_roster"] = save_seat_roster(_seats, roster_mod=roster_mod)
        if _serr:
            out["seat_roster"]["err"] = _serr
    except Exception as e:
        out["seat_roster"] = {"path": "", "count": -1,
                              "err": "席位册落件失败（⛔ 静默）：%s" % type(e).__name__}
    return out