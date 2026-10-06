# -*- coding: utf-8 -*-
"""跨平台路径解析（WSL ↔ Windows）。

背景：历史代码把 WSL 专用路径直接写成默认值：

  - Obsidian vault：``/mnt/d/Obsidian/ClawsJoy/ClawsJoy``
  - Playwright 浏览器缓存：``/mnt/d/whisper_cache/ms-playwright``
  - Windows 命令解释器：``/mnt/c/Windows/System32/cmd.exe``

在 Windows 副本上 ``/mnt/d/...`` 会被解析成「当前盘符下的 \\mnt\\d\\...」
（例如 ``D:\\mnt\\d\\Obsidian\\...``）—— 既不抛错、也找不到真实目录，
属于**静默写错位置**，比直接报错更难排查。

这里统一按平台解析，并保留环境变量覆盖能力：
``PA_VAULT_DIR`` / ``PLAYWRIGHT_BROWSERS_PATH`` / ``COMSPEC``。

⚠ 2026-10-06（承 pm_1387 §二.2 之裁）：vault 之**真源之序**已改 ——
  env ``PA_VAULT_DIR`` ⇒ 配置 ``paths.vault_root`` ⇒ 内置 ``<data_root>/kb``
  ⇒ **末选**：旧机之探测 —— ⚠ **⛔ 字面**（承 pm_1399 §二.3）：唯 env ``PA_VAULT_LEGACY``
  ∧ **组织版开**（``org_enabled()`` · 默认 **关**）方取 ⇒ 否则 **None**（＝「未接（选目录）」）。
  ⛔ 再用 ``D:\\Obsidian\\...`` 作**字面默认** —— 那会把「未接」伪装成「已接」
  （在**净机**上指向**他人机器**之径 ⇒ 同「净机必败」之族）。
"""
import os
import tempfile
from pathlib import Path

# ⭐⭐⭐ 承 pm_1399 §二.3 ／ §三.2（批一）：**组织版之功能级开关** ＋ 组织物之径之**唯一出口**。
#   ⚠ 病（逐字）：旧为**字面**（`/mnt/d/Obsidian/...` ／ `D:\paseo-home\...`）⇒
#     ⠐ **净机必败**（指向他人机器之径）⠐ 且「未接」被伪装成「已接」⇒ ⛔ 入交付物（承 pm_1387 §二.3）。
#   ⇒ 今唯 env 出径；**默认 ⛔ 装**（关闭 ⇒ 其径逻辑 ⛔ 执行 ⇒ 面显「未接（组织版）」）。
ORG_ENV = "PA_ORG_FACES"
ORG_ON_VALUES = ("1", "true", "yes", "on")


def org_enabled():
    """组织版之**功能级**开关（env ``PA_ORG_FACES``）—— 默认 **关**。

    关 ⇒ 凡「组织专用」之面 ／ 器 **⛔ 执行其径逻辑**（其根径 ⛔ 被读 ∧ ⛔ 被 walk）
    ⇒ 显「未接（组织版）」（⛔ 崩 · ⛔ 静默兜底）。
    """
    return (os.environ.get(ORG_ENV, "") or "").strip().lower() in ORG_ON_VALUES


def org_path(env_name):
    """组织物之径之**唯一出口**（env ⇒ 缺 ⇒ ``None``）—— ⛔ 字面 · ⛔ 兜底（承 pm_1399 §二.3）。

    唯 ``org_enabled()`` 为真时取值 ⇒ 默认 **关** ⇒ ``None``（其径逻辑 ⛔ 执行）。
    """
    if not org_enabled():
        return None
    v = (os.environ.get(env_name, "") or "").strip()
    return v or None


def ws_root():
    """工作区根（**产品级**）—— env ``PA_WS_ROOT`` ⇒ 缺 ⇒ ``None``（⛔ 字面兜底）。"""
    v = (os.environ.get("PA_WS_ROOT", "") or "").strip()
    return v or None


WSL_BROWSERS = "/mnt/d/whisper_cache/ms-playwright"
WIN_BROWSERS = "D:\\whisper_cache\\ms-playwright"
WSL_CMD_EXE = "/mnt/c/Windows/System32/cmd.exe"
WIN_CMD_EXE = "C:\\Windows\\System32\\cmd.exe"

