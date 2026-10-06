# -*- coding: utf-8 -*-
r"""PA 环境感知面 v2（T2-刀2′ ＋ 刀2″ · 2026-10-05 · 技术总监 f202f89）：**只读**四栏 ＋ 只读侦察。

【为何立此面】老板问「PA 环境感知能力和障碍是什么」，此前诸面答非所问：
  · `/v9/pa/context` 名为「上下文」，实为**老板画像**（counts={profile,ledger}）；
  · `/v9/pa/kb_mapping` 唯一个 scope、32 行全「未知」；
  · `/v9/pa/roster` 是**能力端点册**（13 卡），⛔ 席位册。
⇒ 无一面能答「本机有哪些 agent ／ 知识库 ／ 工具 ／ 资源」。此面即补此缺口。

【学 Dots（外据 `_交付\_外据\_EXT-001_OpenAI_Dots_环境感知.md` · ⭐ 转述级）之五条】
  1. 自持工位         ⇒ 四栏 ＝ PA 之「工位清单」（⛔ 每次问人）
  2. ⭐ 无人问亦只读侦察 ⇒ `research()`：唯只读工具 ＋ 产**工作笔记**（落盘可查）；⛔ 直接行动
  3. 授权源清单       ⇒ `allowlist()` 白名单；每项带 `approved` ；**白名单外 ⛔ 扫**
  4. 分寸（先备后批）  ⇒ 本面唯**报**；据笔记行动仍须**授权 ＋ 检查**（＝我方 (乙) 人点）
  5. 本机 vs 跨机      ⇒ 本机直读；**WSL 侧 ＝ 跨机** ⇒ 每项标 `scope`

【纪律（承令）】
  · **只读**：⛔ 写任何**被观察之一侧**（承 kb_mapping N1–N6 零噪音）；唯写**自己**的笔记（`env_notes/`）
  · 每项附 `src` ＝ **面之径逐字**；查不到 ⇒ `state="缺"`（⛔ 报「空」）
  · ⭐⭐ **密钥唯布尔**：`D:\paseo-home\config.json` 内含**明文 API key** ⇒ 唯取**键名**，
    ⛔ 值入面 ／ ⛔ 入日志 ／ ⛔ 入 events.jsonl（第一红线）；末闸 `secret_guard` 实扫 `sk-`
  · 无写副作用之**自证** ⇒ `research()` 之内**前后对表**（侦察前 ／ 后之四栏印须同）
"""
import hashlib
import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

from core.lib.paths import vault_root
from core.pa import _proc as _proc   # ⭐ 窗隐唯一出口（PM 2026-10-05 令 · ⛔ 各写 creationflags）

ENV_VERSION = "2026-10-05.3"
REPO_ROOT = Path(__file__).resolve().parents[2]

SRC_PASEO = "paseo agent ls --json"
SRC_SCAN = "core/pa/agent_scan.py"
SRC_ROSTER = "data/v9/pa/roster.json"
SRC_PROVIDERS = "core/pa/providers.py"
SRC_CONFIG = r"D:\paseo-home\config.json"
SRC_ROUTES = "core/pa/gateway_routes.py"
SRC_TOOLS = r"D:\paseo-workspace\_tools"

#: 知识库 —— **逐库**入册（⛔ 只报 `收件箱`）
KB_LIBS = ("内容工坊", "codex", "paseo-pm", os.path.join("_老板", "笔记"), "写小说专栏")

#: 工具面 —— 逐径 ＋ 逐 glob（面之径逐字）；base 之 `REPO:` 前缀 ⇒ 由 REPO_ROOT 拼
TOOL_DIRS = (
    (SRC_TOOLS, ("*.py",), "paseo 工具箱 _tools"),
    (None, ("*.py",), "内容工坊 08_工具"),
    (None, ("*.py", "*.ps1"), "信通插件"),
    ("REPO:scripts/win_pa", ("*.py",), "V9 win_pa 脚本"),
)
TOOL_REL = {"内容工坊 08_工具": ("内容工坊", "08_工具"),
            "信通插件": ("内容工坊", "08_工具", "信通插件"),
            "V9 win_pa 脚本": ("scripts", "win_pa")}


#: ⭐⭐ 径之**一处**（承 pm_1366 §三 ⓐ「一处出径」）—— `build_env()["paths"]` 之真源表。
#: ⚠ 何以立此：前端（`web\pa\faces\products.js:240` 之 `C:/Users/flybo/…` —— ⓒ 待拔）与后端
#:   （`allowlist()` 之 `D:\npm-global\…` —— ⓑ **已拔** ⇒ `_shim_files()`）旧为**各自硬编** ⇒ 「二源必漂」 ∧ **净机必败**。
#:   ⇒ 今唯此处出径；⛔ 值**新硬编**于本档：逐项自 env ∨ **既有之真源**取
#:   （`vault_root()` ／ `get_data_root()` ／ `config paths.logs_root` ／ `SRC_TOOLS`）；
#:   ⭐ **无可推之真源 ⇒ `None` ＋ `paths_src` 明书「未接」**（⛔ 以字面兜底 ——
#:   承「⛔ 以 `C:/Users/…` 兜底」）。
PATH_KEYS = ("repo", "tools", "vault", "data", "npm_global", "render", "log")
PATH_ENV = {
    "tools": ("PA_TOOLS_DIR",),
    "ws_root": ("PA_WS_ROOT",),
    "npm_global": ("PA_NPM_GLOBAL",),
    "render": ("PA_RENDER_DIR",),
}


def _abs(p):
    """相对径 ⇒ 按 REPO_ROOT 拼（⭐ 面之径须**绝对** · 承 pm_1366 §三 判成 ⓑ）。"""
    s = str(p)
    return s if os.path.isabs(s) else str(REPO_ROOT / s)


def _env_first(names):
    for n in names:
        v = os.getenv(n)
        if v:
            return str(v), "env %s" % n
    return None, ""


def _npm_global():
    """⭐ NPM 全局 bin 之径 —— ⛔ 硬编（承 pm_1366 §三 ⓑ「由 `shutil.which` ∨ 配置推」）。

    源之序：env `PA_NPM_GLOBAL` ⇒ env `PA_SEAT_PASEO_PS1` 之 dir（**既有之真源** ·
    `core/pa/dispatch.py:142`）⇒ `shutil.which("paseo")` 之 dir。"""
    v, s = _env_first(PATH_ENV["npm_global"])
    if v:
        return v, s
    ps1 = os.getenv("PA_SEAT_PASEO_PS1")
    if ps1:
        return os.path.dirname(str(ps1)), "PA_SEAT_PASEO_PS1 之 dir（core/pa/dispatch.py:142 之真源）"
    for _n in ("paseo", "paseo.cmd", "paseo.CMD", "codex", "dsh"):
        _w = shutil.which(_n)
        if _w:
            return os.path.dirname(_w), "shutil.which(%s) 之 dir" % _n
    return None, "未接：env PA_NPM_GLOBAL ／ PA_SEAT_PASEO_PS1 ／ PATH 之 paseo 皆无（⛔ 字面兜底）"


