# -*- coding: utf-8 -*-
"""知识库路径「前缀由后端给」验收（2026-09-28 · 承 CEO 六裁 ④ 展示面 ＋ C1 契约）。

从真实 web/pa.html 抽定义（move 而非 retype）在 node 里跑：
  · 两形态（本机 Win 形态 / WSL 挂载形态）都要能认；
  · 不在前缀内的路径 ⛔ 不得误认（防链接化把别处路径也吞进来）；
  · 前缀为**后端**所给 ⇒ 无前缀时返回空（⛔ 不用写死的前缀猜）—— 写死另由 C1 静态防线守。
"""
import os
import subprocess

PA = os.path.join("web", "pa.html")
# JS 侧统一用它拼反斜杠，避免在生成的探针里出现单反斜杠转义（会变成非法/十六进制转义）
_JBS = "String.fromCharCode(92)"


def _extract():
    s = open(PA, encoding="utf-8").read()
    out = ""
    for sig in ("function paKbRootForms(){", "function paKbExtractPaths(text, roots){"):
        i = s.find(sig)
        assert i >= 0, "未在 pa.html 找到: " + sig
        j = s.find(chr(10) + "}", i)
        out += s[i:j + 2] + chr(10)
    return "let paKbCache=null;" + chr(10) + out


def _run(body):
    path = os.path.join(os.environ.get("TEMP") or ".", "_kbroot_probe.mjs")
    open(path, "w", encoding="utf-8").write(_extract() + chr(10) + body)
    return subprocess.run(["node", path], capture_output=True, text=True, encoding="utf-8", errors="replace")


PRELUDE = (
    "const B=" + _JBS + ";"
    "const W='D:'+B+'Obsidian'+B+'ClawsJoy'+B+'ClawsJoy';"
    "const U='/mnt/d/Obsidian/ClawsJoy/ClawsJoy';"
)


def test_both_forms_recognized_and_foreign_not():
    """用例1：两形态皆认；前缀外路径 ⛔ 不认。"""
    r = _run(
        PRELUDE
        + "const forms=[W,U];paKbCache={kb_root_forms:forms,kb_root:W,rows:[]};"
        + "const got=paKbExtractPaths('a '+W+B+'codex'+B+'x.md b '+U+'/dsh/y.md c /other/z.md', forms);"
        + "const hit=x=>got.filter(p=>p.indexOf(x)>=0).length;"
        + "if(hit('x.md')!==1) throw new Error('Win 形态未认出: '+JSON.stringify(got));"
        + "if(hit('y.md')!==1) throw new Error('WSL 形态未认出: '+JSON.stringify(got));"
        + "if(hit('z.md')!==0) throw new Error('前缀外路径被误认: '+JSON.stringify(got));"
        + "console.log('OK both-forms n='+got.length);"
    )
    assert r.returncode == 0, r.stderr + r.stdout
    print(r.stdout.strip())


def test_no_prefix_returns_empty_not_guess():
    """用例2：前缀为空 ⇒ 返回空（⛔ 不用写死前缀猜）。"""
    r = _run(
        PRELUDE
        + "paKbCache={rows:[]};"
        + "const got=paKbExtractPaths('see '+W+B+'a.md', []);"
        + "if(got.length!==0) throw new Error('无前缀却给出了路径: '+JSON.stringify(got));"
        + "console.log('OK empty');"
    )
    assert r.returncode == 0, r.stderr + r.stdout
    print(r.stdout.strip())


def test_root_derived_from_rows_kb_abs():
    """用例3：前缀可由 rows 的 kb_abs 反推（后端两字段齐时）。"""
    r = _run(
        PRELUDE
        + "paKbCache={rows:[{kb_path:'codex/x.md',kb_abs:W+B+'codex'+B+'x.md'}]};"
        + "const forms=paKbRootForms();"
        + "if(forms.length!==1 || forms[0].slice(-8)!=='ClawsJoy') throw new Error('反推根失败: '+JSON.stringify(forms));"
        + "const got=paKbExtractPaths('see '+W+B+'codex'+B+'y.md', forms);"
        + "if(got.length!==1) throw new Error('反推根未生效: '+JSON.stringify(got));"
        + "console.log('OK derived');"
    )
    assert r.returncode == 0, r.stderr + r.stdout
    print(r.stdout.strip())