# -*- coding: utf-8 -*-
u"""台账存底轮转（一次性 · 承 PM 令 `1971` ／ CEO 席 `1968` 之裁）。

对象：`内容工坊/02_协作/信通/投递台账.csv.before_*` —— `落台账_行.py` 之 append-only **救命索**
（其唯**写**：`bak = csv_path + ".before_" + pre` ⇒ 全库无程序**读**之 · 一手核）。
裁：**⛔ 混入常规归仓 ／ 清减** ⇒ 另立 `_备份轮转` ∧ **留最近 20 枚** ⇒ 余 **先压归档 ⇒ 回读校验 ⇒ 清**。

铁序（承清减之律）：`dry` ⇒ `archive`（压归档 ＋ 回读校验 ＋ 逐件清单）⇒ `purge`（复验 ＋ 清）
    ⇒ 备路 `restore`（**可撤回**：自归档复原件 · 唯补不在者 · ⛔ 覆）。
    ⛔ 校验不过 ⇒ **整批回滚**（⛔ 清一件）｜⛔ 删「无归档」之件｜**唯移 ＋ 归档**。
    ⭐ 清之二闸：⒜ 归档内该件之**内容 sha16** 必 ＝ 记（**读内容** · ⛔ 唯信 CRC）⒝ 盘上该件 sha16 必 ＝ 记
    （变 ⇒ 缓）⇒ 二者皆过 ⇒ 方 `os.remove`。
    ⭐ 三判：`成`（已撤）／ `缓`（不合 ⇒ **⛔ 撤**）／ `已不在`（前批已撤 ⇒ ⛔ 计为败 —— 幂等复跑之常形）。
    ⛔ 只读源（唯 `purge` 一步动原盘 · 唯 `restore` 一步补原盘）｜⛔ 关窗 ／ ⛔ 杀进程 ／ ⛔ 触他域。

用法：
  python -X utf8 -B scripts\\dev\\备份轮转_1971.py --stage dry
  python -X utf8 -B scripts\\dev\\备份轮转_1971.py --stage archive --go
  python -X utf8 -B scripts\\dev\\备份轮转_1971.py --stage purge --go
  python -X utf8 -B scripts\\dev\\备份轮转_1971.py --stage restore --go [--only <件名>]
  python -X utf8 -B scripts\\dev\\备份轮转_1971.py --stage read [--json]      # 只读读数（夜办之证物）
  （`--pattern` 可多次 · 默认**二式**：`.before_*` ＋ `.bak_*` ⇒ 一处定形 · 承 PM `1992 §二.3`）
  python -X utf8 -B scripts\\dev\\备份轮转_1971.py --stage repl [--json]      # 主册复现测试（唯一存底之正尺）
  python -X utf8 -B scripts\\dev\\备份轮转_1971.py --self-test
"""
import argparse
import csv
import fnmatch
import hashlib
import io
import json
import os
import shutil
import sys
import time
import zipfile

VAULT = r"D:\Obsidian\ClawsJoy\ClawsJoy"
DEF_DIR = os.path.join(VAULT, u"内容工坊", u"02_协作", u"信通")
DEF_PAT = u"投递台账.csv.before_*"          # ⚠ 旧形（单式 · 兼容）
DEF_PATS = (u"投递台账.csv.before_*", u"投递台账.csv.bak_*")   # ⭐ 二式一器（承 PM `1992 §二.3` 之裁：同 stem ＝ 同族）
DEF_KEEP = 20
DEF_ARCH = r"D:\paseo-workspace\_仓\_备份轮转"
TAG = u"投递台账存底"
DEF_MAIN = u"投递台账.csv"        # 主册（`repl` 之基准 · 承 CEO 席 `1983 §二` 之裁）


