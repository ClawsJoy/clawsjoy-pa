# -*- coding: utf-8 -*-
"""PA 网关接线 v0(2026-09-10): 把 core.pa 暴露为 HTTP 服务层(/v9/pa/*)。

设计原则(老板拍板 2026-09-10):
  - 最小侵入: 网关只加 register_pa_routes(app) 一行; 本模块不 import 网关, 可独立单测
  - 聊天不是闲聊: dialog 走"任务目标导向"的就事论事(响应=画像brief+账本brief+本会话上下文)
  - 聊天模式不触发执行循环: /v9/pa/dialog 纯商量, 要干活走 /v9/pa/dispatch(带契约+代理审核)
  - 画像沉淀: 审美/情感/口径/禁忌 均可随手落档(emotion 域与 aesthetic 并列)

路由:
  GET  /v9/pa/context          画像+账本 brief(前端右栏)
  GET  /v9/pa/profile          画像条目(status/domain 过滤)
  POST /v9/pa/sediment         沉淀一条(domain/value/source/confidence/status)
  POST /v9/pa/dialog           追加式会话(随时打断/换话题), 可选 brain 注入 LLM
  GET  /v9/pa/dialog           会话历史(?user_id&session_id&n)
  GET  /v9/pa/ledger           账本
  POST /v9/pa/ledger/add       加待办
  POST /v9/pa/ledger/done      完成待办
  POST /v9/pa/dispatch         分派(契约->执行->代理审核; 可带 to_seat ⇒ 投到席)
  GET  /v9/pa/dispatch/history 分派历史(?to_seat=)
  GET  /v9/pa/env              环境感知面(只读四栏: agents/kb/tools/resources)
  GET  /v9/pa/env/note         PA 自己的工作笔记(只读 · 侦察之产物)
  POST /v9/pa/env/research     触发一次只读侦察(唯只读工具 · 前后对表自证)
  GET  /v9/pa/resume           断点续面(只读: 离线攒件/续办/水印/失败件)
  POST /v9/pa/agent/invoke      统一调用面(册/席/CLI/云端API; agent_id 空 ⇒ 回册)
  POST /v9/pa/roster/probe      probe 实测刷新(唯此处触实测 ⇒ 落 card_probes.json)
  POST /v9/pa/dispatch/receipt 收口回执(拒未在册 task_id; 四段只进不退)
  GET  /v9/pa/dispatch/receipt 回执只读面(?task_id=)
  POST /v9/pa/dispatch/chase   催收一轮(超阈 + 限次; 同路运输)
  GET  /v9/pa/lines            产品线面(product_line: 线名/席/件集/状态/下一拍)
  POST /v9/pa/vault/sync       账本/站会/未读 同步到 Obsidian
  POST /v9/pa/archive         归档正文落服务端(X-11 层 1; 按 id 合并, 只写 archived, 写后读回确认)
  GET  /v9/pa/archive/<id>     按 id 取归档正文(查不到 404, 不拿空对象冒充)
  POST /v9/pa/steer            steer 通道入队(下一步指导 · 消费性: 每轮 drain 即清; 缺参 400)
"""
import logging
import os
import sys
import time
from pathlib import Path

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

from core.pa.pa_core import PaCore
from core.lib.paths import cmd_exe, org_enabled, path_forms, vault_root, ws_root
from core.pa import _proc as _proc   # ⭐ 窗隐唯一出口（PM 2026-10-05 令 · ⛔ 各写 creationflags）

# ⭐ PM 043 §二.1（裁）：**档** ＝ 显式拨杆（前端）之**单源**；⛔ 推断（`ask_domain` 仅佐证 · ⛔ 作主）。
#   承 L128：档系产品语义 ⇒ 须用户可预期 ⇒ 后端只认传参。
PA_SYSTEM_HEAD = (
    "你是老板的私人 PA(主权 agent)，不是通用聊天机器人。铁律：\n"
    "1) 就事论事、任务目标导向：始终围绕老板的目标/决策，不闲聊、不空转；\n"
)
# ⭐ PM 043 §二.2（P8 裁）：提示内 ⛔ 列字段名（连示例亦 ⛔）⇒ 只给**句意**；
#   三标之字面**唯入闸之码**（转义写 · 见 llm_brain 之 label_hits）⇒ 提示内一字不现。
PA_MODE_CLAUSE = {
    "work": ("2) 场合＝**办事**（显式拨杆 · 单源）：先给一句话答案；"
             "若确需抉择 ⇒ 给两三个备选并指出你荐哪一个，少开放式提问；"
             "⛔ 输出任何固定小标题／模板式标签（⛔ 照抄本提示之字面词）；\n"),
    "companion": ("2) 场合＝**陪伴**（显式拨杆 · 单源）：自然口语，陪着说；"
                  "⛔ 列备选式回执、⛔ 模板式标签、⛔ 固定小标题；\n"),
}
PA_SYSTEM_TAIL = (
    "3) 诚实底线：不编造数字/事实，未查到就写「待核实」，不说假完成；\n"
    "4) 记住他的在意点与情绪，自然地带出来；⛔ 把用户当待建档对象；\n"
    "5) 不越权：不承诺未授权的外部动作(写入/发布/付款)。\n"
    "6) 能力面照实：被问「你能做什么 / 工具 / 知识库检索范围」时，**逐项照抄系统给的真实面**"
    "（接口名照抄），⛔ 不泛泛而谈、⛔ 不承诺清单外的东西；\n"
    "7) ⛔ 无出处不许下事实判断 —— 系统会先跑一次知识库检索，检索结果会随上下文给出；"
    "无命中时**只许**说「查不到」，⛔ 不许给具体数字／无出处的判断。\n"
)

# ⭐⭐ pm_1802 §一.2／§一.3 ＋ pm_1804 §一（令）：**本通道 ＝「陪伴」**（只商量 · ⛔ 出手）。
#   ⭐ **正名之真源（页上之两名）**：`web/pa/faces/selfdesc.js:2868-2869` 之 `VAL`
#     ＝ { companion: 陪伴 ／ work: 办事 }；`web/pa/faces/tasks.js:51` 之**通道**映射
#     ＝ 陪伴 ⇒ `POST /v9/pa/dialog` ／ 办事 ⇒ `POST /v9/agent/chat`
#     ⇒ 提示词内**⛔ 自带一套辞**（旧书写「聊天 ／ 工作」＝ pm_1804 §一.1 之「两套辞」）。
#   ⭐ **两轴分书**（⛔ 混为一谈 · 模型旧病：「在能力面 ⟺ 我能做」）：
#     ⒜ **陪伴轴**（本通道）＝ 只商量 · ⛔ 不出手（⛔ 开只读动作之路 —— pm_1802 §二 之界）；
#     ⒝ **办事轴**（另通道）＝ 真动手 —— 其**许可面**逐条列（见下 9）。
#   ⚠ 办事轴之辞之**真源 ⛔ 在本件**：前端 `web/pa/faces/send.js:212`（CW 域）之 `sys`
#     被服务端模板 `config/prompts/agent_system.md` **覆盖**（`core/gateway/v9_chat/recovery.py:795`
#     `messages[0]["content"] = filled_prompt`）⇒ 本处所列为**镜像**（⛔ 二套真源 ⇒ 宜并为一处 · 报 PM）。
#   ⚠ 「禁辞」之字面**转义写**（承 L56-57：三标之字面唯入闸之码 · 源内 ⛔ 现字面）；
#     运行期之提示**含**此表（PM 令「系统提示须明书」）—— 故源内 `rg` ⛔ 命中（可核）。
PA_CHANNEL_CLAUSE = (
    "8) ⭐ **本通道 ＝「陪伴」**（页上之「陪伴」档）＝ **只商量 · 不出手**：你在这里**只出话** —— "
    "⛔ 执行动作、⛔ 调接口、⛔ 落记录；你说的话**不会**让任何事发生。\n"
    "9) ⭐ **两轴分书**（一名一义 · ⛔ 混为一谈）：\n"
    "   · **陪伴轴**（本通道 · 页上「陪伴」· `POST /v9/pa/dialog`）：**只商量 · ⛔ 不出手**；\n"
    "   · **办事轴**（页上「办事」· `POST /v9/agent/chat`）：**真动手** —— 其许可面逐条 ＝"
    " ⒜ 办公类 computer use：文档 ／ 表格 ／ 浏览器 ／ 图文 ／ 演示；"
    "⒝ 项目开发：代码 ／ 工程（权限最高）；工具用完须汇报**产物**与**待核实**项。\n"
    "10) ⭐ **「在能力面」⛔ 等于「我现在能做」**：上面那份清单答的是「本 PA **有**哪些接口」；"
    "**能不能动手**看**轴**。被问能否动手 ⇒ **照实**：陪伴轴只商量；要真跑 ⇒ 切「办事」。\n"
    "11) ⛔ **禁辞**（「未做而似做」之辞）：⛔ 输出 \u5df2\u53d7\u7406 ／ \u5df2\u5b89\u6392 ／ "
    "\u5df2\u8f6c\u529e ／ \u6b63\u5728\u5904\u7406 之类**暗示你已替老板办了事**之辞"
    "（用户眼里 ⛔ 可分 ⇒ 违诚实底线）。\n"
    "12) ⭐ 每逢「能不能动手 ／ 能不能查」之问 ⇒ **末句须逐字带上此去处**（**照抄 · 一字不省** · "
    "⚠ 此句**非**「备选式回执」之列 —— 承 L62 之禁**不涉**此句）；"
    "⛔ 以「自然口语」或「简洁」为由省略："
    "「要真跑 ⇒ 点 `\U0001fa7a 本机体检`（只读）∨ 切「办事」」。\n"
)

PA_SYSTEM_CLOSE = "回复简洁，控制在 160 字内，中文。"


def pa_mode_name(mode=None):
    """档之**归一**：唯显式拨杆之值 ⇒ `work` ∨ `companion`（⛔ 推断）。"""
    m = str(mode or "work").strip().lower()
    return "companion" if m in ("companion", "陪伴", "peiban", "chat") else "work"


def pa_system_for(mode=None):
    """按**显式 mode** 组装系统提示（PM 043 §二.1 · 单源）。

    ⭐ pm_1802 §一.2／§一.3：**通道节**（`PA_CHANNEL_CLAUSE`）**逐档皆附** ——
      「只商量 · 不出手」＋「能力面 ⟷ 本通道」分书 ＋ 禁辞表 ＋ 可执行之去处。
    """
    return (PA_SYSTEM_HEAD + PA_MODE_CLAUSE[pa_mode_name(mode)]
            + PA_SYSTEM_TAIL + PA_CHANNEL_CLAUSE + PA_SYSTEM_CLOSE)


PA_SYSTEM = pa_system_for("work")   # 兼容既有引用（`system_prompt or PA_SYSTEM`）· ⛔ 破

# ⭐⭐ pm_1802 §一.1（令）：能力面清单 ⇒ **由路由表生成**（⛔ 手写常量 ⇒ 防漂）。
#   ⚠ 旧病（一手 · 两条自证其漂）：
#     ⒜ 手写清单列 `local_client` 而 **⛔ 列** `/v9/pa/sys/*` —— 真路由随 9.0.6 上
#        ⇒ 模型照实回「不在授权面」（**它 ⛔ 说谎 · 是表旧了**）；
#     ⒝ 末行「检索范围（当前）：收件箱 / 知识库 两类」亦旧 —— 真扫面早经 `pa_ask_scan_specs`
#        扩至 `pa_faces()` 之面（`pa_kb_search` 之注：「2026-10-04 … 增扫 PA_FACES 之面」）
#        ⇒ **手写一次 · 漂两处**（此即「防漂须自动生成」之据）。
#   ⭐ 二义**分书**（一名一义 · pm_1802 §一.3）：本节 ＝ **能力面**（本 PA **有**哪些接口）；
#      `PA_CHANNEL_CLAUSE` ＝ **本通道能不能动手**（聊天 ⇒ ⛔ 不能）。
_PA_ROUTE_PREFIX = "/v9/pa/"
_CAP_BRIEF_METHODS = ("GET", "POST", "PUT", "DELETE", "PATCH")


def build_capability_brief(url_map):
    u"""由**路由表**（`app.url_map`）生成能力面清单（⛔ 手写 · pm_1802 §一.1）。

    ⚠ 须于 `app.register_blueprint` **之后**取：注册前蓝图之路由尚在 `deferred_functions`
      之列，⛔ 现于 `url_map` 之 `Rule` ⇒ 早取 ＝ **空表**（假绿）。
    """
    rows = []
    for _r in url_map.iter_rules():
        _rule = str(getattr(_r, "rule", "") or "")
        if not _rule.startswith(_PA_ROUTE_PREFIX):
            continue
        _ms = sorted(_m for _m in (getattr(_r, "methods", None) or set())
                     if _m in _CAP_BRIEF_METHODS)
        rows.append((_rule, u"/".join(_ms) or u"-"))
    rows.sort()
    _head = (u"【本 PA 的真实能力面（**由路由表自动生成** · pm_1802 §一.1）】\n"
             u"· 接口共 %d 条（前缀 `%s`）—— **照抄**，⛔ 不许加清单外的东西。\n"
             u"· ⚠ 此清单答的是「本 PA **有**什么」（供你**如实作答**之料）；\n"
             u"  **⛔ 不等于你此刻能调它** —— 能不能动手**看轴**（见系统提示之「两轴分书」）。\n"
             % (len(rows), _PA_ROUTE_PREFIX))
    return _head + u"".join(u"  [%s] %s\n" % (_m, _p) for _p, _m in rows)


# 生成前之占位（**⛔ 以手写清单充数**）：真值由 `register_pa_routes` 于挂载时落（见下之门）。
PA_CAPABILITY_BRIEF = u""


def capability_brief():
    u"""**门**（一处定形）：取当前能力面清单 —— 未挂载过 ⇒ 以**临时 app** 现生一次。

    ⚠ 由：`llm_brain()` 可于**任何 app 之外**被构造（单测直调）⇒ 全局尚空；
      临时 app 与真 app 走**同一套蓝图** ⇒ 清单同源（⛔ 二套读者）。
    """
    global PA_CAPABILITY_BRIEF
    if not PA_CAPABILITY_BRIEF:
        try:
            from flask import Flask as _Flask
            register_pa_routes(_Flask("pa_capability_standalone"), brain=None)
        except Exception as _e:
            print("[PA] ⚠ 能力面清单（临时 app 生）未成：%s: %s" % (type(_e).__name__, _e), flush=True)
    return PA_CAPABILITY_BRIEF


def _set_capability_brief(app):
    u"""挂载即定形：由**本次挂载后**之路由表现生 ⇒ 新路由一上，清单自跟（pm_1802 §一.1）。"""
    global PA_CAPABILITY_BRIEF
    try:
        PA_CAPABILITY_BRIEF = build_capability_brief(app.url_map)
    except Exception as _e:
        print("[PA] ⚠ 能力面清单未生成：%s: %s" % (type(_e).__name__, _e), flush=True)
    return PA_CAPABILITY_BRIEF


# ⭐ 058 §一.3（裁）：`/v9/pa/ask` 复问缓存（进程级 · 只读检索面）。
#   ⚠ ⛔ 改 `searched` 之语义（承 057 §一.2 唯加键）⇒ 新键 `from_cache` ／ `scanned` ／ `saved_wall_s`。
_ASK_CACHE = {}
_ASK_CACHE_MAX = 256
# ⭐ 059 §二：冷／热两态须分 —— 进程内首轮 ＝ `cold`（本机 7B 首载 · 我一手 `50.6 s`）⟷ 其后 ＝ `warm`。
_LLM_PHASE = {"warmed": False}


def _lru_put(cache, key, val, cap):
    u"""**LRU 存**（一处定形 · pm_1569 §五）—— 满 ⇒ 逐**最旧**（⛔ 弃新）。

    旧病：if len(cache) < cap: cache[k] = v ⇒ 一旦满 ⇒ **新键永不入**（复问恒 miss ∧ 死键只增
      不减 ⇒ 「治了等于没治」之潜口 · 承 pm_1549 §一 之旨）。
    ⚠ **命中亦须过此**（pop ＋ 重插 ⇒ 提为最新）—— 否则降为 FIFO（⛔ LRU）。
    ⚠ dict 保插入序（py3.7+）⇒ 首键 ＝ 最旧 ⇒ ⛔ 须 OrderedDict ／ 新导。
    """
    if key in cache:
        cache.pop(key, None)
    elif len(cache) >= cap:
        cache.pop(next(iter(cache)), None)
    cache[key] = val


def _pa_read_at():
    u"""**取数之刻**（一处定形 · pm_1478 §二）—— 后端算成本轮回执之刻。

    ⚠ 义（⛔ 混）：**取数之刻**（就地时钟 · 本回执诸数之取时）
      —— ⛔ **落盘之刻**（那属 `persisted.*` 之域 · 另一端）。
    ① 名就旧：与 `/v9/pa/ask` 之 `read_at` **同名同义**（前端 `read_at || at` 之首选）。
    ② 格式就旧：`%Y-%m-%d %H:%M:%S`（承三处旧行 · 唯此一处出）。
    """
    from datetime import datetime as _dt
    return _dt.now().strftime("%Y-%m-%d %H:%M:%S")


def llm_brain(system_prompt=None, model=None, max_tokens=None):
    """构造对话脑: 用 V9 LLMClient 生成 PA 回复; 失败返回 None(上层降级为模板回复)。"""

    def _brain(context_text):
        _brain.last_route = {}
        try:
            from core.lib.llm_client import LLMClient

            prompt = "%s\n\n%s\n\n【上下文(画像/账本/本会话)】\n%s" % (
                system_prompt or PA_SYSTEM, capability_brief(), context_text)
            # ⭐⭐ pm_1609 §二.1（令一 · 路由须依「可用性」）：PA 之路旧以 `model=None` 尽付
            #   `LLMClient._call` 之 `model or config.default_model`（＝**本机 Ollama 之 7B**）
            #   ⇒ **⛔ 问可用性**（净机无 Ollama ⇒ 仍取本机 ⇒ [WinError 2]）∧ 与 `GET /v9/pa/providers`
            #   所报之默认（`remote:deepseek`）**二处不一**（pm_1609 §一.5 之铁证）。
            #   今：**缺省之路唯 `providers.default_route()` 一处出**（可用者优先 · 与 providers 同源）；
            #       并「皆不可用 ⇒ ⛔ 调模型」＋ 显形其由（⛔ 静默换 · 承 pm_1471 §三.2）。
            _model_use = model
            _route_note = u""
            if _model_use is None:
                from core.pa.providers import AVAIL_OK, available_state, default_route
                _r0, _route_note = default_route()
                _model_use = _r0.get("model")
                _st0, _why0 = available_state(_r0.get("provider"))
                if _st0 not in AVAIL_OK:
                    _brain.last_route = {"provider": _r0.get("provider"), "model": _model_use,
                                         "fell_back": False, "reason": "no_provider_available",
                                         "provider_state": _st0, "provider_why": _why0,
                                         "route_note": _route_note}
                    return PA_NO_PROVIDER_TEXT
            _c = LLMClient()
            # ⭐ §二.4 裁：max_tokens 入注册表（一处配 · ⛔ 魔数散落）
            #   ⚠ 用新名 `_mt`：直赋 `max_tokens` 会令其成为 `_brain` 之局部 ⇒ 首读即 UnboundLocalError
            _mt = max_tokens
            if _mt is None:
                try:
                    from core.pa.providers import default_max_tokens
                    _mt = default_max_tokens()
                except Exception:
                    _mt = 1600
            # ⭐ pm_1447 §二.3②（P2 最小缝）：`model=` 之链（`llm_brain` ⇒ `generate` · **唯加一参** · ⛔ 改 `_call` 骨架）
            #   ⚠ 缺省 `None` ⇒ `generate` 之默认路（行为 ⛔ 变）。
            out = _c.generate(prompt, model=_model_use, max_tokens=_mt)
            try:
                _brain.last_route = _c.get_last_route()
            except Exception:
                _brain.last_route = {}
            # ⭐ pm_1609 §二.1：**显形**「默认之 X 不可用 ⇒ 由 Y 代之」之由（⛔ 静默换）
            if _route_note:
                _brain.last_route["route_note"] = _route_note
            # ⭐ pm_1609 §二.3：原始异常唯入**机器面**（⛔ 用户面）
            try:
                _brain.last_route["last_error"] = getattr(_c, "last_error", "") or ""
            except Exception:
                pass
            # ⭐ P8 之闸（§二.2：提示内 ⛔ 列字面 ⇒ 兑换必在提示**外**扫描）
            #   以码扫答体之三标（转义写 ⇒ ⛔ 把字面带进提示）
            _brain.last_route["label_hits"] = [
                _s for _s in ("\u7ed3\u8bba\uff1a", "\u9ed8\u8ba4\u9879\uff1a", "\u53ef\u9009\u9879\uff1a")
                if _s in (out or "")]
            # ⭐ 057 §一⒞：本轮 tokens（器取）。每轮新建 `LLMClient` ⇒ `_stats` 即**本轮**之累计
            #   （本机径写 `eval_count` ／ 远端径写 `usage.total_tokens` —— 见 core/lib/llm_client.py 之 eval_count 之读处（今 :437 / :446 / :547）／ usage.total_tokens 之读处（今 :671 / :680））。
            #   ⛔ 编：取不到 ⇒ `None`（回执如实写「无」）。
            try:
                _brain.last_route["tokens"] = int(_c.get_stats().get("total_tokens") or 0)
            except Exception:
                _brain.last_route["tokens"] = None
            return (out or "").strip() or None
        except Exception:
            return None

    _brain._is_pa_brain = True
    return _brain


def _session_binding(_tstate, _uid):
    """会话绑定自检（老板 2026-10-03 裁）：activeThread 为空 ∧ 本地有历史 ⇒ **报「会话未绑定」**。

    为什么需要它：`GET /v9/pa/threads` 在未绑定时返回**空表**（`threads: []`）——
    「空表」被读成「本来就没有」，而盘上明明有有内容的会话（实测 uid `web_1790773805388`
    下 `pa_mu6fxm7z` 有 1,020 个 `.py`，页面却报空）。
    空表是**读数**，⛔ 不是结论 ⇒ 本函数把「为什么空」一并报出（可机检字段 `session_unbound`）。
    判据：`session_bound == False` ∧ `local_sessions != []` ⇒ `session_unbound == True`。
    """
    _out = dict(_tstate) if isinstance(_tstate, dict) else {}
    _active = _out.get("activeThread")
    _locals = []
    try:
        _uid_s = str(_uid or "default")
        _base = None
        for _cand in (Path(_data_dir()).parent.parent / "projects" / _uid_s,
                      Path("data/projects") / _uid_s):
            if _cand.is_dir():
                _base = _cand
                break
        if _base is not None:
            for _d in sorted(_base.iterdir()):
                _dev = _d / "clawsjoy_dev"
                if not (_d.is_dir() and _dev.is_dir()):
                    continue
                _n = sum(1 for _ in _dev.rglob("*.py"))
                if _n:
                    _locals.append({"session_id": _d.name, "py_files": _n})
    except Exception:
        _locals = []
    _out["session_bound"] = bool(_active)
    _out["local_sessions"] = _locals
    _out["session_unbound"] = bool(not _active and _locals)
    if _out["session_unbound"]:
        _out["reason"] = "session_unbound"
        _out["message"] = ("会话未绑定：activeThread 为空，而本地有 %d 个有内容的会话（如 %s）"
                           " ⇒ ⛔ 这不是「没有历史」，须先选定会话。" % (len(_locals), _locals[0]["session_id"]))
    return _out


def _data_dir():
    return os.getenv("PA_DATA_DIR", "data/v9/pa")


# ---------------------------------------------------------------- P2 ①：会话级模型（pm_1449 §二.1）
# 「表出决定之仓」＝ **会话档之字段**（与 `mode` 同轴 · 一处定形）——
#   ⛔ 进程级单例（多会话 ⛔ 分）· ⛔ 前端硬编（承 pm_1449 §二.1 之裁）。
#   名之验 ＝ **后端白名单**（`core/pa/providers.resolve_model` ⇒ 注册表之实名）
#   ⇒ ⛔ 自由字串（非法 ⇒ 400 显因 · ⛔ 静默回落）。
def _loopback(req):
    """唯本机（环回）—— 另端（LAN / 他机）⛔ 达（承 pm_1613 令四 · 端之鉴权）。

    ⚠ 服务绑 0.0.0.0 ⇒ LAN 可达本端 ⇒ 故须显判（⛔ 凭「无鉴权」而放行）。
    """
    a = str(getattr(req, "remote_addr", "") or "").strip()
    if a.startswith("127."):
        return True
    if a.startswith("::ffff:") and a[7:].startswith("127."):
        return True
    return a in ("::1", "localhost")


def _uid_safe(raw):
    """单段 uid（⛔ 空 ／ ⛔ 路径分隔 ／ ⛔ 穿越）—— 会话档之径。⛔ 得 ⇒ ""。"""
    s = str(raw or "").strip()
    if not s or chr(0) in s or s in (".", "..") or "/" in s or "\\" in s or ":" in s:
        return ""
    return s


def session_model_of(uid, req=None):
    u"""会话之 `model` ⇒ (实名 ∨ None, 源之述)。

    `req` 有值 ⇒ **归一 ＋ 白名单验**：非法 ⇒ (None, 拒之由)（调用方 400）
    · 合法 ⇒ 落档（**唯变时写**）。
    ⚠ 会话档读不动（`ThreadStoreCorrupt`）⇒ **⛔ 静默当空**：返 (None, 照实之由)。
    """
    from core.pa.providers import resolve_model_ex
    from core.pa.threads import ThreadStore, ThreadStoreCorrupt

    ts, key = ThreadStore(_data_dir()), (uid or "default")
    if req is not None and str(req).strip():
        _m, _note = resolve_model_ex(req)
        if not _m:
            return None, ("未识之模型名：%s（唯注册表之实名 ∨ 别名 ∨ 显示名 —— 见 GET /v9/pa/providers 之 known_models）" % (str(req)[:60],))
        try:
            st = ts.load(key)
        except ThreadStoreCorrupt as _e:
            return None, "会话档读不动，⛔ 落模型：%s" % (str(_e.reason or "")[:80],)
        if st.get("model") != _m:
            st["model"] = _m
            try:
                ts.save(key, st)
            except ThreadStoreCorrupt as _e:
                return None, "会话档拒写，⛔ 落模型：%s" % (str(_e.reason or "")[:80],)
        return _m, ("会话档" if not _note else ("会话档 ｜ " + _note))
    try:
        st = ts.load(key)
    except ThreadStoreCorrupt as _e:
        return None, "会话档读不动 ⇒ 模型回落默认：%s" % (str(_e.reason or "")[:80],)
    _m = st.get("model")
    return (str(_m) if _m else None), ("会话档" if _m else "未设 ⇒ 默认")


def session_model_clear(uid):
    u"""清会话之 `model` ⇒ 回落默认（注册表 `DEFAULT_MODEL`）。⇒ (bool, 述)。"""
    from core.pa.threads import ThreadStore, ThreadStoreCorrupt

    ts, key = ThreadStore(_data_dir()), (uid or "default")
    try:
        st = ts.load(key)
    except ThreadStoreCorrupt as _e:
        return False, "会话档读不动，⛔ 清：%s" % (str(_e.reason or "")[:80],)
    if "model" in st:
        st.pop("model", None)
        try:
            ts.save(key, st)
        except ThreadStoreCorrupt as _e:
            return False, "会话档拒写，⛔ 清：%s" % (str(_e.reason or "")[:80],)
    return True, "已清（回落默认）"

def _permission_grant_provenance(data_dir):
    """**权限档的来源面**（2026-09-30 · PM 裁定「丙 的更严形态」）。

    只回答一件事：**盘上到底有没有真授予文件**。
    ⛔ 不参与任何判定（谁放行仍由既有代码判）；⛔ 不改 level 语义。
    为什么加：`permission.json` 与 `boss_grant.json` **都不存在**时，
    前端只拿得到 ``level``＝默认值 ⇒ 「默认值假装成读数」（与 437 假绿同族）。

    两处授予（语义不同，⛔ 不合并）：
      · ``pa``  —— PA 侧 ``permission.json``（本路由的生效值来源）
      · ``pes`` —— 执行侧 ``boss_grant.json``（PES 老板级，路径取 core.pes 的默认值，不另发明）
    """
    # 给**绝对**路径：相对路径会带上调用方的 CWD（且分隔符混用），人拿去找不到文件
    pa = os.path.abspath(os.path.join(data_dir, "permission.json"))
    try:
        from core.pes.authorization import DEFAULT_BOSS_PATH as _boss
        pes = str(_boss)
    except Exception:
        pes = os.path.join("data", "v9", "pes", "boss_grant.json")
    return {
        "pa": {"path": pa, "exists": os.path.exists(pa)},
        "pes": {"path": pes, "exists": os.path.exists(pes)},
    }




def _web_root():
    """与 ``core/web/health.py`` 的 ``send_from_directory("web", ...)`` **同源**：
    Flask 把相对目录解析到 ``app.root_path``。⛔ 不另发明路径口径。"""
    try:
        from flask import current_app

        return os.path.join(current_app.root_path, "web")
    except Exception:
        return os.path.join(os.getcwd(), "web")


def _frontend_build(filename="pa.html"):
    """**前端构建指纹**（2026-09-30 · PM 批）：回答「你手上这份页面是哪一版」。

    为什么必须由**服务端现算**：⛔ 页面不能内嵌自身 sha16（改了字节指纹必变 ⇒ 内嵌＝自欺）。
    所以指纹按 **服务端实际发出去的那份** ``web/<filename>`` 现读现算，页面只负责显示。
    现场（09-30）：「😵 服务暂不可用」的归属之争就卡在「两版页面无法区分」
      —— 现盘 ``web/pa.html`` 那句出现 0 次（结构上不可能产出），而 PM 手上的页面产出过它。
    ⛔ 本函数只做读数，不参与任何判定。
    """
    p = os.path.join(_web_root(), filename)
    out = {"path": os.path.abspath(p), "exists": os.path.exists(p)}
    if not out["exists"]:
        return out
    try:
        import hashlib as _hl
        import time as _tm

        with open(p, "rb") as f:
            b = f.read()
        out["bytes"] = len(b)
        out["sha16"] = _hl.sha256(b).hexdigest()[:16]
        out["mtime"] = _tm.strftime("%Y-%m-%d %H:%M:%S", _tm.localtime(os.path.getmtime(p)))
    except Exception as e:
        out["error"] = "%s: %s" % (type(e).__name__, e)
    return out


def _core(user_id=None):
    """单 principal 先跑通(多租户后续: data/v9/pa/users/<uid>)。"""
    return PaCore(data_dir=_data_dir())


# ---- 批176 · 副指标 A：知识库 ↔ 沙箱映射（只读三列 + 状态枚举）----
KB_STATUS_MIRRORED = "已镜像"
KB_STATUS_STALE = "过期"
KB_STATUS_MISSING = "缺失"
KB_STATUS_UNMIRRORED = "未镜像"
# P9 · 验收-B（三态）：没有可比的副本面时判「未知」—— 不适用 不等于 验过，
# 所以也不许把它算成「过期 0」那种看起来像读数的 0。
KB_STATUS_UNKNOWN = "未知"
KB_STATUSES = (KB_STATUS_MIRRORED, KB_STATUS_STALE, KB_STATUS_MISSING, KB_STATUS_UNMIRRORED, KB_STATUS_UNKNOWN)
KB_MAPPING_DEFAULT_SCOPE = "收件箱"
KB_FINGERPRINT = "sha256_16"
KB_FINGERPRINT_MAX_BYTES = 32 * 1024 * 1024
# BUG-2：知识库检索面（有据才答）
PA_KB_ASK_SCOPES = ("收件箱", "知识库")
# ⭐ PM 2026-10-05 22:34 §四⒝-1：拒答之辞 ⇒ **canonical（一处定义 · 真源归后端）**
#   病（逐字）：原辞「查不到（知识库里没有相关内容）」**失实** —— 本闸实扫**八面**
#     （收件箱 ／ 知识库 ／ 文件 ／ 台账 ／ 平台台账 ／ 台账·信通 ／ 梦中月水中花 ／ 文件·产出）
#     ⇒ 「知识库」以偏概全 ⇒ 辞失实（承「⛔ 以偏概全之辞」）。
#   ⚠ 且前端 `web\pa\faces\send.js` 另有 `PA_REFUSE_CANON` ⇒ **两辞并存 ＝ 漂移之床**（承「一处口径」）
#     ⇒ 今定 canonical 于**后端**（唯此一处），前端改**引用**（响应键 `refusal_canon` · 见 `pa_ask` 之 base）⇒ ⛔ 二处各写。
#   ⚠ 界（照 PM 之限）：⛔ 不改闸之判据；⛔ 不改「判据行」（verdict）之实 —— 唯「答话」之辞正。
PA_ASK_REFUSAL = "本机无据 ⇒ 我不答此问。"
# ⭐⭐ pm_1609 §二.1／§二.3（缺陷之族 · 即刻办）：**「皆不可用」之人话 ＋ 去处**（一处定形）。
#   病（净机之屏 · 逐字 · pm_1609 §〇）：三问皆走 `local:qwen2.5:7b-instruct-q4_0-gpu` 而本机无模型
#     ⇒ 屏上 ＝ `模型调用失败：本机与云端皆不可用（[WinError 2] 系统找不到指定的文件。）`。
#   ⇒ 凡「⛔ 可调模型」⇒ 出此一句（⛔ 原始异常 · ⛔ 以失败充答）。
PA_NO_PROVIDER_TEXT = (u"模型不可用：本机与云端皆未接（本机未装模型 ／ 云端未配密钥）"
                       u"⇒ 请到「模型配置」配密钥，或装本机模型。")
# ⭐⭐ pm_1609 §二.2（令二 · 该拒答而未拒）：**检索面为空 ⇒ 亦须有人话**（⛔ 直落模型）。
#   病（净机之屏 · 逐字 · pm_1609 §一.2）：`答源 not_applicable（不适用（检索面为空 ⇒ 拒答与否皆不成立））`
#     ⇒ `answer` 空 ⇒ 前端**直落模型** ⇒ 屏上唯「模型调用失败」（⛔ 以失败充答）。
#   ⇒ 不适用亦出人话（与「拒答」分键：`refused=False` ／ `answer_source="not_applicable"` ⛔ 变）。
PA_KB_EMPTY_ANSWER = u"本机还没有可检索的资料（检索面为空）⇒ 我不答此问。"
# ⭐ 旧辞（失实 · ⛔ 勿再入 answer）：留名以**识别旧痕**（前端词形闸之旁证 · 承 PM 22:34 §三）
PA_ASK_REFUSAL_STALE = "查不到（知识库里没有相关内容）"
# ⭐⭐ pm_1500 §二：库根未接 ⇒ **早返**（⛔ `Path("")` ⇒ **误扫 CWD** · 潜在假有据）
#   病（本刻一手）：以**空串**充「未接」（`kb = os.getenv(...) or (str(_vr) if _vr is not None else "")`）
#     ⇒ `pa_kb_search(q, "")` 之 `Path("") / "收件箱"` ＝ **`收件箱`（CWD 相对）**
#     ⇒ 若 CWD 恰有同名子目录 ⇒ **误扫**（`gateway_routes.py:431` ／ `:484` 所警之族）。
#   ⚠ 二路之别：`PA_FACES` 路**有守**（`_rel_under` 缺基 ⇒ `None` ⇒ 该面 ⛔ 入表）；
#     `PA_KB_ASK_SCOPES`（收件箱 ／ 知识库）一路**无守**（其路取 `Path(kb_root)`）⇒ 本修补之。
#   守：「未接」之判**唯此一处**（`_kb_root_str()`）⇒ ⛔ 二处各判「空」（承「一处定形」）。
#   判词（一处定形）：其因须名「待选目录」 ⇒ **可分**于「扫了而无」（承「空 ≠ 缺」）。
PA_KB_UNSET_VERDICT = (u"未接（选目录）：库根 ⛔ 得 ⇒ 本轮 ⛔ 扫描"
                       u"（⛔ 以空径充 ⇒ 误扫 CWD ⇒ 假有据）"
                       u"⇒ 拒答与否皆不成立（待选目录）")
