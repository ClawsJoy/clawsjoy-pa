# -*- coding: utf-8 -*-
u"""safe_edit —— 通用「按 op 改件」器（去批次 · ⛔ 含某批之字面）。

承：PM 1189 §四⒜（编器落点 ⇒ scripts/dev · 通用与 recipes 分家）
    PM 1183 §二（**印须取自读 · ⛔ 取自算**）
    PM 1178 §五（存底粒度 ＝ 「改」· ⛔ 「件」· 一改一底）
    PM 1187 §二⒜（**assert 是冗余之闸 · ⛔ 代出处**）
    PM 1292 §四（**底名正形**：底 ＝ 〈件名〉.before_〈印16〉 —— ⛔ 再生点前缀之旧形 · 旧形唯备兼容之读）

用法（由 recipe 调）：
    import safe_edit as S
    S.cli(EDITS, ORDER, bases=BASES, title=u"…")
      python -X utf8 -B <recipe>.py <KEY|all> [--apply]   # ⛔ 无 --apply ⇒ 只演
      python -X utf8 -B <recipe>.py --verify               # 由底回放 ／ 比对记录之「出」

op 之形：
    ("sub",    旧串, 新串)          # 命中须恰 1 次
    ("lines",  行首前缀, [新行…])    # 行首先缀命中须恰 1 次（整行替换）
    ("append", 文)                  # 件末追加（保留原行末符 · 前置空行）

⭐ 印之出处（硬律）：改前 ＝ **读盘** ／ 改后 ＝ **写后回读**；
   `assert（回读 ≡ 演算）` 唯作冗余之闸 —— ⛔ 代出处（承 PM 1187 §二⒜）。
"""
import hashlib
import os
import sys

ROOT_DEFAULT = r"D:\clawsjoy_v9"
DOT_PREFIX = ".before_"


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def load(rel, root=None):
    p = rel if os.path.isabs(rel) else os.path.join(root or ROOT_DEFAULT, rel)
    return p, open(p, "rb").read().decode("utf-8")


def backup_path(p, h):
    u"""底之名（**正形** · 承 PM 1292 §四）：〈件名〉.before_〈印16〉 ——
    ⛔ 点前缀之旧形（旧形唯备兼容之**读** · 承 PM 1292 §四）。"""
    return "%s%s%s" % (p, DOT_PREFIX, h)


def backup_path_legacy(p, h):
    u"""旧形（点前缀 · .before_〈印16〉.〈件名〉）—— ⛔ 再生；唯备兼容之读。"""
    return os.path.join(os.path.dirname(p), "%s%s.%s" % (DOT_PREFIX, h, os.path.basename(p)))


def backup_find(p, h):
    u"""底之两形之候（**正形先 · 旧形后**）⇒ 路 ∨ None（唯读 · ⛔ 写）。"""
    for bp in (backup_path(p, h), backup_path_legacy(p, h)):
        if os.path.exists(bp):
            return bp
    return None


def make_backup(p):
    u"""一改一底：底之名 ≡ 其值（**取自读** · ⛔ 取自算 —— 承 PM 1183 §二）。

    已存在且值同 ⇒ 复用（幂等）；已存在而值异 ⇒ 中止（⛔ 覆盖）。
    """
    b = open(p, "rb").read()
    h = sha16(b)
    bp = backup_path(p, h)
    if os.path.exists(bp):
        if open(bp, "rb").read() != b:
            raise SystemExit(u"底已存在而值不同：%s" % bp)
        return h, bp, False
    open(bp, "wb").write(b)
    return h, bp, True


def op_sub(txt, old, new):
    n = txt.count(old)
    if n != 1:
        raise SystemExit(u"sub 命中 %d 次（须 1）：%r" % (n, old[:120]))
    return txt.replace(old, new, 1)


def op_lines(txt, prefix, newlines):
    lines = txt.split("\n")
    idx = [i for i, l in enumerate(lines) if l.startswith(prefix)]
    if len(idx) != 1:
        raise SystemExit(u"lines 行首命中 %d 次：%s" % (len(idx), prefix))
    lines[idx[0]:idx[0] + 1] = newlines
    return "\n".join(lines)


def op_append(txt, text):
    sep = "\r\n" if "\r\n" in txt else "\n"
    return txt.rstrip("\n") + sep + sep + text + sep


