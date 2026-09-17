"""P2b-A: 双读对比 — 补记守卫注入 + 投影一致性"""
import sys, os
sys.path.insert(0, ".")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@127.0.0.1:5432/test")

import pytest
from core.gateway.session_log import SessionLog, log_event, get_session_log, EV_USER_MESSAGE


@pytest.fixture(autouse=True)
def _clean(monkeypatch, tmp_path):
    import core.gateway.session_log as sl
    monkeypatch.setattr(sl, "_logs", {})
    yield tmp_path


def test_guard_message_projected_with_role(tmp_path):
    """守卫注入 system 消息 → user_message 事件带 role → 投影为 system"""
    log = SessionLog("s1", base_dir=tmp_path)
    log.append(EV_USER_MESSAGE, {"role": "system", "content": "[系统] 检测到重复操作", "source": "guard"})
    msgs = log.derive_messages()
    assert msgs[0]["role"] == "system"
    assert "[系统]" in msgs[0]["content"]


def test_backfill_logic(tmp_path):
    """模拟双读对比补记: 内存多出的消息被补记"""
    log = SessionLog("s2", base_dir=tmp_path)
    # 模拟: 内存有 3 条, 日志只记录了 1 条
    log.append(EV_USER_MESSAGE, {"role": "user", "content": "原始消息"})
    messages = [
        {"role": "user", "content": "原始消息"},
        {"role": "system", "content": "[系统] 审计未通过"},
        {"role": "tool", "tool_call_id": "c1", "content": "工具结果"},
    ]
    projected = log.derive_messages()
    mem_count, proj_count = len(messages), len(projected)
    assert mem_count == 3 and proj_count == 1
    # 补记: 尾部未记录消息
    for _m in messages[proj_count:]:
        if _m.get("role") in ("system", "user", "tool"):
            log.append(EV_USER_MESSAGE if _m.get("role") in ("system", "user") else "tool_result",
                       {"role": _m.get("role"), "content": str(_m.get("content", "")),
                        "call_id": _m.get("tool_call_id", ""), "source": "guard_backfill"})
    proj2 = log.derive_messages()
    assert len(proj2) == 3, f"补记后投影应 3 条: {proj2}"
    assert proj2[1]["role"] == "system"
    assert proj2[2]["role"] == "tool"


def test_consistency_compare_no_diff(tmp_path):
    """数量一致 → 内容对比无差异"""
    log = SessionLog("s3", base_dir=tmp_path)
    log.append(EV_USER_MESSAGE, {"role": "user", "content": "请写文件"})
    log.append(EV_USER_MESSAGE, {"role": "system", "content": "[系统] 请收敛"})
    messages = [
        {"role": "user", "content": "请写文件"},
        {"role": "system", "content": "[系统] 请收敛"},
    ]
    projected = log.derive_messages()
    assert len(messages) == len(projected)
    diff = [i for i, (_a, _b) in enumerate(zip(messages, projected))
            if _a.get("role") != _b.get("role") or str(_a.get("content", "")) != str(_b.get("content", ""))]
    assert not diff, f"应无差异: {diff}"
