# -*- coding: utf-8 -*-
"""computer_use —— 桌面级白名单动作（路径 C 前置，2026-09-10）

【为什么在 agent_client 里做】
  Codex 的 Computer Use 运行时（cua_node）是**桌面级**能力：
  list_windows / list_apps / launch_app / activate_window / get_window_state /
  click / drag / scroll / press_key / type_text / set_value / get_screenshot …
  比 agent_client 现有的浏览器自动化高一个量级（能操作【任意】Windows 应用）。

  但 WSL 侧的 PA 碰不到它：Codex 主体在 WindowsApps 下受 Appx ACL 保护（实测 Permission denied）。
  而 agent_client **本来就是 Windows 侧进程**，且已经有
    WS 通道 + 白名单动作 + 治理门（在场授权/一次通过/可随时停止）。
  → 所以在这里加一个 computer_use 动作，复用整套基础设施，不新增接入面。

【治理门怎么复用】
  computer_use 与 open_document 等一样走 /v9/pa/act → BrowserLocalPlugin.execute()
  → core/lib/v8/browser_local.execute()，那条链上已有：
    · 随时停止（stop）拦截所有动作
    · 会话级一次授权（grant）
    · 需要确认时的审批
  即：不在这里另造一套门，而是**沿用同一道门**。

【安全设计（不做通用桌面控制）】
  1. 动作白名单: 只有登记过的 op 才放行, 未知 op 一律拒绝
  2. 只读/写分级: 默认只放行只读(list_windows/list_apps/get_window/get_window_state/get_screenshot);
     写动作(click/type_text/press_key/set_value/launch_app/…)必须显式 allow_write=true
  3. 不假成功: 运行时不可用(helper 缺失 / cua_repl 未启用 / app-server 拉不起来)一律返回
     明确 error 并附启用步骤 —— 绝不返回"成功"
  4. 路径可覆盖: 环境变量 PA_CUA_HELPER 可指定 helper, 便于换版本/换位置

【当前状态（如实标注）】
  本模块**已实现并可探测**，但**尚未实测过一次真实桌面操作**：
  helper(codex-computer-use.exe) 能被执行，但它第一步要拉起 **codex app-server**，
  实测返回 {"ok":false,"error":"failed to launch codex app-server: program not found"}。
  → 需要在 Windows 侧启用 cua_repl(或提供可用的 app-server)后才能跑通。
"""
import glob
import json
import os
import subprocess
import sys

# ⭐ 窗隐（pm_1865 §二.1）：本器由**无控制台之父**起（网关 detached ／ 任务宿主 svchost）
#   ⇒ 裸 `subprocess` 必**新开**控制台窗（屏上一闪）。真源 ＝ `core/pa/_proc.py`
#   （按**文件路径**载 · ⛔ `from core.pa import _proc`：`core/pa/__init__.py` 拉向量库 ⇒ 慢）。
def _load_proc():
    import importlib.util as _ilu
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                      "core", "pa", "_proc.py")
    try:
        _s = _ilu.spec_from_file_location("_pa_proc_hidden", _p)
        _m = _ilu.module_from_spec(_s)
        _s.loader.exec_module(_m)
        if callable(getattr(_m, "run_hidden", None)):
            return _m
    except Exception:                                             # noqa: BLE001 — 照实退本地等价
        pass
    return None


_PROC = _load_proc()


