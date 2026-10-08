# -*- coding: utf-8 -*-
u"""publish_share.py -- 上板器（**一处定形** · 承 PM 请办 `2019 §三.3` · 技术总监席 f202f89）。

其的（一句话）：把「**出包产物根**」之载荷 ＋ 册 ＋ 版 ＋ 记录 **保径**落到分享面（板之静态根）。

⭐⭐ 铁律（本器之存在唯此一条）：
  ⒜ **件唯自「出包产物根」取**（`--src`）—— ⛔ 自工作树（`D:\\clawsjoy_v9` 之树）取。
     由（一手之实 · `2019`）：`_share\\web\\pa\\faces\\config.js` 曾落「工作树之**未提交**之形」
     （`bdedf3cbe1e1908c` ／ `11,365 B`）而册所载者 ＝ **git rev 之件**（`afcb0996ae1397c6` ／ `10,480 B`）
     ⇒ 更新器「逐件校」⇒ 瑕 `1` ⇒ **整体 ⛔ 落**（`exit=2` · 未动盘）。
     ⇒ 根因 ＝ **清单（自 git rev 生成）与载荷（自工作树落盘）不同源** ⇒ 凡工作树有未提交之改 ⇒ 该件必不合。
  ⒝ **落件前核源 ∧ 落件后核面**（二次逐件 · `sha256` ＋ `size`）⇒ 任一处不合 ⇒ **出单 ＋ ⛔ 静默放行**。
  ⒞ **⛔ 硬删**：面上之旧件 ／ 下架之件 唯**移**入 `--old`（可撤回）。

三态：
  `--stage src`（缺省）＝ 唯核「出包根」 vs 册（⛔ 落一件）
  `--stage publish`   ＝ 源核 ⇒ 落（载荷 ⇒ 册 ／ 版 ／ 记录于**最后**）⇒ 面核
  `--stage face`      ＝ 唯核「面」 vs 册（供复核 ／ 供病后定位）

用法：
  python -X utf8 -B scripts\\win_pa\\publish_share.py --src <出包根>
  python -X utf8 -B scripts\\win_pa\\publish_share.py --src <出包根> --stage publish --go
  python -X utf8 -B scripts\\win_pa\\publish_share.py --stage face --dst <面根>
  python -X utf8 -B scripts\\win_pa\\publish_share.py --self-test

退出码：0 成 ／ 2 源 ∨ 面不合（出单）／ 3 入口错
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time

if sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DEFAULT_DST = r"D:\paseo-workspace\_share"
#: 「后落」之三件（**一处定形** · 承旧例「先件后册」⇒ 免「册已新而件未落」）
LATE = (u"ClawsJoyPA-Update.record.json", u"version.json", u"update_manifest.json")
#: 面上之载荷顶（报「册不载之件」之射程）
PAYLOAD_TOPS = (u"core", u"scripts", u"web", u"pyproject.toml")
MAN = u"update_manifest.json"
CHUNK = 1 << 20


def _core():
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)


def _um():
    _core()
    from core.lib import update_manifest as UM
    return UM


def sha16_bytes(b):
    return hashlib.sha256(b).hexdigest()[:16]


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(CHUNK), b""):
            h.update(c)
    return h.hexdigest()


def _join(root, rel):
    return os.path.join(root, rel.replace(u"/", os.sep))


def load_manifest(src):
    u"""读 ／ 校册 ⇒ `(doc, probs)`（⛔ 静默：形不法即出单）。"""
    p = _join(src, MAN)
    if not os.path.isfile(p):
        return None, [u"源无册：%s" % p]
    try:
        doc = json.loads(open(p, "rb").read().decode(u"utf-8"))
    except Exception as e:                                            # noqa: BLE001
        return None, [u"册 ⛔ 解：%s" % e]
    ok, probs = _um().validate(doc)
    if not ok:
        return None, [u"册之形不法："] + list(probs)
    return doc, []


def check_tree(root, man, what=u"件"):
    u"""逐件核 `root` vs 册 ⇒ `[(path, 因)]`（非 del ⇒ 在 ∧ 印尺合；del ⇒ **不在**）。"""
    bad = []
    for it in man[u"files"]:
        rel, mode = it[u"path"], it[u"mode"]
        p = _join(root, rel)
        if mode == u"del":
            if os.path.exists(p):
                bad.append((rel, u"册曰 del 而%s仍在" % what))
            continue
        if not os.path.isfile(p):
            bad.append((rel, u"%s缺件" % what))
            continue
        n = os.path.getsize(p)
        if n != it[u"size"]:
            bad.append((rel, u"%s尺 ≢ 册（%d ≠ %d）" % (what, n, it[u"size"])))
            continue
        h = sha256_file(p)
        if h != it[u"sha256"]:
            bad.append((rel, u"%s印 ≢ 册（%s ≠ %s）" % (what, h[:16], it[u"sha256"][:16])))
    return bad


def stale_on_face(dst, man, tops=PAYLOAD_TOPS):
    u"""面上「册不载」之载荷件（唯报 · ⛔ 擅动）。"""
    want = {f[u"path"] for f in man[u"files"]} | set(LATE)
    extra = []
    for top in tops:
        p = _join(dst, top)
        if os.path.isfile(p):
            if top not in want:
                extra.append(top)
            continue
        for dp, _dn, fn in os.walk(p):
            for f in fn:
                q = os.path.join(dp, f)
                rel = os.path.relpath(q, dst).replace(os.sep, u"/")
                if rel not in want:
                    extra.append(rel)
    return sorted(extra)


def publish(src, dst, old, dry=False):
    u"""源核 ⇒ 落 ⇒ 面核（`dry` ⇒ 唯源核）。"""
    man, probs = load_manifest(src)
    if man is None:
        print(u"[FAIL] %s" % u"；".join(probs))
        return 3
    st = _um().totals(man)
    print(u"[册] %s ⇐ %s ｜ 件 %d（add %d ／ mod %d ／ del %d）｜ %d B ｜ built %s"
          % (man[u"version"], man[u"base_version"], st[u"n"], st[u"add"], st[u"mod"],
             st[u"del"], st[u"bytes"], man[u"built_at"]))
    bad = check_tree(src, man, u"源")
    print(u"[源核] %s" % (u"合（瑕 0）" if not bad else u"⛔ 不合 %d" % len(bad)))
    for b in bad:
        print(u"    [!] %s  %s" % b)
    if bad:
        print(u"[判] ⛔ 源 ≢ 册 ⇒ **⛔ 落一件**（rc=2）")
        return 2
    if dry:
        print(u"[干跑] 源核过 ⇒ 未落（真落须 `--stage publish --go`）")
        return 0
    print(u"[落件]")
    n = 0
    for it in man[u"files"]:
        rel = it[u"path"]
        if rel in LATE:
            continue
        d = _join(dst, rel)
        if it[u"mode"] == u"del":
            if os.path.isfile(d):
                t = os.path.join(old, rel.replace(u"/", u"__"))
                os.makedirs(os.path.dirname(t), exist_ok=True)
                shutil.move(d, t)
                print(u"    %-46s -> _old/%s" % (rel, os.path.basename(t)))
            continue
        s = _join(src, rel)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        if os.path.isfile(d) and sha256_file(d) == it[u"sha256"]:
            print(u"    %-46s %8d  合（⛔ 复写）" % (rel, it[u"size"]))
            continue
        shutil.copyfile(s, d)
        n += 1
        print(u"    %-46s %8d  %s" % (rel, it[u"size"], it[u"mode"]))
    print(u"[落册]（最后）")
    for rel in LATE:
        s, d = _join(src, rel), _join(dst, rel)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copyfile(s, d)
        print(u"    %-46s %8d" % (rel, os.path.getsize(s)))
    bad2 = check_tree(dst, man, u"面")
    print(u"[面核] %s" % (u"合（瑕 0）" if not bad2 else u"⛔ 不合 %d" % len(bad2)))
    for b in bad2:
        print(u"    [!] %s  %s" % b)
    extra = stale_on_face(dst, man)
    if extra:
        print(u"[照实] 面上「册不载」之载荷件 %d（唯报 · ⛔ 擅动）：" % len(extra))
        for e in extra[:20]:
            print(u"    ? %s" % e)
    raw = open(_join(dst, MAN), "rb").read()
    print(u"[印] 册裸印 %s ／ UM.digest %s ／ 落 %d 件 ／ 面瑕 %d"
          % (sha16_bytes(raw), _um().digest(json.loads(raw.decode(u"utf-8"))), n, len(bad2)))
    print(u"[判] %s" % (u"成 ✓" if not bad2 else u"⛔ 面 ≢ 册（rc=2）"))
    return 0 if not bad2 else 2


def face_check(dst):
    u"""唯核「面」 vs 册（供复核 ／ 供病后定位）。"""
    man, probs = load_manifest(dst)
    if man is None:
        print(u"[FAIL] %s" % u"；".join(probs))
        return 3
    bad = check_tree(dst, man, u"面")
    print(u"[面核] 件 %d ／ 不合 %d" % (len(man[u"files"]), len(bad)))
    for b in bad:
        print(u"    [!] %s  %s" % b)
    return 0 if not bad else 2


def _mk(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def self_test():
    u"""自证四例：落成 ／ 源不合即拒 ／ 面不合即咬（`2019` 之病之正控）／ 多余件必报。"""
    import tempfile
    n = 0
    root = tempfile.mkdtemp(prefix=u"pub2019_")
    src, dst = os.path.join(root, u"out"), os.path.join(root, u"face")
    body = {u"a/b.txt": b"hello\n", u"web/pa/faces/config.js": b"cfg-committed\n"}
    for rel, b in body.items():
        _mk(_join(src, rel), b)
    files = [{u"path": rel, u"mode": u"add", u"size": len(b),
              u"sha256": hashlib.sha256(b).hexdigest()} for rel, b in body.items()]
    files.append({u"path": u"old/gone.txt", u"mode": u"del", u"size": 0, u"sha256": u""})
    man = {u"version": u"9.0.11", u"base_version": u"9.0.10", u"channel": u"internal",
           u"built_at": u"2026-10-08T20:00:00+0800", u"files": files}
    _mk(_join(src, MAN), json.dumps(man, ensure_ascii=False).encode(u"utf-8"))
    _mk(_join(src, u"version.json"), b'{"version":"9.0.11"}')
    _mk(_join(src, u"ClawsJoyPA-Update.record.json"), b'{"digest":"x"}')
    _mk(_join(dst, u"old/gone.txt"), b"stale")
    _mk(_join(dst, u"web/pa/faces/config.js"), b"cfg-worktree-DIRTY\n")
    old = os.path.join(dst, u"_old", u"stamp")
    rc = publish(src, dst, old)
    ok = (rc == 0
          and sha256_file(_join(dst, u"web/pa/faces/config.js")) == files[1][u"sha256"]
          and not os.path.exists(_join(dst, u"old/gone.txt"))
          and os.path.isfile(os.path.join(old, u"old__gone.txt")))
    print(u"[自证 1/4] 落 ∧ 面核合 ∧ del 唯移 ⛔ 删：%s" % (u"✓" if ok else u"✗"))
    n += 1 if ok else 0

    before = sha256_file(_join(dst, u"a/b.txt"))
    _mk(_join(src, u"a/b.txt"), b"tampered\n")
    rc = publish(src, dst, old)
    ok = rc == 2 and sha256_file(_join(dst, u"a/b.txt")) == before
    print(u"[自证 2/4] 源 ≢ 册 ⇒ 拒 ∧ ⛔ 落一件（面未动）：%s" % (u"✓" if ok else u"✗"))
    n += 1 if ok else 0

    _mk(_join(src, u"a/b.txt"), body[u"a/b.txt"])
    _mk(_join(dst, u"web/pa/faces/config.js"), b"cfg-worktree-DIRTY\n")
    rc = face_check(dst)
    ok = rc == 2
    print(u"[自证 3/4] 面上「工作树之形」⇒ 面核咬：%s" % (u"✓" if ok else u"✗"))
    n += 1 if ok else 0

    _mk(_join(dst, u"web/pa/faces/zzz.js"), b"orphan")
    ok = u"web/pa/faces/zzz.js" in stale_on_face(dst, man)
    print(u"[自证 4/4] 面上多余件必报：%s" % (u"✓" if ok else u"✗"))
    n += 1 if ok else 0

    shutil.rmtree(root, ignore_errors=True)
    print(u"[自证] %d/4" % n)
    return 0 if n == 4 else 2


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument(u"--src", default=None, help=u"出包产物根（含 update_manifest.json）")
    ap.add_argument(u"--dst", default=DEFAULT_DST, help=u"分享面根（板之静态根）")
    ap.add_argument(u"--old", default=None, help=u"下架件之归档根（缺省 dst\\_old\\<stamp>）")
    ap.add_argument(u"--stage", default=u"src", choices=(u"src", u"publish", u"face"))
    ap.add_argument(u"--go", action="store_true", help=u"`--stage publish` 之真落闸")
    ap.add_argument(u"--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    if a.stage == u"face":
        return face_check(a.dst)
    if not a.src:
        print(u"[FAIL] 缺 `--src`（出包产物根）")
        return 3
    if not os.path.isdir(a.src):
        print(u"[FAIL] 源 ⛔ 在：%s" % a.src)
        return 3
    old = a.old or os.path.join(a.dst, u"_old", time.strftime(u"%Y%m%d-%H%M%S"))
    return publish(a.src, a.dst, old, dry=not (a.stage == u"publish" and a.go))


if __name__ == "__main__":
    sys.exit(main())
