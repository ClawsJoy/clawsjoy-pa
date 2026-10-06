# -*- coding: utf-8 -*-
u"""build_runtime.py -- 造「自带运行时」（embed CPython 3.12 · 64 位 ＋ 构建期预装依赖）。

承 pm_1577（令）：
  §二裁一：**自带 CPython 3.12 · 64 位之 embed 版**（⛔ 净机预装 Python · ⛔ PyInstaller 冻结全应用）。
  §二裁二：**构建期预装** —— 以 embed 之 `python.exe` ＋ `wheel\\` 离线装齐
           （`--no-index --find-links=wheel`）⇒ 产物含全齐之 site-packages ⇒
           **净机 ⛔ 须 pip ∧ ⛔ 须网**（一处定形 —— ⛔ 装时现装）。
  §三.1：下 embed zip ⇒ 解入 `runtime\\` ⇒ 启 `site`（正 `python312._pth`）⇒ 离线装齐 ⇒ 报其果。

一处定形（⛔ 二源）：
  ⭐ 依之表 ＝ `make_client_bundle.required_dists()`（requirements.txt 之必需节）
  ⭐ 逐件验 ＝ `preflight_start.REQUIRED_DEPS`（(import 名, pip 名) 之表）
  ⭐ 版之判 ＝ `preflight_start.classify_python()`（CPython ∧ >= 3.12 ∧ 64 位）
  ⛔ 本器另写一遍（二源必漂）。

用法：
  python -X utf8 scripts\\win_pa\\build_runtime.py                       # 干跑（缺省 · 只印将动何物）
  python -X utf8 scripts\\win_pa\\build_runtime.py --go --out <目录>      # 真造
  python -X utf8 scripts\\win_pa\\build_runtime.py --go --out <目录> --zip <embed.zip> --pip-wheel <pip.whl>
  python -X utf8 scripts\\win_pa\\build_runtime.py --self-test
  python -X utf8 scripts\\win_pa\\build_runtime.py --check --out <目录>   # 唯核（⛔ 动）

退出码：0 = 成（含干跑 ／ 已在而 no-op）｜2 = 前置不足 ∨ 装败 ∨ 验败 ｜3 = 入口错
"""
import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import zipfile

if sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BS = chr(92)

#: embed 之钉（version ／ 件名 ／ 印 ／ 字节）—— 摘自 python.org（器取 · 本机一手）
EMBED_VERSION = u"3.12.10"
EMBED_FILE = u"python-3.12.10-embed-amd64.zip"
EMBED_URL = u"https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip"
EMBED_SHA256 = u"4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3"
EMBED_BYTES = 11133606
#: `._pth` 之正形（embed 之原形把 `import site` 注掉 ⇒ sys.path 无 site-packages ⇒ 依皆 import 败）
PTH_NAME = u"python312._pth"
ZIP_NAME = u"python312.zip"
SITEDIR = u"Lib" + BS + u"site-packages"
PTH_TAIL = u"\n\n# Uncomment to run site.main() automatically\nimport site\n"


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def patch_pth(text):
    u"""`._pth` 之正形（**一处定形**）：首行之 zip 名**照原**（⛔ 改）＋ 显列 `Lib\\site-packages` ＋ 启 `site`。"""
    lines = [l.strip() for l in (text or u"").replace(u"\r\n", u"\n").split(u"\n")]
    keep = [l for l in lines if l and not l.startswith(u"#")]
    zipname = keep[0] if keep else ZIP_NAME
    return zipname + u"\n.\n" + SITEDIR + PTH_TAIL


def pth_ok(text):
    u"""正形之判（幂等之据）：⛔ 合 ⇒ False（承「⛔ 静默」之族 · 须显形）。"""
    return patch_pth(text) == text


def reqs_path(payload):
    u"""依之表之径：**包内**（payload）优先 ⇒ 退本仓（一处定形 · ⛔ 二源）。"""
    p = os.path.join(payload, u"requirements-runtime.txt")
    return p if os.path.isfile(p) else os.path.join(ROOT, u"requirements-runtime.txt")


