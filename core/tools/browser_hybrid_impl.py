# -*- coding: utf-8 -*-
"""browser_hybrid 实现 — Computer Use 混合方案(POC 已验证)。

设计: docs/reports/computer_use_agent_design_20260904.md §1
- enumerate: 枚举可交互元素(role/label/sel/bbox; 坐标仅供展示, 绝不作为点击依据)
- act: 按序号用 DOM 选择器 click/fill/type/press/select_option/hover; 引擎验证
- observe: url_contains/text_visible/field_value 断言(循环验证/完成判定)
- close: 释放页面
页面状态按 page_id 保留(TTL 10min, 会话上限 4); playwright 长驻进程内不关闭。
"""
import os
import re
import time

from core.tools import browser_runtime as _br  # 批197: 浏览器唯一出口（launch/CDP/会话都在那里）

_SESSIONS = _br.SESSIONS  # 批197: 会话表在唯一出口（同一 dict 对象）
_PLAYWRIGHT = None  # 长驻 sync playwright(start 后不 stop)
_MAX_SESSIONS = _br.MAX_SESSIONS
_TTL = _br.SESSION_TTL_S


def _is_private_host(host):
    """与 playwright_browser 同语义的内网/回环判定(避免反向 import 循环)。"""
    h = (host or "").strip().lower()
    if h in ("localhost", "localhost.localdomain") or h.endswith(".localhost"):
        return True
    if h in ("::1", "0.0.0.0", "::") or h.startswith("127."):
        return True
    if h.startswith("10.") or h.startswith("192.168.") or h.startswith("169.254."):
        return True
    if h.startswith("172."):
        try:
            second = int(h.split(".")[1])
            if 16 <= second <= 31:
                return True
        except Exception:
            pass
    if h.startswith("fe80:") or h.startswith("fc") or h.startswith("fd"):
        return True
    return False


def _close_session(page_id):
    """批197：委托**唯一出口**（browser_runtime）—— 本文件不再自己 launch。"""
    _br.close_session(page_id)


def _pw():
    """批197：惰性长驻 driver —— 收敛到 browser_runtime.get_driver()（全仓唯一实例）。"""
    return _br.get_driver()


def _get_session(page_id, viewport_w=None, viewport_h=None):
    """批197：取/建会话 —— 收敛到 browser_runtime.get_session()（唯一 launch 点）。"""
    return _br.get_session(page_id, viewport_w=viewport_w, viewport_h=viewport_h)
    return page, s


