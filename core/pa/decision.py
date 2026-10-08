# -*- coding: utf-8 -*-
"""PA 拍板(决策) + 计划时间轴 服务(2026-09-11)。
老板对 PA 产物/步骤拍板(采纳/小改/大改/退回/暂缓), 决策留痕 decision_log.json。
计划: 任务类型→固定步骤模板(确定性, 保证同一任务两次生成一致), 可选 LLM 细化 label。

2026-09-18（X-16 批 B · DS 拍 A）：**读写走统一出口**（`core/pa/state_out`）；
坏状态 fail-loud（此前 `load()` 静默回落 `{"decisions": []}` ⇒ 下一次 `record()` 即覆写裁决历史）。
"""
import json
import time
from pathlib import Path

from core.pa.state_out import read_state, write_state

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


#: 写者标识（进出口的写者归属台账；供 detect_uninstrumented 识别绕过出口的写者）
_WRITER = "pa.decision"


def _shape(doc):
    """**PA 侧业务结构判据**（DS 拍①：判据留 PA 侧，不给出口加回调）。"""
    if not isinstance(doc.get("decisions"), list):
        return False, "decisions 需为 list"
    return True, ""


#: ⭐ T2-刀19-补 §二：拍板之**用途**分类（`验收 ／ 自检 ／ 测试`之拍板会被前填为面之「拍板来源」）
NONBUSINESS_MARKS = (u'验收', u'自检', u'复验', u'selfcheck', u'selftest', u'e2e', u'canary',
                     u'探针', u'测试', u'test', u'probe', u'干跑')


def usage_of(rec):
    u'''拍板之**用途**：`业务` ∨ `非业务`（返回 `(用途, 命中词)`）。

    ⭐ 由（PM 刀19-补 §二）：T1 交付面之「拍板来源」取**后端 log 之最新「采纳」** ⇒ 验收之拍板
    会**前填**为业务之来源（污染）。分类 ⇒ 面之默认唯**业务**（⛔ 删行：非业务另栏照录）。
    '''
    blob = u' '.join(str((rec or {}).get(k) or '') for k in ('task', 'note', 'session_id'))
    low = blob.lower()
    for m in NONBUSINESS_MARKS:
        if m.lower() in low:
            return u'非业务', m
    return u'业务', ''


def split_by_usage(rows):
    u'''按用途分栏：返回 `(业务行, 非业务行)`（皆**原行** · ⛔ 改值）。'''
    biz, nb = [], []
    for r in (rows or []):
        (biz if usage_of(r)[0] == u'业务' else nb).append(r)
    return biz, nb


