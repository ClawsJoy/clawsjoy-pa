# -*- coding: utf-8 -*-
"""PA 拍板(决策) + 计划时间轴 服务(2026-09-11)。
老板对 PA 产物/步骤拍板(采纳/小改/大改/退回/暂缓), 决策留痕 decision_log.json。
计划: 任务类型→固定步骤模板(确定性, 保证同一任务两次生成一致), 可选 LLM 细化 label。
"""
import json
import time
from pathlib import Path

DECISIONS = ("采纳", "小改", "大改", "退回", "暂缓")

DECISION_ACTIONS = {
    "采纳": {"label": "采纳", "desc": "按现状交付", "pa": "老板已采纳，按现状交付，不必再改。"},
    "小改": {"label": "小改", "desc": "针对指定点微调", "pa": "老板拍板小改，只改老板指定的点，其余不动，改完重新交付。"},
    "大改": {"label": "大改", "desc": "较大范围调整后重做", "pa": "老板拍板大改，较大范围调整后重新执行，不要沿用原方案直接微调。"},
    "退回": {"label": "退回", "desc": "本步重做", "pa": "老板拍板退回，本步重新执行，换思路重做。"},
    "暂缓": {"label": "暂缓", "desc": "先挂起，等老板后续指示", "pa": "老板暂缓，先挂起等待后续指示，不要继续往下做。"},
}

PLAN_BUCKETS = ["调研", "写稿", "出图/排版", "评审", "执行", "交付"]

# 任务类型 → 固定步骤模板(问题4修复: 确定性 stage, 保证同一任务两次生成一致)
# 任务类型 → 固定步骤模板(确定性 stage)。
# 2026-09-13 颗粒度升级: 每步由 (阶段, 说明) 升级为五元组 ——
#   (阶段, 动作说明, produces 产物名(沙箱相对路径, R1), verify 验收项, owner 承接者)
# owner 取 roster 卡名(core/pa/roster.py 内置 6 卡): ds_chat / lingxi /
#   lingxi_local_api / blender / local_vlm / v9_agent
# 每步必须带 verify —— 这是「自学习沉淀」的前提(无 verify 不敢写回模板库)。
TASK_TEMPLATES = {
    "ppt": [
        ("调研", "查口径/政策/审美", "data/reports/materials.md", "列出≥5条依据且含来源", "ds_chat"),
        ("写稿", "写内容大纲", "data/reports/outline.md", "大纲含总页数与每页要点", "ds_chat"),
        ("出图/排版", "排版出图", "data/reports/deck.pptx", "生成 .pptx 且页数=大纲页数", "blender"),
        ("评审", "评审校验", "data/reports/review.md", "逐条核对大纲要点，标出未落实项", "ds_chat"),
        ("交付", "交付产物", "data/reports/delivery.md", "产物路径可打开且评审无未落实项", "ds_chat"),
    ],
    "写文件": [
        ("调研", "明确内容要点", "data/reports/points.md", "列出≥3条要点", "ds_chat"),
        ("写稿", "写正文", "<目标文件>", "文件已写入且非空", "ds_chat"),
        ("评审", "核对校验", "data/reports/review.md", "逐条核对要点是否落实", "ds_chat"),
        ("交付", "交付产物", "data/reports/delivery.md", "产物路径可打开", "ds_chat"),
    ],
    "代码": [
        ("调研", "读代码/查资料", "data/reports/context.md", "定位到目标函数与调用点", "ds_chat"),
        ("写稿", "改代码", "<目标文件>", "改动已落盘且 py_compile 通过", "v9_agent"),
        ("执行", "测试验证", "data/reports/test.log", "测试命令返回码=0", "v9_agent"),
        ("评审", "自查校验", "data/reports/review.md", "逐条核对原始需求", "ds_chat"),
        ("交付", "交付产物", "data/reports/delivery.md", "改动与测试结果可复核", "ds_chat"),
    ],
    "调研": [
        ("调研", "查资料/检索", "data/reports/findings.md", "结论含≥3条依据与来源", "ds_chat"),
        ("交付", "交付结论", "data/reports/report.md", "每条结论可追溯到依据", "ds_chat"),
    ],
    "办公": [
        ("调研", "明确任务", "data/reports/task.md", "复述任务目标(一句话)", "ds_chat"),
        ("执行", "执行操作", "data/reports/result.md", "操作结果可验证", "v9_agent"),
        ("评审", "核对结果", "data/reports/review.md", "逐条核对任务目标", "ds_chat"),
        ("交付", "交付产物", "data/reports/delivery.md", "产物路径可打开", "ds_chat"),
    ],
}


