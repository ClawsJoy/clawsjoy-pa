# -*- coding: utf-8 -*-
"""P3-A 启动块（从 agent_gateway_enhanced.py if __name__ 主体归位，2026-09-12）。"""
import json
import os
import threading as _threading
import time
from datetime import datetime
from pathlib import Path

from core.gateway.registry import _init_registries
from core.gateway.boot_progress import boot_progress, onnx_cache_path
from core.gateway.state_persist import _load_retrieval_cache, _persist_retrieval_cache
from core.lib.unified_config import unified_config


def _serve_http(app, port):
    u"""⭐ pm_1608 §二.2 ⒜「门先开」：HTTP 监听之唯一驻点（后台线程）。"""
    try:
        app.run(host="0.0.0.0", port=port, debug=False, threaded=True, use_reloader=False)
    except Exception as _e:
        print("[BOOT] ⛔ HTTP 监听异常终止：%s: %s" % (type(_e).__name__, _e), flush=True)


def _wait_listen(port, timeout=30.0):
    u"""有界等 127.0.0.1:port 可连（⛔ 长阻）：得 ⇒ 秒数；⛔ 得 ⇒ None。"""
    import socket

    _t0 = time.time()
    while time.time() - _t0 < timeout:
        _s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _s.settimeout(0.5)
        try:
            if _s.connect_ex(("127.0.0.1", port)) == 0:
                return round(time.time() - _t0, 3)
        finally:
            _s.close()
        time.sleep(0.05)
    return None


