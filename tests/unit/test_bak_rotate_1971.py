# -*- coding: utf-8 -*-
u"""齿：台账存底轮转器（承 PM 令 `1971` ／ CEO 席 `1968` 之裁）。

守：留 N 之界（按 mtime）／ 命名之域（他件 ＋ 伴生 ⛔ 收）／ 回读校验（件数 ＋ 尺 ＋ sha16）
    ／ 篡改必咬（归档内容）／ 盘变必缓 ／ 幂等复跑（`已不在` ⛔ 计为败）。
"""
import importlib.util
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = os.path.join(ROOT, u"scripts", u"dev", u"备份轮转_1971.py")


def _load():
    spec = importlib.util.spec_from_file_location(u"bak_rotate_1971", MOD)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_器在且留数为二十():
    assert os.path.exists(MOD), MOD
    m = _load()
    assert m.DEF_KEEP == 20
    assert u"投递台账.csv.before_*" == m.DEF_PAT


def test_自证全过():
    assert _load().self_test() == 0


def test_命名之域与他件皆不收(tmp_path):
    m = _load()
    src = os.path.join(str(tmp_path), u"src")
    os.makedirs(src)
    for i in range(5):
        p = os.path.join(src, u"投递台账.csv.before_%016d" % i)
        with io.open(p, "wb") as f:
            f.write(b"x" * (i + 1))
        os.utime(p, (1000 + i, 1000 + i))
    for nm in (u"投递台账.csv", u"投递台账.csv.sha256", u"投递台账.csv.journal",
               u"投递台账.csv.bak_20260920_210202",
               u"投递台账.csv.before_0000000000000001.sha256"):
        with io.open(os.path.join(src, nm), "wb") as f:
            f.write(b"z")
    rows = m.family(src, m.DEF_PAT)
    assert len(rows) == 5
    assert u"投递台账.csv" not in [r["n"] for r in rows]


def test_留界按时刻(tmp_path):
    m = _load()
    src = os.path.join(str(tmp_path), u"src2")
    os.makedirs(src)
    for i in range(5):
        p = os.path.join(src, u"投递台账.csv.before_%016d" % i)
        with io.open(p, "wb") as f:
            f.write(b"y")
        os.utime(p, (1000 + i, 1000 + i))
    keep, rot = m.select(m.family(src, m.DEF_PAT), 2)
    assert [r["n"][-16:] for r in keep] == [u"0000000000000004", u"0000000000000003"]
    assert len(rot) == 3
    assert min(r["mtime"] for r in keep) > max(r["mtime"] for r in rot)


def test_归档回读与清之三闸(tmp_path):
    m = _load()
    root = str(tmp_path)
    src = m._fixture(os.path.join(root, u"f"), 4)
    _k, rot = m.select(m.family(src, m.DEF_PAT), 1)
    arch = os.path.join(root, u"arch")
    rc, zp, bad = m.do_archive(rot, arch, u"20990101", m.TAG)
    assert rc == 0 and bad == [] and os.path.exists(zp)
    assert len(m.verify_zip(zp, [{"n": r["n"], "p": r["p"], "size": r["size"],
                                  "sha16": m.sha16(r["p"])} for r in rot])) == 0
    stg = m.latest_stage(arch, m.TAG, u"20990101")
    assert stg
    done, fail, gone = m.do_purge(stg)
    assert len(done) == 3 and not fail and not gone
    assert len(m.family(src, m.DEF_PAT)) == 1


def test_盘变必缓且件仍在(tmp_path):
    m = _load()
    root = str(tmp_path)
    src = m._fixture(os.path.join(root, u"g"), 3)
    _k, rot = m.select(m.family(src, m.DEF_PAT), 1)
    arch = os.path.join(root, u"arch2")
    rc, zp, _b = m.do_archive(rot, arch, u"20990101", m.TAG)
    assert rc == 0
    with io.open(rot[0]["p"], "ab") as f:
        f.write(b"CHANGED")
    done, fail, gone = m.do_purge(m.latest_stage(arch, m.TAG, u"20990101"))
    assert len(fail) == 1 and fail[0][0] == rot[0]["n"]
    assert os.path.exists(rot[0]["p"])
    assert len(done) == 1

