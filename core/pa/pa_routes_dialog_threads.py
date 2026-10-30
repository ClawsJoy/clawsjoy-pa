# -*- coding: utf-8 -*-
"""PA 路由 · dialog_threads 簇（②v1 拆件 · 由 gateway_routes.py 机械切出 · 7 条路由）。

共享面唯 `pa_routes_common`（`bp` 唯彼处建）；本件 ⛔ 复建蓝图。
⭐ 导入即挂：件末 `register(bp)`；endpoint 名仍 `pa_routes.<func>`（⛔ 变）。
"""

import time
from pathlib import Path
from flask import jsonify, request
from core.pa.pa_routes_common import bp, ok, err
from core.pa.pa_routes_common import (
    PAStateCorrupt, _code_sha16,
    _core, _data_dir, _owner_corrupt_json, _pa_brain_of_app,
    _pa_read_at, err, ok, register_pa_routes,
)
from core.pa.pa_routes_chat_engine import (
    _dialog_sessions, _jsonl_lines, _lines_delta, pa_gate_view,
)
from core.pa.pa_routes_ledger_audit import (
    _uid_identity,
)
from core.pa.pa_routes_roster_seats import (
    _uid_safe,
)


PA_SYSTEM_HEAD = (
    "你是老板的私人 PA(主权 agent)，不是通用聊天机器人。铁律：\n"
    "1) 就事论事、任务目标导向：始终围绕老板的目标/决策，不闲聊、不空转；\n"
)


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

PA_COMPANION_HEAD = (
    "你是老板的私人 PA，此刻在「陪伴」通道。像熟悉的朋友一样自然聊天：\n"
    "1) 先接住对方的话/情绪，再回应；可以自然追问一句；\n"
    "2) 不要提「通道/体检/办事/接口/能力面」，除非用户明确问；\n"
    "3) 不编事实、不承诺未授权的动作；不知道就直说。\n"
)


PA_COMPANION_CLOSE = "自然口语，2-4 句，不要小标题、不要模板式回执。"



def pa_mode_name(mode=None):
    """档之**归一**：唯显式拨杆之值 ⇒ `work` ∨ `companion`（⛔ 推断）。"""
    m = str(mode or "work").strip().lower()
    return "companion" if m in ("companion", "陪伴", "peiban", "chat") else "work"


def pa_system_for(mode=None):
    """按**显式 mode** 组装系统提示（PM 043 §二.1 · 单源）。

    ⭐ pm_1802 §一.2／§一.3：**通道节**（`PA_CHANNEL_CLAUSE`）**逐档皆附** ——
      「只商量 · 不出手」＋「能力面 ⟷ 本通道」分书 ＋ 禁辞表 ＋ 可执行之去处。
    """
    _m = pa_mode_name(mode)
    if _m == "companion":
        return PA_COMPANION_HEAD + PA_SYSTEM_TAIL + PA_COMPANION_CLOSE
    return (PA_SYSTEM_HEAD + PA_MODE_CLAUSE[_m]
            + PA_SYSTEM_TAIL + PA_CHANNEL_CLAUSE + PA_SYSTEM_CLOSE)


PA_SYSTEM = pa_system_for("work")   # 兼容既有引用（`system_prompt or PA_SYSTEM`）· ⛔ 破


def capability_brief():
    u"""**门**（一处定形）：取当前能力面清单 —— 未挂载过 ⇒ 以**临时 app** 现生一次。

    ⚠ 由：`llm_brain()` 可于**任何 app 之外**被构造（单测直调）⇒ 全局尚空；
      临时 app 与真 app 走**同一套蓝图** ⇒ 清单同源（⛔ 二套读者）。
    """
    # ⚠ ②v1 拆件后：该值之**唯一家**在 `pa_routes_common`（`register_pa_routes` 处 `global` 写）。
    #   旧静态 import ⇒ 本件持陈值「空串」⇒ 每次都另生临时 app（且回空表）。
    from core.pa import pa_routes_common as _pc
    if not _pc.PA_CAPABILITY_BRIEF:
        try:
            from flask import Flask as _Flask
            register_pa_routes(_Flask("pa_capability_standalone"), brain=None)
        except Exception as _e:
            print("[PA] ⚠ 能力面清单（临时 app 生）未成：%s: %s" % (type(_e).__name__, _e), flush=True)
    return _pc.PA_CAPABILITY_BRIEF


