# -*- coding: utf-8 -*-
u"""一键安装器之测（承 pm_1384 §三.4 之五约 · M1 余件之四）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_win_pa_install.py -q

判据（逐条对 pm_1384 §三.4 之判成）：
  ⒜ 干跑（缺省）⇒ rc 0 ∧ 印「将动」∧ ⛔ 动盘
  ⒝ 幂等：已在 ⇒ no-op（⛔ 重复动作）
  ⒞ 前置闸显形：Python 版 ／ 依赖 ／ 端口 ／ data\\ 可写 ／ 显存 ／ ollama 六栏皆在 ∧ 逐栏有因
  ⒟ ⛔ 动 data/** 之文件（唯立目录）
  ⒠ 反控：前置 ⛔ 足 ⇒ rc 2 ∧ 报「⛔ 装」∧ ⛔ 动盘（PA_INSTALL_FORCE_FAIL 之钩）
⛔ 起停：本测唯干跑 ／ --json ／ --self-test（⛔ 起服 ／ ⛔ 注册任务 ／ ⛔ 动盘）。
"""
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WPA = ROOT / "scripts" / "win_pa"
EXE = WPA / "install_win_pa.py"


def _run(args, env=None, timeout=180):
    return subprocess.run([sys.executable, "-X", "utf8", "-B", str(EXE)] + args,
                          capture_output=True, cwd=str(ROOT), timeout=timeout, env=env)


def _plan(env=None):
    r = _run(["--json"], env=env)
    assert r.returncode == 0, (r.returncode, r.stdout[-400:], r.stderr[-400:])
    return json.loads(r.stdout.decode("utf-8-sig"))


def test_installer_exists_and_compiles():
    assert EXE.is_file() and EXE.stat().st_size > 0
    import py_compile
    py_compile.compile(str(EXE), doraise=True)


def test_self_test_passes():
    r = _run(["--self-test"])
    out = r.stdout.decode("utf-8", "replace")
    assert r.returncode == 0, (r.returncode, out[-600:])
    assert "PASS" in out and "5 反控" in out, out[-300:]


def test_dry_run_is_default_and_idempotent():
    u"""⒜ ＋ ⒝：缺省干跑；第二跑 ≡ 第一跑（皆 rc 0 · 皆 ⛔ mkdir）。"""
    d = _plan()
    assert d["dry_run"] is True and d["rc"] == 0, d["rc"]
    txt = "\n".join(d["lines"])
    assert "将动" in txt and "未动" in txt
    assert "mkdir" not in txt, "干跑竟动了盘"
    for it in d["plan"]["dirs"]:
        if it["exists"]:
            assert "no-op" in txt
    d2 = _plan()
    assert d2["rc"] == 0 and [x for x in d2["lines"] if "mkdir" in x] == []


def test_preflight_gates_are_all_shown():
    u"""⒞ 前置闸显形（六栏 · ⛔ 静默过）。"""
    plan = _plan()["plan"]
    names = " ".join(i["name"] for i in plan["preflight"])
    for k in ("Python", "flask", "yaml", "端口", "data", "显存", "ollama"):
        assert k in names, (k, names)
    for i in plan["preflight"]:
        assert i["reason"], i
        if not i["ok"]:
            assert i["note"], ("败之闸须附修之门", i)


def test_reverse_control_preflight_insufficient_refuses():
    u"""⒠ 反控：前置 ⛔ 足 ⇒ rc 2 ∧ 报「⛔ 装」∧ ⛔ mkdir。"""
    env = dict(os.environ, PA_INSTALL_FORCE_FAIL="ollama")
    r = _run(["--json"], env=env)
    assert r.returncode == 2, (r.returncode, r.stdout[-300:])
    d = json.loads(r.stdout.decode("utf-8-sig"))
    assert d["rc"] == 2
    txt = "\n".join(d["lines"])
    assert "⛔ 装" in txt and "mkdir" not in txt, txt[-300:]


def test_only_directories_no_file_writes():
    u"""⒟ 唯立目录（⛔ 文件写点 · ⛔ 删 · ⛔ 起服）—— 以**调用形**判（⛔ 免文档串自指）。"""
    src = io.open(str(EXE), encoding="utf-8").read()
    assert "os.makedirs" in src
    assert not re.search(r"(shutil\.rmtree|os\.remove|os\.unlink)\(", src)
    _modes = [chr(34) + m + chr(34) for m in "wa"] + [chr(39) + m + chr(39) for m in "wa"]
    _opens = re.findall(r"(?<![A-Za-z_])open\(([^)]*)\)", src)
    assert not [o for o in _opens if any(m in o for m in _modes)], _opens
    assert not re.search(r"subprocess\.run\([^)]*pa_nowindow", src)
    for it in _plan()["plan"]["dirs"]:
        assert it["item"] == "dir"


def test_tasks_not_registered_by_default():
    u"""ⓔ（系统动作）：缺省 ⛔ 注册任务（⛔ 改机）。"""
    d = _plan()
    assert d["register_tasks"] is False
    assert any("⛔ 本器 ⛔ 注册" in x for x in d["lines"])


def test_bat_is_thin_shell():
    s = io.open(str(WPA / "install_win_pa.bat"), encoding="utf-8", errors="replace").read()
    pys = [ln.strip() for ln in s.splitlines() if ln.strip().lower().startswith("python")]
    assert pys and len(pys) == 1, pys
    assert "install_win_pa.py" in pys[0], pys



def test_kb_skeleton_dirs_single_source():
    u"""⭐ pm_1442 §二.2（库根新立）：内置知识库之骨架（`data/kb` ＋六约定）须**在立目录之列**，
    且六名**一处定形** ≡ `core.lib.note_kernel.SUBDIRS`（⛔ 二份字面 · 反控：本器 ⛔ 自带其名）。"""
    import importlib
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    nk = importlib.import_module("core.lib.note_kernel")
    d = _plan()
    paths = [i["path"] for i in d["plan"]["dirs"]]
    assert "data/kb" in paths, paths
    for n in nk.SUBDIRS:
        assert ("data/kb/" + n) in paths, (n, paths)
    kb = [i for i in d["plan"]["dirs"] if i["path"] == "data/kb"]
    assert kb and kb[0].get("note"), kb
    src = io.open(str(EXE), encoding="utf-8").read()
    for n in nk.SUBDIRS:
        assert (chr(34) + n + chr(34)) not in src, (u"本器自带子目录字面（应唯引内核）", n)
    assert "note_kernel" in src


def test_kb_skeleton_gate_reverse_control():
    u"""⭐ 反控：`note_kernel.SUBDIRS` ⛔ 得 ⇒ 闸**败**（显因）∧ 立目录之列 ⛔ 含 kb（⛔ 静默半立）。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("_iwp_probe", str(EXE))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.kb_subdirs = lambda: ((), u"ImportError: demo")
    g = m.preflight_gates()
    kb = [i for i in g if i["name"] == u"知识库骨架"]
    assert kb and kb[0]["ok"] is False and "demo" in kb[0]["reason"], kb
    d = m.dir_items()
    assert "data/kb" not in [i["path"] for i in d], d
    assert [i["path"] for i in d] == list(m.DIRS), d
