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
  ⭐ 探针一口（2026-10-11 · 承 CEO 令 第⑤件 · PM 2740）：--box <径> ／ --csv <径> ／
    --lock <径> ⇒ 覆模块常量 XT ／ CSV ⇒ **隔离面**（俾「二进程真并发」之反例门可跑）；
    ⚠ 三守则：⒜ **锁件随面而移**（默认 ＝ <箱>/.号锁 ∨ --lock 显覆）⒝ **隔离面 ⇒ ⛔ 真醒**
    （唯印一行 · ⛔ 实发）⒞ **验毕清面**（临时箱 ／ 台账 ／ 锁 ⇒ 删 ＋ 一笔清算）
    ｜⚠ **默认面 ⛔ 变**（⛔ 传口 ⇒ 行止须 ≡ 改前 · 承 CEO 令 §三）。
    ⚠ 隔离面之 --csv 宜以**真台账之副本**为始（落行器须契行 · ⛔ 则 落行 判红 rc 2 ⇒ 器无咎）；
    其 号锁 ／ 箱件 ／ 孤件之齿 皆**随面而落**（⛔ 污真径 · 守则 ⒜）。
  ⭐ **号锁之二形（2026-10-11 承 CEO 令 §二）**：⒜ 「<箱>/.号锁」（**文件** · 本器 · 临界区 ＝
    **取号 ⇒ 落箱毕**）⒝ 「<箱>/号锁/」（**目录** · 「号锁.py」经「落台账_行.py」· 临界区 ＝
    **落行**）⇒ ⭐ **各守一段 · ⛔ 同段** ⇒ **其「长留」方为残留**（**投中瞬时之在 ＝ 常**）
    ⇒ 判残留须**二件并查** ∧ **并书取刻**（口 ＝ --残留核）—— 免后人误读「其径在 ⇒ 即残留」。
  ⭐ **未结之痕（2026-10-11 承 CEO 令 §一.⒞）**：凡**落箱毕**（其步 rc ＝ 0）⇒ 即写
    「<箱>/_未结_箱成.ndjson」（「态：pending」）⇒ **落行成 ＋ 醒成 ⇒ 销其行** ⇒ **遭截 ⇒ 自留**
    （＝「未达」之机痕）；⚠ 与旧齿「_孤件_箱成行败.ndjson」（**箱成行败 ＝ 已败**）**径 ⛔ 混**
    （一径 ⛔ 混两义）。
  python -X utf8 -B scripts\dev\投一步.py --self-test   # 自证（含 **反控**：醒必败 ⇒ 须返非零）
  ⚠ 席名（2026-10-06 承 pm 1294 §三 · 并收 ／ pm 1298 §二 · 落账归一）：CW 席之**台账名** ＝ 「CodexWindows线」
    （⛔ SEATS 之「V9工程师·全史席」）⇒ 二键并存（**别名只作「入」** ⇒ 投 CW 之件免 --to-id）
    ⇒ ⭐⭐ **落行须归一为台账之名**（CANON：V9工程师·全史席 ⇒ CodexWindows线）⇒ ⛔ 别名入账。
  ⭐ `--from` **必填**（2026-10-08 承 pm_1844 §二.3 · CW 1842 之呈）：原默认「技术总监」⇒ 忘传则**静默误归**
    （「空 ⛔ 混 缺」之族 ∧ 归因错即台账之根病）⇒ ⛔ 采「自件名推」（名 ／ 账 ⛔ 必同源）⇒ 缺则 rc 2 ＋ 显报「席名 ⛔ 给」。

退出码：0 = 三步皆成（演毕亦然）｜2 = 用法错｜3 = 草稿不在｜4 = 落箱败（BOM ／ CR ／ 件之完 ／ 箱内异）
        ｜5 = 落行败（透传其 rc）｜6 = 已落行（复合键在 ⇒ ⛔ 复落）｜7 = **醒败**｜8 = 已投（凭在 ⇒ ⛔ 复投）
         ｜9 = **号撞**（本日之号面 ⇒ 拒投 ＋ 荐空号 · 承 pm_1889 §三 ／ pm_1894 §一）
        ｜10 = **号锁 ⛔ 得**（争锁重试超限 ⇒ 报 ＋ 止 · ⛔ 长阻 · 承 CEO 令 §一.⒊）

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
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

XT = r"D:\Obsidian\ClawsJoy\ClawsJoy\内容工坊\02_协作\信通"
CSV = os.path.join(XT, u"投递台账.csv")
# ⭐ 面（可覆之活值 · 承 CEO 令 第⑤件 · PM 2740）：--box ／ --csv ／ --lock ⇒ 覆 XT ／ CSV
#   ⇒ 隔离面（俾「二进程真并发」之反例门可跑）｜⚠ **默认面（⛔ 传口）之行为须 ≡ 改前**。
#: 隔离面之旗（--box ／ --csv ／ --lock 任一 ⇒ True · 由 main 置 · 守则 ⒝ 之据）
FACE_ISO = False
#: 锁径之显覆（--lock · 空 ⇒ <箱>/.号锁）
LOCK_OVERRIDE = u""


def face_box(box=None):
    u"""面之解（承 CEO 令 第⑤件）：box ⛔ 给 ⇒ 用模块之**活值** XT
    （⇒ --box 之覆得在**调用时**生效 · ⛔ 定义时 ⇒ 函数默认参 ⛔ 硬绑面）。"""
    return XT if box is None else box


def face_csv(csv=None):
    u"""面之解：csv ⛔ 给 ⇒ 用模块之**活值** CSV（同 face_box 之由）。"""
    return CSV if csv is None else csv
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
    # 2026-10-10 承 CEO 2515 §四.2⒜（准）／ PM 2516 §一（令 · 免二源）：客服席
    #   （父席 ＝ CEO · role `customer-service`）⇒ 一键入表 ⇒ 投客服免 `--to-id`；
    #   ⚠ ⛔ 别名（名 ／ 账 必同源）⇒ `CANON` 无需并。
    u"客服": "712c54b8-2d31-4739-9f26-a006b9a6df62",
    # 2026-10-11 承 CEO 2555 §一（真源落键 · 承 PM 2551 §三.3 之请）：二席 ⇒ 名 ＋ 简名二键
    #   （同 id · 承 CW 之先例 · 别名只作「入」）；⚠ 简名（audit ／ maker）⇒ `CANON` 归一为名。
    u"V9审计师": "20a688e",
    u"audit": "20a688e",
    u"内容制作席": "67eb10c",
    u"maker": "67eb10c",
    # 2026-10-11 承 CEO 2596 §四.1 ／ 2599 §四.3⒟（真源三名 · 由 PM 2601 转令）：三席 ⇒ 名 ＋ 简名二键
    #   （同 id · 承 CW ／ audit 之先例 · 别名只作「入」）；⚠ 简名（sec ／ law ／ re）⇒ `CANON` 归一为名。
    u"秘书": "91d7669",
    u"sec": "91d7669",
    u"法律初审": "c94521a",
    u"law": "c94521a",
    u"V9工程师·重建席(403修复验证)": "112b496",
    u"re": "112b496",
    # 2026-10-11 承 CEO 2685（授权）／ PM 2712 §三（令 · 落真源）：二席 ⇒ 名 ＋ 简名二键
    #   （同 id · 承 CW ／ audit 之先例 · 别名只作「入」）；⚠ 简名（dir ／ geo）⇒ `CANON` 归一为名。
    u"导演": "1c89172",
    u"dir": "1c89172",
    u"GEO研究席": "502535f",
    u"geo": "502535f",
}

