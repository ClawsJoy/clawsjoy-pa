#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""编号连续性检查（体检项 34 工具化，2026-09-13 批66）。

为什么需要它：批60 台账写明「新增体检项（入库为 29）」，但库里根本没有第 29 条
（编号 1-28 之后直接跳到 30，空了 29）—— 当时只执行了写入动作就登记结果，**没有回读**。
序列化编号（体检项/工单/基线条目）的**连续性是最便宜的完整性检查**：缺号即报警。

用法：
    python tools/check_ledger_numbering.py            # 检查默认目标
    python tools/check_ledger_numbering.py <path>...  # 检查指定文件
    python tools/check_ledger_numbering.py --selftest # 自检（含造缺号样本）

退出码：0 = 全部编号连续；非 0 = 有缺号或读取失败。
"""
import argparse
import glob
import os
import re
import sys
import tempfile

# 体检项库在 vault（仓库外）⇒ **路径唯一真源 = core.lib.paths.vault_root()**（2026-09-28 成对改）。
# 为什么改：此前默认值写死 WSL 形态 `/mnt/d/...`（见下方兜底）⇒ 在 Windows 侧它解析成
# `D:\mnt\d\...`，既不抛错也找不到真件 ⇒ 工具报「文件不存在」（**判据在场却打错对象**
# ⇒ Win 侧实为坏件）。覆盖：`CLAWSJOY_HEALTH_LIB` 仍**优先**（保留既有能力）。
def _default_health_lib():
    env = os.environ.get("CLAWSJOY_HEALTH_LIB")
    if env:
        return env
    _repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _repo not in sys.path:
        sys.path.insert(0, _repo)
    try:
        from core.lib.paths import vault_root
        return str(vault_root() / "收件箱" / "体检项库_V9.md")
    except Exception:
        # 兜底只留给「真源不可 import」的环境；⛔ 它**不是**权威值（真源在上）
        return "/mnt/d/Obsidian/ClawsJoy/ClawsJoy/收件箱/体检项库_V9.md"


DEFAULT_TARGETS = [
    _default_health_lib(),
]

_ROW_MD = re.compile(r"^\|\s*(\d+)\s*\|", re.M)  # markdown 表格行: | 12 | ...
_ID_JSON = re.compile(r'"(?:no|id|index|seq)"\s*:\s*(\d+)')  # json 里的编号字段


def extract_numbers(path):
    """按扩展名选择抽取方式；返回 (编号列表, 错误说明或 None)。"""
    if not os.path.exists(path):
        return [], "文件不存在"
    try:
        text = open(path, encoding="utf-8").read()
    except Exception as exc:
        return [], "读取失败: %s" % exc
    if path.endswith(".md"):
        # 只扫**条目表**：跳过「明细/引用」类小节 ——
        # 那里会**引用**条目编号（如去重明细表写「2 | 合并了…」），扫进去就是误报。
        # 这是体检项 5（判据必配防误伤用例）的实例：真实数据里存在合法例外。
        nums = []
        skip = False
        for line in text.split("\n"):
            if line.startswith("#"):
                skip = any(k in line for k in ("明细", "引用", "说明", "索引"))
                continue
            if skip:
                continue
            m = _ROW_MD.match(line)
            if m:
                nums.append(int(m.group(1)))
        return nums, None
    if path.endswith(".json") or path.endswith(".jsonl"):
        return [int(n) for n in _ID_JSON.findall(text)], None
    return [], "不支持的类型（只支持 .md / .json / .jsonl）"


def check_file(path, quiet=False):
    """返回 (ok, message)。ok=False 表示缺号或不可读。"""
    nums, err = extract_numbers(path)
    name = os.path.basename(path)
    if err:
        return False, "%s: %s" % (name, err)
    if not nums:
        return True, "%s: 未发现编号（跳过，不视为缺号）" % name
    uniq = sorted(set(nums))
    lo, hi = uniq[0], uniq[-1]
    gaps = [i for i in range(lo, hi + 1) if i not in uniq]
    dups = sorted({n for n in nums if nums.count(n) > 1})
    if gaps:
        return False, "%s: 缺号 %s（区间 %d-%d 共 %d 个编号）" % (name, gaps, lo, hi, len(uniq))
    extra = "；重复编号 %s" % dups if dups else ""
    return True, "%s: 编号 %d-%d 连续（%d 条）%s" % (name, lo, hi, len(uniq), extra)


def _selftest():
    """自检：造一个缺号样本必须报错；正常样本必须通过。"""
    print("=== 自检 ===")
    fails = []
    with tempfile.TemporaryDirectory() as d:
        gap = os.path.join(d, "gap.md")
        open(gap, "w", encoding="utf-8").write("| # | 项 |\n|---|---|\n| 1 | a |\n| 2 | b |\n| 4 | d |\n")
        ok, msg = check_file(gap)
        print("  [缺号样本] ok=%s  %s" % (ok, msg))
        if ok:
            fails.append("缺号样本未被检出（工具失效）")
        good = os.path.join(d, "good.md")
        open(good, "w", encoding="utf-8").write("| # | 项 |\n|---|---|\n| 1 | a |\n| 2 | b |\n| 3 | c |\n")
        ok2, msg2 = check_file(good)
        print("  [正常样本] ok=%s  %s" % (ok2, msg2))
        if not ok2:
            fails.append("正常样本被误报")
    if fails:
        for f in fails:
            print("  !! %s" % f)
        print("自检失败")
        return 1
    print("自检通过")
    return 0


def main():
    ap = argparse.ArgumentParser(description="编号连续性检查（体检项 34）")
    ap.add_argument("paths", nargs="*", help="要检查的文件（默认: 体检项库）")
    ap.add_argument("--selftest", action="store_true", help="自检")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()

    targets = args.paths or DEFAULT_TARGETS
    targets += sorted(glob.glob("data/test_baseline/*.json"))
    targets += sorted(glob.glob("tests/baseline/*.json"))
    if not targets:
        print("[编号检查] 无可检查目标")
        return 0

    bad = 0
    for t in targets:
        ok, msg = check_file(t)
        print(("  [OK]   " if ok else "  [缺号] ") + msg)
        if not ok:
            bad += 1
    print("[编号检查] %d 个目标, %d 个异常" % (len(targets), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
