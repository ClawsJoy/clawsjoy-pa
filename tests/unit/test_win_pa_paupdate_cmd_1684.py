# -*- coding: utf-8 -*-
r"""pm_1684 §三 之齿 —— bootstrap `scripts/win_pa/pa-update.cmd`（按手之更新路）。

以何形调用：
  python -X utf8 -B -m pytest tests/unit/test_win_pa_paupdate_cmd_1684.py -q

判据：
  C1 形之钉：**全 ASCII**（0 个非 ASCII 字节 —— 承 pm_1578 §2.2）· ⛔ BOM · CRLF · 批首存旧码页 ＋ `chcp 65001`。
  C2 取装根之**二形皆认**（壳之 `resources/payload` ／ 旧包之 `%LOCALAPPDATA%\ClawsJoyPA`）＋ `PA_ROOT` 之覆。
  C3 调器之形（**唯一条** python 之调）：`runtime\python.exe -X utf8 -B scripts\win_pa\pa_update.py --root <root> --go --json`
     —— 承「一处定形」（⛔ 二处各拼）。
  C4 真跑之正反控（沙箱之桩根 ／ 唯 `runtime\` 为 junction ⇒ 真 `python.exe`）：成 ⇒ rc 0 ＋ 日志有痕 ＋ 有时长；
     败 ⇒ rc 之传（⛔ 吞）＋ 人话 ＋ 去处。＋ 取不得根 ⇒ rc 3 ＋ 人话（⛔ 静默）。
"""
from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CMD = ROOT / "scripts" / "win_pa" / "pa-update.cmd"
RUNTIME = ROOT / "dist" / "pa_shell" / "payload" / "runtime"


def _raw() -> bytes:
    return CMD.read_bytes()


def _run(args, env=None, cwd=None, timeout=300):
    e = dict(os.environ)
    e["PA_ROOT"] = ""
    for k, v in (env or {}).items():
        e[k] = v
    return subprocess.run(args, capture_output=True, timeout=timeout, env=e, cwd=cwd)


# ---------- C1 形之钉 ----------

def test_C1_ascii_only_no_bom_crlf_and_codepage():
    b = _raw()
    non = [i for i, x in enumerate(b) if x > 127]
    assert non == [], u"须全 ASCII（首个非 ASCII 在 %s）：%r" % (non[:1], b[non[0] - 20:non[0] + 20] if non else b"")
    assert not b.startswith(b"\xef\xbb\xbf"), u"⛔ 得带 BOM"
    assert b.count(b"\r\n") == b.count(b"\n"), u"须 CRLF（cmd 之安）"
    t = b.decode("ascii")
    assert t.count("\n") > 30, u"须为真件"
    i_cp = t.find("chcp 65001")
    assert i_cp > 0, u"须批首 chcp 65001"
    assert t[:i_cp].count("for /f") == 1, u"须先存旧码页（承 install_pa.cmd 之形）"
    assert "_CJPA_CP" in t, u"须存旧码页"


# ---------- C2 取根之三路 ----------

def test_C2_root_lookup_two_shapes_and_override():
    t = _raw().decode("ascii")
    assert (u'if not "%PA_ROOT%"=="" if exist "%PA_ROOT%\\scripts\\win_pa\\pa_update.py"' in t), u"须认 PA_ROOT"
    assert "%LOCALAPPDATA%\\Programs\\ClawsJoyPA\\resources\\payload\\scripts\\win_pa\\pa_update.py" in t, u"须认壳之形（A）"
    assert "%LOCALAPPDATA%\\ClawsJoyPA\\scripts\\win_pa\\pa_update.py" in t, u"须认旧包之形（B）"
    assert ":noroot" in t and "set \"RC=3\"" in t, u"取不得 ⇒ rc 3 ＋ 人话"
    assert ":nopy" in t, u"无 runtime ⇒ 人话（⛔ 静默）"


# ---------- C3 调器之形 ----------