# 2026-10-06 承 pm 1298 §二（**落账归一**）｜pm 1302 §四.2（令）：
# 别名只作「入」⇒ **落行之 recv 须归一为台账之名**（⛔ 二名入账 ⇒ 扫 CW 之件必漏）。
CANON = {
    u"V9工程师·全史席": u"CodexWindows线",
    # 2026-10-11 承 CEO 2555 §一：简名 ⇒ 归一为席之名（⛔ 简名入账）
    u"audit": u"V9审计师",
    u"maker": u"内容制作席",
    # 2026-10-11 承 CEO 2596 §四.1：简名 ⇒ 归一为席之名（⛔ 简名入账）
    u"sec": u"秘书",
    u"law": u"法律初审",
    u"re": u"V9工程师·重建席(403修复验证)",
    # 2026-10-11 承 CEO 2685 ／ PM 2712 §三：简名 ⇒ 归一为席之名（⛔ 简名入账）
    u"dir": u"导演",
    u"geo": u"GEO研究席",
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
    u"""件之完（闸一 ／ 二 ／ 三 ＋ type 短式）⇒ (rc, 报) ∨ None（过）。"""
    _fm = front_matter(text)
    _ty = fm_field(_fm, u"type")
    if _ty and (u"（" in _ty or u"(" in _ty):
        return 4, (u"落箱：⛔ type 栏载整句（须短式 ∨ 明书其容长 · 承 PM 2160 §三.3）"
                   u"｜type ＝ %s ｜书名 ＝ %s" % (_ty, name))
    want, field = promised_sections(_fm)
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


# ⭐ 2026-10-09 承 CEO 2158 §二.2 ／ §四.2 ／ PM 2160 §三：**件名之闸**（真源 ＝ PM 闭集（目录内最大版） `文件名列`）。
# ⭐ 2026-10-09 承 CEO 2221 §二 ／ PM 2222 §一：**十五事之式 庚**已批 ⇒ 六式 ⇒ **七式**。
#   其序遵闭集（目录内最大版）之式清单（甲 → 丁 → 庚 → 乙 → 己 → 丙 → 戊）—— 由：庚若居乙后 ⇒ `_申报_CEO_2147_…md` 归乙 ⇒ 式分布 ⛔ 同。
#   ⚠ 版号 ／ 式数 ⛔ 书死字（承 PM 2237 §一）：其报文由 `resolve_form_list()` 自算「版 ＋ 印（二形）＋ 取数刻」。
NAME_PAT = (
    (u"甲·投递式",  re.compile(u"^投递_.+_to_.+_[0-9]{8}_[0-9]+补?_.+[.]md$")),
    (u"丁·致席式",  re.compile(u"^_[^_]+_致[^_]+_(?:(?:[0-9]{8}|[0-9]{4})_.+|.+_(?:[0-9]{8}|[0-9]{4}))[.]md$")),
    (u"庚·十五事式", re.compile(u"^_(?:申报|计划|派|承|验|收|汇总验|评|结|再决|新循环)_.+[.]md$")),
    (u"乙·短式",    re.compile(u"^_[^_]+_[^_]+_[0-9]{4}_.+[.]md$")),
    (u"己·尾号式",  re.compile(u"^_[^_]+_.+_[0-9]{4}[.]md$")),
    (u"丙·短式无席", re.compile(u"^_[^_]+_[0-9]{4}_.+[.]md$")),
    (u"戊·旧式",    re.compile(u"^[^_]+_[^_]+_[0-9]{4}_.+[.]md$")),
)
NAME_EXCL = (
    (u".sha256", re.compile(u"[.]sha256$")),
    (u".before_", re.compile(u"[.]before_")),
    (u".tmp", re.compile(u"[.]tmp$")),
    (u"台账自身", re.compile(u"^投递台账[.]")),
    (u"板（_reply.txt）", re.compile(u"^_reply[.]txt$")),
    (u"载径", re.compile(u"[" + chr(92) + u"/]")),
    (u"前导 _ 之短式（不覆 3 之形）", re.compile(u"^[^_]+_[0-9]{4}_.+[.]md$")),
)


def name_gate(name):
    u"""件名之闸（承 CEO 2158 §二.2 ／ PM 2160 §三 · 一处出）⇒ (rc, 报) ∨ None（过）。

    ⒜ 无 `.md` 尾 ⇒ 拒（如 `裁二刻形归一与裁封之据与号` · 今 1364 之病）；
    ⒝ 不合闭集之式清单（目录内最大版 · 式数由器自计）之任一 ⇒ 拒；
    ⒞ 反例之族（.sha256 ／ .before_ ／ .tmp ／ 投递台账.* ／ _reply.txt ／ 载径）⇒ 拒。
    """
    for lab, pat in NAME_EXCL:
        if pat.search(name):
            return 4, u"落箱：⛔ 件名含反例族「%s」⇒ 拒（承 CEO 2158 §二.2）｜书名 ＝ %s" % (lab, name)
    if not name.endswith(u".md"):
        return 4, u"落箱：⛔ 件名无 .md 尾（1364 之病）⇒ 拒｜书名 ＝ %s" % name
    for lab, pat in NAME_PAT:
        if pat.match(name):
            return None
    _cs = resolve_form_list()
    _nf = len(NAME_PAT)
    _labs = u" ／ ".join(u"%s" % _l for _l, _p in NAME_PAT)
    _src = ((u"版 %s ／ 印 %s ／ 取数刻 %s ／ 键名 %s ／ 式数 %s（器自计 %d）"
             % (_cs.get(u"版"), _cs.get(u"印2"), _cs.get(u"刻"),
                _cs.get(u"键名"), _cs.get(u"式数"), _nf))
            if _cs.get(u"版") else _cs.get(u"报"))
    return 4, (u"落箱：⛔ 件名不合「式清单」之任一 ⇒ 拒（承 CEO 2158 §四.2 ／ PM 2237 §一：报器所取之版号 ＋ 印 ＋ 取数刻 · ⛔ 书死字）"
               u"｜式（%d）＝ %s｜闭集真源（目录内最大版）＝ %s｜书名 ＝ %s"
               % (_nf, _labs, _src, name))

# ⭐ 2026-10-09 承 CEO 2221 §八.3 ／ PM 2222 §四：**件名之号 ⇒ 须 ≡ 行号**（一处出）。
#   病（CEO 一手）：台账（新纪 ≥ 1900 · 凡 151 行）⇒ 名之首 `_dddd_` ≡ 序号者 148 ∧ ⛔ 合者 3
#     （行 2078 ／ 2216 ／ 2217）⇒ 根 ＝ **先定名 ＋ 后取号** ⇒ 名 ⛔ 随号。
#   正口：取号既得 ⇒ 件名之 `_dddd_` 随号回填（唯「自身之号」之位 · ⏔ 首见之 `_dddd_` ∨ 尾号 `_dddd.md`）。
NAME_NUM_RE = re.compile(u"_[0-9]{4}_")
NAME_TAIL_NUM_RE = re.compile(u"_[0-9]{4}(?=[.]md$)")
# ⭐ 2026-10-09 承 PM 2237 §四：**件之 `序号:` 栏 ⇒ 须 ≡ 行号**（一处出 · 与件名同刻）。
#   病（TD 2236 之补正 · 实证）：`name_with_num()` 唯正件名 ⇒ 件内 `序号:` 栏 ⛔ 随号（件名 ≡ 2235 ∧ 栏 ＝ 2234）。


def seq_field(text):
    u"""件内 `序号:` 栏之值（⛔ 在 ⇒ None）。⛔ 走正则（唯取「行首为 `序号:`」之行 · 一处出）。"""
    for _ln in text.split(chr(10)):
        if _ln.startswith(u"序号:"):
            return _ln.split(u":", 1)[1].strip()
    return None


def seq_with_num(text, num):
    u"""件内 `序号:` 栏 ⇒ 随号回填 ⇒ (文, 变否)。⛔ 在 ⇒ 原文 ＋ False（器须**报** · ⛔ 静默）。"""
    _n = u"序号: %s" % (num,)
    _ls = text.split(chr(10))
    for _i, _ln in enumerate(_ls):
        if _ln.startswith(u"序号:"):
            if _ln == _n:
                return text, False
            _ls[_i] = _n
            return chr(10).join(_ls), True
    return text, False


def name_with_num(name, num):
    u"""件名之号 ⇒ 随号回填（**名 ≡ 行号** · 承 CEO 2221 §八.3 ／ PM 2222 §四 · 一处出）⇒ (名, 变否)。

    ⭐ 唯正「自身之号」之位：首见之 `_dddd_` ∨ 尾号 `_dddd.md`（⏔ 载其 `YYYYMMDD` 之 8 位）。
    ⭐ 无可正之位 ⇒ 原名 ＋ False（器须**报** · ⏔ 静默 ⇒ 承「⏔ 静默之默认」之族）。"""
    n = u"%s" % (num,)
    if not n.isdigit():
        return name, False
    if NAME_NUM_RE.search(name):
        n2 = NAME_NUM_RE.sub(u"_%s_" % n, name, count=1)
        return n2, n2 != name
    if NAME_TAIL_NUM_RE.search(name):
        n2 = NAME_TAIL_NUM_RE.sub(u"_%s" % n, name, count=1)
        return n2, n2 != name
    return name, False


def name_num_aligned(name, num, text=None):
    u"""名之号 ≡ 行号 否（唯读 · ⛔ 正）⇒ True ／ False ／ None（名无号位）。

    ⭐ 新一维（承 PM 2237 §四）：`text` 给 ⇒ 并核**件内 `序号:` 栏 ≡ 号**（⛔ 合 ⇒ 必红 ＝ False）。"""
    n = u"%s" % (num,)
    if text is not None:
        _cur = seq_field(text)
        if _cur is not None and _cur != n:
            return False
    m = NAME_NUM_RE.search(name)
    if m:
        return m.group(0)[1:-1] == n
    m2 = NAME_TAIL_NUM_RE.search(name)
    if m2:
        return m2.group(0)[1:] == n
    return None


def apply_seq_patch(src, num, dry=False):
    u"""件内 `序号:` 栏 ⇒ 回填（一处出 · 与件名同刻 · 承 PM 2237 §四）⇒ (rc, 报)。

    ⭐ 演（dry）⇒ 唯报 ⛔ 落盘；真办 ⇒ 写回并**回读核**（⛔ 合 ⇒ rc 4）。
    ⭐ 件无 `序号:` 栏 ⇒ 照实报 ＋ **拒**（报 ＋ 拒 · 承 PM 2241 §一.3）。"""
    try:
        _t = open(src, "rb").read().decode("utf-8")
    except Exception as _e:
        return 0, u"件内·序号栏：⚠ ⛔ 读件（%s）⇒ 照实（⛔ 静默）｜件 ＝ %s" % (type(_e).__name__, src)
    _cur = seq_field(_t)
    if _cur is None:
        return 4, u"件内·序号栏：⛔ 件无 `序号:` 栏 ⇒ ⛔ 得回填（报 ＋ 拒 · 承 PM 2241 §一.3）｜件 ＝ %s" % src
    _t2, _chg = seq_with_num(_t, num)
    if not _chg:
        return 0, u"件内·序号栏：≡ %s（幂等 · ⛔ 动）" % _cur
    if dry:
        return 0, u"件内·序号栏（演）：`%s` ⇒ `序号: %s`（⛔ 落盘 · 真办方验 · 承 PM 2237 §四）" % (_cur, num)
    open(src, "wb").write(_t2.encode("utf-8"))
    _back = open(src, "rb").read().decode("utf-8")
    if seq_field(_back) != u"%s" % (num,):
        return 4, u"件内·序号栏：⛔ 回读不合 ⇒ 拒（写 %s ／ 读 %s）" % (num, seq_field(_back))
    return 0, u"件内·序号栏：`%s` ⇒ `序号: %s`（一处出 · 与件名同刻）" % (_cur, num)


# ⭐ 2026-10-09 承 PM 2228 §一.4⒞：**读器之闭集真源 ⇒ 取「目录内最大版」**（⛔ 硬编版号）
#   ∧ 键名**容二名**（`七式` ∨ `六式`）⇒ ⛔ 硬编（承 PM 2222 §一.2⒞ ／ 2228 §一.4⒞）。
CLOSED_SET_DIR = "D:/paseo-workspace/_pm"
CLOSED_SET_GLOB = u"_闭集_三栏_v*.json"


def _closed_ver(basename):
    u"""自文件名取版号（`_闭集_三栏_v1_4.json` ⇒ (1, 4)）；不可解 ⇒ None。
    ⛔ 字串序（`v1.10 < v1.2` 之患）⇒ 按**段**比（int 元组 · 同 `落台账_行.py` · 一处出）。"""
    m = re.search(u"_v([0-9]+(?:_[0-9]+)*)[.]json$", basename)
    if not m:
        return None
    return tuple(int(x) for x in m.group(1).split(u"_"))


def resolve_form_list():
    u"""取目录内**最大版**之「文件名列」式清单（承 PM 2228 §一 · 一处出）。

    ⇒ dict：版（`v1.4`）／ 印（sha16）／ 刻（取数刻）／ 键名 ／ 清单 ／ 式数 ／ 报。
    ⭐ 键名**容二名**（`七式` ∨ `六式`）⇒ ⛔ 硬编；无真源 ∨ 无可解之版 ⇒ 「闸未跑」（⛔ 充绿）。"""
    best = None
    try:
        _names = os.listdir(CLOSED_SET_DIR)
    except OSError:
        _names = []
    for bn in _names:
        v = _closed_ver(bn)
        if v is None:
            continue
        if best is None or v > best[0]:
            best = (v, os.path.join(CLOSED_SET_DIR, bn))
    _tss = now_ts()
    if best is None:
        return {u"版": None, u"印": None, u"印2": None, u"刻": _tss, u"键名": None,
                u"件": None, u"清单": None, u"式数": None,
                u"报": u"闸未跑：无真源（%s ／ 版号取「目录内最大」）" % CLOSED_SET_GLOB}
    v, q = best
    b = open(q, "rb").read()
    fn = (json.loads(b.decode("utf-8")) or {}).get(u"文件名列") or {}
    key = u"七式" if u"七式" in fn else (u"六式" if u"六式" in fn else None)
    ver = u"v" + u".".join(str(x) for x in v)
    return {u"版": ver, u"印": sha16(b), u"印2": stamp2(b), u"刻": _tss, u"键名": key,
            u"件": os.path.basename(q),
            u"清单": (fn.get(key) if key else None), u"式数": fn.get(u"式数"),
            u"报": u"[闭集] 版 %s ／ 印 %s（%s）／ 取数刻 %s ／ 键名 %s ／ 式数 %s"
                  % (ver, sha16(b), stamp2(b), _tss, key, fn.get(u"式数"))}


def audit_name_num(csv=None, since=1900, box=None):
    u"""台账逐行核「名之号 ≡ 序号」（承 CEO 2227 §一.5 ／ PM 2228 §四 ／ PM 2241 §一.4）⇒ dict。

    ⭐ 读法 ＝ `csv.reader ＋ newline=''`（承 PM 2154 §二 · ⛔ `splitlines()`）。
    ⭐ 判据A（PM 所定 · §四.2⒝）：**名含 `_dddd_`**（⛔ 以类别白名单为判 —— 实证 CEO 之式漏 `1948`）。
    ⭐ 别族B（并含**尾号式** `_dddd.md` · ⛔ 入判 · 别记）：其尾数多为「被回件之号」之旧习（异族 · 承 PM 2237 §二）。"""
    csv, box = face_csv(csv), face_box(box)
    a = {"核": 0, "⛔": []}
    bb = {"核": 0, "⛔": []}
    c = {"核": 0, "⛔": []}
    with io.open(csv, encoding="utf-8-sig", newline="") as f:
        rd = csvmod.reader(f)
        next(rd, None)
        for row in rd:
            if len(row) < 5:
                continue
            num = (row[0] or "").strip()
            name = (row[4] or "").strip()
            if (not num.isdigit()) or int(num) < since:
                continue
            mid = NAME_NUM_RE.search(name)
            if mid:
                a["核"] += 1
                if mid.group(0)[1:-1] != num:
                    a["⛔"].append((num, name))
                _p = os.path.join(box, name)
                if os.path.isfile(_p):
                    try:
                        _cur = seq_field(open(_p, "rb").read().decode("utf-8"))
                    except Exception:
                        _cur = None
                    if _cur is not None:
                        c["核"] += 1
                        if _cur != num:
                            c["⛔"].append((num, name, _cur))
                continue
            tl = NAME_TAIL_NUM_RE.search(name)
            if tl:
                bb["核"] += 1
                if tl.group(0)[1:] != num:
                    bb["⛔"].append((num, name))
    return {"A": a, "B": bb, "C": c}


def audit_name_num_report(csv=None):
    u"""报「名 ⛔ ≡ 号」之数（逐次 · 承 PM 2228 §四.3⒞）⇒ rc（⛔ 溯改）。"""
    csv = face_csv(csv)
    r = audit_name_num(csv)
    print(u"[名之号 ≡ 行号] 面 ＝ %s ｜ 读法 ＝ csv.reader ＋ newline='' ｜ 取数刻 ＝ %s"
          % (os.path.basename(csv), now_ts()))
    print(u"[判据A · 名含 _dddd_（PM 2228 §四.2⒝）] 核 %d 行 ⇒ ⛔ 合 %d"
          % (r["A"]["核"], len(r["A"]["⛔"])))
    for _n, _nm in r["A"]["⛔"]:
        print(u"  ✗ 行 %s ／ %s" % (_n, _nm))
    print(u"[别族B · 尾号式（己）· ⛔ 入判据A之射程 · 别记（承 PM 2237 §二）] 核 %d 行 ⇒ ⛔ 合 %d"
          % (r["B"]["核"], len(r["B"]["⛔"])))
    print(u"[核C · 件内 `序号:` 栏 ≡ 行号（PM 2241 §一.4 ／ 第 14 条：行号取台账之行 · 栏唯附核）] 箱内在者核 %d 件 ⇒ ⛔ 合 %d"
          % (r["C"]["核"], len(r["C"]["⛔"])))
    for _n, _nm, _cur in r["C"]["⛔"]:
        print(u"  ✗ 行 %s ／ 栏 %s ／ %s" % (_n, _cur, _nm))
    return 2 if r["A"]["⛔"] else 0

# ---------------------------------------------------------------- 落箱
def step_box(src, name, dry=False, box=None):
    u"""落箱：草稿 ⇒ 箱（信通）。⭐ 硬闸：⛔ BOM ／ ⛔ CR（须 LF）／ **件之完（闸一／二／三 · 承 pm 1294 §二）**；箱内已同 ⇒ ⛔ 复写；异 ⇒ 拒。"""
    box = face_box(box)
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
    _ng = name_gate(name)
    if _ng:
        return _ng
    dst = os.path.join(box, name)
    if os.path.isfile(dst):
        d = open(dst, "rb").read()
        if d == b:
            return 0, u"落箱：箱内已同 ⇒ ⛔ 复写（印 %s ／ %d B）" % (sha16(b), len(b))
        return 4, u"落箱：⛔ 箱内已存在而内容异（箱 %s / 草 %s）" % (sha16(d), sha16(b))
    if dry:
        return 0, u"落箱（演）：将写 %s ／ %d B ／ 印 %s" % (os.path.join(box, name), len(b), stamp2(b))
    open(dst, "wb").write(b)
    back = open(dst, "rb").read()
    if sha16(back) != sha16(b):
        return 4, u"落箱：⛔ 回读不合（写 %s / 读 %s）" % (sha16(b), sha16(back))
    return 0, u"落箱：成 · %s ／ %d B ／ 印 %s" % (name, len(b), stamp2(b))


# ---------------------------------------------------------------- 落行
def row_count(num, date, sender, cat, csv=None):
    csv = face_csv(csv)
    rc, out = run([sys.executable, "-X", "utf8", "-B", LAND, "--csv", csv, "--check",
                   "--num", str(num), "--date", date, "--from", sender, "--cat", cat])
    m = re.search(u"复合键出现 (\\d+) 次", out)
    return (int(m.group(1)) if m else -1), out


def step_land(num, date, sender, recv, name, cat, need, note, ts, dry=False, csv=None, box=None, need_file=None):
    u"""落行：落台账_行.py 之唯一写器。⭐ 闸前先核「复合键」⇒ ⛔ 复落。"""
    n, out = row_count(num, date, sender, cat, csv)
    csv, box = face_csv(csv), face_box(box)
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
           "--note", note, "--ts", ts]
    # ⭐ need 之源（一处出 · 承 PM 2216 §一）：--need-file（自件取）优先；否则 --need。折唯在落行器。
    if need_file:
        cmd += ["--need-file", need_file]
    else:
        cmd += ["--need", need]
    if dry:
        cmd.append("--dry-run")
    rc, out = run(cmd)
    print(out.rstrip())
    if rc != 0:
        # ⭐ 并发败之辨（承 CEO 认令 §二.⒝ · 2026-10-11）：下游之「并发闸·挂」（rc 1）
        #   与「复合键已在台账」（rc 2）／「号撞·锁内复算」（rc 9）皆「**他席同刻已落**」之形
        #   ⇒ **可重试**（让号之环 · 重取号 ＋ 重取契 ＋ 重试）；⚠ 他病（入口错 ／ 判红）
        #   ⇒ rc 5（**⛔ 重试** · 免以重试掩他病 —— 承 CEO 认令 §二.⒝.⒟）。
        _mu = out if isinstance(out, str) else u""
        if rc == 1 or (u"[并发闸·挂]" in _mu) or (u"复合键已在台账" in _mu) or (u"[号撞·锁内复算]" in _mu):
            return 11, (u"落行：**并发败**（rc=%s · 他席同刻已落 ⇒ 可重试 · 承 CEO 认令 §二.⒝）" % rc)
        return 5, u"落行：败 rc=%s（见上之判红 / 入口错）" % rc
    return 0, u"落行：%s（rc 0）" % (u"演" if dry else u"成")


# ---------------------------------------------------------------- 契（重取）
def ledger_seal(csv=None):
    u"""**重取契**：复读台账之现印（⛔ 缓存 · ⛔ 凭忆 · 承 CEO 认令 §二.⒝）。

    由：契 ＝ **全局不变式**（二写者并作 ⇒ 后者所见之契必陈）⇒ 让号之环**每轮须重取**
    （本器 ⛔ 持契 ⇒ 落行器每次重读 ／ 重立；此处唯取其**可核之现印**作留痕）。"""
    csv = face_csv(csv)
    try:
        b = open(csv, "rb").read()
    except Exception as _e:
        return u"[契·重取] ⛔ 读（%s：%s）⇒ 照实（⛔ 静默）" % (type(_e).__name__, _e)
    return (u"[契·重取] 台账现印 %s ／ %d B ／ 取数刻 %s（他席之写已见 ⇒ 契随重取）"
            % (sha16(b), len(b), now_ts()))


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


