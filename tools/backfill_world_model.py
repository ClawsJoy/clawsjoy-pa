#!/usr/bin/env python3
"""补全 world_model：扫描真实 core/ 模块入库（过滤网基准）

评估报告（filter_reliability_assessment.md）发现 world_model 只记录
Agent 写过的文件（全是 _*.py 测试文件），真实模块未入库 → 过滤基准弱。
本工具把 core/ 下真实 .py 模块用 _update_world_model 逻辑全量入库。
用法: python3 tools/backfill_world_model.py [--dry-run]
"""
import json
import re
import sys
from pathlib import Path

# 工作区根：脚本自身路径推导（cwd 无关，可在任意目录运行）
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

USER_ID = "web_1783219071801"
SESSION_ID = "session_1783388196051"
PROJECT_ROOT = "clawsjoy_dev"
# 要扫描的真实模块目录（相对工作区根）
SCAN_DIRS = ["core/gateway", "core/lib", "core/tools", "core/context"]
EXCLUDE = ("__pycache__", "_tmp_", "_gate", "_vfy", "vfy_", "_fix", "test_")


def scan_modules():
    """扫描真实 .py 模块（相对 WORKSPACE_ROOT，cwd 无关）"""
    found = []
    for d in SCAN_DIRS:
        p = WORKSPACE_ROOT / d
        if not p.exists():
            print(f"  [SKIP] {d} 不存在")
            continue
        for f in sorted(p.glob("*.py")):
            name = f.name
            if any(x in name for x in EXCLUDE):
                continue
            found.append(str(f))
    return found


def main():
    dry = "--dry-run" in sys.argv
    files = scan_modules()
    print(f"=== 扫描到 {len(files)} 个真实模块 ===")
    for f in files[:20]:
        print(f"  {f}")
    if len(files) > 20:
        print(f"  ... 共 {len(files)} 个")

    from core.gateway.execute_agent_task import _update_world_model

    ok = 0
    for f in files:
        try:
            content = Path(f).read_text(encoding="utf-8")
            if dry:
                print(f"  [DRY] 将入库 {f} ({len(content.splitlines())} 行)")
                ok += 1
                continue
            _update_world_model(f, content, USER_ID, SESSION_ID)
            ok += 1
        except Exception as e:
            print(f"  [FAIL] {f}: {e}")
    print(f"=== {'模拟' if dry else '完成'}入库 {ok}/{len(files)} ===")
    if not dry:
        # 验证
        state = json.loads(
            Path(f"data/projects/{USER_ID}/{SESSION_ID}/{PROJECT_ROOT}/.agent_state.json").read_text(encoding="utf-8")
        )
        mods = state.get("world_model", {}).get("modules", {})
        real = [k for k in mods if not any(x in k for x in EXCLUDE)]
        print(f"world_model 模块总数: {len(mods)}，其中真实模块: {len(real)}")


if __name__ == "__main__":
    main()
