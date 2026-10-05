# -*- coding: utf-8 -*-
u"""recipe —— 1055 批：源标（档行三键）／拒答 canonical／死件账直读路（A–E · 五改五底）。

原器：p103_edit.py（A–D）＋ p103_fixE.py（E）⇒ 并此（承 PM 1189 §四⒜ · 按批编号）。
⛔ 通用之器在 ../safe_edit.py；本件唯「本批之字面」。
用法：python -X utf8 -B <本件> <A|B|C|D|E|all> [--apply]   （⛔ 无 --apply ⇒ 只演）
      python -X utf8 -B <本件> --verify                      （由底回放 ／ 比对记录之「出」）
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import safe_edit as S


# ============================ EDIT A ============================
# ⒝-1：后端拒答之辞 ⇒ canonical（一处定义 · 真源归后端）＋ 供前端引用之响应键
A_REFUSAL_OLD = 'PA_ASK_REFUSAL = "查不到（知识库里没有相关内容）"'
A_REFUSAL_NEW = r'''# ⭐ PM 2026-10-05 22:34 §四⒝-1：拒答之辞 ⇒ **canonical（一处定义 · 真源归后端）**
#   病（逐字）：原辞「查不到（知识库里没有相关内容）」**失实** —— 本闸实扫**八面**
#     （收件箱 ／ 知识库 ／ 文件 ／ 台账 ／ 平台台账 ／ 台账·信通 ／ 梦中月水中花 ／ 文件·产出）
#     ⇒ 「知识库」以偏概全 ⇒ 辞失实（承「⛔ 以偏概全之辞」）。
#   ⚠ 且前端 `web\pa\faces\send.js` 另有 `PA_REFUSE_CANON` ⇒ **两辞并存 ＝ 漂移之床**（承「一处口径」）
#     ⇒ 今定 canonical 于**后端**（唯此一处），前端改**引用**（响应键 `refusal_canon` · 见 `pa_ask` 之 base）⇒ ⛔ 二处各写。
#   ⚠ 界（照 PM 之限）：⛔ 不改闸之判据；⛔ 不改「判据行」（verdict）之实 —— 唯「答话」之辞正。
PA_ASK_REFUSAL = "本机无据 ⇒ 我不答此问。"
# ⭐ 旧辞（失实 · ⛔ 勿再入 answer）：留名以**识别旧痕**（前端词形闸之旁证 · 承 PM 22:34 §三）
PA_ASK_REFUSAL_STALE = "查不到（知识库里没有相关内容）"'''

A_BASE_OLD = '''        base = {"question": q, "read_at": _at, "kb_root": str(kb), "searched": res["searched"],
                "from_cache": _from_cache,
'''
A_BASE_NEW = '''        base = {"question": q, "read_at": _at, "kb_root": str(kb), "searched": res["searched"],
                "from_cache": _from_cache,
                # ⭐ PM 2026-10-05 22:34 §四⒝-1：**canonical 之引用面** —— 前端取此二键
                #   （⛔ 二处各写 ⇒ 免「漂移之床」；「查不到」之旧辞作**词形闸**之旁证）
                "refusal_canon": PA_ASK_REFUSAL, "refusal_stale": PA_ASK_REFUSAL_STALE,
'''

A_DEC_OLD = '''            _bb = {"question": q, "read_at": _at, "kb_root": str(kb), "searched": 0,
                   "scope": [], "threshold": None, "faces": {}, "faces_missing": [],
                   "faces_skipped": {}, "evidence": [], "archive_hits": [], "judge": _j,
                   "ask_domain": "decision"}
'''
A_DEC_NEW = '''            _bb = {"question": q, "read_at": _at, "kb_root": str(kb), "searched": 0,
                   "scope": [], "threshold": None, "faces": {}, "faces_missing": [],
                   "faces_skipped": {}, "evidence": [], "archive_hits": [], "judge": _j,
                   "ask_domain": "decision",
                   "refusal_canon": PA_ASK_REFUSAL, "refusal_stale": PA_ASK_REFUSAL_STALE}
'''

A_META_OLD = '''            _bb = {"question": q, "read_at": _at, "kb_root": str(kb), "searched": 0, "scope": [],
                   "threshold": None, "faces": {}, "faces_missing": [], "faces_skipped": {},
                   "evidence": [], "archive_hits": [], "judge": _j,
                   "ask_domain": "meta", "context_meta": _ctx}
'''
A_META_NEW = '''            _bb = {"question": q, "read_at": _at, "kb_root": str(kb), "searched": 0, "scope": [],
                   "threshold": None, "faces": {}, "faces_missing": [], "faces_skipped": {},
                   "evidence": [], "archive_hits": [], "judge": _j,
                   "ask_domain": "meta", "context_meta": _ctx,
                   "refusal_canon": PA_ASK_REFUSAL, "refusal_stale": PA_ASK_REFUSAL_STALE}
'''

EDIT_A = [("core/pa/gateway_routes.py", [
    ("sub", A_REFUSAL_OLD, A_REFUSAL_NEW),
    ("sub", A_BASE_OLD, A_BASE_NEW),
    ("sub", A_DEC_OLD, A_DEC_NEW),
    ("sub", A_META_OLD, A_META_NEW),
])]

# ============================ EDIT B ============================
B_POST_OLD = '''    def post(self, role, text, topic=None):
        # ⭐ PM 2026-10-05（承 技总 970 §三）：⭐ 只包「读-改-写」（`seq` 之算在锁内）
        #   负控之证（技总 `971 §三`）：拆锁下 8 线程 × 50 ⇒ 重号 79 ／ 丢 2 轮
        with _lock_for(self.path):
            rows = self._read()
            seq = (rows[-1]["seq"] + 1) if rows else 1
            row = {"seq": seq, "role": role, "text": str(text)[:4000], "topic": topic, "ts": time.strftime("%H:%M:%S")}
            self._append(row)
        return row
'''
B_POST_NEW = '''    def post(self, role, text, topic=None, src=None, grounded=None, answer_source=None):
        # ⭐ PM 2026-10-05（承 技总 970 §三）：⭐ 只包「读-改-写」（`seq` 之算在锁内）
        #   负控之证（技总 `971 §三`）：拆锁下 8 线程 × 50 ⇒ 重号 79 ／ 丢 2 轮
        # ⭐ PM 2026-10-05 22:34 §四⒝-2：**源标之加性字段**（见 `_post_row` 之注）
        with _lock_for(self.path):
            rows = self._read()
            seq = (rows[-1]["seq"] + 1) if rows else 1
            row = {"seq": seq, "role": role, "text": str(text)[:4000], "topic": topic, "ts": time.strftime("%H:%M:%S")}
            _post_row(row, src=src, grounded=grounded, answer_source=answer_source)
            self._append(row)
        return row
'''

B_VOCAB_NEW = '''# ⭐ PM 2026-10-05 22:34 §四⒝-2（技总之域）：会话档之**源标**（加性字段 · ⛔ 破既有读者）
#   病（逐字）：档行＝{"seq","role","text","topic","ts"} ⇒ **无源标** ⇒ 档读者（PM ／ 老板 ／
#     日后之席）无从辨「模型断言」vs「有据之答」；老板所见「T1已完成」之编造正出此路
#     ⇒ 屏上有标 ／ **档中无标** ⇒ 事后取证唯见模型之言 ＝ 看似有据（承「假绿」之族）。
#   ⇒ 加**加性键**（JSONL 加键 ＝ 向后兼容 · ⛔ 改 `text` 之体 · ⛔ 改既有四键）：
#     `src`            答之来源类别 —— 闭合集：`model`（脑／模型所生）｜`grounded`（本机有据）
#                      ｜`refused`（闸拒 · 无据不答）｜`unspecified`（调用方未声明 ⇒ ⛔ 当有据）
#     `grounded`       bool ／ ⛔ 缺键（缺键 ＝ 未标 ⇔ ⛔「无据」）
#     `answer_source`  str（后端之原值：decision ／ knowledge ／ refused ／ model ／ …）⇒ 供回指
#   ⚠ **唯当有值 ⇒ 落键**（⛔ 落 None ／ ⛔ 落空串 ⇒ 免「假标」）⇒ 旧行形不变。
#   ⚠ ⭐ **两写路同形**（PM 定 · 须与 CW 对齐）：`/v9/pa/dialog`（脑路）与
#     `POST /v9/pa/turn`（前端写路）**同键同义** ⇒ 唯键名与形一致，读者方可一比。
SRC_MODEL = "model"
SRC_GROUNDED = "grounded"
SRC_REFUSED = "refused"
SRC_UNSPECIFIED = "unspecified"


def _post_row(row, src=None, grounded=None, answer_source=None):
    u"""源标之加性字段（⛔ 覆盖既有四键 · 唯当有值 ⇒ 落键）。"""
    if src is not None and str(src) != "":
        row["src"] = str(src)
    if grounded is not None:
        if isinstance(grounded, str):
            grounded = grounded.strip().lower() in ("1", "true", "yes", "y", "有据")
        row["grounded"] = bool(grounded)
    if answer_source is not None and str(answer_source) != "":
        row["answer_source"] = str(answer_source)
    return row


class DialogSession:'''

B_RESP_OLD = '''    def respond(self, sid, user_text, topic=None, brain=None, profile_brief="", ledger_brief=""):
        s = self.session(sid)
        s.post("user", user_text, topic=topic)
'''
B_RESP_NEW = '''    def respond(self, sid, user_text, topic=None, brain=None, profile_brief="", ledger_brief="",
                src=None, grounded=None, answer_source=None):
        s = self.session(sid)
        s.post("user", user_text, topic=topic)
'''

B_ASSIST_OLD = '        s.post("assistant", reply, topic=topic or s.latest_topic())'
B_ASSIST_NEW = '''        # ⭐ PM 2026-10-05 22:34 §四⒝-2：本路**本即脑（模型）路** ⇒ 缺省标 `model`
        #   （真值 · ⛔ 冒 `grounded`）；调用方知其实（如闸已判有据）⇒ 以显式值覆之。
        s.post("assistant", reply, topic=topic or s.latest_topic(),
               src=(src or SRC_MODEL), grounded=grounded,
               answer_source=(answer_source or SRC_MODEL))'''

EDIT_B = [("core/pa/dialog.py", [
    ("sub", B_POST_OLD, B_POST_NEW),
    ("sub", "class DialogSession:", B_VOCAB_NEW),
    ("sub", B_RESP_OLD, B_RESP_NEW),
    ("sub", B_ASSIST_OLD, B_ASSIST_NEW),
])]

# ============================ EDIT C ============================
C_DIALOG_OLD = '''        r = pa.handle("dialog_post", {"sid": sid, "text": text, "topic": p.get("topic"), "brain": _brain})
'''
C_DIALOG_NEW = '''        # ⭐ PM 2026-10-05 22:34 §四⒝-2：**源标透传**（档行外加性键 · ⛔ 改答话体）
        r = pa.handle("dialog_post", {"sid": sid, "text": text, "topic": p.get("topic"), "brain": _brain,
                                      "src": p.get("src"), "grounded": p.get("grounded"),
                                      "answer_source": p.get("answer_source")})
'''

C_CORE_OLD = '''                r = self.dialog.respond(
                    p["sid"],
                    p["text"],
                    topic=p.get("topic"),
                    brain=p.get("brain"),
                    profile_brief=p.get("profile_brief", self.profile.chat_brief(p.get("text", ""))),
                    ledger_brief=p.get("ledger_brief", ""),
                )
'''
C_CORE_NEW = '''                r = self.dialog.respond(
                    p["sid"],
                    p["text"],
                    topic=p.get("topic"),
                    brain=p.get("brain"),
                    profile_brief=p.get("profile_brief", self.profile.chat_brief(p.get("text", ""))),
                    ledger_brief=p.get("ledger_brief", ""),
                    # ⭐ PM 2026-10-05 22:34 §四⒝-2：源标之透传（⛔ 本层自造值 · ⛔ 覆盖后端之判）
                    src=p.get("src"), grounded=p.get("grounded"),
                    answer_source=p.get("answer_source"),
                )
'''

C_TURN_OLD = '''        _ses_err = ""
        try:
            if _u:
                _sess.post("user", _u)
            if _a:
                _sess.post("assistant", _a)
'''
C_TURN_NEW = '''        _ses_err = ""
        # ⭐ PM 2026-10-05 22:34 §四⒝-2：**源标透传**（本路与 `/v9/pa/dialog` 同键同义 · 承「两写路同形」）
        #   ⚠ 缺省 `unspecified`（调用方未声明）—— ⛔ 冒 `model` ／ ⛔ 冒 `grounded`
        #     （承「⛔ 以我之预期充文本之实」）；前端知其实（如闸已拒）⇒ 显式传 `refused` ／ `grounded`。
        from core.pa.dialog import SRC_UNSPECIFIED   # ⭐ 源标之词表（一处定义 · 在 dialog.py）
        _src_v = p.get("src") or SRC_UNSPECIFIED
        _gr_v = p.get("grounded")
        _as_v = p.get("answer_source")
        try:
            if _u:
                _sess.post("user", _u)
            if _a:
                _sess.post("assistant", _a, src=_src_v, grounded=_gr_v, answer_source=_as_v)
'''

EDIT_C = [("core/pa/gateway_routes.py", [
    ("sub", C_DIALOG_OLD, C_DIALOG_NEW),
    ("sub", C_TURN_OLD, C_TURN_NEW),
]), ("core/pa/pa_core.py", [
    ("sub", C_CORE_OLD, C_CORE_NEW),
])]

# ============================ EDIT D ============================
D_KW_OLD = 'PA_ASK_DECISION_KW = ("决策记录", "决策日志", "决策账", "拍板记录", "decision log", "decision_log")'
D_KW_NEW = '''PA_ASK_DECISION_KW = ("决策记录", "决策日志", "决策账", "拍板记录", "decision log", "decision_log")
# ⭐ PM 2026-10-05 22:34 §三①（准）：**死件账之直读路**之判据表 —— 「逐字入件」（PM 条件⒜）
#   ⒜ 关键字表（问含任一 ⇒ 本路）
PA_ASK_DEADFILE_KW = ("死件", "缺件", "登记之谎", "deadfile", "dead_file", "缺源")
#   ⒝ 名中：唯「**该账已录之名**」（真缺[].value ／ 真缺[].yaml 之 basename ± 扩展）⇒ 见 _ask_deadfile
#   ⚠ 账之真源（一处口径 · 与 1055 之入面表同径）
PA_ASK_DEADFILE_LEDGER = "deadfile_ledger.json"'''

D_FN_NEW = r'''def _ask_deadfile(question):
    u"""⭐ 死件账之**直读路**（PM 2026-10-05 22:34 §三① 准 · 同 _ask_decision 之形）。

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


