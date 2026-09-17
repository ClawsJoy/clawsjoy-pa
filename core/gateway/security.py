"""安全模块 — 越权检测与审计（#106 C2：从 agent_gateway_enhanced.py 解耦，消除循环依赖）

agent_gateway -> sandbox_ops -> agent_gateway 的循环依赖原由 _detect_sys_escape 引起；
本模块独立承载高危命令/路径逃逸检测，双方都 import 本模块。
"""
import re
from pathlib import Path

# ===== 高危系统命令：硬禁止，不提供任何放行 =====
_SYS_ESCAPE_PATTERNS = [
    (r'(?:^|[\s;&|])rm\s+-rf?\s+/', 'rm -rf 根目录'),
    (r'(?:^|[\s;&|])mkfs(?:[.\s]|$)', 'mkfs 格式化'),
    (r'(?:^|[\s;&|])reboot(?:\s|$)', 'reboot'),
    (r'(?:^|[\s;&|])shutdown(?:\s|$)', 'shutdown'),
    (r'(?:^|[\s;&|])dd\s+of=/dev/', 'dd 写裸设备'),
    # 写重定向到系统目录；丢弃到 /dev/null|/dev/stdout|/dev/stderr 是合法 stderr 丢弃，豁免
    (r'(?:[12]?>>?|&>)\s*(?!/dev/(?:null|stdout|stderr)(?:[\s;&|<>]|$))/(?:etc|home|root|var|usr|bin|sbin|opt|proc|sys|dev|boot)', '写入系统目录'),
    (r'open\(["\']/(?:etc|home|root|var|usr|bin|sbin|opt|proc|sys|dev|boot)[^)]*["\']w', 'open 写系统路径'),
    # 下载工具写绝对路径(curl -o / wget -O / 等; 沙箱内应使用相对路径, /dev/null 豁免)
    (r'(?:^|[\s;&|])(?:curl|wget)\b[^\n;]*\s(?:-o|--output|-O)\s+(?!/dev/(?:null|stdout|stderr)\b)/', '下载工具写系统目录'),
    # 架构根治(2026-08-30): heredoc 写项目文件禁止(data/tmp/ 例外; 写只能走 write_file)
    #   A1 重定向 heredoc: cat/python/bash > 文件 <<EOF; A2 tee heredoc; B python heredoc 内写; C shell heredoc 体内重定向
    (r'(?:cat|python3?|bash)\b[^\n]*(?:>|>>)\s*(?!data/tmp/|/dev/(?:null|stdout|stderr)\b)[\w./-]+(?:\.[\w]+)?\s*<<', 'heredoc 写项目文件(重定向)'),
    (r'\btee\s+(?!data/tmp/)[\w./-]+(?:\.[\w]+)?\s*<<', 'heredoc 写项目文件(tee)'),
    (r"python3?\s*-?\s*<<\s*[\"']?[A-Za-z_][A-Za-z0-9_]*[\"']?[\s\S]*?(?:open\(\s*[\"'](?!data/tmp/)[^\"']*[\"']\s*,\s*[\"'](?:w|a|x|r\+|w\+|a\+|wb|ab|xb|w\+b|a\+b)[\"']|Path\(\s*[\"'](?!data/tmp/)[^\"']*[\"']\s*\)\s*\.\s*(?:write_text|write_bytes)\()", 'heredoc 内 python 写文件'),
    (r"(?:^|[\s;&|])(?:bash|sh|zsh)\s*<<\s*[\"']?[A-Za-z_][A-Za-z0-9_]*[\"']?[\s\S]*?\n[^\n]*?(?:[12]?>|>>|&>)\s*(?!data/tmp/|/dev/(?:null|stdout|stderr))[^\s;|&]*[/.][^\s;|&]*", 'heredoc 脚本体内写文件'),
    # 通用系统路径操作命令（touch/mkdir/rm/cp/mv/chmod 等指向 /etc /home /tmp 等）
    (r'(?:^|[\s;&|])(?:touch|mkdir|rm(?:\s+-[a-z]+)?|cp|mv|chmod|chown|ln)\b[^\n;]*/(?:etc|home|root|var|usr|bin|sbin|opt|proc|sys|dev|boot)(?:[/\s]|$)', '操作系统目录'),
]


def _is_path_escape(base, path_str):
    """路径是否逃逸沙箱根（../、绝对路径指向沙箱外）"""
    try:
        if not path_str:
            return False
        p = str(path_str)
        if p.startswith("/") or p.startswith("~"):
            return True
        base_p = Path(base)
        # 剥离可能的 clawsjoy_dev/ 前缀后判断
        rel = p[len("clawsjoy_dev/"):] if p.startswith("clawsjoy_dev/") else p
        resolved = (base_p / rel).resolve()
        if not str(resolved).startswith(str(base_p.resolve())):
            return True
    except Exception:
        return False
    return False


def _is_read_path_escape(sandbox_base, path_str):
    """只读白名单判定(断点2): 解析后须落在 沙箱根 ∪ 会话目录 ∪ 项目根 内。

    系统路径(/etc 等) / 双逃逸(../ 出到其他 session) → True(越权)。
    项目根回退是只读白名单, 不算越权; 写路径不适用本函数(写只进沙箱)。
    """
    try:
        if not path_str:
            return False
        from core.gateway.path_utils import _resolve_path
        import os
        _b = Path(str(sandbox_base))
        _t = _resolve_path(_b, str(path_str)).resolve()
        _allowed = [
            _b.resolve(),              # 沙箱根
            _b.resolve().parent,       # 会话目录 data/projects/{uid}/{sid}(../data 等会话产物)
            Path(os.environ.get("PROJECT_ROOT", str(Path(__file__).resolve().parent.parent.parent))).resolve(),  # 项目根(只读白名单)
        ]
        for _a in _allowed:
            if str(_t) == str(_a) or str(_t).startswith(str(_a) + os.sep):
                return False
        return True
    except Exception:
        return False


def _is_sandbox_tmp_heredoc(command, reason):
    """2026-09-06: heredoc 写类拦截的沙箱内豁免。
    Agent 常写 `cd data/tmp/douyin_weiren && python3 - <<'PY' ... open('segs.json','w') ...` —
    cd 到沙箱 data/tmp 后相对路径写, 字面前缀非 data/tmp/ → 正则误拦(视频配音/字幕/卡片批量生成
    无法用 write_file 逐文件写)。判定: 命令 cd 到 data/tmp 或 data/ 内 + heredoc + 无系统/绝对/../ 逃逸 → 豁免。
    """
    if "heredoc" not in reason:
        return False
    _cd_to_tmp = ("data/tmp/" in command) or bool(re.search(r'cd\s+[^;&|]*data/(?:tmp/|videos?/|tmp|)', command))
    if not _cd_to_tmp:
        return False
    if any(_sysd in command for _sysd in ("/etc/","/home/","/root/","/var/","/usr/","/bin/","/sbin/","/opt/","/proc/","/sys/","/dev/","/boot/")):
        return False
    if "../" in command:
        return False
    return True


def _detect_sys_escape(command):
    """检测高危/越权命令；命中返回 (pattern, reason)，否则 None"""
    if not command:
        return None
    for _pat, _reason in _SYS_ESCAPE_PATTERNS:
        if re.search(_pat, command):
            if _is_sandbox_tmp_heredoc(command, _reason):
                continue  # 沙箱 data/tmp 内 heredoc 写豁免(批量生成素材的合法操作)
            return (_pat, _reason)
    return None
