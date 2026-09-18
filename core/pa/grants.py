# -*- coding: utf-8 -*-
"""授权记忆（grants）—— 老板在卡片上点「一直允许」后，同一**场景**免问（批153）。

设计原点（三条）：
1. **场景要窄、要可解释**：scene = §tool|场景键§——
   · §execute_command§ → 取命令**首 token**（如 §mkdir§、§python3§）；
   · 文件类（§write_file§/§edit_file§/§write_large§）→ 取**目录**（如 §data/reports§）。
   只做**精确匹配**，不做通配、不做前缀——避免「一次授权 = 授权一切」。
2. **出口门不参与授权**（门1 不动）：命令被判定为「往外部发数据」时**不接受授权**——
   这类必须每次问（见 guards/registry.py 的 grant 前置排除）。
3. **每次免问都留痕**（体检项 61）：§[GRANT]§ 打印 + 计数落 §grants.yaml§，老板可查。

落盘：§data/v9/pa/grants.yaml§（与 PA 其他状态同目录；cwd 优先，回落代码根）。
"""
from __future__ import annotations

import datetime as _dt
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

GRANTS_REL = Path("data") / "v9" / "pa" / "grants.yaml"
DECISION_ALWAYS = "always"


def grants_path() -> Path:
    """授权文件路径：cwd 优先；不存在时回落到代码根（与 run_id.default_log_dir 同思路）。"""
    if GRANTS_REL.parent.exists():
        return GRANTS_REL
    _root = Path(__file__).resolve().parents[2]  # core/pa/grants.py → 仓库根
    _alt = _root / GRANTS_REL
    if _alt.parent.exists():
        return _alt
    return GRANTS_REL


def _now() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _load() -> Dict[str, Any]:
    p = grants_path()
    if not p.exists():
        return {"version": 1, "updated": _now(), "grants": []}
    try:
        import yaml  # type: ignore

        d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        if not isinstance(d, dict):
            return {"version": 1, "updated": _now(), "grants": []}
        d.setdefault("grants", [])
        return d
    except Exception as e:
        print("[GRANT_FAIL] 读取 grants.yaml 失败: %s" % e)
        return {"version": 1, "updated": _now(), "grants": []}


def _save(d: Dict[str, Any]) -> bool:
    p = grants_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        d["updated"] = _now()
        try:
            import yaml  # type: ignore

            _txt = yaml.safe_dump(d, allow_unicode=True, sort_keys=False)
        except Exception:
            import json

            _txt = json.dumps(d, ensure_ascii=False, indent=1)
        p.write_text(_txt, encoding="utf-8")
        _audit_save(p, d, True)
        return True
    except Exception as e:
        print("[GRANT_FAIL] 写 grants.yaml 失败: %s" % e)
        _audit_save(p, d, False, str(e)[:200])
        return False


def _audit_save(p, d: Dict[str, Any], ok: bool, error: str = "") -> None:
    """**X-16 批 C（DS 拍 B1）**：`grants.yaml` 是 YAML ⇒ 接不了 JSON-only 的统一出口
    （`StateFile` 只做 `json.loads`/`json.dumps`）⇒ 本处**不接线**，只补**审计留痕**。

    为什么是审计而不是完整性：本处**不是静默失败**（有 `[GRANT_FAIL]` 打印），
    接线价值不在「不丢」，在「**谁/何时/为什么改了授权**」可查。

    契约：**永不抛**（审计失败不得打断授权写入；与 `AuditLog.record` 同一纪律）。
    """
    try:
        from core.pes.audit import audit_log

        audit_log().record(
            "pa.grants.write",
            payload={
                "path": str(p),
                "ok": bool(ok),
                "error": str(error or ""),
                "updated": d.get("updated"),
                "grants_n": len(d.get("grants") or []),
            },
            layer="PA 授权记忆",
        )
    except Exception:
        pass


def _has_unsafe_path(cmd: str) -> bool:
    """命令里是否出现**绝对路径或越界路径** —— 这类**不可授权**（每次必问）。"""
    import re as _re

    _s = str(cmd or "")
    # 批153 实测修正：§2>/dev/null§ 这类**丢弃型重定向**是合法写法（security.py 也豁免它），
    # 不能因为它含 '/' 就把整条命令判成「不可授权」——否则最常见的写命令永远记不住场景。
    _s = _re.sub(r"[12]?>\s*/dev/(null|stdout|stderr)", " ", _s)
    _s = _re.sub(r"&>\s*/dev/(null|stdout|stderr)", " ", _s)
    if ".." in _s:
        return True
    return bool(_re.search(r"(^|[\s'\"()=<>])/", _s))


