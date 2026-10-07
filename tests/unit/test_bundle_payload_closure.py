# -*- coding: utf-8 -*-
u"""载荷之判据之齿（承 pm_1598 §二 令一 · 判据换轴）。

由：`PAYLOAD` 旧为**手写白名单** ⇒ 其「册」与「印」同出一单 ⇒ **以清单自证清单**
  ⇒ `engine/` ／ `agents/` ／ `gateway_endpoint.py`（共 99 件）之缺**闸不响**
  ⇒ 净机「启动不了」。本齿锁：**闭包之件 ⇒ 必在载荷**（⛔ 白名单自证）。

器取：`python -X utf8 -B -m pytest tests/unit/test_bundle_payload_closure.py -q`
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WPA = ROOT / "scripts" / "win_pa"
sys.path.insert(0, str(WPA))
sys.path.insert(0, str(ROOT))

import import_closure as IC  # noqa: E402
import make_client_bundle as M  # noqa: E402


def _norm(x):
    return str(x).replace(os.sep, u"/")


def test_every_closure_file_is_in_the_payload():
    u"""决定之齿：闭包之**自有件** ⇒ 逐件在 `_payload_files()`（⛔ 白名单自证）。"""
    out, _third, _unres = IC.closure(str(ROOT))
    got = {_norm(f) for f in M._payload_files(str(ROOT))}
    # ⛐ 命名空间包（无 `__init__.py`）之**目录标记** ⇒ 非「件」（其下之 `.py` 已在闭包）
    files = [r for r in out
             if os.path.isfile(os.path.join(str(ROOT), r.replace(u"/", os.sep)))]
    miss = sorted(_norm(r) for r in files if _norm(r) not in got)
    assert not miss, u"载荷缺闭包之件 %d：%s" % (len(miss), miss[:20])


def test_the_three_tops_that_were_missing_are_covered():
    u"""反控（pm_1598 §一 之三层）：`engine` ／ `agents` ／ `gateway_endpoint.py` 必得。"""
    eff = set(M.effective_payload(str(ROOT)))
    for want in (u"engine", u"agents", u"gateway_endpoint.py"):
        assert want in eff, (want, sorted(eff))


def test_reference_entry_file_is_reached():
    u"""正控：入口之闭包非空 ∧ 含 `agent_gateway_enhanced.py` 自身。"""
    out, _third, _unres = IC.closure(str(ROOT))
    assert IC.ENTRY in {_norm(r) for r in out}
    assert len(out) > 100, len(out)