PA_ASK_MIN_SCORE = 0.42  # ⭐ 2026-10-04：0.34 → 0.42（扩面后弱命中 0.375 之假有据之修）

# ⭐⭐ pm_1486 §一（裁：取拟一）：**「闸之实」⇒ 回执之结构化判据**（**一处定形**）。
#   病（老板一手 · session_pa_muwdx6o7）：**同一问**（「你使用的模型是什么」）**二次之屏果不同**
#     —— 因前端 Fork-2 以**模型之辞之词形**（`paSelfRefusal`）判果（辞以「查不到」起首 ⇒ 显拒答；
#     辞以「当前检索范围…未找到相关描述」起首 ⇒ 显「回落」）⇒ **以辞判果 ⇒ 必漏**（承「以形判必漏」）。
#   ⇒ 正解：**判据归后端**（一处定形）⇒ 前端**唯读键** ⇒ ⛔ 判辞（承「一处定形」）。
#   ⚠ 唯加键（⛔ 破既有字段之语义）。
# ⭐⭐ pm_1493 §一（令：正 `why` 与公式之抵）：`refused` 之注旧书「若未回落 ⇒ display=refuse」
#   —— ⚠ 与码 **⛔ 同物**（`_disp` 唯取 `fact_family` ⇒ ⛔ 含「回落」之维）⇒ **文从码**（承「一名一义」）。
# ⭐⭐ pm_1493 §三（裁：其义扩为「本机事实族」· **含非是非问**）：旧名 `fact_yn`（是非问）射程 **⛔ 足**
#   （实证 · CW 一手之漏拦之例：`台账里有哪些项目？` ⇒ 非是非问 ⇒ 旧标恒 `false` ⇒ **漏拦**）
#   ⇒ 正名 **`fact_family`**（一名一义：本轮之问**是否属「本机事实族」**）
#   ⇒ `display = "refuse" iff (decision == "refused" ∧ fact_family)`。
#   ⚠ 一处定形：其判唯自**前端一处**出（`PA_FACT_MARK` 一族 · `web/pa/faces/selfdesc.js:1187`）
#     ⇒ 后端**唯读入参**（⛔ 自判 ⇒ 免二源）。
PA_GATE_DECISIONS = ("not_asked", "grounded", "refused", "not_applicable")
PA_GATE_DISPLAY = ("model", "refuse")
PA_GATE_WHY = {
    "not_asked": "本轮未过「有据才答」闸（自述 ／ 元问 ／ 域外等）⇒ 答由模型出",
    "grounded": "闸判有据（hits 非空 ／ 直读本机账）⇒ 答非拒答",
    "refused": "闸判无据（hits 空）⇒ 本机事实族之问显 canonical 拒答（余者按回落显模型之答）",
    "not_applicable": "闸判不适用（searched==0：搜索面为空）⇒ 拒答与否皆不成立",
}


def pa_gate_view(decision=None, origin=None, grounded=None, answer_source=None, fact_family=False):
    """⭐ 一处定形：「闸之实 ＋ 回落之意」⇒ **显示之果**（pm_1486 §二.2）。

    值域（一名一义 · ⛔ 前端自拟）：
      decision ∈ PA_GATE_DECISIONS —— 本轮之闸判（`refused` ＝ 无据且已回落）
      display  ∈ PA_GATE_DISPLAY  —— **显模型之答**（`model`）∨ **显 canonical 拒答**（`refuse`）
      fact_family                 —— 本轮之问**是否属「本机事实族」**（含非是非问 · 转交 · ⛔ 辞）
      refusal_canon               —— canonical 拒答文（真源唯此一处 ⇒ 前端引用）
      why                         —— 该判之由（逐字 · 供注记 · ⛔ 用户面）
    ⚠ 其源：`decision` 取**后端 `/v9/pa/ask` 自产之闸果**（前端**唯转交**）；`fact_family` 取前端之
      **结构判**（`PA_FACT_MARK` 一族 · ⛔ 辞）—— 二者**皆非「模型之辞」**（即本裁之要）。
    """
    _d = decision if decision in PA_GATE_DECISIONS else None
    if _d is None:
        if grounded is True:
            _d = "grounded"
        elif (origin == "refused") or (answer_source in ("refused", "archive_only")):
            _d = "refused"
        elif (origin == "grounded") or (answer_source == "knowledge"):
            _d = "grounded"
        else:
            _d = "not_asked"
    _family = bool(fact_family)
    _disp = "refuse" if (_d == "refused" and _family) else "model"
    return {"decision": _d, "display": _disp, "fact_family": _family,
            "refusal_canon": PA_ASK_REFUSAL, "why": PA_GATE_WHY.get(_d, "")}

# ⭐ 2026-10-04 新增（PM b136893 · 老板批 · 阶段 2「素材面接入」之**最小登记** · 只读）：
#   面表：面名 ⇒ (根…, 通配…)。⛔ 用户输入之路径 —— 根皆**常量**（"@vault:" 前缀＝vault 内相对）
#   ⇒ 无穿越风险（沿用 _kb_safe_rel 之精神）。⛔ 不改 (收件箱/知识库) 之既有口径；⛔ 不写盘。
# ⭐ 2026-10-06（pm_1409 §二.3 ·「产品 ⟷ 组织」之切）：根皆**非字面绝对径** —— 二源出根：
#   ⒈ `ws_root()`（**产品级** · env `PA_WS_ROOT`）⇒ 下之相对段（工作区面：文件 ／ 台账 ／ _交付）；
#   ⒉ `vault_root()`（**用户自选**知识库 · 承 1387 §二.2 ／ 1388 §二.1）⇒ 下之相对段（vault 面）。
#   ⚠ 缺基（＝ `None`）⇒ 该面 **⛔ 入表**（⛔ 空径 ⇒ 误扫 cwd）—— 照实「未接」（⛔ 崩 ／ ⛔ 静默扫错）。


def _rel_under(base, *parts):
    """`base` 之下的相对径（⛔ 字面绝对径 · 承 pm_1409 §二.3）—— 缺 `base` ⇒ `None`。"""
    return os.path.join(base, *parts) if base else None


# ⭐⭐ pm_1520 §二.3（甲 · 件三）：本表 ⇒ **惰算**（⛔ import 即定形）——
#   病：旧为**顶层赋值**（根取自 import 之刻）⇒ 改库根（`POST /v9/pa/vault/set`）⇒
#     **须重起方生效**（承 pm_1517 §二.4 之「选了 ⛔ 生效」）。
#   法：全表移入本函数（`_FACE_WS` ／ `_FACE_VR` 取**当刻**）＋ 名由模块级 `__getattr__` 供 ⇒
#     读者字面**不变** ∧ 取值**当刻** ∧ **无缓存**（⛔ `lru_cache` 之族 · 承 pm_1517 §三.2）。
def _pa_faces_tables():
    u"""（PA_FACES, PA_FACES_GATE）—— **惰算**（依**当刻**之 `ws_root()` ／ `vault_root()`）。"""
    _FACE_WS = ws_root()
    _FACE_VR = vault_root()
    _PA_FACES_ORG = (
        ("文件", (_FACE_WS,), ("*.md", "*.txt")),
        # ⭐ 台账面＝**只取台账本身**（⛔ 不收整个 `_auto\deliver`：那含我的报告集）
        ("台账", (_rel_under(_FACE_WS, "_auto", "deliver"),),
         ("老板令台账_v1.md",)),  # ⛔ 收 `投递台账.csv`／`债单_*.md`（真身皆在信通 · 该根下⛔存在 ⇒ 空转）
        # ⭐ PM 2026-10-05（老板批「并入技总写域」之同批 · 承 技总 972 §五）：新面 `平台台账`
        #   真源 ＝ `…\内容工坊\04_平台台账`（`46` 项 · ⛔ 存底类：`*.md` 天然排除 `.before_*` ／ `.bak_*` ／ `.sha256`）
        #   ＋ `平台注册表.md`（生成物 · 源头 `08_工具\平台\*\plugin.json`）⇒ `role: knowledge`（⛔ archive ⇒ 可作据）
        ("平台台账", (_rel_under(_FACE_VR, "内容工坊/04_平台台账"),), ("*.md",)),
        ("台账·信通", (_rel_under(_FACE_VR, "内容工坊/02_协作/信通"),),
         ("投递台账.csv",)),  # ⛔ 收 `债单_*.md`（内含测试问题引用 ⇒ 污染）
        # ⭐ 2026-10-05（PM b136893 令「menghua 进 PA 试用」§四「先接素材面」· 老板批）：新面 `梦中月水中花`
        #   真源 ＝ `11_实验室/记忆` —— 皆**插件产出**（`梦_*.md` 做梦读数 ／ `唤醒_*.md` 唤醒(体检)读数）· ⛔ 非我测。
        #   ⇒ `role: archive`（**我们之报述** 之族 ⇒ ⛔ 作据 · 仍可检索回指 · 承 PM 846 §二）。
        #   ⚠ 根 ＝ **既有**面：`11_实验室/记忆/` 系 PM `955`／`956` 准我之**跨面子面**（父面属主 ＝ 工作流实验室席 `e621c26`）
        #     ⇒ 只读 · ⛔ 写 · glob 特指 ⇒ 天然排除 `.唤醒水位` 等点件与 `待做梦_*` 备料。
        ("梦中月水中花", (_rel_under(_FACE_VR, "内容工坊/11_实验室/记忆"),),
         ("梦_*.md", "唤醒_*.md")),
        # ⭐ 2026-10-05（PM b136893 令「M1 接线收口：加两个素材面」§二 ⒜ · 老板 20:0x 之纠后）：
        #   新面 `文件·产出` —— **文本产出**（`10_产出` ／ `dsh` ／ `_交付`）⇒ `role: archive`
        #   （**只索引 · ⛔ 作据** · 承 PM 846 §二）。
        #   ⚠ **名 ⛔ 取 `文件`** —— 由：`PA_FACE_ROLE` ／ `PA_FACES_MIN_ROW` 皆**按名取** ⇒ 与本表**既有**之
        #     `文件`（`<workspace>` · `knowledge`）**撞名** ⇒ 一面二义：改 `archive` ⇒ 撤 `q07` 之
        #     真据行（`项目经理_角色卡.md:71` · 承 L152 之注）；改 `knowledge` ⇒ 产出（我们之报述）入据
        #     ＝ 循环取证。⇒ 故取 `文件·产出`（承本表 `台账·信通` 之「大类·子类」之形）—— **候裁名**（承 1048 §三）。
        #   ⚠ **图产出 ⛔ 入本表** —— 本表之列 ⛔ 能表「目录级聚合」（PM §二 ⒝ 之裁）；且 `_cached_lines`
        #     读图 ⇒ `None` ⇒ 该面恒 `0` 件 ＝ **假绿之面** ⇒ 图面走 `PA_SRC_FACES` ＋ `GET /v9/pa/source_faces`。
        ("文件·产出", tuple(x for x in (_rel_under(_FACE_VR, "内容工坊/10_产出"),
                                      _rel_under(_FACE_VR, "dsh"), _rel_under(_FACE_WS, "_交付")) if x), ("*.md",)),
        # ⭐ 2026-10-05（PM 22:34 §二 裁「闸面余 9 件」· 逐件列判 ⇒ **唯此一件入闸**）：
        #   判据（PM 定）：**本机有据 ∧ ⛔ 无 GET 面 ⇒ 入闸**；有 GET 面者 ⇒ 归「另路」。
        #   逐件判：余 8 件皆有 GET /v9/pa/*（ledger ／ deliver/mail ／ caliber ／ roster ／
        #     seats ／ roster(probe 二键) ／ resume ／ threads）⇒ ⛔ 入闸；唯 deadfile_ledger.json
        #     **无任何路由**（rg dead core/pa/gateway_routes.py ⇒ 0 命中）⇒ **入闸**。
        #   ⚠ 根取 _data_dir()（与 DecisionStore 一处口径 · ⛔ 另立绝对径 ⇒ 免「两真源」）。
        ("死件账", (_data_dir(),), ("deadfile_ledger.json",)),
    )
    # ⭐ 2026-10-06（pm_1409 §二.3）：`PA_ORG_FACES` 门（**功能级** · 默认关 ⇒ 其径逻辑 ⛔ 执行）。
    #   本表七面中唯 `死件账` 为**产品面**（本机 `data/` 之账 · 与组织物无关）；余六面
    #   （文件 ／ 台账 ／ 平台台账 ／ 台账·信通 ／ 梦中月水中花 ／ 文件·产出）皆**组织物**
    #   （我方工作区 ／ 台账 ／ 信通 ／ 实验室 ／ 产出）⇒ 净机 ⛔ 得读 ⇒ 门关即 ⛔ 入表。
    #   ⚠ **关**时之面集 ＝ `收件箱` ／ `知识库`（`PA_KB_ASK_SCOPES` · vault 相对 · 用户自选库）
    #     ＋ `死件账`（本表产品面）。⚠ **面之数之变须报**（⛔ 静默减面）：响应附 `faces_gate`。
    # ⚠ 缺基（`_FACE_WS` ／ `_FACE_VR` ＝ `None`）⇒ 该面 ⛔ 入表（⛔ 空径 ⇒ 误扫 cwd · 承 pm_1409 §二.3）。
    # ⚠ 空根（全缺基）亦 ⛔ 入表 —— `all(())` 恒真 ⇒ 须并判 `ff[1]` 非空
    #   （否则该面以「0 件」上屏 ＝ **假绿之面** · 承本表 L323 之注）。
    _PA_FACES_ORG = tuple(ff for ff in _PA_FACES_ORG if ff[1] and all(x for x in ff[1]))
    _PA_FACES_ORG_ONLY = tuple(x for x in _PA_FACES_ORG if x[0] != "死件账")
    _PA_FACES_PRODUCT = tuple(x for x in _PA_FACES_ORG if x[0] == "死件账")
    PA_FACES = (_PA_FACES_ORG_ONLY + _PA_FACES_PRODUCT) if org_enabled() else _PA_FACES_PRODUCT
    PA_FACES_GATE = "org" if org_enabled() else "product"
    return PA_FACES, PA_FACES_GATE
# ⚠ 语料卫生（2026-10-04 · 三改 · 我引入之风险之修）：
#   一改曾把「台账」面设成整个 `_auto\deliver` ⇒ 我之报告**逐字引用**测试问题（如
#   `N1 | 我的老板叫什么名字 | ✅ 如实未答`）⇒ 2-gram 命中 `1.0` ⇒ **拒答面被冲垮**（假有据）。
#   ⇒ 故：⒜ 台账面只取台账本身 ⒝ 文件面**排除 `_auto`**（我之报告 ／ 派件集）⒞ 扩面之阈值独立抬高。
PA_FACES_SKIP = (".git", "node_modules", "__pycache__", ".pytest_cache", "store-assets",
                 "_tmp", "_tools", "_seats", "_pm", "_cdp_profile", "_out", "_auto",
                 # ⭐ pm_1569 §四.1（剔之准随族 · ⛔ 一刀切）：**测试残渣之形** —— --basetemp 落
                 #   根面之新名（ptmp1564 …）曾入检索面（14 件 fixture ⇒ 抖印 ∧ 假有据之口）。
                 "ptmp*")
# ⭐ pm_1569 §四.2（剔之准 ⛔ 随族）：**我方之报告 ／ 派件集** —— 按**件名之前缀族**剔
#   （⛔ 唯目录名 _auto 一据 ⇒ 根面之同族件漏 · 承 L154 ／ L514 之族）。
#   量（我一手器取）：文件面 95 件中 **32 件** 属此族（根 31 ＋ reports 1）⇒ 我方之报述入据
#   ＝ **假有据**。⚠ 唯「文种前缀」之族 · ⛔ 扩面：凡**知识之件**皆留（英文调研 ／ *纪要 ／
#   *报告 ／ 项目经理_角色卡）。
PA_FACES_SKIP_PREFIX = ("作废_", "回执_", "作战单_", "发表_", "投递_", "派单_", "请求_",
                        "申请_", "讲解_", "对表_", "点选表_", "素材_", "方案_", "设计方案_",
                        "外采集_", "外线风险登记_")


def _face_skip_name(name):
    u"""目录名 ⇒ 剔否（**一处定形** · pm_1569 §四.1）—— 精确名 ∨ 通配形（ptmp*）。

    ⚠ 旧形 e.name in PA_FACES_SKIP 唯精确 ⇒ ptmp1564 之流**漏剔**（残渣入面 ⇒ 抖印 ＋ 假有据）。
    """
    if name in PA_FACES_SKIP:
        return True
    import fnmatch                     # ⭐ 局部导入（本模块级 ⛔ 增导 · 承 L22 之族）
    return any(("*" in _p or "?" in _p) and fnmatch.fnmatch(name, _p) for _p in PA_FACES_SKIP)
PA_FACES_MIN_SCORE = {"文件": 0.5, "台账": 0.5, "台账·信通": 0.5}
# ⭐ PM 2026-10-05（承 技总 973 §三 · `v3`）：行侧阈按面可配
#   由：散文面（平台台账 ／ 文件）之长行 ⇒ 行侧覆盖天然低（真答案行 rcv ≈ 0.05–0.11）
#   ⚠ ⛔ 动问侧阈（降阈 ⇒ `v1`／`v2` 造新假有据 · 其一手实证）
PA_FACES_MIN_ROW = {"平台台账": 0.05, "收件箱": 0.05, "文件": 0.05,
                    # ⭐ 2026-10-05（PM 22:34 §二）：死件账 —— 其行为**结构化 JSON**（径 ／ 键），
                    #   ⛔ 散文 ⇒ 行侧覆盖天然低 ⇒ 默认 0.42 会**恒杀**（实测：默认 0 中）。
                    #   ⚠ **唯降行阈 · ⛔ 动问阈**（降问阈 ＝ 扩假有据面 ⇒ 与「扩面之阈值独立抬高」相反）；
                    #   实测：行阈 0.05 ⇒ 应拒之问（老板叫什么 …）**死件账 0 中**（⛔ 假有据）。
                    "死件账": 0.05}
# ⭐ PM 2026-10-05（承 技总 974 §二 · `v4` ＋ 我之并裁）：剔名后 `qg` 同缩 ⇒ **原真据之 `rcv` 亦降**
#   实证：`q07` 之首据 `收件箱/PA待办与进度.md:13` 之 `rcv 0.440 ⇒ 0.364` ⇒ **被行阈所杀**（真据成假阴）
#   ⇒ 故 `收件箱` 入表；并 `文件`（同族 · 且 `q07` 之真答案行 `项目经理_角色卡.md:71` 借此回位）
#   ⚠ 问侧阈 ⛔ 动（承 L166）；改此表 ⇒ `PA_FACES_VERSION` 必 +1（承 L152）
# ⭐ 语料名（判别力 ≈ 0 之 bigram）：问含其名 ⇒ 该 bigram 满布全库 ⇒ 结构性压低 cov ⇒ 剔之
PA_CORPUS_NAME_BIGRAMS = ("内容工坊",)
# ⭐ 面级角色（PM 846 §二.1 · 承 L154）：archive ⇒ ⛔ 计「有据」（仍可检索 ⇒ 另键报出）
#   由：档案面之内容 ＝ **我们之报述**（含问句样本）⇒ 以之作据 ＝ 循环取证（实证：同一问之「据」＝ PM 之报述）
PA_FACE_ROLE = {"收件箱": "knowledge", "知识库": "knowledge",
                "文件": "knowledge", "台账": "archive", "台账·信通": "archive",
                "平台台账": "knowledge", "梦中月水中花": "archive",
                # ⭐ 2026-10-05：文本产出面（PM「M1 接线收口」§二 ⒜）⇒ archive（只索引 · ⛔ 作据）
                "文件·产出": "archive",
                # ⭐ 2026-10-05（PM 22:34 §二）：死件账 ⇒ knowledge —— 由：其内容 ＝
                #   **对盘之事实读数**（死件 ／ 被拖死之件 ／ 登记之谎 ⇒ 逐条带径与由），
                #   ⛔ 「我们之报述」（⚠ 承 846 §二：archive 之义 ＝ 报述含问句样本 ⇒ 循环取证）；
                #   ⚠ 此为**我之判** ⇒ 候 PM 核（改 archive 仅一行 · ⛔ 动骨架）。
                "死件账": "knowledge"}
# ⭐ 面册 ＋ 角色 ＋ 阈 之版本（改此三物 ⇒ 必 +1 · 承 PM 845 §二.1 · L152）
PA_FACES_VERSION = "2026-10-06.11"   # ⭐ .11（pm_1569 §四）：扫面之剔（PA_FACES_SKIP 增 ptmp* ＋ 新 PA_FACES_SKIP_PREFIX「报告 ／ 派件」族）＋ searched 改**唯一件数**（＋ searched_roles ／ searched_scans）⇒ +1（承 L152）｜ ⭐ .10：`PA_ORG_FACES` 门（关 ⇒ 唯产品面 `死件账`）⇒ +1（承 L152）｜ ⭐ .9：元问路（context_missing）之答话 ＋ 死件路「账不可读」之界（PM 1183 §五.1 ／ §八 · 我 1057）⇒ 仍 +1｜⭐ .8：死件账之**直读路**（PM 22:34 §三① 准 · 条件⒟）⇒ 仍 +1（承 L152）｜⭐ .7：面表＋角色表增「死件账」（PM 22:34 §二 裁）｜⭐ 2026-10-05：面表＋角色表增 `文件·产出`（PM「M1 接线收口」§二 ⒜）⇒ 皆 +1
# ⭐ 问域类（PM 846 §三 ／ 847 §五 · 承 L151）：元 ／ 指代 ／ 重复 ／ 上文 ⇒ 走**会话路**（⛔ 进检索闸）
#   ⚠ 轴之分（PM 裁 · 承 L83）：本轴（`meta` ／ `retrieve`）管**路由**；前端 `paAskDomain` 管**自述 ／ 本机 ／ 世界** ⇒ 两轴各管其段（⛔ 二处各判同一物）
PA_ASK_META_KW = ("上一条", "上一句", "上一问", "前一句", "刚才", "原样重复",
                  "重复一遍", "再说一遍", "我问的是什么", "我问了什么", "第几问", "你说过")
PA_ASK_FORCE_KW = ("检索：", "检索:", "@ask")   # ⭐ 退路（与前端同形 · 承 L123）
# ⭐ 排除式（PM 2026-10-05 · 我一手逮之假阳）：**索引类**问（「第几问…」）要的是**索引**
#   ⇒ 归检索面（保守）· ⛔ 拿「上一句」糊弄（承 L150：判据须以「相关」为准）
PA_ASK_META_NOT = ("第几问", "哪一问", "哪一条", "哪句提到", "哪一轮", "哪次")
# ⭐ 自测痕之标（PM 2026-10-05 · 承 L159）：用户可引之面 ⛔ 含开发痕
#   实证：老板问「我上一条问的是什么」⇒ 答出「端到端自检：今天场地研判的结论是什么」（我方 E2E 之键入）
PA_SELFTEST_MARKS = ("（自测）", "端到端自检", "探针 OK", "E2E 自检", "selftest")

# ⭐ 2026-10-05（PM 20:56 §二 修① · 老板实测之洞之修）：**决策账面入闸**。
#   病（老板一手 · session_pa_muv1gdty）：本机 decision_log.json 确有 d1791202075323（note 在）
#   而闸报「本机无据」⇒ 拒答 ⇒ **回落模型 ⇒ 编造／冒认**（答「T1已完成」／「查不到」）。
#   ⇒ 修：凡问含 **decision_id 之形（d\d{13}）** ∨ **「决策记录」之族** ⇒ **直取本机决策账**
#     （data\v9\pa\decision_log.json ⇒ DecisionStore）⇒ ⛔ 回落（承「断『无』须先扫其体」）。
PA_ASK_DECISION_ID_RE = r"d\d{13}"
PA_ASK_DECISION_KW = ("决策记录", "决策日志", "决策账", "拍板记录", "decision log", "decision_log")
# ⭐ PM 2026-10-05 22:34 §三①（准）：**死件账之直读路**之判据表 —— 「逐字入件」（PM 条件⒜）
#   ⒜ 关键字表（问含任一 ⇒ 本路）
PA_ASK_DEADFILE_KW = ("死件", "缺件", "登记之谎", "deadfile", "dead_file", "缺源")
#   ⒝ 名中：唯「**该账已录之名**」（真缺[].value ／ 真缺[].yaml 之 basename ± 扩展）⇒ 见 _ask_deadfile
#   ⚠ 账之真源（一处口径 · 与 1055 之入面表同径）
PA_ASK_DEADFILE_LEDGER = "deadfile_ledger.json"
# ⭐ 第六改（2026-10-04 · PM 自引入之 bug 之修）：逐面尺寸闸 —— 台账类件**天生大**
#   （投递台账.csv 已 2,525,801 B > 2 MiB ⇒ 旧闸致该面「既⛔收亦⛔计件」＝死面）
PA_FACES_MAX_BYTES = {"文件": 2 * 1024 * 1024, "台账": 16 * 1024 * 1024, "台账·信通": 16 * 1024 * 1024}
PA_FACES_DEFAULT_MAX_BYTES = 2 * 1024 * 1024
PA_FACES_MAX_FILES = 4000


def _kb_fingerprint(path, limit=KB_FINGERPRINT_MAX_BYTES):
    """内容指纹（验收-A）：sha256 前 16 位。取不到 / 超限 ⇒ None（判「未知」，不猜）。"""
    import hashlib

    h = hashlib.sha256()
    n = 0
    try:
        with open(path, "rb") as f:
            while True:
                b = f.read(1 << 20)
                if not b:
                    break
                n += len(b)
                if n > limit:
                    return None
                h.update(b)
    except Exception:
        return None
    return h.hexdigest()[:16]


def _jsonl_lines(path):
    """非空行数。落盘回执就这么算：看盘上多没多一行，而不是信任代码里那句「我写了」。

    ⚠ 2026-09-29（PM 裁「该修」· 承 437 假绿 / 验收-B「过期 0」同族）：**读不到 ≠ 0**。
      旧实现 ``except: return 0`` 把「读不了」报成「是空的」——0 看起来像读数：
      实测（独占锁 events.jsonl）回执里出现 ``events_lines_before: 0``，而**真实是 131**。
      ⇒ 现口径：**文件真不存在** ⇒ 0（真空，是读数）；**存在但读不了** ⇒ ``None``（不可得）。
    """
    try:
        with open(path, "rb") as f:
            return sum(1 for ln in f if ln.strip())
    except FileNotFoundError:
        return 0
    except Exception:
        return None


def _lines_delta(before, after):
    """行数差。任一读不可得 ⇒ None（⛔ 不是 0：0 会被读成「没变化」= 又一个假读数）。"""
    if before is None or after is None:
        return None
    return after - before


def _bigrams(t):
    s = "".join(ch for ch in str(t or "") if ch.strip())
    if not s:
        return set()
    return set(s[i:i + 2] for i in range(len(s) - 1)) if len(s) > 1 else set((s,))


def _face_root(kb_root, spec):
    """面之根：常量绝对径 ／ "@vault:" 前缀（vault 内相对）。⛔ 用户输入。"""
    spec = str(spec)
    if spec.startswith("@vault:"):
        return Path(kb_root) / spec[len("@vault:"):]
    return Path(spec)


_LINE_CACHE = {}
_LINE_CACHE_MAX = 3000   # ⭐ pm_1569 §五：上限入常量（旧为字面 3000 · 无淘汰 ⇒ 满则新件永不入）


def _cached_lines(p):
    """按 (path, mtime_ns, size) 缓存行表 ⇒ 复问不重读盘（承「好用」之要求）。

    ⚠ pm_1549 §一.2：粒度**从 ns**（旧 `int(st.st_mtime)` ＝ 秒）—— 同秒内同长之改写
      ⇒ 行表读旧（与「印」不同轴 ⇒ 印变而读旧 ＝ **假新鲜**）。"""
    try:
        st = p.stat()
        k = (str(p), st.st_mtime_ns, st.st_size)   # ⭐ pm_1549 §一.2：**ns**（旧＝秒 ⇒ 同秒同长之改写 ⇒ 读旧）
    except Exception:
        return None
    v = _LINE_CACHE.get(k)
    if v is not None:
        _lru_put(_LINE_CACHE, k, v, _LINE_CACHE_MAX)   # ⭐ pm_1569 §五：命中提为最新（真 LRU）
        return v
    try:
        txt = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
    v = txt.splitlines()
    # ⭐ pm_1569 §五（同族 · 一并）：满 ⇒ 逐最旧（⛔ 旧形「满则新件永不入」）
    _lru_put(_LINE_CACHE, k, v, _LINE_CACHE_MAX)
    return v




def _nows(t):
    u"""去空白 —— 与 `_bigrams()` 之剔法**同源**（`ch.strip()` 为假者皆白）。

    ⚠ 本模块级 ⛔ 增导 `re` ⇒ **局部导入**（承 L22 之族：新导须明其由 · `re` 自缓存所编之式）。
    """
    import re
    return re.sub(r"\s+", "", t)


def _inter_fast(qg, ln, all2):
    u"""⭐ 降本条 ⓑ（先判后算）：**⛔ 建行侧 bigram 集** 即得 `inter`（⛔ 返 `None` 时由调用方回落旧法）。

    `inter` ＝ 问侧 bigram 中**出现于**该行者之数 —— 于「问侧诸元皆 2 字 ∧ 行去白后 ≥ 2 字」时，
    行侧之 bigram 集 ≡ 行**去白后**之 2-gram 集（⚠ 去白会**跨空白**造 2-gram ⇒ 故先 `_nows`）：
    2 字之 `b` ⇒ `b in s` ⟺ `b ∈ _bigrams(ln)`。
    ⛔ 适用条件不成立（问侧含 1 字元 ∨ 去白后 < 2 字）⇒ 返 `None` ⇒ **回落旧法**（⛔ 猜 · 承 L124）。
    """
    if not all2:
        return None
    s = _nows(ln)
    if len(s) < 2:
        return None
    return sum(1 for b in qg if b in s)


def _face_files(root, globs):
    u"""面内文件（⛔ 穿越 · 跳过工程目录 · 有上限）—— 只读列举。

    ⭐ 2026-10-05（降本条 ⓐ · 先判后算）：**剪树列举** —— 入目录前即剔 `PA_FACES_SKIP`。
    由：旧法走**全树**（含 `_tmp` ／ `_tools` ／ `.git` …）再逐件按相对径剔 ⇒ 列举即 **0.865 s**
    （实测 · 六面 141 件之面）⇒ 剪树 ⇒ **0.015 s**（同机同刻）。
    ⭐ 件集与**序** ⛔ 变：仍**逐通配**各 `sorted`（＝旧法之逐 `pat`）⇒ 实测六面**逐件逐序同**。
    ⚠ 界：⛔ 随目录符号链接（旧法 `rglob` 亦不随 · 本树无此物 ⇒ 六面实测同）。
    """
    out = []
    try:
        root = Path(root)
        if not root.is_dir():
            return out
    except Exception:
        return out
    import fnmatch                      # ⭐ 局部导入（本模块级 ⛔ 增导 · 承 L22 之族）
    found = []
    stack = [root]
    while stack:
        d = stack.pop()
        try:
            with os.scandir(d) as it:
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=False):
                            if _face_skip_name(e.name):
                                continue
                            stack.append(Path(e.path))
                        else:
                            # ⭐ pm_1569 §四.2：**件名之前缀族**（我方之报告 ／ 派件集）⇒ 剔（⛔ 入面）
                            if any(e.name.startswith(_sp) for _sp in PA_FACES_SKIP_PREFIX):
                                continue
                            found.append(Path(e.path))
                    except OSError:
                        continue
        except OSError:
            continue
    for pat in globs:
        for p in sorted(x for x in found if fnmatch.fnmatch(x.name, pat)):
            out.append(p)
            if len(out) >= PA_FACES_MAX_FILES:
                return out
    return out


# ⭐ 2026-10-05（PM b136893 令「M1 接线收口：加两个素材面」§二 ⒝ ＋ 其「一律」）：
#   **画像素材面（左栏「来源面」之七面）之读数** —— ⛔ 检索面（`PA_FACES`）⇒ **两轨两名分列**（承 selfdesc「面之差」）。
#   由（PM §二 之裁）：⭐ **面之粒度须与量相称** —— 文本件可**逐件**；图件（千张量级）**按目录聚合**（面 ⛔ 爆）。
#   ⇒ 每面给：`kind` ／ 根（逐字）／ glob（逐字）／ 量 ／ **聚合之式（逐字）** ／ 最近刻 ／ 印。
#   ⚠ `role: archive` —— 产出 ＝ **我们之报述**之族 ⇒ ⛔ 作据 · 只索引 · 承 PM 846 §二。
# ⭐⭐ pm_1520 §二.3（甲 · 件三）：同病之**同轴兄弟**（本表亦取 `_FACE_VR` ／ `_FACE_WS`）——
#   ⇒ 一并惰算（⛔ 穷扫：唯同轴之此一表 · 承 pm_1517 §三.2 之记债）。
def _src_faces_tables():
    u"""（PA_SRC_FACES, PA_SRC_FACES_GATE）—— **惰算**（同上 · 一处定形）。"""
    _FACE_WS = ws_root()
    _FACE_VR = vault_root()
    _PA_SRC_FACES_ALL = (
        # ⒜ 「📄 文件」（前端 today.js:159 `srcRowFile`）—— 文本产出 · **逐件计数**
        ("文件", "archive", "files", ("*.md",),
         tuple(x for x in (_rel_under(_FACE_VR, "内容工坊/10_产出"), _rel_under(_FACE_VR, "dsh"),
                           _rel_under(_FACE_WS, "_交付")) if x),
         "张数＝<根> 递归之 (*.md)（剔 PA_FACES_SKIP 之名）", "文件·产出"),
        # ⒝ 「🎨 出图」（前端 today.js:161 `srcRowDraw`）—— 图产出 · **按目录聚合**（⛔ 逐张 · 千张量级）
        ("出图", "archive", "dirs", ("*.png", "*.jpg", "*.jpeg", "*.webp", "*.gif", "*.svg"),
         tuple(x for x in (_rel_under(_FACE_VR, "内容工坊/10_产出"), _rel_under(_FACE_VR, "工作区/项目")) if x),
         "张数＝<根> 递归之 (png|jpg|jpeg|webp|gif|svg)（剔 PA_FACES_SKIP 之名）· 按目录聚合", None),
    )
    # ⭐ 2026-10-06（pm_1409 §二.3）：`PA_ORG_FACES` 门 —— 本表二面皆**组织物**（`10_产出` ／
    #   `dsh` ／ `_交付` ／ `工作区\项目`）⇒ 门关（默认）即**空表**（响应的 `面之数` ＋ `门` 照实报）。
    _PA_SRC_FACES_ALL = tuple(ff for ff in _PA_SRC_FACES_ALL if ff[4])   # 缺基 ⇒ ⛔ 入表（同上）
    PA_SRC_FACES = _PA_SRC_FACES_ALL if org_enabled() else ()
    PA_SRC_FACES_GATE = "org" if org_enabled() else "product"
    return PA_SRC_FACES, PA_SRC_FACES_GATE
