# -*- coding: utf-8 -*-
u"""「未做而似做」之辞 —— **运行期闸**（一处定形 · pm_1859 §一.3⒞ ／ §一.4）。

象（一手 · pm_1859 §〇）：老板于**办事**轴问「你能检查电脑吗」⇒ 授权 ⇒ 要
`local_client status` ⇒ 说「执行」⇒ **五轮皆 ⛔ 真调**，而辞曰「已把 local_client
status 当动作受理」「待核实，不瞎报」「这轮上下文里仍没带回接口实际返回」。
其字面正合 `PA_CHANNEL_CLAUSE` 之**禁辞表** —— 提示词**禁了**而模型**照犯**
⇒ 提示 ⛔ 能拦 ⇒ 须**运行期**机检（本模块）。

本模块 ＝ 禁辞之**唯一真源**（三处读者同源 · ⛔ 各写一份）：
  ⒜ `core/pa/gateway_routes.py::pa_dialog` 之回执 —— `channel.untrue_wording`
     （陪伴轴 · 唯**标** · ⛔ 改用户面之辞 —— 承 pm_1802 §一.2）；
  ⒝ `core/gateway/v9_chat/bridge_call.py::run_bridge_sync` —— `/v9/agent/chat`
     之**同步**路（办事轴 · 标 ＋ 重写）；
  ⒞ 同件 `make_stream_response` 之 `done` 事件 —— **流式**路（同上）。

判据（pm_1859 §一.4）：**本轮输出含禁辞 ∧ 本轮 ⛔ 有 `tool_call`** ⇒ 判为不实。
  ⒜ 有 `tool_call` ⇒ 「我做了」有真迹可查（`tool_steps`）⇒ ⛔ 入闸
     （否则「已办 ＋ 真调」亦被标 ⇒ 假阳）；
  ⒝ `tool_steps` 由桥接循环落（＝ 本轮**已执行**之步）⇒ 与本判同源。

⚠ 字面**转义写**（承 `gateway_routes.py` 之 L56-57 ／ L86）—— 源内 `rg` ⛔ 命中
  （齿 `tests/unit/test_pa_agent_chat_1859.py` 逐字核之）。
"""
from __future__ import annotations

#: 禁辞表 —— 与 `gateway_routes.PA_CHANNEL_CLAUSE` 之第 11 条**同表**（⛔ 增删而不改彼）。
WORDS = (
    u"\u5df2\u53d7\u7406",
    u"\u5df2\u5b89\u6392",
    u"\u5df2\u8f6c\u529e",
    u"\u6b63\u5728\u5904\u7406",
)

#: 标之前缀（**用户可见** · ⛔ 静默 —— pm_1859 §一.4）。
#   ⚠ 本句**不含**禁辞之字面（⛔ 以免自咬）。
#   ⭐ 去饰（pm_2062 §三.1）：本句**直入回话正文** ⇒ ⭐ **唯人话** —— ⛔ 载 `**` ／ ⛔ 载 `⛔`
#     （皆我方内部之饰 ⇒ ⛔ 上用户面）∧ 「工具步 = 0」⇒ 「工具步 0 个」。
#     ⭐ 工程之据（hits ／ tool_calls ／ flagged）**唯**入结构键 resp[untrue_wording]（⛔ 上屏）。
#   ⭐ 第二行（系统之注）：裁**准留**（pm_2064 §一）—— 其义 ＝ **免责之照实**（免用户误读为「模型自述」）
#     ⇒ 唯**去饰**（人话化 · ⛔ 载 `⛔`）：`——（此提示由系统所加）`。
MARK = (u"\u26a0 本轮之回话含「未做而似做」之词（%s）—— 本轮没有真调（工具步 0 个）⇒ 下面这些字不作数，请以「待核实」视之。\n——（此提示由系统所加）\n\n")


def scan(text):
    u"""命中禁辞（按 `WORDS` 之序 · ⛔ 去重 · ⛔ 改写）。"""
    t = text or ""
    return [w for w in WORDS if w in t]


def verdict(reply, tool_steps=None):
    u"""判据（**一处定形**）：含禁辞 ∧ ⛔ 有 `tool_call` ⇒ `flagged`。

    返回 `{"hits", "tool_calls", "flagged"}` —— `hits` 即真据（⛔ 只给一个布尔）。
    """
    hits = scan(reply)
    n = len(list(tool_steps or []))
    return {"hits": hits, "tool_calls": n, "flagged": bool(hits) and n == 0}


def apply_gate(resp):
    u"""`/v9/agent/chat` 之**一条闸**（同步 ／ 流式同用）—— 就地改 `resp` 并回闸果。

    ⛔ 命中 ／ 有真调 ⇒ **一字不动**（⛔ 误伤真办之轮）。
    ⭐ 命中 ∧ ⛔ 真调 ⇒ ⒜ 回话前加**可见**之标（⛔ 静默）
       ⒝ 回执载结构化键 `untrue_wording`（前端 ／ 台账可查）。
    """
    if not isinstance(resp, dict):
        return {"hits": [], "tool_calls": 0, "flagged": False}
    _msg = None
    _reply = ""
    try:
        _chs = ((resp.get("data") or {}).get("choices") or [])
        if _chs and isinstance(_chs[0], dict) and isinstance(_chs[0].get("message"), dict):
            _msg = _chs[0]["message"]
            _reply = _msg.get("content") or ""
    except Exception:
        _msg, _reply = None, ""
    v = verdict(_reply, resp.get("tool_steps"))
    if not v["flagged"]:
        return v
    resp["untrue_wording"] = dict(v)
    if _msg is not None:
        _msg["content"] = (MARK % u"／".join(v["hits"])) + _reply
    return v
