# -*- coding: utf-8 -*-
r"""preflight_start.py -- PA 网关「启动前自检」（P4 稿 · 2026-10-05 · 技术总监席）

来由（记事 · 病单 P4）：
  · 2026-10-05 晨：同一 start 命令在「非全权」下崩
    （`chromadb.errors.InternalError: ... attempt to write a readonly database`），
    全权下成 ⇒ ⭐ 「启动无自检」：依赖与权限未在启动期验 ⇒ 裸 traceback 后静默死。
  · 本器 ＝ 起之前先把「起不来的因」用**人话**说出来，⛔ 不在起之后猜。

落点（归平台线）：`scripts\win_pa\preflight_start.py`
用法：
  python -X utf8 scripts\win_pa\preflight_start.py            # 自检本机
  python -X utf8 scripts\win_pa\preflight_start.py --root <v9 根>
  python -X utf8 scripts\win_pa\preflight_start.py --self-test

退出码：0 = 全过（可起）｜2 = 有 FAIL（⛔ 不起）｜1 = 自检器自身错（人话报因）

判据（七项 · 逐项 `[PASS]`/`[FAIL]` ＋ 人话因）：
  1. `services.gateway.port`（真源 `core.lib.port_config`）**可读** —— 不可读 ⇒ **起服必拒**
     （`PortUnconfigured` 族 · 2026-10-05 事故：CWD ≠ ROOT ⇒ 配置解析不到 ⇒ 拒启；⛔ 仅验「端口可绑」）
  2. 端口（真源 `core.lib.port_config`）**可绑** —— 被占 ⇒ 报「已被占用/疑已有实例」
     ⚠ 本器**⛔ 用 `SO_REUSEADDR`**（Windows 下它允许**双绑** ⇒ 会**假 PASS** · 我一手逮）
     ⭐ T1.2（承 PM 073 §三）：判据**成对** —— 先 **TCP 实连** ∧ 再**两面皆试绑**（`0.0.0.0` ∧ `127.0.0.1`）；
       由：实例绑 `0.0.0.0` 时只绑 `127.0.0.1` **仍 OK** ⇒ 单面之绑**假绿**（我一手实证 · 本机 socket 语义）
  3. **可写三根**（⭐ 9.0.13 P0）：PA_DATA_DIR ／ PA_LOG_DIR ／ PA_VEC_DIR 皆可写
     （试写 ＋ fsync ＋ 删；缺省 %LOCALAPPDATA%\ClawsJoyPA\{data,logs,vec} · 装根只读 ⇒ ⛔ 落装根）；三根分栏报因并点名 env
  4. **向量库可写**（真源 `<data_root>/vector_kb` ⇒ ⛔ 字面猜径）｜两段：库目录可写 ⇒ 建得 journal/WAL；`PRAGMA user_version` 同值写 ⇒ 真触盘｜⭐ 「未见」⟷「不可写」**分栏**（且**点名真径**）
  5. `ollama` 服务 `127.0.0.1:11434`（TCP ＋ `/api/tags`）
  6. **装根隔离**（⭐ 9.0.13 P0）：运行根皆须在装根**外**（装 Program Files 只读 ⇒ 落装根内必 WinError 5）
  7. **依赖（必需）自检**（承 pm_1386 §二.3 · 2026-10-06）：`REQUIRED_DEPS` 逐包 `find_spec` ⇒ 在 ∨ 缺；
     缺 ⇒ **人话之因 ＋ 修之门**（`pip install -r requirements.txt`）· ⛔ 静默（⛔ 装成可用）。
     ⚠ 单列一栏（⛔ 并一栏）：缺依赖 ⟷ 端口占用 ⟷ 向量库不可写 ＝ **三族**｜真源 ＝ `requirements.txt`
     之「运行依赖（必需）」诸节 · 本表**派生**自 `scripts/dev/scan_client_deps.py`（⛔ 手拟）

独立跑亦自 `os.chdir(root)`（配置按 CWD 解析 —— 承 2026-10-05 事故；⛔ 唯 `--root` 探针之根）

接线点（⛔ 本席不改平台件）：`pa_nowindow.cmd_start` 在 spawn **之前**先跑本器
  ⇒ `rc != 0` ⇒ **⛔ spawn** ＋ 把人话因**透传**给调用者（⛔ 裸 traceback 后静默死）。
"""
import argparse
import json
import os
import socket
import sqlite3
import sys
import urllib.request

if sys.stdout is not None:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

#: ⭐ 9.0.13 P0：可写根之唯一出处（PA_DATA_DIR ／ PA_LOG_DIR ／ PA_VEC_DIR）
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import pa_paths  # noqa: E402

HOST = '127.0.0.1'
OLLAMA_PORT = 11434
# 向量库径 = **真源**（⛔ 字面猜径）：<data_root>/vector_kb
#   真源见 core/lib/vector_knowledge_center.py:47（_init: f"{get_data_root()}/vector_kb"）
#   2026-10-05 PM 053 §二 之裁：旧稿猜 data\chroma\chroma.sqlite3（该目录实为空）⇒ 假红
VECTOR_KB_SUBDIR = 'vector_kb'
VECTOR_KB_SUBDIR = 'vector_kb'


