# -*- coding: utf-8 -*-
"""TaskContract 契约执行内核(2026-09-09, F0 按 GPT 修正版) — 独立于 bridge loop。

原则:
- 唯一真实状态: data/v9/contracts/{task_id}.json, 由纯 reducer 变更。
- bridge/sync/async/审批恢复只投递事件, 不得自行 complete/改进度。
- completed 只能由 reducer 在 artifact/证据验证满足 active node 后写入。
- waiting_user 是成功暂停(返回问题), 禁止自动续跑。
- terminal=true 的证据 = 公开渠道无法验证是正确结论, 不构成继续重试的理由。
零第三方依赖; 未创建契约时上层行为完全不变(向后兼容)。
"""
import json
import re
import threading
import time
from pathlib import Path

PHASES = (
    "planned",
    "researching",
    "evidence_review",
    "waiting_user",
    "drafting",
    "approval_pending",
    "verifying",
    "completed",
)
_WRITE_PHASES = ("drafting", "approval_pending", "verifying")
_RESEARCH_PHASES = ("planned", "researching", "evidence_review")
_CONTRACTS_DIR = Path("data/v9/contracts")
_LOCK = threading.Lock()
_CLAIM_OK = ("verified", "classified", "unverifiable")


def new_contract(task_id, objective="", nodes=None, budget=None):
    nodes = nodes or []
    return {
        "task_id": task_id,
        "objective": objective,
        "phase": "planned",
        "nodes": nodes,
        "active_node": nodes[0]["id"] if nodes else None,
        "evidence": {},
        "_completed_nodes": [],
        "budget": budget or {"per_phase": 20, "per_domain": 2},
        "checkpoint": {"notes": []},
        "created_at": time.time(),
        "updated_at": time.time(),
    }


def node_done(node_id):
    return {"type": "node_done", "node_id": node_id}


def evidence_updated(claim_id, status, sources=None, attempts=0, next_action="", terminal=False, detail="", claim=""):
    return {
        "type": "evidence",
        "claim_id": claim_id,
        "claim": claim,
        "status": status,
        "sources": sources or [],
        "attempts": attempts,
        "next_action": next_action,
        "terminal": terminal,
        "detail": detail,
    }


def request_user(question, options=None):
    return {"type": "request_user", "question": question, "options": options or []}


def user_answer(answer):
    return {"type": "user_answer", "answer": answer}


def artifact_verified(ok, detail="", artifact=None):
    return {"type": "artifact_verified", "ok": bool(ok), "detail": detail, "artifact": artifact or {}}


def note(text):
    return {"type": "note", "text": text}


def _node_by_id(c, nid):
    for n in c.get("nodes", []):
        if n.get("id") == nid:
            return n
    return None


def _claim_ok(v):
    return isinstance(v, dict) and v.get("status") in _CLAIM_OK


def _dw_ok(c, key):
    key = str(key)
    m = re.match(r"(\d+)\s*[/，]\s*(\d+)", key)
    if m:
        need = int(m.group(1))
        return sum(1 for v in c.get("evidence", {}).values() if _claim_ok(v)) >= need
    if key.startswith("artifact "):
        return bool(c.get("_artifact_ok"))
    if key.startswith("wait_user"):
        return c.get("phase") == "waiting_user"
    return _claim_ok(c.get("evidence", {}).get(key))


def _node_done_met(c, n):
    dw = n.get("done_when") or []
    return all(_dw_ok(c, k) for k in dw)


def _complete_node(c, nid, effects):
    done = set(c.get("_completed_nodes") or [])
    done.add(nid)
    c["_completed_nodes"] = sorted(done)
    return _advance(c, effects)