_JS_ENUM = r"""
() => {
    const out = [];
    const seen = new Set();
    function box(el) {
        const r = el.getBoundingClientRect();
        if (!r.width || !r.height || r.width < 6 || r.height < 6) return null;
        if (r.bottom < 0 || r.right < 0 || r.top > window.innerHeight || r.left > window.innerWidth) return null;
        const cs = getComputedStyle(el);
        if (cs.visibility === 'hidden' || cs.display === 'none' || Number(cs.opacity || 1) === 0) return null;
        return {x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2),
                w: Math.round(r.width), h: Math.round(r.height)};
    }
    function chain(el) {
        const arr = [];
        let cur = el;
        for (let i = 0; i < 5 && cur && cur !== document.body; i++) {
            const pa = cur.parentElement;
            if (!pa) break;
            const kids = Array.from(pa.children).filter(c => c.tagName === cur.tagName);
            arr.unshift({tag: cur.tagName, id: cur.id || '', idx: kids.length > 1 ? kids.indexOf(cur) : null});
            cur = pa;
        }
        return arr;
    }
    function labels_of(el) {
        // 关联 label: 属性 for + 包裹
        let txt = '';
        try {
            if (el.labels) txt = Array.from(el.labels).map(l => (l.innerText || '').trim()).join(' ');
        } catch (e) {}
        if (!txt && el.id) {
            const lf = document.querySelector('label[for="' + CSS.escape(el.id) + '"]');
            if (lf) txt = (lf.innerText || '').trim();
        }
        return txt.replace(/\s+/g, ' ');
    }
    function labelledby_of(el) {
        const lb = el.getAttribute('aria-labelledby');
        if (!lb) return '';
        const ids = lb.split(/\\s+/);
        let txt = '';
        for (const id of ids) {
            const n = document.getElementById(id);
            if (n) txt += ' ' + (n.innerText || n.textContent || '');
        }
        return txt.trim().replace(/\s+/g, ' ');
    }
    const q = s => Array.from(document.querySelectorAll(s));
    const cands = [
        ...q('button'),
        ...q('input[type=button]'), ...q('input[type=submit]'),
        ...q('input[type=text]'), ...q('input[type=search]'), ...q('input:not([type])'),
        ...q('input[type=tel]'), ...q('input[type=email]'), ...q('input[type=url]'), ...q('input[type=number]'),
        ...q('textarea'),
        ...q('a[href]'),
        ...q('[role=button]'), ...q('[role=link]'), ...q('[role=searchbox]'), ...q('[role=textbox]'),
        ...q('[role=combobox]'), ...q('select'),
        ...q('[contenteditable="true"]'), ...q('[contenteditable=""]'),
    ];
    for (const el of cands) {
        if (seen.has(el)) continue;
        seen.add(el);
        const b = box(el);
        if (!b) continue;
        const attrs = {};
        for (const a of ['data-testid', 'data-cy', 'data-test', 'name']) {
            const v = el.getAttribute(a);
            if (v) attrs[a] = v;
        }
        out.push({
            tag: el.tagName,
            type: (el.getAttribute('type') || '').toLowerCase(),
            role_attr: el.getAttribute('role') || '',
            contenteditable: el.getAttribute('contenteditable'),
            id: el.id || '',
            name: el.getAttribute('name') || '',
            aria_label: el.getAttribute('aria-label') || '',
            aria_labelledby_text: labelledby_of(el),
            label_for_text: labels_of(el),
            title: el.getAttribute('title') || '',
            alt: el.getAttribute('alt') || '',
            inner_text: (el.innerText || '').replace(/\\s+/g, ' ').trim(),
            value: (el.value != null ? String(el.value) : '').slice(0, 40),
            placeholder: el.getAttribute('placeholder') || '',
            attrs: attrs,
            bbox: b,
            chain: chain(el),
        });
        if (out.length >= 200) break;
    }
    return out;
}
"""


def _build_items(raw_list, roles_filter=None, max_items=40):
    """raw → (role,label,sel,...); 复用 a11y_dom 标签策略(P1)。"""
    from core.tools.a11y_dom import build_selector, is_content_like_placeholder, role_of, stable_label

    items = []
    seen_sel = set()
    for raw in raw_list:
        el = {
            "tag": raw.get("tag"),
            "type": raw.get("type"),
            "role_attr": raw.get("role_attr"),
            "contenteditable": raw.get("contenteditable"),
            "aria_label": raw.get("aria_label"),
            "aria_labelledby_text": raw.get("aria_labelledby_text"),
            "label_for_text": raw.get("label_for_text"),
            "title": raw.get("title"),
            "alt": raw.get("alt"),
            "inner_text": raw.get("inner_text"),
            "value": raw.get("value"),
            "placeholder": raw.get("placeholder"),
            "name": raw.get("name"),
        }
        role = role_of(el)
        if roles_filter and role not in roles_filter:
            continue
        label, label_source = stable_label(el)
        if not label:
            continue
        # 无语义的纯兜底条目(链接/未知)丢弃, 防噪音
        if label_source == "role-desc" and role in ("link", "other"):
            continue
        chain = []
        for c in raw.get("chain") or []:
            chain.append({"tag": c.get("tag"), "id": c.get("id") or None, "idx": c.get("idx")})
        sel = build_selector(chain)
        if not sel or sel in seen_sel:
            continue
        seen_sel.add(sel)
        bb = raw.get("bbox") or {}
        items.append(
            {
                "id": len(items) + 1,
                "role": role,
                "label": label[:40],
                "label_source": label_source,
                "placeholder_content": is_content_like_placeholder(el.get("placeholder")),
                "tag": (raw.get("tag") or ""),
                "sel": sel,
                "x": bb.get("x"),
                "y": bb.get("y"),
                "w": bb.get("w"),
                "h": bb.get("h"),
            }
        )
        if len(items) >= max_items:
            break
    return items