# ⭐ 依赖自检之**必需**集（承 pm_1386 §二.3 · 2026-10-06）—— (import 名, pip 发行名)。
#   ⚠ 真源 ＝ requirements.txt 之「运行依赖（必需）」诸节；本表**派生**自 import 扫描器
#     scripts/dev/scan_client_deps.py（⛔ 手拟）⇒ 由 tests/unit/test_client_deps_scan.py
#     钉「本表 ≡ 真源」（二源必漂）。⚠ 唯 `find_spec`（⛔ 导入其包 ⇒ ⛔ 起服务 ／ 烧显卡）。
REQUIRED_DEPS = (
    ('flask', 'flask'), ('flask_cors', 'flask-cors'), ('requests', 'requests'),
    ('yaml', 'PyYAML'), ('numpy', 'numpy'), ('PIL', 'Pillow'), ('ffmpeg', 'ffmpeg-python'),
    ('jwt', 'PyJWT'), ('redis', 'redis'), ('watchdog', 'watchdog'), ('flasgger', 'flasgger'),
    ('dotenv', 'python-dotenv'), ('prometheus_client', 'prometheus_client'),
    ('psutil', 'psutil'), ('tiktoken', 'tiktoken'), ('chromadb', 'chromadb'),
)

# ⭐ pm_1569 §二（裁一 · 即刻办）：**净机之 Python 锁 CPython 3.12 · 64 位** —— 包内 wheel
#   21 件（我一手器取）皆 cp312-cp312-win_amd64 ⇒ 3.10 ／ 3.11 ／ 32 位之机**装必败**；
#   旧稿书「3.10 或更新」＝ 假言（⛔ 一名一义）⇒ 前置闸须**检版 fail-loud**（⛔ 静默 ／ ⛔ 半装）。
#   ⚠ **一处定形**：本器为**唯一之判** —— 安装器（install_win_pa.preflight_gates）承此出闸，
#   ⛔ 另写一遍（二源必漂 · 承 L59-62 之族）。
PY_REQUIRED = (3, 12)
PY_REQUIRED_BITS = 64


def classify_python(impl, ver, bits):
    u'''⭐ Python 版之判（**一处定形** · pm_1569 §二）：CPython ∧ ver >= 3.12 ∧ 64 位。

    返回 (ok, 人话之实, 修之门)；⛔ 静默 —— 不合则**点名本机之实**（实现 ／ 版 ／ 位数）＋ 门。
    '''
    _v = tuple(ver or ())[:3]
    _impl = (impl or u'').lower()
    _bits = int(bits or 0)
    _ok = (_impl == u'cpython') and (_v >= PY_REQUIRED) and (_bits == PY_REQUIRED_BITS)
    _why = u'%s %s · %d 位' % (impl or u'?', u'.'.join(str(x) for x in _v) or u'?', _bits)
    if _ok:
        return True, _why, u''
    return False, _why, (u'修之门：装 CPython %d.%d · %d 位'
                         u'（python.org ⇒ Windows installer (64-bit)）'
                         % (PY_REQUIRED[0], PY_REQUIRED[1], PY_REQUIRED_BITS))


def probe_python():
    u'''本机之 Python 之实（sys.version_info ＋ sys.maxsize ⇒ 64 位）⇒ classify_python 之果。'''
    return classify_python(sys.implementation.name, sys.version_info[:3],
                           64 if sys.maxsize > 2 ** 32 else 32)


def probe_deps(deps=None):
    u'''⭐ **依赖自检**（承 pm_1386 §二.3）：必需集逐包「在 ∨ 缺」＋ 缺 ⇒ **人话之因 ＋ 修之门**。

    ⚠ 唯 `find_spec`（⛔ 导入其包）；⛔ 静默 —— 缺则**点名**（import 名 ＋ pip 名）＋ 门
    （`pip install -r requirements.txt`）。``deps`` 可传（自测用）。
    '''
    import importlib.util as _ilu
    ds = REQUIRED_DEPS if deps is None else tuple(deps)
    miss = []
    for mod, dist in ds:
        try:
            ok = _ilu.find_spec(mod) is not None
        except Exception:
            ok = False
        if not ok:
            miss.append(u'%s（pip 名 %s）' % (mod, dist))
    if not miss:
        return (True, u'ok（必需 %d 包皆在）' % len(ds), u'')
    return (False,
            u'⛔ 缺依赖 %d 个：%s ⇒ 网关起来即 ImportError ｜ 修之门：'
            u'python -m pip install -r requirements.txt（离线包：见 wheel\\ 目录）'
            % (len(miss), u'、'.join(miss)),
            u'')


def resolve_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def resolve_port(root):
    try:
        sys.path.insert(0, root)
        from core.lib.port_config import gateway_port
        return int(gateway_port()), u'真源 core.lib.port_config'
    except Exception as e:
        return 5102, u'回落常量 5102（真源不可读：%s）' % type(e).__name__


def classify_port_error(e):
    return u'端口占用 ∨ TIME_WAIT（不应答 ⇒ 恐 TIME_WAIT ／ 他进程占）（%s）' % e