def test_读数齿四栏与只读(tmp_path):
    u"""读数齿（PM `1981 §二`）：族之枚数 ／ 尺 ／ 拟转 ／ 刻 ／ 上次轮转 —— 且 **只读**。"""
    m = _load()
    root = str(tmp_path)
    src = m._fixture(os.path.join(root, u"r"), 4)
    arch = os.path.join(root, u"archR")
    _k, rot = m.select(m.family(src, m.DEF_PAT), 2)
    rc, zp, _b = m.do_archive(rot, arch, u"20990101", m.TAG)
    assert rc == 0
    hist = os.path.join(arch, u"_备录.jsonl")
    m.do_purge(m.latest_stage(arch, m.TAG, u"20990101"), hist)
    before = sorted(os.listdir(src))
    rr = m.read_report(src, m.DEF_PAT, 2, arch)
    assert rr["n"] == 2 and rr["n_rot"] == 0
    assert rr["at"] and rr["mib"] >= 0 and rr["bytes"] > 0
    assert rr["last"] and rr["last"]["stage"] == u"purge"
    assert sorted(os.listdir(src)) == before


def test_主册复现测试之尺(tmp_path):
    u"""主册复现测试（承 CEO 席 `1983 §二` 之裁）：前缀 ／ 行集（同号早稿）／ 真唯一 ／ BOM 假阳 ／ 只读。"""
    m = _load()
    d = os.path.join(str(tmp_path), u"repl")
    os.makedirs(d)
    ls = [u"序号,日期,发件,收件", u"001,a,b,c", u"002,d,e,f"]
    t = u"\n".join(ls) + u"\n"

    def _w(nm, sv):
        with io.open(os.path.join(d, nm), "wb") as f:
            f.write(sv.encode("utf-8") if isinstance(sv, type(u"")) else sv)

    _w(u"投递台账.csv", t)
    _w(u"投递台账.csv.before_000000000000000a", u"\n".join(ls[:2]) + u"\n")            # ① 前缀
    _w(u"投递台账.csv.before_000000000000000b", ls[0] + u"\n001,a,b,c\n002,d,ZZZ,f\n")  # 同号早稿
    _w(u"投递台账.csv.before_000000000000000c", ls[0] + u"\n001,a,b,c\n003,x,y,z\n")   # 真唯一
    _w(u"投递台账.csv.before_000000000000000d", b"\xef\xbb\xbf" + t.encode("utf-8"))   # BOM 假阳
    before = sorted(os.listdir(d))
    r = m.replica_test(d, m.DEF_PAT)
    assert r[u"n"] == 4 and r[u"real_unique"] == 1
    assert r[u"prefix"] == 1 and r[u"rowset"] == 1 and r[u"early"] == 1 and r[u"bom_only"] == 1
    assert sorted(os.listdir(d)) == before
    assert m.replica_test(d, u"投递台账.csv.before_*")[u"main_lines"] == 3


def test_表头异不计真唯一(tmp_path):
    u"""假阳之根（PM `1992 §三` 之验）：旧快照表头异（列后加 如 `时点`）⇒ ⛔ 计真唯一。"""
    m = _load()
    d = os.path.join(str(tmp_path), u"hdr")
    os.makedirs(d)
    ls = [u"序号,日期,发件,收件", u"001,a,b,c", u"002,d,e,f"]
    t = u"\n".join(ls) + u"\n"

    def _w(nm, sv):
        with io.open(os.path.join(d, nm), "wb") as f:
            f.write(sv.encode("utf-8"))

    _w(u"投递台账.csv", t)
    _w(u"投递台账.csv.before_0000000000000001", ls[0] + u",时点\n001,a,b,c\n")
    _w(u"投递台账.csv.before_0000000000000002", ls[0] + u",时点\n001,a,b,c\n断行无号\n")
    r = m.replica_test(d, m.DEF_PAT)
    assert r[u"n"] == 2 and r[u"real_unique"] == 1 and r[u"hdr_only"] == 2 and r[u"early"] == 1


def test_护真唯一不转(tmp_path):
    u"""护真唯一（PM `1994 §二.2␬`）：`hold` 系**加护**（⛔ 改「留 `keep`」之数）；默空 ⇒ 旧行为。"""
    m = _load()
    src = m._fixture(os.path.join(str(tmp_path), u"h"), 5)
    rows = m.family(src, m.DEF_PATS)
    held = rows[-1][u"n"]
    k0, r0 = m.select(rows, 2)
    assert len(k0) == 2 and len(r0) == 3
    k1, r1 = m.select(rows, 2, (held,))
    assert len(k1) == 3 and len(r1) == 2
    assert held in [x[u"n"] for x in k1]
    assert held not in [x[u"n"] for x in r1]
