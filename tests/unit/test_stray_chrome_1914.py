# -*- coding: utf-8 -*-
r"""令 1914 之齿 —— 「跑毕必收」（CW 席之起浏览器者之**收** ＋ **账**）。

一事（pm_1914 §一 之照实）：我席昔以「临时命令行起 headless Chrome」跑 CDP 器 ⇒ **跑毕 ⛔ 收**
  ⇒ 遗 `5` 枚散落实例（口 `9348/9348/9223/9227/9223` · 皆 `cw*` profile）＋ 一大批 `%TEMP%\cw*`。

判据（⭐ 逐条自证 · ⛔ 只报「已绿」）：
  S1 器之自证（源）：起 Chrome 者**必有** `finally` 之收（`taskkill /T /F` ＋ 删 profile）；⛔ 静默之径。
  S2 器之自证（跑）：`run_headless` 跑毕 ⇒ 其 `pid` **已尽** ∧ 其 `profile` **已去** ∧
     **散落之列内无我之口**（引 TD 之只读器 `scripts/dev/查散落浏览器.py --json` 为常回归之据）。
  S3 账之可查（`_pm/_chrome_runs.jsonl`）：逐行六栏 `{ts,pid,port,profile,reaped,why}` ∧
     跑毕之行 `reaped: true` ∧ 其 `pid` ／ 口与我之跑一致（承「产出有痕有去处」）。
  S4 散落之判（纯逻辑 · ⛔ 触真机）：无头 ∧ 根 ⇒ 计；子 ／ 非无头 ⇒ ⛔ 计（同 TD 之器之判）。
  S5 引器为常（负控）：TD 之器在 ⇒ 走之；⛔ 在 ⇒ 落己之 PS（⛔ 杀 · 唯读）。
  S6 界：本器唯我席（`%TEMP%\cw*`）—— ⛔ 他径之 profile。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_stray_chrome_1914.py -q
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import socket
import time
import urllib.request

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = os.path.join(ROOT, "tests", "unit", "cw_chrome_reap.py")
TD_VIEWER = os.path.join(ROOT, "scripts", "dev", u"\u67e5\u6563\u843d\u6d4f\u89c8\u5668.py")


@pytest.fixture(scope="module")
def R():
    assert os.path.isfile(MOD), "器不在盘: %s" % MOD
    spec = importlib.util.spec_from_file_location("cw_chrome_reap_1914", MOD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _wait_cdp(port, timeout=20.0):
    u"""等 CDP 真应（⇒ 证其真起）；返 `/json/version` 之 `Browser` 辞。"""
    t0 = time.time()
    last = None
    while time.time() - t0 < timeout:
        try:
            raw = urllib.request.urlopen(
                "http://127.0.0.1:%d/json/version" % int(port), timeout=3).read()
            return json.loads(raw.decode("utf-8")).get("Browser")
        except Exception as exc:
            last = exc
            time.sleep(0.25)
    raise AssertionError(u"CDP %d ⛔ 应（%s）" % (int(port), last))


# 一 ⭐ S1 器之自证（源）：起者必收

@pytest.mark.unit
def test_S1_起者必收_源码自证(R):
    src = io.open(MOD, encoding="utf-8").read()
    assert "taskkill" in src, u"收之法：taskkill /T /F（收树）"
    assert "try:" in src and "finally:" in src, u"起者必收 ⇒ 必有 finally 之径"
    i = src.index("def run_headless(")
    body = src[i:]
    assert "finally:" in body, u"run_headless 之 finally ⛔ 丢"
    assert "_append(row)" in body, u"收之果须入账（⛔ 静默）"
    assert "shutil.rmtree" in body, u"收之三步含删 profile（⛔ 留残）"


# 二 ⭐ S3 账之器：只读 ／ 字段齐

@pytest.mark.unit
def test_S3_账之读_字段齐_R(R):
    rows = R.read_ledger()
    assert isinstance(rows, list)
    for r in rows:
        for k in ("ts", "pid", "port", "profile", "reaped", "why"):
            assert k in r, u"账之行须载六栏，缺 %s：%r" % (k, r)
    assert isinstance(R.LEDGER, str) and R.LEDGER.endswith("_chrome_runs.jsonl")


# 三 ⭐ S4 散落之判（纯逻辑）

@pytest.mark.unit
def test_S4_纯逻辑_无头根计_子与无头不(R):
    T = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "")
    root = {"ProcessId": 10, "ParentProcessId": 9, "Name": "chrome.exe",
            "CommandLine": "chrome.exe --headless=new --remote-debugging-port=9223 "
                           "--user-data-dir=" + T + "cw1807cdp_x"}
    child = {"ProcessId": 11, "ParentProcessId": 10, "Name": "chrome.exe",
             "CommandLine": "chrome.exe --headless=new --user-data-dir=" + T + "cw1807cdp_x"}
    plain = {"ProcessId": 12, "ParentProcessId": 9, "Name": "chrome.exe",
             "CommandLine": "chrome.exe --user-data-dir=" + T + "cw1_y"}
    got = R._strays_from_rows([root, child, plain])
    assert [x[0] for x in got] == [10], u"正控：无头 ∧ 根 ⇒ 计；反控：子 ／ 非无头 ⇒ ⛔ 计（得 %r）" % (got,)
    assert got[0][2] == 9223, u"口须取出（供「列内无我之口」之判）"
    assert got[0][1].endswith("cw1807cdp_x"), u"profile 须取出"


# 四 ⭐ S5 引器为常（负控：器⛔在 ⇒ 落己之 PS · ⛔ 触真机）

@pytest.mark.unit
def test_S5_引TD之器_器在走器_器不在落己(R, monkeypatch):
    assert os.path.isfile(TD_VIEWER), u"TD 之只读器须在盘（常回归之据）"
    # ① 器在 ⇒ 走器（stub 其 subprocess ⇒ ⛔ 真跑 PS）
    fake = json.dumps({"chrome_total": 5, "strays": [[71, u"CodexWindows\u7ebf", 9348, u"C:\\T\\cw1914x"]]})

    class _P(object):
        returncode = 0
        stdout = fake
        stderr = ""

    monkeypatch.setattr(R, "TD_VIEWER", TD_VIEWER)
    monkeypatch.setattr(R, "_ps_chrome", lambda: (_ for _ in ()).throw(AssertionError(u"器在 ⇒ ⛔ 该落己之 PS")))
    monkeypatch.setattr(R.subprocess, "run", lambda *a, **k: _P())
    assert R.strays() == [(71, u"C:\\T\\cw1914x", 9348)], u"器在 ⇒ 须据器之 `--json`"
    # ② 器不在 ⇒ 落己之 PS（stub 之 · 唯读 · ⛔ 杀）
    monkeypatch.setattr(R, "TD_VIEWER", os.path.join(ROOT, "_no_such_viewer.py"))
    monkeypatch.setattr(R, "_ps_chrome", lambda: [{
        "ProcessId": 22, "ParentProcessId": 1, "Name": "chrome.exe",
        "CommandLine": "chrome.exe --headless=new --remote-debugging-port=9227 "
                       "--user-data-dir=C:\\T\\cw1808bar_z"}])
    got = R.strays()
    assert got and got[0][0] == 22 and got[0][2] == 9227, u"器不在 ⇒ 须落己之 PS（得 %r）" % (got,)


# 五 ⭐ S6 界：唯我席之 profile

@pytest.mark.unit
def test_S6_唯我席_cw前缀(R):
    ds = R.my_profiles()
    for d in ds:
        assert os.path.basename(d).lower().startswith("cw"), u"唯 `%TEMP%\\cw*`（界）：%s" % d


# 六 ⭐ S2 ＋ S3 真起真收（一手 · 起 ⇒ 用 ⇒ 收 ⇒ 账）

@pytest.mark.integration
def test_S2S3_真起真收_列内无我之口_账落一行(R):
    if R.chrome_exe() is None:
        pytest.skip(u"chrome.exe ⛔ 在 ⇒ 环境不就绪（⛔ 假绿：须有真机方可证）")
    led0 = len(R.read_ledger())
    port = _free_port()
    pid = prof = None
    with R.run_headless(port=port, tag="1914t", wait_s=12.0, why="pm_1914 tooth") as p:
        pid, prof = p.pid, getattr(p, "cw_profile", None)
        browser = _wait_cdp(port)                      # ⇒ 证其真起（⛔ 唯「起了进程」）
        assert browser, u"CDP 须报 Browser 之辞"
        assert prof and os.path.isdir(prof), u"profile 须真在（起之证）"
        # 并证自清之径（reap）：就地收 ⇒ 同法 ∧ 入账
        assert R.reap(pid, prof, why="pm_1914 tooth(inside reap)") is True, u"reap 须收尽"
    # 跑毕（finally 之径）
    rows = R.read_ledger()
    assert len(rows) - led0 >= 1, u"收之果须入账（承「产出有痕」）"
    mine = [r for r in rows[led0:] if r.get("pid") == pid]
    assert mine, u"账内须有我之 pid 之行：%r" % (rows[led0:],)
    row = mine[-1]
    assert row["reaped"] is True, u"跑毕必收 ⇒ `reaped: true`（得 %r）" % row["reaped"]
    assert row.get("profile_gone") is True, u"收之三步含删 profile（⛔ 留残）"
    assert row["port"] == port and row["why"] == "pm_1914 tooth"
    # S2：列内无我之口
    assert not R._pid_alive(pid), u"pid %d 须已尽（⛔ 散落）" % pid
    assert not os.path.isdir(prof), u"profile 须已去"
    st = R.strays()
    hit = [x for x in st if x[0] == pid or x[2] == port]
    assert hit == [], u"散落之列内无我之口（得 %r ／ 列共 %d）" % (hit, len(st))


# 七 ⭐ S6b 界之负控：他径之 profile ⛔ 收（本器唯己域）

@pytest.mark.unit
def test_S6b_他径之profile_不在我席约(R):
    d = os.path.join(os.environ.get("USERPROFILE", "C:\\Users\\x"), ".clawsjoy")
    assert not os.path.basename(d).lower().startswith("cw"), u"界：⛔ 他径"
    for p in R.my_profiles():
        assert os.path.dirname(p) == R.TEMP, u"唯 `%TEMP%` 之下（界）：%s" % p