def run_gateway_startup(app):
    u"""P3-A 启动：**门先开**（监听先起）⇒ 重初始化（守卫 / SAG / 回填 / 队列 / 平台 / 浏览器）。"""

    # Windows 副本(2026-09-19): loopback 不得走代理。
    # 背景: config/.env:14-15 注入 HTTP_PROXY/HTTPS_PROXY=http://127.0.0.1:7890(Clash)。
    # 于是**本机**调用也被塞进代理 —— 实测 PA /v9/pa/proxy → 灵犀桥(3890) 报
    # "Remote end closed connection without response"，同一条路径在 WSL 侧不报。
    # 这里只补 loopback 的例外; 出网仍照旧走代理(不改变原有行为)。
    for _pk in ("NO_PROXY", "no_proxy"):
        _pv = os.environ.get(_pk, "")
        if "127.0.0.1" not in _pv:
            os.environ[_pk] = ",".join([x for x in (_pv, "127.0.0.1", "localhost", "::1") if x])

    # ⭐⭐ pm_1608 §二.2 ⒜（门先开 · 本件之的）：**HTTP 监听须先起**，重初始化（向量 ／ LLM ／ KB）
    #   一律在其后。旧序「重初始化 ⇒ app.run」令「门」被初始化堵住：净机首启须下向量模型
    #   （all-MiniLM-L6-v2 · ~79 MB）⇒ 数分钟不听端口 ⇒ 页面 ERR_CONNECTION_REFUSED（pm_1607 §〇）。
    #   今：监听先起（后台线程）⇒ 页面 ／ `/health` 即刻可答（`/health` 自报 status=starting）。
    boot_progress.begin(["http_listen", "registries", "guards", "kb",
                         "vector_model_download", "engine", "ready"])
    boot_progress.set_phase("http_listen")
    _port = unified_config.get("services.gateway.port", 5002)
    _door = _threading.Thread(target=_serve_http, args=(app, _port), daemon=False, name="gw-http")
    _door.start()
    _open_s = _wait_listen(_port, timeout=30.0)
    if _open_s is None:
        print("[BOOT] ⚠ 门 ⛔ 开（%s 于 30 s 内 ⛔ 可连）—— 重初始化续，然页面必 ⛔ 达（见下之数行）" % _port, flush=True)
    else:
        print("[BOOT] 门先开：HTTP 监听已起 http://127.0.0.1:%d/ （%.1f s）" % (_port, _open_s), flush=True)

    boot_progress.set_phase("registries")
    from core.lib.hook_manager import HookManager
    from core.lib.startup import startup_manager

    HookManager()
    startup_manager.start()
    try:
        _init_registries()
    except Exception as _e_reg:
        boot_progress.fail("重初始化失败（registry ／ 含向量模型准备）：%s" % _e_reg,
                           "见 logs 之 gateway_<port>_console.log；若为向量模型下载失败（断网）⇒ 联网后重启")
        print("[BOOT] ⛔ 重初始化失败：%s" % _e_reg, flush=True)
        raise
    boot_progress.set_phase("guards")
    # P1 S6: 挂载全局守卫(bridge_loop 用, 含审批/计划/越权)
    try:
        from core.gateway.guards.registry import mount_guards
        from core.os.context import get_v9_context

        mount_guards(get_v9_context())
    except Exception as _guard_mount_err:
        print(f"[GUARDS] 全局守卫挂载失败(不影响运行): {_guard_mount_err}")
    # R3/R4 注册说明书进 SAG（entity_type=manual，DB 不可用时静默降级）
    try:
        from core.lib.sag_audit_bridge import register_manual

        register_manual()
    except Exception:
        pass
    # H9 用户消息沙箱镜像历史回填：启动时补齐缺失（只补不删，幂等，>100 行差异才补）
    try:
        from pathlib import Path as _Path_b

        from core.gateway.archive import backfill_user_message_mirror

        _um_dir = _Path_b("data/v8/user_messages")
        if _um_dir.exists():
            for _um_f in _um_dir.glob("*.jsonl"):
                _sid_b = _um_f.stem
                if _sid_b:
                    backfill_user_message_mirror(user_id="web_1783219071801", session_id=_sid_b)
    except Exception as _bf_start_err:
        print(f"[USER_MSG_BACKFILL] 启动回填异常(忽略): {_bf_start_err}")
    # ===== #192 检索缓存持久化：启动恢复 + 进程退出落盘 =====
    _load_retrieval_cache()
    import atexit as _atexit

    _atexit.register(_persist_retrieval_cache)

    # ── 长线任务检查点恢复（后台线程，不阻塞网关启动）──
    def _recover_long_loop_checkpoint():
        try:
            from core.lib.v8.long_loop_state_machine import LongLoopStateMachine

            machine = LongLoopStateMachine.from_checkpoint()
            if machine is not None:
                print(f"[LONG_LOOP] 恢复未完成任务: {machine.task_id}")
        except Exception as _exc:
            print(f"⚠ 检查点恢复失败: {_exc}")

    _threading.Thread(target=_recover_long_loop_checkpoint, daemon=True).start()

    # ── #31 长线任务断点续跑：回收悬挂 running 任务 → pending（重启后队列重新拉取）──
    try:
        import time as _t31

        _recovered_tasks = []
        for _tf31 in Path("data/v8").glob("tasks_*.json"):
            try:
                _srv31 = _tf31.stem.replace("tasks_", "")
                _data31 = json.loads(_tf31.read_text(encoding="utf-8"))
                _dirty31 = False
                for _tid31, _task31 in _data31.get("tasks", {}).items():
                    if _task31.get("status") == "running":
                        _task31["status"] = "pending"
                        _task31["updated_at"] = _t31.strftime("%Y-%m-%dT%H:%M:%S")
                        _task31.setdefault("history", []).append(
                            {
                                "state": "pending",
                                "at": _t31.strftime("%Y-%m-%dT%H:%M:%S"),
                                "comment": "网关重启，悬挂 running 回收为 pending",
                            }
                        )
                        _recovered_tasks.append(f"{_srv31}:{_tid31}")
                        _dirty31 = True
                if _dirty31:
                    _tf31.write_text(json.dumps(_data31, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                continue
        if _recovered_tasks:
            print(f"[QUEUE_RECOVER] 回收悬挂 running 任务 → pending: {', '.join(_recovered_tasks)}")
    except Exception as _q31_exc:
        print(f"⚠ 任务队列恢复失败: {_q31_exc}")

    # ── P1-4 脏数据清理：空标题/超龄 pending 任务标记 failed（保留审计痕迹，不删除）──
    try:
        _stale_total = 0
        for _tf314 in Path("data/v8").glob("tasks_*.json"):
            try:
                _d314 = json.loads(_tf314.read_text(encoding="utf-8"))
                _dirty314 = False
                for _tid314, _task314 in _d314.get("tasks", {}).items():
                    if _task314.get("status") != "pending":
                        continue
                    _title314 = str(_task314.get("title", "") or "").strip()
                    _upd314 = _task314.get("updated_at", "") or _task314.get("created_at", "")
                    _age_days314 = 999
                    try:
                        _age_days314 = (time.time() - datetime.fromisoformat(_upd314).timestamp()) / 86400
                    except Exception:
                        pass
                    if not _title314 or _age_days314 > 7:
                        _task314["status"] = "failed"
                        _task314.setdefault("history", []).append(
                            {
                                "state": "failed",
                                "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                "comment": "脏数据清理：空标题或超龄未执行",
                            }
                        )
                        _stale_total += 1
                        _dirty314 = True
                if _dirty314:
                    _tf314.write_text(json.dumps(_d314, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                continue
        if _stale_total:
            print(f"[QUEUE_CLEAN] 标记 {_stale_total} 条脏数据任务为 failed（空标题/超龄 pending）")
    except Exception as _q314_exc:
        print(f"⚠ 任务脏数据清理失败: {_q314_exc}")

    port = _port  # 门先开时已取（一处定形 · pm_1608 §二.2 ⒜）
    # 平台连接：启动 PlatformClient
    try:
        from core.lib.platform_client import platform

        if platform.login():
            _subs = platform.fetch_subscriptions()
            print(f"✅ 平台连接成功，已订阅 {len(_subs)} 个 Agent")
        else:
            print("ℹ 平台未配置或离线，本地模式运行")
    except Exception as _e:
        print(f"⚠ 平台连接失败: {_e}")

    boot_progress.set_phase("vector_model_download")
    boot_progress.set_download(onnx_cache_path())
    # V9 本地浏览器(Manus 对齐): 启动独立 WS 服务(扩展连接；端口 = 网关端口 + browser_local.ws_port_offset, 见 ws_port())
    try:
        from core.lib.v8 import browser_local

        browser_local.start_browser_ws()
    except Exception as _bl_err:
        print(f"[BROWSER_LOCAL] WS 服务启动失败: {_bl_err}")

    # P0-2(2026-09-13): turn 持久注册表 —— 建表 + 启动扫描。
    # 把「上次进程死前还在 RUNNING/DETACHED 的 turn」标成 STALE，
    # 这样用户回来看到的是「任务中断 + 最后状态 + 重新继续/重新运行/放弃」，
    # 而不是一片空白（此前状态全在内存，重启即丢）。
    try:
        from core.gateway import turn_registry as _trb

        _trb.init_db()
        _staled = _trb.scan_stale()
        if _staled:
            print(f"[TURN_REGISTRY] 启动扫描: {len(_staled)} 个 turn 心跳超时 → STALE")
            for _s1 in _staled[:5]:
                print(
                    f"   - {_s1['turn_key'][:8]}… session={_s1['session_id']} "
                    f"age={_s1['age_sec']}s (原状态 {_s1['status']})"
                )
        else:
            print("[TURN_REGISTRY] 启动扫描: 无 STALE turn")
    except Exception as _e_trb:
        print(f"[TURN_REGISTRY] 启动失败(不阻断): {_e_trb}")

    # 界面态快照（pm_1558 §二 裁 ⒜）：**服务自落** web/pa/ui_state.json（唯一写者 ＝ 服务）
    #   —— 有界等待（⛔ 长阻启动）· 写失败 ⇒ fail-loud 显形（守二）
    try:
        from core.gateway import ui_state as _ui_state

        _ui_state.write_once_bounded(timeout=6.0)
    except Exception as _ui_exc:
        print(f"[UI_STATE] ⛔ 快照之落 ⛔ 起（{type(_ui_exc).__name__}: {_ui_exc}）")

    boot_progress.set_phase("engine")
    print(f"🚀 ClawsJoy Gateway v6.0 重初始化毕（端口 {port}）")
    # ⭐ 门先开（pm_1608 §二.2 ⒜）：监听之线程为主 —— 主线程并之（⛔ 进程即退）
    boot_progress.mark_ready()
    _door.join()
