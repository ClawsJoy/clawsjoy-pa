#!/usr/bin/env python3
"""Init - Init 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


from core.console_utf8 import ensure_utf8_console

# Windows 控制台默认 GBK：模块级启动日志里的 emoji 会抛 UnicodeEncodeError，
# 直接打断 import core。先切 UTF-8，再做任何输出。
ensure_utf8_console()

from core.lib.unified_config import unified_config
from core.tenant.tenant_vector_index import tenant_index_manager

__all__ = ["tenant_index_manager", "unified_config"]
