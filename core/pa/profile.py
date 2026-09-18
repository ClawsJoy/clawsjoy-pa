# -*- coding: utf-8 -*-
"""PA 画像档案内核(2026-09-10 v0): 老板画像 = 动态迭代沉淀, 非一次建档。

域含 emotion(情感/在意点/偏好强度): 老板对产出的情绪反应与在意点, 与 aesthetic 并列用于审核权重。

每条条目 schema(与 PA方向文档 §5 一致):
  {id, domain, value, source, date, confidence(high|medium|low|pending),
   status(proposed|confirmed|revised|deprecated), supersedes}

规则:
  - 老板修正 -> 旧条目标 revised, 新条目 supersedes 指向旧 id(不覆盖历史)
  - 试错 = 数据: 被否方案/被纠正说法同样入库
  - 持久化 data/v9/pa/profile.json(可被 env PA_PROFILE_PATH 覆盖)

2026-09-18（X-17② 批 2 · DS 拍 A）：**读写都走统一出口**（`core/pa/state_out`）——
坏状态 fail-loud，不再静默回落空档案；业务结构判据（`entries` 需为 list）**留 PA 侧**。
"""
import os
import time
from pathlib import Path

from core.pa.state_out import read_state, write_state

DOMAINS = {"fact", "decision", "aesthetic", "emotion", "style", "product", "channel", "lesson"}
STATUSES = {"proposed", "confirmed", "revised", "deprecated"}
CONFIDENCES = {"high", "medium", "low", "pending"}


def _now():
    return time.strftime("%Y-%m-%d")


#: 写者标识（进出口的写者归属台账；供 detect_uninstrumented 识别绕过出口的写者）
_WRITER = "pa.profile"


def _shape(doc):
    """**PA 侧业务结构判据**（X-17② 批 2 · DS 拍①：判据留 PA 侧，不给出口加回调）。"""
    if not isinstance(doc.get("entries"), list):
        return False, "entries 需为 list"
    return True, ""


