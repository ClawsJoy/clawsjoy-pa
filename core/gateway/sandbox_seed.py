# -*- coding: utf-8 -*-
"""剥离层判据 1 · Seed 检查（B 口径 · S1 定向 seed + **manifest 加固**）。

真实反例：PA 在空骨架沙箱里做「盘点项目」并给结论 ⇒ 判据：未 seed/空骨架/来源不可读 ⇒ BLOCKED。
老板补充反例：**空骨架 + 伪造 seed 标记 ⇒ 不得仅凭标记放行** ⇒ 因此必须有 manifest 凭据。

2026-09-20 · DSH 换锚（DS 裁 A3 三候选之 (i)；实证见 dsh/2026-09-20-dsh-A3建会话即seed_定位与四方案.md）：
  旧语义把 manifest **锚在沙箱** ⇒ 要求「沙箱自 seed 后一个字节都不能变」⇒ 而**沙箱是工作区、设计上会被写**
  ⇒ **接了就自锁**（PA 第一次写文件后，下一回合必被 seed 门拦死）。实测：新增 1 文件 ⇒ blocked；
  删 1 文件 ⇒ blocked（文件数相同也红）。这就是 `seed_sandbox` 长期**零调用者**的真因。
  ⇒ **锚点移到源**：判定看 `seed.source_path` **存在且可读** ＋ 记录含 **`source_manifest_hash`**；
     **沙箱侧 manifest 只作读数（file_count 等），不作判定**。
  seed 记录 {source_path, seed_at, commit, scope, file_count, source_manifest_hash, manifest_hash(读数)}
  已知残余（如实标注）：源 hash **不作判定** ⇒ 伪造者只需给一个"可读路径"即可过门；
    沙箱侧读数留存以便审计比对。
"""
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# S1 定向 seed 范围（老板拍板）：不含 .git / .venv / node_modules / data
SEED_SCOPE = ["core", "web", "config", "docs", "tests", "tools"]
SEED_TOP_FILES = (".md", ".toml", ".txt", ".cfg", ".ini", ".yaml", ".yml")
SKIP_PARTS = (".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache")
# 2026-09-20 · DSH（DS 裁 A3 ①「缩 scope」）：大件不入沙箱。
# 依据：SEED_SCOPE 六目录实测 ≈2.17 GB / 86,355 files（tools 1.7G/81,793 含 lingji-cut 1.3G；
#       web 442M 含 images 375M、mobile 66M）⇒ 照字面 copy=True ＝ **每会话 +2.17 GB**、
#       磁盘 852 GB 余量 ⇒ 约 390 会话打满 ⇒ 与 #27「PA 首用不卡」相悖。
# 排除后：≈21 MB / 4,552 files（降 99%）。判据/反例见 dsh/2026-09-20-dsh-A3建会话即seed_定位与四方案.md
SEED_EXCLUDE = ("tools", "web/images", "web/mobile")


def _is_excluded(rel, exclude=SEED_EXCLUDE):
    """rel 为**相对根**的 posix 路径；命中排除前缀（或整目录名）⇒ True。"""
    rel = str(rel).replace("\\", "/").strip("/")
    for e in (exclude or ()):
        p = str(e).replace("\\", "/").strip("/")
        if rel == p or rel.startswith(p + "/"):
            return True
    return False


def _files(root, scope=None, exclude=SEED_EXCLUDE):
    root = Path(str(root))
    out = []
    targets = [root / s for s in (scope or [])] if scope else [root]
    for t in targets:
        if not t.exists():
            continue
        it = t.rglob("*") if t.is_dir() else [t]
        for p in it:
            if not p.is_file():
                continue
            if any(s in p.parts for s in SKIP_PARTS):
                continue
            try:
                if _is_excluded(p.relative_to(root).as_posix(), exclude):
                    continue
            except Exception:
                pass
            out.append(p)
    # 注意：**不要**在这里按"仅文档后缀"过滤根下文件 —— 该过滤只适用于**仓根**的顶层文件，
    # 由 seed_sandbox 单独处理；否则会漏拷每个 scope 目录的**直属文件**（实测 bug）。
    return sorted(set(out))


