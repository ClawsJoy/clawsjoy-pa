# -*- coding: utf-8 -*-
u"""pm_1628 §二.3 令三（源可配 ＋ 通道 · 并入甲-P0）之齿 —— 更新源之「一处定形」（技术总监席 f202f89 · 2026-10-07）。

一事：`provider` ／ `url` ／ `channel` 之声明 ＝ `config/update_source.yaml`（**入包**）；
  优先序（一处定形）＝ env ⇒ 文件 ⇒ 默认；逐次报「源」（`origin`）。

以何形调用（判通 ／ 断须附）：
  python -X utf8 -B -m pytest tests/unit/test_update_source_1629.py -q

判据：
  ⒜ 正控：文件三键 ⇒ 逐键出 ∧ `origin` 记 `file:`
  ⒝ 正控：env ⇒ 覆文件（**切源 ⛔ 须重出包** 之据）∧ url ／ channel 各可独覆
  ⒞ 反控：无文件 ⇒ 默认 ＋ **明书「未见」**（⛔ 静默）
  ⒟ 反控：通道非常 ／ url 非 http(s) ⇒ **明书其疑**（⛔ 充）
  ⒠ 一处定形：清单 ／ 包之取处唯 `manifest_url` ／ `package_url`（⛔ 各拼）
  ⒡ 反控：本模块**⛔ 出网**（依不出标准库 ∧ ⛔ 含 socket ／ urllib ／ http ／ requests）
  ⒢ 真源随包：`config/update_source.yaml` ⇒ **在 `_payload_files()`**（⛔ 静默地落包外）
"""
import ast
import importlib.util
import io
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts" / "win_pa") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts" / "win_pa"))

spec = importlib.util.spec_from_file_location("_us1629", str(ROOT / "core" / "lib" / "update_source.py"))
US = importlib.util.module_from_spec(spec)
spec.loader.exec_module(US)

YAML = u"url: http://10.0.0.9:8080/\nchannel: beta\nprovider: generic\n"


def _root(t, text=None):
    d = os.path.join(t, "config")
    os.makedirs(d, exist_ok=True)
    if text is not None:
        with io.open(os.path.join(d, "update_source.yaml"), "w", encoding="utf-8", newline=u"") as fh:
            fh.write(text)
    return t


def test_正控_文件三键与origin():
    t = tempfile.mkdtemp(prefix="cjpa_us1629_")
    try:
        _root(t, YAML)
        d = US.load(root=t, env={})
        assert d[u"url"] == u"http://10.0.0.9:8080/", d
        assert d[u"channel"] == u"beta" and d[u"provider"] == u"generic", d
        assert all(x.startswith(u"file:") for x in d[u"origin"].values()), d[u"origin"]
        assert d[u"note"] == u"", d[u"note"]
    finally:
        shutil.rmtree(t, ignore_errors=True)


def test_正控_env覆文件_切源不须重出包():
    u"""⒝：env ⇒ 覆文件（**切源 ⛔ 须重出包** —— 唯改一行 ∨ 设 env）。"""
    t = tempfile.mkdtemp(prefix="cjpa_us1629e_")
    try:
        _root(t, YAML)
        d = US.load(root=t, env={u"PA_UPDATE_CHANNEL": u"internal"})
        assert d[u"channel"] == u"internal", d
        assert d[u"origin"][u"channel"] == u"env:PA_UPDATE_CHANNEL", d[u"origin"]
        assert d[u"url"] == u"http://10.0.0.9:8080/", d
        d2 = US.load(root=t, env={u"PA_UPDATE_URL": u"https://cdn.example.com/updates"})
        assert d2[u"url"] == u"https://cdn.example.com/updates", d2
        assert d2[u"origin"][u"url"].startswith(u"env:"), d2[u"origin"]
    finally:
        shutil.rmtree(t, ignore_errors=True)


def test_反控_无文件则默认且明书():
    u"""⒞：无文件 ⇒ 默认 ∧ **明书「未见」**（⛔ 静默）。"""
    t = tempfile.mkdtemp(prefix="cjpa_us1629n_")
    try:
        _root(t)
        d = US.load(root=t, env={})
        assert d[u"url"] == US.DEFAULT_URL and d[u"channel"] == US.DEFAULT_CHANNEL, d
        assert d[u"provider"] == US.DEFAULT_PROVIDER, d
        assert all(v == u"default" for v in d[u"origin"].values()), d[u"origin"]
        assert u"未见" in d[u"note"], d[u"note"]
    finally:
        shutil.rmtree(t, ignore_errors=True)


def test_反控_通道非常与url非http皆明书():
    u"""⒟：疑 ⇒ **明书其疑**（⛔ 充 ⇒ 免「静默地跨档 ／ 静默地走 ftp」）。"""
    t = tempfile.mkdtemp(prefix="cjpa_us1629b_")
    try:
        _root(t, u"url: ftp://x/\nchannel: canary\nprovider: generic\n")
        d = US.load(root=t, env={})
        assert d[u"channel"] == u"canary" and d[u"url"] == u"ftp://x/", d
        assert u"通道非常" in d[u"note"] and u"非 http" in d[u"note"], d[u"note"]
    finally:
        shutil.rmtree(t, ignore_errors=True)


def test_一处定形_取件之url():
    u"""⒠：清单 ／ 包之取处唯此二处出（⛔ 各拼 ⇒ 免二处漂）。"""
    src = {u"url": u"http://h:1/updates/"}
    assert US.manifest_url(src) == u"http://h:1/updates/update_manifest.json"
    assert US.package_url(src, u"inc_1.zip") == u"http://h:1/updates/inc_1.zip"
    assert US.package_url(src, u"/inc/2.zip") == u"http://h:1/updates/inc/2.zip"


def test_反控_本模块不出网():
    u"""⒡：依不出标准库 ∧ ⛔ 含网络之模（本模块**唯读声明** —— 取件归甲-P0 之器）。"""
    p = ROOT / "core" / "lib" / "update_source.py"
    src = io.open(str(p), encoding="utf-8").read()
    mods = set()
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Import):
            mods |= {a.name.split(u".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module and not n.level:
            mods.add(n.module.split(u".")[0])
    bad = {u"socket", u"urllib", u"http", u"requests", u"ftplib"}
    assert not (bad & mods), mods
    # yaml 为**软依**（try ⇒ 极简回落 `_mini_yaml`）—— 同族于仓内配置之主
    assert not [m for m in mods if m not in (set(sys.stdlib_module_names) | {u"yaml"})], mods


def test_真源随包_在payload():
    u"""⒢：`config/update_source.yaml` ⇒ **在 `_payload_files()`**（⛔ 静默地落包外 ⇒ 净机无源）。"""
    import make_client_bundle as MB
    files = set(MB._payload_files(str(ROOT)))
    assert u"config/update_source.yaml" in files, u"⛔ 入包 ⇒ 净机读不到源之声明"
    assert (ROOT / "config" / "update_source.yaml").is_file()
