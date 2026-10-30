# -*- coding: utf-8 -*-
"""PA 路由 · dispatch_flow 簇（②v1 拆件 · 由 gateway_routes.py 机械切出 · 16 条路由）。

共享面唯 `pa_routes_common`（`bp` 唯彼处建）；本件 ⛔ 复建蓝图。
⭐ 导入即挂：件末 `register(bp)`；endpoint 名仍 `pa_routes.<func>`（⛔ 变）。
"""

import os
import time
from flask import jsonify, request
from core.pa import _proc as _proc
from core.pa.pa_routes_common import bp, ok, err
from core.pa.pa_routes_common import (
    _code_sha16, _core, _data_dir, err,
    ok,
)


import sys


from core.lib.paths import cmd_exe, org_enabled, path_forms, vault_root, ws_root


_REPO_AGENT_CLIENT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts", "agent_client"
)


def _local_client_dir():
    """客户端目录(模块级常量, 页面无法改): 唯仓库内 scripts/agent_client。

    ⭐ 2026-10-06（pm_1409 §二.3 · 批三）：旧桌面回落（Windows 用户桌面之**字面径**）⇒ **删**
    （开发机专用 · 承「开发期／我方通道 ⇒ 删」）。缺 ⇒ 空串 ⇒ `local_client_launchable()`
    判不可启动（⛔ 崩 · 照实「未接」）。
    """
    return _REPO_AGENT_CLIENT if os.path.isdir(_REPO_AGENT_CLIENT) else ""


def _local_client_ws_url():
    """WS 目标 = browser_local.ws_port()（端口唯一真源）。

    不在这里复述端口号：两处各写一个数字时，改一处就会把客户端静默指到旧端口
    （Windows 副本实测: 5007 不可绑，且是 WSL 实例的端口 ⇒ 本机动作有发到 WSL 网关的风险）。
    取不到 ⇒ 返回空串（fail-loud：宁可启不起，不静默连错）。
    """
    try:
        from core.lib.v8.browser_local import ws_port as _wp

        return "ws://127.0.0.1:%d" % _wp()
    except Exception:
        return ""


def _client_python():
    u"""客户端之 pythonw（⛔ 字面开发机径）。

    env `PA_CLIENT_PYTHON` ⇒ 用；缺 ⇒ 自 `sys.executable` 之邻 `pythonw.exe` 推（**产品级**）；
    再缺 ⇒ 空串（`local_client_launchable()` 判不可启动 · 照实「未接」）。
    """
    _v = (os.environ.get("PA_CLIENT_PYTHON") or "").strip()
    if _v:
        return _v
    try:
        _c = os.path.join(os.path.dirname(sys.executable or ""), "pythonw.exe")
        return _c if os.path.exists(_c) else ""
    except Exception:
        return ""


LOCAL_CLIENT = {
    "cmd_exe": cmd_exe(),
    "win_dir": _local_client_dir(),
    "win_python": _client_python(),
    "script": "agent_client.py",
    "ws": _local_client_ws_url(),
    "extra_args": ["--chrome"],
}


LOCAL_CLIENT_COOLDOWN_S = 15.0


LOCAL_CLIENT_GUARD = {"ts": 0.0}  # 模块级（可测：单测直接重置它）


def local_client_launchable():
    """能不能一键启动：Windows 侧 cmd.exe 与 agent_client.py 都在（**未观察到 ≠ 可用**）。"""
    try:
        _script = os.path.join(LOCAL_CLIENT["win_dir"], LOCAL_CLIENT["script"])
        return bool(os.path.exists(LOCAL_CLIENT["cmd_exe"])) and bool(os.path.exists(_script))
    except Exception:
        return False


def local_client_command(user_id):
    """构造启动命令（**唯一出口**：单测断言它不接受任何请求侧字符串）。"""
    return [
        LOCAL_CLIENT["cmd_exe"],
        "/c",
        "start",
        "",
        "/D",
        LOCAL_CLIENT["win_dir"],
        LOCAL_CLIENT["win_python"],
        LOCAL_CLIENT["script"],
        "--user-id",
        str(user_id),
        "--ws",
        LOCAL_CLIENT["ws"],
    ] + list(LOCAL_CLIENT["extra_args"])


