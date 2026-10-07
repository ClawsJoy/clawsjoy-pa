# -*- coding: utf-8 -*-
u"""pm_1770 §二.1⒟ 之齿：`make_update.py` 之**出件根**与**闸**（仓外 ＋ 版号戳 ＋ 已存非空 ⇒ 拒）。

以何形调用：
  python -X utf8 -B -m pytest tests/unit/test_win_pa_make_update_out_1770.py -q

判据（正控 3 ＋ 反控 3）：
  ⒈ **正控**：`default_out(root, v)` ⇒ **仓外**（⛔ 在 `root` 之下 —— 仓内之出件树 ⇒ daemon 之患，
     承 pm_1767 §一）∧ **绝对径** ∧ 末段 ≡ 版号（一批一版号）。
  ⒉ **正控**：`PA_UPDATE_OUT` ⇒ 覆出件之根（承「源须可配」）。
  ⒊ **正控**：干跑（缺省 `--out`）⇒ rc 0 ∧ 印「缺省之径」∧ **⛔ 落盘**。
  ⒋ **反控**：出件目录**已存且非空** ⇒ rc 2 ∧ 报「已存且非空」（**干跑亦拒** —— ⛔ 二形）。
  ⒌ **反控**：同上 ＋ `--force` ⇒ rc 0（明书之覆）。
  ⒍ **反控**：`--go` 真造 ⇒ 落盘；再 `--go`（无 `--force`）⇒ **拒**（治 pm_1760 §二 之坑）。
"""
import importlib
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "win_pa" / "make_update.py"
BASE = "9584d4f"          # 9.0.4 所交付之树（其 version.py ⇒ base_version 自取 9.0.4）
VER = "9.0.6"


def _mu():
    if str(SCRIPT.parent) not in sys.path:
        sys.path.insert(0, str(SCRIPT.parent))
    return importlib.import_module("make_update")


def _run(args, out_root=None):
    env = dict(os.environ)
    if out_root is not None:
        env["PA_UPDATE_OUT"] = str(out_root)
    return subprocess.run([sys.executable, "-X", "utf8", "-B", str(SCRIPT)] + list(args),
                          capture_output=True, cwd=str(ROOT), timeout=600, env=env)


def _tail(r):
    return (r.stdout or b"").decode("utf-8", "replace")[-900:]


def test_正控一_缺省之出件在仓外且加版号戳():
    mu = _mu()
    out = mu.default_out(str(ROOT), VER)
    assert os.path.isabs(out), out
    assert not os.path.abspath(out).startswith(os.path.abspath(str(ROOT)) + os.sep), \
        u"缺省之出件 ⇒ 须在**仓外**（仓内 ⇒ daemon 之患 · 承 pm_1767 §一）：%s" % out
    assert os.path.basename(out) == VER, out


def test_正控二_env可覆出件之根(tmp_path, monkeypatch):
    mu = _mu()
    monkeypatch.setenv("PA_UPDATE_OUT", str(tmp_path / "o"))
    assert mu.out_root(str(ROOT)) == os.path.abspath(str(tmp_path / "o"))
    assert mu.default_out(str(ROOT), VER) == os.path.join(os.path.abspath(str(tmp_path / "o")), VER)


def test_正控三_干跑不落盘(tmp_path):
    r = _run(["--base", BASE, "--version", VER], out_root=tmp_path / "o")
    assert r.returncode == 0, _tail(r)
    assert u"缺省之径" in _tail(r), _tail(r)
    assert not (tmp_path / "o").exists(), u"干跑 ⛔ 得落盘"


def test_反控一_已存且非空则拒_干跑亦拒(tmp_path):
    d = tmp_path / "o" / VER
    d.mkdir(parents=True)
    (d / "update_manifest.json").write_text(u"{}", encoding="utf-8")
    r = _run(["--base", BASE, "--version", VER], out_root=tmp_path / "o")
    assert r.returncode == 2, _tail(r)
    assert u"已存且非空" in _tail(r), _tail(r)


def test_反控二_force许明书之覆(tmp_path):
    d = tmp_path / "o" / VER
    d.mkdir(parents=True)
    (d / "old.txt").write_text(u"x", encoding="utf-8")
    r = _run(["--base", BASE, "--version", VER, "--force"], out_root=tmp_path / "o")
    assert r.returncode == 0, _tail(r)


def test_反控三_真造后再造无force则拒(tmp_path):
    o = tmp_path / "o"
    r1 = _run(["--base", BASE, "--version", VER, "--go"], out_root=o)
    assert r1.returncode == 0, _tail(r1)
    assert (o / VER / "update_manifest.json").is_file(), u"`--go` 须落盘"
    r2 = _run(["--base", BASE, "--version", VER, "--go"], out_root=o)
    assert r2.returncode == 2, u"再 `--go`（无 `--force`）⇒ 须拒\n" + _tail(r2)