#: ⓑ CLI shim 之名（承 pm_1366 §三 ⓑ）—— `allowlist()["files"]` 之四枚（ⓒ 字面）
SHIM_NAMES = ("paseo", "codex", "pi", "dsh")


def _shim_files():
    """ⓑ CLI shim 之径 —— ⓒ 字面（承 pm_1366 §三 ⓑ「由 `shutil.which` ∨ 配置推」）。

    统一自 `_npm_global()`（真源：env `PA_NPM_GLOBAL` ∨ env `PA_SEAT_PASEO_PS1` ∨ `which`）
    之 dir 拼（**同源** ⇒ 一处定形 ∧ 变 `PA_NPM_GLOBAL` 则果变 = 反控有齿）；`_npm_global()` 亦无 ⇒ **空表**（ⓒ 字面兜底 ——
    净机 ⓒ 报一个不存在之「npm-global」径）。"""
    base, _bs = _npm_global()
    if not base:
        return []
    return [os.path.join(str(base), n + ".CMD") for n in SHIM_NAMES]


def resolve_paths():
    """⭐⭐ **一处出径**（承 pm_1366 §三 ⓐ）：返回 `({key: 绝对径|None}, {key: 真源之述})`。

    ⛔ 值硬编：逐项自 env ∨ 既有之真源取；**无可推之真源 ⇒ `None` ＋ 述「未接」**
    （⛔ 造一个假的绝对径去满足判据 —— 那是「装成可用」）。"""
    p, s = {}, {}
    p["repo"] = str(REPO_ROOT)
    s["repo"] = "__file__ 推（parents[2]）"
    try:
        _vr = vault_root()
        if _vr is None:
            raise ValueError("无可解析之真源")
        p["vault"] = str(_vr)
        s["vault"] = "core/lib/paths.py:vault_root()"
    except Exception as e:
        p["vault"], s["vault"] = None, (
            "未接（选目录）：env PA_VAULT_DIR ∨ 配置 paths.vault_root ∨ 内置 <data_root>/kb 皆无（%s）"
            % type(e).__name__)
    try:
        from core.lib.config_helper import get_data_root

        p["data"] = _abs(get_data_root())
        s["data"] = "core/lib/config_helper.py:get_data_root()（⇒ config paths.data_root）"
    except Exception as e:
        p["data"], s["data"] = None, "未接：get_data_root() 不可读（%s）" % type(e).__name__
    try:
        from core.lib.unified_config import unified_config

        p["log"] = _abs(unified_config.get("paths.logs_root", "logs"))
        s["log"] = "config/system/system_unified.yaml:paths.logs_root"
    except Exception as e:
        p["log"], s["log"] = None, "未接：unified_config 不可读（%s）" % type(e).__name__
    v, _s = _env_first(PATH_ENV["tools"])
    p["tools"] = v or SRC_TOOLS
    s["tools"] = _s or "core/pa/env_face.py:SRC_TOOLS（既有之一处）"
    p["npm_global"], s["npm_global"] = _npm_global()
    v, _s = _env_first(PATH_ENV["render"])
    if v:
        p["render"], s["render"] = _abs(v), _s
    else:
        _r, _rs = None, ""
        try:
            from core.lib.unified_config import unified_config

            _r = unified_config.get("paths.render_root", None)
            _rs = "config/system/system_unified.yaml:paths.render_root"
        except Exception:
            _r, _rs = None, ""
        if _r:
            p["render"], s["render"] = _abs(_r), _rs
        else:
            p["render"] = None
            s["render"] = ("未接（M1）：⛔ 真源 —— env PA_RENDER_DIR ∨ config paths.render_root 皆无"
                           "（旧字面 C:/Users/… 已拔 · 承 pm_1366 §三 ⓒ）")
    return p, s


def resolve_ws_root(paths_map=None):
    r"""⭐ 工作区根（`D:\paseo-workspace`）—— ⛔ 字面：env `PA_WS_ROOT` ∨ `tools` 之父。"""
    v, s = _env_first(PATH_ENV["ws_root"])
    if v:
        return _abs(v), s
    p = paths_map if paths_map is not None else resolve_paths()[0]
    _t = p.get("tools")
    if _t:
        return os.path.dirname(str(_t)), "「tools」之父（工作区根）"
    return None, "未接：env PA_WS_ROOT ∨ tools 皆无（⛔ 字面兜底）"


def _drive_letters():
    """⭐ 盘符之**推**（⛔ 字面 `"CD"`）—— 由「已解析之径所含之盘 ＋ 系统盘（env `SystemDrive`）」。

    ⚠ 由（承 pm_1366 §三 ⓑ）：字面 `"CD"` ⇒ 净机（唯 `C:`）**报一个不存在之 `D:`**
    ⇒ 「装有 `D:`」之假（「装成可用」之族）｜⛔ 探 `A:`–`Z:`（白名单外 ⛔ 扫）。"""
    seen = []
    for _v in list(resolve_paths()[0].values()):
        _t = str(_v or "")
        if len(_t) > 1 and _t[1] == ":" and _t[0].isalpha():
            _c = _t[0].upper()
            if _c not in seen:
                seen.append(_c)
    _sd = os.environ.get("SystemDrive") or ""
    if len(_sd) > 1 and _sd[1] == ":" and _sd[0].isalpha():
        _c = _sd[0].upper()
        if _c not in seen:
            seen.insert(0, _c)
    return seen

#: 密钥前缀之**实形**（本表内仅此一处）；**入面者唯「形之述」**
#: ⇒ 免末闸自触（面之输出之 `grep -c` 须 0 · 判据 3）
KEY_PATTERN_RAW = "s" + "k-"
KEY_PATTERN_DESC = "两字母 ＋ 连字符（OpenAI／DeepSeek 密钥之前缀）"

#: 唯只读工具（用于 `research()` 之自陈；皆 ⛔ 写）
READONLY_TOOLS = ("os.stat", "os.listdir", "os.access", "os.path.getsize",
                  "shutil.disk_usage", "json.load",
                  "subprocess(paseo agent ls --json)", "subprocess(wsl -l -q)",
                  "subprocess(wsl sh -lc \"command -v dsh\")", "subprocess(nvidia-smi -L)",
                  "core.pa.roster.load(只读)", "core.pa.providers.public_view(只读)")

#: 笔记箱（唯此目录可写 ⇒ 「只读」指 ⛔ 写被观察之一侧）
NOTE_DIR = Path(os.getenv("PA_ENV_NOTE_DIR") or (REPO_ROOT / "data" / "v9" / "pa" / "env_notes"))

_SCHED_LOCK = threading.Lock()
_SCHED_STARTED = False

