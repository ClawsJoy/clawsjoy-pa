# -*- coding: utf-8 -*-
u"""界面态快照 —— **服务自落**（pm_1558 §二 裁 ⒜）。

面
----
  唯一写者 ＝ 服务（网关）：启动时落一次 ``<root>/web/pa/ui_state.json``（九键 · 与前端只读契约同形）。
  前端（``web/pa/more.js`` ／ ``status.js``）只读该件显示 ⇒ ⛔ 前端自算 · ⛔ 界面直读 ``nvidia-smi``。
  内容工坊之器 ``08_工具/模型_双模.py --落`` ＝ **开发机之旁证**（⛔ 净机之凭 · 承守四）。

守（pm_1558 §二 · 四守）
--------------------------
  守一 一处定形：唯一写者 ＝ 服务 ⇒ ⛔ 双源。（本地 ／ 远端之 base 与 key 名唯自 PA 注册表 ``core.pa.providers``）
  守二 落件之守：写失败（装根只读 ／ UAC 保护区）⇒ **fail-loud 显形**（⛔ 静默 · ⛔ 崩）
                  ∧ 页面照旧显「未载入」（已知貌）。
  守三 义 ⛔ 变：九键之义 ⛔ 变 ∧ 「刻」＝ **真采样刻**（⛔ 冒充实时）。
  守四 器仍作开发机之旁证（⛔ 删 · 唯明书其分）。

齿（``tests/unit/test_ui_state_snapshot_1558.py``）
  正控 新树（⛔ 件）⇒ 落 ⇒ 件在 ∧ 九键 ∧ ⛔BOM ∧ CR 0 ∧ LF 1（≡ 活端 ``200``）。
  反控 ⛔ 落（旧形）⇒ 件 ⛔ 在（≡ 活端 ``404`` ／ 「未载入」）。
  写失败之守 不可写之径 ⇒ 返 False ∧ **显形行在** ∧ ⛔ 崩。
"""
import io
import json
import os
import re
import subprocess
import threading
import time
import urllib.error
import urllib.request

PROBE_TIMEOUT = 3.0                      # 单探之上限（秒）· ⛔ 长阻启动
SNAPSHOT_REL = os.path.join("web", "pa", "ui_state.json")
SNAPSHOT_PATH_ENV = "CJ_UI_STATE"        # 与内容工坊之器同源（一处可改）
FOREVER_YEAR = 2100

