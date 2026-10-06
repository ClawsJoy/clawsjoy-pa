# -*- coding: utf-8 -*-
u"""甲 件二（pm_1520 §二.1 ／ §二.2）：`UnifiedConfig.set_and_save()` 之齿 —— 保注释 ／ 保他行 ／ 存底 ／ 用户级。

判据：
  ⒜ 写 ⇒ **唯该行变**（他行 ／ 注释皆 ⛔ 动）
  ⒝ 键 ⛔ 在 ⇒ 附于父块之后（父块他键 ⛔ 失）
  ⒞ 同值重写 ⇒ `changed:false` ∧ ⛔ 动盘
  ⒟ 坏体 ⇒ 拒写（⛔ 静默 · ⛔ 覆）
  ⒠ 写前存底（`.before_<16hex>` · 承 `core/lib/paths.py` 之派生名预算）
  ⒡ 装根 ⛔ 可写 ⇒ 落用户级（`%APPDATA%` · 序在装根之次 ⇒ **覆盖**）
  ⒢ 注释数（写前 ／ 写后）**须同**（此即「保注释」之齿）

器取：python -X utf8 -B -m pytest tests/unit/test_unified_config_set_and_save.py -q --basetemp=<仓外>
"""
import re
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.lib.unified_config import UnifiedConfig  # noqa: E402


CFG_V = u"""# 头部注释（须保）
version: 4.0.0
paths:
  config_root: config      # 行内注释（须保）
  data_root: data
  vault_root: D:/old      # 旧值之注（须保）
services:
  gateway:
    port: 5103
"""

CFG_NO_V = u"""# 头部注释（须保）
version: 4.0.0
paths:
  config_root: config      # 行内注释（须保）
  data_root: data
  logs_root: logs
services:
  gateway:
    port: 5103
"""


def _fresh(tmp_path, raw, name=u"system_unified.yaml"):
    d = tmp_path / u"config" / u"system"
    d.mkdir(parents=True)
    p = d / name
    p.write_text(raw, encoding=u"utf-8")
    c = object.__new__(UnifiedConfig)      # 绕单例（⛔ 扰全局 `_config`）
    c._config = {}
    c._main_path = p
    return c, p


def _comments(s):
    return sum(1 for ln in s.splitlines() if u"#" in ln)


def test_A_键在_唯该行变_保注释_存底(tmp_path):
    c, p = _fresh(tmp_path, CFG_V)
    before = p.read_text(encoding=u"utf-8")
    r = c.set_and_save(u"paths.vault_root", u"D:/new")
    after = p.read_text(encoding=u"utf-8")
    assert r[u"changed"] is True and r[u"form"] == u"replace-line", r
    # ⒜ 唯该行变
    bl, al = before.splitlines(), after.splitlines()
    assert len(bl) == len(al), (len(bl), len(al))
    diff = [i for i, (x, y) in enumerate(zip(bl, al)) if x != y]
    assert len(diff) == 1 and u"vault_root" in al[diff[0]], (diff, al[diff[0]])
    # ⒢ 注释数同
    assert _comments(before) == _comments(after) == 3, (_comments(before), _comments(after))
    assert u"旧值之注（须保）" in after, after
    # 值生效（盘 ＋ 内存）
    assert yaml.safe_load(after)[u"paths"][u"vault_root"] == u"D:/new"
    assert c.get(u"paths.vault_root") == u"D:/new"
    # ⒠ 存底
    bak = Path(r[u"backup"])
    assert bak.exists() and bak.read_text(encoding=u"utf-8") == before, r
    assert re.match(u"^system_unified\\.yaml\\.before_[0-9a-f]{16}$", bak.name), bak.name


def test_B_键不在_附于父块之后_他键不失(tmp_path):
    c, p = _fresh(tmp_path, CFG_NO_V)
    before = p.read_text(encoding=u"utf-8")
    r = c.set_and_save(u"paths.vault_root", u"D:/picked")
    after = p.read_text(encoding=u"utf-8")
    assert r[u"changed"] is True and r[u"form"] == u"append-key", r
    d = yaml.safe_load(after)
    assert d[u"paths"][u"vault_root"] == u"D:/picked"
    assert d[u"paths"][u"data_root"] == u"data" and d[u"paths"][u"config_root"] == u"config"
    assert _comments(before) == _comments(after) == 2
    # 附于 paths 块之内（⛔ 落 services）
    assert u"services" in after and after.index(u"vault_root") < after.index(u"services"), after
    assert len(after.splitlines()) == len(before.splitlines()) + 1


