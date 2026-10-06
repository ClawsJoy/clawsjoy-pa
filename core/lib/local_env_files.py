# -*- coding: utf-8 -*-
u"""本机「可选引导件」（`config/.env` ／ `config/secrets.yaml`）之**缺 ⇒ 跳读 ＋ 显形**处。

**一处定形**（承 pm_1453 §一 之裁）：此二件在**交付包内必无**
（`.gitignore` 之 `.env` ／ `config/.env` ／ `config/secrets.yaml`；
`scripts/win_pa/make_client_bundle.py` 之 `EXCLUDE` 含 `config/secrets.yaml`）
⇒ 其「缺」＝ **常形**（⛔ 例外）⇒ 凡读此二件者 **须**：

  ⒈ **缺 ⇒ 跳读**（⛔ 崩）—— ⛔ 各自复述 `open`：本机一手逮得之实缺陷
     ＝ ``agent_gateway_enhanced.py`` 于 ``load_dotenv``（**容缺**）之后**无条件**
     再 ``open(_env_path)`` ⇒ 净机 ``FileNotFoundError`` @ **import 期**
     （``main`` 之 try ／ except **捕不到**）⇒ 进程立死。
  ⒉ **显形**（「未配」⟷「已配」须有字 · ⛔ 静默缺 —— 承「空 ≠ 缺」）。

⚠ 本模块**唯读**：⛔ 建件 ／ ⛔ 改件 ／ ⛔ 回内容（唯「在／缺」之态 ＋ 布尔）。
"""
import os

#: 相对树根之径（**一处定形** —— ⛔ 各写一遍字面）
ENV_REL = "config/.env"
SECRETS_REL = "config/secrets.yaml"

#: 「态」之二值（承 pm_1453 §一.1：「未配」⟷「配了」须分）
STATE_ON = u"已配"
STATE_OFF = u"未配"

#: 缺之显形之辞（**逐字** —— 一页纸 ／ 首屏 ／ 报 皆引此）
MISSING_NOTE = u"未配（正常 —— 交付包里本来就没有这一件 · 缺则跳读）"


def present(path):
    u"""在？—— ⛔ 抛（`None` ／ 空 ⇒ False）。"""
    return bool(path) and os.path.isfile(path)


def state(path):
    u"""唯读之态：`{在, 态, 径}`（⛔ 内容 · ⛔ 值）。"""
    _ok = present(path)
    return {"在": _ok, "态": (STATE_ON if _ok else STATE_OFF), "径": (path or None)}


def read_lines(path):
    u"""逐行（**缺 ⇒ `[]` · ⛔ 崩**）。

    ⚠ 编码 `utf-8-sig`（有 BOM 亦通）＋ `errors='replace'`
      ⇒ 半个坏字 ⛔ 拖死起服（承「⛔ 以崩代显形」）。
    """
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as _f:
            return _f.read().splitlines()
    except (IOError, OSError):
        return []


def has_proxy_line(path):
    u"""`.env` 里有没有 `HTTP(S)_PROXY=` 行（**缺 ⇒ False** · ⛔ 崩）。"""
    for _ln in read_lines(path):
        if _ln.startswith("HTTP_PROXY=") or _ln.startswith("HTTPS_PROXY="):
            return True
    return False


def local_files_state(root):
    u"""二件之态（**首屏显形**之用 —— 承 pm_1453 §一.4）。逐项必附「判」（⛔ 裸态）。"""
    out = []
    for _rel, _name, _why in (
            (ENV_REL, u"本机配置（.env）", u"云端密钥 ／ 代理 等本机设置之落处"),
            (SECRETS_REL, u"供应商密钥（secrets.yaml）", u"模型供应商密钥（演示走云端时用）")):
        _p = os.path.join(root, *_rel.split("/"))
        _st = state(_p)
        out.append({"件": _rel, "名": _name, "义": _why, "在": _st["在"],
                    "态": _st["态"], "径": _st["径"],
                    "判": u"包内必无此件 ⇒ 缺＝常形（⛔ 故障）· 缺则跳读（⛔ 崩）· 有则照读"})
    return out