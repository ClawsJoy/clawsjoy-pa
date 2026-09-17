# -*- coding: utf-8 -*-
"""browser_local 动作执行 — playwright 原生实现(替代扩展 CDP)

动作: navigate / extract / screenshot / scroll / click / fill / search / upload / publish
成功返回纯数据 dict(无 "error" 键); 失败返回 {"error": ...}。
"""
import logging
import re
import urllib.parse

try:
    import selector_resolver  # 选择器自愈(2026-09-10)
except Exception:  # 被单独 import 时的兜底
    from . import selector_resolver  # type: ignore

log = logging.getLogger("agent_client.actions")

# 风控/验证页关键字(与 browser.VERIFY_KEYWORDS 对齐)
VERIFY_KEYWORDS = ["安全限制", "IP存在风险", "验证码", "滑动验证", "人机验证", "请完成验证", "captcha", "verify", "安全验证"]


# ===== observe 观察脚本(P2, 2026-08-26) =====
# 设计: docs/design/v9_browser_observe_design.md 附录A
_OBSERVE_START_JS = r"""(function () {
  if (window.__observe_log) return { started: false, reason: 'already' };
  var MAX = window.__observe_max || 200;
  var log = [];
  var t0 = Date.now();
  function rec(a) { if (log.length < MAX) { a.ts = Date.now() - t0; log.push(a); } }
  function selOf(el) {
    if (!el || el === document) return '';
    if (el.id) return '#' + el.id;
    var ph = el.getAttribute && el.getAttribute('placeholder');
    if (ph) return el.tagName.toLowerCase() + "[placeholder='" + ph.slice(0, 40) + "']";
    var t = (el.innerText || '').trim().slice(0, 8);
    if (t && /^[a-z\u4e00-\u9fa5]{2,8}$/.test(t)) return el.tagName.toLowerCase() + ":has-text('" + t + "')";
    var cls = String(el.className || '').split(' ').filter(function(c){ return c.length > 2 && c.length < 24 && !/^[a-zA-Z0-9_-]{16,}$/.test(c); })[0];
    if (cls) return el.tagName.toLowerCase() + '.' + cls;
    return el.tagName.toLowerCase();
  }
  document.addEventListener('click', function (e) {
    var el = e.target && e.target.closest ? e.target.closest('button,input,textarea,a,[role=button]') : e.target;
    rec({ type: 'click', selector: selOf(el), text: (el.innerText || el.value || '').trim().slice(0, 40), tag: el.tagName });
  }, true);
  document.addEventListener('input', function (e) {
    var el = e.target;
    rec({ type: 'input', selector: selOf(el), value: String(el.value || '').slice(0, 200), tag: el.tagName });
  }, true);
  document.addEventListener('change', function (e) {
    var el = e.target;
    if (el && (el.tagName === 'SELECT' || el.type === 'file')) {
      rec({ type: 'input', selector: selOf(el), value: '[file:' + (el.files ? el.files.length : 0) + ']', tag: el.tagName });
    }
  }, true);
  var of = window.fetch;
  window.fetch = function () {
    var url = arguments[0], opts = arguments[1] || {};
    if (!/log|collect|pv|track|monitor/i.test(String(url))) {
      var body = opts.body;
      rec({ type: 'api', method: (opts.method || 'GET'), url: String(url).slice(0, 200), params: (typeof body === 'string' ? body.slice(0, 500) : '') });
    }
    return of.apply(this, arguments);
  };
  window.addEventListener('popstate', function () {
    rec({ type: 'navigate', from: (window.__observe_last || location.href), to: location.href });
    window.__observe_last = location.href;
  });
  window.__observe_last = location.href;
  window.__observe_log = log;
  return { started: true, observe_id: 'obs_' + Math.random().toString(36).slice(2, 10) };
})()"""

_OBSERVE_STOP_JS = r"""(function () {
  var log = window.__observe_log || [];
  window.__observe_log = null;
  window.__observe_max = null;
  return JSON.stringify(log);
})()"""


