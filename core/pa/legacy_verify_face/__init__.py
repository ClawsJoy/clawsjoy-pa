# -*- coding: utf-8 -*-
u"""PA 产品内 legacy 7+2 检查面（T125 · 只读 · ⛔ 建路由 · ⛔ import 顶层 legacy_verify）.

用法：
    from core.pa.legacy_verify_face import run_legacy_7_2
    doc = run_legacy_7_2()   # {face:'legacy_7_2', pass:7, fail:0, na:2, results:[...]}

面：C1/C2/C5/C6/C7/C10/C9 PASS ＋ C12/C13 N/A（quick 面 skip_scan 未扫，⛔ 计 PASS）。
"""
from core.pa.legacy_verify_face.face import (  # noqa: F401
    CHECKS,
    EXPECTED,
    FACE,
    LIVE_ROSTER_URL,
    run_legacy_7_2,
    summarize,
)

__all__ = ["FACE", "EXPECTED", "LIVE_ROSTER_URL", "CHECKS", "summarize", "run_legacy_7_2"]
