# -*- coding: utf-8 -*-
"""S1 canary: L0 进程内集成 — mock adapter 驱动 _v9_bridge_loop, 5 类 golden + 基线落盘。

不改生产代码。断言: reason 正常(最终助手有实质内容)/无重复无效循环/预算阈值内/
关键产物存在/无 data/vault 尝试/空回复自动恢复。跑完写 baseline JSON。
"""
import json
import os
import sys

sys.path.insert(0, ".")
import pytest

import agent_gateway_enhanced as main

CANARY_DIR = "data/computer_use/canary"
RECORDS = []


class ScriptedAdapter:
    """按脚本返回 OpenAI 兼容响应; 空步骤后给兜底完成。"""

    def __init__(self, steps):
        self.steps = list(steps)

    def execute_with_tools(self, messages, tools, user_id=None, temperature=0.7, max_tokens=2000, thinking=False):
        if not self.steps:
            return self._resp({"content": "（脚本耗尽，兜底完成）", "reasoning_content": "", "tokens": 1})
        step = self.steps.pop(0)
        if callable(step):
            r = step(messages)
            # callable 可返回完整 resp(含 data) 或裸 payload → 统一包 _resp
            return r if (isinstance(r, dict) and r.get("data")) else self._resp(r or {})
        return self._resp(step)

    @staticmethod
    def _resp(step):
        msg = {
            "role": "assistant",
            "content": step.get("content", ""),
            "reasoning_content": step.get("reasoning_content", ""),
        }
        if step.get("tool_calls"):
            msg["tool_calls"] = step["tool_calls"]
        return {
            "success": True,
            "data": {"choices": [{"message": msg}]},
            "tokens": step.get("tokens", 60),
            "usage_detail": {"input": 30, "output": 20, "reasoning": 5, "cache": 0, "total": step.get("tokens", 60)},
        }


def _tc(name, args):
    return [
        {
            "id": "call_" + name + "_" + str(abs(hash(json.dumps(args, sort_keys=True))) % 10000),
            "type": "function",
            "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)},
        }
    ]


def _run(name, task, script, asserts):
    sid = "canary_%s_%d" % (name.replace(" ", "_"), os.getpid())
    ad = ScriptedAdapter(script)
    res = main._v9_bridge_loop([{"role": "user", "content": task}], [], "canary_u", sid, ad)
    msgs, tool_steps, exhausted, final_resp, tokens = res[0], res[1], res[2], res[3], res[4]
    finals = [m for m in msgs if m.get("role") == "assistant" and (m.get("content") or "").strip()]
    last_content = finals[-1]["content"] if finals else ""
    step_rows = [
        {"tool": s.get("tool"), "ok": bool(s.get("success", s.get("ok", False))), "arg": str(s.get("arg"))[:40]}
        for s in tool_steps
    ]
    rec = {
        "name": name,
        "tokens": tokens,
        "exhausted": bool(exhausted),
        "steps": step_rows,
        "final_head": last_content[:120],
        "final_empty": not last_content.strip(),
    }
    # 全局断言: 无 data/vault 尝试
    vault_hits = [m.get("content", "") for m in msgs if "data/vault" in str(m.get("content", ""))]
    asserts(rec, finals, tool_steps, msgs)
    assert not vault_hits, "不应出现 data/vault 尝试: %r" % vault_hits[:1]
    RECORDS.append(rec)
    return rec


@pytest.fixture()
def _tmp_vault(tmp_path, monkeypatch):
    """⑪连带(2026-09-13): canary#1 原本依赖真实 vault 的 Pitfalls/避坑清单.md —
    本机 vault 没有该文件, 之前只是被 handler 的 `success=True + 空内容` 掩盖才"绿"。
    ⑪ 把缺文件改成 success=False 后现形 → 改为 hermetic(自造 tmp vault), 保住端到端金标准。
    """
    _pit = tmp_path / "Pitfalls"
    _pit.mkdir(parents=True, exist_ok=True)
    (_pit / "避坑清单.md").write_text("# 避坑清单\n\n- vault 路径只能用 obsidian_knowledge 访问\n- 写文件走审批\n", encoding="utf-8")
    import core.gateway.precision_inject as _pi

    monkeypatch.setattr(_pi, "_vault_path", lambda: str(tmp_path))
    # 2026-09-28: 本 fixture 自造 `Pitfalls/避坑清单.md` ⇒ **配置也要钉住**。
    #   只钉 `_vault_path` 时，避坑清单的**目录**仍读本机 execution_policy.yaml 的
    #   `pitfalls_dir`（该值随 vault 布局变）⇒ 测试变成「本机配置内容依赖型」，
    #   本机把真件指回活区后当场现形。这里显式声明本 fixture 自己的布局。
    monkeypatch.setattr(
        _pi,
        "_obsidian_cfg",
        lambda: {
            "enabled": True,
            "sops_dir": "SOPs",
            "pitfalls_dir": "Pitfalls",
            "pitfalls_file": "避坑清单.md",
        },
    )


