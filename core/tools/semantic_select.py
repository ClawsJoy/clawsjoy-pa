# -*- coding: utf-8 -*-
"""P3: 语义选择层 — 模板固化 + 模式A内联 + 模式B双检 + vision 回退。

设计: docs/reports/computer_use_agent_design_20260904.md §2
- 模式A(内联): Agent 读 enumerate 清单选 id, 引擎 role/值域校验(见 a11y_dom.validate_selection)
- 模式B(双检): 本地文本模型对打乱顺序清单独立再选, 与 Agent 的 id 一致才执行
- vision 回退: 冲突/无稳定名 → 截图把 id 画到 bbox → qwen2.5vl 看图返回编号
本模块只做 提示词/选号/映射/标注 纯逻辑 + ollama 调用; 不 import playwright。
"""
import base64
import json
import os
import re
import urllib.request

from core.tools.a11y_dom import items_text, parse_index

# 设计 §2.3 固化的 system prompt
# P3 实测补强: 通用描述(文本输入框/多行文本输入框)也是输入控件 — 意图含
# 输入/搜索/填写/关键词 时应优先考虑 input/textarea/textbox 类型元素
SELECT_SYSTEM = (
    "你是网页自动化元素选择器。给定任务意图与网页可交互元素清单（序号|类型|稳定名称），"
    "选出唯一目标元素。规则：只输出 1 个整数序号，不要解释；"
    "依据=类型(role)+稳定名称，占位文本只是示例内容、不作依据；找不到输出 0。"
    "注意：意图含 输入/搜索/填写/关键词/键入 时，优先选择 input/textarea/textbox 类型元素"
    "（即使其名称为通用描述，如 文本输入框/多行文本输入框）。"
)
DEFAULT_MODEL_TEXT = "qwen2.5:7b-instruct-q4_0-gpu"
DEFAULT_MODEL_VISION = "qwen2.5vl:7b"
DEFAULT_PORT = 11435

_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/wqy-zenhei/wqy-zenhei.ttc",
)


def ollama_generate(model, prompt, system=SELECT_SYSTEM, images=None,
                    port=DEFAULT_PORT, timeout=180, temperature=0.0, num_ctx=8192):
    """本地 ollama /api/chat 同步调用(禁轮询; P3 实测: /api/generate 忽略 system,
    导致 7B 无约束多话/拒答 → 改 chat API, system 与 images(挂 user 消息)均可靠)。

    返回 assistant 文本。
    """
    user_msg = {"role": "user", "content": prompt}
    if images:
        user_msg["images"] = images
    body = {
        "model": model,
        "messages": ([{"role": "system", "content": system}] if system else []) + [user_msg],
        "stream": False,
        "options": {"temperature": temperature, "num_ctx": num_ctx},
    }
    req = urllib.request.Request(
        "http://127.0.0.1:%d/api/chat" % port,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read().decode("utf-8"))
    return (d.get("message") or {}).get("content", "").strip()


def build_user_prompt(intent, items_text_body):
    """设计 §2.3 user 模板。"""
    return "意图：%s\n清单：\n%s\n目标元素序号：" % (intent, items_text_body)


def _display_to_id_map(items, seed):
    """打乱清单时建立 显示序号→原始item id 映射; 不打乱则 identity。"""
    if seed is None:
        return {i + 1: items[i].get("id", i + 1) for i in range(len(items))}
    _text, order = items_text(items, seed=seed)
    # order: {orig_index(1-based): display}; invert
    return {disp: items[orig - 1].get("id", orig) for orig, disp in (order or {}).items()}


