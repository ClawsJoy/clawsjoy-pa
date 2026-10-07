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


# ⑯(2026-10-08 · 9.0.10 序隔离) 会话级「态」逐件还原 —— 使「全跑 ＝ 单跑之和」。
# 归因(一手 · 两轮全跑之差): 全跑 9 条「全跑红 ／ 单跑绿」= 二类**进程级共享态**残留 ——
#   ⒜ core/gateway/precision_inject.py:201 `_cfg_roots` 为 functools.lru_cache(maxsize=1):
#      首次调用者之 `_obsidian_cfg()`(读 config/v9/execution_policy.yaml)结果**钉死全会话**。
#      全跑时先有**真配置**调用者(知识面/金丝雀用例) ⇒ 缓存 = 真根(`工作区/SOPs/SOPs` 向
#      / `开发区/ComputerUse/Pitfalls`); 之后 tests/unit/test_precision_inject.py 之 `_iso`
#      猴补 `_obsidian_cfg` 对 `_sops_rel`/`_pitfalls_rel`(走缓存)**无效** ⇒ 解析路径落
#      tmp vault 之外 ⇒ 6 条 precision_inject ＋ 2 条知识面用例红(单跑时首调在猴补之后 ⇒ 绿)。
#   ⒝ core/gateway/shared_state.py:646 `_preempt_requests`/`_preempt_starve` 为**进程级共享队列**:
#      tests/unit/test_pm011_n11.py:261 经 `POST /v9/preempt`(路由缺省 `priority=5`/`requester=boss`)
#      为 session `s1` 登记后**未 drain/clear** ⇒ 后继 tests/unit/test_workspace_guard_fixes.py:223
#      的 `_execute_sandbox_tool("web_search", {}, "u1", "s1")` 被「prio 5 抢占」⇒ 1 条红。
# 本 fixture 承 `_v9ctx_service_isolation` 之式: 把「会话级缓存/共享队列」当**隔离边界**,
# 每用例前后还原到入口式样(⛔ 改断言 · ⛔ 关检查)。诊断用 kill-switch: `CJ_NO_ORDER_ISOLATION=1`。
_ORDER_STATE = (
    # (模块, 属性, 形): "lru" = functools 缓存(调 `.cache_clear()`)｜"dict" = 可变容器(调 `.clear()`)
    ("core.gateway.precision_inject", "_cfg_roots", "lru"),
    ("core.gateway.shared_state", "_preempt_requests", "dict"),
    ("core.gateway.shared_state", "_preempt_starve", "dict"),
)


def _order_state_reset():
    """把 `_ORDER_STATE` 所列之会话级态还原到入口式样。

    ⚠ 逐件**重解析**(⛔ 持对象引用): `shared_state.clear_preempt` 会**重绑**
      `_preempt_starve` 之名 ⇒ 缓存下来的旧对象会失效(改了等于没改)。
    ⚠ 只碰**已在 sys.modules 者**: 未用之模块 ⛔ 为清缓存而额外 import(副作用/开销)。
    """
    import importlib
    import sys as _sys

    for _mod, _attr, _kind in _ORDER_STATE:
        if _mod not in _sys.modules:
            continue
        try:
            _obj = getattr(importlib.import_module(_mod), _attr, None)
            if _obj is None:
                continue
            if _kind == "lru":
                _obj.cache_clear()
            else:
                _obj.clear()
        except Exception:
            continue


@pytest.fixture(autouse=True)
def _order_isolation():
    """⑯ 序隔离: 每用例前/后还原会话级共享态 ⇒ 全跑 ＝ 单跑之和(⛔ 假红 ∧ ⛔ 假绿)。"""
    if os.environ.get("CJ_NO_ORDER_ISOLATION") == "1":
        yield
        return
    _order_state_reset()
    try:
        yield
    finally:
        # 后置亦还原: ⛔ 让本用例之残留(尤其失败/异常径)漏给下一件。
        _order_state_reset()
