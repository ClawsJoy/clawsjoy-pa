# -*- coding: utf-8 -*-
r"""scan_bom.py —— **BOM 面之常闸**：扫「面」找「同族之件首三字节 ＝ EF BB BF」之处；⭐ 须带基线 ⇒ 唯报「净增／净减」。

⭐ 为何须此器（PM b136893 · `1215 §二` ＋ `1218 §一` ＋ `1220` 之**终形表**）：
  源 ＝ PS 5.1 之 `Set-Content -Encoding UTF8` ⇒ **带 BOM**（承「一律『器之输入形』」）。
  ⭐ 其害（读者侧）：Python 自会剥 BOM ⇒ 零功能害；⚠ 唯「以 `utf-8` 读之器」⇒ **假 SyntaxError**
     （PM 本刻即中一次 · 10 条假红）⇒ ⭐ 治读法 ＋ 闸（承「探针 ≠ 活闸」）。

--- 域定义（逐字 · ⭐ 何谓一处 BOM 坑）---
  一处 BOM 坑 ＝ 件之**首三字节** ＝ `EF BB BF`（UTF-8 BOM）∧ 其后缀属**本闸之族**（默认 `.py` · 承 `1220 项1`）。
  ⚠ ⛔ 过杀之界：⛔ 判「**内含** U+FEFF」（唯**首**三字节）｜⛔ 判「读得之串」（唯**字节**）。
  ⚠ 域外之后缀（如 `.md` 带 BOM）⇒ ⛔ 报 —— 其非本闸之面（⛔ 过杀）。
  ⚠ 同族（`.js` ／ `.txt`）⛔ 入默认 ⇒ 须 `--ext` ＋ `--rebase`（承 `1215 §二.1` 之「同族」· 见 `1220 项1` 之裁）。

--- ⭐ 净增之判据（承 `1220 项5` · 键 ＝ 名）---
  ⭐ **净增 ≡ 现刻「BOM 件『名』之集」− 基线之「名之集」**｜**主键 ＝ 名**（⭐ **归一化相对径**）
    · 新落 ＝ 名 ∉ 基线｜· 净减 ＝ 名 ∈ 基线 ∧ ⛔ 在现刻
      ⚠ 二者皆「BOM 件『名』之集」之差 ⇒ ⛔ 谓「件之存亡 ／ 已删 ／ 新件 ／ 件之增」（承 PM 1269 §二 · PM 1273 §二 · PM 1274 §二 · 辞须与机制合）。
  ⭐ **内容印 `sha16` ⇒ 另栏**（报「**同名而内容变**」为**信息** · ⛔ 混入净增 —— 由：键含印 ⇒
     基线内之件一经改动即被报 ＝ **假阳** ∧ 与反控⒉「基线内之存量件 ⇒ ⛔ 报」**相悖**）。
  ⚠ `mtime` **唯作辅**（打印于每件之后）· ⛔ 参与判据 —— **由**：`Copy-Item` 保 `mtime`（假阴）／
     `touch` 撞新（假阳）⇒ **`mtime` 与「是否带 BOM」无稳定关系**（CW `1216 §三` 之活证 · PM `1217 §一` 认）。
  ⚠ ⭐ **名之归一须两读一致**（相对径 ＋ 大小写 · 见 `rel_key`）—— ⛔ 一致 ⇒ **同件异名 ⇒ 假阳**。

--- ⭐ 基线（分域 · 承 `1218 §一.更⒉` ＋ `1220 项4`）---
  基线 ＝ JSON：`{基线之刻, 域, 面:[{面之径, 刻, 件数, 印, 件:{相对名: sha16}}]}`。
  ⭐ **分域**：一面一节（各附**面 ＋ 刻 ＋ 印**）⇒ ⛔ 一面之数载二面之物｜⭐ **面之印 ＝ 名→印 映射之正则 sha16**（基线自证）。
  基线**可更**：`--rebase` ⇒ 以本刻之扫果重写基线（⭐ **一改一底**：原基线存 `…json.before_<sha16>`）。

--- ⭐ 扫面（承 `1218 §一.更⒊` ＋ `1220 项3` ＋ `1220 §三`）---
  ⭐ 默认扫面 ≡ **基线之面之并**（⛔ 给 `--root` 时 · 逐面之径）—— ⛔ ≡ ⇒ 「固为仓内（非缺）而不扫」之件 ⭐ **⛔ 入集 · 不可见**。
  ⭐ **面之缺须报**：某面不可达 ⇒ 报「未跑全」（退码 4）· ⛔ 默 —— 由：承「**面不可得 ⛔ ＝ 量得 0**」。
  ⚠ ⭐ **二者互补 · ⛔ 相代**：只设前者 ⇒ 「不扫」之面仍不可见；只设后者 ⇒ 「不可达」之根被当零 ⇒ **须并存**。
  ⭐ **面之「类」**：`目录`（走树 · 默认）／ `git已追`（唯 `git ls-files` 之件 · ⛔ 目录直走 · 承 PM 1221 §二.⒞.2）。
  ⚠ ⭐ **覆盖之界（明知 · 承 PM 1223 §二 · 界须随器）**：本闸 ⛔ 覆 ——
    ⒜ **`git已追` 之面外之件**（⛔ 入版本者）—— 由：**产品之真源 ＝ 已入版本**（承「入库 ＝ 快照」之族）⇒ 先入版本 · 后论其形
    ⒝ ⭐ **`.gitignore` 覆之件**（如 `data/**`）／ ⭐ **未追之新件** —— 彼等之 BOM ⇒ ⭐ **本闸 ⛔ 见**（**明知之界 · ⛔ 掩**）
  ⇒ ⭐ **若日后有「未追而长存之产品源」** ⇒ **另立面**（附 面之定义 ＋ 基线 ＋ 反控）· ⛔ **扩本面**
     —— 由：「**已追**」与「**未追**」之义 ⛔ 同（承「**界须落在『实』上**」）｜承 PM 1222 §二 ／ 1223 §二。

--- 用法 ---
  python scan_bom.py [--root <目录>]... [--face <目录>]... [--face-git <仓根>]... [--ext .py]
                     [--baseline <json>] [--rebase] [--json] [--all] [--selftest]
    --root      本刻要扫之根（可重复 · ⛔ 给 ⇒ 默认用「基线之面之并」；`--rebase` 时兼作「入基线之面」）
    --face      入基线之面（**目录** · 可重复 · 唯 `--rebase` 用 · 皆 ⛔ 给 ⇒ 用旧基线之面 ／ 内定二面）
    --face-git  入基线之面（⭐ **已追**：面之定义 ＝ `git ls-files` 之件 · ⛔ 目录直走 · 承 PM 1221 §二.⒞.2）
    --ext       本闸之族（可重复 · 默认 `.py`）
    --baseline  基线之径（默认：本器同目录之 `scan_bom_baseline.json`）
    --rebase    以本刻之扫果重写基线（⭐ 一改一底 · 唯一写路）
    --all       含 `.git` 与 `__pycache__`（默认排除 · 彼等非「活件」之面）

--- 退出码（同 `scan_path_names.py` 之族 · ⚠ 一处更：面之缺之 4 先于 5）---
  0 = 已扫且净（⛔ 无净增 ∧ ⛔ 无净减）
  2 = **有异**（净增 ∨ 净减 · 判红 · 须改 ∨ `--rebase`）
  3 = 用法／路径错 ∨ 基线缺失（**闸没跑** · 与「判红」⛔ 同）
  4 = 闸未跑完（**面之缺 ∨ 坏件 > 0** ⇒ ⛔ 得报 0 · 承「不可达 ≠ 0」）
  5 = **无件可扫**（**件数 == 0** ⇒ ⛔ 得报 0 · 承「空 ≠ 缺」）
  优先级：3 > **4（面之缺）** > 5 > 4（坏件）> 2 > 0
    ⚠ 我更 `1215 §二.5` 一处：**面之缺之 4 先于 5** —— 由：若先判 5 ⇒ 「面全缺」被读作「无件可扫」
       ＝ **把「面不可得」读成「量得 0」**（正 `1218 §一.新增` 所禁）。

唯读（除 `--rebase`）· 附印（器印 ＋ 面之径 ＋ 取数刻）· 可唯读调。
"""
import argparse
import datetime
import hashlib
import io
import json
import os
import subprocess
import sys

