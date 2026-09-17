# -*- coding: utf-8 -*-
"""PA 分派桥 v0(2026-09-10): PA 拆任务 -> TaskContract -> 执行 agent -> 代理审核。

- 契约: 优先复用 core.gateway.task_contract.compile_contract(纯内核); 不可用时降级最小契约
- 执行: Executor 接口 run(contract) -> {ok, artifact, summary};
        真实 V9 用 V9GatewayExecutor(env V9_URL), 测试/演示用 StubExecutor
- 审核: review(contract, result, profile_brief, rules)
        确定性检查: ok/artifact 非空/rules 关键词命中(可选)/拒绝带理由
- 记录: data/v9/pa/dispatch.json 追加(可回放)
"""
import json
import os
import time
from pathlib import Path

DEFAULT_REVIEW_RULES = [
    ("artifact", "执行结果必须有产物(文件/文本/URL), 不能空手交付"),
    ("honest", "结果不得含编造来源/未标注的待核实数字(风格画像: 诚实底线)"),
    ("done", "executor 必须返回 ok=True 且 summary 说明做了什么"),
]


def make_contract(task_text):
    """生成 TaskContract(复用 F0 内核; 失败降级最小契约)。"""
    try:
        from core.gateway.task_contract import compile_contract

        c = compile_contract("pa_task", task_text)
        if c:
            return c
    except Exception:
        pass
    return {
        "task_id": "task_%d" % int(time.time()),
        "objective": task_text,
        "nodes": [{"type": "verify", "question": task_text}],
        "phase": "planned",
        "_fallback": True,
    }


class StubExecutor:
    """演示/测试执行器: 写一个假产物文件。"""

    def __init__(self, out_dir):
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def run(self, contract):
        f = self.out_dir / ("artifact_%s.txt" % contract.get("task_id", "x")[:12])
        f.write_text("PA 分派执行产物: " + str(contract.get("objective", ""))[:200], encoding="utf-8")
        return {"ok": True, "artifact": str(f), "summary": "已产出产物文件 %s" % f.name}


class V9GatewayExecutor:
    """真实执行: 调 live 网关 /v9/agent/chat(独立 session), 返回末条 assistant 文本。"""

    def __init__(self, url=None, user_id="pa_dispatch", session_prefix="pa_dispatch"):
        self.url = (url or os.getenv("V9_URL", "http://127.0.0.1:5002")).rstrip("/")
        self.user_id = user_id
        self.session_prefix = session_prefix

    def run(self, contract):
        import urllib.request

        sid = "%s_%s" % (self.session_prefix, contract.get("task_id", int(time.time())))
        body = json.dumps(
            {
                "user_id": self.user_id,
                "session_id": sid,
                "model": "deepseek-v4-flash",
                "messages": [{"role": "user", "content": str(contract.get("objective", ""))}],
            }
        ).encode()
        req = urllib.request.Request(
            self.url + "/v9/agent/chat", data=body, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                doc = json.loads(r.read().decode("utf-8", "replace"))
            content = ""
            try:
                content = (doc.get("data") or {}).get("choices", [{}])[0].get("message", {}).get("content", "")
            except Exception:
                content = str(doc)[:2000]
            return {"ok": bool(content), "artifact": content[:8000], "summary": "V9 执行返回 %d 字" % len(content or "")}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200], "summary": "V9 调用失败"}


def review(contract, result, profile_brief="", rules=None):
    reasons = []
    for key, desc in rules or DEFAULT_REVIEW_RULES:
        if key == "artifact":
            art = result.get("artifact") or result.get("error") or ""
            if not art:
                reasons.append("缺失产物: " + desc)
        elif key == "done":
            if not result.get("ok"):
                reasons.append("执行未成功: %s (%s)" % (desc, result.get("error", "")))
        elif key == "honest":
            text = str(result.get("artifact") or "") + str(result.get("summary") or "")
            if (
                "未查到" not in text
                and "待核实" not in text
                and any(k in text for k in ["%", "万", "亿"])
                and profile_brief
                and "诚实底线" not in profile_brief
            ):
                pass  # 规则钩子: 数值类产物需人工/vision 复核(有画像宪法时才启用)
    if reasons:
        return {"verdict": "reject", "reasons": reasons}
    return {"verdict": "pass", "reasons": []}


class DispatchRecord:
    def __init__(self, path=None):
        self.path = Path(path or os.getenv("PA_DISPATCH_PATH", "data/v9/pa/dispatch.json"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.rows = []
        if self.path.exists():
            try:
                self.rows = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                self.rows = []

    def add(self, row):
        self.rows.append(row)
        self.path.write_text(json.dumps(self.rows, ensure_ascii=False, indent=1), encoding="utf-8")
        return row


def dispatch_and_review(contract, result, profile_brief="", executor=None, record=None):
    """分派+审核一步: 返回 {task_id, verdict, reasons, result}。"""
    verdict = review(contract, result, profile_brief=profile_brief)
    row = {
        "task_id": contract.get("task_id"),
        "objective": str(contract.get("objective", ""))[:200],
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "verdict": verdict["verdict"],
        "reasons": verdict["reasons"],
        "result_ok": result.get("ok"),
        "artifact_head": str(result.get("artifact") or "")[:120],
    }
    if record is not None:
        record.add(row)
    return row
