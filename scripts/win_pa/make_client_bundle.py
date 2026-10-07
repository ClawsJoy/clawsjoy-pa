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
import datetime
import hashlib
import io
import json
import os
import re
import shutil
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
    # ⭐ pm_1478 §一：同族（机器生成 · `gitignore:59`）—— `apply_bundle()`
    #   之 `ignored_payload`（`git check-ignore`）实锤 ⇒ 盖闸·二 = 1 ⇒ 「⇒ 止」（rc 2）。
    #   其读者 `core/gateway/registry.py:188` 有 `.exists()` 守 ⇒ **可选**（客机首跑再生）。
    "core/lib/dependency_graph.json",          # 本机产物（`gitignore:59` · `code_entity_extractor` 就地改写）
    "config/clawsjoy/memory/vector.yaml",      # 本机态（安装器立默认）
    "config/memory/memory_optimization.yaml",  # 本机态（安装器立默认）
    "config/v5/memory/config.yaml",            # 本机态（安装器立默认）
    "scripts/win_pa/ClawsJoy_PA_Boot.xml",     # 机器相关（由安装器生）
    "web/pa/ui_state.json",                    # 运行态（前端读不到 ⇒ 显「未知」 · ⛔ 崩）
    "web/ppt_thumbs/manifest.json",            # 生成物
    # ⭐ pm_1580 §二.1：本机之活配置（含个人邮箱）⇒ ⛔ 入包
    "config/alert_config.json",
    "config/scheduler_config.json",
    # ⭐ pm_1656 §三.1 ／ §三.2：**旧演示之陈**（唯引 `web/images/` 者）
    #   ⇒ 随图一并出包（**⛔ 留「开了就空」之面** —— 承「恒虚之支」之戒）。
    #   其链：`web/app_complete.py` ⇒ `web/clawsjoy_story.html` ⇒ 二演示页 ⇒ `web/images/`。
    "web/comic_gallery.html",
    "web/image_compare.html",
    "web/clawsjoy_story.html",
)
_EXCLUDE_SET = frozenset(EXCLUDE)
#: ⭐ 剔之**前缀**（pm_1656 §三.1）：**静态大件** —— `web/images`
#  （370.5 MB · 1882 张 hash 名 `.jpg`）⇒ ⛔ 在运行之闭包
#  （一手：`core/gateway/sandbox_seed.py:33` 之 `SEED_EXCLUDE`）⇒ 出包。
#  ⚠ `web/mobile`（65.3 MB）**本件 ⛔ 剔**：其有**活路由**
#  （`agent_gateway_enhanced.py:310` 挂 `web_bp` · `web/routes.py:17` 之 `/mobile/`）
#  ⇒ 非纯打包之事（`web/**` 属 CW 之域）⇒ 候 PM 裁（报于回件）。
EXCLUDE_PREFIX = ("web/images/",)


def banned_dir_names():
    u"""已剔之前缀之**目录名**（**一处定形** · pm_1656 §三.2）
    ⇒ 供 `ref_scan` ∧ 其齿共用（**⛔ 本处另列**）。"""
    return tuple(sorted({q.strip(u"/").split(u"/")[-1] for q in EXCLUDE_PREFIX if q.strip(u"/")}))


def ref_scan(line, names=None):
    u"""行里「引已剔之目录」之判（**一处定形**）——
    ⚠ 由 `EXCLUDE_PREFIX` 驱动（**⛔ 剔者 ⇒ ⛔ 报** —— 免「假红」，
    如 `web/mobile/` 今本⛔剔 ⇒ 其引者 `web/routes.py` ⇒ 合）。"""
    for n in (names if names is not None else banned_dir_names()):
        for tok in (u"/" + n + u"/", u"'" + n + u"/", u'"' + n + u"/"):
            if tok in line:
                return True
    return False
#: 「引已剔之前缀」之判（**一处定形** · pm_1656 §三.2）
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
             u"_交付", u"_老板", u"写小说专栏", u"\\dsh", u"/dsh",
             # ⭐ pm_1468 §二.2：**开发机之仓根**（二树）—— 旧表漏之 ⇒ 洁闸盲区；
             #    「组织物」之一；⛔ 那二路径在客户机 ⛔ 在 ⇒ 入包 即 坏。
             u"clawsjoy_v9", u"clawsjoy_build")
#: ⭐ 活径之扫之**域**（承 pm_1577 §三.3 之「洁闸之果须 0」· 我一手之探）：
#   ⒜ 「活径」唯**文本之件**之谓 —— 二进制（`.exe` ／ `.dll` ／ `.pyd` ／ `.whl` ／ `.zip`）
#     以注音式读 ⇒ **噪**（我一手：CPython 之 `python312.dll` ／ 第三方 `.pyd` 内嵌**其 CI 之建径**
#     ⇒ `C:/Users/runneradmin/…` 3,381 处 ⇒ **假红** · 承「⛔ 假红」）。
#   ⒝ `runtime\` ＝ **自带运行时**（embed CPython ＋ PyPI 之轮 · **第三方之件**）
#     ⇒ ⛔ 本仓之源 ⇒ 其内之字面 ⛔ 作「本仓泄径」之证 ⇒ 扫 ⛔ 及（**明书** · 报 PM 裁）。
#   ⚠ 「本仓之码」仍全扫（正控 —— 见 self_test）。
SCAN_SKIP_PREFIX = (u"runtime/",)


