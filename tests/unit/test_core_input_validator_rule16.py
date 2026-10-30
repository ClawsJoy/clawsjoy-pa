# -*- coding: utf-8 -*-
u"""齿：最小集第 16 条 —— 凡判「某物在场否」⇒ 须以「在场」为判 · ⛔ 以「替后是否变」为判。

靶：`core/lib/input_validator.py` 之 `validate_message()` 判「有危险内容否」。
旧形以 `sanitized != message` 判 ⇒ 「在场 ∧ 替值 ≡ 原值」与「⛔ 在」同形 ⇒ 假否（漏报）。
今形以 `_count_dangerous_content(message) > 0`（命中数）为判 ⇒ 真逮。

⛔ 触网 ／ ⛔ 触真箱 ／ ⛔ 触台账（唯读本模块 ＋ 内存串）。
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.lib.input_validator import InputValidator


def _old_judge(txt):
    u"""改前之判法（以「替后是否变」为判）—— 唯作对照，⛔ 供生产。"""
    s = txt
    for p in InputValidator.DANGEROUS_PATTERNS:
        s = re.sub(p, "[FILTERED]", s, flags=re.IGNORECASE)
    return s != txt


def test_正控_有险必报():
    r = InputValidator.validate_message("run rm -rf / now")
    assert not r.valid and any(u"危险" in e for e in r.errors)


def test_正控_无险不报():
    r = InputValidator.validate_message("hello world, plain text")
    assert r.valid and r.errors == []


def test_反控_在场而替值同原值_须逮():
    u"""第 16 条之靶：其物在 ∧ 替值 ≡ 原值 ⇒ 旧形假否 ／ 新形必逮。"""
    old = InputValidator.DANGEROUS_PATTERNS
    InputValidator.DANGEROUS_PATTERNS = [r"\[FILTERED\]"]
    try:
        txt = "[FILTERED]"
        assert _old_judge(txt) is False, u"旧形竟未假否 ⇒ 反控不成立"
        assert InputValidator._count_dangerous_content(txt) > 0
        r = InputValidator.validate_message(txt)
        assert not r.valid, u"新形未逮 ⇒ 第 16 条未治"
    finally:
        InputValidator.DANGEROUS_PATTERNS = old
