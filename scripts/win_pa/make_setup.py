# -*- coding: utf-8 -*-
u"""make_setup.py -- 造**真安装包** `ClawsJoyPA-Setup.exe`（承 pm_1577 §二 ／ §三 · 老板裁 ⒞）。

形（承 pm_1577 §二.3 ＋ §三.3 之裁）：
  ⒜ 运行时 ＝ 包内 `runtime\\`（**自带 CPython 3.12 · 64 位 ＋ 构建期预装之依** ⇒ 净机 ⛔ 须 Python ／ ⛔ 须网）
  ⒝ 载荷 ＝ `payload.zip`（**整树** ／ 以 `ZIP_STORED` 存 —— CAB 会再压 ⇒ ⛔ 双压之耗时）
  ⒞ 壳 ＝ **`iexpress` 之自解压 exe**（唯本机在之**免装**工具 · ⛔ Inno ／ ⛔ WiX ／ ⛔ NSIS ／ ⛔ 7-Zip）
     ⚠ iexpress 之限：**⛔ 子目录**（SourceFiles 唯平铺）⇒ **故以 zip 载树**（⛔ 逐件列 17,541 之 SED）；
       大包之限 `~2 GB`（本包约 950 MB ⇒ 在限内）；**无向导 ／ 无回滚** ⇒ 由 `install_pa.cmd` 自兜。
  ⒟ 入口 ＝ `install_pa.cmd`（iexpress 解入 `%TEMP%\\IXP*.TMP` ⇒ 跑之）⇒ 解 zip 入装根 ⇒ 调 `installer_post.py`

一条铁律：**包须自证其出处**（承 pm_1573 §二）⇒ 册之「源」（`commit` ／ `tree` ／ `刻`）随包入册
  ∧ 另落 `ClawsJoyPA-Setup.record.json`（器取之印 ＋ 源）。

用法：
  python -X utf8 scripts\\win_pa\\make_setup.py                        # 干跑（唯印将动何物）
  python -X utf8 scripts\\win_pa\\make_setup.py --go                   # 真造（zip ＋ exe）
  ... --dist dist\\client_v1 ｜ --out dist ｜ --name ClawsJoyPA-Setup
  ... --zip-only ｜ --reuse-zip ｜ --self-test ｜ --json
退出码：0 成 ｜ 2 前置不足 ∨ 造败 ｜ 3 入口错
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile

if sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BS = chr(92)
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
VERSION = u"1.0"

ENTRY = u"install_pa.cmd"
ZIP_NAME = u"payload.zip"
DEFAULT_DIST = os.path.join(u"dist", u"client_v1")
DEFAULT_OUT = u"dist"
DEFAULT_NAME = u"ClawsJoyPA-Setup"
#: ⛔ 入包之件（**须空** —— 承 pm_1565 §二.2 ⒟ · 净机之装须无本机之痕）
FORBIDDEN_TOP = (u"data", u"logs", u"web/pa/ui_state.json")


def sha256_file(p, buf=1 << 20):
    h = hashlib.sha256()
    with io.open(p, "rb") as f:
        for chunk in iter(lambda: f.read(buf), b""):
            h.update(chunk)
    return h.hexdigest()


def walk_tree(root):
    u"""树之件（相对 · 正斜杠）—— 剔 `__pycache__` ／ `.pyc` ／ `.before_*`（与出包同式）。"""
    out = []
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d != u"__pycache__" and not d.startswith(u".")]
        for fn in fns:
            if fn.endswith(u".pyc") or u".before_" in fn or fn.startswith(u"."):
                continue
            fp = os.path.join(dp, fn)
            out.append(os.path.relpath(fp, root).replace(os.sep, u"/"))
    return sorted(out)


def guard_dist(dist):
    u"""前置之守 ⇒ (ok, 人话之因)。⛔ 静默（承「⛔ 假成」）。"""
    if not os.path.isdir(dist):
        return False, u"⛔ 见包内之树：%s（先跑 make_client_bundle.py ＋ build_runtime.py）" % dist
    for rel in (u"runtime" + BS + u"python.exe", u"scripts" + BS + u"win_pa" + BS + u"installer_post.py",
                u"scripts" + BS + u"win_pa" + BS + u"uninstall_pa.py", u"bundle_manifest.json"):
        if not os.path.isfile(os.path.join(dist, rel)):
            return False, u"⛔ 见 %s ⇒ **⛔ 造**（净机无 Python ⇒ 自带运行时为要）" % rel
    for top in FORBIDDEN_TOP:
        p = os.path.join(dist, top.replace(u"/", os.sep))
        if os.path.exists(p):
            return False, u"⛔ 见「⛔ 入包」之件：%s ⇒ **⛔ 造**（本机之痕入包 ＝ 假读数）" % p
    return True, os.path.join(dist, u"runtime", u"python.exe")


def sed_text(stage, target_exe, friendly=u"ClawsJoy PA"):
    u"""iexpress 之 SED（**一处定形**）—— AppLaunched ＝ 入口；载荷唯二件（平铺 ⇒ 合 iexpress 之限）。"""
    return (u"[Version]\r\n"
            u"Class=IEXPRESS\r\n"
            u"SEDVersion=3\r\n"
            u"[Options]\r\n"
            u"PackagePurpose=InstallApp\r\n"
            u"ShowInstallProgramWindow=0\r\n"
            u"HideExtractAnimation=1\r\n"
            u"UseLongFileName=1\r\n"
            u"InsideCompressed=0\r\n"
            u"CAB_FixedSize=0\r\n"
            u"CAB_ResvCodeSigning=0\r\n"
            u"RebootMode=N\r\n"
            u"InstallPrompt=\r\n"
            u"DisplayLicense=\r\n"
            u"FinishMessage=\r\n"
            u"TargetName=" + target_exe + u"\r\n"
            u"FriendlyName=" + friendly + u"\r\n"
            u"AppLaunched=" + ENTRY + u"\r\n"
            u"PostInstallCmd=<None>\r\n"
            u"AdminQuietInstCmd=\r\n"
            u"UserQuietInstCmd=\r\n"
            u"SourceFiles=SourceFiles\r\n"
            u"[Strings]\r\n"
            u"FILE0=\"" + ENTRY + u"\"\r\n"
            u"FILE1=\"" + ZIP_NAME + u"\"\r\n"
            u"[SourceFiles]\r\n"
            u"SourceFiles0=" + stage + BS + u"\r\n"
            u"[SourceFiles0]\r\n"
            u"%FILE0%=\r\n"
            u"%FILE1%=\r\n")


def build_zip(dist, zpath, deflate=False):
    u"""载荷 zip（**平铺之外唯树** —— iexpress ⛔ 子目录 ⇒ 以 zip 载之）。⇒ (件数, 字节)。"""
    files = walk_tree(dist)
    comp = zipfile.ZIP_DEFLATED if deflate else zipfile.ZIP_STORED
    with zipfile.ZipFile(zpath, "w", comp, allowZip64=True) as z:
        for rel in files:
            z.write(os.path.join(dist, rel.replace(u"/", os.sep)), rel)
    return len(files), os.path.getsize(zpath)


def plan(dist, out, name):
    return {"version": VERSION, "dist": dist, "out": out, "name": name,
            "exe": os.path.join(out, name + u".exe"),
            "stage": os.path.join(out, u"_setup_stage"),
            "zip": os.path.join(out, u"_setup_stage", ZIP_NAME),
            "sed": os.path.join(out, u"_setup_stage", name + u".sed")}


def _gate(dist):
    u"""出包之硬闸（pm_1598 §二 令二）：以「包内 runtime ＋ 载荷」真跑 ⇒ (ok, rows)。"""
    try:
        if HERE not in sys.path:
            sys.path.insert(0, HERE)
        import make_client_bundle as M
    except Exception as e:
        return False, [u"[闸] ⛔ 见器 make_client_bundle：%s（⇒ 按驳论 · ⛔ 静绿）" % e]
    return M.release_gate(dist, live=True)


def build(dist, out, name, zip_only=False, reuse=False, deflate=False):
    rows = []
    ok, why = guard_dist(dist)
    if not ok:
        return 2, [u"[FAIL] 前置：%s" % why]
    rows.append(u"[OK] 前置：%s" % why)
    # ⭐ pm_1598 §二 令二：出包之**硬闸** —— ⛔ 过 ⇒ ⛔ 造（先于 zip ／ exe · 失早）
    _g_ok, _g_rows = _gate(dist)
    rows += _g_rows
    if not _g_ok:
        return 2, rows + [u"[FAIL] 出包之闸 ⛔ 过 ⇒ ⛔ 造（pm_1598 §二 令二）"]
    p = plan(dist, out, name)
    stage = p["stage"]
    os.makedirs(stage, exist_ok=True)
    zpath = p["zip"]
    n = 0
    if reuse and os.path.isfile(zpath):
        if not zipfile.is_zipfile(zpath):
            return 2, rows + [u"[FAIL] --reuse 而 %s 非 zip（⛔ 静默）" % zpath]
        with zipfile.ZipFile(zpath) as z:
            n = len(z.namelist())
        rows.append(u"[OK] 复用载荷：%s ｜ %d 件 ｜ %d B" % (zpath, n, os.path.getsize(zpath)))
    else:
        t0 = time.time()
        n, nb = build_zip(dist, zpath, deflate)
        rows.append(u"[OK] 载荷：%s ｜ %d 件 ｜ %d B ｜ %s ｜ %.1fs"
                    % (zpath, n, nb, u"deflate" if deflate else u"store", time.time() - t0))
    src_ok, src = copy_entry(stage)
    if not src_ok:
        return 2, rows + [u"[FAIL] 入口：%s" % src]
    rows.append(u"[OK] 入口：%s" % src)
    if zip_only:
        rows.append(u"[--] --zip-only ⇒ ⛔ 造 exe")
        return 0, rows
    sed = p["sed"]
    body = sed_text(stage, p["exe"], friendly=name)
    if sorted({c for c in body if ord(c) > 127}):
        return 2, rows + [u"[FAIL] SED 含非 ASCII 之字 ⇒ **⛔ 造**"
                          u"（iexpress 所认之码页 ⛔ 定：名 ⁄ 径 须尽 ASCII —— pm_1578 §二.3）"]
    with io.open(sed, "w", encoding=u"ascii", newline=u"") as fh:
        fh.write(body)
    rows.append(u"[OK] SED → %s（尽 ASCII · 码页 ⛔ 涉）" % sed)
    exe = p["exe"]
    t0 = time.time()
    r = subprocess.run([u"iexpress", u"/N", sed], capture_output=True, text=True,
                       encoding=u"utf-8", errors=u"replace", timeout=7200)
    if not os.path.isfile(exe):
        return 2, rows + [u"[FAIL] iexpress rc=%s 而 ⛔ 见 %s ⇒ **⛔ 以 rc 0 代「成」**"
                          % (r.returncode, exe),
                          u"       stderr 尾：%s" % (r.stderr or u"")[-500:]]
    sz = os.path.getsize(exe)
    h = sha256_file(exe)
    rows.append(u"[OK] exe：%s ｜ %d B ｜ %.1f MB ｜ sha256 %s ｜ %.1fs"
                % (exe, sz, sz / 1048576.0, h[:16], time.time() - t0))
    rows.append(u"[OK] 载荷件数（对洁闸「活」数之口径见 PM 报告）：%d" % n)
    rec = {"version": VERSION, "name": name, "exe": exe, "bytes": sz, "sha256": h,
           "payload_files": n, "entry": ENTRY, "dist": dist,
           "built_at": time.strftime(u"%Y-%m-%dT%H:%M:%S%z"), "source": source_stamp(dist)}
    rp = os.path.join(out, name + u".record.json")
    with io.open(rp, "w", encoding="utf-8", newline=u"") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False, indent=1))
    rows.append(u"[OK] 记：%s" % rp)
    rows.append(u"[OK] 源：%s" % json.dumps(rec["source"], ensure_ascii=False))
    return 0, rows


def copy_entry(stage):
    u"""入口入 stage —— **强制 CRLF**（批处理之要 · 本仓之 `.gitattributes` 为 `eol=lf`）。"""
    s = os.path.join(HERE, ENTRY)
    if not os.path.isfile(s):
        return False, u"⛔ 见 %s" % s
    d = os.path.join(stage, ENTRY)
    raw = io.open(s, "rb").read().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    io.open(d, "wb").write(raw)
    return True, d
    return True, d


def source_stamp(dist):
    p = os.path.join(dist, u"bundle_manifest.json")
    try:
        man = json.loads(io.open(p, encoding=u"utf-8").read())
    except Exception as e:
        return {u"册": u"⛔ 读不到（%s: %s）" % (type(e).__name__, e)}
    return {u"册": u"bundle_manifest.json", u"源": man.get(u"源") or u"⛔ 无「源」键"}


def self_test():
    fails = []
    hits = []

    def say(ok, name):
        hits.append(bool(ok))
        print(u"  %s %s" % (u"+" if ok else u"X", name))
        if not ok:
            fails.append(name)

    stage = u"C:" + BS + u"__stage__"
    sed = sed_text(stage, u"C:" + BS + u"out" + BS + u"X.exe")
    say(u"PackagePurpose=InstallApp" in sed, u"正控：SED 之式（自解压 ＋ 跑安装程）")
    say(u"AppLaunched=" + ENTRY in sed, u"正控：AppLaunched ＝ 入口 %s" % ENTRY)
    say(u"TargetName=C:" + BS + u"out" + BS + u"X.exe" in sed, u"正控：TargetName 为**绝对径**（iexpress 之要）")
    say(u"%FILE0%=" in sed and u"%FILE1%=" in sed, u"正控：载荷唯二件（⛔ 逐件列树 ⇒ 合 iexpress 平铺之限）")
    say(ZIP_NAME in sed and ENTRY in sed, u"正控：二件之名在 SED")
    say(u"SourceFiles0=" + stage + BS in sed, u"正控：源目录为**绝对径**（SED 之径为构建期之绝对径）")
    say(sed.count(u"\n") == sed.count(u"\r\n"), u"正控：SED 全 CRLF（iexpress 之要）")
    say(sorted({c for c in sed if ord(c) > 127}) == [],
        u"正控：SED 尽 ASCII（iexpress 所认之码页 ⛔ 涉 ⇒ 丌下之争自消 · pm_1578 §二.3）")
    _eb = io.open(os.path.join(HERE, ENTRY), "rb").read()
    say(sorted({b for b in _eb if b > 127}) == [],
        u"正控：入口 %s 尽 ASCII（cmd 依台之码页解 .cmd 之字节 ⇒ CJK 则吞字节 · pm_1578 §二.2）" % ENTRY)
    say(b"chcp 65001" in _eb,
        u"正控：入口首行之码页已定（一处定形）")
    import tempfile
    t = tempfile.mkdtemp(prefix=u"cjpa_ms_")
    try:
        os.makedirs(os.path.join(t, u"rt", u"Lib"))
        for rel in (u"rt" + BS + u"python.exe", u"a.py", u"rt" + BS + u"Lib" + BS + u"b.pyd"):
            io.open(os.path.join(t, rel), "wb").write(b"x")
        io.open(os.path.join(t, u"x.pyc"), "wb").write(b"x")
        os.makedirs(os.path.join(t, u"__pycache__"))
        io.open(os.path.join(t, u"__pycache__", u"z.pyc"), "wb").write(b"x")
        got = walk_tree(t)
        say(got == [u"a.py", u"rt/Lib/b.pyd", u"rt/python.exe"], u"正控：树之列（剔 pyc ／ pycache ⇒ %s）" % got)
        z = os.path.join(t, u"p.zip")
        n, nb = build_zip(t, z)
        with zipfile.ZipFile(z) as zz:
            names = sorted(zz.namelist())
        say(names == got and n == 3, u"正控：zip 之条目名**正斜杠**（bsdtar 之要）⇒ %s" % names)
        say(all(u"\\" not in x for x in names), u"反控：zip ⛔ 含反斜杠之条目")
        bad = os.path.join(t, u"bad")
        os.makedirs(os.path.join(bad, u"runtime"))
        io.open(os.path.join(bad, u"runtime", u"python.exe"), "wb").write(b"x")
        ok, why = guard_dist(bad)
        say((not ok) and (u"installer_post.py" in why or u"uninstall_pa.py" in why),
            u"反控：⛔ 见自带运行时之件 ⇒ **⛔ 造**（⛔ 静默）")
        good = os.path.join(t, u"good")
        for rel in (u"runtime", u"scripts" + BS + u"win_pa"):
            os.makedirs(os.path.join(good, rel))
        for rel in (u"runtime" + BS + u"python.exe", u"bundle_manifest.json",
                    u"scripts" + BS + u"win_pa" + BS + u"installer_post.py",
                    u"scripts" + BS + u"win_pa" + BS + u"uninstall_pa.py"):
            io.open(os.path.join(good, rel), "wb").write(b"x")
        ok_g, _wg = guard_dist(good)
        say(ok_g, u"正控：齐备之树 ⇒ guard 过")
        os.remove(os.path.join(good, u"bundle_manifest.json"))
        ok2, why2 = guard_dist(good)
        say((not ok2) and (u"bundle_manifest.json" in why2) and (u"⛔ 造" in why2),
            u"反控：⛔ 见册 ⇒ **⛔ 造**")
        io.open(os.path.join(good, u"bundle_manifest.json"), "wb").write(b"x")
        os.makedirs(os.path.join(good, u"data"))
        io.open(os.path.join(good, u"data", u"x.txt"), "wb").write(b"x")
        ok3, why3 = guard_dist(good)
        say((not ok3) and (u"⛔ 入包" in why3),
            u"反控：data" + BS + u" 入包 ⇒ **⛔ 造**（本机之痕）")
    finally:
        shutil.rmtree(t, ignore_errors=True)
    src = io.open(__file__, encoding=u"utf-8").read()
    say(u"tar" in io.open(os.path.join(HERE, ENTRY), encoding=u"utf-8").read(),
        u"正控：入口以 tar 解 zip（Windows 10 1803+ 自带）")
    say(u"Expand-Archive" in io.open(os.path.join(HERE, ENTRY), encoding=u"utf-8").read(),
        u"正控：tar 不可用之支在（PowerShell 兜底）")
    say(src.count(u"shutil.rm" + u"tree(") == 1
        and (u"shutil.rm" + u"tree(t, ignore_errors=True)") in src,
        u"反控：器 ⛔ 删产物（唯自测之 temp 清理）—— ⛔ 删权归老板")
    print(u"=== make_setup 自测 %d/%d ===" % (sum(hits), len(hits)))
    print(u"[self-test] %s" % (u"PASS" if not fails else u"FAIL"))
    for f in fails:
        print(u"  [FAIL] %s" % f)
    return 0 if not fails else 2


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument(u"--dist", default=u"")
    ap.add_argument(u"--out", default=u"")
    ap.add_argument(u"--name", default=DEFAULT_NAME)
    ap.add_argument(u"--go", action=u"store_true")
    ap.add_argument(u"--zip-only", action=u"store_true")
    ap.add_argument(u"--reuse-zip", action=u"store_true")
    ap.add_argument(u"--deflate", action=u"store_true")
    ap.add_argument(u"--json", action=u"store_true")
    ap.add_argument(u"--self-test", action=u"store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    dist = a.dist or os.path.join(ROOT, DEFAULT_DIST)
    out = a.out or os.path.join(ROOT, DEFAULT_OUT)
    p = plan(dist, out, a.name)
    if not a.go:
        print(u"# make_setup（pm_1577 §三.3）｜ ROOT＝%s" % ROOT)
        print(u"[setup] 干跑（⛔ 动盘 · 加 --go 真造）")
        ok, why = guard_dist(dist)
        print(u"[setup] 前置：%s" % (u"OK ⇒ %s" % why if ok else why))
        print(u"[setup] 1 载荷：%s（ZIP_STORED ⇒ CAB 再压 · ⛔ 双压）" % p["zip"])
        print(u"[setup] 2 入口：%s" % ENTRY)
        print(u"[setup] 3 SED：%s（PackagePurpose=InstallApp ／ AppLaunched=%s）" % (p["sed"], ENTRY))
        print(u"[setup] 4 exe：iexpress /N <sed> ⇒ %s" % p["exe"])
        print(u"[setup] 5 记：%s（含 sha256 ＋ 册之「源」）" % os.path.join(out, a.name + u".record.json"))
        return 0
    rc, rows = build(dist, out, a.name, zip_only=a.zip_only, reuse=a.reuse_zip, deflate=a.deflate)
    if a.json:
        print(json.dumps({"rc": rc, "rows": rows}, ensure_ascii=False))
    else:
        for x in rows:
            print(x)
    return rc


if __name__ == u"__main__":
    sys.exit(main(sys.argv[1:]))