def _is_text(b):
    u"""文本 ∨ 二进制（含 NUL ⇒ 二进制；UTF-8 严译败 ⇒ 二进制）—— 器取。"""
    if b"\x00" in b[:4096]:
        return False
    try:
        b.decode(u"utf-8")
        return True
    except Exception:
        return False


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
        if any(rel.startswith(x) for x in SCAN_SKIP_PREFIX):
            continue
        p = os.path.join(root, rel.replace("/", os.sep))
        try:
            raw = io.open(p, "rb").read()
        except Exception:
            continue
        if not _is_text(raw):
            continue
        src = raw.decode("utf-8", "replace")
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


#: 净树之闸之「唯可之未跟踪」（出包之产物 · 相对仓根 · pm_1591 §二.1）
TREE_ALLOW_UNTRACKED = ("dist/",)
#: `git status --porcelain` 之码 ⇒ 人话（报必可读 · 承「⛔ 静默」）
_PORCELAIN_ZH = {"M": "改", "D": "删", "R": "改名", "C": "复本", "A": "新增",
                 "U": "冲突", "T": "型变", "?": "未跟踪", "!": "被忽略"}


def guard_tree(root=None, payload_files=None, allow_untracked=TREE_ALLOW_UNTRACKED):
    u"""⭐ **净树之闸**（pm_1589 §三.1 ／ pm_1591 §二 ／ pm_1606 §二.4）—— 出包之**第一步**。

    其由（pm_1588 §六.1）：载荷**自工作树取件**（⛔ git 树）⇒ 本机之痕（未提交之 `port: 5103`）
      **静**入包（同族者：`web/pa/ui_state.json` ／ `.bak` 之碎屑）⇒ 须以闸锁之。
    口径（三）：
      ⒜ `M` ／ `D` ／ `R` …（**跟踪件之改 ／ 删 ／ 改名**）⇒ **止**
      ⒝ `??`（**未跟踪**）⇒ 唯 `dist/` 之属可（＝出包之产物 · `TREE_ALLOW_UNTRACKED`）／ 余 ⇒ **止**
      ⒞ `!!`（**被忽略而实在** · 如 `*.bak` 之碎屑）⇒ 唯**载荷之内**者计 ⇒ 委 `ignored_payload`
         （**一处定形** —— ⛔ 自拟 ignore 之则 ⇒ 必与 `.gitignore` 漂）
    ⚠ 其闸为**一处**（唯此一形）∧ 置于出包之**冠首**（⛔ 各径各判 · pm_1591 §二.3）。
    ⚠ 「⛔ 得判」（git ⛔ 用 ／ 非仓）⇒ **按拒论**（承「凡阴性须附面与刻」· ⛔ 判绿）。
    ⚠ ⛔ 自动净树（⛔ 代删用户之未跟踪件 · pm_1591 §二.2）—— 唯**报** ＋ 指净树之法。
    返 `(ok, rows)`。
    """
    root = root or ROOT
    rows = [u"[净树] 仓＝%s（唯 `%s` 之未跟踪可 · pm_1606 §二.4）" % (root, u"` ／ `".join(allow_untracked))]
    cmd = ["git", "-C", root, "-c", "core.quotepath=false", "status", "--porcelain"]
    try:
        r = subprocess.run(cmd, capture_output=True)
    except Exception as e:
        rows.append(u"[净树] ⛔ 得判（git ⛔ 可调）：%s ⇒ 按拒论（⛔ 判绿）" % e)
        return False, rows
    if r.returncode != 0:
        err = (r.stderr or b"").decode("utf-8", "replace").strip()[:200]
        rows.append(u"[净树] ⛔ 得判（`git status` rc=%d）：%s ⇒ 按拒论（⛔ 判绿）" % (r.returncode, err))
        return False, rows
    txt = (r.stdout or b"").decode("utf-8", "replace")
    bad, ok_un = [], []
    for ln in txt.splitlines():
        if len(ln) < 4:
            continue
        code, path = ln[:2].strip(), ln[3:].strip()
        if code == "??" and path.replace(BS, "/").startswith(tuple(allow_untracked)):
            ok_un.append(path)
            continue
        zh = u" ／ ".join(_PORCELAIN_ZH.get(c, c) for c in code)
        bad.append(u"%s  %s（%s）" % (code, path, zh))
    files = _payload_files(root) if payload_files is None else payload_files
    ig = ignored_payload(root, files)
    if ig is None:
        rows.append(u"[净树] ⒞ ⛔ 得判（`git check-ignore` ⛔ 用 ／ 非仓）⇒ 按拒论（⛔ 判绿）")
        return False, rows
    rows.append(u"[净树] ⒜⒝ 改 ／ 删 ／ 未跟踪：%d 处（未跟踪而可者 %d：%s）"
                % (len(bad), len(ok_un), u" ／ ".join(ok_un) or u"无"))
    for x in bad[:20]:
        rows.append(u"  ⛔ %s" % x)
    rows.append(u"[净树] ⒞ 载荷内之「被忽略」：%d 处%s"
                % (len(ig), (u"：" + u" ／ ".join(ig[:20])) if ig else u""))
    ok = (not bad) and (not ig)
    rows.append(u"[净树] 判：%s" % (u"净 ⇒ 可（出包之第一步）" if ok else
                                  u"**⛔ 净** ⇒ ⛔ 止（逐件点名 ⇒ 先净树：`git checkout -- <件>` ／ 移出 ／ 入 `.gitignore`）"))
    return ok, rows


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