class DecisionStore:
    def __init__(self, data_dir="data/v9/pa"):
        self.dir = Path(data_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "decision_log.json"

    def load(self):
        """**不存在 ⇒ 空；存在但不可用 ⇒ 抛 PAStateCorrupt**（不再静默回落空裁决历史）。"""
        if not self.path.exists():
            return {"decisions": []}
        return read_state(self.path, _WRITER, _shape)

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
        write_state(self.path, _WRITER, _shape, d, reason="pa.decision.record")
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
    """问题4修复: 任务类型→固定步骤模板(确定性 stage), 可选 LLM 细化 label(不改 stage)。

    ⭐ PM 2110 §一（`source` 之标**不实** · 归我域）：回执之 `source` **按实书** ——
       细化**成** ⇒ `llm`；否则 ⇒ `template`（此前**恒书** `template` ⇒ 面 `renderPlan` 直书之 ⇒
       **屏上之字与实不合** · 违「不实之辞 ⛔ 入屏」）。其义 ＝ **label 之出处**（stage 恒自模板）。
    ⭐ PM 2110 §二.2（⛔ 静默之败）：模型之跑**留痕**于 `refine`（`ok` ／ `ms` ／ `error`）——
       读者可辨「回空」（`error` ＝ 模型回空）与「跑而败」（`error` ＝ 异常类名 ＋ 首句）
       （此前 `except: pass` ⇒ 二态一名蔽）。⚠ 超时**已自带**（`LLMClient._call`：远端 `or 60` ／
       本机 `or config.timeout`＝120）⇒ ⛔ 另设（免改其语义）。
    ⭐ PM 2112 §三（`route` 之显形 · 出机明书之雏）：回执入 `route` —— 本轮**实际所走**之路
       （`provider` ／ `model` ／ `fell_back` ／ `reason` · 取自 `LLMClient.get_last_route()` ⇒ **⛔ 猜**）。
    ⭐ PM 2112 §三.5（其速 · 归我域）：模型名**唯自** `core.pa.providers.default_route()`（注册表之
       **一处定形**）—— 旧形之调用 **⛔ 给 model** ⇒ `_call` 落 `LLMConfig.default_model`
       （**本机 qwen**）⇒ 云端诸支**永不入**（一手实测 `get_last_route()` ＝ ollama ／ `fell_back` False）
       ⇒ 与注册表「默认 ＝ remote:deepseek」**二处漂**。
    ⭐ PM 2117 §三.2（裁：准提 · **一处定形**）：`max_tokens` 唯自注册表之 `default_max_tokens()`
       （⛔ 硬编 `200` ／ `800`）—— 旧 `200` 于**推理模型**（deepseek-v4-flash）必被 `reasoning`
       之额耗尽 ⇒ `API_EMPTY: finish_reason=length` ⇒ 白调二（一手：日志逐字）。
    ⭐ PM 2117 §三.3（照实 · 白调须可查）：`refine` 并载 `max_tokens`（**实用**值）＋ `attempts`
       （试数 · 自 `LLMClient.get_last_attempts()` · ⛔ 猜）。
    """
    tt = _detect_task_type(task_text)
    template = TASK_TEMPLATES.get(tt, TASK_TEMPLATES["办公"])
    stages = [t[0] for t in template]
    labels = [t[1] for t in template]
    produces = [t[2] for t in template]
    verifies = [t[3] for t in template]
    owners = [t[4] for t in template]
    #: 细化之痕（一处定形）：`ok` ＝ 模型之 label 已采纳；`error` 空而 `ok` 假 ⇒ ⛔ 有（今无此态）。
    refine = {"ok": False, "ms": 0, "error": "", "max_tokens": 0, "attempts": 0}
    route = {}
    _c = None
    _rt_note = ""
    _t0 = time.time()
    try:
        from core.lib.llm_client import LLMClient
        from core.pa.providers import default_route as _default_route
        from core.pa.providers import default_max_tokens as _default_max_tokens

        # ⭐ 注册表之**一处定形**（⛔ 硬编模型名 · 承 pm_1468 §二.1）—— 旧形 ⛔ 给 model ⇒ 必落本机。
        _rt, _rt_note = _default_route()
        # ⭐ pm_2117 §三.2：额度亦唯自注册表（与 gateway_routes.py:295 同法 · 一处配）。
        try:
            _mt = int(_default_max_tokens())
        except Exception:
            _mt = 1600
        refine["max_tokens"] = _mt

        prompt = (
            "你是老板的 PA。任务将按固定阶段执行(顺序与阶段名不可改): %s\n"
            "请为每个阶段各写一句<=12字的动作短语, 贴合任务内容。\n"
            "只输出一个 JSON 字符串数组, 长度 %d, 与阶段一一对应, 不要输出其它文字。\n\n"
            "任务: %s" % ("/".join(stages), len(stages), task_text)
        )
        _c = LLMClient()
        out = _c.generate(prompt, model=_rt.get("model"), max_tokens=_mt)
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
                        refine["ok"] = True
                    else:
                        refine["error"] = "回形：有空项"
                else:
                    refine["error"] = "回形：⛔ 数组 ∨ 长 ⛔ 合"
            else:
                refine["error"] = "回形：未见 JSON 数组"
        else:
            refine["error"] = "模型回空"
    except Exception as e:
        refine["error"] = "%s: %s" % (type(e).__name__, str(e)[:120])
    finally:
        if _c is not None:
            try:
                route = _c.get_last_route() or {}
            except Exception:
                route = {}
            try:
                refine["attempts"] = _c.get_last_attempts()
            except Exception:
                refine["attempts"] = 0
        if _rt_note:
            route["note"] = _rt_note
    refine["ms"] = int((time.time() - _t0) * 1000)
    steps = [
        {"stage": s, "label": l, "produces": p, "verify": v, "owner": o}
        for s, l, p, v, o in zip(stages, labels, produces, verifies, owners)
    ]
    return {"steps": steps, "source": ("llm" if refine["ok"] else "template"),
            "task_type": tt, "refine": refine, "route": route}
