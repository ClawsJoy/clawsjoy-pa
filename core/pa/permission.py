# -*- coding: utf-8 -*-
"""PA 权限档（能改）2026-09-11：cfgPerm 后端持久化。

值白名单：只读 / 标准 / 高(需确认)。
存储：data/v9/pa/permission.json（可用 env PA_PERMISSION_PATH / PA_DATA_DIR 覆盖）。

主权约束：本文件只能被 pa.html 前端（老板在场）经 /v9/pa/permission 路由写入；
PA agent 直写被 ForbiddenGuard._CONFIG_FILES 硬拒（agent_manual §4.2）。
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

LEVELS = ("只读", "标准", "高(需确认)")
DEFAULT_LEVEL = "标准"


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
        if self.path.exists():
            try:
                d = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(d, dict) and d.get("level") in LEVELS:
                    self.data = d
            except Exception:
                pass
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
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=1), encoding="utf-8")
        return self
