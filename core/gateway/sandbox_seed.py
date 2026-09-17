# -*- coding: utf-8 -*-
"""剥离层判据 1 · Seed 检查（B 口径 · S1 定向 seed + **manifest 加固**）。

真实反例：PA 在空骨架沙箱里做「盘点项目」并给结论 ⇒ 判据：未 seed/空骨架/来源不可读 ⇒ BLOCKED。
老板补充反例：**空骨架 + 伪造 seed 标记 ⇒ 不得仅凭标记放行** ⇒ 因此必须有 manifest 校验：
  seed 记录 {source_path, seed_at, commit, scope, file_count, manifest_hash}；
  check_seed 会**重算沙箱 manifest 并比对**，对不上 / 文件数远少于 manifest ⇒ BLOCKED（标记不足以放行）。
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


def _files(root, scope=None):
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
            out.append(p)
    # 注意：**不要**在这里按"仅文档后缀"过滤根下文件 —— 该过滤只适用于**仓根**的顶层文件，
    # 由 seed_sandbox 单独处理；否则会漏拷每个 scope 目录的**直属文件**（实测 bug）。
    return sorted(set(out))


def manifest_of(root, scope=None):
    """清单：文件数 + 相对路径/大小 的 sha256（用于"标记与内容一致"校验）。"""
    root = Path(str(root))
    fs = _files(root, scope)
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
    if not ev["manifest_hash"]:
        return {"ok": False, "status": "blocked",
                "reason": "seed 无 manifest_hash（只有标记、无内容凭据）=> BLOCKED（防伪造标记）", "evidence": ev}
    scope = seed.get("scope") or SEED_SCOPE
    cur = manifest_of(sb, scope)
    exp_n = int(seed.get("file_count") or 0)
    ev["manifest_current"] = cur["file_count"]
    if cur["manifest_hash"] != ev["manifest_hash"]:
        return {"ok": False, "status": "blocked",
                "reason": "seed 标记与沙箱内容不符（manifest 不匹配：期望 %s，实测 %s 个文件）" % (exp_n, cur["file_count"]),
                "evidence": ev}
    ev["manifest_ok"] = True
    if ev["file_count"] == 0:
        return {"ok": False, "status": "blocked", "reason": "沙箱为空骨架（0 文件）", "evidence": ev}
    return {"ok": True, "status": "seeded", "reason": "已绑定主体项目（manifest 校验通过）", "evidence": ev}


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
    m = manifest_of(sb, scope)
    rec = {"source_path": str(src), "seed_at": _t.strftime("%Y-%m-%d %H:%M:%S"),
           "commit": str(commit or ""), "scope": scope,
           "file_count": m["file_count"], "manifest_hash": m["manifest_hash"]}
    update_json(sb / ".agent_state.json", lambda _d: _d.update({"seed": rec}))
    rec["copied"] = copied
    return rec
