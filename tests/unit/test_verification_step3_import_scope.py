# -*- coding: utf-8 -*-
"""门：Step3 运行验证的 **import 测试「先证再用」**（2026-09-20 · DSH 修 · DS 741/769 裁）。

触发（实测）：`run_verify` 第三道 import 测试两处**假红** ——
  ① `_mod = _abs.relative_to(base_dir)` 拼点分名（沙箱里得 `clawsjoy_dev.core.lib.x`），
     而**子进程不开 cwd**（跑在网关自己的 cwd）⇒ **沙箱里每个 .py 都 ModuleNotFoundError ⇒ 恒红**；
  ② 件不在 base_dir 下时 `relative_to` 抛 ValueError ⇒ 被 `except (SyntaxError, ValueError)`
     当成「运行级语法错误」⇒ 又一条假红。

新口径（先证再用）：包链（每层须 `__init__.py`）为空 ⇒ **前提不成立 ⇒ 不判**（计数外露
`skipped_import_no_pkg`）；有包链 ⇒ import root ＝ 包链之外那层，**cwd=root** 跑子进程；
**真导入失败 ⇒ 照旧判红（有齿）**。

该红格 ＋ 对照的对照：G3/G4 在旧口径下必红、在新口径下必绿 ⇒ 影子失配 > 0。
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.lib.verification_chain import run_verify  # noqa: E402


def _mk(tmp_path, rel, text, pkgs=()):
    for d in pkgs:
        p = tmp_path / d
        p.mkdir(parents=True, exist_ok=True)
        (p / "__init__.py").write_text("", encoding="utf-8")
    f = tmp_path / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding="utf-8")
    return {"path": rel, "absolute": f}


def _old_import_fails(f, base_dir):
    """修前那段的等价复现（只到 import 测试）：True = 旧口径会判红。"""
    p = Path(f["absolute"])
    try:
        rel = p.relative_to(base_dir) if base_dir else Path(p.name)
    except ValueError:
        return True          # 旧代码把它当「运行级语法错误」⇒ 红
    mod = str(rel).replace(os.sep, ".").replace("/", ".")
    if mod.endswith(".py"):
        mod = mod[:-3]
    r = subprocess.run([sys.executable, "-c", "import " + mod], capture_output=True, text=True, timeout=30)
    return r.returncode != 0


def test_package_module_imports_ok(tmp_path):
    """正格：包链齐全 + 能导入 ⇒ 绿，且无「前提不成立」计数。"""
    f = _mk(tmp_path, "core/lib/ok_mod.py", "V = 1\n", pkgs=("core", "core/lib"))
    r = run_verify([f], tmp_path)
    assert r["passed"] is True, r
    assert r.get("skipped_import_no_pkg") == 0, r


def test_package_module_import_broken_is_red(tmp_path):
    """该红格：包链齐全但**导入真失败** ⇒ 必须红（判据有齿）。"""
    f = _mk(tmp_path, "core/lib/bad_mod.py", "import definitely_missing_module_xyz\n", pkgs=("core", "core/lib"))
    r = run_verify([f], tmp_path)
    assert r["passed"] is False, r
    assert any("import 导入测试失败" in str(x.get("error", "")) for x in r["failed"]), r["failed"]


def test_non_package_script_not_judged(tmp_path):
    """修前恒红那格：裸脚本（无包链）⇒ 新口径**不判**（只计数外露），旧口径必红。"""
    f = _mk(tmp_path, "loose_mod.py", "X = 2\n")
    r = run_verify([f], tmp_path)
    assert r["passed"] is True, r
    assert r.get("skipped_import_no_pkg") == 1, r
    assert _old_import_fails(f, tmp_path) is True, "对照的对照：旧口径应对这格必红"


def test_file_outside_base_dir_not_judged(tmp_path):
    """修前另一条假红：件不在 base_dir 下 ⇒ 旧代码 relative_to 抛 ValueError 被当语法错误 ⇒ 红。"""
    base = tmp_path / "sandbox"
    base.mkdir()
    f = _mk(tmp_path, "outside/x.py", "Y = 3\n")
    assert not str(f["absolute"]).startswith(str(base))
    r = run_verify([f], base)
    assert r["passed"] is True, r
    assert r.get("skipped_import_no_pkg") == 1, r
    assert _old_import_fails(f, base) is True, "对照的对照：旧口径应对这格必红"
