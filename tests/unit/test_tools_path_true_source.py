# -*- coding: utf-8 -*-
"""判据一律引真源 · 两处硬引用反例门（CEO 2026-09-28 终裁 §三① · 准入普通批）。

病理：判据／工具把**绝对路径写死**在本地 ⇒ 换树／换机／换平台（Windows ↔ WSL）就
**判据在场却打错对象**。本批两处实例：
  ① `tools/scan_heartbeat.mjs` —— 载体／留痕／禁区／CLI 共 5 处写死 `D:\\...`；
  ② `tools/check_ledger_numbering.py` —— 默认目标写死 WSL 形态 `/mnt/d/...`，在 Windows
     侧解析成 `D:\\mnt\\d\\...`（不抛错、找不到真件）⇒ 工具**报「文件不存在」**（Win 侧实为坏件）。
⇒ 纪律 = **引真源 ＋ 成对改 ＋ 反例门**：⛔ 不许「只加新串」（那是把 1 个硬编码换成 N 个，
  判据仍不跟随）。真源 = 环境变量（`PA_VAULT_DIR` 与 Python 侧 `core.lib.paths.vault_root()`
  **同名** · `CLAWSJOY_ROOT` · `CODEX_CLI`）／`core.lib.paths.vault_root()`。

判据（每条都能先失败）
  A 真源单点：绝对路径字面量在件内**只出现一次**（复述即红）—— 复扫归零
  B 判据跟随（node 真跑）：改 `CLAWSJOY_ROOT`／`PA_VAULT_DIR` ⇒ 载体／禁区／留痕**跟着走**
  C 判据跟随（python 真跑）：改 `PA_VAULT_DIR` ⇒ 默认目标跟着走；`CLAWSJOY_HEALTH_LIB` 仍优先
  D 功能后绿：`--selftest` rc=0；且默认目标在**真 vault** 上可读（不再「文件不存在」）
"""
import os
import subprocess
import sys

import pytest

sys.path.insert(0, ".")
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_MJS = "tools/scan_heartbeat.mjs"
_PY = "tools/check_ledger_numbering.py"
_REAL_VAULT = Path("D:/Obsidian/ClawsJoy/ClawsJoy")
_TITLE = "体检项库_V9.md"


def _read(rel):
    return (_REPO / rel).read_text(encoding="utf-8")


def _node():
    return os.environ.get("NODE_BIN") or "node"


# ---------- A 真源单点（复扫归零） ----------


def test_A_no_absolute_path_is_restated_in_scan_heartbeat():
    """mjs 里每个绝对路径字面量**只许出现一次**（真源块）—— 复述即红。"""
    t = _read(_MJS)
    for lit in (r"D:\\clawsjoy_v9", r"D:\\Obsidian\\ClawsJoy\\ClawsJoy"):
        n = t.count(lit)
        assert n == 1, "绝对路径被复述 %d 次（应 1 次 · 只留真源块）: %s" % (n, lit)
    # 真源块必须真的读环境（否则「单点」只是把字面量搬了个家）
    for env in ("CLAWSJOY_ROOT", "PA_VAULT_DIR", "CODEX_CLI"):
        assert ("process.env." + env) in t, "缺环境真源: " + env


def test_A_windows_side_tool_keeps_at_most_one_wsl_fallback():
    """py 里 WSL 形态串至多 1 处（且为**兜底**，非权威值）—— 权威值须来自真源。"""
    t = _read(_PY)
    assert t.count("/mnt/d/Obsidian") <= 1, "WSL 串被复述 ⇒ 真源没接上"
    assert "vault_root" in t, "须引 single source: core.lib.paths.vault_root"


# ---------- B 判据跟随真源（node 真跑） ----------


def _probe_mjs(env_extra):
    code = (
        "const m = await import(%r);\n"
        "console.log('PROBE' + JSON.stringify({"
        "carriers: m.DEFAULT_CFG.carriers.map((x) => x.path),"
        "forbidden: m.DEFAULT_CFG.forbiddenRoots,"
        "trace: m.DEFAULT_CFG.tracePath,"
        "cli: m.DEFAULT_CFG.alert.cli,"
        "cfgOk: m.checkConfig().ok}));\n"
    ) % ((_REPO / _MJS).as_uri(),)
    env = dict(os.environ)
    env.update(env_extra)
    p = subprocess.run(
        [_node(), "--input-type=module"],
        input=code, capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(_REPO), env=env,
    )
    assert "PROBE" in (p.stdout or ""), (p.stdout, p.stderr)
    line = [l for l in p.stdout.splitlines() if l.startswith("PROBE")][-1]
    import json

    return json.loads(line[len("PROBE"):])