def payload_scripts(payload):
    r"""包内 `scripts\\win_pa`（验之步以**包内之码**跑 —— ⛔ 以本仓之码替之）。"""
    return os.path.join(payload, u"scripts", u"win_pa")


def sitepkgs(out):
    return os.path.join(out, u"Lib", u"site-packages")


def runtime_exe(out):
    return os.path.join(out, u"python.exe")


def _pf():
    u"""前置器（**一处出**）：版之判 ／ 依之表之验，皆承其出（⛔ 本器另写）。"""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    return __import__(u"preflight_start")


def _mc():
    u"""离线包器（**一处出**）：依之表（⛔ 本器另写「必需 16 件」之字面）。"""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    return __import__(u"make_client_bundle")


def required_dists():
    return list(_mc().required_dists(ROOT))


def guard_out(out):
    u"""⛔ 之守（要）：出径 ⛔ 空 ／ ⛔ 盘根 ／ ⛔ 含 ROOT（免把仓连根毁）。⇒ (ok, 人话之因)。"""
    o = os.path.abspath(out)
    if not o or o.rstrip(BS).endswith(u":"):
        return False, u"出径为空 ∨ 盘根：%s" % out
    if o == os.path.abspath(os.sep):
        return False, u"出径 ＝ 根：%s" % out
    if os.path.abspath(ROOT).startswith(o + os.sep) or o == os.path.abspath(ROOT):
        return False, u"出径含本仓（⇒ 连带删之险）：%s ⟷ ROOT %s" % (o, ROOT)
    return True, u""


def find_pip_wheel(explicit, wheel_dir):
    u"""引 pip 之 wheel：显给 ∨ wheel\\pip-*.whl ∨ 构建缓存（env PA_BUILD_CACHE）⇒ 径 ∨ None。"""
    if explicit:
        return explicit if os.path.isfile(explicit) else None
    cands = []
    if wheel_dir and os.path.isdir(wheel_dir):
        cands += sorted(os.path.join(wheel_dir, n) for n in os.listdir(wheel_dir)
                        if n.lower().startswith(u"pip-") and n.lower().endswith(u".whl"))
    cache = os.environ.get(u"PA_BUILD_CACHE") or u""
    c2 = os.path.join(cache, u"pip_wheel")
    if cache and os.path.isdir(c2):
        cands += sorted(os.path.join(c2, n) for n in os.listdir(c2)
                        if n.lower().startswith(u"pip-") and n.lower().endswith(u".whl"))
    return cands[0] if cands else None


def unpack_wheel(whl, dest):
    u"""轮之解（wheel 即 zip）⇒ dest（引 pip 之唯一法：embed 无 ensurepip · 承本机一手之探）。"""
    n = 0
    with zipfile.ZipFile(whl) as z:
        for info in z.infolist():
            if info.filename.endswith(u"/"):
                continue
            z.extract(info, dest)
            n += 1
    return n


def pip_cmds(exe, wheel, reqs):
    u"""装依之二令（**一处定形**）⇒ [(名, cmd)]。

    ⭐ 我一手逮（本机 · 2026-10-07）：embed 之 `._pth` ⇒ **`PYTHONPATH` 被屏** ⇒
      pip 之 **build isolation**（以 `PYTHONPATH` 喂后端）⇒ `BackendUnavailable:
      Cannot import \'setuptools.build_meta\'`（`flasgger` 唯 sdist ⇒ 必走 PEP517 建 ⇒ 必败）。
      ⇒ 取 ⒜ 先以**本包之轮**铺后端（`setuptools` ／ `wheel` ⇒ site-packages）
        ＋ ⒝ 装依加 `--no-build-isolation`（后端由**本环境** import ⇒ 承 `._pth` 之路）。
      ⛔ 取「去 `._pth`」（其正形为 embed 之根本 —— 承 `build_runtime` §三之正形）。
    """
    base = [exe, u"-X", u"utf8", u"-m", u"pip", u"install", u"--no-index",
            u"--find-links", wheel, u"--disable-pip-version-check"]
    seed = base + [u"setuptools", u"wheel"]
    main = base + [u"--no-build-isolation", u"-r", reqs]
    return [(u"铺后端", seed), (u"装依", main)]


