"""#41 阶段2：三层滚动结构 — 热窗口/滚动语义摘要/SAG 快照"""
import json
import sys

sys.path.insert(0, ".")
import pytest

from core.gateway import message_assembler as MA


@pytest.fixture(autouse=True)
def _clean_store():
    MA._layer_store.clear()
    yield


def _msgs(n=20, with_fail=False):
    """构造 n 轮消息（user + assistant 交替）"""
    msgs = [{"role": "system", "content": "你是助手"}]
    for i in range(n):
        msgs.append({"role": "user", "content": f"任务步骤 {i}：修改模块 {i}"})
        if with_fail and i % 3 == 0:
            msgs.append({"role": "assistant", "content": f"步骤 {i} 失败：编译错误"})
        else:
            msgs.append({"role": "assistant", "content": f"步骤 {i} 已完成：成功修改"})
    return msgs


def test_hot_window_keeps_recent():
    """⑧(2026-09-13) 热窗口口径更新: 旧 assistant/tool 移出, **user 永不压缩**(R2, 2026-08-30)

    旧断言 len(messages) <= 4 是 R2 之前的语义。R2: "用户消息永不压缩——从被移出区
    抽回所有 user 原文, 只摘要 tool/assistant 旧消息"(message_assembler._layered_compress)。
    → 10 轮 user/assistant 的期望保留 = 10 user + 尾部 2 assistant = 12
    """
    msgs = _msgs(10)
    MA._layered_compress("u1", "s1", msgs, keep=4)
    store = MA._layer_store["u1::s1"]
    kept = store["messages"]
    _users = [m for m in kept if m["role"] == "user"]
    _assis = [m for m in kept if m["role"] == "assistant"]
    assert len(_users) == 10, f"R2: user 消息不应被压缩, 实际 {len(_users)}"
    assert len(_assis) < 10, f"旧 assistant 应移出热窗口, 实际保留 {len(_assis)}"
    assert kept[-1]["role"] == "assistant", "最后一条 assistant 应留在热窗口"
    # 移出的旧 assistant 进滚动层摘要(不是丢弃)
    assert store["summary"].get("completed"), "移出的旧 assistant 应进滚动摘要"


def test_rolling_layer_semantic_summary():
    """滚动层：语义摘要提取任务目标/已完成/失败"""
    msgs = _msgs(10, with_fail=True)
    MA._layered_compress("u2", "s2", msgs, keep=4)
    store = MA._layer_store["u2::s2"]
    summary = store["summary"]
    assert isinstance(summary, dict)
    assert summary.get("task_goal"), "应提取任务目标"
    assert summary.get("completed"), "应提取已完成步骤"
    assert summary.get("failed_attempts"), "应提取失败尝试"


def test_assemble_renders_summary_text():
    """组装：summary dict 渲染为 system 文本注入"""
    msgs = _msgs(10)
    MA._layered_compress("u3", "s3", msgs, keep=4)
    out = MA._assemble_messages("u3", "s3")
    assert out[0]["role"] == "system"
    joined = " ".join(str(m.get("content", "")) for m in out)
    assert "任务目标" in joined or "已完成" in joined


