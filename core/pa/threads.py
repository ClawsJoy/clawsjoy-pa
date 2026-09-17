# -*- coding: utf-8 -*-
"""PA 线程/聊天 服务端持久化(2026-09-11): 跨浏览器/跨设备, 数据在服务端不在浏览器 localStorage。"""
import json
from pathlib import Path


class ThreadStore:
    def __init__(self, data_dir="data/v9/pa"):
        self.dir = Path(data_dir)
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, user_id):
        return self.dir / ("threads_%s.json" % str(user_id or "default"))

    def load(self, user_id):
        p = self._path(user_id)
        if p.exists():
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(d, dict) and isinstance(d.get("threads"), list):
                    return d
            except Exception:
                pass
        return {"mode": "chat", "threads": [], "activeThread": None}

    def save(self, user_id, state):
        p = self._path(user_id)
        p.write_text(json.dumps(state or {}, ensure_ascii=False, indent=1), encoding="utf-8")
        return {"ok": True, "path": str(p)}
