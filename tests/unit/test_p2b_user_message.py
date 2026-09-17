"""P2b 修复: 用户消息写入日志 → derive_messages 投影"""
import sys, os
sys.path.insert(0, ".")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@127.0.0.1:5432/test")

import pytest
from pathlib import Path
from core.gateway.session_log import SessionLog


@pytest.fixture(autouse=True)
def _clean(monkeypatch, tmp_path):
    import core.gateway.session_log as sl
    monkeypatch.setattr(sl, "_logs", {})
    _dir = Path("data/session_logs")
    if _dir.exists():
        for _f in _dir.glob("*.jsonl"):
            try:
                _f.unlink()
            except Exception:
                pass
    yield tmp_path
    if _dir.exists():
        for _f in _dir.glob("*.jsonl"):
            try:
                _f.unlink()
            except Exception:
                pass


def _ensure_user_logged(log, messages):
    """模拟 bridge/exec 的幂等写入逻辑"""
    proj_user = [m.get("content") for m in log.derive_messages() if m.get("role") == "user"]
    for m in messages:
        if m.get("role") == "user" and m.get("content") not in proj_user:
            log.append("user_message", {"role": "user", "content": str(m.get("content", "")), "source": "user_input"})


def test_user_message_projected(tmp_path):
    """用户消息写日志 → 投影出 user 消息"""
    log = SessionLog("u1", base_dir=tmp_path)
    messages = [{"role": "user", "content": "请创建 hello.txt"}]
    _ensure_user_logged(log, messages)
    proj = log.derive_messages()
    assert len(proj) == 1
    assert proj[0]["role"] == "user"
    assert proj[0]["content"] == "请创建 hello.txt"


def test_idempotent_no_duplicate(tmp_path):
    """幂等: 同一用户消息不重复写"""
    log = SessionLog("u2", base_dir=tmp_path)
    messages = [{"role": "user", "content": "消息"}]
    _ensure_user_logged(log, messages)
    _ensure_user_logged(log, messages)  # 再跑一次
    assert len(log.derive_messages()) == 1


def test_multiple_user_messages(tmp_path):
    """多条用户消息都写日志"""
    log = SessionLog("u3", base_dir=tmp_path)
    messages = [{"role": "user", "content": "第一条"}, {"role": "user", "content": "第二条"}]
    _ensure_user_logged(log, messages)
    proj = log.derive_messages()
    assert len(proj) == 2
    assert [m["content"] for m in proj] == ["第一条", "第二条"]


def test_file_persisted(tmp_path):
    """JSONL 落盘含 user_message"""
    log = SessionLog("u4", base_dir=tmp_path)
    messages = [{"role": "user", "content": "持久化测试"}]
    _ensure_user_logged(log, messages)
    content = log.log_file.read_text(encoding="utf-8")
    assert "user_message" in content
    assert "持久化测试" in content
