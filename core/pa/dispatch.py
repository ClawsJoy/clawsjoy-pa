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
import sys
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
    """分派记录 —— append-only JSONL（DS 2026-09-18 拍「改真 append」；X-16 方案稿 §九.2）。

    为什么不再用 ``dispatch.json``（顶层 JSON 数组）：
      · 旧 ``add()`` = 「读全量 → 追加 → **整文件重写**」⇒ 每次追加都重写全部历史（非原子，
        写一半崩 ⇒ 历史全丢）；且「顶层数组」与统一出口 ``StateFile``（只认顶层 dict）是两种
        模型 ⇒ 接不了出口（X-16 方案稿 §十.3）。
      · 改成一行一条后：追加只写**一行**、历史不重写；坏也只坏一行，可逐行定位与上报。
    同模型先例：``core/pa/events.py``（``EventLog``）已是 ``events.jsonl``。
    读语义（与 X-17① 同族，但**伤害模型不同 ⇒ 处置不同**）：
      · 文件不存在 ⇒ 空历史（新用户正常，**不是**损坏）；
      · **单行**不可解析／非对象／缺 ``task_id`` ⇒ 跳过该行并**计数 + 报 stderr**。
        理由：append-only 的坏行**不会**导致后续覆盖（没有「读不动就当空基线再写」这条链），
        故不按状态文件那样抛；但**必须可见** —— 不静默，也不把损坏当空历史（经验库 L-08）。
    兼容：同名 ``.json``（旧数组）存在时**只读**它作为更早的历史基线，**不改写、不迁移**。
    """

    def __init__(self, path=None):
        self.path = Path(path or os.getenv("PA_DISPATCH_PATH", "data/v9/pa/dispatch.jsonl"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.legacy_path = self.path.with_suffix(".json") if self.path.suffix == ".jsonl" else None
        self.corrupt_lines = 0
        self.rows = self._load()

    def _report(self, msg):
        self.corrupt_lines += 1
        try:
            sys.stderr.write("[dispatch] %s\n" % msg)
        except Exception:
            pass

    def _load(self):
        rows = []
        if self.legacy_path is not None and self.legacy_path.exists():
            try:
                old = json.loads(self.legacy_path.read_text(encoding="utf-8"))
            except Exception as e:
                self._report("旧格式历史不可解析（只读跳过，未改写）：%s（%s）" % (self.legacy_path, type(e).__name__))
            else:
                if isinstance(old, list):
                    rows.extend(r for r in old if isinstance(r, dict))
                else:
                    self._report("旧格式历史不是数组（只读跳过，未改写）：%s" % self.legacy_path)
        if self.path.exists():
            for no, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except Exception as e:
                    self._report("第 %d 行不可解析（%s）——已跳过该行，其余历史保留" % (no, type(e).__name__))
                    continue
                if not isinstance(row, dict) or not str(row.get("task_id") or "").strip():
                    self._report("第 %d 行结构不符（须为含非空 task_id 的对象）——已跳过该行，其余历史保留" % no)
                    continue
                rows.append(row)
        return rows

    def add(self, row):
        """追加一条：**先自检结构 → 单行追加 → 读回校验**（假成交红线：读回不一致就抛）。"""
        if not isinstance(row, dict) or not str(row.get("task_id") or "").strip():
            raise ValueError("dispatch 记录必须是含非空 task_id 的对象（拒绝写入）")
        line = json.dumps(row, ensure_ascii=False)
        blob = (line + "\n").encode("utf-8")
        with open(self.path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(line + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        if not self.path.read_bytes().endswith(blob):
            raise RuntimeError("dispatch 追加未生效（读回不一致）：%s" % self.path)
        self.rows.append(row)
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
