# -*- coding: utf-8 -*-
"""PA 路由 · decision_perm 簇（②v1 拆件 · 由 gateway_routes.py 机械切出 · 10 条路由）。

共享面唯 `pa_routes_common`（`bp` 唯彼处建）；本件 ⛔ 复建蓝图。
⭐ 导入即挂：件末 `register(bp)`；endpoint 名仍 `pa_routes.<func>`（⛔ 变）。
"""

import logging
import os
from flask import jsonify, request
from core.lib.paths import vault_root
logger = logging.getLogger(__name__)
from core.pa.pa_routes_common import bp, ok, err
from core.pa.pa_routes_common import (
    _code_sha16, _core, _data_dir, _loopback,
    err, ok, pa_vault_state_code, vault_env_override,
)


def _permission_grant_provenance(data_dir):
    """**权限档的来源面**（2026-09-30 · PM 裁定「丙 的更严形态」）。

    只回答一件事：**盘上到底有没有真授予文件**。
    ⛔ 不参与任何判定（谁放行仍由既有代码判）；⛔ 不改 level 语义。
    为什么加：`permission.json` 与 `boss_grant.json` **都不存在**时，
    前端只拿得到 ``level``＝默认值 ⇒ 「默认值假装成读数」（与 437 假绿同族）。

    两处授予（语义不同，⛔ 不合并）：
      · ``pa``  —— PA 侧 ``permission.json``（本路由的生效值来源）
      · ``pes`` —— 执行侧 ``boss_grant.json``（PES 老板级，路径取 core.pes 的默认值，不另发明）
    """
    # 给**绝对**路径：相对路径会带上调用方的 CWD（且分隔符混用），人拿去找不到文件
    pa = os.path.abspath(os.path.join(data_dir, "permission.json"))
    try:
        from core.pes.authorization import DEFAULT_BOSS_PATH as _boss
        pes = str(_boss)
    except Exception:
        pes = os.path.join("data", "v9", "pes", "boss_grant.json")
    return {
        "pa": {"path": pa, "exists": os.path.exists(pa)},
        "pes": {"path": pes, "exists": os.path.exists(pes)},
    }


