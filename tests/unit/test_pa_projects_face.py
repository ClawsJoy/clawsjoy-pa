# -*- coding: utf-8 -*-
u'''齿：端面 /v9/pa/projects 之**采数一处出**（承 CEO 2221 §四 ／ PM 2222 §二 ／ PM 2228 §二）。

⭐ 正控：真跑 codex/_CEO面核.py --due ⇒ 四数可解 ∧ 源 ＋ 取数刻 ＋ 口径 ＋ 源印 皆载。
⭐ 反控：⛔ 采不入（乱文 ∨ 器不在）⇒ **⛔ 端自算**（必报 · ⛔ 以端自算兜底）⇒ 反控必咬。
'''
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V9 = os.path.dirname(os.path.dirname(HERE))
if V9 not in sys.path:
    sys.path.insert(0, V9)

from core.pa.projects_face import DUE_CORE, due_core_parse, projects_face  # noqa: E402


def test_projects_positive_real_due():
    r = projects_face()
    assert r.get("ok") is True, r
    for k in ("数据行", "待收口之试", "红", "阶催缴"):
        assert isinstance(r[k], int), (k, r)
    assert r.get("取数刻"), r
    assert r.get("口径") == u"非空∧十一列", r
    assert r.get("源") == DUE_CORE, r
    assert r.get("端自算") is False, r
    assert str(r.get("源印", "")).startswith(u"md5[:16] "), r


def test_projects_negative_no_self_compute():
    assert due_core_parse(u"") is None
    assert due_core_parse(u"nuisance, no four numbers here") is None
    r = projects_face(core=os.path.join(HERE, u"definitely_missing_core.py"))
    assert r.get("ok") is False, r
    assert r.get("端自算") is False, r
    assert u"面核器不在" in r.get("error", ""), r