class ProfileStore:
    def __init__(self, path=None):
        self.path = Path(path or os.getenv("PA_PROFILE_PATH", "data/v9/pa/profile.json"))
        self.entries = []
        self.load()

    def load(self):
        """**不存在 ⇒ 空档案；存在但不可用 ⇒ 抛 PAStateCorrupt**（不再静默回落空档案）。"""
        self.entries = []
        if self.path.exists():
            self.entries = read_state(self.path, _WRITER, _shape).get("entries") or []
        return self

    def save(self):
        """**走统一出口**（X-17② 批 2）：跨进程锁 + 原子替换 + 坏状态拒绝写入。"""
        write_state(
            self.path,
            _WRITER,
            _shape,
            {"version": 1, "updated": _now(), "entries": self.entries},
            reason="pa.profile.save",
        )
        return self

    def entries_by_domain(self, domain=None, status=None):
        out = self.entries
        if domain:
            out = [e for e in out if e.get("domain") == domain]
        if status:
            out = [e for e in out if e.get("status") == status]
        return out

    def active(self, domain=None):
        out = []
        for e in self.entries:
            if e.get("status") in ("revised", "deprecated"):
                continue
            if domain and e.get("domain") != domain:
                continue
            out.append(e)
        return out

    def top_conf(self, domain, n=5):
        order = {"high": 0, "medium": 1, "low": 2, "pending": 3}
        act = sorted(self.active(domain), key=lambda e: order.get(e.get("confidence", "low"), 2))
        return act[:n]

    def _next_id(self):
        used = {e.get("id") for e in self.entries}
        i = 1
        while ("e%d" % i) in used:
            i += 1
        return "e%d" % i

    def add(self, domain, value, source="", confidence="medium", status="proposed", supersedes=None, key=None):
        """新增条目。key: 参数化字段表的字段名(可选) —— 老条目无 key, 完全向后兼容。"""
        if domain not in DOMAINS:
            raise ValueError("unknown domain: %s" % domain)
        if confidence not in CONFIDENCES:
            raise ValueError("unknown confidence: %s" % confidence)
        if status not in STATUSES:
            raise ValueError("unknown status: %s" % status)
        e = {
            "id": self._next_id(),
            "domain": domain,
            "value": value,
            "source": source,
            "date": _now(),
            "confidence": confidence,
            "status": status,
            "supersedes": supersedes,
        }
        if key:
            e["key"] = key
        self.entries.append(e)
        self.save()
        return e

    def revise(self, old_id, new_value, source="", confidence=None, domain=None, key=None):
        old = None
        for e in self.entries:
            if e.get("id") == old_id:
                old = e
                break
        if old is None:
            return None
        old["status"] = "revised"
        e = self.add(
            domain or old.get("domain"),
            new_value,
            source=source,
            confidence=confidence or old.get("confidence", "medium"),
            status="confirmed",
            supersedes=old_id,
            key=key or old.get("key"),
        )
        self.save()
        return e

    def confirm(self, entry_id, source=""):
        for e in self.entries:
            if e.get("id") == entry_id:
                e["status"] = "confirmed"
                if source:
                    e["source"] = source
                self.save()
                return e
        return None

    def brief(self, domains=None, max_per=6):
        ds = domains or list(DOMAINS)
        lines = []
        for d in ds:
            top = self.top_conf(d, max_per)
            if not top:
                continue
            lines.append("【%s】" % d)
            for e in top:
                mark = "" if e.get("status") == "confirmed" else "(提案)"
                lines.append("  - %s %s[%s] (%s)" % (e["value"], mark, e.get("confidence"), e.get("date")))
        return "\n".join(lines)

    def chat_brief(self, text, n=6):
        # 按需检索画像(聊天): confirmed 里挑与 text 相关的, 最多 n 条; 无命中返回空(不全量注入)
        confirmed = [e for e in self.entries if e.get("status") == "confirmed"]
        if not confirmed or not text or not str(text).strip():
            return ""
        t = str(text).strip()
        grams = {t[i : i + 2] for i in range(len(t) - 1)} if len(t) >= 2 else {t}

        def _hit(e):
            v = str(e.get("value", ""))
            if len(v) < 2:
                return 0
            vg = {v[i : i + 2] for i in range(len(v) - 1)}
            return len(grams & vg)

        scored = [(_hit(e), e) for e in confirmed]
        if all(sc == 0 for sc, _ in scored):
            return ""
        order = {"high": 0, "medium": 1, "low": 2, "pending": 3}
        scored.sort(key=lambda x: (-x[0], order.get(x[1].get("confidence", "low"), 2), x[1].get("date", "")))
        top = [e for sc, e in scored if sc > 0][:n]
        lines = ["【老板画像·与当前话题相关】"]
        for e in top:
            lines.append("  - %s [%s]" % (e["value"], e.get("confidence")))
        return chr(10).join(lines)

    def render_markdown(self):
        lines = ["# PA 画像档案(自动维护 v1)", "", "> 由 core/pa 内核维护; 老板一句纠正 = 旧条目标 revised + 新条目。", ""]
        for d in DOMAINS:
            act = self.active(d)
            if not act:
                continue
            lines.append("## %s" % d)
            for e in act:
                lines.append(
                    "- [%s] %s | conf=%s | %s | src: %s"
                    % (e["id"], e["value"], e.get("confidence"), e.get("date"), e.get("source", ""))
                )
            lines.append("")
        return "\n".join(lines)


# ===== 参数化字段表（2026-09-13 聊天层落地第 1 步）=====
# 设计要点：
# 1. 不新建存储 —— 字段取值仍以 ProfileStore 条目落在 data/v9/pa/profile.json，只是多带 key 标识；
#    旧条目无 key 不受影响（完全向后兼容）。
# 2. 选项来自枚举（封闭）而非自由填写 —— 这是「参数化」核心，也是未来本地小模型训练的前提：
#    枚举值可直接 one-hot / 分桶，自由文本不能。
# 3. domain 复用现有 8 域，不新增域。
FIELD_SCHEMA = {
    "industry": {"label": "行业", "type": "single", "domain": "fact", "options": ["光电", "制造", "贸易", "服务", "其他"]},
    "interests": {
        "label": "兴趣点",
        "type": "multi",
        "domain": "fact",
        "options": ["技术", "市场", "管理", "金融", "法务", "财税", "战略", "日常事务"],
    },
    "report_detail": {"label": "汇报详细度", "type": "single", "domain": "style", "options": ["简", "中", "详"]},
    "tone": {"label": "语气", "type": "single", "domain": "style", "options": ["直接", "委婉"]},
    "iteration": {"label": "迭代偏好", "type": "single", "domain": "style", "options": ["先给草稿再改", "想清楚再动手"]},
    "risk_auto_write": {"label": "允许自动写文件", "type": "bool", "domain": "decision", "options": ["是", "否"]},
    "risk_auto_exec": {"label": "允许自动执行命令", "type": "bool", "domain": "decision", "options": ["是", "否"]},
    "risk_auto_send": {"label": "允许外发", "type": "bool", "domain": "decision", "options": ["是", "否"]},
}


