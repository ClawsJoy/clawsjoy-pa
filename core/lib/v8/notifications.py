# -*- coding: utf-8 -*-
# V8 通知中心后端模块。
#
# 提供 4 个幂等 REST 接口所需的纯函数：
#   - list_notifications: 读取通知列表（含已读状态）
#   - mark_read: 单条标记已读（幂等）
#   - mark_all_read: 全部标记已读（幂等）
#   - unread_count: 未读数
#
# 数据文件：
#   - data/v8/notifications.json       : notify_boss 追加写入的通知本体（本模块只读）
#   - data/v8/notifications_read.json  : 已读 ID 集合（运行时自动创建）
#
# 设计要点：
#   - 追加写与读状态分离，避免写冲突；
#   - (ts, id) 稳定排序，limit 上限钳制；
#   - 读写均加线程锁，写文件先写临时文件再原子替换。

import builtins
import json
import os
import threading
from typing import Dict, List

# ---------------------------------------------------------------------------
# 路径与常量
# ---------------------------------------------------------------------------

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# core/lib/v8/notifications.py -> 上三级为项目根目录
_PROJECT_ROOT = os.path.abspath(os.path.join(_BASE_DIR, "..", "..", ".."))

_NOTIFICATIONS_PATH = os.path.join(_PROJECT_ROOT, "data", "v8", "notifications.json")
_READ_PATH = os.path.join(_PROJECT_ROOT, "data", "v8", "notifications_read.json")

_MAX_LIMIT = 100
_DEFAULT_LIMIT = 50

_lock = threading.RLock()


# ---------------------------------------------------------------------------
# 底层读写
# ---------------------------------------------------------------------------

def _load_notifications() -> List[Dict]:
    # 读取通知本体列表；文件不存在或损坏时返回空列表。
    if not os.path.exists(_NOTIFICATIONS_PATH):
        return []
    try:
        with open(_NOTIFICATIONS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, builtins.list):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return []


def _load_read_ids() -> set:
    # 读取已读 ID 集合；文件不存在或损坏时返回空集合。
    if not os.path.exists(_READ_PATH):
        return set()
    try:
        with open(_READ_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, builtins.list):
            return set(str(x) for x in data)
        if isinstance(data, dict):
            return set(str(x) for x in data.get("read_ids", []))
    except (json.JSONDecodeError, OSError):
        pass
    return set()


def _save_read_ids(read_ids: set) -> None:
    # 持久化已读 ID 集合：先写临时文件，再原子替换。
    os.makedirs(os.path.dirname(_READ_PATH), exist_ok=True)
    tmp = _READ_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(sorted(read_ids), f, ensure_ascii=False, indent=2)
    os.replace(tmp, _READ_PATH)


def _normalize(items: List[Dict], read_ids: set) -> List[Dict]:
    # 归一化通知条目，附加 read 状态字段。
    normalized = []
    for it in items:
        if not isinstance(it, dict):
            continue
        nid = str(it.get("id", ""))
        normalized.append({
            "id": nid,
            "ts": it.get("ts", 0),
            "time": it.get("time", ""),
            "message": it.get("message", ""),
            "level": it.get("level", "info"),
            "event_type": it.get("event_type", "general"),
            "detail": it.get("detail", ""),
            "extra": it.get("extra", {}),
            "read": nid in read_ids,
        })
    return normalized


# ---------------------------------------------------------------------------
# #8 SSE 主动推送: notify_boss 广播新通知给订阅者(EventSource)
# ---------------------------------------------------------------------------

_sse_subscribers = []   # list[queue.Queue]
_sse_lock = threading.RLock()


def subscribe_sse():
    """SSE 订阅: 返回 (queue, 退订函数)。queue 满则丢弃最旧(不阻塞通知写入)。"""
    import queue as _q
    q = _q.Queue(maxsize=100)
    with _sse_lock:
        _sse_subscribers.append(q)

    def _unsub():
        with _sse_lock:
            if q in _sse_subscribers:
                _sse_subscribers.remove(q)
    return q, _unsub


def broadcast_notification(item: Dict) -> None:
    """广播新通知给所有 SSE 订阅者(满队列丢最旧, 防阻塞 notify_boss)。"""
    with _sse_lock:
        # 注意: 模块底部 list = list_notifications 别名遮蔽内置 list → 用推导式
        subs = [s for s in _sse_subscribers]
    for q in subs:
        try:
            q.put_nowait(item)
        except Exception:
            try:
                while True:
                    q.get_nowait()
            except Exception:
                pass
            try:
                q.put_nowait(item)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# 对外接口
# ---------------------------------------------------------------------------

def list_notifications(limit: int = _DEFAULT_LIMIT, offset: int = 0) -> Dict:
    # 返回通知列表（含已读状态），按 (ts, id) 降序稳定排序。
    with _lock:
        items = _load_notifications()
        read_ids = _load_read_ids()

    normalized = _normalize(items, read_ids)
    normalized.sort(key=lambda x: (x["ts"], x["id"]), reverse=True)

    limit = max(1, min(int(limit), _MAX_LIMIT))
    offset = max(0, int(offset))
    page = normalized[offset:offset + limit]
    unread = sum(1 for x in normalized if not x["read"])

    return {
        "items": page,
        "total": len(normalized),
        "unread_count": unread,
        "limit": limit,
        "offset": offset,
    }


def mark_read(notification_id: str) -> Dict:
    # 单条标记已读（幂等）。
    nid = str(notification_id)
    with _lock:
        read_ids = _load_read_ids()
        already = nid in read_ids
        read_ids.add(nid)
        _save_read_ids(read_ids)
    return {"id": nid, "read": True, "already_read": already}


def mark_all_read() -> Dict:
    # 全部标记已读（幂等）。
    with _lock:
        items = _load_notifications()
        read_ids = _load_read_ids()
        before = len(read_ids)
        read_ids.update(
            str(it.get("id", ""))
            for it in items
            if isinstance(it, dict) and it.get("id")
        )
        _save_read_ids(read_ids)
        added = len(read_ids) - before
    return {"read": True, "marked": added, "total_read_ids": len(read_ids)}


def unread_count() -> Dict:
    # 返回未读数。
    with _lock:
        items = _load_notifications()
        read_ids = _load_read_ids()
    unread = sum(
        1 for it in items
        if isinstance(it, dict) and str(it.get("id", "")) not in read_ids
    )
    return {"unread_count": unread, "total": len(items)}


# 计划约定的核心函数名别名
list = list_notifications  # noqa: A001
