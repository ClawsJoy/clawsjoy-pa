# -*- coding: utf-8 -*-
u"""PA 路由 · registry 簇（PA v1.1 S2a · 只读端 `GET /v9/pa/registry`）。

【本件解决什么】PA v1.1 之 Agents 只读面须**一处**取到全量注册表：20 卡 ＋
counts（total ／ active ／ pending）＋ 源刻。真源 ＝ `data/tmp/pa_registry_pilot_v2.json`
（试点册：20 卡 · active 2 · pending 18）；本件 ⛔ 另造卡 ／ ⛔ 改源 ／ ⛔ 写盘。

【判据】
  · 200 ／ 只读（唯 GET · ⛔ 凭据）· counts 逐卡实点（⛔ 手写 20/2/18）；
  · 源缺 ／ 空 ／ 坏 ⇒ **仍 200** ＋ `state` ＋ `error` 显因 ＋ counts 全 0 ＋ cards 空（⛔ 假卡）；
  · pending ⛔ 可派：每卡 `dispatchable` ＝ (status == "active")（只读之据 · 真派发另受门禁）；
  · 卡字段按**白名单**出（⛔ 整件透传 ⇒ 日后源内新增之敏感键 ⛔ 外泄）。

共享面唯 `pa_routes_common`（`bp` 唯彼处建）；本件 ⛔ 复建蓝图。
⭐ 导入即挂：件末 `register(bp)`；endpoint 名仍 `pa_routes.<func>`（⛔ 变）。
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

from flask import jsonify

from core.lib.paths import ws_root
from core.pa.pa_routes_common import bp

logger = logging.getLogger(__name__)

REGISTRY_ROUTE = "/v9/pa/registry"

PILOT_BASENAME = "pa_registry_pilot_v2.json"

PILOT_REL = ("data", "tmp", PILOT_BASENAME)

#: 装包内之**seed 册**（v1.1.2 补：payload 无 `data/tmp` ⇒ Agents 面 0 卡）。
#: 源序：env ⇒ 仓根 data/tmp ⇒ **config/pa seed** ⇒ 数据根 ⇒ 工作区 ⇒ cwd。
PILOT_SEED_REL = ("config", "pa", PILOT_BASENAME)

REGISTRY_SOURCE_ENV = "PA_REGISTRY_PILOT"

# 卡之**必出**字段（源内缺 ⇒ 值 None；⛔ 丢键 —— 面侧照实渲不必判无）。
CARD_CORE_FIELDS = (
    "id", "kind", "name", "class", "status",
    "control_plane", "view", "access_level",
)

# 卡之**可选**字段（源内有且非 None 方出；history_* ／ session_* 即在此列）。
CARD_OPT_FIELDS = (
    "view_cmd", "provider", "capabilities", "boundary", "fragility", "cost",
    "invoke", "probe", "verified", "approved_by", "approved_at", "status_now",
    "cwd", "probe_at", "probe_ok", "enriched_at", "fallbacks", "known_issue",
    "history_view", "history_session_id", "history_session_bytes",
    "history_map", "session_format", "note", "approval_ref",
)


def _repo_root():
    u"""仓根（本件 `core/pa/` 之上两级）—— 与 cwd 无关。"""
    return Path(__file__).resolve().parents[2]


def _pilot_candidates():
    u"""候径之序：① env 明指（⛔ 再回落 —— 缺即缺） ② 仓根 ③ seed ④ 数据根 ⑤ 工作区根 ⑥ cwd。"""
    raw = (os.environ.get(REGISTRY_SOURCE_ENV) or "").strip()
    if raw:
        return [Path(raw)]
    out = [_repo_root().joinpath(*PILOT_REL), _repo_root().joinpath(*PILOT_SEED_REL)]
    try:
        from core.lib.config_helper import get_data_root

        out.append(Path(get_data_root()).joinpath("tmp", PILOT_BASENAME))
    except Exception:
        pass
    root = ws_root()
    if root:
        out.append(Path(root).joinpath(*PILOT_REL))
    out.append(Path.cwd().joinpath(*PILOT_REL))
    uniq, seen = [], set()
    for p in out:
        key = str(p)
        if key not in seen:
            seen.add(key)
            uniq.append(p)
    return uniq


def _pilot_path():
    u"""现用之源径：首个真存在者；皆无 ⇒ 首候（供 `source` 照实显「缺于何处」）。"""
    cands = _pilot_candidates()
    for p in cands:
        try:
            if p.is_file():
                return p
        except OSError:
            continue
    return cands[0]


def _source_label(path):
    u"""源之显名：仓内 ⇒ 相对径（⛔ 全机绝对径）；仓外 ⇒ 原径（照实）。"""
    try:
        return path.resolve().relative_to(_repo_root()).as_posix()
    except Exception:
        return str(path)


def _iso_mtime(path):
    u"""源之刻（文件 mtime 之 ISO 8601 · 带本机时区）；取不到 ⇒ None（⛔ 伪刻）。"""
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds")
    except Exception:
        return None


def _empty_counts():
    return {"total": 0, "active": 0, "pending": 0}


def _counts(cards):
    u"""counts ＝ 逐卡**实点**（⛔ 手写常量 · 承「数不可自拟」）。"""
    return {
        "total": len(cards),
        "active": sum(1 for c in cards if c.get("status") == "active"),
        "pending": sum(1 for c in cards if c.get("status") == "pending"),
    }


def _shape_card(raw):
    u"""单卡白名单成形（⛔ 整件透传）；status 非 active ⇒ `dispatchable` False（pending ⛔ 可派）。"""
    if not isinstance(raw, dict):
        return None
    card = {k: raw.get(k) for k in CARD_CORE_FIELDS}
    for k in CARD_OPT_FIELDS:
        if k in raw and raw[k] is not None:
            card[k] = raw[k]
    card["dispatchable"] = (str(raw.get("status") or "") == "active")
    return card


def build_registry(source=None):
    u"""成形只读回执（⛔ 写盘 · ⛔ 起源）。source 缺 ⇒ 按候径之序取。

    恒返 dict：`generated_at` ／ `source` ／ `counts` ／ `cards` ／ `state` ／
    `error` ／ `readonly` ／ `ok`。源缺 ／ 空 ／ 坏时 cards ⛔ 补（⛔ 以空卡冒充「有册」），
    `ok` 为 False 且 `error` 显因 —— 唯 HTTP 仍 200（读端 ⛔ 500）。
    """
    path = Path(source) if source is not None else _pilot_path()
    doc = {
        "ok": True,
        "generated_at": None,
        "source": _source_label(path),
        "state": "missing",
        "error": None,
        "counts": _empty_counts(),
        "cards": [],
        "readonly": True,
    }
    try:
        exists = path.is_file()
    except OSError:
        exists = False
    if not exists:
        doc["ok"] = False
        doc["error"] = "registry_source_missing"
        doc["message"] = u"试点册未找到：%s（⛔ 以空卡冒充 · 待源就位）" % doc["source"]
        return doc
    doc["generated_at"] = _iso_mtime(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        doc["ok"] = False
        doc["state"] = "invalid"
        doc["error"] = "registry_source_invalid"
        doc["message"] = u"试点册不可解析：%s: %s" % (type(exc).__name__, str(exc)[:120])
        return doc
    if not isinstance(raw, list):
        doc["ok"] = False
        doc["state"] = "invalid"
        doc["error"] = "registry_source_not_list"
        doc["message"] = u"试点册须为卡之列表（今 %s）" % type(raw).__name__
        return doc
    cards = [_shape_card(x) for x in raw]
    cards = [c for c in cards if c is not None]
    doc["cards"] = cards
    doc["counts"] = _counts(cards)
    doc["state"] = "ok" if cards else "empty"
    return doc


def register(bp):
    u"""把本簇之路由挂到共享蓝图 `pa_routes`（endpoint 名 ⛔ 变）。"""
    @bp.route("/v9/pa/registry", methods=["GET"])
    def pa_registry():
        u"""GET /v9/pa/registry —— 只读：pilot 册之 20 卡 ＋ counts ＋ 源刻。

        ⛔ 写盘 · ⛔ 凭据；源缺 ／ 空 ／ 坏 ⇒ 200 ＋ `state` ／ `error`（⛔ 假卡 · ⛔ 500）。
        """
        try:
            doc = build_registry()
        except Exception as exc:  # 只读端 ⛔ 500：显因而空
            logger.error("pa_registry 内部错误: %s: %s", type(exc).__name__, str(exc)[:200])
            doc = {
                "ok": False,
                "generated_at": None,
                "source": "",
                "state": "invalid",
                "error": "registry_internal_error",
                "message": u"registry 读端内部错误（已记日志）",
                "counts": _empty_counts(),
                "cards": [],
                "readonly": True,
            }
        return jsonify(doc)

    return bp


register(bp)
