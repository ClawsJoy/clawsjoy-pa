# -*- coding: utf-8 -*-
r"""get_data_root() 与「根」绑定（承规七）＋ env 之覆 —— pm_1698 §三.1⒜。

以何形调用：
  cd D:\clawsjoy_v9
  python -X utf8 -B -m pytest tests/unit/test_data_root_1698.py -q -p no:cacheprovider

病（一手 · 2026-10-07）：get_data_root() 昔返 config 之字面 `data`（**相对径**）
⇒ 消费者 `Path(get_data_root()) / "vector_kb"` 按 **CWD** 解 ⇒ **异 cwd ⇒ 异仓**（态漂）
（＝规七之第四次显形：CW 之面齿在**沙箱** CWD 下竟写 `D:\clawsjoy_v9\data\**`）。

本件之齿（承规七「二根交叠」之正反控）：
  P1 正控：相对 config 值 ⇒ **绝对** ⟷ 仓根（不按 CWD）
  P1b 正控：换 CWD 至他根 ⇒ 其值**不变**
  P2 正控：env 之覆（绝对 ⇒ 逐字）
  P3 正控：env 之覆（相对 ⇒ 按仓根拼）
  P4 反控：绝对 config 值 ⇒ 逐字（不再拼）
  R1 反控（二根交叠）：A 探得 ⇒ B 不被覆 ∧ 复读 A 仍得 ∧ 他根之 data 不被取
  R2 界：config 空 ∧ env 空 ⇒ 回落 `data`（不成仓根 ／ 不成 None）
  E1 端到端：异 cwd 之消费径 ⇒ 仍归**本仓**（复现其病之反面）
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from core.lib import config_helper as CH

REPO_ROOT = Path(CH.__file__).resolve().parents[2]


class _Cfg:
    """替身：唯供 `unified_config.get("paths.data_root", …)` 一读。"""

    def __init__(self, val):
        self._val = val

    def get(self, key, default=None):
        if key == "paths.data_root":
            return self._val
        return default


def _set(monkeypatch, val, env=None):
    monkeypatch.setattr(CH, "unified_config", _Cfg(val))
    if env is None:
        monkeypatch.delenv(CH.DATA_ROOT_ENV, raising=False)
    else:
        monkeypatch.setenv(CH.DATA_ROOT_ENV, env)


# ---------- P1 正控 ----------

def test_P1_relative_config_anchored_to_repo_root(monkeypatch):
    _set(monkeypatch, "data")
    got = Path(CH.get_data_root())
    assert got.is_absolute(), got
    assert got == REPO_ROOT / "data", (got, REPO_ROOT / "data")


def test_P1b_cwd_never_changes_it(monkeypatch, tmp_path):
    other = tmp_path / "other_root"
    other.mkdir()
    _set(monkeypatch, "data")
    before = CH.get_data_root()
    monkeypatch.chdir(other)
    after = CH.get_data_root()
    assert before == after == str(REPO_ROOT / "data"), (before, after)


# ---------- P2 / P3 正控：env 之覆 ----------

def test_P2_env_absolute_verbatim(monkeypatch, tmp_path):
    _set(monkeypatch, "data", env=str(tmp_path))
    assert CH.get_data_root() == str(tmp_path)


def test_P3_env_relative_anchored(monkeypatch):
    _set(monkeypatch, "data", env="data")
    assert CH.get_data_root() == str(REPO_ROOT / "data")


# ---------- P4 反控：绝对 config 值 ----------

def test_P4_absolute_config_verbatim(monkeypatch, tmp_path):
    _set(monkeypatch, str(tmp_path / "abs_data"))
    assert CH.get_data_root() == str(tmp_path / "abs_data")


# ---------- R1 反控：二根交叠 ----------

def test_R1_two_roots_no_overlap(monkeypatch, tmp_path):
    _set(monkeypatch, "data")
    a1 = CH.get_data_root()
    bdir = tmp_path / "B"
    (bdir / "data").mkdir(parents=True)
    monkeypatch.chdir(bdir)
    a2 = CH.get_data_root()
    assert a1 == a2, (a1, a2)                 # A 探得 ⇒ B 不被覆
    assert Path(a2) == REPO_ROOT / "data"
    assert Path(a2) != (bdir / "data")         # 他根之 data 不被取
    monkeypatch.chdir(REPO_ROOT)
    assert CH.get_data_root() == a1            # 复读 A 仍得


# ---------- R2 界：唯空 ⇒ 回落 data ----------

def test_R2_empty_falls_back_to_data(monkeypatch):
    _set(monkeypatch, "")
    got = CH.get_data_root()
    assert got == str(REPO_ROOT / "data"), got
    assert got != str(REPO_ROOT), got


# ---------- E1 端到端：异 cwd 之消费径仍归本仓 ----------

def test_E1_consumer_path_repo_bound(tmp_path):
    sb = tmp_path / "sb"
    sb.mkdir()
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    env.pop(CH.DATA_ROOT_ENV, None)
    code = ("from core.lib.config_helper import get_data_root\n"
            "from pathlib import Path\n"
            "print('KB', Path(get_data_root()) / 'vector_kb')\n")
    r = subprocess.run([sys.executable, "-X", "utf8", "-B", "-c", code],
                       capture_output=True, cwd=str(sb), env=env, timeout=600)
    out = (r.stdout or b"").decode("utf-8", "replace")
    err = (r.stderr or b"").decode("utf-8", "replace")
    line = [x for x in out.splitlines() if x.startswith("KB ")]
    assert line, (r.returncode, out[-400:], err[-700:])
    kb = Path(line[0][3:].strip())
    assert kb.is_absolute(), kb
    assert str(kb).startswith(str(REPO_ROOT)), (kb, REPO_ROOT)
    assert not str(kb).startswith(str(sb)), kb