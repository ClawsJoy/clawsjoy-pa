#!/usr/bin/env python3
"""Init - Init 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


from core.lib.unified_config import unified_config
from core.tenant.tenant_vector_index import tenant_index_manager

__all__ = ["tenant_index_manager", "unified_config"]
