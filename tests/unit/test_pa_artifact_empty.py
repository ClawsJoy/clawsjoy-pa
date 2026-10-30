# -*- coding: utf-8 -*-
"""PA 迭代40 · T59：R1／C18 空件一律红（0 B 之 .md／.json／.py／.log）＋原逻辑不伤。

判据（承 T48 · 06_pm §三 R1 缺口）：
  0 B .md／.json／.py／.log ⇒ verify_artifact(...)["ok"] is False（size==0 一律拒）；
  与 allow_stub 无关（allow_stub 豁免的是「占位启发式」，⛔ 豁免「空件」）；
  verify_artifacts 批量亦红（逐条 failures）；
  非空件照原逻辑：小 .py／.log 仍免体积闸（ok=True ／ applicable=False）／.json 之 [] 2 B 合法／足量 .md 绿。
⛔ 改阈值：TYPE_MIN_BYTES／STUB_BYTES／MIN_ARTIFACT_BYTES 一字不动（本件末另有锁）。

跑：
  python -X utf8 -B -m pytest tests/unit/test_pa_artifact_empty.py -q
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import artifact as A  # noqa: E402

EMPTY_EXTS = (".md", ".json", ".py", ".log")


def _touch(tmp_path, name, data=b""):
    p = tmp_path / name
    p.write_bytes(data)
    return p


@pytest.mark.parametrize("ext", EMPTY_EXTS)
def test_0B_md_json_py_log_all_rejected(tmp_path, ext):
    """R1 反例：四类 0 B 均红（T48 实测 0 B .py／.log 曾 ok=True）。"""
    _touch(tmp_path, "empty" + ext)
    r = A.verify_artifact("empty" + ext, base_dir=tmp_path)
    assert r["ok"] is False, r
    assert r["size"] == 0, r
    assert r["applicable"] is False, r
    assert "空" in r["reason"], r


@pytest.mark.parametrize("ext", EMPTY_EXTS)
def test_0B_rejected_even_with_allow_stub(tmp_path, ext):
    """allow_stub 是「占位判定豁免」，⛔ 豁免「空件」（空件不是产物）。"""
    _touch(tmp_path, "empty" + ext)
    r = A.verify_artifact("empty" + ext, base_dir=tmp_path, allow_stub=True)
    assert r["ok"] is False, r
    assert r["size"] == 0, r


@pytest.mark.parametrize("ext", EMPTY_EXTS)
def test_0B_rejected_even_with_expected_min_bytes_zero(tmp_path, ext):
    """0 B 判据独立于阈值优先序：即便显式 expected_min_bytes=0，0 B 仍红。"""
    _touch(tmp_path, "empty" + ext)
    r = A.verify_artifact("empty" + ext, base_dir=tmp_path, expected_min_bytes=0)
    assert r["ok"] is False and r["size"] == 0, r


def test_0B_unregistered_type_also_rejected(tmp_path):
    """零字节判据与类型无关：未注册扩展名之 0 B 亦红（该型原逻辑本为 ok=True）。"""
    _touch(tmp_path, "x.xyz")
    r = A.verify_artifact("x.xyz", base_dir=tmp_path)
    assert r["ok"] is False and r["size"] == 0, r


def test_batch_all_empty_rejected(tmp_path):
    for ext in EMPTY_EXTS:
        _touch(tmp_path, "empty" + ext)
    r = A.verify_artifacts(["empty" + e for e in EMPTY_EXTS], base_dir=tmp_path)
    assert r["ok"] is False and r["checked"] == 4 and len(r["failures"]) == 4, r
    assert all(d["ok"] is False for d in r["details"]), r


# ---- 正控：非空件按原逻辑（⛔ 误伤） ----

def test_nonempty_small_py_still_passes(tmp_path):
    """.py 免体积闸照旧：x=1（3 B）⇒ ok=True ／ applicable=False。"""
    _touch(tmp_path, "small.py", b"x=1")
    r = A.verify_artifact("small.py", base_dir=tmp_path)
    assert r["ok"] is True and r["applicable"] is False, r


def test_nonempty_log_still_passes(tmp_path):
    """.log 免体积闸照旧：一行日志（8 B）⇒ ok=True ／ applicable=False。"""
    _touch(tmp_path, "run.log", b"run ok\n")
    r = A.verify_artifact("run.log", base_dir=tmp_path)
    assert r["ok"] is True and r["applicable"] is False, r


def test_nonempty_json_two_bytes_array_passes(tmp_path):
    """.json 之 []（2 B）合法（原逻辑）⇒ ok=True。"""
    _touch(tmp_path, "s.json", b"[]")
    r = A.verify_artifact("s.json", base_dir=tmp_path)
    assert r["ok"] is True, r


def test_nonempty_md_large_passes(tmp_path):
    """足量 .md 照旧绿（正控）。"""
    _touch(tmp_path, "deck.md", "正文".encode("utf-8") * 2000)
    r = A.verify_artifact("deck.md", base_dir=tmp_path)
    assert r["ok"] is True and r["reason"] is None, r


def test_one_byte_whitespace_is_not_zero_byte(tmp_path):
    """边界照实：本单只治 0 B；1 B 空白属「非空」，按原逻辑放行（.py 免体积闸）。"""
    _touch(tmp_path, "ws.py", b"\n")
    r = A.verify_artifact("ws.py", base_dir=tmp_path)
    assert r["ok"] is True and r["size"] == 1, r


# ---- 锁：⛔ 改阈值（T59 界） ----

def test_thresholds_untouched():
    assert A.MIN_ARTIFACT_BYTES == 512, A.MIN_ARTIFACT_BYTES
    assert A.STUB_BYTES == (68,), A.STUB_BYTES
    assert A.TYPE_MIN_BYTES[".md"] == 1024
    assert A.TYPE_MIN_BYTES[".json"] == 2
    assert A.TYPE_MIN_BYTES[".py"] is None
    assert A.TYPE_MIN_BYTES[".log"] is None
