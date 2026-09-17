# -*- coding: utf-8 -*-
"""P4: Computer Use 学习循环 + SOP 生成器(纯逻辑, 可单测)。

设计: docs/reports/computer_use_agent_design_20260904.md §4/§5
- 任务开始: 显式列出可验证完成条件(completion)与失败判据(fail_if)
- 操作序列: data/computer_use/plans/{task_id}_{plan_id}.jsonl
- 停止规则: 同意图连续失败>2 或 连续失败>=3 或 累计失败>3 → 停止出失败报告
- 学会判定: 同 task_key 成功运行 >=2 次 → 生成 SOP
- 防假完成: complete 需 completion 条件有证据满足, 否则拒绝
失败分类: 选择错/执行错/风控/选择器失效/超时/歧义
"""
import json
import os
import re
import time

DEFAULT_PLAN_DIR = "data/computer_use/plans"
DEFAULT_SOP_DIR = "data/computer_use/sops"

# 失败分类(从 browser_hybrid 错误文本/页面特征)
_CATEGORY_RULES = [
    ("风控", re.compile(r"安全验证|验证码|captcha|滑块|wappass|anti-?bot|异常访问")),
    ("选择器失效", re.compile(r"不可见|未找到可编辑|重定位失败|DOM 已变|定位失败|no such element|waiting for locator")),
    ("超时", re.compile(r"timeout|超时|Timeout")),
    ("选择错", re.compile(r"双检不一致|role 不匹配|role 校验|模型返回0|越界|非整数")),
    ("执行错", re.compile(r"act .*失败|Page\.(click|fill)|Error:")),
]


def classify_failure(text):
    """按 风控/选择器失效/超时/选择错/执行错/歧义 分类失败(设计 §4 失败分类)。"""
    t = str(text or "")
    for cat, pat in _CATEGORY_RULES:
        if pat.search(t):
            return cat
    # 2026-09-13 修子串误伤："ask" in t 会把 **task** 也算命中（含 task 的失败文本永远判「歧义」）。
    # 改为词边界匹配（前后补空格判词，不引入正则 —— 避免又一次转义事故）。
    if (" ask " in (" " + t + " ")) or "歧义" in t or "人工" in t:
        return "歧义"
    return "执行错"


def _plan_path(plan_dir, task_id, plan_id):
    return os.path.join(plan_dir, "%s_%s.jsonl" % (task_id, plan_id))


def _meta_path(plan_dir, task_id, plan_id):
    return os.path.join(plan_dir, "%s_%s.meta.json" % (task_id, plan_id))


def start_plan(plan_dir, task_id, objective, completion=None, fail_if=None, task_key=None, extra=None):
    """任务开始: 记录目标 + 可验证完成条件 + 失败判据; 返回 plan dict。

    completion: [{check: url_contains|text_visible, target: str, note: str}]
    fail_if:    [{check..., target...}] (可选: 出现即失败)
    """
    os.makedirs(plan_dir, exist_ok=True)
    plan_id = str(int(time.time() * 1000))
    plan = {
        "plan_id": plan_id,
        "task_id": task_id,
        "task_key": task_key or task_id,
        "objective": objective,
        "completion": completion or [],
        "fail_if": fail_if or [],
        "status": "running",
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "steps_ok": 0,
        "steps_fail": 0,
    }
    if extra:
        plan.update(extra)
    with open(_meta_path(plan_dir, task_id, plan_id), "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=1)
    # 初始化 jsonl(写入首行 meta 注释便于人工查阅)
    with open(_plan_path(plan_dir, task_id, plan_id), "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": plan["created"], "kind": "start", "objective": objective}, ensure_ascii=False) + "\n")
    return plan


def log_step(plan_dir, task_id, plan_id, row):
    """记录一步(成功/失败), 更新 meta 计数; 返回更新后的 state。"""
    row = dict(row or {})
    row["ts"] = row.get("ts") or time.strftime("%Y-%m-%d %H:%M:%S")
    p = _plan_path(plan_dir, task_id, plan_id)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return plan_state(plan_dir, task_id, plan_id)


