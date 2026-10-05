# -*- coding: utf-8 -*-
u"""recipe —— 1057 批：元问答话／死件路之界／器病／档行 origin 改名（F–M · 八改八底）。

原器：p104_edit.py ⇒ 移此（承 PM 1189 §四⒜ · 按批编号）。
⛔ 通用之器在 ../safe_edit.py；本件唯「本批之字面」。
用法：python -X utf8 -B <本件> <F|G|H|I|J|K|L|M|all> [--apply]   （⛔ 无 --apply ⇒ 只演）
      python -X utf8 -B <本件> --verify                            （由底回放 ／ 比对记录之「出」）
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import safe_edit as S

F = [("dialog.py · src ⇒ origin", "core/pa/dialog.py", [
    ("lines", u"#     `src`", [
        u"#     `origin`         答之来源类别（⭐ PM 1183 §五.3：原名 `src` 与响应 `src`＝走径标 **同字异义** ⇒ 改 `origin` · 一名一义）"]),
    ("sub", u'SRC_MODEL = "model"\nSRC_GROUNDED = "grounded"\nSRC_REFUSED = "refused"\nSRC_UNSPECIFIED = "unspecified"',
            u'ORIGIN_MODEL = "model"\nORIGIN_GROUNDED = "grounded"\nORIGIN_REFUSED = "refused"\nORIGIN_UNSPECIFIED = "unspecified"'),
    ("sub", u"def _post_row(row, src=None, grounded=None, answer_source=None):",
            u"def _post_row(row, origin=None, grounded=None, answer_source=None):"),
    ("sub", u'    if src is not None and str(src) != "":\n        row["src"] = str(src)',
            u'    if origin is not None and str(origin) != "":\n        row["origin"] = str(origin)'),
    ("sub", u"    def post(self, role, text, topic=None, src=None, grounded=None, answer_source=None):",
            u"    def post(self, role, text, topic=None, origin=None, grounded=None, answer_source=None):"),
    ("sub", u"            _post_row(row, src=src, grounded=grounded, answer_source=answer_source)",
            u"            _post_row(row, origin=origin, grounded=grounded, answer_source=answer_source)"),
    ("sub", u"                src=None, grounded=None, answer_source=None):",
            u"                origin=None, grounded=None, answer_source=None):"),
    ("sub", u"               src=(src or SRC_MODEL), grounded=grounded,\n               answer_source=(answer_source or SRC_MODEL))",
            u"               origin=(origin or ORIGIN_MODEL), grounded=grounded,\n               answer_source=(answer_source or ORIGIN_MODEL))"),
])]

G = [("pa_core.py · 透传键 src ⇒ origin", "core/pa/pa_core.py", [
    ("sub", u'src=p.get("src"), grounded=p.get("grounded"),',
            u'origin=p.get("origin"), grounded=p.get("grounded"),'),
])]

H = [("gateway_routes.py · 透传键 src ⇒ origin", "core/pa/gateway_routes.py", [
    ("sub", u'"src": p.get("src"), "grounded": p.get("grounded"),',
            u'"origin": p.get("origin"), "grounded": p.get("grounded"),'),
    ("sub", u'        from core.pa.dialog import SRC_UNSPECIFIED   # ⭐ 源标之词表（一处定义 · 在 dialog.py）\n        _src_v = p.get("src") or SRC_UNSPECIFIED',
            u'        #   ⭐ PM 1183 §五.3：档行键 `src` ⇒ **`origin`**（一名一义 —— 与响应之 `src`（＝走径标）别）。\n        from core.pa.dialog import ORIGIN_UNSPECIFIED   # ⭐ 源标之词表（一处定义 · 在 dialog.py）\n        _org_v = p.get("origin") or ORIGIN_UNSPECIFIED'),
    ("sub", u'_sess.post("assistant", _a, src=_src_v, grounded=_gr_v, answer_source=_as_v)',
            u'_sess.post("assistant", _a, origin=_org_v, grounded=_gr_v, answer_source=_as_v)'),
])]

I = [("gateway_routes.py · context_missing 空答 ⇒ 人话句", "core/pa/gateway_routes.py", [
    ("lines", u'            return ok({"grounded": False, "refused": True, "answer_source": "context_missing",', [
        u'            # ⭐ PM 1183 §五.1（准办 · 一改一底）：拒答亦须有人话句 —— 形同 decision_none',
        u'            #   （原 `answer` ＝ "" ⇒ 前端只读 answer ⇒ 见「空答」· 承「⛔ 失败静默」）。',
        u'            return ok({"grounded": False, "refused": True, "answer_source": "context_missing",']),
    ("sub", u'"answer": "", "context_prev": "",',
            u'"answer": "本会话无可读之上句（元问 · 本机无「上一句」可引）⇒ 如实不答（⛔ 不编）", "context_prev": "",'),
])]

J = [("落台账_行.py · 面之快照「取数刻」被吞", r"D:\Obsidian\ClawsJoy\ClawsJoy\内容工坊\08_工具\落台账_行.py", [
    ("sub", u"import os, io, csv, sys, hashlib, argparse, datetime",
            u"import os, io, csv, sys, re, hashlib, argparse, datetime"),
    ("sub", u'+ u"# 面之快照（⛔ 契 · ⛔ 判红之据）· 取数刻 %s · bytes %d · 数据行 %d · 契 %s\\n"',
            u'+ u"# 面之快照（⛔ 契 · ⛔ 判红之据） · 取数刻 %s · bytes %d · 数据行 %d · 契 %s\\n"'),
    ("sub", u'                if u" " in kv:\n                    k, v = kv.split(u" ", 1)\n                    d[k] = v\n        else:',
            u'                if u" " in kv:\n                    k, v = kv.split(u" ", 1)\n                    d[k] = v\n            # ⭐ PM 1183 §八（器病 · 低）：表头括号内之 `·` 与「取数刻」相连\n            #   （「）· 取数刻」）⇒ 裸 split(u" · ") ⛔ 切 ⇒ 该 token 首键落成 `⛔` ⇒ 「取数刻」被吞（恒 `?`）。\n            #   ⇒ 加正则兜（新旧两形表头皆可读 ⇒ 存量侧车亦复）。\n            _m = re.search(u"取数刻\\\\s+(\\\\S+)", ln)\n            if _m:\n                d[u"取数刻"] = _m.group(1)\n        else:'),
])]

K = [(".gitignore · 准入存底两形", ".gitignore", [
    ("append", u"# ===== 存底（一改一底 · 承 PM 1183 §五.2 · ⛔ 删底）=====\n*.before_*\n.before_*"),
])]

L = [("gateway_routes.py · 死件路：账不可读 ⇒ 唯关键字问入本路（⛔ 劫持全问）", "core/pa/gateway_routes.py", [
    ("sub", u'''    except Exception as _e:
        return {"grounded": False, "refused": False,
                "answer": "死件账不可读（%s：%s）⇒ 如实不答（⛔ 不编）" % (_path, _e),''',
            u'''    except Exception as _e:
        # ⭐ 2026-10-05（我自逮 · 1057 · 承 PM 1183 §八之精神）：账不可读 ⇒ ⛔ 得据此断言「本路」
        #   —— 名中之路须读账 ⇒ 无可判 ⇒ **问 ⛔ 含关键字者 ⇒ 返回 None**（交后续分路）；
        #   ⛔ 返回本路之 dict（否则 **每一问** 皆被本路劫持 ⇒ 承「弱保证 ≠ 真闸」）。
        if not _kw:
            return None
        return {"grounded": False, "refused": False,
                "answer": "死件账不可读（%s：%s）⇒ 如实不答（⛔ 不编）" % (_path, _e),'''),
])]

M = [("gateway_routes.py · PA_FACES_VERSION .8 ⇒ .9（载件之面证）", "core/pa/gateway_routes.py", [
    ("sub", u'PA_FACES_VERSION = "2026-10-05.8"   # ⭐ .8：死件账之**直读路**',
            u'PA_FACES_VERSION = "2026-10-05.9"   # ⭐ .9：元问路（context_missing）之答话 ＋ 死件路「账不可读」之界（PM 1183 §五.1 ／ §八 · 我 1057）⇒ 仍 +1｜⭐ .8：死件账之**直读路**'),
])]

EDITS = {"F": F, "G": G, "H": H, "I": I, "J": J, "K": K, "L": L, "M": M}
ORDER = ["F", "G", "H", "I", "J", "K", "L", "M"]

# 何批之改 ⇒ 用何器之印（底 ⇒ 出 · 供 --verify 由底回放）
BASES = [
    ("F", 0, "core/pa/dialog.py", "2e1989eff6a34db1", "c34b0ae7ddb1ef37"),
    ("G", 0, "core/pa/pa_core.py", "5dba11f023edb883", "7cb7d13ed66ca4de"),
    ("H", 0, "core/pa/gateway_routes.py", "783012f8a1550279", "78652e53e372724f"),
    ("I", 0, "core/pa/gateway_routes.py", "78652e53e372724f", "5e720bd71630dd21"),
    ("J", 0, r"D:\Obsidian\ClawsJoy\ClawsJoy\内容工坊\08_工具\落台账_行.py", "4f1a239ea0383d4b", "b95b4004b4aa678e"),
    ("K", 0, ".gitignore", "621b07950bacd199", "b9e7c0771af9910f"),
    ("L", 0, "core/pa/gateway_routes.py", "5e720bd71630dd21", "0f34ad396fa2ef6e"),
    ("M", 0, "core/pa/gateway_routes.py", "0f34ad396fa2ef6e", "4f2b0a4e661157d0"),
]

if __name__ == "__main__":
    raise SystemExit(S.cli(EDITS, ORDER, bases=BASES, title=u"1057 批 · F–M（八改八底）"))
