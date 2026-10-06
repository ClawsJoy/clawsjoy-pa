# -*- coding: utf-8 -*-
"""⭐ 径之消费者之界（承 pm_1423 §二.3）：`GET /v9/pa/env` 之 `paths` 之消费者须 ≤ `1`
（今唯 `web/pa/faces/products.js`）；若 ≥ `2` ⇒ 须立 `window.PA_PATHS`（一处出 · 承 `PA_STAMP` 之例 ·
`web/pa/core.js:128`）。

判之式（明书所扫之面 ＋ 过取之险 · 承 pm_1414 §三.2）：
  · 面 ＝ `web/pa/**/*.js`（**注释先剥** —— 注释内引 `/v9/pa/env` ／ `.paths` ⛔ 计）；
  · 径之消费者 ＝ 同档内**既**取 `/v9/pa/env`**又**读 `.paths` 者（二条件并 ⇒ ⛔ 单条件即计）。
  · 过取之险（反控钉之）：⒈ `tasks.js` ／ `selfdesc.js` 取 `/v9/pa/env` 而读 `cols`（⛔ 径）⇒ ⛔ 计；
    ⒉ `authz.js` 之 `g.paths` ／ `d.paths` 为**授权范围**之 `paths`（⛔ 本面 · ⛔ 取 env）⇒ ⛔ 计；
    ⒊ 唯**注释**内引二者 ⇒ ⛔ 计（剥注释之效）。
  ⚠ 本器为**源码扫** ⇒ 判「消费者之数」而⛔判「运行之实」；`v2` 宜以「载荷之实」代（承 pm_1415 §一）。

以何形调用（判通 ／ 断须附）：
  python -X utf8 -B -m pytest tests/unit/test_pa_paths_single_consumer.py -q
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PA = ROOT / "web" / "pa"
CORE = PA / "core.js"

ENV_RE = re.compile(r"/v9/pa/env")
PATHS_RE = re.compile(r"\.paths\b")
PA_PATHS_RE = re.compile(r"PA_PATHS\b")
#: 正则字面量之起（前一「有意义」之字符 ∈ 此集 ⇒ `/` 起正则 · ⛔ 除号）—— 粗守（承「器之死须分类」）。
_REGEX_PREV = set("(,=:[!&|?{};+-*/%~^<>") | {""}


def strip_js_comments(src):
    """剥 JS 注释（守字串 ／ 模板 ／ 正则字面量之粗守）—— 承「阴性之读须穷其形」。

    ⚠ 粗守：正则字面量以「前一有意义字符」判（⛔ 完备之 JS 词法）⇒ 若他日有奇异之式 ⇒ 须复扫。
    """
    out = []
    i, n = 0, len(src)
    prev = ""
    while i < n:
        c = src[i]
        if c in ('"', "'", "`"):
            q = c
            out.append(c)
            i += 1
            while i < n:
                if src[i] == chr(92) and i + 1 < n:
                    out.append(src[i]); out.append(src[i + 1]); i += 2; continue
                out.append(src[i])
                if src[i] == q:
                    i += 1
                    break
                i += 1
            prev = "x"
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            while i < n and src[i] != chr(10):
                i += 1
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            i += 2
            while i + 1 < n and not (src[i] == "*" and src[i + 1] == "/"):
                i += 1
            i += 2
            continue
        if c == "/" and prev in _REGEX_PREV:
            out.append(c)
            i += 1
            if i < n and src[i] == "/":
                i += 1
            while i < n:
                if src[i] == chr(92) and i + 1 < n:
                    out.append(src[i]); out.append(src[i + 1]); i += 2; continue
                if src[i] == "/":
                    out.append(src[i]); i += 1; break
                out.append(src[i]); i += 1
            prev = "x"
            continue
        out.append(c)
        if not c.isspace():
            prev = c
        i += 1
    return "".join(out)


def consumers_in(text):
    """判一档（码 ／ 注释之原文）是否为「径之消费者」：❨取 `/v9/pa/env`❩ ∧ ❨读 `.paths`❩。"""
    code = strip_js_comments(text)
    return bool(ENV_RE.search(code)) and bool(PATHS_RE.search(code))


def scan(root=PA):
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*.js")
                  if consumers_in(p.read_text(encoding="utf-8")))


def pa_paths_defined():
    return bool(PA_PATHS_RE.search(strip_js_comments(CORE.read_text(encoding="utf-8"))))


def gate_verdict(n_consumers, has_pa_paths):
    """律：消费者 ≥ `2` ⇒ 须立 `PA_PATHS`（一处出）；否则今形合法。"""
    if n_consumers >= 2:
        return has_pa_paths
    return True


def test_only_one_env_paths_consumer_today():
    cs = scan()
    assert cs == ["faces/products.js"], cs


def test_pa_paths_not_defined_today():
    """今消费者唯 `1` ⇒ `PA_PATHS` 尚 ⛔ 立（承 pm_1423 §二.1：消费者唯 1 ⇒ 界未触发）。"""
    assert not pa_paths_defined()


def test_live_gate_passes():
    assert gate_verdict(len(scan()), pa_paths_defined()) is True


def test_reverse_control_env_without_paths_is_not_consumer():
    """反控（齿）：取 env 而读 `cols`（`tasks.js` 之形）⇒ ⛔ 计为径之消费者。"""
    assert consumers_in("const j=await paGetJson(API+'/v9/pa/env'); use(j.cols);") is False


def test_reverse_control_authz_like_paths_without_env_is_not_consumer():
    """反控：读「授权范围」之 `paths`（`authz.js` 之形 · ⛔ 取 env）⇒ ⛔ 计。"""
    assert consumers_in("paPermGate={approved:true, paths:d.paths};") is False


def test_reverse_control_comment_only_is_not_consumer():
    """反控：唯**注释**内引 `/v9/pa/env` ＋ `.paths` ⇒ ⛔ 计（剥注释之效）。"""
    assert consumers_in("/* 真源 ＝ GET /v9/pa/env 之 j.paths.render */") is False


def test_reverse_control_regex_literal_does_not_break_stripper():
    """反控：含 `` ` `` ／ `"` ／ `'` 于字符类之正则字面量（`products.js:3` 之形）⇒ 剥器 ⛔ 崩。"""
    s = 'const paths=[]; const re=/(data\\/(?:reports|tmp)\\/[^\\s`"\'，。]+?\\.(?:md|txt))/g;'
    assert consumers_in(s) is False


def test_gate_bites_when_two_consumers_without_pa_paths():
    """闸之齿：消费者第 `2` 而 ⛔ `PA_PATHS` ⇒ 判红；立之 ⇒ 绿（本测专钉该律）。"""
    a = "const j=await fetch(API+'/v9/pa/env'); use(j.paths.render);"
    b = "const k=await fetch(API+'/v9/pa/env'); use(k.paths.log);"
    n = sum(1 for s in (a, b) if consumers_in(s))
    assert n == 2
    assert gate_verdict(n, has_pa_paths=False) is False
    assert gate_verdict(n, has_pa_paths=True) is True
    assert gate_verdict(1, has_pa_paths=False) is True