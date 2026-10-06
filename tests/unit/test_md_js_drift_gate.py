# -*- coding: utf-8 -*-
u'''批191 · 渲器漂移闸之跑手（承 pm_1399 §二.1）。

⭐ 由：tests/js/md.test.js 为 node 件 ⇒ ⛔ 入 pytest 之自动采集 ⇒ 本跑手代其入闸。
⭐ 判「成」：node tests/js/md.test.js rc = 0（二份逐字相等 ＋ 九反控）。
⚠ 若 node ⛔ 在 PATH ⇒ skip（**⛔ 判绿** —— 唯「⛔ 得跑」须明书 · 承「凡阴性须附面与刻」）。
⛔ 本跑手 ⛔ 证「渲器安全」（唯证「二份相等 ＋ 九反控之行为」）。
'''
import io
import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GATE = os.path.join(ROOT, "tests", "js", "md.test.js")
MD_JS = os.path.join(ROOT, "web", "static", "js", "md.js")
SESSION_JS = os.path.join(ROOT, "web", "pa", "faces", "session.js")

# 反控之料（须逐条在源中唯见 · 否则「齿」无凭）
CUT_ATTR = u'.replace(/"/g, \'&quot;\')'          # md.js · 属性之境之转
CUT_EM = u"'$1<em>$2</em>'"                        # session.js · 词界强调之渲


def _node():
    return shutil.which("node")


def _sandbox(tmp):
    u'''造一「仿真之仓」：唯 web 与 tests 之二面 ⇒ 供反控喂破口之料。'''
    for sub in (("web", "static", "js"), ("web", "pa", "faces"), ("tests", "js")):
        os.makedirs(os.path.join(tmp, *sub), exist_ok=True)
    shutil.copy2(MD_JS, os.path.join(tmp, "web", "static", "js", "md.js"))
    shutil.copy2(SESSION_JS, os.path.join(tmp, "web", "pa", "faces", "session.js"))
    shutil.copy2(GATE, os.path.join(tmp, "tests", "js", "md.test.js"))
    return os.path.join(tmp, "tests", "js", "md.test.js")


def _mutate(path, old, new):
    s = io.open(path, encoding="utf-8").read()
    assert old in s, u"反控之料 ⛔ 见：%s ⇒ 须更（承「凡反控须有齿」）" % old
    io.open(path, "w", encoding="utf-8", newline="").write(s.replace(old, new, 1))


def test_md_js_drift_gate():
    node = _node()
    if not node:
        pytest.skip(u"node ⛔ 在 PATH ⇒ 漂移闸 ⛔ 得跑（既 ⛔ 判绿 亦 ⛔ 判红）")
    assert os.path.isfile(GATE), u"漂移闸不在：%s" % GATE
    r = subprocess.run([node, GATE], cwd=ROOT, capture_output=True)
    out = (r.stdout or b"").decode("utf-8", "replace") + (r.stderr or b"").decode("utf-8", "replace")
    assert r.returncode == 0, u"渲器漂移闸判红（rc=%s）：\n%s" % (r.returncode, out[-4000:])


def test_md_js_drift_gate_has_teeth(tmp_path_factory):
    u'''反控之反控（三向）：清 ／ 拔属性之转（md.js）／ 改强调之渲（session.js）⇒ 必 0 ／ ≠0 ／ ≠0。'''
    node = _node()
    if not node:
        pytest.skip(u"node ⛔ 在 PATH ⇒ 反控 ⛔ 得跑")
    base = str(tmp_path_factory.mktemp("mdgate"))

    # 正控：清之仿仓 ⇒ 必 0
    t1 = os.path.join(base, "clean")
    g1 = _sandbox(t1)
    r1 = subprocess.run([node, g1], cwd=t1, capture_output=True)
    assert r1.returncode == 0, u"正控失：清之仿仓亦判红\n%s" % (r1.stdout or b"").decode("utf-8", "replace")[-2000:]

    # 反控一：拔 md.js 之属性之转 ⇒ 注入反控须失 ⇒ ≠0
    t2 = os.path.join(base, "noattr")
    g2 = _sandbox(t2)
    _mutate(os.path.join(t2, "web", "static", "js", "md.js"), CUT_ATTR, u"")
    r2 = subprocess.run([node, g2], cwd=t2, capture_output=True)
    assert r2.returncode != 0, u"闸 ⛔ 齿：拔属性之转（注入口重开）亦判绿"

    # 反控二：改 session.js 之强调之渲 ⇒ 二份须漂 ⇒ ≠0
    t3 = os.path.join(base, "drifttag")
    g3 = _sandbox(t3)
    _mutate(os.path.join(t3, "web", "pa", "faces", "session.js"), CUT_EM, u"'$1<i>$2</i>'")
    r3 = subprocess.run([node, g3], cwd=t3, capture_output=True)
    assert r3.returncode != 0, u"闸 ⛔ 齿：二份之渲形已漂（em → i）亦判绿"