def sha256_file(p):
    h = hashlib.sha256()
    with io.open(p, "rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def sha16(p):
    return sha256_file(p)[:16]


def _pats(pat):
    u"""⇒ 归一为元组（`str` ⇒ 单元素）—— ⭐ **二式一器**（承 PM `1992 §二.3`）。"""
    return (pat,) if isinstance(pat, str) else tuple(pat)


def family(d, pat):
    u"""⇒ 该族之件（按 mtime 降序 · 同刻以名定序）。⛔ 收伴生（`.sha256`）。"""
    rows = []
    for n in sorted(os.listdir(d)):
        if not any(fnmatch.fnmatch(n, p) for p in _pats(pat)) or n.endswith(u".sha256"):
            continue
        p = os.path.join(d, n)
        if not os.path.isfile(p):
            continue
        st = os.stat(p)
        rows.append({"n": n, "p": p, "size": st.st_size, "mtime": st.st_mtime})
    rows.sort(key=lambda r: (-r["mtime"], r["n"]))
    return rows


def select(rows, keep):
    u"""⇒ (留, 转)：留 ＝ 最近 `keep` 枚（按 mtime）；转 ＝ 余。"""
    return rows[:keep], rows[keep:]


def batch_paths(arch, day):
    u"""⇒ (序, zip, 清单, 待清表)：**轮次自增**（⛔ 同名覆盖 —— 清单之「原径 → 归档处」映射 ＝ 撤回之正据）。"""
    seq = 1
    while True:
        zp = os.path.join(arch, u"%s_%s_%02d.zip" % (TAG, day, seq))
        mp = os.path.join(arch, u"_清单_%s_%s_%02d.txt" % (TAG, day, seq))
        sp = os.path.join(arch, u"_待清_%s_%s_%02d.json" % (TAG, day, seq))
        if not (os.path.exists(zp) or os.path.exists(mp) or os.path.exists(sp)):
            return seq, zp, mp, sp
        seq += 1


def verify_zip(zp, items):
    u"""⇒ 不合之列（空 ＝ 过）：件数 ＋ 逐件尺 ＋ 逐件 sha16（**读内容**）。"""
    bad = []
    with zipfile.ZipFile(zp) as z:
        names = set(i.filename for i in z.infolist())
        if len(names) != len(items):
            bad.append(u"件数 %d ≠ %d" % (len(names), len(items)))
        for it in items:
            if it["n"] not in names:
                bad.append(u"%s 缺" % it["n"])
                continue
            b = z.read(it["n"])
            if len(b) != it["size"]:
                bad.append(u"%s 尺 %d ≠ %d" % (it["n"], len(b), it["size"]))
            elif hashlib.sha256(b).hexdigest()[:16] != it["sha16"]:
                bad.append(u"%s sha 不合" % it["n"])
    return bad


def latest_stage(arch, tag, day):
    u"""⇒ 本(日)最新一轮待清表之径（无 ⇒ None）。"""
    hits = []
    for n in (os.listdir(arch) if os.path.isdir(arch) else []):
        if n.startswith(u"_待清_%s_%s_" % (tag, day)) and n.endswith(u".json"):
            hits.append(n)
    return os.path.join(arch, sorted(hits)[-1]) if hits else None


def last_rotation(hist):
    u"""⇒ 史之末行（上次轮转之记 · 无 ⇒ None）。"""
    try:
        ls = [x for x in io.open(hist, encoding="utf-8").read().splitlines() if x.strip()]
        return json.loads(ls[-1]) if ls else None
    except Exception:
        return None


def read_report(d, pat, keep, arch, hist=None, now=None):
    u"""⭐ **只读**读数（承 PM `1981 §二`）：族之枚数 ＋ 尺 ＋ 拟转 ＋ **刻** ＋ 上次轮转之记。

    ⚠ 三守：⒜ **只读**（⛔ 写族 ／ ⛔ 触他径）⒝ 其数**带刻**（一刻之读 · 族为活）
        ⒞ ⛔ 以「今数」充「**率**」（率须书**观测窗** ＋ 其**形**：匀速 ∨ `burst`）。
    """
    rows = family(d, pat)
    k, r = select(rows, keep)
    ts = lambda t: time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t))
    tb = sum(x["size"] for x in rows)
    rb = sum(x["size"] for x in r)
    return {
        "at": ts(now if now else time.time()),
        "dir": d, "pattern": pat, "keep": keep,
        "n": len(rows), "bytes": tb, "mib": round(tb / 1048576.0, 1),
        "n_rot": len(r), "bytes_rot": rb, "mib_rot": round(rb / 1048576.0, 1),
        "oldest": ts(rows[-1]["mtime"]) if rows else None,
        "newest": ts(rows[0]["mtime"]) if rows else None,
        "rot_newest": ts(r[0]["mtime"]) if r else None,
        "last": last_rotation(hist if hist else os.path.join(arch, u"_备录.jsonl")),
    }