def register(bp):
    """把本簇之路由挂到共享蓝图 `pa_routes`（endpoint 名 ⛔ 变）。"""
    @bp.route("/v9/pa/local_client/status", methods=["GET"])
    def pa_local_client_status():
        uid = request.args.get("user_id") or ""
        info = {"connected": False, "client": ""}
        try:
            from core.lib.v8 import browser_local as _bl

            info = _bl.get_connection_info(uid)
        except Exception as _e_info:
            info = {"connected": False, "client": "", "error": str(_e_info)[:200]}
            _bl = None
        out = dict(info)
        out["launchable"] = local_client_launchable()
        out["印"] = _code_sha16(pa_local_client_status) if _bl is None else _code_sha16(pa_local_client_status, _bl)
        return ok(out)

    @bp.route("/v9/pa/local_client/start", methods=["POST"])
    def pa_local_client_start():
        """一键启动 Windows 侧 agent_client（命令硬编码；页面只能传 user_id）。"""
        import subprocess
        import time as _time

        data = request.get_json(silent=True) or {}
        uid = str(data.get("user_id") or request.args.get("user_id") or "")
        if not uid.startswith("web_"):
            return err("user_id 非法（只允许 web_* 本机用户）", 400)
        try:
            from core.lib.v8 import browser_local as _bl

            _info = _bl.get_connection_info(uid)
        except Exception:
            _info = {"connected": False}
        if _info.get("connected"):
            return ok({"started": False, "already": True, "client": _info.get("client", "")})
        now = _time.time()
        _last = float(LOCAL_CLIENT_GUARD.get("ts") or 0)
        if now - _last < LOCAL_CLIENT_COOLDOWN_S:
            return ok({"started": False, "cooldown": round(LOCAL_CLIENT_COOLDOWN_S - (now - _last), 1)})
        if not local_client_launchable():
            return err("Windows 侧客户端不可启动：cmd.exe 或 agent_client.py 未找到", 500)
        cmd = local_client_command(uid)
        try:
            _proc.popen_hidden(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as _e_start:
            return err("启动失败：%s" % _e_start, 500)
        LOCAL_CLIENT_GUARD["ts"] = now
        print("[PA_LOCAL_CLIENT] 已请求启动桌面 agent_client user=%s（参数硬编码，未接受前端输入）" % uid)
        return ok({"started": True, "hint": "已在 Windows 侧启动；等 5~20 秒，状态会自动变为已连接"})

    @bp.route("/v9/pa/dispatch", methods=["POST"])
    def pa_dispatch():
        pa = _core((request.json or {}).get("user_id"))
        p = request.json or {}
        task = (p.get("task_text") or "").strip()
        if not task:
            return err("dispatch 需要 task_text")
        # ⭐ T2-刀1 ①②⑤（2026-10-05）：席轴 —— 收 shortId（亦认 name）⇒ 落 shortId；
        #   须能在席位册（`GET /v9/pa/roster?kind=seat`）查到；查不到 ⇒ **报错拒派**（⛔ 静默兜底）。
        to_seat_raw = str(p.get("to_seat") or "").strip()
        to_seat = ""
        if to_seat_raw:
            from core.pa.dispatch import resolve_seat

            to_seat = resolve_seat(to_seat_raw)
            if not to_seat:
                return err("to_seat 查不到该席：%s（席位册 ＝ GET /v9/pa/roster?kind=seat；"
                           "形 ＝ shortId（7 位 · 如 5c01a0f）· ⛔ UUID 前 8 位；⛔ 静默兜底）"
                           % to_seat_raw, 400)
        action = "dispatch_v9" if p.get("via_gateway") else "dispatch"
        r = pa.handle(action, {"task_text": task, "url": p.get("url"), "to_seat": to_seat})
        if r.get("ok") and to_seat:
            r["to_seat"] = to_seat
        return ok(r) if r.get("ok") else err(r.get("error"))

    @bp.route("/v9/pa/dispatch/receipt", methods=["POST"])
    def pa_dispatch_receipt():
        r"""收口回执（**拒未在册之 `task_id`** · 四段**只进不退** · ⛔ 静默兜底）。

        `{task_id, to_seat, 果, 印, stage, note}` ⇒ `{ok, task_id, stage, 回执四件}`。
        四段 ＝ 已派 ⇒ 已收 ⇒ 在做 ⇒ 已收口（每段有刻）。
        """
        from core.pa import receipts as _RC

        p = request.get_json(silent=True) or {}
        r = _RC.record(p.get("task_id"), p.get("to_seat") or "",
                       p.get("果") or p.get("result") or "", p.get("印") or p.get("stamp") or "",
                       stage=p.get("stage") or "已收", note=p.get("note") or "",
                       by=p.get("by") or p.get("from") or "")
        try:
            _core(p.get("user_id")).events.append(
                "fact", "dispatch_receipt",
                {"task_id": r.get("task_id"), "stage": r.get("stage"), "ok": r.get("ok"),
                 "印": r.get("印")}, source="pa/dispatch/receipt")
        except Exception:
            pass
        return ok(r) if r.get("ok") else err(r.get("error"), 400)

    @bp.route("/v9/pa/dispatch/receipt", methods=["GET"])
    def pa_dispatch_receipt_get():
        """回执只读面：`?task_id=` ⇒ 该件之四段 ＋ 逐段之刻 ＋ 催之数；不给 ⇒ 全表之态。"""
        from core.pa import receipts as _RC

        q = (request.args.get("task_id") or "").strip()
        try:
            lim = int(request.args.get("n") or 50)
        except Exception:
            lim = 50
        d = _RC.face(task_id=q or None, limit=lim)
        d["印"] = _code_sha16(pa_dispatch_receipt_get, _RC)
        return ok(d)

    @bp.route("/v9/pa/dispatch/chase", methods=["POST"])
    def pa_dispatch_chase():
        """催收一轮：`stage != 已收口` ∧ 距末次刻 > 阈 ⇒ 催**一次**（**限次** · 同路运输）。"""
        from core.pa import receipts as _RC

        p = request.get_json(silent=True) or {}
        r = _RC.chase(threshold_min=p.get("threshold_min"), max_n=p.get("max_n"),
                      dry=bool(p.get("dry")))
        r["印"] = _code_sha16(pa_dispatch_chase, _RC)
        return ok(r)

    @bp.route("/v9/pa/dispatch/history", methods=["GET"])
    def pa_dispatch_history():
        """派发历史读面。BUG-3 三态：rows 空 = 没有派发动作（不适用），不是接线坏了；
        故把判据（记录文件 ＋ 条数）一并给出，读面自己可复核。"""
        pa = _core(request.args.get("user_id"))
        r = pa.handle("dispatch_history")
        _all = r.get("rows") or []
        # ⭐ T2-刀1 ④（2026-10-05）：`?to_seat=` 筛（⛔ 破 `store`／`store_exists`／`count` 与三态判据）
        _want = (request.args.get("to_seat") or "").strip()
        _rows = [x for x in _all if str((x or {}).get("to_seat") or "") == _want] if _want else _all
        # ⭐ T2-刀4 缺之二：行之 `stage` **按四段真走**（＋ `stage_at`／`stage_src`／`chase_count`）
        try:
            from core.pa import receipts as _RC

            _RC.overlay_history(_rows)
        except Exception:
            pass
        r["rows"] = _rows
        r["to_seat"] = (_want or None)
        r["count"] = len(_rows)
        # ⭐ T2-刀9 §〇（2026-10-05 · PM 令）：**态数须真判据 ＋ 附滤**
        #   ⛔ 以**表长**充「等待外部结果」（表长 ⊃ 已终结 ∪ 无席位轴）——**假态**。
        _STAGES4 = ("已派", "已收", "在做", "已收口")
        _seat_rows = [x for x in _rows if str((x or {}).get("to_seat") or "").strip()]
        r["counts"] = {
            "rows": len(_rows),
            "seat_axis": len(_seat_rows),
            "no_seat_axis": len(_rows) - len(_seat_rows),
            "awaiting_receipt": len([x for x in _seat_rows if x.get("stage") != "已收口"]),
            "closed": len([x for x in _rows if x.get("stage") == "已收口"]),
            "by_stage": {s: len([x for x in _rows if x.get("stage") == s]) for s in _STAGES4},
        }
        r["判据"] = {
            "等待外部回执": "to_seat 非空 ∧ stage != 已收口",
            "已终结": "stage == 已收口（派时即已派 ⇒ 无回执者 ⛔ 计入等待）",
            "⛔": "表长 ≠ 等待数（表长 ⊃ 池路行 ＋ 已终结行）",
        }
        r["滤"] = {"面": str(pa.dispatch_rec.path), "式": "逐行谓词（见 判据）",
                  "过面": len(_rows), "印": _RC.RECEIPT_VERSION}
        r["count_all"] = len(_all)
        r["store"] = str(pa.dispatch_rec.path)
        r["store_exists"] = bool(pa.dispatch_rec.path.is_file())
        r["verdict"] = "有派发记录" if _all else "无派发动作发生 ⇒ 空（不适用，非故障）"
        if _want and not _rows:
            r["verdict"] = "无该席之派发（筛 to_seat=%s；面内共 %d 行）" % (_want, len(_all))
        # ⭐ T2-刀26 §二（PM 令 · 2026-10-05）：**面须附「刻」** —— 本面为**活面**（逐次读 dispatch.jsonl，逐次增行）
        #   ⇒ 补**取数刻** ＋ **面之径逐字** ＋ **刻之性**（⛔ 冻结面）＋ **印**（印须载器 · 承 PM 089 §二）。
        r["at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        r["刻之性"] = "读时（活面：本面逐次读 dispatch.jsonl ⇒ 数随刻变 · ⛔ 冻结面）"
        r["面之径逐字"] = str(pa.dispatch_rec.path)
        r["印"] = _code_sha16(pa_dispatch_history, _RC)
        return ok(r)

    @bp.route("/v9/pa/deliver/mail", methods=["POST"])
    def pa_deliver_mail():
        """**可查账的一步交付**：拍板闸（fail-closed）＋ 甲形限域 ＋ 幂等 ＋ 落痕 ＋ 回执四件 ＋ 人话。

        逻辑全在 ``core.pa.mailer.deliver``（纯函数 · 落地前可成对验收）；本路由只做包装。
        ⛔ 缺 ``decision_id`` ⇒ 403 ／ 重放同 ``task_id`` ⇒ 返既有回执（⛔ 重发）
        ／ 落到步 ✗ ⇒ 回执明写「停在哪一步 ＋ 报给谁」。⛔ 口令入屏 ／ 日志 ／ 回执 ／ 台账。
        """
        from core.pa import mailer as _mailer

        # ⭐ T2-刀20 §一：面须**暴露** `dry_run`（⛔ 唯函数参数 ⇒ 无干跑路 ⇒ 探针只能真发）。
        _p = request.json or {}
        _code, _doc = _mailer.deliver(_p, _data_dir(),
                                      dry_run=bool((_p or {}).get('dry_run')))
        # ⭐ T2-刀15 补③：**印须载器**（承 PM 089 §二）—— 器 ＝ 本路由之码之 `sha16`。
        #   ⛔ 载器 ⇒ 读者不知何版所出（半个印）；⛔ 器之印 ⛔ 得 ⇒ `null`（照实「未核」）。
        _c16 = _code_sha16(pa_deliver_mail, _mailer)
        _doc['印'] = _c16
        _rc = _doc.get('receipt')
        if isinstance(_rc, dict) and isinstance(_rc.get('成本'), dict):
            _rc['成本']['印'] = _c16
        return jsonify(_doc), _code

    @bp.route("/v9/pa/deliver/mail", methods=["GET"])
    def pa_deliver_mail_face():
        r"""发信面之**读面之指**（只读 · ⛔ 发信；⛔ 405 使人猜）。

        本面唯 `POST`（发信）；**核回执**须走 `GET /v9/pa/deliver/authz?task_id=`。
        """
        _d = {
            "面": u"交付·邮件（发信）",
            "动形": u"唯 POST（⛔ 无 GET 之发）",
            "用法": {
                "必填": ["task_id", "user_id", "to", "subject", "body_md", "decision_id"],
                "可选": ["in_reply_to", "src_letter", "stop_to"],
                "to 之形": u"**列表** ∨ **逗号分隔字符串**（`;` ／ `；` 亦可）—— 归一在闸之前",
                "回执四件": [u"回了什么", u"凭什么", u"花了多少", u"谁批的"],
            },
            "读面之指": [
                {"读什么": u"逐次授权留痕（含被拒之次）", "面": "GET /v9/pa/deliver/authz?task_id=<件号>",
                 "滤": "task_id ／ limit（默认 50）", "动形": "GET"},
                {"读什么": u"停手之留痕（`报给谁`）", "面": "POST /v9/pa/deliver/stop", "动形": "POST（写入面 · ⛔ 读）"},
                {"读什么": u"交付之台账（面之径逐字）", "面": "data\\v9\\pa\\deliver_authz.jsonl", "动形": "文件"},
            ],
            "判据": u"缺 `decision_id` ⇒ 403 ／ 收件人非本人 or 白名单 ⇒ 403 ／ 重放同 `task_id` ⇒ 返既有回执",
        }
        _d["印"] = _code_sha16(pa_deliver_mail_face)
        return ok(_d)

    @bp.route("/v9/pa/deliver/authz", methods=["GET"])
    def pa_deliver_authz():
        """逐次留痕（只读）：`?task_id=` 筛 ＋ `?limit=`（默认 50）。

        行形 ＝ `{件号, 谁批, 何刻, 授权形, decision_id, 果, 报给谁}`（⛔ 口令 ∴ ⛔ 入此）。
        """
        from core.pa import mailer as _mailer

        _u_raw = request.args.get("usage")
        if _u_raw and str(_u_raw).strip() and _mailer.norm_usage(_u_raw) is None:
            # ⭐ T2-刀21 §三：`usage` 未知 ⇒ **400 载 `allowed`**（⛔ 静默返 `0`）
            return jsonify({"ok": False, "error": u"usage 未知：%s" % str(_u_raw)[:40],
                            "allowed": sorted(_mailer.USAGE_ALIASES),
                            "missing": u"`usage` 之值须在 `allowed` 内"}), 400
        _d = _mailer.load_trail(_data_dir(), request.args.get("task_id"),
                                request.args.get("limit") or 50, usage=_u_raw)
        _d["滤"] = ("task_id=" + str(request.args.get("task_id"))) if request.args.get("task_id") else "无（全量 ／ 末 limit 行）"
        _d["滤"] += " ／ usage=" + str(request.args.get("usage") or "all")
        # ⭐ T2-刀26 §二（PM 令 2026-10-05 17:50）：**面之四键同形** —— 台账轴三面（history／authz／lines）一码读
        _d["at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        _d["刻之性"] = "读时（活面：本面逐次读 deliver_authz.jsonl ⇒ 数随刻变 · ⛔ 冻结面）"
        _d["印"] = _code_sha16(pa_deliver_authz, _mailer)
        return ok(_d)

    @bp.route("/v9/pa/deliver/stop", methods=["POST"])
    def pa_deliver_stop():
        """停手留痕：任一步过不去 ⇒ 停手并报（`报给谁` 恒有字段）。⛔ 静默。"""
        from core.pa import mailer as _mailer

        _d = _mailer.stop_trace(request.json or {}, _data_dir())
        _d["印"] = _code_sha16(pa_deliver_stop, _mailer)
        return ok(_d)

    @bp.route("/v9/pa/feedback/target", methods=["GET"])
    def pa_feedback_target():
        """落点之声明（**运维 ／ 机器之端** —— 承 pm_1640 §一.2 ／ §一.3：**面唯读 `/health`**）。
        ⚠ 其形**唯自** `feedback_target.face()` 出（与 `/health.feedback` **同一处** ⇒ ⛔ 二处各写）。
        """
        from core.lib import feedback_target as _ft
        return ok(_ft.face())

    @bp.route("/v9/pa/feedback", methods=["POST"])
    def pa_feedback_submit():
        """收件（题 ＋ 文 ＋ 附件 ＋ 逐项勾选）⇒ 落**本机**（⛔ 出机 · ⛔ 出站请求）。"""
        from core.pa import feedback_store as _fs
        data = request.get_json(silent=True) or {}
        try:
            fid, doc, rows = _fs.submit(None, data)
        except _fs.FeedbackError as _e:
            return err(str(_e), 400)
        except Exception as _e2:
            return err("收件失败：%s: %s" % (type(_e2).__name__, _e2), 500)
        for _r in rows:
            print(_r)
        return ok({"id": fid, "at": doc["at"], "state": doc["state"],
                   "attach_n": len(doc["attach"]), "consent": doc["consent"],
                   "outbound": doc["target"]["outbound"], "hint": "已存本机；内测期不联网发送"})

    @bp.route("/v9/pa/feedback", methods=["GET"])
    def pa_feedback_list():
        """取件之列（客服席 ／ 板之「我的留言」）—— 新者先 ∧ ⛔ 正文全载。"""
        from core.pa import feedback_store as _fs
        try:
            lim = int(request.args.get("limit") or 50)
        except Exception:
            lim = 50
        return ok({"items": _fs.list_items(None, limit=lim)})

    @bp.route("/v9/pa/feedback/<fid>", methods=["GET"])
    def pa_feedback_item(fid):
        """取件之全 ＋ 回话（照今日原型之黄框）。"""
        from core.pa import feedback_store as _fs
        it = _fs.read_item(None, fid)
        if it is None:
            return err("件 ⛔ 见（%s）" % str(fid)[:40], 404)
        return ok({"item": it})

    @bp.route("/v9/pa/feedback/<fid>/reply", methods=["POST"])
    def pa_feedback_reply(fid):
        """回话（**客服席之口**）⇒ 落 `回话.json` ⇒ 板上显（⛔ 另一体系）。"""
        from core.pa import feedback_store as _fs
        data = request.get_json(silent=True) or {}
        try:
            rows = _fs.write_reply(None, fid, data.get("text"), by=(data.get("by") or "客服席"))
        except _fs.FeedbackError as _e:
            return err(str(_e), 400)
        for _r in rows:
            print(_r)
        return ok({"id": str(fid), "replied": True})

    return bp


register(bp)