def manifest_of(root, scope=None, exclude=SEED_EXCLUDE):
    """清单：文件数 + 相对路径/大小 的 sha256（凭据用）。
    2026-09-20：锚点从「沙箱」移到「源」后，源侧与沙箱侧**都**用本函数（沙箱侧只作读数）。"""
    root = Path(str(root))
    fs = _files(root, scope, exclude)
    lines = []
    for p in fs:
        try:
            lines.append("%s:%d" % (str(p.relative_to(root)), p.stat().st_size))
        except Exception:
            pass
    h = hashlib.sha256("\n".join(sorted(lines)).encode("utf-8")).hexdigest()
    return {"file_count": len(fs), "manifest_hash": h}


def check_seed(sandbox_dir, source_readable=None):
    """返回 {ok, status, reason, evidence}；**标记不足以放行**（须 manifest 对得上）。"""
    sb = Path(str(sandbox_dir))
    ev = {"sandbox": str(sb), "file_count": 0, "source_path": "", "seed_at": "", "commit": "",
          "manifest_hash": "", "manifest_ok": False}
    if not sb.exists():
        return {"ok": False, "status": "blocked", "reason": "沙箱不存在：" + str(sb), "evidence": ev}
    allf = _files(sb)
    ev["file_count"] = len(allf)
    seed = None
    st = sb / ".agent_state.json"
    if st.exists():
        try:
            from core.gateway.state_json import read_json
            seed = (read_json(st) or {}).get("seed")
        except Exception:
            seed = None
    if not isinstance(seed, dict) or not seed.get("source_path"):
        return {"ok": False, "status": "blocked",
                "reason": "未 seed（.agent_state.json 无 seed.source_path）=> 不得盘点/修改/产出结论",
                "evidence": ev}
    ev["source_path"] = str(seed.get("source_path"))
    ev["seed_at"] = str(seed.get("seed_at") or "")
    ev["commit"] = str(seed.get("commit") or "")
    ev["manifest_hash"] = str(seed.get("manifest_hash") or "")
    ok_read = source_readable if source_readable is not None else Path(ev["source_path"]).exists()
    if not ok_read:
        return {"ok": False, "status": "blocked", "reason": "seed 来源不可读：" + ev["source_path"], "evidence": ev}
    # 2026-09-20 · DSH 换锚（DS 裁 A3 三候选之 (i)）：
    #   判定锚 = **源**（source_path 可读 + source_manifest_hash 在场）；**沙箱侧只作读数**。
    #   旧写法锚在沙箱 ⇒ 要求沙箱零变 ⇒ **接了就自锁**（实测：新增/删各 1 文件 ⇒ blocked）。
    _src_hash = str(seed.get("source_manifest_hash") or "")
    ev["source_manifest_hash"] = _src_hash
    if not _src_hash:
        return {"ok": False, "status": "blocked",
                "reason": "seed 缺 source_manifest_hash（旧格式标记）=> BLOCKED（请重钉：seed_sandbox 会补该格）",
                "evidence": ev}
    scope = seed.get("scope") or SEED_SCOPE
    _excl = seed.get("exclude") or SEED_EXCLUDE
    try:
        _src_m = manifest_of(Path(ev["source_path"]), scope, _excl)
    except Exception:
        _src_m = {"file_count": 0, "manifest_hash": ""}
    if int(_src_m.get("file_count") or 0) <= 0:
        return {"ok": False, "status": "blocked",
                "reason": "seed 来源为空骨架（源侧 0 文件）：" + str(ev["source_path"]), "evidence": ev}
    # 沙箱侧：**读数**（不作判定 —— 沙箱是工作区，设计上会被写）
    try:
        _sb_m = manifest_of(sb, scope, _excl)
    except Exception:
        _sb_m = {"file_count": -1, "manifest_hash": ""}
    ev["sandbox_manifest_current"] = _sb_m["file_count"]
    ev["sandbox_manifest_hash"] = _sb_m["manifest_hash"]
    ev["source_file_count"] = _src_m["file_count"]
    ev["source_manifest_now"] = _src_m["manifest_hash"]
    ev["source_manifest_drift"] = bool(_src_m["manifest_hash"] != _src_hash)  # 读数：源已变（提示重钉，**不拦**）
    return {"ok": True, "status": "seeded",
            "reason": "已绑定主体项目（源锚：source_path 可读 ＋ source_manifest_hash 在场；沙箱 manifest 仅读数）",
            "evidence": ev}


