# -*- coding: utf-8 -*-
"""沙箱工具模块：从 agent_gateway_enhanced.py 提取的独立工具函数。

本模块目前仅包含 `_generate_project_tree`（项目文件树生成），
`_execute_sandbox_tool` 及其复杂依赖链按 P1 #144 约束暂不提取。
"""
import os  # noqa: F401  （保留备用，后续工具可能使用）
import json
from pathlib import Path


def _generate_project_tree(user_id="default", session_id="default"):
    """从磁盘扫描 + world_model 合并生成项目文件树。

    断点1 修复: 根目录从"会话沙箱"(data/projects/{uid}/{sid}/clawsjoy_dev, 空 → len=0)
    改为"项目根"(本模块 core/lib/ → 上三级 = 网关工作区, 与 agent_gateway 的 _PROJECT_ROOT 同源),
    让 Agent 知道 core/config/data 在哪。
    大项目(>50 文件)自动走摘要模式(顶层目录 + 入口文件), 注入体积有界;
    >50 时跳过逐文件 meta(行数/函数)计算, 防每次请求全量读文件; 扫描设上限防 data/projects 膨胀。
    """
    _base = Path(__file__).resolve().parent.parent.parent
    if not _base.exists():
        return ""
    try:
        _paths = set()
        _skip_parts = ('__pycache__', '.git', 'code_index', 'vector_db', '.pytest_cache',
                       'node_modules', '.venv', 'venv', '.agent_state.json',
                       '.progress_checkpoint.json', 'sandbox', 'logs', 'exports', 'web/static')
        # 1. 顶层登记(摘要模式完整性: 不依赖 rglob 顺序/上限) — data/ 一并登记, 目录单独收集
        _top_dirs = set()
        try:
            for _e in _base.iterdir():
                _n = _e.name
                if _n in _skip_parts or _n.startswith("."):
                    continue
                if _e.is_dir():
                    _top_dirs.add(_n)
                _paths.add(_n)
        except Exception:
            pass
        # 2. 递归扫描(上限 800; data/ 跳过防海量 session 文件; 其余排除噪音)
        for _f in _base.rglob("*"):
            if not _f.is_file():
                continue
            _rel = str(_f.relative_to(_base))
            _rp = _rel.split("/")
            if _rp[0] == "data" or any(p in _rp for p in _skip_parts):
                continue
            _paths.add(_rel)
            if len(_paths) > 800:
                break
        # 3. world_model 补充（可能有 write_file 过但磁盘尚未写入的 — 会话沙箱状态）
        _state_file = Path(f"data/projects/{user_id}/{session_id}/clawsjoy_dev") / ".agent_state.json"
        if _state_file.exists():
            _state = json.loads(_state_file.read_text())
            _wm = _state.get("world_model", {})
            if isinstance(_wm, str):
                _wm = json.loads(_wm)
            for _k in _wm.get("modules", {}):
                _rel = _k.split("clawsjoy_dev/")[-1] if "clawsjoy_dev/" in _k else _k
                _paths.add(_rel)
        if not _paths:
            return ""
        _sorted_paths = sorted(_paths)
        _tree_lines = ["clawsjoy_dev/"]
        _total_files = len(_paths)
        if _total_files > 50:
            # 大项目摘要模式: 顶层目录(仅目录) + 顶层入口文件(不再计算逐文件 meta)
            _key_files = []
            for _p in _sorted_paths:
                _parts = _p.split("/")
                if _parts[0] in _top_dirs:
                    continue
                if _p in ('app.py', 'config.py', 'requirements.txt', 'README.md', 'agent_gateway_enhanced.py', 'conftest.py') or _p.endswith('/__init__.py'):
                    continue
                if _p.endswith('.py') and '/' not in _p:
                    _key_files.append(_p)
            _tree_lines.append(f" 顶层目录: {', '.join(sorted(_top_dirs)[:20])}")
            if _key_files:
                _tree_lines.append(f" 顶层入口文件: {', '.join(_key_files[:10])}")
        else:
            # 小项目完整树(<=50 文件才计算 meta, 防大项目全量读文件)
            _all_nodes = {}
            for _p in _sorted_paths:
                _parts = ["clawsjoy_dev"] + _p.split("/")
                for _i in range(1, len(_parts)):
                    _parent = "/".join(_parts[:_i])
                    _node = "/".join(_parts[:_i+1])
                    if _parent not in _all_nodes:
                        _all_nodes[_parent] = []
                    if _node not in _all_nodes[_parent]:
                        _all_nodes[_parent].append(_node)
            _meta = {}
            try:
                _wm = json.loads(_state_file.read_text()).get("world_model", {})
                if isinstance(_wm, str):
                    _wm = json.loads(_wm)
                for _fp, _info in _wm.get("modules", {}).items():
                    _short = _fp.split("clawsjoy_dev/")[-1] if "clawsjoy_dev/" in _fp else _fp
                    _lines = _info.get("lines", 0)
                    _funcs = _info.get("functions", [])
                    _classes = _info.get("classes", [])
                    _parts = []
                    if _lines:
                        _parts.append(f"{_lines}行")
                    if _classes:
                        _parts.append("class " + ", ".join(_classes[:2]))
                    if _funcs:
                        _parts.append(", ".join(_funcs[:3]))
                    _meta[_short] = " (" + "; ".join(_parts) + ")" if _parts else ""
            except Exception:
                pass
            for _p in _paths:
                if _p not in _meta:
                    try:
                        _disk_f = _base / _p
                        if _disk_f.exists() and _disk_f.suffix == '.py':
                            _fc = _disk_f.read_text()
                            _fc_lines = len(_fc.split('\n'))
                            import re as _re_meta
                            _fc_funcs = _re_meta.findall(r'^def\s+(\w+)', _fc, _re_meta.MULTILINE)
                            _fc_classes = _re_meta.findall(r'^class\s+(\w+)', _fc, _re_meta.MULTILINE)
                            _parts = [f"{_fc_lines}行"]
                            if _fc_classes:
                                _parts.append("class " + ", ".join(_fc_classes[:2]))
                            if _fc_funcs:
                                _parts.append(", ".join(_fc_funcs[:3]))
                            _meta[_p] = " (" + "; ".join(_parts) + ")"
                    except Exception:
                        pass

            def _render(_key, _depth):
                if _key in _all_nodes:
                    _children = _all_nodes[_key]
                    for _j, _child in enumerate(_children):
                        _name = _child.split("/")[-1]
                        _full = _child
                        if _full.startswith("clawsjoy_dev/"):
                            _full = _full[len("clawsjoy_dev/"):]
                        _extra = _meta.get(_full, "")
                        _is_last = (_j == len(_children) - 1)
                        _indent = "  " * _depth + ("└─ " if _is_last else "├─ ")
                        _tree_lines.append(f"{_indent}{_name}{_extra}")
                        _render(_child, _depth + 1)
            _render("clawsjoy_dev", 0)
        # 追加统计摘要
        _py_count = sum(1 for _p in _paths if _p.endswith('.py'))
        _agent_count = len([_p for _p in _paths if _p.startswith('agents/') and _p.endswith('.py') and _p.count('/') == 1])
        if _total_files > 10:
            _summary = f"\n项目规模: {_total_files} 文件, {_py_count} Python 文件"
            if _agent_count:
                _summary += f", {_agent_count} 个 Agent"
            _tree_lines.append(_summary)
        return "\n".join(_tree_lines) if _tree_lines else ""
    except Exception:
        return ""