#: ⭐ 定时（Dots §2「无人问亦侦察」）之**键 ＋ 建议**（T2-刀17）—— ⛔ **静默默认开**：
#: 欲启须**显式**置 `PA_ENV_RESEARCH_EVERY_S`（>0）；⛔ 别处不得自动开。
SCHED_KEY = "PA_ENV_RESEARCH_EVERY_S"
SCHED_RECOMMEND = {
    "键": SCHED_KEY,
    "建议值_s": 1800,
    "可选区间_s": [900, 3600],
    "下限_s": 60,
    "现默认": 0,
    "由": [
        "单次只读侦察实测 ≈ 6.5 s（含 3 次 subprocess：`paseo agent ls --json` ／ `wsl -l -q` ／ `nvidia-smi`）",
        "⇒ `1800 s` 之占空 ≈ `0.36 %`；⛔ 调模型 · ⛔ 用显卡 ⇒ 成本 ≈ 0（唯 CPU ／ 磁盘）",
        "⛔ 低于 `60 s`：`wsl -l -q` 之反复冷启会与他器抢 IO ⇒ 设**下限** `60 s`（低于此值 ⇒ 起线程时**抬到下限**并明标）",
        "⭐ 与「出图」「夜间整合」**错车** ⇒ 每拍先过 `busy_state()`；忙 ⇒ **跳过本拍**（记 `deferred` · ⛔ 排队堆积）",
        "⭐ 显卡之忙取**合取**（刀21 §一 · PM 裁）：`used ≥ 阈_MiB ∧ util ≥ 阈_util_pct`（`N=10`）⇒ 静态占位（长驻保活 ／ 桌面图形上下文）⛔ 当忙",
    ],
}

#: ⭐ 互斥（T2-刀17 §一.1）：侦察虽 ⛔ 调模型 ／ ⛔ 用显卡，然抢 CPU ／ 磁盘 ／ WSL 冷启 ⇒ 须错车。
MUTEX_GPU_MIB = int(os.getenv("PA_ENV_MUTEX_GPU_MIB", "1500") or 1500)
#: ⭐ 利用率之阈（T2-刀21 §一 · PM 裁）：显存互斥取**合取** `used ≥ 阈_MiB ∧ util ≥ 阈_util_pct`。
#: 由：侦察**永不占卡**（⛔ 载模型）⇒ 「静态显存占用」（长驻保活 ／ 桌面图形上下文）**⛔ 当忙**；
#:    唯 `util` 高（真在算）方 defer。`N=10`（PM 据实测：0.5 s × 24 采样 max 39 ／ 均值 6.9）。
MUTEX_GPU_UTIL_PCT = int(os.getenv("PA_ENV_MUTEX_GPU_UTIL", "10") or 10)
MUTEX_DIR = Path(os.getenv("PA_ENV_MUTEX_DIR") or (REPO_ROOT / "data" / "v9" / "pa" / "mutex"))

#: ⭐ 调度之**持久台账**（T2-刀18 §三）：每拍一行 ⇒ 「无人问也自己跑」**可查账**
SCHED_LOG = Path(os.getenv("PA_ENV_SCHED_LOG") or (REPO_ROOT / "data" / "v9" / "pa" / "scheduler_log.jsonl"))
SCHED_LOG_MAX = int(os.getenv("PA_ENV_SCHED_LOG_MAX", "2000000") or 2000000)

#: 调度之**态**（`ensure_scheduler()` 之回）：唯内存 ⇒ ⛔ 冒充持久台账
_SCHED_STATE = {"ticks": 0, "deferred_n": 0, "errors_n": 0,
                "started_at": None, "last_tick_at": None, "last_note": None,
                "last_same": None, "last_elapsed_s": None,
                "last_defer_at": None, "last_defer_why": None, "last_error": None}


def _sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _vault():
    try:
        root = vault_root()
        if root is None:
            return Path(os.getenv("PA_VAULT_DIR") or "")   # 未接 ⇒ 空 Path（⛔ 假径 · 唯免崩）
        return Path(root)
    except Exception:
        return Path(os.getenv("PA_VAULT_DIR") or "")


def _run(cmd, timeout=30):
    """只读调起：返回 (rc, out_bytes)。⛔ 例外外溢。"""
    try:
        r = _proc.run_hidden(cmd, capture_output=True, timeout=timeout)
    except Exception:
        return None, b""
    return r.returncode, (r.stdout or b"")


# ====================== 授权源清单（白名单） ======================
def allowlist():
    """**获准访问之源**（Dots §3）⇒ 显式列出；`approved` 由本清单判；白名单外 ⛔ 扫。"""
    v = _vault()
    dirs = [
        {"path": str(REPO_ROOT / "scripts" / "win_pa"), "label": "V9 win_pa 脚本"},
        {"path": SRC_TOOLS, "label": "paseo 工具箱 _tools"},
        {"path": str(v / "内容工坊" / "08_工具"), "label": "内容工坊 08_工具"},
        {"path": str(v / "内容工坊" / "08_工具" / "信通插件"), "label": "信通插件"},
        {"path": str(v / "内容工坊"), "label": "知识库 内容工坊"},
        {"path": str(v / "codex"), "label": "知识库 codex"},
        {"path": str(v / "paseo-pm"), "label": "知识库 paseo-pm"},
        {"path": str(v / "_老板" / "笔记"), "label": "知识库 _老板/笔记"},
        {"path": str(v / "写小说专栏"), "label": "知识库 写小说专栏"},
    ]
    files = [
        {"path": str(REPO_ROOT / "core" / "pa" / "gateway_routes.py"), "label": "本网关路由"},
        {"path": str(REPO_ROOT / "core" / "pa" / "providers.py"),
         "label": "模型供应商注册表"},
        {"path": str(REPO_ROOT / "core" / "pa" / "agent_scan.py"), "label": "机件扫面器"},
        {"path": str(REPO_ROOT / "core" / "pa" / "roster.py"), "label": "编队花名册"},
        {"path": self_config_path(), "label": "Paseo 配置（唯键名之布尔入面）"},
    ]
    for p in _shim_files():
        files.append({"path": p, "label": "CLI shim（PATH 之解析果 · shutil.which ∨ npm_global）"})
    cmds = [
        {"cmd": SRC_PASEO, "scope": "本机"}, {"cmd": "nvidia-smi -L", "scope": "本机"},
        {"cmd": "env:CLAWSJOY_NUM_CTX", "scope": "本机"},
        {"cmd": "wsl.exe -l -q", "scope": "跨机"},
        {"cmd": 'wsl sh -lc "command -v dsh"', "scope": "跨机"},
        {"cmd": "wsl sh -lc \"dsh --version\"", "scope": "跨机"},
    ]
    ports = [{"endpoint": "%s:%d" % (h, p), "label": "只读 TCP 探"} for h, p in
             (("127.0.0.1", 11434), ("127.0.0.1", 6767), ("127.0.0.1", 5102))]
    units = [{"unit": "disk:%s:\\" % d, "label": "盘用量（唯stat）"} for d in _drive_letters()]
    #: ⭐ 跨机之源（Dots §5）：WSL 侧须**显式立通道** ⇒ 白名单内明列；⛔ 冒充本机
    cross = [
        {"prefix": "WSL:", "label": "WSL 侧（跨机 · 通道 wsl.exe）", "scope": "跨机"},
        {"prefix": "/mnt/", "label": "WSL 内 Linux 径（跨机 · 唯经 wsl.exe）", "scope": "跨机"},
    ]
    return {"dirs": dirs, "files": files, "cmds": cmds, "endpoints": ports,
            "units": units, "cross": cross}