def do_archive(rot, arch, day, tag):
    u"""压归档 ＋ 回读校验 ＋ 清单 ＋ 待清表。⇒ (rc, zip, 不合之列 · rc=4 即拒 ／ rc=3 无件)。"""
    if not rot:
        return 3, None, []
    os.makedirs(arch, exist_ok=True)
    seq, zp, mp, sp = batch_paths(arch, day)
    items = []
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for r in rot:
            b = io.open(r["p"], "rb").read()
            z.writestr(r["n"], b)
            items.append({"n": r["n"], "p": r["p"], "size": r["size"],
                          "sha16": hashlib.sha256(b).hexdigest()[:16], "arc": os.path.basename(zp)})
    bad = verify_zip(zp, items)
    if bad:
        return 4, zp, bad
    zsha = sha16(zp)
    with io.open(mp, "w", encoding="utf-8", newline="\n") as f:
        f.write(u"# 备份轮转清单（可撤回）｜ %s ｜ 轮次 %02d ｜ 族 %s ｜ 留 %d（唯转其外）\n"
                % (time.strftime("%Y-%m-%dT%H:%M:%S"), seq, tag, DEF_KEEP))
        f.write(u"# 归档包 %s ｜ %.1f MB ｜ sha16 %s ｜ 件 %d\n"
                % (os.path.basename(zp), os.path.getsize(zp) / 1048576.0, zsha, len(items)))
        f.write(u"# 件名\t尺B\tsha16\t归档包\t原径\n")
        for it in items:
            f.write(u"%s\t%d\t%s\t%s\t%s\n" % (it["n"], it["size"], it["sha16"], it["arc"], it["p"]))
    json.dump({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "seq": seq, "zip": zp,
               "zip_sha16": zsha, "count": len(items), "items": items},
              io.open(sp, "w", encoding="utf-8"), ensure_ascii=False)
    return 0, zp, []


def do_purge(stg, hist=None, limit=0):
    u"""二闸复验 ⇒ 清。⇒ (成, 缓, 已不在)。

    ⒜ 归档内该件内容 sha16 ＝ 记（**读内容** · ⛔ 唯信 CRC）⒝ 盘上该件 sha16 ＝ 记 ⇒ 皆过 ⇒ 撤。
    ⭐ `已不在` ＝ 前批已撤（幂等复跑之常形 · ⛔ 计为败 —— 归档仍在 ⇒ 无损）。
    """
    doc = json.loads(io.open(stg, encoding="utf-8").read())
    zp = doc["zip"]
    if not os.path.exists(zp):
        return [], [(u"<批>", u"归档包不在 ⇒ 拒清（整批）")], []
    todo = doc["items"][:limit] if limit else doc["items"]
    done, fail, gone = [], [], []
    with zipfile.ZipFile(zp) as z:
        for it in todo:
            p = it["p"]
            try:
                b = z.read(it["n"])
            except KeyError:
                fail.append((it["n"], u"归档缺 ⇒ 缓")); continue
            except zipfile.BadZipFile:
                fail.append((it["n"], u"归档条目 CRC 不合 ⇒ 缓")); continue
            if hashlib.sha256(b).hexdigest()[:16] != it["sha16"]:
                fail.append((it["n"], u"归档内容不合 ⇒ 缓")); continue
            if not os.path.exists(p):
                gone.append(it); continue
            try:
                if sha16(p) != it["sha16"]:
                    fail.append((it["n"], u"盘上变（sha 不合）⇒ 缓")); continue
            except Exception as e:
                fail.append((it["n"], u"盘复验败:%s" % type(e).__name__)); continue
            try:
                os.remove(p)
                done.append(it)
            except Exception as e:
                fail.append((it["n"], u"%s: %s" % (type(e).__name__, str(e).split(u"\n")[0][:80])))
    if hist:
        try:
            with io.open(hist, "a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "stage": u"purge",
                                    "batch": os.path.basename(stg), "zip": zp,
                                    "done": len(done), "fail": len(fail), "gone": len(gone),
                                    "bytes": sum(x["size"] for x in done)}, ensure_ascii=False) + u"\n")
        except Exception:
            pass
    return done, fail, gone


def do_restore(stg, only=None, limit=0):
    u"""**可撤回**：自归档复原件（唯补盘上不在者 · ⛔ 覆 ／ ⛔ 删）。⇒ (复, 跳, 败)。

    ⭐ 写后即校验（盘上 sha16 ＝ 归档之记）⇒ ⛔ 静默成。
    """
    doc = json.loads(io.open(stg, encoding="utf-8").read())
    zp = doc["zip"]
    if not os.path.exists(zp):
        return [], [], [(u"<批>", u"归档包不在 ⇒ 无从复")]
    todo = [x for x in doc["items"] if (not only or x["n"] in only)]
    if limit:
        todo = todo[:limit]
    back, skip, fail = [], [], []
    with zipfile.ZipFile(zp) as z:
        for it in todo:
            p = it["p"]
            if os.path.exists(p):
                skip.append(it); continue
            try:
                b = z.read(it["n"])
            except KeyError:
                fail.append((it["n"], u"归档缺")); continue
            if hashlib.sha256(b).hexdigest()[:16] != it["sha16"]:
                fail.append((it["n"], u"归档内容不合")); continue
            try:
                d = os.path.dirname(p)
                if d and not os.path.isdir(d):
                    os.makedirs(d)
                with io.open(p, "wb") as f:
                    f.write(b)
                if sha16(p) != it["sha16"]:
                    fail.append((it["n"], u"写后 sha 不合")); continue
                back.append(it)
            except Exception as e:
                fail.append((it["n"], u"%s: %s" % (type(e).__name__, str(e).split(u"\n")[0][:60])))
    return back, skip, fail


