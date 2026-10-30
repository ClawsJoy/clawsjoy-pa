# -*- coding: utf-8 -*-
"""PA 路由 · faces_ui 簇（②v1 拆件 · 由 gateway_routes.py 机械切出 · 8 条路由）。

共享面唯 `pa_routes_common`（`bp` 唯彼处建）；本件 ⛔ 复建蓝图。
⭐ 导入即挂：件末 `register(bp)`；endpoint 名仍 `pa_routes.<func>`（⛔ 变）。
"""

import logging
import os
from pathlib import Path
from flask import jsonify, request
from core.lib.paths import org_enabled, vault_root, ws_root
logger = logging.getLogger(__name__)
from core.pa.pa_routes_common import bp, ok, err
from core.pa.pa_routes_common import (
    PA_SELFTEST_MARKS, _UI_REPO, _code_sha16, _core,
    _data_dir, _face_files, _loopback, _rel_under,
    err, ok, pa_faces,
)


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

    ⚠ ⛔ 手列（手列必与实漂）：无应用上下文（如单测直调本函）⇒ **回落本包之源扫**（`pa_routes_*.py` ＋ `gateway_routes.py` · 同器之真源）。
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
        # ⚠ ②v1 拆件后：真源 ≡ **本包**（各簇）。旧只扫本档 ⇒ 簇外之路由全漏（面册一律判「悬」之假红）。
        try:
            import re as _re
            _here = Path(__file__).resolve().parent
            _srcs = [Path(__file__)]
            _srcs += sorted(_here.glob("pa_routes_*.py"))
            _srcs.append(_here / "gateway_routes.py")
            for _p in _srcs:
                try:
                    _txt = _p.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                for _m in _re.finditer(r'"(/v9/pa[^"]*)"', _txt):
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


def pa_src_faces():
    u"""画像**素材面**之表（惰算 · ⛔ 检索面）。"""
    return _src_faces_tables()[0]


def pa_src_faces_gate():
    u"""素材面之门（惰算）。"""
    return _src_faces_tables()[1]


def register(bp):
    """把本簇之路由挂到共享蓝图 `pa_routes`（endpoint 名 ⛔ 变）。"""
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

    @bp.route("/v9/pa/attach", methods=["POST"])
    def pa_attach():
        """附件上传（**唯本机** · `multipart/form-data` · 字段 `files` 可多）。

        ⇒ `{ok, 附件:[{id,名,字节,sha16,类,落点}], 略, 落点, 唯本机, 明书}`；
        ⛔ 出机 —— 本路唯落本机（模型侧另由 `attach_out` 逐件勾 · 见 `POST /v9/pa/dialog`）。
        """
        if not _loopback(request):
            return err("附件唯本机可用（⛔ 远机）", 403)
        from core.pa import attach as _AT
        _fs = list(request.files.getlist("files") or []) or list(request.files.getlist("file") or [])
        if not _fs:
            return err("须载 files（multipart · 一件以上）", 400)
        items = []
        for f in _fs:
            try:
                items.append((f.filename or "", f.stream.read(int(_AT.MAX_FILE_BYTES) + 1)))
            except Exception as e:
                return err("读上传件失败：%s" % type(e).__name__, 400)
        out = _AT.save(_data_dir(), items)
        out["器印"] = _code_sha16(pa_attach, _AT)
        return ok(out)

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

    return bp


register(bp)
