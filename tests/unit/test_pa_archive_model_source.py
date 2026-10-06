# -*- coding: utf-8 -*-
"""pm_1474 §一 之齿：`core/gateway/v9_chat/archive.py` 之模型名 ⇒ **唯自 PA 注册表**（一处定形）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_archive_model_source.py -q

判据：
  ⒜ 正控（默认之值）：`data` ⛔ 带 `model` ∧ env `DEEPSEEK_MODEL` ⛔ 配 ⇒ model ≡ 注册表 `DEFAULT_MODEL["model"]`
     （**实名** · ⛔ 硬编别名）。
  ⒝ 反控（归一）：旧别名 `deepseek-v4-flash`（前端硬编 ∨ env）⇒ 归一为**实名**。
  ⒞ 齿（一处定形）：改注册表之 `DEFAULT_MODEL` ⇒ archive 之默认随之（⛔ 硬编）。
  ⒟ 保形（⛔ 破）：`""` ／ `None` ／ 未知名 ⇒ **原样透传**（承旧行 `data.get("model", …)` 之形）。
  ⒠ 反控（源）：活代码 ⛔ 模型名字面；⛔ `from core.pa …`（须**按路径载** · 承 `core/gateway/_proc.py` 之律）。
  ⒡ 零副作用（行为齿 · 子进程）：载 archive ⇒ `core.pa` ⛔ 入 `sys.modules`。
"""
from __future__ import annotations

import io
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.gateway.v9_chat import archive as A_ARCH  # noqa: E402

OLDMODEL = "deepseek-" + "v4-flash"
REALMODEL = "deepseek-" + "flash"


def _rsid(user_id, session_id):
    return (session_id, None)


def _model_for(data):
    """跑一次归档层入口 ⇒ 回其定之 `model`。"""
    st = A_ARCH.prepare_chat_entry(data=data, resolve_session_id_fn=_rsid)
    return st["model"]


# ---------- ⒜ 正控：默认之值 ----------

def test_default_model_is_registry_real_name(monkeypatch):
    u"""⒜：默认之值 ≡ 注册表之**实名**（一处定形 · ⛔ 硬编别名）。"""
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)
    want = A_ARCH._pa_providers().DEFAULT_MODEL["model"]
    assert want, u"注册表应有默认模型名"
    assert want in A_ARCH._pa_providers().known_models()
    assert want != OLDMODEL, u"默认 ⛔ 落旧别名"
    assert _model_for({"messages": []}) == want


# ---------- ⒝ 反控：归一 ----------

def test_front_end_legacy_alias_normalized(monkeypatch):
    u"""⒝：前端硬编之旧别名 ⇒ 归一为实名（承 pm_1472 §三）。"""
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)
    assert _model_for({"model": OLDMODEL, "messages": []}) == REALMODEL


def test_env_legacy_alias_normalized(monkeypatch):
    u"""⒝（env）：`DEEPSEEK_MODEL` 之旧别名 ⇒ 归一为实名。"""
    monkeypatch.setenv("DEEPSEEK_MODEL", OLDMODEL)
    assert _model_for({"messages": []}) == REALMODEL


def test_real_name_stays_real_name(monkeypatch):
    u"""⒝（幂等）：已为实名 ⇒ 不变（⛔ 空转）。"""
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)
    assert _model_for({"model": REALMODEL, "messages": []}) == REALMODEL


# ---------- ⒞ 齿：一处定形 ----------

class _FakeP(object):
    DEFAULT_MODEL = {"provider": "remote:deepseek", "model": "zzz-renamed", "thinking": None}

    @staticmethod
    def resolve_model(name):
        return "zzz-renamed" if str(name or "").strip() == "zzz-old" else None


def test_default_follows_registry_change(monkeypatch):
    u"""⒞：改注册表 ⇒ 默认随之（若硬编 `deepseek-flash` 则本测须红）。"""
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)
    monkeypatch.setattr(A_ARCH, "_PA_PROVIDERS", _FakeP)
    assert _model_for({"messages": []}) == "zzz-renamed"
    assert _model_for({"model": "zzz-old", "messages": []}) == "zzz-renamed"


# ---------- ⒟ 保形：⛔ 破 ----------

@pytest.mark.parametrize("raw", ["", None, "unknown-xyz"])
def test_unknown_or_empty_passthrough(monkeypatch, raw):
    u"""⒟：空 ／ None ／ 未知名 ⇒ 原样透传（与旧行同形 · ⛔ 改其他颗）。"""
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)
    assert _model_for({"model": raw, "messages": []}) == raw


# ---------- ⒠ 反控：源 ----------

def _live_lines(pat):
    src = io.open(A_ARCH.__file__, encoding="utf-8").read()
    out = []
    for i, ln in enumerate(src.splitlines(), 1):
        code = ln.split("#", 1)[0]
        if re.search(pat, code):
            out.append((i, ln.strip()))
    return out


def test_no_hardcoded_model_name_in_archive_live_code():
    u"""⒠：本件活代码 ⛔ 载模型名字面（唯自注册表出）。"""
    live = _live_lines(r"deepseek-(?:flash|v4-flash|v4-pro)")
    assert live == [], u"活代码内不得硬编模型名：%r" % (live,)


def test_archive_does_not_import_core_pa_package():
    u"""⒠：⛔ `from core.pa …` —— 须**按路径载**（承 `core/gateway/_proc.py` 之已立之律）。"""
    live = _live_lines(r"^\s*(?:from\s+core\.pa\b|import\s+core\.pa\b)")
    assert live == [], u"不得走包导入（会执行 core/pa/__init__.py）：%r" % (live,)


# ---------- ⒡ 行为齿：零副作用（子进程） ----------

def test_loading_archive_does_not_pull_core_pa_package():
    u"""⒡：子进程内**首载** archive ⇒ `core.pa` ⛔ 入 `sys.modules`（证「零副作用」）。"""
    code = (
        "import sys\n"
        "sys.path.insert(0, r'%s')\n"
        "import core.gateway.v9_chat.archive as a\n"
        "print('PA=%%s' %% ('core.pa' in sys.modules))\n"
    ) % (str(ROOT),)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    p = subprocess.run([sys.executable, "-X", "utf8", "-B", "-c", code],
                       cwd=str(ROOT), env=env, capture_output=True)
    out = (p.stdout or b"").decode("utf-8", "replace")
    err = (p.stderr or b"").decode("utf-8", "replace")
    assert p.returncode == 0, err[-800:]
    assert "PA=False" in out, out[-400:] + err[-400:]