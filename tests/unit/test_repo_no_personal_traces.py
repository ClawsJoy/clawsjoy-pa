# -*- coding: utf-8 -*-
u"""入仓之守（pm_1580 §二.4）：本仓（tracked）之件 ⛔ 载「个人痕」—— 扫 `git ls-files`。

二类（判据 · 一处定形）：
  ⭐ HARD（须 ＝ 0）：个人邮箱 ／ 用户档之径（盘符 ＋ `Users` 目录之形）／ 裸用户名。
     由：真 PII —— 认得出「是谁 ／ 哪台机」· 一 push 即出到外网之盘。
  ⭐ LEGACY（**逐件**符基 · ⛔ 族之总）：本机之库根（盘符 ＋ 库名）／ WSL 之家（`/home/<名>`）／
     开发机之根（盘符 ＋ paseo ／ codex ／ npm ／ clawsjoy 之根）／ 组织物之名（面名三串）。
     留 ∵ **运行 ／ 组织版所必需**（真源表 ／ 径归一 ／ 面之组织定位）—— 逐处之由见回件
     pm_1581。⚠ 其剔之准 ⛔ 随族（⛔ 一刀切 —— 那会把「运行所必需」一并清掉）。
     由：⛔ 静增（其数 ＝ 面之量 ⇒ 须可回指）｜⚠ 清之则**须并降基**（一处定形）。

⭐⭐ 尺之改（承 PM 2054 §三.1⒝ 之荐 · 归端）：
  旧尺 ＝ 「**族之总** ＝ 基」⇒ 他席**每一提交**皆可使之为红。本刻之病即此 ——
  `b544906` 之「改基」其数**取于同批新件之前**：其批并落 `test_sag_catalog_1949.py`（名族 `13`）
  ＋ `编目_要件入SAG.py`（名族 `12`）而基 ⛔ 含之 ⇒ 自该批（10:11）起**恒红**。
  （一手复算该刻：名族之实 ＝ `134`，基 ＝ `109`，差 `25` ＝ 该二件之和 —— 同源同刻之律未落。）
  ⇒ ⭐ 今尺 ＝ 「**逐件**（`rel` → 数）符基」：红时**唯指其件**（⛔ 以族之总累及无辜），
  而**件内之增**仍显形（⛔ 静增之守 ⛔ 丢）。⚠ 并由：改基**须以本器现取**（`--write`）——
  ⛔ 手抄（手抄之数 ＝ 另刻之实 ⇒ 本尺所治之病即此）。
  基线（一处定形）：`tests/baseline/personal_traces_baseline.json`。

⚠ 本档 ⛔ 载其字面：诸式皆以**碎片**拼成（如 `"fly" + "bo"`）⇒ 本档自扫亦清
  ⇒ **⛔ 自指之洞**（⛔ 以「排除本档」为解 —— 那会把本档留作藏身之所）。

何形调用：
  python -X utf8 -B -m pytest tests/unit/test_repo_no_personal_traces.py -q   # 判（四齿）
  python -X utf8 -B tests/unit/test_repo_no_personal_traces.py                # 只报差（⛔ 落盘）
  python -X utf8 -B tests/unit/test_repo_no_personal_traces.py --write        # 现取改基（先印差）
"""
import io
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASELINE_PATH = os.path.join(ROOT, "tests", "baseline", "personal_traces_baseline.json")
SCHEMA = "personal-traces-baseline/1"

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

#: 族之「由」（落基线 · 一处定形）—— 为何 ⛔ 清零，见本档头「二类」。
FAMILY_WHY = {
    u"本机之库根": u"运行必需：盘符 ＋ 库名之径（真源表 ／ 径归一之落处）",
    u"WSL 之家": u"运行必需：WSL 侧「家」之径（径隔离之齿之样）",
    u"开发机之根": u"运行必需：产线诸根之径（paseo ／ codex ／ npm ／ clawsjoy）",
    u"组织物之名": u"组织定位：面名三串（组织 ／ 仓 ／ 信箱）—— 面之组织定位所必需",
}
POLICY = (u"入仓之守：本仓（tracked）之件 ⛔ 载「个人痕」。"
          u"HARD（真 PII：个人邮箱 ／ 用户档之径 ／ 裸用户名）须 ＝ 0；"
          u"LEGACY（运行 ／ 组织版所必需之径与名）**逐件**符基 —— 新增件 ／ 件内之增 ／ 陈旧条目 皆红。")
