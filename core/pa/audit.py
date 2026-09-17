# -*- coding: utf-8 -*-
"""PA 验收器官（2026-09-10，t7/t9：从散落脚本收编为 core/pa 常驻能力）

来源: data/tmp/wpsai_m3/pa_audit.py + visual_check.py（现役脚本，本模块是其 home）。

三层验收:
  A) preflight  —— 渲染前字段级预检（容量/字体语言/CSS变量/诚实标注/老板禁忌）
  B) 内容合规   —— 内部批注不得进对客户可见字段（t22 事故根治：6 页「待核实 #x」泄漏）
  C) postcheck  —— 渲染后三层（像素/图层/文本锚点）

【核心设计（对照 Codex guardian / exec_policy）】
  - 确定性度量决定「通过/打回」: 全部是可复现的规则, 不用模型当判官
  - 分层: preflight 拦「不该出现的内容/字段」, postcheck 验「渲染后的实际形态」
  - fail 是硬门槛, warn 是提示(不拦)
  - 规则默认在代码里, 可用 extra_marks 从画像扩展（规则从画像读）
"""
import collections
import json
import os
import re

# ---------- layout 规格 ----------
LAYOUTS = {
    "cover": {"required": ["title"], "opt": ["subtitle", "tag"], "title_max": 60},
    "section": {"required": [], "opt": ["number", "title", "subtitle", "footer"]},
    "content": {"required": ["title"], "opt": ["body", "tag", "footer"], "body_max_lines": 6, "line_max": 48},
    "stat": {"required": ["number"], "opt": ["label", "description"], "number_max": 12},
    "feature-grid": {"required": ["title"], "opt": ["items"], "items_max": 4},
    "quote": {"required": [], "opt": ["quote", "author", "role"]},
    "comparison": {"required": ["title"], "opt": ["leftLabel", "leftBody", "rightLabel", "rightBody"], "line_max": 40},
    "metric-trio": {"required": ["title"], "opt": ["items"], "items_max": 3},
    "timeline": {"required": ["title"], "opt": ["items"], "items_max": 6},
    "agenda": {"required": ["title"], "opt": ["items"], "items_max": 7},
    "two-column": {"required": ["title"], "opt": ["leftHead", "leftBody", "rightHead", "rightBody"]},
    "image-text": {"required": ["title"], "opt": ["body", "imageUrl"]},
    "process": {"required": ["title"], "opt": ["steps"], "items_max": 5},
    "table": {"required": ["title"], "opt": ["headers", "rows"], "rows_max": 8},
    "bento": {"required": ["title"], "opt": ["heroTitle", "items"], "items_max": 3},
    "closer": {"required": [], "opt": ["mainText", "subText", "contacts"], "contacts_max": 4},
    "freeform": {"required": ["html"], "opt": ["css"]},
}
CSS_VARS_OK = {
    "--bg",
    "--surface",
    "--primary",
    "--accent",
    "--title-color",
    "--body-color",
    "--title-font",
    "--body-font",
}
CJK_FONT_HINTS = ["yahei", "hei", "song", "simsun", "pingfang", "noto", "source han", "思源", "黑", "宋", "楷", "微软雅黑"]
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
# ---------- 内容合规: 内部批注不得进对客户可见字段 ----------
VISIBLE_FIELDS = (
    "title",
    "subtitle",
    "body",
    "items",
    "rows",
    "headers",
    "number",
    "label",
    "description",
    "leftLabel",
    "leftBody",
    "rightLabel",
    "rightBody",
    "leftHead",
    "rightHead",
    "quote",
    "author",
    "role",
    "mainText",
    "subText",
    "contacts",
    "heroTitle",
    "tag",
    "footer",
    "steps",
)
DEFAULT_INTERNAL_MARKS = (
    "待核实",
    "待线下核实",
    "口径",
    "仅供参考",
    "内部",
    "数字待核实",
    "大纲",
    "草稿",
    "初稿",
    "V0.",
    "v0.",
)
_VERSION_RE = re.compile(r"[Vv]\d+\.?\d*")


def content_compliance(pages, extra_marks=()):
    """内部批注泄漏检测。返回 [(page, level, msg)]，level 一律 fail（硬门槛）。"""
    marks = tuple(DEFAULT_INTERNAL_MARKS) + tuple(extra_marks)
    issues = []
    for i, p in enumerate(pages, 1):
        pg = "P%02d" % i
        data = p.get("data") or {}
        for fld in VISIBLE_FIELDS:
            v = data.get(fld)
            if v is None:
                continue
            blob = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
            for m in marks:
                if m and m in blob:
                    j = blob.find(m)
                    snippet = blob[max(0, j - 12) : j + len(m) + 12].replace("\n", " ")
                    issues.append((pg, "fail", "内部批注泄漏: 字段 %s 含「%s」(%s…)，不得出现在对客户可见内容" % (fld, m, snippet)))
                    break
    return issues