def _do_enumerate(page, sess, params):
    url = (params.get("url") or "").strip()
    if url or not sess.get("url"):
        target = url or sess.get("url") or "about:blank"
        loaded = False
        for attempt in range(2):  # 网络瞬断重试一次
            try:
                page.goto(target, wait_until="load", timeout=30000)
                loaded = True
                break
            except Exception:
                if attempt == 0:
                    page.wait_for_timeout(2000)
        page.wait_for_timeout(2000)
        if url and not loaded:
            sess["url"] = page.url if page.url and page.url != "about:blank" else target
            return {"success": False, "error": "页面加载失败(超时/网络): %s" % target}
        sess["url"] = page.url
    raw = page.evaluate(_JS_ENUM)
    roles_filter = params.get("roles")
    if isinstance(roles_filter, str):
        roles_filter = [roles_filter]
    try:
        max_items = int(params.get("max_items") or 40)
    except (TypeError, ValueError):
        max_items = 40
    items = _build_items(raw, roles_filter=set(roles_filter) if roles_filter else None, max_items=max_items)
    sess["items"] = items
    from core.tools.a11y_dom import items_text as _it_text

    text, _order = _it_text(items)
    return {
        "success": True,
        "action": "enumerate",
        "page_id": sess.get("_pid", ""),
        "url": page.url,
        "title": page.title() or "",
        "count": len(items),
        "items": items,
        "items_text": text,
        "meta": {"truncated": len(raw) > max_items, "label_hint": "坐标 x/y 仅供展示; 选择只依据 id/role/label"},
    }


_FILL_SCAN_JS = r"""
() => {
    const out = [];
    const els = document.querySelectorAll(
        'textarea:not([disabled]), input:not([disabled])[type=text], input:not([disabled])[type=search], [contenteditable="true"]');
    for (const el of els) {
        const r = el.getBoundingClientRect();
        if (!r.width || !r.height || r.width < 6 || r.height < 6) continue;
        const cs = getComputedStyle(el);
        if (cs.display === 'none' || cs.visibility === 'hidden' || Number(cs.opacity || 1) === 0) continue;
        out.push({tag: el.tagName, id: el.id || ''});
    }
    return out;
}
"""


def _fill_any_editable(page, sess, value):
    """fill 兜底(执行时直接 DOM 扫描, 百度 A/B 换层/变体实证):
    逐个可见可编辑元素尝试 fill + 回读; 失败则点击聚焦 + 键盘输入重试。"""
    try:
        cands = page.evaluate(_FILL_SCAN_JS)
    except Exception:
        return None
    for c in cands:
        sel = ("#" + c["id"]) if c.get("id") else c["tag"].lower()
        # 尝试 playwright fill + 回读
        try:
            page.wait_for_selector(sel, state="visible", timeout=2000)
            page.fill(sel, value)
            got = _read_value(page, sel)
            if got == value:
                return {"sel": sel, "method": "fill"}
        except Exception:
            pass
        # 点击聚焦 + 全选 + 键盘输入
        try:
            page.locator(sel).click(timeout=1500)
            page.keyboard.press("Control+A")
            page.keyboard.type(value, delay=10)
            got = _read_value(page, sel)
            if got == value:
                return {"sel": sel, "method": "keyboard"}
        except Exception:
            continue
    return None


def _read_value(page, sel):
    """读取输入值(兼容 input/textarea 的 value 与 contenteditable 的 text)。"""
    try:
        return page.eval_on_selector(sel, "el => (el.value != null ? el.value : (el.textContent || ''))")
    except Exception:
        return ""