def test_B_carriers_follow_env_true_source(tmp_path):
    """把真源指到别处 ⇒ 载体／禁区／留痕须**跟着走**（只加新串的实现过不了这条）。"""
    repo, vault = tmp_path / "proj", tmp_path / "vault"
    repo.mkdir(); vault.mkdir()
    got = _probe_mjs({"CLAWSJOY_ROOT": str(repo), "PA_VAULT_DIR": str(vault)})

    def norm(x):
        return os.path.normcase(os.path.normpath(str(x)))

    assert norm(got["carriers"][0]) == norm(repo / "data/tmp/cdp/_poll/watch_health.json")
    assert norm(got["carriers"][1]) == norm(vault / "dsh/_心跳_DSH.jsonl")
    assert norm(got["trace"]) == norm(repo / "data/tmp/l3/scan_trace.jsonl")
    assert [norm(x) for x in got["forbidden"]] == [
        norm(repo / "data/tmp/cdp/_poll"), norm(vault / "dsh"),
    ]
    assert got["cfgOk"] is True, "跟随真源后配置机检须仍绿（留痕不得落进禁区）"


def test_B_cli_follows_env(tmp_path):
    """告警 CLI 亦须可指（换机／换 node 安装位不改件）。"""
    got = _probe_mjs({"CODEX_CLI": str(tmp_path / "x" / "codex.js")})
    assert os.path.normcase(got["cli"]) == os.path.normcase(str(tmp_path / "x" / "codex.js"))


# ---------- C 判据跟随真源（python 真跑） ----------


def _probe_py(env_extra):
    code = (
        "import sys; sys.path.insert(0, %r);"
        "import tools.check_ledger_numbering as m;"
        "print('PROBE' + m._default_health_lib())"
    ) % str(_REPO)
    env = dict(os.environ)
    env.update(env_extra)
    env.pop("CLAWSJOY_HEALTH_LIB", None)
    env.update({k: v for k, v in env_extra.items() if k == "CLAWSJOY_HEALTH_LIB"})
    p = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(_REPO), env=env,
    )
    assert "PROBE" in (p.stdout or ""), (p.stdout, p.stderr)
    line = [l for l in p.stdout.splitlines() if l.startswith("PROBE")][-1]
    return line[len("PROBE"):]


def test_C_default_target_follows_vault_root(tmp_path):
    """默认目标须由 `vault_root()` 算出（⛔ 不写死）⇒ 改 `PA_VAULT_DIR` 即跟着走。"""
    vault = tmp_path / "v"
    vault.mkdir()
    got = _probe_py({"PA_VAULT_DIR": str(vault)})
    assert os.path.normcase(os.path.normpath(got)) == os.path.normcase(
        os.path.normpath(str(vault / "收件箱" / _TITLE))
    ), got


def test_C_explicit_env_still_wins(tmp_path):
    """`CLAWSJOY_HEALTH_LIB` 仍**优先**（保留既有覆盖能力 · 成对改不得推翻旧行为）。"""
    explicit = str(tmp_path / "explicit.md")
    got = _probe_py({"CLAWSJOY_HEALTH_LIB": explicit, "PA_VAULT_DIR": str(tmp_path / "elsewhere")})
    assert got == explicit, got


# ---------- D 功能后绿 ----------


def test_D_selftest_still_green():
    p = subprocess.run(
        [sys.executable, _PY, "--selftest"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(_REPO),
    )
    assert p.returncode == 0, (p.stdout, p.stderr)
    assert "自检通过" in (p.stdout or "")


@pytest.mark.skipif(not (_REAL_VAULT / "收件箱" / _TITLE).is_file(),
                    reason="本机无 Obsidian 体检项库")
def test_D_reads_real_library_not_file_missing():
    """后绿：工具须**真读到**真件（改前 Win 侧恒报「文件不存在」= 判据没打到对象）。"""
    p = subprocess.run(
        [sys.executable, _PY],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(_REPO),
    )
    out = p.stdout or ""
    assert _TITLE in out, out
    assert "文件不存在" not in out, "仍报「文件不存在」⇒ 默认目标没接到真源（Win 侧坏件未修）"
    assert p.returncode in (0, 1), ("仅 0/1 为正常（0 连续 ／ 1 有缺号）", p.returncode, out)