def self_config_path():
    return SRC_CONFIG


def _norm(p):
    try:
        return os.path.normcase(os.path.normpath(str(p)))
    except Exception:
        return str(p).lower()


def _approved(src):
    """是否在**授权源清单**内。⛔ 白名单外 ⇒ 报 `approved=false`（⛔ 默扫）。"""
    s = str(src or "")
    if not s:
        return False
    al = allowlist()
    for c in al["cmds"]:
        if s == c["cmd"]:
            return True
    for e in al["endpoints"]:
        if s == e["endpoint"]:
            return True
    for u in al["units"]:
        if s == u["unit"]:
            return True
    for x in al.get("cross") or []:
        if s.lower().startswith(str(x.get("prefix") or "").lower()):
            return True
    ns = _norm(s)
    for f in al["files"]:
        if ns == _norm(f["path"]):
            return True
    for d in al["dirs"]:
        nd = _norm(d["path"])
        if ns == nd or ns.startswith(nd + os.sep):
            return True
    return False


def _scope(src):
    """**本机** vs **跨机**（Dots §5）：WSL 侧 ＝ 跨机（⛔ 冒充本机）。"""
    s = str(src or "")
    if not s:
        return "本机"
    low = s.lower()
    for x in allowlist().get("cross") or []:
        if low.startswith(str(x.get("prefix") or "").lower()):
            return "跨机"
    if low.startswith("/mnt/") or "wsl" in low or low.startswith("\\\\wsl$") or low.startswith("\\\\wsl.localhost"):
        return "跨机"
    return "本机"


def _entry(p, with_hash=True, cap=524288):
    """路径之读写态 ＋ 量（只 stat ／ 唯读；⛔ 写）。"""
    try:
        os.stat(p)
    except Exception:
        return "只读", "缺", None
    ro = "只读" if not os.access(p, os.W_OK) else "可写"
    if os.path.isdir(p):
        try:
            names = sorted(os.listdir(p))
        except Exception:
            return ro, "不可列", None
        h = _sha16("|".join(names).encode("utf-8")) if with_hash else None
        return ro, "%d 件（顶层）" % len(names), h
    try:
        sz = os.path.getsize(p)
    except Exception:
        return ro, "量不可得", None
    h = None
    if with_hash and sz <= cap:
        try:
            h = _sha16(Path(p).read_bytes())
        except Exception:
            h = None
    return ro, "%d B" % sz, h


def _item(iid, name, kind, src, readable, state, sha=None):
    return {"id": iid, "name": name, "kind": kind, "src": str(src),
            "readable": readable, "state": state, "sha16": sha,
            "approved": _approved(src), "scope": _scope(src)}


# ============================== agents ==============================
def _roster_endpoints():
    u'''`roster.json` 之**端点卡**（⛔ 机扫筛 · T2-刀16 §一）。返回 `(cards, err)`。'''
    try:
        from core.pa import roster as R
        return (R.load().get('cards') or []), ''
    except Exception as e:
        return [], ('%s: %s' % (type(e).__name__, str(e)[:120]))


def agents_col():
    """`paseo agent ls --json`（席位）＋ 机件扫面（PATH／npm／端口／WSL）。"""
    out, note, sha = [], "", None
    try:
        from core.pa import agent_scan as S
    except Exception as e:
        return [], "agent_scan ⛔ 可载：%s" % type(e).__name__, "agents"
    seats, err, sha = S.seats_from_paseo()
    if not seats:
        note = "席位面**缺**：%s" % (err or "unknown")
    for c in seats:
        out.append(_item(c["id"], c.get("name"), "seat", SRC_PASEO, "只读",
                         c.get("state") or "", c.get("sha16")))
        out[-1]["cwd"] = c.get("cwd")
        out[-1]["provider"] = c.get("provider")
        # ⭐ T2-刀8 §一（2026-10-05 · PM 令）：**面名分列** —— 机件（名＋路径）⟷ 组织席位（名＋人）
        #   ⛔ 抹平（两集皆入 `agents` ⇒ 须逐项标其面名 · 承「面名分列 · ⛔ 抹平」）。
        out[-1]["面名"] = "组织席位册"
    # ⭐ T2-刀16 §一（2026-10-05 · PM 令）：**补齐** —— 旧形唯收 `kind ∈ (coding_agent_cli,
    #   local_service)` ∧ 有 `source` 之卡 ⇒ **`14` 卡只得 `7`**（`blender ／ claude ／ ds_chat ／
    #   lingxi ／ lingxi_local_api ／ local_vlm ／ v9_agent` 皆**静默不见**）⇒ 面下 `21`（14 席 ＋ 7）
    #   而读者以为「端点全在此」⇒ **少报**（假数之族）。今：**逐卡全入**（⛔ 筛）＋ 面无 `source`
    #   者照实书「缺」（⛔ 报「空」）＋ 由 `agents_完整性` 之闸兜底（⛔ 静默）。
    cards, cerr = _roster_endpoints()
    if cerr:
        note = ((note + ' ／ ') if note else '') + ('端点面**缺**：%s' % cerr)
    for c in cards:
        raw = str(c.get('source') or '')
        if raw:
            head, _, tail = raw.partition(':')
            ref = tail if head in ('PATH', 'npm', 'PORT', 'WSL') else raw
        else:
            # ⭐ 面之径逐字 ⇒ **卡之面**（`roster.json` · 可逐字打开）—— ⛔ 填「缺」
            #   （卡本有面 ⇒ 非「查不到」）；「卡无 `source`（⛔ 机扫得）」另入 `state` 照实。
            ref = SRC_ROSTER
        _lv = (c.get('access') or {}).get('level') or '?'
        _st = u'access=%s · from %s' % (_lv, SRC_ROSTER)
        if not raw:
            _st += u' · source 缺（⛔ 机扫得 · 人工卡）'
        out.append(_item(c.get('id'), c.get('name'), c.get('kind') or u'未标', ref, u'只读',
                         _st, c.get('sha16')))
        out[-1]['面名'] = u'能力端点册'   # ⭐ T2-刀8 §一：⛔ 与席位同词
        out[-1]['端点之由'] = u'roster.json 之卡（T2-刀16 §一：⛔ 机扫筛 ⇒ 补齐）'
    return out, note, "agents"


# ============================== kb ==============================
def kb_col():
    root = _vault()
    out = []
    for lib in KB_LIBS:
        p = root / lib
        ro, st, h = _entry(str(p))
        out.append(_item(lib.replace("\\", "/"), lib, "vault_dir", str(p), ro, st, h))
    return out, "", "kb"