def run_hidden(cmd, **kw):
    u"""本器之 spawn 出口（窗隐 · ⛔ 各处手写 creationflags）。真源载不到 ⇒ 本地等价。"""
    if _PROC is not None:
        return _PROC.run_hidden(cmd, **kw)
    kw["creationflags"] = int(kw.get("creationflags", 0) or 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(cmd, **kw)


# ---- 动作白名单 ----
# 只读: 只看不动, 可以放开
READ_OPS = (
    "list_windows",  # 列窗口
    "list_apps",  # 列已安装/运行的应用
    "get_window",  # 取某个窗口信息
    "get_window_state",  # 取窗口状态(元素树/可视信息)
    "get_screenshot",  # 截屏
)
# 写: 会改变系统状态, 必须显式 allow_write
WRITE_OPS = (
    "click",
    "drag",
    "drag_handle",
    "move",
    "scroll",
    "press_key",
    "type_text",
    "set_value",
    "launch_app",
    "activate_window",
    "perform_secondary_action",
)
ALL_OPS = READ_OPS + WRITE_OPS

# cua helper 相对路径（@oai/cua 包内的 Windows 二进制）
_HELPER_REL = os.path.join("bin", "node_modules", "@oai", "cua", "bin", "windows", "codex-computer-use.exe")


def _local_appdata():
    return os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")


def _userprofile():
    return os.environ.get("USERPROFILE") or os.path.expanduser("~")


def codex_cli_path():
    """定位 Windows 侧 codex CLI（helper 拉 app-server 需要 CODEX_CLI_PATH）。

    实测(2026-09-10): helper 需要 spawn 一个能跑 app-server 子命令的 codex。
    Windows 上它的位置是: <USERPROFILE>/.codex/plugins/.plugin-appserver/codex.exe
    优先返回显式 env, 其次该打包位置, 最后 PATH 里的 codex。
    """
    env = os.environ.get("CODEX_CLI_PATH")
    if env:
        return env
    cand = os.path.join(_userprofile(), ".codex", "plugins", ".plugin-appserver", "codex.exe")
    if os.path.isfile(cand):
        return cand
    import shutil

    p = shutil.which("codex")
    return p or ""


def helper_candidates():
    """所有可能的 helper 路径(按目录名倒序=优先新版本)。"""
    out = []
    override = os.environ.get("PA_CUA_HELPER")
    if override:
        out.append(override)
    pat = os.path.join(_local_appdata(), "OpenAI", "Codex", "runtimes", "cua_node", "*", _HELPER_REL)
    out.extend(sorted(glob.glob(pat), reverse=True))
    # arm64 变体兜底
    out.extend(sorted(glob.glob(pat.replace(".exe", "-arm64.exe")), reverse=True))
    return out


def find_helper():
    for p in helper_candidates():
        if p and os.path.isfile(p):
            return p
    return None


def config_path():
    return os.path.join(_userprofile(), ".codex", "config.toml")


def cua_repl_enabled():
    """读 Windows 侧 Codex 配置, 判断 [mcp_servers.cua_repl] 是否 enabled。

    只做极简 TOML 段落解析 —— 不引第三方依赖, 解析失败一律当"未启用"(保守)。
    """
    p = config_path()
    if not os.path.isfile(p):
        return False, "未找到 Codex 配置: %s" % p
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except Exception as e:
        return False, "配置不可读: %s" % str(e)[:120]
    in_sec = False
    for ln in lines:
        s = ln.strip()
        if s.startswith("[") and s.endswith("]"):
            in_sec = s[1:-1].strip() == "mcp_servers.cua_repl"
            continue
        if in_sec and s.replace(" ", "").startswith("enabled="):
            val = s.split("=", 1)[1].strip().strip('"').strip("'").lower()
            return (val == "true"), ("已启用" if val == "true" else "已关闭(enabled=false)")
    return False, "配置里没有 [mcp_servers.cua_repl] 段"


def probe():
    """可用性探测 —— 返回结构化结果, 供上层决定能不能派活。"""
    helper = find_helper()
    enabled, why = cua_repl_enabled()
    ok = bool(helper) and bool(enabled)
    reason = ""
    if not helper:
        reason = "未找到 codex-computer-use.exe（cua_node 运行时未安装）"
    elif not enabled:
        reason = "cua_repl 未启用：%s" % why
    return {
        "available": ok,
        "helper": helper,
        "helper_count": len(helper_candidates()),
        "cua_repl_enabled": bool(enabled),
        "cua_repl_note": why,
        "config": config_path(),
        "reason": reason,
        "read_ops": list(READ_OPS),
        "write_ops": list(WRITE_OPS),
    }


def _rpc(op, args, helper, timeout):
    """向 helper 发一条 JSON-RPC 并读回。helper 是自有协议(非 stdio MCP)。

    ⚠️ 该协议尚未实测跑通(需 codex app-server)。此处按已观测到的报文形状实现:
       请求 {"jsonrpc":"2.0","id":N,"method":<op>,"params":{...}}
       响应 {"id":N,"ok":true,"result":...} 或 {"id":N,"ok":false,"error":"..."}
    任何异常/非 ok 响应都当失败返回, 绝不当作成功。
    """
    req = {"jsonrpc": "2.0", "id": 1, "method": op, "params": args or {}}
    payload = (json.dumps(req, ensure_ascii=False) + "\n").encode("utf-8")
    env = dict(os.environ)
    # helper 需要 codex app-server; 这里【自动补齐】必要环境(Windows 原生下才可靠)。
    # WSL interop 传环境给 Windows 进程不可靠(实测 program not found), 故在 agent_client 里自己设。
    _cli = codex_cli_path()
    if _cli:
        env.setdefault("CODEX_CLI_PATH", _cli)
    _home = os.path.join(_userprofile(), ".codex")
    env.setdefault("CODEX_HOME", _home)
    env.setdefault("CODEX_CLI_PATH_FALLBACK", _cli)
    try:
        p = run_hidden(
            [helper], input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, env=env
        )
    except subprocess.TimeoutExpired:
        return {"error": "helper 超时(%ss): 可能正在等待 codex app-server" % timeout}
    except Exception as e:
        return {"error": "helper 启动失败: %s" % str(e)[:200]}
    out = (p.stdout or b"").decode("utf-8", "replace").strip()
    err = (p.stderr or b"").decode("utf-8", "replace").strip()
    if not out:
        return {"error": "helper 无响应(rc=%s)%s" % (p.returncode, (" stderr=" + err[:160]) if err else "")}
    try:
        resp = json.loads(out.splitlines()[-1])
    except Exception:
        return {"error": "helper 响应无法解析: %s" % out[:200]}
    if isinstance(resp, dict) and resp.get("ok") is False:
        return {"error": "helper 拒绝: %s" % str(resp.get("error"))[:200], "helper_raw": resp}
    return {"result": resp}


def computer_use(params=None):
    """computer_use 动作入口。

    params:
      op           动作名(必须在 ALL_OPS 里)
      allow_write  写动作必须显式传 True
      timeout      秒(默认 20)
      其余键透传给 helper
    """
    p = dict(params or {})
    p.pop("action", None)  # 信封里已带 action, 见 local_actions.dispatch
    op = str(p.pop("op", "") or p.pop("op_name", "") or "").strip()
    if not op:
        return {"error": "computer_use 需要 op（可选: %s）" % ", ".join(ALL_OPS)}
    if op not in ALL_OPS:
        return {"error": "computer_use 不支持 op=%r；白名单只读=%s 写=%s" % (op, ",".join(READ_OPS), ",".join(WRITE_OPS))}

    allow_write = bool(p.pop("allow_write", False))
    if op in WRITE_OPS and not allow_write:
        return {
            "error": "op=%s 属【写】动作, 必须显式 allow_write=true 才执行" "（治理门仍需在场授权/可停止）。只读白名单: %s" % (op, ",".join(READ_OPS))
        }

    # (2026-09-10) 写动作治理策略（白皮书 v1 的机器执行层）：应用语义门，默认拒绝。
    # deny 硬拦；其余（allow/approve/approve_presence）目前一律"未放开"——
    # 因为写动作的"定位地基"get_window_state 尚未打通, 审批流也尚未落地。
    # 这里先把决策算出来并透出, 作为放开前的契约；不给任何静默执行的余地。
    if op in WRITE_OPS:
        import computer_use_policy as _pol

        _win = p.get("window") if isinstance(p.get("window"), dict) else {}
        _app = str(p.get("app") or _win.get("app") or "")
        _title = str(p.get("title") or _win.get("title") or "")
        _dec = _pol.evaluate(op, _app, _title, allow_write=True)
        if _dec["decision"] == "deny":
            return {"error": "写动作被治理策略拒绝: %s" % _dec["reason"], "policy": _dec}
        return {
            "status": "write_not_enabled",
            "policy": _dec,
            "error": "写动作尚未放开: 治理契约已就绪, 待 get_window_state 打通 + 审批流落地后逐级启用(先 L1 再 L2/L3)。决策=%s" % _dec["decision"],
        }

    timeout = int(p.pop("timeout", 20) or 20)
    info = probe()
    if not info["available"]:
        return {
            "error": "桌面自动化运行时不可用: %s" % info["reason"],
            "probe": info,
            "how_to_enable": [
                "1) Windows 侧 Codex 配置 %s 里把 [mcp_servers.cua_repl] 的 enabled 改为 true" % info["config"],
                "2) 确保 Codex 桌面应用在运行（helper 需要 codex app-server 提供认证）",
                "3) 重跑本动作；建议先用只读 op=list_windows 验证",
            ],
        }
    out = _rpc(op, p, info["helper"], timeout)
    if "error" in out:
        out["probe"] = {k: info[k] for k in ("helper", "cua_repl_enabled")}
        out["op"] = op
        return out
    return {"op": op, "read_only": op in READ_OPS, "result": out["result"]}
