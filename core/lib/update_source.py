# -*- coding: utf-8 -*-
u"""更新源之「一处定形」（承 pm_1626 §二.1 ＋ pm_1628 §二.3 令三 · 技术总监席 f202f89 · 2026-10-07）。

病（PM 一手 · pm_1626）：更新之「源」若写死单处 ⇒ 内测（局域网分享面）⟷ 静态桶 ⟷ Releases
  皆须重出包 ⇒ ⛔ 可支撑内测之迭代（承「凡『源』⇒ 须可配 ∧ ⛔ 写死」）。
  DSH 之同构物 ＝ `resources/app-update.yml`（`provider ／ owner ／ repo ／ channel` · 一文件一处）。

形（唯三键 · **一处定形**）：
  url      更新源之根（`http(s)://…/` · **唯目录** ⇒ 件名由清单定）；
  channel  通道（内测 ＝ `internal` ／ 后 `beta` ／ `stable`）—— **客户端只取本通道**（⛔ 跨档）；
  provider `generic`（静态文件 · 内测 ／ 静态桶）｜`github`（Releases）｜`oss`（后扩）。
优先序（一处定形）：env ⇒ 文件 `update_source.yaml` ⇒ 内置默认；**逐次报「源」（`origin`）**。
⚠ ⛔ 出网 · ⛔ 取件（本模块唯「读声明」—— 取件 ／ 校验 ／ 替换归甲-P0 之器）。

以何形调用（判通 ／ 断须附）：
  python -X utf8 -B -m pytest tests/unit/test_update_source_1629.py -q
"""
from __future__ import annotations

import io
import os

#: 声明之相对径（**一处定形**）—— 居 `config/`（与仓内余配置同族 ∧ **入包**：根级 yaml ⛔ 入 `_payload_files`）
FILENAME = u"config/update_source.yaml"

#: 内置默认（**一处定形**）—— 内测之分享面（局域网点 · 承 pm_1626 §一.2⒜）；
#: ⚠ 外测 ／ 公网 ⇒ 改文件（⛔ 改码）。
DEFAULT_URL = u"http://192.168.3.11:8800/"
DEFAULT_CHANNEL = u"internal"
DEFAULT_PROVIDER = u"generic"

#: env 之覆（**一处定形**）：env ⇒ 文件 ⇒ 默认。
ENV = {u"url": u"PA_UPDATE_URL", u"channel": u"PA_UPDATE_CHANNEL", u"provider": u"PA_UPDATE_PROVIDER"}
KEYS = (u"url", u"channel", u"provider")


def root_dir():
    u"""装根 ／ 仓根（**一处定形**）：本档 ＝ `<根>/core/lib/update_source.py` ⇒ 上溯三。"""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def path(root=None):
    return os.path.join(root or root_dir(), FILENAME)


def _mini_yaml(text):
    u"""极简解析（唯「键: 值」之平表 ＋ `#` 注）—— 免依 PyYAML 之回落（装根之 runtime 无其依时）。
    ⚠ 本器**唯读三键**；嵌套 ／ 列表 ⇒ 报「⛔ 解」（⛔ 猜 —— 承「真读数」）。
    """
    out = {}
    for ln in (text or u"").splitlines():
        s = ln.strip()
        if (not s) or s.startswith(u"#"):
            continue
        if u":" not in s:
            return None
        k, v = s.split(u":", 1)
        k = k.strip()
        v = v.strip()
        if u"#" in v:
            v = v.split(u"#", 1)[0].strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in (u'"', u"'"):
            v = v[1:-1]
        out[k] = v
    return out


def _from_file(root):
    u"""文件之三键 ⇒ `(dict, note)`；未见 ／ 坏 ⇒ `({}, 因)`（⛔ 静默）。"""
    p = path(root)
    if not os.path.isfile(p):
        return {}, u"未见 %s" % FILENAME
    try:
        text = io.open(p, encoding=u"utf-8-sig").read()
    except Exception as e:                                    # noqa: BLE001 — 照实报因
        return {}, u"%s 读取败：%s: %s" % (FILENAME, type(e).__name__, e)
    d = None
    try:
        import yaml                                           # type: ignore
        d = yaml.safe_load(text)
    except Exception:                                         # noqa: BLE001 — 无 yaml ∨ 解析败 ⇒ 回落
        d = None
    if not isinstance(d, dict):
        d = _mini_yaml(text)
    if not isinstance(d, dict):
        return {}, u"%s ⛔ 解（唯平表「键: 值」）" % FILENAME
    return {k: d.get(k) for k in KEYS if d.get(k) not in (None, u"")}, u""


def load(root=None, env=None):
    u"""更新源之「一处出」⇒ `{url, channel, provider, origin, file, note}`。
    `origin` 逐键记其出（`env` ／ `file` ／ `default`）—— 承「切源 ⛔ 须重出包」之证。
    """
    env = os.environ if env is None else env
    fd, fnote = _from_file(root)
    out = {}
    origin = {}
    for k in KEYS:
        e = (env.get(ENV[k]) or u"").strip()
        if e:
            out[k] = e
            origin[k] = u"env:%s" % ENV[k]
        elif fd.get(k):
            out[k] = str(fd[k])
            origin[k] = u"file:%s" % FILENAME
        else:
            out[k] = {u"url": DEFAULT_URL, u"channel": DEFAULT_CHANNEL,
                      u"provider": DEFAULT_PROVIDER}[k]
            origin[k] = u"default"
    if out[u"channel"] not in (u"internal", u"beta", u"stable"):
        fnote = (fnote + u"；" if fnote else u"") + u"通道非常（%s —— 唯 internal ／ beta ／ stable）" % out[u"channel"]
    url = out[u"url"]
    if not (url.startswith(u"http://") or url.startswith(u"https://")):
        fnote = (fnote + u"；" if fnote else u"") + u"url 非 http(s)（%s）" % url
    out[u"origin"] = origin
    out[u"file"] = path(root)
    out[u"note"] = fnote
    return out


def manifest_url(src):
    u"""清单之取处（**一处定形**）—— `url` 之尾缀 `/` 后接清单之名（甲-P0 之器唯用此）。"""
    return (src.get(u"url") or u"").rstrip(u"/") + u"/" + u"update_manifest.json"


def package_url(src, name):
    u"""包之取处（**一处定形**）—— ⛔ 本模块另拼（防二处漂）。"""
    return (src.get(u"url") or u"").rstrip(u"/") + u"/" + str(name).lstrip(u"/")