def _id_key(s):
    u"""⇒ 号之**归一**（承 PM `1992 §二.4` 之自咬：`77 ≠ 077` ⇒ 假「真唯一」）。

    数字号 ⇒ 去前导零（`int`）｜非数字 ⇒ 原字（`strip`）｜空 ⇒ None。
    """
    if not s:
        return None
    t = s.strip()
    return str(int(t)) if t.isdigit() else t


def _csv_id(line):
    u"""⇒ 该行之首栏（序号）。解析败 ⇒ None。"""
    try:
        r = next(csv.reader([line]))
        return r[0].strip() if r else None
    except Exception:
        return None


def replica_test(d, pat=DEF_PATS, main_name=None, now=None):
    u"""⭐⭐ **主册复现测试**（承 CEO 席 `1983 §二` 之裁）—— 判 append-only 族之「唯一存底」。

    尺（**一处出** · 由 CEO 席裁 · ⛔ 沿「族内尺差 ≥10%」之代理）：
      ①（前缀）该快照**逐字节**为主册之前缀 ⇒ **⛔ 唯一存底**（截取即复得）；
      ②（行集）非前缀 ⇒ 逐行核（**剥 BOM**）：其行皆在主册 ⇒ **⛔ 唯一存底**；
        异行之序号皆在主册 ⇒ **⛔ 唯一存底**（同号之早稿）；
        ⚠ **表头之号（`序号`）⛔ 计「数据行」**（列后加（如 `时点`）⇒ 旧快照表头必异 ⇒ 假阳；计入 `hdr_only`）；
        若有行之序号**不在主册** ⇒ ⭐ **真·唯一存底**。
    由：CEO 一手（`1983 §一.3`）—— 该族逐件测 ⇒ 真·唯一存底 `0`；其「甲」标系**尺之差**
        （假阳之根 ＝ 主册首栏带 `\\ufeff`（BOM）⇒ 逐字节必异）。
    ⚠ **只读**（⛔ 写族 ／ ⛔ 触他径）｜rc：`0` ＝ 无真唯一（合裁）／ `7` ＝ 有真唯一（须护）。
    """
    rows = family(d, pat)
    mp = os.path.join(d, main_name or DEF_MAIN)
    at = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(now if now else time.time()))
    if not os.path.isfile(mp):
        return {"at": at, "dir": d, "err": u"主册不在：%s" % mp, "real_unique": -1}
    mb = io.open(mp, "rb").read()
    mlines = [x.rstrip(u"\r") for x in mb.decode("utf-8-sig", errors="replace").splitlines()]
    mset = set(mlines)
    hid = _id_key(_csv_id(mlines[0])) if mlines else None   # ⭐ 主册表头之号（`序号`）⇒ 快照之表头 ⛔ 计「数据行」
    mids = set(x for x in (_id_key(_csv_id(y)) for y in mlines[1:]) if x)
    n = {"prefix": 0, "rowset": 0, "early": 0, "real": 0, "bom": 0, "hdr": 0}
    det = []
    for r in rows:
        b = io.open(r["p"], "rb").read()
        bom = b[:3] == b"\xef\xbb\xbf"
        if mb.startswith(b):
            v, ev = u"⛔ 前缀", u"逐字节 ＝ 主册前 %d B" % len(b)
            n["prefix"] += 1
        else:
            ls = [x.rstrip(u"\r") for x in b.decode("utf-8-sig", errors="replace").splitlines()]
            diff = [x for x in ls if x not in mset]
            if not diff:
                v, ev = u"⛔ 行集", u"行皆在主册（剥 BOM）"
                n["rowset"] += 1
                if bom:
                    n["bom"] += 1
            else:
                nh = sum(1 for x in diff if hid and _id_key(_csv_id(x)) == hid)
                bad = [i for i in (_id_key(_csv_id(x)) for x in diff) if i and i != hid and i not in mids]
                tail = u"（含表头异 %d 行 · ⛔ 计）" % nh if nh else u""
                if bad:
                    v, ev = u"⭐ 真唯一存底", u"异 %d 行%s · 序号不在主册：%s" % (len(diff), tail, u"、".join(bad[:5]))
                    n["real"] += 1
                else:
                    v, ev = u"⛔ 同号早稿", u"异 %d 行%s · 其序号皆在主册" % (len(diff), tail)
                    n["early"] += 1
                n["hdr"] += nh
        det.append({"n": r["n"], "size": r["size"], "bom": bom, "verdict": v, "evidence": ev})
    return {"at": at, "dir": d, "main": mp, "main_bytes": len(mb), "main_lines": len(mlines),
            "pattern": u" ∨ ".join(_pats(pat)), "n": len(rows), "bytes": sum(x["size"] for x in rows),
            "prefix": n["prefix"], "rowset": n["rowset"], "early": n["early"],
            "bom_only": n["bom"], "real_unique": n["real"], "hdr_only": n["hdr"], "det": det}


