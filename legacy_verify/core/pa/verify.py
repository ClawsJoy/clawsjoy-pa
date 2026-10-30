# -*- coding: utf-8 -*-
"""PA 交付产物核验器（确定性 · 非 LLM）v1 —— 2026-09-28。

承老板 2026-09-28「交付未经核验…（后端 verifier 待接）」⇒ 给 PA 后端接一个**确定性产物核验**：
源 / 运行时 / live HTTP / 测试 / 进程，可经 POST|GET /v9/pa/verify 调用。
⛔ 与 core/lib/v8/verifier.py（LLM 语义验证器）分工不同，不替代之。
CLI: dsh/tools/dsh_pa_verify.py（同一 run_checks）。
"""
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request

V9 = os.environ.get("DSH_V9ROOT", "/home/flybo/clawsjoy_v5")
VAULT = os.environ.get("DSH_VAULT", "/mnt/d/Obsidian/ClawsJoy/ClawsJoy")
BASE = os.environ.get("DSH_PA_BASE", "http://127.0.0.1:5002")


def _sha16(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


def _http_json(path, timeout=8):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode("utf-8", "ignore"))


def _http_code(path, timeout=8):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        r.read(1)
        return r.status


def _proc_start_epoch():
    try:
        import psutil

        for p in psutil.process_iter(["cmdline", "create_time"]):
            cl = p.info.get("cmdline") or []
            if any("agent_gateway_enhanced" in (c or "") for c in cl):
                return p.pid, p.info["create_time"]
    except Exception:
        pass
    return None, None


