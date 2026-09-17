# -*- coding: utf-8 -*-
"""P3-A 辅助函数归位：v9 桥接上下文工具（从 agent_gateway_enhanced.py 迁入，2026-09-12）。"""
import json
import re
from pathlib import Path

from core.gateway.context_validator import _is_plan_message
from core.gateway.message_assembler import _inject_sys_content
from core.lib.sandbox_tools import _generate_project_tree


def _v9_inject_context(messages, user_id, session_id):
    """H1 提取: 上下文注入(plan/goal/manual/rollback) + 项目树 + 配额提示。返回 messages。"""
    # 模板填充后，追加上下文注入（#166 收敛：散落 recap/precision 统一走 LoopContextManager.inject_all）
    try:
        from core.lib.v8.loop_context_manager import LoopContextManager

        _task_name_ctx = ""
        for _m in messages:
            if _m["role"] == "user" and not str(_m.get("content", "")).startswith("[系统]"):
                _task_name_ctx = str(_m["content"])[:80]
                break
        _step_num = 1
        try:
            _st_f = Path(f"data/projects/{user_id}/{session_id}/clawsjoy_dev/.agent_state.json")
            if _st_f.exists():
                _st_d = json.loads(_st_f.read_text(encoding="utf-8"))
                _done_n = len(((_st_d.get("task_progress", {}) or {}).get("completed_steps", [])) or [])
                _step_num = _done_n + 1
        except Exception:
            pass
        _ctx_all = LoopContextManager().inject_all(
            task_name=_task_name_ctx or "通用任务",
            step_number=_step_num,
            user_id=user_id,
            session_id=session_id,
        )
        # SAG 任务子图：当前任务的依赖链图（task→plan→hypothesis→capability）
        try:
            from core.lib.sag_chain_injector import SagChainInjector

            _ctx_all["sag_task_subgraph"] = SagChainInjector().render_injection(
                _task_name_ctx or "通用任务", include_graph=True
            )
            # #81 过滤网自学习：SAG 注入侧按 code_edges.weight 降序追加高权重节点（过滤网优先展示常用实体）
            try:
                from core.lib.code_entity_extractor import extractor as _edge_ext_sag

                _edge_rows_sag = _edge_ext_sag.get_edges(entity_name=None, project_id="default", limit=2000)
                _weight_map_sag = {}
                for _r_sag in _edge_rows_sag:
                    for _k_sag in ("target_name", "source_name"):
                        _n_sag = str(_r_sag.get(_k_sag, "") or "")
                        if _n_sag:
                            _w_sag = float(_r_sag.get("weight") or 0.0)
                            _weight_map_sag[_n_sag] = max(_weight_map_sag.get(_n_sag, 0.0), _w_sag)
                _sorted_sag = sorted(_weight_map_sag.items(), key=lambda x: x[1], reverse=True)[:10]
                if _sorted_sag:
                    _top_sag = "\n".join(f"- {_n_sag} (weight={_w_sag:.2f})" for _n_sag, _w_sag in _sorted_sag)
                    _ctx_all[
                        "sag_task_subgraph"
                    ] += f"\n\n[过滤网权重 Top10] 按 code_edges.weight 降序（自学习排序，优先展示常用实体）：\n{_top_sag}"
            except Exception as _se_w:
                print(f"[V9] sag 权重排序失败: {_se_w}")
        except Exception as _se:
            print(f"[V9] sag_task_subgraph 构建失败: {_se}")
            _ctx_all["sag_task_subgraph"] = ""
        _ctx_parts = []
        for _k in ("recap", "precision_feed", "sag_context", "sag_task_subgraph"):
            _v = str(_ctx_all.get(_k, "") or "").strip()
            if _v:
                _ctx_parts.append(_v)
        if _ctx_parts:
            _inject_sys_content(messages, "\n\n" + "\n\n".join(_ctx_parts))
    except Exception as e:
        print(f"[V9] 上下文注入失败: {e}")

        # 注入项目结构树
    _project_tree = _generate_project_tree(user_id, session_id)
    print(f"[PROJECT_TREE] len={len(_project_tree)}, preview={_project_tree[:100]}")
    if _project_tree:
        # 项目树注入到第一条 user 消息，保持 System Prompt 前缀稳定（KV 缓存优化）
        _tree_msg = {"role": "system", "content": f"[系统] 当前项目文件结构（与磁盘同步）：\n{_project_tree}"}
        _first_user_idx = next((_idx for _idx, _m in enumerate(messages) if _m["role"] == "user"), None)
        if _first_user_idx is not None:
            messages.insert(_first_user_idx + 1, _tree_msg)
        else:
            messages.insert(1, _tree_msg)

    # 注入读取配额提示
    _last_usr_q = ""
    for _mq in messages:
        if _mq["role"] == "user":
            _last_usr_q = _mq["content"]
    _write_kw_q = ["创建", "修改", "添加", "新增", "写入", "实现", "编写", "补充"]
    _is_write_q = any(kw in _last_usr_q for kw in _write_kw_q)
    _max_q = 5 if _is_write_q else 10
    _inject_sys_content(
        messages,
        f'\n路径前缀：search_files 返回的 _project_prefix 字段（"clawsjoy_dev/"）是所有路径操作的标准前缀，read_file/write_file/list_dir 都必须使用此前缀。',
    )
    _inject_sys_content(
        messages,
        f"\n读取配额：本次任务最多读取 {_max_q} 个文件，list_dir 最多 3 次。你可以从以下渠道获取信息而无需消耗配额：1) 上方项目树与磁盘实时同步，已列出所有文件路径，无需 list_dir 逐个确认 2) world_model 包含已写入文件的骨架 3) query_index 可查询代码结构（推荐用于查找目录内容，不消耗配额）。达到配额上限后 read_file 和 list_dir 将被拒绝，届时使用 query_index 获取信息，或基于已有信息直接写入交付。",
    )
    return messages


