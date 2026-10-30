# -*- coding: utf-8 -*-
r"""pa_paths.py -- PA **可写根**之「一处定形」（承 9.0.13 P0 · PM 69 号件）。

病（一手 · 2026-10-28）：
  9.0.12 装 Program Files 后，`pa_nowindow.py` 把 PID ／ stopped ／ life ／ task ／ console
  全指 `ROOT\logs`（装根）⇒ 普通用户 **WinError 5** ⇒ preflight 4/8 FAIL ⇒ 壳起不来。
  根因 ＝ **运行态落在装根**（装根只读），⛔ 权限设置之过。

本器（**一处出径** · 三根）：
  · `PA_DATA_DIR` ⇒ 应用数据根（**亦注入 core 之 `CLAWSJOY_DATA_DIR`**）
  · `PA_LOG_DIR`  ⇒ 运行态根（pid ／ stopped ／ life ／ task ／ console ／ gateway.log）
  · `PA_VEC_DIR`  ⇒ 向量库根（chroma 直接落此目录；core `get_vector_root()` 认之）
  缺省皆 `%LOCALAPPDATA%\ClawsJoyPA\{data,logs,vec}`（无 LOCALAPPDATA ⇒ USERPROFILE ／ ~ 之
  `.local/share/ClawsJoyPA` 兜底 · ⛔ 回落装根 —— 装根只读）。

纪律：
  1. 凡运行态之径 ⇒ **唯自本器出**（⛔ 各器各写一份 ⇒ 二源必漂）。
  2. 子进程 env ⇒ `child_env()` 统一注入三根 ＋ `CLAWSJOY_DATA_DIR` ＋ `PYTHONDONTWRITEBYTECODE=1`
     （装根只读 ⇒ **⛔ 写 `.pyc`** 之护栏亦在此）。
  3. 可写之判 ⇒ `probe_writable()`：试写 ＋ fsync ＋ 删；失败 ⇒ **人话之因 ＋ 该由哪个 env 迁**。
"""
from __future__ import annotations

import os
import sys

#: 三根之 env 名（**一处定形**）
ENV_DATA = u"PA_DATA_DIR"
ENV_LOG = u"PA_LOG_DIR"
ENV_VEC = u"PA_VEC_DIR"

#: 名 ⇒ (env 名, 缺省子径)
ROOTS = (
    (u"data", ENV_DATA, u"data"),
    (u"logs", ENV_LOG, u"logs"),
    (u"vec", ENV_VEC, u"vec"),
)
ENV_BY_NAME = {n: e for n, e, _s in ROOTS}
SUBDIR_BY_NAME = {n: s for n, _e, s in ROOTS}

#: 我司之用户级目录（与 shell ／ core/pa/diagnostics.py 同族）
COMPANY_DIR = u"ClawsJoyPA"

#: core 之数据根 env（`core/lib/config_helper.py:DATA_ROOT_ENV` 同源 —— 承「一处定形」）
DATA_ROOT_ENV = u"CLAWSJOY_DATA_DIR"

#: 子进程 ⛔ 写 `.pyc` 之 env（承 pm_1679 §五.1 · 载荷之根 ≡ 装根）
NO_PYC_ENV = u"PYTHONDONTWRITEBYTECODE"

#: 「相对装根」之运行态 env（⭐ 9.0.13 P0：装根只读 ⇒ 由 child_env 迁入 PA_DATA_DIR 之下）
FEEDBACK_DIR_ENV = u"PA_FEEDBACK_DIR"      # core/lib/feedback_target.py 之 ENV["dir"]
UI_STATE_ENV = u"CJ_UI_STATE"              # core/gateway/ui_state.py 之 snapshot_path()

#: 运行态文件名（**一处定形**）—— 皆落 `PA_LOG_DIR`
PID_NAME = u"win_pa.pid"
STOPPED_NAME = u"win_pa.stopped.json"
LIFE_NAME = u"win_pa_life.jsonl"
TASK_MARK_NAME = u"win_pa.task_dispatch.json"
GATEWAY_LOG_NAME = u"gateway.log"


def _env_of(env):
    return os.environ if env is None else env


def _clean(v):
    return (v or u"").strip()


def _expand(raw):
    u"""env 之值 ⇒ 绝对径（可含 `%LOCALAPPDATA%` ／ `~` 之形；相对径 ⇒ 按 CWD 归一）。"""
    p = os.path.expandvars(os.path.expanduser(raw))
    return os.path.abspath(p)


