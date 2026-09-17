# -*- coding: utf-8 -*-
"""P1: Computer Use 混合方案基础库 — 纯函数, 无浏览器依赖, 可单测。

对应设计: docs/reports/computer_use_agent_design_20260904.md
- §1.1 browser_enumerate: role_of / build_selector / dedupe_key
- §2.1 标签质量: stable_label(优先级 + 占位内容化检测) / is_content_like_placeholder
- §2.3 语义匹配: items_text(清单文本, 可打乱做双检) / parse_index
- §2.4 role 校验: expected_roles_for(action) / validate_selection
POC 依据: 输入框占位文本伪装成内容导致误选(0/3), 稳定描述修复(3/3)。
"""
import hashlib
import re

# ---------------------------------------------------------------- role
_BUTTON_INPUT_TYPES = {"button", "submit", "reset"}
_TEXT_INPUT_TYPES = {"text", "search", "tel", "email", "url", "number"}
_LINK_TAGS = {"A"}
_INTERACTIVE_ROLES = {
    "button", "link", "input", "select", "textarea", "checkbox", "radio",
    "menuitem", "combobox", "textbox", "listbox", "searchbox", "tab", "option",
}


def role_of(el):
    """从 DOM 信息推断可交互角色(设计 §1.1)。

    el: dict {tag, type?, role_attr?}; 返回小写 role 字符串。
    """
    tag = str(el.get("tag") or "").upper()
    role_attr = str(el.get("role_attr") or "").strip().lower()
    if role_attr:
        return role_attr
    # contenteditable 通用编辑区 → textbox(P2 发现: 百度新版搜索输入是 div[contenteditable])
    ce = el.get("contenteditable")
    if ce is not None and str(ce).lower() in ("true", "") and tag in ("DIV", "SPAN", "P", "SECTION", "ARTICLE"):
        return "textbox"
    if tag in ("BUTTON",):
        return "button"
    if tag == "TEXTAREA":
        return "textarea"
    if tag == "INPUT":
        itype = str(el.get("type") or "").lower()
        if itype in ("", "text", "search", "tel", "email", "url", "number"):
            return "input"
        if itype in _BUTTON_INPUT_TYPES:
            return "button"
        if itype in ("checkbox", "radio"):
            return itype
        return "input"
    if tag == "SELECT":
        return "select"
    if tag in ("A",):
        return "link"
    return "other"


# ---------------------------------------------------------------- 占位内容化检测
_ENTITY_PATTERN = re.compile(r"[\u4e00-\u9fff]{2,}(?:称|表示|说|发布|回应|报道|致信|宣布)|[0-9]{1,}岁|[0-9]{2,}[%万亿年月日]|(?:新闻|热搜|热点|今日)")
_NUM_PATTERN = re.compile(r"[0-9]")
# 静态描述性占位开头(像指令/标签, 不像内容)
_STATIC_STARTS = ("请输入", "输入", "搜索", "填写", "写下", "说说", "补充", "关键词", "标题",
                  "正文", "账号", "用户名", "邮箱", "手机", "密码", "昵称", "简介", "内容",
                  "链接", "地址", "名称", "评论", "回复", "发布", "上传", "选择", "验证码",
                  "日期", "价格", "数量", "你的", "您")


def is_content_like_placeholder(text):
    """占位文本内容化检测(设计 §2.1): 占位长得像新闻/内容而不是标签。

    启发式(POC 实证): 实体动作词(称/发布…)、数字、超长(>24)、或以人名/新闻
    口吻开头(如 周健任成都市龙泉驿区委书记 → 非静态指令前缀且非极短)
    → 判定为内容, 不得当元素名; 静态指令前缀(请输入/搜索/…)+短文本 → 标签可用。
    """
    if not text:
        return False
    t = str(text).strip()
    if not t:
        return False
    if len(t) > 24:
        return True
    if any(t.startswith(s) for s in _STATIC_STARTS):
        return False
    if len(t) <= 6:
        return False
    if _ENTITY_PATTERN.search(t):
        return True
    if _NUM_PATTERN.search(t):
        return True
    return True  # 非静态指令前缀的非短文本 → 默认视为内容(宁缺毋滥)


# ---------------------------------------------------------------- 标签策略(§2.1)
def stable_label(el):
    """按优先级产出稳定语义名, 返回 (label, source)。

    优先级: aria-label/aria-labelledby > 关联 label > title/alt > 元素文本
    (button/a) > placeholder(仅静态描述性, 内容化占位跳过) > role 稳定描述。
    """
    def _first(*vals):
        for v in vals:
            s = str(v or "").strip()
            if s:
                return s
        return ""

    aria = _first(el.get("aria_label"), el.get("aria_labelledby_text"))
    if aria:
        return (aria[:40], "aria")
    assoc = _first(el.get("label_for_text"))
    if assoc:
        return (assoc[:40], "label")
    title_alt = _first(el.get("title"), el.get("alt"))
    if title_alt:
        return (title_alt[:40], "title/alt")
    tag = str(el.get("tag") or "").upper()
    if tag in ("BUTTON", "A"):
        txt = _first(el.get("inner_text"), el.get("text_content"))
        if txt:
            return (txt[:40], "text")
    # input/textarea/select: placeholder 仅当静态描述性
    placeholder = str(el.get("placeholder") or "").strip()
    if placeholder and not is_content_like_placeholder(placeholder):
        return (placeholder[:40], "placeholder")
    # 稳定描述兜底
    role = role_of(el)
    if role in ("input", "textbox"):
        itype = str(el.get("type") or "").lower()
        if itype == "search" or "search" in str(el.get("name") or "").lower():
            return ("搜索输入框", "role-desc")
        return ("文本输入框", "role-desc")
    if role == "textarea":
        return ("多行文本输入框", "role-desc")
    if role == "button":
        return ("按钮", "role-desc")
    if role == "link":
        return ("链接", "role-desc")
    if role == "select":
        return ("下拉选择", "role-desc")
    return ("", "none")


