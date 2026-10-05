# -*- coding: utf-8 -*-
u"""recipe —— 序②：开 `POST /v9/pa/steer` 面（core/pa/gateway_routes.py · 纯插入 ＋ 路由清单一行）。

字面之据：PM 1235 §三（令开面 ＋ 定「载荷 ／ 回执之字段名与形」）／ PM 1178 §四 ／ CW 1231 §三（丙-3 候 TD）。
病：通道已在 core/gateway/shared_state.py（add_steer ／ drain_steer · 消费性）· 缺者唯 HTTP 面。
形：唯插入（numstat 之删须 0）＋ 路由清单一行；⛔ 动判据 ／ 退码 ／ `_core` ／ 他路 ／ `web/**`。
⛔ 通用之器在 ../safe_edit.py；本件唯「本批之字面」。

⭐ 补（叠改 · 一改一底 · 承 PM 1253 之裁）：⒈ **裁一** —— 信封 ⭐ `success` ⇒ `ok`（**壳从蓝图 · 键从族**）
  ⇒ ⛔ 动「缺参之键集」（`error` ／ `missing` ／ `kind` ／ `route` 一字 ⛔ 动）⒉ **裁二** —— `_STEER_KINDS`
  ⭐ 收为 `{改令}`（「接管」＝ 待立项 · 须先定义）＋ 其 `400` 附其由（⛔ 唯 `allowed`）⒊ 其器之 docstring
  同改（**辞须与机制合** —— ⛔ 留旧壳之述）。
用法：python -X utf8 -B <本件> <二|补|all> [--apply]   （⛔ 无 --apply ⇒ 只演）
      python -X utf8 -B <本件> --verify               （由底回放 ／ 比对记录之「出」）
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import safe_edit as S

# ⭐ 插入之块（逐行 · ⛔ 逐字拼装）—— 落点 ＝ 锚行 `@bp.route("/v9/pa/dispatch/history")` 之前
#   （块末空行 ＝ 与既有「路与路之间留空行」一致）
_STEER_BLOCK = [
    u'    # ---- 序②（2026-10-05 · PM 1235 §三 令）：steer 通道之 HTTP 面（面先钮后 ⇒ 面落 CW 方可去钮之 disabled）----',
    u'    #   通道已在 core/gateway/shared_state.py（add_steer ／ drain_steer · 消费性）⇒ 本面唯「入队」。',
    u'    #   载荷 ／ 回执之字段名与形 ＝ 本 docstring（CW 候此 · 承 PM 1178 §四）。',
    u'    _STEER_MAX_TEXT = 500           # ＝ shared_state.add_steer 之硬截（str(text)[:500]）⇒ 面先拦 · ⛔ 静默截断',
    u'    _STEER_KINDS = ("改令", "接管")  # 前端两钮（tasks.js 之 paIntervene）之意图 ⇒ 回执须载「所按何钮」',
    u'',
    u'    def _steer_missing(_key):',
    u'        u"""缺参 400：形逐字承 routes/session.py 之 _missing（PM T2-刀8 §三 之 canonical）⇒ 同一键 ⛔ 两套码。"""',
    u'        _rule = request.url_rule',
    u'        _rt = (_rule.rule if _rule is not None else "?").lstrip("/")',
    u'        return jsonify({"success": False, "error": u"%s: 缺 %s" % (_rt, _key),',
    u'                        "missing": [_key], "kind": "missing_param", "route": _rt}), 400',
    u'',
    u'    @bp.route("/v9/pa/steer", methods=["POST"])',
    u'    def pa_steer():',
    u'        u"""POST /v9/pa/steer —— 把一条「下一步指导」入 steer 通道（**消费性**：每轮 drain 即清）。',
    u'',
    u'        载荷（JSON body）：`session_id`（必）／`text`（必 · ≤500 字）／`kind`（默「改令」· ∈{改令,接管}）',
    u'          ／`user_id`（选 · 唯留痕）／`topic`（选 · 唯留痕）⇒ 缺参 400（形 ＝ routes/session.py 之 _missing）。',
    u'        回执（200）：`success` ＋ `queued` ＋ 通道之读（`drain_semantics` ／ `inject_point`）',
    u'          ＋ 四键同形（`at` ／ `刻之性` ／ `面之径逐字` ／ `印`）。',
    u'        ⚠ ⛔ 报 `queued_count`：通道唯 `drain_steer`（取走即清）· **无 peek** ⇒ 得数必先消费（假报「已清」）。',
    u'        ⚠ 界：`add_steer(session_id, …)` 之键**唯 `session_id`**（⛔ 含 `user_id`）⇒ 同 sid 异用户 ⛔ 隔离（照实载界）。',
    u'        """',
    u'        from core.gateway import shared_state as _SS',
    u'',
    u'        data = request.get_json(silent=True) or {}',
    u'        sid = str(data.get("session_id") or request.args.get("session_id") or "").strip()',
    u'        if not sid:',
    u'            return _steer_missing("session_id")',
    u'        _raw = data.get("text")',
    u'        text = "" if _raw is None else str(_raw)',
    u'        if not text.strip():',
    u'            return _steer_missing("text")',
    u'        if len(text) > _STEER_MAX_TEXT:',
    u'            return jsonify({"success": False,',
    u'                            "error": u"v9/pa/steer: text 超限（%d ＞ %d 字）" % (len(text), _STEER_MAX_TEXT),',
    u'                            "allowed_max": _STEER_MAX_TEXT, "text_len": len(text),',
    u'                            "kind": "over_limit", "route": "v9/pa/steer"}), 400',
    u'        kind = str(data.get("kind") or "").strip() or "改令"',
    u'        if kind not in _STEER_KINDS:',
    u'            return jsonify({"success": False, "error": u"v9/pa/steer: kind 未知：%s" % kind[:20],',
    u'                            "allowed": list(_STEER_KINDS),',
    u'                            "kind": "bad_value", "route": "v9/pa/steer"}), 400',
    u'        _SS.add_steer(sid, text)',
    u'        print(u"[STEER] POST /v9/pa/steer session=%s kind=%s len=%d" % (sid, kind, len(text)))',
    u'        return jsonify({',
    u'            "success": True, "route": "v9/pa/steer", "channel": "steer", "queued": True,',
    u'            "session_id": sid, "text": text, "text_len": len(text), "max_text": _STEER_MAX_TEXT,',
    u'            "kind": kind, "user_id": (str(data.get("user_id") or "") or None),',
    u'            "topic": (str(data.get("topic") or "") or None),',
    u'            "drain_semantics": u"消费性：drain 即清空（每轮起点消费 ⇒ 追加为 user 消息 · ⛔ 重放）",',
    u'            "inject_point": u"下一轮 LLM 调用前（core/gateway/v9_bridge/round_start.py 每轮 drain_steer）",',
    u'            "at": time.strftime("%Y-%m-%d %H:%M:%S"),',
    u'            "刻之性": u"写时（入队之实 · ⛔ 读盘）",',
    u'            "面之径逐字": str(getattr(_SS, "__file__", "") or ""),',
    u'            "印": _code_sha16(pa_steer, _SS),',
    u'        })',
    u'',
]