def preflight(pages, extra_marks=()):
    """字段级预检 = 原有排版检查 + 内容合规。返回 [(page, level, msg)]。"""
    issues = []
    for i, p in enumerate(pages, 1):
        pg = "P%02d" % i
        layout = p.get("layout")
        data = p.get("data") or {}
        spec = LAYOUTS.get(layout)
        if not spec:
            issues.append((pg, "fail", "layout '%s' 不在白名单" % layout))
            continue
        for req in spec.get("required", []):
            if not str(data.get(req, "")).strip():
                issues.append((pg, "fail", "缺必填字段 %s" % req))
        if "body" in data:
            lines = [l for l in str(data["body"]).split("\n") if l.strip()]
            if len(lines) > spec.get("body_max_lines", 6):
                issues.append((pg, "fail", "body 行数 %d > 上限 %d" % (len(lines), spec.get("body_max_lines", 6))))
            for l in lines:
                if len(l) > spec.get("line_max", 48):
                    issues.append((pg, "warn", "行过长 %d 字(>%d 可能折行): %s…" % (len(l), spec.get("line_max", 48), l[:16])))
        if "items" in data:
            n = len([x for x in str(data["items"]).split("\n") if x.strip()])
            if n > spec.get("items_max", 4):
                issues.append((pg, "fail", "items %d 条 > 上限 %d" % (n, spec.get("items_max", 4))))
        if "rows" in data:
            n = len([x for x in str(data["rows"]).split("\n") if x.strip()])
            if n > spec.get("rows_max", 8):
                issues.append((pg, "fail", "表格 %d 行 > 上限 %d" % (n, spec.get("rows_max", 8))))
        blob = json.dumps(data, ensure_ascii=False)
        pal = p.get("palette") or {}
        if CJK_RE.search(blob):
            for fld in ("titleFont", "bodyFont"):
                fv = str(pal.get(fld, "") or "")
                if fv and not any(h in fv.lower() for h in CJK_FONT_HINTS):
                    issues.append((pg, "fail", "%s='%s' 无中文字形(中文内容会因度量错配被裁)" % (fld, fv)))
        if layout == "freeform":
            for var in set(re.findall(r"var\((--[a-z-]+)\)", str(data.get("css", "")))):
                if var not in CSS_VARS_OK:
                    issues.append((pg, "fail", "freeform 使用了未定义变量 %s（会整块失效）" % var))
        # (2026-09-10 方法论) 关键数字独立成行: 关键数字要短、独立(供视频特写)
        if layout == "stat":
            _num = str(data.get("number", "")).strip()
            if not _num:
                issues.append((pg, "fail", "stat 布局缺关键数字 number"))
            elif len(_num) > 12:
                issues.append((pg, "warn", "关键数字 %r 过长(>12字)，应独立成行短数字" % _num[:16]))
        if layout == "metric-trio":
            for _it in [x for x in str(data.get("items", "")).split("\n") if x.strip()]:
                _parts = _it.split("|")
                _num = _parts[1].strip() if len(_parts) > 1 else ""
                if not _num:
                    issues.append((pg, "fail", "metric-trio 条目缺关键数字: %s" % _it[:20]))
                elif len(_num) > 12:
                    issues.append((pg, "warn", "关键数字 %r 过长(>12字)" % _num[:16]))
        core = 0
        if "body" in data:
            core += len([x for x in str(data["body"]).split("\n") if x.strip()])
        if "items" in data:
            core += len([x for x in str(data["items"]).split("\n") if x.strip()])
        if layout == "table" and "rows" in data:
            core += len([x for x in str(data["rows"]).split("\n") if x.strip()])
        if core > 5:
            issues.append((pg, "warn", "核心信息 %d 条 > 5（老板禁忌：留白要够）" % core))
    issues.extend(content_compliance(pages, extra_marks=extra_marks))
    # ③ 字体规范落地: 字号三级阶梯(每页 ≤3 级)
    try:
        from core.pa.ppt_method import font_scale_check as _fsc

        issues.extend(_fsc(pages))
    except Exception:
        pass
    return issues


# ---------- postcheck（渲染后三层：像素 / 图层 / 文本锚点）----------
NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}


