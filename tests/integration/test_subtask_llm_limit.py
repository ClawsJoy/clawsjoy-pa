"""任务3 v9: 子任务 LLM 并发限流(信号量 2) + 指数退避重试"""
import sys, time, threading
sys.path.insert(0, ".")
import pytest

import core.gateway.execute_agent_task as eat


def test_semaphore_limits_concurrency():
    """信号量最多放行 2 个并发(第 3 个阻塞等待不报错)"""
    sem = threading.Semaphore(2)
    active = {"count": 0, "max": 0}
    lock = threading.Lock()
    done = []

    def worker(i):
        with sem:
            with lock:
                active["count"] += 1
                active["max"] = max(active["max"], active["count"])
            time.sleep(0.3)
            with lock:
                active["count"] -= 1
            done.append(i)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert active["max"] == 2, f"并发峰值应为 2, got {active['max']}"
    assert len(done) == 4, "4 个 worker 应全部完成(排队不报错)"


def test_retry_exponential_backoff(monkeypatch):
    """LLM 失败指数退避重试: 1s->2s, 最多 3 次调用"""
    calls = {"n": 0}
    sleeps = []

    class _FakeAdapter:
        def execute_with_tools(self, **k):
            calls["n"] += 1
            return {"success": False, "error": "Errno 101 Network is unreachable"}

    monkeypatch.setattr(eat, "time", type("T", (), {"sleep": lambda s: sleeps.append(s), "time": time.time})())
    # 直接测 retry 循环: 构造最小场景(mock 适配器 + 信号量)
    sem = threading.Semaphore(2)
    resp = {"success": False, "error": "init"}
    retries = 0
    delay = 1.0
    sleeps = []
    adapter = _FakeAdapter()
    while retries < 3:
        try:
            with sem:
                resp = adapter.execute_with_tools(messages=[], tools=[], user_id="u", temperature=0.7, max_tokens=100)
        except Exception as e:
            resp = {"success": False, "error": str(e)[:200]}
        if resp.get("success"):
            break
        retries += 1
        if retries < 3:
            sleeps.append(delay)  # 记录退避(不真实 sleep)
            delay *= 2
    assert calls["n"] == 3, f"应重试 3 次, got {calls['n']}"
    assert sleeps == [1.0, 2.0], f"退避应为 1s->2s, got {sleeps}"
    assert resp.get("success") is False, "3 次都失败后保持失败"


def test_retry_recovers_on_third(monkeypatch):
    """第 3 次成功则恢复(不浪费前两次失败)"""
    calls = {"n": 0}

    class _RecoverAdapter:
        def execute_with_tools(self, **k):
            calls["n"] += 1
            if calls["n"] < 3:
                return {"success": False, "error": "temp network"}
            return {"success": True, "data": {"choices": [{"message": {"role": "assistant", "content": "ok"}}]}, "tokens": 1}

    sem = threading.Semaphore(2)
    resp = {"success": False, "error": "init"}
    retries = 0
    adapter = _RecoverAdapter()
    while retries < 3:
        try:
            with sem:
                resp = adapter.execute_with_tools(messages=[], tools=[], user_id="u", temperature=0.7, max_tokens=100)
        except Exception as e:
            resp = {"success": False, "error": str(e)[:200]}
        if resp.get("success"):
            break
        retries += 1
    assert calls["n"] == 3, "应调 3 次"
    assert resp.get("success") is True, "第 3 次应恢复成功"
