# -*- coding: utf-8 -*-
"""产物核验器（2026-09-13，R6）。

为什么需要它：「写了个文件」不等于「交付了产物」。实测事故——
`data/v9/pa/artifacts/artifact_pa_task.txt` 是 **68 字节**的 StubExecutor 假产物，
而审核只判「非空」→ 判 pass。所以「产物存在」必须包含「不是占位物」。

本模块是纯函数：不读全局状态、不写盘、可独立单测。
"""
import re
from pathlib import Path

# 从任务描述/goal objective 里解析**显式**体积规格。
# 只认显式写法，不猜 —— 猜出来的阈值会和类型注册表打架，又变成一个新的误判源。
_SIZE_RE = re.compile(r"(?:min_bytes|expected_min_bytes|不少于|至少|不低于|>=|≥)\s*[=:：]?\s*(\d+)\s*(kb|k|字节|b|bytes)?", re.I)


def parse_expected_min_bytes(text):
    """契约：返回 int 或 None（无显式规格 → None，交类型注册表判定）。

    支持：min_bytes=2048 / 不少于 2KB / 至少 3000 字节 / >= 4096
    """
    try:
        m = _SIZE_RE.search(str(text or ""))
        if not m:
            return None
        n = int(m.group(1))
        unit = (m.group(2) or "").lower()
        if unit in ("kb", "k"):
            n *= 1024
        return n if n > 0 else None
    except Exception:
        return None


# 实测的占位物大小（StubExecutor 写的假产物）
STUB_BYTES = (68,)
# 产物最小可接受体积。
# 2026-09-13 校准：初版定 2048，live 实测把一个 **1822 字节的真实交付**判成「过小」→ 误拦。
# 降到 512：仍能拦住 68 字节 stub 与「一行已完成」这类占位，又不误伤短交付。
MIN_ARTIFACT_BYTES = 512

# 2026-09-13 类型注册表（开拦截前置）：一刀切 512 被实测否决 ——
#   沙箱 .md p05=999；vault Reviews 自动生成 77.8% < 512；json 46.1% < 512（最小 2B 的 [] 合法）。
# 结论（实测）：**单看体积无法区分「占位」与「合法小文件」** → 只能按类型分别设，
# 且「体积启发式不适用」的类型要显式标 NOT_APPLICABLE，而不是硬套一个阈值。
#   None 表示「体积启发式不适用」（跳过体积判定，只做存在性 + stub 精确匹配）。
TYPE_MIN_BYTES = {
    ".md": 1024,  # 交付文档：p05=999 → 1024 略高于 p05，避免误伤短交付
    ".txt": 1024,  # 纯文本同理
    ".pptx": 4096,  # 演示文稿：结构开销大
    ".docx": 2048,
    ".json": 2,  # 状态/配置：2 字节的 [] 是合法的
    ".py": None,  # 辅助脚本 125–414B 合法 → 免体积闸
    ".log": None,  # min=0 合法 → 免体积闸
}