def apply_ops(txt, ops):
    for op in ops:
        kind = op[0]
        if kind == "sub":
            txt = op_sub(txt, op[1], op[2])
        elif kind == "lines":
            txt = op_lines(txt, op[1], op[2])
        elif kind == "append":
            txt = op_append(txt, op[1])
        else:
            raise SystemExit(u"未知 op：%s" % (kind,))
    return txt


def _targets(entries):
    u"""兼容两形：(rel, ops) 二元组 ／ (label, rel, ops) 三元组（条目形不一 ⇒ 器兼收）。"""
    for e in entries:
        if len(e) == 2:
            yield e[0], e[1]
        elif len(e) == 3:
            yield e[1], e[2]
        else:
            raise SystemExit(u"条目形不合（须 2 或 3 元）：%r" % (e,))


def run(edits, keys, apply=False, root=None):
    u"""逐 (rel, ops) 落改。改前印 ＝ 读 ／ 改后印 ＝ 写后回读（⭐ 出处唯一 ＝ 读）。"""
    for key in keys:
        for rel, ops in _targets(edits[key]):
            p, t0 = load(rel, root)
            h0 = sha16(open(p, "rb").read())          # ⭐ 改前之印 ⇒ 取自读
            t1 = apply_ops(t0, ops)
            h1 = sha16(t1.encode("utf-8"))            # 演算之值（唯供「演」· ⛔ 作所报之印）
            print(u"== [%s] %s" % (key, rel))
            print(u"   改前 %s ｜ %d B" % (h0, len(t0.encode("utf-8"))))
            if not apply:
                print(u"   改后（演 · 算） %s ｜ %d B" % (h1, len(t1.encode("utf-8"))))
                print(u"   （演 · 不写盘）")
                continue
            bh, bp, new = make_backup(p)
            open(p, "wb").write(t1.encode("utf-8"))
            print(u"   存底 %s ｜ %s ｜ %s" % (bh, u"新建" if new else u"复用", os.path.basename(bp)))
            h1r = sha16(open(p, "rb").read())         # ⭐ 所报之印 ＝ 「写后回读之值」⇒ 印之出处唯一（皆读）
            print(u"   改后 %s ｜ %d B" % (h1r, os.path.getsize(p)))
            assert h1r == h1, u"「写后回读 ≡ 演算」⛔ 立（冗余之闸 · ⛔ 代出处）：算 %s ／ 读 %s" % (h1, h1r)
    return 0


def verify(edits, bases):
    u"""由「底」回放：取底之字节 ⇒ apply_ops ⇒ 比对记录之「出」印。⛔ 不碰盘上之活件。"""
    bad = []
    for key, idx, rel, hb, hout in bases:
        tg = list(_targets(edits[key]))
        p, _ = load(rel)                       # 唯求「同目录」以定底之路（⛔ 读活件）
        bp = backup_find(p, hb)
        if not bp:
            print(u"   [无底] %s idx=%d ／ %s" % (key, idx, backup_path(p, hb)))
            bad.append(key)
            continue
        b = open(bp, "rb").read()
        if sha16(b) != hb:
            print(u"   [底名 ≠ 其值] %s idx=%d ／ %s" % (key, idx, bp))
            bad.append(key)
            continue
        got = sha16(apply_ops(b.decode("utf-8"), tg[idx][1]).encode("utf-8"))
        ok = (got == hout)
        print(u"   [%s idx=%d] %s ｜ 底 %s ⇒ 回放 %s ／ 记 %s ⇒ %s"
              % (key, idx, rel, hb, got, hout, u"OK" if ok else u"FAIL"))
        if not ok:
            bad.append(key)
    print(u"[回放] 共 %d 条 ／ 不合 %d 条%s" % (len(bases), len(bad), (u"：" + u" · ".join(bad)) if bad else u""))
    return 1 if bad else 0


EXIT_SEM = u"退出码语义：0 = 过（演 ／ 写 ／ 回放皆过）｜1 = 回放不合 ／ 用法错"


def cli(edits, order, bases=None, title=None, root=None):
    args = sys.argv[1:]
    if title:
        print(u"# %s" % title)
    print(u"# " + EXIT_SEM)
    if "--verify" in args:
        return verify(edits, bases or [])
    key = args[0] if args and not args[0].startswith("-") else ""
    do = "--apply" in args
    if key == "all":
        keys = list(order)
    elif key in edits:
        keys = [key]
    else:
        print(u"[用法错] 未知键：%s（有 %s ／ all ／ --verify）" % (key, "/".join(order)))
        return 1
    return run(edits, keys, apply=do, root=root)