def plan_state(plan_dir, task_id, plan_id):
    """从 jsonl 推导 成功/失败/连续失败/分类/同意图失败 计数与停止判定。"""
    state = {
        "ok": 0,
        "fail": 0,
        "consecutive_fail": 0,
        "total_fail": 0,
        "categories": {},
        "by_intent_fail": {},
        "stop": False,
        "stop_reason": "",
    }
    rows = []
    p = _plan_path(plan_dir, task_id, plan_id)
    if os.path.exists(p):
        for ln in open(p, encoding="utf-8"):
            ln = ln.strip()
            if not ln:
                continue
            try:
                r = json.loads(ln)
            except Exception:
                continue
            if r.get("kind") == "start":
                continue
            rows.append(r)
    consec = 0
    last_intent = None
    intent_fail = 0
    for r in rows:
        ok = bool(r.get("ok"))
        if ok:
            state["ok"] += 1
            consec = 0
            last_intent = None
            intent_fail = 0
        else:
            state["fail"] += 1
            state["total_fail"] += 1
            consec += 1
            state["consecutive_fail"] = consec
            cat = r.get("category") or classify_failure(r.get("error") or "")
            state["categories"][cat] = state["categories"].get(cat, 0) + 1
            intent = str(r.get("intent") or "")
            if intent == last_intent:
                intent_fail += 1
            else:
                intent_fail = 1
                last_intent = intent
            state["by_intent_fail"][intent] = state["by_intent_fail"].get(intent, 0) + 1
            # 停止规则(设计 §4.4): 同一意图重试>2 最优先; 其次连续>=3; 再累计>3
            if intent_fail > 2:
                state["stop"] = True
                state["stop_reason"] = "同一意图 %r 失败 %d 次(单步重试上限2), 停止" % (intent, intent_fail)
                break
            if consec >= 3:
                state["stop"] = True
                state["stop_reason"] = "连续 %d 步失败, 停止并输出失败报告" % consec
                break
            if state["total_fail"] > 3:
                state["stop"] = True
                state["stop_reason"] = "累计失败 %d 步(上限3), 停止" % state["total_fail"]
                break
    state["rows"] = rows
    return state


def evidence_satisfies(cond, evidence):
    """单条完成条件是否被证据满足(设计 §4.2 硬断言)。"""
    ev = evidence or {}
    check = cond.get("check")
    target = str(cond.get("target") or "")
    if check == "url_contains":
        return bool(target and target in str(ev.get("url") or ""))
    if check == "text_visible":
        return bool(target and target in str(ev.get("text") or ev.get("head") or ""))
    if check == "field_value":
        return bool(str(ev.get("field_value") or "") == target)
    if check == "explicit":
        return bool(ev.get("result") is True)
    return False