def classify_db_error(e):
    m = str(e).lower()
    if 'readonly' in m or 'read-only' in m:
        return False, u'不可写（readonly）⇒ 正是 P4 之正控：库文件/目录权限不足'
    if 'locked' in m or 'busy' in m:
        return True, u'库被占用（网关在跑？）⇒ 报而 ⛔ 判 FAIL'
    return False, u'不可写（%s: %s）' % (type(e).__name__, e)


def tcp_open(port, timeout=1.5):
    s = socket.socket()
    s.settimeout(timeout)
    try:
        return s.connect_ex((HOST, port)) == 0
    finally:
        s.close()


def classify_config_error(e):
    return (u'不可读（%s: %s）⇒ 起服必拒（PortUnconfigured 族 ⇒ 配置按 CWD 解析 · '
            u'承 2026-10-05 事故）' % (type(e).__name__, e))


def probe_config_port(root):
    try:
        sys.path.insert(0, root)
        from core.lib.port_config import gateway_port
        return True, u'可读 ⇒ %d' % int(gateway_port()), u'真源 core.lib.port_config'
    except Exception as e:
        return False, classify_config_error(e), u''


def _try_bind(addr, port):
    u'''试绑**一面**；返回 (成, OSError)。'''
    s = socket.socket()
    try:
        s.bind((addr, port))
        return True, None
    except OSError as e:
        return False, e
    finally:
        s.close()


def probe_port(port):
    u'''端口闸（**成对** · 承 PM 073 §三）：⛔ 只绑 `127.0.0.1`（实例绑 `0.0.0.0` ⇒ **假绿** · 我一手实证）。

    ⒜ 先 **TCP 实连** ⇒ 有实例在应答 ⇒ 判「已被占用」（⛔ 以「绑得上」为据）｜
    ⒝ 再于**两面**（`0.0.0.0` ∧ `127.0.0.1`）试绑 ⇒ 任一不中 ⇒ 判占用 ∨ TIME_WAIT。
    由（本机一手）：实例绑 `0.0.0.0` 时 `bind(127.0.0.1)` **仍 OK**；绑 `127.0.0.1` 时 `bind(0.0.0.0)` **仍 OK**
    ⇒ ⭐ WSAEADDRINUSE 只对**同址** ⇒ **单面之绑 ⛔ 足信**。
    '''
    if tcp_open(port):
        return False, u'端口已被占用（已有实例在应答 ⇒ 先判是否该停）', u''
    for _addr in ('0.0.0.0', '127.0.0.1'):
        _ok, _e = _try_bind(_addr, port)
        if not _ok:
            return False, classify_port_error(_e), u''
    return True, u'可绑', u''


def probe_writable(d, env_name=u'', source=u''):
    u'''可写之判（试写 ＋ fsync ＋ 删）⇒ `(ok, reason, note)`。

    ⭐ 9.0.13 P0：委 `pa_paths.probe_writable`（**一处定形**）—— 失败之因必含
    「径 ＋ 谁定之（env/缺省）＋ 迁之门」；供 `install_win_pa.preflight_gates` 之旧调用形（无 env 语境）亦 ⛔ 崩。
    '''
    return pa_paths.probe_writable(d, env_name=env_name, source=source)


def resolve_vector_kb(root):
    """⭐ 向量库径 = **真源**（⛔ 字面猜径）：`core.lib.config_helper.get_vector_root()`
    （⭐ 9.0.13 P0：env `PA_VEC_DIR` 优先；缺 ⇒ 旧形 `<data_root>/vector_kb`）。
    归 (kb_dir, src): kb_dir 为绝对径（真源若相对则按 root 拼）。"""
    try:
        sys.path.insert(0, root)
        from core.lib.config_helper import get_vector_root
        v = str(get_vector_root())
        if not os.path.isabs(v):
            v = os.path.join(root, v)
        return os.path.abspath(v), (u'真源 core.lib.config_helper.get_vector_root()（env PA_VEC_DIR 优先）⇒ %s' % v)
    except Exception as e1:
        try:
            from core.lib.config_helper import get_data_root
            dr = get_data_root()
            base = dr if os.path.isabs(str(dr)) else os.path.join(root, str(dr))
            return os.path.join(base, VECTOR_KB_SUBDIR), (
                u'真源 core.lib.config_helper.get_data_root() ⇒ %s（旧形 <data_root>/vector_kb；'
                u'get_vector_root 不可读：%s: %s）' % (dr, type(e1).__name__, e1))
        except Exception as e2:
            return pa_paths.vector_kb(), (
                u'⚠ 回落 pa_paths.vector_kb()（真源不可读：%s: %s ／ %s: %s）'
                % (type(e1).__name__, e1, type(e2).__name__, e2))


