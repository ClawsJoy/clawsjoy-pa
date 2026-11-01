# -*- coding: utf-8 -*-
"""PA 路由 · env_providers 簇（②v1 拆件 · 由 gateway_routes.py 机械切出 · 15 条路由＋DSH 运行时 2）。

共享面唯 `pa_routes_common`（`bp` 唯彼处建）；本件 ⛔ 复建蓝图。
⭐ 导入即挂：件末 `register(bp)`；endpoint 名仍 `pa_routes.<func>`（⛔ 变）。
"""

import os
from flask import request, current_app
from core.pa import _proc as _proc
from core.pa.pa_routes_common import bp, ok, err
from core.pa.pa_routes_common import (
    _code_sha16, _data_dir, _loopback, err,
    ok,
)


def _web_root():
    """与 ``core/web/health.py`` 的 ``send_from_directory("web", ...)`` **同源**：
    Flask 把相对目录解析到 ``app.root_path``。⛔ 不另发明路径口径。"""
    try:
        from flask import current_app

        return os.path.join(current_app.root_path, "web")
    except Exception:
        return os.path.join(os.getcwd(), "web")


def _frontend_build(filename="pa.html"):
    """**前端构建指纹**（2026-09-30 · PM 批）：回答「你手上这份页面是哪一版」。

    为什么必须由**服务端现算**：⛔ 页面不能内嵌自身 sha16（改了字节指纹必变 ⇒ 内嵌＝自欺）。
    所以指纹按 **服务端实际发出去的那份** ``web/<filename>`` 现读现算，页面只负责显示。
    现场（09-30）：「😵 服务暂不可用」的归属之争就卡在「两版页面无法区分」
      —— 现盘 ``web/pa.html`` 那句出现 0 次（结构上不可能产出），而 PM 手上的页面产出过它。
    ⛔ 本函数只做读数，不参与任何判定。
    """
    p = os.path.join(_web_root(), filename)
    out = {"path": os.path.abspath(p), "exists": os.path.exists(p)}
    if not out["exists"]:
        return out
    try:
        import hashlib as _hl
        import time as _tm

        with open(p, "rb") as f:
            b = f.read()
        out["bytes"] = len(b)
        out["sha16"] = _hl.sha256(b).hexdigest()[:16]
        out["mtime"] = _tm.strftime("%Y-%m-%d %H:%M:%S", _tm.localtime(os.path.getmtime(p)))
    except Exception as e:
        out["error"] = "%s: %s" % (type(e).__name__, e)
    return out


