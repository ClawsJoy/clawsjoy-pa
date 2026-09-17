# -*- coding: utf-8 -*-
"""并发修复测试: write_vault_note 原子独占创建 — 同标题多线程零覆盖"""
import sys
import threading

sys.path.insert(0, ".")
from core.gateway import precision_inject as pi


def test_same_title_10_threads_no_overwrite(tmp_path, monkeypatch):
    """10 线程同标题并发 → 10 个唯一文件, 每文件含各自标记(零覆盖)"""
    monkeypatch.setattr(pi, "_obsidian_cfg", lambda: {"enabled": True})
    monkeypatch.setattr(pi, "_vault_path", lambda: str(tmp_path))
    pi._NOTE_WRITE_LOCK = None
    results = {}
    errs = []

    def w(i):
        try:
            p = pi.write_vault_note("同题并发", folder="dir", content="并发正文第 %d 份标记 TOKEN%d 足够长" % (i, i), tags=["t"])
            results[i] = p
        except Exception as exc:
            errs.append((i, str(exc)))

    ts = [threading.Thread(target=w, args=(i,)) for i in range(10)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert not errs, errs
    paths = list(results.values())
    assert len(set(paths)) == 10, "应 10 个唯一文件: %s" % sorted(paths)
    for i, p in results.items():
        txt = open(p, encoding="utf-8").read()
        assert ("TOKEN%d" % i) in txt, "文件 %s 应含线程 %d 标记(被覆盖?)" % (p, i)


def test_sequential_dup_suffix_and_append(tmp_path, monkeypatch):
    """语义保持: 重名 → -2; append → 追加同文件"""
    monkeypatch.setattr(pi, "_obsidian_cfg", lambda: {"enabled": True})
    monkeypatch.setattr(pi, "_vault_path", lambda: str(tmp_path))
    pi._NOTE_WRITE_LOCK = None
    a = pi.write_vault_note("顺序重名", folder="d", content="第一次正文内容足够长超过阈值", tags=["t"])
    b = pi.write_vault_note("顺序重名", folder="d", content="第二次正文内容足够长超过阈值", tags=["t"])
    assert b.endswith("-2.md") and a != b, (a, b)
    c = pi.write_vault_note("顺序重名", folder="d", content="追加片段正文足够长以通过阈值检查", tags=["t"], append=True)
    assert c == a, "append 应续写原名文件"
    assert "追加片段正文足够长以通过阈值检查" in open(a, encoding="utf-8").read()
