# -*- coding: utf-8 -*-
u"""齿：上板器（承 PM 请办 `2019` · 技术总监席 f202f89）。

守：件唯自出包根取（源核）／ 落件后必核面（**2019 之病之正控**：面上「工作树之形」必咬）
    ／ del 唯移 ⛔ 删 ／ 面上多余件必报 ／ 入口错归 3。
"""
import hashlib
import importlib.util
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = os.path.join(ROOT, u"scripts", u"win_pa", u"publish_share.py")


def _load():
    spec = importlib.util.spec_from_file_location(u"publish_share", MOD)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _mk(p, b):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "wb") as f:
        f.write(b)


def _fixture(tmp):
    u"""造「出包根」＋「面」（含一件 del 与一件「工作树之形」之污）。"""
    m = _load()
    root = str(tmp)
    src, dst = os.path.join(root, u"out"), os.path.join(root, u"face")
    body = {u"a/b.txt": b"hello\n", u"web/pa/faces/config.js": b"cfg-committed\n"}
    for rel, b in body.items():
        _mk(m._join(src, rel), b)
    files = [{u"path": rel, u"mode": u"add", u"size": len(b),
              u"sha256": hashlib.sha256(b).hexdigest()} for rel, b in body.items()]
    files.append({u"path": u"old/gone.txt", u"mode": u"del", u"size": 0, u"sha256": u""})
    man = {u"version": u"9.0.11", u"base_version": u"9.0.10", u"channel": u"internal",
           u"built_at": u"2026-10-08T20:00:00+0800", u"files": files}
    _mk(m._join(src, m.MAN), json.dumps(man, ensure_ascii=False).encode(u"utf-8"))
    _mk(m._join(src, u"version.json"), b'{"version":"9.0.11"}')
    _mk(m._join(src, u"ClawsJoyPA-Update.record.json"), b'{"digest":"x"}')
    _mk(m._join(dst, u"old/gone.txt"), b"stale")
    return m, man, src, dst, body


def test_器在且铁律三则():
    assert os.path.exists(MOD), MOD
    m = _load()
    assert u"update_manifest.json" in m.LATE and len(m.LATE) == 3
    assert u"web" in m.PAYLOAD_TOPS


def test_自证全过():
    assert _load().self_test() == 0


def test_源不合即拒且面未动(tmp_path):
    m, man, src, dst, body = _fixture(tmp_path)
    old = os.path.join(dst, u"_old", u"s")
    assert m.publish(src, dst, old) == 0
    before = m.sha256_file(m._join(dst, u"a/b.txt"))
    _mk(m._join(src, u"a/b.txt"), b"tampered\n")
    assert m.publish(src, dst, old) == 2
    assert m.sha256_file(m._join(dst, u"a/b.txt")) == before


def test_面上工作树之形必咬(tmp_path):
    u"""2019 之病之正控：面被换成「工作树之未提交之形」⇒ 面核必咬（rc=2）。"""
    m, man, src, dst, body = _fixture(tmp_path)
    old = os.path.join(dst, u"_old", u"s")
    _mk(m._join(dst, u"web/pa/faces/config.js"), b"cfg-worktree-DIRTY\n")
    assert m.publish(src, dst, old) == 0
    assert m.sha256_file(m._join(dst, u"web/pa/faces/config.js")) == man[u"files"][1][u"sha256"]
    assert m.face_check(dst) == 0
    _mk(m._join(dst, u"web/pa/faces/config.js"), b"cfg-worktree-DIRTY\n")
    assert m.face_check(dst) == 2
    assert m.publish(src, dst, old) == 0
    assert m.face_check(dst) == 0


def test_del唯移不删与多余件必报(tmp_path):
    m, man, src, dst, body = _fixture(tmp_path)
    old = os.path.join(dst, u"_old", u"s")
    assert m.publish(src, dst, old) == 0
    assert not os.path.exists(m._join(dst, u"old/gone.txt"))
    assert os.path.isfile(os.path.join(old, u"old__gone.txt"))
    _mk(m._join(dst, u"web/pa/faces/zzz.js"), b"orphan")
    assert u"web/pa/faces/zzz.js" in m.stale_on_face(dst, man)
    assert m.face_check(dst) == 0


def test_入口错归三(tmp_path):
    m = _load()
    assert m.main([u"--src", os.path.join(str(tmp_path), u"nope")]) == 3
    assert m.main([]) == 3