def step_wake(name, tid, dry=False, box=None):
    u"""醒：wake_send.py（其自带「首成即停」＋ 自动登记）。⭐ 凭在 ⇒ ⛔ 复投。"""
    o = receipt_of(name)
    box = face_box(box)
    if o is not None:
        return 8, u"醒：⛔ 已投（凭据在 · rc 0 · 刻 %s）⇒ ⛔ 复投" % o.get(u"凭据登入刻", u"?")
    if dry and not os.path.isfile(os.path.join(box, name)):
        return 0, u"醒（演·跳）：件未在箱 ⇒ ⛔ 得验（真办 --go 先落箱 ⇒ 方有验）"
    cmd = [sys.executable, "-X", "utf8", "-B", WAKE, "--to", tid, "--file", os.path.join(box, name)]
    if not dry:
        cmd.append("--send")
    rc, msg = _wake_run(cmd, name, tid)
    if rc != 0:
        return 7, msg
    if not dry and receipt_of(name) is None:
        return 0, (u"醒：成 rc=0 ｜ ⚠⚠ 醒成而凭未登 ⇒ **须补登**（⛔ 复投 —— 复投即重送）"
                   u" ／ 书名 ＝ " + name)
    return 0, msg


# ⭐ 承 PM 2168 §四（CEO 2166 §三ⓜ）：凡报「倍 ／ 百分」⇒ 须并示算式（分子 ／ 分母）。
def fmt_ratio(label, numerator, denominator, baseline=u"", steps=None, suffix=u""):
    u"""报比之一处出（承 PM 2168 §四 ＋ PM 2175 §一/§二 · 一条化）：

    凡报「比」⇒ 须示（分子 ＋ 分母 ＋ 对照之基线 ＋ 步数 T）· 缺一 ⇒ 标「⛔ 缺 …」（应判红）。
    ⛔ 唯报「降 N×」—— 同文异基线 ／ 异 T ⇒ 数异（CEO 2171 §二 一手：16.2× 对 Stateful·T=100 ∥ ≈50× 对 Memory·T=200）。"""
    _r = (float(numerator) / denominator) if denominator else float("inf")
    _miss = ratio_missing(baseline, steps)
    _parts = u"%s ÷ %s" % (numerator, denominator)
    if baseline:
        _parts += u" · 对 %s" % baseline
    if steps not in (None, u""):
        _parts += u" · T=%s" % steps
    _tail = (u" ⛔ 缺 " + u"／".join(_miss)) if _miss else u""
    return u"%s %.4g× （%s）%s%s" % (label, _r, _parts, suffix, _tail)


def ratio_missing(baseline, steps):
    u"""比之必备：对照之基线 ＋ 步数 T ⇒ 缺者之名（空 ⇒ 齐）。"""
    _m = []
    if not baseline:
        _m.append(u"对照之基线")
    if steps in (None, u""):
        _m.append(u"步数T")
    return _m




# ⭐ 承 PM 2168 §五（CEO 2166 §四.2ⓝ）：他域之径 ⇒ 报中标之（免读者误判同域）。
OTHER_DOMAIN_PREFIXES = (r"D:\paseo-workspace", r"D:\Obsidian\ClawsJoy\ClawsJoy\codex")

def path_label(p):
    u"""径之标签：属他域 ⇒ 附「（他域之径）」。"""
    _s = str(p)
    for _pre in OTHER_DOMAIN_PREFIXES:
        if _s.startswith(_pre):
            return u"%s（他域之径）" % _s
    return _s


