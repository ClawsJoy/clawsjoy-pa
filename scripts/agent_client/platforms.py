# -*- coding: utf-8 -*-
"""平台配置加载(config/platforms.yaml) — 加平台=加配置, 不改代码。"""

import logging
from pathlib import Path

log = logging.getLogger("agent_client.platforms")

# 内置默认(platforms.yaml 可覆盖/新增)
_DEFAULT = {
    # 2026-09-10 专家页面: V9/PA 与 DeepSeek 专家交互（提问 + 取回答；识图走 upload）
    "deepseek": {
        "login_url": "https://chat.deepseek.com",
        "session_url_tpl": "https://chat.deepseek.com/a/chat/s/{sid}",
        # ✅ 实测校准(2026-09-10, 登录态, 会话 6054f376-...; 老板本人登录后由 PA 只读探测)
        # 探测事实: need_login=false; title="DS chat - DeepSeek"; 页面存在 turnstile 节点(未触碰)。
        # 注意: 未登录访问 /a/chat/s/<sid> 会被重定向到 sign_in, 聊天区根本不渲染 ——
        #       故 need_login_markers 是硬前置检查, 未登录时不要尝试任何 selector。
        "input_selector": "textarea[placeholder*='发送消息']",  # 实测 count=1 ✅
        # (旧写法 textarea#chat-input 实测 count=0, 已废弃)
        # ✅ 三轮真实对话联调验证通过(2026-09-10)。
        # ⚠️ 踩过的坑(务必保留): 同容器 _020ab5b 里有【两个】34×34 按钮, 长得几乎一样:
        #    x=980 的胶囊键  cls 含 iconLabelPrimary + --capsule  → 【不是】发送键
        #    x=1024 的圆形键 cls 含 --primary --filled --circle    → 【才是】发送键
        #    只按"唯一/尺寸/右下角"选会选错; 必须带 --circle 或 --filled 特征。
        #    误点 x=980 那次: 消息没发出去(textarea 未清空), 且无法排除副作用。
        # ⚠️ 仍脆弱: _020ab5b 是 CSS Modules 哈希类名, 随前端构建版本变; 失效表现 count!=1。
        "submit_selector": "div._020ab5b div[class*='ds-button--circle']",
        "submit_selector_fallbacks": [
            "div._020ab5b div[class*='ds-button--filled']",
            "div.ds-button--circle.ds-button--primary",
        ],
        # 发送成功的确定性判据(实测吻合): textarea value 长度归 0 且 .ds-markdown 数量 +1
        "send_success_check": {"textarea_cleared": True, "markdown_delta": 1},
        # ⚠️⚠️ 发送【前置】条件（2026-09-10 事故驱动，硬性要求）
        # 事故: 第4轮联调发到了【新建线程】而不是指定会话。根因是流程里少了"确认目标线程"这一步;
        #       客户端重启后页面为 about:blank, 直接 navigate 基础地址就会新建会话。
        # 铁律: 往已有会话发消息【必须先确认 location.href 命中目标会话 URL, 不匹配就先导航再复查,
        #       复查仍不通过则【不发】】。宁可不发, 也不能发错地方 —— 代理发错场合 = 代表老板说错话。
        "send_precondition": {
            "must_match_url": "https://chat.deepseek.com/a/chat/s/{sid}",
            "on_mismatch": "navigate_then_recheck",
            "abort_if_unverified": True,
            # 老板指定线程(2026-09-16 批195 变更): 旧 sid 6054f376-beb6-4790-8107-391b6b692145 属**另一个账号**, 已作废;
            # 新 sid 来自老板**日常 Chrome 的 DS 账号**。变更必须三份副本同步(live/dev/桌面),
            # 否则会出现「改了一份、另一份照旧发到旧线程」= 代表老板说错话(见 113 深化: 同一标识只能有一个来源)。
            # 原注(2026-09-10): PA 与 @DS Chat 协作一律在这里进行, 不得另起新线程。
            # 硬门默认用它: 不传 expect_sid 时也按这个 sid 校验。
            "expect_sid": "49ad7381-f83b-4745-af63-0ce63c7f2ed1",
            "note": "sid 来自目标会话链接; 允许尾部查询串/锚点差异, 但 pathname 必须完全一致",
        },
        # 老板指定的唯一协作线程(结构性配置, 不靠临时传参)
        "designated_session": {
            "sid": "49ad7381-f83b-4745-af63-0ce63c7f2ed1",
            "url": "https://chat.deepseek.com/a/chat/s/49ad7381-f83b-4745-af63-0ce63c7f2ed1",
            "title": "DS chat",
            "note": "PA 与 @DS Chat 的协作线程(2026-09-16 批195 起 = 老板日常 Chrome 的 DS 账号); 开工前先 navigate 到此 URL 并校验 pathname; 严禁另起新线程",
        },
        # 老板对 @DS Chat 的能力定位(用于 PA 决定何时 @ 它, 而不是自己硬扛)
        "capabilities": ["智能搜索", "图文识别", "推理", "分析"],
        # 批209 · @DS Chat 双通道协作协议：**与 DSH 线同一套规则与工作流**（金库
        #   工作区/SOPs/@DS_CHAT_双通道协作SOP_20260916.md）；两线差异**只在实现与线程**：
        #   · 实现：DSH = CDP（browser_runtime）；PA = agent_client（本地客户端，后续可切 CDP 复用同一实例）
        #   · 线程：**各自单独**（PA 必须**自己新开**，不得占用 DSH 的 f8e586e2 线程）
        "protocol": {
            "sop": "工作区/SOPs/@DS_CHAT_双通道协作SOP_20260916.md",  # 两线共用，禁止各自演化
            "identity": "PA（老板的私人助理）",  # ① 身份
            "request_fields": ["身份", "目的", "目标", "问题", "请求"],  # 每次请求五要素，缺一不发
            "request_kinds": ["分析", "建议", "审核"],  # ⑤ 请求要指明哪一种
            "charter_on_new_thread": [  # 新线程首帖必带的 9 条行为准则（写进给 DS 的准则里）
                "角色：只给我的分析/建议/审核意见；不做本机操作、不写文件",
                "不能主动找我：联系一律由我发起；遇到困难或重要决策拿不准，请告知老板",
                "结论先行：分条、编号、可复核（判据/命令/数字）",
                "区分三态：事实（有出处）/推断（依据+不确定度）/建议（代价），不许把推断写成事实",
                "给结论必须附反例（与我们的正例+反例纪律一致）",
                "不确定就说不确定，宁可标「未观察到」",
                "不客套、不复述我的长文（省上下文）；长答分段+编号，每段自带一行背景",
                "每次回复末尾给 1-3 条「下一步建议」",
                "范围：本线程主题；超出范围请点明，不要硬答",
            ],
            "capabilities_free": ["识别图片", "深度思考", "智能搜索"],  # 请求里要明说用哪一项
            "escalation": {
                "on_difficulty": "说明卡点并建议老板如何补（读不全/拿不到材料/超出能力）",
                "on_major_decision": "标注「需老板拍板」+ 2-3 个选项与代价",
                "relay": "DS → 老板 → PA/DSH（DS 无主动能力，不假设它会来找）",
            },
            "upload": {
                "supported": True,  # 实测（DSH 线 2026-09-16）：DS 页面 accept 含 .md/.txt/.pdf/图片等
                "via": "agent_client 的 upload 动作；接线后亦可走 CDP set_input_files",
                "use_for": "金库 收件箱/ 工作区/ 里已落盘的文档（**替代长粘贴**）",
                "success_judges": ["会话里出现文件名", "正文引用该文件名", "输入框清空"],
                "version_note": "上传是那一刻的快照；正文必须写「文件版本/时间戳 + 关键结论 3 行」",
            },
            "handoff_file": "聊天区/复盘/@DS_CHAT_PA通道_上下文交接.md",  # 超限交接件（PA 版）
            "own_thread_required": True,  # 线程独立：PA 自己新开，不与 DSH 共用
        },
        # ⚠️ 发送【后置】验收（缺一不可）
        # 只验 textarea_cleared + markdown_delta 还不够: 那只证明"发出去了", 不证明"发对地方"。
        # 必须再确认消息出现在【目标线程】的消息列表里, 否则视为投递失败。
        "send_postcheck": [
            "textarea_cleared",  # 发送成功会清空输入框
            "markdown_delta>=1",  # 产生新回复块
            "target_thread_contains_sent_text",  # 关键: 消息必须出现在目标线程中
        ],
        "reply_selector": ".ds-markdown",  # 实测 count=1 ✅
        # 回复容器注意: 多轮对话后 .ds-markdown 会有 N 个(每轮 assistant 一个), 取【最后一个】才是新回答。
        "reply_pick": "last",
        "image_input": "input[type=file][accept*='image']",
        "login_cookie": ["ds_session_id", "session_id"],
        "need_login_markers": ["sign_in", "/login"],  # URL 命中即判定未登录
        "has_turnstile_when_ok": True,  # 登录后页面仍有 turnstile 节点(疑似惰性), 不代表需要人工校验
        "selectors_verified": True,  # 输入框/回复已实测; 发送按钮唯一但依赖哈希类名, 见上
        "verified_at": "2026-09-10",
    },
    "xiaohongshu": {
        "login_url": "https://www.xiaohongshu.com",
        "search_url": "https://www.xiaohongshu.com/search_result?keyword={q}",
        "card_selector": "section.note-item, .note-item",
        "link_selector": "a[href*='/explore/'], a",
        "title_selector": ".title, a[href*='/explore/'] .title",
        "login_cookie": ["web_session", "galaxy_creator_session_id"],
        # 注: 小红书创作者中心发布页为图文/视频双 tab, video_input 待页面实测补充
        "publish": {
            "title": "input[placeholder*='标题'], .title-input, .title input",
            "content": "textarea[placeholder*='正文'], .note-editor, [contenteditable='true']",
            "submit": "button:has-text('发布')",
        },
    },
    "douyin": {
        "login_url": "https://www.douyin.com",
        "search_url": "https://www.douyin.com/search/{q}",
        # 2026-09-05 搜索页真机校准(session douyin_cal, 浏览器实测):
        #   - 旧 card_selector [data-e2e='search-result-item'] 已失效(页面无此 e2e 标记)。
        #   - 实际卡片容器 = .search-result-card(每卡内含整卡链接 a[href*="/video/"] 与封面 .videoImage)。
        #   - 卡片内文本行序(innerText): 时长 / 点赞数 / 标题(+话题) / @作者 / 相对时间;
        #     合集卡首行是「合集」, 提取时首行需偏移(dur=第2行, likes=第3行)。
        #   - 滚动加载: 页面用容器内滚动(外层 .jscIDlNp* 类, scrollHeight>clientHeight),
        #     把该容器 scrollTop 设到底并等 ~4s, .search-result-card 从 ~27 增长到 47+。
        #   - 字段级提取建议用 browser_local evaluate(只读 JS) 而非 extract,
        #     稳定模板见 ComputerUseSOPs/douyin-search-cu-sop.md。
        "card_selector": ".search-result-card",
        "link_selector": "a[href*='/video/']",
        "login_cookie": ["sessionid", "sid_tt"],
        # 2026-08-26 图文发布校准(Windows client 实测):
        # 入口 creator.douyin.com/creator-micro/content/upload?type=image, 传图后跳 post/image?type=new
        "publish": {
            "url": "https://creator.douyin.com/creator-micro/content/post/image?default-tab=3&enter_from=publish_page&media_type=image&type=new",
            "image_input": "input[type=file][accept*='image/']",
            "title": "input[placeholder='添加作品标题']",
            "content": "div[contenteditable='true']",
            "submit": "button[type='submit']",
            "save_draft": "button:has-text('暂存')",
            # 2026-08-26 复盘补全(post/image 图文页实测):
            "cover": "text=选择一张图片作为封面",  # 封面设置(默认第一张图)
            "add_image": "text=继续添加",  # 继续加图
            "clear_upload": "text=清空并重新上传",  # 清空重传
            "topic_input": "div[contenteditable='true']",  # 正文内 #话题
            "visibility": "text=公开",  # 谁可以看(默认公开)
            "timing": "text=立即发布",  # 发布时间(默认立即)
            "publish_btn": "button[type='submit']",  # 正式发布(需审批门)
            # 可选: 音乐/标签/位置/热点/合集/自主声明(默认不选)
            "optional": ["选择音乐", "添加标签", "位置", "关联热点", "添加合集", "自主声明"],
            # 2026-08-26 复盘补全(post/image 图文页实测):
            "cover": "text=选择一张图片作为封面",  # 封面设置(默认第一张图)
            "add_image": "text=继续添加",  # 继续加图
            "clear_upload": "text=清空并重新上传",  # 清空重传
            "topic_input": "div[contenteditable='true']",  # 正文内 #话题
            "visibility": "text=公开",  # 谁可以看(默认公开)
            "timing": "text=立即发布",  # 发布时间(默认立即)
            "publish_btn": "button[type='submit']",  # 正式发布(需审批门)
            # 可选: 音乐/标签/位置/热点/合集/自主声明(默认不选)
            "optional": ["选择音乐", "添加标签", "位置", "关联热点", "添加合集", "自主声明"],
        },
    },
    "bilibili": {
        "login_url": "https://www.bilibili.com",
        "search_url": "https://search.bilibili.com/all?keyword={q}",
        "card_selector": ".bili-video-card, .video-card",
        "login_cookie": ["SESSDATA"],
        "publish": {
            "url": "https://member.bilibili.com/platform/upload/video/frame",
            "video_input": "input[type=file][accept*='video/'], input[type=file][accept*='.mp4'], input[type=file][accept*='.mov'], input[type=file][accept*='.flv'], input[type=file][accept*='.m4v'], input[type=file]",
            "cover_input": "input[type=file][accept*='.jpg'], input[type=file][accept*='.jpeg'], input[type=file][accept*='.png']",
            "title": "input[placeholder*='标题'], input[placeholder*='填写视频标题'], .title input",
            "content": "[contenteditable='true'], textarea[placeholder*='简介'], .desc textarea",
            "submit": "button:has-text('发布'), button:has-text('立即投稿')",
            "tag_list": "[class*='tag-list']",
            "tag_item": "[class*='tag-list'] >> text=%s",
            "zone_trigger": "text=%s",
            "cover_open": "text=添加封面",
        },
    },
    "zhihu": {
        "login_url": "https://www.zhihu.com",
        "search_url": "https://www.zhihu.com/search?q={q}&type=content",
        "card_selector": ".SearchResult-Card, .Card",
        "login_cookie": ["z_c0"],
        "publish": {
            "title": "textarea[placeholder*='请输入标题'], input[placeholder*='标题']",
            "content": "[contenteditable='true'], .DraftEditor, .public-DraftEditor-content",
            "submit": "button:has-text('发布')",
            "cover_input": "input[type=file][accept*='.jpeg'], input[type=file][accept*='.jpg'], input[type=file][accept*='.png']",
            "image_input": "input[type=file][accept*='image/']",
            "topic_input": "input[placeholder*='话题'], input[placeholder*='添加话题'], .TopicEditor input, [class*=topic] input",
            "topic_label": "添加话题",
            "topic_option": "[class*=option], [class*=suggest], [class*=Dropdown] li, [class*=Menu] li",
            "declaration": "input[type=checkbox][class*=declare], [class*=声明] input[type=checkbox], label:has-text('声明') input",
        },
    },
    "weibo": {
        "login_url": "https://weibo.com",
        "search_url": "https://s.weibo.com/weibo?q={q}",
        "card_selector": ".card-wrap",
        "login_cookie": ["SUB", "SUBP"],
    },
    "youtube": {
        "login_url": "https://www.youtube.com",
        "search_url": "https://www.youtube.com/results?search_query={q}",
        "card_selector": "ytd-video-renderer",
        "link_selector": "a#video-title",
        "title_selector": "#video-title",
        "login_cookie": ["SID", "HSID", "SSID"],
        "search_requires_login": False,  # YouTube 搜索无需登录(匿名可用)
        "publish": {
            "title": "",  # YouTube 发布复杂(Studio), 后续实现
            "content": "",
            "submit": "",
        },
    },
}


