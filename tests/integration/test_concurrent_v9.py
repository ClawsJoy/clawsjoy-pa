"""#9 并发压力测试: 多 session 并行 / 同 session 串行 / guard 锁安全 / session_log JSONL 不损坏"""
import json
import os
import sys
import threading

sys.path.insert(0, ".")
import pytest


@pytest.fixture(autouse=True)
def _iso(monkeypatch, tmp_path):
    """隔离: session_log 注册表(磁盘隔离) + 共享状态清零"""
    import core.gateway.goal_state as gs
    import core.gateway.session_log as sl
    import core.gateway.shared_state as ss
    import core.gateway.tool_router as tr

    monkeypatch.setattr(sl, "_logs", {})
    # 注意: tool_router 顶层 import 绑定的是原 dict 对象 → 须同对象替换(清空原地亦可)
    _new_cf = {}
    monkeypatch.setattr(ss, "_consecutive_failures", _new_cf)
    monkeypatch.setattr(tr, "_consecutive_failures", _new_cf)
    _new_pb = {}
    monkeypatch.setattr(ss, "_paused_breakpoints", _new_pb)
    monkeypatch.setattr(tr, "_paused_breakpoints", _new_pb)
    monkeypatch.setattr(ss, "_cancel_flags", {})
    monkeypatch.setattr(gs, "_goals", {})
    _orig = sl.get_session_log

    def _get_iso(sid, base_dir=None):
        return _orig(sid, base_dir=tmp_path)

    monkeypatch.setattr(sl, "get_session_log", _get_iso)
    yield tmp_path


def _write_events(sid, n, base, ev_type="tool_result", tid=0):
    """连续写 n 条事件(模拟子任务回合)"""
    from core.gateway.session_log import log_event

    for i in range(n):
        log_event(
            sid,
            ev_type,
            {"name": "read_file", "call_id": f"{sid}-c{i}", "content": json.dumps({"i": i}), "success": True},
            turn_id=tid,
            step_id=0,
        )
        base.joinpath("done").mkdir(exist_ok=True) if False else None
    return n


def _check_jsonl_intact(path, expect_lines=None):
    """校验 JSONL 每行可解析、行数符合预期"""
    if not path.exists():
        return 0, False
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    ok = True
    for l in lines:
        try:
            ev = json.loads(l)
            if "seq" not in ev or "type" not in ev:
                ok = False
        except Exception:
            ok = False
    if expect_lines is not None and len(lines) != expect_lines:
        ok = False
    return len(lines), ok


def test_three_concurrent_sessions(tmp_path):
    """3 路并发子任务(不同 session): JSONL 各自完整, 互不串扰"""
    sessions = [f"conc_sess_{i}" for i in range(3)]
    errs = []

    def _worker(sid, n):
        try:
            _write_events(sid, n, tmp_path)
        except Exception as e:
            errs.append(str(e))

    threads = [threading.Thread(target=_worker, args=(sid, 40 + i * 10)) for i, sid in enumerate(sessions)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert not errs, errs
    for i, sid in enumerate(sessions):
        path = tmp_path / f"{sid}.jsonl"
        n, ok = _check_jsonl_intact(path, expect_lines=40 + i * 10)
        assert ok, f"{sid} JSONL 损坏: {n} 行"
    # 各自 derive 正常且事件不串扰
    from core.gateway.session_log import get_session_log

    for i, sid in enumerate(sessions):
        msgs = get_session_log(sid).derive_messages()
        assert all(m.get("content") is not None for m in msgs), sid
        assert len(get_session_log(sid)._events) == 40 + i * 10, sid


def test_same_session_concurrent_serialized(tmp_path):
    """同一 session 并发写(预期串行): 事件总数精确、seq 单调、JSONL 不损坏"""
    sid = "conc_same"
    n_per = 60

    def _worker(offset):
        from core.gateway.session_log import get_session_log

        log = get_session_log(sid)
        for i in range(n_per):
            log.append(
                "tool_result",
                {"name": "read_file", "call_id": f"c{offset}-{i}", "content": "{}", "success": True},
                turn_id=0,
                step_id=0,
            )

    threads = [threading.Thread(target=_worker, args=(k,)) for k in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    from core.gateway.session_log import get_session_log

    log = get_session_log(sid)
    assert len(log._events) == 3 * n_per, f"事件总数应精确: {len(log._events)}"
    seqs = [ev.seq for ev in log._events]
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs), "seq 应单调无重复"
    path = tmp_path / f"{sid}.jsonl"
    n, ok = _check_jsonl_intact(path, expect_lines=3 * n_per)
    assert ok, f"同 session 并发写损坏 JSONL: {n} 行"
    assert n == 3 * n_per


def test_guard_concurrent_failure_counter():
    """guard 并发安全: 20 线程并发失败计数(共享锁) → 精确无丢失"""
    from core.gateway.shared_state import _consecutive_failures
    from core.gateway.tool_router import _check_consecutive_failure

    sid = "conc_guard"
    n_threads, n_each = 20, 10
    errs = []

    def _worker():
        try:
            for _ in range(n_each):
                _check_consecutive_failure({"success": False, "error": "x"}, "read_file", sid)
        except Exception as e:
            errs.append(str(e))

    threads = [threading.Thread(target=_worker) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert not errs, errs
    assert (
        _consecutive_failures.get(sid) == n_threads * n_each
    ), f"失败计数应精确 {n_threads * n_each}: {_consecutive_failures.get(sid)} (锁防丢失)"


def test_concurrent_pending_writes_lock(monkeypatch, tmp_path):
    """guard 并发安全: 写审批状态并发读写(锁) → 无异常无竞态丢失"""
    import agent_gateway_enhanced as main

    sid = "conc_pend"
    errs = []

    def _worker(k):
        try:
            for i in range(20):
                with main._get_pending_lock():
                    main._pending_writes[sid] = {"tool": "write_file", "path": f"/tmp/f{k}-{i}"}
        except Exception as e:
            errs.append(str(e))

    threads = [threading.Thread(target=_worker, args=(k,)) for k in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert not errs, errs
    assert "path" in main._pending_writes[sid], "写审批状态应完整"


def test_concurrent_sandbox_read_different_sessions():
    """3 路并发工具执行(不同 session 读工具): 各自成功, 沙箱根独立"""
    import tempfile
    from pathlib import Path

    from core.gateway.tool_router import _execute_sandbox_tool

    # 各 session 独立沙箱根
    tmp = Path(tempfile.mkdtemp())
    for i in range(3):
        d = tmp / f"sandbox_{i}"
        d.mkdir(parents=True)
        (d / f"file_{i}.txt").write_text(f"content-{i}", encoding="utf-8")
    results = {}

    def _worker(i):
        r = _execute_sandbox_tool(
            "read_file", {"path": f"file_{i}.txt"}, f"u{i}", f"sess{i}", sandbox_base=tmp / f"sandbox_{i}"
        )
        results[i] = r

    threads = [threading.Thread(target=_worker, args=(i,)) for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    for i in range(3):
        assert results[i].get("success"), f"sess{i} 读取失败: {results[i]}"
        assert f"content-{i}" in str(results[i].get("content", "")), results[i]