def test_C3_tool_shape_single_place():
    t = _raw().decode("ascii")
    calls = re.findall(r'(?m)^"%PY%" ([^\r\n]*)', t)
    tool = [c for c in calls if "--json" in c]
    assert len(tool) == 1, u"调器须唯一条（今 %d）：%r" % (len(tool), calls)
    assert "--root \"%ROOT%\" --go --json" in tool[0], tool[0]
    assert "-X utf8 -B" in tool[0], tool[0]
    assert t.count("pa_update.py") >= 2, u"器之名须明书（注释 ＋ 调）"
    assert u'set "UPD=%ROOT%\\scripts\\win_pa\\pa_update.py"' in t, u"器之路须由 UPD 一处出"
    assert t.count("--go --json") == 2, u"器之参表：一在明书 ／ 一在调（⛔ 三处）"
    clock = [c for c in calls if "import sys,time" in c]
    assert len(clock) == 2, u"计时器须二（起 ／ 毕）：%r" % (calls,)


# ---------- C4 真跑之正反控 ----------

def _mk_stub_root(base: Path, rc: int, marker: str) -> Path:
    u"""桩根：`scripts\\win_pa\\pa_update.py` ＝ 桩；`runtime\\` ＝ junction ⇒ **真** python.exe。"""
    root = base / ("stub" + str(rc))
    (root / "scripts" / "win_pa").mkdir(parents=True)
    src = (u"# -*- coding: utf-8 -*-\n"
           u"import sys\n"
           u"sys.stdout.reconfigure(encoding=u'utf-8')\n"
           u"print(u'" + marker + u"')\n"
           u"print(u'argv=' + u'|'.join(sys.argv[1:]))\n"
           u"sys.exit(" + str(rc) + u")\n")
    (root / "scripts" / "win_pa" / "pa_update.py").write_bytes(src.encode("utf-8"))
    r = subprocess.run(["cmd", "/c", "mklink", "/J", str(root / "runtime"), str(RUNTIME)],
                       capture_output=True, timeout=60)
    assert (root / "runtime" / "python.exe").is_file(), (r.returncode, r.stdout, r.stderr)
    return root


@pytest.mark.skipif(not (RUNTIME / "python.exe").is_file(), reason=u"无载荷之 runtime")
def test_C4_sandbox_stub_positive_and_negative(tmp_path):
    ok = _mk_stub_root(tmp_path, 0, u"[PA-STUB] 成")
    bad = _mk_stub_root(tmp_path, 2, u"[PA-STUB] 败")
    la = tmp_path / "LA"

    r1 = _run(["cmd", "/c", str(CMD), "<", "NUL"], {"PA_ROOT": str(ok), "LOCALAPPDATA": str(la)})
    o1 = (r1.stdout or b"").decode("utf-8", "replace")
    assert r1.returncode == 0, (r1.returncode, o1, (r1.stderr or b"").decode("utf-8", "replace"))
    assert u"[PA-STUB] 成" in o1, o1
    assert u"[PA] elapsed" in o1 and u"exit=0" in o1, o1
    log = la / "ClawsJoyPA" / "pa-update.log"
    assert log.is_file(), u"须留日志（去处）"
    assert u"[PA-STUB] 成" in io.open(str(log), encoding="utf-8").read(), u"日志之 UTF-8 须真"

    r2 = _run(["cmd", "/c", str(CMD), "<", "NUL"], {"PA_ROOT": str(bad), "LOCALAPPDATA": str(la)})
    o2 = (r2.stdout or b"").decode("utf-8", "replace")
    assert r2.returncode == 2, u"rc 须传（⛔ 吞成 0）：%r" % (r2.returncode,)
    assert u"exit=2" in o2 and u"[FAIL] NOT updated" in o2, o2
    assert u"pa-update.log" in o2, u"须明书去处"

    r3 = _run(["cmd", "/c", str(CMD), "<", "NUL"],
              {"PA_ROOT": str(tmp_path / "nope"), "LOCALAPPDATA": str(tmp_path / "LA2")})
    o3 = (r3.stdout or b"").decode("utf-8", "replace")
    assert r3.returncode == 3, u"取不得根 ⇒ rc 3：%r" % (r3.returncode,)
    assert u"[FAIL] no installed payload found" in o3 and u"PA_ROOT" in o3, o3
    assert u"ClawsJoy PA" in o3, o3