def probe_vector_db(kb_dir, src=u''):
    """⭐ 两栏分报（承 PM 053 §二.3 · 承 §三一二）：
    栏一「未见」（库目录 或 库文件不存在 · 首启 或 径变 或 **径错**）
    栏二「不可写」（存在而权限/占用之病 ⇒ 正是 P4 之正控）
    两栏**皆 FAIL**，但**措辞与因各异** ⇒ 后人可辨「无库」↔「库不可写」；两栏**皆点名真径**。"""
    db = os.path.join(kb_dir, 'chroma.sqlite3')
    if not os.path.isdir(kb_dir):
        return False, u'未见 ⇐ 库目录不存在：%s（首启 或 径变 或 径错 ⇒ 先核真源 <data_root>/vector_kb）' % kb_dir, src
    if not os.path.exists(db):
        return False, u'未见 ⇐ 库文件不存在：%s（首启 或 径变 或 径错）' % db, src
    ok_w, why_w, _ = probe_writable(kb_dir)
    if not ok_w:
        return False, u'不可写 ⇐ 库目录：%s（%s）' % (kb_dir, why_w), src
    con = None
    try:
        con = sqlite3.connect(db, timeout=3)
        v = int(con.execute('PRAGMA user_version').fetchone()[0])
        con.execute('BEGIN IMMEDIATE')
        con.execute('PRAGMA user_version=%d' % v)      # 同值写 ⇒ ⛔ 改内容 · 唯验「真触盘」
        con.execute('ROLLBACK')
        return True, u'可写（%s · user_version 同值写 + 回滚过）' % db, src
    except Exception as e:
        ok2, why2 = classify_db_error(e)
        return ok2, u'%s（%s）' % (why2, db), src
    finally:
        if con is not None:
            con.close()


OLLAMA_FIX_DOOR = (
    u'装 Ollama ∨ 起 `ollama serve` ∨ 拉权重（`ollama pull <模型>`）∨ 指远端（P2 · 未接）'
)


def classify_ollama(tcp_ok, model_count, tags_err=None, first_model=None):
    u'''⭐ 纯函数（⛔ 无网络依赖 ⇒ 可自测）：由「TCP 状 ＋ 权重数」定**三态**。

    ⭐ 承 PM 1369 §三.2「ollama 项 ⛔ 只退 rc」之病 —— 本器须把「因 ＋ 修之门」说成
    **人话**，⛔ 装成可用（承产品三禁）。三态：
      ⒜ 未接（TCP 无应答）        ⇒ FAIL：点名「⛔ 未接」＋ 修之门
      ⒝ 在而**无权重**（models=0）⇒ FAIL：「在」⟷「可用」**⛔ 一事** ＋ 修之门
      ⒞ 在且有权重（models>=1）   ⇒ PASS：点名 `models=N`（首模型）
    ⚠ 一手之据（2026-10-06 07:52 · 本机）：TCP 应答 ∧ `models=3` ⇒ 旧稿之
      「在（TCP 应答）」一名 = **三名蔽作一名**（未接 ／ 无权重 ／ 可用）。

    返回 (ok, reason, note) —— 与 `collect()` 之三元组同形。
    '''
    if not tcp_ok:
        return (
            False,
            u'⛔ 未接：ollama %s:%d 无应答 ⇒ 本机模型路不可用 ｜ 修之门：%s'
            % (HOST, OLLAMA_PORT, OLLAMA_FIX_DOOR),
            u'',
        )
    if tags_err is not None:
        return (
            False,
            u'⛔ 不可达：TCP 应答 ⇐ 而 `/api/tags` 读不到（%s）⇒ 无从判「有无权重」 ｜ 修之门：%s'
            % (tags_err, OLLAMA_FIX_DOOR),
            u'',
        )
    if int(model_count or 0) <= 0:
        return (
            False,
            u'⛔ 在 · 无权重：%s:%d 在（TCP 应答）而 `models=0` ⇒ 本机模型路 ⛔ 可用 ｜ 修之门：%s'
            % (HOST, OLLAMA_PORT, OLLAMA_FIX_DOOR),
            u'models=0',
        )
    _note = u'models=%d' % int(model_count)
    if first_model:
        _note += u'（首 %s）' % first_model
    return True, u'在（TCP 应答 ∧ models>0）', _note


def probe_ollama():
    u'''⭐ 三态探活（承 PM 1369 §三.2）：⛔ 只退 rc；须出「人话之因 ＋ 修之门」。

    ⚠ 「端口开」⟷「有权重」**⛔ 一事**；「无权重」⇒ FAIL（本机模型路不可用），
      仍**分栏**报因 ⇒ 后人可辨「未接」↔「无权重」↔「可用」。
    '''
    if not tcp_open(OLLAMA_PORT):
        return classify_ollama(False, None)
    try:
        with urllib.request.urlopen('http://%s:%d/api/tags' % (HOST, OLLAMA_PORT), timeout=3) as r:
            _ms = (json.loads(r.read().decode('utf-8')) or {}).get('models', []) or []
        _first = (_ms[0] or {}).get('name') if _ms else None
        return classify_ollama(True, len(_ms), None, _first)
    except Exception as e:
        return classify_ollama(True, None, type(e).__name__)


