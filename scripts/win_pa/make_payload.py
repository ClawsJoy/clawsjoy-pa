# -*- coding: utf-8 -*-
u"""make_payload.py -- 造「Electron 壳之载荷」（pm_1672 §五.1 之 ①「载荷入包」· 技术总监席 f202f89）。

其的（一句话）：把「今日之树」装成**壳之载荷**（＝ 净机装根之形）⇒ 置 `extraResources/payload`
  ⇒ 壳之主进程以 `process.resourcesPath/payload` 为 `ROOT`（**一处定形**）⇒ 壳内之服务自壳内之载荷起。

载荷之形（＝ 装根之形 · 与 `make_client_bundle` 之「目录即交付物」同形）：
    agent_gateway_enhanced.py ／ config\\ ／ core\\ ／ routes\\ ／ web\\ ／ scripts\\win_pa\\
  ＋ runtime\\（自带 CPython 3.12.10 embed ＋ 构建期装齐之 site-packages ⇒ 净机 ⛔ 预装 Python）
  ＋ wheel\\（第三方之轮 ⇒ 供修复 ／ 重装）

⭐ 三真源（**⛔ 手写清单 · ⛔ 猜**）：
  ⒜ 件表 ＝ `make_client_bundle.effective_payload()`（资产白名单 ∪ 入口之导入闭包）剔其
     `EXCLUDE` ／ `EXCLUDE_PREFIX`（**同一处定形** ⇒ 与出包一致 · ⛔ 二处各写）；
  ⒝ 树 ＝ `git archive <ref>` 之**纯树**（pm_1672 §四.1 之裁 · ⛔ 取工作区 ⇒ 免「彼侧工作区有未入册之新写」之险）；
  ⒞ 版 ＝ 载荷内 `core/lib/version.py:__version__`（**唯一真源** —— pm_1672 §四.2 之钉：
     壳首启所落之 `version.json` 取**此**数 · ⛔ 取壳之 `package.json` 之版 ⇒ 二者异层）。

⭐ 一辨（我一手 · 须报）：`git archive` 之「纯树」**⛔ 可起** ——
  其无 `runtime\\`（自带 CPython）⇒ 载荷须并 runtime\\ ／ wheel\\ 方为「净机可起」之载荷。

用法：
  python -X utf8 -B scripts\\win_pa\\make_payload.py --ref a121e90 --out <目录>            # 干跑（唯报计划）
  python -X utf8 -B scripts\\win_pa\\make_payload.py --ref a121e90 --out <目录> --go --gate  # 真造 ＋ 三闸
  python -X utf8 -B scripts\\win_pa\\make_payload.py --out <目录> --check                  # 唯核（⛔ 动）
  python -X utf8 -B scripts\\win_pa\\make_payload.py --self-test
退出码：0 成 ｜ 2 红（自测败 ∨ 缺件 ∨ 闸红）｜ 3 入口错
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time

if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BS = chr(92)
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DEFAULT_OUT = os.path.join(ROOT, "dist", "pa_shell", "payload")
#: 载荷之内**必无**（**一处定形** —— 密钥 ／ 用户数据 ／ 本机态 ／ 运行产物 ／ 开发物）
FORBIDDEN_REL = (u"config/.env", u"config/secrets.yaml", u"scripts/win_pa/ClawsJoy_PA_Boot.xml")
FORBIDDEN_TOP = (u"data", u"logs", u"tests", u"dist", u"web/images", u"_share")
#: 运行时之源（自有运行时之候选 · 序取 · ⛔ 须含 runtime\\python.exe）
RUNTIME_SRC_CANDIDATES = (
    os.path.join(os.path.dirname(ROOT), u"clawsjoy_build", u"dist", u"client_v1"),
    os.path.join(ROOT, u"dist", u"client_v1"),
)
#: 观之件（报印用 · **一处定形**）
KEY_FILES = (u"core/lib/version.py", u"pyproject.toml", u"agent_gateway_enhanced.py",
             u"scripts/win_pa/make_update.py", u"web/pa/faces/update.js")

VER_RE = re.compile(u"(?m)^__version__\\s*=\\s*u?[\"']([^\"']+)[\"']")


def _add_paths(root=None):
    for p in (HERE, root or u""):
        if p and p not in sys.path:
            sys.path.insert(0, p)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def sha16f(p):
    u"""「印」之口径（**一处定形** · 与诸席一致）：sha256 之**前十六**（小写）。"""
    return sha256_file(p)[:16]


def git(root, *args):
    r = subprocess.run([u"git", u"-C", root] + list(args), capture_output=True)
    return r.returncode, (r.stdout or b"").decode(u"utf-8", u"replace") + \
        (r.stderr or b"").decode(u"utf-8", u"replace")


def read_version(payload):
    u"""载荷之版之**唯源** ＝ `core/lib/version.py:__version__` ⇒ `(ver, why)`。"""
    p = os.path.join(payload, u"core", u"lib", u"version.py")
    if not os.path.isfile(p):
        return None, u"未见 core/lib/version.py"
    m = VER_RE.search(io.open(p, encoding=u"utf-8").read())
    if not m:
        return None, u"core/lib/version.py 之 `__version__` ⛔ 解"
    return m.group(1), u""


def pyproject_version(payload):
    u"""`pyproject.toml[project].version`（**唯作核** —— ⛔ 作壳之版之真源）⇒ `(ver, why)`。"""
    p = os.path.join(payload, u"pyproject.toml")
    if not os.path.isfile(p):
        return None, u"未见 pyproject.toml"
    try:
        import tomllib as _tl
    except ImportError:                                        # pragma: no cover
        _tl = None
    if _tl is not None:
        try:
            with open(p, u"rb") as fh:
                v = str(((_tl.load(fh).get(u"project") or {}).get(u"version") or u"")).strip()
            return (v or None), (u"" if v else u"pyproject.toml ⛔ 见 [project].version")
        except Exception as e:                                  # noqa: BLE001 -- 照实报因
            return None, u"pyproject.toml 读败：%s: %s" % (type(e).__name__, e)
    m = re.search(r"(?m)^version\s*=\s*[\"']([^\"']+)[\"']",
                  io.open(p, encoding=u"utf-8", errors=u"replace").read())
    return (m.group(1) if m else None), (u"" if m else u"pyproject.toml ⛔ 见 version（兜底逐行）")


def single_source(payload, log):
    u"""**一源之闸**（pm_1672 §四.2 之钉）：载荷之 `version.py` ≡ `pyproject.toml` ⇒ 方许。
    ⇒ 壳首启所落之 `version.json`（＝ `installer_post.write_version_json` 取 pyproject）**即**载荷版。"""
    v1, w1 = read_version(payload)
    v2, w2 = pyproject_version(payload)
    ok = (v1 is not None and v2 is not None and v1 == v2)
    log(u"[闸·零] 一源（version.py ≡ pyproject.toml）：%s ｜ version.py %s ／ pyproject %s%s"
        % (u"OK" if ok else u"**FAIL**", v1, v2,
           u"" if ok else u"  ⚠ %s%s" % (w1 or u"", (u" ／ " + w2) if w2 else u"")))
    return ok


def payload_pred(root):
    u"""「入包否」之尺（**器取** ⇒ 引 `make_client_bundle` 之四表 · ⛔ 手拟 · ⛔ 二处各写）。"""
    import make_client_bundle as M
    tops = tuple(M.effective_payload(root))
    excl = set(M.EXCLUDE)
    pre = tuple(M.EXCLUDE_PREFIX)
    skip = set(M.SKIP_NAMES)

    def inside(rel):
        if not rel or rel in excl or rel.startswith(pre):
            return False
        if not any(rel == t or rel.startswith(t + u"/") for t in tops):
            return False
        segs = rel.split(u"/")
        for s in segs[:-1]:
            if s in skip or s.startswith(u"."):
                return False
        fn = segs[-1]
        return not (fn.endswith(u".pyc") or u".before_" in fn or fn.startswith(u"."))
    return inside


def _drop_member(rel, skip_names, drop_prefix):
    u"""提取期之**早剔**（省时 —— ⛔ 判据 · 判据在 `payload_pred`）：必不入包之件。"""
    if not rel or rel.startswith(u"/") or u".." in rel.split(u"/"):
        return True
    if rel.startswith(tuple(drop_prefix)):
        return True
    segs = rel.split(u"/")
    for s in segs:
        if s.startswith(u".") or s in skip_names:
            return True
    fn = segs[-1]
    return bool(fn.endswith(u".pyc") or u".before_" in fn)


def extract_pure(root, ref, stage, log=None):
    u"""`git archive <ref>` ⇒ stage（**纯树** ⇒ ⛔ 取工作区）⇒ 早剔。"""
    parent = os.path.dirname(stage)
    os.makedirs(parent, exist_ok=True)
    tp = os.path.join(parent, u"_pure.tar")
    if os.path.isfile(tp):
        os.remove(tp)
    rc, out = git(root, u"archive", u"-o", tp, ref, u"--")
    if rc != 0 or not os.path.isfile(tp):
        return None, u"`git archive %s` 败（rc %s）：%s" % (ref, rc, out.strip()[:300])
    if os.path.isdir(stage):
        rmtree_checked(stage)
    os.makedirs(stage, exist_ok=True)
    import make_client_bundle as M
    n, nd = 0, 0
    with tarfile.open(tp, u"r:") as tf:
        for mem in tf:
            name = mem.name.replace(BS, u"/")
            if mem.isdir():
                continue
            if not mem.isfile():
                continue
            if _drop_member(name, set(M.SKIP_NAMES), tuple(M.EXCLUDE_PREFIX)):
                nd += 1
                continue
            dst = os.path.join(stage, name.replace(u"/", os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            src = tf.extractfile(mem)
            if src is None:
                continue
            with open(dst, u"wb") as f:
                shutil.copyfileobj(src, f)
            n += 1
    try:
        os.remove(tp)
    except OSError:
        pass
    if log is not None:
        log(u"[载荷] 1 纯树：`git archive %s` ⇒ %d 件（早剔 %d 件 · ⛔ 取工作区）" % (ref, n, nd))
    return n, u""


def collect(stage):
    u"""stage 之**入包之件**（器取 · 序定）⇒ 相对之径（posix）。"""
    inside = payload_pred(stage)
    out = []
    for dp, dns, fns in os.walk(stage):
        dns[:] = [d for d in dns if not d.startswith(u".")]
        for fn in fns:
            rel = os.path.relpath(os.path.join(dp, fn), stage).replace(os.sep, u"/")
            if inside(rel):
                out.append(rel)
    return sorted(out)


def dir_stats(d):
    n, b = 0, 0
    for dp, dns, fns in os.walk(d):
        for fn in fns:
            n += 1
            try:
                b += os.path.getsize(os.path.join(dp, fn))
            except OSError:
                pass
    return n, b


def mb(b):
    return u"%.3f MB" % (b / 1048576.0)


def rmtree_checked(p):
    u"""递归删之前之**径核**（· 硬规：⛔ 盘根 ／ 仓根 ／ HOME ／ 用户夹）。"""
    a = os.path.abspath(p)
    bad = [os.path.abspath(os.sep), os.path.splitdrive(a)[0] + BS, os.path.abspath(ROOT),
           os.path.abspath(os.path.expanduser(u"~"))]
    if a in bad or len(a.rstrip(BS)) <= 3:
        raise AssertionError(u"⛔ 删此径（过危险）：%s" % a)
    shutil.rmtree(a, ignore_errors=True)


def find_runtime_src(explicit, cands=None):
    u"""运行时之源之**序取**（显式 ⇒ 先；⛔ 得 ⇒ 候之候选；皆⛔ 得 ⇒ None）。"""
    seq = ([explicit] if explicit else []) + list(
        RUNTIME_SRC_CANDIDATES if cands is None else cands)
    for c in seq:
        if c and os.path.isfile(os.path.join(c, u"runtime", u"python.exe")):
            return c
    return None


def top_breakdown(d):
    rows = []
    for name in sorted(os.listdir(d)):
        p = os.path.join(d, name)
        if os.path.isdir(p):
            n, b = dir_stats(p)
        else:
            n, b = 1, os.path.getsize(p)
        rows.append((name + (u"/" if os.path.isdir(p) else u""), n, b))
    return rows


def write_root_version_json(root, payload, ref, log):
    u"""落装根 `version.json`（**一处出** —— 其形唯 `installer_post.version_payload` 出 · ⛔ 本器另拼），
    连同其真源 `bundle_manifest.json` 之「源」（commit ／ tree ／ 刻 ＝ **纯树之实**）。

    ⭐ 由（我一手 · 报 PM）：`version.json` **建时落** ⇒ 装即可见（`/health.build.available` 真）、
      且壳层之更新随「壳内载荷」一体替换 ⇒ **双层之交界自洽**；
      ⛔ 需运行时改装根（免 `installer_post --go` 之 HKCU 注册 ／ 启动器 ／ `install_record.json` 之杂）。
    """
    import installer_post as IP
    rc, out = git(root, u"rev-parse", ref + u"^{commit}")
    commit = out.strip() if rc == 0 else u""
    rc2, out2 = git(root, u"rev-parse", ref + u"^{tree}")
    tree = out2.strip() if rc2 == 0 else u""
    man = {u"版本": 1, u"器": u"make_payload.py",
           u"源": {u"ref": ref, u"commit": commit, u"tree": tree,
                   u"刻": time.strftime(u"%Y-%m-%dT%H:%M:%S%z")}}
    with io.open(os.path.join(payload, u"bundle_manifest.json"), u"w",
                 encoding=u"utf-8", newline=u"") as fh:
        fh.write(json.dumps(man, ensure_ascii=False, indent=1) + u"\n")
    pay = IP.version_payload(payload)
    with io.open(os.path.join(payload, u"version.json"), u"w",
                 encoding=u"utf-8", newline=u"") as fh:
        fh.write(json.dumps(pay, ensure_ascii=False, indent=1))
    log(u"[载荷] 5b 装根 version.json：version %s ／ channel %s ／ commit %s ／ tree %s"
        % (pay[u"version"], pay[u"channel"], (pay[u"commit"] or u"—")[:12], (pay[u"tree"] or u"—")[:12]))
    return pay


def snapshot(d):
    u"""件之集（相对之径 · posix）—— 供「器之副作用」之核。"""
    out = set()
    for dp, dns, fns in os.walk(d):
        for fn in fns:
            out.add(os.path.relpath(os.path.join(dp, fn), d).replace(os.sep, u"/"))
    return out


def prune_extras(d, before, log):
    u"""清**器之副作用**（承「器之副作用 ⛔ 入产品之面」）：闸（`import core`）会落
    `data/vector_kb/chroma.sqlite3` 之类 ⇒ 逐件抹 ⇒ 载荷 ＝ 纯树 ∪ runtime ∪ wheel ∪ 二册。

    ⚠ 唯抹「`before` 之后新出之件」（⛔ 我拣 · 器取）∧ 唯抹其所空之父夹。
    """
    extra = sorted(snapshot(d) - before)
    dirs = []
    for rel in extra:
        p = os.path.join(d, rel.replace(u"/", os.sep))
        try:
            os.remove(p)
        except OSError:
            pass
        q = os.path.dirname(p)
        while os.path.abspath(q) != os.path.abspath(d):
            dirs.append(q)
            q = os.path.dirname(q)
    for q in sorted(set(dirs), key=len, reverse=True):
        try:
            os.rmdir(q)
        except OSError:
            pass
    if extra:
        log(u"[载荷] 7b 清器之副作用（闸所落 · ⛔ 入产品之面）：%d 件 —— %s"
            % (len(extra), u" ／ ".join(extra[:6])))
    return extra


def gate_payload(payload, repo_for_closure, log, rows):
    u"""三闸：⒜ 闭包 ⊆ 载荷 ⒝ 根可入（`import core`）⒞ 离线轮齐（requirements-runtime）。"""
    ok = True
    exe = os.path.join(payload, u"runtime", u"python.exe")
    _r = subprocess.run([sys.executable, u"-X", u"utf8", u"-B",
                         os.path.join(HERE, u"import_closure.py"),
                         u"--repo", repo_for_closure, u"--check", payload],
                        capture_output=True)
    rc = _r.returncode
    o = ((_r.stdout or b"") + (_r.stderr or b"")).decode(u"utf-8", u"replace")
    first = (o.splitlines() or [u""])[0]
    rows.append(u"[闸·一] 闭包 ⊆ 载荷（repo＝%s）：rc %s ｜ %s" % (
        u"纯树" if repo_for_closure != payload else u"载荷自身", rc, first))
    ok = ok and rc == 0
    if os.path.isfile(exe):
        r = subprocess.run([exe, u"-X", u"utf8", u"-B", u"-c",
                            u"import core; print(u'ROOT-IMPORT-OK')"],
                           cwd=payload, capture_output=True, timeout=900)
        o2 = ((r.stdout or b"") + (r.stderr or b"")).decode(u"utf-8", u"replace")
        rows.append(u"[闸·二] 载荷之根可入（`runtime\\python.exe -c \"import core\"`）：rc %s ｜ %s" % (
            r.returncode, (o2.strip().splitlines() or [u""])[-1][:160]))
        ok = ok and r.returncode == 0
    else:
        rows.append(u"[闸·二] ⛔ 无 runtime\\python.exe ⇒ 载荷 ⛔ 可起（**此即「纯树 ⛔ 可起」之证**）")
        ok = False
    wd = os.path.join(payload, u"wheel")
    if os.path.isdir(wd):
        import make_client_bundle as M
        miss = M.missing_wheels(wd, M.required_dists(payload))
        rows.append(u"[闸·三] 离线轮齐（requirements-runtime 之必需）：%s ｜ 缺 %d %s" % (
            u"OK" if not miss else u"FAIL", len(miss), u" ".join(miss[:12])))
        ok = ok and not miss
    else:
        rows.append(u"[闸·三] ⛔ 无 wheel\\ ⇒ 修复 ／ 重装之路 ⛔ 立（报 · 非致命）")
    return ok


def plan(ref, out, root, runtime_src, wheel, runtime):
    u"""干跑：唯报计划（⛔ 动盘外之物）。"""
    rows = []
    rc, head = git(root, u"rev-parse", ref + u"^{commit}")
    rows.append(u"[载荷] 0 树：%s ⇒ %s" % (ref, head.strip()[:40] if rc == 0 else u"⛔ 解"))
    rows.append(u"[载荷] 0 落：%s" % out)
    rows.append(u"[载荷] 0 运行时之源：%s（%s）" % (runtime_src or u"（未得 ⇒ ⛔ 可起）",
                                                   u"含 runtime\\python.exe" if runtime_src else u"—"))
    rows.append(u"[载荷] 0 wheel\\：%s" % (u"入" if wheel else u"⛔ 入"))
    return rows


def apply(root, ref, out, runtime_src, wheel=True, runtime=True, gate=False, log=None):
    rows = []
    log = log or (lambda s: None)
    parent = os.path.dirname(os.path.abspath(out))
    os.makedirs(parent, exist_ok=True)
    stage = os.path.join(parent, u"_stage_%s" % u"pure")
    n, why = extract_pure(root, ref, stage, log=log)
    if why:
        return None, why, rows
    files = collect(stage)
    n2, b2 = 0, 0
    for rel in files:
        src = os.path.join(stage, rel.replace(u"/", os.sep))
        dst = os.path.join(out, rel.replace(u"/", os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        n2 += 1
        b2 += os.path.getsize(dst)
    log(u"[载荷] 2 件表：入包 %d 件 ／ %s（尺 ＝ effective_payload 剔 EXCLUDE ／ EXCLUDE_PREFIX）"
        % (n2, mb(b2)))
    rt_n = rt_b = 0
    if runtime and runtime_src:
        rt_dst = os.path.join(out, u"runtime")
        rt_n, rt_b = copy_tree(os.path.join(runtime_src, u"runtime"), rt_dst)
        log(u"[载荷] 3 运行时：%s\\runtime ⇒ runtime\\（%d 件 ／ %s）"
            % (runtime_src, rt_n, mb(rt_b)))
    elif runtime:
        log(u"[载荷] 3 运行时：⚠ ⛔ 得（⛔ 预装 Python 之净机 ⇒ 载荷 ⛔ 可起）")
    wh_n = wh_b = 0
    if wheel and runtime_src:
        wh_n, wh_b = copy_tree(os.path.join(runtime_src, u"wheel"), os.path.join(out, u"wheel"))
        log(u"[载荷] 4 第三方之轮：%s\\wheel ⇒ wheel\\（%d 件 ／ %s）"
            % (runtime_src, wh_n, mb(wh_b)))
    ver, why2 = read_version(out)
    if ver is None:
        return None, why2, rows
    okv = single_source(out, log)
    pay = write_root_version_json(root, out, ref, log)
    vj = os.path.join(out, u"version.json")
    okj = (pay.get(u"version") == read_version(out)[0])
    log(u"[闸·零b] 装根 version.json ≡ 载荷之版：%s（%s ⟷ %s）"
        % (u"OK" if okj else u"**FAIL**", pay.get(u"version"), read_version(out)[0]))
    okv = okv and okj
    log(u"[载荷] 5 版（**唯源** ＝ 载荷内 core/lib/version.py）：%s ／ 印 %s"
        % (ver, sha16f(os.path.join(out, u"core", u"lib", u"version.py"))))
    tot_n, tot_b = dir_stats(out)
    log(u"[载荷] 6 合：%d 件 ／ %s" % (tot_n, mb(tot_b)))
    for name, nn, bb in top_breakdown(out):
        log(u"        %-14s %5d 件 ／ %s" % (name, nn, mb(bb)))
    info = {
        u"ref": ref, u"out": out, u"version": ver,
        u"files": tot_n, u"bytes": tot_b, u"payload_files": n2, u"payload_bytes": b2,
        u"runtime_files": rt_n, u"runtime_bytes": rt_b,
        u"wheel_files": wh_n, u"wheel_bytes": wh_b,
        u"runtime_src": runtime_src,
        u"version_json": (json.load(io.open(os.path.join(out, u"version.json"), encoding=u"utf-8"))
                          if os.path.isfile(os.path.join(out, u"version.json")) else None),
        u"version_json_sha16": (sha16f(os.path.join(out, u"version.json"))
                                if os.path.isfile(os.path.join(out, u"version.json")) else None),
        u"sha16": {k: (sha16f(os.path.join(out, k.replace(u"/", os.sep)))
                       if os.path.isfile(os.path.join(out, k.replace(u"/", os.sep))) else None)
                   for k in KEY_FILES},
    }
    okg = okv
    if gate:
        _before = snapshot(out)
        okg = gate_payload(out, stage, log, rows) and okg
        prune_extras(out, _before, log)
        log(u"[载荷] 7 闸：%s" % (u"三闸皆过" if okg else u"**有红**"))
    rmtree_checked(stage)
    return (info, okg), u"", rows


def copy_tree(src, dst):
    n, b = 0, 0
    for dp, dns, fns in os.walk(src):
        # ⭐ 逐件**照搬**（⛔ 我拣 —— 运行时 ＝ 第三方之物 ⇒ 与 `build_runtime` 之产物逐字同）
        for fn in fns:
            s = os.path.join(dp, fn)
            rel = os.path.relpath(s, src)
            d = os.path.join(dst, rel)
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)
            n += 1
            b += os.path.getsize(d)
    return n, b


def stray_files(payload):
    u"""载荷之内**混杂之件**（⛔ 纯树 ∪ runtime ∪ wheel 之份）：`__pycache__` ／ `.pyc`。

    ⚠ 我一手之训（载荷之头一跑）：`pa_nowindow.py` ⇒ `preflight_start.py` 之子进程 **⛔ 带 `-B`**
      ⇒ 首跑即把 `core/__pycache__/*.pyc` 写进**装根**（＝ 载荷之根）⇒ 载荷 ⛔ 再等于「纯树」。
      ⇒ 此为**产品侧之实**（其修须动载荷之件 ⇒ 升版号 · 候 PM 裁）；本器唯**捕**之。
    """
    out = []
    for dp, dns, fns in os.walk(payload):
        rel = os.path.relpath(dp, payload).replace(os.sep, u"/")
        if rel == u"runtime" or rel.startswith(u"runtime/"):
            continue                                            # 自带运行时之 `.pyc` ＝ 其份（建时编译）
        for fn in fns:
            if fn.endswith(u".pyc"):
                out.append((rel.strip(u".") + u"/" if rel != u"." else u"") + fn)
    return sorted(out)


def check(payload, log, allow_strays=False):
    u"""唯核既有之载荷（⛔ 动）⇒ (ok, info)。"""
    ok = True
    if not os.path.isdir(payload):
        log(u"[核] ⛔ 载荷不在：%s" % payload)
        return False, {}
    ver, why = read_version(payload)
    log(u"[核] 1 版（唯源）：%s" % (ver if ver is not None else u"**FAIL** " + why))
    ok = ok and ver is not None
    for rel in FORBIDDEN_REL:
        p = os.path.join(payload, rel.replace(u"/", os.sep))
        log(u"[核] 2 ⛔ 入载荷之物：%-40s %s" % (rel, u"**在 ⇒ FAIL**" if os.path.exists(p) else u"不在 ✓"))
        ok = ok and not os.path.exists(p)
    for t in FORBIDDEN_TOP:
        p = os.path.join(payload, t.replace(u"/", os.sep))
        log(u"[核] 3 ⛔ 入载荷之夹：%-40s %s" % (t, u"**在 ⇒ FAIL**" if os.path.exists(p) else u"不在 ✓"))
        ok = ok and not os.path.exists(p)
    exe = os.path.join(payload, u"runtime", u"python.exe")
    log(u"[核] 4 自带运行时：runtime\\python.exe %s" % (u"在 ✓" if os.path.isfile(exe) else u"**不在 ⇒ 载荷 ⛔ 可起**"))
    ok = ok and os.path.isfile(exe)
    ok = single_source(payload, log) and ok
    vjp = os.path.join(payload, u"version.json")
    if os.path.isfile(vjp):
        try:
            _j = json.load(io.open(vjp, encoding=u"utf-8"))
            _same = (_j.get(u"version") == ver)
            log(u"[核] 4b 装根 version.json：version %s ⟷ 载荷之版 %s ⇒ %s（印 %s）"
                % (_j.get(u"version"), ver, u"同 ✓" if _same else u"**异 ⇒ FAIL**", sha16f(vjp)))
            ok = ok and _same
        except Exception as _e:                                 # noqa: BLE001 -- 照实报因
            log(u"[核] 4b 装根 version.json 读 ⛔ 得：%s" % _e)
            ok = False
    else:
        log(u"[核] 4b ⛔ 见装根 version.json ⇒ `/health.build.available` 必 false（照实 · **FAIL**）")
        ok = False
    _st = stray_files(payload)
    if _st:
        log(u"[核] 4c 载荷之混杂（⛔ 纯树之份 · ‰ 首跑之器所落）：%d 件 ⇒ %s —— %s"
            % (len(_st), u"**FAIL**" if not allow_strays else u"（--allow-strays · 唯报）",
               u" ／ ".join(_st[:6])))
        ok = ok and allow_strays
    else:
        log(u"[核] 4c 载荷之混杂：无 ✓（＝ 纯树 ∪ runtime ∪ wheel ∪ 二册）")
    n, b = dir_stats(payload)
    log(u"[核] 5 合：%d 件 ／ %s" % (n, mb(b)))
    for name, nn, bb in top_breakdown(payload):
        log(u"        %-14s %5d 件 ／ %s" % (name, nn, mb(bb)))
    sh = {k: (sha16f(os.path.join(payload, k.replace(u"/", os.sep)))
              if os.path.isfile(os.path.join(payload, k.replace(u"/", os.sep))) else None)
          for k in KEY_FILES}
    for k in KEY_FILES:
        log(u"[核] 6 印 %-34s %s" % (k, sh[k]))
    return ok, {u"out": payload, u"version": ver, u"files": n, u"bytes": b, u"sha16": sh}


def self_test():
    u"""齿：唯纯函 ＋ 小 tar（⛔ 动真盘之载荷 · ⛔ 触 5102）。"""
    t = tempfile.mkdtemp(prefix=u"pa_pl_st_")
    fails = []
    n_hits = []

    def say(ok, s):
        u"""逐条报 ＋ 计（**⛔ 静默** —— 自测之数须可核）。"""
        n_hits.append(1)
        if not ok:
            fails.append(s)
        print(u"  %s %s" % (u"OK " if ok else u"FAIL", s))

    def w(rel, body=u"x"):
        p = os.path.join(t, rel.replace(u"/", os.sep))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        io.open(p, u"w", encoding=u"utf-8").write(body)
        return p

    # T1 版之解（正控）＋ 反控（u 前缀 · 即 a121e90 所修之字面）
    w(u"p1/core/lib/version.py", u'__version__ = u"9.0.1"\n')
    say(read_version(os.path.join(t, u"p1")) == (u"9.0.1", u""), u"T1 版之解：`u\"9.0.1\"` ⇒ 9.0.1")
    w(u"p2/core/lib/version.py", u'X = 1\n# __version__ = "9.9.9"\n')
    say(read_version(os.path.join(t, u"p2"))[0] is None, u"T1b 反控：注中之 `__version__` ⇒ ⛔ 充真源")
    w(u"p3/core/lib/version.py", u'__version__="9.0.2"\n')
    say(read_version(os.path.join(t, u"p3")) == (u"9.0.2", u""), u"T1c 正控：无 u 前缀亦解")

    # T2 早剔（⛔ 入载荷之件）
    say(_drop_member(u"web/images/a.jpg", set(), (u"web/images/",)), u"T2 早剔：web/images/** ⇒ 剔")
    say(_drop_member(u"core/__pycache__/x.pyc", {u"__pycache__"}, ()), u"T2b 早剔：__pycache__ ／ .pyc ⇒ 剔")
    say(_drop_member(u"scripts/win_pa/x.py.before_abc", set(), ()), u"T2c 早剔：`.before_*` ⇒ 剔")
    say(not _drop_member(u"core/lib/version.py", set(), (u"web/images/",)), u"T2d 反控：core/lib/version.py ⇒ ⛔ 剔")
    say(_drop_member(u"../evil.py", set(), ()), u"T2e 反控：`..` ⇒ 剔（⛔ 越径）")

    # T3 尺（payload_pred）之正反控 —— 以本仓为根（唯读）
    inside = payload_pred(ROOT)
    say(inside(u"core/lib/version.py"), u"T3 尺：core/lib/version.py ⇒ 入包")
    say(not inside(u"web/images/a.jpg"), u"T3b 尺：web/images/** ⇒ ⛔ 入包（EXCLUDE_PREFIX）")
    say(not inside(u"web/comic_gallery.html"), u"T3c 尺：旧演示页 ⇒ ⛔ 入包（EXCLUDE）")
    say(not inside(u"config/secrets.yaml"), u"T3d 尺：密钥 ⇒ ⛔ 入包")
    say(not inside(u"tests/unit/test_x.py"), u"T3e 尺：tests/** ⇒ ⛔ 入包")
    say(not inside(u"dist/update/x"), u"T3f 尺：dist/** ⇒ ⛔ 入包")

    # T4 核（--check）之正反控
    pl = os.path.join(t, u"pl")
    w(u"pl/core/lib/version.py", u'__version__ = u"9.0.1"\n')
    w(u"pl/pyproject.toml", u'[project]\nname = "clawsjoy"\nversion = "9.0.1"\n')
    os.makedirs(os.path.join(pl, u"runtime"), exist_ok=True)
    io.open(os.path.join(pl, u"runtime", u"python.exe"), u"wb").write(b"MZ")
    w(u"pl/version.json", u'{\n "version": "9.0.1",\n "channel": "internal"\n}')
    ok4, _ = check(pl, lambda s: None)
    say(ok4, u"T4 核正控：版在 ＋ runtime 在 ＋ 二源同 ＋ 装根 version.json 同 ⇒ 合")
    w(u"pl/version.json", u'{\n "version": "9.0.0",\n "channel": "internal"\n}')
    ok7, _ = check(pl, lambda s: None)
    say(not ok7, u"T4d 核反控：装根 version.json 9.0.0 ⟷ 载荷 9.0.1 ⇒ FAIL")
    os.remove(os.path.join(pl, u"version.json"))
    ok8, _ = check(pl, lambda s: None)
    say(not ok8, u"T4e 核反控：⛔ 见 version.json ⇒ FAIL（/health.build 必 false）")
    w(u"pl/version.json", u'{\n "version": "9.0.1",\n "channel": "internal"\n}')
    w(u"pl/pyproject.toml", u'[project]\nname = "clawsjoy"\nversion = "9.0.9"\n')
    ok6, _ = check(pl, lambda s: None)
    say(not ok6, u"T4c 核反控：version.py 9.0.1 ⟷ pyproject 9.0.9 ⇒ FAIL（一源之闸）")
    w(u"pl/pyproject.toml", u'[project]\nname = "clawsjoy"\nversion = "9.0.1"\n')
    os.makedirs(os.path.join(pl, u"web", u"images"), exist_ok=True)
    io.open(os.path.join(pl, u"web", u"images", u"a.jpg"), u"wb").write(b"J")
    ok5, _ = check(pl, lambda s: None)
    say(not ok5, u"T4b 核反控：载荷内 web/images ⇒ FAIL")

    # T7 器之副作用之清（正反控）
    pd = os.path.join(t, u"pe")
    w(u"pe/a.py", u"1")
    bef = snapshot(pd)
    w(u"pe/data/vector_kb/chroma.sqlite3", u"x")
    w(u"pe/logs/x.log", u"x")
    ex = prune_extras(pd, bef, lambda s: None)
    say(len(ex) == 2 and not os.path.exists(os.path.join(pd, u"data"))
        and not os.path.exists(os.path.join(pd, u"logs")) and os.path.isfile(os.path.join(pd, u"a.py")),
        u"T7 清器之副作用：新出之二件 ⇒ 抹 ∧ 其空之父夹 ⇒ 抹 ∧ **原之件⛔ 动**")
    say(os.path.isdir(pd), u"T7b 反控：载荷之本夹 ⇒ ⛔ 抹")

    # T8 混杂之捕（`__pycache__` ／ runtime 之份 ⛔ 捕）
    w(u"pe2/core/__pycache__/a.cpython-312.pyc", u"x")
    w(u"pe2/core/lib/version.py", u'__version__ = u"9.0.1"\n')
    w(u"pe2/runtime/Lib/site-packages/x/__pycache__/y.cpython-312.pyc", u"x")
    _s = stray_files(os.path.join(t, u"pe2"))
    say(_s == [u"core/__pycache__/a.cpython-312.pyc"],
        u"T8 混杂之捕：core 之 `.pyc` ⇒ 捕 ∧ **runtime 之 `.pyc` ⇒ ⛔ 捕**（其份）")

    # T5 删径之硬规
    for bad in (os.path.abspath(os.sep), os.path.abspath(ROOT)):
        try:
            rmtree_checked(bad)
            say(False, u"T5 ⛔ 删危险径（%s）竟未拦" % bad)
        except AssertionError:
            say(True, u"T5 拦危险径：%s ✓" % bad)

    # T6 运行时之源之判
    say(find_runtime_src(u"", cands=(t,)) is None,
        u"T6 运行时之源：候选皆无 runtime\\python.exe ⇒ None（照实 · ⛔ 猜）")
    say(find_runtime_src(pl, cands=()) == pl, u"T6b 运行时之源：显式有 ⇒ 取")
    say(find_runtime_src(pl, cands=(t,)) == pl, u"T6c 序取：显式先于候选")
    if fails:
        print(u"[自测] **FAIL %d ／ %d 条**" % (len(fails), len(n_hits)))
        return 2
    print(u"[自测] 皆过 ✓（%d/%d）" % (len(n_hits), len(n_hits)))
    rmtree_checked(t)
    return 0


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument(u"--root", default=ROOT)
    ap.add_argument(u"--ref", default=u"a121e90")
    ap.add_argument(u"--out", default=DEFAULT_OUT)
    ap.add_argument(u"--runtime-src", default=u"")
    ap.add_argument(u"--runtime", action=u"store_true", help=u"并 runtime\\（缺省＝并）")
    ap.add_argument(u"--no-runtime", action=u"store_true")
    ap.add_argument(u"--no-wheel", action=u"store_true")
    ap.add_argument(u"--go", action=u"store_true")
    ap.add_argument(u"--gate", action=u"store_true")
    ap.add_argument(u"--check", action=u"store_true")
    ap.add_argument(u"--json", action=u"store_true")
    ap.add_argument(u"--stamp", default=u"")
    ap.add_argument(u"--force", action=u"store_true")
    ap.add_argument(u"--allow-strays", action=u"store_true",
                    help=u"核已跑过之根（其 `__pycache__` 唯报 ⛔ 判红）")
    ap.add_argument(u"--self-test", action=u"store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    root = os.path.abspath(a.root)
    if not os.path.isdir(os.path.join(root, u".git")):
        print(u"[用法钥] 非 git 之根：%s ⇒ --root" % root)
        return 3
    out = os.path.abspath(a.out)
    log = (lambda s: None) if a.json else (lambda s: print(s))
    if a.check:
        ok, info = check(out, log, allow_strays=a.allow_strays)
        if a.json:
            print(json.dumps(dict(info, ok=ok), ensure_ascii=False, indent=1))
        else:
            print(u"[核] 判：%s" % (u"合" if ok else u"**⛔ 合**"))
        return 0 if ok else 2
    rtsrc = find_runtime_src(a.runtime_src)
    use_rt = not a.no_runtime
    use_wh = not a.no_wheel
    if not a.go:
        for s in plan(a.ref, out, root, rtsrc, use_wh, use_rt):
            print(s)
        print(u"[载荷] 干跑毕（⛔ 未落盘 —— 加 --go 真造）")
        return 0
    if os.path.isdir(out) and any(os.scandir(out)):
        if not a.force:
            print(u"[用法钥] 落处已非空：%s ⇒ --force（⛔ 静默覆盖）" % out)
            return 3
        rmtree_checked(out)
    os.makedirs(out, exist_ok=True)
    res, why, rows = apply(root, a.ref, out, rtsrc, wheel=use_wh, runtime=use_rt,
                           gate=a.gate, log=log)
    if res is None:
        print(u"[载荷] **FAIL** %s" % why)
        return 2
    info, okg = res
    for s in rows:
        print(s)
    if a.stamp:
        io.open(a.stamp, u"w", encoding=u"utf-8", newline=u"").write(
            json.dumps(info, ensure_ascii=False, indent=1) + u"\n")
        print(u"[载荷] 印之册：%s" % a.stamp)
    if a.json:
        print(json.dumps(info, ensure_ascii=False, indent=1))
    return 0 if okg else 2


if __name__ == u"__main__":
    sys.exit(main(sys.argv[1:]))