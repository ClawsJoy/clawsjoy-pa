"""#19 错误聚合告警回归测试: 同类失败 1h 窗口 ≥5 次 → 聚合汇总告警 + 抑制逐条(不刷屏)"""
import json
import sys

sys.path.insert(0, ".")
import pytest


@pytest.fixture(autouse=True)
def _iso(monkeypatch, tmp_path):
    """隔离: notifications 输出路径 + 聚合状态 + SSE 订阅"""
    import core.gateway.sandbox_util as su
    import core.lib.v8.notifications as nf

    monkeypatch.setattr(su, "_NOTIFY_OUTPUT_PATH", str(tmp_path / "data" / "v8" / "notifications.json"))
    monkeypatch.setattr(nf, "_NOTIFICATIONS_PATH", str(tmp_path / "data" / "v8" / "notifications.json"))
    monkeypatch.setattr(nf, "_READ_PATH", str(tmp_path / "data" / "v8" / "notifications_read.json"))
    monkeypatch.setattr(nf, "_sse_subscribers", [])
    su._agg_reset_all()
    yield tmp_path


def _items(tmp_path):
    p = tmp_path / "data" / "v8" / "notifications.json"
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


def test_agg_below_threshold_unchanged(tmp_path):
    """未达阈值(1-4次): 行为不变, 逐条落盘, 无聚合标记"""
    from core.gateway.sandbox_util import notify_boss

    for i in range(4):
        notify_boss(event_type="turn_end", message=f"V9 任务回合异常: error — 第{i}次失败", detail=f"turn_id={i}", level="error")
    items = _items(tmp_path)
    assert len(items) == 4, f"未达阈值应逐条落盘: {len(items)}"
    assert all(not it["extra"].get("aggregated") for it in items), "未达阈值不应聚合"


def test_agg_trigger_and_suppress(tmp_path):
    """达到阈值(第5次) → 聚合告警; 第6-9次抑制(不新增落盘); 第10次(10min后)刷新"""
    import time as _t

    from core.gateway.sandbox_util import _AGG_REFRESH, notify_boss

    # 前 4 条逐条
    for i in range(4):
        notify_boss(event_type="turn_end", message=f"V9 任务回合异常: error — 失败{i}", detail=f"turn_id={i}", level="error")
    assert len(_items(tmp_path)) == 4
    # 第 5 条: 聚合触发
    notify_boss(event_type="turn_end", message="V9 任务回合异常: error — 失败4", detail="turn_id=4", level="error")
    items = _items(tmp_path)
    assert len(items) == 5, f"第5次应落聚合告警: {len(items)}"
    agg = items[-1]
    assert agg["extra"].get("aggregated") is True, "第5次应为聚合告警"
    assert agg["extra"].get("agg_count") == 5
    assert "聚合" in agg["message"] or "[聚合]" in agg["message"], f"应含聚合标记: {agg['message']}"
    assert "5 次" in agg["message"], f"汇总应含次数: {agg['message']}"
    # 第 6-9 次: 抑制(不新增)
    for i in range(5, 10):
        notify_boss(event_type="turn_end", message=f"V9 任务回合异常: error — 失败{i}", detail=f"turn_id={i}", level="error")
    items = _items(tmp_path)
    assert len(items) == 5, f"聚合后应抑制逐条: {len(items)} (实际 {len(items)})"
    # 第 10 次: 模拟超过刷新间隔 → 再发一条汇总刷新
    import core.gateway.sandbox_util as su

    with su._get_agg_lock():
        for _st in su._agg_state.values():
            _st["last_notify_ts"] = _t.time() - _AGG_REFRESH - 1
    notify_boss(event_type="turn_end", message="V9 任务回合异常: error — 失败10", detail="turn_id=10", level="error")
    items = _items(tmp_path)
    assert len(items) == 6, f"刷新间隔后应再发一条汇总: {len(items)} (实际 {len(items)})"
    assert items[-1]["extra"].get("agg_count", 0) >= 10, "刷新汇总应含最新计数"


def test_agg_window_reset(tmp_path):
    """窗口(1h)过期 → 计数重置, 重新逐条"""
    import time as _t

    import core.gateway.sandbox_util as su
    from core.gateway.sandbox_util import _AGG_WINDOW, notify_boss

    for i in range(5):
        notify_boss(event_type="tool_fail", message="沙箱越权拦截", detail=f"i={i}", level="error")
    assert len(_items(tmp_path)) == 5
    assert _items(tmp_path)[-1]["extra"].get("aggregated") is True
    # 推进时间超过窗口
    with su._get_agg_lock():
        for _st in su._agg_state.values():
            _st["first_ts"] = _t.time() - _AGG_WINDOW - 1
    notify_boss(event_type="tool_fail", message="沙箱越权拦截", detail="i=5", level="error")
    items = _items(tmp_path)
    assert len(items) == 6, "新窗口首条应正常落盘"
    assert items[-1]["extra"].get("aggregated") is not True, "新窗口首条不应聚合"


def test_agg_distinct_keys(tmp_path):
    """不同分类 key(不同 event_type/前缀)互不干扰"""
    from core.gateway.sandbox_util import notify_boss

    for i in range(5):
        notify_boss(event_type="turn_end", message="V9 任务回合异常: error", detail=f"t={i}", level="error")
    for i in range(4):
        notify_boss(event_type="cost_limit", message="DeepSeek 今日费用超上限", detail=f"c={i}", level="warn")
    items = _items(tmp_path)
    assert len(items) == 9, "不同 key 各自计数, 互不聚合"
    agg_count = sum(1 for it in items if it["extra"].get("aggregated"))
    assert agg_count == 1, f"只有 turn_end 达到阈值聚合: {agg_count}"


def test_agg_key_prefix_stability():
    """聚合 key: 消息前缀稳定, 带数字/session detail 不分裂"""
    from core.gateway.sandbox_util import _agg_key

    k1 = _agg_key("V9 任务回合异常: error — 写操作失败 (session=s1)", "turn_end")
    k2 = _agg_key("V9 任务回合异常: error — 越权拦截 (session=s2)", "turn_end")
    assert k1 == k2, "前缀应稳定: %s vs %s" % (k1, k2)
    k3 = _agg_key("DeepSeek 今日费用 12.34 超上限 20.0", "cost_limit")
    k4 = _agg_key("DeepSeek 今日费用 15.67 超上限 20.0", "cost_limit")
    assert k3 == k4, "数字 detail 不应分裂 key"
