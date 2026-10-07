# -*- coding: utf-8 -*-
u"""入仓之守（pm_1580 §二.4）：本仓（tracked）之件 ⛔ 载「个人痕」—— 扫 `git ls-files`。

二类（判据 · 一处定形）：
  ⭐ HARD（须 ＝ 0）：个人邮箱 ／ 用户档之径（盘符 ＋ `Users` 目录之形）／ 裸用户名。
     由：真 PII —— 认得出「是谁 ／ 哪台机」· 一 push 即出到外网之盘。
  ⭐ LEGACY（须 ＝ 基）：本机之库根（盘符 ＋ 库名）／ WSL 之家（`/home/<名>`）／
     开发机之根（盘符 ＋ paseo ／ codex ／ npm ／ clawsjoy 之根）／ 组织物之名（面名三串）。
     留 ∵ **运行 ／ 组织版所必需**（真源表 ／ 径归一 ／ 面之组织定位）—— 逐处之由见回件
     pm_1581。⚠ 其剔之准 ⛔ 随族（⛔ 一刀切 —— 那会把「运行所必需」一并清掉）。
     由：⛔ 静增（其数 ＝ 面之量 ⇒ 须可回指）｜⚠ 清之则**须并降基**（一处定形）。

⚠ 本档 ⛔ 载其字面：诸式皆以**碎片**拼成（如 `"fly" + "bo"`）⇒ 本档自扫亦清
  ⇒ **⛔ 自指之洞**（⛔ 以「排除本档」为解 —— 那会把本档留作藏身之所）。

何形调用：python -X utf8 -B -m pytest tests/unit/test_repo_no_personal_traces.py -q
"""
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#: 用户名（碎片拼 · 本档自清）—— 先于下文用
_U = "fly" + "bo"
#: 个人邮箱（同上）
_MAIL = _U + "y_qu" + "@" + "163" + ".com"
#: 库根之名 ／ 面名（同上）
_OBS = "Obsid" + "ian"
_ORG = ("paseo" + "-" + "pm", u"\u5185\u5bb9" + u"\u5de5\u574a", u"\u4fe1" + u"\u901a")
#: 盘符之式（`[\\/]{1,2}` 兼收源码之逸写形 · 承 pm_1580 之「并扫逸写之形」）
_ABS = r"[A-Za-z]:[\\/]{1,2}"

HARD = {
    u"个人邮箱": re.compile(re.escape(_MAIL), re.I),
    u"用户档之径": re.compile(_ABS + r"Users[\\/]{1,2}" + _U + r"\b", re.I),
    u"裸用户名": re.compile(r"(?<![/\\])" + _U, re.I),
}
LEGACY = {
    u"本机之库根": re.compile(_ABS + _OBS),
    u"WSL 之家": re.compile(r"/home/" + _U),
    u"开发机之根": re.compile(_ABS + r"(paseo|codex|npm|clawsjoy)[_-]"),
    u"组织物之名": re.compile(u"|".join(re.escape(x) for x in _ORG)),
}

#: 日当值（器取 · 2026-10-07 清毕）—— **须 ＝ 实**：增 ⇒ 红（⛔ 静增）；减 ⇒ 红（一处定形：清了就并降基）。
BASELINE = {u"本机之库根": 19, u"WSL 之家": 1, u"开发机之根": 16, u"组织物之名": 100}


def _tracked(root):
    r = subprocess.run(["git", "-C", root, "-c", "core.quotepath=false", "ls-files"],
                       capture_output=True)
    return [x.decode("utf-8", "replace") for x in (r.stdout or b"").splitlines() if x.strip()]


def scan(root=None):
    u"""还 {family: [(rel, line_no, line_text)]}—— 出包侧之同形扫。
    ⛔ 跳二进制（首 4 KiB 含 NUL）。"""
    root = root or ROOT
    out = {k: [] for k in list(HARD) + list(LEGACY)}
    for rel in _tracked(root):
        p = os.path.join(root, rel.replace("/", os.sep))
        try:
            raw = open(p, "rb").read()
        except Exception:
            continue
        if b"\x00" in raw[:4096]:
            continue
        try:
            txt = raw.decode("utf-8")
        except Exception:
            txt = raw.decode("gbk", "replace")
        for i, line in enumerate(txt.splitlines(), 1):
            for k, rx in list(HARD.items()) + list(LEGACY.items()):
                if rx.search(line):
                    out[k].append((rel, i, line.strip()[:160]))
    return out


def test_仓内无个人痕():
    got = scan()
    bad = [k for k in HARD if got[k]]
    assert not bad, (u"⛔ 硬 PII 入仓：%s\n" % u"、".join(bad)
                     + u"\n".join(u"  %s:%d  %s" % t for k in bad for t in got[k][:8]))
    for k in LEGACY:
        assert len(got[k]) == BASELINE[k], (
            u"⛔ 旧痕之数 ⛔ 符基（%s）⇒ ⛔ 静增 ／ 静减。\n"
            u"  当：%s\n  基：%s\n  前三：%s\n"
            u"  若为正当 ⇒ 请明书并改基（一处定形）") % (
            k, u"  ".join(u"%s = %d" % (n, len(got[n])) for n in LEGACY), BASELINE,
            u" · ".join(u"%s:%d" % (r, i) for r, i, _t in got[k][:3]))