def stamp2(path_or_bytes):
    u"""印之书法二形（一处出 · 承 PM 2205 §二）：⇒ 'md5[:16] xxx ／ sha16 yyy'（二形皆书名 ⇒ 免同源异读数之假案）。"""
    _b = path_or_bytes if isinstance(path_or_bytes, (bytes, bytearray)) else open(path_or_bytes, "rb").read()
    import hashlib as _h
    return u"md5[:16] %s ／ sha16 %s" % (_h.md5(_b).hexdigest()[:16], _h.sha256(_b).hexdigest()[:16])


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

    good = os.path.join(tmp, "投递_技术总监_to_项目经理_20261009_9001_自证.md")
    open(good, "wb").write(u"# 甲\n正文\n".encode("utf-8"))
    bom = os.path.join(tmp, "b.md")
    open(bom, "wb").write(b"\xef\xbb\xbf" + u"# 甲\n".encode("utf-8"))
    crlf = os.path.join(tmp, "c.md")
    open(crlf, "wb").write(b"# x\r\n")
    box = os.path.join(tmp, "box")
    os.makedirs(box)

    print(u"[自证 1 落箱 · 正控]")
    rc, _ = step_box(good, "投递_技术总监_to_项目经理_20261009_9001_自证.md", dry=False, box=box)
    res(u"合规之草 ⇒ 0", rc, 0)
    rc, m = step_box(good, "投递_技术总监_to_项目经理_20261009_9001_自证.md", dry=False, box=box)
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
    noname = os.path.join(tmp, "_报_技术总监_9002_自证.md")
    open(noname, "wb").write(u"---\ntype: 报\ndate: 2026-10-08\n---\n\n## 一 甲\n\n正文\n".encode("utf-8"))
    rc, m = step_box(noname, "_报_技术总监_9002_自证.md", dry=False, box=box)
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

    print(u"[自证 8 件名之闸（承 CEO 2158 §二.2 ／ PM 2160 §三 · 正控 ／ 反控 ≥5）]")
    for _nm in (u"投递_技术总监_to_项目经理_20261009_9001_甲.md",
                u"_回_TD_2160_事.md",
                u"_报_技术总监_2160_事.md",
                u"_报_2160_事.md",
                u"报_技术总监_2160_事.md",
                u"_CEO裁决_致PM_2160_事.md",
                u"_结_2144_事.md",
                u"_汇总验_PA1_2144_事.md"):
        res(u"正控（七式）：%s ⇒ 过" % _nm, name_gate(_nm), None)
    _g7 = [l for l, _p in NAME_PAT if _p.match(u"_结_2144_事.md")]
    res(u"式之序：_结_2144_事.md 首中 ＝ 庚（庚 ⛔ 居乙后）", _g7[:1], [u"庚·十五事式"])
    _g7b = [l for l, _p in NAME_PAT if _p.match(u"_申报_CEO_2147_初.md")]
    res(u"式之序：_申报_… 首中 ＝ 庚（⛔ 归乙）", _g7b[:1], [u"庚·十五事式"])
    for _nm, _why in ((u"裁二刻形归一与裁封之据与号", u"无 .md 尾"),
                      (u"投递台账.csv", u"台账自身"),
                      (u"x.md.sha256", u".sha256"),
                      (u"投递台账.csv.before_abc", u".before_"),
                      (u"a.tmp", u".tmp"),
                      (u"_reply.txt", u"板"),
                      (u"codex" + chr(47) + u"x.md", u"载径"),
                      (u"回件_1905_x.md", u"前导 _ 之短式"),
                      (u"随手一名.md", u"不合「式清单」")):
        _g = name_gate(_nm)
        _ok8 = (_g is not None) and (_g[0] == 4) and (_why in _g[1])
        ok = ok and _ok8
        print(u"  %s 反控：%s ⇒ rc=%s（期 4 · 因含「%s」）"
              % (u"OK " if _ok8 else u"✗ ", _nm, (_g[0] if _g else None), _why))
    _gd = name_gate(u"随手一名.md")
    res(u"报错文 ⛔ 载死字（「今 v」）", u"今 v" in _gd[1], False)
    res(u"报错文载「器所取之版号 ＋ 印（二形）＋ 取数刻」",
        (u"md5[:16]" in _gd[1]) and (u"取数刻" in _gd[1]), True)
    print(u"  " + _gd[1])

    print(u"[自证 3 醒 · 正控 / 反控（承 pm 1291 §四：反控须证其可达「非零」）]")
    print(u"[自证 8.2 件名之号 ≡ 行号（承 CEO 2221 §八.3 ／ PM 2222 §四 · 正控 ／ 反控）]")
    res(u"正控：名 _2216_ ／ 号 2217 ⇒ 回填 _2217_"
        , name_with_num(u"_回_TD_2216_事.md", 2217), (u"_回_TD_2217_事.md", True))
    res(u"正控：名 ≡ 号 ⇒ 幂等（⛔ 变）"
        , name_with_num(u"_回_TD_2225_事.md", 2225), (u"_回_TD_2225_事.md", False))
    res(u"正控：尾号式（己）⇒ 回填 _2201.md"
        , name_with_num(u"_报_TD_2156.md", 2201), (u"_报_TD_2201.md", True))
    res(u"正控：甲式 ⇒ 幂等（⛔ 触其 8 位之日期）"
        , name_with_num(u"投递_技术总监_to_项目经理_20261009_9001_甲.md", 9001)
        , (u"投递_技术总监_to_项目经理_20261009_9001_甲.md", False))
    res(u"反控：件名无号位 ⇒ ⛔ 得回填（器须报 · ⛔ 静默）"
        , name_with_num(u"随手一名.md", 2217), (u"随手一名.md", False))
    res(u"判据：名 ⛔ ≡ 号 ⇒ False（反控之根）", name_num_aligned(u"_回_TD_2216_事.md", 2217), False)
    res(u"判据：名 ≡ 号 ⇒ True", name_num_aligned(u"_回_TD_2217_事.md", 2217), True)
    res(u"判据：名无号位 ⇒ None", name_num_aligned(u"随手一名.md", 2217), None)
    print(u"[自证 8.3 闭集真源 ＝ 目录内最大版（承 PM 2228 §一 · 读器 ⛔ 硬编版 ／ 键名容二名）]")
    _cs = resolve_form_list()
    res(u"报须书「版 ＋ 印 ＋ 刻」（⛔ 只报值）",
        (_cs[u"版"] is not None and _cs[u"印"] is not None and _cs[u"刻"] is not None), True)
    res(u"式清单 ≡ 闭集（目录内最大版 · 一处出）", [l for l, _p in NAME_PAT], _cs[u"清单"])
    res(u"式数 由器自计（⛔ 人手维持）", _cs[u"式数"], len(NAME_PAT))
    res(u"键名容二名（今 ＝ 七式）", _cs[u"键名"] in (u"七式", u"六式"), True)
    print(u"  " + _cs[u"报"])
    res(u"报须载二形之印（md5[:16] ＋ sha16 · PM 2237 §一）", u"md5[:16]" in _cs[u"报"], True)
    _an = audit_name_num()
    _anb = set(int(n) for n, _m in _an["A"]["⛔"])
    res(u"判据A（名含 _dddd_）之旧账 4 行必在（1948 ／ 2078 ／ 2216 ／ 2217）",
        {1948, 2078, 2216, 2217} <= _anb, True)
    res(u"判据A 之核行数 > 0（逐次报数 · 承 PM 2228 §四.3⒞）", _an["A"]["核"] > 0, True)
    print(u"  [附] 判据B（并尾号式）核 %d ／ ⛔ %d ／ 旧账之号 4 ⇒ 别记（⛔ 溯改）"
          % (_an["B"]["核"], len(_an["B"]["⛔"])))

    print(u"[自证 8.4 件内 `序号:` 栏 ≡ 行号（承 PM 2237 §四 · 一处出 · 与件名同刻）]")
    _n2 = chr(10)
    _t0 = _n2.join([u"---", u"type: 令", u"序号: 2234", u"类别: 令", u"---", u"", u"正文", u""])
    _t1 = _n2.join([u"---", u"type: 令", u"序号: 2235", u"类别: 令", u"---", u"", u"正文", u""])
    res(u"取栏值 ⇒ 2234", seq_field(_t0), u"2234")
    res(u"回填栏（2234 ⇒ 2235）", seq_with_num(_t0, 2235), (_t1, True))
    res(u"栏 ≡ 号 ⇒ 幂等（⛔ 变）", seq_with_num(_t1, 2235), (_t1, False))
    res(u"无栏件 ⇒ ⛔ 得回填（器须报 · ⛔ 静默）", seq_with_num(u"# 甲" + _n2 + u"正文" + _n2, 2235), (u"# 甲" + _n2 + u"正文" + _n2, False))
    res(u"判据：栏 ⛔ ≡ 号 ⇒ False（反控之根 · 造栏 2234 而号 2235 ⇒ 必红）", name_num_aligned(u"_回_TD_2235_事.md", 2235, text=_t0), False)
    res(u"判据：栏 ≡ 号 ∧ 名 ≡ 号 ⇒ True", name_num_aligned(u"_回_TD_2235_事.md", 2235, text=_t1), True)
    res(u"判据：栏 ≡ 号 ∧ 名 ⛔ ≡ 号 ⇒ False", name_num_aligned(u"_回_TD_2234_事.md", 2235, text=_t1), False)
    _sq = os.path.join(tmp, u"seq_src.md")
    open(_sq, "wb").write(_t0.encode("utf-8"))
    _rcq, _mq = apply_seq_patch(_sq, 2235, dry=True)
    _same = (open(_sq, "rb").read().decode("utf-8") == _t0)
    res(u"演 ⇒ rc 0 ∧ ⛔ 落盘", (_rcq, _same), (0, True))
    _rcq2, _mq2 = apply_seq_patch(_sq, 2235, dry=False)
    _cur2 = seq_field(open(_sq, "rb").read().decode("utf-8"))
    res(u"真办 ⇒ 栏回填 ∧ 回读核 ⇒ 2235", (_rcq2, _cur2), (0, u"2235"))
    _rcq3, _mq3 = apply_seq_patch(_sq, 2235, dry=False)
    res(u"真办（二次）⇒ 幂等 ⇒ rc 0", _rcq3, 0)
    _sq2 = os.path.join(tmp, u"seq_none.md")
    open(_sq2, "wb").write((u"# 甲" + _n2 + u"正文" + _n2).encode("utf-8"))
    _rcq4, _mq4 = apply_seq_patch(_sq2, 2235, dry=False)
    res(u"无栏件 ⇒ rc 4（报 ＋ 拒 · 承 PM 2241 §一.3）", (_rcq4, u"件无" in _mq4), (4, True))
    print(u"  " + _mq4)

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
    res(u"SEATS 含 客服（承 CEO 2515 §四.2⒜ ／ PM 2516 §一）", SEATS.get(u"客服"), u"712c54b8-2d31-4739-9f26-a006b9a6df62")
    res(u"SEATS 含 V9审计师 ／ audit（同 id · 承 CEO 2555 §一）", SEATS.get(u"V9审计师") == SEATS.get(u"audit"), True)
    res(u"SEATS 含 内容制作席 ／ maker（同 id · 承 CEO 2555 §一）", SEATS.get(u"内容制作席") == SEATS.get(u"maker"), True)
    res(u"CANON 归一 audit ⇒ V9审计师", CANON.get(u"audit"), u"V9审计师")
    res(u"CANON 归一 maker ⇒ 内容制作席", CANON.get(u"maker"), u"内容制作席")
    res(u"SEATS 含 秘书 ／ sec（同 id · 承 CEO 2596 §四.1）", SEATS.get(u"秘书") == SEATS.get(u"sec"), True)
    res(u"SEATS 含 法律初审 ／ law（同 id · 承 CEO 2596 §四.1）", SEATS.get(u"法律初审") == SEATS.get(u"law"), True)
    res(u"SEATS 含 V9工程师·重建席 ／ re（同 id · 承 CEO 2596 §四.1）", SEATS.get(u"V9工程师·重建席(403修复验证)") == SEATS.get(u"re"), True)
    res(u"CANON 归一 sec ⇒ 秘书", CANON.get(u"sec"), u"秘书")
    res(u"CANON 归一 law ⇒ 法律初审", CANON.get(u"law"), u"法律初审")
    res(u"CANON 归一 re ⇒ V9工程师·重建席(403修复验证)", CANON.get(u"re"), u"V9工程师·重建席(403修复验证)")
    res(u"SEATS 含 导演 ／ dir（同 id · 承 PM 2712 §三）", SEATS.get(u"导演") == SEATS.get(u"dir"), True)
    res(u"SEATS 含 GEO研究席 ／ geo（同 id · 承 PM 2712 §三）", SEATS.get(u"GEO研究席") == SEATS.get(u"geo"), True)
    res(u"CANON 归一 dir ⇒ 导演", CANON.get(u"dir"), u"导演")
    res(u"CANON 归一 geo ⇒ GEO研究席", CANON.get(u"geo"), u"GEO研究席")

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
    print(u"[自证 10 箱源之形（尾 ∨ 中段）＋ 号域之约（承 CEO 令 §一.⒜⒝ · 反例门 ＝ 客服 2726 之形）]")
    _tb2 = os.path.join(tmp, "box3")
    os.makedirs(_tb2)
    _tc2 = os.path.join(tmp, "led2.csv")
    _d2 = now_date()
    io.open(_tc2, "w", encoding="utf-8").write(
        u"序号,日期,发件,收件,文件名,类别,状态,动作需求,回执件,备注,时点\n"
        + (u"2730,%s,项目经理,技术总监,_令_TD_2730.md,令,open,x,,,2026-10-11T09:00:00+08:00\n" % _d2))
    io.open(os.path.join(_tb2, u"_回_PM_2731_台账轮转已落.md"), "w", encoding="utf-8").write(u"x\n")
    io.open(os.path.join(_tb2, u"_报_CW_2732.md"), "w", encoding="utf-8").write(u"x\n")
    io.open(os.path.join(_tb2, u"_回_TD_2026_伪命中.md"), "w", encoding="utf-8").write(u"x\n")
    _u2 = day_numbers(_d2, csv=_tc2, box=_tb2)
    res(u"中段形（客服 2726 之形 ⇒ 2731）＋ 尾形（2732）二形并取", sorted(_u2), [2730, 2731, 2732])
    res(u"号域之约：伪命中 _2026_（< 台账当日极大 2730）⇒ 弃", 2026 in _u2, False)
    io.open(os.path.join(_tb2, u"_回_TD_2780_端点.md"), "w", encoding="utf-8").write(u"x\n")
    io.open(os.path.join(_tb2, u"_回_TD_2781_越窗.md"), "w", encoding="utf-8").write(u"x\n")
    _u3 = day_numbers(_d2, csv=_tc2, box=_tb2)
    res(u"号域之约之端点：2780（＝ 极大 ＋ 50）留 ∧ 2781（＋51）弃", [2780 in _u3, 2781 in _u3], [True, False])
    _tc3 = os.path.join(tmp, "led3.csv")
    io.open(_tc3, "w", encoding="utf-8").write(
        u"序号,日期,发件,收件,文件名,类别,状态,动作需求,回执件,备注,时点\n")
    _u4 = day_numbers(_d2, csv=_tc3, box=_tb2)
    res(u"台账当日空 ⇒ ⛔ 约（伪命中亦入面 · 反控之根）", 2026 in _u4, True)
    print(u"[自证 11 孤件之齿（落箱成 ∧ 落行败 ⇒ 机留一行 · 幂等）]")
    _op = os.path.join(tmp, "orphan.ndjson")
    _m1 = orphan_note(2731, _d2, u"_回_PM_2731_台账轮转已落.md", 5, u"落行败", box=_tb2, path=_op)
    _ls = [l for l in io.open(_op, encoding="utf-8").read().split(u"\n") if l.strip()]
    _o1 = json.loads(_ls[0]) if _ls else {}
    res(u"一行 ∧ 可机核（径 ／ 号 ／ 刻 ／ 因 ／ 日 ／ 件名 齐）",
        (len(_ls) == 1 and _o1.get(u"号") == 2731 and _o1.get(u"因") == u"落行败"
         and bool(_o1.get(u"刻")) and bool(_o1.get(u"日")) and bool(_o1.get(u"件名"))), True)
    res(u"与件可对（径 ⇒ 件在 · 径尾 ＝ 件名）",
        str(_o1.get(u"径", u"")).endswith(u"_回_PM_2731_台账轮转已落.md") and os.path.isfile(_o1.get(u"径", u"")), True)
    _m2 = orphan_note(2731, _d2, u"_回_PM_2731_台账轮转已落.md", 5, u"落行败", box=_tb2, path=_op)
    _ls2 = [l for l in io.open(_op, encoding="utf-8").read().split(u"\n") if l.strip()]
    res(u"幂等：复记 ⇒ 仍 1 行", len(_ls2), 1)
    print(u"    其报：" + _m1)
    print(u"[自证 12 号锁（原子占号 · 承 CEO 令 §一.⒉–⒋ · PM 2737）]")
    _lb = os.path.join(tmp, "lockbox")
    os.makedirs(_lb)
    _lp = lock_path(_lb)
    res(u"锁径 ＝ <箱>/.号锁（同卷 ⇒ O_EXCL 原子）", _lp, os.path.join(_lb, u".号锁"))
    res(u"占锁 ⇒ 得（径 ≡ 锁径）", lock_acquire(box=_lb, tries=3, step=0.01), _lp)
    _li = lock_read(_lp)
    res(u"锁件在 ∧ 载 pid ＋ 刻（可机核）",
        (os.path.isfile(_lp) and isinstance(_li.get(u"pid"), int) and bool(_li.get(u"刻"))), True)
    res(u"反控：他锁在（pid 在 ∧ 龄新）⇒ ⛔ 得", lock_acquire(box=_lb, tries=2, step=0.01), None)
    res(u"释锁 ⇒ True", lock_release(_lp), True)
    res(u"释锁（幂等 · 已释）⇒ False ∧ 锁件 ⛔ 在",
        (lock_release(_lp), os.path.isfile(_lp)), (False, False))
    res(u"释毕可复占 ⇒ 得", lock_acquire(box=_lb, tries=3, step=0.01), _lp)
    lock_release(_lp)
    io.open(_lp, "w", encoding="utf-8").write(json.dumps({u"pid": os.getpid(), u"刻": now_ts()}))
    _old = time.time() - (LOCK_STALE_SECONDS + 5)
    os.utime(_lp, (_old, _old))
    res(u"陈旧①（龄 > 60s）⇒ 可破 ＋ 占得", lock_acquire(box=_lb, tries=3, step=0.01), _lp)
    lock_release(_lp)
    io.open(_lp, "w", encoding="utf-8").write(json.dumps({u"pid": 99999999, u"刻": now_ts()}))
    res(u"陈旧②（pid ⛔ 在）⇒ 可破 ＋ 占得", lock_acquire(box=_lb, tries=3, step=0.01), _lp)
    lock_release(_lp)
    io.open(_lp, "w", encoding="utf-8").write(json.dumps({u"pid": os.getpid(), u"刻": now_ts()}))
    res(u"反控：pid 在 ∧ 龄新 ⇒ ⛔ 破（⛔ 静默摘他人之锁）", lock_break_if_stale(_lp), None)
    res(u"反控：其锁仍在", os.path.isfile(_lp), True)
    lock_release(_lp)
    io.open(_lp, "w", encoding="utf-8").write(json.dumps({u"pid": os.getpid(), u"刻": now_ts()}))
    os.utime(_lp, (time.time() - 999, time.time() - 999))
    _whyb = lock_break_if_stale(_lp)
    res(u"破锁须报由（⛔ 静默 · 载「龄」）", bool(_whyb) and (u"龄" in _whyb), True)
    res(u"破毕 ⇒ 锁件 ⛔ 在", os.path.isfile(_lp), False)
    print(u"[自证 13 反例门 ⒝ 二投并发（异号连续）· ⚠ **⛔ 充 PM 之初验**（承 CEO 令 §五.3）]")
    _fb = os.path.join(tmp, "boxc")
    os.makedirs(_fb)
    _fc = os.path.join(tmp, "ledc.csv")
    io.open(_fc, "w", encoding="utf-8").write(
        u"序号,日期,发件,收件,文件名,类别,状态,动作需求,回执件,备注,时点\n"
        + (u"2730,%s,项目经理,技术总监,_令_TD_2730.md,令,open,x,,,2026-10-11T09:00:00+08:00\n" % _d2))
    _snap = day_numbers(_d2, csv=_fc, box=_fb)
    res(u"反控：无锁 · 同快照 ⇒ 二取同号（TOCTOU 之缝 ＝ 号撞之根）",
        (next_free_num(_d2, used=_snap, csv=_fc, box=_fb),
         next_free_num(_d2, used=_snap, csv=_fc, box=_fb)), (2731, 2731))
    _csrc = (u"# -*- coding: utf-8 -*-\n"
             u"import importlib.util, io, os, sys, time\n"
             u"_sp = importlib.util.spec_from_file_location(u'tou1mod', sys.argv[1])\n"
             u"m = importlib.util.module_from_spec(_sp)\n"
             u"_sp.loader.exec_module(m)\n"
             u"_box, _csv, _date = sys.argv[2], sys.argv[3], sys.argv[4]\n"
             u"_p = m.lock_acquire(box=_box, tries=600, step=0.02)\n"
             u"if _p is None:\n"
             u"    print(u'LOCKFAIL'); sys.exit(3)\n"
             u"try:\n"
             u"    _n = m.next_free_num(_date, csv=_csv, box=_box)\n"
             u"    io.open(os.path.join(_box, u'_回_TD_%d_并发.md' % _n), u'w', encoding=u'utf-8').write(u'x\\n')\n"
             u"    time.sleep(0.2)\n"
             u"    print(u'NUM=%d' % _n)\n"
             u"finally:\n"
             u"    m.lock_release(_p)\n")
    _pc = []
    for _i in range(2):
        _pc.append(subprocess.Popen([sys.executable, u"-X", u"utf8", u"-B", u"-c", _csrc,
                                     os.path.abspath(__file__), _fb, _fc, _d2],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT))
    _outs = [q.communicate(timeout=90)[0].decode("utf-8", "replace") for q in _pc]
    _got = sorted(int(re.search(u"NUM=([0-9]+)", _o).group(1)) for _o in _outs if u"NUM=" in _o)
    res(u"正控：有锁 · 二进程并发 ⇒ 二异号 ∧ 连续（2731 ／ 2732）", _got, [2731, 2732])
    res(u"正控：⛔ 同号（⛔ 静默合号）", len(set(_got)), 2)
    res(u"正控：二件皆落箱（号在中段 · 可扫）", sorted(os.listdir(_fb)),
        [u"_回_TD_2731_并发.md", u"_回_TD_2732_并发.md"])
    print(u"    子进程之报：" + u" ／ ".join(_o.strip().replace(u"\n", u"｜") for _o in _outs))
    print(u"[自证 13.2 让号之环（main · 取释 ＋ 留痕 ＋ 争锁超限之齿）]")
    _g2 = globals()
    _sa2 = dict((_k, _g2[_k]) for _k in (u"lock_acquire", u"lock_release",
                                         u"next_free_num", u"one_pass"))
    _sav = sys.argv[:]
    _so = sys.stdout
    _ev = []
    _seq = [9, 0]
    def _op_spy(num, a, name, date, ts, recv, tid, dry, on_box_done=None):
        _r = _seq.pop(0)
        _ev.append(u"op:%d" % _r)
        if on_box_done is not None and _r == 0:
            on_box_done()
            _ev.append(u"box-rel")
        return _r
    try:
        _g2[u"lock_acquire"] = lambda *aa, **kk: (_ev.append(u"acq") or u"<锁·spy>")
        _g2[u"lock_release"] = lambda p: (_ev.append(u"rel") or True)
        _g2[u"next_free_num"] = lambda *aa, **kk: 7777
        _g2[u"one_pass"] = _op_spy
        sys.argv = [u"投一步.py", u"--src", os.path.join(tmp, u"x.md"),
                    u"--name", u"_回_TD_7777_事.md", u"--to", u"项目经理",
                    u"--from", u"技术总监", u"--num", u"auto"]
        _buf = io.StringIO()
        sys.stdout = _buf
        _rcm = main()
        _txt = _buf.getvalue()
    finally:
        sys.stdout = _so
        sys.argv = _sav
        _g2.update(_sa2)
    res(u"让号之环：rc 0（第二次成）", _rcm, 0)
    res(u"逐字「让号·留痕」（承 CEO 令 §一.⒌）", (u"让号·留痕" in _txt), True)
    res(u"占锁 2 次（每次重取皆先占）", _ev.count(u"acq"), 2)
    res(u"落箱毕即释（⛔ 及落行 · 承 CEO 令 §一.⒉）", (u"box-rel" in _ev), True)
    try:
        _g2[u"lock_acquire"] = lambda *aa, **kk: None
        _g2[u"one_pass"] = lambda *aa, **kk: 0
        sys.argv = [u"投一步.py", u"--src", os.path.join(tmp, u"x.md"),
                    u"--name", u"_回_TD_7777_事.md", u"--to", u"项目经理",
                    u"--from", u"技术总监", u"--num", u"auto"]
        _buf2 = io.StringIO()
        sys.stdout = _buf2
        _rcL = main()
        _txt2 = _buf2.getvalue()
    finally:
        sys.stdout = _so
        _g2.update(_sa2)
    res(u"争锁超限 ⇒ rc 10（报 ＋ 止 · ⛔ 长阻）", (_rcL, u"号锁" in _txt2), (10, True))
    print(u"[自证 14 探针一口（--box ／ --csv · 面移 ∧ 默认面 ⛔ 变 · 守则 ⒜⒝）]")
    _pb = os.path.join(tmp, "facebox")
    os.makedirs(_pb)
    _pcv = os.path.join(tmp, "face.csv")
    io.open(_pcv, "w", encoding="utf-8").write(
        u"序号,日期,发件,收件,文件名,类别,状态,动作需求,回执件,备注,时点\n")
    _n2b = chr(10)
    _fsrc = os.path.join(tmp, u"face_src.md")
    io.open(_fsrc, "w", encoding="utf-8").write(
        _n2b.join([u"---", u"type: 令", u"序号: 7777", u"类别: 令", u"---", u"", u"正文", u""]))
    _g3 = globals()
    _face0 = (_g3[u"XT"], _g3[u"CSV"], _g3[u"FACE_ISO"], _g3[u"LOCK_OVERRIDE"])
    _sa3 = dict((_k, _g3[_k]) for _k in (u"step_box", u"step_land", u"step_wake",
                                         u"check_number", u"day_numbers"))
    _seen2 = []
    _g3[u"step_box"] = lambda *aa, **kk: (_seen2.append(u"box") or (0, u"落箱（spy）"))
    _g3[u"step_land"] = lambda *aa, **kk: (_seen2.append(u"land") or (0, u"落行（spy）"))
    _g3[u"step_wake"] = lambda *aa, **kk: (_seen2.append(u"wake") or (0, u"醒（spy）"))
    _g3[u"check_number"] = lambda *aa, **kk: (0, u"号可用（spy）")
    _g3[u"day_numbers"] = lambda *aa, **kk: {}
    _argv_iso = [u"投一步.py", u"--src", _fsrc, u"--name", u"_回_TD_7777_事.md",
                 u"--to", u"项目经理", u"--from", u"技术总监", u"--num", u"7777",
                 u"--box", _pb, u"--csv", _pcv, u"--go"]
    _argv_def = [u"投一步.py", u"--src", _fsrc, u"--name", u"_回_TD_7777_事.md",
                 u"--to", u"项目经理", u"--from", u"技术总监", u"--num", u"7777", u"--go"]
    # ⚠ 默认面之反控昔用**真面** ⇒ 其 pend_mark ／ pend_clear 落真径 ⇒ 今改 temp 面（⛔ 污真径 · 承 CEO 裁 §二）
    _pbd = os.path.join(tmp, "defbox")
    os.makedirs(_pbd)
    _pcvd = os.path.join(tmp, "def.csv")
    io.open(_pcvd, "w", encoding="utf-8").write(
        u"序号,日期,发件,收件,文件名,类别,状态,动作需求,回执件,备注,时点\n")
    try:
        _seen2[:] = []
        sys.argv = _argv_iso
        _b1 = io.StringIO()
        sys.stdout = _b1
        _rc_i = main()
        _t1 = _b1.getvalue()
        _face1 = (_g3[u"XT"], _g3[u"CSV"])
        _seenA = list(_seen2)
        _g3[u"XT"], _g3[u"CSV"] = _pbd, _pcvd   # ⚠ temp 面 ⇒ 免污真径（⛔ 传口 ⇒ 面仍 ⛔ 变）
        _seen2[:] = []
        sys.argv = _argv_def
        _b2 = io.StringIO()
        sys.stdout = _b2
        _rc_d = main()
        _t2 = _b2.getvalue()
        _face2 = (_g3[u"XT"], _g3[u"CSV"])
        _seenB = list(_seen2)
    finally:
        sys.stdout = _so
        sys.argv = _sav
        _g3.update(_sa3)
        _g3[u"XT"], _g3[u"CSV"], _g3[u"FACE_ISO"], _g3[u"LOCK_OVERRIDE"] = _face0
    res(u"传口 ⇒ 面移（XT ⇒ --box ／ CSV ⇒ --csv）", _face1, (_pb, _pcv))
    res(u"传口 ⇒ 其输出含其面之径（可核）", ((_pb in _t1) and (_pcv in _t1)), True)
    res(u"隔离面（守则 ⒝）：醒 ⛔ 实发（唯印一行 · ⛔ 真唤席）",
        (_seenA, (u"⛔ 实发" in _t1)), ([u"box", u"land"], True))
    res(u"反控（默认面 · temp 面）：面 ⛔ 变 ∧ 醒真调 ∧ ⛔ 污真径",
        (_face2, _seenB), ((_pbd, _pcvd), [u"box", u"land", u"wake"]))
    res(u"反控（默认面）：输出 ⛔ 含「⛔ 实发」", (u"⛔ 实发" in _t2), False)
    res(u"二面皆 rc 0", (_rc_i, _rc_d), (0, 0))
    print(u"[自证 9 报比示算式 ／ 他域之径（承 PM 2168 §四 ／ §五）]")
    _fr = fmt_ratio(u"[倍]", 6100000, 122000, baseline=u"Memory", steps=200)
    hit = (u"÷" in _fr) and (u"6100000" in _fr) and (u"122000" in _fr) and (u"对 Memory" in _fr) and (u"T=200" in _fr) and (u"⛔ 缺" not in _fr)
    print(u"  %s 报比示算式 ＋ 对照 ＋ 步数（正控）⇒ %s" % (u"OK " if hit else u"✗ ", _fr))
    ok = ok and hit
    _fr2 = fmt_ratio(u"[倍]", 1062387, 65408)
    hit = (u"⛔ 缺" in _fr2) and (u"对照之基线" in _fr2) and (u"步数T" in _fr2)
    print(u"  %s 报比缺对照 ／ 步数 ⇒ 必标（反控）⇒ %s" % (u"OK " if hit else u"✗ ", _fr2))
    ok = ok and hit
    _fp = path_label(r"D:\paseo-workspace\_tools\wake_send.py")
    hit = (u"他域之径" in _fp)
    print(u"  %s 他域之径标之 ⇒ %s" % (u"OK " if hit else u"✗ ", _fp))
    ok = ok and hit
    _fs = path_label(os.path.join(XT, u"一件.md"))
    hit = (u"他域之径" not in _fs)
    print(u"  %s 同域之径 ⇒ 不标 ⇒ %s" % (u"OK " if hit else u"✗ ", _fs))
    ok = ok and hit

    _st = stamp2(b"abc")
    hit = (u"md5[:16]" in _st) and (u"sha16" in _st)
    print(u"  %s 印二形（一处出 · PM 2205 §二）⇒ %s" % (u"OK " if hit else u"✗ ", _st))
    ok = ok and hit
    print(u"[自证 10 need 一处出 ／ 反控⒝（承 PM 2216 §一 ／ §二）]")
    _g = globals()
    class _A: pass
    _a = _A()
    _a.to = u"项目经理"; _a.sender = u"技术总监"; _a.cat = u"回"
    _a.src = os.path.join(tmp, u"x.md"); _a.need = u""; _a.note = u""; _a.need_file = None
    _seen = []
    _sb, _sl, _sw = _g["step_box"], _g["step_land"], _g["step_wake"]
    _g["step_box"] = lambda *aa, **kk: (_seen.append(u"box") or (0, u"落箱（spy）"))
    _g["step_land"] = lambda *aa, **kk: (_seen.append(u"land") or (5, u"落行：败（spy）"))
    _g["step_wake"] = lambda *aa, **kk: (_seen.append(u"wake") or (0, u"醒（spy）"))
    try:
        _rc_o = one_pass(9003, _a, u"投递_技术总监_to_项目经理_20261009_9003_自证.md",
                         u"2026-10-09", u"2026-10-09T00:00:00+08:00", u"项目经理", u"b136893", True)
    finally:
        _g["step_box"], _g["step_land"], _g["step_wake"] = _sb, _sl, _sw
    res(u"反控⒝：落行败 ⇒ 三步一处断 ⇒ rc=5（必报）", _rc_o, 5)
    res(u"反控⒝：落行败 ⇒ 醒 ⛔ 被调（⛔ 静默）", (u"wake" not in _seen), True)
    print(u"[自证 15 未结之痕（落箱毕 ⇒ pending · 销于落行成 ＋ 醒成 · 遭截自留 · 承 CEO 令 §一.⒞）]")
    _pb = os.path.join(tmp, u"pendbox")
    os.makedirs(_pb, exist_ok=True)
    _pp = os.path.join(_pb, PEND_NAME)
    _cnt = lambda: len([l for l in io.open(_pp, encoding="utf-8").read().split(u"\n") if l.strip()])
    _m1 = pend_mark(9004, u"2026-10-11", u"_回_甲_9004_自证.md", box=_pb)
    res(u"落箱毕 ⇒ 记一行（pending）", (u"成 · 1 行" in _m1, _cnt() if os.path.isfile(_pp) else -1), (True, 1))
    _m2 = pend_mark(9004, u"2026-10-11", u"_回_甲_9004_自证.md", box=_pb)
    res(u"幂等：同键重记 ⇒ 仍 1 行", (_cnt(), u"幂等" in _m2), (1, True))
    _g2 = globals()
    _kxt, _sb2, _sl2, _sw2 = _g2["XT"], _g2["step_box"], _g2["step_land"], _g2["step_wake"]
    class _A2: pass
    _a2 = _A2(); _a2.to = u"项目经理"; _a2.sender = u"技术总监"; _a2.cat = u"回"
    _a2.src = os.path.join(tmp, u"y.md"); _a2.need = u""; _a2.note = u""; _a2.need_file = None
    _g2["XT"] = _pb
    _g2["step_box"] = lambda *aa, **kk: (0, u"落箱（spy）")
    def _boom(*aa, **kk):
        raise RuntimeError(u"模拟遭截（于 ① ② 之间）")
    _g2["step_land"] = _boom
    try:
        one_pass(9007, _a2, u"_回_乙_9007_遭截.md", u"2026-10-11", u"2026-10-11T00:00:00+08:00",
                 u"项目经理", u"b136893", False)
        _trunc = False
    except RuntimeError:
        _trunc = True
    finally:
        _g2["step_land"] = _sl2
    _t7 = u"_回_乙_9007_遭截.md"
    res(u"遭截之模拟（落箱成 ∧ 落行未起）⇒ 其行自留",
        (_trunc, _cnt(), _t7 in io.open(_pp, encoding="utf-8").read()), (True, 2, True))
    _g2["step_land"] = lambda *aa, **kk: (0, u"落行：成（spy）")
    _g2["step_wake"] = lambda *aa, **kk: (0, u"醒：成（spy）")
    try:
        one_pass(9008, _a2, u"_回_丙_9008_全成.md", u"2026-10-11", u"2026-10-11T00:00:00+08:00",
                 u"项目经理", u"b136893", False)
    finally:
        _g2["step_box"], _g2["step_land"], _g2["step_wake"] = _sb2, _sl2, _sw2
        _g2["XT"] = _kxt
    res(u"正控：全成（落行成 ＋ 醒成）⇒ 其行 ⛔ 留", (_cnt(), u"9008" in io.open(_pp, encoding="utf-8").read()), (2, False))
    _c1 = pend_clear(9007, u"2026-10-11", _t7, box=_pb)
    res(u"销：遭截之行者销 ⇒ 该行 ⛔ 在（余先前所记 9004 之一行）",
        (u"成 · 销 1 行" in _c1, _t7 in io.open(_pp, encoding="utf-8").read(), _cnt()), (True, False, 1))
    _c2 = pend_clear(9007, u"2026-10-11", _t7, box=_pb)
    res(u"销之幂等：键 ⛔ 在场 ⇒ ⛔ 重写", u"键 ⛔ 在场" in _c2, True)
    res(u"二径 ⛔ 混（旧齿之径 ≠ 未结之痕之径）", PEND_NAME != u"_孤件_箱成行败.ndjson", True)
    print(u"[自证 16 残留核（面五 · **二件并查** · 并书取刻 · 承 CEO 令 §二.3）]")
    _rb = os.path.join(tmp, u"resbox")
    os.makedirs(_rb, exist_ok=True)
    res(u"正控：二形皆 ⛔ 在 ⇒ rc 0（绿）", residue_report(box=_rb), 0)
    _rf = os.path.join(_rb, LOCK_NAME)
    open(_rf, u"w").write(u"")
    res(u"反控：⒜ 「.号锁」（文件）在 ⇒ rc 2（红）", residue_report(box=_rb), 2)
    os.remove(_rf)
    _rd = os.path.join(_rb, u"号锁")
    os.makedirs(_rd, exist_ok=True)
    res(u"反控：⒝ 「号锁」（目录）在 ⇒ rc 2（红）", residue_report(box=_rb), 2)
    open(_rf, u"w").write(u"")
    res(u"二件并查（二形皆在）⇒ rc 2（红）", residue_report(box=_rb), 2)
    res(u"⛔ 以一件之绿遮另一件（单件在 ⇒ 必红）", residue_report(box=_rb) != 0, True)
    os.remove(_rf)
    os.rmdir(_rd)
    res(u"清面：二形皆 ⛔ 在 ⇒ rc 0", residue_report(box=_rb), 0)
    print(u"[自证 17 未结痕之断言 ⇒ **分二支**（承 CEO 认令 §二.⒜）]")
    _cb = os.path.join(tmp, u"pendbox2")
    os.makedirs(_cb, exist_ok=True)
    _cp = os.path.join(_cb, PEND_NAME)
    _cnt2 = lambda: (len([l for l in io.open(_cp, encoding="utf-8").read().split(u"\n") if l.strip()])
                     if os.path.isfile(_cp) else -1)
    _rd2 = lambda: (io.open(_cp, encoding="utf-8").read() if os.path.isfile(_cp) else u"")
    pend_mark(9101, u"2026-10-11", u"_回_甲_9101_成.md", box=_cb)
    pend_clear(9101, u"2026-10-11", u"_回_甲_9101_成.md", box=_cb)
    res(u"支一：**二投皆成** ⇒ 未结痕 ⛔ 留（册 0 行）", _cnt2(), 0)
    pend_mark(9102, u"2026-10-11", u"_回_乙_9102_败.md", box=_cb)
    res(u"支二：**有一败（rc 5）∨ 遭截** ⇒ 未结痕 留 ＝ 正（册 ≥ 1 行 ∧ 载其名）",
        (_cnt2() >= 1, u"9102" in _rd2()), (True, True))
    res(u"一齿：支二之面 ⇒ **「余 0 行」⛔ 为正**（⛔ 以此为唯一正形）", (_cnt2() == 0), False)
    _rb2 = os.path.join(tmp, u"resbox2")
    os.makedirs(_rb2, exist_ok=True)
    pend_mark(9104, u"2026-10-11", u"_回_丁_9104_败.md", box=_rb2)
    _b7 = io.StringIO()
    sys.stdout = _b7
    try:
        _rc7 = residue_report(box=_rb2)
    finally:
        sys.stdout = _so
    _t7r = _b7.getvalue()
    res(u"残留核（面五）之报亦载此二支（有未结 ⇒ 留 ＝ 正 ∧ ⛔ 判红）",
        ((u"有未结" in _t7r), (u"留 ＝ **正**" in _t7r), _rc7), (True, True, 0))
    print(u"[自证 17.2 让号之环 · 并发败（rc 11）⇒ 重取号 ＋ 重取契 ＋ 重试 ∧ 单进程 ⛔ 重试]")
    _g5 = globals()
    _sa5 = dict((_k, _g5[_k]) for _k in (u"lock_acquire", u"lock_release",
                                         u"next_free_num", u"one_pass", u"ledger_seal"))
    _ev5 = []

    def _mk_op(seq):
        def _op5(num, a, name, date, ts, recv, tid, dry, on_box_done=None):
            _r = seq.pop(0) if seq else 0
            _ev5.append(u"op:%d" % _r)
            return _r
        return _op5
    try:
        _g5[u"lock_acquire"] = lambda *aa, **kk: (_ev5.append(u"acq") or u"<闩·spy>")
        _g5[u"lock_release"] = lambda p: (_ev5.append(u"rel") or True)
        _g5[u"next_free_num"] = lambda *aa, **kk: 7777
        _g5[u"ledger_seal"] = lambda *aa, **kk: u"[契·重取] 台账现印 <spy> ／ 0 B ／ 取数刻 <spy>"
        _g5[u"one_pass"] = _mk_op([11, 0])
        sys.argv = [u"投一步.py", u"--src", os.path.join(tmp, u"x.md"),
                    u"--name", u"_回_TD_7777_事.md", u"--to", u"项目经理",
                    u"--from", u"技术总监", u"--num", u"auto"]
        _buf5 = io.StringIO()
        sys.stdout = _buf5
        _rc5 = main()
        _txt5 = _buf5.getvalue()
    finally:
        sys.stdout = _so
        sys.argv = _sav
        _g5.update(_sa5)
    res(u"并发败 rc 11 ⇒ 重试后成（rc 0）", _rc5, 0)
    res(u"rc 11 入让号之环 ⇒ 留痕「让号·留痕」", (u"让号·留痕" in _txt5), True)
    res(u"重取契 ⇒ 留痕并载「契·重取」＋ 现印", (u"契·重取" in _txt5), True)
    _ev5[:] = []
    try:
        _g5[u"lock_acquire"] = lambda *aa, **kk: (_ev5.append(u"acq") or u"<闩·spy>")
        _g5[u"lock_release"] = lambda p: (_ev5.append(u"rel") or True)
        _g5[u"one_pass"] = _mk_op([0])
        # ⚠ 必重设 argv：前块之 finally 已复 argv ⇒ ⛔ 复设 ⇒ main 重入 selftest（递归之患）
        sys.argv = [u"投一步.py", u"--src", os.path.join(tmp, u"x.md"),
                    u"--name", u"_回_TD_7777_事.md", u"--to", u"项目经理",
                    u"--from", u"技术总监", u"--num", u"auto"]
        _buf6 = io.StringIO()
        sys.stdout = _buf6
        _rc6 = main()
        _txt6 = _buf6.getvalue()
    finally:
        sys.stdout = _so
        sys.argv = _sav
        _g5.update(_sa5)
    res(u"正控：**单进程一次成** ⇒ ⛔ 重试（one_pass 唯 1 次 ∧ 无留痕）",
        (_rc6, _ev5.count(u"acq"), (u"让号·留痕" in _txt6)), (0, 1, False))
    res(u"正控：单进程一次成 ⇒ ⛔ 移残件 ／ ⛔ 销痕（让号之果 ⛔ 见）",
        ((u"残件·移出" in _txt6), (u"残件·销痕" in _txt6)), (False, False))
    print(u"[自证 18 残件之移 ＋ 号锁内销（承 CEO 裁 §二.⒜／⒝ · 2026-10-11）]")
    _qb = os.path.join(tmp, u"quarbox")
    os.makedirs(_qb, exist_ok=True)
    _qsrc = os.path.join(_qb, u"_回_TD_9201_孤.md")
    io.open(_qsrc, u"w", encoding="utf-8", newline=u"\n").write(u"x\n")
    _q1 = quarantine_orphan(9201, u"2026-10-11", u"_回_TD_9201_孤.md", box=_qb)
    res(u"⒜ 让号毕 ⇒ 移孤件出箱（箱 ⛔ 有 ∧ _残件/ 有 · 保留原名）",
        (os.path.isfile(_qsrc),
         os.path.isfile(os.path.join(_qb, QUAR_NAME, u"_回_TD_9201_孤.md")),
         u"成 · " in _q1), (False, True, True))
    _q2 = quarantine_orphan(9201, u"2026-10-11", u"_回_TD_9201_孤.md", box=_qb)
    res(u"⒜ 幂等：重跑 ⇒ 「已在 _残件/」（⛔ 再动）", u"幂等" in _q2, True)
    _q3 = quarantine_orphan(9202, u"2026-10-11", u"_回_TD_9202_未.md", box=_qb)
    res(u"⒜ 源 ⛔ 在 ⇒ 无事（照实）", u"源 ⛔ 在" in _q3, True)
    _g6 = globals()
    _sa6 = dict((_k, _g6[_k]) for _k in (u"lock_acquire", u"lock_release"))
    _ev6 = []
    try:
        _g6[u"lock_acquire"] = lambda *aa, **kk: (_ev6.append(u"acq") or u"<闩·spy>")
        _g6[u"lock_release"] = lambda p: (_ev6.append(u"rel") or True)
        pend_mark(9203, u"2026-10-11", u"_回_丁_9203_成.md", box=_qb)
        _c6 = pend_clear_safe(9203, u"2026-10-11", u"_回_丁_9203_成.md", box=_qb)
    finally:
        _g6.update(_sa6)
    _qp = os.path.join(_qb, PEND_NAME)
    _qc = (len([l for l in io.open(_qp, encoding="utf-8").read().split(u"\n") if l.strip()])
           if os.path.isfile(_qp) else -1)
    res(u"⒝ 销痕之 RMW 入号锁之内（acq ⇒ 销 ⇒ rel）",
        (_ev6, (u"成 · 销 1 行" in _c6), _qc), ([u"acq", u"rel"], True, 0))
    try:
        _g6[u"lock_acquire"] = lambda *aa, **kk: None
        _c7 = pend_clear_safe(9204, u"2026-10-11", u"_回_戊_9204.md", box=_qb)
    finally:
        _g6.update(_sa6)
    res(u"⒝ ⛔ 得锁 ⇒ ⛔ 销 ＋ 照实（宁假警 ⛔ 伪绿）", u"号锁 ⛔ 得" in _c7, True)
    print(u"[自证 18.3 让号之环 ⇒ 残件之移 ∧ 重试成 ⇒ 销痕]")
    _g7 = globals()
    _sa7 = dict((_k, _g7[_k]) for _k in (u"lock_acquire", u"lock_release", u"next_free_num",
                                         u"one_pass", u"ledger_seal", u"XT", u"CSV",
                                         u"FACE_ISO", u"LOCK_OVERRIDE"))
    _ob = os.path.join(tmp, u"loopbox")
    os.makedirs(_ob, exist_ok=True)
    _ev7 = []
    _ops7 = []

    def _op7(num, a, name, date, ts, recv, tid, dry, on_box_done=None):
        _ops7.append(num)
        if len(_ops7) == 1:
            io.open(os.path.join(_ob, name), u"w", encoding="utf-8", newline=u"\n").write(u"x\n")
            pend_mark(num, date, name, box=_ob)
            return 11
        return 0
    try:
        _g7[u"lock_acquire"] = lambda *aa, **kk: (_ev7.append(u"acq") or u"<闩·spy>")
        _g7[u"lock_release"] = lambda p: (_ev7.append(u"rel") or True)
        _g7[u"next_free_num"] = lambda *aa, **kk: 9301
        _g7[u"ledger_seal"] = lambda *aa, **kk: u"[契·重取] 台账现印 <spy> ／ 0 B ／ 取数刻 <spy>"
        _g7[u"one_pass"] = _op7
        sys.argv = [u"投一步.py", u"--src", os.path.join(tmp, u"x.md"),
                    u"--name", u"_回_TD_9301_事.md", u"--to", u"项目经理",
                    u"--from", u"技术总监", u"--num", u"auto", u"--box", _ob, u"--go"]
        _buf7 = io.StringIO()
        sys.stdout = _buf7
        _rc7b = main()
        _txt7 = _buf7.getvalue()
    finally:
        sys.stdout = _so
        sys.argv = _sav
        _g7.update(_sa7)
    res(u"⒜ 让号毕 ⇒ 残件·移出（箱 ⛔ 有 ∧ _残件/ 有）",
        ((u"残件·移：成" in _txt7),
         os.path.isfile(os.path.join(_ob, QUAR_NAME, u"_回_TD_9301_事.md")),
         os.path.isfile(os.path.join(_ob, u"_回_TD_9301_事.md"))), (True, True, False))
    _qp7 = os.path.join(_ob, PEND_NAME)
    _qc7 = (len([l for l in io.open(_qp7, encoding="utf-8").read().split(u"\n") if l.strip()])
            if os.path.isfile(_qp7) else -1)
    res(u"⒝ 重试成 ⇒ 销残件之痕（册 0 行 · ⛔ 假警）∧ 载「残件·销痕」",
        (_rc7b, _qc7, (u"残件·销痕" in _txt7)), (0, 0, True))
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