def select_index(items, intent, model=DEFAULT_MODEL_TEXT, port=DEFAULT_PORT,
                 seed=None, temperature=0.0):
    """模式A/独立选择: 本地模型从清单选序号(显示序号→原始id)。

    返回 {"ok": bool, "id": int|None, "display": int|None, "raw": str, "error": str}
    P3 实测补强: 模型保守返回 0(找不到) 且意图为输入类 → 若清单恰有一个可编辑
    元素则引擎确定性兜底(选它), 防"通用描述标签与搜索词不匹配"误判。
    """
    text, _ = items_text(items, seed=seed)
    prompt = build_user_prompt(intent, text)
    raw = ollama_generate(model, prompt, port=port, temperature=temperature)
    disp = parse_index(raw)
    dmap = _display_to_id_map(items, seed)
    if disp is None or disp == 0:
        # 引擎兜底: 输入类意图 + 唯一可编辑元素
        if re.search(r"输入|搜索|填写|键入|打字|关键词", intent):
            eds = [it for it in items if it.get("role") in ("input", "textarea", "textbox")]
            if len(eds) == 1:
                return {"ok": True, "id": eds[0]["id"], "display": None, "raw": raw,
                        "error": "", "fallback": "single-editable"}
        if disp is None:
            return {"ok": False, "id": None, "display": None, "raw": raw, "error": "响应非整数"}
        return {"ok": False, "id": None, "display": 0, "raw": raw,
                "error": "模型返回0=无匹配; 请换意图表述或 ask"}
    if disp not in dmap:
        return {"ok": False, "id": None, "display": disp, "raw": raw, "error": "序号越界"}
    _chosen_id = dmap[disp]
    # 引擎策略(P3 实测): 输入类意图命中非可编辑元素(模型被内容干扰, 如选热点链接),
    # 且清单恰有一个可编辑元素 → 确定性覆盖为它(role 校验在 act 层仍有兜底)
    if re.search(r"输入|搜索|填写|键入|打字|关键词", intent):
        _eds = [it for it in items if it.get("role") in ("input", "textarea", "textbox")]
        _chosen_role = next((it.get("role") for it in items if it.get("id") == _chosen_id), None)
        if len(_eds) == 1 and _chosen_role not in ("input", "textarea", "textbox"):
            return {"ok": True, "id": _eds[0]["id"], "display": None, "raw": raw,
                    "error": "", "fallback": "input-intent-override"}
    return {"ok": True, "id": _chosen_id, "display": disp, "raw": raw, "error": ""}


def double_check(items, intent, agent_id, model=DEFAULT_MODEL_TEXT, port=DEFAULT_PORT,
                 seed=7, temperature=0.0):
    """模式B: 本地文本模型对打乱清单独立再选, 与 Agent 的 id 是否一致。

    返回 {"agree": bool, "checker_id": int|None, "checker_display": int|None,
          "checker_raw": str, "agent_id": int, "error": str}
    """
    r = select_index(items, intent, model=model, port=port, seed=seed, temperature=temperature)
    if not r["ok"]:
        return {"agree": False, "checker_id": None, "checker_display": None,
                "checker_raw": r["raw"], "agent_id": agent_id, "error": r["error"]}
    return {"agree": bool(r["id"] == agent_id), "checker_id": r["id"],
            "checker_display": r["display"], "checker_raw": r["raw"],
            "agent_id": agent_id, "error": ""}


def _load_font(size=26):
    from PIL import ImageFont
    for p in _FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def draw_numbered_overlay(image_path, out_path, items, legend=True):
    """把 items 的红框+大编号叠加画到截图 → 供 qwen2.5vl 看图选号。

    P3 实测: 无图例时 VL 读错编号(百度一下→14); 加左上角 编号→名称 图例后复测。
    编号画在框上方(字号更大), 图例画在左上角(编号:标签前N字)。
    """
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return False
    try:
        img = Image.open(image_path).convert("RGB")
        dr = ImageDraw.Draw(img)
        font = _load_font(30)
        font_sm = _load_font(16)
        for it in items:
            x, y = it.get("x"), it.get("y")
            w, h = it.get("w"), it.get("h")
            if x is None or y is None or not w or not h:
                continue
            x1, y1 = int(x - w / 2), int(y - h / 2)
            x2, y2 = int(x + w / 2), int(y + h / 2)
            dr.rectangle([x1, y1, x2, y2], outline=(255, 0, 0), width=2)
            tag = str(it.get("id") or "")
            tw = 8 + len(tag) * 18
            ty = max(0, y1 - 34)
            dr.rectangle([x1, ty, x1 + tw, ty + 30], fill=(220, 20, 20))
            dr.text((x1 + 4, ty + 2), tag, fill=(255, 255, 255), font=font)
        if legend:
            ly = 4
            dr.rectangle([2, 0, 400, min(img.height - 2, 4 + 17 * min(len(items), 18))],
                         fill=(255, 255, 255))
            for it in items[:18]:
                line = "%s:%s" % (it.get("id"), str(it.get("label") or "")[:18])
                dr.text((6, ly), line, fill=(20, 20, 220), font=font_sm)
                ly += 17
        img.save(out_path)
        return True
    except Exception:
        return False


def ask_vision_choice(intent, image_path, model=DEFAULT_MODEL_VISION, port=DEFAULT_PORT):
    """vision 回退: qwen2.5vl 看编号截图, 返回元素编号(int|None)。"""
    if not os.path.exists(image_path):
        return None
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    prompt = (
        "这是一张网页截图, 每个可交互元素被红框和编号标注。"
        "请找到「%s」对应的元素, 只输出它的编号(整数), 不要解释。" % intent
    )
    raw = ollama_generate(model, prompt, images=[b64], port=port)
    return parse_index(raw)
