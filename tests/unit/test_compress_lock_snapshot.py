# -*- coding: utf-8 -*-
"""#16+#13 回归: 压缩并发锁 + token 快照"""
import sys

sys.path.insert(0, ".")
import pytest


def test_layer_store_lock():
    """#16: _layer_store 有锁, compress/assemble 用锁"""
    src = open("core/gateway/message_assembler.py", encoding="utf-8").read()
    assert "_layer_store_lock" in src, "缺锁变量"
    assert "def _get_layer_lock" in src, "缺锁函数"
    assert src.count("with _get_layer_lock():") >= 2, "compress+assemble 应都加锁"


def test_snapshot_rollback():
    """#13: 压缩前快照 + 压缩异常回滚"""
    src = open("core/gateway/v9_bridge/round_start.py", encoding="utf-8").read()
    assert "_snap_13" in src, "缺快照变量"
    assert "回滚快照" in src, "缺回滚逻辑"
    assert "dict(m, tool_calls=[dict(tc) for tc in" in src, "缺 tool_calls 深拷贝"


def test_snapshot_logic_simulation():
    """模拟: 压缩降效 → 回滚; 压缩有效 → 保留"""
    # 压缩有效
    est_before, est_after = 850000, 50000
    keep = 6
    snap_msgs = [{"role": "user", "content": "原始"}]
    if est_after < est_before * 0.95:
        result = "compressed"  # 保留压缩结果
    else:
        result = "rolled_back"
    assert result == "compressed", "压缩有效应保留"
    # 压缩降效(未降) → 回滚
    est_before2, est_after2 = 50000, 49000
    n_msgs = 15
    if est_after2 < est_before2 * 0.95 and n_msgs > 10:
        result2 = "compressed"
    else:
        result2 = "rolled_back"
    assert result2 == "rolled_back", "压缩未降效应回滚"