# ---------------------------------------- 载荷之判据（pm_1598 §二 令一 · 换轴）
# 病：`PAYLOAD` 为**手写白名单** ⇒ `engine` ／ `agents` ／ `gateway_endpoint.py` 之缺**闸不响**
#   （其「册」与「印」同出一单 ⇒ **以清单自证清单**）⇒ 净机「启动不了」之根。
# 换轴：**载荷 ＝ 资产白名单 ∪ 入口之导入闭包**（器：同域之 `import_closure.py` · ⛔ 手拟）。
def closure_payload(root=None):
    u"""闭包 ⇒ 须入载荷之诸径：其件在**顶**者 ⇒ 其件（如 `gateway_endpoint.py`）；
    在**夹**者 ⇒ 其**顶之夹**（连带其资产 —— 如 `agents/<名>/config.yaml`，静态闭包 ⛔ 见）。"""
    root = root or ROOT
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import import_closure as _ic
    out, _third, _unres = _ic.closure(root)
    add = []
    for rel in sorted(out):
        r = rel.replace(os.sep, "/")
        if "/" in r:
            top = r.split("/")[0]
        else:
            top = r
            if not os.path.isfile(os.path.join(root, top.replace("/", os.sep))):
                continue   # 裸之命名空间夹（无件）⇒ ⛔ 缠其夹（如 `scripts/` ⇒ 入开发物）
        if top not in add:
            add.append(top)
    return add


def effective_payload(root=None):
    u"""运行子集 ＝ 资产白名单 `PAYLOAD` **∪** 闭包所须之顶（一处定形 · pm_1598 令一）。"""
    out = list(PAYLOAD)
    for t in closure_payload(root):
        if t not in out:
            out.append(t)
    return tuple(out)


def _payload_walk(root):
    u"""运行子集之**全件**（剔 `__pycache__` ／ `.before_*` ／ 点件 · **⛔ 剔 `EXCLUDE`**）—— **器取**。"""
    out = []
    for rel in effective_payload(root):
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
    u"""运行子集之**入包**之件（`_payload_walk` 剔 `EXCLUDE` ／ `EXCLUDE_PREFIX`）—— **器取**。"""
    return [x for x in _payload_walk(root)
            if x not in _EXCLUDE_SET and not x.startswith(EXCLUDE_PREFIX)]


def excluded_prefix_payload(root):
    u"""前缀剔表里**实在**之件（逐条可见 · ⛔ 静默 · pm_1656 §三.1）—— **器取**。"""
    return sorted(x for x in _payload_walk(root) if x.startswith(EXCLUDE_PREFIX))


#: ⭐ 悬链之扫之**面**（pm_1656 §三.2 之「一处定形」）：**唯扫可现之面**
#  （`.html` ／ `.js` ／ `.css`）。⇒ 由：**「开了就空」唯面之病**
#  （⛔ 面者 ⇒ ⛔ 空）；而 `.py` ／ `.json` ／ `.txt` 之「提及其名」
#  多入**注 ／ 文档 ／ 器自身**（如本器之 `EXCLUDE_PREFIX` 字面）
#  ⇒ **假红之源**（一红即 ⛔ 出包 ⇒ 器之自重 ⛔ 值）。
DANGLING_FACE_EXT = (".html", ".js", ".css")


def dangling_refs(root, files):
    u"""⭐ 悬链之齿（pm_1656 §三.2）：出包之**面**若引「已出包之物」⇒ 开则空 ⇒ 逐条报。

    由：承「凡面之支 ⇒ 须能真达」（⛔ 恒虚之支）—— `web/images/` ／ 三演示页既出包
    ⇒ 凡引其者（页 ／ 脚本 ／ 样式）须一并处置（剔 ／ 换明书 ／ 改远端）
    ⇒ 否则 **红**（⛔ 以 rc 0 代「成」）。
    ⚠ 界二条（一处定形）：
      ① **唯扫面**（`DANGLING_FACE_EXT`）—— `.py` ／ `.json` ／ `.txt` 之名
        多入注 ／ 文档 ／ 器自身 ⇒ 假红之源（如本器之 `EXCLUDE_PREFIX` 字面）；
      ② **唯查前缀**（`EXCLUDE_PREFIX`），⏔ 查整件之剔（`EXCLUDE`）——
        其缺多**可容**（如 `web/pa/ui_state.json`：面有「未应答」之路 ⇒ 照实）
        且其名**必现于读数之面** ⇒ 混则假红。
    """
    out = []
    for rel in files:
        if not rel.lower().endswith(DANGLING_FACE_EXT):
            continue
        fp = os.path.join(root, rel.replace("/", os.sep))
        try:
            with io.open(fp, "rb") as fh:
                raw = fh.read(400000)
        except OSError:
            continue
        if not _is_text(raw):
            continue
        for i, line in enumerate(raw.decode("utf-8", "ignore").splitlines(), 1):
            if ref_scan(line):
                out.append({"file": rel, "line": i, "文": line.strip()[:100]})
    return out


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