# ⭐ 2026-10-06（pm_1409 §二.3 · 批二）：自仓根起 ⇒ `core.lib.paths` 可导（直跑 ∨ 引皆可）。
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
from core.lib.paths import org_path   # ⭐ 组织物之径之唯一出口（⛔ 字面）

BOM = b"\xef\xbb\xbf"
DEFAULT_EXTS = (".py",)
SKIP_NAMES = (".git", "__pycache__")
HERE = os.path.abspath(__file__)
DEFAULT_BASELINE = os.path.join(os.path.dirname(HERE), "scan_bom_baseline.json")
# ⭐ 内定二面（承 PM `1220 项3`）：仓内 _pm ＋ 仓外 _pm —— ⛔ 给 --face ∧ ⛔ 有基线时所用。
# ⭐ 2026-10-06（pm_1409 §二.3 · 批二）：二径之字面 ⇒ 拔。
#   仓内 _pm ⇒ 自 `__file__` 推（**产品级** · ⛔ 字面）；仓外 _pm ⇒ `org_path`（**组织版** · 缺 ⇒ ⛔ 入表）。
_PM_IN = os.path.join(_REPO_ROOT, "_pm")
_PM_OUT = org_path("PA_PM_OUT")
DEFAULT_FACES = tuple(x for x in (_PM_IN, _PM_OUT) if x)