def task_entry_gate(user_id, session_id, root=None):
    """**W1 接线**（老板拍板）：**新任务**进入沙箱前的 seed 门。

    只对**新任务**生效（不回溯历史沙箱）：调用方在"新任务/新 goal"时调用本函数；
    未 seed / manifest 不匹配 ⇒ allowed=False，调用方必须**不执行**并回报明确原因。
    """
    import pathlib as _pl
    sb = _pl.Path(root or "data/projects") / str(user_id) / str(session_id) / "clawsjoy_dev"
    res = check_seed(sb)
    return {"allowed": bool(res.get("ok")), "status": res.get("status"), "reason": res.get("reason"),
            "sandbox": str(sb), "evidence": res.get("evidence")}


def seed_sandbox(sandbox_dir, source_path, commit="", scope=None, copy=True):
    """S1 定向 seed：**复制范围内容 + 写 manifest**（走唯一原子出口 update_json）。"""
    import shutil
    import time as _t
    from core.gateway.state_json import update_json

    sb = Path(str(sandbox_dir)); src = Path(str(source_path))
    scope = list(scope or SEED_SCOPE)
    copied = 0
    if copy:
        for name in scope:
            s = src / name
            if not s.exists():
                continue
            d = sb / name
            if s.is_dir():
                # 逐文件容错复制（真仓存在**断链符号链接**，copytree 会整体抛错）
                failed = 0
                for f in _files(s):
                    # 2026-09-20 · DSH 修正：排除项必须按**相对项目根**判（此前按相对 scope 子目录判
                    #   ⇒ 'web/images' 永不命中 ⇒ 实测仍拷了 375M+66M）。判据：沙箱体积应从 452M 降到 ≈11M。
                    try:
                        if _is_excluded(name + "/" + f.relative_to(s).as_posix(), SEED_EXCLUDE):
                            continue
                    except Exception:
                        pass
                    try:
                        dst = d / f.relative_to(s)
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(f, dst)
                        copied += 1
                    except Exception:
                        failed += 1
                if failed:
                    print('[SEED] 跳过不可复制项 %d 个（断链/权限）' % failed)
            else:
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(s, d); copied += 1
        for p in sorted(src.glob("*")):
            if p.is_file() and p.suffix in SEED_TOP_FILES:
                shutil.copy2(p, sb / p.name); copied += 1
    m = manifest_of(sb, scope, SEED_EXCLUDE)          # 沙箱侧（**读数**）
    try:
        src_m = manifest_of(src, scope, SEED_EXCLUDE)  # 源侧（**判定锚**）
    except Exception:
        src_m = {"file_count": 0, "manifest_hash": ""}
    rec = {"source_path": str(src), "seed_at": _t.strftime("%Y-%m-%d %H:%M:%S"),
           "commit": str(commit or ""), "scope": scope, "exclude": list(SEED_EXCLUDE),
           "file_count": m["file_count"], "manifest_hash": m["manifest_hash"],
           "source_manifest_hash": src_m["manifest_hash"], "source_file_count": src_m["file_count"]}
    update_json(sb / ".agent_state.json", lambda _d: _d.update({"seed": rec}))
    rec["copied"] = copied
    return rec
