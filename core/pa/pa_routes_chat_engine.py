# -*- coding: utf-8 -*-
"""PA 路由 · chat_engine 簇（②v1 拆件 · 由 gateway_routes.py 机械切出 · 7 条路由）。

共享面唯 `pa_routes_common`（`bp` 唯彼处建）；本件 ⛔ 复建蓝图。
⭐ 导入即挂：件末 `register(bp)`；endpoint 名仍 `pa_routes.<func>`（⛔ 变）。
"""

import time
from pathlib import Path
from flask import jsonify, request
from core.lib.paths import vault_root
from core.pa.pa_routes_common import bp, ok, err
from core.pa.pa_routes_common import (
    PA_ASK_MIN_SCORE, PA_CORPUS_NAME_BIGRAMS, PA_FACES_DEFAULT_MAX_BYTES, PA_FACES_MAX_BYTES,
    PA_FACES_MIN_ROW, PA_FACES_MIN_SCORE, PA_FACES_VERSION, PA_FACE_ROLE,
    PA_KB_ASK_SCOPES, _ask_deadfile, _ask_decision, _bigrams,
    _cached_lines, _code_sha16, _core, _face_files,
    _inter_fast, _last_user_before, _lru_put, _pa_read_at,
    err, ok, pa_ask_scan_specs, pa_faces,
    pa_faces_gate,
)


_ASK_CACHE = {}


_ASK_CACHE_MAX = 256


PA_ASK_REFUSAL = "本机无据 ⇒ 我不答此问。"


PA_KB_EMPTY_ANSWER = u"本机还没有可检索的资料（检索面为空）⇒ 我不答此问。"


PA_ASK_REFUSAL_STALE = "查不到（知识库里没有相关内容）"


PA_KB_UNSET_VERDICT = (u"未接（选目录）：库根 ⛔ 得 ⇒ 本轮 ⛔ 扫描"
                       u"（⛔ 以空径充 ⇒ 误扫 CWD ⇒ 假有据）"
                       u"⇒ 拒答与否皆不成立（待选目录）")


PA_GATE_DECISIONS = ("not_asked", "grounded", "refused", "not_applicable")


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


PA_TURN_HUMAN = {
    "done": {
        u"一句": u"✅ 已记下这一轮（可回看）",
        u"做了什么": u"记下你这一轮的话与答复",
        u"动了哪些件": u"对话档（只增 · 原稿未动）",
        u"可否退": u"可 —— 只增记；要撤说一声",
    },
    "unknown": {
        u"一句": u"⚠ 这一轮记下没有：一时查不到（可稍后回看）",
        u"做了什么": u"试着记下你这一轮的话与答复",
        u"动了哪些件": u"对话档（读数一时取不得）",
        u"可否退": u"可 —— 只增记；要撤说一声",
    },
    "miss": {
        u"一句": u"⚠ 这一轮没记下（可再发一次）",
        u"做了什么": u"本轮未记入档",
        u"动了哪些件": u"无",
        u"可否退": u"不适用（未动）",
    },
}


def pa_turn_human(recorded, readable):
    u"""本轮之**人话回执**（⭐ 一处定形 · 承 pm_2021 §五.1）⇒ 四键（一句 ／ 做了什么 ／ 动了哪些件 ／ 可否退）。"""
    if not readable:
        return dict(PA_TURN_HUMAN["unknown"])
    return dict(PA_TURN_HUMAN["done" if recorded else "miss"])


PA_ASK_META_KW = ("上一条", "上一句", "上一问", "前一句", "刚才", "原样重复",
                  "重复一遍", "再说一遍", "我问的是什么", "我问了什么", "第几问", "你说过")


PA_ASK_FORCE_KW = ("检索：", "检索:", "@ask")   # ⭐ 退路（与前端同形 · 承 L123）


PA_ASK_META_NOT = ("第几问", "哪一问", "哪一条", "哪句提到", "哪一轮", "哪次")


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


def _kb_root_str():
    u"""库根（**字符串** · 未接 ⇒ ``""``）—— ⭐ pm_1500 §二：**唯一判点**（⛔ 二处各判「空」）。

    ⨀ 其源＝`core.lib.paths.vault_root()`（四序：`PA_VAULT_DIR` ⇒ 配置 `paths.vault_root`
      ⇒ 内置 `<data_root>/kb` ⇒ 末选 `PA_VAULT_LEGACY`）—— 本处 **⛔ 另判**（一处定形）。
    ⚠ 未接之「空」⛔ 同「扫了而无」（承「空 ≠ 缺」）⇒ 由 `no_kb_root` 分标。
    """
    _vr = vault_root()
    return str(_vr) if _vr is not None else ""


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


def register(bp):
    """把本簇之路由挂到共享蓝图 `pa_routes`（endpoint 名 ⛔ 变）。"""
    def _steer_missing(_key):
        u"""缺参 400：**壳从蓝图**（`ok`）＋ **键从族**（`missing` ／ `kind` ／ `route` ＝ `session` 族之 canonical）⇒ 承 PM 1253 §二 裁（⛔ 两族混壳）。"""
        _rule = request.url_rule
        _rt = (_rule.rule if _rule is not None else "?").lstrip("/")
        return jsonify({"ok": False, "error": u"%s: 缺 %s" % (_rt, _key),
                        "missing": [_key], "kind": "missing_param", "route": _rt}), 400

    _STEER_MAX_TEXT = 500           # ＝ shared_state.add_steer 之硬截（str(text)[:500]）⇒ 面先拦 · ⛔ 静默截断

    _STEER_KINDS = ("改令",)          # ⭐ PM 1253 §三 裁：唯「改令」（「接管」＝ 待立项 · 须先定义 · 承 PM 1230 §五）

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
        # ⭐ pm_2021 §五.1：回执之**人话**在此出生（⛔ 令面剥字）
        #   —— 与 recorded 同源判（一处）：⛔ 二处各判。
        _readable = bool(_ses_readable and _ev_readable)
        _recorded = bool(_readable and _after > _before and _ev_after > _ev_before)
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
            "recorded": _recorded,
            "human": pa_turn_human(_recorded, _readable),
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

    @bp.route("/v9/pa/resume", methods=["GET"])
    def pa_resume():
        r"""PA 断点续面（**只读**）：末次开机之攒件／续办／幂等跳过／失败件 ＋ 水印 ＋ 两读对表。

        ⭐ 断点续之跑器 ＝ `scripts\win_pa\boot_resume.py`（开机所调）；本面唯**读**同一真源
        （⛔ 两套读者）⇒ 面之数 ＝ 台账末行 ＋ 水印（⛔ 自报）。
        """
        from core.pa import resume_face as RF

        out = RF.build_resume(route_code_sha16=_code_sha16(pa_resume, RF))
        return ok(out)

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

    return bp


register(bp)