PA_SRC_FACES_VERSION = "2026-10-06.4"   # ⭐ .4：`PA_ORG_FACES` 门（关 ⇒ 空表）⇒ +1（承 PA_FACES_VERSION 之律）｜ ⭐ .3：加「面级之印」（响应之形变 ⇒ 亦 +1）   # ⭐ 改本表 ⇒ 必 +1（承 PA_FACES_VERSION 之律）

# ============================== ⭐ UI 面册（承 pm_1384 §二.1 ／ §三.1）==============================
#: ⭐ **真源 ＝ 盘上**（`web/pa/faces/*.js` · 剔 `*.before_*`）；**旁源** ＝ `web/pa/faces.json`（title ／ 旧面册）。
#:   名之分（PM 1384 §二.1 之裁）：既有 `/v9/pa/source_faces` ＝ **源之面**（文件 ／ 出图 · 素材）
#:   ⟷ 本者 ＝ **UI 面册**（前端之面之册）⇒ **二物 ⛔ 同轴** ⇒ ⛔ 撞名（承「一名一义」）。
_UI_REPO = Path(__file__).resolve().parents[2]
UI_FACES_DIR = _UI_REPO / "web" / "pa" / "faces"
UI_FACES_MANIFEST = _UI_REPO / "web" / "pa" / "faces.json"
PA_UI_FACES_VERSION = "2026-10-06.1"   # ⭐ 改本表之式 ／ 响应之形变 ⇒ 必 +1（承 PA_SRC_FACES_VERSION 之律）


def _ui_face_files():
    u"""盘上之面（**真源**）：`web/pa/faces/*.js`（剔 `*.before_*` 之底）⇒ 排序之 `[(id, file)]`。

    `file` ＝ **相对** `web/pa/` 之径（如 `faces/chat.js`）—— ⛔ 绝对径入面（⛔ 本机之径上屏）。
    """
    out = []
    try:
        for _p in sorted(UI_FACES_DIR.glob("*.js")):
            _n = _p.name
            if _n.startswith(".") or ".before_" in _n:
                continue
            out.append((_n[:-3], "faces/" + _n))
    except Exception as _e:
        logger.warning("ui_faces: 盘上之面不可读: %s: %s", type(_e).__name__, str(_e)[:200])
    return out


def _ui_route_norm(s):
    u"""路由之归一：剔 `<…>` 之参段 ＋ 去尾 `/`（⛔ 参形歧义）。"""
    return "/".join(x for x in str(s).split("/") if not (x.startswith("<") and x.endswith(">"))).rstrip("/")


def _ui_route_set():
    u"""既有 `/v9/pa/*` 路由集 —— **活读** `url_map`（承 pm_1384 §三.1「须在既有路由集内」）。

    ⚠ ⛔ 手列（手列必与实漂）：无应用上下文（如单测直调本函）⇒ **回落本档之源扫**（同器之真源）。
    """
    rs = set()
    try:
        from flask import current_app
        for _r in current_app.url_map.iter_rules():
            _s = str(_r.rule)
            if _s.startswith("/v9/pa"):
                rs.add(_s)
    except Exception:
        rs = set()
    if not rs:
        try:
            import re as _re
            with open(__file__, "r", encoding="utf-8") as _fh:
                for _m in _re.finditer(r'"(/v9/pa[^"]*)"', _fh.read()):
                    rs.add(_m.group(1))
        except Exception:
            pass
    return rs


def _ui_route_known(cand, rs):
    u"""`cand` 是否在既有路由集内（**等** 或 **前缀** · ⛔ 悬）。"""
    _n = _ui_route_norm(cand)
    if not _n:
        return False
    for _r in rs:
        _rn = _ui_route_norm(_r)
        if _rn == _n or _rn.startswith(_n + "/"):
            return True
    return False


def _ui_face_requires(pid, rs):
    u"""⭐ 面之源里所引之 `/v9/pa/*`（**器取** · ⛔ 手列）⇒ `(在既有路由集内, 悬)`。

    ⚠ 源扫之式（两条 · 皆自 `more.js` ／ `archive.js` 之实读得来）：
      ⒜ **先剔注**（`/*…*/` ／ 行 `//`）—— ⛔ 则「注里提到某路由」被读成「引用」
         （实例：`more.js` 之注书「⛔ 自造 `/v9/pa/agents`（该名已撤）」⇒ 剔注方为真）；
      ⒝ 只取**完整之字面**（引号包裹 · 可带查询串）—— ⛔ 取模板串里之片段
         （实例：`archive.js` 之注述 `threads_<uid>.json` ⇒ ⛔ 路由）。
    """
    import re as _re
    try:
        raw = (UI_FACES_DIR / (pid + ".js")).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return [], []
    src = _re.sub(r"/\*.*?\*/", "", raw, flags=_re.S)
    src = _re.sub(r"(?m)^[ \t]*//[^\n]*$", "", src)
    src = _re.sub(r"(?m)(?<![:/])//[^\n]*$", "", src)
    _Q = chr(39) + chr(34) + chr(96)      # 引号三形： ' ｜ " ｜ `（⛔ 直书以避源之引号纠缠）
    _REQ_RE = "[" + _Q + "](/v9/pa/[A-Za-z0-9_/]*)(?:\\?[^" + _Q + "]*)?[" + _Q + "]"
    cand = sorted(set(_re.findall(_REQ_RE, src)))
    hit = [c for c in cand if _ui_route_known(c, rs)]
    miss = [c for c in cand if not _ui_route_known(c, rs)]
    return hit, miss


def _ui_faces_readout():
    u"""⭐ UI 面册之读数（**只读** · 承 pm_1384 §三.1）。

    `面之数` ≡ `web/pa/faces/*.js`（剔 `*.before_*`）之数（**判成 ⒞**）；`requires` 逐条**已在**既有
    `/v9/pa/*` 路由集内（⛔ 悬）；「旁源」（`faces.json`）之**对映漂** 照实报（⛔ 静默 · ⛔ 以旁源代真源）。
    """
    import json as _json
    from time import strftime as _stf
    rs = _ui_route_set()
    files = _ui_face_files()
    man, man_err = {}, None
    try:
        with open(UI_FACES_MANIFEST, "r", encoding="utf-8") as _fh:
            for _f in ((_json.load(_fh) or {}).get("faces") or []):
                if _f.get("id"):
                    man[_f["id"]] = _f
    except Exception as _e:
        man_err = "%s: %s" % (type(_e).__name__, str(_e)[:120])
    faces, miss_all = [], {}
    for _pid, _rel in files:
        _req, _miss = _ui_face_requires(_pid, rs)
        _m = man.get(_pid) or {}
        faces.append({"id": _pid, "title": _m.get("title"), "file": _rel, "requires": _req,
                      "title_src": ("web/pa/faces.json" if _m.get("title") else None)})
        if _miss:
            miss_all[_pid] = _miss
    ids, mids = set(f["id"] for f in faces), set(man)
    return {
        "ok": True,
        "at": _stf("%Y-%m-%d %H:%M:%S"),
        "version": PA_UI_FACES_VERSION,
        "面之数": len(faces),
        "faces": faces,
        "悬": miss_all,
        "对映": {
            "真源": "web/pa/faces/*.js（盘上 · 剔 *.before_*）",
            "旁源": "web/pa/faces.json",
            "旁源之数": len(mids),
            "旁源 open:false（⛔ 计面）": sorted(i for i in mids if man[i].get("open") is False),
            "旁源多出（⛔ 盘上无件）": sorted(mids - ids),
            "旁源缺（盘上有件）": sorted(ids - mids),
            "旁源之读": ("不可读：" + man_err) if man_err else "可读（唯取 title；⛔ 以之代真源之面数）",
        },
        "路由集": {"数": len(set(_ui_route_norm(r) for r in rs)),
                   "式": "current_app.url_map 之 /v9/pa*（无上下文 ⇒ 回落本档源扫）"},
        "口径": "UI 面册（web/pa/faces/*.js）之面之数 ＋ 逐面所引 /v9/pa/*；⛔ 源之面（source_faces 之素材两轨）· 二物 ⛔ 同轴",
    }

def _src_face_readout():
    u"""画像素材面之读数（**只读** · ⛔ 起子进程 ⇒ 常闸 `rc 0` · ⛔ 写盘 · ⛔ 读图内容（只 scandir ＋ stat））。

    ⭐ 粒度（PM 2026-10-05 §二 之裁）：`kind == "files"` ⇒ **逐件**（每根一件数）；
    `kind == "dirs"` ⇒ **目录级聚合**（目录 ＋ 张数 ＋ 最近刻 ＋ **图印**）⇒ ⛔ 逐张入面。
    ⭐ **图印**（我定 · 待裁 —— 承「数须附式」）：该目录内诸件「名 ＋ 制表 ＋ 字节」排序连缀之 sha256[:16]
    ⇒ **增／删／换一件 ⇒ 印变**（⛔ 只数件数 · 承「弱保证 ≠ 真闸」）。
    ⚠ 缺根 ⇒ 明标 `缺根`（⛔ 只报 0 ⇒ 会被读成「无料」· 承 `_scan`）。
    ⭐ 2026-10-05（PM 20:28 令 §二）：**逐面之印** —— 每面出 `印`（面名 ＋ 根 ＋ glob ＋ 逐行
    （本表面名 ⇒ `PA_FACES` 面名 · None ＝ 该面⛔入检索面）＋ 顶层 `对映` ／ `PA_FACES名`
    ⇒ ⛔ 靠人记（承「一名一义」∧「一物两名须明书」）。
    """
    import hashlib as _hl
    import collections as _cy
    from time import strftime as _stf, localtime as _lt
    _at = _stf("%Y-%m-%d %H:%M:%S")
    faces = []
    for name, role, kind, globs, roots, form, mirror in pa_src_faces():
        rows = []
        missing = []
        total = 0
        for root in roots:
            if not Path(root).is_dir():
                missing.append(root)          # ⭐ 缺根 ⇒ 明标（⛔ 只报 0 件）
                continue
            files = _face_files(root, globs)
            if kind == "files":
                rec = None
                _bytes = 0
                for p in files:
                    try:
                        st = p.stat()
                    except OSError:
                        continue
                    _bytes += st.st_size
                    if rec is None or st.st_mtime > rec[0]:
                        rec = (st.st_mtime, p.name)
                rows.append({"root": root, "count": len(files), "字节": _bytes,
                             "recent": (_stf("%Y-%m-%d %H:%M:%S", _lt(rec[0])) if rec else None),
                             "recent_name": (rec[1] if rec else None)})
                total += len(files)
            else:
                bydir = _cy.defaultdict(list)
                for p in files:
                    bydir[str(p.parent)].append(p)
                for d in sorted(bydir):
                    ps = sorted(bydir[d])
                    _h = _hl.sha256()
                    mt = 0.0
                    _bytes = 0
                    for p in ps:
                        try:
                            st = p.stat()
                        except OSError:
                            continue
                        _h.update(("%s\t%d\n" % (p.name, st.st_size)).encode("utf-8"))
                        _bytes += st.st_size
                        mt = max(mt, st.st_mtime)
                    rows.append({"dir": d, "count": len(ps), "字节": _bytes,
                                 "recent": (_stf("%Y-%m-%d %H:%M:%S", _lt(mt)) if mt else None),
                                 "印": _h.hexdigest()[:16]})
                    total += len(ps)
        # ⭐ 面级之印（2026-10-05 · PM b136893 20:28 令 §二 之裁）：**该面之内容之印**
        #   ＝ 面名 ＋ 根 ＋ glob ＋ **本面逐行之（名＋制表＋字节）连缀** ⇒ `sha256[:16]`。
        #   由（PM）：⭐ **印须载「该面之真源」**（承 `PM-88` 之族）—— 面册之全印把
        #   「此面之数」与「他面之变」绑在一起 ⇒ 改他面 ⇒ 此面之印亦变 ⇒ **印失其用**。
        #   ⚠ **与面册之印（顶层 `印`）两键并存 · ⛔ 取代**（全印仍有其用＝**面册级之变**）。
        _hf = _hl.sha256()
        _hf.update(("%s|%s|%s|" % (name, "|".join(roots), "|".join(globs))).encode("utf-8"))
        for r in rows:
            _hf.update(("%s\t%s\t%s\t%s\t%s\n" % (
                r.get("root") or r.get("dir"), r.get("count"), r.get("recent"),
                r.get("recent_name") or r.get("印"), r.get("字节"))).encode("utf-8"))
        faces.append({"name": name, "role": role, "kind": kind, "roots": list(roots),
                      "glob": list(globs), "聚合之式": form, "对映检索面": mirror, "量": total,
                      "行之数": len(rows), "rows": rows, "缺根": missing,
                      "印": _hf.hexdigest()[:16]})
    _h2 = _hl.sha256()
    for f in faces:
        _h2.update(("%s|%s|%d|%s|" % (f["name"], f["kind"], f["量"], f["对映检索面"])).encode("utf-8"))
        for r in f["rows"]:
            _h2.update(("%s|%s|%s|%s\n" % (r.get("root") or r.get("dir"), r.get("count"),
                                           r.get("recent"), r.get("印"))).encode("utf-8"))
    return {"ok": True, "at": _at, "faces": faces, "faces_version": PA_SRC_FACES_VERSION,
            "面之数": len(faces), "门": pa_src_faces_gate(),
            "对映": {f["name"]: f["对映检索面"] for f in faces},
            "PA_FACES名": [x[0] for x in pa_faces()],
            "对映之式": "本表（画像素材面）面名 ⇒ PA_FACES（检索面）面名；None ＝ 该面⛔入检索面（图面：PA_FACES ⛔ 能表目录级聚合）",
            "印": _h2.hexdigest()[:16],
            "口径": "画像素材面（左栏「来源面」）之读数 · ⛔ 检索面（PA_FACES）· 两轨两名分列"}



# ⭐⭐ pm_1517 §一（裁：取拟一 ⇒ 改 `态` 之判据 ⇒ 以「PA 检索面」为准）：
#   病（我 1515 §三 之逮 · 一手）：旧判唯问 `note_kernel.face_state_code()`（＝**内核约定六面**
#     `notes/sop/reviews/inbox/drafts/assets` 之件数）⇒ 本机之组织库（`收件箱` 有物 ·
#     活端 `searched ＝ 540`）反报 `empty` ⇒ 前端据此渲「检索面为空」⇒ **屏上书不实**
#     （承「⛔ 屏上不实」之族）。
#   正解（pm_1517 §一 · **一处定形**）：其判**唯自 PA 检索面**出 —— `PA_KB_ASK_SCOPES`
#     （库根相对）＋ `PA_FACES` 中**以本库根为基**者之件数。
#   ⚠ **⛔ 纳他根之面**（如 `文件`＝工作区根 ／ `死件账`＝`data/` 面）—— 由：⒈、`态` 乃
#     **该键之根**之态（一名一义）⒉、`PA_FACES` 于净机（门关）唯 `死件账`（`data/` 面 ·
#     ⛔ 在本库根之下）⇒ 若纳之 ⇒ 净机亦报 `ok` ⇒ **反控 ⛔ 立**（pm_1517 §一.3）。
def _is_under_path(base, p):
    u"""`p` ⛔ 在 `base` 之下（皆绝对化 ＋ 大小写归一；⛔ 前缀误配 `kb` ⟷ `kb2`）。"""
    try:
        _b = os.path.normcase(os.path.abspath(str(base)))
        _p = os.path.normcase(os.path.abspath(str(p)))
    except Exception:
        return False
    if _p == _b:
        return True
    return _p.startswith(_b + os.sep)


def pa_vault_face_files(root):
    u"""本库根之 **PA 检索面**：⇒ `(件数, 命中面名…)`（判「态」用 · **一处定形** · pm_1517 §一）。

    ＝ `PA_KB_ASK_SCOPES`（库根相对 · `*.md`）＋ `PA_FACES` 中**根在本库根之下**者（各用其通配）。
    ⚠ 只读列举（`_face_files` ⇒ 剪树剔 `PA_FACES_SKIP`）；⚠ **⛔ 他根之面**（见上注）。
    """
    _r = Path(root)
    _n = 0
    _names = []
    for _rel in PA_KB_ASK_SCOPES:
        _c = len(_face_files(_r / _rel, ("*.md",)))
        _n += _c
        if _c:
            _names.append(_rel)
    for _name, _roots, _globs in pa_faces():
        _c = 0
        for _spec in _roots:
            _rp = _face_root(_r, _spec)
            if not _is_under_path(_r, _rp):
                continue
            _c += len(_face_files(_rp, _globs))
        _n += _c
        if _c:
            _names.append(_name)
    return _n, tuple(_names)


def pa_vault_state_code(root=None):
    u"""库根之「**态**」机器码（**一处定形** · pm_1517 §一 之裁 ⇒ 取拟一）。

    值域（一名一义 · 承 `pm_1503 §一`）：
      ``no_root`` —— 库根 ⛔ 得（四序皆无）
      ``empty``   —— 库根在 ∧ **本库根之 PA 检索面诸面皆无件**
      ``ok``      —— 有件
    ⚠ 其源**唯** `pa_vault_face_files()`（⛔ 另立判据 · ⛔ 内核约定六面 —— 二物别 · 报其读者）。
    ⚠ 传 ``root=None``（∨ 空）⇒ 自 `vault_root()`（四序 · 一处定形）。
    """
    from core.lib.note_kernel import (STATE_CODE_EMPTY, STATE_CODE_NO_ROOT,
                                      STATE_CODE_OK)
    _r = Path(root) if str(root or "").strip() else vault_root()
    if _r is None:
        return STATE_CODE_NO_ROOT, 0, ()
    _n, _names = pa_vault_face_files(_r)
    return (STATE_CODE_OK if _n else STATE_CODE_EMPTY), _n, _names


# ⭐ pm_1520 §二.1 ／ pm_1525 §一：`env_override` ＋ `note` —— **一处定形**（⛔ 二处各判）。
#   义：`PA_VAULT_DIR` 在 ⇒ 配置之写（`paths.vault_root`）**⛔ 生效**（env 居四序之首）⇒ 须**明书**
#     （⛔ 静默）—— `GET /v9/pa/first_run` 之「面之源」 ／ `POST /v9/pa/vault/set` 之回 **共用此源**。
PA_VAULT_ENV_KEY = "PA_VAULT_DIR"
PA_VAULT_ENV_NOTE = (u"本机之库根由环境变量 PA_VAULT_DIR 指定 ⇒ 你所选须清该变量方生效")


def vault_env_override():
    u"""(env_override, note) —— 一处定形（⛔ 二处各判 · 承 pm_1525 §一）。"""
    _on = bool((os.environ.get(PA_VAULT_ENV_KEY) or "").strip())
    return _on, (PA_VAULT_ENV_NOTE if _on else "")
# ============================== ⭐ 首启引导（承 pm_1384 §三.3）==============================
PA_FIRST_RUN_VERSION = "2026-10-06.6"   # ⭐ 判成之形变 ⇒ 必 +1（承 PA_UI_FACES_VERSION 之律）
#  ⭐ .6：「面之源」之 PA_VAULT_DIR 键 ⇒ 增 `env_override` ＋ `note`（pm_1525 §一 —— **一处定形**
#           `vault_env_override()` · 与 `POST /v9/pa/vault/set` 之回**同源**）：`env` 在 ⇒ 配置之写
#           **⛔ 生效**（env 居四序之首）⇒ 屏上须**明书**（⛔ 静默）。
#  ⭐ .5：「态」之判据 ⇒ 改依**本库根之 PA 检索面**（pm_1517 §一 之裁 · 取拟一）——
#           旧依「内核约定六面」⇒ 本机（`收件箱` 有物 · `searched＝540`）反报 `empty`
#           ⇒ 屏上不实；一处定形（唯问 `pa_vault_state_code()`）⇒ 前端唯渲、⛔ 比字面哨符。
#  ⭐ .4：「面之源」逐键增「态」（**机器码** `no_root` ／ `empty` ／ `ok` · pm_1503 §一）。
#  ⭐ .2：「面之源」三键（pm_1417 §三.3 · 面之数由三键定 ⇒ 用户须能知）
#  ⭐ .3：「本机配置」显形（pm_1453 §一 之裁 · 本席一手逮得）——
#           `config/.env` ／ `config/secrets.yaml` 在**包内必无** ⇒ 「缺」＝**常形**
#           ⇒ **缺 ⇒ 跳读**（⛔ 崩）＋**显形**：「未配 ⟷ 已配」须有字（⛔ 静默缺）。

#: ⛔ 遥测／分析之显式调用点之形（**调用形** · ⛔ 唯品牌名 —— 名可现于文档而不为调用）
_TELEMETRY_MARKS = ("posthog.", "sentry_sdk.init(", "mixpanel.", "amplitude.",
                    "send_telemetry(", "google-analytics.com", "gtag(", "matomo.", "umami.")


def _telemetry_scan():
    u"""静态核：`core/**` 之显式遥测／分析调用点 —— **器取**（⛔ 口说「无遥测」＝ 装成可用）。

    ⚠ 其为**弱保证**（唯字面扫 · ⛔ 及动态加载）⇒ 面之辞须以本读为据 ＋ 明书其界。
    """
    hits = []
    try:
        for _p in (_UI_REPO / "core").rglob("*.py"):
            try:
                _t = _p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            # ⚠ 剔**本表之定义**自身 —— ⛔ 则自指（我一手逮之实：9 处「命中」皆出本档之定义行）
            if "_TELEMETRY_MARKS = (" in _t:
                _a = _t.index("_TELEMETRY_MARKS = (")
                _b = _t.index(")", _a) if ")" in _t[_a:] else len(_t)
                _t = _t[:_a] + _t[_b + 1:]
            for _k in _TELEMETRY_MARKS:
                if _k in _t:
                    hits.append("%s:%s" % (_p.relative_to(_UI_REPO).as_posix(), _k))
    except Exception as _e:
        return ["未核：%s: %s" % (type(_e).__name__, str(_e)[:80])]
    return hits


def _ollama_tri():
    u"""模型路之**三态** —— **一处出**：`scripts/win_pa/preflight_start.py::probe_ollama`（承 30b523c）。

    ⛔ 本档另写一遍（二源必漂）｜读不到其三态器 ⇒ `态 = 未核` ＋ **显因**（⛔ 静默 · ⛔ 装成可用）。
    """
    out = {"态": "未核", "因": "", "models": None, "首": None,
           "三态器": "scripts/win_pa/preflight_start.py（probe_ollama）"}
    import importlib.util as _ilu
    import sys as _sys
    try:
        _p = _UI_REPO / "scripts" / "win_pa" / "preflight_start.py"
        _spec = _ilu.spec_from_file_location("_pa_preflight_tri", str(_p))
        if _spec is None or _spec.loader is None:
            out["因"] = u"三态器不可读（spec 空）：%s" % _p.as_posix()
            return out
        _m = _ilu.module_from_spec(_spec)
        _so = _sys.stdout
        if _so is not None and not hasattr(_so, "reconfigure"):
            class _Sink(object):      # ⚠ 三态器于**导入期**调 `sys.stdout.reconfigure` ⇒ 须容忍
                def reconfigure(self, *a, **k):
                    return None

                def write(self, s):
                    return len(s)

                def flush(self):
                    pass

            _sys.stdout = _Sink()
        try:
            _spec.loader.exec_module(_m)
        finally:
            _sys.stdout = _so
        _ok, _why, _note = _m.probe_ollama()
        _why = str(_why or "")
        _note = str(_note or "")
        _cnt = None
        if "models=" in _note:
            try:
                _cnt = int(_note.split("models=")[1].split(u"（")[0].split()[0])
            except Exception:
                _cnt = None
        if _ok:
            _st = u"在∧可用"
        elif u"未接" in _why:
            _st = u"未接"
        elif u"不可达" in _why:
            _st = u"不可达"
        elif u"无权重" in _why:
            _st = u"在·无权重"
        else:
            _st = u"未核"
        out.update({"态": _st, "因": _why, "models": _cnt})
        if u"（首 " in _note:
            out["首"] = _note.split(u"（首 ")[1].split(u"）")[0]
    except Exception as _e:
        out["因"] = u"三态器不可用：%s: %s ｜ 修之门：查 scripts/win_pa/preflight_start.py" % (
            type(_e).__name__, str(_e)[:140])
    return out


def _first_run_readout():
    u"""⭐ 首启引导（净机之「第一屏」）之读数 —— **只读**（承 pm_1384 §三.3 之四判成）。

    ⒜ 数据在本机（**人话** · ⛔ 行话）⒝ 模型三态 ＋ 修之门 ⒞ 数据目录（**真源** · ⛔ 造径）
    ⒟ ⛔ 静默（缺则显因）。
    """
    from time import strftime as _stf
    out = {"ok": True, "at": _stf("%Y-%m-%d %H:%M:%S"), "version": PA_FIRST_RUN_VERSION,
           "口径": u"首启之第一屏：数据在本机 ／ 模型三态＋修之门 ／ 数据目录之真源 ／ 缺则显因（⛔ 静默）",
           "缺": []}
    pm, ps = {}, {}
    try:
        from core.pa import env_face as _ef
        pm, ps = _ef.resolve_paths()
    except Exception as _e:
        out["缺"].append({"项": u"径之真源", "因": u"%s: %s" % (type(_e).__name__, str(_e)[:120])})
    _d, _dsrc = pm.get("data"), (ps or {}).get("data")
    out["数据目录"] = {
        "值": _d, "源": _dsrc,
        "可指之径": u"env PA_DATA_DIR ∨ config/system/system_unified.yaml:paths.data_root（本面**唯读** · ⛔ 改）",
    }
    if not _d:
        out["缺"].append({"项": u"数据目录", "因": _dsrc or u"真源不可读"})
    _tri = _ollama_tri()
    out["模型"] = {"态": _tri.get("态"), "因": _tri.get("因"), "models": _tri.get("models"),
                   "首": _tri.get("首"), "三态器": _tri.get("三态器")}
    if _tri.get("态") != u"在∧可用":
        out["缺"].append({"项": u"本机模型（ollama）", "因": _tri.get("因") or _tri.get("态")})
    _tel = _telemetry_scan()
    _port = None
    try:
        from core.lib.port_config import gateway_port as _gp
        _port = int(_gp())
    except Exception:
        _port = None
    _tel_txt = (u"（%s）" % u"、".join(_tel[:3])) if _tel else u""
    out["数据在本机"] = {
        "是": True,
        "上传": False,
        "据": u"本机之门 127.0.0.1%s · 远端算力**未接**（P2）· core/** 之遥测调用点 %d 处%s"
              % (((":%d" % _port) if _port else ""), len(_tel), _tel_txt),
        "辞": u"你的数据留在**这台电脑**上：本产品**自带**之遥测 ／ 自动上传 ＝ **无**；"
              u"唯你显式发起、且远端已接之时方出网（远端**今未接** · P2）。",
    }
    _lf, _lf_err = [], ""
    try:
        from core.lib.local_env_files import local_files_state as _lfs
        _lf = _lfs(str(_UI_REPO))
    except Exception as _e:
        _lf_err = u"%s: %s" % (type(_e).__name__, str(_e)[:120])
        out["缺"].append({"项": u"本机配置（.env ／ secrets.yaml）", "因": _lf_err})
    out["本机配置"] = {
        "口径": u"交付包内**必无** config/.env ／ config/secrets.yaml ⇒ 「未配」＝ **正常之貌**"
                u"（⛔ 故障）· 缺则**跳读**（⛔ 崩）· 有则照读",
        "件": _lf,
        "未核": (_lf_err or None),
    }
    _lf_txt = (u" ／ ".join(u"%s＝%s" % (x["名"], x["态"]) for x in _lf)
               if _lf else (u"未核：%s" % _lf_err))
    _lf_state = u"已配" if any(x.get("态") == u"已配" for x in _lf) else u"未配"
    out["须知"] = [
        {"话": u"你的数据在这台电脑上" + ((u"：%s" % _d) if _d else u"（⛔ 未接 —— 见下「缺」）"),
         "据": _dsrc or u"未接"},
        {"话": u"本产品**不自动上传**你的数据，也**没有**遥测。",
         "据": u"器核（弱保证 · 唯字面扫）：core/** 之遥测调用点 %d 处%s"
               % (len(_tel), (u"（%s）" % u"、".join(_tel[:3])) if _tel else u"")},
        {"话": u"AI 走**本机**模型 —— 现在：**%s**。" % _tri.get("态"),
         "据": _tri.get("因") or u"（三态器未给因 —— 见「缺」）"},
        {"话": u"云端密钥：本机**%s**（正常 —— 交付包里本来就没有这一件）。" % _lf_state,
         "据": _lf_txt},
        {"话": u"缺什么，上面就写什么 —— ⛔ 假装能用。",
         "据": u"「缺」列 %d 项" % len(out["缺"])},
    ]
    _org, _ws, _vr = False, None, None
    _wssrc, _vsrc, _vcode = u"未核", u"未核", u"no_root"
    _v_on, _v_note = False, u""        # ⭐ .6：env 覆盖（唯自 `vault_env_override()` · 一处定形）
    try:
        from core.lib import paths as _P
        _org, _ws, _vr = bool(_P.org_enabled()), _P.ws_root(), _P.vault_root()
        _v_on, _v_note = vault_env_override()
        # ⭐ pm_1502 §一.3：「源」须**同源**（唯自 `core/lib/paths.py` 之 src 器出 · ⛔ 二处各判）
        _wssrc = _P.ws_root_src()[1]
        _vsrc = _P.vault_root_src()[1]
        # ⭐ pm_1503 §一：「态」＝**机器码**（一处定形 · ⛔ 另立判据）
        # ⭐⭐ pm_1517 §一（裁：取拟一）：其**判据改依「PA 检索面」**（⛔ 内核约定六面）——
        #   唯问本模块之 `pa_vault_state_code()`（一处定形 · 其内即 `PA_KB_ASK_SCOPES` ＋ `PA_FACES`）。
        _vcode, _vn, _vfaces = pa_vault_state_code(root=(str(_vr) if _vr else None))
    except Exception as _e:
        out["缺"].append({"项": u"面之源（三键）", "因": u"%s: %s" % (type(_e).__name__, str(_e)[:120])})
    # ⭐ pm_1502 §一.3 ／ §一.4：每键增「源」（env ／ 配置 ／ 内置空库）⇒ 今 ／ 义 二形须合。
    out["面之源"] = {
        "口径": u"「面之数」由三键定 —— 缺则面减（照实 · ⛔ 静默）· 每键附「源」（今之值所自出）"
                u"＋「态」（**机器码** · 前端唯渲 · ⛔ 比字面哨符）",
        "态域": u"no_root（该键之根 ⛔ 得 ∨ ⛔ 在 ⇒ 「未接」）／ empty（根在而**检索面**无件"
                 u" ⇒ 空库之貌 · **⛔ 病**）／ ok（有件）；⚠ PA_VAULT_DIR 之空／有按"
                 u"**本库根之 PA 检索面**（`PA_KB_ASK_SCOPES` ＋ `PA_FACES` 中根在本库根之下者）之件数"
                 u"计（⛔ 内核约定六面 —— 承 pm_1517 §一）；逐键之现域见各「态」",
        "键": [
            {"键": "PA_ORG_FACES",
             "义": u"组织版开关（功能级 · 默认关）—— 开 ⇒ 并入组织面；关 ⇒ 唯产品面「死件账」",
             "今": (u"开" if _org else u"关（默认）"),
             "源": u"env:PA_ORG_FACES（功能级开关 · 默认关）",
             "态": (u"ok" if _org else u"empty")},
            {"键": "PA_WS_ROOT",
             "义": u"工作区根（产品级）—— 组织面之根；缺 ⇒ 组织面 ⛔ 入表",
             "今": (_ws or u"未接"),
             "源": _wssrc,
             "态": (u"ok" if _ws else u"no_root")},
            {"键": "PA_VAULT_DIR",
             "义": u"知识库根（用户自选；亦可指配置 paths.vault_root；皆无 ⇒ 用内置空库 "
                   u"<data_root>/kb）—— 唯四序皆无 ⇒ 显「未接（选目录）」；内置空库在 ⇒"
                   u"「今」为其径 ∧ 「源」明书其自内置空库（⛔ 混同「未接」）；"
                   u"「态」＝ no_root ／ empty ／ ok（**今随态**：no_root ⇒ 今 ＝「未接」）；"
                   u"empty ／ ok 按**本库根之 PA 检索面**（`PA_KB_ASK_SCOPES`：收件箱 ／ 知识库"
                   u" ＋ `PA_FACES` 中**根在本库根之下**者）之件数计 —— ⛔ 内核约定六面"
                   u"（notes ／ sop ／ reviews ／ inbox ／ drafts ／ assets ⇒ 另轴 · 二物别）"
                   u"（承 pm_1517 §一 之裁）；env 在 ⇒ 「今」＝ env 之径 ∧ `note` 明书"
                   u"「所选须清该变量方生效」（env 覆盖配置之写 · 承 pm_1525 §一）",
             "今": (str(_vr) if (_vr and _vcode != u"no_root") else u"未接"),
             "源": _vsrc,
             "态": _vcode,
             # ⭐ .6（pm_1525 §一 · 一处定形）：`env` 在 ⇒ 配置之写**⛔ 生效** ⇒ 须**明书**
             #   （⛔ 静默）；其源唯 `vault_env_override()`（与 `vault/set` 之回**同源** · ⛔ 二处各判）。
             "env_override": _v_on,
             "note": _v_note},
        ],
    }
    return out

def _ask_scope(question):
    """问域类（承 PM 846 §三·⒜）：`meta`（会话路）｜`retrieve`（检索闸）。"""
    _q = (question or "").strip()
    if any(_k in _q for _k in PA_ASK_FORCE_KW):
        return "retrieve"                      # ⭐ 退路：句首「检索：」强制走检索面
    if any(_k in _q for _k in PA_ASK_META_NOT):
        return "retrieve"                      # ⭐ 索引类 ⇒ ⛔ meta（保守归检索）
    if len(_q) <= 40 and any(_k in _q for _k in PA_ASK_META_KW):
        return "meta"
    return "retrieve"


