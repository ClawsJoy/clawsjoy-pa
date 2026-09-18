# -*- coding: utf-8 -*-
"""PA 线程/聊天 服务端持久化(2026-09-11): 跨浏览器/跨设备, 数据在服务端不在浏览器 localStorage。

2026-09-18（X-17 止损 · DS 拍、待老板追认）：**坏状态 fail-loud**。
此前 `load()` 把「文件存在但读不动」与「文件不存在」返回成**同一个空状态**，
下游 `POST /v9/pa/archive` 会拿它当**合并基线** ⇒ 一次写即清空历史归档与 threads
（受控复现：codex/2026-09-18-pa-engineering-self-audit.md 证据 5）。
现在：**不存在 ⇒ 空状态（新用户正常）；存在但损坏 ⇒ 抛 ThreadStoreCorrupt，绝不回落空状态**。

2026-09-18（X-17② 批 2 · DS 拍 A）：**写也走统一出口** —— `save()` 经
`core/pa/state_out.write_state`（跨进程锁 + 原子替换 + `on_corrupt="refuse"`）。
业务结构判据（`threads` 需为 list）**留 PA 侧**，不给出口加结构校验回调（DS 拍①）。
"""
from pathlib import Path

from core.pa.state_out import PAStateCorrupt, read_state, write_state


class ThreadStoreCorrupt(Exception):
    """线程状态文件**存在但不可用**（损坏/结构不符）⇒ 必须 fail-loud，不得静默回落默认值。"""

    def __init__(self, path, reason):
        self.path = str(path)
        self.reason = str(reason)
        super().__init__('线程状态文件损坏，拒绝按空状态继续：%s（%s）' % (self.path, self.reason))


#: 写者标识（进出口的写者归属台账；供 detect_uninstrumented 识别绕过出口的写者）
_WRITER = "core/pa/threads.py"


def _empty():
    """**新用户**的空状态 —— 只在「文件不存在」时用；文件存在但不可用 ⇒ 抛，绝不回落它。"""
    return {'mode': 'chat', 'threads': [], 'activeThread': None}


def _shape(doc):
    """**PA 侧业务结构判据**（X-17② 批 2 · DS 拍①：判据留 PA 侧，不给出口加回调）。

    出口只认「顶层是不是 dict」；`threads` 是不是 list 只有 PA 知道 ⇒ 判据必须在这里。
    """
    if not isinstance(doc.get('threads'), list):
        return False, 'threads 需为 list'
    return True, ''


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
            return _empty()
        try:
            return read_state(p, _WRITER, _shape)
        except PAStateCorrupt as _e:
            raise ThreadStoreCorrupt(p, _e.reason)

    def save(self, user_id, state):
        """**走统一出口**（X-17② 批 2）：跨进程锁 + 原子替换 + **坏状态拒绝写入**。

        契约：坏状态 ⇒ 抛 `ThreadStoreCorrupt`，**活文件一个字节不动**
        （不得静默回落空基线 —— 那正是 X-17「一次写即清空历史归档」的根因）。
        """
        p = self._path(user_id)
        try:
            write_state(p, _WRITER, _shape, state or {}, reason="pa.threads.save")
        except PAStateCorrupt as _e:
            raise ThreadStoreCorrupt(p, _e.reason)
        return {"ok": True, "path": str(p)}