def pa_app():
    u"""**门**（一处定形 · 内读者唯此门）：取当前**真 app** —— 未挂载过 ⇒ 以**临时 app** 现挂一次。

    ⚠ 与 `capability_brief()` 同法：临时 app 与真 app 走**同一套蓝图** ⇒ 视图同源。
    ⚠ ⛔ 自建一套读者（承 pm_1859 §一.4 之防漂 ⇒ 二套必歧）。
    """
    # ⚠ ②v1 拆件后：`_PA_APP` 之**唯一家**在 `pa_routes_common`（同上理）⇒ 露读之家 。
    from core.pa import pa_routes_common as _pc
    if _pc._PA_APP is None:
        try:
            from flask import Flask as _Flask
            register_pa_routes(_Flask("pa_read_standalone"), brain=None)
        except Exception as _e:
            print("[PA] ⚠ 只读面之 app（临时生）未成：%s: %s" % (type(_e).__name__, _e), flush=True)
    return _pc._PA_APP


_LLM_PHASE = {"warmed": False}


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


PA_NO_PROVIDER_TEXT = (u"模型不可用：本机与云端皆未接（本机未装模型 ／ 云端未配密钥）"
                       u"⇒ 请到「模型配置」配密钥，或装本机模型。")


def register(bp):
    """把本簇之路由挂到共享蓝图 `pa_routes`（endpoint 名 ⛔ 变）。"""
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

    @bp.route("/v9/pa/self_intro", methods=["POST"])
    def pa_self_intro():
        u"""能力事实 → 本地模型自然表达（⛔ 走 /v9/pa/ask ／ ⛔ 需云端 key）。"""
        p = request.json or {}
        _facts = {
            "identity": "ClawsJoy PA：老板的私人 PA（本机单例，只有一位主人）",
            "can": ["陪伴", "商量", "积累第二大脑", "分派 Agent", "代理审核"],
            "cannot": ["不编造事实", "不越权执行", "不把内部判据当用户答案"],
            "profile": "未建立（data/profile.json 不存在）",
        }
        try:
            from core.pa.providers import default_route as _dr
            _r, _note = _dr()
            _facts["model"] = {"provider": _r.get("provider"), "model": _r.get("model"), "note": _note}
            _facts["profile"] = "未建立" if not (Path(_data_dir()) / "profile.json").is_file() else "已建立"
        except Exception:
            _facts["model"] = {"provider": "local:ollama", "model": "qwen2.5:7b-instruct-q4_0-gpu"}
        _brief = ""
        try:
            _brief = str(capability_brief() or "")[:3000]
        except Exception:
            pass
        _intro = ""
        try:
            from core.lib.llm_client import LLMClient
            _prompt = ("用 2-3 句自然中文向用户介绍你能做什么。只依据下面事实，不列接口名，"
                       "不提通道/体检/办事，不编造事实，不要小标题。\n\n事实：\n" + _facts["identity"] + "\n"
                       + "能做：" + "、".join(_facts["can"]) + "\n不能做：" + "、".join(_facts["cannot"]) + "\n"
                       + "模型：" + str(_facts.get("model")) + "\n画像：" + str(_facts.get("profile")) + "\n"
                       + ("能力清单（仅参考，不要逐条照抄）：\n" + _brief if _brief else ""))
            _intro = (LLMClient().generate(_prompt, model=(_facts.get("model") or {}).get("model"),
                                           max_tokens=220, timeout=60,
                                           system_prompt="你是 PA 的表达层，不是操作台。自然、简洁、诚实。") or "").strip()
        except Exception as _e:
            _intro = ""
        if not _intro:
            _intro = "我是你的 PA：能陪你商量、帮你积累第二大脑、分派 Agent 办事，并在动手前先请你授权。"
        return ok({"facts": _facts, "intro": _intro, "source": "local:self_intro"})

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
                  if getattr(_pa_brain_of_app(), "_is_pa_brain", False) else _pa_brain_of_app())
        # 就事论事: 把"目标/议题"一起带给对话脑, 不是闲聊
        # ⭐ PM 2026-10-05 22:34 §四⒝-2：**源标透传**（档行外加性键 · ⛔ 改答话体）
        # ⭐⭐ 附件之本机端（pm_1847 §三 ／ pm_1852 §四.3）：`attachments:[id]`（陪伴 ／ 办事**同键同义**）
        #   块由 `core/pa/attach.py` **一处定形**（本处唯接）：唯「文」且**逐件已勾**（`attach_out`）者入体；
        #   图 ／ 档恒 ⛔ 入体（唯本机指路）；**缺省 ⛔ 出机** ⇒ 无 `attachments` 键 ⇒ 空块（⛔ 报错）。
        _att_brief, _att_rep = "", None
        _att_ids = p.get("attachments") or []
        if _att_ids:
            try:
                from core.pa import attach as _AT
                _ab = _AT.model_block(_data_dir(), _att_ids, p.get("attach_out") or [])
                _att_brief = _ab.get("块") or ""
                _att_rep = {"载": _ab.get("载"), "略": _ab.get("略"), "明书": _ab.get("明书"),
                            "出机之律": _ab.get("出机之律")}
            except Exception as _e_att:
                _att_rep = {"载": [], "略": [], "明书": u"附件 ⛔ 入体（读源失败 —— 照实报因）",
                            "因": u"%s: %s" % (type(_e_att).__name__, str(_e_att)[:200])}
        r = pa.handle("dialog_post", {"sid": sid, "text": text, "topic": p.get("topic"), "brain": _brain,
                                      "attach_brief": _att_brief,
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
        _resp = {
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
        if _att_rep is not None:            # ⭐ 附件之本机端（唯加键 · ⛔ 破既有字段）
            _resp["附件"] = _att_rep
        return ok(_resp)

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

    @bp.route("/v9/pa/threads", methods=["GET"])
    def pa_threads_get():
        from core.pa.threads import ThreadStore, ThreadStoreCorrupt
        from core.pa import threads as _TH

        from core.pa import identity as _ID
        try:
            _uid = _uid_identity(request.args.get("user_id"))     # ⭐ 归一
        except _ID.OwnerCorrupt as _oc:
            return _owner_corrupt_json(_oc)
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

    @bp.route("/v9/pa/session_model", methods=["GET", "POST"])
    def pa_session_model():
        u"""会话级模型之仓（P2 ①）。

        ⛔ 前端硬编：本路由 ⇒ 前端取「当前模型」之单源；合法面 ＝ 注册表（`known_models`）。
        POST {user_id, model}：`model` 有值 ⇒ 白名单验 ＋ 落档；`model` 空 ／ null ⇒ **清**（回落默认）。
        """
        from core.pa import providers as _PV

        if request.method == "GET":
            _m, _src = session_model_of(_uid_identity(_uid_safe(request.args.get("user_id"))))
            return ok({"model": _m or "", "model_source": _src,
                       "default": _PV.default_view(),
                       "known_models": list(_PV.known_models()),
                       "model_aliases": _PV.model_aliases()},
                      印=_code_sha16(pa_session_model, _PV))
        body = request.get_json(silent=True) or {}
        _uid = _uid_identity(_uid_safe(body.get("user_id")))     # ⭐ 归一
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

    return bp


register(bp)