#: 件名之**中段号**（`_回_PM_2731_台账轮转已落.md` ⇒ 2731 · 承 CEO 令 §一.⒜）——
#  本族之名 ＝ `_<类别>_<受>_<号>_<题>.md`（号在**中段**）⇒ 旧「唯认名尾」对本族**恒盲**
#  ⇒ 箱源须**二形并取**（尾形 ∨ 中段形 · 首个命中）。
NUM_MID = re.compile(u"_([0-9]{3,4})_")

#: 号域之约之窗（箱取之号 ≤ 台账当日极大 ＋ 此数 · 承 CEO 令 §一.⒝）
NUM_WIN = 50


def day_numbers(date, csv=None, box=None):
    u"""本日各席**已用**之号 ⇒ {号: [(席, 件名, 刻, 源)]}（**二源并取** · 承 pm_1889 §三 ／ pm_1894 §一.1⒞）。

    ⭐ 「预扫 ⛔ 足」：预扫与落箱之间有窗 —— 一手之真场景：pm 令 `1880` ts `07:22:43`
      ∧ CW 报 `1880` ts `07:22:58` ⇒ 15 s 之窗 ⇒ ⭐ **唯落箱之刻为准**。
    ① **台账**（`投递台账.csv` · 日期 ∧ 序号 ∧ 发件 ＋ 文件名 ＋ 时点）＝ 已入账者；
    ② **箱**（本日 mtime ∧ 名尾 `_<号>.md`）＝ 已落箱而账未及者（他席并发之行中）。
    ⭐ 二源**须并取**（任一漏 ⇒ 拒投失守 —— 与「两数须同源」之律同族 · 此处之「源」＝ 落箱那一瞬）。
    ⭐ 取数面（明书 · 承 PM 2216 §三.2）：① `投递台账.csv`（读法 csv ＋ newline）② 箱之目录（mtime ＋ 名尾号）。
    ⭐ 箱源之筛（修 `2026-10-11` · 承 CEO 令 §一.⒜）：**尾形 ∨ 中段形**（`NUM_TAIL` ∨ `NUM_MID` · 首个命中）。
    ⭐ **号域之约**（修 `2026-10-11` · 承 CEO 令 §一.⒝）：箱取之号须 ∈［台账当日极大, ＋`NUM_WIN`］（含端点）
      ⇒ 排除**伪命中**（如 `…_2026_…`）；台账当日空 ⇒ ⛔ 约（照实 · ⛔ 静默）。
      ⭐ 由：凡号由「极大 ＋ 1」而生 ⇒ **落箱之号恒 ≥ 台账极大**。
    """
    csv, box = face_csv(csv), face_box(box)
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
    _lo = max(used) if used else None        # 台账当日极大（⛔ 按全账 · 承 CEO 令 §一.⒝）
    _led = set(used)                         # 台账当日已用之号（箱中之同号 ⇒ 正常 ⇒ ⛔ 报）
    _drop = []                               # 弃而**⛔ 在账**者（照实报 · 免「印勤动」）
    try:
        for fn in os.listdir(box):
            m = NUM_TAIL.search(fn) or NUM_MID.search(fn)   # 尾形 ∨ 中段形（首个命中）
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
            if _lo is not None and not (_lo <= _n <= _lo + NUM_WIN):
                if _n not in _led:           # 已在账 ⇒ 正常（本族之箱恒留旧件）⇒ ⛔ 报
                    _drop.append((fn, _n))   # ⛔ 在账 ⇒ 疑伪命中 ⇒ 照实报（⛔ 静默）
                continue
            if any(_x[1] == fn for _x in used.get(_n, [])):
                continue
            used.setdefault(_n, []).append((u"?（箱内 · 席待账）", fn,
                                            _dt.strftime(u"%H:%M:%S"), u"箱"))
    except Exception as _e:
        print(u"⚠ 箱 ⛔ 读（%s）⇒ 号之面唯见台账（照实 · ⛔ 静默）" % type(_e).__name__)
    if _drop:
        print(u"⚠ 箱源：号 ⛔ 在号域［台账当日极大 %s, ＋%d］∧ ⛔ 在账 ⇒ %d 件（照实 · 疑伪命中）"
              % (_lo, NUM_WIN, len(_drop)))
        for _f, _n in _drop[:5]:
            print(u"    %s（号 %d）" % (_f, _n))
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