def test_sag_layer_snapshot_pointer(monkeypatch):
    """⑩(2026-09-13) 改测法: 摘要超限 → 写快照 + 指针 + 裁剪(completed 末 3/ failed 末 2)

    旧写法靠"堆 60 条消息"让摘要超 2KB, 但摘要器后来加了硬上限
    (completed≤10 / failed≤5 / 每条 [:120], message_assembler:57-64)
    → 实测该 fixture 摘要 JSON 仅 1936 字符 < 2000 阈值 → 快照路径**根本不可达**(测试前提失效)。
    改为: 预置一个超 2KB 的摘要 + 只喂 user 消息(旧 user 被 R2 抽回 → 摘要器输入为空的
    `old`, 不改写预置摘要) → 稳定走到 SAG 分支。
    """
    import glob
    import json as _json

    _big = {
        "task_goal": "巨型任务目标" + "g" * 200,
        "completed": [f"步骤{i}已完成：成功修改了模块{i}的多个函数" + "y" * 100 for i in range(12)],
        "in_progress": "进行中的超长步骤说明" + "p" * 150,
        "failed_attempts": [f"步骤{i}失败：编译错误" + "e" * 100 for i in range(5)],
        "key_findings": [],
        "file_status": {},
    }
    assert len(_json.dumps(_big, ensure_ascii=False)) > 2000, "前置: 预置摘要应超 2KB 阈值"
    # 只喂 user 消息: 被移出的 old 全是 user(R2 抽回) → 摘要器输入为空, 预置摘要不被改写
    _only_users = [{"role": "system", "content": "你是助手"}] + [
        {"role": "user", "content": f"任务步骤 {i}：修改模块 {i}"} for i in range(10)
    ]
    MA._layer_store["u4::s4"] = {"system": [], "messages": [], "summary": _big}
    MA._layered_compress("u4", "s4", _only_users, keep=4)
    summary = MA._layer_store["u4::s4"]["summary"]
    assert isinstance(summary, dict)
    # ① 裁剪语义: completed 末 3 / failed 末 2
    assert len(summary.get("completed", [])) == 3, f"completed 应裁到末 3: {len(summary.get('completed', []))}"
    assert len(summary.get("failed_attempts", [])) == 2, f"failed 应裁到末 2: {len(summary.get('failed_attempts', []))}"
    # ② 指针语义
    assert summary.get("snapshot_pointer"), "应保留快照指针"
    assert "[历史快照:" in summary["snapshot_pointer"]
    # ③ 快照文件已落盘
    snaps = glob.glob("data/v8/context_snapshots/*s4*.json")
    assert snaps, "SAG 快照文件应已写入"


def test_summarize_text_compat_str():
    """兼容旧字符串摘要"""
    assert MA._summarize_text("旧格式字符串") == "旧格式字符串"
    assert MA._summarize_text(None) == ""
    assert MA._summarize_text({}) == ""


def _thinking_msgs(n=30, keep_tail=True):
    """构造 thinking 长任务: 尾部是带 reasoning_content + tool_calls 的 assistant + tool"""
    msgs = [{"role": "system", "content": "你是助手"}]
    for i in range(n):
        msgs.append({"role": "user", "content": f"任务步骤 {i}"})
        msgs.append({"role": "assistant", "content": f"分析 {i}", "reasoning_content": f"思考 {i}"})
    msgs.append(
        {
            "role": "assistant",
            "content": "",
            "reasoning_content": "最后思考: 需要写入",
            "tool_calls": [
                {"id": "t9", "type": "function", "function": {"name": "write_file", "arguments": '{"path": "z.py"}'}}
            ],
        }
    )
    msgs.append({"role": "tool", "tool_call_id": "t9", "content": "成功"})
    return msgs


def test_layered_keeps_last_reasoning_assistant():
    """修复: 压缩后最后一条 assistant 的 reasoning_content 必须保留(切点不能越过它)"""
    msgs = _thinking_msgs(30)
    MA._layered_compress("u5", "s5", msgs, keep=4)
    store = MA._layer_store["u5::s5"]
    kept = store["messages"]
    # 最后一条带 reasoning_content 的 assistant 必须在热窗口内
    last_rc = [m for m in kept if m.get("reasoning_content")]
    assert last_rc, "最后 reasoning assistant 应保留在热窗口"
    assert "最后思考: 需要写入" in last_rc[-1].get("reasoning_content", ""), "reasing 内容应完整"
    # tool 配对完整: 每个 tool 都有对应 assistant tool_calls
    _ids = set()
    for m in kept:
        if m.get("role") == "assistant":
            for _tc in m.get("tool_calls") or []:
                _ids.add(_tc.get("id"))
    for m in kept:
        if m.get("role") == "tool":
            assert m.get("tool_call_id") in _ids, f"孤立 tool: {m}"


def test_layered_tiny_keep_still_protects():
    """keep=1(极端): 最后 reasoning assistant 仍保留(回退保护, 不被摘要替代)"""
    msgs = _thinking_msgs(30)
    MA._layered_compress("u6", "s6", msgs, keep=1)
    store = MA._layer_store["u6::s6"]
    kept = store["messages"]
    last_rc = [m for m in kept if m.get("reasoning_content")]
    assert last_rc, "keep=1 也应保留最后 reasoning assistant"
    # 组装后结构安全: 无孤立 tool, reasoning 可经 dict 拷贝保留
    out = MA._assemble_messages("u6", "s6")
    out_ids = set()
    for m in out:
        if m.get("role") == "assistant":
            for _tc in m.get("tool_calls") or []:
                out_ids.add(_tc.get("id"))
    for m in out:
        if m.get("role") == "tool":
            assert m.get("tool_call_id") in out_ids, f"组装后孤立 tool: {m}"