def _last_user_before(pa, question, session_id=None):
    """取本会话**真序列**之「上一句 user 原文」（⛔ 前端拼 ／ ⛔ 猜）。
    返回 (text|None, meta)：meta 逐项报 picked_by ／ path ／ skipped_self（⛔ 静默）。"""
    import json                      # ⚠ 本件**⛔ 模块级导 json**（我一手核 · 承我第 22 号）
    from datetime import datetime as _dt5
    _d = pa.dir / "sessions"
    _how, _p = None, None
    try:
        if session_id:
            # ⭐ PM 2026-10-05（我一手逮）：指定会话 ⇒ **唯该会话**（文件不在 ⇒ 如实「上下文缺」）
            #   由：旧法「指定而文件不在」⇒ 落「最新会话」⇒ **跨会话泄漏**（A 会话之问取 B 会话之句）
            _c = _d / ("session_%s.jsonl" % session_id)
            if _c.is_file():
                _how, _p = "request", _c
            else:
                return None, {"picked_by": "request", "reason": "指定会话无记录（⛔ 落他会话 · ⛔ 猜）",
                              "session_id": session_id}
        if _p is None:
            _all = sorted(_d.glob("session_*.jsonl"), key=lambda x: x.stat().st_mtime, reverse=True)
            if _all:
                _how, _p = "newest", _all[0]
    except Exception as _e:
        return None, {"picked_by": None, "reason": "列会话异常: %s" % _e}
    if _p is None:
        return None, {"picked_by": None, "reason": "sessions/ 无可读会话"}
    _meta = {"picked_by": _how, "path": str(_p),
             "session_id": _p.name[len("session_"):-len(".jsonl")], "skipped_self": 0,
             "read_at": _pa_read_at()}
    _last = None
    try:
        for _ln in _p.read_text(encoding="utf-8", errors="replace").splitlines():
            _ln = _ln.strip()
            if not _ln:
                continue
            try:
                _r = json.loads(_ln)
            except Exception:
                continue
            if _r.get("role") != "user":
                continue
            _t = (_r.get("text") or "").strip()
            if not _t:
                continue
            if _t == (question or "").strip():   # ⭐ 本问已落会话 ⇒ 再退一句（否则「上一句」＝本问）
                _meta["skipped_self"] += 1
                continue
            # ⭐ PM 2026-10-05（承 L159）：自测 ／ 探针之痕 ⛔ 作答（⛔ 充作「你上一条」）
            if str(_r.get("topic") or "") == "selftest" or any(_m in _t for _m in PA_SELFTEST_MARKS):
                _meta["skipped_selftest"] = _meta.get("skipped_selftest", 0) + 1
                continue
            _last = _t
    except Exception as _e:
        _meta["reason"] = "读会话异常: %s" % _e
    return _last, _meta


def _ask_decision(question, user_id=None, session_id=None):
    r"""⭐ 修①：**决策账之直答**（PM 2026-10-05 §二 · 老板实测 d1791202075323 之洞之修）。

    病：本机 data\v9\pa\decision_log.json 有据，而「有据才答」闸 ⛔ 扫该面 ⇒ 报「本机无据」
    ⇒ 拒答 ⇒ 回落模型 ⇒ **编造／冒认**（老板所见「T1已完成」＝ 编造；「查不到」＝ 闸漏之冒认）。
    ⇒ 修：问含 **decision_id 形（d\d{13}）** ∨ **「决策记录」之族** ⇒ **直取本机决策账**
      （DecisionStore(_data_dir())）⇒ **有据则答**（grounded）／**账无此条则如实「无此决策」**；
      ⛔ 回落模型（承「断『无』须先扫其体」）。
    返回 dict（本路）｜None（⛔ 属本路 ⇒ 交后续 _ask_scope 分路）。
    """
    import re as _re
    from datetime import datetime as _dt6
    _q = question or ""
    _ids = _re.findall(PA_ASK_DECISION_ID_RE, _q)
    _kw = [k for k in PA_ASK_DECISION_KW if k in _q]
    if not _ids and not _kw:
        return None
    from core.pa.decision import DecisionStore
    ds = DecisionStore(_data_dir())
    try:
        _all = ds.list(None)
    except Exception as _e:
        return {"grounded": False, "refused": False,
                "answer": "决策账不可读：%s ⇒ 如实不答（⛔ 不编）" % _e,
                "answer_source": "decision_store_unreadable",
                "decision_hits": [], "decision_source": str(ds.path),
                "decision_query": {"id": _ids, "kw": _kw},
                "verdict": "决策账不可读（%s）⇒ 如实不答（⛔ 不编）" % _e}
    _hits = [r for r in _all if str(r.get("id")) in _ids] if _ids else _all[-5:]
    if not _hits:
        # ⭐ 2026-10-05（PM 22:34 §一 · 活体之逮）：**拒答亦须有人话句** ——
        #   原 answer 为空（唯 verdict 载由）⇒ 前端只读 answer ⇒ 见「空答」
        #   （承「⛔ 失败静默」：拒答 ⛔ 等于无话）。今 answer 亦载逐字之由。
        _what = ", ".join(_ids) if _ids else "/".join(_kw)
        return {"grounded": False, "refused": True,
                "answer": "本机决策账无此条：%s（在盘共 %d 条）⇒ 如实不答（⛔ 不编）"
                          % (_what, len(_all)),
                "answer_source": "decision_none",
                "decision_hits": [], "decision_source": str(ds.path),
                "decision_query": {"id": _ids, "kw": _kw},
                "verdict": "本机决策账无此条（查 %s）⇒ 如实不答（⛔ 不编）" % _what}

    def _fmt(_r):
        _t = _dt6.fromtimestamp(int(_r.get("ts") or 0)).strftime("%Y-%m-%d %H:%M:%S")
        return "决策 %s：%s · 阶段 %s · note：%s · task：%s · 刻 %s" % (
            _r.get("id"), _r.get("decision"), _r.get("stage"),
            (_r.get("note") or "（无）"), (_r.get("task") or "（无）"), _t)

    if _ids:
        _ans = "\n".join(_fmt(_r) for _r in _hits)
    else:
        _ans = "本机决策账：%s（共 %d 条）· 最近：%s" % (ds.path, len(_all), _fmt(_hits[-1]))
    return {"grounded": True, "refused": False, "answer": _ans,
            "answer_source": "decision",
            "decision_hits": _hits, "decision_source": str(ds.path),
            "decision_query": {"id": _ids, "kw": _kw},
            "decision_found": (_hits[0] if _ids else None),
            "verdict": "决策账有据（本机 %d 条 · 逐字照录 ⛔ 模型生成）" % len(_all)}


def _ask_deadfile(question):
    r"""⭐ 死件账之**直读路**（PM 2026-10-05 22:34 §三① 准 · 同 _ask_decision 之形）。

    病：`data\v9\pa\deadfile_ledger.json` 已入 `PA_FACES`（面在），然其行为**结构化 JSON**
    （径 ／ 键），⛔ 散文 ⇒ 行侧覆盖天然低 ⇒ 问阈 `0.42` 下 **prose 型问恒 ⛔ 中**
    （实测：`真缺件有哪些` ⇒ 0 中）⇒ **面在而问无门**（＝「面在而达 ⛔ ⇒ 假绿之形」之族）。
    ⇒ 本路唯「**多一条直读**」（⛔ 改闸之判据 —— 承 PM 之界）。

    ⭐ **判据（逐字 · 关键字／正则表）**：
      ⒜ 关键字表 `PA_ASK_DEADFILE_KW` —— 问含任一词 ⇒ 本路
      ⒝ 名中 —— 问含**该账已录之名**（`真缺[].value` 之 basename（含／不含扩展）∨
         `真缺[].yaml` ∨ 其 basename）⇒ 本路
         （⚠ ⛔ 泛匹配：唯**账中已录之名** ⇒ 天然无假有据 · 承「⛔ 泛面」之族）
      ⒞ 两条件皆 ⛔ 中 ⇒ 返回 `None`（不属本路 ⇒ 交后续 `_ask_scope` ／ 检索闸）

    ⭐ **阴性对照**（PM 条件⒝）：非死件之问（老板叫什么名字 ／ 公司去年的营收是多少 ／
      今天天气怎么样 ／ 帮我写一首诗）⇒ 本路 None ⇒ 0 中（实测见件 1056 之表）。

    返回 dict（本路）｜None（⛔ 属本路）。
    """
    import json as _json     # ⚠ 本件 ⛔ 模块级导 json（承 L668 之注 · 我第 22 号）
    _q = question or ""
    _kw = [k for k in PA_ASK_DEADFILE_KW if k in _q]
    _path = os.path.join(_data_dir(), PA_ASK_DEADFILE_LEDGER)
    try:
        with open(_path, encoding="utf-8-sig") as _f:
            _led = _json.load(_f)
    except Exception as _e:
        # ⭐ 2026-10-05（我自逮 · 1057 · 承 PM 1183 §八之精神）：账不可读 ⇒ ⛔ 得据此断言「本路」
        #   —— 名中之路须读账 ⇒ 无可判 ⇒ **问 ⛔ 含关键字者 ⇒ 返回 None**（交后续分路）；
        #   ⛔ 返回本路之 dict（否则 **每一问** 皆被本路劫持 ⇒ 承「弱保证 ≠ 真闸」）。
        if not _kw:
            return None
        return {"grounded": False, "refused": False,
                "answer": "死件账不可读（%s：%s）⇒ 如实不答（⛔ 不编）" % (_path, _e),
                "answer_source": "deadfile_unreadable",
                "deadfile_path": _path, "deadfile_query": {"kw": _kw, "names": []},
                "verdict": "死件账面不可读 ⇒ 如实不答（⛔ 不编）"}
    _rows = list(_led.get("真缺") or [])
    _vocab = {}
    for _r in _rows:
        _v = str(_r.get("value") or "")
        _y = str(_r.get("yaml") or "")
        for _s in (_v, _v.replace(chr(92), "/").split("/")[-1],
                   os.path.splitext(_v.replace(chr(92), "/").split("/")[-1])[0],
                   _y, _y.replace(chr(92), "/").split("/")[-1],
                   os.path.splitext(_y.replace(chr(92), "/").split("/")[-1])[0]):
            if len(_s) >= 4:
                _vocab.setdefault(_s, []).append(_r)
    _by_name = sorted([k for k in _vocab if k in _q], key=len, reverse=True)
    if not _kw and not _by_name:
        return None
    _meta = {"器": _led.get("器"), "器印": _led.get("器印"), "取数刻": _led.get("取数刻"),
             "域": (_led.get("域") or {}).get("root"), "件数": _led.get("件数"),
             "分档": _led.get("分档"), "真缺件数": _led.get("真缺件数"),
             "path项数": _led.get("path项数"), "盘上无者数": _led.get("盘上无者数")}
    if _by_name:
        _sel, _seen = [], set()
        for _k in _by_name:
            for _r in _vocab[_k]:
                _key = (_r.get("yaml"), _r.get("line"), _r.get("value"))
                if _key in _seen:
                    continue
                _seen.add(_key)
                _sel.append((_k, _r))
        _ls = ["本机死件账（器 %s · 器印 %s · 取数刻 %s）命中 %d 条 —— 逐字照录："
               % (_meta["器"], _meta["器印"], _meta["取数刻"], len(_sel))]
        for _k, _r in _sel:
            _ls.append("  · 命中「%s」｜%s:%s ｜ value %s ｜ 档 %s ｜ 别处有 %s"
                       % (_k, _r.get("yaml"), _r.get("line"), _r.get("value"),
                          _r.get("档"), _r.get("别处有")))
        return {"grounded": True, "refused": False, "answer": "\n".join(_ls),
                "answer_source": "deadfile", "deadfile_path": _path,
                "deadfile_meta": _meta, "deadfile_query": {"kw": _kw, "names": _by_name},
                "deadfile_hits": [_r for _k, _r in _sel],
                "verdict": "死件账有据（本机账命中 %d 条 · 逐字照录 ⛔ 模型生成）" % len(_sel)}
    _ls = ["本机死件账（取数刻 %s · 器 %s · 器印 %s）：真缺件 %s 条 ／ path 项 %s ／ 盘上无者 %s"
           % (_meta["取数刻"], _meta["器"], _meta["器印"], _meta["真缺件数"],
              _meta["path项数"], _meta["盘上无者数"]),
           "分档：%s" % (_meta["分档"],)]
    if not _rows:
        _ls.append("⇒ 真缺件 0 条（照实之读数 · ⛔ 未知）")
    else:
        _ls.append("真缺件逐条（前 %d 条）：" % min(len(_rows), 20))
        for _r in _rows[:20]:
            _ls.append("  · %s:%s ｜ %s ｜ 档 %s ｜ 别处有 %s"
                       % (_r.get("yaml"), _r.get("line"), _r.get("value"),
                          _r.get("档"), _r.get("别处有")))
        if len(_rows) > 20:
            _ls.append("  …（余 %d 条见账）" % (len(_rows) - 20))
    return {"grounded": True, "refused": False, "answer": "\n".join(_ls),
            "answer_source": "deadfile", "deadfile_path": _path,
            "deadfile_meta": _meta, "deadfile_query": {"kw": _kw, "names": []},
            "deadfile_hits": _rows[:20],
            "verdict": "死件账有据（本机账 %s 条 · 逐字照录 ⛔ 模型生成）" % len(_rows)}


def _kb_root_str():
    u"""库根（**字符串** · 未接 ⇒ ``""``）—— ⭐ pm_1500 §二：**唯一判点**（⛔ 二处各判「空」）。

    ⨀ 其源＝`core.lib.paths.vault_root()`（四序：`PA_VAULT_DIR` ⇒ 配置 `paths.vault_root`
      ⇒ 内置 `<data_root>/kb` ⇒ 末选 `PA_VAULT_LEGACY`）—— 本处 **⛔ 另判**（一处定形）。
    ⚠ 未接之「空」⛔ 同「扫了而无」（承「空 ≠ 缺」）⇒ 由 `no_kb_root` 分标。
    """
    _vr = vault_root()
    return str(_vr) if _vr is not None else ""


def pa_ask_scan_specs(kb_root):
    u"""`/v9/pa/ask` 之**扫面清单**（一处定形）—— `(根, 面名, 通配)` 之列。

    ⭐ pm_1549 §一.2：扫（`pa_kb_search`）与「印」（`pa_ask_scan_stamp`）**同用此单**
      ⇒ 「将被扫之件集」二处**必同**（⛔ 二处各列 ⇒ 印与扫错位）。
    """
    out = [(Path(kb_root) / rel, rel, ("*.md",)) for rel in PA_KB_ASK_SCOPES]
    for name, roots, globs in pa_faces():
        for spec in roots:
            out.append((_face_root(kb_root, spec), name, globs))
    return out


def pa_ask_scan_stamp(kb_root):
    u"""**扫面之印**（复问缓存之失效判 · pm_1549 §一.2 裁 ⒝）—— ⛔ 读内容 · 唯列举 ＋ `stat`。

    值 ＝ `件数:sha256(径|mtime_ns|size …)[:16]`；**唯作相等判**（⛔ 人读 ／ ⛔ 入屏）。
    ⇒ 面变（增 ／ 删 ／ 改件 · 或改库根 ⇒ 换面）⇒ 印变 ⇒ 复问缓存**自失效**。
    ⚠ 与 `_cached_lines` **同轴**（二者皆 `mtime_ns`）—— 印之分辨细于行缓存 ⇒
      「印变而读旧」＝**假新鲜**（承「⛔ 不实之辞入屏」）⇒ 故二处必同轴。
    """
    import hashlib                      # ⭐ 局部导入（本模块级 ⛔ 增导 · 承 L22 之族）
    _h = hashlib.sha256()
    _n = 0
    for root, _face, globs in pa_ask_scan_specs(kb_root):
        for p in _face_files(root, globs):
            try:
                _st = p.stat()
            except Exception:
                continue
            _n += 1
            _h.update((u"%s|%d|%d\n" % (p, _st.st_mtime_ns, _st.st_size)).encode("utf-8"))
    return u"%d:%s" % (_n, _h.hexdigest()[:16])


def pa_kb_search(question, kb_root, limit=5, min_score=PA_ASK_MIN_SCORE):
    """PA 知识库检索（BUG-2 的「有据面」）。

    口径：不用子串近似判「命中」；用 2-gram 覆盖率（问题侧 bigram 被某一行覆盖的比例）。
    返回 hits（file/line/score/text）＋ searched（真搜了几件）＋ ⭐ faces（**每面各报件数**）。
    ⭐ 2026-10-04（PM 授权 · 老板批）：除 (收件箱/知识库) 外，增扫 PA_FACES 之面（文件 ／ 台账）。
    """
    # ⭐⭐ pm_1500 §二：库根未接 ⇒ **早返**（⛔ 触 `Path("")` ⇒ 误扫 CWD · 假有据）。
    if not str(kb_root or "").strip():
        return {"hits": [], "archive_hits": [], "searched": 0, "searched_scans": 0,
                "searched_roles": {}, "scope": [],
                "threshold": min_score, "faces": {}, "no_kb_root": True,
                "faces_missing": list(PA_KB_ASK_SCOPES) + [f[0] for f in pa_faces()],
                "faces_skipped": {}, "faces_version": PA_FACES_VERSION,
                "face_snapshot_at": None}
    qg = _bigrams(question)
    # ⭐ PM 2026-10-05（承 技总 973 §三 · `v3` ⒜）：剔**语料名**之 bigram（判别力 ≈ 0 ⇒ 结构性压低 cov）
    for _nm in PA_CORPUS_NAME_BIGRAMS:
        if _nm in question:
            qg = qg - _bigrams(_nm)
    from time import strftime as _strftime   # ⭐ 局部导入（我一手核：本模块级 ⛔ `_tm` ⇒ 前版误用 ⇒ 500）
    _snap = _strftime("%Y-%m-%d %H:%M:%S")   # ⭐ 采样刻（真源 ＝ 扫描起刻 · ⛔ 逐件 mtime · 承 845 §二）
    _qg_all2 = all(len(_b) >= 2 for _b in qg)   # ⭐ 降本条 ⓑ：快路适用条件（见 `_inter_fast`）
    hits = []
    _arch = []   # ⭐ 档案面之命中（⛔ 作据 · 另键报出 · 承 L154）
    searched = 0
    _seen = {}   # ⭐ pm_1569 §四.4：径 ⇒ 角色（searched 之**唯一**之据 · 同件二面 ⇒ 只计一次）
    faces = {}
    face_missing = []
    face_skipped = {}
    if not qg:
        return {"hits": [], "searched": 0, "searched_scans": 0, "searched_roles": {},
                "scope": [], "threshold": min_score, "faces": {},
                "faces_missing": [], "faces_skipped": {}}

    def _scan(root, face, globs):
        nonlocal searched
        n0 = searched
        _role = PA_FACE_ROLE.get(face, "knowledge")   # ⭐ 面级角色（一处取 · pm_1569 §四.3）
        _ms = PA_FACES_MIN_SCORE.get(face, min_score)
        _maxb = PA_FACES_MAX_BYTES.get(face, PA_FACES_DEFAULT_MAX_BYTES)
        if not Path(root).is_dir():
            face_missing.append(face)   # ⭐ 缺根 ⇒ 明标（⛔ 只报 0 件 ⇒ 会被读成「无料」）
        for p in _face_files(root, globs):
            try:
                if p.stat().st_size > _maxb:
                    face_skipped[face] = face_skipped.get(face, 0) + 1   # ⭐ 跳件须计数并上报
                    continue
            except Exception:
                continue
            lines = _cached_lines(p)
            if lines is None:
                continue
            searched += 1
            _seen[str(p)] = _role   # ⭐ pm_1569 §四.4：唯一件数之据（同件二面 ⇒ 只计一次）
            for i, ln in enumerate(lines, 1):
                ln = ln.strip()
                if len(ln) < 4:
                    continue
                _lg = None
                _inter = _inter_fast(qg, ln, _qg_all2)
                if _inter is None:                 # ⛔ 快路不适用 ⇒ 回落旧法（判 ⛔ 变）
                    _lg = _bigrams(ln)
                    _inter = len(qg & _lg)
                cov = _inter / float(len(qg))      # 问题侧（保留 ⇒ 上屏之 score）
                if cov < _ms:
                    continue
                if _role != "archive":             # ⭐ 行侧（PM 846 §二.2 双向取小 · 承 L150）
                    if _lg is None:                #   ⭐ 惰算：唯**存活行**方建行侧集（降本条 ⓑ）
                        _lg = _bigrams(ln)
                    rcv = _inter / float(len(_lg)) if _lg else 0.0
                    if rcv < PA_FACES_MIN_ROW.get(face, _ms):   # ⭐ 行阈按面可配（承 973 §三）
                        continue
                if _role != "archive":
                    hits.append({"file": str(p), "rel": face, "line": i,
                                 "score": round(cov, 3), "role": _role, "text": ln[:160]})
                else:
                    _arch.append({"file": str(p), "rel": face, "line": i,
                                  "score": round(cov, 3), "role": _role, "text": ln[:160]})
        faces[face] = faces.get(face, 0) + (searched - n0)

    for _root, _face, _globs in pa_ask_scan_specs(kb_root):   # ⭐ pm_1549 §一.2：扫面清单**一处定形**（与「印」同轴）
        _scan(_root, _face, _globs)

    hits.sort(key=lambda x: -x["score"])
    _arch.sort(key=lambda x: -x["score"])
    allscope = list(PA_KB_ASK_SCOPES) + [f[0] for f in pa_faces()]
    _roles = {}                      # ⭐ pm_1569 §四.3／§四.4：作据 N ／ 只索引 M（分列 ⇒ ⛔ 静默）
    for _r in _seen.values():
        _roles[_r] = _roles.get(_r, 0) + 1
    return {"hits": hits[:limit], "archive_hits": _arch[:limit], "searched": len(_seen),
            "searched_scans": searched, "searched_roles": _roles,
            "scope": allscope, "threshold": min_score, "faces": faces,
            "faces_missing": face_missing, "faces_skipped": face_skipped,
            "face_snapshot_at": _snap, "faces_version": PA_FACES_VERSION,
            "faces_gate": pa_faces_gate()}