def check_number(num, date, sender, name, box=None, csv=None, used=None):
    u"""落箱之刻**复核号**（承 pm_1889 §三 ／ pm_1894 §一）⇒ (rc, 报)。

    撞 ⇒ (9, 三事逐字：撞谁 ＋ 荐一空号 ＋ 本日之号面)｜⛔ 撞 ⇒ (0, 空串)。
    ⭐ 幂等：**同件名**之号 ⛔ 算撞（＝复投之径 · 免得「拒投之后 ⛔ 得复投」）；
      件名内嵌发件席（`_报_TD_1884.md` 族）⇒ 件名同 ⇒ 同席同件。
    ⛔ 静默改号 ／ ⛔ 代改（唯报 ＋ 荐 —— 承 pm_1894 §一.2）。
    """
    box, csv = face_box(box), face_csv(csv)
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

# ------------------------------------------------- 孤件之齿（承 CEO 令 §一.⒞）
ORPHAN = os.path.join(XT, u"_孤件_箱成行败.ndjson")


def orphan_note(num, date, name, rc, why, box=None, dry=False, path=None):
    u"""孤件之齿：**落箱成 ∧ 落行败** ⇒ 机留一行（承 CEO 令 §一.⒞）。

    形（JSONL · 一行一件 · UTF-8 · LF）：{日 ／ 号 ／ 件名 ／ 径 ／ 刻 ／ rc ／ 因 ／ 面}。
    ⭐ **可机核**：逐行 `json.loads` 即得四元（径 ＋ 号 ＋ 刻 ＋ 因）；⛔ 唯人眼撞见（PM 2729 系偶得）。
    ⭐ **与件可对**：径 ＝ 箱内该件之全径（`os.path.isfile(径)` 即验）。
    ⭐ **幂等**：同（日 ＋ 号 ＋ 件名）已在 ⇒ ⛔ 复记（免「印勤动」之族 · 承 CEO 2686 §二）。
    dry ⇒ ⛔ 落（唯报其形）。
    """
    box = face_box(box)
    p = path or os.path.join(box, u"_孤件_箱成行败.ndjson")
    o = {u"日": date, u"号": int(num), u"件名": name, u"径": os.path.join(box, name),
         u"刻": now_ts(), u"rc": int(rc), u"因": why, u"面": u"箱有件 ∧ 账无行"}
    line = json.dumps(o, ensure_ascii=False)
    if dry:
        return u"孤件（演 · ⛔ 落）：%s" % line
    try:
        if os.path.isfile(p):
            for _l in io.open(p, encoding="utf-8"):
                _l = _l.strip()
                if not _l:
                    continue
                try:
                    _o = json.loads(_l)
                except Exception:
                    continue
                if (_o.get(u"日") == date and str(_o.get(u"号")) == str(int(num))
                        and _o.get(u"件名") == name):
                    return u"孤件：幂等 ⇒ ⛔ 复记（已在 · %s）" % os.path.basename(p)
        io.open(p, "a", encoding="utf-8", newline=u"\n").write(line + u"\n")
    except Exception as _e:
        return u"孤件：⛔ 落（%s：%s）⇒ 照实报（⛔ 静默）" % (type(_e).__name__, _e)
    return u"孤件：成 · 1 行 ⇒ %s ｜ %s" % (os.path.basename(p), line)


