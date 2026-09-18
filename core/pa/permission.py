# -*- coding: utf-8 -*-
"""PA 权限档（能改）2026-09-11：cfgPerm 后端持久化。

值白名单：只读 / 标准 / 高(需确认)。
存储：data/v9/pa/permission.json（可用 env PA_PERMISSION_PATH / PA_DATA_DIR 覆盖）。

主权约束：本文件只能被 pa.html 前端（老板在场）经 /v9/pa/permission 路由写入；
PA agent 直写被 ForbiddenGuard._CONFIG_FILES 硬拒（agent_manual §4.2）。

2026-09-18（X-16 批 B · DS 拍 A）：**读写走统一出口**（`core/pa/state_out`）。
**这同时是对「静默放宽」的对治**：此前「文件存在但不可用」（损坏 JSON／非法 level／空文件）
被静默忽略并回落 `标准`，而 `只读 < 标准` ⇒ **损坏即放宽**。现在 ⇒ **抛**（fail-closed）。
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from core.pa.state_out import read_state, write_state

LEVELS = ("只读", "标准", "高(需确认)")
DEFAULT_LEVEL = "标准"


#: 写者标识（进出口的写者归属台账；供 detect_uninstrumented 识别绕过出口的写者）
_WRITER = "pa.permission"


def _shape(doc):
    """**PA 侧业务结构判据**（DS 拍①：判据留 PA 侧，不给出口加回调）。

    权限档只有三个合法取值 ⇒ 判据同时是「非法 level 不得落盘」的护栏（fail-closed）。
    """
    if doc.get("level") not in LEVELS:
        return False, "level 必须是 %s 之一" % "/".join(LEVELS)
    return True, ""


def _default_path() -> str:
    return os.getenv(
        "PA_PERMISSION_PATH",
        os.path.join(os.getenv("PA_DATA_DIR", "data/v9/pa"), "permission.json"),
    )


class PermissionStore:
    def __init__(self, path: str = None):
        self.path = Path(path or _default_path())
        self.data = {"level": DEFAULT_LEVEL, "updated": "", "updated_by": ""}
        self.load()

    def load(self):
        """**不存在 ⇒ 默认档；存在但不可用 ⇒ 抛 PAStateCorrupt**（不再静默回落默认档）。"""
        self.data = {"level": DEFAULT_LEVEL, "updated": "", "updated_by": ""}
        if self.path.exists():
            self.data = read_state(self.path, _WRITER, _shape)
        return self

    def get(self) -> str:
        return self.data.get("level", DEFAULT_LEVEL)

    def set(self, level, user_id: str = ""):
        if level not in LEVELS:
            return {"ok": False, "error": "权限档必须是: %s（收到 %r）" % ("/".join(LEVELS), level)}
        self.data = {
            "level": level,
            "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_by": str(user_id or ""),
        }
        try:
            self.save()
        except Exception as e:
            return {"ok": False, "error": "权限档落盘失败: %s" % str(e)[:120]}
        return {"ok": True, "level": level}

    def save(self):
        """**走统一出口**（X-16 批 B）：跨进程锁 + 原子替换 + 坏状态拒绝写入。"""
        write_state(self.path, _WRITER, _shape, self.data, reason="pa.permission.save")
        return self
