# -*- coding: utf-8 -*-
u"""客户端**离线包**之器（承 pm_1386 §二.2 ／ §一.1「便携自包含目录」）—— 打包 ＋ 核其全。

形（承 pm_1386 §一.1）：**目录即交付物** —— 内含 ① 本仓之**运行子集**（`PAYLOAD`）②
**wheel\\** 之离网依（`pip download` 于**有网**之机做一次）③ 本器 ＋ 安装器 ／ 卸载器 ／ 前置器
④ `bundle_manifest.json`（逐件 sha256 ＋ 依之表 ⇒ 供**净机核**）。

判「成」（承 §二.2 ⓕ 之离线）：**净机无网** ⇒ `pip install --no-index --find-links=wheel\\ -r
  requirements-runtime.txt` 可装完 ⇒ 网关可起 ∧ 首屏可开。**本器 ⛔ 自评「已通过」** ——
  离线之装须**净机**验之（候老板之净机 · M2）。

洁之闸（承 pm_1396 §二.5）：**活径之扫** —— 包内「活 ∧ 组织物」之径须 ＝ **0**
  （注 ／ docstring ／ `.md` 之例 ⛔ 判红）⇒ ⛔ 0 ⇒ `--go` 拒（免「组织物之径」入交付物）。
洁之闸·二（承 pm_1399 §一）：**⛔ gitignored 之产物** —— 运行子集里凡被 `.gitignore` 忽略之件
  ⇒ ⛔ 入包（皆本机之产物 · 如 `core/lib/scan_bom_baseline.json`；⚠ 其径可指组织物 ⇒ 亦「假绿」之口）。
  ⚠ git ⛔ 得用 ∨ 非仓 ⇒ 判「⛔ 得判」并按拒论（出包须自 **git 树** 出 · 承 pm_1396 §二.1）。
  ⚠ `--check` 之口径 ⛔ 含此条（所核者 ＝ 已成之包 · ⛔ git 树 ⇒ 无从判 · 唯 `plan` ／ `--go` 有之）。

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
import ast
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
#: ⭐ 运行子集里「剔之件」（相对 ROOT · 承 pm_1417 §二 之逐条裁）—— 密钥 ／ 本机态 ／ 机器相关 ／ 生成物。
#  由：`PAYLOAD` 唯按**目录**走 ⇒ 本机之产物亦入（同 `ignored_payload` 之族）⇒ 逐条剔之（⛔ 静默 · 见 `excluded_payload`）。
EXCLUDE = (
    "config/secrets.yaml",                     # 密钥（⛔ 入包 · 值皆 ${ENV} 之占位）
    "core/lib/filter_net.json",                # 本机产物（`gitignore:49` 运行期自学习写）
    "config/clawsjoy/memory/vector.yaml",      # 本机态（安装器立默认）
    "config/memory/memory_optimization.yaml",  # 本机态（安装器立默认）
    "config/v5/memory/config.yaml",            # 本机态（安装器立默认）
    "scripts/win_pa/ClawsJoy_PA_Boot.xml",     # 机器相关（由安装器生）
    "web/pa/ui_state.json",                    # 运行态（前端读不到 ⇒ 显「未知」 · ⛔ 崩）
    "web/ppt_thumbs/manifest.json",            # 生成物
)
_EXCLUDE_SET = frozenset(EXCLUDE)
#: 真源之必需节（⛔ 手拟 · 与 requirements.txt 同源）
SEC_PREFIX = u"运行依赖"


# ---------------------------------------------------------------- 洁之闸 · 「活径之扫」
# 承 pm_1396 §二.5：洁之闸加「活径之扫」—— 判「成」＝ 包内「活之组织物径」＝ 0。
# 口径（承 scripts/dev/scan_abs_paths.py · 同一式）：
#   类甲 绝对径：`[A-Za-z]:[\\/]` ／ `/mnt/[a-z]/` ／ `\\\\srv\\`（UNC）／ `/home/`。
#   类乙 组织物（径中含）：Obsidian/ClawsJoy ／ paseo-workspace ／ paseo-home ／ npm-global
#     ／ codex-home ／ 内容工坊 ／ _tools ／ _auto ／ _交付 ／ _老板 ／ 写小说专栏 ／ dsh。
#   载：`.py` 之 docstring（ast 取）／ 行注（# // * <!--）／ `.md` ⇒ **非活**；余 ⇒ **活**。
#   ⚠ 唯「活」者入闸（注 ／ docstring ／ .md 之例 ⇒ ⛔ 判红 · 承「⛔ 假红」）。
PAT_DRIVE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/](?![\\/])[^\s'\"\)\],;`]*")
PAT_MNT = re.compile(r"(?<![A-Za-z0-9])/mnt/[a-z]/[^\s'\"\)\],;`]*")
PAT_UNC = re.compile(r"(?<![\\\w])\\\\[A-Za-z0-9_.\-]+\\")
PAT_HOME = re.compile(r"(?<![A-Za-z0-9])/home/[A-Za-z0-9_.\-]+/")
ORG_MARKS = (u"Obsidian/ClawsJoy", u"Obsidian\\ClawsJoy", u"paseo-workspace", u"paseo-home",
             u"npm-global", u"codex-home", u"内容工坊", u"_tools", u"_auto",
             u"_交付", u"_老板", u"写小说专栏", u"\\dsh", u"/dsh")
#: 「开发机活径」之标（Windows 用户目录 —— 承 pm_1396 §二.5 之「今 29 ＋ 2」之 2）
#  ⚠ 以「拼」造之（⛔ 字面）—— 否则本器之**自身源**亦中其式 ⇒ 「器自指」之假红。
DEV_MARKS = (u"C:" + u"/Users/", u"C:" + BS + u"Users" + BS, u"/mnt/c/" + u"Users/")
_LINE_COMMENT = re.compile(r"^\s*(#|//|\*|/\*|<!--)")


def _docstring_lines(src):
    u"""`.py` 之 docstring 行号集（`ast` 取 · ⛔ 猜引号）。"""
    out = set()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None) or []
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                s = body[0].value.lineno
                e = getattr(body[0].value, "end_lineno", s)
                out.update(range(s, e + 1))
    return out


def scan_live_paths(root, files):
    u"""**活**之绝对径（剔 注 ／ docstring ／ `.md`）⇒ [{file,line,径,组织物}] —— 器取。

    ⚠ 唯「活」者 —— 注 ／ docstring 之例（如 `C:/Users/x`）⇒ ⛔ 入（⛔ 假红）。
    """
    rows = []
    for rel in files:
        if rel.lower().endswith(".md"):
            continue
        p = os.path.join(root, rel.replace("/", os.sep))
        try:
            src = io.open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        ds = _docstring_lines(src) if rel.lower().endswith(".py") else set()
        for i, line in enumerate(src.splitlines(), 1):
            if i in ds or _LINE_COMMENT.match(line):
                continue
            for pat in (PAT_DRIVE, PAT_MNT, PAT_UNC, PAT_HOME):
                for m in pat.finditer(line):
                    lit = m.group(0)
                    rows.append({"file": rel, "line": i, "径": lit,
                                 "组织物": any(k in lit for k in ORG_MARKS),
                                 "开发机": any(k in lit for k in DEV_MARKS)})
    return rows


def live_org_paths(root, files):
    u"""**活 ∧ 组织物**之径（判「成」＝ 空 · 承 pm_1396 §二.5）。"""
    return [r for r in scan_live_paths(root, files) if r["组织物"]]


def live_offenders(root, files):
    u"""**活 ∧（组织物 ∨ 开发机）**之径 —— 洁之闸之标的（判「成」＝ 空）。"""
    return [r for r in scan_live_paths(root, files) if r["组织物"] or r["开发机"]]


def ignored_payload(root, files):
    u"""**运行子集里被 `.gitignore` 忽略之件**（判「成」＝ 空 · 承 pm_1399 §一）—— **器取**。

    ⭐ 由：`_payload_files` 唯按 `PAYLOAD` 之诸目录走 ⇒ **本机之产物**亦入
      （如 `core/lib/scan_bom_baseline.json` —— `git check-ignore` 实锤）⇒ ⛔ 净（且其径可指组织物）。
    ⚠ 唯以 `git check-ignore` 为据（⛔ 自拟规则 ⇒ 必与 `.gitignore` 漂 —— 承「一名一义」之族）。
    ⚠ 返 `None` ＝ **⛔ 得判**（git ⛔ 用 ∨ 非仓）—— ⛔ 判绿（承「凡阴性须附面与刻」）；
      出包之路见此 ⇒ **按拒论**（副本 ＝ worktree ⇒ 有 git · 承 pm_1396 §二.1）。
    """
    if not files:
        return []
    try:
        # ⚠ 必以**字节**喂 stdin：`text=True` 在 Windows 会把 `\n` 译作 `\r\n`
        #   ⇒ git 收到 `path\r` ⇒ 与 `.gitignore` 之式 ⛔ 合 ⇒ **静默之假空**（我一手逮得 · 本刻）。
        r = subprocess.run(["git", "-C", root, "check-ignore", "--stdin"],
                           input="\n".join(files).encode("utf-8"), capture_output=True)
    except Exception:
        return None
    if r.returncode not in (0, 1):
        return None
    txt = (r.stdout or b"").decode("utf-8", "replace")
    return sorted(set(x.strip() for x in txt.splitlines() if x.strip()))


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


def _payload_walk(root):
    u"""运行子集之**全件**（剔 `__pycache__` ／ `.before_*` ／ 点件 · **⛔ 剔 `EXCLUDE`**）—— **器取**。"""
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


def _payload_files(root):
    u"""运行子集之**入包**之件（`_payload_walk` 剔 `EXCLUDE`）—— **器取**。"""
    return [x for x in _payload_walk(root) if x not in _EXCLUDE_SET]


def excluded_payload(root):
    u"""剔表里**实在**之件（剔何物之逐条报 · ⛔ 静默 · 承 pm_1417 §二）—— **器取**。"""
    return sorted(x for x in _payload_walk(root) if x in _EXCLUDE_SET)


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
    excluded = excluded_payload(root)
    live = scan_live_paths(root, files)
    return {"version": VERSION, "root": root, "out": out, "dists": dists,
            "payload_files": files, "payload_bytes": sum(
                os.path.getsize(os.path.join(root, f.replace("/", os.sep))) for f in files),
            "wheel_dir": os.path.join(out, "wheel"),
            "live_paths": live, "live_org": [r for r in live if r["组织物"]],
            "live_off": [r for r in live if r["组织物"] or r["开发机"]],
            "excluded": excluded,
            "ig_payload": ignored_payload(root, files)}


def check_bundle(path):
    u"""**只读**核：ⓐ wheel\\ 之依全 ／ 缺 ／ 多 ⓑ `bundle_manifest.json` 之印合 ／ 缺 ／ 异。"""
    man = os.path.join(path, "bundle_manifest.json")
    r = {"包": path, "有册": os.path.isfile(man), "依缺": [], "印缺": [], "印异": [],
         "印多": [], "活径": []}
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
    r["活径"] = live_offenders(path, _bundle_files(path))
    return r


#: 构建依（**必入 wheel\\**）—— 运行依含 sdist（如 `flasgger` 无 wheel）⇒ 装时须**构建**
#  ⇒ pip 于 `--no-index` 之下唯以 `find-links` 取构建依 ⇒ ⛔ 在 ⇒ 离线装必败
#  （我一手逮得 · 2026-10-06 M2 预演：`ERROR: Could not find a version that satisfies the
#   requirement setuptools>=40.8.0 (from versions: none)`）。
BUILD_DEPS = ("setuptools", "wheel")


def download_cmd(wheel_dir, reqs_path, python=None):
    u"""`pip download` 之 argv —— 运行依（`-r`）＋ **构建依**（`BUILD_DEPS`）⇒ 离线可装（承 pm_1440 §二.2）。"""
    return [python or sys.executable, "-m", "pip", "download", "-d", wheel_dir,
            "-r", reqs_path] + list(BUILD_DEPS)


def apply_bundle(root=None, out=None, wheel=True, json_out=False):
    u"""真做（⚠ 须**网**）—— ⓐ `pip download` 入 `wheel\\` ⓑ 复运行子集 ⓒ 写册（逐件 sha256）。
    ⛔ 起停 ／ ⛔ 改本仓（唯写 `out`）。"""
    p = plan_bundle(root, out)
    lines = [u"[bundle] out=%s ｜ 件 %d（%.1f MB）｜ 依 %d" % (
        p["out"], len(p["payload_files"]), p["payload_bytes"] / 1048576.0, len(p["dists"]))]
    if p["excluded"]:
        lines.append(u"[bundle] ⊘ 剔（⛔ 入包 · 承 pm_1417 §二）：%d 件" % len(p["excluded"]))
        for x in p["excluded"]:
            lines.append(u"  ⊘ %s" % x)
    if p["live_off"]:
        lines.append(u"[bundle] ⛔ 洁之闸（活径之扫）：包内「活 ∧（组织物 ∨ 开发机）」之径 %d 处 ⇒ 止"
                     u"（⛔ 入交付物 · 判「成」＝ 0 · 承 pm_1396 §二.5）" % len(p["live_off"]))
        for x in p["live_off"][:20]:
            lines.append(u"  · %s:%d  %s" % (x["file"], x["line"], x["径"]))
        return 2, lines
    if p["ig_payload"] is None:
        lines.append(u"[bundle] ⛔ 洁之闸·二（gitignored）：**⛔ 得判**（git ⛔ 用 ∨ 非仓）⇒ 止"
                     u"（出包须自 git 树出 · 承 pm_1399 §一）")
        return 2, lines
    if p["ig_payload"]:
        lines.append(u"[bundle] ⛔ 洁之闸·二（gitignored）：运行子集含被 `.gitignore` 忽略之件 %d ⇒ 止"
                     u"（本机之产物 ⛔ 入包 · 承 pm_1399 §一）" % len(p["ig_payload"]))
        for x in p["ig_payload"][:20]:
            lines.append(u"  · %s" % x)
        return 2, lines
    os.makedirs(p["wheel_dir"], exist_ok=True)
    if wheel:
        cmd = download_cmd(p["wheel_dir"], os.path.join(p["root"], "requirements-runtime.txt"))
        lines.append(u"[bundle] pip download（**须网** · 运行依 ＋ 构建依）：%s" % u" ".join(cmd))
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
    pd = os.path.join(t, "pl", "core", "pa")
    os.makedirs(pd)
    io.open(os.path.join(pd, "a.py"), "w", encoding="utf-8").write(
        'P = r"D:' + BS + 'paseo-workspace' + BS + '_tools"' + chr(10))
    io.open(os.path.join(pd, "b.py"), "w", encoding="utf-8").write(
        'u"""例：D:' + BS + BS + 'paseo-home"""' + chr(10) + 'Q = 1' + chr(10))
    io.open(os.path.join(pd, "c.py"), "w", encoding="utf-8").write(
        '# 注：D:' + BS + BS + 'Obsidian' + BS + 'ClawsJoy' + chr(10) + 'R = 2' + chr(10))
    _lp = scan_live_paths(os.path.join(t, "pl"),
                          ["core/pa/a.py", "core/pa/b.py", "core/pa/c.py"])
    say(len(_lp) >= 1 and all(x["file"] == "core/pa/a.py" for x in _lp),
        u"正控：活之组织物径必逮 ／ 注与 docstring ⛔ 入（⛔ 假红）")
    say(len(_lp) == 1 and _lp[0]["组织物"], u"反控：唯 a.py 之一处 · 且判「组织物」")
    say(len(live_org_paths(os.path.join(t, "pl"), ["core/pa/b.py", "core/pa/c.py"])) == 0,
        u"反控：唯注 ／ docstring ⇒ 活∧组织物 空（⛔ 假红）")
    io.open(os.path.join(pd, "d.py"), "w", encoding="utf-8").write(
        'U = "C:' + "/Users/" + 'flybo/x.pdf"' + chr(10))
    _lo = live_offenders(os.path.join(t, "pl"), ["core/pa/d.py"])
    say(len(_lo) == 1 and _lo[0]["开发机"] and not _lo[0]["组织物"],
        u"正控：开发机活径（用户目录之式）必逮 ／ 且判「开发机」（⛔ 混组织物）")
    io.open(os.path.join(pd, "e.py"), "w", encoding="utf-8").write(
        'V = "D:' + BS + 'other' + BS + 'x"' + chr(10))
    say(len(live_offenders(os.path.join(t, "pl"), ["core/pa/e.py"])) == 0,
        u"反控：寻常盘符径（⛔ 组织物 ∧ ⛔ 开发机）⇒ ⛔ 判红")
    say(len(required_dists()) >= 10 and "chromadb" in [_norm(d) for d in required_dists()],
        u"正控：真源之必需节含 chromadb（⚠ 若红 ⇒ 本机 requirements.txt 已漂）")
    _git = shutil.which("git")
    if not _git:
        print(u"  ⊘ 洁闸·二（gitignored）之反控：⛔ 跳（git ⛔ 在 PATH）—— ⛔ 入计（⛔ 判绿）")
    else:
        g = os.path.join(t, "g")
        os.makedirs(os.path.join(g, "core", "pa"))
        subprocess.run([_git, "-C", g, "init", "-q"], capture_output=True)
        io.open(os.path.join(g, ".gitignore"), "w", encoding="utf-8").write("core/pa/ig.json" + chr(10))
        io.open(os.path.join(g, "core", "pa", "ig.json"), "w", encoding="utf-8").write("{}" + chr(10))
        io.open(os.path.join(g, "core", "pa", "ok.py"), "w", encoding="utf-8").write("x=1" + chr(10))
        say(ignored_payload(g, ["core/pa/ig.json", "core/pa/ok.py"]) == ["core/pa/ig.json"],
            u"正控：gitignored 之件必逮 ／ 寻常之件 ⛔ 入（⛔ 假红）")
        say(ignored_payload(g, []) == [], u"反控：空表 ⇒ 空（⛔ 无谓 git 之调用）")
        say(ignored_payload(os.path.join(t, "nope"), ["a.py"]) is None,
            u"反控：⛔ 非仓 ⇒ 返 None（＝「⛔ 得判」· ⛔ 判绿）")
    # ⭐ 反控（承 pm_1417 §二）：剔表有齿 —— 入表之件必剔 ／ 寻常之件 ⛔ 误剔 ／ 剔何物可报
    ex = os.path.join(t, "ex")
    os.makedirs(os.path.join(ex, "config", "memory"))
    os.makedirs(os.path.join(ex, "core"))
    io.open(os.path.join(ex, "config", "secrets.yaml"), "w", encoding="utf-8").write("x" + chr(10))
    io.open(os.path.join(ex, "config", "memory", "memory_optimization.yaml"), "w", encoding="utf-8").write("x" + chr(10))
    io.open(os.path.join(ex, "core", "keep.py"), "w", encoding="utf-8").write("x=1" + chr(10))
    _pf = _payload_files(ex)
    say("config/secrets.yaml" not in _pf and "config/memory/memory_optimization.yaml" not in _pf,
        u"正控：剔表之件 ⇒ ⛔ 入包")
    say("core/keep.py" in _pf, u"反控：寻常之件 ⛔ 误剔（⛔ 假红）")
    say(excluded_payload(ex) == ["config/memory/memory_optimization.yaml", "config/secrets.yaml"],
        u"正控：剔何物之逐条报（逐件可见 · ⛔ 静默）")
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
        bad = bool(r["依缺"] or r["印缺"] or r["印异"] or r["活径"])
        if a.json:
            print(json.dumps(r, ensure_ascii=False, indent=1))
        else:
            print(u"[核] %s ｜ 册 %s" % (r["包"], u"在" if r["有册"] else u"⛔ 无"))
            print(u"  依缺 %d ／ 印缺 %d ／ 印异 %d ／ 印多 %d ／ 活∧组织物 %d" % (
                len(r["依缺"]), len(r["印缺"]), len(r["印异"]), len(r["印多"]), len(r["活径"])))
            for x in r["活径"][:10]:
                print(u"  ⛔ 活径: %s:%d  %s" % (x["file"], x["line"], x["径"]))
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
            print(u"  洁闸（活径之扫）：活 %d ／ 活∧组织物 %d ／ 活∧（组织物∨开发机）%d（判「成」＝ 0）" % (
                len(p["live_paths"]), len(p["live_org"]), len(p["live_off"])))
            for x in p["live_off"][:12]:
                print(u"    · %s:%d  %s" % (x["file"], x["line"], x["径"]))
            _ig = p["ig_payload"]
            print(u"  洁闸·二（⛔ gitignored 之产物）：%s（判「成」＝ 0）" % (
                u"⛔ 得判（git ⛔ 用 ∨ 非仓）" if _ig is None else u"%d 件" % len(_ig)))
            for x in (_ig or [])[:12]:
                print(u"    ⊘ %s" % x)
            print(u"  将动：① pip download -d %s -r requirements-runtime.txt ② 复运行子集 ③ 写册" % p["wheel_dir"])
        return 0
    rc, lines = apply_bundle(a.root, p["out"], wheel=True, json_out=a.json)
    for x in lines:
        print(x)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