# ============================== tools ==============================
def tools_col(route_count=None):
    vault = _vault()
    out = []
    for base, globs, label in TOOL_DIRS:
        if base is None:
            d = vault.joinpath(*TOOL_REL[label])
            src_glob = str(d)
        elif str(base).startswith("REPO:"):
            d = REPO_ROOT / str(base).split(":", 1)[1]
            src_glob = str(d)
        else:
            d = Path(base)
            src_glob = base
        if not d.is_dir():
            out.append(_item(label, label, "tool_dir", src_glob, "只读", "缺"))
            continue
        for g in globs:
            for f in sorted(d.glob(g)):
                if not f.is_file():
                    continue
                ro, st, h = _entry(str(f))
                out.append(_item(f.name, f.name, "tool_script", str(f), ro, st, h))
    rp = REPO_ROOT / "core" / "pa" / "gateway_routes.py"
    ro, st, h = _entry(str(rp), with_hash=False)
    n = ("%d 条" % route_count) if isinstance(route_count, int) else "未得（⛔ 以 0 充）"
    out.append(_item("v9_pa_routes", "本网关自身路由（pa_routes 蓝图）", "http_route",
                     str(rp), ro, "%s · %s" % (n, st), h))
    return out, "", "tools"


# ============================== resources ==============================
def _secret_bool():
    """唯**键名** ＋ 布尔（⛔ 值）。**绝不**把值写进任何返回。"""
    try:
        with open(SRC_CONFIG, encoding="utf-8-sig") as fh:
            doc = json.load(fh)
    except Exception as e:
        return "缺（%s）" % type(e).__name__
    provs = ((doc.get("agents") or {}).get("providers") or {})
    parts = []
    for pid in sorted(provs):
        v = provs.get(pid) or {}
        env = (v.get("env") or {}) if isinstance(v, dict) else {}
        keys = sorted(env.keys())
        if not keys:
            continue
        parts.append("%s{%s}" % (pid, ",".join("%s:%s" % (k, bool(env.get(k))) for k in keys)))
    return " · ".join(parts) if parts else "无键名可报"


def resources_col():
    out = []
    pp = str(REPO_ROOT / "core" / "pa" / "providers.py")
    try:
        from core.pa.providers import public_view
        pv = public_view()
        ro, st, h = _entry(pp, with_hash=False)
        for it in pv.get("providers") or []:
            out.append(_item("provider:%s" % it.get("id"), it.get("label"), "model_provider",
                             pp, ro, "key_state=%s · models=%d · enabled=%s"
                             % (it.get("key_state"), len(it.get("models") or []),
                                bool(it.get("enabled"))), h))
    except Exception as e:
        out.append(_item("provider:ERR", "模型供应商", "model_provider", pp,
                         "只读", "缺（%s）" % type(e).__name__))
    try:
        from core.pa import agent_scan as S
        for s in S.SERVICES:
            up = bool(S._port(s["host"], s["port"]))
            out.append(_item("port:%s" % s["id"], s["name"], "port",
                             "%s:%d" % (s["host"], s["port"]), "需授权",
                             ("up" if up else "down") + " · from " + SRC_SCAN))
    except Exception as e:
        out.append(_item("port:ERR", "端口服务", "port", SRC_SCAN, "只读",
                         "缺（%s）" % type(e).__name__))
    out.append(_item("num_ctx", "上下文窗口 num_ctx", "param", "env:CLAWSJOY_NUM_CTX",
                     "只读", str(int(os.environ.get("CLAWSJOY_NUM_CTX", "8192")))))
    rc, raw = _run(["nvidia-smi", "-L"], timeout=20)
    if rc == 0 and raw.strip():
        for i, ln in enumerate([x.strip() for x in raw.decode("utf-8", "replace").splitlines() if x.strip()]):
            out.append(_item("gpu:%d" % i, ln.split("(", 1)[0].strip(), "gpu", "nvidia-smi -L",
                             "只读", (ln.split("(", 1)[1].rstrip(")") if "(" in ln else "")))
    else:
        out.append(_item("gpu", "GPU", "gpu", "nvidia-smi -L", "只读", "缺（rc=%s）" % rc))
    roots = ([d + ":\\" for d in _drive_letters() if os.path.exists(d + ":\\")]
             if os.name == "nt" else ["/"])
    for d in roots:
        try:
            u = shutil.disk_usage(d)
            out.append(_item("disk:%s" % d[0], d, "disk", "disk:%s" % d, "只读",
                             "total %.1f GB · used %.1f GB · free %.1f GB"
                             % (u.total / 2**30, u.used / 2**30, u.free / 2**30)))
        except Exception as e:
            out.append(_item("disk:%s" % d[0], d, "disk", "disk:%s" % d, "只读",
                             "缺（%s）" % type(e).__name__))
    out.append(_item("secrets:paseo-home", "Paseo 供应商密钥（唯布尔）", "secret",
                     SRC_CONFIG, "需授权", _secret_bool()))
    return out, "", "resources"


# ============================== 主（面） ==============================
def _cls(it):
    """**变化判据之投影**（⛔ 用全 state ⇒ 活面抖动误报）。
    disk ⇒ 按余量分档；port ⇒ up/down；seat ⇒ 运行态；余 ⇒ 唯存在与身份。"""
    k = it.get("kind")
    st = str(it.get("state") or "")
    if k == "disk":
        try:
            free = float(st.split("free ")[1].split(" GB")[0])
            total = float(st.split("total ")[1].split(" GB")[0])
            r = (free / total) if total else 0
            return "crit" if r < 0.05 else ("warn" if r < 0.10 else "ok")
        except Exception:
            return st
    if k == "port":
        return st.split(" · ")[0]
    if k == "seat":
        return st
    return "存在"


def _digest(it):
    proj = {"id": it.get("id"), "kind": it.get("kind"), "src": it.get("src"),
            "approved": it.get("approved"), "scope": it.get("scope"), "cls": _cls(it),
            "sha16": it.get("sha16")}
    return _sha16(json.dumps(proj, ensure_ascii=False, sort_keys=True).encode("utf-8"))


def _col_digest(items):
    return _sha16("|".join("%s=%s" % (i.get("id"), _digest(i)) for i in items).encode("utf-8"))


def _agents_integrity(agents):
    u'''`agents` 栏之完整性（T2-刀16 §一）：`席位 ∪ 端点` 两集**皆须入栏**。

    ⛔ 少报 ⇒ 面即谎（承「假数比无面更坏」）⇒ 本函给出**缺**之逐项 ＋ 面／滤／式／数。
    '''
    cards, cerr = _roster_endpoints()
    ids_all = [str(c.get('id')) for c in cards]
    in_col = {str(x.get('id')) for x in agents if x.get('kind') != 'seat'}
    seats_n = len([x for x in agents if x.get('kind') == 'seat'])
    missing = [i for i in ids_all if i not in in_col]
    extra = sorted(in_col - set(ids_all))
    return {
        u'面之径逐字': str(Path(__file__).resolve()),
        u'判据': u'agents 栏 ⊆ 席位 ∪ roster 卡，且 roster 卡**逐枚**在栏',
        u'滤': u'无（⛔ 机扫筛 · T2-刀16 §一）',
        u'式': u'list(席位) ＋ list(roster.cards)',
        u'数': {'席位': seats_n, u'roster_卡': len(ids_all),
               u'端点入栏': len(in_col), u'应入': len(ids_all)},
        u'缺': missing, u'栏内多出（roster 无）': extra,
        u'读卡之错': (cerr or None),
        u'ok': (not missing) and (not cerr),
    }