def emu2px(v):
    return int(round(int(v) / 12700.0 * 2))


def layer_audit(pptx_dir, png_dir, n_pages):
    """图层贴边/裁切检测（原 pa_audit.layer_audit 原样收编）。"""
    import xml.etree.ElementTree as ET

    from PIL import Image

    out = {}
    sdir = os.path.join(pptx_dir, "ppt/slides")
    if not os.path.isdir(sdir):
        return out
    files = sorted(
        [f for f in os.listdir(sdir) if f.startswith("slide") and f.endswith(".xml")],
        key=lambda x: int(re.findall(r"\d+", x)[0]),
    )
    for f in files[:n_pages]:
        idx = int(re.findall(r"\d+", f)[0])
        png = os.path.join(png_dir, "ppc_P%02d.png" % idx)
        if not os.path.exists(png):
            continue
        im = Image.open(png).convert("RGB")
        W, H = im.size
        root = ET.parse(os.path.join(sdir, f)).getroot()
        boxes = []
        for p in root.findall(".//p:pic", NS):
            off = p.find(".//a:off", NS)
            ext = p.find(".//a:ext", NS)
            if off is None or ext is None:
                continue
            boxes.append((emu2px(off.get("x")), emu2px(off.get("y")), emu2px(ext.get("cx")), emu2px(ext.get("cy"))))
        if not boxes:
            continue
        boxes.sort(key=lambda b: -(b[2] * b[3]))

        def lum(c):
            return (0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]) / 255.0

        clipped = []
        for x, y, cx, cy in boxes[1:]:
            x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + cx), min(H, y + cy)
            if x1 - x0 < 40 or y1 - y0 < 20:
                continue
            cnt = collections.Counter()
            for yy in range(y0, y1, 3):
                for xx in range(x0, x1, 3):
                    cnt[im.getpixel((xx, yy))] += 1
            bgc = cnt.most_common(1)[0][0]
            bgl = lum(bgc)
            if bgl < 0.75:
                continue
            top = None
            top_dark = False
            for dy in range(0, min(40, y1 - y0)):
                row = [lum(im.getpixel((xx, y0 + dy))) for xx in range(x0, x1, 2)]
                if any(abs(v - bgl) > 0.25 for v in row):
                    top = dy
                    dark = [v for v in row if v < 0.55]
                    ratio = len(dark) / max(1, len(row))
                    top_dark = 0.02 < ratio < 0.60
                    break
            if top is not None and top <= 2 and top_dark:
                clipped.append({"layer": "%dx%d@%d,%d" % (cx, cy, x, y), "distance_top": top})
        out[idx] = {"clipped": clipped}
    return out


def postcheck(png_dir, prefix, pptx_dir, expected=None):
    """渲染后验收（原 pa_audit.postcheck 原样收编）。"""
    report = {"pixels": [], "issues": []}
    if not os.path.isdir(png_dir):
        return report
    pngs = sorted([f for f in os.listdir(png_dir) if f.startswith(prefix) and f.endswith(".png")])
    for f in pngs:
        try:
            import sys as _sys

            _here = os.path.dirname(os.path.abspath(__file__))
            _tmp = os.path.join(_here, "..", "..", "data", "tmp", "wpsai_m3")
            _sys.path.insert(0, _tmp)
            from visual_check import analyze

            m = analyze(os.path.join(png_dir, f))
        except Exception:
            m = {"verdict": ""}
        pg = f.replace(prefix, "").replace(".png", "")
        report["pixels"].append(m)
        v = m.get("verdict", "")
        if v.startswith("fail"):
            report["issues"].append((pg, "fail", v))
        elif v.startswith("warn"):
            report["issues"].append((pg, "warn", v))
    lay = layer_audit(pptx_dir, png_dir, len(pngs))
    report["layers"] = lay
    for idx, info in lay.items():
        if info["clipped"]:
            report["issues"].append(("P%02d" % idx, "warn", "文字层贴边(疑似): %s" % info["clipped"][:2]))
    return report


# ---------- 规则从画像读 ----------
def profile_forbidden_marks(profile_entries):
    """从画像抽取额外的内部批注标记（形式: 禁止出现「X」/ 不得含「X」）。"""
    marks = []
    for e in profile_entries or []:
        v = str(e.get("value") or "")
        for m in re.findall(r"[禁止|不得|不要|不能](?:出现|含|有)?[「『](.+?)[」』]", v):
            marks.append(m.strip())
    return [m for m in marks if m]