def complete_run(plan_dir, task_id, plan_id, evidence=None, report=""):
    """完成判定(防假完成): 全部 completion 条件须被证据满足; 返回 result。

    result: {"ok": bool, "reason": str, "success_runs": int, "sop_ready": bool}
    """
    meta_p = _meta_path(plan_dir, task_id, plan_id)
    meta = {}
    if os.path.exists(meta_p):
        try:
            meta = json.load(open(meta_p, encoding="utf-8"))
        except Exception:
            pass
    conds = meta.get("completion") or []
    if conds:
        missing = [c for c in conds if not evidence_satisfies(c, evidence)]
        if missing:
            return {
                "ok": False,
                "reason": "完成条件无证据: %s (防假完成)" % [c.get("note") or c.get("target") for c in missing],
                "success_runs": 0,
                "sop_ready": False,
            }
    # 成功标记: 写 status=success + evidence + report
    meta["status"] = "success"
    meta["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    meta["evidence"] = evidence or {}
    meta["report"] = str(report or "")[:500]
    with open(meta_p, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    n = count_successes(plan_dir, meta.get("task_key") or task_id)
    return {"ok": True, "reason": "", "success_runs": n, "sop_ready": n >= 2}


def abort_plan(plan_dir, task_id, plan_id, reason=""):
    meta_p = _meta_path(plan_dir, task_id, plan_id)
    if os.path.exists(meta_p):
        try:
            meta = json.load(open(meta_p, encoding="utf-8"))
            meta["status"] = "failed"
            meta["stop_reason"] = str(reason or "")
            with open(meta_p, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=1)
        except Exception:
            pass


def count_successes(plan_dir, task_key):
    """同 task_key 的成功运行次数(学会判定: >=2 生成 SOP)。"""
    n = 0
    if not os.path.isdir(plan_dir):
        return 0
    for fn in os.listdir(plan_dir):
        if not fn.endswith(".meta.json"):
            continue
        try:
            m = json.load(open(os.path.join(plan_dir, fn), encoding="utf-8"))
        except Exception:
            continue
        if (m.get("task_key") or m.get("task_id")) == task_key and m.get("status") == "success":
            n += 1
    return n


def _anchor_of(row):
    return {"role": row.get("role"), "label": row.get("label"), "sel": row.get("sel")}


def build_sop(plan_dir, task_key, meta=None, rows=None):
    """从成功运行的 plan 提炼 SOP markdown(设计 §5 格式)。"""
    # 找 task_key 最新成功运行
    best = None
    if os.path.isdir(plan_dir):
        cands = []
        for fn in os.listdir(plan_dir):
            if not fn.endswith(".meta.json"):
                continue
            try:
                m = json.load(open(os.path.join(plan_dir, fn), encoding="utf-8"))
            except Exception:
                continue
            if (m.get("task_key") or m.get("task_id")) == task_key and m.get("status") == "success":
                cands.append(m)
        if cands:
            best = max(cands, key=lambda m: m.get("created") or "")
    if meta is None:
        meta = best or {}
    if rows is None and best:
        pid = best.get("plan_id")
        tid = best.get("task_id")
        rows = []
        p = _plan_path(plan_dir, tid, pid)
        if os.path.exists(p):
            for ln in open(p, encoding="utf-8"):
                try:
                    r = json.loads(ln)
                except Exception:
                    continue
                if r.get("kind") == "start" or not r.get("ok"):
                    continue
                rows.append(r)
    n_success = count_successes(plan_dir, task_key)
    target_url = meta.get("target_url") or meta.get("extra", {}).get("target_url") or ""
    lines = [
        "---",
        "type: cu-sop",
        "target_url: %s" % target_url,
        "task: %s" % (meta.get("objective") or task_key),
        "verified: %s" % time.strftime("%Y-%m-%d"),
        "success_runs: %d" % n_success,
        "steps: %d" % len(rows or []),
        "tags: [ComputerUse, SOP]",
        "---",
        "# CU-SOP：%s" % (meta.get("objective") or task_key),
        "",
        "## 前置",
        "- 入口 URL：%s" % (target_url or "(目标页打开后开始)"),
        "- 触发意图：%s" % (meta.get("objective") or ""),
        "- 完成条件：%s" % "; ".join("%s=%s" % (c.get("check"), c.get("target")) for c in (meta.get("completion") or [])),
        "",
        "## 步骤",
    ]
    for i, r in enumerate(rows or [], start=1):
        a = _anchor_of(r)
        lines.append("%d. 意图：%s" % (i, r.get("intent")))
        lines.append("   锚点：role=%s + label=%s（sel 建议 %s）" % (a["role"], a["label"], a["sel"]))
        act = r.get("action") or ""
        val = r.get("value") or ""
        lines.append("   动作：%s%s；验证：%s" % (act, (" " + val) if val else "", r.get("verify_note") or "(下一步成功即验证)"))
    lines += ["", "## 失败已知"]
    fails = []
    if rows:
        for r in rows:
            if not r.get("ok") and r.get("error"):
                fails.append("%s：%s" % (r.get("category") or "失败", str(r.get("error"))[:80]))
    lines.append("\n".join(("- " + f) for f in (dict.fromkeys(fails) if fails else [])) or "- （暂无记录）")
    return "\n".join(lines)


def run_action(params, plan_dir=None):
    """cu_learning 工具入口(gateway_helpers 委托): start/log_step/state/complete/abort/count/sop。"""
    action = (params or {}).get("action") or ""
    plan_dir = plan_dir or params.get("plan_dir") or DEFAULT_PLAN_DIR
    task_id = str(params.get("task_id") or "")
    plan_id = str(params.get("plan_id") or "")
    if action == "start":
        if not task_id:
            return {"success": False, "error": "start 需要 task_id"}
        plan = start_plan(
            plan_dir,
            task_id,
            str(params.get("objective") or ""),
            completion=params.get("completion"),
            fail_if=params.get("fail_if"),
            task_key=params.get("task_key"),
            extra={"target_url": params.get("target_url") or ""},
        )
        return {"success": True, "action": "start", "plan_id": plan["plan_id"], "plan": plan}
    if action in ("log_step", "step"):
        if not (task_id and plan_id):
            return {"success": False, "error": "log_step 需要 task_id + plan_id"}
        row = {
            "intent": params.get("intent"),
            "action": params.get("op"),
            "index": params.get("index"),
            "sel": params.get("sel"),
            "role": params.get("role"),
            "label": params.get("label"),
            "ok": bool(params.get("ok")),
            "category": params.get("category"),
            "error": params.get("error"),
            "evidence": params.get("evidence"),
            "value": params.get("value"),
            "verify_note": params.get("verify_note"),
        }
        state = log_step(plan_dir, task_id, plan_id, row)
        return {
            "success": True,
            "action": "log_step",
            "state": state,
            "stop": state.get("stop"),
            "stop_reason": state.get("stop_reason"),
        }
    if action == "state":
        if not (task_id and plan_id):
            return {"success": False, "error": "state 需要 task_id + plan_id"}
        return {"success": True, "action": "state", "state": plan_state(plan_dir, task_id, plan_id)}
    if action == "complete":
        if not (task_id and plan_id):
            return {"success": False, "error": "complete 需要 task_id + plan_id"}
        res = complete_run(
            plan_dir, task_id, plan_id, evidence=params.get("evidence"), report=params.get("report") or ""
        )
        return {"success": res["ok"], "action": "complete", **res}
    if action == "abort":
        abort_plan(plan_dir, task_id, plan_id, params.get("reason") or "")
        return {"success": True, "action": "abort"}
    if action == "count":
        return {
            "success": True,
            "action": "count",
            "task_key": str(params.get("task_key") or task_id),
            "success_runs": count_successes(plan_dir, str(params.get("task_key") or task_id)),
        }
    if action == "telemetry":
        return {"success": True, "action": "telemetry", "stats": telemetry(plan_dir)}
    if action in ("sop", "generate_sop"):
        task_key = str(params.get("task_key") or task_id)
        md = build_sop(plan_dir, task_key)
        if not md or "## 步骤" not in md:
            return {"success": False, "error": "无可用成功运行, 无法生成 SOP(success_runs>=2 才生成)", "action": "sop"}
        title = str(params.get("title") or (task_key + "-cu-sop"))
        sandbox_path = ""
        try:
            os.makedirs(DEFAULT_SOP_DIR, exist_ok=True)
            sandbox_path = os.path.join(DEFAULT_SOP_DIR, "%s.md" % title)
            with open(sandbox_path, "w", encoding="utf-8") as f:
                f.write(md)
        except Exception:
            pass
        vault = persist_sop(md, title)
        return {"success": True, "action": "sop", "md": md, "sandbox_path": sandbox_path, "vault_path": vault}
    return {"success": False, "error": "unsupported action: %r(start/log_step/state/complete/abort/count/sop)" % action}


def persist_sop(md, title):
    """尽力写 vault ComputerUseSOPs/(网关侧 precision_inject 通道); 无 vault 环境返回 None。"""
    try:
        from core.gateway.precision_inject import write_vault_note as _wvn

        return _wvn(str(title), md, folder="ComputerUseSOPs")
    except Exception:
        return None


def _parse_ts(s):
    """解析 meta 时间(created/finished)为 epoch; 失败返回 None。"""
    try:
        return time.mktime(time.strptime(str(s), "%Y-%m-%d %H:%M:%S"))
    except Exception:
        return None


def telemetry(plan_dir):
    """P5 遥测: 汇总 plans 目录全部运行 — 成功率/耗时/失败分类。

    返回 {"total_runs", "success_runs", "fail_runs", "interrupted_runs",
          "success_rate", "duration_avg_s", "duration_total_s",
          "categories": {分类:次数}, "by_task": {task_key: {...}}}
    """
    agg = {
        "total_runs": 0,
        "success_runs": 0,
        "fail_runs": 0,
        "interrupted_runs": 0,
        "durations": [],
        "categories": {},
        "by_task": {},
    }
    if not os.path.isdir(plan_dir):
        return agg
    files = sorted(os.listdir(plan_dir))
    metas = {}
    for fn in files:
        if fn.endswith(".meta.json"):
            try:
                metas[fn] = json.load(open(os.path.join(plan_dir, fn), encoding="utf-8"))
            except Exception:
                continue
    for fn, m in metas.items():
        task_key = m.get("task_key") or m.get("task_id") or "?"
        bt = agg["by_task"].setdefault(
            task_key, {"runs": 0, "success": 0, "fail": 0, "interrupted": 0, "categories": {}}
        )
        bt["runs"] += 1
        agg["total_runs"] += 1
        status = m.get("status")
        if status == "success":
            agg["success_runs"] += 1
            bt["success"] += 1
        elif status == "failed":
            agg["fail_runs"] += 1
            bt["fail"] += 1
        else:
            agg["interrupted_runs"] += 1
            bt["interrupted"] += 1
        t0 = _parse_ts(m.get("created"))
        t1 = _parse_ts(m.get("finished"))
        if t0 and t1 and t1 >= t0:
            d = t1 - t0
            agg["durations"].append(d)
    # 失败分类: 遍历全部 jsonl(跳过 start 与 ok 行)
    for fn in files:
        if not fn.endswith(".jsonl"):
            continue
        jp = os.path.join(plan_dir, fn)
        try:
            rows = open(jp, encoding="utf-8").readlines()
        except Exception:
            continue
        for ln in rows:
            try:
                r = json.loads(ln)
            except Exception:
                continue
            if r.get("kind") == "start" or r.get("ok"):
                continue
            cat = r.get("category") or classify_failure(r.get("error") or "")
            agg["categories"][cat] = agg["categories"].get(cat, 0) + 1
    agg["success_rate"] = (agg["success_runs"] / agg["total_runs"]) if agg["total_runs"] else 0.0
    agg["duration_avg_s"] = (sum(agg["durations"]) / len(agg["durations"])) if agg["durations"] else 0.0
    agg["duration_total_s"] = sum(agg["durations"])
    return agg
