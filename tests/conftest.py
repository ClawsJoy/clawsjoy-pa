"""pytest 配置和共享 fixtures"""
import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 2. engine.audit 缺失(sandbox 环境 engine/ 目录不完整)时忽略 test_engine_interface.py
#    原方案: pytest.ini 用单行 addopts=--ignore 覆盖整份配置(丢失 markers/testpaths/strict-markers),
#    还原配置后改为条件式 collect_ignore——live 有 engine.audit 时该测试正常收集, sandbox 自动跳过。
try:
    import engine.audit  # noqa: F401

    _ENGINE_AUDIT_AVAILABLE = True
except Exception:
    _ENGINE_AUDIT_AVAILABLE = False

if not _ENGINE_AUDIT_AVAILABLE:
    collect_ignore = ["unit/test_engine_interface.py"]


# 1. 拦截 ROS launch_testing 插件污染（环境自愈）
def _purge_ros_plugins():
    for mod_name in list(sys.modules):
        if "launch_testing" in mod_name or "launch_ros" in mod_name:
            del sys.modules[mod_name]


_purge_ros_plugins()


@pytest.fixture
def test_user_id():
    """测试用户ID"""
    return "test_user"


@pytest.fixture
def sample_code():
    """示例代码"""
    return """
def hello():
    print("hello world")

def add(a, b):
    return a + b
"""


@pytest.fixture
def sample_code_with_issues():
    """有问题的示例代码"""
    return """
def unsafe():
    eval(input())
    for i in range(10):
        for j in range(10):
            print(i*j)
    try:
        result = 1/0
    except:
        pass
"""


# 2. Flask test client fixture（test_full_flow 等集成测试依赖）
@pytest.fixture()
def client():
    """提供 Flask test client，用于集成测试"""
    from agent_gateway_enhanced import app
    from core.lib.startup import startup_manager

    app.testing = True
    if not startup_manager.ready:
        startup_manager.start()
        deadline = time.time() + 30
        while not startup_manager.ready and time.time() < deadline:
            time.sleep(0.2)
    with app.test_client() as test_client:
        yield test_client


# ⑭(2026-09-13) 防顺序污染: 每个用例前后快照/还原全局 V9Context 服务。
# 背景: core/os/context.py:95 provide_override 是"直接写 _services" —
#   test_subtask_executor 的 finally 曾 provide_override("pending_writes_cleaner", None)
#   → 键存在但值为 None → core/gateway/write_gate.py:119 的 import 时注册(if not has())
#   **永不重跑** → test_write_gate_unified::cleaner 单跑过、全量跑恒红(顺序依赖)。
# 本 fixture 把"服务表"当测试隔离边界: 用例内怎么改都行, 退出即还原。
@pytest.fixture(autouse=True)
def _v9ctx_service_isolation():
    try:
        from core.os.context import get_v9_context

        _ctx = get_v9_context()
    except Exception:
        yield
        return
    _services = getattr(_ctx, "_services", None)
    if not isinstance(_services, dict):
        yield
        return
    _snapshot = dict(_services)
    try:
        yield
    finally:
        # 只"恢复快照里已有键的原值", **不删除**用例期间新增的键 —
        # 有些服务是 import 时一次性注册(write_gate 的 pending_writes_cleaner 就是),
        # 若整体 clear+update 会把首个用例里刚注册的服务擦掉, 反而制造新的顺序依赖。
        # 覆盖(含被改成 None)与删除都能被这条规则收拾。
        for _k, _v in _snapshot.items():
            _services[_k] = _v


# 测试效率: 预热 tiktoken BPE 词表(首次加载 ~9.7s, 摊到会话启动而非首个调用它的测试)
@pytest.fixture(scope="session", autouse=True)
def _warm_tiktoken():
    try:
        import tiktoken

        tiktoken.encoding_for_model("gpt-4")
    except Exception:
        pass
    yield


# auth_headers fixture（test_api_fixed 等集成测试依赖）
@pytest.fixture()
def auth_headers():
    """返回认证头（本地测试无真实认证，返回空 dict）"""
    return {}