def default_base(env=None):
    r"""三根之父 ⇒ `%LOCALAPPDATA%\ClawsJoyPA`（⛔ 装根 —— 装根只读）。

    无 `LOCALAPPDATA` ⇒ `%USERPROFILE%\AppData\Local` ⇒ `~/.local/share` 兜底；
    三者皆无（极罕）⇒ 临时目录之 `ClawsJoyPA-local`（仍 ⛔ 落装根）。
    """
    e = _env_of(env)
    la = _clean(e.get(u"LOCALAPPDATA"))
    if not la:
        up = _clean(e.get(u"USERPROFILE"))
        if up:
            la = os.path.join(up, u"AppData", u"Local")
    if not la:
        home = _clean(os.path.expanduser(u"~"))
        la = os.path.join(home, u".local", u"share") if home and home != u"~" else u""
    if not la:
        import tempfile
        la = os.path.join(tempfile.gettempdir(), u"ClawsJoyPA-local")
    return os.path.join(la, COMPANY_DIR)


def resolve(name, env=None):
    u"""一根之实 ⇒ `{name, env, path, source, default}`（env 优先 · 否则缺省）。

    `source` 供人读（preflight 之因须点名「谁定的」）；⛔ 静默。
    """
    e = _env_of(env)
    if name not in ENV_BY_NAME:
        raise KeyError(u"未名之根：%r（唯 %s）" % (name, u"/".join(ENV_BY_NAME)))
    env_name = ENV_BY_NAME[name]
    raw = _clean(e.get(env_name))
    if raw:
        return {u"name": name, u"env": env_name, u"path": _expand(raw),
                u"source": u"env:%s=%s" % (env_name, raw), u"default": False}
    path = os.path.join(default_base(e), SUBDIR_BY_NAME[name])
    return {u"name": name, u"env": env_name, u"path": path,
            u"source": u"缺省 %s\\%%LOCALAPPDATA%%\\%s\\%s" % (env_name, COMPANY_DIR, SUBDIR_BY_NAME[name]),
            u"default": True}


def roots(env=None):
    u"""三根之实（名 ⇒ 上述 resolve 之果）。"""
    return {n: resolve(n, env) for n, _e, _s in ROOTS}


def path_of(name, env=None):
    return resolve(name, env)[u"path"]


def data_root(env=None):
    return path_of(u"data", env)


def log_root(env=None):
    return path_of(u"logs", env)


def vec_root(env=None):
    return path_of(u"vec", env)


def log_path(name, env=None):
    u"""运行态之件 ⇒ `PA_LOG_DIR/<name>`（一处定形）。"""
    return os.path.join(log_root(env), name)


def vector_kb(env=None):
    u"""向量库之实径（chroma 直接落此目录 —— `PA_VEC_DIR` 即库目录）。"""
    return vec_root(env)


def legacy_vector_kb(env=None):
    u"""旧形（`<data_root>/vector_kb`）—— 仅供诊断 ／ 迁移对照，⛔ 运行态写入。"""
    return os.path.join(data_root(env), u"vector_kb")


def install_root_of(script_file=None):
    u"""`<root>/scripts/win_pa/<this>.py` ⇒ 装根（与 pa_nowindow 同式）。"""
    p = script_file or __file__
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(p))))


def is_inside(path, root):
    u"""`path` 是否落 `root` 之内（按 realpath ／ normcase 归一 —— 含等）。"""
    try:
        c = os.path.normcase(os.path.realpath(path))
        r = os.path.normcase(os.path.realpath(root))
    except Exception:
        return False
    return c == r or c.startswith(r if r.endswith(os.sep) else r + os.sep)


def roots_inside_install(env=None, install_root=None):
    u"""落装根之内的运行根名表（装根只读 ⇒ 此处应为空）。"""
    root = install_root or install_root_of()
    return [n for n, info in roots(env).items() if is_inside(info[u"path"], root)]


def ensure_roots(env=None):
    u"""立三根之目录 ⇒ `(ok, rows)`；rows ＝ `[(名, 径, 成?, 人话之因)]`（⛔ 静默）。"""
    out = []
    ok_all = True
    for n, _e, _s in ROOTS:
        info = resolve(n, env)
        ok, why, _note = probe_writable(info[u"path"], env_name=info[u"env"], source=info[u"source"],
                                        create_file=False)
        out.append((n, info[u"path"], bool(ok), why))
        ok_all = ok_all and bool(ok)
    return ok_all, out


def explain_error(e):
    u"""异常 ⇒ 人话（权限之族点名 WinError 5 ／ 只读 ／ 不可建）。"""
    _wn = getattr(e, u"winerror", None)
    if isinstance(e, PermissionError) or _wn == 5:
        if _wn is not None:
            return u"权限不足（WinError %s：普通用户不可写 · 装根 ／ Program Files 之常形）" % _wn
        return u"权限不足（PermissionError：普通用户不可写）"
    if isinstance(e, FileNotFoundError):
        return u"父目录不可建或 ⛔ 在（FileNotFoundError）"
    if isinstance(e, NotADirectoryError):
        return u"径上之件非目录（NotADirectoryError）"
    if _wn is not None:
        return u"%s（WinError %s）" % (type(e).__name__, _wn)
    return u"%s: %s" % (type(e).__name__, e)


