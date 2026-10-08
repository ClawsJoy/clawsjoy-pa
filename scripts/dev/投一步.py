# -*- coding: utf-8 -*-
r"""投一步.py —— 件-投-醒 一步之器（落箱 ＋ 落行 ＋ 醒 · ⭐ 一处收三步）。

承：pm 1291 §四（**专批** · 令）｜pm 1290 §四（债一：件/投/醒 三步之原子性 · 「醒」之败须有显报）｜
    pm 1094 之照实（「1093」之 wake 未成 ⇒ send_receipts.jsonl hits 0 ⇒ 静默之病）。

其病（今）：写件 ／ 落行 ／ 醒 三步各手序 ⇒ 「醒」若败 ⇒ **静默**（唯靠对方复扫）。
本器：三步一处；⭐ **醒败返非零 ＋ 印书名 ＋ 印席 ＋ 印凭**（⛔ 静默）。

用法：
  python -X utf8 -B scripts\dev\投一步.py --src <草稿全路径> --to 项目经理 --num 1096 \
      --from 技术总监 --cat 报 --need X --note Y   # 默认 **演**（⛔ 落盘）；⭐ --from **必填**
  （加 --go ⇒ 真办：落箱 ＋ 落行 ＋ 醒）
  python -X utf8 -B scripts\dev\投一步.py --self-test   # 自证（含 **反控**：醒必败 ⇒ 须返非零）
  ⚠ 席名（2026-10-06 承 pm 1294 §三 · 并收 ／ pm 1298 §二 · 落账归一）：CW 席之**台账名** ＝ 「CodexWindows线」
    （⛔ SEATS 之「V9工程师·全史席」）⇒ 二键并存（**别名只作「入」** ⇒ 投 CW 之件免 --to-id）
    ⇒ ⭐⭐ **落行须归一为台账之名**（CANON：V9工程师·全史席 ⇒ CodexWindows线）⇒ ⛔ 别名入账。
  ⭐ `--from` **必填**（2026-10-08 承 pm_1844 §二.3 · CW 1842 之呈）：原默认「技术总监」⇒ 忘传则**静默误归**
    （「空 ⛔ 混 缺」之族 ∧ 归因错即台账之根病）⇒ ⛔ 采「自件名推」（名 ／ 账 ⛔ 必同源）⇒ 缺则 rc 2 ＋ 显报「席名 ⛔ 给」。

退出码：0 = 三步皆成（演毕亦然）｜2 = 用法错｜3 = 草稿不在｜4 = 落箱败（BOM ／ CR ／ 件之完 ／ 箱内异）
        ｜5 = 落行败（透传其 rc）｜6 = 已落行（复合键在 ⇒ ⛔ 复落）｜7 = **醒败**｜8 = 已投（凭在 ⇒ ⛔ 复投）
        ｜9 = **号撞**（本日之号面 ⇒ 拒投 ＋ 荐空号 · 承 pm_1889 §三 ／ pm_1894 §一）

界：⭐ 本器唯「编排」三步（⛔ 自撰字面 ／ ⛔ 自裁）；其三步之闸各归其器（落台账_行 ／ wake_send）。
"""
import argparse
import csv as csvmod
import datetime
import hashlib
import io
import json
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

XT = r"D:\Obsidian\ClawsJoy\ClawsJoy\内容工坊\02_协作\信通"
CSV = os.path.join(XT, u"投递台账.csv")
LAND = r"D:\Obsidian\ClawsJoy\ClawsJoy\内容工坊\08_工具\落台账_行.py"
WAKE = r"D:\paseo-workspace\_tools\wake_send.py"
RECEIPTS = r"D:\paseo-workspace\_tools\_data\send_receipts.jsonl"

SEATS = {
    u"项目经理": "b136893",
    u"技术总监": "f202f89",
    u"V9工程师·全史席": "b2a5182",
    # 2026-10-06 承 pm 1294 §三（**核而并收** · 二名一事）：台账内 CW 席之名 ≡ 「CodexWindows线」
    # （我一手核 · 全 1,540 行：发件 384 ／ 收件 78 ／ 全册 ⛔ 见「V9工程师·全史席」）。
    # ⇒ 并收为**别名键**（**台账之名为准** ⇒ 投 CW 之件免 --to-id · ⛔ 二名致误）。
    u"CodexWindows线": "b2a5182",
}

# 2026-10-06 承 pm 1298 §二（**落账归一**）｜pm 1302 §四.2（令）：
# 别名只作「入」⇒ **落行之 recv 须归一为台账之名**（⛔ 二名入账 ⇒ 扫 CW 之件必漏）。
CANON = {
    u"V9工程师·全史席": u"CodexWindows线",
}


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def now_ts():
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S") + "+08:00"