def register(bp):
    """把本簇之路由挂到共享蓝图 `pa_routes`（endpoint 名 ⛔ 变）。"""
    def _pa_route_count():
        """本网关自身路由之**读数**（唯数 · ⛔ 硬编）。"""
        try:
            return len([r for r in current_app.url_map.iter_rules()
                        if str(r.endpoint).startswith("pa_routes.")])
        except Exception:
            return None

    def _fed_boot():
        from core.gateway.boot_progress import boot_progress
        return boot_progress.snapshot()

    def _fed_version():
        try:
            from core.lib import build_info
            _d, _n = build_info.read(None)
            return (_d or {}).get("version")
        except Exception:
            return None

    def _fed_port():
        try:
            from core.lib import port_config
            return port_config.gateway_port()
        except Exception:
            return None

    @bp.route("/v9/pa/update", methods=["POST"])
    def pa_update_run():
        u"""更新之「动」（承 pm_1684 §四 契约 · 一处定形）。

        体 `{"action": "start"}` ⇒ 起一支（**幂等**：已在跑 ⇒ 回 `running` ∧ ⛔ 起第二支）；
        体 `{"action": "status"}` ∨ 缺 ⇒ **唯读**（⛔ 副作用 —— 面之轮询用之）。
        回 `{ok, phase, note, note_why, …}`；`phase ∈ idle ／ running ／ done ／ failed`。
        ⚠ `idle` ＝ 本席之补（pm_1684 之枚举唯三；「未曾跑」须有一值 —— 空 ⛔ 混 缺）。
        唯本机（⛔ 外网）；正式期须**一次性令牌** —— 复用 `provider_keys` 之形（**记债**）。
        器之状**落盘**（`core/lib/update_run.py`）⇒ 跨「停 → 换 → 起」可察终态
          （网关自停 ⇒ 其进程内 ⛔ 可察 ⇒ 唯盘上之态可读）。
        """
        import subprocess as _sp
        import sys as _sys

        from core.lib import update_run as _UR
        from core.lib import update_source as _US

        if not _loopback(request):
            return err("此端唯本机可用（来源 %s）" % (request.remote_addr or "?"), 403)
        body = request.get_json(silent=True) or {}
        act = str(body.get("action") or "status").strip().lower()
        if act not in ("start", "status"):
            return err("未知之 action：%s（唯 start ／ status）" % (act or "—"), 400)
        root = _US.root_dir()
        if act == "start" and _UR.phase(root).get("phase") != "running":
            _UR.begin(root)                                   # 起态先落 ⇒ 轮询即见 running
            # ⭐ pm_1799 §二.3⒜（**「停／起服务」归壳** · ⛔ 由页内后端自行停／起）：
            #   本端昔以默认之器起（其第 ⑥ 步停网关 · 第 ⑨ 步起 —— 而净机「起」⛔ 成 ⇒
            #   正控 ⛔ 过 ⇒ 回滚 ⇒ rc=2 ⇒ 页内「一键」恒败）。同机之 `fix-update2.cmd`
            #   唯多一个 `--no-restart` ⇒ **成** —— 两条路之**唯一**差别即此。
            #   ⇒ 今同其形：换完即止 ⇒ 页显「已就位 · 请关窗重开」（生效归壳之「重启服务」）。
            #   ⚠ 由之要：**停／起之能归壳**（生命周期是壳之物）⇒ 后端 ⛔ 越俎自停自起。
            argv = [_sys.executable, u"-X", u"utf8", u"-B",
                    os.path.join(root, u"scripts", u"win_pa", u"pa_update.py"),
                    u"--root", root, u"--go", u"--json", u"--no-restart"]
            # 起法与 `pa_nowindow.cmd_start` 同族（`NO_WINDOW ｜ DETACHED ｜ BREAKAWAY`）：
            #   器须**后于**调用者而存。昔之由为「第 ⑥ 步停网关」；今路已改 `--no-restart`
            #   ⇒ 仍留此旗者：老板若于更新**中途关窗** ⇒ 器亦须⛔ 随之亡（序未完 ⇒ 半成品）。
            # pm_1791 §三.3：⛔ 于调用处手写 `creationflags` —— 旗唯 `_proc`
            #   一处定形（`_proc.DETACH_FLAGS` · 承「窗隐唯 `_proc` 出口」）。
            # ⚠ 流之 `DEVNULL` **非「弃其真因」**（pm_1799 §二.2）：器**自落**其全部输出
            #   （`<upd_dir>/log-<目标版>.txt` · `pa_update._Sink`）⇒ 端弃不掉它；
            #   且 ⛔ 宜以「不读之管道」接之（器之输出可溢 ⇒ 器自阻）。
            try:
                _proc.popen_detached(argv, cwd=root, stdin=_sp.DEVNULL,
                                     stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
            except OSError:                                   # BREAKAWAY ⛔ 许（本进程在 job 中）⇒ 退
                try:
                    _proc.popen_hidden(argv, cwd=root, stdin=_sp.DEVNULL,
                                       stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
                except Exception as _e_up:                    # noqa: BLE001 — 照实报因
                    _UR.finish(root, rc=2, note_why=u"%s: %s" % (type(_e_up).__name__, _e_up))
                    return err("起器⛔ 成：%s" % _e_up, 500)
        return ok(_UR.phase(root), 印=_code_sha16(pa_update_run, _UR))

    @bp.route("/v9/pa/version", methods=["GET"])
    def pa_version():
        u"""本机之版本元数据 ＋ 更新源之声明（只读 · 唯此一处出）。"""
        from core.lib import build_info as _bi
        from core.lib import update_source as _us
        _s = _us.load()
        return ok({"build": _bi.report(),
                   "source": {"url": _s["url"], "channel": _s["channel"],
                              "provider": _s["provider"], "origin": _s["origin"],
                              "file": _s["file"], "note": _s["note"]},
                   "manifest_url": _us.manifest_url(_s)},
                  印=_code_sha16(pa_version, _bi, _us))

    @bp.route("/v9/pa/providers", methods=["GET"])
    def pa_providers():
        """模型供应商注册表（只读）。"""
        from core.pa.providers import public_view
        from core.pa import providers as _PV

        return ok(public_view(), 印=_code_sha16(pa_providers, _PV))

    @bp.route("/v9/pa/runtime/status", methods=["GET"])
    def pa_runtime_status():
        u"""引擎真实状态：Ollama / localm / DSH（只读探活 · ⛔ 失败即照实报）。"""
        from core.pa import runtime_status as _RS

        return ok(_RS.runtime_view(), 印=_code_sha16(pa_runtime_status, _RS))

    @bp.route("/v9/pa/benchmark", methods=["POST"])
    def pa_benchmark():
        u"""本机引擎 benchmark：TTFT / tok/s / VRAM（唯本机 · 失败照实报）。"""
        if not _loopback(request):
            return err("此端唯本机可用（来源 %s）" % (request.remote_addr or "?"), 403)
        from core.pa import benchmark as _BM
        body = request.get_json(silent=True) or {}
        engine = str(body.get("engine") or "").strip().lower()
        if engine not in ("ollama", "localm"):
            return err("engine 须为 ollama 或 localm", 400)
        model = str(body.get("model") or "").strip() or None
        if model:
            from core.pa.providers import resolve_model_ex as _rm
            _m, _why = _rm(model)
            if not _m:
                return err(_why, 400)
            model = _m
        try:
            out = _BM.run(engine, model=model,
                          prompt=str(body.get("prompt") or "")[:2000] or None,
                          max_tokens=max(1, min(int(body.get("max_tokens") or 64), 128)),
                          timeout=max(30, min(int(body.get("timeout") or 180), 600)))
            return ok(out, 印=_code_sha16(pa_benchmark, _BM))
        except Exception as e:
            return err("benchmark 失败：%s" % type(e).__name__, 500)

    @bp.route("/v9/pa/harness/runs", methods=["GET"])
    def pa_harness_runs():
        u"""DSH 任务卡：canonical RunRecord ＋ task/events sidecar。"""
        from core.pa import harness_face as _HF
        try:
            return ok(_HF.list_runs(limit=request.args.get("limit") or 20))
        except Exception as e:
            return err("取 harness runs 失败：%s" % type(e).__name__, 500)

    @bp.route("/v9/pa/harness/run", methods=["POST"])
    def pa_harness_run():
        u"""显式跑一次 DSH headless（唯本机 · 同步等待完成）。"""
        if not _loopback(request):
            return err("此端唯本机可用（来源 %s）" % (request.remote_addr or "?"), 403)
        from core.pa import harness_face as _HF
        from core.pa.harness.dsh import DshUnavailable
        body = request.get_json(silent=True) or {}
        task = str(body.get("task") or "").strip()
        if not task:
            return err("task 为空", 400)
        try:
            out = _HF.run_dsh(task, cwd=str(body.get("cwd") or ""),
                              timeout=body.get("timeout") or 120)
            return ok(out)
        except DshUnavailable as e:
            return err("DSH 未接：%s" % e, 503)
        except ValueError as e:
            return err(str(e), 400)
        except Exception as e:
            return err("harness run 失败：%s" % type(e).__name__, 500)

    @bp.route("/v9/pa/providers/key/token", methods=["GET"])
    def pa_provider_key_token():
        """一次性令牌之领（唯本机 · ⛔ 值上屏 —— 唯 Cookie · HttpOnly · SameSite=Strict）。"""
        from core.pa import provider_keys as _PK

        if not _loopback(request):
            return err("此端唯本机可领（来源 %s）" % (request.remote_addr or "?"), 403)
        tok, ttl = _PK.issue_token()
        r = ok({"issued": True, "expires_in": ttl, "cookie": _PK.TOKEN_COOKIE,
                "用": "唯同源 POST /v9/pa/providers/key（Cookie 自带 · 用即焚）"},
               印=_code_sha16(pa_provider_key_token, _PK))
        r.set_cookie(_PK.TOKEN_COOKIE, tok, max_age=int(ttl), path=_PK.TOKEN_PATH,
                     httponly=True, samesite="Strict")
        return r

    @bp.route("/v9/pa/providers/key", methods=["POST"])
    def pa_provider_key():
        """供应商密钥之 落 / 清（承 pm_1613 令四）。唯本机 ＋ 一次性令牌；⛔ 回值（唯布尔 ＋ 面）。"""
        from core.pa import provider_keys as _PK
        from core.pa.providers import PROVIDERS, key_state

        if not _loopback(request):
            return err("此端唯本机可用（来源 %s）" % (request.remote_addr or "?"), 403)
        body = request.get_json(silent=True) or {}
        pid = str(body.get("provider") or "").strip()
        p = PROVIDERS.get(pid)
        if not p:
            return err("无此供应商：%s（见 GET /v9/pa/providers）" % (pid or "—"), 400)
        env_name = p.get("key_env")
        if not env_name:
            return err("此供应商 ⛔ 需密钥（key_env 缺 —— 如本机 Ollama）", 400)
        okc, why = _PK.consume_token(request.cookies.get(_PK.TOKEN_COOKIE))
        if not okc:
            return err("鉴权⛔：%s" % why, 403)
        raw = body.get("key")
        if raw is None or not str(raw).strip():
            okc, face = _PK.clear_key(env_name)
            act = "cleared"
        else:
            okc, face = _PK.set_key(env_name, raw)
            act = "set"
        if not okc:
            return err("密钥⛔ 落：%s" % face, 400)
        _st = key_state(pid)
        r = ok({"provider": pid, "key_env": env_name, "action": act,
                "key_state": _st, "key_configured": (_st == "configured"), "落": face},
               印=_code_sha16(pa_provider_key, _PK))
        r.delete_cookie(_PK.TOKEN_COOKIE, path=_PK.TOKEN_PATH)
        return r

    @bp.route("/v9/pa/env", methods=["GET"])
    def pa_env():
        """PA 之「工位清单」（**只读**四栏）。⛔ 写任何一侧（承 kb_mapping N1–N6）。"""
        from core.pa import env_face as E

        out = E.build_env(route_count=_pa_route_count())
        try:
            out["scheduler"] = E.ensure_scheduler()
        except Exception as _se:
            out["scheduler"] = {"enabled": False, "error": type(_se).__name__}
        out["印"] = _code_sha16(pa_env, E)
        return ok(out)

    @bp.route("/v9/pa/env/note", methods=["GET"])
    def pa_env_note():
        """PA 自己的**工作笔记**（只读 · 侦察之产物 ＋ 实测刻）。"""
        from core.pa import env_face as E

        try:
            _n = int(request.args.get("n") or 20)
        except Exception:
            _n = 20
        _d = E.notes_face(limit=_n, full=bool(request.args.get("full")))
        _d["印"] = _code_sha16(pa_env_note, E)
        return ok(_d)

    @bp.route("/v9/pa/env/research", methods=["POST"])
    def pa_env_research():
        """触发一次**只读**侦察（⛔ 无写副作用 · ⛔ 唯只读工具）；**前后对表**自证。"""
        from core.pa import env_face as E

        r = E.research(route_count=_pa_route_count())
        try:
            r["scheduler"] = E.ensure_scheduler()
        except Exception as _se:
            r["scheduler"] = {"enabled": False, "error": type(_se).__name__}
        return ok(r)

    @bp.route("/v9/pa/build", methods=["GET"])
    def pa_build_get():
        """**前端构建指纹**（PM 2026-09-30 批）：页面自报「我是哪一版」。

        判据（PM）：页面能报自身构建 sha16 **且**探针读数必带它 ⇒ 消灭「两版页面无法区分」
        的归属之争。⛔ 指纹取自**服务端实际发出的那份文件**，不是页面自报的常量。
        """
        r = ok(dict(_frontend_build(request.args.get("file") or "pa.html"), 印=_code_sha16(pa_build_get)))
        try:
            r.headers["Cache-Control"] = "no-store"
        except Exception:
            pass
        return r

    @bp.route("/v9/pa/diagnostics", methods=["POST"])
    def pa_diagnostics_build():
        """一键诊断包（**唯落本机** · ⛔ 上传）：version ＋ 装根清单 ＋ 日志尾 ＋ health ＋ 环境。"""
        from core.pa import diagnostics as _dg
        data = request.get_json(silent=True) or {}
        snap = data.get("health") if isinstance(data.get("health"), dict) else None
        if snap is None:
            try:
                snap = {"boot": _fed_boot(), "version": _fed_version()}
            except Exception:
                snap = None
        try:
            zp, rows = _dg.build(port=_fed_port(), health=snap)
        except Exception as _e:
            return err("打包失败：%s: %s" % (type(_e).__name__, _e), 500)
        for _r in rows:
            print(_r)
        return ok({"pack": zp, "bytes": __import__("os").path.getsize(zp),
                   "members": _dg.members(zp), "uploaded": False,
                   "hint": "唯落本机；由你自己决定交给谁（⛔ 自动上传）"})

    @bp.route("/v9/pa/sys/snapshot", methods=["GET"])
    def pa_sys_snapshot():
        """七面之合体（一屏 ＝ 一次取）。`?fresh=1` ⇒ 真扫（有界）。"""
        if not _loopback(request):
            return err("本机体检唯本机可用（⛔ 远机）", 403)
        from core.pa import sys_face as _sf
        _fresh = str(request.args.get("fresh") or "").strip() in ("1", "true", "yes")
        out = _sf.snapshot(fresh=_fresh)
        out["印"] = _code_sha16(pa_sys_snapshot, _sf)
        return ok(out)

    @bp.route("/v9/pa/sys/<panel>", methods=["GET"])
    def pa_sys_panel(panel):
        """单面之盘（`disk ／ disk_c ／ windows ／ startup ／ perf ／ net ／ guard`）。"""
        if not _loopback(request):
            return err("本机体检唯本机可用（⛔ 远机）", 403)
        from core.pa import sys_face as _sf
        pid = str(panel or "").strip()
        if pid not in _sf.PANELS:
            return err("⛔ 未识之面：%s（白名单：%s）"
                       % (pid, " ／ ".join(_sf.PANELS)), 400)
        _fresh = str(request.args.get("fresh") or "").strip() in ("1", "true", "yes")
        out = _sf.build(pid, fresh=_fresh)
        out["印"] = _code_sha16(pa_sys_panel, _sf)
        return ok(out)

    @bp.route("/v9/pa/sys/act", methods=["POST"])
    def pa_sys_act():
        """本机管理之一处入口（唯本机 · ⛔ 远机 403 · ⛔ 出机）。"""
        if not _loopback(request):
            return err("本机管理唯本机可用（⛔ 远机）", 403)
        from core.pa import sys_act as _sa
        _b = request.get_json(silent=True) or {}
        out = _sa.act(act=_b.get("act"), target=_b.get("target"),
                      dry_run=_b.get("dry_run", True), token=_b.get("token") or "",
                      axis=str(_b.get("axis") or "sys"), data_dir=_data_dir())
        if not out.get("ok"):
            return err(out.get("因") or "⛔ 未成", int(out.get("code") or 400))
        # ⚠ 用 `器印`（⛔ `印`）—— 顶层之 `印` 是**预案之印**（绑 token）· ⛔ 覆。
        out["器印"] = _code_sha16(pa_sys_act, _sa)
        return ok(out)

    # P3-1：DSH 外部运行时检测（设置向导之真状态；⛔ 读/打印 key）
    def _dsh_runtime_state():
        import json as _json
        import shutil as _shutil
        import subprocess as _sp

        data_dir = _data_dir()
        saved_path = ""
        try:
            _sf = os.path.join(data_dir, "dsh_path.json")
            with open(_sf, encoding="utf-8") as fh:
                _doc = _json.load(fh)
            saved_path = str((_doc or {}).get("path") or "").strip()
        except Exception:  # noqa: BLE001
            saved_path = ""
        candidates = []
        env_path = str(os.environ.get("PA_DSH_PATH") or "").strip()
        if env_path:
            candidates.append((env_path, "env"))
        if saved_path:
            candidates.append((saved_path, "saved"))
        which_path = _shutil.which("dsh")
        if which_path:
            candidates.append((which_path, "which"))
        path = ""
        source = "none"
        for cand, src in candidates:
            try:
                if cand and os.path.isfile(cand):
                    path = os.path.abspath(cand)
                    source = src
                    break
            except Exception:  # noqa: BLE001
                continue
        found = bool(path)
        version = None
        if found:
            try:
                proc = _sp.run([path, "--version"], timeout=5, capture_output=True,
                               text=True, encoding="utf-8", errors="replace")
                raw = (proc.stdout or proc.stderr or "").strip()
                version = raw.splitlines()[0].strip() if raw else None
            except Exception:  # noqa: BLE001
                version = None
        return {
            "found": found,
            "path": path or None,
            "version": version,
            "source": source,
            "key_present": bool(os.environ.get("DEEPSEEK_API_KEY")),
            "cloud_supported": True,
            "local_supported": False,
            "install_steps": [
                "安装 Node.js（≥18）",
                "npm install -g @deepseek-ai/dsh",
                "dsh --version 验证",
                "在设置页填入 dsh 路径（或设 PA_DSH_PATH）",
            ],
            "node_present": bool(_shutil.which("node")),
        }

    @bp.route("/v9/pa/runtimes/dsh", methods=["GET"])
    def pa_dsh_runtime_get():
        """DSH 运行时之探测：env PA_DSH_PATH → 保存 → which；找不到 found:false（⛔ 抛）。"""
        return ok(_dsh_runtime_state())

    @bp.route("/v9/pa/runtimes/dsh/path", methods=["POST"])
    def pa_dsh_runtime_path_post():
        """保存用户指定的 dsh 路径（原子写）；坏路径 400；保存后立即 probe。"""
        import json as _json

        body = request.get_json(silent=True) or {}
        raw = str(body.get("path") or "").strip()
        if not raw or not os.path.isfile(raw):
            return err("dsh_path_not_found", 400)
        if os.name != "nt":
            try:
                if not os.access(raw, os.X_OK):
                    return err("dsh_path_not_executable", 400)
            except Exception:  # noqa: BLE001
                return err("dsh_path_not_executable", 400)
        path = os.path.abspath(raw)
        try:
            os.makedirs(_data_dir(), exist_ok=True)
            dst = os.path.join(_data_dir(), "dsh_path.json")
            tmp = dst + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                _json.dump({"path": path}, fh, ensure_ascii=False)
            os.replace(tmp, dst)
        except Exception as exc:  # noqa: BLE001
            return err("dsh_path_save_failed: " + type(exc).__name__, 500)
        return ok(_dsh_runtime_state())

    return bp


register(bp)