RC_MEAN = {
    0: u"已扫且净",
    2: u"有异（净增 ∨ 净减 · 判红）",
    3: u"用法／路径错 ∨ 基线缺失（闸没跑）",
    4: u"闸未跑完（面之缺 ∨ 坏件>0）",
    5: u"无件可扫（件数==0）",
}


def sha16(path):
    try:
        with io.open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except Exception:
        return None


def sha16_bytes(b):
    return hashlib.sha256(b).hexdigest()[:16]


def mtime(path):
    try:
        return os.path.getmtime(path)
    except Exception:
        return 0.0


def mt_str(t):
    try:
        return datetime.datetime.fromtimestamp(t).astimezone().strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return u"?"


def now_stamp():
    return datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S%z")


def rel_key(root, p):
    u"""⭐ 名之归一（两读一致）：相对径 ＋ 正斜杠 ＋ 小写 —— 免「同件异名 ⇒ 假阳」。"""
    r = os.path.relpath(p, root).replace(os.sep, "/")
    if "\\" in r:
        r = r.replace("\\", "/")
    return r.lower()


def scan(root, exts, all_):
    u"""返：(件数, [(绝对径, mtime), ...], [坏件, ...])。"""
    entries = 0
    hits = []
    bad = []
    for dirpath, dirnames, filenames in os.walk(root):
        if not all_:
            dirnames[:] = [d for d in dirnames if d not in SKIP_NAMES]
        for f in filenames:
            if os.path.splitext(f)[1].lower() not in exts:
                continue
            p = os.path.abspath(os.path.join(dirpath, f))
            entries += 1
            try:
                with io.open(p, "rb") as fh:
                    head = fh.read(3)
            except Exception as e:
                bad.append({"path": p, "err": "%s" % e})
                continue
            if head == BOM:
                hits.append((p, mtime(p)))
    return entries, hits, bad


def face_map(root, exts, all_):
    u"""扫一面 ⇒ (件数, {相对名: sha16}, {相对名: 绝对径}, {相对名: mtime}, 坏件)。"""
    entries, hits, bad = scan(root, exts, all_)
    hmap = {}
    dmap = {}
    mmap = {}
    for p, mt in hits:
        k = rel_key(root, p)
        hmap[k] = sha16(p)
        dmap[k] = p
        mmap[k] = mt
    return entries, hmap, dmap, mmap, bad


