# -*- coding: utf-8 -*-
"""agent_client — V9 本地浏览器客户端(playwright 持久上下文)

用法:
  python agent_client.py --user-id <v9-user-id> [--ws ws://127.0.0.1:5007] [--headless] [--platform xiaohongshu]

流程:
  1) 启动真实 Chrome(persistent context, headed 默认)
  2) 连 V9 WS(默认 127.0.0.1:5007, 与 config/v9/execution_policy.yaml 的 browser_local.ws_port 一致), hello 注册 user_id
  3) 主循环收 exec{cmd_id, action, params} → playwright 执行 → result 回传
     (playwright sync 非线程安全: WS 线程只入队, 浏览器操作全在主线程)
  4) --platform 指定时启动即打开该平台登录页, 用户扫码一次, 登录态持久化
"""
import argparse
import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from actions import Actions
from browser import BrowserSession
from platforms import load_platforms
from ws_client import AgentWsClient


def main():
    ap = argparse.ArgumentParser(description="ClawsJoy V9 本地浏览器客户端")
    ap.add_argument("--ws", default=os.environ.get("AGENT_CLIENT_WS", "ws://127.0.0.1:5007"))
    ap.add_argument("--user-id", default=os.environ.get("AGENT_CLIENT_USER", "default"))
    ap.add_argument("--headless", action="store_true", help="无头模式(测试用; 真机登录需 headed)")
    ap.add_argument("--cookies-file", default="", help="启动时注入的 cookies 文件(name=value; 格式)")
    ap.add_argument("--profile-root", default=str(Path.home() / ".clawsjoy" / "profiles"))
    ap.add_argument("--platform", default="", help="启动时打开的登录平台(如 xiaohongshu)")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument(
        "--chrome", action="store_true", help="Windows: 用系统安装的 Chrome(playwright channel=chrome), 可复用用户日常登录态"
    )
    ap.add_argument(
        "--profile",
        default="",
        help=r"Windows: 指定 Chrome 用户数据目录(如 %LOCALAPPDATA%\Google\Chrome\User Data\Default); "
        r"传了则直接用该目录(不拼 /default); 留空用默认 profile",
    )
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    log = logging.getLogger("agent_client")

    platforms = load_platforms()
    _browser_kw = {}
    if args.chrome:
        _browser_kw["channel"] = "chrome"
        log.info("Windows Chrome 模式: channel=chrome")
    if args.profile:
        _browser_kw["user_data_dir"] = args.profile
        log.info("复用 Chrome 用户数据目录: %s", args.profile)
    browser = BrowserSession(
        args.profile_root, headless=args.headless, cookies_file=args.cookies_file, **_browser_kw
    ).start()
    actions = Actions(browser, platforms)

    # 本地白名单动作(无需浏览器页面): open_document / close_wps / lingxi_mcp  (2026-09-10)
    from local_actions import LOCAL_ACTIONS as _LOCAL_ACTIONS
    from local_actions import dispatch as _local_dispatch

    def execute(action, params):
        if action in _LOCAL_ACTIONS:
            log.info("exec local action=%s", action)
            try:
                return _local_dispatch(action, params) or {}
            except Exception as e:
                return {"error": "本地动作失败: %s" % str(e)[:200]}
        # 平台路由: navigate/search 按目标 URL 推断; click/fill/extract/scroll 用当前页面 + 按页面 URL 推断
        from platforms import infer_platform as _inf

        platform = str(params.get("platform") or "").strip()
        if not platform:
            if action in ("navigate", "search"):
                platform = _inf(str(params.get("url") or "")) or "xiaohongshu"
            else:
                _cur = browser.last_page()
                if _cur is None:
                    return {"error": "没有当前浏览器页面, 请先 navigate"}
                platform = _inf(_cur.url) or "xiaohongshu"
        cfg = platforms.get(platform, {})
        log.info("exec action=%s platform=%s", action, platform)
        try:
            if action in ("navigate", "search"):
                page = browser.page_for(platform, cfg)
            else:
                page = browser.last_page() or browser.page_for(platform, cfg)
        except Exception as e:
            return {"error": "浏览器不可用: %s" % str(e)[:200]}
        try:
            if action == "navigate":
                data = actions.navigate(page, params)
            elif action == "extract":
                data = actions.extract(page, params)
            elif action == "scroll":
                data = actions.scroll(page, params)
            elif action == "screenshot":
                data = actions.screenshot(page, params)
            elif action == "frames":
                data = actions.frames(page, params)
            elif action == "evaluate":
                data = actions.evaluate(page, params)
            elif action == "observe_start":
                data = actions.observe_start(page, params)
            elif action == "observe_stop":
                data = actions.observe_stop(page, params)
            elif action == "click":
                data = actions.click(page, platform, params)
            elif action == "fill":
                data = actions.fill(page, platform, params)
            elif action == "search":
                data = actions.search(page, platform, params)
            elif action == "upload":
                data = actions.upload(page, platform, params)
            elif action == "publish":
                data = actions.publish(page, platform, params)
            else:
                data = {"error": "unknown action: %s" % action}
            data = data or {}
            # 风控检测: 动作失败且页面处于验证页 → 升级为 verify_required(Agent 暂停提示用户过验证)
            if "error" in data and not data.get("verify_required"):
                v = browser.detect_verify(page, cfg)
                if v:
                    data = {"error": "检测到风控验证(%s)，请用户手动过验证后继续" % v, "verify_required": True, "platform": platform}
            return data
        except Exception as e:
            return {"error": str(e)[:300]}

    client = AgentWsClient(args.ws, args.user_id, tag="python-client")
    client.start()

    # 启动后(hello 连接就绪)上报各平台登录态
    def report_login_status():
        try:
            for plat, cfg in platforms.items():
                try:
                    page = browser.page_for(plat, cfg)
                    logged = browser.check_login(page, cfg)
                    client.send_login_status(plat, logged)
                    log.info("login_status %s=%s", plat, logged)
                except Exception:
                    client.send_login_status(plat, False)
        except Exception:
            pass

    if args.platform:
        try:
            browser.page_for(args.platform, platforms.get(args.platform, {}), login=True)
            log.info("请在浏览器窗口完成 %s 登录(扫码/密码), 登录态将持久化", args.platform)
        except Exception as e:
            log.error("打开登录页失败: %s", str(e)[:150])

    log.info("agent_client 运行中: %s user=%s (Ctrl+C 退出)", args.ws, args.user_id)
    log.info(
        "[AGENT_CONSTRAINT] 本进程已独占 profile=%s。禁止再写独立 playwright 脚本操作同一 profile(会锁冲突/网页自动关闭)。文件上传/发布请统一走 browser_local(upload/publish 动作)。",
        browser.profile_root / "default",
    )
    reported = False
    try:
        while True:
            item = client.next_exec(timeout=1.0)
            if item is None:
                if not reported and client.ws:
                    reported = True
                    report_login_status()
                continue
            cmd_id, action, params = item
            client.send_state("busy")
            try:
                data = execute(action, params) or {}
                ok = "error" not in data
            except Exception as e:
                data = {"error": str(e)[:300]}
                ok = False
            # 上报: 风控 → verify_required; 未登录 → login_status False
            if data.get("verify_required"):
                client.send_verify_required(
                    str(data.get("platform") or ""),
                )
                client.send_state("verify_wait")
            elif data.get("login_required"):
                client.send_login_status(str(data.get("platform") or ""), False)
            client.send_result(cmd_id, ok, data)
            client.send_state("idle")
    except KeyboardInterrupt:
        log.info("退出中…")
    finally:
        client.stop()
        browser.close()


if __name__ == "__main__":
    main()
