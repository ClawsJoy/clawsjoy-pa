# -*- coding: utf-8 -*-
u"""pa_read 工具（pm_1859 §一.4 之**端**）：PA 之**只读面** ⇒ **可调之工具**。

由（一手 · pm_1859 §一.3⒝）：PA 之诸面（`sys/snapshot` ／ `local_client/status`
  ／ `ask` ／ `ledger` 读 ／ `today`）此前**唯**系统提示里之**一段话** ⇒ 模型**只看得见
  一张「能力单」**而 ⛔ 能调 ⇒ 办事轴遂「只说不做」（老板五轮实录 · pm_1859 §〇）。
治：本工具把**白名单内之只读面**接成真工具 —— ⭐ **由路由表生**（承 pm_1802 §一.1
  之防漂）：`READ_FACES` 逐条 ＝ （名 · 路 · 方法），执行时按**路**在**真 app** 之
  `url_map` 里解析 ⇒ 调**该路由自己的视图** ⇒ ⛔ 新造一套业务逻辑（⛔ 二套读者）。

⚠ **唯读**：`READ_FACES` 即界（⛔ 写类面 · 候 pm_1859 §二 之授权之形）；
  白名单**外**之路由 ⛔ 可即（本工具按**路**解析 ⇒ 表外之路由**无从到达**）。
⚠ 面里之行路（⛔ 主路）：面以 `_loopback` 判本机 ⇒ 本工具**以本机身份**在进程内调
  （`environ_base` 明书 `127.0.0.1` · 承 §二「唯本机」之律）。
"""
from core.tools.base import ToolPlugin

#: 只读面白名单 —— （名, 路, 方法, 人话）。
#   ⭐ 唯此表定「哪些面可调」；齿 `test_pa_agent_chat_1859.py` 逐条核其**在真路由表内**（防漂）。
READ_FACES = (
    ("sys.snapshot", "/v9/pa/sys/snapshot", "GET", u"本机体检七面合体（只读 · 缺省取缓存）"),
    ("sys.panel", "/v9/pa/sys/<panel>", "GET", u"本机体检单面（disk ／ disk_c ／ windows ／ startup ／ perf ／ net ／ guard）"),
    ("local_client.status", "/v9/pa/local_client/status", "GET", u"本机浏览器客户端之连接态"),
    ("ask", "/v9/pa/ask", "POST", u"知识库检索（有据才答 · 无据拒答 · ⛔ 编结论）"),
    ("ledger", "/v9/pa/ledger", "GET", u"账本（只读）"),
    ("today", "/v9/pa/today", "GET", u"今日四行合体（只读）"),
)

_FACE_BY = {_n: (_p, _m, _h) for (_n, _p, _m, _h) in READ_FACES}
_NAMES = [_n for (_n, _p, _m, _h) in READ_FACES]


def faces_known():
    u"""白名单之名（**一处出** —— 齿与 schema 同源）。"""
    return list(_NAMES)


def _app():
    u"""真 app（经 `gateway_routes.pa_app()` 之**门**取 · ⛔ 自建 · 一处定形）。

    ⚠ 由（一手 · 2026-10-08）：直取 `_PA_APP` 而挂载处**未钉** ⇒ 恒 None ⇒ 六面皆拒
      （齿 `test_pa_agent_chat_1859.py::test_today_really_calls_the_face` 咬）⇒ 改走**门**
      （门含「未挂载 ⇒ 临时 app 现挂」之兜底 · 与 `capability_brief()` 同法）。
    """
    try:
        from core.pa import gateway_routes as _GR
    except Exception:
        return None
    _door = getattr(_GR, "pa_app", None)
    if callable(_door):
        return _door()
    return getattr(_GR, "_PA_APP", None)


