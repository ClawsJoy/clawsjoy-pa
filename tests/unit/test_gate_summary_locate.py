# -*- coding: utf-8 -*-
"""G-02 子项⑥ 修法 A 验收：汇总口径 = **全文取最后一条汇总行**（2026-09-18 · 老板/DS 拍）。

背景（实测，同一批代码三次全量跑抓到三种形态）：其中「**假绿**」最危险 ——
产品侧在 cp936 控制台下打印 emoji 抛 `UnicodeEncodeError`，垫片把降级报错打在 pytest 汇总行
**之后** ⇒ 旧「只读末行」写法手里 `counts` **全空**，而门禁**仍判 ✅**（PASS 由 nodeid 名单决定）
⇒ 证据残缺却报绿。

判据：① 汇总行不在末行 ⇒ 仍能定位到它（且 counts 非空）；② 正常跑 ⇒ `summary == tail`（行为不变）；
③ 全文都没有 ⇒ 回落末行（与旧版逐字一致，不引入新失败面）；
④ 短摘要行 / 参数化 id 里的「N failed/passed」**不得**被误认成汇总行；
⑤ **判定层未动**（静态判据：bad 列表不引用 summary/counts）。
"""
from __future__ import annotations

import ast
import importlib.util
import pathlib

_REPO = pathlib.Path(__file__).resolve().parents[2]
_TOOL = _REPO / "tools" / "check_test_baseline.py"

# 真实汇总行（gate_r7 实测形态）
_SUMMARY = "= 25 failed, 1808 passed, 7 skipped, 1 xfailed, 43 warnings in 187.35s (0:03:07) ="
# 真实污染行（gate_r6 实测末行形态）：产品侧 emoji 打印在 cp936 下的降级报错
_POLLUTION = ("[code_agent_v4] 打印错误: 'gbk' codec can't encode character "
              "'\\U0001f4da' in position 45: illegal multibyte sequence")


def _load():
    spec = importlib.util.spec_from_file_location("_cj_gate_summary_locate", _TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _counts(m, text):
    return {k: int(n) for n, k in m._SUMMARY_RE.findall(text)}


def test_summary_found_when_not_last_line():
    """子项⑥ 的核心：汇总行之后还有输出 ⇒ 仍能读到汇总（旧写法会读成空）。"""
    m = _load()
    out = "\n".join([_SUMMARY, "", _POLLUTION]) + "\n"
    summary, tail, off = m._locate_summary(out)
    assert summary == _SUMMARY
    assert tail == _POLLUTION
    assert off is True, "必须标出「汇总不在末行」（否则 summary_off_last_line 恒 false）"
    # 关键断言：counts 不再为空 —— 这就是 r6「假绿」的修复点
    assert _counts(m, summary or tail) == {"failed": 25, "passed": 1808, "skipped": 7, "xfailed": 1}
    # 反例：旧口径（只读末行）在同一样本上必然读成空
    assert _counts(m, tail) == {}, "旧口径在本样本上应读成空 —— 否则本用例没钉住问题"


def test_normal_run_summary_is_the_tail():
    """正常跑：汇总行就是末行 ⇒ `summary == tail`、off=False（输出与旧版逐字一致）。"""
    m = _load()
    out = "tests/unit/test_x.py::test_a PASSED\n\n" + _SUMMARY + "\n"
    summary, tail, off = m._locate_summary(out)
    assert summary == tail == _SUMMARY
    assert off is False


def test_no_summary_anywhere_falls_back_to_tail():
    """全文找不到汇总行 ⇒ 回落末行（与旧版行为一致，不引入新失败面）。"""
    m = _load()
    out = "tests/unit/test_x.py::test_a PASSED\ncollected 3 items\n"
    summary, tail, off = m._locate_summary(out)
    assert summary == ""
    assert tail == "collected 3 items"
    assert off is False


def test_short_summary_and_param_ids_do_not_masquerade():
    """短摘要行 / 参数化 id 里的「N failed/passed」不得被当成汇总行。"""
    m = _load()
    out = "\n".join([
        "tests/unit/test_x.py::test_a[3 passed cases] PASSED",
        "FAILED tests/unit/test_x.py::test_b - AssertionError: 3 failed items",
        _SUMMARY,
    ]) + "\n"
    summary, _tail, _off = m._locate_summary(out)
    assert summary == _SUMMARY, "选中的不是真汇总行：%r" % summary
    # 反向：这些干扰行自己**不该**被 _SUMMARY_LINE_RE 认成汇总行
    assert m._SUMMARY_LINE_RE.search("FAILED tests/x.py::t - AssertionError: 3 failed items") is None


def test_locator_feeds_counts_only_never_the_verdict():
    """静态判据：汇总定位只喂给 counts；判定（bad 列表）不得引用 summary/counts。"""
    src = _TOOL.read_text(encoding="utf-8")
    tree = ast.parse(src)
    main = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main"]
    assert main, "未找到 main"
    seg = ast.get_source_segment(src, main[0])
    assert "bad.append" in seg
    for line in seg.splitlines():
        if "bad.append" in line:
            for forbidden in ("summary", "counts", "_accounted"):
                assert forbidden not in line, "判定层引用了留痕口径: %s" % line