def _advance(c, effects):
    nodes = c.get("nodes") or []
    done = set(c.get("_completed_nodes") or [])
    for n in nodes:
        nid = n["id"]
        if nid in done:
            continue
        deps = n.get("depends_on") or []
        if not all(d in done for d in deps):
            continue
        ph = n.get("phase")
        if ph == "waiting_user":
            c["phase"] = "waiting_user"
            c["active_node"] = nid
            effects.append({"kind": "ask_user", "question": n.get("ask", "请确认后继续"), "options": n.get("options", [])})
            return c, effects
        c["active_node"] = nid
        if not ph:
            ph = "drafting" if (n.get("artifact_spec") or n.get("phase_hint") == "draft") else "researching"
        c["phase"] = ph
        return c, effects
    if len(done) >= len(nodes):
        c["phase"] = "completed"
        c["active_node"] = None
        effects.append({"kind": "completed"})
    return c, effects


def reduce(contract, event):
    c = json.loads(json.dumps(contract))
    effects = []
    et = (event or {}).get("type", "")
    c["updated_at"] = time.time()
    if et == "note":
        c.setdefault("checkpoint", {}).setdefault("notes", []).append(event.get("text", ""))
        return c, effects
    if et == "evidence":
        cid = event["claim_id"]
        c.setdefault("evidence", {})[cid] = {
            "claim": event.get("claim", ""),
            "status": event.get("status", "unverified"),
            "sources": event.get("sources") or [],
            "attempts": int(event.get("attempts") or 0),
            "next_action": event.get("next_action", ""),
            "terminal": bool(event.get("terminal", False)),
            "detail": event.get("detail", ""),
            "updated_at": time.time(),
        }
        if c.get("phase") == "planned":
            c["phase"] = "researching"
        return c, effects
    if et == "request_user":
        c["phase"] = "waiting_user"
        c.setdefault("checkpoint", {})["question"] = event.get("question", "")
        c.setdefault("checkpoint", {})["options"] = event.get("options", [])
        effects.append({"kind": "ask_user", "question": event.get("question", ""), "options": event.get("options", [])})
        return c, effects
    if et == "user_answer":
        if c.get("phase") == "waiting_user":
            n = _node_by_id(c, c.get("active_node"))
            if n and n.get("phase") == "waiting_user":
                c.setdefault("checkpoint", {})["user_answer"] = event.get("answer", "")
                return _complete_node(c, n["id"], effects)
        return c, effects
    if et == "artifact_verified":
        c["_artifact_ok"] = bool(event.get("ok"))
        n = _node_by_id(c, c.get("active_node"))
        if event.get("ok") and n:
            if n.get("artifact_spec") or not n.get("done_when") or _node_done_met(c, n):
                return _complete_node(c, n["id"], effects)
        elif not event.get("ok") and n and n.get("artifact_spec"):
            c["phase"] = "drafting"
            c.setdefault("checkpoint", {})["last_error"] = event.get("detail", "")
        return c, effects
    if et == "node_done":
        n = _node_by_id(c, event.get("node_id"))
        if n and (not n.get("done_when") or _node_done_met(c, n)):
            return _complete_node(c, n["id"], effects)
        return c, effects
    return c, effects


def _dir():
    try:
        _CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return _CONTRACTS_DIR


def save(contract):
    if not contract or not contract.get("task_id"):
        return None
    with _LOCK:
        try:
            p = _dir() / (str(contract["task_id"]) + ".json")
            p.write_text(json.dumps(contract, ensure_ascii=False, indent=1), encoding="utf-8")
            return str(p)
        except Exception:
            return None


def load(task_id):
    if not task_id:
        return None
    try:
        p = _CONTRACTS_DIR / (str(task_id) + ".json")
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None


def phase_allows_final_write(phase):
    return phase in _WRITE_PHASES


def phase_is_research(phase):
    return phase in _RESEARCH_PHASES


def dispatch(task_id, contract, event):
    new_c, effects = reduce(contract, event)
    save(new_c)
    return new_c, effects


# ========== F0.2a: session 注册表 + 入口 phase gate ==========
_INDEX_FILE = Path("data/v9/contracts/_index.json")
_session_index = {}  # session_id -> task_id(模块级缓存)


