# -*- coding: utf-8 -*-
"""PA 编队花名册（2026-09-10）

【战略背景】老板定调: V9 PA 的大方向是 ——
  能调度【市面上所有 agent】协作干活; 近期重点是扩展 PA 操作电脑的能力边界 + V9 的 PA 改造。
  重新定位: 私人主权 agent, 主要面向【用户老板本地部署】的情形。

【本模块解决什么】
  要"调度所有 agent", 先得知道: 能调度谁 / 怎么调度 / 它到底能做到什么、做不到什么 /
  有多脆 / 多贵。散落在对话和文档里的这些认识会丢, 必须变成结构化、可查询、可迭代的资产。

【核心判断（决定了架构）】
  市面上的 agent 绝大多数没有 API。所以 "调度所有 agent" 的通用底座不是 API 集成,
  而是 **computer use** —— 用浏览器/桌面操作去够那些没有接口的 agent。
  接入分级: L4 原生API/SDK > L3 MCP > L2 文档/应用级接口 > L1 UI自动化 > L0 不可接入

【纪律】
  每张卡片的 verified/boundary/fragility 必须有实测来源, 不写"应该可以"。
  未验证的一律标 unverified, 宁可保守也不虚报能力。
"""
import json
import os
import time

# 接入能力分级（与 computer-use 阶梯一致）
ACCESS_LADDER = ("L4", "L3", "L2", "L1", "L0")

_DEFAULT_CARDS = [
    {
        "id": "ds_chat",
        "name": "@DS Chat（DeepSeek）",
        "kind": "external_llm",
        "role": "思考型外脑",
        "capabilities": ["智能搜索", "图文识别", "推理", "分析"],
        "access": {
            "level": "L1",  # 浏览器 UI 操作(无公开 API)
            "channel": "agent_client 浏览器 + 指定线程",
            "entry": "https://chat.deepseek.com/a/chat/s/49ad7381-f83b-4745-af63-0ce63c7f2ed1",  # 批195(2026-09-16): 换账号+换线程（旧线程属另一账号，作废）
            "note": "必须锁定指定线程; 不得另起新线程(2026-09-10 事故)",
        },
        "verified": [
            "多轮对话连续性(三轮, 第3轮准确复述前两轮)",
            "图文识别: 上传 PNG 逐页视觉评审, 15 页全覆盖",
            "多图一次上传(3张/批)可行",
        ],
        "boundary": [
            "无官方 API; 只能靠浏览器 UI 操作",
            "发送/取回需人工可观察的页面, 无后台批量通道",
            "登录态可能被风控打断; 未登录会重定向 sign_in",
        ],
        "fragility": [
            "发送键选择器依赖 CSS Modules 哈希类名 _020ab5b, 前端发版即失效(count!=1)",
            "会话页是虚拟列表: .ds-markdown 计数不可靠; 窗口级 scroll 无效, 需容器内 scrollTop",
            "同 URL navigate 熔断(3分钟3次)会挡住合法的重新导航",
        ],
        "cost": "每轮约 30s~90s; 多图评审约 60s/批",
        "next": ["选择器改为运行时解析(抗发版)", "把'哪个线程'做成不可绕过的前置门"],
    },
    {
        "id": "lingxi",
        "name": "@灵犀（WPS-AI）",
        "kind": "mcp_service",
        "role": "PPT 排版专业工人",
        "capabilities": ["PPT 生成与排版", "文档内容级编辑", "模板/风格应用", "导出 PDF"],
        "access": {
            "level": "L3",
            "channel": "MCP http://127.0.0.1:3890 (Bearer token) + WPS 内插件",
            "entry": "GET /mcp/status 查活; 161 tools",
        },
        "verified": [
            "161 工具桥接可用(pluginAlive=true, toolCount=161)",
            "15 页 PPT 页级渲染与落盘",
            "桥随 WPS 启动自动注册(方案C补丁后, 无人点按钮)",
        ],
        "boundary": [
            "内容是文档级的: 必须有打开且已保存的 WPS 演示文档",
            "未保存的新建文档起不了桥",
            "桥不开时 toolCount=0(标记在线不等于可用)",
        ],
        "fragility": [
            "多实例共存会轮询导致 50% 失败(两个灵犀实例抢一个代理)",
            "WPS 重启后若补丁失效, 桥需人工点『打开灵犀AI』",
        ],
        "cost": "页级渲染约 10s~30s/页",
        "next": ["关闭 PDF 侧多余实例", "把桥体检并入 PA 常驻检查"],
    },
    {
        "id": "lingxi_local_api",
        "name": "灵犀本地服务（文件级通道）",
        "kind": "local_service",
        "role": "文件级版本与网页读取（不依赖桥）",
        "capabilities": ["文档快照/版本化", "文档回滚", "网页正文抓取"],
        "access": {
            "level": "L3",
            "channel": "POST /v9/pa/proxy（强制过 endpoint_guard）",
            "entry": "/doc-snapshot, /doc-restore, /fetch-web",
        },
        "verified": [
            "往返实测: 原稿 9e50eddd → 副本破坏 f30a6e92 → /doc-restore → 9e50eddd 字节级一致",
            "/fetch-web 返回干净正文+标题, 不需要浏览器",
            "与 MCP 桥无关: 桥不开也能用",
        ],
        "boundary": [
            "文件级, 不是内容级: 不能改'第3页标题'",
            "/doc-restore 覆盖写, 属破坏性端点, 需在场授权",
        ],
        "fragility": ["/kv/clear 等破坏性端点无参数即全清(2026-09-10 事故), 已加强制门"],
        "cost": "秒级",
        "next": ["把'改稿前先快照'固化进 PA 改稿标准流程"],
    },
    {
        "id": "blender",
        "name": "@Blender",
        "kind": "desktop_app",
        "role": "3D 专业工人",
        "capabilities": ["3D 建模", "CYCLES 渲染"],
        "access": {
            "level": "L2",
            "channel": "blender-mcp 1.9.1 + headless CLI",
            "entry": "addon 拒绝 background 模式, 需 GUI/xvfb/WSLg",
        },
        "verified": ["headless 建模 + CYCLES CPU 渲染可用", "OpenGL 需 DISPLAY=:0"],
        "boundary": ["addon 在 background 模式下拒绝工作, 自动化路径受限"],
        "fragility": ["WSLg 显示链路不稳"],
        "cost": "渲染分钟级",
        "next": ["验证 xvfb 下 addon 能否常驻"],
    },
    {
        "id": "local_vlm",
        "name": "本地视觉模型 qwen2.5vl:7b",
        "kind": "local_model",
        "role": "本地识图（离线兜底）",
        "capabilities": ["OCR(尚可)", "粗定位"],
        "access": {"level": "L3", "channel": "ollama http://127.0.0.1:11434", "entry": "POST /api/generate"},
        "verified": ["OCR 4/4 准确", "能粗定位选项卡位置"],
        "boundary": [
            "页面类型/风格判断差, 不能做裁判",
            "精确 UI 定位会幻觉(把选项卡名说成文档标题, 坐标越界)",
        ],
        "fragility": ["模型能力边界固定, 不适合当验收判官"],
        "cost": "本地, 免费, 秒级",
        "next": ["只用于 OCR 与粗筛; 精确识别交给 @DS Chat"],
    },
    {
        "id": "v9_agent",
        "name": "V9 Agent（本地主脑）",
        "kind": "agent_framework",
        "role": "PA 的执行手",
        "capabilities": ["文件/命令/检索", "browser_local", "沙箱执行", "任务规划"],
        "access": {"level": "L4", "channel": "POST /v9/agent/chat（本机进程内）", "entry": "带 tools 的完整 agent"},
        "verified": ["三轮浏览器联调", "多批图文评审调度", "守纪律: 前置校验不过就停手、不编造结论"],
        "boundary": ["写文件受审批门限制(会暂停等待确认)", "上下文有限, 长任务需 PA 拆批"],
        "fragility": [
            "跨会话记忆注入会带来与当轮指令冲突的过期结论, 需以当轮为准",
            "同一 URL navigate 熔断; evaluate 表达式形态重复会被拦",
        ],
        "cost": "每轮 20k~30k tokens",
        "next": ["PA 侧统一拆分批次与验收, 不让单轮承担过多步骤"],
    },
]


