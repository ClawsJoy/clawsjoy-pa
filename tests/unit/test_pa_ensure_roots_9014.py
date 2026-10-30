# -*- coding: utf-8 -*-
r"""PA 9.0.14 P0-2 之齿 —— **安装期三根 junction**（ensure_roots.py ／ tasks.nsh ／ installer_post.py）。

病（一手 · docs/71）：9.0.13 装后 gateway 仍向装根写 payload\logs\engine.log ／ payload\data\*。
修（本批）：安装器建三 junction：payload\{logs,data,vec} -> %LOCALAPPDATA%\ClawsJoyPA\{logs,data,vec}；
  装根保持只读；卸载只解 junction（⛔ 删目标）。

判据：
  R1 正控：plan 三根之 link 在装根、target 在 base；default_base 认 LOCALAPPDATA ／ USERPROFILE。
  R2 正控：classify = missing ／ dir ／ file ／ junction（立后）。
  R3 正控：ensure 立三 junction（⛔ 管理员 · mklink /J）且 verify PASS。
  R4 正控：ensure 幂等（二次皆 PASS · 现有 junction 报 no-op）。
  R5 正控：旧「真目录」⇒ 内容迁入 target ∧ 原径变 junction。
  R6 正控：迁移同名冲突 ⇒ 两侧皆留（target 原件不动；源件改名 .from_install_*）。
  R7 正控：错指 junction ⇒ 只解再立（旧 target 之内容 ⛔ 动）。
  R8 正控：remove 只解 junction；target 内件 ⛔ 删。
  R9 正控：remove 遇真目录 ⇒ ⛔ 动（保数据）。
  R10 反控：verify 缺 link ／ 错指 ⇒ FAIL；ensure 后 ⇒ PASS。
  R11 正控：日志落 <base>\logs\ensure_roots.log ∧ 含 ensure PASS。
  R12 正控：dry-run ⛔ 动盘（只出 DRY 行）。
  R13 正控：CLI ensure ／ verify ／ remove 之 rc（0 ／ 2）。
  R14 反控：装根内同名「非目录之件」⇒ FAIL 且 ⛔ 删该件。
  S1 源齿：tasks.nsh 有 customInstall ＋ customUnInstall ∧ 调 ensure_roots.py ∧ 纯 ASCII ∧ ⛔ Abort；
     package.json 之 nsis.include ＝ build/tasks.nsh。
  S2 源齿：installer_post.py 有 ensure_writable_roots ∧ 调 ER.ensure ∧ 在 render_and_maybe_apply 内接。

以何形调用：
  python -X utf8 -B -m pytest tests/unit/test_pa_ensure_roots_9014.py -q
⛔ 动真实 %LOCALAPPDATA%（皆以 --base/env 指临时目录）；⛔ 安装/注册。
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WPA = ROOT / "scripts" / "win_pa"
sys.path.insert(0, str(WPA))

import ensure_roots as ER  # noqa: E402

WIN = (os.name == "nt")
BS = chr(92)


@pytest.fixture
def roots(tmp_path):
    r = tmp_path / "payload"
    b = tmp_path / "localappdata" / "ClawsJoyPA"
    r.mkdir(parents=True, exist_ok=True)
    b.mkdir(parents=True, exist_ok=True)
    yield str(r), str(b)
    # 清 junction（⛔ 动 target 之内容）
    try:
        ER.remove(root=str(r), base=str(b))
    except Exception:
        pass


def _ensure(root, base, dry=False):
    return ER.ensure(root=root, base=base, log_path=os.path.join(base, "logs", ER.LOG_NAME), dry_run=dry)


def _verify(root, base):
    return ER.verify(root=root, base=base, log_path=os.path.join(base, "logs", ER.LOG_NAME))


# ---------------------------------------------------------------- R1 plan ／ base
def test_R1_plan_links_under_root_targets_under_base(roots):
    root, base = roots
    rows = ER.plan(root=root, base=base)
    assert [x["name"] for x in rows] == ["logs", "data", "vec"]
    for it in rows:
        assert os.path.dirname(it["link"]) == os.path.abspath(root), it
        assert os.path.dirname(it["target"]) == os.path.abspath(base), it


def test_R1b_default_base_follows_localappdata(tmp_path):
    env = {"LOCALAPPDATA": str(tmp_path / "LA")}
    assert ER.default_base(env) == os.path.join(str(tmp_path / "LA"), "ClawsJoyPA")
    env2 = {"USERPROFILE": str(tmp_path / "UP")}
    assert ER.default_base(env2) == os.path.join(str(tmp_path / "UP"), "AppData", "Local", "ClawsJoyPA")


# ---------------------------------------------------------------- R2 classify
def test_R2_classify_missing_dir_file_junction(roots):
    root, base = roots
    assert ER.classify(os.path.join(root, "logs")) == "missing"
    os.makedirs(os.path.join(root, "data"))
    assert ER.classify(os.path.join(root, "data")) == "dir"
    io_p = os.path.join(root, "vec")
    with open(io_p, "w", encoding="utf-8") as fh:
        fh.write("x")
    assert ER.classify(io_p) == "file"


# ---------------------------------------------------------------- R3 ensure
@pytest.mark.skipif(not WIN, reason="junction 唯 Windows")
def test_R3_ensure_three_junctions_and_verify_pass(roots):
    root, base = roots
    ok, rows, _ = _ensure(root, base)
    assert ok, rows
    for name in ("logs", "data", "vec"):
        link = os.path.join(root, name)
        target = os.path.join(base, name)
        assert ER.classify(link) == "junction", (name, rows)
        assert ER.junction_target(link) == os.path.abspath(target), (name, ER.junction_target(link))
        assert os.path.isdir(target)
    vok, vrows, _ = _verify(root, base)
    assert vok, vrows


# ---------------------------------------------------------------- R4 idempotent
@pytest.mark.skipif(not WIN, reason="junction 唯 Windows")
def test_R4_ensure_idempotent(roots):
    root, base = roots
    ok1, rows1, _ = _ensure(root, base)
    assert ok1, rows1
    ok2, rows2, _ = _ensure(root, base)
    assert ok2, rows2
    assert all("[PASS]" in r for r in rows2), rows2


# ---------------------------------------------------------------- R5 migrate real dir
@pytest.mark.skipif(not WIN, reason="junction 唯 Windows")
def test_R5_migrate_real_dir_contents(roots):
    root, base = roots
    os.makedirs(os.path.join(root, "logs"))
    with open(os.path.join(root, "logs", "engine.log"), "w", encoding="utf-8") as fh:
        fh.write("legacy")
    ok, rows, _ = _ensure(root, base)
    assert ok, rows
    tgt = os.path.join(base, "logs", "engine.log")
    assert os.path.isfile(tgt), rows
    with open(tgt, encoding="utf-8") as fh:
        assert fh.read() == "legacy"
    assert ER.classify(os.path.join(root, "logs")) == "junction"


# ---------------------------------------------------------------- R6 conflicts kept
@pytest.mark.skipif(not WIN, reason="junction 唯 Windows")
def test_R6_migrate_conflict_keeps_both_sides(roots):
    root, base = roots
    os.makedirs(os.path.join(root, "logs"))
    os.makedirs(os.path.join(base, "logs"))
    with open(os.path.join(root, "logs", "engine.log"), "w", encoding="utf-8") as fh:
        fh.write("old")
    with open(os.path.join(base, "logs", "engine.log"), "w", encoding="utf-8") as fh:
        fh.write("new")
    ok, rows, _ = _ensure(root, base)
    assert ok, rows
    with open(os.path.join(base, "logs", "engine.log"), encoding="utf-8") as fh:
        assert fh.read() == "new"
    alt = [n for n in os.listdir(os.path.join(base, "logs"))
           if n.startswith("engine.log.from_install_")]
    assert alt, os.listdir(os.path.join(base, "logs"))


# ---------------------------------------------------------------- R7 wrong junction
@pytest.mark.skipif(not WIN, reason="junction 唯 Windows")
def test_R7_wrong_junction_repointed_target_untouched(roots, tmp_path):
    root, base = roots
    other = tmp_path / "other_logs"
    other.mkdir()
    (other / "keep.txt").write_text("keep", encoding="utf-8")
    ok, why = ER.make_junction(os.path.join(root, "logs"), str(other))
    assert ok, why
    ok, rows, _ = _ensure(root, base)
    assert ok, rows
    assert ER.junction_target(os.path.join(root, "logs")) == os.path.abspath(os.path.join(base, "logs"))
    assert (other / "keep.txt").is_file()


# ---------------------------------------------------------------- R8 remove keeps target
@pytest.mark.skipif(not WIN, reason="junction 唯 Windows")
def test_R8_remove_unlinks_only(roots):
    root, base = roots
    ok, rows, _ = _ensure(root, base)
    assert ok, rows
    with open(os.path.join(base, "data", "keep.json"), "w", encoding="utf-8") as fh:
        fh.write("{}")
    ok, rows, _ = ER.remove(root=root, base=base, log_path=os.path.join(base, "logs", ER.LOG_NAME))
    assert ok, rows
    for name in ("logs", "data", "vec"):
        assert not os.path.lexists(os.path.join(root, name)), name
    assert os.path.isfile(os.path.join(base, "data", "keep.json"))


# ---------------------------------------------------------------- R9 remove skips real dir
def test_R9_remove_skips_real_dir(roots):
    root, base = roots
    os.makedirs(os.path.join(root, "data"))
    with open(os.path.join(root, "data", "x.json"), "w", encoding="utf-8") as fh:
        fh.write("{}")
    ok, rows, _ = ER.remove(root=root, base=base, log_path=os.path.join(base, "logs", ER.LOG_NAME))
    assert ok, rows
    assert os.path.isfile(os.path.join(root, "data", "x.json"))


# ---------------------------------------------------------------- R10 verify fail
@pytest.mark.skipif(not WIN, reason="junction 唯 Windows")
def test_R10_verify_detects_missing_and_wrong(roots):
    root, base = roots
    vok, vrows, _ = _verify(root, base)
    assert not vok and any("[FAIL]" in r for r in vrows), vrows
    ok, rows, _ = _ensure(root, base)
    assert ok, rows
    os.rmdir(os.path.join(root, "vec"))                 # 解一个 junction
    vok, vrows, _ = _verify(root, base)
    assert not vok and any("[FAIL]" in r for r in vrows), vrows


# ---------------------------------------------------------------- R11 log
@pytest.mark.skipif(not WIN, reason="junction 唯 Windows")
def test_R11_log_written(roots):
    root, base = roots
    ok, rows, lp = _ensure(root, base)
    assert ok, rows
    assert os.path.isfile(lp), lp
    with open(lp, encoding="utf-8") as fh:
        txt = fh.read()
    assert "ensure PASS" in txt


# ---------------------------------------------------------------- R12 dry-run
def test_R12_dry_run_no_changes(roots):
    root, base = roots
    ok, rows, _ = _ensure(root, base, dry=True)
    assert ok, rows
    assert all("[DRY]" in r for r in rows), rows
    for name in ("logs", "data", "vec"):
        assert not os.path.lexists(os.path.join(root, name)), name


# ---------------------------------------------------------------- R13 CLI
@pytest.mark.skipif(not WIN, reason="junction 唯 Windows")
def test_R13_cli_rc(roots, capsys):
    root, base = roots
    lp = os.path.join(base, "logs", ER.LOG_NAME)
    assert ER.main(["ensure", "--root", root, "--base", base, "--log-file", lp]) == 0
    assert ER.main(["verify", "--root", root, "--base", base, "--log-file", lp]) == 0
    assert ER.main(["remove", "--root", root, "--base", base, "--log-file", lp]) == 0
    assert ER.main(["verify", "--root", root, "--base", base, "--log-file", lp]) == 2


# ---------------------------------------------------------------- R14 non-dir file
def test_R14_non_dir_file_fails_and_kept(roots):
    root, base = roots
    with open(os.path.join(root, "logs"), "w", encoding="utf-8") as fh:
        fh.write("not-a-dir")
    ok, rows, _ = _ensure(root, base)
    assert not ok, rows
    assert any("[FAIL]" in r for r in rows), rows
    assert os.path.isfile(os.path.join(root, "logs"))


# ---------------------------------------------------------------- S1 NSIS
def test_S1_tasks_nsh_has_junction_hooks():
    nsh = (ROOT / "shell" / "build" / "tasks.nsh").read_bytes()
    assert not nsh.startswith(b"\xef\xbb\xbf"), "⛔ BOM"
    assert b"\r\n" not in nsh, "须 LF"
    t = nsh.decode("utf-8")
    assert all(ord(c) < 128 for c in t), "须纯 ASCII（makensis 之码页）"
    assert "!macro customInstall" in t and "!macro customUnInstall" in t
    assert "ensure_roots.py" in t and "--root" in t and "ClawsJoyPA" in t
    assert "Abort" not in t, "⛔ 阻安装"
    pkg = json.loads((ROOT / "shell" / "package.json").read_text(encoding="utf-8"))
    assert pkg["build"]["nsis"]["include"] == "build/tasks.nsh"
    # 版本唯源 ＝ core/lib/version.py（⛔ 本齿写版本字面 —— 免每次 bump 皆红）
    m = re.search(r'^__version__\s*=\s*u?["\']([^"\']+)["\']',
                  (ROOT / "core" / "lib" / "version.py").read_text(encoding="utf-8"), re.M)
    assert m, "core/lib/version.py 未见 __version__"
    assert pkg["version"] == m.group(1), (pkg["version"], m.group(1))


# ---------------------------------------------------------------- S2 installer_post
def test_S2_installer_post_calls_ensure_roots():
    src = (ROOT / "scripts" / "win_pa" / "installer_post.py").read_text(encoding="utf-8")
    assert "def ensure_writable_roots(" in src
    assert "ER.ensure(" in src
    seg = src[src.index("def render_and_maybe_apply("):]
    assert "ensure_writable_roots(dest, dry)" in seg, "render_and_maybe_apply 须接"
