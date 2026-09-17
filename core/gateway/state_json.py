# -*- coding: utf-8 -*-
"""批220 · `.agent_state.json` 的**原子写 + 容错读**（修「Extra data」损坏根因）。

根因（2026-09-16 实锤）：`write_gate._persist_pending_writes` 与 `audit` 的审批/escalation 落盘
都是「读整个 json → 改 → `write_text` 覆盖」，**无锁、非原子**；并发写者交错 ⇒ 文件里出现
**两份 JSON 串接** ⇒ 之后 `json.loads` 抛 `Extra data: line 258 column 2 (char 7145)`
⇒ 该线程每个回合直接报错，前端表现「新内容不渲染、旧内容还在」（localStorage 兜底）。

本模块提供：
  · read_json(path)：**容错读** —— 解析失败时抢救**第一份合法 JSON**（raw_decode），不抛；
  · update_json(path, mutate)：**进程内按路径加锁** + 容错读 + mutate(dict) +
    **临时文件 + fsync + os.replace 原子替换**（杜绝半截/串接写入）。
"""
import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any, Callable, Dict

_LOCKS: Dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()


def _lock_for(path: Path) -> threading.Lock:
    """同一路径**共用一个进程内锁**（并发写不再交错）。"""
    key = str(path)
    with _LOCKS_GUARD:
        lk = _LOCKS.get(key)
        if lk is None:
            lk = threading.Lock()
            _LOCKS[key] = lk
        return lk


def read_json(path) -> Dict[str, Any]:
    """容错读：坏文件**抢救第一份合法 JSON**；彻底读不出 ⇒ 返回 {}（不抛）。"""
    p = Path(str(path))
    if not p.exists():
        return {}
    try:
        raw = p.read_text(encoding="utf-8")
    except Exception:
        return {}
    try:
        d = json.loads(raw)
        return d if isinstance(d, dict) else {}
    except Exception:
        try:
            d, end = json.JSONDecoder().raw_decode(raw)
            if isinstance(d, dict):
                print("[STATE_JSON] 容错读：抢救出第一份 JSON（%s，丢弃尾部 %d 字符）" % (p.name, len(raw) - end))
                return d
        except Exception:
            pass
        print("[STATE_JSON] 容错读：无法解析（%s）⇒ 返回空状态，不抛" % p)
        return {}


def update_json(path, mutate: Callable[[Dict[str, Any]], None]) -> Dict[str, Any]:
    """加锁 + 容错读 + mutate + **原子替换**写回；返回写回后的 dict。"""
    p = Path(str(path))
    with _lock_for(p):
        d = read_json(p)
        mutate(d)
        p.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix="." + p.name + ".", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(d, fh, ensure_ascii=False, indent=2)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, p)   # 原子替换：读侧永远看到完整文件
        finally:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except Exception:
                    pass
        return d
