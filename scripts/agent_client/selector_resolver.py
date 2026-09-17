# -*- coding: utf-8 -*-
"""选择器自愈解析（2026-09-10）

背景（真实事故）：@DS Chat 联调第 1 轮发不出消息。
根因是 actions.click 的写法 —— `target.locator(sel).first.click()` ——
**从不校验唯一性，盲点第一个匹配元素**。而 DS Chat 输入框容器里有两个
34×34、紧挨着、长得几乎一样的按钮（左边胶囊=附件族，右边圆形=发送键），
选择器一含糊就点错，且点了错键**不报错**（clicked:true），故障静默。

本模块把"一次 bug"变成"通用能力"，对所有平台生效：

  1. 唯一性校验: 选择器命中 >1 个元素时不再盲点第一个
  2. 回退链: 主选择器不唯一/不存在时，按配置的 fallbacks 依次尝试
  3. 失败即封闭(fail closed) + 诊断: 全都不可用时**不点**，返回候选元素清单，
     让上层能重新校准，而不是静默点错

安全边界（防回归）：
  只对【平台配置里登记过的选择器】启用严格模式（即 role selector）。
  自由选择器（如小红书的 section.note-item 列表项）保持原行为——列表项本来
  就该点第一个，不能因唯一性校验把既有流程改坏。
"""
import json
import logging

log = logging.getLogger("agent_client.selector_resolver")

# 严格角色：页面上【应当唯一】的元素。命中 >1 即视为选择器已失效，必须分辨/回退/拒绝。
# ⚠️ 关键区分（单测抓出来的设计缺陷）：
#   多实例角色绝不能套唯一性校验 —— 否则会把既有流程改坏。
#   例：card_selector(section.note-item) 命中 20 个是【正常】的，列表本来就该点第一个；
#       reply_selector(.ds-markdown) 多轮对话后有 N 个也【正常】，按 reply_pick=last 取最后一个。
STRICT_ROLE_KEYS = (
    "input_selector",  # 输入框: 有且只有一个, 命中多个多半是选择器退化
    "submit_selector",  # 提交/发送键: 本次事故主角
    "image_input",  # 上传入口: 应当唯一
)

# 多实例角色: 仅用于识别"这是平台登记过的选择器"(诊断/回退链), 【不做】唯一性校验
MULTI_ROLE_KEYS = (
    "reply_selector",
    "card_selector",
    "link_selector",
    "title_selector",
)

ROLE_SELECTOR_KEYS = STRICT_ROLE_KEYS + MULTI_ROLE_KEYS

# 带 fallback 链的键 -> 对应主键
_FALLBACK_OF = {
    "submit_selector_fallbacks": "submit_selector",
    "input_selector_fallbacks": "input_selector",
    "reply_selector_fallbacks": "reply_selector",
}

_DIAG_JS = r"""((sel) => {
  const out = [];
  const push = (el, why) => {
    if (!el || out.length >= 8) return;
    const r = el.getBoundingClientRect();
    out.push({
      tag: el.tagName ? el.tagName.toLowerCase() : '?',
      cls: String(el.className || '').slice(0, 120),
      role: el.getAttribute ? el.getAttribute('role') : null,
      ariaDisabled: el.getAttribute ? el.getAttribute('aria-disabled') : null,
      text: String(el.textContent || '').trim().slice(0, 20),
      hasSvg: !!(el.querySelector && el.querySelector('svg')),
      rect: {x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)},
      why: why
    });
  };
  let nodes = [];
  try { nodes = Array.from(document.querySelectorAll(sel)); } catch (e) { return {error: 'bad selector: ' + e.message}; }
  nodes.slice(0, 8).forEach(el => push(el, 'selector-match'));
  return {count: nodes.length, candidates: out};
})"""


def _as_list(v):
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        return [str(x).strip() for x in v if str(x).strip()]
    return [str(v).strip()] if str(v).strip() else []


def role_of_selector(cfg, sel):
    """如果 sel 与平台配置里某个角色选择器（或其 fallback）完全相同，返回该角色名。

    用途：只对登记过的选择器启用严格模式，避免影响自由选择器。
    """
    sel = (sel or "").strip()
    if not sel or not isinstance(cfg, dict):
        return None
    for key in ROLE_SELECTOR_KEYS:
        for cand in _as_list(cfg.get(key)):
            if cand == sel:
                return key
    for fb_key, main_key in _FALLBACK_OF.items():
        for cand in _as_list(cfg.get(fb_key)):
            if cand == sel:
                return main_key
    # submit_selector 的 fallback 里也可能命中 submit_selector 本身
    for cand in _as_list(cfg.get("submit_selector_fallbacks")):
        if cand == sel:
            return "submit_selector"
    return None


