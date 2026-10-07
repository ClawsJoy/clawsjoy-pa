# -*- coding: utf-8 -*-
r"""pm_1688 之齿 —— `make_update.py` 取件须「检出之形」（⛔ 裸 blob）。

以何形调用：
  python -X utf8 -B -m pytest tests/unit/test_win_pa_make_update_blob_1688.py -q

判据（承 pm_1688：「凡载荷之件 ⇒ 其印须 ≡ 检出之形 · 一处定形」）：
  B1 正控：`blob()` 取 `*.cmd`（`.gitattributes` 钉 `eol=crlf`）⇒ **CRLF** ∧ 逐字节 ≡ **盘上之件**
     （＝ 装器 `git archive` 之形）。
  B2 反控（昔之病）：裸 `git show` ⇒ **LF**（`4260 B`）≠ 检出之形 ⇒ 修前之「同物异印」可复现
     （若回归 ⇒ B1 红）。
  B3 界：他件（`*.py` ／ `pyproject.toml`）⇒ `blob()` 逐字节 ≡ 裸 blob（修唯动 eol 之钉之件 · ⛔ 滥改）。
  B4 端到端：真跑 `make_update.py --json`（干跑 · ⛔ 落盘）⇒ 清单里凡 `*.cmd` 之件 ⇒
     `sha256` ／ `size` ≡ 检出之形（＝ 盘上之件）—— 「三处一数」（装器 ／ 增量 ／ 检出）。
     ＋ **`del` 之形**（pm_1757 §三.1：删件之批 ⇒ 其验须含「重出包之齿」）：随 9.0.5 废
     `pa-update.cmd` ⇒ 本基至 HEAD 必含其一 `del` 件 ⇒ 空印 · 零尺（校器之约）。
  ⚠ 标本之换（9.0.5 · pm_1757 §一.2）：`pa-update.cmd` 既废 ⇒ 存活之 `*.cmd` 标本改用
     `install_pa.cmd`（同钉 `eol=crlf`）；`BASE` 随之为 9.0.4 所交付之树 —— 否则「加而复删」
     于二 rev 相抵 ⇒ 增量里 ⛔ 见该件 · 此齿空转。
"""
from __future__ import annotations

import hashlib
import importlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "win_pa" / "make_update.py"
CMD = ROOT / "scripts" / "win_pa" / "install_pa.cmd"   # 存活之 `*.cmd`（标本）
CMD_DEL = "scripts/win_pa/pa-update.cmd"               # 随 9.0.5 废（`del` 之标本）
BASE = "9584d4f"          # 9.0.4 所交付之树（含 pa-update.cmd ⇒ 增量必有 `del` 一件）


def _git(*args):
    r = subprocess.run(["git", "-C", str(ROOT)] + list(args), capture_output=True)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")
    return r.stdout


def _mu():
    if str(SCRIPT.parent) not in sys.path:
        sys.path.insert(0, str(SCRIPT.parent))
    return importlib.import_module("make_update")


# ---------- B1 正控 ----------

def test_B1_blob_cmd_is_checkout_shape():
    rc, raw = _mu().blob(str(ROOT), "HEAD", "scripts/win_pa/install_pa.cmd")
    assert rc == 0, u"取件败"
    disk = CMD.read_bytes()
    assert raw.count(b"\r\n") == raw.count(b"\n") == disk.count(b"\r\n") > 30, u"须 CRLF（cmd 之安）"
    assert raw == disk, u"增量之件须 ≡ 检出之形（盘上）"
    assert hashlib.sha256(raw).hexdigest() == hashlib.sha256(disk).hexdigest(), u"印须 ≡"


# ---------- B2 反控（昔之病） ----------

def test_B2_raw_blob_differs_reproduce_former_bug():
    raw = _git("show", "HEAD:scripts/win_pa/install_pa.cmd")
    disk = CMD.read_bytes()
    assert raw.count(b"\r\n") == 0, u"仓内为 LF（eol 钉之效）"
    assert len(raw) == len(disk) - raw.count(b"\n"), u"差 ≡ 行数（LF ⇒ CRLF 之增）"
    assert raw != disk, u"裸 blob ⇒ 昔之「同物异印」"


# ---------- B3 界 ----------

def test_B3_other_files_unchanged():
    mu = _mu()
    for p in ("core/lib/version.py", "pyproject.toml", "scripts/win_pa/pa_update.py"):
        rc, flt = mu.blob(str(ROOT), "HEAD", p)
        assert rc == 0, u"取件败：%s" % p
        assert flt == _git("show", "HEAD:" + p), u"唯 eol 之钉之件可变：%s" % p


# ---------- B4 端到端 ----------

def test_B4_manifest_entries_are_checkout_shape():
    r = subprocess.run([sys.executable, "-X", "utf8", "-B", str(SCRIPT),
                        "--base", BASE, "--new", "HEAD",
                        "--version", "9.0.5", "--base-version", "9.0.4", "--json"],
                       capture_output=True, cwd=str(ROOT), timeout=300)
    out = r.stdout.decode("utf-8", "replace")
    assert r.returncode == 0, out[-800:]
    man = json.loads(out[out.index("{"):out.rindex("}") + 1])
    cmd_all = [e for e in man["files"] if e["path"].endswith(".cmd")]
    assert cmd_all, u"本基至 HEAD 之增量须含 `*.cmd`（否则此齿空转）"
    live = [e for e in cmd_all if e["mode"] != "del"]
    dead = [e for e in cmd_all if e["mode"] == "del"]
    for e in live:                                    # 存活之件 ⇒ 尺与印 ≡ 检出之形（盘上）
        disk = (ROOT / e["path"]).read_bytes()
        assert e["size"] == len(disk), u"清单之尺须 ≡ 检出之形：%s" % e["path"]
        assert e["sha256"] == hashlib.sha256(disk).hexdigest(), u"清单之印须 ≡ 检出之形：%s" % e["path"]
    assert CMD_DEL in [e["path"] for e in dead], u"9.0.5 之增量须含 `pa-update.cmd` 之 `del`（废之凭）"
    for e in dead:                                    # 已废之件 ⇒ 空印 · 零尺（`update_manifest.MODES` 之约）
        assert e["sha256"] == "" and e["size"] == 0, u"`del` 须空印零尺：%s" % e["path"]