def _wait(ms):
    import time

    time.sleep(max(0, (ms or 0) / 1000.0))


class Actions:
    # 需要登录态的动作(未登录先拦, 提示用户扫码)
    LOGIN_ACTIONS = {"search", "publish", "click", "fill"}

    def __init__(self, browser, platforms):
        self.browser = browser
        self.platforms = platforms
        self._observe = None  # observe 会话: {observe_id, start_ts}

    def _cfg(self, platform):
        return self.platforms.get(platform) or {}

    def _ensure_login(self, page, platform, action):
        """登录门槛: 明确未登录(False)时拦下并提示; None(未知)/True 放行。
        平台可配置 search_requires_login=False(如 YouTube 搜索匿名可用)跳过 search 门槛。"""
        cfg = self._cfg(platform)
        if action == "search" and not cfg.get("search_requires_login", True):
            return None
        logged = self.browser.check_login(page, cfg)
        if logged is False:
            return {"error": "平台 %s 未登录，请用户扫码登录后重试" % platform, "login_required": True, "platform": platform}
        return None

    # ---- 只读 ----
    def navigate(self, page, params):
        url = str(params.get("url") or "").strip()
        if not url:
            return {"error": "navigate 需要 url"}
        page.goto(url, timeout=int(params.get("timeout", 30000) or 30000), wait_until="domcontentloaded")
        _vp = params.get("viewport")
        if isinstance(_vp, dict) and _vp.get("width") and _vp.get("height"):
            try:
                page.set_viewport_size({"width": int(_vp["width"]), "height": int(_vp["height"])})
            except Exception:
                pass
        _wait(params.get("wait_ms", 1500))
        return {"title": page.title() or "", "url": page.url}

    def extract(self, page, params):
        target = self._frame_target(page, params.get("frame"))
        selector = str(params.get("selector") or "").strip()
        if selector:
            try:
                loc = target.locator(selector).first
                if loc.count() > 0:
                    return {"content": (loc.inner_text() or "").strip()[:10000]}
            except Exception:
                pass
        if params.get("include_hidden"):
            # 发布设置调研: 返回隐藏元素(下拉/弹层/选项列表/隐藏 input)的属性和文本
            return {"content": self._extract_hidden(target)}
        expr = "document.body ? document.body.innerText : ''"
        content = self._body_text(target, expr)
        if not content.strip():
            # SPA 水合/懒加载: 等一拍重试
            page.wait_for_timeout(800)
            content = self._body_text(page, expr)
        return {"content": content.strip()[:10000]}

    def _body_text(self, page, expr):
        try:
            return str(page.evaluate(expr) or "")
        except Exception as e:
            log.warning("extract evaluate 失败: %s", str(e)[:120])
            return ""

    def _extract_hidden(self, page):
        """收集隐藏/下拉/弹层元素(发布设置调研): 属性 + 文本 + 可见性。"""
        expr = """() => {
          const seen = new Set(), out = [];
          const nodes = document.querySelectorAll('input, select, option, textarea, button, [hidden], [class*=dropdown], [class*=DropDown], [class*=modal], [class*=Modal], [class*=menu], [class*=Menu], [class*=option], [class*=Option], [style*="display: none"], [style*="display:none"]');
          for (const e of nodes) {
            const vis = !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
            const text = (e.innerText || e.textContent || e.placeholder || e.getAttribute('aria-label') || '').trim().slice(0, 80);
            const key = e.tagName + '|' + (e.name || e.accept || e.type || e.className || e.placeholder || text).toString().slice(0, 50);
            if (seen.has(key)) continue;
            seen.add(key);
            // 隐藏容器(下拉/弹层)连同内部选项文本一并输出
            const isContainer = /dropdown|menu|modal|option|select/i.test((e.className || '').toString());
            const containerText = (isContainer && !vis) ? (e.innerText || '').trim().slice(0, 200) : '';
            out.push({tag: e.tagName, name: (e.name || ''), type: (e.type || ''), ph: (e.placeholder || '').slice(0, 30), accept: (e.accept || '').slice(0, 40), cls: (e.className || '').toString().slice(0, 35), visible: vis, text: text.slice(0, 50), options: containerText});
          }
          return out;
        }"""
        try:
            import json as _json

            items = page.evaluate(expr)
            return _json.dumps(items, ensure_ascii=False)[:10000]
        except Exception as e:
            return "extract_hidden 失败: %s" % str(e)[:120]

    def _frame_target(self, page, frame):
        """返回操作目标: frame 参数 → iframe 内 locator 根; 无 → page 本身。
        frame 支持: CSS selector(iframe#edit / iframe[src*=edit]) 或数字 index(0=第一个)。"""
        if not frame:
            return page
        import re as _re

        _fstr = str(frame).strip()
        try:
            if _re.fullmatch(r"\d+", _fstr):
                _f = page.frames[int(_fstr)] if int(_fstr) < len(page.frames) else None
                if _f:
                    return _f
            return page.frame_locator(_fstr)
        except Exception as e:
            log.warning("frame_locator 失败(%s): 回退主 frame", str(e)[:100])
            return page

    def frames(self, page, params):
        """列出页面所有 frame: name/src/url(iframe 穿透定位用)。"""
        out = []
        for i, f in enumerate(page.frames):
            out.append({"index": i, "name": f.name or "", "url": (f.url or "")[:160]})
        return {"frames": out}

    def evaluate(self, page, params):
        """在页面/iframe 内执行 JS 表达式, 返回 JSON 结果。用于复杂 DOM 提取(弹层/shadow DOM)。
        expr: JS 表达式(返回可 JSON 序列化的值); frame: 可选 iframe 定位。"""
        expr = str(params.get("expr") or "").strip()
        if not expr:
            return {"error": "evaluate 需要 expr(JS 表达式)"}
        target = self._frame_target(page, params.get("frame"))
        try:
            val = target.evaluate(expr)
            import json as _j

            return {"result": _j.dumps(val, ensure_ascii=False, default=str)[:10000]}
        except Exception as e:
            return {"error": "evaluate 失败: %s" % str(e)[:200]}

    def observe_start(self, page, params):
        target = self._frame_target(page, params.get("frame"))
        max_actions = int(params.get("max_actions") or 200)
        try:
            target.evaluate("window.__observe_max = %d;" % max_actions)
            r = target.evaluate(_OBSERVE_START_JS)
            if not isinstance(r, dict) or not r.get("started"):
                return {"error": "observe_start 失败: " + str(r)[:150]}
            import time as _t

            self._observe = {"observe_id": r.get("observe_id", ""), "start_ts": _t.time()}
            return {"success": True, "observe_id": r.get("observe_id"), "started": True}
        except Exception as e:
            return {"error": "observe_start 注入失败: " + str(e)[:200]}

    def observe_stop(self, page, params):
        target = self._frame_target(page, params.get("frame"))
        obs_id = str(params.get("observe_id") or "")
        if self._observe and obs_id and self._observe.get("observe_id") != obs_id:
            return {"error": "observe_id 不匹配: 期望 " + str(self._observe.get("observe_id")) + ", 传入 " + obs_id}
        if not self._observe and not obs_id:
            return {"error": "没有活跃的观察会话, 请先 observe_start"}
        try:
            raw = target.evaluate(_OBSERVE_STOP_JS)
            import json as _j

            log = _j.loads(raw) if isinstance(raw, str) else (raw or [])
        except Exception as e:
            log = []
        duration = 0
        if self._observe:
            import time as _t

            duration = int((_t.time() - self._observe.get("start_ts", 0)) * 1000)
        obs_id = obs_id or (self._observe or {}).get("observe_id", "")
        self._observe = None
        steps = self._observe_to_steps(log)
        return {
            "success": True,
            "observe_id": obs_id,
            "duration_ms": duration,
            "action_count": len(log),
            "actions": log,
            "sop_draft": steps,
        }

    def _observe_to_steps(self, log):
        steps = []
        seen = {}
        for a in log or []:
            t = a.get("type", "")
            if t == "navigate" and a.get("to"):
                steps.append("navigate(" + str(a["to"])[:80] + ")")
            elif t == "click" and a.get("selector"):
                txt = (a.get("text") or "")[:20]
                steps.append("click(" + a["selector"] + (", " + txt if txt else "") + ")")
            elif t == "input" and a.get("selector"):
                sel = a["selector"]
                steps = [s for s in steps if not s.startswith("input(" + sel + ",")]
                steps.append("input(" + sel + ", value=" + str(a.get("value") or "")[:30] + ")")
            elif t == "api" and a.get("url"):
                steps.append("api(" + str(a.get("method", "?")) + " " + str(a["url"])[:80] + ")")
        return {"steps": steps, "confidence": min(0.9, 0.5 + 0.05 * len(steps))}

    def _pick_upload_input(self, page, kind):
        """按 accept 特征选 file input: cover(窄图片集)/image(宽图片集)/document(文档)/video(视频)。
        优先平台配置 selector, 否则 accept 启发式。"""
        # 2026-08-24 修复: 取当前操作平台配置(原来 hardcode zhihu, B站/小红书 cover/video 配置读不到)
        _plat = getattr(self, "_current_platform", "") or "zhihu"
        cfg = self._cfg(_plat).get("publish") or {}
        if kind == "cover" and cfg.get("cover_input"):
            return cfg["cover_input"]
        if kind == "image" and cfg.get("image_input"):
            return cfg["image_input"]
        if kind == "video" and cfg.get("video_input"):
            return cfg["video_input"]
        if kind == "document" and cfg.get("document_input"):
            return cfg["document_input"]
        try:
            all_in = page.query_selector_all("input[type=file]")
            for e in all_in:
                acc = (e.get_attribute("accept") or "").lower()
                if (
                    kind == "cover"
                    and (".jpeg" in acc or ".jpg" in acc or ".png" in acc)
                    and "webp" not in acc
                    and ".pdf" not in acc
                ):
                    return "input[type=file][accept*='.jpeg'], input[type=file][accept*='.jpg'], input[type=file][accept*='.png']"
                if kind == "image" and "image/" in acc and ("webp" in acc or "avif" in acc):
                    return "input[type=file][accept*='image/']"
                if kind == "document" and (".pdf" in acc or ".docx" in acc):
                    return "input[type=file][accept*='.pdf'], input[type=file][accept*='.docx']"
                if kind == "video" and ("video/" in acc or ".mp4" in acc or ".mov" in acc):
                    return "input[type=file][accept*='video/'], input[type=file][accept*='.mp4']"
        except Exception:
            pass
        return None

    def scroll(self, page, params):
        direction = -1 if str(params.get("direction") or "").strip() == "up" else 1
        amount = int(params.get("amount") or 800 or 800)
        page.evaluate("window.scrollBy({top: %d, behavior: 'smooth'})" % (direction * amount))
        page.wait_for_timeout(600)
        return {"scrolled": True, "scrollY": page.evaluate("window.scrollY")}

    def screenshot(self, page, params):
        import base64

        data = page.screenshot(full_page=bool(params.get("full_page")))
        b64 = base64.b64encode(data).decode("utf-8")
        return {"base64": b64[:500], "truncated": len(b64) > 500}

    # ---- 交互 ----
    def click(self, page, platform, params):
        _gate = self._ensure_login(page, platform, "click")
        if _gate:
            return _gate
        sel = str(params.get("selector") or "").strip()
        if not sel:
            return {"error": "click 需要 selector"}
        target = self._frame_target(page, params.get("frame"))
        # (2026-09-10) 选择器自愈: 角色选择器唯一性校验 + fallback 链 + 失败即封闭。
        # 原写法 locator(sel).first.click() 从不校验唯一性 → 选择器含糊时静默点错元素
        # (@DS Chat 第 1 轮就栽在这: 点中 34x34 的附件键而非发送键, 且返回 clicked:true)。
        sel, _diag = selector_resolver.resolve_for_action(target, self._cfg(platform), sel, "click")
        if not sel:
            return {"error": selector_resolver.describe_failure("click", _diag), "selector_diag": _diag}
        try:
            target.locator(sel).first.click(timeout=8000)
            out = {"clicked": True, "selector_used": sel}
            if _diag.get("strict"):
                out["selector_strict"] = True
                if _diag.get("healed"):
                    out["selector_healed"] = True
            return out
        except Exception as e:
            return {"error": "click 失败: %s" % str(e)[:150]}

    def _thread_guard(self, page, platform, params):
        """发消息前的【目标线程】硬门（2026-09-10 事故驱动）。

        事故: 第4轮联调发到了新建线程, 而不是老板指定的会话。
        根因: 流程里没有"确认目标线程"这一步; 客户端重启后页面为 about:blank,
             直接 navigate 基础地址就会新建会话 —— 而发送本身"成功"了, 故障静默。

        门规(默认拒绝, 与 endpoint_guard 同源哲学):
          - 平台配置声明了 send_precondition 才启用
          - 当前 url 必须已落在某个会话线程里 (/a/chat/s/<id>), 否则拒绝
          - 若显式给了 expect_sid, 当前 url 必须包含它, 否则拒绝
          - 确要新建会话, 必须显式 allow_new_thread=true —— 不允许"顺手"新建
        """
        cfg = self._cfg(platform)
        pre = cfg.get("send_precondition") if isinstance(cfg, dict) else None
        if not pre:
            return None
        if params.get("allow_new_thread"):
            return None
        try:
            url = str(page.url or "")
        except Exception:
            url = ""
        m = re.search(r"/a/chat/s/([0-9a-zA-Z-]{8,})", url)
        if not m:
            return {
                "error": (
                    "thread_guard 拒绝: 当前不在任何会话线程(url=%r), 在此发送会【新建会话】。"
                    "请先 navigate 到目标会话链接并复查 URL; 确要新建请显式传 allow_new_thread=true。"
                    "宁可不发, 也不能发错地方。"
                )
                % url
            }
        expect = str(params.get("expect_sid") or (pre.get("expect_sid") if isinstance(pre, dict) else "") or "").strip()
        if expect and expect != m.group(1):
            return {
                "error": ("thread_guard 拒绝: 目标线程不符。期望 sid=%s, 当前 sid=%s (url=%s)。" "已拒绝发送。") % (expect, m.group(1), url)
            }
        return None

    def fill(self, page, platform, params):
        _gate = self._ensure_login(page, platform, "fill")
        if _gate:
            return _gate
        _tg = self._thread_guard(page, platform, params)
        if _tg:
            return _tg
        sel = str(params.get("selector") or "").strip()
        text = str(params.get("text") or "")
        if not sel:
            return {"error": "fill 需要 selector"}
        target = self._frame_target(page, params.get("frame"))
        # (2026-09-10) 同 click: 输入框是角色选择器, 命中多个就必须先分辨, 否则可能填错框
        sel, _diag = selector_resolver.resolve_for_action(target, self._cfg(platform), sel, "fill")
        if not sel:
            return {"error": selector_resolver.describe_failure("fill", _diag), "selector_diag": _diag}
        try:
            target.locator(sel).first.fill(text, timeout=8000)
            out = {"filled": True, "selector_used": sel}
            if _diag.get("strict"):
                out["selector_strict"] = True
                if _diag.get("healed"):
                    out["selector_healed"] = True
            return out
        except Exception as e:
            return {"error": "fill 失败: %s" % str(e)[:150]}

    # ---- 搜索 + 卡片提取 ----
    def search(self, page, platform, params):
        cfg = self._cfg(platform)
        query = str(params.get("query") or "")
        if not query:
            return {"error": "search 需要 query"}
        _gate = self._ensure_login(page, platform, "search")
        if _gate:
            return _gate
        tpl = cfg.get("search_url") or ""
        if not tpl:
            return {"error": "平台 %s 未配置 search_url" % platform}
        url = str(params.get("url") or "").strip() or tpl.format(q=urllib.parse.quote(query))
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        _wait(params.get("wait_ms", 2500))
        # 风控/验证页快速检测(不空等 20s): 命中 → 立即返回 verify_required
        body = self._body_text(page, "document.body ? document.body.innerText : ''")
        if body and any(k in body for k in VERIFY_KEYWORDS):
            return {"error": "检测到风控验证，请用户手动过验证后继续", "verify_required": True, "platform": platform}
        cards = self._extract_cards(page, cfg)
        return {"url": page.url, "query": query, "results": cards}

    def upload(self, page, platform, params):
        """通用文件上传: kind=cover/image/video/document, files=[路径...]。
        返回上传结果; 上传后可选 wait_ms 等待渲染。"""
        _gate = self._ensure_login(page, platform, "upload")
        if _gate:
            return _gate
        kind = str(params.get("kind") or "image")
        self._current_platform = platform  # 供 _pick_upload_input 取平台配置
        files = params.get("files") or params.get("file") or []
        if isinstance(files, str):
            files = [files]
        if not files:
            return {"error": "upload 需要 files(文件路径列表)或 file(单路径)"}
        target = self._frame_target(page, params.get("frame"))
        _sel = self._pick_upload_input(target, kind)
        if not _sel:
            try:
                if page.query_selector("input[type=file]"):
                    _sel = "input[type=file]"
            except Exception:
                pass
        if not _sel:
            return {"error": "未找到 %s 类型的 file input(accept 特征不匹配)" % kind}
        try:
            target.set_input_files(
                _sel, files if len(files) > 1 else files[0], timeout=int(params.get("timeout") or 10000)
            )
        except Exception as e:
            return {"error": "set_input_files 失败: %s" % str(e)[:200]}
        _wait = int(params.get("wait_ms") or 3000)
        target.wait_for_timeout(_wait)
        return {"success": True, "kind": kind, "files": files, "selector": _sel, "waited_ms": _wait}

    def _extract_cards(self, page, cfg, limit=10):
        """提取笔记/视频卡片(标题+链接) — playwright 原生等待 JS 渲染(扩展方案从未等到)。"""
        card_sel = cfg.get("card_selector") or "section.note-item, .note-item"
        link_sel = cfg.get("link_selector") or "a"
        title_sel = cfg.get("title_selector") or ""
        try:
            page.wait_for_selector(card_sel, timeout=20000)
        except Exception:
            body = self._body_text(page, "document.body ? document.body.innerText : ''")
            return [{"hint": str(body)[:200]}] if body.strip() else []
        cards = page.query_selector_all(card_sel)[:limit]
        out = []
        for c in cards:
            try:
                link_el = c.query_selector(link_sel) or c
                href = (link_el.get_attribute("href") or "") if link_el else ""
                if href and not href.startswith("http"):
                    href = urllib.parse.urljoin(page.url, href)
                title = ""
                if title_sel:
                    t = c.query_selector(title_sel)
                    if t:
                        title = (t.inner_text() or "").strip()
                if not title:
                    raw = c.inner_text() or ""
                    title = raw.strip().splitlines()[0] if raw.strip() else ""
                out.append({"title": title[:120], "url": href})
            except Exception:
                continue
        return out

    # ---- 发布(走 V9 审批流, 客户端仅执行) ----
    def publish(self, page, platform, params):
        _gate = self._ensure_login(page, platform, "publish")
        if _gate:
            return _gate
        cfg = (self._cfg(platform) or {}).get("publish") or {}
        title = str(params.get("title") or "")
        content = str(params.get("content") or "")
        tags = params.get("tags") or []
        if isinstance(tags, str):
            tags = [t for t in re.split(r"[,，\s]+", tags) if t]
        tag_txt = " ".join("#" + str(t).lstrip("#") for t in tags)
        body = (content + "\n\n" + tag_txt).strip()
        filled = {"title": False, "content": False}
        if title and cfg.get("title"):
            try:
                page.locator(cfg["title"]).first.fill(title, timeout=5000)
                filled["title"] = True
            except Exception:
                pass
        if body and cfg.get("content"):
            try:
                loc = page.locator(cfg["content"]).first
                try:
                    loc.fill(body, timeout=5000)
                except Exception:
                    loc.click()
                    page.keyboard.type(body, delay=20)
                filled["content"] = True
            except Exception:
                pass
        # ---- 封面/正文插图上传(区分 input: 封面窄图片集 vs 正文宽图片集) ----
        uploads = {"cover": False, "image": False}
        _cover_path = str(params.get("cover") or "").strip()
        _imgs = params.get("images") or []
        if _cover_path:
            _sel = self._pick_upload_input(page, "cover")
            if _sel:
                try:
                    page.set_input_files(_sel, _cover_path, timeout=8000)
                    uploads["cover"] = True
                except Exception:
                    pass
        if _imgs:
            _sel2 = self._pick_upload_input(page, "image")
            if _sel2:
                try:
                    page.set_input_files(_sel2, list(_imgs), timeout=10000)
                    uploads["image"] = True
                except Exception:
                    pass
        # ---- 话题(click 输入 → 输入文本 → 下拉选第一个匹配) ----
        topics = params.get("topics") or []
        if isinstance(topics, str):
            topics = [t for t in re.split(r"[,，\s]+", topics) if t]
        topic_done = 0
        if topics:
            _ti = (
                cfg.get("topic_input")
                or "input[placeholder*='话题'], input[placeholder*='添加话题'], .TopicEditor input, [class*=topic] input"
            )
            _tl = cfg.get("topic_label") or "添加话题"
            _to = cfg.get("topic_option") or "[class*=option], [class*=suggest], [class*=Dropdown] li, [class*=Menu] li"
            try:
                _tin = page.locator(_ti).first
                for _tp in topics[:3]:
                    try:
                        # label 邻近兜底: placeholder selector 找不到时, 点「添加话题」label 旁的可编辑元素
                        if _tin.count() == 0 and _tl:
                            _lbl = page.get_by_text(_tl, exact=False).first
                            if _lbl.count() > 0:
                                _lbl.click(timeout=3000)
                                page.wait_for_timeout(400)
                                _near = page.locator('input[type=text], [contenteditable="true"]').all()[:10]
                                for _n in _near:
                                    try:
                                        _n.click(timeout=1500)
                                        _n.fill(str(_tp), timeout=1500)
                                        _tin = _n
                                        break
                                    except Exception:
                                        continue
                        if _tin.count() == 0:
                            raise Exception("话题输入未找到")
                        _tin.click(timeout=3000)
                        _tin.fill(str(_tp), timeout=3000)
                        page.wait_for_timeout(800)
                        _opt = page.locator(_to).first
                        if _opt.count() > 0:
                            _opt.click(timeout=3000)
                            topic_done += 1
                        else:
                            page.keyboard.press("Enter")
                            topic_done += 1
                        page.wait_for_timeout(400)
                    except Exception:
                        pass
            except Exception:
                pass
        # ---- 声明(原创声明等) ----
        decl_done = None
        _decl = str(params.get("declaration") or "").strip()
        if _decl and cfg.get("declaration"):
            try:
                _dl = page.locator(cfg["declaration"]).first
                _cur = (_dl.get_attribute("checked") == "true") if _dl.count() else False
                _want = _decl.lower() in ("true", "原创", "1", "yes")
                if _cur != _want:
                    _dl.click(timeout=3000)
                decl_done = _want
            except Exception:
                decl_done = None
        page.wait_for_timeout(int(params.get("wait_ms", 800) or 800))
        clicked = False
        if cfg.get("submit"):
            try:
                page.locator(cfg["submit"]).first.click(timeout=5000)
                clicked = True
            except Exception:
                pass
        return {
            "title_filled": filled["title"],
            "content_filled": filled["content"],
            "cover_uploaded": uploads["cover"],
            "image_uploaded": uploads["image"],
            "topics_added": topic_done,
            "declaration": decl_done,
            "publish_clicked": clicked,
        }