def candidates_for(cfg, role):
    """角色 -> 候选选择器列表（主 + fallbacks，去重保序）。"""
    if not cfg or not role:
        return []
    out = []
    for s in _as_list(cfg.get(role)):
        if s not in out:
            out.append(s)
    for fb_key, main_key in _FALLBACK_OF.items():
        if main_key == role:
            for s in _as_list(cfg.get(fb_key)):
                if s not in out:
                    out.append(s)
    if role == "submit_selector":
        for s in _as_list(cfg.get("submit_selector_fallbacks")):
            if s not in out:
                out.append(s)
    return out


def count_matches(target, sel):
    try:
        return int(target.locator(sel).count())
    except Exception as e:
        return -1 if "bad" in str(e).lower() else 0


def diagnose(target, sel):
    """返回候选元素清单（用于失败时给人/PA 看，便于重新校准）。"""
    try:
        return target.evaluate(_DIAG_JS, sel)
    except Exception:
        # frame_locator 等不支持 evaluate 时降级为 locator 计数
        return {"count": count_matches(target, sel), "candidates": []}


def resolve_unique(target, candidates):
    """按顺序返回第一个"恰好命中 1 个"的选择器。

    返回 (sel, count_map)。全都不唯一时 sel 为 None，count_map 记录每个候选的命中数。
    """
    counts = {}
    for sel in candidates:
        c = count_matches(target, sel)
        counts[sel] = c
        if c == 1:
            return sel, counts
    return None, counts


def resolve_for_action(target, cfg, sel, action="click"):
    """动作入口：返回 (最终选择器 or None, 诊断 dict)。

    - 非角色选择器 → 原样返回（保持既有行为）
    - 角色选择器   → 先试主选择器；不唯一/不存在则走 fallbacks；
                     全失败 → 返回 None + 诊断（**不点**）
    """
    role = role_of_selector(cfg, sel)
    if not role:
        return sel, {"strict": False, "reason": "not-a-role-selector"}
    if role not in STRICT_ROLE_KEYS:
        # 多实例角色(列表卡片/回复容器等): 命中多个是正常语义, 绝不干预
        return sel, {"strict": False, "reason": "multi-instance-role", "role": role}

    cands = candidates_for(cfg, role) or [sel]
    if sel in cands:
        cands = [sel] + [c for c in cands if c != sel]

    chosen, counts = resolve_unique(target, cands)
    if chosen:
        diag = {"strict": True, "role": role, "chosen": chosen, "counts": counts}
        if chosen != sel:
            log.warning("selector 自愈: role=%s 主选择器 %r 不可用, 改用 %r", role, sel, chosen)
            diag["healed"] = True
        return chosen, diag

    diag = {
        "strict": True,
        "role": role,
        "chosen": None,
        "counts": counts,
        "error": "no unique candidate",
        "diagnose": diagnose(target, cands[0] if cands else sel),
    }
    log.error("selector 全候选不唯一, 拒绝执行 %s: role=%s counts=%s", action, role, counts)
    return None, diag


def describe_failure(action, diag):
    """把诊断拼成给上层看的一句话(含候选清单, 便于重新校准)。"""
    role = diag.get("role") or "?"
    counts = diag.get("counts") or {}
    parts = ["选择器不唯一/不可用(role=%s, action=%s)" % (role, action)]
    parts.append("候选命中数: " + json.dumps(counts, ensure_ascii=False))
    dg = diag.get("diagnose") or {}
    cands = dg.get("candidates") or []
    if cands:
        brief = [
            "#%d %s cls=%s rect=%s" % (i, c.get("tag"), (c.get("cls") or "")[:60], c.get("rect"))
            for i, c in enumerate(cands[:5])
        ]
        parts.append("页面候选: " + " | ".join(brief))
    parts.append("已拒绝执行(fail closed, 不盲点第一个)。请重新校准该角色选择器。")
    return "; ".join(parts)