def probe_writable(d, env_name=u"", source=u"", create_file=True):
    u"""可写之判（试写 ＋ fsync ＋ 删）⇒ `(ok, reason, note)`。

    失败之因必含：**所在之径**（点名）＋ **谁定之**（env ／ 缺省）＋ **迁之门**（该设哪个 env）。
    `create_file=False` ⇒ 唯立目录（供 `ensure_roots` 之预立）。
    """
    try:
        os.makedirs(d, exist_ok=True)
    except Exception as e:
        return (False, u"不可写（%s）｜径＝%s｜源＝%s｜修之门：设 env %s 至用户可写处"
                % (explain_error(e), d, source or u"未记", env_name or u"（本根）"), u"")
    if not create_file:
        return (True, u"可写（目录已立：%s）" % d, d)
    p = os.path.join(d, u".pa_write_probe_%d_%d" % (os.getpid(), id(d) & 0xFFFF))
    try:
        with open(p, u"wb") as f:
            f.write(b"probe")
            f.flush()
            os.fsync(f.fileno())
        os.remove(p)
        return (True, u"可写（试写 ＋ fsync ＋ 删：%s）" % d, d)
    except Exception as e:
        try:
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            pass
        return (False, u"不可写（%s）｜径＝%s｜源＝%s｜修之门：设 env %s 至用户可写处"
                % (explain_error(e), d, source or u"未记", env_name or u"（本根）"), u"")


def child_env(base=None):
    u"""子进程之 env（**一处定形** · 承 pm_1679 §五.1）：

    ① 三根皆注入（缺省亦注入 ⇒ 孙进程 ⛔ 回落装根）；
    ② `CLAWSJOY_DATA_DIR` ＝ `PA_DATA_DIR`（core `get_data_root()` 之真口）；
    ③ `PYTHONDONTWRITEBYTECODE=1`（装根只读 ⇒ ⛔ 落 `.pyc`）。
    """
    e = dict(_env_of(base))
    r = roots(e)
    for n, _env_name, _s in ROOTS:
        e[ENV_BY_NAME[n]] = r[n][u"path"]
    e[DATA_ROOT_ENV] = r[u"data"][u"path"]
    #: ⭐ 9.0.13 P0：凡「相对装根」之运行态亦须迁出（装根只读 ⇒ 写必 WinError 5）：
    #:   · feedback 收件目录（core/lib/feedback_target.py:ENV["dir"]；缺省 data/pa/feedback）
    #:   · 界面态快照（core/gateway/ui_state.py: env CJ_UI_STATE ∨ <root>/web/pa/ui_state.json）
    e[FEEDBACK_DIR_ENV] = os.path.join(r[u"data"][u"path"], u"pa", u"feedback")
    e[UI_STATE_ENV] = os.path.join(r[u"data"][u"path"], u"ui_state.json")
    e[NO_PYC_ENV] = u"1"
    return e


def describe(env=None):
    u"""人读之三根（供 preflight ／ 日志首屏）⇒ 多行文本。"""
    rows = []
    for n, info in roots(env).items():
        rows.append(u"  %-4s %-12s = %s（%s）" % (n, info[u"env"], info[u"path"], info[u"source"]))
    return u"\n".join(rows)


def main(argv=None):
    u"""CLI（诊断用）：`pa_paths.py [--json]` ⇒ 印三根。"""
    import json as _json
    argv = list(sys.argv[1:] if argv is None else argv)
    if sys.stdout is not None:
        try:
            sys.stdout.reconfigure(encoding=u"utf-8", errors=u"replace")
        except Exception:
            pass
    if u"--json" in argv:
        print(_json.dumps({n: {"env": i[u"env"], "path": i[u"path"], "source": i[u"source"]}
                           for n, i in roots().items()}, ensure_ascii=False, indent=2))
        return 0
    print(u"[PA 可写根] 装根=%s" % install_root_of())
    print(describe())
    ok, rows = ensure_roots()
    print(u"[三根可写] %s" % (u"PASS" if ok else u"FAIL"))
    for n, p, o, w in rows:
        print(u"  %s %-4s %s ⇒ %s" % (u"[PASS]" if o else u"[FAIL]", n, p, w))
    return 0 if ok else 2


if __name__ == u"__main__":
    sys.exit(main())