def _extract_path_token(cmd: str) -> str:
    """从命令里抽「目标目录」当场景键（批153 实测：首 token 不稳）。

    规则：扫 shell 词元，取**第一个含 '/' 的、非选项/非 URL 的**路径，去掉引号；
    若带文件名（含扩展名）取其所在目录；最后只保留**前两级**（如 §data/批153验证§）。
    抽不到返回空串（由调用方回落首 token）。"""
    import re as _re

    _s = str(cmd or "")
    # ① 丢弃型重定向先剔除（§2>/dev/null§ 合法写法，含 '/' 但不是目标路径）
    _s = _re.sub(r"[12]?>\s*/dev/(null|stdout|stderr)", " ", _s)
    _s = _re.sub(r"&>\s*/dev/(null|stdout|stderr)", " ", _s)
    # ② URL 剔除（外发类本来就不参与授权，别把域名当路径）
    _s = _re.sub(r"\S+://\S+", " ", _s)
    # ③ 出现绝对路径 / 越界路径 ⇒ **不归场景**（这类必须每次问）
    if ".." in _s or _re.search(r"(^|[\s'\"()=<>])/", _s):
        return ""
    # ④ 收集「像相对路径」的片段，**优先取项目内顶层目录开头的那个**
    _TOP = (
        "data",
        "docs",
        "core",
        "web",
        "tests",
        "tools",
        "archive",
        "agents",
        "config",
        "scripts",
        "engine",
        "skills",
    )
    _cands: List[str] = []
    for _m in _re.finditer(r"[\w\u4e00-\u9fff.-]+(?:/[\w\u4e00-\u9fff.-]+)+", _s):
        _parts = [p for p in _m.group(0).split("/") if p]
        if len(_parts) < 2:
            continue
        if "." in _parts[-1]:  # 末段是文件名 ⇒ 取其目录
            _parts = _parts[:-1]
        if _parts:
            _cands.append("/".join(_parts[:2]))
    for _c in _cands:
        if _c.split("/")[0] in _TOP:
            return _c
    return _cands[0] if _cands else ""


def scene_of(tool: str, args: Optional[Dict[str, Any]]) -> str:
    """把一次写操作归到一个**窄场景**（精确匹配用；空场景 = 不可授权）。"""
    _tool = str(tool or "")
    _args = args or {}
    if _tool == "execute_command":
        _cmd = str(_args.get("command") or "").strip()
        if not _cmd:
            return ""
        # 批153 实测修正：**首 token 太脆** —— 同一件事这次写成 §python3 -c ...open('data/批153验证/note.md')§、
        # 下次写成 §mkdir -p data/批153验证 && ...§，首 token 从 python3 变 mkdir ⇒ 授权记了也用不上。
        # 改为**优先按「目标路径」归场景**（从命令里抽第一个像路径的 token，取前两级目录），
        # 抽不到再回落到首 token。这样「同一个目标目录」的写操作算同一场景。
        # 绝对路径 / 越界路径 ⇒ **不可授权**（不能回落首 token，否则一个 python3 授权会放行一切）
        if _has_unsafe_path(_cmd):
            return ""
        _path_tok = _extract_path_token(_cmd)
        if _path_tok:
            return "execute_command|%s" % _path_tok
        return "execute_command|%s" % _cmd.split()[0]
    _p = str(_args.get("path") or "").strip()
    if not _p:
        return ""
    _dir = os.path.dirname(_p) or "."
    return "%s|%s" % (_tool, _dir)


def is_granted(scene: str, path: Optional[Path] = None) -> bool:
    if not scene:
        return False
    d = _load()
    for g in d.get("grants") or []:
        if str(g.get("scene")) == scene and str(g.get("decision")) == DECISION_ALWAYS:
            return True
    return False


def grant(scene: str, decision: str = DECISION_ALWAYS, note: str = "") -> Dict[str, Any]:
    """记录一条授权（幂等：同场景已存在则只更新 note/时间）。"""
    d = _load()
    _items: List[Dict[str, Any]] = d.get("grants") or []
    for g in _items:
        if str(g.get("scene")) == scene:
            g["decision"] = decision
            g["decided_at"] = _now()
            if note:
                g["note"] = note
            _save(d)
            return g
    _new = {
        "scene": scene,
        "decision": decision,
        "decided_at": _now(),
        "note": note or "老板在审批卡选择「一直允许」",
        "uses": 0,
        "last_used_at": "",
    }
    _items.append(_new)
    d["grants"] = _items
    _save(d)
    return _new


def log_grant_use(scene: str, tool: str = "", args: Optional[Dict[str, Any]] = None) -> None:
    """每次「免问放行」都留痕：打印 + 计数（体检项 61：判定型代码两个分支都要留痕）。"""
    _args = args or {}
    _tgt = str(_args.get("command") or _args.get("path") or "")[:120]
    print("[GRANT] 免问放行 scene=%s tool=%s target=%s" % (scene, tool, _tgt))
    d = _load()
    for g in d.get("grants") or []:
        if str(g.get("scene")) == scene:
            g["uses"] = int(g.get("uses") or 0) + 1
            g["last_used_at"] = _now()
            _save(d)
            return


def list_grants() -> List[Dict[str, Any]]:
    return list(_load().get("grants") or [])