IS_WINDOWS = os.name == "nt"


def _first_existing(*candidates):
    """返回第一个真实存在的目录，全都不存在时返回 None。"""
    for candidate in candidates:
        if candidate and Path(str(candidate)).is_dir():
            return str(candidate)
    return None


def _config_vault_root():
    """配置真源（首启引导所立）：配置之 ``paths.vault_root``（用户自选知识库目录）。

    ⚠ 惰性 import（免 import 期环）· 唯读；取不到 ⇒ ``None``（⛔ 崩 · 唯返「未接」之据）。
    """
    try:
        from core.lib.unified_config import unified_config

        v = unified_config.get("paths.vault_root", None)
        if v is None or str(v).strip() in ("", "."):
            return None
        return str(v).strip()
    except Exception:
        return None


def _builtin_kb():
    """内置（空）知识库：``<data_root>/kb`` —— **存在方用**（⛔ 立目录 · 唯读）。

    净机之默认即是它（⛔ 用 ``D:\\Obsidian\\...`` 之字面兜底）。
    """
    try:
        from core.lib.config_helper import get_data_root

        p = Path(str(get_data_root())) / "kb"
        return str(p) if p.is_dir() else None
    except Exception:
        return None


def vault_root():
    """Obsidian vault 根目录 —— **真源之序**（2026-10-06 承 pm_1387 §二.2 之裁）：

        ① 显式 env ``PA_VAULT_DIR``（最高 · 未变）
        ② 配置 ``paths.vault_root``（首启引导／设置里所选之知识库目录）
        ③ 内置空知识库 ``<data_root>/kb``（存在方用）
        ④ **末选**：旧机之探测 —— env ``PA_VAULT_LEGACY``（⚠ 唯组织版开时取 · ⛔ 字面）

    全无 ⇒ **None**（＝「**未接（选目录）**」· 承四态之一处定形 · ⛔ 崩 · ⛔ 静默用字面默认）。
    ⚠ 调用方须自辨 ``None``（⛔ ``str(vault_root())`` —— 那得 ``"None"`` ＝ 假径）。
    """
    env = os.environ.get("PA_VAULT_DIR")
    if env:
        return Path(env)
    cfg = _config_vault_root()
    if cfg:
        return Path(cfg)
    builtin = _builtin_kb()
    if builtin:
        return Path(builtin)
    legacy = org_path("PA_VAULT_LEGACY")   # 末选（旧机兼容）—— 组织版关（默认）⇒ None
    if legacy and os.path.isdir(legacy):
        return Path(legacy)
    return None


# ===== 件名长度守护（2026-09-28 落 · 承「命名无上限」逮 ＋ 对端回件 §五）=====
MAX_NAME_BYTES = 200
# 派生名预算（CEO 2026-09-28 §三）：授权名 ≤ 200 B ＋ 最长派生后缀 `.before_<16hex>` = 24 B
# ⇒ 派生名 ≤ 224 ≤ NAME_MAX(255)（余 31 B · 并容 `.sha256` 之 7 B）。
# ⇒ 派生写点（如 `write_file` 的 `.bak`）按本上限判，⛔ 别拿 200 去卡派生名（会误拒合法派生件）。
MAX_DERIVED_NAME_BYTES = 224


def check_name_len(path, limit=MAX_NAME_BYTES):
    """件名（basename）UTF-8 字节数 <= ``limit`` ⇒ 否则 **fail-loud 拒写**。

    为什么按**字节**而非字数：``ext4`` 的 ``NAME_MAX`` 是 **255 字节**；一个中文字
    占 3 B ⇒ 80 个中文字 = 240 B **超限**，但按字数看只有 80（看着很短）。
    ⇒ 超限即当场炸 —— 写了对端（WSL）也读不到（``ENAMETOOLONG``）⇒ 宁可拒写，
      ⛔ 不落一个「本侧看得见、对端读不到」的件。

    ⚠ 只查 **basename**；父目录段同受 ``NAME_MAX`` 约束，本函数**不覆盖**（待证）。
    """
    name = os.path.basename(str(path))
    n = len(name.encode("utf-8"))
    if n > limit:
        raise ValueError(
            "件名 UTF-8 %dB > %dB ⇒ 拒写（WSL/ext4 ENAMETOOLONG ⇒ 对端读不到）: %s"
            % (n, limit, name)
        )
    return n