def _vision_pick(page, items, intent):
    """vision 回退: 截图 + 把 id 画到 bbox → qwen2.5vl 看图返回编号 → 匹配 item。"""
    import os as _os

    _dir = "data/screenshots"
    try:
        _os.makedirs(_dir, exist_ok=True)
        _shot = _os.path.join(_dir, "browser_hybrid_overlay_%d.png" % _os.getpid())
        page.screenshot(path=_shot, full_page=False)
        from core.tools.semantic_select import ask_vision_choice, draw_numbered_overlay

        _ov = _os.path.join(_dir, "browser_hybrid_overlay_num_%d.png" % _os.getpid())
        if not draw_numbered_overlay(_shot, _ov, items):
            return None
        _n = ask_vision_choice(intent, _ov)
        if _n is None:
            return None
        for _it in items:
            if int(_it.get("id") or -1) == _n:
                return _it
    except Exception:
        return None
    return None


def _do_act(page, sess, params):
    from core.tools.a11y_dom import validate_selection

    op = (params.get("action") or "").strip()
    if op not in ("click", "fill", "type", "press", "select_option", "hover", "screenshot"):
        return {"success": False, "error": "act 动作不支持: %r" % op}
    try:
        index = int(params.get("index"))
    except (TypeError, ValueError):
        return {"success": False, "error": "act 需要整数 index(来自 enumerate 清单序号)"}
    items = sess.get("items") or []
    v = validate_selection(index, len(items), action=op, items_roles=[it["role"] for it in items])
    if not v["ok"]:
        return {"success": False, "error": v["reason"]}
    it = items[index - 1]
    sel = it["sel"]
    value = params.get("value")
    # P3 模式B: 关键动作双检 — 本地文本模型对打乱清单独立再选, 两次一致才执行
    _need_dc = bool(params.get("double_check")) and bool(params.get("intent"))
    if _need_dc:
        try:
            from core.tools.semantic_select import double_check as _dc_fn

            _dc = _dc_fn(
                items,
                str(params.get("intent")),
                index,
                model=str(params.get("checker_model") or "qwen2.5:7b-instruct-q4_0-gpu"),
                port=int(params.get("checker_port") or 11435),
            )
        except Exception as _dce:
            return {"success": False, "error": "双检调用失败: %s" % _dce}
        if not _dc["agree"]:
            _payload = {
                "intent": params.get("intent"),
                "agent": {"index": index, "role": it["role"], "label": it["label"]},
                "checker": {"index": _dc.get("checker_id"), "raw": (_dc.get("checker_raw") or "")[:80]},
            }
            _msg = "双检不一致(agent=#%s, checker=#%s), 动作未执行" % (index, _dc.get("checker_id"))
            if (params.get("fallback") or "none") == "vision":
                _vit = _vision_pick(page, items, str(params.get("intent")))
                _payload["vision"] = _vit["id"] if _vit else None
                if _vit and _vit["id"] in (index, _dc.get("checker_id")):
                    if _vit["id"] != index:  # 采纳 vision 选择
                        it = _vit
                        index = int(_vit["id"])
                        sel = _vit["sel"]
                        _vv = validate_selection(index, len(items), action=op, items_roles=[x["role"] for x in items])
                        if not _vv["ok"]:
                            return {
                                "success": False,
                                "reason": "double_check_conflict",
                                "error": _msg + " 且 vision 目标 role 不匹配",
                                "payload": _payload,
                            }
                    _payload["vision_adopted"] = True
                    _msg += " → vision 回退采纳 #%s" % _vit["id"]
                else:
                    return {
                        "success": False,
                        "reason": "double_check_conflict",
                        "error": _msg + " 且 vision 回退未收敛(#%s), 请 ask 老板或重新描述意图" % (_payload["vision"]),
                        "payload": _payload,
                    }
            else:
                return {
                    "success": False,
                    "reason": "double_check_conflict",
                    "error": _msg + "; 可 fallback=vision 自动回退或 ask 老板",
                    "payload": _payload,
                }
    # 等待可见
    try:
        page.wait_for_selector(sel, state="visible", timeout=5000)
    except Exception:
        # 一次自动重定位(SPA 漂移防护): 重新 enumerate 后按 label+role 找
        try:
            raw = page.evaluate(_JS_ENUM)
            fresh = _build_items(raw)
            if fresh:
                sess["items"] = fresh
            hit = [x for x in (sess.get("items") or []) if x["role"] == it["role"] and x["label"] == it["label"]]
            if hit:
                sel = hit[0]["sel"]
                page.wait_for_selector(sel, state="visible", timeout=5000)
            else:
                return {
                    "success": False,
                    "error": "元素不可见且重定位失败(DOM 已变), 请重新 enumerate",
                    "intent": {"role": it["role"], "label": it["label"]},
                }
        except Exception as exc:
            return {"success": False, "error": "定位失败: %s" % exc}
    sub = op  # op 即动作(click/fill/type/press/select_option/hover/screenshot)
    if sub in ("fill", "type", "press", "select_option", "click", "hover", "screenshot"):
        try:
            if op == "fill":
                if value is None:
                    return {"success": False, "error": "fill 需要 value"}
                try:
                    page.fill(sel, value)
                except Exception:
                    _hit = _fill_any_editable(page, sess, value)
                    if _hit is None:
                        return {"success": False, "error": "fill 失败且未找到可编辑元素(DOM 已变), 请重新 enumerate"}
                    sel = _hit["sel"]  # 后续回读校验用重定位后的选择器
            elif op == "type":
                page.type(sel, value or "", delay=20)
            elif op == "press":
                page.press(sel, value or "Enter")
            elif op == "select_option":
                page.select_option(sel, value or "")
            elif op == "click":
                page.click(sel, timeout=8000)
            elif op == "hover":
                page.hover(sel)
            elif op == "screenshot":
                shot = params.get("screenshot_path") or ""
                if shot:
                    os.makedirs(os.path.dirname(shot) or ".", exist_ok=True)
                    page.screenshot(path=shot)
        except Exception as exc:
            return {
                "success": False,
                "error": "act %s 失败: %s" % (op, exc),
                "target": {"index": index, "role": it["role"], "label": it["label"], "sel": sel},
            }
    else:
        return {"success": False, "error": "act 子动作不支持: %r(click/fill/type/press/select_option/hover/screenshot)" % op}
    # P4 发现: 链接常 target=_blank 开新标签页 → click 后接管新页(会话页面切换)
    if op == "click":
        _u_before = page.url
        try:
            _pages = sess.get("context").pages
            if len(_pages) > 1:
                _np = _pages[-1]
                if _np.url and _np.url != _u_before:
                    sess["page"] = _np
                    page = _np
                    _np.bring_to_front()
                    _np.wait_for_timeout(1200)
        except Exception:
            pass
        # headless 中 target=_blank 链接点击常不产生新页(浏览器策略) → 取 href 同页导航兜底
        if page.url == _u_before and str(it.get("tag") or "").upper() == "A":
            try:
                _href = page.eval_on_selector(sel, "el => el.href")
                if _href and str(_href).startswith("http"):
                    page.goto(_href, wait_until="load", timeout=30000)
                    page.wait_for_timeout(1200)
            except Exception:
                pass
    # 动作后小等 + 回读校验
    page.wait_for_timeout(800)
    evidence = _evidence(page, params)
    # 输入回读校验
    if op in ("fill", "type"):
        try:
            got = page.input_value(sel)
            evidence["field_value"] = got
            if value is not None and got != value:
                return {
                    "success": False,
                    "error": "输入回读不一致(期望 %r 实际 %r)" % (value, got),
                    "evidence": evidence,
                    "target": {"index": index, "role": it["role"], "label": it["label"]},
                }
        except Exception:
            pass
    return {
        "success": True,
        "action": op,
        "index": index,
        "target": {"role": it["role"], "label": it["label"], "sel": sel},
        "evidence": evidence,
    }