def test_canary_01_obsidian_knowledge_read(_tmp_vault):
    """golden1 知识检索: obsidian read(真实读路径 + hermetic vault) + 总结"""
    sid = "canary_01"
    script = [
        {
            "content": "读避坑清单",
            "reasoning_content": "想",
            "tokens": 60,
            "tool_calls": _tc("obsidian_knowledge", {"action": "read", "sop_key": "避坑清单"}),
        },
        {"content": "检索完成: 避坑清单含 vault/路径/审批等条目。", "reasoning_content": "", "tokens": 40},
    ]

    def chk(rec, finals, steps, msgs):
        assert rec["final_empty"] is False, "应产出实质结论"
        assert any(
            s["tool"] == "obsidian_knowledge" and (s.get("success") or s.get("ok")) for s in steps
        ), "obsidian read 应成功"
        assert rec["tokens"] < 2000, "预算内"
        assert "避坑清单" in rec["final_head"]

    _run("01-知识检索", "读 Obsidian 避坑清单并 3 行总结要点", script, chk)


def test_canary_02_poc_analysis():
    """golden2 浏览器 POC(离线数据): 读 a11y 结果并给出选序号结论"""
    import pytest as _pytest

    a11y = "data/tmp/a11y_elements.json"
    if not os.path.exists(a11y):
        _pytest.skip("前置 POC 产物缺失(需先跑浏览器 a11y 枚举生成 %s), 环境类跳过" % a11y)
    script = [
        {"content": "读枚举结果", "reasoning_content": "想", "tokens": 60, "tool_calls": _tc("read_file", {"path": a11y})},
        {"content": "POC 结论: a11y 枚举 + LLM 选序号可行(此前实测 100%)。", "reasoning_content": "", "tokens": 40},
    ]

    def chk(rec, finals, steps, msgs):
        assert rec["final_empty"] is False
        assert any(s["tool"] == "read_file" and (s.get("success") or s.get("ok")) for s in steps)
        assert "POC" in rec["final_head"]

    _run("02-浏览器POC分析", "分析 a11y_elements.json 并给出混合方案结论", script, chk)


def test_canary_03_local_refactor_plan():
    """golden3 本地小重构: 读源 + 列目录 + 产出重构计划"""
    script = [
        {
            "content": "先读源文件与目录",
            "reasoning_content": "想",
            "tokens": 60,
            "tool_calls": _tc("read_file", {"path": "core/tools/a11y_dom.py"}),
        },
        {
            "content": "再看 tools 目录",
            "reasoning_content": "想",
            "tokens": 60,
            "tool_calls": _tc("list_dir", {"path": "core/tools"}),
        },
        {"content": "重构计划: 将 a11y_dom 纯函数保持单文件, 后续收敛缓存层。", "reasoning_content": "", "tokens": 40},
    ]

    def chk(rec, finals, steps, msgs):
        assert rec["final_empty"] is False
        tools = [s["tool"] for s in steps]
        assert "read_file" in tools and "list_dir" in tools, "应执行读+列目录"
        assert "重构计划" in rec["final_head"]

    _run("03-本地小重构", "阅读 a11y_dom.py 与 core/tools 目录并给出重构计划(2 行)", script, chk)


