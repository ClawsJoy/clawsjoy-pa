# -*- coding: utf-8 -*-
"""write-gate 归位回归：主文件经 import * 引用的 write-gate 状态必须与 write_gate 模块同一对象。

防「双份分裂」复发（历史 bug：主文件与 shared_state 各持一份 dict，
_clean_session_context 清一套、v9_agent_chat 读另一套 → 清上下文不生效）。
"""

import sys

sys.path.insert(0, ".")


def test_write_gate_state_not_split():
    import agent_gateway_enhanced as main
    import core.gateway.write_gate as wg

    assert main._pending_writes is wg._pending_writes, "pending_writes 双份分裂！"
    assert main._plan_pending is wg._plan_pending, "plan_pending 双份分裂！"
    assert main._PENDING_TTL == wg._PENDING_TTL

    assert main._get_pending_lock is wg._get_pending_lock
    # _pending_lock 会被 _get_pending_lock() 重绑定(锁工厂)，main 的 import 副本是过期值；
    # 正确断言：两个模块经函数拿到同一个锁对象（锁无分裂）。
    assert main._get_pending_lock() is wg._get_pending_lock(), "pending_lock 经工厂分裂！"
    assert main._persist_pending_writes is wg._persist_pending_writes
    assert main._pending_cleanup is wg._pending_cleanup
    assert main._clear_pending_write is wg._clear_pending_write


def test_session_cleaner_shares_write_gate_state():
    import core.gateway.session_cleaner as sc
    import core.gateway.write_gate as wg

    # session_cleaner 经 from ... import 引用的 write-gate 状态必须同一对象（防分裂）
    assert sc._pending_writes is wg._pending_writes, "session_cleaner pending_writes 分裂！"
    assert sc._plan_pending is wg._plan_pending, "session_cleaner plan_pending 分裂！"
    assert sc._get_pending_lock is wg._get_pending_lock


def test_session_id_resolver_shared_state():
    import agent_gateway_enhanced as main
    import core.gateway.shared_state as ss

    assert main._resolve_v9_session_id is ss._resolve_v9_session_id, "_resolve_v9_session_id 分裂！"


def test_write_gate_cleaner_registered_in_context():
    import core.gateway.write_gate as wg
    from core.os.context import get_v9_context

    cleaner = get_v9_context().get_opt("pending_writes_cleaner")
    assert cleaner is wg._clear_pending_write, "pending_writes_cleaner 未指向 write_gate._clear_pending_write"
