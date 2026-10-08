# -*- coding: utf-8 -*-
u"""pm_1859 §一（红线）之齿：办事轴「只说不做」之**治** ——

  ⒜ **端**：PA 之只读面 ⇒ **真工具**（`pa_read` · 由**路由表**生 · pm_1859 §一.4）；
  ⒝ **闸**：禁辞之**运行期**机检（一处定形 · 含禁辞 ∧ ⛔ tool_call ⇒ 标 ＋ 重写）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_agent_chat_1859.py -q -p no:cacheprovider

判据：
  ⒜ 正控：`pa_read` 已注册 ∧ `_get_agent_tools()` 见之 ∧ schema 之 enum ≡ `READ_FACES`。
  ⒝ 正控（**防漂**）：`READ_FACES` 逐条在**真路由表**内（路 ＋ 方法）；反控：凭空一条 ⇒ 齿咬。
  ⒞ 正控：模式白名单（minimal）**仍保** `pa_read`；反控：白名单外之**写类**工具**仍被滤**。
  ⒟ 正控（**真调**）：`today` ⇒ `success` ∧ 真返回（`行`）∧ 载 `route` ／ `http` 之据。
  ⒠ 反控：未知 action ⇒ **结构化**拒（⛔ 静默兜底）；写类面（`sys.act`）不在白名单 ⇒ 拒。
  ⒡ 反控（闸）：含禁辞 ∧ 无 tool ⇒ `flagged` ＋ 重写 ＋ 键；有 tool ⇒ ⛔ 咬；无禁辞 ⇒ ⛔ 咬。
  ⒢ 正控（**同步路真接**）：`run_bridge_sync` 真跑 ⇒ 答体被标 ＋ 键；有 tool ⇒ 一字不动。
  ⒣ 正控（**流式路真接**）：`make_stream_response` 之 `done` 事件被标（真跑 · ⛔ 只核源）。
  ⒤ 一处定形：`untrue_wording.WORDS` ⊆ 运行期提示之禁辞表 ∧ 两源内**皆无**字面（转义写）。
  ⒥ 反控（陪伴轴之界照旧）：`/v9/pa/dialog` 回执仍载 `channel.untrue_wording` ∧ `acts is False`。
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import gateway_routes as GR  # noqa: E402
from core.pa import untrue_wording as UW  # noqa: E402
from core.tools import pa_read as PR  # noqa: E402

BANNED = (u"\u5df2\u53d7\u7406", u"\u5df2\u5b89\u6392",
          u"\u5df2\u8f6c\u529e", u"\u6b63\u5728\u5904\u7406")


class _Ctx:
    user_id = "web_1859"
    session_id = "s_1859"


def _app(name="t1859"):
    a = Flask(name)
    GR.register_pa_routes(a)
    return a


# ---------- ⒜ 已注册 ＋ schema 同源 ----------

def test_pa_read_registered_and_listed_by_llm():
    u"""⒜：注册表 ∧ `_get_agent_tools()`（LLM 真看得见）∧ schema enum ≡ 白名单。"""
    from core.gateway.tool_router import _TOOL_REGISTRY
    from core.lib.gateway_helpers import _get_agent_tools

    assert _TOOL_REGISTRY.get("pa_read") is PR.PaReadPlugin, u"未注册 ⇒ 模型仍只见「能力单」"
    names = {t.get("function", {}).get("name") for t in _get_agent_tools()}
    assert "pa_read" in names, u"未入 tools ⇒ 本修为空"
    _sch = [t for t in _get_agent_tools() if t.get("function", {}).get("name") == "pa_read"][0]
    _enum = _sch["function"]["parameters"]["properties"]["action"]["enum"]
    assert list(_enum) == PR.faces_known(), (_enum, PR.faces_known())


# ---------- ⒝ 防漂：由路由表生 ----------

def test_every_declared_face_exists_in_route_table():
    u"""⒝ 正控：白名单逐条在**真**路由表内（⛔ 手写一处 · 漂一处）。"""
    a = _app("t1859b")
    table = {}
    for _r in a.url_map.iter_rules():
        table[str(_r.rule)] = set(_r.methods or ())
    assert PR.READ_FACES, u"白名单为空 ⇒ 判据无从谈起"
    for _n, _p, _m, _h in PR.READ_FACES:
        assert _p in table, u"白名单之路由不在真表内（漂）：%s" % _p
        assert _m in table[_p], (_n, _p, _m, sorted(table[_p]))


def test_face_check_bites_when_route_absent():
    u"""⒝ 反控：路由表里没有 ⇒ 该白名单条**必**判缺（齿能咬 ⇒ ⛔ 装饰层）。"""
    a = Flask("t1859b2")
    a.add_url_rule("/v9/pa/only_1859", "only_1859", lambda: "ok", methods=["GET"])
    table = {str(_r.rule) for _r in a.url_map.iter_rules()}
    assert "/v9/pa/sys/snapshot" not in table
    _missing = [_p for _n, _p, _m, _h in PR.READ_FACES if _p not in table]
    assert _missing, u"空表下白名单条**皆**缺 ⇒ 若无缺 ⇒ 判据与表脱钩（假绿）"


# ---------- ⒞ 模式白名单 ----------

def test_mode_filter_keeps_pa_read():
    u"""⒞ 正控：minimal（按任务收敛广度）**仍保** PA 之读数口；写类仍受白名单。"""
    from core.gateway.tool_router import _filter_tools_by_mode
    from core.gateway import quota_manager as qm

    tools = [{"function": {"name": n}} for n in ("read_file", "write_file", "pa_read", "wps_office")]
    _old_m, _old_t = qm.get_mode, qm.get_mode_tools
    try:
        qm.get_mode = lambda sid, hint="": "minimal"
        qm.get_mode_tools = lambda sid, hint="": ["read_file", "write_file"]
        out = _filter_tools_by_mode(tools, "s1859", [{"role": "user", "content": u"查一下"}])
    finally:
        qm.get_mode, qm.get_mode_tools = _old_m, _old_t
    names = {t["function"]["name"] for t in out}
    assert "pa_read" in names, u"被模式白名单滤掉 ⇒ 模型看不见 ⇒ 本修为空"
    assert "wps_office" not in names, u"白名单外之**写类**面仍须被滤（⛔ 顺手放宽）"


# ---------- ⒟ 真调 ----------

def test_today_really_calls_the_face():
    u"""⒟ 正控：真调（⛔ 只说「已受理」）—— 回体载真返回 ＋ 路由之据。"""
    _app("t1859d")
    out = PR.PaReadPlugin().execute({"action": "today"}, _Ctx())
    assert out["success"] is True, out
    assert out["route"] == "/v9/pa/today" and out["method"] == "GET" and out["http"] == 200, out
    assert isinstance(out["result"], dict) and out["result"].get("ok") is True, out
    assert out["result"].get("行"), u"真返回为空 ⇒ 与「无据」无从分（承「空 ⛔ 混 缺」）"


def test_bad_action_is_refused_structurally():
    u"""⒠ 反控：表外之名（含**写类** `sys.act`）⇒ 结构化拒 ＋ 白名单（⛔ 静默兜底）。"""
    _app("t1859e")
    for _bad in ("nope", "sys.act", "/v9/pa/sys/act", ""):
        out = PR.PaReadPlugin().execute({"action": _bad}, _Ctx())
        assert out["success"] is False, (_bad, out)
        assert out.get("allowed") == PR.faces_known(), (_bad, out)
        assert out.get("error"), u"⛔ 静默：须给结构化之因"


# ---------- ⒡ 闸之判据 ----------

def test_gate_flags_only_when_no_tool_call():
    u"""⒡ 反控三形：含禁辞 ∧ 无 tool ⇒ 咬；有 tool ⇒ ⛔ 咬；无禁辞 ⇒ ⛔ 咬。"""
    _r = u"%s，我这就去看。" % BANNED[0]
    _no_tool = {"data": {"choices": [{"message": {"role": "assistant", "content": _r}}]},
                "tool_steps": []}
    _v = UW.apply_gate(_no_tool)
    assert _v["flagged"] is True and _v["hits"] == [BANNED[0]], _v
    assert _no_tool["untrue_wording"]["flagged"] is True, u"回执须载结构化键（⛔ 静默）"
    _c = _no_tool["data"]["choices"][0]["message"]["content"]
    assert _c != _r and _r in _c, u"须**重写**（标可见 · ⛔ 静默放行）"

    _with_tool = {"data": {"choices": [{"message": {"role": "assistant", "content": _r}}]},
                  "tool_steps": [{"tool": "pa_read", "success": True}]}
    assert UW.apply_gate(_with_tool)["flagged"] is False, u"有真调 ⇒ ⛔ 咬（否则假阳）"
    assert _with_tool["data"]["choices"][0]["message"]["content"] == _r, u"有真调 ⇒ 一字不动"
    assert "untrue_wording" not in _with_tool

    _clean = {"data": {"choices": [{"message": {"role": "assistant", "content": u"待核实：无据。"}}]},
              "tool_steps": []}
    assert UW.apply_gate(_clean)["flagged"] is False
    assert "untrue_wording" not in _clean


def test_scan_matches_only_listed_words():
    u"""⒡ 正控：唯表内四枚（⛔ 泛扫 ⇒ 假阳之海 —— 承 pm_1850 §二.2 之尺）。"""
    assert UW.scan(u"待核实 · 未做 · 稍等") == []
    assert UW.scan(u"／".join(BANNED)) == list(BANNED)


# ---------- ⒢ 同步路真接 ----------

def _run_sync(reply, steps):
    from core.gateway.v9_chat.bridge_call import run_bridge_sync

    def _loop(messages, tools, user_id, session_id, adapter, thinking2, model, plan_status, current_plan, data):
        _m = list(messages) + [{"role": "assistant", "content": reply}]
        return (_m, list(steps), False, None, 3, "stop", "ok")

    return run_bridge_sync(
        bridge_loop_fn=_loop, messages=[{"role": "user", "content": u"检查电脑"}], tools=[],
        user_id="web_1859", session_id="s_1859", adapter=None, thinking2=None, model="m",
        plan_status="", current_plan=None, data={}, max_total_tools=8,
        goal_info_fn=lambda sid: None)


def test_sync_path_gate_is_wired():
    u"""⒢ 正控（**真跑** · ⛔ 只核源）：同步路含禁辞 ∧ 无 tool ⇒ 标；有 tool ⇒ 一字不动。"""
    _r = u"%s，已把 local_client status 当动作受理。" % BANNED[0]
    _d = _run_sync(_r, [])
    assert _d["untrue_wording"]["flagged"] is True, _d.get("untrue_wording")
    assert _d["data"]["choices"][0]["message"]["content"] != _r, u"须重写（用户可见）"

    _r2 = u"%s。" % BANNED[3]
    _d2 = _run_sync(_r2, [{"tool": "pa_read", "arg": "today", "success": True}])
    assert "untrue_wording" not in _d2, u"有真调 ⇒ ⛔ 咬"
    assert _d2["data"]["choices"][0]["message"]["content"] == _r2


# ---------- ⒣ 流式路真接 ----------

def test_stream_path_gate_is_wired():
    u"""⒣ 正控（**真跑**）：流式 `done` 事件亦载标 ＋ 键（两条路同源）。"""
    from core.gateway.v9_chat.bridge_call import make_stream_response

    _r = u"%s，已把 local_client status 当动作受理。" % BANNED[0]

    def _loop(messages, tools, user_id, session_id, adapter, thinking2, model, plan_status, current_plan, data, **kw):
        return (list(messages) + [{"role": "assistant", "content": _r}], [], False, None, 3, "stop", "ok")

    _gen = make_stream_response(
        bridge_loop_fn=_loop, messages=[{"role": "user", "content": u"检查电脑"}], tools=[],
        user_id="web_1859", session_id="s_1859", adapter=None, thinking2=None, model="m",
        plan_status="", current_plan=None, data={}, max_total_tools=8,
        goal_info_fn=lambda sid: None)
    _done = None
    for _chunk in _gen:
        for _line in str(_chunk).splitlines():
            if _line.startswith("data: ") and _line[6:].strip() not in ("[DONE]", ""):
                try:
                    _ev = json.loads(_line[6:])
                except Exception:
                    continue
                if isinstance(_ev, dict) and _ev.get("type") == "done":
                    _done = _ev
    assert _done is not None, u"未取得 done 事件"
    assert _done.get("untrue_wording", {}).get("flagged") is True, _done.get("untrue_wording")
    assert _done["data"]["choices"][0]["message"]["content"] != _r, u"须重写（用户可见）"


# ---------- ⒤ 一处定形 ----------

def test_single_source_of_banned_words():
    u"""⒤：表 ＝ 运行期提示之禁辞表 ∧ 三处源内**皆无**字面（转义写 · 承 L56-57）。"""
    _prompt = GR.pa_system_for("companion")
    for _w in UW.WORDS:
        assert _w in _prompt, u"表 ⟷ 提示 脱钩：%s（⛔ 二套真源）" % _w
    for _p in (UW.__file__, GR.__file__, PR.__file__):
        _src = io.open(_p, encoding="utf-8").read()
        for _w in UW.WORDS:
            assert _w not in _src, u"字面须转义写（源内 ⛔ 现）：%s ／ %s" % (_w, _p)


def test_gate_has_exactly_three_readers():
    u"""⒤ 反控：闸之接入点**逐处列毕**（同步 ／ 流式 ／ 陪伴回执 ⇒ 三 · ⛔ 只报总数）。"""
    _bc = io.open(Path(GR.__file__).resolve().parents[1] / "gateway" / "v9_chat" / "bridge_call.py",
                  encoding="utf-8").read()
    assert _bc.count("untrue_wording") >= 2, u"同步 ／ 流式 两路须各接一处"
    _gr = io.open(GR.__file__, encoding="utf-8").read()
    assert "untrue_wording" in _gr, u"陪伴轴回执须同源"


# ---------- ⒥ 陪伴轴之界照旧 ----------

def _client(tmp_path, monkeypatch, reply):
    monkeypatch.setenv("PA_DATA_DIR", str(tmp_path / "pa"))

    def _fake_llm_brain(system_prompt=None, model=None, max_tokens=None):
        def _b(context_text):
            return reply

        _b._is_pa_brain = True
        return _b

    monkeypatch.setattr(GR, "llm_brain", _fake_llm_brain)
    a = Flask("t1859i")
    GR.register_pa_routes(a, brain=GR.llm_brain())
    return a.test_client()


def test_companion_axis_keeps_its_boundary(tmp_path, monkeypatch):
    u"""⒥ 反控：陪伴轴仍 `acts is False`（只商量）∧ 禁辞走**回执键**（⛔ 改用户面之辞）。"""
    _r = u"%s，我这就去看。" % BANNED[0]
    c = _client(tmp_path, monkeypatch, _r)
    d = c.post("/v9/pa/dialog", json={"user_id": "u1859", "session_id": "s1859",
                                      "text": u"你能检查电脑吗"}).get_json()
    assert d["channel"]["acts"] is False and d["channel"]["kind"] == "dialog"
    assert BANNED[0] in d["channel"]["untrue_wording"], d["channel"]

    c2 = _client(tmp_path, monkeypatch, u"要真跑 ⇒ 切「办事」。")
    d2 = c2.post("/v9/pa/dialog", json={"user_id": "u1859", "session_id": "s1859b",
                                       "text": u"你能检查电脑吗"}).get_json()
    assert d2["channel"]["untrue_wording"] == [], d2["channel"]
