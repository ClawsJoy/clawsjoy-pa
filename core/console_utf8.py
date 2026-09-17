# -*- coding: utf-8 -*-
"""Windows 控制台 UTF-8 兼容垫片。

Windows 中文环境下 ``sys.stdout`` 默认是 cp936(GBK)。任何 emoji（例如启动
日志里的 ``✅``）都会抛 ``UnicodeEncodeError``，而异常发生在**模块级**打印里，
会直接把 ``import core`` 整个打断 —— 测试期看不出来，因为 pytest 用 UTF-8
抓取 stdout。

这里把标准流显式切到 UTF-8；已经是 UTF-8 的流（pytest 抓取 / 已重定向）保持不动。
"""
import sys

_UTF8_ALIASES = {"utf8", "utf8mb4", "cp65001"}


def ensure_utf8_console():
    """让 stdout/stderr 能安全输出非 GBK 字符（emoji 等）。返回是否有改动。"""
    if sys.platform != "win32":
        return False
    changed = False
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        enc = (getattr(stream, "encoding", "") or "").lower().replace("-", "")
        if enc in _UTF8_ALIASES:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
            changed = True
        except Exception:
            pass
    return changed