def _dialog_sessions(pa, limit=20):
    """sessions/ 清单（改时倒序）—— 供「读面默认取哪个会话」与复核用。"""
    from datetime import datetime as _dt

    out = []
    try:
        d = pa.dir / "sessions"
        for p in sorted(d.glob("session_*.jsonl"), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
            _st = p.stat()
            _n = _jsonl_lines(p)          # None = 读不到（⛔ 不是 0）
            out.append({
                "session_id": p.name[len("session_"):-len(".jsonl")],
                "path": str(p),
                "bytes": _st.st_size,
                "lines": _n,
                "lines_readable": _n is not None,
                "mtime": _dt.fromtimestamp(_st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            })
    except Exception:
        pass
    return out


def _kb_safe_rel(scope):
    """scope 必须是 vault 内的**相对**子路径（拒绝绝对路径 / .. 穿越 / 空字节）。"""
    s = str(scope or "").strip().replace(chr(92), "/").strip("/")
    if chr(0) in s:
        raise ValueError("scope 含非法字符")
    parts = [p for p in s.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise ValueError("scope 不允许 .. 穿越: %r" % scope)
    return "/".join(parts)


def build_kb_mapping(*, kb_root, sandbox_root, scope=KB_MAPPING_DEFAULT_SCOPE, limit=100, mirror_manifest=None):
    """知识库 ↔ 沙箱映射（批176 副指标 A）。**只读**：不写知识库、不写沙箱、不改 mtime。

    主语 = 知识库：kb_path（相对 kb_root）→ sandbox_path（沙箱内映射目标）→ status。
    状态判据（可机械复核）：
      已镜像 = 沙箱有副本，且大小相同、副本 mtime >= 源 mtime
      过期   = 沙箱有副本，但大小不同 或 副本更旧
      缺失   = 沙箱无副本，但**有镜像记录**（mirror_manifest；镜像功能落地后才可能出现）
      未镜像 = 沙箱无副本且无记录（默认态）
    """
    from datetime import datetime as _dt

    rel = _kb_safe_rel(scope)
    lim = max(1, min(int(limit or 100), 500))
    src_dir = (Path(kb_root) / rel) if rel else Path(kb_root)
    out = {
        "kb_root": str(kb_root),
        "kb_root_forms": list(path_forms(kb_root)),
        "sandbox_root": str(sandbox_root or ""),
        "scope": rel,
        "limit": lim,
        "readonly": True,
        "statuses": list(KB_STATUSES),
        "fingerprint": KB_FINGERPRINT,
        "rows": [],
        "counts": {s: 0 for s in KB_STATUSES},
        "total": 0,
        "truncated": False,
        "degraded": "",
        # 验收-B：判据跑没跑要能看出来 —— False 时上面那份 counts 不是读数（不适用 不等于 验过）
        "verified": True,
    }
    if not src_dir.is_dir():
        out["degraded"] = "知识库目录不存在: %s" % src_dir
        return out
    try:
        entries = [p for p in src_dir.iterdir() if p.is_file()]
    except Exception as _e_dir:
        out["degraded"] = "知识库目录不可读: %s" % _e_dir
        return out
    entries.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    out["total"] = len(entries)
    if len(entries) > lim:
        entries = entries[:lim]
        out["truncated"] = True
    sb_root = Path(sandbox_root) if sandbox_root else None
    _sb_ok = bool(sb_root is not None and sb_root.is_dir())
    if not _sb_ok:
        # 验收-B：没有副本面 ⇒ 判「未知」（不适用），不许报「过期 0」（那是没验，不是 0）
        out["verified"] = False
        out["degraded"] = ("沙箱目录不存在（%s）⇒ 无法比对 ⇒ 状态判「%s」；"
                           "这份 counts 不是读数（不适用 不等于 验过）"
                           % (sandbox_root or "未提供", KB_STATUS_UNKNOWN))
    manifest = set()
    if isinstance(mirror_manifest, dict):
        _mf = mirror_manifest.get("files", mirror_manifest)
        manifest = set(_mf.keys()) if isinstance(_mf, dict) else set(map(str, _mf or []))
    elif isinstance(mirror_manifest, (list, tuple, set)):
        manifest = set(map(str, mirror_manifest))
    for p in entries:
        kb_rel = ("%s/%s" % (rel, p.name)) if rel else p.name
        sb_path = (sb_root / rel / p.name) if sb_root else (Path(rel) / p.name)
        _st = p.stat()
        row = {
            "name": p.name,
            "kb_path": kb_rel,
            "kb_abs": str(p),
            "sandbox_path": str(sb_path),
            "kb_bytes": _st.st_size,
            "kb_mtime": _dt.fromtimestamp(_st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "mirror_bytes": None,
            "mirror_mtime": None,
            "kb_sha16": None,
            "mirror_sha16": None,
            "status": KB_STATUS_UNMIRRORED,
            "reason": "沙箱无此副本",
        }
        if not _sb_ok:
            row["status"] = KB_STATUS_UNKNOWN
            row["reason"] = "沙箱目录不存在 ⇒ 无法比对（不适用；不是「未镜像」，也不是 0）"
        try:
            if not _sb_ok:
                pass
            elif sb_path.is_file():
                _sm = sb_path.stat()
                row["mirror_bytes"] = _sm.st_size
                row["mirror_mtime"] = _dt.fromtimestamp(_sm.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                # 验收-A：判据由「大小＋改时」改成「内容指纹 ＋ 非空」。
                # 为什么必须改：旧判据把这两种都判绿 ——
                #   ① 源与副本**都换成空件**（0 字节 == 0 字节）；② **等长换内容**（512 == 512）。
                #   ⇒ 这两条恰是「改名换姓的 exists-only」，比只看存在更难发现（PM 反例门实测 · 本线 P2 同一发现）。
                if _sm.st_size != row["kb_bytes"]:
                    row["status"] = KB_STATUS_STALE
                    row["reason"] = "大小不同（源 %d / 副本 %d 字节）" % (row["kb_bytes"], _sm.st_size)
                elif _sm.st_size == 0:
                    row["status"] = KB_STATUS_STALE
                    row["reason"] = "副本是空件（0 字节）⇒ 不算镜像（旧判据在此假绿）"
                else:
                    row["kb_sha16"] = _kb_fingerprint(p)
                    row["mirror_sha16"] = _kb_fingerprint(sb_path)
                    if row["kb_sha16"] is None or row["mirror_sha16"] is None:
                        row["status"] = KB_STATUS_UNKNOWN
                        row["reason"] = ("文件超指纹上限（%d MB）⇒ 无法比对（不适用）"
                                         % (KB_FINGERPRINT_MAX_BYTES // (1024 * 1024)))
                    elif row["kb_sha16"] != row["mirror_sha16"]:
                        row["status"] = KB_STATUS_STALE
                        row["reason"] = ("内容指纹不同（源 %s / 副本 %s）⇒ 字节数相同也不算镜像"
                                         % (row["kb_sha16"], row["mirror_sha16"]))
                    elif _sm.st_mtime < _st.st_mtime:
                        row["status"] = KB_STATUS_STALE
                        row["reason"] = ("指纹一致 %s 但副本比源旧（%s < %s）"
                                         % (row["kb_sha16"], row["mirror_mtime"], row["kb_mtime"]))
                    else:
                        row["status"] = KB_STATUS_MIRRORED
                        row["reason"] = "内容指纹一致 %s（非空 %d 字节）" % (row["kb_sha16"], row["kb_bytes"])
            elif kb_rel in manifest:
                row["status"] = KB_STATUS_MISSING
                row["reason"] = "有镜像记录但沙箱副本不存在"
        except Exception as _e_row:
            row["reason"] = "状态判定异常: %s" % _e_row
        out["counts"][row["status"]] = out["counts"].get(row["status"], 0) + 1
        out["rows"].append(row)
    return out


# ---- 批196 · 本地浏览器「一键启动 + 富状态」（老板：不能让老板自己去 PowerShell 起客户端）----
# 设计要点：
#   · 启动命令与参数**硬编码在模块级**（页面只能传 user_id）⇒ 页面无法把它指向别的账号/别的端口/别的程序；
#   · 已连接时**不重复启动**；15s 冷却（防连点）；
#   · 走 WSL→Windows interop（cmd.exe start）⇒ 客户端在 Windows 侧运行（它要驱动 Windows Chrome）。
# Windows 副本(2026-09-19): 客户端正本 = 仓库内 scripts/agent_client。
# WSL 版当年把它放在 Windows 桌面, 靠 cmd.exe interop 从 WSL 拉起; Windows 版同仓同栈, 不需要这层。
_REPO_AGENT_CLIENT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts", "agent_client"
)


def _local_client_dir():
    """客户端目录(模块级常量, 页面无法改): 唯仓库内 scripts/agent_client。

    ⭐ 2026-10-06（pm_1409 §二.3 · 批三）：旧桌面回落（Windows 用户桌面之**字面径**）⇒ **删**
    （开发机专用 · 承「开发期／我方通道 ⇒ 删」）。缺 ⇒ 空串 ⇒ `local_client_launchable()`
    判不可启动（⛔ 崩 · 照实「未接」）。
    """
    return _REPO_AGENT_CLIENT if os.path.isdir(_REPO_AGENT_CLIENT) else ""


def _local_client_ws_url():
    """WS 目标 = browser_local.ws_port()（端口唯一真源）。

    不在这里复述端口号：两处各写一个数字时，改一处就会把客户端静默指到旧端口
    （Windows 副本实测: 5007 不可绑，且是 WSL 实例的端口 ⇒ 本机动作有发到 WSL 网关的风险）。
    取不到 ⇒ 返回空串（fail-loud：宁可启不起，不静默连错）。
    """
    try:
        from core.lib.v8.browser_local import ws_port as _wp

        return "ws://127.0.0.1:%d" % _wp()
    except Exception:
        return ""


# ⭐ 2026-10-06（pm_1409 §二.3 · 批三）：客户端之 pythonw（原为开发机之字面径）⇒ env ∨ 自推。
def _client_python():
    u"""客户端之 pythonw（⛔ 字面开发机径）。

    env `PA_CLIENT_PYTHON` ⇒ 用；缺 ⇒ 自 `sys.executable` 之邻 `pythonw.exe` 推（**产品级**）；
    再缺 ⇒ 空串（`local_client_launchable()` 判不可启动 · 照实「未接」）。
    """
    _v = (os.environ.get("PA_CLIENT_PYTHON") or "").strip()
    if _v:
        return _v
    try:
        _c = os.path.join(os.path.dirname(sys.executable or ""), "pythonw.exe")
        return _c if os.path.exists(_c) else ""
    except Exception:
        return ""


LOCAL_CLIENT = {
    "cmd_exe": cmd_exe(),
    "win_dir": _local_client_dir(),
    "win_python": _client_python(),
    "script": "agent_client.py",
    "ws": _local_client_ws_url(),
    "extra_args": ["--chrome"],
}
LOCAL_CLIENT_COOLDOWN_S = 15.0
LOCAL_CLIENT_GUARD = {"ts": 0.0}  # 模块级（可测：单测直接重置它）


def local_client_launchable():
    """能不能一键启动：Windows 侧 cmd.exe 与 agent_client.py 都在（**未观察到 ≠ 可用**）。"""
    try:
        _script = os.path.join(LOCAL_CLIENT["win_dir"], LOCAL_CLIENT["script"])
        return bool(os.path.exists(LOCAL_CLIENT["cmd_exe"])) and bool(os.path.exists(_script))
    except Exception:
        return False


def local_client_command(user_id):
    """构造启动命令（**唯一出口**：单测断言它不接受任何请求侧字符串）。"""
    return [
        LOCAL_CLIENT["cmd_exe"],
        "/c",
        "start",
        "",
        "/D",
        LOCAL_CLIENT["win_dir"],
        LOCAL_CLIENT["win_python"],
        LOCAL_CLIENT["script"],
        "--user-id",
        str(user_id),
        "--ws",
        LOCAL_CLIENT["ws"],
    ] + list(LOCAL_CLIENT["extra_args"])


def _code_sha16(_o, *_more):
    u"""⭐ PM 089 §二（令）：**器之身份** —— 本路由之码之 `sha16`（**印须载器** · 承 `1018 §一`）。

    由：印之义 ＝ 「**以此器** · 以此面滤式 ⇒ 此数」⇒ **⛔ 载器 ⇒ 读者不知何版所出**（半个印）。
    ⛔ 人立之版号（承 `1018 §一`：**号可被默改** ⇒ 印稳而实 ⛔ 稳）。
    取 `inspect.getsource(_o)` ＝ **本路由之码**（⛔ 本模块之全文）；取不到 ⇒ 回落**本模块之字节**（皆为器之身份）。
    ⛔ 两路皆败 ⇒ `None` ⇒ ⭐ **调用方须 `印 = null`**（照实「未核」· ⛔ 以**缺器之印**冒充载器之印）。
    ⚠ 本模块级 ⛔ 增导 ⇒ **局部导入**（承 L22 之族）｜实测取价 ≈ `1.5 ms`／次（`100` 次均值）。
    ⭐ T2-刀26 §二（PM 裁 2026-10-05 17:55）：**印须载「产生此数之器之真源」** —— `_more` 承**面之真源**
      （如 `core/pa/lines.py` 之**模块源**）⇒ 印 ＝ `sha16(路由源 ＋ 真源)`；⛔ 传 `_more` ⇒ **旧义逐字同**（向后兼容）。
    """
    import hashlib, inspect
    _parts = []
    for _x in (_o,) + tuple(_more):
        try:
            _parts.append(inspect.getsource(_x).encode("utf-8"))
        except Exception:
            _parts.append(None)
    if any(_p is None for _p in _parts):
        try:
            with open(__file__, "rb") as _fh:
                _b = _fh.read()
        except Exception:
            return None
    else:
        _b = b"".join(_parts)
    return hashlib.sha256(_b).hexdigest()[:16]


def register_pa_routes(app, brain=None):
    """把 PA 路由挂到 Flask app。brain: 可选 callable(context_text)->str (LLM 对话脑)。"""
    bp = Blueprint("pa_routes", __name__)

    def ok(payload=None, **kw):
        doc = {"ok": True}
        if payload is not None:
            doc.update(payload)
        doc.update(kw)
        return jsonify(doc)

    def err(msg, code=400):
        return jsonify({"ok": False, "error": str(msg)[:300]}), code

    # ---- 批196 · 本地浏览器：一键启动 + 富状态（实现见模块顶部 LOCAL_CLIENT / local_client_command）----
    @bp.route("/v9/pa/local_client/status", methods=["GET"])
    def pa_local_client_status():
        uid = request.args.get("user_id") or ""
        info = {"connected": False, "client": ""}
        try:
            from core.lib.v8 import browser_local as _bl

            info = _bl.get_connection_info(uid)
        except Exception as _e_info:
            info = {"connected": False, "client": "", "error": str(_e_info)[:200]}
            _bl = None
        out = dict(info)
        out["launchable"] = local_client_launchable()
        out["印"] = _code_sha16(pa_local_client_status) if _bl is None else _code_sha16(pa_local_client_status, _bl)
        return ok(out)

    @bp.route("/v9/pa/local_client/start", methods=["POST"])
    def pa_local_client_start():
        """一键启动 Windows 侧 agent_client（命令硬编码；页面只能传 user_id）。"""
        import subprocess
        import time as _time

        data = request.get_json(silent=True) or {}
        uid = str(data.get("user_id") or request.args.get("user_id") or "")
        if not uid.startswith("web_"):
            return err("user_id 非法（只允许 web_* 本机用户）", 400)
        try:
            from core.lib.v8 import browser_local as _bl

            _info = _bl.get_connection_info(uid)
        except Exception:
            _info = {"connected": False}
        if _info.get("connected"):
            return ok({"started": False, "already": True, "client": _info.get("client", "")})
        now = _time.time()
        _last = float(LOCAL_CLIENT_GUARD.get("ts") or 0)
        if now - _last < LOCAL_CLIENT_COOLDOWN_S:
            return ok({"started": False, "cooldown": round(LOCAL_CLIENT_COOLDOWN_S - (now - _last), 1)})
        if not local_client_launchable():
            return err("Windows 侧客户端不可启动：cmd.exe 或 agent_client.py 未找到", 500)
        cmd = local_client_command(uid)
        try:
            _proc.popen_hidden(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as _e_start:
            return err("启动失败：%s" % _e_start, 500)
        LOCAL_CLIENT_GUARD["ts"] = now
        print("[PA_LOCAL_CLIENT] 已请求启动桌面 agent_client user=%s（参数硬编码，未接受前端输入）" % uid)
        return ok({"started": True, "hint": "已在 Windows 侧启动；等 5~20 秒，状态会自动变为已连接"})

    # ---- pm_1684 §四（契约）：更新之「动」之端 —— 读一处（/health）· 动分端 ----
    @bp.route("/v9/pa/update", methods=["POST"])
    def pa_update_run():
        u"""更新之「动」（承 pm_1684 §四 契约 · 一处定形）。

        体 `{"action": "start"}` ⇒ 起一支（**幂等**：已在跑 ⇒ 回 `running` ∧ ⛔ 起第二支）；
        体 `{"action": "status"}` ∨ 缺 ⇒ **唯读**（⛔ 副作用 —— 面之轮询用之）。
        回 `{ok, phase, note, note_why, …}`；`phase ∈ idle ／ running ／ done ／ failed`。
        ⚠ `idle` ＝ 本席之补（pm_1684 之枚举唯三；「未曾跑」须有一值 —— 空 ⛔ 混 缺）。
        唯本机（⛔ 外网）；正式期须**一次性令牌** —— 复用 `provider_keys` 之形（**记债**）。
        器之状**落盘**（`core/lib/update_run.py`）⇒ 跨「停 → 换 → 起」可察终态
          （网关自停 ⇒ 其进程内 ⛔ 可察 ⇒ 唯盘上之态可读）。
        """
        import subprocess as _sp
        import sys as _sys

        from core.lib import update_run as _UR
        from core.lib import update_source as _US

        if not _loopback(request):
            return err("此端唯本机可用（来源 %s）" % (request.remote_addr or "?"), 403)
        body = request.get_json(silent=True) or {}
        act = str(body.get("action") or "status").strip().lower()
        if act not in ("start", "status"):
            return err("未知之 action：%s（唯 start ／ status）" % (act or "—"), 400)
        root = _US.root_dir()
        if act == "start" and _UR.phase(root).get("phase") != "running":
            _UR.begin(root)                                   # 起态先落 ⇒ 轮询即见 running
            # ⭐ pm_1799 §二.3⒜（**「停／起服务」归壳** · ⛔ 由页内后端自行停／起）：
            #   本端昔以默认之器起（其第 ⑥ 步停网关 · 第 ⑨ 步起 —— 而净机「起」⛔ 成 ⇒
            #   正控 ⛔ 过 ⇒ 回滚 ⇒ rc=2 ⇒ 页内「一键」恒败）。同机之 `fix-update2.cmd`
            #   唯多一个 `--no-restart` ⇒ **成** —— 两条路之**唯一**差别即此。
            #   ⇒ 今同其形：换完即止 ⇒ 页显「已就位 · 请关窗重开」（生效归壳之「重启服务」）。
            #   ⚠ 由之要：**停／起之能归壳**（生命周期是壳之物）⇒ 后端 ⛔ 越俎自停自起。
            argv = [_sys.executable, u"-X", u"utf8", u"-B",
                    os.path.join(root, u"scripts", u"win_pa", u"pa_update.py"),
                    u"--root", root, u"--go", u"--json", u"--no-restart"]
            # 起法与 `pa_nowindow.cmd_start` 同族（`NO_WINDOW ｜ DETACHED ｜ BREAKAWAY`）：
            #   器须**后于**调用者而存。昔之由为「第 ⑥ 步停网关」；今路已改 `--no-restart`
            #   ⇒ 仍留此旗者：老板若于更新**中途关窗** ⇒ 器亦须⛔ 随之亡（序未完 ⇒ 半成品）。
            # pm_1791 §三.3：⛔ 于调用处手写 `creationflags` —— 旗唯 `_proc`
            #   一处定形（`_proc.DETACH_FLAGS` · 承「窗隐唯 `_proc` 出口」）。
            # ⚠ 流之 `DEVNULL` **非「弃其真因」**（pm_1799 §二.2）：器**自落**其全部输出
            #   （`<upd_dir>/log-<目标版>.txt` · `pa_update._Sink`）⇒ 端弃不掉它；
            #   且 ⛔ 宜以「不读之管道」接之（器之输出可溢 ⇒ 器自阻）。
            try:
                _proc.popen_detached(argv, cwd=root, stdin=_sp.DEVNULL,
                                     stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
            except OSError:                                   # BREAKAWAY ⛔ 许（本进程在 job 中）⇒ 退
                try:
                    _proc.popen_hidden(argv, cwd=root, stdin=_sp.DEVNULL,
                                       stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
                except Exception as _e_up:                    # noqa: BLE001 — 照实报因
                    _UR.finish(root, rc=2, note_why=u"%s: %s" % (type(_e_up).__name__, _e_up))
                    return err("起器⛔ 成：%s" % _e_up, 500)
        return ok(_UR.phase(root), 印=_code_sha16(pa_update_run, _UR))

    @bp.route("/v9/pa/context", methods=["GET"])
    def pa_context():
        pa = _core(request.args.get("user_id"))
        r = pa.handle("context")
        _conf = sorted(pa.profile.entries_by_domain(status="confirmed"), key=lambda e: e.get("date", ""), reverse=True)
        prof = _conf[:20]
        # ⭐ T2-刀10（2026-10-05 · PM 补令）：**待裁**之真源 ＝ 画像 `status="proposed"`
        #   ⚠ 病：旧面**唯下 `confirmed`** ⇒ 前端「待裁 0」是**假数**（实 4 条）
        #             ⇒ 承「空 ⛔ 混 缺」：**未下** ⇔ **真为 0** ⇔ 不可辨
        _prop = sorted(pa.profile.entries_by_domain(status="proposed"), key=lambda e: e.get("date", ""), reverse=True)
        _all_n = len(pa.profile.entries_by_domain())
        led = pa.ledger.open_items()
        # ⭐ PM 2026-10-04（承 投递 1049 §三.1）：画像件之径须由后端下发（⛔ 前端硬编常量）
        import hashlib as _hl
        import datetime as _dt
        from core.pa import pa_core as _PC
        from core.pa import profile as _PF

        _pf = pa.profile.path
        _pfi = {"path": str(_pf), "exists": False, "mtime": None, "sha16": None}
        try:
            if _pf.is_file():
                _pfi["exists"] = True
                _pfi["mtime"] = _dt.datetime.fromtimestamp(_pf.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                _pfi["sha16"] = _hl.sha256(_pf.read_bytes()).hexdigest()[:16]
        except Exception as _pe:
            _pfi["error"] = "profile_file 读取失败：%s: %s" % (type(_pe).__name__, _pe)
        _out = {
                "brief": r.get("profile", ""),
                "ledger_brief": r.get("ledger", ""),
                "profile": prof,
                "proposed": _prop,   # ⭐ T2-刀10：**待裁**集（画像 `status=proposed` · ⛔ 混入 `confirmed`）
                "ledger": led,
                "profile_file": _pfi,
                # ⭐ PM 2026-10-04（承 955 §五）：`num_ctx` 之真源（与 llm_client 同源 env · 前端上屏「实到值」用）
                "num_ctx": int(os.environ.get("CLAWSJOY_NUM_CTX", "8192")),
                # ⭐ PM 2026-10-05（承 CW 1067 §五.③ · L83 单源）：自测痕词表之**真源**
                #   前端 ⛔ 自持一份（两表必漂）⇒ 取此键
                "selftest_marks": list(PA_SELFTEST_MARKS),
                "counts": {"profile": len(prof), "ledger": len(led), "pending": len(_prop)},
                "proposed_judge": {
                    "面之径逐字": "data/v9/pa/profile.json",
                    "判据": "status == 'proposed'（⛔ 非 `confirmed`）",
                    "entries_total": _all_n,
                    "注": "「待裁」＝画像待老板圈定之条 · ⛔ 同于「审批待审」",
                },
            }
        _out["印"] = _code_sha16(pa_context, _PC, _PF)
        return ok(_out)

    @bp.route("/v9/pa/profile", methods=["GET"])
    def pa_profile():
        from core.pa import profile as _PF
        pa = _core(request.args.get("user_id"))
        d = request.args.get("domain") or None
        return ok({"entries": pa.profile.active(d)}, 印=_code_sha16(pa_profile, _PF))

    @bp.route("/v9/pa/profile/schema", methods=["GET"])
    def pa_profile_schema():
        """字段表 + 当前取值 + 推导能力开关 —— 前端按此渲染表单（不硬编码字段）。"""
        from core.pa.profile import FIELD_SCHEMA, capability_switches, field_schema, get_fields
        from core.pa import profile as _PF

        pa = _core(request.args.get("user_id"))
        vals = get_fields(pa.profile)
        # order: Flask jsonify 默认按 key 排序, 字段顺序必须显式下发(表单按语义排, 不按字母)
        return ok(
            {
                "fields": field_schema(),
                "order": list(FIELD_SCHEMA.keys()),
                "values": vals,
                "switches": capability_switches(vals),
            },
            印=_code_sha16(pa_profile_schema, _PF),
        )

    @bp.route("/v9/pa/profile", methods=["POST"])
    def pa_profile_write():
        """参数化收集写入口：表单(source=form) 与 聊天(source=chat) **同一条落库路径**。

        body: {values:{字段:取值}, source, user_id}；取值不合法进 rejected 不落库。
        """
        from core.pa.profile import capability_switches, collect_fields, get_fields

        p = request.json or {}
        values = p.get("values") or {}
        if not isinstance(values, dict) or not values:
            return err("profile 写入需要 values:{字段:取值}")
        src = p.get("source") or "form"
        pa = _core(p.get("user_id"))
        r = collect_fields(pa.profile, values, source=src)
        pa.events.append(
            "fact",
            "field_collect",
            {
                "source": src,
                "values": values,
                "written": [w["key"] for w in r["written"]],
                "rejected": [x["key"] for x in r["rejected"]],
            },
            source=src,
        )
        vals = get_fields(pa.profile)
        return ok(
            {
                "written": r["written"],
                "unchanged": r["unchanged"],
                "rejected": r["rejected"],
                "fields": vals,
                "switches": capability_switches(vals),
            }
        )

    @bp.route("/v9/pa/sediment", methods=["POST"])
    def pa_sediment():
        pa = _core((request.json or {}).get("user_id"))
        p = request.json or {}
        if not p.get("domain") or not p.get("value"):
            return err("sediment 需要 domain + value")
        r = pa.handle("profile_sediment", p)
        return ok(r) if r.get("ok") else err(r.get("error"))

    @bp.route("/v9/pa/dialog", methods=["POST"])
    def pa_dialog():
        pa = _core((request.json or {}).get("user_id"))
        p = request.json or {}
        text = (p.get("text") or "").strip()
        if not text:
            return err("dialog 需要 text")
        sid = p.get("session_id") or "pa_default"
        # ⭐ PM 043 §二.1（P7 裁）：档 ＝ **显式拨杆（前端）之单源** ⇒ 后端只认 `mode`，⛔ 推断。
        #   本机真脑（llm_brain 所造 · `_is_pa_brain`）按 mode 重组系统提示；注入之别脑（测试）⛔ 覆盖。
        _mode = p.get("mode")
        # ⭐ P2 ①（pm_1449 §二.1）：模型唯**会话档**出 ∨ 本轮所请
        #   （后端白名单验 ⇒ ⛔ 自由字串；非法 ⇒ 400 显因 · ⛔ 静默回落）
        _uid = _uid_safe(p.get("user_id"))
        _model, _model_src = session_model_of(_uid, p.get("model"))
        if _model is None and str(p.get("model") or "").strip():
            return err(_model_src, 400)
        _t0 = time.perf_counter()   # ⭐ 057：本轮墙钟之起点（器取）
        _brain = (llm_brain(system_prompt=pa_system_for(_mode), model=_model)
                  if getattr(brain, "_is_pa_brain", False) else brain)
        # 就事论事: 把"目标/议题"一起带给对话脑, 不是闲聊
        # ⭐ PM 2026-10-05 22:34 §四⒝-2：**源标透传**（档行外加性键 · ⛔ 改答话体）
        r = pa.handle("dialog_post", {"sid": sid, "text": text, "topic": p.get("topic"), "brain": _brain,
                                      "origin": p.get("origin"), "grounded": p.get("grounded"),
                                      "answer_source": p.get("answer_source")})
        reply = (r.get("dialog") or {}).get("reply") or "（PA 脑暂不可用：已记录本条，稍后可继续商量）"
        # ⭐⭐ pm_1802 §一.2（令）：**⛔ 不实之辞入屏** —— 本通道只商量（⛔ 出手）
        #   ⇒ 答体若现「未做而似做」之辞（**字面逐条见 `PA_CHANNEL_CLAUSE` 之禁辞表**）
        #   ⇒ **结构化标出**（⛔ 静默放行 · ⛔ 改用户面之辞）：`channel.untrue_wording` 载逐条。
        #   ⚠ 字面**转义写**（承 L56-57 · 与 `label_hits` 同族）。
        _untrue_hits = [_s for _s in (u"\u5df2\u53d7\u7406", u"\u5df2\u5b89\u6392",
                                      u"\u5df2\u8f6c\u529e", u"\u6b63\u5728\u5904\u7406")
                        if _s in (reply or "")]
        # ⭐ PM 038 §一.1（老板令 2026-10-05）：聊天 ＝ **陪伴** ⇒ ⛔ 以聊天为采集器。
        #   旧路（detect_fields ⇒ collect_fields(source="chat")）已**撤** —— 画像之新源
        #   ＝ 全部会话上下文之抽取器（R3 · 另规格）。表单路 /v9/pa/profile 仍为显式入口。
        #   `collected` 键保留（空）＝ 回执形不变（前端半另件 pm_1091）。
        collected = {"written": [], "unchanged": [], "rejected": []}
        # ⭐ BUG-1：把「本轮已落盘」从**前端推断**改成**后端回执**。
        # 判据（PM 006）：发一条 ⇒ events.jsonl 行数 +1 ∧ 会话 jsonl 有本轮 ⇒ 前端才许说「已落盘」。
        _sess = pa.dialog.session(sid)
        _ev_before = _jsonl_lines(pa.events.path)
        # ⚠ 会话行数同样要防「读不到」：旧写法裸调 history() ⇒ 会话文件被独占时**抛异常 ⇒ 整条路由 500**，
        #   前端连回执都拿不到 ⇒ 「读数不可得」被静默并进「确实没落盘」（PM 裁的口径正是不许并）。
        try:
            _ses_lines = len(_sess.history(100000))
        except Exception:
            _ses_lines = None
        _ev_err = ""
        try:
            pa.events.append("dialog", "turn", {"sid": sid, "chars": len(text)}, source="pa/dialog")
        except Exception as _e_ev:
            _ev_err = str(_e_ev)[:200]
        _ev_after = _jsonl_lines(pa.events.path)
        _persisted = {
            "session_id": sid,
            "session_path": str(_sess.path),
            "session_lines": _ses_lines,
            "session_bytes": _sess.path.stat().st_size if _sess.path.is_file() else 0,
            "events_path": str(pa.events.path),
            "events_lines_before": _ev_before,
            "events_lines_after": _ev_after,
            "events_delta": _lines_delta(_ev_before, _ev_after),
            "events_readable": _ev_before is not None and _ev_after is not None,
            "session_readable": _ses_lines is not None,
            "error": _ev_err,
            "recorded": bool(_ses_lines is not None and _ses_lines >= 2
                             and _ev_before is not None and _ev_after is not None
                             and _ev_after > _ev_before),
        }
        # ⭐ PM 034 §三.⒝ ／ 037 §A.2：走径标取自**后端实况**（⛔ 前端自说）；
        # 回落 ⇒ 人话（⛔ 说成「正常」）。
        from core.pa.providers import (src_label as _src_label,
                                       fallback_note as _fallback_note,
                                       route_kind as _route_kind)

        _route = dict(getattr(_brain, "last_route", None) or {}) if _brain else {}
        # ⭐ pm_1460 §一（裁）：**回执必给 `kind`**（`local` ／ `remote` ·
        #   一处定形 ＝ `providers.route_kind` · 与 `src_label` 同源 `PROVIDER_KIND`
        #   · ⛔ 前端猜 ／ ⛔ 由 `model` 名反推）。
        #   由：前端「出机」之标（红线）唯 `kind ∈ 远端集` 时上屏
        #   ⇒ 无 `kind` ⇒ **红线恰于演示（走云端）时失效**。
        #   唯加键（⛔ 改既有字段之语义）；空 route（⛔ 走模型）⇒ 自不加。
        if _route:
            _route["kind"] = _route_kind(_route)
        # ⭐ 057 §一：成本轴（器取 · 唯加键 ⇒ ⛔ 改既有字段之语义）。
        #   ⒜ wall_s 墙钟 ⒝ bytes 入／出分列 ⒞ tokens 模型径（无 ⇒ None）⒟ money 外呼花费。
        #   ⭐ 对内对外分轴（PA-5：⛔ 对用户按 token 计费）⇒ 本轴属**内部成本闸**，用户面由前端择取。
        _tok = _route.get("tokens")
        _prov = str(_route.get("provider") or "")
        _remote = (_prov == "deepseek")
        _cost = {
            "wall_s": round(time.perf_counter() - _t0, 3),
            "bytes": {"in": len(text.encode("utf-8")), "out": len(reply.encode("utf-8"))},
            "tokens": _tok,
            "money": (round((_tok or 0) / 1000.0 * 0.001, 8) if _remote else 0.0),
            "currency": "CNY",
            "source": ("remote:" + _prov) if _remote else ("local:" + (_prov or "none")),
            "tokens_source": ("llm_client._stats.total_tokens(本轮)" if _tok is not None else "无"),
            "phase": ("warm" if _LLM_PHASE["warmed"] else "cold"),
        }
        _LLM_PHASE["warmed"] = True
        # ⭐ 058 §一.2（裁）：**活动轴** —— 每一用户可见之轮须有一行（本地轮 `cost=0.0` ＋ 墙钟）。
        #   ⛔ best-effort：记不上 ⇒ 回执照出（⛔ 因记账而断主路）· 但**如实报** `recorded=False`。
        _activity = {"recorded": False, "axis": "activity", "wall_s": _cost["wall_s"],
                     "error": ""}
        try:
            from core.lib.v8.ledger import ledger as _led_act
            _led_act.record_activity(
                server_id="default", agent_name="pa_dialog", position="PA对话",
                model=str(_route.get("model") or ""), tokens=_tok, wall_s=_cost["wall_s"],
                task_id=sid, summary="PA轮 sid=%s src=%s phase=%s" % (sid, _cost["source"], _cost["phase"]),
                currency="CNY", source=_cost["source"],
                nbytes=_cost["bytes"])        # ⭐ PM 088 §三（令）：体量轴入账（唯加 `bytes` 键）
            _activity["recorded"] = True
        except Exception as _e_act:
            _activity["error"] = str(_e_act)[:200]
        return ok(
            {
                # ⭐ pm_1478 §二：本轮之**取数刻**（回执必给 · 唯加键）——
                #   前端走径行刻（`more.js` 探针取 `read_at || at`）之真源。
                "read_at": _pa_read_at(),
                "reply": reply,
                "topic": (r.get("dialog") or {}).get("topic", ""),
                "session_id": sid,
                "collected": collected,
                "persisted": _persisted,
                "route": _route,
                "mode": pa_mode_name(_mode),
                # ⭐ P2 ①：本轮实用之模型 ＋ 其源（唯加键 · ⛔ 破既有字段）
                "model": _model or "",
                "model_source": _model_src,
                "src": _src_label(_route),
                "fell_back": bool(_route.get("fell_back")),
                "fallback_note": _fallback_note(_route),
                # ⭐ pm_1486 §二.1：闸之实 ⇒ 结构化判据（一处定形 · 唯加键）
                "gate": pa_gate_view(decision=p.get("gate_decision"), origin=p.get("origin"), grounded=p.get("grounded"), answer_source=p.get("answer_source"), fact_family=p.get("fact_family")),
                "cost": _cost,
                # ⭐ pm_1802 §一.2／§一.3：本通道**能不能动手**之结构化据（唯加键 · ⛔ 破既有）。
                "channel": {"kind": "dialog", "acts": False, "untrue_wording": _untrue_hits},
                "activity": _activity,
            }
        )

    @bp.route("/v9/pa/dialog", methods=["GET"])
    def pa_dialog_history():
        from core.pa import pa_core as _PC
        """会话读面。BUG-3：**不带 session_id ⇒ 回最近会话**。

        为什么：写面把每轮落进 sessions/session_<sid>.jsonl（sid = 前端线程 id），
        而旧读面固定按 pa_default 读 ⇒ 读面与写面不是同一个面（判据打错对象），
        于是「刚说过一轮、读面仍空」被读成「没接线」。这里把默认改成最近会话，
        并把 sessions 清单一起给出，读面才**能回答「刚才那轮记下没有」**。
        """
        pa = _core(request.args.get("user_id"))
        n = int(request.args.get("n") or 30)
        sid = (request.args.get("session_id") or "").strip()
        _inv = _dialog_sessions(pa)
        if not sid:
            sid = _inv[0]["session_id"] if _inv else "pa_default"
        r = pa.handle("dialog_context", {"sid": sid, "n": n})
        r["session_id"] = sid
        r["sessions"] = _inv
        r["store"] = str(pa.dir / "sessions")
        r["印"] = _code_sha16(pa_dialog_history, _PC)
        return ok(r)

    @bp.route("/v9/pa/sessions", methods=["GET"])
    def pa_sessions_list():
        """真源清单（只读 · 薄别名 · 裁 1 ／ PM 051 §一）。

        与 `GET /v9/pa/dialog` 之 `sessions[]` 逐值同（同走 `_dialog_sessions`）。
        ⛔ 含 `history`（那属 dialog 之能）· ⛔ 含页态键（`threads` ／ `activeThread` ／
        `session_bound` ／ `session_unbound` —— 承 049 §二「⛔ 以页态冒真源」之戒）。
        `lines` 为 `None` ＝ **读不到**（⛔ 不是 `0`）。只读：⛔ 写 ／ ⛔ 起会话。
        """
        pa = _core(request.args.get("user_id"))
        from core.pa import pa_core as _PC
        return ok({"sessions": _dialog_sessions(pa), "store": str(pa.dir / "sessions")}, 印=_code_sha16(pa_sessions_list, _PC))

    @bp.route("/v9/pa/turn", methods=["POST"])
    def pa_turn_record():
        """记一轮对话（工作/开发模式的**落盘出口** · BUG-1）。

        为什么需要它：工作模式走 /v9/agent/chat（通用执行通道，不写 PA 记录），
        于是「PA 页面被用过」在 PA 自己的面上零痕迹，而页面却显示「已落盘」。
        本路由只记不动手：把该轮追加进会话 jsonl ＋ 一条事件，并返回**回执**。
        """
        pa = _core((request.json or {}).get("user_id"))
        _t0 = time.perf_counter()   # ⭐ 057：本轮墙钟之起点（器取）
        p = request.json or {}
        sid = (p.get("session_id") or "").strip() or "pa_default"
        _u = str(p.get("user_text") or "")
        _a = str(p.get("assistant_text") or "")
        if not _u and not _a:
            return err("turn 需要 user_text 或 assistant_text")
        _sess = pa.dialog.session(sid)
        _ev_before = _jsonl_lines(pa.events.path)
        _before = _jsonl_lines(_sess.path)
        # ⚠ 两条写腿要对称：events 腿有 try/except，会话腿原本裸调 ⇒ 会话文件被占时
        #   **抛异常 ⇒ 整条路由 500**，前端连回执都拿不到 ⇒ 两种事又被并成一种。
        _ses_err = ""
        # ⭐ PM 2026-10-05 22:34 §四⒝-2：**源标透传**（本路与 `/v9/pa/dialog` 同键同义 · 承「两写路同形」）
        #   ⚠ 缺省 `unspecified`（调用方未声明）—— ⛔ 冒 `model` ／ ⛔ 冒 `grounded`
        #     （承「⛔ 以我之预期充文本之实」）；前端知其实（如闸已拒）⇒ 显式传 `refused` ／ `grounded`。
        #   ⭐ PM 1183 §五.3：档行键 `src` ⇒ **`origin`**（一名一义 —— 与响应之 `src`（＝走径标）别）。
        from core.pa.dialog import ORIGIN_UNSPECIFIED   # ⭐ 源标之词表（一处定义 · 在 dialog.py）
        _org_v = p.get("origin") or ORIGIN_UNSPECIFIED
        _gr_v = p.get("grounded")
        _as_v = p.get("answer_source")
        try:
            if _u:
                _sess.post("user", _u)
            if _a:
                _sess.post("assistant", _a, origin=_org_v, grounded=_gr_v, answer_source=_as_v)
        except Exception as _e_ses:
            _ses_err = str(_e_ses)[:200]
        _err = ""
        try:
            pa.events.append("dialog", "turn", {"sid": sid, "mode": p.get("mode"), "chars": len(_u)}, source="pa/turn")
        except Exception as _e_ev:
            _err = str(_e_ev)[:200]
        _after = _jsonl_lines(_sess.path)
        _ev_after = _jsonl_lines(pa.events.path)
        _ev_readable = _ev_before is not None and _ev_after is not None
        _ses_readable = _before is not None and _after is not None
        # ⭐ 057 §一：本路由**唯记不动手**（无脑径）⇒ tokens 如实为 None ／ money 恒 0。
        _cost = {
            "wall_s": round(time.perf_counter() - _t0, 3),
            "bytes": {"in": len(_u.encode("utf-8")), "out": len(_a.encode("utf-8"))},
            "tokens": None,
            "money": 0.0,
            "currency": "CNY",
            "source": "record-only",
            "tokens_source": "无",
        }
        return ok({
            "session_id": sid,
            "session_path": str(_sess.path),
            "session_lines_before": _before,
            "session_lines_after": _after,
            "session_delta": _lines_delta(_before, _after),
            "events_path": str(pa.events.path),
            "events_lines_before": _ev_before,
            "events_lines_after": _ev_after,
            "events_delta": _lines_delta(_ev_before, _ev_after),
            "events_readable": _ev_readable,
            "session_readable": _ses_readable,
            "session_error": _ses_err,
            "error": _err or _ses_err,
            "recorded": bool(_ses_readable and _ev_readable
                             and _after > _before and _ev_after > _ev_before),
            "gate": pa_gate_view(decision=p.get("gate_decision"), origin=p.get("origin"), grounded=p.get("grounded"), answer_source=p.get("answer_source"), fact_family=p.get("fact_family")),
            "cost": _cost,
        })

    @bp.route("/v9/pa/ask", methods=["POST"])
    def pa_ask():
        """BUG-2：**有据才答**（反例门：库里没有的问题 ⇒ 100% 答「查不到」）。

        判据（PM 006）：N 条「库里没有」的问题必须 100% 拒答。
        实现：先检索、后作答 ——
          · 有命中 ⇒ 返回证据（文件 ＋ 行号）＋ grounded=True（结论仍须带出处，⛔ 本路由不编结论）；
          · 无命中 ⇒ 当场拒答（refused=True），且**不调用模型**（没有据，就没有可编的空间）；
          · searched==0（知识库面不可达）⇒ 判「不适用」，⛔ 不算「拒答成功」（三态纪律）。
        """
        from datetime import datetime as _dt2

        p = request.json or {}
        q = (p.get("question") or "").strip()
        if not q:
            return err("ask 需要 question")
        kb = _kb_root_str()   # ⭐ pm_1500 §二：**唯此一处**判「库根未接」（⛔ 各判「空」 · ⛔ `None` 之假径）
        _at = _pa_read_at()   # ⭐ pm_1478 §二：一处定形（⛔ 二处各打时戳）
        _fact_family = bool(p.get("fact_family"))   # ⭐ pm_1493 §三：前端之**结构判**（本机事实族 · ⛔ 辞）⇒ 转交
        _tk0 = time.perf_counter()   # ⭐ 058：本轮检索之起点（器取）
        # ⭐ 修①（PM 2026-10-05 · 老板实测之修）：**决策账 ⇒ 直取本机**（⛔ 回落模型）
        _dec = _ask_decision(q, p.get("user_id"), p.get("session_id"))
        if _dec is not None:
            _j = {"threshold": None, "faces_version": PA_FACES_VERSION, "faces_count": 0,
                  "faces_files_total": 0, "face_snapshot_at": None, "judge_at": _at}
            _bb = {"question": q, "read_at": _at, "kb_root": str(kb), "searched": 0,
                   "scope": [], "threshold": None, "faces": {}, "faces_missing": [],
                   "faces_skipped": {}, "evidence": [], "archive_hits": [], "judge": _j,
                   "ask_domain": "decision",
                   "gate": pa_gate_view(decision="grounded", fact_family=_fact_family),
                   "refusal_canon": PA_ASK_REFUSAL, "refusal_stale": PA_ASK_REFUSAL_STALE}
            _bb.update(_dec)
            return ok(_bb)
        # ⭐ 死件账之直读路（PM 2026-10-05 22:34 §三① 准 · 同修①之形 · ⛔ 改闸之判据）
        _dead = _ask_deadfile(q)
        if _dead is not None:
            _j = {"threshold": None, "faces_version": PA_FACES_VERSION, "faces_count": 0,
                  "faces_files_total": 0, "face_snapshot_at": None, "judge_at": _at}
            _bb = {"question": q, "read_at": _at, "kb_root": str(kb), "searched": 0,
                   "scope": [], "threshold": None, "faces": {}, "faces_missing": [],
                   "faces_skipped": {}, "evidence": [], "archive_hits": [], "judge": _j,
                   "ask_domain": "deadfile",
                   "gate": pa_gate_view(decision="grounded", fact_family=_fact_family),
                   "refusal_canon": PA_ASK_REFUSAL, "refusal_stale": PA_ASK_REFUSAL_STALE}
            _bb.update(_dead)
            return ok(_bb)
        if _ask_scope(q) == "meta":                  # ⭐ ② 元问 ⇒ 走会话路（⛔ 检索闸 · 承 L151）
            _prev, _ctx = _last_user_before(_core(p.get("user_id")), q, p.get("session_id"))
            _j = {"threshold": None, "faces_version": PA_FACES_VERSION, "faces_count": 0,
                  "faces_files_total": 0, "face_snapshot_at": None, "judge_at": _at}
            _bb = {"question": q, "read_at": _at, "kb_root": str(kb), "searched": 0, "scope": [],
                   "threshold": None, "faces": {}, "faces_missing": [], "faces_skipped": {},
                   "evidence": [], "archive_hits": [], "judge": _j,
                   "ask_domain": "meta", "context_meta": _ctx,
                   "gate": pa_gate_view(decision="not_asked", fact_family=_fact_family),
                   "refusal_canon": PA_ASK_REFUSAL, "refusal_stale": PA_ASK_REFUSAL_STALE}
            if _prev:
                return ok({"grounded": False, "refused": False, "answer_source": "context",
                           "answer": _prev, "context_prev": _prev,
                           "verdict": "上下文（本会话上一句 · ⛔ 检索面）", **_bb})
            # ⭐ PM 1183 §五.1（准办 · 一改一底）：拒答亦须有人话句 —— 形同 decision_none
            #   （原 `answer` ＝ "" ⇒ 前端只读 answer ⇒ 见「空答」· 承「⛔ 失败静默」）。
            return ok({"grounded": False, "refused": True, "answer_source": "context_missing",
                       "answer": "本会话无可读之上句（元问 · 本机无「上一句」可引）⇒ 如实不答（⛔ 不编）", "context_prev": "",
                       "verdict": "上下文缺（本会话无可读上一句 ⇒ 如实不答）", **_bb})
        # ⭐⭐ pm_1500 §二：库根未接 ⇒ **早返**（⛔ 入 `pa_kb_search(q, "")` ⇒ `Path("")` ⇒ 误扫 CWD）。
        #   ⚠ 其态**可分**于「扫了而无」（`kb_state=unset` ＋ 判词）—— 承「空 ≠ 缺」。
        if not kb:
            _j = {"threshold": None, "faces_version": PA_FACES_VERSION, "faces_count": 0,
                  "faces_files_total": 0, "face_snapshot_at": None, "judge_at": _at}
            _bb = {"question": q, "read_at": _at, "kb_root": "", "kb_state": "unset",
                   "searched": 0, "scanned": 0, "scope": list(PA_KB_ASK_SCOPES),
                   "threshold": None, "faces": {},
                   "faces_missing": list(PA_KB_ASK_SCOPES), "faces_skipped": {},
                   "evidence": [], "archive_hits": [], "judge": _j,
                   "refusal_canon": PA_ASK_REFUSAL, "refusal_stale": PA_ASK_REFUSAL_STALE}
            return ok({"grounded": False, "refused": False, "answer": "",
                       "answer_source": "not_applicable", "ask_domain": "retrieve",
                       "verdict": PA_KB_UNSET_VERDICT,
                       "gate": pa_gate_view(decision="not_applicable", fact_family=_fact_family),
                       **_bb})
        # ⭐ 058 §一.3（裁）：复问缓存 —— 同问（同 kb ／ 同 limit）二次 ⇒ 复用首扫之果。
        _limit = int(p.get("limit") or 5)
        # ⭐⭐ pm_1549 §一.2（裁 ⒝ · 印随动）：键含**扫面之印** ——
        #   病（CW `1546 §三` 一手）：旧键 `(q, kb, limit)` ⇒ **面变而果不变** ⇒ 复问复用
        #     「整份扫描之果」（含 `face_snapshot_at` ／ 其「据」）⇒ 屏上之刻旧 ∧ 用户以为新实为旧。
        #   法：面变（增 ／ 删 ／ 改件 ∧ 改库根）⇒ 印变 ⇒ 键变 ⇒ **自失效**（⛔ TTL 之「唯减其时」）。
        _stamp = pa_ask_scan_stamp(kb)
        _ck = (q, str(kb), _limit, _stamp)
        _hit = _ASK_CACHE.get(_ck)
        if _hit is not None:
            res, _cached_wall_s = _hit
            _from_cache = True
            _lru_put(_ASK_CACHE, _ck, _hit, _ASK_CACHE_MAX)   # ⭐ pm_1569 §五：命中提为最新（真 LRU）
        else:
            res = pa_kb_search(q, kb, limit=_limit)
            _cached_wall_s = 0.0
            _from_cache = False
            # ⭐ pm_1569 §五（即刻办 · 治）：满 ⇒ **逐最旧**（⛔ 旧形「满则新键永不入」＝ 复问恒 miss）
            _lru_put(_ASK_CACHE, _ck, (res, round(time.perf_counter() - _tk0, 3)), _ASK_CACHE_MAX)
        _search_wall_s = round(time.perf_counter() - _tk0, 3)
        _faces = res.get("faces", {})
        _arch = res.get("archive_hits", [])
        base = {"question": q, "read_at": _at, "kb_root": str(kb), "searched": res["searched"],
                # ⭐ pm_1569 §四.3／§四.4（**唯加键**）：作据 N ／ 只索引 M 分列 —— 面之半
                #   （今 dsh 308 件）为**只索引**（role: archive）⇒ ⛔ 静默（承「⛔ 不实之辞入屏」）
                "searched_roles": res.get("searched_roles", {}),
                "searched_scans": res.get("searched_scans"),
                "kb_state": "set",
                "from_cache": _from_cache,
                # ⭐ PM 2026-10-05 22:34 §四⒝-1：**canonical 之引用面** —— 前端取此二键
                #   （⛔ 二处各写 ⇒ 免「漂移之床」；「查不到」之旧辞作**词形闸**之旁证）
                "refusal_canon": PA_ASK_REFUSAL, "refusal_stale": PA_ASK_REFUSAL_STALE,
                "scanned": (0 if _from_cache else res["searched"]),
                "search_wall_s": _search_wall_s,
                "saved_wall_s": (round(_cached_wall_s, 3) if _from_cache else 0.0),
                "scope": res["scope"], "threshold": res["threshold"], "faces": _faces,
                "faces_missing": res.get("faces_missing", []),
                "faces_skipped": res.get("faces_skipped", {}), "evidence": res["hits"],
                # ⭐ 档案面之命中（⛔ 作据 · 承 L154）
                "archive_hits": _arch,
                # ⭐ 判据之刻与值（PM 845 §二.1 · 承 L152：参数变更须可回指）
                "judge": {"threshold": res["threshold"],
                          "faces_version": res.get("faces_version"),
                          "faces_count": len(_faces),
                          "faces_files_total": sum(_faces.values()),
                          "face_snapshot_at": res.get("face_snapshot_at"),
                          "judge_at": _at}}
        if res["searched"] == 0:
            return ok({"grounded": False, "refused": False, "answer": PA_KB_EMPTY_ANSWER,
                       "answer_source": "not_applicable", "ask_domain": "retrieve",
                       "answer_canon": PA_KB_EMPTY_ANSWER,
                       "verdict": "不适用（搜索面为空：知识库目录不可达 ⇒ 拒答与否都不成立）",
                       "gate": pa_gate_view(decision="not_applicable", fact_family=_fact_family), **base})
        if not res["hits"]:
            if _arch:
                return ok({"grounded": False, "refused": True, "answer": PA_ASK_REFUSAL,
                           "answer_source": "archive_only", "ask_domain": "retrieve",
                           "gate": pa_gate_view(decision="refused", fact_family=_fact_family),
                           "verdict": "拒答（知识面无据）；档案面另有 %d 条（⛔ 作据 —— 那是我们之报述，⛔ 世界之实）" % len(_arch),
                           **base})
            return ok({"grounded": False, "refused": True, "answer": PA_ASK_REFUSAL,
                       "answer_source": "refused", "ask_domain": "retrieve",
                       "gate": pa_gate_view(decision="refused", fact_family=_fact_family),
                       "verdict": "拒答（库里无依据 ⇒ 按「有据才答」不答）", **base})
        return ok({"grounded": True, "refused": False, "answer": "",
                   "answer_source": "knowledge", "ask_domain": "retrieve",
                   "gate": pa_gate_view(decision="grounded", fact_family=_fact_family),
                   "verdict": "有据（须带出处作答）", **base})

    @bp.route("/v9/pa/threads", methods=["GET"])
    def pa_threads_get():
        from core.pa.threads import ThreadStore, ThreadStoreCorrupt
        from core.pa import threads as _TH

        _uid = request.args.get("user_id")
        ts = ThreadStore(_data_dir())
        try:
            _tstate = ts.load(_uid)
        except ThreadStoreCorrupt as _c:
            # X-17：坏状态**不回落空状态**（前端是 `if(r.ok)` ⇒ 自动跳过，不会炸页面）
            return jsonify({"ok": False, "error": "thread_state_corrupt",
                            "message": str(_c), "path": _c.path}), 409
        _th = _session_binding(_tstate, _uid)
        _th["印"] = _code_sha16(pa_threads_get, _TH)
        return ok(_th)

    @bp.route("/v9/pa/threads", methods=["POST"])
    def pa_threads_post():
        # 批189 · #3（老板要求）：PA 单线程 ⇒ **关闭线程状态写入**（前端不得创建/切换线程）。
        # 历史仍可经 GET 只读查询（ThreadStore.load）。理由：POST 开着 = 前端仍可多线程 ⇒ 单线程不成立。
        print("[PA_SINGLE_THREAD] 拒绝 POST /v9/pa/threads（单线程模式；历史请用 GET）")
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "single_thread_mode",
                    "message": "PA 已切到单线程：线程状态写入已关闭（历史可用 GET /v9/pa/threads 只读查询）",
                }
            ),
            410,
        )

    @bp.route("/v9/pa/ledger", methods=["GET"])
    def pa_ledger():
        r"""账本（只读）。⭐ T2-刀20 §二：逐条标 `用途`（探针 ⇒ **⛔ 业务**）＋ `?usage=` 可滤。

        ⛔ 改盘上之值：唯**读时**标（承「⛔ 删行」）。
        """
        from core.pa.mailer import trail_usage, norm_usage, USAGE_ALIASES
        from core.pa import ledger as _LG
        from core.pa import mailer as _ML

        pa = _core(request.args.get("user_id"))
        _items = [dict(_it) for _it in (pa.ledger.items or [])]
        for _it in _items:
            _it[u'用途'], _it[u'用途之由'] = trail_usage({'件号': _it.get('id'), u'题': _it.get('title'), '果': _it.get('果')}, True)   # ⭐ T2-刀25 §二：读时果判
        _u_raw = request.args.get("usage")
        if _u_raw and str(_u_raw).strip() and norm_usage(_u_raw) is None:
            return jsonify({"ok": False, "error": u"usage 未知：%s" % str(_u_raw)[:40],
                            "allowed": sorted(USAGE_ALIASES),
                            "missing": u"`usage` 之值须在 `allowed` 内"}), 400
        _u = norm_usage(_u_raw)
        _cnt = {u'业务': sum(1 for i in _items if i.get(u'用途') == u'业务'),
                u'探针': sum(1 for i in _items if i.get(u'用途') == u'探针'), u'全量': len(_items)}
        _show = _items
        if _u in (u'探针', u'业务'):
            _show = [i for i in _items if i.get(u'用途') == _u]
        return ok({"items": _show, "open": pa.ledger.open_items(),
                   "count": len(_show), u'用途之数': _cnt,
                   "滤": "usage=" + str(_u_raw or "all") + (u"（归：%s）" % _u if _u else ""),
                   u'用途之判据': u'⭐ 以**果**判（承 T2-刀25 §二）：`果 = ok`（真发 · SMTP 动作）⇒ **业务**（果覆初筛）；否则初筛（`件号` 以 `probe ／ lv-` 起 ∨ 含 `probe ／ 探针`…）⇒ **探针**；否则 **业务**',},
                   印=_code_sha16(pa_ledger, _LG, _ML))

    @bp.route("/v9/pa/cost", methods=["GET"])
    def pa_cost():
        u"""成本读面（PM 085 §三 之令）：**逐轴聚合** —— 轮数 ／ `wall_s` ／ `tokens` ／ `money` ／ 刻窗。

        为什么：成本轴**有写 ⛔ 读** —— 每轮之 `_cost`（`wall_s` ／ `bytes` ／ `tokens` ／ `money`）
        落了盘，而产品**无面可读**（无路由 ⇒ 无聚合 ⇒ 无趋势）⇒「单位产出成本可算」（`PA-8`
        成本地板）之判据 ⛔ 达。补此面 ＝ 基线之前提（⛔ 无基线之优化 ＝ 凭感觉）。

        ⭐ 三条口径（承 PM 085 §三 · 承 070 §一：**`3 ≠ 2`**）：
          ⒈ **唯读 ＋ 唯聚合**：⛔ 改既有成本轴之语义（承 057 §一「唯加键」）；
          ⒉ **无数据 ≠ 成本为零**：无行 ⇒ `has_data=false` ∧ 各值 `null`（⛔ 以 `0` 充「已计」）；
          ⒊ **未记之字段须点名**：`bytes.in/out`（账上未落 · 唯见响应 `cost`）／`phase`（唯嵌 `summary`）
             明报；**无 `axis` 之旧行**（`2026-09-17` 之 canary 等）**单列** ⇒ ⛔ 并入两轴。

        面 ＝ `<data_dir>/v8/billing_default.jsonl`（账本之库）｜滤 ＝ `axis`｜式 ＝ 逐轴累积 ＋ 直方
        ⇒ 数 ＋ `凭`（面 ／ 滤 ／ 式 ／ 数 ／ **器** ／ 印 · 承 1018 §四「报数须附印」· 承 PM 089 §二「印须载器」）。
        """
        import hashlib
        import json as _json
        from datetime import datetime as _dt, timedelta as _td

        try:
            _days = int(request.args.get("days") or 0)
        except Exception:
            _days = 0
        # ⭐ 面之径**取自写者**（`ledger._billing_file` ⇒ 读写**同源** ⇒ ⛔ 径漂）：
        #   ⛔ 按 CWD 硬编径、⛔ 按 `_data_dir()` 拼（那是 PA 用户面之径 · 非账本之径）。
        _path_err = ""
        try:
            from core.lib.v8.ledger import ledger as _led
            _path = str(_led._billing_file("default"))
        except Exception as _e_p:
            _path, _path_err = "", str(_e_p)[:200]
        # `abspath` ⇒ 把写者之相对径解成**绝对径**（起服三步 ＝ `CWD=ROOT`）⇒ ⛔ 读者猜径。
        _path = os.path.abspath(_path or os.path.join(str(_data_dir()), "v8", "billing_default.jsonl"))
        _since = (_dt.now() - _td(days=_days)).isoformat() if _days > 0 else None

        _act, _money, _legacy, _bad = [], [], 0, 0
        _read_err = ""
        _raw = None
        try:
            with open(_path, "rb") as _f:
                _raw = _f.read().decode("utf-8", "replace")
        except OSError as _e:
            _read_err = str(_e)[:200]
        for _line in (_raw or "").splitlines():
            if not _line.strip():
                continue
            try:
                _r = _json.loads(_line)
            except Exception:
                _bad += 1
                continue
            if not isinstance(_r, dict):
                _bad += 1
                continue
            if _since is not None and str(_r.get("timestamp") or "") < _since:
                continue
            if _r.get("axis") == "activity":
                _act.append(_r)
            elif _r.get("axis") == "money":
                _money.append(_r)
            else:
                _legacy += 1          # ⛔ 并入两轴：`058` 前之旧行**无** `axis`
        _n = len(_act)

        def _f(_r, _k):
            _v = _r.get(_k)
            return float(_v) if isinstance(_v, (int, float)) else None

        _wall = [x for x in (_f(_r, "wall_s") for _r in _act) if x is not None]
        _tk = [x for x in (_f(_r, "tokens") for _r in _act) if x is not None]
        _m_act = [(_f(_r, "cost") or 0.0) for _r in _act]
        _far = [x for x in _m_act if x > 0.0]
        _by_src = {}
        for _r in _act:
            _g = _by_src.setdefault(str(_r.get("source") or u"未记"),
                                    {u"轮": 0, u"wall_s": 0.0, u"tokens": 0, u"tokens无值轮": 0})
            _g[u"轮"] += 1
            _g[u"wall_s"] = round(_g[u"wall_s"] + (_f(_r, "wall_s") or 0.0), 3)
            _t = _f(_r, "tokens")
            if _t is None:
                _g[u"tokens无值轮"] += 1
            else:
                _g[u"tokens"] += int(_t)
        _ts = sorted(str(_r.get("timestamp") or "") for _r in _act if _r.get("timestamp"))
        def _n2(_r, _k):                       # ⭐ PM 088 §三：`bytes` 入账后，本面须**可读**（⛔ 只写不读）
            _v = _r.get("bytes")
            _v = (_v.get(_k) if isinstance(_v, dict) else None)
            return _v if isinstance(_v, (int, float)) else None
        _bin = [x for x in (_n2(_r, "in") for _r in _act) if x is not None]
        _bout = [x for x in (_n2(_r, "out") for _r in _act) if x is not None]
        _nokey = sum(1 for _r in _act if not isinstance(_r.get("bytes"), dict))
        # ⭐ 未记须**随本账实况**（⛔ 硬编：加 `bytes` 参后仍报「未记」＝ 假报 · 承 088 §三）
        _na = []
        if not _n:
            _na.append({u"字段": u"bytes.in / bytes.out",
                        u"由": u"本面无 activity 行 ⇒ **无数据**（⛔ 非「零」· 承 085 §三）"})
        elif _nokey:
            _na.append({u"字段": u"bytes.in / bytes.out",
                        u"由": u"本账 activity 行中 **%d／%d 行无** `bytes` 键（`record_activity` 加 `bytes` 参**前**所落）"
                              u"⇒ 本面 ⛔ 回读（承「无数据 ≠ 零」· ⛔ 以 0 充已计）" % (_nokey, _n)})
        _na.append({u"字段": u"phase",
                    u"由": u"活动轴行**无** `phase` 键 ⇒ 唯嵌在 `summary` 文本内（`phase=…`）"})
        _payload = {
            u"has_data": bool(_n > 0),
            u"轮数": _n,
            u"刻窗": {u"入参days": _days, u"since": _since,
                     u"首轮刻": (_ts[0] if _ts else None), u"末轮刻": (_ts[-1] if _ts else None)},
            u"wall_s": (None if not _n else {
                u"合计": round(sum(_wall), 3),
                u"均值": (round(sum(_wall) / len(_wall), 3) if _wall else None),
                u"最大": (round(max(_wall), 3) if _wall else None),
                u"有值轮": len(_wall), u"无值轮": _n - len(_wall)}),
            u"tokens": (None if not _n else {
                u"合计": (int(sum(_tk)) if _tk else None),
                u"有值轮": len(_tk), u"无值轮": _n - len(_tk)}),
            u"money": (None if not _n else {
                u"币": u"CNY", u"合计": round(sum(_m_act), 8),
                u"本地轮": _n - len(_far), u"本地合计": 0.0,
                u"远端轮": len(_far), u"远端合计": round(sum(_far), 8)}),
            u"分组": ({u"source": _by_src} if _n else None),
            u"bytes": (None if not _n else {
                u"入合计": (int(sum(_bin)) if _bin else None),
                u"出合计": (int(sum(_bout)) if _bout else None),
                u"有值轮": len(_bin), u"无值轮": _n - len(_bin),
                u"无键行": _nokey}),
            u"未记": _na,
            u"账本": {u"面": _path, u"滤": u"axis（activity ／ money ／ 无）", u"式": u"逐轴累积 ＋ source 直方",
                     u"行数": {u"activity": _n, u"money": len(_money),
                              u"无axis之旧行": _legacy, u"坏行": _bad},
                     u"读错": (_read_err or None), u"取径之错": (_path_err or None)},
        }
        # ⭐ PM 089 §二（令）：**印须载器** —— `器` ＝ **本路由之码之 `sha16`** ⇒ 印 ⊂ 器 ＋ 面 ＋ 滤 ＋ 式 ＋ 数。
        #   ⛔ 载器之病之实证（PM `089 §二`）：码改（加 `bytes` 轴）而 `数` 未变 ⇒ 旧式两版**同印**。
        # ⭐ T2-刀26 §二（PM 裁 17:57 · 下批）：**印须载器之真源** —— 本面之**径**出 `core/lib/v8/ledger.py` ⇒ 器 ＝ sha16(路由源 ＋ ledger 模块源)
        import core.lib.v8.ledger as _ledmod
        _c16 = _code_sha16(pa_cost, _ledmod)
        _payload[u"凭"] = {
            u"面": _path, u"滤": u"axis=activity", u"式": u"逐轴累积＋直方", u"数": _n,
            u"器": _c16,
            u"印": (None if _c16 is None else hashlib.sha256(
                (u"%s|%s|%s|%d|%s" % (_path, u"axis=activity", u"逐轴累积＋直方", _n, _c16)).encode("utf-8")
            ).hexdigest()[:16]),
            u"印之由": u"本路由**自印**（⛔ ＝ 计数_公器 之印）：印 ⊂ **器**（＝本路由之码之 sha16）＋ 面 ＋ 滤 ＋ 式 ＋ 数"
                       u" ⇒ 器不同则印不同（承 1018 §一 · PM 089 §二）"
                       u"｜⚠ **器 ⛔ 得 ⇒ 印 `null`**（照实「未核」· ⛔ 以缺器之印冒充载器之印）",
        }
        return ok(_payload)

    @bp.route("/v9/pa/ledger/add", methods=["POST"])
    def pa_ledger_add():
        pa = _core((request.json or {}).get("user_id"))
        p = request.json or {}
        if not p.get("title"):
            return err("ledger/add 需要 title")
        r = pa.handle(
            "todo_add",
            {"title": p["title"], "kind": p.get("kind", "todo"), "note": p.get("note", ""), "due": p.get("due")},
        )
        return ok(r) if r.get("ok") else err(r.get("error"))

    @bp.route("/v9/pa/ledger/done", methods=["POST"])
    def pa_ledger_done():
        pa = _core((request.json or {}).get("user_id"))
        p = request.json or {}
        if not p.get("id"):
            return err("ledger/done 需要 id")
        r = pa.handle("todo_done", {"id": p["id"]})
        return ok(r) if r.get("ok") else err(r.get("error"))

    # ⭐⭐ pm_1824 §二.2（令）：**逐条撤回**（一件一撤回 ＋ 留痕）—— 产品态 §五.1
    #   「凡积累必可查、可导出、可撤回」；今唯 add ／ done ⇒ **缺撤回**（一手：全路由 .gitignore 外无 revoke）。
    #   ⚠ 撤 ＝ **标 cancelled**（⛔ 删行 —— 承账本之「⛔ 删行」律；行仍在盘 ⇒ 可查）。
    @bp.route("/v9/pa/ledger/revoke", methods=["POST"])
    def pa_ledger_revoke():
        """逐条撤回一件待办（`{id, reason?, user_id?}`）：落 cancelled ＋ 刻 ／ 因，并记事件留痕。"""
        pa = _core((request.json or {}).get("user_id"))
        p = request.json or {}
        if not p.get("id"):
            return err("ledger/revoke 需要 id")
        r = pa.handle("todo_revoke", {"id": p["id"], "reason": p.get("reason", "")})
        if not r.get("ok"):
            return err(r.get("error"))
        if r.get("item") is None:
            # 查不到 ⇒ **404 载因**（⛔ 返 ok:true 假装已撤 —— 承「空 ⛔ 混 缺」）
            return err("ledger/revoke 查不到该件：%s（⛔ 未撤）" % p["id"], 404)
        return ok(r)

    @bp.route("/v9/pa/dispatch", methods=["POST"])
    def pa_dispatch():
        pa = _core((request.json or {}).get("user_id"))
        p = request.json or {}
        task = (p.get("task_text") or "").strip()
        if not task:
            return err("dispatch 需要 task_text")
        # ⭐ T2-刀1 ①②⑤（2026-10-05）：席轴 —— 收 shortId（亦认 name）⇒ 落 shortId；
        #   须能在席位册（`GET /v9/pa/roster?kind=seat`）查到；查不到 ⇒ **报错拒派**（⛔ 静默兜底）。
        to_seat_raw = str(p.get("to_seat") or "").strip()
        to_seat = ""
        if to_seat_raw:
            from core.pa.dispatch import resolve_seat

            to_seat = resolve_seat(to_seat_raw)
            if not to_seat:
                return err("to_seat 查不到该席：%s（席位册 ＝ GET /v9/pa/roster?kind=seat；"
                           "形 ＝ shortId（7 位 · 如 5c01a0f）· ⛔ UUID 前 8 位；⛔ 静默兜底）"
                           % to_seat_raw, 400)
        action = "dispatch_v9" if p.get("via_gateway") else "dispatch"
        r = pa.handle(action, {"task_text": task, "url": p.get("url"), "to_seat": to_seat})
        if r.get("ok") and to_seat:
            r["to_seat"] = to_seat
        return ok(r) if r.get("ok") else err(r.get("error"))

    # ---- 版本与更新源之面（pm_1628 §二.2 令二 ＋ §二.3 令三）：只读 · 一处定形 ----
    #   真源：`core/lib/build_info.py`（装根 `version.json`）＋ `core/lib/update_source.py`
    #   （`update_source.yaml` · env 可覆）。⛔ 密钥 · ⛔ 用户数据；未见 ⇒ 照实报（⛔ 充）。
    @bp.route("/v9/pa/version", methods=["GET"])
    def pa_version():
        u"""本机之版本元数据 ＋ 更新源之声明（只读 · 唯此一处出）。"""
        from core.lib import build_info as _bi
        from core.lib import update_source as _us
        _s = _us.load()
        return ok({"build": _bi.report(),
                   "source": {"url": _s["url"], "channel": _s["channel"],
                              "provider": _s["provider"], "origin": _s["origin"],
                              "file": _s["file"], "note": _s["note"]},
                   "manifest_url": _us.manifest_url(_s)},
                  印=_code_sha16(pa_version, _bi, _us))

    # ---- 模型供应商面（PM 034 P0）：只读 · 密钥唯布尔 · ⛔ 值 ----
    @bp.route("/v9/pa/providers", methods=["GET"])
    def pa_providers():
        """模型供应商注册表（只读）。"""
        from core.pa.providers import public_view
        from core.pa import providers as _PV

        return ok(public_view(), 印=_code_sha16(pa_providers, _PV))

    # ---- 供应商密钥之「写」口（pm_1613 令四 · 后端半）：唯本机 ＋ 一次性令牌 · ⛔ 值 ----
    @bp.route("/v9/pa/providers/key/token", methods=["GET"])
    def pa_provider_key_token():
        """一次性令牌之领（唯本机 · ⛔ 值上屏 —— 唯 Cookie · HttpOnly · SameSite=Strict）。"""
        from core.pa import provider_keys as _PK

        if not _loopback(request):
            return err("此端唯本机可领（来源 %s）" % (request.remote_addr or "?"), 403)
        tok, ttl = _PK.issue_token()
        r = ok({"issued": True, "expires_in": ttl, "cookie": _PK.TOKEN_COOKIE,
                "用": "唯同源 POST /v9/pa/providers/key（Cookie 自带 · 用即焚）"},
               印=_code_sha16(pa_provider_key_token, _PK))
        r.set_cookie(_PK.TOKEN_COOKIE, tok, max_age=int(ttl), path=_PK.TOKEN_PATH,
                     httponly=True, samesite="Strict")
        return r

    @bp.route("/v9/pa/providers/key", methods=["POST"])
    def pa_provider_key():
        """供应商密钥之 落 / 清（承 pm_1613 令四）。唯本机 ＋ 一次性令牌；⛔ 回值（唯布尔 ＋ 面）。"""
        from core.pa import provider_keys as _PK
        from core.pa.providers import PROVIDERS, key_state

        if not _loopback(request):
            return err("此端唯本机可用（来源 %s）" % (request.remote_addr or "?"), 403)
        body = request.get_json(silent=True) or {}
        pid = str(body.get("provider") or "").strip()
        p = PROVIDERS.get(pid)
        if not p:
            return err("无此供应商：%s（见 GET /v9/pa/providers）" % (pid or "—"), 400)
        env_name = p.get("key_env")
        if not env_name:
            return err("此供应商 ⛔ 需密钥（key_env 缺 —— 如本机 Ollama）", 400)
        okc, why = _PK.consume_token(request.cookies.get(_PK.TOKEN_COOKIE))
        if not okc:
            return err("鉴权⛔：%s" % why, 403)
        raw = body.get("key")
        if raw is None or not str(raw).strip():
            okc, face = _PK.clear_key(env_name)
            act = "cleared"
        else:
            okc, face = _PK.set_key(env_name, raw)
            act = "set"
        if not okc:
            return err("密钥⛔ 落：%s" % face, 400)
        _st = key_state(pid)
        r = ok({"provider": pid, "key_env": env_name, "action": act,
                "key_state": _st, "key_configured": (_st == "configured"), "落": face},
               印=_code_sha16(pa_provider_key, _PK))
        r.delete_cookie(_PK.TOKEN_COOKIE, path=_PK.TOKEN_PATH)
        return r

    # ---- P2 ①（pm_1449 §二.1）：会话级模型之仓 —— 读（GET）／ 落 · 清（POST） ----
    @bp.route("/v9/pa/session_model", methods=["GET", "POST"])
    def pa_session_model():
        u"""会话级模型之仓（P2 ①）。

        ⛔ 前端硬编：本路由 ⇒ 前端取「当前模型」之单源；合法面 ＝ 注册表（`known_models`）。
        POST {user_id, model}：`model` 有值 ⇒ 白名单验 ＋ 落档；`model` 空 ／ null ⇒ **清**（回落默认）。
        """
        from core.pa import providers as _PV

        if request.method == "GET":
            _m, _src = session_model_of(_uid_safe(request.args.get("user_id")))
            return ok({"model": _m or "", "model_source": _src,
                       "default": _PV.default_view(),
                       "known_models": list(_PV.known_models()),
                       "model_aliases": _PV.model_aliases()},
                      印=_code_sha16(pa_session_model, _PV))
        body = request.get_json(silent=True) or {}
        _uid = _uid_safe(body.get("user_id"))
        _raw = body.get("model")
        if _raw is None or not str(_raw).strip():
            _okc, _src = session_model_clear(_uid)
            if not _okc:
                return err(_src, 409)
            return ok({"model": "", "model_source": _src, "cleared": True},
                      印=_code_sha16(pa_session_model, _PV))
        _m, _src = session_model_of(_uid, _raw)
        if not _m:
            return err(_src, 400)
        return ok({"model": _m, "model_source": _src, "cleared": False},
                  印=_code_sha16(pa_session_model, _PV))

    # ---- 执行层 agent 扫描（PM 035/036 Q0 · 037 §B.2）：果灌**既有** roster.upsert ----
    @bp.route("/v9/pa/roster/scan", methods=["POST"])
    def pa_roster_scan():
        from core.pa import agent_scan as S

        r = S.scan_and_upsert()
        return ok({"upsert": r["upsert"], "modes": r.get("upsert_modes", {}),
                   "scan_at": r["scan_at"], "scan_version": r["scan_version"]})

    # ---- 编队花名册: PA 派活前先查"谁能干、怎么调、边界在哪" ----
    # ---- ⭐ T2-刀8 §一（2026-10-05 · PM 令）：**组织席位**之**独立真源面** ----
    # 由：`/v9/pa/roster` 之 `14` ＝ **能力端点**册；`env.agents` 之 `kind=seat` ＝ **组织席位**。
    #     两者皆 `14` ⇒ 面上一词盖两义（承「面名分列 · ⛔ 抹平」）⇒ 立独立面 ＋ 各标面名。
    @bp.route("/v9/pa/seats", methods=["GET"])
    def pa_seats():
        """**组织席位册**（真源 ＝ `paseo agent ls --json` ⇒ `seat_roster.json` · ⛔ roster.json）。

        与 `GET /v9/pa/roster`（**能力端点册**）**两名分列** —— ⛔ 互为别名、⛔ 抹平。
        """
        from core.pa import roster as R

        d = R.summary(kind="seat")
        d["印"] = _code_sha16(pa_seats, R)
        return ok(d)

    @bp.route("/v9/pa/roster", methods=["GET"])
    def pa_roster():
        from core.pa import roster as R
        from core.pa import agent_invoke as _AI

        kind = (request.args.get("kind") or "").strip()
        if kind:  # ⭐ T2-刀2.3：`kind=seat` ⇒ 唯**席位册**；T2-刀8 §〇：**真筛**（⛔ 假筛）
            d = R.summary(kind=kind)
            d["印"] = _code_sha16(pa_roster, R, _AI)
            return ok(d)
        # ⭐ T2-刀7-正（2026-10-05）：补**二键** `invoke` ＋ `probe`（⛔ 改既存七键 · ⛔ 更名）
        if request.args.get("full"):
            return ok({"cards": _AI.attach_cards(R.load().get("cards", [])),
                       "面名": "能力端点册（逐卡全字段）",
                       "别于": "GET /v9/pa/seats（组织席位册）",
                       "印": _code_sha16(pa_roster, R, _AI)})
        d = _AI.attach(R.summary())
        d["面名"] = "能力端点册"
        d["别于"] = "GET /v9/pa/seats（组织席位册 · 真源 `paseo agent ls --json`）"
        d["印"] = _code_sha16(pa_roster, R, _AI)
        return ok(d)

    @bp.route("/v9/pa/roster/find", methods=["GET"])
    def pa_roster_find():
        """按能力找人 —— 派活第一步。"""
        from core.pa import roster as R

        # ⭐ T2-刀2.3：`cap` 亦收**四种权**（写码 ／ 起停 ／ 部署 ／ 裁决复核）
        cap = (request.args.get("cap") or request.args.get("right") or "").strip()
        rights = tuple(getattr(R, "GOVERNANCE_RIGHTS", ()))
        cands = R.by_governance(cap) if cap in rights else R.by_capability(cap)
        return ok({"cap": cap, "candidates": cands, "rights": list(rights)})

    @bp.route("/v9/pa/roster/<agent_id>", methods=["GET"])
    def pa_roster_card(agent_id):
        from core.pa import roster as R

        c = R.get(agent_id)
        if c:
            try:  # ⭐ T2-刀7-正：单卡面补 `invoke` ＋ `probe`（⛔ 改既有键）
                from core.pa import agent_invoke as _AI
                _AI.attach_cards([c])
            except Exception:
                pass
        return ok({"card": c}) if c else err("无此卡片: %s" % agent_id, 404)

    @bp.route("/v9/pa/roster/upsert", methods=["POST"])
    def pa_roster_upsert():
        """新增/更新卡片: 把新获得的能力认识固化下来(迭代的落点)。"""
        from core.pa import roster as R

        p = request.json or {}
        card = p.get("card") or p
        r = R.upsert(card)
        if r.get("ok"):
            try:
                _core(p.get("user_id")).events.append(
                    "fact", "roster_upsert", {"id": card.get("id"), "keys": sorted(card.keys())}, source="pa/roster"
                )
            except Exception:
                pass
            return ok(r)
        return err(r.get("error"))

    # ---- 环境感知面（T2-刀2′／刀2″ · 2026-10-05）：只读四栏 ＋ 只读侦察 ＋ 工作笔记 ----
    def _pa_route_count():
        """本网关自身路由之**读数**（唯数 · ⛔ 硬编）。"""
        try:
            return len([r for r in app.url_map.iter_rules()
                        if str(r.endpoint).startswith("pa_routes.")])
        except Exception:
            return None

    @bp.route("/v9/pa/env", methods=["GET"])
    def pa_env():
        """PA 之「工位清单」（**只读**四栏）。⛔ 写任何一侧（承 kb_mapping N1–N6）。"""
        from core.pa import env_face as E

        out = E.build_env(route_count=_pa_route_count())
        try:
            out["scheduler"] = E.ensure_scheduler()
        except Exception as _se:
            out["scheduler"] = {"enabled": False, "error": type(_se).__name__}
        out["印"] = _code_sha16(pa_env, E)
        return ok(out)

    @bp.route("/v9/pa/env/note", methods=["GET"])
    def pa_env_note():
        """PA 自己的**工作笔记**（只读 · 侦察之产物 ＋ 实测刻）。"""
        from core.pa import env_face as E

        try:
            _n = int(request.args.get("n") or 20)
        except Exception:
            _n = 20
        _d = E.notes_face(limit=_n, full=bool(request.args.get("full")))
        _d["印"] = _code_sha16(pa_env_note, E)
        return ok(_d)

    @bp.route("/v9/pa/env/research", methods=["POST"])
    def pa_env_research():
        """触发一次**只读**侦察（⛔ 无写副作用 · ⛔ 唯只读工具）；**前后对表**自证。"""
        from core.pa import env_face as E

        r = E.research(route_count=_pa_route_count())
        try:
            r["scheduler"] = E.ensure_scheduler()
        except Exception as _se:
            r["scheduler"] = {"enabled": False, "error": type(_se).__name__}
        return ok(r)

    # ---- 断点续面（T2-刀6 · 2026-10-05）：只读 · 离线攒件／续办／水印／失败件 ----
    @bp.route("/v9/pa/resume", methods=["GET"])
    def pa_resume():
        r"""PA 断点续面（**只读**）：末次开机之攒件／续办／幂等跳过／失败件 ＋ 水印 ＋ 两读对表。

        ⭐ 断点续之跑器 ＝ `scripts\win_pa\boot_resume.py`（开机所调）；本面唯**读**同一真源
        （⛔ 两套读者）⇒ 面之数 ＝ 台账末行 ＋ 水印（⛔ 自报）。
        """
        from core.pa import resume_face as RF

        out = RF.build_resume(route_code_sha16=_code_sha16(pa_resume, RF))
        return ok(out)

    # ---- 统一调用面（T2-刀7 ／ 刀7-正 · 2026-10-05）：能派 · 能盯 · 能收 · 能记 ----
    @bp.route("/v9/pa/agent/invoke", methods=["POST"])
    def pa_agent_invoke():
        r"""统一调用面（**册 ／ 席 ／ CLI ／ 云端 API**）：`{agent_id, task, mode, timeout_s}`
        ⇒ `{ok, agent_id, via, ms, out, 印}`（`印` **载器** ＝ 本路由之码之 `sha16`）。

        ⭐ `agent_id` 空 ⇒ 回**册**（可枚举 · ⛔ 未在册者**拒调**）。
        三类执行器（⛔ 另造运输）：`seat`（`paseo agent send` · **复用** `dispatch.SeatExecutor`）／
        `cli`（起进程 ＋ 超时必带 ＋ ⛔ 交互式）／`api`（云端 · 密钥**唯从 `config.json` 读** · **唯布尔**）。
        ⚠ RTX 2060 · 6 GB ⇒ 本地并发**排队**（`PA_INVOKE_LOCAL_CONCURRENCY`）＋ 记时长。
        """
        from core.pa import agent_invoke as _AI

        p = request.get_json(silent=True) or {}
        r = _AI.invoke(p.get("agent_id"), p.get("task") or p.get("prompt") or "",
                       mode=p.get("mode") or "auto", timeout_s=p.get("timeout_s"))
        r["印"] = _code_sha16(pa_agent_invoke, _AI)   # ⭐ 印须载器（承 PM 089 §二 ／ 1018 §一）
        try:
            _core(p.get("user_id")).events.append(
                "fact", "agent_invoke",
                {"agent_id": r.get("agent_id"), "via": r.get("via"), "ok": r.get("ok"),
                 "印": r.get("印")}, source="pa/agent_invoke")
        except Exception:
            pass
        return ok(r)

    @bp.route("/v9/pa/roster/probe", methods=["POST"])
    def pa_roster_probe():
        """`probe` 之**实测刷新**（⛔ 唯此处触实测 ⇒ 落 `card_probes.json`；面只读缓存）。"""
        from core.pa import agent_invoke as _AI

        p = request.get_json(silent=True) or {}
        doc = _AI.refresh_probes(with_api=bool(p.get("with_api") or request.args.get("with_api")))
        doc["印"] = _code_sha16(pa_roster_probe, _AI)
        return ok(doc)

    # ---- 收口之道（T2-刀4 · 2026-10-05）：回执面 ／ 四段之盯 ／ 催收 ／ 产品线 ----
    @bp.route("/v9/pa/dispatch/receipt", methods=["POST"])
    def pa_dispatch_receipt():
        r"""收口回执（**拒未在册之 `task_id`** · 四段**只进不退** · ⛔ 静默兜底）。

        `{task_id, to_seat, 果, 印, stage, note}` ⇒ `{ok, task_id, stage, 回执四件}`。
        四段 ＝ 已派 ⇒ 已收 ⇒ 在做 ⇒ 已收口（每段有刻）。
        """
        from core.pa import receipts as _RC

        p = request.get_json(silent=True) or {}
        r = _RC.record(p.get("task_id"), p.get("to_seat") or "",
                       p.get("果") or p.get("result") or "", p.get("印") or p.get("stamp") or "",
                       stage=p.get("stage") or "已收", note=p.get("note") or "",
                       by=p.get("by") or p.get("from") or "")
        try:
            _core(p.get("user_id")).events.append(
                "fact", "dispatch_receipt",
                {"task_id": r.get("task_id"), "stage": r.get("stage"), "ok": r.get("ok"),
                 "印": r.get("印")}, source="pa/dispatch/receipt")
        except Exception:
            pass
        return ok(r) if r.get("ok") else err(r.get("error"), 400)

    @bp.route("/v9/pa/dispatch/receipt", methods=["GET"])
    def pa_dispatch_receipt_get():
        """回执只读面：`?task_id=` ⇒ 该件之四段 ＋ 逐段之刻 ＋ 催之数；不给 ⇒ 全表之态。"""
        from core.pa import receipts as _RC

        q = (request.args.get("task_id") or "").strip()
        try:
            lim = int(request.args.get("n") or 50)
        except Exception:
            lim = 50
        d = _RC.face(task_id=q or None, limit=lim)
        d["印"] = _code_sha16(pa_dispatch_receipt_get, _RC)
        return ok(d)

    @bp.route("/v9/pa/dispatch/chase", methods=["POST"])
    def pa_dispatch_chase():
        """催收一轮：`stage != 已收口` ∧ 距末次刻 > 阈 ⇒ 催**一次**（**限次** · 同路运输）。"""
        from core.pa import receipts as _RC

        p = request.get_json(silent=True) or {}
        r = _RC.chase(threshold_min=p.get("threshold_min"), max_n=p.get("max_n"),
                      dry=bool(p.get("dry")))
        r["印"] = _code_sha16(pa_dispatch_chase, _RC)
        return ok(r)

    @bp.route("/v9/pa/lines", methods=["GET"])
    def pa_lines():
        """**产品线**面（`product_line = {线名, 席, 件集[], 状态, 下一拍}`）。"""
        from core.pa import lines as _L

        d = _L.face()
        # ⭐ T2-刀26 §二（PM 裁 17:55）：**印须载器之真源** —— 本面之数出 `core/pa/lines.py` ⇒ 印 ＝ sha16(路由源 ＋ lines.py 全源)
        d["印"] = _code_sha16(pa_lines, _L)
        return ok(d)

    @bp.route("/v9/pa/lines/upsert", methods=["POST"])
    def pa_lines_upsert():
        """补一条线之**人手认识**（线名／下一拍／备注）；⛔ 覆派生之件集与状态。"""
        from core.pa import lines as _L

        p = request.get_json(silent=True) or {}
        r = _L.upsert(p.get("line") or p)
        return ok(r) if r.get("ok") else err(r.get("error"), 400)

    @bp.route("/v9/pa/proxy", methods=["POST"])
    def pa_proxy():
        """PA 调用本地灵犀服务(3890)的【唯一入口】—— 强制经过端点分级门。

        为什么必须走这里: 2026-09-10 我用脚本对每个候选路径盲发 POST {},
        其中 POST /kv/clear 无参数即清空全部 → 插件配置库 8 条全灭。
        现在起 PA 不允许直连 3890; 一切经本路由, 由 endpoint_guard 分级:
          只读 -> 放行 / 写 -> 放行并记账 / 破坏性 -> 需在场授权 / 未登记非 GET -> 默认拒绝
        """
        import json as _json

        from core.pa import endpoint_guard as G

        try:
            p = request.json
        except Exception as _e_body:
            return err("proxy: body 不是合法 JSON（%s）" % type(_e_body).__name__)
        if p is None:
            p = {}
        if not isinstance(p, dict):
            return err("proxy: body 需要 JSON 对象（拿到 %s）" % type(p).__name__)
        method = (p.get("method") or "GET").upper()
        path = (p.get("path") or "").strip()
        body = p.get("body")
        user_id = p.get("user_id") or ""
        if not path:
            return err("proxy 需要 path")

        # /mcp/call 按 body.name(工具名) 分级, 其余端点按路径分级(见 endpoint_guard)
        _mcp_tool = (body or {}).get("name") if isinstance(body, dict) else None
        allowed, level, reason = G.check(method, path, user_id, body)
        # 记账(含被拒): 谁在什么时候想动什么, 必须可追溯
        try:
            pa = _core(user_id)
            _ev = {"method": method, "path": path, "level": level, "allowed": bool(allowed), "reason": reason}
            if _mcp_tool:
                _ev["mcp_tool"] = _mcp_tool
            pa.events.append("fact", "proxy_call", _ev, source="pa/proxy")
        except Exception:
            pass
        if not allowed:
            return jsonify({"ok": False, "error": reason, "blocked_by": "endpoint_guard", "level": level}), 403

        base = os.getenv("LINGXI_PROXY_BASE", "http://127.0.0.1:3890")
        url = base.rstrip("/") + path
        try:
            import urllib.request

            headers = {"Content-Type": "application/json"}
            # token 从插件 KV 现取(read 级), 避免硬编码
            try:
                _kv = urllib.request.urlopen(base.rstrip("/") + "/kv/all", timeout=5)
                _tok = (_json.loads(_kv.read().decode("utf-8")) or {}).get("items", {}).get("wpsAiMcpBridgeToken")
                if _tok:
                    headers["Authorization"] = "Bearer " + str(_tok)
            except Exception:
                pass
            data = None
            if method in ("POST", "PUT", "PATCH"):
                data = _json.dumps(body if body is not None else {}).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=float(p.get("timeout", 20))) as resp:
                raw = resp.read().decode("utf-8", "replace")
                try:
                    parsed = _json.loads(raw)
                except Exception:
                    parsed = {"raw": raw[:2000]}
                return ok({"level": level, "status": resp.status, "data": parsed})
        except urllib.error.HTTPError as e:
            try:
                _b = _json.loads(e.read().decode("utf-8", "replace"))
            except Exception:
                _b = {"raw": ""}
            # N2b：⛔ 不用 str(<例外>) —— 只回上游 HTTP 状态行（e.code ／ e.reason），无内部对象 ／ 类名
            return jsonify({"ok": False, "level": level, "status": e.code,
                            "error": "上游返回 %s %s" % (e.code, e.reason), "data": _b}), e.code
        except Exception as e:
            # N2b：⛔ 异常原文不回客户端（详情只落服务端日志）
            logger.error("proxy 调用失败: %s", type(e).__name__)
            return err("proxy 调用失败（内部错误，已记日志）")

    @bp.route("/v9/pa/proxy/gate", methods=["GET"])
    def pa_proxy_gate():
        from core.pa import endpoint_guard as G

        _d = G.gate_state(request.args.get("user_id") or "")
        _d["印"] = _code_sha16(pa_proxy_gate, G)
        return ok(_d)

    @bp.route("/v9/pa/proxy/approve", methods=["POST"])
    def pa_proxy_approve():
        """老板在场授权破坏性端点(会话级, 默认 30 分钟)。"""
        from core.pa import endpoint_guard as G

        p = request.json or {}
        if p.get("revoke"):
            return ok(G.revoke(p.get("user_id") or ""))
        r = G.approve_destructive(
            p.get("user_id") or "", p.get("path"), float(p.get("ttl_s") or 1800), p.get("note") or ""
        )
        try:
            _core(p.get("user_id")).events.append("fact", "proxy_approve", {"paths": r.get("paths")}, source="pa/proxy")
        except Exception:
            pass
        return ok(r)

    # ---- 验收器官: 审核(preflight + 内容合规 + postcheck) ----
    # ---- 口径卡: 政策数字定状态 + 与内容合规联动 ----
    @bp.route("/v9/pa/caliber", methods=["GET"])
    def pa_caliber():
        from core.pa import caliber as C

        return ok({"cards": C.summary(), "counts": C.counts(), "source": C.source()}, 印=_code_sha16(pa_caliber, C))

    @bp.route("/v9/pa/caliber/change", methods=["POST"])
    def pa_caliber_change():
        """口径变更单（P7 · 2026-09-29）：把「改口径」从**改源码**变成**记一条**。
        必填 id/status/owner/why（缺一即拒，⛔ 不默认）；append-only 落
        data/v9/pa/caliber_changes.jsonl，**含改前值**；store 损坏 ⇒ 409（⛔ 不静默）。
        """
        from core.pa.caliber_store import CaliberStore, CaliberStoreCorrupt, CaliberStoreError

        try:
            p = request.json
        except Exception as _e_body:
            return err("caliber/change: body 不是合法 JSON（%s）" % type(_e_body).__name__)
        if not isinstance(p, dict):
            return err("caliber/change: body 需要 JSON 对象（拿到 %s）" % type(p).__name__)
        try:
            r = CaliberStore(_data_dir()).apply_change(p)
        except CaliberStoreError as _e:
            # PM 2026-09-30 裁「改」：域因原樣回，但**必帶路由定位**（與 caliber/check 同族）
            return err("caliber/change: %s" % _e)
        except CaliberStoreCorrupt as _c:
            return jsonify({"ok": False, "error": "caliber_store_corrupt",
                            "message": str(_c), "path": _c.path}), 409
        except Exception as _e:
            logger.error("caliber/change 内部错误: %s: %s", type(_e).__name__, str(_e)[:200])
            return jsonify({"ok": False, "error": "caliber/change: 内部错误（已记日志）"}), 500
        try:
            _core(p.get("user_id")).events.append(
                "fact", "caliber_change", r.get("change") or {}, source="pa/caliber"
            )
        except Exception:
            pass
        return ok(r)

    @bp.route("/v9/pa/caliber/check", methods=["POST"])
    def pa_caliber_check():
        """口径预检（P7 · L2 门）。

        N2（2026-09-30 · PM 批）：**输入形状校到底** —— 错形状一律回可分辨的 ``err(...)``，
        ⛔ 不再 500 ＋ 内部文本（``AttributeError``），⛔ 也不再**假绿**。
        改前有三处会把「形状坏」说成「好读数」：
          · body 是 JSON 数组（``[]``）    ⇒ ``[] or {}`` 吞成 ``{}`` ⇒ ok ／ ``hit_count=0``
          · ``pages`` 是 falsy 非列表（``""``／``0``／``false``）⇒ ``or []`` 吞成 ``[]`` ⇒ ok ／ 0
          · 元素非对象 ／ ``data`` 非对象  ⇒ ``AttributeError`` ⇒ **500 ＋ 内部文本**
        （前两处与 437 假绿 ／ ``_jsonl_lines`` 的 ``0`` ／ 验收-B「过期 0」同族：**0 看起来像读数**。）

        判据（可机检）：① 任何形状错 ⇒ ``{"ok": false, ...}`` ＋ HTTP **400**（⛔ 非 500）；
        ② 错误文本**含出错位置**（``pages[1]``／``pages[0].data``／``body``）；③ 响应里 ⛔ 不得出现内部文本；
        ④ **正形状逐字不动**（与改前同答复）。
        ⚠ 本件只动**输入边界**：⛔ 不碰 ``C.check()`` 语义、⛔ 不碰 store、⛔ 不改返回字段。
        """
        from core.pa import caliber as C

        try:
            p = request.json
        except Exception as _e_body:
            return err("caliber/check: body 不是合法 JSON（%s）" % type(_e_body).__name__)
        if not isinstance(p, dict):
            return err("caliber/check: body 需要 JSON 对象（拿到 %s）" % type(p).__name__)
        pages = p.get("pages")
        if pages is None:
            pages = []
        if not isinstance(pages, list):
            return err("caliber/check: pages 需要列表（拿到 %s）" % type(pages).__name__)
        for i, pg in enumerate(pages):
            if not isinstance(pg, dict):
                return err("caliber/check: pages[%d] 不是对象（拿到 %s）" % (i, type(pg).__name__))
            data = pg.get("data")
            if data is not None and not isinstance(data, dict):
                return err("caliber/check: pages[%d].data 不是对象（拿到 %s）" % (i, type(data).__name__))
        hits = C.check(pages)
        return ok({"hits": hits, "hit_count": len(hits)})

    @bp.route("/v9/pa/audit/preflight", methods=["POST"])
    def pa_audit_preflight():
        """渲染前字段级预检 + 内容合规。规则从画像读(extra_marks 由画像禁忌抽取)。"""
        from core.pa import audit as A

        # N2c：输入形状校到底 —— 错形状一律回可分辨的 err(...)，⛔ 不再 500 ＋ 含糊体。
        # 改前有五处会把「形状坏」说成「服务器出错」：body 非对象 ／ 非法 JSON ／
        # 元素非对象 ／ pages[i].data 非对象（⇒ 下游 `.get` ⇒ AttributeError）。
        # ⚠ 本件只动**输入边界**：⛔ 不碰 A.preflight() 语义、⛔ 不改返回字段、⛔ 不改成功文案。
        try:
            p = request.json
        except Exception as _e_body:
            return err("audit/preflight: body 不是合法 JSON（%s）" % type(_e_body).__name__)
        if p is None:
            p = {}
        if not isinstance(p, dict):
            return err("audit/preflight: body 需要 JSON 对象（拿到 %s）" % type(p).__name__)
        pages = p.get("pages")
        if pages is None:
            pages = []
        if not isinstance(pages, list):
            return err("audit/preflight: pages 需要列表（拿到 %s）" % type(pages).__name__)
        if not pages:
            return err("audit/preflight 需要 pages 列表")
        for _i, _pg in enumerate(pages):
            if not isinstance(_pg, dict):
                return err("audit/preflight: pages[%d] 不是对象（拿到 %s）" % (_i, type(_pg).__name__))
            _d = _pg.get("data")
            if _d is not None and not isinstance(_d, dict):
                return err("audit/preflight: pages[%d].data 不是对象（拿到 %s）" % (_i, type(_d).__name__))
        extra = p.get("extra_marks") or []
        try:
            _pa = _core(p.get("user_id"))
            extra = list(extra) + A.profile_forbidden_marks(
                _pa.profile.entries("aesthetic") + _pa.profile.entries("decision")
            )
        except Exception:
            pass
        issues = A.preflight(pages, extra_marks=extra)
        fails = [x for x in issues if x[1] == "fail"]
        warns = [x for x in issues if x[1] == "warn"]
        out = {
            "pages": len(pages),
            "issues": issues,
            "fail_count": len(fails),
            "warn_count": len(warns),
            "pass": len(fails) == 0,
        }
        try:
            _pa.events.append(
                "fact",
                "audit_preflight",
                {"pages": len(pages), "fail": len(fails), "warn": len(warns), "pass": out["pass"]},
                source="pa/audit",
            )
        except Exception:
            pass
        return ok(out)

    @bp.route("/v9/pa/audit/postcheck", methods=["POST"])
    def pa_audit_postcheck():
        from core.pa import audit as A

        p = request.json or {}
        if not p.get("png_dir") or not p.get("prefix") or not p.get("pptx_dir"):
            return err("audit/postcheck 需要 png_dir/prefix/pptx_dir")
        rep = A.postcheck(p["png_dir"], p["prefix"], p["pptx_dir"], p.get("expected"))
        fails = [x for x in rep["issues"] if x[1] == "fail"]
        rep["pass"] = len(fails) == 0
        try:
            _core(p.get("user_id")).events.append(
                "fact", "audit_postcheck", {"pass": rep["pass"], "issues": len(rep["issues"])}, source="pa/audit"
            )
        except Exception:
            pass
        return ok(rep)

    @bp.route("/v9/pa/act", methods=["POST"])
    def pa_act():
        """PA 本地动作直派(分派层执行原语)。

        用途: 老板说"打开第 7 页给我看"/"关掉 WPS 释放文件锁"时, PA 不必为一次
        系统动作起一整轮 agent 对话 —— 直接派发到 agent_client 白名单执行。

        边界(硬): 只放行 LOCAL_SYSTEM_ACTIONS(open_document/close_wps/lingxi_mcp);
        浏览器动作(navigate/click/publish 等)不走这里, 必须走 agent + 治理门。
        治理门同源: 仍经 browser_local.execute() → 随时停止(stop)对本地动作同样生效。
        """
        from core.tools.browser_local import LOCAL_SYSTEM_ACTIONS, BrowserLocalPlugin

        p = request.json or {}
        action = (p.get("action") or "").strip()
        params = p.get("params") or {}
        if action not in LOCAL_SYSTEM_ACTIONS:
            return err("仅支持本地动作: %s(收到 %r)" % (sorted(LOCAL_SYSTEM_ACTIONS), action))
        if not isinstance(params, dict):
            return err("params 需为对象")
        import types as _types

        args = dict(params)
        args["action"] = action
        ctx = _types.SimpleNamespace(user_id=p.get("user_id") or "", session_id=p.get("session_id") or "")
        r = BrowserLocalPlugin().execute(args, ctx)
        # 记账: 本地动作入 PA 事件流(可追溯老板授权过什么)
        try:
            pa = _core(p.get("user_id"))
            pa.events.append(
                "fact",
                "local_action",
                {
                    "action": action,
                    "path": params.get("path", ""),
                    "ok": bool(r.get("success")),
                    "error": r.get("error", ""),
                },
                source="pa/act",
            )
        except Exception:
            pass
        if r.get("success"):
            return ok({"result": r})
        return jsonify({"ok": False, "error": str(r.get("error") or "动作失败")[:300], "result": r}), 400

    # ---- 序②（2026-10-05 · PM 1235 §三 令）：steer 通道之 HTTP 面（面先钮后 ⇒ 面落 CW 方可去钮之 disabled）----
    #   通道已在 core/gateway/shared_state.py（add_steer ／ drain_steer · 消费性）⇒ 本面唯「入队」。
    #   载荷 ／ 回执之字段名与形 ＝ 本 docstring（CW 候此 · 承 PM 1178 §四）。
    _STEER_MAX_TEXT = 500           # ＝ shared_state.add_steer 之硬截（str(text)[:500]）⇒ 面先拦 · ⛔ 静默截断
    _STEER_KINDS = ("改令",)          # ⭐ PM 1253 §三 裁：唯「改令」（「接管」＝ 待立项 · 须先定义 · 承 PM 1230 §五）

    def _steer_missing(_key):
        u"""缺参 400：**壳从蓝图**（`ok`）＋ **键从族**（`missing` ／ `kind` ／ `route` ＝ `session` 族之 canonical）⇒ 承 PM 1253 §二 裁（⛔ 两族混壳）。"""
        _rule = request.url_rule
        _rt = (_rule.rule if _rule is not None else "?").lstrip("/")
        return jsonify({"ok": False, "error": u"%s: 缺 %s" % (_rt, _key),
                        "missing": [_key], "kind": "missing_param", "route": _rt}), 400

    @bp.route("/v9/pa/steer", methods=["POST"])
    def pa_steer():
        u"""POST /v9/pa/steer —— 把一条「下一步指导」入 steer 通道（**消费性**：每轮 drain 即清）。

        载荷（JSON body）：`session_id`（必）／`text`（必 · ≤500 字）／`kind`（默「改令」· ⭐ 唯 `{改令}`：接管 ＝ 待立项 · ⛔ 送）
          ／`user_id`（选 · 唯留痕）／`topic`（选 · 唯留痕）⇒ 缺参 400（形 ＝ routes/session.py 之 _missing）。
        回执（200）：`ok` ＋ `queued` ＋ 通道之读（`drain_semantics` ／ `inject_point`）
          ＋ 四键同形（`at` ／ `刻之性` ／ `面之径逐字` ／ `印`）。
        ⚠ 形（PM 1253 §二 裁）：**壳从蓝图**（`ok` ／ `err` · 本蓝图 idiom）· **键从族**（`missing` ／ `kind` ／ `route` ＝ `session` 族之 canonical · ⛔ 两族混壳）。
        ⚠ ⛔ 报 `queued_count`：通道唯 `drain_steer`（取走即清）· **无 peek** ⇒ 得数必先消费（假报「已清」）。
        ⚠ 界：`add_steer(session_id, …)` 之键**唯 `session_id`**（⛔ 含 `user_id`）⇒ 同 sid 异用户 ⛔ 隔离（照实载界）。
        """
        from core.gateway import shared_state as _SS

        data = request.get_json(silent=True) or {}
        sid = str(data.get("session_id") or request.args.get("session_id") or "").strip()
        if not sid:
            return _steer_missing("session_id")
        _raw = data.get("text")
        text = "" if _raw is None else str(_raw)
        if not text.strip():
            return _steer_missing("text")
        if len(text) > _STEER_MAX_TEXT:
            return jsonify({"ok": False,
                            "error": u"v9/pa/steer: text 超限（%d ＞ %d 字）" % (len(text), _STEER_MAX_TEXT),
                            "allowed_max": _STEER_MAX_TEXT, "text_len": len(text),
                            "kind": "over_limit", "route": "v9/pa/steer"}), 400
        kind = str(data.get("kind") or "").strip() or "改令"
        if kind not in _STEER_KINDS:
            # ⭐ PM 1253 §三：⛔ 唯 `allowed` —— 「接管」须附其由（＝ 待立项 · 须先定义）
            _why = u"（接管 ＝ 待立项（须先定义）· 承 PM 1230 §五）" if kind == "接管" else u""
            return jsonify({"ok": False, "error": u"v9/pa/steer: kind 未知：%s%s" % (kind[:20], _why),
                            "allowed": list(_STEER_KINDS),
                            "kind": "bad_value", "route": "v9/pa/steer"}), 400
        _SS.add_steer(sid, text)
        print(u"[STEER] POST /v9/pa/steer session=%s kind=%s len=%d" % (sid, kind, len(text)))
        return jsonify({
            "ok": True, "route": "v9/pa/steer", "channel": "steer", "queued": True,
            "session_id": sid, "text": text, "text_len": len(text), "max_text": _STEER_MAX_TEXT,
            "kind": kind, "user_id": (str(data.get("user_id") or "") or None),
            "topic": (str(data.get("topic") or "") or None),
            "drain_semantics": u"消费性：drain 即清空（每轮起点消费 ⇒ 追加为 user 消息 · ⛔ 重放）",
            "inject_point": u"下一轮 LLM 调用前（core/gateway/v9_bridge/round_start.py 每轮 drain_steer）",
            "at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "刻之性": u"写时（入队之实 · ⛔ 读盘）",
            "面之径逐字": str(getattr(_SS, "__file__", "") or ""),
            "印": _code_sha16(pa_steer, _SS),
        })

    @bp.route("/v9/pa/dispatch/history", methods=["GET"])
    def pa_dispatch_history():
        """派发历史读面。BUG-3 三态：rows 空 = 没有派发动作（不适用），不是接线坏了；
        故把判据（记录文件 ＋ 条数）一并给出，读面自己可复核。"""
        pa = _core(request.args.get("user_id"))
        r = pa.handle("dispatch_history")
        _all = r.get("rows") or []
        # ⭐ T2-刀1 ④（2026-10-05）：`?to_seat=` 筛（⛔ 破 `store`／`store_exists`／`count` 与三态判据）
        _want = (request.args.get("to_seat") or "").strip()
        _rows = [x for x in _all if str((x or {}).get("to_seat") or "") == _want] if _want else _all
        # ⭐ T2-刀4 缺之二：行之 `stage` **按四段真走**（＋ `stage_at`／`stage_src`／`chase_count`）
        try:
            from core.pa import receipts as _RC

            _RC.overlay_history(_rows)
        except Exception:
            pass
        r["rows"] = _rows
        r["to_seat"] = (_want or None)
        r["count"] = len(_rows)
        # ⭐ T2-刀9 §〇（2026-10-05 · PM 令）：**态数须真判据 ＋ 附滤**
        #   ⛔ 以**表长**充「等待外部结果」（表长 ⊃ 已终结 ∪ 无席位轴）——**假态**。
        _STAGES4 = ("已派", "已收", "在做", "已收口")
        _seat_rows = [x for x in _rows if str((x or {}).get("to_seat") or "").strip()]
        r["counts"] = {
            "rows": len(_rows),
            "seat_axis": len(_seat_rows),
            "no_seat_axis": len(_rows) - len(_seat_rows),
            "awaiting_receipt": len([x for x in _seat_rows if x.get("stage") != "已收口"]),
            "closed": len([x for x in _rows if x.get("stage") == "已收口"]),
            "by_stage": {s: len([x for x in _rows if x.get("stage") == s]) for s in _STAGES4},
        }
        r["判据"] = {
            "等待外部回执": "to_seat 非空 ∧ stage != 已收口",
            "已终结": "stage == 已收口（派时即已派 ⇒ 无回执者 ⛔ 计入等待）",
            "⛔": "表长 ≠ 等待数（表长 ⊃ 池路行 ＋ 已终结行）",
        }
        r["滤"] = {"面": str(pa.dispatch_rec.path), "式": "逐行谓词（见 判据）",
                  "过面": len(_rows), "印": _RC.RECEIPT_VERSION}
        r["count_all"] = len(_all)
        r["store"] = str(pa.dispatch_rec.path)
        r["store_exists"] = bool(pa.dispatch_rec.path.is_file())
        r["verdict"] = "有派发记录" if _all else "无派发动作发生 ⇒ 空（不适用，非故障）"
        if _want and not _rows:
            r["verdict"] = "无该席之派发（筛 to_seat=%s；面内共 %d 行）" % (_want, len(_all))
        # ⭐ T2-刀26 §二（PM 令 · 2026-10-05）：**面须附「刻」** —— 本面为**活面**（逐次读 dispatch.jsonl，逐次增行）
        #   ⇒ 补**取数刻** ＋ **面之径逐字** ＋ **刻之性**（⛔ 冻结面）＋ **印**（印须载器 · 承 PM 089 §二）。
        r["at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        r["刻之性"] = "读时（活面：本面逐次读 dispatch.jsonl ⇒ 数随刻变 · ⛔ 冻结面）"
        r["面之径逐字"] = str(pa.dispatch_rec.path)
        r["印"] = _code_sha16(pa_dispatch_history, _RC)
        return ok(r)

    @bp.route("/v9/pa/vault/sync", methods=["POST"])
    def pa_vault_sync():
        """账本 -> Obsidian(待办/站会/未读索引)。vault 路径可用 env PA_VAULT_DIR 覆盖。"""
        from core.pa.vault_brain import BrainSync

        pa = _core((request.json or {}).get("user_id"))
        _vr = vault_root()
        vault = os.getenv("PA_VAULT_DIR") or (str(_vr) if _vr is not None else None)
        if not vault:
            return err("vault 未接（选目录）：env PA_VAULT_DIR ∨ 配置 paths.vault_root ∨ "
                       "内置 <data_root>/kb 皆无 —— 请先在「首启引导／设置」里选知识库目录")
        brain_sync = BrainSync(pa.ledger, vault_dir=vault)
        out = {
            "ledger_md": brain_sync.sync_ledger(),
            "unread": brain_sync.unread_index(),
            "standup": brain_sync.daily_standup(),
        }
        return ok(out)

    # ---- 拍板(决策) + 计划时间轴(2026-09-11): 老板对 PA 产物四选一拍板, 留痕 decision_log.json ----
    @bp.route("/v9/pa/plan", methods=["POST"])
    def pa_plan():
        """派活后 PA 先出「语义步骤计划」(时间轴节点=拍板点), 再执行。"""
        from core.pa.decision import generate_plan

        p = request.json or {}
        task = (p.get("task") or "").strip()
        if not task:
            return err("plan 需要 task")
        return ok(generate_plan(task, mode=p.get("mode") or "work", user_id=p.get("user_id")))

    @bp.route("/v9/pa/decision", methods=["POST"])
    def pa_decision():
        """老板拍板: 采纳/小改/大改/退回/暂缓 → 写 decision_log.json。"""
        from core.pa.decision import DECISIONS, DecisionStore

        p = request.json or {}
        decision = (p.get("decision") or "").strip()
        if decision not in DECISIONS:
            return err("decision 必须是: %s" % "/".join(DECISIONS))
        ds = DecisionStore(_data_dir())
        rec = ds.record(
            p.get("user_id"),
            p.get("session_id"),
            p.get("node"),
            p.get("stage"),
            decision,
            p.get("note") or "",
            p.get("task") or "",
        )
        try:
            _core(p.get("user_id")).events.append(
                "fact",
                "pa_decision",
                {"decision": decision, "node": p.get("node"), "stage": p.get("stage")},
                source="pa/decision",
            )
        except Exception:
            pass
        return ok({"decision": rec})

    @bp.route("/v9/pa/decision/log", methods=["GET"])
    def pa_decision_log():
        r"""拍板之 log（只读）。⭐ T2-刀19-补 §二：**按用途分栏** —— 默认 `decisions` 唯**业务**。

        ⛔ 删行：`验收 ／ 自检 ／ 测试`之拍板另栏 `nonbusiness`（照录 · 各带 `用途之由`）。
        `?include_nonbusiness=1` ⇒ 全量（⛔ 破既有键：`decisions` ／ `count` 皆在）。
        """
        from core.pa.decision import DecisionStore, usage_of, split_by_usage

        ds = DecisionStore(_data_dir())
        _rows = ds.list(request.args.get("user_id"), request.args.get("session_id"))
        for _r in _rows:
            _u, _m = usage_of(_r)
            _r["用途"] = _u
            _r["用途之由"] = (_m or u"（无命中词）")
        _biz, _nb = split_by_usage(_rows)
        _inc = str(request.args.get("include_nonbusiness") or "").strip().lower() in ("1", "true", "yes", "on")
        _d = {"decisions": (_rows if _inc else _biz),
              "count": len(_rows if _inc else _biz),
              "nonbusiness": _nb, "nonbusiness_count": len(_nb), "all_count": len(_rows),
              "业务之最新": (_biz[-1] if _biz else None),
              "用途之判据": u"`task ／ note ／ session_id` 含「验收 ／ 自检 ／ 复验 ／ 探针 ／ 测试 ／ e2e ／ canary …」⇒ 非业务",
              "面之径逐字": str(ds.path), "store": str(ds.path),
              "收件人面之指": u"拍板来源之读面 ＝ 本面（默认唯业务）",
              "verdict": ("有拍板记录" if _rows else "无拍板动作发生 ⇒ 空（不适用，非故障）")}
        # ⭐ T2-刀26 §二（PM 裁 17:57 · 下批）：**印须载器之真源** —— 本面之**分栏数**出 `core/pa/decision.py` ⇒ 器 ＝ sha16(路由源 ＋ decision 模块源)
        from core.pa import decision as _D
        _d["印"] = _code_sha16(pa_decision_log, _D)
        return ok(_d)

    # ---- T1（2026-10-05 · PM 071 §二 · 域线之裁）：对外交付之一路 —— 邮件 ----
    # 甲形限域：收件人只许**本人**（CJ_MAIL_USER）∨ PA_MAIL_ALLOW_TO 白名单；
    # 对外（第三人）唯「乙形」= 提醒 ＋ 转交 ＋ **人点**（⛔ 代发第三方内容 · 063 附 新律）。
    @bp.route("/v9/pa/deliver/mail", methods=["POST"])
    def pa_deliver_mail():
        """**可查账的一步交付**：拍板闸（fail-closed）＋ 甲形限域 ＋ 幂等 ＋ 落痕 ＋ 回执四件 ＋ 人话。

        逻辑全在 ``core.pa.mailer.deliver``（纯函数 · 落地前可成对验收）；本路由只做包装。
        ⛔ 缺 ``decision_id`` ⇒ 403 ／ 重放同 ``task_id`` ⇒ 返既有回执（⛔ 重发）
        ／ 落到步 ✗ ⇒ 回执明写「停在哪一步 ＋ 报给谁」。⛔ 口令入屏 ／ 日志 ／ 回执 ／ 台账。
        """
        from core.pa import mailer as _mailer

        # ⭐ T2-刀20 §一：面须**暴露** `dry_run`（⛔ 唯函数参数 ⇒ 无干跑路 ⇒ 探针只能真发）。
        _p = request.json or {}
        _code, _doc = _mailer.deliver(_p, _data_dir(),
                                      dry_run=bool((_p or {}).get('dry_run')))
        # ⭐ T2-刀15 补③：**印须载器**（承 PM 089 §二）—— 器 ＝ 本路由之码之 `sha16`。
        #   ⛔ 载器 ⇒ 读者不知何版所出（半个印）；⛔ 器之印 ⛔ 得 ⇒ `null`（照实「未核」）。
        _c16 = _code_sha16(pa_deliver_mail, _mailer)
        _doc['印'] = _c16
        _rc = _doc.get('receipt')
        if isinstance(_rc, dict) and isinstance(_rc.get('成本'), dict):
            _rc['成本']['印'] = _c16
        return jsonify(_doc), _code

    # ---- T2-刀19 §三：本面**唯 POST** ⇒ 以 GET 核回执者必撞 405（PM 已撞 · 记为「使我再猜」）----
    #   ⭐ 立此 GET 面（只读 · ⛔ 发）：回「**读面之指**」⇒ 此后 ⛔ 再猜。
    @bp.route("/v9/pa/deliver/mail", methods=["GET"])
    def pa_deliver_mail_face():
        r"""发信面之**读面之指**（只读 · ⛔ 发信；⛔ 405 使人猜）。

        本面唯 `POST`（发信）；**核回执**须走 `GET /v9/pa/deliver/authz?task_id=`。
        """
        _d = {
            "面": u"交付·邮件（发信）",
            "动形": u"唯 POST（⛔ 无 GET 之发）",
            "用法": {
                "必填": ["task_id", "user_id", "to", "subject", "body_md", "decision_id"],
                "可选": ["in_reply_to", "src_letter", "stop_to"],
                "to 之形": u"**列表** ∨ **逗号分隔字符串**（`;` ／ `；` 亦可）—— 归一在闸之前",
                "回执四件": [u"回了什么", u"凭什么", u"花了多少", u"谁批的"],
            },
            "读面之指": [
                {"读什么": u"逐次授权留痕（含被拒之次）", "面": "GET /v9/pa/deliver/authz?task_id=<件号>",
                 "滤": "task_id ／ limit（默认 50）", "动形": "GET"},
                {"读什么": u"停手之留痕（`报给谁`）", "面": "POST /v9/pa/deliver/stop", "动形": "POST（写入面 · ⛔ 读）"},
                {"读什么": u"交付之台账（面之径逐字）", "面": "data\\v9\\pa\\deliver_authz.jsonl", "动形": "文件"},
            ],
            "判据": u"缺 `decision_id` ⇒ 403 ／ 收件人非本人 or 白名单 ⇒ 403 ／ 重放同 `task_id` ⇒ 返既有回执",
        }
        _d["印"] = _code_sha16(pa_deliver_mail_face)
        return ok(_d)

    # ---- T2-刀15 补②：**逐次授权留痕**之只读面（承 PM 刀15-补 判据⑤「每次留痕可调」）----
    @bp.route("/v9/pa/deliver/authz", methods=["GET"])
    def pa_deliver_authz():
        """逐次留痕（只读）：`?task_id=` 筛 ＋ `?limit=`（默认 50）。

        行形 ＝ `{件号, 谁批, 何刻, 授权形, decision_id, 果, 报给谁}`（⛔ 口令 ∴ ⛔ 入此）。
        """
        from core.pa import mailer as _mailer

        _u_raw = request.args.get("usage")
        if _u_raw and str(_u_raw).strip() and _mailer.norm_usage(_u_raw) is None:
            # ⭐ T2-刀21 §三：`usage` 未知 ⇒ **400 载 `allowed`**（⛔ 静默返 `0`）
            return jsonify({"ok": False, "error": u"usage 未知：%s" % str(_u_raw)[:40],
                            "allowed": sorted(_mailer.USAGE_ALIASES),
                            "missing": u"`usage` 之值须在 `allowed` 内"}), 400
        _d = _mailer.load_trail(_data_dir(), request.args.get("task_id"),
                                request.args.get("limit") or 50, usage=_u_raw)
        _d["滤"] = ("task_id=" + str(request.args.get("task_id"))) if request.args.get("task_id") else "无（全量 ／ 末 limit 行）"
        _d["滤"] += " ／ usage=" + str(request.args.get("usage") or "all")
        # ⭐ T2-刀26 §二（PM 令 2026-10-05 17:50）：**面之四键同形** —— 台账轴三面（history／authz／lines）一码读
        _d["at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        _d["刻之性"] = "读时（活面：本面逐次读 deliver_authz.jsonl ⇒ 数随刻变 · ⛔ 冻结面）"
        _d["印"] = _code_sha16(pa_deliver_authz, _mailer)
        return ok(_d)

    # ---- T2-刀15 补②：**停手之留痕**（承 PA-6 · 判据⑥：「报给谁」须有字段）----
    @bp.route("/v9/pa/deliver/stop", methods=["POST"])
    def pa_deliver_stop():
        """停手留痕：任一步过不去 ⇒ 停手并报（`报给谁` 恒有字段）。⛔ 静默。"""
        from core.pa import mailer as _mailer

        _d = _mailer.stop_trace(request.json or {}, _data_dir())
        _d["印"] = _code_sha16(pa_deliver_stop, _mailer)
        return ok(_d)

    # ---- 能改(2026-09-11): cfgPerm 后端持久化。PA 不能自改规则(见 registry._CONFIG_FILES 写保护) ----
    @bp.route("/v9/pa/permission", methods=["GET"])
    def pa_permission_get():
        from core.pa.permission import PermissionStore
        from core.pa import permission as _PM

        ps = PermissionStore(os.path.join(_data_dir(), "permission.json"))
        return ok({"level": ps.get(), "grant": _permission_grant_provenance(_data_dir())}, 印=_code_sha16(pa_permission_get, _PM))

    @bp.route("/v9/pa/build", methods=["GET"])
    def pa_build_get():
        """**前端构建指纹**（PM 2026-09-30 批）：页面自报「我是哪一版」。

        判据（PM）：页面能报自身构建 sha16 **且**探针读数必带它 ⇒ 消灭「两版页面无法区分」
        的归属之争。⛔ 指纹取自**服务端实际发出的那份文件**，不是页面自报的常量。
        """
        r = ok(dict(_frontend_build(request.args.get("file") or "pa.html"), 印=_code_sha16(pa_build_get)))
        try:
            r.headers["Cache-Control"] = "no-store"
        except Exception:
            pass
        return r

    @bp.route("/v9/pa/permission", methods=["POST"])
    def pa_permission_post():
        """老板在场改权限档。只认白名单值; PA 无工具触达本路由, 直写被 ForbiddenGuard 拦。"""
        from core.pa.permission import PermissionStore

        p = request.json or {}
        ps = PermissionStore(os.path.join(_data_dir(), "permission.json"))
        r = ps.set(p.get("level"), p.get("user_id") or "")
        if not r.get("ok"):
            return err(r.get("error"))
        try:
            _core(p.get("user_id")).events.append(
                "fact", "permission_change", {"level": r["level"]}, source="pa/permission"
            )
        except Exception:
            pass
        return ok(r)

    @bp.route("/v9/pa/ppt/comments", methods=["GET"])
    def pa_ppt_comments_get():
        """读批注（C2 后端，2026-09-13）。读方：前端加载批注(C3) + 发布清单回溯。"""
        from core.pa import ppt_comments as _pc

        try:
            _deck = request.args.get("deck") or ""
            return jsonify({"ok": True, "comments": _pc.list_comments(_data_dir(), _deck or None), "印": _code_sha16(pa_ppt_comments_get, _pc)})
        except Exception as _e:
            logger.error("ppt/comments 读内部错误: %s: %s", type(_e).__name__, str(_e)[:200])
            return jsonify({"ok": False, "error": "ppt/comments: 读内部错误（已记日志）"}), 500

    @bp.route("/v9/pa/ppt/comments", methods=["POST"])
    def pa_ppt_comments_post():
        """写批注（C2 后端，2026-09-13）。前端双写：localStorage 保留离线可用，后端为准。"""
        from core.pa import ppt_comments as _pc

        _body = request.get_json(silent=True)
        if _body is None:
            _body = {}
        if not isinstance(_body, dict):
            return jsonify({"ok": False, "error": "ppt/comments: body 需要 JSON 对象（拿到 %s）" % type(_body).__name__}), 400
        try:
            _rec = _pc.add_comment(
                _data_dir(), _body.get("deck") or "", _body.get("page_index"), _body.get("comment") or ""
            )
            return jsonify({"ok": True, "comment": _rec})
        except ValueError as _ve:
            return jsonify({"ok": False, "error": str(_ve)}), 400
        except Exception as _e:
            logger.error("ppt/comments 写内部错误: %s: %s", type(_e).__name__, str(_e)[:200])
            return jsonify({"ok": False, "error": "ppt/comments: 写内部错误（已记日志）"}), 500

    @bp.route("/v9/pa/artifact/thumbs", methods=["POST"])
    def pa_artifact_thumbs_post():
        """C1(批73): 缩略图上传落盘。**后端定位置**，出参只给相对 url_base。"""
        from core.pa import artifact_thumbs as _at

        _b = request.get_json(silent=True)
        if _b is None:
            _b = {}
        if not isinstance(_b, dict):
            return jsonify({"ok": False, "error": "artifact/thumbs: body 需要 JSON 对象（拿到 %s）" % type(_b).__name__}), 400
        try:
            _r = _at.save_thumbs(_b.get("deck"), _b.get("files") or [])
            return jsonify(_r), (200 if _r.get("ok") else 400)
        except Exception as _e:
            logger.error("artifact/thumbs 内部错误: %s: %s", type(_e).__name__, str(_e)[:200])
            return jsonify({"ok": False, "error": "artifact/thumbs: 内部错误（已记日志）"}), 500

    @bp.route("/v9/pa/source_faces", methods=["GET"])
    def pa_source_faces():
        """画像素材面（左栏「来源面」）之读数 —— **只读**。

        PM 2026-10-05 令「M1 接线收口：加两个素材面」⇒ 面 `文件`（文本产出）＋ 面 `出图`（图产出 · **按目录聚合**）。
        ⛔ 起子进程 ／ ⛔ 写盘 ／ ⛔ 读图内容（只 `scandir` ＋ `stat`）｜⭐ 面名**逐字** ＝ 前端之面（`文件` ／ `出图`）。
        """
        try:
            return jsonify(dict(_src_face_readout(), 印器=_code_sha16(pa_source_faces, _src_face_readout)))
        except Exception as _e:
            logger.error("source_faces 内部错误: %s: %s", type(_e).__name__, str(_e)[:200])
            return jsonify({"ok": False, "error": "source_faces: 内部错误（已记日志）"}), 500

    @bp.route("/v9/pa/ui_faces", methods=["GET"])
    def pa_ui_faces():
        """⭐ UI 面册（`web/pa/faces/*.js`）之读数 —— **只读**（承 pm_1384 §二.1 ／ §三.1）。

        名之分（PM 1384 §二.1 之裁）：`source_faces` ＝ **源之面**（文件 ／ 出图 · 素材）；
        本者 ＝ **UI 面册**（前端之面之册）⇒ **二物 ⛔ 同轴** ⇒ ⛔ 撞名 · ⛔ 混一。
        ⛔ 起子进程 ／ ⛔ 写盘 ／ ⛔ 绝对径入面（`file` 皆 `faces/<名>.js` 之相对径）。
        """
        try:
            return jsonify(dict(_ui_faces_readout(), 印=_code_sha16(pa_ui_faces, _ui_faces_readout)))
        except Exception as _e:
            logger.error("ui_faces 内部错误: %s: %s", type(_e).__name__, str(_e)[:200])
            return jsonify({"ok": False, "error": "ui_faces: 内部错误（已记日志）"}), 500

    @bp.route("/v9/pa/first_run", methods=["GET"])
    def pa_first_run():
        """⭐ 首启引导（净机之「第一屏」）之读数 —— **只读**（承 pm_1384 §三.3）。

        ⒜ 数据在本机（**人话** · ⛔ 行话）⒝ 模型三态（未接／在·无权重／在∧可用）＋ **修之门**
        ⒞ 数据目录（真源 `env_face.resolve_paths()` · ⛔ 造径）⒟ ⛔ 静默（缺则显因）。
        ⛔ 写盘 ／ ⛔ 绝对径之字面入面（径为**值**，⛔ 硬编）｜唯 TCP 探 ollama（同 preflight）。
        """
        try:
            return jsonify(dict(_first_run_readout(), 印=_code_sha16(pa_first_run, _first_run_readout)))
        except Exception as _e:
            logger.error("first_run 内部错误: %s: %s", type(_e).__name__, str(_e)[:200])
            return jsonify({"ok": False, "error": "first_run: 内部错误（已记日志）"}), 500

    @bp.route("/v9/pa/vault/set", methods=["POST"])
    def pa_vault_set():
        u"""⭐ 甲 · 件一（pm_1520 §二.1）：**选一个笔记目录** ⇒ 立库根（`paths.vault_root`）—— **唯一写端**。

        体：`{"path": "<绝对径>"}`（⇒ 立之）｜`{"path": ""}`（⇒ **清** ⇒ 落回内置空库 ／ 未接）。
        校：**在 ∧ 可写**（⛔ 静默收）｜**幂等**（同值 ⇒ `changed:false` · ⛔ 报错）。
        回：`{ok, vault_root, vault_root_src, state, at, changed, env_override, note}`；
        错：`{ok:false, error:"<逐字>"}`（前端唯渲 · ⛔ 自编）。
        ⛔ 写非库根之物 ／ ⛔ 起停 ／ ⛔ 平台动作。
        """
        from time import strftime as _stf
        _p = request.get_json(silent=True)
        if not isinstance(_p, dict) or "path" not in _p:
            return jsonify({"ok": False,
                            "error": u'体须为 {"path": "<\u7edd\u5bf9\u5f84>"} ∨ {"path": ""}'}), 400
        _raw = _p.get("path")
        if not isinstance(_raw, str):
            return jsonify({"ok": False, "error": u"path 须为字符串"}), 400
        _s = _raw.strip()
        try:
            from core.lib.unified_config import unified_config as _uc
            if _s == "":
                _r = _uc.set_and_save("paths.vault_root", "")
            else:
                if not os.path.isabs(_s):
                    return jsonify({"ok": False, "error": u"径须为绝对径：%s" % _s}), 400
                _ap = os.path.abspath(_s)
                if not os.path.isdir(_ap):
                    return jsonify({"ok": False, "error": u"径不存在 ／ 非目录：%s" % _ap}), 400
                if not os.access(_ap, os.W_OK):
                    return jsonify({"ok": False, "error": u"径不可写：%s" % _ap}), 400
                _r = _uc.set_and_save("paths.vault_root", _ap)
        except Exception as _e:
            logger.error("vault/set 内部错误: %s: %s", type(_e).__name__, str(_e)[:200])
            return jsonify({"ok": False,
                            "error": u"写配置失败：%s: %s" % (type(_e).__name__, str(_e)[:160])}), 500
        from core.lib import paths as _P
        _vr = _P.vault_root()
        _src = _P.vault_root_src()[1]
        _code = pa_vault_state_code(root=(str(_vr) if _vr else None))[0]
        _on, _note = vault_env_override()
        return jsonify({
            "ok": True, "at": _stf("%Y-%m-%d %H:%M:%S"),
            "changed": bool(_r.get("changed")),
            "path": _s, "file": _r.get("file"), "backup": _r.get("backup"),
            "vault_root": (str(_vr) if _vr else None),
            "vault_root_src": _src, "state": _code,
            "env_override": _on, "note": _note,
        })
    @bp.route("/v9/pa/kb_mapping", methods=["GET"])
    def pa_kb_mapping():
        """知识库 ↔ 沙箱映射（批176 副指标 A）：**只读**三列 + 状态枚举。

        只 stat，不写任何一侧（N1–N6 零噪音的前置约束）；镜像记录（若有）读沙箱 .kb_mirror.json。
        """
        import json as _json

        from core.lib.gateway_helpers import _get_sandbox_base as _gsb

        try:
            _uid = request.args.get("user_id")
            _sid = (request.args.get("session_id") or "").strip()
            _scope = request.args.get("scope") or KB_MAPPING_DEFAULT_SCOPE
            _limit = request.args.get("limit") or 100
            _vr = vault_root()   # ⚠ 可 None（未接）⇒ ⛔ str(None) 之假径
            _kb = os.getenv("PA_VAULT_DIR") or (str(_vr) if _vr is not None else "")
            _sb = ""
            _man = None
            if _sid:
                try:
                    _sb = str(_gsb(_uid or "default", _sid))
                except Exception:
                    _sb = ""
                _mf = (Path(_sb) / ".kb_mirror.json") if _sb else None
                if _mf is not None and _mf.is_file():
                    try:
                        _man = _json.loads(_mf.read_text(encoding="utf-8"))
                    except Exception:
                        _man = None
            return jsonify(
                {
                    "ok": True,
                    **build_kb_mapping(kb_root=_kb, sandbox_root=_sb, scope=_scope, limit=_limit, mirror_manifest=_man),
                    "印": _code_sha16(pa_kb_mapping, build_kb_mapping),
                }
            )
        except ValueError as _ve:
            return jsonify({"ok": False, "error": str(_ve)}), 400
        except Exception as _e:
            logger.error("kb_mapping 内部错误: %s: %s", type(_e).__name__, str(_e)[:200])
            return jsonify({"ok": False, "error": "kb_mapping: 内部错误（已记日志）"}), 500

    # ---- 层 1 · 归档正文落服务端（X-11；老板/DS 2026-09-18 拍 A：Windows 起本机网关 + 端口错峰）----
    # 目的：**本地足迹与归档条数解耦** —— 正文搬进 data/v9/pa/threads_<uid>.json，
    #       前端随即将本地 archived[].msgs 换成最小索引（id/title/archived_at/msg_count/server）。
    # 纪律（与方案 §三 逐条对应）：
    #   1) **按 id 合并**：不覆盖既有条、不产生重复；同一批重发 ⇒ written=0（幂等）；
    #   2) **只碰 archived**：不改 POST /v9/pa/threads 的单线程关闭语义，不动 threads/activeThread；
    #   3) **写完立刻读回**：缺任一条 ⇒ ok:False（**不得假装成功**）；
    #   4) 校验**全部通过才 save**（本端点自身不留半截；前端「本地一字不改」由前端保证）；
    #   5) items 空 / 项缺 id / 缺 user_id / uid 非法 ⇒ 400 且**零写入**；
    #   6) 按 user_id 隔离（threads_<uid>.json）；非法 uid（路径分隔/穿越）⇒ 400；
    #   7) **不自动删除任何数据**（批221·A：归档不设上限、不裁剪）。
    def _archive_uid(raw):
        """uid 必须是**单段**标识：拒空/拒路径分隔/拒 '..'/拒空字节（防穿越出 data/v9/pa/）。"""
        s = str(raw or "").strip()
        if not s:
            raise ValueError("user_id 缺失")
        if chr(0) in s:
            raise ValueError("user_id 含非法字符")
        if s in (".", "..") or "/" in s or "\\" in s or ":" in s:
            raise ValueError("user_id 必须是单段标识（不允许路径分隔/穿越）")
        return s

    @bp.route("/v9/pa/archive", methods=["POST"])
    def pa_archive_post():
        """归档正文落服务端（层 1）。入参 {user_id, items:[{id,title,archived_at,msgs}]}。"""
        import json as _json

        from core.pa.threads import ThreadStore, ThreadStoreCorrupt

        body = request.get_json(silent=True) or {}
        try:
            uid = _archive_uid(body.get("user_id"))
        except ValueError as _ve:
            return err(_ve, 400)
        items = body.get("items")
        if not isinstance(items, list) or not items:
            return err("items 必须是非空数组", 400)
        for _it in items:
            if not isinstance(_it, dict) or not str(_it.get("id") or "").strip():
                return err("每个 item 必须有非空 id", 400)

        ts = ThreadStore(_data_dir())
        try:
            state = ts.load(uid)
        except ThreadStoreCorrupt as _c:
            # X-17 关键止损：坏状态**不得当空基线**（否则一次写即清空历史归档）⇒ 报错且**零写入**
            return jsonify({"ok": False, "error": "thread_state_corrupt",
                            "message": str(_c), "path": _c.path, "written": 0}), 409
        archived = state.get("archived")
        if not isinstance(archived, list):
            archived = []
        by_id = {}
        order = []
        for _a in archived:
            if isinstance(_a, dict) and _a.get("id") is not None:
                _k = str(_a["id"])
                if _k not in by_id:
                    order.append(_k)
                by_id[_k] = _a
        written = 0
        for _it in items:
            _k = str(_it.get("id"))
            _old = by_id.get(_k)
            _new = dict(_it)
            if _old is None or _json.dumps(_old, ensure_ascii=False, sort_keys=True) != _json.dumps(
                _new, ensure_ascii=False, sort_keys=True
            ):
                written += 1
            if _old is None:
                order.append(_k)
            by_id[_k] = _new
        state["archived"] = [by_id[_k] for _k in order]
        try:
            res = ts.save(uid, state)
        except ThreadStoreCorrupt as _c:
            # X-17② 批 2：save 现在也 fail-loud（坏状态拒绝写入）⇒ 与 load 同形状回报，
            # 不把「读→写」窗口内变坏的情况漏成 Flask HTML 500（前端 `if(r.ok)` 依赖 JSON 形状）。
            return jsonify({"ok": False, "error": "thread_state_corrupt",
                            "message": str(_c), "path": _c.path, "written": 0}), 409
        if not (isinstance(res, dict) and res.get("ok")):
            return jsonify({"ok": False, "error": "写入失败：save 未返回 ok", "written": 0}), 500
        # **读回确认**（本项目既有教训：测试绿 ≠ 数据在）
        back = ts.load(uid)
        back_ids = {
            str(_a["id"]) for _a in (back.get("archived") or []) if isinstance(_a, dict) and _a.get("id") is not None
        }
        missing = [str(_it.get("id")) for _it in items if str(_it.get("id")) not in back_ids]
        if missing:
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "读回不一致：缺 %d 条" % len(missing),
                        "missing": missing[:10],
                        "written": 0,
                    }
                ),
                500,
            )
        return ok(
            {
                "written": written,
                "archived_total": len(back.get("archived") or []),
                "path": str(res.get("path") or ""),
            }
        )

    @bp.route("/v9/pa/archive/<archive_id>", methods=["GET"])
    def pa_archive_get(archive_id):
        """按 id 取一条归档（含正文）。**查不到返 404，不得拿空对象冒充**。"""
        from core.pa.threads import ThreadStore, ThreadStoreCorrupt

        try:
            uid = _archive_uid(request.args.get("user_id"))
        except ValueError as _ve:
            return err(_ve, 400)
        try:
            state = ThreadStore(_data_dir()).load(uid)
        except ThreadStoreCorrupt as _c:
            # X-17：损坏**不得谎报 404「不存在」**（404 = 确实没这条；读不动 ≠ 不存在）
            return jsonify({"ok": False, "error": "thread_state_corrupt",
                            "message": str(_c), "path": _c.path}), 409
        for _a in state.get("archived") or []:
            if isinstance(_a, dict) and str(_a.get("id")) == str(archive_id):
                return ok({"item": _a})
        return jsonify({"ok": False, "error": "archive_not_found"}), 404
    # ---- X-16 批 B（DS 2026-09-18 拍）：PA 状态不可用 ⇒ **可读提示**，不外泄原始 traceback ----
    from core.pa.state_out import PAStateCorrupt

    @bp.errorhandler(PAStateCorrupt)
    def _pa_state_corrupt(e):
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "pa_state_corrupt",
                    "message": str(e),
                    "path": getattr(e, "path", ""),
                    "hint": "状态文件已隔离到同目录 .quarantine/；可人工核对后放回，或按业务重建。",
                }
            ),
            409,
        )

    # ===== 丙-P0：留言板 ＋ 一键诊断（承 pm_1634 §二 · 技术总监席 f202f89 · 2026-10-07）=====
    # 铁律：**内测期 ⛔ 出机** —— 落点唯本机之收件目录（`feedback_target.outbound()` 为唯一判据）；
    # 本区之端⛔ 引网络之件（其证 ＝ 结构齿 `tests/unit/test_pa_feedback_1634.py` 之源码扫）。
    def _fed_root():
        from core.pa import feedback_store as _fs
        return _fs.root_of(None)

    def _fed_boot():
        from core.gateway.boot_progress import boot_progress
        return boot_progress.snapshot()

    def _fed_version():
        try:
            from core.lib import build_info
            _d, _n = build_info.read(None)
            return (_d or {}).get("version")
        except Exception:
            return None

    def _fed_port():
        try:
            from core.lib import port_config
            return port_config.gateway_port()
        except Exception:
            return None

    @bp.route("/v9/pa/feedback/target", methods=["GET"])
    def pa_feedback_target():
        """落点之声明（**运维 ／ 机器之端** —— 承 pm_1640 §一.2 ／ §一.3：**面唯读 `/health`**）。
        ⚠ 其形**唯自** `feedback_target.face()` 出（与 `/health.feedback` **同一处** ⇒ ⛔ 二处各写）。
        """
        from core.lib import feedback_target as _ft
        return ok(_ft.face())

    @bp.route("/v9/pa/feedback", methods=["POST"])
    def pa_feedback_submit():
        """收件（题 ＋ 文 ＋ 附件 ＋ 逐项勾选）⇒ 落**本机**（⛔ 出机 · ⛔ 出站请求）。"""
        from core.pa import feedback_store as _fs
        data = request.get_json(silent=True) or {}
        try:
            fid, doc, rows = _fs.submit(None, data)
        except _fs.FeedbackError as _e:
            return err(str(_e), 400)
        except Exception as _e2:
            return err("收件失败：%s: %s" % (type(_e2).__name__, _e2), 500)
        for _r in rows:
            print(_r)
        return ok({"id": fid, "at": doc["at"], "state": doc["state"],
                   "attach_n": len(doc["attach"]), "consent": doc["consent"],
                   "outbound": doc["target"]["outbound"], "hint": "已存本机；内测期不联网发送"})

    @bp.route("/v9/pa/feedback", methods=["GET"])
    def pa_feedback_list():
        """取件之列（客服席 ／ 板之「我的留言」）—— 新者先 ∧ ⛔ 正文全载。"""
        from core.pa import feedback_store as _fs
        try:
            lim = int(request.args.get("limit") or 50)
        except Exception:
            lim = 50
        return ok({"items": _fs.list_items(None, limit=lim)})

    @bp.route("/v9/pa/feedback/<fid>", methods=["GET"])
    def pa_feedback_item(fid):
        """取件之全 ＋ 回话（照今日原型之黄框）。"""
        from core.pa import feedback_store as _fs
        it = _fs.read_item(None, fid)
        if it is None:
            return err("件 ⛔ 见（%s）" % str(fid)[:40], 404)
        return ok({"item": it})

    @bp.route("/v9/pa/feedback/<fid>/reply", methods=["POST"])
    def pa_feedback_reply(fid):
        """回话（**客服席之口**）⇒ 落 `回话.json` ⇒ 板上显（⛔ 另一体系）。"""
        from core.pa import feedback_store as _fs
        data = request.get_json(silent=True) or {}
        try:
            rows = _fs.write_reply(None, fid, data.get("text"), by=(data.get("by") or "客服席"))
        except _fs.FeedbackError as _e:
            return err(str(_e), 400)
        for _r in rows:
            print(_r)
        return ok({"id": str(fid), "replied": True})

    @bp.route("/v9/pa/diagnostics", methods=["POST"])
    def pa_diagnostics_build():
        """一键诊断包（**唯落本机** · ⛔ 上传）：version ＋ 装根清单 ＋ 日志尾 ＋ health ＋ 环境。"""
        from core.pa import diagnostics as _dg
        data = request.get_json(silent=True) or {}
        snap = data.get("health") if isinstance(data.get("health"), dict) else None
        if snap is None:
            try:
                snap = {"boot": _fed_boot(), "version": _fed_version()}
            except Exception:
                snap = None
        try:
            zp, rows = _dg.build(port=_fed_port(), health=snap)
        except Exception as _e:
            return err("打包失败：%s: %s" % (type(_e).__name__, _e), 500)
        for _r in rows:
            print(_r)
        return ok({"pack": zp, "bytes": __import__("os").path.getsize(zp),
                   "members": _dg.members(zp), "uploaded": False,
                   "hint": "唯落本机；由你自己决定交给谁（⛔ 自动上传）"})

    # ---- 本机体检（只读 · 七面 · 一阶段）—— pm_1750 §二 ／ pm_1751 §一–§四 ／ pm_1753 §一–§二 ----
    #   ⭐ 唯读：⛔ 写 ／ ⛔ 改注册表（`KEY_READ`）／ ⛔ 起停服务 ／ ⛔ 提权静默（须授权者明标）；
    #   ⛔ 出机（全程本机）；本机闸 `_loopback`。实现在 `core/pa/sys_face.py`
    #   （**薄壳**：本处唯接线 ⇒ ⛔ 主逻辑在此 · ⛔ 二套读者）。
    @bp.route("/v9/pa/sys/snapshot", methods=["GET"])
    def pa_sys_snapshot():
        """七面之合体（一屏 ＝ 一次取）。`?fresh=1` ⇒ 真扫（有界）。"""
        if not _loopback(request):
            return err("本机体检唯本机可用（⛔ 远机）", 403)
        from core.pa import sys_face as _sf
        _fresh = str(request.args.get("fresh") or "").strip() in ("1", "true", "yes")
        out = _sf.snapshot(fresh=_fresh)
        out["印"] = _code_sha16(pa_sys_snapshot, _sf)
        return ok(out)

    @bp.route("/v9/pa/sys/<panel>", methods=["GET"])
    def pa_sys_panel(panel):
        """单面之盘（`disk ／ disk_c ／ windows ／ startup ／ perf ／ net ／ guard`）。"""
        if not _loopback(request):
            return err("本机体检唯本机可用（⛔ 远机）", 403)
        from core.pa import sys_face as _sf
        pid = str(panel or "").strip()
        if pid not in _sf.PANELS:
            return err("⛔ 未识之面：%s（白名单：%s）"
                       % (pid, " ／ ".join(_sf.PANELS)), 400)
        _fresh = str(request.args.get("fresh") or "").strip() in ("1", "true", "yes")
        out = _sf.build(pid, fresh=_fresh)
        out["印"] = _code_sha16(pa_sys_panel, _sf)
        return ok(out)

    # ---- 本机管理（二阶段 · 授权之动作）—— pm_1852 §四.2（准形 ＝ pm_1847 §一）----
    #   ⭐ 二段：`dry_run`（**缺省 true**）⇒ 预案 ＋ 一次性 `token`（TTL `120 s` ·
    #   绑 `act` ／ `target` ／ **预案之印**）⇒ `dry_run:false` ＋ `token` ⇒
    #   真跑 ⇒ 回执四件 ＋ **撤之径**。⛔ 提权静默 ／ ⛔ 出机 ／ 可撤（入 `_trash`）／ 幂等 ／ 审计。
    #   实现在 `core/pa/sys_act.py`（**薄壳**：本处唯接线 · ⛔ 二套读者）。
    @bp.route("/v9/pa/sys/act", methods=["POST"])
    def pa_sys_act():
        """本机管理之一处入口（唯本机 · ⛔ 远机 403 · ⛔ 出机）。"""
        if not _loopback(request):
            return err("本机管理唯本机可用（⛔ 远机）", 403)
        from core.pa import sys_act as _sa
        _b = request.get_json(silent=True) or {}
        out = _sa.act(act=_b.get("act"), target=_b.get("target"),
                      dry_run=_b.get("dry_run", True), token=_b.get("token") or "",
                      axis=str(_b.get("axis") or "sys"), data_dir=_data_dir())
        if not out.get("ok"):
            return err(out.get("因") or "⛔ 未成", int(out.get("code") or 400))
        # ⚠ 用 `器印`（⛔ `印`）—— 顶层之 `印` 是**预案之印**（绑 token）· ⛔ 覆。
        out["器印"] = _code_sha16(pa_sys_act, _sa)
        return ok(out)

    # ---- 「今日」四行（一处出四类）—— pm_1824 §二.1 ----
    #   四类之判据**唯在** core/pa/today.py 一处（⛔ 前端各判 ⇒ 必歧）；本处唯接线（**薄壳**）。
    @bp.route("/v9/pa/today", methods=["GET"])
    def pa_today():
        """四行合体：要我拍的 ／ 今天该做的 ／ 在等的 ／ 近来之痕（各带 数 ／ 源 ／ 去处）。

        ⚠ 只读；某源读不动 ⇒ 该源 `读数: null` ＋ `因`（**⛔ 以 0 充「没有」**）。
        """
        from core.pa import today as _TDY
        out = _TDY.build(data_dir=_data_dir(),
                         user_id=request.args.get("user_id"),
                         session_id=request.args.get("session_id"))
        out["印"] = _code_sha16(pa_today, _TDY)
        return ok(out)

    app.register_blueprint(bp)
    # ⭐⭐ pm_1802 §一.1（令）：**挂载即定形** —— 能力面清单由**本次挂载后**之路由表现生
    #   （新路由一上 ⇒ 清单自跟 · ⛔ 手写常量 ⇒ 防漂）。
    _set_capability_brief(app)
    return bp


# ⭐ 惰算之**四门**（甲 · 件三 · 一处定形）—— 内读者**唯此四门**。
#   由：模块级 `__getattr__` **唯**外读者（`module.NAME` ／ `from ... import`）得用；
#   本模块**自己**之函数取全局名**不经**之（`LOAD_GLOBAL` 直查 `__dict__`）⇒ 内读者须显式调门。
def pa_faces():
    u"""PA **检索面**之表（**惰算** · pm_1520 §二.3）—— 旧名 `PA_FACES` 亦由此出。"""
    return _pa_faces_tables()[0]


def pa_faces_gate():
    u"""`PA_ORG_FACES` 之**门**（`org` ／ `product` · 惰算）。"""
    return _pa_faces_tables()[1]


def pa_src_faces():
    u"""画像**素材面**之表（惰算 · ⛔ 检索面）。"""
    return _src_faces_tables()[0]


def pa_src_faces_gate():
    u"""素材面之门（惰算）。"""
    return _src_faces_tables()[1]


# ===== ⭐ 惰算之门（甲 · 件三 · pm_1520 §二.3）—— 一处定形 =====
# 由：`_FACE_WS` ／ `_FACE_VR` ／ `PA_FACES`（＋ `PA_SRC_FACES`）旧为**顶层赋值** ⇒ **import 即定形**
#     ⇒ 改库根 ⇒ 须重起方生效。本门按名**当刻**算（⛔ 缓存 ⇒ 无「旧缓存残留」之反控）。
# ⚠ 其名**唯此一处**出（⛔ 二处各判 · 承「一处定形」）；令以 `AttributeError` 收（⛔ 吞）。
def __getattr__(name):
    u"""模块级惰算（⛔ 顶层赋值 ⇒ ⛔ import 即定形）—— ⛔ 缓存。"""
    if name == "_FACE_WS":
        return ws_root()
    if name == "_FACE_VR":
        return vault_root()
    if name == "PA_FACES":
        return pa_faces()
    if name == "PA_FACES_GATE":
        return pa_faces_gate()
    if name == "PA_SRC_FACES":
        return pa_src_faces()
    if name == "PA_SRC_FACES_GATE":
        return pa_src_faces_gate()
    raise AttributeError("module %r has no attribute %r" % (__name__, name))