def now_date():
    return datetime.date.today().strftime("%Y-%m-%d")


def _load_proc():
    u"""按**文件路径**载「窗隐唯一出口」之真源（`core/pa/_proc.py`）⇒ 模块 ∨ None。

    ⚠ ⛔ 走 `from core.lib import _proc`：那会执行 `core/__init__.py`（拉 `chromadb` 之族）
      ⇒ 每次投递多 ~1.5 s ∧ 无谓副作用（承 `core/lib/_proc.py` 自述之由）。
      真源唯依赖 `subprocess` ⇒ 按路径载 ＝ **零副作用 ／ 零环 ／ 仍单源**。
    """
    import importlib.util
    p = os.environ.get("CJ_PROC_PY") or r"D:\clawsjoy_v9\core\pa\_proc.py"
    if not os.path.isfile(p):
        print(u"⚠ 窗隐真源不可载（%s）⇒ 退朴素形（仍并 CREATE_NO_WINDOW）" % p)
        return None
    spec = importlib.util.spec_from_file_location("_cj_proc", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_PROC = _load_proc()


def run(cmd):
    u"""跑一条外部命令 ⇒ `(rc, out)`。

    ⭐⭐ pm_1793 §二.1（**窗隐**）：昔为**裸** `subprocess.run` —— 未带 `CREATE_NO_WINDOW`
      ⇒ 本器每次投递起 3~4 个**控制台程序**（`落台账_行` ／ `wake_send` ／ `send_receipt_log`
      皆 `python.exe`）⇒ 每个弹一个控制台窗（`conhost`）＝ 老板所报「投递一闪」之一源。
      ⇒ 今唯走**窗隐唯一出口**（`run_hidden` ⇒ 并 `CREATE_NO_WINDOW`）。
    """
    if _PROC is not None:
        r = _PROC.run_hidden(cmd, capture_output=True, text=True,
                             encoding="utf-8", errors="replace")
    else:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace",
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return r.returncode, (r.stdout or "") + (r.stderr or "")


# ------------------------------------------------ 件之完（闸一 ／ 二 ／ 三 · 承 pm 1294 §二 ／ pm 1298 §三）
HAN = u"一二三四五六七八九十"
SUSPECT_TAIL = (u"（", u"(", u"[", u"：", u":", u"，", u",", u"、", u"＋", u"｜", u"——", u"「", u"/", u"-")


def han_to_int(s):
    u"""汉字数 ⇒ 整数（唯及「十」· 本族之节号 ⛔ 越十）⇒ 失败 ⇒ None。"""
    if not s:
        return None
    if len(s) == 1:
        return HAN.index(s) + 1 if s in HAN else None
    if s[0] == u"十" and len(s) == 2 and s[1] in HAN:
        return 10 + HAN.index(s[1]) + 1
    if len(s) == 2 and s[1] == u"十" and s[0] in HAN:
        return (HAN.index(s[0]) + 1) * 10
    return None


def front_matter(text):
    u"""取 front matter 之行（⛔ 含二界之 ---）⇒ list ∨ None。"""
    lines = text.split("\n")
    if not lines or lines[0].strip() != u"---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == u"---":
            return lines[1:i]
    return None


FM_FIELD = re.compile(u"^([A-Za-z_\u4e00-\u9fff\u00b7][^:]*):[ \t]?(.*)$")


def fm_field(fm, name):
    u"""front matter 之某字段 ⇒ 其值（含续行 · 以空格联）∨ 空串。"""
    out, on = u"", False
    for l in (fm or []):
        m = FM_FIELD.match(l)
        if m:
            on = (m.group(1).strip() == name)
            if on:
                out = m.group(2)
            continue
        if on and l.strip():
            out = (out + u" " + l.strip()).strip()
    return out


#: 需求动作之字段名（**一处并收** —— pm_1835 §二.2 之令 ＋ pm_1837 §二.1 · 技术总监 f202f89）：
#   本族**二名并存**（一手扫 `02_协作\信通` 之 2107 件：「动作需求」1656 ／「需求动作」193 ／ 二者皆有 0）
#   ⇒ 器**认二名**（同 SEATS 别名 ／ CANON 之族 · 一处并收）；
#   ⚠ 唯认一名 ⇒ 其一名之件之**闸一静默过**（＝器之绿 ⛔ 充事之实 · 一手之正反控见 --self-test）。
NEED_FIELDS = (u"动作需求", u"需求动作")


def promised_sections(fm):
    u"""「动作需求」之 §〈汉字数〉 ⇒ (集, 所取之列逐字) —— ⚠ **唯取本字段** ∧ **§ 须紧接「（」**
    （承 pm 1298 §三.1 之剔法 ＋ 实探）：本族之诺之形 ≡ （§三）／（§一 · 器取）；
    ⛔ 取他件之引（如 §五.⒊ 之界 ／ pm 1294 §三 ⇒ 实：1222 ／ 1253 之假红）；
    ⛔ 取变体（如（器取逐行 · §一）⇒ 宁漏 ⛔ 假红）。
    ⭐ 字段名**认二名**（`NEED_FIELDS` —— pm_1835 §二.2 ／ pm_1837 §二.1 · 一手：1656 ／ 193）。"""
    f = u""
    for _nf in NEED_FIELDS:
        f = fm_field(fm, _nf)
        if f:
            break
    got = set()
    for m in re.finditer(u"（§[ \t]*([%s]+)" % HAN, f):
        n = han_to_int(m.group(1))
        if n:
            got.add(n)
    return got, f


def heading_sections(text):
    u"""节标题之汉字数集（## 三 ／ ### 三 ／ ## §三 任一体 —— 承 pm 1294 §二）。"""
    got = set()
    for m in re.finditer(u"(?m)^#{2,4}[ \t]*§?[ \t]*([%s]+)(?=[ \t\u3000\u00b7\uff1a\uff0f\uff09]|$)" % HAN, text):
        n = han_to_int(m.group(1))
        if n:
            got.add(n)
    return got


def int_to_han(n):
    return HAN[n - 1] if 1 <= n <= len(HAN) else str(n)


def last_nonblank(text):
    for l in reversed(text.split("\n")):
        if l.strip():
            return l
    return u""


def body_gate(b, text, name):
    u"""件之完（闸一 ／ 二 ／ 三）⇒ (rc, 报) ∨ None（过）。"""
    want, field = promised_sections(front_matter(text))
    miss = sorted(n for n in want if n not in heading_sections(text))
    if miss:
        return 4, (u"落箱：⛔ 动作需求 诺之节 ⛔ 见其文（缺：%s）⇒ 疑截断（承 pm 1294 §二 闸一）"
                   u"｜所取之列逐字 ＝ %s ｜书名 ＝ %s"
                   % (u"／".join(u"§" + int_to_han(n) for n in miss), field, name))
    last = last_nonblank(text)
    if last.rstrip().endswith(SUSPECT_TAIL):
        return 4, (u"落箱：⛔ 末行疑截断（承 pm 1294 §二 闸二）｜末行逐字 ＝ %s ｜书名 ＝ %s"
                   % (last, name))
    if not last:
        return 4, u"落箱：⛔ 件为「空」（⛔ 无非空之行）｜书名 ＝ %s" % name
    if not b.endswith(b"\n"):
        return 4, u"落箱：⛔ 件无尾（末字节 ⛔ ＝ \\n）｜书名 ＝ %s" % name
    if not any(l.strip() for l in text.split("\n")[:3]):
        return 4, u"落箱：⛔ 件首三行皆空（疑残）｜书名 ＝ %s" % name
    return None


# ---------------------------------------------------------------- 落箱
def step_box(src, name, dry=False, box=XT):
    u"""落箱：草稿 ⇒ 箱（信通）。⭐ 硬闸：⛔ BOM ／ ⛔ CR（须 LF）／ **件之完（闸一／二／三 · 承 pm 1294 §二）**；箱内已同 ⇒ ⛔ 复写；异 ⇒ 拒。"""
    if not os.path.isfile(src):
        return 3, u"落箱：⛔ 草稿不在：%s" % src
    b = open(src, "rb").read()
    if b[:3] == b"\xef\xbb\xbf":
        return 4, u"落箱：⛔ 草稿带 BOM（信通之件须 ⛔ BOM）"
    if b"\r" in b:
        return 4, u"落箱：⛔ 草稿带 CR（信通之件须 LF）"
    try:
        _t = b.decode("utf-8")
    except Exception:
        return 4, u"落箱：⛔ 草稿 ⛔ 合 UTF-8（译码败）"
    _g = body_gate(b, _t, name)
    if _g:
        return _g
    dst = os.path.join(box, name)
    if os.path.isfile(dst):
        d = open(dst, "rb").read()
        if d == b:
            return 0, u"落箱：箱内已同 ⇒ ⛔ 复写（印 %s ／ %d B）" % (sha16(b), len(b))
        return 4, u"落箱：⛔ 箱内已存在而内容异（箱 %s / 草 %s）" % (sha16(d), sha16(b))
    if dry:
        return 0, u"落箱（演）：将写 %s ／ %d B ／ 印 %s" % (os.path.join(box, name), len(b), sha16(b))
    open(dst, "wb").write(b)
    back = open(dst, "rb").read()
    if sha16(back) != sha16(b):
        return 4, u"落箱：⛔ 回读不合（写 %s / 读 %s）" % (sha16(b), sha16(back))
    return 0, u"落箱：成 · %s ／ %d B ／ 印 %s" % (name, len(b), sha16(b))


# ---------------------------------------------------------------- 落行
def row_count(num, date, sender, cat, csv=CSV):
    rc, out = run([sys.executable, "-X", "utf8", "-B", LAND, "--csv", csv, "--check",
                   "--num", str(num), "--date", date, "--from", sender, "--cat", cat])
    m = re.search(u"复合键出现 (\\d+) 次", out)
    return (int(m.group(1)) if m else -1), out


def step_land(num, date, sender, recv, name, cat, need, note, ts, dry=False, csv=CSV, box=XT):
    u"""落行：落台账_行.py 之唯一写器。⭐ 闸前先核「复合键」⇒ ⛔ 复落。"""
    n, out = row_count(num, date, sender, cat, csv)
    if n > 0:
        return 6, u"落行：⛔ 复合键已在（%s / %s / %s / %s ⇒ %d 次）⇒ ⛔ 复落" % (num, date, sender, cat, n)
    if n < 0:
        return 5, u"落行：⛔ 查行未得判（⛔ 复落之闸不可用）"
    if not os.path.isfile(os.path.join(box, name)):
        if dry:
            return 0, u"落行（演·跳）：件未在箱 ⇒ ⛔ 得验（真办 --go 先落箱 ⇒ 方有验）"
        return 5, u"落行：⛔ 件不在箱 ⇒ 须先落箱（落台账_行 之入口闸）"
    cmd = [sys.executable, "-X", "utf8", "-B", LAND, "--csv", csv, "--num", str(num),
           "--date", date, "--from", sender, "--to", recv, "--file", name, "--cat", cat,
           "--need", need, "--note", note, "--ts", ts]
    if dry:
        cmd.append("--dry-run")
    rc, out = run(cmd)
    print(out.rstrip())
    if rc != 0:
        return 5, u"落行：败 rc=%s（见上之判红 / 入口错）" % rc
    return 0, u"落行：%s（rc 0）" % (u"演" if dry else u"成")


# ---------------------------------------------------------------- 醒
def receipt_of(name, path=RECEIPTS):
    if not os.path.isfile(path):
        return None
    for line in io.open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        if o.get(u"件") == name and str(o.get("rc")) == "0":
            return o
    return None


def _wake_run(cmd, name, tid):
    u"""醒之核：⭐ 返非零则 **显报**（书名 ＋ 席 ＋ 凭）。"""
    rc, out = run(cmd)
    print(out.rstrip())
    if rc != 0:
        return rc, (u"醒：⭐败 rc=%s ⇒ 书名 ＝ %s ／ 席 ＝ %s ／ 凭 ＝ %s"
                    % (rc, name, tid, out.strip()[-240:] or u"（空）"))
    return 0, u"醒：成 rc=0"


def step_wake(name, tid, dry=False):
    u"""醒：wake_send.py（其自带「首成即停」＋ 自动登记）。⭐ 凭在 ⇒ ⛔ 复投。"""
    o = receipt_of(name)
    if o is not None:
        return 8, u"醒：⛔ 已投（凭据在 · rc 0 · 刻 %s）⇒ ⛔ 复投" % o.get(u"凭据登入刻", u"?")
    if dry and not os.path.isfile(os.path.join(XT, name)):
        return 0, u"醒（演·跳）：件未在箱 ⇒ ⛔ 得验（真办 --go 先落箱 ⇒ 方有验）"
    cmd = [sys.executable, "-X", "utf8", "-B", WAKE, "--to", tid, "--file", os.path.join(XT, name)]
    if not dry:
        cmd.append("--send")
    rc, msg = _wake_run(cmd, name, tid)
    if rc != 0:
        return 7, msg
    if not dry and receipt_of(name) is None:
        return 0, (u"醒：成 rc=0 ｜ ⚠⚠ 醒成而凭未登 ⇒ **须补登**（⛔ 复投 —— 复投即重送）"
                   u" ／ 书名 ＝ " + name)
    return 0, msg


# ---------------------------------------------------------------- 自证
def selftest():
    u"""自证 ⇒ rc（0 ／ 1）· ⭐ temp **自清**（承 `make_setup.py` 之族：唯自测之 temp 清理 · ⛔ 删产物）。"""
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix="tou1_")
    try:
        return _selftest_body(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _selftest_body(tmp):
    ok = True

    def res(name, got, want):
        nonlocal ok
        hit = (got == want)
        ok = ok and hit
        print(u"  %s %s ⇒ %s（期 %s）" % (u"OK " if hit else u"✗ ", name, got, want))

    good = os.path.join(tmp, "a.md")
    open(good, "wb").write(u"# 甲\n正文\n".encode("utf-8"))
    bom = os.path.join(tmp, "b.md")
    open(bom, "wb").write(b"\xef\xbb\xbf" + u"# 甲\n".encode("utf-8"))
    crlf = os.path.join(tmp, "c.md")
    open(crlf, "wb").write(b"# x\r\n")
    box = os.path.join(tmp, "box")
    os.makedirs(box)

    print(u"[自证 1 落箱 · 正控]")
    rc, _ = step_box(good, "a.md", dry=False, box=box)
    res(u"合规之草 ⇒ 0", rc, 0)
    rc, m = step_box(good, "a.md", dry=False, box=box)
    res(u"已同 ⇒ 0（⛔ 复写）", rc, 0)
    print(u"[自证 2 落箱 · 反控（⛔ 须非零 · 且其因可指）]")
    rc, m = step_box(bom, "b.md", dry=False, box=box)
    res(u"BOM 之草 ⇒ 4", rc, 4)
    print(u"    其报：" + m)
    rc, m = step_box(crlf, "c.md", dry=False, box=box)
    res(u"CR 之草 ⇒ 4", rc, 4)
    print(u"    其报：" + m)
    rc, m = step_box(os.path.join(tmp, "无此件.md"), "x.md", dry=False, box=box)
    res(u"草不在 ⇒ 3", rc, 3)

    print(u"[自证 4 落箱 · 件之完之反控三（承 pm 1294 §二 ／ pm 1298 §三）]")
    lack = os.path.join(tmp, "d.md")
    open(lack, "wb").write(u"---\ntype: 报\ndate: 2026-10-06\n动作需求: 办一（§一）／ 办六（§六）\n---\n\n## 一 甲\n\n正文\n".encode("utf-8"))
    rc, m = step_box(lack, "d.md", dry=False, box=box)
    res(u"缺节（诺 §一／§六 · 其文唯 §一）⇒ 4", rc, 4)
    print(u"    其报：" + m)
    hit = (u"§六" in m) and (u"动作需求" in m)
    print(u"  %s 其报含「所缺之节号逐字 ＋ 所取之列逐字」" % (u"OK " if hit else u"✗ "))
    ok = ok and hit
    # ⭐ 2026-10-08（pm_1835 §二.2 ／ pm_1837 §二.1）：**二名皆须触发闸一**（正控）∧ **缺名 ⇒ 仍过**（反控）
    lack2 = os.path.join(tmp, "d2.md")
    open(lack2, "wb").write(u"---\ntype: 报\ndate: 2026-10-08\n需求动作: 办一（§一）／ 办六（§六）\n---\n\n## 一 甲\n\n正文\n".encode("utf-8"))
    rc, m = step_box(lack2, "d2.md", dry=False, box=box)
    res(u"二名之正控（需求动作 诺 §一／§六 · 其文唯 §一）⇒ 4", rc, 4)
    print(u"    其报：" + m)
    hit = (u"§六" in m)
    print(u"  %s 其报含「所缺之节号逐字」" % (u"OK " if hit else u"✗ "))
    ok = ok and hit
    noname = os.path.join(tmp, "d3.md")
    open(noname, "wb").write(u"---\ntype: 报\ndate: 2026-10-08\n---\n\n## 一 甲\n\n正文\n".encode("utf-8"))
    rc, m = step_box(noname, "d3.md", dry=False, box=box)
    res(u"二名之反控（⛔ 该字段 ⇒ 无为而治 · 须 0）", rc, 0)
    susp = os.path.join(tmp, "e.md")
    open(susp, "wb").write(u"# 甲\n正文（\n".encode("utf-8"))
    rc, m = step_box(susp, "e.md", dry=False, box=box)
    res(u"末悬（末行 ＝「正文（」）⇒ 4", rc, 4)
    hit = (u"正文（" in m)
    print(u"  %s 其报含「末行逐字」" % (u"OK " if hit else u"✗ "))
    ok = ok and hit
    blank = os.path.join(tmp, "f.md")
    open(blank, "wb").write(b"\n")
    rc, m = step_box(blank, "f.md", dry=False, box=box)
    res(u"空件（唯 \\n）⇒ 4", rc, 4)
    print(u"    其报：" + m)
    notail = os.path.join(tmp, "g.md")
    open(notail, "wb").write(u"# 甲\n正文".encode("utf-8"))
    rc, m = step_box(notail, "g.md", dry=False, box=box)
    res(u"无尾（末字节 ⛔ ＝ \\n）⇒ 4", rc, 4)

    print(u"[自证 3 醒 · 正控 / 反控（承 pm 1291 §四：反控须证其可达「非零」）]")
    z = [sys.executable, "-c", "import sys; sys.exit(0)"]
    f = [sys.executable, "-c", "import sys; print('STUB-WAKE-FAIL'); sys.exit(7)"]
    rc, m = _wake_run(z, "件甲.md", "b136893")
    res(u"stub rc0 ⇒ 0", rc, 0)
    rc, m = _wake_run(f, "件甲.md", "b136893")
    res(u"stub rc7 ⇒ 7", rc, 7)
    hit = (u"件甲.md" in m) and (u"b136893" in m) and (u"STUB-WAKE-FAIL" in m)
    print(u"  %s 显报含「书名 ＋ 席 ＋ 凭」 ⇒ %s" % (u"OK " if hit else u"✗ ", m))
    ok = ok and hit

    print(u"[自证 5 席名归一（承 pm 1298 §二 ／ pm 1302 §四.2 · 别名 ⛔ 入账）]")
    res(u"SEATS 二键 ⇔ 同 id（别名只作入）", SEATS.get(u"V9工程师·全史席") == SEATS.get(u"CodexWindows线"), True)
    res(u"CANON 归一台账之名", CANON.get(u"V9工程师·全史席"), u"CodexWindows线")
    res(u"CANON 幂等", CANON.get(u"CodexWindows线", u"CodexWindows线"), u"CodexWindows线")

    print(u"[自证 6 席名必填（承 pm_1844 §二.3 · 静默之默认 ＝ 误归）]")
    rc_n, m_n = check_sender(None)
    res(u"⛔ --from（None）⇒ 2", rc_n, 2)
    print(u"    其报：" + m_n)
    res(u"其报含「席名 ⛔ 给」逐字", (u"席名 ⛔ 给" in m_n), True)
    res(u"--from ＝ 空白 ⇒ 2", check_sender(u"   ")[0], 2)
    res(u"明书席名 ⇒ 0（反控 · 可达零）", check_sender(u"技术总监")[0], 0)
    print(u"[自证 7 号撞（承 pm_1889 §三 ／ pm_1894 §一 · ⭐ 逐字 ＋ 幂等 ＋ 荐号真可用）]")
    _tb = os.path.join(tmp, "box2")
    os.makedirs(_tb)
    _tc = os.path.join(tmp, "led.csv")
    _d = now_date()
    io.open(_tc, "w", encoding="utf-8").write(
        u"序号,日期,发件,收件,文件名,类别,状态,动作需求,回执件,备注,时点\n"
        + (u"1888,%s,项目经理,技术总监,_令_TD_1888.md,令,open,x,,,2026-10-08T07:00:00+08:00\n" % _d)
        + (u"1889,%s,项目经理,技术总监,_补_TD_1889.md,补,open,x,,,2026-10-08T07:01:00+08:00\n" % _d))
    io.open(os.path.join(_tb, u"_报_CW_1890.md"), "w", encoding="utf-8").write(u"x\n")
    _u = day_numbers(_d, csv=_tc, box=_tb)
    res(u"号面二源并取（台账 2 ＋ 箱 1 ⇒ %s）" % sorted(_u), sorted(_u), [1888, 1889, 1890])
    rc, m = check_number(1889, _d, u"技术总监", u"_报_TD_1899.md", box=_tb, csv=_tc)
    res(u"反控：撞（异席之号）⇒ 9", rc, 9)
    print(u"    其报：" + m.replace(u"\n", u" ／ "))
    res(u"逐字 ⒜ 撞谁", (u"撞号：1889 已被 项目经理（2026-10-08T07:01:00+08:00 · _补_TD_1889.md）占用" in m), True)
    res(u"逐字 ⒝ 荐一空号：1891", (u"荐一空号：1891" in m), True)
    res(u"逐字 ⒞ 本日之号面", (u"本日之号面（近十）：" in m), True)
    _c = int(re.search(u"荐一空号：([0-9]+)", m).group(1))
    res(u"荐号**真可用**（不在号面）", (_c not in _u), True)
    res(u"⛔ 静默改号（报 ⛔ 含「已改」）", (u"已改" in m), False)
    rc, m = check_number(1888, _d, u"技术总监", u"_令_TD_1888.md", box=_tb, csv=_tc)
    res(u"幂等：同席 ＋ 同件名 ⇒ 0（复投之径）", rc, 0)
    rc, m = check_number(1877, _d, u"技术总监", u"_报_TD_1877.md", box=_tb, csv=_tc)
    res(u"正控：未用之号 ⇒ 0", rc, 0)
    rc, m = check_number(1890, _d, u"技术总监", u"_报_TD_1895.md", box=_tb, csv=_tc)
    res(u"反控：箱内之号（账未及）亦算撞 ⇒ 9", rc, 9)
    print(u"[总判] %s" % (u"PASS" if ok else u"FAIL"))
    return 0 if ok else 1


#: 席名之检（承 pm_1844 §二.3）：⛔ 默认值 ⇒ 忘传即**静默误归** ⇒ 缺则 rc 2 ＋ 显报。
def check_sender(sender):
    u"""席名 ⛔ 给 ⇒ (2, 显报)。⭐ ⛔ 采「自件名推」（名 ／ 账 ⛔ 必同源）
    —— 承 pm_1844 §二.3（静默之默认 ＝ 误归 · CW 1842 即中招）⇒ 唯明书。"""
    if (sender or u"").strip():
        return 0, u"席名 ＝ %s" % sender.strip()
    return 2, (u"席名 ⛔ 给（--from）⇒ 静默之默认 ＝ 误归（承 pm_1844 §二.3 · CW 1842 即中招）"
               u"｜表：%s" % u" ／ ".join(sorted(SEATS)))


# ------------------------------------------------ 号之面（承 pm_1889 §三 ／ pm_1894 §一）

#: 件名之尾号（`_报_TD_1884.md` ⇒ 1884 · 承 pm_1889 §三）
NUM_TAIL = re.compile(u"_([0-9]{3,4})[.]md$")


def day_numbers(date, csv=CSV, box=XT):
    u"""本日各席**已用**之号 ⇒ {号: [(席, 件名, 刻, 源)]}（**二源并取** · 承 pm_1889 §三 ／ pm_1894 §一.1⒞）。

    ⭐ 「预扫 ⛔ 足」：预扫与落箱之间有窗 —— 一手之真场景：pm 令 `1880` ts `07:22:43`
      ∧ CW 报 `1880` ts `07:22:58` ⇒ 15 s 之窗 ⇒ ⭐ **唯落箱之刻为准**。
    ① **台账**（`投递台账.csv` · 日期 ∧ 序号 ∧ 发件 ＋ 文件名 ＋ 时点）＝ 已入账者；
    ② **箱**（本日 mtime ∧ 名尾 `_<号>.md`）＝ 已落箱而账未及者（他席并发之行中）。
    ⭐ 二源**须并取**（任一漏 ⇒ 拒投失守 —— 与「两数须同源」之律同族 · 此处之「源」＝ 落箱那一瞬）。
    """
    used = {}
    try:
        with io.open(csv, encoding="utf-8-sig", newline=u"") as f:
            for r in csvmod.DictReader(f):
                if (r.get(u"日期") or u"").strip() != date:
                    continue
                _n = (r.get(u"序号") or u"").strip()
                if not _n.isdigit():
                    continue
                used.setdefault(int(_n), []).append(
                    ((r.get(u"发件") or u"").strip(), (r.get(u"文件名") or u"").strip(),
                     (r.get(u"时点") or u"").strip(), u"台账"))
    except Exception as _e:
        print(u"⚠ 台账 ⛔ 读（%s）⇒ 号之面唯见箱（照实 · ⛔ 静默）" % type(_e).__name__)
    try:
        for fn in os.listdir(box):
            m = NUM_TAIL.search(fn)
            if not m:
                continue
            fp = os.path.join(box, fn)
            try:
                _dt = datetime.datetime.fromtimestamp(os.path.getmtime(fp))
            except Exception:
                continue
            if _dt.strftime(u"%Y-%m-%d") != date:
                continue
            _n = int(m.group(1))
            if any(_x[1] == fn for _x in used.get(_n, [])):
                continue
            used.setdefault(_n, []).append((u"?（箱内 · 席待账）", fn,
                                            _dt.strftime(u"%H:%M:%S"), u"箱"))
    except Exception as _e:
        print(u"⚠ 箱 ⛔ 读（%s）⇒ 号之面唯见台账（照实 · ⛔ 静默）" % type(_e).__name__)
    return used


def num_face(used, upto=10):
    u"""本日之号面 ⇒ 一行（近 `upto` 号 ＋ 各席用之者 · 降序 · 承 pm_1894 §一.1⒞）。"""
    _ns = sorted(used, reverse=True)[:upto]
    if not _ns:
        return u"（本日 0 号）"
    _out = []
    for n in _ns:
        _seats = []
        for _x in used[n]:
            _k = u"%s%s" % (_x[0], u"" if _x[3] == u"台账" else u"/箱")
            if _k not in _seats:
                _seats.append(_k)
        _out.append(u"%d(%s)" % (n, u"∧".join(_seats)))
    return u" ｜ ".join(_out)


def check_number(num, date, sender, name, box=XT, csv=CSV, used=None):
    u"""落箱之刻**复核号**（承 pm_1889 §三 ／ pm_1894 §一）⇒ (rc, 报)。

    撞 ⇒ (9, 三事逐字：撞谁 ＋ 荐一空号 ＋ 本日之号面)｜⛔ 撞 ⇒ (0, 空串)。
    ⭐ 幂等：**同件名**之号 ⛔ 算撞（＝复投之径 · 免得「拒投之后 ⛔ 得复投」）；
      件名内嵌发件席（`_报_TD_1884.md` 族）⇒ 件名同 ⇒ 同席同件。
    ⛔ 静默改号 ／ ⛔ 代改（唯报 ＋ 荐 —— 承 pm_1894 §一.2）。
    """
    try:
        _n = int(num)
    except Exception:
        return 0, u""
    if used is None:
        used = day_numbers(date, csv, box)
    _others = [_x for _x in used.get(_n, []) if _x[1] != name]
    if not _others:
        return 0, u""
    _lines = [u"撞号：%d 已被 %s（%s · %s）占用" % (_n, _x[0], _x[2] or u"刻未记", _x[1])
              for _x in _others]
    _cand = (max(used) + 1) if used else 1
    while _cand in used:
        _cand += 1
    _lines.append(u"荐一空号：%d（本日极大 %d ＋ 1 · 已复核不在本日号面）"
                  % (_cand, max(used) if used else 0))
    _lines.append(u"本日之号面（近十）：" + num_face(used))
    return 9, u"\n".join(_lines)

# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--self-test", dest="selftest", action="store_true")
    ap.add_argument("--src")
    ap.add_argument("--name")
    ap.add_argument("--to")
    ap.add_argument("--to-id")
    # ⭐ `--from` 改**必填**（承 pm_1844 §二.3）：原 default ＝ 「技术总监」⇒ 忘传则静默误归
    #   （CW 1842 即中招）⇒ ⛔ 默认（「空 ⛔ 混 缺」）∧ ⛔ 自件名推（名 ／ 账 ⛔ 必同源）。
    ap.add_argument("--from", dest="sender")
    ap.add_argument("--num")
    ap.add_argument("--date")
    ap.add_argument("--cat", default=u"报")
    ap.add_argument("--need", default=u"")
    ap.add_argument("--note", default=u"")
    ap.add_argument("--ts", default=u"")
    ap.add_argument("--go", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not (a.src and a.to and a.num):
        print(u"[用法错] 须 --src ／ --to ／ --num（rc=2）")
        return 2
    rc_s, msg_s = check_sender(a.sender)
    if rc_s != 0:
        print(u"[用法错] " + msg_s)
        return rc_s
    tid = a.to_id or SEATS.get(a.to)
    if not tid:
        print(u"[用法错] 席位「%s」⛔ 在表 ⇒ 以 --to-id 明书（rc=2）｜表：%s"
              % (a.to, u" ／ ".join(sorted(SEATS))))
        return 2
    recv = CANON.get(a.to, a.to)
    name = a.name or os.path.basename(a.src)
    date = a.date or now_date()
    ts = a.ts or now_ts()
    dry = not a.go
    print(u"【投一步】%s ｜ 件 ＝ %s ｜ 席 ＝ %s（%s）｜ 号 ＝ %s ／ 日 ＝ %s ／ 类 ＝ %s"
          % (u"演（⛔ 落盘 · 加 --go 真办）" if dry else u"真办", name, a.to, tid, a.num, date, a.cat))
    if recv != a.to:
        print(u"落账之名（归一）＝ %s（别名「%s」唯作入 · ⛔ 入账 · 承 pm 1298 §二）" % (recv, a.to))
    print(u"刻（器取）＝ %s ／ 箱 ＝ %s" % (ts, XT))
    _used_n = day_numbers(date)
    _rc_n, _msg_n = check_number(a.num, date, a.sender, name, used=_used_n)
    if _rc_n != 0:
        print(u"[号撞] " + _msg_n)
        print(u"[止] 号 ⛔ 可用 ⇒ **拒投**（承 pm_1889 §三 ／ pm_1894 §一 · ⛔ 静默改号 ／ ⛔ 代改）｜rc=%s" % _rc_n)
        return _rc_n
    print(u"本日之号面（近十）＝ %s" % num_face(_used_n))
    skipped = []
    for label, fn in ((u"① 落箱", lambda: step_box(a.src, name, dry=dry)),
                      (u"② 落行", lambda: step_land(a.num, date, a.sender, recv, name, a.cat,
                                                     a.need, a.note, ts, dry=dry)),
                      (u"③ 醒", lambda: step_wake(name, tid, dry=dry))):
        rc, msg = fn()
        print(u"%s ⇒ %s" % (label, msg))
        if u"演·跳" in msg:
            skipped.append(label)
        if rc != 0:
            print(u"[止] %s 不合 ⇒ ⛔ 续跑（三步须一处断）｜rc=%s" % (label, rc))
            return rc
    if skipped:
        print(u"[总判] 演毕（rc 0 · ⚠ %s ⛔ 得验：件未在箱 ⇒ 真办方验）" % u"／".join(skipped))
    else:
        print(u"[总判] 三步皆成（rc 0 · %s）" % (u"演" if dry else u"真办"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