def _detect_task_type(text):
    t = str(text or "").lower()
    if any(k in t for k in ("ppt", "演示", "幻灯片", "slides", "讲义", "排版", "封面", "出图")):
        return "ppt"
    if any(k in t for k in ("代码", "开发", "程序", "脚本", "函数", "bug", "修复", "重构", "实现", "接口", "爬虫")):
        return "代码"
    if any(k in t for k in ("写", "文件", "报告", "文档", "稿", "笔记", "记录", "整理", "生成", "创建")):
        return "写文件"
    if any(k in t for k in ("查", "搜", "调研", "检索", "了解", "找", "是什么", "有哪些", "分析", "对比")):
        return "调研"
    return "办公"


class DecisionStore:
    def __init__(self, data_dir="data/v9/pa"):
        self.dir = Path(data_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "decision_log.json"

    def load(self):
        if self.path.exists():
            try:
                d = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(d, dict) and isinstance(d.get("decisions"), list):
                    return d
            except Exception:
                pass
        return {"decisions": []}

    def record(self, user_id, session_id, node, stage, decision, note="", task=""):
        d = self.load()
        rec = {
            "id": "d" + str(int(time.time() * 1000)),
            "ts": int(time.time()),
            "user_id": user_id or "",
            "session_id": session_id or "",
            "node": node or "",
            "stage": stage or "",
            "decision": decision,
            "note": (note or "").strip(),
            "task": (task or "").strip()[:200],
        }
        d["decisions"].append(rec)
        self.path.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        return rec

    def list(self, user_id=None, session_id=None, limit=100):
        d = self.load()
        out = d["decisions"]
        if user_id:
            out = [x for x in out if x.get("user_id") == user_id]
        if session_id:
            out = [x for x in out if x.get("session_id") == session_id]
        return out[-limit:]


def generate_plan(task_text, mode="work", user_id=None):
    """问题4修复: 任务类型→固定步骤模板(确定性 stage), 可选 LLM 细化 label(不改 stage)。"""
    tt = _detect_task_type(task_text)
    template = TASK_TEMPLATES.get(tt, TASK_TEMPLATES["办公"])
    stages = [t[0] for t in template]
    labels = [t[1] for t in template]
    produces = [t[2] for t in template]
    verifies = [t[3] for t in template]
    owners = [t[4] for t in template]
    try:
        from core.lib.llm_client import LLMClient

        prompt = (
            "你是老板的 PA。任务将按固定阶段执行(顺序与阶段名不可改): %s\n"
            "请为每个阶段各写一句<=12字的动作短语, 贴合任务内容。\n"
            "只输出一个 JSON 字符串数组, 长度 %d, 与阶段一一对应, 不要输出其它文字。\n\n"
            "任务: %s" % ("/".join(stages), len(stages), task_text)
        )
        out = LLMClient().generate(prompt, max_tokens=200)
        if out:
            s = (out or "").strip()
            i = s.find("[")
            j = s.rfind("]")
            if 0 <= i < j:
                arr = json.loads(s[i : j + 1])
                if isinstance(arr, list) and len(arr) == len(stages):
                    arr2 = [str(x).strip()[:20] for x in arr]
                    if all(arr2):
                        labels = arr2
    except Exception:
        pass
    steps = [
        {"stage": s, "label": l, "produces": p, "verify": v, "owner": o}
        for s, l, p, v, o in zip(stages, labels, produces, verifies, owners)
    ]
    return {"steps": steps, "source": "template", "task_type": tt}
