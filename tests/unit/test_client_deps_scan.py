# -*- coding: utf-8 -*-
u"""客户端依赖清单**器**（`scripts/dev/scan_client_deps.py`）之测（承 pm_1386 §二.1）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_client_deps_scan.py -q

判据（⛔ 无齿之闸 ＝ 假绿）：
  ⒈ **层之三则**（⛔ 一名蔽之）：模块级 ∧ ⛔ 兜底 ⇒ **必需** ／ 模块级 ∧ 在 `try` 内 ⇒ **兜底** ／
     函数体 ∨ 经惰性之链 ⇒ **惰性**。
  ⒉ **父包之 `__init__.py` 须入图**（Python 语义）—— 反控：`pkg/__init__.py` 之依必判「必需」
     （⛔ 则 `core/__init__.py ⇒ tenant_vector_index ⇒ chromadb` 之链漏 ⇒ **假阴** · 我一手逮之）。
  ⒊ **命名空间包**（无 `__init__.py` 之目录）判**仓内** ／ `from 包 import 符号` 之**符号**（⛔ 模块）
     ⛔ 误记为第三方。
  ⒋ **本仓之实**（回归钉 · 器取）：`chromadb` **必需**（且声明于**运行依赖**段 · ⛔ 旧之「可选」）／
     `psutil` 必需 ／ `tiktoken` 兜底 ／ 硬缺 ＝ `0`。
  ⒌ **镜像之钉**：`requirements-runtime.txt` ≡ `requirements.txt` 之「运行依赖（必需）」诸节。
"""
import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "dev"))
sys.path.insert(0, str(ROOT))

from scan_client_deps import _norm, declared, report, scan  # noqa: E402


def _mk(tmp_path, files):
    for rel, body in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return tmp_path


def test_层之三则_与父包init入图(tmp_path):
    u"""反控（承 ⒈ ⒉）：三则分明 ／ 父包 `__init__.py` 之依必入（⛔ 假阴）。"""
    _mk(tmp_path, {
        "entry.py": u"import pkg.mod\n",
        "pkg/__init__.py": u"import zzz_pkginit\n",
        "pkg/mod.py": (u"import zzz_mod\n"
                       u"def f():\n"
                       u"    import zzz_lazy\n"
                       u"try:\n"
                       u"    import zzz_guard\n"
                       u"except Exception:\n"
                       u"    zzz_guard = None\n"),
    })
    third, _dyn, _roots, _sh = scan(str(tmp_path), "entry.py")
    assert third["zzz_pkginit"]["必需"] is True, u"父包 __init__.py 之依漏（⛔ 则 chromadb 之链假阴）"
    assert third["zzz_mod"]["必需"] is True
    assert third["zzz_lazy"]["惰性"] is True and third["zzz_lazy"]["必需"] is False
    assert third["zzz_guard"]["兜底"] is True and third["zzz_guard"]["必需"] is False
    assert third["zzz_lazy"]["诸处"] and third["zzz_guard"]["诸处"]


def test_命名空间包与符号(tmp_path):
    u"""反控（承 ⒊）：`from core.tools import thing` 之 `thing` ＝ **符号**（⛔ 模块）／
    命名空间目录之子模块须入图。"""
    _mk(tmp_path, {
        "entry.py": u"from core.tools import thing\n",
        "core/__init__.py": u"import zzz_rootdep\n",
        "core/tools/thing.py": u"import zzz_sub\n",
    })
    third, _dyn, _roots, _sh = scan(str(tmp_path), "entry.py")
    assert "core" not in third, u"本地符号（⛔ 模块）被误记成第三方「core」"
    assert third["zzz_rootdep"]["必需"] is True, u"core/__init__.py 之依漏"
    assert third["zzz_sub"]["必需"] is True, u"命名空间包内之子模块未入图"


def test_本仓之实_回归钉():
    u"""承 ⒋：以器取之本仓之实（⛔ 手拟）。"""
    third, _dyn, _roots, shadows = scan(str(ROOT))
    assert third.get("chromadb", {}).get("必需") is True, u"chromadb 非「必需」⇒ core/__init__.py 链断（假阴）"
    assert third.get("psutil", {}).get("必需") is True
    assert third.get("tiktoken", {}).get("必需") is False, \
        u"tiktoken 之 import 皆在函数体 ∨ 惰性之链 ⇒ ⛔ 判「必需」"
    assert "code_entity_extractor" not in third, u"仓内同名之件被作第三方发行（假红）"
    assert shadows.get("code_entity_extractor", {}).get("仓内同名") == "core/lib/code_entity_extractor.py"
    assert not [k for k in third if k == "pythoncom" or k.startswith("win32")], \
        u"pywin32 之说法 ⛔ 复现（`win32` 唯 sys.platform 之字串 · ⛔ import）"
    decl = declared(str(ROOT))
    assert decl["chromadb"][0] == "requirements.txt"
    assert decl["chromadb"][2].startswith(u"运行依赖"), \
        u"chromadb 须在「运行依赖」段（⛔ 旧之「可选依赖」）: %r" % (decl["chromadb"],)
    for k in ("psutil", "tiktoken", "chromadb"):
        assert k in decl, k


def test_本仓硬缺为零():
    u"""承 ⒋：`report()` 之两栏皆空（已正 requirements.txt）—— 回归钉。"""
    r = report(str(ROOT))
    assert r["必需而未声明"] == [], r["必需而未声明"]
    assert r["兜底而未声明"] == [], r["兜底而未声明"]
    assert r["口径"] and r["根"]


def _req_names(path, only_required=False):
    sec, out = "", set()
    for ln in io.open(str(path), encoding="utf-8").read().splitlines():
        s = ln.strip()
        if s.startswith("#"):
            m = re.search(r"=\s*([^=]+?)\s*=", s)
            if m:
                sec = m.group(1).strip()
            continue
        s = s.split("#")[0].strip()
        if not s:
            continue
        m = re.match(r"^([A-Za-z0-9][A-Za-z0-9_.\-]*)", s)
        if not m:
            continue
        if only_required and not sec.startswith(u"运行依赖"):
            continue
        out.add(_norm(m.group(1)))
    return out


def test_镜像之钉_runtime_eq_必需节():
    u"""承 ⒌：`requirements-runtime.txt` ≡ 真源之「运行依赖（必需）」诸节（二源必漂 ⇒ 钉之）。"""
    src = _req_names(ROOT / "requirements.txt", only_required=True)
    mirror = _req_names(ROOT / "requirements-runtime.txt")
    assert src, u"真源之必需节空 ＝ 判据无齿"
    assert mirror == src, (u"镜像缺:", sorted(src - mirror), u"镜像多:", sorted(mirror - src))
    for k in ("chromadb", "psutil", "tiktoken"):
        assert k in mirror, k