def pa_kb_search(question, kb_root, limit=5, min_score=PA_ASK_MIN_SCORE):'''

D_WIRE_NEW = '''        # ⭐ 死件账之直读路（PM 2026-10-05 22:34 §三① 准 · 同修①之形 · ⛔ 改闸之判据）
        _dead = _ask_deadfile(q)
        if _dead is not None:
            _j = {"threshold": None, "faces_version": PA_FACES_VERSION, "faces_count": 0,
                  "faces_files_total": 0, "face_snapshot_at": None, "judge_at": _at}
            _bb = {"question": q, "read_at": _at, "kb_root": str(kb), "searched": 0,
                   "scope": [], "threshold": None, "faces": {}, "faces_missing": [],
                   "faces_skipped": {}, "evidence": [], "archive_hits": [], "judge": _j,
                   "ask_domain": "deadfile",
                   "refusal_canon": PA_ASK_REFUSAL, "refusal_stale": PA_ASK_REFUSAL_STALE}
            _bb.update(_dead)
            return ok(_bb)
        if _ask_scope(q) == "meta":'''

D_VER_NEW = ['PA_FACES_VERSION = "2026-10-05.8"   # ⭐ .8：死件账之**直读路**（PM 22:34 §三① 准 · 条件⒟）⇒ 仍 +1（承 L152）｜⭐ .7：面表＋角色表增「死件账」（PM 22:34 §二 裁）｜⭐ 2026-10-05：面表＋角色表增 `文件·产出`（PM「M1 接线收口」§二 ⒜）⇒ 皆 +1']

EDIT_D = [("core/pa/gateway_routes.py", [
    ("sub", D_KW_OLD, D_KW_NEW),
    ("sub", "def pa_kb_search(question, kb_root, limit=5, min_score=PA_ASK_MIN_SCORE):", D_FN_NEW),
    ("sub", '        if _ask_scope(q) == "meta":', D_WIRE_NEW),
    ("lines", "PA_FACES_VERSION = ", D_VER_NEW),
])]

# ============================ EDIT E ============================
# E：docstring 前缀 u ⇒ r（SyntaxWarning 之修 · 原 p103_fixE.py）
EDIT_E = [("core/pa/gateway_routes.py", [
    ("sub", '    u"""⭐ 死件账之**直读路**（PM 2026-10-05 22:34 §三① 准 · 同 _ask_decision 之形）。', '    r"""⭐ 死件账之**直读路**（PM 2026-10-05 22:34 §三① 准 · 同 _ask_decision 之形）。'),
])]

EDITS = {"A": EDIT_A, "B": EDIT_B, "C": EDIT_C, "D": EDIT_D, "E": EDIT_E}
ORDER = ["A", "B", "C", "D", "E"]

# 何批之改 ⇒ 用何器之印（底 ⇒ 出 · 供 --verify 由底回放）
BASES = [
    ("A", 0, "core/pa/gateway_routes.py", "abe08578671ffbb5", "ba41c213da539bb5"),
    ("B", 0, "core/pa/dialog.py", "703f2b2796a62b1a", "2e1989eff6a34db1"),
    ("C", 0, "core/pa/gateway_routes.py", "ba41c213da539bb5", "3c2f4a3a7e74524f"),
    ("C", 1, "core/pa/pa_core.py", "ea11b5233b4e5544", "5dba11f023edb883"),
    ("D", 0, "core/pa/gateway_routes.py", "3c2f4a3a7e74524f", "1cf3948d22ee26df"),
    ("E", 0, "core/pa/gateway_routes.py", "1cf3948d22ee26df", "783012f8a1550279"),
]

if __name__ == "__main__":
    raise SystemExit(S.cli(EDITS, ORDER, bases=BASES, title=u"1055 批 · A–E（五改五底）"))
