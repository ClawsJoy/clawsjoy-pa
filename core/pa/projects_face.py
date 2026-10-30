# -*- coding: utf-8 -*-
u"""projects_face.py —— 端面「到点／项目」之采数**一处出**（承 CEO 2221 §四 ／ PM 2222 §二 ／ PM 2228 §二）。

⭐ 律：**唯调 codex/_CEO面核.py --due（一处出）· ⛔ 端自算**（承 CEO 2131 §一.2：同源之律）。
⭐ 返必载「取数刻 ＋ 口径 ＋ 源」（⛔ 只报值 · 承「引数须核取数面」）。
⭐ 唯读（⛔ 写 ／ ⛔ 动台账）。
"""
import hashlib
import os
import re
import subprocess
import sys

# 产品默认：用户自己的 Obsidian 库；⛔ 不把某个开发机的个人路径打进发行包。
VAULT = (os.getenv("PA_VAULT_ROOT") or "").strip() or os.path.join(
    os.path.expanduser("~"), "Obsidian", "ClawsJoy")
DUE_CORE = (os.getenv("PA_DUE_CORE") or "").strip() or os.path.join(VAULT, "codex", "_CEO面核.py")

# ⭐ 采数之所（四数 ＋ 取数刻 ＋ 口径）—— 逐字对 --due 之排版（真源 ＝ 器之出 · 此处唯解析）。
_DUE = re.compile(r"\[到点\] *数据行 *(\d+)[^｜]*｜ *待收口之试 *(\d+) *⇒ *红 *(\d+) *／ *阶催缴 *(\d+)[^｜]*｜ *取数刻 *([^｜]+?) *｜ *口径 *(\S+)")


def due_core_parse(text):
    u"""自 --due 之一行 ⇒ dict ∨ None（⛔ 采不入 ⇒ ⛔ 端自算兜底）。"""
    if not text:
        return None
    for ln in text.split("\n"):
        m = _DUE.search(ln)
        if m:
            return {"数据行": int(m.group(1)), "待收口之试": int(m.group(2)),
                    "红": int(m.group(3)), "阶催缴": int(m.group(4)),
                    "取数刻": m.group(5).strip(), "口径": m.group(6).strip()}
    return None


def due_core_run(core=None, timeout=90):
    u"""跑 codex/_CEO面核.py --due（唯读 · 一处出）⇒ (rc, 出) ∨ (None, 报)。"""
    p = core or DUE_CORE
    if not os.path.isfile(p):
        return None, u"⛔ 面核器不在：%s" % p
    try:
        r = subprocess.run([sys.executable, "-X", "utf8", "-B", p, "--due"],
                           capture_output=True, timeout=timeout)
    except Exception as e:
        return None, u"⛔ 面核器不可跑（%s）" % type(e).__name__
    return r.returncode, (r.stdout or b"").decode("utf-8", "replace") + (r.stderr or b"").decode("utf-8", "replace")


def stamp2(path):
    u"""印之书法二形（一处出 · 承 PM 2205 §二）。"""
    b = open(path, "rb").read()
    return u"md5[:16] %s ／ sha16 %s" % (hashlib.md5(b).hexdigest()[:16], hashlib.sha256(b).hexdigest()[:16])


def projects_face(core=None):
    u"""端面之数（唯调 --due · 一处出）⇒ dict（⛔ 自算 ⇒ 反控必咬）。"""
    p = core or DUE_CORE
    rc, out = due_core_run(p)
    if rc is None:
        return {"ok": False, "error": out, "源": p, "端自算": False}
    d = due_core_parse(out)
    if d is None:
        return {"ok": False, "error": u"⛔ 采数不入（⛔ 以端自算兜底）｜rc=%s" % rc,
                "源": p, "端自算": False, "原出": (out or "").strip()[:400]}
    d.update({"ok": True, "源": p, "端自算": False,
              "源印": (stamp2(p) if os.path.isfile(p) else None),
              "刻之性": u"读时（活面：逐次跑 --due ⇒ 数随刻变 · ⛔ 冻结面）"})
    return d
