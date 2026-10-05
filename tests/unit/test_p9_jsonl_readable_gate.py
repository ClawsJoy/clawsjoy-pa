# -*- coding: utf-8 -*-
"""P9 补 · 「**读不到 ≠ 0**」判据门（2026-09-29 · PM 裁「该修」）。

病：`_jsonl_lines()`（``core/pa/gateway_routes.py``）旧实现 ``except: return 0`` ⇒
**读不了**被报成**是空的**。0 看起来像读数 ⇒ 实测（独占锁 ``events.jsonl``）回执里出现
``events_lines_before: 0``，而**真实是 131**。与 437 假绿 / 验收-B「过期 0」**同族**。

修（PM 三条要求）：① 失败区分 ``None`` 与 0；② 回执加 ``events_readable``；
③ 前端把「读数不可得」与「确实没落盘」**分开说**。

本文件三层判据，**都带反例齿**（承 C18：判据必须能红）：
 1. 纯函数层：**不可读 ⇒ None**（不是 0）＋ 反例齿＝把旧实现放同一面 ⇒ **必须给 0**；
 2. 接线层（判据打在设计上）：两张回执都声明 ``events_readable``；差值走 ``_lines_delta``（None 可传）；
    且**旧的裸减法与旧 recorded 表达式不许再在**；
 3. 前端三层话术：**读数不可得** 与 **未落盘** 必须分得开 ＋ 反例齿＝把第三支条件改恒假 ⇒ 必须判红。

本文件不改产品代码；临时 js 落仓内 scratch。
"""
from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
import ctypes
import ctypes.wintypes as wt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.pa.gateway_routes import _jsonl_lines, _lines_delta  # noqa: E402

# 拆面（承 pm 1334 §三.1 · 惟改径）：P9 判据块之家 ＝ web/pa/faces/send.js
PA = ROOT / "web" / "pa" / "faces" / "send.js"
GR = ROOT / "core" / "pa" / "gateway_routes.py"
SCRATCH = ROOT / "data" / "tmp" / "_p9_jsonl_readable"

_BLOCK_START = "const rc = paRun.receipt;"
_BLOCK_TAIL = "'P9 BUG-1');"

UNREADABLE = {"recorded": False, "events_readable": False, "session_readable": True,
              "events_lines_before": None, "events_lines_after": None, "events_delta": None,
              "session_lines_before": 4, "session_lines_after": 4, "session_delta": 0,
              "session_path": "s.jsonl", "error": "[Errno 13] Permission denied"}
NOT_RECORDED = {"recorded": False, "events_readable": True, "session_readable": True,
                "session_lines_before": 4, "session_lines_after": 4, "events_lines_before": 127,
                "events_lines_after": 127, "session_path": "s.jsonl"}


# ---- 独占锁（真造「存在但读不了」，与实测现场同构） -------------------------

_GENERIC_READ = 0x80000000
_OPEN_EXISTING = 3
_FILE_ATTRIBUTE_NORMAL = 0x80


def _lock_exclusive(path: Path):
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.CreateFileW.restype = ctypes.c_void_p
    k.CreateFileW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p,
                              wt.DWORD, wt.DWORD, ctypes.c_void_p]
    h = k.CreateFileW(str(path), _GENERIC_READ, 0, None, _OPEN_EXISTING,
                      _FILE_ATTRIBUTE_NORMAL, None)
    assert h and h != ctypes.c_void_p(-1).value, "建锁失败 err=%s" % ctypes.get_last_error()
    return k, h


def _old_jsonl_lines(path):
    """改前实现（**逐字复制自存底件**，用来说明齿）：失败即 0。"""
    try:
        with open(path, "rb") as f:
            return sum(1 for ln in f if ln.strip())
    except Exception:
        return 0


# ---- 判据 1：纯函数层 -------------------------------------------------------

def test_missing_file_is_zero_vacuum():
    """文件**真不存在** ⇒ 0（真空 ⇒ 是读数）。"""
    assert _jsonl_lines(ROOT / "data" / "v9" / "pa" / "__no_such__.jsonl") == 0


