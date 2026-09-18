# -*- coding: utf-8 -*-
"""PA 侧「状态出口」适配层（2026-09-18 · X-17② 批 2 · DS 拍）。

【为什么需要这一层】
X-17② 给通用出口 ``core/pes/state_integrity.StateFile`` 加了 ``on_corrupt="refuse"``
（坏状态 ⇒ 拒绝写入）。但**出口认识的「坏」只到「顶层是不是 dict」** —— 它不认识 PA 的
业务结构（``threads`` 的子键是不是 list、``items`` 是不是 list……）。
⇒ 若 PA 四处 store 直接调 ``update_runtime``，``36eeeaf`` 刚立的
「结构不符 ⇒ fail-loud」会被**静默降级**成「结构不符也照写」（经验库 L-16）。

【拍板口径（DS 2026-09-18 拍）】
 ① 业务结构判据**留在 PA 侧自检** —— **不给出口加「结构校验回调」**（出口保持通用、
    不耦合 PA 业务；与「五层」分层一致）；
 ② 判据范围用 **PA store 白名单**（不是 ``data/v9`` 全域 —— ``turn_registry`` 等
    store 的判据不同）。

【分层责任（谁负责什么，别混）】
  PA 侧（本模块）：**业务结构判据**（``shape`` 谓词）＋ 拒绝时抛 PA 自己的异常；
  出口侧（``StateFile``）：跨进程锁 ＋ 原子替换 ＋ 坏状态 refuse（**race 兜底**）。

【两条读语义（同 X-17①，不可漂移）】
  · 文件**不存在** ⇒ 空状态（新用户正常，**不是**损坏）；
  · 文件**存在但不可用**（读不动／JSON 非法／业务结构不符）⇒ **抛，绝不回落默认值**。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Tuple

from core.pes.state_integrity import StateFile


class PAStateCorrupt(Exception):
    """PA store 文件**存在但不可用**（损坏／业务结构不符）⇒ 必须 fail-loud。"""

    def __init__(self, path, reason):
        self.path = str(path)
        self.reason = str(reason)
        super().__init__("PA 状态文件不可用，拒绝按空状态继续：%s（%s）" % (self.path, self.reason))


#: 判据范围的 **PA store 白名单**（不是 ``data/v9`` 全域；DS 2026-09-18 拍口径②）
PA_STORES: Tuple[str, ...] = (
    "threads_<uid>.json",
    "ledger.json",
    "profile.json",
    "roster.json",
)


def _assert_shape(shape: Callable[[Dict[str, Any]], Tuple[bool, str]], doc, path) -> None:
    """跑一次 PA 侧业务结构判据；不通过 ⇒ 抛（**不静默**，也不回落默认值）。"""
    try:
        ok, reason = shape(doc if isinstance(doc, dict) else {})
    except Exception as e:  # 判据自身出错 ⇒ 也当「不可用」，不得当通过
        raise PAStateCorrupt(path, "结构判据执行失败：%s" % type(e).__name__)
    if not ok:
        raise PAStateCorrupt(path, "业务结构不符：%s" % (reason or "unknown"))


def read_state(path, writer: str, shape) -> Dict[str, Any]:
    """**PA 侧自检读**。不存在 ⇒ ``{}``；存在但不可用 ⇒ 抛 :class:`PAStateCorrupt`。

    返回的是**原始 doc**（含非业务键），由调用方自行取用。
    """
    p = Path(path)
    if not p.exists():
        return {}
    rep = StateFile(p, writer=writer).read()
    if rep.corrupted:
        raise PAStateCorrupt(p, "损坏（reason=%s）" % (rep.reason or "unknown"))
    doc = rep.data if isinstance(rep.data, dict) else {}
    _assert_shape(shape, doc, p)
    return doc


def write_state(path, writer: str, shape, new_doc: Dict[str, Any], reason: str = "") -> Dict[str, Any]:
    """**PA 侧写**：先自检读（业务结构判据）⇒ 再走出口 ``refuse`` 写。

    契约：返回**已落盘**的 doc。任一环不通过 ⇒ 抛 :class:`PAStateCorrupt`，
    **活文件一个字节不动**（这正是 X-17「静默数据丢失 + 假成交」的对治点）。
    """
    p = Path(path)
    if p.exists():
        # 业务结构判据必须在**写之前**跑；不通过 ⇒ 抛，绝不拿坏结构当合并基线。
        read_state(p, writer, shape)
    sf = StateFile(p, writer=writer)

    def _replace(doc):
        doc.clear()
        doc.update(new_doc or {})

    doc, rep = sf.update_runtime(_replace, reason=reason or "pa.state.write", on_corrupt="refuse")
    if not rep.written:
        # race 兜底：自检读到写之间文件变坏 ⇒ 出口拒绝写（原文件已隔离，此处一字未写）。
        raise PAStateCorrupt(p, "坏状态 ⇒ 出口拒绝写入（reason=%s）" % (rep.reason or "unknown"))
    return doc
