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
  3. `data\` **可写**（试写 ＋ `fsync` ＋ 删）
  4. **向量库可写**（真源 `<data_root>/vector_kb` ⇒ ⛔ 字面猜径）｜两段：库目录可写 ⇒ 建得 journal/WAL；`PRAGMA user_version` 同值写 ⇒ 真触盘｜⭐ 「未见」⟷「不可写」**分栏**（且**点名真径**）
  5. `ollama` 服务 `127.0.0.1:11434`（TCP ＋ `/api/tags`）
  6. `logs\` **可写**（console 追加面）
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


def probe_writable(d):
    try:
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, '.preflight_probe_%d' % os.getpid())
        with open(p, 'wb') as f:
            f.write(b'probe')
            f.flush()
            os.fsync(f.fileno())
        os.remove(p)
        return True, u'可写', u''
    except Exception as e:
        return False, u'不可写（%s: %s）' % (type(e).__name__, e), u''


def resolve_vector_kb(root):
    """⭐ 向量库径 = **真源**（⛔ 字面猜径）：`core.lib.config_helper.get_data_root()` + `vector_kb`
    （真源见 `core/lib/vector_knowledge_center.py:47` · `_init` 之默认库）。
    归 (kb_dir, src): kb_dir 为绝对径（data_root 若相对则按 root 拼）。"""
    try:
        sys.path.insert(0, root)
        from core.lib.config_helper import get_data_root
        dr = get_data_root()
        src = u'真源 core.lib.config_helper.get_data_root() ⇒ %s' % dr
    except Exception as e:
        dr = 'data'
        src = u'⚠ 回落字面 data（真源不可读：%s: %s）' % (type(e).__name__, e)
    base = dr if os.path.isabs(str(dr)) else os.path.join(root, str(dr))
    return os.path.join(base, VECTOR_KB_SUBDIR), src


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


def collect(root):
    port, src = resolve_port(root)
    items = [(u'依赖（必需 %d 包）' % len(REQUIRED_DEPS), probe_deps())]
    items.append((u'services.gateway.port 可读', probe_config_port(root)))
    items.append((u'端口 %d 可绑' % port, probe_port(port)))
    items.append((u'data\\ 可写', probe_writable(os.path.join(root, 'data'))))
    kb_dir, kb_src = resolve_vector_kb(root)
    items.append((u'向量库可写', probe_vector_db(kb_dir, kb_src)))
    items.append((u'ollama %s:%d' % (HOST, OLLAMA_PORT), probe_ollama()))
    items.append((u'logs\\ 可写', probe_writable(os.path.join(root, 'logs'))))
    return port, src, items


def verdict(items):
    bad = [n for n, (ok, _r, _x) in items if not ok]
    return (0 if not bad else 2), bad


def selftest():
    hits = []

    def say(ok, name):
        print(u'  %s %s' % (u'✓' if ok else u'✗', name))
        hits.append(bool(ok))

    def case(name, expect, items):
        rc, bad = verdict(items)
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
    case(u'正控：ollama 未接 ⇒ 判红', 2, ok6[:4] + [(u'ollama', classify_ollama(False, None))] + ok6[5:])
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
    n, t = sum(1 for c in hits if c), len(hits)
    print(u'=== 自检器自测 %d/%d 通过（%s）===' % (n, t, u'rc=0' if n == t else u'rc=2'))
    return 0 if n == t else 2


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--root', default=u'')
    ap.add_argument('--self-test', action='store_true')
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
    for name, (ok, reason, note) in items:
        print(u'  %s %-18s ⇒ %s%s' % (u'[PASS]' if ok else u'[FAIL]', name, reason,
                                      (u'（' + note + u'）') if note else u''))
    rc, bad = verdict(items)
    print(u'[总判] %s（%d/%d）%s' % (u'PASS ⇒ 可起' if rc == 0 else u'FAIL ⇒ ⛔ 起',
                                    len(items) - len(bad), len(items),
                                    (u'｜先修：' + u' · '.join(bad)) if bad else u''))
    return rc


if __name__ == '__main__':
    sys.exit(main())