def _v9_mark_agent_plan(messages, task_id=None):
    """H1 提取: 给 Agent 计划消息打隐藏标记 + 自出计划入库 plan.md。返回 messages。"""
    import re
    import re as _re_plan  # H2 防线修复: 提取漏 re import(原 NameError 被吞)

    # 计划标记：给 Agent 输出的计划打上隐藏标记
    for _mp in reversed(messages):
        if _mp["role"] == "assistant" and _mp.get("content"):
            _ac = _mp["content"]
            if "<!-- CLAWSJOY_PLAN -->" not in _ac and _is_plan_message(_ac):
                _mp["content"] = _ac + "\n\n<!-- CLAWSJOY_PLAN -->"
            break
    # Agent 自出计划检测：复用 _is_plan_message 严格条件；带 <!-- CLAWSJOY_PLAN --> 标记的消息视为计划
    try:
        _plan_task_id = re.sub(r"[^\w-]+", "", task_id or "default")
        for _mp in reversed(messages):
            if _mp.get("role") == "assistant" and _mp.get("content"):
                _ac_plan = _mp["content"]
                if "<!-- CLAWSJOY_PLAN -->" in _ac_plan or _is_plan_message(_ac_plan):
                    _plan_dir = Path("data/tasks") / _plan_task_id
                    _plan_dir.mkdir(parents=True, exist_ok=True)
                    (_plan_dir / "plan.md").write_text(_ac_plan, encoding="utf-8")
                    if not any(_m.get("role") == "system" and "检测到执行计划" in _m.get("content", "") for _m in messages):
                        messages.append({"role": "system", "content": "[系统] 检测到执行计划，已入库。请按计划继续执行。"})
                break
    except Exception:
        pass

    return messages


def _v9_is_resume_utterance(text):
    """(b) 2026-09-05: 判断短文本是否为「继续/恢复」类指令(复用最近 goal, 不新建)。"""
    t = str(text or "").strip()
    if not t or len(t) > 12:
        return False
    return t.startswith(("继续", "恢复", "/continue")) or t in ("接着做", "接着干", "再来")