def load_platforms(path=None):
    if path is None:
        path = Path(__file__).parent / "config" / "platforms.yaml"
    cfg = {k: dict(v) for k, v in _DEFAULT.items()}
    try:
        import yaml

        if Path(path).exists():
            data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
            for k, v in data.items():
                if isinstance(v, dict):
                    cfg[k] = {**cfg.get(k, {}), **v}
    except Exception as e:
        log.warning("platforms.yaml 加载失败(用内置默认): %s", str(e)[:120])
    return cfg


def infer_platform(url):
    """按 URL 推断平台: zhuanlan.zhihu.com/zhihu.com → zhihu; xiaohongshu.com → xiaohongshu 等。
    用于无 platform 参数的动作(click/fill/extract)路由到当前页面所属平台。"""
    u = (url or "").lower()
    pairs = [
        ("xiaohongshu.com", "xiaohongshu"),
        ("xhslink.com", "xiaohongshu"),
        ("douyin.com", "douyin"),
        ("iesdouyin.com", "douyin"),
        ("bilibili.com", "bilibili"),
        ("b23.tv", "bilibili"),
        ("zhihu.com", "zhihu"),
        ("weibo.com", "weibo"),
        ("chat.deepseek.com", "deepseek"),
        ("deepseek.com", "deepseek"),
        ("youtube.com", "youtube"),
    ]
    for host, plat in pairs:
        if host in u:
            return plat
    return ""