def build_env(route_count=None):
    """四栏之面（**只读**）。每栏独立兜底 ⇒ 一栏坏 ⛔ 拖倒全盘（并**明报** errors）。"""
    cols = {"agents": [], "kb": [], "tools": [], "resources": []}
    errors, notes, dig = {}, {}, {}
    fns = {"agents": agents_col, "kb": kb_col,
           "tools": lambda: tools_col(route_count=route_count), "resources": resources_col}
    for name in cols:
        try:
            items, note, _tag = fns[name]()
            cols[name] = items
            if note:
                notes[name] = note
        except Exception as e:
            cols[name] = []
            errors[name] = "%s: %s" % (type(e).__name__, str(e)[:200])
        dig[name] = _col_digest(cols[name])
    vault = str(_vault())
    _pm, _ps = resolve_paths()
    _ws, _ws_src = resolve_ws_root(_pm)
    out = {
        "ok": True,
        "at": _now(),
        "env_version": ENV_VERSION,
        # ⭐⭐ 径之**一处出径**（承 pm_1366 §三 ⓐ）：`ws_root` 单值（绝对）＋ `paths` 逐键。
        #    ⛔ 前端自拼（`web\pa\faces\products.js:240` 之活硬编 即此病）｜⛔ `None` 键 ⇒ 顾主须显「未接」
        #    （⛔ 静默 · ⛔ 以空串 ／ 盘符兜底）。
        "ws_root": _ws,
        "ws_root_src": _ws_src,
        "paths": _pm,
        "paths_src": _ps,
        "cols": cols,
        "counts": {k: len(cols[k]) for k in cols},
        # ⭐ T2-刀8 §一：`agents` 栏**一栏两义**（席位 ⟷ 端点）⇒ 附**分列之数**（⛔ 抹平）
        "agents_breakdown": {
            "组织席位册": len([x for x in cols.get("agents", []) if x.get("kind") == "seat"]),
            "能力端点册": len([x for x in cols.get("agents", []) if x.get("kind") != "seat"]),
        },
        # ⭐ T2-刀16 §一：**完整性之闸** —— 端点卡一枚不入 ⇒ 明报（⛔ 静默少报）
        "agents_完整性": _agents_integrity(cols.get("agents", [])),
        "sources": {
            "agents": "%s ＋ %s（其果落 %s）" % (SRC_PASEO, SRC_SCAN, SRC_ROSTER),
            "kb": "%s（vault_root() 逐库）" % vault,
            "tools": "%s ＋ %s ＋ %s" % (SRC_TOOLS, vault, SRC_ROUTES),
            "resources": "%s ／ %s · SERVICES ／ env:CLAWSJOY_NUM_CTX ／ nvidia-smi -L ／ disk_usage"
                         % (SRC_PROVIDERS, SRC_SCAN),
        },
        "sha16": dig,
        "allowlist": allowlist(),
        "scope_legend": "本机 ＝ 本机原生直读；跨机 ＝ WSL 侧（须显式通道）",
    }
    if notes:
        out["notes"] = notes
    if errors:
        out["errors"] = errors
    blob = json.dumps(out, ensure_ascii=False)
    guard = {"pattern": KEY_PATTERN_DESC, "hits": blob.count(KEY_PATTERN_RAW),
             "note": "0 ⇒ 面无密钥之形；>0 ⇒ 须查（第一红线）"}
    # 自证：guard 自身不得载实形（否则面之输出必得≥**判据 3 破**）
    guard["self_hit"] = json.dumps(guard, ensure_ascii=False).count(KEY_PATTERN_RAW)
    out["secret_guard"] = guard
    return out


# ============================== 笔记 ＋ 侦察 ==============================
def _items_map(env):
    return {c: {i.get("id"): _digest(i) for i in (env["cols"].get(c) or [])} for c in env["cols"]}


def _latest_note():
    if not NOTE_DIR.is_dir():
        return None, None
    fs = sorted(NOTE_DIR.glob("note_*.json"))
    if not fs:
        return None, None
    f = fs[-1]
    try:
        return f, json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return f, None


def _diff(prev_items, now_items):
    changed = []
    for col in ("agents", "kb", "tools", "resources"):
        p = (prev_items or {}).get(col) or {}
        n = now_items.get(col) or {}
        for iid in sorted(set(p) | set(n)):
            was, now = p.get(iid, "缺"), n.get(iid, "缺")
            if was != now:
                changed.append({"col": col, "id": iid, "was": was, "now": now,
                                "kind": ("新增" if was == "缺" and now != "缺" else
                                         ("消失" if now == "缺" and was != "缺" else "变"))})
    return changed


def notes_face(limit=20, full=False):
    """`GET /v9/pa/env/note` —— PA 自己的**工作笔记**（只读 · 侦察之产物 ＋ 实测刻）。"""
    NOTE_DIR.mkdir(parents=True, exist_ok=True)
    fs = sorted(NOTE_DIR.glob("note_*.json"), reverse=True)[:max(int(limit or 20), 1)]
    idx = []
    for f in fs:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            d = {}
        md = f.with_suffix(".md")
        idx.append({"path": str(f), "md_path": (str(md) if md.is_file() else None),
                    "at": d.get("at"), "trigger": d.get("trigger"),
                    "sha16": _sha16(f.read_bytes()),
                    "counts": d.get("counts"), "changed_n": len(d.get("changed") or []),
                    "readonly_only": bool(d.get("readonly_only"))})
    out = {"ok": True, "at": _now(), "note_dir": str(NOTE_DIR), "count": len(idx), "notes": idx,
           "note_dir_exists": NOTE_DIR.is_dir()}
    if full and idx:
        try:
            out["latest"] = json.loads(Path(idx[0]["path"]).read_text(encoding="utf-8"))
            if idx[0].get("md_path"):
                out["latest_md"] = Path(idx[0]["md_path"]).read_text(encoding="utf-8")
        except Exception as e:
            out["latest_error"] = "%s: %s" % (type(e).__name__, str(e)[:200])
    return out


def _gpu_used_mib():
    """显卡之**已用兆 ＋ 利用率**（唯读 · ⛔ 占卡）；取不到 ⇒ `(None, None)`（照实）。"""
    try:
        r = _proc.run_hidden(["nvidia-smi", "--query-gpu=memory.used,utilization.gpu",
                            "--format=csv,noheader,nounits"],
                           capture_output=True, timeout=10, stdin=subprocess.DEVNULL)
        ln = (r.stdout or b"").decode("utf-8", "replace").strip().splitlines()[0]
        a = [x.strip() for x in ln.split(",")]
        return int(a[0]), (int(a[1]) if len(a) > 1 and a[1].isdigit() else None)
    except Exception:
        return None, None