NOTE = (u"本档是**逐件白名单**（`族 -> {rel: 数}`），由 tests/unit/test_repo_no_personal_traces.py 读取："
        u"新增件或件内之增 ⇒ 红（须明书其由）；条目不再复现 ⇒ 红（陈旧 ＝ 噪声掩体 · 清了须并降基）。"
        u"⚠ 改基唯以本器**现取** —— `python -X utf8 -B tests/unit/test_repo_no_personal_traces.py --write`"
        u"（⛔ 手抄：手抄之数 ＝ 另刻之实 ⇒ 本尺所治之病即此 · 同「同源同刻」之律）。")
DECISION_REF = (u"pm_1580 二.4（立齿）／ pm_1936 二（二次核基）／ PM 2054 三.1b（改逐件之判法 · 归端）。")

_CACHE = {}


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


def _got():
    u"""一遍之扫（四齿共用 · ⛔ 各扫一遍）。"""
    if "got" not in _CACHE:
        _CACHE["got"] = scan()
    return _CACHE["got"]


def ledger(got=None):
    u"""还 {族: {rel: 数}} —— **逐件**（判据与改基同以此为骨 · 一处定形）。"""
    got = _got() if got is None else got
    return {fam: dict(sorted(Counter(rel for rel, _i, _t in got[fam]).items()))
            for fam in LEGACY}


