# -*- coding: utf-8 -*-
"""browser_local 工具插件 — 本地浏览器操作(对齐 Manus 本地浏览器能力)

P1: navigate / extract / screenshot / scroll(只读调研)
P2+: click / fill / search(交互)
P3+: publish(发布, 需审批)

与 playwright_browser 区别: 操作用户真实本地浏览器(复用登录态/IP), 突破登录墙。
依赖: core.lib.v8.browser_local.execute(WS 连接)。
"""
import threading

from core.tools.base import ToolPlugin

# (2026-09-07) 同 URL navigate 熔断: 飞书长文档调研一次任务对同一 wiki 导航 5+ 次、
# 每轮把整页上下文重新注入 → 50 万 token 烧穿仍未落盘。同一 (user, url) 3 分钟内
# navigate ≥3 次 → 拒绝并提示复用已打开页面/基于已有内容直接落盘(web_fetch_guard 同源语义)。
_NAV_HIST = {}  # key=(user_id, url) -> {"n": count, "ts": last}
_NAV_WINDOW = 180
_NAV_LIMIT = 3
_NAV_LOCK = threading.Lock()


def _navigate_over_limit(user_id, url):
    """同 URL navigate 是否超限(3 分钟窗内 ≥3 次)。超限返回提示, 否则返回 ''。"""
    import time as _t_nav

    key = (str(user_id or ""), str(url or "").strip())
    now = _t_nav.time()
    with _NAV_LOCK:
        e = _NAV_HIST.get(key)
        if e is None or now - e["ts"] > _NAV_WINDOW:
            e = {"n": 0, "ts": now}
            _NAV_HIST[key] = e
        e["n"] += 1
        e["ts"] = now
        for k in list(_NAV_HIST):
            if now - _NAV_HIST[k]["ts"] > _NAV_WINDOW:
                _NAV_HIST.pop(k, None)
        if e["n"] >= _NAV_LIMIT:
            return (
                f"同一 URL 已 navigate {e['n']} 次(3 分钟上限 {_NAV_LIMIT})。页面已打开/内容应已获取——"
                "停止重复导航, 基于当前页面 extract/evaluate/screenshot 或直接落盘已有内容。"
            )
    return ""


