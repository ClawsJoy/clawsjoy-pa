# -*- coding: utf-8 -*-
"""agent_client 第4+5步验证: login_status/login_required + verify_required + click/fill/publish

- nologin_shop(未登录 cookie) → search 返回 login_required(Agent 提示扫码)
- verify_shop(页面含风控文案) → search 返回 verify_required + 客户端发 verify_required 消息
- shop(发布表单 fixture) → navigate 后 click/fill/publish 正常执行(审批流在 V9 侧, 客户端仅执行)
真机: 用户在自家网络跑 agent_client.py --platform xiaohongshu, 未登录/风控场景相同逻辑。
"""
import json
import os
import sys
import tempfile
import threading
import time
import http.server
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ws_client import AgentWsClient
from browser import BrowserSession
from actions import Actions
from platforms import load_platforms

WS_PORT = 5931
FIX_PORT = 5932

PAGES = {
    "/verify": """<!doctype html><html><body><div>安全限制 IP存在风险，请切换可靠网络环境后重试 300012</div></body></html>""",
    "/pub": """<!doctype html><html><body>
      <input id="title" placeholder="标题"><textarea id="content" placeholder="正文"></textarea>
      <button id="pub">发布</button></body></html>""",
    "/shop": """<!doctype html><html><body>
      <section class="note-item"><a href="/explore/x"><div class="title">考研数学基础班笔记 2026</div></a></section>
      <section class="note-item"><a href="/explore/y"><div class="title">英语一高频词汇整理 3000词</div></a></section>
      </body></html>""",
}


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = (PAGES.get(self.path) or "<html><body>ok</body></html>").encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def make_mock_v9(port, got):
    from websockets.sync.server import serve

    seq = [
        ("c0", "navigate", {"platform": "shop", "url": "http://127.0.0.1:%d/pub" % FIX_PORT}),
        ("c1", "search", {"platform": "nologin_shop", "query": "考研复习"}),
        ("c2", "search", {"platform": "verify_shop", "query": "考研复习"}),
        ("c3", "fill", {"platform": "shop", "selector": "#title", "text": "测试笔记标题"}),
        ("c4", "click", {"platform": "shop", "selector": "#pub"}),
        ("c5", "publish", {"platform": "shop", "title": "考研数学测试", "content": "这是测试正文", "tags": ["考研"]}),
    ]
    state = {"i": 0}

    def handler(ws):
        for raw in ws:
            msg = json.loads(raw)
            got.append(msg)
            mt = msg.get("type")
            if mt == "hello":
                _cid, _act, _par = seq[0]
                ws.send(json.dumps({"type": "exec", "cmd_id": _cid, "action": _act, "params": _par}))
                state["i"] = 1
            elif mt == "result" and state["i"] < len(seq):
                _cid, _act, _par = seq[state["i"]]
                ws.send(json.dumps({"type": "exec", "cmd_id": _cid, "action": _act, "params": _par}))
                state["i"] += 1

    srv = serve(handler, "127.0.0.1", port)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main():
    ok = True
    def check(cond, name):
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + name, flush=True)
        if not cond:
            ok = False

    fix = http.server.ThreadingHTTPServer(("127.0.0.1", FIX_PORT), H)
    threading.Thread(target=fix.serve_forever, daemon=True).start()

    got = []
    make_mock_v9(WS_PORT, got)

    tmp = tempfile.mkdtemp(prefix="agent_client_s45_")
    yaml_path = os.path.join(tmp, "platforms.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(
            "nologin_shop:\n"
            "  search_url: \"http://127.0.0.1:%d/shop?keyword={q}\"\n"
            "  card_selector: \"section.note-item\"\n"
            "  login_cookie: [\"NEVER_PRESENT_COOKIE\"]\n"
            "verify_shop:\n"
            "  search_url: \"http://127.0.0.1:%d/verify\"\n"
            "  card_selector: \"section.note-item\"\n"
            "shop:\n"
            "  search_url: \"http://127.0.0.1:%d/shop?keyword={q}\"\n"
            "  card_selector: \"section.note-item\"\n"
            "  publish: {title: \"#title\", content: \"#content\", submit: \"#pub\"}\n"
            % (FIX_PORT, FIX_PORT, FIX_PORT)
        )
    platforms = load_platforms(yaml_path)

    browser = BrowserSession(os.path.join(tmp, "profile"), headless=True).start()
    actions = Actions(browser, platforms)

    def execute(action, params):
        platform = str(params.get("platform") or "xiaohongshu")
        cfg = platforms.get(platform, {})
        page = browser.page_for(platform, cfg)
        if action == "navigate":
            data = actions.navigate(page, params)
        elif action == "search":
            data = actions.search(page, platform, params)
        elif action == "fill":
            data = actions.fill(page, platform, params)
        elif action == "click":
            data = actions.click(page, platform, params)
        elif action == "publish":
            data = actions.publish(page, platform, params)
        else:
            data = {"error": "unknown"}
        data = data or {}
        if "error" in data and not data.get("verify_required"):
            v = browser.detect_verify(page, cfg)
            if v:
                data = {"error": "检测到风控验证(%s)" % v, "verify_required": True, "platform": platform}
        return data

    client = AgentWsClient("ws://127.0.0.1:%d" % WS_PORT, "t-user-45", tag="python-client")
    client.start()

    results = []
    deadline = time.time() + 60
    while time.time() < deadline and len(results) < 6:
        item = client.next_exec(timeout=1.0)
        if item:
            cmd_id, action, params = item
            data = execute(action, params)
            ok_ = "error" not in data
            if data.get("verify_required"):
                client.send_verify_required(str(data.get("platform") or ""))
            elif data.get("login_required"):
                client.send_login_status(str(data.get("platform") or ""), False)
            client.send_result(cmd_id, ok_, data)
            results.append({"cmd_id": cmd_id, "action": action, "data": data, "ok": ok_})

    by_cmd = {r["cmd_id"]: r for r in results}

    r1 = by_cmd.get("c1", {}).get("data") or {}
    check(r1.get("login_required") is True and "未登录" in r1.get("error", ""),
          "未登录平台 search → login_required(提示扫码)")

    r2 = by_cmd.get("c2", {}).get("data") or {}
    check(r2.get("verify_required") is True, "风控页 search → verify_required")
    vreq = [m for m in got if m.get("type") == "verify_required"]
    check(len(vreq) == 1 and vreq[0].get("platform") == "verify_shop",
          "客户端已发 verify_required 消息(%s)" % (vreq[0].get("platform") if vreq else "无"))

    r3 = by_cmd.get("c3", {}).get("data") or {}
    check(r3.get("filled") is True, "fill 真实填入 input")
    r4 = by_cmd.get("c4", {}).get("data") or {}
    check(r4.get("clicked") is True, "click 真实点击按钮")
    r5 = by_cmd.get("c5", {}).get("data") or {}
    check(r5.get("title_filled") and r5.get("content_filled") and r5.get("publish_clicked"),
          "publish 填表+点发布(title=%s content=%s clicked=%s)" % (
              r5.get("title_filled"), r5.get("content_filled"), r5.get("publish_clicked")))

    login_st = [m for m in got if m.get("type") == "login_status"]
    check(any(m.get("platform") == "nologin_shop" and m.get("logged_in") is False for m in login_st),
          "login_status False 已上报(未登录平台)")

    client.stop()
    browser.close()
    fix.shutdown()
    print("== 结果: %s ==" % ("ALL PASS" if ok else "SOME FAILED"), flush=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
