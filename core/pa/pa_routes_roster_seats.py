# -*- coding: utf-8 -*-
"""PA 路由 · roster_seats 簇（②v1 拆件 · 由 gateway_routes.py 机械切出 · 14 条路由）。

共享面唯 `pa_routes_common`（`bp` 唯彼处建）；本件 ⛔ 复建蓝图。
⭐ 导入即挂：件末 `register(bp)`；endpoint 名仍 `pa_routes.<func>`（⛔ 变）。
"""

import logging
from flask import jsonify, request
logger = logging.getLogger(__name__)
from core.pa.pa_routes_common import bp, ok, err
from core.pa.pa_routes_common import (
    _UI_REPO, _code_sha16, _core, _data_dir,
    _loopback, _owner_corrupt_json, err, ok,
    pa_vault_state_code, vault_env_override,
)


def _uid_safe(raw):
    """单段 uid（⛔ 空 ／ ⛔ 路径分隔 ／ ⛔ 穿越）—— 会话档之径。⛔ 得 ⇒ ""。"""
    s = str(raw or "").strip()
    if not s or chr(0) in s or s in (".", "..") or "/" in s or "\\" in s or ":" in s:
        return ""
    return s


PA_FIRST_RUN_VERSION = "2026-10-06.6"   # ⭐ 判成之形变 ⇒ 必 +1（承 PA_UI_FACES_VERSION 之律）


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


def register(bp):
    """把本簇之路由挂到共享蓝图 `pa_routes`（endpoint 名 ⛔ 变）。"""
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

    @bp.route("/v9/pa/whoami", methods=["GET"])
    def pa_whoami():
        u"""本机身份之**唯一读面**：hint（浏览器之标签）⇒ owner id ＋ 人话之 display。

        ⭐ 唯本机（承 pm_1858 §四.1）：远机 ⇒ 403（身份 ⛔ 由远机定）。
        ⭐ 人话（承 §二.3）：display 唯「画像之名 ∘ 本机」⇒ ⛔ 机器号 ／ ⛔ 内部缩写上屏。
        ⚠ owner.json 坏 ⇒ 409（fail-loud · ⛔ 回落空身份 ／ ⛔ 另铸）。
        ⭐ 并报「未认领之旧史」（⛔ 窃 ／ ⛔ 静默 · 承 pm_1858 §三.3）—— 旧史在盘上就得看得见。
        """
        from core.pa import identity as _ID

        if not _loopback(request):
            return err(u"唯本机之请求（身份 ⛔ 由远机定 —— 承 pm_1858 §四.1）", 403)
        _hint = str(request.args.get("user_id") or "").strip()
        if _hint and not _uid_safe(_hint):
            return err(u"user_id 非法（须单段标识 · ⛔ 路径分隔 ／ 穿越）", 400)
        try:
            _doc = _ID.ensure_owner(_data_dir(), hint=_hint)
        except _ID.OwnerCorrupt as _oc:
            return _owner_corrupt_json(_oc)
        _disp, _dsrc = _ID.display_of(_data_dir())
        _out = {"owner_id": str(_doc.get("id") or ""), "source": str(_doc.get("source") or ""),
                "owner_file": _ID.OWNER_FILE, "display": _disp, "display_source": _dsrc,
                u"未认领之旧史": _ID.unclaimed_legacy(_data_dir(), owner_id=_doc.get("id"))}
        if _doc.get("claimed_from"):
            _out["claimed_from"] = str(_doc["claimed_from"])
        return ok(_out)

    @bp.route("/v9/pa/roster/scan", methods=["POST"])
    def pa_roster_scan():
        from core.pa import agent_scan as S

        r = S.scan_and_upsert()
        return ok({"upsert": r["upsert"], "modes": r.get("upsert_modes", {}),
                   "scan_at": r["scan_at"], "scan_version": r["scan_version"]})

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

    @bp.route("/v9/pa/roster/probe", methods=["POST"])
    def pa_roster_probe():
        """`probe` 之**实测刷新**（⛔ 唯此处触实测 ⇒ 落 `card_probes.json`；面只读缓存）。"""
        from core.pa import agent_invoke as _AI

        p = request.get_json(silent=True) or {}
        doc = _AI.refresh_probes(with_api=bool(p.get("with_api") or request.args.get("with_api")))
        doc["印"] = _code_sha16(pa_roster_probe, _AI)
        return ok(doc)

    @bp.route("/v9/pa/projects", methods=["GET"])
    def pa_projects():
        """到点面（只读 · **唯调 codex/_CEO面核.py --due 一处出** · ⛔ 端自算）。

        承 CEO 2221 §四 四条件：⒜ 唯调面核器（一处出）∧ ⛔ 端自算 ⇒ 反控必咬；
        ⒝ 返必载「取数刻 ＋ 口径 ＋ 源」（⛔ 只报值）；⒞ 唯读；⒟ 落毕报面之列之变 ＋ 印 ＋ 刻。
        """
        from core.pa import projects_face as _pfm

        r = _pfm.projects_face()
        if not r.get("ok"):
            return err(r.get("error") or u"面核器采数不入（⛔ 端自算兜底）", 503)
        r["面印"] = _code_sha16(pa_projects, _pfm.projects_face)
        return ok(r)

    @bp.route("/v9/pa/plan", methods=["POST"])
    def pa_plan():
        """派活后 PA 先出「语义步骤计划」(时间轴节点=拍板点), 再执行。"""
        from core.pa.decision import generate_plan

        p = request.json or {}
        task = (p.get("task") or "").strip()
        if not task:
            return err("plan 需要 task")
        return ok(generate_plan(task, mode=p.get("mode") or "work", user_id=p.get("user_id")))

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

    return bp


register(bp)