def _mutex_markers():
    """**协作式**标记件：他器（出图 ／ 夜间整合…）置 `mutex/*.json` ＝「我占着」。
    形 `{who, until, why}`；`until` 已过 ⇒ ⛔ 计忙；不可读之件 ⇒ **照实**计入忙（⛔ 静默放行）。"""
    out = []
    if not MUTEX_DIR.is_dir():
        return out
    now = time.time()
    for f in sorted(MUTEX_DIR.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            out.append({"marker": str(f), "who": None, "why": "标记件不可读（照实计入忙）"})
            continue
        until, exp = d.get("until"), False
        try:
            if isinstance(until, (int, float)):
                exp = float(until) < now
            elif until:
                exp = time.mktime(time.strptime(str(until)[:19], "%Y-%m-%d %H:%M:%S")) < now
        except Exception:
            exp = False
        if not exp:
            out.append({"marker": str(f), "who": d.get("who"), "why": d.get("why"), "until": until})
    return out


def busy_state():
    """**互斥判**（T2-刀17）⇒ `{busy, reasons[], gpu_used_mib, gpu_util, markers}`（唯读）。"""
    used, util = _gpu_used_mib()
    mk = _mutex_markers()
    reasons = []
    gpu_busy = (used is not None and util is not None
                and used >= MUTEX_GPU_MIB and util >= MUTEX_GPU_UTIL_PCT)
    if gpu_busy:
        reasons.append("显卡**在算**：占用 %s MiB ≥ 阈 %s MiB ∧ util %s%% ≥ 阈 %s%%（合取 · 真在算）"
                       % (used, MUTEX_GPU_MIB, util, MUTEX_GPU_UTIL_PCT))
    for m in mk:
        reasons.append("协作标记：%s（who=%s · why=%s）" % (m.get("marker"), m.get("who"), m.get("why")))
    gpu = {"used_mib": used, "util_pct": util,
           "阈_MiB": MUTEX_GPU_MIB, "阈_util_pct": MUTEX_GPU_UTIL_PCT,
           "判": ("忙" if gpu_busy else ("闲" if used is not None else "缺")),
           "式": "used ≥ 阈_MiB ∧ util ≥ 阈_util_pct（**合取** · PM 刀21 §一）"}
    return {"busy": bool(reasons), "reasons": reasons, "gpu": gpu,
            "gpu_used_mib": used, "gpu_util": util,
            "markers": mk, "阈_MiB": MUTEX_GPU_MIB, "阈_util_pct": MUTEX_GPU_UTIL_PCT,
            "标记件箱": str(MUTEX_DIR),
            "判据": "① `nvidia-smi` `memory.used` ≥ 阈_MiB **∧** `utilization.gpu` ≥ 阈_util_pct（**合取** · 刀21 §一）② `mutex\\*.json` 之未过期标记 ⇒ 任一 ⇒ 忙（本拍跳过）"}


def _sched_log(rec):
    """每拍**一行**落 `scheduler_log.jsonl`（追加 · 可轮转）；写不成 ⇒ **静默不吞**（记 `_SCHED_STATE`）。"""
    try:
        SCHED_LOG.parent.mkdir(parents=True, exist_ok=True)
        try:
            if SCHED_LOG.is_file() and SCHED_LOG.stat().st_size > SCHED_LOG_MAX:
                SCHED_LOG.replace(SCHED_LOG.with_name(SCHED_LOG.name + ".1"))
        except Exception:
            pass
        with SCHED_LOG.open("a", encoding="utf-8", newline="") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return True
    except Exception as e:
        _SCHED_STATE["last_error"] = "log: %s: %s" % (type(e).__name__, str(e)[:160])
        return False


def sched_log_tail(n=10):
    """台账之**尾**（只读）：`{log_path, log_exists, log_lines, tail[]}`（⛔ 不吞坏行）。"""
    out = {"log_path": str(SCHED_LOG), "log_exists": SCHED_LOG.is_file(), "log_lines": None,
           "log_max_B": SCHED_LOG_MAX, "tail": []}
    try:
        if out["log_exists"]:
            lines = SCHED_LOG.read_text(encoding="utf-8").splitlines()
            out["log_lines"] = len(lines)
            for ln in lines[-max(int(n or 10), 1):]:
                try:
                    out["tail"].append(json.loads(ln))
                except Exception:
                    out["tail"].append({"坏行": ln[:120]})
    except Exception as e:
        out["error"] = "%s: %s" % (type(e).__name__, str(e)[:160])
    return out


def _sched_tick():
    """定时之拍：**每拍先过互斥** ⇒ 忙则跳过（记 `deferred`），闲则跑一次只读侦察。"""
    global _SCHED_STARTED
    try:
        every = int(os.getenv(SCHED_KEY, "0") or 0)
    except Exception:
        every = 0
    if every <= 0:
        return
    every = max(every, SCHED_RECOMMEND["下限_s"])
    _SCHED_STATE["started_at"] = _now()
    while True:
        time.sleep(every)
        st = busy_state()
        if st.get("busy"):
            _SCHED_STATE["deferred_n"] += 1
            _SCHED_STATE["last_defer_at"] = _now()
            _SCHED_STATE["last_defer_why"] = st.get("reasons")
            _sched_log({"at": _SCHED_STATE["last_defer_at"], "trigger": "定时",
                        "same": None, "elapsed_s": None,
                        "ticks": _SCHED_STATE["ticks"], "deferred_n": _SCHED_STATE["deferred_n"],
                        "errors_n": _SCHED_STATE["errors_n"],
                        "gpu": st.get("gpu"),
                        "busy_reason": st.get("reasons")})
            continue
        try:
            r = research(trigger="定时")
            _SCHED_STATE["ticks"] += 1
            _SCHED_STATE["last_tick_at"] = r.get("at")
            _SCHED_STATE["last_note"] = r.get("note_path")
            _SCHED_STATE["last_same"] = (r.get("before_after") or {}).get("same")
            _SCHED_STATE["last_elapsed_s"] = r.get("elapsed_s")
            _sched_log({"at": r.get("at"), "trigger": "定时",
                        "same": (r.get("before_after") or {}).get("same"),
                        "elapsed_s": r.get("elapsed_s"),
                        "ticks": _SCHED_STATE["ticks"], "deferred_n": _SCHED_STATE["deferred_n"],
                        "errors_n": _SCHED_STATE["errors_n"]})
        except Exception as e:
            _SCHED_STATE["errors_n"] += 1
            _SCHED_STATE["last_error"] = "%s: %s" % (type(e).__name__, str(e)[:200])
            _sched_log({"at": _now(), "trigger": "定时", "same": None, "elapsed_s": None,
                        "ticks": _SCHED_STATE["ticks"], "deferred_n": _SCHED_STATE["deferred_n"],
                        "errors_n": _SCHED_STATE["errors_n"],
                        "busy_reason": ["error: %s" % _SCHED_STATE["last_error"]]})


def ensure_scheduler():
    """定时／无人问自跑（Dots §2）。**默认关**（⛔ 静默默认开）⇒ 唯**显式**置 env 方启。"""
    global _SCHED_STARTED
    try:
        raw = int(os.getenv(SCHED_KEY, "0") or 0)
    except Exception:
        raw = 0
    base = {"建议": SCHED_RECOMMEND,
            "互斥": {"阈_MiB": MUTEX_GPU_MIB, "阈_util_pct": MUTEX_GPU_UTIL_PCT,
                    "式": "used ≥ 阈_MiB ∧ util ≥ 阈_util_pct（**合取** · 刀21 §一）",
                    "标记件箱": str(MUTEX_DIR),
                    "判据": "每拍先过 `busy_state()`；忙 ⇒ 跳过本拍（记 `deferred` · ⛔ 排队堆积）"},
            "成本": {"口径": "逐拍唯只读（⛔ 调模型 · ⛔ 用显卡）⇒ `$/拍 ≈ 0`；唯记 wall ／ CPU",
                    "近拍_elapsed_s": _SCHED_STATE.get("last_elapsed_s")},
            "态": dict(_SCHED_STATE),
            "态之性": "唯内存（起服即归零）⇒ 持久之账见 `log_tail`（`scheduler_log.jsonl`）",
            "log_tail": sched_log_tail(10)}
    if raw <= 0:
        base.update({"enabled": False, "every_s": 0, "env": raw,
                     "note": "未启（env `%s`=0 ／ 未置）⇒ 唯按 `POST /v9/pa/env/research` 触发（⛔ 静默默认开）" % SCHED_KEY})
        return base
    every = max(raw, SCHED_RECOMMEND["下限_s"])
    with _SCHED_LOCK:
        if not _SCHED_STARTED:
            t = threading.Thread(target=_sched_tick, name="pa_env_research", daemon=True)
            t.start()
            _SCHED_STARTED = True
    base.update({"enabled": True, "every_s": every, "env": raw, "started": _SCHED_STARTED,
                 "抬下限": (every != raw),
                 "note": "定时已启（`%s`=%s s）· 每拍先过互斥 ⇒ 忙则跳过" % (SCHED_KEY, every)})
    return base


def research(route_count=None, trigger="手动"):
    """`POST /v9/pa/env/research` —— **一次只读侦察** ⇒ 产工作笔记。

    ⛔ 无写副作用（唯写**自己**的笔记）；据 **前后对表** 自证：
    侦察前 ／ 后之四栏印须**逐字同**（⛔ 自报「我只读」）。
    """
    t0 = time.time()
    before = build_env(route_count=route_count)      # 侦察前
    prev_f, prev = _latest_note()
    now_items = _items_map(before)
    # 前笔之 items 已是 {col: {id: digest}} 之形 ⇒ **直取**（⛔ 再喂 `_items_map`：它收的是 env 之 doc）
    prev_items = (prev.get("items") if isinstance(prev, dict) else None) or None
    has_prev = bool(prev_items)
    # ⭐ 首笔 ⇒ **无前笔可比** ⇒ `changed=[]`（⛔ 以「全新增」充「变化」）
    changed = _diff(prev_items, now_items) if has_prev else []
    after = build_env(route_count=route_count)       # 侦察后
    same = (before.get("sha16") == after.get("sha16"))
    NOTE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    jf = NOTE_DIR / ("note_%s.json" % stamp)
    mf = NOTE_DIR / ("note_%s.md" % stamp)
    doc = {"at": _now(), "env_version": ENV_VERSION, "trigger": trigger,
           "counts": before.get("counts"),
           "cols_sha16": before.get("sha16"), "items": now_items, "changed": changed,
           "readonly_only": True, "readonly_tools": list(READONLY_TOOLS),
           "first_note": (not has_prev),
           "prev_note": (str(prev_f) if prev_f else None),
           "before_after": {"cols_sha16_before": before.get("sha16"),
                            "cols_sha16_after": after.get("sha16"), "same": same},
           "secret_guard": before.get("secret_guard"),
           "elapsed_s": round(time.time() - t0, 3)}
    jf.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    mf.write_text(_render_md(doc), encoding="utf-8")
    reads = sum(1 for d in ("agents", "kb", "tools", "resources")
                for i in ((before.get("cols") or {}).get(d) or []) if (i or {}).get("approved"))
    resp = {"ok": True, "at": doc["at"], "trigger": trigger,
            "readonly_tools": list(READONLY_TOOLS),
            "changed": changed, "changed_n": len(changed),
            "first_note": (not has_prev),
            "note_path": str(jf), "note_md": str(mf),
            "印": _sha16(jf.read_bytes()),
            "before_after": doc["before_after"],
            "counts": before.get("counts"), "cols_sha16": before.get("sha16"),
            "approved_items": reads,
            "secret_guard": before.get("secret_guard"),
            "elapsed_s": doc["elapsed_s"],
            "acted": False,
            "next": "据笔记行动 ⇒ 仍须**授权 ＋ 检查**（(乙) 人点 · ⛔ 不可逆动作全自动）"}
    return resp


def _render_md(doc):
    L = []
    L.append("# PA 环境侦察笔记（只读）")
    L.append("")
    L.append("- 刻：%s" % doc.get("at"))
    L.append("- 面版：%s" % doc.get("env_version"))
    L.append("- 触发：%s" % (doc.get("trigger") or "未标（旧笔）"))
    L.append("- 唯只读工具：%s" % " ／ ".join(doc.get("readonly_tools") or []))
    L.append("- 前后对表：%s（侦察前 ／ 后之四栏印**逐字同** ⇒ 无写副作用）"
             % ("同" if (doc.get("before_after") or {}).get("same") else "⛔ 异（须查）"))
    L.append("- 四栏之印：%s" % json.dumps(doc.get("cols_sha16") or {}, ensure_ascii=False))
    L.append("- 计数：%s" % json.dumps(doc.get("counts") or {}, ensure_ascii=False))
    L.append("- 密钥末闸：%s" % json.dumps(doc.get("secret_guard") or {}, ensure_ascii=False))
    L.append("- 上一笔：%s" % (doc.get("prev_note") or "无（首笔）"))
    L.append("- 本笔：%s" % ("首笔（无前笔可比 ⇒ 变化栏空）"
             if doc.get("first_note") else "有前笔 ⇒ 变化见下"))
    L.append("")
    L.append("## 变化（vs 上一笔）")
    ch = doc.get("changed") or []
    if not ch:
        L.append("- 无")
    for c in ch[:200]:
        L.append("- %s ／ %s：%s ⇒ %s（%s）" % (c.get("col"), c.get("id"), c.get("was"),
                                             c.get("now"), c.get("kind")))
    L.append("")
    L.append("## 分寸")
    L.append("- 本笔**唯报**；据之行动须**授权 ＋ 检查**（⛔ 不可逆动作全自动）。")
    return "\n".join(L) + "\n"