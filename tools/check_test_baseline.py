#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试基线门禁(2026-09-13 基线归零起): 失败条数不增 + 每条失败/skip 必须登记。

为什么要有它:
  旧口径是"逐条同基线(保证不新增, 不保证清零)" —— **只比条数、不比内容**,
  于是"14 个基线失败"稳定多轮没人盘, 噪声里新增也看不出来
  (上一轮误归档 6 个在用模块时, 条数一度涨到 16 才被发现)。
新门禁三条:
  1. 失败条数 > 台账登记数(N) → 红
  2. 有失败但未在 failure_ledger.json 登记(性质/owner/计划) → 红
  3. 出现未在 skip_ledger.json 登记的 skip → 红(skip 不许当垃圾桶)

用法:
  python3 tools/check_test_baseline.py                  # 跑全量并判定
  python3 tools/check_test_baseline.py --no-run          # 只校验台账格式
  python3 tools/check_test_baseline.py --pytest-args "tests/unit -q --tb=no"
退出码: 0 通过 / 1 不通过
"""
# G-02 留痕/告警（2026-09-17 · Windows 侧第一版）:
#   只**记录/告警**, **不参与判定** —— 判据仍是下方 4 条 bad 规则 + 退出码逻辑，未改一行。
#   记录: pytest 退出码 / 收集数 / 收集期错误行 / warnings / reported_pass / human_confirmed_pass（留空待人工）。
#   为什么: 失败可能被“吞”——部分收集失败时 rc!=1、收集错误行无 `::` 不进 failed 名单
#   ⇒ 门禁自称的 PASS 严格只能算 **reported PASS**，第四问（收集阶段有无异常）
#   必须人工补齐后另记 **human_confirmed_pass**。
#   证据等级: 【实测】D:\clawsjoy_v9 · Windows 11 + PowerShell 5.1 + Python 3.12 · 2026-09-17。
#
# X-03 防复发(2026-09-18 · 老板拍定「做」):
#   新增「文件编码显式化债务」AST 扫描(tools/check_encoding_explicit.py), 同样**只告警不改判定**;
#   结果进 warnings + last_run.json 的 encoding_debt 字段, 不进 bad 列表、不改退出码。
#   为什么: X-03 存量(产品侧 11 处)修完后必须防新增, 否则下一批代码又长出同类债务。
#
# G-02 子项⑤(2026-09-18 · 老板拍定「做」): **漏解析自检**。
#   首跑实测: counts.failed=25 而只解析到 24 条 nodeid ⇒ 差额那条被误判成「台账陈旧」⇒ **假红**
#   (同族于「假绿」: 判定依据与实际证据不一致)。修法=只把差额暴露成 WARN, **判定层/退出码一行不动**。
#   证据等级: 【实测】2026-09-18 · data/test_baseline/last_run.json 首跑 vs 复跑对照。
#
# G-02 子项⑥(2026-09-18 · 老板/DS 拍「修法 A」): **汇总口径 = 全文取最后一条汇总行**。
#   实测(同一批代码三次全量跑, 三种形态): ①假红(汇总 25 / 解析 24) ②**假绿**——产品侧 cp936 下
#   打印 emoji 抛 UnicodeEncodeError, 垫片把降级报错打在汇总行**之后** ⇒ 旧「只读末行」写法手里
#   counts 读成 {} 而门禁**仍判 ✅**(PASS 由 nodeid 名单决定) ⇒ 证据残缺却报绿 ③正常。
#   修法(只动「汇总从哪儿读」): 末行 → 全文最后一条汇总行(找不到回落末行, 行为与旧版逐字一致)
#   + 末行≠汇总行时印一条**非告警**的注 + last_run.json 记 summary_off_last_line(为「要不要上
#   判定 B」积累实测数据)。**判定层/退出码/台账一行未动**(老板 2026-09-18 拍: 只做 A, B 等数据)。
#   为什么不加 WARN: 汇总既然能从全文找到 ⇒ 此处**没有问题**, 报警即「假警报」(与假绿同等有害)。
#   证据等级: 【实测】2026-09-18 · data/tmp/gate_r5|r6|r7.txt; 反例证明 data/tmp/g02_proof_a.py。
#
# G-02 子项⑥ 续(2026-09-18 · 老板/DS 拍「做」): **证据不完整时把原始 stdout 落盘**。
#   为什么要: 漏解析/汇总缺失时日志里只有「差额 1」, **看不到那一行长什么样** ⇒ 机制无法定位
#   (本批 5 次跑 3 次命中「汇总 N / 解析 N-1」, 却始终拿不到被污染的那一行)。
#   口径: **纯留痕** —— 不改判定/退出码/台账; 只在「证据可能不完整」时留存(时间戳文件, 只留最新
#   _RAW_KEEP 份); 正常跑不堆积(只留一份滚动 raw_last.txt, 在 data/ = gitignored)。
#   证据等级: 【实测】2026-09-18 · tests/unit/test_gate_raw_stdout_kept.py; 门禁 data/tmp/gate_r12.txt。
import argparse
import datetime
import json
import pathlib
import re
import shutil
import subprocess
import sys

_REPO = pathlib.Path(__file__).resolve().parent.parent

# Windows(2026-09-17): 本脚本自身也打印 emoji(✅/❌)。中文 GBK 控制台编码不了 emoji,
# 会 UnicodeEncodeError 让门禁在**最后一行结论**上崩掉(判定其实已经算完)。
# 复用产品侧同一个垫片; 这里用**按路径加载**而不是 `import core.console_utf8` ——
# 后者会执行 core/__init__.py, 连带拉起 chromadb + 向量中心(慢, 且会去碰 data/
# 下的文件锁), 对纯门禁工具是负担。
import importlib.util as _importlib_util

_shim_spec = _importlib_util.spec_from_file_location(
    "_cj_console_utf8", _REPO / "core" / "console_utf8.py"
)
_cj_shim = _importlib_util.module_from_spec(_shim_spec)
_shim_spec.loader.exec_module(_cj_shim)
_cj_shim.ensure_utf8_console()
# 台账**入库**(tests/baseline/, "登记"是可 review 的动作); 运行产物写 data/(gitignored)
_LEDGER = _REPO / "tests" / "baseline"
_RUN_DIR = _REPO / "data" / "test_baseline"
_STATUS_RE = re.compile(r"^(\S+::\S+)\s+(PASSED|FAILED|SKIPPED|ERROR|XFAIL|XPASS)\b")
# G-02(2026-09-17): 一并计入 xfailed/xpassed/errors —— 否则正常跑会因「收集 1756 > 已统计 1755」
# 报假警告（简单说就是那 1 条 xfailed）。仅影响留痕统计，不参与判定。
_SUMMARY_RE = re.compile(r"(\d+) (failed|passed|skipped|errors?|xfailed|xpassed)")
# 子项⑥ 修法 A: 汇总**行**的形态判据 —— 比 _SUMMARY_RE 多一个「时长尾」(`in <秒>`)。
# 为什么要多这一层: _SUMMARY_RE 在**短摘要行**(例 `FAILED tests/x.py::t - AssertionError: 3 failed items`)
# 与**参数化 id**(例 `t[3 passed cases] PASSED`)上都会误配 ⇒ 单靠它挑不出「哪一行才是汇总行」。
_SUMMARY_LINE_RE = re.compile(r"\d+ (?:failed|passed|skipped|errors?|xfailed|xpassed)\b.*\bin \d")
_COLLECTED_RE = re.compile(r"collected (\d+) items")
# 子项⑥ 续: 证据不完整时留存的原始 stdout 最多保留几份（文件名以时间戳开头 ⇒ 按名排序即按时间）
_RAW_KEEP = 5


def _load(path):
    if not path.exists():
        print(f"[GATE] 缺台账: {path}")
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def _locate_summary(stdout):
    """G-02 子项⑥（修法 A）：从**全文**里定位 pytest 汇总行。

    为什么不能只取末行：任何在汇总行**之后**打印的内容（实测：产品侧 cp936 下打印 emoji 抛
    UnicodeEncodeError，垫片把降级报错打在汇总行之后）都会把末行顶掉 ⇒ 旧写法手里 `counts`
    **全空**，而门禁仍判 ✅（PASS 由 nodeid 名单决定）—— **证据残缺却报绿**。
    规则：取**最后一条**「像汇总行」的行（`_SUMMARY_LINE_RE`，带时长尾以避免误配短摘要/参数化 id）；
    一条都没有就**回落末行**（行为与旧版逐字一致，不引入新失败面）。

    返回：(summary, tail, off_last_line) —— summary 为空串表示**全文都没找到**汇总行。
    （本函数只服务「留痕/告警」；**判定层不引用它**，见 tests/unit/test_gate_summary_locate.py 的静态判据。）
    """
    lines = [l.strip() for l in stdout.strip().splitlines()]
    tail = lines[-1] if lines else ""
    summary = ""
    for line in lines:
        if _SUMMARY_LINE_RE.search(line):
            summary = line
    return summary, tail, bool(summary) and summary != tail


def _run_pytest(extra):
    cmd = [sys.executable, "-m", "pytest", "-v", "--tb=no", "-p", "no:cacheprovider"]
    if extra:
        cmd += extra.split()
    else:
        cmd += ["tests/"]
    print("[GATE] " + " ".join(cmd))
    # Windows(2026-09-17): 子进程 pytest 的 stdout 已被产品侧垫片切成 UTF-8, 而 text=True
    # 是按 locale(cp936) 解码 —— 一旦输出里带中文(失败断言文本), 这里就
    # UnicodeDecodeError 崩掉。显式 utf-8 + errors=replace: 解析只依赖 ASCII 的
    # "nodeid PASSED/FAILED" 与汇总行, 个别字符降级不影响判定。
    p = subprocess.run(cmd, cwd=str(_REPO), capture_output=True, encoding="utf-8", errors="replace")
    failed, skipped, counts = [], [], {}
    for line in p.stdout.splitlines():
        m = _STATUS_RE.match(line.strip())
        if m:
            _id, _st = m.group(1), m.group(2)
            if _st in ("FAILED", "ERROR"):
                failed.append(_id)
            elif _st == "SKIPPED":
                skipped.append(_id)
    # 子项⑥ 修法 A: 汇总口径 = **全文取最后一条汇总行**（一条都没有才回落末行），
    # 而不是旧版的「只读末行」—— 末行被别的输出顶掉时，旧写法会把 counts 读空。
    summary, tail, off_last_line = _locate_summary(p.stdout)
    for n, k in _SUMMARY_RE.findall(summary or tail):
        counts[k] = int(n)
    # G-02 留痕: 收集数 + 收集期错误行（无 `::`，故不会进 failed 名单）
    collected = None
    _m_col = _COLLECTED_RE.search(p.stdout)
    if _m_col:
        collected = int(_m_col.group(1))
    collect_errors = [s for s in (l.strip() for l in p.stdout.splitlines())
                      if s.startswith("ERROR ") and "::" not in s]
    # 子项⑥ 续: 先落一份**滚动**原始 stdout（data/ 是 gitignored）。是否**留存**由 main 按
    # 「证据是否完整」决定 ⇒ 正常跑不堆积。写失败不打扰判定（最外层 try）。
    try:
        _RUN_DIR.mkdir(parents=True, exist_ok=True)
        (_RUN_DIR / "raw_last.txt").write_text(p.stdout, encoding="utf-8")
    except Exception:
        pass
    return (failed, skipped, counts, summary, tail, off_last_line,
            p.returncode, collected, collect_errors)


def _keep_raw_stdout(gaps):
    """G-02 子项⑥ 续（2026-09-18 拍）：证据不完整时把**原始 stdout** 留存一份。

    为什么：漏解析 / 汇总缺失时，日志里只有「差额 1」，**看不到那一行长什么样** ⇒ 机制无法定位。
    口径：**纯留痕**（不改判定 / 退出码 / 台账）；只保留最新 `_RAW_KEEP` 份（文件名以时间戳开头，
    按名排序即按时间）；正常跑不留存（不堆积）。

    返回：留存件的**仓库相对路径**；源文件（滚动副本）不存在时返回 None。
    """
    src = _RUN_DIR / "raw_last.txt"
    if not src.exists():
        return None
    d = _RUN_DIR / "raw"
    d.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    dst = d / ("%s_%s.txt" % (stamp, "-".join(gaps) or "evidence"))
    shutil.copyfile(str(src), str(dst))
    olds = sorted(d.glob("*.txt"))
    if _RAW_KEEP > 0:
        for old in olds[:-_RAW_KEEP]:
            try:
                old.unlink()
            except OSError:
                pass
    try:
        return str(dst.relative_to(_REPO))
    except ValueError:
        return str(dst)


def _parse_selfcheck(counts, failed):
    """G-02 子项⑤：判定用的 failed 名单与 pytest 汇总口径是否一致（**只算告警文本**）。

    为什么需要它：pytest 汇总行给的是**条数**，而判定用的是**逐条 nodeid**。两者不一致时，
    「台账陈旧」的红可能是**假红**（漏解析 ≠ 真修好），也可能掩盖**漏登记**。
    规则：**宁可不报，也不报假警报** —— 口径一致或无法判定时返回 None。
    返回：告警文本；None 表示无需告警。（本函数**不参与判定**，调用点只 append 到 warnings）
    """
    exp = None
    for k in ("failed", "error", "errors"):
        if k in counts:
            try:
                exp = (exp or 0) + int(counts[k])
            except (TypeError, ValueError):
                return None
    if exp is None:
        if failed:
            return ("解析自检: 解析到 %d 条失败, 但全文都没有 failed/errors 计数(汇总形态异常)"
                    " —— 判定依据可能不完整, 请人工核对 -v 输出" % len(failed))
        return None
    if exp == len(failed):
        return None
    return ("解析自检: 汇总 failed/errors=%d 但只解析到 %d 条 nodeid(差额 %d)"
            " —— 判定用的名单可能不完整(既可能漏登记, 也可能把「台账陈旧」判成假红), 请人工核对 -v 输出"
            % (exp, len(failed), exp - len(failed)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-run", action="store_true", help="只校验台账格式, 不跑测试")
    ap.add_argument("--pytest-args", default="", help="覆盖 pytest 参数(默认 tests/ -v)")
    a = ap.parse_args()

    fl = _load(_LEDGER / "failure_ledger.json")
    sl = _load(_LEDGER / "skip_ledger.json")
    known = {e["id"]: e for e in fl.get("known_failures", [])}
    known_skip = {e["id"]: e for e in sl.get("skips", [])}
    print(f"[GATE] 登记失败 {len(known)} 条 / 登记 skip {len(known_skip)} 条")
    if a.no_run:
        print("[GATE] --no-run: 台账格式 OK")
        return 0

    (failed, skipped, counts, summary, tail, off_last_line,
     rc, collected, collect_errors) = _run_pytest(a.pytest_args)
    # 子项⑥: 印**汇总行**（全文都没找到才印末行）。旧写法一律印末行 ⇒ 末行被顶掉时，
    # 门禁的头条会变成一条无关输出（实测就是那行 cp936 报错），读的人无从判断。
    print(f"[GATE] {summary or tail}")
    # 子项⑥ 续: 收集「证据可能不完整」的**理由**；空 ⇒ 正常跑，不必留存原始 stdout
    gaps = []
    if off_last_line:
        print("[GATE] 注: 汇总行不在末行（已从全文定位；末行另有输出）"
              " —— 旧「只读末行」口径在这里会把 counts 读空（**不是告警**，判定未受影响）")
        gaps.append("summary_off_last_line")

    # --- G-02 留痕/告警：只记录与告警，**不改判定**（bad 列表与退出码逻辑未动）---
    warnings = []
    if rc not in (0, 1):
        warnings.append(f"pytest 退出码 {rc}（非 0/1：中断/内部错误/用法错误）—— 本轮结果可能不完整")
        gaps.append("pytest_rc")
    if collected is None:
        warnings.append("未能解析收集数（collected N items 缺失）—— 是否部分收集失败需人工确认")
        gaps.append("collected_missing")
    else:
        _accounted = sum(counts.values())
        if _accounted < collected:
            warnings.append(f"已统计 {_accounted} < 收集数 {collected}：差额 {collected - _accounted} 条未归类（常见: xfailed/xpassed/error）")
            gaps.append("counts_short")
    if collect_errors:
        warnings.append(f"收集期错误行 {len(collect_errors)} 条: " + "; ".join(collect_errors[:3]))
        gaps.append("collect_errors")
    # --- X-03 防复发（2026-09-18）：文件编码显式化债务 —— 与 G-02 同一规矩：**只告警，不改判定** ---
    #   判据在 tools/check_encoding_explicit.py（AST，只报不改）；基线台账 tests/baseline/encoding_explicit_baseline.json。
    #   为什么: X-03 存量修完后必须防**新增**，否则下一批代码又会长出 `open()` 不带 encoding 的同类债务。
    #   边界: 新增只进 warnings 与 last_run.json 的 encoding_debt 字段，**不进 bad 列表、不改退出码**（老板 2026-09-18 拍定）。
    encoding_debt = None
    try:
        _enc_spec = _importlib_util.spec_from_file_location(
            "_cj_encoding_scan", _REPO / "tools" / "check_encoding_explicit.py")
        _enc_mod = _importlib_util.module_from_spec(_enc_spec)
        _enc_spec.loader.exec_module(_enc_mod)
        encoding_debt = _enc_mod.scan_summary(_REPO)
        print("[GATE] X-03 编码扫描(只报): %d 个 .py / 命中 %d / 基线内 %d / 新增 %d / 未判定 %d"
              % (encoding_debt["scanned_files"], encoding_debt["total"], encoding_debt["allowed"],
                 len(encoding_debt["new_findings"]), encoding_debt["unresolved_attr_open"]))
        if encoding_debt["new_findings"]:
            _shown = ", ".join("%s:%d" % (f["file"], f["line"]) for f in encoding_debt["new_findings"][:5])
            warnings.append("X-03 编码显式化债务新增 %d 处: %s%s（请补 encoding=\"utf-8\"；口径见 tools/check_encoding_explicit.py）"
                            % (len(encoding_debt["new_findings"]), _shown,
                               " …" if len(encoding_debt["new_findings"]) > 5 else ""))
        elif encoding_debt["baseline_state"] != "ok":
            warnings.append("X-03 编码基线不可读(%s) —— 新增债务无法对照，请检查 tests/baseline/encoding_explicit_baseline.json"
                            % encoding_debt["baseline_state"])
    except Exception as _e:  # 扫描器自身出问题也不能把门禁搞红（只告警）
        warnings.append("X-03 编码扫描未执行: %r" % (_e,))
    # --- G-02 子项⑤：漏解析自检（只告警）---
    _selfcheck = _parse_selfcheck(counts, failed)
    if _selfcheck:
        warnings.append(_selfcheck)
        gaps.append("parse_selfcheck")
    for _w in warnings:
        print(f"[GATE][WARN] {_w}")
    # 子项⑥ 续（2026-09-18 拍）：证据不完整 ⇒ 把原始 stdout **留存**一份（纯留痕，不改判定）
    _raw_kept = None
    if gaps:
        try:
            _raw_kept = _keep_raw_stdout(gaps)
        except Exception as _e:      # 留存失败也不能把门禁搞红（与 X-03 扫描同规矩）
            warnings.append("原始 stdout 留存失败: %r" % (_e,))
        if _raw_kept:
            print(f"[GATE] 注: 证据可能不完整({', '.join(gaps)}) ⇒ 原始 stdout 已留存: {_raw_kept}"
                  "（**不是告警**，判定未受影响）")
    print("[GATE] 证据范围: 上行 PASS 仅覆盖 ①②③ 三问；第④问（收集阶段）只留痕不判定，见 last_run.json")

    bad = []
    # 1) 条数
    if len(failed) > len(known):
        bad.append(f"失败条数 {len(failed)} > 台账登记 {len(known)}")
    # 2) 未登记失败
    unregistered = [t for t in failed if t not in known]
    if unregistered:
        bad.append("未登记失败(必须先登记性质/owner/计划): " + ", ".join(unregistered))
    # 3) 已登记但已修好的(台账要摘除, 防"登记了就一直挂着")
    stale = [t for t in known if t not in failed]
    if stale:
        bad.append("台账已登记但当前不再是失败(请从 known_failures 摘到 resolved): " + ", ".join(stale))
    # 4) 未登记 skip
    unreg_skip = [t for t in skipped if t not in known_skip]
    if unreg_skip:
        bad.append("未登记 skip: " + ", ".join(unreg_skip))
    miss_skip = [t for t in known_skip if t not in skipped]
    if miss_skip:
        bad.append("台账登记 skip 但当前已有结果(请更新 skip_ledger.json): " + ", ".join(miss_skip))

    _RUN_DIR.mkdir(parents=True, exist_ok=True)
    (_RUN_DIR / "last_run.json").write_text(
        json.dumps(
            {
                "ts": datetime.datetime.now().isoformat(timespec="seconds"),
                "counts": counts,
                # 子项⑥ 留痕：汇总行是否**不在末行**（为「要不要上判定 B」积累实测数据；非告警）
                "summary_off_last_line": off_last_line,
                "failed": failed,
                "skipped": skipped,
                "pytest_rc": rc,
                "collected": collected,
                "collect_errors": collect_errors,
                "evidence_gaps": gaps,
                "raw_stdout_kept": _raw_kept,
                "warnings": warnings,
                "encoding_debt": encoding_debt,
                "reported_pass": not bad,
                "human_confirmed_pass": None,
                "human_confirmed_note": "需人工补齐第④问（收集数/退出码/末行形态）后填写；"
                                       "门禁自报的 reported_pass 不可单独用于验收",
                "registry": {"known_failures": len(known), "known_skips": len(known_skip)},
                "verdict": "PASS" if not bad else "FAIL",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    if bad:
        print("\n[GATE] ❌ 不通过:")
        for b in bad:
            print("  - " + b)
        return 1
    print(f"\n[GATE] ✅ 通过(reported PASS): 失败 {len(failed)} 条全部已登记 · skip {len(skipped)} 条全部已登记 · 台账与实际一致")
    print("[GATE] 注: 上行为 reported PASS（门禁自报），不等于 human_confirmed_pass（人工确认）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
