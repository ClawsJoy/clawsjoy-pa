# -*- coding: utf-8 -*-
u"""启动器之「形」与「字面」之齿（承 pm_1595 §二 · 令四）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_win_pa_launcher_form.py -q

判据（⛔ 无齿之闸 ＝ 假绿）：
  ⒈ **字面之齿**：四启动器之逐字 ＋ `installer_post.py` 之源（**并扫逸写之形** ——
     以 ast **并接**相邻 ／ `+` 接之字符串常量）⇒ ⛔ 含两端口之数
     （端口唯真源 `config/system/system_unified.yaml` ⇒ ⛔ 二源 · 承 pm_1595 §二 令三）。
  ⒉ **形之齿（静）**：凡「反引号之 for /f」（`in (` … `)`）⇒ 其命令 ⛔ **首末皆引号**
     （A 支之形：`cmd /c` 吞其外引号 ⇒ 路径被扯碎 ⇒ **空果** ⇒ 死值上位 —— 即 pm_1595 之根因）。
  ⒊ **形之齿（活 · Windows）**：以 `cmd /c` 跑 A 支之形 ⇒ **必空果**（**反控**）；
     跑本器之形（`pa_nowindow.py open --print-url`）⇒ **必得址**（**正控**）。
  ⒋ **辞之齿**：启动器所引 `pa_msg.py` 之键 ⇒ 须皆在（⛔ 键之名 ⛔ 漂）。
"""
import ast
import io
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WPA = ROOT / "scripts" / "win_pa"
sys.path.insert(0, str(WPA))
sys.path.insert(0, str(ROOT))

import installer_post as IP  # noqa: E402
import pa_msg as PMSG  # noqa: E402

#: 齿之针（**⛔ 居被扫之件** —— 免「自指之字面」之假红 · 承 `_SYSREG` 之族）
NEEDLES = (u"510" + u"2", u"510" + u"3")
#: 反引号之 `for /f` 之命令文
FORF = re.compile(r"in \(`(.*?)`\)", re.S)
#: 启动器所引之 pa_msg 键
MSGKEY = re.compile(r"pa_msg\.py\"\s+([A-Za-z][A-Za-z0-9-]*)")


def _static_str(node):
    u"""唯可静态求值之字符串（常量 ／ `+` 并接之链）⇒ str；余 ⇒ None。"""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        a = _static_str(node.left)
        b = _static_str(node.right)
        if a is not None and b is not None:
            return a + b
    return None


def _joined_literals(src):
    u"""源内之诸字符串（**含 `+` 并接之果**）—— 逸写（`u"51" + u"03"`）亦现形。"""
    out = []
    for node in ast.walk(ast.parse(src)):
        v = _static_str(node)
        if v is not None:
            out.append(v)
    return out


def test_no_port_literal_in_launchers_nor_generator():
    u"""⒈ 字面之齿：⛔ 端口之数（⛔ 二源）—— 逐字 ＋ 源 ＋ 逸写。"""
    src = io.open(str(WPA / "installer_post.py"), encoding="utf-8").read()
    bad = []
    for n, t in IP.launcher_texts().items():
        for nd in NEEDLES:
            if nd in t:
                bad.append((u"启动器", n, nd))
    for nd in NEEDLES:
        if nd in src:
            bad.append((u"源之文", u"installer_post.py", nd))
    for v in _joined_literals(src):
        for nd in NEEDLES:
            if nd in v:
                bad.append((u"源之常量（并接）", v[:60], nd))
    assert not bad, u"端口之字面入器 ⇒ ⛔ 二源（真源唯 config）：%s" % (bad,)


def test_no_outer_quote_swallowing_shape():
    u"""⒉ 形之齿（静）：凡反引号之 for /f ⇒ 命令 ⛔ 首末皆引号（A 支 ⇒ 空果）。"""
    bad = []
    for n, t in IP.launcher_texts().items():
        for cmd in FORF.findall(t):
            s = cmd.strip()
            if s.startswith(u'"') and s.endswith(u'"'):
                bad.append((n, s[:90]))
    assert not bad, u"A 支之形（cmd 吞外引号 ⇒ 空果）：%s" % (bad,)
    assert u"in (`" not in IP.launcher_texts()[IP.LAUNCH_OPEN], \
        u"打开页面之器 ⛔ 得用「反引号之 for /f」（唯调唯一入口 pa_nowindow.py open）"


def test_launcher_message_keys_all_exist():
    u"""⒋ 辞之齿：启动器所引之 pa_msg 键 ⇒ 皆在（⛔ 漂名 ⇒ 运行期静默之患）。"""
    for n, t in IP.launcher_texts().items():
        for key in MSGKEY.findall(t):
            assert PMSG.render(key) is not None, (n, key, sorted(PMSG.MSG))


@pytest.mark.skipif(os.name != u"nt", reason=u"cmd /c 唯 Windows（⛔ 静绿 —— 见 pytest 之 s）")
def test_live_a_shape_is_empty_and_our_shape_yields_url(tmp_path):
    u"""⒊ 形之齿（活）：反控（A 支 ⇒ 空果）＋ 正控（本器之形 ⇒ 得址）。"""
    exe = sys.executable
    # ⚠ 形之齿之自坑（我一手撞见）：⛔ 用 `%` 之格式化写 `.cmd` —— `%%U` 会被吞成 `%U`
    #   （cmd 视 `%U` 为变量 ⇒ 空 ⇒ 其「for」之形自坏 ⇒ 齿假红）。故以 `.replace()` 代。
    a_txt = (u'@echo off\r\n'
             u'set "OUT="\r\n'
             u'for /f "usebackq delims=" %%U in (`__EXE__ -X utf8 -c "print(\'URL-OK\')"`) do set "OUT=%%U"\r\n'
             u'echo A=[%OUT%]\r\n').replace(u"__EXE__", u'"' + exe + u'"')
    a = tmp_path / u"a_shape.cmd"
    a.write_bytes(a_txt.encode(u"utf-8"))
    r = subprocess.run([u"cmd", u"/c", str(a)], capture_output=True, text=True,
                       encoding=u"utf-8", errors=u"replace", timeout=120)
    assert u"A=[]" in (r.stdout or u""), (r.returncode, r.stdout, r.stderr)
    assert u"URL-OK" not in (r.stdout or u""), (r.returncode, r.stdout, r.stderr)

    b = tmp_path / u"our_shape.cmd"
    b.write_bytes((u'@echo off\r\n'
                   u'cd /d "%s"\r\n'
                   u'"%s" -X utf8 "%s" open --print-url\r\n'
                   % (str(ROOT), exe, str(WPA / u"pa_nowindow.py"))).encode(u"utf-8"))
    r2 = subprocess.run([u"cmd", u"/c", str(b)], capture_output=True, text=True,
                        encoding=u"utf-8", errors=u"replace", timeout=180)
    out = (r2.stdout or u"").strip()
    assert u"/web/pa.html" in out, (r2.returncode, r2.stdout, r2.stderr)
    assert u"510" + u"3" not in out, out
