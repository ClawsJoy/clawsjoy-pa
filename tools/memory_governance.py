#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""永久记忆数据治理(方案B) — 合并孤儿文件到用户 key, 清理历史遗留

背景: 永久记忆 key = md5(f"{user_id}_{name}")[:16], 历史 user_id 变更/多入口
(discord/test/memory_test_user/已清理会话) 导致孤儿文件与当前用户 key 不匹配。
方案A(合并加载 fallback)已恢复可见性; 本脚本将孤儿记忆合并归位, 保持目录整洁。

用法(在 live 网关目录执行):
  python3 tools/memory_governance.py --dry-run   # 只报告
  python3 tools/memory_governance.py --merge     # 合并孤儿到目标用户 + 归档源文件
"""
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

DATA_ROOT = Path(__file__).resolve().parent.parent / "data"
MEM_DIR = DATA_ROOT / "permanent_memory"

# 合并目标: 网关主用户(需按部署调整)
TARGET_USER = "web_1783219071801"
TARGET_NAME = "memory_agent_v4"

# 已破解归属(无需迁移, 由精确 key 或方案A fallback 读取)
KNOWN_USER = {
    "41bc87125166c472": "web_1783219071801",
    "5fd59f6287d7e6c9": "test",
    "eb2396aaed09f5f3": "memory_test_user",
    "d9e0deae9e5ee037": "discord_1103300395406725150",
}
# 孤儿(未破解 user_id, 时间戳 6/27 批次) — 合并候选
ORPHANS = ["0fc8dcbb88bfb788", "81524bb7356a68da", "910c7eb3b85fb81a"]


def _ts(v: dict) -> str:
    return str(v.get("timestamp", ""))


def main():
    dry = "--merge" not in sys.argv
    print(f"== 永久记忆治理 {'DRY-RUN' if dry else 'EXECUTE'} ==")
    print(f"目录: {MEM_DIR}")
    if not MEM_DIR.exists():
        print("记忆目录不存在, 退出")
        return
    files = sorted(MEM_DIR.glob("*.json"))
    print(f"共 {len(files)} 个记忆文件\n")

    target_key = hashlib.md5(f"{TARGET_USER}_{TARGET_NAME}".encode()).hexdigest()[:16]
    target_file = MEM_DIR / f"{target_key}.json"

    # 收集孤儿记忆(同 key 冲突取最新时间戳)
    orphan_mem = {}
    orphan_files = []
    for f in files:
        if f.stem not in ORPHANS:
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  [SKIP] {f.name} 解析失败: {e}")
            continue
        orphan_files.append(f)
        for k, v in data.items():
            if not isinstance(v, dict) or "value" not in v:
                continue
            if k not in orphan_mem or _ts(v) > _ts(orphan_mem[k]):
                orphan_mem[k] = v  # 最新时间戳胜出

    print("== 孤儿记忆(合并候选) ==")
    for f in orphan_files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        for k, v in data.items():
            if isinstance(v, dict) and "value" in v:
                print(f"  {f.name}  {k}: {str(v.get('value'))[:30]}  @{_ts(v)[:16]}")
    if not orphan_mem:
        print("无孤儿记忆")
        return

    print(f"\n== 合并计划: {len(orphan_mem)} 条 → {target_file.name} ==")
    for k, v in orphan_mem.items():
        print(f"  + {k}: {str(v.get('value'))[:30]}  @{_ts(v)[:16]}")

    if dry:
        print("\n[DRY-RUN] 未执行。加 --merge 执行。")
        return

    # 执行: 合并到目标文件(保留已有, 孤儿新值覆盖同 key 旧值)
    existing = {}
    if target_file.exists():
        try:
            existing = json.loads(target_file.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
    existing.update(orphan_mem)
    target_file.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✅ 已合并 {len(orphan_mem)} 条到 {target_file.name}")

    # 归档源文件(不删除, 可回溯)
    backup_dir = MEM_DIR / ".backup"
    backup_dir.mkdir(exist_ok=True)
    for f in orphan_files:
        dest = backup_dir / f.name
        if f.exists():
            shutil.move(str(f), str(dest))
            print(f"  🗂 {f.name} → .backup/")
    print("\n✅ 治理完成: 孤儿已合并, 源文件归档 .backup")


if __name__ == "__main__":
    main()