二 = [(u"core/pa/gateway_routes.py · 序②（开 POST /v9/pa/steer 面 ＋ 路由清单一行）", "core/pa/gateway_routes.py", [
    ("lines", u'    @bp.route("/v9/pa/dispatch/history"',
     _STEER_BLOCK + [u'    @bp.route("/v9/pa/dispatch/history", methods=["GET"])']),
    ("lines", u'  GET  /v9/pa/archive/<id>',
     [u'  GET  /v9/pa/archive/<id>     按 id 取归档正文(查不到 404, 不拿空对象冒充)',
      u'  POST /v9/pa/steer            steer 通道入队(下一步指导 · 消费性: 每轮 drain 即清; 缺参 400)']),
])]

补 = [(u"core/pa/gateway_routes.py · 序②之补正（PM 1253 裁一 ／ 裁二）", "core/pa/gateway_routes.py", [
    ("sub", u'        u"""缺参 400：形逐字承 routes/session.py 之 _missing（PM T2-刀8 §三 之 canonical）⇒ 同一键 ⛔ 两套码。"""',
            u'        u"""缺参 400：**壳从蓝图**（`ok`）＋ **键从族**（`missing` ／ `kind` ／ `route` ＝ `session` 族之 canonical）⇒ 承 PM 1253 §二 裁（⛔ 两族混壳）。"""'),
    ("sub", u'    _STEER_KINDS = ("改令", "接管")  # 前端两钮（tasks.js 之 paIntervene）之意图 ⇒ 回执须载「所按何钮」',
            u'    _STEER_KINDS = ("改令",)          # ⭐ PM 1253 §三 裁：唯「改令」（「接管」＝ 待立项 · 须先定义 · 承 PM 1230 §五）'),
    ("sub", u'／`kind`（默「改令」· ∈{改令,接管}）',
            u'／`kind`（默「改令」· ⭐ 唯 `{改令}`：接管 ＝ 待立项 · ⛔ 送）'),
    ("sub", u'回执（200）：`success` ＋ `queued`',
            u'回执（200）：`ok` ＋ `queued`'),
    ("sub", u'          ＋ 四键同形（`at` ／ `刻之性` ／ `面之径逐字` ／ `印`）。\n        ⚠ ⛔ 报 `queued_count`',
            u'          ＋ 四键同形（`at` ／ `刻之性` ／ `面之径逐字` ／ `印`）。\n        ⚠ 形（PM 1253 §二 裁）：**壳从蓝图**（`ok` ／ `err` · 本蓝图 idiom）· **键从族**（`missing` ／ `kind` ／ `route` ＝ `session` 族之 canonical · ⛔ 两族混壳）。\n        ⚠ ⛔ 报 `queued_count`'),
    ("sub", u'        return jsonify({"success": False, "error": u"%s: 缺 %s" % (_rt, _key),',
            u'        return jsonify({"ok": False, "error": u"%s: 缺 %s" % (_rt, _key),'),
    ("sub", u'            return jsonify({"success": False,\n                            "error": u"v9/pa/steer: text 超限',
            u'            return jsonify({"ok": False,\n                            "error": u"v9/pa/steer: text 超限'),
    ("sub", u'            return jsonify({"success": False, "error": u"v9/pa/steer: kind 未知：%s" % kind[:20],\n                            "allowed": list(_STEER_KINDS),\n                            "kind": "bad_value", "route": "v9/pa/steer"}), 400',
            u'            # ⭐ PM 1253 §三：⛔ 唯 `allowed` —— 「接管」须附其由（＝ 待立项 · 须先定义）\n            _why = u"（接管 ＝ 待立项（须先定义）· 承 PM 1230 §五）" if kind == "接管" else u""\n            return jsonify({"ok": False, "error": u"v9/pa/steer: kind 未知：%s%s" % (kind[:20], _why),\n                            "allowed": list(_STEER_KINDS),\n                            "kind": "bad_value", "route": "v9/pa/steer"}), 400'),
    ("sub", u'            "success": True, "route": "v9/pa/steer", "channel": "steer", "queued": True,',
            u'            "ok": True, "route": "v9/pa/steer", "channel": "steer", "queued": True,'),
])]

EDITS = {"二": 二, "补": 补}
ORDER = ["二", "补"]

# 何批之改 ⇒ 用何器之印（底 ⇒ 出 · 供 --verify 由底回放）
BASES = [
    ("二", 0, "core/pa/gateway_routes.py", "4f2b0a4e661157d0", "98a350b4a20b055b"),
    ("补", 0, "core/pa/gateway_routes.py", "98a350b4a20b055b", "6b8c21c9b09fbfaf"),
]

if __name__ == "__main__":
    raise SystemExit(S.cli(EDITS, ORDER, bases=BASES, title=u"序② · 开 POST /v9/pa/steer 面 ＋ 补正（一改一底）"))
