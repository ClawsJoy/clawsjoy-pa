# -*- coding: utf-8 -*-
u"""make_update.py -- 造**增量包**（甲-P0 之器一 · 承 pm_1620 §二.1 ＋ pm_1645 §二 令一 · 技术总监席 f202f89）。

其的（一句话）：把「本批之小修」从建机送到用户机 ⇒ **⛔ 重下整包**（`534.3 MB` ⟷ `≈ 0.6 MB`）。

形（承 `core/lib/update_manifest.py` 之**一处定形** · ⛔ 二处各写）：
  `update_manifest.json`（唯五键：`version` ／ `base_version` ／ `channel` ／ `built_at` ／ `files`）
  ＋ 逐件（`path` ＝ **装根相对之径** · 内容按径**镜像落盘** ⇒ 静态面 `<url><path>` 即取）。
  ＋ `ClawsJoyPA-Update.record.json`（器之印 ＋ 二 rev ＋ 数 —— 「包须自证其出处」· 承 pm_1573 §二）。

其域（**唯入包之件** · 承 pm_1620 §三.10「闭包 ⊆ 载荷」）：以 `make_client_bundle` 之
  `PAYLOAD` ／ `SKIP_NAMES` ／ `EXCLUDE` 为尺（**器取** · ⛔ 手拟）⇒ `tests/**` ／ `docs/**` ／
  `dist/**` ／ `data/**` ／ `logs/**` 之改 **⛔ 入增量**（其本 ⛔ 在客户端之树）。

用法：
  python -X utf8 scripts\\win_pa\\make_update.py --base <旧 rev> [--new HEAD] --out <dir>   # 干跑
  python -X utf8 scripts\\win_pa\\make_update.py --base <旧 rev> --out <dir> --go --json    # 真造
  ... [--version <v>] [--base-version <bv>] [--channel internal] [--root <仓根>] [--self-test]
退出码：0 成 ｜ 2 前置 ⛔ 足 ∨ 造败 ｜ 3 入口错
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import time

if sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BS = chr(92)
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
RECORD_NAME = u"ClawsJoyPA-Update.record.json"
#: ⛔ 入增量之「点名」（**一处定形** —— 双保险 ∧ ⛔ 静默）：密钥 ／ 本机态 ／ 用户数据。
NEVER = (u"config/.env", u"config/secrets.yaml", u"scripts/win_pa/ClawsJoyPA_PA_Boot.xml")
NEVER_PREFIX = (u"data/", u"logs/", u"dist/", u"tests/", u".git/", u"_share/",
                # ⭐ pm_1656 §三.3：**静态大件** ⇒ 入 ⛔ 入增量
                #   （彼二处 ⛔ 在运行之闭包 —— `sandbox_seed.SEED_EXCLUDE` 一手 ⇒
                #    若一改而入 ⇒ **一条增量可至数百 MB**）
                u"web/images/", u"web/mobile/")

#: 增量之阈（**一处定形** · pm_1656 §三.3）：超 ⇒ 红（须 `--allow-big` 明书）。
#: 其由：`web/images/` ／ `web/mobile/` 已入 `NEVER_PREFIX` ⇒ 常规增量 ≈ 1 MB 量级 ⇒
#: 超此数 ⇒ 疑「大件误入」（**⛔ 静默**）。
MAX_FILES = 400
MAX_BYTES = 8 * 1024 * 1024


def _add_core(root):
    if root not in sys.path:
        sys.path.insert(0, root)
    if HERE not in sys.path:
        sys.path.insert(0, HERE)


def git(root, *args, binary=False):
    u"""`git -C <root> …` ⇒ `(rc, out)`；`binary` ⇒ 原字节（⛔ 译码 —— 免 CRLF 之改）。"""
    r = subprocess.run([u"git", u"-C", root] + list(args), capture_output=True)
    if binary:
        return r.returncode, r.stdout
    return r.returncode, (r.stdout or b"").decode(u"utf-8", u"replace") + \
        (r.stderr or b"").decode(u"utf-8", u"replace")


def changed(root, base, new):
    u"""二 rev 之改（**⛔ 认重命名** —— 一律拆为 `del` ＋ `add`）⇒ `[(status, posix path)]`。"""
    # ⚠ `core.quotepath` 默认真 ⇒ 非 ASCII 之名被 **八进制之转义**（`"scripts/\345\207..."`
    #   ⇒ 清单之 `path` 成谎（下件必 404）—— 故**逐次关之**（真读数 · ⛔ 猜）。
    rc, out = git(root, u"-c", u"core.quotepath=false", u"diff", u"--name-status",
                  u"--no-renames", base, new)
    if rc != 0:
        return None, out.strip()[:300]
    rows = []
    for ln in out.splitlines():
        if not ln.strip():
            continue
        parts = ln.split(u"\t")
        if len(parts) < 2:
            return None, u"`git diff` 之行 ⛔ 解：%r" % ln[:120]
        rows.append((parts[0].strip()[:1], parts[-1].strip().replace(BS, u"/")))
    return rows, u""


def payload_pred(root):
    u"""「入包否」之尺（**器取** —— 引 `make_client_bundle` 之三表 · ⛔ 手拟）。"""
    import make_client_bundle as M
    tops = tuple(M.effective_payload(root))
    excl = set(M.EXCLUDE)
    skip = set(M.SKIP_NAMES)

    def inside(rel):
        if rel in excl:
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


def never(rel):
    u"""⛔ 入增量之点名 ⇒ 因 ∨ 空串（**一处定形** · pm_1417 ／ pm_1580 之族）。"""
    if rel in NEVER:
        return u"点名（密钥 ／ 机器相关）"
    for p in NEVER_PREFIX:
        if rel.startswith(p):
            return u"点名之前缀（%s）" % p
    return u""


def _totals(man):
    u"""清单之合数（**一处出** —— 借 `update_manifest.totals` ⇒ ⛔ 本器另算）。"""
    from core.lib import update_manifest as UM
    return UM.totals(man)


def _over_threshold(man):
    u"""超阈之因（**一处定形** · pm_1656 §三.3）⇒ `[因]` ∨ `[]`（合）。"""
    t = _totals(man)
    over = []
    if t[u"n"] > MAX_FILES:
        over.append(u"件数 %d > 阈 %d" % (t[u"n"], MAX_FILES))
    if t[u"bytes"] > MAX_BYTES:
        over.append(u"字节 %d > 阈 %d" % (t[u"bytes"], MAX_BYTES))
    return over


def pkg_version(root):
    u"""产品之版号（**一处定形** · ⛔ 字面）：`pyproject.toml[project].version`（≡ `core/lib/version.py`）。"""
    p = os.path.join(root, u"pyproject.toml")
    try:
        try:
            import tomllib as _tl
        except ImportError:
            _tl = None
        if _tl is not None:
            with io.open(p, u"rb") as fh:
                v = str(((_tl.load(fh).get(u"project") or {}).get(u"version") or u"")).strip()
            if v:
                return v, u"pyproject.toml[project].version"
    except Exception:                                         # noqa: BLE001 — 回落
        pass
    try:
        txt = io.open(p, encoding=u"utf-8", errors=u"replace").read()
        for ln in txt.splitlines():
            s = ln.strip()
            if s.startswith(u"version") and u"=" in s:
                v = s.split(u"=", 1)[1].strip().strip(u'"').strip(u"'")
                if v:
                    return v, u"pyproject.toml（逐行 · 兜底）"
    except Exception:                                         # noqa: BLE001 — 照实回落
        pass
    return u"", u"⛔ 读 pyproject.toml 之 version"


def _version_py_at(root, rev):
    rc, raw = git(root, u"show", u"%s:core/lib/version.py" % rev, binary=True)
    if rc != 0 or not raw:
        return None
    for ln in raw.decode(u"utf-8", u"replace").splitlines():
        s = ln.strip()
        if s.startswith(u"__version__") and u"=" in s:
            v = s.split(u"=", 1)[1].strip().strip(u'"').strip(u"'").strip()
            if v:
                return v
    return None


def _exists_at(root, rev, path):
    u"""件在某 rev 是否有（⇒ 判 `add` ／ `mod` 之诚 · ⛔ 猜）。"""
    rc, _o = git(root, u"cat-file", u"-e", u"%s:%s" % (rev, path))
    return rc == 0


def version_payload(root, rev, man):
    u"""装根 `version.json` 之内容（**一处定形** —— 逐键 ≡ `core.lib.build_info.FIELDS`）。
    其随增量**以常规之件**入（`path = version.json`）⇒ 升后**版号即可见**（承 pm_1620 §三.12）∧
    应用器**无须特判**（唯逐件换之）。
    """
    _rc, commit = git(root, u"rev-parse", u"%s^{commit}" % rev)
    _rc2, tree = git(root, u"rev-parse", u"%s^{tree}" % rev)
    return {"version": man[u"version"], "commit": commit.strip() or None,
            "tree": tree.strip() or None, "built_at": man[u"built_at"],
            "channel": man[u"channel"]}


def plan(root, base, new, version, base_version, channel, out, allow_big=False):
    u"""造之料（**⛔ 落盘**）⇒ `(rc, rows, manifest | None)`。"""
    rows = []
    if not os.path.isdir(os.path.join(root, u".git")):
        return 3, [u"[FAIL] %s 非 git 仓" % root], None
    for rev in (base, new):
        rc, _o = git(root, u"rev-parse", u"--verify", u"%s^{commit}" % rev)
        if rc != 0:
            return 3, [u"[FAIL] rev ⛔ 在：%s" % rev], None
    ch, why = changed(root, base, new)
    if ch is None:
        return 2, [u"[FAIL] 取 diff 败：%s" % why], None
    inside = payload_pred(root)
    keep, drop = [], []
    for st, rel in ch:
        nv = never(rel)
        if nv:
            drop.append((rel, nv))
            continue
        if not inside(rel):
            drop.append((rel, u"⛔ 在运行子集（`tests/**` ／ `docs/**` ／ …）"))
            continue
        keep.append((st, rel))
    rows.append(u"[PLAN] 二 rev 之差：%d 件 ⇒ 入增量 %d ／ 剔 %d"
                % (len(ch), len(keep), len(drop)))
    for rel, r in drop[:12]:
        rows.append(u"    [剔] %-58s %s" % (rel, r))
    if len(drop) > 12:
        rows.append(u"    …（余 %d 件略）" % (len(drop) - 12))
    files = []
    for st, rel in keep:
        if st == u"D":
            files.append({"path": rel, "sha256": u"", "size": 0, "mode": u"del"})
            continue
        rc, raw = git(root, u"show", u"%s:%s" % (new, rel), binary=True)
        if rc != 0:
            return 2, rows + [u"[FAIL] 取件败：%s@%s" % (rel, new)], None
        files.append({"path": rel, "sha256": hashlib.sha256(raw).hexdigest(),
                      "size": len(raw), "mode": u"mod" if st == u"M" else u"add"})
    man = {"version": version, "base_version": base_version, "channel": channel,
           "built_at": time.strftime(u"%Y-%m-%dT%H:%M:%S%z"), "files": files}
    # ⭐ 装根 `version.json` **随增量**（一处之定形 · 承 pm_1620 §三.12「版本可见」）：
    #   以常规之件入 ⇒ 应用器无须特判 ∧ 升后 `/health.build.available=true`。
    vraw = json.dumps(version_payload(root, new, man), ensure_ascii=False,
                      indent=1).encode(u"utf-8")
    files.append({"path": u"version.json", "sha256": hashlib.sha256(vraw).hexdigest(),
                  "size": len(vraw),
                  "mode": u"mod" if _exists_at(root, base, u"version.json") else u"add"})
    files.sort(key=lambda e: e["path"])
    over = _over_threshold(man)
    if over:
        msg = u"；".join(over)
        if not allow_big:
            return 2, rows + [
                u"[FAIL] 增量超阈：%s" % msg,
                u"       ⇒ 去处：核 `NEVER_PREFIX`（`web/images/` ／ `web/mobile/` ／ 大件之误入）"
                u" ∨ 确知 ⇒ 明书 `--allow-big`"], None
        rows.append(u"[WARN] 增量超阈（`--allow-big` 明书）：%s" % msg)
    return 0, rows, man


def build(root, man, out, new, base=None):
    u"""真造（**唯 `--go`**）：落清单 ＋ 逐件（镜像之径）⇒ `(rc, rows)`。"""
    from core.lib import update_manifest as UM
    rows = []
    ok, probs = UM.validate(man)
    if not ok:
        return 2, [u"[FAIL] 清单之形 ⛔ 合：%s" % u"；".join(probs[:4])]
    os.makedirs(out, exist_ok=True)
    n_ok = 0
    t0 = time.time()
    vraw = json.dumps(version_payload(root, new, man), ensure_ascii=False,
                      indent=1).encode(u"utf-8")
    for e in man["files"]:
        if e["mode"] == u"del":
            continue
        if e["path"] == u"version.json":
            raw = vraw
            rc = 0
        else:
            rc, raw = git(root, u"show", u"%s:%s" % (new, e["path"]), binary=True)
        if rc != 0 or hashlib.sha256(raw).hexdigest() != e["sha256"] or len(raw) != e["size"]:
            return 2, rows + [u"[FAIL] 件之印 ⛔ 合：%s（回读自校）" % e["path"]]
        dst = os.path.join(out, e["path"].replace(u"/", os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with io.open(dst, u"wb") as fh:
            fh.write(raw)
        n_ok += 1
    mp = os.path.join(out, UM.MANIFEST_NAME)
    with io.open(mp, u"w", encoding=u"utf-8", newline=u"") as fh:
        fh.write(json.dumps(man, ensure_ascii=False, indent=1))
    t = UM.totals(man)
    rec = {"tool": u"make_update.py", "tool_version": u"1.0", "base": base, "new": new,
           "manifest": mp, "digest": UM.digest(man), "version": man["version"],
           "base_version": man["base_version"], "channel": man["channel"],
           "files": t, "written": n_ok,
           "built_at": man["built_at"], "elapsed_s": round(time.time() - t0, 1)}
    rp = os.path.join(out, RECORD_NAME)
    with io.open(rp, u"w", encoding=u"utf-8", newline=u"") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False, indent=1))
    rows.append(u"[OK] 清单 → %s（印 %s）" % (mp, rec["digest"]))
    rows.append(u"[OK] 逐件 → %d 件（剔 %d）｜%d B（%.2f MB）｜%.1f s"
                % (t["n"], t["del"], t["bytes"], t["bytes"] / 1048576.0, rec["elapsed_s"]))
    rows.append(u"[OK] 记 → %s" % rp)
    return 0, rows


def say(ok, name):
    print(u"[%s] %s" % (u"OK" if ok else u"FAIL", name))
    return ok


def self_test():
    u"""自证（⛔ 出网 · ⛔ 落盘）：形 ／ 尺 ／ 守 之正反控。"""
    from core.lib import update_manifest as UM
    ok = True
    ok &= say(UM.bad_path(u"core/x.py") == u"", u"正控：常径合")
    ok &= say(bool(UM.bad_path(u"../x")) and bool(UM.bad_path(u"C:/x")) and \
              bool(UM.bad_path(u"a\\b")), u"反控：`..` ／ 盘符 ／ 反斜杠 ⇒ 拒")
    ok &= say(never(u"config/.env") != u"" and never(u"tests/unit/a.py") != u"", u"正控：点名 ／ 前缀 ⇒ ⛔ 入")
    ok &= say(never(u"core/lib/x.py") == u"", u"反控：常件 ⇒ 合")
    ok &= say(never(u"web/images/a.jpg") != u"" and never(u"web/mobile/vosk.bin") != u"",
              u"正控（pm_1656 §三.3）：`web/images/` ／ `web/mobile/` ⇒ ⛔ 入（免一条增量数百 MB）")
    man = {"version": u"9.0.1", "base_version": u"9.0.0", "channel": u"internal",
           "built_at": u"2026-10-07T00:00:00+0800",
           "files": [{"path": u"core/a.py", "sha256": u"a" * 64, "size": 3, "mode": u"add"},
                     {"path": u"core/b.py", "sha256": u"", "size": 0, "mode": u"del"}]}
    v_ok, probs = UM.validate(man)
    ok &= say(v_ok, u"正控：清单合（%s）" % (u"；".join(probs[:2]) or u"无瑕"))
    bad = json.loads(json.dumps(man))
    bad["files"][0]["sha256"] = u"XYZ"
    ok &= say(not UM.validate(bad)[0], u"反控：`sha256` 非 hex64 ⇒ ⛔ 合")
    bad2 = json.loads(json.dumps(man))
    bad2["files"][0]["path"] = u"../evil"
    ok &= say(not UM.validate(bad2)[0], u"反控：`path` 越界 ⇒ ⛔ 合")
    t = UM.totals(man)
    ok &= say(t[u"n"] == 2 and t[u"add"] == 1 and t[u"del"] == 1 and t[u"bytes"] == 3,
               u"正控：自述之数（%r）" % t)
    big = {"version": u"9.0.1", "base_version": u"9.0.0", "channel": u"internal",
           "built_at": u"2026-10-07T00:00:00+0800",
           "files": [{"path": u"core/x%d.py" % i, "sha256": u"a" * 64, "size": 16,
                      "mode": u"add"} for i in range(MAX_FILES + 1)]}
    ok &= say(_over_threshold(big) != [] and _over_threshold(man) == [],
              u"正控 ／ 反控：超阈之判（%r）" % (_over_threshold(big)[:1],))
    return 0 if ok else 2


def main(argv=None):
    ap = argparse.ArgumentParser(description=u"造增量包（甲-P0 之器一）")
    ap.add_argument(u"--root", default=ROOT)
    ap.add_argument(u"--base", default=None, help=u"旧 rev（出货之刻 · 见装根 version.json 之 commit）")
    ap.add_argument(u"--new", default=u"HEAD")
    ap.add_argument(u"--out", default=os.path.join(u"dist", u"update"))
    ap.add_argument(u"--version", default=None)
    ap.add_argument(u"--base-version", default=None)
    ap.add_argument(u"--channel", default=u"internal")
    ap.add_argument(u"--go", action="store_true")
    ap.add_argument(u"--json", action="store_true")
    ap.add_argument(u"--allow-big", action="store_true",
                    help=u"明书：许超阈之增量（否则超阈 ⇒ 红 · pm_1656 §三.3）")
    ap.add_argument(u"--self-test", action="store_true")
    a = ap.parse_args(argv)
    root = os.path.abspath(a.root)
    _add_core(root)
    if a.self_test:
        return self_test()
    if not a.base:
        print(u"[FAIL] 须 --base（旧 rev —— 出货之刻）")
        return 3
    ver, vwhy = (a.version, u"--version") if a.version else pkg_version(root)
    if not ver:
        print(u"[FAIL] 版号 ⛔ 得：%s" % vwhy)
        return 2
    bver = a.base_version or _version_py_at(root, a.base) or u""
    if not bver:
        print(u"[FAIL] base_version ⛔ 得（请 --base-version）")
        return 2
    out = a.out if os.path.isabs(a.out) else os.path.join(root, a.out)
    rc, rows, man = plan(root, a.base, a.new, ver, bver, a.channel, out,
                         allow_big=a.allow_big)
    print(u"\n".join(rows))
    if rc != 0:
        return rc
    if a.json:
        print(json.dumps(man, ensure_ascii=False, indent=1))
    if not a.go:
        print(u"[--] 干跑（⛔ 落盘）—— 加 --go 真造 ⇒ %s" % out)
        return 0
    rc2, rows2 = build(root, man, out, a.new, base=a.base)
    print(u"\n".join(rows2))
    return rc2


if __name__ == u"__main__":
    sys.exit(main())