# ------------------------------------------------- 未结之痕（「遭截」之另一面 · 承 CEO 令 §一.⒞）
PEND_NAME = u"_未结_箱成.ndjson"


def pend_path(box=None):
    u"""未结之痕之径 ＝ 「<箱>/_未结_箱成.ndjson」（随面而落 · 守则 ⒜）。"""
    return os.path.join(face_box(box), PEND_NAME)


def _pend_key(o):
    u"""未结之痕之键 ＝ （日 ／ 号 ／ 件名）—— ⛔ 含刻（刻异 ⇒ 仍同键 ⇒ 幂等之要）。"""
    try:
        n = str(int(o.get(u"号")))
    except Exception:
        n = u"%s" % o.get(u"号")
    return (o.get(u"日"), n, o.get(u"件名"))


def pend_mark(num, date, name, box=None, dry=False, path=None):
    u"""**落箱毕**（其步 rc ＝ 0）⇒ 即写一行 **pending**（承 CEO 令 §一.⒉ · 2026-10-11）。

    由：旧齿唯于「落行败」之刻写 ⇒ **遭截（进程中道被杀 ⇒ 工具调用被截）⇒ 其写未及**
    ⇒ 「箱有件 ∧ 账无行」唯靠人眼 —— 四例（客服 2726 ／ 法律 2725 ／ PM 2750 ／ PM 2758）皆然。
    形（JSONL · 一行 · UTF-8 · LF）：{日 ／ 号 ／ 件名 ／ 径 ／ 落箱刻 ／ 态：pending}。
    ⭐ 幂等：同键已在 ⇒ ⛔ 复记（免「印勤动」之族）。⭐ 其销 ＝ pend_clear；**遭截 ⇒ 自留**。
    ⚠ 与旧齿之径 **⛔ 混**（一径 ⛔ 混两义）：旧齿 ＝ **已败** ／ 本痕 ＝ **未结**。
    ⭐ 其写之位移：**在号锁之内**（取号 ⇒ 落箱毕）⇒ append 免并发之失。
    """
    box = face_box(box)
    p = path or pend_path(box)
    o = {u"日": date, u"号": int(num), u"件名": name, u"径": os.path.join(box, name),
         u"落箱刻": now_ts(), u"态": u"pending"}
    line = json.dumps(o, ensure_ascii=False)
    if dry:
        return u"未结：演 · ⛔ 落：%s" % line
    try:
        if os.path.isfile(p):
            for _l in io.open(p, encoding="utf-8"):
                _l = _l.strip()
                if not _l:
                    continue
                try:
                    _o = json.loads(_l)
                except Exception:
                    continue
                if _pend_key(_o) == _pend_key(o):
                    return u"未结：幂等 ⇒ ⛔ 复记（已在 · %s）" % PEND_NAME
        io.open(p, "a", encoding="utf-8", newline=u"\n").write(line + u"\n")
    except Exception as _e:
        return u"未结：⛔ 落（%s：%s）⇒ 照实报（⛔ 静默）" % (type(_e).__name__, _e)
    return u"未结：成 · 1 行 ⇒ %s ｜ %s" % (PEND_NAME, line)


def pend_clear(num, date, name, box=None, dry=False, path=None):
    u"""**落行成 ＋ 醒成** ⇒ 销其行（承 CEO 令 §一.⒉）。⭐⭐ 二择（销 ／ 标 done）我取 **销**：

    由 ⒜ 册之内容**即**「未结」之集 ⇒ 判据直读（⛔ 算差集）⒝ 其失（并发下之重写互覆）唯
    「销未至」⇒ **假警**（安全之向 · ⛔ 反向）⒞ 键 ⛔ 在场 ⇒ ⛔ 重写（免 churn）。
    ⚠ 销之写**在号锁之外**（②③ 于释锁后）⇒ 与他席之重写或互覆 ⇒ 唯假警之向。
    """
    box = face_box(box)
    p = path or pend_path(box)
    if not os.path.isfile(p):
        return u"未结·销：册 ⛔ 在 ⇒ 无事（照实）"
    try:
        lines = [l for l in io.open(p, encoding="utf-8").read().split(u"\n") if l.strip()]
    except Exception as _e:
        return u"未结·销：⛔ 读（%s：%s）⇒ 照实报" % (type(_e).__name__, _e)
    key = _pend_key({u"日": date, u"号": num, u"件名": name})
    keep, drop = [], 0
    for l in lines:
        try:
            _o = json.loads(l)
        except Exception:
            keep.append(l)
            continue
        if _pend_key(_o) == key:
            drop += 1
        else:
            keep.append(l)
    if drop == 0:
        return u"未结·销：键 ⛔ 在场 ⇒ ⛔ 重写（幂等）"
    if dry:
        return u"未结·销（演）：将销 %d 行 ⇒ %s" % (drop, PEND_NAME)
    try:
        io.open(p, "w", encoding="utf-8", newline=u"\n").write(
            (u"\n".join(keep) + u"\n") if keep else u"")
    except Exception as _e:
        return u"未结·销：⛔ 写（%s：%s）⇒ 照实报" % (type(_e).__name__, _e)
    return u"未结·销：成 · 销 %d 行 ⇒ 余 %d 行（%s）" % (drop, len(keep), PEND_NAME)


def residue_report(box=None):
    u"""面五（残留）之判据 ＝ **二件并查**（承 CEO 令 §二.3 · 2026-10-11）。

    ⒜ 「<箱>/.号锁」（**文件** · 本器 · 临界区 ＝ 取号 ⇒ 落箱毕）
    ⒝ 「<箱>/号锁/」（**目录** · 「号锁.py」经「落台账_行.py」· 临界区 ＝ 落行）
    ⇒ ⭐ **各守一段 · ⛔ 同段** ⇒ **其「长留」方为残留**（**投中瞬时之在 ＝ 常**）
    ⇒ 判残留须**二件并查** ∧ **并书取刻**（⛔ 误读「其径在 ⇒ 即残留」）。
    rc：0 ＝ 绿（二形皆 ⛔ 在）／2 ＝ 红（有一在 ⇒ 核是否投中）。
    """
    b = face_box(box)
    a1, a2 = os.path.join(b, LOCK_NAME), os.path.join(b, u"号锁")
    e1, e2 = os.path.exists(a1), os.path.exists(a2)
    ok = (not e1) and (not e2)
    print(u"[层 ③] 残留核 %s ｜ 箱 ＝ %s" % (now_ts(), path_label(b)))
    print(u"  ⒜ .号锁（文件 · 取号⇒落箱）⇒ %s" % (u"在（残留 ∨ 投中）" if e1 else u"⛔ 在"))
    print(u"  ⒝ 号锁（目录 · 落行）⇒ %s" % (u"在（残留 ∨ 投中）" if e2 else u"⛔ 在"))
    # ⭐ 未结之痕 ⇒ **断言分二支**（承 CEO 认令 §二.⒜）：二投皆成 ⇒ 痕 ⛔ 留；
    #   有一败 ∨ 遭截 ⇒ 留 ＝ 正 ⇒ **⛔ 以「余 0 行」为唯一正形**。只报 · ⛔ 判红。
    _pp = pend_path(b)
    if not os.path.isfile(_pp):
        _np = 0
    else:
        try:
            _np = len([l for l in io.open(_pp, encoding="utf-8").read().split(u"\n") if l.strip()])
        except Exception:
            _np = -2
    print(u"  ⒞ 未结之痕（%s）⇒ %s"
          % (PEND_NAME,
             (u"⛔ 读（照实）" if _np < 0 else
              (u"0 行 ⇒ 无未结（**二投皆成**之面 ⇒ 此为正形）" if _np == 0 else
               u"%d 行 ⇒ **有未结**（有一败 ∨ 遭截 ⇒ 留 ＝ **正**）⇒ 须核其件" % _np))))
    print(u"     ⚠ 二支皆正 ⇒ ⛔ 以「余 0 行」为唯一正形（承 CEO 认令 §二.⒜）")
    print(u"     ⚠ 一齿：若余行 ⇒ 必核其件**在箱**（分「真未结」与「已销之残」· 承 CEO 裁 §二.⒝）")
    print(u"[总判] %s（二件并查 · 取刻 %s）"
          % (u"绿 ⇒ 二形皆 ⛔ 在" if ok else u"红 ⇒ 有在（核是否投中）", now_ts()))
    return 0 if ok else 2


# ---------------------------------------------------------------- main
def _num_auto(num):
    u"""`--num` 是否为取号之旗（唯字面 `auto` · ⛔ 大小写之外之魔法值）。"""
    return str(num).strip().lower() == u"auto"


def ledger_max_num(csv=None):
    u"""全账之**极大号**（跨日 · ⛔ 按「本日」滤）—— 号之底（全局单调）。

    ⭐ 修（`2026-10-10` 我一手所逮 · 应 `_pm/_投_auto.py` 齿⒞ 逐字所指）：
      病 ＝ `next_free_num` 唯取**本日**之号面 ⇒ **日界 ⇒ 新日之首件返 `1`**（破全局单调）。
      据（我一手 · 器取）：`10-08` `23:58:32` ⇒ `#2074` ∧ `10-09` `00:22:52` ⇒ `#2075`（跨日 ⛔ 断号）
        ⇒ 而 `10-10` 新日 ⇒ 器返 `1` ⇒ 断（我一手：全账极大 ＝ `2450`）。
      ⇒ 法 ＝ 底取**全账极大**（⛔ 按日）⇒ `n ＝ max(全账极大, 本日已用) ＋ 1` ⇒ 单调复。
    ⛔ 读账 ⇒ 报（照实）＋ 底 `0`（⛔ 静默）—— 下游 `_投_auto.py` 之齿⒞ 另有一闸。"""
    csv = face_csv(csv)
    best = 0
    try:
        with io.open(csv, encoding="utf-8-sig", newline=u"") as f:
            for r in csvmod.DictReader(f):
                _n = (r.get(u"序号") or u"").strip()
                if _n.isdigit() and int(_n) > best:
                    best = int(_n)
    except Exception as _e:
        print(u"⚠ 全账之极大号 ⛔ 取（%s）⇒ 底 ＝ 0（照实 · ⛔ 静默）" % type(_e).__name__)
    return best


def next_free_num(date, used=None, csv=None, box=None):
    u"""本日之号 ⇒ 唯「**底 ＋ 1**」（**全局单调** · `--num auto` 之取号处 · 一处定形）。

    ⭐ 承 PM 2141 §二 ／ CEO 2140 §六.2：取号唯在 **auto** 之下发生；显式号优先。
    ⚠ 正其言（承 CEO 2208 §二.6 ／ PM 2216 §三）：旧书「**最小空号**」为误 —— 实为 **极大 ＋ 1**
      （⛔ 补隙：补隙破「今日之号」之**单调** · 承 CEO 2153 §五.6）。
    ⭐ 取数面 ＝ `day_numbers`（**台账 ＋ 箱** 二源并取 · 明书以免「二源不书名」之假异）⇒ 与拒投之闸**同源**。
    ⭐ 底 ＝ `ledger_max_num`（**全账 · 跨日**）⇒ 日界 ⛔ 断号（修 `2026-10-10` · 见上）。"""
    csv, box = face_csv(csv), face_box(box)
    used = day_numbers(date, csv, box) if used is None else used
    _floor = ledger_max_num(csv)
    n = max([_floor] + list(used)) + 1
    while n in used:
        n += 1
    return n


# ------------------------------------------------- 号锁（原子占号 · 承 CEO 令 §一.⒉–⒋ · PM 2737）
#: 锁件之名（**箱内** ⇒ 与落箱同卷 ⇒ O_CREAT ｜ O_EXCL 得**原子**占号）
LOCK_NAME = u".号锁"
#: 陈旧之限（秒）：锁龄逾此 ∨ 其 pid ⛔ 在 ⇒ 可破（承 CEO 令 §一.⒋）
LOCK_STALE_SECONDS = 60
#: 争锁重试（tries × step ⇒ 累计 ≈ 2.0 s · ⛔ 长阻 · 承 CEO 令 §一.⒊）
LOCK_WAIT_TRIES = 40
LOCK_WAIT_STEP = 0.05


def lock_path(box=None, path=None):
    u"""锁件之全径 —— **随面而移**（承 CEO 令 §二.⒜）：path 显给 ∨ LOCK_OVERRIDE（--lock）
    ∨ <箱>/.号锁 ⇒ ⛔ 硬码器旁（否则隔离面之二进程仍争**真锁** ⇒ 面伪隔离）。"""
    if path:
        return path
    if LOCK_OVERRIDE:
        return LOCK_OVERRIDE
    return os.path.join(face_box(box), LOCK_NAME)


def _pid_alive(pid):
    u"""pid 是否在场 —— Win32 OpenProcess
    （⛔ os.kill：其于 Windows 会**真杀**进程 ⇒ 破锁之检 ⛔ 用）。"""
    try:
        import ctypes
        _k = ctypes.windll.kernel32
        _h = _k.OpenProcess(0x1000, False, int(pid))    # PROCESS_QUERY_LIMITED_INFORMATION
        if not _h:
            return False
        _k.CloseHandle(_h)
        return True
    except Exception:
        return False


def lock_read(p):
    u"""读锁件 ⇒ {pid, 刻}；⛔ 读 ∨ ⛔ 合 ⇒ 空表（照实 · 由破锁者报）。"""
    try:
        _o = json.loads(io.open(p, encoding="utf-8").read() or u"{}")
    except Exception:
        return {}
    return _o if isinstance(_o, dict) else {}


def lock_break_if_stale(p, stale=None, alive=_pid_alive):
    u"""陈旧之破（承 CEO 令 §一.⒋）：锁**龄 > stale** ∨ 其 **pid ⛔ 在** ⇒ 删 ＋ 返由（⛔ 静默）。"""
    stale = LOCK_STALE_SECONDS if stale is None else stale
    try:
        _age = time.time() - os.path.getmtime(p)
    except OSError:
        return None
    _pid = lock_read(p).get(u"pid")
    if _age > stale:
        _why = u"锁龄 %.1fs > %ds" % (_age, stale)
    elif _pid is not None and not alive(_pid):
        _why = u"pid %s ⛔ 在" % _pid
    else:
        return None
    try:
        os.remove(p)
    except OSError:
        return None
    return _why


