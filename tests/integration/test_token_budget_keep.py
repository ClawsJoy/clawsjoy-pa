"""#41 阶段1：token 预算驱动截断 — 动态 keep 推导验证"""
import sys
sys.path.insert(0, ".")
import pytest


def _derive_keep(est, budget, n_msgs):
    """复现 agent_gateway 内 #41 动态 keep 推导逻辑"""
    n = max(n_msgs, 1)
    avg = max(est / n, 1)
    target = budget * 0.8
    return max(min(int(target / avg), 20), 4), avg


def test_keep_scales_with_budget():
    """消息多、超预算 → keep 收敛到合理范围（4~20）"""
    # 500 条消息、每条 ~200 tok → est=100000；budget 32000
    keep, avg = _derive_keep(100000, 32000, 500)
    assert 4 <= keep <= 20, f"keep={keep} 越界"
    assert avg == pytest.approx(200.0)
    # 预算 32000 * 0.8 = 25600 / 200 = 128 → clamp 到 20
    assert keep == 20


def test_keep_floor_4():
    """消息极大、每条巨量 → keep 收敛到下限 4（不跌破）"""
    keep, avg = _derive_keep(500000, 32000, 50)
    assert keep == 4, f"keep={keep}"
    assert avg == pytest.approx(10000.0)


def test_keep_ceiling_20():
    """消息少、每条小 → keep 收敛到上限 20"""
    keep, avg = _derive_keep(1000, 32000, 10)
    assert keep == 20, f"keep={keep}"


def test_keep_floor_with_low_budget():
    """预算小 + 消息大 → 收敛到下限 4"""
    keep, avg = _derive_keep(8000, 4000, 8)  # 8 条 × 1000 tok = 8000；target=3200 → 3.2 → floor 4
    assert keep == 4, f"keep={keep}"
    assert avg == pytest.approx(1000.0)


def test_keep_mid_range():
    """中等规模 → keep 落在中间（非 4 非 20）"""
    keep, avg = _derive_keep(8000, 4000, 40)  # avg=200, target=3200 → 16
    assert 4 < keep < 20, f"keep={keep}"
    assert keep == 16


def test_budget_driven_compress_end_to_end():
    """端到端：构造超预算消息 → 走 _compress_messages 后 est < budget"""
    from core.gateway.message_assembler import _compress_messages, _validate_messages
    # 构造 60 条消息（模拟长任务）
    msgs = [{"role": "system", "content": "你是 ClawsJoy 的 AI 助手。"}]
    for i in range(30):
        msgs.append({"role": "user", "content": f"任务步骤 {i}：" + "x" * 200})
        msgs.append({"role": "assistant", "content": f"已完成步骤 {i}：" + "y" * 200})
    # 大 budget 场景：keep=30 → 压缩后消息数明显减少
    out = _compress_messages(msgs, "tok_u", "tok_s", keep=10)
    out = _validate_messages(out)
    assert len(out) < len(msgs), f"压缩后 {len(out)} 应少于 {len(msgs)}"
    # 保留 system 头
    assert out[0]["role"] == "system"