def _do_observe(page, sess, params):
    check = (params.get("check") or "").strip()
    value = params.get("value")
    if check == "url_contains":
        return {"success": bool(value and value in page.url), "check": check, "value": value, "url": page.url}
    if check == "text_visible":
        try:
            body = page.inner_text("body")
        except Exception:
            body = ""
        return {
            "success": bool(value and value in body),
            "check": check,
            "value": value,
            "found": bool(value and value in body),
        }
    if check == "field_value":
        try:
            index = int(params.get("index"))
        except (TypeError, ValueError):
            return {"success": False, "error": "field_value 需要 index(清单序号)"}
        items = sess.get("items") or []
        if not (1 <= index <= len(items)):
            return {"success": False, "error": "index 越界"}
        try:
            got = page.input_value(items[index - 1]["sel"])
        except Exception as exc:
            return {"success": False, "error": "读取输入框失败: %s" % exc}
        return {
            "success": bool(value is not None and got == value),
            "check": check,
            "index": index,
            "expected": value,
            "actual": got,
        }
    return {"success": False, "error": "observe check 不支持: %r(url_contains/text_visible/field_value)" % check}


def _evidence(page, params):
    ev = {"url": page.url, "title": page.title() or ""}
    try:
        head = page.evaluate("document.body ? document.body.innerText.slice(0, 240) : ''")
        ev["head"] = head.replace("\n", " ").strip()
    except Exception:
        ev["head"] = ""
    return ev