def report(rows, keep, title):
    k, r = select(rows, keep)
    tb = sum(x["size"] for x in rows)
    kb = sum(x["size"] for x in k)
    rb = sum(x["size"] for x in r)
    print(u"%s：族 %d 枚 ／ %.1f MiB" % (title, len(rows), tb / 1048576.0))
    print(u"   留（最近 %d）%d 枚 ／ %.1f MiB ｜ 转 %d 枚 ／ %.1f MiB"
          % (keep, len(k), kb / 1048576.0, len(r), rb / 1048576.0))
    ts = lambda t: time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t))
    if k:
        print(u"   界：留之最旧 %s（%s）" % (k[-1]["n"], ts(k[-1]["mtime"])))
    if r:
        print(u"   界：转之最新 %s（%s）｜转之最旧 %s（%s）"
              % (r[0]["n"], ts(r[0]["mtime"]), r[-1]["n"], ts(r[-1]["mtime"])))
    return k, r


def _fixture(root, n, extra=False):
    src = os.path.join(root, u"src")
    os.makedirs(src, exist_ok=True)
    for i in range(n):
        p = os.path.join(src, u"投递台账.csv.before_%016d" % i)
        io.open(p, "wb").write((u"v%d\n" % i).encode("utf-8") * (i + 1))
        os.utime(p, (1000 + i * 10, 1000 + i * 10))
    if extra:
        for nm in (u"投递台账.csv", u"投递台账.csv.sha256", u"投递台账.csv.journal",
                   u"投递台账.csv.bak_20260920_210202",
                   u"投递台账.csv.before_0000000000000003.sha256"):
            io.open(os.path.join(src, nm), "wb").write(b"x\n")
    return src