# ---------------------------------------------------------------- 选择器生成
def build_selector(path):
    """从祖先链路径生成可执行 CSS 选择器(设计 §1.1)。

    path: list[dict], 每项 {tag, id?, attrs?: {k:v}, idx?: int(同 tag 兄弟序号,
    0-based)}; path[0] 为最深元素(目标)。id/data-* 优先, 否则 tag:nth-of-type 链。
    """
    if not path:
        return ""
    segs = []
    for i, node in enumerate(path):
        tag = str(node.get("tag") or "").lower()
        if not tag:
            continue
        el_id = str(node.get("id") or "").strip()
        if el_id and i == 0:
            return "#" + _css_escape(el_id)
        if i == 0:
            for attr in ("data-testid", "data-cy", "data-test", "name"):
                v = str((node.get("attrs") or {}).get(attr) or "").strip()
                if v:
                    return f"{tag}[{attr}=\"{_css_escape(v)}\"]"
        seg = tag
        idx = node.get("idx")
        if idx is not None and isinstance(idx, int):
            seg += f":nth-of-type({idx + 1})"
        segs.append(seg)
    return " > ".join(segs)


def _css_escape(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


# ---------------------------------------------------------------- 去重
def dedupe_key(el):
    """元素去重键: 目标自身 + 最近定位祖先, 避免父子重复计数。"""
    tag = str(el.get("tag") or "").upper()
    label, _src = stable_label(el)
    sel = str(el.get("sel") or "")
    return hashlib.md5(f"{tag}|{label}|{sel}".encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------- 语义选择工具(§2.3/2.4)
def items_text(items, fields=("role", "label"), seed=None):
    """把元素清单转成提示词文本 每行 N|role|label; seed 打乱(双检用)。

    返回 (text, order): order = {原始序号(1-based): 打乱后显示序号} 或 None。
    """
    seq = list(range(1, len(items) + 1))
    order = None
    if seed is not None:
        import random
        rng = random.Random(seed)
        rng.shuffle(seq)  # seq 现在是 1..n 的乱序; orig序号→显示序号映射
        order = {orig: disp for disp, orig in enumerate(seq, start=1)}
    lines = []
    for orig in range(1, len(items) + 1):
        disp = order[orig] if order else orig
        it = items[orig - 1]
        parts = [str(disp), str(it.get(fields[0]) or ""), str(it.get(fields[1]) or "")]
        lines.append("|".join(parts))
    return ("\n".join(lines), order)


def parse_index(text):
    """从模型响应解析严格整数(1..n; 0=找不到)。非整数返回 None。"""
    if text is None:
        return None
    m = re.search(r"(?<!\d)(\d{1,4})(?!\d)", str(text).strip())
    return int(m.group(1)) if m else None


def expected_roles_for(action):
    """动作→期望元素角色集合(设计 §2.4 校验表)。"""
    a = (action or "").lower()
    if a in ("click",):
        return {"button", "link", "checkbox", "radio", "menuitem", "tab", "option"}
    if a in ("fill", "type"):
        return {"input", "textarea", "textbox", "combobox", "searchbox"}
    if a in ("select_option",):
        return {"select", "listbox"}
    if a in ("press",):
        return {"button", "link", "form", "input", "textarea"}
    if a in ("hover", "screenshot"):
        return _INTERACTIVE_ROLES
    return _INTERACTIVE_ROLES


def validate_selection(index, total, action=None, items_roles=None):
    """引擎侧校验: 值域 + 动作 role 期望(设计 §2.4)。

    返回 {"ok": bool, "reason": str}; ok=False 时 reason 给 Agent 可操作信息。
    """
    if index is None:
        return {"ok": False, "reason": "响应非整数, 请重试(只输出序号)"}
    if index == 0:
        return {"ok": False, "reason": "模型返回 0=清单中无匹配元素; 请换意图或加相近候选"}
    if index < 0 or index > total:
        return {"ok": False, "reason": f"序号 {index} 越界(1..{total}), 请重选"}
    if action and items_roles is not None:
        expected = expected_roles_for(action)
        role = str(items_roles[index - 1] or "")
        if role not in expected:
            return {"ok": False,
                    "reason": f"序号 {index} 角色={role} 不匹配动作 {action}(期望 {sorted(expected)}), 请重选"}
    return {"ok": True, "reason": ""}


def pick_stable_anchor_for(items, role, label_keywords):
    """引擎侧文本锚点(备用): 在清单中找 role+label 含关键词的元素序号列表(0=无)。"""
    hits = []
    for i, it in enumerate(items, start=1):
        r = str(it.get("role") or "")
        lb = str(it.get("label") or "")
        if r == role and any(k in lb for k in label_keywords):
            hits.append(i)
    return hits
