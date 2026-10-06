"""#106 P2: 前后端协议一致性测试 — agentSend 处理的状态覆盖后端返回

⭐ 2026-10-06（pm_1415 §一 · 明书 · ⛔ 改其判之逻辑）：本测之「判之式」＋「所扫之面」＋「过取之险」照实：

⒈ **判之式 ＝ 源码扫（双向）**（⛔ 运行之实 —— 唯读文件之字节 ＋ `re.findall`）：
   后端：`re.findall(r'"status": "([a-z_]+)"', bridge)`
   前端：`re.findall(r"d.status === '([a-z_]+)'", <该段>)`
   ⇒ 取「后端所报之状态名之集」−「前端所处理之状态名之集」⇒ 非空即 `assert` 红。
⒉ **二面之射程**（各以字面串切段 ⇒ 段外 ⛔ 扫）：
   后端：`routes/v9_chat.py` ＋ `core/gateway/v9_chat/entry.py` ＋ `.../bridge_call.py`
         ⇒ 自 `def v9_agent_chat()` 切至 `def _handle_write_approval`（前置之 `irrelevant` 表除外）。
   前端：`web/static/js/chat.js` 之自 `async function agentSend(` 切至 `async function agentSendAsync()`
         ＋ `web/static/js/approval.js` 之自 `async function sendWriteApproval` 切至
         `function renderWriteConfirmCard`（后者不在 ⇒ 退 `[]`）。
⒊ ⚠ **过取之险（要）**：所扫者 ＝ **源码之字面**（⛔ 语义）⇒ **内层字面亦中**
   ⇒ 可判「前端**须**处理某态」而其态**今生 ⛔ 达前端**（后端只在其内层分支产出）。
   实例：`approval_exempt` —— 后端之 `"status": "approval_exempt"` 在**内层**产出，前端**⛔ 收**
   （2026-10-06 修 `chat.js` 之 `seed_failed` ／ `approval_exempt` 二态支，即为此「假阳」所迫 · `39ad4ea`）。
   ⇒ 本测**过包括**（宁可多要求一端之支）· ⛔ 判「此态真达前端」。
⒋ ⭐ `v2`（宜改）：判据宜改**「载荷之实」**（真跑后端 ⇒ 录其**实发**之 `status` ⇒ 核前端之支），
   ⛔ 以「源码之形」代「运行之实」（承「探针 ≠ 活闸」之族）。
⒌ ⛔ 改本测之判之逻辑（本注唯**明书**；改判 ⇒ 另件）。
"""
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
