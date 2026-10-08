# -*- coding: utf-8 -*-
u'''齿：pm_1896 §三（壳层 r3）—— 桥之一处定形 ＋ 壳层自更新之策 ＋ 装期任务之形之接（归 9.0.11）。

以何形调用：
  python -X utf8 -B -m pytest tests/unit/test_shell_r3_1896.py -q

判据：
  S1 一处定形 · 纯策：`shell_update.js` ⛔ 引 electron ／ electron-updater ／ http ／ ⛔ 出网字面
     （`https://` ／ `fetch(` ／ `0.0.0.0` ／ XMLHttpRequest）· `main.js` 之 `require('./shell_update')`
     唯 1 处 · 且入壳之 `files`；
  S1b 桥名一处定形（CW `1887 §一.1` ／ pm_1896 §三）：`preload.js` 三名俱在 ∧ ⛔ 传态（唯唤面再拉）
     ∧ 二 IPC 名唯 `main.js` 出 ∧ 入口 id 一处（二处菜单共引）；
  S2 node 台架：策之自证 rc 0 ∧ 返形之键集**恒为定形**（成 5 键 ／ 败 7 键）∧ ⛔ 编数（pct null）
     ∧ `reduce` 为**纯**（⛔ 改入参）∧ `DEST` ⛔ 载本机径（⛔ `C:`）；
  S3 `tasks.nsh`：纯 ASCII ∧ ⛔ `Abort`（⛔ 阻装 —— pm_1896 §二.3⒞）∧ 调**装期之记器** ∧ ⛔ 调
     `install_win_pa`（一处定形）∧ 先清旧 rc（免陈旧之假绿）；
  S4 `package.json`：`version` ≡ 载荷之版（`core/lib/version.py`）∧ `nsis.include` ＝ `build/tasks.nsh`
     ∧ `publish` 唯 provider ／ url ／ channel（⛔ `publisherName` —— pm_1889 §一）；
  S5 `main.js` 之 rc 之析：⛔ 数字者 ⇒ null（照实 · ⛔ 编数）。
'''
from __future__ import annotations

import io
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHELL = ROOT / "shell"
SU = SHELL / "shell_update.js"
MAIN = SHELL / "main.js"
PRELOAD = SHELL / "preload.js"
PKG = SHELL / "package.json"
NSH = SHELL / "build" / "tasks.nsh"


def _read(p: Path) -> str:
    return io.open(str(p), encoding="utf-8").read()


def _node(src: str) -> dict:
    r = subprocess.run(["node", "-e", src], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=180, cwd=str(SHELL))
    assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
    return json.loads((r.stdout or "").strip().splitlines()[-1])


# ---------- S1 一处定形 · 纯策 ----------

def test_S1_policy_is_pure_and_referenced_once():
    t = _read(MAIN)
    assert t.count("require('./shell_update')") == 1, u"策须唯 1 处引（⛔ 二处定形）"
    d = _read(SU)
    for bad in ("require('electron')", "require('electron-updater')", "require('http')",
                "require('https')", "https://", "fetch(", "0.0.0.0", "XMLHttpRequest"):
        assert bad not in d, u"shell_update.js 须纯策（⛔ 得含 " + bad + "）"
    pkg = json.loads(_read(PKG))
    assert "shell_update.js" in pkg["build"]["files"], u"须入壳（否则 ⛔ 入 app.asar）"


def test_S1b_bridge_names_live_in_one_place():
    p = _read(PRELOAD)
    for n in ("openFeedbackDir", "shellUpdateState", "shellUpdateInstall", "onShellUpdate"):
        assert n in p, u"桥名须唯 preload.js 出：" + n
    m0 = _read(MAIN)
    for n in ("shellUpdateState", "shellUpdateInstall"):
        assert n not in m0, u"桥名须唯 preload.js 出（⛔ 二处定形）：" + n
    # ⚠ onShellUpdate 之名在 main 里只能作 onShellUpdateClick 之首（⛔ 作桥名）
    assert not re.search(r"onShellUpdate\b(?!Click)", m0), u"桥名 onShellUpdate ⛔ 得于 main.js 重立"
    assert "'pa:shell-update-state'" in _read(MAIN), u"IPC 之实须在 main.js"
    assert "'pa:shell-update-install'" in _read(MAIN), u"IPC 之实须在 main.js"
    assert "'pa:shell-update-ping'" in p, u"推之名须唯 preload 侧听"
    # ⭐ 一处定形之守：⛔ 传态（推之载荷唯「唤面再拉」⇒ 免得「拉与推不一」）
    assert "pa:shell-update-ping'" in _read(MAIN), u"壳须能发其 ping"
    assert "webContents.send('pa:shell-update-ping')" in _read(MAIN), u"ping ⛔ 载态（唯唤拉）"
    m = _read(MAIN)
    assert m.count("SHELL_UPD_ID") >= 3, u"二处菜单（托盘 ／ 应用菜单）须共引同一 id"
    assert m.count("function onShellUpdateClick()") == 1, u"入口之实唯 1 处"
    assert "shellUpdateLabel" in m, u"可点 ⇒ 须出人话之题"