def check_path_len(path, limit=MAX_NAME_BYTES):
    """路径**每一段**（含父目录段）UTF-8 字节数 <= ``limit`` ⇒ 否则 **fail-loud**。

    ⚠ 为什么要查父段：``NAME_MAX`` 是**逐段**约束 —— 「件名短、父目录段超限」同样
    ``ENAMETOOLONG``。只查 basename ＝ 判据**只打在半段上**（承 DS 2026-09-28 裁
    「守护扩到父目录段」）。
    返回最长段的字节数；超限则报**是哪一段**（便于定位）。
    """
    worst, worst_seg = 0, ""
    for seg in Path(str(path)).parts:
        if seg in ("/", "\\", "."):
            continue
        n = len(seg.encode("utf-8"))
        if n > worst:
            worst, worst_seg = n, seg
    if worst > limit:
        raise ValueError(
            "路径段 UTF-8 %dB > %dB ⇒ 拒写（WSL/ext4 ENAMETOOLONG 逐段生效 ⇒ 对端读不到）: %s"
            % (worst, limit, worst_seg)
        )
    return worst


def write_text_lf(path, text, encoding="utf-8", limit=MAX_NAME_BYTES):
    """写文本件**强制 LF**（⛔ 不随平台翻 CRLF）—— vault 写点的唯一出口。

    为什么必须显式：``Path.write_text()`` 默认 ``newline=None`` ⇒ 在 Windows 上把
    ``\n`` 翻成 ``\r\n``（本机实测 ``write_text("x\n")`` -> ``b"x\r\n"``）。
    vault 是**跨平台镜像面**（WSL 侧按 LF 播种/镜像/比对）⇒ 本侧写入一旦带 CRLF：
      · 同一逻辑内容按字节分成两份 ⇒ ``sha16`` 与对端不等（四元组对不上）
      · 镜像判据只能靠「归一 EOL 后逐位同」勉强过 ⇒ 判据被稀释
      · 清单 ``bytes`` 读数随写入者变化 ⇒ 报数不稳
    ⇒ 承 CEO 2026-09-28 终裁 §一③ / §三②：「**写进 vault 的镜像须纯 LF**」。
    ⇒ 承「成对改 ＋ 反例门」：门 = ``tests/unit/test_vault_write_lf.py``。
    ⇒ 同址另挂**路径段守护** ``check_path_len()``（**逐段** · 含父目录段 · UTF-8 ≤ 200 B
      ⇒ 否则**拒写** · 门 = ``tests/unit/test_vault_write_namelen.py``）：超名件对端（WSL）
      读不到（``ENAMETOOLONG``）⇒ 宁可不落，⛔ 不落「本侧看得见、对端读不到」的件。
      （``check_name_len()`` 仍在，只查 basename —— 供「只关心件名」的调用方用。）
    ``limit`` 默认 ``MAX_NAME_BYTES``（授权名）；**派生名**写点（``.bak`` / ``.sha256`` /
      ``.before_*``）传 ``MAX_DERIVED_NAME_BYTES``（= 224 = 200 ＋ 24 B 派生后缀 ≤ 255）。

    ⚠ 沙箱镜像面（``sync_knowledge_to_sandbox`` 与 ``update_sop`` 的 ``dst``）**不在**本函数
    范围：CEO 同裁「沙箱镜像 ⛔ 不要求逐位同（判据 = 归一 EOL 后逐位同）」⇒ 那两处**不动**。
    """
    p = Path(path)
    check_path_len(p, limit)  # 逐段（含父目录段）—— 只查 basename 是判据打半段
    if p.parent and not p.parent.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding=encoding, newline="") as f:
        f.write(text)
    return p