def _path():
    d = os.getenv("PA_DATA_DIR", "data/v9/pa")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "roster.json")


def load():
    """读花名册; 文件不存在则用内置卡片初始化。"""
    p = _path()
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("cards"), list):
                return data
        except Exception:
            pass
    data = {"cards": [dict(c) for c in _DEFAULT_CARDS], "ts": time.time()}
    save(data)
    return data


def save(data):
    data["ts"] = time.time()
    with open(_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    return {"ok": True, "count": len(data.get("cards") or [])}


def get(agent_id):
    for c in load().get("cards", []):
        if c.get("id") == agent_id:
            return c
    return None


def upsert(card):
    """新增或局部更新一张卡片(按 id)。只覆盖传入字段, 避免误删既有认识。"""
    if not isinstance(card, dict) or not card.get("id"):
        return {"ok": False, "error": "card 需要 id"}
    data = load()
    cards = data.get("cards") or []
    for i, c in enumerate(cards):
        if c.get("id") == card["id"]:
            merged = dict(c)
            merged.update({k: v for k, v in card.items() if v is not None})
            cards[i] = merged
            save(data)
            return {"ok": True, "updated": card["id"]}
    cards.append(card)
    save(data)
    return {"ok": True, "added": card["id"]}


def by_capability(keyword):
    """按能力标签找人 —— PA 派活时的第一步: 谁能干这个活?"""
    kw = (keyword or "").strip()
    if not kw:
        return []
    out = []
    for c in load().get("cards", []):
        blob = " ".join([c.get("name", ""), c.get("role", "")] + list(c.get("capabilities") or []))
        if kw in blob:
            out.append(
                {
                    "id": c["id"],
                    "name": c.get("name"),
                    "level": (c.get("access") or {}).get("level"),
                    "role": c.get("role"),
                }
            )
    return out


def summary():
    """给 PA 决策用的简表: 谁 / 什么级别 / 能干什么 / 有多脆。"""
    cards = load().get("cards", [])
    return {
        "count": len(cards),
        "by_level": {
            lv: [c["id"] for c in cards if (c.get("access") or {}).get("level") == lv] for lv in ACCESS_LADDER
        },
        "rows": [
            {
                "id": c.get("id"),
                "name": c.get("name"),
                "level": (c.get("access") or {}).get("level"),
                "role": c.get("role"),
                "caps": c.get("capabilities"),
                "fragility_n": len(c.get("fragility") or []),
            }
            for c in cards
        ],
    }
