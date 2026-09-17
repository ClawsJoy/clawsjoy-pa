# -*- coding: utf-8 -*-
"""白名单本地动作（2026-09-10）: open_document / close_wps / lingxi_mcp

背景：PA 需要能"打开/关闭"WPS 与文档（三个坑同源：文件锁 / 多实例轮询 / 桥在线不可用）。
Linux 侧无 Windows 互操作，因此把这三个动作放在 Windows 侧 agent_client 执行。

安全设计（不做通用 shell）：
  1. open_document: 仅文档扩展名 + 仅白名单目录（Desktop / Documents / AGENT_LOCAL_DIRS）
  2. close_wps: 只关固定进程名（wps.exe / wpp.exe / et.exe），不接受自定义参数
  3. lingxi_mcp: 仅探测插件持久化配置；写入需先确认键名（不擅自改插件配置）
非 Windows 平台一律返回明确 error，绝不假装成功。
"""
import os
import subprocess
import sys

ALLOWED_EXTS = {".pptx", ".ppt", ".docx", ".doc", ".xlsx", ".xls", ".pdf"}
WPS_PROCS = ("wps.exe", "wpp.exe", "et.exe")
# computer_use(2026-09-10, 路径C前置): 桌面级白名单动作, 桥接 Codex CUA helper。
# 与其它本地动作一样走 /v9/pa/act → browser_local.execute(), 复用同一道治理门。
LOCAL_ACTIONS = {"open_document", "close_wps", "lingxi_mcp", "computer_use"}


def _allowed_dirs():
    base = [os.path.join(os.path.expanduser("~"), "Desktop"), os.path.join(os.path.expanduser("~"), "Documents")]
    extra = os.getenv("AGENT_LOCAL_DIRS", "")
    base += [d.strip() for d in extra.split(";") if d.strip()]
    out = []
    for d in base:
        try:
            out.append(os.path.normcase(os.path.realpath(d)))
        except Exception:
            continue
    return out


def validate_path(path):
    """纯函数：路径白名单校验。返回 (ok, err)。"""
    if not path or not isinstance(path, str):
        return False, "path 必填"
    ext = os.path.splitext(path)[1].lower()
    if ext not in ALLOWED_EXTS:
        return False, "扩展名 %s 不在白名单(%s)" % (ext or "(无)", ",".join(sorted(ALLOWED_EXTS)))
    try:
        ap = os.path.normcase(os.path.realpath(path))
    except Exception as e:
        return False, "路径无法解析: %s" % str(e)[:80]
    for d in _allowed_dirs():
        if ap == d or ap.startswith(d + os.sep):
            return True, ""
    return False, "目录不在白名单（仅 Desktop / Documents / AGENT_LOCAL_DIRS）"


def open_document(params=None):
    """用系统默认程序打开文档（仅白名单目录 + 文档扩展名）。"""
    p = params or {}
    path = str(p.get("path") or "").strip()
    # 参数白名单：只接受 path（拒绝 cmd/shell/args 之类）
    bad = [k for k in p if k not in ("path", "wait_ms")]
    if bad:
        return {"error": "open_document 不接受参数 %s（安全）" % bad}
    ok, err = validate_path(path)
    if not ok:
        return {"error": "拒绝: " + err}
    if sys.platform != "win32":
        return {"error": "open_document 仅支持 Windows（当前 %s）" % sys.platform}
    if not os.path.isfile(path):
        return {"error": "文件不存在: %s" % path}
    try:
        os.startfile(path)  # noqa: S606 — Windows 默认程序打开
        return {"opened": path, "ext": os.path.splitext(path)[1].lower()}
    except Exception as e:
        return {"error": "打开失败: %s" % str(e)[:200]}


def close_wps(params=None):
    """关闭 WPS 主程序（固定进程名，不接受自定义参数）。"""
    p = params or {}
    bad = [k for k in p if k not in ("force", "wait_ms")]
    if bad:
        return {"error": "close_wps 不接受参数 %s（安全，进程名固定）" % bad}
    if sys.platform != "win32":
        return {"error": "close_wps 仅支持 Windows（当前 %s）" % sys.platform}
    killed = []
    for name in WPS_PROCS:
        try:
            r = subprocess.run(["taskkill", "/IM", name, "/F"], capture_output=True, text=True, timeout=20)
            msg = (r.stdout or r.stderr or "").strip().replace("\n", " ")[:120]
            killed.append({"proc": name, "rc": r.returncode, "msg": msg})
        except Exception as e:
            killed.append({"proc": name, "rc": -1, "msg": str(e)[:100]})
    return {"closed": killed}


def lingxi_mcp(params=None):
    """探测灵犀插件持久化配置（只读；写入需确认键名后再实现）。"""
    p = params or {}
    enable = bool(p.get("enable", True))
    cands = []
    for env in ("APPDATA", "LOCALAPPDATA"):
        v = os.getenv(env)
        if v:
            cands += [
                os.path.join(v, "lingxi-ai"),
                os.path.join(v, "LingxiAI"),
                os.path.join(v, "Kingsoft", "lingxi-ai"),
            ]
    cands.append(os.path.join(os.path.expanduser("~"), ".lingxi-ai"))
    dirs = [d for d in cands if os.path.isdir(d)]
    files = []
    for d in dirs:
        for root, _dirs, fs_ in os.walk(d):
            for f in fs_:
                if f.lower().endswith((".json", ".ini", ".cfg", ".conf", ".db")):
                    files.append(os.path.join(root, f))
    if not dirs:
        return {
            "error": "未发现灵犀持久化配置目录：开关可能存于插件 WebView localStorage，" "需 UI 自动化（pyautogui/win32）或人工开启",
            "candidates": cands,
            "enable_requested": enable,
        }
    return {
        "config_dirs": dirs,
        "config_files": files[:20],
        "enable_requested": enable,
        "note": "仅探测未写入；确认键名后再实现写入（避免误改插件配置）",
    }


def dispatch(action, params=None):
    # (2026-09-10) 网关下发的 params 是完整 args, 里面同时带着 "action"(信封里也有一份)。
    # 各动作的参数白名单只认业务参数, 因此这里先摘掉 action; 若两份不一致则拒绝
    # (防篡改: 信封说 open_document、参数说 close_wps 这类混淆)。
    p = dict(params or {})
    _req = p.pop("action", None)
    if _req is not None and str(_req) != str(action):
        return {"error": "action 不一致: 信封=%r 参数=%r（拒绝）" % (action, _req)}
    params = p
    if action == "open_document":
        return open_document(params)
    if action == "close_wps":
        return close_wps(params)
    if action == "lingxi_mcp":
        return lingxi_mcp(params)
    if action == "computer_use":
        import computer_use as _cu  # 桌面级白名单动作(只读默认放行, 写需 allow_write)

        return _cu.computer_use(params)
    return {"error": "unknown local action: %s" % action}
