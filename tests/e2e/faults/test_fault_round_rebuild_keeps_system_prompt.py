# -*- coding: utf-8 -*-
"""故障注入 #16：轮首 rebuild_context 重建后，系统提示词必须仍在（2026-09-13 批63 A1）。

事故（B 块残留：批59 发现 → 批61 定性 → 批63 立测）：
  entry.py:72-73                 build_prompt 组装 messages（SYS 在 messages[0]）
  → agent_gateway_enhanced.py:440 rebuild_context(...)
  → round_start.py:19            derive_messages(last_task_only=True) **整体替换** messages
  → SYS 丢失；round_start.py:22-46 的回挂是**窄口径**（只认 3 个 _RESUME_MARKS），
    而 agent_system.md 开头是 '# Agent 工作区 System Prompt'，**不匹配** → 救不回来。

影响（批63 A2 量化）：22,238 字节 / 约 **7,848 token**，**每轮**；占 round budget(61,536) 的 12.8%；
不越压缩阈值(36,922) ⇒ 修复不会改变压缩行为。丢失的是**约束类段落**
（工具声明段 / 执行纪律 G1-G3 / 防幻觉硬约束 / 禁止行为 / 代码修改强制验证）→ **行为漂移而非报错**。

状态：**xfail(strict=True)** —— 修复尚未落地（批63 只做前置两件事 A1/A2）。
修复落地后本用例会 XPASS → strict 使其变为**失败** → **强制摘掉 xfail**，
避免「修好了但标记没人摘」这种假绿。
"""
import os
import sys

import pytest

sys.path.insert(0, ".")

_SYS_PATH = "config/prompts/agent_system.md"
_SYS_HEAD = "# Agent 工作区 System Prompt"


# 批65：a 方案已落地（round_start.py 扩大回挂口径）→ 摘除 xfail（原 xfail(strict=True)，修复后 XPASS 强制摘标记）
def test_FAULT_round_rebuild_keeps_system_prompt():
    """round=0 重建后 SYS 必在 —— 测**调用点**（真调 rebuild_context），不 mock 被测逻辑。"""
    from core.gateway.v9_bridge.round_start import rebuild_context

    sys_text = open(_SYS_PATH, encoding="utf-8").read()
    assert sys_text.startswith(_SYS_HEAD), "前置：系统提示词开头应为固定标记（若改了要同步本测试）"

    sid = "fault_sys_%d" % os.getpid()  # pid 隔离：并发 pytest 各自独立现场（见批59 flaky 归因）
    out = rebuild_context(
        messages=[{"role": "system", "content": sys_text}, {"role": "user", "content": "把报告整理成 data/reports/x.md"}],
        tools=[],
        user_id="fault_sys_u",
        session_id=sid,
        model="deepseek-chat",
        is_7b_fallback=False,
    )
    kept = [m for m in (out or []) if isinstance(m, dict) and str(m.get("content") or "").startswith(_SYS_HEAD)]
    assert kept, "轮首重建后系统提示词丢失（每轮丢 SYS ⇒ 工具声明段/执行纪律/防幻觉硬约束" "/禁止行为/代码修改强制验证 全部消失，表现为行为漂移而非报错）"
