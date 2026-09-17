# -*- coding: utf-8 -*-
"""PPT 图文生产管线方法论 V0.1 的机器执行层（2026-09-10）"""

# ③ 字体规范：字号阶梯
FONT_SCALE = {"H1": 72, "H2": 40, "H3": 24, "STAT": 72, "BODY": 18, "CAPTION": 14}
MIN_LEVEL_RATIO = 1.3
MAX_LEVELS_PER_PAGE = 3
CJK_FONT_NAMES = ("思源黑体", "微软雅黑", "黑体", "宋体", "SimHei", "Microsoft YaHei", "Source Han Sans", "Noto Sans CJK", "思源宋体")

# ② 文字排版规则
LAYOUT_RULES = {"margin_x": 0.08, "margin_y": 0.07, "content_max_h": 0.70, "max_core_items": 5, "card_gap_ratio": 1.5}

# ① AI 生图硬约束（prompt 后缀）
IMAGE_PROMPT_SUFFIX = "写实/半写实风格，低饱和冷灰底+单一强调橙(#E8552D)，构图主体偏左或偏右、另一侧留白≥40%供文字，统一16:9画幅，顶部留15%标题安全区、底部留8%页脚安全区。禁止：neon、gradient、cyberpunk、glowing、holographic、霓虹、渐变、光效。主体不放大。"

# ⑤ slides.json schema
SLIDES_JSON_SCHEMA = {
    "page_type": "str",
    "title": "str",
    "voiceover": "str",
    "image_prompt": "str",
    "image": "str",
    "stat": "str|None",
    "aspect_ratio": "16:9",
    "next_hint": "str",
}


def build_image_prompt(base, suffix=IMAGE_PROMPT_SUFFIX):
    return (base or "").strip() + "。" + suffix


def voiceover_ok(text):
    return bool(text) and len(str(text).strip()) <= 20


def slides_json(pages):
    out = []
    for p in pages:
        data = p.get("data") or {}
        row = {
            "page_type": p.get("layout", "content"),
            "title": str(data.get("title", "") or "").strip(),
            "voiceover": str(p.get("voiceover", "") or "").strip(),
            "image_prompt": build_image_prompt(p.get("image_prompt", "") or ""),
            "stat": str(data.get("number", "") or "").strip() or None,
            "aspect_ratio": "16:9",
            "next_hint": str(p.get("next_hint", "") or "").strip(),
        }
        out.append(row)
    return out


def render_lock(pages):
    return {"render_lock": True, "pages": len(pages) if isinstance(pages, list) else 0}


def font_scale_check(pages):
    """③ 字体规范落地: 每页字号层级 ≤ MAX_LEVELS_PER_PAGE。返回 [(page, level, msg)]。
    层级口径: title=H1, items/rows/headers=H2, body/description/contacts=H3, number=STAT。"""
    issues = []
    for i, p in enumerate(pages, 1):
        data = p.get("data") or {}
        layout = p.get("layout", "")
        levels = 1 if str(data.get("title", "")).strip() else 0
        if layout == "stat" and str(data.get("number", "")).strip():
            levels += 1
        elif layout == "metric-trio" and str(data.get("items", "")).strip():
            levels += 1
        if (
            str(data.get("items", "")).strip()
            or str(data.get("rows", "")).strip()
            or str(data.get("headers", "")).strip()
        ):
            levels += 1
        if (
            str(data.get("body", "")).strip()
            or str(data.get("description", "")).strip()
            or str(data.get("contacts", "")).strip()
        ):
            levels += 1
        if levels > MAX_LEVELS_PER_PAGE:
            issues.append(
                ("P%02d" % i, "warn", "字号层级 %d 级 > %d（FONT_SCALE 上限，应精简为 H1/H2/H3 三级）" % (levels, MAX_LEVELS_PER_PAGE))
            )
    return issues