# ===== vault（Obsidian）路径判据的唯一真源（2026-09-28 成对改）=====
# 为什么必须唯一：vault 旁挂着**两处安全判据** ——
#   ① core/gateway/guards/registry.py 的 vault 归类（读工具被拦时给哪个提示）
#   ② core/gateway/v9_bridge/tool_runner.py 的「续跑期禁写 vault」统一守卫
# 判据各自写死路径串时，脑根一改 ⇒ 判据**在场却打错对象**（判据还在，判的不是真对象）。
# ⇒ 判据一律引本模块：is_vault_path()（精确）/ contains_vault_marker()（过包括）。
#
# 历史串只作**跨平台文本回落**：日志 / 载荷 / 命令串里出现的是 WSL 形态
# `/mnt/d/Obsidian/...` 或片段 `Obsidian/ClawsJoy`，而脑根实算是 `D:\Obsidian\...`。
# ⛔ 不得只留历史串 —— 那样 vault 一搬家判据就瞎（这正是本子类要防的）。
VAULT_LEGACY_MARKERS = ("/mnt/d/Obsidian", "Obsidian/ClawsJoy", "/mnt/d/obsidian")


def _norm_path(text):
    """判据用的归一化：反斜杠 → 正斜杠 + 小写（跨平台形态可比较）。

    ⚠ 只用于「是不是 vault」这类**过包括**判断，⛔ 不用于落盘 —— POSIX 上反斜杠
    是合法文件名字符，归一化会改变文件名语义。
    """
    return str(text or "").replace("\\", "/").lower()


def path_forms(root):
    """同一目录的**另一平台形态**（Windows `D:\\...` ↔ WSL `/mnt/d/...`）。

    为什么单立：脑根在**同一台机上两形态并存**（Windows 看 `D:...`，WSL 看 `/mnt/d/...`）
    ⇒ 凡需「两形态都认」之处（vault 判据 ／ 前端把引用链接化的前缀 ／ 清单对齐）一律
    引本函数，⛔ 不各写一份（承「不复制第二份判据」）。
    """
    _root = str(root or "")
    if not _root:
        return ()
    out = [_root]
    _slash = _root.replace("\\", "/")
    _low = _slash.lower()
    if _low.startswith("d:/obsidian/"):
        out.append("/mnt/d/Obsidian/" + _slash[len("D:/Obsidian/"):])
    elif _low.startswith("/mnt/d/obsidian/"):
        out.append("D:/Obsidian/" + _slash[len("/mnt/d/Obsidian/"):])
    return tuple(dict.fromkeys(m for m in out if m))


def vault_markers():
    """vault 的路径指纹 = **实算真源** ＋ 历史串（原样大小写；判据内部再归一化）。

    实算真源同时给出「另一形态」变体：同一台机两形态并存（Windows 看 `D:\\...`，
    WSL 看 `/mnt/d/...`），两边文本都要能被认出。
    """
    out = list(path_forms(vault_root()))
    out.extend(VAULT_LEGACY_MARKERS)
    return tuple(dict.fromkeys(m for m in out if m))


def is_vault_path(path):
    """`path` 是否指向本机 vault（**精确判据**：前缀实算 ＋ 历史串回落）。"""
    _p = _norm_path(path).rstrip("/")
    if not _p:
        return False
    _root = _norm_path(vault_root()).rstrip("/")
    if _root and (_p == _root or _p.startswith(_root + "/")):
        return True
    return any(_norm_path(m) in _p for m in VAULT_LEGACY_MARKERS)


def contains_vault_marker(text):
    """自由文本（命令串 / 需求描述）里是否出现 vault 指纹（**过包括**判据）。"""
    _t = _norm_path(text)
    if not _t:
        return False
    return any(_norm_path(m) in _t for m in vault_markers())

def _win_default_browsers():
    """Playwright 在 Windows 上的**自带默认**缓存：``%LOCALAPPDATA%\\ms-playwright``。

    ``D:\\whisper_cache\\ms-playwright`` 是从 WSL 带过来的缓存，里面只有
    ``*-linux64`` 构建；Windows 要用 ``*-win64``，所以默认优先用本地这一份。
    """
    base = os.environ.get("LOCALAPPDATA")
    return str(Path(base) / "ms-playwright") if base else None


