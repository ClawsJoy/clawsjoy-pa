#!/usr/bin/env python3
"""全量重建 dependency_graph.json（依赖图）

现状: code_entity_extractor.update_dependency_graph 只在 write_file 后
增量更新单文件条目 -> 图不完整(仅含 Agent 写过的文件)。
precision_feed 从 {沙箱}/data/dependency_graph.json 注入, 与生成位置
(core/lib/) 不一致 -> 注入源永远为空。

本工具:
1. 扫描 core/ + engine/ + agent_gateway_enhanced.py 真实 .py 模块
2. AST 提取 import 路径(与 _extract_import_paths 同逻辑)
3. 原子写 core/lib/dependency_graph.json (registry/SAG 入库用)
4. 镜像写 {沙箱}/data/dependency_graph.json (precision_feed 注入用)

用法: python3 tools/backfill_dependency_graph.py [--dry-run]
"""
import sys
import ast
import json
import os
import tempfile
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

# 扫描范围：核心实现模块（与 backfill_world_model 一致）
SCAN_DIRS = ["core/gateway", "core/lib", "core/tools", "core/context"]
SCAN_FILES = ["agent_gateway_enhanced.py"]
EXCLUDE = ("__pycache__", "_tmp_", "_gate", "_vfy", "vfy_", "_fix", "test_", ".pyc")


def _scan_py_files():
    found = []
    for d in SCAN_DIRS:
        p = WORKSPACE_ROOT / d
        if not p.exists():
            print(f"  [SKIP] {d} 不存在")
            continue
        for f in sorted(p.rglob("*.py")):
            if any(tok in f.name for tok in EXCLUDE):
                continue
            found.append(f)
    for rel in SCAN_FILES:
        f = WORKSPACE_ROOT / rel
        if f.exists():
            found.append(f)
    return found


def _extract_import_paths(content):
    """与 code_entity_extractor._extract_import_paths 同逻辑"""
    mods = []
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return mods
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mods.append(node.module)
    return list(dict.fromkeys(mods))[:30]


def _key_for(path):
    """key = basename（与 update_dependency_graph 的 rsplit('/')[-1] 一致）"""
    return path.name


def _atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    except Exception:
        os.unlink(tmp)
        raise


def main():
    dry = "--dry-run" in sys.argv
    files = _scan_py_files()
    print(f"扫描到 {len(files)} 个 .py 文件")
    graph = {}
    ok = skip = 0
    for f in files:
        try:
            content = f.read_text(encoding="utf-8")
        except Exception:
            skip += 1
            continue
        imports = _extract_import_paths(content)
        graph[_key_for(f)] = imports
        ok += 1
    print(f"提取完成: {ok} 文件, 跳过 {skip}, 图条目 {len(graph)}")

    core_lib_path = WORKSPACE_ROOT / "core" / "lib" / "dependency_graph.json"
    print(f"写入: {core_lib_path} ({len(graph)} 条)")
    if not dry:
        _atomic_write(core_lib_path, graph)

    # 镜像写沙箱项目 data/（precision_feed 注入源）
    sandbox_data = WORKSPACE_ROOT / "data" / "dependency_graph.json"
    if WORKSPACE_ROOT.name == "clawsjoy_dev" or (WORKSPACE_ROOT / "data").exists():
        print(f"镜像写入: {sandbox_data}")
        if not dry:
            _atomic_write(sandbox_data, graph)
    else:
        print(f"[SKIP] 沙箱 data/ 目录不存在: {sandbox_data.parent}")

    print("done")


if __name__ == "__main__":
    main()