def handle(params):
    """browser_hybrid 工具入口(gateway_helpers 委托调用)。"""
    params = params or {}
    action = (params.get("action") or "").strip()
    _ACT_OPS = ("click", "fill", "type", "press", "select_option", "hover", "screenshot")
    if action not in ("enumerate", "observe", "close") + _ACT_OPS:
        return {
            "success": False,
            "error": "unsupported action: %r, supported: enumerate/observe/close + %s" % (action, "/".join(_ACT_OPS)),
        }
    _is_act = action in _ACT_OPS
    page_id = str(params.get("page_id") or "").strip() or "default"
    if not re.match(r"^[A-Za-z0-9_\-]{1,64}$", page_id):
        return {"success": False, "error": "page_id 非法(仅字母数字_- 且 <=64)"}
    url = (params.get("url") or "").strip()
    if url:
        import urllib.parse as up

        parsed = up.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return {"success": False, "error": "only http/https URLs are allowed"}
        if _is_private_host(parsed.hostname or ""):
            return {"success": False, "error": "localhost/内网地址不允许访问"}
    if (_is_act or action == "observe") and page_id not in _SESSIONS:
        return {"success": False, "error": "page_id 无活动页面, 请先 enumerate(url=...) 打开页面"}
    if _is_act and not (_SESSIONS.get(page_id) or {}).get("items"):
        return {"success": False, "error": "页面尚未 enumerate, 请先执行 enumerate 获取元素清单"}
    # TTL 清理 + 会话上限
    _br.reap()  # 批197: TTL/上限逻辑收敛到唯一出口
    if action == "close":
        _close_session(page_id)
        return {"success": True, "action": "close", "page_id": page_id}
    try:
        page, sess = _get_session(page_id, viewport_w=params.get("viewport_w"), viewport_h=params.get("viewport_h"))
    except Exception as exc:
        return {"success": False, "error": "浏览器启动失败: %s" % exc}
    sess["_pid"] = page_id
    try:
        if action == "enumerate":
            return _do_enumerate(page, sess, params)
        if action == "observe":
            return _do_observe(page, sess, params)
        return _do_act(page, sess, params)
    except Exception as exc:
        return {"success": False, "error": "%s: %s" % (type(exc).__name__, exc)}