def playwright_browsers_path():
    """Playwright chromium 缓存目录（决定 "Executable doesn't exist" 是否出现）。"""
    env = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if env:
        return env
    if IS_WINDOWS:
        # Windows 侧：先本地默认（真正的 win64 构建）→ D: 缓存 → WSL 缓存
        found = _first_existing(_win_default_browsers(), WIN_BROWSERS, WSL_BROWSERS)
        return found or _win_default_browsers() or WIN_BROWSERS
    found = _first_existing(WSL_BROWSERS, WIN_BROWSERS)
    return found or WSL_BROWSERS


def cmd_exe():
    """Windows 命令解释器；WSL 侧走 /mnt/c interop，Windows 侧用 COMSPEC。"""
    if IS_WINDOWS:
        return os.environ.get("COMSPEC") or WIN_CMD_EXE
    return WSL_CMD_EXE


def runtime_tmp_dir():
    """宿主**运行时临时根目录**（带 clawsjoy 命名空间）。

    为什么需要它：历史代码把 Linux 临时目录写死成 ``/tmp/...``。Windows 上
    ``/tmp/x`` 会解析成 ``<当前盘符>:\\tmp\\x``（本机 ``D:\\tmp`` **不存在**）——
    不抛错、但写到别处（**静默写错位置**，比报错更难排查）。

    **WSL 侧行为零变化**：``tempfile.gettempdir()`` 在 Linux/WSL 上就是 ``/tmp``
    （故本函数在 WSL 返回 ``/tmp/clawsjoy``，与既有语义同域），Windows 侧是 ``%TEMP%``。
    覆盖：``PA_RUNTIME_TMP``。
    """
    env = os.environ.get("PA_RUNTIME_TMP")
    base = Path(env) if env else Path(tempfile.gettempdir()) / "clawsjoy"
    # 目录不存在时创建（幂等）；只读/受限环境下静默降级，不因临时目录不可建而中断
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return base


def runtime_tmp_path(*parts):
    """``runtime_tmp_dir()`` 下的一个路径，**返回正斜杠字符串**。

    为什么返回正斜杠：这些路径会经 JSON / 工具参数传给 agent 再回传
    （如 ``write_finalize(temp_path=...)``），**反斜杠在 JSON 与模型回抄时容易被吞**。
    Windows API（``open`` / ``Path``）接受正斜杠。
    """
    return runtime_tmp_dir().joinpath(*[str(x) for x in parts]).as_posix()


def map_linux_tmp(path):
    """把外部（文本 / agent 给出）的 ``/tmp/...`` 映射到宿主运行时临时目录；其它原样返回。

    只映射**前缀**，不改写其余内容。POSIX 侧 ``/tmp/x`` 与 ``runtime_tmp_dir()/x``
    本来就是同一处 ⇒ 本函数在 WSL 上是**恒等映射**；Windows 侧把 ``D:\\tmp\\x``
    这类误写纠正到真实位置。
    """
    p = str(path or "")
    if not p.startswith("/tmp/"):
        return p
    return runtime_tmp_path(p[len("/tmp/"):])


def to_host_path(path):
    """把外部传入的路径规整为**本机可用**的路径。

    WSL：``C:\\Users\\x`` -> ``/mnt/c/Users/x``（interop 需要挂载形式）
    Windows：``/mnt/c/Users/x`` -> ``C:\\Users\\x``，其余原样返回
    """
    p = str(path or "").strip()
    if not p:
        return p
    p = p.replace("\\", "/")

    if IS_WINDOWS:
        # /mnt/<drive>/... -> <DRIVE>:/...
        if p.startswith("/mnt/") and len(p) > 6 and p[6] == "/":
            return "%s:/%s" % (p[5].upper(), p[7:])
        if len(p) > 2 and p[1] == ":":
            return p[0].upper() + p[1:]
        return p

    # POSIX（WSL）：<drive>:/... -> /mnt/<drive>/...
    if len(p) > 2 and p[1] == ":" and p[2] == "/":
        return "/mnt/%s/%s" % (p[0].lower(), p[3:])
    return p