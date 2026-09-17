# -*- coding: utf-8 -*-
"""批197 · 浏览器**唯一出口**（统一 launch / 会话复用 / CDP 连接层）——「A 第一步」。

为什么要有它（老板 2026-09-16 拍板 A）：此前全仓 **3 处各自** `sync_playwright()` + `chromium.launch(headless=True)`：
  · `core/tools/browser_hybrid_impl.py`（会话复用：TTL 600s / 上限 4）
  · `core/tools/table_extract.py`（一次性读取）
  · `core/lib/gateway_helpers.py`（一次性读取）
⇒ 各起各的浏览器、各拿各的 profile ⇒ 登录态与「渲染是否同源」无从治理（体检 109 延伸）。
本模块把 launch **收敛到一处**，并内置 **CDP 连接层**：专用实例长驻 + 端口只 Windows 本机 + portproxy（老板已拍）。

对外 API（**别再自己 launch**；门内判据会拦住第四个出口）：
  · `prepare_env()`                    —— `PLAYWRIGHT_BROWSERS_PATH` 默认值（原两处各自 setdefault，收敛到一处）
  · `get_driver()`                     —— 进程内长驻 playwright driver（跨调用复用，不再每次起 stop）
  · `browser_ctx()`                    —— **一次性**浏览器（contextmanager，供单发读取类工具）
  · `get_session(page_id, **kw)`       —— **复用型**会话（TTL/上限，供交互式工具）
  · `close_session(pid)` / `reap()` / `session_stats()`

模式（`CLAWSJOY_BROWSER_CDP`，如 `http://127.0.0.1:9222`）：
  · 未设置 ⇒ 现状不变：launch 自己的 chromium（headless）
  · 已设置 ⇒ `connect_over_cdp` 连**长驻专用实例**（真同源：同一浏览器、同一 profile、老板屏幕可见）
  · **连不上则明确报错，不悄悄回退 launch** —— 静默回退会造出「以为同源、其实另起一个」的**假成交**
"""
import logging
import os
import threading
import time
from contextlib import contextmanager
from typing import Dict, Optional, Tuple
from core.lib.paths import playwright_browsers_path

log = logging.getLogger(__name__)

BROWSERS_PATH_DEFAULT = playwright_browsers_path()
MAX_SESSIONS = 4
SESSION_TTL_S = 600

_PLAYWRIGHT = None
_LOCK = threading.Lock()
# page_id -> {"browser", "context", "page", "url", "items", "ts"}（与批-old browser_hybrid 同形）
SESSIONS: Dict[str, dict] = {}


def prepare_env():
    """部署环境 chromium 缓存路径（可被 shell env 覆盖）——**唯一一处** setdefault。"""
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", BROWSERS_PATH_DEFAULT)


def cdp_url() -> str:
    """CDP 连接地址；空 = 未启用（走 launch）。"""
    return str(os.environ.get("CLAWSJOY_BROWSER_CDP") or "").strip()


def get_driver():
    """进程内长驻 playwright driver（跨工具调用复用；**不再**每次 sync_playwright() 起停）。"""
    global _PLAYWRIGHT
    with _LOCK:
        if _PLAYWRIGHT is None:
            from playwright.sync_api import sync_playwright

            _PLAYWRIGHT = sync_playwright().start()
        return _PLAYWRIGHT


def _open_browser():
    """**全仓唯一的浏览器打开点**。返回 (browser, mode)。"""
    prepare_env()
    driver = get_driver()
    url = cdp_url()
    if url:
        try:
            b = driver.chromium.connect_over_cdp(url)
            log.info("[BROWSER_EXIT] CDP 已连接 %s（同源模式）", url)
            return b, "cdp"
        except Exception as exc:
            # 明确失败，**不**回退 launch（否则「以为同源其实另起」= 假成交）
            raise RuntimeError(
                "CDP 连接失败(%s)：%s（请先起专用实例：bash tools/start_dedicated_chrome.sh（mirrored 网络不需要 portproxy））" % (url, exc)
            )
    b = driver.chromium.launch(headless=True)
    return b, "launch"


@contextmanager
def browser_ctx():
    """一次性浏览器：with 内用完即关（供单发读取类工具；driver 仍复用）。"""
    browser, mode = _open_browser()
    try:
        yield browser
    finally:
        try:
            browser.close()
        except Exception:
            pass


@contextmanager
def with_page(viewport_w: Optional[int] = None, viewport_h: Optional[int] = None):
    """一次性页面（= browser_ctx + new_context + new_page，自动收尾）。"""
    with browser_ctx() as browser:
        ctx = browser.new_context(viewport={"width": int(viewport_w or 1280), "height": int(viewport_h or 810)})
        page = ctx.new_page()
        try:
            yield page
        finally:
            try:
                ctx.close()
            except Exception:
                pass


def close_session(page_id: str) -> None:
    s = SESSIONS.pop(page_id, None)
    if not s:
        return
    try:
        s["browser"].close()
    except Exception:
        pass


def reap(now: Optional[float] = None, ttl: int = SESSION_TTL_S, cap: int = MAX_SESSIONS) -> None:
    """TTL 清理 + 会话上限（原 browser_hybrid_impl 内联逻辑，收敛到出口）。"""
    t = now if now is not None else time.time()
    for pid in list(SESSIONS):
        if t - (SESSIONS[pid].get("ts") or 0) > ttl:
            close_session(pid)
    while len(SESSIONS) >= cap:
        old = min(SESSIONS, key=lambda k: SESSIONS[k].get("ts") or 0)
        close_session(old)


def get_session(
    page_id: str, viewport_w: Optional[int] = None, viewport_h: Optional[int] = None
) -> Tuple[object, dict]:
    """复用型会话（同 page_id 返回同一页面；超过 TTL/上限由 reap 处理）。"""
    now = time.time()
    s = SESSIONS.get(page_id)
    if s is not None and s.get("page") is not None:
        s["ts"] = now
        return s["page"], s
    browser, mode = _open_browser()
    ctx = browser.new_context(viewport={"width": int(viewport_w or 1280), "height": int(viewport_h or 810)})
    page = ctx.new_page()
    s = {"browser": browser, "context": ctx, "page": page, "url": "", "items": [], "ts": now, "mode": mode}
    SESSIONS[page_id] = s
    return page, s


def session_stats() -> dict:
    return {
        "sessions": len(SESSIONS),
        "ttl_s": SESSION_TTL_S,
        "cap": MAX_SESSIONS,
        "mode": ("cdp" if cdp_url() else "launch"),
        "cdp_url": cdp_url(),
    }