def test_C_同值重写_不动盘_无存底(tmp_path):
    c, p = _fresh(tmp_path, CFG_V)
    before = p.read_bytes()
    r = c.set_and_save(u"paths.vault_root", u"D:/old")
    assert r[u"changed"] is False and r[u"backup"] is None, r
    assert p.read_bytes() == before
    assert not list(p.parent.glob(u"*.before_*"))


def test_D_坏体_拒写_不覆(tmp_path):
    bad = u"paths: [unclosed\n"
    c, p = _fresh(tmp_path, bad)
    before = p.read_bytes()
    with pytest.raises(ValueError):
        c.set_and_save(u"paths.vault_root", u"D:/x")
    assert p.read_bytes() == before
    assert not list(p.parent.glob(u"*.before_*"))


def test_E_父块皆无_文末立之(tmp_path):
    c, p = _fresh(tmp_path, u"version: 4.0.0\n# 注（须保）\n")
    r = c.set_and_save(u"paths.vault_root", u"D:/new")
    after = p.read_text(encoding=u"utf-8")
    assert r[u"form"] == u"append-block", r
    assert yaml.safe_load(after)[u"paths"][u"vault_root"] == u"D:/new"
    assert u"# 注（须保）" in after


def test_F_父块非块式_拒写(tmp_path):
    c, p = _fresh(tmp_path, u"paths: {data_root: data}\n")
    before = p.read_bytes()
    with pytest.raises(ValueError):
        c.set_and_save(u"paths.vault_root", u"D:/x")
    assert p.read_bytes() == before


def test_G_装根不可写_落用户级(tmp_path, monkeypatch):
    c, p = _fresh(tmp_path, CFG_NO_V)
    ap = tmp_path / u"appdata"
    monkeypatch.setenv(u"APPDATA", str(ap))
    _uc = sys.modules[u"core.lib.unified_config"]   # ⚠ `import ... as` 得**单例**（名被 `core/lib/__init__` 夺）

    _real_os = _uc.os

    class _NoW(object):
        def __getattr__(self, k):
            if k == u"access":
                return lambda *a, **kw: False
            return getattr(_real_os, k)

    monkeypatch.setattr(_uc, u"os", _NoW())
    r = c.set_and_save(u"paths.vault_root", u"D:/u")
    u = ap / u"ClawsJoy" / u"system_unified.yaml"
    assert u.exists() and r[u"file"] == str(u), r
    assert yaml.safe_load(u.read_text(encoding=u"utf-8"))[u"paths"][u"vault_root"] == u"D:/u"
    assert p.read_text(encoding=u"utf-8") == CFG_NO_V      # 装根 ⛔ 动


def test_H_用户级层_覆盖装根_深并(tmp_path, monkeypatch):
    root = tmp_path / u"repo"
    (root / u"config" / u"system").mkdir(parents=True)
    (root / u"config" / u"system" / u"system_unified.yaml").write_text(
        u"paths:\n  data_root: data\n  vault_root: D:/install\n", encoding=u"utf-8")
    ap = tmp_path / u"appdata"
    (ap / u"ClawsJoy").mkdir(parents=True)
    (ap / u"ClawsJoy" / u"system_unified.yaml").write_text(
        u"paths:\n  vault_root: D:/user\n", encoding=u"utf-8")
    monkeypatch.setenv(u"APPDATA", str(ap))
    monkeypatch.chdir(root)
    c = object.__new__(UnifiedConfig)
    c._config = {}
    c._load()
    assert c.get(u"paths.vault_root") == u"D:/user"
    assert c.get(u"paths.data_root") == u"data"      # 深并 ⇒ 装根之他键 ⛔ 失
    assert str(c._main_path).endswith(u"system_unified.yaml")