def test_counts_non_blank_lines():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    p = SCRATCH / "sample.jsonl"
    io.open(p, "w", encoding="utf-8", newline="\n").write('{"a":1}\n\n{"b":2}\n')
    assert _jsonl_lines(p) == 2


def test_unreadable_is_none_not_zero():
    """⭐ 核心：**存在但读不了** ⇒ None（⛔ 不许回 0）。"""
    SCRATCH.mkdir(parents=True, exist_ok=True)
    p = SCRATCH / "locked.jsonl"
    io.open(p, "w", encoding="utf-8", newline="\n").write('{"a":1}\n{"b":2}\n')
    k, h = _lock_exclusive(p)
    try:
        got = _jsonl_lines(p)
    finally:
        k.CloseHandle(h)
    assert got is None, "不可读竟回了 %r（0 会被读成「是空的」= 假读数）" % (got,)
    assert _jsonl_lines(p) == 2, "解锁后应恢复真实读数"


def test_gate_has_teeth_old_impl_would_say_zero():
    """反例齿：旧实现放同一面 ⇒ **必须**给 0 ⇒ 与现口径不同（证明这条闸能红）。"""
    SCRATCH.mkdir(parents=True, exist_ok=True)
    p = SCRATCH / "locked2.jsonl"
    io.open(p, "w", encoding="utf-8", newline="\n").write('{"a":1}\n')
    k, h = _lock_exclusive(p)
    try:
        new_v = _jsonl_lines(p)
        old_v = _old_jsonl_lines(p)
    finally:
        k.CloseHandle(h)
    assert old_v == 0, "旧实现应当给 0（否则本齿无效）"
    assert new_v is None and new_v != old_v, "新旧口径必须可分辨"


def test_lines_delta_propagates_none():
    assert _lines_delta(1, 3) == 2
    assert _lines_delta(None, 3) is None and _lines_delta(3, None) is None


# ---- 判据 2：接线层（判据打在设计上，不靠跑一遍碰运气） ----------------------

def _gr() -> str:
    return io.open(GR, encoding="utf-8").read()


def test_both_receipts_declare_events_readable():
    s = _gr()
    assert s.count('"events_readable": ') == 2, "两张回执（dialog persisted / turn）都应声明 events_readable"
    assert '"session_readable": _ses_readable,' in s, "turn 回执应声明 session_readable"


def test_deltas_go_through_none_safe_helper():
    s = _gr()
    assert s.count('"events_delta": _lines_delta(') == 2
    assert '"events_delta": _ev_after - _ev_before,' not in s, "旧的裸减法仍在 ⇒ None 会炸/会假"
    assert 'recorded": bool(_ses_lines >= 2 and _ev_after > _ev_before)' not in s, "旧的 recorded 表达式仍在"
    assert '"lines_readable": _n is not None,' in s, "sessions 清单应暴露 lines_readable"


# ---- 判据 3：前端三层话术（抽取真码执行） -----------------------------------

def _node() -> str:
    exe = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
    assert exe
    return exe


def _block() -> str:
    s = io.open(PA, encoding="utf-8").read()
    i = s.find(_BLOCK_START)
    assert i > 0, "未找到判据块"
    depth, opened, e = 0, False, i
    while e < len(s):
        ch = s[e]
        if ch == "{":
            depth += 1
            opened = True
        elif ch == "}":
            depth -= 1
            if opened and depth == 0 and not s[e + 1:e + 41].lstrip().startswith("else"):
                e += 1
                break
        e += 1
    blk = s[i:e]
    assert "读数不可得" in blk, "判据块里没有「读数不可得」支 ⇒ 本门无从谈起"
    assert blk.rstrip().endswith("}")
    return blk