#: 自带运行时之件（供入册）—— 剔 `__pycache__` ／ 点件（与运行子集同式）
#: ⚠ 自带运行时之**剔之名**（**一处定形**）—— ⛔ 用本仓之 `SKIP_NAMES`！
#   我一手速（pm_1577 §三.3）：`SKIP_NAMES` 含 `logs` ／ `data`（为**本仓之生成物**而设）
#   而 site-packages 里 `opentelemetry/proto/collector/logs/` 乃**真代码**
#   ⇒ 以之剔则 `ModuleNotFoundError: No module named 'opentelemetry.proto.collector.logs'`
#   。本树唯剔：`__pycache__` ／ `.git` ／ `node_modules` ／ `.venv` ／ 点件（缓存与 VCS 之属）。
RUNTIME_SKIP_NAMES = ("__pycache__", ".git", "node_modules", ".venv",)


def _runtime_walk(src):
    u"""自带运行时之**入册**之件（相对 `src` · 剔 `__pycache__` ／ `.pyc` ／ 点件）。"""
    out = []
    for dp, dns, fns in os.walk(src):
        dns[:] = [d for d in dns if d not in RUNTIME_SKIP_NAMES and not d.startswith(".")]
        for fn in fns:
            if fn.endswith(".pyc") or ".before_" in fn or fn.startswith("."):
                continue
            fp = os.path.join(dp, fn)
            out.append(os.path.relpath(fp, src).replace(os.sep, "/"))
    return sorted(out)