def field_schema():
    """返回字段表（字段 -> {label,type,domain,options}）—— 前后端共用。"""
    return {k: dict(v) for k, v in FIELD_SCHEMA.items()}


def validate_field(key, value):
    """校验单字段取值。契约：返回 (ok, normalized_or_reason)；multi 返回 list，其余返回 str。"""
    spec = FIELD_SCHEMA.get(key)
    if spec is None:
        return False, "未知字段 %s" % key
    opts = set(spec["options"])
    if spec["type"] == "multi":
        vals = value if isinstance(value, list) else [value]
        vals = [str(v).strip() for v in vals if str(v).strip()]
        bad = [v for v in vals if v not in opts]
        if bad:
            return False, "%s 取值不在选项内: %s" % (key, bad)
        return True, vals
    v = str(value).strip()
    if v not in opts:
        return False, "%s 取值不在选项内: %s" % (key, v)
    return True, v


def _same(a, b):
    """取值等价判断（multi 字段是 list，顺序无关）。"""
    if isinstance(a, list) or isinstance(b, list):
        na = a if isinstance(a, list) else [a]
        nb = b if isinstance(b, list) else [b]
        return sorted(str(x) for x in na) == sorted(str(x) for x in nb)
    return str(a) == str(b)


def _active_entry_id(store, key):
    """当前生效的该字段条目 id（同 key 多条时取最后一条）。"""
    hit = None
    for e in store.active():
        if e.get("key") == key:
            hit = e.get("id")
    return hit


def collect_fields(store, values, source="chat", confidence=None, status="confirmed"):
    """结构化收集：按字段表写入画像（复用 ProfileStore 持久化，不新建存储）。

    契约：返回 {written, unchanged, rejected}
      written   本次真正写入的字段 [{key, value, entry_id, superseded}]
      unchanged 取值与当前一致，不重复写（幂等，避免刷库）
      rejected  取值不合法 [{key, reason}]

    写入条目 domain 取自字段表；**修正走 supersedes 链**（旧条目标 revised）。
    这条链就是训练标注：老板把 A 改成 B = 一条 (上下文, 错答 A, 正答 B)。
    来源可信度：表单(source=form) 高；聊天推断(source=chat) 中 —— 训练时可按可信度加权。
    """
    written, unchanged, rejected = [], [], []
    conf = confidence or ("high" if source == "form" else "medium")
    current = get_fields(store)
    for k, v in (values or {}).items():
        ok, norm = validate_field(k, v)
        if not ok:
            rejected.append({"key": k, "reason": norm})
            continue
        if k in current and _same(current[k], norm):
            unchanged.append({"key": k, "value": norm})
            continue
        spec = FIELD_SCHEMA[k]
        old_id = _active_entry_id(store, k)
        if old_id:
            e = store.revise(old_id, norm, source=source, confidence=conf, key=k)
        else:
            e = store.add(spec["domain"], norm, source=source, confidence=conf, status=status, key=k)
        written.append({"key": k, "value": norm, "entry_id": (e or {}).get("id"), "superseded": old_id})
    return {"written": written, "unchanged": unchanged, "rejected": rejected}


def get_fields(store):
    """读取已确认字段取值 -> 供「因人而异」驱动能力选择。返回 {key: value}。

    契约：按写入顺序取最后一条生效条目（supersedes 链的末端）；无 key 的老条目忽略。
    """
    out = {}
    try:
        entries = store.active()
    except Exception:
        return out
    for e in entries or []:
        k = e.get("key")
        if k in FIELD_SCHEMA:
            out[k] = e.get("value")
    return out


def capability_switches(fields):
    """由字段表取值推导能力开关（「因人而异」落点）。

    契约：返回 {auto_write, auto_exec, auto_send, detail}；缺省保守（未声明 -> 不允许自动）。
    """
    f = fields or {}
    return {
        "auto_write": f.get("risk_auto_write") == "是",
        "auto_exec": f.get("risk_auto_exec") == "是",
        "auto_send": f.get("risk_auto_send") == "是",
        "detail": f.get("report_detail") or "中",
    }