# core/gateway/ui_state.py ⇒ 剥三层到仓库根
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def now_str():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def http_get(url, headers=None, timeout=PROBE_TIMEOUT):
    u"""(status, text)。⛔ 抛：一切异常收成 (-1, "err: ...")。"""
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return (r.status, r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return (e.code, "err: HTTP %s" % e.code)
    except Exception as e:
        return (-1, "err: %s" % type(e).__name__)


def host_of(url):
    m = re.match(r"^[a-zA-Z]+://([^/]+)", url or u"")
    return m.group(1) if m else (url or u"—")


def forever_names(ps_text):
    u"""`/api/ps` 之 JSON ⇒ [模型名]（`expires_at` 之年 ≥ 2100 ⇒ 判 Forever）。纯函数。"""
    try:
        d = json.loads(ps_text)
    except Exception:
        return []
    out = []
    for m in d.get("models", []) or []:
        ex = str(m.get("expires_at") or u"")
        yr = re.match(r"^(\d{4})-", ex)
        if yr and int(yr.group(1)) >= FOREVER_YEAR:
            out.append(str(m.get("name") or m.get("model") or u"?"))
    return out


def count_models(text):
    u"""`/api/tags` ／ `/api/ps` 之 JSON ⇒ 模型数。纯函数（⛔ 解 ⇒ -1）。"""
    try:
        return len(json.loads(text).get("models", []) or [])
    except Exception:
        return -1


def count_remote_models(text):
    u"""OpenAI 兼容 `GET /v1/models` 之 JSON ⇒ 模型数。纯函数。"""
    try:
        d = json.loads(text)
    except Exception:
        return -1
    return len(d["data"]) if isinstance(d.get("data"), list) else -1


def gpu():
    u"""(total, free) MiB ∨ None —— 口径照 `GPU_让位.py`（nounits ⇒ 纯数字）。"""
    exe = None
    for c in (r"C:\Windows\System32\nvidia-smi.exe", "nvidia-smi"):
        if c.endswith(".exe"):
            if os.path.isfile(c):
                exe = c
                break
        else:
            import shutil
            if shutil.which(c):
                exe = c
                break
    if not exe:
        return None
    try:
        out = subprocess.check_output([exe, "--query-gpu=memory.total,memory.free",
                                       "--format=csv,noheader,nounits"],
                                      stderr=subprocess.STDOUT).decode("utf-8", "replace")
    except Exception:
        return None
    m = re.findall(r"\d+", out)
    return (int(m[0]), int(m[1])) if len(m) >= 2 else None


# ===== 配置之源（守一：一处定形 · 唯自 PA 注册表 core.pa.providers）=====
def _reg(pid):
    try:
        from core.pa.providers import PROVIDERS
        return PROVIDERS.get(pid) or {}
    except Exception:
        return {}


def local_base():
    u"""本地（Ollama）base —— env `OLLAMA_HOST` ／ `OLLAMA_BASE_URL` ⇒ 注册表 `local:ollama.base_url`。"""
    for k in ("OLLAMA_HOST", "OLLAMA_BASE_URL"):
        v = (os.environ.get(k) or "").strip()
        if v:
            return v.rstrip("/")
    return str(_reg("local:ollama").get("base_url") or "http://127.0.0.1:11434").rstrip("/")


def remote_base():
    u"""远端 base —— env `OPENAI_BASE_URL` ⇒ 注册表 `base_url_env`（DEEPSEEK_ENDPOINT）⇒ 注册表 `base_url`。"""
    r = _reg("remote:deepseek")
    for k in ("OPENAI_BASE_URL", r.get("base_url_env") or "DEEPSEEK_ENDPOINT"):
        if not k:
            continue
        v = (os.environ.get(k) or "").strip()
        if v:
            return v.rstrip("/")
    return str(r.get("base_url") or "").rstrip("/")


def _remote_key_value():
    u"""远端凭据之**值**（唯供请求头 · ⛔ 外露 · ⛔ 入快照 · ⛔ 入日志 · 承 L21）。"""
    r = _reg("remote:deepseek")
    for k in ("OPENAI_API_KEY", r.get("key_env") or "DEEPSEEK_API_KEY"):
        v = (os.environ.get(k) or "").strip() if k else u""
        if v:
            return v
    return u""


def remote_key_present():
    u"""远端凭据**只判在否**（⛔ 值 · ⛔ 长度 · ⛔ 哈希 · 承 L21）。"""
    return bool(_remote_key_value())


def remote_state(base, status):
    u"""三态：`未配` ／ `配了但不通` ／ `配了且通`。纯函数（⛔ 三态挤一个）。"""
    if not (base or u"").strip():
        return u"未配"
    return u"配了且通" if status == 200 else u"配了但不通"


def remote_reason(base, status, body):
    u"""`远端态` 之短因：`未配` ／ `HTTP nnn` ／ `连接失败` ／ `通`。"""
    if not (base or u"").strip():
        return u"未配（⛔ 见 env DEEPSEEK_ENDPOINT）"
    if status == 200:
        return u"通（GET /v1/models = 200）"
    if status is None:
        return u"未探"
    if status < 0:
        return u"连接失败 ／ " + (body or u"")[:60]
    return u"HTTP %d ／ 端点活（凭据 ∨ 路径之故）" % status


def collect():
    u"""采**九键**（守三：义 ⛔ 变 · 「刻」＝ 真采样刻）。"""
    lb = local_base()
    rb = remote_base()
    ver = http_get(lb + u"/api/version")
    tags = http_get(lb + u"/api/tags")
    ps = http_get(lb + u"/api/ps")
    g = gpu()
    rem = (None, u"")
    if rb:
        # 与内容工坊之器同形：带 Bearer 头（⛔ 带 ⇒ 401 ⇒ 「配了但不通」，二者必同）
        _k = _remote_key_value()
        _h = {u"Authorization": u"Bearer " + _k} if _k else {}
        rem = http_get(rb + u"/v1/models", _h)
    return {
        u"已载": count_models(ps[1]),
        u"显存": {u"free": (g[1] if g else -1), u"total": (g[0] if g else -1)},
        u"Forever": forever_names(ps[1]),
        u"本地在": ver[0] == 200,
        u"远端在": rem[0] == 200,
        u"远端host": host_of(rb),
        u"远端态": remote_state(rb, rem[0]),
        u"远端因": remote_reason(rb, rem[0], rem[1]),
        u"刻": now_str(),
    }


#: 「快照九键」之规格（键 ⇒ 类型判）—— ⭐ 唯此一处（承「同形门」· ⛔ 各写一份）。
SNAPSHOT_SPEC = (
    (u"已载",     lambda v: isinstance(v, int) and (not isinstance(v, bool))),
    (u"显存",     lambda v: isinstance(v, dict)
                            and isinstance(v.get(u"free"), int) and (not isinstance(v.get(u"free"), bool))
                            and isinstance(v.get(u"total"), int) and (not isinstance(v.get(u"total"), bool))),
    (u"Forever",  lambda v: isinstance(v, list)),
    (u"本地在",   lambda v: isinstance(v, bool)),
    (u"远端在",   lambda v: isinstance(v, bool)),
    (u"远端host", lambda v: isinstance(v, str)),
    (u"远端态",   lambda v: v in (u"未配", u"配了但不通", u"配了且通")),
    (u"远端因",   lambda v: isinstance(v, str)),
    (u"刻",       lambda v: isinstance(v, str)),
)


def check_snapshot(d):
    u"""键齐守护 ⇒ (ok, 缺／错清单)（逐字段点名）。"""
    if not isinstance(d, dict):
        return (False, [u"<整>：⛔ 是对象"])
    bad = []
    for k, fn in SNAPSHOT_SPEC:
        if k not in d:
            bad.append(u"%s：缺" % k)
            continue
        try:
            if not fn(d[k]):
                bad.append(u"%s：型错" % k)
        except Exception:
            bad.append(u"%s：型错" % k)
    return (len(bad) == 0, bad)


def snapshot_path():
    u"""落点（守一：唯一写者 ＝ 服务）＝ env `CJ_UI_STATE` ∨ `<root>/web/pa/ui_state.json`。"""
    v = (os.environ.get(SNAPSHOT_PATH_ENV) or "").strip()
    return v if v else os.path.join(_REPO_ROOT, SNAPSHOT_REL)


def write_snapshot(path, data):
    u"""把九键**只读写出**（⛔BOM · CR 0 · 末单 LF）⇒ 返 bytes；**坏快照 ⇒ 抛**（守二：fail-loud）。

    ⚠ 以 bytes 落盘 ⇒ ⛔ 受平台换行转换（保 CR 0）。
    """
    ok, bad = check_snapshot(data)
    if not ok:
        raise ValueError(u"坏快照（⛔ 落）：%s" % u" ／ ".join(bad))
    raw = (json.dumps(data, ensure_ascii=False).rstrip(u"\n") + u"\n").encode("utf-8")
    parent = os.path.dirname(os.path.abspath(path))
    if parent and (not os.path.isdir(parent)):
        os.makedirs(parent)
    with io.open(path, "wb") as fh:
        fh.write(raw)
    return raw


def write_once(path=None):
    u"""落一次 ⇒ True；失败 ⇒ False ＋ **显形行**（守二：⛔ 静默 · ⛔ 崩）。"""
    p = path or snapshot_path()
    try:
        raw = write_snapshot(p, collect())
    except Exception as e:
        print(u"[UI_STATE] ⛔ 界面态快照 ⛔ 落（%s: %s）—— 界面将显「未载入」（已知貌）｜ 径=%s"
              % (type(e).__name__, e, p))
        return False
    try:
        stamp = json.loads(raw.decode(u"utf-8")).get(u"刻", u"?")
    except Exception:
        stamp = u"?"
    print(u"[UI_STATE] 界面态快照已落（服务自落 · pm_1558 §二 裁 ⒜）：%s ｜ %d B ｜ 刻=%s"
          % (p, len(raw), stamp))
    return True


def write_once_bounded(timeout=6.0, path=None):
    u"""有界等待之落（⛔ 长阻启动）：超时 ⇒ 报一行，后台续跑。返 True ／ False。"""
    box = {}

    def _go():
        box["ok"] = write_once(path)

    t = threading.Thread(target=_go, daemon=True, name="ui-state-snapshot")
    t.start()
    t.join(timeout)
    if t.is_alive():
        print(u"[UI_STATE] ⚠ 快照之落 ⛔ 及于 %ss（后台续跑 · 首屏暂显「未载入」）" % timeout)
        return False
    return bool(box.get("ok"))