def git_tracked(root, exts):
    u"""⭐ 面之定义 ＝ `git ls-files`（唯**已追** · ⛔ 目录直走 · 承 PM 1221 §二.⒞.2）。"""
    r = subprocess.run(["git", "-C", root, "ls-files", "-z"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0:
        raise RuntimeError(u"git ls-files rc=%d" % r.returncode)
    names = [x for x in r.stdout.decode("utf-8", "surrogateescape").split(u"\0") if x]
    return [x for x in names if os.path.splitext(x)[1].lower() in exts]


def git_face(root, exts):
    u"""扫「已追」之面 ⇒ 同 face_map 之形（⛔ 目录直走 · 唯 git ls-files 之件）。"""
    try:
        rels = git_tracked(root, exts)
    except Exception:
        return None
    entries = 0
    hmap, dmap, mmap, bad = {}, {}, {}, []
    for rel in rels:
        entries += 1
        p = os.path.abspath(os.path.join(root, rel.replace(u"/", os.sep)))
        try:
            with io.open(p, "rb") as fh:
                head = fh.read(3)
        except Exception as e:
            bad.append({"path": p, "err": "%s" % e})
            continue
        if head == BOM:
            k = rel_key(root, p)
            hmap[k] = sha16(p)
            dmap[k] = p
            mmap[k] = mtime(p)
    return entries, hmap, dmap, mmap, bad


def face_scan(fdef, exts, all_):
    u"""按面之「类」扫。返 None ⇒ **面不可达**（面之缺 ∨ ⛔ 为仓 · 承 `1218 §一.新增`）。"""
    root = fdef.get(u"面之径") or u""
    kind = fdef.get(u"类") or u"目录"
    if not os.path.isdir(root):
        return None
    if kind == u"git已追":
        return git_face(root, exts)
    return face_map(root, exts, all_)


def face_seal(hmap):
    u"""面之印 ＝ 其「名→印」映射之正则 sha16（键排序 · ⛔ 附 mtime ⇒ 印随值）。"""
    canon = json.dumps({k: hmap[k] for k in sorted(hmap)}, ensure_ascii=False,
                       separators=(",", ":")).encode("utf-8")
    return sha16_bytes(canon)


def load_baseline(path):
    if not os.path.isfile(path):
        return None
    with io.open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_baseline(path, data):
    u"""一改一底：原基线先存 `.before_<sha16>`。"""
    bak = None
    if os.path.isfile(path):
        h = sha16(path)
        bak = path + ".before_" + (h or "unknown")
        with io.open(path, "rb") as fi, io.open(bak, "wb") as fo:
            fo.write(fi.read())
    tmp = path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True))
        f.write(u"\n")
    os.replace(tmp, path)
    return bak


def delta_per_face(hmap, base_map):
    u"""⭐ 名之集差。返 (新落, 同名而内容变, 净减) —— ⚠ 皆以「名」为键。"""
    fresh = sorted(k for k in hmap if k not in base_map)
    chg = sorted(k for k in hmap if k in base_map and hmap[k] != base_map[k])
    gone = sorted(k for k in base_map if k not in hmap)
    return fresh, chg, gone


# ---------------- 自证（闸须有反控 · 承「⛔ 唯正控不成闸」）----------------
POS = [b"\xef\xbb\xbf# -*- coding: utf-8 -*-", b"\xef\xbb\xbfimport os",
       b"\xef\xbb\xbf\xef\xbb\xbfx"]
NEG = [b"# -*- coding: utf-8 -*-", b"import os", b"", b"\xef\xbb", b"\xef\xbb\xbf"[::-1],
       b"x\xef\xbb\xbf"]


def _bom_of(head):
    return head[:3] == BOM


def _quiet_main(args):
    old_o = sys.stdout
    old_e = sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    try:
        rc = main(args)
        return rc, sys.stdout.getvalue()
    finally:
        sys.stdout = old_o
        sys.stderr = old_e


