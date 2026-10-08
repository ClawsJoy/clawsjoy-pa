# -*- coding: utf-8 -*-
"""1913 ② · 「窗数入账」之齿 —— `scripts/dev/窗数入账.py` 之纯逻辑。

承 pm_1913 §二.3（准落：账增「可见窗之数 ／ 其题 ／ 其 rect」）。

正控：一扇可见 PA 窗（正位）⇒ 判 ok ／ rc 0。
反控：① **最小化**（`iconic` ／ rect `-32000`）⇒ **⛔ 疑**（＝ 本器 v1 之自正 ·
「`-32000` 恒为最小化之常形 · ⛔ 离屏首绘」）　② 二扇可见 PA 窗 ⇒ 疑「白幕 ×2」
　③ 非最小化 ∧ 离屏 ⇒ 疑　④ 零尺寸 ⇒ 疑　⑤ 不可见 ／ 非 chrome ⇒ ⛔ 入
　⑥ 虚拟屏读不到 ⇒ ⛔ 假红　⑦ 器 **只读** —— 源码 ⛔ 含关窗 ／ 杀进程 ／ 发消息之调用。

⚠ 本件 ⛔ 起真浏览器 · ⛔ 关任何窗 · ⛔ 杀任何进程（唯读源码 ＋ 纯逻辑）。
"""
import importlib.util
import io
import os

import pytest

_MOD = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "scripts", "dev", "窗数入账.py",
)
PA = "ClawsJoy PA · v3 工作台（3 主面 · 同源真页） - Google Chrome"
MINI = (-32000, -32000, -31840, -31972)


def _load():
    spec = importlib.util.spec_from_file_location("win_probe_1913", _MOD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def M():
    assert os.path.exists(_MOD), "器不在盘: %s" % _MOD
    return _load()


def _W(hwnd, pid, title, rect, vis=True, iconic=False, vs=(0, 0, 2560, 1440)):
    return {"hwnd": hwnd, "pid": pid, "title": title, "rect": rect,
            "visible": vis, "iconic": iconic, "vs": vs}


def test_器在盘且只读(M):
    src = io.open(_MOD, encoding="utf-8").read()
    for bad in ("Stop-Process", "taskkill", "TerminateProcess", "os.kill", "p.Kill",
                "CloseWindow", "PostMessage", "DestroyWindow", "SendMessageW"):
        assert bad not in src, "器须只读，⛔ 含 %s" % bad


def test_正控_一扇可见PA窗判常态(M):
    rec = M.build_record([_W(1, 100, PA, (0, 0, 1600, 900))], [100], "t")
    assert rec["verdict"] == "ok" and rec["visible_pa"] == 1 and M.rc_of(rec) == 0


def test_反控_最小化不算疑(M):
    rec = M.build_record([_W(1, 100, PA, MINI, iconic=True)], [100], "t")
    assert rec["windows"][0]["flags"] == ["minimized", "pa"]
    assert rec["verdict"] == "ok", "-32000 ＋ iconic ⇒ 最小化之常形 ⇒ ⛔ 疑"
    assert rec["visible_minimized"] == 1


def test_反控_非最小化离屏则疑(M):
    rec = M.build_record([_W(1, 100, PA, MINI, iconic=False)], [100], "t")
    assert "offscreen" in rec["windows"][0]["flags"] and M.rc_of(rec) == 1


def test_反控_二扇可见PA窗疑白幕(M):
    rec = M.build_record([_W(1, 100, PA, (0, 0, 900, 600)), _W(2, 100, PA, (0, 0, 900, 600))], [100], "t")
    assert any("白幕" in s for s in rec["suspect"]) and M.rc_of(rec) == 1


def test_反控_不可见与非chrome不计(M):
    assert M.build_record([_W(1, 100, PA, (0, 0, 900, 600), vis=False)], [100], "t")["visible_chrome"] == 0
    assert M.build_record([_W(1, 42, "记事本", (0, 0, 900, 600))], [100], "t")["visible_chrome"] == 0


def test_反控_虚拟屏读不到不假红(M):
    assert M.intersects(MINI, (0, 0, 0, 0)) is True
    assert M.intersects((0, 0, 100, 100), (0, 0, 2560, 1440)) is True
    assert M.intersects((4000, 0, 4100, 100), (0, 0, 2560, 1440)) is False


def test_账_行可回读(M):
    import json
    rec = M.build_record([_W(1, 100, PA, (0, 0, 1600, 900))], [100], "t", chrome_total=7)
    assert json.loads(M.jsonl_of(rec))["visible_pa"] == 1


def test_自证十二例(M):
    assert M._self_test() == 0