def lock_acquire(box=None, tries=None, step=None, stale=None, alive=_pid_alive):
    u"""原子占号之锁（承 CEO 令 §一.⒊）：O_CREAT ｜ O_EXCL（同卷 ⇒ 原子）。

    得 ⇒ 返锁径（其内载 pid ＋ 刻）；败（EEXIST）⇒ 短等重试（累计 ≈ tries × step）。
    ⛔ 长阻：重试超限 ⇒ 返 None（由调用者报 ＋ 止 ⇒ rc 10）。
    """
    p = lock_path(box)
    tries = LOCK_WAIT_TRIES if tries is None else tries
    step = LOCK_WAIT_STEP if step is None else step
    for _i in range(tries):
        try:
            fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except OSError:
            _why = lock_break_if_stale(p, stale=stale, alive=alive)
            if _why:
                print(u"[号锁·破陈旧] %s ⇒ %s（承 CEO 令 §一.⒋ · ⛔ 静默）" % (p, _why))
                continue
            time.sleep(step)
            continue
        try:
            os.write(fd, json.dumps({u"pid": os.getpid(), u"刻": now_ts()},
                                    ensure_ascii=False).encode("utf-8"))
        finally:
            os.close(fd)
        return p
    return None


def lock_release(p):
    u"""释锁（幂等）：删锁件 ⇒ True；⛔ 得（已释 ∨ 已破）⇒ False（⛔ 报 —— 常事）。"""
    if not p:
        return False
    try:
        os.remove(p)
        return True
    except OSError:
        return False


#: 残件区之名（让号所生之孤件 ⇒ 移此 · 承 CEO 裁 2026-10-11 §二.⒜ · 准移 ⇔ ⛔ 删）
QUAR_NAME = u"_残件"


def quarantine_path(box=None):
    u"""残件区之径 ＝ 「<箱>/_残件」（随面而落 · 守则 ⒜）。"""
    return os.path.join(face_box(box), QUAR_NAME)


def quarantine_orphan(num, date, name, box=None, dry=False):
    u"""让号毕（重试之前）⇒ **移孤件出箱**（承 CEO 裁 §二.⒜ · 2026-10-11）。

    由：**箱 ＝ 件之唯一面**（他席以箱为证）⇒ 让号后之二件并存 ⇒ 恐**误读** ／ **误复投**。
    法：落 <箱>/_残件/（**保留原名** ⇒ 留证）＋ 并写未结痕一行（＝ 机逮之证）
    ⇒ **重试成 ⇒ 销其行** ⇒ ⛔ 删（准移 ⇔ ⛔ 删 ⇒ 留证）。
    ⭐ 幂等 ∧ 须在**号锁之内**（见 quarantine_locked · 免并发再撞）。
    """
    box = face_box(box)
    src = os.path.join(box, name)
    _q = quarantine_path(box)
    dst = os.path.join(_q, name)
    if dry:
        return u"残件·移（演）：%s ⇒ %s/（若在）" % (name, QUAR_NAME)
    if not os.path.isfile(src):
        if os.path.isfile(dst):
            return u"残件·移：幂等 ⇒ 已在 %s/（⛔ 再动）" % QUAR_NAME
        return u"残件·移：源 ⛔ 在（%s）⇒ 无事（照实）" % name
    try:
        if not os.path.isdir(_q):
            os.makedirs(_q)
        if os.path.exists(dst):
            os.remove(src)
            return u"残件·移：同名已在 %s/ ⇒ 删源（罕 · 照实报）" % QUAR_NAME
        os.replace(src, dst)
    except Exception as _e:
        return u"残件·移：⛔ 移（%s：%s）⇒ 照实报（⛔ 静默）" % (type(_e).__name__, _e)
    return u"残件·移：成 · %s ⇒ %s/（保留原名 ⇒ 留证 · ⛔ 删）" % (name, QUAR_NAME)


def quarantine_locked(num, date, name, box=None, dry=False):
    u"""quarantine_orphan 之**号锁壳**（入号锁之内 · 承 CEO 裁 §二.⒜）：先保痕 ⇒ 移。"""
    if dry:
        return quarantine_orphan(num, date, name, box=box, dry=True)
    _lk = lock_acquire(box)
    if _lk is None:
        return u"残件·移：号锁 ⛔ 得（争锁超限）⇒ ⛔ 移（照实 · 免伪面）"
    try:
        _m = pend_mark(num, date, name, box=box)
        return u"%s ｜ 痕：%s" % (quarantine_orphan(num, date, name, box=box), _m)
    finally:
        lock_release(_lk)


def pend_clear_safe(num, date, name, box=None, dry=False):
    u"""销痕之**号锁内销**（承 CEO 裁 §二.⒝）：读 ⇒ 改 ⇒ 写**入号锁之内** ⇒ 免互覆之窗。

    由：未结痕之证力 ＝ **独一之机逮** ⇒ 混假警 ⇒ 其值削 ⇒ 销之 RMW 须原子（同锁）。
    ⛔ 得锁（争锁超限）⇒ ⛔ 销 ＋ 照实报（宁留痕为假警 · ⛔ 伪绿）。
    """
    if dry:
        return pend_clear(num, date, name, box=box, dry=True)
    _lk = lock_acquire(box)
    if _lk is None:
        return u"未结·销：号锁 ⛔ 得（争锁超限）⇒ ⛔ 销（照实 · 宁假警 ⛔ 伪绿）"
    try:
        return pend_clear(num, date, name, box=box)
    finally:
        lock_release(_lk)


def one_pass(num, a, name, date, ts, recv, tid, dry, on_box_done=None):
    u"""一趟三步（① 落箱 ② 落行 ③ 醒）⇒ rc（一处编排 · ⛔ 自裁字面）。"""
    print(u"【投一步】%s ｜ 件 ＝ %s ｜ 席 ＝ %s（%s）｜ 号 ＝ %s ／ 日 ＝ %s ／ 类 ＝ %s"
          % (u"演（⛔ 落盘 · 加 --go 真办）" if dry else u"真办", name, a.to, tid, num, date, a.cat))
    if recv != a.to:
        print(u"落账之名（归一）＝ %s（别名「%s」唯作入 · ⛔ 入账 · 承 pm 1298 §二）" % (recv, a.to))
    print(u"刻（器取）＝ %s ／ 箱＝ %s" % (ts, path_label(XT)))
    if getattr(a, "need_file", None):
        print(u"need 之源 ＝ 自件之「动作需求」栏（%s · ⛔ 人手复述 · 承 PM 2216 一）" % a.need_file)
    _used_n = day_numbers(date)
    _rc_n, _msg_n = check_number(num, date, a.sender, name, used=_used_n)
    if _rc_n != 0:
        print(u"[号撞] " + _msg_n)
        print(u"[止] 号 ⛔ 可用 ⇒ **拒投**（承 pm_1889 §三 ／ pm_1894 §一 · ⛔ 静默改号 ／ ⛔ 代改）｜rc=%s" % _rc_n)
        return _rc_n
    print(u"本日之号面（近十）＝ %s" % num_face(_used_n))
    _rc_q, _msg_q = apply_seq_patch(a.src, num, dry=dry)
    print(_msg_q)
    if _rc_q != 0:
        print(u"[止] 件内 · 序号栏 不合 ⇒ ⛔ 续跑（三步须一处断）｜rc=%s" % _rc_q)
        return _rc_q
    skipped = []
    _box_ok = False
    def _step_wake():
        if FACE_ISO and not dry:
            return 0, (u"醒（⛔ 实发 · 隔离面）：若醒 ⇒ 致 %s（席 %s）—— 承 CEO 令 §二.⒝"
                       % (a.to, tid))
        return step_wake(name, tid, dry=dry)
    for label, fn in ((u"① 落箱", lambda: step_box(a.src, name, dry=dry)),
                      (u"② 落行", lambda: step_land(num, date, a.sender, recv, name, a.cat,
                                                     a.need, a.note, ts, dry=dry,
                                                     need_file=getattr(a, "need_file", None))),
                      (u"③ 醒", _step_wake)):
        rc, msg = fn()
        print(u"%s ⇒ %s" % (label, msg))
        if label == u"① 落箱" and rc == 0:
            _box_ok = True
            print(u"[未结之痕] " + pend_mark(num, date, name, dry=dry))
            if on_box_done is not None:
                on_box_done()
        if u"演·跳" in msg:
            skipped.append(label)
        if rc != 0:
            print(u"[止] %s 不合 ⇒ ⛔ 续跑（三步须一处断）｜rc=%s" % (label, rc))
            if _box_ok and label == u"② 落行":
                print(u"[孤件之齿] " + orphan_note(num, date, name, rc,
                                                    u"落行败（箱成 · rc=%s）" % rc, dry=dry))
            return rc
    if skipped:
        print(u"[总判] 演毕（rc 0 · ⚠ %s ⛔ 得验：件未在箱 ⇒ 真办方验）" % u"／".join(skipped))
    else:
        if _box_ok and not dry:
            print(u"[未结之痕] " + pend_clear_safe(num, date, name))
        print(u"[总判] 三步皆成（rc 0 · %s）" % (u"演" if dry else u"真办"))
    return 0

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
    ap.add_argument("--need-file", dest="need_file")   # ⭐ 自件取 need（一处出 · PM 2216 一）
    ap.add_argument("--ts", default=u"")
    ap.add_argument("--go", action="store_true")
    # ⭐ 探针一口（承 CEO 令 第⑤件 · PM 2740）：面之覆 ⇒ 隔离面（俾真并发之反例门可跑）
    ap.add_argument("--box")
    ap.add_argument("--csv")
    ap.add_argument("--lock")
    ap.add_argument("--audit-name-num", dest="audit_name_num", action="store_true")   # ⭐ 名之号 ≡ 行号 之逐次核（承 PM 2228 §四）
    ap.add_argument("--残留核", dest="residue", action="store_true")   # ⭐ 面五（残留）· 二件并查（承 CEO 令 §二.3）
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if getattr(a, "residue", False):
        return residue_report()
    if getattr(a, "audit_name_num", False):
        return audit_name_num_report()
    # ⭐ 面之覆（承 CEO 令 第⑤件）：--box ／ --csv ／ --lock ⇒ 覆模块活值 ⇒ 隔离面
    #   ｜⛔ 传口 ⇒ 默认面 ⛔ 变（守则 ⒜ 锁件随面而移 ∧ ⒝ 隔离面 ⛔ 真醒）。
    globals()["FACE_ISO"] = bool(a.box or a.csv or a.lock)
    if a.box:
        globals()["XT"] = a.box
    if a.csv:
        globals()["CSV"] = a.csv
    globals()["LOCK_OVERRIDE"] = a.lock or u""
    if FACE_ISO:
        print(u"[面] 隔离面（探针）：箱 ＝ %s ／ 台账 ＝ %s（默认面 ⛔ 变 · 承 CEO 令 第⑤件）"
              % (XT, CSV))
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
    # ⭐ need 之源（一处出 · 承 PM 2216 §一）：--need-file（自件之「动作需求」栏取）
    #   ⇒ ⛔ 人手复述 ／ ⛔ 壳自折；缺 ／ ⛔ 给 ⇒ 默认 = 本件（--src）。落行器唯折（一处）。
    if not a.need_file and not (a.need or u"").strip():
        a.need_file = a.src
    # ⭐ 号锁之全形（承 PM 2141 §二 · CEO 2140 §六.2 · 三闸）：
    #   ⒜ 唯字面 `--num auto` 方取号（显式号优先 · ⛔ 默认改自动 ⇒ 免静默改号）；
    #   ⒝ 让号须留痕（逐次印「让号·留痕」）；⒞ 锁之超时 ⇒ 报（在 号锁 ／ 落行器 · ⛔ 长阻）。
    # ⭐ 原子占号（修 2026-10-11 · 承 CEO 令 §一.⒉–⒋ · PM 2737）：临界区 ＝ 「取号 ⇒ 落箱毕」
    #   ⇒ lock_acquire（O_EXCL ⇒ 原子）⇒ 取号 ＋ one_pass（on_box_done 即释）⇒ finally 幂等释；
    #   争锁超限 ⇒ rc 10（⛔ 长阻）；陈旧（龄 > 60s ∨ pid ⛔ 在）⇒ 可破 ＋ 报一行。
    if _num_auto(a.num):
        _rc = 2
        _quar = []                            # ⭐ 让号所生之残件（重试成 ⇒ 销其痕 · 承 CEO 裁 §二.⒜）
        for _attempt in range(4):
            _lk = lock_acquire()
            if _lk is None:
                print(u"[号锁] 号锁 ⛔ 得（争锁累计 ≈ %.1fs）⇒ 报 ＋ 止（⛔ 长阻 · 承 CEO 令 §一.⒊）｜rc=10"
                      % (LOCK_WAIT_TRIES * LOCK_WAIT_STEP))
                return 10
            try:
                _cand = next_free_num(date)
                _nm2, _chg = name_with_num(name, _cand)
                if _chg:
                    print(u"[件名·号回填] %s ⇒ %s（名 ≡ 行号 · 承 CEO 2221 §八.3 ／ PM 2222 §四）" % (name, _nm2))
                elif name_num_aligned(name, _cand) is None:
                    print(u"[件名·号] ⛔ 件名无号位 ⇒ ⛔ 得回填（报 ＋ 拒 · 承 PM 2241 §一.3）｜书名 ＝ %s" % name)
                    return 4
                _rc = one_pass(_cand, a, _nm2, date, ts, recv, tid, dry,
                               on_box_done=lambda: lock_release(_lk))
            finally:
                lock_release(_lk)
            if _rc == 0 and _quar:
                for _qn, _qnm in _quar:      # ⭐ 重试成 ⇒ 销残件之痕（号锁内销 · 承 CEO 裁 §二.⒜）
                    print(u"[残件·销痕] " + pend_clear_safe(_qn, date, _qnm, dry=dry))
                _quar[:] = []
            if _rc in (6, 9, 11) and _attempt < 3:
                _why_n = {6: u"复合键已在", 9: u"号撞", 11: u"并发败（他席同刻已落）"}.get(_rc, u"?")
                print(u"[让号·留痕] 号 %d ⛔ 得（rc=%d ⇒ %s）⇒ 让 ⇒ 重取号 ＋ **重取契** ＋ 重试（第 %d 次 · 取数刻 %s）"
                      % (_cand, _rc, _why_n, _attempt + 1, now_ts()))
                print(u"[残件·移出] " + quarantine_locked(_cand, date, _nm2, dry=dry))
                if not dry:                  # ⚠ 演（⛔ --go）⇒ ⛔ 记残件（免真径之触 · 承守则 ⒝）
                    _quar.append((_cand, _nm2))
                print(ledger_seal())
                continue
            if _rc in (6, 9, 11):
                print(u"[让号·报] 让号之环 已尽（4 次 · 末 rc=%d ⇒ 号 %s）⇒ **报 ＋ 止**（⛔ 静默 · 承 CEO 认令 §二.⒝.⒝）"
                      % (_rc, _cand))
            return _rc
        return _rc
    _nm9, _chg9 = name_with_num(name, a.num)
    if _chg9:
        print(u"[件名·号回填] %s ⇒ %s（名 ≡ 行号 · 承 CEO 2221 §八.3 ／ PM 2222 §四）" % (name, _nm9))
    elif name_num_aligned(name, a.num) is None:
        print(u"[件名·号] ⛔ 件名无号位 ⇒ ⛔ 得回填（报 ＋ 拒 · 承 PM 2241 §一.3）｜书名 ＝ %s" % name)
        return 4
    return one_pass(a.num, a, _nm9, date, ts, recv, tid, dry)


if __name__ == "__main__":
    sys.exit(main())
