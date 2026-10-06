# -*- coding: utf-8 -*-
u"""客户端**离线包**之器（承 pm_1386 §二.2 ／ §一.1「便携自包含目录」）—— 打包 ＋ 核其全。

形（承 pm_1386 §一.1）：**目录即交付物** —— 内含 ① 本仓之**运行子集**（`PAYLOAD`）②
**wheel\\** 之离网依（`pip download` 于**有网**之机做一次）③ 本器 ＋ 安装器 ／ 卸载器 ／ 前置器
④ `bundle_manifest.json`（逐件 sha256 ＋ 依之表 ⇒ 供**净机核**）。

判「成」（承 §二.2 ⓕ 之离线）：**净机无网** ⇒ `pip install --no-index --find-links=wheel\\ -r
  requirements-runtime.txt` 可装完 ⇒ 网关可起 ∧ 首屏可开。**本器 ⛔ 自评「已通过」** ——
  离线之装须**净机**验之（候老板之净机 · M2）。

用法：
  python -X utf8 scripts\\win_pa\\make_client_bundle.py                    # 干跑（印计划 ＋ 估体积）
  python -X utf8 scripts\\win_pa\\make_client_bundle.py --go               # 真做（须**网**：pip download）
  python -X utf8 scripts\\win_pa\\make_client_bundle.py --check <包之径>    # **只读**核：依全 ∨ 缺 ＋ 印合
  python -X utf8 scripts\\win_pa\\make_client_bundle.py --json
  python -X utf8 scripts\\win_pa\\make_client_bundle.py --self-test
退出码：0 ＝ 干跑 ／ 核全 ｜ 2 ＝ 有缺（依缺 ∨ 印不合）｜ 3 ＝ 入口错 ｜ 1 ＝ 器自错
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BS = chr(92)
VERSION = 1
#: 运行子集（相对 ROOT）—— 「本仓之运行子集」（承 pm_1386 §一.1）
PAYLOAD = ("agent_gateway_enhanced.py", "requirements.txt", "requirements-runtime.txt",
           "pyproject.toml", "config", "core", "routes", "web", "scripts/win_pa")
#: 复本时之剔（⛔ 入包）
SKIP_NAMES = ("__pycache__", ".git", "data", "logs", "dist", "node_modules", ".venv")
#: 真源之必需节（⛔ 手拟 · 与 requirements.txt 同源）
SEC_PREFIX = u"运行依赖"


def _norm(n):
    u"""PEP 503 名之归一（⛔ 则 `PyYAML` ⟷ `pyyaml` 判二物）。"""
    return re.sub(r"[-_.]+", "-", str(n)).strip().lower()


def required_dists(root=None):
    u"""必需之 **pip 发行名**（自 `requirements.txt` 之「运行依赖（必需）」诸节 · ⛔ 手拟）。"""
    p = os.path.join(root or ROOT, "requirements.txt")
    sec, out = "", []
    for ln in io.open(p, encoding="utf-8").read().splitlines():
        s = ln.strip()
        if s.startswith("#"):
            m = re.search(r"=\s*([^=]+?)\s*=", s)
            if m:
                sec = m.group(1).strip()
            continue
        s = s.split("#")[0].strip()
        if not s or not sec.startswith(SEC_PREFIX):
            continue
        m = re.match(r"^([A-Za-z0-9][A-Za-z0-9_.\-]*)", s)
        if m:
            out.append(m.group(1))
    return out


def wheel_names(wheel_dir):
    u"""`wheel\\` 之件 ⇒ 其**发行名**（归一）之集 —— 轮子（`.whl`）＋ 源码包（`.tar.gz`）。"""
    got = set()
    if not os.path.isdir(wheel_dir):
        return got
    for fn in os.listdir(wheel_dir):
        if fn.endswith(".whl"):
            got.add(_norm(fn.split("-")[0]))
        elif fn.endswith((".tar.gz", ".zip")):
            got.add(_norm(re.split(r"-\d", fn)[0]))
    return got


def missing_wheels(wheel_dir, dists):
    u"""缺之**发行名**（⛔ 留空 ⇒ 「离线可装」之说 ⛔ 立）。"""
    got = wheel_names(wheel_dir)
    return [d for d in dists if _norm(d) not in got]


def _payload_files(root):
    u"""运行子集之**件**（剔 `__pycache__` ／ `.before_*` ／ `__pycache__` 之流）—— **器取**。"""
    out = []
    for rel in PAYLOAD:
        p = os.path.join(root, rel.replace("/", os.sep))
        if os.path.isfile(p):
            out.append(rel)
            continue
        if not os.path.isdir(p):
            continue
        for dp, dns, fns in os.walk(p):
            dns[:] = [d for d in dns if d not in SKIP_NAMES and not d.startswith(".")]
            for fn in fns:
                if fn.endswith(".pyc") or ".before_" in fn or fn.startswith("."):
                    continue
                fp = os.path.join(dp, fn)
                out.append(os.path.relpath(fp, root).replace(os.sep, "/"))
    return sorted(out)


def _bundle_files(path):
    u"""包内之件（剔 `wheel/**` ／ 册 ／ `__pycache__`）—— 供「**册外之件**」之判（⛔ 静默吞）。

    ⚠ ⛔ 以 `PAYLOAD` 走（那是**本仓**之表）—— 包之径 ⛔ 含本仓之诸目录 ⇒ 必**凡走**。
    """
    out = []
    for dp, dns, fns in os.walk(path):
        dns[:] = [d for d in dns if d not in SKIP_NAMES and not d.startswith(".")]
        for fn in fns:
            if fn.endswith(".pyc") or ".before_" in fn or fn.startswith("."):
                continue
            rel = os.path.relpath(os.path.join(dp, fn), path).replace(os.sep, "/")
            if rel.startswith("wheel/") or rel == "bundle_manifest.json":
                continue
            out.append(rel)
    return sorted(out)


def _sha256(path):
    h = hashlib.sha256()
    with io.open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def plan_bundle(root=None, out=None):
    root = root or ROOT
    out = out or os.path.join(root, "dist", "client_v1")
    dists = required_dists(root)
    files = _payload_files(root)
    return {"version": VERSION, "root": root, "out": out, "dists": dists,
            "payload_files": files, "payload_bytes": sum(
                os.path.getsize(os.path.join(root, f.replace("/", os.sep))) for f in files),
            "wheel_dir": os.path.join(out, "wheel")}


def check_bundle(path):
    u"""**只读**核：ⓐ wheel\\ 之依全 ／ 缺 ／ 多 ⓑ `bundle_manifest.json` 之印合 ／ 缺 ／ 异。"""
    man = os.path.join(path, "bundle_manifest.json")
    r = {"包": path, "有册": os.path.isfile(man), "依缺": [], "印缺": [], "印异": [], "印多": []}
    if not r["有册"]:
        r["依缺"] = missing_wheels(os.path.join(path, "wheel"), required_dists())
        return r
    j = json.loads(io.open(man, encoding="utf-8").read())
    r["依缺"] = missing_wheels(os.path.join(path, "wheel"), [d for d in j.get("依之表", [])])
    seen = set()
    for f in j.get("件之表", []):
        rel, want = f.get("rel"), f.get("sha256")
        seen.add(rel)
        fp = os.path.join(path, rel.replace("/", os.sep))
        if not os.path.isfile(fp):
            r["印缺"].append(rel)
        elif _sha256(fp) != want:
            r["印异"].append(rel)
    for f in _bundle_files(path):
        if f not in seen:
            r["印多"].append(f)
    return r


def apply_bundle(root=None, out=None, wheel=True, json_out=False):
    u"""真做（⚠ 须**网**）—— ⓐ `pip download` 入 `wheel\\` ⓑ 复运行子集 ⓒ 写册（逐件 sha256）。
    ⛔ 起停 ／ ⛔ 改本仓（唯写 `out`）。"""
    p = plan_bundle(root, out)
    lines = [u"[bundle] out=%s ｜ 件 %d（%.1f MB）｜ 依 %d" % (
        p["out"], len(p["payload_files"]), p["payload_bytes"] / 1048576.0, len(p["dists"]))]
    os.makedirs(p["wheel_dir"], exist_ok=True)
    if wheel:
        cmd = [sys.executable, "-m", "pip", "download", "-d", p["wheel_dir"],
               "-r", os.path.join(p["root"], "requirements-runtime.txt")]
        lines.append(u"[bundle] pip download（**须网**）: %s" % u" ".join(cmd))
        r = subprocess.run(cmd)
        if r.returncode != 0:
            lines.append(u"[bundle] ⛔ pip download rc=%d ⇒ 止（离线包不立 —— ⛔ 装成可用）" % r.returncode)
            return 2, lines
    miss = missing_wheels(p["wheel_dir"], p["dists"])
    if miss:
        lines.append(u"[bundle] ⛔ wheel\\ 仍缺 %d：%s ⇒ 离线 ⛔ 可装" % (len(miss), u"、".join(miss[:8])))
        return 2, lines
    entries = []
    for rel in p["payload_files"]:
        src = os.path.join(p["root"], rel.replace("/", os.sep))
        dst = os.path.join(p["out"], rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with io.open(src, "rb") as a, io.open(dst, "wb") as b:
            b.write(a.read())
        entries.append({"rel": rel, "sha256": _sha256(dst), "bytes": os.path.getsize(dst)})
    man = {"version": VERSION, "依之表": p["dists"], "件之表": entries,
           "口径": u"离线包：wheel\\ 之依全 ∧ 运行子集之 sha256；⛔ 含模型（须另下）"}
    io.open(os.path.join(p["out"], "bundle_manifest.json"), "w", encoding="utf-8", newline="").write(
        json.dumps(man, ensure_ascii=False, indent=1))
    lines.append(u"[bundle] 立毕：件 %d ｜ 依 %d ｜ 册 bundle_manifest.json" % (len(entries), len(p["dists"])))
    return 0, lines


def self_test():
    u"""反控（⛔ 离机 · ⛔ 起停）：ⓐ 缺轮 ⇒ 必逮 ⓑ 全轮 ⇒ ⛔ 假红 ⓒ 册之外 ⇒ 判「印多」。"""
    fails, hits = [], []

    def say(ok, name):
        hits.append(bool(ok))
        print(u"  %s %s" % (u"✓" if ok else u"✗", name))
        if not ok:
            fails.append(name)

    import shutil
    import tempfile
    t = tempfile.mkdtemp(prefix="p102_bundle_")
    try:
        w = os.path.join(t, "wheel")
        os.makedirs(w)
        say(missing_wheels(w, ["flask", "PyYAML"]) == ["flask", "PyYAML"], u"正控：空 wheel ⇒ 皆缺")
        io.open(os.path.join(w, "Flask-3.1.3-py3-none-any.whl"), "w").write("")
        io.open(os.path.join(w, "PyYAML-6.0.3-cp312-cp312-win_amd64.whl"), "w").write("")
        say(missing_wheels(w, ["flask", "PyYAML"]) == [], u"反例：全轮 ⇒ 缺空（⛔ 假红）")
        say(missing_wheels(w, ["flask-cors"]) == ["flask-cors"], u"反例：一包之名 ⛔ 混（flask ⟷ flask-cors）")
        say(_norm("PyYAML") == _norm("pyyaml") == "pyyaml", u"正控：名之归一")
        # 册：件在而印异 ⇒ 判「印异」
        io.open(os.path.join(t, "a.py"), "w").write("x=1\n")
        io.open(os.path.join(t, "bundle_manifest.json"), "w", encoding="utf-8").write(
            json.dumps({"依之表": ["flask"], "件之表": [{"rel": "a.py", "sha256": "0" * 64}]}))
        r = check_bundle(t)
        say(r["印异"] == ["a.py"], u"正控：印不合 ⇒ 判「印异」")
        io.open(os.path.join(t, "a.py"), "w").write("x=2\n")
        r2 = check_bundle(t)
        say("a.py" in r2["印异"], u"正控：改件 ⇒ 印随即变")
    finally:
        shutil.rmtree(t, ignore_errors=True)
    say(len(required_dists()) >= 10 and "chromadb" in [_norm(d) for d in required_dists()],
        u"正控：真源之必需节含 chromadb（⚠ 若红 ⇒ 本机 requirements.txt 已漂）")
    n, tt = sum(1 for c in hits if c), len(hits)
    print(u"=== 离线包器自测 %d/%d 通过（%s）===" % (n, tt, u"rc=0" if n == tt else u"rc=2"))
    return 0 if n == tt else 2


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--out", default="")
    ap.add_argument("--go", action="store_true")
    ap.add_argument("--check", default="")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    if a.check:
        if not os.path.isdir(a.check):
            print(u"[bundle] ⛔ 入口错：--check 之径不在：%s" % a.check)
            return 3
        r = check_bundle(a.check)
        bad = bool(r["依缺"] or r["印缺"] or r["印异"])
        if a.json:
            print(json.dumps(r, ensure_ascii=False, indent=1))
        else:
            print(u"[核] %s ｜ 册 %s" % (r["包"], u"在" if r["有册"] else u"⛔ 无"))
            print(u"  依缺 %d ／ 印缺 %d ／ 印异 %d ／ 印多 %d" % (
                len(r["依缺"]), len(r["印缺"]), len(r["印异"]), len(r["印多"])))
            for k in ("依缺", "印缺", "印异"):
                for x in r[k][:10]:
                    print(u"  ⛔ %s: %s" % (k, x))
        return 2 if bad else 0
    p = plan_bundle(a.root, a.out or None)
    if not a.go:
        if a.json:
            print(json.dumps(p, ensure_ascii=False, indent=1))
        else:
            print(u"[干跑] out=%s（⛔ 未动盘 —— 加 --go 方真做 · 须网）" % p["out"])
            print(u"  件 %d（%.1f MB）｜ 依 %d：%s" % (
                len(p["payload_files"]), p["payload_bytes"] / 1048576.0, len(p["dists"]),
                u"、".join(p["dists"])))
            print(u"  将动：① pip download -d %s -r requirements-runtime.txt ② 复运行子集 ③ 写册" % p["wheel_dir"])
        return 0
    rc, lines = apply_bundle(a.root, p["out"], wheel=True, json_out=a.json)
    for x in lines:
        print(x)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