def test_canary_04_covergen_empty_reply_recovery():
    """golden4 封面生成(空回复多发): 两次同参 list_dir + 空回复 → 自动恢复"""
    script = [
        {
            "content": "侦察素材",
            "reasoning_content": "想",
            "tokens": 60,
            "tool_calls": _tc("list_dir", {"path": "data/screenshots"}),
        },
        {"content": "", "reasoning_content": "想", "tokens": 50},  # 空回复
        {
            "content": "继续侦察",
            "reasoning_content": "想",
            "tokens": 60,
            "tool_calls": _tc("list_dir", {"path": "data/screenshots"}),
        },  # 同参(应去重/短)
        {"content": "封面生成方案: 以 ui_test_baidu.png 为底做 900x383 封面(待用户确认字体)。", "reasoning_content": "", "tokens": 50},
    ]

    def chk(rec, finals, steps, msgs):
        assert rec["final_empty"] is False, "空回复后应自动恢复并出结论"
        assert "封面" in rec["final_head"]
        assert rec["tokens"] < 3000, "预算内"
        # 同参 list_dir 第二次应命中 L4 缓存(l4_cached)或至少不再全量重读
        l4 = [s for s in steps if s.get("tool") == "list_dir"]
        assert len(l4) >= 2, "应有两次 list_dir"

    _run("04-封面生成空回复", "生成 900x383 封面(可能多轮空回复, 需自恢复)", script, chk)


def test_canary_05_report_write_loop():
    """golden5 写报告(学习循环): cu_learning start→log_step→complete(证据门禁)→落盘 meta"""
    import re as _re
    import time

    tid = "canary_report_%d" % int(time.time())
    _pid_holder = {}

    def _plan_id_from(msgs):
        if _pid_holder.get("pid"):
            return _pid_holder["pid"]
        for m in reversed(msgs):
            if m.get("role") == "tool":
                mm = _re.search(r'"plan_id":\s*"([^"]+)"', str(m.get("content") or ""))
                if mm:
                    _pid_holder["pid"] = mm.group(1)
                    return mm.group(1)
        return ""

    def step_log(msgs):
        return {
            "content": "完成步骤",
            "reasoning_content": "想",
            "tokens": 60,
            "tool_calls": _tc(
                "cu_learning",
                {
                    "action": "log_step",
                    "task_id": tid,
                    "plan_id": _plan_id_from(msgs),
                    "ok": True,
                    "op": "write_note",
                    "intent": "写报告",
                },
            ),
        }

    def step_complete(msgs):
        return {
            "content": "提交证据",
            "reasoning_content": "想",
            "tokens": 60,
            "tool_calls": _tc(
                "cu_learning",
                {
                    "action": "complete",
                    "task_id": tid,
                    "plan_id": _plan_id_from(msgs),
                    "evidence": {"url": "https://x.com/ok"},
                    "report": "报告已写",
                },
            ),
        }

    script = [
        {
            "content": "记录计划",
            "reasoning_content": "想",
            "tokens": 60,
            "tool_calls": _tc(
                "cu_learning",
                {
                    "action": "start",
                    "task_id": tid,
                    "objective": "写 canary 报告",
                    "completion": [{"check": "url_contains", "target": "ok"}],
                },
            ),
        },
        step_log,
        step_complete,
        {"content": "报告已写入(学习循环记录完成, success_runs 累计)。", "reasoning_content": "", "tokens": 40},
    ]

    def chk(rec, finals, steps, msgs):
        assert rec["final_empty"] is False
        cu_ok = [s for s in steps if s["tool"] == "cu_learning" and (s.get("success") or s.get("ok"))]
        assert len(cu_ok) >= 3, "cu 三步应成功"
        # 关键产物: plans meta status=success
        meta = os.path.join("data/computer_use/plans", "%s_*" % tid)
        import glob

        metas = [f for f in glob.glob(meta + "*.meta.json")]
        assert metas and any(
            json.load(open(f, encoding="utf-8")).get("status") == "success" for f in metas
        ), "学习循环成功 meta 应落盘"

    _run("05-写报告学习循环", "把评估报告经学习循环落盘", script, chk)


def test_baseline_recorded():
    """canary 全绿后把基线写盘(供后续每层改动对比)"""
    import pytest as _pytest

    if not os.path.exists("data/tmp/a11y_elements.json"):
        _pytest.skip("前置 POC 产物缺失(a11y_elements.json), golden2 跳过导致不足 5 条 — 环境类跳过")
    assert len(RECORDS) == 5, "5 个 golden 都应记录"
    os.makedirs(CANARY_DIR, exist_ok=True)
    path = os.path.join(CANARY_DIR, "baseline_20260905.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"generated": "2026-09-05", "canary": RECORDS}, f, ensure_ascii=False, indent=1)
    print("BASELINE_SAVED", path)
    print(json.dumps(RECORDS, ensure_ascii=False, indent=1)[:1200])
