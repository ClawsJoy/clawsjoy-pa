# -*- coding: utf-8 -*-
"""agent_client 集成验证: WS 协议往返 + playwright 动作 + 卡片提取

沙箱 IP 被小红书风控(300012)无法直连真站, 用本地 fixture 页面模拟
小红书搜索页 DOM(section.note-item > a[href*='/explore/'] + .title)验证提取逻辑。
真机验证: 用户在自家网络跑 agent_client.py --platform xiaohongshu 扫码后执行 search。
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

WS_PORT = 5921
FIX_PORT = 5922

FIX_HTML = """<!doctype html><html><head><title>考研复习 - 小红书搜索(fixture)</title></head>
<body>
<div class="search-container">
  <section class="note-item">
    <a href="/explore/考研数学基础班笔记"><div class="title">考研数学基础班笔记 2026</div></a>
  </section>
  <section class="note-item">
    <a href="/explore/英语一高频词汇整理"><div class="title">英语一高频词汇整理 3000词</div></a>
  </section>
  <section class="note-item">
    <a href="/explore/政治肖四背诵版"><div class="title">政治肖四背诵版 精简提纲</div></a>
  </section>
  <section class="note-item">
    <a href="/explore/专业课408真题解析"><div class="title">专业课408真题解析 十年</div></a>
  </section>
  <section class="note-item">
    <a href="/explore/考研时间表规划"><div class="title">考研时间表规划 12个月</div></a>
  </section>
</div>
<div style="height:3000px"></div>
</body></html>"""


class FixHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = FIX_HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def make_mock_v9(port, got):
    from websockets.sync.server import serve

    def handler(ws):
        for raw in ws:
            msg = json.loads(raw)
            got.append(msg)
            mt = msg.get("type")
            if mt == "hello":
                ws.send(json.dumps({"type": "exec", "cmd_id": "c1",
                                    "action": "search",
                                    "params": {"platform": "xiaohongshu", "query": "考研复习"}}))
            elif mt == "result":
                ws.send(json.dumps({"type": "exec", "cmd_id": "c2",
                                    "action": "extract", "params": {}}))

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

    fix = http.server.ThreadingHTTPServer(("127.0.0.1", FIX_PORT), FixHandler)
    threading.Thread(target=fix.serve_forever, daemon=True).start()

    got = []
    make_mock_v9(WS_PORT, got)

    tmp = tempfile.mkdtemp(prefix="agent_client_test_")
    yaml_path = os.path.join(tmp, "platforms.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write("xiaohongshu:\n  search_url: \"http://127.0.0.1:%d/search_result?keyword={q}\"\n  login_cookie: []\n" % FIX_PORT)
    platforms = load_platforms(yaml_path)

    browser = BrowserSession(os.path.join(tmp, "profile"), headless=True).start()
    actions = Actions(browser, platforms)

    def execute(action, params):
        platform = str(params.get("platform") or "xiaohongshu")
        page = browser.page_for(platform, platforms.get(platform, {}))
        if action == "search":
            return actions.search(page, platform, params)
        if action == "extract":
            return actions.extract(page, params)
        return {"error": "unknown"}

    client = AgentWsClient("ws://127.0.0.1:%d" % WS_PORT, "test-user-1", tag="python-client")
    client.start()

    results_ = []
    deadline = time.time() + 30
    while time.time() < deadline and len(results_) < 2:
        item = client.next_exec(timeout=1.0)
        if item:
            cmd_id, action, params = item
            data = execute(action, params)
            ok_ = "error" not in data
            client.send_result(cmd_id, ok_, data)
            results_.append({"cmd_id": cmd_id, "action": action, "data": data, "ok": ok_})
        if len(results_) < 2:
            time.sleep(0.1)

    hellos = [m for m in got if m.get("type") == "hello"]
    check(len(hellos) == 1 and hellos[0].get("user_id") == "test-user-1", "WS hello 注册 user_id")
    check(len(results_) >= 2, "收到 2 个 exec 并回传 result(实际 %d)" % len(results_))

    r1 = results_[0]["data"] if results_ else {}
    cards = r1.get("results") or []
    check(len(cards) == 5, "search 提取 5 张卡片(实际 %d)" % len(cards))
    if cards:
        check(cards[0].get("title", "").startswith("考研数学基础班"), "卡片1 标题正确: %s" % cards[0].get("title"))
        check("/explore/" in cards[0].get("url", ""), "卡片1 链接含 /explore/: %s" % cards[0].get("url"))

    r2 = results_[1]["data"] if len(results_) > 1 else {}
    content = r2.get("content") or ""
    check("考研数学基础班笔记" in content, "extract 返回页面正文(含卡片标题)")

    page = browser.page_for("fixture", {"login_url": ""})
    nav = actions.navigate(page, {"url": "http://127.0.0.1:%d/search_result" % FIX_PORT})
    check(nav.get("title", "").startswith("考研复习"), "navigate 返回标题")
    ext = actions.extract(page, {})
    check("考研时间表规划" in ext.get("content", ""), "extract 原生 main world 取到全文")
    sc = actions.scroll(page, {"amount": 600})
    check((sc.get("scrollY") or 0) > 0, "scroll 生效 scrollY=%s" % sc.get("scrollY"))

    client.stop()
    browser.close()
    fix.shutdown()
    print("== 结果: %s ==" % ("ALL PASS" if ok else "SOME FAILED"), flush=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()