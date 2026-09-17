"""H9: user_messages 沙箱镜像历史回填 — 只补不删、幂等、阈值"""
import sys, json
sys.path.insert(0, ".")
import pytest
from pathlib import Path

from core.gateway import archive as AR


def _mk_entry(i, sid):
    return json.dumps({"role": "user", "content": f"msg{i}", "session_id": sid, "agent_name": "", "ts": f"2026-08-15T00:00:{i:02d}"})


@pytest.fixture
def _clean(session_id="bf_s1"):
    """清掉测试 session 的正本与镜像，测试后恢复现场"""
    sid = session_id
    live = Path("data/v8/user_messages") / f"{sid}.jsonl"
    mirror = Path("data/projects") / "bf_u" / sid / "clawsjoy_dev" / "data" / "v8" / "user_messages" / f"{sid}.jsonl"
    live_bak = live.read_text(encoding="utf-8") if live.exists() else None
    mirror_bak = mirror.read_text(encoding="utf-8") if mirror.exists() else None
    live.unlink(missing_ok=True)
    mirror.unlink(missing_ok=True)
    yield sid
    if live_bak is not None:
        live.write_text(live_bak, encoding="utf-8")
    else:
        live.unlink(missing_ok=True)
    if mirror_bak is not None:
        mirror.write_text(mirror_bak, encoding="utf-8")
    else:
        mirror.unlink(missing_ok=True)


def test_backfill_fills_missing(_clean):
    """正本 200 行、镜像 50 行（差 150 > 100）→ 补齐 150 行"""
    sid = _clean
    live = Path("data/v8/user_messages") / f"{sid}.jsonl"
    mirror = Path("data/projects") / "bf_u" / sid / "clawsjoy_dev" / "data" / "v8" / "user_messages" / f"{sid}.jsonl"
    live.parent.mkdir(parents=True, exist_ok=True)
    with open(live, "w", encoding="utf-8") as f:
        for i in range(200):
            f.write(_mk_entry(i, sid) + "\n")
    mirror.parent.mkdir(parents=True, exist_ok=True)
    with open(mirror, "w", encoding="utf-8") as f:
        for i in range(50):
            f.write(_mk_entry(i, sid) + "\n")
    n = AR.backfill_user_message_mirror("bf_u", sid)
    assert n == 150
    with open(mirror, encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 200, f"镜像应 200 行，实际 {len(lines)}"


def test_backfill_idempotent(_clean):
    """幂等：第二次调用不重复追加"""
    sid = _clean
    live = Path("data/v8/user_messages") / f"{sid}.jsonl"
    mirror = Path("data/projects") / "bf_u" / sid / "clawsjoy_dev" / "data" / "v8" / "user_messages" / f"{sid}.jsonl"
    live.parent.mkdir(parents=True, exist_ok=True)
    with open(live, "w", encoding="utf-8") as f:
        for i in range(120):
            f.write(_mk_entry(i, sid) + "\n")
    mirror.parent.mkdir(parents=True, exist_ok=True)
    with open(mirror, "w", encoding="utf-8") as f:
        for i in range(10):
            f.write(_mk_entry(i, sid) + "\n")
    AR.backfill_user_message_mirror("bf_u", sid)
    n2 = AR.backfill_user_message_mirror("bf_u", sid)
    assert n2 == 0, "第二次不应再补"
    with open(mirror, encoding="utf-8") as f:
        assert len(f.readlines()) == 120


def test_backfill_below_threshold(_clean):
    """差异 ≤ 阈值（100）→ 不补"""
    sid = _clean
    live = Path("data/v8/user_messages") / f"{sid}.jsonl"
    mirror = Path("data/projects") / "bf_u" / sid / "clawsjoy_dev" / "data" / "v8" / "user_messages" / f"{sid}.jsonl"
    live.parent.mkdir(parents=True, exist_ok=True)
    with open(live, "w", encoding="utf-8") as f:
        for i in range(105):
            f.write(_mk_entry(i, sid) + "\n")
    mirror.parent.mkdir(parents=True, exist_ok=True)
    with open(mirror, "w", encoding="utf-8") as f:
        for i in range(50):
            f.write(_mk_entry(i, sid) + "\n")
    n = AR.backfill_user_message_mirror("bf_u", sid)
    assert n == 0, f"差 55 ≤ 100 不应补，实际 {n}"


def test_backfill_mirror_only_no_delete(_clean):
    """镜像比正本多 → 不删（只补不删）"""
    sid = _clean
    live = Path("data/v8/user_messages") / f"{sid}.jsonl"
    mirror = Path("data/projects") / "bf_u" / sid / "clawsjoy_dev" / "data" / "v8" / "user_messages" / f"{sid}.jsonl"
    live.parent.mkdir(parents=True, exist_ok=True)
    with open(live, "w", encoding="utf-8") as f:
        for i in range(10):
            f.write(_mk_entry(i, sid) + "\n")
    mirror.parent.mkdir(parents=True, exist_ok=True)
    with open(mirror, "w", encoding="utf-8") as f:
        for i in range(50):
            f.write(_mk_entry(i, sid) + "\n")
    n = AR.backfill_user_message_mirror("bf_u", sid)
    assert n == 0
    with open(mirror, encoding="utf-8") as f:
        assert len(f.readlines()) == 50, "镜像不应被删除"
