"""能力边界检查单测: 网络任务在无网络工具模式提前拦截; 只读/写任务零影响"""
import sys

sys.path.insert(0, ".")
import pytest


@pytest.fixture
def _monkey(monkeypatch):
    import core.gateway.quota_manager as qm

    monkeypatch.setattr(qm, "get_mode", lambda sid, hint="": "minimal")
    monkeypatch.setattr(qm, "get_mode_tools", lambda sid, hint="": ["read_file", "write_file", "execute_command"])
    yield


def _msgs(content):
    return [{"role": "user", "content": content}]


def _cap(msgs, tools=None):
    from core.gateway.v9_bridge.loop import _check_v9_capability

    return _check_v9_capability(msgs, tools or [], "s1", "u1")


def test_network_task_blocked_without_tools(_monkey):
    r = _cap(_msgs("帮我搜索今天AI行业的最新新闻"))
    assert r is not None
    assert r["success"] is False
    assert r["capability_blocked"] is True
    assert "当前模式不支持网络访问" in r["error"]
    assert "无法完成信息收集任务" in r["error"]


def test_network_task_blocked_when_tools_missing_in_mode(_monkey):
    # LLM 工具池有 fetch_web, 但模式白名单没有 → 仍拦截
    r = _cap(_msgs("抓取网页 https://x.com 的内容"), tools=[{"function": {"name": "fetch_web"}}])
    assert r is not None and r["capability_blocked"] is True


def test_network_task_allowed_when_tools_available(_monkey):
    import core.gateway.quota_manager as qm
    from core.gateway.v9_bridge.loop import _check_v9_capability

    # 模式含 fetch_web → 放行
    qm.get_mode_tools = lambda sid, hint="": ["read_file", "write_file", "execute_command", "fetch_web", "browse_web"]
    r = _check_v9_capability(_msgs("搜索今日AI新闻"), [{"function": {"name": "fetch_web"}}], "s1", "u1")
    assert r is None


def test_readonly_task_unaffected(_monkey):
    r = _cap(_msgs("读取 README.md 并总结"))
    assert r is None


def test_write_task_unaffected(_monkey):
    r = _cap(_msgs("修改 config.yaml 里的端口号"))
    assert r is None


def test_analysis_task_without_network_keywords(_monkey):
    r = _cap(_msgs("分析当前目录结构"))
    assert r is None


def test_system_prefixed_message_skipped(_monkey):
    # 最后一条是 [系统] 注入 → 取真实用户任务(只读) → 不拦截
    msgs = [{"role": "user", "content": "读取文件"}, {"role": "user", "content": "[系统] 继续执行当前目标"}]
    r = _cap(msgs)
    assert r is None
