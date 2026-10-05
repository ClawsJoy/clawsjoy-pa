# -*- coding: utf-8 -*-
r"""投一步.py —— 件-投-醒 一步之器（落箱 ＋ 落行 ＋ 醒 · ⭐ 一处收三步）。

承：pm 1291 §四（**专批** · 令）｜pm 1290 §四（债一：件/投/醒 三步之原子性 · 「醒」之败须有显报）｜
    pm 1094 之照实（「1093」之 wake 未成 ⇒ send_receipts.jsonl hits 0 ⇒ 静默之病）。

其病（今）：写件 ／ 落行 ／ 醒 三步各手序 ⇒ 「醒」若败 ⇒ **静默**（唯靠对方复扫）。
本器：三步一处；⭐ **醒败返非零 ＋ 印书名 ＋ 印席 ＋ 印凭**（⛔ 静默）。

用法：
  python -X utf8 -B scripts\dev\投一步.py --src <草稿全路径> --to 项目经理 --num 1096 \
      --cat 报 --need X --note Y                # 默认 **演**（⛔ 落盘）
  （加 --go ⇒ 真办：落箱 ＋ 落行 ＋ 醒）
  python -X utf8 -B scripts\dev\投一步.py --self-test   # 自证（含 **反控**：醒必败 ⇒ 须返非零）
  ⚠ 席名（2026-10-06 承 pm 1294 §三 · 并收）：CW 席之**台账名** ＝ 「CodexWindows线」（⛔ SEATS 之「V9工程师·全史席」）
    ⇒ 二键并存 · **以台账之名为准**（投 CW 之件 ⇒ --to CodexWindows线 · 免 --to-id）。

退出码：0 = 三步皆成（演毕亦然）｜2 = 用法错｜3 = 草稿不在｜4 = 落箱败（BOM ／ CR ／ 箱内异）
        ｜5 = 落行败（透传其 rc）｜6 = 已落行（复合键在 ⇒ ⛔ 复落）｜7 = **醒败**｜8 = 已投（凭在 ⇒ ⛔ 复投）

界：⭐ 本器唯「编排」三步（⛔ 自撰字面 ／ ⛔ 自裁）；其三步之闸各归其器（落台账_行 ／ wake_send）。
"""
import argparse
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


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def now_ts():
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S") + "+08:00"


def now_date():
    return datetime.date.today().strftime("%Y-%m-%d")


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


# ---------------------------------------------------------------- 落箱
def step_box(src, name, dry=False, box=XT):
    u"""落箱：草稿 ⇒ 箱（信通）。⭐ 硬闸：⛔ BOM ／ ⛔ CR（须 LF）；箱内已同 ⇒ ⛔ 复写；异 ⇒ 拒。"""
    if not os.path.isfile(src):
        return 3, u"落箱：⛔ 草稿不在：%s" % src
    b = open(src, "rb").read()
    if b[:3] == b"\xef\xbb\xbf":
        return 4, u"落箱：⛔ 草稿带 BOM（信通之件须 ⛔ BOM）"
    if b"\r" in b:
        return 4, u"落箱：⛔ 草稿带 CR（信通之件须 LF）"
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
    import tempfile
    ok = True

    def res(name, got, want):
        nonlocal ok
        hit = (got == want)
        ok = ok and hit
        print(u"  %s %s ⇒ %s（期 %s）" % (u"OK " if hit else u"✗ ", name, got, want))

    tmp = tempfile.mkdtemp(prefix="tou1_")
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

    print(u"[总判] %s" % (u"PASS" if ok else u"FAIL"))
    return 0 if ok else 1


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--self-test", dest="selftest", action="store_true")
    ap.add_argument("--src")
    ap.add_argument("--name")
    ap.add_argument("--to")
    ap.add_argument("--to-id")
    ap.add_argument("--from", dest="sender", default=u"技术总监")
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
    tid = a.to_id or SEATS.get(a.to)
    if not tid:
        print(u"[用法错] 席位「%s」⛔ 在表 ⇒ 以 --to-id 明书（rc=2）｜表：%s"
              % (a.to, u" ／ ".join(sorted(SEATS))))
        return 2
    name = a.name or os.path.basename(a.src)
    date = a.date or now_date()
    ts = a.ts or now_ts()
    dry = not a.go
    print(u"【投一步】%s ｜ 件 ＝ %s ｜ 席 ＝ %s（%s）｜ 号 ＝ %s ／ 日 ＝ %s ／ 类 ＝ %s"
          % (u"演（⛔ 落盘 · 加 --go 真办）" if dry else u"真办", name, a.to, tid, a.num, date, a.cat))
    print(u"刻（器取）＝ %s ／ 箱 ＝ %s" % (ts, XT))
    skipped = []
    for label, fn in ((u"① 落箱", lambda: step_box(a.src, name, dry=dry)),
                      (u"② 落行", lambda: step_land(a.num, date, a.sender, a.to, name, a.cat,
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
