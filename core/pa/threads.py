# -*- coding: utf-8 -*-
"""PA 线程/聊天 服务端持久化(2026-09-11): 跨浏览器/跨设备, 数据在服务端不在浏览器 localStorage。

2026-09-18（X-17 止损 · DS 拍、待老板追认）：**坏状态 fail-loud**。
此前 `load()` 把「文件存在但读不动」与「文件不存在」返回成**同一个空状态**，
下游 `POST /v9/pa/archive` 会拿它当**合并基线** ⇒ 一次写即清空历史归档与 threads
（受控复现：codex/2026-09-18-pa-engineering-self-audit.md 证据 5）。
现在：**不存在 ⇒ 空状态（新用户正常）；存在但损坏 ⇒ 抛 ThreadStoreCorrupt，绝不回落空状态**。
"""
import json
from pathlib import Path


class ThreadStoreCorrupt(Exception):
    """线程状态文件**存在但不可用**（损坏/结构不符）⇒ 必须 fail-loud，不得静默回落默认值。"""

    def __init__(self, path, reason):
        self.path = str(path)
        self.reason = str(reason)
        super().__init__('线程状态文件损坏，拒绝按空状态继续：%s（%s）' % (self.path, self.reason))


class ThreadStore:
    def __init__(self, data_dir="data/v9/pa"):
        self.dir = Path(data_dir)
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, user_id):
        return self.dir / ("threads_%s.json" % str(user_id or "default"))

    def load(self, user_id):
        """**不存在 ⇒ 空状态；存在但损坏 ⇒ 抛 ThreadStoreCorrupt**（不得静默回落空状态）。"""
        p = self._path(user_id)
        if not p.exists():
            return {'mode': 'chat', 'threads': [], 'activeThread': None}
        try:
            raw = p.read_text(encoding='utf-8')
        except Exception as _e:
            raise ThreadStoreCorrupt(p, '读取失败：%s' % str(_e)[:80])
        try:
            d = json.loads(raw)
        except Exception as _e:
            raise ThreadStoreCorrupt(p, 'JSON 解析失败：%s' % str(_e)[:80])
        if not isinstance(d, dict) or not isinstance(d.get('threads'), list):
            raise ThreadStoreCorrupt(p, '结构不符（需 dict 且 threads 为 list）')
        return d

    def save(self, user_id, state):
        p = self._path(user_id)
        p.write_text(json.dumps(state or {}, ensure_ascii=False, indent=1), encoding="utf-8")
        return {"ok": True, "path": str(p)}