def self_test():
    u"""自证：留 N 之界 ／ 命名之域 ／ 归档回读 ／ 篡改必咬 ／ 盘变必缓 ／ 幂等复跑 ／ 可撤回。"""
    ck = []
    def c(nm, cond):
        ck.append((nm, bool(cond)))
    root = os.path.join(u"D:\\pa_tmp", u"bt_1971_%d" % os.getpid())
    if os.path.isdir(root):
        shutil.rmtree(root)
    try:
        src = _fixture(root, 7, extra=True)
        rows = family(src, u"投递台账.csv.before_*")
        c(u"族数 7（他件 ＋ 伴生 ⛔ 收）", len(rows) == 7)
        c(u"降序（新在前）", rows[0]["n"].endswith(u"0000000000000006"))
        k, r = select(rows, 3)
        c(u"留 3 ／ 转 4", len(k) == 3 and len(r) == 4)
        c(u"留者皆新于转者", min(x["mtime"] for x in k) > max(x["mtime"] for x in r))

        arch = os.path.join(root, u"arch")
        rc, zp, bad = do_archive(r, arch, u"20990101", TAG)
        c(u"归档 rc=0", rc == 0 and os.path.exists(zp))
        c(u"回读无不合", bad == [])
        with zipfile.ZipFile(zp) as z:
            c(u"归档含 4 件", len(z.infolist()) == 4)
        c(u"清单在盘", os.path.exists(os.path.join(arch, u"_清单_%s_20990101_01.txt" % TAG)))
        stg = os.path.join(arch, u"_待清_%s_20990101_01.json" % TAG)
        c(u"待清表在盘", os.path.exists(stg))
        c(u"轮次取最新", latest_stage(arch, TAG, u"20990101") == stg)
        hist = os.path.join(root, u"_备录.jsonl")

        # ⒜ 篡改归档内容 ⇒ 该件必缓（且盘上仍在）；余三件撤
        doc = json.loads(io.open(stg, encoding="utf-8").read())
        bad_n = doc["items"][0]["n"]
        with zipfile.ZipFile(zp, "a") as z:
            z.writestr(bad_n, b"TAMPER")
        done, fail, gone = do_purge(stg, hist)
        c(u"归档内容改 ⇒ 该件缓", len(fail) == 1 and fail[0][0] == bad_n)
        c(u"缓者盘上仍在", os.path.exists(doc["items"][0]["p"]))
        c(u"余三件已撤", len(done) == 3 and not gone)
        c(u"盘上余 4（3 留 ＋ 1 缓）", len(family(src, u"投递台账.csv.before_*")) == 4)

        # ⒝ 幂等复跑 ⇒ 余三件计「已不在」（⛔ 计为败）＋ 坏件仍缓
        done, fail, gone = do_purge(stg, hist)
        c(u"复跑：成 0 ／ 缓 1 ／ 已不在 3", len(done) == 0 and len(fail) == 1 and len(gone) == 3)

        # ⒞ 撤回：唯补不在者（坏件在盘 ⇒ 跳）⇒ 净增 3（4 → 7）
        back, skip, rfail = do_restore(stg)
        c(u"撤回：复 3 ／ 跳 1 ／ 败 0", len(back) == 3 and len(skip) == 1 and not rfail)
        c(u"撤回后盘上 7", len(family(src, u"投递台账.csv.before_*")) == 7)
        c(u"复者内容 ＝ 归档之记", all(sha16(x["p"]) == x["sha16"] for x in back))

        # ⒟ 复原归档 ⇒ 再撤 ⇒ 再清（闭环）
        with zipfile.ZipFile(zp, "a") as z:
            z.writestr(bad_n, io.open(doc["items"][0]["p"], "rb").read())
        done, fail, gone = do_purge(stg, hist)
        c(u"复原后四件皆撤", len(done) == 4 and not fail)
        c(u"盘上余 3", len(family(src, u"投递台账.csv.before_*")) == 3)

        # ⒠ 盘上变 ⇒ 缓（回读之旧态 ≠ 盘上今态）
        root2 = os.path.join(root, u"b")
        src2 = _fixture(root2, 3)
        _k2, r2 = select(family(src2, u"投递台账.csv.before_*"), 1)
        arch2 = os.path.join(root2, u"arch2")
        rc2, zp2, _ = do_archive(r2, arch2, u"20990101", TAG)
        stg2 = latest_stage(arch2, TAG, u"20990101")
        with io.open(r2[0]["p"], "ab") as f:
            f.write(b"X")
        done, fail, gone = do_purge(stg2, hist)
        c(u"盘变者缓 ／ 余者撤", len(fail) == 1 and fail[0][0] == r2[0]["n"] and len(done) == 1)
        c(u"变者仍在", os.path.exists(r2[0]["p"]))

        # ⒡ 归档包不在 ⇒ 整批拒（清 ／ 撤 皆拒）
        os.remove(zp2)
        done, fail, gone = do_purge(stg2, hist)
        c(u"归档不在 ⇒ 清整批拒", len(done) == 0 and len(fail) == 1 and not gone)
        back, skip, rfail = do_restore(stg2)
        c(u"归档不在 ⇒ 撤亦拒", len(back) == 0 and len(rfail) == 1)
        # ⒢ 读数齿 ⇒ **只读**（跑前后之盘上快照须同）＋ 带刻 ＋ 上次轮转可见
        snap0 = [(x["n"], x["size"], x["mtime"]) for x in family(src, u"投递台账.csv.before_*")]
        rr = read_report(src, u"投递台账.csv.before_*", 3, arch, hist=hist, now=1700000000)
        c(u"读数：枚数 3 ／ 拟转 0（族 ＝ keep）", rr["n"] == 3 and rr["n_rot"] == 0)
        c(u"读数：带刻（一刻之读）", rr["at"] == u"2023-11-15T06:13:20")
        c(u"读数：上次轮转取自史", bool(rr["last"]) and rr["last"]["batch"].startswith(u"_待清_"))
        snap1 = [(x["n"], x["size"], x["mtime"]) for x in family(src, u"投递台账.csv.before_*")]
        # ⒣ 主册复现测试（承 CEO 席 `1983 §二`）：前缀 ／ 行集 ∧ 同号早稿 ／ 真唯一 ／ BOM 假阳
        root3 = os.path.join(root, u"c")
        os.makedirs(root3, exist_ok=True)
        ls3 = [u"序号,日期,发件,收件", u"001,a,b,c", u"002,d,e,f"]
        t3 = u"\n".join(ls3) + u"\n"
        io.open(os.path.join(root3, u"投递台账.csv"), "wb").write(t3.encode("utf-8"))
        def _w3(nm, sv):
            io.open(os.path.join(root3, nm), "wb").write(sv.encode("utf-8"))
        _w3(u"投递台账.csv.before_000000000000000a", u"\n".join(ls3[:2]) + u"\n")
        _w3(u"投递台账.csv.before_000000000000000b", ls3[0] + u"\n001,a,b,c\n002,d,ZZZ,f\n")
        _w3(u"投递台账.csv.before_000000000000000c", ls3[0] + u"\n001,a,b,c\n003,x,y,z\n")
        io.open(os.path.join(root3, u"投递台账.csv.before_000000000000000d"), "wb").write(
            b"\xef\xbb\xbf" + t3.encode("utf-8"))
        rp = replica_test(root3, u"投递台账.csv.before_*", now=1700000000)
        c(u"复现：族 4 ／ 真唯一 1", rp["n"] == 4 and rp["real_unique"] == 1)
        c(u"复现：前缀 1 ／ 行集 1 ／ 早稿 1", rp["prefix"] == 1 and rp["rowset"] == 1 and rp["early"] == 1)
        c(u"复现：BOM 假阳 1", rp["bom_only"] == 1)
        c(u"复现：只读（盘上不动）", len(family(root3, u"投递台账.csv.before_*")) == 4)
        # ⒤ 号形归一 ＋ 正控 ＋ 二式一器（承 PM `1992 §二.3`／`§二.4`／`§三`）
        root4 = os.path.join(root, u"d")
        os.makedirs(root4, exist_ok=True)
        ml4 = [u"序号,日期", u"001,a", u"077,b"]
        io.open(os.path.join(root4, u"投递台账.csv"), "wb").write(
            (u"\n".join(ml4) + u"\n").encode("utf-8"))
        def _w4(nm, sv):
            io.open(os.path.join(root4, nm), "wb").write(sv.encode("utf-8"))
        _w4(u"投递台账.csv.before_000000000000000e", ml4[0] + u"\n001,a\n")                     # 前缀
        _w4(u"投递台账.csv.before_000000000000000f", ml4[0] + u"\n001,a\n77,b\n")              # 号形之差（归一 ⇒ 早稿）
        _w4(u"投递台账.csv.before_0000000000000010", ml4[0] + u"\n001,a\n077,b\n断行无序号\n")   # 误写态之形 ⇒ 真唯一
        rp4 = replica_test(root4, u"投递台账.csv.before_*", now=1700000000)
        c(u"归一二验：号形之差（77 vs 077）⇒ 早稿 ⛔ 计真唯一", rp4[u"early"] == 1)
        c(u"正控：断行（无序号）⇒ 真唯一 1（rc 7 须护）", rp4[u"real_unique"] == 1)
        # ␥ 表头异 ⇒ ⛔ 计真唯一（假阳之根 · 承 PM `1992 §三` 之验）
        root5 = os.path.join(root, u"e")
        os.makedirs(root5, exist_ok=True)
        io.open(os.path.join(root5, u"投递台账.csv"), "wb").write((u"\n".join(ml4) + u"\n").encode("utf-8"))
        io.open(os.path.join(root5, u"投递台账.csv.before_0000000000000011"), "wb").write((ml4[0] + u",备注\n001,a\n").encode("utf-8"))
        io.open(os.path.join(root5, u"投递台账.csv.before_0000000000000012"), "wb").write((ml4[0] + u",备注\n001,a\n断行无序号\n").encode("utf-8"))
        rp5 = replica_test(root5, u"投递台账.csv.before_*", now=1700000000)
        c(u"表头异 ⛔ 计真唯一（假阳之根）", rp5[u"real_unique"] == 1 and rp5[u"hdr_only"] == 2 and rp5[u"early"] == 1)
        _w4(u"投递台账.csv.bak_20260925_1318_误写态_x", ml4[0] + u"\n001,a\n077,b\n9,z\n")
        c(u"二式一器：.bak_* 入族 ⇒ 4", len(family(root4, DEF_PATS)) == 4)
        c(u"旧 glob 唯 .before_ ⇒ 3（⛔ 破兼容）", len(family(root4, u"投递台账.csv.before_*")) == 3)
        c(u"读数齿只读（盘上 ⛔ 变）", snap0 == snap1)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    ok = sum(1 for _, v in ck if v)
    for nm, v in ck:
        print(u"   %s %s" % (u"OK " if v else u"FAIL", nm))
    print(u"[自证] %d/%d" % (ok, len(ck)))
    return 0 if ok == len(ck) else 1


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=DEF_DIR)
    ap.add_argument("--pattern", action="append", default=None,
                    help=u"族之 glob（可多次 · 默认二式：`.before_*` ＋ `.bak_*`）")
    ap.add_argument("--keep", type=int, default=DEF_KEEP)
    ap.add_argument("--arch", default=DEF_ARCH)
    ap.add_argument("--stage", default=u"dry",
                    choices=[u"dry", u"archive", u"purge", u"restore", u"read", u"repl"])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--go", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", action="append", default=None, help=u"唯复此件（可多次 · `restore` 用）")
    ap.add_argument("--main", default=DEF_MAIN, help=u"主册之名（`repl` 用）")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    pats = tuple(a.pattern) if a.pattern else DEF_PATS
    if a.self_test:
        return self_test()
    if not os.path.isdir(a.dir):
        print(u"[缺] 件夹不在：%s" % a.dir)
        return 2
    day = time.strftime("%Y%m%d")
    if a.stage == u"repl":
        rr = replica_test(a.dir, pats, a.main)
        if a.json:
            print(json.dumps(rr, ensure_ascii=False))
            return 0 if rr.get("real_unique", -1) == 0 else 7
        if rr.get("real_unique", -1) < 0:
            print(u"[缺] %s" % rr.get("err"))
            return 2
        print(u"[复现] 刻 %s ｜ 主册 %d B ／ %d 行 ｜ 族 %d 枚 ／ %.1f MiB"
              % (rr["at"], rr["main_bytes"], rr["main_lines"], rr["n"], rr["bytes"] / 1048576.0))
        print(u"   前缀 %d ｜ 行集 %d（含 BOM 假阳 %d）｜ 同号早稿 %d ｜ ⭐ 真唯一存底 %d"
              % (rr["prefix"], rr["rowset"], rr["bom_only"], rr["early"], rr["real_unique"]))
        for x in [y for y in rr["det"] if y["verdict"].startswith(u"⭐")][:8]:
            print(u"   ⚠ %s ⇒ %s" % (x["n"], x["evidence"]))
        print(u"   ⚠ 本数系**一刻之读**（族为活）｜⛔ 唯一存底 ＝ 内容别无可替（⛔ 尺差代理）")
        return 0 if rr["real_unique"] == 0 else 7
    if a.stage == u"read":
        rr = read_report(a.dir, pats, a.keep, a.arch)
        if a.json:
            print(json.dumps(rr, ensure_ascii=False))
            return 0
        print(u"[读数] 刻 %s ｜ 族 %d 枚 ／ %.1f MiB ｜ keep %d ⇒ 拟转 %d 枚 ／ %.1f MiB"
              % (rr["at"], rr["n"], rr["mib"], rr["keep"], rr["n_rot"], rr["mib_rot"]))
        print(u"   族之最旧 %s ｜ 族之最新 %s" % (rr["oldest"], rr["newest"]))
        _l = rr["last"]
        print(u"   拟转之最新 %s ｜ 上次轮转 %s"
              % (rr["rot_newest"] or u"（无）",
                 (u"%s ｜ %s ｜ 成 %s ／ 缓 %s ／ 已不在 %s ｜ %.1f MiB"
                  % (_l["at"], _l["batch"], _l["done"], _l["fail"], _l.get("gone"),
                     _l["bytes"] / 1048576.0)) if _l else u"（无）"))
        print(u"   ⚠ 本数系**一刻之读**（族为活）｜⛔ 以此为「率」（率须书**窗** ＋ **形**）")
        return 0
    rows = family(a.dir, pats)
    k, r = report(rows, a.keep, u"[读] %s ／ %s" % (a.dir, u" ∨ ".join(pats)))
    if a.stage == u"dry" or not a.go:
        return 0
    if a.stage == u"archive":
        if not r:
            print(u"[空] 无可转之件"); return 3
        rc, zp, bad = do_archive(r, a.arch, day, TAG)
        if rc == 4:
            print(u"[拒] 回读校验不合 ⇒ ⛔ 清（整批回滚）")
            for x in bad[:8]:
                print(u"   ⚠ %s" % x)
            return 4
        print(u"[归档] %s ｜ %d 件 ／ %.1f MB ⇒ 回读校验 过 ｜ 清单 ＋ 待清表 已落"
              % (zp, len(r), os.path.getsize(zp) / 1048576.0))
        return 0
    stg = latest_stage(a.arch, TAG, day)
    if not stg:
        print(u"[拒] 本日无待清表（须先 --stage archive 且校验过）⇒ ⛔ 办")
        return 5
    if a.stage == u"restore":
        back, skip, rfail = do_restore(stg, set(a.only) if a.only else None, a.limit)
        print(u"[撤回] %s ｜ 复 %d ／ 跳（已在盘）%d ／ 败 %d ｜ %.1f MB"
              % (os.path.basename(stg), len(back), len(skip), len(rfail),
                 sum(x["size"] for x in back) / 1048576.0))
        for x in rfail[:5]:
            print(u"   ⚠ %s ⇒ %s" % x)
        left = family(a.dir, pats)
        print(u"[复量] 族今 %d 枚 ／ %.1f MiB" % (len(left), sum(x["size"] for x in left) / 1048576.0))
        return 0 if not rfail else 6
    t0 = time.time()
    done, fail, gone = do_purge(stg, os.path.join(a.arch, u"_备录.jsonl"), a.limit)
    print(u"[清] %s ｜ 成 %d ／ 缓 %d ／ 已不在 %d ｜ %.1f MB ｜ %.0fs"
          % (os.path.basename(stg), len(done), len(fail), len(gone),
             sum(x["size"] for x in done) / 1048576.0, time.time() - t0))
    for x in fail[:5]:
        print(u"   ⚠ %s ⇒ %s" % x)
    left = family(a.dir, pats)
    print(u"[复量] 族今 %d 枚 ／ %.1f MiB" % (len(left), sum(x["size"] for x in left) / 1048576.0))
    return 0 if not fail else 6


if __name__ == "__main__":
    if sys.stdout is not None:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main(sys.argv[1:]))