def probe_install_root(root, roots_info=None):
    u'''⭐ 装根只读之判（9.0.13 P0 · **报而阻起** 者唯「运行根落装根内」）：
      ① 三根皆在装根外 ⇒ PASS（装根 0 写 —— 本批之的；缺省恒如此）；
      ② 任一在装根内 ⇒ **FAIL**（装 Program Files 时必 WinError 5 —— 9.0.12 之病）。
    ⚠ 何以「装根可写（开发树）」亦判红（不从 os.access 之虚绿 —— 一手：deny (AD,WD) 后
      os.access(root, W_OK) 仍报 True）：装根之可写性**非**本批之契约；契约是运行根**不在**装根内。
    '''
    r = roots_info or pa_paths.roots()
    inside = [n for n, i in r.items() if pa_paths.is_inside(i[u'path'], root)]
    if not inside:
        return True, u'运行根皆在装根外（装根 ⛔ 需可写 · 0 写）', u'装根＝%s' % root
    _names = u' · '.join(u'%s(%s)' % (n, r[n][u'path']) for n in inside)
    return False, (u'运行根落在**只读装根**内（装 Program Files 必 WinError 5）：%s ｜ '
                   u'修之门：设 env PA_DATA_DIR / PA_LOG_DIR / PA_VEC_DIR 至用户可写处'
                   u'（缺省 %%LOCALAPPDATA%%\\ClawsJoyPA\\{data,logs,vec}）' % _names), u''


def collect(root):
    u'''逐项自检 ⇒ (port, 端口真源, items)；⭐ 9.0.13 P0：三根（data/logs/vec）**分栏**可写。'''
    port, src = resolve_port(root)
    r = pa_paths.roots()
    items = [(u'Python 版（须 %d.%d · %d 位）'
              % (PY_REQUIRED[0], PY_REQUIRED[1], PY_REQUIRED_BITS), probe_python()),
             (u'依赖（必需 %d 包）' % len(REQUIRED_DEPS), probe_deps())]
    items.append((u'services.gateway.port 可读', probe_config_port(root)))
    items.append((u'端口 %d 可绑' % port, probe_port(port)))
    items.append((u'安装根只读（运行根隔离）', probe_install_root(root, r)))
    for _n, _label in ((u'data', u'data 根可写（PA_DATA_DIR）'),
                       (u'logs', u'logs 根可写（PA_LOG_DIR）'),
                       (u'vec', u'vec 根可写（PA_VEC_DIR）')):
        _info = r[_n]
        items.append((_label, probe_writable(_info[u'path'], _info[u'env'], _info[u'source'])))
    kb_dir, kb_src = resolve_vector_kb(root)
    items.append((u'向量库可写', probe_vector_db(kb_dir, kb_src)))
    items.append((u'ollama %s:%d' % (HOST, OLLAMA_PORT), probe_ollama()))
    return port, src, items


#: ⭐ **降级之闸（advisory）** —— 报而不阻（承 pm_1569 §三「本机模型可选」· pm_1577 §四.1「净机必起」）。
#   ⒜ `ollama` 之三态（未接 ／ 在·无权重 ／ 可用）：**本机模型可选**（主线 ＝ 云端 deepseek 系）
#      ⇒ 其 ⛔ 可用**不阻起**（⛔ 阻 ⇒ 净机恒⛔起 ＝ ⒞ 之的落空）。
#   ⒝ 「向量库**未见**」：**首启之常貌** —— 真源 `core/lib/vector_knowledge_center.py:47` 之
#      `_init` 先 `mkdir(parents=True, exist_ok=True)` 再 `PersistentClient` ⇒ **自建**
#      ⇒ 「未见」⛔ 是病 ⇒ **⛔ 阻起**。
#   ⚠ 「向量库 **不可写**」仍**阻起**（真病 —— 原器之的 · P4 之正控）；`--strict` ⇒ 全按旧律（皆阻）。
ADVISORY_PREFIXES = ('ollama',)
ADVISORY_NEEDLES = ('未见',)


def is_advisory(name, reason=u''):
    u'''该闸「报而不阻」否（**一处定形**）—— 唯上列二族；余者皆阻起。'''
    n = name or u''
    if any(n.startswith(p) for p in ADVISORY_PREFIXES):
        return True
    if n.startswith(u'向量库可写') and any(x in (reason or u'') for x in ADVISORY_NEEDLES):
        return True
    return False


def verdict(items, strict=False):
    u'''总判 ⇒ (rc, 先修之名)。rc 0 ＝ 可起。

    ⚠ 降级之闸（`is_advisory`）缺 ⇒ 记 **WARN** 而 ⛔ 计入 rc（除 `strict` ／ `--strict` 之旧律）。
    '''
    bad = []
    for n, (ok, reason, _x) in items:
        if ok:
            continue
        if (not strict) and is_advisory(n, reason):
            continue
        bad.append(n)
    return (0 if not bad else 2), bad


def degraded(items, strict=False):
    u'''降级之闸之名（报而行）—— `strict` 之下恒空。'''
    if strict:
        return []
    return [n for n, (ok, reason, _x) in items if (not ok) and is_advisory(n, reason)]


