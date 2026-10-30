# -*- coding: utf-8 -*-
"""PA 路由 · ledger_audit 簇（②v1 拆件 · 由 gateway_routes.py 机械切出 · 9 条路由）。

共享面唯 `pa_routes_common`（`bp` 唯彼处建）；本件 ⛔ 复建蓝图。
⭐ 导入即挂：件末 `register(bp)`；endpoint 名仍 `pa_routes.<func>`（⛔ 变）。
"""

import os
from flask import jsonify, request
from core.pa.pa_routes_common import bp, ok, err
from core.pa.pa_routes_common import (
    _code_sha16, _core, _data_dir, _owner_corrupt_json,
    err, ok,
)


def _identity():
    u"""身份之器（**一处出**）—— ⛔ 各路由另写「铸 ／ 认领 ／ 恒用既有」之判。"""
    from core.pa import identity as _ID
    return _ID


def _uid_identity(raw):
    u"""hint（浏览器之 user_id）⇒ **本机 owner 之 id**（归一 · pm_1858 §二.2）。

    · 客户端标签（ web_* ）⇒ 归一：owner 既立 ⇒ **恒返它**（⛔ 由 hint 定归属）；首见 ⇒ 认领（其件非空）∘ 铸；
    · 余者（ u1 式兼容之值 ／ 空）⇒ **直通**（本轮兼容 · 承 pm_1858 §四.3 旧齿之保）。
    ⚠ owner.json **存在但不可用** ⇒ **抛 identity.OwnerCorrupt** ⇒ 调用方 409（⛔ 回落空身份续跑）。
    """
    return str(_identity().resolve(_data_dir(), hint=str(raw or "").strip()))


def register(bp):
    """把本簇之路由挂到共享蓝图 `pa_routes`（endpoint 名 ⛔ 变）。"""
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
        from core.pa import identity as _ID
        try:
            uid = _uid_identity(uid)          # ⭐ 归一（pm_1858 §二.2）：⛔ 由 hint 定归属
        except _ID.OwnerCorrupt as _oc:
            return _owner_corrupt_json(_oc)
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
        from core.pa import identity as _ID
        try:
            uid = _uid_identity(uid)          # ⭐ 归一（与 POST 同规）：⛔ 读面之径 ≠ 写面之径
        except _ID.OwnerCorrupt as _oc:
            return _owner_corrupt_json(_oc)
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

    return bp


register(bp)