def register(bp):
    """把本簇之路由挂到共享蓝图 `pa_routes`（endpoint 名 ⛔ 变）。"""
    @bp.route("/v9/pa/proxy", methods=["POST"])
    def pa_proxy():
        """PA 调用本地灵犀服务(3890)的【唯一入口】—— 强制经过端点分级门。

        为什么必须走这里: 2026-09-10 我用脚本对每个候选路径盲发 POST {},
        其中 POST /kv/clear 无参数即清空全部 → 插件配置库 8 条全灭。
        现在起 PA 不允许直连 3890; 一切经本路由, 由 endpoint_guard 分级:
          只读 -> 放行 / 写 -> 放行并记账 / 破坏性 -> 需在场授权 / 未登记非 GET -> 默认拒绝
        """
        import json as _json

        from core.pa import endpoint_guard as G

        try:
            p = request.json
        except Exception as _e_body:
            return err("proxy: body 不是合法 JSON（%s）" % type(_e_body).__name__)
        if p is None:
            p = {}
        if not isinstance(p, dict):
            return err("proxy: body 需要 JSON 对象（拿到 %s）" % type(p).__name__)
        method = (p.get("method") or "GET").upper()
        path = (p.get("path") or "").strip()
        body = p.get("body")
        user_id = p.get("user_id") or ""
        if not path:
            return err("proxy 需要 path")

        # /mcp/call 按 body.name(工具名) 分级, 其余端点按路径分级(见 endpoint_guard)
        _mcp_tool = (body or {}).get("name") if isinstance(body, dict) else None
        allowed, level, reason = G.check(method, path, user_id, body)
        # 记账(含被拒): 谁在什么时候想动什么, 必须可追溯
        try:
            pa = _core(user_id)
            _ev = {"method": method, "path": path, "level": level, "allowed": bool(allowed), "reason": reason}
            if _mcp_tool:
                _ev["mcp_tool"] = _mcp_tool
            pa.events.append("fact", "proxy_call", _ev, source="pa/proxy")
        except Exception:
            pass
        if not allowed:
            return jsonify({"ok": False, "error": reason, "blocked_by": "endpoint_guard", "level": level}), 403

        base = os.getenv("LINGXI_PROXY_BASE", "http://127.0.0.1:3890")
        url = base.rstrip("/") + path
        try:
            import urllib.request

            headers = {"Content-Type": "application/json"}
            # token 从插件 KV 现取(read 级), 避免硬编码
            try:
                _kv = urllib.request.urlopen(base.rstrip("/") + "/kv/all", timeout=5)
                _tok = (_json.loads(_kv.read().decode("utf-8")) or {}).get("items", {}).get("wpsAiMcpBridgeToken")
                if _tok:
                    headers["Authorization"] = "Bearer " + str(_tok)
            except Exception:
                pass
            data = None
            if method in ("POST", "PUT", "PATCH"):
                data = _json.dumps(body if body is not None else {}).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=float(p.get("timeout", 20))) as resp:
                raw = resp.read().decode("utf-8", "replace")
                try:
                    parsed = _json.loads(raw)
                except Exception:
                    parsed = {"raw": raw[:2000]}
                return ok({"level": level, "status": resp.status, "data": parsed})
        except urllib.error.HTTPError as e:
            try:
                _b = _json.loads(e.read().decode("utf-8", "replace"))
            except Exception:
                _b = {"raw": ""}
            # N2b：⛔ 不用 str(<例外>) —— 只回上游 HTTP 状态行（e.code ／ e.reason），无内部对象 ／ 类名
            return jsonify({"ok": False, "level": level, "status": e.code,
                            "error": "上游返回 %s %s" % (e.code, e.reason), "data": _b}), e.code
        except Exception as e:
            # N2b：⛔ 异常原文不回客户端（详情只落服务端日志）
            logger.error("proxy 调用失败: %s", type(e).__name__)
            return err("proxy 调用失败（内部错误，已记日志）")

    @bp.route("/v9/pa/proxy/gate", methods=["GET"])
    def pa_proxy_gate():
        from core.pa import endpoint_guard as G

        _d = G.gate_state(request.args.get("user_id") or "")
        _d["印"] = _code_sha16(pa_proxy_gate, G)
        return ok(_d)

    @bp.route("/v9/pa/proxy/approve", methods=["POST"])
    def pa_proxy_approve():
        """老板在场授权破坏性端点(会话级, 默认 30 分钟)。"""
        from core.pa import endpoint_guard as G

        p = request.json or {}
        if p.get("revoke"):
            return ok(G.revoke(p.get("user_id") or ""))
        r = G.approve_destructive(
            p.get("user_id") or "", p.get("path"), float(p.get("ttl_s") or 1800), p.get("note") or ""
        )
        try:
            _core(p.get("user_id")).events.append("fact", "proxy_approve", {"paths": r.get("paths")}, source="pa/proxy")
        except Exception:
            pass
        return ok(r)

    @bp.route("/v9/pa/vault/sync", methods=["POST"])
    def pa_vault_sync():
        """账本 -> Obsidian(待办/站会/未读索引)。vault 路径可用 env PA_VAULT_DIR 覆盖。"""
        from core.pa.vault_brain import BrainSync

        pa = _core((request.json or {}).get("user_id"))
        _vr = vault_root()
        vault = os.getenv("PA_VAULT_DIR") or (str(_vr) if _vr is not None else None)
        if not vault:
            return err("vault 未接（选目录）：env PA_VAULT_DIR ∨ 配置 paths.vault_root ∨ "
                       "内置 <data_root>/kb 皆无 —— 请先在「首启引导／设置」里选知识库目录")
        brain_sync = BrainSync(pa.ledger, vault_dir=vault)
        out = {
            "ledger_md": brain_sync.sync_ledger(),
            "unread": brain_sync.unread_index(),
            "standup": brain_sync.daily_standup(),
        }
        return ok(out)

    @bp.route("/v9/pa/decision", methods=["POST"])
    def pa_decision():
        """老板拍板: 采纳/小改/大改/退回/暂缓 → 写 decision_log.json。"""
        from core.pa.decision import DECISIONS, DecisionStore

        p = request.json or {}
        decision = (p.get("decision") or "").strip()
        if decision not in DECISIONS:
            return err("decision 必须是: %s" % "/".join(DECISIONS))
        ds = DecisionStore(_data_dir())
        rec = ds.record(
            p.get("user_id"),
            p.get("session_id"),
            p.get("node"),
            p.get("stage"),
            decision,
            p.get("note") or "",
            p.get("task") or "",
        )
        try:
            _core(p.get("user_id")).events.append(
                "fact",
                "pa_decision",
                {"decision": decision, "node": p.get("node"), "stage": p.get("stage")},
                source="pa/decision",
            )
        except Exception:
            pass
        return ok({"decision": rec})

    @bp.route("/v9/pa/decision/log", methods=["GET"])
    def pa_decision_log():
        r"""拍板之 log（只读）。⭐ T2-刀19-补 §二：**按用途分栏** —— 默认 `decisions` 唯**业务**。

        ⛔ 删行：`验收 ／ 自检 ／ 测试`之拍板另栏 `nonbusiness`（照录 · 各带 `用途之由`）。
        `?include_nonbusiness=1` ⇒ 全量（⛔ 破既有键：`decisions` ／ `count` 皆在）。
        """
        from core.pa.decision import DecisionStore, usage_of, split_by_usage

        ds = DecisionStore(_data_dir())
        _rows = ds.list(request.args.get("user_id"), request.args.get("session_id"))
        for _r in _rows:
            _u, _m = usage_of(_r)
            _r["用途"] = _u
            _r["用途之由"] = (_m or u"（无命中词）")
        _biz, _nb = split_by_usage(_rows)
        _inc = str(request.args.get("include_nonbusiness") or "").strip().lower() in ("1", "true", "yes", "on")
        _d = {"decisions": (_rows if _inc else _biz),
              "count": len(_rows if _inc else _biz),
              "nonbusiness": _nb, "nonbusiness_count": len(_nb), "all_count": len(_rows),
              "业务之最新": (_biz[-1] if _biz else None),
              "用途之判据": u"`task ／ note ／ session_id` 含「验收 ／ 自检 ／ 复验 ／ 探针 ／ 测试 ／ e2e ／ canary …」⇒ 非业务",
              "面之径逐字": str(ds.path), "store": str(ds.path),
              "收件人面之指": u"拍板来源之读面 ＝ 本面（默认唯业务）",
              "verdict": ("有拍板记录" if _rows else "无拍板动作发生 ⇒ 空（不适用，非故障）")}
        # ⭐ T2-刀26 §二（PM 裁 17:57 · 下批）：**印须载器之真源** —— 本面之**分栏数**出 `core/pa/decision.py` ⇒ 器 ＝ sha16(路由源 ＋ decision 模块源)
        from core.pa import decision as _D
        _d["印"] = _code_sha16(pa_decision_log, _D)
        return ok(_d)

    @bp.route("/v9/pa/permission", methods=["GET"])
    def pa_permission_get():
        from core.pa.permission import PermissionStore
        from core.pa import permission as _PM

        ps = PermissionStore(os.path.join(_data_dir(), "permission.json"))
        return ok({"level": ps.get(), "grant": _permission_grant_provenance(_data_dir())}, 印=_code_sha16(pa_permission_get, _PM))

    @bp.route("/v9/pa/grants", methods=["GET"])
    def pa_grants_get():
        u"""`list_grants()` 之只读面（PM 3407 §一 ／ PM 3433 §一 正形）。

        判据四条（§二）：⒈ 环回 ⇒ `200` ＋ `list_grants()`；⒉ 非环回 ⇒ `403`
        （承 `_loopback` 现例 · 前端无 token ⇒ ⛔ token 判据）；⒊ 坏件 ⇒ `409`
        （fail-closed · ⛔ `200` 空表）；⒋ 四态可分（`state ∈ active ／ none ／
        missing ／ corrupt`）。

        ⭐ PM `3433 §一` **正形**：**读面 ⛔ 用 `403`** —— `active` ／ `none` ／
        `missing` 皆 `200` ＋ `ok:true` ＋ `state` ＋ `count`（`missing` ⇒ `count=0`）；
        `corrupt` ⇒ `409`。`403` 只归**授权路径**（`is_granted(...)` 于 `missing` 恒 `False`）
        与**非环回**。

        ⛔ 写：新增 ／ 撤销授权归 D2（本批只读）。
        """
        from core.pa import grants as _G

        if not _loopback(request):
            return err(u"此端唯本机可用（来源 %s）" % (request.remote_addr or "?"), 403)
        _st = _G.load_state()
        if _st["state"] == _G.STATE_CORRUPT:
            # ⭐ 坏件 ⇒ 409（fail-closed · ⛔ 以 `200` 空表冒充 —— 与 `permission.py` 已修之
            #   「损坏即放宽」同族）。⚠ 读面无 `403`：`missing` 是**合法初态**（老板未启用）。
            return jsonify({"ok": False, "state": _st["state"], "count": 0, "grants": [],
                            "source": _st["source"], "captured_at": _st["captured_at"],
                            "error": u"grants.yaml 坏件（fail-closed）：%s" % _st["error"]}), 409
        try:
            _items = _G.list_grants()
        except _G.GrantsCorrupt as _e:
            return jsonify({"ok": False, "state": _G.STATE_CORRUPT, "count": 0, "grants": [],
                            "source": _st["source"], "captured_at": _st["captured_at"],
                            "error": u"grants.yaml 坏件（fail-closed）：%s" % _e}), 409
        return ok({"state": _st["state"], "count": len(_items), "grants": _items,
                   "source": _st["source"], "captured_at": _st["captured_at"]},
                  印=_code_sha16(pa_grants_get, _G))

    @bp.route("/v9/pa/relations/status", methods=["GET"])
    def pa_relations_status():
        u"""外联脚手架 · **只读状态面**（T121）：本机可读；非环回 403 owner_required；⛔ token。

        返回 version ＋ 证据账 30 天保鲜 verify 摘要（⛔ 写账 ／ ⛔ 改账；bad ／ superseded 照实）。
        """
        if not _loopback(request):
            return jsonify({"ok": False, "error": "owner_required",
                            "message": u"此端唯本机可用（来源 %s）"
                                       % (request.remote_addr or "?")}), 403
        from core.lib.version import __version__
        from core.pa import evidence_ledger as EL

        ledger_path = str(EL.default_ledger_path())
        try:
            got = EL.verify(ledger_path, max_age_days=30)
        except Exception as exc:                             # noqa: BLE001
            logger.error("relations/status verify 失败: %s", type(exc).__name__)
            return jsonify({"ok": False, "error": "ledger_verify_failed",
                            "version": str(__version__), "source": ledger_path}), 500
        ledger_ok = bool(got.get("ok"))
        # T126：外层 ok **等于**账之 ok（账坏 ⇒ false；HTTP 仍 200 只读，照实报）
        return jsonify({"ok": ledger_ok,
                        "version": str(__version__),
                        "ledger": {"ok": ledger_ok,
                                   "total": int(got.get("total") or 0),
                                   "bad": got.get("bad") or [],
                                   "superseded": got.get("superseded") or [],
                                   "max_age_days": 30},
                        "source": ledger_path})

    @bp.route("/v9/pa/verify/legacy_7_2", methods=["GET"])
    def pa_verify_legacy_7_2():
        u"""G3 legacy 7+2 **只读**面（T128 · 老板批新路径 D-11b）。

        唯本机（环回）；非环回 403 owner_required（⛔ token）；唯 GET。调产品包
        `core.pa.legacy_verify_face.run_legacy_7_2()`，face 7/0/2（⛔ 9/9 ／ ⛔ 14/14）；
        旧 `/v9/pa/verify` 仍 404（本路由 ⛔ 占旧径）；⛔ 写账。
        """
        if not _loopback(request):
            return jsonify({"ok": False, "error": "owner_required",
                            "message": u"此端唯本机可用（来源 %s）"
                                       % (request.remote_addr or "?")}), 403
        from core.lib.version import __version__
        from core.pa import legacy_verify_face as LV

        try:
            doc = LV.run_legacy_7_2()
        except Exception as exc:                             # noqa: BLE001
            logger.error("verify/legacy_7_2 运行失败: %s", type(exc).__name__)
            return jsonify({"ok": False, "error": "legacy_7_2_failed",
                            "version": str(__version__)}), 500
        face = str(doc.get("face") or "")
        npass = int(doc.get("pass") or 0)
        nfail = int(doc.get("fail") or 0)
        nna = int(doc.get("na") or 0)
        profile_ok = (face == "legacy_7_2" and (npass, nfail, nna) == (7, 0, 2))
        return jsonify({"ok": bool(profile_ok), "version": str(__version__),
                        "face": face, "pass": npass, "fail": nfail, "na": nna,
                        "results": doc.get("results") or []})

    @bp.route("/v9/pa/permission", methods=["POST"])
    def pa_permission_post():
        """老板在场改权限档。只认白名单值; PA 无工具触达本路由, 直写被 ForbiddenGuard 拦。"""
        from core.pa.permission import PermissionStore

        p = request.json or {}
        ps = PermissionStore(os.path.join(_data_dir(), "permission.json"))
        r = ps.set(p.get("level"), p.get("user_id") or "")
        if not r.get("ok"):
            return err(r.get("error"))
        try:
            _core(p.get("user_id")).events.append(
                "fact", "permission_change", {"level": r["level"]}, source="pa/permission"
            )
        except Exception:
            pass
        return ok(r)

    @bp.route("/v9/pa/vault/set", methods=["POST"])
    def pa_vault_set():
        u"""⭐ 甲 · 件一（pm_1520 §二.1）：**选一个笔记目录** ⇒ 立库根（`paths.vault_root`）—— **唯一写端**。

        体：`{"path": "<绝对径>"}`（⇒ 立之）｜`{"path": ""}`（⇒ **清** ⇒ 落回内置空库 ／ 未接）。
        校：**在 ∧ 可写**（⛔ 静默收）｜**幂等**（同值 ⇒ `changed:false` · ⛔ 报错）。
        回：`{ok, vault_root, vault_root_src, state, at, changed, env_override, note}`；
        错：`{ok:false, error:"<逐字>"}`（前端唯渲 · ⛔ 自编）。
        ⛔ 写非库根之物 ／ ⛔ 起停 ／ ⛔ 平台动作。
        """
        from time import strftime as _stf
        _p = request.get_json(silent=True)
        if not isinstance(_p, dict) or "path" not in _p:
            return jsonify({"ok": False,
                            "error": u'体须为 {"path": "<\u7edd\u5bf9\u5f84>"} ∨ {"path": ""}'}), 400
        _raw = _p.get("path")
        if not isinstance(_raw, str):
            return jsonify({"ok": False, "error": u"path 须为字符串"}), 400
        _s = _raw.strip()
        try:
            from core.lib.unified_config import unified_config as _uc
            if _s == "":
                _r = _uc.set_and_save("paths.vault_root", "")
            else:
                if not os.path.isabs(_s):
                    return jsonify({"ok": False, "error": u"径须为绝对径：%s" % _s}), 400
                _ap = os.path.abspath(_s)
                if not os.path.isdir(_ap):
                    return jsonify({"ok": False, "error": u"径不存在 ／ 非目录：%s" % _ap}), 400
                if not os.access(_ap, os.W_OK):
                    return jsonify({"ok": False, "error": u"径不可写：%s" % _ap}), 400
                _r = _uc.set_and_save("paths.vault_root", _ap)
        except Exception as _e:
            logger.error("vault/set 内部错误: %s: %s", type(_e).__name__, str(_e)[:200])
            return jsonify({"ok": False,
                            "error": u"写配置失败：%s: %s" % (type(_e).__name__, str(_e)[:160])}), 500
        from core.lib import paths as _P
        _vr = _P.vault_root()
        _src = _P.vault_root_src()[1]
        _code = pa_vault_state_code(root=(str(_vr) if _vr else None))[0]
        _on, _note = vault_env_override()
        return jsonify({
            "ok": True, "at": _stf("%Y-%m-%d %H:%M:%S"),
            "changed": bool(_r.get("changed")),
            "path": _s, "file": _r.get("file"), "backup": _r.get("backup"),
            "vault_root": (str(_vr) if _vr else None),
            "vault_root_src": _src, "state": _code,
            "env_override": _on, "note": _note,
        })

    return bp


register(bp)
