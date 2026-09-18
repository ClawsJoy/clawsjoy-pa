# -*- coding: utf-8 -*-
"""Playwright 持久上下文浏览器会话 — 真实 Chrome(headed 默认), 登录态持久复用

- launch_persistent_context(user_data_dir) → 登录态/指纹跨重启保存
- 每平台独立页面(可同时多平台)
- headed 窗口常驻可见: 用户可直接扫码登录 / 过风控验证
"""
import logging
import os
from pathlib import Path

log = logging.getLogger("agent_client.browser")


class BrowserSession:
    def __init__(
        self, profile_root, headless=False, executable_path=None, cookies_file=None, channel=None, user_data_dir=None
    ):
        """浏览器会话。

        channel: 浏览器通道(custom=系统 Chrome / chrome=Windows 版 Chrome / msedge 等)
                 Windows 用 --chrome 启动真实 Chrome 时传 channel="chrome";
                 **默认仍用专用实例目录, 不接管日常 profile**(显式传 user_data_dir 才算接管)
        user_data_dir: **显式接管**一个已存在的 Chrome 用户数据目录(会复用其中登录态)。
                       传了则直接用该目录(不再拼 /default); 留空用 profile_root/default 专用实例目录。
        """
        self.profile_root = Path(profile_root)
        self.profile_root.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.executable_path = executable_path
        self.cookies_file = cookies_file
        self.channel = channel
        self.user_data_dir = user_data_dir
        self._pw = None
        self._ctx = None
        self._pages = {}  # platform -> page
        self._last_page = None  # 最近使用的页面(无 platform 动作路由用)

    def _resolve_user_data_dir(self):
        """返回实际 user_data_dir: 显式指定优先, 否则 profile_root/default。"""
        if self.user_data_dir:
            _d = Path(self.user_data_dir)
            _d.mkdir(parents=True, exist_ok=True)
            return str(_d)
        return str(self.profile_root / "default")

    def _announce_profile(self, user_data_dir):
        """**显式接管必须可见**：实际用哪个 profile 一律打日志。

        契约：``core/pes/windows.py::BROWSER_ISOLATION`` 的 ``user_profile_reuse=explicit_only``
        —— 复用日常 profile 只允许「**显式接管**」，且必须**看得见**（不许静默接管）。
        该契约本身仍是声明性的（``wired=False``），本函数是该策略在执行面的落点。

        - 显式传了 ``user_data_dir`` ⇒ **WARNING**（接管外部目录，会复用其中登录态）；
        - 留空（专用实例 ``profile_root/default``）⇒ INFO。
        """
        if self.user_data_dir:
            log.warning(
                "显式接管外部 profile 目录: %s（复用其登录态, 非专用实例; 与日常 Chrome 同目录时注意 profile 锁冲突）",
                user_data_dir,
            )
        else:
            log.info("使用专用实例 profile 目录: %s", user_data_dir)

    def _profile_locked(self) -> bool:
        """检测 profile 是否被其他 Chromium 实例占用(SingletonLock 机制)。
        返回 True 表示锁文件存在且被锁定(另一个浏览器正在用该 profile)。"""
        lock_dir = self.profile_root / "default"
        import glob as _glob

        # Chromium 锁: SingletonLock(老) / SingletonCookie / SingletonSocket(新)
        for name in ("SingletonLock", "SingletonSocket", "SingletonCookie"):
            f = lock_dir / name
            if f.exists():
                try:
                    # 有内容的 SingletonLock 表示被持有; 空文件可能是残留
                    if f.stat().st_size > 0:
                        return True
                except Exception:
                    pass
        # 更可靠的判定: SingletonLock 存在且非空 + 最近修改
        return False

    def start(self):
        from playwright.sync_api import sync_playwright

        # 2026-08-24: profile 锁检测 — 若另一实例占用同一 profile, 立即报错而非让 playwright 崩溃
        if self._profile_locked():
            raise RuntimeError(
                "profile 被其他浏览器实例占用: %s (SingletonLock)。"
                "请先关闭占用进程(如残留的 playwright 脚本浏览器/旧 agent_client), 再启动。"
                "⚠️ 禁止再写独立 playwright 脚本操作同一 profile — 统一走 browser_local 工具。" % (self.profile_root / "default")
            )
        self._pw = sync_playwright().start()
        args = []
        if os.name == "posix":
            args += ["--no-sandbox", "--disable-dev-shm-usage"]
        # 最大化启动 + 不固定视口: 窗口与用户日常全屏一致(此前固定小视口 469x554 导致三栏溢出)
        args += ["--start-maximized"]
        _ud = self._resolve_user_data_dir()
        # X-18 方向 3（2026-09-18 拍）: 先宣告、再启动 —— 显式接管必须在日志里可见
        self._announce_profile(_ud)
        _kw = dict(
            headless=self.headless,
            args=args,
            executable_path=self.executable_path or None,
            # 显式视口=窗口尺寸: no_viewport 对系统 Chrome 不生效(viewport 1241 不跟随窗口1920)
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
        )
        if self.channel:
            # Windows: channel="chrome" 用系统安装的 Chrome(仍用专用实例目录, 不接管日常 profile)
            _kw["channel"] = self.channel
            log.info("使用系统浏览器 channel=%s", self.channel)
        self._ctx = self._pw.chromium.launch_persistent_context(_ud, **_kw)
        log.info(
            "浏览器已启动 persistent context(headless=%s, channel=%s, profile=%s)",
            self.headless,
            self.channel or "default",
            _ud,
        )
        self._inject_cookies()
        return self

    def page_for(self, platform, platform_cfg=None, login=False):
        """取平台页面; 无则新开 tab; login=True 导航到登录页。"""
        page = self._pages.get(platform)
        if page is None or page.is_closed():
            page = self._ctx.new_page()
            self._pages[platform] = page
        if login:
            url = (platform_cfg or {}).get("login_url") or "https://www.xiaohongshu.com"
            try:
                page.goto(url, timeout=60000, wait_until="domcontentloaded")
                log.info("已打开 %s 登录页: %s", platform, url)
            except Exception as e:
                log.warning("打开 %s 登录页失败: %s", platform, str(e)[:150])
        self._last_page = page
        return page

    def last_page(self):
        """最近使用的页面(无 platform 参数的动作应路由到它)。"""
        if self._last_page is not None and not self._last_page.is_closed():
            return self._last_page
        return None

    def set_last_page(self, page):
        self._last_page = page

    def check_login(self, page, platform_cfg=None):
        """粗略登录态: 检查持久上下文 cookies 中是否含平台登录标识(配置 login_cookie)。
        True=已登录 / False=未登录 / None=无法判断(未配置 login_cookie)。"""
        names = (platform_cfg or {}).get("login_cookie") or []
        if not names:
            return None
        try:
            have = set(c.get("name", "") for c in self._ctx.cookies())
            return any(n in have for n in names)
        except Exception:
            return None

    # 风控/验证页关键字(可被 platform_cfg["verify_keywords"] 覆盖)
    VERIFY_KEYWORDS = ["安全限制", "IP存在风险", "验证码", "滑动验证", "人机验证", "请完成验证", "captcha", "verify", "安全验证"]

    def _body_text(self, page):
        try:
            return str(page.evaluate("document.body ? document.body.innerText : ''") or "")
        except Exception:
            return ""

    def detect_verify(self, page, platform_cfg=None):
        """检测当前页面是否处于风控/验证状态。命中返回描述, 否则 None。"""
        try:
            url = (page.url or "").lower()
            if any(k in url for k in ("captcha", "verify", "security-verification", "login")):
                return "url:" + page.url
            body = self._body_text(page)
            keywords = (platform_cfg or {}).get("verify_keywords") or self.VERIFY_KEYWORDS
            for k in keywords:
                if k in body:
                    return "keyword:" + k
        except Exception:
            pass
        return None

    def _inject_cookies(self):
        """从 cookies 文件注入登录态(格式: name=value; name=value; ... 多行)。"""
        if not self.cookies_file or not self._ctx:
            return
        try:
            import os as _os

            _f = (
                self.cookies_file
                if _os.path.isabs(self.cookies_file)
                else _os.path.join(_os.getcwd(), self.cookies_file)
            )
            if not _os.path.exists(_f):
                log.warning("cookies 文件不存在: %s", _f)
                return
            _parsed = {}
            for _ln in open(_f, encoding="utf-8").read().splitlines():
                for _part in _ln.split(";"):
                    _part = _part.strip()
                    if not _part or "=" not in _part:
                        continue
                    _n, _, _v = _part.partition("=")
                    if _n.strip():
                        _parsed[_n.strip()] = {
                            "name": _n.strip(),
                            "value": _v.strip(),
                            "domain": ".zhihu.com",
                            "path": "/",
                        }
            _ck = list(_parsed.values())
            if _ck:
                self._ctx.add_cookies(_ck)
                log.info("已注入 %d 个 cookies", len(_ck))
        except Exception as e:
            log.warning("cookies 注入失败: %s", str(e)[:120])

    def close(self):
        try:
            if self._ctx:
                self._ctx.close()
        except Exception:
            pass
        try:
            if self._pw:
                self._pw.stop()
        except Exception:
            pass
        log.info("浏览器已关闭")