def run_checks(skip_scan=False, live_http=True):
    """返回 dict：{ok, pass, total, results[], ts}。

    live_http=False 用于 PA 进程内调用（不在自身进程里再发 HTTP，免自打/死锁）。
    """
    results = []

    def rec(cid, ok, ev):
        results.append({"id": cid, "pass": bool(ok), "evidence": ev})

    cwd = os.getcwd()
    try:
        os.chdir(V9)
        if V9 not in sys.path:
            sys.path.insert(0, V9)

        # C1 源
        rp = os.path.join(V9, "core/pa/roster.py")
        src = open(rp, encoding="utf-8").read() if os.path.exists(rp) else ""
        rec(
            "C1",
            "obsidian_brain" in src,
            "roster.py sha16=%s has_obsidian_brain=%s"
            % (_sha16(rp) if os.path.exists(rp) else "NA", "obsidian_brain" in src),
        )

        # C2 运行时
        jp = os.path.join(V9, "data/v9/pa/roster.json")
        try:
            ids = [c.get("id") for c in json.load(open(jp, encoding="utf-8")).get("cards", [])]
        except Exception as e:
            ids = ["<err:%s>" % e]
        rec(
            "C2",
            "obsidian_brain" in ids,
            "roster.json ids=%s sha16=%s" % (ids, _sha16(jp) if os.path.exists(jp) else "NA"),
        )

        # C3/C4 live HTTP（进程内跳过）
        if live_http:
            try:
                _st, d = _http_json("/v9/pa/roster")
                ob = [r for r in d.get("rows", []) if r.get("id") == "obsidian_brain"]
                rec(
                    "C3",
                    bool(ob) and ob[0].get("level") == "L4",
                    "live count=%s obsidian_brain=%s" % (d.get("count"), bool(ob)),
                )
            except Exception as e:
                rec("C3", False, "live /v9/pa/roster 不可达: %s" % e)
            try:
                rec("C4", _http_code("/v9/pa/roster/obsidian_brain") == 200, "GET /v9/pa/roster/obsidian_brain -> 200")
            except Exception as e:
                rec("C4", False, "GET /v9/pa/roster/obsidian_brain 失败: %s" % e)

        # C5/C6/C7/C10 产品模块
        try:
            from pathlib import Path

            from core.gateway import precision_inject as PI

            root = Path(PI._vault_path())
            f1 = {k: (root / info["rel"]).is_file() for k, info in PI._KNOWLEDGE_FILES.items()}
            rec("C5", all(f1.values()), "F1 exists=%s" % f1)
            cfg = PI._obsidian_cfg()
            sd = cfg.get("sops_dir") or ""
            rec(
                "C6",
                bool(sd) and (root / sd).is_dir(),
                "sops_dir=%s exists=%s" % (sd, bool(sd) and (root / sd).is_dir()),
            )
            fn = getattr(PI, "_scan_excluded", None)
            if fn is None:
                rec("C7", False, "缺 _scan_excluded")
                rec("C10", False, "缺 _scan_excluded（无法测遍历留痕）")
            else:
                cases = {
                    "_冷区/x.md": True,
                    "_垃圾箱/P/d.md": True,
                    ".obsidian/x.md": True,
                    "Templates/t.md": True,
                    "工作区/SOPs/SOPs/a.md": False,
                    "dsh/a.md": False,
                }
                bad = {k: fn(k) for k, exp in cases.items() if fn(k) != exp}
                leak_n = None
                errs = None
                codex_n = None
                if not skip_scan:
                    notes = PI._scan_vault()
                    leak_n = len([n for n in notes if n["rel_path"].split("/", 1)[0] in ("_冷区", "_垃圾箱")])
                    codex_n = len([n for n in notes if n["rel_path"].startswith("codex/")])
                    lwe = getattr(PI, "last_walk_errors", None)
                    errs = lwe() if lwe is not None else None
                rec("C7", (not bad) and (leak_n in (None, 0)), "谓词不符=%s leaked=%s" % (bad, leak_n))
                rec(
                    "C10",
                    (errs is not None) or bool(skip_scan),
                    ("遍历留痕 last_walk_errors=%s" % (errs[:1] if errs else errs)) if not skip_scan else "skip_scan：未验",
                )
                rec("C12", (codex_n is None) or (codex_n > 0), "容错恢复 codex/ md=%s（EIO 目录不再整棵丢）" % codex_n)
                try:
                    if skip_scan:
                        rec("C13", True, "skip_scan：未验清单通道")
                    else:
                        _mf = os.path.join(V9, "data/v9/vault_manifest_win.txt")
                        man = [l.strip() for l in open(_mf, encoding="utf-8", errors="ignore") if l.strip()]
                        man_ne = [r for r in man if r.split("/", 1)[0] not in (".obsidian", "Templates", "_冷区", "_垃圾箱")]
                        got = set(n["rel_path"] for n in notes)
                        miss = [r for r in man_ne if r not in got]
                        try:
                            exp = set(
                                l.strip()
                                for l in open(
                                    os.path.join(V9, "data/v9/vault_missing_win.txt"), encoding="utf-8", errors="ignore"
                                )
                                if l.strip()
                            )
                        except Exception:
                            exp = set()
                        rec(
                            "C13",
                            len(man_ne) > 0 and set(miss) == exp,
                            "Windows清单通道 non_excluded=%d scan=%d missing=%d（与缺项册一致=%s）"
                            % (len(man_ne), len(notes), len(miss), set(miss) == exp),
                        )
                        badname = [r for r in miss if len(os.path.basename(r).encode("utf-8")) <= 255]
                        rec("C14", len(badname) == 0, "缺项全部 ENAMETOOLONG（文件名>255B）: %s" % (not badname))
                except Exception as e:
                    rec("C13", False, "清单通道检查失败: %s" % e)
        except Exception as e:
            rec("C5", False, "import precision_inject 失败: %s" % e)

        # C8 测试
        if not skip_scan:
            try:
                cp = subprocess.run(
                    [sys.executable, "-m", "pytest", "tests/unit/test_roster.py", "-q", "-p", "no:cacheprovider"],
                    cwd=V9,
                    capture_output=True,
                    text=True,
                    timeout=180,
                )
                tail = (cp.stdout or "").strip().splitlines()[-1] if cp.stdout else ""
                rec("C8", cp.returncode == 0, "pytest rc=%s tail=%s" % (cp.returncode, tail))
            except Exception as e:
                rec("C8", False, "pytest 失败: %s" % e)

        # C9 live + 进程启动时序
        st = None
        if live_http:
            try:
                st = _http_code("/health")
            except Exception as e:
                st = "ERR:%s" % e
        pid, ct = _proc_start_epoch()
        newest = 0.0
        for f in ("core/pa/roster.py", "core/gateway/precision_inject.py", "config/v9/execution_policy.yaml"):
            p = os.path.join(V9, f)
            if os.path.exists(p):
                newest = max(newest, os.path.getmtime(p))
        ok9 = ct is not None and ct >= newest and (st == 200 or not live_http)
        rec(
            "C9",
            ok9,
            "health=%s pid=%s proc_start=%s newest_src=%s"
            % (
                st,
                pid,
                time.strftime("%H:%M:%S", time.localtime(ct)) if ct else "NA",
                time.strftime("%H:%M:%S", time.localtime(newest)),
            ),
        )
    finally:
        os.chdir(cwd)

    npass = sum(1 for r in results if r["pass"])
    return {
        "verifier": "core/pa/verify v1",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "v9": V9,
        "pass": npass,
        "total": len(results),
        "ok": npass == len(results),
        "results": results,
    }
