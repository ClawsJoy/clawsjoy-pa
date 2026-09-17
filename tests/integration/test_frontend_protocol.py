"""#106 P2: 前后端协议一致性测试 — agentSend 处理的状态覆盖后端返回"""
import re


def test_frontend_handles_backend_statuses():
    """agentSend 处理的状态覆盖 v9_agent_chat 桥接返回的状态"""
    # 模块化拆分后: agentSend/runAgentLoop 在 chat.js, sendWriteApproval 在 approval.js
    html = open("web/static/js/chat.js", encoding="utf-8").read()
    approval_src = open("web/static/js/approval.js", encoding="utf-8").read()
    backend = (
        open("routes/v9_chat.py", encoding="utf-8").read()
        + open("core/gateway/v9_chat/entry.py", encoding="utf-8").read()
        + open("core/gateway/v9_chat/bridge_call.py", encoding="utf-8").read()
    )  # P3-B: 路由已迁出

    # 后端 v9_agent_chat（桥接路径 1541-2400 行）返回的 status
    bridge = backend.split("def v9_agent_chat()")[1].split("def _handle_write_approval")[0]
    backend_statuses = set(re.findall(r'"status": "([a-z_]+)"', bridge))
    # 排除非桥接状态（其他路由/内部步骤状态）
    irrelevant = {"executing", "previous_done", "started", "approved", "rejected", "already_correct"}
    bridge_statuses = backend_statuses - irrelevant

    # 前端 agentSend/runAgentLoop 处理的状态（agentSend 现接受 continueMsgs 参数）
    agent_send = html.split("async function agentSend(")[1].split("async function agentSendAsync()")[0]
    front_statuses = set(re.findall(r"d.status === '([a-z_]+)'", agent_send))
    # approve 回调也处理 write_confirmed/write_rejected
    front_statuses |= set(
        re.findall(
            r"d.status === '([a-z_]+)'",
            approval_src.split("async function sendWriteApproval")[1].split("function renderWriteConfirmCard")[0],
        )
        if "async function sendWriteApproval" in approval_src
        else []
    )

    missing = bridge_statuses - front_statuses
    assert not missing, f"前端未处理后端状态: {missing}"
    print(f"桥接状态 {sorted(bridge_statuses)} 全部被前端处理 ✅")


def test_no_double_registration():
    """#106 C3: roster 路由只注册一次"""
    src = open("agent_gateway_enhanced.py", encoding="utf-8").read()
    n = src.count("register_roster_routes(app)")
    assert n == 1, f"roster 注册 {n} 次"