def _sha256(path):
    h = hashlib.sha256()
    with io.open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def _git_out(args, cwd):
    u"""git 之一行（**只读** · ⛔ 起停 · 失败 ⇒ `None`）—— 一处定形（pm_1573 §二）。"""
    try:
        r = subprocess.run(["git", "-C", cwd] + list(args), capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
    except Exception:
        return None
    if r.returncode != 0:
        return None
    return (r.stdout or "").strip() or None


def source_stamp(root=None, now=None):
    u"""**源之印**（一处定形 · pm_1573 §二）：册须自证其出处 ⇒ `commit` ／ `tree` ／ `刻`。

    由（PM 1573 §二.1 · 我一手）：旧册唯四键（`version` ／ `依之表` ／ `件之表` ／ `口径`）
      ⇒ 「此包出于何源」**唯靠回件可回指** ⇒ 包 **⛔ 自证**（承「入库 ＝ 快照 ⛔ 品质之证」）。
    ⚠ 主库（`master`）之对件 **⛔ 入册**：本器于**副本**跑 ∧ ⛔ 知主库之径
      （硬编码本机径 ＝ 新病 · 承「⛔ 硬编码本机径」）⇒ **明书**之（回件报其 `sha` · 承 PM 1573 §二.2「∨ 明书」）。
    """
    root = root or ROOT
    commit = _git_out(["rev-parse", "HEAD"], root)
    tree = _git_out(["rev-parse", "HEAD^{tree}"], root)
    branch = _git_out(["rev-parse", "--abbrev-ref", "HEAD"], root)
    stamp = now or datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
    return {"commit": commit, "tree": tree, "分支": branch, "刻": stamp,
            "明书": u"唯副本之源：主库（master）之对件 sha 由回件明书（器 ⛔ 知主库之径）"}

def plan_bundle(root=None, out=None):
    root = root or ROOT
    out = out or os.path.join(root, "dist", "client_v1")
    dists = required_dists(root)
    files = _payload_files(root)
    excluded = excluded_payload(root)
    live = scan_live_paths(root, files)
    return {"version": VERSION, "root": root, "out": out, "dists": dists,
            "源": source_stamp(root),
            "payload_files": files, "payload_bytes": sum(
                os.path.getsize(os.path.join(root, f.replace("/", os.sep))) for f in files),
            "wheel_dir": os.path.join(out, "wheel"),
            "live_paths": live, "live_org": [r for r in live if r["组织物"]],
            "live_off": [r for r in live if r["组织物"] or r["开发机"]],
            "excluded": excluded,
            "excluded_prefix": excluded_prefix_payload(root),
            "dangling": dangling_refs(root, files),
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
    r["源"] = j.get("源")
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


def manifest_for(entries, dists, src):
    u"""册之形（**一处出** · pm_1573 §二）—— 唯此一处拼册（⛔ 各点各拼 ⇒ 免「二源必漂」）。"""
    return {"version": VERSION, "源": dict(src), "依之表": list(dists),
            "件之表": list(entries),
            "口径": u"离线包：wheel\\ 之依全 ∧ 运行子集之 sha256；⛔ 含模型（须另下）"}

def prune_stale(out, want, skip_top=("wheel", "runtime")):
    u"""陈件之清（pm_1578 补 · 我一手逮）：本器唯「覆写」⇒ 旧包之件（今树 ⛔ 有）会**留**在 out
    ⇒ 下一出包之 zip 一并收之 ⇒ **重出而仍旧**之口（例：`ci_windows.yml.备件` 随老板之 git mv 而消 ⇒ 旧包之件留
    ⇒ 新包仍旧印之）。⛔ 触 `wheel\\`（pip 所管）∨ `runtime\\`（上已整树重落）。"""
    want = set(want)
    stale = []
    for dp, dns, fns in os.walk(out):
        rel = os.path.relpath(dp, out).replace(os.sep, u"/")
        if rel == u".":
            rel = u""
        if rel.split(u"/")[0] in skip_top:
            dns[:] = []
            continue
        for fn in fns:
            r = (rel + u"/" + fn) if rel else fn
            if r not in want:
                stale.append(r)
    for r in sorted(stale):
        os.remove(os.path.join(out, r.replace(u"/", os.sep)))
    for dp, _dns, _fns in os.walk(out, topdown=False):
        rel = os.path.relpath(dp, out).replace(os.sep, u"/")
        if rel == u"." or rel.split(u"/")[0] in skip_top:
            continue
        if not os.listdir(dp):
            os.rmdir(dp)
    return sorted(stale)


# ------------------------------------------ 出包之硬闸（pm_1598 §二 令二）
def release_gate(payload, root=None, live=True):
    u"""⭐ 出包之**硬闸**：以「包内 runtime ＋ 载荷」真跑二器 ⇒ `(ok, rows)`。

    ⛔ 过 ⇒ ⛔ 出包（免再出「净机启动不了」之包 —— 承「⛔ 以 rc 0 代『成』」）。
    ① `import_closure.py --check`：**入口之导入闭包 ⊆ 载荷**（⛔ 白名单自证）
    ② `build_runtime.py --check [--live]`：包内之根（`import core` rc 0）＋ 起服正控（`/health` 200）
    ⚠ 闸之端口 ＝ `socket.bind(0)` 取空 ＋ 临时 `APPDATA` 覆盖端口 ⇒ **⛔ 撞现役 `5102`**。
    """
    root = root or ROOT
    payload = os.path.abspath(payload)
    rows = [u"[闸] 载荷＝%s ｜ 仓＝%s" % (payload, root)]
    ok = True
    py = sys.executable
    r1 = subprocess.run([py, u"-X", u"utf8", u"-B", os.path.join(HERE, u"import_closure.py"),
                         u"--repo", root, u"--check", payload],
                        capture_output=True, text=True, encoding=u"utf-8", errors=u"replace")
    rows += [x for x in (r1.stdout or u"").split(u"\n") if x.strip()]
    ok1 = (r1.returncode == 0)
    ok = ok and ok1
    rows.append(u"[闸·一] 导入闭包 ⊆ 载荷：%s（rc %s）" % (u"过" if ok1 else u"⛔ 驳", r1.returncode))
    cmd = [py, u"-X", u"utf8", u"-B", os.path.join(HERE, u"build_runtime.py"),
           u"--root", root, u"--out", os.path.join(payload, u"runtime"),
           u"--payload", payload, u"--check"]
    if live:
        cmd.append(u"--live")
    r2 = subprocess.run(cmd, capture_output=True, text=True, encoding=u"utf-8", errors=u"replace")
    rows += [x for x in (r2.stdout or u"").split(u"\n") if x.strip()]
    ok2 = (r2.returncode == 0)
    ok = ok and ok2
    rows.append(u"[闸·二] 包内 runtime ＋ 载荷（起服正控%s）：%s（rc %s）"
                % (u"" if live else u" · ⛔ 跑", u"过" if ok2 else u"⛔ 驳", r2.returncode))
    rows.append(u"[闸] 判：%s ⇒ %s" % (u"过" if ok else u"⛔ 驳",
                                    u"可出包" if ok else u"**⛔ 出包**（承 pm_1598 §二 令二）"))
    return ok, rows


def apply_bundle(root=None, out=None, wheel=True, json_out=False, runtime=None):
    u"""真做（⚠ 须**网**）—— ⓐ `pip download` 入 `wheel\\` ⓑ 复运行子集 ⓒ 写册（逐件 sha256）。
    ⛔ 起停 ／ ⛔ 改本仓（唯写 `out`）。"""
    p = plan_bundle(root, out)
    lines = [u"[bundle] out=%s ｜ 件 %d（%.1f MB）｜ 依 %d" % (
        p["out"], len(p["payload_files"]), p["payload_bytes"] / 1048576.0, len(p["dists"]))]
    # ⭐ pm_1606 §二.4 ⒜：**净树之闸** —— 出包之**第一步**（载荷自工作树取件 ⇒ 先净树）
    _t_ok, _t_rows = guard_tree(p["root"], p["payload_files"])
    lines += _t_rows
    if not _t_ok:
        lines.append(u"[bundle] ⛔ 净树之闸驳 ⇒ ⛔ 出包（pm_1606 §二.4）")
        return 2, lines
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

    if not (p["源"].get("commit") and p["源"].get("tree")):
        lines.append(u"[bundle] ⛔ 源之印 ⛔ 得判（git ⛔ 用 ∨ 非仓 ∨ HEAD 无）⇒ 止"
                     u"（包须自证其出处 · 承 pm_1573 §二）")
        return 2, lines
    rt_src = runtime
    if rt_src and not os.path.isdir(rt_src):
        lines.append(u"[bundle] \u26d4 \u89c1\u81ea\u5e26\u8fd0\u884c\u65f6\uff1a%s\uff08\u26d4 \u9759\u9ed8\uff09" % rt_src)
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
    rt_files = _runtime_walk(rt_src) if rt_src else []
    if rt_files:
        rt_dst = os.path.join(p["out"], u"runtime")
        if os.path.isdir(rt_dst):
            shutil.rmtree(rt_dst)
        n_rt = 0
        for rel in rt_files:
            src = os.path.join(rt_src, rel.replace("/", os.sep))
            dst = os.path.join(rt_dst, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with io.open(src, "rb") as a, io.open(dst, "wb") as b:
                b.write(a.read())
            n_rt += 1
        lines.append(u"[bundle] \u81ea\u5e26\u8fd0\u884c\u65f6\uff1a%s \u21d2 runtime\\ \uff08%d \u4ef6 \u00b7 \u5165\u518c\uff09" % (rt_src, n_rt))
    stale = prune_stale(p["out"], p["payload_files"])
    if stale:
        lines.append(u"[bundle] ⊘ 陈件（旧包留下 · 今树 ⛔ 有）：%d 件 ⇒ 已清（⛔ 清则下一出包必收之 —— 重出而仍旧之口 · pm_1578 补）" % len(stale))
        for x in stale[:20]:
            lines.append(u"  ⊘ %s" % x)
    entries = []
    for rel in p["payload_files"]:
        src = os.path.join(p["root"], rel.replace("/", os.sep))
        dst = os.path.join(p["out"], rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with io.open(src, "rb") as a, io.open(dst, "wb") as b:
            b.write(a.read())
        entries.append({"rel": rel, "sha256": _sha256(dst), "bytes": os.path.getsize(dst)})
    for rel in rt_files:
        fp = os.path.join(p["out"], u"runtime", rel.replace("/", os.sep))
        entries.append({"rel": u"runtime/" + rel, "sha256": _sha256(fp),
                        "bytes": os.path.getsize(fp)})
    # ⭐ pm_1628 §二.1 令一：卸载器 exe（**构建期**编 ⇒ **随包入 payload** ∧ **入册**
    #   —— 一处定形：编器 /命名 / 落处 皆在 `make_uninstaller`；本处唯“呼之 ∧ 记之”。
    #   ⚠ ⛔ 得（无 csc ⁄ 编败）⇒ 明书其行 ∧ 卸载项走 `卸载ClawsJoyPA.cmd` 兜底（仍可卸 · 包仍可交付）。
    try:
        if HERE not in sys.path:
            sys.path.insert(0, HERE)
        import make_uninstaller as _mu
        _exe_ok, _exe_rows = _mu.ensure_exe(p["out"])
        lines += _exe_rows
        if _exe_ok:
            _fp = os.path.join(p["out"], _mu.EXE_NAME)
            entries.append({"rel": _mu.EXE_NAME, "sha256": _sha256(_fp),
                            "bytes": os.path.getsize(_fp)})
        else:
            lines.append(u"[bundle] ⚠ 卸载器 exe ⛔ 编 ⇒ 卸载项走 卸载ClawsJoyPA.cmd 兜底（仍可卸 · 包仍可交付）")
    except Exception as _e_exe:                              # noqa: BLE001 — 照实报因
        lines.append(u"[bundle] ⚠ 卸载器 exe 之钩败：%s: %s" % (type(_e_exe).__name__, _e_exe))
    man = manifest_for(entries, p["dists"], p["源"])
    io.open(os.path.join(p["out"], "bundle_manifest.json"), "w", encoding="utf-8", newline="").write(
        json.dumps(man, ensure_ascii=False, indent=1))
    lines.append(u"[bundle] 立毕：件 %d ｜ 依 %d ｜ 册 bundle_manifest.json" % (len(entries), len(p["dists"])))
    # ⭐ pm_1598 §二 令二：出包之**硬闸** —— 以「包内 runtime ＋ 载荷」真跑（⛔ 过 ⇒ ⛔ 出包）
    _g_ok, _g_rows = release_gate(p["out"], root=p["root"], live=True)
    lines += _g_rows
    if not _g_ok:
        lines.append(u"[bundle] ⛔ 闸驳 ⇒ 本包 ⛔ 可交付（pm_1598 §二 令二）")
        return 2, lines
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
        'U = "C:' + "/Users/" + 'alice/x.pdf"' + chr(10))
    _lo = live_offenders(os.path.join(t, "pl"), ["core/pa/d.py"])
    say(len(_lo) == 1 and _lo[0]["开发机"] and not _lo[0]["组织物"],
        u"正控：开发机活径（用户目录之式）必逮 ／ 且判「开发机」（⛔ 混组织物）")
    io.open(os.path.join(pd, "e.py"), "w", encoding="utf-8").write(
        'V = "D:' + BS + 'other' + BS + 'x"' + chr(10))
    say(len(live_offenders(os.path.join(t, "pl"), ["core/pa/e.py"])) == 0,
        u"反控：寻常盘符径（⛔ 组织物 ∧ ⛔ 开发机）⇒ ⛔ 判红")
    io.open(os.path.join(pd, "f.py"), "w", encoding="utf-8").write(
        'W = "D:' + BS + 'clawsjoy_v9' + BS + 'core' + BS + 'x.py"' + chr(10))
    _lv = live_org_paths(os.path.join(t, "pl"), ["core/pa/f.py"])
    say(len(_lv) == 1 and _lv[0]["组织物"],
        u"正控：开发机之**仓根**（clawsjoy_v9）必速 ／ 判「组织物」（pm_1468 §二.2 之盲区）")
    io.open(os.path.join(pd, "g.py"), "w", encoding="utf-8").write(
        'X = "D:' + BS + 'clawsjoy_lab' + BS + 'y.py"' + chr(10))
    say(len(live_org_paths(os.path.join(t, "pl"), ["core/pa/g.py"])) == 0,
        u"反控：同前缀异尾（clawsjoy_lab）⇒ ⛔ 判红（⛔ 宽于其分）")
    # \u2b50 pm_1577 \u00a7\u4e09.3\uff1a\u6d3b\u5f84\u4e4b\u626b\u4e4b**\u57df** \u2014\u2014 \u24dc \u4e8c\u8fdb\u5236 \u26d4 \u5165\uff08\u5185\u5d4c\u4e4b\u5efa\u5f84 \uff1d \u566a\uff09
    #   \u24dd `runtime\\`\uff08\u81ea\u5e26\u8fd0\u884c\u65f6 \uff1d \u7b2c\u4e09\u65b9\u4e4b\u4ef6\uff09\u26d4 \u5165\u626b\uff08\u660e\u4e66 \u00b7 \u62a5 PM \u88c1\uff09
    io.open(os.path.join(pd, "h.dll"), "wb").write(b"\x00C:/Users/runneradmin/x" + bytes(4))
    say(len(live_offenders(os.path.join(t, "pl"), ["core/pa/h.dll"])) == 0,
        u"\u53cd\u63a7\uff1a\u4e8c\u8fdb\u5236\u4e4b\u4ef6\uff08\u542b NUL\uff09\u21d2 \u26d4 \u5165\u626b\uff08\u5185\u5d4c\u4e4b\u5efa\u5f84 \uff1d \u566a \u00b7 \u26d4 \u5047\u7ea2\uff09")
    io.open(os.path.join(pd, "i.py"), "w", encoding="utf-8").write('Y = "C:' + "/Users/" + 'x"' + chr(10))
    say(len(live_offenders(os.path.join(t, "pl"), ["core/pa/i.py"])) == 1,
        u"\u6b63\u63a7\uff1a\u6587\u672c\u4e4b\u4ef6\uff08.py\uff09\u540c\u5f0f \u21d2 \u5fc5\u901f\uff08\u26d4 \u56e0\u300c\u26d4 \u4e8c\u8fdb\u5236\u300d\u800c\u6f0f\uff09")
    rd = os.path.join(t, "pl", "runtime", "Lib")
    os.makedirs(rd, exist_ok=True)
    io.open(os.path.join(rd, "j.py"), "w", encoding="utf-8").write('Z = "C:' + "/Users/" + 'x"' + chr(10))
    say(len(live_offenders(os.path.join(t, "pl"), ["runtime/Lib/j.py"])) == 0,
        u"\u53cd\u63a7\uff1aruntime\\\uff08\u81ea\u5e26\u8fd0\u884c\u65f6 \u00b7 \u7b2c\u4e09\u65b9\u4e4b\u4ef6\uff09\u21d2 \u26d4 \u5165\u626b\uff08\u660e\u4e66 \u00b7 \u975e\u672c\u4ed3\u4e4b\u6e90\uff09")
    _rd = os.path.join(t, "pl", "runtime", "Lib", "site-packages", "opentelemetry", "proto", "collector", "logs")
    os.makedirs(_rd, exist_ok=True)
    io.open(os.path.join(_rd, "__init__.py"), "w", encoding="utf-8").write("x = 1" + chr(10))
    _rw = _runtime_walk(os.path.join(t, "pl", "runtime"))
    say(any(x.endswith("collector/logs/__init__.py") for x in _rw),
        u"\u53cd\u63a7\uff1a\u81ea\u5e26\u8fd0\u884c\u65f6\u4e4b\u5254\u26d4 \u5403\u6389 `logs` \u540d\u4e4b\u771f\u4ee3\u7801\uff08site-packages \u4e4b\u5e38\u89c1\u540d\uff09")
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
    # ⭐ pm_1656 §三.1 ／ §三.2：前缀剔 ＋ 悬链之齿
    os.makedirs(os.path.join(ex, "web", "images"))
    io.open(os.path.join(ex, "web", "images", "a.jpg"), "w", encoding="utf-8").write("x")
    io.open(os.path.join(ex, "web", "pa.html"), "w", encoding="utf-8").write(
        "<a href=" + chr(34) + "/images/a.jpg" + chr(34) + ">q</a>" + chr(10))
    io.open(os.path.join(ex, "web", "ok.html"), "w", encoding="utf-8").write("<p>hi</p>" + chr(10))
    _pf2 = _payload_files(ex)
    say("web/images/a.jpg" not in _pf2, u"正控（pm_1656 §三.1）：`web/images/` ⇒ ⛔ 入包（静态大件）")
    say(excluded_prefix_payload(ex) == ["web/images/a.jpg"], u"正控：前缀剔 ⇒ 逐条可见（⛔ 静默）")
    _dr = dangling_refs(ex, _pf2)
    say(any(x["file"] == "web/pa.html" for x in _dr),
        u"正控：引已剔之前缀 ⇒ 悬链之齿响（%d 处）" % len(_dr))
    say(not any(x["file"] == "web/ok.html" for x in _dr), u"反控：⛔ 引者 ⛔ 假红")
    io.open(os.path.join(ex, "web", "ref.py"), "w", encoding="utf-8").write(
        "# 其链：`web/images/` 出包" + chr(10))
    io.open(os.path.join(ex, "web", "hub.html"), "w", encoding="utf-8").write(
        "<a href=" + chr(34) + "/web/ui_state.json" + chr(34) + ">h</a>" + chr(10))
    _dr2 = dangling_refs(ex, _payload_files(ex))
    say(not any(x["file"] == "web/hub.html" for x in _dr2),
        u"反控：面引「整件之剔」（其缺可容）⇒ ⏔ 报（⏔ 假红）")
    say(not any(x["file"] == "web/ref.py" for x in _dr2),
        u"反控（面之界）：`.py` 之提及其名 ⇒ ⛔ 报（假红之源）")

    say(not ref_scan("Path(__file__).parent / " + chr(34) + "mobile" + chr(34) + " / " + chr(34) + "index.html" + chr(34)),
        u"反控：`mobile`（今 ⛔ 剔）⇒ ⛔ 报（免假红）")
    say(ref_scan("r = " + chr(34) + "/mobile/" + chr(34), ("mobile",)), u"正控：若 `mobile` 入剔表 ⇒ 其路由引者 ⛔ 逃过")
    # ⭐ pm_1573 §二：册须载「源」（`commit` ／ `tree` ／ `刻`）⇒ 齿（正控 ／ 反控）
    _st = source_stamp(ROOT)
    say(len(_st.get("commit") or "") == 40 and len(_st.get("tree") or "") == 40,
        u"正控：源之印须得（`commit` ／ `tree` 各 40 hex —— 册须自证其出处 · pm_1573 §二）")
    say(bool(re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{4}$", _st.get("刻") or "")),
        u"正控：刻之形（含时区 ⇒ 可回指）")
    _man = manifest_for([{"rel": "a.py", "sha256": "0" * 64, "bytes": 1}], ["flask"], _st)
    say(_man["源"]["commit"] == _st["commit"] and _man["件之表"] and _man["依之表"],
        u"正控：册之形（唯 `manifest_for` 一处出 · 含源）")
    say(source_stamp(os.path.join(t, "norepo"))["commit"] is None,
        u"反控：⛔ 非仓 ⇒ `commit` `None`（fail-loud 之据 · ⛔ 假印）")
    n, tt = sum(1 for c in hits if c), len(hits)
    print(u"=== 离线包器自测 %d/%d 通过（%s）===" % (n, tt, u"rc=0" if n == tt else u"rc=2"))
    return 0 if n == tt else 2


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--out", default="")
    ap.add_argument("--go", action="store_true")
    ap.add_argument("--check", default="")
    ap.add_argument("--runtime", default="", help=u"自带运行时之径（入包 ＋ 入册）")
    ap.add_argument("--no-wheel", action="store_true", help=u"⛔ 跑 pip download（轮已在）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--gate", default="", help=u"出包之硬闸：以「包内 runtime ＋ 载荷」真跑二器")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    if a.gate:
        if not os.path.isdir(a.gate):
            print(u"[bundle] ⛔ 入口错：--gate 之径不在：%s" % a.gate)
            return 3
        ok, rows = release_gate(a.gate, root=a.root, live=True)
        print(u"\n".join(rows))
        return 0 if ok else 2
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
            _exp = p["excluded_prefix"]
            print(u"  剔·前缀（pm_1656 §三.1）：%d 件 ｜ %s" % (
                len(_exp), (u"%s …" % _exp[0]) if _exp else u"（无）"))
            _dr = p["dangling"]
            print(u"  悬链之齿（pm_1656 §三.2）：%d 处（判「成」＝ 0）" % len(_dr))
            for x in _dr[:12]:
                print(u"    ⛔ %s:%d  %s" % (x["file"], x["line"], x["文"]))
            _s = p["源"]
            print(u"  源（pm_1573 §二）：commit %s ／ tree %s ／ 分支 %s ／ 刻 %s"
                  % (_s.get("commit"), _s.get("tree"), _s.get("分支"), _s.get("刻")))
            print(u"  将动：① pip download -d %s -r requirements-runtime.txt ② 复运行子集 ③ 写册"
                  u" ④ 自带运行时（--runtime）入包 ＋ 入册" % p["wheel_dir"])
        return 0
    if p["dangling"]:
        print(u"[FAIL] 悬链之齿（pm_1656 §三.2）：%d 处引**已剔之前缀** ⇒ 开则空 ⇒ **⛔ 出包**"
              % len(p["dangling"]))
        for x in p["dangling"][:12]:
            print(u"    ⛔ %s:%d  %s" % (x["file"], x["line"], x["文"]))
        print(u"    ⇒ 去处：随包一并处置（剔 ／ 换明书 ／ 改远端）"
              u" —— 承「凡面之支 ⇒ 须能真达」")
        return 2
    rc, lines = apply_bundle(a.root, p["out"], wheel=not a.no_wheel, json_out=a.json,
                             runtime=a.runtime or None)
    for x in lines:
        print(x)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