def verify_artifact(path, base_dir=None, min_bytes=None, allow_stub=False, expected_min_bytes=None):
    """核验单个产物。契约：返回 {ok, path, size, reason, applicable}。

    applicable=False 表示「体积启发式对该类型不适用」（NOT_APPLICABLE），只做了存在性 + stub 精确匹配。
    阈值优先级：expected_min_bytes（任务级） > min_bytes（显式） > TYPE_MIN_BYTES[扩展名] > None(不适用)。

    判据（R6）：
      1. 路径非空、非绝对系统路径（/tmp、/etc、/home 视为越界）；
      2. 真实存在且是文件；
      3. 体积 >= min_bytes，且不落在 STUB_BYTES 里（allow_stub=True 可豁免，仅供测试与过渡）。
    """
    p = str(path or "").strip()
    if not p:
        return {"ok": False, "path": p, "size": 0, "applicable": False, "reason": "产物路径为空"}
    if p.startswith(("/tmp", "/etc", "/home", "/root")):
        return {"ok": False, "path": p, "size": 0, "applicable": False, "reason": "产物路径越界（系统路径）：%s" % p}
    fp = Path(p)
    if base_dir and not fp.is_absolute():
        _cand = Path(base_dir) / fp
        if not _cand.exists():
            # 批187 · 缺陷1 第二层修复（假失败）：写入侧以「session 目录」为基准
            # （write_file 的 arg 常自带 clawsjoy_dev/ 前缀 ⇒ 真实落盘 = session_dir + arg），
            # 而核验侧传的是「沙箱根」(*/clawsjoy_dev) ⇒ 拼成双重 clawsjoy_dev ⇒ 报「产物不存在」。
            # 仅在「直拼不存在、上一级拼接存在」时切换 ⇒ 对正确用法零影响。
            _alt = Path(base_dir).parent / fp
            if _alt.exists():
                _cand = _alt
        fp = _cand
    try:
        if not fp.exists():
            return {"ok": False, "path": p, "size": 0, "applicable": False, "reason": "产物不存在：%s" % p}
        if fp.is_dir():
            return {"ok": False, "path": p, "size": 0, "applicable": False, "reason": "产物是目录不是文件：%s" % p}
        size = fp.stat().st_size
    except Exception as e:
        return {"ok": False, "path": p, "size": 0, "applicable": False, "reason": "产物不可读：%s（%s）" % (p, str(e)[:80])}
    # allow_stub=True 是「占位判定整体豁免」（过渡/测试用）：两条占位判据一起跳过。
    # 注意仍要求「存在且是文件」—— 豁免的是体积启发式，不是存在性。
    import os as _os_a

    _ext = _os_a.path.splitext(p)[1].lower()
    _mb = (
        expected_min_bytes
        if expected_min_bytes is not None
        else (min_bytes if min_bytes is not None else TYPE_MIN_BYTES.get(_ext, None))
    )
    if not allow_stub:
        # stub 精确匹配**不跳过**（68 字节是已知假产物，不是启发式）—— 与类型无关
        if size in STUB_BYTES:
            return {
                "ok": False,
                "path": p,
                "size": size,
                "reason": "疑似占位产物（%d 字节，与 StubExecutor 假产物同尺寸）：%s" % (size, p),
            }
        if _mb is not None and size < int(_mb) and _looks_like_stub(fp):
            return {
                "ok": False,
                "path": p,
                "size": size,
                "reason": "产物过小（%d < %d 字节，类型 %s），疑似占位：%s" % (size, int(_mb), _ext or "未注册", p),
            }
    _note = None
    if _mb is not None and size < int(_mb):
        _note = "小于推荐体积（%d < %d 字节），但内容非占位 ⇒ 放行" % (size, int(_mb))
    return {"ok": True, "path": p, "size": size, "reason": None, "applicable": _mb is not None, "note": _note}


_STUB_MARKS = ("todo", "占位", "stub", "placeholder", "待补", "待填", "tbd", "coming soon")


def _looks_like_stub(fp):
    """批187 · 缺陷1 第三层：体积过小时改用**内容判据**，避免真实小文档假失败。

    背景（实测假失败）：老板亲手写的 docs/pa187_probe.md 只有 581 B（<.md 阈值 1024）
    ⇒ 被纯体积启发式判「疑似占位」⇒ 界面显示「⚠ 核验未通过」，而内容是完整的标题+小节+结论。
    判据：① 含占位标记词 ② 非空行 < 3 行 ⇒ 才算占位；否则按实质内容放行。
    """
    try:
        t = fp.read_text(encoding="utf-8", errors="replace")[:2048]
    except Exception:
        return False
    low = t.lower()
    if any(m in low for m in _STUB_MARKS):
        return True
    return len([x for x in t.splitlines() if x.strip()]) < 3


def verify_artifacts(paths, base_dir=None, min_bytes=None, expected_min_bytes=None):
    """批量核验。契约：返回 {ok, checked, failures:[str], details:[...]}。"""
    details, failures = [], []
    for p in paths or []:
        r = verify_artifact(p, base_dir=base_dir, min_bytes=min_bytes, expected_min_bytes=expected_min_bytes)
        details.append(r)
        if not r["ok"]:
            failures.append(r["reason"])
    return {"ok": not failures, "checked": len(details), "failures": failures, "details": details}