def run(cmd, cwd=None, timeout=3600):
    print(u"   $ " + u" ".join(cmd))
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       encoding=u"utf-8", errors=u"replace", timeout=timeout)
    return r


def plan_lines(a):
    u"""干跑之诺（逐条）：将动何物 —— ⛔ 静默（承五约 ⓐ 之族）。"""
    lines = [
        u"[runtime] 1 取 embed：%s（%s ／ %d B ／ sha256 钉 %s）" % (a.zip or u"<须给>", EMBED_VERSION, EMBED_BYTES, EMBED_SHA256[:16]),
        u"[runtime] 2 解入：%s（先净 ⇒ 再解 ／ ⛔ 覆盖他物）" % a.out,
        u"[runtime] 3 正 `%s`：+%s ∧ 启 `import site`" % (PTH_NAME, SITEDIR),
        u"[runtime] 4 引 pip：%s（embed ⛔ 含 ensurepip ⇒ 以轮之 zip 解入）" % (a.pip_wheel or u"<须给>"),
        u"[runtime] 5 装依（二令）：%s"
        % u" ／ ".join(u"%s：%s" % (n, u" ".join(c)) for n, c in pip_cmds(runtime_exe(a.out), a.wheel, reqs_path(a.payload))),
        u"[runtime] 6 逐件验：%s（%d 包 · 承 preflight_start.REQUIRED_DEPS）" % (u"find_spec", len(_pf().REQUIRED_DEPS)),
        u"[runtime] 7 报：python --version 逐字 ／ pip list 之件数 ／ 体量 ／ 件数",
    ]
    return lines


def check(a):
    u"""唯核（⛔ 动）：版 ／ `._pth` ／ 依 ⇒ (ok, 报行)。"""
    exe = runtime_exe(a.out)
    rows = []
    if not os.path.isfile(exe):
        return False, rows + [u"[FAIL] ⛔ 见 %s" % exe]
    pth = os.path.join(a.out, PTH_NAME)
    t = io.open(pth, encoding=u"utf-8").read() if os.path.isfile(pth) else u""
    rows.append(u"[%s] `%s` 正形%s" % (u"OK" if pth_ok(t) else u"FAIL", PTH_NAME,
                                       u"" if pth_ok(t) else u"：逐字 ＝ %r" % t))
    r = run([exe, u"-X", u"utf8", u"-c",
             u"import sys,platform;print(platform.python_version(), platform.machine(), sys.maxsize>2**32)"])
    v = (r.stdout or u"").strip()
    rows.append(u"[%s] `python.exe --version` ⇒ %s" % (u"OK" if r.returncode == 0 else u"FAIL", v))
    ok_v = False
    if r.returncode == 0 and v:
        try:
            ver, mach, bits = v.split()
            ok_v, why, fix = _pf().classify_python(u"cpython", tuple(int(x) for x in ver.split(u".")), 64 if bits == u"True" else 32)
            rows.append(u"[%s] 版之判：%s%s" % (u"OK" if ok_v else u"FAIL", why, (u" ｜ " + fix) if fix else u""))
        except Exception as e:
            rows.append(u"[FAIL] 版之判败：%s" % e)
    r2 = run([exe, u"-X", u"utf8", u"-c",
              u"import sys;sys.path.insert(0,r'%s');import preflight_start as P;ok,why,fix=P.probe_deps();print(ok);print(why)"
              % payload_scripts(a.payload)])
    out = (r2.stdout or u"").strip().split(u"\n")
    ok_d = bool(out and out[0].strip() == u"True")
    rows.append(u"[%s] 依之验：%s" % (u"OK" if ok_d else u"FAIL", out[1] if len(out) > 1 else (r2.stderr or u"")[:200]))
    return (ok_v and ok_d), rows