def selftest():
    hits = []

    def say(ok, name):
        print(u'  %s %s' % (u'✓' if ok else u'✗', name))
        hits.append(bool(ok))

    def case(name, expect, items, strict=False):
        rc, bad = verdict(items, strict)
        say(rc == expect, u'%s ⇒ rc=%d 期望=%d%s' % (name, rc, expect,
                                                     (u'（点名：' + u'；'.join(bad) + u'）') if bad else u''))

    ok6 = [(u'a', (True, u'ok', u'')), (u'b', (True, u'ok', u'')), (u'c', (True, u'ok', u'')),
           (u'd', (True, u'ok', u'')), (u'e', (True, u'ok', u'')), (u'f', (True, u'ok', u''))]
    ro = sqlite3.OperationalError('attempt to write a readonly database')
    lk = sqlite3.OperationalError('database is locked')

    class PortUnconfigured(Exception):
        pass

    cf = PortUnconfigured(u'services.gateway.port 未配置 ⇒ 拒启（不回落字面量）')
    case(u'正控：六项全过 ⇒ 可起', 0, ok6)
    case(u'反例：配置不可读 ⇒ 判红', 2,
         [(u'services.gateway.port 可读', (False, classify_config_error(cf), u''))] + ok6[1:])
    case(u'反例：端口被占 ⇒ 判红', 2, ok6[:1] + [(u'端口 5102 可绑', (False, classify_port_error(lk), u''))] + ok6[2:])
    # ⭐ 承 PM 073 §三：端口闸之**真**成对控（⛔ 以 classify 代读物 —— 上一条 ＝「假控」）
    _L = socket.socket(); _L.bind(('0.0.0.0', 0)); _L.listen(1)
    try:
        _P = _L.getsockname()[1]
        _occ = probe_port(_P)
        say(_occ[0] is False and u'占用' in _occ[1], u'正控：真监听（0.0.0.0）⇒ 端口闸判「已被占用」（⛔ 假绿）')
    finally:
        _L.close()
    _F = socket.socket(); _F.bind(('0.0.0.0', 0)); _PF = _F.getsockname()[1]; _F.close()
    _free = probe_port(_PF)
    say(_free[0] is True and u'可绑' in _free[1], u'反例：空端口 ⇒ 判「可绑」')
    case(u'反例：向量库 readonly ⇒ 判红', 2,
         ok6[:3] + [(u'向量库可写', classify_db_error(ro) + (u'',))] + ok6[4:])
    _oll = ok6[:4] + [(u'ollama %s:%d' % (HOST, OLLAMA_PORT), classify_ollama(False, None))] + ok6[5:]
    case(u'正控：ollama 未接 ⇒ **降级**（报而⛔ 阻起）', 0, _oll)
    case(u'反控：--strict 之下 ollama 未接 ⇒ 判红（旧律）', 2, _oll, strict=True)
    say(degraded(_oll) == [u'ollama %s:%d' % (HOST, OLLAMA_PORT)],
        u'正控：降级之名入 [降级] 之列（供人读）')
    _vecnew = ok6[:5] + [(u'向量库可写', probe_vector_db(os.path.join(sys.prefix, '__nope_vk__')))] + ok6[6:]
    _vn = _vecnew[5][1][1]
    say(u'未见' in _vn, u'正控：首启（库目录 ⛔ 见）⇒ 因含「未见」')
    case(u'正控：向量库「未见」（首启 · chromadb 自建）⇒ **降级**', 0, _vecnew)
    case(u'反控：--strict 之下「未见」⇒ 判红（旧律）', 2, _vecnew, strict=True)
    # ⭐ 承 PM 1369 §三.2：ollama 三态须**分栏**（⛔ 只退 rc · ⛔ 装成可用）
    _oa = classify_ollama(False, None)
    say(_oa[0] is False and (u'⛔ 未接' in _oa[1]) and (u'装 Ollama' in _oa[1]),
        u'正控：ollama 未接 ⇒ 判红 ＋ 人话之因 ＋ 修之门（点名装 Ollama）')
    _ob = classify_ollama(True, 0)
    say(_ob[0] is False and (u'无权重' in _ob[1]) and (u'ollama pull' in _ob[1]),
        u'正控：端口开而 models=0 ⇒ 判红（「在」⟷「可用」⛔ 一事）＋ 点名拉权重')
    _oc = classify_ollama(True, 3, None, u'qwen2.5:7b')
    say(_oc[0] is True and (u'models=3' in _oc[2]) and (u'qwen2.5:7b' in _oc[2]),
        u'反例：在且有权重 ⇒ 过（models=3 ∧ 点名首模型）')
    _od = classify_ollama(True, None, u'HTTPError')
    say(_od[0] is False and (u'不可达' in _od[1]),
        u'正控：/api/tags 读不到 ⇒ 判红（⛔ 当「在」）')
    case(u'正控：库 locked（网关在跑）⇒ 报而 ⛔ 判 FAIL', 0,
         ok6[:3] + [(u'向量库可写', classify_db_error(lk) + (u'',))] + ok6[4:])
    say(u'端口占用' in classify_port_error(lk), u'正控：端口占用之因含「端口占用」∧ 人话')
    say(u'readonly' in classify_db_error(ro)[1], u'正控：readonly 之因含「readonly」∧ 人话')
    say(u'占用' in classify_db_error(lk)[1], u'正控：locked 之因含「占用」∧ 人话')
    say(classify_db_error(lk)[0] is True, u'正控：locked 之 ok=True（⛔ 误判红）')
    say(u'不可读' in classify_config_error(cf), u'正控：配置不可读之因含「不可读」∧ 人话')
    import tempfile, shutil
    _t = tempfile.mkdtemp(prefix='p4_vk_')
    try:
        _kb = os.path.join(_t, VECTOR_KB_SUBDIR)
        os.makedirs(_kb)
        _db = os.path.join(_kb, 'chroma.sqlite3')
        _c = sqlite3.connect(_db); _c.execute('PRAGMA user_version=0'); _c.close()
        _ok = probe_vector_db(_kb, 'selftest')
        say(_ok[0] is True and _db in _ok[1], u'正控：真径可写 ⇒ 绿 ∧ 点名该径')
        _np = os.path.join(_t, 'nope')
        _no = probe_vector_db(_np, 'selftest')
        say(_no[0] is False and u'未见' in _no[1] and _np in _no[1],
            u'反例：真径未见 ⇒ 红 ∧ 分栏「未见」∧ 点名该径')
        _kb2 = os.path.join(_t, 'kb2'); os.makedirs(_kb2)
        os.makedirs(os.path.join(_kb2, 'chroma.sqlite3'))   # 库位是目录 ⇒ sqlite 打不开
        _nw = probe_vector_db(_kb2, 'selftest')
        say(_nw[0] is False and u'不可写' in _nw[1] and os.path.join(_kb2, 'chroma.sqlite3') in _nw[1],
            u'反例：真径不可写 ⇒ 红 ∧ 分栏「不可写」∧ 点名该径')
        say((u'未见' in _no[1]) and (u'不可写' in _nw[1]) and _no[1] != _nw[1],
            u'正控：「未见」⟷「不可写」分栏互斥（⛔ 并一栏）')
    finally:
        shutil.rmtree(_t, ignore_errors=True)
    say(VECTOR_KB_SUBDIR == 'vector_kb', u'正控：向量库子径 = vector_kb（真源 <data_root>/vector_kb）')
    import io as _io, ast as _ast
    _tr = _ast.parse(_io.open(__file__, encoding='utf-8').read())
    _mn = [n for n in _tr.body if isinstance(n, _ast.FunctionDef) and n.name == 'main']
    _cd = [x for x in _ast.walk(_mn[0]) if isinstance(x, _ast.Call) and getattr(x.func, 'attr', '') == 'chdir'] if _mn else []
    say(len(_cd) == 1, u'正控：main 含 os.chdir(root) 恰一处（独立跑免 CWD 之病 · AST 验）')
    _dp = probe_deps((('no_such_mod_zzz', 'no-such-dist'),))
    say(_dp[0] is False and u'修之门' in _dp[1] and u'no_such_mod_zzz' in _dp[1] and u'no-such-dist' in _dp[1],
        u'正控：缺依赖 ⇒ 判红 ＋ 点名（import 名 ＋ pip 名）＋ 修之门（⛔ 静默）')
    say(probe_deps((('json', 'n/a'), ('os', 'n/a')))[0] is True,
        u'反例：在 ⇒ 过（⛔ 假红）')
    say(probe_deps(REQUIRED_DEPS)[0] is True and u'必需' in probe_deps(REQUIRED_DEPS)[1],
        u'正控：本机之必需集 ⇒ 过 ∧ 点名其数（若红 ⇒ 本机缺依赖 · 见其因）')
    _pk = classify_python(u'cpython', (3, 12, 10), 64)
    say(_pk[0] is True and (u'3.12.10' in _pk[1]),
        u'正控：CPython 3.12.10 · 64 位 ⇒ 过（⛔ 假红）')
    _po = classify_python(u'cpython', (3, 10, 11), 64)
    say(_po[0] is False and (u'3.12' in _po[2]) and (u'修之门' in _po[2]),
        u'反例：CPython 3.10 · 64 位 ⇒ 判红 ＋ 点名须 3.12 ＋ 修之门')
    _pb = classify_python(u'cpython', (3, 12, 10), 32)
    say(_pb[0] is False and (u'64' in _pb[2]),
        u'反例：CPython 3.12 · **32 位** ⇒ 判红 ＋ 点名须 64 位')
    # ⭐ 9.0.13 P0：可写根之齿（缺省 ／ env 覆 ／ 不可写 ／ 装根隔离 ／ 禁 .pyc）
    _la = os.path.join(tempfile.gettempdir(), u'p4_localappdata_selftest')
    _fake = {u'LOCALAPPDATA': _la}
    _dft = pa_paths.resolve(u'logs', _fake)
    say(_dft[u'path'] == os.path.join(_la, u'ClawsJoyPA', u'logs') and _dft[u'default'],
        u'正控：PA_LOG_DIR 缺省 ⇒ %LOCALAPPDATA%\\ClawsJoyPA\\logs（⛔ 装根）')
    _ov = dict(_fake)
    _ov[u'PA_LOG_DIR'] = os.path.join(tempfile.gettempdir(), u'p4_override_logs')
    _res = pa_paths.resolve(u'logs', _ov)
    say(_res[u'path'] == os.path.abspath(_ov[u'PA_LOG_DIR']) and not _res[u'default'],
        u'正控：env PA_LOG_DIR ⇒ 覆缺省（一处定形 · ⛔ 二源）')
    _ce = pa_paths.child_env(dict(_fake))
    say(bool(_ce.get(u'PA_DATA_DIR')) and bool(_ce.get(u'PA_LOG_DIR')) and bool(_ce.get(u'PA_VEC_DIR'))
        and _ce.get(u'CLAWSJOY_DATA_DIR') == _ce.get(u'PA_DATA_DIR')
        and _ce.get(u'PYTHONDONTWRITEBYTECODE') == u'1',
        u'正控：子进程 env 注入三根 ＋ CLAWSJOY_DATA_DIR ＋ 禁 .pyc')
    _venv = dict(_fake)
    _venv[u'PA_VEC_DIR'] = os.path.join(tempfile.gettempdir(), u'p4_override_vec')
    say(pa_paths.vector_kb(_venv) == os.path.abspath(_venv[u'PA_VEC_DIR']),
        u'正控：PA_VEC_DIR 即向量库目录（env 可覆）')
    _t2 = tempfile.mkdtemp(prefix=u'p4_roots_')
    try:
        _blk = os.path.join(_t2, u'blocker')
        with open(_blk, u'wb') as _fh:
            _fh.write(b'x')
        _bad = pa_paths.probe_writable(os.path.join(_blk, u'x'), env_name=u'PA_LOG_DIR', source=u'selftest')
        say(_bad[0] is False and (u'不可写' in _bad[1]) and (u'PA_LOG_DIR' in _bad[1]) and (u'修之门' in _bad[1]),
            u'反例：根不可写 ⇒ 判红 ＋ 点名径/env ＋ 修之门（⛔ 静默）')
        _good = pa_paths.probe_writable(os.path.join(_t2, u'ok'), env_name=u'PA_DATA_DIR', source=u'selftest')
        say(_good[0] is True and (u'可写' in _good[1]), u'正控：可写目录 ⇒ 绿')
        _fake_root = os.path.join(tempfile.gettempdir(), u'p4_install_nope')
        _out_env = dict(_fake)
        _out_env[u'PA_DATA_DIR'] = os.path.join(_fake_root, u'data')
        _out_env[u'PA_LOG_DIR'] = os.path.join(_fake_root, u'logs')
        _out_env[u'PA_VEC_DIR'] = os.path.join(_fake_root, u'vec')
        _out = probe_install_root(_fake_root, pa_paths.roots(_out_env))
        say(_out[0] is False and (u'只读装根' in _out[1]) and (u'修之门' in _out[1]),
            u'反例：运行根落只读装根内 ⇒ 判红 ＋ 修之门（9.0.12 之病）')
        _out2 = probe_install_root(os.path.join(tempfile.gettempdir(), u'p4_install_nope'), pa_paths.roots())
        say(_out2[0] is True and (u'装根外' in _out2[1]), u'正控：缺省三根皆在装根外 ⇒ 绿（装根 0 写）')
    finally:
        shutil.rmtree(_t2, ignore_errors=True)
    n, t = sum(1 for c in hits if c), len(hits)
    print(u'=== 自检器自测 %d/%d 通过（%s）===' % (n, t, u'rc=0' if n == t else u'rc=2'))
    return 0 if n == t else 2


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--root', default=u'')
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--strict', action='store_true',
                    help=u'旧律：降级之闸亦阻起（默认关）')
    a = ap.parse_args()
    if a.self_test:
        return selftest()
    root = a.root or resolve_root()
    try:
        os.chdir(root)          # 独立跑亦免 CWD 之病（配置按 CWD 解析 · 承 2026-10-05 事故）
    except Exception as e:
        print(u'[自检器异常] os.chdir(%s) 失败：%s: %s（rc=1 ⇒ 视同未审 · ⛔ 起）' % (root, type(e).__name__, e))
        return 1
    try:
        port, src, items = collect(root)
    except Exception as e:
        print(u'[自检器异常] %s: %s（rc=1 ⇒ 视同未审 · ⛔ 起）' % (type(e).__name__, e))
        return 1
    print(u'[自检] PA 网关启动前 · root=%s\n[端口真源] %s' % (root, src))
    print(u'[可写根]（⭐ 9.0.13 P0：装根只读 ⇒ 运行态 ⛔ 落装根 · env 可覆）')
    print(pa_paths.describe())
    _deg = degraded(items, a.strict)
    for name, (ok, reason, note) in items:
        _warn = (not ok) and is_advisory(name, reason) and (not a.strict)
        print(u'  %s %-18s ⇒ %s%s' % (u'[PASS]' if ok else (u'[WARN]' if _warn else u'[FAIL]'),
                                      name, reason, (u'（' + note + u'）') if note else u''))
    rc, bad = verdict(items, a.strict)
    if _deg:
        print(u'[降级] ⚠ %d 项报而⛔ 阻起（可选之能 · 承 pm_1569 §三）：%s'
              % (len(_deg), u' · '.join(_deg)))
        print(u'[降级] ⚠ 本机模型路：走云端；向量库：首用自建。⛔ 影响网关与页面。')
    print(u'[总判] %s（%d/%d）%s' % (u'PASS ⇒ 可起' if rc == 0 else u'FAIL ⇒ ⛔ 起',
                                    len(items) - len(bad) - len(_deg), len(items),
                                    (u'｜先修：' + u' · '.join(bad)) if bad
                                    else ((u'（%d 项降级（⛔ 阻起）、详上「[降级]」）' % len(_deg)) if _deg else u'')))
    return rc


if __name__ == '__main__':
    sys.exit(main())