def _load_index():
    global _session_index
    if _session_index:
        return _session_index
    try:
        if _INDEX_FILE.exists():
            _session_index = json.loads(_INDEX_FILE.read_text(encoding="utf-8")) or {}
    except Exception:
        _session_index = {}
    return _session_index


def _save_index():
    try:
        _INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
        _INDEX_FILE.write_text(json.dumps(_session_index, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def bind_session(session_id, task_id):
    """task_id<->session 注册(契约存在时调用)。"""
    if not session_id or not task_id:
        return None
    _load_index()
    _session_index[str(session_id)] = str(task_id)
    _save_index()
    return task_id


def contract_for_session(session_id):
    """返回该 session 绑定的契约(无则 None — 上层保持旧行为)。"""
    if not session_id:
        return None
    _load_index()
    task_id = _session_index.get(str(session_id))
    return load(task_id) if task_id else None


# 验证阶段允许的工具(只验证+修复; 研究工具一律挡)
_VERIFY_ALLOWED_PREFIX = (
    "read_file",
    "list_dir",
    "search_files",
    "write_file",
    "execute_command",
    "edit_file",
    "obsidian_knowledge",
)
_RESEARCH_TOOLS = (
    "web_search",
    "fetch_web",
    "browse_web",
    "browser_local",
    "playwright_browser",
    "browser_hybrid",
    "table_extract",
)


def phase_gate(contract, tool):
    """入口级工具闸: (allowed, steer)。waiting_user 由上层短路, 不在此放行执行。"""
    if not contract:
        return True, None
    phase = contract.get("phase") or ""
    tool = str(tool or "")
    if phase == "researching":
        return True, None  # 检索/读/证据写入均允许
    if phase == "verifying":
        if tool in _RESEARCH_TOOLS:
            return False, ("[系统] 当前任务处于 verifying 阶段(只验证与修复), 禁止继续检索/抓取。" "请只读回产物并核对验收条件, 必要时修复后重跑验证。")
        return True, None
    return True, None


def should_require_final_write(session_id):
    """F0.2a: 假完成守卫是否要求最终写入。
    有契约且 phase 为研究类 → False(研究阶段不要求写最终文件, 不触发假完成);
    无契约 → None(上层沿用关键词旧逻辑)。"""
    c = contract_for_session(session_id)
    if c is None:
        return None
    return phase_allows_final_write(c.get("phase") or "")


def waiting_user_payload(session_id):
    """waiting_user 短路负载: {status, question, options} 或 None。"""
    c = contract_for_session(session_id)
    if c and c.get("phase") == "waiting_user":
        cp = c.get("checkpoint") or {}
        return {
            "status": "waiting_user",
            "question": cp.get("question") or cp.get("user_answer") or "",
            "options": cp.get("options") or [],
            "task_id": c.get("task_id"),
        }
    return None


# ========== F0.2b: 轻量任务编译(用户消息 → 契约; 失败回退 None) ==========
import re as _re_c

_NEW_TASK_VERBS = ("生成", "制作", "写", "输出", "创建", "新建", "保存", "落盘", "补全")
_ART_RE = _re_c.compile(r"(data/[\w./\-\u4e00-\u9fff]+\.(?:md|pptx?|py|json))")
_ORDER_RE = _re_c.compile(r"(先[^，。]*?再[^，。]*?|核实[^，。]*?(?:后|再)[^，。]*|.*?后[，,]?\s*(?:生成|制作|输出))")


def _guess_artifact(msg):
    m = _ART_RE.search(msg or "")
    if m:
        return {"path": m.group(1)}
    if any(k in (msg or "") for k in ("PPT", "PPTX", "大纲")):
        return {"path": "data/reports/output.md"}
    if "报告" in (msg or ""):
        return {"path": "data/reports/report.md"}
    return None


def compile_contract(task_id, user_msg, objective=""):
    """轻量编译: 识别 核实→等待确认→生成 链; 无法识别返回 None(上层回退无契约)。
    输出节点: verify(researching, done_when=claim 计数) / ask(waiting_user) / gen(drafting, artifact_spec)。"""
    msg = str(user_msg or "")
    if not msg.strip() or not any(k in msg for k in ("核实", "调研", "检索", "生成", "制作", "输出", "PPT", "报告", "大纲")):
        return None
    nodes = []
    if any(k in msg for k in ("核实", "调研", "检索", "搜索")):
        nodes.append(
            {"id": "verify", "depends_on": [], "phase": "researching", "phase_hint": "research", "done_when": []}
        )
    if any(k in msg for k in ("确认", "风格", "视觉", "请你", "请确认", "选")):
        ask_q = "请确认下一步(如视觉/版式风格)?"
        m2 = _re_c.search(r"(视觉风格|版式|风格|视觉)[^，。?？]*", msg)
        if m2:
            ask_q = "请确认" + m2.group(0) + "?"
        nodes.append(
            {
                "id": "ask_style",
                "depends_on": ["verify"] if nodes else [],
                "phase": "waiting_user",
                "ask": ask_q,
                "options": ["工业科技风", "产业资本风", "政府申报风"],
            }
        )
    art = _guess_artifact(msg)
    if any(k in msg for k in ("生成", "制作", "输出", "保存", "PPT", "PPTX", "大纲", "报告", "补全")):
        nodes.append(
            {
                "id": "gen",
                "depends_on": ([n["id"] for n in nodes] if nodes else []),
                "phase": "drafting",
                "artifact_spec": art or {"path": "data/reports/output.md"},
            }
        )
    if not nodes:
        return None
    c = new_contract(task_id, objective=objective or msg[:80], nodes=nodes)
    save(c)
    return c


def ensure_contract(session_id, task_id, user_msg):
    """F0.2b 入口: session 无契约且消息可编译 → 创建并绑定; 返回契约或 None。"""
    if contract_for_session(session_id):
        return contract_for_session(session_id)
    c = compile_contract(task_id, user_msg)
    if c:
        bind_session(session_id, task_id)
    return c


# ========== F0.5: 单一完成裁决(上层只调用 decide_completion, 不再自行 complete) ==========
def decide_completion(contract, artifact_ok, detail="", artifact=None):
    """上层完成任务收尾时的唯一裁决入口:
    无契约 → (None, None) 上层沿用旧 complete_goal;
    有契约 → 投递 artifact_verified, reducer 判定; 返回 (new_contract, effects)。
    """
    if contract is None:
        return None, None
    new_c, effects = reduce(contract, artifact_verified(ok=artifact_ok, detail=detail, artifact=artifact or {}))
    save(new_c)
    return new_c, effects


def contract_should_complete(contract):
    """reducer 裁决是否已完成(供上层 propagate complete_goal)。"""
    return bool(contract) and contract.get("phase") == "completed"


# ========== F0.2b-final: 首轮 auto-bind + goal↔contract 绑定校验 ==========
def first_round_autobind(session_id, task_id, user_msg):
    """新任务首轮: 仅当可编译出>=2 节点链(核实/确认+生成)才建契约绑定;
    单节点或闲聊 → 不绑(零回归)。返回 (contract|None, bound:bool)。"""
    if contract_for_session(session_id):
        return contract_for_session(session_id), True
    c = compile_contract(task_id, user_msg)
    if c and len(c.get("nodes") or []) >= 2:
        bind_session(session_id, task_id)
        return c, True
    return None, False


def _norm_obj(txt):
    import re as _re_n

    return re.sub(r"[\s，。,.、:：\-—]+", "", str(txt or ""))[:60]


def binding_mismatch(goal_objective, contract):
    """goal↔contract 绑定校验: 目标原文与契约 objective 明显不一致 → True(应停问)。
    无契约 → False(不拦截)。"""
    if contract is None:
        return False
    co = str(contract.get("objective") or "")
    go = str(goal_objective or "")
    if not co or not go:
        return False
    import difflib as _df_n

    a, b = _norm_obj(go), _norm_obj(co)
    if not a or not b:
        return False
    return _df_n.SequenceMatcher(None, a, b).ratio() < 0.6
