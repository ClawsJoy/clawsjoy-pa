"""P3: 结构化失败回调 on_fail 携带 {code, message} + 兼容降级"""
import sys, os
sys.path.insert(0, ".")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")  # import task_orchestrator 链式实例化 extractor
import pytest

from core.gateway.execute_agent_task import _notify_fail_impl, _notify_fail_to_text


def _call(reason, cb):
    _notify_fail_impl(cb, "t1", "u1", "s1", None, reason)


def test_annotation_dict_gets_structured():
    """回调参数注解 dict → 收到结构化 {code, message}"""
    got = {}
    def cb(tid, uid, sid, reason: dict):
        got["reason"] = reason
    _call({"code": "LLM_API", "message": "余额不足"}, cb)
    assert got["reason"] == {"code": "LLM_API", "message": "余额不足"}, f"dict 注解应收到原样 dict: {got['reason']}"


def test_no_annotation_gets_text():
    """无注解回调 → 自动降级为 '[CODE] message' 文本(兼容旧消费方)"""
    got = {}
    def cb(tid, uid, sid, reason):
        got["reason"] = reason
    _call({"code": "TIMEOUT", "message": "超过最大轮次"}, cb)
    assert got["reason"] == "[TIMEOUT] 超过最大轮次", f"无注解应降级文本: {got['reason']}"


def test_str_annotation_gets_text():
    """注解为 str → 降级文本"""
    got = {}
    def cb(tid, uid, sid, reason: str):
        got["reason"] = reason
    _call({"code": "TOOL_EXEC", "message": "工具 no_such_tool 执行失败"}, cb)
    assert got["reason"] == "[TOOL_EXEC] 工具 no_such_tool 执行失败"


def test_dict_without_code_degrades_to_message():
    """结构化 dict 无 code → 文本只含 message"""
    got = {}
    def cb(tid, uid, sid, reason):
        got["reason"] = reason
    _call({"message": "仅消息"}, cb)
    assert got["reason"] == "仅消息"


def test_plain_text_reason_passthrough():
    """旧式纯文本 reason → 原样传递(不破坏)"""
    got = {}
    def cb(tid, uid, sid, reason):
        got["reason"] = reason
    _call("旧的纯文本错误", cb)
    assert got["reason"] == "旧的纯文本错误"


def test_callback_exception_ignored():
    """回调抛异常 → 忽略不阻断"""
    def cb(tid, uid, sid, reason: dict):
        raise RuntimeError("cb boom")
    _call({"code": "X", "message": "m"}, cb)  # 不应抛出


def test_signature_unparseable_degrades():
    """签名不可解析(如内置函数) → 保守降级文本"""
    got = {}
    _notify_fail_impl(len, "t", "u", "s", None, {"code": "UNKNOWN", "message": "m"})  # len 签名不可解析, 不应崩
    assert True


def test_to_text_plain_str():
    """_notify_fail_to_text: 纯文本原样返回"""
    assert _notify_fail_to_text("abc") == "abc"
    assert _notify_fail_to_text(None) == "None"


# ===== on_v9_fail code 决策(NETWORK 重试 / TIMEOUT 终止) =====

class _FakeTaskEngine:
    """mock task_engine: 内存任务 + 记录 transition/重试计数"""
    def __init__(self):
        self.tasks = {}
        self.transitions = []
    def get(self, server_id, task_id):
        return self.tasks.get(task_id)
    def transition(self, server_id, task_id, new_state, note=""):
        self.transitions.append((task_id, new_state, note))
        if task_id in self.tasks:
            self.tasks[task_id]["status"] = new_state
    def _load(self, server_id):
        return {"tasks": self.tasks}
    def _save(self, server_id, data):
        self.tasks = data["tasks"]


@pytest.fixture()
def orch_module(monkeypatch):
    """import task_orchestrator 时若 code_entity_extractor 尚未加载, 注入 stub 避免 DB 连接"""
    import sys, types
    if 'core.lib.code_entity_extractor' not in sys.modules:
        stub = types.ModuleType('core.lib.code_entity_extractor')
        class _CEE:
            def __init__(self, *a, **k):
                pass
            db_url = "postgresql://stub"
        stub.CodeEntityExtractor = _CEE
        stub.extractor = _CEE()
        monkeypatch.setitem(sys.modules, 'core.lib.code_entity_extractor', stub)
    from core.lib.v8 import task_orchestrator as to
    return to


def _make_orch(monkeypatch, orch_module):
    fake = _FakeTaskEngine()
    monkeypatch.setattr(orch_module, "task_engine", fake)
    orch = orch_module.TaskOrchestrator.__new__(orch_module.TaskOrchestrator)  # 跳过 __init__(加载文件)
    orch._orchestrations = {"u1": {"task_ids": ["t1", "t2"]}}
    orch._next_v9 = lambda *a, **k: None          # 简化: 不真正跑链式
    orch.run_v9_queue_task = lambda *a, **k: None  # 简化: 不真正重跑
    fake.tasks = {"t1": {"status": "running", "_retry_count": 0}, "t2": {"status": "pending"}}
    return orch, fake


def test_on_v9_fail_network_retries(monkeypatch, orch_module):
    """NETWORK → 重试 1 次(run_v9_queue_task 被调)"""
    orch, fake = _make_orch(monkeypatch, orch_module)
    retried = []
    orch.run_v9_queue_task = lambda task, uid, sid: retried.append(task["status"])
    orch.on_v9_fail("t1", "u1", "s1", {"code": "NETWORK", "message": "connection reset"})
    assert retried, "NETWORK 应触发重试"
    assert fake.transitions[-1][0] == "t1" and fake.transitions[-1][1] == "failed"


def test_on_v9_fail_timeout_terminates(monkeypatch, orch_module):
    """TIMEOUT → 终止不重试(_next_v9 被调, run_v9_queue_task 不调)"""
    orch, fake = _make_orch(monkeypatch, orch_module)
    nexted = []
    retried = []
    orch._next_v9 = lambda task, uid, sid: nexted.append(task["status"])
    orch.run_v9_queue_task = lambda task, uid, sid: retried.append(task["status"])
    orch.on_v9_fail("t1", "u1", "s1", {"code": "TIMEOUT", "message": "超过最大轮次"})
    assert not retried, "TIMEOUT 不应重试"
    assert nexted, "TIMEOUT 应继续下一个"
    assert fake.transitions[-1][2] == "超过最大轮次", f"note 应为 message: {fake.transitions[-1][2]}"


def test_on_v9_fail_legacy_text_retries(monkeypatch, orch_module):
    """旧式纯文本 reason(兼容路径) → 保持原重试 1 次行为"""
    orch, fake = _make_orch(monkeypatch, orch_module)
    retried = []
    orch.run_v9_queue_task = lambda task, uid, sid: retried.append(1)
    orch.on_v9_fail("t1", "u1", "s1", "旧的文本错误")
    assert retried, "纯文本应保持重试"