BROWSER_LOCAL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "browser_local",
        "description": (
            "操作本地浏览器(用户真实浏览器, 复用登录态)。用于需要登录/风控的调研, 如小红书/抖音/B站/知乎。"
            "动作: navigate(打开URL) / extract(提取正文) / screenshot(截图) / scroll(滚动加载) / "
            "click(点击) / fill(填表) / search(搜索) / upload(上传文件, kind=cover/image/video/document)。仅限白名单平台域。"
            "本地系统动作(无需浏览器页面): open_document(默认程序打开文档, 参数 path; 仅 Desktop/Documents 白名单目录 + pptx/docx/xlsx/pdf) / close_wps(关闭 wps/wpp/et, 释放文件锁) / lingxi_mcp(探测灵犀持久化配置) / "
            "computer_use(桌面级白名单动作, 参数 op; 只读 list_windows/list_apps/get_window/get_window_state/get_screenshot 默认放行, 写动作需 allow_write=true 且经治理门)。"
        ),
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "navigate",
                        "extract",
                        "screenshot",
                        "scroll",
                        "click",
                        "fill",
                        "search",
                        "upload",
                        "frames",
                        "evaluate",
                        "observe_start",
                        "observe_stop",
                        "publish",
                        "monitor_start",
                        "monitor_stop",
                        "reply_enqueue",
                        "reply_approve",
                        "open_document",
                        "close_wps",
                        "lingxi_mcp",
                        "computer_use",
                    ],
                    "description": "操作动作",
                },
                "url": {"type": "string", "description": "目标 URL(navigate/search 需要)"},
                "viewport": {"type": "object", "description": "视口尺寸(可选, navigate 用): {width, height}, 用于多视口自测"},
                "selector": {"type": "string", "description": "CSS 选择器(click/fill/extract 需要)"},
                "path": {"type": "string", "description": "本地文档路径(open_document 需要; 仅白名单目录 + 文档扩展名)"},
                "frame": {
                    "type": "string",
                    "description": "iframe 定位(可选): CSS selector 或数字 index; 编辑区在 iframe 内时必填(B站投稿页等)",
                },
                "expr": {"type": "string", "description": "JS 表达式(evaluate, 返回 JSON 可序列化值; 弹层/复杂 DOM 提取用)"},
                "observe_id": {"type": "string", "description": "观察会话 ID(observe_stop 需要)"},
                "max_actions": {"type": "integer", "description": "观察动作日志上限(observe_start, 默认 200)"},
                "include_hidden": {"type": "boolean", "description": "extract 是否返回隐藏元素(下拉/弹层/选项列表)的属性和文本(发布设置调研用)"},
                "cover": {"type": "string", "description": "封面图路径(publish, 知乎文章封面)"},
                "text": {"type": "string", "description": "填写文本(fill 需要)"},
                "query": {"type": "string", "description": "搜索词(search 需要)"},
                "direction": {"type": "string", "enum": ["down", "up"], "description": "滚动方向(scroll)"},
                "amount": {"type": "integer", "description": "滚动像素量(scroll, 默认 800)"},
                "full_page": {"type": "boolean", "description": "整页截图(screenshot)"},
                "wait_ms": {"type": "integer", "description": "操作前等待毫秒"},
                "platform": {
                    "type": "string",
                    "enum": ["xiaohongshu", "douyin", "bilibili", "zhihu", "weibo", "youtube", "deepseek"],
                    "description": "发布/监控平台(publish/monitor_start); deepseek=@专家通道",
                },
                "title": {"type": "string", "description": "笔记标题(publish)"},
                "content": {"type": "string", "description": "笔记正文(publish)"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "话题标签列表(publish)"},
                "images": {"type": "array", "items": {"type": "string"}, "description": "配图路径列表(可选, publish)"},
                "kind": {
                    "type": "string",
                    "enum": ["cover", "image", "video", "document"],
                    "description": "上传文件类型(upload)",
                },
                "files": {"type": "array", "items": {"type": "string"}, "description": "上传文件路径列表(upload)"},
                "file": {"type": "string", "description": "单文件路径(upload, 与 files 二选一)"},
                "target": {"type": "string", "description": "监控目标(话题/关键词/页面, monitor_start)"},
                "interval": {"type": "integer", "description": "监控间隔秒(monitor_start, 默认 60)"},
                "item": {"type": "object", "description": "待回复内容项(reply_enqueue)"},
                "suggested_reply": {"type": "string", "description": "回复建议文本(reply_enqueue)"},
                "reply_id": {"type": "string", "description": "回复项 ID(reply_approve)"},
                "approve": {"type": "boolean", "description": "审批通过/拒绝(reply_approve)"},
                "reply_text": {"type": "string", "description": "自定义回复文本(可选, reply_approve)"},
            },
            "required": ["action"],
        },
    },
}


# 单一事实源: 运行时白名单从 schema enum 派生。
# (2026-09-10 事故) 新增 open_document/close_wps/lingxi_mcp 时只改了 schema enum,
# 漏改 execute() 内的手写 valid 集合 → 动作过得了 schema 校验、死在运行时校验
# ("unsupported action")。派生后两处不可能再漂移。
def _schema_actions():
    try:
        return frozenset(BROWSER_LOCAL_SCHEMA["function"]["parameters"]["properties"]["action"]["enum"])
    except Exception:
        return frozenset()


VALID_ACTIONS = _schema_actions()

# 本地系统动作子集(不依赖浏览器页面, 由 agent_client 白名单执行)。
# 与 scripts/agent_client/local_actions.LOCAL_ACTIONS 必须一致 —— 由单测锁死
# (tests/unit/test_local_actions.py::test_client_local_actions_accepted_by_gateway)。
LOCAL_SYSTEM_ACTIONS = frozenset({"open_document", "close_wps", "lingxi_mcp", "computer_use"})


