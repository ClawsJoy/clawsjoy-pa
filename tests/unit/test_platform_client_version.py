# -*- coding: utf-8 -*-
u"""R6 G1（task-64）：平台注册 payload 之版本**唯引真源** `core.lib.version.__version__`（⛔ 第二定义点）。

以何形调用：
  python -X utf8 -B -m pytest tests/unit/test_platform_client_version.py -q

判据（可机检）：
  ① import 可用：`core.lib.platform_client` 在无 `os.uname` 之平台（Windows）亦**不崩**；
  ② 源内 ⛔ 我方版号族字面（`9.0.x`）；⛔ 重定义 `__version__`；必引 `from core.lib.version import __version__`；
  ③ AST：`login()` 之 `/api/os/register` payload 的 `"version"` 值 ＝ `Name(__version__)`（⛔ 字面），
     其余字段（hostname ／ capabilities）**不动**、键序不动；
  ④ 行为（假 requests · ⛔ 触网）：register payload 之 version ≡ 真源；且真源变 ⇒ payload 随变（⛔ 字面）；
  ⑤ 反控：本测之字面扫描器喂假字面 ⇒ 必逮（⛔ 无齿之闸 ＝ 假绿）。
"""
import ast
import re
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.lib import platform_client as PC  # noqa: E402
from core.lib.version import __version__  # noqa: E402

SRC = Path(PC.__file__).resolve()

SRC_TEXT = SRC.read_text(encoding="utf-8")

#: 我方版号族之字面（三段数字 · 前后 ⛔ 接数字与点）；「族」由真源取（⛔ 手写 9.）
FAMILY_PREFIX = __version__.split(".")[0] + "."

VER_LITERAL_RE = re.compile(r"(?<![\d.])(\d+\.\d+\.\d+)(?![\d.])")

VERSION_ASSIGN_RE = re.compile(r"(?m)^__version__\s*=")


def _family_literals(text):
    """版号族之字面（与 test_version_literals_1849 同形之最小复刻 —— 本测自有齿）。"""
    return [m.group(1) for m in VER_LITERAL_RE.finditer(text)
            if m.group(1).startswith(FAMILY_PREFIX)]


def _register_payload_dict():
    """从 AST 取 `/api/os/register` 之 payload Dict（hostname ／ version ／ capabilities 三键）。"""
    tree = ast.parse(SRC_TEXT)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        keys = [k.value for k in node.keys if isinstance(k, ast.Constant)]
        if set(keys) == {"hostname", "version", "capabilities"}:
            return node, keys
    return None, None


class _FakeRequests:
    """假 requests：记 call、回 200/token（⛔ 触网）。"""

    def __init__(self):
        self.calls = []

    def post(self, url, **kw):
        self.calls.append((url, dict(kw)))
        return types.SimpleNamespace(status_code=200, json=lambda: {"token": "jwt-test"})

    def get(self, url, **kw):  # pragma: no cover - login 不走 GET
        raise AssertionError("本测 ⛔ 触网：%s" % url)


def _client(monkeypatch):
    fake = _FakeRequests()
    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(post=fake.post))
    client = PC.PlatformClient(platform_url="http://platform.invalid")
    monkeypatch.setattr(client, "_load_or_create_key",
                        lambda: {"public_key": "PUBKEY-B64"})
    return client, fake


# ---------- ① import ----------

def test_import_works_without_os_uname():
    u"""真机（Windows 无 os.uname）import 成 — 旧形 `platform = PlatformClient()` 即崩。"""
    assert isinstance(PC.platform, PC.PlatformClient)
    assert isinstance(PC.platform.hostname, str) and PC.platform.hostname, PC.platform.hostname
    assert PC.__version__ == __version__, (PC.__version__, __version__)


# ---------- ② 源：无字面 ／ 无第二定义 ／ 引真源 ----------

def test_source_has_no_family_version_literal():
    assert _family_literals(SRC_TEXT) == [], u"⛔ 手写版号族字面：%s" % _family_literals(SRC_TEXT)


def test_source_imports_single_source_and_does_not_redefine():
    assert "from core.lib.version import __version__" in SRC_TEXT
    assert not VERSION_ASSIGN_RE.search(SRC_TEXT), u"⛔ 第二定义点（__version__ 赋值）"
    assert u'"version": __version__' in SRC_TEXT, u"payload 之 version 须引真源"


# ---------- ③ AST：payload 形状 ----------

def test_register_payload_other_fields_and_key_order_unchanged():
    node, keys = _register_payload_dict()
    assert node is not None, u"未找到 os/register payload（hostname/version/capabilities）"
    assert keys == ["hostname", "version", "capabilities"], keys
    idx = keys.index("version")
    value = node.values[idx]
    assert isinstance(value, ast.Name) and value.id == "__version__", ast.dump(value)
    for field in ("hostname", "capabilities"):
        assert isinstance(node.values[keys.index(field)], (ast.Name, ast.Attribute, ast.List, ast.Constant)), field


# ---------- ④ 行为：payload version 取自真源（假 requests） ----------

def test_login_register_payload_uses_version_source(monkeypatch):
    client, fake = _client(monkeypatch)
    assert client.login() is True
    assert client.jwt == "jwt-test"
    register = [(url, kw) for url, kw in fake.calls if url.endswith("/api/os/register")]
    assert len(register) == 1, fake.calls
    url, kw = register[0]
    payload = kw["json"]
    assert set(payload) == {"hostname", "version", "capabilities"}, payload
    assert payload["version"] == __version__, payload
    assert payload["hostname"] == client.hostname, payload
    assert payload["capabilities"] == ["agent_workspace"], payload
    assert kw["timeout"] == 5, kw


def test_payload_follows_source_change(monkeypatch):
    u"""反控：真源变 ⇒ payload **随变**（⛔ 字面 · 改版必跟）。"""
    monkeypatch.setattr(PC, "__version__", u"9.9.9-simulated")
    client, fake = _client(monkeypatch)
    assert client.login() is True
    payload = [kw["json"] for url, kw in fake.calls if url.endswith("/api/os/register")][0]
    assert payload["version"] == u"9.9.9-simulated", payload


# ---------- ⑤ 反控：扫描器有齿 ----------

def test_scanner_teeth():
    fake_src = 'return {"hostname": "h", "version": "9.0.40", "capabilities": []}'
    ok_src = 'return {"hostname": "h", "version": __version__, "capabilities": []}'
    assert _family_literals(fake_src) == ["9.0.40"], u"反控失败：假字面未被逮"
    assert _family_literals(ok_src) == [], u"反控失败：真源之引被误逮"
