# -*- coding: utf-8 -*-
"""X-09 验收：生命周期日志 / 兜底报错**不得写 stdout**（2026-09-18 · DS 拍「修污染源，不加固解析器」）。

背景（实测，物证 `data/test_baseline/raw/20260918T140448_parse_selfcheck-parse_miss.txt:331`、`:720`）：
Windows cp936 流上 `LifecycleMixin.log()` 里的 emoji `print` 抛 `UnicodeEncodeError`，
`_start_lifecycle_loop` 的兜底 `except` 再把「[{name}] 生命周期错误: {e}」打到**同一个 stdout**
⇒ 这行插进 pytest -v 的进度行中间，把「nodeid … 状态」劈成两行
⇒ 门禁逐行解析拿不到该 nodeid（差额 1）⇒ 误判「台账陈旧」**假红**（G-02 分子漏解析的真因）。

判据（与被判定的事同层：看**写到哪条流**，不看日志内容）：
① 正常路径：`log()` 只落 stderr，stdout 一字不落；
② 异常路径：把 stdout 换成 cp936 严格流（复刻真实现场），兜底报错仍**不得**落 stdout；
③ 不静默：两条路径都仍能在 stderr 读到内容（降级可见，不许吞）。

反例证明：本文件在 HEAD 版 `lifecycle_mixin.py` 上 2 条全红；修复后 2 条全绿。
"""
from __future__ import annotations

import io
import sys
import time

from core.agents.base.mixins.lifecycle_mixin import LifecycleMixin

_MARK = "生命周期错误"


class _ProbeAgent(LifecycleMixin):
    """最小宿主：只要 name（兜底报错要打它）。"""

    name = "probe_agent_v4"

    def __init__(self):
        super().__init__()


def _written(stream):
    """取文本流背后 BytesIO 的已写字节（write_through=True，写入即见）。"""
    try:
        stream.flush()
    except Exception:
        pass
    return stream.buffer.getvalue()


def test_log_goes_to_stderr_not_stdout(capsys):
    """① 正常路径：log() 只写 stderr。"""
    _ProbeAgent().log("\U0001f4ad 进入梦境 (第1次)")
    out, err = capsys.readouterr()
    assert out == "", f"stdout 必须干净（门禁解析面），实际: {out!r}"
    assert "进入梦境" in err, f"日志不得静默丢弃，应可在 stderr 读到，实际: {err!r}"


def test_lifecycle_fallback_does_not_write_stdout(monkeypatch):
    """②③ 异常路径：stdout 为 cp936 严格流时，兜底报错走 stderr（stdout 零字节）。"""
    fake_stdout = io.TextIOWrapper(io.BytesIO(), encoding="gbk", errors="strict", write_through=True)
    fake_stderr = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", write_through=True)
    monkeypatch.setattr(sys, "stdout", fake_stdout)
    monkeypatch.setattr(sys, "stderr", fake_stderr)

    def _boom(self, message, level="INFO"):      # 复刻真实现场：cp936 流上写 emoji
        raise UnicodeEncodeError("gbk", "\U0001f4ad", 0, 1, "illegal multibyte sequence")

    monkeypatch.setattr(LifecycleMixin, "log", _boom)
    agent = _ProbeAgent()
    agent._lifecycle_state = "sleeping"          # 第一轮就 _should_wake() -> _wake_up() -> log()
    agent._lifecycle_running = True
    agent._last_wake = None
    agent._wake_count = 0
    agent._start_lifecycle_loop()                # 后台守护线程，立即跑一轮

    deadline = time.time() + 5.0
    while time.time() < deadline and not (_written(fake_stdout) or _written(fake_stderr)):
        time.sleep(0.05)
    agent._lifecycle_running = False             # 让线程下一轮直接退出（不留残余写者）

    assert _written(fake_stdout) == b"", f"兜底报错污染了 stdout: {_written(fake_stdout)!r}"
    assert _MARK.encode("utf-8") in _written(fake_stderr), (
        "兜底报错不得静默丢弃，应可在 stderr 读到，实际: %r" % (_written(fake_stderr),))