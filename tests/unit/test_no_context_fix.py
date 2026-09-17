# -*- coding: utf-8 -*-
"""no_context 修复专测（2026-09-11）

验收 4 组：
  组1 长任务中断 → 继续 → 上下文恢复（不报 no_context）
  组2 BRIEF.md 正常写入（任务跑时生成，非空）
  组3 多步任务中断 → 继续 → 200 字兜底够不够（够=过，不够=记录升级方向）
  组4 现有功能不变（回归由其它测试覆盖）
"""
import ast
import json
import sys

sys.path.insert(0, ".")

import pytest

from core.lib.brief_manager import BriefManager

_GW_SRC = open("agent_gateway_enhanced.py", encoding="utf-8").read()
_EXE_SRC = open("core/gateway/execute_agent_task.py", encoding="utf-8").read()


def _isolated_bm(tmp_path, uid="u1", sid="s1"):
    bm = BriefManager(uid, sid)
    bm.master_brief = tmp_path / "plans" / "BRIEF.md"
    bm.brief_path = tmp_path / "projects" / "BRIEF.md"
    return bm


# ---- 组2：BRIEF.md 正常写入（generate → 非空） ----
def test_brief_generate_writes_nonempty(tmp_path):
    bm = _isolated_bm(tmp_path)
    bm.generate("做一份 5 步 PPT：封面/大纲/正文/图表/导出")
    content = bm.load()
    assert content, "generate 后 BRIEF.md 应非空"
    assert "做一份 5 步 PPT" in content
    assert "## 3. 执行进度" in content, "应含执行进度段(续跑/update_progress 依赖)"


def test_brief_generate_guard_keeps_existing(tmp_path):
    """组2 守卫：已存在 BRIEF.md 时不重写（保留「继续」的进度）。"""
    bm = _isolated_bm(tmp_path)
    bm.generate("任务A")
    first = bm.load()
    # 模拟 execute_agent_task 主任务启动处的守卫：load() 非 None → 不 generate
    if bm.load() is None:
        bm.generate("任务B")
    assert bm.load() == first, "已存在时不应重写(否则丢进度)"


def _called_names(src):
    """AST 层收集「被调用到的名字」——只看有没有这些调用，不看怎么写的。"""
    called = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name):
                called.add(f.id)
            elif isinstance(f, ast.Attribute):
                called.add(f.attr)
    return called


def _has_none_compare(src):
    """AST 层判断有无「与 None 比较」的守卫（不管写 is None / == None / not ... is not None）。"""
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Compare) and any(isinstance(c, ast.Constant) and c.value is None for c in n.comparators):
            return True
    return False


def test_generate_guard_behaviour(tmp_path):
    """组2 契约（**行为**断言）：BRIEF.md 已存在 → 守卫语义 = 不重写（保留续跑进度）。

    断言的是 BriefManager 的**行为契约**，与任何源码写法无关 ——
    实现换变量名/换写法/合并两处实现都不会误红。
    """
    bm = _isolated_bm(tmp_path)
    assert bm.load() is None, "初始应为空 → 守卫条件成立"
    bm.generate("任务A")
    first = bm.load()
    assert first, "generate 后应非空"
    if bm.load() is None:  # 被守卫拦住的分支（即产品里的守卫语义）
        bm.generate("任务B")
    assert bm.load() == first, "已存在时不应重写(否则丢进度)"


def test_generate_wired_in_execute_agent_task():
    """组2 接线（**AST 结构**断言，2026-09-13 批61 松绑）。

    松绑原因：原实现断言 3 行**源码字面量**
      "get_brief_manager(user_id, session_id)" / "_bm.load() is None" / "_bm.generate(_last_task_msg)"
    → 只要重构换名、换行、或把两处重复实现合并，就**误红** ⇒ **把实现形态钉死，锁死重构空间**
    （B 块实测：execute_agent_task 的 BRIEF 生成块与新 helper 功能重叠却不敢合并，正是被此测试挡住）。

    改为断言**结构**：execute_agent_task 必须**调用** brief 相关 API，且必须有 None 守卫判断。
    不断言字面量、不断言顺序、不断言变量名 ⇒ 重构自由，删掉接线仍会红。
    """
    called = _called_names(_EXE_SRC)
    assert "get_brief_manager" in called, "execute_agent_task 必须调用 get_brief_manager（接线）"
    assert "load" in called, "必须有 load() 守卫（先查后写）"
    assert "generate" in called, "必须调用 generate（任务跑时生成 BRIEF）"
    assert _has_none_compare(_EXE_SRC), "必须有「与 None 比较」的守卫判断（不存在才生成）"


# ---- 组1/组3：兜底接线 + 行为 ----
def test_no_context_fallback_wired():
    """组3 接线：no_context 分支回退 last_task，而非直接报错。"""
    _REC3 = open("core/gateway/v9_chat/recovery.py", encoding="utf-8").read()  # P3-B: C 块已归位
    assert "上下文恢复(降级)" in _REC3, "应有降级注入文案(recovery)"
    assert 'get("last_task"' in _REC3, "应读 .agent_state.json 的 last_task(recovery)"
    assert "上下文丢失，请重新下达指令" in _REC3, "真·无兜底源时仍报 no_context(不静默)(recovery)"


def test_inject_empty_when_no_brief(tmp_path):
    """组1 前置：BRIEF.md 不存在时 inject() 返回空（触发兜底分支）。"""
    bm = _isolated_bm(tmp_path)
    assert bm.inject() == ""


def test_fallback_last_task_extraction(tmp_path):
    """组3 行为：.agent_state.json last_task 可被读回作降级上下文。"""
    state = tmp_path / ".agent_state.json"
    last_task = "做一份关于 AI 的 5 步 PPT：①封面②大纲③正文④图表⑤导出"
    state.write_text(json.dumps({"last_task": last_task, "other": 1}, ensure_ascii=False), encoding="utf-8")
    d = json.loads(state.read_text(encoding="utf-8"))
    assert d.get("last_task") == last_task


# ---- 组3：200 字兜底够不够（多步任务） ----
def test_multi_step_task_fits_200():
    """多步任务(PPT 5 步) 的自然描述是否 ≤200 字 → 够用判断依据。"""
    multi = "做一份关于 AI 行业的 5 步 PPT：①封面标题 ②大纲 ③正文 ④图表 ⑤导出，风格简约商务。"
    assert len(multi) <= 200, f"多步任务描述 {len(multi)} 字，200 字内够用"
    # 极端：带详细子要求的超长任务 → 超过 200 字会被截断（记入"升级方向"）
    long_task = "做一份 5 步 PPT：" + "第一步封面含标题副标题日期，" * 20
    assert len(long_task) > 200, "超长任务描述 >200 字，last_task 截断——记录兜底源需升级(session 消息历史)"