def selftest():
    import shutil
    import tempfile
    bad = []
    for p in POS:
        if not _bom_of(p):
            bad.append(u"正控未中：%r" % p)
    for n in NEG:
        if _bom_of(n):
            bad.append(u"反控误中：%r" % n)
    n_ctrl = 0
    root = tempfile.mkdtemp(prefix="scan_bom_st_")
    try:
        face = os.path.join(root, "face")
        os.makedirs(face)
        base = os.path.join(root, "base.json")

        def w(name, data, mt=None):
            p = os.path.join(face, name)
            with io.open(p, "wb") as f:
                f.write(data)
            if mt is not None:
                os.utime(p, (mt, mt))
            return p

        n_ctrl += 1
        if _quiet_main(["--root", face, "--baseline", base])[0] != 3:
            bad.append(u"反控：无基线 ⇒ 应 rc3（闸没跑）")
        w("a.py", b"x=1\n")
        n_ctrl += 1
        if _quiet_main(["--root", face, "--baseline", base, "--rebase"])[0] != 0:
            bad.append(u"反控：rebase 初立 ⇒ 应 rc0")
        n_ctrl += 1
        if _quiet_main(["--root", face, "--baseline", base])[0] != 0:
            bad.append(u"反控1：无 BOM 之 .py ⇒ 应 rc0（⛔ 报）")
        w("b.py", BOM + b"y=2\n")
        n_ctrl += 1
        if _quiet_main(["--root", face, "--baseline", base])[0] != 2:
            bad.append(u"正控：新落 BOM ⇒ 应 rc2（报）")
        src = os.path.join(root, "old_bom.py")
        with io.open(src, "wb") as f:
            f.write(BOM + b"z=3\n")
        os.utime(src, (1000000000, 1000000000))
        shutil.copy2(src, os.path.join(face, "copied.py"))
        n_ctrl += 1
        if _quiet_main(["--root", face, "--baseline", base])[0] != 2:
            bad.append(u"反控3：复制而 mtime 旧之 BOM ⇒ 应 rc2（名差 · ⛔ 漏）")
        os.remove(os.path.join(face, "copied.py"))
        _quiet_main(["--root", face, "--baseline", base, "--rebase"])
        n_ctrl += 1
        if _quiet_main(["--root", face, "--baseline", base])[0] != 0:
            bad.append(u"反控2：基线内之存量 BOM ⇒ 应 rc0（⛔ 报）")
        w("b.py", BOM + b"y=2\n")
        n_ctrl += 1
        if _quiet_main(["--root", face, "--baseline", base])[0] != 0:
            bad.append(u"反控2：重写同内容 ⇒ 应 rc0（⛔ 报）")
        w("b.py", BOM + b"y=99\n")
        rc_c, out_c = _quiet_main(["--root", face, "--baseline", base])
        n_ctrl += 1
        if rc_c != 0:
            bad.append(u"反控2：同名而内容变 ⇒ 应 rc0（唯信息 · ⛔ 入净增）")
        elif u"同名而内容变" not in out_c:
            bad.append(u"反控2：同名而内容变 ⇒ 须报为信息（今无此栏）")
        os.remove(os.path.join(face, "b.py"))
        n_ctrl += 1
        if _quiet_main(["--root", face, "--baseline", base])[0] != 2:
            bad.append(u"反控4：删一件带 BOM ⇒ 应 rc2（须报净减 · ⛔ 静默）")
        _quiet_main(["--root", face, "--baseline", base, "--rebase"])
        w("c.py", b"x=1\n" + BOM + b"tail\n")
        n_ctrl += 1
        if _quiet_main(["--root", face, "--baseline", base])[0] != 0:
            bad.append(u"反控：内嵌 EF BB BF（⛔ 首三字节）⇒ 应 rc0（⛔ 报）")
        w("d.md", BOM + b"# t\n")
        n_ctrl += 1
        if _quiet_main(["--root", face, "--baseline", base])[0] != 0:
            bad.append(u"反控：域外 .md 带 BOM ⇒ 应 rc0（⛔ 报）")
        n_ctrl += 1
        if _quiet_main(["--root", os.path.join(root, "nope"), "--baseline", base])[0] != 3:
            bad.append(u"反控：根不存在 ⇒ 应 rc3（用法错）")
        base2 = os.path.join(root, "base2.json")
        with io.open(base2, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps({
                u"说明": u"st", u"基线之刻": now_stamp(), u"域": list(DEFAULT_EXTS),
                u"面": [{u"面之径": os.path.join(root, "gone"), u"刻": u"x", u"件数": 0,
                        u"印": u"0", u"件": {}}],
            }, ensure_ascii=False))
        n_ctrl += 1
        if _quiet_main(["--baseline", base2])[0] != 4:
            bad.append(u"反控：基线之面缺 ⇒ 应 rc4（⛔ 静默 · ⛔ 读作 rc5）")
        grepo = os.path.join(root, "grepo")
        os.makedirs(grepo)
        subprocess.run(["git", "-C", grepo, "init", "-q"], capture_output=True)
        with io.open(os.path.join(grepo, "clean.py"), "wb") as f:
            f.write(b"a=1\n")
        subprocess.run(["git", "-C", grepo, "add", "-A"], capture_output=True)
        gbase = os.path.join(root, "gbase.json")
        n_ctrl += 1
        if _quiet_main(["--rebase", "--face-git", grepo, "--baseline", gbase])[0] != 0:
            bad.append(u"反控：git 面 rebase ⇒ 应 rc0")
        g_rc, g_out = _quiet_main(["--baseline", gbase])
        n_ctrl += 1
        if g_rc != 0:
            bad.append(u"反控：git 面（无 BOM 之已追 .py）⇒ 应 rc0")
        elif u"git已追" not in g_out:
            bad.append(u"反控：git 面 ⇒ 输出须显其类（git已追）")
        with io.open(os.path.join(grepo, "bad.py"), "wb") as f:
            f.write(BOM + b"b=2\n")
        subprocess.run(["git", "-C", grepo, "add", "-A"], capture_output=True)
        n_ctrl += 1
        if _quiet_main(["--baseline", gbase])[0] != 2:
            bad.append(u"正控：git 面之新已追 BOM ⇒ 应 rc2（报）")
        _quiet_main(["--rebase", "--face-git", grepo, "--baseline", gbase])
        with io.open(os.path.join(grepo, "untracked.py"), "wb") as f:
            f.write(BOM + b"c=3\n")
        n_ctrl += 1
        if _quiet_main(["--baseline", gbase])[0] != 0:
            bad.append(u"反控：⛔ 已追之 BOM（在目录内而不入面）⇒ 应 rc0（⛔ 报）")
        nogit = os.path.join(root, "nogit")
        os.makedirs(nogit)
        gbase2 = os.path.join(root, "gbase2.json")
        with io.open(gbase2, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps({u"说明": u"st", u"基线之刻": now_stamp(),
                                u"域": list(DEFAULT_EXTS),
                                u"面": [{u"类": u"git已追", u"面之径": nogit, u"刻": u"x",
                                        u"件数": 0, u"印": u"0", u"件": {}}]},
                               ensure_ascii=False))
        n_ctrl += 1
        if _quiet_main(["--baseline", gbase2])[0] != 4:
            bad.append(u"反控：git 面之根 ⛔ 为仓 ⇒ 应 rc4（面之缺）")
        empty = os.path.join(root, "empty")
        os.makedirs(empty)
        n_ctrl += 1
        if _quiet_main(["--root", empty, "--baseline", base])[0] != 5:
            bad.append(u"反控：空面 ⇒ 应 rc5")
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print(u"[自证] 正控 %d ／ 反控 %d ⇒ %s" % (len(POS), n_ctrl,
          u"PASS" if not bad else u"FAIL " + u" ／ ".join(bad)))
    return 0 if not bad else 1


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if "--selftest" in argv:
        return selftest()
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--root", action="append", default=[])
    ap.add_argument("--face", action="append", default=[])
    ap.add_argument("--face-git", action="append", default=[])
    ap.add_argument("--ext", action="append", default=[])
    ap.add_argument("--baseline", default=DEFAULT_BASELINE)
    ap.add_argument("--rebase", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args(argv)

    base_path = os.path.abspath(a.baseline)
    exts = tuple(sorted(set(e.lower() if e.startswith(".") else "." + e.lower()
                            for e in (a.ext or DEFAULT_EXTS))))
    base = load_baseline(base_path)

    # ---------------- rebase（唯一写路 · 一改一底）----------------
    if a.rebase:
        fdefs = [{"面之径": os.path.abspath(x), u"类": u"目录"}
                 for x in (a.face or a.root)]
        fdefs += [{"面之径": os.path.abspath(x), u"类": u"git已追"}
                  for x in a.face_git]
        if not fdefs and base:
            fdefs = [{"面之径": os.path.abspath(sec.get(u"面之径") or u""),
                      u"类": sec.get(u"类") or u"目录"}
                     for sec in (base.get(u"面") or [])]
        if not fdefs:
            fdefs = [{"面之径": os.path.abspath(x), u"类": u"目录"}
                     for x in DEFAULT_FACES]
        missing = [f["面之径"] for f in fdefs if not os.path.isdir(f["面之径"])]
        if missing:
            sys.stderr.write(u"⛔ 面不存在（闸没跑）：%s\n" % u" ／ ".join(missing))
            return 3
        stamp = now_stamp()
        sections = []
        for fd in fdefs:
            got = face_scan(fd, exts, a.all)
            if got is None:
                sys.stderr.write(u"⛔ 面不可达（闸没跑）：%s\n" % fd["面之径"])
                return 3
            entries, hmap, dmap, mmap, bad = got
            sections.append({
                u"类": fd[u"类"], u"面之径": fd["面之径"], u"刻": stamp,
                u"件数": len(hmap), u"印": face_seal(hmap), u"件": hmap,
                u"面内件数": entries, u"坏件": len(bad),
            })
        data = {
            u"器": HERE, u"器印": sha16(HERE),
            u"说明": u"scan_bom 之基线（⭐ 分域 · 键＝名 · 唯报净变 · 承 PM 1220 项4 · ⛔ 删）",
            u"基线之刻": stamp, u"域": list(exts),
            u"面": sections, u"件数": sum(s[u"件数"] for s in sections),
        }
        bak = save_baseline(base_path, data)
        out = {u"重写基线": base_path, u"基线存底": bak, u"域": list(exts),
               u"件数": data[u"件数"],
               u"面": [{u"类": s[u"类"], u"面之径": s[u"面之径"], u"件数": s[u"件数"],
                       u"印": s[u"印"]} for s in sections]}
        if a.json:
            print(json.dumps(out, ensure_ascii=False, indent=1))
        else:
            print(u"[rebase] 基线 %s ／ 件 %d ／ 存底 %s" % (base_path, data[u"件数"], bak))
            for s in sections:
                print(u"    面[%s] %s ／ 件 %d ／ 印 %s"
                      % (s[u"类"], s[u"面之径"], s[u"件数"], s[u"印"]))
        return 0

    # ---------------- check（唯读）----------------
    if base is None:
        sys.stderr.write(u"⛔ 基线缺失（闸没跑）：%s ⇒ 先 `--rebase`\n" % base_path)
        return 3

    base_faces = {}
    for sec in (base.get(u"面") or []):
        base_faces[(os.path.abspath(sec.get(u"面之径") or u""),
                    sec.get(u"类") or u"目录")] = sec

    explicit = bool(a.root or a.face_git)
    if explicit:
        fdefs = [{"面之径": os.path.abspath(x), u"类": u"目录"} for x in a.root]
        fdefs += [{"面之径": os.path.abspath(x), u"类": u"git已追"}
                  for x in a.face_git]
        for fd in fdefs:
            if not os.path.isdir(fd["面之径"]):
                sys.stderr.write(u"⛔ 路径不存在（闸没跑）：%s\n" % fd["面之径"])
                return 3
        keys = set((f["面之径"], f[u"类"]) for f in fdefs)
        not_scanned = [u"[%s] %s" % (k[1], k[0]) for k in base_faces if k not in keys]
    else:
        fdefs = [{"面之径": os.path.abspath(sec.get(u"面之径") or u""),
                  u"类": sec.get(u"类") or u"目录"} for sec in (base.get(u"面") or [])]
        not_scanned = []

    entries_total = 0
    hits_all = {}
    bad_all = []
    per = []
    fail = []
    for fd in fdefs:
        got = face_scan(fd, exts, a.all)
        sec = base_faces.get((fd["面之径"], fd[u"类"])) or {}
        bmap = sec.get(u"件") or {}
        if got is None:
            fail.append(u"[%s] %s" % (fd[u"类"], fd["面之径"]))
            per.append({u"类": fd[u"类"], u"面之径": fd["面之径"], u"件数": 0,
                        u"BOM数": 0, u"基线之件数": len(bmap),
                        u"基线之刻": sec.get(u"刻"), u"缺": True,
                        u"新落": [], u"同名而内容变": [], u"净减": [],
                        u"dmap": {}, u"mmap": {}, u"base_map": bmap})
            continue
        entries, hmap, dmap, mmap, bad = got
        entries_total += entries
        bad_all.extend(bad)
        fresh, chg, gone = delta_per_face(hmap, bmap)
        hits_all.update(hmap)
        per.append({u"类": fd[u"类"], u"面之径": fd["面之径"], u"件数": entries,
                    u"BOM数": len(hmap), u"基线之件数": len(bmap),
                    u"基线之刻": sec.get(u"刻"),
                    u"新落": fresh, u"同名而内容变": chg, u"净减": gone,
                    u"dmap": dmap, u"mmap": mmap, u"base_map": bmap})

    if explicit and fail:
        sys.stderr.write(u"⛔ 面不可达（闸没跑）：%s\n" % u" ／ ".join(fail))
        return 3
    miss_face = [] if explicit else fail

    n_fresh = sum(len(x[u"新落"]) for x in per)
    n_chg = sum(len(x[u"同名而内容变"]) for x in per)
    n_gone = sum(len(x[u"净减"]) for x in per)

    if miss_face:
        rc = 4
    elif entries_total == 0:
        rc = 5
    elif bad_all:
        rc = 4
    elif n_fresh or n_gone:
        rc = 2
    else:
        rc = 0

    rep = {
        u"器": HERE, u"器印": sha16(HERE),
        u"面之径逐字": [u"[%s] %s" % (f[u"类"], f["面之径"]) for f in fdefs],
        u"取数刻": now_stamp(),
        u"域定义": u"首三字节 ＝ EF BB BF ∧ 后缀属本闸之族（%s）" % u" ".join(exts),
        u"同族": list(exts),
        u"件数": entries_total, u"BOM数": len(hits_all),
        u"基线之径": base_path, u"基线之刻": base.get(u"基线之刻"),
        u"分母面": [{k: v for k, v in x.items()
                     if k not in (u"dmap", u"mmap", u"base_map")} for x in per],
        u"面之缺": miss_face, u"未扫之基线面": not_scanned, u"坏件": bad_all,
        u"净增": {u"新落": n_fresh, u"合": n_fresh},
        u"同名而内容变_信息_不入净增": n_chg,
        u"净减": n_gone, u"rc": rc,
    }

    if a.json:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
    else:
        print(u"器: %s" % rep[u"器"])
        print(u"器印: %s" % rep[u"器印"])
        print(u"面之径逐字: %s"
              % u" ／ ".join(u"[%s] %s" % (f[u"类"], f["面之径"]) for f in fdefs))
        print(u"取数刻: %s" % rep[u"取数刻"])
        print(u"域定义: %s" % rep[u"域定义"])
        print(u"基线: %s ／ 刻 %s" % (base_path, rep[u"基线之刻"]))
        for x in per:
            if x.get(u"缺"):
                print(u"—— 面[%s] %s ⇒ ⛔ 面之缺（未跑全）" % (x[u"类"], x[u"面之径"]))
                continue
            print(u"—— 面[%s] %s ／ 件 %d ／ BOM %d ／ 基线之件数 %d（刻 %s）"
                  % (x[u"类"], x[u"面之径"], x[u"件数"], x[u"BOM数"],
                     x[u"基线之件数"], x[u"基线之刻"]))
            for k in x[u"新落"]:
                print(u"  ⚠ 新落（BOM 之件：基线无 · 今 BOM）%s（mtime %s）"
                      % (x[u"dmap"].get(k, k), mt_str(x[u"mmap"].get(k, 0.0))))
            for k in x[u"同名而内容变"]:
                print(u"  · 同名而内容变 %s（基线印 %s ⇒ 今 %s · 信息 · ⛔ 入净增）"
                      % (x[u"dmap"].get(k, k), x[u"base_map"].get(k), x[u"mmap"].get(k) and sha16(x[u"dmap"].get(k))))
            for k in x[u"净减"]:
                print(u"  ⚠ 净减（BOM 之件：基线有 · 今不 BOM · ⛔ 谓件已删）%s" % k)
        print(u"—— 件 %d ／ BOM %d ／ 净增（BOM 之件）%d ／ 同名而内容变 %d（信息）／ 净减（BOM 之件）%d ／ 面之缺 %d ／ 坏件 %d"
              % (entries_total, len(hits_all), n_fresh, n_chg, n_gone,
                 len(miss_face), len(bad_all)))
        for f in miss_face:
            print(u"  ⚠ 面之缺（未跑全）%s" % f)
        for f in not_scanned:
            print(u"  ⚠ 未扫之基线面（`--root` 覆盖）：%s" % f)
        for b in bad_all:
            print(u"  ⚠ 坏件 %s: %s" % (b["path"], b["err"]))
        print(u"rc: %d ＝ %s" % (rc, RC_MEAN.get(rc, u"?")))
    return rc


if __name__ == "__main__":
    sys.exit(main())