def call_face(action, *, panel=None, question=None, fresh=None, user_id="", session_id=""):
    u"""调一面（**唯读** · 一处定形）—— 返回 `{"ok","code","route","method","data"}`。

    ⚠ 表外之名 ⇒ `ok=False` ＋ 白名单（⛔ 静默兜底 · 承「空 ⛔ 混 缺」）。
    """
    face = _FACE_BY.get(str(action or "").strip())
    if face is None:
        return {"ok": False, "code": 0, "action": action, "error": u"未知 action（白名单：%s）"
                % u" ／ ".join(_NAMES), "allowed": list(_NAMES)}
    _rule, _method, _human = face
    app = _app()
    if app is None:
        return {"ok": False, "code": 0, "action": action,
                "error": u"PA 路由未挂载 ⇒ 无从调面（⛔ 以「没数据」充「没接口」）"}
    from urllib.parse import urlencode
    path = _rule
    query = {}
    body = None
    if "<panel>" in path:
        _pid = str(panel or "").strip()
        if not _pid:
            return {"ok": False, "code": 0, "action": action, "error": u"sys.panel 需要 panel"}
        path = path.replace("<panel>", _pid)
    if _method == "GET" and action in ("sys.snapshot", "sys.panel"):
        if str(fresh or "").strip().lower() in ("1", "true", "yes", "fresh"):
            query["fresh"] = "1"
    if action == "local_client.status":
        query["user_id"] = str(user_id or "")
    if action == "today":
        query["user_id"] = str(user_id or "")
        query["session_id"] = str(session_id or "")
    if action == "ask":
        _q = str(question or "").strip()
        if not _q:
            return {"ok": False, "code": 0, "action": action, "error": u"ask 需要 question（⛔ 空问）"}
        body = {"question": _q, "user_id": str(user_id or ""), "session_id": str(session_id or "")}
    qs = urlencode({k: v for k, v in query.items() if v not in (None, "")})
    full = path + (("?" + qs) if qs else "")
    try:
        with app.test_request_context(full, method=_method, json=body,
                                      environ_base={"REMOTE_ADDR": "127.0.0.1"}):
            _ep, _va = app.url_map.bind("127.0.0.1").match(path, method=_method)
            rv = app.view_functions[_ep](**_va)
    except Exception as _e:
        return {"ok": False, "code": 0, "action": action, "route": _rule, "method": _method,
                "error": u"调面 ⛔ 成：%s: %s" % (type(_e).__name__, str(_e)[:200])}
    if isinstance(rv, tuple):
        _obj = rv[0]
        _code = int(rv[1]) if len(rv) > 1 and isinstance(rv[1], int) else 200
    else:
        _obj, _code = rv, 200
    try:
        data = _obj.get_json() if hasattr(_obj, "get_json") else _obj
    except Exception:
        data = None
    _ok = bool(_code == 200 and isinstance(data, dict) and data.get("ok") is not False)
    out = {"ok": _ok, "code": _code, "action": action, "route": _rule, "method": _method,
           "data": data}
    if not _ok:
        out["error"] = (data or {}).get("error") if isinstance(data, dict) else u"面 ⛔ 成（HTTP %s）" % _code
    return out


def _schema():
    _lines = u"；".join(u"%s ＝ %s（%s）" % (_n, _p, _h) for (_n, _p, _m, _h) in READ_FACES)
    return {
        "type": "function",
        "function": {
            "name": "pa_read",
            "strict": True,
            "description": (
                u"调本 PA 的**只读面**（真调 · 真返回 · 唯本机）：%s。"
                u"⚠ 这是你**真能调**的东西 —— 被问「能不能查 ／ 能不能检查本机」时，"
                u"**直接调**本工具，并把**真返回**讲给老板（⛔ 只说「我有这些面」；"
                u"⛔ 说「\u5df2\u53d7\u7406 ／ \u5df2\u5b89\u6392」—— 那是没做而似做）。"
                % _lines),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "action": {"type": "string", "enum": list(_NAMES),
                               "description": u"要调的只读面（白名单）"},
                    "panel": {"type": "string",
                              "description": u"sys.panel 之面板名（其余面 ⛔ 用）"},
                    "question": {"type": "string",
                                 "description": u"ask 之问题（其余面 ⛔ 用）"},
                    "fresh": {"type": "string",
                              "description": u"sys.* 是否真扫（1 ＝ 真扫 · 缺省取缓存）"},
                },
                "required": ["action"],
            },
        },
    }


class PaReadPlugin(ToolPlugin):
    u"""PA 只读面之**唯一口**（pm_1859 §一.4）。"""

    name = "pa_read"
    schema = _schema()
    quota = 1

    def execute(self, args, ctx):
        _uid = str(getattr(ctx, "user_id", "") or "")
        _sid = str(getattr(ctx, "session_id", "") or "")
        out = call_face(args.get("action"), panel=args.get("panel"),
                        question=args.get("question"), fresh=args.get("fresh"),
                        user_id=_uid, session_id=_sid)
        _rep = {"success": bool(out.get("ok")), "action": out.get("action"),
                "route": out.get("route"), "method": out.get("method"),
                "http": out.get("code"), "唯读": True,
                "result": out.get("data") if out.get("ok") else None}
        if not out.get("ok"):
            _rep["error"] = out.get("error") or u"面 ⛔ 成"
            if out.get("allowed"):
                _rep["allowed"] = out["allowed"]
        return _rep