def _load(path=None):
    with io.open(path or BASELINE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _base_files(doc):
    fams = doc.get("families") or {}
    return {fam: dict((fams.get(fam) or {}).get("files") or {}) for fam in LEGACY}


def _baseline_or_fail():
    assert os.path.exists(BASELINE_PATH), (
        u"⛔ 基线档缺（%s）⇒ 判据无据。请以本器**现取**（⛔ 手造）：\n"
        u"    python -X utf8 -B tests/unit/test_repo_no_personal_traces.py --write"
        % os.path.relpath(BASELINE_PATH, ROOT))
    doc = _load()
    assert doc.get("schema") == SCHEMA, u"⛔ 基线之 schema ⛔ 符：%r" % doc.get("schema")
    return _base_files(doc)


def _diff(base, now):
    u"""还 (新／增, 陈旧／减) —— 逐件比（⛔ 比族之总 · 尺之改即此）。"""
    add, sub = [], []
    for fam in LEGACY:
        b, n = base.get(fam, {}), now.get(fam, {})
        for rel in sorted(set(b) | set(n)):
            if n.get(rel, 0) == b.get(rel, 0):
                continue
            line = u"%s ｜ %s：%d ⇒ %d" % (fam, rel, b.get(rel, 0), n.get(rel, 0))
            (add if n.get(rel, 0) > b.get(rel, 0) else sub).append(line)
    return add, sub


def _spots(spec, got=None):
    u"""spec（`族 ｜ rel`）⇒ 其件之首三处（照实 —— 供判「是否属运行 ／ 组织所必需」）。"""
    got = _got() if got is None else got
    fam, _sep, rel = spec.partition(u" ｜ ")
    return [u"%s:%d  %s" % (r, i, t) for r, i, t in got.get(fam, []) if r == rel][:3]


def test_仓内无个人痕():
    u"""旧名保留为锚（PM 2054 ／ CW 2050 皆引此 nodeid）—— 其义今 ＝ **HARD ＝ 0**（真 PII）。
    旧属此齿之 LEGACY 一族（「族之总 ＝ 基」）⇒ 已拆为 test_旧痕逐件符基 ／ test_基线无陈旧条目。"""
    got = _got()
    bad = [k for k in HARD if got[k]]
    assert not bad, (u"⛔ 硬 PII 入仓：%s\n" % u"、".join(bad)
                     + u"\n".join(u"  %s:%d  %s" % t for k in bad for t in got[k][:8]))


def test_旧痕逐件符基():
    u"""新件 ／ 件内之增 ＝ 红（⛔ 静增）—— 逐件比，红时唯指其件。"""
    got = _got()
    add, _sub = _diff(_baseline_or_fail(), ledger(got=got))
    assert not add, (
        u"⛔ 旧痕有新增件 ／ 件内之增（%d 条）—— 逐条：\n    %s\n"
        u"  其件之处（照实 · 判其是否「运行 ／ 组织版所必需」）：\n%s\n"
        u"  若为正当 ⇒ 请以本器**现取**改基（⛔ 手抄 ／ ⛔ 静增）：\n"
        u"    python -X utf8 -B tests/unit/test_repo_no_personal_traces.py --write\n"
        u"  若不正当 ⇒ 清其痕（真 PII ⇒ 归 HARD · 须 ＝ 0）。"
        % (len(add), u"\n    ".join(add),
           u"\n".join(u"    %s ⇒ %s" % (a, u" ／ ".join(_spots(a, got)) or u"（⛔ 见）")
                     for a in add)))


def test_基线无陈旧条目():
    u"""陈旧 ＝ 红：条目已 ⛔ 复现而仍留 ⇒ 基线成了噪声掩体（一处定形：清了就并降基）。"""
    got = _got()
    _add, sub = _diff(_baseline_or_fail(), ledger(got=got))
    assert not sub, (
        u"⛔ 基线有陈旧条目（%d 条）—— 已 ⛔ 复现（件去 ／ 痕清）而条目仍留：\n    %s\n"
        u"  请以本器**现取**改基（一处定形）：\n"
        u"    python -X utf8 -B tests/unit/test_repo_no_personal_traces.py --write"
        % (len(sub), u"\n    ".join(sub)))


def test_判据非空转():
    u"""扫描量之下限（防判据静默空转 —— `git ls-files` 若失手则命中同为 0）。"""
    tracked = _tracked(ROOT)
    hits = sum(len(v) for v in _got().values())
    assert len(tracked) >= 3000, u"扫描件数过少 ⇒ 判据可能空转：%d" % len(tracked)
    assert hits >= 150, u"命中处过少 ⇒ 判据可能空转：%d" % hits


def _cli(argv):
    got = _got()
    now = ledger(got=got)
    base = _base_files(_load()) if os.path.exists(BASELINE_PATH) else {fam: {} for fam in LEGACY}
    add, sub = _diff(base, now)
    print(u"[旧痕·逐件] 族之总：%s"
          % u"  ".join(u"%s=%d" % (f, sum(now[f].values())) for f in LEGACY))
    print(u"[旧痕·逐件] 件数：%s" % u"  ".join(u"%s=%d" % (f, len(now[f])) for f in LEGACY))
    print(u"[旧痕·逐件] 新／增 %d 条：%s" % (len(add), u" ／ ".join(add) or u"无"))
    print(u"[旧痕·逐件] 陈旧／减 %d 条：%s" % (len(sub), u" ／ ".join(sub) or u"无"))
    if u"--write" not in argv:
        print(u"（⛔ 未落盘 · 加 --write 方以今之树**现取**改基）")
        return 0
    doc = {
        "schema": SCHEMA,
        "policy": POLICY,
        "note": NOTE,
        "updated": time.strftime("%Y-%m-%d"),
        "decision_ref": DECISION_REF,
        "scan": u"git ls-files（tracked · 全仓 · ⛔ 跳二进制）",
        "hard_must_be": 0,
        "families": {fam: {"由": FAMILY_WHY[fam], "files": now[fam]} for fam in LEGACY},
    }
    d = os.path.dirname(BASELINE_PATH)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with io.open(BASELINE_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(doc, ensure_ascii=False, indent=2) + u"\n")
    print(u"[改基] 已以今之树**现取**落盘：%s" % os.path.relpath(BASELINE_PATH, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