def build(a):
    u"""真造 ⇒ (rc, 报行)。"""
    rows = []
    if not os.path.isdir(a.payload):
        return 2, [u"[FAIL] ⛔ 见包内之树（payload）：%s" % a.payload]
    if not os.path.isdir(a.wheel):
        return 2, [u"[FAIL] ⛔ 见 wheel 之目录：%s" % a.wheel]
    if not a.zip or not os.path.isfile(a.zip):
        return 2, [u"[FAIL] ⛔ 见 embed zip：%s（⛔ 静默）｜修之门：--zip <python-%s-embed-amd64.zip>" % (a.zip, EMBED_VERSION)]
    b = os.path.getsize(a.zip)
    h = sha256_file(a.zip)
    if h != EMBED_SHA256:
        return 2, [u"[FAIL] embed zip 之印 ⛔ 合：%s ⟷ 钉 %s（⛔ 以他件代 · 承「⛔ 假印」）" % (h, EMBED_SHA256)]
    rows.append(u"[OK] 1 embed zip：%s ｜ %d B（钉 %d B）｜ sha256 %s ≡ 钉" % (a.zip, b, EMBED_BYTES, h[:16]))
    whl = find_pip_wheel(a.pip_wheel, a.wheel)
    if not whl:
        return 2, rows + [u"[FAIL] ⛔ 见引 pip 之轮（embed ⛔ 含 ensurepip）：--pip-wheel <pip-*.whl>"]
    if os.path.isdir(a.out):
        if not a.clean:
            return 0, rows + [u"[--] 出径已在：%s ⇒ ⛔ 动（幂等）｜⛔ 重做 ⇒ 加 --clean" % a.out]
        shutil.rmtree(a.out)
    os.makedirs(a.out)
    with zipfile.ZipFile(a.zip) as z:
        z.extractall(a.out)
    rows.append(u"[OK] 2 解入：%s ｜ 件数 %d" % (a.out, sum(len(f) for _, _, f in os.walk(a.out))))
    pth = os.path.join(a.out, PTH_NAME)
    t0 = io.open(pth, encoding=u"utf-8").read()
    t1 = patch_pth(t0)
    io.open(pth, u"w", encoding=u"utf-8", newline=u"\n").write(t1)
    rows.append(u"[OK] 3 正 `%s`：%r ⇒ %r" % (PTH_NAME, t0[:30], t1[:40]))
    os.makedirs(sitepkgs(a.out), exist_ok=True)
    n = unpack_wheel(whl, sitepkgs(a.out))
    rows.append(u"[OK] 4 引 pip：%s ⇒ %s ｜ %d 件" % (os.path.basename(whl), sitepkgs(a.out), n))
    exe = runtime_exe(a.out)
    for name, cmd in pip_cmds(exe, a.wheel, reqs_path(a.payload)):
        r = run(cmd, cwd=a.out)
        tail = [l for l in (r.stdout or u"").split(u"\n") if l.strip()][-2:]
        rows.append(u"[%s] 5 %s ⇒ rc %d ｜ 尾：%s" % (u"OK" if r.returncode == 0 else u"FAIL",
                                                     name, r.returncode, u" ／ ".join(tail)))
        if r.returncode != 0:
            return 2, rows + [u"   ⛔ stderr 尾：%s" % (r.stderr or u"")[-600:]]
    ok, rws = check(a)
    rows += [u"[--] 6/7 " + x for x in rws]
    if not ok:
        return 2, rows
    return 0, rows


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument(u"--root", default=ROOT)
    ap.add_argument(u"--out", default=u"")
    ap.add_argument(u"--zip", default=u"")
    ap.add_argument(u"--pip-wheel", default=u"")
    ap.add_argument(u"--wheel", default=u"")
    ap.add_argument(u"--payload", default=u"")
    ap.add_argument(u"--clean", action=u"store_true")
    ap.add_argument(u"--check", action=u"store_true")
    ap.add_argument(u"--go", action=u"store_true")
    ap.add_argument(u"--json", action=u"store_true")
    ap.add_argument(u"--self-test", action=u"store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    a.out = a.out or os.path.join(ROOT, u"runtime")
    a.payload = a.payload or os.path.dirname(os.path.abspath(a.out))
    a.wheel = a.wheel or os.path.join(a.payload, u"wheel")
    a.zip = a.zip or os.path.join(os.environ.get(u"PA_BUILD_CACHE") or u"", EMBED_FILE)
    print(u"# build_runtime（pm_1577 §三.1）｜ ROOT＝%s ｜ 包内之树＝%s" % (ROOT, a.payload))
    ok, why = guard_out(a.out)
    if not ok:
        print(u"[FAIL] 出径之守：%s" % why)
        return 3
    if a.check:
        ok, rows = check(a)
        print(u"\n".join(rows))
        return 0 if ok else 2
    if not a.go:
        print(u"[runtime] 干跑（⛔ 动盘 · 加 --go 真做）")
        for l in plan_lines(a):
            print(l)
        print(u"[runtime] 前置预判：zip %s ｜ pip 轮 %s ｜ wheel 之依 %d 件"
              % (u"在" if os.path.isfile(a.zip) else u"⛔ 在",
                 os.path.basename(find_pip_wheel(a.pip_wheel, a.wheel) or u"") or u"⛔ 见",
                 len(required_dists())))
        return 0
    rc, rows = build(a)
    print(u"\n".join(rows))
    if a.json:
        print(json.dumps({u"rc": rc, u"out": a.out, u"rows": rows}, ensure_ascii=False))
    return rc


def self_test():
    u"""反控（⛔ 触盘 · ⛔ 网）：ⓐ `._pth` 之正形（幂等 ／ zip 名照原）ⓑ 出径之守 ⓒ ≥ 0。"""
    fails = []

    def say(ok, name):
        print(u"  %s %s" % (u"✓" if ok else u"✗", name))
        if not ok:
            fails.append(name)

    stock = u"python312.zip\r\n.\r\n\r\n# Uncomment to run site.main() automatically\r\n#import site\r\n"
    say(patch_pth(stock) == u"python312.zip\n.\n" + SITEDIR + PTH_TAIL, u"正控：原形 ⇒ 正形（启 site ＋ 列 site-packages）")
    say(pth_ok(patch_pth(stock)), u"正控：正形 ⇒ 幂等")
    say(not pth_ok(stock), u"正控：原形 ⇒ ⛔ 为正形（⛔ 静默过）")
    say(patch_pth(u"python313.zip\n.\n") .startswith(u"python313.zip\n.\n" + SITEDIR),
        u"正控：他版之 zip 名 ⇒ 照原（⛔ 改成 312）")
    say(patch_pth(u"") == ZIP_NAME + u"\n.\n" + SITEDIR + PTH_TAIL, u"正控：空 ⇒ 以 312 之默认")
    for bad in (u"", u"C:", u"C:" + BS, ROOT, os.path.dirname(ROOT)):
        ok, _ = guard_out(bad)
        say(not ok, u"反控：出径 ⛔ 许：%s" % (bad or u"<空>"))
    say(guard_out(os.path.join(ROOT, u"dist", u"rt"))[0] is True
        and guard_out(ROOT)[0] is False and guard_out(os.path.dirname(ROOT))[0] is False,
        u"正控：仓内子径 ⇒ 许 ／ 仓根与父径 ⇒ ⛔ 许")
    _seed, _main = pip_cmds(u"py.exe", u"w", u"r.txt")
    say(u"--no-build-isolation" in _main[1] and u"-r" in _main[1],
        u"正控：装依之令带 --no-build-isolation（embed 之 `._pth` ⇒ 隔绝不立 · 我一手逮）")
    say(u"setuptools" in _seed[1] and u"wheel" in _seed[1] and u"--no-index" in _seed[1],
        u"正控：铺后端之令（setuptools ／ wheel · 皆本包之轮）")
    say(u"--find-links" in _main[1] and u"--no-index" in _main[1],
        u"正控：装依之令离线（--no-index ∧ --find-links）")
    say(len(required_dists()) >= 10, u"正控：依之表 ≥ 10 件（承 make_client_bundle）")
    say(len(_pf().REQUIRED_DEPS) >= 10, u"正控：逐件验之表 ≥ 10 件（承 preflight_start）")
    total = 15
    print(u"=== build_runtime 自测 %d/%d %s ===" % (total - len(fails), total, u"通过" if not fails else u"败"))
    return 0 if not fails else 1


if __name__ == u"__main__":
    sys.exit(main(sys.argv[1:]))