class BrowserLocalPlugin(ToolPlugin):
    name = "browser_local"
    quota = 20
    schema = BROWSER_LOCAL_SCHEMA

    def execute(self, args: dict, ctx) -> dict:
        from core.lib.v8 import browser_local

        action = (args or {}).get("action", "").strip()
        valid = VALID_ACTIONS  # 由 schema enum 派生, 勿手写(见模块顶部注释)
        if action not in valid:
            return {"success": False, "error": "unsupported action: %r, supported: %s" % (action, sorted(valid))}
        user_id = getattr(ctx, "user_id", "") or ""
        session_id = getattr(ctx, "session_id", "") or ""
        # P4 运营动作直接转发(不走 WS 指令)
        if action == "monitor_start":
            return browser_local.monitor_start(
                user_id,
                str(args.get("platform", "")),
                str(args.get("target", "")),
                interval=int(args.get("interval", 60) or 60),
                url=str(args.get("url", "") or ""),
            )
        if action == "monitor_stop":
            return browser_local.monitor_stop(user_id, str(args.get("platform", "")), str(args.get("target", "")))
        if action == "reply_enqueue":
            return browser_local.enqueue_reply(
                user_id, args.get("item", {}) or {}, str(args.get("suggested_reply", "") or "")
            )
        if action == "reply_approve":
            return browser_local.approve_reply(
                user_id,
                str(args.get("reply_id", "")),
                bool(args.get("approve")),
                reply_text=str(args.get("reply_text", "") or ""),
            )
        # 域名白名单检查(navigate/search 必须校验)
        url = (args or {}).get("url", "") or ""
        if action in ("navigate", "search") and url:
            import urllib.parse as _up

            try:
                host = _up.urlparse(url).hostname or ""
            except Exception:
                host = ""
            if not browser_local._url_allowed(url):
                return {"success": False, "error": "域名/端口不在白名单: %s(仅限平台域 + 本地 5002/3080/5173)" % host}
        # (2026-09-07) 同 URL navigate 熔断(navigate 专属, 不误伤 evaluate 多样探测)
        if action == "navigate" and url:
            _nav_block = _navigate_over_limit(user_id, url)
            if _nav_block:
                return {"success": False, "error": _nav_block, "guard_denied": True}
        # 敏感操作硬拒绝(密码/支付)
        text = (args or {}).get("text", "") or ""
        if action == "fill" and any(k in text.lower() for k in ("password", "密码", "支付", "card", "卡号")):
            return {"success": False, "error": "禁止填写敏感信息(密码/支付/卡号)"}
        # evaluate 写保护(2026-08-29 现场确认): Agent 用 evaluate 执行含 .click()/.submit() 的 JS
        # 自动点击提交按钮(如"申请别名"弹窗) — 任务漂移根因(用户要查看状态, 却提交了申请)。
        # evaluate 是只读探测通道; 交互(点击/填表/提交)必须用 click/fill/search action(走审批/白名单)。
        if action == "evaluate":
            _expr_low = str((args or {}).get("expr") or (args or {}).get("expression") or "").lower()
            _write_markers = (
                ".click(",
                ".submit(",
                ".value=",
                "innerhtml",
                ".appendchild(",
                ".remove(",
                "localstorage.set",
                "form.submit",
            )
            # 写操作标记命中 → 直接拦
            _has_write = any(_mk in _expr_low for _mk in _write_markers)
            # 动态执行载体(eval/new Function/setTimeout)是无条件绕过载体 → 拦
            _bypass_markers = ("eval(", "new function(", "settimeout(", "setinterval(")
            _has_bypass = any(_mk in _expr_low for _mk in _bypass_markers)
            # function( 是函数探针的合法写法(function(){return document.title}) — 仅当函数体内含写操作时才拦,
            # 避免误伤只读探测(2026-08-29 审核: function( 太宽会拦正常探针)
            _has_fn_write = "function(" in _expr_low and _has_write
            if _has_write or _has_bypass or _has_fn_write:
                # 2026-08-30: 附具体替代示例(harness 风格 — 告诉 Agent 怎么改, 不只说不能做什么)
                return {
                    "success": False,
                    "error": "evaluate 是只读探测通道, 禁止包含写操作(click/submit/value赋值/appendChild/eval 动态执行等)。"
                    "页面交互请改用独立 action: click(selector='...') 点击 / fill(selector='...', text='...') 填表 "
                    "/ keyboard.type 输入 / upload 上传。不要在 evaluate 的 JS 里做交互。",
                }
        timeout = float((args or {}).get("timeout", 30))
        result = browser_local.execute(user_id, action, args or {}, timeout=timeout, session_id=session_id)
        return result