# ---------- S2 node 台架 ----------

_HARNESS = r'''
const SU = require('./shell_update.js');
const out = {};
out.selftest_rc = SU.selfTest();
function keys(o){ return Object.keys(o).sort(); }
out.ok_keys  = keys(SU.reply(SU.blank('9.0.11')));
const bad = SU.reply(SU.reduce(SU.blank('9.0.11'), {t:'error', err:new Error('connect ECONNREFUSED 1.2.3.4:80')}));
out.bad_keys = keys(bad);
out.bad_code = bad.code; out.bad_phase = bad.phase;
out.p_null = SU.progressOf(null);
const s0 = SU.blank('9.0.1');
const snap = JSON.stringify(s0);
SU.reduce(s0, {t:'available', info:{version:'9.0.11'}});
out.reduce_pure = (JSON.stringify(s0) === snap);
out.dest = SU.DEST;
out.dest_local = (SU.DEST.indexOf('C:') >= 0);
out.phases = SU.PHASES.length; out.codes = SU.CODES.length;
console.log(JSON.stringify(out));
'''


def test_S2_policy_chineses_and_reverse_controls():
    u = _node(_HARNESS)
    assert u["selftest_rc"] == 0, u
    assert u["ok_keys"] == ["current", "latest", "ok", "phase", "progress"], u["ok_keys"]
    assert u["bad_keys"] == ["code", "current", "latest", "message", "ok", "phase", "progress"], u["bad_keys"]
    assert u["bad_code"] == "offline" and u["bad_phase"] == "failed", u
    assert u["p_null"] is None, u"⛔ 编数：progressOf(null) 须 null"
    assert u["reduce_pure"] is True, u"reduce 须纯（⛔ 改入参）"
    assert u["dest_local"] is False, u"DEST ⛔ 得载本机径（`C:`）"
    assert u["phases"] == 8 and u["codes"] == 7, u


# ---------- S3 tasks.nsh ----------

def test_S3_tasks_nsh_never_aborts_and_calls_the_recorder():
    raw = NSH.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf"), u"⛔ BOM"
    assert b"\r\n" not in raw, u"须 LF"
    t = raw.decode("utf-8")
    assert all(ord(c) < 128 for c in t), u"须纯 ASCII（makensis 之码页）"
    assert "!macro customInstall" in t and "!macroend" in t, u"须为 NSIS 之宏（include）"
    assert "Abort" not in t, u"⭐ ⛔ 阻装（任务败而阻壳 ＝ 更坏之态 · pm_1896 §二.3⒞）"
    code = "\n".join(l for l in t.splitlines() if not l.strip().startswith(";"))  # ⚠ 去其释（其文可论证）
    assert "install_tasks_silent.py" in code, u"须调装期之记器"
    assert "install_win_pa.py" not in code, u"任务之逻辑须唯 install_win_pa 一处定形（⛔ 于此另调）"
    assert "nsExec::ExecToStack" in t, u"须静默（⛔ ExecWait —— 会现窗）"
    assert code.index("Delete") < code.index("ExecToStack"), u"先清旧 rc（免陈旧之假绿）"
    assert "install_tasks.rc" in t and "rc=$0" in t, u"rc 唯装器侧落（一源）"


# ---------- S4 package.json ----------

def test_S4_package_version_and_nsis_include():
    pkg = json.loads(_read(PKG))
    ver = re.search(r'^__version__\s*=\s*u?["\']([^"\']+)["\']',
                    _read(ROOT / "core" / "lib" / "version.py"), re.M)
    assert ver, u"未见载荷之版（core/lib/version.py）"
    assert pkg["version"] == ver.group(1), (pkg["version"], ver.group(1))
    assert pkg["build"]["nsis"]["include"] == "build/tasks.nsh", u"include 一处定形"
    pub = pkg["build"]["publish"][0]
    assert pub["provider"] == "generic" and pub["channel"] == "internal", pub
    assert "publisherName" not in json.dumps(pkg), u"⛔ 加 publisherName（＝自堵 · pm_1889 §一）"
    assert pkg["build"]["nsis"]["artifactName"].startswith("ClawsJoyPA-Setup-"), u"件名照 artifactName"


# ---------- S5 rc 之析 ----------

def test_S5_rc_parse_is_honest():
    m = _read(MAIN)
    assert re.search(r"match\(/rc=\(\\S\*\)/\)", m), u"rc 之析须纳**非数字**（照实）"
    assert "/^-?\\d+$/" in m, u"⛔ 数字者须判 null（⛔ 编数）"
    assert "install_tasks.log" in m, u"败之明书须载「去处」"