def _run(block_js: str, scenarios: dict) -> dict:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    js = ("function run(receipt){\n  const calls=[];\n"
          "  function addLog(t,l){ calls.push({t:String(t), l:(l===undefined?'':String(l))}); }\n"
          "  function saveState(){}\n  const paRun={receipt:receipt};\n  try{\n"
          + block_js + "\n  }catch(e){}\n  return calls;\n}\n"
          "const out={};\nfor (const k of Object.keys(SCEN)) out[k]=run(SCEN[k]);\n"
          "console.log(JSON.stringify(out));\n")
    f = SCRATCH / "harness.js"
    io.open(f, "w", encoding="utf-8", newline="\n").write(
        "const SCEN=" + json.dumps(scenarios, ensure_ascii=False) + ";\n" + js)
    r = subprocess.run([_node(), str(f)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert r.returncode == 0, "node 失败 rc=%s\n%s" % (r.returncode, r.stderr[-600:])
    return json.loads(r.stdout.strip().splitlines()[-1])


def _texts(calls):
    return " || ".join(c["t"] for c in calls or [])


def test_frontend_distinguishes_unreadable_from_not_recorded():
    out = _run(_block(), {"unread": UNREADABLE, "bad": NOT_RECORDED})
    tu, tb = _texts(out["unread"]), _texts(out["bad"])
    assert "读数不可得" in tu, "读数不可得的情形没有单独的话术"
    assert "未落盘" not in tu, "把「读数不可得」说成了「未落盘」（两种事混成一种）"
    assert "已落盘" not in tu, "把「读数不可得」说成了「已落盘」（假绿）"
    assert "未落盘" in tb and "读数不可得" not in tb, "确实没落盘的情形话术不对"


def test_gate_has_teeth_third_branch_removed_is_caught():
    mutant = _block().replace("rc.events_readable===false || rc.session_readable===false", "false")
    assert mutant != _block()
    out = _run(mutant, {"unread": UNREADABLE})
    t = _texts(out["unread"])
    assert "未落盘" in t, "齿失效：拿掉第三支后「读数不可得」竟没掉进「未落盘」⇒ 这把尺是装饰层"

# ---- 判据 4：后端会话面「读不到」不许变成 500 ----------------------------------
# 病（我自己那版修复的**残余**，本轮补）：dialog 路由里 `_ses_lines = len(_sess.history(100000))`
# 是**裸调**，且发生在**回执构造之前** ⇒ 会话文件被独占时**抛异常 ⇒ 整条路由 500**，
# 前端连回执都拿不到 ⇒ 「读数不可得」被静默并进「确实没落盘」。
# 判据：**读不到 ⇒ 仍回 200 ＋ 回执里 session_readable=false**（两种事必须分得开）。


def test_gr_guards_session_history_read():
    s = _gr()
    assert "\n        _ses_lines = len(_sess.history(100000))\n" not in s, \
        "裸调 history() 还在 ⇒ 会话文件被独占时整条路由 500（回执到不了前端）"
    assert '"session_readable": _ses_lines is not None,' in s, \
        "dialog 回执应声明 session_readable（前端第三支靠它）"
    assert '"recorded": bool(_ses_lines is not None and _ses_lines >= 2' in s, \
        "recorded 未防 None ⇒ `None >= 2` 会抛 TypeError"


class _RaisingSession:
    """会话文件被独占的替身：读行数抛异常（与实测「真负例②」同构）。"""

    path = SCRATCH / "locked_session.jsonl"

    def history(self, n=None):
        raise PermissionError("[Errno 13] Permission denied")

    def post(self, role, text):
        raise PermissionError("[Errno 13] Permission denied")


class _FakeEvents:
    path = SCRATCH / "events_fake.jsonl"

    def append(self, *a, **k):
        return None


class _FakeDialog:
    def session(self, sid):
        return _RaisingSession()


class _FakePa:
    dialog = _FakeDialog()
    events = _FakeEvents()
    profile = None

    def handle(self, action, payload=None):
        return {"dialog": {"reply": "ok"}}


def test_dialog_route_survives_unreadable_session():
    """⭐ 端到端：会话读不到 ⇒ **200** ＋ session_readable=false（⛔ 不是 500、⛔ 不是 recorded=true）。"""
    from flask import Flask
    from core.pa.collect import detect_fields
    import core.pa.gateway_routes as gr

    text = "p9 lock probe"
    assert not detect_fields(text), "选定文本不应触发字段收集（否则本测走岔面）"

    app = Flask(__name__)
    gr.register_pa_routes(app, brain=None)
    orig = gr._core
    gr._core = lambda user_id=None: _FakePa()
    try:
        r = app.test_client().post("/v9/pa/dialog",
                                   json={"text": text, "session_id": "p9_lockprobe"})
    finally:
        gr._core = orig
    assert r.status_code == 200, "读不到会话竟回了 %s（回执到不了前端 ⇒ 两种事又混了）" % r.status_code
    per = r.get_json()["persisted"]
    assert per["session_readable"] is False, "回执没把「会话读数不可得」说出来"
    assert per["session_lines"] is None, \
        "读不到却报了 %r（0 会被读成「是空的」= 假读数）" % (per["session_lines"],)
    assert per["recorded"] is False, "读数不可得竟报 recorded=true ⇒ 假绿"

# ---- 判据 5：后端**写腿**失败也不许变成 500（会话腿与事件腿要对称） ---------------
# 病（同一族的另一处，本轮补）：turn 路由里 events 写有 try/except，**会话写是裸调**
# ⇒ 会话文件被占 ⇒ 抛异常 ⇒ 500，前端连回执都拿不到（＝ PM 真负例②的那条路）。


def test_gr_guards_turn_session_write():
    s = _gr()
    naked = ('\n        if _u:\n            _sess.post("user", _u)\n'
             '        if _a:\n            _sess.post("assistant", _a)\n')
    assert naked not in s, "会话写腿仍裸调 ⇒ 会话文件被占时 500（回执到不了前端）"
    assert '"session_error": _ses_err,' in s, "回执应把会话写腿的失败单独说出来"
    assert '"error": _err or _ses_err,' in s, "error 应兼收两条腿（否则会话腿的失败被吞掉）"


class _LockedFileSession:
    """会话文件**真被独占**的替身（path 指向真锁住的件，与实测同构）。"""

    def __init__(self, path):
        self.path = path

    def history(self, n=None):
        raise PermissionError("[Errno 13] Permission denied")

    def post(self, role, text):
        raise PermissionError("[Errno 13] Permission denied")


def _fake_pa(session_obj):
    class _D:
        def session(self, sid):
            return session_obj

    class _E:
        path = SCRATCH / "events_fake.jsonl"

        def append(self, *a, **k):
            return None

    class _P:
        dialog = _D()
        events = _E()
        profile = None

        def handle(self, action, payload=None):
            return {"dialog": {"reply": "ok"}}

    return _P()


def _client(fake):
    import contextlib
    from flask import Flask
    import core.pa.gateway_routes as gr

    @contextlib.contextmanager
    def cm():
        app = Flask(__name__)
        gr.register_pa_routes(app, brain=None)
        orig = gr._core
        gr._core = lambda user_id=None: fake
        try:
            with app.test_client() as c:
                yield c
        finally:
            gr._core = orig

    return cm()


def test_turn_route_survives_locked_session_file():
    """⭐ 端到端（＝ PM 真负例② 的复现）：会话文件真被独占 ⇒ **200** ＋ 回执说得出、⛔ 不是 500。"""
    SCRATCH.mkdir(parents=True, exist_ok=True)
    p = SCRATCH / "locked_turn_session.jsonl"
    io.open(p, "w", encoding="utf-8", newline="\n").write('{"role":"user"}\n')
    k, h = _lock_exclusive(p)
    try:
        with _client(_fake_pa(_LockedFileSession(p))) as c:
            r = c.post("/v9/pa/turn", json={"session_id": "p9_locksess", "user_text": "x"})
    finally:
        k.CloseHandle(h)
    assert r.status_code == 200, "会话文件被占竟回了 %s（回执到不了前端 ⇒ 两种事又混了）" % r.status_code
    j = r.get_json()
    assert j["session_readable"] is False, "读不到却没说「读数不可得」"
    assert j["session_lines_before"] is None and j["session_lines_after"] is None, \
        "读不到却报了数字（0 会被读成「是空的」）"
    assert j["recorded"] is False, "读数不可得竟报 recorded=true ⇒ 假绿"
    assert j["session_error"], "会话写腿失败没在回执里留痕（被吞掉了）"