def _v9_ctx_summary(messages, limit=220):
    """(a) 2026-09-05: 上一轮上下文摘要(空回复自动重试时注入, 帮助模型续上)。"""
    if not messages:
        return ""
    for m in reversed(messages):
        c = str(m.get("content") or "").strip()
        if m.get("role") == "assistant" and c and not c.startswith("[系统]"):
            return c[:limit]
    for m in reversed(messages):
        c = str(m.get("content") or "").strip()
        if m.get("role") == "user" and c and not c.startswith("[系统]"):
            return c[:limit]
    return ""


def _v9_looks_like_new_task(text):
    """(c) 2026-09-05: 长任务文本(>12字且非 继续/恢复 开头)视为新任务 —
    防止含「继续/下一步」关键词的新任务被误当旧任务确认, 泄漏旧任务上下文。"""
    t = str(text or "").strip()
    if len(t) <= 12:
        return False
    return not t.startswith(("继续", "恢复", "/continue", "接着"))


def _v9_keep_old_task(prev, new):
    """(c) 旧任务尾注入门禁: 仅「继续/恢复」指令或与上次任务高相似文本才保留旧摘要;
    长新任务(含 继续/下一步 等词)一律不注入, 防上下文串扰。"""
    import difflib

    if not prev or not new:
        return False
    new = str(new).strip()
    if _v9_is_resume_utterance(new) or len(new) <= 4:
        return True
    if len(new) < 10 or _v9_looks_like_new_task(new):
        return False
    r = difflib.SequenceMatcher(None, str(prev)[:120], new[:120]).ratio()
    return r >= 0.5


def _v9_round_checkpoint(events, cap=18):
    """S2(2026-09-05): 记忆三兄弟(L0 recon-digest / L2 轮摘要 / L3 步骤断点)
    合并为单一轮检查点 — 一个数据结构、一处注入点、行为不变。
    产出: 上一轮结束原因 + 已执行步骤(✓/✗/⚪ + 参数 + 结果头) + 最后进展;
    原始事件仍在事件层全量保留。events 支持 .type/.payload 对象或 dict。
    """
    norm = []
    for ev in list(events or []):
        if isinstance(ev, dict):
            norm.append((ev.get("type"), ev.get("payload") or {}))
        else:
            norm.append((getattr(ev, "type", None), getattr(ev, "payload", None) or {}))
    uidx = [i for i, (t, p) in enumerate(norm) if t == "user_message" and p.get("source") == "user_input"]
    seg = norm
    reason = ""
    if len(uidx) >= 2:
        seg = norm[uidx[-2] + 1 : uidx[-1]]
        for t, p in seg:
            if t == "turn_end":
                reason = str(p.get("reason") or "")
    results = {}
    for t, p in norm:
        if t == "tool_result" and p.get("call_id"):
            results[str(p["call_id"])] = {
                "ok": bool(p.get("success")),
                "head": str(p.get("content") or "")[:60].replace(chr(10), " "),
            }
    lines = []
    for t, p in seg:
        if t != "tool_call":
            continue
        nm = p.get("name") or "?"
        cid = str(p.get("call_id") or "")
        try:
            a = json.dumps(p.get("arguments") or {}, ensure_ascii=False)
        except Exception:
            a = ""
        res = results.get(cid)
        mark = "⚪ 未执行" if res is None else ("✓" if res["ok"] else "✗")
        line = "%s %s %s" % (mark, nm, a[:50])
        if res and res.get("head"):
            line += " → " + res["head"][:50]
        lines.append(line)
    prog = ""
    for t, p in reversed(seg):
        if t == "assistant_message":
            c = str(p.get("content") or "")
            if c and not c.startswith("[系统]"):
                prog = c[:160].replace(chr(10), " ")
                break
    if not lines and not prog and not reason:
        return ""
    parts = [
        "上一轮结束: %s" % reason if reason else "任务进行中",
        "已执行步骤(✓ 已完成勿重复执行, ✗/⚪ 才重试):" + chr(10) + (chr(10).join(lines[:cap]) if lines else "（无工具步骤）"),
    ]
    if prog:
        parts.append("最后进展: " + prog)
    return "[轮检查点] " + chr(10).join(parts)
